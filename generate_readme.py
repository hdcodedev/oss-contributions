"""
Legacy entry point.

The implementation now lives in the ``src`` package
(config, github, model, render, cli). Running
``python generate_readme.py`` still triggers the generator via ``cli.main``.
"""

import sys

from src.cli import main

if __name__ == "__main__":
    # Propagate the exit code so CI fails loudly instead of committing stale data.
    sys.exit(main())
