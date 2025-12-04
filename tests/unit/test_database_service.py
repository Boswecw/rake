"""
Tests for Database Service

Tests the DatabaseService class for job persistence and CRUD operations.
Uses SQLite in-memory database for fast, isolated testing.

Example:
    >>> pytest tests/unit/test_database_service.py -v
"""

import pytest
from datetime import datetime
from typing import List

from services.database import DatabaseService, DatabaseError
from models.job import Job, JobStatus


# ============================================================================
# Initialization Tests
# ============================================================================


class TestDatabaseServiceInit:
    """Test database service initialization."""

    @pytest.mark.asyncio
    async def test_init_creates_instance(self):
        """Test that DatabaseService initializes correctly."""
        db = DatabaseService()
        assert db is not None
        assert db._engine is None  # Not initialized yet
        assert db._session_factory is None

    @pytest.mark.asyncio
    async def test_init_with_custom_url(self):
        """Test initialization with custom database URL."""
        db = DatabaseService(database_url="sqlite+aiosqlite:///:memory:")
        assert db.database_url == "sqlite+aiosqlite:///:memory:"

    @pytest.mark.asyncio
    async def test_init_method(self, test_db):
        """Test that init() sets up engine and session factory."""
        assert test_db._engine is not None
        assert test_db._session_factory is not None

    @pytest.mark.asyncio
    async def test_close_method(self, test_db):
        """Test that close() disposes engine."""
        await test_db.close()
        # After close, engine should be disposed
        # Note: We can't easily verify disposal, but we can verify no errors


# ============================================================================
# Health Check Tests
# ============================================================================


class TestHealthCheck:
    """Test database health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, test_db):
        """Test health check returns True when database is accessible."""
        is_healthy = await test_db.health_check()
        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_before_init(self):
        """Test health check returns False when not initialized."""
        db = DatabaseService()
        is_healthy = await db.health_check()
        assert is_healthy is False


# ============================================================================
# Create Job Tests
# ============================================================================


class TestCreateJob:
    """Test job creation operations."""

    @pytest.mark.asyncio
    async def test_create_job_minimal(self, test_db):
        """Test creating a job with minimal required fields."""
        job_data = {
            "job_id": "job-minimal-test",
            "source": "file_upload",
            "status": JobStatus.PENDING,
        }

        job = await test_db.create_job(job_data)

        assert job is not None
        assert job.job_id == "job-minimal-test"
        assert job.source == "file_upload"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None
        assert job.stages_completed == []
        assert job.source_params == {}

    @pytest.mark.asyncio
    async def test_create_job_with_all_fields(self, test_db):
        """Test creating a job with all fields populated."""
        job_data = {
            "job_id": "job-complete-test",
            "correlation_id": "corr-123",
            "source": "url_scrape",
            "status": JobStatus.COMPLETED,
            "tenant_id": "tenant-abc",
            "created_at": datetime.utcnow(),
            "completed_at": datetime.utcnow(),
            "duration_ms": 1500.0,
            "documents_stored": 5,
            "chunks_created": 25,
            "embeddings_generated": 25,
            "stages_completed": ["fetch", "clean", "chunk", "embed", "store"],
            "source_params": {"url": "https://example.com"}
        }

        job = await test_db.create_job(job_data)

        assert job.job_id == "job-complete-test"
        assert job.correlation_id == "corr-123"
        assert job.source == "url_scrape"
        assert job.status == JobStatus.COMPLETED
        assert job.tenant_id == "tenant-abc"
        assert job.duration_ms == 1500.0
        assert job.documents_stored == 5
        assert job.chunks_created == 25
        assert job.embeddings_generated == 25
        assert job.stages_completed == ["fetch", "clean", "chunk", "embed", "store"]
        assert job.source_params == {"url": "https://example.com"}

    @pytest.mark.asyncio
    async def test_create_job_with_error(self, test_db):
        """Test creating a failed job with error message."""
        job_data = {
            "job_id": "job-failed-test",
            "source": "api_fetch",
            "status": JobStatus.FAILED,
            "error_message": "Connection timeout",
            "source_params": {}
        }

        job = await test_db.create_job(job_data)

        assert job.job_id == "job-failed-test"
        assert job.status == JobStatus.FAILED
        assert job.error_message == "Connection timeout"


# ============================================================================
# Get Job Tests
# ============================================================================


class TestGetJob:
    """Test job retrieval operations."""

    @pytest.mark.asyncio
    async def test_get_existing_job(self, test_db_with_jobs):
        """Test getting a job that exists."""
        job = await test_db_with_jobs.get_job("job-test-1")

        assert job is not None
        assert job.job_id == "job-test-1"
        assert job.source == "file_upload"
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, test_db):
        """Test getting a job that doesn't exist."""
        job = await test_db.get_job("job-nonexistent")
        assert job is None

    @pytest.mark.asyncio
    async def test_get_job_returns_correct_data(self, test_db_with_jobs):
        """Test that retrieved job has all correct fields."""
        job = await test_db_with_jobs.get_job("job-test-1")

        assert job.job_id == "job-test-1"
        assert job.source == "file_upload"
        assert job.status == JobStatus.COMPLETED
        assert job.tenant_id == "tenant-test"
        assert job.chunks_created == 10


