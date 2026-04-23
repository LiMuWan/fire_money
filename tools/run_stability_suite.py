from __future__ import annotations

import ast
import importlib
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = ROOT / "docs"
TEST_FILE = ROOT / "tests" / "test_core.py"
PERF_BASELINE = DOCS_DIR / "perf_baseline_2026-04-15.json"
PERF_CURRENT = DOCS_DIR / "perf_current_latest.json"
PERF_REPORT = DOCS_DIR / "PERF_COMPARISON_latest.md"
SUMMARY_JSON = DOCS_DIR / "stability_suite_latest.json"
SUMMARY_MD = DOCS_DIR / "STABILITY_SUITE_LATEST.md"
PY313 = Path(r"C:\Users\18335\AppData\Local\Programs\Python\Python313\python.exe")
PY312 = Path(r"C:\Users\18335\AppData\Local\Programs\Python\Python312\python.exe")


@dataclass(frozen=True)
class CommandResult:
    name: str
    returncode: int
    stdout: str
    stderr: str


def _run(name: str, command: list[str]) -> CommandResult:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return CommandResult(
        name=name,
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def _compatibility_subset_command() -> str:
    source = TEST_FILE.read_text(encoding="utf-8-sig")
    module_ast = ast.parse(source)
    app_qt_tests: set[str] = set()
    for node in module_ast.body:
        if isinstance(node, ast.ClassDef) and node.name == "StrategyWorkflowTests":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name.startswith("test_"):
                    text = ast.get_source_segment(source, item) or ""
                    if 'import_module("app_qt")' in text or "import_module('app_qt')" in text or "import app_qt" in text:
                        app_qt_tests.add(item.name)
    excluded = sorted(app_qt_tests)
    return f"""
import importlib
import unittest

excluded = {excluded!r}
mod = importlib.import_module('tests.test_core')
case = mod.StrategyWorkflowTests
suite = unittest.TestSuite()
for name in sorted(n for n in dir(case) if n.startswith('test_') and n not in excluded):
    suite.addTest(case(name))
result = unittest.TextTestRunner(verbosity=1, failfast=True).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
""".strip()


def _extract_pass_count(output: str) -> int:
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("Ran ") and " tests" in line:
            try:
                return int(line.split()[1])
            except Exception:
                return 0
    return 0


def _extract_first_failure(output: str) -> dict[str, str] | None:
    text = str(output or "")
    for section in text.split("======================================================================"):
        lines = [line.rstrip() for line in section.splitlines()]
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            continue
        header = lines[0].strip()
        match = re.match(r"^(FAIL|ERROR):\s+(.+)$", header)
        if not match:
            continue
        kind = match.group(1)
        name = match.group(2).strip()
        summary = ""
        for raw_line in reversed(lines[1:]):
            stripped = raw_line.strip()
            if not stripped:
                continue
            if stripped.startswith("FAILED"):
                continue
            if stripped.startswith("OK"):
                continue
            if stripped.startswith("Ran "):
                continue
            if stripped.startswith("-" * 6):
                continue
            if stripped.startswith("Traceback"):
                continue
            if stripped.startswith("File "):
                continue
            if stripped.startswith("^"):
                continue
            if stripped.startswith("During handling of the above exception"):
                continue
            summary = stripped
            break
        return {
            "kind": kind,
            "name": name,
            "summary": summary or "See command output for traceback details.",
        }
    return None


def _build_test_summary(result: CommandResult) -> dict[str, Any]:
    output = result.stdout + "\n" + result.stderr
    summary: dict[str, Any] = {
        "status": "OK" if result.returncode == 0 else "FAIL",
        "count": _extract_pass_count(output),
    }
    first_failure = _extract_first_failure(output)
    if first_failure is not None:
        summary["first_failure"] = first_failure
    return summary


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _render_summary(payload: dict[str, Any]) -> str:
    lines = ["# Quant Hunter Stability Suite", ""]
    lines.extend(
        [
            "## Summary",
            "",
            f"- 3.13 full tests: {payload['full_tests']['count']} ({payload['full_tests']['status']})",
            f"- 3.12 compatibility subset: {payload['compat_tests']['count']} ({payload['compat_tests']['status']})",
            f"- Perf regressions: {len(payload['perf'].get('perf_regressions', []))}",
            "",
            "## First Failures",
            "",
        ]
    )
    full_failure = payload["full_tests"].get("first_failure")
    compat_failure = payload["compat_tests"].get("first_failure")
    if full_failure or compat_failure:
        if full_failure:
            lines.append(
                f"- 3.13: {full_failure['kind']} `{full_failure['name']}` -> {full_failure['summary']}"
            )
        if compat_failure:
            lines.append(
                f"- 3.12: {compat_failure['kind']} `{compat_failure['name']}` -> {compat_failure['summary']}"
            )
    else:
        lines.append("- None")
    lines.extend(
        [
            "",
            "## Outputs",
            "",
            f"- Perf current JSON: `{PERF_CURRENT.name}`",
            f"- Perf comparison report: `{PERF_REPORT.name}`",
            "",
        ]
    )
    if payload["perf"].get("perf_regressions"):
        lines.extend(["## Performance Alerts", ""])
        lines.extend(f"- {item}" for item in payload["perf"]["perf_regressions"])
    else:
        lines.extend(["## Performance Alerts", "", "- None"])
    return "\n".join(lines)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    full = _run(
        "full_tests",
        [str(PY313), "-u", "-m", "unittest", "tests.test_core", "-q"],
    )

    compat = _run(
        "compat_tests",
        [str(PY312), "-c", _compatibility_subset_command()],
    )

    perf = _run(
        "perf",
        [
            str(PY313),
            str(ROOT / "tools" / "perf_smoke.py"),
            "--files",
            "10",
            "50",
            "100",
            "200",
            "500",
            "--pipeline-repeats",
            "3",
            "--qt-iterations",
            "3",
            "--baseline",
            str(PERF_BASELINE),
            "--report-md",
            str(PERF_REPORT),
            "--save-json",
            str(PERF_CURRENT),
            "--json",
        ],
    )

    payload = {
        "full_tests": _build_test_summary(full),
        "compat_tests": _build_test_summary(compat),
        "perf": _load_json(PERF_CURRENT) if PERF_CURRENT.exists() else {},
        "commands": {
            "full_tests": asdict(full),
            "compat_tests": asdict(compat),
            "perf": asdict(perf),
        },
    }

    SUMMARY_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_MD.write_text(_render_summary(payload), encoding="utf-8")

    print(json.dumps(payload["full_tests"], ensure_ascii=False))
    print(json.dumps(payload["compat_tests"], ensure_ascii=False))
    print(f"perf_regressions={len(payload['perf'].get('perf_regressions', []))}")


if __name__ == "__main__":
    main()
