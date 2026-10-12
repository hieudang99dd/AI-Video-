from __future__ import annotations

from app.core.config import settings


def enqueue_render(job_id: str) -> bool:
    if not settings.redis_url:
        return False
    try:
        import redis
        r = redis.from_url(settings.redis_url, decode_responses=True)
        r.lpush("cinevideo:render", job_id)
        return True
    except Exception:
        return False


def pop_render(timeout: int = 2) -> str | None:
    if not settings.redis_url:
        return None
    try:
        import redis
        r = redis.from_url(settings.redis_url, decode_responses=True)
        item = r.brpop("cinevideo:render", timeout=timeout)
        return item[1] if item else None
    except Exception:
        return None
