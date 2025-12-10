"""
Transformation pipeline orchestrator for chaining data transformations.

Provides a flexible pipeline system for applying multiple transformation steps
in sequence with comprehensive reporting and error handling.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime
import pandas as pd

from app.services.transformation.cleaner import (
    remove_duplicates,
    handle_missing_values,
    trim_whitespace,
    standardize_case,
    remove_outliers,
    clean_numeric,
    CleaningReport
)
from app.services.transformation.normalizer import (
    normalize_column_names,
    scale_numeric,
    encode_categorical,
    NormalizationError
)

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """Base exception for pipeline errors."""
    pass


class TransformationStep:
    """
    Represents a single transformation step in a pipeline.
    """
    
    def __init__(
        self,
        name: str,
        func: Callable,
        kwargs: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ):
        """
        Initialize a transformation step.
        
        Args:
            name: Name of the transformation step
            func: Function to execute
            kwargs: Keyword arguments to pass to the function
            description: Optional description of what this step does
        """
        self.name = name
        self.func = func
        self.kwargs = kwargs or {}
        self.description = description or f"Execute {name}"
        self.executed = False
        self.success = False
        self.error = None
        self.duration = None
        self.report = None
    
    def execute(self, dataframe: pd.DataFrame) -> Tuple[pd.DataFrame, Any]:
        """
        Execute the transformation step.
        
        Args:
            dataframe: Input DataFrame
        
        Returns:
            Tuple of (transformed_dataframe, step_report)
        """
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Executing step: {self.name}")
            
            # Execute the transformation function
            result = self.func(dataframe, **self.kwargs)
            
            # Handle different return types
            if isinstance(result, tuple):
                # Function returns (dataframe, report)
                df_output, step_report = result
            else:
                # Function returns only dataframe
                df_output = result
                step_report = None
            
            self.executed = True
            self.success = True
            self.report = step_report
            
            end_time = datetime.utcnow()
            self.duration = (end_time - start_time).total_seconds()
            
            logger.info(f"Step '{self.name}' completed in {self.duration:.2f}s")
            return df_output, step_report
        
        except Exception as e:
            self.executed = True
            self.success = False
            self.error = str(e)
            
            end_time = datetime.utcnow()
            self.duration = (end_time - start_time).total_seconds()
            
            logger.error(f"Step '{self.name}' failed: {e}")
            raise PipelineError(f"Step '{self.name}' failed: {str(e)}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert step to dictionary representation."""
        result = {
            'name': self.name,
            'description': self.description,
            'executed': self.executed,
            'success': self.success,
            'duration': self.duration,
            'kwargs': self.kwargs
        }
        
        if self.error:
            result['error'] = self.error
        
        if self.report:
            # Handle CleaningReport objects
            if hasattr(self.report, 'to_dict'):
                result['report'] = self.report.to_dict()
            elif isinstance(self.report, dict):
                result['report'] = self.report
        
        return result


