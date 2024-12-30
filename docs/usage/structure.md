# Structure Generation

The structure generator helps you visualize and document your project's directory structure. This guide explains how to use it effectively, from basic usage to advanced features.

## Basic Usage

The simplest way to generate a structure visualization is using the `generate_structure` function:

```python
from pyweaver.processors import generate_structure

structure = generate_structure(
    "my_project",
    style="tree",
    show_size=True
)
print(structure)
```

This will output something like:
```
my_project/
├── src/ (4.2 KB)
│   ├── core.py (2.1 KB)
│   ├── models.py (1.5 KB)
│   └── utils.py (600 B)
└── tests/ (1.8 KB)
    ├── test_core.py (1.2 KB)
    └── test_models.py (600 B)
```

## Output Styles

The structure generator supports several output styles to match your needs:

### Tree Style
The traditional tree view with branch connectors (can be seen above):
```python
structure = generate_structure("src", style="tree")
```

### Flat Style
A simple list of paths:
```python
structure = generate_structure("src", style="flat")
```
```
src/core.py
src/models.py
src/utils.py
src/tests/test_core.py
```

### Markdown Style
Documentation-ready Markdown format:
```python
structure = generate_structure("src", style="markdown")
```
```markdown
- src/
  - core.py
  - models.py
  - utils.py
  - tests/
    - test_core.py
```

## Advanced Features

### Pattern Matching

Control which files are included using glob patterns:

```python
structure = generate_structure(
    "my_project",
    style="tree",
    include_patterns={"*.py", "*.md"},
    ignore_patterns={
        "**/__pycache__",
        "**/.git",
        "**/node_modules",
        "**/*.pyc"
    }
)
```

### Size and Date Information

Add file sizes and modification dates:

```python
structure = generate_structure(
    "my_project",
    show_size=True,
    show_date=True,
    size_format="auto"  # "bytes", "kb", "mb", or "auto"
)
```

### Depth Control

Limit the directory depth to show:

```python
structure = generate_structure(
    "my_project",
    max_depth=3  # Only show up to 3 levels deep
)
```

## Using the StructurePrinter Class

For more control, use the `StructurePrinter` class directly:

```python
from pyweaver.processors import (
    StructurePrinter,
    StructureOptions,
    ListingStyle,
    SortOrder
)

# Configure options
options = StructureOptions(
    style=ListingStyle.TREE,
    sort_order=SortOrder.ALPHA_DIRS_FIRST,
    show_size=True,
    show_date=True,
    max_depth=3,
    ignore_patterns={"**/__pycache__", "**/.git"}
)

# Create printer and generate structure
printer = StructurePrinter("my_project", options)
structure = printer.generate_structure()

# Get statistics
stats = printer.get_statistics()
print(f"Files: {stats['total_files']}")
print(f"Directories: {stats['total_dirs']}")
print(f"Total size: {stats['total_size']:,} bytes")
```

## Best Practices

1. **Pattern Management**
   - Keep ignore patterns in configuration files
   - Use consistent patterns across your project
   - Document pattern choices in comments

2. **Documentation Integration**
   - Generate structure documentation automatically
   - Include structure in project README
   - Update structure diagrams when significant changes occur

3. **Size Optimization**
   - Use `max_depth` for large projects
   - Filter unnecessary files with patterns
   - Consider size format based on project scale

4. **Error Handling**
   ```python
   try:
       structure = generate_structure("my_project")
   except Exception as e:
       print(f"Error generating structure: {e}")
   ```

## Common Issues

### Permission Errors
If you encounter permission errors, check:
- File permissions in your project
- Whether you have read access to all directories
- If any files are locked by other processes

### Performance Issues
For large projects:
- Use pattern matching to limit file scanning
- Set appropriate max_depth
- Consider using flat style instead of tree for better performance

## Next Steps

- Learn about [Init Files Management](init.md)
- Explore [File Combining](combining.md)
- Check the [API Reference](../api.md) for detailed information