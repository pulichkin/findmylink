FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends gettext-base && \
    rm -rf /var/lib/apt/lists/*

RUN mkdir -p /app/data/logs /app/data/db

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev


COPY src/configs/config.yaml /app/config.template.yaml

COPY . /app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# Place executables in the environment at the front of the path
ENV PATH="/app/.venv/bin:$PATH"

RUN echo '#!/bin/sh\n\
set -e\n\
echo "Генерация config.yaml из шаблона..."\n\
# Проверка наличия переменных\n\
if [ -z "$BOT_TOKEN" ]; then\n\
  echo "Ошибка: BOT_TOKEN не установлен!"\n\
  exit 1\n\
fi\n\
# Генерация с проверкой синтаксиса\n\
envsubst < /app/config.template.yaml > /app/config.yaml.tmp && \\\n\
python3 -c "import yaml; yaml.safe_load(open('\''/app/config.yaml.tmp'\''))" && \\\n\
mv /app/config.yaml.tmp /app/config.yaml || {\n\
  echo "Ошибка генерации config.yaml!"\n\
  cat /app/config.yaml.tmp\n\
  exit 1\n\
}\n\
echo "Конфиг успешно сгенерирован"\n\
exec "$@"' > /entrypoint.sh && \
chmod +x /entrypoint.sh

ENV CFG_CONFIG=./config.yaml
ENTRYPOINT ["/entrypoint.sh"]
CMD ["granian", "--interface", "asgi", "--host", "0.0.0.0", "src.app:app"]
