"""
Insight API endpoints.

Handles AI-generated insights including generation, retrieval, natural language
queries, dataset summaries, and user feedback with proper authentication.
"""

import logging
import time
from typing import Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Dataset, Insight, InsightType, Visualization
from app.schemas.insight import (
    InsightResponse,
    InsightListResponse,
    InsightSummary,
    GenerateInsightsRequest,
    GenerateInsightsResponse,
    InsightQuestionRequest,
    InsightQuestionResponse,
)
from app.services.llm.insight_generator import InsightGeneratorService

logger = logging.getLogger(__name__)

router = APIRouter()


async def generate_insights_task(
    dataset_id: UUID,
    organization_id: UUID,
    use_llm: bool,
    save_to_db: bool,
    max_insights: int,
    db: AsyncSession
):
    """
    Background task to generate insights for a dataset.
    
    Args:
        dataset_id: Dataset to analyze
        organization_id: Organization ID for multi-tenancy
        use_llm: Whether to use LLM for generation
        save_to_db: Whether to save insights to database
        max_insights: Maximum number of insights
        db: Database session
    """
    try:
        logger.info(f"Starting insight generation for dataset {dataset_id}")
        
        insight_service = InsightGeneratorService(db)
        
        # Generate insights
        insights = await insight_service.generate_insights(
            dataset_id=dataset_id,
            use_llm=use_llm,
            save_to_db=save_to_db,
            max_insights=max_insights
        )
        
        logger.info(f"Generated {len(insights)} insights for dataset {dataset_id}")
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}", exc_info=True)


@router.post(
    "/datasets/{dataset_id}/insights/generate",
    response_model=GenerateInsightsResponse,
    dependencies=[Depends(require_permission("data:analyze"))]
)
async def generate_dataset_insights(
    dataset_id: UUID,
    background_tasks: BackgroundTasks,
    use_llm: bool = Query(True, description="Use LLM for enhanced insights"),
    save_to_db: bool = Query(True, description="Save insights to database"),
    max_insights: int = Query(10, ge=1, le=50, description="Maximum insights to generate"),
    run_async: bool = Query(False, description="Run as background task"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Generate AI insights for a dataset.
    
    Uses LLM and rule-based analysis to discover trends, anomalies,
    correlations, and recommendations. Can run synchronously or as
    a background task for large datasets.
    
    **Required Permission:** `data:analyze`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )
        
        # If async requested, run as background task
        if run_async:
            background_tasks.add_task(
                generate_insights_task,
                dataset_id=dataset_id,
                organization_id=organization_id,
                use_llm=use_llm,
                save_to_db=save_to_db,
                max_insights=max_insights,
                db=db
            )
            
            # Return task acknowledgment
            return GenerateInsightsResponse(
                dataset_id=dataset_id,
                dataset_name=dataset.name,
                insights=[],
                total_generated=0,
                generation_time_seconds=0.0,
                used_llm=use_llm
            )
        
        # Run synchronously
        start_time = time.time()
        
        insight_service = InsightGeneratorService(db)
        insights = await insight_service.generate_insights(
            dataset_id=dataset_id,
            use_llm=use_llm,
            save_to_db=save_to_db,
            max_insights=max_insights
        )
        
        generation_time = time.time() - start_time
        
        logger.info(f"User {current_user.id} generated {len(insights)} insights for dataset {dataset_id}")
        
        # Build response
        insight_responses = []
        for insight in insights:
            # Get related entities
            viz = await db.get(Visualization, insight.visualization_id) if insight.visualization_id else None
            
            response = InsightResponse.model_validate(insight)
            response.confidence_level = insight.confidence_level
            response.has_visualization = insight.has_visualization
            response.has_action = insight.has_action
            response.dataset_name = dataset.name
            response.visualization_name = viz.name if viz else None
            
            insight_responses.append(response)
        
        return GenerateInsightsResponse(
            dataset_id=dataset_id,
            dataset_name=dataset.name,
            insights=insight_responses,
            total_generated=len(insight_responses),
            generation_time_seconds=round(generation_time, 2),
            used_llm=use_llm
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate insights: {str(e)}"
        )


@router.get(
    "/datasets/{dataset_id}/insights",
    response_model=InsightListResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def list_dataset_insights(
    dataset_id: UUID,
    insight_type: Optional[InsightType] = Query(None, description="Filter by insight type"),
    min_confidence: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    sort_by: Literal["confidence", "created_at"] = Query("confidence", description="Sort field"),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    List all insights for a dataset.
    
    Supports filtering by type, minimum confidence, and sorting.
    
    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )
        
        # Build query
        query = select(Insight).where(
            Insight.dataset_id == dataset_id
        )
        
        # Apply filters
        if insight_type:
            query = query.where(Insight.insight_type == insight_type)
        
        if min_confidence is not None:
            query = query.where(Insight.confidence >= min_confidence)
        
        # Apply sorting
        if sort_by == "confidence":
            sort_column = Insight.confidence
        else:
            sort_column = Insight.created_at
        
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Count total
        count_query = select(Insight.id).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = len(total_result.all())
        
        # Apply pagination
        skip = (page - 1) * page_size
        query = query.offset(skip).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        insights = result.scalars().all()
        
        # Build response items
        items = []
        for insight in insights:
            summary = InsightSummary(
                id=insight.id,
                insight_type=insight.insight_type,
                title=insight.title,
                description=insight.description[:200] if len(insight.description) > 200 else insight.description,
                confidence=insight.confidence,
                confidence_level=insight.confidence_level,
                generated_by=insight.generated_by,
                has_visualization=insight.has_visualization,
                has_action=insight.has_action,
                created_at=insight.created_at
            )
            items.append(summary)
        
        total_pages = (total + page_size - 1) // page_size
        
        return InsightListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list insights: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list insights: {str(e)}"
        )


@router.get(
    "/insights/{insight_id}",
    response_model=InsightResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_insight(
    insight_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get insight details with supporting data.
    
    **Required Permission:** `data:view`
    """
    try:
        # Get insight
        insight = await db.get(Insight, insight_id)
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )
        
        # Verify organization access
        if insight.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insight does not belong to your organization"
            )
        
        # Get related entities
        dataset = await db.get(Dataset, insight.dataset_id)
        viz = await db.get(Visualization, insight.visualization_id) if insight.visualization_id else None
        
        # Build response
        response = InsightResponse.model_validate(insight)
        response.confidence_level = insight.confidence_level
        response.has_visualization = insight.has_visualization
        response.has_action = insight.has_action
        response.dataset_name = dataset.name if dataset else None
        response.visualization_name = viz.name if viz else None
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get insight: {str(e)}"
        )


@router.delete(
    "/insights/{insight_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("data:analyze"))]
)
async def delete_insight(
    insight_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Delete an insight.
    
    **Required Permission:** `data:analyze`
    """
    try:
        # Get insight
        insight = await db.get(Insight, insight_id)
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )
        
        # Verify organization access
        if insight.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insight does not belong to your organization"
            )
        
        # Delete insight
        await db.delete(insight)
        await db.commit()
        
        logger.info(f"User {current_user.id} deleted insight {insight_id}")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete insight: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete insight: {str(e)}"
        )


