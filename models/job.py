"""
Job Model for Persistent Storage

Database models for job tracking and management using SQLAlchemy 2.0.

Example:
    >>> from models.job import Job
    >>> job = Job(
    ...     job_id="job-123",
    ...     source="file_upload",
    ...     status="pending",
    ...     tenant_id="tenant-abc"
    ... )
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from sqlalchemy import String, Text, DateTime, Integer, JSON, Enum as SQLEnum, Index
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class JobStatus(str, Enum):
    """Job processing status."""
    PENDING = "pending"
    FETCHING = "fetching"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    STORING = "storing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Job(Base):
    """Job model for tracking pipeline execution.

    Stores job metadata, status, and results in PostgreSQL for
    persistence and multi-instance deployment.

    Attributes:
        id: Auto-incrementing primary key
        job_id: Unique job identifier (UUID)
        correlation_id: Distributed tracing ID
        source: Source type (file_upload, url_scrape, etc.)
        status: Current job status
        tenant_id: Multi-tenant identifier
        created_at: Job creation timestamp
        completed_at: Job completion timestamp
        duration_ms: Total duration in milliseconds
        documents_stored: Number of documents stored
        chunks_created: Number of chunks created
        embeddings_generated: Number of embeddings generated
        error_message: Error message if failed
        stages_completed: List of completed stage names (JSON)
        source_params: Source-specific parameters (JSON)

    Example:
        >>> job = Job(
        ...     job_id="job-abc123",
        ...     source="file_upload",
        ...     status=JobStatus.PENDING,
        ...     tenant_id="tenant-123"
        ... )
        >>> session.add(job)
        >>> await session.commit()
    """

    __tablename__ = "jobs"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Job identifiers
    job_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    correlation_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Job metadata
    source: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        SQLEnum(JobStatus, native_enum=False, length=20),
        nullable=False,
        default=JobStatus.PENDING,
        index=True
    )
    tenant_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Results
    duration_ms: Mapped[Optional[float]] = mapped_column(nullable=True)
    documents_stored: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunks_created: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embeddings_generated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # JSON fields
    stages_completed: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True, default=list)
    source_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)

    # Indexes for common queries
    __table_args__ = (
        Index('idx_jobs_tenant_status', 'tenant_id', 'status'),
        Index('idx_jobs_tenant_created', 'tenant_id', 'created_at'),
        Index('idx_jobs_status_created', 'status', 'created_at'),
    )

    def __repr__(self) -> str:
        """String representation of Job."""
        return (
            f"<Job(job_id='{self.job_id}', source='{self.source}', "
            f"status='{self.status}', tenant_id='{self.tenant_id}')>"
        )

    def to_dict(self) -> dict:
        """Convert job to dictionary for API responses.

        Returns:
            Dictionary representation of job

        Example:
            >>> job = Job(job_id="job-123", source="file_upload")
            >>> data = job.to_dict()
            >>> print(data["job_id"])
            job-123
        """
        return {
            "job_id": self.job_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "status": self.status,
            "tenant_id": self.tenant_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_ms": self.duration_ms,
            "documents_stored": self.documents_stored,
            "chunks_created": self.chunks_created,
            "embeddings_generated": self.embeddings_generated,
            "error_message": self.error_message,
            "stages_completed": self.stages_completed or [],
        }
