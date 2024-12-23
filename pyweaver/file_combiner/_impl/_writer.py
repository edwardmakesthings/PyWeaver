"""Private implementation of combined file writing.

Handles writing combined file content and generating tree structure
documentation.

Path: pyweaver/file_combiner/_impl/_writer.py
"""

from pathlib import Path
from typing import List, Dict, Any
import logging

from pyweaver.file_combiner._impl._combiner import FileContent
from pyweaver.file_combiner.combiner import CombinerConfig

logger = logging.getLogger(__name__)

class CombinerWriter:
    """Handles writing combined content and tree structure."""

    def __init__(self, config: CombinerConfig):
        self.config = config

    def write_combined(self, files: List[FileContent], output_path: Path) -> None:
        """Write combined content to output file.

        Args:
            files: List of processed file content
            output_path: Path to write combined output

        Raises:
            IOError: If writing fails
        """
        try:
            content = self.format_combined(files)

            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write combined content
            output_path.write_text(content)
            logger.info(f"Wrote combined output to {output_path}")

        except Exception as e:
            logger.error(f"Error writing combined output: {e}")
            raise

    def write_tree(self, paths: List[Path]) -> None:
        """Write tree structure documentation.

        Args:
            paths: List of paths to include in tree

        Raises:
            IOError: If writing fails
        """
        try:
            # Get output path for tree
            output_path = self.config.output_file.with_suffix('.tree.txt')

            # Generate tree content
            content = self._generate_tree(paths)

            # Write tree file
            output_path.write_text(content)
            logger.info(f"Wrote tree structure to {output_path}")

        except Exception as e:
            logger.error(f"Error writing tree structure: {e}")
            raise

    def format_combined(self, files: List[FileContent]) -> str:
        """Format content for combined output.

        Args:
            files: List of processed file content

        Returns:
            Formatted content ready for writing
        """
        lines = []

        # Add header
        lines.append("# Combined Source Files")
        lines.append(f"# Total files: {len(files)}\n")

        # Add each file
        for file_content in files:
            lines.append(f"{'#' * 80}")
            lines.append(f"# Source path: {file_content.rel_path}")
            lines.append(f"{'#' * 80}\n")

            lines.append(file_content.content)
            lines.append("")  # Empty line between files

        return "\n".join(lines)

    def _generate_tree(self, paths: List[Path]) -> str:
        """Generate tree structure documentation.

        Args:
            paths: List of paths to include in tree

        Returns:
            Formatted tree structure
        """
        # Build tree dictionary
        tree: Dict[str, Any] = {}
        for path in sorted(paths):
            current = tree
            for part in path.parts:
                current = current.setdefault(part, {})

        # Format tree
        lines = [
            "# Project Structure",
            f"# Total files: {len(paths)}",
            ""
        ]

        lines.extend(self._format_tree_node(tree))
        return "\n".join(lines)

    def _format_tree_node(self, node: Dict[str, Any], prefix: str = "", is_last: bool = True) -> List[str]:
        """Format a single node in the tree structure.

        Args:
            node: Node to format
            prefix: Current line prefix
            is_last: Whether this is the last item at this level

        Returns:
            List of formatted lines
        """
        lines = []

        if not node:
            return lines

        items = sorted(node.items())
        for i, (name, subtree) in enumerate(items):
            is_last_item = i == len(items) - 1
            connector = "└── " if is_last_item else "├── "

            lines.append(f"{prefix}{connector}{name}")

            if subtree:
                extension = "    " if is_last_item else "│   "
                lines.extend(self._format_tree_node(
                    subtree,
                    prefix + extension,
                    is_last_item
                ))

        return lines
