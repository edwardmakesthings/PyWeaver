"""File processing base implementation for the PyWeaver framework.

This module provides the core infrastructure for processing files with consistent error
handling, validation, and result tracking. It serves as the foundation for all file
processing operations in PyWeaver.

Classes:
    BaseProcessor: Abstract base class defining the processor interface and common functionality.

Example:
    ```python
    processor = CustomProcessor(options)
    validation = processor.validate()
    if validation.is_valid:
        result = processor.process()
        if result.success:
            print(f"Processed {result.files_processed} files")
    ```

Version: 1.0.0

Path: pyweaver/common/base_processor.py
"""
import logging
from pathlib import Path
from typing import Dict, Optional, List

from pyweaver.common.type_definitions import (
    GeneratorOptions,
    GeneratorResult,
    ProcessingContext,
    ValidationResult
)

logger = logging.getLogger(__name__)

class BaseProcessor:
    """Abstract base class providing core file processing functionality.

    Handles common processor operations including error tracking, validation,
    file management and result aggregation. Subclasses must implement specific
    processing logic.

    Attributes:
        options (GeneratorOptions): Configuration options for the processor.
        _processed_files (Dict[Path, str]): Map of processed files to their status.
        _errors (List[str]): Collection of error messages during processing.
        _warnings (List[str]): Collection of warning messages during processing.
        _context (ProcessingContext): Processing context with paths and patterns.

    Example:
        ```python
        class ImageProcessor(BaseProcessor):
            def process_file(self, path: Path) -> None:
                # Process image file
                self._processed_files[path] = "success"
        ```
    """

    def __init__(self, options: GeneratorOptions):
        self.options = options
        self._processed_files: Dict[Path, str] = {}
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._context = ProcessingContext(
            root_dir=self._get_root_dir(),
            exclude_patterns=options.exclude_patterns,
            include_patterns=options.include_patterns
        )

    def _get_root_dir(self) -> Path:
        """Determine the root directory for processing operations.

        Returns:
            Path: The root directory path, either from output_path parent or current working directory.
        """
        if self.options.output_path:
            return self.options.output_path.parent
        return Path.cwd()

    def get_result(self) -> GeneratorResult:
        """Collate and return the processing results.

        Returns:
            GeneratorResult: Processing outcome including success status, message,
                file counts, and any errors or warnings.
        """
        return GeneratorResult(
            success=len(self._errors) == 0,
            message=self._get_result_message(),
            files_processed=len(self._processed_files),
            files_written=len([f for f in self._processed_files if f.exists()]),
            errors=self._errors.copy(),
            warnings=self._warnings.copy()
        )

    def _get_result_message(self) -> str:
        """Generate a human-readable processing result message.

        Returns:
            str: Status message describing processing outcome with error/warning counts.
        """
        if self._errors:
            return f"Processing completed with {len(self._errors)} errors"
        elif self._warnings:
            return f"Processing completed with {len(self._warnings)} warnings"
        return "Processing completed successfully"

    def add_error(self, error: str):
        """Record an error that occurred during processing.

        Args:
            error (str): Error message to record.

        Side Effects:
            - Adds error to internal error list
            - Logs error message using logger
        """
        self._errors.append(error)
        logger.error(error)

    def add_warning(self, warning: str):
        """Record a warning that occurred during processing.

        Args:
            warning (str): Warning message to record.

        Side Effects:
            - Adds warning to internal warning list
            - Logs warning message using logger
        """
        self._warnings.append(warning)
        logger.warning(warning)

    def validate(self) -> ValidationResult:
        """Validate the processor configuration before processing.

        Checks:
            - Root directory existence
            - Other implementation-specific validations in subclasses

        Returns:
            ValidationResult: Validation outcome with errors if any validation failed.
        """
        result = ValidationResult(is_valid=True)

        if not self._context.root_dir.exists():
            result.is_valid = False
            result.errors.append(
                f"Root directory does not exist: {self._context.root_dir}"
            )

        return result