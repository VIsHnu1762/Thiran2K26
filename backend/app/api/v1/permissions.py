"""
BillAgent Pro - RBAC Permissions
=================================
Role-Based Access Control (RBAC) implementation with permission decorators.
"""

from enum import Enum
from functools import wraps
from typing import Annotated, Callable, List, Union

from fastapi import Depends, HTTPException, status

from ...models.user import User, UserRole
from .auth import get_current_active_user


# =============================================================================
# Permission Definitions
# =============================================================================

class Permission(str, Enum):
    """Fine-grained permissions for RBAC."""
    
    # Bill permissions
    BILL_VIEW = "bill:view"
    BILL_CREATE = "bill:create"
    BILL_EDIT = "bill:edit"
    BILL_DELETE = "bill:delete"
    BILL_APPROVE = "bill:approve"
    BILL_POST = "bill:post"
    
    # Vendor permissions
    VENDOR_VIEW = "vendor:view"
    VENDOR_CREATE = "vendor:create"
    VENDOR_EDIT = "vendor:edit"
    VENDOR_DELETE = "vendor:delete"
    
    # GL Code permissions
    GL_VIEW = "gl:view"
    GL_CREATE = "gl:create"
    GL_EDIT = "gl:edit"
    GL_DELETE = "gl:delete"
    
    # User management permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_EDIT = "user:edit"
    USER_DELETE = "user:delete"
    
    # Analytics permissions
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"
    
    # System permissions
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"


# =============================================================================
# Role -> Permission Mapping
# =============================================================================

ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.VIEWER: {
        Permission.BILL_VIEW,
        Permission.VENDOR_VIEW,
        Permission.GL_VIEW,
        Permission.ANALYTICS_VIEW,
    },
    
    UserRole.ACCOUNTANT: {
        # Include all Viewer permissions
        Permission.BILL_VIEW,
        Permission.BILL_CREATE,
        Permission.BILL_EDIT,
        Permission.VENDOR_VIEW,
        Permission.VENDOR_CREATE,
        Permission.VENDOR_EDIT,
        Permission.GL_VIEW,
        Permission.GL_CREATE,
        Permission.GL_EDIT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
    },
    
    UserRole.APPROVER: {
        # Include all Accountant permissions
        Permission.BILL_VIEW,
        Permission.BILL_CREATE,
        Permission.BILL_EDIT,
        Permission.BILL_APPROVE,
        Permission.BILL_POST,
        Permission.VENDOR_VIEW,
        Permission.VENDOR_CREATE,
        Permission.VENDOR_EDIT,
        Permission.GL_VIEW,
        Permission.GL_CREATE,
        Permission.GL_EDIT,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.SYSTEM_AUDIT,
    },
    
    UserRole.ADMIN: {
        # Full access
        Permission.BILL_VIEW,
        Permission.BILL_CREATE,
        Permission.BILL_EDIT,
        Permission.BILL_DELETE,
        Permission.BILL_APPROVE,
        Permission.BILL_POST,
        Permission.VENDOR_VIEW,
        Permission.VENDOR_CREATE,
        Permission.VENDOR_EDIT,
        Permission.VENDOR_DELETE,
        Permission.GL_VIEW,
        Permission.GL_CREATE,
        Permission.GL_EDIT,
        Permission.GL_DELETE,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_EDIT,
        Permission.USER_DELETE,
        Permission.ANALYTICS_VIEW,
        Permission.ANALYTICS_EXPORT,
        Permission.SYSTEM_CONFIG,
        Permission.SYSTEM_AUDIT,
    },
}


# =============================================================================
# Permission Checking Functions
# =============================================================================

def has_permission(user: User, permission: Permission) -> bool:
    """
    Check if a user has a specific permission.
    
    Args:
        user: User to check
        permission: Permission to verify
        
    Returns:
        True if user has the permission
    """
    if user.is_superuser:
        return True
    
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return permission in user_permissions


def has_any_permission(user: User, permissions: List[Permission]) -> bool:
    """
    Check if a user has any of the specified permissions.
    
    Args:
        user: User to check
        permissions: List of permissions (OR logic)
        
    Returns:
        True if user has at least one permission
    """
    if user.is_superuser:
        return True
    
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return bool(user_permissions.intersection(set(permissions)))


def has_all_permissions(user: User, permissions: List[Permission]) -> bool:
    """
    Check if a user has all specified permissions.
    
    Args:
        user: User to check
        permissions: List of permissions (AND logic)
        
    Returns:
        True if user has all permissions
    """
    if user.is_superuser:
        return True
    
    user_permissions = ROLE_PERMISSIONS.get(user.role, set())
    return set(permissions).issubset(user_permissions)


# =============================================================================
# FastAPI Dependencies for RBAC
# =============================================================================

def require_permission(permission: Permission):
    """
    Dependency factory for requiring a specific permission.
    
    Usage:
        @router.get("/bills")
        async def list_bills(
            user: User = Depends(require_permission(Permission.BILL_VIEW))
        ):
            ...
    """
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
        return current_user
    
    return permission_checker


def require_any_permission(permissions: List[Permission]):
    """
    Dependency factory for requiring any of multiple permissions.
    
    Usage:
        @router.get("/bills")
        async def list_bills(
            user: User = Depends(require_any_permission([Permission.BILL_VIEW, Permission.BILL_EDIT]))
        ):
            ...
    """
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if not has_any_permission(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: one of {[p.value for p in permissions]} required"
            )
        return current_user
    
    return permission_checker


def require_all_permissions(permissions: List[Permission]):
    """
    Dependency factory for requiring all specified permissions.
    
    Usage:
        @router.post("/bills/approve")
        async def approve_bill(
            user: User = Depends(require_all_permissions([Permission.BILL_VIEW, Permission.BILL_APPROVE]))
        ):
            ...
    """
    async def permission_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if not has_all_permissions(current_user, permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: all of {[p.value for p in permissions]} required"
            )
        return current_user
    
    return permission_checker


def require_role(role: Union[UserRole, List[UserRole]]):
    """
    Dependency factory for requiring a specific role or roles.
    
    Usage:
        @router.get("/admin/users")
        async def list_users(
            user: User = Depends(require_role(UserRole.ADMIN))
        ):
            ...
        
        @router.get("/settings")
        async def get_settings(
            user: User = Depends(require_role([UserRole.ADMIN, UserRole.APPROVER]))
        ):
            ...
    """
    roles = [role] if isinstance(role, UserRole) else role
    
    async def role_checker(
        current_user: Annotated[User, Depends(get_current_active_user)]
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role denied: {[r.value for r in roles]} required"
            )
        return current_user
    
    return role_checker


# =============================================================================
# Utility Functions
# =============================================================================

def get_user_permissions(user: User) -> List[Permission]:
    """
    Get all permissions for a user based on their role.
    
    Args:
        user: User to get permissions for
        
    Returns:
        List of permissions the user has
    """
    if user.is_superuser:
        return list(Permission)
    
    return list(ROLE_PERMISSIONS.get(user.role, set()))


def get_role_permissions(role: UserRole) -> List[Permission]:
    """
    Get all permissions for a specific role.
    
    Args:
        role: Role to get permissions for
        
    Returns:
        List of permissions for the role
    """
    return list(ROLE_PERMISSIONS.get(role, set()))
