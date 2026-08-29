from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm


ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd())).resolve()
PACK_PATH = Path("/tmp/log-aggregation-capabilities.tuffpack")
console = Console()


def tuff(*args: str) -> None:
    command = ["tuff", *args]
    print(f"\033[38;5;202m$ {' '.join(command)}\033[0m", flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def ask(step: int, title: str, command: str) -> bool:
    console.print(f"\n[bold cyan]▶ {title}[/bold cyan]\n[orange1]  $ {command}[/orange1]")
    if os.environ.get("DEMO_AUTO_APPROVE") == "1":
        console.print("  [dim](auto-approved)[/dim]")
        return True
    # Numbered like the host prompts so a recording can gate on each one.
    return Confirm.ask(f"  Proceed with runtime step {step}?", default=True)


def main() -> int:
    reference = os.environ.get("CAPABILITY_REF")
    if not reference:
        raise RuntimeError("CAPABILITY_REF must point to the published GHCR Tuff pack")
    if not ask(1, "Initialize a clean runtime project", "tuff init"):
        return 0
    tuff("init")
    if not ask(2, "Pull and verify the published pack", f"tuff pack pull {reference} --output {PACK_PATH} && tuff pack verify {PACK_PATH}"):
        return 0
    tuff("pack", "pull", reference, "--output", str(PACK_PATH))
    tuff("pack", "verify", str(PACK_PATH))
    if not ask(3, "Install the pulled pack into the runtime", f"tuff add pack {PACK_PATH} -a open-agents"):
        return 0
    tuff("add", "pack", str(PACK_PATH), "-a", "open-agents")
    if not ask(4, "List and check the installed runtime capabilities", "tuff list && tuff check"):
        return 0
    tuff("list")
    tuff("check")
    if not ask(5, "Run the Python agent using the installed capability", "python -m runtime.agent"):
        return 0
    print("\033[32m✓ Published capabilities installed; starting Python agent\033[0m", flush=True)
    from .agent import main as run_agent
    return run_agent()


if __name__ == "__main__":
    raise SystemExit(main())
