from __future__ import annotations
import hashlib
import json
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Any
from redis.asyncio import Redis
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import get_settings
from app.links.models import ExpiredLink, Link

settings = get_settings()
redis_client: Redis | None = None
ALPHABET = string.ascii_letters + string.digits
ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED_ALIASES = {"search", "shorten", "expired", "auth", "docs", "openapi.json", "redoc"}

# Создание случайныого кода нужной длины
def generate_short_code(length: int) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
# Проверяю alias
def validate_custom_alias(alias: str) -> bool:
    return bool(ALIAS_PATTERN.fullmatch(alias)) and alias not in RESERVED_ALIASES

# Генерация short code
async def find_unique_short_code(session: AsyncSession) -> str:
    while True:
        candidate = generate_short_code(settings.short_code_length)
        if candidate in RESERVED_ALIASES:
            continue
        result = await session.execute(select(Link).where(Link.short_code == candidate))
        if result.scalar_one_or_none() is None:
            return candidate

# Инициализация Redis
async def init_redis() -> None:
    global redis_client
    redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    await redis_client.ping()

# Закрытие Redis
async def close_redis() -> None:
    global redis_client
    if redis_client is not None:
        if hasattr(redis_client, "aclose"):
            await redis_client.aclose()
        else:
            await redis_client.close()
        redis_client = None

# Создать "сходу"
def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.redis_url, decode_responses=True)
    return redis_client

# Ключи
def link_cache_key(short_code: str) -> str:
    return f"link:{short_code}"
def stats_cache_key(short_code: str) -> str:
    return f"stats:{short_code}"
def search_cache_key(original_url: str) -> str:
    digest = hashlib.sha256(original_url.encode("utf-8")).hexdigest()
    return f"search:{digest}"

# JSON для Redis
async def set_json(key: str, payload: dict[str, Any], ttl: int) -> None:
    await get_redis().set(key, json.dumps(payload, default=_json_default), ex=ttl)
async def get_json(key: str) -> dict[str, Any] | None:
    data = await get_redis().get(key)
    if not data:
        return None
    return json.loads(data)
async def delete_keys(*keys: str) -> None:
    keys = [key for key in keys if key]
    if keys:
        await get_redis().delete(*keys)

# Кэш-функции
async def cache_link(short_code: str, original_url: str, expires_at: datetime | None) -> None:
    await set_json(
        link_cache_key(short_code),
        {
            "original_url": original_url,
            "expires_at": expires_at.isoformat() if expires_at else None,
        },
        settings.redirect_cache_ttl_seconds,
    )

async def get_cached_link(short_code: str) -> dict[str, Any] | None:
    return await get_json(link_cache_key(short_code))

async def cache_stats(short_code: str, payload: dict[str, Any]) -> None:
    await set_json(stats_cache_key(short_code), payload, settings.stats_cache_ttl_seconds)

async def get_cached_stats(short_code: str) -> dict[str, Any] | None:
    return await get_json(stats_cache_key(short_code))

async def invalidate_link_cache(short_code: str) -> None:
    await delete_keys(link_cache_key(short_code), stats_cache_key(short_code))

async def invalidate_search_cache(original_url: str) -> None:
    await delete_keys(search_cache_key(original_url))

# Архивация ссылок
async def archive_link(session: AsyncSession, link: Link, reason: str) -> None:
    session.add(
        ExpiredLink(
            short_code=link.short_code,
            original_url=link.original_url,
            created_at=link.created_at,
            expired_at=datetime.now(timezone.utc),
            click_count=link.click_count,
            last_used_at=link.last_used_at,
            owner_user_id=link.owner_user_id,
            reason=reason,
        )
    )

async def archive_and_delete_link(session: AsyncSession, link: Link, reason: str) -> None:
    await archive_link(session, link, reason)
    await invalidate_link_cache(link.short_code)
    await session.delete(link)

# Удаление одной "протухшей" ссылки
async def delete_expired_link_by_code(session: AsyncSession, short_code: str) -> bool:
    result = await session.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        return False
    if link.expires_at is None or link.expires_at > datetime.now(timezone.utc):
        return False
    await archive_and_delete_link(session, link, reason="expired")
    await session.commit()
    return True

# Очистка неактивных ссылок
async def cleanup_expired_links(session: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    result = await session.execute(select(Link).where(Link.expires_at.is_not(None), Link.expires_at <= now))
    links = list(result.scalars().all())
    for link in links:
        await archive_and_delete_link(session, link, reason="expired")
    await session.commit()
    return len(links)

async def cleanup_inactive_links(session: AsyncSession) -> int:
    threshold = datetime.now(timezone.utc) - timedelta(days=settings.inactive_link_days)
    result = await session.execute(
        select(Link).where(
            or_(
                and_(Link.last_used_at.is_not(None), Link.last_used_at <= threshold),
                and_(Link.last_used_at.is_(None), Link.created_at <= threshold),
            )
        )
    )
    links = list(result.scalars().all())
    for link in links:
        await archive_and_delete_link(session, link, reason="inactive_cleanup")
    await session.commit()
    return len(links)

# JSON serializer helper (без этого у меня падал json.dumps())
def _json_default(value: Any) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    raise TypeError(f"Unsupported type for JSON serialization: {type(value)!r}")
