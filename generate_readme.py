"""
Legacy entry point.

The implementation now lives in the ``src`` package
(config, github, sheet, model, render, cli). Running
``python generate_readme.py`` still triggers the generator via ``cli.main``.
"""

from src.cli import main

if __name__ == "__main__":
    main()
