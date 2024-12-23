"""Example usage of the init generator.

This example demonstrates different approaches to generating __init__.py files:
1. Basic generator: For simple package structures
2. Config-based generator: For complex projects with standardized init files

The config-based approach is particularly useful for:
- Large projects with many packages
- Standardized docstring formats
- Consistent export organization
- Multiple package structures

Path: examples/init_generator_example.py
"""

import json
from pathlib import Path
from pyweaver.init_generator import (
    create_generator,
    create_config_generator,
    ExportCollectionMode,
    InitGeneratorConfig
)
from pyweaver.common.type_definitions import GeneratorMode

def basic_usage():
    """Simple init file generation without configuration.

    Best for:
    - Single packages
    - Simple export requirements
    - Basic docstring needs
    """
    generator = create_generator(
        root_dir=Path("my_package"),
        mode=GeneratorMode.PREVIEW,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    # Generate with preview mode first
    changes = generator.preview()
    print("\nPreview of changes:")
    for path, content in changes.items():
        print(f"\n--- {path} ---")
        print(content)
        print("-" * 40)

    # If changes look good, switch to write mode
    generator_write = create_generator(
        root_dir=Path("my_package"),
        mode=GeneratorMode.WRITE,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    # Generate the files
    result = generator_write.write()
    if result.success:
        print(f"Successfully wrote {result.files_written} files")
    else:
        print(f"Errors during generation: {result.errors}")

def config_based_single_package():
    """Generate init files for a single package using configuration.

    Best for:
    - Complex package structures
    - Custom docstring templates
    - Organized exports by type
    """
    generator = create_config_generator(
        config_path=Path("init_config.json"),
        root_dir=Path("my_project"),
        mode=GeneratorMode.PREVIEW
    )

    # Process specific package
    result = generator.process_package("my_package.core")

    if result.success:
        print(f"Processed package successfully")
        print(f"Files that would be written: {result.files_processed}")
    else:
        print("Errors:", result.errors)

def config_based_full_project():
    """Generate init files for entire project using configuration.

    Best for:
    - Multi-package projects
    - Standardized init files
    - Consistent export organization
    """
    # First validate the configuration
    generator = create_config_generator(
        config_path=Path("init_config.json"),
        root_dir=Path("my_project"),
        mode=GeneratorMode.PREVIEW
    )

    validation = generator.validate()
    if not validation.is_valid:
        print("Configuration errors:", validation.errors)
        return

    # Preview changes first
    results = generator.process_all()

    print("\nPreview Results:")
    for package, result in results.items():
        print(f"\n{package}:")
        print(f"Files processed: {result.files_processed}")
        if not result.success:
            print("Errors:", result.errors)

    # If preview looks good, generate with write mode
    if input("\nGenerate files? (y/n): ").lower() == 'y':
        generator = create_config_generator(
            config_path=Path("init_config.json"),
            root_dir=Path("my_project"),
            mode=GeneratorMode.WRITE
        )
        results = generator.process_all()

        print("\nGeneration Results:")
        for package, result in results.items():
            status = "Success" if result.success else "Failed"
            print(f"{package}: {status} ({result.files_written} files written)")

def example_config():
    """Creates an example init_config.json file."""
    config = {
        "global": {
            "order_policy": "dependency_first",
            "docstring": "Auto-generated __init__.py file.",
            "exports_blacklist": ["internal_*", "test_*", "_*"],
            "excluded_paths": [
                "**/.git",
                "**/__pycache__",
                "**/tests"
            ],
            "collect_from_submodules": True,
            "sections": {
                "classes": {
                    "enabled": True,
                    "order": 0,
                    "header_comment": "# Classes",
                },
                "functions": {
                    "enabled": True,
                    "order": 1,
                    "header_comment": "# Functions",
                }
            }
        },
        "paths": {
            "my_package.core": {
                "docstring": "Core functionality for my_package.\n\nProvides essential features and base classes.",
                "inline_content": {
                    "version": {
                        "code": "__version__ = '0.1.0'",
                        "order": 999,
                        "section": "constants"
                    }
                }
            }
        }
    }

    with open("init_config_example.json", "w") as f:
        json.dump(config, f, indent=2)
    print("Created example config file: init_config_example.json")

if __name__ == "__main__":
    print("Init Generator Examples")
    print("1. Basic Usage")
    print("2. Config-Based (Single Package)")
    print("3. Config-Based (Full Project)")
    print("4. Create Example Config")

    choice = input("\nSelect example (1-4): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        config_based_single_package()
    elif choice == "3":
        config_based_full_project()
    elif choice == "4":
        example_config()
    else:
        print("Invalid choice")