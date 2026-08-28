from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DELAY = float(os.environ.get("DEMO_STEP_DELAY", "1"))


def run(label: str, command: list[str], env: dict[str, str] | None = None) -> None:
    print(f"\033[36m▶ {label}\033[0m", flush=True)
    print(f"  \033[31m$ {' '.join(command)}\033[0m", flush=True)
    time.sleep(DELAY)
    completed = subprocess.run(command, cwd=ROOT, env=env, text=True)
    if completed.returncode:
        raise SystemExit(completed.returncode)


def main() -> int:
    run("Run deterministic aggregation", [sys.executable, "-m", "log_aggregation.cli", "aggregate", "--input", "data/api.log", "--json-output", "reports/aggregation.json", "--markdown-output", "reports/aggregation.md"])
    if os.environ.get("SKIP_AGENT") == "1":
        print("\033[33m✓ deterministic stage complete (SKIP_AGENT=1)\033[0m")
        return 0
    run("Run the real OpenAI Agents SDK agent in the container", ["docker", "compose", "run", "--rm", "agent"])
    print("\033[32m✓ log aggregation agent demo complete\033[0m")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
