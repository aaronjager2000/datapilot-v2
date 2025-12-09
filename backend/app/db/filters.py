from typing import Optional, TypeVar
from uuid import UUID

from sqlalchemy import Select
from sqlalchemy.orm import Query
from fastapi import Request

from app.models.base import BaseModel


T = TypeVar("T", bound=BaseModel)


def apply_tenant_filter(
    query: Select[tuple[T]],
    organization_id: UUID,
    model: type[T],
    bypass: bool = False
) -> Select[tuple[T]]:
    if bypass:
        return query

    return query.where(model.organization_id == organization_id)


def get_tenant_query(
    request: Request,
    query: Select[tuple[T]],
    model: type[T]
) -> Select[tuple[T]]:
    organization_id = getattr(request.state, "organization_id", None)
    is_superuser = getattr(request.state, "is_superuser", False)

    if is_superuser:
        return query

    if not organization_id:
        raise ValueError("No organization_id found in request state")

    return apply_tenant_filter(query, organization_id, model)
