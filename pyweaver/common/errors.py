"""Common error types for file processing.

This module provides a comprehensive error handling system for file processing operations,
including standardized error types, detailed error contexts, and hierarchical error
classification. It ensures consistent error handling and reporting across the entire
application.

The module implements:
- Hierarchical error classification
- Detailed error context tracking
- Standard error codes with categories
- Rich error messages with context

Path: pyweaver/common/errors.py
"""
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List

class ErrorCategory(Enum):
    """High-level categorization of errors."""
    FILE = "FILE"        # File system operations
    PATH = "PATH"        # Path operations and validation
    CONFIG = "CFG"       # Configuration handling
    PROCESS = "PROC"     # Processing operations
    VALIDATION = "VAL"   # Data validation
    MEMORY = "MEM"       # Memory operations
    STATE = "STATE"      # State management
    SYSTEM = "SYS"       # System-level operations

class ErrorCode(Enum):
    """Detailed error codes with categories.

    Format: CATEGORY_XXX where:
    - CATEGORY is the error category
    - XXX is a three-digit number
    """
    # File Operations (FILE)
    FILE_GENERAL = "FILE001"           # General file error
    FILE_NOT_FOUND = "FILE002"         # File not found
    FILE_READ = "FILE003"              # Read error
    FILE_WRITE = "FILE004"             # Write error
    FILE_PERMISSION = "FILE005"        # Permission error
    FILE_ENCODING = "FILE006"          # Encoding error
    FILE_LOCK = "FILE007"              # File locking error

    # Path Operations (PATH)
    PATH_GENERAL = "PATH001"           # General path error
    PATH_INVALID = "PATH002"           # Invalid path
    PATH_NOT_FOUND = "PATH003"         # Path not found
    PATH_EXCLUDED = "PATH004"          # Path excluded by pattern
    PATH_ACCESS = "PATH005"            # Path access error

    # Configuration (CFG)
    CONFIG_GENERAL = "CFG001"          # General config error
    CONFIG_PARSE = "CFG002"            # Parse error
    CONFIG_VALIDATION = "CFG003"       # Validation error
    CONFIG_PATH = "CFG004"             # Path configuration error
    CONFIG_TYPE = "CFG005"             # Type configuration error
    CONFIG_MISSING = "CFG006"          # Missing configuration
    CONFIG_INIT = "CFG007"             # Configuration initialization error
    CONFIG_MERGE = "CFG008"            # Configuration merge error

    # Processing (PROC)
    PROCESS_GENERAL = "PROC001"        # General processing error
    PROCESS_INIT = "PROC002"           # Initialization error
    PROCESS_EXECUTION = "PROC003"      # Execution error
    PROCESS_STATE = "PROC004"          # State error
    PROCESS_TIMEOUT = "PROC005"        # Processing timeout
    PROCESS_INTERRUPT = "PROC006"      # Processing interrupted

    # Validation (VAL)
    VALIDATION_GENERAL = "VAL001"      # General validation error
    VALIDATION_TYPE = "VAL002"         # Type validation error
    VALIDATION_FORMAT = "VAL003"       # Format validation error
    VALIDATION_CONSTRAINT = "VAL004"   # Constraint validation error
    VALIDATION_DEPENDENCY = "VAL005"   # Dependency validation error

    # Memory Operations (MEM)
    MEMORY_GENERAL = "MEM001"          # General memory error
    MEMORY_ALLOCATION = "MEM002"       # Memory allocation error
    MEMORY_LIMIT = "MEM003"            # Memory limit exceeded

    # State Management (STATE)
    STATE_GENERAL = "STATE001"         # General state error
    STATE_INVALID = "STATE002"         # Invalid state
    STATE_TRANSITION = "STATE003"      # State transition error

    # System Operations (SYS)
    SYSTEM_GENERAL = "SYS001"          # General system error
    SYSTEM_RESOURCE = "SYS002"         # Resource error
    SYSTEM_ENVIRONMENT = "SYS003"      # Environment error

    @property
    def category(self) -> ErrorCategory:
        """Get the category for this error code."""
        return ErrorCategory(''.join(c for c in self.value if c.isalpha()))

@dataclass
class ErrorContext:
    """Detailed context information for processing errors.

    This class provides rich context about where and why an error occurred,
    including operation details, paths, and additional contextual information.

    Attributes:
        operation: Name of the operation that failed
        error_code: Specific error code
        path: Optional path related to the error
        details: Optional dictionary of additional details
        timestamp: When the error occurred
        stack: List of nested error contexts for tracking error chain
    """
    operation: str
    error_code: ErrorCode
    path: Optional[Path] = None
    details: Dict[str, Any] = field(default_factory=dict)
    stack: List['ErrorContext'] = field(default_factory=list)

    def add_context(self, context: 'ErrorContext') -> None:
        """Add nested error context to the stack."""
        self.stack.append(context)

    def format_details(self) -> str:
        """Format error details for display."""
        parts = []
        if self.path:
            parts.append(f"path: {self.path}")
        if self.operation:
            parts.append(f"operation: {self.operation}")
        if self.details:
            parts.extend(f"{k}: {v}" for k, v in self.details.items())
        return " | ".join(parts)

