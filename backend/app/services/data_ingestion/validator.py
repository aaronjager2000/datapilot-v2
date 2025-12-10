"""
Data validation service for validating DataFrame contents.

Provides comprehensive validation rules including column presence, data types,
uniqueness constraints, range validation, pattern matching, and referential integrity.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Set, Union
from enum import Enum
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class ValidationSeverity(str, Enum):
    """Severity levels for validation errors."""
    ERROR = "error"      # Critical errors that must be fixed
    WARNING = "warning"  # Non-critical issues that should be reviewed
    INFO = "info"        # Informational messages


class ValidationError(Exception):
    """Base exception for validation errors."""
    pass


class MissingColumnsError(ValidationError):
    """Raised when required columns are missing."""
    pass


class DataValidationError(ValidationError):
    """Raised when data validation fails."""
    pass


class ValidationResult:
    """
    Container for validation results.
    """
    def __init__(self):
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.info: List[Dict[str, Any]] = []
        self.passed = True
    
    def add_error(self, rule: str, message: str, details: Optional[Dict] = None):
        """Add a validation error."""
        self.errors.append({
            'rule': rule,
            'severity': ValidationSeverity.ERROR,
            'message': message,
            'details': details or {}
        })
        self.passed = False
    
    def add_warning(self, rule: str, message: str, details: Optional[Dict] = None):
        """Add a validation warning."""
        self.warnings.append({
            'rule': rule,
            'severity': ValidationSeverity.WARNING,
            'message': message,
            'details': details or {}
        })
    
    def add_info(self, rule: str, message: str, details: Optional[Dict] = None):
        """Add validation info."""
        self.info.append({
            'rule': rule,
            'severity': ValidationSeverity.INFO,
            'message': message,
            'details': details or {}
        })
    
    def get_all_issues(self) -> List[Dict[str, Any]]:
        """Get all validation issues combined."""
        return self.errors + self.warnings + self.info
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            'passed': self.passed,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'info_count': len(self.info),
            'errors': self.errors,
            'warnings': self.warnings,
            'info': self.info
        }


def validate_required_columns(
    dataframe: pd.DataFrame,
    required_columns: List[str],
    raise_error: bool = True
) -> ValidationResult:
    """
    Validate that all required columns are present in the DataFrame.

    Args:
        dataframe: Pandas DataFrame to validate
        required_columns: List of required column names
        raise_error: If True, raises MissingColumnsError when columns are missing

    Returns:
        ValidationResult object

    Raises:
        MissingColumnsError: If required columns are missing and raise_error=True
    """
    result = ValidationResult()
    
    if not required_columns:
        result.add_info('required_columns', 'No required columns specified')
        return result
    
    try:
        existing_columns = set(dataframe.columns)
        required_set = set(required_columns)
        missing_columns = required_set - existing_columns
        
        if missing_columns:
            missing_list = sorted(list(missing_columns))
            message = f"Missing required columns: {', '.join(missing_list)}"
            result.add_error(
                'required_columns',
                message,
                {
                    'missing_columns': missing_list,
                    'existing_columns': list(existing_columns),
                    'required_columns': list(required_set)
                }
            )
            
            if raise_error:
                logger.error(message)
                raise MissingColumnsError(message)
        else:
            result.add_info(
                'required_columns',
                f'All {len(required_columns)} required columns present'
            )
        
        logger.info(f"Required columns validation: {len(missing_columns)} missing")
        return result
    
    except MissingColumnsError:
        raise
    except Exception as e:
        logger.error(f"Failed to validate required columns: {e}")
        raise ValidationError(f"Column validation failed: {str(e)}")


def validate_data_types(
    dataframe: pd.DataFrame,
    schema: Dict[str, str],
    sample_invalid: int = 10
) -> ValidationResult:
    """
    Validate that columns match expected data types.

    Args:
        dataframe: Pandas DataFrame to validate
        schema: Dictionary mapping column names to expected types
                Supported types: 'integer', 'float', 'string', 'boolean', 'datetime', 'date'
        sample_invalid: Number of invalid values to include in details

    Returns:
        ValidationResult with row-level type validation errors
    """
    result = ValidationResult()
    
    if not schema:
        result.add_info('data_types', 'No type schema specified')
        return result
    
    try:
        for column, expected_type in schema.items():
            if column not in dataframe.columns:
                result.add_warning(
                    'data_types',
                    f"Column '{column}' in schema not found in DataFrame"
                )
                continue
            
            col_data = dataframe[column]
            invalid_rows = []
            invalid_values = []
            
            # Get non-null data for validation
            non_null_mask = col_data.notna()
            non_null_data = col_data[non_null_mask]
            
            if len(non_null_data) == 0:
                result.add_info(
                    'data_types',
                    f"Column '{column}': All values are null"
                )
                continue
            
            # Validate based on expected type
            if expected_type == 'integer':
                numeric_series = pd.to_numeric(non_null_data, errors='coerce')
                invalid_mask = numeric_series.isna()
                
            elif expected_type == 'float':
                numeric_series = pd.to_numeric(non_null_data, errors='coerce')
                invalid_mask = numeric_series.isna()
                
            elif expected_type == 'boolean':
                bool_values = {'true', 'false', 't', 'f', 'yes', 'no', 'y', 'n', '1', '0', 1, 0, True, False}
                str_series = non_null_data.astype(str).str.lower()
                invalid_mask = ~str_series.isin([str(v).lower() for v in bool_values])
                
            elif expected_type in ['datetime', 'date']:
                datetime_series = pd.to_datetime(non_null_data, errors='coerce')
                invalid_mask = datetime_series.isna()
                
            elif expected_type == 'string':
                # Strings are generally always valid
                invalid_mask = pd.Series([False] * len(non_null_data), index=non_null_data.index)
                
            else:
                result.add_warning(
                    'data_types',
                    f"Unknown type '{expected_type}' for column '{column}'"
                )
                continue
            
            # Collect invalid values
            if invalid_mask.any():
                invalid_indices = non_null_data[invalid_mask].index.tolist()
                invalid_values_list = non_null_data[invalid_mask].head(sample_invalid).tolist()
                
                invalid_count = invalid_mask.sum()
                total_count = len(non_null_data)
                invalid_percentage = (invalid_count / total_count * 100) if total_count > 0 else 0
                
                result.add_error(
                    'data_types',
                    f"Column '{column}': {invalid_count} values ({invalid_percentage:.1f}%) cannot be converted to {expected_type}",
                    {
                        'column': column,
                        'expected_type': expected_type,
                        'invalid_count': int(invalid_count),
                        'total_non_null': int(total_count),
                        'invalid_percentage': float(invalid_percentage),
                        'invalid_row_indices': invalid_indices[:sample_invalid],
                        'sample_invalid_values': [str(v) for v in invalid_values_list]
                    }
                )
            else:
                result.add_info(
                    'data_types',
                    f"Column '{column}': All values match type {expected_type}"
                )
        
        logger.info(f"Data type validation: {len(result.errors)} type errors found")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate data types: {e}")
        raise ValidationError(f"Type validation failed: {str(e)}")


def validate_unique_constraint(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    sample_duplicates: int = 10
) -> ValidationResult:
    """
    Check for duplicate values in specified columns.

    Args:
        dataframe: Pandas DataFrame to validate
        columns: Column name or list of column names that should be unique
        sample_duplicates: Number of duplicate examples to include in details

    Returns:
        ValidationResult with duplicate information
    """
    result = ValidationResult()
    
    # Normalize to list
    if isinstance(columns, str):
        columns = [columns]
    
    try:
        # Check if columns exist
        missing_cols = set(columns) - set(dataframe.columns)
        if missing_cols:
            result.add_error(
                'unique_constraint',
                f"Columns not found: {', '.join(missing_cols)}"
            )
            return result
        
        # Find duplicates
        duplicate_mask = dataframe.duplicated(subset=columns, keep=False)
        duplicate_count = duplicate_mask.sum()
        
        if duplicate_count > 0:
            # Get duplicate values
            duplicates_df = dataframe[duplicate_mask][columns]
            
            # Group by to find duplicate groups
            duplicate_groups = duplicates_df.groupby(list(columns)).size()
            duplicate_groups = duplicate_groups[duplicate_groups > 1].sort_values(ascending=False)
            
            # Sample duplicates
            sample_groups = duplicate_groups.head(sample_duplicates)
            
            column_str = ', '.join(columns) if len(columns) > 1 else columns[0]
            result.add_error(
                'unique_constraint',
                f"{duplicate_count} duplicate rows found in column(s): {column_str}",
                {
                    'columns': columns,
                    'duplicate_row_count': int(duplicate_count),
                    'unique_duplicate_values': int(len(duplicate_groups)),
                    'duplicate_row_indices': dataframe[duplicate_mask].index.tolist()[:sample_duplicates],
                    'sample_duplicates': [
                        {
                            'value': str(idx) if not isinstance(idx, tuple) else {columns[i]: str(idx[i]) for i in range(len(columns))},
                            'count': int(count)
                        }
                        for idx, count in sample_groups.items()
                    ]
                }
            )
        else:
            column_str = ', '.join(columns) if len(columns) > 1 else columns[0]
            result.add_info(
                'unique_constraint',
                f"All values unique in column(s): {column_str}"
            )
        
        logger.info(f"Unique constraint validation: {duplicate_count} duplicates found")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate unique constraint: {e}")
        raise ValidationError(f"Unique constraint validation failed: {str(e)}")


def validate_range(
    dataframe: pd.DataFrame,
    column: str,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    sample_invalid: int = 10
) -> ValidationResult:
    """
    Validate that numeric values fall within a specified range.

    Args:
        dataframe: Pandas DataFrame to validate
        column: Column name to validate
        min_value: Minimum allowed value (inclusive)
        max_value: Maximum allowed value (inclusive)
        sample_invalid: Number of out-of-range values to include in details

    Returns:
        ValidationResult with range violation information
    """
    result = ValidationResult()
    
    if min_value is None and max_value is None:
        result.add_warning('range_validation', 'No range specified')
        return result
    
    try:
        if column not in dataframe.columns:
            result.add_error('range_validation', f"Column '{column}' not found")
            return result
        
        col_data = dataframe[column]
        
        # Convert to numeric
        numeric_data = pd.to_numeric(col_data, errors='coerce')
        non_null_data = numeric_data.dropna()
        
        if len(non_null_data) == 0:
            result.add_warning('range_validation', f"Column '{column}': No numeric values to validate")
            return result
        
        # Check range
        invalid_mask = pd.Series([False] * len(numeric_data), index=numeric_data.index)
        
        if min_value is not None:
            invalid_mask |= (numeric_data < min_value)
        
        if max_value is not None:
            invalid_mask |= (numeric_data > max_value)
        
        # Remove NaN from invalid mask (NaN are handled separately)
        invalid_mask = invalid_mask & numeric_data.notna()
        
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            invalid_values = numeric_data[invalid_mask].head(sample_invalid).tolist()
            invalid_indices = numeric_data[invalid_mask].index.tolist()[:sample_invalid]
            
            range_str = f"[{min_value}, {max_value}]"
            if min_value is None:
                range_str = f"<= {max_value}"
            elif max_value is None:
                range_str = f">= {min_value}"
            
            total_count = len(non_null_data)
            invalid_percentage = (invalid_count / total_count * 100) if total_count > 0 else 0
            
            result.add_error(
                'range_validation',
                f"Column '{column}': {invalid_count} values ({invalid_percentage:.1f}%) outside range {range_str}",
                {
                    'column': column,
                    'min_value': min_value,
                    'max_value': max_value,
                    'invalid_count': int(invalid_count),
                    'total_count': int(total_count),
                    'invalid_percentage': float(invalid_percentage),
                    'actual_min': float(non_null_data.min()),
                    'actual_max': float(non_null_data.max()),
                    'invalid_row_indices': invalid_indices,
                    'sample_invalid_values': invalid_values
                }
            )
        else:
            range_str = f"[{min_value}, {max_value}]"
            if min_value is None:
                range_str = f"<= {max_value}"
            elif max_value is None:
                range_str = f">= {min_value}"
            
            result.add_info(
                'range_validation',
                f"Column '{column}': All values within range {range_str}"
            )
        
        logger.info(f"Range validation: {invalid_count} out-of-range values found")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate range: {e}")
        raise ValidationError(f"Range validation failed: {str(e)}")


def validate_pattern(
    dataframe: pd.DataFrame,
    column: str,
    pattern: str,
    flags: int = 0,
    sample_invalid: int = 10
) -> ValidationResult:
    """
    Validate that string values match a regex pattern.

    Args:
        dataframe: Pandas DataFrame to validate
        column: Column name to validate
        pattern: Regex pattern that values should match
        flags: Regex flags (e.g., re.IGNORECASE)
        sample_invalid: Number of non-matching values to include in details

    Returns:
        ValidationResult with pattern mismatch information
    """
    result = ValidationResult()
    
    try:
        if column not in dataframe.columns:
            result.add_error('pattern_validation', f"Column '{column}' not found")
            return result
        
        col_data = dataframe[column]
        non_null_data = col_data.dropna()
        
        if len(non_null_data) == 0:
            result.add_warning('pattern_validation', f"Column '{column}': No values to validate")
            return result
        
        # Compile regex
        try:
            regex = re.compile(pattern, flags)
        except re.error as e:
            result.add_error('pattern_validation', f"Invalid regex pattern: {str(e)}")
            return result
        
        # Check pattern
        str_data = non_null_data.astype(str)
        matches = str_data.apply(lambda x: bool(regex.match(x)))
        invalid_mask = ~matches
        
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            invalid_values = str_data[invalid_mask].head(sample_invalid).tolist()
            invalid_indices = str_data[invalid_mask].index.tolist()[:sample_invalid]
            
            total_count = len(non_null_data)
            invalid_percentage = (invalid_count / total_count * 100) if total_count > 0 else 0
            
            result.add_error(
                'pattern_validation',
                f"Column '{column}': {invalid_count} values ({invalid_percentage:.1f}%) don't match pattern '{pattern}'",
                {
                    'column': column,
                    'pattern': pattern,
                    'invalid_count': int(invalid_count),
                    'total_count': int(total_count),
                    'invalid_percentage': float(invalid_percentage),
                    'invalid_row_indices': invalid_indices,
                    'sample_invalid_values': invalid_values
                }
            )
        else:
            result.add_info(
                'pattern_validation',
                f"Column '{column}': All values match pattern '{pattern}'"
            )
        
        logger.info(f"Pattern validation: {invalid_count} non-matching values found")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate pattern: {e}")
        raise ValidationError(f"Pattern validation failed: {str(e)}")


def validate_foreign_key(
    dataframe: pd.DataFrame,
    column: str,
    valid_values: Union[List, Set, pd.Series],
    sample_invalid: int = 10
) -> ValidationResult:
    """
    Validate referential integrity by checking if values exist in a reference set.

    Args:
        dataframe: Pandas DataFrame to validate
        column: Column name to validate
        valid_values: List, set, or Series of valid reference values
        sample_invalid: Number of invalid values to include in details

    Returns:
        ValidationResult with referential integrity violations
    """
    result = ValidationResult()
    
    try:
        if column not in dataframe.columns:
            result.add_error('foreign_key', f"Column '{column}' not found")
            return result
        
        col_data = dataframe[column]
        non_null_data = col_data.dropna()
        
        if len(non_null_data) == 0:
            result.add_warning('foreign_key', f"Column '{column}': No values to validate")
            return result
        
        # Convert valid_values to set for faster lookup
        if isinstance(valid_values, pd.Series):
            valid_set = set(valid_values.dropna().values)
        else:
            valid_set = set(valid_values)
        
        if len(valid_set) == 0:
            result.add_warning('foreign_key', 'No valid reference values provided')
            return result
        
        # Check foreign key constraint
        invalid_mask = ~non_null_data.isin(valid_set)
        invalid_count = invalid_mask.sum()
        
        if invalid_count > 0:
            invalid_values = non_null_data[invalid_mask].unique()[:sample_invalid].tolist()
            invalid_indices = non_null_data[invalid_mask].index.tolist()[:sample_invalid]
            
            total_count = len(non_null_data)
            invalid_percentage = (invalid_count / total_count * 100) if total_count > 0 else 0
            
            result.add_error(
                'foreign_key',
                f"Column '{column}': {invalid_count} values ({invalid_percentage:.1f}%) not in reference set",
                {
                    'column': column,
                    'invalid_count': int(invalid_count),
                    'total_count': int(total_count),
                    'invalid_percentage': float(invalid_percentage),
                    'valid_values_count': len(valid_set),
                    'invalid_row_indices': invalid_indices,
                    'sample_invalid_values': [str(v) for v in invalid_values]
                }
            )
        else:
            result.add_info(
                'foreign_key',
                f"Column '{column}': All values exist in reference set"
            )
        
        logger.info(f"Foreign key validation: {invalid_count} invalid references found")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate foreign key: {e}")
        raise ValidationError(f"Foreign key validation failed: {str(e)}")


def get_validation_summary(
    dataframe: pd.DataFrame,
    rules: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Execute multiple validation rules and return a comprehensive summary.

    Args:
        dataframe: Pandas DataFrame to validate
        rules: Dictionary of validation rules:
        {
            'required_columns': ['col1', 'col2'],
            'data_types': {'col1': 'integer', 'col2': 'string'},
            'unique_constraints': [['col1'], ['col2', 'col3']],
            'range_checks': [
                {'column': 'age', 'min': 0, 'max': 150},
                {'column': 'price', 'min': 0}
            ],
            'pattern_checks': [
                {'column': 'email', 'pattern': r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$'}
            ],
            'foreign_keys': [
                {'column': 'category_id', 'valid_values': [1, 2, 3]}
            ]
        }

    Returns:
        Dictionary with comprehensive validation summary:
        {
            'passed': bool,
            'total_errors': int,
            'total_warnings': int,
            'results_by_rule': {...},
            'all_errors': [...],
            'all_warnings': [...],
            'dataframe_info': {...}
        }
    """
    try:
        logger.info("Starting comprehensive validation")
        
        summary = {
            'passed': True,
            'total_errors': 0,
            'total_warnings': 0,
            'total_info': 0,
            'results_by_rule': {},
            'all_errors': [],
            'all_warnings': [],
            'all_info': [],
            'dataframe_info': {
                'rows': len(dataframe),
                'columns': len(dataframe.columns),
                'column_names': list(dataframe.columns)
            }
        }
        
        # Required columns validation
        if 'required_columns' in rules:
            result = validate_required_columns(
                dataframe,
                rules['required_columns'],
                raise_error=False
            )
            summary['results_by_rule']['required_columns'] = result.to_dict()
            summary['all_errors'].extend(result.errors)
            summary['all_warnings'].extend(result.warnings)
            summary['all_info'].extend(result.info)
            if not result.passed:
                summary['passed'] = False
        
        # Data types validation
        if 'data_types' in rules:
            result = validate_data_types(dataframe, rules['data_types'])
            summary['results_by_rule']['data_types'] = result.to_dict()
            summary['all_errors'].extend(result.errors)
            summary['all_warnings'].extend(result.warnings)
            summary['all_info'].extend(result.info)
            if not result.passed:
                summary['passed'] = False
        
        # Unique constraints validation
        if 'unique_constraints' in rules:
            unique_results = []
            for columns in rules['unique_constraints']:
                result = validate_unique_constraint(dataframe, columns)
                unique_results.append(result.to_dict())
                summary['all_errors'].extend(result.errors)
                summary['all_warnings'].extend(result.warnings)
                summary['all_info'].extend(result.info)
                if not result.passed:
                    summary['passed'] = False
            summary['results_by_rule']['unique_constraints'] = unique_results
        
        # Range checks validation
        if 'range_checks' in rules:
            range_results = []
            for check in rules['range_checks']:
                result = validate_range(
                    dataframe,
                    check['column'],
                    check.get('min'),
                    check.get('max')
                )
                range_results.append(result.to_dict())
                summary['all_errors'].extend(result.errors)
                summary['all_warnings'].extend(result.warnings)
                summary['all_info'].extend(result.info)
                if not result.passed:
                    summary['passed'] = False
            summary['results_by_rule']['range_checks'] = range_results
        
        # Pattern checks validation
        if 'pattern_checks' in rules:
            pattern_results = []
            for check in rules['pattern_checks']:
                result = validate_pattern(
                    dataframe,
                    check['column'],
                    check['pattern'],
                    check.get('flags', 0)
                )
                pattern_results.append(result.to_dict())
                summary['all_errors'].extend(result.errors)
                summary['all_warnings'].extend(result.warnings)
                summary['all_info'].extend(result.info)
                if not result.passed:
                    summary['passed'] = False
            summary['results_by_rule']['pattern_checks'] = pattern_results
        
        # Foreign key validation
        if 'foreign_keys' in rules:
            fk_results = []
            for check in rules['foreign_keys']:
                result = validate_foreign_key(
                    dataframe,
                    check['column'],
                    check['valid_values']
                )
                fk_results.append(result.to_dict())
                summary['all_errors'].extend(result.errors)
                summary['all_warnings'].extend(result.warnings)
                summary['all_info'].extend(result.info)
                if not result.passed:
                    summary['passed'] = False
            summary['results_by_rule']['foreign_keys'] = fk_results
        
        # Count totals
        summary['total_errors'] = len(summary['all_errors'])
        summary['total_warnings'] = len(summary['all_warnings'])
        summary['total_info'] = len(summary['all_info'])
        
        logger.info(
            f"Validation complete: {summary['total_errors']} errors, "
            f"{summary['total_warnings']} warnings, {summary['total_info']} info"
        )
        
        return summary
    
    except Exception as e:
        logger.error(f"Failed to generate validation summary: {e}", exc_info=True)
        raise ValidationError(f"Validation summary generation failed: {str(e)}")


