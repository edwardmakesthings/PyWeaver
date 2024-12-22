"""Private implementation of directory scanning.

Handles scanning directories and building structure representation while
respecting configuration options.

Path: tools/project_tools/structure_gen/_impl/_scanner.py
"""

from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from ...common.types import Pattern
from ..generator import StructureConfig
from ._types import DirectoryNode

logger = logging.getLogger(__name__)

class DirectoryScanner:
    """Scans directories to build structure."""

    def __init__(self, config: StructureConfig):
        self.config = config
        self._patterns = {
            'exclude': {Pattern(p) for p in config.exclude_patterns},
            'include': {Pattern(p) for p in config.include_patterns}
        }
        self._current_depth = 0

    def scan_directory(self) -> DirectoryNode:
        """Scan directory and build structure."""
        root_path = self.config.root_dir
        if not root_path.exists():
            raise FileNotFoundError(f"Directory not found: {root_path}")

        self._current_depth = 0
        return self._scan_node(root_path)

    def _scan_node(self, path: Path) -> Optional[DirectoryNode]:
        """Scan a single node in the structure."""
        try:
            # Skip if beyond max depth
            if (self.config.max_depth is not None and
                self._current_depth > self.config.max_depth):
                return self._create_node(path, children=[])

            # Skip if should be excluded
            if not self._should_include(path):
                return None

            # Create node for current path
            node = self._create_node(path)

            # Process children if directory
            if path.is_dir():
                self._current_depth += 1
                try:
                    children = []
                    for child_path in sorted(path.iterdir()):
                        child_node = self._scan_node(child_path)
                        if child_node is not None:
                            children.append(child_node)

                    # Only include empty dirs if configured
                    if children or self.config.include_empty:
                        node.children = children

                finally:
                    self._current_depth -= 1

            return node

        except PermissionError:
            logger.warning(f"Permission denied: {path}")
            return self._create_node(path, children=[])

        except Exception as e:
            logger.error(f"Error scanning {path}: {e}")
            return None

    def _create_node(self, path: Path, children: Optional[List[DirectoryNode]] = None) -> DirectoryNode:
        """Create a node for a path."""
        try:
            size = path.stat().st_size if path.is_file() and self.config.show_size else None
        except:
            size = None

        return DirectoryNode(
            path=path,
            rel_path=path.relative_to(self.config.root_dir),
            is_dir=path.is_dir(),
            size=size,
            children=children
        )

    def _should_include(self, path: Path) -> bool:
        """Check if path should be included."""
        try:
            rel_path = path.relative_to(self.config.root_dir)
            str_path = str(rel_path)

            # Check exclusions first
            for pattern in self._patterns['exclude']:
                if pattern.matches(str_path):
                    return False

            # Check inclusions if specified
            if self._patterns['include']:
                return any(p.matches(str_path) for p in self._patterns['include'])

            return True

        except Exception as e:
            logger.error(f"Error checking path {path}: {e}")
            return False
