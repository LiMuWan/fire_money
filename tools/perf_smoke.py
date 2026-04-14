from __future__ import annotations

import argparse
import csv
import importlib
import importlib.util
import json
import os
import shutil
import sys
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "sample_data"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from quant_hunter.board import BoardModeEngine
from quant_hunter.decision import DecisionEngine
from quant_hunter.paper_trading import PaperTradingEngine, export_paper_trading_report
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review
from quant_hunter.scanner import UniverseScanner
from quant_hunter.strategy import StrategyParams
from quant_hunter.data import load_news_catalysts_from_csv, load_stock_profiles_from_csv, load_theme_aliases_from_csv
from quant_hunter.models import PaperTradingState
from tools.generate_sample_data import generate_rows


@dataclass(frozen=True)
class PerfSample:
    files: int
    scan_ms: float
    backtest_ms: float
    recommend_ms: float
    plan_ms: float
    board_ms: float
    export_ms: float
    paper_ms: float
    rows: int
    pool: int
    decisions: int


def _write_universe(root: Path, file_count: int) -> None:
    patterns = ("reclaim", "watch", "weak")
    for index in range(file_count):
        symbol = f"SHSE.{600100 + index:06d}"
        pattern = patterns[index % len(patterns)]
        path = root / f"{symbol}_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows(symbol, pattern))


def _measure_pipeline(file_count: int) -> PerfSample:
    temp_root = ROOT / "tests" / ".tmp" / f"perf_smoke_{file_count}_{uuid.uuid4().hex[:8]}"
    universe_dir = temp_root / "universe"
    export_dir = temp_root / "exports"
    try:
        universe_dir.mkdir(parents=True, exist_ok=True)
        export_dir.mkdir(parents=True, exist_ok=True)
        _write_universe(universe_dir, file_count)

        scanner = UniverseScanner(StrategyParams())
        builder = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(SAMPLE_DIR / "stock_profiles.csv"),
            news_map=load_news_catalysts_from_csv(SAMPLE_DIR / "news_catalysts.csv"),
            theme_aliases=load_theme_aliases_from_csv(SAMPLE_DIR / "theme_aliases.csv"),
        )

        start = perf_counter()
        rows, bars_by_symbol, analyses_by_symbol, _ = scanner.scan_folder(universe_dir)
        scan_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        summaries = scanner.summarize_backtests(bars_by_symbol, analyses_by_symbol)
        backtest_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        pool = builder.build(rows, analyses_by_symbol, summaries, top_n=max(10, file_count))
        recommend_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        trade_plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)
        plan_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        board_plan = BoardModeEngine().build(pool, top_n=5)
        board_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        export_daily_trade_plan(output_dir=export_dir, recommendations=pool, trade_plan=trade_plan, holdings=[])
        export_end_of_day_review(
            output_dir=export_dir,
            recommendations=pool,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=[],
            cash_snapshot=None,
            scan_rows=rows,
        )
        export_ms = (perf_counter() - start) * 1000.0

        start = perf_counter()
        paper_state = PaperTradingEngine().run_cycle(
            PaperTradingState(enabled=True, initial_cash=100000.0, cash=100000.0, max_position_pct=0.25),
            pool,
            as_of="2026-04-15 10:05:00",
        )
        export_paper_trading_report(paper_state, output_dir=export_dir, exported_at="2026-04-15 15:10:00")
        paper_ms = (perf_counter() - start) * 1000.0

        return PerfSample(
            files=file_count,
            scan_ms=round(scan_ms, 2),
            backtest_ms=round(backtest_ms, 2),
            recommend_ms=round(recommend_ms, 2),
            plan_ms=round(plan_ms, 2),
            board_ms=round(board_ms, 2),
            export_ms=round(export_ms, 2),
            paper_ms=round(paper_ms, 2),
            rows=len(rows),
            pool=len(pool),
            decisions=len(trade_plan.decisions),
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def _measure_qt_boot(iterations: int) -> dict[str, Any]:
    if importlib.util.find_spec("PySide6") is None:
        return {"available": False, "iterations": 0, "boot_ms": []}

    previous = os.environ.get("QT_QPA_PLATFORM")
    os.environ["QT_QPA_PLATFORM"] = previous or "offscreen"
    try:
        from PySide6.QtWidgets import QApplication

        module = importlib.import_module("app_qt")
        app = QApplication.instance() or QApplication([])
        samples: list[float] = []
        for _ in range(iterations):
            start = perf_counter()
            window = module.QuantHunterWindow()
            app.processEvents()
            samples.append(round((perf_counter() - start) * 1000.0, 2))
            window.close()
            app.processEvents()
        return {"available": True, "iterations": iterations, "boot_ms": samples}
    finally:
        if previous is None:
            os.environ.pop("QT_QPA_PLATFORM", None)
        else:
            os.environ["QT_QPA_PLATFORM"] = previous


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local performance smoke checks for the app pipeline.")
    parser.add_argument("--files", nargs="+", type=int, default=[10, 50, 100], help="Universe sizes to benchmark.")
    parser.add_argument("--qt-iterations", type=int, default=3, help="How many repeated Qt boot samples to capture.")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of plain text.")
    args = parser.parse_args()

    pipeline = [_measure_pipeline(file_count) for file_count in args.files]
    qt = _measure_qt_boot(args.qt_iterations)
    payload = {
        "pipeline": [asdict(item) for item in pipeline],
        "qt_boot": qt,
    }

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    print("Pipeline")
    for item in pipeline:
        print(
            f"files={item.files} scan={item.scan_ms}ms backtest={item.backtest_ms}ms "
            f"recommend={item.recommend_ms}ms plan={item.plan_ms}ms board={item.board_ms}ms "
            f"export={item.export_ms}ms paper={item.paper_ms}ms rows={item.rows} pool={item.pool} decisions={item.decisions}"
        )
    if qt["available"]:
        print("QtBoot")
        print("samples=" + ", ".join(f"{value}ms" for value in qt["boot_ms"]))
    else:
        print("QtBoot")
        print("unavailable")


if __name__ == "__main__":
    main()
