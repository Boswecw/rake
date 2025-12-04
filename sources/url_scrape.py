"""
URL Scraping Source Adapter

Fetches and extracts content from web pages, articles, and documentation sites.
Supports single URLs, sitemap parsing, and link following with depth control.

Supported content types:
    - HTML pages (articles, blogs, documentation)
    - XML sitemaps (bulk scraping)
    - RSS/Atom feeds
    - Plain text pages

Features:
    - Robots.txt compliance
    - Rate limiting per domain
    - Metadata extraction (title, description, author, date)
    - Link extraction and following
    - Content cleaning and normalization
    - User-Agent customization

Example:
    >>> from sources.url_scrape import URLScrapeAdapter
    >>> adapter = URLScrapeAdapter(
    ...     user_agent="MyBot/1.0 (contact@example.com)",
    ...     tenant_id="tenant-123"
    ... )
    >>> # Scrape single URL
    >>> documents = await adapter.fetch(url="https://example.com/article")
    >>> # Scrape sitemap
    >>> documents = await adapter.fetch(
    ...     sitemap_url="https://example.com/sitemap.xml",
    ...     max_pages=10
    ... )
"""

import asyncio
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
import logging

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for URL scraping adapter. "
        "Install with: pip install httpx"
    )

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "beautifulsoup4 is required for URL scraping adapter. "
        "Install with: pip install beautifulsoup4 lxml"
    )

from models.document import RawDocument, DocumentSource
from sources.base import BaseSourceAdapter, FetchError, ValidationError

logger = logging.getLogger(__name__)


