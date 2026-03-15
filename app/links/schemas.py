from datetime import datetime, timezone
from pydantic import BaseModel, HttpUrl, field_validator

# Схема для POST /links/shorten
class LinkCreate(BaseModel):
    original_url: HttpUrl
    custom_alias: str | None = None
    expires_at: datetime | None = None

    @field_validator("custom_alias")
    @classmethod
    def normalize_alias(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None
    @field_validator("expires_at")
    @classmethod
    def round_to_minute(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.replace(second=0, microsecond=0)

# Схема для PUT /links/{short_code}
class LinkUpdate(BaseModel):
    original_url: HttpUrl
    expires_at: datetime | None = None
    @field_validator("expires_at")
    @classmethod
    def round_to_minute(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.replace(second=0, microsecond=0)

# Ответ на создание/обновление ссылки
class LinkResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    owner_user_id: int | None

# Один элемент как результат поиска
class LinkSearchItem(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None
    owner_user_id: int | None
    model_config = {"from_attributes": True}

# Ответ для статистики
class LinkStatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_used_at: datetime | None
    expires_at: datetime | None
    model_config = {"from_attributes": True}

# Схема для истории expired links
class ExpiredLinkItem(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    expired_at: datetime
    click_count: int
    last_used_at: datetime | None
    reason: str
    model_config = {"from_attributes": True}
