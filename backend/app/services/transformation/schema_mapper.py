"""
Schema mapping service for transforming data between different schemas.

Allows users to map their dataset columns to predefined schemas with automatic
suggestion, validation, and transformation capabilities.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Tuple
from difflib import SequenceMatcher
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class SchemaMappingError(Exception):
    """Base exception for schema mapping errors."""
    pass


class MappingValidationError(SchemaMappingError):
    """Raised when mapping validation fails."""
    pass


def create_mapping(
    source_columns: List[str],
    target_schema: Dict[str, Any],
    auto_suggest: bool = True
) -> Dict[str, Any]:
    """
    Generate column mappings from source columns to target schema.

    Args:
        source_columns: List of source column names
        target_schema: Target schema definition with column specifications:
            {
                'column_name': {
                    'type': 'string|integer|float|boolean|datetime',
                    'required': True|False,
                    'description': 'Column description'
                }
            }
        auto_suggest: Whether to auto-suggest mappings based on name similarity

    Returns:
        Dictionary with mapping information:
        {
            'mappings': {
                'source_col': 'target_col',
                ...
            },
            'unmapped_source': ['col1', ...],
            'unmapped_target': ['col1', ...],
            'suggestions': {
                'source_col': [('target_col', confidence), ...],
                ...
            }
        }

    Raises:
        SchemaMappingError: If mapping creation fails
    """
    try:
        logger.info(f"Creating mapping for {len(source_columns)} source columns to {len(target_schema)} target columns")
        
        result = {
            'mappings': {},
            'unmapped_source': [],
            'unmapped_target': [],
            'suggestions': {}
        }
        
        target_columns = list(target_schema.keys())
        mapped_sources = set()
        mapped_targets = set()
        
        # First pass: exact matches (case-insensitive)
        for source_col in source_columns:
            source_normalized = _normalize_column_name(source_col)
            
            for target_col in target_columns:
                target_normalized = _normalize_column_name(target_col)
                
                if source_normalized == target_normalized:
                    result['mappings'][source_col] = target_col
                    mapped_sources.add(source_col)
                    mapped_targets.add(target_col)
                    logger.debug(f"Exact match: {source_col} → {target_col}")
                    break
        
        # Second pass: auto-suggest for unmapped columns
        if auto_suggest:
            for source_col in source_columns:
                if source_col not in mapped_sources:
                    suggestions = suggest_mappings([source_col], target_columns, top_n=3)
                    
                    if suggestions.get(source_col):
                        result['suggestions'][source_col] = suggestions[source_col]
                        
                        # Auto-map if confidence is very high (>0.9)
                        best_match = suggestions[source_col][0]
                        if best_match[1] > 0.9 and best_match[0] not in mapped_targets:
                            result['mappings'][source_col] = best_match[0]
                            mapped_sources.add(source_col)
                            mapped_targets.add(best_match[0])
                            logger.debug(f"Auto-mapped (high confidence): {source_col} → {best_match[0]} ({best_match[1]:.2f})")
        
        # Identify unmapped columns
        result['unmapped_source'] = [col for col in source_columns if col not in mapped_sources]
        result['unmapped_target'] = [col for col in target_columns if col not in mapped_targets]
        
        logger.info(
            f"Mapping created: {len(result['mappings'])} mapped, "
            f"{len(result['unmapped_source'])} unmapped source, "
            f"{len(result['unmapped_target'])} unmapped target"
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Failed to create mapping: {e}", exc_info=True)
        raise SchemaMappingError(f"Mapping creation failed: {str(e)}")


def apply_mapping(
    dataframe: pd.DataFrame,
    mapping: Dict[str, str],
    drop_unmapped: bool = False
) -> pd.DataFrame:
    """
    Transform DataFrame using column mapping.

    Args:
        dataframe: Source DataFrame to transform
        mapping: Dictionary mapping source column names to target column names
                 {'source_col': 'target_col', ...}
        drop_unmapped: Whether to drop columns not in the mapping

    Returns:
        Transformed DataFrame with renamed columns

    Raises:
        SchemaMappingError: If mapping application fails
    """
    try:
        logger.info(f"Applying mapping to DataFrame with {len(dataframe.columns)} columns")
        
        # Validate that mapped columns exist
        missing_columns = set(mapping.keys()) - set(dataframe.columns)
        if missing_columns:
            raise SchemaMappingError(
                f"Mapping references columns not in DataFrame: {', '.join(missing_columns)}"
            )
        
        # Create copy to avoid modifying original
        df_transformed = dataframe.copy()
        
        # Rename columns according to mapping
        df_transformed = df_transformed.rename(columns=mapping)
        
        # Drop unmapped columns if requested
        if drop_unmapped:
            target_columns = set(mapping.values())
            columns_to_keep = [col for col in df_transformed.columns if col in target_columns]
            df_transformed = df_transformed[columns_to_keep]
            logger.debug(f"Dropped {len(df_transformed.columns) - len(columns_to_keep)} unmapped columns")
        
        logger.info(f"Mapping applied: DataFrame now has {len(df_transformed.columns)} columns")
        return df_transformed
    
    except SchemaMappingError:
        raise
    except Exception as e:
        logger.error(f"Failed to apply mapping: {e}", exc_info=True)
        raise SchemaMappingError(f"Mapping application failed: {str(e)}")


def suggest_mappings(
    source_columns: List[str],
    target_columns: List[str],
    top_n: int = 5,
    min_confidence: float = 0.3
) -> Dict[str, List[Tuple[str, float]]]:
    """
    Auto-suggest column mappings based on name similarity.

    Args:
        source_columns: List of source column names
        target_columns: List of target column names
        top_n: Number of suggestions per source column
        min_confidence: Minimum similarity score to include (0.0 to 1.0)

    Returns:
        Dictionary mapping source columns to list of (target_column, confidence) tuples:
        {
            'source_col': [('target_col1', 0.95), ('target_col2', 0.75), ...],
            ...
        }

    Raises:
        SchemaMappingError: If suggestion generation fails
    """
    try:
        logger.info(f"Suggesting mappings for {len(source_columns)} source columns")
        
        suggestions = {}
        
        for source_col in source_columns:
            source_normalized = _normalize_column_name(source_col)
            similarities = []
            
            for target_col in target_columns:
                target_normalized = _normalize_column_name(target_col)
                
                # Calculate similarity score
                similarity = _calculate_similarity(source_normalized, target_normalized)
                
                # Add semantic boost for common patterns
                similarity = _apply_semantic_boost(source_col, target_col, similarity)
                
                if similarity >= min_confidence:
                    similarities.append((target_col, similarity))
            
            # Sort by similarity (descending) and take top N
            similarities.sort(key=lambda x: x[1], reverse=True)
            suggestions[source_col] = similarities[:top_n]
            
            if suggestions[source_col]:
                logger.debug(
                    f"Suggestions for '{source_col}': "
                    f"{[(col, f'{conf:.2f}') for col, conf in suggestions[source_col]]}"
                )
        
        return suggestions
    
    except Exception as e:
        logger.error(f"Failed to suggest mappings: {e}", exc_info=True)
        raise SchemaMappingError(f"Mapping suggestion failed: {str(e)}")


def validate_mapping(
    dataframe: pd.DataFrame,
    mapping: Dict[str, str],
    target_schema: Dict[str, Any],
    strict: bool = False
) -> Dict[str, Any]:
    """
    Validate that a mapping is compatible with target schema.

    Args:
        dataframe: Source DataFrame
        mapping: Column mapping dictionary
        target_schema: Target schema definition with type and constraint information
        strict: If True, require all target columns to be mapped

    Returns:
        Validation result dictionary:
        {
            'valid': bool,
            'errors': [...],
            'warnings': [...],
            'mapped_columns': [...],
            'missing_required': [...],
            'type_mismatches': [...]
        }

    Raises:
        MappingValidationError: If validation fails with strict=True
    """
    try:
        logger.info("Validating mapping against target schema")
        
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'mapped_columns': [],
            'missing_required': [],
            'type_mismatches': []
        }
        
        # Check that all mapped source columns exist
        missing_source = set(mapping.keys()) - set(dataframe.columns)
        if missing_source:
            error = f"Source columns not found in DataFrame: {', '.join(missing_source)}"
            result['errors'].append(error)
            result['valid'] = False
        
        # Check that all mapped target columns exist in schema
        invalid_targets = set(mapping.values()) - set(target_schema.keys())
        if invalid_targets:
            error = f"Target columns not found in schema: {', '.join(invalid_targets)}"
            result['errors'].append(error)
            result['valid'] = False
        
        # Track mapped columns
        result['mapped_columns'] = list(mapping.values())
        
        # Check for required columns
        for target_col, col_spec in target_schema.items():
            is_required = col_spec.get('required', False)
            is_mapped = target_col in mapping.values()
            
            if is_required and not is_mapped:
                result['missing_required'].append(target_col)
                error = f"Required target column '{target_col}' is not mapped"
                result['errors'].append(error)
                result['valid'] = False
        
        # Check type compatibility
        for source_col, target_col in mapping.items():
            if source_col not in dataframe.columns:
                continue
            
            if target_col not in target_schema:
                continue
            
            source_dtype = dataframe[source_col].dtype
            target_type = target_schema[target_col].get('type', 'string')
            
            compatible = _check_type_compatibility(source_dtype, target_type)
            
            if not compatible:
                mismatch = {
                    'source_column': source_col,
                    'target_column': target_col,
                    'source_type': str(source_dtype),
                    'target_type': target_type
                }
                result['type_mismatches'].append(mismatch)
                
                warning = (
                    f"Type mismatch: {source_col} ({source_dtype}) "
                    f"mapped to {target_col} (expected {target_type})"
                )
                result['warnings'].append(warning)
        
        # Check for duplicate mappings (multiple sources to same target)
        target_counts = {}
        for target_col in mapping.values():
            target_counts[target_col] = target_counts.get(target_col, 0) + 1
        
        duplicates = {col: count for col, count in target_counts.items() if count > 1}
        if duplicates:
            for target_col, count in duplicates.items():
                warning = f"Multiple source columns mapped to '{target_col}' ({count} sources)"
                result['warnings'].append(warning)
        
        # Summary
        logger.info(
            f"Validation complete: valid={result['valid']}, "
            f"{len(result['errors'])} errors, {len(result['warnings'])} warnings"
        )
        
        # Raise exception in strict mode if validation failed
        if strict and not result['valid']:
            error_msg = "; ".join(result['errors'])
            raise MappingValidationError(f"Mapping validation failed: {error_msg}")
        
        return result
    
    except MappingValidationError:
        raise
    except Exception as e:
        logger.error(f"Failed to validate mapping: {e}", exc_info=True)
        raise SchemaMappingError(f"Mapping validation failed: {str(e)}")


def transform_with_schema(
    dataframe: pd.DataFrame,
    mapping: Dict[str, str],
    target_schema: Dict[str, Any],
    convert_types: bool = True,
    fill_missing: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Transform DataFrame to match target schema with type conversion.

    Args:
        dataframe: Source DataFrame
        mapping: Column mapping dictionary
        target_schema: Target schema definition
        convert_types: Whether to convert column types to match schema
        fill_missing: Whether to add missing required columns with default values

    Returns:
        Tuple of (transformed_dataframe, transformation_report)

    Raises:
        SchemaMappingError: If transformation fails
    """
    try:
        logger.info("Transforming DataFrame to match target schema")
        
        report = {
            'columns_renamed': 0,
            'columns_added': 0,
            'types_converted': 0,
            'operations': []
        }
        
        # Apply column mapping
        df_transformed = apply_mapping(dataframe, mapping)
        report['columns_renamed'] = len(mapping)
        report['operations'].append(f"Renamed {len(mapping)} columns")
        
        # Add missing required columns
        if fill_missing:
            for target_col, col_spec in target_schema.items():
                if col_spec.get('required', False) and target_col not in df_transformed.columns:
                    default_value = _get_default_value(col_spec.get('type', 'string'))
                    df_transformed[target_col] = default_value
                    report['columns_added'] += 1
                    report['operations'].append(
                        f"Added required column '{target_col}' with default value"
                    )
        
        # Convert types
        if convert_types:
            for target_col in df_transformed.columns:
                if target_col in target_schema:
                    target_type = target_schema[target_col].get('type', 'string')
                    
                    try:
                        df_transformed[target_col] = _convert_column_type(
                            df_transformed[target_col],
                            target_type
                        )
                        report['types_converted'] += 1
                        report['operations'].append(
                            f"Converted '{target_col}' to {target_type}"
                        )
                    except Exception as e:
                        logger.warning(f"Failed to convert {target_col} to {target_type}: {e}")
        
        logger.info(
            f"Transformation complete: {report['columns_renamed']} renamed, "
            f"{report['columns_added']} added, {report['types_converted']} converted"
        )
        
        return df_transformed, report
    
    except Exception as e:
        logger.error(f"Failed to transform with schema: {e}", exc_info=True)
        raise SchemaMappingError(f"Schema transformation failed: {str(e)}")


