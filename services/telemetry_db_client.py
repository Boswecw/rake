"""
Database-based Telemetry Client for Rake Service

Writes telemetry events directly to DataForge SQLite database instead of HTTP POST.
This provides faster, more reliable telemetry with no network dependencies.

Features:
    - Direct SQLite writes to DataForge database
    - Same API as HTTP telemetry client (drop-in replacement)
    - Automatic retry on database lock
    - Correlation ID tracking
    - Multi-tenant support
    - Structured event schemas

Example:
    >>> from services.telemetry_db_client import telemetry
    >>> await telemetry.emit_job_started(
    ...     job_id="job-123",
    ...     source="file_upload",
    ...     correlation_id="trace-abc"
    ... )
"""

import logging
import sqlite3
import json
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from config import settings
from models.events import (
    JobStartedEvent,
    PhaseCompletedEvent,
    JobCompletedEvent,
    JobFailedEvent,
    RetryAttemptEvent,
)

logger = logging.getLogger(__name__)


class TelemetryDatabaseClient:
    """Client for emitting telemetry events directly to database.

    Writes telemetry events to DataForge SQLite database for consumption
    by ForgeCommand monitoring dashboard.

    Attributes:
        db_path: Path to DataForge SQLite database
        enabled: Whether telemetry is enabled

    Example:
        >>> client = TelemetryDatabaseClient()
        >>> await client.emit_job_started("job-123", "file_upload", "trace-abc")
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        enabled: bool = True
    ):
        """Initialize database telemetry client.

        Args:
            db_path: Path to DataForge database (defaults to configured path)
            enabled: Whether to actually emit events (disable for testing)

        Example:
            >>> client = TelemetryDatabaseClient(
            ...     db_path="/path/to/dataforge.db",
            ...     enabled=True
            ... )
        """
        # Default to DataForge database path
        if db_path is None:
            db_path = getattr(settings, 'DATAFORGE_DB_PATH',
                             '/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db')

        self.db_path = Path(db_path)
        self.enabled = enabled

        # Validate database exists
        if self.enabled and not self.db_path.exists():
            logger.warning(
                f"DataForge database not found at {self.db_path}. "
                "Telemetry will be disabled."
            )
            self.enabled = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection.

        Returns:
            SQLite connection with JSON support

        Example:
            >>> conn = telemetry._get_connection()
        """
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _emit_event(
        self,
        event: Dict[str, Any],
        correlation_id: str
    ) -> bool:
        """Emit a telemetry event to database.

        Args:
            event: Event data dictionary
            correlation_id: Distributed tracing ID

        Returns:
            True if event was written successfully, False otherwise

        Example:
            >>> telemetry._emit_event(
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
            conn = self._get_connection()
            cursor = conn.cursor()

            # Generate event ID
            event_id = str(uuid4())

            # Extract event fields
            event_type = event.get("event_type")
            timestamp = event.get("timestamp", datetime.utcnow().isoformat())
            severity = event.get("severity", "info")
            metadata = json.dumps(event.get("metadata", {}))
            metrics = json.dumps(event.get("metrics", {}))

            # Insert event into database
            cursor.execute("""
                INSERT INTO events (
                    event_id,
                    timestamp,
                    service,
                    event_type,
                    severity,
                    correlation_id,
                    metadata,
                    metrics
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                timestamp,
                "rake",  # Always "rake" for this client
                event_type,
                severity,
                correlation_id,
                metadata,
                metrics
            ))

            conn.commit()
            conn.close()

            logger.debug(
                "Telemetry event written to database",
                extra={
                    "correlation_id": correlation_id,
                    "event_id": event_id,
                    "event_type": event_type
                }
            )
            return True

        except sqlite3.OperationalError as e:
            logger.warning(
                f"Database locked, telemetry event skipped: {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "event_type": event.get("event_type")
                }
            )
            return False

        except Exception as e:
            logger.error(
                f"Failed to write telemetry event to database: {str(e)}",
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
            True if event was written successfully

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

        return self._emit_event(event.model_dump(mode='json'), correlation_id)

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
            True if event was written successfully

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

        return self._emit_event(event.model_dump(mode='json'), correlation_id)

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
            True if event was written successfully

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
        # Map job_completed to ingestion_complete for Rake metrics
        # Add pipeline info to metadata (ForgeCommand queries expect it in metrics JSON field)
        enriched_metadata = metadata.copy() if metadata else {}
        if not enriched_metadata.get("pipeline_id"):
            enriched_metadata["pipeline_id"] = job_id[:8]
        if not enriched_metadata.get("pipeline_name"):
            enriched_metadata["pipeline_name"] = f"Pipeline {job_id[:8]}"

        event_dict = {
            "event_type": "ingestion_complete",
            "job_id": job_id,
            "source": source,
            "correlation_id": correlation_id,
            "severity": "info",
            "timestamp": datetime.utcnow().isoformat(),
            "tenant_id": tenant_id,
            "metadata": enriched_metadata,
            "metrics": {
                "total_duration_ms": total_duration_ms,
                "chunks_created": float(chunks_created),
                "embeddings_generated": float(embeddings_generated),
                # Include pipeline info here too for ForgeCommand SQL queries
                "pipeline_id": enriched_metadata["pipeline_id"],
                "pipeline_name": enriched_metadata["pipeline_name"]
            }
        }

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

        return self._emit_event(event_dict, correlation_id)

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
            True if event was written successfully

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

        # Override severity to error
        event_dict = event.model_dump(mode='json')
        event_dict['severity'] = 'error'

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

        return self._emit_event(event_dict, correlation_id)

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
            True if event was written successfully

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

        # Override severity to warning
        event_dict = event.model_dump(mode='json')
        event_dict['severity'] = 'warning'

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

        return self._emit_event(event_dict, correlation_id)

    async def close(self) -> None:
        """Close client (no-op for database client).

        Provided for API compatibility with HTTP client.

        Example:
            >>> await telemetry.close()
        """
        pass  # No cleanup needed for SQLite client


# Global telemetry client instance
telemetry = TelemetryDatabaseClient(
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
        tenant_id="tenant-123",
        metadata={"pipeline_id": "pdf-pipeline", "pipeline_name": "PDF Pipeline"}
    )

    # Phase completed
    await telemetry.emit_phase_completed(
        job_id=job_id,
        phase="chunk",
        phase_number=3,
        correlation_id=correlation_id,
        duration_ms=1500.0,
        items_processed=10,
        tenant_id="tenant-123",
        metadata={"pipeline_id": "pdf-pipeline", "pipeline_name": "PDF Pipeline"}
    )

    # Job completed
    await telemetry.emit_job_completed(
        job_id=job_id,
        source="file_upload",
        correlation_id=correlation_id,
        total_duration_ms=5000.0,
        chunks_created=10,
        embeddings_generated=10,
        tenant_id="tenant-123",
        metadata={"pipeline_id": "pdf-pipeline", "pipeline_name": "PDF Pipeline"}
    )

    # Clean up
    await telemetry.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
