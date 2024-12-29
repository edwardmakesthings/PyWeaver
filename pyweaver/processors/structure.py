"""File structure printing utilities.

This module provides sophisticated tools for generating directory structure listings
with configurable formatting and filtering options. The implementation supports both
tree-style and flat file listings, with careful handling of large directory structures
and memory-efficient processing.

The structure printer is designed to handle various use cases such as:
- Documentation generation
- Project structure visualization
- Directory comparison
- File system analysis
- Structure validation

The implementation prioritizes readability and flexibility while maintaining
performance for large directory structures.

Path: pyweaver/processors/structure.py
"""
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import time
from typing import List, Set, Any, Optional, Dict

from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)

logger = logging.getLogger(__name__)

class ListingStyle(Enum):
    """Output style for structure listings.

    This enum defines different ways to format the directory structure,
    allowing for various visualization needs.
    """
    TREE = "tree"          # Traditional tree with branches
    FLAT = "flat"          # Flat list of paths
    INDENTED = "indented"  # Indented list without branches
    MARKDOWN = "markdown"  # Markdown-compatible list

class SortOrder(Enum):
    """Sort order for directory entries.

    This enum defines different ways to order directory entries in the output,
    supporting various organizational needs.
    """
    ALPHA = "alpha"        # Alphabetical by name
    ALPHA_DIRS_FIRST = "alpha_dirs_first"  # Directories, then files
    ALPHA_FILES_FIRST = "alpha_files_first"  # Files, then directories
    MODIFIED = "modified"  # By modification time
    SIZE = "size"         # By file size

@dataclass
class StructureOptions:
    """Configuration for structure printing.

    This class centralizes all configuration options for generating
    directory structure listings, providing fine-grained control over
    the output format and content.

    Attributes:
        include_empty: Whether to include empty directories
        style: Output style to use
        sort_order: How to sort directory entries
        max_depth: Maximum directory depth to show
        show_size: Whether to show file sizes
        show_date: Whether to show modification dates
        show_permissions: Whether to show file permissions
        ignore_patterns: Patterns for files/directories to ignore
        include_patterns: Patterns to explicitly include
        size_format: How to format file sizes
        date_format: How to format dates
        max_name_length: Maximum length for file names
    """
    include_empty: bool = False
    style: ListingStyle = ListingStyle.TREE
    sort_order: SortOrder = SortOrder.ALPHA
    max_depth: Optional[int] = None
    show_size: bool = False
    show_date: bool = False
    show_permissions: bool = False
    ignore_patterns: Set[str] = field(default_factory=lambda: {
        '__pycache__',
        '.git',
        '.pytest_cache',
        '.vscode',
        '.idea',
        '*.pyc',
        '*.pyo',
        '*.pyd',
        '.DS_Store',
        '.venv',
        'node_modules'
    })
    include_patterns: Set[str] = field(default_factory=set)
    size_format: str = "auto"  # "bytes", "kb", "mb", "auto"
    date_format: str = "%Y-%m-%d %H:%M"
    max_name_length: Optional[int] = None

@dataclass
class EntryInfo:
    """Information about a directory entry.

    This class tracks information about individual files and directories
    for use in generating the structure listing.

    Attributes:
        path: Path to the entry
        is_dir: Whether entry is a directory
        size: File size in bytes
        modified: Modification timestamp
        error: Optional error message if access failed
    """
    path: Path
    is_dir: bool
    size: int = 0
    modified: float = field(default_factory=time.time)
    error: Optional[str] = None

