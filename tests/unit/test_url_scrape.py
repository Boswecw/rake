"""Unit Tests for URL Scrape Source Adapter

Tests for URL scraping functionality including single URLs, sitemaps,
robots.txt compliance, and content extraction.

Run with:
    pytest tests/unit/test_url_scrape.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from datetime import datetime

from sources.url_scrape import URLScrapeAdapter
from sources.base import FetchError, ValidationError
from models.document import DocumentSource


class TestURLScrapeAdapterInit:
    """Tests for URL scraper adapter initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        assert adapter.user_agent == "Rake/1.0 (Data Ingestion Bot)"
        assert adapter.tenant_id == "tenant-123"
        assert adapter.source_type == DocumentSource.URL_SCRAPE
        assert adapter.rate_limit_delay == 1.0
        assert adapter.max_content_size == 10 * 1024 * 1024
        assert adapter.timeout == 30.0
        assert adapter.follow_links is False
        assert adapter.max_depth == 1
        assert adapter.respect_robots is True

    def test_init_with_custom_user_agent(self):
        """Test initialization with custom user-agent."""
        adapter = URLScrapeAdapter(
            user_agent="MyBot/2.0 (Custom Scraper)",
            tenant_id="tenant-123"
        )
        assert adapter.user_agent == "MyBot/2.0 (Custom Scraper)"

    def test_init_with_custom_rate_limit(self):
        """Test initialization with custom rate limit."""
        adapter = URLScrapeAdapter(
            tenant_id="tenant-123",
            rate_limit_delay=2.5
        )
        assert adapter.rate_limit_delay == 2.5

    def test_init_with_custom_max_size(self):
        """Test initialization with custom max content size."""
        adapter = URLScrapeAdapter(
            tenant_id="tenant-123",
            max_content_size=20 * 1024 * 1024  # 20MB
        )
        assert adapter.max_content_size == 20 * 1024 * 1024

    def test_init_with_follow_links(self):
        """Test initialization with link following enabled."""
        adapter = URLScrapeAdapter(
            tenant_id="tenant-123",
            follow_links=True,
            max_depth=3
        )
        assert adapter.follow_links is True
        assert adapter.max_depth == 3

    def test_init_with_robots_disabled(self):
        """Test initialization with robots.txt respect disabled."""
        adapter = URLScrapeAdapter(
            tenant_id="tenant-123",
            respect_robots=False
        )
        assert adapter.respect_robots is False


class TestValidateInput:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_validate_with_url(self):
        """Test validation with URL parameter."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        await adapter._validate_input(url="https://example.com")
        # Should not raise

    @pytest.mark.asyncio
    async def test_validate_with_sitemap_url(self):
        """Test validation with sitemap URL parameter."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        await adapter._validate_input(sitemap_url="https://example.com/sitemap.xml")
        # Should not raise

    @pytest.mark.asyncio
    async def test_validate_without_url_or_sitemap(self):
        """Test validation fails without URL or sitemap."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input()

        assert "url or sitemap_url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_with_invalid_url(self):
        """Test validation fails with malformed URL."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(url="not-a-valid-url")

        assert "invalid url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_with_non_http_url(self):
        """Test validation fails with non-HTTP(S) URL."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        with pytest.raises(ValidationError) as exc_info:
            await adapter._validate_input(url="ftp://example.com/file.txt")

        assert "http" in str(exc_info.value).lower()


class TestRobotsCompliance:
    """Tests for robots.txt compliance checking."""

    @pytest.mark.asyncio
    async def test_check_robots_allowed(self):
        """Test robots.txt allows crawling."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=True)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin/
Allow: /
"""

        with patch.object(adapter.client, 'get', return_value=mock_response):
            allowed = await adapter._check_robots_txt("https://example.com/page")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_check_robots_disallowed(self):
        """Test robots.txt disallows crawling."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=True)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /
"""

        with patch.object(adapter.client, 'get', return_value=mock_response):
            allowed = await adapter._check_robots_txt("https://example.com/page")
            assert allowed is False

    @pytest.mark.asyncio
    async def test_check_robots_not_found(self):
        """Test missing robots.txt allows crawling."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=True)

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(adapter.client, 'get', return_value=mock_response):
            allowed = await adapter._check_robots_txt("https://example.com/page")
            assert allowed is True

    @pytest.mark.asyncio
    async def test_check_robots_disabled(self):
        """Test robots.txt check skipped when disabled."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=False)

        # Should return True without making any HTTP call
        allowed = await adapter._check_robots_txt("https://example.com/page")
        assert allowed is True

    @pytest.mark.asyncio
    async def test_check_robots_error(self):
        """Test robots.txt check allows on error."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=True)

        with patch.object(adapter.client, 'get', side_effect=httpx.RequestError("Connection error")):
            allowed = await adapter._check_robots_txt("https://example.com/page")
            assert allowed is True


