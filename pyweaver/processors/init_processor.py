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
from typing import Dict, Optional, Set, List, Any, Union
from dataclasses import dataclass

from pyweaver.common.base import BaseProcessor, ProcessorProgress, ProcessorResult
from pyweaver.common.tracking import TrackerType
from pyweaver.common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)
from pyweaver.config.init import InitConfig, ImportSection, InitSettings
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
                output_file: Optional[Path | str] = None,
                print_preview: bool = False,
                return_dict: bool = False
    ) -> Union[str, Dict[Path, str]]:
        """Preview changes that would be made to init files.

        This method performs a dry run of the processing operation, generating a
        formatted preview of all changes that would be made.

        Args:
            output_file: Optional path to save preview content
            print_preview: If True, print preview to console
            return_dict: If True, return changes as dictionary instead of formatted text

        Returns:
            Formatted preview of all changes

        Raises:
            ProcessingError: If preview generation fails
            FileError: If preview file cannot be written
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
                if print_preview or output_file:
                    preview_text = self._format_preview()

                    if print_preview:
                        print(preview_text)

                    if output_file:
                        output_path = Path(output_file)
                        output_path.parent.mkdir(parents=True, exist_ok=True)
                        output_path.write_text(preview_text, encoding="utf-8")

                return self._changes.copy() if return_dict else preview_text

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

    def get_changes(self) -> Dict[Path, str]:
        """Get changes made to init files during processing.

        Returns:
            Dictionary mapping file paths to their content
        """
        return self._changes.copy()

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
            # Get settings directly from init_config
            settings = self.init_config.get_settings_for_path(path)

            # Skip if path should be excluded
            if self.init_config.pattern_matcher.is_excluded_path(path):
                self._add_warning(f"Skipping excluded path: {path}")
                return

            # Collect module information
            module_info = self._collect_module_info(path, settings)
            if not module_info:
                logger.debug("No modules found in %s", path)
                return

            self.progress.modules_analyzed += len(module_info)

            # Generate content
            content = self._generate_init_content(path, module_info, settings)
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

    def _collect_module_info(
        self,
        dir_path: Path,
        settings: InitSettings
    ) -> Dict[str, ModuleInfo]:
        """Collect information about modules in a directory.

        This method analyzes Python modules in a directory to extract information
        about their exports, classes, functions, and dependencies.

        Args:
            dir_path: Directory to analyze
            settings: Configuration settings from InitConfig

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
            if settings.collect_from_submodules:
                for subdir in dir_path.iterdir():
                    if not subdir.is_dir():
                        continue

                    # Skip if excluded
                    if self.init_config.pattern_matcher.is_excluded_path(subdir):
                        continue

                    # Skip if not in included submodules
                    if (settings.include_submodules and
                        subdir.name not in settings.include_submodules):
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
                details={"config": str(settings)}
            )
            raise ProcessingError(
                "Failed to collect module information",
                context=context,
                original_error=e
            ) from e

    def _generate_init_content(
        self,
        dir_path: Path,
        module_info: Dict[str, ModuleInfo],
        settings: InitSettings
    ) -> Optional[str]:
        """Generate content for an init file.

        This method generates the content for an __init__.py file based on
        the collected module information and configuration settings.

        Args:
            dir_path: Directory being processed
            module_info: Information about modules
            settings: Configuration settings from InitConfig

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
                rel_path = dir_path

            # Initialize content with docstring
            content = [f'"""{settings.docstring}\n']

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
                [(section, cfg) for section, cfg in settings.sections.items() if cfg.enabled],
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
                    "num_sections": len(settings.sections)
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

    def _write_output(self, path: Path) -> None:
        """Write all init files to disk.

        Implements BaseProcessor._write_output() for init file generation.
        Note that path parameter is ignored as init files are written to
        their respective locations.
        """
        try:
            for file_path, content in self._changes.items():
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    file_path.write_text(content)
                    logger.info("Wrote init file: %s", file_path)
                except Exception as e:
                    raise FileError(
                        f"Failed to write init file: {e}",
                        path=file_path,
                        operation="write_init"
                    ) from e

        except Exception as e:
            context = ErrorContext(
                operation="write_init_files",
                error_code=ErrorCode.FILE_WRITE,
                path=path  # Original target path
            )
            raise ProcessingError(
                "Failed to write init files",
                context=context,
                original_error=e
            ) from e

    def __repr__(self) -> str:
        """Get string representation of processor state."""
        return comprehensive_repr(
            self,
            exclude=['_changes'],
            prioritize=['root_dir', 'dry_run'],
            one_per_line=True
        )

