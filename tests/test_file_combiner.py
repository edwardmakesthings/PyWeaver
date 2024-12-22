"""Test suite for file combiner.

Provides comprehensive testing of the file combiner functionality
including different handling modes and pattern matching.

Path: tests/test_file_combiner.py
"""

import pytest
from pathlib import Path
import tempfile
import textwrap
from typing import Generator, Any

from tools.project_tools.file_combiner import (
    create_combiner,
    quick_combine,
    FileHandlingMode,
    CombinerConfig
)

@pytest.fixture
def test_files() -> Generator[Path, Any, None]:
    """Create temporary test files with different content types."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create Python file with comments and docstrings
        py_file = tmp_path / "example.py"
        py_file.write_text(textwrap.dedent('''
            """Module docstring."""

            # This is a comment
            class Example:
                """Class docstring."""
                def __init__(self):
                    # Initialize
                    pass

            def function():
                """Function docstring."""
                # Function comment
                return True
        '''))

        # Create TypeScript file
        ts_file = tmp_path / "component.ts"
        ts_file.write_text(textwrap.dedent('''
            /**
             * Component documentation
             */

            // Import statement
            import { Something } from 'somewhere';

            /* Multi-line
               comment */
            export class Component {
                // Property
                private value: string;

                constructor() {
                    // Initialize
                    this.value = '';
                }
            }
        '''))

        # Create CSS file
        css_file = tmp_path / "styles.css"
        css_file.write_text(textwrap.dedent('''
            /* Header styles */
            .header {
                color: blue;
            }

            /* Main content */
            .content {
                /* Nested comment */
                padding: 20px;
            }
        '''))

        yield tmp_path

def test_basic_combining(test_files: Path):
    """Test basic file combining functionality."""
    output_file = test_files / "combined.txt"

    result = quick_combine(
        input_dir=test_files,
        output_file=output_file
    )

    assert result.success
    assert result.files_processed > 0
    assert output_file.exists()

    # Check content
    content = output_file.read_text()
    assert "Module docstring" in content
    assert "Component documentation" in content
    assert "Header styles" in content

def test_file_handling_modes(test_files: Path):
    """Test different file handling modes."""
    results = {}

    for mode in FileHandlingMode:
        output_file = test_files / f"combined_{mode.value}.txt"

        combiner = create_combiner(
            root_dir=test_files,
            patterns=["*.py"],  # Test with Python files only
            output_file=output_file,
            mode=mode
        )

        result = combiner.combine()
        assert result.success

        content = output_file.read_text()
        results[mode] = content

    # Check FULL mode
    assert "# This is a comment" in results[FileHandlingMode.FULL]
    assert '"""Module docstring."""' in results[FileHandlingMode.FULL]

    # Check NO_COMMENTS mode
    assert "# This is a comment" not in results[FileHandlingMode.NO_COMMENTS]
    assert '"""Module docstring."""' in results[FileHandlingMode.NO_COMMENTS]

    # Check NO_DOCSTRINGS mode
    assert "# This is a comment" in results[FileHandlingMode.NO_DOCSTRINGS]
    assert '"""Module docstring."""' not in results[FileHandlingMode.NO_DOCSTRINGS]

    # Check MINIMAL mode
    assert "# This is a comment" not in results[FileHandlingMode.MINIMAL]
    assert '"""Module docstring."""' not in results[FileHandlingMode.MINIMAL]

def test_pattern_matching(test_files: Path):
    """Test pattern-based file selection."""
    output_file = test_files / "combined.txt"

    # Test Python files only
    py_combiner = create_combiner(
        root_dir=test_files,
        patterns=["*.py"],
        output_file=output_file
    )

    py_result = py_combiner.combine()
    assert py_result.success
    content = output_file.read_text()
    assert "class Example" in content
    assert "export class Component" not in content

    # Test TypeScript files only
    ts_combiner = create_generator(
        root_dir=test_files,
        patterns=["*.ts"],
        output_file=output_file
    )

    ts_result = ts_combiner.combine()
    assert ts_result.success
    content = output_file.read_text()
    assert "export class Component" in content
    assert "class Example" not in content

def test_exclude_patterns(test_files: Path):
    """Test pattern-based exclusion."""
    # Create a file that should be excluded
    test_dir = test_files / "test_dir"
    test_dir.mkdir()
    test_file = test_dir / "test.py"
    test_file.write_text("# Test file\n")

    output_file = test_files / "combined.txt"

    combiner = create_combiner(
        root_dir=test_files,
        patterns=["*.py"],
        output_file=output_file,
        exclude_patterns={"test_dir/*"}
    )

    result = combiner.combine()
    assert result.success

    content = output_file.read_text()
    assert "# Test file" not in content
    assert "class Example" in content

def test_tree_generation(test_files: Path):
    """Test tree structure generation."""
    output_file = test_files / "combined.txt"

    combiner = create_combiner(
        root_dir=test_files,
        patterns=["*.*"],
        output_file=output_file,
        generate_tree=True
    )

    result = combiner.combine()
    assert result.success

    # Check tree file
    tree_file = output_file.with_suffix('.tree.txt')
    assert tree_file.exists()

    tree_content = tree_file.read_text()
    assert "example.py" in tree_content
    assert "component.ts" in tree_content
    assert "styles.css" in tree_content

def test_preview_functionality(test_files: Path):
    """Test preview generation."""
    combiner = create_combiner(
        root_dir=test_files,
        patterns=["*.py"],
        output_file=test_files / "combined.txt"
    )

    preview = combiner.preview()
    assert isinstance(preview, str)
    assert "class Example" in preview

    # Preview shouldn't create files
    assert not (test_files / "combined.txt").exists()

def test_error_handling():
    """Test error handling for invalid inputs."""
    # Test with non-existent directory
    with pytest.raises(Exception):
        combiner = create_combiner(
            root_dir=Path("non_existent_dir"),
            patterns=["*.py"],
            output_file=Path("output.txt")
        )
        combiner.combine()

    # Test with invalid pattern
    with pytest.raises(Exception):
        combiner = create_combiner(
            root_dir=Path.cwd(),
            patterns=["[invalid pattern"],
            output_file=Path("output.txt")
        )
        combiner.combine()

if __name__ == "__main__":
    pytest.main([__file__])
