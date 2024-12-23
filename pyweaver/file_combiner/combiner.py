"""Public interface for file combining operations.

Provides functionality for combining multiple source files into a single
output file with configurable comment and docstring handling.

Classes:
    FileCombiner: Main interface for file combining.
    CombinerConfig: Configuration for file combining.
    FileHandlingMode: How to handle file content.

Functions:
    create_combiner: Create configured combiner instance.
    quick_combine: Simple one-shot file combining.

Path: pyweaver/file_combiner/combiner.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional, Set

from pyweaver.common.base_processor import BaseProcessor
from pyweaver.common.type_definitions import (
    GeneratorResult,
    ValidationResult
)

class FileHandlingMode(Enum):
    """How file content should be handled."""
    FULL = "full"  # Keep all content
    NO_COMMENTS = "no_comments"  # Remove comments
    NO_DOCSTRINGS = "no_docstrings"  # Remove docstrings
    MINIMAL = "minimal"  # Remove both comments and docstrings

@dataclass
class CombinerConfig:
    """Configuration for file combining."""
    root_dir: Path
    patterns: List[str]
    output_file: Path
    mode: FileHandlingMode = FileHandlingMode.FULL
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)
    generate_tree: bool = False

class FileCombiner(BaseProcessor):
    """Combines multiple source files."""

    def __init__(self, config: CombinerConfig):
        super().__init__(options=config)
        self.config = config

    def combine(self) -> GeneratorResult:
        """Combine files according to configuration."""
        try:
            self._process_files()
            self._write_output()
            return self.get_result()
        except Exception as e:
            self.add_error(f"Failed to combine files: {str(e)}")
            return self.get_result()

    def preview(self) -> str:
        """Preview combined output."""
        self._process_files()
        return self._format_output()

    def validate(self) -> ValidationResult:
        """Validate configuration."""
        result = super().validate()

        if not self.config.patterns:
            result.is_valid = False
            result.errors.append("At least one file pattern required")

        if not self.config.output_file:
            result.is_valid = False
            result.errors.append("Output file path required")

        return result

    def _process_files(self):
        """Process input files."""
        # Implementation details here

    def _write_output(self):
        """Write combined output."""
        # Implementation details here

    def _format_output(self) -> str:
        """Format combined output."""
        # Implementation details here
        return ""  # Placeholder

def create_combiner(
    root_dir: Path,
    patterns: List[str],
    output_file: Path,
    mode: FileHandlingMode = FileHandlingMode.FULL,
    **kwargs
) -> FileCombiner:
    """Create a configured combiner instance."""
    config = CombinerConfig(
        root_dir=root_dir,
        patterns=patterns,
        output_file=output_file,
        mode=mode,
        **kwargs
    )
    return FileCombiner(config)

def quick_combine(
    input_dir: Path,
    output_file: Path,
    patterns: Optional[List[str]] = None,
) -> GeneratorResult:
    """Quick file combining with minimal configuration."""
    config = CombinerConfig(
        root_dir=input_dir,
        patterns=patterns or ["*.py"],
        output_file=output_file
    )
    combiner = FileCombiner(config)
    return combiner.combine()
