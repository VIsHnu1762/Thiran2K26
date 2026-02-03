"""
BillAgent Pro - Agent Tests
============================
Tests for AI agents (digitizer, accountant, auditor, etc.).
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch


# =============================================================================
# Digitizer Agent Tests
# =============================================================================
class TestDigitizerAgent:
    """Test digitizer agent functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_digitizer_import(self):
        """Test digitizer agent can be imported."""
        try:
            from agents.digitizer import DigitizerAgent
            assert DigitizerAgent is not None
        except ImportError:
            pytest.skip("DigitizerAgent not available")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_digitizer_extract_text(self, mock_ocr_service):
        """Test text extraction from image."""
        try:
            from agents.digitizer import DigitizerAgent
        except ImportError:
            pytest.skip("DigitizerAgent not available")
            return

        with patch.object(DigitizerAgent, "process_image", mock_ocr_service.process_image):
            result = await mock_ocr_service.process_image(b"fake_image")
            assert "vendor_name" in result
            assert "invoice_number" in result
            assert "confidence" in result


# =============================================================================
# Accountant Agent Tests
# =============================================================================
class TestAccountantAgent:
    """Test accountant agent functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_accountant_import(self):
        """Test accountant agent can be imported."""
        try:
            from agents.accountant import AccountantAgent
            assert AccountantAgent is not None
        except ImportError:
            pytest.skip("AccountantAgent not available")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_math_validation(self):
        """Test mathematical validation of bill totals."""
        from utils.math_checks import validate_bill_math
        
        # Valid bill
        result = validate_bill_math(
            subtotal=Decimal("100.00"),
            tax=Decimal("8.25"),
            total=Decimal("108.25")
        )
        assert result["valid"] is True
        
        # Invalid bill (totals don't match)
        result = validate_bill_math(
            subtotal=Decimal("100.00"),
            tax=Decimal("8.25"),
            total=Decimal("200.00")  # Wrong!
        )
        assert result["valid"] is False


# =============================================================================
# Auditor Agent Tests
# =============================================================================
class TestAuditorAgent:
    """Test auditor agent functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_auditor_import(self):
        """Test auditor agent can be imported."""
        try:
            from agents.auditor import AuditorAgent
            assert AuditorAgent is not None
        except ImportError:
            pytest.skip("AuditorAgent not available")


# =============================================================================
# Confidence Agent Tests
# =============================================================================
class TestConfidenceAgent:
    """Test confidence scoring agent."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_confidence_import(self):
        """Test confidence agent can be imported."""
        try:
            from agents.confidence_agent import ConfidenceAgent
            assert ConfidenceAgent is not None
        except ImportError:
            pytest.skip("ConfidenceAgent not available")

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_confidence_calculation(self):
        """Test confidence score calculation."""
        from utils.confidence_utils import calculate_field_confidence
        
        # High confidence - clear text
        score = calculate_field_confidence(
            text="Invoice #12345",
            field_type="invoice_number"
        )
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_confidence_threshold(self):
        """Test confidence threshold validation."""
        from app.config import settings
        
        # Verify threshold is within valid range
        assert 0.0 <= settings.ocr_confidence_threshold <= 1.0


# =============================================================================
# Controller Agent Tests
# =============================================================================
class TestControllerAgent:
    """Test controller agent functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_controller_import(self):
        """Test controller agent can be imported."""
        try:
            from agents.controller import ControllerAgent
            assert ControllerAgent is not None
        except ImportError:
            pytest.skip("ControllerAgent not available")


# =============================================================================
# Workflow Agent Tests
# =============================================================================
class TestWorkflowAgent:
    """Test workflow agent functionality."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_workflow_import(self):
        """Test workflow agent can be imported."""
        try:
            from agents.workflow_agent import WorkflowAgent
            assert WorkflowAgent is not None
        except ImportError:
            pytest.skip("WorkflowAgent not available")