class StructurePrinter:
    """Generates formatted directory structure listings.

    This class provides sophisticated directory structure visualization with
    support for various output formats, sorting options, and filtering rules.
    It handles large directory structures efficiently and provides detailed
    error reporting.

    The printer supports:
    - Multiple output formats (tree, flat, etc.)
    - Configurable sorting and filtering
    - Size and date information
    - Memory-efficient processing
    - Detailed error tracking

    Example:
        ```python
        # Create printer with custom options
        options = StructureOptions(
            style=ListingStyle.TREE,
            show_size=True,
            max_depth=3
        )
        printer = StructurePrinter("src", options)

        # Generate structure
        print(printer.generate_structure())

        # Get statistics
        stats = printer.get_statistics()
        print(f"Processed {stats['total_files']} files")

        # Check for errors
        for error in printer.get_errors():
            print(f"Error: {error}")
        ```
    """

    def __init__(
        self,
        root_dir: Path | str,
        options: Optional[StructureOptions] = None
    ):
        """Initialize printer with root directory and options.

        Args:
            root_dir: Directory to analyze
            options: Configuration options
        """
        self.root_dir = Path(root_dir)
        self.options = options or StructureOptions()

        # Tracking collections
        self._entries: Dict[Path, EntryInfo] = {}
        self._errors: List[str] = []

        # Statistics
        self._total_files = 0
        self._total_dirs = 0
        self._total_size = 0
        self._start_time = 0
        self._end_time = 0

        logger.debug(
            "Initialized StructurePrinter for %s (%s style)",
            self.root_dir, self.options.style.value
        )

    def generate_structure(self) -> str:
        """Generate formatted directory structure.

        This method processes the directory tree and generates a formatted
        representation according to the configured options.

        Returns:
            Formatted structure string

        Raises:
            ProcessingError: If structure generation fails
        """
        try:
            self._start_time = time.time()

            # Scan directory structure
            self._scan_directory(self.root_dir)

            # Generate formatted output
            if self.options.style == ListingStyle.TREE:
                output = self._generate_tree()
            elif self.options.style == ListingStyle.FLAT:
                output = self._generate_flat()
            elif self.options.style == ListingStyle.INDENTED:
                output = self._generate_indented()
            else:  # ListingStyle.MARKDOWN
                output = self._generate_markdown()

            self._end_time = time.time()

            logger.info(
                "Generated structure for %s (%d files, %d dirs)",
                self.root_dir, self._total_files, self._total_dirs
            )

            return output

        except Exception as e:
            context = ErrorContext(
                operation="generate_structure",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=self.root_dir,
                details={"style": self.options.style.value}
            )
            raise ProcessingError(
                "Failed to generate structure",
                context=context,
                original_error=e
            ) from e

    def _scan_directory(self, path: Path, depth: int = 0) -> None:
        """Scan a directory and collect entry information.

        This method recursively scans the directory tree, collecting
        information about files and directories while respecting
        configured limits and filters.

        Args:
            path: Directory to scan
            depth: Current recursion depth

        Raises:
            FileError: If directory cannot be accessed
        """
        try:
            # Check depth limit
            if (self.options.max_depth is not None and
                depth > self.options.max_depth):
                return

            # Process directory entries
            for item in path.iterdir():
                try:
                    # Check ignore patterns
                    if self._should_ignore(item):
                        continue

                    # Collect entry information
                    info = EntryInfo(
                        path=item,
                        is_dir=item.is_dir()
                    )

                    if not info.is_dir:
                        # Collect file information
                        info.size = item.stat().st_size
                        info.modified = item.stat().st_mtime
                        self._total_files += 1
                        self._total_size += info.size
                    else:
                        self._total_dirs += 1

                    self._entries[item] = info

                    # Recurse into directories
                    if info.is_dir:
                        self._scan_directory(item, depth + 1)

                except Exception as e:
                    error = f"Error processing {item}: {str(e)}"
                    self._errors.append(error)
                    logger.warning(error)

                    # Add error entry
                    self._entries[item] = EntryInfo(
                        path=item,
                        is_dir=item.is_dir(),
                        error=str(e)
                    )

        except Exception as e:
            context = ErrorContext(
                operation="scan_directory",
                error_code=ErrorCode.FILE_READ,
                path=path,
                details={"depth": depth}
            )
            raise FileError(
                f"Failed to scan directory: {str(e)}",
                path=path,
                context=context,
                original_error=e
            ) from e

    def _generate_tree(self) -> str:
        """Generate tree-style structure listing.

        This method creates a traditional tree visualization with
        branch characters and proper indentation.

        Returns:
            Tree-style structure string
        """
        lines = []
        root_items = self._get_sorted_entries(self.root_dir)

        for i, entry in enumerate(root_items):
            is_last = i == len(root_items) - 1
            prefix = "" if i == 0 else "\n"

            # Add entry and its children
            lines.extend(self._format_tree_entry(
                entry=entry,
                prefix=prefix,
                is_last=is_last,
                indent_level=0
            ))

        return "".join(lines)

    def _format_tree_entry(
        self,
        entry: EntryInfo,
        prefix: str,
        is_last: bool,
        indent_level: int
    ) -> List[str]:
        """Format a single entry in tree style.

        This method handles the formatting of individual entries in the
        tree structure, including proper indentation and branch characters.

        Args:
            entry: Entry to format
            prefix: Prefix string (usually newline)
            is_last: Whether this is the last entry at this level
            indent_level: Current indentation level

        Returns:
            List of formatted lines
        """
        lines = []
        indent = "    " * indent_level
        connector = "└── " if is_last else "├── "

        # Format entry name with optional information
        entry_text = self._format_entry_name(entry)
        lines.append(f"{prefix}{indent}{connector}{entry_text}")

        # Process children if directory
        if entry.is_dir:
            children = self._get_sorted_entries(entry.path)
            child_indent = indent + ("    " if is_last else "│   ")

            for i, child in enumerate(children):
                child_lines = self._format_tree_entry(
                    entry=child,
                    prefix="\n",
                    is_last=i == len(children) - 1,
                    indent_level=indent_level + 1
                )
                lines.extend(child_lines)

        return lines

    def _generate_flat(self) -> str:
        """Generate flat structure listing.

        This method creates a simple list of paths relative to the
        root directory.

        Returns:
            Flat structure string
        """
        lines = []

        for entry in sorted(
            self._entries.values(),
            key=lambda e: str(e.path)
        ):
            try:
                rel_path = entry.path.relative_to(self.root_dir)
                entry_text = self._format_entry_name(entry)
                lines.append(f"{rel_path} {entry_text}")
            except ValueError:
                continue

        return "\n".join(lines)

    def _generate_indented(self) -> str:
        """Generate indented structure listing.

        This method creates an indented list without branch characters,
        suitable for simpler visualization needs.

        Returns:
            Indented structure string
        """
        lines = []
        root_items = self._get_sorted_entries(self.root_dir)

        for entry in root_items:
            lines.extend(self._format_indented_entry(
                entry=entry,
                indent_level=0
            ))

        return "\n".join(lines)

    def _generate_markdown(self) -> str:
        """Generate Markdown-compatible structure listing.

        This method creates a structure listing using Markdown list
        syntax, suitable for documentation.

        Returns:
            Markdown structure string
        """
        lines = []
        root_items = self._get_sorted_entries(self.root_dir)

        for entry in root_items:
            lines.extend(self._format_markdown_entry(
                entry=entry,
                indent_level=0
            ))

        return "\n".join(lines)

    def _format_entry_name(self, entry: EntryInfo) -> str:
        """Format an entry's name with optional information.

        This method handles the formatting of entry names including
        any configured additional information like sizes and dates.

        Args:
            entry: Entry to format

        Returns:
            Formatted entry string
        """
        parts = []
        name = entry.path.name

        # Truncate name if configured
        if (self.options.max_name_length and
            len(name) > self.options.max_name_length):
            name = name[:self.options.max_name_length-3] + "..."

        parts.append(name)

        # Add size if configured
        if self.options.show_size and not entry.is_dir:
            size_str = self._format_size(entry.size)
            parts.append(f"({size_str})")

        # Add date if configured
        if self.options.show_date:
            date_str = time.strftime(
                self.options.date_format,
                time.localtime(entry.modified)
            )
            parts.append(f"[{date_str}]")

        # Add error if present
        if entry.error:
            parts.append(f"[Error: {entry.error}]")

        return " ".join(parts)

    def _format_indented_entry(
        self,
        entry: EntryInfo,
        indent_level: int
    ) -> List[str]:
        """Format an entry for indented style output.

        This method handles the formatting of entries in the indented style,
        which uses spaces for hierarchy without branch characters.

        Args:
            entry: Entry to format
            indent_level: Current indentation level

        Returns:
            List of formatted lines
        """
        lines = []
        indent = "    " * indent_level

        # Format current entry
        entry_text = self._format_entry_name(entry)
        lines.append(f"{indent}{entry_text}")

        # Process children if directory
        if entry.is_dir:
            children = self._get_sorted_entries(entry.path)
            for child in children:
                lines.extend(self._format_indented_entry(
                    entry=child,
                    indent_level=indent_level + 1
                ))

        return lines

    def _format_markdown_entry(
        self,
        entry: EntryInfo,
        indent_level: int
    ) -> List[str]:
        """Format an entry for Markdown-style output.

        This method handles the formatting of entries using Markdown list
        syntax, making the output suitable for documentation.

        Args:
            entry: Entry to format
            indent_level: Current indentation level

        Returns:
            List of formatted lines
        """
        lines = []
        indent = "  " * indent_level  # Markdown typically uses 2 spaces

        # Format current entry
        entry_text = self._format_entry_name(entry)
        lines.append(f"{indent}- {entry_text}")

        # Process children if directory
        if entry.is_dir:
            children = self._get_sorted_entries(entry.path)
            for child in children:
                lines.extend(self._format_markdown_entry(
                    entry=child,
                    indent_level=indent_level + 1
                ))

        return lines

    def _get_sorted_entries(self, directory: Path) -> List[EntryInfo]:
        """Get sorted list of entries for a directory.

        This method retrieves and sorts directory entries according to
        the configured sort order, handling various sorting strategies.

        Args:
            directory: Directory to get entries for

        Returns:
            Sorted list of entry information
        """
        # Collect entries for this directory
        entries = [
            entry for entry in self._entries.values()
            if entry.path.parent == directory
        ]

        # Apply sorting based on configuration
        if self.options.sort_order == SortOrder.ALPHA:
            entries.sort(key=lambda e: str(e.path).lower())
        elif self.options.sort_order == SortOrder.ALPHA_DIRS_FIRST:
            entries.sort(key=lambda e: (not e.is_dir, str(e.path).lower()))
        elif self.options.sort_order == SortOrder.ALPHA_FILES_FIRST:
            entries.sort(key=lambda e: (e.is_dir, str(e.path).lower()))
        elif self.options.sort_order == SortOrder.MODIFIED:
            entries.sort(key=lambda e: e.modified)
        elif self.options.sort_order == SortOrder.SIZE:
            entries.sort(key=lambda e: (e.size if not e.is_dir else 0))

        return entries

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        This method applies the configured ignore and include patterns
        to determine if a path should be excluded from the listing.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        # Check include patterns first if specified
        if self.options.include_patterns:
            included = any(
                path.match(pattern)
                for pattern in self.options.include_patterns
            )
            if not included:
                return True

        # Check ignore patterns
        return any(
            path.match(pattern)
            for pattern in self.options.ignore_patterns
        )

    def _format_size(self, size: int) -> str:
        """Format a file size according to configuration.

        This method converts file sizes to human-readable format based
        on the configured size format option.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        if self.options.size_format == "bytes":
            return f"{size:,} B"

        # Convert to appropriate unit
        units = ["B", "KB", "MB", "GB", "TB"]
        unit_index = 0

        if self.options.size_format == "auto":
            while size >= 1024 and unit_index < len(units) - 1:
                size /= 1024
                unit_index += 1
        else:
            # Convert to specific unit
            target_unit = self.options.size_format.upper()
            while unit_index < len(units) - 1 and units[unit_index] != target_unit:
                size /= 1024
                unit_index += 1

        return f"{size:,.1f} {units[unit_index]}"

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the processed structure.

        This method provides detailed statistics about the processed
        directory structure, including counts, sizes, and timing.

        Returns:
            Dictionary of statistics
        """
        return {
            "total_files": self._total_files,
            "total_dirs": self._total_dirs,
            "total_size": self._total_size,
            "total_entries": len(self._entries),
            "processing_time": self._end_time - self._start_time,
            "error_count": len(self._errors)
        }

    def get_errors(self) -> List[str]:
        """Get list of errors encountered during processing.

        Returns:
            List of error messages
        """
        return self._errors.copy()

    def __repr__(self) -> str:
        """Get string representation of printer state."""
        return (
            f"StructurePrinter("
            f"root={self.root_dir}, "
            f"style={self.options.style.value}, "
            f"files={self._total_files}, "
            f"dirs={self._total_dirs})"
        )
