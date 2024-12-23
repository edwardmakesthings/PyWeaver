"""Public interface for configuration-based init file generation.

Provides functionality for generating __init__.py files across a project using
a JSON configuration file. Supports global and package-specific settings,
section organization, and content customization.

Path: pyweaver/init_generator/config_generator.py
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, Set

from .generator import create_generator, ExportCollectionMode, InitGeneratorConfig
from pyweaver.common.type_definitions import (
    GeneratorMode,
    GeneratorResult,
    ValidationResult
)

@dataclass
class ConfigSectionSettings:
    """Configuration for a content section."""
    enabled: bool = True
    order: int = 0
    header_comment: Optional[str] = None
    separator: str = "\n"
    include_patterns: Set[str] = field(default_factory=set)
    exclude_patterns: Set[str] = field(default_factory=set)

@dataclass
class ConfigInlineContent:
    """Configuration for inline content injection."""
    code: str
    order: int = 999
    section: str = "constants"
    before_imports: bool = False

@dataclass
class PackageConfig:
    """Configuration for a specific package."""
    docstring: Optional[str] = None
    order_policy: str = "dependency_first"
    exports_blacklist: Set[str] = field(default_factory=set)
    excluded_paths: Set[str] = field(default_factory=set)
    collect_from_submodules: bool = True
    sections: Dict[str, ConfigSectionSettings] = field(default_factory=dict)
    inline_content: Dict[str, ConfigInlineContent] = field(default_factory=dict)

class ConfigGenerator:
    """Generates init files using JSON configuration."""

    def __init__(
        self,
        config_path: Path,
        root_dir: Optional[Path] = None,
        mode: GeneratorMode = GeneratorMode.PREVIEW
    ):
        """Initialize with configuration file path.

        Args:
            config_path: Path to init_config.json
            root_dir: Optional root directory for package paths
            mode: Generation mode (PREVIEW, OUTPUT_ONLY, or WRITE)
        """
        self.config_path = config_path
        self.root_dir = root_dir
        self.mode = mode
        self._impl = None
        self._ensure_impl()

    def process_package(
        self,
        package_path: str,
        mode: Optional[GeneratorMode] = None
    ) -> GeneratorResult:
        """Process a single package configuration.

        Args:
            package_path: Package path (e.g., "omniui.core")
            mode: Override the default generation mode

        Returns:
            Result of the generation operation
        """
        # Handle mode precedence
        effective_mode = mode or self.mode
        return self._impl.process_package(package_path, effective_mode)

    def process_all(
        self,
        mode: Optional[GeneratorMode] = None
    ) -> Dict[str, GeneratorResult]:
        """Process all packages in configuration.

        Args:
            mode: Override the default generation mode

        Returns:
            Dict mapping package paths to their generation results
        """
        # Handle mode precedence
        effective_mode = mode or self.mode
        return self._impl.process_all(effective_mode)

    def validate(self) -> ValidationResult:
        """Validate configuration and package structure.

        Returns:
            Validation result with any errors/warnings
        """
        return self._impl.validate()

    def _ensure_impl(self):
        """Ensure implementation is initialized."""
        if self._impl is None:
            from ._impl._config_generator import ConfigGeneratorImpl
            self._impl = ConfigGeneratorImpl(self.config_path)

def create_config_generator(
    config_path: Path,
    root_dir: Optional[Path] = None,
    mode: GeneratorMode = GeneratorMode.PREVIEW
) -> ConfigGenerator:
    """Create a config generator instance.

    Args:
        config_path: Path to init_config.json
        root_dir: Optional root directory for package paths
        mode: Generation mode (PREVIEW, OUTPUT_ONLY, or WRITE)

    Returns:
        Configured ConfigGenerator instance
    """
    return ConfigGenerator(config_path, root_dir, mode)

def quick_generate_from_config(
    config_path: Path,
    root_dir: Optional[Path] = None,
    mode: GeneratorMode = GeneratorMode.PREVIEW
) -> Dict[str, GeneratorResult]:
    """Quick generation using configuration file.

    Args:
        config_path: Path to init_config.json
        root_dir: Optional root directory for package paths
        mode: Generation mode (PREVIEW, OUTPUT_ONLY, or WRITE)

    Returns:
        Dict mapping package paths to their generation results
    """
    generator = create_config_generator(config_path, root_dir, mode)
    return generator.process_all(mode=mode)