# ============================================================================
# Update Job Tests
# ============================================================================


class TestUpdateJob:
    """Test job update operations."""

    @pytest.mark.asyncio
    async def test_update_job_status(self, test_db_with_jobs):
        """Test updating job status."""
        updates = {"status": JobStatus.COMPLETED}
        job = await test_db_with_jobs.update_job("job-test-2", updates)

        assert job is not None
        assert job.job_id == "job-test-2"
        assert job.status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_update_job_multiple_fields(self, test_db_with_jobs):
        """Test updating multiple job fields."""
        updates = {
            "status": JobStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
            "duration_ms": 2500.0,
            "chunks_created": 42,
            "embeddings_generated": 42,
        }
        job = await test_db_with_jobs.update_job("job-test-2", updates)

        assert job.status == JobStatus.COMPLETED
        assert job.completed_at is not None
        assert job.duration_ms == 2500.0
        assert job.chunks_created == 42
        assert job.embeddings_generated == 42

    @pytest.mark.asyncio
    async def test_update_nonexistent_job(self, test_db):
        """Test updating a job that doesn't exist."""
        updates = {"status": JobStatus.COMPLETED}
        job = await test_db.update_job("job-nonexistent", updates)
        assert job is None

    @pytest.mark.asyncio
    async def test_update_stages_completed(self, test_db_with_jobs):
        """Test updating stages_completed list."""
        updates = {
            "stages_completed": ["fetch", "clean", "chunk"]
        }
        job = await test_db_with_jobs.update_job("job-test-2", updates)

        assert job.stages_completed == ["fetch", "clean", "chunk"]


# ============================================================================
# List Jobs Tests
# ============================================================================


