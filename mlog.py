"""Official Python DSL module for Mindustry Logic (mlog-py).

Exports all compiler intrinsics, enums, builtins, compiler and decompiler entry points.
"""

import sys
from src.mlog import *
from src.mlog import __all__, main

if __name__ == "__main__":
    sys.exit(main())
