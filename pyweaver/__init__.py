"""PyWeaver - A toolkit for weaving together well-structured Python projects.

This package provides tools for managing Python project structure and organization:

Core Features:
- Directory structure visualization and documentation
- Init file generation and management
- File combining with content processing
- Configuration management
- Pattern matching utilities

The package is organized into several modules:
- processors: Main processing implementations
- common: Shared functionality and base classes
- config: Configuration management
- utils: Utility functions and helpers

Example:
    ```python
    from pyweaver.processors import (
        generate_structure,
        generate_init_files,
        combine_files
    )

    # Generate project structure
    structure = generate_structure(
        "src",
        style="tree",
        show_size=True
    )

    # Generate init files
    generate_init_files(
        "src",
        collect_submodules=True
    )

    # Combine files
    combine_files(
        "src",
        "combined.txt",
        patterns=["*.py"]
    )
    ```

Path: pyweaver/__init__.py
"""

# Version information
__version__ = '1.0.0'

# Import processors and their components
from .processors import (
    # Structure generation
    ListingStyle,
    SortOrder,
    StructureOptions,
    StructurePrinter,
    generate_structure,

    # File combining
    ContentMode,
    FileSectionConfig,
    CombinerProgress,
    CombinerConfig,
    FileCombinerProcessor,
    combine_files,

    # Init file generation
    InitFileProgress,
    InitFileProcessor,
    generate_init_files
)

# Import configuration components
from .config import (
    # Base configuration
    ConfigValidationModel,
    BaseConfig,

    # Path configuration
    PathSettings,
    PathConfig,

    # Init configuration
    ImportOrderPolicy,
    ImportSection,
    ExportMode,
    InitSectionConfig,
    InlineContent,
    InitSettings,
    InitConfig
)

# Import common components
from .common import (
    # Base processor
    ProcessorState,
    ProcessorProgress,
    ProcessorResult,
    BaseProcessor,

    # Error handling
    ErrorCategory,
    ErrorCode,
    ErrorContext,
    ProcessingError,
    FileError,
    ConfigError,
    StateError,
    ValidationError,

    # Tracking
    TrackerType,
    TrackerState,
    ItemStatus,
    TrackedItem,
    TrackerStats,
    FileTracker
)

# Import utilities
from .utils import (
    # Module analysis
    ImportInfo,
    FunctionInfo,
    ClassInfo,
    ModuleInfo,
    ModuleAnalyzer,

    # Pattern matching
    PatternType,
    PatternCache,
    PatternMatcher,

    # Representation
    comprehensive_repr
)

# Define public API
__all__ = [
    # Processors
    'ListingStyle',
    'SortOrder',
    'StructureOptions',
    'StructurePrinter',
    'generate_structure',
    'ContentMode',
    'FileSectionConfig',
    'CombinerProgress',
    'CombinerConfig',
    'FileCombinerProcessor',
    'combine_files',
    'InitFileProgress',
    'InitFileProcessor',
    'generate_init_files',

    # Configuration
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

    # Common Components
    'ProcessorState',
    'ProcessorProgress',
    'ProcessorResult',
    'BaseProcessor',
    'ErrorCategory',
    'ErrorCode',
    'ErrorContext',
    'ProcessingError',
    'FileError',
    'ConfigError',
    'StateError',
    'ValidationError',
    'TrackerType',
    'TrackerState',
    'ItemStatus',
    'TrackedItem',
    'TrackerStats',
    'FileTracker',

    # Utilities
    'ImportInfo',
    'FunctionInfo',
    'ClassInfo',
    'ModuleInfo',
    'ModuleAnalyzer',
    'PatternType',
    'PatternCache',
    'PatternMatcher',
    'comprehensive_repr'
]