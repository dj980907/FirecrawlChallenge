# Production Dockerfile - FastAPI
FROM python:3.12-slim

WORKDIR /app

ENV POETRY_VIRTUALENVS_CREATE=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir poetry

COPY backend/api/pyproject.toml backend/api/poetry.lock ./
RUN poetry install --no-interaction --no-ansi --no-root --only main

COPY backend/api/app ./app

EXPOSE 80

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
