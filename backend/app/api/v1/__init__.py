"""
BillAgent Pro - API v1 Module
==============================
Version 1 API routes.
"""

from .auth import router as auth_router, get_current_user, get_current_active_user
from .users import router as users_router
from .permissions import (
    Permission,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_role,
    has_permission,
    ROLE_PERMISSIONS
)

__all__ = [
    "auth_router",
    "users_router",
    "get_current_user",
    "get_current_active_user",
    "Permission",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_role",
    "has_permission",
    "ROLE_PERMISSIONS"
]