class TransformationPipeline:
    """
    Orchestrates multiple transformation steps in sequence.
    
    Features:
    - Add transformation steps dynamically
    - Execute all steps in order
    - Comprehensive reporting
    - Error handling with rollback
    - Step validation
    """
    
    def __init__(self, name: str = "Transformation Pipeline"):
        """
        Initialize transformation pipeline.
        
        Args:
            name: Name of the pipeline
        """
        self.name = name
        self.steps: List[TransformationStep] = []
        self.executed = False
        self.success = False
        self.input_shape = None
        self.output_shape = None
        self.total_duration = None
        self.start_time = None
        self.end_time = None
    
    def add_step(
        self,
        step_func: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> 'TransformationPipeline':
        """
        Add a transformation step to the pipeline.
        
        Args:
            step_func: Function to execute
            name: Optional name for the step (defaults to function name)
            description: Optional description
            **kwargs: Keyword arguments to pass to the function
        
        Returns:
            Self for method chaining
        """
        step_name = name or step_func.__name__
        
        step = TransformationStep(
            name=step_name,
            func=step_func,
            kwargs=kwargs,
            description=description
        )
        
        self.steps.append(step)
        logger.debug(f"Added step '{step_name}' to pipeline '{self.name}'")
        
        return self
    
    def run(
        self,
        dataframe: pd.DataFrame,
        stop_on_error: bool = True
    ) -> pd.DataFrame:
        """
        Execute all transformation steps in order.
        
        Args:
            dataframe: Input DataFrame to transform
            stop_on_error: If True, stop execution on first error
        
        Returns:
            Transformed DataFrame
        
        Raises:
            PipelineError: If a step fails and stop_on_error=True
        """
        if not self.steps:
            logger.warning("No transformation steps defined in pipeline")
            return dataframe
        
        logger.info(f"Starting pipeline '{self.name}' with {len(self.steps)} steps")
        
        self.start_time = datetime.utcnow()
        self.input_shape = dataframe.shape
        self.executed = True
        
        # Start with input dataframe
        df_current = dataframe.copy()
        
        try:
            # Execute each step
            for i, step in enumerate(self.steps, 1):
                logger.info(f"Step {i}/{len(self.steps)}: {step.name}")
                
                try:
                    df_current, step_report = step.execute(df_current)
                except PipelineError as e:
                    if stop_on_error:
                        raise
                    else:
                        logger.warning(f"Step failed but continuing: {e}")
                        continue
            
            # Pipeline completed successfully
            self.success = True
            self.output_shape = df_current.shape
            self.end_time = datetime.utcnow()
            self.total_duration = (self.end_time - self.start_time).total_seconds()
            
            logger.info(
                f"Pipeline '{self.name}' completed successfully in {self.total_duration:.2f}s. "
                f"Shape: {self.input_shape} → {self.output_shape}"
            )
            
            return df_current
        
        except Exception as e:
            self.success = False
            self.end_time = datetime.utcnow()
            self.total_duration = (self.end_time - self.start_time).total_seconds()
            
            logger.error(f"Pipeline '{self.name}' failed: {e}")
            raise PipelineError(f"Pipeline execution failed: {str(e)}")
    
    def get_report(self) -> Dict[str, Any]:
        """
        Get comprehensive report of all transformations applied.
        
        Returns:
            Dictionary with pipeline execution details
        """
        report = {
            'pipeline_name': self.name,
            'executed': self.executed,
            'success': self.success,
            'total_steps': len(self.steps),
            'successful_steps': sum(1 for step in self.steps if step.success),
            'failed_steps': sum(1 for step in self.steps if step.executed and not step.success),
            'input_shape': self.input_shape,
            'output_shape': self.output_shape,
            'total_duration': self.total_duration,
            'steps': [step.to_dict() for step in self.steps]
        }
        
        if self.start_time:
            report['start_time'] = self.start_time.isoformat()
        
        if self.end_time:
            report['end_time'] = self.end_time.isoformat()
        
        # Calculate shape changes
        if self.input_shape and self.output_shape:
            report['rows_changed'] = self.output_shape[0] - self.input_shape[0]
            report['columns_changed'] = self.output_shape[1] - self.input_shape[1]
        
        return report
    
    def clear(self) -> 'TransformationPipeline':
        """
        Clear all steps from the pipeline.
        
        Returns:
            Self for method chaining
        """
        self.steps = []
        self.executed = False
        self.success = False
        self.input_shape = None
        self.output_shape = None
        logger.debug(f"Cleared all steps from pipeline '{self.name}'")
        return self
    
    def validate(self) -> Dict[str, Any]:
        """
        Validate pipeline configuration.
        
        Returns:
            Validation results
        """
        issues = []
        
        if not self.steps:
            issues.append("No transformation steps defined")
        
        # Check for duplicate step names
        step_names = [step.name for step in self.steps]
        duplicates = [name for name in step_names if step_names.count(name) > 1]
        if duplicates:
            issues.append(f"Duplicate step names: {set(duplicates)}")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'step_count': len(self.steps)
        }


# Built-in pipeline factories

def standard_cleaning_pipeline() -> TransformationPipeline:
    """
    Create a standard data cleaning pipeline.
    
    Steps:
    1. Remove duplicate rows
    2. Trim whitespace from strings
    3. Handle missing values (drop rows with all missing)
    
    Returns:
        Configured TransformationPipeline
    """
    pipeline = TransformationPipeline(name="Standard Cleaning Pipeline")
    
    pipeline.add_step(
        remove_duplicates,
        name="remove_duplicates",
        description="Remove duplicate rows from dataset"
    )
    
    pipeline.add_step(
        trim_whitespace,
        name="trim_whitespace",
        description="Trim leading/trailing whitespace from string columns"
    )
    
    pipeline.add_step(
        handle_missing_values,
        name="handle_missing_values",
        description="Drop rows where all values are missing",
        strategy="drop_all"
    )
    
    logger.info("Created standard cleaning pipeline with 3 steps")
    return pipeline


def numeric_preprocessing_pipeline(
    columns: List[str],
    remove_outliers_method: str = "iqr",
    scaling_method: str = "minmax"
) -> TransformationPipeline:
    """
    Create a numeric data preprocessing pipeline.
    
    Steps:
    1. Clean numeric data (remove currency symbols, commas)
    2. Remove outliers (IQR method by default)
    3. Scale numeric values (min-max by default)
    
    Args:
        columns: List of numeric columns to process
        remove_outliers_method: Method for outlier removal ('iqr' or 'zscore')
        scaling_method: Method for scaling ('minmax', 'standard', etc.)
    
    Returns:
        Configured TransformationPipeline
    """
    pipeline = TransformationPipeline(name="Numeric Preprocessing Pipeline")
    
    # Clean numeric data
    pipeline.add_step(
        clean_numeric,
        name="clean_numeric",
        description=f"Clean numeric columns: {', '.join(columns)}",
        columns=columns
    )
    
    # Remove outliers for each column
    for column in columns:
        pipeline.add_step(
            remove_outliers,
            name=f"remove_outliers_{column}",
            description=f"Remove outliers from {column} using {remove_outliers_method}",
            column=column,
            method=remove_outliers_method
        )
    
    # Scale numeric columns
    pipeline.add_step(
        scale_numeric,
        name="scale_numeric",
        description=f"Scale columns using {scaling_method} method",
        columns=columns,
        method=scaling_method
    )
    
    logger.info(f"Created numeric preprocessing pipeline for {len(columns)} columns")
    return pipeline


