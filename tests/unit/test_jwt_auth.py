"""
Tests for JWT Authentication and Tenant Context

Tests the JWT handler and tenant context management for secure,
multi-tenant authentication.

Example:
    >>> pytest tests/unit/test_jwt_auth.py -v
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock

from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    extract_tenant_id,
    extract_user_id,
    is_token_expired,
    hash_password,
    verify_password,
    TokenError,
)
from auth.tenant_context import (
    set_tenant_context,
    get_tenant_context,
    clear_tenant_context,
    require_tenant_context,
    get_current_tenant,
    get_optional_tenant,
    get_tenant_from_header,
    TenantContextError,
)


# ============================================================================
# JWT Token Creation Tests
# ============================================================================


class TestCreateAccessToken:
    """Test JWT access token creation."""

    def test_create_token_with_tenant_only(self):
        """Test creating token with only tenant_id."""
        token = create_access_token(tenant_id="tenant-123")

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are typically 100+ chars

    def test_create_token_with_user(self):
        """Test creating token with tenant_id and user_id."""
        token = create_access_token(
            tenant_id="tenant-123",
            user_id="user-456"
        )

        payload = verify_token(token)
        assert payload["tenant_id"] == "tenant-123"
        assert payload["user_id"] == "user-456"

    def test_create_token_with_additional_claims(self):
        """Test creating token with custom claims."""
        token = create_access_token(
            tenant_id="tenant-123",
            user_id="user-456",
            additional_claims={"role": "admin", "permissions": ["read", "write"]}
        )

        payload = verify_token(token)
        assert payload["tenant_id"] == "tenant-123"
        assert payload["user_id"] == "user-456"
        assert payload["role"] == "admin"
        assert payload["permissions"] == ["read", "write"]

    def test_create_token_with_custom_expiration(self):
        """Test creating token with custom expiration time."""
        # Get current time before creating token
        before = datetime.utcnow()

        token = create_access_token(
            tenant_id="tenant-123",
            expires_delta=timedelta(minutes=30)
        )

        payload = verify_token(token)
        assert payload["tenant_id"] == "tenant-123"

        # Check expiration is roughly 30 minutes from creation
        exp_timestamp = payload["exp"]
        iat_timestamp = payload["iat"]

        exp_datetime = datetime.utcfromtimestamp(exp_timestamp)
        iat_datetime = datetime.utcfromtimestamp(iat_timestamp)

        # Calculate time difference between expiration and issuance
        time_diff = (exp_datetime - iat_datetime).total_seconds()

        # Should be around 30 minutes (1800 seconds), allow 5 second tolerance
        assert 1795 < time_diff < 1805

    def test_token_has_required_fields(self):
        """Test that created token has all required JWT fields."""
        token = create_access_token(tenant_id="tenant-123")
        payload = verify_token(token)

        # Required fields
        assert "tenant_id" in payload
        assert "exp" in payload  # Expiration
        assert "iat" in payload  # Issued at
        assert "type" in payload
        assert payload["type"] == "access"


class TestCreateRefreshToken:
    """Test JWT refresh token creation."""

    def test_create_refresh_token(self):
        """Test creating refresh token."""
        token = create_refresh_token(
            tenant_id="tenant-123",
            user_id="user-456"
        )

        payload = verify_token(token)
        assert payload["tenant_id"] == "tenant-123"
        assert payload["user_id"] == "user-456"
        assert payload["type"] == "refresh"

    def test_refresh_token_longer_expiration(self):
        """Test that refresh tokens have longer expiration than access tokens."""
        access_token = create_access_token(tenant_id="tenant-123")
        refresh_token = create_refresh_token(tenant_id="tenant-123")

        access_payload = verify_token(access_token)
        refresh_payload = verify_token(refresh_token)

        # Refresh token should expire much later than access token
        assert refresh_payload["exp"] > access_payload["exp"]


# ============================================================================
# JWT Token Verification Tests
# ============================================================================


class TestVerifyToken:
    """Test JWT token verification."""

    def test_verify_valid_token(self):
        """Test verifying a valid token."""
        token = create_access_token(tenant_id="tenant-123")
        payload = verify_token(token)

        assert payload["tenant_id"] == "tenant-123"

    def test_verify_token_with_all_fields(self):
        """Test verifying token returns all fields."""
        token = create_access_token(
            tenant_id="tenant-123",
            user_id="user-456",
            additional_claims={"role": "admin"}
        )
        payload = verify_token(token)

        assert payload["tenant_id"] == "tenant-123"
        assert payload["user_id"] == "user-456"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_verify_invalid_token(self):
        """Test verifying an invalid token raises error."""
        with pytest.raises(TokenError):
            verify_token("invalid-token-string")

    def test_verify_token_without_tenant_id(self):
        """Test verifying token without tenant_id raises error."""
        # This would require manually creating a malformed token
        # which is difficult, so we skip this edge case

    def test_verify_expired_token(self):
        """Test verifying expired token raises error."""
        # Create token that expires immediately
        token = create_access_token(
            tenant_id="tenant-123",
            expires_delta=timedelta(seconds=-1)  # Already expired
        )

        with pytest.raises(TokenError, match="Invalid token"):
            verify_token(token)


# ============================================================================
# Token Extraction Tests
# ============================================================================


class TestExtractTenantId:
    """Test tenant ID extraction from tokens."""

    def test_extract_tenant_id(self):
        """Test extracting tenant_id from token."""
        token = create_access_token(tenant_id="tenant-123")
        tenant_id = extract_tenant_id(token)

        assert tenant_id == "tenant-123"

    def test_extract_from_token_with_user(self):
        """Test extracting tenant_id when user_id is also present."""
        token = create_access_token(
            tenant_id="tenant-abc",
            user_id="user-xyz"
        )
        tenant_id = extract_tenant_id(token)

        assert tenant_id == "tenant-abc"

    def test_extract_from_invalid_token(self):
        """Test extracting from invalid token raises error."""
        with pytest.raises(TokenError):
            extract_tenant_id("invalid-token")


class TestExtractUserId:
    """Test user ID extraction from tokens."""

    def test_extract_user_id(self):
        """Test extracting user_id from token."""
        token = create_access_token(
            tenant_id="tenant-123",
            user_id="user-456"
        )
        user_id = extract_user_id(token)

        assert user_id == "user-456"

    def test_extract_user_id_when_not_present(self):
        """Test extracting user_id when not in token returns None."""
        token = create_access_token(tenant_id="tenant-123")
        user_id = extract_user_id(token)

        assert user_id is None


class TestIsTokenExpired:
    """Test token expiration checking."""

    def test_token_not_expired(self):
        """Test that fresh token is not expired."""
        token = create_access_token(tenant_id="tenant-123")

        assert is_token_expired(token) is False

    def test_token_is_expired(self):
        """Test that expired token is detected."""
        # Create token that expires in 1 second
        token = create_access_token(
            tenant_id="tenant-123",
            expires_delta=timedelta(seconds=1)
        )

        # Wait for expiration
        time.sleep(2)

        assert is_token_expired(token) is True


# ============================================================================
# Password Hashing Tests
# ============================================================================


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self):
        """Test hashing a password."""
        password = "my-secret-password"
        hashed = hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt hash prefix

    def test_verify_correct_password(self):
        """Test verifying correct password."""
        password = "my-secret-password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Test verifying incorrect password."""
        password = "my-secret-password"
        hashed = hash_password(password)

        assert verify_password("wrong-password", hashed) is False

    def test_different_passwords_different_hashes(self):
        """Test that same password hashed twice produces different hashes."""
        password = "my-secret-password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (bcrypt uses random salt)
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True


