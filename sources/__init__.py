"""
Source Adapters for Rake Pipeline

This module contains source adapters for fetching documents from various sources.

Available Adapters:
    - FileUploadAdapter: PDF, DOCX, TXT, PPTX files
    - SECEdgarAdapter: SEC EDGAR financial filings
    - URLScrapeAdapter: Web pages and articles
    - APIFetchAdapter: External REST/HTTP APIs
    - DatabaseQueryAdapter: SQL database queries (PostgreSQL, MySQL, SQLite)

Example:
    >>> from sources import (
    ...     FileUploadAdapter,
    ...     SECEdgarAdapter,
    ...     URLScrapeAdapter,
    ...     APIFetchAdapter,
    ...     DatabaseQueryAdapter
    ... )
    >>> file_adapter = FileUploadAdapter(tenant_id="tenant-123")
    >>> sec_adapter = SECEdgarAdapter(
    ...     user_agent="MyApp support@example.com",
    ...     tenant_id="tenant-123"
    ... )
    >>> url_adapter = URLScrapeAdapter(
    ...     user_agent="Rake/1.0 (Data Bot)",
    ...     tenant_id="tenant-123"
    ... )
    >>> api_adapter = APIFetchAdapter(
    ...     user_agent="Rake/1.0 (API Bot)",
    ...     tenant_id="tenant-123"
    ... )
    >>> db_adapter = DatabaseQueryAdapter(
    ...     tenant_id="tenant-123",
    ...     max_rows=1000,
    ...     read_only=True
    ... )
"""

from sources.base import (
    BaseSourceAdapter,
    SourceError,
    FetchError,
    ValidationError
)
from sources.file_upload import FileUploadAdapter
from sources.sec_edgar import SECEdgarAdapter
from sources.url_scrape import URLScrapeAdapter
from sources.api_fetch import APIFetchAdapter
from sources.database_query import DatabaseQueryAdapter

__all__ = [
    "BaseSourceAdapter",
    "SourceError",
    "FetchError",
    "ValidationError",
    "FileUploadAdapter",
    "SECEdgarAdapter",
    "URLScrapeAdapter",
    "APIFetchAdapter",
    "DatabaseQueryAdapter",
]
