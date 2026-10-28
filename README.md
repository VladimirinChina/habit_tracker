# Habit Tracker

Бэкенд трекера полезных привычек по мотивам книги Джеймса Клира «Атомные привычки».
Пользователь создаёт привычки («я буду [действие] в [время] в [месте]»), а Telegram-бот
присылает напоминания по расписанию.

## Стек

Python 3.14, Django, Django REST Framework, PostgreSQL, Celery, Redis,
SimpleJWT, drf-spectacular, django-cors-headers.

## Установка

1. Клонировать репозиторий и установить зависимости:

   ```bash
   poetry install
   ```

2. Создать файл `.env` по образцу `.env.template` и заполнить значения.

3. Поднять PostgreSQL и Redis (пример через Docker):

   ```bash
   docker run -d --name habits_db -e POSTGRES_DB=habits -e POSTGRES_USER=postgres \
     -e POSTGRES_PASSWORD=<пароль> -p 5433:5432 -v habits_pgdata:/var/lib/postgresql/data postgres:17
   docker run -d --name habits_redis -p 6380:6379 redis:7
   ```

   Порты и пароль должны совпадать со значениями в `.env`.

4. Применить миграции и запустить сервер:

   ```bash
   poetry run python manage.py migrate
   poetry run python manage.py runserver
   ```

## Переменные окружения

См. `.env.template`: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`,
`CSRF_TRUSTED_ORIGINS`, `POSTGRES_*`, `CELERY_BROKER_URL`, `TELEGRAM_BOT_TOKEN`.

## Telegram-напоминания

1. Создать бота через `@BotFather` и записать токен в `TELEGRAM_BOT_TOKEN`.
2. Написать боту `/start`, затем узнать свой chat id (`https://api.telegram.org/bot<TOKEN>/getUpdates`).
3. Сохранить chat id в профиле: `PATCH /api/users/profile/` с телом `{"tg_chat_id": "<id>"}`.
4. Запустить воркер и планировщик:

   ```bash
   poetry run celery -A config worker -l info
   poetry run celery -A config beat -l info
   ```

   На macOS воркер лучше запускать с флагом `--pool=solo`.

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
| GET | `/api/habits/public/` | Публичные привычки |
| POST | `/api/habits/create/` | Создание привычки |
| GET, PUT, PATCH | `/api/habits/<id>/` | Просмотр и редактирование своей привычки |
| DELETE | `/api/habits/<id>/delete/` | Удаление своей привычки |

Пагинация: параметры `limit` и `offset`, в ответе `count`, `next`, `previous`, `results`.
Авторизация: заголовок `Authorization: Bearer <access>`.

## Документация API

- Swagger UI: `/api/docs/`
- OpenAPI-схема: `/api/schema/`

## Тесты и покрытие

```bash
poetry run coverage run manage.py test
poetry run coverage report
```

## Качество кода

```bash
poetry run black .
poetry run isort .
poetry run flake8
poetry run mypy .
```