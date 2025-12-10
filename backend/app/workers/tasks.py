"""
Base Celery tasks with progress tracking and state management.

Provides custom task class for tracking progress, storing state in Redis,
and preparing hooks for WebSocket progress updates.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from celery import Task, current_task
from celery.exceptions import SoftTimeLimitExceeded

from app.workers.celery_app import celery_app
from app.core.redis import get_redis_client_sync

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Helper class for tracking task progress in Redis.
    """
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.redis_key = f"task:progress:{task_id}"
        self.redis_client = None
    
    def _get_redis(self):
        """Lazy load Redis client."""
        if self.redis_client is None:
            self.redis_client = get_redis_client_sync()
        return self.redis_client
    
    def set_progress(
        self,
        current: int,
        total: int,
        status: str = "processing",
        message: Optional[str] = None,
        metadata: Optional[Dict] = None
    ):
        """
        Update task progress in Redis.
        
        Args:
            current: Current progress value
            total: Total progress value
            status: Task status ('processing', 'completed', 'failed', etc.)
            message: Optional progress message
            metadata: Optional additional metadata
        """
        try:
            percentage = (current / total * 100) if total > 0 else 0
            
            progress_data = {
                "task_id": self.task_id,
                "current": current,
                "total": total,
                "percentage": round(percentage, 2),
                "status": status,
                "message": message,
                "metadata": metadata or {},
                "updated_at": datetime.utcnow().isoformat()
            }
            
            redis = self._get_redis()
            # Store progress data with 1 hour expiration
            redis.setex(
                self.redis_key,
                3600,  # 1 hour
                json.dumps(progress_data)
            )
            
            # Publish to WebSocket channel for real-time updates
            channel = f"task:updates:{self.task_id}"
            redis.publish(channel, json.dumps(progress_data))
            
            logger.debug(f"Progress updated for task {self.task_id}: {percentage:.1f}%")
        
        except Exception as e:
            logger.error(f"Failed to set progress for task {self.task_id}: {e}")
    
    def get_progress(self) -> Optional[Dict]:
        """
        Get current task progress from Redis.
        
        Returns:
            Dictionary with progress data or None if not found
        """
        try:
            redis = self._get_redis()
            data = redis.get(self.redis_key)
            
            if data:
                return json.loads(data)
            return None
        
        except Exception as e:
            logger.error(f"Failed to get progress for task {self.task_id}: {e}")
            return None
    
    def clear_progress(self):
        """Remove progress data from Redis."""
        try:
            redis = self._get_redis()
            redis.delete(self.redis_key)
        except Exception as e:
            logger.error(f"Failed to clear progress for task {self.task_id}: {e}")


