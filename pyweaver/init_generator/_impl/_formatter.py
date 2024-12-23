"""Private implementation of init file content formatting.

Formats collected module content into proper __init__.py file content
following project standards.

Path: pyweaver/init_generator/_impl/_formatter.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

from pyweaver.init_generator.generator import InitGeneratorConfig
from pyweaver.init_generator._impl._collector import ModuleContent

logger = logging.getLogger(__name__)

@dataclass
class Section:
    """Content section with optional header."""
    name: str
    header: Optional[str] = None
    content: List[str] = None

    def __post_init__(self):
        self.content = self.content or []

    def add(self, line: str):
        """Add line to section."""
        self.content.append(line)

    def is_empty(self) -> bool:
        """Check if section has content."""
        return len(self.content) == 0

    def format(self, indent: str = "") -> str:
        """Format section content."""
        if self.is_empty():
            return ""

        lines = []
        if self.header:
            lines.append(f"\n{self.header}")

        for line in self.content:
            if line:
                lines.append(f"{indent}{line}")
            else:
                lines.append("")

        return "\n".join(lines)

class ContentFormatter:
    """Formats init file content."""

    def __init__(self, config: InitGeneratorConfig):
        self.config = config

    def format_content(self, content: ModuleContent) -> str:
        """Format module content into init file content."""
        sections = self._create_sections()

        # Add docstring
        self._add_docstring(content, sections['docstring'])

        # Add imports
        if content.imports:
            self._add_imports(content.imports, sections['imports'])

        # Add exports by type
        self._sort_exports(content.exports, sections)

        # Add __all__ declaration if there are exports
        if content.exports:
            self._add_all_exports(content.exports, sections['exports'])

        # Combine sections
        return self._combine_sections(sections)

    def _create_sections(self) -> Dict[str, Section]:
        """Create standard content sections."""
        return {
            'docstring': Section('docstring'),
            'imports': Section('imports', "# Imports"),
            'classes': Section('classes', "# Classes"),
            'functions': Section('functions', "# Functions"),
            'constants': Section('constants', "# Constants"),
            'type_definitions': Section('type_definitions', "# Type Definitions"),
            'variables': Section('variables', "# Variables"),
            'exports': Section('exports')
        }

    def _add_docstring(self, content: ModuleContent, section: Section):
        """Format and add docstring."""
        lines = []

        # Use template if provided
        if self.config.docstring_template:
            docstring = self.config.docstring_template
            # Replace placeholders
            docstring = docstring.replace("${path}", str(content.path))
        else:
            docstring = content.docstring or "Module initialization."

        lines.extend(docstring.split('\n'))

        # Add path information
        rel_path = content.path.relative_to(self.config.root_dir)
        lines.append("")
        lines.append(f"Path: {rel_path}")

        section.add(f'"""{chr(10).join(lines)}"""')
        section.add("")

    def _add_imports(self, imports: Set[str], section: Section):
        """Add formatted imports."""
        # Sort imports for consistency
        for import_stmt in sorted(imports):
            section.add(import_stmt)
        section.add("")  # Add blank line after imports

    def _sort_exports(self, exports: Set[str], sections: Dict[str, Section]):
        """Sort exports into appropriate sections."""
        for export in sorted(exports):
            # Skip __all__ as it's handled separately
            if export == '__all__':
                continue

            if export.isupper() or export.endswith('_CONSTANT'):
                sections['constants'].add(export)
            elif export.endswith(('Type', 'Types', 'Config')):
                sections['type_definitions'].add(export)
            elif export[0].isupper():
                sections['classes'].add(export)
            elif not any(export.endswith(suffix) for suffix in ('_CONSTANT', 'Type', 'Types', 'Config')):
                sections['functions'].add(export)

    def _add_all_exports(self, exports: Set[str], section: Section):
        """Add __all__ export declaration."""
        # Filter out special names and sort
        public_exports = sorted(export for export in exports if export != '__all__')

        if public_exports:
            section.add("__all__ = [")
            for export in public_exports:
                section.add(f'    "{export}",')
            section.add("]")

    def _combine_sections(self, sections: Dict[str, Section]) -> str:
        """Combine sections into final content."""
        parts = []

        # Order of sections
        section_order = [
            'docstring',
            'imports',
            'classes',
            'functions',
            'constants',
            'type_definitions',
            'variables',
            'exports'
        ]

        for name in section_order:
            if name in sections:  # Only process sections that exist
                section = sections[name]
                if not section.is_empty():
                    formatted = section.format()
                    if formatted:
                        parts.append(formatted)

        return "\n".join(parts)
