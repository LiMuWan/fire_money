from __future__ import annotations

import csv
import importlib
import os
import unittest
from pathlib import Path
from unittest.mock import patch

import quant_hunter.broker as broker_module
import quant_hunter.ui_binders as ui_binders_module
from quant_hunter.broker import EastmoneyBrokerAdapter
from quant_hunter.backtest import Backtester
from quant_hunter.board import BoardModeEngine
from quant_hunter.decision import DecisionEngine
from quant_hunter.data import (
    load_bars_from_csv,
    load_news_catalysts_from_csv,
    load_stock_profiles_from_csv,
    load_theme_aliases_from_csv,
)
from quant_hunter.market_feed import EastmoneyMarketFeed, LocalMarketCache, MarketSnapshot, RemoteMarketScreener
from quant_hunter.models import BrokerProfile, CashSnapshot, HoldingRecord, PriceBar, RecommendationRow, ScanRow
from quant_hunter.optimizer import ParameterOptimizer
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review
from quant_hunter.scanner import UniverseScanner
from quant_hunter.storage import AppState, load_app_state, save_app_state
from quant_hunter.strategy import AntiHarvestStrategy, StrategyParams
from quant_hunter.theme import summarize_themes
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

    def test_backtest_produces_trade(self) -> None:
        path = self._write_demo_csv("backtest_demo.csv")
        bars = load_bars_from_csv(path)
        analyses = AntiHarvestStrategy(StrategyParams()).analyze(bars)
        result = Backtester().run(bars, analyses)

        self.assertGreaterEqual(len(result.trades), 1)
        self.assertGreater(result.ending_equity, 0)

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
        ui_refresh = importlib.import_module("quant_hunter.ui_refresh")
        ui_runtime = importlib.import_module("quant_hunter.ui_runtime")
        workspace_builders = importlib.import_module("quant_hunter.workspace_builders")
        self.assertTrue(hasattr(module, "QuantHunterWindow"))
        self.assertTrue(hasattr(module, "InsightCardBase"))
        self.assertTrue(hasattr(module, "StrategyWorkbenchCard"))
        self.assertTrue(hasattr(module, "ActionFlowCard"))
        self.assertTrue(hasattr(module, "CompactSummaryCard"))
        self.assertTrue(hasattr(module, "AlertSignalCard"))
        self.assertTrue(hasattr(ui_cards, "LeaderboardCard"))
        self.assertTrue(hasattr(ui_config, "WORKSPACE_TAB_ORDER"))
        self.assertTrue(hasattr(ui_binders, "apply_daily_pool_rows"))
        self.assertTrue(hasattr(ui_binders, "apply_market_screen_result"))
        self.assertTrue(hasattr(ui_binders, "apply_scan_universe_result"))
        self.assertTrue(hasattr(ui_binders, "handle_daily_pool_error"))
        self.assertTrue(hasattr(ui_binders, "handle_market_refresh_error"))
        self.assertTrue(hasattr(ui_binders, "handle_scan_error"))
        self.assertTrue(hasattr(ui_binders, "refresh_license_status_view"))
        self.assertTrue(hasattr(ui_controllers, "refresh_daily_pool_controller"))
        self.assertTrue(hasattr(ui_controllers, "refresh_remote_market_controller"))
        self.assertTrue(hasattr(ui_controllers, "run_background_job_controller"))
        self.assertTrue(hasattr(ui_controllers, "run_parameter_optimization_controller"))
        self.assertTrue(hasattr(ui_controllers, "save_strategy_preferences_controller"))
        self.assertTrue(hasattr(ui_controllers, "switch_license_plan_controller"))
        self.assertTrue(hasattr(ui_runtime, "build_runtime_overview_text"))
        self.assertTrue(hasattr(ui_runtime, "append_runtime_log"))
        self.assertTrue(hasattr(ui_runtime, "clear_market_cache"))
        self.assertTrue(hasattr(ui_runtime, "record_job_result"))
        self.assertTrue(hasattr(ui_runtime, "refresh_runtime_panel"))
        self.assertTrue(hasattr(ui_runtime, "runtime_export_dir"))
        self.assertTrue(hasattr(ui_runtime, "export_runtime_log"))
        self.assertTrue(hasattr(ui_helpers, "build_workspace_hero"))
        self.assertTrue(hasattr(ui_refresh, "refresh_priority_cards"))
        self.assertTrue(hasattr(ui_refresh, "render_leaderboard_cards"))
        self.assertTrue(hasattr(ui_refresh, "refresh_theme_heat_panels"))
        self.assertTrue(hasattr(ui_refresh, "apply_market_filters"))
        self.assertTrue(hasattr(ui_refresh, "fill_scan_rows"))
        self.assertTrue(hasattr(ui_refresh, "refresh_intraday_monitor"))
        self.assertTrue(hasattr(workspace_builders, "build_auth_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_board_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_broker_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_config_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_overview_workspace"))
        self.assertTrue(hasattr(workspace_builders, "build_recommend_workspace"))

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
            finally:
                window.close()
                app.processEvents()

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
        self.assertIn("收盘复盘日报", markdown)
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
        self.assertIn("盘前交易计划", markdown)
        self.assertIn("授权方案: TRIAL", markdown)
        self.assertIn("用户关注题材: 银行", markdown)
        self.assertIn("市场周期", markdown)
        self.assertIn("今日主线题材", markdown)
        self.assertIn('"focus_themes": [', payload)

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
        self.assertIn(leader_rows[0].leader_level, {"CORE_LEADER", "ACTIVE_LEADER"})

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
                market_theme_filter="主力雷达",
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.theme_alias_path, "sample_data/theme_aliases.csv")
        self.assertEqual(restored.recommend_theme_filter, "银行")
        self.assertEqual(restored.market_theme_filter, "主力雷达")

    def test_app_state_persists_strategy_and_license_settings(self) -> None:
        state_path = self._temp_dir() / "app_state_strategy.json"
        save_app_state(
            state_path,
            AppState(
                focus_themes=["银行", "机器人"],
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
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.focus_themes, ["银行", "机器人"])
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
        self.assertIn(item.primary_strategy, {"龙头模型", "主力雷达", "擒龙打板", "价值低吸", "掘龙决策"})
        self.assertGreater(item.leader_model_score, 0.0)
        self.assertGreater(item.main_force_score, 0.0)
        self.assertGreater(item.board_attack_score, 0.0)
        self.assertGreater(item.value_recovery_score, 0.0)
        self.assertGreater(item.dragon_decision_score, 0.0)

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


if __name__ == "__main__":
    unittest.main()
