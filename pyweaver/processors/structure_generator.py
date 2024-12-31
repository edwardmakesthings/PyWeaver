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

The module provides both a comprehensive StructurePrinter class for fine-grained control
and a simple generate_structure() convenience function for common use cases.

Example:
    ```python
    # Using convenience function
    structure = generate_structure("src", style="tree", show_size=True)
    print(structure)

    # Using full printer for more control
    printer = StructurePrinter(
        "src",
        options=StructureOptions(
            style=ListingStyle.TREE,
            show_size=True,
            max_depth=3
        )
    )
    structure = printer.generate_structure()
    print(structure)
    ```

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

from pyweaver.common.enums import ListingStyle
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)

logger = logging.getLogger(__name__)

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

class TreeChars(str, Enum):
    """Characters used for tree-style output.

    This enum defines the characters used for tree-style output
    to represent directory structures with proper indentation.
    """
    PIPE = "│"   # U+2502
    TEE  = "├──" # U+251C U+2500 U+2500
    LAST = "└──" # U+2514 U+2500 U+2500
    SPACE = "    "

    def __str__(self) -> str:
        """Return the actual character value."""
        return self.value

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
        try:
            self.root_dir = Path(root_dir).resolve()
            if not self.root_dir.exists():
                raise FileError(
                    f"Directory does not exist: {root_dir}",
                    path=self.root_dir,
                    operation="init"
                )

            self.options = options or StructureOptions()

            # Ensure UTF-8 encoding for tree characters
            self._ensure_encoding()

            # Initialize tracking collections
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
        except Exception as e:
            raise ProcessingError(
                f"Failed to initialize structure printer: {e}",
                operation="init",
                path=root_dir
            ) from e

    def _ensure_encoding(self) -> None:
        """Ensure proper encoding for tree characters."""
        import sys
        if sys.stdout.encoding.lower() != 'utf-8':
            import codecs
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)

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

            # Reset counters before scan
            self._total_files = 0
            self._total_dirs = 0
            self._total_size = 0
            self._entries.clear()

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

    def write(self, output_file: Path | str) -> None:
        """Write structure to file.

        This method generates the structure and writes it to the specified file.
        It handles directory creation and provides proper error context.

        Args:
            output_file: Path to write structure to

        Raises:
            FileError: If file cannot be written
            ProcessingError: If structure generation fails
        """
        try:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate structure and write with explicit UTF-8 encoding
            content = self.generate_structure()
            output_path.write_text(content, encoding='utf-8', newline='\n')

            logger.info("Wrote structure to %s", output_path)

        except Exception as e:
            context = ErrorContext(
                operation="write_structure",
                error_code=ErrorCode.FILE_WRITE,
                path=output_file
            )
            raise FileError(
                f"Failed to write structure file: {e}",
                path=Path(output_file),
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

            try:
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
                            try:
                                stat = item.stat()
                                info.size = stat.st_size
                                info.modified = stat.st_mtime
                                self._total_files += 1
                                self._total_size += info.size
                            except (OSError, PermissionError) as e:
                                info.error = f"Cannot access file: {e}"
                        else:
                            self._total_dirs += 1

                        self._entries[item] = info

                        # Recurse into directories
                        if info.is_dir:
                            try:
                                self._scan_directory(item, depth + 1)
                            except (OSError, PermissionError) as e:
                                info.error = f"Cannot access directory: {e}"

                    except Exception as e:
                        error = f"Error processing {item}: {str(e)}"
                        self._errors.append(error)
                        logger.warning(error)

            except (OSError, PermissionError) as e:
                raise FileError(
                    f"Cannot access directory: {e}",
                    path=path,
                    operation="scan_directory"
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
        indent = TreeChars.SPACE.value * indent_level
        # Ensure we use the actual unicode characters, not their names
        line_prefix = f"{indent}{TreeChars.LAST.value if is_last else TreeChars.TEE.value}"

        # Format entry name with optional information
        entry_text = self._format_entry_name(entry)
        lines.append(f"{prefix}{line_prefix} {entry_text}")

        # Process children if directory
        if entry.is_dir:
            children = self._get_sorted_entries(entry.path)
            child_indent = (TreeChars.SPACE.value if is_last else
                        f"{TreeChars.PIPE.value}   ")

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
                rel_path_str = str(rel_path).replace('\\', '/')
                entry_text = self._format_entry_name(entry)
                lines.append(f"{rel_path_str} {entry_text}")
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
        indent = str(TreeChars.SPACE) * indent_level

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

    def _format_date(self, timestamp: float) -> str:
        """Format date according to configuration."""
        try:
            return time.strftime(
                self.options.date_format,
                time.localtime(timestamp)
            )
        except Exception as e:
            logger.warning("Date formatting failed: %s", e)
            return str(timestamp)

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
            if entry.path.parent.resolve() == directory.resolve()
        ]

        # Create sort key function based on configuration
        key_funcs = {
            SortOrder.ALPHA: lambda e: str(e.path).lower(),
            SortOrder.ALPHA_DIRS_FIRST: lambda e: (not e.is_dir, str(e.path).lower()),
            SortOrder.ALPHA_FILES_FIRST: lambda e: (e.is_dir, str(e.path).lower()),
            SortOrder.MODIFIED: lambda e: e.modified,
            SortOrder.SIZE: lambda e: (e.size if not e.is_dir else 0)
        }

        sort_key = key_funcs.get(self.options.sort_order, key_funcs[SortOrder.ALPHA])
        return sorted(entries, key=sort_key)

    def _should_ignore(self, path: Path) -> bool:
        """Check if a path should be ignored.

        This method applies the configured ignore and include patterns
        to determine if a path should be excluded from the listing.

        Args:
            path: Path to check

        Returns:
            True if path should be ignored
        """
        relative_path = str(path.resolve().relative_to(self.root_dir.resolve()))

        # Check include patterns first if specified
        if self.options.include_patterns:
            included = any(
                path.match(pattern) or relative_path.startswith(pattern.rstrip('*'))
                for pattern in self.options.include_patterns
            )
            if not included:
                return True

        # Check ignore patterns
        return any(
            path.match(pattern) or relative_path.startswith(pattern.rstrip('*'))
            for pattern in self.options.ignore_patterns
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the processed structure.

        This method provides detailed statistics about the processed
        directory structure, including counts, sizes, and timing.

        Returns:
            Dictionary of statistics
        """
        stats = {
            "total_files": self._total_files,
            "total_dirs": self._total_dirs,
            "total_size": self._total_size,
            "total_entries": len(self._entries),
            "processing_time": self._end_time - self._start_time if self._end_time else 0,
            "error_count": len(self._errors)
        }

        # Reset counters after reading
        self._total_files = 0
        self._total_dirs = 0
        self._total_size = 0

        return stats

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

def generate_structure(
    input_dir: str | Path,
    output_file: Optional[str | Path] = None,
    print_output: bool = False,
    print_only: bool = False,
    style: str = "tree",
    show_size: bool = False,
    show_date: bool = False,
    max_depth: Optional[int] = None,
    ignore_patterns: Optional[Set[str]] = None,
    include_patterns: Optional[Set[str]] = None,
    sort_type: str = "alpha",
    show_permissions: bool = False,
    size_format: str = "auto",
    date_format: str = "%Y-%m-%d %H:%M",
    max_name_length: Optional[int] = None,
    include_empty: bool = False
) -> str:
    """Generate a formatted directory structure listing.

    This convenience function provides a simpler interface to generate directory
    structure listings with options for output control.

    Args:
        input_dir: Root directory to analyze
        output_file: Path to save the structure output. If None, output is only returned
                    as a string
        print_output: If True, print the structure to console
        print_only: If True, generate the structure but don't write to file even if
                     output_file is specified
        style: Output style ("tree", "flat", "indented", "markdown")
        show_size: Whether to show file sizes
        show_date: Whether to show modification dates
        max_depth: Maximum directory depth to show
        ignore_patterns: Set of glob patterns for files/directories to ignore
        include_patterns: Set of glob patterns to explicitly include
        sort_type: Sort order ("alpha", "alpha_dirs_first", "alpha_files_first",
                             "modified", "size")
        show_permissions: Whether to show file permissions
        size_format: How to format file sizes
        date_format: How to format dates
        max_name_length: Maximum length for file names
        include_empty: Whether to include empty directories

    Returns:
        Formatted structure representation

    Raises:
        ProcessingError: If structure generation fails
        ValueError: If invalid style or sort type specified
        FileError: If file output fails

    Example:
        ```python
        # Just return the structure
        structure = generate_structure("src")

        # Save to file and show on console
        structure = generate_structure(
            "src",
            output_file="docs/structure.md",
            print_output=True,
            style="markdown"
        )

        # Preview what would be written but don't actually write
        structure = generate_structure(
            "src",
            output_file="docs/structure.md",
            print_output=True,
            print_only=True
        )
        ```
    """
    try:
        # Validate and convert style
        try:
            listing_style = ListingStyle(style.lower())
        except ValueError as e:
            valid_styles = ", ".join(s.value for s in ListingStyle)
            raise ValueError(
                f"Invalid style '{style}'. Must be one of: {valid_styles}"
            ) from e

        # Validate and convert sort order
        try:
            sort_order = SortOrder(sort_type.lower())
        except ValueError as e:
            valid_sorts = ", ".join(s.value for s in SortOrder)
            raise ValueError(
                f"Invalid sort type '{sort_type}'. Must be one of: {valid_sorts}"
            ) from e

        # Create options with provided settings
        options = StructureOptions(
            style=listing_style,
            sort_order=sort_order,
            show_size=show_size,
            show_date=show_date,
            max_depth=max_depth,
            ignore_patterns=ignore_patterns or set(),
            include_patterns=include_patterns or set(),
            show_permissions=show_permissions,
            size_format=size_format,
            date_format=date_format,
            max_name_length=max_name_length,
            include_empty=include_empty
        )

        # Generate structure
        printer = StructurePrinter(input_dir, options)
        structure = printer.generate_structure()

        # Handle console output if requested
        if print_output:
            print("\nDirectory Structure:")
            print("-" * 80)
            print(structure)
            print("-" * 80)

        # Handle file output if requested and not preview
        if output_file and not print_only:
            try:
                output_path = Path(output_file)
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                except OSError as e:
                    # If it's read-only, you'll get an OSError here
                    context = ErrorContext(
                        operation="create_directory",
                        error_code=ErrorCode.FILE_PERMISSION,
                        path=output_file
                    )
                    raise FileError(
                        f"Do not have permission to create directory: {e}",
                        path=output_path,
                        context=context,
                        original_error=e
                    ) from e

                try:
                    output_path.write_text(structure, encoding="utf-8")
                except OSError as e:
                    # If directory is read-only, writing fails here
                    context = ErrorContext(
                        operation="write_structure",
                        error_code=ErrorCode.FILE_PERMISSION,
                        path=output_file
                    )
                    raise FileError(
                        f"Do not have permission to write to directory: {e}",
                        path=output_path,
                        context=context,
                        original_error=e
                    ) from e

                logger.info("Wrote structure to %s", output_path)

            except Exception as e:
                context = ErrorContext(
                    operation="write_structure",
                    error_code=ErrorCode.FILE_WRITE,
                    path=output_file
                )
                raise FileError(
                    f"Failed to write structure file: {e}",
                    path=output_path,
                    context=context,
                    original_error=e
                ) from e

        return structure

    except Exception as e:
        if isinstance(e, (ValueError, FileError)):
            raise  # Re-raise validation and file errors directly

        context = ErrorContext(
            operation="generate_structure",
            error_code=ErrorCode.PROCESS_EXECUTION,
            path=input_dir,
            details={
                "style": style,
                "sort_type": sort_type,
                "output_file": str(output_file) if output_file else None,
                "preview_only": print_only
            }
        )
        raise ProcessingError(
            f"Failed to generate structure: {str(e)}",
            context=context,
            original_error=e
        ) from e