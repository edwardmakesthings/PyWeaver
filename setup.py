"""Setup configuration for project tools.

Allow installation of project tools in development mode.

Path: setup.py
"""

from setuptools import setup, find_packages

setup(
    name="project-tools",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pytest>=7.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
        ]
    }
)