def generate_init_files(
    root_dir: str | Path,
    print_output: bool = False,
    print_only: bool = False,
    docstring: Optional[str] = None,
    collect_submodules: bool = True,
    exclude_patterns: Optional[Set[str]] = None,
    preview: bool = False,
    config_path: Optional[str | Path] = None,
    include_submodules: Optional[List[str]] = None,
    order_policy: Optional[str] = None,
    exports_blacklist: Optional[Set[str]] = None,
    sections: Optional[Dict[str, Any]] = None,
    exact_path_only: bool = False,
    export_mode: Optional[str] = None
) -> Dict[Path, str]:
    """Generate or update __init__.py files across a project.

    This convenience function provides a simpler interface to the InitFileProcessor
    for common use cases. It properly handles configuration settings and allows
    for customization through explicit parameters.

    Args:
        root_dir: Root directory of the project
        print_output: If True, print init files as 1 file to console
        print_only: If True, only print output and don't write files
        docstring: Optional default docstring for __init__.py files
        collect_submodules: Whether to collect exports from submodules. This affects
                          whether the processor will look for exports in subdirectories
        exclude_patterns: Patterns for paths to exclude from processing
        preview: If True, return changes without writing files
        config_path: Optional path to configuration file
        include_submodules: List of specific submodules to include
        order_policy: How to order imports ("dependency_first", "alphabetical", etc.)
        exports_blacklist: Set of names to exclude from exports
        sections: Dictionary of section configurations
        exact_path_only: Whether to use exact path matching
        export_mode: How to determine exports

    Returns:
        Dictionary mapping file paths to their content (if preview=True)
        or to their status message (if preview=False)

    Raises:
        ProcessingError: If init file generation fails
        ValidationError: If configuration is invalid
        FileError: If file operations fail

    Example:
        ```python
        # Basic generation with submodule collection
        generate_init_files("src", collect_submodules=True)

        # Advanced usage with custom configuration
        generate_init_files(
            "src",
            docstring="Package initialization.",
            collect_submodules=True,
            exclude_patterns={"tests", "docs"},
            order_policy="alphabetical",
            include_submodules=["core", "utils"]
        )
        ```
    """
    try:
        # Initialize processor
        processor = InitFileProcessor(
            root_dir=root_dir,
            config_path=config_path,
            dry_run=preview
        )

        # Update configuration with provided settings
        settings = processor.init_config.global_settings

        # Base settings
        settings.collect_from_submodules = collect_submodules

        if docstring is not None:
            settings.docstring = docstring

        if exclude_patterns:
            settings.excluded_paths.update(exclude_patterns)

        # Optional configuration settings
        if include_submodules is not None:
            settings.include_submodules = include_submodules

        if order_policy is not None:
            settings.order_policy = order_policy

        if exports_blacklist is not None:
            settings.exports_blacklist = exports_blacklist

        if sections is not None:
            settings.sections = sections

        settings.exact_path_only = exact_path_only

        if export_mode is not None:
            settings.export_mode = export_mode

        # Process files
        # result = processor.process()

        # Handle output options
        if print_output or print_only:
            processor.preview(print_preview=True)

        if not print_only:
            processor.write()

        return processor.get_changes()

    except Exception as e:
        return ProcessorResult(
            success=False,
            message=str(e),
            errors=[str(e)]
        )