"""Generate the code reference pages and navigation.

This script scans the PyWeaver package to generate API reference documentation.
It creates a documentation file for each Python module and builds a navigation
structure for MkDocs to use.
"""

from pathlib import Path
import mkdocs_gen_files
import sys

# Add the package root to Python path
package_root = Path(__file__).parent.parent  # Points to the PyWeaver root
sys.path.insert(0, str(package_root))

nav = mkdocs_gen_files.Nav()

# Define PyWeaver's main modules
MODULE_PATHS = [
    "processors",
    "common",
    "config",
    "utils"
]

for module in MODULE_PATHS:
    module_path = Path(module)

    # Skip if module directory doesn't exist
    if not (package_root / "pyweaver" / module_path).exists():
        continue

    # Look for Python files in the module
    for path in sorted((package_root / "pyweaver" / module_path).rglob("*.py")):
        # Get the path relative to the package root
        rel_path = path.relative_to(package_root)
        doc_path = rel_path.with_suffix(".md")
        full_doc_path = Path("reference", doc_path)

        # Split the path into parts for navigation
        parts = tuple(rel_path.parts)

        # Handle special cases
        if parts[-1] == "__init__":
            # Convert __init__.py to index.md for nicer URLs
            parts = parts[:-1]
            doc_path = doc_path.with_name("index.md")
            full_doc_path = full_doc_path.with_name("index.md")
        elif parts[-1] == "__main__":
            # Skip __main__.py files
            continue

        # Skip private modules (starting with _)
        if any(part.startswith("_") for part in parts):
            continue

        # Add to navigation
        nav[parts] = doc_path.as_posix()

        # Create the documentation file
        with mkdocs_gen_files.open(full_doc_path, "w") as fd:
            # Create module path without .py extension
            module_path = rel_path.relative_to("pyweaver").with_suffix("")
            # Convert path separators to dots for Python import
            module_name = "pyweaver."+str(module_path).replace('/', '.').replace('\\', '.')

            # Write the documentation
            fd.write(f"# {parts[-1]}\n\n")
            fd.write(f"::: {module_name}")

        # Set up edit path for GitHub integration
        mkdocs_gen_files.set_edit_path(full_doc_path, path)

# Generate the navigation file
with mkdocs_gen_files.open("reference/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())