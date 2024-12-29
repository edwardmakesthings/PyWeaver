"""Path configuration management for file processing operations.

This module provides configuration management focused on file paths and patterns.
It extends our base configuration system to handle path-specific settings while
maintaining consistent error handling and validation. The implementation supports
both global settings and path-specific overrides, allowing for flexible but
controlled configuration inheritance.

The module integrates with our broader configuration ecosystem by:
- Building on the base configuration validation system
- Using standardized error handling with proper context
- Providing path-specific pattern matching
- Supporting efficient configuration inheritance

When path-specific settings are applied, they follow clear inheritance rules:
- Pattern sets are combined (union of base and override patterns)
- Additional options are merged with override taking precedence
- Settings are cached for performance while maintaining consistency

Path: pyweaver/config/path.py
"""
import logging
from pathlib import Path
from typing import Dict, Set, Any, Optional, List, Union
from functools import lru_cache
from pydantic import BaseModel, Field, field_validator

from pyweaver.config.base import BaseConfig, ConfigValidationModel
from pyweaver.common.errors import (
    ConfigError, ErrorContext, ErrorCode, ValidationError
)
from pyweaver.utils.patterns import PatternMatcher
from pyweaver.utils.repr import comprehensive_repr

logger = logging.getLogger(__name__)

class PathSettings(BaseModel):
    """Settings that can be applied globally or to specific paths.

    This model defines the configuration options available for path-based
    settings, including pattern matching and processing options. It handles
    validation of patterns and ensures configuration consistency.

    Patterns can be specified in several formats:
    - Individual strings: "*.py"
    - Lists of strings: ["*.py", "test_*.py"]
    - Sets of strings: {"*.py", "test_*.py"}

    Pattern inheritance follows union semantics - when configs are merged,
    pattern sets are combined to ensure no patterns are lost while avoiding
    duplicates.

    Attributes:
        ignore_patterns: Patterns for files/directories to ignore
        include_patterns: Patterns to explicitly include
        additional_options: Processor-specific options
    """
    ignore_patterns: Set[str] = Field(
        default_factory=lambda: {
            "*.pyc",
            "__pycache__",
            ".git",
            ".venv",
            "node_modules"
        },
        description="Patterns for files/directories to ignore"
    )
    include_patterns: Set[str] = Field(
        default_factory=set,
        description="Patterns for files/directories to explicitly include"
    )
    additional_options: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processor-specific options"
    )

    @field_validator('ignore_patterns', 'include_patterns')
    @classmethod
    def validate_patterns(cls, v: Union[Set[str], str, List[str]]) -> Set[str]:
        """Validate and normalize glob patterns.

        This method ensures patterns are properly formatted and valid for
        use in path matching operations. It handles various input formats
        and provides clear error messages for invalid patterns.

        Args:
            v: Pattern(s) to validate (string, list, or set)

        Returns:
            Set of validated patterns

        Raises:
            ValidationError: If patterns are invalid
        """
        try:
            # Convert input to set if needed
            if isinstance(v, str):
                v = {v}
            elif isinstance(v, (list, tuple)):
                v = set(v)
            elif not isinstance(v, set):
                raise ValueError(
                    f"Expected string, list, or set, got {type(v)}"
                )

            # Validate each pattern
            validated = set()
            for pattern in v:
                if not isinstance(pattern, str):
                    raise ValueError(
                        f"Pattern must be string, got {type(pattern)}"
                    )
                if not pattern:
                    raise ValueError("Empty patterns not allowed")
                if len(pattern) > 1000:
                    raise ValueError("Pattern too long")
                if pattern.startswith('**') and not pattern.startswith('**/'):
                    raise ValueError(
                        "Invalid glob pattern: '**' must be followed by '/'"
                    )
                validated.add(pattern)

            return validated

        except Exception as e:
            context = ErrorContext(
                operation="validate_patterns",
                error_code=ErrorCode.VALIDATION_FORMAT,
                details={"patterns": list(v) if isinstance(v, (set, list)) else v}
            )
            raise ValidationError(
                f"Pattern validation failed: {str(e)}",
                context=context,
                original_error=e
            ) from e

