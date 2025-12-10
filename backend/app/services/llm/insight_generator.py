"""
Insight Generator service for AI-powered data analysis.

Orchestrates data analysis, LLM processing, and insight generation
by combining statistical analysis with natural language AI.
"""

import json
import logging
from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, Insight, InsightType, InsightGenerator as InsightGeneratorEnum, Visualization
from app.services.llm.client import get_llm_client, LLMClient
from app.services.llm.prompts import (
    INSIGHT_GENERATION_PROMPT,
    DATA_QUESTION_PROMPT,
    DATASET_SUMMARY_PROMPT,
    CORRELATION_EXPLANATION_PROMPT,
    ANOMALY_DETECTION_PROMPT,
    SYSTEM_PROMPTS,
    format_schema,
    format_stats,
    format_sample_data
)
from app.services.visualization.summary import SummaryService
from app.services.visualization.aggregator import AggregationService


logger = logging.getLogger(__name__)


class InsightGeneratorService:
    """
    Service for generating AI-powered insights from data.

    Combines statistical analysis with LLM processing to generate
    actionable insights, answer questions, and explain visualizations.
    """

    def __init__(self, db: AsyncSession, llm_client: Optional[LLMClient] = None):
        """
        Initialize insight generator.

        Args:
            db: Database session
            llm_client: Optional LLM client (creates default if not provided)
        """
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.summary_service = SummaryService(db)
        self.aggregator = AggregationService(db)

    async def generate_insights(
        self,
        dataset_id: UUID,
        save_to_db: bool = True
    ) -> list[dict[str, Any]]:
        """
        Generate comprehensive insights for a dataset.

        Steps:
        1. Get dataset summary and statistics
        2. Identify trends (if time-series data)
        3. Find correlations between numeric columns
        4. Detect anomalies in distributions
        5. Generate LLM prompt with findings
        6. Parse LLM response into structured insights
        7. Optionally save insights to database
        8. Return insights

        Args:
            dataset_id: Dataset UUID
            save_to_db: Whether to save insights to database

        Returns:
            List of insight dictionaries
        """
        logger.info(f"Generating insights for dataset {dataset_id}")

        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Step 1: Get dataset summary
        summary = await self.summary_service.generate_dataset_summary(dataset_id)

        # Step 2: Identify trends (if date column exists)
        trends = await self._identify_trends(dataset_id, summary)

        # Step 3: Find correlations
        correlations = await self._find_correlations(dataset_id, summary)

        # Step 4: Detect anomalies
        anomalies = await self._detect_anomalies(dataset_id, summary)

        # Step 5: Generate LLM prompt
        prompt = self._build_insight_prompt(summary, trends, correlations, anomalies)

        # Step 6: Get insights from LLM
        try:
            schema = {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "title": {"type": "string"},
                        "description": {"type": "string"},
                        "confidence": {"type": "number"},
                        "supporting_data": {"type": "object"},
                        "suggested_action": {"type": "string"}
                    }
                }
            }

            llm_insights = await self.llm_client.generate_structured_output(
                prompt=prompt,
                schema=schema,
                system_prompt=SYSTEM_PROMPTS["data_analyst"],
                max_tokens=3000,
                temperature=0.7
            )

        except Exception as e:
            logger.error(f"LLM insight generation failed: {e}")
            # Fallback to rule-based insights
            llm_insights = self._generate_fallback_insights(summary, trends, correlations, anomalies)

        # Step 7: Save to database if requested
        if save_to_db:
            await self._save_insights_to_db(dataset_id, dataset.organization_id, llm_insights)

        logger.info(f"Generated {len(llm_insights)} insights for dataset {dataset_id}")
        return llm_insights

    async def answer_data_question(
        self,
        dataset_id: UUID,
        question: str
    ) -> dict[str, Any]:
        """
        Answer a natural language question about the dataset.

        Args:
            dataset_id: Dataset UUID
            question: User's question in natural language

        Returns:
            Dict with answer and supporting data:
            {
                "question": str,
                "answer": str,
                "supporting_data": {...},
                "confidence": float
            }
        """
        logger.info(f"Answering question for dataset {dataset_id}: {question}")

        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get dataset summary
        summary = await self.summary_service.generate_dataset_summary(dataset_id)

        # Get sample data
        sample_data = await self._get_sample_data(dataset_id, limit=10)

        # Build prompt
        schema_info = summary.get("columns", {})
        column_stats = self._format_column_stats(schema_info)

        prompt = DATA_QUESTION_PROMPT.format(
            dataset_name=dataset.name,
            row_count=summary.get("row_count", 0),
            column_count=summary.get("column_count", 0),
            schema=format_schema(dataset.schema_info.get("columns", [])),
            column_stats=column_stats,
            sample_data=format_sample_data(sample_data, limit=5),
            user_question=question
        )

        # Get answer from LLM
        try:
            answer = await self.llm_client.generate_completion(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPTS["data_analyst"],
                max_tokens=1000,
                temperature=0.7
            )

            return {
                "question": question,
                "answer": answer,
                "dataset_name": dataset.name,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to answer question: {e}")
            return {
                "question": question,
                "answer": f"I encountered an error while analyzing your data: {str(e)}",
                "error": True
            }

    async def explain_visualization(
        self,
        visualization_id: UUID
    ) -> dict[str, Any]:
        """
        Generate natural language explanation for a visualization.

        Args:
            visualization_id: Visualization UUID

        Returns:
            Dict with explanation:
            {
                "visualization_id": str,
                "explanation": str,
                "key_takeaways": [...],
                "recommendations": [...]
            }
        """
        logger.info(f"Explaining visualization {visualization_id}")

        # Get visualization
        viz = await self.db.get(Visualization, visualization_id)
        if not viz:
            raise ValueError(f"Visualization {visualization_id} not found")

        # Get dataset
        dataset = await self.db.get(Dataset, viz.dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {viz.dataset_id} not found")

        # Analyze the visualization configuration
        config = viz.config or {}
        chart_type = viz.chart_type.value

        # Get relevant data statistics
        x_axis = config.get("x_axis")
        y_axis = config.get("y_axis")
        grouping = config.get("grouping")
        aggregation = config.get("aggregation", "count")

        # Build explanation prompt
        prompt = f"""Explain this data visualization in plain language.

Visualization Details:
- Name: {viz.name}
- Chart Type: {chart_type}
- Dataset: {dataset.name}
- X-Axis: {x_axis}
- Y-Axis: {y_axis}
- Grouping: {grouping or "None"}
- Aggregation: {aggregation}

Configuration:
{json.dumps(config, indent=2)}

Please provide:
1. What this visualization shows (2-3 sentences)
2. Key takeaways (3-5 bullet points)
3. What patterns or trends are visible
4. Recommendations for action or further analysis

Be specific and reference the actual data being visualized."""

        try:
            explanation = await self.llm_client.generate_completion(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPTS["technical_writer"],
                max_tokens=800,
                temperature=0.7
            )

            return {
                "visualization_id": str(visualization_id),
                "visualization_name": viz.name,
                "chart_type": chart_type,
                "explanation": explanation,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to explain visualization: {e}")
            return {
                "visualization_id": str(visualization_id),
                "explanation": f"This {chart_type} chart displays {y_axis} by {x_axis}.",
                "error": True
            }

    async def _identify_trends(
        self,
        dataset_id: UUID,
        summary: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify trends in time-series data."""
        trends = []

        # Look for date/time columns
        columns = summary.get("columns", {})
        date_columns = [
            col_name for col_name, col_info in columns.items()
            if col_info.get("type") in ["date", "datetime", "timestamp"]
        ]

        if not date_columns:
            return trends

        # Analyze trends for numeric columns over time
        numeric_columns = summary.get("numeric_columns", [])

        for date_col in date_columns[:1]:  # Limit to first date column
            for num_col in numeric_columns[:3]:  # Limit to first 3 numeric columns
                try:
                    trend_data = await self.aggregator.group_by_time(
                        dataset_id=dataset_id,
                        date_column=date_col,
                        interval="month",
                        metric={"column": num_col, "aggregation": "avg"}
                    )

                    if trend_data.get("data"):
                        trends.append({
                            "time_column": date_col,
                            "metric_column": num_col,
                            "data_points": len(trend_data["data"]),
                            "summary": f"Analyzed {num_col} over time"
                        })

                except Exception as e:
                    logger.warning(f"Failed to analyze trend for {num_col}: {e}")

        return trends

    async def _find_correlations(
        self,
        dataset_id: UUID,
        summary: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Find correlations between numeric columns."""
        correlations = []
        numeric_columns = summary.get("numeric_columns", [])

        # Limit to top correlations to avoid too many API calls
        max_pairs = 5
        count = 0

        for i, col1 in enumerate(numeric_columns):
            for col2 in numeric_columns[i+1:]:
                if count >= max_pairs:
                    break

                try:
                    corr_result = await self.aggregator.calculate_correlation(
                        dataset_id=dataset_id,
                        column1=col1,
                        column2=col2
                    )

                    if "error" not in corr_result:
                        # Only include significant correlations
                        if abs(corr_result.get("correlation", 0)) > 0.5:
                            correlations.append(corr_result)
                            count += 1

                except Exception as e:
                    logger.warning(f"Failed to calculate correlation for {col1} and {col2}: {e}")

        return correlations

    async def _detect_anomalies(
        self,
        dataset_id: UUID,
        summary: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect anomalies in numeric columns."""
        anomalies = []
        numeric_columns = summary.get("numeric_columns", [])

        # Limit to first few columns
        for col in numeric_columns[:5]:
            try:
                outliers = await self.aggregator.detect_outliers(
                    dataset_id=dataset_id,
                    column=col,
                    method="iqr"
                )

                if "error" not in outliers and outliers.get("outlier_count", 0) > 0:
                    anomalies.append({
                        "column": col,
                        "outlier_count": outliers["outlier_count"],
                        "total_records": outliers["total_records"],
                        "method": outliers["method"]
                    })

            except Exception as e:
                logger.warning(f"Failed to detect outliers for {col}: {e}")

        return anomalies

    def _build_insight_prompt(
        self,
        summary: dict[str, Any],
        trends: list[dict[str, Any]],
        correlations: list[dict[str, Any]],
        anomalies: list[dict[str, Any]]
    ) -> str:
        """Build the insight generation prompt."""
        # Format summary
        dataset_summary = f"""
Dataset: {summary.get('dataset_name', 'Unknown')}
Rows: {summary.get('row_count', 0):,}
Columns: {summary.get('column_count', 0)}
Data Quality Score: {summary.get('data_quality_score', 0)}/100
"""

        # Format trends
        trends_text = "No time-series trends analyzed."
        if trends:
            trends_text = "\n".join([
                f"- {t['metric_column']} over {t['time_column']}: {t['data_points']} data points"
                for t in trends
            ])

        # Format correlations
        correlations_text = "No significant correlations found."
        if correlations:
            correlations_text = "\n".join([
                f"- {c['column1']} and {c['column2']}: r={c['correlation']:.3f} ({c['strength']})"
                for c in correlations
            ])

        # Format anomalies
        anomalies_text = "No anomalies detected."
        if anomalies:
            anomalies_text = "\n".join([
                f"- {a['column']}: {a['outlier_count']} outliers out of {a['total_records']} records"
                for a in anomalies
            ])

        # Build full prompt
        prompt = INSIGHT_GENERATION_PROMPT.format(
            dataset_summary=dataset_summary,
            statistical_analysis=f"Quality Score: {summary.get('data_quality_score', 0)}/100",
            correlations=correlations_text,
            trends=trends_text
        )

        # Add anomalies section
        prompt += f"\n\nAnomalies Detected:\n{anomalies_text}"

        return prompt

    def _generate_fallback_insights(
        self,
        summary: dict[str, Any],
        trends: list[dict[str, Any]],
        correlations: list[dict[str, Any]],
        anomalies: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Generate rule-based insights as fallback."""
        insights = []

        # Data quality insight
        quality_score = summary.get("data_quality_score", 0)
        if quality_score < 80:
            insights.append({
                "type": "summary",
                "title": "Data Quality Needs Attention",
                "description": f"The dataset has a quality score of {quality_score}/100. Consider reviewing missing values and data consistency.",
                "confidence": 0.9,
                "supporting_data": {"quality_score": quality_score},
                "suggested_action": "Review missing values and perform data cleaning."
            })

        # Correlation insights
        for corr in correlations[:2]:
            insights.append({
                "type": "correlation",
                "title": f"Strong Correlation: {corr['column1']} and {corr['column2']}",
                "description": f"These columns show a {corr['strength']} {corr['direction']} correlation (r={corr['correlation']:.3f}).",
                "confidence": min(abs(corr['correlation']), 0.95),
                "supporting_data": corr,
                "suggested_action": f"Investigate the relationship between {corr['column1']} and {corr['column2']}."
            })

        # Anomaly insights
        if anomalies:
            total_anomalies = sum(a["outlier_count"] for a in anomalies)
            insights.append({
                "type": "anomaly",
                "title": f"Outliers Detected in {len(anomalies)} Columns",
                "description": f"Found {total_anomalies} total outliers across multiple columns. These may indicate data quality issues or interesting patterns.",
                "confidence": 0.8,
                "supporting_data": {"anomalies": anomalies},
                "suggested_action": "Review outliers to determine if they are errors or legitimate extreme values."
            })

        return insights

    async def _save_insights_to_db(
        self,
        dataset_id: UUID,
        organization_id: UUID,
        insights: list[dict[str, Any]]
    ):
        """Save insights to database."""
        for insight_data in insights:
            try:
                # Map insight type string to enum
                insight_type_str = insight_data.get("type", "summary")
                insight_type = InsightType(insight_type_str) if insight_type_str in [t.value for t in InsightType] else InsightType.SUMMARY

                insight = Insight(
                    dataset_id=dataset_id,
                    organization_id=organization_id,
                    insight_type=insight_type,
                    title=insight_data.get("title", "Insight"),
                    description=insight_data.get("description", ""),
                    confidence=insight_data.get("confidence", 0.5),
                    data_support=insight_data.get("supporting_data", {}),
                    suggested_action=insight_data.get("suggested_action"),
                    generated_by=InsightGeneratorEnum.LLM
                )

                self.db.add(insight)

            except Exception as e:
                logger.error(f"Failed to save insight: {e}")

        await self.db.commit()

    async def _get_sample_data(
        self,
        dataset_id: UUID,
        limit: int = 10
    ) -> list[dict[str, Any]]:
        """Get sample data records."""
        from sqlalchemy import select, text
        from app.models import Record

        query = select(Record.data).where(
            Record.dataset_id == dataset_id,
            Record.is_valid == True
        ).limit(limit)

        result = await self.db.execute(query)
        rows = result.scalars().all()

        return [row for row in rows if row]

    def _format_column_stats(self, columns: dict[str, Any]) -> str:
        """Format column statistics for prompts."""
        lines = []
        for col_name, col_info in columns.items():
            col_type = col_info.get("type", "unknown")
            stats = col_info.get("stats", {})

            if col_type == "numeric" and stats:
                lines.append(f"{col_name} ({col_type}): mean={stats.get('mean', 0):.2f}, median={stats.get('median', 0):.2f}")
            elif col_type in ["categorical", "text"] and stats:
                lines.append(f"{col_name} ({col_type}): {stats.get('unique_values', 0)} unique values")
            else:
                lines.append(f"{col_name} ({col_type})")

        return "\n  ".join(lines)


# Factory function
async def get_insight_generator(db: AsyncSession) -> InsightGeneratorService:
    """
    Get insight generator instance.

    Args:
        db: Database session

    Returns:
        InsightGeneratorService instance
    """
    return InsightGeneratorService(db)
