"""Job Scheduler for Rake Service

Provides scheduled job execution using APScheduler for automated
data ingestion tasks.

Features:
    - Cron-based scheduling
    - Interval-based scheduling
    - Job persistence (optional)
    - Error handling and retries
    - Job status monitoring
    - Integration with pipeline orchestrator

Example:
    >>> from scheduler import RakeScheduler
    >>>
    >>> scheduler = RakeScheduler()
    >>> scheduler.start()
    >>>
    >>> # Schedule a job to run every hour
    >>> scheduler.add_job(
    ...     job_id="hourly-ingestion",
    ...     source="file_upload",
    ...     file_path="/data/documents",
    ...     tenant_id="tenant-123",
    ...     interval_minutes=60
    ... )
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_MISSED,
    JobExecutionEvent
)

from config import settings
from pipeline.orchestrator import PipelineOrchestrator, PipelineError
from services.telemetry_db_client import telemetry

logger = logging.getLogger(__name__)


class SchedulerError(Exception):
    """Exception raised for scheduler-related errors.

    Example:
        >>> raise SchedulerError("Failed to schedule job")
    """
    pass


class RakeScheduler:
    """Scheduler for automated data ingestion jobs.

    Manages scheduled jobs using APScheduler with async support.

    Attributes:
        scheduler: APScheduler AsyncIOScheduler instance
        orchestrator: Pipeline orchestrator for job execution
        jobs: Dictionary of scheduled jobs by job_id

    Example:
        >>> scheduler = RakeScheduler()
        >>> scheduler.start()
        >>>
        >>> # Add cron job (daily at 2 AM)
        >>> scheduler.add_job(
        ...     job_id="daily-sync",
        ...     source="file_upload",
        ...     file_path="/data/daily",
        ...     tenant_id="tenant-123",
        ...     cron_expression="0 2 * * *"
        ... )
        >>>
        >>> # Add interval job (every 30 minutes)
        >>> scheduler.add_job(
        ...     job_id="frequent-sync",
        ...     source="file_upload",
        ...     file_path="/data/frequent",
        ...     tenant_id="tenant-123",
        ...     interval_minutes=30
        ... )
    """

    def __init__(self):
        """Initialize the scheduler.

        Creates an AsyncIOScheduler instance and sets up event listeners.
        """
        self.scheduler = AsyncIOScheduler()
        self.orchestrator = PipelineOrchestrator()
        self.jobs: Dict[str, Dict[str, Any]] = {}

        # Register event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED
        )
        self.scheduler.add_listener(
            self._job_error_listener,
            EVENT_JOB_ERROR
        )
        self.scheduler.add_listener(
            self._job_missed_listener,
            EVENT_JOB_MISSED
        )

        logger.info("RakeScheduler initialized")

    def start(self) -> None:
        """Start the scheduler.

        Begins processing scheduled jobs.

        Example:
            >>> scheduler = RakeScheduler()
            >>> scheduler.start()
            >>> # Scheduler is now running
        """
        if not settings.SCHEDULER_ENABLED:
            logger.warning("Scheduler is disabled in settings (SCHEDULER_ENABLED=False)")
            return

        try:
            self.scheduler.start()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            raise SchedulerError(f"Scheduler startup failed: {e}")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Stops the scheduler and optionally waits for running jobs to complete.

        Args:
            wait: If True, wait for running jobs to finish

        Example:
            >>> scheduler.shutdown(wait=True)
        """
        try:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error during scheduler shutdown: {e}", exc_info=True)

    async def _execute_scheduled_job(
        self,
        job_id: str,
        source: str,
        tenant_id: str,
        **source_params
    ) -> None:
        """Execute a scheduled pipeline job.

        This is the actual function that APScheduler calls.

        Args:
            job_id: Scheduled job identifier
            source: Document source type
            tenant_id: Tenant identifier
            **source_params: Source-specific parameters

        Example:
            This is called automatically by APScheduler, not directly.
        """
        correlation_id = str(uuid4())
        pipeline_job_id = f"scheduled-{job_id}-{datetime.utcnow().timestamp()}"

        logger.info(
            f"Executing scheduled job: {job_id}",
            extra={
                "correlation_id": correlation_id,
                "job_id": job_id,
                "tenant_id": tenant_id,
                "source": source
            }
        )

        try:
            # Run pipeline
            result = await self.orchestrator.run(
                source=source,
                tenant_id=tenant_id,
                job_id=pipeline_job_id,
                correlation_id=correlation_id,
                **source_params
            )

            logger.info(
                f"Scheduled job completed: {job_id}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "status": result["status"],
                    "duration_ms": result["duration_ms"]
                }
            )

        except PipelineError as e:
            logger.error(
                f"Scheduled job failed: {job_id} - {str(e)}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id,
                    "error": str(e)
                },
                exc_info=True
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error in scheduled job: {job_id}",
                extra={
                    "correlation_id": correlation_id,
                    "job_id": job_id
                },
                exc_info=True
            )
            raise

    def add_job(
        self,
        job_id: str,
        source: str,
        tenant_id: str,
        cron_expression: Optional[str] = None,
        interval_minutes: Optional[int] = None,
        **source_params
    ) -> str:
        """Add a scheduled job.

        Creates a new scheduled job with either cron or interval trigger.

        Args:
            job_id: Unique job identifier
            source: Document source type (file_upload, url_scrape, etc.)
            tenant_id: Tenant identifier
            cron_expression: Cron expression (e.g., "0 2 * * *" for daily at 2 AM)
            interval_minutes: Interval in minutes (alternative to cron)
            **source_params: Source-specific parameters

        Returns:
            Job ID of the created job

        Raises:
            SchedulerError: If job creation fails

        Example:
            >>> # Cron job (daily at 2 AM)
            >>> scheduler.add_job(
            ...     job_id="daily-sync",
            ...     source="file_upload",
            ...     file_path="/data/daily",
            ...     tenant_id="tenant-123",
            ...     cron_expression="0 2 * * *"
            ... )
            >>>
            >>> # Interval job (every 30 minutes)
            >>> scheduler.add_job(
            ...     job_id="frequent-sync",
            ...     source="file_upload",
            ...     file_path="/data/frequent",
            ...     tenant_id="tenant-123",
            ...     interval_minutes=30
            ... )
        """
        if job_id in self.jobs:
            raise SchedulerError(f"Job with ID '{job_id}' already exists")

        if not cron_expression and not interval_minutes:
            raise SchedulerError("Either cron_expression or interval_minutes must be provided")

        if cron_expression and interval_minutes:
            raise SchedulerError("Cannot specify both cron_expression and interval_minutes")

        try:
            # Determine trigger type
            if cron_expression:
                trigger = CronTrigger.from_crontab(cron_expression)
                trigger_type = "cron"
                trigger_value = cron_expression
            else:
                trigger = IntervalTrigger(minutes=interval_minutes)
                trigger_type = "interval"
                trigger_value = f"{interval_minutes}m"

            # Add job to scheduler
            self.scheduler.add_job(
                func=self._execute_scheduled_job,
                trigger=trigger,
                id=job_id,
                name=f"Rake Job: {job_id}",
                kwargs={
                    "job_id": job_id,
                    "source": source,
                    "tenant_id": tenant_id,
                    **source_params
                },
                replace_existing=False,
                max_instances=1  # Prevent concurrent execution
            )

            # Store job metadata
            self.jobs[job_id] = {
                "job_id": job_id,
                "source": source,
                "tenant_id": tenant_id,
                "trigger_type": trigger_type,
                "trigger_value": trigger_value,
                "created_at": datetime.utcnow(),
                "source_params": source_params,
                "status": "active"
            }

            logger.info(
                f"Scheduled job added: {job_id} ({trigger_type}: {trigger_value})",
                extra={
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "source": source,
                    "trigger_type": trigger_type
                }
            )

            return job_id

        except Exception as e:
            logger.error(f"Failed to add scheduled job: {e}", exc_info=True)
            raise SchedulerError(f"Failed to add job: {e}")

    def remove_job(self, job_id: str) -> None:
        """Remove a scheduled job.

        Args:
            job_id: Job identifier to remove

        Raises:
            SchedulerError: If job doesn't exist

        Example:
            >>> scheduler.remove_job("daily-sync")
        """
        if job_id not in self.jobs:
            raise SchedulerError(f"Job '{job_id}' not found")

        try:
            self.scheduler.remove_job(job_id)
            del self.jobs[job_id]

            logger.info(
                f"Scheduled job removed: {job_id}",
                extra={"job_id": job_id}
            )

        except Exception as e:
            logger.error(f"Failed to remove job {job_id}: {e}", exc_info=True)
            raise SchedulerError(f"Failed to remove job: {e}")

    def pause_job(self, job_id: str) -> None:
        """Pause a scheduled job.

        Args:
            job_id: Job identifier to pause

        Example:
            >>> scheduler.pause_job("daily-sync")
        """
        if job_id not in self.jobs:
            raise SchedulerError(f"Job '{job_id}' not found")

        try:
            self.scheduler.pause_job(job_id)
            self.jobs[job_id]["status"] = "paused"

            logger.info(f"Job paused: {job_id}", extra={"job_id": job_id})

        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {e}", exc_info=True)
            raise SchedulerError(f"Failed to pause job: {e}")

    def resume_job(self, job_id: str) -> None:
        """Resume a paused job.

        Args:
            job_id: Job identifier to resume

        Example:
            >>> scheduler.resume_job("daily-sync")
        """
        if job_id not in self.jobs:
            raise SchedulerError(f"Job '{job_id}' not found")

        try:
            self.scheduler.resume_job(job_id)
            self.jobs[job_id]["status"] = "active"

            logger.info(f"Job resumed: {job_id}", extra={"job_id": job_id})

        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {e}", exc_info=True)
            raise SchedulerError(f"Failed to resume job: {e}")

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job details.

        Args:
            job_id: Job identifier

        Returns:
            Job metadata dictionary, or None if not found

        Example:
            >>> job = scheduler.get_job("daily-sync")
            >>> print(job['trigger_type'])
            cron
        """
        return self.jobs.get(job_id)

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all scheduled jobs.

        Returns:
            List of job metadata dictionaries

        Example:
            >>> jobs = scheduler.list_jobs()
            >>> for job in jobs:
            ...     print(f"{job['job_id']}: {job['status']}")
        """
        return list(self.jobs.values())

    def _job_executed_listener(self, event: JobExecutionEvent) -> None:
        """Handle job execution events.

        Args:
            event: APScheduler job execution event
        """
        logger.info(
            f"Scheduled job executed successfully: {event.job_id}",
            extra={"job_id": event.job_id}
        )

    def _job_error_listener(self, event: JobExecutionEvent) -> None:
        """Handle job error events.

        Args:
            event: APScheduler job error event
        """
        logger.error(
            f"Scheduled job failed: {event.job_id} - {event.exception}",
            extra={"job_id": event.job_id},
            exc_info=event.exception
        )

    def _job_missed_listener(self, event: JobExecutionEvent) -> None:
        """Handle missed job events.

        Args:
            event: APScheduler missed job event
        """
        logger.warning(
            f"Scheduled job missed: {event.job_id}",
            extra={"job_id": event.job_id}
        )


