"""Private implementation of base processor functionality.

Provides internal implementations of file processing operations
including file walking, pattern matching, and result generation.

Path: tools/project_tools/common/_impl/_processor.py
"""

from pathlib import Path
from typing import Dict, Iterator, List, Set, Tuple, Optional
import logging

from ..types import Pattern, GeneratorResult

logger = logging.getLogger(__name__)

def walk_directory(
    path: Path,
    exclude_patterns: Set[Pattern],
    include_patterns: Optional[Set[Pattern]] = None
) -> Iterator[Tuple[Path, List[Path], List[Path]]]:
    """
    Walk directory yielding (current_path, dirs, files) tuples.

    Args:
        path: Root directory to walk
        exclude_patterns: Patterns to exclude
        include_patterns: Optional patterns to include (if None, include all)

    Yields:
        Tuple of (current path, list of directories, list of files)
    """
    def should_process(item_path: Path) -> bool:
        """Check if path should be processed."""
        try:
            rel_path = item_path.relative_to(path)
        except ValueError:
            return False

        # Check exclusions first
        for pattern in exclude_patterns:
            if pattern.matches(rel_path):
                logger.debug("Excluding %s (matched: %s)", rel_path, pattern.pattern)
                return False

        # Then check inclusions
        if include_patterns:
            return any(p.matches(rel_path) for p in include_patterns)

        return True

    # Process root directory
    root_files: List[Path] = []
    root_dirs: List[Path] = []

    # Collect immediate children
    for item in path.iterdir():
        if should_process(item):
            if item.is_file():
                root_files.append(item)
            elif item.is_dir():
                root_dirs.append(item)

    # Yield root if it has files or we're including empty dirs
    if root_files:
        yield path, root_dirs, root_files

    # Process each subdirectory
    for dir_path in sorted(root_dirs):
        current_files: List[Path] = []
        current_dirs: List[Path] = []

        try:
            for item in dir_path.iterdir():
                if should_process(item):
                    if item.is_file():
                        current_files.append(item)
                    elif item.is_dir():
                        current_dirs.append(item)
        except PermissionError:
            logger.warning("Permission denied: %s", dir_path)
            continue

        yield dir_path, current_dirs, current_files

        # Recurse into subdirectories
        for subdir in sorted(current_dirs):
            yield from walk_directory(subdir, exclude_patterns, include_patterns)

def format_result(
    processed: Dict[Path, str],
    errors: List[str],
    warnings: List[str]
) -> GeneratorResult:
    """Format processing results into GeneratorResult."""
    return GeneratorResult(
        success=len(errors) == 0,
        message=_format_result_message(len(processed), errors, warnings),
        files_processed=len(processed),
        files_written=len([f for f in processed if f.exists()]),
        errors=errors.copy(),
        warnings=warnings.copy()
    )

def _format_result_message(processed: int, errors: List[str], warnings: List[str]) -> str:
    """Format result message based on operation outcomes."""
    if errors:
        return f"Processing completed with {len(errors)} errors"
    elif warnings:
        return f"Processing completed with {len(warnings)} warnings"
    return f"Successfully processed {processed} files"
