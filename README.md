# PyWeaver

PyWeaver is a Python toolkit for weaving together well-structured Python projects. It provides a suite of file processing tools focused on modularity, maintainability, and organization.

[![PyPI version](https://badge.fury.io/py/pyweaver.svg)](https://badge.fury.io/py/pyweaver)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Structure Generation**: Visualize and document project directory structures with customizable formats and filtering
- **Init File Management**: Generate and maintain `__init__.py` files with sophisticated export collection and section organization
- **File Combining**: Merge multiple source files with intelligent content processing and language-specific handling
- **Comprehensive Configuration**: Rich configuration system supporting global and path-specific settings
- **Preview Support**: Preview all changes before applying them
- **Robust Error Handling**: Detailed error reporting with proper context and recovery options

## Installation

```bash
pip install pyweaver
```

## Quick Start

### Generate Project Structure

```python
from pyweaver.processors import generate_structure, ListingStyle

# Generate tree structure
structure = generate_structure(
    "src",
    style=ListingStyle.TREE,
    show_size=True,
    max_depth=3,
    ignore_patterns={"**/__pycache__", "**/.git"}
)

print(structure)
```

### Manage Init Files

```python
from pyweaver.processors import generate_init_files, ExportMode

# Generate init files with preview
changes = generate_init_files(
    "src",
    docstring="Package initialization.",
    collect_submodules=True,
    export_mode=ExportMode.ALL_PUBLIC,
    preview=True
)

# Review changes
for path, content in changes.items():
    print(f"Would update: {path}")

# Generate files
result = generate_init_files(
    "src",
    collect_submodules=True,
    preview=False
)
```

### Combine Files

```python
from pyweaver.processors import combine_files, ContentMode

# Combine files with content processing
result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py", "*.tsx"],
    content_mode=ContentMode.NO_COMMENTS,
    generate_tree=True
)

if result.success:
    print(f"Combined {result.files_processed} files")
```

## Advanced Usage

### Structure Generation

The structure generator offers multiple output styles and comprehensive configuration:

```python
from pyweaver.processors import (
    StructurePrinter,
    StructureOptions,
    ListingStyle,
    SortOrder
)

options = StructureOptions(
    style=ListingStyle.TREE,
    sort_order=SortOrder.ALPHA_DIRS_FIRST,
    show_size=True,
    show_date=True,
    max_depth=3,
    ignore_patterns={
        "**/__pycache__",
        "**/.git",
        "**/node_modules"
    }
)

printer = StructurePrinter("src", options)
structure = printer.generate_structure()
print(structure)

# Get statistics
stats = printer.get_statistics()
print(f"Processed {stats['total_files']} files")
```

### Init File Generation

The init generator supports sophisticated module analysis and content organization:

```python
from pyweaver.processors import (
    InitFileProcessor,
    ImportOrderPolicy,
    ImportSection
)

processor = InitFileProcessor(
    root_dir="src",
    dry_run=True  # Preview mode
)

# Configure section organization
processor.init_config.global_settings.sections = {
    ImportSection.CLASSES.value: {
        "enabled": True,
        "order": 1,
        "header_comment": "# Classes"
    },
    ImportSection.FUNCTIONS.value: {
        "enabled": True,
        "order": 2,
        "header_comment": "# Functions"
    }
}

# Preview changes
changes = processor.preview()
for path, content in changes.items():
    print(f"Would update: {path}")
```

### File Combining

The file combiner provides language-aware content processing and organization:

```python
from pyweaver.processors import (
    FileCombinerProcessor,
    ContentMode,
    FileSectionConfig
)

# Configure section formatting
section_config = FileSectionConfig(
    header_template="#" * 80 + "\n# Source: {path}\n" + "#" * 80,
    footer_template="\n",
    include_empty_lines=True,
    remove_trailing_whitespace=True
)

processor = FileCombinerProcessor(
    root_dir="src",
    output_file="combined.txt",
    patterns=["*.py", "*.tsx"],
    content_mode=ContentMode.NO_COMMENTS,
    section_config=section_config,
    generate_tree=True
)

# Preview output
print(processor.preview())

# Generate if preview looks good
result = processor.process()
```

## Pattern Matching

PyWeaver uses glob-style patterns with additional features:

- `*` matches any characters except path separators
- `**` matches any characters including path separators
- `?` matches any single character
- `[seq]` matches any character in sequence
- `[!seq]` matches any character not in sequence

Example patterns:
```python
exclude_patterns = {
    "**/__pycache__",  # Exclude all pycache directories
    "test_*.py",       # Exclude test files
    "**/_*.py",        # Exclude private modules
    ".git/**",         # Exclude git directory
    "**/*.pyc"         # Exclude compiled Python files
}
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

The project uses pytest for testing. To run the tests:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_file_combiner_enhanced.py

# Run with coverage reporting
pytest --cov=pyweaver
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

The key changes I've made:
1. Updated the API examples to reflect the actual implementation
2. Added more detailed configuration examples
3. Removed the `create_*` factory functions which don't exist
4. Added proper class and enum references
5. Updated the pattern matching section with current capabilities
6. Added testing information
7. Reorganized advanced usage to better reflect the actual features

Would you like me to explain any of these changes in more detail?