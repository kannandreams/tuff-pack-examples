from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_SERVER = ROOT / "projects/csv-data-quality/agent-capabilities/csv-quality-check/server.py"
SECURITY_SERVER = ROOT / "projects/security-review/agent-capabilities/security-baseline-scan/server.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ToolTests(unittest.TestCase):
    def test_csv_starting_fixture_fails_and_expected_fixture_passes(self):
        csv_tool = load_module("csv_quality_check_test", CSV_SERVER)
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            shutil.copytree(ROOT / "projects/csv-data-quality", project, dirs_exist_ok=True)
            failed = csv_tool.check_csv(project)
            self.assertEqual(failed["status"], "fail")
            self.assertEqual({item["code"] for item in failed["findings"]}, {"null_value", "duplicate_key", "below_minimum", "invalid_number"})
            shutil.copy(project / "expected/orders.csv", project / "data/orders.csv")
            passed = csv_tool.check_csv(project)
            self.assertEqual(passed["status"], "pass")
            self.assertEqual(passed["row_count"], 4)

    def test_security_starting_fixture_fails_and_expected_fixture_passes(self):
        security_tool = load_module("security_baseline_scan_test", SECURITY_SERVER)
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            shutil.copytree(ROOT / "projects/security-review", project, dirs_exist_ok=True)
            failed = security_tool.scan(project)
            self.assertEqual(failed["status"], "fail")
            self.assertEqual({item["code"] for item in failed["signals"]}, {"hardcoded_secret", "dynamic_evaluation", "shell_subprocess", "interpolated_sql"})
            shutil.copy(project / "expected/service.py", project / "app/service.py")
            passed = security_tool.scan(project)
            self.assertEqual(passed["status"], "pass")

    def test_paths_cannot_escape_project(self):
        csv_tool = load_module("csv_quality_path_test", CSV_SERVER)
        security_tool = load_module("security_path_test", SECURITY_SERVER)
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary)
            for module in (csv_tool, security_tool):
                with self.assertRaises(module.InputError):
                    module.project_path(project, "../outside")
                with self.assertRaises(module.InputError):
                    module.project_path(project, "/absolute")

    def test_both_mcp_protocol_eras_list_the_tool(self):
        cases = ((CSV_SERVER, "csv_quality_check"), (SECURITY_SERVER, "security_baseline_scan"))
        for server, tool_name in cases:
            with self.subTest(tool=tool_name):
                requests = [
                    {"jsonrpc": "2.0", "id": 1, "method": "server/discover", "params": {}},
                    {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
                    {"jsonrpc": "2.0", "id": 3, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"}}},
                    {"jsonrpc": "2.0", "id": 4, "method": "tools/list", "params": {}},
                ]
                completed = subprocess.run([sys.executable, str(server)], cwd=ROOT, input="".join(json.dumps(item) + "\n" for item in requests), text=True, capture_output=True, check=True)
                responses = [json.loads(line) for line in completed.stdout.splitlines()]
                self.assertEqual(responses[0]["result"]["supportedVersions"], ["2026-07-28"])
                self.assertEqual(responses[1]["result"]["resultType"], "complete")
                self.assertEqual(responses[1]["result"]["tools"][0]["name"], tool_name)
                self.assertNotIn("resultType", responses[3]["result"])
                self.assertEqual(responses[3]["result"]["tools"][0]["name"], tool_name)


if __name__ == "__main__":
    unittest.main()
