FROM --platform=linux/amd64 python:3.12-slim

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install wait-for-it 
RUN apt-get update && apt-get install -y --no-install-recommends \
    wait-for-it \
    && rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml ./
RUN pip install -U pip && pip install uv && uv sync --frozen --no-install-project --no-dev

RUN addgroup --gid 10000 django && adduser --shell /bin/bash --disabled-password --gecos "" --uid 10000 --ingroup django django
RUN chown -R django:django /app
USER django:django

COPY --chown=django:django . .

EXPOSE 8000

