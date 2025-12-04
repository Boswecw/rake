"""
Rake API Routes

REST API endpoints for the Rake data ingestion pipeline.

Endpoints:
    POST   /api/v1/jobs          - Submit new ingestion job
    GET    /api/v1/jobs/{job_id} - Get job status
    GET    /api/v1/jobs          - List jobs (with filters)
    DELETE /api/v1/jobs/{job_id} - Cancel job
    GET    /api/v1/health        - Health check

Example:
    >>> import httpx
    >>> response = await httpx.post(
    ...     "http://localhost:8000/api/v1/jobs",
    ...     json={
    ...         "source": "file_upload",
    ...         "file_path": "/path/to/doc.pdf",
    ...         "tenant_id": "tenant-123"
    ...     }
    ... )
    >>> print(response.json())
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict

from pipeline.orchestrator import PipelineOrchestrator, PipelineError
from services.telemetry_client import telemetry

logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================


class JobSubmitRequest(BaseModel):
    """Request schema for submitting a new ingestion job.

    Attributes:
        source: Source type (file_upload, url_scrape, etc.)
        tenant_id: Multi-tenant identifier
        file_path: Path to file (for file_upload source)
        url: URL to scrape (for url_scrape source)
        scheduled: Whether job is scheduled (default: False)
        metadata: Additional job metadata

    Example:
        >>> request = JobSubmitRequest(
        ...     source="file_upload",
        ...     tenant_id="tenant-123",
        ...     file_path="/path/to/document.pdf"
        ... )
    """

    model_config = ConfigDict(extra="allow")

    source: str = Field(..., description="Source type (file_upload, url_scrape, etc.)")
    tenant_id: Optional[str] = Field(None, description="Multi-tenant identifier")
    file_path: Optional[str] = Field(None, description="File path for file_upload source")
    url: Optional[str] = Field(None, description="URL for url_scrape source")
    scheduled: bool = Field(default=False, description="Whether job is scheduled")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class JobResponse(BaseModel):
    """Response schema for job operations.

    Attributes:
        job_id: Job identifier
        correlation_id: Distributed tracing ID
        status: Job status (pending, fetching, cleaning, chunking, embedding, storing, completed, failed)
        source: Source type
        tenant_id: Multi-tenant identifier
        created_at: Job creation timestamp
        completed_at: Job completion timestamp
        duration_ms: Total duration in milliseconds
        documents_stored: Number of documents stored
        chunks_created: Number of chunks created
        embeddings_generated: Number of embeddings generated
        error_message: Error message if failed
        stages_completed: List of completed stage names

    Example:
        >>> response = JobResponse(
        ...     job_id="job-abc123",
        ...     status="completed",
        ...     source="file_upload",
        ...     chunks_created=10
        ... )
    """

    model_config = ConfigDict(use_enum_values=True)

    job_id: str
    correlation_id: Optional[str] = None
    status: str
    source: str
    tenant_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: Optional[float] = None
    documents_stored: Optional[int] = None
    chunks_created: Optional[int] = None
    embeddings_generated: Optional[int] = None
    error_message: Optional[str] = None
    stages_completed: List[str] = Field(default_factory=list)


class JobListResponse(BaseModel):
    """Response schema for job list endpoint.

    Attributes:
        jobs: List of jobs
        total: Total number of jobs
        page: Current page number
        page_size: Number of jobs per page

    Example:
        >>> response = JobListResponse(
        ...     jobs=[job1, job2],
        ...     total=2,
        ...     page=1,
        ...     page_size=10
        ... )
    """

    jobs: List[JobResponse]
    total: int
    page: int = 1
    page_size: int = 10


# ============================================================================
# IN-MEMORY JOB STORAGE (TODO: Replace with database)
# ============================================================================

# TODO: Replace with database persistence (PostgreSQL + SQLAlchemy)
# This is a temporary in-memory store for development/testing
_job_store: Dict[str, Dict[str, Any]] = {}
_job_store_lock = asyncio.Lock()


async def _store_job(job_data: Dict[str, Any]) -> None:
    """Store job in in-memory storage.

    TODO: Replace with database INSERT operation.

    Args:
        job_data: Job data dictionary

    Example:
        >>> await _store_job({"job_id": "job-123", "status": "pending"})
    """
    async with _job_store_lock:
        _job_store[job_data["job_id"]] = job_data


async def _get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job from in-memory storage.

    TODO: Replace with database SELECT operation.

    Args:
        job_id: Job identifier

    Returns:
        Job data or None if not found

    Example:
        >>> job = await _get_job("job-123")
    """
    async with _job_store_lock:
        return _job_store.get(job_id)


async def _update_job(job_id: str, updates: Dict[str, Any]) -> None:
    """Update job in in-memory storage.

    TODO: Replace with database UPDATE operation.

    Args:
        job_id: Job identifier
        updates: Fields to update

    Example:
        >>> await _update_job("job-123", {"status": "completed"})
    """
    async with _job_store_lock:
        if job_id in _job_store:
            _job_store[job_id].update(updates)


