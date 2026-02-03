"""
BillAgent Pro - Authentication Schemas
=======================================
Pydantic schemas for authentication and authorization.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr

from ..models.user import UserRole


# =============================================================================
# Token Schemas
# =============================================================================

class Token(BaseModel):
    """JWT token response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")


class TokenPayload(BaseModel):
    """JWT token payload schema (internal use)."""
    sub: str = Field(..., description="Subject (user ID)")
    email: str = Field(..., description="User email")
    role: UserRole = Field(..., description="User role")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")
    type: str = Field(..., description="Token type (access/refresh)")


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str = Field(..., description="Refresh token")


# =============================================================================
# Login Schemas
# =============================================================================

class LoginRequest(BaseModel):
    """Schema for login request."""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="User password")


class LoginResponse(BaseModel):
    """Schema for login response with user info."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user: "UserRead" = Field(..., description="User information")


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema with common fields."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    role: UserRole = Field(default=UserRole.VIEWER, description="User role")
    is_active: bool = Field(default=True, description="Account active status")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, max_length=100, description="Password")


class UserUpdate(BaseModel):
    """Schema for updating a user (all fields optional)."""
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="Full name")
    role: Optional[UserRole] = Field(None, description="User role")
    is_active: Optional[bool] = Field(None, description="Account active status")
    password: Optional[str] = Field(None, min_length=8, max_length=100, description="New password")


class UserRead(UserBase):
    """Schema for reading user data."""
    id: UUID = Field(..., description="User ID")
    is_superuser: bool = Field(..., description="Superuser status")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    last_login: Optional[datetime] = Field(None, description="Last login timestamp")
    
    model_config = {"from_attributes": True}


class UserList(BaseModel):
    """Schema for listing users."""
    items: list[UserRead] = Field(..., description="List of users")
    total: int = Field(..., ge=0, description="Total count")
    
    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    """Brief user info for embedding in other schemas."""
    id: UUID = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    full_name: Optional[str] = Field(None, description="Full name")
    role: UserRole = Field(..., description="User role")
    
    model_config = {"from_attributes": True}


# =============================================================================
# Password Schemas
# =============================================================================

class PasswordChange(BaseModel):
    """Schema for password change request."""
    current_password: str = Field(..., min_length=6, description="Current password")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


class PasswordReset(BaseModel):
    """Schema for password reset request."""
    token: str = Field(..., description="Password reset token")
    new_password: str = Field(..., min_length=8, max_length=100, description="New password")


# Update forward references
LoginResponse.model_rebuild()
