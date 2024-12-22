"""Private implementation of init file generator.

Provides internal implementation details for init file generation,
including content collection, docstring formatting, and file writing
operations.

Modules:
    collector: Module content collection
    writer: Init file writing
    formatter: Content formatting

Path: tools/project_tools/init_generator/_impl/__init__.py
"""
from typing import Dict
from pathlib import Path

from ._collector import ModuleCollector
from ._formatter import ContentFormatter
from ._writer import InitFileWriter

class InitGeneratorImpl:
    """Internal implementation of init file generator."""

    def __init__(self, config: 'InitGeneratorConfig'):
        self.config = config
        self.collector = ModuleCollector(config)
        self.formatter = ContentFormatter(config)
        self.writer = InitFileWriter(config)

    def preview_files(self) -> Dict[Path, str]:
        """Generate preview of init files."""
        modules = self.collector.collect_modules()
        return {
            path: self.formatter.format_content(content)
            for path, content in modules.items()
        }

    def write_files(self) -> 'GeneratorResult':
        """Write init files to disk."""
        previews = self.preview_files()
        return self.writer.write_files(previews)

    def generate_combined(self, output_path: Path) -> Path:
        """Generate combined output file."""
        previews = self.preview_files()
        return self.writer.write_combined(previews, output_path)

    def validate(self) -> 'ValidationResult':
        """Validate configuration and setup."""
        result = ValidationResult(is_valid=True)

        # Validate root directory
        if not self.config.root_dir.is_dir():
            result.is_valid = False
            result.errors.append(f"Root directory does not exist: {self.config.root_dir}")

        # Validate patterns
        try:
            for pattern in self.config.exclude_patterns:
                Pattern(pattern)
            for pattern in self.config.include_patterns:
                Pattern(pattern)
        except re.error as e:
            result.is_valid = False
            result.errors.append(f"Invalid pattern: {e}")

        return result

__all__ = [
    "InitGeneratorImpl"
]
