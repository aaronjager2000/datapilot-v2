"""
Visualization API endpoints.

Handles visualization creation, retrieval, updates, deletion, chart suggestions,
and data aggregation with proper authentication and permissions.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Visualization, Dataset, ChartType
from app.schemas.visualization import (
    VisualizationCreate,
    VisualizationUpdate,
    VisualizationResponse,
    VisualizationListResponse,
    ChartSuggestionRequest,
    ChartSuggestionsResponse,
    ChartSuggestion,
)
from app.services.visualization.aggregator import AggregationService
from app.services.visualization.chart_generator import ChartGenerator
from app.services.llm.chart_suggester import ChartSuggesterService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=VisualizationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def create_visualization(
    visualization_data: VisualizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Create a new visualization.

    Accepts dataset_id, chart_type, and config. Generates chart data using
    the aggregation service and returns the visualization with chart data.

    **Required Permission:** `data:visualize`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, visualization_data.dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {visualization_data.dataset_id} not found"
            )

        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )

        # Create visualization record
        visualization = Visualization(
            name=visualization_data.name,
            description=visualization_data.description,
            chart_type=visualization_data.chart_type,
            dataset_id=visualization_data.dataset_id,
            config=visualization_data.config.model_dump(),
            organization_id=organization_id,
            created_by=current_user.id
        )

        db.add(visualization)
        await db.commit()
        await db.refresh(visualization)

        # Generate chart data
        chart_generator = ChartGenerator()
        aggregation_service = AggregationService(db)

        # Aggregate data based on config
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

        # Generate chart configuration
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

        logger.info(f"User {current_user.id} created visualization {visualization.id}")

        # Build response
        response_data = VisualizationResponse.model_validate(visualization)
        response_data.chart_data = chart_config
        response_data.dataset_name = dataset.name
        response_data.creator_name = f"{current_user.first_name} {current_user.last_name}".strip()

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create visualization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create visualization: {str(e)}"
        )


@router.get(
    "",
    response_model=VisualizationListResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def list_visualizations(
    dataset_id: Optional[UUID] = Query(None, description="Filter by dataset ID"),
    chart_type: Optional[ChartType] = Query(None, description="Filter by chart type"),
    created_by: Optional[UUID] = Query(None, description="Filter by creator user ID"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    List all visualizations for the organization.

    Supports filtering by dataset, chart_type, creator, and search.
    Results are paginated.

    **Required Permission:** `data:view`
    """
    try:
        # Build query
        query = select(Visualization).where(
            Visualization.organization_id == organization_id
        )

        # Apply filters
        if dataset_id:
            query = query.where(Visualization.dataset_id == dataset_id)

        if chart_type:
            query = query.where(Visualization.chart_type == chart_type)

        if created_by:
            query = query.where(Visualization.created_by == created_by)

        if search:
            search_filter = f"%{search}%"
            query = query.where(
                (Visualization.name.ilike(search_filter)) |
                (Visualization.description.ilike(search_filter))
            )

        # Count total
        count_query = select(Visualization.id).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.all())

        # Apply pagination
        skip = (page - 1) * page_size
        query = query.order_by(Visualization.created_at.desc()).offset(skip).limit(page_size)

        # Execute query
        result = await db.execute(query)
        visualizations = result.scalars().all()

        # Build response items with populated data
        items = []
        for viz in visualizations:
            # Get related entities
            dataset = await db.get(Dataset, viz.dataset_id)
            creator = await db.get(User, viz.created_by)

            viz_response = VisualizationResponse.model_validate(viz)
            viz_response.dataset_name = dataset.name if dataset else None
            viz_response.creator_name = creator.full_name if creator else None

            items.append(viz_response)

        total_pages = (total + page_size - 1) // page_size

        return VisualizationListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    except Exception as e:
        logger.error(f"Failed to list visualizations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list visualizations: {str(e)}"
        )


