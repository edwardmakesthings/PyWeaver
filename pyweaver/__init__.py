"""
Project tools for code generation and management.

Provides utilities for managing Python projects including init file generation,
file combining, and structure documentation.

Path: pyweaver/__init__.py
"""

__version__ = '0.1.0'

from .common.type_definitions import (
    GeneratorError,
    GeneratorMode,
    GeneratorOptions,
    GeneratorResult,
    ProcessingError,
    ValidationError,
)

from .file_combiner import (
    FileCombiner,
    CombinerConfig,
    FileHandlingMode,
    create_combiner,
    quick_combine
)

from .init_generator import (
    InitGenerator,
    InitGeneratorConfig,
    ExportCollectionMode,
    create_generator as create_init_generator,
    preview_generator,

    ConfigSectionSettings,
    ConfigInlineContent,
    PackageConfig,
    ConfigGenerator,
    create_config_generator,
    quick_generate_from_config
)

from .structure_generator import (
    StructureGenerator,
    StructureConfig,
    OutputFormat,
    create_generator as create_structure_generator,
    quick_generate
)

__all__ = [
    # Version
    "__version__",

    # Common types
    "GeneratorError",
    "GeneratorMode",
    "GeneratorOptions",
    "GeneratorResult",
    "ProcessingError",
    "ValidationError",

    # File combiner
    "FileCombiner",
    "CombinerConfig",
    "FileHandlingMode",
    "create_combiner",
    "quick_combine",

    # Init generator
    "InitGenerator",
    "InitGeneratorConfig",
    "ExportCollectionMode",
    "create_init_generator",
    "preview_generator",

    "ConfigSectionSettings",
    "ConfigInlineContent",
    "PackageConfig",
    "ConfigGenerator",
    "create_config_generator",
    "quick_generate_from_config",

    # Structure generator
    "StructureGenerator",
    "StructureConfig",
    "OutputFormat",
    "create_structure_generator",
    "quick_generate"
]