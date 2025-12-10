"""
Celery application configuration.

Configures Celery with Redis broker, task serialization, result backend,
task routes, retry policies, and concurrency settings.
"""

import logging
from celery import Celery
from celery.signals import task_prerun, task_postrun, task_failure
from kombu import Exchange, Queue

from app.core.config import settings

logger = logging.getLogger(__name__)


# Initialize Celery app
celery_app = Celery(
    "datapilot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.ingestion_worker",
        "app.workers.transformation_worker",
    ]
)


# Celery Configuration
celery_app.conf.update(
    # Task Serialization
    task_serializer="json",
    accept_content=["json"],  # Only accept JSON for security
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Result Backend Settings
    result_backend=settings.CELERY_RESULT_BACKEND,
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Store results persistently
    result_extended=True,  # Include args and kwargs in result
    
    # Task Execution Settings
    task_track_started=True,  # Track when tasks start
    task_time_limit=3600,  # Hard time limit: 1 hour
    task_soft_time_limit=3300,  # Soft time limit: 55 minutes (warning)
    task_acks_late=True,  # Acknowledge tasks after completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    
    # Retry Configuration
    task_default_retry_delay=60,  # Retry after 60 seconds
    task_max_retries=3,  # Maximum 3 retries
    task_default_rate_limit="100/m",  # 100 tasks per minute per worker
    
    # Worker Configuration
    worker_prefetch_multiplier=4,  # Number of tasks to prefetch
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks
    worker_disable_rate_limits=False,
    worker_log_format="[%(asctime)s: %(levelname)s/%(processName)s] %(message)s",
    worker_task_log_format="[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s",
    
    # Connection Settings
    broker_connection_retry=True,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=10,
    broker_pool_limit=10,
    
    # Result Backend Connection
    redis_max_connections=50,
    redis_socket_timeout=5,
    redis_socket_connect_timeout=5,
    
    # Task Always Eager (for testing)
    task_always_eager=settings.CELERY_TASK_ALWAYS_EAGER,
    task_eager_propagates=True,  # Propagate exceptions in eager mode
)


# Define task queues and exchanges
celery_app.conf.task_queues = (
    # Default queue
    Queue(
        "default",
        Exchange("default"),
        routing_key="default",
        priority=5
    ),
    
    # High priority queue for time-sensitive tasks
    Queue(
        "high_priority",
        Exchange("high_priority"),
        routing_key="high_priority",
        priority=10
    ),
    
    # Data ingestion queue
    Queue(
        "ingestion",
        Exchange("ingestion"),
        routing_key="ingestion",
        priority=7
    ),
    
    # Data transformation queue
    Queue(
        "transformation",
        Exchange("transformation"),
        routing_key="transformation",
        priority=6
    ),
    
    # Low priority queue for background tasks
    Queue(
        "low_priority",
        Exchange("low_priority"),
        routing_key="low_priority",
        priority=3
    ),
)


# Task routing configuration
celery_app.conf.task_routes = {
    # Ingestion tasks
    "app.workers.ingestion_worker.ingest_file_task": {
        "queue": "ingestion",
        "routing_key": "ingestion"
    },
    "app.workers.ingestion_worker.validate_file_task": {
        "queue": "ingestion",
        "routing_key": "ingestion"
    },
    
    # Transformation tasks
    "app.workers.transformation_worker.transform_data_task": {
        "queue": "transformation",
        "routing_key": "transformation"
    },
    "app.workers.transformation_worker.clean_data_task": {
        "queue": "transformation",
        "routing_key": "transformation"
    },
    
    # High priority tasks (e.g., user-initiated operations)
    "app.workers.tasks.high_priority_*": {
        "queue": "high_priority",
        "routing_key": "high_priority"
    },
    
    # Default queue for everything else
    "*": {
        "queue": "default",
        "routing_key": "default"
    }
}


# Beat schedule for periodic tasks (cron-like scheduling)
celery_app.conf.beat_schedule = {
    # Cleanup old task results every day at 2 AM
    "cleanup-old-results": {
        "task": "app.workers.tasks.cleanup_old_results",
        "schedule": 3600 * 24,  # Every 24 hours
        "options": {"queue": "low_priority"}
    },
    
    # Health check every 5 minutes
    "health-check": {
        "task": "app.workers.tasks.health_check",
        "schedule": 300,  # Every 5 minutes
        "options": {"queue": "low_priority"}
    },
}


# Celery signals for logging and monitoring
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **extra_kwargs):
    """Handler called before task execution."""
    logger.info(
        f"Task starting: {task.name}[{task_id}]",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "task_args": args,  # Renamed from 'args' to avoid conflict with LogRecord
            "task_kwargs": kwargs
        }
    )


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **extra_kwargs):
    """Handler called after task execution."""
    logger.info(
        f"Task completed: {task.name}[{task_id}] - State: {state}",
        extra={
            "task_id": task_id,
            "task_name": task.name,
            "state": state
        }
    )


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **extra_kwargs):
    """Handler called when task fails."""
    logger.error(
        f"Task failed: {sender.name}[{task_id}] - Exception: {exception}",
        extra={
            "task_id": task_id,
            "task_name": sender.name,
            "exception": str(exception),
            "traceback": str(traceback)
        },
        exc_info=einfo
    )


# Export celery app
__all__ = ["celery_app"]
