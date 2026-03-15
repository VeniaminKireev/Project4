from celery import Celery
from app.config import get_settings
settings = get_settings()

# Создаю Celery app
celery_app = Celery(
    "url_shortener",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.tasks"],
)
# Настройка времени
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "cleanup-expired-links-every-minute": {
            "task": "app.tasks.tasks.cleanup_expired_links_task",
            "schedule": 60.0,
        },
        "cleanup-inactive-links-every-day": {
            "task": "app.tasks.tasks.cleanup_inactive_links_task",
            "schedule": 60.0 * 60.0 * 24.0,
        },
    },
)
