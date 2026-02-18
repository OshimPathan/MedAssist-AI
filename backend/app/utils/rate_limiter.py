"""
MedAssist AI - Rate Limiting Middleware
In-memory rate limiting with sliding window per client IP
"""

import time
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding-window rate limiter per client IP.
    Limits requests to RATE_LIMIT_PER_MINUTE per 60-second window.
    Health checks and docs are exempt.
    """

    def __init__(self, app, max_requests: int = None):
        super().__init__(app)
        self.max_requests = max_requests or settings.RATE_LIMIT_PER_MINUTE
        self.window_seconds = 60
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_old_entries(self, ip: str, now: float):
        cutoff = now - self.window_seconds
        self._requests[ip] = [t for t in self._requests[ip] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Exempt health checks and docs
        path = request.url.path
        if path in ("/", "/health", "/api/docs", "/api/redoc", "/openapi.json"):
            return await call_next(request)

        ip = self._get_client_ip(request)
        now = time.time()
        self._clean_old_entries(ip, now)

        if len(self._requests[ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for {ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Max {self.max_requests} requests per minute.",
                headers={"Retry-After": "60"},
            )

        self._requests[ip].append(now)

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(
            self.max_requests - len(self._requests[ip])
        )
        return response
