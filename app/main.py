#!/usr/bin/env python3
"""Shortify entry point."""

from pathlib import Path
import sys

# Ensure package imports work both in development and in PyInstaller builds.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ui.shell import ShortifyApp


if __name__ == "__main__":
    app = ShortifyApp()
    app.mainloop()
