from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import get_settings

settings = get_settings()
# Алгоритм хэширования bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# Хэширую пароль
def hash_password(password: str) -> str:
    return pwd_context.hash(password)
# Сравнение обычного пароля с хэшем
def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)

# Создание JWT
def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)

# Декодирование JWT
def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

    subject = payload.get("sub")
    if not subject:
        raise ValueError("Token subject is missing")
    return str(subject)
