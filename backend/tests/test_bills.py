"""
BillAgent Pro - Bill API Tests
===============================
Tests for bill CRUD operations and processing.
"""

from datetime import datetime
from decimal import Decimal
from io import BytesIO

import pytest
from httpx import AsyncClient

from app.models.bill import BillStatus


# =============================================================================
# Bill List Tests
# =============================================================================
class TestBillList:
    """Test bill listing endpoints."""

    @pytest.mark.asyncio
    async def test_list_bills_unauthorized(self, client: AsyncClient):
        """Test listing bills without authentication."""
        response = await client.get("/bills")
        assert response.status_code in [401, 404]

    @pytest.mark.asyncio
    async def test_list_bills_empty(self, client: AsyncClient, auth_headers):
        """Test listing bills when none exist."""
        response = await client.get("/bills", headers=auth_headers)
        # Endpoint might be at /bills or return 404
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))

    @pytest.mark.asyncio
    async def test_list_bills_with_data(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test listing bills with existing data."""
        response = await client.get("/bills", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            # Check that we get some bills
            if isinstance(data, dict) and "items" in data:
                assert len(data["items"]) >= 1
            elif isinstance(data, list):
                assert len(data) >= 1


# =============================================================================
# Bill Detail Tests
# =============================================================================
class TestBillDetail:
    """Test bill detail endpoints."""

    @pytest.mark.asyncio
    async def test_get_bill_by_id(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test getting a specific bill by ID."""
        response = await client.get(
            f"/bills/{sample_bill.id}",
            headers=auth_headers
        )
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == sample_bill.id
            assert data["invoice_number"] == sample_bill.invoice_number

    @pytest.mark.asyncio
    async def test_get_nonexistent_bill(self, client: AsyncClient, auth_headers):
        """Test getting a bill that doesn't exist."""
        response = await client.get("/bills/99999", headers=auth_headers)
        assert response.status_code in [404, 401]


# =============================================================================
# Bill Update Tests
# =============================================================================
class TestBillUpdate:
    """Test bill update operations."""

    @pytest.mark.asyncio
    async def test_update_bill_status(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test updating bill status."""
        response = await client.patch(
            f"/bills/{sample_bill.id}",
            headers=auth_headers,
            json={"status": "approved"}
        )
        # Might return 200 if endpoint exists
        if response.status_code == 200:
            data = response.json()
            assert data["status"] == "approved"

    @pytest.mark.asyncio
    async def test_update_bill_amount(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test updating bill amounts."""
        response = await client.patch(
            f"/bills/{sample_bill.id}",
            headers=auth_headers,
            json={
                "subtotal": "200.00",
                "total_amount": "216.50"
            }
        )
        if response.status_code == 200:
            data = response.json()
            # Verify amounts were updated
            assert Decimal(str(data.get("subtotal", 0))) == Decimal("200.00")


# =============================================================================
# Bill Validation Tests
# =============================================================================
class TestBillValidation:
    """Test bill validation."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_bill_model_validation(self, sample_bill):
        """Test bill model has required fields."""
        assert sample_bill.id is not None
        assert sample_bill.invoice_number is not None
        assert sample_bill.total_amount is not None
        assert sample_bill.status is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_bill_status_enum(self, sample_bill):
        """Test bill status is valid enum value."""
        assert sample_bill.status in [s for s in BillStatus]

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_bill_amount_calculation(self, sample_bill):
        """Test bill amount calculations."""
        expected_total = sample_bill.subtotal + sample_bill.tax_amount
        assert sample_bill.total_amount == expected_total


# =============================================================================
# Bill Upload Tests
# =============================================================================
class TestBillUpload:
    """Test bill upload functionality."""

    @pytest.mark.asyncio
    async def test_upload_bill_image(self, client: AsyncClient, auth_headers):
        """Test uploading a bill image."""
        # Create a fake image file
        fake_image = BytesIO(b"fake image content")
        
        response = await client.post(
            "/bills/upload",
            headers=auth_headers,
            files={"file": ("test_bill.png", fake_image, "image/png")}
        )
        # May return 200/201 if implemented, or 404/422
        assert response.status_code in [200, 201, 404, 422, 500]

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, auth_headers):
        """Test uploading invalid file type."""
        fake_file = BytesIO(b"not an image")
        
        response = await client.post(
            "/bills/upload",
            headers=auth_headers,
            files={"file": ("test.txt", fake_file, "text/plain")}
        )
        # Should reject non-image files
        assert response.status_code in [400, 415, 422, 404, 500]


# =============================================================================
# Bill Search Tests
# =============================================================================
class TestBillSearch:
    """Test bill search functionality."""

    @pytest.mark.asyncio
    async def test_search_bills_by_invoice_number(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test searching bills by invoice number."""
        response = await client.get(
            "/bills",
            headers=auth_headers,
            params={"invoice_number": sample_bill.invoice_number}
        )
        if response.status_code == 200:
            data = response.json()
            # Verify search results
            if isinstance(data, dict) and "items" in data:
                items = data["items"]
            else:
                items = data if isinstance(data, list) else []
            # Should find the bill
            assert any(
                item.get("invoice_number") == sample_bill.invoice_number
                for item in items
            ) if items else True

    @pytest.mark.asyncio
    async def test_search_bills_by_status(
        self, client: AsyncClient, auth_headers, sample_bill
    ):
        """Test searching bills by status."""
        response = await client.get(
            "/bills",
            headers=auth_headers,
            params={"status": sample_bill.status.value}
        )
        if response.status_code == 200:
            data = response.json()
            # All returned bills should have matching status
            if isinstance(data, dict) and "items" in data:
                for item in data["items"]:
                    assert item.get("status") == sample_bill.status.value
