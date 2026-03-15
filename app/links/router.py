from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.db import get_db_session
from app.dependencies import get_current_user, get_current_user_optional
from app.links.models import ExpiredLink, Link
from app.links.schemas import (
    ExpiredLinkItem,
    LinkCreate,
    LinkResponse,
    LinkSearchItem,
    LinkStatsResponse,
    LinkUpdate,
)
from app.links.utils import (
    archive_and_delete_link,
    cache_link,
    cache_stats,
    delete_expired_link_by_code,
    find_unique_short_code,
    get_cached_link,
    get_cached_stats,
    get_json,
    invalidate_link_cache,
    invalidate_search_cache,
    search_cache_key,
    set_json,
    settings,
    validate_custom_alias,
)
# Все эндпоинты будут начинаться с /links
router = APIRouter(prefix="/links", tags=["links"])


def build_short_url(request: Request, short_code: str) -> str:
    return f"{str(request.base_url).rstrip('/')}/links/{short_code}"

def ensure_not_expired(expires_at: datetime | None) -> None:
    if expires_at is not None and expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="expires_at must be in the future",
        )

# POST /links/shorten
@router.post("/shorten", summary="Создать ссылку", response_model=LinkResponse, status_code=status.HTTP_201_CREATED)
async def create_short_link(
    payload: LinkCreate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User | None = Depends(get_current_user_optional),
):
    ensure_not_expired(payload.expires_at)

    if payload.custom_alias:
        if not validate_custom_alias(payload.custom_alias):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="custom_alias must match ^[A-Za-z0-9_-]{3,32}$ and must not be reserved",
            )
        short_code = payload.custom_alias
        result = await session.execute(select(Link).where(Link.short_code == short_code))
        if result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Alias is already in use")
    else:
        short_code = await find_unique_short_code(session)

    link = Link(
        short_code=short_code,
        original_url=str(payload.original_url),
        expires_at=payload.expires_at,
        owner_user_id=current_user.id if current_user else None,
    )
    session.add(link)
    await session.commit()
    await session.refresh(link)

    await cache_link(link.short_code, link.original_url, link.expires_at)

    return LinkResponse(
        short_code=link.short_code,
        short_url=build_short_url(request, link.short_code),
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
        owner_user_id=link.owner_user_id,
    )

# GET /links/search
@router.get("/search", summary="Поиск по ссылке", response_model=list[LinkSearchItem])
async def search_by_original_url(
    original_url: str = Query(..., description="Original URL for exact-match search"),
    session: AsyncSession = Depends(get_db_session),
):
    cache_key = search_cache_key(original_url)
    cached = await get_json(cache_key)
    if cached is not None:
        return cached["items"]

    result = await session.execute(
        select(Link).where(Link.original_url == original_url).order_by(Link.created_at.desc())
    )
    links = result.scalars().all()
    items = [LinkSearchItem.model_validate(link).model_dump(mode="json") for link in links]
    await set_json(cache_key, {"items": items}, settings.search_cache_ttl_seconds)
    return items

# GET /links/expired/history
@router.get("/expired/history", summary="Получить историю ссылок", response_model=list[ExpiredLinkItem])
async def expired_links_history(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(ExpiredLink)
        .where(ExpiredLink.owner_user_id == current_user.id)
        .order_by(ExpiredLink.expired_at.desc())
    )
    return list(result.scalars().all())

# GET /links/{short_code}
@router.get("/{short_code}", summary="Получить ссылку по коду")
async def redirect_to_original(
    short_code: str,
    session: AsyncSession = Depends(get_db_session),
):
    cached = await get_cached_link(short_code)
    now = datetime.now(timezone.utc)

    if cached is not None:
        expires_at_raw = cached.get("expires_at")
        expires_at = datetime.fromisoformat(expires_at_raw) if expires_at_raw else None
        if expires_at is not None and expires_at <= now:
            await delete_expired_link_by_code(session, short_code)
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short link has expired")

        await session.execute(
            update(Link)
            .where(Link.short_code == short_code)
            .values(click_count=Link.click_count + 1, last_used_at=now, updated_at=now)
        )
        await session.commit()
        await invalidate_link_cache(short_code)
        await cache_link(short_code, cached["original_url"], expires_at)
        return RedirectResponse(url=cached["original_url"], status_code=status.HTTP_307_TEMPORARY_REDIRECT)

    result = await session.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")

    if link.expires_at is not None and link.expires_at <= now:
        await archive_and_delete_link(session, link, reason="expired")
        await session.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short link has expired")

    link.click_count += 1
    link.last_used_at = now
    await session.commit()
    await invalidate_link_cache(short_code)
    await cache_link(link.short_code, link.original_url, link.expires_at)
    return RedirectResponse(url=link.original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)

# GET /links/{short_code}/stats
@router.get("/{short_code}/stats", summary="Статистика", response_model=LinkStatsResponse)
async def get_link_stats(
    short_code: str,
    session: AsyncSession = Depends(get_db_session),
):
    cached = await get_cached_stats(short_code)
    if cached is not None:
        return cached

    result = await session.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")

    now = datetime.now(timezone.utc)
    if link.expires_at is not None and link.expires_at <= now:
        await archive_and_delete_link(session, link, reason="expired")
        await session.commit()
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short link has expired")

    payload = LinkStatsResponse.model_validate(link).model_dump(mode="json")
    await cache_stats(short_code, payload)
    return payload

# PUT /links/{short_code}
@router.put("/{short_code}", summary="Обновить ссылку", response_model=LinkResponse)
async def update_link(
    short_code: str,
    payload: LinkUpdate,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    ensure_not_expired(payload.expires_at)

    result = await session.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")
    if link.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only edit your own links")

    old_original_url = link.original_url
    link.original_url = str(payload.original_url)
    link.expires_at = payload.expires_at
    await session.commit()
    await session.refresh(link)

    await invalidate_link_cache(short_code)
    await invalidate_search_cache(old_original_url)
    await invalidate_search_cache(link.original_url)
    await cache_link(link.short_code, link.original_url, link.expires_at)

    return LinkResponse(
        short_code=link.short_code,
        short_url=build_short_url(request, link.short_code),
        original_url=link.original_url,
        created_at=link.created_at,
        expires_at=link.expires_at,
        owner_user_id=link.owner_user_id,
    )

# DELETE /links/{short_code}
@router.delete("/{short_code}", summary="Удалить ссылку", status_code=status.HTTP_204_NO_CONTENT)
async def delete_link(
    short_code: str,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(select(Link).where(Link.short_code == short_code))
    link = result.scalar_one_or_none()
    if link is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short link not found")
    if link.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only delete your own links")

    await archive_and_delete_link(session, link, reason="deleted")
    await session.commit()
    await invalidate_search_cache(link.original_url)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
