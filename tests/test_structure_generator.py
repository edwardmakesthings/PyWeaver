"""Test suite for structure generator examples.

This module provides comprehensive testing for the structure generator example
functionality. It verifies that all example use cases work correctly and
produce the expected results.

The tests cover:
- Documentation generation
- Project analysis
- Focused views
- Pattern filtering
- Statistics gathering
- Error handling

Path: tests/test_structure_examples.py
"""

from pathlib import Path
import tempfile
from typing import Generator, Any
import pytest

from examples.structure_generator_example import (
    document_project_structure,
)
from pyweaver.processors import generate_structure, StructurePrinter

@pytest.fixture
def example_project() -> Generator[Path, Any, None]:
    """Create a sample project structure for testing.

    This fixture creates a realistic project structure with various
    file types and nested directories to test structure generation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)

        # Create source structure
        src = project_root / "src"
        src.mkdir()

        # Create modules
        for module in ["core", "utils", "api"]:
            module_dir = src / module
            module_dir.mkdir()

            # Add Python files
            (module_dir / "__init__.py").touch()
            (module_dir / f"{module}.py").write_text(f"# {module} implementation")
            (module_dir / f"{module}_utils.py").write_text("# Utility functions")

            # Add tests
            test_dir = module_dir / "tests"
            test_dir.mkdir()
            (test_dir / f"test_{module}.py").write_text("# Test cases")

        # Create documentation
        docs = project_root / "docs"
        docs.mkdir()
        (docs / "readme.md").write_text("# Project Documentation")
        (docs / "api.md").write_text("# API Documentation")

        # Create files that should be ignored
        (project_root / "__pycache__").mkdir()
        (project_root / "__pycache__/cache.pyc").touch()
        (project_root / ".git").mkdir()
        (project_root / ".git/config").touch()

        yield project_root

def test_document_project_structure(example_project, monkeypatch):
    """Test project structure documentation generation."""
    # Mock current directory
    monkeypatch.chdir(example_project)

    # Generate tree structure
    tree = generate_structure(
        "src",
        style="tree",
        show_size=True,
        sort_type="alpha_dirs_first"
    )

    # Verify tree structure content
    assert "src" in tree
    assert "core" in tree
    assert "utils" in tree
    assert "api" in tree
    assert ".py" in tree
    assert "B" in tree  # Size indicator

    # Verify Markdown generation
    docs_dir = example_project / "docs"
    structure_md = docs_dir / "structure.md"

    document_project_structure()
    assert structure_md.exists()

    content = structure_md.read_text()
    assert "# Project Structure" in content
    assert "Generated on:" in content
    assert "Directory Tree" in content
    assert "src" in content
    assert "Structure Statistics" in content

def test_analyze_project_organization(example_project, monkeypatch):
    """Test project organization analysis."""
    monkeypatch.chdir(example_project)

    # Capture statistics before changes
    options = StructurePrinter(example_project).get_statistics()
    initial_files = options["total_files"]
    initial_dirs = options["total_dirs"]

    # Add some files to test change detection
    new_module = example_project / "src/new_module"
    new_module.mkdir()
    (new_module / "new_file.py").write_text("# New content")

    # Re-analyze project
    options = StructurePrinter(example_project).get_statistics()
    assert options["total_files"] == initial_files + 1
    assert options["total_dirs"] == initial_dirs + 1
    assert options["total_size"] > 0
    assert options["processing_time"] >= 0

def test_generate_focused_views(example_project, monkeypatch):
    """Test generation of focused structure views."""
    monkeypatch.chdir(example_project)

    # Test source files view
    src_view = generate_structure(
        ".",
        style="tree",
        include_patterns={"**/src/**/*.py"},
        ignore_patterns={"**/*test*", "**/__init__.py"}
    )
    assert "src" in src_view
    assert "core.py" in src_view
    assert "utils.py" in src_view
    assert "api.py" in src_view
    assert "__init__.py" not in src_view
    assert "test_" not in src_view

    # Test test files view
    test_view = generate_structure(
        ".",
        style="tree",
        include_patterns={"**/tests/**/*.py", "**/*test*.py"}
    )
    assert "tests" in test_view
    assert "test_core.py" in test_view
    assert "test_utils.py" in test_view
    assert "core.py" not in test_view

    # Test documentation view
    docs_view = generate_structure(
        ".",
        style="markdown",
        include_patterns={"**/*.md", "**/docs/**/*"}
    )
    assert "docs" in docs_view
    assert "readme.md" in docs_view
    assert "api.md" in docs_view
    assert ".py" not in docs_view

def test_error_handling(example_project):
    """Test error handling in structure generation."""
    # Test invalid directory
    with pytest.raises(Exception):
        generate_structure(example_project / "nonexistent")

    # Test invalid patterns
    with pytest.raises(Exception):
        generate_structure(
            example_project,
            include_patterns={"[invalid"}
        )

    # Test excessive depth
    deep_structure = example_project / "deep"
    current = deep_structure
    for i in range(100):  # Create very deep structure
        current.mkdir(parents=True)
        current = current / str(i)

    # Should handle deep structure gracefully
    structure = generate_structure(deep_structure)
    assert structure  # Should return something
    assert "Maximum depth exceeded" not in structure

def test_special_cases(example_project):
    """Test special cases and edge conditions."""
    # Test empty directory
    empty_dir = example_project / "empty"
    empty_dir.mkdir()

    structure = generate_structure(empty_dir)
    assert structure
    assert "empty" in structure

    # Test single file
    single_file = example_project / "single.txt"
    single_file.write_text("content")

    structure = generate_structure(single_file.parent)
    assert structure
    assert "single.txt" in structure

    # Test with all files filtered out
    structure = generate_structure(
        example_project,
        include_patterns={"**/*.nonexistent"}
    )
    assert structure
    assert "No matching files" in structure

if __name__ == "__main__":
    pytest.main([__file__])