@router.post(
    "/insights/{insight_id}/feedback",
    response_model=dict,
    dependencies=[Depends(require_permission("data:view"))]
)
async def submit_insight_feedback(
    insight_id: UUID,
    helpful: bool = Query(..., description="Whether insight was helpful"),
    comment: Optional[str] = Query(None, max_length=1000, description="Optional feedback comment"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Accept user feedback on an insight.
    
    Stores feedback to improve future insights. Feedback includes
    helpful/not helpful rating and optional comments.
    
    **Required Permission:** `data:view`
    """
    try:
        # Get insight
        insight = await db.get(Insight, insight_id)
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insight {insight_id} not found"
            )
        
        # Verify organization access
        if insight.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insight does not belong to your organization"
            )
        
        # Store feedback in data_support (extend the JSONB field)
        feedback_data = {
            "user_id": str(current_user.id),
            "helpful": helpful,
            "comment": comment,
            "timestamp": time.time()
        }
        
        # Add feedback to insight's data_support
        if "feedback" not in insight.data_support:
            insight.data_support["feedback"] = []
        
        insight.data_support["feedback"].append(feedback_data)
        
        # Mark the JSONB field as modified for SQLAlchemy
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(insight, "data_support")
        
        await db.commit()
        
        logger.info(f"User {current_user.id} submitted feedback for insight {insight_id}: helpful={helpful}")
        
        return {
            "insight_id": str(insight_id),
            "feedback_recorded": True,
            "helpful": helpful,
            "total_feedback": len(insight.data_support.get("feedback", []))
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.post(
    "/datasets/{dataset_id}/ask",
    response_model=InsightQuestionResponse,
    dependencies=[Depends(require_permission("data:view"))]
)
async def ask_dataset_question(
    dataset_id: UUID,
    request: InsightQuestionRequest,
    create_insight: bool = Query(False, description="Create insight from answer"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Natural language query endpoint.
    
    Ask questions about your dataset in natural language and receive
    AI-powered answers with supporting data. Optionally create an
    insight from the answer for future reference.
    
    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )
        
        # Generate answer using LLM
        insight_service = InsightGeneratorService(db)
        answer_data = await insight_service.answer_data_question(
            dataset_id=dataset_id,
            question=request.question
        )
        
        # Get related insights if requested
        related_insights = []
        if request.include_existing_insights:
            # Query for insights with similar keywords
            query = select(Insight).where(
                Insight.dataset_id == dataset_id
            ).order_by(desc(Insight.confidence)).limit(5)
            
            result = await db.execute(query)
            insights = result.scalars().all()
            
            for insight in insights:
                summary = InsightSummary(
                    id=insight.id,
                    insight_type=insight.insight_type,
                    title=insight.title,
                    description=insight.description[:200],
                    confidence=insight.confidence,
                    confidence_level=insight.confidence_level,
                    generated_by=insight.generated_by,
                    has_visualization=insight.has_visualization,
                    has_action=insight.has_action,
                    created_at=insight.created_at
                )
                related_insights.append(summary)
        
        # Optionally create insight from answer
        if create_insight and answer_data.get("confidence", 0) > 0.5:
            new_insight = Insight(
                dataset_id=dataset_id,
                organization_id=organization_id,
                insight_type=InsightType.SUMMARY,
                generated_by=answer_data.get("generated_by", "llm"),
                title=f"Q: {request.question[:100]}",
                description=answer_data.get("answer", ""),
                confidence=answer_data.get("confidence", 0.7),
                data_support={
                    "question": request.question,
                    "answer": answer_data.get("answer", ""),
                    "context": answer_data.get("context", {})
                }
            )
            
            db.add(new_insight)
            await db.commit()
            await db.refresh(new_insight)
            
            logger.info(f"Created insight from Q&A: {new_insight.id}")
        
        logger.info(f"User {current_user.id} asked question about dataset {dataset_id}")
        
        return InsightQuestionResponse(
            question=request.question,
            answer=answer_data.get("answer", ""),
            confidence=answer_data.get("confidence", 0.7),
            related_insights=related_insights,
            suggested_visualizations=answer_data.get("suggested_visualizations")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to answer question: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to answer question: {str(e)}"
        )


@router.get(
    "/datasets/{dataset_id}/summary",
    response_model=dict,
    dependencies=[Depends(require_permission("data:view"))]
)
async def get_dataset_summary(
    dataset_id: UUID,
    regenerate: bool = Query(False, description="Force regenerate summary"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get AI-generated summary of dataset.
    
    Returns a comprehensive summary of the dataset including key
    characteristics, data quality, and notable patterns. Summaries
    are cached and regenerated only when requested or data changes.
    
    **Required Permission:** `data:view`
    """
    try:
        # Verify dataset exists and belongs to organization
        dataset = await db.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Dataset {dataset_id} not found"
            )
        
        if dataset.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Dataset does not belong to your organization"
            )
        
        # Check if summary exists and is fresh
        metadata = dataset.metadata or {}
        cached_summary = metadata.get("ai_summary")
        
        if cached_summary and not regenerate:
            logger.info(f"Returning cached summary for dataset {dataset_id}")
            return {
                "dataset_id": str(dataset_id),
                "dataset_name": dataset.name,
                "summary": cached_summary,
                "cached": True,
                "generated_at": metadata.get("ai_summary_generated_at")
            }
        
        # Generate new summary
        logger.info(f"Generating new summary for dataset {dataset_id}")
        
        insight_service = InsightGeneratorService(db)
        
        # Get dataset summary from summary service
        from app.services.visualization.summary import SummaryService
        summary_service = SummaryService(db)
        
        dataset_summary = await summary_service.generate_dataset_summary(dataset_id)
        
        # Generate AI narrative summary
        from app.services.llm.prompts import DATASET_SUMMARY_PROMPT, SYSTEM_PROMPTS
        from app.services.llm.client import get_llm_client
        
        llm_client = get_llm_client()
        
        prompt = DATASET_SUMMARY_PROMPT.format(
            dataset_name=dataset.name,
            row_count=dataset_summary.get("row_count", 0),
            column_count=dataset_summary.get("column_count", 0),
            schema=str(dataset_summary.get("columns", {})),
            column_stats=str(dataset_summary.get("statistics", {})),
            sample_data="Sample data available"
        )
        
        ai_summary = await llm_client.generate_completion(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPTS["data_analyst"],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Cache summary in dataset metadata
        if metadata is None:
            metadata = {}
        
        metadata["ai_summary"] = ai_summary
        metadata["ai_summary_generated_at"] = time.time()
        metadata["summary_stats"] = dataset_summary
        
        dataset.metadata = metadata
        
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(dataset, "metadata")
        
        await db.commit()
        
        logger.info(f"Generated and cached summary for dataset {dataset_id}")
        
        return {
            "dataset_id": str(dataset_id),
            "dataset_name": dataset.name,
            "summary": ai_summary,
            "cached": False,
            "generated_at": metadata["ai_summary_generated_at"],
            "statistics": dataset_summary
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate summary: {str(e)}"
        )
