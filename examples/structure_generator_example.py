"""Example usage of the structure generator.

This example demonstrates various ways to use the structure generator,
from simple one-shot generation to more complex configurations.

Path: examples/structure_generator_example.py
"""

from pathlib import Path
from tools.project_tools.structure_gen import (
    create_generator,
    quick_generate,
    OutputFormat,
    StructureConfig
)

def basic_usage():
    """Simple usage with quick_generate."""
    # Generate structure for current directory
    output_file = quick_generate(Path.cwd())
    print(f"Generated structure at: {output_file}")

def advanced_usage():
    """More complex usage with custom configuration."""
    # Create generator with custom config
    generator = create_generator(
        root_dir=Path("my_project"),
        output_file=Path("docs/structure.md"),
        format=OutputFormat.MARKDOWN,
        show_size=True,
        max_depth=3,
        exclude_patterns={
            "**/__pycache__/*",
            "**/.git/*",
            "**/node_modules/*",
            "**/*.pyc"
        }
    )

    # Preview structure first
    preview = generator.preview()
    print("Structure Preview:")
    print(preview)
    print("\nGenerate? (y/n)")

    if input().lower() == 'y':
        result = generator.generate()
        if result.success:
            print(f"Structure generated: {result.message}")
            print(f"Files processed: {result.files_processed}")
        else:
            print(f"Generation failed: {result.message}")
            for error in result.errors:
                print(f"Error: {error}")

def multiple_formats():
    """Generate structure in different formats."""
    root_dir = Path("my_project")

    # Common configuration
    config_base = {
        "root_dir": root_dir,
        "show_size": True,
        "exclude_patterns": {"**/__pycache__/*", "**/.git/*"}
    }

    # Generate in each format
    for format in OutputFormat:
        output_file = root_dir / f"structure.{format.value}"
        generator = create_generator(
            output_file=output_file,
            format=format,
            **config_base
        )

        result = generator.generate()
        print(f"{format.value}: {'Success' if result.success else 'Failed'}")

if __name__ == "__main__":
    print("1. Basic Usage")
    print("2. Advanced Usage")
    print("3. Multiple Formats")
    choice = input("Select example to run (1-3): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        advanced_usage()
    elif choice == "3":
        multiple_formats()
    else:
        print("Invalid choice")
