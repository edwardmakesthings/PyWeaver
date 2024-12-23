"""Private implementation of structure generation.

Coordinates directory scanning, structure formatting and output generation.

Path: pyweaver/structure_generator/_impl/_generator.py
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from pyweaver.common.type_definitions import GeneratorResult, ProcessingError
from pyweaver.structure_generator.generator import StructureConfig
from pyweaver.structure_generator._impl._scanner import DirectoryScanner
from pyweaver.structure_generator._impl._formatter import StructureFormatter
from pyweaver.structure_generator._impl._types import DirectoryNode

logger = logging.getLogger(__name__)

class StructureGeneratorImpl:
    """Internal implementation of structure generator."""

    def __init__(self, config: StructureConfig):
        self.config = config
        self._scanner = DirectoryScanner(config)
        self._formatter = StructureFormatter(config)
        self._structure: DirectoryNode = None

    def generate_structure(self) -> GeneratorResult:
        """Generate structure documentation."""
        try:
            # Scan directory
            structure = self._scanner.scan_directory()
            self._structure = structure

            # Format and write structure
            content = self._formatter.format_structure(structure)
            self._write_output(content)

            return GeneratorResult(
                success=True,
                message=f"Structure written to {self.config.output_file}",
                files_processed=self._count_nodes(structure),
                files_written=1
            )

        except Exception as e:
            logger.error("Error generating structure: %s", e)
            raise ProcessingError(f"Failed to generate structure: {str(e)}")

    def preview_structure(self) -> str:
        """Generate preview without writing."""
        try:
            structure = self._scanner.scan_directory()
            return self._formatter.format_structure(structure)
        except Exception as e:
            logger.error("Error generating preview: %s", e)
            raise ProcessingError(f"Failed to generate preview: {str(e)}")

    def _write_output(self, content: str) -> None:
        """Write formatted content to output file."""
        try:
            self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.output_file.write_text(content)
        except Exception as e:
            logger.error("Error writing output: %s", e)
            raise ProcessingError(f"Failed to write output: {str(e)}")

    def _count_nodes(self, node: DirectoryNode) -> int:
        """Count total nodes in structure."""
        count = 1  # Current node
        if node.children:
            count += sum(self._count_nodes(child) for child in node.children)
        return count
