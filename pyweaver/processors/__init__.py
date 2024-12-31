"""File processing implementations and utilities.

This module provides concrete implementations of file processors for:
- Directory structure visualization
- File combining and content processing
- Init file generation and management

Each processor provides both a comprehensive class-based interface for advanced
usage and simple convenience functions for common cases. The processors handle:
- File traversal and filtering
- Content processing and transformation
- Progress tracking and reporting
- Error handling and recovery

Example:
    ```python
    from pyweaver.processors import (
        generate_structure,
        combine_files,
        generate_init_files
    )

    # Generate directory structure
    print(generate_structure("src", style="tree", show_size=True))

    # Combine Python files
    combine_files("src", "combined.py", patterns=["*.py"])

    # Generate init files
    init_files = generate_init_files(
        "src",
        collect_submodules=True,
        preview=True
    )
    for path, content in init_files.items():
        print(f"Would update: {path}")
    ```

Path: pyweaver/processors/__init__.py
"""

from .structure_generator import (
    SortOrder,
    StructureOptions,
    EntryInfo,
    StructurePrinter,
    generate_structure
)
from .file_combiner import (
    CombinerProgress,
    FileCombinerProcessor,
    combine_files
)
from .init_processor import (
    InitFileProgress,
    InitFileProcessor,
    generate_init_files
)

__all__ = [
    'SortOrder',
    'StructureOptions',
    'EntryInfo',
    'StructurePrinter',
    'generate_structure',

    'CombinerProgress',
    'FileCombinerProcessor',
    'combine_files',

    'InitFileProgress',
    'InitFileProcessor',
    'generate_init_files'
]
