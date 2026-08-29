#!/usr/bin/env python3
"""Deterministic CSV quality checker with CLI and stdio MCP interfaces."""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any

DEFAULT_POLICY = ".tuff-example/data-quality-policy.json"
DEFAULT_OUTPUT = ".tuff-reports/data-quality.json"
TOOL_NAME = "csv_quality_check"
MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"


class InputError(Exception):
    """A safe, user-actionable policy or input error."""


def project_path(root: Path, value: str, *, must_exist: bool = False) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        raise InputError(f"path must be project-relative: {value}")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise InputError(f"path escapes the project: {value}")
    if must_exist and not resolved.is_file():
        raise InputError(f"file does not exist: {value}")
    return resolved


def load_policy(root: Path, policy_name: str) -> dict[str, Any]:
    path = project_path(root, policy_name, must_exist=True)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read JSON policy {policy_name}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputError("policy must be a JSON object")
    if not isinstance(value.get("input"), str):
        raise InputError("policy field 'input' must be a project-relative string")
    for field in ("required_columns", "non_null"):
        if field in value and not (
            isinstance(value[field], list)
            and all(isinstance(item, str) for item in value[field])
        ):
            raise InputError(f"policy field '{field}' must be an array of strings")
    if "unique_key" in value and not isinstance(value["unique_key"], str):
        raise InputError("policy field 'unique_key' must be a string")
    for field in ("source", "quarantine"):
        if field in value and not isinstance(value[field], str):
            raise InputError(f"policy field '{field}' must be a project-relative string")
    allowed = value.get("allowed_values", {})
    if not isinstance(allowed, dict) or not all(
        isinstance(name, str)
        and isinstance(values, list)
        and values
        and all(isinstance(item, str) for item in values)
        for name, values in allowed.items()
    ):
        raise InputError(
            "policy field 'allowed_values' must map column names to non-empty arrays of strings"
        )
    numeric = value.get("numeric", {})
    if not isinstance(numeric, dict) or not all(
        isinstance(name, str) and isinstance(rule, dict)
        for name, rule in numeric.items()
    ):
        raise InputError("policy field 'numeric' must map column names to rule objects")
    for name, rule in numeric.items():
        unknown = set(rule) - {"min", "max"}
        if unknown or not all(
            isinstance(number, (int, float)) and not isinstance(number, bool)
            for number in rule.values()
        ):
            raise InputError(f"numeric rule for '{name}' may contain only numeric min/max")
    return value


def finding(code: str, message: str, row: int | None = None, column: str | None = None) -> dict[str, Any]:
    item: dict[str, Any] = {"code": code, "message": message}
    if row is not None:
        item["row"] = row
    if column is not None:
        item["column"] = column
    return item


def read_rows(root: Path, name: str) -> tuple[list[dict[str, Any]], list[str]]:
    path = project_path(root, name, must_exist=True)
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            if columns is None:
                raise InputError(f"CSV has no header: {name}")
            return list(reader), list(columns)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InputError(f"cannot read CSV {name}: {exc}") from exc


