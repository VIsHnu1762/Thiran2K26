"""
BillAgent Pro - Abstract OCR Engine Base Class
===============================================
Defines the interface for all OCR engine implementations.
Supports multiple engines with consistent output format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes for OCR Results
# =============================================================================

@dataclass
class BoundingBox:
    """
    Bounding box coordinates for a detected text region.
    Uses normalized coordinates (0.0 to 1.0) relative to image dimensions.
    """
    x1: float  # Top-left X (0.0 to 1.0)
    y1: float  # Top-left Y (0.0 to 1.0)
    x2: float  # Bottom-right X (0.0 to 1.0)
    y2: float  # Bottom-right Y (0.0 to 1.0)
    
    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for JSON serialization."""
        return {
            "x1": self.x1,
            "y1": self.y1,
            "x2": self.x2,
            "y2": self.y2,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> "BoundingBox":
        """Create from dictionary."""
        return cls(
            x1=data["x1"],
            y1=data["y1"],
            x2=data["x2"],
            y2=data["y2"],
        )
    
    @classmethod
    def from_polygon(cls, polygon: List[List[float]], image_width: int, image_height: int) -> "BoundingBox":
        """
        Create from polygon coordinates (typically [[x1,y1], [x2,y1], [x2,y2], [x1,y2]]).
        Normalizes to 0.0-1.0 range based on image dimensions.
        """
        xs = [p[0] for p in polygon]
        ys = [p[1] for p in polygon]
        return cls(
            x1=min(xs) / image_width,
            y1=min(ys) / image_height,
            x2=max(xs) / image_width,
            y2=max(ys) / image_height,
        )
    
    def to_absolute(self, image_width: int, image_height: int) -> Dict[str, int]:
        """Convert normalized coordinates to absolute pixel values."""
        return {
            "x1": int(self.x1 * image_width),
            "y1": int(self.y1 * image_height),
            "x2": int(self.x2 * image_width),
            "y2": int(self.y2 * image_height),
        }


@dataclass
class OCRField:
    """
    A single extracted field with confidence and bounding box.
    """
    name: str                           # Field name (e.g., "vendor_name", "invoice_number")
    value: Any                          # Extracted value
    confidence: float                   # Confidence score (0.0 to 1.0)
    bounding_box: Optional[BoundingBox] = None  # Location in image
    raw_text: Optional[str] = None      # Original text before parsing
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "value": self.value if not isinstance(self.value, (date, Decimal)) else str(self.value),
            "confidence": self.confidence,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "raw_text": self.raw_text,
        }


@dataclass
class OCRLineItem:
    """
    A single line item extracted from a bill.
    """
    description: str
    quantity: Decimal
    unit_price: Decimal
    total_price: Decimal
    unit: Optional[str] = None
    confidence: float = 0.0
    field_confidence: Dict[str, float] = field(default_factory=dict)
    bounding_box: Optional[BoundingBox] = None
    sort_order: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "description": self.description,
            "quantity": str(self.quantity),
            "unit_price": str(self.unit_price),
            "total_price": str(self.total_price),
            "unit": self.unit,
            "confidence": self.confidence,
            "field_confidence": self.field_confidence,
            "bounding_box": self.bounding_box.to_dict() if self.bounding_box else None,
            "sort_order": self.sort_order,
        }


class OCREngineType(str, Enum):
    """Supported OCR engines."""
    MISTRAL = "mistral_ocr"
    GPT4_VISION = "gpt4_vision"
    GEMINI = "gemini_vision"
    EASYOCR = "easyocr"