class TestListJobs:
    """Test job listing operations."""

    @pytest.mark.asyncio
    async def test_list_all_jobs(self, test_db_with_jobs):
        """Test listing all jobs without filters."""
        jobs, total = await test_db_with_jobs.list_jobs()

        assert total == 3
        assert len(jobs) == 3

    @pytest.mark.asyncio
    async def test_list_jobs_by_tenant(self, test_db_with_jobs):
        """Test filtering jobs by tenant_id."""
        jobs, total = await test_db_with_jobs.list_jobs(tenant_id="tenant-test")

        assert total == 2  # job-test-1 and job-test-2
        assert len(jobs) == 2
        assert all(job.tenant_id == "tenant-test" for job in jobs)

    @pytest.mark.asyncio
    async def test_list_jobs_by_status(self, test_db_with_jobs):
        """Test filtering jobs by status."""
        jobs, total = await test_db_with_jobs.list_jobs(status="completed")

        assert total == 1  # Only job-test-1
        assert len(jobs) == 1
        assert jobs[0].status == JobStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_list_jobs_with_pagination(self, test_db_with_jobs):
        """Test job pagination."""
        # Page 1: First 2 jobs
        jobs_page1, total = await test_db_with_jobs.list_jobs(page=1, page_size=2)
        assert total == 3
        assert len(jobs_page1) == 2

        # Page 2: Last 1 job
        jobs_page2, total = await test_db_with_jobs.list_jobs(page=2, page_size=2)
        assert total == 3
        assert len(jobs_page2) == 1

    @pytest.mark.asyncio
    async def test_list_jobs_combined_filters(self, test_db_with_jobs):
        """Test combining tenant and status filters."""
        jobs, total = await test_db_with_jobs.list_jobs(
            tenant_id="tenant-test",
            status="pending"
        )

        assert total == 1  # Only job-test-2
        assert len(jobs) == 1
        assert jobs[0].job_id == "job-test-2"

    @pytest.mark.asyncio
    async def test_list_jobs_empty_result(self, test_db):
        """Test listing jobs when database is empty."""
        jobs, total = await test_db.list_jobs()

        assert total == 0
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_list_jobs_ordered_by_created_at(self, test_db_with_jobs):
        """Test that jobs are ordered by created_at descending."""
        jobs, total = await test_db_with_jobs.list_jobs()

        # Jobs should be ordered by created_at DESC (newest first)
        for i in range(len(jobs) - 1):
            assert jobs[i].created_at >= jobs[i + 1].created_at


# ============================================================================
# Delete Job Tests
# ============================================================================


class TestDeleteJob:
    """Test job deletion operations."""

    @pytest.mark.asyncio
    async def test_delete_existing_job(self, test_db_with_jobs):
        """Test deleting a job that exists."""
        deleted = await test_db_with_jobs.delete_job("job-test-1")
        assert deleted is True

        # Verify job is gone
        job = await test_db_with_jobs.get_job("job-test-1")
        assert job is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_job(self, test_db):
        """Test deleting a job that doesn't exist."""
        deleted = await test_db.delete_job("job-nonexistent")
        assert deleted is False


# ============================================================================
# Get Active Jobs Tests
# ============================================================================


class TestGetActiveJobs:
    """Test active jobs retrieval."""

    @pytest.mark.asyncio
    async def test_get_active_jobs(self, test_db_with_jobs):
        """Test getting all active (non-completed/failed) jobs."""
        active_jobs = await test_db_with_jobs.get_active_jobs()

        # job-test-2 is pending (active)
        # job-test-1 is completed (not active)
        # job-test-3 is failed (not active)
        assert len(active_jobs) == 1
        assert active_jobs[0].job_id == "job-test-2"
        assert active_jobs[0].status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_active_jobs_by_tenant(self, test_db_with_jobs):
        """Test getting active jobs filtered by tenant."""
        active_jobs = await test_db_with_jobs.get_active_jobs(tenant_id="tenant-test")

        assert len(active_jobs) == 1
        assert active_jobs[0].tenant_id == "tenant-test"
        assert active_jobs[0].status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_active_jobs_empty(self, test_db):
        """Test getting active jobs when none exist."""
        active_jobs = await test_db.get_active_jobs()
        assert len(active_jobs) == 0


# ============================================================================
# Job Model Tests
# ============================================================================


