"""
BillAgent Pro - Authentication Service
=======================================
JWT token creation, validation, and password hashing.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.user import User, UserRole
from ..schemas.auth_schema import TokenPayload, Token, UserCreate, UserRead


# =============================================================================
# Password Hashing Configuration
# =============================================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# =============================================================================
# Password Utilities
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT Token Utilities
# =============================================================================

def create_access_token(
    user_id: str,
    email: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        user_id: User's UUID as string
        email: User's email
        role: User's role
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_refresh_token(
    user_id: str,
    email: str,
    role: UserRole,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Args:
        user_id: User's UUID as string
        email: User's email
        role: User's role
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)
    
    payload = {
        "sub": user_id,
        "email": email,
        "role": role.value,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh"
    }
    
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def create_token_pair(user: User) -> Tuple[str, str]:
    """
    Create both access and refresh tokens for a user.
    
    Args:
        user: User model instance
        
    Returns:
        Tuple of (access_token, refresh_token)
    """
    access_token = create_access_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role
    )
    refresh_token = create_refresh_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role
    )
    return access_token, refresh_token


def decode_token(token: str) -> Optional[TokenPayload]:
    """
    Decode and validate a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenPayload if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return TokenPayload(
            sub=payload["sub"],
            email=payload["email"],
            role=UserRole(payload["role"]),
            exp=payload["exp"],
            iat=payload["iat"],
            type=payload["type"]
        )
    except JWTError:
        return None


def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    """
    Verify a JWT token and check its type.
    
    Args:
        token: JWT token string
        token_type: Expected token type ("access" or "refresh")
        
    Returns:
        TokenPayload if valid and type matches, None otherwise
    """
    payload = decode_token(token)
    if payload is None:
        return None
    if payload.type != token_type:
        return None
    return payload


# =============================================================================
# User Authentication Service
# =============================================================================

class AuthService:
    """Service class for authentication operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user by email and password.
        
        Args:
            email: User's email
            password: Plain text password
            
        Returns:
            User if authentication succeeds, None otherwise
        """
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            return None
        if not user.is_active:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        await self.db.commit()
        
        return user
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email address."""
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            Created User instance
        """
        user = User(
            email=user_data.email,
            hashed_password=hash_password(user_data.password),
            full_name=user_data.full_name,
            role=user_data.role,
            is_active=user_data.is_active
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Update a user's password.
        
        Args:
            user: User to update
            current_password: Current password for verification
            new_password: New password
            
        Returns:
            True if successful, False if current password is wrong
        """
        if not verify_password(current_password, user.hashed_password):
            return False
        
        user.hashed_password = hash_password(new_password)
        await self.db.commit()
        return True
    
    async def refresh_tokens(self, refresh_token: str) -> Optional[Tuple[str, str]]:
        """
        Refresh access and refresh tokens.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            Tuple of (new_access_token, new_refresh_token) if valid, None otherwise
        """
        payload = verify_token(refresh_token, token_type="refresh")
        if payload is None:
            return None
        
        user = await self.get_user_by_id(uuid.UUID(payload.sub))
        if user is None or not user.is_active:
            return None
        
        return create_token_pair(user)
    
    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100,
        role: Optional[UserRole] = None
    ) -> Tuple[list[User], int]:
        """
        List users with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            role: Optional role filter
            
        Returns:
            Tuple of (users, total_count)
        """
        query = select(User)
        if role:
            query = query.where(User.role == role)
        
        # Get total count
        from sqlalchemy import func
        count_query = select(func.count()).select_from(User)
        if role:
            count_query = count_query.where(User.role == role)
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = list(result.scalars().all())
        
        return users, total