async def _list_jobs(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> tuple[List[Dict[str, Any]], int]:
    """List jobs from in-memory storage.

    TODO: Replace with database SELECT with filters and pagination.

    Args:
        tenant_id: Filter by tenant
        status: Filter by status
        page: Page number (1-indexed)
        page_size: Number of jobs per page

    Returns:
        Tuple of (jobs list, total count)

    Example:
        >>> jobs, total = await _list_jobs(tenant_id="tenant-123", page=1)
    """
    async with _job_store_lock:
        # Filter jobs
        jobs = list(_job_store.values())

        if tenant_id:
            jobs = [j for j in jobs if j.get("tenant_id") == tenant_id]
        if status:
            jobs = [j for j in jobs if j.get("status") == status]

        # Sort by created_at descending
        jobs.sort(key=lambda x: x.get("created_at", datetime.min), reverse=True)

        total = len(jobs)

        # Paginate
        start = (page - 1) * page_size
        end = start + page_size
        paginated_jobs = jobs[start:end]

        return paginated_jobs, total


# ============================================================================
# BACKGROUND JOB EXECUTION
# ============================================================================


async def _run_pipeline_job(
    job_id: str,
    source: str,
    tenant_id: Optional[str],
    correlation_id: str,
    **source_params
) -> None:
    """Run pipeline job in background.

    Executes the complete 5-stage pipeline and updates job status.

    Args:
        job_id: Job identifier
        source: Source type
        tenant_id: Multi-tenant identifier
        correlation_id: Distributed tracing ID
        **source_params: Source-specific parameters

    Example:
        >>> await _run_pipeline_job(
        ...     job_id="job-123",
        ...     source="file_upload",
        ...     tenant_id="tenant-123",
        ...     correlation_id="trace-abc",
        ...     file_path="/path/to/doc.pdf"
        ... )
    """
    orchestrator = PipelineOrchestrator()

    try:
        logger.info(
            f"Starting background pipeline job: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "source": source,
                "tenant_id": tenant_id
            }
        )

        # Update job status to processing
        await _update_job(job_id, {"status": "fetching"})

        # Run pipeline
        result = await orchestrator.run(
            source=source,
            tenant_id=tenant_id,
            job_id=job_id,
            correlation_id=correlation_id,
            **source_params
        )

        # Update job with results
        await _update_job(
            job_id,
            {
                "status": result["status"],
                "completed_at": datetime.utcnow(),
                "duration_ms": result["duration_ms"],
                "documents_stored": result["documents_stored"],
                "chunks_created": result["chunks_created"],
                "embeddings_generated": result["embeddings_generated"],
                "stages_completed": result["stages_completed"],
            }
        )

        logger.info(
            f"Pipeline job completed: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "duration_ms": result["duration_ms"],
                "chunks_created": result["chunks_created"]
            }
        )

    except PipelineError as e:
        # Pipeline-specific error
        error_msg = str(e)
        logger.error(
            f"Pipeline job failed: {job_id} - {error_msg}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "error": error_msg
            },
            exc_info=True
        )

        await _update_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error_message": error_msg,
            }
        )

    except Exception as e:
        # Unexpected error
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(
            f"Pipeline job failed with unexpected error: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "error": error_msg
            },
            exc_info=True
        )

        await _update_job(
            job_id,
            {
                "status": "failed",
                "completed_at": datetime.utcnow(),
                "error_message": error_msg,
            }
        )

    finally:
        # Cleanup
        await orchestrator.close()


# ============================================================================
# API ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1", tags=["jobs"])


@router.post("/jobs", response_model=JobResponse, status_code=202)
async def submit_job(
    request: JobSubmitRequest,
    background_tasks: BackgroundTasks
) -> JobResponse:
    """Submit a new ingestion job.

    Accepts job parameters and queues the job for background processing.
    Returns immediately with job_id and status.

    Args:
        request: Job submission request
        background_tasks: FastAPI background tasks

    Returns:
        JobResponse with job_id and initial status

    Raises:
        HTTPException: 400 if validation fails

    Example:
        >>> response = await client.post(
        ...     "/api/v1/jobs",
        ...     json={
        ...         "source": "file_upload",
        ...         "file_path": "/path/to/doc.pdf",
        ...         "tenant_id": "tenant-123"
        ...     }
        ... )
        >>> print(response.json()["job_id"])
        job-abc123def456
    """
    # Generate IDs
    job_id = f"job-{uuid4().hex[:12]}"
    correlation_id = str(uuid4())

    # Validate source-specific parameters
    if request.source == "file_upload" and not request.file_path:
        raise HTTPException(
            status_code=400,
            detail="file_path is required for file_upload source"
        )
    elif request.source == "url_scrape" and not request.url:
        raise HTTPException(
            status_code=400,
            detail="url is required for url_scrape source"
        )

    # Create job record
    job_data = {
        "job_id": job_id,
        "correlation_id": correlation_id,
        "status": "pending",
        "source": request.source,
        "tenant_id": request.tenant_id,
        "created_at": datetime.utcnow(),
        "completed_at": None,
        "duration_ms": None,
        "documents_stored": None,
        "chunks_created": None,
        "embeddings_generated": None,
        "error_message": None,
        "stages_completed": [],
    }

    # Store job
    await _store_job(job_data)

    # Queue background task
    source_params = {}
    if request.file_path:
        source_params["file_path"] = request.file_path
    if request.url:
        source_params["url"] = request.url
    if request.scheduled:
        source_params["scheduled"] = request.scheduled
    # Include any extra fields from request
    source_params.update(request.metadata)

    background_tasks.add_task(
        _run_pipeline_job,
        job_id=job_id,
        source=request.source,
        tenant_id=request.tenant_id,
        correlation_id=correlation_id,
        **source_params
    )

    logger.info(
        f"Job submitted: {job_id}",
        extra={
            "correlation_id": correlation_id,
            "job_id": job_id,
            "source": request.source,
            "tenant_id": request.tenant_id
        }
    )

    return JobResponse(**job_data)


