"""Private implementation of file combining functionality.

This module provides the internal implementation details for the file combining system.
It handles the complexities of content processing, section organization, and file
operations while maintaining a clean separation from the public interface.

The implementation provides:
- Content processing strategies for different file types
- Section-based content organization
- Memory-efficient processing
- Robust error handling

Path: pyweaver/processors/_impl/_file_combiner.py
"""
import ast
import logging
from pathlib import Path
from typing import Dict, List
import re
import time
from dataclasses import dataclass

from pyweaver.processors.file_combiner import CombinerConfig, ContentMode
from pyweaver.processors.structure import StructurePrinter, StructureOptions
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)

logger = logging.getLogger(__name__)

@dataclass
class ProcessedContent:
    """Information about processed file content.

    This class tracks details about processed content to help with
    organization and error handling.

    Attributes:
        content: The processed content
        original_size: Size of original content
        processed_size: Size after processing
        line_count: Number of lines in processed content
        processing_time: Time taken to process
    """
    content: str
    original_size: int
    processed_size: int
    line_count: int
    processing_time: float

class FileProcessor:
    """Base class for file type specific processors.

    This class provides the foundation for implementing content processing
    strategies for different file types.
    """
    def process(self, content: str, mode: ContentMode) -> str:
        """Process content according to specified mode.

        Args:
            content: Raw file content
            mode: Processing mode to apply

        Returns:
            Processed content
        """
        if mode == ContentMode.FULL:
            return content
        return self._process_content(content, mode)

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Implement specific processing logic."""
        raise NotImplementedError

class PythonProcessor(FileProcessor):
    """Content processor for Python files."""

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Process Python content with docstring and comment handling."""
        try:
            # Handle docstrings if needed
            if mode in {ContentMode.NO_DOCSTRINGS, ContentMode.MINIMAL}:
                try:
                    tree = ast.parse(content)
                    content = self._remove_docstrings(tree)
                except SyntaxError:
                    content = self._remove_docstrings_basic(content)

            # Handle comments if needed
            if mode in {ContentMode.NO_COMMENTS, ContentMode.MINIMAL}:
                content = self._remove_comments(content)

            return content

        except Exception as e:
            context = ErrorContext(
                operation="process_python",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"mode": mode.value}
            )
            raise ProcessingError(
                "Failed to process Python content",
                context=context,
                original_error=e
            ) from e

    def _remove_docstrings(self, tree: ast.AST) -> str:
        """Remove docstrings using AST."""
        class DocstringRemover(ast.NodeTransformer):
            def visit_Module(self, node):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Str)):
                    node.body.pop(0)
                return node

            def visit_ClassDef(self, node):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Str)):
                    node.body.pop(0)
                return node

            def visit_FunctionDef(self, node):
                if (node.body and isinstance(node.body[0], ast.Expr) and
                    isinstance(node.body[0].value, ast.Str)):
                    node.body.pop(0)
                return node

        tree = DocstringRemover().visit(tree)
        return ast.unparse(tree)

    def _remove_docstrings_basic(self, content: str) -> str:
        """Remove docstrings using basic parsing."""
        lines = []
        in_docstring = False
        docstring_delimiter = None

        for line in content.splitlines():
            stripped = line.strip()

            if not in_docstring:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') == 2 or stripped.count("'''") == 2:
                        continue  # Skip single-line docstring
                    in_docstring = True
                    docstring_delimiter = stripped[:3]
                    continue
                lines.append(line)
            elif stripped.endswith(docstring_delimiter):
                in_docstring = False
                docstring_delimiter = None

        return '\n'.join(lines)

    def _remove_comments(self, content: str) -> str:
        """Remove comments while preserving string literals."""
        lines = []
        for line in content.splitlines():
            if "#" in line:
                # Only split on # if it's not in a string
                in_string = False
                string_char = None
                comment_pos = -1

                for i, char in enumerate(line):
                    if char in '"\'':
                        if not in_string:
                            in_string = True
                            string_char = char
                        elif char == string_char and line[i-1] != '\\':
                            in_string = False
                    elif char == '#' and not in_string:
                        comment_pos = i
                        break

                if comment_pos >= 0:
                    code = line[:comment_pos].rstrip()
                    if code:
                        lines.append(code)
                else:
                    lines.append(line)
            else:
                lines.append(line)

        return '\n'.join(lines)

