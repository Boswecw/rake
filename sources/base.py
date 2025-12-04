"""
Base Source Adapter for Rake Pipeline

Abstract base class defining the interface for all data source adapters.
All source implementations (file_upload, url_scrape, api_fetch, etc.)
must inherit from this base class.

Example:
    >>> from sources.base import BaseSourceAdapter
    >>> class MySource(BaseSourceAdapter):
    ...     async def fetch(self, url: str) -> List[RawDocument]:
    ...         # Implementation here
    ...         pass
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from models.document import RawDocument, DocumentSource

logger = logging.getLogger(__name__)


class SourceError(Exception):
    """Base exception for source adapter errors.

    Raised when a source adapter encounters an error during fetching.

    Example:
        >>> raise SourceError("Failed to fetch document", source="file_upload")
    """

    def __init__(self, message: str, source: Optional[str] = None, **kwargs):
        """Initialize source error.

        Args:
            message: Error message
            source: Source identifier
            **kwargs: Additional error context
        """
        self.message = message
        self.source = source
        self.context = kwargs
        super().__init__(message)


class FetchError(SourceError):
    """Exception raised when fetching fails.

    Example:
        >>> raise FetchError("Network timeout", source="url_scrape", url="https://example.com")
    """
    pass


class ValidationError(SourceError):
    """Exception raised when input validation fails.

    Example:
        >>> raise ValidationError("Invalid URL format", source="url_scrape", url="bad-url")
    """
    pass


class BaseSourceAdapter(ABC):
    """Abstract base class for all source adapters.

    All source adapters must implement the fetch() method to retrieve
    documents from their respective sources.

    Attributes:
        source_type: Type of source (file_upload, url_scrape, etc.)
        tenant_id: Multi-tenant identifier

    Example:
        >>> class FileUploadAdapter(BaseSourceAdapter):
        ...     async def fetch(self, file_path: str, **kwargs) -> List[RawDocument]:
        ...         # Read file and return RawDocument
        ...         pass
    """

    def __init__(
        self,
        source_type: DocumentSource,
        tenant_id: Optional[str] = None
    ):
        """Initialize source adapter.

        Args:
            source_type: Type of source
            tenant_id: Multi-tenant identifier

        Example:
            >>> adapter = FileUploadAdapter(
            ...     source_type=DocumentSource.FILE_UPLOAD,
            ...     tenant_id="tenant-123"
            ... )
        """
        self.source_type = source_type
        self.tenant_id = tenant_id
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def fetch(self, *args, **kwargs) -> List[RawDocument]:
        """Fetch documents from the source.

        This method must be implemented by all subclasses.

        Args:
            *args: Positional arguments (source-specific)
            **kwargs: Keyword arguments (source-specific)

        Returns:
            List of RawDocument objects

        Raises:
            FetchError: If fetching fails
            ValidationError: If input validation fails

        Example:
            >>> documents = await adapter.fetch(file_path="/path/to/doc.pdf")
            >>> print(f"Fetched {len(documents)} documents")
        """
        raise NotImplementedError("Subclasses must implement fetch()")

    async def validate_input(self, *args, **kwargs) -> bool:
        """Validate input parameters before fetching.

        Override this method to implement source-specific validation.

        Args:
            *args: Positional arguments to validate
            **kwargs: Keyword arguments to validate

        Returns:
            True if validation passes

        Raises:
            ValidationError: If validation fails

        Example:
            >>> await adapter.validate_input(file_path="/path/to/doc.pdf")
            True
        """
        return True

    def _create_raw_document(
        self,
        content: str,
        url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> RawDocument:
        """Create a RawDocument instance.

        Helper method for creating RawDocument objects with
        consistent tenant_id and source_type.

        Args:
            content: Document content
            url: Optional source URL
            metadata: Additional metadata

        Returns:
            RawDocument instance

        Example:
            >>> doc = adapter._create_raw_document(
            ...     content="Document text",
            ...     metadata={"filename": "doc.pdf"}
            ... )
        """
        return RawDocument(
            source=self.source_type,
            url=url,
            content=content,
            metadata=metadata or {},
            fetched_at=datetime.utcnow(),
            tenant_id=self.tenant_id
        )

    async def fetch_with_retry(
        self,
        max_attempts: int = 3,
        backoff_base: float = 2.0,
        *args,
        **kwargs
    ) -> List[RawDocument]:
        """Fetch documents with automatic retry logic.

        Implements exponential backoff for transient failures.

        Args:
            max_attempts: Maximum number of retry attempts
            backoff_base: Base for exponential backoff calculation
            *args: Arguments to pass to fetch()
            **kwargs: Keyword arguments to pass to fetch()

        Returns:
            List of RawDocument objects

        Raises:
            FetchError: If all retry attempts fail

        Example:
            >>> documents = await adapter.fetch_with_retry(
            ...     max_attempts=3,
            ...     file_path="/path/to/doc.pdf"
            ... )
        """
        import asyncio

        last_error = None

        for attempt in range(1, max_attempts + 1):
            try:
                self.logger.info(
                    f"Fetch attempt {attempt}/{max_attempts}",
                    extra={
                        "source_type": self.source_type.value,
                        "attempt": attempt,
                        "max_attempts": max_attempts
                    }
                )

                documents = await self.fetch(*args, **kwargs)

                if attempt > 1:
                    self.logger.info(
                        f"Fetch succeeded on attempt {attempt}",
                        extra={
                            "source_type": self.source_type.value,
                            "attempt": attempt
                        }
                    )

                return documents

            except Exception as e:
                last_error = e
                self.logger.warning(
                    f"Fetch attempt {attempt} failed: {str(e)}",
                    extra={
                        "source_type": self.source_type.value,
                        "attempt": attempt,
                        "error": str(e)
                    }
                )

                if attempt < max_attempts:
                    backoff_seconds = backoff_base ** attempt
                    self.logger.info(
                        f"Retrying in {backoff_seconds:.1f} seconds",
                        extra={
                            "source_type": self.source_type.value,
                            "backoff_seconds": backoff_seconds
                        }
                    )
                    await asyncio.sleep(backoff_seconds)

        # All attempts failed
        error_msg = f"Failed to fetch after {max_attempts} attempts: {str(last_error)}"
        self.logger.error(
            error_msg,
            extra={
                "source_type": self.source_type.value,
                "max_attempts": max_attempts
            },
            exc_info=True
        )
        raise FetchError(error_msg, source=self.source_type.value)

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats for this source.

        Override this method to specify supported formats.

        Returns:
            List of supported formats (e.g., ["pdf", "txt", "docx"])

        Example:
            >>> formats = adapter.get_supported_formats()
            >>> print(f"Supports: {', '.join(formats)}")
        """
        return []

    async def health_check(self) -> bool:
        """Check if the source is accessible and healthy.

        Override this method to implement source-specific health checks.

        Returns:
            True if source is healthy, False otherwise

        Example:
            >>> is_healthy = await adapter.health_check()
            >>> if not is_healthy:
            ...     print("Source is down")
        """
        return True

    def __repr__(self) -> str:
        """String representation of the adapter.

        Returns:
            String representation

        Example:
            >>> print(adapter)
            FileUploadAdapter(source_type=file_upload, tenant_id=tenant-123)
        """
        return (
            f"{self.__class__.__name__}("
            f"source_type={self.source_type.value}, "
            f"tenant_id={self.tenant_id})"
        )


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    class MockSourceAdapter(BaseSourceAdapter):
        """Mock adapter for testing."""

        async def fetch(self, content: str, **kwargs) -> List[RawDocument]:
            """Fetch mock documents."""
            return [
                self._create_raw_document(
                    content=content,
                    metadata={"test": True}
                )
            ]

    async def test_adapter():
        """Test the base adapter functionality."""
        adapter = MockSourceAdapter(
            source_type=DocumentSource.FILE_UPLOAD,
            tenant_id="tenant-test"
        )

        print(f"Adapter: {adapter}")

        # Test fetch
        docs = await adapter.fetch(content="Test content")
        print(f"Fetched {len(docs)} documents")
        print(f"First doc: {docs[0].id}, source: {docs[0].source}")

        # Test fetch with retry
        docs = await adapter.fetch_with_retry(
            max_attempts=2,
            content="Test with retry"
        )
        print(f"Fetched with retry: {len(docs)} documents")

    asyncio.run(test_adapter())
