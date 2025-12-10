"""
Data cleaning service for transforming and cleaning DataFrames.

Provides functions for removing duplicates, handling missing values, trimming whitespace,
standardizing text case, removing outliers, normalizing dates, and cleaning numeric data.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime
import pandas as pd
import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)


class CleaningError(Exception):
    """Base exception for data cleaning errors."""
    pass


class CleaningReport:
    """
    Container for tracking changes made during cleaning operations.
    """
    def __init__(self, operation: str):
        self.operation = operation
        self.changes: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {}
        self.warnings: List[str] = []
    
    def add_change(self, description: str, details: Optional[Dict] = None):
        """Add a change record."""
        self.changes.append({
            'description': description,
            'details': details or {}
        })
    
    def add_warning(self, warning: str):
        """Add a warning."""
        self.warnings.append(warning)
    
    def set_summary(self, **kwargs):
        """Set summary statistics."""
        self.summary.update(kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            'operation': self.operation,
            'summary': self.summary,
            'changes': self.changes,
            'warnings': self.warnings
        }


def remove_duplicates(
    dataframe: pd.DataFrame,
    subset: Optional[Union[str, List[str]]] = None,
    keep: str = 'first'
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Remove duplicate rows from DataFrame.

    Args:
        dataframe: Pandas DataFrame to clean
        subset: Column name(s) to consider for duplicates (None = all columns)
        keep: Which duplicates to keep ('first', 'last', or False to remove all)

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('remove_duplicates')
    
    try:
        original_count = len(dataframe)
        
        # Normalize subset to list
        if isinstance(subset, str):
            subset = [subset]
        
        # Check if columns exist
        if subset:
            missing_cols = set(subset) - set(dataframe.columns)
            if missing_cols:
                raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
        
        # Find duplicates before removal
        duplicate_mask = dataframe.duplicated(subset=subset, keep=False)
        duplicate_count = duplicate_mask.sum()
        
        # Remove duplicates
        cleaned_df = dataframe.drop_duplicates(subset=subset, keep=keep, ignore_index=False)
        removed_count = original_count - len(cleaned_df)
        
        # Build report
        report.set_summary(
            original_rows=original_count,
            cleaned_rows=len(cleaned_df),
            duplicates_removed=removed_count,
            duplicate_groups=int(duplicate_count / 2) if duplicate_count > 0 else 0,
            subset_columns=subset or 'all columns',
            keep_strategy=keep
        )
        
        if removed_count > 0:
            report.add_change(
                f"Removed {removed_count} duplicate rows",
                {
                    'removed_count': removed_count,
                    'percentage_removed': round(removed_count / original_count * 100, 2)
                }
            )
        else:
            report.add_change("No duplicates found")
        
        logger.info(f"Removed {removed_count} duplicates from {original_count} rows")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to remove duplicates: {e}", exc_info=True)
        raise CleaningError(f"Duplicate removal failed: {str(e)}")


def handle_missing_values(
    dataframe: pd.DataFrame,
    strategy: str = 'drop',
    columns: Optional[List[str]] = None,
    fill_value: Any = None
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Handle missing values in DataFrame using various strategies.

    Args:
        dataframe: Pandas DataFrame to clean
        strategy: Strategy for handling missing values:
            - 'drop': Remove rows with any missing values
            - 'drop_all': Remove rows where all values are missing
            - 'fill_mean': Fill with column mean (numeric only)
            - 'fill_median': Fill with column median (numeric only)
            - 'fill_mode': Fill with most frequent value
            - 'fill_forward': Forward fill (propagate last valid value)
            - 'fill_backward': Backward fill (propagate next valid value)
            - 'fill_value': Fill with specific value
            - 'interpolate': Interpolate missing values (numeric only)
        columns: Specific columns to apply strategy to (None = all columns)
        fill_value: Value to use when strategy='fill_value'

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('handle_missing_values')
    
    valid_strategies = [
        'drop', 'drop_all', 'fill_mean', 'fill_median', 'fill_mode',
        'fill_forward', 'fill_backward', 'fill_value', 'interpolate'
    ]
    
    if strategy not in valid_strategies:
        raise CleaningError(f"Invalid strategy '{strategy}'. Valid strategies: {valid_strategies}")
    
    try:
        original_count = len(dataframe)
        cleaned_df = dataframe.copy()
        
        # Get columns to process
        if columns:
            missing_cols = set(columns) - set(dataframe.columns)
            if missing_cols:
                raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
            process_columns = columns
        else:
            process_columns = list(dataframe.columns)
        
        # Count missing values before
        missing_before = {}
        for col in process_columns:
            null_count = dataframe[col].isna().sum()
            if null_count > 0:
                missing_before[col] = {
                    'count': int(null_count),
                    'percentage': round(null_count / original_count * 100, 2)
                }
        
        total_missing_before = sum(d['count'] for d in missing_before.values())
        
        # Apply strategy
        if strategy == 'drop':
            cleaned_df = cleaned_df.dropna(subset=process_columns, how='any')
            rows_removed = original_count - len(cleaned_df)
            report.add_change(
                f"Dropped {rows_removed} rows with missing values",
                {'rows_removed': rows_removed}
            )
        
        elif strategy == 'drop_all':
            cleaned_df = cleaned_df.dropna(subset=process_columns, how='all')
            rows_removed = original_count - len(cleaned_df)
            report.add_change(
                f"Dropped {rows_removed} rows where all values are missing",
                {'rows_removed': rows_removed}
            )
        
        elif strategy == 'fill_mean':
            for col in process_columns:
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    mean_val = cleaned_df[col].mean()
                    filled_count = cleaned_df[col].isna().sum()
                    cleaned_df[col] = cleaned_df[col].fillna(mean_val)
                    if filled_count > 0:
                        report.add_change(
                            f"Filled {filled_count} missing values in '{col}' with mean ({mean_val:.2f})",
                            {'column': col, 'filled_count': int(filled_count), 'fill_value': float(mean_val)}
                        )
                else:
                    report.add_warning(f"Column '{col}' is not numeric, skipped for mean fill")
        
        elif strategy == 'fill_median':
            for col in process_columns:
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    median_val = cleaned_df[col].median()
                    filled_count = cleaned_df[col].isna().sum()
                    cleaned_df[col] = cleaned_df[col].fillna(median_val)
                    if filled_count > 0:
                        report.add_change(
                            f"Filled {filled_count} missing values in '{col}' with median ({median_val:.2f})",
                            {'column': col, 'filled_count': int(filled_count), 'fill_value': float(median_val)}
                        )
                else:
                    report.add_warning(f"Column '{col}' is not numeric, skipped for median fill")
        
        elif strategy == 'fill_mode':
            for col in process_columns:
                mode_values = cleaned_df[col].mode()
                if len(mode_values) > 0:
                    mode_val = mode_values[0]
                    filled_count = cleaned_df[col].isna().sum()
                    cleaned_df[col] = cleaned_df[col].fillna(mode_val)
                    if filled_count > 0:
                        report.add_change(
                            f"Filled {filled_count} missing values in '{col}' with mode ({mode_val})",
                            {'column': col, 'filled_count': int(filled_count), 'fill_value': str(mode_val)}
                        )
        
        elif strategy == 'fill_forward':
            for col in process_columns:
                filled_count = cleaned_df[col].isna().sum()
                cleaned_df[col] = cleaned_df[col].fillna(method='ffill')
                remaining_nulls = cleaned_df[col].isna().sum()
                actual_filled = filled_count - remaining_nulls
                if actual_filled > 0:
                    report.add_change(
                        f"Forward filled {actual_filled} missing values in '{col}'",
                        {'column': col, 'filled_count': int(actual_filled)}
                    )
                if remaining_nulls > 0:
                    report.add_warning(f"Column '{col}' still has {remaining_nulls} missing values (no prior values to fill)")
        
        elif strategy == 'fill_backward':
            for col in process_columns:
                filled_count = cleaned_df[col].isna().sum()
                cleaned_df[col] = cleaned_df[col].fillna(method='bfill')
                remaining_nulls = cleaned_df[col].isna().sum()
                actual_filled = filled_count - remaining_nulls
                if actual_filled > 0:
                    report.add_change(
                        f"Backward filled {actual_filled} missing values in '{col}'",
                        {'column': col, 'filled_count': int(actual_filled)}
                    )
                if remaining_nulls > 0:
                    report.add_warning(f"Column '{col}' still has {remaining_nulls} missing values (no subsequent values to fill)")
        
        elif strategy == 'fill_value':
            if fill_value is None:
                raise CleaningError("fill_value must be provided when strategy='fill_value'")
            for col in process_columns:
                filled_count = cleaned_df[col].isna().sum()
                cleaned_df[col] = cleaned_df[col].fillna(fill_value)
                if filled_count > 0:
                    report.add_change(
                        f"Filled {filled_count} missing values in '{col}' with {fill_value}",
                        {'column': col, 'filled_count': int(filled_count), 'fill_value': str(fill_value)}
                    )
        
        elif strategy == 'interpolate':
            for col in process_columns:
                if pd.api.types.is_numeric_dtype(cleaned_df[col]):
                    filled_count = cleaned_df[col].isna().sum()
                    cleaned_df[col] = cleaned_df[col].interpolate(method='linear')
                    remaining_nulls = cleaned_df[col].isna().sum()
                    actual_filled = filled_count - remaining_nulls
                    if actual_filled > 0:
                        report.add_change(
                            f"Interpolated {actual_filled} missing values in '{col}'",
                            {'column': col, 'filled_count': int(actual_filled)}
                        )
                else:
                    report.add_warning(f"Column '{col}' is not numeric, skipped for interpolation")
        
        # Count missing values after
        missing_after = {}
        total_missing_after = 0
        for col in process_columns:
            if col in cleaned_df.columns:
                null_count = cleaned_df[col].isna().sum()
                if null_count > 0:
                    missing_after[col] = int(null_count)
                total_missing_after += null_count
        
        # Build summary
        report.set_summary(
            strategy=strategy,
            original_rows=original_count,
            cleaned_rows=len(cleaned_df),
            columns_processed=len(process_columns),
            total_missing_before=total_missing_before,
            total_missing_after=int(total_missing_after),
            missing_by_column_before=missing_before,
            missing_by_column_after=missing_after
        )
        
        logger.info(f"Handled missing values with strategy '{strategy}': {total_missing_before} → {total_missing_after}")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to handle missing values: {e}", exc_info=True)
        raise CleaningError(f"Missing value handling failed: {str(e)}")


def trim_whitespace(
    dataframe: pd.DataFrame,
    columns: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Trim leading and trailing whitespace from string columns.

    Args:
        dataframe: Pandas DataFrame to clean
        columns: Specific columns to trim (None = all string columns)

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('trim_whitespace')
    
    try:
        cleaned_df = dataframe.copy()
        
        # Determine columns to process
        if columns:
            missing_cols = set(columns) - set(dataframe.columns)
            if missing_cols:
                raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
            process_columns = columns
        else:
            # Auto-detect string columns
            process_columns = [
                col for col in dataframe.columns
                if pd.api.types.is_string_dtype(dataframe[col]) or 
                   dataframe[col].dtype == 'object'
            ]
        
        if not process_columns:
            report.add_warning("No string columns found to trim")
            report.set_summary(columns_processed=0, values_changed=0)
            return cleaned_df, report
        
        total_changed = 0
        
        for col in process_columns:
            # Convert to string and trim
            original_values = cleaned_df[col].copy()
            cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
            
            # Count changes (excluding NaN)
            non_null_mask = original_values.notna()
            if non_null_mask.any():
                changed_mask = (original_values[non_null_mask].astype(str) != cleaned_df.loc[non_null_mask, col])
                changed_count = changed_mask.sum()
                
                if changed_count > 0:
                    total_changed += changed_count
                    report.add_change(
                        f"Trimmed whitespace from {changed_count} values in '{col}'",
                        {'column': col, 'values_changed': int(changed_count)}
                    )
        
        report.set_summary(
            columns_processed=len(process_columns),
            total_values_changed=total_changed
        )
        
        logger.info(f"Trimmed whitespace from {len(process_columns)} columns, {total_changed} values changed")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to trim whitespace: {e}", exc_info=True)
        raise CleaningError(f"Whitespace trimming failed: {str(e)}")


def standardize_case(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    case: str = 'lower'
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Standardize text case in string columns.

    Args:
        dataframe: Pandas DataFrame to clean
        columns: Column name(s) to standardize
        case: Case to convert to ('lower', 'upper', 'title', 'capitalize')

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('standardize_case')
    
    valid_cases = ['lower', 'upper', 'title', 'capitalize']
    if case not in valid_cases:
        raise CleaningError(f"Invalid case '{case}'. Valid cases: {valid_cases}")
    
    try:
        cleaned_df = dataframe.copy()
        
        # Normalize to list
        if isinstance(columns, str):
            columns = [columns]
        
        # Check if columns exist
        missing_cols = set(columns) - set(dataframe.columns)
        if missing_cols:
            raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
        
        total_changed = 0
        
        for col in columns:
            original_values = cleaned_df[col].copy()
            
            # Apply case transformation
            if case == 'lower':
                cleaned_df[col] = cleaned_df[col].astype(str).str.lower()
            elif case == 'upper':
                cleaned_df[col] = cleaned_df[col].astype(str).str.upper()
            elif case == 'title':
                cleaned_df[col] = cleaned_df[col].astype(str).str.title()
            elif case == 'capitalize':
                cleaned_df[col] = cleaned_df[col].astype(str).str.capitalize()
            
            # Count changes
            non_null_mask = original_values.notna()
            if non_null_mask.any():
                changed_mask = (original_values[non_null_mask].astype(str) != cleaned_df.loc[non_null_mask, col])
                changed_count = changed_mask.sum()
                
                if changed_count > 0:
                    total_changed += changed_count
                    report.add_change(
                        f"Standardized {changed_count} values in '{col}' to {case} case",
                        {'column': col, 'case': case, 'values_changed': int(changed_count)}
                    )
        
        report.set_summary(
            case=case,
            columns_processed=len(columns),
            total_values_changed=total_changed
        )
        
        logger.info(f"Standardized case to '{case}' for {len(columns)} columns, {total_changed} values changed")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to standardize case: {e}", exc_info=True)
        raise CleaningError(f"Case standardization failed: {str(e)}")


def remove_outliers(
    dataframe: pd.DataFrame,
    column: str,
    method: str = 'iqr',
    threshold: float = 1.5
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Remove outliers from a numeric column.

    Args:
        dataframe: Pandas DataFrame to clean
        column: Column name to remove outliers from
        method: Method for detecting outliers:
            - 'iqr': Interquartile range method (default)
            - 'zscore': Z-score method
        threshold: Threshold for outlier detection:
            - For IQR: multiplier for IQR (default 1.5)
            - For Z-score: number of standard deviations (default 3)

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('remove_outliers')
    
    valid_methods = ['iqr', 'zscore']
    if method not in valid_methods:
        raise CleaningError(f"Invalid method '{method}'. Valid methods: {valid_methods}")
    
    try:
        if column not in dataframe.columns:
            raise CleaningError(f"Column '{column}' not found")
        
        # Check if column is numeric
        if not pd.api.types.is_numeric_dtype(dataframe[column]):
            raise CleaningError(f"Column '{column}' is not numeric")
        
        original_count = len(dataframe)
        col_data = dataframe[column].dropna()
        
        if len(col_data) == 0:
            report.add_warning(f"Column '{column}' has no non-null values")
            report.set_summary(original_rows=original_count, cleaned_rows=original_count, outliers_removed=0)
            return dataframe.copy(), report
        
        # Detect outliers based on method
        if method == 'iqr':
            Q1 = col_data.quantile(0.25)
            Q3 = col_data.quantile(0.75)
            IQR = Q3 - Q1
            
            lower_bound = Q1 - threshold * IQR
            upper_bound = Q3 + threshold * IQR
            
            outlier_mask = (dataframe[column] < lower_bound) | (dataframe[column] > upper_bound)
            
            method_details = {
                'Q1': float(Q1),
                'Q3': float(Q3),
                'IQR': float(IQR),
                'lower_bound': float(lower_bound),
                'upper_bound': float(upper_bound),
                'threshold': threshold
            }
        
        elif method == 'zscore':
            mean = col_data.mean()
            std = col_data.std()
            
            if std == 0:
                report.add_warning(f"Column '{column}' has zero standard deviation, no outliers detected")
                report.set_summary(original_rows=original_count, cleaned_rows=original_count, outliers_removed=0)
                return dataframe.copy(), report
            
            z_scores = np.abs((dataframe[column] - mean) / std)
            outlier_mask = z_scores > threshold
            
            method_details = {
                'mean': float(mean),
                'std': float(std),
                'threshold': threshold
            }
        
        # Remove outliers
        outlier_count = outlier_mask.sum()
        cleaned_df = dataframe[~outlier_mask].copy()
        
        # Get outlier statistics
        if outlier_count > 0:
            outlier_values = dataframe.loc[outlier_mask, column].dropna()
            outlier_stats = {
                'min_outlier': float(outlier_values.min()) if len(outlier_values) > 0 else None,
                'max_outlier': float(outlier_values.max()) if len(outlier_values) > 0 else None,
                'sample_outliers': outlier_values.head(10).tolist()
            }
        else:
            outlier_stats = {}
        
        report.add_change(
            f"Removed {outlier_count} outliers from '{column}' using {method} method",
            {
                'column': column,
                'method': method,
                'outliers_removed': int(outlier_count),
                'percentage_removed': round(outlier_count / original_count * 100, 2),
                **method_details,
                **outlier_stats
            }
        )
        
        report.set_summary(
            column=column,
            method=method,
            original_rows=original_count,
            cleaned_rows=len(cleaned_df),
            outliers_removed=int(outlier_count)
        )
        
        logger.info(f"Removed {outlier_count} outliers from '{column}' using {method} method")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to remove outliers: {e}", exc_info=True)
        raise CleaningError(f"Outlier removal failed: {str(e)}")


def normalize_dates(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    target_format: str = 'ISO8601',
    parse_format: Optional[str] = None
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Normalize date columns to a standard format.

    Args:
        dataframe: Pandas DataFrame to clean
        columns: Column name(s) to normalize
        target_format: Target date format:
            - 'ISO8601': ISO 8601 format (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
            - Custom strftime format string (e.g., '%Y-%m-%d', '%m/%d/%Y')
        parse_format: Optional format string to help parse input dates

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('normalize_dates')
    
    try:
        cleaned_df = dataframe.copy()
        
        # Normalize to list
        if isinstance(columns, str):
            columns = [columns]
        
        # Check if columns exist
        missing_cols = set(columns) - set(dataframe.columns)
        if missing_cols:
            raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
        
        total_converted = 0
        total_failed = 0
        
        for col in columns:
            original_values = cleaned_df[col].copy()
            
            # Parse dates
            if parse_format:
                datetime_series = pd.to_datetime(
                    cleaned_df[col],
                    format=parse_format,
                    errors='coerce'
                )
            else:
                datetime_series = pd.to_datetime(
                    cleaned_df[col],
                    errors='coerce',
                    infer_datetime_format=True
                )
            
            # Count successful conversions
            non_null_original = original_values.notna().sum()
            successful_conversions = datetime_series.notna().sum()
            failed_conversions = non_null_original - successful_conversions
            
            # Format dates
            if target_format == 'ISO8601':
                # Keep as datetime object for ISO format
                cleaned_df[col] = datetime_series
            else:
                # Format using custom format string
                cleaned_df[col] = datetime_series.dt.strftime(target_format)
            
            if successful_conversions > 0:
                total_converted += successful_conversions
                report.add_change(
                    f"Normalized {successful_conversions} dates in '{col}' to {target_format} format",
                    {
                        'column': col,
                        'converted_count': int(successful_conversions),
                        'failed_count': int(failed_conversions),
                        'target_format': target_format
                    }
                )
            
            if failed_conversions > 0:
                total_failed += failed_conversions
                report.add_warning(
                    f"Failed to parse {failed_conversions} date values in '{col}'"
                )
        
        report.set_summary(
            target_format=target_format,
            parse_format=parse_format,
            columns_processed=len(columns),
            total_converted=int(total_converted),
            total_failed=int(total_failed)
        )
        
        logger.info(f"Normalized dates in {len(columns)} columns: {total_converted} converted, {total_failed} failed")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to normalize dates: {e}", exc_info=True)
        raise CleaningError(f"Date normalization failed: {str(e)}")


def clean_numeric(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    remove_chars: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, CleaningReport]:
    """
    Clean numeric columns by removing non-numeric characters.

    Args:
        dataframe: Pandas DataFrame to clean
        columns: Column name(s) to clean
        remove_chars: List of characters to remove (default: currency symbols, commas, spaces)

    Returns:
        Tuple of (cleaned_dataframe, report)

    Raises:
        CleaningError: If cleaning operation fails
    """
    report = CleaningReport('clean_numeric')
    
    try:
        cleaned_df = dataframe.copy()
        
        # Normalize to list
        if isinstance(columns, str):
            columns = [columns]
        
        # Check if columns exist
        missing_cols = set(columns) - set(dataframe.columns)
        if missing_cols:
            raise CleaningError(f"Columns not found: {', '.join(missing_cols)}")
        
        # Default characters to remove
        if remove_chars is None:
            remove_chars = ['$', '€', '£', '¥', '₹', ',', ' ', '%']
        
        total_converted = 0
        total_failed = 0
        
        for col in columns:
            original_values = cleaned_df[col].copy()
            
            # Skip if already numeric
            if pd.api.types.is_numeric_dtype(original_values):
                report.add_change(
                    f"Column '{col}' is already numeric, skipped",
                    {'column': col}
                )
                continue
            
            # Convert to string and clean
            str_values = original_values.astype(str)
            
            # Remove specified characters
            cleaned_values = str_values
            for char in remove_chars:
                cleaned_values = cleaned_values.str.replace(char, '', regex=False)
            
            # Convert to numeric
            numeric_values = pd.to_numeric(cleaned_values, errors='coerce')
            
            # Count conversions
            non_null_original = original_values.notna().sum()
            successful_conversions = numeric_values.notna().sum()
            failed_conversions = non_null_original - successful_conversions
            
            # Count actual changes (where cleaning made a difference)
            changed_mask = (original_values.notna()) & (original_values.astype(str) != cleaned_values)
            changed_count = changed_mask.sum()
            
            cleaned_df[col] = numeric_values
            
            if successful_conversions > 0:
                total_converted += successful_conversions
                report.add_change(
                    f"Cleaned and converted {successful_conversions} values in '{col}' to numeric ({changed_count} required cleaning)",
                    {
                        'column': col,
                        'converted_count': int(successful_conversions),
                        'cleaned_count': int(changed_count),
                        'failed_count': int(failed_conversions),
                        'removed_chars': remove_chars
                    }
                )
            
            if failed_conversions > 0:
                total_failed += failed_conversions
                # Get sample failed values
                failed_mask = (original_values.notna()) & (numeric_values.isna())
                failed_samples = original_values[failed_mask].head(5).tolist()
                report.add_warning(
                    f"Failed to convert {failed_conversions} values in '{col}' to numeric. "
                    f"Sample values: {failed_samples}"
                )
        
        report.set_summary(
            columns_processed=len(columns),
            total_converted=int(total_converted),
            total_failed=int(total_failed),
            removed_chars=remove_chars
        )
        
        logger.info(f"Cleaned numeric data in {len(columns)} columns: {total_converted} converted, {total_failed} failed")
        return cleaned_df, report
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to clean numeric data: {e}", exc_info=True)
        raise CleaningError(f"Numeric cleaning failed: {str(e)}")


def apply_cleaning_pipeline(
    dataframe: pd.DataFrame,
    operations: List[Dict[str, Any]]
) -> Tuple[pd.DataFrame, List[CleaningReport]]:
    """
    Apply multiple cleaning operations in sequence.

    Args:
        dataframe: Pandas DataFrame to clean
        operations: List of cleaning operations to apply:
        [
            {'operation': 'remove_duplicates', 'params': {'subset': ['id']}},
            {'operation': 'handle_missing_values', 'params': {'strategy': 'drop'}},
            {'operation': 'trim_whitespace', 'params': {}},
            ...
        ]

    Returns:
        Tuple of (cleaned_dataframe, list_of_reports)

    Raises:
        CleaningError: If any cleaning operation fails
    """
    try:
        cleaned_df = dataframe.copy()
        reports = []
        
        operation_map = {
            'remove_duplicates': remove_duplicates,
            'handle_missing_values': handle_missing_values,
            'trim_whitespace': trim_whitespace,
            'standardize_case': standardize_case,
            'remove_outliers': remove_outliers,
            'normalize_dates': normalize_dates,
            'clean_numeric': clean_numeric
        }
        
        for i, op in enumerate(operations):
            operation_name = op.get('operation')
            params = op.get('params', {})
            
            if operation_name not in operation_map:
                raise CleaningError(
                    f"Unknown operation '{operation_name}'. "
                    f"Valid operations: {list(operation_map.keys())}"
                )
            
            logger.info(f"Applying operation {i+1}/{len(operations)}: {operation_name}")
            
            operation_func = operation_map[operation_name]
            cleaned_df, report = operation_func(cleaned_df, **params)
            reports.append(report)
        
        logger.info(f"Cleaning pipeline complete: {len(operations)} operations applied")
        return cleaned_df, reports
    
    except CleaningError:
        raise
    except Exception as e:
        logger.error(f"Failed to apply cleaning pipeline: {e}", exc_info=True)
        raise CleaningError(f"Cleaning pipeline failed: {str(e)}")