class JavaScriptProcessor(FileProcessor):
    """Content processor for JavaScript/TypeScript files."""

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Process JavaScript content with JSDoc and comment handling."""
        if mode == ContentMode.FULL:
            return content

        lines = []
        in_multiline = False
        in_jsdoc = False
        in_string = False
        string_char = None

        try:
            for line in content.splitlines():
                if not in_multiline and not in_jsdoc:
                    processed_line = ''
                    i = 0
                    while i < len(line):
                        if not in_string:
                            if line[i:i+2] == '/*':
                                if line[i:i+3] == '/**':
                                    if mode in {ContentMode.NO_DOCSTRINGS, ContentMode.MINIMAL}:
                                        in_jsdoc = True
                                        break
                                in_multiline = True
                                break
                            elif line[i:i+2] == '//' and not in_string:
                                processed_line += line[:i].rstrip()
                                break
                            elif line[i] in '"\'`':
                                in_string = True
                                string_char = line[i]
                        else:
                            if line[i] == string_char and line[i-1] != '\\':
                                in_string = False

                        processed_line += line[i]
                        i += 1

                    if processed_line or not line.strip():
                        lines.append(processed_line)
                else:
                    if '*/' in line:
                        in_multiline = False
                        in_jsdoc = False
                        after_comment = line.split('*/')[-1].lstrip()
                        if after_comment:
                            lines.append(after_comment)

            return '\n'.join(lines)

        except Exception as e:
            context = ErrorContext(
                operation="process_javascript",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"mode": mode.value}
            )
            raise ProcessingError(
                "Failed to process JavaScript content",
                context=context,
                original_error=e
            ) from e

class StyleProcessor(FileProcessor):
    """Content processor for CSS/SCSS/LESS files."""

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Process style content, handling comments appropriately."""
        try:
            if mode == ContentMode.FULL:
                return content

            if mode in {ContentMode.NO_COMMENTS, ContentMode.MINIMAL}:
                # Remove multi-line comments while preserving content
                content = re.sub(r'/\*[\s\S]*?\*/', '', content)

                # Remove single-line comments
                content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)

            return content

        except Exception as e:
            context = ErrorContext(
                operation="process_style",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"mode": mode.value}
            )
            raise ProcessingError(
                "Failed to process style content",
                context=context,
                original_error=e
            ) from e

