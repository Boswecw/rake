"""
API Fetch Source Adapter

Fetches data from external REST/HTTP APIs with support for various
authentication methods, pagination strategies, and response formats.

Example:
    >>> from sources.api_fetch import APIFetchAdapter
    >>> adapter = APIFetchAdapter(tenant_id="tenant-123")
    >>> documents = await adapter.fetch(
    ...     url="https://api.example.com/v1/articles",
    ...     auth_type="api_key",
    ...     api_key="secret-key-123",
    ...     auth_location="header",
    ...     response_format="json",
    ...     data_path="data.articles"
    ... )
"""

import logging
import time
import json
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Literal
from uuid import uuid4
from urllib.parse import urljoin, urlencode
import httpx
from bs4 import BeautifulSoup

from models.document import RawDocument, DocumentSource
from sources.base import BaseSourceAdapter, FetchError, ValidationError

logger = logging.getLogger(__name__)


class APIFetchAdapter(BaseSourceAdapter):
    """Adapter for fetching data from external REST/HTTP APIs.

    Supports multiple authentication methods, pagination strategies,
    and response formats (JSON, XML).

    Attributes:
        user_agent: User-Agent string for HTTP requests
        tenant_id: Multi-tenant identifier
        rate_limit_delay: Delay between requests (seconds)
        timeout: Request timeout (seconds)
        max_retries: Maximum retry attempts
        max_items: Maximum items to fetch

    Example:
        >>> adapter = APIFetchAdapter(
        ...     user_agent="MyApp/1.0",
        ...     tenant_id="tenant-123",
        ...     rate_limit_delay=0.5,
        ...     timeout=30.0
        ... )
        >>> documents = await adapter.fetch(
        ...     url="https://api.example.com/data",
        ...     auth_type="bearer",
        ...     bearer_token="token-abc"
        ... )
    """

    def __init__(
        self,
        user_agent: str = "Rake/1.0 (API Integration Bot)",
        tenant_id: Optional[str] = None,
        rate_limit_delay: float = 0.5,
        timeout: float = 30.0,
        max_retries: int = 3,
        max_items: int = 100,
        verify_ssl: bool = True
    ):
        """Initialize API fetch adapter.

        Args:
            user_agent: User-Agent header for requests
            tenant_id: Multi-tenant identifier
            rate_limit_delay: Delay between requests in seconds
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            max_items: Maximum items to fetch per job
            verify_ssl: Verify SSL certificates

        Example:
            >>> adapter = APIFetchAdapter(
            ...     user_agent="CustomBot/2.0",
            ...     tenant_id="tenant-456",
            ...     rate_limit_delay=1.0
            ... )
        """
        super().__init__(tenant_id=tenant_id)
        self.source_type = DocumentSource.API_FETCH
        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_items = max_items
        self.verify_ssl = verify_ssl
        self.logger = logging.getLogger(__name__)

        # HTTP client
        self.client = httpx.AsyncClient(
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
            follow_redirects=True,
            verify=self.verify_ssl
        )

        self.logger.info(
            f"APIFetchAdapter initialized with rate_limit={rate_limit_delay}s, "
            f"timeout={timeout}s, max_items={max_items}"
        )

    async def _validate_input(
        self,
        url: Optional[str] = None,
        auth_type: Optional[str] = None,
        **kwargs
    ) -> None:
        """Validate input parameters.

        Args:
            url: API endpoint URL
            auth_type: Authentication type
            **kwargs: Additional parameters

        Raises:
            ValidationError: If validation fails

        Example:
            >>> await adapter._validate_input(
            ...     url="https://api.example.com/data",
            ...     auth_type="api_key"
            ... )
        """
        if not url:
            raise ValidationError("URL is required for API fetch")

        if not url.startswith(("http://", "https://")):
            raise ValidationError(f"Invalid URL format: {url}")

        # Validate auth type
        valid_auth_types = ["none", "api_key", "bearer", "basic", "custom"]
        if auth_type and auth_type not in valid_auth_types:
            raise ValidationError(
                f"Invalid auth_type: {auth_type}. "
                f"Must be one of {valid_auth_types}"
            )

        # Validate auth parameters based on type
        if auth_type == "api_key":
            if not kwargs.get("api_key"):
                raise ValidationError("api_key is required for api_key auth")
            if not kwargs.get("auth_location"):
                raise ValidationError(
                    "auth_location is required for api_key auth (header or query)"
                )

        elif auth_type == "bearer":
            if not kwargs.get("bearer_token"):
                raise ValidationError("bearer_token is required for bearer auth")

        elif auth_type == "basic":
            if not kwargs.get("username") or not kwargs.get("password"):
                raise ValidationError(
                    "username and password are required for basic auth"
                )

    def _build_headers(
        self,
        auth_type: str = "none",
        api_key: Optional[str] = None,
        api_key_name: str = "X-API-Key",
        bearer_token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        **kwargs
    ) -> Dict[str, str]:
        """Build HTTP headers including authentication.

        Args:
            auth_type: Authentication type
            api_key: API key for api_key auth
            api_key_name: Header name for API key
            bearer_token: Token for bearer auth
            custom_headers: Additional custom headers
            **kwargs: Additional parameters

        Returns:
            Dict of HTTP headers

        Example:
            >>> headers = adapter._build_headers(
            ...     auth_type="bearer",
            ...     bearer_token="abc123"
            ... )
        """
        headers = {"User-Agent": self.user_agent}

        # Authentication
        if auth_type == "api_key" and kwargs.get("auth_location") == "header":
            headers[api_key_name] = api_key

        elif auth_type == "bearer":
            headers["Authorization"] = f"Bearer {bearer_token}"

        # Custom headers
        if custom_headers:
            headers.update(custom_headers)

        return headers

    def _build_url(
        self,
        base_url: str,
        query_params: Optional[Dict[str, Any]] = None,
        auth_type: str = "none",
        api_key: Optional[str] = None,
        api_key_name: str = "api_key",
        **kwargs
    ) -> str:
        """Build complete URL with query parameters.

        Args:
            base_url: Base API URL
            query_params: Query parameters to add
            auth_type: Authentication type
            api_key: API key for api_key auth
            api_key_name: Query param name for API key
            **kwargs: Additional parameters

        Returns:
            Complete URL with query string

        Example:
            >>> url = adapter._build_url(
            ...     base_url="https://api.example.com/data",
            ...     query_params={"limit": 10}
            ... )
        """
        params = query_params.copy() if query_params else {}

        # Add API key to query params if needed
        if auth_type == "api_key" and kwargs.get("auth_location") == "query":
            params[api_key_name] = api_key

        if params:
            query_string = urlencode(params)
            return f"{base_url}?{query_string}"

        return base_url

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Dict[str, Any]] = None,
        basic_auth: Optional[tuple] = None
    ) -> httpx.Response:
        """Make HTTP request to API.

        Args:
            url: Request URL
            method: HTTP method
            headers: Request headers
            body: Request body (for POST/PUT)
            basic_auth: (username, password) tuple for basic auth

        Returns:
            HTTP response

        Raises:
            FetchError: If request fails

        Example:
            >>> response = await adapter._make_request(
            ...     url="https://api.example.com/data",
            ...     method="GET",
            ...     headers={"X-API-Key": "secret"}
            ... )
        """
        try:
            self.logger.debug(f"Making {method} request to {url}")

            if method.upper() == "GET":
                response = await self.client.get(
                    url,
                    headers=headers,
                    auth=basic_auth
                )
            elif method.upper() == "POST":
                response = await self.client.post(
                    url,
                    headers=headers,
                    json=body,
                    auth=basic_auth
                )
            elif method.upper() == "PUT":
                response = await self.client.put(
                    url,
                    headers=headers,
                    json=body,
                    auth=basic_auth
                )
            elif method.upper() == "PATCH":
                response = await self.client.patch(
                    url,
                    headers=headers,
                    json=body,
                    auth=basic_auth
                )
            elif method.upper() == "DELETE":
                response = await self.client.delete(
                    url,
                    headers=headers,
                    auth=basic_auth
                )
            else:
                raise FetchError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response

        except httpx.HTTPStatusError as e:
            raise FetchError(
                f"HTTP {e.response.status_code} error: {str(e)}",
                status_code=e.response.status_code,
                url=url
            )
        except httpx.TimeoutException:
            raise FetchError(f"Request timeout after {self.timeout}s", url=url)
        except httpx.RequestError as e:
            raise FetchError(f"Request error: {str(e)}", url=url)

    def _parse_json_response(
        self,
        response: httpx.Response,
        data_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Parse JSON response and extract data.

        Args:
            response: HTTP response
            data_path: Dot-notation path to data (e.g., "data.items")

        Returns:
            List of data items

        Raises:
            FetchError: If parsing fails

        Example:
            >>> items = adapter._parse_json_response(
            ...     response,
            ...     data_path="data.articles"
            ... )
        """
        try:
            data = response.json()

            # Navigate to data using path
            if data_path:
                for key in data_path.split("."):
                    if isinstance(data, dict):
                        data = data.get(key, [])
                    else:
                        break

            # Ensure data is a list
            if isinstance(data, dict):
                return [data]
            elif isinstance(data, list):
                return data
            else:
                return [{"content": str(data)}]

        except json.JSONDecodeError as e:
            raise FetchError(f"Invalid JSON response: {str(e)}")

    def _parse_xml_response(
        self,
        response: httpx.Response,
        item_tag: str = "item"
    ) -> List[Dict[str, Any]]:
        """Parse XML response and extract data.

        Args:
            response: HTTP response
            item_tag: XML tag name for items

        Returns:
            List of data items

        Raises:
            FetchError: If parsing fails

        Example:
            >>> items = adapter._parse_xml_response(
            ...     response,
            ...     item_tag="article"
            ... )
        """
        try:
            root = ET.fromstring(response.text)

            items = []
            for item in root.findall(f".//{item_tag}"):
                item_data = {}
                for child in item:
                    item_data[child.tag] = child.text or ""
                items.append(item_data)

            return items

        except ET.ParseError as e:
            raise FetchError(f"Invalid XML response: {str(e)}")

    def _extract_pagination_info(
        self,
        response: httpx.Response,
        pagination_type: str = "none",
        next_page_path: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """Extract next page URL from response.

        Args:
            response: HTTP response
            pagination_type: Pagination strategy
            next_page_path: JSON path to next page URL
            **kwargs: Additional parameters

        Returns:
            Next page URL or None

        Example:
            >>> next_url = adapter._extract_pagination_info(
            ...     response,
            ...     pagination_type="link_header"
            ... )
        """
        if pagination_type == "none":
            return None

        elif pagination_type == "link_header":
            # Parse Link header
            link_header = response.headers.get("Link", "")
            for link in link_header.split(","):
                if 'rel="next"' in link:
                    url = link.split(";")[0].strip("<>")
                    return url

        elif pagination_type == "json_path":
            # Extract from JSON response
            try:
                data = response.json()
                if next_page_path:
                    for key in next_page_path.split("."):
                        data = data.get(key) if isinstance(data, dict) else None
                    return data
            except (json.JSONDecodeError, AttributeError):
                pass

        return None

    def _convert_to_document(
        self,
        item: Dict[str, Any],
        source_url: str,
        content_field: str = "content",
        title_field: str = "title",
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Convert API response item to RawDocument.

        Args:
            item: Data item from API response
            source_url: Source API URL
            content_field: Field name containing content
            title_field: Field name containing title
            additional_metadata: Additional metadata to attach

        Returns:
            RawDocument instance

        Example:
            >>> doc = adapter._convert_to_document(
            ...     item={"title": "Article", "body": "Content"},
            ...     source_url="https://api.example.com/articles",
            ...     content_field="body"
            ... )
        """
        # Extract content
        content = item.get(content_field, "")
        if not content:
            # Try common content field names
            for field in ["body", "text", "description", "summary"]:
                if field in item:
                    content = item[field]
                    break

        # If still no content, serialize the entire item
        if not content:
            content = json.dumps(item, indent=2)

        # Build metadata
        metadata = {
            "source_url": source_url,
            "title": item.get(title_field, ""),
            "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "api_response": item,
        }

        # Add additional metadata
        if additional_metadata:
            metadata.update(additional_metadata)

        # Create document
        doc = RawDocument(
            id=f"api-{uuid4().hex[:12]}",
            content=str(content),
            source=self.source_type,
            metadata=metadata,
            tenant_id=self.tenant_id
        )

        return doc

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        auth_type: str = "none",
        api_key: Optional[str] = None,
        api_key_name: str = "X-API-Key",
        auth_location: str = "header",
        bearer_token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        body: Optional[Dict[str, Any]] = None,
        response_format: str = "json",
        data_path: Optional[str] = None,
        xml_item_tag: str = "item",
        content_field: str = "content",
        title_field: str = "title",
        pagination_type: str = "none",
        next_page_path: Optional[str] = None,
        max_pages: int = 10,
        **kwargs
    ) -> List[RawDocument]:
        """Fetch data from API endpoint.

        Args:
            url: API endpoint URL
            method: HTTP method (GET, POST, PUT, etc.)
            auth_type: Authentication type (none, api_key, bearer, basic, custom)
            api_key: API key for api_key auth
            api_key_name: Header/query param name for API key
            auth_location: Where to put API key (header or query)
            bearer_token: Token for bearer auth
            username: Username for basic auth
            password: Password for basic auth
            custom_headers: Additional HTTP headers
            query_params: Query parameters
            body: Request body for POST/PUT
            response_format: Response format (json or xml)
            data_path: JSON path to data (e.g., "data.items")
            xml_item_tag: XML tag name for items
            content_field: Field name containing content
            title_field: Field name containing title
            pagination_type: Pagination strategy (none, link_header, json_path, offset)
            next_page_path: JSON path to next page URL
            max_pages: Maximum pages to fetch
            **kwargs: Additional parameters

        Returns:
            List of RawDocument objects

        Raises:
            FetchError: If fetch fails
            ValidationError: If validation fails

        Example:
            >>> documents = await adapter.fetch(
            ...     url="https://api.example.com/articles",
            ...     auth_type="bearer",
            ...     bearer_token="secret-token",
            ...     response_format="json",
            ...     data_path="data.articles",
            ...     pagination_type="json_path",
            ...     next_page_path="pagination.next",
            ...     max_pages=5
            ... )
        """
        # Validate inputs
        await self._validate_input(
            url=url,
            auth_type=auth_type,
            api_key=api_key,
            auth_location=auth_location,
            bearer_token=bearer_token,
            username=username,
            password=password,
            **kwargs
        )

        all_documents = []
        current_url = url
        pages_fetched = 0

        while current_url and pages_fetched < max_pages:
            # Build headers
            headers = self._build_headers(
                auth_type=auth_type,
                api_key=api_key,
                api_key_name=api_key_name,
                bearer_token=bearer_token,
                custom_headers=custom_headers,
                auth_location=auth_location
            )

            # Build URL with query params
            request_url = self._build_url(
                base_url=current_url,
                query_params=query_params,
                auth_type=auth_type,
                api_key=api_key,
                api_key_name=api_key_name,
                auth_location=auth_location
            )

            # Basic auth tuple
            basic_auth = None
            if auth_type == "basic":
                basic_auth = (username, password)

            # Make request
            response = await self._make_request(
                url=request_url,
                method=method,
                headers=headers,
                body=body,
                basic_auth=basic_auth
            )

            # Parse response
            if response_format == "json":
                items = self._parse_json_response(response, data_path)
            elif response_format == "xml":
                items = self._parse_xml_response(response, xml_item_tag)
            else:
                raise ValidationError(
                    f"Invalid response_format: {response_format}. "
                    "Must be 'json' or 'xml'"
                )

            self.logger.info(f"Fetched {len(items)} items from {request_url}")

            # Convert items to documents
            for item in items:
                if len(all_documents) >= self.max_items:
                    self.logger.warning(
                        f"Reached max_items limit ({self.max_items}), stopping"
                    )
                    return all_documents

                doc = self._convert_to_document(
                    item=item,
                    source_url=url,
                    content_field=content_field,
                    title_field=title_field,
                    additional_metadata={"page": pages_fetched + 1}
                )
                all_documents.append(doc)

            pages_fetched += 1

            # Get next page URL
            current_url = self._extract_pagination_info(
                response=response,
                pagination_type=pagination_type,
                next_page_path=next_page_path
            )

            # Rate limiting
            if current_url:
                await self._rate_limit()

        self.logger.info(
            f"Completed API fetch: {len(all_documents)} documents "
            f"from {pages_fetched} pages"
        )

        return all_documents

    async def _rate_limit(self) -> None:
        """Apply rate limiting delay.

        Example:
            >>> await adapter._rate_limit()
        """
        if self.rate_limit_delay > 0:
            await self.client.aclose()
            await asyncio.sleep(self.rate_limit_delay)
            self.client = httpx.AsyncClient(
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
                follow_redirects=True,
                verify=self.verify_ssl
            )

    async def health_check(self) -> bool:
        """Check if HTTP client is working.

        Returns:
            True if healthy, False otherwise

        Example:
            >>> is_healthy = await adapter.health_check()
        """
        try:
            # Test with a simple request to a reliable endpoint
            response = await self.client.get("https://httpbin.org/status/200")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Health check failed: {str(e)}")
            return False

    def get_supported_formats(self) -> List[str]:
        """Get list of supported response formats.

        Returns:
            List of format identifiers

        Example:
            >>> formats = adapter.get_supported_formats()
            >>> print(formats)
            ['json', 'xml']
        """
        return ["json", "xml"]

    def get_supported_auth_types(self) -> List[str]:
        """Get list of supported authentication types.

        Returns:
            List of auth type identifiers

        Example:
            >>> auth_types = adapter.get_supported_auth_types()
            >>> print(auth_types)
            ['none', 'api_key', 'bearer', 'basic', 'custom']
        """
        return ["none", "api_key", "bearer", "basic", "custom"]

    def get_supported_pagination_types(self) -> List[str]:
        """Get list of supported pagination strategies.

        Returns:
            List of pagination type identifiers

        Example:
            >>> pagination_types = adapter.get_supported_pagination_types()
            >>> print(pagination_types)
            ['none', 'link_header', 'json_path', 'offset']
        """
        return ["none", "link_header", "json_path", "offset"]

    async def close(self) -> None:
        """Close HTTP client connection.

        Example:
            >>> await adapter.close()
        """
        await self.client.aclose()


# Import asyncio for rate limiting
import asyncio
