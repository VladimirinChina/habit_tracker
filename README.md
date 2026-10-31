# Habit Tracker

Бэкенд трекера полезных привычек по мотивам книги Джеймса Клира «Атомные привычки».
Пользователь создаёт привычки («я буду [действие] в [время] в [месте]»), а Telegram-бот
присылает напоминания по расписанию.

## Стек

Python 3.14, Django, Django REST Framework, PostgreSQL, Celery, Redis, Nginx, Gunicorn,
SimpleJWT, drf-spectacular, django-cors-headers, Docker Compose, GitHub Actions.

## Запуск одной командой (Docker)

1. Создать `.env` по образцу `.env.template` и заполнить значения (`SECRET_KEY`,
   `POSTGRES_*`, `TELEGRAM_BOT_TOKEN`). Хосты `db` и `redis` внутри контейнеров
   подставляются автоматически.
2. Запустить все сервисы:

   ```bash
   docker compose up -d --build
   ```

3. Проверить: `docker compose ps` (должны работать `db`, `redis`, `app`,
   `celery_worker`, `celery_beat`, `nginx`), документация открывается на
   `http://localhost/api/docs/` (порт задаётся переменной `NGINX_PORT`).
4. Создать суперпользователя (по желанию):

   ```bash
   docker compose exec app python manage.py createsuperuser
   ```

Остановить: `docker compose down` (данные БД сохраняются в volume; `down -v` удаляет их).

### Сервисы docker-compose

| Сервис | Назначение |
|--------|-----------|
| `db` | PostgreSQL 17, данные в volume `pg_data` |
| `redis` | брокер сообщений Celery |
| `app` | Django + Gunicorn, при старте выполняет миграции и `collectstatic` |
| `celery_worker` | выполнение задач Celery |
| `celery_beat` | расписание: напоминания каждую минуту |
| `nginx` | обратный прокси, раздача статики |

## Локальный запуск без Docker

1. `poetry install`
2. Создать `.env` по `.env.template` (`POSTGRES_HOST=localhost`, порты своих локальных PostgreSQL и Redis).
3. `poetry run python manage.py migrate`
4. `poetry run python manage.py runserver`
5. Celery (в отдельных терминалах; на macOS воркер запускать с `--pool=solo`):

   ```bash
   poetry run celery -A config worker -l info
   poetry run celery -A config beat -l info
   ```

## Переменные окружения

См. `.env.template`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
`CSRF_TRUSTED_ORIGINS`, `POSTGRES_*`, `CELERY_BROKER_URL`, `TELEGRAM_BOT_TOKEN`, `NGINX_PORT`.

## Telegram-напоминания

1. Создать бота через `@BotFather`, токен записать в `TELEGRAM_BOT_TOKEN`.
2. Написать боту `/start`, узнать свой chat id: `https://api.telegram.org/bot<TOKEN>/getUpdates`.
3. Сохранить chat id: `PATCH /api/users/profile/` с телом `{"tg_chat_id": "<id>"}`.

Задача `send_habit_reminders` запускается каждую минуту и отправляет напоминания о полезных
привычках в назначенное время с учётом периодичности (раз в N дней, N от 1 до 7).

## Эндпоинты

| Метод | URL | Описание |
|-------|-----|----------|
| POST | `/api/users/register/` | Регистрация |
| POST | `/api/users/login/` | Авторизация (JWT) |
| POST | `/api/users/token/refresh/` | Обновление токена |
| GET, PATCH | `/api/users/profile/` | Профиль, Telegram chat id |
| GET | `/api/habits/` | Привычки текущего пользователя (по 5 на страницу) |
| GET | `/api/habits/public/` | Публичные привычки (без авторизации) |
| POST | `/api/habits/create/` | Создание привычки |
| GET, PUT, PATCH | `/api/habits/<id>/` | Просмотр и редактирование своей привычки |
| DELETE | `/api/habits/<id>/delete/` | Удаление своей привычки |

Пагинация: `limit` и `offset`, в ответе `count`, `next`, `previous`, `results`.
Авторизация: заголовок `Authorization: Bearer <access>`.
Документация: Swagger UI `/api/docs/`, схема OpenAPI `/api/schema/`.

## Тесты и качество кода

```bash
poetry run coverage run manage.py test
poetry run coverage report
poetry run black . && poetry run isort . && poetry run flake8 && poetry run mypy .
```

## CI/CD (GitHub Actions)

Pipeline описан в `.github/workflows/ci-cd.yaml` и состоит из трёх задач:

1. **test** — линтинг (`black`, `isort`, `flake8`, `mypy`) и тесты с проверкой покрытия не ниже 80%.
2. **build** — сборка Docker-образа; при push образ публикуется в GitHub Container Registry (GHCR).
3. **deploy** — при успешных предыдущих шагах и push в `develop` копирует на сервер
   `docker-compose.prod.yaml`, конфигурацию Nginx и `.env`, скачивает свежий образ и
   перезапускает сервисы, затем проверяет, что приложение отвечает.

### Секреты репозитория

GitHub → Settings → Secrets and variables → Actions:

| Секрет | Описание |
|--------|----------|
| `SSH_HOST` | IP-адрес сервера |
| `SSH_USER` | пользователь для деплоя |
| `SSH_KEY` | приватный SSH-ключ (целиком, с `BEGIN`/`END`) |
| `SECRET_KEY` | секретный ключ Django для сервера |
| `POSTGRES_PASSWORD` | пароль базы данных на сервере |
| `TELEGRAM_BOT_TOKEN` | токен Telegram-бота |

`GITHUB_TOKEN` создавать не нужно: он выдаётся автоматически. В настройках репозитория
(Settings → Actions → General → Workflow permissions) должно быть разрешено чтение и запись.

### Подготовка сервера (Ubuntu)

1. Создать пользователя для деплоя и добавить его в группу `docker`.
2. Установить Docker и Docker Compose (плагин `docker compose`).
3. Добавить публичный SSH-ключ в `~/.ssh/authorized_keys` пользователя деплоя;
   приватный ключ — в секрет `SSH_KEY`.
4. Открыть порты в файрволе: `sudo ufw allow OpenSSH`, `sudo ufw allow 8080/tcp`.
5. Запустить pipeline (push в `develop`). Приложение будет доступно по адресу
   `http://<SSH_HOST>:8080/api/docs/`.