"""Unit Tests for API Fetch Source Adapter

Tests for API integration functionality including authentication methods,
pagination strategies, response parsing, and error handling.

Run with:
    pytest tests/unit/test_api_fetch.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import json

from sources.api_fetch import APIFetchAdapter
from sources.base import FetchError, ValidationError
from models.document import DocumentSource


class TestAPIFetchAdapterInit:
    """Tests for API fetch adapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        assert adapter.user_agent == "Rake/1.0 (API Integration Bot)"
        assert adapter.tenant_id == "tenant-123"
        assert adapter.source_type == DocumentSource.API_FETCH
        assert adapter.rate_limit_delay == 0.5
        assert adapter.timeout == 30.0
        assert adapter.max_retries == 3
        assert adapter.max_items == 100
        assert adapter.verify_ssl is True

    def test_init_with_custom_user_agent(self):
        """Test initialization with custom user-agent."""
        adapter = APIFetchAdapter(
            user_agent="CustomBot/2.0",
            tenant_id="tenant-123"
        )
        assert adapter.user_agent == "CustomBot/2.0"

    def test_init_with_custom_rate_limit(self):
        """Test initialization with custom rate limit."""
        adapter = APIFetchAdapter(
            tenant_id="tenant-123",
            rate_limit_delay=1.0
        )
        assert adapter.rate_limit_delay == 1.0

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        adapter = APIFetchAdapter(
            tenant_id="tenant-123",
            timeout=60.0
        )
        assert adapter.timeout == 60.0

    def test_init_with_ssl_disabled(self):
        """Test initialization with SSL verification disabled."""
        adapter = APIFetchAdapter(
            tenant_id="tenant-123",
            verify_ssl=False
        )
        assert adapter.verify_ssl is False


class TestValidateInput:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_validate_with_url(self):
        """Test validation with URL parameter."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        await adapter._validate_input(url="https://api.example.com/data")
        # Should not raise

    @pytest.mark.asyncio
    async def test_validate_without_url(self):
        """Test validation fails without URL."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input()

        assert "url is required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_with_invalid_url(self):
        """Test validation fails with invalid URL."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(url="not-a-valid-url")

        assert "invalid url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_with_invalid_auth_type(self):
        """Test validation fails with invalid auth type."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                url="https://api.example.com",
                auth_type="invalid"
            )

        assert "invalid auth_type" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_api_key_missing_key(self):
        """Test validation fails for api_key auth without key."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                url="https://api.example.com",
                auth_type="api_key"
            )

        assert "api_key is required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_api_key_missing_location(self):
        """Test validation fails for api_key auth without location."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                url="https://api.example.com",
                auth_type="api_key",
                api_key="secret-123"
            )

        assert "auth_location is required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_bearer_missing_token(self):
        """Test validation fails for bearer auth without token."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                url="https://api.example.com",
                auth_type="bearer"
            )

        assert "bearer_token is required" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_basic_missing_credentials(self):
        """Test validation fails for basic auth without credentials."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(
                url="https://api.example.com",
                auth_type="basic"
            )

        assert "username and password" in str(exc_info.value).lower()


