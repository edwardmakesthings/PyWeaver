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

Path: tools/project_tools/structure_generator/generator.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Set, Optional

from ..common.types import GeneratorMode, GeneratorResult
from ..common.processor import FileProcessor, ValidationResult
from _impl._generator import StructureGeneratorImpl

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

class StructureGenerator(FileProcessor):
    """Main interface for structure generation."""

    def __init__(self, config: StructureConfig):
        super().__init__(options=config)
        self._impl = StructureGeneratorImpl(config)

    def generate(self) -> GeneratorResult:
        """Generate structure documentation."""
        try:
            return self._impl.generate_structure()
        except Exception as e:
            return GeneratorResult(
                success=False,
                message=f"Failed to generate structure: {str(e)}",
                errors=[str(e)]
            )

    def preview(self) -> str:
        """Preview structure without writing."""
        return self._impl.preview_structure()

    def validate(self) -> ValidationResult:
        """Validate configuration and preparation."""
        result = super().validate()

        # Add structure-specific validation
        if not self._impl.config.root_dir.is_dir():
            result.is_valid = False
            result.errors.append(
                f"Root directory does not exist: {self._impl.config.root_dir}"
            )

        if self._impl.config.max_depth is not None:
            if self._impl.config.max_depth < 1:
                result.is_valid = False
                result.errors.append("Max depth must be at least 1")

        return result

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
