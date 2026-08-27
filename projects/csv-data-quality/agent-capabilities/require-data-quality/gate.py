#!/usr/bin/env python3
"""Open Agents before-finish hook that reruns the CSV quality checker."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path.cwd()
    checker = root / ".agents" / "tools" / "csv-quality-check" / "server.py"
    if not checker.is_file():
        print("Data-quality gate could not find .agents/tools/csv-quality-check/server.py. Reinstall or re-extract the pack before finishing.", file=sys.stderr)
        return 2
    completed = subprocess.run(
        [sys.executable, str(checker), "check", "--policy", ".tuff-example/data-quality-policy.json", "--output", ".tuff-reports/data-quality.json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return 0
    detail = completed.stdout.strip() or completed.stderr.strip() or f"checker exited {completed.returncode}"
    print("Data-quality gate failed. Read .tuff-reports/data-quality.json, repair the governed CSV without weakening the policy, rerun csv_quality_check, and then finish again.\n" + detail[-4000:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
