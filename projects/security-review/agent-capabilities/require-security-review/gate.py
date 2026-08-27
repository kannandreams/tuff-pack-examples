#!/usr/bin/env python3
"""Claude Stop hook that reruns the installed security baseline scanner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def hook_input() -> dict[str, object]:
    try:
        value = json.load(sys.stdin)
    except (json.JSONDecodeError, OSError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    if hook_input().get("stop_hook_active") is True:
        return 0
    root = Path.cwd()
    scanner = root / ".claude" / "tools" / "security-baseline-scan" / "server.py"
    if not scanner.is_file():
        print("Security gate could not find .claude/tools/security-baseline-scan/server.py. Reinstall or re-extract the pack before finishing.", file=sys.stderr)
        return 2
    completed = subprocess.run(
        [sys.executable, str(scanner), "check", "--policy", ".tuff-example/security-policy.json", "--output", ".tuff-reports/security-review.json"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return 0
    detail = completed.stdout.strip() or completed.stderr.strip() or f"scanner exited {completed.returncode}"
    print("Security baseline gate failed. Read .tuff-reports/security-review.json, validate each signal with the security-review skill, fix the unsafe example without weakening the policy, rerun security_baseline_scan, and then finish again.\n" + detail[-4000:], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