# Helper functions

def _normalize_column_name(column_name: str) -> str:
    """Normalize column name for comparison."""
    # Convert to lowercase
    normalized = column_name.lower()
    
    # Remove special characters except underscores
    normalized = re.sub(r'[^a-z0-9_]', '', normalized)
    
    # Remove multiple underscores
    normalized = re.sub(r'_+', '_', normalized)
    
    # Remove leading/trailing underscores
    normalized = normalized.strip('_')
    
    return normalized


def _calculate_similarity(str1: str, str2: str) -> float:
    """
    Calculate similarity score between two strings.
    
    Uses SequenceMatcher for fuzzy string matching.
    
    Returns:
        Similarity score between 0.0 and 1.0
    """
    return SequenceMatcher(None, str1, str2).ratio()


def _apply_semantic_boost(source: str, target: str, base_similarity: float) -> float:
    """
    Apply semantic boost to similarity score based on common patterns.
    
    Args:
        source: Source column name
        target: Target column name
        base_similarity: Base similarity score
    
    Returns:
        Adjusted similarity score
    """
    # Common abbreviations and patterns
    patterns = [
        ('id', 'identifier'),
        ('num', 'number'),
        ('qty', 'quantity'),
        ('amt', 'amount'),
        ('desc', 'description'),
        ('addr', 'address'),
        ('temp', 'temperature'),
        ('val', 'value'),
        ('dt', 'date'),
        ('ts', 'timestamp'),
        ('cat', 'category'),
        ('ref', 'reference'),
    ]
    
    source_lower = source.lower()
    target_lower = target.lower()
    
    # Check for pattern matches
    for abbr, full in patterns:
        if (abbr in source_lower and full in target_lower) or \
           (full in source_lower and abbr in target_lower):
            # Boost similarity for known abbreviation patterns
            return min(base_similarity + 0.2, 1.0)
    
    # Check for common prefixes/suffixes
    common_affixes = ['is_', 'has_', 'get_', 'set_', '_id', '_name', '_date', '_time']
    
    for affix in common_affixes:
        source_stripped = source_lower.replace(affix, '')
        target_stripped = target_lower.replace(affix, '')
        
        if source_stripped and target_stripped and source_stripped == target_stripped:
            return min(base_similarity + 0.15, 1.0)
    
    return base_similarity


