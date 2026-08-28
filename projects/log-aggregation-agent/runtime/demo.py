from __future__ import annotations

import os
import subprocess
import sys
import time
import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELAY = float(os.environ.get("DEMO_STEP_DELAY", "1"))
AUTO_APPROVE = os.environ.get("DEMO_AUTO_APPROVE") == "1"


def should_proceed(label: str, auto_approve: bool) -> bool:
    if auto_approve or not sys.stdin.isatty():
        print("  \033[2m(auto-approved)\033[0m", flush=True)
        return True
    answer = input(f"  Proceed with {label}? [Y/n] ").strip().lower()
    return answer in {"", "y", "yes"}


def run(label: str, command: list[str], auto_approve: bool, env: dict[str, str] | None = None) -> bool:
    print(f"\033[36m▶ {label}\033[0m", flush=True)
    print(f"  \033[31m$ {' '.join(command)}\033[0m", flush=True)
    if not should_proceed(label, auto_approve):
        print(f"\033[33m■ stopped before: {label}\033[0m", flush=True)
        return False
    time.sleep(DELAY)
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True)
    if completed.returncode:
        raise SystemExit(completed.returncode)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive log aggregation agent demo")
    parser.add_argument("--yes", action="store_true", help="approve every demo step")
    args = parser.parse_args()
    auto_approve = AUTO_APPROVE or args.yes

    ran_preview = run("Preview deterministic aggregation (optional)", [sys.executable, "-m", "log_aggregation.cli", "aggregate", "--input", "data/api.log", "--json-output", "reports/aggregation.json", "--markdown-output", "reports/aggregation.md"], auto_approve)
    if not ran_preview:
        print("  Continuing to the agent; it will invoke the same capability through MCP.", flush=True)
    if os.environ.get("SKIP_AGENT") == "1":
        print("\033[33m✓ deterministic stage complete (SKIP_AGENT=1)\033[0m")
        return 0
    if not run("Build and run the real OpenAI Agents SDK agent in the container", ["docker", "compose", "run", "--build", "--rm", "agent"], auto_approve):
        return 0
    print("\033[32m✓ log aggregation agent demo complete\033[0m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