class BaseTask(Task):
    """
    Custom Celery task class with enhanced features.
    
    Features:
    - Automatic progress tracking
    - State storage in Redis
    - WebSocket update hooks
    - Error handling and logging
    - Retry configuration
    """
    
    # Retry configuration
    autoretry_for = (Exception,)  # Retry on any exception
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True  # Exponential backoff
    retry_backoff_max = 600  # Max 10 minutes between retries
    retry_jitter = True  # Add randomness to backoff
    
    def __call__(self, *args, **kwargs):
        """
        Override task execution to add progress tracking.
        """
        # Initialize progress tracker
        self.progress_tracker = ProgressTracker(self.request.id)
        
        # Set initial progress
        self.update_progress(0, 100, "started", "Task started")
        
        try:
            # Execute the actual task
            result = super().__call__(*args, **kwargs)
            
            # Mark as completed
            self.update_progress(100, 100, "completed", "Task completed successfully")
            
            return result
        
        except SoftTimeLimitExceeded:
            # Handle soft time limit
            logger.warning(f"Task {self.name}[{self.request.id}] exceeded soft time limit")
            self.update_progress(
                self.progress_tracker.get_progress().get("current", 0),
                100,
                "timeout",
                "Task exceeded time limit"
            )
            raise
        
        except Exception as e:
            # Handle errors
            logger.error(f"Task {self.name}[{self.request.id}] failed: {e}", exc_info=True)
            self.update_progress(
                self.progress_tracker.get_progress().get("current", 0),
                100,
                "failed",
                f"Task failed: {str(e)}"
            )
            raise
    
    def update_progress(
        self,
        current: int,
        total: int,
        status: str = "processing",
        message: Optional[str] = None,
        **metadata
    ):
        """
        Update task progress.
        
        Args:
            current: Current progress value
            total: Total progress value
            status: Task status
            message: Progress message
            **metadata: Additional metadata to store
        """
        if hasattr(self, "progress_tracker"):
            self.progress_tracker.set_progress(
                current=current,
                total=total,
                status=status,
                message=message,
                metadata=metadata
            )
        
        # Also update Celery's built-in state
        self.update_state(
            state=status.upper(),
            meta={
                "current": current,
                "total": total,
                "percentage": (current / total * 100) if total > 0 else 0,
                "message": message,
                **metadata
            }
        )
    
    def on_success(self, retval, task_id, args, kwargs):
        """
        Handler called when task succeeds.
        """
        logger.info(f"Task {self.name}[{task_id}] succeeded")
        
        # Store success state in Redis
        self._store_task_result(task_id, "SUCCESS", retval)
        
        return super().on_success(retval, task_id, args, kwargs)
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """
        Handler called when task fails.
        """
        logger.error(f"Task {self.name}[{task_id}] failed: {exc}")
        
        # Store failure state in Redis
        self._store_task_result(
            task_id,
            "FAILURE",
            {
                "error": str(exc),
                "traceback": str(einfo)
            }
        )
        
        return super().on_failure(exc, task_id, args, kwargs, einfo)
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """
        Handler called when task is retried.
        """
        logger.warning(f"Task {self.name}[{task_id}] is being retried: {exc}")
        
        # Update progress with retry information
        if hasattr(self, "progress_tracker"):
            self.progress_tracker.set_progress(
                current=0,
                total=100,
                status="retrying",
                message=f"Retrying task due to: {str(exc)}",
                metadata={
                    "retry_count": self.request.retries,
                    "max_retries": self.max_retries
                }
            )
        
        return super().on_retry(exc, task_id, args, kwargs, einfo)
    
    def _store_task_result(self, task_id: str, state: str, result: Any):
        """
        Store task result in Redis with metadata.
        
        Args:
            task_id: Task ID
            state: Task state (SUCCESS, FAILURE, etc.)
            result: Task result or error information
        """
        try:
            redis = get_redis_client_sync()
            result_key = f"task:result:{task_id}"
            
            result_data = {
                "task_id": task_id,
                "task_name": self.name,
                "state": state,
                "result": result,
                "completed_at": datetime.utcnow().isoformat()
            }
            
            # Store with 24 hour expiration
            redis.setex(
                result_key,
                86400,  # 24 hours
                json.dumps(result_data)
            )
        
        except Exception as e:
            logger.error(f"Failed to store task result: {e}")


# Example utility tasks
@celery_app.task(base=BaseTask, name="app.workers.tasks.cleanup_old_results")
def cleanup_old_results():
    """
    Periodic task to clean up old task results from Redis.
    """
    try:
        redis = get_redis_client_sync()
        
        # Scan for old task keys
        cursor = 0
        deleted_count = 0
        cutoff_time = datetime.utcnow() - timedelta(days=7)
        
        while True:
            cursor, keys = redis.scan(cursor, match="task:result:*", count=100)
            
            for key in keys:
                try:
                    data = redis.get(key)
                    if data:
                        result = json.loads(data)
                        completed_at = datetime.fromisoformat(result.get("completed_at", ""))
                        
                        if completed_at < cutoff_time:
                            redis.delete(key)
                            deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to process key {key}: {e}")
            
            if cursor == 0:
                break
        
        logger.info(f"Cleaned up {deleted_count} old task results")
        return {"deleted_count": deleted_count}
    
    except Exception as e:
        logger.error(f"Failed to cleanup old results: {e}")
        raise


@celery_app.task(base=BaseTask, name="app.workers.tasks.health_check")
def health_check():
    """
    Periodic health check task.
    """
    try:
        # Check Redis connection
        redis = get_redis_client_sync()
        redis.ping()
        
        # Check Celery
        celery_app.control.inspect().stats()
        
        logger.debug("Health check passed")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


def get_task_progress(task_id: str) -> Optional[Dict]:
    """
    Get progress information for a task.
    
    Args:
        task_id: Celery task ID
    
    Returns:
        Progress data dictionary or None if not found
    """
    tracker = ProgressTracker(task_id)
    return tracker.get_progress()


def cancel_task(task_id: str, terminate: bool = False):
    """
    Cancel a running task.
    
    Args:
        task_id: Celery task ID
        terminate: If True, forcefully terminate the task
    """
    try:
        celery_app.control.revoke(task_id, terminate=terminate)
        
        # Update progress to cancelled
        tracker = ProgressTracker(task_id)
        tracker.set_progress(
            current=0,
            total=100,
            status="cancelled",
            message="Task was cancelled"
        )
        
        logger.info(f"Task {task_id} cancelled (terminate={terminate})")
    
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise


# Export main components
__all__ = [
    "BaseTask",
    "ProgressTracker",
    "get_task_progress",
    "cancel_task",
    "cleanup_old_results",
    "health_check"
]
