# Phase 6: Authentication & Security

## Overview

This phase implements comprehensive authentication, role-based access control (RBAC), and security hardening for BillAgent Pro.

## Features Implemented

### 6.1 Authentication Backend

#### User Model (`backend/app/models/user.py`)
- UUID primary key
- Email (unique) with password hash
- Role-based access (viewer, accountant, approver, admin)
- Account status tracking (is_active, is_superuser)
- Timestamps (created_at, updated_at, last_login)

#### Auth Schemas (`backend/app/schemas/auth_schema.py`)
- `LoginRequest` / `LoginResponse` - Login flow
- `Token` / `TokenRefresh` - JWT token management
- `UserCreate` / `UserUpdate` / `UserRead` - User CRUD
- `PasswordChange` / `PasswordReset` - Password management

#### Auth Service (`backend/app/services/auth_service.py`)
- Password hashing with bcrypt
- JWT access token generation (configurable expiry)
- JWT refresh token generation (7-day default)
- Token verification and decoding
- User authentication workflow

#### Auth API Endpoints (`backend/app/api/v1/auth.py`)
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | OAuth2 compatible login (form data) |
| `/api/v1/auth/login/json` | POST | JSON login for frontend |
| `/api/v1/auth/refresh` | POST | Refresh access token |
| `/api/v1/auth/me` | GET | Get current user profile |
| `/api/v1/auth/change-password` | POST | Change user password |
| `/api/v1/auth/logout` | POST | Logout (client-side token discard) |

### 6.2 Role-Based Access Control

#### Roles (`backend/app/models/user.py`)
| Role | Description |
|------|-------------|
| `viewer` | Read-only access to bills and reports |
| `accountant` | Can process, edit bills and manage vendors |
| `approver` | Can approve/post bills + all accountant permissions |
| `admin` | Full system access including user management |

#### Permissions (`backend/app/api/v1/permissions.py`)
```python
# Available permissions
BILL_VIEW, BILL_CREATE, BILL_EDIT, BILL_DELETE, BILL_APPROVE, BILL_POST
VENDOR_VIEW, VENDOR_CREATE, VENDOR_EDIT, VENDOR_DELETE
GL_VIEW, GL_CREATE, GL_EDIT, GL_DELETE
USER_VIEW, USER_CREATE, USER_EDIT, USER_DELETE
ANALYTICS_VIEW, ANALYTICS_EXPORT
SYSTEM_CONFIG, SYSTEM_AUDIT
```

#### Permission Decorators
```python
from backend.app.api.v1.permissions import require_permission, require_role, Permission

# Require specific permission
@router.get("/bills")
async def list_bills(user: User = Depends(require_permission(Permission.BILL_VIEW))):
    ...

# Require specific role
@router.get("/admin/users")
async def list_users(user: User = Depends(require_role(UserRole.ADMIN))):
    ...
```

### 6.3 Frontend Authentication

#### Auth Service (`services/auth.ts`)
- JWT token storage in localStorage
- Automatic token refresh before expiry
- Auth state management with subscribers
- Role-based permission checks

#### Login Component (`components/LoginNew.tsx`)
- Email/password form with validation
- Demo account quick login buttons
- Loading states and error handling
- Password visibility toggle

#### Protected Route (`components/ProtectedRoute.tsx`)
- Authentication wrapper for routes
- Role-based access control
- Access denied screen with user feedback
- Loading states during auth check

#### Auth Context (`components/AuthContext.tsx`)
- React context for auth state
- Hooks: `useAuthContext`, `usePermission`
- HOC: `withAuth` for component protection

### 6.4 Security Hardening

#### Rate Limiting (`backend/app/middleware/security.py`)
- Token bucket algorithm (100 req/min default)
- Per-client limiting (by IP or JWT token)
- Rate limit headers in responses
- Configurable burst size

