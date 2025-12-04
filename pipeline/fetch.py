"""
Pipeline Stage 1: FETCH

Retrieves documents from various sources using source adapters.
This is the first stage of the 5-stage pipeline.

Example:
    >>> from pipeline.fetch import FetchStage
    >>> stage = FetchStage()
    >>> documents = await stage.execute(
    ...     source="file_upload",
    ...     file_path="/path/to/doc.pdf",
    ...     correlation_id="trace-123"
    ... )
"""

import logging
import time
from typing import List, Dict, Any, Optional
from uuid import uuid4

from models.document import RawDocument, DocumentSource
from sources.base import BaseSourceAdapter, FetchError
from sources.file_upload import FileUploadAdapter
from sources.sec_edgar import SECEdgarAdapter
from sources.url_scrape import URLScrapeAdapter
from sources.api_fetch import APIFetchAdapter
from services.telemetry_client import telemetry
from config import settings

logger = logging.getLogger(__name__)


class FetchStageError(Exception):
    """Exception raised when fetch stage fails.

    Example:
        >>> raise FetchStageError("Unknown source type", source="invalid")
    """

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class FetchStage:
    """Stage 1: Fetch documents from sources.

    Retrieves raw documents from various sources using the appropriate
    source adapter. Emits telemetry events for monitoring.

    Attributes:
        adapters: Registry of available source adapters

    Example:
        >>> stage = FetchStage()
        >>> docs = await stage.execute(
        ...     source="file_upload",
        ...     file_path="report.pdf",
        ...     correlation_id="trace-abc"
        ... )
    """

    def __init__(self):
        """Initialize fetch stage with available adapters.

        Example:
            >>> stage = FetchStage()
            >>> print(stage.get_available_sources())
        """
        self.adapters: Dict[str, type[BaseSourceAdapter]] = {
            DocumentSource.FILE_UPLOAD.value: FileUploadAdapter,
            DocumentSource.SEC_EDGAR.value: SECEdgarAdapter,
            DocumentSource.URL_SCRAPE.value: URLScrapeAdapter,
            DocumentSource.API_FETCH.value: APIFetchAdapter,
            # Add more adapters as they're implemented:
            # DocumentSource.DATABASE_QUERY.value: DatabaseQueryAdapter,
        }
        self.logger = logging.getLogger(__name__)

    def get_available_sources(self) -> List[str]:
        """Get list of available source types.

        Returns:
            List of source type identifiers

        Example:
            >>> stage = FetchStage()
            >>> sources = stage.get_available_sources()
            >>> print(sources)
            ['file_upload']
        """
        return list(self.adapters.keys())

    def _get_adapter(
        self,
        source: str,
        tenant_id: Optional[str] = None
    ) -> BaseSourceAdapter:
        """Get appropriate source adapter for the given source type.

        Args:
            source: Source type identifier
            tenant_id: Multi-tenant identifier

        Returns:
            Initialized source adapter

        Raises:
            FetchStageError: If source type is not supported

        Example:
            >>> adapter = stage._get_adapter("file_upload", "tenant-123")
        """
        if source not in self.adapters:
            raise FetchStageError(
                f"Unknown source type: {source}",
                source=source,
                available_sources=self.get_available_sources()
            )

        adapter_class = self.adapters[source]

        # SEC EDGAR adapter requires user_agent
        if source == DocumentSource.SEC_EDGAR.value:
            user_agent = settings.SEC_EDGAR_USER_AGENT
            if not user_agent:
                raise FetchStageError(
                    "SEC_EDGAR_USER_AGENT configuration is required for SEC EDGAR source",
                    source=source
                )
            return adapter_class(
                user_agent=user_agent,
                tenant_id=tenant_id,
                rate_limit_delay=settings.SEC_EDGAR_RATE_LIMIT
            )

        return adapter_class(tenant_id=tenant_id)

    async def execute(
        self,
        source: str,
        correlation_id: str,
        job_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        **source_params
    ) -> List[RawDocument]:
        """Execute the fetch stage.

        Retrieves documents from the specified source and emits telemetry.

        Args:
            source: Source type (file_upload, url_scrape, etc.)
            correlation_id: Distributed tracing ID
            job_id: Optional job identifier
            tenant_id: Multi-tenant identifier
            **source_params: Source-specific parameters (file_path, url, etc.)

        Returns:
            List of RawDocument objects

        Raises:
            FetchStageError: If fetch fails

        Example:
            >>> documents = await stage.execute(
            ...     source="file_upload",
            ...     correlation_id="trace-123",
            ...     job_id="job-456",
            ...     tenant_id="tenant-789",
            ...     file_path="/path/to/doc.pdf"
            ... )
            >>> print(f"Fetched {len(documents)} documents")
        """
        start_time = time.time()
        job_id = job_id or f"job-{uuid4().hex[:12]}"

        self.logger.info(
            f"Starting fetch stage for source: {source}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "source": source,
                "tenant_id": tenant_id
            }
        )

        try:
            # Get appropriate adapter
            adapter = self._get_adapter(source, tenant_id)

            self.logger.debug(
                f"Using adapter: {adapter.__class__.__name__}",
                extra={
                    "correlation_id": correlation_id,
                    "adapter": adapter.__class__.__name__
                }
            )

            # Fetch documents with retry logic
            documents = await adapter.fetch_with_retry(
                max_attempts=3,
                **source_params
            )

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Emit telemetry
            await telemetry.emit_phase_completed(
                job_id=job_id,
                phase="fetch",
                phase_number=1,
                correlation_id=correlation_id,
                duration_ms=duration_ms,
                items_processed=len(documents),
                tenant_id=tenant_id,
                metadata={
                    "source": source,
                    "document_count": len(documents),
                    "total_content_length": sum(len(doc.content) for doc in documents)
                }
            )

            self.logger.info(
                f"Fetch stage completed: {len(documents)} documents in {duration_ms:.2f}ms",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "document_count": len(documents),
                    "duration_ms": duration_ms
                }
            )

            return documents

        except FetchError as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Fetch stage failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "source": source,
                    "error": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )

            # Emit failure telemetry
            await telemetry.emit_job_failed(
                job_id=job_id,
                source=source,
                correlation_id=correlation_id,
                failed_stage="fetch",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise FetchStageError(
                f"Fetch failed: {str(e)}",
                source=source,
                error=str(e),
                **e.context if hasattr(e, 'context') else {}
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            self.logger.error(
                f"Unexpected error in fetch stage: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "source": source,
                    "error": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )

            # Emit failure telemetry
            await telemetry.emit_job_failed(
                job_id=job_id,
                source=source,
                correlation_id=correlation_id,
                failed_stage="fetch",
                error_type=e.__class__.__name__,
                error_message=str(e),
                tenant_id=tenant_id
            )

            raise FetchStageError(
                f"Unexpected error: {str(e)}",
                source=source,
                error=str(e)
            )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of all registered source adapters.

        Returns:
            Dict mapping source types to health status

        Example:
            >>> health = await stage.health_check()
            >>> print(health)
            {'file_upload': True}
        """
        health_status = {}

        for source_type, adapter_class in self.adapters.items():
            try:
                adapter = adapter_class()
                is_healthy = await adapter.health_check()
                health_status[source_type] = is_healthy
            except Exception as e:
                self.logger.warning(
                    f"Health check failed for {source_type}: {str(e)}",
                    extra={"source_type": source_type, "error": str(e)}
                )
                health_status[source_type] = False

        return health_status


# Example usage
if __name__ == "__main__":
    import asyncio
    from pathlib import Path

    async def test_fetch_stage():
        """Test the fetch stage."""
        stage = FetchStage()
        correlation_id = str(uuid4())

        print(f"Available sources: {stage.get_available_sources()}")

        # Create test file
        test_file = Path("test_fetch.txt")
        test_file.write_text("This is a test document for the fetch stage.\n\nIt has multiple lines.")

        try:
            # Execute fetch stage
            documents = await stage.execute(
                source="file_upload",
                correlation_id=correlation_id,
                job_id="job-test",
                tenant_id="tenant-test",
                file_path=str(test_file)
            )

            print(f"\nFetched {len(documents)} document(s)")
            doc = documents[0]
            print(f"Document ID: {doc.id}")
            print(f"Source: {doc.source}")
            print(f"Content length: {len(doc.content)} chars")
            print(f"Metadata: {doc.metadata}")

            # Check health
            health = await stage.health_check()
            print(f"\nHealth status: {health}")

        finally:
            # Cleanup
            if test_file.exists():
                test_file.unlink()
            await telemetry.close()

    asyncio.run(test_fetch_stage())
