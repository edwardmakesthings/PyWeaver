"""Type definitions for structure generation.

Contains data classes and type definitions used across the structure
generator implementation.

Path: pyweaver/structure_generator/_impl/_types.py
"""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

@dataclass
class DirectoryNode:
    """Node in directory structure."""
    path: Path
    rel_path: Path
    is_dir: bool
    size: Optional[int] = None
    children: Optional[List['DirectoryNode']] = None
