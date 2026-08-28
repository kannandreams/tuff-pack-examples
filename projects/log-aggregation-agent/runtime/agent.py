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


ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd())).resolve()


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
include the deterministic manifest counts exactly."""


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


async def run() -> None:
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
        model=os.environ.get("OPENAI_MODEL", "gpt-5.1"),
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
    print((ROOT / "reports/agent-summary.md").read_text(encoding="utf-8"))


def main() -> int:
    asyncio.run(run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
