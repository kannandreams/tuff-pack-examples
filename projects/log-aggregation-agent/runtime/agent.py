from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

from agents import Agent, Runner, set_default_openai_key
from agents.mcp import MCPServerStdio, create_static_tool_filter
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table


ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd())).resolve()
DEMO_MODEL = "gpt-5-mini"
console = Console()


class IncidentSummary(BaseModel):
    title: str
    summary: str
    timeline: list[str] = Field(default_factory=list)
    affected_services: list[str] = Field(default_factory=list)
    observed_facts: list[str] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    evidence_groups: list[str] = Field(default_factory=list)
    input_line_count: int
    group_count: int
    compression_ratio: float
    covered_line_count: int
    report_paths: list[str] = Field(default_factory=list)


def api_key() -> str:
    key_file = Path(os.environ.get("OPENAI_API_KEY_FILE", "/run/secrets/openai_api_key"))
    if not key_file.is_file():
        raise RuntimeError(f"OpenAI key file not found: {key_file}")
    key = key_file.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError("OpenAI key file does not contain an sk- key")
    return key


def instructions() -> str:
    return """You are an incident context aggregator for an on-call engineer.
First call the log_aggregate MCP tool exactly once with:
input=data/api.log, json_output=reports/aggregation.json,
markdown_output=reports/aggregation.md.
Use only the tool's sanitized manifest and evidence. Never request or infer raw
secrets. Preserve the source line ranges, request IDs, trace IDs, services,
levels, and timestamps. Clearly separate observed facts from hypotheses; do not
claim a root cause unless the evidence proves it. Explain what the on-call
engineer should investigate next. Return the requested structured summary and
include the deterministic manifest counts exactly. If the tool call fails,
stop and report the failure instead of producing an incident summary."""


def write_summary(summary: IncidentSummary) -> None:
    reports = ROOT / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    payload = summary.model_dump()
    (reports / "agent-summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {summary.title}", "", summary.summary, "", "## Timeline"]
    lines.extend(f"- {item}" for item in summary.timeline)
    lines.extend(["", "## Affected services"])
    lines.extend(f"- `{item}`" for item in summary.affected_services)
    for heading, values in (("Observed facts", summary.observed_facts), ("Hypotheses", summary.hypotheses), ("Uncertainties", summary.uncertainties)):
        lines.extend(["", f"## {heading}"])
        lines.extend(f"- {item}" for item in values)
    lines.extend(["", "## Evidence groups"])
    lines.extend(f"- `{item}`" for item in summary.evidence_groups)
    lines.extend(["", "## Deterministic coverage", f"- Input lines: **{summary.input_line_count}**", f"- Groups: **{summary.group_count}**", f"- Compression: **{summary.compression_ratio}x**", f"- Covered lines: **{summary.covered_line_count}**", "", "Reports: `reports/aggregation.json`, `reports/aggregation.md`"])
    (reports / "agent-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def clip(text: str, limit: int = 200) -> str:
    return text if len(text) <= limit else f"{text[: limit - 1].rstrip()}…"


def render_summary(path: Path) -> None:
    """Show the incident summary at reading speed.

    The full report keeps every evidence group and raw timeline line; printing
    it verbatim buries the result under several screens of manifest text, so
    the terminal gets the conclusions and a pointer to the file. Set
    AGENT_SUMMARY_FULL=1 for the untouched markdown.
    """
    text = path.read_text(encoding="utf-8")
    if os.environ.get("AGENT_SUMMARY_FULL") == "1":
        print(text)
        return

    title = ""
    lead: list[str] = []
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if line.startswith("# "):
            title = line[2:].strip()
        elif line.startswith("## "):
            current = line[3:].strip()
            sections[current] = []
        elif not stripped:
            continue
        elif current is None:
            lead.append(stripped)
        else:
            sections[current].append(stripped.removeprefix("- ").strip())

    console.print()
    console.print(Panel(escape(" ".join(lead)), title=f"[bold]{escape(title)}[/bold]", title_align="left", border_style="green"))

    coverage = " · ".join(item.replace("**", "") for item in sections.get("Deterministic coverage", []) if ":" in item and not item.startswith("Reports"))
    facts = Table(box=None, show_header=False, pad_edge=False)
    facts.add_column(style="dim")
    facts.add_column(overflow="fold")
    facts.add_row("services", ", ".join(item.strip("`") for item in sections.get("Affected services", [])))
    facts.add_row("timeline", f"{len(sections.get('Timeline', []))} events")
    facts.add_row("evidence", f"{len(sections.get('Evidence groups', []))} groups")
    facts.add_row("coverage", coverage)
    console.print(facts)

    for heading in ("Hypotheses", "Uncertainties"):
        items = sections.get(heading, [])
        if not items:
            continue
        console.print(f"\n[bold]{heading}[/bold]")
        bullets = Table(box=None, show_header=False, pad_edge=False, padding=(0, 1))
        bullets.add_column(style="cyan", width=1)
        bullets.add_column(overflow="fold")
        for item in items:
            bullets.add_row("•", escape(clip(item)))
        console.print(bullets)

    console.print("\n[dim]Full report: reports/agent-summary.md · reports/aggregation.json · reports/aggregation.md[/dim]")


async def run() -> None:
    cached_summary = ROOT / "reports/agent-summary.md"
    if cached_summary.is_file():
        render_summary(cached_summary)
        return

    set_default_openai_key(api_key())
    tool_server = MCPServerStdio(
        name="log-aggregation",
        params={
            "command": sys.executable,
            "args": [str(ROOT / ".agents/tools/log-aggregate/server.py")],
            "cwd": str(ROOT),
        },
        tool_filter=create_static_tool_filter(allowed_tool_names=["log_aggregate"]),
    )
    agent = Agent(
        name="Incident Context Aggregator",
        model=DEMO_MODEL,
        instructions=instructions(),
        mcp_servers=[tool_server],
        output_type=IncidentSummary,
    )
    async with tool_server:
        result = await Runner.run(agent, "Aggregate the API outage logs and prepare the on-call handoff.")
    write_summary(result.final_output)
    hook = subprocess.run([sys.executable, ".agents/hooks/require-log-summary/run.py"], cwd=ROOT, text=True)
    if hook.returncode:
        raise RuntimeError("require-log-summary hook failed")
    render_summary(ROOT / "reports/agent-summary.md")


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