class TestJobModel:
    """Test Job model methods."""

    @pytest.mark.asyncio
    async def test_job_to_dict(self, test_db_with_jobs):
        """Test Job.to_dict() conversion."""
        job = await test_db_with_jobs.get_job("job-test-1")
        job_dict = job.to_dict()

        assert isinstance(job_dict, dict)
        assert job_dict["job_id"] == "job-test-1"
        assert job_dict["source"] == "file_upload"
        assert job_dict["status"] == JobStatus.COMPLETED
        assert job_dict["tenant_id"] == "tenant-test"
        assert "created_at" in job_dict
        assert isinstance(job_dict["created_at"], str)  # ISO format

    @pytest.mark.asyncio
    async def test_job_repr(self, test_db_with_jobs):
        """Test Job.__repr__() string representation."""
        job = await test_db_with_jobs.get_job("job-test-1")
        repr_str = repr(job)

        assert "job-test-1" in repr_str
        assert "file_upload" in repr_str
        assert "tenant-test" in repr_str


# ============================================================================
# Session Context Manager Tests
# ============================================================================


class TestSessionContextManager:
    """Test database session context manager."""

    @pytest.mark.asyncio
    async def test_session_commits_on_success(self, test_db):
        """Test that session commits on successful operations."""
        async with test_db.session() as session:
            job = Job(
                job_id="job-session-test",
                source="file_upload",
                status=JobStatus.PENDING,
                source_params={}
            )
            session.add(job)
        # No need to call commit - context manager does it

        # Verify job was committed
        retrieved_job = await test_db.get_job("job-session-test")
        assert retrieved_job is not None
        assert retrieved_job.job_id == "job-session-test"

    @pytest.mark.asyncio
    async def test_session_raises_before_init(self):
        """Test that session raises error if database not initialized."""
        db = DatabaseService()

        with pytest.raises(DatabaseError, match="not initialized"):
            async with db.session() as session:
                pass


# ============================================================================
# Integration Tests
# ============================================================================


class TestDatabaseIntegration:
    """Test complete database workflows."""

    @pytest.mark.asyncio
    async def test_complete_job_lifecycle(self, test_db):
        """Test complete job lifecycle from creation to completion."""
        # Create pending job
        job_data = {
            "job_id": "job-lifecycle-test",
            "source": "url_scrape",
            "status": JobStatus.PENDING,
            "tenant_id": "tenant-integration",
            "source_params": {"url": "https://example.com"}
        }
        created_job = await test_db.create_job(job_data)
        assert created_job.status == JobStatus.PENDING

        # Update to in-progress
        await test_db.update_job("job-lifecycle-test", {"status": JobStatus.FETCHING})
        job = await test_db.get_job("job-lifecycle-test")
        assert job.status == JobStatus.FETCHING

        # Update to completed with results
        await test_db.update_job("job-lifecycle-test", {
            "status": JobStatus.COMPLETED,
            "completed_at": datetime.utcnow(),
            "duration_ms": 3000.0,
            "chunks_created": 15,
            "embeddings_generated": 15,
            "stages_completed": ["fetch", "clean", "chunk", "embed", "store"]
        })
        job = await test_db.get_job("job-lifecycle-test")
        assert job.status == JobStatus.COMPLETED
        assert job.chunks_created == 15

    @pytest.mark.asyncio
    async def test_multiple_tenants_isolation(self, test_db):
        """Test that tenant filtering correctly isolates data."""
        # Create jobs for different tenants
        await test_db.create_job({
            "job_id": "job-tenant-a-1",
            "source": "file_upload",
            "tenant_id": "tenant-a",
            "source_params": {}
        })
        await test_db.create_job({
            "job_id": "job-tenant-a-2",
            "source": "file_upload",
            "tenant_id": "tenant-a",
            "source_params": {}
        })
        await test_db.create_job({
            "job_id": "job-tenant-b-1",
            "source": "file_upload",
            "tenant_id": "tenant-b",
            "source_params": {}
        })

        # Query tenant-a jobs
        jobs_a, total_a = await test_db.list_jobs(tenant_id="tenant-a")
        assert total_a == 2
        assert all(job.tenant_id == "tenant-a" for job in jobs_a)

        # Query tenant-b jobs
        jobs_b, total_b = await test_db.list_jobs(tenant_id="tenant-b")
        assert total_b == 1
        assert jobs_b[0].tenant_id == "tenant-b"
