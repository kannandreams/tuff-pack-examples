#!/usr/bin/env python3
"""Deterministic project-local security signal scanner with CLI and MCP modes."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

DEFAULT_POLICY = ".tuff-example/security-policy.json"
DEFAULT_OUTPUT = ".tuff-reports/security-review.json"
TOOL_NAME = "security_baseline_scan"
MODERN_VERSION = "2026-07-28"
LEGACY_VERSION = "2025-11-25"
DEFAULT_EXTENSIONS = [".py", ".js", ".ts", ".tsx", ".jsx", ".rs", ".go", ".java", ".rb", ".php", ".sh", ".yaml", ".yml", ".json", ".toml"]
DEFAULT_EXCLUDE = [".git", ".claude", ".agents", ".tuff-reports", "node_modules", "target", "dist", "build", "__pycache__"]
PATTERNS = [
    ("hardcoded_secret", "high", re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|auth[_-]?token|password|secret)\b\s*[:=]\s*['\"][^'\"]{8,}['\"]"), "credential-like value is assigned directly in source"),
    ("dynamic_evaluation", "high", re.compile(r"\b(?:eval|exec)\s*\("), "dynamic code evaluation requires attacker-control analysis"),
    ("shell_subprocess", "high", re.compile(r"\bsubprocess\.(?:run|call|Popen|check_output|check_call)\s*\(.*\bshell\s*=\s*True"), "shell-enabled subprocess requires command-injection analysis"),
    ("interpolated_sql", "high", re.compile(r"\b(?:execute|executemany)\s*\(\s*(?:f['\"]|['\"].*(?:%|\.format\s*\())"), "interpolated SQL requires injection analysis and parameterization"),
]


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
    if must_exist and not resolved.exists():
        raise InputError(f"path does not exist: {value}")
    return resolved


def load_policy(root: Path, policy_name: str) -> dict[str, Any]:
    path = project_path(root, policy_name, must_exist=True)
    try:
        policy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InputError(f"cannot read JSON policy {policy_name}: {exc}") from exc
    if not isinstance(policy, dict):
        raise InputError("policy must be a JSON object")
    scope = policy.get("scope", ".")
    if not isinstance(scope, str):
        raise InputError("policy field 'scope' must be a project-relative string")
    for field, default in (("extensions", DEFAULT_EXTENSIONS), ("exclude", DEFAULT_EXCLUDE)):
        value = policy.get(field, default)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise InputError(f"policy field '{field}' must be an array of non-empty strings")
    maximum = policy.get("max_file_bytes", 1_000_000)
    if not isinstance(maximum, int) or isinstance(maximum, bool) or maximum < 1:
        raise InputError("policy field 'max_file_bytes' must be a positive integer")
    return policy


def source_files(root: Path, policy: dict[str, Any]) -> list[Path]:
    scope = project_path(root, policy.get("scope", "."), must_exist=True)
    extensions = set(policy.get("extensions", DEFAULT_EXTENSIONS))
    excluded = set(policy.get("exclude", DEFAULT_EXCLUDE))
    candidates = [scope] if scope.is_file() else scope.rglob("*")
    files: list[Path] = []
    for path in candidates:
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in extensions:
            continue
        relative = path.relative_to(root.resolve())
        if any(part in excluded for part in relative.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root.resolve()).as_posix())


def scan(root: Path, policy_name: str = DEFAULT_POLICY) -> dict[str, Any]:
    policy = load_policy(root, policy_name)
    maximum = policy.get("max_file_bytes", 1_000_000)
    signals: list[dict[str, Any]] = []
    scanned: list[str] = []
    skipped: list[dict[str, str]] = []
    for path in source_files(root, policy):
        relative = path.relative_to(root.resolve()).as_posix()
        try:
            if path.stat().st_size > maximum:
                skipped.append({"path": relative, "reason": "file exceeds max_file_bytes"})
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            skipped.append({"path": relative, "reason": f"cannot read text file: {exc}"})
            continue
        scanned.append(relative)
        for line_number, line in enumerate(text.splitlines(), start=1):
            for code, severity, pattern, message in PATTERNS:
                if pattern.search(line):
                    signals.append({"code": code, "severity": severity, "path": relative, "line": line_number, "message": message})
    signals.sort(key=lambda item: (item["path"], item["line"], item["code"]))
    skipped.sort(key=lambda item: (item["path"], item["reason"]))
    return {
        "schema": 1,
        "tool": TOOL_NAME,
        "status": "pass" if not signals else "fail",
        "scope": policy.get("scope", "."),
        "files_scanned": len(scanned),
        "scanned_paths": scanned,
        "files_skipped": skipped,
        "signal_count": len(signals),
        "signals": signals,
        "limitations": "Pattern signals require contextual validation; a passing baseline does not prove security.",
    }


def write_report(root: Path, output_name: str, report: dict[str, Any]) -> None:
    output = project_path(root, output_name)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_check(root: Path, policy_name: str, output_name: str) -> dict[str, Any]:
    report = scan(root, policy_name)
    write_report(root, output_name, report)
    return {**report, "report": output_name}


def tool_definition() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": "Find deterministic security signals that must be contextually reviewed.",
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
                response = rpc_result(request_id, {"supportedVersions": [MODERN_VERSION], "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": TOOL_NAME, "version": "1.0.0"}, "instructions": "Treat signals as investigation seeds, not confirmed vulnerabilities.", "resultType": "complete", "ttlMs": 0, "cacheScope": "private"})
            elif method == "initialize":
                modern = False
                response = rpc_result(request_id, {"protocolVersion": LEGACY_VERSION, "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": TOOL_NAME, "version": "1.0.0"}, "instructions": "Treat signals as investigation seeds, not confirmed vulnerabilities."})
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
    check_parser = subparsers.add_parser("check", help="run one baseline scan")
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
