from datetime import datetime
from pydantic import BaseModel, EmailStr

# Схема для регистрации
class UserCreate(BaseModel):
    email: EmailStr
    password: str
# Схема для логина
class UserLogin(BaseModel):
    email: EmailStr
    password: str
# Схема ответа с данными пользователя
class UserRead(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime
    model_config = {"from_attributes": True}
# Схема ответа с данными пользователя
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
