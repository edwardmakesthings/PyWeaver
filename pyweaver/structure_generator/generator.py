"""Public interface for project structure generation.

Provides functionality for generating and documenting project directory
structures with configurable output formats and filtering.

Classes:
    StructureGenerator: Main interface for structure generation
    StructureConfig: Configuration options
    OutputFormat: Structure output formats

Functions:
    create_generator: Create configured generator instance
    quick_generate: Simple one-shot structure generation

Path: pyweaver/structure_generator/generator.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Set, Optional

from pyweaver.common.base_processor import BaseProcessor
from pyweaver.common.type_definitions import (
    GeneratorMode,
    GeneratorResult,
    ValidationResult,
    GeneratorError
)

class OutputFormat(Enum):
    """Structure output formats."""
    TREE = "tree"       # Tree-style with indentation and connectors
    PLAIN = "plain"     # Simple filepath listing
    MARKDOWN = "md"     # Markdown-formatted structure

@dataclass
class StructureConfig:
    """Configuration for structure generation."""
    root_dir: Path
    output_file: Path
    format: OutputFormat = OutputFormat.TREE
    include_empty: bool = False
    show_size: bool = False
    max_depth: Optional[int] = None
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)

class StructureGeneratorError(GeneratorError):
    """Structure generator specific errors."""
    def __init__(self, message: str):
        super().__init__(message, "STRUCT_ERR")

class StructureGenerator(BaseProcessor):
    """Main interface for structure generation."""

    def __init__(self, config: StructureConfig):
        super().__init__(options=config)
        self.config = config
        self._impl = None  # Will be initialized lazily

    def generate(self) -> GeneratorResult:
        """Generate structure documentation."""
        try:
            self._ensure_impl()
            return self._impl.generate_structure()
        except Exception as e:
            self.add_error(f"Failed to generate structure: {str(e)}")
            return self.get_result()

    def preview(self) -> str:
        """Preview structure without writing."""
        self._ensure_impl()
        return self._impl.preview_structure()

    def validate(self) -> ValidationResult:
        """Validate configuration and preparation."""
        result = super().validate()

        if not self.config.root_dir.is_dir():
            result.is_valid = False
            result.errors.append(
                f"Root directory does not exist: {self.config.root_dir}"
            )

        if self.config.max_depth is not None:
            if self.config.max_depth < 1:
                result.is_valid = False
                result.errors.append("Max depth must be at least 1")

        return result

    def _ensure_impl(self):
        """Ensure implementation is initialized."""
        if self._impl is None:
            from pyweaver.structure_generator._impl._generator import StructureGeneratorImpl
            self._impl = StructureGeneratorImpl(self.config)

def create_generator(
    root_dir: Path,
    output_file: Path,
    format: OutputFormat = OutputFormat.TREE,
    **kwargs
) -> StructureGenerator:
    """Create a configured generator instance.

    Args:
        root_dir: Root directory to analyze
        output_file: Where to write structure
        format: Output format to use
        **kwargs: Additional configuration options

    Returns:
        Configured StructureGenerator instance
    """
    config = StructureConfig(
        root_dir=root_dir,
        output_file=output_file,
        format=format,
        **kwargs
    )
    return StructureGenerator(config)

def quick_generate(
    root_dir: Path,
    output_file: Optional[Path] = None
) -> Path:
    """Quick structure generation with minimal configuration.

    Args:
        root_dir: Directory to analyze
        output_file: Optional output path (default: root_dir/structure.txt)

    Returns:
        Path to generated file
    """
    if output_file is None:
        output_file = root_dir / "structure.txt"

    generator = create_generator(root_dir, output_file)
    generator.generate()
    return output_file
