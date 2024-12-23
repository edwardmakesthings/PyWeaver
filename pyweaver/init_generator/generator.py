"""Public interface for initialization file generation.

Provides functionality for generating and managing __init__.py files with
options for previewing changes, collecting imports, and controlling content
generation.

Classes:
    InitGenerator: Main interface for init file generation.
    InitGeneratorConfig: Configuration for init file generation.
    ExportCollectionMode: Controls how exports are collected.

Path: pyweaver/init_generator/generator.py
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Set, Optional

from pyweaver.common.base_processor import BaseProcessor
from pyweaver.common.type_definitions import (
    GeneratorMode,
    GeneratorResult,
    ValidationResult,
    GeneratorError
)

class ImportOrderPolicy(Enum):
    """Import ordering policies."""
    DEPENDENCY_FIRST = "dependency_first"
    ALPHABETICAL = "alphabetical"
    CUSTOM = "custom"
    LENGTH = "length"

class ImportSection(Enum):
    """Section types for __init__ file organization."""
    CLASSES = "classes"
    FUNCTIONS = "functions"
    CONSTANTS = "constants"
    TYPE_DEFINITIONS = "type_definitions"
    VARIABLES = "variables"

class ExportCollectionMode(Enum):
    """Controls how exports should be collected from modules."""
    EXPLICIT = "explicit"  # Only explicitly marked exports (__all__)
    ALL_PUBLIC = "all_public"  # All public names (no leading underscore)
    CUSTOM = "custom"  # Use custom export collection logic

@dataclass
class SectionConfig:
    """Configuration for a section in the __init__ file."""
    enabled: bool = True
    order: int = 0
    header_comment: Optional[str] = None
    footer_comment: Optional[str] = None
    separator: str = "\n"
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)

@dataclass
class InlineContent:
    """Content to be included directly in the __init__ file."""
    code: str
    order: int = 999  # Default to end of file
    section: Optional[str] = None  # Section to place it in
    before_imports: bool = False  # Whether to place before imports

@dataclass
class InitGeneratorConfig:
    """Configuration for init file generation."""
    root_dir: Path
    mode: GeneratorMode = GeneratorMode.PREVIEW
    output_path: Optional[Path] = None  # Changed from output_file to output_path
    order_policy: ImportOrderPolicy = ImportOrderPolicy.DEPENDENCY_FIRST
    sections: Dict[ImportSection, SectionConfig] = field(default_factory=dict)
    inline_content: Optional[Dict[str, InlineContent]] = None
    exclude_patterns: Set[str] = field(default_factory=set)
    include_patterns: Set[str] = field(default_factory=set)
    docstring_template: Optional[str] = None
    combine_output: bool = False
    export_mode: ExportCollectionMode = ExportCollectionMode.ALL_PUBLIC

    @property
    def output_file(self) -> Optional[Path]:
        """Maintain backward compatibility."""
        return self.output_path

    @output_file.setter
    def output_file(self, value: Optional[Path]):
        """Maintain backward compatibility."""
        self.output_path = value

class InitGeneratorError(GeneratorError):
    """Init generator specific errors."""
    def __init__(self, message: str):
        super().__init__(message, "INIT_ERR")

class InitGenerator(BaseProcessor):
    """Main interface for init file generation."""

    def __init__(self, config: InitGeneratorConfig):
        super().__init__(options=config)
        self.config = config
        self._impl = None  # Will be initialized lazily

    def preview(self) -> Dict[Path, str]:
        """Preview init files that would be generated.

        Returns:
            Dict mapping paths to their generated content
        """
        self._ensure_impl()
        return self._impl.preview_files()

    def write(self) -> GeneratorResult:
        """Write init files according to configuration.

        Returns:
            Result of the write operation
        """
        try:
            self._ensure_impl()
            return self._impl.write_files()
        except Exception as e:
            self.add_error(f"Failed to write files: {str(e)}")
            return self.get_result()

    def generate_combined(self, output_path: Optional[Path] = None) -> Path:
        """Generate combined output of all init files.

        Args:
            output_path: Optional path for combined output

        Returns:
            Path to generated file

        Raises:
            InitGeneratorError: If output path not provided and not in config
        """
        if not output_path and not self.config.output_file:
            raise InitGeneratorError("Output path required for combined generation")

        self._ensure_impl()
        return self._impl.generate_combined(output_path or self.config.output_file)

    def validate(self) -> ValidationResult:
        """Validate configuration and preparation.

        Returns:
            Validation result with any errors/warnings
        """
        result = super().validate()

        if self.config.mode == GeneratorMode.OUTPUT_ONLY:
            if not self.config.output_file:
                result.is_valid = False
                result.errors.append("Output file required for OUTPUT_ONLY mode")

        return result

    def _ensure_impl(self):
        """Ensure implementation is initialized."""
        if self._impl is None:
            from pyweaver.init_generator._impl._generator import InitGeneratorImpl
            self._impl = InitGeneratorImpl(self.config)

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
