"""
Pydantic schemas for Visualization API endpoints.

Provides request/response models for chart visualizations including
configurations, suggestions, and chart data.
"""

from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.models import ChartType


# Chart Configuration Schema
class ChartConfig(BaseModel):
    """Chart configuration details."""

    # Axes configuration
    x_axis: Optional[str] = Field(None, description="Column name for X-axis")
    y_axis: Optional[str] = Field(None, description="Column name for Y-axis")

    # Data aggregation
    grouping: Optional[str] = Field(None, description="Column to group by")
    aggregation: Optional[str] = Field("sum", description="Aggregation function: sum, avg, count, min, max")

    # Filters
    filters: Optional[dict[str, Any]] = Field(default_factory=dict, description="Data filters to apply")

    # Visual styling
    colors: Optional[list[str]] = Field(None, description="Custom color palette")
    theme: Optional[str] = Field("light", description="Chart theme: light or dark")

    # Chart-specific options
    options: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Chart-specific options (e.g., stacked, smooth, show_legend)"
    )

    @field_validator("aggregation")
    @classmethod
    def validate_aggregation(cls, v: str) -> str:
        """Validate aggregation function."""
        valid_aggregations = {"sum", "avg", "count", "min", "max", "median"}
        if v not in valid_aggregations:
            raise ValueError(f"Invalid aggregation. Must be one of: {valid_aggregations}")
        return v

    model_config = ConfigDict(from_attributes=True)


# Base Visualization Schema
class VisualizationBase(BaseModel):
    """Base schema with common visualization fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Visualization name")
    description: Optional[str] = Field(None, description="Visualization description")
    chart_type: ChartType = Field(..., description="Type of chart")
    dataset_id: UUID = Field(..., description="Associated dataset ID")
    config: ChartConfig = Field(..., description="Chart configuration")


# Create Visualization Schema
class VisualizationCreate(VisualizationBase):
    """Schema for creating a new visualization."""
    pass


# Update Visualization Schema
class VisualizationUpdate(BaseModel):
    """Schema for updating a visualization."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    chart_type: Optional[ChartType] = None
    config: Optional[ChartConfig] = None

    model_config = ConfigDict(from_attributes=True)


# Database Representation Schema
class VisualizationInDB(VisualizationBase):
    """Full visualization representation from database."""

    id: UUID
    organization_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# API Response Schema with Chart Data
class VisualizationResponse(VisualizationInDB):
    """API response including chart data."""

    chart_data: Optional[dict[str, Any]] = Field(
        None,
        description="Processed chart data ready for rendering"
    )
    dataset_name: Optional[str] = Field(None, description="Name of associated dataset")
    creator_name: Optional[str] = Field(None, description="Name of creator")

    model_config = ConfigDict(from_attributes=True)


# Chart Suggestion Schema
class ChartSuggestion(BaseModel):
    """Suggested chart configuration with reasoning."""

    chart_type: ChartType = Field(..., description="Recommended chart type")
    title: str = Field(..., description="Suggested chart title")
    config: ChartConfig = Field(..., description="Recommended configuration")
    reasoning: str = Field(..., description="Explanation of why this chart is recommended")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    priority: Optional[int] = Field(None, description="Suggestion priority rank")
    alternative_charts: Optional[list[ChartType]] = Field(
        default_factory=list,
        description="Alternative chart types to consider"
    )

    model_config = ConfigDict(from_attributes=True)


# Chart Suggestion Request
class ChartSuggestionRequest(BaseModel):
    """Request for chart suggestions."""

    dataset_id: UUID = Field(..., description="Dataset to analyze")
    question: Optional[str] = Field(
        None,
        description="User's question or visualization goal"
    )
    use_ai: bool = Field(
        False,
        description="Whether to use AI for enhanced suggestions"
    )
    max_suggestions: int = Field(
        5,
        ge=1,
        le=10,
        description="Maximum number of suggestions to return"
    )

    model_config = ConfigDict(from_attributes=True)


# Chart Suggestions Response
class ChartSuggestionsResponse(BaseModel):
    """Response containing multiple chart suggestions."""

    dataset_id: UUID
    dataset_name: str
    suggestions: list[ChartSuggestion]
    total_count: int = Field(..., description="Total number of suggestions")

    model_config = ConfigDict(from_attributes=True)


# Visualization List Response
class VisualizationListResponse(BaseModel):
    """Paginated list of visualizations."""

    items: list[VisualizationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# Chart Data Export Schema
class ChartDataExport(BaseModel):
    """Schema for exporting chart data."""

    visualization_id: UUID
    name: str
    chart_type: ChartType
    data: dict[str, Any] = Field(..., description="Chart data")
    config: ChartConfig
    exported_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)
