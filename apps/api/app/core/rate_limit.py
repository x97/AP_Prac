"""Small in-process rate limiter.

This is adequate for a single-process dev/demo deployment. Production with
multiple workers should replace the store with Redis; the middleware contract
stays the same.
"""

from __future__ import annotations

import hashlib
import threading
import time
from collections import deque
from typing import Deque

from fastapi import Request
from fastapi.responses import JSONResponse


class SlidingWindowLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return False, retry_after
            bucket.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._buckets.clear()


limiter = SlidingWindowLimiter()


def _session_key(request: Request) -> str | None:
    for cookie_name in ("ap_session", "ap_admin_session"):
        value = request.cookies.get(cookie_name)
        if value:
            digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]
            return f"session:{digest}"
    return None


def _ip_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",")[0].strip() if forwarded else ""
    if not ip:
        ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


async def rate_limit_middleware(request: Request, call_next):
    from app.core.config import get_settings

    settings = get_settings()
    if (
        not settings.rate_limit_enabled
        or request.method == "OPTIONS"
        or not request.url.path.startswith("/api/")
    ):
        return await call_next(request)

    checks = [(f"{_ip_key(request)}:all", settings.rate_limit_per_minute * 2)]
    session_key = _session_key(request)
    if session_key:
        checks.append((f"{session_key}:all", settings.rate_limit_per_minute))
    retry_after = 0
    for key, limit in checks:
        allowed, wait = limiter.allow(key, limit, 60)
        if not allowed:
            retry_after = max(retry_after, wait)
    if retry_after:
        return JSONResponse(
            status_code=429,
            content={
                "code": "RATE_LIMITED",
                "message": "请求过于频繁，请稍后再试",
            },
            headers={"Retry-After": str(retry_after)},
        )
    response = await call_next(request)
    response.headers.setdefault("X-RateLimit-Limit", str(settings.rate_limit_per_minute))
    return response
