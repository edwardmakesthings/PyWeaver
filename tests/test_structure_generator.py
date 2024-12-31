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
import time
from datetime import datetime
import os
from typing import Generator, Any
import subprocess
import pytest

from examples.structure_generator_example import (
    document_project_structure,
)
from pyweaver.common.enums import ListingStyle
from pyweaver.common.errors import FileError, ProcessingError
from pyweaver.processors import generate_structure, StructurePrinter, SortOrder

def compare_structure_content(actual: str, expected: str) -> None:
    """Helper function to compare structure content.

    Args:
        actual: Actual structure content
        expected: Expected structure content
    """
    actual_lines = [line.rstrip() for line in actual.splitlines() if line.strip()]
    expected_lines = [line.rstrip() for line in expected.splitlines() if line.strip()]

    assert len(actual_lines) == len(expected_lines), \
        f"Line count mismatch. Expected {len(expected_lines)}, got {len(actual_lines)}"

    for i, (actual_line, expected_line) in enumerate(zip(actual_lines, expected_lines)):
        assert actual_line == expected_line, \
            f"Line {i + 1} mismatch:\nExpected: {expected_line}\nActual:   {actual_line}"

def example_structure(project_root: Path):
    """This function creates a sample project structure for testing.

    It is not intended to be run alone, but as a helper function for the tests.
    """
    # Create source structure
    src = project_root / "src"
    src.mkdir()

    # Create modules
    for module in ["core", "utils", "api"]:
        module_dir = src / module
        module_dir.mkdir()

        # Add Python files
        (module_dir / "__init__.py").touch()
        (module_dir / f"{module}.py").write_text(f"# {module} implementation", encoding="utf-8")
        (module_dir / f"{module}_utils.py").write_text("# Utility functions", encoding="utf-8")

        # Add tests
        test_dir = module_dir / "tests"
        test_dir.mkdir()
        (test_dir / f"test_{module}.py").write_text("# Test cases", encoding="utf-8")

    # Create documentation
    docs = project_root / "docs"
    docs.mkdir()
    (docs / "readme.md").write_text("# Project Documentation", encoding="utf-8")
    (docs / "api.md").write_text("# API Documentation", encoding="utf-8")

    # Create files that should be ignored
    (project_root / "__pycache__").mkdir()
    (project_root / "__pycache__/cache.pyc").touch()
    (project_root / ".git").mkdir()
    (project_root / ".git/config").touch()

@pytest.fixture
def example_project(tmp_path: Path) -> Path:
    """Create a sample project structure for testing."""
    try:
        project_root = tmp_path / "project"
        project_root.mkdir()

        # Create source structure
        src = project_root / "src"
        src.mkdir()

        # Create modules inside src
        for module in ["core", "utils", "api"]:
            module_dir = src / module
            module_dir.mkdir(parents=True)

            # Add Python files
            (module_dir / "__init__.py").write_text("")
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
        (project_root / "__pycache__" / "cache.pyc").touch()
        (project_root / ".git").mkdir()
        (project_root / ".git" / "config").touch()

        return project_root

    except Exception as e:
        pytest.fail(f"Failed to create example project: {e}")

@pytest.fixture
def readonly_dir(tmp_path: Path) -> Path:
    """Create a read-only directory for testing permissions."""
    test_dir = tmp_path / "readonly"
    test_dir.mkdir()

    # Add a test file
    test_file = test_dir / "test.txt"
    test_file.write_text("test content")

    return test_dir

@pytest.fixture
def example_project_permissions() -> Generator[Path, Any, None]:
    """Create a sample project structure for testing.

    This fixture creates a realistic project structure with various
    file types and nested directories to test structure generation.
    """
    with tempfile.TemporaryDirectory() as tmp:
        project_root = Path(tmp)
        example_structure(project_root)

        # Remove write permissions from this directory on Windows
        subprocess.run(["icacls", str(project_root), "/deny", "Everyone:(W)"], check=False)

        yield project_root

        # Restore permissions after the test
        subprocess.run(["icacls", str(project_root), "/remove:d", "Everyone"], check=False)
        subprocess.run(["icacls", str(project_root), "/grant", "Everyone:(F)"], check=False)

