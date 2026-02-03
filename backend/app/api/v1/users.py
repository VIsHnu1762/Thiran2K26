"""
BillAgent Pro - Users API
==========================
User management endpoints (admin only).
"""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...database import get_db
from ...models.user import User, UserRole
from ...schemas.auth_schema import UserCreate, UserUpdate, UserRead, UserList
from ...services.auth_service import AuthService, hash_password
from ..v1.auth import get_current_active_user
from .permissions import require_role, require_permission, Permission


router = APIRouter(prefix="/users", tags=["Users"])


# =============================================================================
# User Management Endpoints
# =============================================================================

@router.get(
    "/",
    response_model=UserList,
    summary="List Users",
    description="List all users (Admin only)"
)
async def list_users(
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0, description="Records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Max records to return"),
    role: Optional[UserRole] = Query(None, description="Filter by role")
):
    """
    List all users with pagination and optional role filter.
    
    Only accessible by Admin users.
    """
    auth_service = AuthService(db)
    users, total = await auth_service.list_users(skip=skip, limit=limit, role=role)
    
    return UserList(
        items=[UserRead.model_validate(u) for u in users],
        total=total
    )


@router.post(
    "/",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User",
    description="Create a new user (Admin only)"
)
async def create_user(
    user_data: UserCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new user account.
    
    Only accessible by Admin users.
    """
    auth_service = AuthService(db)
    
    # Check if email already exists
    existing = await auth_service.get_user_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    user = await auth_service.create_user(user_data)
    return UserRead.model_validate(user)


@router.get(
    "/{user_id}",
    response_model=UserRead,
    summary="Get User",
    description="Get user by ID (Admin only)"
)
async def get_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db)
):
    """
    Get a specific user by ID.
    
    Only accessible by Admin users.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserRead.model_validate(user)


@router.put(
    "/{user_id}",
    response_model=UserRead,
    summary="Update User",
    description="Update user by ID (Admin only)"
)
async def update_user(
    user_id: uuid.UUID,
    user_data: UserUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db)
):
    """
    Update a user's information.
    
    Only accessible by Admin users.
    """
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-demotion from admin
    if user.id == current_user.id and user_data.role and user_data.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own admin role"
        )
    
    # Update fields
    update_dict = user_data.model_dump(exclude_unset=True)
    
    if "password" in update_dict:
        update_dict["hashed_password"] = hash_password(update_dict.pop("password"))
    
    for field, value in update_dict.items():
        setattr(user, field, value)
    
    await db.commit()
    await db.refresh(user)
    
    return UserRead.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete User",
    description="Delete (deactivate) user by ID (Admin only)"
)
async def delete_user(
    user_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_role(UserRole.ADMIN))],
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivate a user account.
    
    Only accessible by Admin users. Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    auth_service = AuthService(db)
    user = await auth_service.get_user_by_id(user_id)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Soft delete - just deactivate
    user.is_active = False
    await db.commit()
    
    return None
