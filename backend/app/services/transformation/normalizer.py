"""
Data normalization service for transforming and standardizing DataFrames.

Provides functions for normalizing column names, type conversion, scaling numeric data,
encoding categorical variables, flattening nested structures, and pivoting data.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union, Tuple
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler, StandardScaler, LabelEncoder

logger = logging.getLogger(__name__)


class NormalizationError(Exception):
    """Base exception for normalization errors."""
    pass


def normalize_column_names(
    dataframe: pd.DataFrame,
    case: str = 'snake',
    remove_special: bool = True,
    max_length: Optional[int] = None
) -> pd.DataFrame:
    """
    Normalize column names to a standard format.

    Args:
        dataframe: Pandas DataFrame to normalize
        case: Naming convention ('snake', 'camel', 'pascal', 'lower', 'upper')
        remove_special: Whether to remove special characters
        max_length: Maximum column name length (None = no limit)

    Returns:
        DataFrame with normalized column names

    Raises:
        NormalizationError: If normalization fails
    """
    try:
        df = dataframe.copy()
        new_columns = []
        rename_map = {}
        
        for col in df.columns:
            original_col = col
            normalized_col = str(col)
            
            # Remove special characters if requested
            if remove_special:
                # Keep only alphanumeric and underscores/spaces
                normalized_col = re.sub(r'[^a-zA-Z0-9_\s]', '', normalized_col)
            
            # Replace multiple spaces with single space
            normalized_col = re.sub(r'\s+', ' ', normalized_col)
            
            # Apply case convention
            if case == 'snake':
                # Convert to snake_case
                # Replace spaces and hyphens with underscores
                normalized_col = normalized_col.replace(' ', '_').replace('-', '_')
                # Insert underscore before capital letters
                normalized_col = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', normalized_col)
                normalized_col = normalized_col.lower()
                # Remove multiple underscores
                normalized_col = re.sub(r'_+', '_', normalized_col)
                # Remove leading/trailing underscores
                normalized_col = normalized_col.strip('_')
                
            elif case == 'camel':
                # Convert to camelCase
                parts = re.split(r'[\s_-]+', normalized_col)
                normalized_col = parts[0].lower() + ''.join(word.capitalize() for word in parts[1:])
                
            elif case == 'pascal':
                # Convert to PascalCase
                parts = re.split(r'[\s_-]+', normalized_col)
                normalized_col = ''.join(word.capitalize() for word in parts)
                
            elif case == 'lower':
                normalized_col = normalized_col.lower().replace(' ', '_')
                
            elif case == 'upper':
                normalized_col = normalized_col.upper().replace(' ', '_')
            
            else:
                raise NormalizationError(f"Invalid case '{case}'. Valid options: snake, camel, pascal, lower, upper")
            
            # Apply max length if specified
            if max_length and len(normalized_col) > max_length:
                normalized_col = normalized_col[:max_length]
            
            # Ensure column name is not empty
            if not normalized_col:
                normalized_col = f"column_{len(new_columns)}"
            
            # Handle duplicate column names
            if normalized_col in new_columns:
                counter = 1
                base_name = normalized_col
                while normalized_col in new_columns:
                    normalized_col = f"{base_name}_{counter}"
                    counter += 1
            
            new_columns.append(normalized_col)
            rename_map[original_col] = normalized_col
        
        df.columns = new_columns
        
        # Log changes
        changed_count = sum(1 for old, new in rename_map.items() if old != new)
        logger.info(f"Normalized {changed_count} column names to {case} case")
        
        return df
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to normalize column names: {e}", exc_info=True)
        raise NormalizationError(f"Column name normalization failed: {str(e)}")


def convert_types(
    dataframe: pd.DataFrame,
    type_map: Dict[str, str],
    errors: str = 'raise'
) -> pd.DataFrame:
    """
    Convert columns to specified data types.

    Args:
        dataframe: Pandas DataFrame to convert
        type_map: Dictionary mapping column names to target types
                  Supported types: 'int', 'float', 'str', 'bool', 'datetime', 'category'
        errors: How to handle conversion errors:
                - 'raise': Raise an exception
                - 'coerce': Convert invalid values to NaN/NaT
                - 'ignore': Keep original values

    Returns:
        DataFrame with converted types

    Raises:
        NormalizationError: If type conversion fails
    """
    try:
        df = dataframe.copy()
        conversion_report = {}
        
        for column, target_type in type_map.items():
            if column not in df.columns:
                if errors == 'raise':
                    raise NormalizationError(f"Column '{column}' not found")
                else:
                    logger.warning(f"Column '{column}' not found, skipping")
                    continue
            
            original_dtype = df[column].dtype
            
            try:
                if target_type in ['int', 'integer', 'int64']:
                    if errors == 'coerce':
                        df[column] = pd.to_numeric(df[column], errors='coerce').astype('Int64')
                    else:
                        df[column] = df[column].astype('int64')
                
                elif target_type in ['float', 'float64']:
                    if errors == 'coerce':
                        df[column] = pd.to_numeric(df[column], errors='coerce')
                    else:
                        df[column] = df[column].astype('float64')
                
                elif target_type in ['str', 'string']:
                    df[column] = df[column].astype(str)
                
                elif target_type in ['bool', 'boolean']:
                    if errors == 'coerce':
                        # Handle common boolean representations
                        bool_map = {
                            'true': True, 'false': False,
                            't': True, 'f': False,
                            'yes': True, 'no': False,
                            'y': True, 'n': False,
                            '1': True, '0': False,
                            1: True, 0: False
                        }
                        df[column] = df[column].astype(str).str.lower().map(bool_map)
                    else:
                        df[column] = df[column].astype(bool)
                
                elif target_type in ['datetime', 'datetime64']:
                    if errors == 'coerce':
                        df[column] = pd.to_datetime(df[column], errors='coerce')
                    else:
                        df[column] = pd.to_datetime(df[column])
                
                elif target_type == 'category':
                    df[column] = df[column].astype('category')
                
                else:
                    raise NormalizationError(f"Unsupported type '{target_type}'")
                
                conversion_report[column] = {
                    'original_dtype': str(original_dtype),
                    'target_dtype': target_type,
                    'new_dtype': str(df[column].dtype),
                    'success': True
                }
                
                logger.debug(f"Converted '{column}' from {original_dtype} to {df[column].dtype}")
            
            except Exception as e:
                if errors == 'raise':
                    raise NormalizationError(f"Failed to convert '{column}' to {target_type}: {str(e)}")
                elif errors == 'ignore':
                    logger.warning(f"Failed to convert '{column}' to {target_type}, keeping original: {str(e)}")
                    conversion_report[column] = {
                        'original_dtype': str(original_dtype),
                        'target_dtype': target_type,
                        'success': False,
                        'error': str(e)
                    }
        
        logger.info(f"Converted types for {len(type_map)} columns")
        return df
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to convert types: {e}", exc_info=True)
        raise NormalizationError(f"Type conversion failed: {str(e)}")


def scale_numeric(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    method: str = 'minmax',
    feature_range: Tuple[float, float] = (0, 1)
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Scale numeric columns using various normalization methods.

    Args:
        dataframe: Pandas DataFrame to scale
        columns: Column name(s) to scale
        method: Scaling method:
            - 'minmax': Min-max scaling (default)
            - 'standard' or 'zscore': Z-score standardization
            - 'robust': Robust scaling using median and IQR
            - 'maxabs': Maximum absolute scaling
        feature_range: Target range for min-max scaling (default: 0 to 1)

    Returns:
        Tuple of (scaled_dataframe, scaling_parameters)
        scaling_parameters contains the scaler info for inverse transformation

    Raises:
        NormalizationError: If scaling fails
    """
    try:
        df = dataframe.copy()
        
        # Normalize to list
        if isinstance(columns, str):
            columns = [columns]
        
        # Validate columns exist
        missing_cols = set(columns) - set(df.columns)
        if missing_cols:
            raise NormalizationError(f"Columns not found: {', '.join(missing_cols)}")
        
        # Validate columns are numeric
        non_numeric = [col for col in columns if not pd.api.types.is_numeric_dtype(df[col])]
        if non_numeric:
            raise NormalizationError(f"Non-numeric columns cannot be scaled: {', '.join(non_numeric)}")
        
        scaling_params = {
            'method': method,
            'columns': columns,
            'parameters': {}
        }
        
        for column in columns:
            col_data = df[column].values.reshape(-1, 1)
            
            # Handle missing values
            non_null_mask = ~np.isnan(col_data.flatten())
            if not non_null_mask.any():
                logger.warning(f"Column '{column}' has no non-null values, skipping")
                continue
            
            if method == 'minmax':
                scaler = MinMaxScaler(feature_range=feature_range)
                
                # Fit only on non-null values
                scaler.fit(col_data[non_null_mask].reshape(-1, 1))
                
                # Transform all values
                scaled_values = col_data.copy()
                scaled_values[non_null_mask] = scaler.transform(col_data[non_null_mask].reshape(-1, 1))
                df[column] = scaled_values.flatten()
                
                scaling_params['parameters'][column] = {
                    'min': float(scaler.data_min_[0]),
                    'max': float(scaler.data_max_[0]),
                    'feature_range': feature_range
                }
            
            elif method in ['standard', 'zscore']:
                scaler = StandardScaler()
                
                # Fit only on non-null values
                scaler.fit(col_data[non_null_mask].reshape(-1, 1))
                
                # Transform all values
                scaled_values = col_data.copy()
                scaled_values[non_null_mask] = scaler.transform(col_data[non_null_mask].reshape(-1, 1))
                df[column] = scaled_values.flatten()
                
                scaling_params['parameters'][column] = {
                    'mean': float(scaler.mean_[0]),
                    'std': float(scaler.scale_[0])
                }
            
            elif method == 'robust':
                # Robust scaling using median and IQR
                col_series = df[column]
                median = col_series.median()
                q1 = col_series.quantile(0.25)
                q3 = col_series.quantile(0.75)
                iqr = q3 - q1
                
                if iqr == 0:
                    logger.warning(f"Column '{column}' has IQR of 0, skipping robust scaling")
                    continue
                
                df[column] = (col_series - median) / iqr
                
                scaling_params['parameters'][column] = {
                    'median': float(median),
                    'q1': float(q1),
                    'q3': float(q3),
                    'iqr': float(iqr)
                }
            
            elif method == 'maxabs':
                # Scale by maximum absolute value
                max_abs = df[column].abs().max()
                
                if max_abs == 0:
                    logger.warning(f"Column '{column}' has max absolute value of 0, skipping")
                    continue
                
                df[column] = df[column] / max_abs
                
                scaling_params['parameters'][column] = {
                    'max_abs': float(max_abs)
                }
            
            else:
                raise NormalizationError(
                    f"Invalid scaling method '{method}'. "
                    f"Valid methods: minmax, standard, zscore, robust, maxabs"
                )
        
        logger.info(f"Scaled {len(columns)} numeric columns using {method} method")
        return df, scaling_params
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to scale numeric data: {e}", exc_info=True)
        raise NormalizationError(f"Numeric scaling failed: {str(e)}")


