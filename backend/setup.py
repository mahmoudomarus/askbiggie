#!/usr/bin/env python3
"""
Minimal setup.py for Ask Biggie backend package.
This works in conjunction with pyproject.toml for package installation.
"""

from setuptools import setup, find_packages

if __name__ == "__main__":
    setup(
        name="biggie",
        packages=find_packages(),
        include_package_data=True,
        python_requires=">=3.11",
    ) 