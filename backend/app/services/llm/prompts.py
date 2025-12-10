"""
LLM prompt templates for AI-powered data insights.

Provides structured prompts for various data analysis tasks including
summaries, insights, chart suggestions, anomaly detection, and Q&A.
"""

from typing import Any


# System prompts for different roles
SYSTEM_PROMPTS = {
    "data_analyst": """You are an expert data analyst with deep knowledge of statistics,
data visualization, and business intelligence. You provide clear, actionable insights
based on data analysis.""",

    "technical_writer": """You are a technical writer skilled at explaining complex
data analysis results in clear, accessible language for business users.""",

    "statistician": """You are a professional statistician with expertise in
statistical analysis, hypothesis testing, and data quality assessment.""",
}


# Dataset Summary Prompt
DATASET_SUMMARY_PROMPT = """Analyze this dataset and provide a comprehensive summary.

Dataset Information:
- Name: {dataset_name}
- Rows: {row_count:,}
- Columns: {column_count}

Schema:
{schema}

Column Statistics:
{column_stats}

Sample Data (first 5 rows):
{sample_data}

Please provide:
1. A brief overview of what this dataset contains
2. Key characteristics of the data
3. Data quality assessment (completeness, potential issues)
4. Notable patterns or initial observations
5. Suggestions for potential analyses

Keep your response concise and business-focused."""


# Insight Generation Prompt
INSIGHT_GENERATION_PROMPT = """Analyze this dataset and generate data-driven insights.

Dataset Summary:
{dataset_summary}

Statistical Analysis:
{statistical_analysis}

Correlations:
{correlations}

Trends:
{trends}

Instructions:
1. Identify 3-5 significant insights from the data
2. Each insight should be:
   - Actionable and relevant to business decisions
   - Supported by the data provided
   - Clear and specific
3. Assign a confidence score (0.0-1.0) based on:
   - Statistical significance
   - Sample size
   - Data quality
   - Clarity of pattern

Respond with a JSON array of insights:
[
  {{
    "type": "trend|correlation|anomaly|summary|recommendation",
    "title": "Brief descriptive title",
    "description": "Detailed explanation of the insight",
    "confidence": 0.85,
    "supporting_data": {{
      "key_metrics": [...],
      "evidence": "..."
    }},
    "suggested_action": "Optional recommendation based on this insight"
  }}
]"""


# Chart Suggestion Prompt
CHART_SUGGESTION_PROMPT = """Recommend the best chart type for visualizing this data.

Dataset Schema:
{schema}

Column Types:
{column_types}

User Question/Goal:
{user_question}

Available Chart Types:
- line: Time series, trends over continuous data
- bar: Comparisons across categories
- pie: Part-to-whole relationships (limited categories)
- scatter: Relationships between two numeric variables
- heatmap: Patterns in 2D data (correlations, time vs category)
- area: Cumulative trends over time
- table: Detailed data inspection

Available Columns:
{available_columns}

Instructions:
1. Recommend the MOST appropriate chart type
2. Specify which columns to use for X and Y axes (or other dimensions)
3. Explain WHY this chart type is best
4. Suggest any additional configuration (grouping, aggregation, filters)

Respond with JSON:
{{
  "chart_type": "bar",
  "x_axis": "column_name",
  "y_axis": "column_name",
  "grouping": "optional_column_name",
  "aggregation": "sum|avg|count|min|max",
  "reasoning": "Explanation of why this visualization is appropriate",
  "alternative_charts": ["line", "area"],
  "confidence": 0.9
}}"""


