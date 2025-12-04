"""Tenant Context Management for Rake Service

Provides tenant context management for multi-tenant data isolation.
Ensures all operations are scoped to the correct tenant.

Features:
    - FastAPI dependency for tenant extraction
    - Context variable for tenant ID storage
    - Tenant validation
    - Request middleware integration

Example:
    >>> from fastapi import Depends
    >>> from auth.tenant_context import get_current_tenant
    >>>
    >>> @app.get("/api/v1/jobs")
    >>> async def list_jobs(tenant_id: str = Depends(get_current_tenant)):
    ...     # All jobs are automatically filtered by tenant_id
    ...     return await get_jobs_for_tenant(tenant_id)
"""

import logging
from contextvars import ContextVar
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from auth.jwt_handler import extract_tenant_id, verify_token, TokenError

logger = logging.getLogger(__name__)

# Context variable for storing tenant ID across async calls
_tenant_context: ContextVar[Optional[str]] = ContextVar("tenant_context", default=None)

# Security scheme for JWT bearer tokens
security = HTTPBearer()


class TenantContextError(Exception):
    """Exception raised for tenant context errors.

    Example:
        >>> raise TenantContextError("No tenant context available")
    """
    pass


def set_tenant_context(tenant_id: str) -> None:
    """Set the tenant ID in the current context.

    Args:
        tenant_id: Tenant identifier to set

    Example:
        >>> set_tenant_context("tenant-123")
        >>> current = get_tenant_context()
        >>> print(current)
        tenant-123
    """
    _tenant_context.set(tenant_id)
    logger.debug(f"Tenant context set: {tenant_id}")


def get_tenant_context() -> Optional[str]:
    """Get the tenant ID from the current context.

    Returns:
        Current tenant ID, or None if not set

    Example:
        >>> set_tenant_context("tenant-123")
        >>> tenant_id = get_tenant_context()
        >>> print(tenant_id)
        tenant-123
    """
    return _tenant_context.get()


def clear_tenant_context() -> None:
    """Clear the tenant context.

    Useful for cleanup in test scenarios or error handling.

    Example:
        >>> set_tenant_context("tenant-123")
        >>> clear_tenant_context()
        >>> get_tenant_context()
        None
    """
    _tenant_context.set(None)
    logger.debug("Tenant context cleared")


