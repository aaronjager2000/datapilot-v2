"""
Pydantic schemas for Insight API endpoints.

Provides request/response models for AI-generated insights including
trends, anomalies, correlations, summaries, and recommendations.
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models import InsightType, InsightGenerator


# Base Insight Schema
class InsightBase(BaseModel):
    """Base schema with common insight fields."""

    insight_type: InsightType = Field(..., description="Type of insight")
    title: str = Field(..., min_length=1, max_length=500, description="Insight title")
    description: str = Field(..., min_length=1, description="Detailed insight description")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    generated_by: InsightGenerator = Field(..., description="Generation method (LLM or rule-based)")
    data_support: dict[str, Any] = Field(
        default_factory=dict,
        description="Supporting data, statistics, and evidence"
    )
    suggested_action: Optional[str] = Field(
        None,
        description="Actionable recommendation based on insight"
    )


# Create Insight Schema
class InsightCreate(InsightBase):
    """Schema for creating a new insight."""

    dataset_id: UUID = Field(..., description="Dataset this insight is about")
    visualization_id: Optional[UUID] = Field(
        None,
        description="Optional visualization illustrating this insight"
    )


# Update Insight Schema
class InsightUpdate(BaseModel):
    """Schema for updating an insight."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    data_support: Optional[dict[str, Any]] = None
    suggested_action: Optional[str] = None
    visualization_id: Optional[UUID] = None

    model_config = ConfigDict(from_attributes=True)


# Database Representation Schema
class InsightInDB(InsightBase):
    """Full insight representation from database."""

    id: UUID
    dataset_id: UUID
    organization_id: UUID
    visualization_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Insight Summary (for lists)
class InsightSummary(BaseModel):
    """Lightweight insight summary for list views."""

    id: UUID
    insight_type: InsightType
    title: str
    description: str = Field(..., description="Truncated to 200 chars in list views")
    confidence: float
    confidence_level: str = Field(..., description="Human-readable: high, medium, low")
    generated_by: InsightGenerator
    has_visualization: bool
    has_action: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# API Response Schema
class InsightResponse(InsightInDB):
    """API response including computed properties."""

    confidence_level: str = Field(..., description="Human-readable confidence level")
    has_visualization: bool = Field(..., description="Whether insight has visualization")
    has_action: bool = Field(..., description="Whether insight has suggested action")
    dataset_name: Optional[str] = Field(None, description="Name of associated dataset")
    visualization_name: Optional[str] = Field(None, description="Name of visualization if present")

    model_config = ConfigDict(from_attributes=True)


# Insight List Response
class InsightListResponse(BaseModel):
    """Paginated list of insights."""

    items: list[InsightSummary]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# Generate Insights Request
class GenerateInsightsRequest(BaseModel):
    """Request to generate insights for a dataset."""

    dataset_id: UUID = Field(..., description="Dataset to analyze")
    use_llm: bool = Field(
        True,
        description="Whether to use LLM for insights (vs rule-based only)"
    )
    save_to_db: bool = Field(
        True,
        description="Whether to save generated insights to database"
    )
    max_insights: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum number of insights to generate"
    )
    focus_areas: Optional[list[InsightType]] = Field(
        None,
        description="Specific insight types to focus on"
    )

    model_config = ConfigDict(from_attributes=True)


# Generate Insights Response
class GenerateInsightsResponse(BaseModel):
    """Response from insight generation."""

    dataset_id: UUID
    dataset_name: str
    insights: list[InsightResponse]
    total_generated: int
    generation_time_seconds: float
    used_llm: bool

    model_config = ConfigDict(from_attributes=True)


# Insight by Type Response
class InsightsByTypeResponse(BaseModel):
    """Insights grouped by type."""

    dataset_id: UUID
    dataset_name: str
    trends: list[InsightSummary]
    anomalies: list[InsightSummary]
    correlations: list[InsightSummary]
    summaries: list[InsightSummary]
    recommendations: list[InsightSummary]
    total_count: int

    model_config = ConfigDict(from_attributes=True)


# Data Support Schemas (for specific insight types)

class TrendDataSupport(BaseModel):
    """Data support structure for trend insights."""

    column: str = Field(..., description="Column showing trend")
    direction: str = Field(..., description="Trend direction: increasing, decreasing, stable")
    rate_of_change: Optional[float] = Field(None, description="Rate of change value")
    time_period: Optional[str] = Field(None, description="Time period analyzed")
    sample_values: Optional[list[Any]] = Field(None, description="Sample data points")

    model_config = ConfigDict(from_attributes=True)


