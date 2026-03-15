# URL Shortener API (lecture-style structure)

Версия проекта с той же функциональностью, но в более "лекционной" структуре:

```text
app/
  main.py
  config.py
  db.py
  dependencies.py
  auth/
    models.py
    schemas.py
    router.py
    utils.py
  links/
    models.py
    schemas.py
    router.py
    utils.py
  tasks/
    celery_app.py
    tasks.py
```

## Что реализовано

### Обязательные функции
- `POST /links/shorten`
- `GET /links/{short_code}`
- `PUT /links/{short_code}`
- `DELETE /links/{short_code}`
- `GET /links/{short_code}/stats`
- кастомный alias через `custom_alias`
- поиск по `original_url` через `GET /links/search`
- время жизни ссылки через `expires_at`

### Дополнительные функции
- история истекших/удалённых ссылок: `GET /links/expired/history`
- автоматическое удаление неиспользуемых ссылок спустя `INACTIVE_LINK_DAYS`

### Авторизация
- `POST /auth/register`
- `POST /auth/login`

`POST /links/shorten` и redirect доступны всем. Обновление, удаление и просмотр истории доступны только владельцу ссылки.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Сервис:
- `http://localhost:8000`
- `http://localhost:8000/docs`

## Примеры запросов

### Регистрация
```bash
curl -X POST http://localhost:8000/auth/register   -H "Content-Type: application/json"   -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'
```

### Логин
```bash
curl -X POST http://localhost:8000/auth/login   -H "Content-Type: application/json"   -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'
```

### Создание ссылки
```bash
curl -X POST http://localhost:8000/links/shorten   -H "Content-Type: application/json"   -H "Authorization: Bearer <TOKEN>"   -d '{
    "original_url": "https://example.com/very/long/path",
    "custom_alias": "my-demo-link",
    "expires_at": "2026-03-20T14:30:00Z"
  }'
```

### Статистика
```bash
curl http://localhost:8000/links/my-demo-link/stats
```

## Кэширование

Redis используется для:
- redirect по `short_code`
- статистики по ссылке
- результата поиска по `original_url`

Кэш очищается при обновлении, удалении и истечении ссылки.

## Важное отличие от прошлой версии

Здесь убран отдельный `services/`-слой. Логика сгруппирована ближе к доменам `auth` и `links`, чтобы проект был визуально ближе к учебному примеру FastAPI с модулями `auth / booking / tasks`.
