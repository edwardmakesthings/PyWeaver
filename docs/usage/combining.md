# File Combining

The file combiner helps you merge multiple source files while intelligently handling comments, docstrings, and formatting. This guide explains how to use its features effectively to create clean, organized combined outputs.

## Understanding File Combining

When working with multiple source files, you might need to combine them for various purposes such as:
- Creating a single-file version of your code
- Preparing code for review or documentation
- Analyzing code structure and dependencies
- Creating deployment bundles

The file combiner helps with these tasks by providing intelligent content processing and organization features.

## Basic Usage

The simplest way to combine files is using the `combine_files` function:

```python
from pyweaver.processors import combine_files

result = combine_files(
    "src",              # Source directory
    "combined.txt",     # Output file
    patterns=["*.py"]   # File patterns to include
)

if result.success:
    print(f"Combined {result.files_processed} files")
else:
    print("Error:", result.message)
```

## Content Processing Modes

The combiner supports different modes for handling comments and docstrings:

### Full Mode
Keeps all content unchanged:
```python
from pyweaver.processors import combine_files, ContentMode

result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py"],
    content_mode=ContentMode.FULL
)
```

### No Comments Mode
Removes comments but keeps docstrings:
```python
result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py"],
    content_mode=ContentMode.NO_COMMENTS
)
```

### No Docstrings Mode
Removes docstrings but keeps comments:
```python
result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py"],
    content_mode=ContentMode.NO_DOCSTRINGS
)
```

### Minimal Mode
Removes both comments and docstrings:
```python
result = combine_files(
    "src",
    "combined.txt",
    patterns=["*.py"],
    content_mode=ContentMode.MINIMAL
)
```

## Section Organization

The combiner can organize files into clear sections:

```python
from pyweaver.processors import (
    FileCombinerProcessor,
    SectionConfig
)

# Create custom section config
section_config = SectionConfig(
    enabled=True,
    header_template="### {path} ###\n",
    footer_template="\n# End of {path} #\n",
    include_empty_lines=False,
    remove_trailing_whitespace=True
)

# Create processor with config
processor = FileCombinerProcessor(
    root_dir="src",
    output_file="combined.txt",
    patterns=["*.py"],
    section_config=section_config
)

# Process files
result = processor.process()
```

## Language Support

The file combiner handles various programming languages intelligently:

### Python Files
- Docstrings (single and multi-line)
- Comments (# style)
- Type hints and decorators

### JavaScript/TypeScript Files
- JSDoc comments
- Single and multi-line comments
- Import/export statements

### Style Files (CSS/SCSS)
- Single and multi-line comments
- Nested comment blocks
- @import statements

### HTML/Vue Files
- HTML comments
- Script and style sections
- Component documentation

## Advanced Features

### Preview Changes

See what will be combined before processing:

```python
processor = FileCombinerProcessor(
    root_dir="src",
    output_file="combined.txt",
    patterns=["*.py"]
)

# Generate preview
preview = processor.preview()
print(preview)

# Generate tree structure
tree = processor.generate_tree()
print(tree)
```

### Pattern Matching

Control which files are included:

```python
processor = FileCombinerProcessor(
    root_dir="src",
    output_file="combined.txt",
    patterns=["*.py", "*.tsx"],
    exclude_patterns={
        "**/__pycache__/*",
        "**/*.pyc",
        "**/node_modules/*",
        "**/.git/*"
    }
)
```

### Error Handling

Handle processing errors gracefully:

```python
try:
    processor = FileCombinerProcessor(
        root_dir="src",
        output_file="combined.txt"
    )

    result = processor.process()
    if not result.success:
        print("Errors occurred:")
        for error in result.errors:
            print(f"- {error}")

except Exception as e:
    print(f"Critical error: {e}")
```

## Best Practices

1. **Content Processing**
   - Choose appropriate processing mode for your needs
   - Be consistent with comment/docstring handling
   - Preserve important documentation

2. **Section Organization**
   - Use clear section headers
   - Group related files together
   - Include file path information

3. **Pattern Management**
   - Be specific with include patterns
   - Exclude unnecessary files
   - Document pattern choices

4. **Performance**
   - Process files in batches if needed
   - Use appropriate pattern matching
   - Consider memory usage for large files

## Common Issues

### Memory Usage
For large projects:
- Process files in smaller groups
- Use more specific patterns
- Consider excluding unnecessary files

### Encoding Issues
If you encounter encoding problems:
- Specify encoding explicitly
- Check for BOM markers
- Verify file encodings match

### Content Processing
If content isn't processed correctly:
- Verify file types are supported
- Check processing mode settings
- Look for malformed comments/docstrings

## Next Steps

- Learn about [Structure Generation](structure.md)
- Explore [Init Files Management](init.md)
- Check the [API Reference](../api.md) for detailed information