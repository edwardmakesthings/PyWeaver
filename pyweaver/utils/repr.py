"""Object representation generation utilities.

This module provides sophisticated tools for generating string representations of
Python objects. It handles complex scenarios like circular references, deep object
hierarchies, and custom formatting requirements. The implementation supports both
basic string representation needs and advanced formatting scenarios.

Key features include:
- Circular reference detection
- Customizable formatting options
- Type-specific handling
- Depth control
- Memory-efficient processing
- Comprehensive documentation

Path: pyweaver/utils/repr.py
"""
from typing import (
    Any, Optional, List, Set, Callable, TypeVar, Union, Iterable
)
from dataclasses import is_dataclass, fields
from datetime import datetime, date
from pathlib import Path
from enum import Enum

T = TypeVar('T')

class ReprConfig:
    """Configuration for representation generation.

    This class centralizes all configuration options for generating string
    representations, making it easier to customize output formatting and
    control representation behavior.

    Attributes:
        indent_size: Number of spaces for each indent level
        max_depth: Maximum recursion depth for nested objects
        max_length: Maximum length for generated strings
        max_items: Maximum number of items to show for collections
        show_private: Whether to include private attributes
        show_dunder: Whether to include dunder methods
        show_callable: Whether to include callable attributes
        sort_keys: Whether to sort dictionary keys and attributes
        use_oneline: Whether to generate one-line output
        show_types: Whether to include type information
        recursion_marker: String to indicate recursive references
        truncation_marker: String to indicate truncated content
    """
    def __init__(
        self,
        indent_size: int = 4,
        max_depth: int = 10,
        max_length: Optional[int] = None,
        max_items: Optional[int] = None,
        show_private: bool = False,
        show_dunder: bool = False,
        show_callable: bool = False,
        sort_keys: bool = True,
        use_oneline: bool = False,
        show_types: bool = False,
        recursion_marker: str = "...",
        truncation_marker: str = "..."
    ):
        """Initialize representation configuration."""
        self.indent_size = indent_size
        self.max_depth = max_depth
        self.max_length = max_length
        self.max_items = max_items
        self.show_private = show_private
        self.show_dunder = show_dunder
        self.show_callable = show_callable
        self.sort_keys = sort_keys
        self.use_oneline = use_oneline
        self.show_types = show_types
        self.recursion_marker = recursion_marker
        self.truncation_marker = truncation_marker

    def get_indent(self, depth: int) -> str:
        """Get indentation string for given depth."""
        return " " * (self.indent_size * depth)