class TestBuildHeaders:
    """Tests for HTTP header building."""

    def test_build_headers_no_auth(self):
        """Test building headers with no authentication."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        headers = adapter._build_headers(auth_type="none")

        assert "User-Agent" in headers
        assert "Authorization" not in headers

    def test_build_headers_api_key_header(self):
        """Test building headers with API key in header."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        headers = adapter._build_headers(
            auth_type="api_key",
            api_key="secret-123",
            api_key_name="X-API-Key",
            auth_location="header"
        )

        assert headers["X-API-Key"] == "secret-123"

    def test_build_headers_api_key_query(self):
        """Test building headers with API key in query (not in headers)."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        headers = adapter._build_headers(
            auth_type="api_key",
            api_key="secret-123",
            auth_location="query"
        )

        assert "X-API-Key" not in headers
        assert "User-Agent" in headers

    def test_build_headers_bearer_token(self):
        """Test building headers with Bearer token."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        headers = adapter._build_headers(
            auth_type="bearer",
            bearer_token="token-abc-123"
        )

        assert headers["Authorization"] == "Bearer token-abc-123"

    def test_build_headers_custom(self):
        """Test building headers with custom headers."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        custom_headers = {
            "X-Custom-Header": "custom-value",
            "X-Request-ID": "req-123"
        }
        headers = adapter._build_headers(
            auth_type="none",
            custom_headers=custom_headers
        )

        assert headers["X-Custom-Header"] == "custom-value"
        assert headers["X-Request-ID"] == "req-123"


class TestBuildURL:
    """Tests for URL building."""

    def test_build_url_no_params(self):
        """Test building URL without query parameters."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        url = adapter._build_url(base_url="https://api.example.com/data")

        assert url == "https://api.example.com/data"

    def test_build_url_with_query_params(self):
        """Test building URL with query parameters."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        url = adapter._build_url(
            base_url="https://api.example.com/data",
            query_params={"limit": 10, "offset": 0}
        )

        assert "limit=10" in url
        assert "offset=0" in url

    def test_build_url_api_key_in_query(self):
        """Test building URL with API key in query string."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        url = adapter._build_url(
            base_url="https://api.example.com/data",
            auth_type="api_key",
            api_key="secret-123",
            api_key_name="api_key",
            auth_location="query"
        )

        assert "api_key=secret-123" in url


class TestParseJSONResponse:
    """Tests for JSON response parsing."""

    def test_parse_json_simple_list(self):
        """Test parsing JSON response with simple list."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.json.return_value = [
            {"id": 1, "title": "Item 1"},
            {"id": 2, "title": "Item 2"}
        ]

        items = adapter._parse_json_response(response)

        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["title"] == "Item 2"

    def test_parse_json_with_data_path(self):
        """Test parsing JSON response with data path."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.json.return_value = {
            "success": True,
            "data": {
                "items": [
                    {"id": 1, "title": "Item 1"},
                    {"id": 2, "title": "Item 2"}
                ]
            }
        }

        items = adapter._parse_json_response(response, data_path="data.items")

        assert len(items) == 2
        assert items[0]["id"] == 1

    def test_parse_json_single_object(self):
        """Test parsing JSON response with single object."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.json.return_value = {"id": 1, "title": "Single Item"}

        items = adapter._parse_json_response(response)

        assert len(items) == 1
        assert items[0]["id"] == 1

    def test_parse_json_invalid(self):
        """Test parsing invalid JSON raises error."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with pytest.raises(FetchError) as exc_info:
            adapter._parse_json_response(response)

        assert "invalid json" in str(exc_info.value).lower()


class TestParseXMLResponse:
    """Tests for XML response parsing."""

    def test_parse_xml_with_items(self):
        """Test parsing XML response with items."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        xml_content = """<?xml version="1.0"?>
        <root>
            <item>
                <id>1</id>
                <title>Item 1</title>
            </item>
            <item>
                <id>2</id>
                <title>Item 2</title>
            </item>
        </root>
        """

        response = MagicMock()
        response.text = xml_content

        items = adapter._parse_xml_response(response, item_tag="item")

        assert len(items) == 2
        assert items[0]["id"] == "1"
        assert items[1]["title"] == "Item 2"

    def test_parse_xml_custom_tag(self):
        """Test parsing XML response with custom tag."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        xml_content = """<?xml version="1.0"?>
        <root>
            <article>
                <title>Article 1</title>
            </article>
        </root>
        """

        response = MagicMock()
        response.text = xml_content

        items = adapter._parse_xml_response(response, item_tag="article")

        assert len(items) == 1
        assert items[0]["title"] == "Article 1"

    def test_parse_xml_invalid(self):
        """Test parsing invalid XML raises error."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.text = "Not valid XML"

        with pytest.raises(FetchError) as exc_info:
            adapter._parse_xml_response(response)

        assert "invalid xml" in str(exc_info.value).lower()


