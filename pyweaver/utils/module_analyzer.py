"""Python module analysis utilities.

This module provides sophisticated tools for analyzing Python source files to extract
detailed information about their structure, contents, and relationships. It uses
Python's ast module to perform static analysis, gathering information about classes,
functions, imports, and exports while maintaining proper context and scope.

The analyzer is designed to handle complex Python constructs including:
- Nested class and function definitions
- Import variations (import, from import, import as)
- Export declarations (__all__ assignments)
- Docstring extraction and analysis
- Type annotations and hints
- Module-level variables and constants

The implementation prioritizes accuracy and completeness while maintaining
performance through careful caching and incremental analysis.

Path: pyweaver/utils/module_analyzer.py
"""
import ast
import logging
from pathlib import Path
from typing import Dict, Set, Optional, List, Any, NamedTuple
from dataclasses import dataclass, field

from .repr import comprehensive_repr
from ..common.errors import (
    ProcessingError, ErrorContext, ErrorCode, FileError
)

logger = logging.getLogger(__name__)

class ImportInfo(NamedTuple):
    """Information about a module import.

    Tracks details about how a module is imported and what names are imported
    from it.

    Attributes:
        module_path: Full path of the imported module
        names: Set of imported names
        is_relative: Whether it's a relative import
        level: Number of dots in relative import
        alias: Optional alias for the import
    """
    module_path: str
    names: Set[str]
    is_relative: bool
    level: int = 0
    alias: Optional[str] = None

@dataclass
class FunctionInfo:
    """Information about a function definition.

    Tracks details about a function including its signature, docstring,
    and decorators.

    Attributes:
        name: Function name
        docstring: Function's docstring
        is_async: Whether it's an async function
        decorators: List of decorator names
        return_annotation: Optional return type annotation
        parameters: Dictionary of parameter information
        is_property: Whether function is a property
        is_classmethod: Whether function is a classmethod
        is_staticmethod: Whether function is a staticmethod
    """
    name: str
    docstring: str = ""
    is_async: bool = False
    decorators: List[str] = field(default_factory=list)
    return_annotation: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_property: bool = False
    is_classmethod: bool = False
    is_staticmethod: bool = False

@dataclass
class ClassInfo:
    """Information about a class definition.

    Tracks comprehensive information about a class including its methods,
    attributes, and relationships.

    Attributes:
        name: Class name
        docstring: Class's docstring
        bases: List of base class names
        decorators: List of decorator names
        methods: Dictionary of method information
        class_variables: Dictionary of class variables
        instance_variables: Dictionary of instance variables
        is_dataclass: Whether class is a dataclass
        nested_classes: Dictionary of nested class information
    """
    name: str
    docstring: str = ""
    bases: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    methods: Dict[str, FunctionInfo] = field(default_factory=dict)
    class_variables: Dict[str, Any] = field(default_factory=dict)
    instance_variables: Dict[str, Any] = field(default_factory=dict)
    is_dataclass: bool = False
    nested_classes: Dict[str, 'ClassInfo'] = field(default_factory=dict)

