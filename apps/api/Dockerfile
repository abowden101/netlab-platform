# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Containerlab binary so the API can orchestrate labs on the host's Docker.
# The host Docker socket is mounted at runtime (see docker-compose.yml).
RUN apt-get update && apt-get install -y --no-install-recommends \
      curl ca-certificates \
    && curl -sL https://get.containerlab.dev | bash \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY packages/shared /app/packages/shared
COPY packages/topology /app/packages/topology
COPY packages/drivers /app/packages/drivers
COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir -e /app/packages/shared \
       -e /app/packages/topology -e /app/packages/drivers

COPY apps/api/app /app/app
COPY apps/api/alembic /app/alembic
COPY apps/api/alembic.ini /app/alembic.ini
COPY labs /app/labs

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
