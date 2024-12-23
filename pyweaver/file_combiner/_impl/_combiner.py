"""Private implementation of file combining functionality.

Coordinates file scanning, content processing and combined output generation.

Path: pyweaver/file_combiner/_impl/_combiner.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set
import logging

from pyweaver.common.type_definitions import GeneratorResult, ProcessingError
from pyweaver.file_combiner.combiner import CombinerConfig
from pyweaver.file_combiner._impl._processor import ContentProcessor
from pyweaver.file_combiner._impl._writer import CombinerWriter

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
        self._collected_files: Dict[Path, FileContent] = {}

    def combine_files(self) -> GeneratorResult:
        """Combine files according to configuration."""
        try:
            self._collect_files()
            processed = self._process_files()
            self._writer.write_combined(processed, self.config.output_file)

            if self.config.generate_tree:
                self._writer.write_tree([f.rel_path for f in self._collected_files.values()])

            return GeneratorResult(
                success=True,
                message=f"Successfully combined {len(processed)} files",
                files_processed=len(processed),
                files_written=1
            )

        except Exception as e:
            logger.error("Error combining files: %s", e)
            raise ProcessingError(f"Failed to combine files: {str(e)}")

    def preview_output(self) -> str:
        """Generate preview of combined output."""
        try:
            self._collect_files()
            processed = self._process_files()
            return self._writer.format_combined(processed)
        except Exception as e:
            logger.error("Error generating preview: %s", e)
            raise ProcessingError(f"Failed to generate preview: {str(e)}")

    def _collect_files(self) -> None:
        """Collect all matching files."""
        self._collected_files.clear()

        try:
            for path in self._find_matching_files():
                try:
                    content = path.read_text(encoding='utf-8')
                    self._collected_files[path] = FileContent(
                        path=path,
                        content=content,
                        rel_path=path.relative_to(self.config.root_dir)
                    )
                except Exception as e:
                    logger.error("Error reading %s: %s", path, e)
                    raise ProcessingError(f"Failed to read {path}: {str(e)}")
        except Exception as e:
            logger.error("Error collecting files: %s", e)
            raise ProcessingError(f"Failed to collect files: {str(e)}")

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
                logger.error("Error processing %s: %s", file_content.path, e)
                raise ProcessingError(f"Failed to process {file_content.path}: {str(e)}")

        return processed

    def _find_matching_files(self) -> Set[Path]:
        """Find all files matching patterns."""
        try:
            matching = set()

            for path in self.config.root_dir.rglob("*"):
                if not path.is_file():
                    continue

                rel_path = path.relative_to(self.config.root_dir)
                str_path = str(rel_path)

                # Check patterns match
                if any(pattern in str_path for pattern in self.config.patterns):
                    if not any(exclude in str_path for exclude in self.config.exclude_patterns):
                        matching.add(path)

            return matching

        except Exception as e:
            logger.error("Error finding matching files: %s", e)
            raise ProcessingError(f"Failed to find matching files: {str(e)}")