class URLScrapeAdapter(BaseSourceAdapter):
    """Adapter for scraping content from web pages.

    Handles HTML content extraction, metadata parsing, and link following
    with rate limiting and robots.txt compliance.

    Attributes:
        user_agent: User-Agent string for HTTP requests
        rate_limit_delay: Delay between requests to same domain (seconds)
        max_content_size: Maximum page size to download (bytes)
        timeout: Request timeout in seconds
        follow_links: Whether to follow links (for crawling)
        max_depth: Maximum crawl depth when following links
        respect_robots: Whether to check robots.txt

    Example:
        >>> adapter = URLScrapeAdapter(
        ...     user_agent="MyBot/1.0",
        ...     tenant_id="tenant-123",
        ...     rate_limit_delay=1.0  # 1 second between requests
        ... )
        >>> docs = await adapter.fetch(url="https://example.com")
    """

    def __init__(
        self,
        user_agent: str = "Rake/1.0 (Data Ingestion Bot)",
        tenant_id: Optional[str] = None,
        rate_limit_delay: float = 1.0,
        max_content_size: int = 10 * 1024 * 1024,  # 10MB
        timeout: float = 30.0,
        follow_links: bool = False,
        max_depth: int = 1,
        respect_robots: bool = True
    ):
        """Initialize URL scrape adapter.

        Args:
            user_agent: User-Agent string for requests
            tenant_id: Multi-tenant identifier
            rate_limit_delay: Delay between requests to same domain (seconds)
            max_content_size: Maximum page size in bytes
            timeout: Request timeout in seconds
            follow_links: Whether to follow links
            max_depth: Maximum crawl depth
            respect_robots: Whether to check robots.txt

        Example:
            >>> adapter = URLScrapeAdapter(
            ...     user_agent="MyApp/1.0",
            ...     rate_limit_delay=2.0,  # 2 seconds between requests
            ...     max_content_size=5 * 1024 * 1024  # 5MB limit
            ... )
        """
        super().__init__(
            source_type=DocumentSource.URL_SCRAPE,
            tenant_id=tenant_id
        )

        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.max_content_size = max_content_size
        self.timeout = timeout
        self.follow_links = follow_links
        self.max_depth = max_depth
        self.respect_robots = respect_robots

        # Track last request time per domain for rate limiting
        self._last_request_per_domain: Dict[str, float] = {}

        # Track visited URLs to avoid duplicates
        self._visited_urls: Set[str] = set()

        # HTTP client
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
            },
            timeout=self.timeout,
            follow_redirects=True,
            max_redirects=5
        )

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL for rate limiting.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., "example.com")

        Example:
            >>> adapter._get_domain("https://example.com/page")
            'example.com'
        """
        parsed = urlparse(url)
        return parsed.netloc

    async def _rate_limit(self, url: str):
        """Enforce rate limiting per domain.

        Args:
            url: URL to rate limit

        Example:
            >>> await adapter._rate_limit("https://example.com/page")
        """
        domain = self._get_domain(url)
        current_time = asyncio.get_event_loop().time()

        if domain in self._last_request_per_domain:
            time_since_last = current_time - self._last_request_per_domain[domain]
            if time_since_last < self.rate_limit_delay:
                await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self._last_request_per_domain[domain] = asyncio.get_event_loop().time()

    async def _check_robots_txt(self, url: str) -> bool:
        """Check if URL is allowed by robots.txt.

        Args:
            url: URL to check

        Returns:
            True if allowed, False if disallowed

        Example:
            >>> allowed = await adapter._check_robots_txt("https://example.com/page")
        """
        if not self.respect_robots:
            return True

        try:
            parsed = urlparse(url)
            robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"

            await self._rate_limit(robots_url)
            response = await self.client.get(robots_url)

            if response.status_code == 200:
                # Simple robots.txt parsing (basic implementation)
                robots_content = response.text
                user_agent_section = False
                for line in robots_content.split('\n'):
                    line = line.strip().lower()
                    if line.startswith('user-agent:'):
                        ua = line.split(':', 1)[1].strip()
                        user_agent_section = ua == '*' or ua in self.user_agent.lower()
                    elif user_agent_section and line.startswith('disallow:'):
                        path = line.split(':', 1)[1].strip()
                        if path and parsed.path.startswith(path):
                            self.logger.warning(
                                f"URL disallowed by robots.txt: {url}",
                                extra={"url": url, "disallowed_path": path}
                            )
                            return False

            return True

        except Exception as e:
            self.logger.warning(
                f"Failed to check robots.txt: {str(e)}",
                extra={"url": url, "error": str(e)}
            )
            # If robots.txt check fails, allow scraping (permissive)
            return True

    async def _fetch_url_content(self, url: str) -> tuple[str, Dict[str, Any]]:
        """Fetch and parse content from a single URL.

        Args:
            url: URL to fetch

        Returns:
            Tuple of (content, metadata)

        Raises:
            FetchError: If fetching fails

        Example:
            >>> content, metadata = await adapter._fetch_url_content("https://example.com")
        """
        await self._rate_limit(url)

        try:
            self.logger.info(
                f"Fetching URL: {url}",
                extra={"url": url}
            )

            response = await self.client.get(url)
            response.raise_for_status()

            # Check content size
            content_length = len(response.content)
            if content_length > self.max_content_size:
                raise FetchError(
                    f"Content too large: {content_length} bytes (max: {self.max_content_size})",
                    source=self.source_type.value,
                    url=url,
                    content_size=content_length
                )

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract metadata
            metadata = self._extract_metadata(soup, url)
            metadata['url'] = url
            metadata['status_code'] = response.status_code
            metadata['content_type'] = response.headers.get('content-type', '')
            metadata['content_length'] = content_length

            # Extract main content
            content = self._extract_content(soup)

            self.logger.info(
                f"Successfully fetched {len(content)} characters from {url}",
                extra={
                    "url": url,
                    "content_length": len(content),
                    "title": metadata.get('title')
                }
            )

            return content, metadata

        except httpx.HTTPError as e:
            raise FetchError(
                f"Failed to fetch URL: {str(e)}",
                source=self.source_type.value,
                url=url,
                error=str(e)
            )

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract metadata from HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            url: Source URL

        Returns:
            Dictionary of metadata

        Example:
            >>> metadata = adapter._extract_metadata(soup, "https://example.com")
        """
        metadata: Dict[str, Any] = {}

        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text().strip()

        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name', '').lower()
            property_name = meta.get('property', '').lower()
            content = meta.get('content', '')

            if name == 'description' or property_name == 'og:description':
                metadata['description'] = content
            elif name == 'author':
                metadata['author'] = content
            elif name == 'keywords':
                metadata['keywords'] = content
            elif property_name == 'og:title':
                metadata.setdefault('title', content)
            elif property_name == 'og:type':
                metadata['type'] = content
            elif name == 'published_time' or property_name == 'article:published_time':
                metadata['published_date'] = content

        # Canonical URL
        canonical = soup.find('link', {'rel': 'canonical'})
        if canonical:
            metadata['canonical_url'] = canonical.get('href')

        # Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata['language'] = html_tag.get('lang')

        return metadata

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from HTML.

        Args:
            soup: BeautifulSoup parsed HTML

        Returns:
            Extracted text content

        Example:
            >>> content = adapter._extract_content(soup)
        """
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'header', 'footer',
                            'aside', 'iframe', 'noscript']):
            element.decompose()

        # Try to find main content area
        main_content = None

        # Common content selectors (in order of preference)
        content_selectors = [
            'article',
            'main',
            '[role="main"]',
            '.content',
            '#content',
            '.post-content',
            '.article-content',
            '.entry-content',
        ]

        for selector in content_selectors:
            main_content = soup.select_one(selector)
            if main_content:
                break

        # If no main content found, use body
        if not main_content:
            main_content = soup.find('body')

        if not main_content:
            main_content = soup

        # Extract text
        text = main_content.get_text(separator='\n', strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        content = '\n'.join(lines)

        return content

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """Extract links from HTML.

        Args:
            soup: BeautifulSoup parsed HTML
            base_url: Base URL for resolving relative links

        Returns:
            List of absolute URLs

        Example:
            >>> links = adapter._extract_links(soup, "https://example.com")
        """
        links = []
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Resolve relative URLs
            absolute_url = urljoin(base_url, href)
            # Only include HTTP(S) links
            if absolute_url.startswith(('http://', 'https://')):
                links.append(absolute_url)

        return links

    async def _parse_sitemap(self, sitemap_url: str, max_pages: int = 100) -> List[str]:
        """Parse XML sitemap and extract URLs.

        Args:
            sitemap_url: URL to sitemap.xml
            max_pages: Maximum number of URLs to extract

        Returns:
            List of URLs from sitemap

        Example:
            >>> urls = await adapter._parse_sitemap("https://example.com/sitemap.xml")
        """
        await self._rate_limit(sitemap_url)

        try:
            self.logger.info(
                f"Parsing sitemap: {sitemap_url}",
                extra={"sitemap_url": sitemap_url, "max_pages": max_pages}
            )

            response = await self.client.get(sitemap_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'xml')
            urls = []

            # Extract URLs from sitemap
            for loc in soup.find_all('loc'):
                url = loc.get_text().strip()
                if url:
                    urls.append(url)
                    if len(urls) >= max_pages:
                        break

            self.logger.info(
                f"Found {len(urls)} URLs in sitemap",
                extra={"sitemap_url": sitemap_url, "url_count": len(urls)}
            )

            return urls

        except Exception as e:
            raise FetchError(
                f"Failed to parse sitemap: {str(e)}",
                source=self.source_type.value,
                sitemap_url=sitemap_url,
                error=str(e)
            )

    async def validate_input(
        self,
        url: Optional[str] = None,
        sitemap_url: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Validate input parameters.

        Args:
            url: Single URL to scrape
            sitemap_url: Sitemap URL for bulk scraping
            **kwargs: Additional arguments

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails

        Example:
            >>> await adapter.validate_input(url="https://example.com")
        """
        # Must provide either url or sitemap_url
        if not url and not sitemap_url:
            raise ValidationError(
                "Must provide either 'url' or 'sitemap_url' parameter",
                source=self.source_type.value
            )

        # Validate URL format
        if url:
            if not url.startswith(('http://', 'https://')):
                raise ValidationError(
                    f"Invalid URL format: {url}. Must start with http:// or https://",
                    source=self.source_type.value,
                    url=url
                )

        if sitemap_url:
            if not sitemap_url.startswith(('http://', 'https://')):
                raise ValidationError(
                    f"Invalid sitemap URL format: {sitemap_url}",
                    source=self.source_type.value,
                    sitemap_url=sitemap_url
                )

        return True

    async def fetch(
        self,
        url: Optional[str] = None,
        sitemap_url: Optional[str] = None,
        max_pages: int = 10,
        **kwargs
    ) -> List[RawDocument]:
        """Fetch documents from URLs.

        Args:
            url: Single URL to scrape
            sitemap_url: Sitemap URL for bulk scraping
            max_pages: Maximum number of pages to scrape (for sitemap)
            **kwargs: Additional metadata to include

        Returns:
            List of RawDocument objects

        Raises:
            ValidationError: If input validation fails
            FetchError: If fetching fails

        Example:
            >>> # Single URL
            >>> docs = await adapter.fetch(url="https://example.com/article")
            >>>
            >>> # Sitemap
            >>> docs = await adapter.fetch(
            ...     sitemap_url="https://example.com/sitemap.xml",
            ...     max_pages=5
            ... )
        """
        # Validate input
        await self.validate_input(url=url, sitemap_url=sitemap_url)

        # Clear visited URLs for new fetch
        self._visited_urls.clear()

        try:
            documents = []

            # Sitemap mode: fetch multiple URLs
            if sitemap_url:
                urls = await self._parse_sitemap(sitemap_url, max_pages=max_pages)

                for page_url in urls:
                    # Check robots.txt
                    if not await self._check_robots_txt(page_url):
                        self.logger.warning(
                            f"Skipping URL (robots.txt): {page_url}",
                            extra={"url": page_url}
                        )
                        continue

                    # Skip if already visited
                    if page_url in self._visited_urls:
                        continue

                    self._visited_urls.add(page_url)

                    try:
                        content, metadata = await self._fetch_url_content(page_url)

                        # Add sitemap metadata
                        metadata['from_sitemap'] = True
                        metadata['sitemap_url'] = sitemap_url
                        metadata.update(kwargs)

                        # Create document
                        doc = self._create_raw_document(
                            content=content,
                            url=page_url,
                            metadata=metadata
                        )
                        documents.append(doc)

                    except FetchError as e:
                        self.logger.error(
                            f"Failed to fetch URL from sitemap: {str(e)}",
                            extra={"url": page_url, "error": str(e)}
                        )
                        # Continue with other URLs
                        continue

            # Single URL mode
            elif url:
                # Check robots.txt
                if not await self._check_robots_txt(url):
                    raise FetchError(
                        f"URL disallowed by robots.txt: {url}",
                        source=self.source_type.value,
                        url=url
                    )

                content, metadata = await self._fetch_url_content(url)
                metadata.update(kwargs)

                # Create document
                doc = self._create_raw_document(
                    content=content,
                    url=url,
                    metadata=metadata
                )
                documents.append(doc)

            if not documents:
                raise FetchError(
                    "No documents were successfully fetched",
                    source=self.source_type.value,
                    url=url,
                    sitemap_url=sitemap_url
                )

            self.logger.info(
                f"Successfully fetched {len(documents)} document(s)",
                extra={
                    "document_count": len(documents),
                    "url": url,
                    "sitemap_url": sitemap_url
                }
            )

            return documents

        except Exception as e:
            if isinstance(e, (FetchError, ValidationError)):
                raise

            error_msg = f"Failed to fetch URLs: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "sitemap_url": sitemap_url,
                    "error": str(e)
                },
                exc_info=True
            )
            raise FetchError(
                error_msg,
                source=self.source_type.value,
                url=url,
                sitemap_url=sitemap_url,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Check if HTTP client is functional.

        Returns:
            True if client is healthy, False otherwise

        Example:
            >>> is_healthy = await adapter.health_check()
        """
        try:
            # Simple HTTP request to check connectivity
            response = await self.client.get("https://httpbin.org/get", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                f"Health check failed: {str(e)}",
                extra={"error": str(e)}
            )
            return False

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_url_scraper():
        """Test URL scraper adapter."""
        adapter = URLScrapeAdapter(
            user_agent="TestBot/1.0 (test@example.com)",
            tenant_id="tenant-test",
            rate_limit_delay=1.0
        )

        try:
            print("Testing URL scraper...\n")

            # Test single URL
            print("1. Fetching single URL...")
            docs = await adapter.fetch(url="https://example.com")

            print(f"   Fetched {len(docs)} document(s)")
            for doc in docs:
                print(f"   - Title: {doc.metadata.get('title')}")
                print(f"   - URL: {doc.metadata.get('url')}")
                print(f"   - Content length: {len(doc.content)} characters")
                print(f"   - Preview: {doc.content[:200]}...")

            print("\n2. Health check...")
            is_healthy = await adapter.health_check()
            print(f"   Adapter healthy: {is_healthy}")

        finally:
            await adapter.client.aclose()

    asyncio.run(test_url_scraper())