class AnomalyDataSupport(BaseModel):
    """Data support structure for anomaly insights."""

    column: str = Field(..., description="Column containing anomalies")
    anomalies: list[dict[str, Any]] = Field(..., description="List of detected anomalies")
    method: str = Field(..., description="Detection method: iqr, z_score, modified_z")
    threshold: Optional[float] = Field(None, description="Threshold used for detection")

    model_config = ConfigDict(from_attributes=True)


class CorrelationDataSupport(BaseModel):
    """Data support structure for correlation insights."""

    column1: str = Field(..., description="First column")
    column2: str = Field(..., description="Second column")
    coefficient: float = Field(..., ge=-1.0, le=1.0, description="Correlation coefficient")
    p_value: Optional[float] = Field(None, description="Statistical significance")
    sample_size: Optional[int] = Field(None, description="Number of data points")
    strength: Optional[str] = Field(None, description="Correlation strength: weak, moderate, strong")

    model_config = ConfigDict(from_attributes=True)


class SummaryDataSupport(BaseModel):
    """Data support structure for summary insights."""

    columns: list[str] = Field(..., description="Columns summarized")
    statistics: dict[str, dict[str, float]] = Field(
        ...,
        description="Statistics per column (mean, median, std, etc.)"
    )
    row_count: Optional[int] = Field(None, description="Number of rows analyzed")

    model_config = ConfigDict(from_attributes=True)


class RecommendationDataSupport(BaseModel):
    """Data support structure for recommendation insights."""

    based_on: str = Field(..., description="What this recommendation is based on")
    impact_estimate: Optional[str] = Field(None, description="Expected impact: high, medium, low")
    effort_estimate: Optional[str] = Field(None, description="Required effort: high, medium, low")
    expected_outcome: Optional[str] = Field(None, description="Expected outcome description")
    priority: Optional[str] = Field(None, description="Priority level: high, medium, low")

    model_config = ConfigDict(from_attributes=True)


# Insight Question Request
class InsightQuestionRequest(BaseModel):
    """Request to ask a question about insights."""

    dataset_id: UUID = Field(..., description="Dataset to query")
    question: str = Field(..., min_length=1, max_length=1000, description="Question about the data")
    include_existing_insights: bool = Field(
        True,
        description="Whether to include existing insights in context"
    )

    model_config = ConfigDict(from_attributes=True)


# Insight Question Response
class InsightQuestionResponse(BaseModel):
    """Response to insight question."""

    question: str
    answer: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    related_insights: list[InsightSummary] = Field(
        default_factory=list,
        description="Existing insights related to the question"
    )
    suggested_visualizations: Optional[list[dict[str, Any]]] = Field(
        None,
        description="Suggested visualizations for this question"
    )

    model_config = ConfigDict(from_attributes=True)


# Insight Explanation Request
class ExplainInsightRequest(BaseModel):
    """Request to get detailed explanation of an insight."""

    insight_id: UUID = Field(..., description="Insight to explain")
    detail_level: str = Field(
        "medium",
        description="Explanation detail: basic, medium, detailed"
    )

    @field_validator("detail_level")
    @classmethod
    def validate_detail_level(cls, v: str) -> str:
        """Validate detail level."""
        valid_levels = {"basic", "medium", "detailed"}
        if v not in valid_levels:
            raise ValueError(f"Invalid detail level. Must be one of: {valid_levels}")
        return v

    model_config = ConfigDict(from_attributes=True)


# Insight Explanation Response
class ExplainInsightResponse(BaseModel):
    """Detailed explanation of an insight."""

    insight_id: UUID
    insight_type: InsightType
    title: str
    explanation: str = Field(..., description="Detailed explanation of the insight")
    methodology: str = Field(..., description="How the insight was generated")
    supporting_evidence: dict[str, Any] = Field(..., description="Evidence and data points")
    statistical_significance: Optional[str] = Field(None, description="Statistical significance notes")
    limitations: Optional[list[str]] = Field(None, description="Limitations or caveats")
    related_insights: list[InsightSummary] = Field(
        default_factory=list,
        description="Related insights"
    )

    model_config = ConfigDict(from_attributes=True)
