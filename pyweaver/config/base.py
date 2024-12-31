"""Base configuration system for file processing operations.

This module establishes the foundation for all configuration handling in the system.
It implements a hierarchical configuration system that supports inheritance,
validation, and type safety. The design allows for both global settings and
path-specific overrides while ensuring configuration integrity through comprehensive
validation.

Key features:
- Type-safe configuration through Pydantic models
- Hierarchical configuration with inheritance
- JSON schema support for validation
- Comprehensive error handling
- Configuration merging strategies
- Cache management for performance

Path: pyweaver/config/base.py
"""
from pathlib import Path
from typing import Dict, Any, Optional, Generic, TypeVar, get_args
import json
import logging
from abc import ABC, abstractmethod
from pydantic import BaseModel, Field, field_validator

from pyweaver.common.errors import (ConfigError, ErrorContext, ErrorCode)

logger = logging.getLogger(__name__)

# Type variable for settings models
SettingsT = TypeVar('SettingsT', bound=BaseModel)

class ConfigValidationModel(BaseModel, Generic[SettingsT]):
    """Base model for configuration validation.

    This model provides the foundation for validating configuration data,
    ensuring type safety and structural correctness. It supports generic
    settings types while maintaining strict validation.

    Attributes:
        global_settings: Default settings applied globally
        path_specific: Dictionary of path-specific setting overrides
    """
    global_settings: SettingsT
    path_specific: Dict[Path, SettingsT] = Field(default_factory=dict)

    model_config = {
        "arbitrary_types_allowed": True,
        "json_encoders": {
            Path: str
        }
    }

    @field_validator('path_specific')
    @classmethod
    def validate_paths(cls, v: Dict) -> Dict[Path, Any]:
        """Validate and normalize path dictionary keys.

        This method ensures all paths in the configuration are properly
        normalized and valid.

        Args:
            v: Dictionary of path-specific settings to validate

        Returns:
            Dictionary with validated and normalized paths

        Raises:
            ValueError: If paths are invalid
        """
        validated = {}
        for path, settings in v.items():
            try:
                if isinstance(path, str):
                    path = Path(path)
                validated[path] = settings
            except Exception as e:
                raise ValueError(f"Invalid path '{path}': {e}") from e
        return validated

    @field_validator('global_settings')
    @classmethod
    def validate_settings(cls, v: Any) -> SettingsT:
        """Validate global settings against the settings model.

        This method ensures the global settings conform to the expected
        settings model type.

        Args:
            v: Settings to validate

        Returns:
            Validated settings instance

        Raises:
            ValueError: If settings are invalid
        """
        try:
            settings_type = get_args(cls.__orig_bases__[0])[0]
            if not isinstance(v, settings_type):
                raise ValueError(
                    f"Global settings must be instance of {settings_type.__name__}"
                )
        except (IndexError, AttributeError):
            settings_type = cls.__annotations__.get('global_settings', dict)
        return settings_type(**v) if isinstance(v, dict) else v