@dataclass
class OCRResult:
    """
    Complete result from OCR processing.
    Contains all extracted data with confidence scores and bounding boxes.
    """
    # Success/failure
    success: bool = False
    error_message: Optional[str] = None
    
    # Engine info
    engine: OCREngineType = OCREngineType.MISTRAL
    processing_time_ms: int = 0
    
    # Extracted header fields
    vendor_name: Optional[OCRField] = None
    invoice_number: Optional[OCRField] = None
    invoice_date: Optional[OCRField] = None
    due_date: Optional[OCRField] = None
    subtotal: Optional[OCRField] = None
    tax_amount: Optional[OCRField] = None
    total_amount: Optional[OCRField] = None
    currency: Optional[OCRField] = None
    
    # Line items
    line_items: List[OCRLineItem] = field(default_factory=list)
    
    # Overall confidence
    overall_confidence: float = 0.0
    
    # Raw OCR response (for debugging)
    raw_response: Optional[Dict[str, Any]] = None
    
    # All bounding boxes indexed by field name
    bounding_boxes: Dict[str, BoundingBox] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON/JSONB storage."""
        result = {
            "success": self.success,
            "error_message": self.error_message,
            "engine": self.engine.value,
            "processing_time_ms": self.processing_time_ms,
            "overall_confidence": self.overall_confidence,
            "line_items": [item.to_dict() for item in self.line_items],
            "bounding_boxes": {k: v.to_dict() for k, v in self.bounding_boxes.items()},
        }
        
        # Add header fields
        for field_name in ["vendor_name", "invoice_number", "invoice_date", 
                          "due_date", "subtotal", "tax_amount", "total_amount", "currency"]:
            field_obj = getattr(self, field_name)
            if field_obj:
                result[field_name] = field_obj.to_dict()
        
        return result
    
    def get_field_confidence(self) -> Dict[str, float]:
        """Get confidence scores for all fields."""
        confidence = {}
        
        for field_name in ["vendor_name", "invoice_number", "invoice_date", 
                          "due_date", "subtotal", "tax_amount", "total_amount", "currency"]:
            field_obj = getattr(self, field_name)
            if field_obj:
                confidence[field_name] = field_obj.confidence
        
        # Add average line item confidence
        if self.line_items:
            confidence["line_items_avg"] = sum(
                item.confidence for item in self.line_items
            ) / len(self.line_items)
        
        return confidence
    
    def calculate_overall_confidence(self) -> float:
        """Calculate weighted overall confidence score."""
        weights = {
            "vendor_name": 1.5,
            "invoice_number": 1.5,
            "invoice_date": 1.2,
            "total_amount": 2.0,
            "line_items_avg": 2.0,
        }
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        field_confidence = self.get_field_confidence()
        
        for field_name, weight in weights.items():
            if field_name in field_confidence:
                weighted_sum += field_confidence[field_name] * weight
                total_weight += weight
        
        if total_weight > 0:
            self.overall_confidence = weighted_sum / total_weight
        
        return self.overall_confidence


# =============================================================================
# Abstract OCR Engine
# =============================================================================

class OCREngine(ABC):
    """
    Abstract base class for OCR engines.
    All OCR implementations must inherit from this class.
    """
    
    @property
    @abstractmethod
    def engine_type(self) -> OCREngineType:
        """Return the engine type identifier."""
        pass
    
    @property
    @abstractmethod
    def supports_bounding_boxes(self) -> bool:
        """Whether this engine returns bounding box coordinates."""
        pass
    
    @property
    @abstractmethod
    def supports_handwritten(self) -> bool:
        """Whether this engine handles handwritten text well."""
        pass
    
    @abstractmethod
    async def extract(self, image_bytes: bytes) -> OCRResult:
        """
        Extract text and structured data from an image.
        
        Args:
            image_bytes: Raw image bytes (JPEG, PNG, etc.)
            
        Returns:
            OCRResult with extracted data, confidence scores, and bounding boxes
        """
        pass
    
    async def health_check(self) -> Tuple[bool, str]:
        """
        Check if the OCR engine is available and functioning.
        
        Returns:
            Tuple of (is_healthy, message)
        """
        try:
            # Simple test - subclasses can override for more specific checks
            return True, f"{self.engine_type.value} is available"
        except Exception as e:
            return False, f"{self.engine_type.value} health check failed: {str(e)}"
    
    def _create_error_result(self, error_message: str) -> OCRResult:
        """Create an error result."""
        return OCRResult(
            success=False,
            error_message=error_message,
            engine=self.engine_type,
        )
    
    def _get_image_dimensions(self, image_bytes: bytes) -> Tuple[int, int]:
        """Get image width and height from bytes."""
        from PIL import Image
        import io
        
        image = Image.open(io.BytesIO(image_bytes))
        return image.width, image.height
