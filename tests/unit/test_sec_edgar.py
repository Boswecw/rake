"""Unit Tests for SEC EDGAR Source Adapter

Tests for SEC EDGAR financial filing retrieval functionality.

Run with:
    pytest tests/unit/test_sec_edgar.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from sources.sec_edgar import SECEdgarAdapter
from sources.base import FetchError, ValidationError
from models.document import DocumentSource


class TestSECEdgarAdapterInit:
    """Tests for SEC EDGAR adapter initialization."""

    def test_init_with_valid_email(self):
        """Test initialization with valid email in user-agent."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp/1.0 test@example.com",
            tenant_id="tenant-123"
        )
        assert adapter.user_agent == "TestApp/1.0 test@example.com"
        assert adapter.tenant_id == "tenant-123"
        assert adapter.source_type == DocumentSource.SEC_EDGAR

    def test_init_with_valid_website(self):
        """Test initialization with valid website in user-agent."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp/1.0 https://example.com",
            tenant_id="tenant-123"
        )
        assert adapter.user_agent == "TestApp/1.0 https://example.com"

    def test_init_without_contact_info(self):
        """Test that initialization fails without contact info."""
        with pytest.raises(ValidationError) as exc_info:
            SECEdgarAdapter(user_agent="TestApp/1.0", tenant_id="tenant-123")

        assert "contact information" in str(exc_info.value).lower()

    def test_init_with_custom_rate_limit(self):
        """Test initialization with custom rate limit."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123",
            rate_limit_delay=0.2
        )
        assert adapter.rate_limit_delay == 0.2

    def test_init_with_custom_max_size(self):
        """Test initialization with custom max filing size."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123",
            max_filing_size=100 * 1024 * 1024  # 100MB
        )
        assert adapter.max_filing_size == 100 * 1024 * 1024


class TestValidateUserAgent:
    """Tests for user-agent validation."""

    def test_validate_with_email(self):
        """Test validation with email address."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        assert adapter._validate_user_agent("MyApp admin@company.com") is True

    def test_validate_with_website(self):
        """Test validation with website URL."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        assert adapter._validate_user_agent("MyApp http://example.com") is True
        assert adapter._validate_user_agent("MyApp https://example.com") is True

    def test_validate_without_contact(self):
        """Test validation fails without contact info."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        assert adapter._validate_user_agent("MyApp") is False
        assert adapter._validate_user_agent("v1.0.0") is False


class TestValidateInput:
    """Tests for input validation."""

    @pytest.mark.asyncio
    async def test_validate_with_cik(self):
        """Test validation with CIK number."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        assert await adapter.validate_input(cik="0000320193") is True

    @pytest.mark.asyncio
    async def test_validate_with_ticker(self):
        """Test validation with ticker symbol."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        assert await adapter.validate_input(ticker="AAPL") is True

    @pytest.mark.asyncio
    async def test_validate_without_cik_or_ticker(self):
        """Test validation fails without CIK or ticker."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        with pytest.raises(ValidationError) as exc_info:
            await adapter.validate_input(form_type="10-K")

        assert "cik" in str(exc_info.value).lower() or "ticker" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_validate_with_form_type(self):
        """Test validation with form type."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )
        # Should pass even with unsupported form type (just logs warning)
        assert await adapter.validate_input(cik="0000320193", form_type="CUSTOM") is True