# Anomaly Detection Prompt
ANOMALY_DETECTION_PROMPT = """Analyze this data for anomalies and provide explanations.

Column: {column_name}
Type: {column_type}

Statistics:
- Mean: {mean}
- Median: {median}
- Std Dev: {std}
- Min: {min_val}
- Max: {max_val}
- Q1: {q1}
- Q3: {q3}

Detected Outliers:
{outliers}

Time Series Context (if applicable):
{time_context}

Instructions:
1. Analyze the detected outliers
2. Classify each anomaly:
   - Data quality issue (error, typo)
   - Legitimate extreme value (rare but valid)
   - Interesting pattern (worthy of investigation)
3. Provide possible explanations
4. Recommend actions (investigate, clean, ignore)

Respond with JSON:
{{
  "summary": "Brief overview of anomalies found",
  "anomaly_count": 5,
  "severity": "low|medium|high",
  "anomalies": [
    {{
      "value": 10000.0,
      "row_number": 42,
      "classification": "legitimate_extreme|data_error|interesting_pattern",
      "explanation": "Why this value is anomalous",
      "confidence": 0.8,
      "recommended_action": "investigate|clean|ignore"
    }}
  ],
  "overall_assessment": "General assessment of data quality for this column"
}}"""


# Data Question Answering Prompt
DATA_QUESTION_PROMPT = """Answer the user's question about their dataset.

Dataset Information:
- Name: {dataset_name}
- Rows: {row_count:,}
- Columns: {column_count}

Schema:
{schema}

Column Statistics:
{column_stats}

Sample Data:
{sample_data}

User Question:
{user_question}

Instructions:
1. Answer the question directly and clearly
2. Reference specific data points from the dataset
3. If the question cannot be fully answered with available data, explain what's missing
4. Provide relevant statistics or examples
5. Suggest follow-up analyses if appropriate

Keep your response conversational but precise. Use numbers and specifics from the data."""


# Correlation Explanation Prompt
CORRELATION_EXPLANATION_PROMPT = """Explain the correlation between two variables.

Variable 1: {column1}
Variable 2: {column2}

Correlation Coefficient: {correlation:.3f}
Sample Size: {sample_size}
Strength: {strength}

Statistics for {column1}:
- Mean: {col1_mean}
- Std: {col1_std}
- Range: {col1_min} to {col1_max}

Statistics for {column2}:
- Mean: {col2_mean}
- Std: {col2_std}
- Range: {col2_min} to {col2_max}

Instructions:
1. Explain what this correlation means in plain language
2. Describe the relationship (positive/negative, strong/weak)
3. Provide real-world interpretation
4. Note any limitations or caveats
5. Suggest potential follow-up analyses

Keep it accessible for non-technical users."""


# Trend Analysis Prompt
TREND_ANALYSIS_PROMPT = """Analyze trends in this time series data.

Column: {column_name}
Time Column: {time_column}
Interval: {interval}

Data Points:
{time_series_data}

Statistics:
- Starting Value: {start_value}
- Ending Value: {end_value}
- Change: {change_value} ({change_percent}%)
- Average Value: {avg_value}
- Volatility (Std): {volatility}

Instructions:
1. Identify the overall trend (increasing, decreasing, stable, volatile)
2. Note any significant changes or inflection points
3. Describe patterns (seasonal, cyclical, irregular)
4. Provide business interpretation
5. Make forecasting recommendations if appropriate

Respond with JSON:
{{
  "trend_direction": "increasing|decreasing|stable|volatile",
  "confidence": 0.85,
  "key_observations": [
    "First key observation",
    "Second key observation"
  ],
  "business_interpretation": "What this means for the business",
  "recommendations": [
    "Specific recommendation based on trend"
  ],
  "forecast_suggestion": "Optional: methodology for forecasting"
}}"""


# Dataset Comparison Prompt
DATASET_COMPARISON_PROMPT = """Compare two datasets and highlight key differences.

Dataset 1:
- Name: {dataset1_name}
- Rows: {dataset1_rows:,}
- Columns: {dataset1_columns}

Dataset 2:
- Name: {dataset2_name}
- Rows: {dataset2_rows:,}
- Columns: {dataset2_columns}

Schema Differences:
{schema_differences}

Distribution Comparisons (for common numeric columns):
{distribution_comparisons}

Instructions:
1. Summarize the main differences between datasets
2. Highlight significant changes in data distributions
3. Identify new or removed columns
4. Note any data quality differences
5. Provide context on what these differences might indicate

Keep the comparison structured and easy to understand."""