#### Security Headers
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Permissions-Policy` (restrict browser features)
- `Content-Security-Policy` (production only)
- `Strict-Transport-Security` (production only)

#### Request Validation
- Content length validation (10MB max)
- Malicious user-agent blocking
- Request ID tracking for tracing

#### Error Monitoring
- Sentry integration (optional)
- Transaction tracing
- SQLAlchemy integration

## Database Migration

Run the migration to create the users table:

```bash
cd backend
alembic upgrade head
```

## Seeding Demo Users

```bash
cd backend
python -m app.scripts.seed_db
```

### Demo Credentials
| Role | Email | Password |
|------|-------|----------|
| Admin | admin@billagent.pro | admin123456 |
| Approver | approver@billagent.pro | approver123456 |
| Accountant | accountant@billagent.pro | account123456 |
| Viewer | viewer@billagent.pro | viewer123456 |

## Environment Variables

Add these to your `.env` file:

```env
# Security
SECRET_KEY=your-secure-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST_SIZE=20

# Error Monitoring (optional)
SENTRY_DSN=your-sentry-dsn
```

## Python Dependencies

Add to `requirements.txt`:

```
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0
sentry-sdk[fastapi]>=1.40.0
```

## Usage Examples

### Backend: Protecting an Endpoint

```python
from backend.app.api.v1.auth import get_current_active_user
from backend.app.api.v1.permissions import require_permission, Permission

@router.post("/bills/{bill_id}/approve")
async def approve_bill(
    bill_id: uuid.UUID,
    user: User = Depends(require_permission(Permission.BILL_APPROVE)),
    db: AsyncSession = Depends(get_db)
):
    # Only users with BILL_APPROVE permission can access
    ...
```

### Frontend: Protected Page

```tsx
import { ProtectedRoute } from './components/ProtectedRoute';
import { UserRole } from './services/auth';

// In your router or App.tsx
<ProtectedRoute requiredRoles={[UserRole.ADMIN, UserRole.APPROVER]}>
    <ApprovalPage />
</ProtectedRoute>
```

### Frontend: Check Permission in Component

```tsx
import { useAuthContext } from './components/AuthContext';
import { UserRole } from './services/auth';

function BillActions({ billId }) {
    const { hasRole, canAccess } = useAuthContext();
    
    return (
        <div>
            {canAccess([UserRole.ACCOUNTANT, UserRole.APPROVER, UserRole.ADMIN]) && (
                <button onClick={() => editBill(billId)}>Edit</button>
            )}
            {hasRole(UserRole.APPROVER) && (
                <button onClick={() => approveBill(billId)}>Approve</button>
            )}
        </div>
    );
}
```

## API Response Headers

All API responses include:
- `X-Request-ID` - Unique request identifier
- `X-RateLimit-Limit` - Max requests per period
- `X-RateLimit-Remaining` - Remaining requests
- `X-RateLimit-Reset` - Reset timestamp

## Testing

### Test Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@billagent.pro", "password": "admin123456"}'
```

### Test Protected Endpoint
```bash
curl -X GET http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Files Created/Modified

### New Files
- `backend/app/models/user.py` - User model
- `backend/app/schemas/auth_schema.py` - Auth schemas
- `backend/app/services/auth_service.py` - Auth service
- `backend/app/api/__init__.py` - API module
- `backend/app/api/v1/__init__.py` - v1 API module
- `backend/app/api/v1/auth.py` - Auth endpoints
- `backend/app/api/v1/users.py` - User management endpoints
- `backend/app/api/v1/permissions.py` - RBAC permissions
- `backend/app/middleware/__init__.py` - Middleware module
- `backend/app/middleware/security.py` - Security middleware
- `backend/alembic/versions/002_add_users_table.py` - Migration
- `services/auth.ts` - Frontend auth service
- `components/LoginNew.tsx` - Updated login component
- `components/ProtectedRoute.tsx` - Route protection
- `components/AuthContext.tsx` - Auth React context

### Modified Files
- `backend/app/models/__init__.py` - Export User model
- `backend/app/schemas/__init__.py` - Export auth schemas
- `backend/app/config.py` - Security settings
- `backend/app/main.py` - Auth routes & middleware
- `backend/app/scripts/seed_db.py` - Demo user seeding
- `backend/.env.example` - Environment template
- `services/api.ts` - Auth header integration
- `types.ts` - User types
