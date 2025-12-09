from typing import Callable, Optional
from uuid import UUID

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.security import decode_token


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract organization_id from JWT token if present
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
            token_data = decode_token(token)

            if token_data:
                # Store organization_id in request state for tenant isolation
                request.state.organization_id = token_data.org_id
                request.state.user_id = token_data.sub
                request.state.is_superuser = token_data.is_superuser
            else:
                request.state.organization_id = None
                request.state.user_id = None
                request.state.is_superuser = False
        else:
            request.state.organization_id = None
            request.state.user_id = None
            request.state.is_superuser = False

        response = await call_next(request)
        return response


def get_organization_id(request: Request) -> Optional[UUID]:
    return getattr(request.state, "organization_id", None)


def get_user_id(request: Request) -> Optional[UUID]:
    return getattr(request.state, "user_id", None)


def is_superuser(request: Request) -> bool:
    return getattr(request.state, "is_superuser", False)
