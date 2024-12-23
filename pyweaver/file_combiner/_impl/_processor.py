"""Private implementation of file content processing.

Handles processing of file content including comment and docstring removal
based on configured mode.

Path: pyweaver/file_combiner/_impl/_processor.py
"""

import ast
import re
from typing import List, Optional
import logging

from pyweaver.file_combiner.combiner import FileHandlingMode

logger = logging.getLogger(__name__)

class ContentProcessor:
    """Processes file content according to configured mode."""

    def __init__(self, mode: FileHandlingMode):
        self.mode = mode

    def process_content(self, content: str, file_type: str) -> str:
        """Process file content according to mode."""
        if self.mode == FileHandlingMode.FULL:
            return content

        if file_type == '.py':
            return self._process_python(content)
        elif file_type in {'.js', '.ts', '.tsx'}:
            return self._process_javascript(content)
        elif file_type == '.css':
            return self._process_css(content)
        else:
            return content

    def _process_python(self, content: str) -> str:
        """Process Python file content."""
        try:
            lines = content.split('\n')
            cleaned_lines = []
            i = 0
            in_docstring = False
            in_function = False
            docstring_start = None
            indentation = 0
            current_indent = 0

            while i < len(lines):
                line = lines[i].rstrip()
                stripped = line.strip()
                current_indent = len(line) - len(line.lstrip())

                # Track function/class definitions
                if stripped.startswith(('def ', 'class ')):
                    in_function = True
                    indentation = current_indent

                # Handle docstring detection and removal
                if not in_docstring:
                    if stripped.startswith('"""') or stripped.startswith("'''"):
                        # Verify this is actually a docstring
                        is_docstring = (
                            i == 0 or  # Module level
                            (in_function and current_indent > indentation) or  # Function/class
                            docstring_start is not None  # Standalone
                        )

                        if is_docstring and self.mode in {FileHandlingMode.NO_DOCSTRINGS, FileHandlingMode.MINIMAL}:
                            docstring_delimiter = stripped[:3]
                            if stripped == docstring_delimiter:
                                docstring_start = i
                                in_docstring = True
                            elif stripped.endswith(docstring_delimiter) and len(stripped) > 3:
                                i += 1
                                continue
                            else:
                                cleaned_lines.append(line)
                        else:
                            cleaned_lines.append(line)
                    else:
                        if self.mode in {FileHandlingMode.NO_COMMENTS, FileHandlingMode.MINIMAL}:
                            code_part = line.split('#')[0].rstrip()
                            if code_part or not line.strip():
                                cleaned_lines.append(code_part)
                        else:
                            cleaned_lines.append(line)
                else:
                    # In docstring - look for end
                    if (stripped.endswith('"""') or stripped.endswith("'''")) and not stripped.startswith('#'):
                        in_docstring = False
                        docstring_start = None
                        if self.mode not in {FileHandlingMode.NO_DOCSTRINGS, FileHandlingMode.MINIMAL}:
                            cleaned_lines.extend(lines[docstring_start:i+1])

                i += 1

            return '\n'.join(cleaned_lines)

        except Exception as e:
            logger.error(f"Error processing Python content: {e}")
            return content

    def _process_javascript(self, content: str) -> str:
        """Process JavaScript/TypeScript file content."""
        if not (self.mode in {FileHandlingMode.NO_COMMENTS, FileHandlingMode.MINIMAL}):
            return content

        lines = content.split('\n')
        cleaned_lines = []
        in_multiline = False
        in_jsdoc = False

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Handle JSDoc comments
            if self.mode in {FileHandlingMode.NO_DOCSTRINGS, FileHandlingMode.MINIMAL}:
                if '/**' in line:
                    in_jsdoc = True
                    i += 1
                    continue
                elif in_jsdoc and '*/' in line:
                    in_jsdoc = False
                    i += 1
                    continue
                elif in_jsdoc:
                    i += 1
                    continue

            if self.mode in {FileHandlingMode.NO_COMMENTS, FileHandlingMode.MINIMAL}:
                # Handle regular multi-line comments
                if '/*' in line:
                    in_multiline = True
                    code_part = line.split('/*')[0].rstrip()
                    if code_part:
                        cleaned_lines.append(code_part)
                    i += 1
                    continue
                elif '*/' in line:
                    in_multiline = False
                    code_part = line.split('*/')[1].rstrip()
                    if code_part:
                        cleaned_lines.append(code_part)
                    i += 1
                    continue
                elif in_multiline:
                    i += 1
                    continue

                # Handle single-line comments
                if '//' in line:
                    code_part = line.split('//')[0].rstrip()
                    if code_part or not line.strip():
                        cleaned_lines.append(code_part)
                else:
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)

            i += 1

        return '\n'.join(cleaned_lines)

    def _process_css(self, content: str) -> str:
        """Process CSS file content."""
        if not (self.mode in {FileHandlingMode.NO_COMMENTS, FileHandlingMode.MINIMAL}):
            return content

        lines = content.split('\n')
        cleaned_lines = []
        in_multiline = False

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            if '/*' in line:
                in_multiline = True
                code_part = line.split('/*')[0].rstrip()
                if code_part:
                    cleaned_lines.append(code_part)
                i += 1
                continue
            elif '*/' in line:
                in_multiline = False
                code_part = line.split('*/')[1].rstrip()
                if code_part:
                    cleaned_lines.append(code_part)
                i += 1
                continue
            elif in_multiline:
                i += 1
                continue
            else:
                cleaned_lines.append(line)

            i += 1

        return '\n'.join(cleaned_lines)
