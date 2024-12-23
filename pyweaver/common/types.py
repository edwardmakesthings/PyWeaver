"""Type definitions and enums for project tools.

Provides shared type definitions, enums, and error classes used across
all project tools.

Path: pyweaver/common/types.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set
import re

class GeneratorError(Exception):
    """Base error for all generator operations."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message)
        self.message = message
        self.code = code or 'GEN_ERR'

class ValidationError(GeneratorError):
    """Error during validation operations."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'VAL_ERR')

class ProcessingError(GeneratorError):
    """Error during processing operations."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'PROC_ERR')

class ConfigurationError(GeneratorError):
    """Error in configuration."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'CFG_ERR')

class FileError(GeneratorError):
    """Error during file operations."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'FILE_ERR')

# Specific error types
class CombinerError(GeneratorError):
    """File combiner specific errors."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'COMB_ERR')

class InitGeneratorError(GeneratorError):
    """Init generator specific errors."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'INIT_ERR')

class StructureGeneratorError(GeneratorError):
    """Structure generator specific errors."""

    def __init__(self, message: str, code: str = None):
        super().__init__(message, code or 'STRUCT_ERR')

# Error code constants
ERROR_CODES = {
    'GEN_ERR': 'General generator error',
    'VAL_ERR': 'Validation error',
    'PROC_ERR': 'Processing error',
    'CFG_ERR': 'Configuration error',
    'FILE_ERR': 'File operation error',
    'COMB_ERR': 'File combiner error',
    'INIT_ERR': 'Init generator error',
    'STRUCT_ERR': 'Structure generator error'
}

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

@dataclass(frozen=True)  # Make the class immutable
class Pattern:
    """File pattern matching utility."""
    pattern: str
    is_negation: bool = False
    # regex should not be included in hash or equality comparisons
    regex: Optional[re.Pattern] = field(default=None, hash=False, compare=False)

    def __post_init__(self):
        """Convert pattern to regex."""
        if self.pattern.startswith('!'):
            # Since class is frozen, use object.__setattr__
            object.__setattr__(self, 'pattern', self.pattern[1:])
            object.__setattr__(self, 'is_negation', True)

        pattern = self.pattern
        # Convert glob patterns to regex
        pattern = pattern.replace('\\', '/')  # Normalize path separators
        pattern = re.escape(pattern)  # Escape special regex characters
        pattern = pattern.replace('\\*\\*', '.*')  # Replace ** with .*
        pattern = pattern.replace('\\*', '[^/]*')  # Replace * with [^/]*
        pattern = f"^{pattern}$"  # Anchor pattern

        try:
            # Since class is frozen, use object.__setattr__
            object.__setattr__(self, 'regex', re.compile(pattern))
        except re.error as e:
            # Fall back to a literal match pattern
            object.__setattr__(self, 'regex', re.compile(re.escape(self.pattern)))

    def matches(self, path: str | Path) -> bool:
        """Test if path matches pattern."""
        path_str = str(path).replace('\\', '/')  # Normalize path separators
        result = bool(self.regex.search(path_str))
        return not result if self.is_negation else result

    def __hash__(self):
        """Make Pattern hashable based on pattern string and negation flag."""
        return hash((self.pattern, self.is_negation))