"""Example usage of the file combiner.

Demonstrates various approaches to combining files, each suited for
different use cases:

1. Basic Usage (quick_combine):
   - Best for simple file combining needs
   - Combines all matching files in a directory
   - Uses default settings for handling content
   - Ideal for quick documentation tasks
   - Good for creating simple combined outputs

2. Advanced Usage (create_combiner):
   - Perfect for complex combining needs
   - Supports multiple file patterns
   - Can exclude specific paths/patterns
   - Allows preview before combining
   - Can generate directory structure
   - Ideal for creating comprehensive documentation

3. Different Modes:
   - Shows how different handling modes affect output
   - FULL: Keeps all content including comments
   - NO_COMMENTS: Removes comments but keeps docstrings
   - NO_DOCSTRINGS: Keeps comments but removes docstrings
   - MINIMAL: Removes both comments and docstrings
   - Good for understanding content handling options

4. Selective Combining:
   - Best for targeted file combining
   - Can focus on specific file types
   - Supports complex pattern matching
   - Good for creating focused documentation
   - Ideal for specific subsystem documentation
   - Useful for combining related files only

Common Use Cases:
1. Documentation Generation:
   - Combining source files for documentation
   - Creating searchable codebases
   - Generating training materials

2. Code Analysis:
   - Combining files for analysis tools
   - Creating full project overviews
   - Supporting code reviews

3. Distribution:
   - Creating single-file versions of multi-file projects
   - Preparing code for sharing or publication
   - Creating backup consolidations

Path: examples/file_combiner_example.py
"""

from pathlib import Path
from pyweaver.file_combiner import (
    create_combiner,
    quick_combine,
    FileHandlingMode,
    CombinerConfig
)

def basic_usage():
    """Simple file combining with quick_combine."""
    result = quick_combine(
        input_dir=Path("my_project"),
        output_file=Path("combined_output.txt")
    )

    if result.success:
        print(f"Combined {result.files_processed} files")
        print(f"Output written to: {result.files_written}")
    else:
        print(f"Combining failed: {result.message}")

def advanced_usage():
    """Advanced usage with custom configuration."""
    combiner = create_combiner(
        root_dir=Path("my_project"),
        patterns=["*.py", "*.tsx", "*.ts"],
        output_file=Path("docs/combined.txt"),
        mode=FileHandlingMode.NO_COMMENTS,  # Remove comments but keep docstrings
        exclude_patterns={
            "**/node_modules/*",
            "**/__pycache__/*",
            "**/build/*",
            "**/dist/*"
        },
        generate_tree=True  # Also generate directory structure
    )

    # Preview before generating
    print("Preview of combined output:")
    print("-" * 40)
    print(combiner.preview())
    print("-" * 40)

    if input("\nGenerate combined file? (y/n): ").lower() == 'y':
        result = combiner.combine()
        if result.success:
            print(f"Successfully combined {result.files_processed} files")
        else:
            print(f"Combining failed: {result.message}")
            for error in result.errors:
                print(f"Error: {error}")

def different_modes():
    """Demonstrate different file handling modes."""
    input_dir = Path("my_project")
    test_file = Path("test_output")

    # Create output directory
    test_file.parent.mkdir(parents=True, exist_ok=True)

    for mode in FileHandlingMode:
        output_file = test_file / f"combined_{mode.value}.txt"

        combiner = create_combiner(
            root_dir=input_dir,
            patterns=["*.py"],
            output_file=output_file,
            mode=mode
        )

        result = combiner.combine()
        print(f"\nMode {mode.value}:")
        print(f"Success: {result.success}")
        print(f"Files processed: {result.files_processed}")
        if not result.success:
            print(f"Errors: {result.errors}")

def selective_combining():
    """Demonstrate selective file combining with patterns."""
    combiner = create_combiner(
        root_dir=Path("my_project"),
        patterns=["src/**/*.ts", "src/**/*.tsx"],  # TypeScript/React files
        output_file=Path("combined_frontend.txt"),
        mode=FileHandlingMode.NO_COMMENTS,
        exclude_patterns={"**/tests/*", "**/stories/*"},
        generate_tree=True
    )

    # Preview the files that would be included
    preview = combiner.preview()
    print("Files to be combined:")
    print(preview)

    if input("\nProceed with combining? (y/n): ").lower() == 'y':
        result = combiner.combine()
        if result.success:
            print(f"Combined {result.files_processed} files")
            print("Also generated tree structure at: combined_frontend.tree.txt")
        else:
            print(f"Failed: {result.message}")

if __name__ == "__main__":
    print("File Combiner Examples")
    print("1. Basic Usage")
    print("2. Advanced Usage")
    print("3. Different Modes")
    print("4. Selective Combining")

    choice = input("\nSelect example (1-4): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        advanced_usage()
    elif choice == "3":
        different_modes()
    elif choice == "4":
        selective_combining()
    else:
        print("Invalid choice")
