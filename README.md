# ИМЯ

**findmylink** — браузерное расширение, для быстрого поиска - вкладок и закладок и подписками через Telegram-бота, API.

# СИНТАКСИС

```sh
# Запуск через Docker Compose
$ docker compose up --build

# Основные директории
findmylink/api      # backend API (Python, Litestar, SQLAlchemy)
findmylink/bot      # Telegram-бот (Python, aiogram)
findmylink/chrome-extension  # Chrome-расширение (TypeScript, Vite)
```

# ОПИСАНИЕ

- **API**: Асинхронный backend на Python (Litestar + SQLAlchemy), поддержка JWT, миграции, шаблоны Jinja2, интеграция с KeyDB и SQLite.
- **Telegram-бот**: Управление подписками, триалами, промокодами, интеграция с API и KeyDB.
- **Chrome-расширение**: Поиск по закладкам и вкладкам, авторизация через Telegram, централизованная конфигурация, локализация.
- **Инфраструктура**: Docker Compose, KeyDB/Redis, миграции, логирование, HTTPS/nginx-ready.

# ТРЕБОВАНИЯ

- Docker, Docker Compose
- Python 3.13+
- Node.js 18+, npm/pnpm (для chrome-extension)
- Переменные окружения (см. `api/src/configs/.env.example`, `bot/src/configs/.env.example`)

# ФАЙЛЫ

- `api/` — исходный код и конфиги backend API
- `bot/` — исходный код Telegram-бота
- `chrome-extension/` — исходный код расширения для браузера
- `docker-compose.yaml` — описание сервисов и инфраструктуры
- `README.md` — этот файл

# АВТОР

- [Александр Пуличкин](https://github.com/pulichkin)

# СМОТРИТЕ ТАКЖЕ

- [Документация по Litestar](https://litestar.dev/)
- [Документация по aiogram](https://docs.aiogram.dev/)
- [Документация по KeyDB](https://docs.keydb.dev/)
- [Пример оформления README.md](https://github.com/pulichkin/litestarcats)

