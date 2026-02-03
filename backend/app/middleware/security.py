"""
BillAgent Pro - Security Middleware
=====================================
Rate limiting, security headers, and request validation.
"""

import time
from typing import Callable, Optional
from collections import defaultdict
import asyncio

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from .config import settings


# =============================================================================
# Rate Limiting
# =============================================================================

class RateLimiter:
    """
    In-memory rate limiter using token bucket algorithm.
    
    For production, consider using Redis for distributed rate limiting.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: int = 10
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.tokens: dict[str, float] = defaultdict(lambda: float(burst_size))
        self.last_refill: dict[str, float] = defaultdict(time.time)
        self._lock = asyncio.Lock()
    
    def _get_client_key(self, request: Request) -> str:
        """Get unique identifier for rate limiting (IP or user ID)."""
        # Try to get user ID from auth header if available
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            # Use a hash of the token for anonymity
            return f"token:{hash(auth_header)}"
        
        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return f"ip:{forwarded.split(',')[0].strip()}"
        
        client_host = request.client.host if request.client else "unknown"
        return f"ip:{client_host}"
    
    async def is_allowed(self, request: Request) -> tuple[bool, dict]:
        """
        Check if request is allowed under rate limits.
        
        Returns:
            Tuple of (is_allowed, rate_limit_headers)
        """
        async with self._lock:
            client_key = self._get_client_key(request)
            current_time = time.time()
            
            # Refill tokens based on time elapsed
            time_elapsed = current_time - self.last_refill[client_key]
            tokens_to_add = time_elapsed * (self.requests_per_minute / 60.0)
            self.tokens[client_key] = min(
                self.burst_size,
                self.tokens[client_key] + tokens_to_add
            )
            self.last_refill[client_key] = current_time
            
            # Calculate rate limit headers
            remaining = int(self.tokens[client_key])
            headers = {
                "X-RateLimit-Limit": str(self.requests_per_minute),
                "X-RateLimit-Remaining": str(max(0, remaining - 1)),
                "X-RateLimit-Reset": str(int(current_time + 60))
            }
            
            # Check if request is allowed
            if self.tokens[client_key] >= 1:
                self.tokens[client_key] -= 1
                return True, headers
            
            # Calculate retry-after
            tokens_needed = 1 - self.tokens[client_key]
            retry_after = int(tokens_needed / (self.requests_per_minute / 60.0)) + 1
            headers["Retry-After"] = str(retry_after)
            
            return False, headers


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.
    """
    
    def __init__(
        self,
        app: FastAPI,
        requests_per_minute: int = 100,
        burst_size: int = 10,
        exclude_paths: Optional[list[str]] = None
    ):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, burst_size)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)
        
        is_allowed, headers = await self.limiter.is_allowed(request)
        
        if not is_allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please slow down.",
                    "retry_after": headers.get("Retry-After", "60")
                },
                headers=headers
            )
        
        response = await call_next(request)
        
        # Add rate limit headers to response
        for key, value in headers.items():
            response.headers[key] = value
        
        return response


# =============================================================================
# Security Headers
# =============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add security headers to all responses (similar to helmet.js).
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # XSS Protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        # Permissions Policy (formerly Feature Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), magnetometer=(), gyroscope=()"
        )
        
        # Content Security Policy (adjust based on your frontend needs)
        if not settings.debug:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none'; "
                "base-uri 'self'; "
                "form-action 'self'"
            )
        
        # Strict Transport Security (HSTS) - only in production
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        
        return response


# =============================================================================
# Request Validation Middleware
# =============================================================================

class RequestValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate incoming requests for security issues.
    """
    
    # Maximum allowed content length (10MB)
    MAX_CONTENT_LENGTH = 10 * 1024 * 1024
    
    # Suspicious patterns to block
    BLOCKED_USER_AGENTS = [
        "sqlmap",
        "nikto",
        "nmap",
        "masscan",
        "dirbuster"
    ]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check content length
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.MAX_CONTENT_LENGTH:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": "PAYLOAD_TOO_LARGE",
                    "message": f"Request body exceeds {self.MAX_CONTENT_LENGTH // (1024*1024)}MB limit"
                }
            )
        
        # Check for suspicious user agents (basic scanner detection)
        user_agent = request.headers.get("user-agent", "").lower()
        for blocked in self.BLOCKED_USER_AGENTS:
            if blocked in user_agent:
                return JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={
                        "error": "FORBIDDEN",
                        "message": "Request blocked"
                    }
                )
        
        return await call_next(request)


# =============================================================================
# Request ID Middleware
# =============================================================================

import uuid

class RequestIdMiddleware(BaseHTTPMiddleware):
    """
    Add unique request ID to each request for tracing.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        
        # Add to request state for logging
        request.state.request_id = request_id
        
        response = await call_next(request)
        
        # Add to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response


# =============================================================================
# Setup Function
# =============================================================================

def setup_security(
    app: FastAPI,
    rate_limit_per_minute: int = 100,
    enable_rate_limiting: bool = True,
    enable_security_headers: bool = True,
    enable_request_validation: bool = True,
    enable_request_id: bool = True
):
    """
    Configure all security middleware for the FastAPI application.
    
    Args:
        app: FastAPI application instance
        rate_limit_per_minute: Max requests per minute per client
        enable_rate_limiting: Enable rate limiting middleware
        enable_security_headers: Enable security headers middleware
        enable_request_validation: Enable request validation middleware
        enable_request_id: Enable request ID middleware
    """
    
    # Add middlewares in reverse order (last added = first executed)
    
    if enable_request_id:
        app.add_middleware(RequestIdMiddleware)
    
    if enable_request_validation:
        app.add_middleware(RequestValidationMiddleware)
    
    if enable_security_headers:
        app.add_middleware(SecurityHeadersMiddleware)
    
    if enable_rate_limiting:
        app.add_middleware(
            RateLimitMiddleware,
            requests_per_minute=rate_limit_per_minute,
            burst_size=min(20, rate_limit_per_minute // 5)
        )
    
    print(f"   ✅ Security middleware configured:")
    print(f"      - Rate limiting: {rate_limit_per_minute} req/min" if enable_rate_limiting else "      - Rate limiting: disabled")
    print(f"      - Security headers: enabled" if enable_security_headers else "      - Security headers: disabled")
    print(f"      - Request validation: enabled" if enable_request_validation else "      - Request validation: disabled")
    print(f"      - Request ID tracking: enabled" if enable_request_id else "      - Request ID tracking: disabled")
