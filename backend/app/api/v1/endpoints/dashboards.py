"""
Dashboard API endpoints.

Handles dashboard creation, retrieval, updates, deletion, widget management,
and duplication with proper authentication and permissions.
"""

import logging
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Dashboard, Visualization, Dataset
from app.schemas.dashboard import (
    DashboardCreate,
    DashboardUpdate,
    DashboardResponse,
    DashboardListResponse,
    AddWidgetRequest,
    RemoveWidgetRequest,
    AddVisualizationRequest,
    PopulatedWidget,
    DashboardWidget,
)
from app.schemas.visualization import VisualizationResponse
from app.services.visualization.aggregator import AggregationService
from app.services.visualization.chart_generator import ChartGenerator

logger = logging.getLogger(__name__)

router = APIRouter()


async def populate_widget(
    widget: dict,
    db: AsyncSession,
    organization_id: UUID
) -> PopulatedWidget:
    """
    Populate a widget with visualization data.

    Args:
        widget: Widget configuration dict
        db: Database session
        organization_id: Current organization ID

    Returns:
        PopulatedWidget with visualization data
    """
    populated = PopulatedWidget(**widget)

    # Only populate if it's a visualization widget
    if widget.get('type') == 'visualization' and widget.get('visualization_id'):
        viz_id = widget['visualization_id']

        try:
            # Get visualization
            visualization = await db.get(Visualization, viz_id)

            if visualization and visualization.organization_id == organization_id:
                # Get dataset
                dataset = await db.get(Dataset, visualization.dataset_id)
                creator = await db.get(User, visualization.created_by)

                # Generate chart data
                chart_generator = ChartGenerator()
                aggregation_service = AggregationService(db)

                config = visualization.config
                aggregated_data = await aggregation_service.aggregate_data(
                    dataset_id=visualization.dataset_id,
                    config={
                        'x_column': config.get('x_axis'),
                        'y_column': config.get('y_axis'),
                        'grouping': config.get('grouping'),
                        'aggregation': config.get('aggregation', 'sum'),
                        'filters': config.get('filters', {})
                    }
                )

                chart_config = chart_generator.generate_chart_config(
                    chart_type=visualization.chart_type.value,
                    data=aggregated_data,
                    options={
                        'title': visualization.name,
                        'colors': config.get('colors'),
                        'theme': config.get('theme', 'light'),
                        **config.get('options', {})
                    }
                )

                # Build visualization response
                viz_response = VisualizationResponse.model_validate(visualization)
                viz_response.chart_data = chart_config
                viz_response.dataset_name = dataset.name if dataset else None
                viz_response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

                populated.visualization = viz_response

        except Exception as e:
            logger.warning(f"Failed to populate widget {widget.get('id')}: {e}")

    return populated


