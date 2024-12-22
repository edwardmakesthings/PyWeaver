"""Test suite for structure generator.

Provides comprehensive testing of the structure generator functionality
including unit tests and integration tests.

Path: tests/test_structure_generator.py
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from typing import Generator, Any

from tools.project_tools.structure_gen import (
    create_generator,
    OutputFormat,
    StructureConfig
)

@pytest.fixture
def temp_dir() -> Generator[Path, Any, None]:
    """Create a temporary directory with test files."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create test directory structure
        (tmp_path / "src").mkdir()
        (tmp_path / "src/module1").mkdir()
        (tmp_path / "src/module2").mkdir()
        (tmp_path / "tests").mkdir()

        # Create some files
        (tmp_path / "src/module1/file1.py").touch()
        (tmp_path / "src/module2/file2.py").touch()
        (tmp_path / "tests/test_file.py").touch()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__/cache.pyc").touch()

        yield tmp_path

def test_basic_generation(temp_dir: Path):
    """Test basic structure generation."""
    output_file = temp_dir / "structure.txt"

    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file
    )

    result = generator.generate()
    assert result.success
    assert result.files_processed > 0
    assert output_file.exists()

    # Check content
    content = output_file.read_text()
    assert "src" in content
    assert "module1" in content
    assert "module2" in content
    assert "tests" in content

def test_format_outputs(temp_dir: Path):
    """Test different output formats."""
    for format in OutputFormat:
        output_file = temp_dir / f"structure.{format.value}"

        generator = create_generator(
            root_dir=temp_dir,
            output_file=output_file,
            format=format
        )

        result = generator.generate()
        assert result.success
        assert output_file.exists()

        content = output_file.read_text()
        if format == OutputFormat.MARKDOWN:
            assert "📁" in content  # Check for directory emoji
        elif format == OutputFormat.TREE:
            assert "└──" in content  # Check for tree connector

def test_exclusion_patterns(temp_dir: Path):
    """Test pattern-based exclusions."""
    output_file = temp_dir / "structure.txt"

    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file,
        exclude_patterns={"**/__pycache__/*", "**/*.pyc"}
    )

    result = generator.generate()
    assert result.success

    content = output_file.read_text()
    assert "__pycache__" not in content
    assert "cache.pyc" not in content
    assert "file1.py" in content  # Regular files should be included

def test_max_depth(temp_dir: Path):
    """Test max depth limitation."""
    output_file = temp_dir / "structure.txt"

    # Test with depth 1 (should only show top-level)
    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file,
        max_depth=1
    )

    result = generator.generate()
    assert result.success

    content = output_file.read_text()
    assert "src" in content
    assert "module1" not in content  # Too deep
    assert "file1.py" not in content  # Too deep

def test_show_file_sizes(temp_dir: Path):
    """Test file size display."""
    # Create a file with known content
    test_file = temp_dir / "test_file.txt"
    test_file.write_text("test content")

    output_file = temp_dir / "structure.txt"
    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file,
        show_size=True
    )

    result = generator.generate()
    assert result.success

    content = output_file.read_text()
    # File size should be shown in the output
    assert "test_file.txt" in content
    assert "12 B" in content  # Size of "test content"

def test_empty_directory_handling(temp_dir: Path):
    """Test handling of empty directories."""
    # Create an empty directory
    empty_dir = temp_dir / "empty_dir"
    empty_dir.mkdir()

    output_file = temp_dir / "structure.txt"

    # Test with empty dirs excluded
    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file,
        include_empty=False
    )

    result = generator.generate()
    assert result.success
    content = output_file.read_text()
    assert "empty_dir" not in content

    # Test with empty dirs included
    generator = create_generator(
        root_dir=temp_dir,
        output_file=output_file,
        include_empty=True
    )

    result = generator.generate()
    assert result.success
    content = output_file.read_text()
    assert "empty_dir" in content

def test_error_handling():
    """Test error handling for invalid inputs."""
    # Test with non-existent directory
    with pytest.raises(FileNotFoundError):
        generator = create_generator(
            root_dir=Path("non_existent_dir"),
            output_file=Path("structure.txt")
        )
        generator.generate()

    # Test with invalid max_depth
    with pytest.raises(ValueError):
        generator = create_generator(
            root_dir=Path.cwd(),
            output_file=Path("structure.txt"),
            max_depth=-1
        )
        generator.generate()

def test_preview_functionality(temp_dir: Path):
    """Test preview generation."""
    generator = create_generator(
        root_dir=temp_dir,
        output_file=temp_dir / "structure.txt"
    )

    # Preview shouldn't create the file
    preview = generator.preview()
    assert isinstance(preview, str)
    assert "src" in preview
    assert not (temp_dir / "structure.txt").exists()

if __name__ == "__main__":
    pytest.main([__file__])
