from __future__ import annotations

import ast
import csv
import importlib
import json
import os
import unittest
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import quant_hunter.broker as broker_module
import quant_hunter.broker_status as broker_status_module
import quant_hunter.license_policy as license_policy_module
import quant_hunter.recommend_status as recommend_status_module
import quant_hunter.ui_binders as ui_binders_module
import quant_hunter.ui_status as ui_status_module
from quant_hunter.ui_refresh import (
    build_dashboard_metrics_snapshot,
    build_detail_workspace_snapshot,
    build_market_text_snapshot,
    build_overview_command_snapshot,
    build_recommend_bucket_snapshot,
    build_recommend_dispatch_snapshot,
    build_recommend_review_snapshot,
    select_recommend_action_targets,
)
from quant_hunter.ui_helpers import one_day_hold_grade, one_day_hold_phase_labels, one_day_hold_tripwire_metrics, position_advice_check_item, tail_buy_execution_checklist, tail_buy_runtime_panel_lines, tail_buy_runtime_status, trade_decision_focus_lines, trade_plan_execution_hint
from quant_hunter.broker import (
    build_order_intent_from_trade_decision,
    EastmoneyBrokerAdapter,
    describe_order_intent,
    preview_position_changes,
    summarize_execution_statuses,
    summarize_trade_recap,
    summarize_broker_execution,
)
from quant_hunter.backtest import Backtester, BacktestParams
from quant_hunter.board import BoardModeEngine
from quant_hunter.decision import DecisionEngine
from quant_hunter.decision import TradeDecision
from quant_hunter.data import (
    aggregate_price_bars,
    load_bars_from_csv,
    load_news_catalysts_from_csv,
    load_stock_profiles_from_csv,
    load_theme_aliases_from_csv,
)
from quant_hunter.market_feed import EastmoneyMarketFeed, LocalMarketCache, MarketSnapshot, RemoteMarketScreener
from quant_hunter.models import BacktestResult, BrokerProfile, CashSnapshot, DailyAnalysis, HoldingRecord, PriceBar, RecommendationRow, ScanRow, SymbolBacktestSummary
from quant_hunter.models import OrderIntent
from quant_hunter.optimizer import ParameterOptimizer
from quant_hunter.paper_trading import (
    PaperTradingEngine,
    build_strategy_rotation_snapshot,
    export_paper_trading_report,
    should_auto_run_paper_trading,
    summarize_paper_trading_performance,
)
from quant_hunter.recommend import DailyPoolBuilder, _recommendation_sort_key
from quant_hunter.risk import (
    DEFAULT_RISK_CONTROLS,
    RISK_PROFILE_AGGRESSIVE,
    RISK_PROFILE_CONSERVATIVE,
    RISK_PROFILE_STANDARD,
    normalize_risk_profile,
    risk_profile_brief,
    resolve_risk_controls,
)
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review
from quant_hunter.scanner import UniverseScanner
from quant_hunter.storage import AppState, load_app_state, save_app_state
from quant_hunter.strategy import AntiHarvestStrategy, StrategyParams
from quant_hunter.theme import infer_mainline_flow_signal, infer_mainline_stage, summarize_themes, ThemeHeatEngine
from quant_hunter.models import PaperEquityPoint, PaperOrderRecord, PaperPatrolLog, PaperPosition, PaperTradingState
from tools.generate_sample_data import generate_rows