@dataclass
class ModuleInfo:
    """Information extracted from a Python module.

    Provides a comprehensive view of a module's contents including all
    declarations, imports, and exports.

    Attributes:
        path: Path to the module file
        docstring: Module's docstring
        classes: Dictionary of class information
        functions: Dictionary of function information
        imports: Set of import statements
        exports: Set of explicitly exported names
        dependencies: Set of module dependencies
        variables: Dictionary of module-level variables
        all_declarations: Set of all declared names
        errors: List of any errors encountered
    """
    path: Path
    docstring: str = ""
    classes: Dict[str, ClassInfo] = field(default_factory=dict)
    functions: Dict[str, FunctionInfo] = field(default_factory=dict)
    imports: Set[ImportInfo] = field(default_factory=set)
    exports: Set[str] = field(default_factory=set)
    dependencies: Set[str] = field(default_factory=set)
    variables: Dict[str, Any] = field(default_factory=dict)
    all_declarations: Set[str] = field(default_factory=set)
    errors: List[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message to the module's error list."""
        self.errors.append(error)
        logger.error("Module %s: %s", self.path, error)

class ModuleAnalyzer:
    """Analyzes Python modules to extract structural information.

    This class provides comprehensive analysis of Python source files,
    extracting detailed information about their contents and structure.
    It maintains an efficient caching system to improve performance for
    frequently analyzed modules.

    The analyzer handles:
    - Class and function definitions
    - Import statements and module relationships
    - Export declarations
    - Variable assignments
    - Type annotations
    - Documentation strings

    Example:
        ```python
        analyzer = ModuleAnalyzer()

        # Analyze a module
        info = analyzer.analyze_file(path)
        if info:
            # Access extracted information
            print(f"Module docstring: {info.docstring}")
            print(f"Found {len(info.classes)} classes:")
            for name, cls in info.classes.items():
                print(f"  {name}: {cls.docstring}")

            print(f"Exports: {info.exports}")

        # Cache management
        analyzer.clear_cache()  # Clear cached results
        ```
    """

    def __init__(self, cache_size: int = 100):
        """Initialize analyzer with optional cache size.

        Args:
            cache_size: Maximum number of modules to cache
        """
        self._file_cache: Dict[Path, ModuleInfo] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

        logger.debug(
            "Initialized ModuleAnalyzer (cache_size=%d)",
            cache_size
        )

    def analyze_file(
        self,
        file_path: Path,
        package_name: Optional[str] = None
    ) -> Optional[ModuleInfo]:
        """Analyze a Python file to extract information.

        This method performs a comprehensive analysis of a Python source
        file, extracting information about its contents and structure.

        Args:
            file_path: Path to Python file
            package_name: Optional package name for dependency tracking

        Returns:
            ModuleInfo if successful, None on error

        Raises:
            ProcessingError: If file analysis fails
            FileError: If file cannot be read
        """
        try:
            # Check cache first
            if info := self._check_cache(file_path):
                return info

            # Read and parse file
            content = self._read_file(file_path)
            tree = self._parse_content(content, file_path)

            # Create module info
            info = ModuleInfo(path=file_path)

            # Extract docstring
            info.docstring = ast.get_docstring(tree) or ""

            # Analyze module contents
            self._analyze_node(tree, info, package_name)

            # Update cache
            self._update_cache(file_path, info)

            return info

        except Exception as e:
            context = ErrorContext(
                operation="analyze_file",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=file_path,
                details={"package_name": package_name}
            )
            raise ProcessingError(
                f"Failed to analyze {file_path}",
                context=context,
                original_error=e
            ) from e

    def _check_cache(self, file_path: Path) -> Optional[ModuleInfo]:
        """Check if a module's analysis is cached.

        Args:
            file_path: Path to check

        Returns:
            Cached ModuleInfo or None if not cached
        """
        if file_path in self._file_cache:
            self._cache_hits += 1
            logger.debug("Cache hit for %s", file_path)
            return self._file_cache[file_path]

        self._cache_misses += 1
        logger.debug("Cache miss for %s", file_path)
        return None

    def _update_cache(self, file_path: Path, info: ModuleInfo) -> None:
        """Update the analysis cache with new information.

        Args:
            file_path: Path being cached
            info: Analysis results to cache
        """
        # Implement simple LRU by removing oldest if at capacity
        if len(self._file_cache) >= self._cache_size:
            oldest = next(iter(self._file_cache))
            del self._file_cache[oldest]

        self._file_cache[file_path] = info
        logger.debug("Cached analysis for %s", file_path)

    def _read_file(self, path: Path) -> str:
        """Read a Python source file.

        Args:
            path: Path to file

        Returns:
            File contents

        Raises:
            FileError: If file cannot be read
        """
        try:
            return path.read_text(encoding='utf-8')

        except Exception as e:
            context = ErrorContext(
                operation="read_file",
                error_code=ErrorCode.FILE_READ,
                path=path
            )
            raise FileError(
                f"Failed to read Python file: {e}",
                path=path,
                context=context,
                original_error=e
            ) from e

    def _parse_content(self, content: str, path: Path) -> ast.AST:
        """Parse Python source code into an AST.

        Args:
            content: Source code to parse
            path: Source file path (for error reporting)

        Returns:
            Parsed AST

        Raises:
            ProcessingError: If parsing fails
        """
        try:
            return ast.parse(content)

        except SyntaxError as e:
            context = ErrorContext(
                operation="parse_content",
                error_code=ErrorCode.VALIDATION_FORMAT,
                path=path,
                details={
                    "line": e.lineno,
                    "offset": e.offset,
                    "text": e.text
                }
            )
            raise ProcessingError(
                f"Syntax error in Python file: {e}",
                context=context,
                original_error=e
            ) from e
        except Exception as e:
            context = ErrorContext(
                operation="parse_content",
                error_code=ErrorCode.PROCESS_EXECUTION,
                path=path
            )
            raise ProcessingError(
                f"Failed to parse Python file: {e}",
                context=context,
                original_error=e
            ) from e

    def _analyze_node(
        self,
        node: ast.AST,
        info: ModuleInfo,
        package_name: Optional[str] = None
    ) -> None:
        """Analyze an AST node and update module information.

        This method recursively analyzes AST nodes, extracting relevant
        information and updating the ModuleInfo object.

        Args:
            node: AST node to analyze
            info: ModuleInfo to update
            package_name: Optional package name for dependency tracking
        """
        for child in ast.walk(node):
            # Handle classes
            if isinstance(child, ast.ClassDef):
                class_info = self._analyze_class(child)
                if not child.name.startswith('_'):
                    info.classes[child.name] = class_info
                    info.exports.add(child.name)
                info.all_declarations.add(child.name)

            # Handle functions
            elif isinstance(child, ast.FunctionDef):
                if not hasattr(child, '_processed'):
                    func_info = self._analyze_function(child)
                    if not child.name.startswith('_'):
                        info.functions[child.name] = func_info
                        info.exports.add(child.name)
                    info.all_declarations.add(child.name)
                    child._processed = True

            # Handle imports
            elif isinstance(child, ast.Import):
                for name in child.names:
                    import_info = ImportInfo(
                        module_path=name.name,
                        names={name.asname or name.name},
                        is_relative=False,
                        alias=name.asname
                    )
                    info.imports.add(import_info)
                    if package_name and name.name.startswith(package_name):
                        info.dependencies.add(name.name)

            # Handle from imports
            elif isinstance(child, ast.ImportFrom):
                if child.module:
                    names = {n.name for n in child.names}
                    import_info = ImportInfo(
                        module_path=child.module,
                        names=names,
                        is_relative=child.level > 0,
                        level=child.level
                    )
                    info.imports.add(import_info)
                    if package_name and child.module.startswith(package_name):
                        info.dependencies.add(child.module)

            # Handle __all__ assignments
            elif (isinstance(child, ast.Assign) and
                  isinstance(child.targets[0], ast.Name) and
                  child.targets[0].id == '__all__'):
                if isinstance(child.value, ast.List):
                    for elt in child.value.elts:
                        if isinstance(elt, ast.Constant):
                            info.exports.add(elt.s)

            # Handle variable assignments
            elif isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        if not target.id.startswith('_'):
                            info.variables[target.id] = self._get_value(child.value)
                        info.all_declarations.add(target.id)

    def _analyze_class(self, node: ast.ClassDef) -> ClassInfo:
        """Analyze a class definition node.

        This method extracts comprehensive information about a class
        definition including its methods, attributes, and relationships.

        Args:
            node: ClassDef node to analyze

        Returns:
            Extracted class information
        """
        class_info = ClassInfo(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            bases=[self._get_name(base) for base in node.bases],
            decorators=[self._get_name(d) for d in node.decorator_list]
        )

        # Check for dataclass
        class_info.is_dataclass = any(
            d.id == 'dataclass' for d in node.decorator_list
        )

        # Analyze class body
        for item in node.body:
            # Handle methods
            if isinstance(item, ast.FunctionDef):
                method_info = self._analyze_function(item)
                class_info.methods[item.name] = method_info

                # Check for special method types
                if any(d.id == 'property' for d in item.decorator_list):
                    method_info.is_property = True
                elif any(d.id == 'classmethod' for d in item.decorator_list):
                    method_info.is_classmethod = True
                elif any(d.id == 'staticmethod' for d in item.decorator_list):
                    method_info.is_staticmethod = True

            # Handle nested classes
            elif isinstance(item, ast.ClassDef):
                nested_info = self._analyze_class(item)
                class_info.nested_classes[item.name] = nested_info

            # Handle class variables
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info.class_variables[target.id] = self._get_value(item.value)

            # Handle instance variables (in __init__)
            elif isinstance(item, ast.FunctionDef) and item.name == '__init__':
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Attribute) and \
                               isinstance(target.value, ast.Name) and \
                               target.value.id == 'self':
                                class_info.instance_variables[target.attr] = \
                                    self._get_value(stmt.value)

        return class_info

    def _analyze_function(self, node: ast.FunctionDef) -> FunctionInfo:
        """Analyze a function definition node.

        This method extracts detailed information about a function definition
        including its signature, decorators, and documentation.

        Args:
            node: FunctionDef node to analyze

        Returns:
            Extracted function information
        """
        function_info = FunctionInfo(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            is_async=isinstance(node, ast.AsyncFunctionDef),
            decorators=[self._get_name(d) for d in node.decorator_list]
        )

        # Analyze return annotation
        if node.returns:
            function_info.return_annotation = self._get_annotation(node.returns)

        # Analyze parameters
        for arg in node.args.args:
            param_info = {
                'name': arg.arg,
                'annotation': self._get_annotation(arg.annotation) if arg.annotation else None,
                'has_default': False,
                'default_value': None
            }
            function_info.parameters[arg.arg] = param_info

        # Handle default values
        defaults = node.args.defaults
        if defaults:
            for arg, default in zip(reversed(node.args.args), reversed(defaults)):
                param_info = function_info.parameters[arg.arg]
                param_info['has_default'] = True
                param_info['default_value'] = self._get_value(default)

        return function_info

    def _get_annotation(self, node: Optional[ast.AST]) -> Optional[str]:
        """Extract type annotation from an AST node.

        This method converts AST type annotation nodes into their string
        representation, handling various forms of type hints.

        Args:
            node: AST node containing type annotation

        Returns:
            String representation of type annotation or None
        """
        if node is None:
            return None

        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Attribute):
            return f"{self._get_annotation(node.value)}.{node.attr}"
        elif isinstance(node, ast.Subscript):
            value = self._get_annotation(node.value)
            slice_value = self._get_annotation(node.slice)
            return f"{value}[{slice_value}]"
        elif isinstance(node, ast.Tuple):
            elements = [self._get_annotation(elt) for elt in node.elts]
            return f"Tuple[{', '.join(elements)}]"
        elif isinstance(node, ast.List):
            elements = [self._get_annotation(elt) for elt in node.elts]
            return f"List[{', '.join(elements)}]"
        elif isinstance(node, ast.Dict):
            keys = [self._get_annotation(k) for k in node.keys]
            values = [self._get_annotation(v) for v in node.values]
            return f"Dict[{', '.join(keys)}, {', '.join(values)}]"
        else:
            return ast.unparse(node)

    def _get_value(self, node: ast.AST) -> Any:
        """Extract value from an AST node.

        This method attempts to convert AST value nodes into their Python
        equivalents for easier analysis and representation.

        Args:
            node: AST node containing a value

        Returns:
            Python value or AST node if conversion not possible
        """
        try:
            if isinstance(node, ast.Constant):
                return node.value
            elif isinstance(node, ast.Name):
                return node.id
            elif isinstance(node, ast.List):
                return [self._get_value(elt) for elt in node.elts]
            elif isinstance(node, ast.Tuple):
                return tuple(self._get_value(elt) for elt in node.elts)
            elif isinstance(node, ast.Dict):
                return {
                    self._get_value(k): self._get_value(v)
                    for k, v in zip(node.keys, node.values)
                }
            elif isinstance(node, ast.Set):
                return {self._get_value(elt) for elt in node.elts}
            elif isinstance(node, (ast.Call, ast.BinOp, ast.UnaryOp)):
                # For complex expressions, return the AST node
                return node
            else:
                return ast.unparse(node)
        except Exception:
            # Fall back to unparsing for any errors
            return ast.unparse(node)

    def _get_name(self, node: ast.AST) -> str:
        """Extract a name from an AST node.

        This method handles various forms of name references in the AST,
        including attributes and complex expressions.

        Args:
            node: AST node containing a name

        Returns:
            Extracted name as string
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            base = self._get_name(node.value)
            return f"{base}.{node.attr}"
        else:
            return ast.unparse(node)

    def get_cache_stats(self) -> Dict[str, int]:
        """Get statistics about the analyzer's cache usage.

        Returns:
            Dictionary containing cache statistics
        """
        return {
            'size': len(self._file_cache),
            'capacity': self._cache_size,
            'hits': self._cache_hits,
            'misses': self._cache_misses
        }

    def clear_cache(self) -> None:
        """Clear the file analysis cache and reset statistics."""
        self._file_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        logger.debug("Cleared module analyzer cache")

    def __repr__(self) -> str:
        """Get string representation of analyzer state."""
        return comprehensive_repr(
            self,
            exclude=['_file_cache'],
            prioritize=['_cache_size', '_cache_hits', '_cache_misses'],
            one_per_line=True
        )