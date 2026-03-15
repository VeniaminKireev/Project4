from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.models import User
from app.auth.utils import decode_access_token
from app.db import get_db_session

DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
bearer_optional = HTTPBearer(auto_error=False)
bearer_required = HTTPBearer(auto_error=True)

# Для “мягкой” авторизации (к примеру, POST /links/shorten доступен всем)
async def get_current_user_optional(
    session: DbSessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_optional)],
) -> User | None:
    if credentials is None:
        return None

    try:
        user_id = int(decode_access_token(credentials.credentials))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# Для защищённых операций (PUT, DELETE, ...)
async def get_current_user(
    session: DbSessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_required)],
) -> User:
    try:
        user_id = int(decode_access_token(credentials.credentials))
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
