from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from app.auth.models import User
from app.auth.schemas import Token, UserCreate, UserLogin, UserRead
from app.auth.utils import create_access_token, hash_password, verify_password
from app.db import get_db_session

router = APIRouter(prefix="/auth", tags=["auth"])

# POST /auth/register
@router.post("/register", summary="Регистрация", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, session=Depends(get_db_session)):
    result = await session.execute(select(User).where(User.email == payload.email))
    if result.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user

# POST /auth/login
@router.post("/login", summary="Авторизация", response_model=Token)
async def login(payload: UserLogin, session=Depends(get_db_session)):
    result = await session.execute(select(User).where(User.email == payload.email))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return Token(access_token=create_access_token(str(user.id)))
