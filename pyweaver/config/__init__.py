"""Configuration management for file processing operations.

This module provides a comprehensive configuration system that supports:
- Type-safe configuration through Pydantic models
- Hierarchical configuration with inheritance
- Path-specific configuration overrides
- Init file generation settings
- Configuration validation and error handling

The module is structured around three main configuration types:
- Base configuration providing core functionality
- Path configuration for file/directory operations
- Init configuration for managing __init__.py files

Example:
    ```python
    from pyweaver.config import PathConfig, InitConfig

    # Configure file operations
    path_config = PathConfig(
        global_settings={"ignore_patterns": ["*.pyc"]},
        path_specific={"/src": {"ignore_patterns": ["*.test.py"]}}
    )

    # Configure init file generation
    init_config = InitConfig.from_file("init_config.json")
    settings = init_config.get_settings_for_path("src/module")
    ```

Path: pyweaver/config/__init__.py
"""

from .base import (
    ConfigValidationModel,
    BaseConfig
)
from .path import (
    PathSettings,
    PathConfig
)
from .init import (
    ImportOrderPolicy,
    ImportSection,
    ExportMode,
    InitSectionConfig,
    InlineContent,
    InitSettings,
    InitConfig
)
from .combiner import (
    ContentMode,
    FileSectionConfig,
    CombinerConfig
)

__all__ = [
    'ConfigValidationModel',
    'BaseConfig',

    'PathSettings',
    'PathConfig',

    'ImportOrderPolicy',
    'ImportSection',
    'ExportMode',
    'InitSectionConfig',
    'InlineContent',
    'InitSettings',
    'InitConfig',

    'ContentMode',
    'FileSectionConfig',
    'CombinerConfig'
]