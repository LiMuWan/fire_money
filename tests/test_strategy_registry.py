from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from quant_hunter.board import BoardPlan
from quant_hunter.decision import DecisionEngine
from quant_hunter.models import HoldingRecord, RecommendationRow, ScanRow
from quant_hunter.paper_trading import PaperTradingEngine
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review
from quant_hunter.strategy_registry import (
    build_strategy_template_payload,
    get_strategy_filter_labels,
    get_strategy_registry,
    get_strategy_score_fields,
    get_strategy_workbench_specs,
    ranked_strategy_scores,
    reload_strategy_registry,
    save_strategy_catalog_payload,
    strategy_buy_position_meta,
    strategy_execution_discipline_meta,
    strategy_score_map,
    strategy_sell_position_meta,
)
from quant_hunter.storage import load_app_state


LEADER = "\u9f99\u5934\u6a21\u578b"
MAIN_FORCE = "\u4e3b\u529b\u96f7\u8fbe"
BOARD_ATTACK = "\u64d2\u9f99\u6253\u677f"
VALUE = "\u4ef7\u503c\u4f4e\u5438"
TAIL_BUY = "\u5c3e\u76d8\u4e70\u5165\u6cd5"
ONE_DAY = "\u4e00\u65e5\u6301\u80a1\u6cd5"
HALF_POSITION = "\u534a\u4ed3\u6301\u80a1\u6cd5"
DECISION = "\u6398\u9f99\u51b3\u7b56"
ALIAS_RELAY = "\u5f3a\u52bf\u63a5\u529b"
ALIAS_TAIL = "\u5c3e\u76d8\u4e70\u5165"
ALL = "\u5168\u90e8"


def _make_recommendation(**overrides) -> RecommendationRow:
    payload = {
        "symbol": "SZSE.300001",
        "stock_id": "300001",
        "stock_name": "Test Sample",
        "action": "BUY",
        "label": "RECLAIM_LONG",
        "signal_date": "2026-04-06",
        "close": 10.0,
        "entry_price": 10.0,
        "stop_price": 0.0,
        "target_price": 0.0,
        "technical_score": 84.0,
        "position_score": 74.0,
        "persistence_score": 79.0,
        "news_score": 75.0,
        "leader_score": 77.0,
        "total_score": 83.0,
        "theme_name": "robotics",
        "theme_rank": 1,
        "stock_pool": "trend",
        "primary_strategy": DECISION,
        "dragon_decision_score": 85.0,
    }
    payload.update(overrides)
    return RecommendationRow(**payload)


class StrategyRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        reload_strategy_registry()

    def tearDown(self) -> None:
        reload_strategy_registry()

    def test_registry_canonicalizes_aliases_and_exposes_plan_defaults(self) -> None:
        registry = reload_strategy_registry()

        self.assertEqual(registry.canonical_strategy_name(ALIAS_RELAY), BOARD_ATTACK)
        self.assertEqual(registry.canonical_strategy_name(ALIAS_TAIL), TAIL_BUY)
        self.assertEqual(registry.canonical_strategy_name("\u505aT"), HALF_POSITION)
        self.assertEqual(registry.definition(LEADER).ui_metadata.get("short_label"), "\u9f99\u5934")

        defaults = registry.plan_defaults(ALIAS_TAIL)
        self.assertAlmostEqual(defaults.stop_pct, 0.024, places=4)
        self.assertAlmostEqual(defaults.target_pct, 0.032, places=4)
        self.assertAlmostEqual(defaults.budget_multiplier_strong, 0.82, places=4)
        self.assertAlmostEqual(defaults.budget_multiplier_normal, 0.72, places=4)

    def test_strategy_position_metadata_describes_buy_and_sell_sizes(self) -> None:
        registry = get_strategy_registry()

        for strategy_name in registry.strategy_names:
            self.assertTrue(strategy_buy_position_meta(strategy_name), strategy_name)
            self.assertTrue(strategy_sell_position_meta(strategy_name), strategy_name)
            discipline = strategy_execution_discipline_meta(strategy_name)
            self.assertTrue(discipline, strategy_name)
            self.assertTrue(any(keyword in discipline for keyword in ("必须", "不能", "只做", "禁止", "严格")), strategy_name)

        self.assertIn("1-2 成", strategy_buy_position_meta(TAIL_BUY))
        self.assertIn("先卖 1/2", strategy_sell_position_meta(TAIL_BUY))
        self.assertIn("14:30", strategy_execution_discipline_meta(TAIL_BUY))
        self.assertIn("底仓", strategy_buy_position_meta(HALF_POSITION))
        self.assertIn("机动仓", strategy_sell_position_meta(HALF_POSITION))
        self.assertIn("必须停止做T", strategy_execution_discipline_meta(HALF_POSITION))

    def test_registry_hides_disabled_strategies_from_runtime_exports(self) -> None:
        import quant_hunter.strategy_registry as registry_module

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            payload = {
                "strategies": [
                    {**build_strategy_template_payload("custom_flow"), "enabled": True},
                    {**build_strategy_template_payload("disabled_tail"), "enabled": False},
                ]
            }
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path), patch.object(
                registry_module,
                "_strategy_plugin_directory",
                return_value=Path(tmp) / "plugins",
            ):
                save_strategy_catalog_payload(payload)
                registry = reload_strategy_registry()
                self.assertEqual(registry.strategy_names, ("custom_flow",))
                self.assertEqual(get_strategy_filter_labels(), [ALL, "custom_flow"])

    def test_registry_computes_dependency_driven_scores(self) -> None:
        registry = get_strategy_registry()
        context = {
            "technical": 84.0,
            "position": 74.0,
            "persistence": 79.0,
            "news": 75.0,
            "leader": 77.0,
            "main_force_bias": 0.0,
            "board_bias": 0.0,
            "value_bias": 0.0,
            "one_day_bias": 0.0,
            "tail_buy_bias": 12.0,
            "next_day_window": 90.0,
            "tail_buy_window": 94.0,
            "board_window": 86.0,
            "value_window": 74.0,
        }

        scores = registry.compute_scores(context)

        self.assertIn("main_force_score", scores)
        self.assertIn("board_attack_score", scores)
        self.assertIn("one_day_hold_score", scores)
        self.assertIn("tail_buy_score", scores)
        self.assertEqual(scores["primary_strategy"], TAIL_BUY)

    def test_half_position_plugin_scores_single_stock_t_context(self) -> None:
        registry = get_strategy_registry()
        context = {
            "technical": 78.0,
            "position": 68.0,
            "persistence": 76.0,
            "news": 62.0,
            "leader": 60.0,
            "main_force_bias": 8.0,
            "value_bias": 8.0,
            "half_position_bias": 22.0,
            "t_trade_window": 96.0,
            "single_stock_focus": 92.0,
        }

        scores = registry.compute_scores(context)

        self.assertIn("half_position_hold_score", scores)
        self.assertEqual(scores["primary_strategy"], HALF_POSITION)
        self.assertGreater(float(scores["half_position_hold_score"]), 85.0)

    def test_registry_exports_ui_specs(self) -> None:
        registry = get_strategy_registry()

        self.assertEqual(get_strategy_filter_labels(), [ALL, *list(registry.strategy_names)])
        self.assertEqual(get_strategy_score_fields()[TAIL_BUY], "tail_buy_score")
        self.assertIn((DECISION, "\u6c47\u603b\u524d\u4e94\u5927\u6218\u6cd5\uff0c\u7ed9\u6700\u7ec8\u52a8\u4f5c"), get_strategy_workbench_specs())

    def test_dynamic_strategy_score_helpers_prefer_strategy_scores(self) -> None:
        row = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                LEADER: 68.0,
                MAIN_FORCE: 72.0,
                BOARD_ATTACK: 80.0,
                VALUE: 66.0,
                TAIL_BUY: 78.0,
                ONE_DAY: 75.0,
                DECISION: 77.0,
            },
            leader_model_score=10.0,
            main_force_score=11.0,
            board_attack_score=12.0,
            value_recovery_score=13.0,
            tail_buy_score=14.0,
            one_day_hold_score=15.0,
            dragon_decision_score=16.0,
        )

        score_map = strategy_score_map(row)
        ranked = ranked_strategy_scores(row)

        self.assertEqual(score_map[BOARD_ATTACK], 80.0)
        self.assertEqual(ranked[0][0], BOARD_ATTACK)
        self.assertEqual(PaperTradingEngine().infer_strategy_name(row), BOARD_ATTACK)

    def test_daily_pool_builder_populates_dynamic_strategy_score_map(self) -> None:
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
                reason="main force inflow leader repair",
                source_path="demo",
            )
        ]
        profiles = {
            "SHSE.600000": type(
                "Profile",
                (),
                {"stock_id": "600000", "name": "Leader Demo", "industry": "bank", "notes": "main force inflow", "is_leader": True},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, {"SHSE.600000": []}, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertEqual(set(item.strategy_scores), set(get_strategy_registry().strategy_names))
        self.assertAlmostEqual(item.strategy_scores[LEADER], item.leader_model_score, places=2)
        self.assertAlmostEqual(item.strategy_scores[DECISION], item.dragon_decision_score, places=2)
        self.assertIn(HALF_POSITION, item.strategy_scores)

    def test_daily_pool_builder_surfaces_half_position_t_plan(self) -> None:
        rows = [
            ScanRow(
                stock_name="Half Position Demo",
                stock_id="300777",
                symbol="SZSE.300777",
                action="BUY",
                label="RECLAIM_LONG",
                score=76,
                close=20.0,
                signal_date="2026-04-05",
                entry_price=20.0,
                stop_price=19.2,
                target_price=21.0,
                reason="半仓持股 做T 高抛低吸 专心拿好一只股 主力承接",
                source_path="demo",
            )
        ]
        profiles = {
            "SZSE.300777": type(
                "Profile",
                (),
                {"stock_id": "300777", "name": "Half Position Demo", "industry": "robot", "notes": "单票熟悉 反复跟踪", "is_leader": False},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, {"SZSE.300777": []}, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertEqual(item.primary_strategy, HALF_POSITION)
        self.assertGreater(item.strategy_scores[HALF_POSITION], 80.0)
        self.assertIn("半仓", item.buy_point)
        self.assertIn("做T", item.add_point)
        self.assertIn("高抛", item.sell_point)
        self.assertIn("半仓", item.rationale)
        self.assertIn("执行纪律", item.rationale)
        self.assertIn("必须停止做T", item.rationale)

    def test_decision_engine_caps_half_position_budget_and_next_focus(self) -> None:
        recommendation = _make_recommendation(
            symbol="SZSE.300777",
            stock_id="300777",
            stock_name="Half Position Demo",
            entry_price=20.0,
            stop_price=19.2,
            target_price=21.2,
            total_score=86.0,
            news_score=70.0,
            leader_score=60.0,
            primary_strategy=HALF_POSITION,
            strategy_scores={
                LEADER: 58.0,
                MAIN_FORCE: 70.0,
                VALUE: 72.0,
                HALF_POSITION: 91.0,
                DECISION: 84.0,
            },
            stock_pool="趋势股",
            buy_point="底仓半仓以内，回踩承接再低吸机动仓",
            sell_point="冲高先高抛机动仓",
            rationale="半仓持股 做T 高抛低吸",
        )

        trade_plan = DecisionEngine().build_plan([recommendation], [], available_cash=100000, max_picks=1)

        self.assertEqual(len(trade_plan.decisions), 1)
        decision = trade_plan.decisions[0]
        self.assertLessEqual(decision.suggested_budget, 50000.0)
        self.assertIn("买入仓位", decision.rationale)
        self.assertIn("卖出仓位", decision.rationale)
        self.assertIn("执行纪律", decision.rationale)
        self.assertIn("底仓不超过半仓", decision.rationale)
        self.assertIn("高抛低吸", decision.rationale)
        self.assertIn("停止做T", decision.next_focus)

    def test_decision_engine_reduces_half_position_mobile_lot_on_profit(self) -> None:
        recommendation = _make_recommendation(
            symbol="SZSE.300777",
            stock_id="300777",
            stock_name="Half Position Demo",
            close=20.6,
            primary_strategy=HALF_POSITION,
            strategy_scores={
                HALF_POSITION: 91.0,
                DECISION: 84.0,
            },
        )
        holding = HoldingRecord(
            symbol="SZSE.300777",
            quantity=1000,
            available=1000,
            cost_price=20.0,
            market_value=20600.0,
        )

        trade_plan = DecisionEngine().build_plan([recommendation], [holding], available_cash=20000, max_picks=1)

        self.assertEqual(len(trade_plan.position_advice), 1)
        advice = trade_plan.position_advice[0]
        self.assertEqual(advice.action, "REDUCE")
        self.assertIn("高抛机动仓", advice.rationale)

    def test_export_daily_trade_plan_surfaces_dynamic_strategy_brief(self) -> None:
        recommendation = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                LEADER: 68.0,
                MAIN_FORCE: 72.0,
                BOARD_ATTACK: 91.0,
                VALUE: 66.0,
                TAIL_BUY: 61.0,
                ONE_DAY: 64.0,
                DECISION: 82.0,
            },
            board_attack_score=0.0,
            rationale="dynamic strategy test",
        )
        trade_plan = DecisionEngine().build_plan([recommendation], [], available_cash=100000, max_picks=5)
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = export_daily_trade_plan(
                output_dir=tmp,
                recommendations=[recommendation],
                trade_plan=trade_plan,
                holdings=[],
            )
            with open(artifacts.csv_path, "r", encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.reader(handle))
            markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")

        self.assertIn(BOARD_ATTACK, csv_rows[1][-1])
        self.assertIn(f"\u6218\u6cd5: {BOARD_ATTACK}", markdown)

    def test_export_end_of_day_review_surfaces_dynamic_strategy_brief(self) -> None:
        recommendation = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                LEADER: 70.0,
                MAIN_FORCE: 88.0,
                BOARD_ATTACK: 74.0,
                VALUE: 66.0,
                TAIL_BUY: 58.0,
                ONE_DAY: 55.0,
                DECISION: 79.0,
            },
            main_force_score=0.0,
            rationale="review dynamic strategy test",
        )
        trade_plan = DecisionEngine().build_plan([recommendation], [], available_cash=100000, max_picks=5)
        board_plan = BoardPlan(temperature="watch", avg_score=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = export_end_of_day_review(
                output_dir=tmp,
                recommendations=[recommendation],
                trade_plan=trade_plan,
                board_plan=board_plan,
                holdings=[],
                scan_rows=[],
            )
            csv_text = Path(artifacts.csv_path).read_text(encoding="utf-8-sig")
            markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")

        self.assertIn(MAIN_FORCE, csv_text)
        self.assertIn(f"\u6218\u6cd5: {MAIN_FORCE}", markdown)

    def test_app_qt_filtered_daily_pool_rows_uses_dynamic_tail_buy_scores(self) -> None:
        import app_qt as module

        strong = _make_recommendation(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="Strong Tail",
            primary_strategy="",
            strategy_scores={
                LEADER: 55.0,
                MAIN_FORCE: 62.0,
                BOARD_ATTACK: 68.0,
                VALUE: 57.0,
                TAIL_BUY: 89.0,
                ONE_DAY: 74.0,
                DECISION: 80.0,
            },
            tail_buy_score=0.0,
            execution_readiness=80.0,
            mainline_risk_flag="\u4f4e",
        )
        weak = _make_recommendation(
            symbol="SZSE.301189",
            stock_id="301189",
            stock_name="Weak Tail",
            primary_strategy="",
            strategy_scores={
                LEADER: 55.0,
                MAIN_FORCE: 60.0,
                BOARD_ATTACK: 64.0,
                VALUE: 57.0,
                TAIL_BUY: 77.0,
                ONE_DAY: 70.0,
                DECISION: 76.0,
            },
            tail_buy_score=0.0,
            execution_readiness=69.0,
            mainline_risk_flag="\u4e2d",
        )
        window = SimpleNamespace(
            daily_pool_rows=[strong, weak],
            recommend_theme_filter=ALL,
            recommend_strategy_filter="\u5c3e\u76d8\u4f18\u9009",
        )

        rows = module.QuantHunterWindow._filtered_daily_pool_rows(window)

        self.assertEqual([item.stock_id for item in rows], ["301188"])

    def test_app_qt_filtered_daily_pool_rows_supports_half_position_strategy(self) -> None:
        import app_qt as module

        half_position = _make_recommendation(
            symbol="SZSE.301288",
            stock_id="301288",
            stock_name="Half Position",
            primary_strategy="",
            strategy_scores={
                LEADER: 58.0,
                MAIN_FORCE: 70.0,
                BOARD_ATTACK: 62.0,
                VALUE: 72.0,
                TAIL_BUY: 60.0,
                ONE_DAY: 61.0,
                HALF_POSITION: 91.0,
                DECISION: 78.0,
            },
        )
        leader = _make_recommendation(
            symbol="SHSE.600188",
            stock_id="600188",
            stock_name="Leader",
            primary_strategy=LEADER,
            strategy_scores={
                LEADER: 88.0,
                HALF_POSITION: 40.0,
                DECISION: 80.0,
            },
        )
        window = SimpleNamespace(
            daily_pool_rows=[half_position, leader],
            recommend_theme_filter=ALL,
            recommend_strategy_filter=HALF_POSITION,
        )

        rows = module.QuantHunterWindow._filtered_daily_pool_rows(window)

        self.assertEqual([item.stock_id for item in rows], ["301288"])

    def test_app_qt_runtime_refresh_populates_recommend_strategy_combo(self) -> None:
        import app_qt as module

        class DummyCombo:
            def __init__(self) -> None:
                self.items: list[str] = []
                self.value = ""

            def currentText(self) -> str:
                return self.value

            def blockSignals(self, _value: bool) -> None:
                return None

            def clear(self) -> None:
                self.items = []

            def addItems(self, values: list[str]) -> None:
                self.items.extend(values)

            def setCurrentText(self, value: str) -> None:
                self.value = value

        combo = DummyCombo()
        host = SimpleNamespace(
            recommend_strategy_combo=combo,
            recommend_strategy_filter=HALF_POSITION,
            market_filter_tag=ALL,
            _strategy_catalog_current_name=lambda: "",
            _rebuild_market_filter_buttons=lambda: None,
            _rebuild_strategy_pack_cards=lambda: None,
        )

        module.QuantHunterWindow._refresh_strategy_runtime_widgets(host)

        self.assertIn(HALF_POSITION, combo.items)
        self.assertIn("\u5c3e\u76d8\u4f18\u9009", combo.items)
        self.assertEqual(combo.value, HALF_POSITION)

    def test_app_qt_set_strategy_detail_from_row_uses_resolved_primary_strategy(self) -> None:
        import app_qt as module

        class DummyCombo:
            def __init__(self) -> None:
                self.value = ""

            def setCurrentText(self, value: str) -> None:
                self.value = value

        row = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                LEADER: 70.0,
                MAIN_FORCE: 72.0,
                BOARD_ATTACK: 91.0,
                VALUE: 66.0,
                TAIL_BUY: 61.0,
                ONE_DAY: 64.0,
                DECISION: 82.0,
            },
            board_attack_score=0.0,
        )
        window = SimpleNamespace(strategy_detail_combo=DummyCombo())

        module.QuantHunterWindow._set_strategy_detail_from_row(window, row)

        self.assertEqual(window.strategy_detail_combo.value, BOARD_ATTACK)


if __name__ == "__main__":
    unittest.main()
