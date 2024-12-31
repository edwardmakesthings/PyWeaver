"""Example usage of the structure generator.

This module demonstrates practical use cases for generating directory structure
visualizations. The structure generator can be used both through its simple
convenience function and its more powerful processor class, each suited for
different needs.

Common use cases:
- Project Documentation: Create visual directory trees for documentation
- Code Reviews: Generate structural overviews for review purposes
- Project Analysis: Analyze and verify project organization
- Documentation Generation: Create structure documentation automatically

The examples show both basic usage for quick results and advanced usage for
more complex requirements.

Path: examples/structure_example.py
"""

from pathlib import Path
from datetime import datetime
from pyweaver.common.enums import ListingStyle
from pyweaver.processors import (
    generate_structure,
    StructurePrinter,
    StructureOptions,
    SortOrder
)

def document_project_structure():
    """Generate project structure documentation.

    This example shows how to create documentation-ready structure diagrams,
    including both a tree view for visual output and Markdown format for
    documentation files.
    """
    # Generate tree view for console display
    structure = generate_structure(
        "src",
        style="tree",
        show_size=True,
        sort_type="alpha_dirs_first",
        ignore_patterns={"**/__pycache__", "**/*.pyc", "**/.git"},
        print_output=True  # Print to console
    )

    # Generate Markdown for documentation
    generate_structure(
        "src",
        style="markdown",
        show_size=True,
        max_depth=3,  # Limit depth for readability
        output_file="docs/structure.md"  # Write to file
    )

    print("\nGenerated Markdown documentation in docs/structure.md")

def analyze_project_organization():
    """Analyze project organization using the StructurePrinter.

    This example shows how to use the StructurePrinter class for more
    detailed analysis of project structure, including gathering statistics
    and filtering specific patterns.
    """
    # Create printer with custom options
    options = StructureOptions(
        style=ListingStyle.TREE,
        sort_order=SortOrder.ALPHA_DIRS_FIRST,
        show_size=True,
        show_date=True,
        max_depth=None,  # Show full depth
        ignore_patterns={
            "**/__pycache__",
            "**/*.pyc",
            "**/.git",
            "**/node_modules",
            "**/.venv"
        }
    )

    printer = StructurePrinter(".", options)

    # Generate and print structure
    structure = printer.generate_structure()
    print("\nFull Project Structure:")
    print("-" * 80)
    print(structure)
    print("-" * 80)

    # Write full analysis to file
    printer.write("docs/project_analysis.txt")

    # Get and display statistics
    stats = printer.get_statistics()
    print("\nProject Statistics:")
    print(f"Total Files: {stats['total_files']}")
    print(f"Total Directories: {stats['total_dirs']}")
    print(f"Total Size: {stats['total_size']:,} bytes")
    print(f"Processing Time: {stats['processing_time']:.2f} seconds")

    # Check for any errors
    errors = printer.get_errors()
    if errors:
        print("\nWarnings/Errors encountered:")
        for error in errors:
            print(f"- {error}")

def generate_focused_views():
    """Generate focused views of specific project areas.

    This example shows how to generate structure views focused on specific
    parts of the project using include/exclude patterns.
    """
    # View source files only
    generate_structure(
        ".",
        style="tree",
        include_patterns={"**/src/**/*.py", "**/src/**/*.tsx"},
        ignore_patterns={"**/*test*", "**/__init__.py"},
        show_size=True,
        max_depth=4,
        output_file="docs/source_structure.txt",
        print_output=True  # Show while generating
    )

    # View test files only
    generate_structure(
        ".",
        style="tree",
        include_patterns={"**/tests/**/*.py", "**/*test*.py"},
        show_size=True,
        sort_type="alpha",
        output_file="docs/test_structure.txt",
        print_output=True
    )

    # View documentation files
    generate_structure(
        ".",
        style="markdown",
        include_patterns={"**/*.md", "**/docs/**/*"},
        show_date=True,  # Show last modified dates
        output_file="docs/documentation_structure.md",
        print_output=True
    )

if __name__ == "__main__":
    print("Structure Generator Examples")
    print("1. Document Project Structure")
    print("2. Analyze Project Organization")
    print("3. Generate Focused Views")

    choice = input("\nSelect example (1-3): ")

    if choice == "1":
        document_project_structure()
    elif choice == "2":
        analyze_project_organization()
    elif choice == "3":
        generate_focused_views()
    else:
        print("Invalid choice")