class TestExtractMetadata:
    """Tests for metadata extraction from HTML."""

    def test_extract_metadata_with_meta_tags(self):
        """Test metadata extraction from meta tags."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
                <meta name="author" content="John Doe">
                <meta name="keywords" content="test, example, demo">
                <meta property="og:type" content="article">
                <meta property="og:site_name" content="Example Site">
            </head>
            <body></body>
        </html>
        """

        metadata = adapter._extract_metadata(html, "https://example.com/test")

        assert metadata["title"] == "Test Page"
        assert metadata["description"] == "Test description"
        assert metadata["author"] == "John Doe"
        assert metadata["keywords"] == "test, example, demo"
        assert metadata["og_type"] == "article"
        assert metadata["og_site_name"] == "Example Site"
        assert metadata["url"] == "https://example.com/test"

    def test_extract_metadata_with_og_tags(self):
        """Test metadata extraction from Open Graph tags."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <head>
                <meta property="og:title" content="OG Title">
                <meta property="og:description" content="OG Description">
                <meta property="og:image" content="https://example.com/image.jpg">
                <meta property="og:url" content="https://example.com/canonical">
            </head>
            <body></body>
        </html>
        """

        metadata = adapter._extract_metadata(html, "https://example.com/test")

        assert metadata["og_title"] == "OG Title"
        assert metadata["og_description"] == "OG Description"
        assert metadata["og_image"] == "https://example.com/image.jpg"
        assert metadata["og_url"] == "https://example.com/canonical"

    def test_extract_metadata_with_twitter_tags(self):
        """Test metadata extraction from Twitter Card tags."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <head>
                <meta name="twitter:card" content="summary_large_image">
                <meta name="twitter:title" content="Twitter Title">
                <meta name="twitter:description" content="Twitter Description">
            </head>
            <body></body>
        </html>
        """

        metadata = adapter._extract_metadata(html, "https://example.com/test")

        assert metadata["twitter_card"] == "summary_large_image"
        assert metadata["twitter_title"] == "Twitter Title"
        assert metadata["twitter_description"] == "Twitter Description"

    def test_extract_metadata_no_tags(self):
        """Test metadata extraction with minimal HTML."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = "<html><body>Content</body></html>"
        metadata = adapter._extract_metadata(html, "https://example.com")

        assert metadata["url"] == "https://example.com"
        assert "fetched_at" in metadata


class TestExtractMainContent:
    """Tests for main content extraction."""

    def test_extract_with_article_tag(self):
        """Test content extraction from <article> tag."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <body>
                <nav>Navigation</nav>
                <article>
                    <h1>Article Title</h1>
                    <p>This is the main content.</p>
                </article>
                <footer>Footer</footer>
            </body>
        </html>
        """

        content = adapter._extract_main_content(html)
        assert "Article Title" in content
        assert "This is the main content." in content
        assert "Navigation" not in content
        assert "Footer" not in content

    def test_extract_with_main_tag(self):
        """Test content extraction from <main> tag."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <body>
                <header>Header</header>
                <main>
                    <h1>Main Content</h1>
                    <p>Primary content here.</p>
                </main>
                <aside>Sidebar</aside>
            </body>
        </html>
        """

        content = adapter._extract_main_content(html)
        assert "Main Content" in content
        assert "Primary content here." in content
        assert "Header" not in content
        assert "Sidebar" not in content

    def test_extract_with_role_main(self):
        """Test content extraction from role='main'."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <body>
                <div role="main">
                    <h1>Content with Role</h1>
                    <p>This uses ARIA role.</p>
                </div>
            </body>
        </html>
        """

        content = adapter._extract_main_content(html)
        assert "Content with Role" in content
        assert "This uses ARIA role." in content

    def test_extract_with_content_class(self):
        """Test content extraction from common content classes."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <body>
                <div class="content">
                    <h1>Class-based Content</h1>
                    <p>Content identified by class.</p>
                </div>
            </body>
        </html>
        """

        content = adapter._extract_main_content(html)
        assert "Class-based Content" in content
        assert "Content identified by class." in content

    def test_extract_fallback_to_body(self):
        """Test fallback to body text when no content selectors match."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <body>
                <h1>Simple Page</h1>
                <p>No semantic tags.</p>
            </body>
        </html>
        """

        content = adapter._extract_main_content(html)
        assert "Simple Page" in content
        assert "No semantic tags." in content


class TestParseSitemap:
    """Tests for sitemap parsing."""

    @pytest.mark.asyncio
    async def test_parse_sitemap_xml(self):
        """Test parsing XML sitemap."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>https://example.com/page1</loc>
                <lastmod>2023-01-01</lastmod>
            </url>
            <url>
                <loc>https://example.com/page2</loc>
                <lastmod>2023-01-02</lastmod>
            </url>
            <url>
                <loc>https://example.com/page3</loc>
                <lastmod>2023-01-03</lastmod>
            </url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sitemap_xml

        with patch.object(adapter.client, 'get', return_value=mock_response):
            urls = await adapter._parse_sitemap("https://example.com/sitemap.xml", max_pages=10)

            assert len(urls) == 3
            assert "https://example.com/page1" in urls
            assert "https://example.com/page2" in urls
            assert "https://example.com/page3" in urls

    @pytest.mark.asyncio
    async def test_parse_sitemap_with_max_pages(self):
        """Test sitemap parsing respects max_pages limit."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
            <url><loc>https://example.com/page3</loc></url>
            <url><loc>https://example.com/page4</loc></url>
            <url><loc>https://example.com/page5</loc></url>
        </urlset>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = sitemap_xml

        with patch.object(adapter.client, 'get', return_value=mock_response):
            urls = await adapter._parse_sitemap("https://example.com/sitemap.xml", max_pages=2)

            assert len(urls) == 2

    @pytest.mark.asyncio
    async def test_parse_sitemap_index(self):
        """Test parsing sitemap index file."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        sitemap_index = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap>
                <loc>https://example.com/sitemap1.xml</loc>
            </sitemap>
            <sitemap>
                <loc>https://example.com/sitemap2.xml</loc>
            </sitemap>
        </sitemapindex>
        """

        sitemap1_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
        </urlset>
        """

        sitemap2_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """

        async def mock_get(url):
            response = MagicMock()
            response.status_code = 200
            if "sitemap1.xml" in url:
                response.text = sitemap1_xml
            elif "sitemap2.xml" in url:
                response.text = sitemap2_xml
            else:
                response.text = sitemap_index
            return response

        with patch.object(adapter.client, 'get', side_effect=mock_get):
            urls = await adapter._parse_sitemap("https://example.com/sitemap.xml", max_pages=10)

            assert len(urls) == 2
            assert "https://example.com/page1" in urls
            assert "https://example.com/page2" in urls

    @pytest.mark.asyncio
    async def test_parse_sitemap_not_found(self):
        """Test sitemap parsing handles 404."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch.object(adapter.client, 'get', return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                await adapter._parse_sitemap("https://example.com/sitemap.xml", max_pages=10)

            assert "404" in str(exc_info.value)