class StrategyWorkflowTests(unittest.TestCase):
    def _temp_dir(self) -> Path:
        output_dir = Path(__file__).resolve().parent / ".tmp"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def _write_demo_csv(self, filename: str) -> Path:
        path = self._temp_dir() / filename
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows())
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def test_csv_loader_and_strategy_generate_reclaim_signal(self) -> None:
        path = self._write_demo_csv("loader_demo.csv")
        bars = load_bars_from_csv(path)
        analyses = AntiHarvestStrategy(StrategyParams()).analyze(bars)
        labels = [item.label for item in analyses]

        self.assertIn("TRAP_DETECTED", labels)
        self.assertIn("RECLAIM_LONG", labels)

    def test_csv_loader_ignores_blank_rows(self) -> None:
        path = self._temp_dir() / "loader_blank_row.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerow(["2026-04-01", "SHSE.600000", "10", "10.5", "9.8", "10.2", "1000"])
            writer.writerow(["", "", "", "", "", "", ""])
            writer.writerow(["2026-04-02", "SHSE.600000", "10.2", "10.7", "10.0", "10.5", "1200"])
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        bars = load_bars_from_csv(path)

        self.assertEqual(len(bars), 2)
        self.assertEqual(bars[0].date, "2026-04-01")
        self.assertEqual(bars[1].date, "2026-04-02")

    def test_csv_loader_reports_row_and_field_for_invalid_numeric_value(self) -> None:
        path = self._temp_dir() / "loader_bad_number.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerow(["2026-04-01", "SHSE.600000", "10", "10.5", "9.8", "oops", "1000"])
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        with self.assertRaisesRegex(ValueError, r"loader_bad_number\.csv 第 2 行字段 close 不是有效数字"):
            load_bars_from_csv(path)

    def test_aggregate_price_bars_supports_weekly_and_monthly(self) -> None:
        bars = [
            PriceBar(date="2026-03-30", symbol="SHSE.600000", open=10.0, high=10.5, low=9.9, close=10.2, volume=1000),
            PriceBar(date="2026-03-31", symbol="SHSE.600000", open=10.2, high=10.8, low=10.1, close=10.6, volume=1200),
            PriceBar(date="2026-04-01", symbol="SHSE.600000", open=10.6, high=11.0, low=10.4, close=10.9, volume=1500),
            PriceBar(date="2026-04-15", symbol="SHSE.600000", open=11.0, high=11.6, low=10.8, close=11.3, volume=1800),
        ]

        weekly = aggregate_price_bars(bars, "weekly")
        monthly = aggregate_price_bars(bars, "monthly")

        self.assertGreaterEqual(len(weekly), 2)
        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly[0].date, "2026-03-31")
        self.assertEqual(monthly[0].open, 10.0)
        self.assertEqual(monthly[0].close, 10.6)
        self.assertEqual(monthly[0].high, 10.8)
        self.assertEqual(monthly[0].low, 9.9)
        self.assertEqual(monthly[0].volume, 2200)

    def test_backtest_produces_trade(self) -> None:
        path = self._write_demo_csv("backtest_demo.csv")
        bars = load_bars_from_csv(path)
        analyses = AntiHarvestStrategy(StrategyParams()).analyze(bars)
        result = Backtester().run(bars, analyses)

        self.assertGreaterEqual(len(result.trades), 1)
        self.assertGreater(result.ending_equity, 0)

    def test_backtest_skips_gap_entry_when_risk_reward_breaks(self) -> None:
        bars = [
            PriceBar(date="2026-04-01", symbol="SHSE.600000", open=10.0, high=10.3, low=9.9, close=10.1, volume=1000),
            PriceBar(date="2026-04-02", symbol="SHSE.600000", open=10.1, high=10.4, low=10.0, close=10.3, volume=1200),
            PriceBar(date="2026-04-03", symbol="SHSE.600000", open=11.1, high=11.4, low=10.9, close=11.2, volume=1500),
        ]
        analyses = [
            DailyAnalysis(
                date="2026-04-01",
                symbol="SHSE.600000",
                close=10.1,
                atr=0.3,
                ma_fast=10.0,
                ma_slow=9.9,
                breakout_level=10.0,
                volume_ratio=1.0,
                upper_shadow_pct=0.1,
                close_location=0.7,
                label="NONE",
                score=0,
                reason="",
            ),
            DailyAnalysis(
                date="2026-04-02",
                symbol="SHSE.600000",
                close=10.3,
                atr=0.35,
                ma_fast=10.1,
                ma_slow=10.0,
                breakout_level=10.1,
                volume_ratio=1.5,
                upper_shadow_pct=0.1,
                close_location=0.8,
                label="RECLAIM_LONG",
                score=88,
                reason="demo",
                entry_price=10.3,
                stop_price=9.8,
                target_price=11.3,
            ),
            DailyAnalysis(
                date="2026-04-03",
                symbol="SHSE.600000",
                close=11.2,
                atr=0.4,
                ma_fast=10.6,
                ma_slow=10.2,
                breakout_level=10.3,
                volume_ratio=1.2,
                upper_shadow_pct=0.1,
                close_location=0.7,
                label="NONE",
                score=0,
                reason="",
            ),
        ]

        result = Backtester(backtest_params=BacktestParams(min_entry_risk_reward_ratio=1.2)).run(bars, analyses)

        self.assertEqual(result.trades, [])
        self.assertEqual(result.ending_equity, 200000.0)

    def test_universe_scanner_finds_ranked_rows(self) -> None:
        sample_dir = self._temp_dir() / "universe"
        sample_dir.mkdir(exist_ok=True)
        files = {
            "SHSE.600000_demo.csv": generate_rows("SHSE.600000", "reclaim"),
            "SZSE.000001_demo.csv": generate_rows("SZSE.000001", "watch"),
            "SHSE.601398_demo.csv": generate_rows("SHSE.601398", "weak"),
        }
        for filename, rows in files.items():
            path = sample_dir / filename
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
                writer.writerows(rows)
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)

        self.assertEqual(len(bars_by_symbol), 3)
        self.assertEqual(rows[0].symbol, "SHSE.600000")
        self.assertEqual(rows[0].label, "RECLAIM_LONG")
        self.assertIn("SZSE.000001", analyses_by_symbol)

    def test_universe_scanner_skips_bad_csv_files_without_blocking_valid_ones(self) -> None:
        sample_dir = self._temp_dir() / "universe_mixed_quality"
        sample_dir.mkdir(exist_ok=True)
        valid_path = sample_dir / "SHSE.600000_demo.csv"
        with valid_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        bad_path = sample_dir / "BROKEN_demo.csv"
        with bad_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerow(["2026-04-01", "BROKEN", "10", "10.5", "9.8", "oops", "1000"])
        self.addCleanup(lambda: valid_path.unlink(missing_ok=True))
        self.addCleanup(lambda: bad_path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol = UniverseScanner(StrategyParams()).scan_folder(sample_dir)

        self.assertEqual(len(bars_by_symbol), 1)
        self.assertIn("SHSE.600000", bars_by_symbol)
        self.assertIn("SHSE.600000", analyses_by_symbol)
        self.assertIn("SHSE.600000", paths_by_symbol)
        self.assertNotIn("BROKEN", bars_by_symbol)
        self.assertEqual(rows[0].symbol, "SHSE.600000")

    def test_broker_export_creates_csv(self) -> None:
        row_path = self._write_demo_csv("order_demo.csv")
        bars = load_bars_from_csv(row_path)
        analyses = AntiHarvestStrategy(StrategyParams()).analyze(bars)
        signal = next(item for item in analyses if item.label == "RECLAIM_LONG")
        adapter = EastmoneyBrokerAdapter()
        orders = adapter.build_order_intents(
            [
                type("Row", (), {
                    "symbol": signal.symbol,
                    "label": signal.label,
                    "entry_price": signal.entry_price,
                    "stop_price": signal.stop_price,
                    "target_price": signal.target_price,
                    "signal_date": signal.date,
                    "reason": signal.reason,
                })()
            ],
            per_trade_budget=30000,
        )
        export_dir = self._temp_dir() / "exports"
        export_dir.mkdir(exist_ok=True)
        output = adapter.export_order_plan(orders, export_dir)
        self.addCleanup(lambda: output.unlink(missing_ok=True))

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)

    def test_broker_export_submission_records_creates_csv(self) -> None:
        adapter = EastmoneyBrokerAdapter()
        export_dir = self._temp_dir() / "submission_exports"
        export_dir.mkdir(exist_ok=True)
        output = adapter.export_submission_records(
            [
                {
                    "timestamp": "2026-04-04 22:10:00",
                    "order_status": "SUBMITTED",
                    "fill_status": "PENDING",
                    "symbol": "SHSE.600000",
                    "side": "BUY",
                    "price": "12.230",
                    "quantity": "2400",
                    "failure_reason": "",
                    "message": "submitted",
                }
            ],
            export_dir,
        )
        self.addCleanup(lambda: output.unlink(missing_ok=True))

        self.assertTrue(output.exists())
        self.assertGreater(output.stat().st_size, 0)
        with output.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.reader(handle))
        self.assertEqual(
            rows[0],
            [
                "timestamp",
                "order_status",
                "fill_status",
                "symbol",
                "side",
                "price",
                "quantity",
                "failure_reason",
                "message",
            ],
        )
        self.assertEqual(rows[1][1], "SUBMITTED")
        self.assertEqual(rows[1][2], "PENDING")

    def test_recommend_dispatch_snapshot_highlights_pending_and_failed_flow(self) -> None:
        rows = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.5,
                technical_score=82.0,
                position_score=78.0,
                persistence_score=76.0,
                news_score=72.0,
                leader_score=70.0,
                total_score=81.0,
                theme_name="金融",
                mainline_tag="金融",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_window_score=82.0,
                mainline_risk_flag="低",
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                catalyst="量价共振",
                rationale="主线回流",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="平安银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=12.0,
                entry_price=12.0,
                stop_price=11.4,
                target_price=13.2,
                technical_score=76.0,
                position_score=74.0,
                persistence_score=70.0,
                news_score=69.0,
                leader_score=68.0,
                total_score=75.0,
                theme_name="金融",
                mainline_tag="金融",
                mainline_rank=1,
                mainline_role="FRONT",
                mainline_window_score=76.0,
                mainline_risk_flag="低",
                primary_strategy="主力雷达",
                dragon_decision_score=79.0,
                catalyst="政策催化",
                rationale="趋势延续",
            ),
        ]
        snapshot = build_recommend_dispatch_snapshot(
            rows,
            SimpleNamespace(),
            {
                "SHSE.600000": "待观察",
                "SZSE.000001": "提交失败",
            },
            selected_row=rows[1],
        )

        self.assertIn("今日分发", snapshot["headline"])
        self.assertIn("继续跟", snapshot["headline"])
        self.assertIn("先复核 浦发银行", snapshot["headline"])
        self.assertIn("主线: 金融", snapshot["headline"])
        self.assertIn("总池 2", snapshot["headline"])
        self.assertIn("待复核 1", snapshot["headline"])
        self.assertIn("平安银行", snapshot["focus"])
        self.assertIn("提交失败", snapshot["focus"])
        self.assertIn("继续跟", snapshot["focus"])
        self.assertIn("主线/位次/角色", snapshot["focus"])
        self.assertIn("动作/状态", snapshot["focus"])
        self.assertIn("风险 低", snapshot["focus"])
        self.assertIn("执行队列概览", snapshot["queue"])
        self.assertIn("待复核", snapshot["queue"])
        self.assertIn("失败单 | 平安银行", snapshot["queue"])

    def test_recommend_review_snapshot_uses_brief_signal_card_format(self) -> None:
        rows = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.5,
                technical_score=82.0,
                position_score=78.0,
                persistence_score=76.0,
                news_score=72.0,
                leader_score=70.0,
                total_score=81.0,
                theme_name="金融",
                mainline_tag="金融",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_window_score=82.0,
                mainline_risk_flag="低",
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
            ),
            RecommendationRow(
                symbol="SZSE.300750",
                stock_id="300750",
                stock_name="宁德时代",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=180.0,
                entry_price=180.0,
                stop_price=172.0,
                target_price=198.0,
                technical_score=73.0,
                position_score=72.0,
                persistence_score=71.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=77.0,
                theme_name="新能源",
                mainline_tag="新能源",
                mainline_rank=2,
                mainline_role="FOLLOW",
                mainline_window_score=58.0,
                mainline_risk_flag="中",
                dragon_decision_score=83.0,
            ),
        ]

        snapshot = build_recommend_review_snapshot(
            rows,
            {
                "SHSE.600000": "待观察",
                "SZSE.300750": "提交失败",
            },
            [],
            SimpleNamespace(),
        )

        self.assertIn("当日执行复盘", snapshot["review"])
        self.assertIn("结论：送审 0 | 提交 0 | 失败 1", snapshot["review"])
        self.assertIn("风险：失败单 宁德时代", snapshot["review"])
        self.assertIn("下一步：当前执行链路稳定，可进入盘后复盘与策略归因。", snapshot["review"])
        self.assertIn("次日预案", snapshot["next_day"])
        self.assertIn("结论：继续跟 宁德时代 | 新能源 | 只观察", snapshot["next_day"])
        self.assertIn("风险：防切换 宁德时代 | 新能源 | 只观察", snapshot["next_day"])
        self.assertIn("下一步：只观察 浦发银行 | 金融 | 继续跟", snapshot["next_day"])

    def test_select_recommend_action_targets_prefers_highest_priority_rows(self) -> None:
        rows = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.5,
                technical_score=82.0,
                position_score=78.0,
                persistence_score=76.0,
                news_score=72.0,
                leader_score=70.0,
                total_score=81.0,
                theme_name="金融",
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="平安银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=12.0,
                entry_price=12.0,
                stop_price=11.2,
                target_price=13.4,
                technical_score=75.0,
                position_score=74.0,
                persistence_score=70.0,
                news_score=69.0,
                leader_score=68.0,
                total_score=75.0,
                theme_name="金融",
                primary_strategy="主力雷达",
                dragon_decision_score=79.0,
            ),
            RecommendationRow(
                symbol="SZSE.300750",
                stock_id="300750",
                stock_name="宁德时代",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=180.0,
                entry_price=180.0,
                stop_price=172.0,
                target_price=198.0,
                technical_score=73.0,
                position_score=72.0,
                persistence_score=71.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=77.0,
                theme_name="新能源",
                primary_strategy="主力雷达",
                dragon_decision_score=83.0,
            ),
        ]
        targets = select_recommend_action_targets(
            rows,
            {
                "SHSE.600000": "待观察",
                "SZSE.000001": "提交失败",
                "SZSE.300750": "已送审",
            },
        )

        self.assertEqual(targets["priority_buy"].symbol, "SHSE.600000")
        self.assertEqual(targets["failed_pick"].symbol, "SZSE.000001")
        self.assertEqual(targets["review_pick"].symbol, "SZSE.300750")
        self.assertEqual(targets["pending_review_count"], 1)
        self.assertEqual(targets["failed_count"], 1)
        self.assertEqual(targets["reviewing_count"], 1)

    def test_dashboard_metrics_snapshot_uses_mainline_window_for_top_theme(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=28.5,
                entry_price=28.5,
                stop_price=27.2,
                target_price=31.8,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="人工智能",
                mainline_tag="人工智能",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_window_score=86.0,
                dragon_decision_score=93.0,
            ),
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="银行跟随",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=10.2,
                entry_price=10.2,
                stop_price=9.8,
                target_price=11.0,
                technical_score=68.0,
                position_score=70.0,
                persistence_score=62.0,
                news_score=60.0,
                leader_score=64.0,
                total_score=67.0,
                theme_name="银行",
                mainline_tag="银行",
                mainline_rank=2,
                mainline_role="FOLLOW",
                mainline_window_score=44.0,
                dragon_decision_score=68.0,
            ),
        ]

        snapshot = build_dashboard_metrics_snapshot([], recommendations)

        self.assertEqual(snapshot["top_theme"][0], "人工智能")
        self.assertIn("继续跟", snapshot["top_theme"][1])
        self.assertIn("窗口 86.0", snapshot["top_theme"][1])

    def test_build_recommend_bucket_snapshot_splits_core_watch_and_risk(self) -> None:
        rows = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.5,
                technical_score=82.0,
                position_score=78.0,
                persistence_score=76.0,
                news_score=72.0,
                leader_score=70.0,
                total_score=81.0,
                theme_name="金融",
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                mainline_tag="金融",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                mainline_window_score=86.0,
            ),
            RecommendationRow(
                symbol="SZSE.300750",
                stock_id="300750",
                stock_name="宁德时代",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=180.0,
                entry_price=180.0,
                stop_price=172.0,
                target_price=198.0,
                technical_score=73.0,
                position_score=72.0,
                persistence_score=71.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=77.0,
                theme_name="新能源",
                primary_strategy="主力雷达",
                dragon_decision_score=83.0,
                mainline_tag="新能源",
                mainline_rank=2,
                mainline_role="FOLLOW",
                mainline_strength_score=64.0,
                mainline_continuation_score=58.0,
                theme_divergence_score=40.0,
                theme_failure_risk=42.0,
                mainline_window_score=64.0,
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="平安银行",
                action="REDUCE",
                label="REDUCE",
                signal_date="2026-04-06",
                close=12.0,
                entry_price=12.0,
                stop_price=11.2,
                target_price=13.4,
                technical_score=75.0,
                position_score=74.0,
                persistence_score=70.0,
                news_score=69.0,
                leader_score=68.0,
                total_score=75.0,
                theme_name="金融",
                primary_strategy="主力雷达",
                dragon_decision_score=79.0,
                mainline_tag="金融",
                mainline_rank=5,
                mainline_role="FOLLOW",
                mainline_strength_score=60.0,
                mainline_continuation_score=42.0,
                theme_divergence_score=62.0,
                theme_failure_risk=60.0,
                mainline_window_score=55.0,
            ),
        ]
        snapshot = build_recommend_bucket_snapshot(
            rows,
            {
                "SHSE.600000": "待观察",
                "SZSE.300750": "已送审",
                "SZSE.000001": "提交失败",
            },
        )

        self.assertIn("核心执行", snapshot["core"])
        self.assertIn("继续跟", snapshot["core"])
        self.assertIn("浦发银行", snapshot["core"])
        self.assertIn("观察跟踪", snapshot["watch"])
        self.assertIn("只观察", snapshot["watch"])
        self.assertIn("宁德时代", snapshot["watch"])
        self.assertIn("风险回避", snapshot["risk"])
        self.assertIn("防切换", snapshot["risk"])
        self.assertIn("平安银行", snapshot["risk"])

    def test_build_recommend_review_snapshot_summarizes_recap_and_next_day(self) -> None:
        rows = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.5,
                technical_score=82.0,
                position_score=78.0,
                persistence_score=76.0,
                news_score=72.0,
                leader_score=70.0,
                total_score=81.0,
                theme_name="金融",
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                mainline_tag="金融",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                mainline_window_score=86.0,
            ),
            RecommendationRow(
                symbol="SZSE.300750",
                stock_id="300750",
                stock_name="宁德时代",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=180.0,
                entry_price=180.0,
                stop_price=172.0,
                target_price=198.0,
                technical_score=73.0,
                position_score=72.0,
                persistence_score=71.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=77.0,
                theme_name="新能源",
                primary_strategy="主力雷达",
                dragon_decision_score=83.0,
                mainline_tag="新能源",
                mainline_rank=2,
                mainline_role="FOLLOW",
                mainline_strength_score=64.0,
                mainline_continuation_score=58.0,
                theme_divergence_score=40.0,
                theme_failure_risk=42.0,
                mainline_window_score=64.0,
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="平安银行",
                action="REDUCE",
                label="REDUCE",
                signal_date="2026-04-06",
                close=12.0,
                entry_price=12.0,
                stop_price=11.2,
                target_price=13.4,
                technical_score=75.0,
                position_score=74.0,
                persistence_score=70.0,
                news_score=69.0,
                leader_score=68.0,
                total_score=75.0,
                theme_name="金融",
                primary_strategy="主力雷达",
                dragon_decision_score=79.0,
                mainline_tag="金融",
                mainline_rank=5,
                mainline_role="FOLLOW",
                mainline_strength_score=60.0,
                mainline_continuation_score=42.0,
                theme_divergence_score=62.0,
                theme_failure_risk=60.0,
                mainline_window_score=55.0,
            ),
        ]
        submission_records = [
            {
                "timestamp": "2026-04-06 10:11:00",
                "order_status": "SUBMITTED",
                "fill_status": "PENDING",
                "symbol": "SHSE.600000",
                "side": "BUY",
                "price": "10.00",
                "quantity": "1000",
                "failure_reason": "",
                "message": "submitted",
            },
            {
                "timestamp": "2026-04-06 10:15:00",
                "order_status": "FAILED",
                "fill_status": "REJECTED",
                "symbol": "SZSE.000001",
                "side": "SELL",
                "price": "12.00",
                "quantity": "800",
                "failure_reason": "risk",
                "message": "rejected",
            },
        ]
        plan = SimpleNamespace(decisions=[SimpleNamespace(symbol="SHSE.600000"), SimpleNamespace(symbol="SZSE.000001")])
        snapshot = build_recommend_review_snapshot(
            rows,
            {
                "SHSE.600000": "已提交",
                "SZSE.000001": "提交失败",
                "SZSE.300750": "已送审",
            },
            submission_records,
            plan,
        )

        self.assertIn("当日执行复盘", snapshot["review"])
        self.assertIn("提交 1", snapshot["review"])
        self.assertIn("失败 1", snapshot["review"])
        self.assertIn("次日预案", snapshot["next_day"])
        self.assertIn("继续跟", snapshot["next_day"])
        self.assertIn("只观察", snapshot["next_day"])
        self.assertIn("防切换", snapshot["next_day"])
        self.assertIn("宁德时代", snapshot["next_day"])
        self.assertIn("平安银行", snapshot["next_day"])

    def test_build_detail_workspace_snapshot_covers_decision_execution_and_conclusion(self) -> None:
        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.5,
            target_price=11.5,
            technical_score=82.0,
            position_score=78.0,
            persistence_score=76.0,
            news_score=72.0,
            leader_score=70.0,
            total_score=81.0,
            theme_name="金融",
            primary_strategy="掘龙决策",
            dragon_decision_score=88.0,
            catalyst="量价共振",
            rationale="主线回流",
        )
        latest_signal = SimpleNamespace(
            date="2026-04-06",
            label="RECLAIM_LONG",
            score=88,
            reason="缩量回踩后重新转强",
        )
        backtest_result = SimpleNamespace(
            trades=[1, 2, 3],
            total_return=0.18,
            win_rate=0.67,
            max_drawdown=0.08,
        )
        order_intent = SimpleNamespace(side="BUY", quantity=1000, price=10.0)
        snapshot = build_detail_workspace_snapshot(
            symbol="SHSE.600000",
            recommendation=recommendation,
            execution_status="已送审",
            submission_records=[
                {
                    "timestamp": "2026-04-06 10:11:00",
                    "order_status": "SUBMITTED",
                    "fill_status": "PENDING",
                    "symbol": "SHSE.600000",
                    "message": "submitted",
                    "failure_reason": "",
                }
            ],
            latest_signal=latest_signal,
            backtest_result=backtest_result,
            source_path="sample.csv",
            order_intent=order_intent,
        )

        self.assertIn("交易决策画像", snapshot["decision"])
        self.assertIn("浦发银行", snapshot["decision"])
        self.assertIn("已送审", snapshot["execution"])
        self.assertIn("submitted", snapshot["execution"])
        self.assertIn("复盘结论", snapshot["conclusion"])
        self.assertIn("回测表现", snapshot["conclusion"])

    def test_broker_execution_summary_marks_sdk_blockers_and_risk(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="sdk",
                export_dir="exports",
                account_id="demo-account",
                token="",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=12.0,
                    quantity=3000,
                    stop_price=11.4,
                    target_price=13.2,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=30000.0, total_assets=80000.0),
        )

        self.assertEqual(summary["readiness"], "待补齐")
        self.assertIn("缺少 SDK Token", summary["blockers"])
        self.assertIn("SDK 环境未就绪", summary["blockers"])
        self.assertIn("预计委托金额超过可用资金", summary["blockers"])
        self.assertGreater(summary["estimated_loss"], 0.0)
        self.assertAlmostEqual(summary["risk_reward_ratio"], 2.0, places=2)

    def test_broker_execution_summary_marks_export_mode_ready(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.5,
                    target_price=11.0,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600000",
                    quantity=1000,
                    available=1000,
                    cost_price=9.8,
                    market_value=10000.0,
                )
            ],
            cash_snapshot=CashSnapshot(available_cash=20000.0, total_assets=60000.0),
        )

        self.assertEqual(summary["readiness"], "可导出执行")
        self.assertEqual(summary["risk_profile"], "standard")
        self.assertFalse(summary["blockers"])
        self.assertIn("当前为导出模式，下单前仍需人工导入券商终端", summary["warnings"])
        self.assertEqual(summary["side_counts"]["BUY"], 1)
        self.assertAlmostEqual(summary["capital_usage_ratio"], 0.5, places=2)

    def test_broker_execution_summary_blocks_non_mainline_buy(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.5,
                    target_price=11.0,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=20000.0, total_assets=60000.0),
            recommendations=[
                RecommendationRow(
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="浦发银行",
                    action="BUY",
                    label="RECLAIM_LONG",
                    signal_date="2026-04-06",
                    close=10.0,
                    entry_price=10.0,
                    stop_price=9.5,
                    target_price=11.0,
                    technical_score=72.0,
                    position_score=66.0,
                    persistence_score=64.0,
                    news_score=58.0,
                    leader_score=55.0,
                    total_score=66.0,
                    theme_name="银行",
                    mainline_tag="银行",
                    mainline_rank=5,
                    mainline_role="NOISE",
                    mainline_window_score=42.0,
                    theme_failure_risk=74.0,
                    mainline_risk_flag="高",
                    primary_strategy="价值低吸",
                    dragon_decision_score=68.0,
                )
            ],
        )

        self.assertEqual(summary["mainline_review"]["status"], "拦截")
        self.assertTrue(any("主线审查" in item for item in summary["blockers"]))
        self.assertIn("主线闸门", " | ".join(summary["blockers"]))

    def test_broker_execution_summary_passes_core_mainline_buy(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SZSE.300024",
                    side="BUY",
                    price=28.5,
                    quantity=500,
                    stop_price=27.2,
                    target_price=31.8,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=30000.0, total_assets=80000.0),
            recommendations=[
                RecommendationRow(
                    symbol="SZSE.300024",
                    stock_id="300024",
                    stock_name="机器人核心",
                    action="BUY",
                    label="RECLAIM_LONG",
                    signal_date="2026-04-06",
                    close=28.5,
                    entry_price=28.5,
                    stop_price=27.2,
                    target_price=31.8,
                    technical_score=90.0,
                    position_score=84.0,
                    persistence_score=88.0,
                    news_score=82.0,
                    leader_score=92.0,
                    total_score=91.0,
                    theme_name="人工智能",
                    mainline_tag="人工智能",
                    mainline_rank=1,
                    mainline_role="CORE",
                    mainline_window_score=86.0,
                    theme_failure_risk=24.0,
                    mainline_risk_flag="低",
                    primary_strategy="龙头模型",
                    dragon_decision_score=93.0,
                )
            ],
        )

        self.assertEqual(summary["mainline_review"]["status"], "通过")
        self.assertFalse(summary["mainline_review"]["blockers"])
        self.assertEqual(summary["mainline_review"]["pass_count"], 1)

    def test_broker_execution_summary_blocks_oversell_order(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600001",
                    side="SELL",
                    price=8.6,
                    quantity=900,
                    stop_price=8.0,
                    target_price=9.0,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600001",
                    quantity=800,
                    available=500,
                    cost_price=8.5,
                    market_value=6800.0,
                )
            ],
            cash_snapshot=CashSnapshot(available_cash=20000.0, total_assets=60000.0),
        )

        self.assertTrue(any("\u53ef\u5356\u6570\u91cf\u4e0d\u8db3" in item for item in summary["blockers"]))
        self.assertEqual(summary["estimated_capital"], 0.0)
        self.assertEqual(summary["capital_usage_ratio"], 0.0)

    def test_broker_execution_summary_blocks_over_concentrated_buy(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600010",
                    side="BUY",
                    price=10.0,
                    quantity=3000,
                    stop_price=9.5,
                    target_price=11.2,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=35000.0, total_assets=80000.0),
        )

        self.assertEqual(summary["portfolio_risk_review"]["status_code"], "BLOCKED")
        self.assertTrue(any("资金占用过高" in item for item in summary["blockers"]))
        self.assertEqual(summary["portfolio_risk_review"]["rows"][0]["status_code"], "BLOCKED")

    def test_broker_execution_summary_warns_when_total_loss_budget_is_high(self) -> None:
        summary = summarize_broker_execution(
            profile=BrokerProfile(
                mode="export",
                export_dir="exports",
            ),
            env={
                "direct_ready": False,
                "bridge_ready": False,
            },
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1200,
                    stop_price=9.4,
                    target_price=11.2,
                    signal_date="2026-04-06",
                    reason="demo-a",
                ),
                broker_module.OrderIntent(
                    symbol="SZSE.000001",
                    side="BUY",
                    price=8.0,
                    quantity=1200,
                    stop_price=7.5,
                    target_price=8.9,
                    signal_date="2026-04-06",
                    reason="demo-b",
                ),
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=50000.0),
        )

        self.assertEqual(summary["portfolio_risk_review"]["status_code"], "CAUTION")
        self.assertGreater(summary["portfolio_risk_review"]["total_loss_ratio"], 0.02)
        self.assertTrue(any("组合预估止损亏损占总资产约" in item for item in summary["warnings"]))

    def test_broker_execution_summary_risk_profile_changes_portfolio_gate(self) -> None:
        kwargs = dict(
            profile=BrokerProfile(mode="export", export_dir="exports"),
            env={"direct_ready": False, "bridge_ready": False},
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.1,
                    target_price=11.2,
                    signal_date="2026-04-06",
                    reason="demo-a",
                )
            ],
            holdings=[],
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=50000.0),
        )

        conservative = summarize_broker_execution(risk_profile="conservative", **kwargs)
        aggressive = summarize_broker_execution(risk_profile="aggressive", **kwargs)

        self.assertEqual(conservative["portfolio_risk_review"]["status_code"], "BLOCKED")
        self.assertEqual(aggressive["portfolio_risk_review"]["status_code"], "CAUTION")

    def test_describe_order_intent_returns_priority_and_checks(self) -> None:
        detail = describe_order_intent(
            broker_module.OrderIntent(
                symbol="SHSE.600000",
                side="BUY",
                price=10.0,
                quantity=1000,
                stop_price=9.5,
                target_price=11.5,
                signal_date="2026-04-06",
                reason="主线回流，量价结构修复，适合做低吸回补。",
            ),
            available_cash=30000.0,
        )

        self.assertEqual(detail["priority"], "A")
        self.assertEqual(detail["check_label"], "通过")
        self.assertAlmostEqual(detail["capital_ratio"], 1 / 3, places=2)
        self.assertIn("主线回流", detail["reason_summary"])

        risky = describe_order_intent(
            broker_module.OrderIntent(
                symbol="SHSE.600001",
                side="BUY",
                price=10.0,
                quantity=4000,
                stop_price=10.2,
                target_price=10.4,
                signal_date="2026-04-06",
                reason="risk",
            ),
            available_cash=20000.0,
        )
        self.assertEqual(risky["priority"], "C")
        self.assertIn("止损价偏高", risky["check_label"])

    def test_describe_order_intent_risk_profile_changes_priority(self) -> None:
        item = broker_module.OrderIntent(
            symbol="SHSE.600000",
            side="BUY",
            price=10.0,
            quantity=1000,
            stop_price=9.5,
            target_price=10.7,
            signal_date="2026-04-06",
            reason="demo",
        )

        conservative = describe_order_intent(item, available_cash=50000.0, risk_profile="conservative")
        aggressive = describe_order_intent(item, available_cash=50000.0, risk_profile="aggressive")

        self.assertEqual(conservative["priority"], "C")
        self.assertEqual(aggressive["priority"], "B")

    def test_preview_position_changes_summarizes_holdings_transition(self) -> None:
        preview = preview_position_changes(
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600000",
                    quantity=1000,
                    available=1000,
                    cost_price=9.8,
                    market_value=10000.0,
                ),
                HoldingRecord(
                    symbol="SHSE.600001",
                    quantity=800,
                    available=800,
                    cost_price=8.5,
                    market_value=6800.0,
                ),
            ],
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=500,
                    stop_price=9.4,
                    target_price=11.2,
                    signal_date="2026-04-06",
                    reason="demo",
                ),
                broker_module.OrderIntent(
                    symbol="SHSE.600001",
                    side="SELL",
                    price=8.6,
                    quantity=800,
                    stop_price=8.0,
                    target_price=9.0,
                    signal_date="2026-04-06",
                    reason="demo",
                ),
                broker_module.OrderIntent(
                    symbol="SHSE.600002",
                    side="BUY",
                    price=12.0,
                    quantity=600,
                    stop_price=11.2,
                    target_price=13.8,
                    signal_date="2026-04-06",
                    reason="demo",
                ),
            ],
        )

        rows = {item["symbol"]: item for item in preview["rows"]}
        self.assertEqual(rows["SHSE.600000"]["status"], "加仓")
        self.assertEqual(rows["SHSE.600001"]["status"], "清仓")
        self.assertEqual(rows["SHSE.600002"]["status"], "新增")
        self.assertEqual(preview["new_symbol_count"], 1)
        self.assertEqual(preview["exit_symbol_count"], 1)

    def test_preview_position_changes_marks_oversell(self) -> None:
        preview = preview_position_changes(
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600003",
                    quantity=500,
                    available=200,
                    cost_price=7.5,
                    market_value=3750.0,
                )
            ],
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600003",
                    side="SELL",
                    price=7.6,
                    quantity=400,
                    stop_price=7.2,
                    target_price=8.0,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
        )

        rows = {item["symbol"]: item for item in preview["rows"]}
        self.assertEqual(rows["SHSE.600003"]["status"], "\u8d85\u5356")
        self.assertTrue(rows["SHSE.600003"]["oversell"])
        self.assertEqual(preview["oversell_count"], 1)
        self.assertIn("SHSE.600003", preview["high_risk_symbols"])

    def test_summarize_trade_recap_counts_execution_and_flags(self) -> None:
        recap = summarize_trade_recap(
            submission_records=[
                {
                    "timestamp": "2026-04-06 09:31:00",
                    "order_status": "SUBMITTED",
                    "fill_status": "PENDING",
                    "symbol": "SHSE.600000",
                    "side": "BUY",
                    "price": "10.00",
                    "quantity": "1000",
                    "failure_reason": "",
                    "message": "submitted",
                },
                {
                    "timestamp": "2026-04-06 09:32:00",
                    "order_status": "FAILED",
                    "fill_status": "REJECTED",
                    "symbol": "SHSE.600001",
                    "side": "SELL",
                    "price": "8.50",
                    "quantity": "800",
                    "failure_reason": "risk",
                    "message": "rejected",
                },
            ],
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600000",
                    quantity=1000,
                    available=1000,
                    cost_price=9.8,
                    market_value=10000.0,
                )
            ],
            order_intents=[
                broker_module.OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.5,
                    target_price=11.0,
                    signal_date="2026-04-06",
                    reason="demo",
                )
            ],
            order_log=[
                "[2026-04-06 09:31:00] SHSE.600000 BUY 1000 @ 10.0: submitted",
                "[2026-04-06 09:32:00] SHSE.600001 SELL 800 @ 8.5: rejected",
            ],
        )

        self.assertEqual(recap["submitted_count"], 1)
        self.assertEqual(recap["failed_count"], 1)
        self.assertEqual(recap["pending_count"], 1)
        self.assertEqual(recap["rejected_count"], 1)
        self.assertAlmostEqual(recap["executed_capital"], 16800.0, places=2)
        self.assertIn("SHSE.600000", recap["focus_symbols"])
        self.assertTrue(any("失败" in item or "拒绝" in item for item in recap["review_flags"]))

    def test_build_order_intent_from_trade_decision_uses_budget_and_lot_size(self) -> None:
        intent = build_order_intent_from_trade_decision(
            TradeDecision(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                confidence=0.82,
                planned_entry=10.0,
                planned_stop=9.5,
                planned_target=11.2,
                suggested_budget=25600.0,
                rationale="demo",
            )
        )
        self.assertIsNotNone(intent)
        assert intent is not None
        self.assertEqual(intent.quantity, 2500)
        self.assertEqual(intent.side, "BUY")
        self.assertEqual(intent.signal_date, "计划股")

        skipped = build_order_intent_from_trade_decision(
            TradeDecision(
                symbol="SHSE.600001",
                stock_id="600001",
                stock_name="示例股票",
                action="WATCH",
                confidence=0.4,
                planned_entry=10.0,
                planned_stop=9.5,
                planned_target=10.8,
                suggested_budget=10000.0,
                rationale="skip",
            )
        )
        self.assertIsNone(skipped)

        low_rr = build_order_intent_from_trade_decision(
            TradeDecision(
                symbol="SHSE.600002",
                stock_id="600002",
                stock_name="低盈亏比示例",
                action="BUY",
                confidence=0.7,
                planned_entry=10.0,
                planned_stop=9.6,
                planned_target=10.2,
                suggested_budget=10000.0,
                rationale="skip low rr",
            )
        )
        self.assertIsNone(low_rr)

    def test_summarize_execution_statuses_counts_pipeline_states(self) -> None:
        summary = summarize_execution_statuses(
            ["SHSE.600000", "SHSE.600001", "SHSE.600002", "SHSE.600003"],
            {
                "SHSE.600000": "已送审",
                "SHSE.600001": "已提交",
                "SHSE.600002": "提交失败",
            },
        )
        self.assertEqual(summary["total"], 4)
        self.assertEqual(summary["reviewing"], 1)
        self.assertEqual(summary["submitted"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["pending"], 1)

    def test_stock_profile_and_news_loaders_support_daily_pool(self) -> None:
        temp_dir = self._temp_dir()
        profile_path = temp_dir / "profiles.csv"
        news_path = temp_dir / "news.csv"
        profile_path.write_text(
            "symbol,name,industry,is_leader\nSHSE.600000,浦发银行,银行,1\n",
            encoding="utf-8-sig",
        )
        news_path.write_text(
            "symbol,title,summary,published_at,sentiment_score,heat\n"
            "SHSE.600000,资金回流银行,板块修复,2026-02-25,1.1,1.2\n",
            encoding="utf-8-sig",
        )
        self.addCleanup(lambda: profile_path.unlink(missing_ok=True))
        self.addCleanup(lambda: news_path.unlink(missing_ok=True))

        profiles = load_stock_profiles_from_csv(profile_path)
        news_map = load_news_catalysts_from_csv(news_path)

        self.assertEqual(profiles["SHSE.600000"].name, "浦发银行")
        self.assertTrue(profiles["SHSE.600000"].is_leader)
        self.assertEqual(news_map["SHSE.600000"][0].title, "资金回流银行")

    def test_daily_pool_builder_ranks_reclaim_candidate(self) -> None:
        sample_dir = self._temp_dir() / "daily_pool_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        builder = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        )
        pool = builder.build(rows, analyses_by_symbol, summaries, top_n=5)

        self.assertGreaterEqual(len(pool), 1)
        self.assertEqual(pool[0].stock_name, "浦发银行")
        self.assertEqual(pool[0].stock_id, "600000")
        self.assertGreater(pool[0].total_score, 70)
        self.assertTrue(pool[0].theme_name)
        self.assertGreaterEqual(pool[0].theme_score, 0)

    def test_decision_engine_builds_up_to_five_candidates(self) -> None:
        sample_dir = self._temp_dir() / "decision_universe"
        sample_dir.mkdir(exist_ok=True)
        for index in range(5):
            path = sample_dir / f"SHSE.60000{index}_demo.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
                writer.writerows(generate_rows(f"SHSE.60000{index}", "reclaim"))
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        builder = DailyPoolBuilder(theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")))
        pool = builder.build(rows, analyses_by_symbol, summaries, top_n=5)
        plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)

        self.assertLessEqual(len(plan.decisions), 5)
        self.assertTrue(all(item.action == "BUY" for item in plan.decisions))
        self.assertIn(plan.market_pulse.market_regime, {"主升", "修复", "分歧", "退潮", "冰点观察"})
        self.assertIn(plan.market_pulse.risk_level, {"低", "中", "高"})
        self.assertGreaterEqual(plan.market_pulse.max_total_exposure, 0.0)

    def test_decision_engine_generates_position_advice(self) -> None:
        sample_dir = self._temp_dir() / "position_advice_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        builder = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        )
        pool = builder.build(rows, analyses_by_symbol, summaries, top_n=5)
        holdings = [
            HoldingRecord(
                symbol="SHSE.600000",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=12300.0,
            )
        ]

        plan = DecisionEngine().build_plan(pool, holdings, available_cash=50000, max_picks=5)

        self.assertEqual(len(plan.position_advice), 1)
        self.assertIn(plan.position_advice[0].action, {"HOLD", "REDUCE", "SELL", "WATCH"})

    def test_decision_engine_uses_strategy_specific_targets(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Board Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=0.0,
                target_price=0.0,
                technical_score=80.0,
                position_score=78.0,
                persistence_score=82.0,
                news_score=76.0,
                leader_score=85.0,
                total_score=83.0,
                theme_name="机器人",
                theme_rank=1,
                primary_strategy="擒龙打板",
                dragon_decision_score=90.0,
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="Value Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=0.0,
                target_price=0.0,
                technical_score=75.0,
                position_score=84.0,
                persistence_score=74.0,
                news_score=68.0,
                leader_score=72.0,
                total_score=79.0,
                theme_name="银行",
                theme_rank=2,
                primary_strategy="价值低吸",
                dragon_decision_score=82.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 2)
        board_pick = next(item for item in plan.decisions if item.stock_id == "600000")
        value_pick = next(item for item in plan.decisions if item.stock_id == "000001")
        self.assertAlmostEqual(board_pick.planned_stop, 9.65, places=2)
        self.assertAlmostEqual(board_pick.planned_target, 11.3, places=2)
        self.assertAlmostEqual(value_pick.planned_stop, 9.45, places=2)
        self.assertAlmostEqual(value_pick.planned_target, 10.9, places=2)

    def test_decision_engine_filters_trade_with_wide_stop_loss(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="稳健样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=82.0,
                position_score=80.0,
                persistence_score=76.0,
                news_score=70.0,
                leader_score=78.0,
                total_score=84.0,
                theme_name="银行",
                theme_rank=1,
                dragon_decision_score=88.0,
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="宽止损样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.0,
                target_price=11.4,
                technical_score=80.0,
                position_score=78.0,
                persistence_score=75.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=83.0,
                theme_name="银行",
                theme_rank=1,
                dragon_decision_score=87.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertEqual(plan.decisions[0].stock_id, "600000")
        self.assertTrue(any("计划风险结构过滤" in note or "过滤" in note for note in plan.notes))

    def test_decision_engine_computes_risk_reward_ratio_when_row_missing(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.0,
                technical_score=82.0,
                position_score=84.0,
                persistence_score=80.0,
                news_score=76.0,
                leader_score=78.0,
                total_score=83.0,
                theme_name="银行",
                theme_rank=1,
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                risk_reward_ratio=0.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertAlmostEqual(plan.decisions[0].risk_reward_ratio, 2.0, places=2)

    def test_decision_engine_applies_risk_profile_thresholds(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="档位样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=10.7,
                technical_score=82.0,
                position_score=84.0,
                persistence_score=80.0,
                news_score=76.0,
                leader_score=78.0,
                total_score=83.0,
                theme_name="银行",
                theme_rank=1,
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                risk_reward_ratio=1.4,
            ),
        ]

        standard_plan = DecisionEngine(risk_profile="standard").build_plan(recommendations, [], available_cash=100000, max_picks=5)
        conservative_plan = DecisionEngine(risk_profile="conservative").build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(standard_plan.decisions), 1)
        self.assertEqual(len(conservative_plan.decisions), 0)

    def test_decision_engine_risk_profile_changes_suggested_budget(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="仓位档位样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date=date.today().isoformat(),
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=76.0,
                leader_score=82.0,
                total_score=84.0,
                theme_name="银行",
                theme_rank=1,
                primary_strategy="掘龙决策",
                dragon_decision_score=88.0,
                risk_reward_ratio=2.4,
                opportunity_tier="优先处理",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="仓位档位对照",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date=date.today().isoformat(),
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=82.0,
                position_score=80.0,
                persistence_score=78.0,
                news_score=74.0,
                leader_score=80.0,
                total_score=82.0,
                theme_name="银行",
                theme_rank=1,
                primary_strategy="掘龙决策",
                dragon_decision_score=86.0,
                risk_reward_ratio=2.4,
                opportunity_tier="优先处理",
            ),
        ]

        conservative_plan = DecisionEngine(risk_profile="conservative").build_plan(recommendations, [], available_cash=100000, max_picks=5)
        standard_plan = DecisionEngine(risk_profile="standard").build_plan(recommendations, [], available_cash=100000, max_picks=5)
        aggressive_plan = DecisionEngine(risk_profile="aggressive").build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(conservative_plan.decisions), 2)
        self.assertEqual(len(standard_plan.decisions), 2)
        self.assertEqual(len(aggressive_plan.decisions), 2)
        self.assertLess(conservative_plan.decisions[0].suggested_budget, standard_plan.decisions[0].suggested_budget)
        self.assertLess(standard_plan.decisions[0].suggested_budget, aggressive_plan.decisions[0].suggested_budget)

    def test_shared_risk_controls_keep_core_thresholds_aligned(self) -> None:
        self.assertAlmostEqual(DEFAULT_RISK_CONTROLS.backtest_min_entry_risk_reward_ratio, 1.2, places=2)
        self.assertAlmostEqual(DEFAULT_RISK_CONTROLS.plan_min_risk_reward_ratio, 1.2, places=2)
        self.assertAlmostEqual(DEFAULT_RISK_CONTROLS.recommendation_min_risk_reward_ratio, 1.35, places=2)
        self.assertAlmostEqual(DEFAULT_RISK_CONTROLS.execution_low_risk_reward_ratio, 1.35, places=2)
        self.assertAlmostEqual(DEFAULT_RISK_CONTROLS.max_plan_stop_loss_pct, 0.08, places=2)

    def test_risk_profile_resolution_supports_named_presets(self) -> None:
        self.assertEqual(normalize_risk_profile("保守"), RISK_PROFILE_CONSERVATIVE)
        self.assertEqual(normalize_risk_profile("激进"), RISK_PROFILE_AGGRESSIVE)
        self.assertEqual(normalize_risk_profile("balanced"), RISK_PROFILE_STANDARD)

        conservative = resolve_risk_controls("conservative")
        standard = resolve_risk_controls("standard")
        aggressive = resolve_risk_controls("aggressive")

        self.assertGreater(conservative.plan_min_risk_reward_ratio, standard.plan_min_risk_reward_ratio)
        self.assertLess(aggressive.plan_min_risk_reward_ratio, standard.plan_min_risk_reward_ratio)
        self.assertLess(conservative.max_plan_stop_loss_pct, standard.max_plan_stop_loss_pct)
        self.assertGreater(aggressive.max_plan_stop_loss_pct, standard.max_plan_stop_loss_pct)

    def test_risk_profile_brief_returns_human_readable_summary(self) -> None:
        self.assertIn("盈亏比", risk_profile_brief("conservative"))
        self.assertIn("均衡", risk_profile_brief("standard"))
        self.assertIn("放宽", risk_profile_brief("aggressive"))

    def test_board_mode_engine_builds_candidates(self) -> None:
        sample_dir = self._temp_dir() / "board_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=5)
        plan = BoardModeEngine().build(pool, top_n=5)

        self.assertGreaterEqual(len(plan.candidates), 1)
        self.assertIn(plan.temperature, {"可积极尝试", "轻仓参与", "只做观察", "暂不出手"})

    def test_optimizer_returns_ranked_results(self) -> None:
        sample_dir = self._temp_dir() / "optimizer_universe"
        sample_dir.mkdir(exist_ok=True)
        files = {
            "SHSE.600000_demo.csv": generate_rows("SHSE.600000", "reclaim"),
            "SZSE.000001_demo.csv": generate_rows("SZSE.000001", "watch"),
        }
        for filename, rows in files.items():
            path = sample_dir / filename
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
                writer.writerows(rows)
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))
        _, bars_by_symbol, _, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        results = ParameterOptimizer(StrategyParams()).optimize(
            bars_by_symbol,
            grid={"breakout_lookback": [15, 20], "min_volume_ratio": [1.6, 1.8]},
            top_n=3,
        )

        self.assertEqual(results[0].rank, 1)
        self.assertLessEqual(len(results), 3)
        self.assertTrue(all(result.symbols_tested == 2 for result in results))

    def test_optimizer_prefers_more_stable_parameter_set(self) -> None:
        bars = [
            PriceBar(
                date=f"2026-04-{index:02d}",
                symbol="SHSE.600000",
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.2,
                volume=1000 + index,
            )
            for index in range(1, 13)
        ]
        bars_by_symbol = {"SHSE.600000": bars}

        class FakeStrategy:
            def __init__(self, params):
                self.params = params

            def analyze(self, series):
                return [None] * len(series)

        class FakeBacktester:
            def __init__(self, strategy_params=None, backtest_params=None):
                self.params = strategy_params

            def run(self, series, analyses):
                first_date = series[0].date
                key = int(self.params.breakout_lookback)
                if len(series) == 12:
                    if key == 4:
                        total_return = 0.10
                    else:
                        total_return = 0.12
                elif first_date == "2026-04-01":
                    total_return = 0.09 if key == 4 else 0.24
                else:
                    total_return = 0.08 if key == 4 else -0.11
                return BacktestResult(
                    initial_capital=200000.0,
                    ending_equity=200000.0 * (1 + total_return),
                    total_return=total_return,
                    max_drawdown=0.04,
                    win_rate=0.6,
                    profit_factor=1.8,
                    trades=[],
                    equity_curve=[],
                )

        with patch("quant_hunter.optimizer.AntiHarvestStrategy", FakeStrategy), patch("quant_hunter.optimizer.Backtester", FakeBacktester):
            results = ParameterOptimizer(StrategyParams(slow_ma_window=4)).optimize(
                bars_by_symbol,
                grid={"breakout_lookback": [4, 5]},
                top_n=2,
            )

        self.assertEqual(results[0].params["breakout_lookback"], 4)

    def test_broker_generates_gm_strategy_script(self) -> None:
        adapter = EastmoneyBrokerAdapter()
        export_dir = self._temp_dir() / "gm_script"
        export_dir.mkdir(exist_ok=True)
        intents = [
            adapter.build_order_intents(
                [
                    ScanRow(
                        symbol="SHSE.600000",
                        signal_date="2026-02-24",
                        label="RECLAIM_LONG",
                        action="BUY",
                        score=88,
                        close=12.23,
                        entry_price=12.23,
                        stop_price=11.6,
                        target_price=13.2,
                        reason="demo",
                        source_path="sample.csv",
                    )
                ],
                per_trade_budget=30000,
            )[0]
        ]
        path = adapter.generate_gm_strategy_script(
            BrokerProfile(account_id="demo-account", token="demo-token", strategy_id="demo-strategy"),
            intents,
            export_dir,
        )
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        content = path.read_text(encoding="utf-8")

        self.assertIn("order_volume(", content)
        self.assertIn("MODE_LIVE", content)
        self.assertIn("demo-account", content)

    def test_broker_submit_uses_sdk_order_volume(self) -> None:
        class FakeSdk:
            OrderSide_Buy = "BUY"
            OrderSide_Sell = "SELL"
            OrderType_Limit = "LIMIT"
            PositionEffect_Open = "OPEN"

            def __init__(self) -> None:
                self.calls = []

            def set_token(self, token: str) -> None:
                self.token = token

            def order_volume(self, **kwargs):
                self.calls.append(kwargs)
                return {"ok": True, "symbol": kwargs["symbol"]}

        sdk = FakeSdk()
        adapter = EastmoneyBrokerAdapter()
        intents = adapter.build_order_intents(
            [
                ScanRow(
                    symbol="SHSE.600000",
                    signal_date="2026-02-24",
                    label="RECLAIM_LONG",
                    action="BUY",
                    score=88,
                    close=12.23,
                    entry_price=12.23,
                    stop_price=11.6,
                    target_price=13.2,
                    reason="demo",
                    source_path="sample.csv",
                )
            ],
            per_trade_budget=30000,
        )
        with (
            patch.object(adapter, "diagnose_environment", return_value={
                "python_version": "3.12.0",
                "sdk_module": "gm.api",
                "module_installed": True,
                "runtime_supported": True,
                "direct_ready": True,
                "bridge_python": "",
                "bridge_module_installed": False,
                "bridge_ready": False,
                "mode": "sdk",
            }),
            patch.object(adapter, "_is_runtime_supported", return_value=True),
            patch.object(adapter, "_load_sdk_module", return_value=sdk),
        ):
            results = adapter.submit_order_intents(
                BrokerProfile(account_id="demo-account", token="demo-token", strategy_id="demo-strategy"),
                intents,
            )

        self.assertEqual(len(sdk.calls), 1)
        self.assertIn("SHSE.600000", results[0])
        self.assertEqual(sdk.calls[0]["account"], "demo-account")

    def test_submit_order_intents_uses_close_effect_for_sell_orders(self) -> None:
        class FakeSdk:
            OrderSide_Buy = "BUY_SIDE"
            OrderSide_Sell = "SELL_SIDE"
            OrderType_Limit = "LIMIT"
            PositionEffect_Open = "OPEN"
            PositionEffect_Close = "CLOSE"

            def __init__(self) -> None:
                self.calls = []

            def set_token(self, token: str) -> None:
                self.token = token

            def order_volume(self, **kwargs):
                self.calls.append(kwargs)
                return {"ok": True, "symbol": kwargs["symbol"]}

        sdk = FakeSdk()
        adapter = EastmoneyBrokerAdapter()
        intents = [
            broker_module.OrderIntent(
                symbol="SHSE.600000",
                side="SELL",
                price=12.23,
                quantity=800,
                stop_price=11.6,
                target_price=13.2,
                signal_date="2026-02-24",
                reason="demo",
            )
        ]
        with (
            patch.object(adapter, "diagnose_environment", return_value={
                "python_version": "3.12.0",
                "sdk_module": "gm.api",
                "module_installed": True,
                "runtime_supported": True,
                "direct_ready": True,
                "bridge_python": "",
                "bridge_module_installed": False,
                "bridge_ready": False,
                "mode": "sdk",
            }),
            patch.object(adapter, "_is_runtime_supported", return_value=True),
            patch.object(adapter, "_load_sdk_module", return_value=sdk),
        ):
            adapter.submit_order_intents(
                BrokerProfile(account_id="demo-account", token="demo-token", strategy_id="demo-strategy"),
                intents,
            )

        self.assertEqual(len(sdk.calls), 1)
        self.assertEqual(sdk.calls[0]["side"], "SELL_SIDE")
        self.assertEqual(sdk.calls[0]["position_effect"], "CLOSE")

    def test_gm_runtime_diagnosis_flags_python_313(self) -> None:
        adapter = EastmoneyBrokerAdapter()
        self.assertFalse(adapter._is_runtime_supported("gm.api", (3, 13)))
        self.assertTrue(adapter._is_runtime_supported("gm.api", (3, 12)))

    def test_sdk_bridge_script_exists_for_runtime(self) -> None:
        self.assertTrue(broker_module.SDK_BRIDGE.exists())
        self.assertEqual(broker_module.SDK_BRIDGE.name, "sdk_bridge.py")

    def test_remote_market_screener_builds_algorithmic_pool(self) -> None:
        class FakeFeed:
            def fetch_market_snapshots(self, limit: int = 150):
                return [
                    MarketSnapshot(
                        symbol="SHSE.600000",
                        stock_id="600000",
                        stock_name="浦发银行",
                        latest_price=12.23,
                        pct_change=6.8,
                        change_amount=0.78,
                        turnover=8.5,
                        amount=980000000.0,
                        open_price=11.82,
                        high_price=12.50,
                        low_price=11.70,
                        prev_close=11.45,
                        main_inflow=210000000.0,
                        pe_ratio=8.5,
                        heat_score=86.0,
                        fund_model="主力净流入",
                        strategy_tag="主力雷达",
                        momentum_bias=68.0,
                    )
                ]

            def fetch_daily_bars(self, symbol: str, start: str = "20240101", end: str = "20500101"):
                rows = generate_rows("SHSE.600000", "reclaim")
                bars = []
                for row in rows:
                    bars.append(
                        PriceBar(
                            date=row[0],
                            symbol="SHSE.600000",
                            open=float(row[2]),
                            high=float(row[3]),
                            low=float(row[4]),
                            close=float(row[5]),
                            volume=float(row[6]),
                        )
                    )
                return bars

        result = RemoteMarketScreener(feed=FakeFeed()).screen_market(top_n=5, prefetch_limit=10, history_limit=5)

        self.assertGreaterEqual(len(result.algorithmic_pool), 1)
        self.assertEqual(result.algorithmic_pool[0].stock_id, "600000")
        self.assertIn(result.algorithmic_pool[0].fund_model, {"主力净流入", "游资强攻", "机构趋势", "低位试盘", "强势博弈"})
        self.assertTrue(result.algorithmic_pool[0].theme_name)
        self.assertGreater(result.algorithmic_pool[0].decision_score, 0.0)
        self.assertGreaterEqual(len(result.recommendations), 1)
        self.assertTrue(result.recommendations[0].theme_name)

    def test_eastmoney_feed_falls_back_to_stale_snapshot_cache(self) -> None:
        cache_dir = self._temp_dir() / "market_cache_test"
        cache = LocalMarketCache(root=cache_dir, snapshot_ttl_seconds=0, bars_ttl_seconds=0)
        snapshots = [
            MarketSnapshot(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="浦发银行",
                latest_price=12.3,
                pct_change=2.1,
                change_amount=0.25,
                turnover=3.2,
                amount=8.6e8,
                open_price=12.0,
                high_price=12.5,
                low_price=11.9,
                prev_close=12.05,
                main_inflow=1.1e8,
                pe_ratio=6.5,
                heat_score=86.0,
                fund_model="主力净流入",
                strategy_tag="主力雷达",
                momentum_bias=62.0,
            )
        ]
        cache.put_market_snapshots(20, snapshots)
        feed = EastmoneyMarketFeed(timeout=1, cache=cache)

        with patch.object(feed, "_fetch_json", side_effect=RuntimeError("network down")):
            restored = feed.fetch_market_snapshots(limit=20)

        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].stock_id, "600000")

    def test_local_market_cache_roundtrip_for_bars(self) -> None:
        cache_dir = self._temp_dir() / "market_cache_roundtrip"
        cache = LocalMarketCache(root=cache_dir, snapshot_ttl_seconds=60, bars_ttl_seconds=60)
        bars = [
            PriceBar(
                date="2026-04-01",
                symbol="SHSE.600000",
                open=11.80,
                high=12.40,
                low=11.70,
                close=12.30,
                volume=1234567.0,
            )
        ]

        cache.put_daily_bars("SHSE.600000", bars)
        restored = cache.get_daily_bars("SHSE.600000")
        stats = cache.cache_stats()

        self.assertEqual(len(restored), 1)
        self.assertEqual(restored[0].close, 12.30)
        self.assertGreaterEqual(stats["files"], 1)

    def test_local_market_cache_clear_removes_files(self) -> None:
        cache_dir = self._temp_dir() / "market_cache_clear"
        cache = LocalMarketCache(root=cache_dir, snapshot_ttl_seconds=60, bars_ttl_seconds=60)
        cache.put_market_snapshots(
            20,
            [
                MarketSnapshot(
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="浦发银行",
                    latest_price=12.3,
                    pct_change=2.1,
                    change_amount=0.25,
                    turnover=3.2,
                    amount=8.6e8,
                    open_price=12.0,
                    high_price=12.5,
                    low_price=11.9,
                    prev_close=12.05,
                    main_inflow=1.1e8,
                    pe_ratio=6.5,
                    heat_score=86.0,
                    fund_model="主力净流入",
                    strategy_tag="主力雷达",
                    momentum_bias=62.0,
                )
            ],
        )
        cache.put_daily_bars(
            "SHSE.600000",
            [
                PriceBar(
                    date="2026-04-01",
                    symbol="SHSE.600000",
                    open=11.80,
                    high=12.40,
                    low=11.70,
                    close=12.30,
                    volume=1234567.0,
                )
            ],
        )

        before = cache.cache_stats()
        cleared = cache.clear()
        after = cache.cache_stats()

        self.assertGreaterEqual(before["files"], 2)
        self.assertGreaterEqual(cleared["files"], 2)
        self.assertGreater(cleared["bytes"], 0)
        self.assertEqual(after["files"], 0)
        self.assertEqual(after["bytes"], 0)

    def test_qt_entry_module_imports(self) -> None:
        if importlib.util.find_spec("PySide6") is None:
            self.skipTest("PySide6 is not installed in the current interpreter")
        module = importlib.import_module("app_qt")
        ui_cards = importlib.import_module("quant_hunter.ui_cards")
        ui_config = importlib.import_module("quant_hunter.ui_config")
        ui_binders = importlib.import_module("quant_hunter.ui_binders")
        ui_controllers = importlib.import_module("quant_hunter.ui_controllers")
        ui_helpers = importlib.import_module("quant_hunter.ui_helpers")
        cross_focus_patches = importlib.import_module("quant_hunter.ui_window_cross_workspace_focus_patches")
        focus_bridge_patches = importlib.import_module("quant_hunter.ui_window_focus_bridge_patches")
        broker_status = importlib.import_module("quant_hunter.broker_status")
        license_policy = importlib.import_module("quant_hunter.license_policy")
        recommend_status = importlib.import_module("quant_hunter.recommend_status")
        ui_refresh = importlib.import_module("quant_hunter.ui_refresh")
        ui_runtime = importlib.import_module("quant_hunter.ui_runtime")
        ui_status = importlib.import_module("quant_hunter.ui_status")
        workspace_builders = importlib.import_module("quant_hunter.workspace_builders")
        self.assertTrue(hasattr(module, "QuantHunterWindow"))
        self.assertTrue(hasattr(module, "InsightCardBase"))
        self.assertTrue(hasattr(module, "StrategyWorkbenchCard"))
        self.assertTrue(hasattr(module, "ActionFlowCard"))
        self.assertTrue(hasattr(module, "CompactSummaryCard"))
        self.assertTrue(hasattr(module, "AlertSignalCard"))
        self.assertTrue(hasattr(ui_cards, "LeaderboardCard"))
        self.assertTrue(hasattr(ui_config, "WORKSPACE_TAB_ORDER"))
        self.assertTrue(hasattr(ui_config, "workspace_name_for_index"))
        self.assertTrue(hasattr(ui_binders, "apply_daily_pool_rows"))
        self.assertTrue(hasattr(ui_binders, "apply_market_screen_result"))
        self.assertTrue(hasattr(ui_binders, "apply_scan_universe_result"))
        self.assertTrue(hasattr(ui_binders, "handle_daily_pool_error"))
        self.assertTrue(hasattr(ui_binders, "handle_market_refresh_error"))
        self.assertTrue(hasattr(ui_binders, "handle_scan_error"))
        self.assertTrue(hasattr(ui_binders, "refresh_license_status_view"))
        self.assertTrue(hasattr(ui_binders, "append_order_result_entry"))
        self.assertTrue(hasattr(ui_binders, "append_submission_record_entry"))
        self.assertTrue(hasattr(ui_controllers, "refresh_daily_pool_controller"))
        self.assertTrue(hasattr(ui_controllers, "refresh_remote_market_controller"))
        self.assertTrue(hasattr(ui_controllers, "run_background_job_controller"))
        self.assertTrue(hasattr(ui_controllers, "run_parameter_optimization_controller"))
        self.assertTrue(hasattr(ui_controllers, "save_broker_profile_controller"))
        self.assertTrue(hasattr(ui_controllers, "create_broker_templates_controller"))
        self.assertTrue(hasattr(ui_controllers, "generate_order_suggestions_controller"))
        self.assertTrue(hasattr(ui_controllers, "export_order_plan_controller"))
        self.assertTrue(hasattr(ui_controllers, "export_order_result_log_controller"))
        self.assertTrue(hasattr(ui_controllers, "sync_broker_via_sdk_controller"))
        self.assertTrue(hasattr(ui_controllers, "generate_sdk_strategy_script_controller"))
        self.assertTrue(hasattr(ui_controllers, "prepare_order_submission_controller"))
        self.assertTrue(hasattr(ui_controllers, "handle_order_submission_failure_controller"))
        self.assertTrue(hasattr(ui_controllers, "handle_order_submission_success_controller"))
        self.assertTrue(hasattr(ui_controllers, "confirm_and_submit_orders_controller"))
        self.assertTrue(hasattr(ui_controllers, "save_strategy_preferences_controller"))
        self.assertTrue(hasattr(ui_controllers, "switch_license_plan_controller"))
        self.assertTrue(hasattr(license_policy, "license_capabilities"))
        self.assertTrue(hasattr(ui_runtime, "build_runtime_overview_text"))
        self.assertTrue(hasattr(ui_runtime, "append_runtime_log"))
        self.assertTrue(hasattr(ui_runtime, "clear_market_cache"))
        self.assertTrue(hasattr(ui_runtime, "record_job_result"))
        self.assertTrue(hasattr(ui_runtime, "refresh_runtime_panel"))
        self.assertTrue(hasattr(ui_runtime, "runtime_export_dir"))
        self.assertTrue(hasattr(ui_runtime, "export_runtime_log"))
        self.assertTrue(hasattr(ui_status, "signal_colors"))
        self.assertTrue(hasattr(ui_status, "submission_colors"))
        self.assertTrue(hasattr(ui_status, "display_order_status"))
        self.assertTrue(hasattr(ui_status, "display_fill_status"))
        self.assertTrue(hasattr(ui_status, "display_action"))
        self.assertTrue(hasattr(ui_status, "display_label"))
        self.assertTrue(hasattr(ui_status, "display_mode"))
        self.assertTrue(hasattr(ui_status, "display_leader_level"))
        self.assertTrue(hasattr(ui_status, "fund_badge_palette"))
        self.assertTrue(hasattr(ui_status, "strategy_badge_palette"))
        self.assertTrue(hasattr(ui_status, "signal_badge_palette"))
        self.assertTrue(hasattr(ui_status, "board_risk_colors"))
        self.assertTrue(hasattr(ui_status, "board_monitor_colors"))
        self.assertTrue(hasattr(ui_status, "market_mode_label"))
        self.assertTrue(hasattr(ui_status, "market_source_mode_label"))
        self.assertTrue(hasattr(broker_status, "build_broker_execution_summary"))
        self.assertTrue(hasattr(recommend_status, "execution_status_for_symbol"))
        self.assertTrue(hasattr(recommend_status, "recommend_execution_summary"))
        self.assertTrue(hasattr(recommend_status, "execution_summary_for_rows"))
        self.assertTrue(hasattr(ui_refresh, "build_market_proxy_points"))
        self.assertTrue(hasattr(ui_refresh, "history_window_limit"))
        self.assertTrue(hasattr(ui_helpers, "build_workspace_hero"))
        self.assertTrue(hasattr(ui_helpers, "build_overview_outline_style"))
        self.assertTrue(hasattr(ui_helpers, "build_overview_filled_style"))
        self.assertTrue(hasattr(ui_helpers, "build_stock_identity_cell"))
        self.assertTrue(hasattr(ui_helpers, "create_metric_card"))
        self.assertTrue(hasattr(ui_helpers, "build_badge_strip"))
        self.assertTrue(hasattr(ui_helpers, "create_shell_chip"))
        self.assertTrue(hasattr(ui_helpers, "set_shell_chip"))
        self.assertTrue(hasattr(ui_helpers, "style_dark_chart"))
        self.assertTrue(hasattr(ui_helpers, "configure_splitter"))
        self.assertTrue(hasattr(ui_helpers, "enable_smooth_scroll"))
        self.assertTrue(hasattr(ui_helpers, "select_first_row"))
        self.assertTrue(hasattr(ui_helpers, "focus_widget_later"))
        self.assertTrue(hasattr(ui_helpers, "stock_profile_for_symbol"))
        self.assertTrue(hasattr(ui_helpers, "stock_name_for_symbol"))
        self.assertTrue(hasattr(ui_helpers, "stock_id_for_symbol"))
        self.assertTrue(hasattr(cross_focus_patches, "apply_cross_workspace_focus_patches"))
        self.assertTrue(hasattr(focus_bridge_patches, "apply_focus_bridge_patches"))
        self.assertTrue(hasattr(ui_refresh, "refresh_priority_cards"))
        self.assertTrue(hasattr(ui_refresh, "render_leaderboard_cards"))
        self.assertTrue(hasattr(ui_refresh, "refresh_theme_heat_panels"))
        self.assertTrue(hasattr(ui_refresh, "apply_market_filters"))
        self.assertTrue(hasattr(ui_refresh, "build_overview_command_snapshot"))
        self.assertTrue(hasattr(ui_refresh, "build_dashboard_metrics_snapshot"))
        self.assertTrue(hasattr(ui_refresh, "fill_scan_rows"))
        self.assertTrue(hasattr(ui_refresh, "refresh_intraday_monitor"))
        self.assertTrue(hasattr(ui_refresh, "refresh_trade_recap"))
        self.assertTrue(hasattr(ui_refresh, "refresh_broker_execution_panel"))
        self.assertTrue(hasattr(ui_refresh, "refresh_broker_status"))
        self.assertTrue(hasattr(ui_refresh, "fill_holdings_table"))
        self.assertTrue(hasattr(ui_runtime, "review_output_dir"))
        self.assertTrue(hasattr(ui_runtime, "daily_plan_output_dir"))
        self.assertTrue(hasattr(ui_runtime, "current_strategy_runtime_config"))
        self.assertTrue(hasattr(ui_runtime, "current_report_template_config"))
        self.assertTrue(hasattr(ui_runtime, "parse_focus_themes_text"))
        self.assertTrue(hasattr(ui_refresh, "fill_order_intents_table"))
        self.assertTrue(hasattr(ui_refresh, "refresh_submission_table"))
        self.assertTrue(hasattr(workspace_builders, "build_auth_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_board_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_broker_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_config_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_overview_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_recommend_workspace"))

    def test_workspace_builder_module_has_no_duplicate_workspace_functions(self) -> None:
        path = Path(__file__).resolve().parents[1] / "quant_hunter" / "workspace_builders.py"
        module = ast.parse(path.read_text(encoding="utf-8"))

        seen: dict[str, int] = {}
        duplicates: list[str] = []
        for node in module.body:
            if not isinstance(node, ast.FunctionDef):
                continue
            if not node.name.startswith("build_") or not node.name.endswith("_workspace"):
                continue
            if node.name in seen:
                duplicates.append(node.name)
                continue
            seen[node.name] = node.lineno

        self.assertEqual(duplicates, [])

    def test_qt_window_smoke_boot(self) -> None:
        if importlib.util.find_spec("PySide6") is None:
            self.skipTest("PySide6 is not installed in the current interpreter")
        with patch.dict(os.environ, {"QT_QPA_PLATFORM": os.environ.get("QT_QPA_PLATFORM", "offscreen")}):
            from PySide6.QtWidgets import QApplication

            module = importlib.import_module("app_qt")
            app = QApplication.instance() or QApplication([])
            window = module.QuantHunterWindow()
            try:
                app.processEvents()
                self.assertIsNotNone(window.tabs)
                self.assertGreaterEqual(window.tabs.count(), 6)
                self.assertTrue(hasattr(window, "paper_trading_focus_label"))
                self.assertTrue(hasattr(window, "paper_to_recommend_button"))
                self.assertTrue(hasattr(window, "recommend_decision_summary_text"))
                self.assertTrue(hasattr(window, "recommend_push_focus_button"))
            finally:
                window.close()
                app.processEvents()

    def test_emit_action_feedback_updates_workspace_labels_and_story(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        refresh_calls: list[str] = []
        runtime_logs: list[str] = []
        status_messages: list[tuple[str, int]] = []
        window = SimpleNamespace(
            recommend_status_label=module.QLabel(),
            broker_status_banner=module.QLabel(),
            scan_summary_label=module.QLabel(),
            status_action_label=module.QLabel(),
            _append_runtime_log=lambda message: runtime_logs.append(message),
            _refresh_runtime_story_v10=lambda: refresh_calls.append("refresh"),
            _sync_commercial_statusbar_v35=lambda: refresh_calls.append("statusbar"),
            _set_label_text_if_changed=lambda label, text, tooltip=None: label.setText(text) if label.text() != text else None,
            statusBar=lambda: SimpleNamespace(showMessage=lambda message, timeout: status_messages.append((message, timeout))),
        )

        module.QuantHunterWindow._emit_action_feedback_v11(
            window,
            "机会池",
            "复盘页 -> 机会池",
            recommend_text="推荐状态：已同步焦点。",
            broker_text="交易台：等待复核。",
            scan_text="扫描状态：继续观察。",
        )

        self.assertEqual(runtime_logs, ["页面联动：机会池 | 复盘页 -> 机会池"])
        self.assertEqual(window.recommend_status_label.text(), "推荐状态：已同步焦点。")
        self.assertEqual(window.broker_status_banner.text(), "交易台：等待复核。")
        self.assertEqual(window.scan_summary_label.text(), "扫描状态：继续观察。")
        self.assertEqual(status_messages, [("最近动作：机会池 | 复盘页 -> 机会池", 5000)])
        self.assertEqual(window._qh_last_action_feedback_v35, "最近动作：机会池 | 复盘页 -> 机会池")
        self.assertEqual(refresh_calls, ["refresh", "statusbar"])

    def test_sync_pipeline_panels_updates_summary_counts(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            scan_rows=[object(), object()],
            daily_pool_rows=[object()],
            order_intents=[object(), object(), object()],
            order_submission_records=[object()],
            scanner_live_summary_headline=module.QLabel(),
            scanner_live_summary_detail=module.QLabel(),
            scanner_live_summary_meta=module.QLabel(),
            recommend_live_summary_headline=module.QLabel(),
            recommend_live_summary_detail=module.QLabel(),
            recommend_live_summary_meta=module.QLabel(),
            broker_live_summary_headline=module.QLabel(),
            broker_live_summary_detail=module.QLabel(),
            broker_live_summary_meta=module.QLabel(),
        )

        module.QuantHunterWindow._sync_pipeline_panels_v12(window)

        self.assertEqual(window.scanner_live_summary_headline.text(), "扫描态势")
        self.assertIn("已扫描 2 只候选", window.scanner_live_summary_detail.text())
        self.assertEqual(window.recommend_live_summary_headline.text(), "推荐态势")
        self.assertIn("已生成 1 只机会候选", window.recommend_live_summary_detail.text())
        self.assertEqual(window.broker_live_summary_headline.text(), "交易态势")
        self.assertEqual(window.broker_live_summary_detail.text(), "委托建议 3 笔，提交记录 1 笔。")
        self.assertEqual(window.broker_live_summary_meta.text(), "下一步：复核委托后再确认提交。")

    def test_board_mode_engine_builds_candidates(self) -> None:
        sample_dir = self._temp_dir() / "board_universe_v2"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=5)
        plan = BoardModeEngine().build(pool, top_n=5)

        self.assertGreaterEqual(len(plan.candidates), 1)
        self.assertGreaterEqual(len(plan.monitor_rows), 1)
        self.assertIn(plan.temperature, {"积极试错", "轻仓参与", "先观察", "暂停出手"})
        self.assertIn(plan.monitor_rows[0].monitor_state, {"强势连板候选", "回封观察", "分歧待确认", "炸板风险"})

    def test_end_of_day_review_export_creates_files(self) -> None:
        sample_dir = self._temp_dir() / "review_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=5)
        trade_plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)
        board_plan = BoardModeEngine().build(pool, top_n=5)

        output_dir = self._temp_dir() / "review_exports"
        output_dir.mkdir(exist_ok=True)
        artifacts = export_end_of_day_review(
            output_dir=output_dir,
            recommendations=pool,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600000",
                    quantity=1000,
                    available=1000,
                    cost_price=10.0,
                    market_value=12300.0,
                )
            ],
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=62300.0),
            scan_rows=rows,
            focus_themes=["银行", "中字头"],
            license_plan="PRO",
        )
        self.addCleanup(lambda: Path(artifacts.markdown_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.csv_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.json_path).unlink(missing_ok=True))

        self.assertTrue(Path(artifacts.markdown_path).exists())
        self.assertTrue(Path(artifacts.csv_path).exists())
        self.assertTrue(Path(artifacts.json_path).exists())
        markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")
        payload = Path(artifacts.json_path).read_text(encoding="utf-8")
        self.assertIn("收盘复盘", markdown)
        self.assertIn("## 今日交易计划", markdown)
        self.assertIn("授权方案: PRO", markdown)
        self.assertIn("用户关注题材: 银行, 中字头", markdown)
        self.assertIn("SHSE.600000", payload)
        self.assertIn('"license_plan": "PRO"', payload)

    def test_daily_trade_plan_export_creates_files(self) -> None:
        sample_dir = self._temp_dir() / "daily_plan_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=5)
        trade_plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)

        output_dir = self._temp_dir() / "daily_plan_exports"
        output_dir.mkdir(exist_ok=True)
        artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=pool,
            trade_plan=trade_plan,
            holdings=[],
            focus_themes=["银行"],
            license_plan="TRIAL",
        )
        self.addCleanup(lambda: Path(artifacts.markdown_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.csv_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.json_path).unlink(missing_ok=True))

        self.assertTrue(Path(artifacts.markdown_path).exists())
        self.assertTrue(Path(artifacts.csv_path).exists())
        self.assertTrue(Path(artifacts.json_path).exists())
        markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")
        payload = Path(artifacts.json_path).read_text(encoding="utf-8")
        with Path(artifacts.csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
            csv_rows = list(csv.reader(handle))
        self.assertIn("盘前交易计划", markdown)
        self.assertIn("授权方案: TRIAL", markdown)
        self.assertIn("用户关注题材: 银行", markdown)
        self.assertIn("市场周期", markdown)
        self.assertIn("今日主线题材", markdown)
        self.assertIn("分层:", markdown)
        self.assertIn("盈亏比:", markdown)
        self.assertIn('"focus_themes": [', payload)
        self.assertIn("opportunity_tier", payload)
        self.assertIn("risk_reward_ratio", payload)
        self.assertEqual(
            csv_rows[0],
            [
                "section",
                "stock_name",
                "stock_id",
                "symbol",
                "action",
                "score",
                "price",
                "stop",
                "target",
                "opportunity_tier",
                "risk_flag",
                "risk_reward_ratio",
                "signal_source",
                "next_focus",
                "invalidation_reason",
                "note",
            ],
        )

    def test_end_to_end_exports_succeed_when_risk_filters_block_new_trades(self) -> None:
        sample_dir = self._temp_dir() / "daily_plan_signal_exports"
        sample_dir.mkdir(exist_ok=True)
        files = {
            "SHSE.600000_demo.csv": generate_rows("SHSE.600000", "reclaim"),
            "SZSE.000001_demo.csv": generate_rows("SZSE.000001", "watch"),
            "SHSE.601398_demo.csv": generate_rows("SHSE.601398", "weak"),
        }
        for filename, generated_rows in files.items():
            path = sample_dir / filename
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
                writer.writerows(generated_rows)
            self.addCleanup(lambda target=path: target.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=10)
        trade_plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)
        board_plan = BoardModeEngine().build(pool, top_n=5)
        paper_state = PaperTradingEngine().run_cycle(
            PaperTradingState(enabled=True, initial_cash=100000.0, cash=100000.0, max_position_pct=0.25),
            pool,
            as_of="2026-04-15 14:35:00",
        )

        output_dir = self._temp_dir() / "daily_plan_signal_exports_reports"
        output_dir.mkdir(exist_ok=True)
        plan_artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=pool,
            trade_plan=trade_plan,
            holdings=[],
        )
        review_artifacts = export_end_of_day_review(
            output_dir=output_dir,
            recommendations=pool,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=[],
            cash_snapshot=None,
            scan_rows=rows,
        )
        paper_artifacts = export_paper_trading_report(
            paper_state,
            output_dir=output_dir,
            exported_at="2026-04-15 15:10:00",
        )
        for artifacts in (plan_artifacts, review_artifacts, paper_artifacts):
            self.addCleanup(lambda target=Path(artifacts.markdown_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.csv_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.json_path): target.unlink(missing_ok=True))

        self.assertEqual(len(pool), 2)
        self.assertEqual(len(trade_plan.decisions), 0)
        self.assertEqual(paper_state.positions, [])
        self.assertEqual(paper_state.ledger, [])
        self.assertIn("当前没有符合条件的新开仓候选", " | ".join(trade_plan.notes))
        self.assertIn("本轮没有触发新的模拟成交", paper_state.last_strategy_note)
        self.assertTrue(Path(plan_artifacts.markdown_path).exists())
        self.assertTrue(Path(review_artifacts.markdown_path).exists())
        self.assertTrue(Path(paper_artifacts.markdown_path).exists())

    def test_end_to_end_trade_path_generates_decision_intent_and_reports(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-15",
                close=28.5,
                entry_price=28.5,
                stop_price=27.6,
                target_price=31.5,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="人工智能",
                stock_pool="龙头股",
                buy_point="回踩 28.50 附近承接后低吸",
                sell_point="冲击 31.50 一带分批兑现",
                primary_strategy="龙头模型",
                mainline_tag="人工智能",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                mainline_window_score=86.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                risk_reward_ratio=3.33,
                setup_quality_score=90.0,
                execution_readiness=84.0,
                confidence_score=87.0,
                opportunity_tier="优先处理",
                rationale="主线延续，空间和风报比都达标。",
                next_focus="盯承接和主线强化，不追高。",
                signal_source="synthetic-e2e",
            )
        ]

        trade_plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)
        board_plan = BoardModeEngine().build(recommendations, top_n=5)
        intents = [
            item
            for item in (build_order_intent_from_trade_decision(decision) for decision in trade_plan.decisions)
            if item is not None
        ]
        paper_state = PaperTradingEngine().run_cycle(
            PaperTradingState(enabled=True, initial_cash=100000.0, cash=100000.0, max_position_pct=0.25),
            recommendations,
            as_of="2026-04-15 10:05:00",
        )

        output_dir = self._temp_dir() / "daily_plan_buy_path_exports"
        output_dir.mkdir(exist_ok=True)
        plan_artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            holdings=[],
        )
        review_artifacts = export_end_of_day_review(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=[],
            cash_snapshot=None,
            scan_rows=[],
        )
        paper_artifacts = export_paper_trading_report(
            paper_state,
            output_dir=output_dir,
            exported_at="2026-04-15 15:10:00",
        )
        for artifacts in (plan_artifacts, review_artifacts, paper_artifacts):
            self.addCleanup(lambda target=Path(artifacts.markdown_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.csv_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.json_path): target.unlink(missing_ok=True))

        self.assertEqual(len(trade_plan.decisions), 1)
        self.assertEqual(trade_plan.decisions[0].symbol, "SZSE.300024")
        self.assertEqual(len(intents), 1)
        self.assertEqual(intents[0].symbol, "SZSE.300024")
        self.assertGreaterEqual(intents[0].quantity, 100)
        self.assertEqual(len(paper_state.positions), 1)
        self.assertEqual(len(paper_state.ledger), 1)
        self.assertIn("新开 1 笔", paper_state.last_strategy_note)
        self.assertTrue(Path(plan_artifacts.markdown_path).exists())
        self.assertTrue(Path(review_artifacts.markdown_path).exists())
        self.assertTrue(Path(paper_artifacts.markdown_path).exists())
        self.assertIn("机器人核心", Path(plan_artifacts.markdown_path).read_text(encoding="utf-8"))
        self.assertIn("机器人核心", Path(review_artifacts.markdown_path).read_text(encoding="utf-8"))
        self.assertIn("机器人核心", Path(paper_artifacts.markdown_path).read_text(encoding="utf-8"))

    def test_report_exports_preserve_chinese_content(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-15",
                close=28.5,
                entry_price=28.5,
                stop_price=27.6,
                target_price=31.5,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="人工智能",
                stock_pool="龙头股",
                buy_point="回踩 28.50 附近承接后低吸",
                sell_point="冲击 31.50 一带分批兑现",
                primary_strategy="龙头模型",
                mainline_tag="人工智能",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                mainline_window_score=86.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                risk_reward_ratio=3.33,
                setup_quality_score=90.0,
                execution_readiness=84.0,
                confidence_score=87.0,
                opportunity_tier="优先处理",
                rationale="主线延续，空间和风报比都达标。",
                next_focus="盯承接和主线强化，不追高。",
                signal_source="utf8-check",
            )
        ]
        trade_plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)
        board_plan = BoardModeEngine().build(recommendations, top_n=5)
        paper_state = PaperTradingEngine().run_cycle(
            PaperTradingState(enabled=True, initial_cash=100000.0, cash=100000.0, max_position_pct=0.25),
            recommendations,
            as_of="2026-04-15 10:05:00",
        )

        output_dir = self._temp_dir() / "utf8_exports"
        output_dir.mkdir(exist_ok=True)
        plan_artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            holdings=[],
        )
        review_artifacts = export_end_of_day_review(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=[],
            cash_snapshot=None,
            scan_rows=[],
        )
        paper_artifacts = export_paper_trading_report(
            paper_state,
            output_dir=output_dir,
            exported_at="2026-04-15 15:10:00",
        )
        for artifacts in (plan_artifacts, review_artifacts, paper_artifacts):
            self.addCleanup(lambda target=Path(artifacts.markdown_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.csv_path): target.unlink(missing_ok=True))
            self.addCleanup(lambda target=Path(artifacts.json_path): target.unlink(missing_ok=True))

        plan_markdown = Path(plan_artifacts.markdown_path).read_text(encoding="utf-8")
        review_markdown = Path(review_artifacts.markdown_path).read_text(encoding="utf-8")
        paper_markdown = Path(paper_artifacts.markdown_path).read_text(encoding="utf-8")
        review_payload = Path(review_artifacts.json_path).read_text(encoding="utf-8")
        paper_payload = Path(paper_artifacts.json_path).read_text(encoding="utf-8")

        for text in (plan_markdown, review_markdown, paper_markdown, review_payload, paper_payload):
            self.assertIn("机器人核心", text)
            self.assertIn("人工智能", text)
        self.assertIn("龙头模型", plan_markdown)
        self.assertIn("龙头模型", paper_markdown)
        self.assertIn("龙头模型", review_payload)
        self.assertIn("龙头模型", paper_payload)
        self.assertIn(board_plan.temperature, review_markdown)

    def test_daily_trade_plan_export_surfaces_mainline_prelaunch_guidance(self) -> None:
        from quant_hunter.reports import export_daily_trade_plan

        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="延续偏强",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=82.0,
                position_score=84.0,
                persistence_score=80.0,
                news_score=76.0,
                leader_score=88.0,
                total_score=84.0,
                theme_name="AI",
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                mainline_window_score=82.0,
                mainline_risk_flag="低",
                rationale="continue demo",
            ),
            RecommendationRow(
                symbol="SZSE.300750",
                stock_id="300750",
                stock_name="延续可跟踪",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-05",
                close=180.0,
                entry_price=180.0,
                stop_price=172.0,
                target_price=198.0,
                technical_score=73.0,
                position_score=72.0,
                persistence_score=71.0,
                news_score=68.0,
                leader_score=74.0,
                total_score=77.0,
                theme_name="新能源",
                theme_rank=2,
                mainline_tag="新能源",
                mainline_rank=2,
                mainline_role="FOLLOW",
                mainline_strength_score=64.0,
                mainline_continuation_score=58.0,
                theme_divergence_score=40.0,
                theme_failure_risk=42.0,
                mainline_window_score=58.0,
                mainline_risk_flag="中",
                rationale="watch demo",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="切换预警",
                action="REDUCE",
                label="REDUCE",
                signal_date="2026-04-05",
                close=12.0,
                entry_price=12.0,
                stop_price=11.2,
                target_price=13.4,
                technical_score=75.0,
                position_score=74.0,
                persistence_score=70.0,
                news_score=69.0,
                leader_score=68.0,
                total_score=75.0,
                theme_name="金融",
                theme_rank=5,
                mainline_tag="金融",
                mainline_rank=5,
                mainline_role="FOLLOW",
                mainline_strength_score=60.0,
                mainline_continuation_score=42.0,
                theme_divergence_score=62.0,
                theme_failure_risk=60.0,
                mainline_window_score=43.0,
                mainline_risk_flag="高",
                rationale="switch demo",
            ),
        ]
        trade_plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        output_dir = self._temp_dir() / "daily_plan_signal_exports"
        output_dir.mkdir(exist_ok=True)
        artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            holdings=[],
            focus_themes=["AI"],
            license_plan="TRIAL",
        )
        self.addCleanup(lambda: Path(artifacts.markdown_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.csv_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.json_path).unlink(missing_ok=True))

        markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")
        self.assertIn("主线预案", markdown)
        self.assertIn("继续跟", markdown)
        self.assertIn("只观察", markdown)
        self.assertIn("防切换", markdown)
        self.assertIn("延续偏强", markdown)
        self.assertIn("切换预警", markdown)

    def test_theme_summary_builds_rows_and_leaders(self) -> None:
        sample_dir = self._temp_dir() / "theme_universe"
        sample_dir.mkdir(exist_ok=True)
        path = sample_dir / "SHSE.600000_demo.csv"
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "symbol", "open", "high", "low", "close", "volume"])
            writer.writerows(generate_rows("SHSE.600000", "reclaim"))
        self.addCleanup(lambda: path.unlink(missing_ok=True))

        rows, bars_by_symbol, analyses_by_symbol, _ = UniverseScanner(StrategyParams()).scan_folder(sample_dir)
        summaries = UniverseScanner(StrategyParams()).summarize_backtests(bars_by_symbol, analyses_by_symbol)
        pool = DailyPoolBuilder(
            stock_profiles=load_stock_profiles_from_csv(Path("sample_data/stock_profiles.csv")),
            news_map=load_news_catalysts_from_csv(Path("sample_data/news_catalysts.csv")),
            theme_aliases=load_theme_aliases_from_csv(Path("sample_data/theme_aliases.csv")),
        ).build(rows, analyses_by_symbol, summaries, top_n=5)
        theme_rows, leader_rows = summarize_themes(pool)

        self.assertGreaterEqual(len(theme_rows), 1)
        self.assertGreaterEqual(len(leader_rows), 1)
        self.assertEqual(theme_rows[0].theme_rank, 1)
        self.assertTrue(theme_rows[0].is_primary)
        self.assertGreater(theme_rows[0].window_score, 0.0)
        self.assertGreaterEqual(theme_rows[0].failure_risk, 0.0)
        self.assertIn(leader_rows[0].leader_level, {"CORE_LEADER", "ACTIVE_LEADER"})
        self.assertIn(leader_rows[0].mainline_role, {"CORE", "FRONT", "ASSIST"})

    def test_theme_heat_engine_prioritizes_primary_mainline_and_assigns_roles(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=28.5,
                entry_price=28.5,
                stop_price=27.2,
                target_price=31.8,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="机器人",
                primary_strategy="龙头模型",
                dragon_decision_score=93.0,
                rationale="主线龙头",
            ),
            RecommendationRow(
                symbol="SZSE.300025",
                stock_id="300025",
                stock_name="机器人前排",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=19.3,
                entry_price=19.3,
                stop_price=18.4,
                target_price=21.2,
                technical_score=84.0,
                position_score=80.0,
                persistence_score=82.0,
                news_score=76.0,
                leader_score=84.0,
                total_score=84.0,
                theme_name="机器人",
                primary_strategy="主力雷达",
                dragon_decision_score=86.0,
                rationale="主线助攻",
            ),
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="银行跟随",
                action="WATCH",
                label="WATCH",
                signal_date="2026-04-06",
                close=10.2,
                entry_price=10.2,
                stop_price=9.8,
                target_price=11.0,
                technical_score=68.0,
                position_score=70.0,
                persistence_score=62.0,
                news_score=60.0,
                leader_score=64.0,
                total_score=67.0,
                theme_name="银行",
                primary_strategy="价值低吸",
                dragon_decision_score=68.0,
                rationale="非主线观察",
            ),
        ]

        enriched, theme_rows, leader_rows = ThemeHeatEngine().analyze(recommendations)

        self.assertEqual(theme_rows[0].theme_name, "人工智能")
        self.assertEqual(enriched[0].stock_id, "300024")
        self.assertEqual(enriched[0].mainline_tag, "人工智能")
        self.assertEqual(enriched[0].mainline_rank, 1)
        self.assertEqual(enriched[0].mainline_role, "CORE")
        self.assertGreater(enriched[0].mainline_window_score, 70.0)
        self.assertGreater(enriched[0].leader_position_score, 80.0)
        self.assertIn(enriched[-1].mainline_role, {"NOISE", "ELIMINATED", "FOLLOW"})
        self.assertGreaterEqual(theme_rows[0].window_score, theme_rows[1].window_score)
        self.assertTrue(any(item.mainline_role in {"CORE", "FRONT"} for item in leader_rows))

    def test_infer_mainline_stage_classifies_core_market_phases(self) -> None:
        self.assertEqual(
            infer_mainline_stage(1, 88.0, 76.0, 28.0, 18.0, 86.0, "CORE"),
            "加速",
        )
        self.assertEqual(
            infer_mainline_stage(2, 74.0, 58.0, 63.0, 49.0, 61.0, "FRONT"),
            "分歧",
        )
        self.assertEqual(
            infer_mainline_stage(2, 78.0, 62.0, 36.0, 42.0, 67.0, "CORE"),
            "启动",
        )
        self.assertEqual(
            infer_mainline_stage(5, 56.0, 44.0, 40.0, 73.0, 43.0, "NOISE"),
            "退潮",
        )

    def test_infer_mainline_flow_signal_distinguishes_continuation_and_switching(self) -> None:
        self.assertEqual(
            infer_mainline_flow_signal(1, 88.0, 76.0, 28.0, 18.0, 86.0, "CORE"),
            "延续偏强",
        )
        self.assertEqual(
            infer_mainline_flow_signal(2, 74.0, 58.0, 63.0, 49.0, 61.0, "FRONT"),
            "切换预警",
        )
        self.assertEqual(
            infer_mainline_flow_signal(2, 78.0, 62.0, 36.0, 42.0, 67.0, "CORE"),
            "延续待确认",
        )
        self.assertEqual(
            infer_mainline_flow_signal(5, 56.0, 44.0, 40.0, 73.0, 43.0, "NOISE"),
            "切换/退潮",
        )

    def test_recommendation_sort_key_prefers_accelerating_mainline(self) -> None:
        accelerating = RecommendationRow(
            symbol="SZSE.300100",
            stock_id="300100",
            stock_name="加速主线",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=18.0,
            entry_price=18.0,
            stop_price=17.2,
            target_price=20.1,
            technical_score=82.0,
            position_score=79.0,
            persistence_score=77.0,
            news_score=70.0,
            leader_score=86.0,
            total_score=84.0,
            theme_name="人工智能",
            theme_score=88.0,
            theme_rank=1,
            leader_level="CORE_LEADER",
            primary_strategy="主力决策",
            stock_pool="龙头股",
            pool_score=90.0,
            mainline_tag="人工智能",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_strength_score=88.0,
            mainline_continuation_score=76.0,
            leader_position_score=88.0,
            mainline_window_score=86.0,
            theme_divergence_score=28.0,
            theme_failure_risk=18.0,
            mainline_risk_flag="低",
            rationale="阶段 加速 | 信号 延续偏强",
        )
        diverging = RecommendationRow(
            symbol="SZSE.300101",
            stock_id="300101",
            stock_name="分歧主线",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=16.0,
            entry_price=16.0,
            stop_price=15.3,
            target_price=17.8,
            technical_score=85.0,
            position_score=80.0,
            persistence_score=74.0,
            news_score=72.0,
            leader_score=84.0,
            total_score=86.0,
            theme_name="人工智能",
            theme_score=84.0,
            theme_rank=1,
            leader_level="ACTIVE_LEADER",
            primary_strategy="主力决策",
            stock_pool="趋势股",
            pool_score=87.0,
            mainline_tag="人工智能",
            mainline_rank=1,
            mainline_role="FRONT",
            mainline_strength_score=84.0,
            mainline_continuation_score=58.0,
            leader_position_score=82.0,
            mainline_window_score=61.0,
            theme_divergence_score=63.0,
            theme_failure_risk=49.0,
            mainline_risk_flag="中",
            rationale="阶段 分歧 | 信号 切换预警",
        )

        self.assertLess(_recommendation_sort_key(accelerating), _recommendation_sort_key(diverging))

    def test_recommendation_sort_key_prefers_stronger_one_day_hold_tripwire_setup(self) -> None:
        stronger = RecommendationRow(
            symbol="SZSE.300200",
            stock_id="300200",
            stock_name="强隔日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=12.0,
            entry_price=12.0,
            stop_price=11.6,
            target_price=12.8,
            technical_score=82.0,
            position_score=79.0,
            persistence_score=77.0,
            news_score=72.0,
            leader_score=80.0,
            total_score=83.0,
            theme_name="机器人",
            theme_score=84.0,
            theme_rank=1,
            leader_level="ACTIVE_LEADER",
            primary_strategy="一日持股法",
            stock_pool="趋势股",
            pool_score=88.0,
            mainline_tag="机器人",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_strength_score=84.0,
            mainline_continuation_score=79.0,
            leader_position_score=81.0,
            mainline_window_score=84.0,
            theme_divergence_score=24.0,
            theme_failure_risk=20.0,
            mainline_risk_flag="低",
            one_day_hold_score=88.0,
            execution_readiness=82.0,
            rationale="阶段 加速 | 信号 延续偏强",
        )
        weaker = RecommendationRow(
            symbol="SZSE.300201",
            stock_id="300201",
            stock_name="弱隔日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=12.0,
            entry_price=12.0,
            stop_price=11.6,
            target_price=12.8,
            technical_score=83.0,
            position_score=79.0,
            persistence_score=77.0,
            news_score=72.0,
            leader_score=80.0,
            total_score=84.0,
            theme_name="机器人",
            theme_score=84.0,
            theme_rank=1,
            leader_level="ACTIVE_LEADER",
            primary_strategy="一日持股法",
            stock_pool="趋势股",
            pool_score=89.0,
            mainline_tag="机器人",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_strength_score=84.0,
            mainline_continuation_score=68.0,
            leader_position_score=81.0,
            mainline_window_score=76.0,
            theme_divergence_score=24.0,
            theme_failure_risk=20.0,
            mainline_risk_flag="中",
            one_day_hold_score=80.0,
            execution_readiness=70.0,
            rationale="阶段 加速 | 信号 延续待确认",
        )

        self.assertLess(_recommendation_sort_key(stronger), _recommendation_sort_key(weaker))

    def test_theme_heat_engine_rationale_includes_flow_signal(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=28.5,
                entry_price=28.5,
                stop_price=27.2,
                target_price=31.8,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="机器人",
                primary_strategy="龙头模型",
                dragon_decision_score=93.0,
                rationale="主线龙头",
            ),
            RecommendationRow(
                symbol="SZSE.300025",
                stock_id="300025",
                stock_name="机器人前排",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=19.3,
                entry_price=19.3,
                stop_price=18.4,
                target_price=21.2,
                technical_score=84.0,
                position_score=80.0,
                persistence_score=82.0,
                news_score=76.0,
                leader_score=84.0,
                total_score=84.0,
                theme_name="机器人",
                primary_strategy="主力雷达",
                dragon_decision_score=86.0,
                rationale="主线助攻",
            ),
        ]

        enriched, _, _ = ThemeHeatEngine().analyze(recommendations)

        self.assertIn("信号 延续", enriched[0].rationale)
        self.assertIn("阶段", enriched[0].rationale)

    def test_theme_alias_loader_supports_custom_mapping(self) -> None:
        temp_dir = self._temp_dir()
        theme_path = temp_dir / "themes.csv"
        theme_path.write_text(
            "theme_name,keywords\n银行,\"银行,金融,信贷\"\n半导体,\"芯片,算力,存储\"\n",
            encoding="utf-8-sig",
        )
        self.addCleanup(lambda: theme_path.unlink(missing_ok=True))

        mapping = load_theme_aliases_from_csv(theme_path)

        self.assertIn("银行", mapping)
        self.assertIn("金融", mapping["银行"])

    def test_app_state_persists_theme_filters_and_alias_path(self) -> None:
        state_path = self._temp_dir() / "app_state.json"
        save_app_state(
            state_path,
            AppState(
                universe_dir="demo",
                selected_symbol="SHSE.600000",
                watchlist=["SHSE.600000"],
                ui_theme="graphite",
                theme_alias_path="sample_data/theme_aliases.csv",
                recommend_theme_filter="银行",
                recommend_strategy_filter="掘龙决策",
                recommend_action_filter="买入",
                recommend_execution_filter="已提交",
                market_theme_filter="主力雷达",
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.theme_alias_path, "sample_data/theme_aliases.csv")
        self.assertEqual(restored.recommend_theme_filter, "银行")
        self.assertEqual(restored.recommend_strategy_filter, "掘龙决策")
        self.assertEqual(restored.recommend_action_filter, "买入")
        self.assertEqual(restored.recommend_execution_filter, "已提交")
        self.assertEqual(restored.market_theme_filter, "主力雷达")

    def test_app_state_persists_strategy_and_license_settings(self) -> None:
        state_path = self._temp_dir() / "app_state_strategy.json"
        save_app_state(
            state_path,
            AppState(
                focus_themes=["银行", "机器人"],
                strategy_risk_profile="conservative",
                strategy_top_theme_limit=4,
                strategy_max_total_exposure=0.65,
                strategy_theme_drop_reduce=False,
                license_plan="PRO",
                trial_started_at="2026-04-01",
                auto_daily_plan_export=True,
                daily_plan_template="focus",
                daily_plan_focus_only=True,
                daily_plan_candidate_limit=8,
                market_data_mode="cache",
                market_timeframe_mode="周线",
                market_history_window="近3年",
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.focus_themes, ["银行", "机器人"])
        self.assertEqual(restored.strategy_risk_profile, "conservative")
        self.assertEqual(restored.strategy_top_theme_limit, 4)
        self.assertAlmostEqual(restored.strategy_max_total_exposure, 0.65)
        self.assertFalse(restored.strategy_theme_drop_reduce)
        self.assertEqual(restored.license_plan, "PRO")
        self.assertEqual(restored.trial_started_at, "2026-04-01")
        self.assertTrue(restored.auto_daily_plan_export)
        self.assertEqual(restored.daily_plan_template, "focus")
        self.assertTrue(restored.daily_plan_focus_only)
        self.assertEqual(restored.daily_plan_candidate_limit, 8)
        self.assertEqual(restored.market_data_mode, "cache")
        self.assertEqual(restored.market_timeframe_mode, "周线")
        self.assertEqual(restored.market_history_window, "近3年")

    def test_load_app_state_normalizes_risk_profile(self) -> None:
        state_path = self._temp_dir() / "app_state_risk_profile.json"
        state_path.write_text(
            json.dumps({"strategy_risk_profile": "balanced"}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.strategy_risk_profile, "standard")

    def test_load_app_state_falls_back_on_invalid_json(self) -> None:
        state_path = self._temp_dir() / "app_state_invalid.json"
        state_path.write_text("", encoding="utf-8")
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.license_plan, "TRIAL")
        self.assertEqual(restored.ui_theme, "sunrise")
        self.assertEqual(restored.watchlist, [])

    def test_load_app_state_ignores_string_values_for_list_fields(self) -> None:
        state_path = self._temp_dir() / "app_state_string_lists.json"
        state_path.write_text(
            json.dumps(
                {
                    "watchlist": "SHSE.600000",
                    "focus_themes": "人工智能",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.watchlist, [])
        self.assertEqual(restored.focus_themes, [])

    def test_load_app_state_tolerates_invalid_numeric_paper_trading_fields(self) -> None:
        state_path = self._temp_dir() / "app_state_paper_bad_numbers.json"
        state_path.write_text(
            json.dumps(
                {
                    "paper_trading_state": {
                        "enabled": True,
                        "cash": "oops",
                        "total_equity": "bad",
                        "positions": [
                            {
                                "symbol": "SHSE.600000",
                                "stock_id": "600000",
                                "stock_name": "Paper Demo",
                                "quantity": "broken",
                                "available": "broken",
                                "avg_cost": "oops",
                            }
                        ],
                        "ledger": [
                            {
                                "order_id": "SIM00001",
                                "timestamp": "2026-04-13 09:35:00",
                                "symbol": "SHSE.600000",
                                "stock_id": "600000",
                                "stock_name": "Paper Demo",
                                "side": "BUY",
                                "price": "oops",
                                "quantity": "broken",
                                "amount": "bad",
                            }
                        ],
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertTrue(restored.paper_trading_state.enabled)
        self.assertEqual(restored.paper_trading_state.cash, 100000.0)
        self.assertEqual(restored.paper_trading_state.total_equity, 100000.0)
        self.assertEqual(restored.paper_trading_state.positions[0].quantity, 0)
        self.assertEqual(restored.paper_trading_state.positions[0].avg_cost, 0.0)
        self.assertEqual(restored.paper_trading_state.ledger[0].price, 0.0)
        self.assertEqual(restored.paper_trading_state.ledger[0].quantity, 0)

    def test_app_state_roundtrip_handles_large_watchlist(self) -> None:
        state_path = self._temp_dir() / "app_state_large_watchlist.json"
        watchlist = [f"SHSE.{600000 + index:06d}" for index in range(320)]

        save_app_state(state_path, AppState(watchlist=watchlist))
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(len(restored.watchlist), len(watchlist))
        self.assertEqual(restored.watchlist[:3], watchlist[:3])
        self.assertEqual(restored.watchlist[-3:], watchlist[-3:])

    def test_app_state_encrypts_sensitive_broker_credentials(self) -> None:
        state_path = self._temp_dir() / "app_state_broker_secure.json"
        save_app_state(
            state_path,
            AppState(
                broker_profile=BrokerProfile(
                    account_id="demo-account",
                    token="demo-token",
                    strategy_id="demo-strategy",
                    username="demo-user",
                    password="demo-password",
                )
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        raw_payload = json.loads(state_path.read_text(encoding="utf-8"))
        broker_profile = raw_payload["broker_profile"]

        self.assertEqual(broker_profile["account_id"], "demo-account")
        self.assertEqual(broker_profile["strategy_id"], "demo-strategy")
        self.assertEqual(broker_profile["username"], "demo-user")
        self.assertNotEqual(broker_profile["token"], "demo-token")
        self.assertNotEqual(broker_profile["password"], "demo-password")

        restored = load_app_state(state_path)

        self.assertEqual(restored.broker_profile.account_id, "demo-account")
        self.assertEqual(restored.broker_profile.token, "demo-token")
        self.assertEqual(restored.broker_profile.password, "demo-password")

    def test_load_app_state_keeps_plaintext_broker_credentials_compatible(self) -> None:
        state_path = self._temp_dir() / "app_state_broker_legacy.json"
        state_path.write_text(
            json.dumps(
                {
                    "broker_profile": {
                        "account_id": "legacy-account",
                        "token": "legacy-token",
                        "strategy_id": "legacy-strategy",
                        "username": "legacy-user",
                        "password": "legacy-password",
                    }
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.broker_profile.account_id, "legacy-account")
        self.assertEqual(restored.broker_profile.token, "legacy-token")
        self.assertEqual(restored.broker_profile.password, "legacy-password")

    def test_app_state_persists_paper_trading_state(self) -> None:
        state_path = self._temp_dir() / "app_state_paper_trading.json"
        save_app_state(
            state_path,
            AppState(
                paper_trading_state=PaperTradingState(
                    enabled=True,
                    auto_run=True,
                    auto_interval_minutes=7.5,
                    initial_cash=50000.0,
                    cash=42100.0,
                    max_position_pct=0.2,
                    positions=[
                        PaperPosition(
                            symbol="SHSE.600000",
                            stock_id="600000",
                            stock_name="Paper Demo",
                            quantity=1000,
                            available=1000,
                            avg_cost=10.0,
                            current_price=10.6,
                            market_value=10600.0,
                            entry_date="2026-04-13 09:35:00",
                            strategy_name="龙头模型",
                            buy_point="10.00 附近承接",
                            sell_point="11.20 附近止盈",
                            stop_price=9.5,
                            target_price=11.2,
                            rationale="paper demo",
                            unrealized_pnl=600.0,
                            unrealized_pnl_pct=0.06,
                        )
                    ],
                    ledger=[
                        PaperOrderRecord(
                            order_id="SIM00001",
                            timestamp="2026-04-13 09:35:00",
                            symbol="SHSE.600000",
                            stock_id="600000",
                            stock_name="Paper Demo",
                            side="BUY",
                            price=10.0,
                            quantity=1000,
                            amount=10000.0,
                            strategy_name="龙头模型",
                            position_pct=0.2,
                            signal_source="RECLAIM_LONG",
                            buy_point="10.00 附近承接",
                            sell_point="11.20 附近止盈",
                            status="FILLED",
                            note="paper demo",
                            realized_pnl=0.0,
                            realized_pnl_pct=0.0,
                            cumulative_realized_pnl=0.0,
                        )
                    ],
                    equity_curve=[
                        PaperEquityPoint(
                            timestamp="2026-04-13 14:30:00",
                            cash=42100.0,
                            market_value=10600.0,
                            total_equity=52700.0,
                            realized_pnl=1200.0,
                            total_return=0.054,
                            position_count=1,
                        )
                    ],
                    patrol_logs=[
                        PaperPatrolLog(
                            timestamp="2026-04-13 14:30:00",
                            event_type="CYCLE",
                            summary="巡航完成",
                            detail="AI 本轮新开 1 笔",
                            equity=52700.0,
                            total_return=0.054,
                            position_count=1,
                        )
                    ],
                    realized_pnl=1200.0,
                    total_equity=52700.0,
                    total_return=0.054,
                    last_run_at="2026-04-13 14:30:00",
                    last_strategy_note="AI 本轮新开 1 笔",
                    order_sequence=1,
                )
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertTrue(restored.paper_trading_state.enabled)
        self.assertTrue(restored.paper_trading_state.auto_run)
        self.assertAlmostEqual(restored.paper_trading_state.auto_interval_minutes, 7.5)
        self.assertEqual(restored.paper_trading_state.positions[0].strategy_name, "龙头模型")
        self.assertEqual(restored.paper_trading_state.ledger[0].order_id, "SIM00001")
        self.assertEqual(restored.paper_trading_state.equity_curve[0].position_count, 1)
        self.assertEqual(restored.paper_trading_state.patrol_logs[0].event_type, "CYCLE")
        self.assertAlmostEqual(restored.paper_trading_state.total_return, 0.054)

    def test_paper_trading_engine_opens_position_with_best_strategy(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-13",
                close=10.0,
                entry_price=10.0,
                stop_price=9.6,
                target_price=11.0,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=86.0,
                total_score=85.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                primary_strategy="",
                buy_point="10.00 附近承接",
                sell_point="11.00 附近止盈",
                leader_model_score=91.0,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=86.0,
                mainline_continuation_score=74.0,
                mainline_window_score=78.0,
                theme_failure_risk=30.0,
                rationale="leader demo",
            )
        ]

        state = PaperTradingEngine().initialize_state(initial_cash=100000.0, max_position_pct=0.3, auto_interval_minutes=9.0)
        updated = PaperTradingEngine().run_cycle(state, recommendations, as_of="2026-04-13 10:00:00")

        self.assertEqual(len(updated.positions), 1)
        self.assertEqual(len(updated.ledger), 1)
        self.assertEqual(updated.positions[0].strategy_name, "龙头模型")
        self.assertEqual(updated.ledger[0].side, "BUY")
        self.assertGreater(updated.positions[0].quantity, 0)
        self.assertLess(updated.cash, updated.initial_cash)
        self.assertAlmostEqual(updated.auto_interval_minutes, 9.0)
        self.assertGreaterEqual(len(updated.patrol_logs), 2)
        self.assertEqual(updated.patrol_logs[-1].event_type, "CYCLE")
        self.assertIn("本轮实验", updated.last_strategy_note)

    def test_paper_trading_engine_risk_profile_changes_position_size(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Risk Size Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-15",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=86.0,
                total_score=85.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                primary_strategy="掘龙决策",
                buy_point="10.00 附近承接",
                sell_point="11.20 附近止盈",
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=86.0,
                mainline_continuation_score=74.0,
                mainline_window_score=78.0,
                theme_failure_risk=30.0,
                rationale="risk size demo",
            )
        ]

        conservative_state = PaperTradingEngine().initialize_state(initial_cash=100000.0, max_position_pct=0.3)
        aggressive_state = PaperTradingEngine().initialize_state(initial_cash=100000.0, max_position_pct=0.3)
        conservative_updated = PaperTradingEngine().run_cycle(
            conservative_state,
            recommendations,
            as_of="2026-04-15 10:00:00",
            risk_profile="conservative",
        )
        aggressive_updated = PaperTradingEngine().run_cycle(
            aggressive_state,
            recommendations,
            as_of="2026-04-15 10:00:00",
            risk_profile="aggressive",
        )

        self.assertEqual(len(conservative_updated.positions), 1)
        self.assertEqual(len(aggressive_updated.positions), 1)
        self.assertLess(conservative_updated.positions[0].quantity, aggressive_updated.positions[0].quantity)
        self.assertIn("本轮实验", aggressive_updated.last_strategy_note)

    def test_paper_trading_engine_exits_position_when_stop_price_breaks(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="HOLD",
                label="RECLAIM_LONG",
                signal_date="2026-04-13",
                close=9.4,
                entry_price=9.4,
                stop_price=9.5,
                target_price=11.0,
                technical_score=70.0,
                position_score=68.0,
                persistence_score=66.0,
                news_score=62.0,
                leader_score=64.0,
                total_score=69.0,
                theme_name="AI",
                theme_score=74.0,
                theme_rank=1,
                primary_strategy="龙头模型",
                buy_point="10.00 附近承接",
                sell_point="11.00 附近止盈",
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=74.0,
                mainline_continuation_score=62.0,
                mainline_window_score=58.0,
                theme_failure_risk=40.0,
                rationale="stop break demo",
            )
        ]
        state = PaperTradingState(
            enabled=True,
            initial_cash=100000.0,
            cash=90000.0,
            max_position_pct=0.25,
            positions=[
                PaperPosition(
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    quantity=1000,
                    available=1000,
                    avg_cost=10.0,
                    current_price=10.0,
                    market_value=10000.0,
                    entry_date="2026-04-12 10:00:00",
                    strategy_name="龙头模型",
                    buy_point="10.00 附近承接",
                    sell_point="11.00 附近止盈",
                    stop_price=9.5,
                    target_price=11.0,
                    rationale="leader demo",
                )
            ],
            total_equity=100000.0,
        )

        updated = PaperTradingEngine().run_cycle(state, recommendations, as_of="2026-04-13 14:00:00")

        self.assertEqual(len(updated.positions), 0)
        self.assertEqual(updated.ledger[-1].side, "SELL")
        self.assertLess(updated.realized_pnl, 0.0)
        self.assertIn("止损", updated.last_strategy_note or updated.ledger[-1].note)

    def test_paper_trading_engine_does_not_rebuy_symbol_in_same_cycle(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-13",
                close=9.4,
                entry_price=9.4,
                stop_price=9.5,
                target_price=10.6,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=86.0,
                total_score=85.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                primary_strategy="龙头模型",
                buy_point="9.40 附近承接",
                sell_point="10.60 附近止盈",
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=86.0,
                mainline_continuation_score=74.0,
                mainline_window_score=78.0,
                theme_failure_risk=30.0,
                rationale="stop break but still buy rated demo",
            )
        ]
        state = PaperTradingState(
            enabled=True,
            initial_cash=100000.0,
            cash=90000.0,
            max_position_pct=0.25,
            positions=[
                PaperPosition(
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    quantity=1000,
                    available=1000,
                    avg_cost=10.0,
                    current_price=10.0,
                    market_value=10000.0,
                    entry_date="2026-04-12 10:00:00",
                    strategy_name="龙头模型",
                    buy_point="10.00 附近承接",
                    sell_point="11.00 附近止盈",
                    stop_price=9.5,
                    target_price=11.0,
                    rationale="leader demo",
                )
            ],
            total_equity=100000.0,
        )

        updated = PaperTradingEngine().run_cycle(state, recommendations, as_of="2026-04-13 14:00:00")

        self.assertEqual(len(updated.positions), 0)
        self.assertEqual([item.side for item in updated.ledger], ["SELL"])
        self.assertIn("暂缓回补", updated.last_strategy_note)

    def test_paper_trading_engine_appends_equity_curve(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-13",
                close=10.0,
                entry_price=10.0,
                stop_price=9.6,
                target_price=11.0,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=86.0,
                total_score=85.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                primary_strategy="龙头模型",
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=86.0,
                mainline_continuation_score=74.0,
                mainline_window_score=78.0,
                theme_failure_risk=30.0,
                rationale="leader demo",
            )
        ]

        state = PaperTradingEngine().initialize_state(initial_cash=100000.0, max_position_pct=0.3)
        updated = PaperTradingEngine().run_cycle(state, recommendations, as_of="2026-04-13 10:00:00")

        self.assertGreaterEqual(len(updated.equity_curve), 2)
        self.assertEqual(updated.equity_curve[-1].timestamp, "2026-04-13 10:00:00")
        self.assertAlmostEqual(updated.equity_curve[-1].total_equity, updated.total_equity)

    def test_paper_trading_engine_caps_history_buffers_at_500_items(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-13",
                close=10.0,
                entry_price=10.0,
                stop_price=9.6,
                target_price=11.0,
                technical_score=84.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=86.0,
                total_score=85.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                primary_strategy="龙头模型",
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=86.0,
                mainline_continuation_score=74.0,
                mainline_window_score=78.0,
                theme_failure_risk=30.0,
                rationale="leader demo",
            )
        ]
        state = PaperTradingState(
            enabled=True,
            initial_cash=100000.0,
            cash=100000.0,
            max_position_pct=0.25,
            ledger=[
                PaperOrderRecord(
                    order_id=f"SIM{i:05d}",
                    timestamp=f"2026-04-12 09:{i % 60:02d}:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="BUY",
                    price=10.0,
                    quantity=100,
                    amount=1000.0,
                )
                for i in range(505)
            ],
            equity_curve=[
                PaperEquityPoint(
                    timestamp=f"历史{i:03d}",
                    cash=100000.0,
                    market_value=0.0,
                    total_equity=100000.0,
                    realized_pnl=0.0,
                    total_return=0.0,
                    position_count=0,
                )
                for i in range(505)
            ],
            patrol_logs=[
                PaperPatrolLog(
                    timestamp=f"2026-04-12 14:{i % 60:02d}:00",
                    event_type="CYCLE",
                    summary=f"历史巡航 {i}",
                    detail="demo",
                    equity=100000.0,
                    total_return=0.0,
                    position_count=0,
                )
                for i in range(505)
            ],
        )

        updated = PaperTradingEngine().run_cycle(state, recommendations, as_of="2026-04-13 10:05:00")

        self.assertEqual(len(updated.ledger), 500)
        self.assertEqual(len(updated.equity_curve), 500)
        self.assertEqual(len(updated.patrol_logs), 500)
        self.assertEqual(updated.ledger[0].order_id, "SIM00006")
        self.assertEqual(updated.equity_curve[0].timestamp, "历史006")
        self.assertEqual(updated.patrol_logs[0].summary, "历史巡航 7")
        self.assertEqual(updated.equity_curve[-1].timestamp, "2026-04-13 10:05:00")
        self.assertEqual(updated.patrol_logs[-1].event_type, "CYCLE")

    def test_summarize_paper_trading_performance_merges_strategy_aliases(self) -> None:
        state = PaperTradingState(
            enabled=True,
            ledger=[
                PaperOrderRecord(
                    order_id="SIM00001",
                    timestamp="2026-04-13 09:35:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    amount=10000.0,
                    strategy_name="强势接力",
                    position_pct=0.1,
                ),
                PaperOrderRecord(
                    order_id="SIM00002",
                    timestamp="2026-04-13 10:10:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="SELL",
                    price=10.8,
                    quantity=1000,
                    amount=10800.0,
                    strategy_name="擒龙打板",
                    position_pct=0.1,
                    realized_pnl=800.0,
                    cumulative_realized_pnl=800.0,
                ),
            ],
        )

        analytics = summarize_paper_trading_performance(state)

        self.assertEqual(len(analytics["strategy_rows"]), 1)
        self.assertEqual(analytics["strategy_rows"][0]["strategy_name"], "擒龙打板")
        self.assertEqual(analytics["strategy_rows"][0]["sell_count"], 1)
        self.assertEqual(analytics["hold_cycle_sample_count"], 1)
        self.assertAlmostEqual(analytics["avg_hold_days"], 0.02, places=2)
        self.assertEqual(analytics["hold_cycle_note"], "平均持有 0.02 天 / 样本 1")
        self.assertEqual(analytics["hold_cycle"]["strategy_rows"][0]["strategy_name"], "擒龙打板")
        self.assertEqual(analytics["strategy_rows"][0]["avg_hold_days"], 0.02)
        self.assertEqual(analytics["strategy_rows"][0]["hold_sample_count"], 1)
        self.assertEqual(analytics["strategy_rows"][0]["hold_cycle_note"], "平均持有 0.02 天 / 样本 1")

    def test_build_strategy_rotation_snapshot_surfaces_bias_and_sample_count(self) -> None:
        state = PaperTradingState(
            enabled=True,
            initial_cash=100000.0,
            ledger=[
                PaperOrderRecord(
                    order_id="SIM00001",
                    timestamp="2026-04-13 09:35:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    amount=10000.0,
                    strategy_name="龙头模型",
                    position_pct=0.1,
                ),
                PaperOrderRecord(
                    order_id="SIM00002",
                    timestamp="2026-04-13 10:10:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="SELL",
                    price=10.8,
                    quantity=1000,
                    amount=10800.0,
                    strategy_name="龙头模型",
                    position_pct=0.1,
                    realized_pnl=800.0,
                    cumulative_realized_pnl=800.0,
                ),
            ],
        )

        rows = build_strategy_rotation_snapshot(state)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["strategy_name"], "龙头模型")
        self.assertEqual(rows[0]["sample_count"], 2)
        self.assertEqual(rows[0]["bias_label"], "加权")
        self.assertGreater(float(rows[0]["budget_multiplier"]), 1.0)
        self.assertEqual(rows[0]["avg_hold_days"], 0.02)
        self.assertEqual(rows[0]["hold_sample_count"], 1)
        self.assertEqual(rows[0]["hold_cycle_note"], "平均持有 0.02 天 / 样本 1")

    def test_paper_trading_auto_run_respects_interval_and_session(self) -> None:
        state = PaperTradingState(
            enabled=True,
            auto_run=True,
            auto_interval_minutes=10.0,
            last_run_at="2026-04-13 10:00:00",
        )

        self.assertFalse(
            should_auto_run_paper_trading(
                state,
                now=datetime.fromisoformat("2026-04-13 10:05:00"),
                in_session=True,
            )
        )
        self.assertTrue(
            should_auto_run_paper_trading(
                state,
                now=datetime.fromisoformat("2026-04-13 10:10:00"),
                in_session=True,
            )
        )
        self.assertFalse(
            should_auto_run_paper_trading(
                state,
                now=datetime.fromisoformat("2026-04-13 10:20:00"),
                in_session=False,
            )
        )

    def test_export_paper_trading_report_writes_markdown_csv_and_json(self) -> None:
        output_dir = self._temp_dir() / "paper_trading_exports"
        output_dir.mkdir(exist_ok=True)
        state = PaperTradingState(
            enabled=True,
            auto_run=True,
            initial_cash=100000.0,
            cash=89000.0,
            max_position_pct=0.25,
            positions=[
                PaperPosition(
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    quantity=1000,
                    available=1000,
                    avg_cost=10.0,
                    current_price=10.5,
                    market_value=10500.0,
                    entry_date="2026-04-13 10:00:00",
                    strategy_name="龙头模型",
                    buy_point="10.00 承接",
                    sell_point="11.00 止盈",
                    stop_price=9.6,
                    target_price=11.0,
                    rationale="leader demo",
                    unrealized_pnl=500.0,
                    unrealized_pnl_pct=0.05,
                )
            ],
            ledger=[
                PaperOrderRecord(
                    order_id="SIM00001",
                    timestamp="2026-04-13 10:00:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="Leader Demo",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    amount=10000.0,
                    strategy_name="龙头模型",
                    position_pct=0.1,
                    signal_source="RECLAIM_LONG",
                    buy_point="10.00 承接",
                    sell_point="11.00 止盈",
                    status="FILLED",
                    note="leader demo",
                    cumulative_realized_pnl=0.0,
                )
            ],
            equity_curve=[
                PaperEquityPoint(timestamp="初始", cash=100000.0, market_value=0.0, total_equity=100000.0, realized_pnl=0.0, total_return=0.0, position_count=0),
                PaperEquityPoint(timestamp="2026-04-13 10:00:00", cash=89000.0, market_value=10500.0, total_equity=99500.0, realized_pnl=0.0, total_return=-0.005, position_count=1),
            ],
            patrol_logs=[
                PaperPatrolLog(
                    timestamp="2026-04-13 10:00:00",
                    event_type="BUY",
                    summary="Leader Demo 开仓 1000 股",
                    detail="龙头模型 | leader demo",
                    equity=99500.0,
                    total_return=-0.005,
                    position_count=1,
                ),
                PaperPatrolLog(
                    timestamp="2026-04-13 15:00:00",
                    event_type="CYCLE",
                    summary="巡航完成: 卖出 0 笔, 新开 1 笔",
                    detail="AI 本轮新开 1 笔",
                    equity=99500.0,
                    total_return=-0.005,
                    position_count=1,
                ),
            ],
            realized_pnl=0.0,
            total_equity=99500.0,
            total_return=-0.005,
            last_run_at="2026-04-13 10:00:00",
            last_strategy_note="AI 本轮新开 1 笔",
            order_sequence=1,
        )

        artifacts = export_paper_trading_report(state, output_dir=output_dir, exported_at="2026-04-13 15:00:00")
        self.addCleanup(lambda: Path(artifacts.markdown_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.csv_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.json_path).unlink(missing_ok=True))

        markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")
        payload = Path(artifacts.json_path).read_text(encoding="utf-8")

        self.assertTrue(Path(artifacts.csv_path).exists())
        self.assertIn("AI 模拟盘报告", markdown)
        self.assertIn("战法拆解", markdown)
        self.assertIn("巡航日志", markdown)
        self.assertIn("Leader Demo", markdown)
        self.assertIn('"order_id": "SIM00001"', payload)
        self.assertIn('"analytics"', payload)
        self.assertIn('"patrol_logs"', payload)

    def test_daily_pool_builder_boosts_focus_themes(self) -> None:
        rows = [
            ScanRow(
                stock_name="Bank Demo",
                stock_id="600000",
                symbol="SHSE.600000",
                action="BUY",
                label="RECLAIM_LONG",
                score=78,
                close=12.3,
                signal_date="2026-04-05",
                entry_price=12.3,
                stop_price=11.7,
                target_price=13.5,
                reason="bank repair",
                source_path="demo",
            ),
            ScanRow(
                stock_name="Robot Demo",
                stock_id="300024",
                symbol="SZSE.300024",
                action="BUY",
                label="RECLAIM_LONG",
                score=76,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=18.8,
                target_price=22.4,
                reason="robot momentum",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SHSE.600000": [], "SZSE.300024": []}
        summaries = []
        profiles = {
            "SHSE.600000": type("Profile", (), {"stock_id": "600000", "name": "Bank Demo", "industry": "bank", "notes": "bank repair", "is_leader": True})(),
            "SZSE.300024": type("Profile", (), {"stock_id": "300024", "name": "Robot Demo", "industry": "robot", "notes": "robot momentum", "is_leader": False})(),
        }
        aliases = {"robot": ("robot",), "bank": ("bank",)}

        plain_pool = DailyPoolBuilder(stock_profiles=profiles, theme_aliases=aliases).build(
            rows,
            analyses_by_symbol,
            summaries,
            top_n=5,
        )
        boosted_pool = DailyPoolBuilder(
            stock_profiles=profiles,
            theme_aliases=aliases,
            focus_themes=["robot"],
            focus_theme_boost=20.0,
        ).build(rows, analyses_by_symbol, summaries, top_n=5)

        plain_robot = next(item for item in plain_pool if item.stock_id == "300024")
        boosted_robot = next(item for item in boosted_pool if item.stock_id == "300024")

        self.assertEqual(plain_pool[0].stock_id, "600000")
        self.assertGreater(boosted_robot.total_score, plain_robot.total_score)
        self.assertIn("关注题材加权", boosted_robot.rationale)

    def test_daily_pool_builder_populates_strategy_scores(self) -> None:
        rows = [
            ScanRow(
                stock_name="Leader Demo",
                stock_id="600000",
                symbol="SHSE.600000",
                action="BUY",
                label="RECLAIM_LONG",
                score=88,
                close=12.3,
                signal_date="2026-04-05",
                entry_price=12.3,
                stop_price=11.7,
                target_price=13.5,
                reason="主力净流入 龙头修复",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SHSE.600000": []}
        profiles = {
            "SHSE.600000": type(
                "Profile",
                (),
                {"stock_id": "600000", "name": "Leader Demo", "industry": "bank", "notes": "主力净流入", "is_leader": True},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, analyses_by_symbol, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertIn(item.primary_strategy, {"龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"})
        self.assertGreater(item.leader_model_score, 0.0)
        self.assertGreater(item.main_force_score, 0.0)
        self.assertGreater(item.board_attack_score, 0.0)
        self.assertGreater(item.value_recovery_score, 0.0)
        self.assertGreater(item.tail_buy_score, 0.0)
        self.assertGreater(item.one_day_hold_score, 0.0)
        self.assertGreater(item.dragon_decision_score, 0.0)
        self.assertIn(item.stock_pool, {"龙头股", "趋势股", "价值股"})
        self.assertTrue(item.buy_point)
        self.assertTrue(item.sell_point)
        self.assertTrue(item.risk_line)
        self.assertTrue(item.mainline_tag)
        self.assertGreaterEqual(item.mainline_rank, 1)
        self.assertIn(item.mainline_role, {"CORE", "FRONT", "ASSIST", "FOLLOW", "NOISE", "ELIMINATED"})
        self.assertGreater(item.mainline_window_score, 0.0)
        self.assertGreater(item.leader_position_score, 0.0)

    def test_daily_pool_builder_assigns_value_pool_when_repair_signal_is_strong(self) -> None:
        rows = [
            ScanRow(
                stock_name="Value Demo",
                stock_id="000001",
                symbol="SZSE.000001",
                action="BUY",
                label="RECLAIM_LONG",
                score=71,
                close=10.0,
                signal_date="2026-04-05",
                entry_price=9.9,
                stop_price=9.3,
                target_price=10.8,
                reason="低位 回踩 修复 价值 反抽",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SZSE.000001": []}
        pool = DailyPoolBuilder().build(rows, analyses_by_symbol, [], top_n=5)

        self.assertEqual(len(pool), 1)
        self.assertEqual(pool[0].stock_pool, "价值股")
        self.assertIn("试仓", pool[0].buy_point)
        self.assertIn("放弃博弈", pool[0].sell_point)

    def test_daily_pool_builder_populates_user_focus_fields(self) -> None:
        rows = [
            ScanRow(
                stock_name="Focus Demo",
                stock_id="300001",
                symbol="SZSE.300001",
                action="BUY",
                label="RECLAIM_LONG",
                score=86,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=18.9,
                target_price=22.8,
                reason="主力 净流入 回封 突破",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SZSE.300001": []}
        profiles = {
            "SZSE.300001": type(
                "Profile",
                (),
                {"stock_id": "300001", "name": "Focus Demo", "industry": "AI", "notes": "主线前排", "is_leader": True},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, analyses_by_symbol, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertGreater(item.confidence_score, 0.0)
        self.assertGreater(item.execution_readiness, 0.0)
        self.assertGreater(item.timeliness_score, 0.0)
        self.assertTrue(item.opportunity_tier)
        self.assertTrue(item.next_focus)
        self.assertTrue(item.invalidation_reason)

    def test_daily_pool_builder_prefers_stronger_backtest_quality(self) -> None:
        rows = [
            ScanRow(
                stock_name="Strong Demo",
                stock_id="300001",
                symbol="SZSE.300001",
                action="BUY",
                label="RECLAIM_LONG",
                score=82,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=19.0,
                target_price=22.5,
                reason="主线回流",
                source_path="demo",
            ),
            ScanRow(
                stock_name="Weak Demo",
                stock_id="300002",
                symbol="SZSE.300002",
                action="BUY",
                label="RECLAIM_LONG",
                score=84,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=19.0,
                target_price=22.5,
                reason="主线回流",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SZSE.300001": [], "SZSE.300002": []}
        profiles = {
            "SZSE.300001": type("Profile", (), {"stock_id": "300001", "name": "Strong Demo", "industry": "AI", "notes": "主线前排", "is_leader": True})(),
            "SZSE.300002": type("Profile", (), {"stock_id": "300002", "name": "Weak Demo", "industry": "AI", "notes": "主线前排", "is_leader": True})(),
        }
        summaries = [
            SymbolBacktestSummary(symbol="SZSE.300001", trades=8, total_return=0.28, max_drawdown=0.06, win_rate=0.68, ending_equity=128000.0),
            SymbolBacktestSummary(symbol="SZSE.300002", trades=3, total_return=-0.02, max_drawdown=0.19, win_rate=0.34, ending_equity=98000.0),
        ]

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, analyses_by_symbol, summaries, top_n=5)

        self.assertEqual(pool[0].stock_name, "Strong Demo")
        self.assertGreater(pool[0].backtest_quality_score, pool[1].backtest_quality_score)

    def test_daily_pool_builder_risk_profile_changes_opportunity_tier(self) -> None:
        rows = [
            ScanRow(
                stock_name="Risk Demo",
                stock_id="300003",
                symbol="SZSE.300003",
                action="BUY",
                label="RECLAIM_LONG",
                score=84,
                close=20.0,
                signal_date=date.today().isoformat(),
                entry_price=20.0,
                stop_price=19.0,
                target_price=21.4,
                reason="主线回流 主力承接",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {
            "SZSE.300003": [
                DailyAnalysis(
                    date=date.today().isoformat(),
                    symbol="SZSE.300003",
                    close=20.0,
                    atr=0.8,
                    ma_fast=19.8,
                    ma_slow=19.4,
                    breakout_level=19.5,
                    volume_ratio=1.2,
                    upper_shadow_pct=1.0,
                    close_location=0.75,
                    label="RECLAIM_LONG",
                    score=84,
                    reason="主线回流",
                    entry_price=20.0,
                    stop_price=19.0,
                    target_price=21.4,
                )
            ]
        }
        profiles = {
            "SZSE.300003": type("Profile", (), {"stock_id": "300003", "name": "Risk Demo", "industry": "AI", "notes": "主线前排", "is_leader": True})(),
        }

        as_of = datetime(2026, 4, 6).date()
        conservative_pool = DailyPoolBuilder(stock_profiles=profiles, risk_profile="conservative").build(
            rows,
            analyses_by_symbol,
            [],
            top_n=5,
            as_of=as_of,
        )
        aggressive_pool = DailyPoolBuilder(stock_profiles=profiles, risk_profile="aggressive").build(
            rows,
            analyses_by_symbol,
            [],
            top_n=5,
            as_of=as_of,
        )

        self.assertEqual(conservative_pool[0].opportunity_tier, "风险回避")
        self.assertEqual(aggressive_pool[0].opportunity_tier, "跟踪确认")

    def test_daily_pool_builder_applies_strategy_rotation_bias(self) -> None:
        rows = [
            ScanRow(
                stock_name="Leader Demo",
                stock_id="300001",
                symbol="SZSE.300001",
                action="BUY",
                label="RECLAIM_LONG",
                score=80,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=19.0,
                target_price=22.0,
                reason="主线 龙头 回封",
                source_path="demo",
            )
        ]
        analyses_by_symbol = {"SZSE.300001": []}
        profiles = {
            "SZSE.300001": type("Profile", (), {"stock_id": "300001", "name": "Leader Demo", "industry": "AI", "notes": "主线前排", "is_leader": True})(),
        }

        plain_pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, analyses_by_symbol, [], top_n=5)
        boosted_pool = DailyPoolBuilder(
            stock_profiles=profiles,
            strategy_bias_by_name={"龙头模型": 0.4},
        ).build(rows, analyses_by_symbol, [], top_n=5)

        self.assertGreater(boosted_pool[0].leader_model_score, plain_pool[0].leader_model_score)

    def test_daily_pool_builder_can_promote_one_day_hold_strategy(self) -> None:
        rows = [
            ScanRow(
                stock_name="Overnight Demo",
                stock_id="300888",
                symbol="SZSE.300888",
                action="BUY",
                label="RECLAIM_LONG",
                score=89,
                close=18.6,
                signal_date="2026-04-05",
                entry_price=18.6,
                stop_price=18.0,
                target_price=19.7,
                reason="次日转强 竞价高开 一日持股 隔日兑现",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SZSE.300888": []}
        profiles = {
            "SZSE.300888": type(
                "Profile",
                (),
                {"stock_id": "300888", "name": "Overnight Demo", "industry": "AI", "notes": "次日博弈", "is_leader": False},
            )(),
        }
        builder = DailyPoolBuilder(stock_profiles=profiles)

        pool = builder.build(rows, analyses_by_symbol, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertEqual(item.primary_strategy, "一日持股法")
        self.assertGreater(item.one_day_hold_score, item.value_recovery_score)
        self.assertIn("隔日", item.buy_point)
        self.assertIn("次日", item.sell_point)

    def test_daily_pool_builder_can_promote_tail_buy_strategy(self) -> None:
        rows = [
            ScanRow(
                stock_name="Tail Demo",
                stock_id="301188",
                symbol="SZSE.301188",
                action="BUY",
                label="RECLAIM_LONG",
                score=87,
                close=15.8,
                signal_date="2026-04-05",
                entry_price=15.8,
                stop_price=15.4,
                target_price=16.3,
                reason="尾盘买入 尾盘回流 次日开盘卖 14:30 后确认",
                source_path="demo",
            ),
        ]
        analyses_by_symbol = {"SZSE.301188": []}
        profiles = {
            "SZSE.301188": type(
                "Profile",
                (),
                {"stock_id": "301188", "name": "Tail Demo", "industry": "机器人", "notes": "尾盘抢筹", "is_leader": False},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, analyses_by_symbol, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertEqual(item.primary_strategy, "尾盘买入法")
        self.assertGreater(item.tail_buy_score, item.value_recovery_score)
        self.assertIn("14:30", item.buy_point)
        self.assertIn("次日开盘", item.sell_point)

    def test_decision_engine_applies_pool_specific_trade_plan(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Leader Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=12.3,
                entry_price=12.3,
                stop_price=11.9,
                target_price=14.2,
                technical_score=88.0,
                position_score=82.0,
                persistence_score=81.0,
                news_score=76.0,
                leader_score=90.0,
                total_score=86.0,
                theme_name="bank",
                theme_score=82.0,
                theme_rank=1,
                leader_level="CORE_LEADER",
                primary_strategy="龙头模型",
                stock_pool="龙头股",
                pool_score=91.0,
                buy_point="放量突破后在 12.30 附近分批介入",
                add_point="回封承接不破 12.10 加仓",
                sell_point="冲高到 14.20 附近分批止盈",
                risk_line="跌破 11.90 离场",
                dragon_decision_score=92.0,
                rationale="leader demo",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="Value Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.4,
                target_price=10.8,
                technical_score=72.0,
                position_score=84.0,
                persistence_score=68.0,
                news_score=60.0,
                leader_score=55.0,
                total_score=74.0,
                theme_name="repair",
                theme_score=70.0,
                theme_rank=2,
                leader_level="FOLLOWER",
                primary_strategy="价值低吸",
                stock_pool="价值股",
                pool_score=85.0,
                buy_point="超跌修复确认后在 10.00 附近试仓",
                add_point="二次回踩不破 9.80 再补仓",
                sell_point="修复到 10.80 附近落袋",
                risk_line="跌破 9.40 放弃修复",
                dragon_decision_score=80.0,
                rationale="value demo",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 2)
        leader_decision = next(item for item in plan.decisions if item.stock_id == "600000")
        value_decision = next(item for item in plan.decisions if item.stock_id == "000001")
        self.assertEqual(leader_decision.stock_pool, "龙头股")
        self.assertEqual(value_decision.stock_pool, "价值股")
        self.assertGreater(leader_decision.suggested_budget, value_decision.suggested_budget)
        self.assertIn("买点", leader_decision.rationale)
        self.assertIn("股票池分布", " ".join(plan.notes))

    def test_decision_engine_carries_user_focus_fields_into_trade_plan(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Focus Leader",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=12.3,
                entry_price=12.3,
                stop_price=11.9,
                target_price=14.2,
                technical_score=88.0,
                position_score=82.0,
                persistence_score=81.0,
                news_score=76.0,
                leader_score=90.0,
                total_score=86.0,
                theme_name="bank",
                theme_score=82.0,
                theme_rank=1,
                leader_level="CORE_LEADER",
                primary_strategy="龙头模型",
                stock_pool="龙头股",
                pool_score=91.0,
                buy_point="放量突破后在 12.30 附近分批介入",
                add_point="回封承接不破 12.10 加仓",
                sell_point="冲高到 14.20 附近分批止盈",
                risk_line="跌破 11.90 离场",
                dragon_decision_score=92.0,
                mainline_tag="bank",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_window_score=83.0,
                theme_failure_risk=28.0,
                opportunity_tier="优先处理",
                execution_readiness=81.0,
                next_focus="盯回封强度和量能放大。",
                rationale="focus demo",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertEqual(plan.decisions[0].opportunity_tier, "优先处理")
        self.assertEqual(plan.decisions[0].execution_readiness, 81.0)
        self.assertIn("量能放大", plan.decisions[0].next_focus)
        self.assertTrue(any("下一步" in note for note in plan.notes))

    def test_daily_plan_export_applies_template_and_focus_filter(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Bank Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=12.3,
                entry_price=12.3,
                stop_price=11.7,
                target_price=13.5,
                technical_score=82.0,
                position_score=80.0,
                persistence_score=78.0,
                news_score=70.0,
                leader_score=86.0,
                total_score=83.0,
                theme_name="bank",
                theme_score=81.0,
                theme_rank=1,
                leader_level="CORE_LEADER",
                rationale="bank demo",
            ),
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="Robot Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=20.0,
                entry_price=20.0,
                stop_price=18.8,
                target_price=22.4,
                technical_score=75.0,
                position_score=74.0,
                persistence_score=72.0,
                news_score=68.0,
                leader_score=66.0,
                total_score=76.0,
                theme_name="robot",
                theme_score=79.0,
                theme_rank=2,
                leader_level="ACTIVE_LEADER",
                rationale="robot demo",
            ),
        ]
        trade_plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)
        output_dir = self._temp_dir() / "plan_template_exports"
        output_dir.mkdir(exist_ok=True)

        artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=recommendations,
            trade_plan=trade_plan,
            holdings=[],
            focus_themes=["robot"],
            license_plan="ENTERPRISE",
            template_name="focus",
            focus_only=True,
            candidate_limit=5,
        )
        self.addCleanup(lambda: Path(artifacts.markdown_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.csv_path).unlink(missing_ok=True))
        self.addCleanup(lambda: Path(artifacts.json_path).unlink(missing_ok=True))

        markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")
        payload = Path(artifacts.json_path).read_text(encoding="utf-8")

        self.assertIn("报告模板: focus", markdown)
        self.assertIn("仅关注题材: 是", markdown)
        self.assertIn("Robot Demo", markdown)
        self.assertNotIn("Bank Demo (600000 / SHSE.600000)", markdown)
        self.assertIn('"template_name": "focus"', payload)

    def test_decision_engine_limits_new_positions_to_top_themes(self) -> None:
        pool = [
            type("Rec", (), {
                "symbol": "SHSE.600000",
                "stock_id": "600000",
                "stock_name": "浦发银行",
                "action": "BUY",
                "label": "RECLAIM_LONG",
                "signal_date": "2026-04-05",
                "close": 12.3,
                "entry_price": 12.3,
                "stop_price": 11.7,
                "target_price": 13.5,
                "technical_score": 88.0,
                "position_score": 82.0,
                "persistence_score": 80.0,
                "news_score": 76.0,
                "leader_score": 85.0,
                "total_score": 86.0,
                "theme_name": "银行",
                "theme_score": 82.0,
                "theme_rank": 1,
                "leader_level": "CORE_LEADER",
                "catalyst": "银行修复",
                "rationale": "demo",
            })(),
            type("Rec", (), {
                "symbol": "SZSE.000001",
                "stock_id": "000001",
                "stock_name": "平安银行",
                "action": "BUY",
                "label": "RECLAIM_LONG",
                "signal_date": "2026-04-05",
                "close": 10.1,
                "entry_price": 10.1,
                "stop_price": 9.7,
                "target_price": 11.2,
                "technical_score": 82.0,
                "position_score": 80.0,
                "persistence_score": 76.0,
                "news_score": 70.0,
                "leader_score": 78.0,
                "total_score": 79.0,
                "theme_name": "冷门主题",
                "theme_score": 55.0,
                "theme_rank": 6,
                "leader_level": "FOLLOWER",
                "catalyst": "弱催化",
                "rationale": "demo",
            })(),
        ]

        plan = DecisionEngine().build_plan(pool, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertEqual(plan.decisions[0].stock_id, "600000")

    def test_build_overview_command_snapshot_uses_direct_trading_language(self) -> None:
        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-05",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=11.0,
            technical_score=82.0,
            position_score=84.0,
            persistence_score=80.0,
            news_score=76.0,
            leader_score=78.0,
            total_score=83.0,
            theme_name="银行修复",
            stock_pool="趋势股",
            buy_point="回踩 10.00 后承接不弱再买",
            risk_line="跌破 9.60 先撤",
        )

        snapshot = build_overview_command_snapshot(
            pool=[recommendation],
            recommendations=[recommendation],
            execution_status_by_symbol={},
            market_data_source="cache",
            last_market_success_at="2026-04-06 20:40:00",
            last_market_error="",
            last_job_status="success",
            last_job_name="daily_pool",
            last_job_finished_at="2026-04-06 20:39:00",
            order_submission_log=[],
        )

        self.assertIn("今日主线", snapshot["command"])
        self.assertIn("总评", snapshot["command"])
        self.assertIn("结论", snapshot["command"])
        self.assertIn("防切换", snapshot["command"])
        self.assertIn("买点", snapshot["command"])
        self.assertIn("持仓怎么处理", snapshot["execution"])
        self.assertIn("本地缓存", snapshot["command"])

    def test_ui_refresh_compact_mainline_text_keeps_scan_friendly_summary(self) -> None:
        from quant_hunter import ui_refresh

        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-05",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=11.0,
            technical_score=82.0,
            position_score=84.0,
            persistence_score=80.0,
            news_score=76.0,
            leader_score=78.0,
            total_score=83.0,
            theme_name="银行修复",
            mainline_tag="银行修复",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=78.0,
            mainline_risk_flag="低",
        )

        text = ui_refresh._compact_mainline_text(recommendation)

        self.assertIn("继续跟", text)
        self.assertIn("银行修复", text)
        self.assertIn("核心龙头", text)
        self.assertIn("第1位", text)
        self.assertIn("窗78.0", text)
        self.assertIn("风低", text)

    def test_build_market_text_snapshot_surfaces_buy_hold_reduce_sell_points(self) -> None:
        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-05",
            close=10.0,
            entry_price=10.0,
            stop_price=9.5,
            target_price=11.2,
            technical_score=82.0,
            position_score=84.0,
            persistence_score=80.0,
            news_score=76.0,
            leader_score=78.0,
            total_score=83.0,
            theme_name="银行修复",
            stock_pool="龙头股",
            buy_point="10.00 上方放量再建仓",
            add_point="10.40 放量再加仓",
            sell_point="接近 11.20 分批减仓",
            risk_line="跌破 9.50 直接止损",
            catalyst="板块修复加速",
        )
        market_snapshot = SimpleNamespace(
            heat_score=82.0,
            pct_change=1.8,
            main_inflow=560000000.0,
            turnover=4.2,
            amount=1280000000.0,
        )

        snapshot = build_market_text_snapshot(
            market_snapshot,
            recommendation,
            latest_signal=None,
            display_action_fn=lambda value: value,
            display_label_fn=lambda value: value,
        )

        self.assertIn("持仓与大盘", snapshot["capital_text"])
        self.assertIn("大盘结论", snapshot["capital_text"])
        self.assertIn("建仓买点", snapshot["decision_text"])
        self.assertIn("减仓卖点", snapshot["decision_text"])
        self.assertIn("消息催化", snapshot["decision_text"])
        self.assertEqual(snapshot["decision_headline"], "BUY")

    def test_decision_engine_filters_out_high_risk_non_mainline_buy(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Noise Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.5,
                entry_price=10.5,
                stop_price=9.9,
                target_price=11.6,
                technical_score=88.0,
                position_score=82.0,
                persistence_score=80.0,
                news_score=76.0,
                leader_score=78.0,
                total_score=89.0,
                theme_name="AI",
                theme_score=85.0,
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=4,
                mainline_role="NOISE",
                mainline_strength_score=84.0,
                mainline_window_score=42.0,
                theme_failure_risk=83.0,
                dragon_decision_score=91.0,
                rationale="noise demo",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="Core Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=79.0,
                position_score=81.0,
                persistence_score=77.0,
                news_score=74.0,
                leader_score=83.0,
                total_score=82.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_window_score=78.0,
                theme_failure_risk=36.0,
                dragon_decision_score=86.0,
                rationale="core demo",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertEqual(plan.decisions[0].stock_id, "000001")
        self.assertTrue(any("主线" in note for note in plan.notes))

    def test_decision_engine_reduces_position_when_mainline_eliminated(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Drop Demo",
                action="HOLD",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=12.0,
                entry_price=12.0,
                stop_price=11.2,
                target_price=13.5,
                technical_score=76.0,
                position_score=70.0,
                persistence_score=68.0,
                news_score=58.0,
                leader_score=60.0,
                total_score=71.0,
                theme_name="机器人",
                theme_score=70.0,
                theme_rank=5,
                mainline_tag="机器人",
                mainline_rank=5,
                mainline_role="ELIMINATED",
                mainline_strength_score=58.0,
                mainline_window_score=40.0,
                theme_failure_risk=86.0,
                rationale="drop demo",
            )
        ]
        holdings = [
            HoldingRecord(
                symbol="SHSE.600000",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=12000.0,
            )
        ]

        plan = DecisionEngine().build_plan(recommendations, holdings, available_cash=50000, max_picks=5)

        self.assertEqual(len(plan.position_advice), 1)
        self.assertEqual(plan.position_advice[0].action, "REDUCE")
        self.assertIn("主线", plan.position_advice[0].rationale)

    def test_ui_refresh_mainline_gate_text_formats_core_fields(self) -> None:
        from quant_hunter import ui_refresh

        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="Gate Demo",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-05",
            close=10.0,
            entry_price=10.0,
            stop_price=9.5,
            target_price=11.2,
            technical_score=79.0,
            position_score=81.0,
            persistence_score=77.0,
            news_score=74.0,
            leader_score=83.0,
            total_score=82.0,
            theme_name="AI",
            theme_score=84.0,
            theme_rank=1,
            mainline_tag="AI",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=78.0,
            mainline_risk_flag="低",
            rationale="gate demo",
        )

        gate_text = ui_refresh._mainline_gate_text(recommendation)

        self.assertIn("第 1 位", gate_text)
        self.assertIn("核心龙头", gate_text)
        self.assertIn("窗口 78.0", gate_text)
        self.assertIn("风险 低", gate_text)

    def test_ui_refresh_daily_pool_row_compacts_table_text(self) -> None:
        from quant_hunter import ui_refresh

        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-10",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=11.0,
            technical_score=82.0,
            position_score=84.0,
            persistence_score=80.0,
            news_score=76.0,
            leader_score=78.0,
            total_score=83.0,
            theme_name="银行修复",
            theme_score=84.0,
            theme_rank=1,
            mainline_tag="银行修复",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=78.0,
            mainline_risk_flag="低",
            primary_strategy="掘龙决策",
            leader_level="CORE_LEADER",
            stock_pool="趋势股",
            pool_score=81.0,
            buy_point="回踩 10.00 承接",
            sell_point="冲高 11.00 分批走",
            catalyst="资金回流与板块修复催化",
            rationale="主线延续，适合短线扫读",
        )

        window = SimpleNamespace(_display_leader_level=lambda value: "核心龙头")

        self.assertEqual(ui_refresh._compact_daily_pool_status("已送审"), "送审")
        self.assertEqual(ui_refresh._compact_daily_pool_role("CORE"), "核心")
        self.assertEqual(ui_refresh._compact_daily_pool_action("BUY"), "买")
        self.assertEqual(ui_refresh._compact_daily_pool_strategy("掘龙决策"), "掘龙")
        self.assertEqual(ui_refresh._compact_daily_pool_date("2026-04-10"), "04-10")
        self.assertEqual(ui_refresh._shorten_daily_pool_text("资金回流与板块修复催化", 6), "资金回流与…")

        tooltip = ui_refresh._daily_pool_row_tooltip(window, recommendation, "已送审")

        self.assertIn("状态：已送审", tooltip)
        self.assertIn("主线：银行修复 | 第 1 位 | 核心龙头", tooltip)
        self.assertIn("策略：掘龙决策 | 级别：核心龙头 | 总分：83.0", tooltip)
        self.assertIn("股池：趋势股 | 池分：81.0 | 消息：76.0", tooltip)
        self.assertIn("买卖点：回踩 10.00 承接 / 冲高 11.00 分批走", tooltip)
        self.assertIn("催化：资金回流与板块修复催化", tooltip)
        self.assertIn("理由：主线延续，适合短线扫读", tooltip)

    def test_daily_pool_tooltip_surfaces_one_day_hold_grade(self) -> None:
        from quant_hunter import ui_refresh

        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-10",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            leader_level="CORE_LEADER",
            primary_strategy="一日持股法",
            stock_pool="趋势股",
            pool_score=88.0,
            buy_point="竞价转强后在 10.00 附近跟随",
            sell_point="次日冲高 3% 至 5% 优先兑现",
            one_day_hold_score=88.0,
            execution_readiness=82.0,
            mainline_risk_flag="低",
            catalyst="隔日博弈催化",
            rationale="适合隔日节奏",
        )

        window = SimpleNamespace(_display_leader_level=lambda value: "核心龙头")
        tooltip = ui_refresh._daily_pool_row_tooltip(window, recommendation, "已送审")

        self.assertIn("隔日博弈等级：强博弈", tooltip)

    def test_refresh_recommend_summary_cards_stays_compact_for_intraday_scan(self) -> None:
        from quant_hunter import ui_refresh

        class DummyCard:
            def __init__(self) -> None:
                self.data = None

            def set_data(self, title, value) -> None:
                self.data = (title, value)

        window = SimpleNamespace(
            daily_pool_rows=[
                SimpleNamespace(
                    stock_name="浦发银行",
                    mainline_role="CORE",
                    mainline_rank=1,
                    mainline_window_score=78.0,
                    mainline_risk_flag="低",
                    mainline_tag="AI",
                    theme_name="AI",
                )
            ],
            recommend_summary_cards={key: DummyCard() for key in ("logic", "plan", "pulse", "holding")},
            _recommend_execution_summary=lambda _plan: {"reviewing": 1, "submitted": 2, "failed": 0, "pending": 3},
        )
        plan = SimpleNamespace(
            decisions=[SimpleNamespace(stock_name="浦发银行")],
            notes=["主线回流"],
            market_pulse=SimpleNamespace(
                sentiment_score=72.1,
                sentiment_label="偏强",
                market_regime="修复",
                risk_level="中",
            ),
        )

        ui_refresh.refresh_recommend_summary_cards(window, plan)

        self.assertEqual(window.recommend_summary_cards["plan"].data[0], "计划 1 / 送审 2")
        self.assertEqual(window.recommend_summary_cards["logic"].data[0], "继续跟")
        self.assertIn("核心龙头", window.recommend_summary_cards["logic"].data[1])
        self.assertIn("窗78.0", window.recommend_summary_cards["logic"].data[1])
        self.assertIn("待执行 3", window.recommend_summary_cards["holding"].data[0])
        self.assertIn("继续跟", window.recommend_summary_cards["holding"].data[1])
        self.assertIn("送审 2", window.recommend_summary_cards["holding"].data[1])

    def test_refresh_recommend_summary_cards_surfaces_one_day_hold_grade(self) -> None:
        from quant_hunter import ui_refresh

        class DummyCard:
            def __init__(self) -> None:
                self.data = None

            def set_data(self, title, value) -> None:
                self.data = (title, value)

        window = SimpleNamespace(
            daily_pool_rows=[
                RecommendationRow(
                    symbol="SZSE.300001",
                    stock_id="300001",
                    stock_name="一日样本",
                    action="BUY",
                    label="RECLAIM_LONG",
                    signal_date="2026-04-06",
                    close=10.0,
                    entry_price=10.0,
                    stop_price=9.72,
                    target_price=10.55,
                    technical_score=86.0,
                    position_score=76.0,
                    persistence_score=80.0,
                    news_score=78.0,
                    leader_score=88.0,
                    total_score=84.0,
                    theme_name="机器人",
                    theme_rank=1,
                    mainline_tag="机器人",
                    mainline_role="CORE",
                    mainline_window_score=84.0,
                    mainline_risk_flag="低",
                    stock_pool="趋势股",
                    primary_strategy="一日持股法",
                    one_day_hold_score=88.0,
                    execution_readiness=82.0,
                )
            ],
            recommend_summary_cards={key: DummyCard() for key in ("logic", "plan", "pulse", "holding")},
            _recommend_execution_summary=lambda _plan: {"reviewing": 1, "submitted": 2, "failed": 0, "pending": 3},
        )
        plan = SimpleNamespace(
            decisions=[SimpleNamespace(stock_name="一日样本")],
            notes=["隔日优先兑现"],
            market_pulse=SimpleNamespace(
                sentiment_score=74.0,
                sentiment_label="偏强",
                market_regime="修复",
                risk_level="中",
            ),
        )

        ui_refresh.refresh_recommend_summary_cards(window, plan)

        self.assertIn("隔日 强博弈", window.recommend_summary_cards["plan"].data[1])
        self.assertIn("隔日 强博弈", window.recommend_summary_cards["holding"].data[1])

    def test_refresh_recommend_summary_cards_surfaces_tail_buy_runtime_phase(self) -> None:
        from quant_hunter import ui_refresh

        class DummyCard:
            def __init__(self) -> None:
                self.data = None

            def set_data(self, title, value) -> None:
                self.data = (title, value)

        window = SimpleNamespace(
            daily_pool_rows=[
                RecommendationRow(
                    symbol="SZSE.301188",
                    stock_id="301188",
                    stock_name="尾盘样本",
                    action="BUY",
                    label="RECLAIM_LONG",
                    signal_date="2026-04-06",
                    close=15.8,
                    entry_price=15.8,
                    stop_price=15.4,
                    target_price=16.3,
                    technical_score=84.0,
                    position_score=74.0,
                    persistence_score=79.0,
                    news_score=75.0,
                    leader_score=77.0,
                    total_score=83.0,
                    theme_name="机器人",
                    theme_rank=1,
                    mainline_tag="机器人",
                    mainline_role="FRONT",
                    mainline_window_score=80.0,
                    mainline_risk_flag="低",
                    stock_pool="趋势股",
                    primary_strategy="尾盘买入法",
                    tail_buy_score=89.0,
                    execution_readiness=80.0,
                )
            ],
            recommend_summary_cards={key: DummyCard() for key in ("logic", "plan", "pulse", "holding")},
            _recommend_execution_summary=lambda _plan: {"reviewing": 1, "submitted": 2, "failed": 0, "pending": 3},
        )
        plan = SimpleNamespace(
            decisions=[SimpleNamespace(stock_name="尾盘样本")],
            notes=["尾盘确认后隔夜，次日开盘优先兑现"],
            market_pulse=SimpleNamespace(
                sentiment_score=74.0,
                sentiment_label="偏强",
                market_regime="修复",
                risk_level="中",
            ),
        )

        with patch.object(ui_refresh, "tail_buy_runtime_status", return_value=("尾盘执行窗", "回流与承接共振时再试仓，准备隔夜但不追拉升。")):
            ui_refresh.refresh_recommend_summary_cards(window, plan)

        self.assertIn("尾盘 尾盘执行窗", window.recommend_summary_cards["plan"].data[1])
        self.assertIn("尾盘 尾盘执行窗", window.recommend_summary_cards["holding"].data[1])

    def test_ui_refresh_order_risk_lamp_flags_blockers_and_position_gaps(self) -> None:
        from quant_hunter import ui_refresh

        recommendation = RecommendationRow(
            symbol="SHSE.600001",
            stock_id="600001",
            stock_name="Risk Demo",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-05",
            close=10.0,
            entry_price=10.0,
            stop_price=9.5,
            target_price=11.2,
            technical_score=79.0,
            position_score=81.0,
            persistence_score=77.0,
            news_score=74.0,
            leader_score=83.0,
            total_score=82.0,
            theme_name="AI",
            theme_score=84.0,
            theme_rank=1,
            mainline_tag="AI",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=78.0,
            mainline_risk_flag="低",
            rationale="risk demo",
        )
        blocker_window = SimpleNamespace(
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600001",
                    quantity=100,
                    available=40,
                    cost_price=9.8,
                    market_value=1000.0,
                )
            ],
            last_broker_execution_summary={"blockers": ["主线审查未通过"], "warnings": []},
        )

        oversell = ui_refresh._order_risk_lamp_text(
            blocker_window,
            broker_module.OrderIntent(
                symbol="SHSE.600001",
                side="SELL",
                price=10.0,
                quantity=60,
                stop_price=9.5,
                target_price=11.2,
                signal_date="计划股",
                reason="risk demo",
            ),
            recommendation=recommendation,
            details={"checks": []},
            summary=blocker_window.last_broker_execution_summary,
        )
        missing = ui_refresh._order_risk_lamp_text(
            SimpleNamespace(holdings=[], last_broker_execution_summary={}),
            broker_module.OrderIntent(
                symbol="SHSE.600002",
                side="SELL",
                price=10.0,
                quantity=60,
                stop_price=9.5,
                target_price=11.2,
                signal_date="计划股",
                reason="risk demo",
            ),
            recommendation=None,
            details={"checks": []},
            summary={},
        )
        blocked = ui_refresh._order_risk_lamp_text(
            blocker_window,
            broker_module.OrderIntent(
                symbol="SHSE.600001",
                side="BUY",
                price=10.0,
                quantity=60,
                stop_price=9.5,
                target_price=11.2,
                signal_date="计划股",
                reason="risk demo",
            ),
            recommendation=recommendation,
            details={"checks": []},
            summary=blocker_window.last_broker_execution_summary,
        )

        self.assertTrue(oversell.startswith("红灯"))
        self.assertIn("超卖", oversell)
        self.assertIn("缺持仓", missing)
        self.assertIn("阻塞", blocked)

    def test_broker_focus_action_helpers_return_direct_next_step_guidance(self) -> None:
        module = importlib.import_module("app_qt")
        window = SimpleNamespace()

        buy_intent = OrderIntent(
            symbol="SHSE.600001",
            side="BUY",
            price=10.0,
            quantity=100,
            stop_price=9.5,
            target_price=11.2,
            signal_date="计划股",
            reason="buy demo",
        )
        buy_label = module.QuantHunterWindow._broker_focus_action_label(
            window,
            buy_intent,
            "绿灯",
            blockers=[],
            warnings=[],
            preview_row=None,
            allowed=True,
        )
        buy_hint = module.QuantHunterWindow._broker_focus_action_hint(
            window,
            buy_intent,
            "绿灯",
            blockers=[],
            warnings=[],
            preview_row=None,
            allowed=True,
        )

        sell_intent = OrderIntent(
            symbol="SHSE.600002",
            side="SELL",
            price=10.0,
            quantity=120,
            stop_price=9.5,
            target_price=11.2,
            signal_date="计划股",
            reason="sell demo",
        )
        sell_label = module.QuantHunterWindow._broker_focus_action_label(
            window,
            sell_intent,
            "红灯",
            blockers=[],
            warnings=[],
            preview_row={"status": "超卖"},
            allowed=False,
        )
        sell_hint = module.QuantHunterWindow._broker_focus_action_hint(
            window,
            sell_intent,
            "红灯",
            blockers=[],
            warnings=[],
            preview_row={"status": "超卖"},
            allowed=False,
        )
        risk_summary = module.QuantHunterWindow._broker_focus_risk_summary(
            window,
            sell_intent,
            {"checks": []},
            blockers=[],
            warnings=[],
            preview_row={"status": "超卖"},
            available_qty=40,
        )

        self.assertEqual(buy_label, "继续确认买入")
        self.assertIn("优先确认前排主线", buy_hint)
        self.assertEqual(sell_label, "先改数量")
        self.assertIn("先改数量再提交", sell_hint)
        self.assertEqual(risk_summary, "阻塞项：卖出数量超过可卖仓位")

    def test_refresh_broker_order_focus_renders_action_suggestion_line(self) -> None:
        module = importlib.import_module("app_qt")

        class _Sink:
            def __init__(self) -> None:
                self.text = ""

            def setText(self, value: str) -> None:
                self.text = value

            def setPlainText(self, value: str) -> None:
                self.text = value

        intent = OrderIntent(
            symbol="SHSE.600001",
            side="SELL",
            price=10.0,
            quantity=120,
            stop_price=9.5,
            target_price=11.2,
            signal_date="计划股",
            reason="sell demo",
        )
        focus_window = SimpleNamespace(
            broker_order_focus_text=_Sink(),
            orders_focus_label=_Sink(),
            broker_order_metric_labels={key: _Sink() for key in ("symbol", "gate", "risk", "position")},
            broker_order_metric_accents={key: _Sink() for key in ("symbol", "gate", "risk", "position")},
            broker_order_metric_cards=None,
            cash_snapshot=SimpleNamespace(available_cash=100000.0),
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600001",
                    quantity=100,
                    available=40,
                    cost_price=9.8,
                    market_value=1000.0,
                )
            ],
            daily_pool_rows=[
                SimpleNamespace(
                    symbol="SHSE.600001",
                    theme_name="AI",
                    primary_strategy="龙头模型",
                    action="BUY",
                    mainline_flow_signal="延续偏强",
                    mainline_stage="加速",
                )
            ],
            last_broker_execution_summary={"blockers": [], "warnings": ["SHSE.600001 盘中回撤需关注"]},
            _selected_order_intent=lambda: intent,
            _mainline_gate_for_order_intent=lambda _intent: (True, "主线闸门通过"),
            _broker_risk_lamp_for_intent=lambda *_args, **_kwargs: "红灯",
            _broker_focus_risk_summary=lambda *args, **kwargs: module.QuantHunterWindow._broker_focus_risk_summary(focus_window, *args, **kwargs),
            _broker_focus_action_label=lambda *args, **kwargs: module.QuantHunterWindow._broker_focus_action_label(focus_window, *args, **kwargs),
            _broker_focus_action_hint=lambda *args, **kwargs: module.QuantHunterWindow._broker_focus_action_hint(focus_window, *args, **kwargs),
            _stock_name_for_symbol=lambda _symbol: "Risk Demo",
            _stock_id_for_symbol=lambda _symbol: "600001",
            _display_action=lambda value: {"BUY": "买入", "SELL": "卖出", "REDUCE": "减仓"}.get(value, value),
            _set_metric_card_state=lambda *args, **kwargs: None,
        )

        module.QuantHunterWindow._refresh_broker_order_focus(focus_window)

        self.assertIn("当前委托动作面板", focus_window.broker_order_focus_text.text)
        self.assertIn("动作建议：先改数量", focus_window.broker_order_focus_text.text)
        self.assertIn("主线状态：延续偏强 / 加速 | 继续跟", focus_window.broker_order_focus_text.text)
        self.assertIn("下一步：卖出数量超过可卖仓位，先改数量再提交。", focus_window.broker_order_focus_text.text)
        self.assertIn("阻塞/预警：阻塞项：卖出数量超过可卖仓位", focus_window.broker_order_focus_text.text)
        self.assertIn("可卖信息：可卖 40", focus_window.broker_order_focus_text.text)
        self.assertIn("委托焦点", focus_window.orders_focus_label.text)
        self.assertIn("状态 继续跟", focus_window.orders_focus_label.text)
        self.assertIn("下一步 优先退出", focus_window.orders_focus_label.text)

    def test_position_helpers_compact_mainline_and_action_language(self) -> None:
        module = importlib.import_module("app_qt")
        window = SimpleNamespace()

        keep_item = SimpleNamespace(action="HOLD", mainline_flow_signal="延续偏强", mainline_stage="加速")
        watch_item = SimpleNamespace(action="HOLD", mainline_flow_signal="延续观察", mainline_stage="观察")
        sell_item = SimpleNamespace(action="SELL", mainline_flow_signal="切换预警", mainline_stage="分歧")

        self.assertEqual(module.QuantHunterWindow._position_mainline_brief(window, keep_item), "继续跟")
        self.assertEqual(module.QuantHunterWindow._position_action_brief(window, keep_item), "继续拿")
        self.assertEqual(module.QuantHunterWindow._position_mainline_brief(window, watch_item), "只观察")
        self.assertEqual(module.QuantHunterWindow._position_action_brief(window, watch_item), "等确认")
        self.assertEqual(module.QuantHunterWindow._position_mainline_brief(window, sell_item), "防切换")
        self.assertEqual(module.QuantHunterWindow._position_action_brief(window, sell_item), "先退出")

    def test_overview_focus_normalizes_new_investment_views(self) -> None:
        module = importlib.import_module("app_qt")
        window = SimpleNamespace()

        self.assertEqual(module.QuantHunterWindow._normalize_overview_focus(window, "龙头池"), "主线龙头")
        self.assertEqual(module.QuantHunterWindow._normalize_overview_focus(window, "题材热度"), "主线龙头")
        self.assertEqual(module.QuantHunterWindow._normalize_overview_focus(window, "资金方向"), "消息催化")
        self.assertEqual(module.QuantHunterWindow._normalize_overview_focus(window, "复盘"), "复盘研究")
        self.assertEqual(module.QuantHunterWindow._normalize_overview_focus(window, "趋势"), "趋势机会")

    def test_recommend_review_sequence_surfaces_clear_gate_order(self) -> None:
        module = importlib.import_module("app_qt")

        executable = module._qh_recommend_review_sequence_v36("继续跟", "BUY", True, "买点和主线同向，可进入送审或交易计划。")
        blocked = module._qh_recommend_review_sequence_v36("只观察", "BUY", False, "虽然进入候选，但主线或买点还没完全确认，暂不送审。")
        defensive = module._qh_recommend_review_sequence_v36("防切换", "SELL", False, "卖出优先，按风险计划处理。")

        self.assertEqual(executable, "1 主线确认 2 价位确认 3 风险确认 4 送审执行")
        self.assertEqual(blocked, "1 先等确认信号 2 再核对买点/止损 3 通过门槛后再送审")
        self.assertEqual(defensive, "1 先处理风险 2 再决定是否保留观察 3 当前不急于送审")

    def test_recommend_workspace_stage_surfaces_commercial_progression(self) -> None:
        module = importlib.import_module("app_qt")
        base_kwargs = dict(
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=10.8,
            technical_score=80.0,
            position_score=75.0,
            persistence_score=74.0,
            news_score=72.0,
            leader_score=73.0,
            total_score=81.0,
        )
        buy_row = RecommendationRow(symbol="SZSE.300001", stock_id="300001", stock_name="样本A", action="BUY", **base_kwargs)
        sell_row = RecommendationRow(symbol="SZSE.300002", stock_id="300002", stock_name="样本B", action="SELL", **base_kwargs)

        self.assertEqual(
            module._qh_recommend_workspace_stage_v37(None, "观察", False, "", False),
            ("待建立焦点", "先从主线前排选一只焦点票，再判断是否进入成交链路。"),
        )
        self.assertEqual(
            module._qh_recommend_workspace_stage_v37(buy_row, "条件较齐，可以执行", True, "待观察", True)[0],
            "可推进成交",
        )
        self.assertEqual(
            module._qh_recommend_workspace_stage_v37(buy_row, "等待送审确认", False, "已送审", True)[0],
            "送审复核",
        )
        self.assertEqual(
            module._qh_recommend_workspace_stage_v37(sell_row, "先防守，处理风险", False, "待观察", True)[0],
            "持仓处理",
        )

    def test_recommend_cta_labels_follow_execution_state(self) -> None:
        module = importlib.import_module("app_qt")

        ready = module._qh_recommend_cta_labels_v37(can_submit=True, can_open_broker=True, execution_state="待观察")
        reviewing = module._qh_recommend_cta_labels_v37(can_submit=False, can_open_broker=True, execution_state="已送审")
        submitted = module._qh_recommend_cta_labels_v37(can_submit=False, can_open_broker=True, execution_state="已提交")
        blocked = module._qh_recommend_cta_labels_v37(can_submit=False, can_open_broker=False, execution_state="待观察")

        self.assertEqual(ready["push"], "进入送审")
        self.assertEqual(ready["broker"], "打开交易执行")
        self.assertEqual(reviewing["push"], "查看送审中")
        self.assertEqual(reviewing["broker"], "查看交易链路")
        self.assertEqual(submitted["push"], "查看已提交")
        self.assertEqual(submitted["broker"], "查看交易回执")
        self.assertEqual(blocked["push"], "暂不送审")
        self.assertEqual(blocked["broker"], "暂不进交易")

    def test_broker_link_copy_distinguishes_review_submit_and_failure(self) -> None:
        module = importlib.import_module("app_qt")

        reviewing = module._qh_broker_link_copy_v39(
            stock_name="宁德时代",
            stock_id="300750",
            symbol="SZSE.300750",
            execution_status="已送审",
            has_scan_rows=True,
            has_linked_records=True,
        )
        submitted = module._qh_broker_link_copy_v39(
            stock_name="招商银行",
            stock_id="600036",
            symbol="SHSE.600036",
            execution_status="已提交",
            has_scan_rows=True,
            has_linked_records=True,
        )
        failed = module._qh_broker_link_copy_v39(
            stock_name="比亚迪",
            stock_id="002594",
            symbol="SZSE.002594",
            execution_status="提交失败",
            has_scan_rows=True,
            has_linked_records=True,
        )

        self.assertIn("已送审", reviewing[0])
        self.assertIn("交易链路", reviewing[1])
        self.assertIn("已提交", submitted[0])
        self.assertIn("交易回执", submitted[1])
        self.assertIn("提交失败", failed[0])
        self.assertIn("阻塞项", failed[1])

    def test_broker_link_target_prefers_execution_for_submitted_and_failed(self) -> None:
        module = importlib.import_module("app_qt")

        submitted = module._qh_broker_link_target_v40(
            execution_status="已提交",
            order_selected=True,
            execution_selected=True,
        )
        failed = module._qh_broker_link_target_v40(
            execution_status="提交失败",
            order_selected=False,
            execution_selected=True,
        )
        reviewing = module._qh_broker_link_target_v40(
            execution_status="已送审",
            order_selected=True,
            execution_selected=True,
        )

        self.assertEqual(submitted, "execution_table")
        self.assertEqual(failed, "execution_table")
        self.assertEqual(reviewing, "orders_table")

    def test_broker_execution_summary_distinguishes_pending_filled_and_failure(self) -> None:
        module = importlib.import_module("app_qt")

        pending = module._qh_broker_execution_summary_v41(
            stock_name="招商银行",
            stock_id="600036",
            symbol="SHSE.600036",
            order_status_text="已提交",
            fill_status_text="待成交",
            failure_reason="",
            message="等待柜台回执",
        )
        filled = module._qh_broker_execution_summary_v41(
            stock_name="宁德时代",
            stock_id="300750",
            symbol="SZSE.300750",
            order_status_text="已提交",
            fill_status_text="已成交",
            failure_reason="",
            message="成交完成",
        )
        failed = module._qh_broker_execution_summary_v41(
            stock_name="比亚迪",
            stock_id="002594",
            symbol="SZSE.002594",
            order_status_text="提交失败",
            fill_status_text="已拒绝",
            failure_reason="可用资金不足",
            message="柜台拒绝",
        )

        self.assertEqual(pending["stage"], "待成交跟踪")
        self.assertIn("回执", pending["next_step"])
        self.assertEqual(filled["stage"], "已成交待复盘")
        self.assertIn("持仓", filled["judgement"])
        self.assertEqual(failed["stage"], "阻塞待处理")
        self.assertIn("可用资金不足", failed["tooltip"])

    def test_broker_execution_followup_routes_by_stage(self) -> None:
        module = importlib.import_module("app_qt")

        blocked = module._qh_broker_execution_followup_v42(
            stage="阻塞待处理",
            has_recommendation=True,
            has_intent=True,
        )
        pending = module._qh_broker_execution_followup_v42(
            stage="待成交跟踪",
            has_recommendation=True,
            has_intent=True,
        )
        filled = module._qh_broker_execution_followup_v42(
            stage="已成交待复盘",
            has_recommendation=True,
            has_intent=False,
        )

        self.assertEqual(blocked["headline"], "回推荐页复核")
        self.assertIn("主线", blocked["detail"])
        self.assertEqual(pending["route"], "交易页")
        self.assertIn("盯回执", pending["headline"])
        self.assertEqual(filled["route"], "复盘页")
        self.assertIn("执行偏差", filled["detail"])

    def test_broker_repair_hint_distinguishes_capital_risk_and_channel_blockers(self) -> None:
        module = importlib.import_module("app_qt")

        capital = module._qh_broker_repair_hint_v43(
            failure_reason="可用资金不足",
            message="柜台拒绝",
            has_recommendation=True,
        )
        risk = module._qh_broker_repair_hint_v43(
            failure_reason="超过可卖数量",
            message="触发风控",
            has_recommendation=True,
        )
        channel = module._qh_broker_repair_hint_v43(
            failure_reason="",
            message="SDK 通道未就绪",
            has_recommendation=False,
        )

        self.assertEqual(capital["headline"], "先收缩仓位")
        self.assertIn("可用资金", capital["checkpoint"])
        self.assertEqual(risk["headline"], "先修正风控")
        self.assertIn("止损位", risk["checkpoint"])
        self.assertEqual(channel["headline"], "先检查通道")
        self.assertIn("桥接解释器", channel["checkpoint"])

    def test_broker_execution_tone_maps_stage_to_visual_priority(self) -> None:
        module = importlib.import_module("app_qt")

        self.assertEqual(module._qh_broker_execution_tone_v44("阻塞待处理"), "risk")
        self.assertEqual(module._qh_broker_execution_tone_v44("待成交跟踪"), "watch")
        self.assertEqual(module._qh_broker_execution_tone_v44("已成交待复盘"), "buy")
        self.assertEqual(module._qh_broker_execution_tone_v44(""), "idle")

    def test_broker_recommend_context_formats_price_plan_and_news(self) -> None:
        module = importlib.import_module("app_qt")

        with_news = module._qh_broker_recommend_context_v45(
            price_brief="买 12.30 | 损 11.70 | 目标 13.40",
            news_lines=["- 机器人订单放量 (证券时报 / 10:05)", "  摘要内容"],
        )
        empty_news = module._qh_broker_recommend_context_v45(
            price_brief="",
            news_lines=[],
        )

        self.assertEqual(with_news[0], "价格计划：买 12.30 | 损 11.70 | 目标 13.40")
        self.assertIn("机器人订单放量", with_news[1])
        self.assertEqual(empty_news, ["最近催化：暂无近期催化"])

    def test_broker_parameter_alignment_flags_buy_price_drift_and_goal_zone(self) -> None:
        module = importlib.import_module("app_qt")

        rich_buy = module._qh_broker_parameter_alignment_v46(
            side="BUY",
            order_price="12.80",
            plan_entry=12.0,
            plan_stop=11.4,
            plan_target=13.2,
        )
        near_target = module._qh_broker_parameter_alignment_v46(
            side="BUY",
            order_price="13.20",
            plan_entry=12.0,
            plan_stop=11.4,
            plan_target=13.2,
        )
        sell_zone = module._qh_broker_parameter_alignment_v46(
            side="SELL",
            order_price="13.10",
            plan_entry=12.0,
            plan_stop=11.4,
            plan_target=13.2,
        )

        self.assertEqual(rich_buy["headline"], "买点偏高")
        self.assertIn("重算买点区间", rich_buy["checkpoint"])
        self.assertEqual(near_target["headline"], "接近目标位")
        self.assertIn("追价", near_target["detail"])
        self.assertEqual(sell_zone["headline"], "接近兑现区")
        self.assertIn("兑现比例", sell_zone["checkpoint"])

    def test_broker_resolution_action_routes_to_recommend_trade_config_or_review(self) -> None:
        module = importlib.import_module("app_qt")

        channel = module._qh_broker_resolution_action_v47(
            stage="阻塞待处理",
            repair_headline="先检查通道",
            parameter_headline="参数待复核",
            has_recommendation=True,
            channel_text="东方财富",
        )
        recommend = module._qh_broker_resolution_action_v47(
            stage="待成交跟踪",
            repair_headline="先复核参数",
            parameter_headline="买点偏高",
            has_recommendation=True,
            channel_text="GM",
        )
        review = module._qh_broker_resolution_action_v47(
            stage="已成交待复盘",
            repair_headline="先复核参数",
            parameter_headline="价格贴合计划",
            has_recommendation=True,
            channel_text="GM",
        )

        self.assertEqual(channel["target"], "账户配置")
        self.assertIn("东方财富", channel["detail"])
        self.assertEqual(recommend["target"], "推荐页")
        self.assertIn("重生成委托", recommend["detail"])
        self.assertEqual(review["target"], "复盘页")
        self.assertIn("复盘", review["detail"])

    def test_broker_terminal_brief_compresses_visible_status_copy(self) -> None:
        module = importlib.import_module("app_qt")

        brief = module._qh_broker_terminal_brief_v48(
            stock_name="宁德时代",
            stock_id="300750",
            stage="待成交跟踪",
            mainline_signal="继续跟",
            parameter_headline="买点偏高",
            resolution_target="推荐页",
        )

        self.assertEqual(brief["status"], "交易状态：宁德时代 300750 | 待成交跟踪 | 去推荐页")
        self.assertIn("主线 继续跟", brief["workbench"])
        self.assertEqual(brief["stage"], "执行阶段：待成交跟踪 | 主线 继续跟 | 去推荐页")
        self.assertEqual(brief["focus"], "执行焦点：宁德时代 | 买点偏高 | 去推荐页")

    def test_broker_panel_conclusion_surfaces_stage_and_resolution_in_one_line(self) -> None:
        module = importlib.import_module("app_qt")

        line = module._qh_broker_panel_conclusion_v49(
            stage="阻塞待处理",
            parameter_headline="先检查通道",
            resolution_target="账户配置",
        )

        self.assertEqual(line, "结论：阻塞待处理 / 先检查通道 / 去账户配置")

    def test_broker_execution_deck_packs_middle_panel_values_for_execution_focus(self) -> None:
        module = importlib.import_module("app_qt")

        deck = module._qh_broker_execution_deck_v50(
            stock_name="宁德时代",
            stock_id="300750",
            symbol="SZSE.300750",
            side_text="买入",
            quantity="2400",
            price="182.50",
            mainline_signal="继续跟",
            mainline_stage="强化中",
            stage="待成交跟踪",
            parameter_headline="买点偏高",
            repair_headline="先收缩仓位",
            resolution_target="推荐页",
        )

        self.assertEqual(deck["symbol_value"], "宁德时代")
        self.assertEqual(deck["symbol_accent"], "300750 / SZSE.300750")
        self.assertEqual(deck["gate_value"], "待成交跟踪")
        self.assertEqual(deck["gate_accent"], "继续跟 / 强化中")
        self.assertEqual(deck["risk_value"], "买点偏高")
        self.assertEqual(deck["risk_accent"], "先收缩仓位")
        self.assertEqual(deck["position_value"], "去推荐页")
        self.assertEqual(deck["position_accent"], "买入 2400 @ 182.50")
        self.assertEqual(deck["headline"], "执行动作面板：宁德时代 | 待成交跟踪 | 去推荐页")

    def test_broker_focus_shortcuts_sync_blocker_and_priority_tooltips(self) -> None:
        module = importlib.import_module("app_qt")

        blocked = module._qh_broker_focus_shortcuts_v51(
            stock_name="比亚迪",
            stage="阻塞待处理",
            blocker_present=True,
            blocker_hint="先检查通道",
            parameter_headline="参数待复核",
            resolution_target="账户配置",
        )
        tracking = module._qh_broker_focus_shortcuts_v51(
            stock_name="宁德时代",
            stage="待成交跟踪",
            blocker_present=False,
            blocker_hint="先复核参数",
            parameter_headline="买点偏高",
            resolution_target="推荐页",
        )

        self.assertIn("阻塞优先", blocked["blocker_tooltip"])
        self.assertIn("先检查通道", blocked["blocker_tooltip"])
        self.assertIn("前排暂缓", blocked["priority_tooltip"])
        self.assertIn("待成交跟踪", tracking["blocker_tooltip"])
        self.assertIn("买点偏高", tracking["priority_tooltip"])
        self.assertIn("推荐页", tracking["priority_tooltip"])

    def test_broker_action_strip_labels_follow_execution_stage(self) -> None:
        module = importlib.import_module("app_qt")

        blocked = module._qh_broker_action_strip_labels_v52(
            stage="阻塞待处理",
            blocker_present=True,
            has_priority_target=True,
        )
        pending = module._qh_broker_action_strip_labels_v52(
            stage="待成交跟踪",
            blocker_present=False,
            has_priority_target=True,
        )
        review = module._qh_broker_action_strip_labels_v52(
            stage="已成交待复盘",
            blocker_present=False,
            has_priority_target=True,
        )
        empty = module._qh_broker_action_strip_labels_v52(
            stage="待成交跟踪",
            blocker_present=False,
            has_priority_target=False,
        )

        self.assertEqual(blocked["blocker_text"], "处理阻塞")
        self.assertEqual(blocked["priority_text"], "前排暂缓")
        self.assertEqual(pending["priority_text"], "跟前排单")
        self.assertEqual(review["blocker_text"], "看偏差项")
        self.assertEqual(review["priority_text"], "看前排复盘")
        self.assertEqual(empty["priority_text"], "暂无前排")

    def test_broker_primary_cta_labels_follow_stage_and_order_counts(self) -> None:
        module = importlib.import_module("app_qt")

        cold = module._qh_broker_primary_cta_labels_v53(
            stage="",
            order_count=0,
            submit_count=0,
            has_focus_symbol=False,
        )
        ready = module._qh_broker_primary_cta_labels_v53(
            stage="",
            order_count=3,
            submit_count=0,
            has_focus_symbol=True,
        )
        blocked = module._qh_broker_primary_cta_labels_v53(
            stage="阻塞待处理",
            order_count=2,
            submit_count=1,
            has_focus_symbol=True,
        )
        in_flight = module._qh_broker_primary_cta_labels_v53(
            stage="待成交跟踪",
            order_count=1,
            submit_count=1,
            has_focus_symbol=True,
        )

        self.assertEqual(cold["generate_text"], "生成委托链路")
        self.assertEqual(cold["confirm_text"], "确认并提交委托")
        self.assertEqual(ready["generate_text"], "重算委托链路")
        self.assertEqual(ready["confirm_text"], "核对后提交 (3)")
        self.assertEqual(blocked["generate_text"], "按阻塞重生成")
        self.assertEqual(blocked["confirm_text"], "修正后提交 (2)")
        self.assertEqual(in_flight["generate_text"], "围绕焦点重生成")
        self.assertEqual(in_flight["confirm_text"], "核对后提交 (1)")

    def test_broker_primary_cta_tooltips_follow_stage_and_focus(self) -> None:
        module = importlib.import_module("app_qt")

        cold = module._qh_broker_primary_cta_tooltips_v54(
            stage="",
            order_count=0,
            submit_count=0,
            stock_name="当前焦点",
        )
        blocked = module._qh_broker_primary_cta_tooltips_v54(
            stage="阻塞待处理",
            order_count=2,
            submit_count=1,
            stock_name="比亚迪",
        )
        in_flight = module._qh_broker_primary_cta_tooltips_v54(
            stage="待成交跟踪",
            order_count=1,
            submit_count=1,
            stock_name="宁德时代",
        )

        self.assertIn("自动生成委托建议", cold["generate_tooltip"])
        self.assertIn("请先从推荐池生成委托建议", cold["confirm_tooltip"])
        self.assertIn("按最新阻塞项重生成", blocked["generate_tooltip"])
        self.assertIn("请先修正阻塞项", blocked["confirm_tooltip"])
        self.assertIn("宁德时代", in_flight["generate_tooltip"])
        self.assertIn("再次核对后提交", in_flight["confirm_tooltip"])

    def test_update_broker_action_flow_resets_shortcut_labels_when_no_execution_focus(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            order_intents=[],
            order_submission_records=[],
            active_symbol="",
            broker_focus_blocker_button=module.QPushButton("处理阻塞"),
            broker_focus_priority_button=module.QPushButton("前排暂缓"),
            confirm_submit_orders_button=module.QPushButton(),
            generate_order_suggestions_button=module.QPushButton(),
            broker_status_banner=module.QLabel(),
            broker_execution_text=module.QTextEdit(),
            _stock_name_for_symbol=lambda symbol: "宁德时代" if symbol else "--",
            _set_label_text_if_changed=lambda widget, text, tooltip=None: (
                widget.setText(text) if widget.text() != text else None,
                widget.setToolTip(tooltip) if tooltip is not None and hasattr(widget, "setToolTip") and widget.toolTip() != tooltip else None,
            ),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
        )

        module._qh_update_broker_action_flow_v26(window)

        self.assertEqual(window.broker_focus_blocker_button.text(), "定位阻塞")
        self.assertEqual(window.broker_focus_priority_button.text(), "定位高优先")
        self.assertEqual(window.generate_order_suggestions_button.text(), "生成委托链路")
        self.assertEqual(window.confirm_submit_orders_button.text(), "确认并提交委托")
        self.assertIn("当前没有阻塞项", window.broker_focus_blocker_button.toolTip())
        self.assertIn("当前没有高优先委托", window.broker_focus_priority_button.toolTip())
        self.assertIn("自动生成委托建议", window.generate_order_suggestions_button.toolTip())
        self.assertIn("请先从推荐池生成委托建议", window.confirm_submit_orders_button.toolTip())

    def test_set_aux_stage_visibility_updates_toggle_and_status(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            recommend_stage_container=module.QWidget(),
            recommend_stage_toggle_button=module.QPushButton(),
            recommend_stage_status_label=module.QLabel(),
            _set_label_text_if_changed=lambda label, text: label.setText(text) if label.text() != text else None,
        )

        module.QuantHunterWindow._set_aux_stage_visibility_v38(window, False)
        self.assertFalse(window.recommend_stage_container.isVisible())
        self.assertEqual(window.recommend_stage_toggle_button.text(), "展开辅助洞察")
        self.assertIn("辅助洞察已折叠", window.recommend_stage_status_label.text())

        module.QuantHunterWindow._set_aux_stage_visibility_v38(window, True)
        self.assertTrue(window.recommend_stage_container.isVisible())
        self.assertEqual(window.recommend_stage_toggle_button.text(), "收起辅助洞察")
        self.assertIn("辅助洞察已展开", window.recommend_stage_status_label.text())

    def test_refresh_recommend_decision_summary_sets_empty_cta_defaults(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            recommend_decision_summary_label=module.QLabel(),
            recommend_decision_summary_text=module.QTextEdit(),
            recommend_push_focus_button=module.QPushButton(),
            recommend_detail_focus_button=module.QPushButton(),
            recommend_broker_focus_button=module.QPushButton(),
            _current_recommend_focus=lambda: None,
            _set_label_text_if_changed=lambda widget, text, tooltip=None: widget.setText(text) if widget.text() != text else None,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
        )

        module.QuantHunterWindow._refresh_recommend_decision_summary(window, None)

        self.assertEqual(window.recommend_push_focus_button.text(), "暂不送审")
        self.assertFalse(window.recommend_push_focus_button.isEnabled())
        self.assertEqual(window.recommend_detail_focus_button.text(), "查看复盘证据")
        self.assertFalse(window.recommend_detail_focus_button.isEnabled())
        self.assertEqual(window.recommend_broker_focus_button.text(), "暂不进交易")
        self.assertFalse(window.recommend_broker_focus_button.isEnabled())

    def test_update_paper_trading_focus_hint_toggles_label_and_buttons(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            paper_trading_focus_label=module.QLabel(),
            paper_to_recommend_button=module.QPushButton(),
            paper_to_detail_button=module.QPushButton(),
            paper_to_broker_button=module.QPushButton(),
            _selected_paper_symbol=lambda: "",
            _stock_name_for_symbol=lambda _symbol: "龙头样本",
            _stock_id_for_symbol=lambda _symbol: "300001",
        )

        module.QuantHunterWindow._update_paper_trading_focus_hint(window)
        self.assertIn("点击持仓或交割单后", window.paper_trading_focus_label.text())
        self.assertFalse(window.paper_to_recommend_button.isEnabled())
        self.assertFalse(window.paper_to_detail_button.isEnabled())
        self.assertFalse(window.paper_to_broker_button.isEnabled())

        window._selected_paper_symbol = lambda: "SZSE.300001"
        module.QuantHunterWindow._update_paper_trading_focus_hint(window)
        self.assertIn("龙头样本", window.paper_trading_focus_label.text())
        self.assertIn("300001 / SZSE.300001", window.paper_trading_focus_label.text())
        self.assertTrue(window.paper_to_recommend_button.isEnabled())
        self.assertTrue(window.paper_to_detail_button.isEnabled())
        self.assertTrue(window.paper_to_broker_button.isEnabled())

    def test_open_selected_recommend_in_broker_syncs_symbol_and_routes(self) -> None:
        module = importlib.import_module("app_qt")
        base_row = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="龙头样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-14",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=10.8,
            technical_score=86.0,
            position_score=77.0,
            persistence_score=82.0,
            news_score=73.0,
            leader_score=90.0,
            total_score=88.0,
        )
        broker_calls: list[str] = []
        focus_calls: list[tuple[str, str]] = []
        window = SimpleNamespace(
            active_symbol="",
            _current_recommend_focus=lambda: base_row,
            _focus_symbol_in_broker_workspace=lambda symbol: broker_calls.append(symbol),
            _focus_symbol_everywhere=lambda symbol, origin="": focus_calls.append((symbol, origin)),
        )

        module.QuantHunterWindow.open_selected_recommend_in_broker(window)

        self.assertEqual(window.active_symbol, "SZSE.300001")
        self.assertEqual(broker_calls, ["SZSE.300001"])
        self.assertEqual(focus_calls, [("SZSE.300001", "recommend")])

    def test_refresh_recommendation_focus_panels_renders_queue_and_review_copy(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        base_row = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="龙头样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-14",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=10.8,
            technical_score=86.0,
            position_score=77.0,
            persistence_score=82.0,
            news_score=73.0,
            leader_score=90.0,
            total_score=88.0,
            mainline_tag="机器人",
            mainline_risk_flag="低",
            confidence_score=84.0,
            execution_readiness=81.0,
            opportunity_tier="优先处理",
            primary_strategy="龙头低吸",
            catalyst="主线强化 + 量能回流",
            rationale="主线强度和位置都在前排",
            next_focus="继续盯换手与承接。",
            invalidation_reason="跌破 9.60 防守线",
        )
        row = SimpleNamespace(**base_row.__dict__, execution_status="待观察", mainline_flow_signal="继续跟")
        waiting = SimpleNamespace(
            **{
                **base_row.__dict__,
                "symbol": "SZSE.300002",
                "stock_id": "300002",
                "stock_name": "排队样本",
                "execution_status": "待观察",
                "mainline_flow_signal": "继续跟",
            }
        )
        window = SimpleNamespace(
            recommend_dispatch_text=module.QTextEdit(),
            recommend_focus_review_text=module.QTextEdit(),
            recommend_queue_text=module.QTextEdit(),
            daily_pool_rows=[waiting, row],
            execution_status_by_symbol={"SZSE.300001": "待观察", "SZSE.300002": "待观察"},
            _current_recommend_focus=lambda: row,
            _selected_daily_pool_recommendation=lambda: row,
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _display_mainline_role=lambda value: value or "主升",
            _refresh_recommend_story_panels=lambda current=None: None,
            _refresh_recommend_focus_status=lambda current=None: None,
            _refresh_recommend_focus_cards=lambda current=None: None,
            _refresh_recommend_decision_summary=lambda current=None: None,
            _refresh_action_button_states_v30=lambda: None,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
        )

        module.QuantHunterWindow._refresh_recommendation_focus_panels(window, row)

        self.assertIn("结论：龙头样本 | 条件较齐，可以执行", window.recommend_dispatch_text.toPlainText())
        self.assertIn("确认信号：", window.recommend_focus_review_text.toPlainText())
        self.assertIn("机器人 | 主升", window.recommend_focus_review_text.toPlainText())
        self.assertIn("当前优先：排队样本", window.recommend_queue_text.toPlainText())

    def test_refresh_broker_order_focus_uses_recommendation_when_intent_missing(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        row = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="龙头样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-14",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=10.8,
            technical_score=86.0,
            position_score=77.0,
            persistence_score=82.0,
            news_score=73.0,
            leader_score=90.0,
            total_score=88.0,
            mainline_tag="机器人",
            mainline_risk_flag="低",
            next_focus="先生成委托链路，再复核交易条件。",
        )
        window = SimpleNamespace(
            orders_focus_label=module.QLabel(),
            broker_order_focus_text=module.QTextEdit(),
            broker_order_metric_labels={key: module.QLabel() for key in ("symbol", "gate", "risk", "position")},
            broker_order_metric_accents={key: module.QLabel() for key in ("symbol", "gate", "risk", "position")},
            _selected_order_intent=lambda: None,
            _explicit_recommendation_focus=lambda: row,
            _stock_name_for_symbol=lambda _symbol: "龙头样本",
            _stock_id_for_symbol=lambda _symbol: "300001",
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: widget.setText(text) if widget.text() != text else None,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
            _refresh_live_workspace_summary_panels=lambda: None,
        )

        with patch.object(module, "_qh_mainline_signal_brief_v4", return_value="继续跟"), patch.object(
            module, "_qh_signal_action_text_v4", return_value="买入"
        ):
            module.QuantHunterWindow._refresh_broker_order_focus(window)

        self.assertIn("龙头样本 | 待生成委托", window.orders_focus_label.text())
        self.assertIn("当前还没有委托建议", window.broker_order_focus_text.toPlainText())
        self.assertIn(window.broker_order_metric_labels["gate"].text(), {"继续跟", "只观察"})
        self.assertEqual(window.broker_order_metric_accents["risk"].text(), "等待生成委托")

    def test_toggle_recommend_auxiliary_stage_flips_state(self) -> None:
        module = importlib.import_module("app_qt")
        calls: list[bool] = []
        window = SimpleNamespace(
            _qh_recommend_aux_stage_visible_v38=False,
            _set_aux_stage_visibility_v38=lambda visible: calls.append(bool(visible)),
        )

        module.QuantHunterWindow.toggle_recommend_auxiliary_stage(window)
        self.assertEqual(calls, [True])

    def test_paper_lab_stage_distinguishes_setup_sample_and_review(self) -> None:
        module = importlib.import_module("app_qt")

        empty_state = PaperTradingState()
        started_state = PaperTradingState(enabled=True, ledger=[PaperOrderRecord(order_id="SIM1", timestamp="2026-04-14 10:00:00", symbol="SZSE.300001", stock_id="300001", stock_name="样本", side="BUY", price=10.0, quantity=100, amount=1000.0, strategy_name="龙头模型", position_pct=0.1)])
        review_state = PaperTradingState(
            enabled=True,
            ledger=[
                PaperOrderRecord(
                    order_id="SIM2",
                    timestamp="2026-04-14 10:30:00",
                    symbol="SZSE.300002",
                    stock_id="300002",
                    stock_name="样本B",
                    side="SELL",
                    price=10.8,
                    quantity=100,
                    amount=1080.0,
                    strategy_name="龙头模型",
                    position_pct=0.1,
                    realized_pnl=80.0,
                )
            ],
        )

        self.assertEqual(
            module._qh_paper_lab_stage_v39(empty_state, {"closed_trade_count": 0}),
            ("待初始化", "先创建实验账户，再跑第一轮策略样本。"),
        )
        self.assertEqual(
            module._qh_paper_lab_stage_v39(started_state, {"closed_trade_count": 0}),
            ("样本积累中", "已经开始建仓，但还没有形成完整闭环，先继续滚动验证。"),
        )
        self.assertEqual(
            module._qh_paper_lab_stage_v39(review_state, {"closed_trade_count": 5}),
            ("进入策略复盘", "闭环样本已经足够，可以把这里当成策略实验室持续复盘。"),
        )

    def test_set_paper_lab_detail_visibility_updates_widgets_and_copy(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            paper_trading_splitter=module.QWidget(),
            paper_analytics_splitter=module.QWidget(),
            paper_trading_text=module.QTextEdit(),
            paper_lab_toggle_button=module.QPushButton(),
            paper_lab_toggle_status_label=module.QLabel(),
            _set_label_text_if_changed=lambda label, text: label.setText(text) if label.text() != text else None,
        )

        module.QuantHunterWindow._set_paper_lab_detail_visibility_v39(window, False)
        self.assertFalse(window.paper_trading_splitter.isVisible())
        self.assertEqual(window.paper_lab_toggle_button.text(), "展开原始流水")
        self.assertIn("原始流水已折叠", window.paper_lab_toggle_status_label.text())

        module.QuantHunterWindow._set_paper_lab_detail_visibility_v39(window, True)
        self.assertTrue(window.paper_trading_splitter.isVisible())
        self.assertEqual(window.paper_lab_toggle_button.text(), "收起原始流水")
        self.assertIn("已展开原始流水", window.paper_lab_toggle_status_label.text())

    def test_broker_workspace_stage_distinguishes_build_submit_and_review(self) -> None:
        module = importlib.import_module("app_qt")

        self.assertEqual(
            module._qh_broker_workspace_stage_v40(0, 0, 0),
            ("待生成委托", "先从推荐页或交易计划生成第一批可执行委托。"),
        )
        self.assertEqual(
            module._qh_broker_workspace_stage_v40(2, 0, 0),
            ("待确认提交", "委托已经生成，下一步打开确认弹窗核对后提交。"),
        )
        self.assertEqual(
            module._qh_broker_workspace_stage_v40(0, 1, 0),
            ("执行回执", "已经进入执行跟踪阶段，当前重点是回执、成交和偏差。"),
        )
        self.assertEqual(
            module._qh_broker_workspace_stage_v40(1, 0, 2),
            ("风控阻塞", "存在阻塞项，先排除风险灯和仓位问题，再进入提交。"),
        )

    def test_broker_experiment_review_lines_surface_strategy_role_and_cta(self) -> None:
        broker_patches = importlib.import_module("quant_hunter.ui_window_broker_patches")

        with patch.object(
            broker_patches,
            "paper_strategy_experiment_bridge_v45",
            return_value={
                "title": "主测 | 龙头模型 | 继续主测",
                "detail": "样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "cta": "推荐页优先筛同战法前排，交易页按主测纪律推进。",
            },
        ):
            lines = broker_patches.broker_experiment_review_lines_v47(
                PaperTradingState(enabled=True),
                "龙头模型",
            )

        self.assertEqual(lines[0], "模拟盘实验：主测 | 龙头模型 | 继续主测")
        self.assertEqual(lines[1], "实验纪律：样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18")
        self.assertEqual(lines[2], "交易约束：推荐页优先筛同战法前排，交易页按主测纪律推进。")

    def test_broker_workspace_patch_appends_paper_experiment_summary_to_submission_focus(self) -> None:
        broker_patches = importlib.import_module("quant_hunter.ui_window_broker_patches")
        app = importlib.import_module("app_qt")
        qt_app = app.QApplication.instance() or app.QApplication([])
        _ = qt_app

        class DummyWindow:
            def __init__(self) -> None:
                self.daily_pool_rows = [SimpleNamespace(symbol="SZSE.300001", primary_strategy="龙头模型")]
                self.paper_trading_state = PaperTradingState(enabled=True)
                self.broker_mainline_review_text = app.QTextEdit()
                self.broker_execution_text = app.QTextEdit()

            def _refresh_broker_auxiliary_panels(self) -> None:
                return None

            def _post_build_ui_tweaks(self) -> None:
                return None

            def _refresh_submission_focus(self) -> None:
                self.broker_mainline_review_text.setPlainText("主线闸门审查：龙头样本\n执行阶段：待确认提交")
                self.broker_execution_text.setPlainText("交易流程\n\n当前焦点：龙头样本")

            def _selected_submission_record(self):
                return {"symbol": "SZSE.300001"}

            def _set_plain_text_if_changed(self, widget, text):
                if widget.toPlainText() != text:
                    widget.setPlainText(text)

        broker_patches.apply_broker_workspace_patches(DummyWindow)
        window = DummyWindow()

        with patch.object(
            broker_patches,
            "broker_experiment_review_lines_v47",
            return_value=[
                "模拟盘实验：主测 | 龙头模型 | 继续主测",
                "实验纪律：样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "交易约束：推荐页优先筛同战法前排，交易页按主测纪律推进。",
            ],
        ):
            window._refresh_submission_focus()

        self.assertIn("模拟盘实验：主测 | 龙头模型 | 继续主测", window.broker_mainline_review_text.toPlainText())
        self.assertIn("交易约束：推荐页优先筛同战法前排，交易页按主测纪律推进。", window.broker_mainline_review_text.toPlainText())
        self.assertIn("模拟盘实验：主测 | 龙头模型 | 继续主测", window.broker_execution_text.toPlainText())

    def test_broker_pre_submit_experiment_lines_surface_bridge_summary(self) -> None:
        workbench_patches = importlib.import_module("quant_hunter.ui_window_workbench_patches")

        with patch.object(
            workbench_patches,
            "paper_strategy_experiment_bridge_v45",
            return_value={
                "title": "主测 | 龙头模型 | 继续主测",
                "detail": "样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "cta": "推荐页优先筛同战法前排，交易页按主测纪律推进。",
            },
        ):
            lines = workbench_patches.broker_pre_submit_experiment_lines_v48(
                PaperTradingState(enabled=True),
                "龙头模型",
            )

        self.assertEqual(lines[0], "模拟盘实验：主测 | 龙头模型 | 继续主测")
        self.assertEqual(lines[1], "实验纪律：样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18")
        self.assertEqual(lines[2], "提交前提示：推荐页优先筛同战法前排，交易页按主测纪律推进。")

    def test_merge_broker_experiment_lines_replaces_old_block(self) -> None:
        workbench_patches = importlib.import_module("quant_hunter.ui_window_workbench_patches")

        merged = workbench_patches.merge_broker_experiment_lines_v47(
            "执行回放\n\n当前状态：待提交委托 1 笔\n模拟盘实验：旧内容\n实验纪律：旧内容\n提交前提示：旧内容",
            [
                "模拟盘实验：主测 | 龙头模型 | 继续主测",
                "实验纪律：样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "提交前提示：推荐页优先筛同战法前排，交易页按主测纪律推进。",
            ],
        )

        self.assertIn("执行回放", merged)
        self.assertEqual(merged.count("模拟盘实验："), 1)
        self.assertEqual(merged.count("实验纪律："), 1)
        self.assertIn("模拟盘实验：主测 | 龙头模型 | 继续主测", merged)
        self.assertIn("提交前提示：推荐页优先筛同战法前排，交易页按主测纪律推进。", merged)

    def test_shell_pipeline_story_summarizes_daily_workflow(self) -> None:
        module = importlib.import_module("app_qt")

        cold = module._qh_shell_pipeline_story_v41(
            pool_count=0,
            trade_decisions_count=0,
            pending_orders=0,
            submitted_orders=0,
            paper_enabled=False,
            paper_closed_trades=0,
        )
        active = module._qh_shell_pipeline_story_v41(
            pool_count=12,
            trade_decisions_count=4,
            pending_orders=2,
            submitted_orders=0,
            paper_enabled=True,
            paper_closed_trades=0,
        )
        review = module._qh_shell_pipeline_story_v41(
            pool_count=18,
            trade_decisions_count=5,
            pending_orders=0,
            submitted_orders=3,
            paper_enabled=True,
            paper_closed_trades=6,
        )

        self.assertEqual(cold, "市场待刷新 -> 推荐待生成 -> 交易未启动 -> 实验待初始化")
        self.assertEqual(active, "市场已同步 -> 推荐已生成 -> 交易待确认 -> 实验跑样本")
        self.assertEqual(review, "市场已同步 -> 推荐已生成 -> 交易跟踪中 -> 实验可复盘")

    def test_refresh_action_button_states_updates_workspace_routes(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        scanner_tab = module.QWidget()
        scanner_layout = module.QVBoxLayout(scanner_tab)
        review_button = module.QPushButton("查看复盘")
        scanner_layout.addWidget(review_button)

        overview_tab = module.QWidget()
        overview_layout = module.QVBoxLayout(overview_tab)
        fund_button = module.QPushButton("资金看推荐")
        overview_layout.addWidget(fund_button)

        window = SimpleNamespace(
            recommend_to_broker_button=module.QPushButton(),
            plan_to_broker_button=module.QPushButton(),
            focus_pending_button=module.QPushButton(),
            retry_failed_button=module.QPushButton(),
            push_priority_button=module.QPushButton(),
            broker_focus_blocker_button=module.QPushButton(),
            broker_focus_priority_button=module.QPushButton(),
            paper_to_recommend_button=module.QPushButton(),
            paper_to_detail_button=module.QPushButton(),
            paper_to_broker_button=module.QPushButton(),
            scanner_tab=scanner_tab,
            board_tab=module.QWidget(),
            recommend_tab=module.QWidget(),
            broker_tab=module.QWidget(),
            detail_tab=module.QWidget(),
            overview_tab=overview_tab,
            current_trade_plan=SimpleNamespace(decisions=[]),
            order_intents=[],
            daily_pool_rows=[],
            active_symbol="",
            last_broker_execution_summary={},
            _selected_daily_pool_recommendation=lambda: None,
            _has_pending_recommendations_v30=lambda: False,
            _has_failed_recommendations_v30=lambda: False,
            _selected_paper_symbol=lambda: "",
            _selected_symbol_from_watchlist=lambda: "",
            _selected_board_symbol=lambda: "",
        )

        module.QuantHunterWindow._refresh_action_button_states_v30(window)
        self.assertFalse(window.recommend_to_broker_button.isEnabled())
        self.assertFalse(window.focus_pending_button.isEnabled())
        self.assertFalse(window.push_priority_button.isEnabled())
        self.assertFalse(review_button.isEnabled())
        self.assertFalse(fund_button.isEnabled())

        window.active_symbol = "SZSE.300001"
        window.order_intents = [object()]
        window.daily_pool_rows = [SimpleNamespace(execution_status="待复核")]
        window._selected_daily_pool_recommendation = lambda: object()
        window._has_pending_recommendations_v30 = lambda: True
        window._selected_paper_symbol = lambda: "SZSE.300001"

        module.QuantHunterWindow._refresh_action_button_states_v30(window)
        self.assertTrue(window.recommend_to_broker_button.isEnabled())
        self.assertTrue(window.focus_pending_button.isEnabled())
        self.assertTrue(window.push_priority_button.isEnabled())
        self.assertTrue(window.broker_focus_priority_button.isEnabled())
        self.assertTrue(window.paper_to_recommend_button.isEnabled())
        self.assertTrue(review_button.isEnabled())
        self.assertTrue(fund_button.isEnabled())

    def test_hydrate_runtime_empty_states_populates_default_copy(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            runtime_log_text=module.QTextEdit(),
            paper_experiment_text=module.QTextEdit(),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
        )

        module.QuantHunterWindow._hydrate_runtime_empty_states_v33(window)

        self.assertIn("运行日志", window.runtime_log_text.toPlainText())
        self.assertIn("实验记录", window.paper_experiment_text.toPlainText())

    def test_shell_workflow_stage_specs_switch_targets_and_statuses(self) -> None:
        module = importlib.import_module("app_qt")

        cold_specs, cold_next = module._qh_shell_workflow_stage_specs_v42(
            current_workspace_key="overview",
            pool_count=0,
            trade_decisions_count=0,
            pending_orders=0,
            submitted_orders=0,
            paper_enabled=False,
            paper_closed_trades=0,
            paper_position_count=0,
        )
        review_specs, review_next = module._qh_shell_workflow_stage_specs_v42(
            current_workspace_key="broker",
            pool_count=18,
            trade_decisions_count=5,
            pending_orders=0,
            submitted_orders=3,
            paper_enabled=True,
            paper_closed_trades=6,
            paper_position_count=2,
        )

        self.assertEqual(cold_next, "market")
        self.assertEqual(cold_specs[0]["button_text"], "市场 待刷新")
        self.assertEqual(cold_specs[0]["role"], "accent")
        self.assertEqual(cold_specs[1]["widget"], "daily_pool_table")
        self.assertEqual(cold_specs[3]["widget"], "paper_initialize_button")
        self.assertEqual(cold_specs[3]["button_text"], "实验 待初始化")

        self.assertEqual(review_next, "experiment")
        self.assertEqual(review_specs[1]["widget"], "trade_plan_table")
        self.assertEqual(review_specs[2]["button_text"], "交易 跟踪中")
        self.assertEqual(review_specs[2]["role"], "accent")
        self.assertEqual(review_specs[3]["widget"], "paper_positions_table")
        self.assertEqual(review_specs[3]["button_text"], "实验 可复盘")

    def test_open_shell_workflow_stage_uses_dynamic_routes(self) -> None:
        module = importlib.import_module("app_qt")

        class DummyTabs:
            def currentIndex(self) -> int:
                return 2

        calls: list[tuple[str, str | None, str | None]] = []
        window = SimpleNamespace(
            tabs=DummyTabs(),
            daily_pool_rows=[object()],
            current_trade_plan=SimpleNamespace(decisions=[object()]),
            order_intents=[],
            order_submission_records=[object()],
            paper_trading_state=PaperTradingState(
                enabled=True,
                positions=[PaperPosition(symbol="300001", stock_name="样本股", stock_id="300001", strategy_name="龙头模型")],
            ),
            _navigate_to_workspace=lambda workspace, widget=None, select_row=None: calls.append((workspace, widget, select_row)),
        )

        module.QuantHunterWindow._open_shell_workflow_stage(window, "recommend")
        module.QuantHunterWindow._open_shell_workflow_stage(window, "experiment")

        self.assertEqual(calls[0], ("recommend", "trade_plan_table", None))
        self.assertEqual(calls[1], ("broker", "paper_positions_table", None))

    def test_set_broker_execution_detail_visibility_updates_controls(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        window = SimpleNamespace(
            broker_result_box=module.QGroupBox(),
            broker_recap_box=module.QGroupBox(),
            broker_detail_toggle_button=module.QPushButton(),
            broker_detail_status_label=module.QLabel(),
            _set_label_text_if_changed=lambda label, text: label.setText(text) if label.text() != text else None,
        )

        module.QuantHunterWindow._set_broker_execution_detail_visibility_v40(window, False)
        self.assertFalse(window.broker_result_box.isVisible())
        self.assertEqual(window.broker_detail_toggle_button.text(), "展开执行明细")
        self.assertIn("执行明细已折叠", window.broker_detail_status_label.text())

        module.QuantHunterWindow._set_broker_execution_detail_visibility_v40(window, True)
        self.assertTrue(window.broker_result_box.isVisible())
        self.assertEqual(window.broker_detail_toggle_button.text(), "收起执行明细")
        self.assertIn("执行明细已展开", window.broker_detail_status_label.text())

    def test_build_paper_experiment_lines_highlights_verdict_and_next_round(self) -> None:
        module = importlib.import_module("app_qt")
        state = PaperTradingState(
            enabled=True,
            last_run_at="2026-04-14 10:30:00",
            last_strategy_note="本轮实验：龙头模型继续领先，先看第二轮复现。",
            patrol_logs=[
                PaperPatrolLog(
                    timestamp="2026-04-14 10:30:00",
                    event_type="CYCLE",
                    summary="本轮实验：龙头模型继续领先，先看第二轮复现。",
                    detail="卖出 2 笔，新开 1 笔",
                    equity=103500.0,
                    total_return=0.035,
                    position_count=2,
                )
            ],
        )
        analytics = {
            "closed_trade_count": 5,
            "win_rate": 0.6,
            "avg_hold_days": 1.4,
            "hold_cycle_sample_count": 3,
        }
        rotation_rows = [
            {
                "strategy_name": "龙头模型",
                "bias_label": "加权",
                "budget_multiplier": 1.18,
                "realized_pnl": 3200.0,
            },
            {
                "strategy_name": "价值低吸",
                "bias_label": "观察",
                "budget_multiplier": 0.92,
                "realized_pnl": 800.0,
            },
        ]

        lines = module._qh_build_paper_experiment_lines_v36(state, analytics, rotation_rows)
        text = "\n".join(lines)

        self.assertIn("实验结论：可继续加样本 | 闭环 5 | 胜率 60.0%", text)
        self.assertIn("主测战法：龙头模型 | 倾向 加权 x1.18 | 已实现 3,200", text)
        self.assertIn("对照战法：价值低吸 | 倾向 观察 x0.92", text)
        self.assertIn("最近实验：本轮实验：龙头模型继续领先，先看第二轮复现。", text)
        self.assertIn("下一轮建议：继续以 龙头模型 为主测", text)

    def test_paper_experiment_role_specs_builds_lead_compare_and_watch_slots(self) -> None:
        module = importlib.import_module("app_qt")
        state = PaperTradingState(enabled=True)
        analytics = {
            "closed_trade_count": 6,
            "win_rate": 0.6,
            "strategy_rows": [
                {"strategy_name": "龙头模型", "win_rate": 0.6},
                {"strategy_name": "价值低吸", "win_rate": 0.5},
                {"strategy_name": "尾盘买入法", "win_rate": 0.25},
            ],
        }
        rotation_rows = [
            {"strategy_name": "龙头模型", "bias_label": "加权", "budget_multiplier": 1.18, "sample_count": 6, "realized_pnl": 3200.0},
            {"strategy_name": "价值低吸", "bias_label": "观察", "budget_multiplier": 0.92, "sample_count": 4, "realized_pnl": 800.0},
            {"strategy_name": "尾盘买入法", "bias_label": "降权", "budget_multiplier": 0.68, "sample_count": 3, "realized_pnl": -1200.0},
        ]

        specs = module._qh_paper_experiment_role_specs_v43(state, analytics, rotation_rows)

        self.assertEqual(specs[0]["headline"], "主测战法：龙头模型")
        self.assertIn("样本 6", specs[0]["detail"])
        self.assertIn("胜率 60.0%", specs[0]["detail"])
        self.assertEqual(specs[1]["headline"], "对照战法：价值低吸")
        self.assertIn("保留对照", specs[1]["detail"])
        self.assertEqual(specs[2]["headline"], "降权观察：尾盘买入法")
        self.assertIn("降权或暂停", specs[2]["detail"])

    def test_paper_experiment_table_context_surfaces_role_deltas_and_decisions(self) -> None:
        module = importlib.import_module("app_qt")
        analytics = {
            "strategy_rows": [
                {
                    "strategy_name": "龙头模型",
                    "buy_count": 4,
                    "sell_count": 3,
                    "win_rate": 0.62,
                    "realized_pnl": 4200.0,
                    "avg_hold_days": 1.8,
                },
                {
                    "strategy_name": "价值低吸",
                    "buy_count": 3,
                    "sell_count": 2,
                    "win_rate": 0.5,
                    "realized_pnl": 1200.0,
                    "avg_hold_days": 1.1,
                },
                {
                    "strategy_name": "尾盘买入法",
                    "buy_count": 2,
                    "sell_count": 1,
                    "win_rate": 0.25,
                    "realized_pnl": -900.0,
                    "avg_hold_days": 2.6,
                },
            ]
        }
        rotation_rows = [
            {"strategy_name": "龙头模型", "bias_label": "加权", "budget_multiplier": 1.18, "sample_count": 7, "rotation_score": 0.32},
            {"strategy_name": "价值低吸", "bias_label": "中性", "budget_multiplier": 0.98, "sample_count": 5, "rotation_score": 0.04},
            {"strategy_name": "尾盘买入法", "bias_label": "降权", "budget_multiplier": 0.68, "sample_count": 3, "rotation_score": -0.27},
        ]

        contexts = module._qh_paper_experiment_table_context_v44(analytics, rotation_rows)

        self.assertEqual(contexts["龙头模型"]["role_label"], "主测")
        self.assertEqual(contexts["龙头模型"]["decision"], "继续主测")
        self.assertEqual(contexts["龙头模型"]["win_rate_delta"], 0.0)
        self.assertEqual(contexts["价值低吸"]["role_label"], "对照")
        self.assertEqual(contexts["价值低吸"]["decision"], "保留对照")
        self.assertAlmostEqual(float(contexts["价值低吸"]["win_rate_delta"]), -0.12, places=2)
        self.assertAlmostEqual(float(contexts["价值低吸"]["hold_delta"]), -0.7, places=2)
        self.assertEqual(contexts["尾盘买入法"]["role_label"], "观察")
        self.assertEqual(contexts["尾盘买入法"]["decision"], "降权观察")

    def test_paper_strategy_experiment_bridge_marks_strategy_role_and_cta(self) -> None:
        module = importlib.import_module("quant_hunter.ui_window_paper_experiment_patches")
        state = PaperTradingState(enabled=True)
        analytics = {
            "strategy_rows": [
                {
                    "strategy_name": "龙头模型",
                    "buy_count": 4,
                    "sell_count": 3,
                    "win_rate": 0.62,
                    "realized_pnl": 4200.0,
                    "avg_hold_days": 1.8,
                },
                {
                    "strategy_name": "价值低吸",
                    "buy_count": 3,
                    "sell_count": 2,
                    "win_rate": 0.5,
                    "realized_pnl": 1200.0,
                    "avg_hold_days": 1.1,
                },
            ]
        }
        rotation_rows = [
            {"strategy_name": "龙头模型", "bias_label": "加权", "budget_multiplier": 1.18, "sample_count": 7, "rotation_score": 0.32},
            {"strategy_name": "价值低吸", "bias_label": "中性", "budget_multiplier": 0.98, "sample_count": 5, "rotation_score": 0.04},
        ]

        lead = module.paper_strategy_experiment_bridge_v45(
            state,
            "龙头模型",
            analytics=analytics,
            rotation_rows=rotation_rows,
        )
        other = module.paper_strategy_experiment_bridge_v45(
            state,
            "尾盘买入法",
            analytics=analytics,
            rotation_rows=rotation_rows,
        )

        self.assertEqual(lead["badge"], "主测")
        self.assertIn("主测 | 龙头模型 | 继续主测", lead["title"])
        self.assertIn("样本 7", lead["detail"])
        self.assertIn("推荐页优先筛同战法前排", lead["cta"])
        self.assertEqual(other["badge"], "备选")
        self.assertIn("未进入实验前排 | 尾盘买入法", other["title"])
        self.assertIn("主测 龙头模型 | 对照 价值低吸", other["detail"])

    def test_refresh_recommend_decision_summary_surfaces_paper_experiment_bridge(self) -> None:
        module = importlib.import_module("app_qt")
        recommend_patches = importlib.import_module("quant_hunter.ui_window_recommend_patches")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        row = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="龙头样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-14",
            close=10.0,
            entry_price=10.0,
            stop_price=9.6,
            target_price=10.8,
            technical_score=86.0,
            position_score=77.0,
            persistence_score=82.0,
            news_score=73.0,
            leader_score=90.0,
            total_score=88.0,
            theme_name="机器人",
            mainline_tag="机器人",
            mainline_risk_flag="低",
            primary_strategy="龙头模型",
            rationale="主线龙头延续",
            next_focus="继续盯换手与承接。",
        )
        window = SimpleNamespace(
            recommend_decision_summary_label=module.QLabel(),
            recommend_decision_summary_text=module.QTextEdit(),
            recommend_push_focus_button=module.QPushButton(),
            recommend_detail_focus_button=module.QPushButton(),
            recommend_broker_focus_button=module.QPushButton(),
            paper_trading_state=PaperTradingState(enabled=True),
            current_trade_plan=SimpleNamespace(decisions=[]),
            current_position_advice=[],
            _current_recommend_focus=lambda: row,
            _stock_name_for_symbol=lambda _symbol: "龙头样本",
            _stock_id_for_symbol=lambda _symbol: "300001",
            _recommend_price_snapshot=lambda _row: {"upside_pct": 8.0, "downside_pct": 4.0, "rr_ratio": 2.0},
            _recommend_price_brief=lambda _row: "买点 10.00 -> 目标 10.80",
            _hype_logic_for_symbol=lambda _symbol, recommendation=None: getattr(recommendation, "rationale", ""),
            _news_digest_lines_for_symbol=lambda _symbol, limit=2: ["最近催化：机器人主线延续"],
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: widget.setText(text) if widget.text() != text else None,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text) if widget.toPlainText() != text else None,
        )

        with patch.object(module, "_qh_mainline_signal_brief_v4", return_value="继续跟"), patch.object(
            module, "_qh_signal_action_text_v4", return_value="买入"
        ), patch.object(
            module, "_qh_recommend_execution_summary_v24", return_value=("可继续跟踪", "主线和价位已对齐", True, True)
        ), patch.object(
            module, "_qh_recommend_focus_reason_v24", return_value="主线强度和位置都在前排"
        ), patch.object(
            module, "_qh_recommend_queue_snapshot_v25", return_value={"pending_review": [], "reviewing": [], "submitted": [], "failed": []}
        ), patch.object(
            module, "_qh_queue_sequence_summary", return_value="先看主线，再看价位"
        ), patch.object(
            module, "_qh_next_review_target", return_value="龙头样本"
        ), patch.object(
            module, "_qh_recommend_cta_labels_v37", return_value={"push": "推进送审", "detail": "查看复盘证据", "broker": "进入交易准备"}
        ), patch.object(
            recommend_patches,
            "paper_strategy_experiment_bridge_v45",
            return_value={
                "badge": "主测",
                "title": "主测 | 龙头模型 | 继续主测",
                "detail": "样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "cta": "推荐页优先筛同战法前排，交易页按主测纪律推进。",
            },
        ):
            module.QuantHunterWindow._refresh_recommend_decision_summary(window, row)

        text = window.recommend_decision_summary_text.toPlainText()
        self.assertIn("模拟盘联动：主测 | 龙头模型 | 继续主测", text)
        self.assertIn("实验提示：样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18", text)
        self.assertIn("实验 CTA：推荐页优先筛同战法前排，交易页按主测纪律推进。", text)
        self.assertIn("实验 主测", window.recommend_decision_summary_label.text())
        self.assertIn("模拟盘：主测 | 龙头模型 | 继续主测", window.recommend_push_focus_button.toolTip())
        self.assertIn("模拟盘：主测 | 龙头模型 | 继续主测", window.recommend_broker_focus_button.toolTip())

    def test_filtered_daily_pool_rows_supports_tail_buy_priority_view(self) -> None:
        module = importlib.import_module("app_qt")

        strong = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="强尾盘",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            theme_name="机器人",
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
            mainline_risk_flag="低",
        )
        weak = RecommendationRow(
            symbol="SZSE.301189",
            stock_id="301189",
            stock_name="弱尾盘",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=80.0,
            position_score=70.0,
            persistence_score=72.0,
            news_score=68.0,
            leader_score=70.0,
            total_score=79.0,
            theme_name="机器人",
            primary_strategy="尾盘买入法",
            tail_buy_score=77.0,
            execution_readiness=69.0,
            mainline_risk_flag="中",
        )
        other = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            primary_strategy="一日持股法",
            one_day_hold_score=88.0,
            execution_readiness=82.0,
            mainline_risk_flag="低",
        )
        window = SimpleNamespace(
            daily_pool_rows=[strong, weak, other],
            recommend_theme_filter="全部",
            recommend_strategy_filter="尾盘优选",
        )

        rows = module.QuantHunterWindow._filtered_daily_pool_rows(window)

        self.assertEqual([item.stock_id for item in rows], ["301188"])

    def test_set_market_filter_switches_tail_buy_to_priority_view(self) -> None:
        module = importlib.import_module("app_qt")

        class DummyButton:
            def __init__(self) -> None:
                self.checked = False

            def setChecked(self, value: bool) -> None:
                self.checked = value

        class DummyCombo:
            def __init__(self) -> None:
                self.value = ""

            def setCurrentText(self, value: str) -> None:
                self.value = value

        captured = {"populated": 0}
        window = SimpleNamespace(
            market_filter_buttons={key: DummyButton() for key in ("全部", "尾盘买入法")},
            strategy_detail_combo=DummyCombo(),
            _apply_market_filters=lambda: captured.__setitem__("applied", True),
            _populate_filtered_daily_pool_table=lambda: captured.__setitem__("populated", captured["populated"] + 1),
            market_status_label=None,
        )

        module.QuantHunterWindow.set_market_filter(window, "尾盘买入法")

        self.assertEqual(window.recommend_strategy_filter, "尾盘优选")
        self.assertEqual(window.strategy_detail_combo.value, "尾盘买入法")
        self.assertEqual(captured["populated"], 1)

    def test_overview_quick_routes_cover_trend_and_review_views(self) -> None:
        from quant_hunter.ui_config import OVERVIEW_QUICK_ROUTE_SPECS

        self.assertIn("主线龙头", OVERVIEW_QUICK_ROUTE_SPECS)
        self.assertIn("趋势机会", OVERVIEW_QUICK_ROUTE_SPECS)
        self.assertIn("消息催化", OVERVIEW_QUICK_ROUTE_SPECS)
        self.assertIn("买卖决策", OVERVIEW_QUICK_ROUTE_SPECS)
        self.assertIn("复盘研究", OVERVIEW_QUICK_ROUTE_SPECS)
        self.assertEqual(OVERVIEW_QUICK_ROUTE_SPECS["趋势机会"]["workspace"], "recommend")
        self.assertEqual(OVERVIEW_QUICK_ROUTE_SPECS["复盘研究"]["widget"], "recommend_review_text")

    def test_decision_engine_trade_rationale_contains_mainline_status(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Core Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=79.0,
                position_score=81.0,
                persistence_score=77.0,
                news_score=74.0,
                leader_score=83.0,
                total_score=82.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_window_score=78.0,
                theme_failure_risk=36.0,
                dragon_decision_score=86.0,
                stock_pool="龙头股",
                primary_strategy="龙头模型",
                rationale="core demo",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        self.assertIn("AI", plan.decisions[0].rationale)
        self.assertIn("核心龙头", plan.decisions[0].rationale)
        self.assertIn("窗口", plan.decisions[0].rationale)

    def test_decision_engine_prefers_continuation_signal_over_switch_warning(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="延续偏强",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.3,
                technical_score=82.0,
                position_score=79.0,
                persistence_score=77.0,
                news_score=74.0,
                leader_score=86.0,
                total_score=84.0,
                theme_name="AI",
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                mainline_window_score=86.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                dragon_decision_score=90.0,
                stock_pool="龙头股",
                primary_strategy="龙头模型",
                rationale="阶段 加速 | 信号 延续偏强",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="切换预警",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=11.0,
                entry_price=11.0,
                stop_price=10.4,
                target_price=12.0,
                technical_score=76.0,
                position_score=74.0,
                persistence_score=68.0,
                news_score=69.0,
                leader_score=78.0,
                total_score=78.0,
                theme_name="AI",
                theme_rank=2,
                mainline_tag="AI",
                mainline_rank=2,
                mainline_role="FRONT",
                mainline_strength_score=64.0,
                mainline_continuation_score=58.0,
                mainline_window_score=61.0,
                theme_divergence_score=63.0,
                theme_failure_risk=49.0,
                dragon_decision_score=81.0,
                stock_pool="趋势股",
                primary_strategy="主力雷达",
                rationale="阶段 分歧 | 信号 切换预警",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 2)
        self.assertEqual(plan.decisions[0].stock_id, "600000")
        self.assertEqual(plan.decisions[0].mainline_flow_signal, "延续偏强")
        self.assertEqual(plan.decisions[1].mainline_flow_signal, "切换预警")
        self.assertIn("信号 延续偏强", plan.decisions[0].rationale)
        self.assertGreater(plan.decisions[0].suggested_budget, plan.decisions[1].suggested_budget)

    def test_decision_engine_position_advice_reacts_to_switch_signals(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="切换预警仓",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=11.2,
                entry_price=11.2,
                stop_price=10.6,
                target_price=12.1,
                technical_score=75.0,
                position_score=73.0,
                persistence_score=67.0,
                news_score=68.0,
                leader_score=77.0,
                total_score=77.0,
                theme_name="AI",
                theme_rank=2,
                mainline_tag="AI",
                mainline_rank=2,
                mainline_role="FRONT",
                mainline_strength_score=74.0,
                mainline_continuation_score=58.0,
                mainline_window_score=61.0,
                theme_divergence_score=63.0,
                theme_failure_risk=49.0,
                stock_pool="趋势股",
                primary_strategy="主力雷达",
                rationale="阶段 分歧 | 信号 切换预警",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="切换退潮仓",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=9.8,
                entry_price=9.8,
                stop_price=9.1,
                target_price=10.5,
                technical_score=66.0,
                position_score=63.0,
                persistence_score=60.0,
                news_score=58.0,
                leader_score=64.0,
                total_score=65.0,
                theme_name="银行",
                theme_rank=5,
                mainline_tag="银行",
                mainline_rank=5,
                mainline_role="FOLLOW",
                mainline_strength_score=60.0,
                mainline_continuation_score=42.0,
                mainline_window_score=43.0,
                theme_divergence_score=54.0,
                theme_failure_risk=75.0,
                stock_pool="趋势股",
                primary_strategy="主力雷达",
                rationale="阶段 退潮 | 信号 切换/退潮",
            ),
        ]
        holdings = [
            HoldingRecord(
                symbol="SHSE.600000",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=11200.0,
            ),
            HoldingRecord(
                symbol="SZSE.000001",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=9800.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, holdings, available_cash=0, max_picks=5)

        advice_by_symbol = {item.symbol: item for item in plan.position_advice}
        self.assertEqual(advice_by_symbol["SHSE.600000"].action, "REDUCE")
        self.assertEqual(advice_by_symbol["SHSE.600000"].mainline_flow_signal, "切换预警")
        self.assertEqual(advice_by_symbol["SZSE.000001"].action, "SELL")
        self.assertEqual(advice_by_symbol["SZSE.000001"].mainline_flow_signal, "切换/退潮")

    def test_decision_engine_applies_one_day_hold_trade_profile(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300001",
                stock_id="300001",
                stock_name="一日样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.0,
                entry_price=10.0,
                stop_price=0.0,
                target_price=0.0,
                technical_score=86.0,
                position_score=76.0,
                persistence_score=80.0,
                news_score=78.0,
                leader_score=88.0,
                total_score=84.0,
                theme_name="机器人",
                theme_rank=1,
                stock_pool="趋势股",
                primary_strategy="一日持股法",
                buy_point="竞价转强后在 10.00 附近跟随",
                sell_point="次日冲高 3% 至 5% 优先兑现",
                rationale="隔日转强样本",
                dragon_decision_score=86.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        decision = plan.decisions[0]
        self.assertAlmostEqual(decision.planned_stop, 9.72, places=2)
        self.assertAlmostEqual(decision.planned_target, 10.55, places=2)
        self.assertAlmostEqual(decision.suggested_budget, 96000.0, places=2)
        self.assertIn("隔日", decision.rationale)
        self.assertIn("竞价", decision.next_focus)

    def test_decision_engine_applies_tail_buy_trade_profile(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.301188",
                stock_id="301188",
                stock_name="尾盘样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=15.8,
                entry_price=15.8,
                stop_price=0.0,
                target_price=0.0,
                technical_score=84.0,
                position_score=74.0,
                persistence_score=79.0,
                news_score=75.0,
                leader_score=77.0,
                total_score=83.0,
                theme_name="机器人",
                theme_rank=1,
                stock_pool="趋势股",
                primary_strategy="尾盘买入法",
                buy_point="仅在 14:30 之后确认尾盘回流后介入",
                sell_point="次日开盘优先兑现",
                rationale="尾盘回流样本",
                tail_buy_score=89.0,
                dragon_decision_score=85.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        decision = plan.decisions[0]
        self.assertAlmostEqual(decision.planned_stop, 15.42, places=2)
        self.assertAlmostEqual(decision.planned_target, 16.31, places=2)
        self.assertAlmostEqual(decision.suggested_budget, 82000.0, places=2)
        self.assertIn("次日开盘优先卖", decision.rationale)
        self.assertIn("14:30", decision.next_focus)

    def test_decision_engine_position_advice_respects_one_day_hold_discipline(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300001",
                stock_id="300001",
                stock_name="次日兑现样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=10.35,
                entry_price=10.1,
                stop_price=0.0,
                target_price=0.0,
                technical_score=80.0,
                position_score=76.0,
                persistence_score=74.0,
                news_score=72.0,
                leader_score=78.0,
                total_score=79.0,
                theme_name="机器人",
                theme_rank=1,
                stock_pool="趋势股",
                primary_strategy="一日持股法",
            ),
            RecommendationRow(
                symbol="SZSE.300002",
                stock_id="300002",
                stock_name="弱转弱样本",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=9.75,
                entry_price=9.9,
                stop_price=0.0,
                target_price=0.0,
                technical_score=71.0,
                position_score=74.0,
                persistence_score=69.0,
                news_score=66.0,
                leader_score=70.0,
                total_score=73.0,
                theme_name="机器人",
                theme_rank=2,
                stock_pool="趋势股",
                primary_strategy="一日持股法",
            ),
        ]
        holdings = [
            HoldingRecord(
                symbol="SZSE.300001",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=10350.0,
            ),
            HoldingRecord(
                symbol="SZSE.300002",
                quantity=1000,
                available=1000,
                cost_price=10.0,
                market_value=9750.0,
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, holdings, available_cash=0, max_picks=5)

        advice_by_symbol = {item.symbol: item for item in plan.position_advice}
        self.assertEqual(advice_by_symbol["SZSE.300001"].action, "REDUCE")
        self.assertIn("隔日兑现", advice_by_symbol["SZSE.300001"].rationale)
        self.assertEqual(advice_by_symbol["SZSE.300002"].action, "SELL")
        self.assertIn("未转强", advice_by_symbol["SZSE.300002"].rationale)

    def test_trade_decision_focus_lines_surfaces_one_day_hold_tempo(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )
        decision = TradeDecision(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            confidence=0.86,
            planned_entry=10.0,
            planned_stop=9.72,
            planned_target=10.55,
            suggested_budget=96000.0,
            rationale="一日持股法 | 隔日兑现",
            opportunity_tier="优先处理",
            execution_readiness=82.0,
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )

        lines = trade_decision_focus_lines(decision, recommendation)

        self.assertTrue(any("一日节奏" in line for line in lines))
        self.assertTrue(any("竞价" in line for line in lines))

    def test_trade_plan_execution_hint_uses_one_day_hold_specific_language(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )
        decision = TradeDecision(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            confidence=0.86,
            planned_entry=10.0,
            planned_stop=9.72,
            planned_target=10.55,
            suggested_budget=96000.0,
            rationale="一日持股法 | 隔日兑现",
            opportunity_tier="优先处理",
            execution_readiness=82.0,
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )

        hint = trade_plan_execution_hint(decision, recommendation)

        self.assertIn("竞价", hint)
        self.assertIn("兑现", hint)

    def test_position_advice_check_item_uses_one_day_hold_specific_language(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.35,
            entry_price=10.1,
            stop_price=9.72,
            target_price=10.55,
            technical_score=80.0,
            position_score=76.0,
            persistence_score=74.0,
            news_score=72.0,
            leader_score=78.0,
            total_score=79.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
        )
        advice = SimpleNamespace(action="REDUCE")

        hint = position_advice_check_item(advice, recommendation)

        self.assertIn("竞价", hint)
        self.assertIn("降仓", hint)

    def test_one_day_hold_phase_labels_cover_intraday_checks(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
        )
        decision = TradeDecision(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            confidence=0.86,
            planned_entry=10.0,
            planned_stop=9.72,
            planned_target=10.55,
            suggested_budget=96000.0,
            rationale="一日持股法 | 隔日兑现",
            opportunity_tier="优先处理",
            execution_readiness=82.0,
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )

        labels = one_day_hold_phase_labels(decision, recommendation)

        self.assertEqual(len(labels), 3)
        self.assertTrue(any("竞价检查" in item for item in labels))
        self.assertTrue(any("开盘5分" in item for item in labels))
        self.assertTrue(any("午后确认" in item for item in labels))

    def test_one_day_hold_grade_distinguishes_strength_levels(self) -> None:
        strong = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="强博弈样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            one_day_hold_score=88.0,
            execution_readiness=82.0,
            mainline_risk_flag="低",
        )
        medium = RecommendationRow(
            symbol="SZSE.300002",
            stock_id="300002",
            stock_name="轻试仓样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=78.0,
            position_score=74.0,
            persistence_score=74.0,
            news_score=72.0,
            leader_score=76.0,
            total_score=78.0,
            theme_name="机器人",
            theme_rank=2,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            one_day_hold_score=79.0,
            execution_readiness=70.0,
            mainline_risk_flag="中",
        )
        weak = RecommendationRow(
            symbol="SZSE.300003",
            stock_id="300003",
            stock_name="观察样本",
            action="WATCH",
            label="WATCH",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=70.0,
            position_score=68.0,
            persistence_score=66.0,
            news_score=64.0,
            leader_score=68.0,
            total_score=70.0,
            theme_name="机器人",
            theme_rank=3,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            one_day_hold_score=72.0,
            execution_readiness=62.0,
            mainline_risk_flag="高",
        )

        self.assertEqual(one_day_hold_grade(strong), "强博弈")
        self.assertEqual(one_day_hold_grade(medium), "轻试仓")
        self.assertEqual(one_day_hold_grade(weak), "只观察")

    def test_one_day_hold_tripwire_metrics_expose_three_intraday_checks(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="强博弈样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            one_day_hold_score=88.0,
            execution_readiness=82.0,
            mainline_window_score=84.0,
            mainline_continuation_score=79.0,
            mainline_risk_flag="低",
        )

        metrics = one_day_hold_tripwire_metrics(recommendation)

        self.assertEqual(len(metrics), 3)
        self.assertEqual(metrics[0][0], "竞价符合率")
        self.assertEqual(metrics[1][0], "开盘承接率")
        self.assertEqual(metrics[2][0], "午后转强率")
        self.assertTrue(all(0.0 <= item[1] <= 100.0 for item in metrics))
        self.assertTrue(any("优先盯" in item[2] or "可跟" in item[2] for item in metrics))

    def test_one_day_hold_tripwire_metrics_support_tail_buy_strategy(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
            mainline_window_score=80.0,
            mainline_continuation_score=76.0,
            mainline_risk_flag="低",
        )

        metrics = one_day_hold_tripwire_metrics(recommendation)

        self.assertEqual(len(metrics), 3)
        self.assertEqual(metrics[0][0], "尾盘确认率")
        self.assertEqual(metrics[1][0], "尾盘承接率")
        self.assertEqual(metrics[2][0], "开盘兑现率")

    def test_tail_buy_execution_checklist_surfaces_four_steps(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            theme_name="机器人",
            theme_rank=1,
            stock_pool="趋势股",
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
            mainline_window_score=80.0,
            mainline_risk_flag="低",
            next_focus="只在 14:30 后确认尾盘回流和承接，隔夜后次日开盘优先兑现。",
        )

        checklist = tail_buy_execution_checklist(recommendation)

        self.assertGreaterEqual(len(checklist), 4)
        self.assertTrue(any("14:30回流" in item for item in checklist))
        self.assertTrue(any("尾盘承接" in item for item in checklist))
        self.assertTrue(any("隔夜消息" in item for item in checklist))
        self.assertTrue(any("次日开盘" in item for item in checklist))

    def test_tail_buy_runtime_status_tracks_execution_windows(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
        )

        intraday_phase, intraday_hint = tail_buy_runtime_status(recommendation, datetime(2026, 4, 6, 14, 40))
        next_day_phase, next_day_hint = tail_buy_runtime_status(recommendation, datetime(2026, 4, 7, 9, 32))

        self.assertEqual(intraday_phase, "尾盘执行窗")
        self.assertIn("回流", intraday_hint)
        self.assertEqual(next_day_phase, "次日开盘兑现窗")
        self.assertIn("弱开直接走", next_day_hint)

    def test_tail_buy_runtime_panel_lines_build_execution_board(self) -> None:
        recommendation = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
            mainline_window_score=80.0,
            mainline_risk_flag="低",
        )

        panel_lines = tail_buy_runtime_panel_lines(recommendation, datetime(2026, 4, 6, 14, 40))

        self.assertGreaterEqual(len(panel_lines), 4)
        self.assertIn("当前阶段：尾盘执行窗", panel_lines[0])
        self.assertTrue(any("14:30" in item for item in panel_lines))
        self.assertTrue(any("次日开盘" in item for item in panel_lines))

    def test_refresh_recommend_focus_status_appends_tail_buy_runtime_phase(self) -> None:
        module = importlib.import_module("app_qt")

        class DummyLabel:
            def __init__(self) -> None:
                self.value = ""
                self.tooltip = ""

            def text(self) -> str:
                return self.value

            def setText(self, value: str) -> None:
                self.value = value

            def setToolTip(self, value: str) -> None:
                self.tooltip = value

            def toolTip(self) -> str:
                return self.tooltip

        row = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            theme_name="机器人",
            mainline_tag="机器人",
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
        )
        label = DummyLabel()
        window = SimpleNamespace(
            recommend_status_label=label,
            _set_label_text_if_changed=lambda widget, text: widget.setText(text),
            _current_recommend_focus=lambda: row,
            _stock_name_for_symbol=lambda _symbol: "尾盘样本",
            _stock_id_for_symbol=lambda _symbol: "301188",
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _recommend_price_brief=lambda _row: "计划买点 15.80 | 止损 15.40 | 目标 16.30",
            _news_digest_lines_for_symbol=lambda _symbol, limit=1: ["尾盘回流催化"],
        )

        def _fake_original(self, _row=None) -> None:
            self.recommend_status_label.setText("推荐状态：尾盘样本 | 机器人 | 买入 | 执行准备 80.0 | 置信 0.0")

        with patch.object(module, "_ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_STATUS_V23", _fake_original):
            with patch.object(module, "tail_buy_runtime_status", return_value=("尾盘执行窗", "回流与承接共振时再试仓，准备隔夜但不追拉升。")):
                module._qh_refresh_recommend_focus_status_v23(window, row)

        self.assertIn("尾盘阶段 尾盘执行窗", label.text())
        self.assertIn("尾盘阶段：尾盘执行窗", label.toolTip())
        self.assertIn("执行节奏：回流与承接共振时再试仓", label.toolTip())

    def test_refresh_recommend_focus_cards_promotes_tail_buy_execution_board(self) -> None:
        module = importlib.import_module("app_qt")

        class DummyCard:
            def __init__(self) -> None:
                self.data = None

            def set_data(self, title, value) -> None:
                self.data = (title, value)

        row = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            execution_readiness=80.0,
        )
        window = SimpleNamespace(
            recommend_summary_cards={key: DummyCard() for key in ("logic", "plan", "pulse", "holding")},
            _current_recommend_focus=lambda: row,
        )

        with patch.object(module, "_ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_CARDS_V8", lambda _self, _row=None: None):
            with patch.object(module, "tail_buy_runtime_status", return_value=("尾盘执行窗", "回流与承接共振时再试仓，准备隔夜但不追拉升。")):
                with patch.object(
                    module,
                    "tail_buy_runtime_panel_lines",
                    return_value=[
                        "当前阶段：尾盘执行窗",
                        "执行提示：回流与承接共振时再试仓，准备隔夜但不追拉升。",
                        "[当前] 14:30回流 | 可重点盯回流确认再动手",
                        "[待命] 次日开盘 | 优先兑现，不做拖仓",
                    ],
                ):
                    module._qh_refresh_recommend_focus_cards_v8(window, row)

        self.assertEqual(window.recommend_summary_cards["plan"].data[0], "尾盘执行阶段")
        self.assertIn("尾盘执行窗", window.recommend_summary_cards["plan"].data[1])
        self.assertIn("14:30回流", window.recommend_summary_cards["pulse"].data[1])
        self.assertIn("次日开盘", window.recommend_summary_cards["holding"].data[1])

    def test_refresh_strategy_focus_detail_surfaces_one_day_hold_tripwire_metrics(self) -> None:
        from quant_hunter import ui_refresh
        from quant_hunter.ui_config import STRATEGY_SCORE_FIELDS

        class DummyText:
            def __init__(self) -> None:
                self.value = ""

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyCombo:
            def currentText(self) -> str:
                return "一日持股法"

        class DummyTable:
            def currentRow(self) -> int:
                return 0

        row = RecommendationRow(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="一日样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=10.0,
            entry_price=10.0,
            stop_price=9.72,
            target_price=10.55,
            technical_score=86.0,
            position_score=76.0,
            persistence_score=80.0,
            news_score=78.0,
            leader_score=88.0,
            total_score=84.0,
            theme_name="机器人",
            theme_rank=1,
            mainline_tag="机器人",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=84.0,
            mainline_continuation_score=79.0,
            mainline_risk_flag="低",
            catalyst="隔日博弈催化",
            rationale="适合隔日节奏",
            stock_pool="趋势股",
            primary_strategy="一日持股法",
            one_day_hold_score=88.0,
            dragon_decision_score=83.0,
            execution_readiness=82.0,
            buy_point="竞价转强后在 10.00 附近跟随",
            sell_point="冲高到 10.55 附近先兑现",
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
        )
        window = SimpleNamespace(
            strategy_detail_text=DummyText(),
            strategy_detail_combo=DummyCombo(),
            daily_pool_table=DummyTable(),
            daily_pool_rows=[row],
            _filtered_daily_pool_rows=lambda: [row],
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _display_mainline_role=lambda value: {"CORE": "核心龙头"}.get(value, value),
            _display_leader_level=lambda value: value or "前排",
        )

        ui_refresh.refresh_strategy_focus_detail(window, STRATEGY_SCORE_FIELDS)

        text = window.strategy_detail_text.toPlainText()
        self.assertIn("隔日三段判断", text)
        self.assertIn("博弈等级：强博弈", text)
        self.assertIn("竞价符合率", text)
        self.assertIn("开盘承接率", text)
        self.assertIn("午后转强率", text)

    def test_refresh_strategy_focus_detail_surfaces_tail_buy_checklist(self) -> None:
        from quant_hunter import ui_refresh
        from quant_hunter.ui_config import STRATEGY_SCORE_FIELDS

        class DummyText:
            def __init__(self) -> None:
                self.value = ""

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyCombo:
            def currentText(self) -> str:
                return "尾盘买入法"

        class DummyTable:
            def currentRow(self) -> int:
                return 0

        row = RecommendationRow(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="尾盘样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=15.8,
            entry_price=15.8,
            stop_price=15.4,
            target_price=16.3,
            technical_score=84.0,
            position_score=74.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=77.0,
            total_score=83.0,
            theme_name="机器人",
            theme_rank=1,
            mainline_tag="机器人",
            mainline_rank=1,
            mainline_role="FRONT",
            mainline_window_score=80.0,
            mainline_continuation_score=76.0,
            mainline_risk_flag="低",
            catalyst="尾盘回流催化",
            rationale="适合尾盘隔夜",
            stock_pool="趋势股",
            primary_strategy="尾盘买入法",
            tail_buy_score=89.0,
            dragon_decision_score=84.0,
            execution_readiness=80.0,
            buy_point="仅在 14:30 之后确认尾盘回流后介入",
            sell_point="次日开盘优先兑现",
            next_focus="只在 14:30 后确认尾盘回流和承接，隔夜后次日开盘优先兑现。",
        )
        window = SimpleNamespace(
            strategy_detail_text=DummyText(),
            strategy_detail_combo=DummyCombo(),
            daily_pool_table=DummyTable(),
            daily_pool_rows=[row],
            _filtered_daily_pool_rows=lambda: [row],
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _display_mainline_role=lambda value: {"FRONT": "前排核心"}.get(value, value),
            _display_leader_level=lambda value: value or "前排",
        )

        with patch.object(
            ui_refresh,
            "tail_buy_runtime_panel_lines",
            return_value=[
                "当前阶段：尾盘执行窗",
                "执行提示：回流与承接共振时再试仓，准备隔夜但不追拉升。",
                "[当前] 14:30回流 | 可重点盯回流确认再动手",
                "[待命] 次日开盘 | 优先兑现，不做拖仓",
            ],
        ):
            ui_refresh.refresh_strategy_focus_detail(window, STRATEGY_SCORE_FIELDS)

        text = window.strategy_detail_text.toPlainText()
        self.assertIn("尾盘执行面板", text)
        self.assertIn("当前阶段：尾盘执行窗", text)
        self.assertIn("尾盘 checklist", text)
        self.assertIn("14:30回流", text)
        self.assertIn("尾盘承接", text)
        self.assertIn("隔夜消息", text)
        self.assertIn("次日开盘", text)

    def test_refresh_strategy_focus_detail_surfaces_commercial_strategy_labels(self) -> None:
        from quant_hunter import ui_refresh
        from quant_hunter.ui_config import STRATEGY_SCORE_FIELDS

        class DummyText:
            def __init__(self) -> None:
                self.value = ""

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyCombo:
            def currentText(self) -> str:
                return "价值低吸"

        class DummyTable:
            def currentRow(self) -> int:
                return 0

        row = RecommendationRow(
            symbol="SZSE.002111",
            stock_id="002111",
            stock_name="低吸样本",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-06",
            close=12.6,
            entry_price=12.5,
            stop_price=12.0,
            target_price=13.4,
            technical_score=79.0,
            position_score=73.0,
            persistence_score=76.0,
            news_score=68.0,
            leader_score=70.0,
            total_score=80.0,
            theme_name="机器人",
            theme_rank=2,
            mainline_tag="机器人",
            mainline_rank=2,
            mainline_role="FOLLOW",
            mainline_window_score=71.0,
            mainline_continuation_score=69.0,
            mainline_risk_flag="低",
            catalyst="板块修复预期",
            rationale="回踩承接较稳",
            stock_pool="价值池",
            primary_strategy="价值低吸",
            value_recovery_score=86.0,
            dragon_decision_score=78.0,
            execution_readiness=74.0,
            buy_point="回踩 12.50 一线企稳后分批低吸",
            sell_point="修复到 13.40 一线分批兑现",
            next_focus="先看回踩后的承接是否稳定，再看修复强度。",
            invalidation_reason="跌破 12.00 防守线后停止低吸。",
        )
        window = SimpleNamespace(
            strategy_detail_text=DummyText(),
            strategy_detail_combo=DummyCombo(),
            daily_pool_table=DummyTable(),
            daily_pool_rows=[row],
            _filtered_daily_pool_rows=lambda: [row],
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _display_mainline_role=lambda value: {"FOLLOW": "跟随核心"}.get(value, value),
            _display_leader_level=lambda value: value or "前排",
        )

        ui_refresh.refresh_strategy_focus_detail(window, STRATEGY_SCORE_FIELDS)

        text = window.strategy_detail_text.toPlainText()
        self.assertIn("战法定位", text)
        self.assertIn("产品定位：修复型低吸", text)
        self.assertIn("风险等级：中低风险", text)
        self.assertIn("适合资金：分批低吸 / 修复博弈", text)
        self.assertIn("仓位建议：优先分批吸，不要一次性打满。", text)
        self.assertIn("禁做情形：修复逻辑不成立、承接不足、跌破防守位时不做。", text)
        self.assertIn("商品说明", text)
        self.assertIn("适用行情：适合主线分歧后的回踩修复、承接重新回流、追高性价比偏低的行情。", text)
        self.assertIn("容量上限：更适合中等容量分批布局，不适合在无承接时一次性打满。", text)
        self.assertIn("标准动作：先等回踩企稳，再分批低吸；修复到 13.40 一线分批兑现", text)
        self.assertIn("失败样本：最容易失败在修复预期落空、承接不足、跌破 12.00 防守线后停止低吸。后还继续摊低成本。", text)

    def test_refresh_trade_plan_focus_label_surfaces_one_day_hold_grade(self) -> None:
        module = importlib.import_module("app_qt")

        class _Sink:
            def __init__(self) -> None:
                self.value = ""

            def text(self) -> str:
                return self.value

            def setText(self, value: str) -> None:
                self.value = value

        window = SimpleNamespace(
            current_trade_plan=SimpleNamespace(
                decisions=[
                    SimpleNamespace(
                        symbol="SZSE.300001",
                        stock_name="一日样本",
                        action="BUY",
                        mainline_flow_signal="延续偏强",
                        mainline_stage="加速",
                    )
                ]
            ),
            daily_pool_rows=[
                RecommendationRow(
                    symbol="SZSE.300001",
                    stock_id="300001",
                    stock_name="一日样本",
                    action="BUY",
                    label="RECLAIM_LONG",
                    signal_date="2026-04-06",
                    close=10.0,
                    entry_price=10.0,
                    stop_price=9.72,
                    target_price=10.55,
                    technical_score=86.0,
                    position_score=76.0,
                    persistence_score=80.0,
                    news_score=78.0,
                    leader_score=88.0,
                    total_score=84.0,
                    theme_name="机器人",
                    theme_rank=1,
                    mainline_risk_flag="低",
                    stock_pool="趋势股",
                    primary_strategy="一日持股法",
                    one_day_hold_score=88.0,
                    execution_readiness=82.0,
                )
            ],
            trade_plan_focus_label=_Sink(),
            _set_label_text_if_changed=lambda widget, text: widget.setText(text),
        )

        with patch.object(module, "_ORIGINAL_QH_REFRESH_TRADE_PLAN_V7", lambda _window: None):
            module._qh_refresh_trade_plan_v5(window)

        self.assertIn("隔日 强博弈", window.trade_plan_focus_label.text())

    def test_decision_engine_market_pulse_exposes_flow_signal(self) -> None:
        recommendations = [
            RecommendationRow(
                symbol="SZSE.300024",
                stock_id="300024",
                stock_name="机器人核心",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-06",
                close=28.5,
                entry_price=28.5,
                stop_price=27.2,
                target_price=31.8,
                technical_score=90.0,
                position_score=84.0,
                persistence_score=88.0,
                news_score=82.0,
                leader_score=92.0,
                total_score=91.0,
                theme_name="人工智能",
                mainline_tag="人工智能",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_continuation_score=76.0,
                mainline_window_score=86.0,
                theme_divergence_score=28.0,
                theme_failure_risk=18.0,
                rationale="阶段 加速 | 信号 延续偏强",
            ),
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(plan.market_pulse.mainline_flow_signal, "延续偏强")
        self.assertGreater(plan.market_pulse.mainline_flow_score, 80.0)
        self.assertTrue(any("市场脉冲信号" in note for note in plan.notes))

    def test_generate_order_suggestions_controller_prefers_trade_plan_decisions(self) -> None:
        from quant_hunter import ui_controllers

        calls = {"filled": False, "info": 0}

        class DummyInput:
            def text(self) -> str:
                return "30000"

        class DummyAdapter:
            @staticmethod
            def build_order_intents(_rows, _budget):
                raise AssertionError("should use current trade plan decisions first")

        window = SimpleNamespace(
            scan_rows=[],
            current_trade_plan=SimpleNamespace(
                decisions=[
                    SimpleNamespace(
                        symbol="SHSE.600000",
                        action="BUY",
                        planned_entry=10.0,
                        planned_stop=9.5,
                        planned_target=11.2,
                        suggested_budget=12000.0,
                        rationale="主线核心出手",
                    )
                ]
            ),
            state=SimpleNamespace(watchlist=[]),
            per_trade_budget_input=DummyInput(),
            order_intents=[],
            _fill_orders=lambda: calls.__setitem__("filled", True),
            _refresh_broker_status=lambda extra="": calls.__setitem__("status_extra", extra),
        )

        ui_controllers.generate_order_suggestions_controller(
            window,
            adapter_cls=DummyAdapter,
            info_dialog_fn=lambda *_args, **_kwargs: calls.__setitem__("info", calls["info"] + 1),
            error_dialog_fn=lambda *_args, **_kwargs: calls.__setitem__("error", True),
        )

        self.assertTrue(calls["filled"])
        self.assertEqual(calls["info"], 0)
        self.assertEqual(len(window.order_intents), 1)
        self.assertEqual(window.order_intents[0].symbol, "SHSE.600000")
        self.assertEqual(window.order_intents[0].signal_date, "计划股")
        self.assertEqual(window.order_intents[0].quantity, 1200)

    def test_prepare_order_submission_controller_blocks_mainline_rejected_orders(self) -> None:
        from quant_hunter import ui_controllers
        from quant_hunter.models import OrderIntent

        status = {"extra": ""}

        class DummyAdapter:
            def diagnose_environment(self, _profile):
                return {
                    "python_version": "3.13",
                    "sdk_module": "gm.api",
                    "module_installed": True,
                    "bridge_python": "",
                    "bridge_module_installed": False,
                    "bridge_ready": False,
                    "direct_ready": True,
                }

        window = SimpleNamespace(
            order_intents=[
                OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.5,
                    target_price=11.2,
                    signal_date="计划股",
                    reason="主线风险过高",
                )
            ],
            generate_order_suggestions=lambda: None,
            _mainline_gate_for_order_intent=lambda _intent: (False, "主线风险偏高"),
            _refresh_broker_status=lambda extra="": status.__setitem__("extra", extra),
            current_broker_profile=lambda: SimpleNamespace(
                export_dir="",
                token="demo-token",
                strategy_id="demo-strategy",
                account_id="demo-account",
                mode="export",
                sdk_module="gm.api",
            ),
            holdings=[],
            cash_snapshot=None,
            daily_pool_rows=[],
        )

        prepared = ui_controllers.prepare_order_submission_controller(
            window,
            adapter_cls=DummyAdapter,
            confirmation_dialog_cls=SimpleNamespace(confirm=lambda *_args, **_kwargs: True),
        )

        self.assertIsNone(prepared)
        self.assertIn("提交前硬拦截", status["extra"])

    def test_prepare_order_submission_controller_uses_keyword_arguments_for_confirmation(self) -> None:
        from quant_hunter import ui_controllers
        from quant_hunter.models import OrderIntent, PaperTradingState

        captured = {}
        status = {"extra": ""}

        class DummyAdapter:
            def diagnose_environment(self, _profile):
                return {
                    "python_version": "3.13",
                    "sdk_module": "gm.api",
                    "module_installed": True,
                    "bridge_python": "",
                    "bridge_module_installed": False,
                    "bridge_ready": False,
                    "direct_ready": True,
                }

        def confirm(**kwargs):
            captured.update(kwargs)
            return False

        window = SimpleNamespace(
            order_intents=[
                OrderIntent(
                    symbol="SHSE.600000",
                    side="SELL",
                    price=10.0,
                    quantity=100,
                    stop_price=9.5,
                    target_price=11.2,
                    signal_date="计划股",
                    reason="减仓确认",
                )
            ],
            generate_order_suggestions=lambda: None,
            _refresh_broker_status=lambda extra="": status.__setitem__("extra", extra),
            current_broker_profile=lambda: SimpleNamespace(
                export_dir="exports",
                token="demo-token",
                strategy_id="demo-strategy",
                account_id="demo-account",
                mode="export",
                sdk_module="gm.api",
            ),
            holdings=[
                HoldingRecord(
                    symbol="SHSE.600000",
                    quantity=100,
                    available=100,
                    cost_price=9.8,
                    market_value=1000.0,
                )
            ],
            cash_snapshot=None,
            daily_pool_rows=[SimpleNamespace(symbol="SHSE.600000", primary_strategy="龙头模型")],
            paper_trading_state=PaperTradingState(enabled=True),
        )

        with patch.object(
            ui_controllers,
            "paper_strategy_experiment_bridge_v45",
            return_value={
                "badge": "主测",
                "title": "主测 | 龙头模型 | 继续主测",
                "detail": "样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "cta": "推荐页优先筛同战法前排，交易页按主测纪律推进。",
            },
        ):
            prepared = ui_controllers.prepare_order_submission_controller(
                window,
                adapter_cls=DummyAdapter,
                confirmation_dialog_cls=SimpleNamespace(confirm=confirm),
            )

        self.assertIsNone(prepared)
        self.assertIs(captured["parent"], window)
        self.assertEqual(captured["recommendations"], window.daily_pool_rows)
        self.assertEqual(captured["intents"], window.order_intents)
        self.assertEqual(captured["strategy_name"], "龙头模型")
        self.assertEqual(captured["experiment_bridge"]["badge"], "主测")
        self.assertIn("本次提交已取消", status["extra"])
        self.assertTrue(hasattr(window, "last_broker_execution_summary"))

    def test_save_strategy_preferences_controller_persists_risk_profile(self) -> None:
        from quant_hunter import ui_controllers

        class DummyCombo:
            def currentData(self):
                return "conservative"

        class DummyCheckbox:
            def isChecked(self):
                return True

        calls = {"saved": 0, "license": 0, "pool": 0, "monitor": 0}
        window = SimpleNamespace(
            state=SimpleNamespace(
                strategy_risk_profile="standard",
                strategy_top_theme_limit=3,
                strategy_max_total_exposure=0.85,
                strategy_theme_drop_reduce=True,
                focus_themes=[],
                auto_daily_plan_export=False,
                daily_plan_template="balanced",
                daily_plan_focus_only=False,
                daily_plan_candidate_limit=10,
            ),
            strategy_risk_profile_combo=DummyCombo(),
            auto_daily_plan_export_checkbox=DummyCheckbox(),
            _current_strategy_runtime_config=lambda: (4, 0.65, False),
            _parse_focus_themes=lambda: ["银行", "机器人"],
            _current_report_template_config=lambda: ("focus", True, 8),
            save_state=lambda: calls.__setitem__("saved", calls["saved"] + 1),
            _refresh_license_status_view=lambda: calls.__setitem__("license", calls["license"] + 1),
            refresh_daily_pool=lambda: calls.__setitem__("pool", calls["pool"] + 1),
            _refresh_intraday_monitor=lambda: calls.__setitem__("monitor", calls["monitor"] + 1),
        )

        ui_controllers.save_strategy_preferences_controller(window, info_dialog_fn=lambda *_args, **_kwargs: None)

        self.assertEqual(window.state.strategy_risk_profile, "conservative")
        self.assertEqual(window.state.strategy_top_theme_limit, 4)
        self.assertAlmostEqual(window.state.strategy_max_total_exposure, 0.65)
        self.assertEqual(window.state.focus_themes, ["银行", "机器人"])
        self.assertEqual(window.state.daily_plan_template, "focus")
        self.assertEqual(calls["saved"], 1)
        self.assertEqual(calls["license"], 1)
        self.assertEqual(calls["pool"], 1)
        self.assertEqual(calls["monitor"], 1)

    def test_order_confirmation_dialog_surfaces_experiment_guardrails(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        class DummyAdapter:
            def diagnose_environment(self, _profile):
                return {
                    "bridge_python": "",
                    "direct_ready": True,
                    "bridge_ready": False,
                }

        dialog = module.OrderConfirmationDialog(
            SimpleNamespace(
                account_name="演示账户",
                account_id="demo-account",
                strategy_id="demo-strategy",
                mode="export",
                sdk_module="gm.api",
            ),
            [
                OrderIntent(
                    symbol="SHSE.600000",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    stop_price=9.5,
                    target_price=11.2,
                    signal_date="计划股",
                    reason="主测推进",
                )
            ],
            DummyAdapter(),
            strategy_name="龙头模型",
            experiment_bridge={
                "badge": "主测",
                "title": "主测 | 龙头模型 | 继续主测",
                "detail": "样本 7 | 胜率 62.0% | 平均持有 1.8 天 | 预算 x1.18",
                "cta": "推荐页优先筛同战法前排，交易页按主测纪律推进。",
            },
        )
        try:
            self.assertIn("当前战法：龙头模型", dialog.summary_text.toPlainText())
            self.assertIn("实验结论：主测 | 龙头模型 | 继续主测", dialog.experiment_text.toPlainText())
            self.assertIn("真实交易建议：可以继续推进", dialog.experiment_text.toPlainText())
            self.assertIn("下一步：推荐页优先筛同战法前排", dialog.experiment_text.toPlainText())
            self.assertIn("模拟盘结论与风险", dialog.confirm_checkbox.text())
        finally:
            dialog.close()
            app.processEvents()

    def test_report_recommendation_sorting_prefers_mainline_over_raw_total_score(self) -> None:
        from quant_hunter import reports

        recommendations = [
            RecommendationRow(
                symbol="SHSE.600000",
                stock_id="600000",
                stock_name="Score Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=90.0,
                position_score=82.0,
                persistence_score=76.0,
                news_score=70.0,
                leader_score=72.0,
                total_score=92.0,
                theme_name="杂题材",
                theme_score=80.0,
                theme_rank=4,
                mainline_tag="杂题材",
                mainline_rank=4,
                mainline_role="FOLLOW",
                mainline_strength_score=72.0,
                mainline_window_score=46.0,
                theme_failure_risk=72.0,
                rationale="score demo",
            ),
            RecommendationRow(
                symbol="SZSE.000001",
                stock_id="000001",
                stock_name="Mainline Demo",
                action="BUY",
                label="RECLAIM_LONG",
                signal_date="2026-04-05",
                close=10.0,
                entry_price=10.0,
                stop_price=9.5,
                target_price=11.2,
                technical_score=79.0,
                position_score=81.0,
                persistence_score=77.0,
                news_score=74.0,
                leader_score=83.0,
                total_score=82.0,
                theme_name="AI",
                theme_score=84.0,
                theme_rank=1,
                mainline_tag="AI",
                mainline_rank=1,
                mainline_role="CORE",
                mainline_strength_score=88.0,
                mainline_window_score=78.0,
                theme_failure_risk=36.0,
                rationale="mainline demo",
            ),
        ]

        filtered = reports._filter_recommendations_for_plan(
            recommendations,
            focus_themes=[],
            template_name="balanced",
            focus_only=False,
            candidate_limit=10,
        )

        self.assertEqual(filtered[0].stock_id, "000001")


if __name__ == "__main__":
    unittest.main()

