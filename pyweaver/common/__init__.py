"""Common utilities and base classes for file processing operations.

This module provides the foundation for file processing operations, including:
- Base processor classes that define common processing patterns
- Comprehensive error handling with proper context and error codes
- Robust file and directory tracking mechanisms
- Progress monitoring and reporting
- Resource management and cleanup

The module implements a layered architecture where:
- Base classes provide core functionality and contracts
- Error handling provides detailed context for debugging
- Tracking system manages file processing state
- Progress system monitors operation status

Example:
    ```python
    from pyweaver.common import BaseProcessor, ProcessorState, FileTracker

    class CustomProcessor(BaseProcessor):
        def _process_item(self, path: Path) -> None:
            with self._processing_context(path):
                # Custom processing logic
                content = self._process_content(path)
                self._write_output(content)

    # Initialize and use processor
    processor = CustomProcessor(config)
    result = processor.process()
    if result.success:
        print(f"Processed {result.files_processed} files")
    ```

Path: pyweaver/common/__init__.py
"""

from .base import (
    ProcessorState,
    ProcessorProgress,
    ProcessorResult,
    BaseProcessor
)
from .errors import (
    ErrorCategory,
    ErrorCode,
    ErrorContext,
    ProcessingError,
    FileError,
    ConfigError,
    StateError,
    ValidationError
)
from .tracking import (
    TrackerType,
    TrackerState,
    ItemStatus,
    TrackedItem,
    TrackerStats,
    FileTracker
)

__all__ = [
    'ProcessorState',
    'ProcessorProgress',
    'ProcessorResult',
    'BaseProcessor',

    'ErrorCategory',
    'ErrorCode',
    'ErrorContext',
    'ProcessingError',
    'FileError',
    'ConfigError',
    'StateError',
    'ValidationError',

    'TrackerType',
    'TrackerState',
    'ItemStatus',
    'TrackedItem',
    'TrackerStats',
    'FileTracker'
]
