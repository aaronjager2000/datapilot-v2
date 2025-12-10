import logging
from typing import Callable

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.exc import SQLAlchemyError
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response

        except HTTPException as exc:
            # FastAPI HTTP exceptions - already handled, just log
            logger.warning(
                f"HTTP exception: {exc.status_code} - {exc.detail}",
                extra={
                    "status_code": exc.status_code,
                    "detail": exc.detail,
                    "path": request.url.path,
                }
            )
            raise

        except RequestValidationError as exc:
            # Pydantic validation errors
            logger.warning(
                "Validation error",
                extra={
                    "errors": exc.errors(),
                    "path": request.url.path,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Validation error",
                    "errors": exc.errors()
                }
            )

        except ValidationError as exc:
            # Pydantic validation errors (from models)
            logger.warning(
                "Model validation error",
                extra={
                    "errors": exc.errors(),
                    "path": request.url.path,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "detail": "Validation error",
                    "errors": exc.errors()
                }
            )

        except SQLAlchemyError as exc:
            # Database errors
            logger.error(
                "Database error",
                extra={
                    "error": str(exc),
                    "path": request.url.path,
                },
                exc_info=True
            )
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Database error occurred",
                    "error": "An error occurred while processing your request"
                }
            )

        except NotImplementedError as exc:
            # Feature not yet implemented
            logger.info(
                "Not implemented",
                extra={
                    "error": str(exc),
                    "path": request.url.path,
                }
            )
            return JSONResponse(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                content={
                    "detail": str(exc) or "This feature is not yet implemented"
                }
            )

        except Exception as exc:
            # Unexpected errors
            logger.error(
                f"Unexpected error: {type(exc).__name__}: {str(exc)}",
                extra={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "path": request.url.path,
                },
                exc_info=True
            )
            # In development, return the actual error
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Internal server error",
                    "error": str(exc),
                    "error_type": type(exc).__name__
                }
            )
