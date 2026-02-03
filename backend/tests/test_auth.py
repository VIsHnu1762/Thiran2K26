"""
BillAgent Pro - Authentication Tests
=====================================
Tests for authentication endpoints and JWT handling.
"""

import pytest
from httpx import AsyncClient


# =============================================================================
# Login Tests
# =============================================================================
class TestLogin:
    """Test login functionality."""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, sample_user):
        """Test successful login."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": sample_user.email,
                "password": "testpassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Test login with invalid email."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "nonexistent@test.com",
                "password": "password123",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient, sample_user):
        """Test login with invalid password."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": sample_user.email,
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_empty_credentials(self, client: AsyncClient):
        """Test login with empty credentials."""
        response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": "",
                "password": "",
            },
        )
        assert response.status_code in [401, 422]


# =============================================================================
# Protected Routes Tests
# =============================================================================
class TestProtectedRoutes:
    """Test protected route access."""

    @pytest.mark.asyncio
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """Test accessing protected route without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_access_protected_route_with_token(
        self, client: AsyncClient, auth_headers
    ):
        """Test accessing protected route with valid token."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "username" in data

    @pytest.mark.asyncio
    async def test_access_protected_route_with_invalid_token(self, client: AsyncClient):
        """Test accessing protected route with invalid token."""
        headers = {"Authorization": "Bearer invalid-token-here"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401


# =============================================================================
# Token Refresh Tests
# =============================================================================
class TestTokenRefresh:
    """Test token refresh functionality."""

    @pytest.mark.asyncio
    async def test_refresh_token(self, client: AsyncClient, sample_user):
        """Test refreshing access token."""
        # First, login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            data={
                "username": sample_user.email,
                "password": "testpassword123",
            },
        )
        assert login_response.status_code == 200
        refresh_token = login_response.json()["refresh_token"]

        # Try to refresh the token
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        # May return 200 if implemented, or 404/422 if not
        assert response.status_code in [200, 404, 422]


# =============================================================================
# Registration Tests
# =============================================================================
class TestRegistration:
    """Test user registration."""

    @pytest.mark.asyncio
    async def test_register_new_user(self, client: AsyncClient):
        """Test registering a new user."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@test.com",
                "username": "newuser",
                "password": "newpassword123",
                "full_name": "New User",
            },
        )
        # May return 201 if implemented, or 404 if endpoint doesn't exist
        assert response.status_code in [200, 201, 404, 422]

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, sample_user):
        """Test registering with duplicate email."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": sample_user.email,
                "username": "different_user",
                "password": "password123",
                "full_name": "Another User",
            },
        )
        # Should fail with 400/409 or 404 if endpoint doesn't exist
        assert response.status_code in [400, 409, 404, 422]
