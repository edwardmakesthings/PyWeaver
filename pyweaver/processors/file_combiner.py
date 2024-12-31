"""File combiner processor implementation.

This module provides functionality for combining multiple source files into a single
output file. It supports various content processing options, custom formatting rules,
and configurable organization. The implementation separates the public interface
from the private processing logic to maintain clean architecture while providing
powerful file combining capabilities.

Features include:
- Configurable content processing (comments, docstrings)
- Section-based organization
- Content transformation rules
- Progress tracking and reporting
- Preview functionality

Path: pyweaver/processors/file_combiner.py
"""
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from pyweaver.common.base import BaseProcessor, ProcessorResult, ProcessorProgress
from pyweaver.common.tracking import TrackerType
from pyweaver.common.enums import ListingStyle
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, StateError, FileError
)
from pyweaver.config.combiner import CombinerConfig, ContentMode, FileSectionConfig
from pyweaver.utils.patterns import PatternMatcher
from pyweaver.processors._impl._file_combiner import FileCombinerImpl

logger = logging.getLogger(__name__)

@dataclass
class CombinerProgress(ProcessorProgress):
    """Extended progress tracking for file combining.

    This class adds combiner-specific progress metrics to the base
    progress tracking functionality.

    Attributes:
        bytes_processed: Total bytes of content processed
        lines_processed: Total lines of content processed
        current_section: Currently processing section name
    """
    bytes_processed: int = 0
    lines_processed: int = 0
    current_section: Optional[str] = None

class FileCombinerProcessor(BaseProcessor):
    """Processor for combining multiple source files.

    This processor combines multiple source files into a single output file,
    with support for content processing, section organization, and various
    formatting options. It provides both immediate processing and preview
    functionality.

    The processor provides:
    - Content processing options
    - Section-based organization
    - Preview functionality
    - Progress tracking
    - Error recovery

    Example:
        ```python
        processor = FileCombinerProcessor(
            root_dir="src",
            output_file="combined.txt",
            patterns=["*.py", "*.md"],
            content_mode=ContentMode.NO_COMMENTS
        )

        # Preview changes
        print(processor.preview())

        # Process files
        result = processor.process()
        if result.success:
            print(f"Combined {result.files_processed} files")
            print(f"Processed {processor.progress.bytes_processed} bytes")
        ```
    """

    def __init__(
        self,
        root_dir: str | Path,
        output_file: str | Path,
        patterns: Optional[List[str]] = None,
        content_mode: ContentMode = ContentMode.FULL,
        remove_comments: bool = False,
        remove_docstrings: bool = False,
        generate_tree: bool = False,
        section_config: Optional[FileSectionConfig] = None,
    ):
        """Initialize the file combiner processor.

        Args:
            root_dir: Root directory to scan
            output_file: Where to write combined output
            patterns: File patterns to match
            content_mode: Mode for content processing
            remove_comments: Whether to strip comments (ignored if content_mode set)
            remove_docstrings: Whether to strip docstrings (ignored if content_mode set)
            generate_tree: Whether to generate directory tree
            section_config: Custom section formatting

        Raises:
            ValidationError: If configuration is invalid
            FileError: If required files cannot be accessed
        """
        try:
            # Only use flags if content_mode is FULL (default)
            if content_mode == ContentMode.FULL:
                if remove_comments and remove_docstrings:
                    content_mode = ContentMode.MINIMAL
                elif remove_comments:
                    content_mode = ContentMode.NO_COMMENTS
                elif remove_docstrings:
                    content_mode = ContentMode.NO_DOCSTRINGS

            # Create configuration
            self.config = CombinerConfig(
                output_file=Path(output_file),
                content_mode=content_mode,
                file_patterns=patterns or ["*.py"],
                include_structure=generate_tree,
                structure_format=ListingStyle.TREE,
                section_config=section_config or FileSectionConfig()
            )

            # Validate configuration
            self.config.validate_patterns()

            # Initialize base class
            super().__init__(config=self.config, tracker_type=TrackerType.FILES)

            # Initialize specialized components
            self.root_dir = Path(root_dir).resolve()
            self.pattern_matcher = PatternMatcher()
            self._impl: Optional[FileCombinerImpl] = None

            # Replace standard progress with specialized version
            self.progress = CombinerProgress()

            logger.info(
                "Initialized FileCombinerProcessor for %s -> %s",
                self.root_dir, self.config.output_file
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_combiner",
                error_code=ErrorCode.PROCESS_INIT,
                path=root_dir,
                details={
                    "output_file": str(output_file),
                    "patterns": patterns
                }
            )
            raise ProcessingError(
                "Failed to initialize file combiner",
                context=context,
                original_error=e
            ) from e

    def preview(self, output_file: Optional[Path | str] = None, print_preview: bool = False) -> str:
        """Preview combined output without writing production files.

        Args:
            output_file: Optional path to save preview content
            print_preview: If True, print preview to console

        Returns:
            Combined content preview

        Raises:
            ProcessingError: If preview generation fails
            FileError: If preview file cannot be written
        """
        try:
            self._ensure_impl()
            content = self._impl.preview_output()

            if print_preview:
                print("\nPreview of combined output:")
                print("-" * 80)
                print(content)
                print("-" * 80)

            if output_file:
                self.write(output_file)  # Uses BaseProcessor.write()

            return content

        except Exception as e:
            context = ErrorContext(
                operation="preview",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"output_file": str(output_file) if output_file else None}
            )
            raise ProcessingError(
                "Failed to generate preview",
                context=context,
                original_error=e
            ) from e

    def generate_tree(self) -> str:
        """Generate tree structure of included files.

        This method generates a visual representation of the file structure
        that will be combined.

        Returns:
            Tree structure representation

        Raises:
            ProcessingError: If tree generation fails
        """
        try:
            self._ensure_impl()
            return self._impl.generate_tree()

        except Exception as e:
            context = ErrorContext(
                operation="generate_tree",
                error_code=ErrorCode.PROCESS_EXECUTION
            )
            raise ProcessingError(
                "Failed to generate tree structure",
                context=context,
                original_error=e
            ) from e

    def _process_item(self, path: Path) -> None:
        """Process a single file for combining.

        This method processes an individual file, applying the configured
        content processing rules and adding it to the combined output.

        Args:
            path: Path to file to process

        Raises:
            ProcessingError: If processing fails
            FileError: If file operations fail
        """
        try:
            self._ensure_impl()
            self._impl.process_file(path)

            # Update progress
            self.progress.bytes_processed += path.stat().st_size
            with path.open() as f:
                self.progress.lines_processed += sum(1 for _ in f)

        except Exception as e:
            context = ErrorContext(
                operation="process_file",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=path
            )
            raise ProcessingError(
                f"Failed to process file: {path}",
                context=context,
                original_error=e
            ) from e

    def _should_process(self, path: Path) -> bool:
        """Check if a file should be processed.

        This method determines whether a file should be included in the
        combined output based on configuration settings.

        Args:
            path: Path to check

        Returns:
            True if file should be processed
        """
        if not path.is_file():
            return False

        rel_path = str(path.relative_to(self.root_dir))

        # Check file patterns
        matches_pattern = any(
            self.pattern_matcher.matches_path_pattern(path=rel_path, pattern=pattern)
            for pattern in self.config.file_patterns
        )

        if not matches_pattern:
            return False

        # Check ignore patterns
        return not any(
            self.pattern_matcher.matches_path_pattern(path=rel_path, pattern=pattern)
            for pattern in self.config.global_settings.ignore_patterns
        )

    def _ensure_impl(self) -> None:
        """Ensure implementation component is initialized.

        This method lazily initializes the implementation component
        when needed, ensuring proper resource management.

        Raises:
            StateError: If implementation cannot be initialized
        """
        if self._impl is None:
            try:
                self._impl = FileCombinerImpl(self.config, self.root_dir)
            except Exception as e:
                raise StateError(
                    "Failed to initialize implementation",
                    operation="init_impl",
                    original_error=e
                ) from e

    def _write_output(self, path: Path) -> None:
        """Write combined output to file.

        Implements BaseProcessor._write_output() for file combining.
        """
        try:
            content = self._impl.preview_output()
            path.write_text(content, encoding=self.config.encoding)
        except Exception as e:
            raise FileError(
                f"Failed to write combined output: {e}",
                path=path,
                operation="write_combined"
            ) from e

