"""Example usage of the init file generator.

Demonstrates various ways to use the init file generator, from simple
generation to advanced configuration using init_config.json.

Path: examples/init_generator_example.py
"""

import json
from pathlib import Path
from tools.project_tools.init_generator import (
    create_generator,
    preview_generator,
    ExportCollectionMode,
    InitGeneratorConfig
)

def load_config(config_path: Path) -> dict:
    """Load and parse init_config.json."""
    with open(config_path, 'r') as f:
        return json.load(f)

def basic_usage():
    """Simple init file generation."""
    generator = create_generator(
        root_dir=Path("my_package"),
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    # Preview changes first
    changes = generator.preview()
    print("\nPreview of changes:")
    for path, content in changes.items():
        print(f"\n--- {path} ---")
        print(content)
        print("-" * 40)

    # Generate if changes look good
    if input("\nGenerate files? (y/n): ").lower() == 'y':
        result = generator.write()
        if result.success:
            print(f"Successfully wrote {result.files_written} files")
        else:
            print(f"Errors during generation: {result.errors}")

def advanced_usage_with_config():
    """Advanced usage using init_config.json."""
    config_file = Path("init_config.json")
    config_data = load_config(config_file)

    # Get global settings
    global_config = config_data["global"]

    # Example for generating inits for the omniui package
    package_path = Path("omniui")

    # Merge global and package-specific settings
    settings = global_config.copy()
    if str(package_path) in config_data["paths"]:
        settings.update(config_data["paths"][str(package_path)])

    # Create generator with config
    generator = create_generator(
        root_dir=package_path,
        export_mode=ExportCollectionMode.ALL_PUBLIC,
        exclude_patterns=set(settings.get("excluded_paths", [])),
        docstring_template=settings.get("docstring"),
    )

    # Preview changes
    print(f"\nPreviewing changes for {package_path}")
    changes = generator.preview()

    for path, content in changes.items():
        print(f"\nWould write to {path}:")
        print("-" * 40)
        print(content)
        print("-" * 40)

    # Generate if approved
    if input("\nGenerate files? (y/n): ").lower() == 'y':
        result = generator.write()
        print(f"Generated {result.files_written} files")
        if result.errors:
            print("Errors:", result.errors)

def generate_all_packages():
    """Generate init files for all configured packages."""
    config_data = load_config(Path("init_config.json"))

    for path_str, path_config in config_data["paths"].items():
        path = Path(path_str)
        if not path.exists():
            print(f"Skipping {path} - directory doesn't exist")
            continue

        print(f"\nProcessing {path}")

        # Merge global and path-specific config
        settings = config_data["global"].copy()
        settings.update(path_config)

        generator = create_generator(
            root_dir=path,
            export_mode=ExportCollectionMode.ALL_PUBLIC,
            exclude_patterns=set(settings.get("excluded_paths", [])),
            docstring_template=settings.get("docstring"),
        )

        # Generate without preview for batch operation
        result = generator.write()
        print(f"Generated {result.files_written} files")
        if result.errors:
            print("Errors:", result.errors)

if __name__ == "__main__":
    print("Init Generator Examples")
    print("1. Basic Usage")
    print("2. Advanced Usage with Config")
    print("3. Generate All Packages")

    choice = input("\nSelect example (1-3): ")

    if choice == "1":
        basic_usage()
    elif choice == "2":
        advanced_usage_with_config()
    elif choice == "3":
        generate_all_packages()
    else:
        print("Invalid choice")
