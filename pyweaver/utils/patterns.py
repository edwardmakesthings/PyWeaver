"""Pattern matching utilities for file processing operations.

This module provides a robust system for matching file patterns, path patterns,
and content patterns. It implements an efficient pattern matching engine with
proper glob support and performance optimizations through caching.

The pattern matching system handles several types of patterns:
1. File patterns (e.g., "*.py", "test_*.js")
2. Path patterns (e.g., "src/**/*.ts")
3. Name patterns (e.g., "*Controller", "Base*")

The implementation uses a two-level caching strategy:
- Compiled regex patterns are cached for performance
- Path match results are cached to avoid redundant calculations

Path: pyweaver/utils/patterns.py
"""
import re
import logging
from pathlib import Path
from typing import Optional, Set, Dict, Pattern, NamedTuple

from pyweaver.utils.repr import comprehensive_repr
from pyweaver.common.errors import (ErrorContext, ErrorCode, ValidationError)

logger = logging.getLogger(__name__)

class PatternType(NamedTuple):
    """Information about a pattern's type and characteristics.

    This class helps classify patterns to optimize matching strategies.

    Attributes:
        has_wildcards: Whether pattern contains * or ?
        has_deep_wildcards: Whether pattern contains **
        is_absolute: Whether pattern represents absolute path
        is_negated: Whether pattern is negated with !
    """
    has_wildcards: bool
    has_deep_wildcards: bool
    is_absolute: bool
    is_negated: bool

class PatternCache:
    """Cache for compiled patterns and match results.

    This class manages both regex pattern compilation caching and
    path match result caching for optimal performance.

    Attributes:
        regex_patterns: Cache of compiled regex patterns
        match_results: Cache of path match results
        max_size: Maximum number of cached results
    """
    def __init__(self, max_size: int = 1000):
        """Initialize pattern cache.

        Args:
            max_size: Maximum number of cached results
        """
        self.regex_patterns: Dict[str, Pattern] = {}
        self.match_results: Dict[str, bool] = {}
        self.max_size = max_size

    def get_pattern(self, pattern: str) -> Optional[Pattern]:
        """Get cached compiled pattern."""
        return self.regex_patterns.get(pattern)

    def set_pattern(self, pattern: str, regex: Pattern) -> None:
        """Cache compiled pattern."""
        self.regex_patterns[pattern] = regex

        # Implement simple LRU by removing oldest if at capacity
        if len(self.regex_patterns) > self.max_size:
            self.regex_patterns.pop(next(iter(self.regex_patterns)))

    def get_result(self, key: str) -> Optional[bool]:
        """Get cached match result."""
        return self.match_results.get(key)

    def set_result(self, key: str, result: bool) -> None:
        """Cache match result."""
        self.match_results[key] = result

        # Implement simple LRU by removing oldest if at capacity
        if len(self.match_results) > self.max_size:
            self.match_results.pop(next(iter(self.match_results)))

    def clear(self) -> None:
        """Clear all cached data."""
        self.regex_patterns.clear()
        self.match_results.clear()

