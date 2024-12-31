"""Example usage of the init file generator.

This example demonstrates different approaches to generating __init__.py files,
from simple package initialization to complex configurations with customized
content organization.

The init generator supports:
- Simple package initialization
- Customized docstrings and content
- Submodule handling and export collection
- Section-based content organization
- Preview functionality

Example use cases:
1. Package Setup: Initialize new Python packages
2. Documentation: Generate well-documented init files
3. Refactoring: Update init files during restructuring
4. Standardization: Maintain consistent package structure

Path: examples/init_generator_example.py
"""

from pyweaver.processors import (
    generate_init_files,
    InitFileProcessor
)


def basic_usage():
    """Simple init file generation."""
    result = generate_init_files(
        "src",
        docstring="Package initialization.",
        collect_submodules=True,
        print_output=True  # Show what will be generated
    )

    if result.success:
        print(f"\nGenerated {result.files_processed} init files")
    else:
        print(f"\nGeneration failed: {result.message}")

def advanced_usage():
    """Advanced usage with custom configuration."""
    # Create processor with specific settings
    processor = InitFileProcessor(
        root_dir="src",
        config_path="init_config.json",
    )

    # Preview changes first
    processor.preview(print_preview=True)

    if input("\nGenerate files? (y/n): ").lower() == 'y':
        # Process and write files
        result = processor.process()
        if result.success:
            processor.write()
            print(f"\nSuccessfully generated {result.files_processed} files")
        else:
            print(f"\nGeneration failed: {result.message}")
            for error in result.errors:
                print(f"Error: {error}")

def selective_generation():
    """Generate init files with specific settings."""
    # Preview changes first
    generate_init_files(
        "src",
        docstring="Project initialization.",
        collect_submodules=True,
        exclude_patterns={"tests", "docs"},
        print_output=True,
        print_only=True
    )

    # Generate if approved
    if input("\nGenerate files? (y/n): ").lower() == 'y':
        result = generate_init_files(
            "src",
            docstring="Project initialization.",
            collect_submodules=True,
            exclude_patterns={"tests", "docs"}
        )

        if result.success:
            print(f"\nGenerated {result.files_processed} init files")
        else:
            print(f"\nGeneration failed: {result.message}")

if __name__ == "__main__":
    print("Init Generator Examples")
    print("1. Basic Usage")
    print("2. Advanced Usage")
    print("3. Selective Generation")

    choice = input("\nSelect example (1-3): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        advanced_usage()
    elif choice == "3":
        selective_generation()
    else:
        print("Invalid choice")
