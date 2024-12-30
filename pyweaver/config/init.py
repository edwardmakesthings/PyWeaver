"""Enhanced configuration system for init file generation.

This module provides specialized configuration support for generating and managing
Python package initialization files. It builds on the base configuration system
to provide fine-grained control over __init__.py file generation, including
content organization, export management, and documentation handling.

The configuration system supports:
- Section-based content organization
- Flexible export configuration
- Import order management
- Custom content injection
- Documentation templating

The module integrates with our broader configuration ecosystem by:
- Extending the base configuration validation system
- Using standardized error handling
- Supporting hierarchical configuration inheritance
- Providing efficient caching and validation

Path: pyweaver/config/init.py
"""
import logging
import json
from enum import Enum
from pathlib import Path
from typing import Dict, Set, List, Optional, Any
from pydantic import BaseModel, Field, field_validator

from pyweaver.config.base import BaseConfig, ConfigValidationModel
from pyweaver.common.errors import (ConfigError, ErrorContext, ErrorCode)
from pyweaver.utils.patterns import PatternMatcher
from pyweaver.utils.repr import comprehensive_repr

logger = logging.getLogger(__name__)

class ImportOrderPolicy(str, Enum):
    """Controls how imports are ordered within init files.

    This enum defines different strategies for organizing imports,
    allowing for flexible organization based on project needs.
    """
    DEPENDENCY_FIRST = "dependency_first"  # Orders based on dependency graph
    ALPHABETICAL = "alphabetical"         # Simple alphabetical ordering
    CUSTOM = "custom"                     # Uses custom_order list
    LENGTH = "length"                     # Orders by import statement length

class ImportSection(str, Enum):
    """Defines different sections within init files.

    This enum represents the various logical sections that can appear
    in an initialization file, helping to organize the content clearly.
    """
    CLASSES = "classes"
    FUNCTIONS = "functions"
    CONSTANTS = "constants"
    TYPE_DEFINITIONS = "type_definitions"
    VARIABLES = "variables"

    def get_default_patterns(self) -> Set[str]:
        """Get default patterns for identifying content for this section."""
        if self == ImportSection.CONSTANTS:
            return {"*_CONSTANT", "*_CONFIG", "DEFAULT_*"}
        elif self == ImportSection.TYPE_DEFINITIONS:
            return {"*Type", "*Config"}
        return {"*"}

    def get_default_order(self) -> int:
        """Get the default ordering position for this section."""
        section_orders = {
            ImportSection.TYPE_DEFINITIONS: 0,
            ImportSection.CONSTANTS: 1,
            ImportSection.CLASSES: 2,
            ImportSection.FUNCTIONS: 3,
            ImportSection.VARIABLES: 4
        }
        return section_orders.get(self, 99)

class ExportMode(str, Enum):
    """Defines how exports are collected from modules.

    This enum determines the strategy for identifying which names
    should be exported from the initialization file.
    """
    EXPLICIT = "explicit"    # Only items in __all__
    ALL_PUBLIC = "all_public"  # All non-underscore names
    CUSTOM = "custom"        # Uses custom export rules

class InitSectionConfig(BaseModel):
    """Configuration for a content section in init files.

    This model defines how a specific section should be formatted and
    what content it should include. It supports pattern-based content
    selection and custom formatting options.
    """
    enabled: bool = True
    order: int = Field(default=0)
    header_comment: Optional[str] = None
    footer_comment: Optional[str] = None
    separator: str = "\n"
    include_patterns: Set[str] = Field(default_factory=set)
    exclude_patterns: Set[str] = Field(default_factory=set)

    @field_validator('separator')
    @classmethod
    def validate_separator(cls, v: str) -> str:
        """Ensure separator contains at least one newline."""
        if '\n' not in v:
            v = v + '\n'
        return v

    def should_include(self, name: str, pattern_matcher: PatternMatcher) -> bool:
        """Determine if a name belongs in this section.

        Args:
            name: Name to check
            pattern_matcher: Pattern matcher to use

        Returns:
            True if name should be included
        """
        # Check exclusions first
        if any(pattern_matcher.matches_name_pattern(name, pattern)
               for pattern in self.exclude_patterns):
            return False

        # Check inclusions if specified
        if self.include_patterns:
            return any(pattern_matcher.matches_name_pattern(name, pattern)
                      for pattern in self.include_patterns)

        return True

class InlineContent(BaseModel):
    """Configuration for inline content injection.

    This model defines content that should be injected into init files,
    allowing for custom code or documentation insertion with proper
    positioning control.
    """
    code: str
    order: int = 999
    section: Optional[str] = None
    before_imports: bool = False

    @field_validator('code')
    @classmethod
    def validate_code(cls, v: str) -> str:
        """Ensure code ends with exactly one newline."""
        return v.rstrip() + '\n'

