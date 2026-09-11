# ---- build stage -------------------------------------------------------
# Kept separate so the compiler needed for any dependency without a manylinux
# wheel doesn't end up in the image that actually runs in production.
FROM python:3.12-slim AS builder

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ---- runtime stage -----------------------------------------------------
FROM python:3.12-slim

# Unbuffered so log lines reach CloudWatch as they happen rather than when the
# buffer fills; no .pyc files since the filesystem is read-only to a non-root
# user anyway.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=builder /opt/venv /opt/venv

WORKDIR /app
COPY . .

# Drop privileges. The agent spawns core/mcp_server.py as a subprocess, which
# works fine unprivileged - it only needs to read the code and talk over pipes.
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser

# App Runner's default listening port.
EXPOSE 8080

# Migrations are deliberately NOT run here. With more than one instance the
# containers would race each other on startup, so "alembic upgrade head" is a
# separate step run once against the database before rolling out a new image.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
