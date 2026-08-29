from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import webbrowser
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table


ROOT = Path(__file__).resolve().parents[1]
console = Console()
DELAY = float(os.environ.get("DEMO_STEP_DELAY", "1"))
TUFF = os.environ.get("TUFF_COMMAND", "tuff")
VERBOSE = os.environ.get("DEMO_VERBOSE") == "1"
TOTAL_STEPS = 7


def ask(step: int, title: str, command: str, yes: bool) -> bool:
    console.print(
        Panel(
            f"[bold cyan]{title}[/bold cyan]\n\n[orange1]$ {command}[/orange1]",
            title=f"[dim]step {step}/{TOTAL_STEPS}[/dim]",
            title_align="left",
            border_style="cyan",
        )
    )
    time.sleep(DELAY)
    # The prompt carries its step number so a recording can wait for this
    # exact prompt. A generic "Proceed?" also matches the previous, already
    # answered prompt line, which makes VHS fire every gate at once.
    return yes or Confirm.ask(f"Proceed with step {step}?", default=True)


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def run_quiet(command: list[str], label: str, env: dict[str, str] | None = None, tail: int = 20) -> str:
    """Run a noisy command behind a spinner; only surface logs when it fails."""
    if VERBOSE:
        console.print(f"[dim]$ {' '.join(command)}[/dim]")
        run(command, env)
        return ""
    # A static line rather than an animated spinner: a spinner repaints ~12x a
    # second, and a terminal recorder capturing every repaint cannot keep up at
    # a large frame size, which backs up the pty and stalls the demo.
    console.print(f"[dim]⋯ {label}…[/dim]")
    started = time.perf_counter()
    proc = subprocess.run(
        command,
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    elapsed = time.perf_counter() - started
    if proc.returncode != 0:
        console.print(f"[bold red]✗ {label} failed[/bold red] [dim](exit {proc.returncode})[/dim]")
        console.print("".join(proc.stdout.splitlines(keepends=True)[-tail:]).rstrip())
        raise SystemExit(proc.returncode)
    console.print(f"[green]✓[/green] {label} [dim]({elapsed:.1f}s)[/dim]")
    return proc.stdout


def output(command: list[str]) -> str:
    return subprocess.check_output(command, cwd=ROOT, text=True).strip()


def tuff(*args: str) -> list[str]:
    return [TUFF, *args]


def image_table(image: str) -> None:
    template = "{{.Repository}}\t{{.Tag}}\t{{.ID}}\t{{.Size}}"
    rows = [line.split("\t") for line in output(["docker", "image", "ls", "--format", template, image]).splitlines() if line]
    table = Table("Repository", "Tag", "Image ID", "Size", box=None, pad_edge=False)
    for row in rows:
        table.add_row(*row)
    console.print(table)


def package_panel(pack_name: str, reference: str, open_browser: bool) -> None:
    """Render the GHCR package entry the push just created or updated."""
    try:
        package = json.loads(output(["gh", "api", f"/user/packages/container/{pack_name}"]))
        versions = json.loads(output(["gh", "api", f"/user/packages/container/{pack_name}/versions"]))
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        console.print(f"[yellow]![/yellow] published, but the GHCR package API was unavailable — see {reference}")
        return

    latest = versions[0] if versions else {}
    tags = ", ".join(latest.get("metadata", {}).get("container", {}).get("tags", [])) or "—"
    digest = latest.get("name", "—")
    url = package.get("html_url", "")
    table = Table(box=None, pad_edge=False, show_header=False)
    table.add_column(style="dim")
    table.add_column(overflow="fold")
    table.add_row("package", f"[bold]{package.get('name', pack_name)}[/bold]")
    table.add_row("visibility", package.get("visibility", "—"))
    table.add_row("versions", str(package.get("version_count", len(versions))))
    table.add_row("latest tag", tags)
    table.add_row("digest", f"{digest[:26]}…" if len(digest) > 27 else digest)
    table.add_row("published", latest.get("created_at", package.get("updated_at", "—")))
    table.add_row("pull", f"[orange1]tuff pack pull {reference}[/orange1]")
    table.add_row("url", f"[link={url}]{url}[/link]")
    console.print(Panel(table, title="[bold]GitHub Packages — ghcr.io[/bold]", border_style="green", expand=False))

    if open_browser and url:
        console.print("[dim]opening the package page in your browser…[/dim]")
        webbrowser.open(url)


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive published Tuff pack demo")
    parser.add_argument("--yes", action="store_true", help="approve every demo step")
    parser.add_argument(
        "--open-package",
        action="store_true",
        default=os.environ.get("DEMO_OPEN_PACKAGE") == "1",
        help="open the GHCR package page in a browser after publishing",
    )
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

        if not ask(1, "Discover capability sources", "find agent-capabilities -name tuff.toml", args.yes):
            return 0
        run(["find", "agent-capabilities", "-name", "tuff.toml", "-print"])

        if not ask(2, "Install capabilities into the local Tuff project", f"{TUFF} add ... -a open-agents", args.yes):
            return 0
        for path in ["log-workbench", "log-aggregate", "require-log-summary", "log-aggregation-review"]:
            run_quiet(tuff("add", "--agent", "open-agents", f"agent-capabilities/{path}"), f"tuff add {path}")

        if not ask(3, "List and validate installed capabilities", f"{TUFF} list && {TUFF} check", args.yes):
            return 0
        run(tuff("list"))
        run(tuff("check"))

        if pack.exists():
            pack.unlink()
        if not ask(4, "Build, verify, and inspect the Tuff pack", f"{TUFF} pack build --name {pack_name} --version {pack_version}", args.yes):
            return 0
        run_quiet(tuff("pack", "build", "--name", pack_name, "--version", pack_version), "tuff pack build")
        run_quiet(tuff("pack", "verify", str(pack)), "tuff pack verify")
        run(tuff("pack", "inspect", str(pack)))

        token = output(["gh", "auth", "token"])
        auth = base64.b64encode(f"{ghcr_user}:{token}".encode()).decode()
        (docker_config / "config.json").write_text(f'{{"auths":{{"ghcr.io":{{"auth":"{auth}"}}}}}}\n', encoding="utf-8")
        os.chmod(docker_config / "config.json", 0o600)
        publish_env = {**os.environ, "DOCKER_CONFIG": str(docker_config)}
        if not ask(5, "Publish the Tuff pack to GitHub Container Registry", f"{TUFF} pack push {pack.relative_to(ROOT)} {reference}", args.yes):
            return 0
        run_quiet(tuff("pack", "push", str(pack), reference), f"tuff pack push → {reference}", publish_env)
        package_panel(pack_name, reference, args.open_package)

        if not ask(6, "Build the clean runtime image", f"docker build -f Dockerfile.agent-runtime -t {image} .", args.yes):
            return 0
        run_quiet(["docker", "build", "-f", "Dockerfile.agent-runtime", "-t", image, "."], f"docker build {image}")
        image_table(image)

        if not key_file.is_file():
            raise SystemExit("OPENAI_API_KEY_FILE must point to an existing key file")
        if not ask(7, "Start clean container, pull/install the pack, and run the agent", f"docker run ... {image}", args.yes):
            return 0
        # -t only when the host has a real terminal: it gives the container a
        # pty so tuff's tables size themselves to the window instead of
        # wrapping, and docker rejects it when stdin is a pipe.
        container_command = ["docker", "run", "--rm", "-i"]
        if sys.stdin.isatty() and sys.stdout.isatty():
            container_command.append("-t")
        container_command.extend(["-e", f"CAPABILITY_REF={reference}", "-e", "DOCKER_CONFIG=/root/.docker"])
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
