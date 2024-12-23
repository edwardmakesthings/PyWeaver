"""Common utilities and base classes.

Provides shared functionality and type definitions used across the project.

Path: pyweaver/common/__init__.py
"""

from .type_definitions import (
    GeneratorError,
    GeneratorMode,
    GeneratorOptions,
    GeneratorResult,
    ProcessingError,
    ValidationError,
    ProcessingContext,
    ValidationResult
)

from .base_processor import BaseProcessor

__all__ = [
    "BaseProcessor",
    "GeneratorError",
    "GeneratorMode",
    "GeneratorOptions",
    "GeneratorResult",
    "ProcessingContext",
    "ProcessingError",
    "ValidationError",
    "ValidationResult"
]