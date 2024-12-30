"""Configuration file for pytest.

This file ensures proper path handling for imports in tests, allowing
tests to import from examples and other project directories without
requiring package installation or path manipulation in test files.
"""

import os
import sys
import pytest

# Add project root to Python path
pytest_plugins = []
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))