def _check_type_compatibility(source_dtype, target_type: str) -> bool:
    """
    Check if source data type is compatible with target type.
    
    Args:
        source_dtype: Pandas dtype
        target_type: Target type string
    
    Returns:
        True if types are compatible
    """
    source_str = str(source_dtype).lower()
    target_lower = target_type.lower()
    
    # Type compatibility matrix
    if target_lower in ['string', 'str', 'text']:
        return True  # Any type can be converted to string
    
    elif target_lower in ['integer', 'int']:
        return 'int' in source_str or 'uint' in source_str
    
    elif target_lower in ['float', 'double', 'decimal', 'numeric']:
        return 'float' in source_str or 'int' in source_str
    
    elif target_lower in ['boolean', 'bool']:
        return 'bool' in source_str or 'int' in source_str
    
    elif target_lower in ['datetime', 'timestamp', 'date']:
        return 'datetime' in source_str or 'object' in source_str
    
    else:
        # Unknown target type, assume compatible
        return True


def _get_default_value(data_type: str) -> Any:
    """Get default value for a data type."""
    defaults = {
        'string': '',
        'str': '',
        'text': '',
        'integer': 0,
        'int': 0,
        'float': 0.0,
        'double': 0.0,
        'decimal': 0.0,
        'boolean': False,
        'bool': False,
        'datetime': pd.NaT,
        'date': pd.NaT,
        'timestamp': pd.NaT,
    }
    
    return defaults.get(data_type.lower(), None)