def encode_categorical(
    dataframe: pd.DataFrame,
    columns: Union[str, List[str]],
    method: str = 'onehot',
    drop_first: bool = False
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Encode categorical columns as numeric values.

    Args:
        dataframe: Pandas DataFrame to encode
        columns: Column name(s) to encode
        method: Encoding method:
            - 'onehot': One-hot encoding (creates binary columns)
            - 'label': Label encoding (converts to integers)
            - 'ordinal': Ordinal encoding (maintains order)
        drop_first: For one-hot encoding, drop first category to avoid multicollinearity

    Returns:
        Tuple of (encoded_dataframe, encoding_parameters)
        encoding_parameters contains the mapping for decoding

    Raises:
        NormalizationError: If encoding fails
    """
    try:
        df = dataframe.copy()
        
        # Normalize to list
        if isinstance(columns, str):
            columns = [columns]
        
        # Validate columns exist
        missing_cols = set(columns) - set(df.columns)
        if missing_cols:
            raise NormalizationError(f"Columns not found: {', '.join(missing_cols)}")
        
        encoding_params = {
            'method': method,
            'columns': columns,
            'mappings': {}
        }
        
        if method == 'onehot':
            # One-hot encoding
            df_encoded = pd.get_dummies(
                df,
                columns=columns,
                drop_first=drop_first,
                prefix=columns,
                prefix_sep='_'
            )
            
            # Record which columns were created
            for column in columns:
                new_cols = [col for col in df_encoded.columns if col.startswith(f"{column}_")]
                encoding_params['mappings'][column] = {
                    'new_columns': new_cols,
                    'drop_first': drop_first
                }
            
            df = df_encoded
            logger.info(f"One-hot encoded {len(columns)} columns")
        
        elif method == 'label':
            # Label encoding
            for column in columns:
                le = LabelEncoder()
                
                # Fit encoder
                non_null_values = df[column].dropna()
                if len(non_null_values) == 0:
                    logger.warning(f"Column '{column}' has no non-null values, skipping")
                    continue
                
                le.fit(non_null_values)
                
                # Transform values
                encoded_values = df[column].copy()
                non_null_mask = df[column].notna()
                encoded_values[non_null_mask] = le.transform(df[column][non_null_mask])
                
                df[column] = encoded_values
                
                # Store mapping
                encoding_params['mappings'][column] = {
                    'classes': le.classes_.tolist(),
                    'mapping': {label: int(idx) for idx, label in enumerate(le.classes_)}
                }
            
            logger.info(f"Label encoded {len(columns)} columns")
        
        elif method == 'ordinal':
            # Ordinal encoding (similar to label but preserves order)
            for column in columns:
                unique_values = df[column].dropna().unique()
                sorted_values = sorted(unique_values)
                
                # Create mapping
                ordinal_map = {val: idx for idx, val in enumerate(sorted_values)}
                
                # Apply mapping
                df[column] = df[column].map(ordinal_map)
                
                # Store mapping
                encoding_params['mappings'][column] = {
                    'order': sorted_values.tolist() if hasattr(sorted_values, 'tolist') else list(sorted_values),
                    'mapping': ordinal_map
                }
            
            logger.info(f"Ordinal encoded {len(columns)} columns")
        
        else:
            raise NormalizationError(
                f"Invalid encoding method '{method}'. "
                f"Valid methods: onehot, label, ordinal"
            )
        
        return df, encoding_params
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to encode categorical data: {e}", exc_info=True)
        raise NormalizationError(f"Categorical encoding failed: {str(e)}")


def flatten_nested_data(
    data: Union[Dict, List],
    parent_key: str = '',
    separator: str = '_'
) -> Dict:
    """
    Flatten nested JSON/dictionary structures.

    Args:
        data: Nested dictionary or list to flatten
        parent_key: Parent key for nested structure (used in recursion)
        separator: Separator for nested keys (default: '_')

    Returns:
        Flattened dictionary

    Raises:
        NormalizationError: If flattening fails

    Example:
        Input: {'a': {'b': 1, 'c': 2}, 'd': 3}
        Output: {'a_b': 1, 'a_c': 2, 'd': 3}
    """
    try:
        items = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}{separator}{key}" if parent_key else key
                
                if isinstance(value, dict):
                    # Recursively flatten nested dict
                    items.extend(flatten_nested_data(value, new_key, separator).items())
                elif isinstance(value, list):
                    # Handle lists
                    if all(isinstance(item, (dict, list)) for item in value):
                        # List of dicts/lists - flatten each with index
                        for idx, item in enumerate(value):
                            indexed_key = f"{new_key}{separator}{idx}"
                            if isinstance(item, (dict, list)):
                                items.extend(flatten_nested_data(item, indexed_key, separator).items())
                            else:
                                items.append((indexed_key, item))
                    else:
                        # List of primitives - keep as is
                        items.append((new_key, value))
                else:
                    # Primitive value
                    items.append((new_key, value))
        
        elif isinstance(data, list):
            # Handle root-level list
            for idx, item in enumerate(data):
                new_key = f"{parent_key}{separator}{idx}" if parent_key else str(idx)
                if isinstance(item, (dict, list)):
                    items.extend(flatten_nested_data(item, new_key, separator).items())
                else:
                    items.append((new_key, item))
        
        else:
            # Primitive value at root
            items.append((parent_key or 'value', data))
        
        result = dict(items)
        logger.debug(f"Flattened nested data: {len(result)} keys")
        return result
    
    except Exception as e:
        logger.error(f"Failed to flatten nested data: {e}", exc_info=True)
        raise NormalizationError(f"Data flattening failed: {str(e)}")


def pivot_data(
    dataframe: pd.DataFrame,
    index: Union[str, List[str]],
    columns: str,
    values: Union[str, List[str]],
    aggfunc: str = 'mean',
    fill_value: Any = None
) -> pd.DataFrame:
    """
    Reshape data using pivot operation.

    Args:
        dataframe: Pandas DataFrame to pivot
        index: Column(s) to use as index
        columns: Column to use for creating new columns
        values: Column(s) to aggregate
        aggfunc: Aggregation function ('mean', 'sum', 'count', 'min', 'max', 'first', 'last')
        fill_value: Value to replace missing values after pivot

    Returns:
        Pivoted DataFrame

    Raises:
        NormalizationError: If pivot operation fails
    """
    try:
        # Validate columns exist
        all_columns = [index] if isinstance(index, str) else index
        all_columns.append(columns)
        if isinstance(values, str):
            all_columns.append(values)
        else:
            all_columns.extend(values)
        
        missing_cols = set(all_columns) - set(dataframe.columns)
        if missing_cols:
            raise NormalizationError(f"Columns not found: {', '.join(missing_cols)}")
        
        # Perform pivot
        pivoted = pd.pivot_table(
            dataframe,
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
            fill_value=fill_value
        )
        
        # Flatten multi-level column names if present
        if isinstance(pivoted.columns, pd.MultiIndex):
            pivoted.columns = ['_'.join(map(str, col)).strip() for col in pivoted.columns.values]
        
        # Reset index to make it a regular column
        pivoted = pivoted.reset_index()
        
        logger.info(
            f"Pivoted data: {len(dataframe)} rows → {len(pivoted)} rows, "
            f"{len(dataframe.columns)} cols → {len(pivoted.columns)} cols"
        )
        
        return pivoted
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to pivot data: {e}", exc_info=True)
        raise NormalizationError(f"Data pivot failed: {str(e)}")


def unpivot_data(
    dataframe: pd.DataFrame,
    id_vars: Union[str, List[str]],
    value_vars: Optional[Union[str, List[str]]] = None,
    var_name: str = 'variable',
    value_name: str = 'value'
) -> pd.DataFrame:
    """
    Unpivot (melt) a DataFrame from wide to long format.

    Args:
        dataframe: Pandas DataFrame to unpivot
        id_vars: Column(s) to use as identifier variables
        value_vars: Column(s) to unpivot (None = all columns except id_vars)
        var_name: Name for the variable column
        value_name: Name for the value column

    Returns:
        Unpivoted DataFrame

    Raises:
        NormalizationError: If unpivot operation fails
    """
    try:
        # Normalize to list
        if isinstance(id_vars, str):
            id_vars = [id_vars]
        
        # Validate id_vars exist
        missing_cols = set(id_vars) - set(dataframe.columns)
        if missing_cols:
            raise NormalizationError(f"ID columns not found: {', '.join(missing_cols)}")
        
        # Perform melt
        melted = pd.melt(
            dataframe,
            id_vars=id_vars,
            value_vars=value_vars,
            var_name=var_name,
            value_name=value_name
        )
        
        logger.info(
            f"Unpivoted data: {len(dataframe)} rows → {len(melted)} rows, "
            f"{len(dataframe.columns)} cols → {len(melted.columns)} cols"
        )
        
        return melted
    
    except NormalizationError:
        raise
    except Exception as e:
        logger.error(f"Failed to unpivot data: {e}", exc_info=True)
        raise NormalizationError(f"Data unpivot failed: {str(e)}")


def normalize_dataframe(
    dataframe: pd.DataFrame,
    normalize_columns: bool = True,
    convert_types: Optional[Dict[str, str]] = None,
    scale_numeric_columns: Optional[List[str]] = None,
    encode_categorical_columns: Optional[List[str]] = None,
    scaling_method: str = 'minmax',
    encoding_method: str = 'onehot'
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Apply comprehensive normalization pipeline to a DataFrame.

    Args:
        dataframe: Pandas DataFrame to normalize
        normalize_columns: Whether to normalize column names
        convert_types: Type conversion map
        scale_numeric_columns: Columns to scale
        encode_categorical_columns: Columns to encode
        scaling_method: Method for scaling ('minmax', 'standard', etc.)
        encoding_method: Method for encoding ('onehot', 'label', etc.)

    Returns:
        Tuple of (normalized_dataframe, normalization_report)

    Raises:
        NormalizationError: If normalization fails
    """
    try:
        df = dataframe.copy()
        report = {
            'operations': [],
            'original_shape': dataframe.shape,
            'parameters': {}
        }
        
        # 1. Normalize column names
        if normalize_columns:
            df = normalize_column_names(df)
            report['operations'].append('normalize_column_names')
        
        # 2. Convert types
        if convert_types:
            df = convert_types(df, convert_types)
            report['operations'].append('convert_types')
            report['parameters']['type_conversions'] = convert_types
        
        # 3. Scale numeric columns
        if scale_numeric_columns:
            df, scaling_params = scale_numeric(df, scale_numeric_columns, method=scaling_method)
            report['operations'].append('scale_numeric')
            report['parameters']['scaling'] = scaling_params
        
        # 4. Encode categorical columns
        if encode_categorical_columns:
            df, encoding_params = encode_categorical(df, encode_categorical_columns, method=encoding_method)
            report['operations'].append('encode_categorical')
            report['parameters']['encoding'] = encoding_params
        
        report['final_shape'] = df.shape
        
        logger.info(
            f"Normalization complete: {len(report['operations'])} operations, "
            f"shape {report['original_shape']} → {report['final_shape']}"
        )
        
        return df, report
    
    except Exception as e:
        logger.error(f"Failed to normalize dataframe: {e}", exc_info=True)
        raise NormalizationError(f"DataFrame normalization failed: {str(e)}")
