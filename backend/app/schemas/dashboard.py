"""
Pydantic schemas for Dashboard API endpoints.

Provides request/response models for dashboards including
widget configurations, layouts, and populated visualizations.
"""

from typing import Optional, Any, Literal
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.schemas.visualization import VisualizationResponse


# Dashboard Widget Schema
class DashboardWidget(BaseModel):
    """Widget configuration for dashboard."""

    id: str = Field(..., description="Unique widget identifier")
    type: Literal["visualization", "text", "metric", "filter"] = Field(
        ...,
        description="Widget type"
    )
    visualization_id: Optional[UUID] = Field(
        None,
        description="Associated visualization ID (for type='visualization')"
    )

    # Position and size
    position: dict[str, int] = Field(
        ...,
        description="Widget position: {x: int, y: int}"
    )
    size: dict[str, int] = Field(
        ...,
        description="Widget size: {width: int, height: int}"
    )

    # Widget-specific configuration
    config: Optional[dict[str, Any]] = Field(
        default_factory=dict,
        description="Widget-specific configuration"
    )

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: dict) -> dict:
        """Validate position has required fields."""
        if "x" not in v or "y" not in v:
            raise ValueError("Position must have 'x' and 'y' coordinates")
        if not isinstance(v["x"], int) or not isinstance(v["y"], int):
            raise ValueError("Position coordinates must be integers")
        if v["x"] < 0 or v["y"] < 0:
            raise ValueError("Position coordinates must be non-negative")
        return v

    @field_validator("size")
    @classmethod
    def validate_size(cls, v: dict) -> dict:
        """Validate size has required fields."""
        if "width" not in v or "height" not in v:
            raise ValueError("Size must have 'width' and 'height'")
        if not isinstance(v["width"], int) or not isinstance(v["height"], int):
            raise ValueError("Size dimensions must be integers")
        if v["width"] <= 0 or v["height"] <= 0:
            raise ValueError("Size dimensions must be positive")
        return v

    model_config = ConfigDict(from_attributes=True)


# Dashboard Layout Schema
class DashboardLayout(BaseModel):
    """Grid layout configuration for dashboard."""

    columns: int = Field(12, ge=1, le=24, description="Number of grid columns")
    row_height: int = Field(100, ge=50, le=500, description="Height of each row in pixels")
    gap: int = Field(16, ge=0, le=50, description="Gap between widgets in pixels")
    breakpoints: Optional[dict[str, int]] = Field(
        default_factory=lambda: {
            "lg": 1200,
            "md": 996,
            "sm": 768,
            "xs": 480
        },
        description="Responsive breakpoints"
    )

    model_config = ConfigDict(from_attributes=True)


# Base Dashboard Schema
class DashboardBase(BaseModel):
    """Base schema with common dashboard fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Dashboard name")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout: DashboardLayout = Field(
        default_factory=DashboardLayout,
        description="Grid layout configuration"
    )
    is_public: bool = Field(False, description="Whether dashboard is publicly accessible")


# Create Dashboard Schema
class DashboardCreate(DashboardBase):
    """Schema for creating a new dashboard."""

    widgets: list[DashboardWidget] = Field(
        default_factory=list,
        description="Initial widgets for the dashboard"
    )
    visualization_ids: Optional[list[UUID]] = Field(
        default_factory=list,
        description="Visualizations to add to dashboard"
    )


# Update Dashboard Schema
class DashboardUpdate(BaseModel):
    """Schema for updating a dashboard."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    layout: Optional[DashboardLayout] = None
    widgets: Optional[list[DashboardWidget]] = None
    is_public: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


# Database Representation Schema
class DashboardInDB(DashboardBase):
    """Full dashboard representation from database."""

    id: UUID
    organization_id: UUID
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    widgets: list[DashboardWidget]

    model_config = ConfigDict(from_attributes=True)


# Widget with Populated Data
class PopulatedWidget(DashboardWidget):
    """Widget with populated visualization data."""

    visualization: Optional[VisualizationResponse] = Field(
        None,
        description="Populated visualization (for type='visualization')"
    )

    model_config = ConfigDict(from_attributes=True)


# API Response Schema with Populated Widgets
class DashboardResponse(DashboardInDB):
    """API response including populated widgets."""

    populated_widgets: list[PopulatedWidget] = Field(
        ...,
        description="Widgets with populated visualization data"
    )
    visualization_count: int = Field(
        ...,
        description="Total number of visualizations on dashboard"
    )
    creator_name: Optional[str] = Field(None, description="Name of creator")

    model_config = ConfigDict(from_attributes=True)


# Add Widget Request
class AddWidgetRequest(BaseModel):
    """Request to add a widget to dashboard."""

    widget: DashboardWidget = Field(..., description="Widget to add")

    model_config = ConfigDict(from_attributes=True)


# Update Widget Request
class UpdateWidgetRequest(BaseModel):
    """Request to update a widget."""

    widget_id: str = Field(..., description="Widget ID to update")
    position: Optional[dict[str, int]] = None
    size: Optional[dict[str, int]] = None
    config: Optional[dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


# Remove Widget Request
class RemoveWidgetRequest(BaseModel):
    """Request to remove a widget from dashboard."""

    widget_id: str = Field(..., description="Widget ID to remove")

    model_config = ConfigDict(from_attributes=True)


# Add Visualization Request
class AddVisualizationRequest(BaseModel):
    """Request to add a visualization to dashboard."""

    visualization_id: UUID = Field(..., description="Visualization ID to add")
    position: Optional[dict[str, int]] = Field(
        None,
        description="Widget position (auto-assigned if not provided)"
    )
    size: Optional[dict[str, int]] = Field(
        None,
        description="Widget size (defaults if not provided)"
    )

    model_config = ConfigDict(from_attributes=True)


# Dashboard List Response
class DashboardListResponse(BaseModel):
    """Paginated list of dashboards."""

    items: list[DashboardResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    model_config = ConfigDict(from_attributes=True)


# Dashboard Export Schema
class DashboardExport(BaseModel):
    """Schema for exporting dashboard configuration."""

    dashboard_id: UUID
    name: str
    description: Optional[str]
    layout: DashboardLayout
    widgets: list[DashboardWidget]
    exported_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)


# Dashboard Template Schema
class DashboardTemplate(BaseModel):
    """Template for creating dashboards from predefined layouts."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    category: str = Field(..., description="Template category (e.g., 'analytics', 'executive')")
    layout: DashboardLayout
    widget_templates: list[dict[str, Any]] = Field(
        ...,
        description="Widget templates (type, position, size)"
    )
    preview_image: Optional[str] = Field(None, description="Preview image URL")

    model_config = ConfigDict(from_attributes=True)


# Dashboard Share Settings
class DashboardShareSettings(BaseModel):
    """Settings for sharing a dashboard."""

    is_public: bool = Field(..., description="Whether dashboard is publicly accessible")
    shared_with: list[UUID] = Field(
        default_factory=list,
        description="User IDs with access"
    )
    allow_export: bool = Field(True, description="Whether users can export data")
    allow_filtering: bool = Field(True, description="Whether users can apply filters")

    model_config = ConfigDict(from_attributes=True)