@pytest.mark.asyncio
class TestGetCIKFromTicker:
    """Tests for ticker to CIK conversion."""

    async def test_successful_ticker_lookup(self):
        """Test successful ticker to CIK conversion."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock HTTP response
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed>
            <CIK>0000320193</CIK>
            <companyName>APPLE INC</companyName>
        </feed>"""

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_xml
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            cik = await adapter._get_cik_from_ticker("AAPL")
            assert cik == "0000320193"

    async def test_ticker_not_found(self):
        """Test error when ticker not found."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock HTTP response with no CIK
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed>
            <error>No matching ticker</error>
        </feed>"""

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_xml
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            with pytest.raises(FetchError) as exc_info:
                await adapter._get_cik_from_ticker("INVALID")

            assert "not found" in str(exc_info.value).lower()

    async def test_ticker_lookup_network_error(self):
        """Test handling of network errors during ticker lookup."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        with patch.object(adapter.client, 'get') as mock_get:
            mock_get.side_effect = httpx.NetworkError("Connection failed")

            with pytest.raises(FetchError) as exc_info:
                await adapter._get_cik_from_ticker("AAPL")

            assert "failed to lookup ticker" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestGetCompanyFilings:
    """Tests for retrieving company filings."""

    async def test_successful_filings_retrieval(self):
        """Test successful retrieval of company filings."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock HTTP response
        mock_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed>
            <companyName>APPLE INC</companyName>
            <filing>
                <type>10-K</type>
                <filingDate>2023-11-03</filingDate>
                <accessionNumber>0000320193-23-000077</accessionNumber>
                <fileNumber>001-36743</fileNumber>
                <filingHref>https://www.sec.gov/Archives/edgar/data/320193/000032019323000077/0000320193-23-000077-index.htm</filingHref>
            </filing>
            <filing>
                <type>10-Q</type>
                <filingDate>2023-08-04</filingDate>
                <accessionNumber>0000320193-23-000067</accessionNumber>
                <fileNumber>001-36743</fileNumber>
                <filingHref>https://www.sec.gov/Archives/edgar/data/320193/000032019323000067/0000320193-23-000067-index.htm</filingHref>
            </filing>
        </feed>"""

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_xml
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            filings = await adapter._get_company_filings("0000320193", form_type="10-K", count=2)

            assert len(filings) == 2
            assert filings[0]["form_type"] == "10-K"
            assert filings[0]["company_name"] == "APPLE INC"
            assert filings[0]["filing_date"] == "2023-11-03"
            assert filings[1]["form_type"] == "10-Q"


@pytest.mark.asyncio
class TestFetchFilingContent:
    """Tests for fetching filing content."""

    async def test_successful_content_fetch(self):
        """Test successful filing content retrieval."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock HTTP response with HTML
        mock_html = """
        <!DOCTYPE html>
        <html>
        <head><title>10-K Filing</title></head>
        <body>
            <h1>Annual Report</h1>
            <p>This is the company's annual report content.</p>
            <p>Financial data and disclosures.</p>
        </body>
        </html>
        """

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_response.content = mock_html.encode()
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            content = await adapter._fetch_filing_content("https://www.sec.gov/filing.htm")

            assert "Annual Report" in content
            assert "annual report content" in content
            assert "Financial data" in content
            # Should not contain HTML tags
            assert "<p>" not in content
            assert "<h1>" not in content

    async def test_content_too_large(self):
        """Test error when filing content exceeds size limit."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123",
            max_filing_size=100  # Very small limit
        )

        mock_html = "<html>" + ("x" * 1000) + "</html>"

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = mock_html
            mock_response.content = mock_html.encode()
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response

            with pytest.raises(FetchError) as exc_info:
                await adapter._fetch_filing_content("https://www.sec.gov/filing.htm")

            assert "too large" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestFetch:
    """Tests for full fetch workflow."""

    async def test_fetch_by_ticker(self):
        """Test fetching filings by ticker symbol."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock ticker lookup
        mock_ticker_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed><CIK>0000320193</CIK></feed>"""

        # Mock filings list
        mock_filings_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed>
            <companyName>APPLE INC</companyName>
            <filing>
                <type>10-K</type>
                <filingDate>2023-11-03</filingDate>
                <accessionNumber>0000320193-23-000077</accessionNumber>
                <fileNumber>001-36743</fileNumber>
                <filingHref>https://www.sec.gov/filing.htm</filingHref>
            </filing>
        </feed>"""

        # Mock filing content
        mock_filing_html = "<html><body><p>Annual report content here.</p></body></html>"

        with patch.object(adapter.client, 'get') as mock_get:
            def mock_get_response(url, *args, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()

                if "ticker=" in url:
                    mock_response.text = mock_ticker_xml
                elif "getcompany" in url or "action=" in url:
                    mock_response.text = mock_filings_xml
                else:
                    mock_response.text = mock_filing_html
                    mock_response.content = mock_filing_html.encode()

                return mock_response

            mock_get.side_effect = mock_get_response

            documents = await adapter.fetch(ticker="AAPL", form_type="10-K", count=1)

            assert len(documents) == 1
            doc = documents[0]
            assert doc.source == DocumentSource.SEC_EDGAR
            assert doc.metadata["company_name"] == "APPLE INC"
            assert doc.metadata["form_type"] == "10-K"
            assert doc.metadata["ticker"] is None  # Not in original request
            assert "Annual report content" in doc.content

    async def test_fetch_by_cik(self):
        """Test fetching filings by CIK number."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        # Mock filings list
        mock_filings_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed>
            <companyName>APPLE INC</companyName>
            <filing>
                <type>10-Q</type>
                <filingDate>2023-08-04</filingDate>
                <accessionNumber>0000320193-23-000067</accessionNumber>
                <fileNumber>001-36743</fileNumber>
                <filingHref>https://www.sec.gov/filing.htm</filingHref>
            </filing>
        </feed>"""

        # Mock filing content
        mock_filing_html = "<html><body><p>Quarterly report content.</p></body></html>"

        with patch.object(adapter.client, 'get') as mock_get:
            def mock_get_response(url, *args, **kwargs):
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.raise_for_status = MagicMock()

                if "getcompany" in url or "action=" in url:
                    mock_response.text = mock_filings_xml
                else:
                    mock_response.text = mock_filing_html
                    mock_response.content = mock_filing_html.encode()

                return mock_response

            mock_get.side_effect = mock_get_response

            documents = await adapter.fetch(cik="0000320193", form_type="10-Q", count=1)

            assert len(documents) == 1
            assert documents[0].metadata["form_type"] == "10-Q"
            assert "Quarterly report" in documents[0].content

    async def test_fetch_without_cik_or_ticker(self):
        """Test fetch fails without CIK or ticker."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        with pytest.raises(ValidationError):
            await adapter.fetch(form_type="10-K")


@pytest.mark.asyncio
class TestHealthCheck:
    """Tests for health check functionality."""

    async def test_health_check_success(self):
        """Test successful health check."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        with patch.object(adapter.client, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response

            is_healthy = await adapter.health_check()
            assert is_healthy is True

    async def test_health_check_failure(self):
        """Test failed health check."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        with patch.object(adapter.client, 'get') as mock_get:
            mock_get.side_effect = httpx.NetworkError("Connection failed")

            is_healthy = await adapter.health_check()
            assert is_healthy is False


class TestGetSupportedFormats:
    """Tests for supported formats list."""

    def test_get_supported_formats(self):
        """Test getting list of supported filing forms."""
        adapter = SECEdgarAdapter(
            user_agent="TestApp test@example.com",
            tenant_id="tenant-123"
        )

        formats = adapter.get_supported_formats()
        assert isinstance(formats, list)
        assert "10-K" in formats
        assert "10-Q" in formats
        assert "8-K" in formats
        assert len(formats) > 0


# Run tests with: pytest tests/unit/test_sec_edgar.py -v