async def get_current_tenant(
    authorization: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """FastAPI dependency to extract tenant ID from JWT token.

    Extracts the tenant ID from the Authorization header and validates it.

    Args:
        authorization: HTTP Authorization header with Bearer token

    Returns:
        Validated tenant ID

    Raises:
        HTTPException: 401 if token is invalid or missing tenant_id

    Example:
        >>> from fastapi import Depends
        >>>
        >>> @app.get("/api/v1/data")
        >>> async def get_data(tenant_id: str = Depends(get_current_tenant)):
        ...     return {"tenant_id": tenant_id, "data": [...]}
    """
    try:
        token = authorization.credentials

        # Verify and extract tenant ID
        tenant_id = extract_tenant_id(token)

        # Set in context for use in downstream operations
        set_tenant_context(tenant_id)

        logger.info(
            f"Authenticated request for tenant: {tenant_id}",
            extra={"tenant_id": tenant_id}
        )

        return tenant_id

    except TokenError as e:
        logger.warning(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Authentication error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_tenant(
    authorization: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """FastAPI dependency to extract optional tenant ID.

    Similar to get_current_tenant but doesn't raise an error if missing.
    Useful for endpoints that work with or without authentication.

    Args:
        authorization: Optional HTTP Authorization header

    Returns:
        Tenant ID if present and valid, None otherwise

    Example:
        >>> @app.get("/api/v1/public-data")
        >>> async def get_public_data(
        ...     tenant_id: Optional[str] = Depends(get_optional_tenant)
        ... ):
        ...     if tenant_id:
        ...         return get_tenant_specific_data(tenant_id)
        ...     return get_public_data()
    """
    if not authorization:
        return None

    try:
        tenant_id = extract_tenant_id(authorization.credentials)
        set_tenant_context(tenant_id)
        return tenant_id
    except TokenError:
        return None
    except Exception as e:
        logger.warning(f"Optional tenant extraction failed: {e}")
        return None


async def get_tenant_from_header(
    x_tenant_id: Optional[str] = Header(None)
) -> Optional[str]:
    """FastAPI dependency to extract tenant ID from custom header.

    Alternative to JWT-based extraction. Useful for internal service-to-service
    communication or development/testing.

    Args:
        x_tenant_id: Custom X-Tenant-ID header

    Returns:
        Tenant ID from header

    Example:
        >>> @app.post("/api/v1/internal/jobs")
        >>> async def create_internal_job(
        ...     tenant_id: str = Depends(get_tenant_from_header)
        ... ):
        ...     return create_job(tenant_id)
    """
    if x_tenant_id:
        set_tenant_context(x_tenant_id)
        logger.debug(f"Tenant ID from header: {x_tenant_id}")

    return x_tenant_id


def require_tenant_context() -> str:
    """Get tenant ID from context, raising error if not set.

    Useful in internal functions that expect tenant context to be set
    by middleware or dependency injection.

    Returns:
        Current tenant ID

    Raises:
        TenantContextError: If tenant context is not set

    Example:
        >>> # In a route handler
        >>> @app.get("/api/v1/jobs")
        >>> async def list_jobs(tenant_id: str = Depends(get_current_tenant)):
        ...     return await _fetch_jobs()
        >>>
        >>> # In internal function
        >>> async def _fetch_jobs():
        ...     tenant_id = require_tenant_context()
        ...     return db.query(Job).filter(Job.tenant_id == tenant_id).all()
    """
    tenant_id = get_tenant_context()
    if not tenant_id:
        raise TenantContextError("Tenant context not set")
    return tenant_id


class TenantContextMiddleware:
    """Middleware to extract and set tenant context from requests.

    Automatically extracts tenant ID from Authorization header or
    X-Tenant-ID header and sets it in the context for the request.

    Example:
        >>> from fastapi import FastAPI
        >>> from auth.tenant_context import TenantContextMiddleware
        >>>
        >>> app = FastAPI()
        >>> app.add_middleware(TenantContextMiddleware)
    """

    def __init__(self, app):
        """Initialize middleware.

        Args:
            app: FastAPI application
        """
        self.app = app

    async def __call__(self, scope, receive, send):
        """Process request and set tenant context.

        Args:
            scope: ASGI scope
            receive: ASGI receive callable
            send: ASGI send callable
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract tenant from headers
        headers = dict(scope.get("headers", []))

        # Try X-Tenant-ID header first
        tenant_id = headers.get(b"x-tenant-id", b"").decode("utf-8")

        # Try Authorization header if X-Tenant-ID not present
        if not tenant_id:
            auth_header = headers.get(b"authorization", b"").decode("utf-8")
            if auth_header.startswith("Bearer "):
                try:
                    token = auth_header[7:]  # Remove "Bearer " prefix
                    tenant_id = extract_tenant_id(token)
                except TokenError:
                    pass  # Continue without tenant context

        # Set tenant context if found
        if tenant_id:
            set_tenant_context(tenant_id)
            logger.debug(f"Middleware set tenant context: {tenant_id}")

        try:
            await self.app(scope, receive, send)
        finally:
            # Clean up context after request
            clear_tenant_context()


# Example usage and testing
if __name__ == "__main__":
    from auth.jwt_handler import create_access_token

    print("=== Tenant Context Examples ===\n")

    # Example 1: Set and get tenant context
    print("Example 1: Tenant Context")
    set_tenant_context("tenant-123")
    current = get_tenant_context()
    print(f"Current tenant: {current}")

    # Example 2: Clear context
    print("\n\nExample 2: Clear Context")
    clear_tenant_context()
    current = get_tenant_context()
    print(f"After clear: {current}")

    # Example 3: Require context (should fail)
    print("\n\nExample 3: Require Context (should fail)")
    try:
        tenant = require_tenant_context()
    except TenantContextError as e:
        print(f"Error (expected): {e}")

    # Example 4: Extract from token
    print("\n\nExample 4: Extract from Token")
    token = create_access_token(tenant_id="tenant-456", user_id="user-789")
    tenant_id = extract_tenant_id(token)
    set_tenant_context(tenant_id)
    print(f"Tenant from token: {tenant_id}")
    print(f"Context value: {get_tenant_context()}")

    print("\n✅ All examples completed")
