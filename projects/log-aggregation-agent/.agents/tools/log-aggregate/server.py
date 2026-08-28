#!/usr/bin/env python3
"""Tuff-packaged entrypoint for the deterministic log aggregation MCP tool."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from log_aggregation.cli import main  # noqa: E402
from log_aggregation.server import main as serve  # noqa: E402


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(main())
    raise SystemExit(serve())
