"""Setup configuration for pyweaver.

Allows installation of pyweaver package in development mode.

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
    description="Python tools for structure generation, init files, and file combining",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Edward Jaworenko",
    author_email="edward@jaworenko.design",
    url="https://github.com/edwardmakesthings/pyweaver",
    packages=find_packages(exclude=['tests*', 'docs*', 'examples*']),
    python_requires=">=3.7",
    install_requires=[
        "pytest>=7.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=2.0.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "flake8>=4.0.0",
        ]
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)