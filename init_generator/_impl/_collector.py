"""Private implementation of module content collection.

Collects exports, docstrings and dependencies from Python modules.

Path: tools/project_tools/init_generator/_impl/_collector.py
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, Optional
import logging

from ...common.types import Pattern
from ..generator import InitGeneratorConfig, ExportCollectionMode

logger = logging.getLogger(__name__)

@dataclass
class ModuleContent:
    """Content collected from a module."""
    path: Path
    exports: Set[str] = field(default_factory=set)
    docstring: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)
    source_code: Optional[str] = None

class ModuleCollector:
    """Collects content from Python modules."""

    def __init__(self, config: InitGeneratorConfig):
        self.config = config
        self._module_cache: Dict[Path, ModuleContent] = {}
        self._patterns = {
            'exclude': {Pattern(p) for p in config.exclude_patterns},
            'include': {Pattern(p) for p in config.include_patterns}
        }
        self._current_class = None

    def collect_modules(self) -> Dict[Path, ModuleContent]:
        """Collect content from all modules in directory."""
        results = {}

        # Find Python files
        for py_file in self.config.root_dir.rglob("*.py"):
            if self._should_process(py_file):
                try:
                    content = self._collect_from_file(py_file)
                    if content:
                        results[py_file] = content
                except Exception as e:
                    logger.error("Error collecting from %s: %s", py_file, e)

        return results

    def _should_process(self, path: Path) -> bool:
        """Check if path should be processed."""
        try:
            rel_path = path.relative_to(self.config.root_dir)
        except ValueError:
            return False

        # Check exclusions first
        for pattern in self._patterns['exclude']:
            if pattern.matches(rel_path):
                return False

        # Check inclusions if specified
        if self._patterns['include']:
            return any(p.matches(rel_path) for p in self._patterns['include'])

        return True

    def _collect_from_file(self, path: Path) -> Optional[ModuleContent]:
        """Collect content from a single Python file."""
        if path in self._module_cache:
            return self._module_cache[path]

        try:
            with open(path, 'r', encoding='utf-8') as f:
                source = f.read()
                tree = ast.parse(source)

            content = ModuleContent(
                path=path,
                source_code=source
            )

            # Get module docstring
            content.docstring = ast.get_docstring(tree)

            # Collect exports and dependencies
            visitor = ModuleVisitor(self.config.export_mode)
            visitor.visit(tree)
            content.exports = visitor.exports
            content.dependencies = visitor.dependencies

            self._module_cache[path] = content
            return content

        except Exception as e:
            logger.error("Error parsing %s: %s", path, e)
            return None

class ModuleVisitor(ast.NodeVisitor):
    """AST visitor to collect module contents."""

    def __init__(self, export_mode: ExportCollectionMode):
        self.export_mode = export_mode
        self.exports: Set[str] = set()
        self.dependencies: Set[str] = set()
        self._current_class = None
        self._all_exports: Optional[Set[str]] = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        prev_class = self._current_class
        self._current_class = node

        if self._should_export(node.name):
            self.exports.add(node.name)

        # Visit class contents
        self.generic_visit(node)
        self._current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        # Only export module-level functions
        if not self._current_class and self._should_export(node.name):
            self.exports.add(node.name)

    def visit_Import(self, node: ast.Import):
        """Visit import statement."""
        for alias in node.names:
            self.dependencies.add(alias.name.split('.')[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statement."""
        if node.module:
            self.dependencies.add(node.module.split('.')[0])

    def visit_Assign(self, node: ast.Assign):
        """Visit assignment statement - handle __all__ and exports."""
        if not self._current_class:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Handle __all__ definition
                    if target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            self._all_exports = {
                                elt.s for elt in node.value.elts
                                if isinstance(elt, ast.Str)  # Use .s instead of .value
                            }
                    elif self._should_export(target.id):
                        self.exports.add(target.id)

    def _should_export(self, name: str) -> bool:
        """Check if name should be exported based on mode."""
        # Never export private names
        if name.startswith('_'):
            return False

        if self.export_mode == ExportCollectionMode.EXPLICIT:
            # Only export if in __all__
            return self._all_exports is not None and name in self._all_exports

        elif self.export_mode == ExportCollectionMode.ALL_PUBLIC:
            # Export all public names
            return True

        # Custom mode - implement specific logic here
        return False

