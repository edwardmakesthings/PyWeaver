"""Type definitions and enums for project tools.

Provides shared type definitions, enums, and error classes used across
all project tools.

Path: tools/project_tools/common/types.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
import re

class GeneratorError(Exception):
    """Base exception for all generator errors."""

class ProcessingError(GeneratorError):
    """Error during file processing."""

class ValidationError(GeneratorError):
    """Error during file validation."""

class WriterError(GeneratorError):
    """Error during file writing."""

class GeneratorMode(Enum):
    """Operation modes for generators."""
    PREVIEW = "preview"  # Show what would be written
    OUTPUT_ONLY = "output_only"  # Generate combined output file
    WRITE = "write"  # Actually write the files

@dataclass
class GeneratorOptions:
    """Configuration options for generators."""
    mode: GeneratorMode = GeneratorMode.PREVIEW
    output_path: Optional[Path] = None
    dry_run: bool = True
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)

@dataclass
class GeneratorResult:
    """Result from a generator operation."""
    success: bool
    message: str
    files_processed: int = 0
    files_written: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class Pattern:
    """File pattern matching utility."""
    pattern: str
    regex: Optional[str] = None
    is_negation: bool = False

    def __post_init__(self):
        """Convert pattern to regex."""
        if self.pattern.startswith('!'):
            self.pattern = self.pattern[1:]
            self.is_negation = True

        pattern = self.pattern
        # Convert glob patterns to regex
        pattern = pattern.replace('.', r'\.')
        pattern = pattern.replace('**', '.*?')
        pattern = pattern.replace('*', '[^/]*?')
        pattern = f"^{pattern}$"

        self.regex = re.compile(pattern)

    def matches(self, path: str | Path) -> bool:
        """Test if path matches pattern."""
        result = bool(self.regex.match(str(path)))
        return not result if self.is_negation else result
