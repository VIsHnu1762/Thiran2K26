"""
BillAgent Pro - OCR Service Tests
==================================
Unit tests for the new OCR service architecture.
"""

import asyncio
import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import json

# Import the modules we're testing
from backend.app.services.ocr.base import (
    OCREngine,
    OCREngineType,
    OCRResult,
    OCRField,
    OCRLineItem,
    BoundingBox,
)
from backend.app.services.ocr.mistral_ocr import MistralOCR
from backend.app.services.ocr.gpt4_vision import GPT4VisionOCR
from backend.app.services.ocr.ocr_parser import OCRParser


class TestBoundingBox:
    """Tests for BoundingBox dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.8, y2=0.9)
        result = bbox.to_dict()
        
        assert result == {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
    
    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.9}
        bbox = BoundingBox.from_dict(data)
        
        assert bbox.x1 == 0.1
        assert bbox.y1 == 0.2
        assert bbox.x2 == 0.8
        assert bbox.y2 == 0.9
    
    def test_from_polygon(self):
        """Test creation from polygon coordinates."""
        # Polygon: [[10, 20], [100, 20], [100, 50], [10, 50]]
        polygon = [[10, 20], [100, 20], [100, 50], [10, 50]]
        bbox = BoundingBox.from_polygon(polygon, image_width=200, image_height=100)
        
        assert bbox.x1 == 0.05  # 10/200
        assert bbox.y1 == 0.2   # 20/100
        assert bbox.x2 == 0.5   # 100/200
        assert bbox.y2 == 0.5   # 50/100
    
    def test_to_absolute(self):
        """Test conversion to absolute pixel coordinates."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.5, y2=0.5)
        result = bbox.to_absolute(image_width=200, image_height=100)
        
        assert result == {"x1": 20, "y1": 20, "x2": 100, "y2": 50}


class TestOCRField:
    """Tests for OCRField dataclass."""
    
    def test_to_dict(self):
        """Test conversion to dictionary."""
        field = OCRField(
            name="vendor_name",
            value="Test Vendor",
            confidence=0.95,
            raw_text="TEST VENDOR",
        )
        result = field.to_dict()
        
        assert result["name"] == "vendor_name"
        assert result["value"] == "Test Vendor"
        assert result["confidence"] == 0.95
        assert result["raw_text"] == "TEST VENDOR"
        assert result["bounding_box"] is None
    
    def test_to_dict_with_bbox(self):
        """Test conversion with bounding box."""
        bbox = BoundingBox(x1=0.1, y1=0.2, x2=0.8, y2=0.3)
        field = OCRField(
            name="total_amount",
            value=Decimal("100.50"),
            confidence=0.9,
            bounding_box=bbox,
        )
        result = field.to_dict()
        
        assert result["value"] == "100.50"  # Decimal converted to string
        assert result["bounding_box"] == {"x1": 0.1, "y1": 0.2, "x2": 0.8, "y2": 0.3}


class TestOCRResult:
    """Tests for OCRResult dataclass."""
    
    def test_empty_result(self):
        """Test default empty result."""
        result = OCRResult()
        
        assert result.success is False
        assert result.line_items == []
        assert result.overall_confidence == 0.0
    
    def test_get_field_confidence(self):
        """Test field confidence extraction."""
        result = OCRResult(
            success=True,
            vendor_name=OCRField("vendor_name", "Test", 0.95),
            invoice_number=OCRField("invoice_number", "INV-001", 0.9),
            total_amount=OCRField("total_amount", Decimal("100"), 0.85),
        )
        
        confidence = result.get_field_confidence()
        
        assert confidence["vendor_name"] == 0.95
        assert confidence["invoice_number"] == 0.9
        assert confidence["total_amount"] == 0.85
    
    def test_calculate_overall_confidence(self):
        """Test weighted confidence calculation."""
        result = OCRResult(
            success=True,
            vendor_name=OCRField("vendor_name", "Test", 0.9),
            invoice_number=OCRField("invoice_number", "INV-001", 0.85),
            total_amount=OCRField("total_amount", Decimal("100"), 0.95),
            line_items=[
                OCRLineItem(
                    description="Item 1",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50"),
                    total_price=Decimal("50"),
                    confidence=0.88,
                ),
                OCRLineItem(
                    description="Item 2",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50"),
                    total_price=Decimal("50"),
                    confidence=0.92,
                ),
            ],
        )
        
        confidence = result.calculate_overall_confidence()
        
        assert 0.85 <= confidence <= 0.95  # Should be weighted average