class PathConfig(BaseConfig[PathSettings]):
    """Configuration manager supporting global and path-specific settings.

    This class provides comprehensive path-based configuration management,
    supporting both global settings and path-specific overrides. It maintains
    efficient caching of both settings and pattern matching results while
    ensuring configuration consistency.

    The configuration system supports:
    - Global default settings
    - Path-specific setting overrides
    - Pattern-based path matching
    - Configuration inheritance
    - Performance optimization through caching

    Example:
        ```python
        config = PathConfig(
            global_settings={
                "ignore_patterns": {"*.pyc"},
                "include_patterns": {"*.py"}
            },
            path_specific={
                "src": {
                    "ignore_patterns": {"*.test.py"}
                }
            }
        )

        # Get settings for a specific path
        settings = config.get_settings_for_path("src/module.py")

        # Check if path matches patterns
        if not config.matches_any_pattern(path, settings.ignore_patterns):
            # Process the file...
            pass
        ```
    """

    def __init__(
        self,
        global_settings: Optional[Dict[str, Any]] = None,
        path_specific: Optional[Dict[str, Dict[str, Any]]] = None,
        pattern_matcher: Optional[PatternMatcher] = None
    ):
        """Initialize path configuration.

        Args:
            global_settings: Default settings applied globally
            path_specific: Dictionary mapping paths to their settings
            pattern_matcher: Optional pattern matcher instance

        Raises:
            ConfigError: If configuration validation fails
        """
        try:
            super().__init__(global_settings, path_specific)
            self.pattern_matcher = pattern_matcher or PatternMatcher()
            self._settings_cache: Dict[Path, PathSettings] = {}

            logger.debug(
                "Initialized PathConfig with %d path-specific settings",
                len(self.path_specific)
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_pathconfig",
                error_code=ErrorCode.CONFIG_INIT,
                details={
                    "has_global": bool(global_settings),
                    "path_count": len(path_specific) if path_specific else 0
                }
            )
            raise ConfigError(
                "Failed to initialize path configuration",
                context=context,
                original_error=e
            ) from e

    def matches_any_pattern(self, path: Path | str, patterns: Set[str]) -> bool:
        """Check if a path matches any of the given patterns.

        This method provides efficient pattern matching with caching for
        improved performance on repeated operations.

        Args:
            path: Path to check
            patterns: Set of patterns to match against

        Returns:
            True if path matches any pattern
        """
        try:
            # Normalize path for consistent matching
            path_str = str(path).replace('\\', '/')

            # Check each pattern with caching
            return any(
                self._match_pattern_cached(path_str, pattern)
                for pattern in patterns
            )

        except Exception as e:
            logger.warning(
                "Pattern matching failed for %s: %s",
                path, e
            )
            return False

    def _validate_config(
        self,
        config_data: Dict[str, Any]
    ) -> ConfigValidationModel[PathSettings]:
        """Validate raw configuration data.

        This method ensures the configuration data meets our requirements
        and provides proper error context if validation fails.

        Args:
            config_data: Raw configuration dictionary

        Returns:
            Validated configuration model

        Raises:
            ConfigError: If validation fails
        """
        try:
            return ConfigValidationModel[PathSettings](**config_data)
        except Exception as e:
            context = ErrorContext(
                operation="validate_config",
                error_code=ErrorCode.CONFIG_VALIDATION,
                details={
                    "error": str(e),
                    "config_keys": list(config_data.keys())
                }
            )
            raise ConfigError(
                "Configuration validation failed",
                context=context,
                original_error=e
            ) from e

    def _merge_settings(
        self,
        base: PathSettings,
        path_settings: Optional[PathSettings]
    ) -> PathSettings:
        """Merge path-specific settings into base settings.

        This method implements the strategy for combining base settings
        with path-specific overrides, ensuring proper inheritance of
        patterns and options.

        Args:
            base: Base settings to start from
            path_settings: Optional path-specific settings to merge

        Returns:
            New PathSettings instance with merged configuration
        """
        if not path_settings:
            return base.model_copy()

        try:
            # Create new settings with merged values
            return PathSettings(
                ignore_patterns=base.ignore_patterns | path_settings.ignore_patterns,
                include_patterns=base.include_patterns | path_settings.include_patterns,
                additional_options={
                    **base.additional_options,
                    **path_settings.additional_options
                }
            )

        except Exception as e:
            context = ErrorContext(
                operation="merge_settings",
                error_code=ErrorCode.CONFIG_MERGE,
                details={
                    "base_patterns": len(base.ignore_patterns),
                    "override_patterns": len(path_settings.ignore_patterns)
                }
            )
            raise ConfigError(
                "Failed to merge settings",
                context=context,
                original_error=e
            ) from e

    @lru_cache(maxsize=1000)
    def _match_pattern_cached(self, path: str, pattern: str) -> bool:
        """Cached pattern matching for improved performance.

        This method caches pattern matching results to improve performance
        for frequently checked paths and patterns.

        Args:
            path: Normalized path string
            pattern: Pattern to match against

        Returns:
            True if path matches pattern
        """
        try:
            return self.pattern_matcher.matches_path_pattern(path, pattern)
        except Exception as e:
            logger.warning(
                "Pattern matching failed: %s vs %s: %s",
                path, pattern, e
            )
            return False

    def clear_cache(self) -> None:
        """Clear all caches to ensure fresh pattern matching.

        This method should be called when configuration changes or when
        memory needs to be freed.
        """
        self._settings_cache.clear()
        self._match_pattern_cached.cache_clear()
        logger.debug("Cleared path configuration caches")

    def __repr__(self) -> str:
        """Get string representation of configuration."""
        return comprehensive_repr(
            self,
            prioritize=["global_settings", "path_specific"],
            exclude=["_settings_cache"],
            one_per_line=True
        )