def combine_files(
    input_dir: str | Path,
    output_file: str | Path,
    print_output: bool = False,
    print_only: bool = False,
    patterns: Optional[List[str]] = None,
    content_mode: ContentMode = ContentMode.FULL,
    remove_comments: bool = False,
    remove_docstrings: bool = False,
    include_structure: bool = False
) -> ProcessorResult:
    """Convenience function for quick file combining.

    This function provides a simplified interface for common file combining
    operations without needing to manage a processor instance directly.

    Args:
        input_dir: Directory to scan
        output_file: Where to write output
        print_output: If True, print combined content to console
        print_only: If True, only print preview without writing final output
        patterns: File patterns to match
        content_mode: Mode for content processing
        remove_comments: Whether to remove comments
        remove_docstrings: Whether to remove docstrings
        include_structure: Whether to include directory structure

    Returns:
        ProcessorResult with operation status

    Example:
        ```python
        # Basic combining
        result = combine_files("src", "combined.txt", patterns=["*.py"])

        # Preview without writing
        result = combine_files(
            "src",
            "combined.txt",
            patterns=["*.py"],
            print_output=True,
            print_only=True
        )

        # Complex combining
        result = combine_files(
            "src",
            "combined.txt",
            patterns=["*.py", "*.ts"],
            content_mode=ContentMode.NO_COMMENTS,
            include_structure=True
        )
        ```
    """
    processor = FileCombinerProcessor(
        root_dir=input_dir,
        output_file=output_file,
        patterns=patterns,
        content_mode=content_mode,
        remove_comments=remove_comments,
        remove_docstrings=remove_docstrings,
        generate_tree=include_structure
    )

    try:
        # Process files
        result = processor.process()

        # Handle output options
        if print_output or print_only:
            processor.preview(print_preview=True)

        if not print_only:
            processor.write()  # Uses the configured output_file

        return result

    except Exception as e:
        return ProcessorResult(
            success=False,
            message=str(e),
            errors=[str(e)]
        )