def comprehensive_repr(
    obj: Any,
    exclude: Optional[List[str]] = None,
    prioritize: Optional[List[str]] = None,
    include_private: bool = False,
    include_callable: bool = False,
    sort_keys: bool = False,
    max_length: Optional[int] = None,
    one_per_line: bool = False,
    filter_func: Optional[Callable[[str, Any], bool]] = None,
    config: Optional[ReprConfig] = None,
    _depth: int = 0,
    _visited: Optional[Set[int]] = None
) -> str:
    """Generate a comprehensive string representation of an object.

    This function creates detailed string representations of Python objects,
    handling complex scenarios like circular references and deep hierarchies.
    It provides extensive customization options for controlling output format
    and content.

    The function supports:
    - Custom attribute filtering and ordering
    - Circular reference detection
    - Type-specific formatting
    - Depth-based recursion control
    - Memory-efficient processing

    Args:
        obj: Object to represent
        exclude: Attributes to exclude
        prioritize: Attributes to list first
        include_private: Include attributes starting with underscore
        include_callable: Include methods and callable attributes
        sort_keys: Sort attributes alphabetically
        max_length: Truncate result to this length
        one_per_line: Put each attribute on new line
        filter_func: Custom attribute filter function
        config: Optional configuration settings
        _depth: Internal recursion depth counter
        _visited: Internal set of visited object IDs

    Returns:
        Formatted string representation

    Example:
        ```python
        class Complex:
            def __init__(self):
                self.real = 1
                self.imag = 2
                self._private = 3

        obj = Complex()

        # Basic representation
        print(comprehensive_repr(obj))
        # Complex(real=1, imag=2)

        # Include private attributes
        print(comprehensive_repr(obj, include_private=True))
        # Complex(real=1, imag=2, _private=3)

        # One attribute per line
        print(comprehensive_repr(obj, one_per_line=True))
        # Complex(
        #     real=1
        #     imag=2
        # )
        ```
    """
    # Initialize configuration
    config = config or ReprConfig()
    if _visited is None:
        _visited = set()

    # Check recursion limits
    if _depth > config.max_depth:
        return f"{obj.__class__.__name__}({config.recursion_marker})"

    obj_id = id(obj)
    if obj_id in _visited:
        return f"{obj.__class__.__name__}({config.recursion_marker})"

    _visited.add(obj_id)

    try:
        # Initialize representation components
        exclude = exclude or []
        prioritize = prioritize or []
        attributes = []

        # Setup formatting
        indent = config.get_indent(_depth + 1) if one_per_line else ""
        joiner = f"\n{indent}" if one_per_line else ", "
        starter = f"\n{indent}" if one_per_line else ""

        # Handle different types of objects
        if isinstance(obj, (str, int, float, bool, type(None))):
            return repr(obj)

        elif isinstance(obj, (datetime, date)):
            return repr(obj)

        elif isinstance(obj, Path):
            return f"Path('{obj}')"

        elif isinstance(obj, Enum):
            return f"{obj.__class__.__name__}.{obj.name}"

        elif isinstance(obj, (list, tuple, set)):
            return _format_sequence(obj, config, _depth, _visited)

        elif isinstance(obj, dict):
            return _format_dict(obj, config, _depth, _visited)

        elif is_dataclass(obj):
            return _format_dataclass(obj, config, _depth, _visited)

        # Process object attributes
        attributes.extend(_process_prioritized_attributes(
            obj, prioritize, exclude, config, _depth, _visited
        ))

        attributes.extend(_process_regular_attributes(
            obj, prioritize, exclude, include_private,
            include_callable, filter_func, config, _depth, _visited
        ))

        if sort_keys:
            attributes.sort()

        # Format final output
        class_name = obj.__class__.__name__
        content = joiner.join(attributes)

        if one_per_line:
            result = f"{class_name}({starter}{content}\n{' ' * (_depth * config.indent_size)})"
        else:
            result = f"{class_name}({content})"

        # Apply length limit if specified
        if max_length and len(result) > max_length:
            result = result[:max_length-3] + config.truncation_marker

        # Add exclusion information if needed
        if exclude:
            excluded_str = ", ".join(exclude)
            if one_per_line:
                result += f"\n{' ' * (_depth * config.indent_size)}# Excluded: {excluded_str}"
            else:
                result += f" # Excluded: {excluded_str}"

        return result

    finally:
        _visited.discard(obj_id)

