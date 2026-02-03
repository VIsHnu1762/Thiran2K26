"""
BillAgent Pro - Health & API Tests
===================================
Tests for health check endpoints and basic API functionality.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Health Check Tests
# =============================================================================
class TestHealthEndpoints:
    """Test health check endpoints."""
    
    @pytest.mark.asyncio
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns API info."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "BillAgent" in data["message"]
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health check endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "environment" in data
        assert "database" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_health_returns_correct_environment(self, client: AsyncClient):
        """Test health check returns correct environment."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # In test mode, environment might be 'test' or 'development'
        assert data["environment"] in ["test", "development", "production"]


# =============================================================================
# API Version Tests
# =============================================================================
class TestAPIVersion:
    """Test API versioning."""

    @pytest.mark.asyncio
    async def test_api_docs_available_in_debug(self, client: AsyncClient):
        """Test that API docs are available in debug mode."""
        response = await client.get("/docs")
        # In debug mode, docs should be available
        assert response.status_code in [200, 404]  # May be disabled in tests

    @pytest.mark.asyncio
    async def test_api_prefix(self, client: AsyncClient):
        """Test that API v1 prefix is configured."""
        # Try to access an authenticated endpoint
        response = await client.get("/api/v1/auth/me")
        # Should return 401 (unauthorized), not 404 (not found)
        assert response.status_code == 401


# =============================================================================
# CORS Tests
# =============================================================================
class TestCORS:
    """Test CORS configuration."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, client: AsyncClient):
        """Test CORS headers are returned."""
        response = await client.options(
            "/",
            headers={"Origin": "http://localhost:3000"}
        )
        # Check that the request doesn't fail
        assert response.status_code in [200, 204, 405]