# Column Profiling Summary Prompt
COLUMN_PROFILING_SUMMARY_PROMPT = """Provide a detailed profile summary for this column.

Column: {column_name}
Type: {column_type}

Statistics:
{statistics}

Distribution:
{distribution}

Null Analysis:
- Null Count: {null_count}
- Completeness: {completeness}%

{additional_info}

Instructions:
1. Describe the column's characteristics
2. Note data quality (completeness, outliers, consistency)
3. Suggest appropriate uses for this column in analysis
4. Recommend any data cleaning steps if needed
5. Identify potential issues or interesting patterns

Keep it concise and actionable."""


# Chart Configuration Prompt
CHART_CONFIG_PROMPT = """Generate a detailed configuration for a {chart_type} chart.

Data to Visualize:
{data_description}

User Requirements:
{user_requirements}

Available Options:
- Colors: {color_schemes}
- Themes: light, dark
- Aggregations: sum, avg, count, min, max
- Grouping: available
- Stacking: available (for bar/area)

Instructions:
Generate a complete chart configuration including:
1. Axis labels and titles
2. Color scheme selection
3. Legend placement
4. Any special features (stacking, smoothing, etc.)
5. Tooltip configuration

Respond with JSON:
{{
  "title": "Chart title",
  "x_label": "X-axis label",
  "y_label": "Y-axis label",
  "color_scheme": "vibrant",
  "theme": "light",
  "show_legend": true,
  "show_grid": true,
  "special_config": {{
    "stacked": false,
    "smooth": true
  }}
}}"""


# Data Quality Assessment Prompt
DATA_QUALITY_ASSESSMENT_PROMPT = """Assess the overall quality of this dataset.

Dataset: {dataset_name}
Total Records: {row_count:,}
Total Fields: {column_count}

Missing Values:
{missing_analysis}

Outliers Detected:
{outliers_summary}

Column Types Distribution:
{column_types_dist}

Data Completeness: {completeness_score}%

Instructions:
1. Provide an overall data quality score (0-100)
2. Identify major quality issues
3. Assess completeness, consistency, and accuracy
4. Recommend specific cleaning/preparation steps
5. Highlight any columns that need attention

Respond with JSON:
{{
  "quality_score": 85,
  "grade": "A|B|C|D|F",
  "strengths": ["High completeness", "No duplicates"],
  "issues": [
    {{
      "severity": "high|medium|low",
      "description": "Issue description",
      "affected_columns": ["col1", "col2"],
      "recommendation": "How to fix"
    }}
  ],
  "recommended_actions": [
    "Prioritized list of actions to improve quality"
  ],
  "ready_for_analysis": true
}}"""


# Helper function to format data for prompts
def format_schema(columns: list[dict]) -> str:
    """Format schema information for prompts."""
    lines = []
    for col in columns:
        col_type = col.get("type", "unknown")
        col_name = col.get("name", "unknown")
        nullable = " (nullable)" if col.get("nullable", False) else ""
        lines.append(f"  - {col_name}: {col_type}{nullable}")
    return "\n".join(lines)


def format_stats(stats: dict[str, Any]) -> str:
    """Format statistics for prompts."""
    lines = []
    for key, value in stats.items():
        if isinstance(value, float):
            lines.append(f"  {key}: {value:.2f}")
        elif isinstance(value, int):
            lines.append(f"  {key}: {value:,}")
        else:
            lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def format_sample_data(data: list[dict], limit: int = 5) -> str:
    """Format sample data as a readable table."""
    if not data:
        return "  (No sample data available)"

    # Take only first N rows
    sample = data[:limit]

    # Format as simple table
    if sample:
        headers = list(sample[0].keys())
        lines = ["  " + " | ".join(headers)]
        lines.append("  " + "-" * (len(lines[0]) - 2))

        for row in sample:
            values = [str(row.get(h, ""))[:20] for h in headers]  # Truncate long values
            lines.append("  " + " | ".join(values))

        return "\n".join(lines)

    return "  (No data)"


def format_column_list(columns: list[dict]) -> str:
    """Format column list with types."""
    lines = []
    for col in columns:
        col_name = col.get("name", "unknown")
        col_type = col.get("type", "unknown")
        lines.append(f"  - {col_name} ({col_type})")
    return "\n".join(lines)
