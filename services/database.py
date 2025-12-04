"""
Database Service for Job Management

Provides async database operations for job persistence using SQLAlchemy 2.0.

Example:
    >>> from services.database import DatabaseService
    >>> db = DatabaseService()
    >>> await db.create_job(job_data)
    >>> job = await db.get_job("job-123")
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import asynccontextmanager

from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from models.job import Job, JobStatus, Base

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """Exception raised when database operation fails."""

    def __init__(self, message: str, **context):
        self.message = message
        self.context = context
        super().__init__(message)


class DatabaseService:
    """Service for async database operations.

    Manages job persistence, queries, and updates using SQLAlchemy 2.0
    with async support.

    Attributes:
        engine: Async SQLAlchemy engine
        session_factory: Async session factory

    Example:
        >>> db = DatabaseService()
        >>> await db.init()
        >>> job = await db.create_job({
        ...     "job_id": "job-123",
        ...     "source": "file_upload",
        ...     "status": "pending"
        ... })
    """

    def __init__(self, database_url: Optional[str] = None):
        """Initialize database service.

        Args:
            database_url: Database connection URL (defaults to settings)

        Example:
            >>> db = DatabaseService()
            >>> # or with custom URL
            >>> db = DatabaseService("postgresql+asyncpg://localhost/testdb")
        """
        self.database_url = database_url or settings.DATABASE_URL
        self.logger = logging.getLogger(__name__)
        self._engine = None
        self._session_factory = None

    async def init(self) -> None:
        """Initialize database engine and session factory.

        Should be called during application startup.

        Example:
            >>> db = DatabaseService()
            >>> await db.init()
        """
        try:
            self._engine = create_async_engine(
                self.database_url,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_pre_ping=True,
                echo=settings.ENVIRONMENT == "development"
            )

            self._session_factory = async_sessionmaker(
                self._engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            self.logger.info("Database service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize database: {str(e)}")
            raise DatabaseError(f"Database initialization failed: {str(e)}")

    async def close(self) -> None:
        """Close database connections.

        Should be called during application shutdown.

        Example:
            >>> await db.close()
        """
        if self._engine:
            await self._engine.dispose()
            self.logger.info("Database connections closed")

    @asynccontextmanager
    async def session(self):
        """Get async database session.

        Yields:
            AsyncSession: Database session

        Example:
            >>> async with db.session() as session:
            ...     result = await session.execute(select(Job))
        """
        if not self._session_factory:
            raise DatabaseError("Database not initialized. Call init() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                raise e

    async def health_check(self) -> bool:
        """Check database connectivity.

        Returns:
            True if healthy, False otherwise

        Example:
            >>> is_healthy = await db.health_check()
        """
        try:
            if not self._engine:
                return False

            async with self.session() as session:
                await session.execute(select(1))
            return True

        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return False

    async def create_job(self, job_data: Dict[str, Any]) -> Job:
        """Create a new job record.

        Args:
            job_data: Job data dictionary

        Returns:
            Created Job instance

        Raises:
            DatabaseError: If creation fails

        Example:
            >>> job = await db.create_job({
            ...     "job_id": "job-123",
            ...     "source": "file_upload",
            ...     "status": "pending",
            ...     "tenant_id": "tenant-abc"
            ... })
        """
        try:
            async with self.session() as session:
                job = Job(
                    job_id=job_data["job_id"],
                    correlation_id=job_data.get("correlation_id"),
                    source=job_data["source"],
                    status=job_data.get("status", JobStatus.PENDING),
                    tenant_id=job_data.get("tenant_id"),
                    created_at=job_data.get("created_at", datetime.utcnow()),
                    stages_completed=job_data.get("stages_completed", []),
                    source_params=job_data.get("source_params", {})
                )

                session.add(job)
                await session.commit()
                await session.refresh(job)

                self.logger.info(f"Created job: {job.job_id}")
                return job

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to create job: {str(e)}")
            raise DatabaseError(f"Failed to create job: {str(e)}")

    async def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID.

        Args:
            job_id: Job identifier

        Returns:
            Job instance or None if not found

        Example:
            >>> job = await db.get_job("job-123")
            >>> if job:
            ...     print(job.status)
        """
        try:
            async with self.session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                return result.scalar_one_or_none()

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get job {job_id}: {str(e)}")
            return None

    async def update_job(self, job_id: str, updates: Dict[str, Any]) -> Optional[Job]:
        """Update job fields.

        Args:
            job_id: Job identifier
            updates: Fields to update

        Returns:
            Updated Job instance or None if not found

        Raises:
            DatabaseError: If update fails

        Example:
            >>> job = await db.update_job("job-123", {
            ...     "status": "completed",
            ...     "completed_at": datetime.utcnow(),
            ...     "chunks_created": 42
            ... })
        """
        try:
            async with self.session() as session:
                result = await session.execute(
                    select(Job).where(Job.job_id == job_id)
                )
                job = result.scalar_one_or_none()

                if not job:
                    return None

                for key, value in updates.items():
                    if hasattr(job, key):
                        setattr(job, key, value)

                await session.commit()
                await session.refresh(job)

                self.logger.info(f"Updated job: {job_id}")
                return job

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to update job {job_id}: {str(e)}")
            raise DatabaseError(f"Failed to update job: {str(e)}")

    async def list_jobs(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Job], int]:
        """List jobs with filtering and pagination.

        Args:
            tenant_id: Filter by tenant
            status: Filter by status
            page: Page number (1-indexed)
            page_size: Number of jobs per page

        Returns:
            Tuple of (jobs list, total count)

        Example:
            >>> jobs, total = await db.list_jobs(
            ...     tenant_id="tenant-123",
            ...     status="completed",
            ...     page=1,
            ...     page_size=20
            ... )
        """
        try:
            async with self.session() as session:
                # Build base query
                query = select(Job)

                # Apply filters
                if tenant_id:
                    query = query.where(Job.tenant_id == tenant_id)
                if status:
                    query = query.where(Job.status == status)

                # Get total count
                count_query = select(func.count()).select_from(query.subquery())
                total_result = await session.execute(count_query)
                total = total_result.scalar()

                # Apply pagination and ordering
                query = query.order_by(desc(Job.created_at))
                query = query.offset((page - 1) * page_size).limit(page_size)

                # Execute query
                result = await session.execute(query)
                jobs = result.scalars().all()

                return list(jobs), total

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to list jobs: {str(e)}")
            return [], 0

    async def delete_job(self, job_id: str) -> bool:
        """Delete job by ID.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted, False if not found

        Example:
            >>> deleted = await db.delete_job("job-123")
        """
        try:
            async with self.session() as session:
                result = await session.execute(
                    delete(Job).where(Job.job_id == job_id)
                )
                await session.commit()

                if result.rowcount > 0:
                    self.logger.info(f"Deleted job: {job_id}")
                    return True
                return False

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to delete job {job_id}: {str(e)}")
            return False

    async def get_active_jobs(self, tenant_id: Optional[str] = None) -> List[Job]:
        """Get all active (non-completed/non-failed) jobs.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of active jobs

        Example:
            >>> active_jobs = await db.get_active_jobs(tenant_id="tenant-123")
        """
        try:
            async with self.session() as session:
                query = select(Job).where(
                    Job.status.not_in([JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED])
                )

                if tenant_id:
                    query = query.where(Job.tenant_id == tenant_id)

                result = await session.execute(query)
                return list(result.scalars().all())

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get active jobs: {str(e)}")
            return []


# Global database service instance
_db_service: Optional[DatabaseService] = None


def get_database() -> DatabaseService:
    """Get global database service instance.

    Returns:
        DatabaseService instance

    Example:
        >>> db = get_database()
        >>> await db.init()
    """
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
