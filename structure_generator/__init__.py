"""Project structure generator.

Provides functionality for generating and documenting project directory
structures with configurable output formats and filtering options.

Classes:
    StructureGenerator: Main interface for generation.
    StructureConfig: Configuration options.
    OutputFormat: Available output formats.

Functions:
    create_generator: Create configured instance.
    quick_generate: Simple one-shot generation.

Path: tools/project_tools/structure_generator/__init__.py
"""

from .generator import (
    StructureGenerator,
    StructureConfig,
    OutputFormat,
    create_generator,
    quick_generate
)

__all__ = [
    "StructureGenerator",
    "StructureConfig",
    "OutputFormat",
    "create_generator",
    "quick_generate"
]
