from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional
import logging

from pyweaver.common.enums import ListingStyle
from pyweaver.common.errors import ValidationError
from pyweaver.config.path import PathConfig
from pyweaver.utils.patterns import PatternMatcher

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
class FileSectionConfig:
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

    def format_header(self, path: Path, **kwargs: dict) -> str:
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

    def format_footer(self, path: Path, **kwargs: dict) -> str:
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
class CombinerConfig(PathConfig):
    """Configuration for file combining operations.

    This class extends PathConfig with settings specific to file combining operations,
    providing comprehensive configuration options for both file processing and
    structure generation.

    Attributes:
        output_file: Where to write combined output
        content_mode: How to process file content
        file_patterns: Patterns for files to include
        section_config: Configuration for section formatting
        encoding: File encoding to use
        include_sections: Specific sections to include
        exclude_sections: Sections to exclude
        line_ending: Line ending standardization
        add_file_stats: Whether to add file statistics
        include_structure: Whether to include directory structure in output
        structure_format: Format for directory structure (if included)
        include_empty_dirs: Whether to include empty directories in structure
    """
    output_file: Path
    content_mode: ContentMode = ContentMode.FULL
    file_patterns: List[str] = field(default_factory=lambda: ["*.py"])
    section_config: FileSectionConfig = field(default_factory=FileSectionConfig)
    encoding: str = "utf-8"
    include_sections: Optional[List[str]] = None
    exclude_sections: Optional[List[str]] = None
    line_ending: str = "\n"
    add_file_stats: bool = False
    include_structure: bool = False
    structure_format: ListingStyle = ListingStyle.TREE
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