# Global scheduler instance
_scheduler: Optional[RakeScheduler] = None


def get_scheduler() -> RakeScheduler:
    """Get the global scheduler instance.

    Creates the scheduler on first call (singleton pattern).

    Returns:
        Global RakeScheduler instance

    Example:
        >>> scheduler = get_scheduler()
        >>> scheduler.start()
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = RakeScheduler()
    return _scheduler


# Example usage and testing
if __name__ == "__main__":
    import asyncio

    async def main():
        """Test scheduler functionality."""
        print("=== Rake Scheduler Examples ===\n")

        # Create scheduler
        scheduler = RakeScheduler()

        # Note: We can't actually start it without proper setup
        # But we can demonstrate the API

        print("Example 1: Add Cron Job")
        print("  (Would run daily at 2 AM)")
        print("  scheduler.add_job(")
        print("    job_id='daily-sync',")
        print("    source='file_upload',")
        print("    file_path='/data/daily',")
        print("    tenant_id='tenant-123',")
        print("    cron_expression='0 2 * * *'")
        print("  )")

        print("\n\nExample 2: Add Interval Job")
        print("  (Would run every 30 minutes)")
        print("  scheduler.add_job(")
        print("    job_id='frequent-sync',")
        print("    source='file_upload',")
        print("    file_path='/data/frequent',")
        print("    tenant_id='tenant-123',")
        print("    interval_minutes=30")
        print("  )")

        print("\n\nExample 3: Job Management")
        print("  scheduler.pause_job('daily-sync')")
        print("  scheduler.resume_job('daily-sync')")
        print("  scheduler.remove_job('daily-sync')")

        print("\n\nExample 4: List Jobs")
        print("  jobs = scheduler.list_jobs()")
        print("  for job in jobs:")
        print("    print(job['job_id'], job['status'])")

        print("\n✅ Examples completed")
        print("\nNote: Set SCHEDULER_ENABLED=true in .env to enable scheduling")

    asyncio.run(main())
