"""Utility functions and classes for file processing operations.

This module provides essential utilities that support the core functionality:
- Python module analysis and information extraction
- Pattern matching for files and paths
- Object representation generation
- Path manipulation and validation

The utilities are designed to be:
- Efficient through proper caching
- Memory-conscious for large operations
- Thread-safe where needed
- Easily extensible

Example:
    ```python
    from pyweaver.utils import ModuleAnalyzer, PatternMatcher

    # Analyze Python modules
    analyzer = ModuleAnalyzer()
    info = analyzer.analyze_file('module.py')
    print(f"Found {len(info.exports)} exports")

    # Match file patterns
    matcher = PatternMatcher()
    if matcher.matches_path_pattern('src/test.py', '*.py'):
        print("Processing Python file...")
    ```

Path: pyweaver/utils/__init__.py
"""

from .module_analyzer import (
    ImportInfo,
    FunctionInfo,
    ClassInfo,
    ModuleInfo,
    ModuleAnalyzer
)

from .patterns import (
    PatternType,
    PatternCache,
    PatternMatcher
)

from .repr import (
    comprehensive_repr
)

__all__ = [
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