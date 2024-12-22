"""Private implementation of file combining functionality.

Coordinates file scanning, content processing and combined output generation.

Path: tools/project_tools/file_combiner/_impl/_combiner.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
import logging

from ...common.types import GeneratorResult, Pattern
from ..combiner import CombinerConfig, FileHandlingMode
from _processor import ContentProcessor
from _writer import CombinerWriter

logger = logging.getLogger(__name__)

@dataclass
class FileContent:
    """Content from a single file."""
    path: Path
    content: str
    rel_path: Path

class FileCombinerImpl:
    """Internal implementation of file combiner."""

    def __init__(self, config: CombinerConfig):
        self.config = config
        self._processor = ContentProcessor(config.mode)
        self._writer = CombinerWriter(config)
        self._patterns = {
            'include': {Pattern(p) for p in config.patterns},
            'exclude': {Pattern(p) for p in config.exclude_patterns}
        }
        self._collected_files: Dict[Path, FileContent] = {}

    def combine_files(self) -> GeneratorResult:
        """Combine files according to configuration."""
        try:
            # Collect and process files
            self._collect_files()
            processed = self._process_files()

            # Write output
            self._writer.write_combined(processed, self.config.output_file)

            # Generate tree if requested
            if self.config.generate_tree:
                self._writer.write_tree([f.rel_path for f in self._collected_files.values()])

            return GeneratorResult(
                success=True,
                message=f"Successfully combined {len(processed)} files",
                files_processed=len(processed),
                files_written=1
            )

        except Exception as e:
            logger.error(f"Error combining files: {e}")
            return GeneratorResult(
                success=False,
                message=f"Failed to combine files: {str(e)}",
                errors=[str(e)]
            )

    def preview_output(self) -> str:
        """Generate preview of combined output."""
        self._collect_files()
        processed = self._process_files()
        return self._writer.format_combined(processed)

    def _collect_files(self) -> None:
        """Collect all matching files."""
        self._collected_files.clear()

        for path in self._find_matching_files():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                self._collected_files[path] = FileContent(
                    path=path,
                    content=content,
                    rel_path=path.relative_to(self.config.root_dir)
                )

            except Exception as e:
                logger.error(f"Error reading {path}: {e}")

    def _process_files(self) -> List[FileContent]:
        """Process collected file content."""
        processed = []

        for file_content in sorted(
            self._collected_files.values(),
            key=lambda f: f.rel_path
        ):
            try:
                processed_content = self._processor.process_content(
                    file_content.content,
                    file_content.path.suffix
                )

                processed.append(FileContent(
                    path=file_content.path,
                    content=processed_content,
                    rel_path=file_content.rel_path
                ))

            except Exception as e:
                logger.error(f"Error processing {file_content.path}: {e}")

        return processed

    def _find_matching_files(self) -> Set[Path]:
        """Find all files matching patterns."""
        matching = set()

        # Check each file against patterns
        for path in self.config.root_dir.rglob("*"):
            # Skip directories
            if not path.is_file():
                continue

            rel_path = path.relative_to(self.config.root_dir)
            str_path = str(rel_path)

            # Check exclusions first
            if any(p.matches(str_path) for p in self._patterns['exclude']):
                continue

            # Then check inclusions
            if any(p.matches(str_path) for p in self._patterns['include']):
                matching.add(path)

        return matching