def _convert_column_type(series: pd.Series, target_type: str) -> pd.Series:
    """
    Convert pandas Series to target type.
    
    Args:
        series: Pandas Series to convert
        target_type: Target type string
    
    Returns:
        Converted Series
    """
    target_lower = target_type.lower()
    
    if target_lower in ['string', 'str', 'text']:
        return series.astype(str)
    
    elif target_lower in ['integer', 'int']:
        return pd.to_numeric(series, errors='coerce').astype('Int64')
    
    elif target_lower in ['float', 'double', 'decimal', 'numeric']:
        return pd.to_numeric(series, errors='coerce')
    
    elif target_lower in ['boolean', 'bool']:
        # Handle common boolean representations
        if series.dtype == 'object':
            bool_map = {
                'true': True, 'false': False,
                't': True, 'f': False,
                'yes': True, 'no': False,
                'y': True, 'n': False,
                '1': True, '0': False,
            }
            return series.astype(str).str.lower().map(bool_map)
        else:
            return series.astype(bool)
    
    elif target_lower in ['datetime', 'timestamp', 'date']:
        return pd.to_datetime(series, errors='coerce')
    
    else:
        logger.warning(f"Unknown target type '{target_type}', keeping original type")
        return series


def generate_schema_from_dataframe(
    dataframe: pd.DataFrame,
    mark_all_required: bool = False
) -> Dict[str, Any]:
    """
    Generate a target schema from an existing DataFrame.
    
    Args:
        dataframe: DataFrame to analyze
        mark_all_required: Whether to mark all columns as required
    
    Returns:
        Schema definition dictionary
    """
    try:
        schema = {}
        
        for column in dataframe.columns:
            dtype = dataframe[column].dtype
            
            # Infer type
            if pd.api.types.is_integer_dtype(dtype):
                col_type = 'integer'
            elif pd.api.types.is_float_dtype(dtype):
                col_type = 'float'
            elif pd.api.types.is_bool_dtype(dtype):
                col_type = 'boolean'
            elif pd.api.types.is_datetime64_any_dtype(dtype):
                col_type = 'datetime'
            else:
                col_type = 'string'
            
            schema[column] = {
                'type': col_type,
                'required': mark_all_required,
                'nullable': dataframe[column].isna().any(),
                'unique_count': int(dataframe[column].nunique())
            }
        
        logger.info(f"Generated schema for {len(schema)} columns")
        return schema
    
    except Exception as e:
        logger.error(f"Failed to generate schema: {e}", exc_info=True)
        raise SchemaMappingError(f"Schema generation failed: {str(e)}")


# Export main functions
__all__ = [
    "create_mapping",
    "apply_mapping",
    "suggest_mappings",
    "validate_mapping",
    "transform_with_schema",
    "generate_schema_from_dataframe",
    "SchemaMappingError",
    "MappingValidationError"
]
