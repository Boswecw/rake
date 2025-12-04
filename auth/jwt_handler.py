"""JWT Authentication Handler for Rake Service

Provides JWT token creation, validation, and decoding for API authentication.
Supports tenant-aware authentication for multi-tenancy.

Features:
    - JWT token generation
    - Token validation and verification
    - Tenant ID extraction
    - Token expiration handling
    - Refresh token support

Example:
    >>> from auth.jwt_handler import create_access_token, verify_token
    >>>
    >>> # Create token
    >>> token = create_access_token(
    ...     tenant_id="tenant-123",
    ...     user_id="user-456"
    ... )
    >>>
    >>> # Verify token
    >>> payload = verify_token(token)
    >>> print(payload['tenant_id'])
    tenant-123
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings

logger = logging.getLogger(__name__)

# JWT Configuration loaded from environment variables
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenError(Exception):
    """Exception raised for token-related errors.

    Example:
        >>> raise TokenError("Invalid token signature")
    """
    pass


def create_access_token(
    tenant_id: str,
    user_id: Optional[str] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier (optional)
        additional_claims: Additional JWT claims
        expires_delta: Custom expiration time

    Returns:
        Encoded JWT token

    Raises:
        TokenError: If token creation fails

    Example:
        >>> token = create_access_token(
        ...     tenant_id="tenant-123",
        ...     user_id="user-456",
        ...     additional_claims={"role": "admin"}
        ... )
        >>> print(token[:20])  # First 20 chars
        eyJhbGciOiJIUzI1NiIs...
    """
    try:
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        # Build claims
        claims = {
            "tenant_id": tenant_id,
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }

        if user_id:
            claims["user_id"] = user_id

        if additional_claims:
            claims.update(additional_claims)

        # Encode token
        token = jwt.encode(claims, SECRET_KEY, algorithm=ALGORITHM)

        logger.debug(
            f"Created access token for tenant {tenant_id}",
            extra={"tenant_id": tenant_id, "user_id": user_id}
        )

        return token

    except Exception as e:
        logger.error(f"Failed to create access token: {e}", exc_info=True)
        raise TokenError(f"Token creation failed: {e}")


def create_refresh_token(
    tenant_id: str,
    user_id: Optional[str] = None
) -> str:
    """Create a JWT refresh token.

    Refresh tokens have longer expiration times and are used to
    obtain new access tokens without re-authentication.

    Args:
        tenant_id: Tenant identifier
        user_id: User identifier (optional)

    Returns:
        Encoded JWT refresh token

    Example:
        >>> refresh_token = create_refresh_token(
        ...     tenant_id="tenant-123",
        ...     user_id="user-456"
        ... )
    """
    return create_access_token(
        tenant_id=tenant_id,
        user_id=user_id,
        additional_claims={"type": "refresh"},
        expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )


def verify_token(token: str) -> Dict[str, Any]:
    """Verify and decode a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Decoded token payload

    Raises:
        TokenError: If token is invalid or expired

    Example:
        >>> token = create_access_token("tenant-123")
        >>> payload = verify_token(token)
        >>> print(payload['tenant_id'])
        tenant-123
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # Validate required fields
        if "tenant_id" not in payload:
            raise TokenError("Token missing tenant_id claim")

        if "type" not in payload or payload["type"] not in ["access", "refresh"]:
            raise TokenError("Invalid token type")

        logger.debug(
            f"Token verified for tenant {payload['tenant_id']}",
            extra={"tenant_id": payload.get("tenant_id")}
        )

        return payload

    except JWTError as e:
        logger.warning(f"Token verification failed: {e}")
        raise TokenError(f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Unexpected error verifying token: {e}", exc_info=True)
        raise TokenError(f"Token verification error: {e}")


def extract_tenant_id(token: str) -> str:
    """Extract tenant ID from JWT token.

    Convenience function to get tenant ID without full verification.

    Args:
        token: JWT token

    Returns:
        Tenant ID

    Raises:
        TokenError: If token is invalid or missing tenant_id

    Example:
        >>> token = create_access_token("tenant-123")
        >>> tenant_id = extract_tenant_id(token)
        >>> print(tenant_id)
        tenant-123
    """
    payload = verify_token(token)
    return payload["tenant_id"]


def extract_user_id(token: str) -> Optional[str]:
    """Extract user ID from JWT token.

    Args:
        token: JWT token

    Returns:
        User ID if present, None otherwise

    Example:
        >>> token = create_access_token("tenant-123", user_id="user-456")
        >>> user_id = extract_user_id(token)
        >>> print(user_id)
        user-456
    """
    payload = verify_token(token)
    return payload.get("user_id")


def is_token_expired(token: str) -> bool:
    """Check if a token is expired without raising an exception.

    Args:
        token: JWT token

    Returns:
        True if expired, False otherwise

    Example:
        >>> token = create_access_token("tenant-123")
        >>> is_token_expired(token)
        False
    """
    try:
        verify_token(token)
        return False
    except TokenError as e:
        if "expired" in str(e).lower():
            return True
        raise


# Password hashing utilities

def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password

    Example:
        >>> hashed = hash_password("my-secret-password")
        >>> print(hashed[:7])
        $2b$12$
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches, False otherwise

    Example:
        >>> hashed = hash_password("secret")
        >>> verify_password("secret", hashed)
        True
        >>> verify_password("wrong", hashed)
        False
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Password verification error: {e}")
        return False


# Example usage and testing
if __name__ == "__main__":
    import time

    print("=== JWT Handler Examples ===\n")

    # Example 1: Create and verify access token
    print("Example 1: Access Token")
    access_token = create_access_token(
        tenant_id="tenant-123",
        user_id="user-456",
        additional_claims={"role": "admin", "permissions": ["read", "write"]}
    )
    print(f"Token: {access_token[:50]}...")

    payload = verify_token(access_token)
    print(f"Tenant ID: {payload['tenant_id']}")
    print(f"User ID: {payload['user_id']}")
    print(f"Role: {payload.get('role')}")
    print(f"Expires: {datetime.fromtimestamp(payload['exp'])}")

    # Example 2: Extract tenant ID
    print("\n\nExample 2: Extract Tenant ID")
    tenant_id = extract_tenant_id(access_token)
    print(f"Extracted tenant_id: {tenant_id}")

    # Example 3: Refresh token
    print("\n\nExample 3: Refresh Token")
    refresh_token = create_refresh_token(
        tenant_id="tenant-123",
        user_id="user-456"
    )
    refresh_payload = verify_token(refresh_token)
    print(f"Token type: {refresh_payload['type']}")
    print(f"Expires: {datetime.fromtimestamp(refresh_payload['exp'])}")

    # Example 4: Password hashing
    print("\n\nExample 4: Password Hashing")
    password = "my-secret-password"
    hashed = hash_password(password)
    print(f"Original: {password}")
    print(f"Hashed: {hashed}")
    print(f"Verify correct: {verify_password(password, hashed)}")
    print(f"Verify wrong: {verify_password('wrong-password', hashed)}")

    # Example 5: Expired token
    print("\n\nExample 5: Token Expiration")
    short_token = create_access_token(
        tenant_id="tenant-123",
        expires_delta=timedelta(seconds=1)
    )
    print(f"Token created (expires in 1 second)")
    print(f"Is expired (immediate): {is_token_expired(short_token)}")
    time.sleep(2)
    print(f"Is expired (after 2 seconds): {is_token_expired(short_token)}")

    print("\n✅ All examples completed")