class TestFetchURLContent:
    """Tests for fetching content from a single URL."""

    @pytest.mark.asyncio
    async def test_fetch_url_content_success(self):
        """Test successful URL content fetching."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <head>
                <title>Test Page</title>
                <meta name="description" content="Test description">
            </head>
            <body>
                <article>
                    <h1>Article Title</h1>
                    <p>Article content here.</p>
                </article>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html; charset=utf-8"}

        with patch.object(adapter.client, 'get', return_value=mock_response):
            content, metadata = await adapter._fetch_url_content("https://example.com/page")

            assert "Article Title" in content
            assert "Article content here." in content
            assert metadata["title"] == "Test Page"
            assert metadata["description"] == "Test description"
            assert metadata["url"] == "https://example.com/page"

    @pytest.mark.asyncio
    async def test_fetch_url_content_too_large(self):
        """Test content size limit enforcement."""
        adapter = URLScrapeAdapter(
            tenant_id="tenant-123",
            max_content_size=100  # 100 bytes
        )

        large_html = "<html><body>" + ("x" * 1000) + "</body></html>"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = large_html
        mock_response.headers = {"content-type": "text/html"}

        with patch.object(adapter.client, 'get', return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                await adapter._fetch_url_content("https://example.com/page")

            assert "too large" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_url_content_not_html(self):
        """Test non-HTML content type rejection."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Plain text content"
        mock_response.headers = {"content-type": "application/json"}

        with patch.object(adapter.client, 'get', return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                await adapter._fetch_url_content("https://example.com/api")

            assert "html" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_url_content_http_error(self):
        """Test handling of HTTP errors."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=mock_response
        )

        with patch.object(adapter.client, 'get', return_value=mock_response):
            with pytest.raises(FetchError) as exc_info:
                await adapter._fetch_url_content("https://example.com/error")

            assert "500" in str(exc_info.value) or "http" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_url_content_timeout(self):
        """Test timeout handling."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", timeout=1.0)

        with patch.object(adapter.client, 'get', side_effect=httpx.TimeoutException("Timeout")):
            with pytest.raises(FetchError) as exc_info:
                await adapter._fetch_url_content("https://example.com/slow")

            assert "timeout" in str(exc_info.value).lower()


