"""
Setup configuration for StockBot CLI.
Allows installation as a command-line tool.
"""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip()
        for line in requirements_file.read_text().splitlines()
        if line.strip() and not line.startswith('#')
    ]

setup(
    name="stockbot",
    version="0.1.0",
    description="AI-powered stock options analysis bot",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="StockBot",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "stockbot=src.cli.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
