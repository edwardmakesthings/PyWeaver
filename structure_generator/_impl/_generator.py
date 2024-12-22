"""Private implementation of structure generation.

Coordinates directory scanning, structure formatting and output generation.

Path: tools/project_tools/structure_generator/_impl/_generator.py
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from ...common.types import GeneratorResult, Pattern
from ..generator import StructureConfig, OutputFormat
from ._scanner import DirectoryScanner
from ._formatter import StructureFormatter
from ._types import DirectoryNode

logger = logging.getLogger(__name__)

class StructureGeneratorImpl:
    """Internal implementation of structure generator."""

    def __init__(self, config: StructureConfig):
        self.config = config
        self._scanner = DirectoryScanner(config)
        self._formatter = StructureFormatter(config)
        self._structure: Optional[DirectoryNode] = None

    def generate_structure(self) -> GeneratorResult:
        """Generate structure documentation."""
        try:
            # Scan directory
            structure = self._scanner.scan_directory()
            self._structure = structure

            # Format structure
            content = self._formatter.format_structure(structure)

            # Write output
            self.config.output_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.output_file.write_text(content)

            return GeneratorResult(
                success=True,
                message=f"Structure written to {self.config.output_file}",
                files_processed=self._count_nodes(structure),
                files_written=1
            )

        except Exception as e:
            logger.error(f"Error generating structure: {e}")
            return GeneratorResult(
                success=False,
                message=f"Failed to generate structure: {str(e)}",
                errors=[str(e)]
            )

    def preview_structure(self) -> str:
        """Generate preview without writing."""
        structure = self._scanner.scan_directory()
        return self._formatter.format_structure(structure)

    def _count_nodes(self, node: DirectoryNode) -> int:
        """Count total nodes in structure."""
        count = 1  # Current node
        if node.children:
            count += sum(self._count_nodes(child) for child in node.children)
        return count