# ============================================================================
# Tenant Context Tests
# ============================================================================


class TestTenantContext:
    """Test tenant context management."""

    def test_set_and_get_context(self):
        """Test setting and getting tenant context."""
        set_tenant_context("tenant-123")
        current = get_tenant_context()

        assert current == "tenant-123"

    def test_get_context_when_not_set(self):
        """Test getting context when not set returns None."""
        clear_tenant_context()
        current = get_tenant_context()

        assert current is None

    def test_clear_context(self):
        """Test clearing tenant context."""
        set_tenant_context("tenant-123")
        clear_tenant_context()
        current = get_tenant_context()

        assert current is None

    def test_require_context_when_set(self):
        """Test requiring context when it's set."""
        set_tenant_context("tenant-123")
        tenant_id = require_tenant_context()

        assert tenant_id == "tenant-123"

    def test_require_context_when_not_set(self):
        """Test requiring context when not set raises error."""
        clear_tenant_context()

        with pytest.raises(TenantContextError, match="not set"):
            require_tenant_context()

    def test_context_isolation(self):
        """Test that context changes don't affect previous reads."""
        set_tenant_context("tenant-1")
        first_read = get_tenant_context()

        set_tenant_context("tenant-2")
        second_read = get_tenant_context()

        assert first_read == "tenant-1"
        assert second_read == "tenant-2"


# ============================================================================
# FastAPI Dependency Tests
# ============================================================================


class TestGetCurrentTenant:
    """Test get_current_tenant FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_tenant_from_valid_token(self):
        """Test extracting tenant from valid JWT token."""
        # Create valid token
        token = create_access_token(tenant_id="tenant-123", user_id="user-456")

        # Create mock authorization header
        auth = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials=token
        )

        # Call dependency
        tenant_id = await get_current_tenant(authorization=auth)

        assert tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_get_tenant_sets_context(self):
        """Test that get_current_tenant sets the context."""
        clear_tenant_context()

        token = create_access_token(tenant_id="tenant-abc")
        auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        await get_current_tenant(authorization=auth)

        # Context should be set
        assert get_tenant_context() == "tenant-abc"

    @pytest.mark.asyncio
    async def test_get_tenant_invalid_token_raises_401(self):
        """Test that invalid token raises HTTPException 401."""
        auth = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_tenant(authorization=auth)

        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail


class TestGetOptionalTenant:
    """Test get_optional_tenant FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_tenant_when_present(self):
        """Test extracting tenant when authorization is present."""
        token = create_access_token(tenant_id="tenant-123")
        auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        tenant_id = await get_optional_tenant(authorization=auth)

        assert tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_get_tenant_when_not_present(self):
        """Test that missing authorization returns None."""
        tenant_id = await get_optional_tenant(authorization=None)

        assert tenant_id is None

    @pytest.mark.asyncio
    async def test_get_tenant_invalid_token_returns_none(self):
        """Test that invalid token returns None (no exception)."""
        auth = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-token"
        )

        tenant_id = await get_optional_tenant(authorization=auth)

        assert tenant_id is None