class InitSettings(BaseModel):
    """Core settings model for init file generation.

    This model defines all configurable aspects of init file generation,
    providing a validated structure for configuration data.
    """
    docstring: Optional[str] = None
    order_policy: ImportOrderPolicy = ImportOrderPolicy.DEPENDENCY_FIRST
    exports_blacklist: Set[str] = Field(default_factory=set)
    excluded_paths: Set[str] = Field(default_factory=set)
    collect_from_submodules: bool = True
    include_submodules: Optional[List[str]] = None
    sections: Dict[str, InitSectionConfig] = Field(default_factory=dict)
    inline_content: Dict[str, InlineContent] = Field(default_factory=dict)
    custom_order: Optional[List[str]] = None
    dependencies: List[str] = Field(default_factory=list)
    exact_path_only: bool = False
    export_mode: ExportMode = ExportMode.ALL_PUBLIC

    @field_validator('sections')
    @classmethod
    def validate_sections(cls, v: Dict[str, InitSectionConfig]) -> Dict[str, InitSectionConfig]:
        """Validate section configurations and set defaults.

        This method ensures all sections have proper configurations and
        default values where needed.
        """
        try:
            valid_sections = {section.value for section in ImportSection}
            validated = {}

            for name, config in v.items():
                if name not in valid_sections:
                    raise ValueError(f"Invalid section name: {name}")

                # Apply defaults based on section type
                section = ImportSection(name)
                if not config.include_patterns:
                    config.include_patterns = section.get_default_patterns()
                if config.order == 0:
                    config.order = section.get_default_order()

                validated[name] = config

            return validated

        except Exception as e:
            raise ValueError(f"Section validation failed: {e}") from e

    @field_validator('export_mode')
    @classmethod
    def validate_export_mode(cls, v: ExportMode) -> ExportMode:
        """Validate export mode configuration."""
        if v == ExportMode.CUSTOM and not cls.exports_blacklist:
            raise ValueError("Custom export mode requires exports_blacklist")
        return v

