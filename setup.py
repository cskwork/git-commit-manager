from setuptools import setup, find_packages

setup(
    name="git-commit-manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "watchdog>=3.0.0",
        "gitpython>=3.1.40",
        "click>=8.1.7",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "rich>=13.7.0",
        "ollama>=0.1.7",
        "google-generativeai>=0.3.2",
    ],
    entry_points={
        "console_scripts": [
            "gcm=git_commit_manager.cli:main",
        ],
    },
    python_requires=">=3.8",
) 