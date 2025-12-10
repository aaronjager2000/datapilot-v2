"""
CSV and Excel file parser service.

Handles parsing of CSV and Excel files with automatic encoding detection,
delimiter inference, and robust error handling.
"""

import logging
import csv
from pathlib import Path
from typing import Optional, Union, List
import chardet
import pandas as pd
from io import StringIO

logger = logging.getLogger(__name__)


class FileParserError(Exception):
    """Base exception for file parsing errors."""
    pass


class EncodingDetectionError(FileParserError):
    """Raised when file encoding cannot be detected."""
    pass


class DelimiterDetectionError(FileParserError):
    """Raised when CSV delimiter cannot be inferred."""
    pass


class CorruptedFileError(FileParserError):
    """Raised when file is corrupted or unreadable."""
    pass


def infer_delimiter(file_path: str, sample_size: int = 8192) -> str:
    """
    Infer the delimiter used in a CSV file.

    Args:
        file_path: Path to the CSV file
        sample_size: Number of bytes to read for inference

    Returns:
        The detected delimiter character

    Raises:
        DelimiterDetectionError: If delimiter cannot be inferred
    """
    try:
        # First detect encoding
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'

        # Read sample with detected encoding
        with open(file_path, 'r', encoding=encoding, errors='replace') as f:
            sample = f.read(sample_size)

        # Use csv.Sniffer to detect delimiter
        sniffer = csv.Sniffer()
        try:
            dialect = sniffer.sniff(sample, delimiters=',;\t|')
            delimiter = dialect.delimiter
            logger.info(f"Detected delimiter: {repr(delimiter)}")
            return delimiter
        except csv.Error:
            # If Sniffer fails, count occurrences of common delimiters
            delimiters = {',': sample.count(','),
                         ';': sample.count(';'),
                         '\t': sample.count('\t'),
                         '|': sample.count('|')}

            # Choose the most common delimiter
            delimiter = max(delimiters, key=delimiters.get)
            if delimiters[delimiter] == 0:
                raise DelimiterDetectionError("No common delimiter found in file")

            logger.info(f"Inferred delimiter by frequency: {repr(delimiter)}")
            return delimiter

    except Exception as e:
        logger.error(f"Failed to infer delimiter: {str(e)}")
        raise DelimiterDetectionError(f"Could not infer delimiter: {str(e)}")


