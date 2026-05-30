"""PyInstaller entry point for Server Studio.

A plain script (not a package module) so PyInstaller has a concrete file to analyze.
It defers to the real UI entrypoint.
"""
import sys

from server_studio.ui.main import main

if __name__ == "__main__":
    sys.exit(main())