class TestExtractPaginationInfo:
    """Tests for pagination information extraction."""

    def test_extract_pagination_none(self):
        """Test no pagination extraction."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        next_url = adapter._extract_pagination_info(response, pagination_type="none")

        assert next_url is None

    def test_extract_pagination_link_header(self):
        """Test pagination extraction from Link header."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.headers = {
            "Link": '<https://api.example.com/data?page=2>; rel="next"'
        }

        next_url = adapter._extract_pagination_info(
            response,
            pagination_type="link_header"
        )

        assert next_url == "https://api.example.com/data?page=2"

    def test_extract_pagination_json_path(self):
        """Test pagination extraction from JSON path."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        response = MagicMock()
        response.json.return_value = {
            "pagination": {
                "next": "https://api.example.com/data?page=2"
            }
        }

        next_url = adapter._extract_pagination_info(
            response,
            pagination_type="json_path",
            next_page_path="pagination.next"
        )

        assert next_url == "https://api.example.com/data?page=2"


class TestConvertToDocument:
    """Tests for converting API items to documents."""

    def test_convert_to_document_with_content_field(self):
        """Test converting item with explicit content field."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        item = {
            "id": 1,
            "title": "Article Title",
            "body": "Article content here"
        }

        doc = adapter._convert_to_document(
            item=item,
            source_url="https://api.example.com/articles",
            content_field="body",
            title_field="title"
        )

        assert "Article content here" in doc.content
        assert doc.metadata["title"] == "Article Title"
        assert doc.metadata["source_url"] == "https://api.example.com/articles"
        assert doc.source == DocumentSource.API_FETCH

    def test_convert_to_document_fallback_fields(self):
        """Test converting item with fallback content fields."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        item = {
            "id": 1,
            "title": "Article Title",
            "text": "Article text content"
        }

        doc = adapter._convert_to_document(
            item=item,
            source_url="https://api.example.com/articles",
            content_field="content"  # Not present, should fallback
        )

        assert "Article text content" in doc.content

    def test_convert_to_document_json_fallback(self):
        """Test converting item with no content field uses JSON."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        item = {
            "id": 1,
            "status": "active"
        }

        doc = adapter._convert_to_document(
            item=item,
            source_url="https://api.example.com/items",
            content_field="content"
        )

        # Should serialize entire item as JSON
        assert '"id": 1' in doc.content or '"id":1' in doc.content


