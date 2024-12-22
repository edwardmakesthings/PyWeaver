"""Private implementation of init file generator.

Coordinates the collection, formatting and writing of init files.

Path: tools/project_tools/init_generator/_impl/_generator.py
"""

from pathlib import Path
from typing import Dict
import logging

from ...common.types import GeneratorResult
from ..generator import InitGeneratorConfig
from ._collector import ModuleCollector
from ._formatter import ContentFormatter
from ._writer import InitWriter

logger = logging.getLogger(__name__)

class InitGeneratorImpl:
    """Internal implementation of init file generator."""

    def __init__(self, config: InitGeneratorConfig):
        self.config = config
        self._collector = ModuleCollector(config)
        self._formatter = ContentFormatter(config)
        self._writer = InitWriter(config)

    def preview_files(self) -> Dict[Path, str]:
        """Generate preview of init files that would be written."""
        # Collect module content
        module_contents = self._collector.collect_modules()

        # Format each module's content
        return {
            path: self._formatter.format_content(content)
            for path, content in module_contents.items()
        }

    def write_files(self) -> GeneratorResult:
        """Write init files to disk."""
        try:
            # Get formatted content
            files = self.preview_files()

            # Write files
            return self._writer.write_files(files)
        except Exception as e:
            logger.error("Error writing files: %s", e)
            return GeneratorResult(
                success=False,
                message=f"Failed to write files: {e}",
                files_processed=0,
                files_written=0,
                errors=[str(e)]
            )

    def generate_combined(self, output_path: Path) -> Path:
        """Generate combined output file."""
        try:
            # Get all content
            files = self.preview_files()

            # Write combined output
            return self._writer.write_combined(files, output_path)
        except Exception as e:
            logger.error("Error generating combined output: %s", e)
            raise


