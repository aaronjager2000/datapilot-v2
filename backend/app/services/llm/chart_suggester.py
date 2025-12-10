"""
Chart Suggester service for intelligent visualization recommendations.

Provides rule-based and AI-powered chart suggestions based on data
characteristics, user questions, and best practices.
"""

import logging
from typing import Any, Optional, Literal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Dataset, ChartType
from app.services.llm.client import get_llm_client, LLMClient
from app.services.llm.prompts import CHART_SUGGESTION_PROMPT, SYSTEM_PROMPTS, format_schema, format_column_list
from app.services.visualization.summary import SummaryService


logger = logging.getLogger(__name__)


class ChartSuggesterService:
    """
    Service for suggesting appropriate visualizations.

    Combines rule-based heuristics with optional AI enhancement to
    recommend the best charts for datasets and user questions.
    """

    def __init__(self, db: AsyncSession, llm_client: Optional[LLMClient] = None):
        """
        Initialize chart suggester.

        Args:
            db: Database session
            llm_client: Optional LLM client for AI-powered suggestions
        """
        self.db = db
        self.llm_client = llm_client or get_llm_client()
        self.summary_service = SummaryService(db)

    async def suggest_visualizations(
        self,
        dataset_id: UUID,
        use_ai: bool = False,
        max_suggestions: int = 5
    ) -> list[dict[str, Any]]:
        """
        Generate visualization suggestions for a dataset.

        Uses rule-based heuristics to generate chart suggestions based on:
        - Data types (numeric, categorical, datetime)
        - Column relationships
        - Dataset characteristics

        Args:
            dataset_id: Dataset UUID
            use_ai: Whether to enhance suggestions with AI
            max_suggestions: Maximum number of suggestions to return

        Returns:
            List of visualization suggestions with configs
        """
        logger.info(f"Generating chart suggestions for dataset {dataset_id}")

        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get dataset summary
        summary = await self.summary_service.generate_dataset_summary(dataset_id)

        # Generate rule-based suggestions
        suggestions = self._generate_rule_based_suggestions(summary, dataset)

        # Optionally enhance with AI
        if use_ai and suggestions:
            try:
                suggestions = await self._enhance_with_ai(dataset, summary, suggestions)
            except Exception as e:
                logger.warning(f"AI enhancement failed: {e}. Using rule-based suggestions.")

        # Limit results
        return suggestions[:max_suggestions]

    async def suggest_chart_for_question(
        self,
        dataset_id: UUID,
        question: str
    ) -> dict[str, Any]:
        """
        Suggest a chart based on user's question or intent.

        Uses AI to parse the question and determine the best visualization.

        Args:
            dataset_id: Dataset UUID
            question: User's question or visualization intent

        Returns:
            Chart suggestion with configuration
        """
        logger.info(f"Suggesting chart for question: {question}")

        # Get dataset
        dataset = await self.db.get(Dataset, dataset_id)
        if not dataset:
            raise ValueError(f"Dataset {dataset_id} not found")

        # Get schema info
        schema_info = dataset.schema_info or {}
        columns = schema_info.get("columns", [])

        # Determine column types
        column_types = {
            col["name"]: col.get("type", "unknown")
            for col in columns
        }

        # Build AI prompt
        prompt = CHART_SUGGESTION_PROMPT.format(
            schema=format_schema(columns),
            column_types="\n".join([f"  - {name}: {type_}" for name, type_ in column_types.items()]),
            user_question=question,
            available_columns=format_column_list(columns)
        )

        try:
            # Get suggestion from AI
            schema = {
                "type": "object",
                "properties": {
                    "chart_type": {"type": "string"},
                    "x_axis": {"type": "string"},
                    "y_axis": {"type": "string"},
                    "grouping": {"type": "string"},
                    "aggregation": {"type": "string"},
                    "reasoning": {"type": "string"},
                    "alternative_charts": {"type": "array"},
                    "confidence": {"type": "number"}
                }
            }

            suggestion = await self.llm_client.generate_structured_output(
                prompt=prompt,
                schema=schema,
                system_prompt=SYSTEM_PROMPTS["data_analyst"],
                max_tokens=800,
                temperature=0.7
            )

            # Add dataset info
            suggestion["dataset_id"] = str(dataset_id)
            suggestion["dataset_name"] = dataset.name

            return suggestion

        except Exception as e:
            logger.error(f"Failed to generate AI chart suggestion: {e}")
            # Fallback to basic suggestion
            return self._generate_fallback_suggestion(question, columns)

    def _generate_rule_based_suggestions(
        self,
        summary: dict[str, Any],
        dataset: Dataset
    ) -> list[dict[str, Any]]:
        """Generate chart suggestions using rule-based heuristics."""
        suggestions = []
        columns_info = summary.get("columns", {})
        numeric_columns = summary.get("numeric_columns", [])
        categorical_columns = summary.get("categorical_columns", [])

        # Identify date/time columns
        datetime_columns = [
            col_name for col_name, col_info in columns_info.items()
            if col_info.get("type") in ["date", "datetime", "timestamp"]
        ]

        # Rule 1: Time-series line chart
        if datetime_columns and numeric_columns:
            for datetime_col in datetime_columns[:1]:  # Take first datetime column
                for num_col in numeric_columns[:2]:  # Top 2 numeric columns
                    suggestions.append({
                        "chart_type": "line",
                        "title": f"{num_col} Over Time",
                        "x_axis": datetime_col,
                        "y_axis": num_col,
                        "aggregation": "avg",
                        "reasoning": "Time-series data is best visualized with line charts to show trends.",
                        "confidence": 0.9,
                        "priority": 1
                    })

        # Rule 2: Categorical + Numeric = Bar chart
        if categorical_columns and numeric_columns:
            for cat_col in categorical_columns[:2]:
                # Check cardinality
                col_info = columns_info.get(cat_col, {})
                unique_values = col_info.get("stats", {}).get("unique_values", 0)

                # Only suggest if reasonable number of categories
                if unique_values > 0 and unique_values <= 20:
                    for num_col in numeric_columns[:2]:
                        suggestions.append({
                            "chart_type": "bar",
                            "title": f"{num_col} by {cat_col}",
                            "x_axis": cat_col,
                            "y_axis": num_col,
                            "aggregation": "sum",
                            "reasoning": f"Bar charts effectively compare {num_col} across {unique_values} categories.",
                            "confidence": 0.85,
                            "priority": 2
                        })

        # Rule 3: Two numeric columns = Scatter plot
        if len(numeric_columns) >= 2:
            # Take the first two numeric columns
            col1, col2 = numeric_columns[0], numeric_columns[1]
            suggestions.append({
                "chart_type": "scatter",
                "title": f"{col1} vs {col2}",
                "x_axis": col1,
                "y_axis": col2,
                "reasoning": f"Scatter plots reveal relationships between {col1} and {col2}.",
                "confidence": 0.8,
                "priority": 3
            })

        # Rule 4: Single numeric column = Histogram (distribution)
        if numeric_columns:
            for num_col in numeric_columns[:1]:
                suggestions.append({
                    "chart_type": "bar",  # Using bar chart for distribution
                    "title": f"Distribution of {num_col}",
                    "x_axis": num_col,
                    "y_axis": "count",
                    "aggregation": "count",
                    "reasoning": f"Shows the distribution of values in {num_col}.",
                    "confidence": 0.75,
                    "priority": 4
                })

        # Rule 5: Categorical column for composition = Pie chart
        if categorical_columns:
            for cat_col in categorical_columns[:1]:
                col_info = columns_info.get(cat_col, {})
                unique_values = col_info.get("stats", {}).get("unique_values", 0)

                # Pie charts work best with 3-7 categories
                if 3 <= unique_values <= 10:
                    suggestions.append({
                        "chart_type": "pie",
                        "title": f"Composition by {cat_col}",
                        "values_column": cat_col,
                        "labels_column": cat_col,
                        "reasoning": f"Pie chart shows proportions across {unique_values} categories.",
                        "confidence": 0.7,
                        "priority": 5
                    })

        # Rule 6: Time-series + area chart (for cumulative)
        if datetime_columns and numeric_columns:
            for datetime_col in datetime_columns[:1]:
                for num_col in numeric_columns[:1]:
                    suggestions.append({
                        "chart_type": "area",
                        "title": f"Cumulative {num_col}",
                        "x_axis": datetime_col,
                        "y_axis": num_col,
                        "aggregation": "sum",
                        "reasoning": "Area charts emphasize magnitude and cumulative values over time.",
                        "confidence": 0.75,
                        "priority": 6
                    })

        # Sort by priority and confidence
        suggestions.sort(key=lambda x: (x.get("priority", 999), -x.get("confidence", 0)))

        return suggestions

    async def _enhance_with_ai(
        self,
        dataset: Dataset,
        summary: dict[str, Any],
        suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Enhance suggestions with AI analysis."""
        # Build prompt with existing suggestions
        suggestions_text = "\n".join([
            f"{i+1}. {s['chart_type']}: {s['title']} (confidence: {s['confidence']})"
            for i, s in enumerate(suggestions[:5])
        ])

        prompt = f"""Review and enhance these visualization suggestions for a dataset.

Dataset: {dataset.name}
Rows: {summary.get('row_count', 0):,}
Columns: {summary.get('column_count', 0)}

Current Suggestions:
{suggestions_text}

Numeric columns: {', '.join(summary.get('numeric_columns', []))}
Categorical columns: {', '.join(summary.get('categorical_columns', []))}

Please:
1. Validate the suggestions
2. Improve the reasoning/titles where needed
3. Suggest any additional interesting visualizations
4. Rank by usefulness

Keep the same format but enhance the descriptions."""

        try:
            enhancement = await self.llm_client.generate_completion(
                prompt=prompt,
                system_prompt=SYSTEM_PROMPTS["data_analyst"],
                max_tokens=1000,
                temperature=0.7
            )

            # For now, just add AI feedback to first suggestion
            if suggestions:
                suggestions[0]["ai_enhancement"] = enhancement

        except Exception as e:
            logger.warning(f"AI enhancement failed: {e}")

        return suggestions

    def _generate_fallback_suggestion(
        self,
        question: str,
        columns: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Generate a basic suggestion when AI fails."""
        # Simple intent detection
        question_lower = question.lower()

        # Look for keywords
        if any(word in question_lower for word in ["trend", "over time", "change", "growth"]):
            intent = "trend"
            suggested_chart = "line"
        elif any(word in question_lower for word in ["compare", "versus", "vs", "difference"]):
            intent = "comparison"
            suggested_chart = "bar"
        elif any(word in question_lower for word in ["relationship", "correlation", "related"]):
            intent = "relationship"
            suggested_chart = "scatter"
        elif any(word in question_lower for word in ["distribution", "spread", "range"]):
            intent = "distribution"
            suggested_chart = "bar"
        elif any(word in question_lower for word in ["composition", "breakdown", "proportion"]):
            intent = "composition"
            suggested_chart = "pie"
        else:
            intent = "general"
            suggested_chart = "bar"

        # Pick first suitable columns
        numeric_cols = [c for c in columns if c.get("type") == "numeric"]
        categorical_cols = [c for c in columns if c.get("type") == "categorical"]
        datetime_cols = [c for c in columns if c.get("type") in ["date", "datetime"]]

        x_axis = None
        y_axis = None

        if suggested_chart == "line" and datetime_cols and numeric_cols:
            x_axis = datetime_cols[0]["name"]
            y_axis = numeric_cols[0]["name"]
        elif suggested_chart == "scatter" and len(numeric_cols) >= 2:
            x_axis = numeric_cols[0]["name"]
            y_axis = numeric_cols[1]["name"]
        elif categorical_cols and numeric_cols:
            x_axis = categorical_cols[0]["name"]
            y_axis = numeric_cols[0]["name"]

        return {
            "chart_type": suggested_chart,
            "x_axis": x_axis,
            "y_axis": y_axis,
            "reasoning": f"Based on your question about {intent}, a {suggested_chart} chart is recommended.",
            "confidence": 0.6,
            "fallback": True
        }

    def classify_visualization_intent(self, question: str) -> dict[str, Any]:
        """
        Classify user's visualization intent from question.

        Args:
            question: User's question

        Returns:
            Dict with intent classification
        """
        question_lower = question.lower()

        intents = {
            "trend": ["trend", "over time", "change", "growth", "decline", "historical"],
            "comparison": ["compare", "versus", "vs", "difference", "better", "worse"],
            "relationship": ["relationship", "correlation", "related", "connected", "association"],
            "distribution": ["distribution", "spread", "range", "variance", "outliers"],
            "composition": ["composition", "breakdown", "proportion", "percentage", "share"],
            "ranking": ["top", "bottom", "highest", "lowest", "rank", "best", "worst"]
        }

        detected_intents = []
        for intent_type, keywords in intents.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_intents.append(intent_type)

        primary_intent = detected_intents[0] if detected_intents else "general"

        # Map intent to recommended chart types
        intent_to_charts = {
            "trend": ["line", "area"],
            "comparison": ["bar", "line"],
            "relationship": ["scatter", "heatmap"],
            "distribution": ["bar", "area"],
            "composition": ["pie", "doughnut", "bar"],
            "ranking": ["bar"],
            "general": ["bar", "line"]
        }

        return {
            "primary_intent": primary_intent,
            "all_intents": detected_intents,
            "recommended_charts": intent_to_charts.get(primary_intent, ["bar"]),
            "confidence": 0.8 if detected_intents else 0.5
        }


# Factory function
async def get_chart_suggester(db: AsyncSession) -> ChartSuggesterService:
    """
    Get chart suggester instance.

    Args:
        db: Database session

    Returns:
        ChartSuggesterService instance
    """
    return ChartSuggesterService(db)
