"""Init file processor implementation.

This module provides a specialized processor for generating and updating __init__.py
files across a project structure. It analyzes Python modules to extract exports,
organizes content into sections, and maintains proper documentation. The processor
supports preview functionality, configuration overrides, and incremental updates.

The module implements:
- Module analysis and export collection
- Structured content generation
- Preview functionality
- Incremental file updates
- Comprehensive error handling

Path: pyweaver/processors/init_processor.py
"""
import logging
from pathlib import Path
from typing import Dict, Optional, Set
from dataclasses import dataclass

from pyweaver.common.base import BaseProcessor, ProcessorProgress
from pyweaver.common.tracking import TrackerType
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)
from pyweaver.config.init import InitConfig, ImportSection
from pyweaver.config.path import PathConfig
from pyweaver.utils.module_analyzer import ModuleAnalyzer, ModuleInfo
from pyweaver.utils.repr import comprehensive_repr

logger = logging.getLogger(__name__)

@dataclass
class InitFileProgress(ProcessorProgress):
    """Extended progress tracking for init file generation.

    This class adds init-specific progress metrics to the base progress
    tracking functionality.

    Attributes:
        modules_analyzed: Number of modules analyzed
        exports_collected: Number of exports found
        sections_generated: Number of sections generated
        content_size: Total size of generated content
    """
    modules_analyzed: int = 0
    exports_collected: int = 0
    sections_generated: int = 0
    content_size: int = 0