class TestMakeRequest:
    """Tests for making HTTP requests."""

    @pytest.mark.asyncio
    async def test_make_request_get(self):
        """Test making GET request."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        with patch.object(adapter.client, 'get', return_value=mock_response):
            response = await adapter._make_request(
                url="https://api.example.com/data",
                method="GET"
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_make_request_post(self):
        """Test making POST request."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()

        body = {"key": "value"}

        with patch.object(adapter.client, 'post', return_value=mock_response):
            response = await adapter._make_request(
                url="https://api.example.com/data",
                method="POST",
                body=body
            )

            assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_make_request_http_error(self):
        """Test HTTP error handling."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=mock_response
        )

        with patch.object(adapter.client, 'get', return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                await adapter._make_request(
                    url="https://api.example.com/notfound",
                    method="GET"
                )

            assert "404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_make_request_timeout(self):
        """Test request timeout handling."""
        adapter = APIFetchAdapter(tenant_id="tenant-123", timeout=1.0)

        with patch.object(adapter.client, 'get', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(FetchError) as exc_info:
                await adapter._make_request(
                    url="https://api.example.com/slow",
                    method="GET"
                )

            assert "timeout" in str(exc_info.value).lower()


class TestFetch:
    """Tests for the main fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_simple_json(self):
        """Test fetching simple JSON data."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        json_data = [
            {"id": 1, "title": "Item 1", "content": "Content 1"},
            {"id": 2, "title": "Item 2", "content": "Content 2"}
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch.object(adapter.client, 'get', return_value=mock_response):
            documents = await adapter.fetch(
                url="https://api.example.com/items",
                auth_type="none",
                response_format="json"
            )

            assert len(documents) == 2
            assert "Content 1" in documents[0].content
            assert documents[0].source == DocumentSource.API_FETCH
            assert documents[0].tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_fetch_with_api_key_header(self):
        """Test fetching with API key in header."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        json_data = [{"id": 1, "content": "Secured content"}]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch.object(adapter.client, 'get', return_value=mock_response) as mock_get:
            documents = await adapter.fetch(
                url="https://api.example.com/secure",
                auth_type="api_key",
                api_key="secret-123",
                api_key_name="X-API-Key",
                auth_location="header",
                response_format="json"
            )

            assert len(documents) == 1
            # Verify API key was in headers
            call_headers = mock_get.call_args[1]["headers"]
            assert call_headers["X-API-Key"] == "secret-123"

    @pytest.mark.asyncio
    async def test_fetch_with_bearer_token(self):
        """Test fetching with Bearer token."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        json_data = [{"id": 1, "content": "Authorized content"}]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch.object(adapter.client, 'get', return_value=mock_response) as mock_get:
            documents = await adapter.fetch(
                url="https://api.example.com/auth",
                auth_type="bearer",
                bearer_token="token-xyz",
                response_format="json"
            )

            assert len(documents) == 1
            call_headers = mock_get.call_args[1]["headers"]
            assert call_headers["Authorization"] == "Bearer token-xyz"

    @pytest.mark.asyncio
    async def test_fetch_with_pagination(self):
        """Test fetching with pagination."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        page1_data = [{"id": 1, "content": "Page 1"}]
        page2_data = [{"id": 2, "content": "Page 2"}]

        mock_response_1 = MagicMock()
        mock_response_1.status_code = 200
        mock_response_1.json.return_value = page1_data
        mock_response_1.raise_for_status = MagicMock()
        mock_response_1.headers = {
            "Link": '<https://api.example.com/items?page=2>; rel="next"'
        }

        mock_response_2 = MagicMock()
        mock_response_2.status_code = 200
        mock_response_2.json.return_value = page2_data
        mock_response_2.raise_for_status = MagicMock()
        mock_response_2.headers = {}

        with patch.object(adapter.client, 'get', side_effect=[mock_response_1, mock_response_2]):
            with patch.object(adapter.client, 'aclose', return_value=None):
                documents = await adapter.fetch(
                    url="https://api.example.com/items",
                    auth_type="none",
                    response_format="json",
                    pagination_type="link_header",
                    max_pages=2
                )

                assert len(documents) == 2

    @pytest.mark.asyncio
    async def test_fetch_respects_max_items(self):
        """Test fetch respects max_items limit."""
        adapter = APIFetchAdapter(tenant_id="tenant-123", max_items=1)

        json_data = [
            {"id": 1, "content": "Item 1"},
            {"id": 2, "content": "Item 2"}
        ]

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = json_data
        mock_response.raise_for_status = MagicMock()
        mock_response.headers = {}

        with patch.object(adapter.client, 'get', return_value=mock_response):
            documents = await adapter.fetch(
                url="https://api.example.com/items",
                auth_type="none",
                response_format="json"
            )

            # Should only return 1 document despite 2 in response
            assert len(documents) == 1


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(adapter.client, 'get', return_value=mock_response):
            is_healthy = await adapter.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")

        with patch.object(adapter.client, 'get', side_effect=httpx.RequestError("Connection failed")):
            is_healthy = await adapter.health_check()
            assert is_healthy is False


class TestSupportedFormats:
    """Tests for supported formats and auth types."""

    def test_get_supported_formats(self):
        """Test getting supported response formats."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        formats = adapter.get_supported_formats()

        assert "json" in formats
        assert "xml" in formats

    def test_get_supported_auth_types(self):
        """Test getting supported authentication types."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        auth_types = adapter.get_supported_auth_types()

        assert "none" in auth_types
        assert "api_key" in auth_types
        assert "bearer" in auth_types
        assert "basic" in auth_types
        assert "custom" in auth_types

    def test_get_supported_pagination_types(self):
        """Test getting supported pagination types."""
        adapter = APIFetchAdapter(tenant_id="tenant-123")
        pagination_types = adapter.get_supported_pagination_types()

        assert "none" in pagination_types
        assert "link_header" in pagination_types
        assert "json_path" in pagination_types
        assert "offset" in pagination_types
