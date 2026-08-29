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
    @staticmethod
    def triage(project, released, quarantined):
        """Write one candidate answer. There is no fixture holding the result."""
        (project / "data/orders.csv").write_text(
            "order_id,customer_id,amount,currency\n" + "".join(released), encoding="utf-8"
        )
        (project / "data/quarantine.csv").write_text(
            "source_row,order_id,reason\n" + "".join(quarantined), encoding="utf-8"
        )

    RELEASED = [
        "1001,c-1,42.50,GBP\n",
        "1002,c-2,15.00,GBP\n",
        "1003,c-3,8.25,GBP\n",
        "1004,c-4,25.00,GBP\n",
    ]
    QUARANTINED = [
        "6,1004,exact duplicate of source row 5\n",
        "7,1005,customer_id is empty\n",
        "8,1006,amount is not a number\n",
        "9,1007,amount is below the policy minimum\n",
        "10,1008,currency JPY has no conversion rate\n",
        "11,1009,conflicting duplicate\n",
        "12,1009,conflicting duplicate\n",
    ]

    def csv_project(self, temporary):
        project = Path(temporary)
        shutil.copytree(ROOT / "projects/csv-data-quality", project, dirs_exist_ok=True)
        shutil.copy(project / "data/orders-extract.csv", project / "data/orders.csv")
        (project / "data/quarantine.csv").unlink(missing_ok=True)
        return project

    def test_csv_starting_fixture_fails_and_a_correct_triage_passes(self):
        csv_tool = load_module("csv_quality_check_test", CSV_SERVER)
        with tempfile.TemporaryDirectory() as temporary:
            project = self.csv_project(temporary)
            failed = csv_tool.check_csv(project)
            self.assertEqual(failed["status"], "fail")
            self.assertEqual(
                {item["code"] for item in failed["findings"]},
                {
                    "null_value",
                    "duplicate_key",
                    "below_minimum",
                    "invalid_number",
                    "value_not_allowed",
                    "quarantine_missing",
                },
            )
            self.triage(project, self.RELEASED, self.QUARANTINED)
            passed = csv_tool.check_csv(project)
            self.assertEqual(passed["status"], "pass", passed["findings"])
            self.assertEqual(passed["row_count"], 4)

    def test_csv_reconciliation_rejects_shortcuts(self):
        """Quarantining must not be able to collapse into deleting."""
        csv_tool = load_module("csv_quality_check_reconcile_test", CSV_SERVER)
        shortcuts = {
            "quarantine_missing": (self.RELEASED, None),
            "quarantine_reason": (self.RELEASED, self.QUARANTINED[:1] + ["7,1005,\n"] + self.QUARANTINED[2:]),
            "invented_row": (self.RELEASED + ["9999,c-99,50.00,GBP\n"], self.QUARANTINED[:-1]),
            "quarantine_duplicate": (self.RELEASED[:-1], self.QUARANTINED + ["12,1009,padding\n"]),
            "row_accounting": (self.RELEASED, self.QUARANTINED[:-1]),
        }
        for expected_code, (released, quarantined) in shortcuts.items():
            with self.subTest(shortcut=expected_code):
                with tempfile.TemporaryDirectory() as temporary:
                    project = self.csv_project(temporary)
                    if quarantined is None:
                        self.triage(project, released, [])
                        (project / "data/quarantine.csv").unlink()
                    else:
                        self.triage(project, released, quarantined)
                    report = csv_tool.check_csv(project)
                    self.assertEqual(report["status"], "fail")
                    self.assertIn(expected_code, {item["code"] for item in report["findings"]})

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
