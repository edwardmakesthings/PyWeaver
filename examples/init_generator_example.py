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
from pyweaver.config import ImportOrderPolicy


def basic_usage():
    """Simple init file generation."""
    result = generate_init_files(
        "src",
        docstring="Package initialization.",
        collect_submodules=True
    )

    print("\nGenerated init files:")
    for path, status in result.items():
        print(f"{path}: {status}")

def advanced_usage():
    """Advanced usage with custom configuration."""
    # Create processor with specific settings
    processor = InitFileProcessor(
        root_dir="src",
        config_path="init_config.json",
        dry_run=True  # Preview mode
    )

    # Preview changes first
    changes = processor.preview()

    print("\nPreview of changes:")
    for path, content in changes.items():
        print(f"\n--- {path} ---")
        print(content)
        print("-" * 40)

    # Generate if approved
    if input("\nGenerate files? (y/n): ").lower() == 'y':
        # Switch to write mode
        processor.dry_run = False
        result = processor.process()

        if result.success:
            print(f"Successfully generated {result.files_processed} files")
        else:
            print(f"Generation failed: {result.message}")
            for error in result.errors:
                print(f"Error: {error}")

def selective_generation():
    """Generate init files with specific settings."""
    result = generate_init_files(
        "src",
        docstring="Project initialization.",
        collect_submodules=True,
        exclude_patterns={"tests", "docs"},
        order_policy=ImportOrderPolicy.DEPENDENCY_FIRST,
        generate_tree=True,
        include_submodules=["core", "utils"]
    )

    for path, status in result.items():
        print(f"{path}: {status}")

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
