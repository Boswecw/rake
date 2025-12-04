"""
Telemetry Event Models for Rake Service

Pydantic models for telemetry events emitted throughout the pipeline.
All events follow a consistent schema for monitoring and debugging.

Event Types:
    - job_started: Pipeline begins processing
    - phase_completed: A stage completes successfully
    - job_completed: Entire pipeline completes
    - job_failed: Pipeline fails at any stage

Example:
    >>> from models.events import JobStartedEvent
    >>> event = JobStartedEvent(
    ...     job_id="job-123",
    ...     source="file_upload",
    ...     correlation_id="trace-abc"
    ... )
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class EventSeverity(str, Enum):
    """Severity levels for telemetry events.

    Attributes:
        DEBUG: Detailed debug information
        INFO: Informational messages
        WARNING: Warning conditions
        ERROR: Error conditions
        CRITICAL: Critical failures

    Example:
        >>> severity = EventSeverity.INFO
        >>> print(severity.value)
        info
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(str, Enum):
    """Types of telemetry events.

    Attributes:
        JOB_STARTED: Pipeline job started
        PHASE_COMPLETED: Stage completed successfully
        JOB_COMPLETED: Job completed successfully
        JOB_FAILED: Job failed at some stage
        RETRY_ATTEMPT: Retrying after failure

    Example:
        >>> event_type = EventType.JOB_STARTED
        >>> print(event_type.value)
        job_started
    """
    JOB_STARTED = "job_started"
    PHASE_COMPLETED = "phase_completed"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    RETRY_ATTEMPT = "retry_attempt"