@router.get(
    "/{viz_id}",
    response_model=VisualizationResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_visualization(
    viz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get a visualization with current chart data.

    Re-aggregates data with latest records to ensure freshness.

    **Required Permission:** `data:view`
    """
    try:
        # Get visualization
        visualization = await db.get(Visualization, viz_id)
        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        # Verify organization access
        if visualization.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visualization does not belong to your organization"
            )

        # Get dataset
        dataset = await db.get(Dataset, visualization.dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {visualization.dataset_id} not found"
            )

        # Get creator
        creator = await db.get(User, visualization.created_by)

        # Regenerate chart data with latest records
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

        # Build response
        response_data = VisualizationResponse.model_validate(visualization)
        response_data.chart_data = chart_config
        response_data.dataset_name = dataset.name
        response_data.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get visualization: {str(e)}"
        )


@router.put(
    "/{viz_id}",
    response_model=VisualizationResponse,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def update_visualization(
    viz_id: UUID,
    update_data: VisualizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Update a visualization configuration.

    Regenerates chart data with new configuration.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get visualization
        visualization = await db.get(Visualization, viz_id)
        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        # Verify organization access
        if visualization.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visualization does not belong to your organization"
            )

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)

        if 'name' in update_dict:
            visualization.name = update_dict['name']

        if 'description' in update_dict:
            visualization.description = update_dict['description']

        if 'chart_type' in update_dict:
            visualization.chart_type = update_dict['chart_type']

        if 'config' in update_dict:
            # Merge with existing config
            existing_config = visualization.config or {}
            new_config = update_dict['config']
            existing_config.update(new_config.model_dump() if hasattr(new_config, 'model_dump') else new_config)
            visualization.config = existing_config

        await db.commit()
        await db.refresh(visualization)

        # Get dataset
        dataset = await db.get(Dataset, visualization.dataset_id)
        creator = await db.get(User, visualization.created_by)

        # Regenerate chart data
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

        logger.info(f"User {current_user.id} updated visualization {viz_id}")

        # Build response
        response_data = VisualizationResponse.model_validate(visualization)
        response_data.chart_data = chart_config
        response_data.dataset_name = dataset.name if dataset else None
        response_data.creator_name = f"{creator.first_name} {creator.last_name}".strip() if creator else None

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update visualization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update visualization: {str(e)}"
        )


@router.delete(
    "/{viz_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("data:visualize"))]
)
async def delete_visualization(
    viz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Delete a visualization.

    **Required Permission:** `data:visualize`
    """
    try:
        # Get visualization
        visualization = await db.get(Visualization, viz_id)
        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        # Verify organization access
        if visualization.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visualization does not belong to your organization"
            )

        # Delete visualization
        await db.delete(visualization)
        await db.commit()

        logger.info(f"User {current_user.id} deleted visualization {viz_id}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete visualization: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete visualization: {str(e)}"
        )


@router.post(
    "/suggest",
    response_model=ChartSuggestionsResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def suggest_visualizations(
    request: ChartSuggestionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get chart suggestions for a dataset.

    Accepts dataset_id and optional question. Returns suggested visualizations
    using the chart suggester service with rule-based and optional AI analysis.

    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, request.dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {request.dataset_id} not found"
            )

        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )

        # Get chart suggestions
        chart_suggester = ChartSuggesterService(db)

        if request.question:
            # Question-based suggestion
            suggestion_data = await chart_suggester.suggest_chart_for_question(
                dataset_id=request.dataset_id,
                question=request.question
            )

            # Convert to ChartSuggestion schema
            suggestion = ChartSuggestion(
                chart_type=ChartType(suggestion_data['chart_type']),
                title=f"{suggestion_data.get('y_axis', 'Data')} by {suggestion_data.get('x_axis', 'Category')}",
                config={
                    'x_axis': suggestion_data.get('x_axis'),
                    'y_axis': suggestion_data.get('y_axis'),
                    'grouping': suggestion_data.get('grouping'),
                    'aggregation': suggestion_data.get('aggregation', 'sum')
                },
                reasoning=suggestion_data.get('reasoning', ''),
                confidence=suggestion_data.get('confidence', 0.7),
                alternative_charts=[
                    ChartType(ct) for ct in suggestion_data.get('alternative_charts', [])
                    if ct in [e.value for e in ChartType]
                ]
            )
            suggestions = [suggestion]
        else:
            # General dataset suggestions
            suggestion_list = await chart_suggester.suggest_visualizations(
                dataset_id=request.dataset_id,
                use_ai=request.use_ai,
                max_suggestions=request.max_suggestions
            )

            # Convert to ChartSuggestion schemas
            suggestions = []
            for s in suggestion_list:
                try:
                    chart_type_str = s.get('chart_type', 'bar')
                    # Validate chart type
                    if chart_type_str not in [e.value for e in ChartType]:
                        chart_type_str = 'bar'  # Default fallback

                    suggestion = ChartSuggestion(
                        chart_type=ChartType(chart_type_str),
                        title=s.get('title', 'Suggested Chart'),
                        config={
                            'x_axis': s.get('x_axis'),
                            'y_axis': s.get('y_axis'),
                            'grouping': s.get('grouping'),
                            'aggregation': s.get('aggregation', 'sum')
                        },
                        reasoning=s.get('reasoning', ''),
                        confidence=s.get('confidence', 0.7),
                        priority=s.get('priority')
                    )
                    suggestions.append(suggestion)
                except Exception as e:
                    logger.warning(f"Skipping invalid suggestion: {e}")
                    continue

        logger.info(f"Generated {len(suggestions)} chart suggestions for dataset {request.dataset_id}")

        return ChartSuggestionsResponse(
            dataset_id=request.dataset_id,
            dataset_name=dataset.name,
            suggestions=suggestions,
            total_count=len(suggestions)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to suggest visualizations: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suggest visualizations: {str(e)}"
        )


@router.get(
    "/{viz_id}/data",
    response_model=dict,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_visualization_data(
    viz_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get aggregated data for a chart (without full visualization object).

    Useful for real-time updates and refreshing chart data without
    retrieving the entire visualization configuration.

    **Required Permission:** `data:view`
    """
    try:
        # Get visualization
        visualization = await db.get(Visualization, viz_id)
        if not visualization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Visualization {viz_id} not found"
            )

        # Verify organization access
        if visualization.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Visualization does not belong to your organization"
            )

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

        return {
            'visualization_id': str(viz_id),
            'chart_type': visualization.chart_type.value,
            'chart_data': chart_config,
            'generated_at': visualization.updated_at.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get visualization data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get visualization data: {str(e)}"
        )