def text_preprocessing_pipeline(
    columns: List[str],
    lowercase: bool = True,
    trim_whitespace: bool = True
) -> TransformationPipeline:
    """
    Create a text data preprocessing pipeline.
    
    Steps:
    1. Trim whitespace (optional)
    2. Convert to lowercase (optional)
    
    Args:
        columns: List of text columns to process
        lowercase: Whether to convert text to lowercase
        trim_whitespace: Whether to trim whitespace
    
    Returns:
        Configured TransformationPipeline
    """
    pipeline = TransformationPipeline(name="Text Preprocessing Pipeline")
    
    if trim_whitespace:
        pipeline.add_step(
            trim_whitespace,
            name="trim_whitespace",
            description="Trim whitespace from text columns",
            columns=columns
        )
    
    if lowercase:
        pipeline.add_step(
            standardize_case,
            name="lowercase_text",
            description=f"Convert to lowercase: {', '.join(columns)}",
            columns=columns,
            case="lower"
        )
    
    logger.info(f"Created text preprocessing pipeline for {len(columns)} columns")
    return pipeline


def full_preprocessing_pipeline(
    numeric_columns: Optional[List[str]] = None,
    text_columns: Optional[List[str]] = None,
    categorical_columns: Optional[List[str]] = None,
    normalize_column_names: bool = True
) -> TransformationPipeline:
    """
    Create a comprehensive preprocessing pipeline.
    
    Combines cleaning, numeric processing, text processing, and encoding.
    
    Args:
        numeric_columns: List of numeric columns to scale
        text_columns: List of text columns to clean
        categorical_columns: List of categorical columns to encode
        normalize_column_names: Whether to normalize column names
    
    Returns:
        Configured TransformationPipeline
    """
    pipeline = TransformationPipeline(name="Full Preprocessing Pipeline")
    
    # Step 1: Standard cleaning
    pipeline.add_step(
        remove_duplicates,
        name="remove_duplicates",
        description="Remove duplicate rows"
    )
    
    # Step 2: Normalize column names
    if normalize_column_names:
        pipeline.add_step(
            normalize_column_names,
            name="normalize_columns",
            description="Normalize column names to snake_case",
            case="snake"
        )
    
    # Step 3: Trim whitespace
    pipeline.add_step(
        trim_whitespace,
        name="trim_whitespace",
        description="Trim whitespace from all string columns"
    )
    
    # Step 4: Clean numeric columns
    if numeric_columns:
        pipeline.add_step(
            clean_numeric,
            name="clean_numeric",
            description=f"Clean numeric columns: {', '.join(numeric_columns)}",
            columns=numeric_columns
        )
    
    # Step 5: Standardize text columns to lowercase
    if text_columns:
        pipeline.add_step(
            standardize_case,
            name="lowercase_text",
            description=f"Convert text to lowercase: {', '.join(text_columns)}",
            columns=text_columns,
            case="lower"
        )
    
    # Step 6: Encode categorical columns
    if categorical_columns:
        pipeline.add_step(
            encode_categorical,
            name="encode_categorical",
            description=f"Encode categorical columns: {', '.join(categorical_columns)}",
            columns=categorical_columns,
            method="label"
        )
    
    # Step 7: Handle missing values
    pipeline.add_step(
        handle_missing_values,
        name="handle_missing",
        description="Drop rows with all missing values",
        strategy="drop_all"
    )
    
    logger.info(f"Created full preprocessing pipeline with {len(pipeline.steps)} steps")
    return pipeline


def create_custom_pipeline(
    name: str,
    steps: List[Dict[str, Any]]
) -> TransformationPipeline:
    """
    Create a custom pipeline from a list of step definitions.
    
    Args:
        name: Name of the pipeline
        steps: List of step definitions:
            [
                {
                    'function': function_reference,
                    'name': 'step_name',
                    'description': 'step description',
                    'params': {'param1': value1, ...}
                },
                ...
            ]
    
    Returns:
        Configured TransformationPipeline
    """
    pipeline = TransformationPipeline(name=name)
    
    for step_config in steps:
        func = step_config.get('function')
        step_name = step_config.get('name', func.__name__)
        description = step_config.get('description')
        params = step_config.get('params', {})
        
        pipeline.add_step(
            func,
            name=step_name,
            description=description,
            **params
        )
    
    logger.info(f"Created custom pipeline '{name}' with {len(steps)} steps")
    return pipeline


# Export main components
__all__ = [
    "TransformationPipeline",
    "TransformationStep",
    "PipelineError",
    "standard_cleaning_pipeline",
    "numeric_preprocessing_pipeline",
    "text_preprocessing_pipeline",
    "full_preprocessing_pipeline",
    "create_custom_pipeline"
]
