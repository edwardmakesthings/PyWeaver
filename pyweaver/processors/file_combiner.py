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
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pyweaver.common.base import BaseProcessor, ProcessorResult, ProcessorProgress
from pyweaver.common.tracking import TrackerType
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, ValidationError, StateError
)
from pyweaver.config.path import PathConfig
from pyweaver.utils.patterns import PatternMatcher
from pyweaver.processors._impl._file_combiner import FileCombinerImpl

logger = logging.getLogger(__name__)

class ContentMode(Enum):
    """Processing modes for file content.

    This enum defines how file content should be processed during combining.
    Different modes allow for varying levels of content transformation.
    """
    FULL = "full"            # Keep all content as is
    NO_COMMENTS = "no_comments"      # Remove comments only
    NO_DOCSTRINGS = "no_docstrings"  # Remove docstrings only
    MINIMAL = "minimal"      # Remove both comments and docstrings

@dataclass
class SectionConfig:
    """Configuration for file sections in combined output.

    This class defines how individual file sections should be formatted
    in the combined output, including headers, footers, and formatting rules.

    Attributes:
        enabled: Whether section formatting is enabled
        header_template: Template for section headers
        footer_template: Template for section footers
        include_empty_lines: Whether to keep empty lines
        remove_trailing_whitespace: Whether to trim line endings
    """
    enabled: bool = True
    header_template: str = "#" * 80 + "\n# Source: {path}\n" + "#" * 80
    footer_template: str = "\n"
    include_empty_lines: bool = True
    remove_trailing_whitespace: bool = True

    def format_header(self, path: Path, **kwargs) -> str:
        """Format section header for a file.

        Args:
            path: Path to the file
            **kwargs: Additional template variables

        Returns:
            Formatted header string
        """
        try:
            return self.header_template.format(
                path=path,
                type=path.suffix.lstrip('.'),
                **kwargs
            )
        except Exception as e:
            raise ValidationError(
                f"Failed to format header template: {e}",
                details={"template": self.header_template, "path": str(path)}
            ) from e

    def format_footer(self, path: Path, **kwargs) -> str:
        """Format section footer for a file.

        Args:
            path: Path to the file
            **kwargs: Additional template variables

        Returns:
            Formatted footer string
        """
        try:
            return self.footer_template.format(
                path=path,
                type=path.suffix.lstrip('.'),
                **kwargs
            )
        except Exception as e:
            raise ValidationError(
                f"Failed to format footer template: {e}",
                details={"template": self.footer_template, "path": str(path)}
            ) from e

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

@dataclass
class CombinerConfig(PathConfig):
    """Configuration for file combining operations.

    This class extends the base PathConfig with settings specific to
    file combining operations, providing comprehensive configuration
    options.

    Attributes:
        output_file: Where to write combined output
        content_mode: How to process file content
        file_patterns: Patterns for files to include
        generate_tree: Whether to generate directory tree
        section_config: Configuration for section formatting
        encoding: File encoding to use
        include_sections: Specific sections to include
        exclude_sections: Sections to exclude
        line_ending: Line ending standardization
        add_file_stats: Whether to add file statistics
    """
    output_file: Path
    content_mode: ContentMode = ContentMode.FULL
    file_patterns: List[str] = field(default_factory=lambda: ["*.py"])
    generate_tree: bool = False
    section_config: SectionConfig = field(default_factory=SectionConfig)
    encoding: str = "utf-8"
    include_sections: Optional[List[str]] = None
    exclude_sections: Optional[List[str]] = None
    line_ending: str = "\n"
    add_file_stats: bool = False
    include_structure: bool = False
    structure_tree_format: bool = True
    include_empty_dirs: bool = False

    def validate_patterns(self) -> None:
        """Validate file patterns configuration.

        This method ensures all file patterns are valid and properly formatted.

        Raises:
            ValidationError: If patterns are invalid
        """
        try:
            pattern_matcher = PatternMatcher()
            for pattern in self.file_patterns:
                if not pattern or not isinstance(pattern, str):
                    raise ValueError(f"Invalid pattern: {pattern}")

                # Try to use pattern to validate format
                if not pattern_matcher.matches_path_pattern("test.txt", pattern):
                    logger.debug("Pattern validation passed: %s", pattern)

        except Exception as e:
            raise ValidationError(
                "Invalid file patterns configuration",
                details={"patterns": self.file_patterns},
                original_error=e
            ) from e

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
        remove_comments: bool = False,
        remove_docstrings: bool = False,
        generate_tree: bool = False,
        section_config: Optional[SectionConfig] = None,
        **kwargs
    ):
        """Initialize the file combiner processor.

        Args:
            root_dir: Root directory to scan
            output_file: Where to write combined output
            patterns: File patterns to match
            remove_comments: Whether to strip comments
            remove_docstrings: Whether to strip docstrings
            generate_tree: Whether to generate directory tree
            section_config: Custom section formatting
            **kwargs: Additional configuration options

        Raises:
            ValidationError: If configuration is invalid
            FileError: If required files cannot be accessed
        """
        try:
            # Determine content mode from flags
            mode = ContentMode.FULL
            if remove_comments and remove_docstrings:
                mode = ContentMode.MINIMAL
            elif remove_comments:
                mode = ContentMode.NO_COMMENTS
            elif remove_docstrings:
                mode = ContentMode.NO_DOCSTRINGS

            # Create configuration
            self.config = CombinerConfig(
                output_file=Path(output_file),
                content_mode=mode,
                file_patterns=patterns or ["*.py"],
                generate_tree=generate_tree,
                section_config=section_config or SectionConfig(),
                **kwargs
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

    def preview(self) -> str:
        """Preview combined output without writing files.

        This method performs a dry run of the processing operation,
        returning the content that would be written to the output file.

        Returns:
            Combined content preview

        Raises:
            ProcessingError: If preview generation fails
        """
        try:
            self._ensure_impl()
            return self._impl.preview_output()

        except Exception as e:
            context = ErrorContext(
                operation="preview",
                error_code=ErrorCode.PROCESS_EXECUTION
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
            for pattern in self.config.ignore_patterns
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

def combine_files(
    root_dir: str | Path,
    output_file: str | Path,
    patterns: Optional[List[str]] = None,
    remove_comments: bool = False,
    remove_docstrings: bool = False,
    **kwargs
) -> ProcessorResult:
    """Convenience function for quick file combining.

    This function provides a simplified interface for common file combining
    operations without needing to manage a processor instance directly.

    Args:
        root_dir: Directory to scan
        output_file: Where to write output
        patterns: File patterns to match
        remove_comments: Whether to remove comments
        remove_docstrings: Whether to remove docstrings
        **kwargs: Additional processor options

    Returns:
        ProcessorResult with operation status

    Example:
        ```python
        result = combine_files(
            "src",
            "output.txt",
            patterns=["*.py"],
            remove_comments=True
        )
        print(f"Combined {result.files_processed} files")
        ```
    """
    processor = FileCombinerProcessor(
        root_dir=root_dir,
        output_file=output_file,
        patterns=patterns,
        remove_comments=remove_comments,
        remove_docstrings=remove_docstrings,
        **kwargs
    )
    return processor.process()