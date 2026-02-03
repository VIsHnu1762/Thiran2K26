"""
BillAgent Pro - OCR Response Parser
====================================
Converts OCR results to database models and performs data enrichment.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import UUID

from .base import OCRResult, OCRLineItem

logger = logging.getLogger(__name__)


class OCRParser:
    """
    Parses and transforms OCR results into database-ready structures.
    Performs validation, enrichment, and vendor lookup/creation.
    """
    
    def __init__(self, vendor_repository=None):
        """
        Initialize parser with optional vendor repository for lookups.
        
        Args:
            vendor_repository: Repository for vendor database operations
        """
        self.vendor_repository = vendor_repository
    
    def to_bill_create_data(
        self,
        ocr_result: OCRResult,
        image_url: str,
    ) -> dict:
        """
        Convert OCR result to data suitable for BillCreate schema.
        
        Args:
            ocr_result: Parsed OCR result
            image_url: Path/URL to the bill image
            
        Returns:
            Dictionary compatible with BillCreate schema
        """
        data = {
            "image_url": image_url,
            "line_items": [],
        }
        
        # Extract header fields
        if ocr_result.vendor_name:
            data["vendor_name"] = ocr_result.vendor_name.value
        
        if ocr_result.invoice_number:
            data["invoice_number"] = ocr_result.invoice_number.value
        
        if ocr_result.invoice_date and ocr_result.invoice_date.value:
            data["invoice_date"] = ocr_result.invoice_date.value
        
        if ocr_result.due_date and ocr_result.due_date.value:
            data["due_date"] = ocr_result.due_date.value
        
        if ocr_result.subtotal and ocr_result.subtotal.value:
            data["subtotal"] = ocr_result.subtotal.value
        
        if ocr_result.tax_amount and ocr_result.tax_amount.value:
            data["tax_amount"] = ocr_result.tax_amount.value
        
        if ocr_result.total_amount and ocr_result.total_amount.value:
            data["total_amount"] = ocr_result.total_amount.value
        
        if ocr_result.currency:
            data["currency"] = ocr_result.currency.value
        
        # Convert line items
        for item in ocr_result.line_items:
            line_item_data = self._convert_line_item(item)
            data["line_items"].append(line_item_data)
        
        return data
    
    def _convert_line_item(self, ocr_item: OCRLineItem) -> dict:
        """Convert OCR line item to LineItemCreate-compatible dict."""
        return {
            "description": ocr_item.description,
            "quantity": ocr_item.quantity,
            "unit": ocr_item.unit,
            "unit_price": ocr_item.unit_price,
            "total_price": ocr_item.total_price,
            "sort_order": ocr_item.sort_order,
        }
    
    def extract_metadata(self, ocr_result: OCRResult) -> dict:
        """
        Extract metadata for bill record (confidence, bounding boxes, raw data).
        
        Args:
            ocr_result: Parsed OCR result
            
        Returns:
            Dictionary with confidence scores, bounding boxes, etc.
        """
        return {
            "confidence_score": ocr_result.overall_confidence,
            "field_confidence": ocr_result.get_field_confidence(),
            "bounding_boxes": {k: v.to_dict() for k, v in ocr_result.bounding_boxes.items()},
            "ocr_raw_data": ocr_result.raw_response,
            "ocr_engine": ocr_result.engine.value,
            "processing_time_ms": ocr_result.processing_time_ms,
        }
    
    def validate_extraction(self, ocr_result: OCRResult) -> Tuple[bool, List[dict]]:
        """
        Validate OCR extraction results.
        
        Args:
            ocr_result: Parsed OCR result
            
        Returns:
            Tuple of (is_valid, list of validation errors)
        """
        errors = []
        
        # Check for required fields
        if not ocr_result.total_amount or ocr_result.total_amount.value == Decimal("0"):
            errors.append({
                "field": "total_amount",
                "message": "Total amount not found or is zero",
                "severity": "error",
            })
        
        # Validate line items exist
        if not ocr_result.line_items:
            errors.append({
                "field": "line_items",
                "message": "No line items extracted",
                "severity": "warning",
            })
        
        # Validate math consistency
        if ocr_result.line_items and ocr_result.total_amount:
            calculated_total = sum(item.total_price for item in ocr_result.line_items)
            
            # Account for tax if present
            if ocr_result.tax_amount:
                calculated_total += ocr_result.tax_amount.value
            
            actual_total = ocr_result.total_amount.value
            
            # Allow 1% tolerance for rounding
            tolerance = actual_total * Decimal("0.01")
            if abs(calculated_total - actual_total) > tolerance:
                errors.append({
                    "field": "total_amount",
                    "message": f"Math mismatch: sum of items ({calculated_total}) != total ({actual_total})",
                    "severity": "warning",
                    "expected_value": str(calculated_total),
                    "actual_value": str(actual_total),
                })
        
        # Check individual line item math
        for idx, item in enumerate(ocr_result.line_items):
            expected_total = item.quantity * item.unit_price
            tolerance = expected_total * Decimal("0.01")
            
            if abs(expected_total - item.total_price) > tolerance:
                errors.append({
                    "field": f"line_item_{idx}_total",
                    "message": f"Line item math error: {item.quantity} × {item.unit_price} != {item.total_price}",
                    "severity": "warning",
                    "expected_value": str(expected_total),
                    "actual_value": str(item.total_price),
                })
        
        # Check confidence thresholds
        low_confidence_fields = []
        for field_name, confidence in ocr_result.get_field_confidence().items():
            if confidence < 0.7:
                low_confidence_fields.append(field_name)
        
        if low_confidence_fields:
            errors.append({
                "field": "confidence",
                "message": f"Low confidence fields: {', '.join(low_confidence_fields)}",
                "severity": "warning",
            })
        
        # Overall validation passes if no errors (warnings are ok)
        has_errors = any(e["severity"] == "error" for e in errors)
        
        return not has_errors, errors
    
    def determine_status(
        self,
        ocr_result: OCRResult,
        validation_errors: List[dict],
    ) -> str:
        """
        Determine appropriate bill status based on extraction results.
        
        Args:
            ocr_result: Parsed OCR result
            validation_errors: List of validation errors
            
        Returns:
            Suggested bill status
        """
        # If OCR failed
        if not ocr_result.success:
            return "FAILED"
        
        # If there are errors
        has_errors = any(e["severity"] == "error" for e in validation_errors)
        if has_errors:
            return "FAILED"
        
        # If confidence is too low
        if ocr_result.overall_confidence < 0.7:
            return "NEEDS_REVIEW"
        
        # If there are warnings
        has_warnings = any(e["severity"] == "warning" for e in validation_errors)
        if has_warnings or ocr_result.overall_confidence < 0.85:
            return "NEEDS_REVIEW"
        
        # Good extraction - can proceed
        return "PROCESSING"
    
    async def lookup_or_create_vendor(
        self,
        vendor_name: str,
        db_session=None,
    ) -> Optional[UUID]:
        """
        Look up existing vendor or create a new one.
        
        Args:
            vendor_name: Extracted vendor name
            db_session: Database session for operations
            
        Returns:
            Vendor UUID if found/created, None otherwise
        """
        if not vendor_name or not self.vendor_repository:
            return None
        
        try:
            # Normalize vendor name
            normalized_name = self._normalize_vendor_name(vendor_name)
            
            # Try to find existing vendor
            vendor = await self.vendor_repository.find_by_name(
                normalized_name,
                session=db_session,
            )
            
            if vendor:
                logger.info(f"Found existing vendor: {vendor.name} (ID: {vendor.id})")
                return vendor.id
            
            # Create new vendor
            # Import here to avoid circular imports
            try:
                from ..schemas.vendor_schema import VendorCreate
            except ImportError:
                # Fallback for different project structures
                logger.warning("Could not import VendorCreate schema")
                return None
            
            new_vendor = await self.vendor_repository.create(
                VendorCreate(name=normalized_name),
                session=db_session,
            )
            
            logger.info(f"Created new vendor: {new_vendor.name} (ID: {new_vendor.id})")
            return new_vendor.id
            
        except Exception as e:
            logger.warning(f"Failed to lookup/create vendor '{vendor_name}': {e}")
            return None
    
    def _normalize_vendor_name(self, name: str) -> str:
        """
        Normalize vendor name for consistency.
        
        Args:
            name: Raw vendor name
            
        Returns:
            Normalized vendor name
        """
        if not name:
            return ""
        
        # Basic normalization
        normalized = name.strip()
        
        # Remove common suffixes/prefixes
        for suffix in [" Pvt Ltd", " Private Limited", " Ltd", " LLC", " Inc", " Corp"]:
            if normalized.lower().endswith(suffix.lower()):
                normalized = normalized[:-len(suffix)]
        
        # Title case
        normalized = normalized.title()
        
        return normalized.strip()
    
    def enrich_line_items(
        self,
        line_items: List[OCRLineItem],
        gl_code_mapping: Optional[dict] = None,
    ) -> List[dict]:
        """
        Enrich line items with additional data (e.g., suggested GL codes).
        
        Args:
            line_items: OCR extracted line items
            gl_code_mapping: Optional mapping of keywords to GL codes
            
        Returns:
            Enriched line item dictionaries
        """
        enriched = []
        
        for item in line_items:
            item_dict = self._convert_line_item(item)
            
            # Try to suggest GL code based on description
            if gl_code_mapping:
                suggested_gl = self._suggest_gl_code(
                    item.description,
                    gl_code_mapping,
                )
                if suggested_gl:
                    item_dict["gl_code"] = suggested_gl
                    item_dict["gl_code_source"] = "auto_suggested"
            
            enriched.append(item_dict)
        
        return enriched
    
    def _suggest_gl_code(self, description: str, gl_mapping: dict) -> Optional[str]:
        """
        Suggest GL code based on line item description.
        
        Args:
            description: Line item description
            gl_mapping: Dictionary mapping keywords to GL codes
            
        Returns:
            Suggested GL code or None
        """
        description_lower = description.lower()
        
        for keyword, gl_code in gl_mapping.items():
            if keyword.lower() in description_lower:
                return gl_code
        
        return None
