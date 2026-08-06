"""In-process token-bucket rate limiter, keyed by client IP.

Single-instance scope on purpose: this page is a public marketing surface with an LLM
behind it, so the job is to stop one bored visitor (or a scraper) burning tokens. If the
service is ever scaled horizontally, swap the bucket store for Redis — the interface does
not change.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from fastapi import Request


@dataclass(slots=True)
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    def __init__(self, per_minute: int, burst: int) -> None:
        self.rate = per_minute / 60.0
        self.burst = float(burst)
        self._buckets: dict[str, _Bucket] = {}
        self._last_sweep = time.monotonic()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        self._sweep(now)

        bucket = self._buckets.get(key)
        if bucket is None:
            self._buckets[key] = _Bucket(tokens=self.burst - 1, updated=now)
            return True

        bucket.tokens = min(self.burst, bucket.tokens + (now - bucket.updated) * self.rate)
        bucket.updated = now
        if bucket.tokens < 1:
            return False
        bucket.tokens -= 1
        return True

    def _sweep(self, now: float) -> None:
        if now - self._last_sweep < 300:
            return
        self._last_sweep = now
        cutoff = now - 600
        self._buckets = {k: v for k, v in self._buckets.items() if v.updated > cutoff}


def client_key(request: Request) -> str:
    """Trust `X-Forwarded-For` only for its left-most hop; fall back to the socket peer."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
