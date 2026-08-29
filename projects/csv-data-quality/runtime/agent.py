"""Agent that decides which extract rows to release and which to quarantine.

The split of work matters. The packaged `csv_quality_check` tool decides what
violates the policy, deterministically and identically every run. The model
decides only what cannot be derived from the data: whether a violation is
repairable from the evidence at hand, or whether the correct value is a
business fact nobody has. Writing the files is deterministic Python again, so
a plan that does not account for every source row is rejected before anything
is written.
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import subprocess
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path

from agents import Agent, Runner, set_default_openai_key
from agents.mcp import MCPServerStdio, create_static_tool_filter
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.table import Table


ROOT = Path(os.environ.get("PROJECT_ROOT", Path.cwd())).resolve()
POLICY = os.environ.get("DATA_QUALITY_POLICY", ".tuff-example/data-quality-policy.json")
REPORT = os.environ.get("DATA_QUALITY_REPORT", ".tuff-reports/data-quality.json")
DEMO_MODEL = "gpt-5-mini"
console = Console()


class ReleasedRow(BaseModel):
    source_row: int = Field(description="Line number in the extract, header counted as line 1")
    order_id: str
    customer_id: str
    amount: str
    currency: str


class QuarantinedRow(BaseModel):
    source_row: int = Field(description="Line number in the extract, header counted as line 1")
    order_id: str
    reason: str = Field(description="Why this row cannot be released, specific to the row")


class RepairPlan(BaseModel):
    released: list[ReleasedRow] = Field(default_factory=list)
    quarantined: list[QuarantinedRow] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def api_key() -> str:
    key_file = Path(os.environ.get("OPENAI_API_KEY_FILE", "/run/secrets/openai_api_key"))
    if not key_file.is_file():
        raise RuntimeError(f"OpenAI key file not found: {key_file}")
    key = key_file.read_text(encoding="utf-8").strip()
    if not key.startswith("sk-"):
        raise RuntimeError("OpenAI key file does not contain an sk- key")
    return key


def policy() -> dict:
    return json.loads((ROOT / POLICY).read_text(encoding="utf-8"))


def source_rows() -> list[tuple[int, dict[str, str]]]:
    path = ROOT / policy()["source"]
    with path.open(newline="", encoding="utf-8") as handle:
        return [(number, row) for number, row in enumerate(csv.DictReader(handle), start=2)]


def instructions() -> str:
    return """You prepare a delivered orders extract for a downstream revenue load.

Call the csv_quality_check MCP tool once before deciding anything, and treat
its findings as the authoritative list of policy violations.

Then decide, for every row in the extract, whether to release or quarantine it.

Repair and release a row only when the correct value follows from the data
itself: normalizing the case of a currency code that is already correct,
trimming surrounding whitespace, or dropping a row that duplicates another in
every single field.

Quarantine a row when the correct value is a business fact the extract does not
contain: a missing customer, an amount that is not a number, a negative amount,
a currency with no conversion rate available, or two rows that claim the same
order_id with different values. When two rows conflict on a key, quarantine
both — you cannot know which is right.

