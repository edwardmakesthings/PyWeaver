"""Additional test suite for structure generator advanced features.

This module provides testing for advanced features and edge cases of the
structure generator that aren't covered in the basic test suite.

Path: tests/test_structure_generator_advanced.py
"""

from pathlib import Path
import tempfile
import time
from datetime import datetime
from typing import Generator, Any
import os
import pytest

from pyweaver.processors import (
    generate_structure,
    ListingStyle,
    SortOrder
)

@pytest.fixture
def dated_files() -> Generator[Path, Any, None]:
    """Create files with different dates for testing."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        # Create files with different dates
        for days in [0, 7, 30, 90]:
            file = root / f"file_{days}days.txt"
            file.write_text(f"Content for {days} days ago")
            # Set access/modify times
            timestamp = time.time() - (days * 86400)
            os.utime(file, (timestamp, timestamp))

        yield root

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
        # Verify sort order logic
        lines = structure.splitlines()
        if sort_type == SortOrder.ALPHA:
            # Check alphabetical ordering
            sorted_lines = sorted(lines)
            assert lines == sorted_lines
        elif sort_type == SortOrder.SIZE:
            # Add size checks
            pass

def test_date_display(dated_files):
    """Test date display functionality."""
    structure = generate_structure(
        dated_files,
        show_date=True,
        date_format="%Y-%m-%d"
    )

    today = datetime.now().strftime("%Y-%m-%d")
    assert today in structure

    # Test custom date format
    structure = generate_structure(
        dated_files,
        show_date=True,
        date_format="%d/%m/%y"
    )
    assert today.replace("-", "/") in structure

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
