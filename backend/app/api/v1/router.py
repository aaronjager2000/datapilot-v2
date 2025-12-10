from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    organizations,
    files,
    datasets,
    records,
    websocket,
    visualizations,
    dashboards,
    insights,
    webhooks,
    roles,
    permissions,
)

api_router = APIRouter()

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    organizations.router,
    prefix="/organizations",
    tags=["organizations"]
)

api_router.include_router(
    files.router,
    prefix="/files",
    tags=["files"]
)

api_router.include_router(
    datasets.router,
    prefix="/datasets",
    tags=["datasets"]
)

api_router.include_router(
    records.router,
    prefix="/records",
    tags=["records"]
)

api_router.include_router(
    websocket.router,
    prefix="/ws",
    tags=["websocket"]
)

api_router.include_router(
    visualizations.router,
    prefix="/visualizations",
    tags=["visualizations"]
)

api_router.include_router(
    dashboards.router,
    prefix="/dashboards",
    tags=["dashboards"]
)

api_router.include_router(
    insights.router,
    prefix="",
    tags=["insights"]
)

api_router.include_router(
    webhooks.router,
    prefix="/webhooks",
    tags=["webhooks"]
)

api_router.include_router(
    roles.router,
    prefix="/roles",
    tags=["roles"]
)

api_router.include_router(
    permissions.router,
    prefix="/permissions",
    tags=["permissions"]
)