Never invent a business value. A guessed customer or amount that makes the
check pass corrupts the revenue load silently, which is worse than a
quarantined row. Every extract row must appear exactly once across released and
quarantined, identified by its source_row line number."""


def write_plan(plan: RepairPlan) -> None:
    settings = policy()
    released = sorted(plan.released, key=lambda row: row.source_row)
    quarantined = sorted(plan.quarantined, key=lambda row: row.source_row)

    governed = ROOT / settings["input"]
    with governed.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["order_id", "customer_id", "amount", "currency"])
        writer.writeheader()
        for row in released:
            writer.writerow({
                "order_id": row.order_id,
                "customer_id": row.customer_id,
                "amount": row.amount,
                "currency": row.currency,
            })

    quarantine = ROOT / settings["quarantine"]
    with quarantine.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["source_row", "order_id", "reason"])
        writer.writeheader()
        for row in quarantined:
            writer.writerow({"source_row": row.source_row, "order_id": row.order_id, "reason": row.reason})


def plan_gaps(plan: RepairPlan) -> list[str]:
    """Reject a plan that does not account for the extract, before writing it."""
    expected = {number for number, _ in source_rows()}
    claimed: dict[int, int] = {}
    for row in [*plan.released, *plan.quarantined]:
        claimed[row.source_row] = claimed.get(row.source_row, 0) + 1

    problems = []
    for number in sorted(expected - claimed.keys()):
        problems.append(f"source row {number} is neither released nor quarantined")
    for number in sorted(claimed.keys() - expected):
        problems.append(f"source row {number} does not exist in the extract")
    for number, count in sorted(claimed.items()):
        if count > 1 and number in expected:
            problems.append(f"source row {number} is claimed {count} times")
    for row in plan.quarantined:
        if not row.reason.strip():
            problems.append(f"source row {row.source_row} is quarantined without a reason")
    return problems


def run_check() -> dict:
    checker = ROOT / ".agents/tools/csv-quality-check/server.py"
    subprocess.run(
        [sys.executable, str(checker), "check", "--policy", POLICY, "--output", REPORT],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return json.loads((ROOT / REPORT).read_text(encoding="utf-8"))


def released_total(plan: RepairPlan) -> str:
    totals: dict[str, Decimal] = {}
    for row in plan.released:
        try:
            totals[row.currency] = totals.get(row.currency, Decimal(0)) + Decimal(row.amount.strip())
        except InvalidOperation:
            return "unavailable"
    return ", ".join(f"{currency} {total}" for currency, total in sorted(totals.items())) or "nothing released"


def render(plan: RepairPlan, report: dict) -> None:
    console.print()
    status = report["status"]
    console.print(
        Panel(
            f"released [bold]{len(plan.released)}[/bold] · quarantined [bold]{len(plan.quarantined)}[/bold] · "
            f"total {escape(released_total(plan))}",
            title=f"[bold]Data quality: {status}[/bold]",
            title_align="left",
            border_style="green" if status == "pass" else "red",
        )
    )
    if plan.quarantined:
        table = Table("source row", "order", "reason", box=None, pad_edge=False)
        for row in sorted(plan.quarantined, key=lambda item: item.source_row):
            table.add_row(str(row.source_row), escape(row.order_id), escape(row.reason))
        console.print(table)
    for note in plan.notes:
        console.print(f"  [dim]{escape(note)}[/dim]")
    console.print(f"\n[dim]Report: {REPORT}[/dim]")


async def run() -> int:
    set_default_openai_key(api_key())
    tool_server = MCPServerStdio(
        name="csv-quality-check",
        params={
            "command": sys.executable,
            "args": [str(ROOT / ".agents/tools/csv-quality-check/server.py")],
            "cwd": str(ROOT),
        },
        tool_filter=create_static_tool_filter(allowed_tool_names=["csv_quality_check"]),
    )
    agent = Agent(
        name="CSV Data Quality Steward",
        model=DEMO_MODEL,
        instructions=instructions(),
        mcp_servers=[tool_server],
        output_type=RepairPlan,
    )
    extract = "\n".join(
        f"{number}: " + ",".join(f"{key}={value!r}" for key, value in row.items())
        for number, row in source_rows()
    )
    prompt = (
        f"Policy: {json.dumps(policy(), sort_keys=True)}\n\n"
        f"Extract rows, by source_row line number:\n{extract}\n\n"
        "Decide the release and quarantine sets."
    )
    async with tool_server:
        result = await Runner.run(agent, prompt)
    plan: RepairPlan = result.final_output

    gaps = plan_gaps(plan)
    if gaps:
        console.print("[bold red]The plan does not account for the extract; nothing was written.[/bold red]")
        for gap in gaps:
            console.print(f"  [red]•[/red] {escape(gap)}")
        return 1

    write_plan(plan)
    report = run_check()
    render(plan, report)
    return 0 if report["status"] == "pass" else 1


def main() -> int:
    return asyncio.run(run())


if __name__ == "__main__":
    raise SystemExit(main())