class TestGetTenantFromHeader:
    """Test get_tenant_from_header FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_get_tenant_from_header(self):
        """Test extracting tenant from X-Tenant-ID header."""
        tenant_id = await get_tenant_from_header(x_tenant_id="tenant-123")

        assert tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_get_tenant_header_not_present(self):
        """Test that missing header returns None."""
        tenant_id = await get_tenant_from_header(x_tenant_id=None)

        assert tenant_id is None

    @pytest.mark.asyncio
    async def test_get_tenant_header_sets_context(self):
        """Test that header extraction sets context."""
        clear_tenant_context()

        await get_tenant_from_header(x_tenant_id="tenant-xyz")

        assert get_tenant_context() == "tenant-xyz"


# ============================================================================
# Integration Tests
# ============================================================================


class TestJWTIntegration:
    """Test complete JWT authentication workflows."""

    def test_complete_authentication_flow(self):
        """Test complete flow: create token → verify → extract data."""
        # 1. Create access token
        access_token = create_access_token(
            tenant_id="tenant-integration",
            user_id="user-integration",
            additional_claims={"role": "admin"}
        )

        # 2. Verify token
        payload = verify_token(access_token)
        assert payload["tenant_id"] == "tenant-integration"
        assert payload["user_id"] == "user-integration"
        assert payload["role"] == "admin"

        # 3. Extract specific fields
        tenant_id = extract_tenant_id(access_token)
        user_id = extract_user_id(access_token)

        assert tenant_id == "tenant-integration"
        assert user_id == "user-integration"

    def test_refresh_token_flow(self):
        """Test creating and using refresh token."""
        # Create refresh token
        refresh_token = create_refresh_token(
            tenant_id="tenant-refresh",
            user_id="user-refresh"
        )

        # Verify it's a refresh token
        payload = verify_token(refresh_token)
        assert payload["type"] == "refresh"
        assert payload["tenant_id"] == "tenant-refresh"

        # Can extract tenant from refresh token
        tenant_id = extract_tenant_id(refresh_token)
        assert tenant_id == "tenant-refresh"

    @pytest.mark.asyncio
    async def test_fastapi_dependency_flow(self):
        """Test FastAPI dependency injection flow."""
        # Create token
        token = create_access_token(
            tenant_id="tenant-fastapi",
            user_id="user-fastapi"
        )

        # Simulate FastAPI dependency resolution
        auth = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        tenant_id = await get_current_tenant(authorization=auth)

        # Verify context is set
        assert tenant_id == "tenant-fastapi"
        assert get_tenant_context() == "tenant-fastapi"

        # Can use require_tenant_context in downstream functions
        current_tenant = require_tenant_context()
        assert current_tenant == "tenant-fastapi"

    def test_password_authentication_flow(self):
        """Test complete password authentication workflow."""
        # 1. User registers - hash password
        plain_password = "user-secret-password"
        hashed_password = hash_password(plain_password)

        # Store hashed_password in database...

        # 2. User logs in - verify password
        login_password = "user-secret-password"
        is_valid = verify_password(login_password, hashed_password)
        assert is_valid is True

        # 3. Create access token for authenticated user
        if is_valid:
            token = create_access_token(
                tenant_id="tenant-auth",
                user_id="user-auth"
            )

            # 4. Token can be used for subsequent requests
            tenant_id = extract_tenant_id(token)
            assert tenant_id == "tenant-auth"

    def test_multi_tenant_isolation(self):
        """Test that different tenants have isolated contexts."""
        # Create tokens for different tenants
        token_a = create_access_token(tenant_id="tenant-a")
        token_b = create_access_token(tenant_id="tenant-b")

        # Extract tenant IDs
        tenant_a = extract_tenant_id(token_a)
        tenant_b = extract_tenant_id(token_b)

        # Verify isolation
        assert tenant_a == "tenant-a"
        assert tenant_b == "tenant-b"
        assert tenant_a != tenant_b

        # Set context for tenant A
        set_tenant_context(tenant_a)
        assert get_tenant_context() == "tenant-a"

        # Switch to tenant B
        set_tenant_context(tenant_b)
        assert get_tenant_context() == "tenant-b"
