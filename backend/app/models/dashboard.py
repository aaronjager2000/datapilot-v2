"""
Dashboard model - represents customizable dashboards with widget layouts.

Dashboards are containers for visualizations and other widgets arranged in
a grid layout. They can be private or shared within an organization.
"""

from typing import Optional, TYPE_CHECKING
from datetime import datetime

from sqlalchemy import String, Text, Boolean, ForeignKey, Table, Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.visualization import Visualization


# Association table for many-to-many relationship between dashboards and visualizations
dashboard_visualizations = Table(
    'dashboard_visualizations',
    Base.metadata,
    Column(
        'dashboard_id',
        UUID(as_uuid=True),
        ForeignKey('dashboards.id', ondelete='CASCADE'),
        primary_key=True,
        comment="Dashboard ID"
    ),
    Column(
        'visualization_id',
        UUID(as_uuid=True),
        ForeignKey('visualizations.id', ondelete='CASCADE'),
        primary_key=True,
        comment="Visualization ID"
    ),
    Column(
        'added_at',
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="When the visualization was added to the dashboard"
    ),
    comment="Association table linking dashboards to their visualizations"
)


class Dashboard(BaseModel):
    """
    Dashboard model - represents customizable visualization dashboards.

    Dashboards contain multiple widgets (visualizations, stat cards, tables)
    arranged in a grid layout. They can be private or shared across the organization.
    """

    __tablename__ = "dashboards"

    # Basic Information
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Dashboard name"
    )

    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Optional description of the dashboard's purpose"
    )

    # Layout Configuration
    layout: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Grid layout configuration for dashboard widgets"
    )
    """
    Layout structure:
    {
        "grid": {
            "columns": 12,           # Grid columns (e.g., 12-column grid)
            "rowHeight": 100,        # Height of each row in pixels
            "gap": 16                # Gap between widgets in pixels
        },
        "breakpoints": {             # Responsive breakpoints
            "lg": 1200,
            "md": 996,
            "sm": 768,
            "xs": 480
        }
    }
    """

    # Widgets Configuration
    widgets: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        comment="Array of widgets with their configurations"
    )
    """
    Widgets structure:
    [
        {
            "id": "widget_1",                    # Unique widget ID
            "type": "chart",                     # Widget type: chart, stat_card, table
            "visualization_id": "uuid",          # Reference to visualization (if type is chart)
            "position": {
                "x": 0,                          # X position in grid
                "y": 0,                          # Y position in grid
                "w": 6,                          # Width in grid columns
                "h": 4                           # Height in grid rows
            },
            "config": {                          # Widget-specific configuration
                "title": "Widget Title",
                "showHeader": true,
                "refreshInterval": 300000        # Auto-refresh interval in ms
            }
        },
        {
            "id": "widget_2",
            "type": "stat_card",
            "dataset_id": "uuid",                # For stat cards
            "metric": {
                "column": "revenue",
                "aggregation": "sum",
                "format": "currency"
            },
            "position": {"x": 6, "y": 0, "w": 3, "h": 2},
            "config": {
                "title": "Total Revenue",
                "icon": "dollar",
                "color": "green"
            }
        }
    ]
    """

    # Sharing Settings
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Whether dashboard is shared with all organization members"
    )

    # Creator
    created_by: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User who created this dashboard"
    )

    # Relationships
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[created_by],
        back_populates="dashboards"
    )

    visualizations: Mapped[list["Visualization"]] = relationship(
        "Visualization",
        secondary=dashboard_visualizations,
        back_populates="dashboards",
        lazy="selectin"  # Eager load visualizations when querying dashboards
    )

    def __repr__(self) -> str:
        return f"<Dashboard(id={self.id}, name='{self.name}', widgets={len(self.widgets)}, org_id={self.organization_id})>"

    @property
    def widget_count(self) -> int:
        """Get the number of widgets in this dashboard."""
        return len(self.widgets)

    @property
    def chart_widgets(self) -> list[dict]:
        """Get only chart widgets from the dashboard."""
        return [w for w in self.widgets if w.get("type") == "chart"]

    @property
    def stat_card_widgets(self) -> list[dict]:
        """Get only stat card widgets from the dashboard."""
        return [w for w in self.widgets if w.get("type") == "stat_card"]

    @property
    def table_widgets(self) -> list[dict]:
        """Get only table widgets from the dashboard."""
        return [w for w in self.widgets if w.get("type") == "table"]

    @property
    def grid_columns(self) -> int:
        """Get grid column count from layout."""
        return self.layout.get("grid", {}).get("columns", 12)

    @property
    def visualization_ids(self) -> list[str]:
        """Get all visualization IDs used in chart widgets."""
        return [
            w.get("visualization_id")
            for w in self.widgets
            if w.get("type") == "chart" and w.get("visualization_id")
        ]

    def get_widget_by_id(self, widget_id: str) -> Optional[dict]:
        """
        Get a widget by its ID.

        Args:
            widget_id: The widget ID to search for

        Returns:
            Widget dict if found, None otherwise
        """
        for widget in self.widgets:
            if widget.get("id") == widget_id:
                return widget
        return None

    def add_widget(self, widget: dict) -> bool:
        """
        Add a widget to the dashboard.

        Args:
            widget: Widget configuration dict

        Returns:
            True if added successfully, False if widget ID already exists
        """
        if not widget.get("id"):
            return False

        # Check if widget ID already exists
        if self.get_widget_by_id(widget["id"]):
            return False

        self.widgets.append(widget)
        return True

    def remove_widget(self, widget_id: str) -> bool:
        """
        Remove a widget from the dashboard.

        Args:
            widget_id: The widget ID to remove

        Returns:
            True if removed, False if not found
        """
        initial_count = len(self.widgets)
        self.widgets = [w for w in self.widgets if w.get("id") != widget_id]
        return len(self.widgets) < initial_count

    def update_widget(self, widget_id: str, updates: dict) -> bool:
        """
        Update a widget's configuration.

        Args:
            widget_id: The widget ID to update
            updates: Dict of fields to update

        Returns:
            True if updated, False if not found
        """
        for i, widget in enumerate(self.widgets):
            if widget.get("id") == widget_id:
                self.widgets[i].update(updates)
                return True
        return False

    def validate_layout(self) -> tuple[bool, Optional[str]]:
        """
        Validate dashboard layout and widget configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Validate layout structure
        if not isinstance(self.layout, dict):
            return False, "Layout must be a dictionary"

        # Validate widgets
        if not isinstance(self.widgets, list):
            return False, "Widgets must be a list"

        # Check for duplicate widget IDs
        widget_ids = [w.get("id") for w in self.widgets if w.get("id")]
        if len(widget_ids) != len(set(widget_ids)):
            return False, "Duplicate widget IDs found"

        # Validate each widget
        valid_widget_types = ["chart", "stat_card", "table"]
        for i, widget in enumerate(self.widgets):
            if not isinstance(widget, dict):
                return False, f"Widget {i} must be a dictionary"

            if not widget.get("id"):
                return False, f"Widget {i} missing required field: id"

            widget_type = widget.get("type")
            if not widget_type:
                return False, f"Widget {i} missing required field: type"

            if widget_type not in valid_widget_types:
                return False, f"Widget {i} has invalid type: {widget_type}. Must be one of: {', '.join(valid_widget_types)}"

            if not widget.get("position"):
                return False, f"Widget {i} missing required field: position"

            position = widget.get("position", {})
            required_position_fields = ["x", "y", "w", "h"]
            for field in required_position_fields:
                if field not in position:
                    return False, f"Widget {i} position missing required field: {field}"

            # Validate chart widgets have visualization_id
            if widget_type == "chart" and not widget.get("visualization_id"):
                return False, f"Chart widget {widget.get('id')} missing visualization_id"

        return True, None
