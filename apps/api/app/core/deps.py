"""Shared FastAPI dependencies: DB session, optional Redis."""

from collections.abc import Iterator

import redis
from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal

_redis_client: redis.Redis | None = None


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_redis() -> redis.Redis | None:
    """Return a Redis client, or None when Redis is unreachable (the queue
    and session-state helpers fall back to in-memory stores)."""
    global _redis_client
    if _redis_client is None:
        try:
            client = redis.Redis.from_url(
                settings.redis_url, socket_connect_timeout=1, decode_responses=True
            )
            client.ping()
            _redis_client = client
        except Exception:
            return None
    return _redis_client


# Re-export for routers that prefer `Depends(get_db)`.
DB = Depends(get_db)