class BaseTelemetryEvent(BaseModel):
    """Base model for all telemetry events.

    All telemetry events inherit from this base model, ensuring
    consistent structure across the system.

    Attributes:
        service: Service name (always "rake")
        event_type: Type of event
        severity: Event severity level
        correlation_id: Distributed tracing ID
        timestamp: When event occurred
        metadata: Additional event-specific metadata
        metrics: Numerical metrics (duration, counts, etc.)

    Example:
        >>> event = BaseTelemetryEvent(
        ...     event_type=EventType.JOB_STARTED,
        ...     severity=EventSeverity.INFO,
        ...     correlation_id="trace-123",
        ...     metadata={"job_id": "job-123"}
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    service: str = "rake"
    event_type: EventType
    severity: EventSeverity
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)


class JobStartedEvent(BaseTelemetryEvent):
    """Event emitted when a pipeline job starts.

    Attributes:
        job_id: Job identifier
        source: Document source type
        scheduled: Whether job was triggered by scheduler
        tenant_id: Multi-tenant identifier

    Example:
        >>> event = JobStartedEvent(
        ...     job_id="job-123",
        ...     source="file_upload",
        ...     correlation_id="trace-abc",
        ...     scheduled=False,
        ...     tenant_id="tenant-123"
        ... )
        >>> print(event.model_dump_json())
    """

    event_type: EventType = EventType.JOB_STARTED
    severity: EventSeverity = EventSeverity.INFO
    job_id: str
    source: str
    scheduled: bool = False
    tenant_id: Optional[str] = None


class PhaseCompletedEvent(BaseTelemetryEvent):
    """Event emitted when a pipeline stage completes.

    Attributes:
        job_id: Job identifier
        phase: Stage name (fetch, clean, chunk, embed, store)
        phase_number: Stage number (1-5)
        duration_ms: Stage duration in milliseconds
        items_processed: Number of items processed (chunks, embeddings, etc.)
        tenant_id: Multi-tenant identifier

    Example:
        >>> event = PhaseCompletedEvent(
        ...     job_id="job-123",
        ...     phase="chunk",
        ...     phase_number=3,
        ...     correlation_id="trace-abc",
        ...     duration_ms=1500.0,
        ...     items_processed=10,
        ...     tenant_id="tenant-123"
        ... )
    """

    event_type: EventType = EventType.PHASE_COMPLETED
    severity: EventSeverity = EventSeverity.INFO
    job_id: str
    phase: str
    phase_number: int = Field(ge=1, le=5)
    duration_ms: float = Field(ge=0.0)
    items_processed: int = Field(default=0, ge=0)
    tenant_id: Optional[str] = None


class JobCompletedEvent(BaseTelemetryEvent):
    """Event emitted when a pipeline job completes successfully.

    Attributes:
        job_id: Job identifier
        source: Document source type
        total_duration_ms: Total job duration in milliseconds
        chunks_created: Number of chunks created
        embeddings_generated: Number of embeddings generated
        tenant_id: Multi-tenant identifier

    Example:
        >>> event = JobCompletedEvent(
        ...     job_id="job-123",
        ...     source="file_upload",
        ...     correlation_id="trace-abc",
        ...     total_duration_ms=5000.0,
        ...     chunks_created=15,
        ...     embeddings_generated=15,
        ...     tenant_id="tenant-123"
        ... )
    """

    event_type: EventType = EventType.JOB_COMPLETED
    severity: EventSeverity = EventSeverity.INFO
    job_id: str
    source: str
    total_duration_ms: float = Field(ge=0.0)
    chunks_created: int = Field(default=0, ge=0)
    embeddings_generated: int = Field(default=0, ge=0)
    tenant_id: Optional[str] = None


class JobFailedEvent(BaseTelemetryEvent):
    """Event emitted when a pipeline job fails.

    Attributes:
        job_id: Job identifier
        source: Document source type
        failed_stage: Stage where failure occurred
        error_type: Exception type
        error_message: Error message
        retry_count: Number of retries attempted
        tenant_id: Multi-tenant identifier

    Example:
        >>> event = JobFailedEvent(
        ...     job_id="job-123",
        ...     source="file_upload",
        ...     correlation_id="trace-abc",
        ...     failed_stage="embed",
        ...     error_type="OpenAIError",
        ...     error_message="API rate limit exceeded",
        ...     retry_count=2,
        ...     tenant_id="tenant-123"
        ... )
    """

    event_type: EventType = EventType.JOB_FAILED
    severity: EventSeverity = EventSeverity.ERROR
    job_id: str
    source: str
    failed_stage: str
    error_type: str
    error_message: str
    retry_count: int = Field(default=0, ge=0)
    tenant_id: Optional[str] = None


class RetryAttemptEvent(BaseTelemetryEvent):
    """Event emitted when retrying a failed operation.

    Attributes:
        job_id: Job identifier
        stage: Stage being retried
        attempt_number: Retry attempt number
        max_attempts: Maximum retry attempts
        error_message: Original error message
        backoff_seconds: Backoff delay before retry
        tenant_id: Multi-tenant identifier

    Example:
        >>> event = RetryAttemptEvent(
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

    event_type: EventType = EventType.RETRY_ATTEMPT
    severity: EventSeverity = EventSeverity.WARNING
    job_id: str
    stage: str
    attempt_number: int = Field(ge=1)
    max_attempts: int = Field(ge=1)
    error_message: str
    backoff_seconds: float = Field(ge=0.0)
    tenant_id: Optional[str] = None


# Example usage
if __name__ == "__main__":
    correlation_id = str(uuid4())

    # Job started
    started = JobStartedEvent(
        job_id="job-123",
        source="file_upload",
        correlation_id=correlation_id,
        scheduled=False,
        tenant_id="tenant-123"
    )
    print("Job Started Event:")
    print(started.model_dump_json(indent=2))

    # Phase completed
    phase = PhaseCompletedEvent(
        job_id="job-123",
        phase="chunk",
        phase_number=3,
        correlation_id=correlation_id,
        duration_ms=1500.0,
        items_processed=10,
        tenant_id="tenant-123"
    )
    print("\nPhase Completed Event:")
    print(phase.model_dump_json(indent=2))

    # Job completed
    completed = JobCompletedEvent(
        job_id="job-123",
        source="file_upload",
        correlation_id=correlation_id,
        total_duration_ms=5000.0,
        chunks_created=10,
        embeddings_generated=10,
        tenant_id="tenant-123"
    )
    print("\nJob Completed Event:")
    print(completed.model_dump_json(indent=2))

    # Job failed
    failed = JobFailedEvent(
        job_id="job-123",
        source="file_upload",
        correlation_id=correlation_id,
        failed_stage="embed",
        error_type="OpenAIError",
        error_message="API rate limit exceeded",
        retry_count=2,
        tenant_id="tenant-123"
    )
    print("\nJob Failed Event:")
    print(failed.model_dump_json(indent=2))
