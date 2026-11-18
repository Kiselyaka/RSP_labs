"""Run service and HTTP unit tests without PostgreSQL or an HTTP server."""
import cmd
import sys
from pathlib import Path

import pytest


if __name__ == "__main__":
    if not hasattr(cmd, "Cmd"):
        raise SystemExit("Use python -P tests/run_unit.py")
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    raise SystemExit(pytest.main([
        "-v", "-p", "no:cacheprovider", str(root / "tests/test_services.py"),
        str(root / "tests/test_http.py"),
    ]))
