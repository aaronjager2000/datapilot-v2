"""
Data aggregation service for visualizations.

Provides efficient data aggregation, statistical calculations, and analysis
using optimized SQL queries to avoid loading large datasets into memory.
"""

from typing import Optional, Any, Literal
from uuid import UUID
from datetime import datetime
import statistics
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, Record


class AggregationService:
    """Service for aggregating and analyzing dataset data."""

    def __init__(self, db: AsyncSession):
        """
        Initialize aggregation service.

        Args:
            db: Database session
        """
        self.db = db

    async def aggregate_data(
        self,
        dataset_id: UUID,
        config: dict
    ) -> dict[str, Any]:
        """
        Aggregate data based on configuration for visualization.

        Uses optimized SQL queries to process data without loading all records
        into memory. Returns data in format ready for charting.

        Args:
            dataset_id: Dataset UUID
            config: Aggregation configuration:
                - columns: list of column names to include
                - aggregation: function name (sum, avg, count, min, max)
                - grouping: optional column to group by
                - filters: optional array of filter conditions
                - limit: optional result limit

        Returns:
            Dict with aggregated data ready for visualization:
            {
                "labels": [...],      # Group labels or x-axis values
                "datasets": [         # One or more data series
                    {
                        "label": "Series Name",
                        "data": [...]
                    }
                ],
                "metadata": {
                    "total_records": int,
                    "aggregation": str,
                    "grouping": str
                }
            }

        Example config:
            {
                "columns": ["revenue"],
                "aggregation": "sum",
                "grouping": "month",
                "filters": [
                    {"column": "status", "operator": "eq", "value": "completed"}
                ]
            }
        """
        # Validate dataset exists
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        columns = config.get("columns", [])
        aggregation = config.get("aggregation", "count")
        grouping = config.get("grouping")
        filters = config.get("filters", [])
        limit = config.get("limit", 1000)

        # Build SQL query
        query_parts = []
        params = {"dataset_id": str(dataset_id)}

        # Build aggregation expression
        agg_func = self._get_aggregation_function(aggregation)

        if grouping:
            # Group by aggregation
            select_clause = f"data->>'{grouping}' as label"

            for col in columns:
                select_clause += f", {agg_func}((data->>'{col}')::numeric) as {col}_agg"

            query = f"""
                SELECT {select_clause}
                FROM records
                WHERE dataset_id = :dataset_id
                  AND is_valid = true
                  {self._build_filter_clause(filters)}
                GROUP BY data->>'{grouping}'
                ORDER BY label
                LIMIT :limit
            """
        else:
            # Simple aggregation without grouping
            select_clause = "1 as label"

            for col in columns:
                select_clause += f", {agg_func}((data->>'{col}')::numeric) as {col}_agg"

            query = f"""
                SELECT {select_clause}
                FROM records
                WHERE dataset_id = :dataset_id
                  AND is_valid = true
                  {self._build_filter_clause(filters)}
            """

        params["limit"] = limit

        # Execute query
        result = await self.db.execute(text(query), params)
        rows = result.fetchall()

        # Format results
        labels = []
        datasets = {col: [] for col in columns}

        for row in rows:
            labels.append(row[0] if row[0] is not None else "null")
            for i, col in enumerate(columns):
                value = row[i + 1]
                datasets[col].append(float(value) if value is not None else 0)

        # Get total record count
        count_query = text("""
            SELECT COUNT(*)
            FROM records
            WHERE dataset_id = :dataset_id AND is_valid = true
        """)
        count_result = await self.db.execute(count_query, {"dataset_id": str(dataset_id)})
        total_records = count_result.scalar()

        return {
            "labels": labels,
            "datasets": [
                {
                    "label": col,
                    "data": datasets[col]
                }
                for col in columns
            ],
            "metadata": {
                "total_records": total_records,
                "aggregation": aggregation,
                "grouping": grouping,
                "filtered_results": len(labels)
            }
        }

    async def group_by_time(
        self,
        dataset_id: UUID,
        date_column: str,
        interval: Literal["hour", "day", "week", "month", "year"],
        metric: dict
    ) -> dict[str, Any]:
        """
        Aggregate data by time intervals.

        Args:
            dataset_id: Dataset UUID
            date_column: Name of the date/timestamp column
            interval: Time interval (hour, day, week, month, year)
            metric: Metric configuration:
                - column: column to aggregate
                - aggregation: function (sum, avg, count, min, max)

        Returns:
            Dict with time-series data:
            {
                "labels": ["2023-01", "2023-02", ...],
                "data": [100, 150, 200, ...],
                "metadata": {
                    "interval": "month",
                    "metric": "revenue",
                    "aggregation": "sum"
                }
            }
        """
        # Validate dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        metric_column = metric.get("column")
        aggregation = metric.get("aggregation", "count")

        # Map interval to PostgreSQL date_trunc
        trunc_format = {
            "hour": "hour",
            "day": "day",
            "week": "week",
            "month": "month",
            "year": "year"
        }[interval]

        agg_func = self._get_aggregation_function(aggregation)

        # Build query
        if metric_column:
            query = f"""
                SELECT
                    DATE_TRUNC('{trunc_format}', (data->>'{date_column}')::timestamp) as time_bucket,
                    {agg_func}((data->>'{metric_column}')::numeric) as value
                FROM records
                WHERE dataset_id = :dataset_id
                  AND is_valid = true
                  AND data->>'{date_column}' IS NOT NULL
                GROUP BY time_bucket
                ORDER BY time_bucket
            """
        else:
            # Count records if no metric column specified
            query = f"""
                SELECT
                    DATE_TRUNC('{trunc_format}', (data->>'{date_column}')::timestamp) as time_bucket,
                    COUNT(*) as value
                FROM records
                WHERE dataset_id = :dataset_id
                  AND is_valid = true
                  AND data->>'{date_column}' IS NOT NULL
                GROUP BY time_bucket
                ORDER BY time_bucket
            """

        result = await self.db.execute(text(query), {"dataset_id": str(dataset_id)})
        rows = result.fetchall()

        # Format results
        labels = []
        data = []

        for row in rows:
            # Format timestamp based on interval
            timestamp = row[0]
            if interval == "hour":
                labels.append(timestamp.strftime("%Y-%m-%d %H:00"))
            elif interval == "day":
                labels.append(timestamp.strftime("%Y-%m-%d"))
            elif interval == "week":
                labels.append(timestamp.strftime("%Y-W%U"))
            elif interval == "month":
                labels.append(timestamp.strftime("%Y-%m"))
            else:  # year
                labels.append(timestamp.strftime("%Y"))

            data.append(float(row[1]) if row[1] is not None else 0)

        return {
            "labels": labels,
            "data": data,
            "metadata": {
                "interval": interval,
                "metric": metric_column or "count",
                "aggregation": aggregation,
                "data_points": len(labels)
            }
        }

    async def calculate_statistics(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """
        Calculate descriptive statistics for a column.

        Args:
            dataset_id: Dataset UUID
            column: Column name to analyze

        Returns:
            Dict with statistical measures:
            {
                "count": int,
                "mean": float,
                "median": float,
                "std": float,
                "min": float,
                "max": float,
                "q25": float,  # 25th percentile
                "q75": float,  # 75th percentile
                "sum": float,
                "variance": float
            }
        """
        # Validate dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Use PostgreSQL aggregation functions for efficiency
        query = text(r"""
            SELECT
                COUNT((data->>:column)::numeric) as count,
                AVG((data->>:column)::numeric) as mean,
                STDDEV((data->>:column)::numeric) as std,
                MIN((data->>:column)::numeric) as min,
                MAX((data->>:column)::numeric) as max,
                SUM((data->>:column)::numeric) as sum,
                VARIANCE((data->>:column)::numeric) as variance,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as q25,
                PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as median,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as q75
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'  -- Ensure numeric values
        """)

        result = await self.db.execute(
            query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row or row[0] == 0:
            return {
                "error": f"No valid numeric data found for column '{column}'"
            }

        return {
            "count": int(row[0]) if row[0] else 0,
            "mean": float(row[1]) if row[1] is not None else None,
            "std": float(row[2]) if row[2] is not None else None,
            "min": float(row[3]) if row[3] is not None else None,
            "max": float(row[4]) if row[4] is not None else None,
            "sum": float(row[5]) if row[5] is not None else None,
            "variance": float(row[6]) if row[6] is not None else None,
            "q25": float(row[7]) if row[7] is not None else None,
            "median": float(row[8]) if row[8] is not None else None,
            "q75": float(row[9]) if row[9] is not None else None,
        }

    async def calculate_correlation(
        self,
        dataset_id: UUID,
        column1: str,
        column2: str
    ) -> dict[str, Any]:
        """
        Calculate correlation coefficient between two columns.

        Args:
            dataset_id: Dataset UUID
            column1: First column name
            column2: Second column name

        Returns:
            Dict with correlation information:
            {
                "correlation": float,  # Pearson correlation coefficient (-1 to 1)
                "sample_size": int,
                "column1": str,
                "column2": str,
                "strength": str  # weak, moderate, strong
            }
        """
        # Validate dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Calculate Pearson correlation using PostgreSQL
        query = text(r"""
            SELECT
                CORR((data->>:column1)::numeric, (data->>:column2)::numeric) as correlation,
                COUNT(*) as sample_size
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column1 IS NOT NULL
              AND data->>:column2 IS NOT NULL
              AND data->>:column1 ~ '^-?[0-9]+\.?[0-9]*$'
              AND data->>:column2 ~ '^-?[0-9]+\.?[0-9]*$'
        """)

        result = await self.db.execute(
            query,
            {
                "dataset_id": str(dataset_id),
                "column1": column1,
                "column2": column2
            }
        )
        row = result.fetchone()

        if not row or row[1] < 2:
            return {
                "error": "Insufficient data for correlation calculation (need at least 2 valid pairs)"
            }

        correlation = float(row[0]) if row[0] is not None else 0.0
        sample_size = int(row[1])

        # Determine correlation strength
        abs_corr = abs(correlation)
        if abs_corr < 0.3:
            strength = "weak"
        elif abs_corr < 0.7:
            strength = "moderate"
        else:
            strength = "strong"

        return {
            "correlation": correlation,
            "sample_size": sample_size,
            "column1": column1,
            "column2": column2,
            "strength": strength,
            "direction": "positive" if correlation > 0 else "negative" if correlation < 0 else "none"
        }

    async def detect_outliers(
        self,
        dataset_id: UUID,
        column: str,
        method: Literal["iqr", "z_score", "modified_z"] = "iqr"
    ) -> dict[str, Any]:
        """
        Detect outliers in a numeric column.

        Args:
            dataset_id: Dataset UUID
            column: Column name to analyze
            method: Detection method:
                - "iqr": Interquartile Range (values beyond Q1-1.5*IQR or Q3+1.5*IQR)
                - "z_score": Z-score method (|z| > 3)
                - "modified_z": Modified Z-score using MAD (|z| > 3.5)

        Returns:
            Dict with outlier information:
            {
                "method": str,
                "outliers": [
                    {
                        "row_number": int,
                        "value": float,
                        "z_score": float (if applicable)
                    }
                ],
                "outlier_count": int,
                "total_records": int,
                "threshold_low": float,
                "threshold_high": float
            }
        """
        # Validate dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        if method == "iqr":
            return await self._detect_outliers_iqr(dataset_id, column)
        elif method == "z_score":
            return await self._detect_outliers_zscore(dataset_id, column)
        elif method == "modified_z":
            return await self._detect_outliers_modified_z(dataset_id, column)
        else:
            raise ValueError(f"Unknown outlier detection method: {method}")

    async def _detect_outliers_iqr(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """Detect outliers using Interquartile Range method."""
        # Calculate quartiles
        stats_query = text(r"""
            SELECT
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as q1,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as q3,
                COUNT(*) as total
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
        """)

        result = await self.db.execute(
            stats_query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row or row[2] == 0:
            return {"error": f"No valid numeric data found for column '{column}'"}

        q1, q3, total = float(row[0]), float(row[1]), int(row[2])
        iqr = q3 - q1
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        # Find outliers
        outliers_query = text(r"""
            SELECT
                row_number,
                (data->>:column)::numeric as value
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
              AND ((data->>:column)::numeric < :lower_bound
                   OR (data->>:column)::numeric > :upper_bound)
            ORDER BY ABS((data->>:column)::numeric - :median) DESC
            LIMIT 100
        """)

        median = (q1 + q3) / 2
        outliers_result = await self.db.execute(
            outliers_query,
            {
                "dataset_id": str(dataset_id),
                "column": column,
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "median": median
            }
        )
        outlier_rows = outliers_result.fetchall()

        outliers = [
            {
                "row_number": row[0],
                "value": float(row[1])
            }
            for row in outlier_rows
        ]

        return {
            "method": "iqr",
            "outliers": outliers,
            "outlier_count": len(outliers),
            "total_records": total,
            "threshold_low": lower_bound,
            "threshold_high": upper_bound,
            "q1": q1,
            "q3": q3,
            "iqr": iqr
        }

    async def _detect_outliers_zscore(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """Detect outliers using Z-score method."""
        # Calculate mean and std
        stats_query = text(r"""
            SELECT
                AVG((data->>:column)::numeric) as mean,
                STDDEV((data->>:column)::numeric) as std,
                COUNT(*) as total
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
        """)

        result = await self.db.execute(
            stats_query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row or row[2] == 0:
            return {"error": f"No valid numeric data found for column '{column}'"}

        mean, std, total = float(row[0]), float(row[1]), int(row[2])

        if std == 0:
            return {"error": "Cannot calculate Z-score: standard deviation is zero"}

        # Find outliers (|z| > 3)
        outliers_query = text(r"""
            SELECT
                row_number,
                (data->>:column)::numeric as value,
                ABS(((data->>:column)::numeric - :mean) / :std) as z_score
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
              AND ABS(((data->>:column)::numeric - :mean) / :std) > 3
            ORDER BY z_score DESC
            LIMIT 100
        """)

        outliers_result = await self.db.execute(
            outliers_query,
            {
                "dataset_id": str(dataset_id),
                "column": column,
                "mean": mean,
                "std": std
            }
        )
        outlier_rows = outliers_result.fetchall()

        outliers = [
            {
                "row_number": row[0],
                "value": float(row[1]),
                "z_score": float(row[2])
            }
            for row in outlier_rows
        ]

        threshold_low = mean - 3 * std
        threshold_high = mean + 3 * std

        return {
            "method": "z_score",
            "outliers": outliers,
            "outlier_count": len(outliers),
            "total_records": total,
            "threshold_low": threshold_low,
            "threshold_high": threshold_high,
            "mean": mean,
            "std": std
        }

    async def _detect_outliers_modified_z(
        self,
        dataset_id: UUID,
        column: str
    ) -> dict[str, Any]:
        """Detect outliers using Modified Z-score with MAD."""
        # Calculate median and MAD
        stats_query = text(r"""
            WITH stats AS (
                SELECT
                    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY (data->>:column)::numeric) as median,
                    COUNT(*) as total
                FROM records
                WHERE dataset_id = :dataset_id
                  AND is_valid = true
                  AND data->>:column IS NOT NULL
                  AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
            )
            SELECT
                median,
                PERCENTILE_CONT(0.5) WITHIN GROUP (
                    ORDER BY ABS((data->>:column)::numeric - median)
                ) as mad,
                total
            FROM records, stats
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
            GROUP BY median, total
        """)

        result = await self.db.execute(
            stats_query,
            {"dataset_id": str(dataset_id), "column": column}
        )
        row = result.fetchone()

        if not row or row[2] == 0:
            return {"error": f"No valid numeric data found for column '{column}'"}

        median, mad, total = float(row[0]), float(row[1]), int(row[2])

        if mad == 0:
            return {"error": "Cannot calculate Modified Z-score: MAD is zero"}

        # Modified Z-score = 0.6745 * (x - median) / MAD
        # Outliers: |modified_z| > 3.5
        outliers_query = text(r"""
            SELECT
                row_number,
                (data->>:column)::numeric as value,
                ABS(0.6745 * ((data->>:column)::numeric - :median) / :mad) as modified_z
            FROM records
            WHERE dataset_id = :dataset_id
              AND is_valid = true
              AND data->>:column IS NOT NULL
              AND data->>:column ~ '^-?[0-9]+\.?[0-9]*$'
              AND ABS(0.6745 * ((data->>:column)::numeric - :median) / :mad) > 3.5
            ORDER BY modified_z DESC
            LIMIT 100
        """)

        outliers_result = await self.db.execute(
            outliers_query,
            {
                "dataset_id": str(dataset_id),
                "column": column,
                "median": median,
                "mad": mad
            }
        )
        outlier_rows = outliers_result.fetchall()

        outliers = [
            {
                "row_number": row[0],
                "value": float(row[1]),
                "modified_z_score": float(row[2])
            }
            for row in outlier_rows
        ]

        # Approximate thresholds
        threshold_low = median - (3.5 * mad / 0.6745)
        threshold_high = median + (3.5 * mad / 0.6745)

        return {
            "method": "modified_z",
            "outliers": outliers,
            "outlier_count": len(outliers),
            "total_records": total,
            "threshold_low": threshold_low,
            "threshold_high": threshold_high,
            "median": median,
            "mad": mad
        }

    def _get_aggregation_function(self, aggregation: str) -> str:
        """Map aggregation name to SQL function."""
        agg_map = {
            "sum": "SUM",
            "avg": "AVG",
            "mean": "AVG",
            "count": "COUNT",
            "min": "MIN",
            "max": "MAX"
        }
        return agg_map.get(aggregation.lower(), "COUNT")

    def _build_filter_clause(self, filters: list[dict]) -> str:
        """Build SQL WHERE clause from filter configuration."""
        if not filters:
            return ""

        clauses = []
        for f in filters:
            column = f.get("column")
            operator = f.get("operator", "eq")
            value = f.get("value")

            if operator == "eq":
                clauses.append(f"AND data->>'{column}' = '{value}'")
            elif operator == "ne":
                clauses.append(f"AND data->>'{column}' != '{value}'")
            elif operator == "gt":
                clauses.append(f"AND (data->>'{column}')::numeric > {value}")
            elif operator == "lt":
                clauses.append(f"AND (data->>'{column}')::numeric < {value}")
            elif operator == "gte":
                clauses.append(f"AND (data->>'{column}')::numeric >= {value}")
            elif operator == "lte":
                clauses.append(f"AND (data->>'{column}')::numeric <= {value}")
            elif operator == "contains":
                clauses.append(f"AND data->>'{column}' ILIKE '%{value}%'")
            elif operator == "in" and isinstance(value, list):
                values_str = "','".join(str(v) for v in value)
                clauses.append(f"AND data->>'{column}' IN ('{values_str}')")

        return " ".join(clauses)


# Factory function for dependency injection
async def get_aggregation_service(db: AsyncSession) -> AggregationService:
    """
    Get aggregation service instance.

    Args:
        db: Database session

    Returns:
        AggregationService instance
    """
    return AggregationService(db)
