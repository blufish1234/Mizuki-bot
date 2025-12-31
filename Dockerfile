FROM python:3.13-alpine AS builder

RUN apk add --no-cache git
WORKDIR /app

COPY uv.lock pyproject.toml ./

ENV UV_NO_DEV=1

# Improve startup speed (increase image size)
# ENV UV_COMPILE_BYTECODE=1

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    uv sync --frozen

FROM python:3.13-alpine

COPY --from=builder /app/.venv /app/.venv

COPY ./mizuki_bot /app/mizuki_bot
COPY ./main.py /app/main.py

WORKDIR /app

CMD ["/app/.venv/bin/python", "main.py"]
