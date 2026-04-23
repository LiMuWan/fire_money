from __future__ import annotations

import unittest

from tools.run_stability_suite import (
    CommandResult,
    _build_test_summary,
    _extract_first_failure,
    _extract_pass_count,
    _render_summary,
)


class StabilitySuiteToolTests(unittest.TestCase):
    def test_extract_pass_count_reads_unittest_footer(self) -> None:
        output = """
test_alpha ... ok
test_beta ... ok

----------------------------------------------------------------------
Ran 42 tests in 3.210s

OK
""".strip()

        self.assertEqual(_extract_pass_count(output), 42)

    def test_extract_first_failure_reads_first_failure_block(self) -> None:
        output = """
................................................................E
======================================================================
ERROR: test_current_strategy_budget_bias_map_passes_execution_recap (tests.test_core.StrategyWorkflowTests.test_current_strategy_budget_bias_map_passes_execution_recap)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "tests/test_core.py", line 19215, in test_current_strategy_budget_bias_map_passes_execution_recap
    self.assertEqual(bias_map["龙头模型"], 0.92)
KeyError: '龙头模型'

----------------------------------------------------------------------
Ran 98 tests in 4.353s

FAILED (errors=1)
""".strip()

        failure = _extract_first_failure(output)

        self.assertIsNotNone(failure)
        self.assertEqual(failure["kind"], "ERROR")
        self.assertIn("test_current_strategy_budget_bias_map_passes_execution_recap", failure["name"])
        self.assertEqual(failure["summary"], "KeyError: '龙头模型'")

    def test_build_test_summary_includes_first_failure(self) -> None:
        result = CommandResult(
            name="full_tests",
            returncode=1,
            stdout="""
======================================================================
FAIL: test_load_universe_folder_runs_local_scan (tests.test_core.StrategyWorkflowTests.test_load_universe_folder_runs_local_scan)
----------------------------------------------------------------------
Traceback (most recent call last):
AssertionError: '等待本地扫描结果回流' not found

----------------------------------------------------------------------
Ran 176 tests in 0.803s

FAILED (failures=1)
""".strip(),
            stderr="",
        )

        summary = _build_test_summary(result)

        self.assertEqual(summary["status"], "FAIL")
        self.assertEqual(summary["count"], 176)
        self.assertEqual(summary["first_failure"]["kind"], "FAIL")
        self.assertIn("test_load_universe_folder_runs_local_scan", summary["first_failure"]["name"])

    def test_render_summary_surfaces_first_failures_section(self) -> None:
        payload = {
            "full_tests": {
                "status": "FAIL",
                "count": 176,
                "first_failure": {
                    "kind": "FAIL",
                    "name": "test_load_universe_folder_runs_local_scan",
                    "summary": "AssertionError: expected loading copy",
                },
            },
            "compat_tests": {
                "status": "FAIL",
                "count": 98,
                "first_failure": {
                    "kind": "ERROR",
                    "name": "test_current_strategy_budget_bias_map_passes_execution_recap",
                    "summary": "KeyError: '龙头模型'",
                },
            },
            "perf": {"perf_regressions": []},
        }

        text = _render_summary(payload)

        self.assertIn("## First Failures", text)
        self.assertIn("3.13: FAIL `test_load_universe_folder_runs_local_scan`", text)
        self.assertIn("3.12: ERROR `test_current_strategy_budget_bias_map_passes_execution_recap`", text)


if __name__ == "__main__":
    unittest.main()
