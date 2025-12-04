"""
Telemetry Client for Rake Service

Centralized telemetry emission for monitoring and debugging. All pipeline
operations emit telemetry events that can be consumed by Command Central
or other monitoring systems.

Features:
    - Async event emission
    - Automatic retry on failure
    - Correlation ID tracking
    - Multi-tenant support
    - Structured event schemas

Example:
    >>> from services.telemetry_client import telemetry
    >>> await telemetry.emit_job_started(
    ...     job_id="job-123",
    ...     source="file_upload",
    ...     correlation_id="trace-abc"
    ... )
"""

import logging
from typing import Dict, Any, Optional
from uuid import uuid4

import httpx

from config import settings
from models.events import (
    JobStartedEvent,
    PhaseCompletedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    RetryAttemptEvent,
)

logger = logging.getLogger(__name__)


class TelemetryClient:
    """Client for emitting telemetry events.

    Handles async emission of telemetry events to monitoring systems.
    Events are sent via HTTP POST to a telemetry endpoint (Command Central).

    Attributes:
        endpoint: Telemetry endpoint URL
        timeout: HTTP request timeout in seconds
        enabled: Whether telemetry is enabled

    Example:
        >>> client = TelemetryClient()
        >>> await client.emit_job_started("job-123", "file_upload", "trace-abc")
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: int = 5,
        enabled: bool = True
    ):
        """Initialize telemetry client.

        Args:
            endpoint: Telemetry endpoint URL (defaults to Command Central)
            timeout: HTTP request timeout in seconds
            enabled: Whether to actually emit events (disable for testing)

        Example:
            >>> client = TelemetryClient(
            ...     endpoint="http://localhost:3000/api/telemetry",
            ...     timeout=5,
            ...     enabled=True
            ... )
        """
        self.endpoint = endpoint or f"{settings.DATAFORGE_BASE_URL}/telemetry"
        self.timeout = timeout
        self.enabled = enabled
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client.

        Returns:
            Configured httpx AsyncClient

        Example:
            >>> client = await telemetry._get_client()
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self) -> None:
        """Close HTTP client.

        Should be called during application shutdown.

        Example:
            >>> await telemetry.close()
        """
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _emit_event(
        self,
        event: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """Emit a telemetry event.

        Args:
            event: Event data dictionary
            correlation_id: Distributed tracing ID

        Returns:
            True if event was sent successfully, False otherwise

        Example:
            >>> await telemetry._emit_event(
            ...     {"event_type": "job_started", "job_id": "123"},
            ...     "trace-abc"
            ... )
        """
        if not self.enabled:
            logger.debug(
                "Telemetry disabled, skipping event emission",
                extra={"correlation_id": correlation_id}
            )
            return False

        try:
            client = await self._get_client()

            response = await client.post(
                self.endpoint,
                json=event,
                headers={
                    "X-Correlation-ID": correlation_id,
                    "Content-Type": "application/json"
                }
            )

            if response.status_code >= 400:
                logger.warning(
                    f"Failed to emit telemetry event: HTTP {response.status_code}",
                    extra={
                        "correlation_id": correlation_id,
                        "event_type": event.get("event_type"),
                        "status_code": response.status_code
                    }
                )
                return False

            logger.debug(
                "Telemetry event emitted successfully",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event.get("event_type")
                }
            )
            return True

        except httpx.TimeoutException:
            logger.warning(
                "Telemetry emission timed out",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event.get("event_type")
                }
            )
            return False

        except Exception as e:
            logger.error(
                f"Telemetry emission failed: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event.get("event_type")
                },
                exc_info=True
            )
            return False

    async def emit_job_started(
        self,
        job_id: str,
        source: str,
        correlation_id: str,
        scheduled: bool = False,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit job_started event.

        Called at the beginning of a pipeline job.

        Args:
            job_id: Job identifier
            source: Document source type
            correlation_id: Distributed tracing ID
            scheduled: Whether job was triggered by scheduler
            tenant_id: Multi-tenant identifier
            metadata: Additional event metadata

        Returns:
            True if event was sent successfully

        Example:
            >>> await telemetry.emit_job_started(
            ...     job_id="job-123",
            ...     source="file_upload",
            ...     correlation_id="trace-abc",
            ...     scheduled=False,
            ...     tenant_id="tenant-123"
            ... )
        """
        event = JobStartedEvent(
            job_id=job_id,
            source=source,
            correlation_id=correlation_id,
            scheduled=scheduled,
            tenant_id=tenant_id,
            metadata=metadata or {}
        )

        logger.info(
            f"Job started: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "source": source
            }
        )

        return await self._emit_event(event.model_dump(mode='json'), correlation_id)

    async def emit_phase_completed(
        self,
        job_id: str,
        phase: str,
        phase_number: int,
        correlation_id: str,
        duration_ms: float,
        items_processed: int = 0,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit phase_completed event.

        Called after each pipeline stage completes.

        Args:
            job_id: Job identifier
            phase: Stage name (fetch, clean, chunk, embed, store)
            phase_number: Stage number (1-5)
            correlation_id: Distributed tracing ID
            duration_ms: Stage duration in milliseconds
            items_processed: Number of items processed
            tenant_id: Multi-tenant identifier
            metadata: Additional event metadata

        Returns:
            True if event was sent successfully

        Example:
            >>> await telemetry.emit_phase_completed(
            ...     job_id="job-123",
            ...     phase="chunk",
            ...     phase_number=3,
            ...     correlation_id="trace-abc",
            ...     duration_ms=1500.0,
            ...     items_processed=10,
            ...     tenant_id="tenant-123"
            ... )
        """
        event = PhaseCompletedEvent(
            job_id=job_id,
            phase=phase,
            phase_number=phase_number,
            correlation_id=correlation_id,
            duration_ms=duration_ms,
            items_processed=items_processed,
            tenant_id=tenant_id,
            metadata=metadata or {},
            metrics={
                "duration_ms": duration_ms,
                "items_processed": float(items_processed)
            }
        )

        logger.info(
            f"Phase {phase} completed for job {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "phase": phase,
                "duration_ms": duration_ms,
                "items_processed": items_processed
            }
        )

        return await self._emit_event(event.model_dump(mode='json'), correlation_id)

    async def emit_job_completed(
        self,
        job_id: str,
        source: str,
        correlation_id: str,
        total_duration_ms: float,
        chunks_created: int,
        embeddings_generated: int,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit job_completed event.

        Called when entire pipeline completes successfully.

        Args:
            job_id: Job identifier
            source: Document source type
            correlation_id: Distributed tracing ID
            total_duration_ms: Total job duration in milliseconds
            chunks_created: Number of chunks created
            embeddings_generated: Number of embeddings generated
            tenant_id: Multi-tenant identifier
            metadata: Additional event metadata

        Returns:
            True if event was sent successfully

        Example:
            >>> await telemetry.emit_job_completed(
            ...     job_id="job-123",
            ...     source="file_upload",
            ...     correlation_id="trace-abc",
            ...     total_duration_ms=5000.0,
            ...     chunks_created=10,
            ...     embeddings_generated=10,
            ...     tenant_id="tenant-123"
            ... )
        """
        event = JobCompletedEvent(
            job_id=job_id,
            source=source,
            correlation_id=correlation_id,
            total_duration_ms=total_duration_ms,
            chunks_created=chunks_created,
            embeddings_generated=embeddings_generated,
            tenant_id=tenant_id,
            metadata=metadata or {},
            metrics={
                "total_duration_ms": total_duration_ms,
                "chunks_created": float(chunks_created),
                "embeddings_generated": float(embeddings_generated)
            }
        )

        logger.info(
            f"Job completed: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "total_duration_ms": total_duration_ms,
                "chunks_created": chunks_created,
                "embeddings_generated": embeddings_generated
            }
        )

        return await self._emit_event(event.model_dump(mode='json'), correlation_id)

    async def emit_job_failed(
        self,
        job_id: str,
        source: str,
        correlation_id: str,
        failed_stage: str,
        error_type: str,
        error_message: str,
        retry_count: int = 0,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit job_failed event.

        Called when pipeline fails at any stage.

        Args:
            job_id: Job identifier
            source: Document source type
            correlation_id: Distributed tracing ID
            failed_stage: Stage where failure occurred
            error_type: Exception type name
            error_message: Error message
            retry_count: Number of retries attempted
            tenant_id: Multi-tenant identifier
            metadata: Additional event metadata

        Returns:
            True if event was sent successfully

        Example:
            >>> await telemetry.emit_job_failed(
            ...     job_id="job-123",
            ...     source="file_upload",
            ...     correlation_id="trace-abc",
            ...     failed_stage="embed",
            ...     error_type="OpenAIError",
            ...     error_message="Rate limit exceeded",
            ...     retry_count=2,
            ...     tenant_id="tenant-123"
            ... )
        """
        event = JobFailedEvent(
            job_id=job_id,
            source=source,
            correlation_id=correlation_id,
            failed_stage=failed_stage,
            error_type=error_type,
            error_message=error_message,
            retry_count=retry_count,
            tenant_id=tenant_id,
            metadata=metadata or {}
        )

        logger.error(
            f"Job failed: {job_id} at stage {failed_stage}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "failed_stage": failed_stage,
                "error_type": error_type,
                "error_message": error_message,
                "retry_count": retry_count
            }
        )

        return await self._emit_event(event.model_dump(mode='json'), correlation_id)

    async def emit_retry_attempt(
        self,
        job_id: str,
        stage: str,
        correlation_id: str,
        attempt_number: int,
        max_attempts: int,
        error_message: str,
        backoff_seconds: float,
        tenant_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Emit retry_attempt event.

        Called when retrying a failed operation.

        Args:
            job_id: Job identifier
            stage: Stage being retried
            correlation_id: Distributed tracing ID
            attempt_number: Current retry attempt
            max_attempts: Maximum retry attempts
            error_message: Original error message
            backoff_seconds: Backoff delay before retry
            tenant_id: Multi-tenant identifier
            metadata: Additional event metadata

        Returns:
            True if event was sent successfully

        Example:
            >>> await telemetry.emit_retry_attempt(
            ...     job_id="job-123",
            ...     stage="embed",
            ...     correlation_id="trace-abc",
            ...     attempt_number=1,
            ...     max_attempts=3,
            ...     error_message="Rate limit exceeded",
            ...     backoff_seconds=2.0,
            ...     tenant_id="tenant-123"
            ... )
        """
        event = RetryAttemptEvent(
            job_id=job_id,
            stage=stage,
            correlation_id=correlation_id,
            attempt_number=attempt_number,
            max_attempts=max_attempts,
            error_message=error_message,
            backoff_seconds=backoff_seconds,
            tenant_id=tenant_id,
            metadata=metadata or {},
            metrics={
                "attempt_number": float(attempt_number),
                "max_attempts": float(max_attempts),
                "backoff_seconds": backoff_seconds
            }
        )

        logger.warning(
            f"Retry attempt {attempt_number}/{max_attempts} for job {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "stage": stage,
                "attempt_number": attempt_number,
                "max_attempts": max_attempts,
                "backoff_seconds": backoff_seconds
            }
        )

        return await self._emit_event(event.model_dump(mode='json'), correlation_id)


# Global telemetry client instance
telemetry = TelemetryClient(
    enabled=settings.ENVIRONMENT != "test"  # Disable in tests
)


# Example usage
async def example_usage():
    """Example telemetry workflow."""
    correlation_id = str(uuid4())
    job_id = "job-123"

    # Job started
    await telemetry.emit_job_started(
        job_id=job_id,
        source="file_upload",
        correlation_id=correlation_id,
        tenant_id="tenant-123"
    )

    # Phase completed
    await telemetry.emit_phase_completed(
        job_id=job_id,
        phase="chunk",
        phase_number=3,
        correlation_id=correlation_id,
        duration_ms=1500.0,
        items_processed=10,
        tenant_id="tenant-123"
    )

    # Job completed
    await telemetry.emit_job_completed(
        job_id=job_id,
        source="file_upload",
        correlation_id=correlation_id,
        total_duration_ms=5000.0,
        chunks_created=10,
        embeddings_generated=10,
        tenant_id="tenant-123"
    )

    # Clean up
    await telemetry.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