class TestFetch:
    """Tests for the main fetch method."""

    @pytest.mark.asyncio
    async def test_fetch_single_url(self):
        """Test fetching a single URL."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <article>
                    <h1>Test Content</h1>
                    <p>Page content.</p>
                </article>
            </body>
        </html>
        """

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.headers = {"content-type": "text/html"}

        # Mock robots.txt check
        with patch.object(adapter, '_check_robots_txt', return_value=True):
            with patch.object(adapter.client, 'get', return_value=mock_response):
                documents = await adapter.fetch(url="https://example.com/page")

                assert len(documents) == 1
                doc = documents[0]
                assert "Test Content" in doc.content
                assert "Page content." in doc.content
                assert doc.metadata["title"] == "Test Page"
                assert doc.metadata["url"] == "https://example.com/page"
                assert doc.source == DocumentSource.URL_SCRAPE
                assert doc.tenant_id == "tenant-123"

    @pytest.mark.asyncio
    async def test_fetch_robots_blocked(self):
        """Test URL blocked by robots.txt."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", respect_robots=True)

        with patch.object(adapter, '_check_robots_txt', return_value=False):
            with pytest.raises(FetchError) as exc_info:
                await adapter.fetch(url="https://example.com/blocked")

            assert "robots.txt" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_fetch_sitemap(self):
        """Test fetching multiple URLs from sitemap."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
        </urlset>
        """

        page_html = """
        <html>
            <head><title>Page</title></head>
            <body><p>Content</p></body>
        </html>
        """

        async def mock_get(url):
            response = MagicMock()
            response.status_code = 200
            if "sitemap.xml" in url:
                response.text = sitemap_xml
            else:
                response.text = page_html
            response.headers = {"content-type": "text/html"}
            return response

        with patch.object(adapter, '_check_robots_txt', return_value=True):
            with patch.object(adapter.client, 'get', side_effect=mock_get):
                documents = await adapter.fetch(
                    sitemap_url="https://example.com/sitemap.xml",
                    max_pages=10
                )

                assert len(documents) == 2
                assert all(doc.source == DocumentSource.URL_SCRAPE for doc in documents)
                assert all(doc.tenant_id == "tenant-123" for doc in documents)

    @pytest.mark.asyncio
    async def test_fetch_with_rate_limiting(self):
        """Test rate limiting between requests."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123", rate_limit_delay=0.1)

        sitemap_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>https://example.com/page1</loc></url>
            <url><loc>https://example.com/page2</loc></url>
            <url><loc>https://example.com/page3</loc></url>
        </urlset>
        """

        page_html = "<html><body><p>Content</p></body></html>"

        call_times = []

        async def mock_get(url):
            call_times.append(datetime.now())
            response = MagicMock()
            response.status_code = 200
            if "sitemap.xml" in url:
                response.text = sitemap_xml
            else:
                response.text = page_html
            response.headers = {"content-type": "text/html"}
            return response

        with patch.object(adapter, '_check_robots_txt', return_value=True):
            with patch.object(adapter.client, 'get', side_effect=mock_get):
                await adapter.fetch(
                    sitemap_url="https://example.com/sitemap.xml",
                    max_pages=10
                )

                # Check that there's a delay between calls (at least 4 calls: sitemap + 3 pages)
                assert len(call_times) >= 4


class TestHealthCheck:
    """Tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch.object(adapter.client, 'get', return_value=mock_response):
            is_healthy = await adapter.health_check()
            assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")

        with patch.object(adapter.client, 'get', side_effect=httpx.RequestError("Connection failed")):
            is_healthy = await adapter.health_check()
            assert is_healthy is False


class TestGetSupportedFormats:
    """Tests for supported formats listing."""

    def test_get_supported_formats(self):
        """Test getting list of supported formats."""
        adapter = URLScrapeAdapter(tenant_id="tenant-123")
        formats = adapter.get_supported_formats()

        assert "html" in formats
        assert "text/html" in formats
        assert isinstance(formats, list)
        assert len(formats) > 0
