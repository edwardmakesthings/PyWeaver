"""Setup configuration for PyWeaver package.

This module contains package configuration for installation via pip. It defines
metadata about the package, its dependencies, and installation requirements.

Path: setup.py
"""

from setuptools import setup, find_packages
import os

# Read version from package __init__.py
version = None
init_path = os.path.join('pyweaver', '__init__.py')
with open(init_path, 'r', encoding="utf-8") as f:
    for line in f:
        if line.startswith('__version__'):
            version = line.split('=')[1].strip().strip('"').strip("'")
            break

if version is None:
    raise RuntimeError('Version information not found')

# Read README for long description
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="pyweaver",
    version=version,
    author="Edward Jaworenko",
    author_email="edward@jaworenko.design",
    description="A toolkit for weaving together well-structured Python projects",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/edwardmakesthings/pyweaver",

    # Package configuration
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    include_package_data=True,

    # Package dependencies
    install_requires=[
        "pydantic>=2.0.0"
    ],

    # Development dependencies
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=2.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "flake8>=4.0.0",
        ]
    },

    # Package classifiers
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Build Tools",
    ],

    # Package requirements
    python_requires=">=3.7",
)