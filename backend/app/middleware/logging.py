import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate request ID
        request_id = request.headers.get("X-Request-ID", "unknown")

        # Extract user info if available
        user_id = getattr(request.state, "user_id", None)
        org_id = getattr(request.state, "organization_id", None)

        # Log request
        start_time = time.time()

        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "user_id": str(user_id) if user_id else None,
                "organization_id": str(org_id) if org_id else None,
                "client_host": request.client.host if request.client else None,
            }
        )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration * 1000, 2),
                    "user_id": str(user_id) if user_id else None,
                    "organization_id": str(org_id) if org_id else None,
                }
            )

            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as exc:
            duration = time.time() - start_time

            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "user_id": str(user_id) if user_id else None,
                    "organization_id": str(org_id) if org_id else None,
                    "error": str(exc),
                },
                exc_info=True
            )

            raise
