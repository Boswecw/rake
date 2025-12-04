# API Integration Guide

Complete guide for fetching data from external REST/HTTP APIs with support for various authentication methods, pagination strategies, and response formats.

---

## Overview

The API Fetch adapter allows Rake to automatically fetch and process data from external APIs. It supports multiple authentication methods, pagination strategies, and response formats (JSON, XML).

**Supported authentication:**
- None (public APIs)
- API Key (header or query parameter)
- Bearer Token (JWT, OAuth)
- Basic Auth (username/password)
- Custom Headers

**Supported HTTP methods:**
- GET, POST, PUT, PATCH, DELETE

**Supported pagination:**
- Link headers (RFC 5988)
- JSON path navigation
- Offset-based pagination

**Supported response formats:**
- JSON (with dot-notation path navigation)
- XML (with configurable item tags)

---

## Configuration

Add these to your `.env` file:

```bash
# API Fetch Configuration
API_FETCH_USER_AGENT="Rake/1.0 (API Integration Bot)"
API_FETCH_RATE_LIMIT=0.5  # 0.5 seconds between requests
API_FETCH_TIMEOUT=30.0  # 30 seconds timeout
API_FETCH_MAX_RETRIES=3  # Maximum retry attempts
API_FETCH_MAX_ITEMS=100  # Maximum items per job
API_FETCH_VERIFY_SSL=true  # Verify SSL certificates
```

---

## Quick Start

**Fetch from public JSON API:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://jsonplaceholder.typicode.com/posts",
    "response_format": "json",
    "tenant_id": "tenant-123"
  }'
```

**Fetch with API key authentication:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://api.example.com/v1/articles",
    "auth_type": "api_key",
    "api_key": "your-api-key-here",
    "api_key_name": "X-API-Key",
    "auth_location": "header",
    "response_format": "json",
    "data_path": "data.articles",
    "tenant_id": "tenant-123"
  }'
```

**Fetch with Bearer token:**
```bash
curl -X POST http://localhost:8002/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "source": "api_fetch",
    "api_url": "https://api.example.com/protected/data",
    "auth_type": "bearer",
    "bearer_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "response_format": "json",
    "tenant_id": "tenant-123"
  }'
```

---

## Authentication Methods

### 1. No Authentication
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/public/data",
  "auth_type": "none"
}
```

### 2. API Key (Header)
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/data",
  "auth_type": "api_key",
  "api_key": "secret-key-123",
  "api_key_name": "X-API-Key",
  "auth_location": "header"
}
```

### 3. API Key (Query Parameter)
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/data",
  "auth_type": "api_key",
  "api_key": "secret-key-123",
  "api_key_name": "apikey",
  "auth_location": "query"
}
```

### 4. Bearer Token
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/protected",
  "auth_type": "bearer",
  "bearer_token": "your-jwt-token"
}
```

### 5. Basic Authentication
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/secure",
  "auth_type": "basic",
  "username": "user",
  "password": "pass"
}
```

---

## Pagination Strategies

### 1. Link Headers (RFC 5988)
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/items",
  "pagination_type": "link_header",
  "max_api_pages": 5
}
```

### 2. JSON Path
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/articles",
  "pagination_type": "json_path",
  "next_page_path": "pagination.next",
  "max_api_pages": 10
}
```

---

## Response Formats

### JSON with Data Path
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/data",
  "response_format": "json",
  "data_path": "data.items"
}
```

### XML with Item Tag
```json
{
  "source": "api_fetch",
  "api_url": "https://api.example.com/feed.xml",
  "response_format": "xml",
  "xml_item_tag": "article"
}
```

---

## Best Practices

1. **Use appropriate rate limiting**
2. **Implement proper error handling**
3. **Limit pagination to avoid overwhelming APIs**
4. **Use SSL verification in production**
5. **Store API keys securely**

---

## Error Handling

Common errors and solutions:

**Invalid URL:**
```
ValidationError: Invalid URL format
```
Solution: Ensure URL starts with http:// or https://

**Missing authentication:**
```
ValidationError: api_key is required for api_key auth
```
Solution: Provide required authentication parameters

**HTTP errors:**
```
FetchError: HTTP 401: Unauthorized
```
Solution: Check authentication credentials

---

## Support

For issues with API integration:
1. Check logs with correlation ID
2. Verify API credentials
3. Test API endpoint directly
4. Review rate limit settings

**Status**: ✅ API Integration Complete
