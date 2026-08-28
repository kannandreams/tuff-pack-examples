from __future__ import annotations

import difflib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

TIMESTAMP_RE = re.compile(r"^(?P<timestamp>\S+)\s+(?P<level>[A-Za-z]+)\s+(?P<service>\S+)\s+(?P<body>.*)$")
FIELD_RE = re.compile(r"(?P<key>[A-Za-z_][A-Za-z0-9_]*)=(?P<value>\"[^\"]*\"|\S+)")
UUID_RE = re.compile(r"\b[0-9a-f]{8}-[0-9a-f-]{27,}\b", re.I)
IP_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
SECRET_RE = re.compile(
    r"(?i)(bearer\s+|(?:api[_-]?key|token|password|secret)\s*[=:]\s*)[A-Za-z0-9_./+=:-]+"
)


@dataclass(frozen=True)
class Event:
    line: int
    timestamp: str | None
    level: str
    service: str
    message: str
    fields: dict[str, str]
    sanitized: str


def scrub(value: str) -> str:
    return SECRET_RE.sub(lambda match: f"{match.group(1)}<redacted>", value)


def parse_line(line_number: int, raw: str) -> Event:
    sanitized = scrub(raw.rstrip("\n"))
    match = TIMESTAMP_RE.match(sanitized)
    if not match:
        return Event(line_number, None, "UNKNOWN", "unknown", sanitized, {}, sanitized)

    fields = {item.group("key"): item.group("value").strip('"') for item in FIELD_RE.finditer(match.group("body"))}
    message = FIELD_RE.sub("", match.group("body"))
    message = " ".join(message.split()) or "<structured event>"
    level = match.group("level").upper().replace("WARNING", "WARN")
    return Event(line_number, match.group("timestamp"), level, match.group("service"), message, fields, sanitized)


def fingerprint(event: Event) -> str:
    value = event.message.lower()
    value = UUID_RE.sub("<uuid>", value)
    value = IP_RE.sub("<ip>", value)
    value = NUMBER_RE.sub("<number>", value)
    return re.sub(r"\s+", " ", value).strip()


def line_ranges(lines: list[int]) -> list[str]:
    if not lines:
        return []
    result: list[str] = []
    start = previous = lines[0]
    for line in lines[1:]:
        if line == previous + 1:
            previous = line
            continue
        result.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = line
    result.append(str(start) if start == previous else f"{start}-{previous}")
    return result


def _compatible(event: Event, group: dict[str, Any]) -> bool:
    return event.service == group["service"] and event.level == group["level"]


def _similar(left: str, right: str) -> bool:
    return difflib.SequenceMatcher(None, left, right).ratio() >= 0.88


def aggregate_log(path: str | Path, input_label: str | None = None) -> dict[str, Any]:
    input_path = Path(path)
    events = [parse_line(number, line) for number, line in enumerate(input_path.read_text(encoding="utf-8").splitlines(), 1)]
    groups: list[dict[str, Any]] = []

    for event in events:
        normalized = fingerprint(event)
        selected: dict[str, Any] | None = None
        for group in groups:
            if not _compatible(event, group):
                continue
            if group["fingerprint"] == normalized or _similar(normalized, group["fingerprint"]):
                selected = group
                break
        if selected is None:
            selected = {
                "group_id": f"event-{len(groups) + 1:03d}",
                "fingerprint": normalized,
                "service": event.service,
                "level": event.level,
                "count": 0,
                "line_numbers": [],
                "timestamps": [],
                "request_ids": [],
                "trace_ids": [],
                "representative_lines": [],
                "messages": [],
            }
            groups.append(selected)

        selected["count"] += 1
        selected["line_numbers"].append(event.line)
        if event.timestamp:
            selected["timestamps"].append(event.timestamp)
        for field, target in (("request_id", "request_ids"), ("trace_id", "trace_ids")):
            if event.fields.get(field) and event.fields[field] not in selected[target]:
                selected[target].append(event.fields[field])
        if event.sanitized not in selected["representative_lines"] and len(selected["representative_lines"]) < 3:
            selected["representative_lines"].append(event.sanitized)
        if event.message not in selected["messages"] and len(selected["messages"]) < 3:
            selected["messages"].append(event.message)

    for group in groups:
        numbers = group.pop("line_numbers")
        timestamps = group.pop("timestamps")
        group["line_ranges"] = line_ranges(numbers)
        group["first_timestamp"] = timestamps[0] if timestamps else None
        group["last_timestamp"] = timestamps[-1] if timestamps else None

    input_lines = len(events)
    grouped_lines = sum(group["count"] for group in groups)
    return {
        "schema": 1,
        "input": input_label or str(input_path),
        "input_line_count": input_lines,
        "group_count": len(groups),
        "compressed_line_count": len(groups),
        "compression_ratio": round(input_lines / len(groups), 2) if groups else 0,
        "covered_line_count": grouped_lines,
        "uncovered_line_count": input_lines - grouped_lines,
        "groups": groups,
    }


def write_reports(manifest: dict[str, Any], json_path: str | Path, markdown_path: str | Path) -> None:
    json_file = Path(json_path)
    markdown_file = Path(markdown_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    markdown_file.parent.mkdir(parents=True, exist_ok=True)
    json_file.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Incident log summary",
        "",
        f"- Input lines: **{manifest['input_line_count']}**",
        f"- Event groups: **{manifest['group_count']}**",
        f"- Compression ratio: **{manifest['compression_ratio']}x**",
        f"- Line coverage: **{manifest['covered_line_count']}/{manifest['input_line_count']}**",
        "",
        "## Evidence groups",
    ]
    for group in manifest["groups"]:
        lines.extend([
            "",
            f"### {group['group_id']} — {group['level']} {group['service']} ({group['count']} lines)",
            f"- Source lines: `{', '.join(group['line_ranges'])}`",
            f"- Time range: `{group['first_timestamp']}` → `{group['last_timestamp']}`",
            f"- Request IDs: `{', '.join(group['request_ids']) or 'none'}`",
            f"- Trace IDs: `{', '.join(group['trace_ids']) or 'none'}`",
            "- Evidence:",
        ])
        lines.extend(f"  - `{line}`" for line in group["representative_lines"])
    markdown_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