def reconcile(root: Path, policy: dict[str, Any], governed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Account for every source row exactly once.

    Without this, quarantining is indistinguishable from deleting: an agent
    could drop every row it could not repair and the governed file would pass
    on its own.
    """
    source_name = policy["source"]
    quarantine_name = policy["quarantine"]
    findings: list[dict[str, Any]] = []
    source_rows, _ = read_rows(root, source_name)

    try:
        quarantine_rows, quarantine_columns = read_rows(root, quarantine_name)
    except InputError:
        return [
            finding(
                "quarantine_missing",
                f"every source row must be released or quarantined, but {quarantine_name} does not exist",
            )
        ]

    for required in ("source_row", "reason"):
        if required not in quarantine_columns:
            findings.append(
                finding("quarantine_schema", f"quarantine file must have a {required} column", column=required)
            )
    if findings:
        return findings

    seen: dict[int, int] = {}
    for row_number, row in enumerate(quarantine_rows, start=2):
        raw = str(row.get("source_row", "")).strip()
        try:
            source_row = int(raw)
        except ValueError:
            findings.append(finding("quarantine_source_row", f"source_row is not an integer: {raw!r}", row_number, "source_row"))
            continue
        if not 2 <= source_row <= len(source_rows) + 1:
            findings.append(finding("quarantine_source_row", f"source_row {source_row} is outside {source_name}", row_number, "source_row"))
        elif source_row in seen:
            findings.append(finding("quarantine_duplicate", f"source_row {source_row} is already quarantined on row {seen[source_row]}", row_number, "source_row"))
        else:
            seen[source_row] = row_number
        if not str(row.get("reason", "")).strip():
            findings.append(finding("quarantine_reason", "every quarantined row needs a non-empty reason", row_number, "reason"))

    released = len(governed)
    quarantined = len(quarantine_rows)
    if released + quarantined != len(source_rows):
        findings.append(
            finding(
                "row_accounting",
                f"{len(source_rows)} source rows must be accounted for, but {released} were released and {quarantined} quarantined",
            )
        )

    source_keys = [str(row.get("order_id", "")).strip() for row in source_rows]
    for row_number, row in enumerate(governed, start=2):
        key = str(row.get("order_id", "")).strip()
        if key and key not in source_keys:
            findings.append(finding("invented_row", f"order_id {key} does not appear in {source_name}", row_number, "order_id"))

    return findings


def check_csv(root: Path, policy_name: str = DEFAULT_POLICY) -> dict[str, Any]:
    policy = load_policy(root, policy_name)
    input_name = policy["input"]
    input_path = project_path(root, input_name, must_exist=True)
    findings: list[dict[str, Any]] = []
    rows: list[dict[str | None, str | list[str] | None]] = []
    try:
        with input_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames
            if columns is None:
                raise InputError(f"CSV has no header: {input_name}")
            if len(columns) != len(set(columns)):
                findings.append(finding("duplicate_header", "CSV header contains duplicate column names"))
            for row_number, row in enumerate(reader, start=2):
                rows.append(row)
                if None in row or any(value is None for key, value in row.items() if key is not None):
                    findings.append(finding("malformed_row", "row has a different number of fields than the header", row_number))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InputError(f"cannot read CSV {input_name}: {exc}") from exc

    required = policy.get("required_columns", [])
    missing_columns = [name for name in required if name not in columns]
    for name in missing_columns:
        findings.append(finding("missing_column", f"required column is missing: {name}", column=name))

    non_null = policy.get("non_null", [])
    for row_number, row in enumerate(rows, start=2):
        for name in non_null:
            if name in columns and (row.get(name) is None or str(row.get(name, "")).strip() == ""):
                findings.append(finding("null_value", f"required value is empty in column {name}", row_number, name))

    unique_key = policy.get("unique_key")
    if unique_key and unique_key in columns:
        seen: dict[str, int] = {}
        for row_number, row in enumerate(rows, start=2):
            value = str(row.get(unique_key, "")).strip()
            if not value:
                continue
            if value in seen:
                findings.append(finding("duplicate_key", f"value duplicates row {seen[value]} in key {unique_key}", row_number, unique_key))
            else:
                seen[value] = row_number

    for name, values in sorted(policy.get("allowed_values", {}).items()):
        if name not in columns:
            continue
        permitted = set(values)
        for row_number, row in enumerate(rows, start=2):
            raw = row.get(name)
            if raw is None or str(raw).strip() == "":
                continue
            if str(raw) not in permitted:
                findings.append(
                    finding(
                        "value_not_allowed",
                        f"value is not one of {', '.join(sorted(permitted))} in column {name}",
                        row_number,
                        name,
                    )
                )

    for name, rule in sorted(policy.get("numeric", {}).items()):
        if name not in columns:
            continue
        for row_number, row in enumerate(rows, start=2):
            raw = str(row.get(name, "")).strip()
            if not raw:
                continue
            try:
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError
            except ValueError:
                findings.append(finding("invalid_number", f"value is not a finite number in column {name}", row_number, name))
                continue
            if "min" in rule and value < rule["min"]:
                findings.append(finding("below_minimum", f"value is below minimum {rule['min']} in column {name}", row_number, name))
            if "max" in rule and value > rule["max"]:
                findings.append(finding("above_maximum", f"value is above maximum {rule['max']} in column {name}", row_number, name))

    if "source" in policy and "quarantine" in policy:
        findings.extend(reconcile(root, policy, rows))

    findings.sort(key=lambda item: (item.get("row", 0), item.get("column", ""), item["code"], item["message"]))
    return {
        "schema": 1,
        "tool": TOOL_NAME,
        "status": "pass" if not findings else "fail",
        "input": input_name,
        "row_count": len(rows),
        "columns": columns,
        "finding_count": len(findings),
        "findings": findings,
    }


def write_report(root: Path, output_name: str, report: dict[str, Any]) -> None:
    output_path = project_path(root, output_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_check(root: Path, policy_name: str, output_name: str) -> dict[str, Any]:
    report = check_csv(root, policy_name)
    write_report(root, output_name, report)
    report = {**report, "report": output_name}
    return report


def tool_definition() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": "Validate a CSV against the project's deterministic data-quality policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "policy": {"type": "string", "description": f"Project-relative policy path; default {DEFAULT_POLICY}."},
                "output": {"type": "string", "description": f"Project-relative report path; default {DEFAULT_OUTPUT}."},
            },
            "additionalProperties": False,
        },
    }


def modernize(result: dict[str, Any], modern: bool) -> dict[str, Any]:
    if modern:
        return {**result, "resultType": "complete", "ttlMs": 0, "cacheScope": "private"}
    return result


def rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


def serve_mcp(root: Path) -> int:
    modern = False
    for raw_line in sys.stdin:
        if not raw_line.strip():
            continue
        request_id: Any = None
        try:
            request = json.loads(raw_line)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            if "id" not in request:
                continue
            if method == "server/discover":
                modern = True
                result = {
                    "supportedVersions": [MODERN_VERSION],
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": TOOL_NAME, "version": "1.0.0"},
                    "instructions": "Use this tool before and after editing policy-governed CSV data.",
                    "resultType": "complete",
                    "ttlMs": 0,
                    "cacheScope": "private",
                }
                response = rpc_result(request_id, result)
            elif method == "initialize":
                modern = False
                result = {
                    "protocolVersion": LEGACY_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": TOOL_NAME, "version": "1.0.0"},
                    "instructions": "Use this tool before and after editing policy-governed CSV data.",
                }
                response = rpc_result(request_id, result)
            elif method == "ping":
                response = rpc_result(request_id, modernize({}, modern))
            elif method == "tools/list":
                response = rpc_result(request_id, modernize({"tools": [tool_definition()]}, modern))
            elif method == "tools/call":
                if params.get("name") != TOOL_NAME:
                    response = rpc_error(request_id, -32602, f"unknown tool: {params.get('name')}")
                else:
                    arguments = params.get("arguments") or {}
                    try:
                        report = run_check(root, arguments.get("policy", DEFAULT_POLICY), arguments.get("output", DEFAULT_OUTPUT))
                        body = {"content": [{"type": "text", "text": json.dumps(report, sort_keys=True)}], "structuredContent": report, "isError": report["status"] != "pass"}
                    except InputError as exc:
                        body = {"content": [{"type": "text", "text": str(exc)}], "isError": True}
                    response = rpc_result(request_id, modernize(body, modern))
            else:
                response = rpc_error(request_id, -32601, "Method not found")
        except (json.JSONDecodeError, AttributeError, TypeError) as exc:
            response = rpc_error(request_id, -32600, f"Invalid request: {exc}")
        sys.stdout.write(json.dumps(response, separators=(",", ":"), sort_keys=True) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command")
    check_parser = subparsers.add_parser("check", help="run one CSV quality check")
    check_parser.add_argument("--policy", default=DEFAULT_POLICY)
    check_parser.add_argument("--output", default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    root = Path.cwd()
    if args.command is None:
        return serve_mcp(root)
    try:
        report = run_check(root, args.policy, args.output)
    except InputError as exc:
        print(json.dumps({"schema": 1, "tool": TOOL_NAME, "status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