@pytest.fixture
def dated_files() -> Generator[Path, Any, None]:
    """Create files with different dates for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Create files with different dates
        for days in [0, 7, 30, 90]:
            file = root / f"file_{days}days.txt"
            file.write_text(f"Content for {days} days ago", encoding="utf-8")
            # Set access/modify times
            timestamp = time.time() - (days * 86400)
            os.utime(file, (timestamp, timestamp))

        yield root

def test_file_output(example_project, tmp_path):
    """Test structure output to file."""
    output_path = tmp_path / "structure.txt"

    printer = StructurePrinter(example_project)

    # Generate and write structure
    structure = printer.generate_structure()
    printer.write(output_path)

    # Verify file was written
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == structure

def test_file_output_errors(tmp_path: Path):
    """Test error handling for file output."""
    # Create test structure
    test_dir = tmp_path / "test"
    test_dir.mkdir()
    (test_dir / "test.txt").write_text("test")

    # Test non-existent output directory
    invalid_output = tmp_path / "nonexistent" / "output.txt"
    with pytest.raises(ProcessingError) as exc_info:
        generate_structure(test_dir, output_file=invalid_output)
    assert "Failed to write" in str(exc_info.value)

def test_document_project_structure(example_project, tmp_path):
    """Test project structure documentation."""

    # Generate tree view for src directory specifically
    tree = generate_structure(
        example_project / "src",
        style="tree",
        show_size=True,
        sort_type="alpha_dirs_first"
    )

    # Basic structure verification
    assert "src" in str(example_project / "src")  # Verify base path
    assert "core" in tree
    assert "utils" in tree
    assert "api" in tree
    assert ".py" in tree
    assert "B)" in tree  # Size indicator

    # Generate Markdown for documentation
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    structure_md = docs_dir / "structure.md"

    generate_structure(
        example_project,
        style="markdown",
        show_size=True,
        max_depth=3,
        output_file=structure_md
    )

    # Verify documentation was generated
    assert structure_md.exists()
    content = structure_md.read_text()
    assert "src" in content
    assert "docs" in content
    assert "Structure Statistics" in content

def test_analyze_project_organization(example_project):
    """Test project organization analysis."""
    # Get initial statistics
    printer = StructurePrinter(example_project)
    printer.generate_structure()  # Generate to populate statistics
    initial_stats = printer.get_statistics()

    # Add new files
    new_module = example_project / "src" / "new_module"
    new_module.mkdir(parents=True)
    (new_module / "new_file.py").write_text("# New content")

    # Re-analyze and check statistics
    printer = StructurePrinter(example_project)
    printer.generate_structure()
    new_stats = printer.get_statistics()

    assert new_stats["total_files"] == initial_stats["total_files"] + 1
    assert new_stats["total_dirs"] == initial_stats["total_dirs"] + 1

def test_generate_focused_views(example_project):
    """Test generation of focused structure views."""
    # Test source files view
    src_view = generate_structure(
        example_project,
        style="tree",
        include_patterns={"src/**/*.py"},
        ignore_patterns={"**/test_*.py", "**/__init__.py"}
    )

    # Basic assertions for src view
    assert src_view, "View should not be empty"
    assert "src" in src_view
    assert ".py" in src_view
    assert "__init__.py" not in src_view
    assert "test_" not in src_view

    # Test test files view
    test_view = generate_structure(
        example_project,
        style="tree",
        include_patterns={"**/tests/**/*.py", "**/*test*.py"}
    )

    # Basic assertions for test view
    assert test_view, "View should not be empty"
    assert "tests" in test_view
    assert "test_" in test_view
    assert not any(f in test_view for f in ["api.py", "core.py", "utils.py"])

def test_error_handling(tmp_path: Path):
    """Test error handling scenarios."""
    # Test with non-existent directory
    nonexistent = tmp_path / "nonexistent"
    with pytest.raises(ProcessingError) as exc_info:
        generate_structure(nonexistent)
    assert "does not exist" in str(exc_info.value)

    # Test with invalid patterns
    with pytest.raises(ProcessingError) as exc_info:
        generate_structure(
            tmp_path,
            include_patterns={"[invalid"}
        )
    assert "pattern" in str(exc_info.value).lower()

def test_special_cases(tmp_path: Path):
    """Test special cases and edge conditions."""
    # Test empty directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    structure = generate_structure(empty_dir)
    assert structure.strip(), "Structure should not be empty"
    assert "empty" in structure, "Directory name should be in structure"

    # Test single file case
    file_dir = tmp_path / "single"
    file_dir.mkdir()
    test_file = file_dir / "test.txt"
    test_file.write_text("test content")

    structure = generate_structure(file_dir)
    assert structure.strip(), "Structure should not be empty"
    assert "test.txt" in structure, "File should be in structure"

def test_convenience_function_output(example_project, tmp_path):
    """Test output handling in convenience function."""
    output_path = tmp_path / "structure.txt"

    # Test print-only mode
    structure = generate_structure(
        example_project,
        print_output=True,
        style="tree"
    )
    assert isinstance(structure, str)
    assert not output_path.exists()

    # Test file output
    structure = generate_structure(
        example_project,
        output_file=output_path,
        style="markdown"
    )
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == structure

    # Test both print and file output
    output_path.unlink()  # Clean up previous file
    structure = generate_structure(
        example_project,
        output_file=output_path,
        print_output=True,
        style="tree"
    )
    assert output_path.exists()
    assert output_path.read_text(encoding="utf-8") == structure

def test_listing_styles(example_project):
    """Test all available listing styles."""
    for style in ListingStyle:
        structure = generate_structure(
            example_project,
            style=style.value
        )

        if style == ListingStyle.TREE:
            assert "├──" in structure or "└──" in structure
        elif style == ListingStyle.FLAT:
            assert "/" in structure
            assert "├──" not in structure
        elif style == ListingStyle.INDENTED:
            assert "    " in structure
        elif style == ListingStyle.MARKDOWN:
            assert "-" in structure

def test_sort_orders(example_project):
    """Test different sort ordering options."""
    for sort_type in SortOrder:
        structure = generate_structure(
            example_project,
            sort_type=sort_type.value
        )

        lines = structure.splitlines()

        if sort_type == SortOrder.ALPHA:
            # Names should be alphabetically sorted ignoring tree characters
            names = [line.split('──')[-1].strip() for line in lines if '──' in line]
            sorted_names = sorted(names)
            assert names == sorted_names

        elif sort_type == SortOrder.ALPHA_DIRS_FIRST:
            # Directories should come before files
            content = []
            for line in lines:
                if '──' in line:
                    name = line.split('──')[-1].strip()
                    is_dir = not ('.' in name)  # Simple check for directories
                    content.append((is_dir, name))

            # Check that directories come first
            is_dir_list = [x[0] for x in content]
            assert all(is_dir_list[i] >= is_dir_list[i+1] for i in range(len(is_dir_list)-1))

def test_date_display(dated_files: Path):
    """Test date display functionality."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Test default format
    structure = generate_structure(
        dated_files,
        show_date=True,
        date_format="%Y-%m-%d"
    )
    assert today in structure

    # Test custom format
    custom_format = "%d/%m/%y"
    structure = generate_structure(
        dated_files,
        show_date=True,
        date_format=custom_format
    )
    formatted_date = datetime.now().strftime(custom_format)
    assert formatted_date in structure

def test_size_formatting(example_project):
    """Test different size format options."""
    # Test bytes format
    structure = generate_structure(
        example_project,
        show_size=True,
        size_format="bytes"
    )
    assert "B" in structure

    # Test automatic scaling
    structure = generate_structure(
        example_project,
        show_size=True,
        size_format="auto"
    )
    for unit in ["B", "KB", "MB"]:
        if unit in structure:
            break
    else:
        pytest.fail("No size unit found in output")

def test_name_length_limits(example_project):
    """Test name length limiting functionality."""
    long_name = "a" * 100
    test_file = example_project / f"{long_name}.txt"
    test_file.touch()

    structure = generate_structure(
        example_project,
        max_name_length=20
    )
    assert "..." in structure
    assert long_name not in structure


if __name__ == "__main__":
    pytest.main([__file__])