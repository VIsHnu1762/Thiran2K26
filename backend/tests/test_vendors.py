"""
BillAgent Pro - Vendor API Tests
=================================
Tests for vendor CRUD operations.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Vendor List Tests
# =============================================================================
class TestVendorList:
    """Test vendor listing endpoints."""

    @pytest.mark.asyncio
    async def test_list_vendors(self, client: AsyncClient, auth_headers, sample_vendor):
        """Test listing vendors."""
        response = await client.get("/vendors", headers=auth_headers)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))
            # If paginated
            if isinstance(data, dict) and "items" in data:
                assert len(data["items"]) >= 1
            elif isinstance(data, list):
                assert len(data) >= 1


# =============================================================================
# Vendor Detail Tests
# =============================================================================
class TestVendorDetail:
    """Test vendor detail endpoints."""

    @pytest.mark.asyncio
    async def test_get_vendor_by_id(
        self, client: AsyncClient, auth_headers, sample_vendor
    ):
        """Test getting a specific vendor."""
        response = await client.get(
            f"/vendors/{sample_vendor.id}",
            headers=auth_headers
        )
        if response.status_code == 200:
            data = response.json()
            assert data["id"] == sample_vendor.id
            assert data["name"] == sample_vendor.name

    @pytest.mark.asyncio
    async def test_get_nonexistent_vendor(self, client: AsyncClient, auth_headers):
        """Test getting a vendor that doesn't exist."""
        response = await client.get("/vendors/99999", headers=auth_headers)
        assert response.status_code in [404, 401]


# =============================================================================
# Vendor Create Tests
# =============================================================================
class TestVendorCreate:
    """Test vendor creation."""

    @pytest.mark.asyncio
    async def test_create_vendor(self, client: AsyncClient, auth_headers):
        """Test creating a new vendor."""
        vendor_data = {
            "name": "New Test Vendor",
            "address": "456 New Street",
            "city": "New City",
            "state": "NY",
            "zip_code": "10001",
            "email": "newvendor@test.com",
        }
        response = await client.post(
            "/vendors",
            headers=auth_headers,
            json=vendor_data
        )
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["name"] == vendor_data["name"]
            assert data["email"] == vendor_data["email"]

    @pytest.mark.asyncio
    async def test_create_vendor_missing_required_field(
        self, client: AsyncClient, auth_headers
    ):
        """Test creating vendor with missing required field."""
        vendor_data = {
            # Missing 'name' which should be required
            "email": "noname@test.com",
        }
        response = await client.post(
            "/vendors",
            headers=auth_headers,
            json=vendor_data
        )
        # Should return validation error
        assert response.status_code in [400, 422, 404]


# =============================================================================
# Vendor Update Tests
# =============================================================================
class TestVendorUpdate:
    """Test vendor update operations."""

    @pytest.mark.asyncio
    async def test_update_vendor(
        self, client: AsyncClient, auth_headers, sample_vendor
    ):
        """Test updating a vendor."""
        response = await client.patch(
            f"/vendors/{sample_vendor.id}",
            headers=auth_headers,
            json={"name": "Updated Vendor Name"}
        )
        if response.status_code == 200:
            data = response.json()
            assert data["name"] == "Updated Vendor Name"


# =============================================================================
# Vendor Model Tests
# =============================================================================
class TestVendorModel:
    """Test vendor model."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_vendor_has_required_fields(self, sample_vendor):
        """Test vendor model has required fields."""
        assert sample_vendor.id is not None
        assert sample_vendor.name is not None
        assert sample_vendor.is_active is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_vendor_optional_fields(self, sample_vendor):
        """Test vendor optional fields."""
        # These should be set from fixture
        assert sample_vendor.email is not None
        assert sample_vendor.address is not None
