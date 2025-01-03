# Init File Management

The init file generator helps you maintain clean and organized `__init__.py` files across your Python project. This guide covers everything from basic generation to advanced configuration and customization.

## Basic Usage

Generate init files with default settings using the `generate_init_files` function:

```python
from pyweaver.processors import generate_init_files

# Preview changes first
changes = generate_init_files(
    "my_package",
    preview=True  # Don't write files, just show what would change
)

# Generate files if preview looks good
result = generate_init_files("my_package")
print(f"Updated {result.files_processed} init files")
```

## Export Collection

The generator can collect exports in different ways:

### All Public Names
Collects all non-underscore names:
```python
from pyweaver.processors import generate_init_files, ExportMode

result = generate_init_files(
    "my_package",
    export_mode=ExportMode.ALL_PUBLIC
)
```

### Explicit Exports
Only collects names listed in `__all__`:
```python
result = generate_init_files(
    "my_package",
    export_mode=ExportMode.EXPLICIT
)
```

### Custom Export Rules
Use patterns to control exports:
```python
result = generate_init_files(
    "my_package",
    export_mode=ExportMode.CUSTOM,
    exports_blacklist={
        "*_internal",
        "test_*",
        "_*"
    }
)
```

## Content Organization

### Section-Based Organization

Organize init file content into logical sections:

```python
from pyweaver.processors import (
    InitFileProcessor,
    ImportSection,
    ImportOrderPolicy
)

processor = InitFileProcessor("my_package")

# Configure sections
processor.init_config.global_settings.sections = {
    ImportSection.CLASSES.value: {
        "enabled": True,
        "order": 1,
        "header_comment": "# Classes",
        "include_patterns": {"*Controller", "*Service"}
    },
    ImportSection.FUNCTIONS.value: {
        "enabled": True,
        "order": 2,
        "header_comment": "# Functions",
        "include_patterns": {"get_*", "create_*"}
    },
    ImportSection.CONSTANTS.value: {
        "enabled": True,
        "order": 3,
        "header_comment": "# Constants",
        "include_patterns": {"*_CONFIG", "DEFAULT_*"}
    }
}

result = processor.process()
```

### Import Ordering

Control how imports are ordered:

```python
result = generate_init_files(
    "my_package",
    order_policy=ImportOrderPolicy.DEPENDENCY_FIRST  # Order by dependencies
)

# Other ordering options:
# - ImportOrderPolicy.ALPHABETICAL
# - ImportOrderPolicy.CUSTOM (uses custom_order list)
# - ImportOrderPolicy.LENGTH (by import statement length)
```

## Docstring Generation

Customize docstrings for init files:

```python
result = generate_init_files(
    "my_package",
    docstring="""Package initialization.

This module provides core functionality for the package.
Automatically generated by PyWeaver.

Path: {path}
"""
)
```

## Advanced Usage

### Using the Processor Class

For more control, use the `InitFileProcessor` class directly:

```python
from pyweaver.processors import InitFileProcessor

processor = InitFileProcessor(
    root_dir="my_package",
    dry_run=True  # Start in preview mode
)

# Configure processor
processor.init_config.global_settings.collect_from_submodules = True
processor.init_config.global_settings.excluded_paths = {"tests", "docs"}

# Preview changes
changes = processor.preview()
for path, content in changes.items():
    print(f"Would update: {path}")
    print(content)
    print("-" * 80)

# Generate if preview looks good
processor.dry_run = False
result = processor.process()
```

### Pattern-Based Exclusions

Control which paths are processed:

```python
result = generate_init_files(
    "my_package",
    exclude_patterns={
        "tests/*",
        "docs/*",
        "**/_*",  # Exclude private modules
        "**/internal/*"
    }
)
```

## Best Practices

1. **Export Management**
   - Choose an export mode that matches your project's style
   - Use consistent naming conventions for exports
   - Document export decisions in comments

2. **Section Organization**
   - Group related imports into sections
   - Use clear section headers
   - Order sections logically

3. **Documentation**
   - Include clear docstrings
   - Document module relationships
   - Keep comments up to date

4. **Maintenance**
   - Review init files periodically
   - Update when module structure changes
   - Use preview mode before making changes

## Common Issues

### Circular Imports
If you encounter circular imports:
- Review your module dependencies
- Consider restructuring your imports
- Use lazy imports where appropriate

### Missing Exports
If exports aren't being collected:
- Check your export mode
- Verify file patterns
- Look for syntax errors in source files

## Next Steps

- Learn about [Structure Generation](structure.md)
- Explore [File Combining](combining.md)
- Check the [API Reference](../reference/pyweaver/processors/file_combiner.md) for detailed information