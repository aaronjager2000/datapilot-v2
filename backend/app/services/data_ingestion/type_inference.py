"""
Type inference service for analyzing DataFrame columns.

Provides automatic type detection, statistical analysis, and SQL type mapping
for data ingestion and schema generation.
"""

import logging
import re
from collections import Counter
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# Regex patterns for type detection
EMAIL_PATTERN = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)
URL_PATTERN = re.compile(
    r'^https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b'
    r'(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)$'
)
UUID_PATTERN = re.compile(
    r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
    re.IGNORECASE
)
PHONE_PATTERN = re.compile(
    r'^[\+]?[(]?[0-9]{1,4}[)]?[-\s\.]?[(]?[0-9]{1,4}[)]?[-\s\.]?[0-9]{1,9}$'
)


class TypeInferenceError(Exception):
    """Base exception for type inference errors."""
    pass


def infer_column_types(
    dataframe: pd.DataFrame,
    sample_size: int = 1000,
    confidence_threshold: float = 0.8
) -> Dict[str, Dict[str, Any]]:
    """
    Infer the types of all columns in a DataFrame with confidence scores.

    Args:
        dataframe: Pandas DataFrame to analyze
        sample_size: Number of rows to sample for inference (None = all rows)
        confidence_threshold: Minimum confidence to accept a type (0.0-1.0)

    Returns:
        Dictionary mapping column names to type information:
        {
            'column_name': {
                'inferred_type': str,  # e.g., 'integer', 'email', 'datetime'
                'confidence': float,    # 0.0 to 1.0
                'pandas_dtype': str,    # Original pandas dtype
                'nullable': bool,       # Whether column has null values
                'null_count': int,      # Number of null values
                'sample_values': list   # Sample of values
            }
        }

    Raises:
        TypeInferenceError: If inference fails
    """
    if dataframe is None or dataframe.empty:
        raise TypeInferenceError("DataFrame is empty or None")

    try:
        result = {}
        
        for column in dataframe.columns:
            logger.debug(f"Inferring type for column: {column}")
            
            # Get column data
            col_data = dataframe[column]
            
            # Sample data if dataset is large
            if sample_size and len(col_data) > sample_size:
                col_sample = col_data.sample(n=sample_size, random_state=42)
            else:
                col_sample = col_data
            
            # Count nulls
            null_count = col_sample.isna().sum()
            non_null_sample = col_sample.dropna()
            
            if len(non_null_sample) == 0:
                # All null column
                result[column] = {
                    'inferred_type': 'null',
                    'confidence': 1.0,
                    'pandas_dtype': str(col_data.dtype),
                    'nullable': True,
                    'null_count': int(null_count),
                    'sample_values': []
                }
                continue
            
            # Infer type
            inferred_type, confidence = _infer_single_column_type(non_null_sample)
            
            # Get sample values (up to 5)
            sample_values = non_null_sample.head(5).tolist()
            
            result[column] = {
                'inferred_type': inferred_type,
                'confidence': confidence,
                'pandas_dtype': str(col_data.dtype),
                'nullable': null_count > 0,
                'null_count': int(null_count),
                'sample_values': sample_values
            }
        
        logger.info(f"Successfully inferred types for {len(result)} columns")
        return result
    
    except Exception as e:
        logger.error(f"Failed to infer column types: {e}", exc_info=True)
        raise TypeInferenceError(f"Type inference failed: {str(e)}")


