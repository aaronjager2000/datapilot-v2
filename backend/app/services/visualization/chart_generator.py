"""
Chart generation service for visualizations.

Provides configuration generation for various chart types, automatic chart type
suggestions, color palette generation, and data formatting for frontend libraries.
"""

from typing import Any, Optional, Literal
from enum import Enum


class ChartType(str, Enum):
    """Supported chart types."""
    LINE = "line"
    BAR = "bar"
    PIE = "pie"
    SCATTER = "scatter"
    HEATMAP = "heatmap"
    AREA = "area"
    DOUGHNUT = "doughnut"


class ColorScheme(str, Enum):
    """Predefined color schemes."""
    DEFAULT = "default"
    VIBRANT = "vibrant"
    PASTEL = "pastel"
    OCEAN = "ocean"
    SUNSET = "sunset"
    FOREST = "forest"
    MONOCHROME = "monochrome"


class Theme(str, Enum):
    """Visual themes."""
    LIGHT = "light"
    DARK = "dark"


class ChartGenerator:
    """Service for generating chart configurations and recommendations."""

    # Predefined color palettes
    COLOR_PALETTES = {
        "default": [
            "#3B82F6",  # Blue
            "#10B981",  # Green
            "#F59E0B",  # Amber
            "#EF4444",  # Red
            "#8B5CF6",  # Purple
            "#EC4899",  # Pink
            "#06B6D4",  # Cyan
            "#84CC16",  # Lime
        ],
        "vibrant": [
            "#FF6B6B",  # Red
            "#4ECDC4",  # Teal
            "#45B7D1",  # Blue
            "#FFA07A",  # Light Salmon
            "#98D8C8",  # Mint
            "#F7DC6F",  # Yellow
            "#BB8FCE",  # Purple
            "#85C1E2",  # Sky Blue
        ],
        "pastel": [
            "#FFB6C1",  # Light Pink
            "#B0E0E6",  # Powder Blue
            "#98FB98",  # Pale Green
            "#DDA0DD",  # Plum
            "#F0E68C",  # Khaki
            "#FFDAB9",  # Peach
            "#E0BBE4",  # Lavender
            "#B2F7EF",  # Mint Cream
        ],
        "ocean": [
            "#006994",  # Deep Blue
            "#0FA3B1",  # Teal
            "#B5E2FA",  # Light Blue
            "#F9F7F3",  # Off White
            "#EDDEA4",  # Sand
            "#5C6B73",  # Slate
            "#9DB4C0",  # Steel Blue
            "#253D5B",  # Navy
        ],
        "sunset": [
            "#FF6B35",  # Orange Red
            "#F7931E",  # Orange
            "#FDC830",  # Yellow
            "#F37335",  # Dark Orange
            "#E63946",  # Red
            "#FFB997",  # Peach
            "#FF8966",  # Coral
            "#FFAA80",  # Light Coral
        ],
        "forest": [
            "#2D6A4F",  # Forest Green
            "#40916C",  # Green
            "#52B788",  # Light Green
            "#74C69D",  # Mint Green
            "#95D5B2",  # Pale Green
            "#B7E4C7",  # Very Light Green
            "#1B4332",  # Dark Green
            "#081C15",  # Very Dark Green
        ],
        "monochrome": [
            "#000000",  # Black
            "#404040",  # Dark Gray
            "#808080",  # Gray
            "#B0B0B0",  # Light Gray
            "#D0D0D0",  # Very Light Gray
            "#E8E8E8",  # Almost White
            "#202020",  # Almost Black
            "#606060",  # Medium Gray
        ],
    }

    def generate_chart_config(
        self,
        chart_type: str,
        data: dict[str, Any],
        options: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """
        Generate chart configuration compatible with Chart.js and Recharts.

        Args:
            chart_type: Type of chart (line, bar, pie, scatter, heatmap, area, doughnut)
            data: Chart data with labels and datasets
            options: Optional configuration overrides:
                - title: Chart title
                - theme: light or dark
                - color_scheme: Color palette name
                - show_legend: Boolean
                - show_grid: Boolean
                - stacked: Boolean (for bar/area charts)
                - smooth: Boolean (for line charts)
                - x_label: X-axis label
                - y_label: Y-axis label

        Returns:
            Chart configuration object compatible with Chart.js/Recharts
        """
        options = options or {}
        theme = options.get("theme", "light")
        color_scheme = options.get("color_scheme", "default")

        # Generate base configuration
        config = {
            "type": chart_type,
            "data": self._prepare_chart_data(data, chart_type, color_scheme),
            "options": self._generate_chart_options(chart_type, options, theme)
        }

        return config

    def suggest_chart_type(
        self,
        data: dict[str, Any],
        x_column: str,
        y_column: Optional[str] = None,
        column_types: Optional[dict[str, str]] = None
    ) -> dict[str, Any]:
        """
        Recommend the best chart type based on data characteristics.

        Args:
            data: Sample data for analysis
            x_column: X-axis column name
            y_column: Optional Y-axis column name
            column_types: Optional dict mapping column names to types
                         (numeric, categorical, date, etc.)

        Returns:
            Dict with recommendation:
            {
                "suggested_type": "bar",
                "reason": "Categorical X-axis with numeric Y-axis",
                "alternatives": ["line", "area"],
                "confidence": 0.9
            }
        """
        # Infer column types if not provided
        if column_types is None:
            column_types = self._infer_column_types(data)

        x_type = column_types.get(x_column, "unknown")
        y_type = column_types.get(y_column, "unknown") if y_column else None

        # Decision rules
        suggestions = []

        # Categorical X + Numeric Y = Bar chart
        if x_type == "categorical" and y_type == "numeric":
            suggestions.append({
                "type": "bar",
                "reason": "Categorical X-axis with numeric Y-axis is ideal for bar charts",
                "confidence": 0.95
            })
            suggestions.append({
                "type": "line",
                "reason": "Line chart can also show trends across categories",
                "confidence": 0.7
            })

        # Date/Time X + Numeric Y = Line chart
        elif x_type in ["date", "datetime"] and y_type == "numeric":
            suggestions.append({
                "type": "line",
                "reason": "Time-series data is best visualized with line charts",
                "confidence": 0.95
            })
            suggestions.append({
                "type": "area",
                "reason": "Area chart emphasizes magnitude over time",
                "confidence": 0.85
            })
            suggestions.append({
                "type": "bar",
                "reason": "Bar chart for discrete time intervals",
                "confidence": 0.7
            })

        # Numeric X + Numeric Y = Scatter plot
        elif x_type == "numeric" and y_type == "numeric":
            suggestions.append({
                "type": "scatter",
                "reason": "Scatter plot reveals relationships between numeric variables",
                "confidence": 0.9
            })
            suggestions.append({
                "type": "line",
                "reason": "Line chart if data has a natural order",
                "confidence": 0.75
            })

        # Single categorical column = Pie chart
        elif x_type == "categorical" and y_type is None:
            suggestions.append({
                "type": "pie",
                "reason": "Pie chart shows proportions of a whole",
                "confidence": 0.85
            })
            suggestions.append({
                "type": "doughnut",
                "reason": "Doughnut chart is a modern alternative to pie",
                "confidence": 0.85
            })
            suggestions.append({
                "type": "bar",
                "reason": "Bar chart for easier comparison of values",
                "confidence": 0.8
            })

        # Default fallback
        else:
            suggestions.append({
                "type": "bar",
                "reason": "Bar chart is versatile for most data types",
                "confidence": 0.6
            })

        # Return top suggestion with alternatives
        if suggestions:
            top = suggestions[0]
            alternatives = [s["type"] for s in suggestions[1:]]
            return {
                "suggested_type": top["type"],
                "reason": top["reason"],
                "confidence": top["confidence"],
                "alternatives": alternatives
            }

        return {
            "suggested_type": "bar",
            "reason": "Default recommendation",
            "confidence": 0.5,
            "alternatives": []
        }

    def generate_color_palette(
        self,
        count: int,
        scheme: str = "default"
    ) -> list[str]:
        """
        Generate N colors from a color scheme.

        Args:
            count: Number of colors needed
            scheme: Color scheme name (default, vibrant, pastel, ocean, sunset, forest, monochrome)

        Returns:
            List of color hex codes
        """
        base_colors = self.COLOR_PALETTES.get(scheme, self.COLOR_PALETTES["default"])

        if count <= len(base_colors):
            return base_colors[:count]

        # If we need more colors, repeat and adjust brightness
        colors = []
        cycles = (count + len(base_colors) - 1) // len(base_colors)

        for cycle in range(cycles):
            for color in base_colors:
                if len(colors) >= count:
                    break
                # Adjust brightness for repeated colors
                if cycle > 0:
                    colors.append(self._adjust_color_brightness(color, 1 - (cycle * 0.15)))
                else:
                    colors.append(color)

        return colors[:count]

    def format_chart_data(
        self,
        raw_data: dict[str, Any],
        chart_type: str
    ) -> dict[str, Any]:
        """
        Transform raw data for frontend charting libraries.

        Args:
            raw_data: Raw data from aggregation service
            chart_type: Target chart type

        Returns:
            Formatted data structure for Chart.js/Recharts
        """
        if chart_type in ["line", "bar", "area"]:
            return self._format_cartesian_data(raw_data)
        elif chart_type in ["pie", "doughnut"]:
            return self._format_pie_data(raw_data)
        elif chart_type == "scatter":
            return self._format_scatter_data(raw_data)
        elif chart_type == "heatmap":
            return self._format_heatmap_data(raw_data)
        else:
            return raw_data

    def _prepare_chart_data(
        self,
        data: dict[str, Any],
        chart_type: str,
        color_scheme: str
    ) -> dict[str, Any]:
        """Prepare data with colors applied."""
        formatted_data = self.format_chart_data(data, chart_type)

        # Apply colors to datasets
        if "datasets" in formatted_data:
            colors = self.generate_color_palette(len(formatted_data["datasets"]), color_scheme)
            for i, dataset in enumerate(formatted_data["datasets"]):
                color = colors[i % len(colors)]
                dataset["backgroundColor"] = color
                dataset["borderColor"] = color
                if chart_type == "line":
                    dataset["borderWidth"] = 2
                    dataset["backgroundColor"] = self._add_alpha(color, 0.1)
                elif chart_type == "area":
                    dataset["fill"] = True
                    dataset["backgroundColor"] = self._add_alpha(color, 0.3)

        return formatted_data

    def _generate_chart_options(
        self,
        chart_type: str,
        options: dict[str, Any],
        theme: str
    ) -> dict[str, Any]:
        """Generate Chart.js options object."""
        is_dark = theme == "dark"

        base_options = {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {
                    "display": options.get("show_legend", True),
                    "position": "top",
                    "labels": {
                        "color": "#E5E7EB" if is_dark else "#1F2937",
                        "font": {
                            "size": 12
                        }
                    }
                },
                "title": {
                    "display": bool(options.get("title")),
                    "text": options.get("title", ""),
                    "color": "#F3F4F6" if is_dark else "#111827",
                    "font": {
                        "size": 16,
                        "weight": "bold"
                    }
                },
                "tooltip": {
                    "enabled": True,
                    "backgroundColor": "#1F2937" if is_dark else "#FFFFFF",
                    "titleColor": "#F3F4F6" if is_dark else "#111827",
                    "bodyColor": "#E5E7EB" if is_dark else "#374151",
                    "borderColor": "#374151" if is_dark else "#E5E7EB",
                    "borderWidth": 1
                }
            }
        }

        # Chart-specific options
        if chart_type in ["line", "bar", "area", "scatter"]:
            base_options["scales"] = {
                "x": {
                    "display": True,
                    "title": {
                        "display": bool(options.get("x_label")),
                        "text": options.get("x_label", ""),
                        "color": "#E5E7EB" if is_dark else "#374151"
                    },
                    "grid": {
                        "display": options.get("show_grid", True),
                        "color": "#374151" if is_dark else "#E5E7EB"
                    },
                    "ticks": {
                        "color": "#D1D5DB" if is_dark else "#4B5563"
                    }
                },
                "y": {
                    "display": True,
                    "title": {
                        "display": bool(options.get("y_label")),
                        "text": options.get("y_label", ""),
                        "color": "#E5E7EB" if is_dark else "#374151"
                    },
                    "grid": {
                        "display": options.get("show_grid", True),
                        "color": "#374151" if is_dark else "#E5E7EB"
                    },
                    "ticks": {
                        "color": "#D1D5DB" if is_dark else "#4B5563"
                    }
                }
            }

        # Bar chart specific
        if chart_type == "bar":
            base_options["scales"]["x"]["stacked"] = options.get("stacked", False)
            base_options["scales"]["y"]["stacked"] = options.get("stacked", False)
            base_options["scales"]["y"]["beginAtZero"] = True

        # Line chart specific
        if chart_type == "line":
            base_options["elements"] = {
                "line": {
                    "tension": 0.4 if options.get("smooth", True) else 0
                }
            }

        return base_options

    def _format_cartesian_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Format data for line, bar, and area charts."""
        return {
            "labels": raw_data.get("labels", []),
            "datasets": [
                {
                    "label": dataset.get("label", "Data"),
                    "data": dataset.get("data", [])
                }
                for dataset in raw_data.get("datasets", [])
            ]
        }

    def _format_pie_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Format data for pie and doughnut charts."""
        labels = raw_data.get("labels", [])
        datasets = raw_data.get("datasets", [])

        # Pie charts typically use a single dataset
        if datasets:
            data = datasets[0].get("data", [])
        else:
            data = []

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": "Distribution",
                    "data": data
                }
            ]
        }

    def _format_scatter_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Format data for scatter plots."""
        datasets = raw_data.get("datasets", [])

        formatted_datasets = []
        for dataset in datasets:
            data = dataset.get("data", [])
            # Convert to {x, y} format if not already
            if data and isinstance(data[0], (int, float)):
                labels = raw_data.get("labels", [])
                data = [{"x": i, "y": val} for i, val in enumerate(data)]

            formatted_datasets.append({
                "label": dataset.get("label", "Data"),
                "data": data
            })

        return {
            "datasets": formatted_datasets
        }

    def _format_heatmap_data(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """Format data for heatmap."""
        # Heatmap requires 2D array structure
        return {
            "xLabels": raw_data.get("x_labels", []),
            "yLabels": raw_data.get("y_labels", []),
            "data": raw_data.get("data", [])
        }

    def _infer_column_types(self, data: dict[str, Any]) -> dict[str, str]:
        """Infer column types from sample data."""
        column_types = {}

        # Check labels
        labels = data.get("labels", [])
        if labels:
            sample = labels[0]
            if isinstance(sample, (int, float)):
                column_types["x"] = "numeric"
            elif isinstance(sample, str):
                # Try to parse as date
                try:
                    from datetime import datetime
                    datetime.fromisoformat(sample.replace("Z", "+00:00"))
                    column_types["x"] = "date"
                except:
                    column_types["x"] = "categorical"

        # Check dataset values
        datasets = data.get("datasets", [])
        if datasets and datasets[0].get("data"):
            sample = datasets[0]["data"][0]
            if isinstance(sample, (int, float)):
                column_types["y"] = "numeric"
            elif isinstance(sample, dict) and "x" in sample and "y" in sample:
                column_types["y"] = "numeric"
            else:
                column_types["y"] = "categorical"

        return column_types

    def _adjust_color_brightness(self, hex_color: str, factor: float) -> str:
        """Adjust color brightness by a factor (0-1)."""
        # Remove # if present
        hex_color = hex_color.lstrip("#")

        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Adjust brightness
        r = int(min(255, max(0, r * factor)))
        g = int(min(255, max(0, g * factor)))
        b = int(min(255, max(0, b * factor)))

        # Convert back to hex
        return f"#{r:02x}{g:02x}{b:02x}"

    def _add_alpha(self, hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba with alpha."""
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r}, {g}, {b}, {alpha})"


# Factory function
def get_chart_generator() -> ChartGenerator:
    """
    Get chart generator instance.

    Returns:
        ChartGenerator instance
    """
    return ChartGenerator()
