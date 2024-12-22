"""Common utilities and base classes for project tools.

Provides shared functionality for file processing, pattern matching,
and error handling used across the project tools.

Path: tools/project_tools/common/__init__.py
"""

from .types import (
    GeneratorError,
    GeneratorMode,
    GeneratorOptions,
    GeneratorResult,
    Pattern,
    ProcessingError,
    ValidationError,
    WriterError
)

from .processor import (
    FileProcessor,
    ProcessingContext,
    ValidationResult
)

__all__ = [
    "FileProcessor",
    "GeneratorError",
    "GeneratorMode",
    "GeneratorOptions",
    "GeneratorResult",
    "Pattern",
    "ProcessingContext",
    "ProcessingError",
    "ValidationError",
    "ValidationResult",
    "WriterError"
]
