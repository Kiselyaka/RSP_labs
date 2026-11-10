"""Run pytest with Python's standard cmd module available to pdb."""

import cmd
import sys
from pathlib import Path

import pytest


if __name__ == "__main__":
    if not hasattr(cmd, "Cmd"):
        raise SystemExit("Run this script with python -P.")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    raise SystemExit(pytest.main(["-p", "no:cacheprovider", "-q", str(root / "tests")]))
