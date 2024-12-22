"""Public interface for initialization file generation.

Provides functionality for generating and managing __init__.py files with
options for previewing changes, collecting imports, and controlling content
generation.

Classes:
    InitGenerator: Main interface for init file generation.
    InitGeneratorConfig: Configuration for init file generation.
    ExportCollectionMode: Controls how exports are collected.

Path: tools/project_tools/init_generator/generator.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Set, Optional

from ..common.types import GeneratorMode, GeneratorResult, GeneratorError
from ..common.processor import FileProcessor, ValidationResult
from ._impl._generator import InitGeneratorImpl

class ExportCollectionMode(Enum):
    """Controls how exports should be collected from modules."""
    EXPLICIT = "explicit"  # Only explicitly marked exports (__all__)
    ALL_PUBLIC = "all_public"  # All public names (no leading underscore)
    CUSTOM = "custom"  # Use custom export collection logic

@dataclass
class InitGeneratorConfig:
    """Configuration for init file generation."""
    root_dir: Path
    mode: GeneratorMode = GeneratorMode.PREVIEW
    output_file: Optional[Path] = None
    export_mode: ExportCollectionMode = ExportCollectionMode.ALL_PUBLIC
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)
    docstring_template: Optional[str] = None
    combine_output: bool = False

class InitGeneratorError(GeneratorError):
    """Base error for init file generation."""

class InitGenerator(FileProcessor):
    """Main interface for init file generation."""

    def __init__(self, config: InitGeneratorConfig):
        super().__init__(options=config)
        self._impl = InitGeneratorImpl(config)

    def preview(self) -> Dict[Path, str]:
        """Preview init files that would be generated.

        Returns:
            Dict mapping paths to their generated content
        """
        return self._impl.preview_files()

    def write(self) -> GeneratorResult:
        """Write init files according to configuration.

        Returns:
            Result of the write operation
        """
        return self._impl.write_files()

    def generate_combined(self, output_path: Optional[Path] = None) -> Path:
        """Generate combined output of all init files.

        Args:
            output_path: Optional path for combined output

        Returns:
            Path to generated file

        Raises:
            InitGeneratorError: If output path not provided and not in config
        """
        if not output_path and not self._impl.config.output_file:
            raise InitGeneratorError("Output path required for combined generation")
        return self._impl.generate_combined(output_path or self._impl.config.output_file)

    def validate(self) -> ValidationResult:
        """Validate configuration and preparation.

        Returns:
            Validation result with any errors/warnings
        """
        result = super().validate()

        # Add init-specific validation
        if self._impl.config.mode == GeneratorMode.OUTPUT_ONLY:
            if not self._impl.config.output_file:
                result.is_valid = False
                result.errors.append("Output file required for OUTPUT_ONLY mode")

        return result

def create_generator(
    root_dir: Path,
    mode: GeneratorMode = GeneratorMode.PREVIEW,
    **kwargs
) -> InitGenerator:
    """Create a configured generator instance.

    Args:
        root_dir: Root directory to process
        mode: Operation mode
        **kwargs: Additional configuration options

    Returns:
        Configured InitGenerator instance
    """
    config = InitGeneratorConfig(
        root_dir=root_dir,
        mode=mode,
        **kwargs
    )
    return InitGenerator(config)

def preview_generator(root_dir: Path, **kwargs) -> InitGenerator:
    """Create a generator in preview mode.

    Args:
        root_dir: Root directory to process
        **kwargs: Additional configuration options

    Returns:
        InitGenerator in preview mode
    """
    return create_generator(root_dir, GeneratorMode.PREVIEW, **kwargs)
