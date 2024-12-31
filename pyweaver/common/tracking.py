"""File and directory tracking for processing operations.

This module provides a robust system for tracking the status of files and directories
during processing operations. It maintains thread-safe sets of pending, processed,
and ignored items while supporting different tracking modes and providing detailed
state management.

The module implements:
- Thread-safe tracking collections
- Configurable tracking modes
- Detailed state reporting
- Memory-efficient item handling
- Comprehensive error tracking

Path: pyweaver/common/tracking.py
"""
import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, List, Tuple, NamedTuple
from threading import Lock
from dataclasses import dataclass, field
import time

from pyweaver.utils.repr import comprehensive_repr
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, StateError
)

logger = logging.getLogger(__name__)

class TrackerType(Enum):
    """Types of items that can be tracked.

    This enum defines the different types of filesystem items that can be tracked,
    allowing for focused tracking of specific item types.
    """
    FILES = "files"
    DIRECTORIES = "directories"
    BOTH = "both"

class TrackerState(Enum):
    """Possible states of the tracker.

    This enum represents the various operational states of the tracker,
    helping manage the tracker's lifecycle.
    """
    INITIALIZED = "initialized"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

class ItemStatus(Enum):
    """Status of tracked items.

    This enum represents the various states an item can be in during processing,
    providing clear status tracking.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    IGNORED = "ignored"
    ERROR = "error"

@dataclass
class TrackedItem:
    """Information about a tracked item.

    This class maintains detailed information about each tracked item,
    including its status and any associated errors.

    Attributes:
        path: Path to the tracked item
        status: Current status of the item
        error: Optional error information if processing failed
        attempts: Number of processing attempts
        timestamp: When the item was last updated
    """
    path: Path
    status: ItemStatus = ItemStatus.PENDING
    error: Optional[ProcessingError] = None
    attempts: int = 0
    timestamp: float = field(default_factory=time.time)

class TrackerStats(NamedTuple):
    """Statistical information about tracked items.

    This class provides a snapshot of the tracker's current state
    for monitoring and reporting purposes.
    """
    pending: int
    processing: int
    processed: int
    ignored: int
    errors: int
    total: int

class FileTracker:
    """Tracks processing status of files and directories.

    This class provides thread-safe tracking of file and directory processing,
    with support for different tracking modes, state management, and error handling.

    Attributes:
        type: What type of items to track
        state: Current operational state
        max_attempts: Maximum processing attempts per item
        _items: Dictionary of all tracked items
        _lock: Thread synchronization lock

    Example:
        ```python
        tracker = FileTracker(TrackerType.FILES)

        # Add items to track
        tracker.add_pending(path)

        # Process items
        while tracker.has_pending():
            if item := tracker.next_pending():
                try:
                    # Process item...
                    tracker.mark_processed(item)
                except Exception as e:
                    tracker.mark_error(item, e)

        # Get statistics
        stats = tracker.get_stats()
        print(f"Processed {stats.processed} items with {stats.errors} errors")
        ```
    """

    def __init__(
        self,
        type_items: TrackerType = TrackerType.FILES,
        max_attempts: int = 3
    ):
        """Initialize tracker with specified type and settings.

        Args:
            type_items: Type of items to track
            max_attempts: Maximum processing attempts per item

        Raises:
            ValidationError: If invalid parameters are provided
        """
        try:
            self.type = type_items
            self.state = TrackerState.INITIALIZED
            self.max_attempts = max_attempts

            self._items: Dict[Path, TrackedItem] = {}
            self._lock = Lock()

            logger.debug(
                "Initialized FileTracker with type=%s, max_attempts=%d",
                type_items.value, max_attempts
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_tracker",
                error_code=ErrorCode.PROCESS_INIT,
                details={"type": type_items.value, "max_attempts": max_attempts}
            )
            raise ProcessingError(
                "Failed to initialize tracker",
                context=context,
                original_error=e
            ) from e

    def add_pending(self, path: Path) -> None:
        """Add an item to the pending set if it matches tracker type.

        Args:
            path: Path to potentially pending item

        Raises:
            ValidationError: If path is invalid
            StateError: If tracker is in invalid state
        """
        try:
            if self.state not in {TrackerState.INITIALIZED, TrackerState.ACTIVE}:
                raise StateError("Tracker must be initialized or active to add items")

            if not self._validate_item_type(path):
                logger.debug("Skipping item %s: wrong type for tracker", path)
                return

            with self._lock:
                if path not in self._items:
                    self._items[path] = TrackedItem(path)
                    self.state = TrackerState.ACTIVE
                    logger.debug("Added pending item: %s", path)

        except Exception as e:
            context = ErrorContext(
                operation="add_pending",
                error_code=ErrorCode.PROCESS_STATE,
                path=path,
                details={"tracker_type": self.type.value}
            )
            raise ProcessingError(
                f"Failed to add pending item: {path}",
                context=context,
                original_error=e
            ) from e

    def mark_processed(self, path: Path) -> None:
        """Mark an item as processed, updating its status.

        Args:
            path: Path to processed item

        Raises:
            StateError: If item doesn't exist or is in invalid state
        """
        try:
            with self._lock:
                if item := self._items.get(path):
                    if item.status not in {ItemStatus.PENDING, ItemStatus.PROCESSING}:
                        raise StateError(f"Cannot mark item as processed from state: {item.status}")

                    item.status = ItemStatus.PROCESSED
                    item.timestamp = time.time()
                    logger.debug("Marked item as processed: %s", path)
                else:
                    raise StateError(f"Item not found: {path}")

        except Exception as e:
            context = ErrorContext(
                operation="mark_processed",
                error_code=ErrorCode.PROCESS_STATE,
                path=path
            )
            raise ProcessingError(
                f"Failed to mark item as processed: {path}",
                context=context,
                original_error=e
            ) from e

    def mark_error(self, path: Path, error: Exception) -> None:
        """Mark an item as having encountered an error.

        Args:
            path: Path to item with error
            error: Exception that occurred

        Raises:
            StateError: If item doesn't exist
        """
        try:
            with self._lock:
                if item := self._items.get(path):
                    item.status = ItemStatus.ERROR
                    item.error = error if isinstance(error, ProcessingError) else ProcessingError(
                        str(error),
                        operation="process_item",
                        path=path,
                        original_error=error
                    )
                    item.timestamp = time.time()
                    item.attempts += 1

                    # If max attempts not reached, requeue
                    if item.attempts < self.max_attempts:
                        item.status = ItemStatus.PENDING
                        logger.warning(
                            "Item %s failed (attempt %d/%d), requeueing",
                            path, item.attempts, self.max_attempts
                        )
                    else:
                        logger.error(
                            "Item %s failed after %d attempts, marking as error",
                            path, item.attempts
                        )
                else:
                    raise StateError(f"Item not found: {path}")

        except Exception as e:
            context = ErrorContext(
                operation="mark_error",
                error_code=ErrorCode.PROCESS_STATE,
                path=path,
                details={"original_error": str(error)}
            )
            raise ProcessingError(
                f"Failed to mark item error: {path}",
                context=context,
                original_error=e
            ) from e

    def mark_ignored(self, path: Path) -> None:
        """Mark an item as ignored, updating its status.

        Args:
            path: Path to ignored item

        Raises:
            StateError: If item doesn't exist
        """
        try:
            with self._lock:
                if item := self._items.get(path):
                    item.status = ItemStatus.IGNORED
                    item.timestamp = time.time()
                    logger.debug("Marked item as ignored: %s", path)
                else:
                    raise StateError(f"Item not found: {path}")

        except Exception as e:
            context = ErrorContext(
                operation="mark_ignored",
                error_code=ErrorCode.PROCESS_STATE,
                path=path
            )
            raise ProcessingError(
                f"Failed to mark item as ignored: {path}",
                context=context,
                original_error=e
            ) from e

    def has_pending(self) -> bool:
        """Check if there are any pending items.

        Returns:
            True if there are pending items to process
        """
        with self._lock:
            return any(
                item.status == ItemStatus.PENDING
                for item in self._items.values()
            )

    def next_pending(self) -> Optional[Path]:
        """Get next pending item and mark it as processing.

        Returns:
            Next pending item or None if no items pending

        Raises:
            StateError: If tracker is in invalid state
        """
        try:
            with self._lock:
                for item in self._items.values():
                    if item.status == ItemStatus.PENDING:
                        item.status = ItemStatus.PROCESSING
                        item.timestamp = time.time()
                        logger.debug("Retrieved next pending item: %s", item.path)
                        return item.path
                return None

        except Exception as e:
            context = ErrorContext(
                operation="next_pending",
                error_code=ErrorCode.PROCESS_STATE
            )
            raise ProcessingError(
                "Failed to get next pending item",
                context=context,
                original_error=e
            ) from e

    def get_stats(self) -> TrackerStats:
        """Get current tracking statistics.

        Returns:
            TrackerStats with current counts
        """
        with self._lock:
            counts = {status: 0 for status in ItemStatus}
            for item in self._items.values():
                counts[item.status] += 1

            return TrackerStats(
                pending=counts[ItemStatus.PENDING],
                processing=counts[ItemStatus.PROCESSING],
                processed=counts[ItemStatus.PROCESSED],
                ignored=counts[ItemStatus.IGNORED],
                errors=counts[ItemStatus.ERROR],
                total=len(self._items)
            )

    def get_errors(self) -> List[Tuple[Path, ProcessingError]]:
        """Get list of all items that encountered errors.

        Returns:
            List of tuples containing path and error information
        """
        with self._lock:
            return [
                (item.path, item.error)
                for item in self._items.values()
                if item.status == ItemStatus.ERROR and item.error
            ]

    def cleanup(self) -> None:
        """Clear all tracking state and reset tracker.

        This method should be called when tracking is complete to free resources.
        """
        with self._lock:
            self._items.clear()
            self.state = TrackerState.COMPLETED
            logger.debug("Cleaned up tracker state")

    def _validate_item_type(self, path: Path) -> bool:
        """Check if an item matches the tracker type.

        Args:
            path: Path to validate

        Returns:
            True if item matches tracker type
        """
        try:
            if self.type == TrackerType.BOTH:
                return True
            elif self.type == TrackerType.FILES:
                return path.is_file()
            else:  # TrackerType.DIRECTORIES
                return path.is_dir()

        except Exception as e:
            logger.warning(
                "Error validating item type for %s: %s",
                path, e
            )
            return False

    def __repr__(self) -> str:
        """Get string representation of tracker state."""
        return comprehensive_repr(
            self,
            exclude=['_lock'],
            prioritize=['type', 'state'],
            one_per_line=True
        )
