from __future__ import annotations

import argparse
import base64
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table


ROOT = Path(__file__).resolve().parents[1]
console = Console()
DELAY = float(os.environ.get("DEMO_STEP_DELAY", "1"))
TUFF = os.environ.get("TUFF_COMMAND", "tuff")


def ask(title: str, command: str, yes: bool) -> bool:
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]\n\n[orange1]$ {command}[/orange1]", border_style="cyan"))
    time.sleep(DELAY)
    return yes or Confirm.ask("Proceed?", default=True)


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def tuff(*args: str) -> list[str]:
    return [TUFF, *args]


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive published Tuff pack demo")
    parser.add_argument("--yes", action="store_true", help="approve every demo step")
    args = parser.parse_args()
    pack_name = os.environ.get("PACK_NAME", "log-aggregation-capabilities")
    pack_version = os.environ.get("PACK_VERSION", "1.0.0")
    image = os.environ.get("RUNTIME_IMAGE", "log-aggregation-agent-runtime:demo")
    ghcr_user = output(["gh", "api", "user", "--jq", ".login"]).lower()
    reference = os.environ.get("CAPABILITY_REF", f"ghcr.io/{ghcr_user}/{pack_name}:{pack_version}")
    pack = ROOT / "tuff-dist" / f"{pack_name}-{pack_version}.tuffpack"
    key_file = Path(os.environ.get("OPENAI_API_KEY_FILE", ""))
    docker_config = Path(tempfile.mkdtemp(prefix="log-agent-docker-"))
    try:
        console.print(Panel.fit("[bold green]Log aggregation agent — published capability demo[/bold green]", border_style="green"))
        table = Table("Stage", "Source of truth")
        table.add_row("Author", "agent-capabilities/")
        table.add_row("Pack", reference)
        table.add_row("Runtime", "clean container → pull → verify → add pack → Python agent")
        console.print(table)

        if not ask("1. Discover capability sources", "find agent-capabilities -name tuff.toml", args.yes):
            return 0
        run(["find", "agent-capabilities", "-name", "tuff.toml", "-print"])

        if not ask("2. Install capabilities into the local Tuff project", f"{TUFF} add ... -a open-agents", args.yes):
            return 0
        for path in ["log-workbench", "log-aggregate", "require-log-summary", "log-aggregation-review"]:
            run(tuff("add", "--agent", "open-agents", f"agent-capabilities/{path}"))

        if not ask("3. List and validate installed capabilities", f"{TUFF} list && {TUFF} check", args.yes):
            return 0
        run(tuff("list"))
        run(tuff("check"))

        if pack.exists():
            pack.unlink()
        if not ask("4. Build, verify, and inspect the Tuff pack", f"{TUFF} pack build --name {pack_name} --version {pack_version}", args.yes):
            return 0
        run(tuff("pack", "build", "--name", pack_name, "--version", pack_version))
        run(tuff("pack", "verify", str(pack)))
        run(tuff("pack", "inspect", str(pack)))

        token = output(["gh", "auth", "token"])
        auth = base64.b64encode(f"{ghcr_user}:{token}".encode()).decode()
        (docker_config / "config.json").write_text(f'{{"auths":{{"ghcr.io":{{"auth":"{auth}"}}}}}}\n', encoding="utf-8")
        os.chmod(docker_config / "config.json", 0o600)
        publish_env = {**os.environ, "DOCKER_CONFIG": str(docker_config)}
        if not ask("5. Publish the Tuff pack to GitHub Container Registry", f"{TUFF} pack push {pack} {reference}", args.yes):
            return 0
        run(tuff("pack", "push", str(pack), reference), publish_env)

        if not ask("6. Build the clean runtime image", f"docker build -f Dockerfile.agent-runtime -t {image} .", args.yes):
            return 0
        run(["docker", "build", "-f", "Dockerfile.agent-runtime", "-t", image, "."])
        run(["docker", "image", "ls", image])

        if not key_file.is_file():
            raise SystemExit("OPENAI_API_KEY_FILE must point to an existing key file")
        if not ask("7. Start clean container, pull/install the pack, and run the agent", f"docker run ... {image}", args.yes):
            return 0
        container_command = ["docker", "run", "--rm", "-i", "-e", f"CAPABILITY_REF={reference}", "-e", "DOCKER_CONFIG=/root/.docker"]
        if args.yes or os.environ.get("DEMO_AUTO_APPROVE") == "1":
            container_command.extend(["-e", "DEMO_AUTO_APPROVE=1"])
        container_command.extend(["-v", f"{docker_config}:/root/.docker:ro", "-v", f"{key_file}:/run/secrets/openai_api_key:ro", "-v", f"{ROOT / 'reports'}:/workspace/reports", image])
        # Keep the host Docker CLI environment intact so it uses the user's
        # active Docker Desktop context. The temporary config is mounted into
        # the container separately for its Tuff registry pull.
        run(container_command)
        console.print(Panel.fit("[bold green]Demo complete: the agent consumed the published Tuff pack.[/bold green]", border_style="green"))
        return 0
    finally:
        shutil.rmtree(docker_config, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
