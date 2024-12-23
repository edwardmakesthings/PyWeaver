"""Private implementation of configuration-based init file generation.

Handles configuration parsing, validation, and init file generation using
the configuration settings.

Path: pyweaver/init_generator/_impl/_config_generator.py
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from pyweaver.common.type_definitions import (
    GeneratorMode,
    GeneratorResult,
    ValidationResult,
    ProcessingError
)
from pyweaver.init_generator.config_generator import (
    PackageConfig,
    ConfigSectionSettings,
    ConfigInlineContent
)
from pyweaver.init_generator.generator import (
    create_generator,
    ExportCollectionMode,
    InlineContent,
    InitGeneratorConfig
)

logger = logging.getLogger(__name__)

class ConfigGeneratorImpl:
    """Internal implementation of config-based generation."""

    def __init__(self, config_path: Path, root_dir: Optional[Path] = None):
        self.config_path = config_path
        self.root_dir = root_dir
        self.config_data = self._load_config()
        self.global_config = self._parse_package_config(self.config_data.get("global", {}))
        self._cached_generators = {}
        self._module_cache = {}

    def process_package(self, package_path: str, mode: GeneratorMode = None) -> GeneratorResult:
        """Process single package configuration."""
        try:
            # Get merged configuration - ensure package-specific content only
            config = self._get_package_config(package_path, strict_scope=True)

            # Create generator if needed
            if package_path not in self._cached_generators:
                self._cached_generators[package_path] = self._create_generator(
                    package_path, config
                )

            generator = self._cached_generators[package_path]

            # Handle preview mode
            if mode == GeneratorMode.PREVIEW:
                changes = generator.preview()
                self._display_preview(package_path, changes)

                if input(f"\nGenerate init files for {package_path}? (y/n): ").lower() != 'y':
                    return GeneratorResult(
                        success=True,
                        message="Generation skipped by user",
                        files_processed=len(changes)
                    )

            # Generate files
            return generator.write()

        except Exception as e:
            logger.error("Error processing package %s: %s", package_path, e)
            raise ProcessingError(f"Failed to process {package_path}: {str(e)}")

    def process_all(self, mode: GeneratorMode = GeneratorMode.PREVIEW) -> Dict[str, GeneratorResult]:
        """Process all package configurations."""
        results = {}

        for package_path in self.config_data.get("paths", {}):
            try:
                results[package_path] = self.process_package(package_path, mode)
            except Exception as e:
                logger.error("Error processing %s: %s", package_path, e)
                results[package_path] = GeneratorResult(
                    success=False,
                    message=str(e),
                    errors=[str(e)]
                )

        return results

    def validate(self) -> ValidationResult:
        """Validate configuration and structure."""
        result = ValidationResult(is_valid=True)

        try:
            # Check config file exists
            if not self.config_path.exists():
                result.is_valid = False
                result.errors.append(f"Config file not found: {self.config_path}")
                return result

            # Check global config
            if "global" not in self.config_data:
                result.warnings.append("No global configuration found")

            # Validate each package path
            for package_path in self.config_data.get("paths", {}):
                # Get actual path considering root_dir
                actual_path = self._get_actual_path(package_path)
                if not actual_path.exists():
                    result.warnings.append(f"Package path does not exist: {actual_path}")

            return result

        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed: {str(e)}")
            return result

    def _get_actual_path(self, package_path: str) -> Path:
        """Get actual filesystem path for package."""
        # Convert package path to filesystem path
        path = Path(package_path.replace('.', '/'))

        # If root_dir is provided, make path relative to it
        if self.root_dir is not None:
            path = self.root_dir / path

        return path

    def _load_config(self) -> Dict[str, Any]:
        """Load and parse configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error("Error loading config: %s", e)
            raise ProcessingError(f"Failed to load config: {str(e)}")

    def _parse_package_config(self, config_data: Dict[str, Any]) -> PackageConfig:
        """Parse package configuration data."""
        sections = {}
        for name, section_data in config_data.get("sections", {}).items():
            sections[name] = ConfigSectionSettings(
                enabled=section_data.get("enabled", True),
                order=section_data.get("order", 0),
                header_comment=section_data.get("header_comment"),
                separator=section_data.get("separator", "\n"),
                include_patterns=set(section_data.get("include_patterns", [])),
                exclude_patterns=set(section_data.get("exclude_patterns", []))
            )

        # Only parse inline content if it's in the current package's config
        inline_content = {}
        if config_data.get("inline_content"):
            inline_content = {
                name: ConfigInlineContent(
                    code=content["code"],
                    order=content.get("order", 999),
                    section=content.get("section", "constants"),
                    before_imports=content.get("before_imports", False)
                )
                for name, content in config_data["inline_content"].items()
            }

        return PackageConfig(
            docstring=config_data.get("docstring"),
            order_policy=config_data.get("order_policy", "dependency_first"),
            exports_blacklist=set(config_data.get("exports_blacklist", [])),
            excluded_paths=set(config_data.get("excluded_paths", [])),
            collect_from_submodules=config_data.get("collect_from_submodules", True),
            sections=sections,
            inline_content=inline_content  # Only package-specific inline content
        )

    def _parse_inline_content(self, inline_data: Dict) -> Dict[str, InlineContent]:
        """Parse inline content configuration."""
        return {
            name: InlineContent(
                code=content["code"],
                order=content.get("order", 999),
                section=content.get("section", "constants"),
                before_imports=content.get("before_imports", False)
            )
            for name, content in inline_data.items()
        }

    def _get_package_config(self, package_path: str, strict_scope: bool = True) -> PackageConfig:
        """Get configuration for package with proper scoping."""
        # Start with clean base config with NO inline content from global
        config = PackageConfig(
            docstring=self.global_config.docstring,
            order_policy=self.global_config.order_policy,
            exports_blacklist=self.global_config.exports_blacklist.copy(),
            excluded_paths=self.global_config.excluded_paths.copy(),
            collect_from_submodules=self.global_config.collect_from_submodules,
            sections=dict(self.global_config.sections),
            inline_content={}  # Always start empty
        )

        if package_path in self.config_data.get("paths", {}):
            package_data = self.config_data["paths"][package_path]

            # Add only package-specific configuration
            if "docstring" in package_data:
                config.docstring = package_data["docstring"]
            if "order_policy" in package_data:
                config.order_policy = package_data["order_policy"]
            if "exports_blacklist" in package_data:
                config.exports_blacklist.update(package_data["exports_blacklist"])
            if "excluded_paths" in package_data:
                config.excluded_paths.update(package_data["excluded_paths"])
            if "collect_from_submodules" in package_data:
                config.collect_from_submodules = package_data["collect_from_submodules"]
            if "sections" in package_data:
                config.sections.update(self._parse_sections(package_data["sections"]))

            # Only add inline content if it's explicitly defined for this package
            if "inline_content" in package_data:
                config.inline_content = {
                    name: ConfigInlineContent(
                        code=content["code"],
                        order=content.get("order", 999),
                        section=content.get("section", "constants"),
                        before_imports=content.get("before_imports", False)
                    )
                    for name, content in package_data["inline_content"].items()
                }

        return config

    def _parse_sections(self, sections_data: Dict) -> Dict:
        """Parse section configurations."""
        return {
            name: ConfigSectionSettings(
                enabled=section.get("enabled", True),
                order=section.get("order", 0),
                header_comment=section.get("header_comment"),
                separator=section.get("separator", "\n"),
                include_patterns=set(section.get("include_patterns", [])),
                exclude_patterns=set(section.get("exclude_patterns", []))
            )
            for name, section in sections_data.items()
        }

    def _create_generator(self, package_path: str, config: PackageConfig):
        """Create generator with configuration."""
        path = self._get_actual_path(package_path)

        return create_generator(
            root_dir=path,
            mode=GeneratorMode.PREVIEW,
            export_mode=ExportCollectionMode.ALL_PUBLIC,
            exclude_patterns=config.excluded_paths,
            docstring_template=config.docstring,
            sections=config.sections,
            order_policy=config.order_policy,
            inline_content=config.inline_content  # Pass the package-specific inline content
        )

    def _create_generator_config(self, path: Path, config: PackageConfig) -> InitGeneratorConfig:
        """Create generator configuration from package config."""
        return InitGeneratorConfig(
            root_dir=path,
            mode=GeneratorMode.PREVIEW,
            export_mode=ExportCollectionMode.ALL_PUBLIC,
            exclude_patterns=config.excluded_paths,
            docstring_template=config.docstring,
            sections=config.sections,
            order_policy=config.order_policy
        )

    def _display_preview(self, package_path: str, changes: Dict[Path, str]) -> None:
        """Display preview of changes."""
        print(f"\nPreview for {package_path}:")
        print("=" * 80)

        for path, content in changes.items():
            print(f"--- {path} ---")
            print("-" * 40)
            print(content)
            print("-" * 40)