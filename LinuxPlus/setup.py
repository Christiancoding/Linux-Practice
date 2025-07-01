#!/usr/bin/env python3

from setuptools import setup, find_packages

setup(
    name="lpem",
    version="0.1.0",
    description="Linux+ Practice Environment Manager for CompTIA Linux+ exam (XK0-005)",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "libvirt-python",
        "paramiko",
        "pyyaml",
        "typer[all]",
        "rich",
        "typing-extensions",
    ],
    entry_points={
        "console_scripts": [
            "lpem=lpem.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Education",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.6",
)
