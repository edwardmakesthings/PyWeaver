# PyWeaver

PyWeaver is a Python toolkit for weaving together well-structured Python projects. It provides a suite of tools for generating project structures, managing initialization files, and combining source files with a focus on maintainability and organization.

[![PyPI version](https://badge.fury.io/py/pyweaver.svg)](https://badge.fury.io/py/pyweaver)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **Structure Generation**: Generate and document project directory structures with configurable output formats
- **Init File Management**: Automatically generate and maintain `__init__.py` files with export collection and docstring support
- **File Combining**: Merge multiple source files with configurable handling of comments and docstrings
- **Flexible Configuration**: Extensive configuration options for customizing behavior
- **Preview Support**: Preview changes before applying them
- **Pattern Matching**: Sophisticated pattern matching for file inclusion/exclusion

## Installation

```bash
pip install pyweaver
```

## Quick Start

### Generate Project Structure

```python
from pyweaver import create_structure_generator

# Generate project structure documentation
generator = create_structure_generator(
    root_dir="my_project",
    output_file="structure.md",
    format="markdown",
    show_size=True
)

# Preview before generating
print(generator.preview())

# Generate if it looks good
result = generator.generate()
```

### Manage Init Files

```python
from pyweaver import create_init_generator

# Create init file generator
generator = create_init_generator(
    root_dir="my_package",
    mode="preview",  # Start in preview mode
    export_mode="all_public",
    exclude_patterns={"test/*", "**/_*"}
)

# Preview changes
changes = generator.preview()
for path, content in changes.items():
    print(f"Would write to {path}:")
    print(content)

# Generate after preview
result = generator.write()
```

### Combine Files

```python
from pyweaver import create_file_combiner

# Create file combiner
combiner = create_file_combiner(
    root_dir="my_project",
    patterns=["*.py", "*.tsx"],
    output_file="combined_output.txt",
    mode="no_comments",  # Remove comments but keep docstrings
    exclude_patterns={"node_modules/*", "**/__pycache__/*"},
    generate_tree=True  # Also generate directory structure
)

# Preview combined output
preview = combiner.preview()
print(preview)

# Combine if preview looks good
result = combiner.combine()
```

## Documentation

### Structure Generation

The structure generator creates documentation of your project's directory structure in various formats:

- Tree-style with connectors
- Plain file listing
- Markdown format

```python
from pyweaver import create_structure_generator, OutputFormat

generator = create_structure_generator(
    root_dir="my_project",
    output_file="structure.md",
    format=OutputFormat.MARKDOWN,
    show_size=True,    # Include file sizes
    max_depth=3,       # Limit directory depth
    exclude_patterns={
        "**/__pycache__",
        "**/.git",
        "**/node_modules"
    }
)
```

### Init File Generation

The init generator helps maintain consistent `__init__.py` files across your project:

- Collects exports from modules
- Generates appropriate docstrings
- Manages dependencies
- Supports different export collection modes

```python
from pyweaver import create_init_generator, ExportCollectionMode

generator = create_init_generator(
    root_dir="my_package",
    export_mode=ExportCollectionMode.ALL_PUBLIC,
    exclude_patterns={"test/*"},
    docstring_template="""
    ${module_name}

    Module description.

    Path: ${path}
    """
)
```

### File Combining

The file combiner merges multiple source files with configurable content handling:

- Combine multiple files into one
- Remove comments and/or docstrings
- Generate directory structure
- Pattern-based file selection

```python
from pyweaver import create_file_combiner, FileHandlingMode

combiner = create_file_combiner(
    root_dir="my_project",
    patterns=["*.py"],
    output_file="combined.txt",
    mode=FileHandlingMode.NO_COMMENTS,
    exclude_patterns={"test/*"},
    generate_tree=True
)
```

## Configuration

### Pattern Matching

PyWeaver uses glob-style patterns for file matching:

- `*` matches any characters except path separators
- `**` matches any characters including path separators
- `?` matches any single character
- `[seq]` matches any character in seq
- `[!seq]` matches any character not in seq

Example patterns:
```python
exclude_patterns = {
    "**/__pycache__/*",  # Exclude all pycache directories
    "test_*.py",         # Exclude test files
    "**/_*.py",          # Exclude private modules
}
```

### File Handling Modes

When combining files, several modes are available:

- `FULL`: Keep all content
- `NO_COMMENTS`: Remove comments
- `NO_DOCSTRINGS`: Remove docstrings
- `MINIMAL`: Remove both comments and docstrings

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

PyWeaver was inspired by the need for better project organization tools in the Python ecosystem and builds upon best practices from various project management tools.