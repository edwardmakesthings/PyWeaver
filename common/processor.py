"""Base classes for file processing operations.

Provides base classes and utilities for file processing, including
context management, validation, and result handling.

Path: tools/project_tools/common/processor.py
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from .types import Pattern, GeneratorOptions, GeneratorResult

logger = logging.getLogger(__name__)

@dataclass
class ProcessingContext:
    """Context for file processing operations."""
    root_dir: Path
    current_file: Optional[Path] = None
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)

    def __post_init__(self):
        """Convert string patterns to Pattern objects."""
        self._exclude_matchers = {Pattern(p) for p in self.exclude_patterns}
        self._include_matchers = {Pattern(p) for p in self.include_patterns}

    def should_process(self, path: Path) -> bool:
        """Check if path should be processed."""
        try:
            rel_path = path.relative_to(self.root_dir)
        except ValueError:
            return False

        # Check exclusions first
        for matcher in self._exclude_matchers:
            if matcher.matches(rel_path):
                logger.debug("Excluding %s (matched pattern: %s)", rel_path, matcher.pattern)
                return False

        # Then check inclusions
        if self._include_matchers:
            return any(m.matches(rel_path) for m in self._include_matchers)

        return True

@dataclass
class ValidationResult:
    """Result of file validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

class FileProcessor:
    """Base class for file processing operations."""

    def __init__(self, options: GeneratorOptions):
        self.options = options
        self._processed_files: Dict[Path, str] = {}
        self._errors: List[str] = []
        self._warnings: List[str] = []
        self._context = ProcessingContext(
            root_dir=Path(options.output_path).parent if options.output_path else Path.cwd(),
            exclude_patterns=options.exclude_patterns,
            include_patterns=options.include_patterns
        )

    def get_result(self) -> GeneratorResult:
        """Get the result of the processing operation."""
        return GeneratorResult(
            success=len(self._errors) == 0,
            message=self._get_result_message(),
            files_processed=len(self._processed_files),
            files_written=len([f for f in self._processed_files if f.exists()]),
            errors=self._errors.copy(),
            warnings=self._warnings.copy()
        )

    def _get_result_message(self) -> str:
        """Generate result message based on operation outcome."""
        if self._errors:
            return f"Processing completed with {len(self._errors)} errors"
        elif self._warnings:
            return f"Processing completed with {len(self._warnings)} warnings"
        return "Processing completed successfully"

    def add_error(self, error: str):
        """Add an error message."""
        self._errors.append(error)
        logger.error(error)

    def add_warning(self, warning: str):
        """Add a warning message."""
        self._warnings.append(warning)
        logger.warning(warning)

    def validate(self) -> ValidationResult:
        """Validate processor configuration and setup."""
        result = ValidationResult(is_valid=True)

        # Validate root directory exists
        if not self._context.root_dir.exists():
            result.is_valid = False
            result.errors.append(f"Root directory does not exist: {self._context.root_dir}")

        return result