class BaseConfig(ABC, Generic[SettingsT]):
    """Abstract base class for configuration management.

    This class provides the core functionality for managing configurations,
    including loading, validation, and settings retrieval. It maintains
    type safety through generic typing while allowing for customization
    in derived classes.

    Example:
        ```python
        class MySettings(BaseModel):
            setting1: str
            setting2: int

        class MyConfig(BaseConfig[MySettings]):
            def _validate_config(self, data):
                return ConfigValidationModel[MySettings](**data)

            def _merge_settings(self, base, override):
                return MySettings(
                    setting1=override.setting1 or base.setting1,
                    setting2=override.setting2 or base.setting2
                )

        # Use the configuration
        config = MyConfig(global_settings={"setting1": "value", "setting2": 42})
        settings = config.get_settings_for_path("some/path")
        ```
    """

    def __init__(
        self,
        global_settings: Optional[Dict[str, Any]] = None,
        path_specific: Optional[Dict[str, Dict[str, Any]]] = None
    ):
        """Initialize configuration with validation.

        Args:
            global_settings: Default settings applied to all paths
            path_specific: Dictionary mapping paths to their specific settings

        Raises:
            ConfigError: If configuration validation fails
        """
        try:
            # Create and validate configuration
            validated = self._validate_config({
                "global_settings": global_settings or {},
                "path_specific": path_specific or {}
            })

            self.global_settings = validated.global_settings
            self.path_specific = validated.path_specific

            # Initialize cache
            self._settings_cache: Dict[Path, SettingsT] = {}

            logger.debug(
                "Initialized configuration with %d path-specific settings",
                len(self.path_specific)
            )

        except Exception as e:
            context = ErrorContext(
                operation="init_config",
                error_code=ErrorCode.CONFIG_VALIDATION,
                details={"error": str(e)}
            )
            logger.error("Configuration validation failed: %s", e)
            raise ConfigError(
                "Configuration validation failed",
                context=context,
                original_error=e
            ) from e

    @classmethod
    def from_file(cls, config_path: Path | str) -> 'BaseConfig':
        """Create configuration from JSON file.

        This method loads and validates configuration from a JSON file,
        providing proper error handling and context.

        Args:
            config_path: Path to configuration file

        Returns:
            Initialized configuration instance

        Raises:
            ConfigError: If file reading or validation fails
        """
        try:
            if isinstance(config_path, str):
                config_path = Path(config_path)

            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            return cls(**config_data)

        except json.JSONDecodeError as e:
            context = ErrorContext(
                operation="read_config",
                error_code=ErrorCode.CONFIG_PARSE,
                path=config_path,
                details={
                    "error_line": e.lineno,
                    "error_col": e.colno,
                    "error_msg": e.msg
                }
            )
            raise ConfigError(
                f"Failed to parse configuration file: {e.msg}",
                context=context,
                original_error=e
            ) from e

        except Exception as e:
            context = ErrorContext(
                operation="load_config",
                error_code=ErrorCode.CONFIG_PATH,
                path=config_path
            )
            raise ConfigError(
                "Failed to load configuration file",
                context=context,
                original_error=e
            ) from e

    def get_settings_for_path(self, path: Path | str) -> SettingsT:
        """Get effective settings for a specific path.

        This method combines global settings with any path-specific overrides
        that apply to the given path. Results are cached for performance.

        Args:
            path: Path to get settings for

        Returns:
            Settings instance with combined configuration

        Raises:
            ConfigError: If settings cannot be retrieved
        """
        try:
            if isinstance(path, str):
                path = Path(path)

            # Check cache first
            if path in self._settings_cache:
                return self._settings_cache[path]

            # Start with global settings
            effective_settings = self._merge_settings(
                self.global_settings,
                path_settings=None
            )

            # Apply any matching path-specific settings
            for config_path, settings in self.path_specific.items():
                if self._is_path_match(path, config_path):
                    effective_settings = self._merge_settings(
                        effective_settings,
                        settings
                    )

            # Cache and return results
            self._settings_cache[path] = effective_settings
            return effective_settings

        except Exception as e:
            context = ErrorContext(
                operation="get_settings",
                error_code=ErrorCode.CONFIG_PATH,
                path=path,
                details={
                    "config_paths": [str(p) for p in self.path_specific.keys()]
                }
            )
            raise ConfigError(
                f"Failed to get configuration settings for {path}",
                context=context,
                original_error=e
            ) from e

    def clear_cache(self) -> None:
        """Clear the settings cache.

        This method should be called when configuration changes or when
        memory needs to be freed.
        """
        self._settings_cache.clear()
        logger.debug("Cleared settings cache")

    def _is_path_match(self, path: Path, config_path: Path) -> bool:
        """Check if a path matches a configuration path.

        This method determines whether a given path should inherit settings
        from a configuration path.

        Args:
            path: Path to check
            config_path: Configuration path to match against

        Returns:
            True if path matches the configuration path
        """
        try:
            return str(path).startswith(str(config_path))
        except Exception:
            return False

    @abstractmethod
    def _validate_config(self, config_data: Dict[str, Any]) -> ConfigValidationModel[SettingsT]:
        """Validate raw configuration data.

        This method must be implemented by concrete classes to provide
        their specific validation logic.

        Args:
            config_data: Raw configuration dictionary

        Returns:
            Validated configuration model
        """
        raise NotImplementedError

    @abstractmethod
    def _merge_settings(
        self,
        base: SettingsT,
        path_settings: Optional[SettingsT]
    ) -> SettingsT:
        """Merge path-specific settings into base settings.

        This method must be implemented by concrete classes to define
        how settings should be combined.

        Args:
            base: Base settings to start from
            path_settings: Optional path-specific settings to merge

        Returns:
            New settings instance with merged configuration
        """
        raise NotImplementedError