def _infer_single_column_type(series: pd.Series) -> Tuple[str, float]:
    """
    Infer the type of a single column (series).

    Args:
        series: Pandas Series with non-null values

    Returns:
        Tuple of (inferred_type, confidence_score)
    """
    # Convert to string for pattern matching
    str_series = series.astype(str)
    total_count = len(str_series)
    
    # Check for boolean (case-insensitive)
    bool_values = {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0'}
    bool_matches = str_series.str.lower().isin(bool_values).sum()
    if bool_matches / total_count >= 0.9:
        return 'boolean', bool_matches / total_count
    
    # Check for datetime (pandas already parsed or can parse)
    if pd.api.types.is_datetime64_any_dtype(series):
        return 'datetime', 1.0
    
    # Try to parse as datetime
    try:
        datetime_series = pd.to_datetime(series, errors='coerce')
        datetime_matches = datetime_series.notna().sum()
        if datetime_matches / total_count >= 0.9:
            # Check if it's date only (no time component)
            has_time = False
            for dt in datetime_series.dropna().head(100):
                if dt.hour != 0 or dt.minute != 0 or dt.second != 0:
                    has_time = True
                    break
            
            if has_time:
                return 'datetime', datetime_matches / total_count
            else:
                return 'date', datetime_matches / total_count
    except:
        pass
    
    # Check for numeric types
    if pd.api.types.is_numeric_dtype(series):
        # Check if integer
        if pd.api.types.is_integer_dtype(series):
            return 'integer', 1.0
        
        # Check if float values are actually integers
        try:
            if (series == series.astype(int)).all():
                return 'integer', 1.0
        except:
            pass
        
        return 'float', 1.0
    
    # Try to convert to numeric
    numeric_series = pd.to_numeric(series, errors='coerce')
    numeric_matches = numeric_series.notna().sum()
    if numeric_matches / total_count >= 0.9:
        # Check if all are integers
        try:
            non_null_numeric = numeric_series.dropna()
            if len(non_null_numeric) > 0 and (non_null_numeric == non_null_numeric.astype(int)).all():
                return 'integer', numeric_matches / total_count
        except:
            pass
        
        return 'float', numeric_matches / total_count
    
    # Check for email
    email_matches = str_series.apply(lambda x: bool(EMAIL_PATTERN.match(str(x).strip()))).sum()
    if email_matches / total_count >= 0.8:
        return 'email', email_matches / total_count
    
    # Check for URL
    url_matches = str_series.apply(lambda x: bool(URL_PATTERN.match(str(x).strip()))).sum()
    if url_matches / total_count >= 0.8:
        return 'url', url_matches / total_count
    
    # Check for UUID
    uuid_matches = str_series.apply(lambda x: bool(UUID_PATTERN.match(str(x).strip()))).sum()
    if uuid_matches / total_count >= 0.8:
        return 'uuid', uuid_matches / total_count
    
    # Check for phone number
    phone_matches = str_series.apply(lambda x: bool(PHONE_PATTERN.match(str(x).strip()))).sum()
    if phone_matches / total_count >= 0.8:
        return 'phone', phone_matches / total_count
    
    # Default to string
    return 'string', 1.0


def get_column_stats(
    dataframe: pd.DataFrame,
    column: str,
    include_percentiles: bool = True
) -> Dict[str, Any]:
    """
    Get statistical information about a specific column.

    Args:
        dataframe: Pandas DataFrame
        column: Column name to analyze
        include_percentiles: Whether to include percentile statistics

    Returns:
        Dictionary with statistics based on column type:
        - For numeric columns: min, max, mean, median, std, percentiles
        - For string columns: max_length, min_length, avg_length, unique_count, most_common
        - For all columns: null_count, null_percentage, total_count, dtype

    Raises:
        TypeInferenceError: If column doesn't exist or analysis fails
    """
    if column not in dataframe.columns:
        raise TypeInferenceError(f"Column '{column}' not found in DataFrame")
    
    try:
        col_data = dataframe[column]
        total_count = len(col_data)
        null_count = col_data.isna().sum()
        null_percentage = (null_count / total_count * 100) if total_count > 0 else 0
        non_null_data = col_data.dropna()
        
        stats = {
            'column_name': column,
            'total_count': int(total_count),
            'null_count': int(null_count),
            'null_percentage': float(null_percentage),
            'non_null_count': int(len(non_null_data)),
            'dtype': str(col_data.dtype),
        }
        
        # Numeric statistics
        if pd.api.types.is_numeric_dtype(non_null_data) and len(non_null_data) > 0:
            stats['min'] = float(non_null_data.min())
            stats['max'] = float(non_null_data.max())
            stats['mean'] = float(non_null_data.mean())
            stats['median'] = float(non_null_data.median())
            stats['std'] = float(non_null_data.std()) if len(non_null_data) > 1 else 0.0
            stats['sum'] = float(non_null_data.sum())
            
            if include_percentiles:
                stats['percentile_25'] = float(non_null_data.quantile(0.25))
                stats['percentile_75'] = float(non_null_data.quantile(0.75))
                stats['percentile_90'] = float(non_null_data.quantile(0.90))
                stats['percentile_95'] = float(non_null_data.quantile(0.95))
            
            stats['unique_count'] = int(non_null_data.nunique())
            stats['type_category'] = 'numeric'
        
        # String statistics
        elif len(non_null_data) > 0:
            str_data = non_null_data.astype(str)
            lengths = str_data.str.len()
            
            stats['max_length'] = int(lengths.max()) if len(lengths) > 0 else 0
            stats['min_length'] = int(lengths.min()) if len(lengths) > 0 else 0
            stats['avg_length'] = float(lengths.mean()) if len(lengths) > 0 else 0.0
            stats['unique_count'] = int(str_data.nunique())
            
            # Most common values (up to 10)
            value_counts = str_data.value_counts().head(10)
            stats['most_common'] = [
                {'value': str(val), 'count': int(count)}
                for val, count in value_counts.items()
            ]
            
            # Calculate cardinality ratio (unique / total)
            stats['cardinality_ratio'] = float(stats['unique_count'] / len(str_data))
            stats['type_category'] = 'string'
        
        # Datetime statistics
        if pd.api.types.is_datetime64_any_dtype(non_null_data) and len(non_null_data) > 0:
            stats['min_date'] = str(non_null_data.min())
            stats['max_date'] = str(non_null_data.max())
            stats['date_range_days'] = (non_null_data.max() - non_null_data.min()).days
            stats['unique_count'] = int(non_null_data.nunique())
            stats['type_category'] = 'datetime'
        
        logger.debug(f"Generated statistics for column '{column}'")
        return stats
    
    except Exception as e:
        logger.error(f"Failed to get stats for column '{column}': {e}")
        raise TypeInferenceError(f"Failed to analyze column '{column}': {str(e)}")


def suggest_data_types(
    dataframe: pd.DataFrame,
    inferred_types: Optional[Dict[str, Dict[str, Any]]] = None
) -> Dict[str, str]:
    """
    Suggest PostgreSQL data types for DataFrame columns.

    Args:
        dataframe: Pandas DataFrame
        inferred_types: Optional pre-computed type inference results

    Returns:
        Dictionary mapping column names to suggested PostgreSQL types:
        {
            'column_name': 'VARCHAR(255)',
            'age': 'INTEGER',
            'price': 'DECIMAL(10,2)',
            'created_at': 'TIMESTAMP'
        }

    Raises:
        TypeInferenceError: If type suggestion fails
    """
    try:
        # Get inferred types if not provided
        if inferred_types is None:
            inferred_types = infer_column_types(dataframe)
        
        suggested_types = {}
        
        for column, type_info in inferred_types.items():
            inferred_type = type_info['inferred_type']
            pandas_dtype = type_info['pandas_dtype']
            
            # Get column stats for string length determination
            if inferred_type == 'string':
                try:
                    stats = get_column_stats(dataframe, column, include_percentiles=False)
                    max_length = stats.get('max_length', 255)
                    
                    # Add buffer to max length (20% or minimum 50)
                    suggested_length = max(int(max_length * 1.2), max_length + 50, 50)
                    
                    # Cap at reasonable limit
                    if suggested_length > 1000:
                        sql_type = 'TEXT'
                    else:
                        sql_type = f'VARCHAR({min(suggested_length, 1000)})'
                except:
                    sql_type = 'VARCHAR(255)'
            
            else:
                # Map inferred types to PostgreSQL types
                sql_type = _map_to_postgres_type(inferred_type, pandas_dtype)
            
            suggested_types[column] = sql_type
        
        logger.info(f"Suggested PostgreSQL types for {len(suggested_types)} columns")
        return suggested_types
    
    except Exception as e:
        logger.error(f"Failed to suggest data types: {e}")
        raise TypeInferenceError(f"Type suggestion failed: {str(e)}")


def _map_to_postgres_type(inferred_type: str, pandas_dtype: str) -> str:
    """
    Map inferred type to PostgreSQL data type.

    Args:
        inferred_type: The inferred semantic type
        pandas_dtype: The pandas dtype string

    Returns:
        PostgreSQL type string
    """
    type_mapping = {
        'integer': 'INTEGER',
        'float': 'DOUBLE PRECISION',
        'boolean': 'BOOLEAN',
        'date': 'DATE',
        'datetime': 'TIMESTAMP',
        'string': 'TEXT',
        'email': 'VARCHAR(255)',
        'url': 'TEXT',
        'uuid': 'UUID',
        'phone': 'VARCHAR(20)',
        'null': 'TEXT'
    }
    
    # Get base type
    sql_type = type_mapping.get(inferred_type, 'TEXT')
    
    # Handle specific pandas types for better precision
    if 'int8' in pandas_dtype or 'int16' in pandas_dtype:
        sql_type = 'SMALLINT'
    elif 'int32' in pandas_dtype:
        sql_type = 'INTEGER'
    elif 'int64' in pandas_dtype:
        sql_type = 'BIGINT'
    elif 'float32' in pandas_dtype:
        sql_type = 'REAL'
    elif 'float64' in pandas_dtype:
        sql_type = 'DOUBLE PRECISION'
    
    return sql_type


def analyze_dataframe(
    dataframe: pd.DataFrame,
    detailed: bool = True
) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a DataFrame.

    Args:
        dataframe: Pandas DataFrame to analyze
        detailed: Whether to include detailed statistics for each column

    Returns:
        Dictionary with complete DataFrame analysis:
        {
            'shape': {'rows': int, 'columns': int},
            'columns': [...],
            'inferred_types': {...},
            'suggested_sql_types': {...},
            'column_stats': {...},  # Only if detailed=True
            'memory_usage': int
        }

    Raises:
        TypeInferenceError: If analysis fails
    """
    try:
        logger.info(f"Analyzing DataFrame: {dataframe.shape[0]} rows x {dataframe.shape[1]} columns")
        
        # Basic info
        analysis = {
            'shape': {
                'rows': int(dataframe.shape[0]),
                'columns': int(dataframe.shape[1])
            },
            'columns': list(dataframe.columns),
            'memory_usage_bytes': int(dataframe.memory_usage(deep=True).sum()),
            'memory_usage_mb': round(dataframe.memory_usage(deep=True).sum() / (1024 * 1024), 2)
        }
        
        # Infer types
        inferred_types = infer_column_types(dataframe)
        analysis['inferred_types'] = inferred_types
        
        # Suggest SQL types
        suggested_types = suggest_data_types(dataframe, inferred_types)
        analysis['suggested_sql_types'] = suggested_types
        
        # Detailed column statistics
        if detailed:
            column_stats = {}
            for column in dataframe.columns:
                try:
                    column_stats[column] = get_column_stats(dataframe, column)
                except Exception as e:
                    logger.warning(f"Failed to get stats for column '{column}': {e}")
                    column_stats[column] = {'error': str(e)}
            
            analysis['column_stats'] = column_stats
        
        logger.info("DataFrame analysis complete")
        return analysis
    
    except Exception as e:
        logger.error(f"Failed to analyze DataFrame: {e}", exc_info=True)
        raise TypeInferenceError(f"DataFrame analysis failed: {str(e)}")


def validate_type_conversion(
    dataframe: pd.DataFrame,
    column: str,
    target_type: str
) -> Dict[str, Any]:
    """
    Validate if a column can be safely converted to a target type.

    Args:
        dataframe: Pandas DataFrame
        column: Column name to validate
        target_type: Target type ('integer', 'float', 'boolean', 'datetime', etc.)

    Returns:
        Dictionary with validation results:
        {
            'can_convert': bool,
            'conversion_rate': float,  # Percentage of values that can convert
            'failed_values': list,     # Sample of values that would fail
            'null_handling': str       # How nulls would be handled
        }

    Raises:
        TypeInferenceError: If validation fails
    """
    if column not in dataframe.columns:
        raise TypeInferenceError(f"Column '{column}' not found")
    
    try:
        col_data = dataframe[column]
        non_null_data = col_data.dropna()
        total_non_null = len(non_null_data)
        
        if total_non_null == 0:
            return {
                'can_convert': True,
                'conversion_rate': 1.0,
                'failed_values': [],
                'null_handling': 'All values are null'
            }
        
        failed_values = []
        successful_conversions = 0
        
        # Test conversion based on target type
        if target_type == 'integer':
            numeric_series = pd.to_numeric(non_null_data, errors='coerce')
            successful_conversions = numeric_series.notna().sum()
            failed_mask = numeric_series.isna()
            
        elif target_type == 'float':
            numeric_series = pd.to_numeric(non_null_data, errors='coerce')
            successful_conversions = numeric_series.notna().sum()
            failed_mask = numeric_series.isna()
            
        elif target_type == 'boolean':
            bool_values = {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0', 1, 0, True, False}
            str_series = non_null_data.astype(str).str.lower()
            successful_conversions = str_series.isin([str(v).lower() for v in bool_values]).sum()
            failed_mask = ~str_series.isin([str(v).lower() for v in bool_values])
            
        elif target_type in ['date', 'datetime']:
            datetime_series = pd.to_datetime(non_null_data, errors='coerce')
            successful_conversions = datetime_series.notna().sum()
            failed_mask = datetime_series.isna()
            
        else:
            # String conversion always works
            return {
                'can_convert': True,
                'conversion_rate': 1.0,
                'failed_values': [],
                'null_handling': 'All values can be converted to string'
            }
        
        # Get sample of failed values
        if failed_mask.any():
            failed_values = non_null_data[failed_mask].head(10).tolist()
        
        conversion_rate = successful_conversions / total_non_null if total_non_null > 0 else 0
        can_convert = conversion_rate >= 0.95  # 95% threshold
        
        return {
            'can_convert': can_convert,
            'conversion_rate': float(conversion_rate),
            'successful_count': int(successful_conversions),
            'failed_count': int(total_non_null - successful_conversions),
            'failed_values': [str(v) for v in failed_values],
            'null_handling': f"{col_data.isna().sum()} null values will remain null"
        }
    
    except Exception as e:
        logger.error(f"Failed to validate type conversion: {e}")
        raise TypeInferenceError(f"Type conversion validation failed: {str(e)}")
