"""
Celery application instance.

Import this anywhere you need to dispatch tasks:
    from app.workers.celery_app import celery_app

The worker is started via:
    celery -A app.workers.celery_app worker --loglevel=info
"""

from app.core.config import settings
from celery import Celery

celery_app = Celery(
    "codesense",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.index_repo"],  # register task modules
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Task behaviour
    task_track_started=True,  # tasks show STARTED state in backend
    task_acks_late=True,  # ack after task completes, not before
    worker_prefetch_multiplier=1,  # one task at a time per worker (fair dispatch)
    task_reject_on_worker_lost=True,  # requeue if worker dies mid-task
    # Results
    result_expires=3600,  # results expire after 1 hour
    # Retry defaults
    task_default_retry_delay=30,  # 30s between retries
    task_max_retries=3,
)
