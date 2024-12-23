"""Type definitions and interfaces for the PyWeaver framework.

This module defines the core type system used throughout PyWeaver, including:
- Generator configuration and results
- Error handling types
- Processing context and validation
- Common interfaces and data structures

The types defined here are deliberately isolated to prevent circular dependencies
and provide a single source of truth for shared type definitions.

Example:
    ```python
    from pyweaver.common.type_definitions import GeneratorOptions, GeneratorMode

    options = GeneratorOptions(
        mode=GeneratorMode.PREVIEW,
        exclude_patterns={'*.pyc', '__pycache__'}
    )
    ```

Path: pyweaver/common/type_definitions.py
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

# Base Types
class GeneratorMode(Enum):
    """Operation modes that control generator behavior.

    Attributes:
        PREVIEW: Generate output without writing files, useful for testing
        OUTPUT_ONLY: Generate only the output files, skip source modifications
        WRITE: Full generation mode that writes all output and modifies sources
    """
    PREVIEW = "preview"
    OUTPUT_ONLY = "output_only"
    WRITE = "write"

@dataclass
class GeneratorOptions:
    """Configuration options for generator behavior.

    Attributes:
        mode: The GeneratorMode controlling output behavior
        output_path: Target directory for generated files
        dry_run: If True, simulate operations without making changes
        exclude_patterns: Set of glob patterns for files to ignore
        include_patterns: Set of glob patterns for files to process

    Example:
        ```python
        options = GeneratorOptions(
            mode=GeneratorMode.WRITE,
            output_path=Path("./output"),
            exclude_patterns={"*.tmp", "*.bak"}
        )
        ```
    """
    mode: GeneratorMode = GeneratorMode.PREVIEW
    output_path: Optional[Path] = None
    dry_run: bool = True
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)

@dataclass
class GeneratorResult:
    """Results and statistics from a generator operation.

    Tracks success/failure status, processed file counts, and any errors or
    warnings that occurred during generation.

    Attributes:
        success: True if generation completed without errors
        message: Summary message describing the result
        files_processed: Number of files processed
        files_written: Number of files written
        errors: List of error messages encountered
        warnings: List of warning messages encountered
    """
    success: bool
    message: str
    files_processed: int = 0
    files_written: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.errors = self.errors or []
        self.warnings = self.warnings or []

# Error Types
class GeneratorError(Exception):
    """Base exception class for generator errors.

    Attributes:
        message: Human-readable error description
        code: Machine-readable error code, defaults to "GEN_ERR"

    Example:
        ```python
        raise GeneratorError("Failed to process file", code="FILE_ERR")
        ```
    """
    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.code = code or "GEN_ERR"

class ValidationError(GeneratorError):
    """Exception raised when validation fails in the PyWeaver framework.

    This error indicates issues found during the validation phase before
    actual processing begins, such as invalid configurations, missing
    required fields, or unsupported options.

    Args:
        message (str): Human-readable description of the validation error

    Attributes:
        message (str): The error message
        code (str): Error code, always set to "VAL_ERR"

    Example:
        ```python
        if not config.is_valid():
            raise ValidationError("Missing required field 'output_path'")
        ```
    """
    def __init__(self, message: str):
        super().__init__(message, "VAL_ERR")

class ProcessingError(GeneratorError):
    """Exception raised when errors occur during file processing.

    This error indicates issues that occur during the actual processing
    phase, such as file I/O errors, parsing failures, or generation
    failures.

    Args:
        message (str): Human-readable description of the processing error

    Attributes:
        message (str): The error message
        code (str): Error code, always set to "PROC_ERR"

    Example:
        ```python
        try:
            process_file(path)
        except IOError as e:
            raise ProcessingError(f"Failed to process {path}: {str(e)}")
        ```
    """
    def __init__(self, message: str):
        super().__init__(message, "PROC_ERR")

# Shared Interfaces
@dataclass
class ProcessingContext:
    """Context information for file processing operations.

    Maintains state and configuration during file processing including paths,
    current file being processed, and pattern matching rules.

    Attributes:
        root_dir: Base directory for processing operations
        current_file: File currently being processed, if any
        exclude_patterns: Glob patterns for files to exclude
        include_patterns: Glob patterns for files to include
    """
    root_dir: Path
    current_file: Optional[Path] = None
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)

@dataclass
class ValidationResult:
    """Results from validation operations.

    Tracks validation status and any validation errors or warnings.

    Attributes:
        is_valid: True if validation passed without errors
        errors: List of validation error messages
        warnings: List of validation warning messages

    Example:
        ```python
        result = ValidationResult(
            is_valid=True,
            warnings=["Optional field missing"]
        )
        ```
    """
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.errors = self.errors or []
        self.warnings = self.warnings or []