class PatternMatcher:
    """Utility for matching various types of patterns.

    This class provides efficient pattern matching capabilities for files,
    paths, and content patterns. It implements caching strategies for
    better performance and provides detailed error context for debugging.

    The matcher supports:
    - Glob patterns with * and ** wildcards
    - Path-specific pattern matching
    - Name pattern matching for exports
    - Pattern type classification
    - Result caching for performance

    Example:
        ```python
        matcher = PatternMatcher()

        # Configure root directory for relative path handling
        matcher.set_root_dir(Path.cwd())

        # Match file patterns
        if matcher.matches_path_pattern("src/test.py", "*.py"):
            # Process Python file
            pass

        # Match name patterns
        if matcher.matches_name_pattern("UserController", "*Controller"):
            # Process controller class
            pass
        ```
    """

    def __init__(
        self,
        root_dir: Optional[Path | str] = None,
        excluded_paths: Optional[Set[str]] = None,
        cache_size: int = 1000
    ):
        """Initialize matcher with configuration.

        Args:
            root_dir: Root directory for relative path handling
            excluded_paths: Set of glob patterns for paths to exclude
            cache_size: Maximum size of pattern caches
        """
        self.excluded_paths = excluded_paths or set()
        self.root_dir = Path(root_dir) if root_dir else None

        # Initialize caches
        self._path_cache = PatternCache(cache_size)
        self._name_cache = PatternCache(cache_size)

        if self.root_dir and not self.root_dir.is_absolute():
            try:
                self.root_dir = self.root_dir.resolve()
            except Exception as e:
                logger.error("Failed to resolve root directory path: %s", e)
                self.root_dir = None

        logger.debug(
            "Initialized PatternMatcher (root_dir=%s, excluded_paths=%d)",
            self.root_dir, len(self.excluded_paths)
        )

    def matches_path_pattern(self, path: Path | str, pattern: str) -> bool:
        """Match path-specific glob patterns with proper ** handling.

        This method provides efficient path pattern matching with support
        for both simple and complex glob patterns.

        Args:
            path: Path to check
            pattern: Glob pattern to match against

        Returns:
            True if path matches pattern

        Raises:
            ValidationError: If pattern is invalid
        """
        try:
            # Normalize path and pattern
            path_str = self._normalize_path(path)
            pattern = pattern.replace('\\', '/')

            # Check cache first
            cache_key = f"{path_str}:{pattern}"
            if cached := self._path_cache.get_result(cache_key):
                return cached

            # Get or create regex pattern
            regex = self._get_or_create_pattern(pattern)
            if regex is None:
                return False

            # Perform match
            matches = bool(regex.search(path_str))

            # Cache result
            self._path_cache.set_result(cache_key, matches)

            if matches:
                rel_path = self.get_relative_path(path_str)
                logger.debug(
                    "Path '%s' matched pattern '%s'",
                    rel_path, pattern
                )

            return matches

        except Exception as e:
            context = ErrorContext(
                operation="match_path",
                error_code=ErrorCode.VALIDATION_FORMAT,
                details={"pattern": pattern, "path": str(path)}
            )
            raise ValidationError(
                f"Invalid path pattern: {e}",
                context=context,
                original_error=e
            ) from e

    def matches_name_pattern(self, name: str, pattern: str) -> bool:
        """Match simple glob patterns for names.

        This method handles simple pattern matching for names like types,
        classes, and constants. It supports basic wildcards but not
        path-specific features.

        Args:
            name: Name to check
            pattern: Simple glob pattern to match against

        Returns:
            True if name matches pattern

        Raises:
            ValidationError: If pattern is invalid
        """
        try:
            # Check cache first
            cache_key = f"{name}:{pattern}"
            if cached := self._name_cache.get_result(cache_key):
                return cached

            # Convert to regex pattern
            regex_pattern = self._convert_name_pattern_to_regex(pattern)

            # Perform match
            matches = bool(re.match(regex_pattern, name))

            # Cache result
            self._name_cache.set_result(cache_key, matches)

            return matches

        except Exception as e:
            context = ErrorContext(
                operation="match_name",
                error_code=ErrorCode.VALIDATION_FORMAT,
                details={"pattern": pattern, "name": name}
            )
            raise ValidationError(
                f"Invalid name pattern: {e}",
                context=context,
                original_error=e
            ) from e

    def is_excluded_path(self, path: Path | str) -> bool:
        """Check if a path should be excluded.

        This method determines whether a path matches any of the configured
        exclusion patterns.

        Args:
            path: Path to check against exclusion patterns

        Returns:
            True if path matches any exclusion pattern
        """
        try:
            path_str = self._normalize_path(path)
            logger.debug("Checking exclusion patterns for path: %s", path_str)

            for pattern in self.excluded_paths:
                try:
                    if self.matches_path_pattern(path_str, pattern):
                        rel_path = self.get_relative_path(path_str)
                        logger.info(
                            "Excluding %s (matched pattern: %s)",
                            rel_path, pattern
                        )
                        return True
                except Exception as e:
                    logger.warning(
                        "Error checking exclusion pattern '%s': %s",
                        pattern, e
                    )

            return False

        except Exception as e:
            logger.error("Error checking path exclusion: %s", e, exc_info=True)
            return False

    def get_relative_path(self, path: Path | str) -> str:
        """Get path relative to root directory.

        This method converts absolute paths to paths relative to the
        configured root directory.

        Args:
            path: Path to convert

        Returns:
            Path as string relative to root_dir, or original path if no root_dir
        """
        if not self.root_dir:
            return str(path)

        try:
            path_obj = Path(path).resolve()
            rel_path = path_obj.relative_to(self.root_dir)
            return str(rel_path).replace('\\', '/')

        except (ValueError, RuntimeError) as e:
            logger.debug("Could not make path relative to root: %s", e)
            return str(path)

    def clear_caches(self) -> None:
        """Clear all pattern and result caches."""
        self._path_cache.clear()
        self._name_cache.clear()
        logger.debug("Cleared pattern matcher caches")

    def _normalize_path(self, path: Path | str) -> str:
        """Normalize path for consistent matching.

        Args:
            path: Path to normalize

        Returns:
            Normalized path string
        """
        return str(path).replace('\\', '/')

    def _get_or_create_pattern(self, pattern: str) -> Optional[Pattern]:
        """Get or create a compiled regex pattern.

        This method handles pattern compilation and caching for
        efficient matching.

        Args:
            pattern: Glob pattern to compile

        Returns:
            Compiled regex pattern or None if compilation fails
        """
        try:
            # Check cache first
            if cached := self._path_cache.get_pattern(pattern):
                return cached

            # Convert glob to regex and compile
            regex_pattern = self._convert_glob_to_regex(pattern)
            compiled = re.compile(regex_pattern)

            # Cache pattern
            self._path_cache.set_pattern(pattern, compiled)

            return compiled

        except re.error as e:
            logger.warning("Invalid pattern '%s': %s", pattern, e)
            return None

    def _convert_glob_to_regex(self, pattern: str) -> str:
        """Convert glob pattern to regex pattern.

        This method handles the conversion of glob-style patterns to
        proper regex patterns that handle all our matching needs.

        Args:
            pattern: Glob pattern to convert

        Returns:
            Regex pattern string
        """
        pattern_info = self._analyze_pattern(pattern)

        # Handle negation
        if pattern_info.is_negated:
            pattern = pattern[1:]

        # Handle leading dot
        if pattern.startswith('.'):
            pattern = pattern[1:]

        # Convert glob syntax to regex
        pattern = pattern.replace('**/', '.*?/')
        pattern = pattern.replace('/**', '/.*?')
        pattern = pattern.replace('*', '[^/]*')
        pattern = pattern.replace('?', '[^/]')

        # Add anchors if absolute
        if pattern_info.is_absolute:
            pattern = '^' + pattern

        return pattern

    def _convert_name_pattern_to_regex(self, pattern: str) -> str:
        """Convert name glob pattern to regex pattern.

        This method handles the conversion of simple name-matching
        patterns to regex patterns.

        Args:
            pattern: Name pattern to convert

        Returns:
            Regex pattern string
        """
        regex_pattern = pattern.replace('*', '[^/]*')
        return f"^{regex_pattern}$"

    def _analyze_pattern(self, pattern: str) -> PatternType:
        """Analyze pattern to determine its characteristics.

        This method examines a pattern to understand its type and
        features for optimized matching.

        Args:
            pattern: Pattern to analyze

        Returns:
            PatternType with pattern characteristics
        """
        return PatternType(
            has_wildcards='*' in pattern or '?' in pattern,
            has_deep_wildcards='**' in pattern,
            is_absolute=pattern.startswith('/') or pattern.startswith('\\'),
            is_negated=pattern.startswith('!')
        )

    def __repr__(self) -> str:
        """Get string representation of matcher state."""
        return comprehensive_repr(
            self,
            prioritize=["root_dir", "excluded_paths"],
            exclude=["_path_cache", "_name_cache"],
            one_per_line=True
        )
