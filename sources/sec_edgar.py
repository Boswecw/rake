"""
SEC EDGAR Source Adapter

Fetches financial filings and documents from the SEC EDGAR database.
Supports company lookup by CIK or ticker symbol, and retrieval of various
filing types (10-K, 10-Q, 8-K, etc.).

The SEC requires:
1. User-Agent header with contact information
2. Rate limiting (10 requests per second maximum)
3. Fair access to the EDGAR system

Supported filing types:
    - 10-K: Annual reports
    - 10-Q: Quarterly reports
    - 8-K: Current reports
    - DEF 14A: Proxy statements
    - S-1: Registration statements
    - 13F: Institutional investment reports
    - And many more

Example:
    >>> from sources.sec_edgar import SECEdgarAdapter
    >>> adapter = SECEdgarAdapter(
    ...     user_agent="MyCompany support@mycompany.com",
    ...     tenant_id="tenant-123"
    ... )
    >>> # Fetch latest 10-K for Apple
    >>> documents = await adapter.fetch(
    ...     ticker="AAPL",
    ...     form_type="10-K",
    ...     count=1
    ... )
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

try:
    import httpx
except ImportError:
    raise ImportError(
        "httpx is required for SEC EDGAR adapter. "
        "Install with: pip install httpx"
    )

try:
    from bs4 import BeautifulSoup
except ImportError:
    raise ImportError(
        "beautifulsoup4 is required for SEC EDGAR adapter. "
        "Install with: pip install beautifulsoup4"
    )

from models.document import RawDocument, DocumentSource
from sources.base import BaseSourceAdapter, FetchError, ValidationError

logger = logging.getLogger(__name__)


class SECEdgarAdapter(BaseSourceAdapter):
    """Adapter for fetching documents from SEC EDGAR database.

    The SEC EDGAR system provides access to company filings submitted to the
    U.S. Securities and Exchange Commission. This adapter handles company lookup,
    filing retrieval, and text extraction.

    Attributes:
        user_agent: User-Agent string (required by SEC, must include contact info)
        rate_limit_delay: Delay between requests in seconds (default: 0.1 = 10 req/s)
        max_filing_size: Maximum filing size to download in bytes

    Example:
        >>> adapter = SECEdgarAdapter(
        ...     user_agent="Research Project contact@university.edu",
        ...     tenant_id="tenant-123"
        ... )
        >>> docs = await adapter.fetch(cik="0000320193", form_type="10-K")
    """

    # SEC EDGAR API endpoints
    EDGAR_BASE_URL = "https://www.sec.gov"
    EDGAR_SEARCH_API = f"{EDGAR_BASE_URL}/cgi-bin/browse-edgar"
    EDGAR_COMPANY_API = f"{EDGAR_BASE_URL}/cgi-bin/browse-edgar"
    EDGAR_SUBMISSIONS_API = f"{EDGAR_BASE_URL}/cgi-bin/browse-edgar"

    # Common filing types
    SUPPORTED_FORMS = [
        "10-K", "10-Q", "8-K",  # Common corporate filings
        "DEF 14A", "S-1", "S-3",  # Proxy and registration
        "13F-HR", "13D", "13G",  # Institutional holdings
        "4", "3", "5",  # Insider trading
        "20-F", "6-K",  # Foreign issuers
    ]

    def __init__(
        self,
        user_agent: str,
        tenant_id: Optional[str] = None,
        rate_limit_delay: float = 0.1,  # 10 requests/second
        max_filing_size: int = 50 * 1024 * 1024  # 50MB
    ):
        """Initialize SEC EDGAR adapter.

        Args:
            user_agent: User-Agent header (required by SEC, must include contact)
            tenant_id: Multi-tenant identifier
            rate_limit_delay: Delay between requests (default: 0.1s = 10 req/s)
            max_filing_size: Maximum filing size in bytes

        Raises:
            ValidationError: If user_agent doesn't include contact information

        Example:
            >>> adapter = SECEdgarAdapter(
            ...     user_agent="MyApp/1.0 admin@example.com",
            ...     tenant_id="tenant-123"
            ... )
        """
        super().__init__(
            source_type=DocumentSource.SEC_EDGAR,
            tenant_id=tenant_id
        )

        # Validate user-agent includes contact info
        if not self._validate_user_agent(user_agent):
            raise ValidationError(
                "User-Agent must include contact information (email or website). "
                "Example: 'MyCompany/1.0 contact@mycompany.com'",
                source=self.source_type.value,
                user_agent=user_agent
            )

        self.user_agent = user_agent
        self.rate_limit_delay = rate_limit_delay
        self.max_filing_size = max_filing_size
        self._last_request_time = 0.0

        # HTTP client with proper headers
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": self.user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Host": "www.sec.gov"
            },
            timeout=30.0,
            follow_redirects=True
        )

    def _validate_user_agent(self, user_agent: str) -> bool:
        """Validate user-agent includes contact information.

        SEC requires User-Agent to include company name and contact info.

        Args:
            user_agent: User-Agent string to validate

        Returns:
            True if valid, False otherwise

        Example:
            >>> adapter._validate_user_agent("MyApp admin@example.com")
            True
        """
        # Check for email or website
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        website_pattern = r'https?://[^\s]+'

        has_email = re.search(email_pattern, user_agent) is not None
        has_website = re.search(website_pattern, user_agent) is not None

        return has_email or has_website

    async def _rate_limit(self):
        """Enforce rate limiting (max 10 requests per second).

        SEC requires fair access with max 10 requests per second.

        Example:
            >>> await adapter._rate_limit()  # Ensures proper spacing
        """
        current_time = asyncio.get_event_loop().time()
        time_since_last = current_time - self._last_request_time

        if time_since_last < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - time_since_last)

        self._last_request_time = asyncio.get_event_loop().time()

    async def _get_cik_from_ticker(self, ticker: str) -> str:
        """Convert ticker symbol to CIK number.

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            CIK number as string (e.g., "0000320193")

        Raises:
            FetchError: If ticker not found or lookup fails

        Example:
            >>> cik = await adapter._get_cik_from_ticker("AAPL")
            >>> print(cik)
            0000320193
        """
        await self._rate_limit()

        url = f"{self.EDGAR_COMPANY_API}?action=getcompany&ticker={ticker}&output=xml"

        try:
            self.logger.info(
                f"Looking up CIK for ticker: {ticker}",
                extra={"ticker": ticker}
            )

            response = await self.client.get(url)
            response.raise_for_status()

            # Parse XML response
            soup = BeautifulSoup(response.text, "xml")
            cik_elem = soup.find("CIK")

            if not cik_elem:
                raise FetchError(
                    f"Ticker '{ticker}' not found in SEC EDGAR",
                    source=self.source_type.value,
                    ticker=ticker
                )

            cik = cik_elem.text.strip()
            self.logger.info(
                f"Found CIK {cik} for ticker {ticker}",
                extra={"ticker": ticker, "cik": cik}
            )

            return cik

        except httpx.HTTPError as e:
            raise FetchError(
                f"Failed to lookup ticker {ticker}: {str(e)}",
                source=self.source_type.value,
                ticker=ticker,
                error=str(e)
            )

    async def _get_company_filings(
        self,
        cik: str,
        form_type: Optional[str] = None,
        count: int = 10
    ) -> List[Dict[str, Any]]:
        """Get list of company filings.

        Args:
            cik: Company CIK number
            form_type: Filing form type (e.g., "10-K", "10-Q")
            count: Number of filings to retrieve

        Returns:
            List of filing metadata dictionaries

        Example:
            >>> filings = await adapter._get_company_filings("0000320193", "10-K", 5)
            >>> print(f"Found {len(filings)} filings")
        """
        await self._rate_limit()

        # Build URL with parameters
        params = {
            "action": "getcompany",
            "CIK": cik,
            "type": form_type if form_type else "",
            "dateb": "",
            "owner": "exclude",
            "count": str(count),
            "output": "xml"
        }

        url = f"{self.EDGAR_COMPANY_API}"

        try:
            self.logger.info(
                f"Fetching filings for CIK {cik}",
                extra={"cik": cik, "form_type": form_type, "count": count}
            )

            response = await self.client.get(url, params=params)
            response.raise_for_status()

            # Parse XML response
            soup = BeautifulSoup(response.text, "xml")
            company_name = soup.find("companyName")
            company_name_text = company_name.text if company_name else "Unknown"

            filings = []
            for filing in soup.find_all("filing"):
                filing_data = {
                    "company_name": company_name_text,
                    "cik": cik,
                    "form_type": filing.find("type").text if filing.find("type") else None,
                    "filing_date": filing.find("filingDate").text if filing.find("filingDate") else None,
                    "accession_number": filing.find("accessionNumber").text if filing.find("accessionNumber") else None,
                    "file_number": filing.find("fileNumber").text if filing.find("fileNumber") else None,
                    "filing_href": filing.find("filingHref").text if filing.find("filingHref") else None,
                }
                filings.append(filing_data)

            self.logger.info(
                f"Found {len(filings)} filings for CIK {cik}",
                extra={"cik": cik, "count": len(filings)}
            )

            return filings

        except httpx.HTTPError as e:
            raise FetchError(
                f"Failed to fetch filings for CIK {cik}: {str(e)}",
                source=self.source_type.value,
                cik=cik,
                error=str(e)
            )

    async def _fetch_filing_content(self, filing_url: str) -> str:
        """Fetch and extract text from a filing document.

        Args:
            filing_url: URL to filing document

        Returns:
            Extracted text content

        Example:
            >>> content = await adapter._fetch_filing_content(filing_url)
            >>> print(f"Extracted {len(content)} characters")
        """
        await self._rate_limit()

        try:
            self.logger.info(
                f"Fetching filing content from: {filing_url}",
                extra={"filing_url": filing_url}
            )

            response = await self.client.get(filing_url)
            response.raise_for_status()

            # Check file size
            content_length = len(response.content)
            if content_length > self.max_filing_size:
                raise FetchError(
                    f"Filing too large: {content_length} bytes (max: {self.max_filing_size})",
                    source=self.source_type.value,
                    filing_url=filing_url,
                    file_size=content_length
                )

            # Parse HTML and extract text
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text content
            text = soup.get_text(separator="\n", strip=True)

            # Clean up whitespace
            lines = [line.strip() for line in text.split("\n") if line.strip()]
            content = "\n".join(lines)

            self.logger.info(
                f"Extracted {len(content)} characters from filing",
                extra={"filing_url": filing_url, "content_length": len(content)}
            )

            return content

        except httpx.HTTPError as e:
            raise FetchError(
                f"Failed to fetch filing content: {str(e)}",
                source=self.source_type.value,
                filing_url=filing_url,
                error=str(e)
            )

    async def validate_input(
        self,
        cik: Optional[str] = None,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None,
        **kwargs
    ) -> bool:
        """Validate input parameters.

        Args:
            cik: Company CIK number
            ticker: Stock ticker symbol
            form_type: Filing form type
            **kwargs: Additional arguments

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails

        Example:
            >>> await adapter.validate_input(ticker="AAPL", form_type="10-K")
            True
        """
        # Must provide either CIK or ticker
        if not cik and not ticker:
            raise ValidationError(
                "Must provide either 'cik' or 'ticker' parameter",
                source=self.source_type.value
            )

        # Validate form type if provided
        if form_type and form_type not in self.SUPPORTED_FORMS:
            self.logger.warning(
                f"Form type '{form_type}' not in common list. Proceeding anyway.",
                extra={"form_type": form_type, "supported_forms": self.SUPPORTED_FORMS}
            )

        return True

    async def fetch(
        self,
        cik: Optional[str] = None,
        ticker: Optional[str] = None,
        form_type: Optional[str] = None,
        count: int = 1,
        **kwargs
    ) -> List[RawDocument]:
        """Fetch SEC EDGAR filings.

        Args:
            cik: Company CIK number (e.g., "0000320193")
            ticker: Stock ticker symbol (e.g., "AAPL")
            form_type: Filing form type (e.g., "10-K", "10-Q")
            count: Number of filings to fetch (default: 1)
            **kwargs: Additional metadata to include

        Returns:
            List of RawDocument objects (one per filing)

        Raises:
            ValidationError: If input validation fails
            FetchError: If fetching fails

        Example:
            >>> # Fetch latest 10-K for Apple by ticker
            >>> docs = await adapter.fetch(ticker="AAPL", form_type="10-K", count=1)
            >>> print(f"Fetched {len(docs)} document(s)")
            >>>
            >>> # Fetch latest 3 filings by CIK
            >>> docs = await adapter.fetch(cik="0000320193", count=3)
        """
        # Validate input
        await self.validate_input(cik=cik, ticker=ticker, form_type=form_type)

        try:
            # Convert ticker to CIK if needed
            if ticker and not cik:
                cik = await self._get_cik_from_ticker(ticker)

            # Get company filings
            filings = await self._get_company_filings(
                cik=cik,
                form_type=form_type,
                count=count
            )

            if not filings:
                raise FetchError(
                    f"No filings found for CIK {cik}",
                    source=self.source_type.value,
                    cik=cik,
                    form_type=form_type
                )

            # Fetch content for each filing
            documents = []
            for i, filing in enumerate(filings):
                self.logger.info(
                    f"Processing filing {i+1}/{len(filings)}: {filing['form_type']} from {filing['filing_date']}",
                    extra={
                        "filing_index": i+1,
                        "total_filings": len(filings),
                        "form_type": filing['form_type']
                    }
                )

                # Fetch filing content
                filing_url = filing.get("filing_href")
                if not filing_url:
                    self.logger.warning(
                        f"No URL for filing {i+1}, skipping",
                        extra={"filing_data": filing}
                    )
                    continue

                content = await self._fetch_filing_content(filing_url)

                # Create document metadata
                metadata = {
                    "company_name": filing.get("company_name"),
                    "cik": filing.get("cik"),
                    "form_type": filing.get("form_type"),
                    "filing_date": filing.get("filing_date"),
                    "accession_number": filing.get("accession_number"),
                    "file_number": filing.get("file_number"),
                    "filing_url": filing_url,
                    **kwargs  # Include additional metadata
                }

                # Create RawDocument
                document = self._create_raw_document(
                    content=content,
                    url=filing_url,
                    metadata=metadata
                )

                documents.append(document)

                self.logger.info(
                    f"Successfully fetched filing: {filing['form_type']} ({len(content)} chars)",
                    extra={
                        "document_id": document.id,
                        "form_type": filing['form_type'],
                        "content_length": len(content)
                    }
                )

            self.logger.info(
                f"Successfully fetched {len(documents)} SEC EDGAR document(s)",
                extra={
                    "cik": cik,
                    "ticker": ticker,
                    "form_type": form_type,
                    "count": len(documents)
                }
            )

            return documents

        except Exception as e:
            if isinstance(e, (FetchError, ValidationError)):
                raise

            error_msg = f"Failed to fetch SEC EDGAR filings: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "cik": cik,
                    "ticker": ticker,
                    "form_type": form_type,
                    "error": str(e)
                },
                exc_info=True
            )
            raise FetchError(
                error_msg,
                source=self.source_type.value,
                cik=cik,
                ticker=ticker,
                error=str(e)
            )

    async def health_check(self) -> bool:
        """Check if SEC EDGAR is accessible.

        Returns:
            True if SEC EDGAR is accessible, False otherwise

        Example:
            >>> is_healthy = await adapter.health_check()
            >>> if is_healthy:
            ...     print("SEC EDGAR is accessible")
        """
        try:
            await self._rate_limit()
            response = await self.client.get(self.EDGAR_BASE_URL)
            return response.status_code == 200
        except Exception as e:
            self.logger.error(
                f"SEC EDGAR health check failed: {str(e)}",
                extra={"error": str(e)}
            )
            return False

    def get_supported_formats(self) -> List[str]:
        """Get list of supported filing forms.

        Returns:
            List of supported form types

        Example:
            >>> forms = adapter.get_supported_formats()
            >>> print(f"Supports: {', '.join(forms)}")
        """
        return self.SUPPORTED_FORMS

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()


# Example usage
if __name__ == "__main__":
    import asyncio

    async def test_sec_edgar():
        """Test SEC EDGAR adapter."""
        # Initialize adapter
        adapter = SECEdgarAdapter(
            user_agent="TestApp/1.0 test@example.com",
            tenant_id="tenant-test"
        )

        try:
            print("Testing SEC EDGAR adapter...\n")

            # Test health check
            print("1. Health check...")
            is_healthy = await adapter.health_check()
            print(f"   SEC EDGAR accessible: {is_healthy}\n")

            # Test ticker lookup
            print("2. Looking up Apple (AAPL) CIK...")
            cik = await adapter._get_cik_from_ticker("AAPL")
            print(f"   Found CIK: {cik}\n")

            # Test fetching latest 10-K
            print("3. Fetching latest 10-K filing...")
            docs = await adapter.fetch(
                ticker="AAPL",
                form_type="10-K",
                count=1
            )

            print(f"   Fetched {len(docs)} document(s)")
            for doc in docs:
                print(f"   - Document ID: {doc.id}")
                print(f"   - Company: {doc.metadata.get('company_name')}")
                print(f"   - Form: {doc.metadata.get('form_type')}")
                print(f"   - Date: {doc.metadata.get('filing_date')}")
                print(f"   - Content length: {len(doc.content)} characters")
                print(f"   - Content preview: {doc.content[:200]}...")

        finally:
            await adapter.client.aclose()

    asyncio.run(test_sec_edgar())