@router.post(
    "",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Create a new dashboard.

    Accepts name, description, initial layout, and optional widgets.

    **Required Permission:** `data:visualize`
    """
    try:
        # Create dashboard record
        dashboard = Dashboard(
            name=dashboard_data.name,
            description=dashboard_data.description,
            layout=dashboard_data.layout.model_dump(),
            is_public=dashboard_data.is_public,
            widgets=[w.model_dump() for w in dashboard_data.widgets],
            organization_id=organization_id,
            created_by=current_user.id
        )

        # Add visualizations if provided
        if dashboard_data.visualization_ids:
            for viz_id in dashboard_data.visualization_ids:
                # Verify visualization exists and belongs to organization
                visualization = await db.get(Visualization, viz_id)
                if visualization and visualization.organization_id == organization_id:
                    dashboard.visualizations.append(visualization)

        db.add(dashboard)
        await db.commit()
        await db.refresh(dashboard)

        logger.info(f"User {current_user.id} created dashboard {dashboard.id}")

        # Build response with populated widgets
        populated_widgets = []
        for widget in dashboard.widgets:
            populated = await populate_widget(widget, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, dashboard.created_by)

        response = DashboardResponse.model_validate(dashboard)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except Exception as e:
        logger.error(f"Failed to create dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create dashboard: {str(e)}"
        )


@router.get(
    "",
    response_model=DashboardListResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def list_dashboards(
    created_by: Optional[UUID] = Query(None, description="Filter by creator user ID"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    is_public: Optional[bool] = Query(None, description="Filter by public status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    List all dashboards for the organization.

    Supports filtering by creator, public status, and search.
    Includes preview data with widget counts.

    **Required Permission:** `data:view`
    """
    try:
        # Build query
        query = select(Dashboard).where(
            Dashboard.organization_id == organization_id
        )

        # Apply filters
        if created_by:
            query = query.where(Dashboard.created_by == created_by)

        if is_public is not None:
            query = query.where(Dashboard.is_public == is_public)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (Dashboard.name.ilike(search_filter)) |
                (Dashboard.description.ilike(search_filter))
            )

        # Count total
        count_query = select(Dashboard.id).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.all())

        # Apply pagination
        skip = (page - 1) * page_size
        query = query.order_by(Dashboard.created_at.desc()).offset(skip).limit(page_size)

        # Execute query
        result = await db.execute(query)
        dashboards = result.scalars().all()

        # Build response items with preview data
        items = []
        for dashboard in dashboards:
            creator = await db.get(User, dashboard.created_by)

            # Populate widgets with preview data (first 3 widgets)
            populated_widgets = []
            preview_widgets = dashboard.widgets[:3] if dashboard.widgets else []

            for widget in preview_widgets:
                populated = await populate_widget(widget, db, organization_id)
                populated_widgets.append(populated)

            response = DashboardResponse.model_validate(dashboard)
            response.populated_widgets = populated_widgets
            response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
            response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

            items.append(response)

        total_pages = (total + page_size - 1) // page_size

        return DashboardListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to list dashboards: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list dashboards: {str(e)}"
        )


