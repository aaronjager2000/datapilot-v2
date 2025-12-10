"""
Visualization model - represents chart and table visualizations for datasets.

Visualizations define how dataset data should be displayed visually,
including chart types, axes, grouping, aggregations, and styling.
"""

from enum import Enum as PyEnum
from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.dataset import Dataset
    from app.models.dashboard import Dashboard
    from app.models.insight import Insight


class ChartType(str, PyEnum):
    """Supported chart types for visualizations."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    TABLE = "table"


class Visualization(BaseModel):
    """
    Visualization model - represents visual representations of dataset data.

    Visualizations are created by users to display dataset data in various
    chart formats with configurable axes, grouping, aggregation, and styling.
    """

    __tablename__ = "visualizations"

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Name of the visualization"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of what the visualization shows"
    )

    # Dataset Reference
    dataset_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("datasets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Dataset this visualization is based on"
    )

    # Chart Type
    chart_type: Mapped[ChartType] = mapped_column(
        Enum(ChartType, name="chart_type_enum"),
        nullable=False,
        index=True,
        comment="Type of chart to display (line, bar, pie, scatter, heatmap, table)"
    )

    # Configuration
    config: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Chart configuration including axes, grouping, aggregation, filters, and styling"
    )
    """
    Config structure:
    {
        "x_axis": "column_name",          # Column for x-axis
        "y_axis": ["col1", "col2"],       # Column(s) for y-axis (can be single or array)
        "grouping": "category_column",    # Optional: Column to group data by
        "aggregation": "sum",             # Aggregation function: sum, avg, count, min, max
        "filters": [                      # Optional: Array of filter conditions
            {
                "column": "status",
                "operator": "eq",         # eq, ne, gt, lt, gte, lte, in, contains
                "value": "active"
            }
        ],
        "colors": {                       # Color scheme configuration
            "scheme": "blue",             # Named scheme or custom colors
            "custom": ["#FF0000", ...]    # Optional custom color array
        },
        "options": {                      # Chart-specific options
            "stacked": false,             # For bar/area charts
            "smooth": true,               # For line charts
            "showLegend": true,
            "showGrid": true,
            "title": "Chart Title",
            "xLabel": "X Axis Label",
            "yLabel": "Y Axis Label"
        }
    }
    """

    # Creator
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this visualization"
    )

    # Relationships
    dataset: Mapped["Dataset"] = relationship(
        "Dataset",
        foreign_keys=[dataset_id],
        back_populates="visualizations"
    )

    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="visualizations"
    )

    dashboards: Mapped[list["Dashboard"]] = relationship(
        "Dashboard",
        secondary="dashboard_visualizations",
        back_populates="visualizations",
        lazy="selectin"
    )

    insights: Mapped[list["Insight"]] = relationship(
        "Insight",
        back_populates="visualization",
        foreign_keys="Insight.visualization_id"
    )

    def __repr__(self) -> str:
        return f"<Visualization(id={self.id}, name='{self.name}', chart_type={self.chart_type.value}, dataset_id={self.dataset_id})>"

    @property
    def x_axis(self) -> Optional[str]:
        """Get x-axis column name from config."""
        return self.config.get("x_axis")

    @property
    def y_axis(self) -> Optional[list[str] | str]:
        """Get y-axis column name(s) from config."""
        return self.config.get("y_axis")

    @property
    def grouping(self) -> Optional[str]:
        """Get grouping column name from config."""
        return self.config.get("grouping")

    @property
    def aggregation(self) -> Optional[str]:
        """Get aggregation function from config."""
        return self.config.get("aggregation")

    @property
    def filters(self) -> list[dict]:
        """Get filter conditions from config."""
        return self.config.get("filters", [])

    @property
    def has_filters(self) -> bool:
        """Check if visualization has any filters applied."""
        return len(self.filters) > 0

    @property
    def color_scheme(self) -> Optional[str]:
        """Get color scheme from config."""
        colors = self.config.get("colors", {})
        return colors.get("scheme")

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """
        Validate visualization configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required fields based on chart type
        if self.chart_type in [ChartType.LINE, ChartType.BAR, ChartType.SCATTER]:
            if not self.x_axis:
                return False, "x_axis is required for this chart type"
            if not self.y_axis:
                return False, "y_axis is required for this chart type"

        elif self.chart_type == ChartType.PIE:
            if not self.config.get("values"):
                return False, "values column is required for pie charts"
            if not self.config.get("labels"):
                return False, "labels column is required for pie charts"

        elif self.chart_type == ChartType.HEATMAP:
            if not self.x_axis or not self.y_axis:
                return False, "Both x_axis and y_axis are required for heatmap"

        # Validate aggregation function if present
        valid_aggregations = ["sum", "avg", "count", "min", "max"]
        if self.aggregation and self.aggregation not in valid_aggregations:
            return False, f"Invalid aggregation function. Must be one of: {', '.join(valid_aggregations)}"

        # Validate filter operators if present
        valid_operators = ["eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"]
        for filter_condition in self.filters:
            operator = filter_condition.get("operator")
            if operator and operator not in valid_operators:
                return False, f"Invalid filter operator '{operator}'. Must be one of: {', '.join(valid_operators)}"

        return True, None
