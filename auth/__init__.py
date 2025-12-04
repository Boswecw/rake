"""Authentication and Authorization modules for Rake Service

Provides JWT authentication, tenant context management, and access control.
"""

from auth.jwt_handler import (
    create_access_token,
    create_refresh_token,
    verify_token,
    extract_tenant_id,
    extract_user_id,
    is_token_expired,
    hash_password,
    verify_password,
    TokenError
)

from auth.tenant_context import (
    set_tenant_context,
    get_tenant_context,
    clear_tenant_context,
    get_current_tenant,
    get_optional_tenant,
    get_tenant_from_header,
    require_tenant_context,
    TenantContextMiddleware,
    TenantContextError
)

__all__ = [
    # JWT handler
    "create_access_token",
    "create_refresh_token",
    "verify_token",
    "extract_tenant_id",
    "extract_user_id",
    "is_token_expired",
    "hash_password",
    "verify_password",
    "TokenError",

    # Tenant context
    "set_tenant_context",
    "get_tenant_context",
    "clear_tenant_context",
    "get_current_tenant",
    "get_optional_tenant",
    "get_tenant_from_header",
    "require_tenant_context",
    "TenantContextMiddleware",
    "TenantContextError",
]
