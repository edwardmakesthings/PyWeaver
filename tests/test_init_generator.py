"""Test suite for init file generator.

Provides comprehensive testing of the init file generator including
configuration handling, export collection, and file generation.

Path: tests/test_init_generator.py
"""

import json
import pytest
from pathlib import Path
import tempfile
import textwrap
from typing import Generator, Any

from tools.project_tools.init_generator import (
    create_generator,
    ExportCollectionMode,
    InitGeneratorConfig
)

@pytest.fixture
def temp_package() -> Generator[Path, Any, None]:
    """Create a temporary package structure."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Create a sample package structure
        pkg_root = tmp_path / "sample_package"
        pkg_root.mkdir()

        # Create some modules with exports
        module1 = pkg_root / "module1.py"
        module1.write_text(textwrap.dedent('''
            """Module 1 docstring."""

            class MyClass:
                """A sample class."""
                pass

            def my_function():
                """A sample function."""
                pass

            CONSTANT = "value"
            _private = "hidden"
        '''))

        # Create a subpackage
        subpkg = pkg_root / "subpackage"
        subpkg.mkdir()

        # Add a module to the subpackage
        submodule = subpkg / "submodule.py"
        submodule.write_text(textwrap.dedent('''
            """Submodule docstring."""

            class SubClass:
                """A submodule class."""
                pass

            def sub_function():
                """A submodule function."""
                pass
        '''))

        yield pkg_root

@pytest.fixture
def config_file(temp_package: Path) -> Path:
    """Create a test configuration file."""
    config = {
        "global": {
            "order_policy": "dependency_first",
            "docstring": "Auto-generated __init__.py file.",
            "exports_blacklist": ["internal_*", "test_*", "_*"],
            "excluded_paths": [
                "**/__pycache__",
                "**/.git"
            ]
        },
        "paths": {
            str(temp_package): {
                "docstring": "Test package initialization.",
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

    config_path = temp_package.parent / "init_config.json"
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    return config_path

def test_basic_generation(temp_package: Path):
    """Test basic init file generation."""
    generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    # Generate init files
    result = generator.write()
    assert result.success
    assert result.files_written > 0

    # Check main init file
    init_file = temp_package / "__init__.py"
    assert init_file.exists()
    content = init_file.read_text()

    # Should include public exports
    assert "MyClass" in content
    assert "my_function" in content
    assert "CONSTANT" in content
    assert "_private" not in content  # Should exclude private

def test_config_based_generation(temp_package: Path, config_file: Path):
    """Test generation using configuration file."""
    # Load config
    with open(config_file) as f:
        config = json.load(f)

    # Get settings for package
    settings = config["global"].copy()
    settings.update(config["paths"][str(temp_package)])

    generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC,
        exclude_patterns=set(settings.get("excluded_paths", [])),
        docstring_template=settings.get("docstring")
    )

    result = generator.write()
    assert result.success

    # Check init file content
    init_file = temp_package / "__init__.py"
    content = init_file.read_text()

    # Should include configured docstring
    assert "Test package initialization." in content
    # Should include version from inline content
    assert '__version__ = ' in content

def test_export_collection_modes(temp_package: Path):
    """Test different export collection modes."""
    # Test explicit mode
    explicit_generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.EXPLICIT
    )

    explicit_preview = explicit_generator.preview()

    # Test all public mode
    public_generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    public_preview = public_generator.preview()

    # Public mode should include more exports
    assert len(str(public_preview)) > len(str(explicit_preview))

def test_preview_functionality(temp_package: Path):
    """Test preview generation."""
    generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    # Get preview
    changes = generator.preview()

    # Preview shouldn't create files
    init_file = temp_package / "__init__.py"
    assert not init_file.exists()

    # Preview should show expected content
    assert isinstance(changes, dict)
    assert any("__init__.py" in str(path) for path in changes.keys())

def test_error_handling():
    """Test error handling for invalid inputs."""
    # Test with non-existent directory
    with pytest.raises(Exception):
        generator = create_generator(
            root_dir=Path("non_existent_dir"),
            export_mode=ExportCollectionMode.ALL_PUBLIC
        )
        generator.write()

def test_docstring_handling(temp_package: Path):
    """Test docstring handling in generated files."""
    custom_docstring = "Custom package docstring."

    generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC,
        docstring_template=custom_docstring
    )

    result = generator.write()
    assert result.success

    # Check docstring in generated file
    init_file = temp_package / "__init__.py"
    content = init_file.read_text()
    assert custom_docstring in content

def test_subpackage_handling(temp_package: Path):
    """Test handling of subpackages."""
    generator = create_generator(
        root_dir=temp_package,
        export_mode=ExportCollectionMode.ALL_PUBLIC
    )

    result = generator.write()
    assert result.success

    # Check subpackage init
    subpkg_init = temp_package / "subpackage" / "__init__.py"
    assert subpkg_init.exists()

    content = subpkg_init.read_text()
    assert "SubClass" in content
    assert "sub_function" in content

if __name__ == "__main__":
    pytest.main([__file__])
