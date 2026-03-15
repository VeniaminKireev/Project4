from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.auth import models as auth_models
from app.auth.router import router as auth_router
from app.config import get_settings
from app.db import Base, engine
from app.links import models as link_models
from app.links.router import router as links_router
from app.links.utils import close_redis, init_redis

# Получаю настройки
settings = get_settings()

# Подключение к Redis перед стартом приложения или закрытие соединения после остановки
@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await init_redis()
    yield
    await close_redis()

app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
#Подключаю роутеры
app.include_router(auth_router)
app.include_router(links_router)

# root endpoint на всякий случай (health-check)
@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "URL Shortener API is running"}
