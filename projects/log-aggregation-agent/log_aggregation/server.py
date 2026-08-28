from __future__ import annotations

import json
import sys
from pathlib import Path

from .engine import aggregate_log, write_reports

TOOL_NAME = "log_aggregate"


def response(request_id, result):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def error(request_id, message):
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32602, "message": message}}


def project_path(root: Path, value: str) -> Path:
    candidate = (root / value).resolve()
    if root not in candidate.parents:
        raise ValueError(f"path must remain inside the project: {value}")
    return candidate


def main() -> int:
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request_id = None
        try:
            request = json.loads(raw)
            request_id = request.get("id")
            method = request.get("method")
            params = request.get("params") or {}
            if method in {"initialize", "server/discover"}:
                result = {"protocolVersion": "2025-11-25", "capabilities": {"tools": {"listChanged": False}}, "serverInfo": {"name": TOOL_NAME, "version": "1.0.0"}}
                if method == "server/discover":
                    result["supportedVersions"] = ["2026-07-28"]
                print(json.dumps(response(request_id, result), separators=(",", ":")), flush=True)
            elif method == "tools/list":
                tool = {"name": TOOL_NAME, "description": "Group sanitized application log lines while preserving complete source-line coverage.", "inputSchema": {"type": "object", "properties": {"input": {"type": "string"}, "json_output": {"type": "string"}, "markdown_output": {"type": "string"}}, "required": ["input", "json_output", "markdown_output"], "additionalProperties": False}}
                print(json.dumps(response(request_id, {"tools": [tool]}), separators=(",", ":")), flush=True)
            elif method == "tools/call":
                arguments = params.get("arguments") or {}
                root = Path.cwd().resolve()
                input_value = arguments["input"]
                json_value = arguments["json_output"]
                markdown_value = arguments["markdown_output"]
                input_path = project_path(root, input_value)
                manifest = aggregate_log(input_path, input_label=input_value)
                write_reports(manifest, project_path(root, json_value), project_path(root, markdown_value))
                body = {"content": [{"type": "text", "text": json.dumps(manifest, sort_keys=True)}], "structuredContent": manifest}
                print(json.dumps(response(request_id, body), separators=(",", ":")), flush=True)
            elif "id" in request:
                print(json.dumps(error(request_id, "method not found"), separators=(",", ":")), flush=True)
        except Exception as exc:
            print(json.dumps(error(request_id, str(exc)), separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