class HTMLProcessor(FileProcessor):
    """Content processor for HTML files."""

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Process HTML content, handling comments appropriately."""
        try:
            if mode == ContentMode.FULL:
                return content

            if mode in {ContentMode.NO_COMMENTS, ContentMode.MINIMAL}:
                # Remove HTML comments while preserving conditional comments
                content = re.sub(
                    r'<!--(?!.*?[\[<].*?>).*?-->',
                    '',
                    content,
                    flags=re.DOTALL
                )

            return content

        except Exception as e:
            context = ErrorContext(
                operation="process_html",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"mode": mode.value}
            )
            raise ProcessingError(
                "Failed to process HTML content",
                context=context,
                original_error=e
            ) from e

class VueProcessor(FileProcessor):
    """Content processor for Vue component files."""

    def _process_content(self, content: str, mode: ContentMode) -> str:
        """Process Vue content, handling section-specific processing."""
        try:
            if mode == ContentMode.FULL:
                return content

            sections = re.split(
                r'(<template>|<script>|<style>|</template>|</script>|</style>)',
                content
            )
            processed = []

            html_processor = HTMLProcessor()
            js_processor = JavaScriptProcessor()
            style_processor = StyleProcessor()

            current_section = None
            for section in sections:
                if section in {'<template>', '<script>', '<style>'}:
                    current_section = section
                    processed.append(section)
                elif section in {'</template>', '</script>', '</style>'}:
                    current_section = None
                    processed.append(section)
                else:
                    if current_section == '<template>':
                        processed.append(html_processor.process(section, mode))
                    elif current_section == '<script>':
                        processed.append(js_processor.process(section, mode))
                    elif current_section == '<style>':
                        processed.append(style_processor.process(section, mode))
                    else:
                        processed.append(section)

            return ''.join(processed)

        except Exception as e:
            context = ErrorContext(
                operation="process_vue",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"mode": mode.value}
            )
            raise ProcessingError(
                "Failed to process Vue content",
                context=context,
                original_error=e
            ) from e

class FileCombinerImpl:
    """Internal implementation of file combining operations.

    This class handles the details of combining files, including content
    processing, organization, and output generation. It maintains separation
    from the public interface while providing robust processing capabilities.
    """

    def __init__(self, config: CombinerConfig, root_dir: Path):
        """Initialize implementation with configuration.

        Args:
            config: Combining configuration
            root_dir: Root directory for processing
        """
        self.config = config
        self.root_dir = root_dir
        self._combined_content: List[str] = []
        self._processed_files: Dict[Path, ProcessedContent] = {}

        # Initialize processors
        self._processors = {
            '.py': PythonProcessor(),
            '.js': JavaScriptProcessor(),
            '.ts': JavaScriptProcessor(),
            '.tsx': JavaScriptProcessor(),
            '.jsx': JavaScriptProcessor(),
            '.css': StyleProcessor(),
            '.scss': StyleProcessor(),
            '.less': StyleProcessor(),
            '.html': HTMLProcessor(),
            '.vue': VueProcessor()
        }

        logger.debug(
            "Initialized combiner implementation with %d processors",
            len(self._processors)
        )

    def process_file(self, path: Path) -> None:
        """Process a single file's content.

        Args:
            path: Path to file to process

        Raises:
            FileError: If file cannot be read or processed
            ProcessingError: If content processing fails
        """
        try:
            start_time = time.time()

            # Read content
            content = self._read_file(path)
            original_size = len(content)

            # Process content
            processed = self._process_content(content, path.suffix)

            # Apply formatting
            if self.config.section_config.remove_trailing_whitespace:
                processed = '\n'.join(
                    line.rstrip()
                    for line in processed.splitlines()
                )

            if not self.config.section_config.include_empty_lines:
                processed = '\n'.join(
                    line for line in processed.splitlines()
                    if line.strip()
                )

            # Standardize line endings
            processed = processed.replace('\r\n', '\n').replace('\r', '\n')
            if self.config.line_ending != '\n':
                processed = processed.replace('\n', self.config.line_ending)

            # Get relative path
            rel_path = path.relative_to(self.root_dir)

            # Format section
            header = self.config.section_config.format_header(
                rel_path,
                size=len(content),
                lines=len(content.splitlines())
            )

            footer = self.config.section_config.format_footer(
                rel_path,
                size=len(processed),
                lines=len(processed.splitlines())
            )

            # Store processing results
            processing_time = time.time() - start_time
            self._processed_files[path] = ProcessedContent(
                content=processed,
                original_size=original_size,
                processed_size=len(processed),
                line_count=len(processed.splitlines()),
                processing_time=processing_time
            )

            # Add to combined content
            self._combined_content.extend([
                header,
                processed,
                footer
            ])

            logger.debug(
                "Processed %s (original: %d bytes, processed: %d bytes, time: %.2fs)",
                rel_path, original_size, len(processed), processing_time
            )

        except Exception as e:
            context = ErrorContext(
                operation="process_file",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=path,
                details={
                    "file_type": path.suffix,
                    "content_mode": self.config.content_mode.value
                }
            )
            raise ProcessingError(
                f"Failed to process {path}",
                context=context,
                original_error=e
            ) from e

    def write_output(self) -> None:
        """Write combined output to file.

        This method generates and writes the final combined output,
        including any requested structure information or statistics.

        Raises:
            FileError: If writing fails
        """
        try:
            # Create output directory if needed
            self.config.output_file.parent.mkdir(parents=True, exist_ok=True)

            # Generate complete output content
            output = self._generate_output()

            # Write final content
            self.config.output_file.write_text(
                output,
                encoding=self.config.encoding
            )

            logger.info(
                "Wrote combined output to %s (%d bytes)",
                self.config.output_file,
                len(output)
            )

        except Exception as e:
            context = ErrorContext(
                operation="write_output",
                error_code=ErrorCode.FILE_WRITE,
                path=self.config.output_file,
                details={"encoding": self.config.encoding}
            )
            raise FileError(
                "Failed to write output file",
                path=self.config.output_file,
                context=context,
                original_error=e
            ) from e

    def preview_output(self) -> str:
        """Generate preview of combined output.

        This method creates a preview of what would be written to the output
        file, including all structural elements and statistics if configured.

        Returns:
            Preview of combined content

        Raises:
            ProcessingError: If preview generation fails
        """
        try:
            if not self._combined_content:
                return "No files processed yet"

            return self._generate_output()

        except Exception as e:
            context = ErrorContext(
                operation="preview_output",
                error_code=ErrorCode.PROCESS_EXECUTION
            )
            raise ProcessingError(
                "Failed to generate preview",
                context=context,
                original_error=e
            ) from e

    def generate_tree(self) -> str:
        """Generate tree structure of included files.

        This method creates a visual representation of the file structure
        being combined, useful for documentation and verification.

        Returns:
            Tree structure representation

        Raises:
            ProcessingError: If tree generation fails
        """
        try:
            if not self._processed_files:
                return "No files processed"

            def build_tree(paths: List[Path], prefix: str = "") -> List[str]:
                """Build tree structure recursively."""
                if not paths:
                    return []

                tree = []
                for i, path in enumerate(sorted(paths)):
                    is_last = i == len(paths) - 1
                    connector = "└── " if is_last else "├── "
                    tree.append(f"{prefix}{connector}{path.name}")

                    # Process children
                    children = [p for p in paths if p.parent == path]
                    if children:
                        ext_prefix = "    " if is_last else "│   "
                        tree.extend(build_tree(children, prefix + ext_prefix))

                return tree

            paths = [Path(file.relative_to(self.root_dir))
                    for file in self._processed_files.keys()]

            return "\n".join([
                "# Project Structure",
                f"# Total files: {len(paths)}",
                "",
                *build_tree(paths)
            ])

        except Exception as e:
            context = ErrorContext(
                operation="generate_tree",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"num_files": len(self._processed_files)}
            )
            raise ProcessingError(
                "Failed to generate tree structure",
                context=context,
                original_error=e
            ) from e

    def _read_file(self, path: Path) -> str:
        """Read file content with proper error handling.

        Args:
            path: Path to file to read

        Returns:
            File content

        Raises:
            FileError: If file cannot be read
        """
        try:
            return path.read_text(encoding=self.config.encoding)

        except Exception as e:
            context = ErrorContext(
                operation="read_file",
                error_code=ErrorCode.FILE_READ,
                path=path,
                details={"encoding": self.config.encoding}
            )
            raise FileError(
                f"Failed to read file: {e}",
                path=path,
                context=context,
                original_error=e
            ) from e

    def _process_content(self, content: str, file_type: str) -> str:
        """Process content according to file type and configuration.

        This method applies the appropriate processing strategy based on
        the file type and configured content mode.

        Args:
            content: Raw file content
            file_type: File extension including dot

        Returns:
            Processed content

        Raises:
            ProcessingError: If processing fails
        """
        try:
            # Get appropriate processor
            processor = self._processors.get(file_type.lower())
            if processor is None:
                logger.debug(
                    "No specific processor for %s, using raw content",
                    file_type
                )
                return content

            return processor.process(content, self.config.content_mode)

        except Exception as e:
            context = ErrorContext(
                operation="process_content",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={
                    "file_type": file_type,
                    "content_mode": self.config.content_mode.value
                }
            )
            raise ProcessingError(
                f"Failed to process content",
                context=context,
                original_error=e
            ) from e

    def _generate_output(self) -> str:
        """Generate complete output content.

        This method combines all processed content with optional structure
        information and statistics into the final output format.

        Returns:
            Complete output content
        """
        output = []

        # Add file structure if requested
        if self.config.include_structure:
            options = StructureOptions(
                include_empty=self.config.include_empty_dirs,
                use_tree_format=self.config.structure_tree_format,
                ignore_patterns=self.config.ignore_patterns
            )
            printer = StructurePrinter(self.root_dir, options)
            structure = printer.generate_structure()

            output.extend([
                "# Project Structure",
                "#" * 80,
                structure,
                "#" * 80,
                ""
            ])

        # Add file statistics if requested
        if self.config.add_file_stats:
            total_files = len(self._processed_files)
            total_original = sum(f.original_size for f in self._processed_files.values())
            total_processed = sum(f.processed_size for f in self._processed_files.values())
            total_lines = sum(f.line_count for f in self._processed_files.values())

            stats = [
                f"# Combined {total_files} files",
                f"# Original size: {total_original:,} bytes",
                f"# Processed size: {total_processed:,} bytes",
                f"# Total lines: {total_lines:,}",
                f"# Content mode: {self.config.content_mode.value}",
                "#" * 80,
                ""
            ]
            output.extend(stats)

        # Add combined content
        output.extend(self._combined_content)

        return '\n'.join(output)