def detect_encoding(file_path: str, sample_size: int = 100000) -> str:
    """
    Detect the encoding of a file.

    Args:
        file_path: Path to the file
        sample_size: Number of bytes to read for detection

    Returns:
        The detected encoding name

    Raises:
        EncodingDetectionError: If encoding cannot be detected
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(sample_size)
            result = chardet.detect(raw_data)

            encoding = result['encoding']
            confidence = result['confidence']

            if encoding is None:
                raise EncodingDetectionError("Could not detect file encoding")

            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")

            # Normalize encoding names
            encoding = encoding.lower()
            if 'utf' in encoding and '8' in encoding:
                return 'utf-8'
            elif 'latin' in encoding or 'iso-8859' in encoding:
                return 'latin-1'
            elif 'windows' in encoding or 'cp1252' in encoding:
                return 'cp1252'

            return encoding

    except Exception as e:
        logger.error(f"Failed to detect encoding: {str(e)}")
        raise EncodingDetectionError(f"Could not detect encoding: {str(e)}")


def parse_csv(
    file_path: str,
    delimiter: Optional[str] = None,
    encoding: Optional[str] = None,
    parse_dates: bool = True,
    **kwargs
) -> pd.DataFrame:
    """
    Parse a CSV file into a pandas DataFrame.

    Automatically detects encoding and delimiter if not provided.

    Args:
        file_path: Path to the CSV file
        delimiter: CSV delimiter (auto-detected if None)
        encoding: File encoding (auto-detected if None)
        parse_dates: Whether to attempt parsing date columns
        **kwargs: Additional arguments passed to pd.read_csv

    Returns:
        Pandas DataFrame containing the CSV data

    Raises:
        FileParserError: If file cannot be parsed
    """
    try:
        # Detect encoding if not provided
        if encoding is None:
            encoding = detect_encoding(file_path)

        # Detect delimiter if not provided
        if delimiter is None:
            delimiter = infer_delimiter(file_path)

        logger.info(f"Parsing CSV: {file_path} (encoding={encoding}, delimiter={repr(delimiter)})")

        # Parse CSV with pandas
        df = pd.read_csv(
            file_path,
            delimiter=delimiter,
            encoding=encoding,
            parse_dates=parse_dates,
            infer_datetime_format=True,
            on_bad_lines='warn',  # Log bad lines but continue
            engine='python',  # More flexible parser
            **kwargs
        )

        logger.info(f"Successfully parsed CSV: {len(df)} rows, {len(df.columns)} columns")
        return df

    except (EncodingDetectionError, DelimiterDetectionError) as e:
        logger.error(f"Detection error: {str(e)}")
        raise FileParserError(f"Failed to detect file properties: {str(e)}")

    except pd.errors.ParserError as e:
        logger.error(f"CSV parsing error: {str(e)}")
        raise FileParserError(f"Failed to parse CSV file: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error parsing CSV: {str(e)}", exc_info=True)
        raise FileParserError(f"Unexpected error parsing CSV: {str(e)}")


def get_sheet_names(file_path: str) -> List[str]:
    """
    Get the names of all sheets in an Excel file.

    Args:
        file_path: Path to the Excel file

    Returns:
        List of sheet names

    Raises:
        FileParserError: If sheet names cannot be read
    """
    try:
        excel_file = pd.ExcelFile(file_path, engine='openpyxl')
        sheet_names = excel_file.sheet_names
        logger.info(f"Found {len(sheet_names)} sheets: {sheet_names}")
        return sheet_names

    except Exception as e:
        logger.error(f"Failed to read sheet names: {str(e)}")
        raise FileParserError(f"Could not read Excel sheets: {str(e)}")


def parse_excel(
    file_path: str,
    sheet_name: Optional[Union[str, int, List[Union[str, int]]]] = None,
    parse_dates: bool = True,
    **kwargs
) -> Union[pd.DataFrame, dict]:
    """
    Parse an Excel file into pandas DataFrame(s).

    Args:
        file_path: Path to the Excel file
        sheet_name: Sheet name(s) to parse. If None, parses first sheet.
                   Can be:
                   - None: first sheet only (returns DataFrame)
                   - str: specific sheet name (returns DataFrame)
                   - int: sheet index (returns DataFrame)
                   - list: multiple sheets (returns dict of DataFrames)
        parse_dates: Whether to attempt parsing date columns
        **kwargs: Additional arguments passed to pd.read_excel

    Returns:
        - Single DataFrame if sheet_name is None, str, or int
        - Dictionary of {sheet_name: DataFrame} if sheet_name is a list

    Raises:
        FileParserError: If file cannot be parsed
    """
    try:
        logger.info(f"Parsing Excel: {file_path} (sheet={sheet_name})")

        # If no sheet specified, use the first sheet
        if sheet_name is None:
            sheet_name = 0

        # Parse Excel file
        result = pd.read_excel(
            file_path,
            sheet_name=sheet_name,
            engine='openpyxl',
            parse_dates=parse_dates,
            **kwargs
        )

        # Log results
        if isinstance(result, dict):
            for name, df in result.items():
                logger.info(f"Sheet '{name}': {len(df)} rows, {len(df.columns)} columns")
        else:
            logger.info(f"Successfully parsed Excel: {len(result)} rows, {len(result.columns)} columns")

        return result

    except FileNotFoundError:
        logger.error(f"Excel file not found: {file_path}")
        raise FileParserError(f"Excel file not found: {file_path}")

    except ValueError as e:
        if "Worksheet" in str(e):
            logger.error(f"Sheet not found: {str(e)}")
            raise FileParserError(f"Sheet not found in Excel file: {str(e)}")
        raise FileParserError(f"Invalid Excel file: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to parse Excel file: {str(e)}", exc_info=True)
        raise FileParserError(f"Could not parse Excel file: {str(e)}")


def parse_file(
    file_path: str,
    file_type: Optional[str] = None,
    **kwargs
) -> Union[pd.DataFrame, dict]:
    """
    Parse a data file (CSV or Excel) based on file extension.

    Args:
        file_path: Path to the file
        file_type: File type ('csv', 'xlsx', 'xls'). Auto-detected if None.
        **kwargs: Additional arguments passed to specific parser

    Returns:
        Pandas DataFrame or dict of DataFrames

    Raises:
        FileParserError: If file cannot be parsed or type is unsupported
    """
    path = Path(file_path)

    if not path.exists():
        raise FileParserError(f"File not found: {file_path}")

    # Determine file type
    if file_type is None:
        file_type = path.suffix.lower().lstrip('.')

    logger.info(f"Parsing file: {file_path} (type={file_type})")

    # Route to appropriate parser
    if file_type == 'csv':
        return parse_csv(file_path, **kwargs)
    elif file_type in ['xlsx', 'xls']:
        return parse_excel(file_path, **kwargs)
    else:
        raise FileParserError(f"Unsupported file type: {file_type}")


def validate_dataframe(df: pd.DataFrame, min_rows: int = 1, min_cols: int = 1) -> None:
    """
    Validate that a DataFrame meets minimum requirements.

    Args:
        df: DataFrame to validate
        min_rows: Minimum number of rows required
        min_cols: Minimum number of columns required

    Raises:
        FileParserError: If validation fails
    """
    if df is None or df.empty:
        raise FileParserError("DataFrame is empty")

    if len(df) < min_rows:
        raise FileParserError(f"DataFrame has only {len(df)} rows (minimum: {min_rows})")

    if len(df.columns) < min_cols:
        raise FileParserError(f"DataFrame has only {len(df.columns)} columns (minimum: {min_cols})")

    logger.info(f"DataFrame validation passed: {len(df)} rows, {len(df.columns)} columns")