@router.get(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_dashboard(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get a dashboard with all widgets and their data.

    Executes all visualizations and populates widgets with fresh data.

    **Required Permission:** `data:view`
    """
    try:
        # Get dashboard
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if dashboard.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Populate all widgets with data
        populated_widgets = []
        for widget in dashboard.widgets:
            populated = await populate_widget(widget, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, dashboard.created_by)

        response = DashboardResponse.model_validate(dashboard)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}"
        )


@router.put(
    "/{dashboard_id}",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def update_dashboard(
    dashboard_id: UUID,
    update_data: DashboardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Update dashboard layout or metadata.

    Can add/remove widgets by updating the widgets array.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get dashboard
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if dashboard.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)

        if 'name' in update_dict:
            dashboard.name = update_dict['name']

        if 'description' in update_dict:
            dashboard.description = update_dict['description']

        if 'layout' in update_dict:
            layout_data = update_dict['layout']
            dashboard.layout = layout_data.model_dump() if hasattr(layout_data, 'model_dump') else layout_data

        if 'widgets' in update_dict:
            widgets_data = update_dict['widgets']
            dashboard.widgets = [
                w.model_dump() if hasattr(w, 'model_dump') else w
                for w in widgets_data
            ]

        if 'is_public' in update_dict:
            dashboard.is_public = update_dict['is_public']

        await db.commit()
        await db.refresh(dashboard)

        logger.info(f"User {current_user.id} updated dashboard {dashboard_id}")

        # Build response with populated widgets
        populated_widgets = []
        for widget in dashboard.widgets:
            populated = await populate_widget(widget, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, dashboard.created_by)

        response = DashboardResponse.model_validate(dashboard)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update dashboard: {str(e)}"
        )


@router.delete(
    "/{dashboard_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def delete_dashboard(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Delete a dashboard.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get dashboard
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if dashboard.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Delete dashboard
        await db.delete(dashboard)
        await db.commit()

        logger.info(f"User {current_user.id} deleted dashboard {dashboard_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete dashboard: {str(e)}"
        )


@router.post(
    "/{dashboard_id}/widgets",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def add_widget_to_dashboard(
    dashboard_id: UUID,
    request: AddVisualizationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Add a widget to a dashboard.

    Accepts visualization_id, position, and size. Auto-assigns position/size if not provided.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get dashboard
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if dashboard.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Verify visualization exists and belongs to organization
        visualization = await db.get(Visualization, request.visualization_id)
        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {request.visualization_id} not found"
            )

        if visualization.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visualization does not belong to your organization"
            )

        # Auto-assign position if not provided
        position = request.position
        if not position:
            # Find next available position (simple stacking)
            max_y = 0
            for widget in dashboard.widgets:
                widget_y = widget.get('position', {}).get('y', 0)
                widget_height = widget.get('size', {}).get('height', 4)
                max_y = max(max_y, widget_y + widget_height)

            position = {'x': 0, 'y': max_y}

        # Auto-assign size if not provided
        size = request.size or {'width': 6, 'height': 4}

        # Create widget
        widget = DashboardWidget(
            id=str(uuid4()),
            type='visualization',
            visualization_id=request.visualization_id,
            position=position,
            size=size,
            config={}
        )

        # Add widget to dashboard
        widgets = dashboard.widgets or []
        widgets.append(widget.model_dump())
        dashboard.widgets = widgets

        await db.commit()
        await db.refresh(dashboard)

        logger.info(f"User {current_user.id} added widget to dashboard {dashboard_id}")

        # Build response with populated widgets
        populated_widgets = []
        for w in dashboard.widgets:
            populated = await populate_widget(w, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, dashboard.created_by)

        response = DashboardResponse.model_validate(dashboard)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to add widget to dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add widget to dashboard: {str(e)}"
        )


@router.delete(
    "/{dashboard_id}/widgets/{widget_id}",
    response_model=DashboardResponse,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def remove_widget_from_dashboard(
    dashboard_id: UUID,
    widget_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Remove a widget from a dashboard.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get dashboard
        dashboard = await db.get(Dashboard, dashboard_id)
        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if dashboard.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Remove widget
        widgets = dashboard.widgets or []
        original_count = len(widgets)
        widgets = [w for w in widgets if w.get('id') != widget_id]

        if len(widgets) == original_count:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Widget {widget_id} not found in dashboard"
            )

        dashboard.widgets = widgets

        await db.commit()
        await db.refresh(dashboard)

        logger.info(f"User {current_user.id} removed widget {widget_id} from dashboard {dashboard_id}")

        # Build response with populated widgets
        populated_widgets = []
        for w in dashboard.widgets:
            populated = await populate_widget(w, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, dashboard.created_by)

        response = DashboardResponse.model_validate(dashboard)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in dashboard.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove widget from dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove widget from dashboard: {str(e)}"
        )


@router.post(
    "/{dashboard_id}/duplicate",
    response_model=DashboardResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def duplicate_dashboard(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Create a copy of a dashboard.

    Duplicates the dashboard with all widgets, layout, and configuration.
    The new dashboard is named "{original_name} (Copy)".

    **Required Permission:** `data:visualize`
    """
    try:
        # Get original dashboard
        original = await db.get(Dashboard, dashboard_id)
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dashboard {dashboard_id} not found"
            )

        # Verify organization access
        if original.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dashboard does not belong to your organization"
            )

        # Create duplicate
        duplicate = Dashboard(
            name=f"{original.name} (Copy)",
            description=original.description,
            layout=original.layout.copy() if original.layout else {},
            is_public=False,  # Duplicates are private by default
            widgets=[w.copy() for w in original.widgets] if original.widgets else [],
            organization_id=organization_id,
            created_by=current_user.id
        )

        # Generate new widget IDs for the duplicate
        if duplicate.widgets:
            for widget in duplicate.widgets:
                widget['id'] = str(uuid4())

        # Copy visualization associations
        for viz in original.visualizations:
            duplicate.visualizations.append(viz)

        db.add(duplicate)
        await db.commit()
        await db.refresh(duplicate)

        logger.info(f"User {current_user.id} duplicated dashboard {dashboard_id} to {duplicate.id}")

        # Build response with populated widgets
        populated_widgets = []
        for widget in duplicate.widgets:
            populated = await populate_widget(widget, db, organization_id)
            populated_widgets.append(populated)

        creator = await db.get(User, duplicate.created_by)

        response = DashboardResponse.model_validate(duplicate)
        response.populated_widgets = populated_widgets
        response.visualization_count = len([w for w in duplicate.widgets if w.get('type') == 'visualization'])
        response.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate dashboard: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate dashboard: {str(e)}"
        )