class InitFileProcessor(BaseProcessor):
    """Processor for generating and updating __init__.py files.

    This processor analyzes Python modules within a project structure and generates
    appropriate __init__.py files with exports, documentation, and organized sections.
    It supports preview functionality, incremental updates, and detailed configuration
    options.

    The processor provides:
    - Module analysis and export collection
    - Structured content generation
    - Preview functionality
    - Incremental file updates
    - Configuration overrides

    Example:
        ```python
        processor = InitFileProcessor("./src")

        # Preview changes
        changes = processor.preview()
        for path, content in changes.items():
            print(f"Would update: {path}")

        # Generate files
        result = processor.process()
        if result.success:
            print(f"Updated {result.files_processed} files")
        ```
    """

    def __init__(
        self,
        root_dir: str | Path,
        config_path: Optional[str | Path] = None,
        dry_run: bool = False
    ):
        """Initialize the init file processor.

        Args:
            root_dir: Root directory to process
            config_path: Optional path to init_config.json
            dry_run: If True, don't write any files

        Raises:
            ValidationError: If configuration is invalid
            FileError: If required files cannot be accessed
        """
        try:
            # Convert paths
            self.root_dir = Path(root_dir).resolve()
            self.config_path = Path(config_path) if config_path else self.root_dir / "init_config.json"

            # Initialize specialized configuration
            self.init_config = InitConfig.from_file(
                config_path=self.config_path,
                root_dir=self.root_dir
            )

            # Create base config for file tracking
            base_config = PathConfig(
                global_settings={
                    "ignore_patterns": self.init_config.global_settings.excluded_paths
                }
            )

            # Initialize base class
            super().__init__(base_config, TrackerType.BOTH)

            self.pattern_matcher = self.init_config.pattern_matcher
            self.dry_run = dry_run
            self.module_analyzer = ModuleAnalyzer()

            # Replace standard progress with specialized version
            self.progress = InitFileProgress()

            # Storage for generated content
            self._changes: Dict[Path, str] = {}

            logger.info(
                "Initialized InitFileProcessor for %s (dry_run=%s)",
                self.root_dir, dry_run
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_processor",
                error_code=ErrorCode.PROCESS_INIT,
                path=root_dir,
                details={"config_path": str(self.config_path)}
            )
            raise ProcessingError(
                "Failed to initialize init file processor",
                context=context,
                original_error=e
            ) from e

    def preview(self,
                print_changes: bool = False,
                output_file: Optional[str | Path] = None) -> Dict[Path, str]:
        """Preview changes that would be made to init files.

        This method performs a dry run of the processing operation, collecting
        all changes that would be made without actually writing files.

        Args:
            print_changes: If True, print changes to console
            output_file: Optional file path to save preview output

        Returns:
            Dict mapping file paths to their proposed content

        Raises:
            ProcessingError: If preview generation fails
        """
        try:
            # Ensure we're in preview mode
            original_dry_run = self.dry_run
            self.dry_run = True

            try:
                # Perform processing
                self._scan_project()
                self.process()

                # Generate preview output if requested
                if print_changes or output_file:
                    preview_text = self._format_preview()

                    if print_changes:
                        print(preview_text)

                    if output_file:
                        output_path = Path(output_file)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(preview_text, encoding="utf-8")

                return self._changes.copy()

            finally:
                # Restore original dry_run setting
                self.dry_run = original_dry_run

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

    def _scan_project(self) -> None:
        """Scan project to find directories needing init files.

        This method identifies all Python package directories that need
        __init__.py files generated or updated.

        Raises:
            ProcessingError: If project scanning fails
        """
        try:
            # Clear previous state
            self.tracker.cleanup()
            self._changes.clear()

            logger.info("Starting project scan from: %s", self.root_dir)

            # Add root directory
            self.tracker.add_pending(self.root_dir)

            # Track statistics for logging
            total_files = 0
            excluded_files = 0
            excluded_paths = []

            # Scan for Python files to identify package directories
            for path in self.root_dir.rglob("*.py"):
                total_files += 1
                if path.name == "__init__.py":
                    continue

                dir_path = path.parent
                rel_path = dir_path.relative_to(self.root_dir)

                if not self.init_config.pattern_matcher.is_excluded_path(dir_path):
                    self.tracker.add_pending(dir_path)
                    logger.debug("Added directory to pending: %s", dir_path)
                else:
                    excluded_files += 1
                    excluded_paths.append(str(rel_path))
                    logger.debug("Excluded directory: %s", dir_path)

            # Update progress tracking
            self.progress.total_items = self.tracker.get_stats().total

            logger.info(
                "Scan complete. Found %d Python files (%d excluded).",
                total_files, excluded_files
            )
            logger.info(
                "Added %d directories to process",
                self.progress.total_items
            )

        except Exception as e:
            context = ErrorContext(
                operation="scan_project",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=self.root_dir
            )
            raise ProcessingError(
                "Project scanning failed",
                context=context,
                original_error=e
            ) from e

    def _process_item(self, path: Path) -> None:
        """Process a single directory to generate/update its __init__.py.

        This method analyzes the Python modules in a directory and generates
        or updates its __init__.py file with appropriate exports and documentation.

        Args:
            path: Directory to process

        Raises:
            ProcessingError: If processing fails
            FileError: If file operations fail
        """
        try:
            # Skip if path should be excluded
            if self.init_config.pattern_matcher.is_excluded_path(path):
                self._add_warning(f"Skipping excluded path: {path}")
                return

            # Get package configuration
            package_config = self.init_config.get_package_config(path)

            # Collect module information
            module_info = self._collect_module_info(path, package_config)
            if not module_info:
                logger.debug("No modules found in %s", path)
                return

            self.progress.modules_analyzed += len(module_info)

            # Generate content
            content = self._generate_init_content(path, module_info, package_config)
            if not content:
                logger.debug("No content generated for %s", path)
                return

            self.progress.content_size += len(content)

            # Update init file
            init_file = path / "__init__.py"
            try:
                current_content = init_file.read_text() if init_file.exists() else None
            except Exception as e:
                context = ErrorContext(
                    operation="read_init",
                    error_code=ErrorCode.FILE_READ,
                    path=init_file
                )
                raise FileError(
                    "Failed to read existing __init__.py",
                    path=init_file,
                    context=context,
                    original_error=e
                ) from e

            # Only update if content has changed
            if content != current_content:
                self._changes[init_file] = content
                if not self.dry_run:
                    try:
                        init_file.parent.mkdir(parents=True, exist_ok=True)
                        init_file.write_text(content)
                        logger.info("Updated %s", init_file)
                    except Exception as e:
                        context = ErrorContext(
                            operation="write_init",
                            error_code=ErrorCode.FILE_WRITE,
                            path=init_file
                        )
                        raise FileError(
                            "Failed to write __init__.py",
                            path=init_file,
                            context=context,
                            original_error=e
                        ) from e

        except Exception as e:
            context = ErrorContext(
                operation="process_directory",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=path,
                details={"dry_run": self.dry_run}
            )
            raise ProcessingError(
                f"Failed to process directory: {path}",
                context=context,
                original_error=e
            ) from e

    def _collect_module_info(self, dir_path: Path, config: PackageConfig) -> Dict[str, ModuleInfo]:
        """Collect information about modules in a directory.

        This method analyzes Python modules in a directory to extract information
        about their exports, classes, functions, and dependencies.

        Args:
            dir_path: Directory to analyze
            config: Package configuration

        Returns:
            Dictionary mapping module names to their information

        Raises:
            ProcessingError: If module analysis fails
        """
        try:
            module_info = {}

            # Process Python files
            for py_file in dir_path.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue

                info = self.module_analyzer.analyze_file(
                    py_file,
                    str(self.root_dir.name)
                )
                if info:
                    module_info[py_file.stem] = info
                    self.progress.exports_collected += len(info.exports)

            # Process submodules if enabled
            if config.collect_from_submodules:
                for subdir in dir_path.iterdir():
                    if not subdir.is_dir():
                        continue

                    # Skip if excluded
                    if self.init_config.pattern_matcher.is_excluded_path(subdir):
                        continue

                    # Skip if not in included submodules
                    if (config.include_submodules and
                        subdir.name not in config.include_submodules):
                        continue

                    sub_init = subdir / "__init__.py"
                    if sub_init.exists():
                        info = self.module_analyzer.analyze_file(
                            sub_init,
                            str(self.root_dir.name)
                        )
                        if info:
                            module_info[subdir.name] = info
                            self.progress.exports_collected += len(info.exports)

            return module_info

        except Exception as e:
            context = ErrorContext(
                operation="collect_module_info",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=dir_path,
                details={"config": str(config)}
            )
            raise ProcessingError(
                "Failed to collect module information",
                context=context,
                original_error=e
            ) from e

    def _generate_init_content(self,
        dir_path: Path,
        module_info: Dict[str, ModuleInfo],
        config: PackageConfig) -> Optional[str]:
        """Generate content for an init file.

        This method generates the content for an __init__.py file based on
        the collected module information and configuration settings.

        Args:
            dir_path: Directory being processed
            module_info: Information about modules
            config: Package configuration

        Returns:
            Generated content or None if no content needed

        Raises:
            ProcessingError: If content generation fails
        """
        try:
            # Get relative path from project root
            try:
                rel_path = dir_path.relative_to(self.root_dir)
            except ValueError:
                rel_path = dir_path  # Fallback to full path if can't make relative

            # Initialize content with docstring
            content = [f'"""{config.docstring}\n']

            # Collect class documentation
            class_docs = []
            for info in module_info.values():
                for class_name, docstring in info.classes.items():
                    if docstring:
                        first_line = docstring.split('\n')[0].strip()
                        class_docs.append(f"    {class_name}: {first_line}")

            # Add class documentation if available
            if class_docs:
                content.extend(sorted(class_docs))
                content.append("")

            # Add path information for traceability
            content.append(f'Path: {rel_path.as_posix()}/__init__.py\n"""')

            # Track imported items to prevent duplicates
            imported_items = set()

            # Process sections in configured order
            sorted_sections = sorted(
                [(section, cfg) for section, cfg in config.sections.items() if cfg.enabled],
                key=lambda x: x[1].order
            )

            # Add imports organized by section
            for section, section_config in sorted_sections:
                section_imports = set()

                # Collect imports for this section
                for module_name, info in module_info.items():
                    imports = []
                    for name in info.exports:
                        # Skip if already imported
                        if name in imported_items:
                            continue

                        # Determine if name belongs in this section
                        belongs_in_section = False
                        if section == ImportSection.CLASSES.value and name in info.classes:
                            belongs_in_section = True
                        elif section == ImportSection.FUNCTIONS.value and name in info.functions:
                            belongs_in_section = True
                        elif section == ImportSection.TYPE_DEFINITIONS.value and \
                            section_config.should_include(name, self.pattern_matcher):
                            belongs_in_section = True

                        if belongs_in_section:
                            imports.append(name)
                            imported_items.add(name)

                    if imports:
                        import_statement = f"from .{module_name} import {', '.join(sorted(imports))}"
                        section_imports.add(import_statement)

                # Add section if it has imports
                if section_imports:
                    self.progress.sections_generated += 1
                    if section_config.header_comment:
                        content.append(f"\n{section_config.header_comment}")
                    content.extend(sorted(section_imports))

            # Add exports declaration
            exports = self._collect_exports(module_info)
            if exports:
                content.extend([
                    "",
                    "__all__ = [",
                    *[f'    "{item}",' for item in sorted(exports)],
                    "]"
                ])

            return "\n".join(content)

        except Exception as e:
            context = ErrorContext(
                operation="generate_init_content",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=dir_path,
                details={
                    "num_modules": len(module_info),
                    "num_sections": len(config.sections)
                }
            )
            raise ProcessingError(
                "Failed to generate init content",
                context=context,
                original_error=e
            ) from e

    def _collect_exports(self, module_info: Dict[str, ModuleInfo]) -> Set[str]:
        """Collect all exports from module information.

        This method aggregates exports from all modules while handling
        potential conflicts and applying export filters.

        Args:
            module_info: Dictionary of module information

        Returns:
            Set of names to export

        Raises:
            ProcessingError: If export collection fails
        """
        try:
            exports = set()

            for info in module_info.values():
                exports.update(info.exports)

            return exports

        except Exception as e:
            context = ErrorContext(
                operation="collect_exports",
                error_code=ErrorCode.PROCESS_EXECUTION,
                details={"num_modules": len(module_info)}
            )
            raise ProcessingError(
                "Failed to collect exports",
                context=context,
                original_error=e
            ) from e

    def _format_preview(self) -> str:
        """Format changes for preview output.

        This method generates a human-readable preview of all changes
        that would be made to init files.

        Returns:
            Formatted preview text
        """
        preview_lines = []

        for path, content in sorted(self._changes.items()):
            rel_path = path.relative_to(self.root_dir)
            preview_lines.extend([
                f"\nFile: {rel_path}",
                "=" * (len(str(rel_path)) + 6),
                content,
                "-" * 80
            ])

        return "\n".join(preview_lines)

    def __repr__(self) -> str:
        return comprehensive_repr(self, prioritize=["root_dir", "config_path", "dry_run"], one_per_line=True)