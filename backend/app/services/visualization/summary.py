"""
Data summary service for dataset analysis and profiling.

Provides comprehensive summaries, column profiling, distribution analysis,
and dataset comparison capabilities.
"""

from typing import Any, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset
from app.services.visualization.aggregator import AggregationService


class SummaryService:
    """Service for generating data summaries and profiles."""

    def __init__(self, db: AsyncSession):
        """
        Initialize summary service.

        Args:
            db: Database session
        """
        self.db = db
        self.aggregator = AggregationService(db)

    async def generate_dataset_summary(
        self,
        dataset_id: UUID
    ) -> dict[str, Any]:
        """
        Generate comprehensive dataset summary.

        Includes row/column counts, statistics for numeric/categorical columns,
        missing value analysis, and data quality score.

        Args:
            dataset_id: Dataset UUID

        Returns:
            Dict with comprehensive summary:
            {
                "dataset_id": str,
                "row_count": int,
                "column_count": int,
                "columns": {
                    "column_name": {
                        "type": "numeric" | "categorical" | "text" | "null",
                        "stats": {...},
                        "missing_count": int,
                        "missing_percentage": float
                    }
                },
                "numeric_columns": [...],
                "categorical_columns": [...],
                "missing_values_summary": {...},
                "data_quality_score": float,
                "file_info": {...}
            }
        """
        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get basic info
        row_count = dataset.row_count or 0
        schema_info = dataset.schema_info or {}
        columns_info = schema_info.get("columns", [])

        if not columns_info:
            return {
                "error": "Dataset schema information not available"
            }

        # Analyze each column
        column_summaries = {}
        numeric_columns = []
        categorical_columns = []
        total_missing = 0
        total_cells = row_count * len(columns_info)

        for col_info in columns_info:
            col_name = col_info.get("name")
            col_type = col_info.get("type", "unknown")

            # Get missing value count
            missing_stats = await self._get_missing_stats(dataset_id, col_name, row_count)

            column_summary = {
                "type": col_type,
                "missing_count": missing_stats["count"],
                "missing_percentage": missing_stats["percentage"]
            }

            total_missing += missing_stats["count"]

            # Get type-specific stats
            if col_type == "numeric":
                stats = await self.aggregator.calculate_statistics(dataset_id, col_name)
                if "error" not in stats:
                    column_summary["stats"] = {
                        "count": stats["count"],
                        "mean": stats["mean"],
                        "median": stats["median"],
                        "std": stats["std"],
                        "min": stats["min"],
                        "max": stats["max"],
                        "q25": stats["q25"],
                        "q75": stats["q75"]
                    }
                    numeric_columns.append(col_name)

            elif col_type in ["categorical", "text"]:
                cat_stats = await self._get_categorical_stats(dataset_id, col_name)
                column_summary["stats"] = cat_stats
                if col_type == "categorical":
                    categorical_columns.append(col_name)

            column_summaries[col_name] = column_summary

        # Calculate data quality score
        completeness_score = 1 - (total_missing / total_cells) if total_cells > 0 else 0
        data_quality_score = completeness_score * 100

        return {
            "dataset_id": str(dataset_id),
            "dataset_name": dataset.name,
            "row_count": row_count,
            "column_count": len(columns_info),
            "columns": column_summaries,
            "numeric_columns": numeric_columns,
            "categorical_columns": categorical_columns,
            "missing_values_summary": {
                "total_missing": total_missing,
                "total_cells": total_cells,
                "missing_percentage": (total_missing / total_cells * 100) if total_cells > 0 else 0
            },
            "data_quality_score": round(data_quality_score, 2),
            "file_info": {
                "file_name": dataset.file_name,
                "file_size": dataset.file_size,
                "file_size_mb": dataset.file_size_mb,
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None
            }
        }

    async def generate_column_profile(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """
        Generate detailed column profile.

        Includes distribution histogram, frequency table, null analysis,
        and outlier detection.

        Args:
            dataset_id: Dataset UUID
            column: Column name to profile

        Returns:
            Dict with column profile:
            {
                "column": str,
                "type": str,
                "statistics": {...},
                "distribution": {
                    "histogram": [...],
                    "bins": [...]
                },
                "frequency_table": [...],
                "null_analysis": {...},
                "outliers": {...}
            }
        """
        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Determine column type
        schema_info = dataset.schema_info or {}
        columns_info = schema_info.get("columns", [])
        col_info = next((c for c in columns_info if c.get("name") == column), None)

        if not col_info:
            raise ValueError(f"Column '{column}' not found in dataset")

        col_type = col_info.get("type", "unknown")

        profile = {
            "column": column,
            "type": col_type,
            "dataset_id": str(dataset_id)
        }

        # Get basic statistics
        if col_type == "numeric":
            stats = await self.aggregator.calculate_statistics(dataset_id, column)
            if "error" not in stats:
                profile["statistics"] = stats

                # Get distribution histogram
                distribution = await self._get_numeric_distribution(dataset_id, column, stats)
                profile["distribution"] = distribution

                # Detect outliers
                outliers = await self.aggregator.detect_outliers(dataset_id, column, method="iqr")
                profile["outliers"] = outliers

        elif col_type in ["categorical", "text"]:
            # Get frequency table
            freq_table = await self._get_frequency_table(dataset_id, column, limit=50)
            profile["frequency_table"] = freq_table

            # Get categorical stats
            cat_stats = await self._get_categorical_stats(dataset_id, column)
            profile["statistics"] = cat_stats

        # Null analysis
        null_analysis = await self._get_null_analysis(dataset_id, column, dataset.row_count or 0)
        profile["null_analysis"] = null_analysis

        return profile

    async def compare_datasets(
        self,
        dataset_id1: UUID,
        dataset_id2: UUID
    ) -> dict[str, Any]:
        """
        Compare two datasets.

        Analyzes schema differences and value distribution differences.

        Args:
            dataset_id1: First dataset UUID
            dataset_id2: Second dataset UUID

        Returns:
            Dict with comparison:
            {
                "dataset1": {...},
                "dataset2": {...},
                "schema_comparison": {
                    "common_columns": [...],
                    "only_in_dataset1": [...],
                    "only_in_dataset2": [...],
                    "type_differences": [...]
                },
                "distribution_comparison": {...}
            }
        """
        # Get both datasets
        dataset1 = await self.db.get(Dataset, dataset_id1)
        dataset2 = await self.db.get(Dataset, dataset_id2)

        if not dataset1:
            raise ValueError(f"Dataset {dataset_id1} not found")
        if not dataset2:
            raise ValueError(f"Dataset {dataset_id2} not found")

        # Get schema info
        schema1 = dataset1.schema_info or {}
        schema2 = dataset2.schema_info or {}

        columns1 = {c["name"]: c.get("type") for c in schema1.get("columns", [])}
        columns2 = {c["name"]: c.get("type") for c in schema2.get("columns", [])}

        # Schema comparison
        common_columns = set(columns1.keys()) & set(columns2.keys())
        only_in_1 = set(columns1.keys()) - set(columns2.keys())
        only_in_2 = set(columns2.keys()) - set(columns1.keys())

        type_differences = []
        for col in common_columns:
            if columns1[col] != columns2[col]:
                type_differences.append({
                    "column": col,
                    "dataset1_type": columns1[col],
                    "dataset2_type": columns2[col]
                })

        schema_comparison = {
            "common_columns": list(common_columns),
            "only_in_dataset1": list(only_in_1),
            "only_in_dataset2": list(only_in_2),
            "type_differences": type_differences
        }

        # Distribution comparison for common numeric columns
        distribution_comparison = {}
        for col in common_columns:
            if columns1[col] == "numeric" and columns2[col] == "numeric":
                stats1 = await self.aggregator.calculate_statistics(dataset_id1, col)
                stats2 = await self.aggregator.calculate_statistics(dataset_id2, col)

                if "error" not in stats1 and "error" not in stats2:
                    distribution_comparison[col] = {
                        "dataset1": {
                            "mean": stats1["mean"],
                            "median": stats1["median"],
                            "std": stats1["std"],
                            "min": stats1["min"],
                            "max": stats1["max"]
                        },
                        "dataset2": {
                            "mean": stats2["mean"],
                            "median": stats2["median"],
                            "std": stats2["std"],
                            "min": stats2["min"],
                            "max": stats2["max"]
                        },
                        "differences": {
                            "mean_diff": abs(stats1["mean"] - stats2["mean"]) if stats1["mean"] and stats2["mean"] else None,
                            "median_diff": abs(stats1["median"] - stats2["median"]) if stats1["median"] and stats2["median"] else None
                        }
                    }

        return {
            "dataset1": {
                "id": str(dataset_id1),
                "name": dataset1.name,
                "row_count": dataset1.row_count,
                "column_count": len(columns1)
            },
            "dataset2": {
                "id": str(dataset_id2),
                "name": dataset2.name,
                "row_count": dataset2.row_count,
                "column_count": len(columns2)
            },
            "schema_comparison": schema_comparison,
            "distribution_comparison": distribution_comparison
        }

    async def _get_missing_stats(
        self,
        dataset_id: UUID,
        column: str,
        total_rows: int
    ) -> dict[str, Any]:
        """Get missing value statistics for a column."""
        query = text(r"""
            SELECT COUNT(*) as missing_count
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND (data->>:column IS NULL OR data->>:column = '')
        """)

        result = await self.db.execute(
            query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()
        missing_count = row[0] if row else 0

        return {
            "count": missing_count,
            "percentage": (missing_count / total_rows * 100) if total_rows > 0 else 0
        }

    async def _get_categorical_stats(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """Get statistics for categorical columns."""
        query = text(r"""
            SELECT
                COUNT(DISTINCT data->>:column) as unique_values,
                COUNT(*) as total_count,
                data->>:column as mode_value,
                COUNT(*) as mode_count
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
            GROUP BY data->>:column
            ORDER BY mode_count DESC
            LIMIT 1
        """)

        result = await self.db.execute(
            query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row:
            return {
                "unique_values": 0,
                "mode": None,
                "mode_count": 0
            }

        # Get total unique count
        unique_query = text(r"""
            SELECT COUNT(DISTINCT data->>:column) as unique_count
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
        """)

        unique_result = await self.db.execute(
            unique_query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        unique_row = unique_result.fetchone()
        unique_count = unique_row[0] if unique_row else 0

        return {
            "unique_values": unique_count,
            "mode": row[2],
            "mode_count": int(row[3])
        }

    async def _get_numeric_distribution(
        self,
        dataset_id: UUID,
        column: str,
        stats: dict[str, Any],
        bins: int = 10
    ) -> dict[str, Any]:
        """Generate histogram for numeric column."""
        min_val = stats.get("min", 0)
        max_val = stats.get("max", 0)

        if min_val == max_val:
            return {
                "bins": [min_val],
                "counts": [stats.get("count", 0)]
            }

        bin_width = (max_val - min_val) / bins

        # Generate histogram using SQL
        query = text(r"""
            SELECT
                WIDTH_BUCKET((data->>:column)::numeric, :min_val, :max_val, :bins) as bin,
                COUNT(*) as count
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
            GROUP BY bin
            ORDER BY bin
        """)

        result = await self.db.execute(
            query,
            {
                "dataset_id": str(dataset_id),
                "column": column,
                "min_val": float(min_val),
                "max_val": float(max_val),
                "bins": bins
            }
        )
        rows = result.fetchall()

        # Create bin labels and counts
        bin_edges = [min_val + i * bin_width for i in range(bins + 1)]
        bin_labels = [
            f"{bin_edges[i]:.2f}-{bin_edges[i+1]:.2f}"
            for i in range(bins)
        ]

        # Fill in counts (some bins might be empty)
        counts = [0] * bins
        for row in rows:
            bin_idx = int(row[0]) - 1  # WIDTH_BUCKET is 1-indexed
            if 0 <= bin_idx < bins:
                counts[bin_idx] = int(row[1])

        return {
            "bins": bin_labels,
            "counts": counts,
            "bin_width": bin_width
        }

    async def _get_frequency_table(
        self,
        dataset_id: UUID,
        column: str,
        limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get frequency table for categorical column."""
        query = text(r"""
            SELECT
                data->>:column as value,
                COUNT(*) as count,
                (COUNT(*) * 100.0 / SUM(COUNT(*)) OVER ()) as percentage
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
            GROUP BY data->>:column
            ORDER BY count DESC
            LIMIT :limit
        """)

        result = await self.db.execute(
            query,
            {
                "dataset_id": str(dataset_id),
                "column": column,
                "limit": limit
            }
        )
        rows = result.fetchall()

        return [
            {
                "value": row[0],
                "count": int(row[1]),
                "percentage": float(row[2])
            }
            for row in rows
        ]

    async def _get_null_analysis(
        self,
        dataset_id: UUID,
        column: str,
        total_rows: int
    ) -> dict[str, Any]:
        """Analyze null values in column."""
        query = text(r"""
            SELECT
                COUNT(*) FILTER (WHERE data->>:column IS NULL) as null_count,
                COUNT(*) FILTER (WHERE data->>:column = '') as empty_string_count,
                COUNT(*) FILTER (WHERE data->>:column IS NOT NULL AND data->>:column != '') as non_null_count
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
        """)

        result = await self.db.execute(
            query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row:
            return {
                "null_count": 0,
                "empty_string_count": 0,
                "non_null_count": 0,
                "null_percentage": 0,
                "completeness": 0
            }

        null_count = int(row[0])
        empty_count = int(row[1])
        non_null_count = int(row[2])
        total_missing = null_count + empty_count

        return {
            "null_count": null_count,
            "empty_string_count": empty_count,
            "non_null_count": non_null_count,
            "total_missing": total_missing,
            "null_percentage": (total_missing / total_rows * 100) if total_rows > 0 else 0,
            "completeness": (non_null_count / total_rows * 100) if total_rows > 0 else 0
        }


# Factory function for dependency injection
async def get_summary_service(db: AsyncSession) -> SummaryService:
    """
    Get summary service instance.

    Args:
        db: Database session

    Returns:
        SummaryService instance
    """
    return SummaryService(db)
