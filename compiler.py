#!/data/data/com.termux/files/usr/bin/env python3
"""CLI entry point for the Python-to-mlog compiler."""

import sys
from src.mlog import main

if __name__ == "__main__":
    sys.exit(main())
