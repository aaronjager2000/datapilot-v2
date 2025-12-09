import logging
import time
from typing import Callable, Optional

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        redis_client: Redis,
        default_limit: int = 100,
        default_window: int = 60,
        authenticated_limit: int = 1000,
        authenticated_window: int = 60,
    ):
        super().__init__(app)
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window
        self.authenticated_limit = authenticated_limit
        self.authenticated_window = authenticated_window

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)

        # Determine rate limit key and limits
        if user_id:
            rate_limit_key = f"rate_limit:user:{user_id}"
            limit = self.authenticated_limit
            window = self.authenticated_window
        else:
            client_ip = request.client.host if request.client else "unknown"
            rate_limit_key = f"rate_limit:ip:{client_ip}"
            limit = self.default_limit
            window = self.default_window

        # Check rate limit
        try:
            is_allowed, remaining, reset_time = await self._check_rate_limit(
                rate_limit_key, limit, window
            )

            if not is_allowed:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "key": rate_limit_key,
                        "limit": limit,
                        "window": window,
                        "path": request.url.path,
                    }
                )
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": "Rate limit exceeded. Please try again later.",
                        "retry_after": reset_time
                    },
                    headers={
                        "X-RateLimit-Limit": str(limit),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(reset_time)
                    }
                )

            # Process request
            response = await call_next(request)

            # Add rate limit headers
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(reset_time)

            return response

        except Exception as exc:
            # Fail open - if Redis is unavailable, allow the request
            logger.error(
                "Rate limit check failed, allowing request",
                extra={
                    "error": str(exc),
                    "key": rate_limit_key,
                },
                exc_info=True
            )
            response = await call_next(request)
            return response

    async def _check_rate_limit(
        self, key: str, limit: int, window: int
    ) -> tuple[bool, int, int]:
        now = time.time()
        window_start = now - window

        # Use Redis sorted set for sliding window
        pipeline = self.redis.pipeline()

        # Remove old entries outside the window
        pipeline.zremrangebyscore(key, 0, window_start)

        # Count requests in current window
        pipeline.zcard(key)

        # Add current request
        pipeline.zadd(key, {str(now): now})

        # Set expiry on the key
        pipeline.expire(key, window)

        results = await pipeline.execute()

        # Get count before adding current request
        current_count = results[1]

        # Calculate reset time (end of current window)
        reset_time = int(now + window)

        # Check if limit exceeded
        is_allowed = current_count < limit
        remaining = max(0, limit - current_count - 1)

        return is_allowed, remaining, reset_time


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window: int
) -> tuple[bool, int, int]:
    now = time.time()
    window_start = now - window

    try:
        pipeline = redis.pipeline()

        pipeline.zremrangebyscore(key, 0, window_start)
        pipeline.zcard(key)
        pipeline.zadd(key, {str(now): now})
        pipeline.expire(key, window)

        results = await pipeline.execute()
        current_count = results[1]

        reset_time = int(now + window)
        is_allowed = current_count < limit
        remaining = max(0, limit - current_count - 1)

        return is_allowed, remaining, reset_time

    except Exception as exc:
        logger.error(
            "Rate limit check failed",
            extra={"error": str(exc), "key": key},
            exc_info=True
        )
        # Fail open on error
        return True, limit, int(now + window)
