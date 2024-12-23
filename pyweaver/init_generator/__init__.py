"""Init file generator for Python packages.

Provides functionality for generating and managing __init__.py files in
Python packages with configurable content collection and preview capabilities.

Classes:
    InitGenerator: Main interface for init file generation.
    InitGeneratorConfig: Configuration options.
    ExportCollectionMode: Export collection modes.
    InitGeneratorError: Generator-specific errors.

Functions:
    create_generator: Create configured generator instance.
    preview_generator: Create generator in preview mode.

Path: pyweaver/init_generator/__init__.py
"""

from .generator import (
    InitGenerator,
    InitGeneratorConfig,
    ExportCollectionMode,
    InitGeneratorError,
    create_generator,
    preview_generator
)

from .config_generator import (
    ConfigSectionSettings,
    ConfigInlineContent,
    PackageConfig,
    ConfigGenerator,
    create_config_generator,
    quick_generate_from_config
)

__all__ = [
    "InitGenerator",
    "InitGeneratorConfig",
    "ExportCollectionMode",
    "InitGeneratorError",
    "create_generator",
    "preview_generator",

    "ConfigSectionSettings",
    "ConfigInlineContent",
    "PackageConfig",
    "ConfigGenerator",
    "create_config_generator",
    "quick_generate_from_config"
]
