# Quick Start Guide

This guide will help you get started with PyWeaver's main features quickly. We'll look at basic examples of each tool that you can adapt for your needs.

## Installation

First, install PyWeaver using pip:

```bash
pip install pyweaver
```

## Generating Project Structure

To visualize your project's structure:

```python
from pyweaver.processors import generate_structure

# Generate a tree-style structure
structure = generate_structure(
    "my_project",
    style="tree",
    show_size=True,
    ignore_patterns={"**/__pycache__", "**/.git"}
)

print(structure)
```

This will output something like:
```
my_project/
├── src/ (4.2 KB)
│   ├── __init__.py (128 B)
│   ├── core.py (2.1 KB)
│   └── utils.py (2.0 KB)
└── tests/ (1.8 KB)
    ├── test_core.py (1.2 KB)
    └── test_utils.py (600 B)
```

## Managing Init Files

To generate or update `__init__.py` files:

```python
from pyweaver.processors import generate_init_files

# Preview changes
changes = generate_init_files(
    "my_package",
    collect_submodules=True,
    preview=True
)

# This will show you the planned content of each __init__.py file:
"""
Would update: my_package/core/__init__.py:
'''Core functionality for my_package.

This module provides core components and base classes.

Path: my_package/core/__init__.py
'''

from .handlers import BaseHandler, CustomHandler
from .processors import BaseProcessor, DataProcessor
from .interfaces import HandlerInterface, ProcessorInterface

__all__ = [
    'BaseHandler',
    'CustomHandler',
    'BaseProcessor',
    'DataProcessor',
    'HandlerInterface',
    'ProcessorInterface'
]
"""

# Generate files if the preview looks good
result = generate_init_files(
    "my_package",
    collect_submodules=True)
```

## Combining Files

To combine multiple source files:

```python
from pyweaver.processors import combine_files

# Combine Python files
result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py"],
    remove_comments=True
)

if result.success:
    print(f"Combined {result.files_processed} files")
```

## Next Steps

For more detailed information about each feature:

- Learn about [Structure Generation](structure.md)
- Explore [Init Files Management](init.md)
- Understand [File Combining](combining.md)

For complete API documentation, check out the [API Reference](../reference/pyweaver/processors/file_combiner.md).