class InitConfig(BaseConfig[InitSettings]):
    """Configuration manager for init file generation.

    This class handles all aspects of init file configuration, providing
    a clean interface while ensuring configuration validity through the
    validation system.

    Example:
        ```python
        config = InitConfig(
            global_settings={
                "docstring": "Package initialization.",
                "order_policy": "dependency_first",
                "sections": {
                    "classes": {
                        "enabled": True,
                        "order": 1
                    }
                }
            },
            path_specific={
                "src/models": {
                    "collect_from_submodules": False
                }
            }
        )

        # Get configuration for a package
        settings = config.get_settings_for_path("src/models")
        ```
    """

    def __init__(
        self,
        global_settings: Optional[Dict[str, Any]] = None,
        path_specific: Optional[Dict[str, Dict[str, Any]]] = None,
        pattern_matcher: Optional[PatternMatcher] = None
    ):
        """Initialize init configuration.

        Args:
            global_settings: Default settings applied globally
            path_specific: Dictionary mapping paths to their settings
            pattern_matcher: Optional pattern matcher instance

        Raises:
            ConfigError: If configuration initialization fails
        """
        try:
            super().__init__(global_settings, path_specific)
            self.pattern_matcher = pattern_matcher or PatternMatcher()

            logger.debug(
                "Initialized InitConfig with %d path-specific settings",
                len(self.path_specific)
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_config",
                error_code=ErrorCode.CONFIG_INIT,
                details={
                    "has_global": bool(global_settings),
                    "path_count": len(path_specific) if path_specific else 0
                }
            )
            raise ConfigError(
                "Failed to initialize init configuration",
                context=context,
                original_error=e
            ) from e

    @classmethod
    def from_file(cls, config_path: Path | str, root_dir: Optional[Path] = None) -> 'InitConfig':
        """Create configuration from JSON file.

        This method provides additional support for root directory
        configuration when loading from a file.

        Args:
            config_path: Path to configuration file
            root_dir: Optional root directory for relative paths

        Returns:
            Initialized InitConfig instance

        Raises:
            ConfigError: If configuration loading fails
        """
        try:
            if isinstance(config_path, str):
                config_path = Path(config_path)

            if not config_path.exists():
                return cls._create_default_config(config_path, root_dir)

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            return cls(**config_data)

        except Exception as e:
            context = ErrorContext(
                operation="load_config",
                error_code=ErrorCode.CONFIG_PATH,
                path=config_path,
                details={"root_dir": str(root_dir) if root_dir else None}
            )
            raise ConfigError(
                "Failed to load configuration file",
                context=context,
                original_error=e
            ) from e

    def _validate_config(self, config_data: Dict[str, Any]) -> ConfigValidationModel[InitSettings]:
        """Validate raw configuration data.

        This method ensures the configuration data meets our requirements
        and provides proper error context if validation fails.

        Args:
            config_data: Raw configuration dictionary

        Returns:
            Validated configuration model

        Raises:
            ConfigError: If validation fails
        """
        try:
            return ConfigValidationModel[InitSettings](**config_data)
        except Exception as e:
            context = ErrorContext(
                operation="validate_config",
                error_code=ErrorCode.CONFIG_VALIDATION,
                details={
                    "error": str(e),
                    "config_keys": list(config_data.keys())
                }
            )
            raise ConfigError(
                "Configuration validation failed",
                context=context,
                original_error=e
            ) from e

    def _merge_settings(
        self,
        base: InitSettings,
        path_settings: Optional[InitSettings]
    ) -> InitSettings:
        """Merge path-specific settings into base settings.

        This method implements the strategy for combining base settings
        with path-specific overrides, handling complex nested structures
        like sections and inline content.

        Args:
            base: Base settings to start from
            path_settings: Optional path-specific settings to merge

        Returns:
            New InitSettings instance with merged configuration

        Raises:
            ConfigError: If settings merge fails
        """
        try:
            if not path_settings:
                return base.model_copy()

            merged = InitSettings(
                docstring=path_settings.docstring or base.docstring,
                order_policy=path_settings.order_policy,
                exports_blacklist=base.exports_blacklist | path_settings.exports_blacklist,
                excluded_paths=base.excluded_paths | path_settings.excluded_paths,
                collect_from_submodules=path_settings.collect_from_submodules,
                include_submodules=path_settings.include_submodules or base.include_submodules,
                custom_order=path_settings.custom_order or base.custom_order,
                dependencies=base.dependencies + path_settings.dependencies,
                exact_path_only=path_settings.exact_path_only,
                export_mode=path_settings.export_mode
            )

            # Merge sections
            merged.sections = base.sections.copy()
            for name, section in path_settings.sections.items():
                if name in merged.sections:
                    base_section = merged.sections[name]
                    merged.sections[name] = InitSectionConfig(
                        enabled=section.enabled,
                        order=section.order if section.order is not None else base_section.order,
                        header_comment=section.header_comment or base_section.header_comment,
                        footer_comment=section.footer_comment or base_section.footer_comment,
                        separator=section.separator,
                        include_patterns=base_section.include_patterns | section.include_patterns,
                        exclude_patterns=base_section.exclude_patterns | section.exclude_patterns
                    )
                else:
                    merged.sections[name] = section

            # Merge inline content
            merged.inline_content = {**base.inline_content, **path_settings.inline_content}

            return merged

        except Exception as e:
            context = ErrorContext(
                operation="merge_settings",
                error_code=ErrorCode.CONFIG_MERGE,
                details={
                    "base_sections": list(base.sections.keys()),
                    "override_sections": list(path_settings.sections.keys()) if path_settings else []
                }
            )
            raise ConfigError(
                "Failed to merge settings",
                context=context,
                original_error=e
            ) from e

    @classmethod
    def _create_default_config(cls, config_path: Path, root_dir: Optional[Path] = None) -> 'InitConfig':
        """Create and save default configuration.

        This method generates a sensible default configuration when none exists,
        providing a starting point for customization.

        Args:
            config_path: Where to save default config
            root_dir: Optional root directory for relative paths

        Returns:
            Default configuration instance

        Raises:
            ConfigError: If default config creation fails
        """
        try:
            default_config = {
                "global_settings": {
                    "docstring": "Auto-generated __init__.py file.",
                    "order_policy": ImportOrderPolicy.DEPENDENCY_FIRST.value,
                    "sections": {
                        ImportSection.CLASSES.value: {
                            "enabled": True,
                            "order": ImportSection.CLASSES.get_default_order(),
                            "include_patterns": list(ImportSection.CLASSES.get_default_patterns())
                        },
                        ImportSection.FUNCTIONS.value: {
                            "enabled": True,
                            "order": ImportSection.FUNCTIONS.get_default_order(),
                            "include_patterns": list(ImportSection.FUNCTIONS.get_default_patterns())
                        },
                        ImportSection.CONSTANTS.value: {
                            "enabled": True,
                            "order": ImportSection.CONSTANTS.get_default_order(),
                            "include_patterns": list(ImportSection.CONSTANTS.get_default_patterns())
                        }
                    },
                    "export_mode": ExportMode.ALL_PUBLIC.value,
                    "collect_from_submodules": True
                },
                "path_specific": {}
            }

            # Create config directory if needed
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # Save default configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4)

            logger.info(
                "Created default configuration at %s",
                config_path
            )
            return cls(**default_config)

        except Exception as e:
            context = ErrorContext(
                operation="create_default_config",
                error_code=ErrorCode.CONFIG_INIT,
                path=config_path,
                details={
                    "root_dir": str(root_dir) if root_dir else None
                }
            )
            raise ConfigError(
                "Failed to create default configuration",
                context=context,
                original_error=e
            ) from e

    def __repr__(self) -> str:
        """Get string representation of configuration."""
        return comprehensive_repr(
            self,
            prioritize=["global_settings", "path_specific"],
            exclude=["pattern_matcher"],
            one_per_line=True
        )
