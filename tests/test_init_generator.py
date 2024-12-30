"""Comprehensive test suite for init file generation.

This module provides thorough testing of the init file generator functionality,
including complex scenarios, error cases, and edge conditions.

Path: tests/test_init_generator.py
"""

from pathlib import Path
import tempfile
import textwrap
from typing import Generator, Any
import pytest

from pyweaver.processors import (
    InitFileProcessor,
    generate_init_files
)
from pyweaver.config.init import (
    ImportOrderPolicy,
    ImportSection,
    ExportMode
)

@pytest.fixture
def complex_package() -> Generator[Path, Any, None]:
    """Create a complex package structure for testing.

    This fixture creates a more sophisticated package structure with:
    - Nested modules and packages
    - Complex class hierarchies
    - Various import patterns
    - Different export declarations
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        pkg_root = tmp_path / "complex_package"
        pkg_root.mkdir()

        # Create base classes module
        base_dir = pkg_root / "base"
        base_dir.mkdir()
        base_init = base_dir / "__init__.py"
        base_init.write_text(textwrap.dedent('''
            """Base package with core abstractions."""

            from .base_classes import BaseHandler, BaseProcessor
            from .interfaces import HandlerInterface, ProcessorInterface

            __all__ = [
                'BaseHandler',
                'BaseProcessor',
                'HandlerInterface',
                'ProcessorInterface'
            ]
        '''))

        base_classes = base_dir / "base_classes.py"
        base_classes.write_text(textwrap.dedent('''
            """Base implementation classes."""

            from abc import ABC, abstractmethod
            from .interfaces import HandlerInterface, ProcessorInterface

            class BaseHandler(HandlerInterface):
                """Base handler implementation."""
                def handle(self):
                    """Handle request."""
                    pass

            class BaseProcessor(ProcessorInterface):
                """Base processor implementation."""
                def process(self):
                    """Process data."""
                    pass
        '''))

        interfaces = base_dir / "interfaces.py"
        interfaces.write_text(textwrap.dedent('''
            """Core interfaces."""

            from abc import ABC, abstractmethod
            from typing import Any

            class HandlerInterface(ABC):
                """Interface for handlers."""
                @abstractmethod
                def handle(self) -> Any:
                    """Handle request."""
                    pass

            class ProcessorInterface(ABC):
                """Interface for processors."""
                @abstractmethod
                def process(self) -> Any:
                    """Process data."""
                    pass
        '''))

        # Create implementations
        impl_dir = pkg_root / "impl"
        impl_dir.mkdir()
        impl_init = impl_dir / "__init__.py"
        impl_init.write_text(textwrap.dedent('''
            """Implementation package."""

            from .handlers import CustomHandler, SpecialHandler
            from .processors import DataProcessor, FileProcessor

            __all__ = [
                'CustomHandler',
                'SpecialHandler',
                'DataProcessor',
                'FileProcessor'
            ]
        '''))

        handlers = impl_dir / "handlers.py"
        handlers.write_text(textwrap.dedent('''
            """Handler implementations."""

            from ..base import BaseHandler

            class CustomHandler(BaseHandler):
                """Custom handler implementation."""
                def handle(self):
                    """Handle custom request."""
                    return "Handled"

            class SpecialHandler(BaseHandler):
                """Special handler implementation."""
                def handle(self):
                    """Handle special request."""
                    return "Special"
        '''))

        processors = impl_dir / "processors.py"
        processors.write_text(textwrap.dedent('''
            """Processor implementations."""

            from ..base import BaseProcessor
            from typing import Optional

            class DataProcessor(BaseProcessor):
                """Data processor implementation."""
                def process(self):
                    """Process data."""
                    return "Processed"

            class FileProcessor(BaseProcessor):
                """File processor implementation."""
                def __init__(self, path: Optional[str] = None):
                    self.path = path

                def process(self):
                    """Process file."""
                    return f"Processed {self.path}"
        '''))

        # Create utils package with no __init__.py
        utils_dir = pkg_root / "utils"
        utils_dir.mkdir()
        helpers = utils_dir / "helpers.py"
        helpers.write_text(textwrap.dedent('''
            """Helper utilities."""

            def format_output(value: str) -> str:
                """Format output value."""
                return f"[{value}]"

            def validate_input(value: str) -> bool:
                """Validate input value."""
                return bool(value.strip())
        '''))

        yield pkg_root

def test_complex_package_generation(complex_package: Path):
    """Test init file generation for complex package structure."""
    # Generate init files
    generator = InitFileProcessor(complex_package)
    result = generator.process()

    assert result.success
    assert result.files_processed > 0

    # Verify base package init
    base_init = complex_package / "base" / "__init__.py"
    content = base_init.read_text()
    assert "BaseHandler" in content
    assert "BaseProcessor" in content
    assert "HandlerInterface" in content
    assert "ProcessorInterface" in content

    # Verify implementation package init
    impl_init = complex_package / "impl" / "__init__.py"
    content = impl_init.read_text()
    assert "CustomHandler" in content
    assert "SpecialHandler" in content
    assert "DataProcessor" in content
    assert "FileProcessor" in content

def test_export_collection_modes(complex_package: Path):
    """Test different export collection modes."""
    # Test explicit mode
    explicit_result = generate_init_files(
        complex_package,
        export_mode=ExportMode.EXPLICIT,
        preview=True
    )

    # Test all public mode
    public_result = generate_init_files(
        complex_package,
        export_mode=ExportMode.ALL_PUBLIC,
        preview=True
    )

    # Explicit mode should only include items in __all__
    base_init = explicit_result[complex_package / "base" / "__init__.py"]
    assert all(name in base_init for name in [
        "BaseHandler",
        "BaseProcessor",
        "HandlerInterface",
        "ProcessorInterface"
    ])

    # Public mode should include all non-underscore items
    impl_init = public_result[complex_package / "impl" / "__init__.py"]
    assert all(name in impl_init for name in [
        "CustomHandler",
        "SpecialHandler",
        "DataProcessor",
        "FileProcessor"
    ])

def test_import_ordering_policies(complex_package: Path):
    """Test different import ordering policies."""
    # Test dependency-first ordering
    dependency_result = generate_init_files(
        complex_package,
        order_policy=ImportOrderPolicy.DEPENDENCY_FIRST,
        preview=True
    )

    # Test alphabetical ordering
    alpha_result = generate_init_files(
        complex_package,
        order_policy=ImportOrderPolicy.ALPHABETICAL,
        preview=True
    )

    # Verify dependency ordering
    base_init = dependency_result[complex_package / "base" / "__init__.py"]
    interface_index = base_init.index("interfaces")
    base_classes_index = base_init.index("base_classes")
    assert interface_index < base_classes_index  # Interfaces should be imported first

    # Verify alphabetical ordering
    impl_init = alpha_result[complex_package / "impl" / "__init__.py"]
    handlers_index = impl_init.index("handlers")
    processors_index = impl_init.index("processors")
    assert handlers_index < processors_index  # handlers before processors

def test_section_organization(complex_package: Path):
    """Test content organization into sections."""
    generator = InitFileProcessor(
        complex_package,
        config_path=None  # Use default config
    )

    # Customize section configuration
    generator.init_config.global_settings.sections = {
        ImportSection.CLASSES.value: {
            "enabled": True,
            "order": 1,
            "header_comment": "# Classes",
            "include_patterns": {"*Handler", "*Processor"}
        },
        ImportSection.FUNCTIONS.value: {
            "enabled": True,
            "order": 2,
            "header_comment": "# Functions",
            "include_patterns": {"format_*", "validate_*"}
        }
    }

    changes = generator.preview()

    # Check section organization in utils init
    utils_init = changes.get(complex_package / "utils" / "__init__.py", "")
    assert "# Classes" in utils_init
    assert "# Functions" in utils_init
    assert utils_init.index("# Classes") < utils_init.index("# Functions")

def test_error_handling(complex_package: Path):
    """Test error handling scenarios."""
    # Test with invalid config
    with pytest.raises(Exception):
        InitFileProcessor(
            complex_package,
            config_path=complex_package / "nonexistent.json"
        )

    # Test with invalid root directory
    with pytest.raises(Exception):
        generate_init_files(
            complex_package / "nonexistent",
            preview=True
        )

    # Test with syntax error in Python file
    invalid_file = complex_package / "invalid.py"
    invalid_file.write_text("this is not valid python")

    generator = InitFileProcessor(complex_package)
    result = generator.process()

    assert not result.success
    assert len(result.errors) > 0
    assert "syntax" in result.errors[0].lower()

def test_preview_functionality(complex_package: Path):
    """Test preview generation functionality."""
    generator = InitFileProcessor(complex_package)
    preview = generator.preview()

    # Verify preview content
    assert isinstance(preview, dict)
    assert len(preview) > 0

    # Verify no files were actually created
    utils_init = complex_package / "utils" / "__init__.py"
    assert not utils_init.exists()

    # Generate files and verify content matches preview
    result = generator.process()
    assert result.success

    for path, preview_content in preview.items():
        assert path.exists()
        actual_content = path.read_text()
        assert actual_content == preview_content

def test_docstring_handling(complex_package: Path):
    """Test docstring handling in generated files."""
    custom_docstring = "Custom package initialization."

    result = generate_init_files(
        complex_package,
        docstring=custom_docstring,
        preview=True
    )

    # Check docstring in each init file
    for content in result.values():
        assert content.startswith('"""')
        assert custom_docstring in content
        assert 'Path:' in content  # Should include path information

def test_nested_package_handling(complex_package: Path):
    """Test handling of nested package structures."""
    generator = InitFileProcessor(complex_package)
    result = generator.process()

    assert result.success

    # Check base package init
    base_init = complex_package / "base" / "__init__.py"
    assert base_init.exists()
    content = base_init.read_text()
    assert "from .base_classes import" in content
    assert "from .interfaces import" in content

    # Check implementation package init
    impl_init = complex_package / "impl" / "__init__.py"
    assert impl_init.exists()
    content = impl_init.read_text()
    assert "from .handlers import" in content
    assert "from .processors import" in content

if __name__ == "__main__":
    pytest.main([__file__])
