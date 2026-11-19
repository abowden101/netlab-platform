"""Deploy queue: FIFO, Redis-backed when Redis is up, in-memory otherwise."""

from collections import deque

import redis


class DeployQueue:
    """A FIFO queue of (user_id, lab_slug) deploy requests.

    When Redis is available the queue is a Redis list (survives API
    restarts); otherwise it is an in-process deque (dev only)."""

    KEY = "netlab:deploy-queue"

    def __init__(self, redis_client: redis.Redis | None = None):
        self._redis = redis_client
        self._memory: deque[tuple[int, str]] = deque()

    def enqueue(self, user_id: int, lab_slug: str) -> int:
        """Append a request; return its 1-based position."""
        if self._redis is not None:
            self._redis.rpush(self.KEY, f"{user_id}:{lab_slug}")
            return self._redis.llen(self.KEY)
        self._memory.append((user_id, lab_slug))
        return len(self._memory)

    def dequeue(self) -> tuple[int, str] | None:
        if self._redis is not None:
            item = self._redis.lpop(self.KEY)
            if item is None:
                return None
            user_id, _, lab_slug = item.partition(":")
            return int(user_id), lab_slug
        if not self._memory:
            return None
        return self._memory.popleft()

    def position(self, user_id: int, lab_slug: str) -> int | None:
        """1-based position of a request, or None if not queued."""
        if self._redis is not None:
            items = self._redis.lrange(self.KEY, 0, -1)
            for i, item in enumerate(items, start=1):
                if item == f"{user_id}:{lab_slug}":
                    return i
            return None
        for i, (uid, slug) in enumerate(self._memory, start=1):
            if uid == user_id and slug == lab_slug:
                return i
        return None

    def __len__(self) -> int:
        if self._redis is not None:
            return self._redis.llen(self.KEY)
        return len(self._memory)
