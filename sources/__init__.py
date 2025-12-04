"""
Source Adapters for Rake Pipeline

This module contains source adapters for fetching documents from various sources.

Available Adapters:
    - FileUploadAdapter: PDF, DOCX, TXT, PPTX files
    - SECEdgarAdapter: SEC EDGAR financial filings

Example:
    >>> from sources import FileUploadAdapter, SECEdgarAdapter
    >>> file_adapter = FileUploadAdapter(tenant_id="tenant-123")
    >>> sec_adapter = SECEdgarAdapter(
    ...     user_agent="MyApp support@example.com",
    ...     tenant_id="tenant-123"
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

__all__ = [
    "BaseSourceAdapter",
    "SourceError",
    "FetchError",
    "ValidationError",
    "FileUploadAdapter",
    "SECEdgarAdapter",
]
