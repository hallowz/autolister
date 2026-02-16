"""
Background tasks for scraping and processing
"""
from celery import Celery
from app.config import get_settings

settings = get_settings()

# Create Celery app instance
celery_app = Celery(
    'autolister',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['app.tasks.jobs']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

from .jobs import (
    run_scraping_job,
    process_approved_manuals,
    create_etsy_listings
)

__all__ = [
    'celery_app',
    'run_scraping_job',
    'process_approved_manuals',
    'create_etsy_listings',
]
