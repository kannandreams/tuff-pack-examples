#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path.cwd().resolve()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from log_aggregation.engine import aggregate_log, write_reports  # noqa: E402


def main() -> int:
    input_path = ROOT / "data" / "api.log"
    json_path = ROOT / "reports" / "aggregation.json"
    markdown_path = ROOT / "reports" / "aggregation.md"
    if not input_path.is_file():
        print("log summary gate could not find data/api.log", file=sys.stderr)
        return 2
    manifest = aggregate_log(input_path)
    write_reports(manifest, json_path, markdown_path)
    if manifest["uncovered_line_count"] != 0:
        print("log summary gate failed: source lines are not fully covered", file=sys.stderr)
        return 2
    try:
        stored = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"log summary gate failed: cannot read {json_path}: {exc}", file=sys.stderr)
        return 2
    if stored != manifest:
        print("log summary gate failed: report does not match deterministic aggregation", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