class TestOCRParser:
    """Tests for OCRParser."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.parser = OCRParser()
    
    def test_to_bill_create_data(self):
        """Test conversion to bill create data."""
        ocr_result = OCRResult(
            success=True,
            vendor_name=OCRField("vendor_name", "Test Vendor", 0.95),
            invoice_number=OCRField("invoice_number", "INV-001", 0.9),
            total_amount=OCRField("total_amount", Decimal("150.00"), 0.95),
            line_items=[
                OCRLineItem(
                    description="Widget A",
                    quantity=Decimal("2"),
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("100.00"),
                    confidence=0.9,
                ),
                OCRLineItem(
                    description="Widget B",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("50.00"),
                    confidence=0.85,
                ),
            ],
        )
        
        data = self.parser.to_bill_create_data(ocr_result, "/uploads/test.jpg")
        
        assert data["vendor_name"] == "Test Vendor"
        assert data["invoice_number"] == "INV-001"
        assert data["total_amount"] == Decimal("150.00")
        assert data["image_url"] == "/uploads/test.jpg"
        assert len(data["line_items"]) == 2
        assert data["line_items"][0]["description"] == "Widget A"
    
    def test_validate_extraction_success(self):
        """Test validation with valid extraction."""
        ocr_result = OCRResult(
            success=True,
            total_amount=OCRField("total_amount", Decimal("100.00"), 0.95),
            line_items=[
                OCRLineItem(
                    description="Item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("100.00"),
                    confidence=0.9,
                ),
            ],
            overall_confidence=0.9,
        )
        
        is_valid, errors = self.parser.validate_extraction(ocr_result)
        
        # Should pass validation (may have warnings but no errors)
        assert is_valid
    
    def test_validate_extraction_missing_total(self):
        """Test validation fails without total."""
        ocr_result = OCRResult(
            success=True,
            line_items=[
                OCRLineItem(
                    description="Item",
                    quantity=Decimal("1"),
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("50.00"),
                    confidence=0.9,
                ),
            ],
        )
        
        is_valid, errors = self.parser.validate_extraction(ocr_result)
        
        assert not is_valid
        assert any(e["field"] == "total_amount" for e in errors)
    
    def test_validate_extraction_math_mismatch(self):
        """Test validation catches math errors."""
        ocr_result = OCRResult(
            success=True,
            total_amount=OCRField("total_amount", Decimal("200.00"), 0.95),  # Wrong!
            line_items=[
                OCRLineItem(
                    description="Item",
                    quantity=Decimal("2"),
                    unit_price=Decimal("50.00"),
                    total_price=Decimal("100.00"),  # Actual: 100.00
                    confidence=0.9,
                ),
            ],
            overall_confidence=0.9,
        )
        
        is_valid, errors = self.parser.validate_extraction(ocr_result)
        
        # Should have warning about math mismatch
        assert any("Math mismatch" in e.get("message", "") for e in errors)
    
    def test_determine_status_success(self):
        """Test status determination for good extraction."""
        ocr_result = OCRResult(success=True, overall_confidence=0.9)
        
        status = self.parser.determine_status(ocr_result, [])
        
        assert status == "PROCESSING"
    
    def test_determine_status_low_confidence(self):
        """Test status for low confidence."""
        ocr_result = OCRResult(success=True, overall_confidence=0.65)
        
        status = self.parser.determine_status(ocr_result, [])
        
        assert status == "NEEDS_REVIEW"
    
    def test_determine_status_failed(self):
        """Test status for failed extraction."""
        ocr_result = OCRResult(success=False, error_message="API error")
        
        status = self.parser.determine_status(ocr_result, [])
        
        assert status == "FAILED"
    
    def test_normalize_vendor_name(self):
        """Test vendor name normalization."""
        test_cases = [
            ("  ACME Corp Pvt Ltd  ", "Acme Corp"),
            ("Test Company Private Limited", "Test Company"),
            ("Vendor LLC", "Vendor"),
            ("simple name", "Simple Name"),
        ]
        
        for input_name, expected in test_cases:
            result = self.parser._normalize_vendor_name(input_name)
            assert result == expected, f"Failed for '{input_name}'"


class TestMistralOCR:
    """Tests for MistralOCR engine."""
    
    @pytest.fixture
    def mock_response(self):
        """Sample successful API response."""
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "vendor": {"name": "Test Store", "confidence": 0.95},
                        "invoice_number": {"value": "INV-001", "confidence": 0.9},
                        "total_amount": {"value": 150.00, "confidence": 0.95},
                        "line_items": [
                            {
                                "description": "Product A",
                                "quantity": 2,
                                "unit_price": 50.00,
                                "total_price": 100.00,
                                "confidence": 0.9,
                            },
                            {
                                "description": "Product B",
                                "quantity": 1,
                                "unit_price": 50.00,
                                "total_price": 50.00,
                                "confidence": 0.85,
                            },
                        ],
                    })
                }
            }]
        }
    
    def test_engine_properties(self):
        """Test engine property values."""
        ocr = MistralOCR(api_key="test-key")
        
        assert ocr.engine_type == OCREngineType.MISTRAL
        assert ocr.supports_bounding_boxes is True
        assert ocr.supports_handwritten is True
    
    @pytest.mark.asyncio
    async def test_parse_response(self, mock_response):
        """Test response parsing."""
        ocr = MistralOCR(api_key="test-key")
        
        result = ocr._parse_response(mock_response, image_width=800, image_height=600)
        
        assert result.success is True
        assert result.vendor_name.value == "Test Store"
        assert result.invoice_number.value == "INV-001"
        assert len(result.line_items) == 2
        assert result.line_items[0].description == "Product A"
    
    def test_parse_date(self):
        """Test date parsing from various formats."""
        ocr = MistralOCR(api_key="test-key")
        
        test_cases = [
            ("2024-01-15", "2024-01-15"),
            ("15-01-2024", "2024-01-15"),
            ("15/01/2024", "2024-01-15"),
            ("01/15/2024", "2024-01-15"),
            ("15 Jan 2024", "2024-01-15"),
        ]
        
        from datetime import date
        for input_str, expected_str in test_cases:
            result = ocr._parse_date(input_str)
            expected = date.fromisoformat(expected_str)
            assert result == expected, f"Failed for '{input_str}'"
    
    def test_parse_decimal(self):
        """Test decimal parsing from various formats."""
        ocr = MistralOCR(api_key="test-key")
        
        test_cases = [
            ("100.50", Decimal("100.50")),
            ("1,000.50", Decimal("1000.50")),
            ("₹500", Decimal("500")),
            ("Rs 250.00", Decimal("250.00")),
            (100, Decimal("100")),
            (100.5, Decimal("100.5")),
        ]
        
        for input_val, expected in test_cases:
            result = ocr._parse_decimal(input_val)
            assert result == expected, f"Failed for '{input_val}'"
    
    def test_detect_image_type(self):
        """Test image type detection."""
        ocr = MistralOCR(api_key="test-key")
        
        # PNG magic bytes
        png_bytes = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
        assert ocr._detect_image_type(png_bytes) == "image/png"
        
        # JPEG magic bytes
        jpeg_bytes = b'\xff\xd8' + b'\x00' * 100
        assert ocr._detect_image_type(jpeg_bytes) == "image/jpeg"


class TestGPT4VisionOCR:
    """Tests for GPT4VisionOCR engine."""
    
    def test_engine_properties(self):
        """Test engine property values."""
        ocr = GPT4VisionOCR(api_key="test-key")
        
        assert ocr.engine_type == OCREngineType.GPT4_VISION
        assert ocr.supports_bounding_boxes is False  # GPT-4 doesn't return bbox
        assert ocr.supports_handwritten is True


# =============================================================================
# Run tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
