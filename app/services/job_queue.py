import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)


class JobQueue:
    """Async job queue with concurrency control using asyncio.Semaphore."""

    def __init__(self):
        settings = get_settings()
        self.max_concurrent = settings.MAX_CONCURRENT_JOBS
        self.semaphore = asyncio.Semaphore(self.max_concurrent)
        self._jobs: dict[str, dict[str, Any]] = {}

    async def submit(self, job_id: str, coroutine_func: Callable, *args, **kwargs) -> None:
        """Submit a job to the queue with concurrency control."""
        self._jobs[job_id] = {
            "status": "pending",
            "submitted_at": datetime.now(UTC).isoformat(),
            "result": None,
            "error": None,
        }

        async def _run_job():
            async with self.semaphore:
                self._jobs[job_id]["status"] = "running"
                self._jobs[job_id]["started_at"] = datetime.now(UTC).isoformat()
                try:
                    result = await coroutine_func(*args, **kwargs)
                    self._jobs[job_id]["status"] = "completed"
                    self._jobs[job_id]["result"] = result
                except Exception as e:
                    self._jobs[job_id]["status"] = "failed"
                    self._jobs[job_id]["error"] = str(e)
                    logger.error(f"Job {job_id} failed: {e}")
                finally:
                    self._jobs[job_id]["completed_at"] = datetime.now(UTC).isoformat()

        asyncio.create_task(_run_job())

    def get_status(self, job_id: str) -> dict[str, Any] | None:
        """Get the status of a job."""
        return self._jobs.get(job_id)

    def list_jobs(self) -> dict[str, dict[str, Any]]:
        """List all jobs."""
        return self._jobs


# Global job queue instance
job_queue = JobQueue()
