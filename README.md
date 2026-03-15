# URL Shortener API

URL Shortener API — сервис для сокращения ссылок, написаный на FastAPI. Пользователь может создать короткую ссылку для длинного URL, использовать кастомный элиас, задать срок жизни ссылки, получать статистику переходов, искать ссылку по исходному URL и управлять своими ссылками после регистрации

Поддерживаемые возможности:
- регистрация и логин пользователя по JWT;
- создание короткой ссылки для авторизованных и неавторизованных пользователей;
- редирект по короткому коду на исходный URL;
- обновление и удаление ссылки владельцем;
- статистика по ссылке;
- поиск по `original_url`;
- кастомный элиас;
- автоматическое истечение ссылок по `expires_at`;
- история истекших и удалённых ссылок;
- очистка истекших и неиспользуемых ссылок через Celery;
- кеширование через Redis

## Описание API

### Аутентификация

`POST /auth/register` — регистрация пользователя

`POST /auth/login` — логин пользователя, возвращает JWT access token

### Ссылки

`POST /links/shorten` — создать короткую ссылку

`GET /links/{short_code}` — выполнить редирект на исходный URL

`PUT /links/{short_code}` — обновить исходный URL и/или `expires_at` для своей ссылки

`DELETE /links/{short_code}` — удалить свою ссылку

`GET /links/{short_code}/stats` — получить статистику по ссылке

`GET /links/search?original_url=...` — найти ссылки по точному совпадению исходного URL

`GET /links/expired/history` — получить историю истекших и удалённых ссылок текущего пользователя

### Авторизация по методам

Без авторизации доступны:
- `POST /links/shorten`
- `GET /links/{short_code}`
- `GET /links/{short_code}/stats`
- `GET /links/search`

Только для авторизованного пользователя доступны:
- `PUT /links/{short_code}`
- `DELETE /links/{short_code}`
- `GET /links/expired/history`

## Примеры запросов

Во всех примерах локальный адрес сервиса такой:

```bash
BASE_URL=http://localhost:8000
```

### 1. Регистрация

```bash
curl -X POST "$BASE_URL/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'
```

Пример ответа:

```json
{
  "id": 1,
  "email": "user@example.com",
  "created_at": "2026-03-15T20:00:00.000000Z"
}
```

### 2. Логин

```bash
curl -X POST "$BASE_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "secret123"
  }'
```

Пример ответа:

```json
{
  "access_token": "<JWT_TOKEN>",
  "token_type": "bearer"
}
```

### 3. Создание короткой ссылки без кастомного элиаса

```bash
curl -X POST "$BASE_URL/links/shorten" \
  -H "Content-Type: application/json" \
  -d '{
    "original_url": "https://example.com/articles/very/long/path"
  }'
```

### 4. Создание короткой ссылки с элиасом и сроком жизни

```bash
curl -X POST "$BASE_URL/links/shorten" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{
    "original_url": "https://example.com/docs/page",
    "custom_alias": "my-docs-link",
    "expires_at": "2026-03-20T14:30:00Z"
  }'
```

Пример ответа:

```json
{
  "short_code": "my-docs-link",
  "short_url": "http://localhost:8000/links/my-docs-link",
  "original_url": "https://example.com/docs/page",
  "created_at": "2026-03-15T20:05:00.000000Z",
  "expires_at": "2026-03-20T14:30:00Z",
  "owner_user_id": 1
}
```

### 5. Переход по короткой ссылке

```bash
curl -i "$BASE_URL/links/my-docs-link"
```

Ожидается ответ с `307 Temporary Redirect` и заголовком `Location`.

### 6. Получение статистики

```bash
curl "$BASE_URL/links/my-docs-link/stats"
```

Пример ответа:

```json
{
  "short_code": "my-docs-link",
  "original_url": "https://example.com/docs/page",
  "created_at": "2026-03-15T20:05:00.000000Z",
  "click_count": 3,
  "last_used_at": "2026-03-15T20:10:00.000000Z",
  "expires_at": "2026-03-20T14:30:00Z"
}
```

### 7. Поиск по исходному URL

```bash
curl "$BASE_URL/links/search?original_url=https://example.com/docs/page"
```

### 8. Обновление ссылки

```bash
curl -X PUT "$BASE_URL/links/my-docs-link" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <JWT_TOKEN>" \
  -d '{
    "original_url": "https://example.com/docs/new-page",
    "expires_at": "2026-03-25T10:00:00Z"
  }'
```

### 9. Удаление ссылки

```bash
curl -X DELETE "$BASE_URL/links/my-docs-link" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

Ожидается ответ `204 No Content`.

### 10. История истекших и удалённых ссылок

```bash
curl "$BASE_URL/links/expired/history" \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

## Инструкция по запуску

### 1. Запустить проект

```bash
docker compose up --build
```

### 2. Проверить, что сервис запущен

После старта приложение будет доступно по адресам:
- `http://localhost:8000`
- `http://localhost:8000/docs`

Swagger UI доступен по `http://localhost:8000/docs`.

### 3. Остановка

```bash
docker compose down
```

Для удаления тома с данными Postgres:

```bash
docker compose down -v
```

## Описание БД

В проекте используется PostgreSQL

### Таблица `users`
Хранит зарегистрированных пользователей

Поля:
- `id` — первичный ключ;
- `email` — уникальный email пользователя;
- `hashed_password` — хэш пароля;
- `created_at` — дата регистрации

### Таблица `links`
Хранит активные короткие ссылки

Поля:
- `id` — первичный ключ;
- `short_code` — короткий код ссылки, уникальный;
- `original_url` — исходный URL;
- `created_at` — дата создания;
- `updated_at` — дата последнего обновления;
- `expires_at` — дата истечения ссылки, если задана;
- `click_count` — количество переходов;
- `last_used_at` — дата последнего перехода;
- `owner_user_id` — id владельца ссылки, может быть `NULL` для анонимных пользователей

Индексы:
- уникальный индекс по `short_code`;
- индекс по `original_url`;
- индекс по `expires_at`

### Таблица `expired_links`
Хранит архив истекших и удалённых ссылок

Поля:
- `id` — первичный ключ;
- `short_code` — короткий код ссылки;
- `original_url` — исходный URL;
- `created_at` — дата создания исходной ссылки;
- `expired_at` — дата переноса записи в архив;
- `click_count` — количество переходов на момент архивирования;
- `last_used_at` — дата последнего перехода;
- `owner_user_id` — id владельца;
- `reason` — причина архивирования (`expired`, `deleted`, `inactive_cleanup`)

### Redis

Redis используется как кэш и как брокер для Celery:
- кэш редиректов по короткому коду;
- кэш статистики;
- кэш поиска по `original_url`;
- очередь задач Celery для очистки истекших и неиспользуемых ссылок
