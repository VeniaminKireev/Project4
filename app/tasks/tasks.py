import asyncio
from app.db import AsyncSessionLocal
from app.links.utils import cleanup_expired_links, cleanup_inactive_links
from app.tasks.celery_app import celery_app

# Синхронная задача Celery вызывает асинхронную cleanup-функцию через asyncio.run()
@celery_app.task(name="app.tasks.tasks.cleanup_expired_links_task")
def cleanup_expired_links_task() -> int:
    return asyncio.run(_cleanup_expired())

# Для неактивных ссылок
@celery_app.task(name="app.tasks.tasks.cleanup_inactive_links_task")
def cleanup_inactive_links_task() -> int:
    return asyncio.run(_cleanup_inactive())

# Открыть async SQLAlchemy session и вызвать util-функцию
async def _cleanup_expired() -> int:
    async with AsyncSessionLocal() as session:
        return await cleanup_expired_links(session)

# Для cleanup inactive
async def _cleanup_inactive() -> int:
    async with AsyncSessionLocal() as session:
        return await cleanup_inactive_links(session)
