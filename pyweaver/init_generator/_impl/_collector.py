"""Private implementation of module content collection.

Collects exports, docstrings and dependencies from Python modules.

Path: pyweaver/init_generator/_impl/_collector.py
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, Optional, List
import logging

from pyweaver.common.types import Pattern
from pyweaver.init_generator.generator import InitGeneratorConfig, ExportCollectionMode

logger = logging.getLogger(__name__)

@dataclass
class SectionConfig:
    """Configuration for a section in the __init__ file."""
    enabled: bool = True
    order: int = 0
    header_comment: Optional[str] = None
    footer_comment: Optional[str] = None
    separator: str = "\n"
    include_patterns: List[str] = field(default_factory=list)
    exclude_patterns: List[str] = field(default_factory=list)

class ParentNodeVisitor(ast.NodeTransformer):
    """AST visitor that adds parent references to all nodes."""
    def visit(self, node):
        for child in ast.iter_child_nodes(node):
            child.parent = node
        return super().visit(node)

@dataclass
class ModuleContent:
    """Content collected from a module."""
    path: Path
    exports: Set[str] = field(default_factory=set)
    imports: Set[str] = field(default_factory=set)  # Added imports field
    docstring: Optional[str] = None
    dependencies: Set[str] = field(default_factory=set)
    source_code: Optional[str] = None

    def __post_init__(self):
        """Ensure collections are initialized."""
        self.exports = self.exports or set()
        self.imports = self.imports or set()
        self.dependencies = self.dependencies or set()

class ModuleCollector:
    """Collects content from Python modules."""

    def __init__(self, config: InitGeneratorConfig):
        self.config = config
        self._module_cache: Dict[Path, ModuleContent] = {}
        self._patterns = {
            'exclude': {Pattern(p) for p in config.exclude_patterns},
            'include': {Pattern(p) for p in config.include_patterns}
        }

    def collect_modules(self) -> Dict[Path, ModuleContent]:
        """Collect content from all modules in directory."""
        results = {}

        # Only look for __init__.py files
        for init_file in self.config.root_dir.rglob("__init__.py"):
            if self._should_process(init_file):
                try:
                    content = self._collect_from_file(init_file)
                    if content:
                        results[init_file] = content
                except Exception as e:
                    logger.error("Error collecting from %s: %s", init_file, e)

        return results

    def _should_process(self, path: Path) -> bool:
        """Check if path should be processed."""
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
        except ValueError:
            return False

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

            # Collect exports and imports
            visitor = ModuleVisitor(self.config.export_mode)
            visitor.visit(tree)

            # Filter out any exports not actually defined in this module
            defined_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
                    defined_names.add(node.id)
                elif isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                    defined_names.add(node.name)

            # Only include exports that are actually defined in this module
            content.exports = {name for name in visitor.exports if name in defined_names}
            content.imports = visitor.imports
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
        self.imports: Set[str] = set()  # Will store full import statements only
        self.dependencies: Set[str] = set()
        self._current_class = None
        self._all_exports: Optional[Set[str]] = None
        self._in_class = False

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        prev_in_class = self._in_class
        self._in_class = True

        # Only export module-level classes
        if not prev_in_class and self._should_export(node.name):
            self.exports.add(node.name)

        self.generic_visit(node)
        self._in_class = prev_in_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        # Only export module-level functions
        if not self._in_class and self._should_export(node.name):
            self.exports.add(node.name)

    def visit_Import(self, node: ast.Import):
        """Visit import statement."""
        for alias in node.names:
            # Build the full import statement
            if alias.asname:
                self.imports.add(f"import {alias.name} as {alias.asname}")
            else:
                self.imports.add(f"import {alias.name}")

            # Track the base module dependency
            self.dependencies.add(alias.name.split('.')[0])

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from-import statement."""
        if node.module:
            # Build the module path
            if node.level > 0:
                module_prefix = '.' * node.level
                module_path = f"{module_prefix}{node.module}" if node.module else module_prefix
            else:
                module_path = node.module

            # Handle the imported names
            names = []
            for alias in node.names:
                if alias.name == '*':
                    continue  # Skip star imports
                if alias.asname:
                    names.append(f"{alias.name} as {alias.asname}")
                else:
                    names.append(alias.name)

            if names:
                self.imports.add(f"from {module_path} import {', '.join(sorted(names))}")

            # Track the base module dependency
            if node.module:
                self.dependencies.add(node.module.split('.')[0])

    def visit_Assign(self, node: ast.Assign):
        """Visit assignment statement."""
        if not self._in_class:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    # Handle __all__ definition
                    if target.id == '__all__':
                        if isinstance(node.value, ast.List):
                            self._all_exports = {
                                elt.s for elt in node.value.elts
                                if isinstance(elt, ast.Str)
                            }
                    elif self._should_export(target.id):
                        # Export constants and variables
                        self.exports.add(target.id)

    def _should_export(self, name: str) -> bool:
        """Check if name should be exported based on mode."""
        # Never export private names
        if name.startswith('_') and not name == '__all__':
            return False

        if self.export_mode == ExportCollectionMode.EXPLICIT:
            # Only export if in __all__
            return self._all_exports is not None and name in self._all_exports

        elif self.export_mode == ExportCollectionMode.ALL_PUBLIC:
            # Export all public names
            return True

        # Custom mode - implement specific logic here
        return False

