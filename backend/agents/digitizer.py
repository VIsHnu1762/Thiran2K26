"""
BillAgent Pro - Digitizer Agent
================================
Agent 1: Primary agent responsible for bill digitization.
Orchestrates OCR extraction with fallback and retry logic.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

# Import from app module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.ocr import (
    OCREngine,
    OCREngineType,
    OCRResult,
    OCRParser,
    MistralOCR,
    GPT4VisionOCR,
)
from app.config import get_settings

logger = logging.getLogger(__name__)


class DigitizationStatus(str, Enum):
    """Status of digitization process."""
    SUCCESS = "success"
    PARTIAL = "partial"  # Some fields missing but usable
    FALLBACK_USED = "fallback_used"  # Primary failed, fallback succeeded
    FAILED = "failed"


@dataclass
class DigitizationResult:
    """
    Result of the digitization process.
    Contains OCR results, metadata, and processing information.
    """
    status: DigitizationStatus
    ocr_result: Optional[OCRResult] = None
    bill_data: Optional[dict] = None
    metadata: Optional[dict] = None
    validation_errors: List[dict] = field(default_factory=list)
    suggested_status: str = "PROCESSING"
    vendor_id: Optional[UUID] = None
    
    # Processing info
    primary_engine_used: bool = True
    fallback_reason: Optional[str] = None
    total_processing_time_ms: int = 0
    retry_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "bill_data": self.bill_data,
            "metadata": self.metadata,
            "validation_errors": self.validation_errors,
            "suggested_status": self.suggested_status,
            "vendor_id": str(self.vendor_id) if self.vendor_id else None,
            "primary_engine_used": self.primary_engine_used,
            "fallback_reason": self.fallback_reason,
            "total_processing_time_ms": self.total_processing_time_ms,
            "retry_count": self.retry_count,
        }


class DigitizerAgent:
    """
    Agent 1: Digitizer Agent
    
    Responsible for:
    - Orchestrating OCR extraction from bill images
    - Managing primary/fallback OCR engine selection
    - Retry logic with exponential backoff
    - Vendor lookup/creation
    - Returning structured data with confidence scores and bounding boxes
    """
    
    def __init__(
        self,
        primary_ocr: Optional[OCREngine] = None,
        fallback_ocr: Optional[OCREngine] = None,
        parser: Optional[OCRParser] = None,
        vendor_repository=None,
        max_retries: int = 2,
        retry_delay: float = 1.0,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize the Digitizer Agent.
        
        Args:
            primary_ocr: Primary OCR engine (default: MistralOCR)
            fallback_ocr: Fallback OCR engine (default: GPT4VisionOCR)
            parser: OCR result parser
            vendor_repository: Repository for vendor operations
            max_retries: Maximum retry attempts per engine
            retry_delay: Initial delay between retries
            confidence_threshold: Minimum confidence to accept result
        """
        self.settings = get_settings()
        
        # Initialize OCR engines
        self.primary_ocr = primary_ocr or self._create_primary_ocr()
        self.fallback_ocr = fallback_ocr or self._create_fallback_ocr()
        
        # Initialize parser
        self.parser = parser or OCRParser(vendor_repository=vendor_repository)
        self.vendor_repository = vendor_repository
        
        # Configuration
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.confidence_threshold = confidence_threshold
    
    def _create_primary_ocr(self) -> Optional[OCREngine]:
        """Create primary OCR engine (Mistral)."""
        api_key = self.settings.mistral_api_key
        if not api_key:
            logger.warning("Mistral API key not configured, primary OCR unavailable")
            return None
        
        return MistralOCR(api_key=api_key)
    
    def _create_fallback_ocr(self) -> Optional[OCREngine]:
        """Create fallback OCR engine (GPT-4o)."""
        api_key = self.settings.openai_api_key
        if not api_key:
            logger.warning("OpenAI API key not configured, fallback OCR unavailable")
            return None
        
        return GPT4VisionOCR(api_key=api_key)
    
    async def extract(
        self,
        image_bytes: bytes,
        image_url: str = "",
        db_session=None,
    ) -> DigitizationResult:
        """
        Extract structured data from a bill image.
        
        This is the main entry point for bill digitization.
        It orchestrates:
        1. Primary OCR extraction with retries
        2. Fallback OCR if primary fails or has low confidence
        3. Vendor lookup/creation
        4. Validation and status determination
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            image_url: Path/URL to the stored image
            db_session: Database session for vendor operations
            
        Returns:
            DigitizationResult with extracted data, metadata, and status
        """
        start_time = time.perf_counter()
        total_retries = 0
        
        logger.info(f"Starting bill digitization for image: {image_url}")
        
        # Try primary OCR
        ocr_result = None
        primary_used = True
        fallback_reason = None
        
        if self.primary_ocr:
            ocr_result, retries = await self._extract_with_retry(
                self.primary_ocr,
                image_bytes,
            )
            total_retries += retries
            
            # Check if result is acceptable
            if ocr_result and ocr_result.success:
                if ocr_result.overall_confidence >= self.confidence_threshold:
                    logger.info(
                        f"Primary OCR ({self.primary_ocr.engine_type.value}) succeeded "
                        f"with {ocr_result.overall_confidence:.1%} confidence"
                    )
                else:
                    logger.warning(
                        f"Primary OCR has low confidence ({ocr_result.overall_confidence:.1%}), "
                        f"trying fallback"
                    )
                    fallback_reason = f"Low confidence: {ocr_result.overall_confidence:.1%}"
                    ocr_result = None
            else:
                fallback_reason = ocr_result.error_message if ocr_result else "Primary OCR failed"
                ocr_result = None
        else:
            fallback_reason = "Primary OCR not configured"
        
        # Try fallback OCR if needed
        if ocr_result is None and self.fallback_ocr:
            logger.info(f"Using fallback OCR ({self.fallback_ocr.engine_type.value})")
            primary_used = False
            
            ocr_result, retries = await self._extract_with_retry(
                self.fallback_ocr,
                image_bytes,
            )
            total_retries += retries
        
        # Calculate total time
        total_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        # Handle complete failure
        if ocr_result is None or not ocr_result.success:
            logger.error("All OCR engines failed")
            return DigitizationResult(
                status=DigitizationStatus.FAILED,
                ocr_result=ocr_result,
                validation_errors=[{
                    "field": "ocr",
                    "message": ocr_result.error_message if ocr_result else "All OCR engines failed",
                    "severity": "error",
                }],
                suggested_status="FAILED",
                primary_engine_used=primary_used,
                fallback_reason=fallback_reason,
                total_processing_time_ms=total_time_ms,
                retry_count=total_retries,
            )
        
        # Parse and validate results
        is_valid, validation_errors = self.parser.validate_extraction(ocr_result)
        suggested_status = self.parser.determine_status(ocr_result, validation_errors)
        
        # Convert to bill data
        bill_data = self.parser.to_bill_create_data(ocr_result, image_url)
        metadata = self.parser.extract_metadata(ocr_result)
        
        # Lookup/create vendor
        vendor_id = None
        if ocr_result.vendor_name and ocr_result.vendor_name.value:
            vendor_id = await self.parser.lookup_or_create_vendor(
                ocr_result.vendor_name.value,
                db_session=db_session,
            )
            if vendor_id:
                bill_data["vendor_id"] = vendor_id
        
        # Determine final status
        if not primary_used:
            status = DigitizationStatus.FALLBACK_USED
        elif ocr_result.overall_confidence < 0.85:
            status = DigitizationStatus.PARTIAL
        else:
            status = DigitizationStatus.SUCCESS
        
        logger.info(
            f"Digitization completed: status={status.value}, "
            f"confidence={ocr_result.overall_confidence:.1%}, "
            f"items={len(ocr_result.line_items)}, "
            f"time={total_time_ms}ms"
        )
        
        return DigitizationResult(
            status=status,
            ocr_result=ocr_result,
            bill_data=bill_data,
            metadata=metadata,
            validation_errors=validation_errors,
            suggested_status=suggested_status,
            vendor_id=vendor_id,
            primary_engine_used=primary_used,
            fallback_reason=fallback_reason if not primary_used else None,
            total_processing_time_ms=total_time_ms,
            retry_count=total_retries,
        )
    
    async def _extract_with_retry(
        self,
        engine: OCREngine,
        image_bytes: bytes,
    ) -> Tuple[Optional[OCRResult], int]:
        """
        Attempt OCR extraction with retry logic.
        
        Args:
            engine: OCR engine to use
            image_bytes: Raw image bytes
            
        Returns:
            Tuple of (OCRResult, retry_count)
        """
        last_result = None
        
        for attempt in range(self.max_retries + 1):
            try:
                result = await engine.extract(image_bytes)
                
                if result.success:
                    return result, attempt
                
                last_result = result
                
                # Don't retry on certain errors
                if "Invalid" in (result.error_message or ""):
                    break
                
            except Exception as e:
                logger.warning(
                    f"OCR attempt {attempt + 1} failed: {e}",
                    exc_info=True,
                )
                last_result = engine._create_error_result(str(e))
            
            # Wait before retry (exponential backoff)
            if attempt < self.max_retries:
                delay = self.retry_delay * (2 ** attempt)
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        return last_result, self.max_retries
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Check health of all OCR engines.
        
        Returns:
            Dictionary with health status of each engine
        """
        results = {
            "primary": {"available": False, "message": "Not configured"},
            "fallback": {"available": False, "message": "Not configured"},
        }
        
        if self.primary_ocr:
            is_healthy, message = await self.primary_ocr.health_check()
            results["primary"] = {
                "available": is_healthy,
                "message": message,
                "engine": self.primary_ocr.engine_type.value,
            }
        
        if self.fallback_ocr:
            is_healthy, message = await self.fallback_ocr.health_check()
            results["fallback"] = {
                "available": is_healthy,
                "message": message,
                "engine": self.fallback_ocr.engine_type.value,
            }
        
        return results
    
    async def close(self):
        """Clean up resources."""
        if self.primary_ocr is not None:
            if hasattr(self.primary_ocr, 'close'):
                coro = self.primary_ocr.close()  # type: ignore
                if asyncio.iscoroutine(coro):
                    await coro
        
        if self.fallback_ocr is not None:
            if hasattr(self.fallback_ocr, 'close'):
                coro = self.fallback_ocr.close()  # type: ignore
                if asyncio.iscoroutine(coro):
                    await coro


# =============================================================================
# Factory function for easy instantiation
# =============================================================================

def create_digitizer_agent(
    vendor_repository=None,
    **kwargs,
) -> DigitizerAgent:
    """
    Factory function to create a DigitizerAgent with default configuration.
    
    Args:
        vendor_repository: Repository for vendor operations
        **kwargs: Additional arguments passed to DigitizerAgent
        
    Returns:
        Configured DigitizerAgent instance
    """
    return DigitizerAgent(
        vendor_repository=vendor_repository,
        **kwargs,
    )