@router.get("/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: str) -> JobResponse:
    """Get job status and details.

    Args:
        job_id: Job identifier

    Returns:
        JobResponse with current job status

    Raises:
        HTTPException: 404 if job not found

    Example:
        >>> response = await client.get("/api/v1/jobs/job-abc123")
        >>> print(response.json()["status"])
        completed
    """
    job_data = await _get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    return JobResponse(**job_data)


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant_id"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(10, ge=1, le=100, description="Jobs per page")
) -> JobListResponse:
    """List jobs with optional filters and pagination.

    Args:
        tenant_id: Filter by tenant (optional)
        status: Filter by status (optional)
        page: Page number (1-indexed)
        page_size: Number of jobs per page (1-100)

    Returns:
        JobListResponse with paginated jobs

    Example:
        >>> response = await client.get(
        ...     "/api/v1/jobs?tenant_id=tenant-123&page=1&page_size=10"
        ... )
        >>> print(f"Total jobs: {response.json()['total']}")
    """
    jobs, total = await _list_jobs(
        tenant_id=tenant_id,
        status=status,
        page=page,
        page_size=page_size
    )

    job_responses = [JobResponse(**job) for job in jobs]

    return JobListResponse(
        jobs=job_responses,
        total=total,
        page=page,
        page_size=page_size
    )


@router.delete("/jobs/{job_id}", status_code=204)
async def cancel_job(job_id: str) -> None:
    """Cancel a pending or running job.

    TODO: Implement job cancellation logic. Currently this is a no-op
    because we don't have a mechanism to cancel background tasks in FastAPI.
    Consider using Celery or similar for production.

    Args:
        job_id: Job identifier

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 409 if job already completed

    Example:
        >>> await client.delete("/api/v1/jobs/job-abc123")
    """
    job_data = await _get_job(job_id)

    if not job_data:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if job_data["status"] in ["completed", "failed"]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel job with status: {job_data['status']}"
        )

    # TODO: Implement actual cancellation mechanism
    # For now, just mark as cancelled
    await _update_job(job_id, {"status": "cancelled"})

    logger.info(
        f"Job cancelled: {job_id}",
        extra={
            "job_id": job_id,
            "previous_status": job_data["status"]
        }
    )


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint.

    Returns service status and basic statistics.

    Returns:
        Health status dictionary

    Example:
        >>> response = await client.get("/api/v1/health")
        >>> print(response.json()["status"])
        healthy
    """
    async with _job_store_lock:
        total_jobs = len(_job_store)
        pending_jobs = len([j for j in _job_store.values() if j["status"] == "pending"])
        running_jobs = len([
            j for j in _job_store.values()
            if j["status"] in ["fetching", "cleaning", "chunking", "embedding", "storing"]
        ])
        completed_jobs = len([j for j in _job_store.values() if j["status"] == "completed"])
        failed_jobs = len([j for j in _job_store.values() if j["status"] == "failed"])

    return {
        "status": "healthy",
        "service": "rake",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "statistics": {
            "total_jobs": total_jobs,
            "pending_jobs": pending_jobs,
            "running_jobs": running_jobs,
            "completed_jobs": completed_jobs,
            "failed_jobs": failed_jobs,
        }
    }


# Example usage and testing
if __name__ == "__main__":
    import asyncio
    from fastapi.testclient import TestClient
    from fastapi import FastAPI

    # Create test app
    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)

    # Test job submission
    print("Testing job submission...")
    response = client.post(
        "/api/v1/jobs",
        json={
            "source": "file_upload",
            "file_path": "/path/to/test.pdf",
            "tenant_id": "tenant-test"
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    job_id = response.json()["job_id"]

    # Test job retrieval
    print(f"\nTesting job retrieval for {job_id}...")
    response = client.get(f"/api/v1/jobs/{job_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test job list
    print("\nTesting job list...")
    response = client.get("/api/v1/jobs?page=1&page_size=10")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")

    # Test health check
    print("\nTesting health check...")
    response = client.get("/api/v1/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
