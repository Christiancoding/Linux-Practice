#!/usr/bin/env python3
"""
Setup configuration for Linux+ Practice Environment Manager (LPEM)
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="lpem",
    version="1.0.0",
    description="Linux+ Practice Environment Manager - VM and Challenge Management Tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/lpem",
    
    # Package discovery
    packages=find_packages(),
    
    # Include non-Python files
    include_package_data=True,
    package_data={
        'lpem': [
            'challenges/*.yaml',
            'cli_sandbox/*',
            'templates/*.html',
            'static/css/*.css',
            'static/js/*.js',
            'data/*.json'
        ],
    },
    
    # Dependencies
    install_requires=requirements,
    
    # Extra dependencies for different features
    extras_require={
        'web': ['flask>=2.0.0', 'jinja2>=3.0.0'],
        'dev': ['pytest>=6.0', 'black', 'flake8', 'mypy'],
    },
    
    # Console script entry points
    entry_points={
        'console_scripts': [
            'lpem=main:main',
        ],
    },
    
    # Python version requirement
    python_requires=">=3.8",
    
    # PyPI classifiers
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Education",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Education",
        "Topic :: System :: Systems Administration",
        "Topic :: Software Development :: Testing",
    ],
    
    # Keywords for discovery
    keywords="linux, certification, practice, vm, libvirt, education",
    
    # License
    license="MIT",
)