def _format_sequence(
    obj: Union[list, tuple, set],
    config: ReprConfig,
    depth: int,
    visited: Set[int]
) -> str:
    """Format sequence-like objects.

    This function handles the formatting of lists, tuples, and sets,
    applying proper type markers and handling nested elements.

    Args:
        obj: Sequence to format
        config: Formatting configuration
        depth: Current recursion depth
        visited: Set of visited object IDs

    Returns:
        Formatted string representation
    """
    # Determine sequence type markers
    if isinstance(obj, tuple):
        start, end = "(", ")"
    elif isinstance(obj, set):
        start, end = "{", "}"
    else:  # list
        start, end = "[", "]"

    # Handle empty sequences
    if not obj:
        return f"{start}{end}"

    # Apply item limit if configured
    items = list(obj)
    if config.max_items:
        items = items[:config.max_items]
        truncated = len(obj) > config.max_items
    else:
        truncated = False

    # Format items
    formatted = [
        comprehensive_repr(
            item,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        for item in items
    ]

    if truncated:
        formatted.append(config.truncation_marker)

    # Join items with appropriate formatting
    if config.use_oneline:
        content = ", ".join(formatted)
    else:
        indent = config.get_indent(depth + 1)
        content = f",\n{indent}".join(formatted)
        if not config.use_oneline:
            return f"{start}\n{indent}{content}\n{config.get_indent(depth)}{end}"

    return f"{start}{content}{end}"

def _format_dict(
    obj: dict,
    config: ReprConfig,
    depth: int,
    visited: Set[int]
) -> str:
    """Format dictionary objects.

    This function handles dictionary formatting with support for
    nested structures and key sorting.

    Args:
        obj: Dictionary to format
        config: Formatting configuration
        depth: Current recursion depth
        visited: Set of visited object IDs

    Returns:
        Formatted string representation
    """
    if not obj:
        return "{}"

    # Prepare items for formatting
    items = list(obj.items())
    if config.sort_keys:
        items.sort(key=lambda x: str(x[0]))

    if config.max_items:
        items = items[:config.max_items]
        truncated = len(obj) > config.max_items
    else:
        truncated = False

    # Format key-value pairs
    formatted = []
    for key, value in items:
        key_repr = comprehensive_repr(
            key,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        value_repr = comprehensive_repr(
            value,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        formatted.append(f"{key_repr}: {value_repr}")

    if truncated:
        formatted.append(config.truncation_marker)

    # Apply formatting
    if config.use_oneline:
        content = ", ".join(formatted)
        return f"{{{content}}}"
    else:
        indent = config.get_indent(depth + 1)
        content = f",\n{indent}".join(formatted)
        return f"{{\n{indent}{content}\n{config.get_indent(depth)}}}"

def _format_dataclass(
    obj: Any,
    config: ReprConfig,
    depth: int,
    visited: Set[int]
) -> str:
    """Format dataclass instances.

    This function provides specialized formatting for dataclass instances,
    respecting field ordering and metadata.

    Args:
        obj: Dataclass instance to format
        config: Formatting configuration
        depth: Current recursion depth
        visited: Set of visited object IDs

    Returns:
        Formatted string representation
    """
    items = []
    for field in fields(obj):
        if not config.show_private and field.name.startswith('_'):
            continue

        value = getattr(obj, field.name)
        value_repr = comprehensive_repr(
            value,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        items.append(f"{field.name}={value_repr}")

    if config.use_oneline:
        content = ", ".join(items)
        return f"{obj.__class__.__name__}({content})"
    else:
        indent = config.get_indent(depth + 1)
        content = f",\n{indent}".join(items)
        return (
            f"{obj.__class__.__name__}(\n"
            f"{indent}{content}\n"
            f"{config.get_indent(depth)})"
        )

def _process_prioritized_attributes(
    obj: Any,
    prioritize: List[str],
    exclude: List[str],
    config: ReprConfig,
    depth: int,
    visited: Set[int]
) -> List[str]:
    """Process prioritized attributes for representation.

    This function handles attributes that should appear first in the
    representation, applying proper formatting and filtering.

    Args:
        obj: Object being processed
        prioritize: Attributes to prioritize
        exclude: Attributes to exclude
        config: Formatting configuration
        depth: Current recursion depth
        visited: Set of visited object IDs

    Returns:
        List of formatted attribute strings
    """
    attributes = []
    for attr in prioritize:
        if attr in exclude or not hasattr(obj, attr):
            continue

        value = getattr(obj, attr)
        if not config.show_callable and callable(value):
            continue

        value_repr = comprehensive_repr(
            value,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        attributes.append(f"{attr}={value_repr}")
    return attributes

def _process_regular_attributes(
    obj: Any,
    prioritize: List[str],
    exclude: List[str],
    include_private: bool,
    include_callable: bool,
    filter_func: Optional[Callable[[str, Any], bool]],
    config: ReprConfig,
    depth: int,
    visited: Set[int]
) -> List[str]:
    """Process regular (non-prioritized) attributes.

    This function handles the bulk of attribute processing, applying
    filtering rules and formatting configurations.

    Args:
        obj: Object being processed
        prioritize: Already processed attributes to skip
        exclude: Attributes to exclude
        include_private: Whether to include private attributes
        include_callable: Whether to include callable attributes
        filter_func: Optional custom filter function
        config: Formatting configuration
        depth: Current recursion depth
        visited: Set of visited object IDs

    Returns:
        List of formatted attribute strings
    """
    attributes = []
    for key, value in _get_attributes(obj):
        # Skip already processed or excluded attributes
        if key in prioritize or key in exclude:
            continue

        # Skip private attributes if not included
        if not include_private and key.startswith('_'):
            continue

        # Skip callable attributes if not included
        if not include_callable and callable(value):
            continue

        # Apply custom filter if provided
        if filter_func and not filter_func(key, value):
            continue

        # Format and add the attribute
        value_repr = comprehensive_repr(
            value,
            config=config,
            _depth=depth + 1,
            _visited=visited
        )
        attributes.append(f"{key}={value_repr}")

    return attributes

def _get_attributes(obj: Any) -> Iterable[tuple[str, Any]]:
    """Get all relevant attributes of an object.

    This function provides a unified way to access object attributes,
    handling different types of objects appropriately.

    Args:
        obj: Object to get attributes from

    Returns:
        Iterable of (name, value) pairs
    """
    # For dataclasses, use field information
    if is_dataclass(obj):
        return ((f.name, getattr(obj, f.name)) for f in fields(obj))

    # For objects with __slots__, use slot information
    elif hasattr(obj, '__slots__'):
        return (
            (attr, getattr(obj, attr))
            for attr in obj.__slots__
            if hasattr(obj, attr)
        )

    # For regular objects, use __dict__
    elif hasattr(obj, '__dict__'):
        return obj.__dict__.items()

    # For other objects, use dir() to find attributes
    else:
        return (
            (attr, getattr(obj, attr))
            for attr in dir(obj)
            if not attr.startswith('__')
        )