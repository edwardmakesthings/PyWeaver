"""File combiner for merging source files.

Provides functionality for combining multiple source files into a single
output file with configurable handling of comments, docstrings, and
file selection.

Classes:
    FileCombiner: Main interface for file combining.
    CombinerConfig: Configuration options.
    FileHandlingMode: Content handling modes.

Functions:
    create_combiner: Create configured combiner.
    quick_combine: Simple one-shot combining.

Path: pyweaver/file_combiner/__init__.py
"""

from .combiner import (
    FileCombiner,
    CombinerConfig,
    FileHandlingMode,
    create_combiner,
    quick_combine
)

__all__ = [
    "FileCombiner",
    "CombinerConfig",
    "FileHandlingMode",
    "create_combiner",
    "quick_combine"
]
