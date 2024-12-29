"""Base processor implementation for file processing operations.

This module provides the foundation for all file processors in the system. It implements
a robust processing framework with state management, error handling, and progress
tracking. The BaseProcessor class serves as an abstract base that specific processors
extend to implement their unique processing logic while inheriting common functionality.

The module implements:
- Lifecycle management for processing operations
- Comprehensive error handling and recovery
- Progress tracking and reporting
- Resource management and cleanup
- Configurable processing behavior

Path: pyweaver/common/base.py
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager
import time

from pyweaver.config.path import PathConfig
from pyweaver.common.tracking import FileTracker, TrackerType, TrackerStats
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, StateError, ValidationError
)

logger = logging.getLogger(__name__)

class ProcessorState(Enum):
    """States a processor can be in during its lifecycle.

    This enum defines the various operational states of a processor,
    helping manage its lifecycle and ensure operations occur in the
    correct order.
    """
    INITIALIZED = "initialized"  # Just created
    CONFIGURING = "configuring"  # Setting up configuration
    READY = "ready"         # Ready to process
    PROCESSING = "processing"   # Actively processing
    PAUSED = "paused"       # Temporarily suspended
    COMPLETED = "completed"    # Successfully finished
    ERROR = "error"         # Error state
    CLEANUP = "cleanup"      # Performing cleanup

@dataclass
class ProcessorProgress:
    """Detailed progress information for processing operations.

    This class tracks various metrics about the processing operation,
    providing insight into its progress and performance.

    Attributes:
        total_items: Total number of items to process
        processed_items: Number of items processed
        ignored_items: Number of items ignored
        error_items: Number of items with errors
        start_time: When processing started
        end_time: When processing completed
        current_item: Currently processing item
    """
    total_items: int = 0
    processed_items: int = 0
    ignored_items: int = 0
    error_items: int = 0
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_item: Optional[Path] = None

    @property
    def completion_percentage(self) -> float:
        """Calculate percentage of items processed."""
        if self.total_items == 0:
            return 0.0
        return (self.processed_items / self.total_items) * 100

    @property
    def is_complete(self) -> bool:
        """Check if processing is complete."""
        return (self.processed_items + self.ignored_items + self.error_items) == self.total_items
@dataclass
class ProcessorResult:
    """Results from a processing operation.

    This class provides comprehensive information about the outcome
    of a processing operation, including any errors or warnings.

    Attributes:
        success: Whether processing completed successfully
        message: Human-readable status message
        files_processed: Number of files processed
        errors: List of error messages
        warnings: List of warning messages
        stats: Detailed processing statistics
    """
    success: bool = True
    message: str = ""
    files_processed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: Optional[TrackerStats] = None

class BaseProcessor(ABC):
    """Abstract base class for file processors.

    This class provides the foundation for all file processors, implementing
    common functionality for configuration, tracking, error handling, and
    lifecycle management. Specific processors inherit from this class and
    implement their unique processing logic.

    The class implements a robust processing framework with:
    - State management for proper operation ordering
    - Error handling with recovery options
    - Progress tracking and reporting
    - Resource management and cleanup
    - Configurable processing behavior

    Attributes:
        config: Path-specific configuration settings
        tracker: File/directory tracking
        state: Current processor state
        progress: Processing progress information
        _errors: List of error messages
        _warnings: List of warning messages

    Example:
        ```python
        class CustomProcessor(BaseProcessor):
            def _process_item(self, path: Path) -> None:
                with self._processing_context(path):
                    # Implementation-specific processing
                    with path.open() as f:
                        content = self._process_content(f.read())
                        self._write_output(content)
        ```
    """

    def __init__(
        self,
        config: PathConfig,
        tracker_type: TrackerType = TrackerType.FILES,
        max_retries: int = 3
    ):
        """Initialize processor with configuration.

        Args:
            config: Configuration settings
            tracker_type: Type of items to track
            max_retries: Maximum processing attempts per item

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            self.config = config
            self.tracker = FileTracker(tracker_type, max_retries)
            self.state = ProcessorState.INITIALIZED
            self.progress = ProcessorProgress()

            self._errors: List[str] = []
            self._warnings: List[str] = []

            # Validate configuration
            self._validate_configuration()

            self.state = ProcessorState.READY
            logger.info(
                "Initialized %s with tracker_type=%s, max_retries=%d",
                self.__class__.__name__, tracker_type.value, max_retries
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_processor",
                error_code=ErrorCode.PROCESS_INIT,
                details={
                    "processor_type": self.__class__.__name__,
                    "tracker_type": tracker_type.value
                }
            )
            raise ProcessingError(
                "Failed to initialize processor",
                context=context,
                original_error=e
            ) from e

    def process(self) -> ProcessorResult:
        """Process all pending items with error handling and progress tracking.

        This method implements the main processing loop with proper state
        management, error handling, and progress tracking.

        Returns:
            ProcessorResult with success status and any errors/warnings

        Raises:
            ProcessingError: If a critical processing error occurs
            StateError: If processor is in invalid state
        """
        try:
            self._ensure_state(ProcessorState.READY)
            self.state = ProcessorState.PROCESSING
            self.progress.start_time = time.time()

            stats = self.tracker.get_stats()
            self.progress.total_items = stats.total

            logger.info(
                "Starting processing of %d items",
                self.progress.total_items
            )

            while self.tracker.has_pending():
                if self.state == ProcessorState.PAUSED:
                    logger.info("Processing paused")
                    continue

                if item := self.tracker.next_pending():
                    try:
                        if self._should_process(item):
                            with self._processing_context(item):
                                self._process_item(item)
                                self.tracker.mark_processed(item)
                                self.progress.processed_items += 1
                        else:
                            self.tracker.mark_ignored(item)
                            self.progress.ignored_items += 1

                    except Exception as e:
                        self._handle_item_error(item, e)
                        self.progress.error_items += 1

            self.progress.end_time = time.time()
            self.state = ProcessorState.COMPLETED

            return self._get_result()

        except Exception as e:
            self.state = ProcessorState.ERROR
            context = ErrorContext(
                operation="process",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"state": self.state.value}
            )
            raise ProcessingError(
                "Processing failed",
                context=context,
                original_error=e
            ) from e
        finally:
            self._cleanup()

    @abstractmethod
    def _process_item(self, path: Path) -> None:
        """Process a single item. Must be implemented by subclasses.

        This method should implement the specific processing logic for
        individual items. It can assume proper state management and error
        handling are handled by the base class.

        Args:
            path: Path to item to process

        Raises:
            NotImplementedError: If subclass doesn't implement this method
            ProcessingError: If processing fails
        """
        raise NotImplementedError

    def _should_process(self, path: Path) -> bool:
        """Check if an item should be processed based on configuration.

        This method implements the logic for determining whether an item
        should be processed or ignored based on configuration settings
        and item characteristics.

        Args:
            path: Path to check

        Returns:
            True if item should be processed
        """
        if not path:
            return False

        settings = self.config.get_settings_for_path(path)

        # Check ignore patterns
        for pattern in settings.ignore_patterns:
            if path.match(pattern):
                self._add_warning(
                    f"Ignoring {path} (matches pattern {pattern})"
                )
                return False

        # Check include patterns if specified
        if settings.include_patterns:
            for pattern in settings.include_patterns:
                if path.match(pattern):
                    return True
            return False

        return True

    def pause(self) -> None:
        """Pause processing temporarily.

        This method allows for graceful suspension of processing,
        ensuring the current item completes before pausing.

        Raises:
            StateError: If processor is not in PROCESSING state
        """
        self._ensure_state(ProcessorState.PROCESSING)
        self.state = ProcessorState.PAUSED
        logger.info("Processing paused")

    def resume(self) -> None:
        """Resume paused processing.

        This method resumes processing from where it was paused.

        Raises:
            StateError: If processor is not in PAUSED state
        """
        self._ensure_state(ProcessorState.PAUSED)
        self.state = ProcessorState.PROCESSING
        logger.info("Processing resumed")

    @contextmanager
    def _processing_context(self, path: Path):
        """Context manager for processing individual items.

        This method provides proper setup and cleanup around
        individual item processing, ensuring resources are properly
        managed even if errors occur.

        Args:
            path: Path being processed
        """
        self.progress.current_item = path
        logger.debug("Processing item: %s", path)
        try:
            yield
        finally:
            self.progress.current_item = None

    def _handle_item_error(self, path: Path, error: Exception) -> None:
        """Handle errors during item processing.

        This method provides standardized error handling for item
        processing failures, including proper error wrapping and logging.

        Args:
            path: Path that caused error
            error: Exception that occurred
        """
        if not isinstance(error, ProcessingError):
            context = ErrorContext(
                operation="process_item",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=path
            )
            error = ProcessingError(
                str(error),
                context=context,
                original_error=error
            )

        self._errors.append(str(error))
        self.tracker.mark_error(path, error)
        logger.error(
            "Error processing %s: %s",
            path, error,
            exc_info=True
        )

    def _validate_configuration(self) -> None:
        """Validate processor configuration.

        This method ensures the processor's configuration is valid
        before processing begins.

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            # Base validation - subclasses can extend
            if not isinstance(self.config, PathConfig):
                raise ValidationError(
                    "Invalid configuration type",
                    details={"type": type(self.config)}
                )
        except Exception as e:
            context = ErrorContext(
                operation="validate_config",
                error_code=ErrorCode.CONFIG_VALIDATION,
                details={"config_type": type(self.config)}
            )
            raise ValidationError(
                "Configuration validation failed",
                context=context,
                original_error=e
            ) from e

    def _ensure_state(self, expected_state: ProcessorState) -> None:
        """Ensure processor is in expected state.

        Args:
            expected_state: State processor should be in

        Raises:
            StateError: If processor is not in expected state
        """
        if self.state != expected_state:
            raise StateError(
                "Invalid processor state for operation",
                current_state=self.state.value,
                expected_state=expected_state.value
            )

    def _cleanup(self) -> None:
        """Clean up resources used during processing.

        This method ensures all resources are properly released
        after processing completes or fails.
        """
        try:
            self.state = ProcessorState.CLEANUP
            self.tracker.cleanup()
            logger.debug("Processor cleanup completed")
        except Exception as e:
            logger.error(
                "Error during cleanup: %s",
                e,
                exc_info=True
            )

    def _get_result(self) -> ProcessorResult:
        """Generate processing result with current status.

        Returns:
            ProcessorResult with success status and messages
        """
        return ProcessorResult(
            success=len(self._errors) == 0,
            message=self._get_status_message(),
            files_processed=self.progress.processed_items,
            errors=self._errors.copy(),
            warnings=self._warnings.copy(),
            stats=self.tracker.get_stats()
        )

    def _get_status_message(self) -> str:
        """Generate human-readable status message.

        Returns:
            Status message describing current state
        """
        if self._errors:
            return f"Processing completed with {len(self._errors)} errors"
        elif self._warnings:
            return f"Processing completed with {len(self._warnings)} warnings"
        return "Processing completed successfully"

    def _add_warning(self, warning: str) -> None:
        """Record a warning message and log it.

        Args:
            warning: Warning message to record
        """
        self._warnings.append(warning)
        logger.warning(warning)

    def __repr__(self) -> str:
        """Get string representation of processor."""
        return (
            f"{self.__class__.__name__}("
            f"state={self.state.value}, "
            f"processed={self.progress.processed_items}, "
            f"errors={len(self._errors)})"
        )
