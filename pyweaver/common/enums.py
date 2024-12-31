"""This package exists primarily to avoid circular imports."""

from enum import Enum

class ListingStyle(Enum):
    """Output style for structure listings.

    This enum defines different ways to format the directory structure,
    allowing for various visualization needs.
    """
    TREE = "tree"          # Traditional tree with branches
    FLAT = "flat"          # Flat list of paths
    INDENTED = "indented"  # Indented list without branches
    MARKDOWN = "markdown"  # Markdown-compatible list