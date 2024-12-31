"""Example usage of the file combiner.

This example demonstrates different ways to combine files using both the
simple convenience function and the more advanced processor interface.
Each example illustrates different features and capabilities of the
file combiner.

Key features demonstrated:
- Basic file combining
- Content processing modes
- Pattern-based selection
- Preview functionality
- Tree structure generation

Example use cases:
1. Documentation: Combine source files for documentation
2. Analysis: Create consolidated files for code analysis
3. Distribution: Generate combined versions of multi-file projects
4. Backup: Create consolidated backups of important files

Path: examples/file_combiner_example.py
"""

from pyweaver.config.combiner import ContentMode
from pyweaver.processors import (
    combine_files,
    FileCombinerProcessor
)

def basic_usage():
    """Simple file combining."""
    result = combine_files(
        "src",
        "combined.txt",
        patterns=["*.py"]
    )

    if result.success:
        print(f"Combined {result.files_processed} files")
        print("Output written to: combined.txt")
    else:
        print(f"Combining failed: {result.message}")

def advanced_usage():
    """Advanced usage with configuration."""
    # Create processor with specific configuration
    processor = FileCombinerProcessor(
        root_dir="src",
        output_file="docs/combined.txt",
        patterns=["*.py", "*.ts", "*.tsx"],
        content_mode=ContentMode.NO_COMMENTS,
        generate_tree=True
    )

    # Preview changes first
    print("Preview of combined output:")
    processor.preview(print_preview=True)

    if input("\nGenerate combined file? (y/n): ").lower() == 'y':
        result = processor.process()
        if result.success:
            processor.write()  # Write to configured output file
            print(f"Successfully combined {result.files_processed} files")
        else:
            print(f"Combining failed: {result.message}")
            for error in result.errors:
                print(f"Error: {error}")

def content_modes():
    """Demonstrate different content processing modes."""
    modes = [
        (ContentMode.FULL, "full"),
        (ContentMode.NO_COMMENTS, "no_comments"),
        (ContentMode.NO_DOCSTRINGS, "no_docstrings"),
        (ContentMode.MINIMAL, "minimal")
    ]

    for mode, name in modes:
        output_file = f"output_{name}.txt"
        print(f"\nMode: {name}")

        result = combine_files(
            "src",
            output_file,
            patterns=["*.py"],
            print_output=True  # Show preview
        )

        if result.success:
            print(f"Generated {output_file}")
            print(f"Files processed: {result.files_processed}")
        else:
            print(f"Failed: {result.message}")

if __name__ == "__main__":
    print("File Combiner Examples")
    print("1. Basic Usage")
    print("2. Advanced Usage")
    print("3. Content Modes")

    choice = input("\nSelect example (1-3): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        advanced_usage()
    elif choice == "3":
        content_modes()
    else:
        print("Invalid choice")
