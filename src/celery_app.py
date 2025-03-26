from celery import Celery
import os
from src.tasks.links import delete_unused_links

celery_app = Celery(
    'tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:5370'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:5370')
)

celery_app.conf.broker_connection_retry_on_startup = True
celery_app.conf.broker_connection_retry = True

celery_app.conf.beat_schedule = {
    'delete-unused-links': {
        'task': 'src.tasks.links.delete_unused_links_task',
        'schedule': 86400,  # Запускать ежедневно (в секундах)
    },
}

@celery_app.task
def delete_unused_links_task():
    import asyncio
    return asyncio.get_event_loop().run_until_complete(delete_unused_links())