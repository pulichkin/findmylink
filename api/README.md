# ИМЯ

**findmylink-api** — асинхронный backend для FindMyLink: управление пользователями, подписками, промокодами, авторизацией через Telegram.

# СИНТАКСИС

```sh
# Запуск API
$ cd api
$ docker compose up api
# или локально
$ uvicorn src.app:app --reload
```

# ОПИСАНИЕ

- REST API на Python (Litestar + SQLAlchemy)
- JWT-авторизация, поддержка Telegram Login Widget
- Миграции, асинхронная работа с SQLite
- Интеграция с Redis/KeyDB для rate-limit и кэша
- Jinja2-шаблоны для страниц

# ТРЕБОВАНИЯ

- Python 3.13+
- Docker (для prod)
- Переменные окружения (см. `src/configs/.env.example`)

# ФАЙЛЫ

- `src/app.py` — основной ASGI-приложение
- `src/models/` — SQLAlchemy-модели
- `src/utils/` — бизнес-логика и утилиты
- `src/configs/` — конфиги, .env, миграции
- `src/templates/` — Jinja2-шаблоны

# АВТОР

- [Александр Пуличкин](https://github.com/pulichkin)

# СМОТРИТЕ ТАКЖЕ

- [Документация по Litestar](https://litestar.dev/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Пример оформления README.md](https://github.com/pulichkin/litestarcats)

## Новая система конфигурации

Вся конфигурация теперь хранится в файле `config.yaml` и типизирована через `config.py` с использованием [config-lib-msgspec](https://github.com/rastaclaus/config-lib-msgspec).

- Поддержка YAML, переменных окружения, CLI
- Типизация через msgspec.Struct
- Пример:

```python
from config import config
print(config.telegram.bot_token)
```

Изменить параметры можно в config.yaml или через переменные окружения (например, CFG_TELEGRAM__BOT_TOKEN).