class ProcessingError(Exception):
    """Base error for all processing operations.

    This is the primary error class for the application, providing detailed
    error information and context tracking.

    Attributes:
        message: Error description
        context: Detailed error context
        original_error: Original exception if this wraps another error
    """
    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        operation: Optional[str] = None,
        path: Optional[Path] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize processing error with context.

        Args:
            message: Error description
            context: Optional error context
            operation: Optional operation name (used if context not provided)
            path: Optional path (used if context not provided)
            original_error: Optional original exception
        """
        super().__init__(message)
        self.message = message
        self.context = context or (
            ErrorContext(
                operation=operation or "unknown_operation",
                error_code=ErrorCode.PROCESS_GENERAL,
                path=path
            ) if operation or path else None
        )
        self.original_error = original_error

    def __str__(self) -> str:
        """Format error message with context."""
        parts = [self.message]
        if self.context:
            details = self.context.format_details()
            if details:
                parts.append(f"({details})")
            if self.context.stack:
                parts.append("Error stack:")
                for ctx in self.context.stack:
                    parts.append(f"  - {ctx.error_code.value}: {ctx.format_details()}")
        return " ".join(parts)

class FileError(ProcessingError):
    """Error specific to file operations.

    Provides additional context specific to file operations while maintaining
    compatibility with the base ProcessingError.

    Attributes:
        path: Path that caused the error
        context: Detailed error context
    """
    def __init__(
        self,
        message: str,
        *,
        path: Path,
        context: Optional[ErrorContext] = None,
        operation: Optional[str] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize file error with required path.

        Args:
            message: Error description
            path: Path that caused the error
            context: Optional error context
            operation: Optional operation name
            original_error: Optional original exception
        """
        # Create context if not provided, ensuring path is included
        if context:
            context.path = path  # Override path in provided context
        else:
            context = ErrorContext(
                operation=operation or "file_operation",
                error_code=ErrorCode.FILE_GENERAL,
                path=path
            )

        super().__init__(
            message,
            context=context,
            original_error=original_error
        )
        self.path = path  # Keep path as direct attribute for compatibility

class ConfigError(ProcessingError):
    """Error specific to configuration operations.

    Handles errors related to configuration loading, validation, and application.

    Attributes:
        context: Detailed error context including configuration details
    """
    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        operation: Optional[str] = None,
        config_details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize configuration error.

        Args:
            message: Error description
            context: Optional error context
            operation: Optional operation name
            config_details: Optional configuration details
            original_error: Optional original exception
        """
        if context:
            if config_details:
                context.details = context.details or {}
                context.details.update(config_details)
        else:
            context = ErrorContext(
                operation=operation or "configuration",
                error_code=ErrorCode.CONFIG_GENERAL,
                details=config_details or {}
            )

        super().__init__(
            message,
            context=context,
            original_error=original_error
        )

class StateError(ProcessingError):
    """Error specific to state management operations.

    Handles errors related to invalid state transitions, state validation,
    and state-dependent operations. This is particularly useful for components
    that maintain internal state machines or lifecycle management.

    Attributes:
        context: Detailed error context including state information
        current_state: The current state when the error occurred
        expected_state: The expected or target state
    """
    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        operation: Optional[str] = None,
        current_state: Optional[str] = None,
        expected_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize state error with state information.

        Args:
            message: Error description
            context: Optional error context
            operation: Optional operation name
            current_state: Optional current state description
            expected_state: Optional expected state description
            details: Optional additional details
            original_error: Optional original exception
        """
        state_details = {
            **(details or {}),
            "current_state": current_state,
            "expected_state": expected_state
        }

        if context:
            context.details = context.details or {}
            context.details.update(state_details)
        else:
            context = ErrorContext(
                operation=operation or "state_management",
                error_code=ErrorCode.STATE_INVALID,
                details=state_details
            )

        super().__init__(
            message,
            context=context,
            original_error=original_error
        )
        self.current_state = current_state
        self.expected_state = expected_state

class ValidationError(ProcessingError):
    """Error specific to validation operations.

    Handles errors related to data validation, format checking, and constraints.

    Attributes:
        context: Detailed error context including validation details
    """
    def __init__(
        self,
        message: str,
        *,
        context: Optional[ErrorContext] = None,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        constraints: Optional[Dict[str, Any]] = None,
        original_error: Optional[Exception] = None
    ):
        """Initialize validation error.

        Args:
            message: Error description
            context: Optional error context
            operation: Optional operation name
            details: Optional validation details
            constraints: Optional validation constraints
            original_error: Optional original exception
        """
        if context:
            if details:
                context.details = context.details or {}
                context.details.update(details)
            if constraints:
                context.details["constraints"] = constraints
        else:
            context = ErrorContext(
                operation=operation or "validation",
                error_code=ErrorCode.VALIDATION_GENERAL,
                details={**(details or {}), "constraints": constraints} if constraints else details
            )

        super().__init__(
            message,
            context=context,
            original_error=original_error
        )
