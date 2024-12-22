"""Private implementation of init file writing.

Handles writing formatted init file content to disk with proper
error handling and validation.

Path: tools/project_tools/init_generator/_impl/_writer.py
"""

from pathlib import Path
from typing import Dict, Set
import logging

from ...common.types import GeneratorResult
from ...init_generator import InitGeneratorConfig

logger = logging.getLogger(__name__)

class InitWriter:
    """Handles writing init files to disk."""

    def __init__(self, config: InitGeneratorConfig):
        self.config = config
        self._written_files: Set[Path] = set()

    def write_files(self, files: Dict[Path, str]) -> GeneratorResult:
        """Write init files to disk.

        Args:
            files: Dict mapping module paths to their content

        Returns:
            GeneratorResult with operation results
        """
        result = GeneratorResult(
            success=True,
            message="",
            files_processed=len(files),
            files_written=0,
            errors=[],
            warnings=[]
        )

        for module_path, content in files.items():
            try:
                # Get init file path
                init_path = module_path.parent / "__init__.py"

                # Check if content has changed
                if init_path.exists():
                    current = init_path.read_text()
                    if current.strip() == content.strip():
                        logger.debug("No changes needed for %s", init_path)
                        continue

                # Write file
                init_path.parent.mkdir(parents=True, exist_ok=True)
                init_path.write_text(content)
                self._written_files.add(init_path)
                result.files_written += 1
                logger.info("Updated %s", init_path)

            except Exception as e:
                logger.error("Error writing %s: %s", module_path, e)
                result.success = False
                result.errors.append(f"Failed to write {module_path}: {str(e)}")

        # Set final message
        result.message = self._get_result_message(result)
        return result

    def write_combined(self, files: Dict[Path, str], output_path: Path) -> Path:
        """Write combined output file.

        Args:
            files: Dict mapping module paths to their content
            output_path: Path for combined output

        Returns:
            Path to written file
        """
        try:
            content = []

            # Add header
            content.append("# Combined __init__.py files")
            content.append(f"# Total files: {len(files)}\n")

            # Add each module
            for module_path, module_content in sorted(files.items()):
                rel_path = module_path.relative_to(self.config.root_dir)
                content.append(f"{'#' * 80}")
                content.append(f"# {rel_path}/__init__.py")
                content.append(f"{'#' * 80}")
                content.append(module_content)
                content.append("")  # Empty line between modules

            # Write combined file
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("\n".join(content))
            self._written_files.add(output_path)

            logger.info("Wrote combined output to %s", output_path)
            return output_path

        except Exception as e:
            logger.error("Error writing combined output: %s", e)
            raise

    def _get_result_message(self, result: GeneratorResult) -> str:
        """Generate appropriate result message."""
        if result.success:
            msg = f"Successfully wrote {result.files_written} init files"
            if result.warnings:
                msg += f" with {len(result.warnings)} warnings"
            return msg
        else:
            return f"Completed with {len(result.errors)} errors"

    @property
    def written_files(self) -> Set[Path]:
        """Get set of files written."""
        return self._written_files.copy()