def validate_not_null(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    sample_nulls: int = 10
) -> ValidationResult:
    """
    Validate that specified columns don't contain null values.

    Args:
        dataframe: Pandas DataFrame to validate
        columns: Column name or list of column names that should not have nulls
        sample_nulls: Number of null row indices to include in details

    Returns:
        ValidationResult with null value information
    """
    result = ValidationResult()
    
    # Normalize to list
    if isinstance(columns, str):
        columns = [columns]
    
    try:
        for column in columns:
            if column not in dataframe.columns:
                result.add_error('not_null', f"Column '{column}' not found")
                continue
            
            col_data = dataframe[column]
            null_mask = col_data.isna()
            null_count = null_mask.sum()
            
            if null_count > 0:
                null_indices = dataframe[null_mask].index.tolist()[:sample_nulls]
                total_count = len(col_data)
                null_percentage = (null_count / total_count * 100) if total_count > 0 else 0
                
                result.add_error(
                    'not_null',
                    f"Column '{column}': {null_count} null values ({null_percentage:.1f}%) found",
                    {
                        'column': column,
                        'null_count': int(null_count),
                        'total_count': int(total_count),
                        'null_percentage': float(null_percentage),
                        'null_row_indices': null_indices
                    }
                )
            else:
                result.add_info('not_null', f"Column '{column}': No null values")
        
        logger.info(f"Not null validation complete")
        return result
    
    except Exception as e:
        logger.error(f"Failed to validate not null: {e}")
        raise ValidationError(f"Not null validation failed: {str(e)}")
