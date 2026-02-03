"""
BillAgent Pro - Authentication API
===================================
Authentication endpoints for login, refresh, and logout.
"""

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ...database import get_db
from ...models.user import User, UserRole
from ...schemas.auth_schema import (
    LoginRequest, LoginResponse, Token, TokenRefresh,
    UserRead, PasswordChange
)
from ...services.auth_service import (
    AuthService, verify_token, create_token_pair
)


router = APIRouter(prefix="/auth", tags=["Authentication"])

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_v1_prefix}/auth/login")


# =============================================================================
# Dependency: Get Current User
# =============================================================================

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Raises:
        HTTPException 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = verify_token(token, token_type="access")
    if payload is None:
        raise credentials_exception
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(uuid.UUID(payload.sub))
    
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """Dependency to ensure user is active."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


# =============================================================================
# Authentication Endpoints
# =============================================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="User Login",
    description="Authenticate user and return JWT tokens"
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: AsyncSession = Depends(get_db)
):
    """
    OAuth2 compatible token login.
    
    - **username**: User's email address
    - **password**: User's password
    
    Returns access token, refresh token, and user info.
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(
        email=form_data.username,
        password=form_data.password
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = create_token_pair(user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user)
    )


@router.post(
    "/login/json",
    response_model=LoginResponse,
    summary="JSON User Login",
    description="Authenticate user with JSON body and return JWT tokens"
)
async def login_json(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    JSON body login endpoint for frontend applications.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns access token, refresh token, and user info.
    """
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(
        email=login_data.email,
        password=login_data.password
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = create_token_pair(user)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserRead.model_validate(user)
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh Access Token",
    description="Get new access token using refresh token"
)
async def refresh_token(
    token_data: TokenRefresh,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using a valid refresh token.
    
    - **refresh_token**: Valid refresh token
    
    Returns new access and refresh tokens.
    """
    auth_service = AuthService(db)
    tokens = await auth_service.refresh_tokens(token_data.refresh_token)
    
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token, refresh_token = tokens
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60
    )


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get Current User",
    description="Get information about the currently authenticated user"
)
async def get_me(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Get current authenticated user's profile.
    
    Requires valid access token in Authorization header.
    """
    return UserRead.model_validate(current_user)


@router.post(
    "/change-password",
    summary="Change Password",
    description="Change the current user's password"
)
async def change_password(
    password_data: PasswordChange,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db)
):
    """
    Change the current user's password.
    
    - **current_password**: Current password for verification
    - **new_password**: New password (min 8 characters)
    """
    auth_service = AuthService(db)
    success = await auth_service.update_password(
        user=current_user,
        current_password=password_data.current_password,
        new_password=password_data.new_password
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    return {"message": "Password updated successfully"}


@router.post(
    "/logout",
    summary="Logout",
    description="Logout the current user (client should discard tokens)"
)
async def logout(
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    """
    Logout endpoint.
    
    Note: Since we use stateless JWT tokens, the client should discard
    the tokens on their end. For enhanced security, consider implementing
    a token blacklist using Redis.
    """
    return {"message": "Successfully logged out"}
