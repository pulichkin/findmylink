# ИМЯ

**findmylink-bot** — Telegram-бот для управления подписками, триалами, промокодами и интеграции с FindMyLink API.

# СИНТАКСИС

```sh
# Запуск бота
$ cd bot
$ docker compose up bot
# или локально
$ uvicorn src.bot:app --reload
```

# ОПИСАНИЕ

- Telegram-бот на Python (aiogram/ext)
- Управление подписками, триалами, промокодами
- Интеграция с API и KeyDB/Redis
- Локализация, логирование, резервные копии

# ТРЕБОВАНИЯ

- Python 3.13+
- Docker (для prod)
- Переменные окружения (см. `src/configs/.env.example`)

# ФАЙЛЫ

- `src/bot.py` — основной бот
- `src/handlers/` — обработчики команд и событий
- `src/utils/` — бизнес-логика, работа с БД и Redis
- `src/configs/` — конфиги, .env

# АВТОР

- [Александр Пуличкин](https://github.com/pulichkin)

# СМОТРИТЕ ТАКЖЕ

- [Документация по aiogram](https://docs.aiogram.dev/)
- [KeyDB](https://docs.keydb.dev/)
- [Пример оформления README.md](https://github.com/pulichkin/litestarcats)
