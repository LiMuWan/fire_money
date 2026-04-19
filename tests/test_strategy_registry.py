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
from quant_hunter.models import RecommendationRow, ScanRow
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.paper_trading import PaperTradingEngine
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review
from quant_hunter.strategy_registry import (
    build_strategy_template_payload,
    delete_strategy_from_catalog,
    get_strategy_filter_labels,
    get_strategy_registry,
    get_strategy_score_fields,
    get_strategy_workbench_specs,
    import_strategy_payloads,
    load_strategy_catalog_payload,
    ranked_strategy_scores,
    reload_strategy_registry,
    replace_strategy_in_catalog,
    save_strategy_catalog_payload,
    strategy_formula_example_weights,
    strategy_formula_reference_text,
    strategy_score_map,
    validate_strategy_definition_payload,
)
from quant_hunter.storage import load_app_state


def _make_recommendation(**overrides) -> RecommendationRow:
    payload = {
        "symbol": "SZSE.300001",
        "stock_id": "300001",
        "stock_name": "测试样本",
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
        "theme_name": "机器人",
        "theme_rank": 1,
        "stock_pool": "趋势股",
        "primary_strategy": "掘龙决策",
        "dragon_decision_score": 85.0,
    }
    payload.update(overrides)
    return RecommendationRow(**payload)


class StrategyRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        reload_strategy_registry()

    def tearDown(self) -> None:
        reload_strategy_registry()

    def test_registry_canonicalizes_legacy_aliases_and_exposes_plan_defaults(self) -> None:
        registry = reload_strategy_registry()

        self.assertEqual(registry.canonical_strategy_name("强势接力"), "擒龙打板")
        self.assertEqual(registry.canonical_strategy_name("尾盘买入"), "尾盘买入法")
        self.assertEqual(registry.definition("龙头模型").ui_metadata.get("short_label"), "龙头")
        self.assertEqual(registry.definition("尾盘买入法").ui_metadata.get("capital_style"), "尾盘试仓 / 隔夜兑现")

        defaults = registry.plan_defaults("尾盘买入")
        self.assertAlmostEqual(defaults.stop_pct, 0.024, places=4)
        self.assertAlmostEqual(defaults.target_pct, 0.032, places=4)
        self.assertAlmostEqual(defaults.budget_multiplier_strong, 0.82, places=4)
        self.assertAlmostEqual(defaults.budget_multiplier_normal, 0.72, places=4)

    def test_registry_hides_disabled_strategies_from_runtime_exports(self) -> None:
        import quant_hunter.strategy_registry as registry_module

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            payload = {
                "strategies": [
                    {**build_strategy_template_payload("量价共振"), "enabled": True},
                    {**build_strategy_template_payload("尾盘验证"), "enabled": False},
                ]
            }
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                save_strategy_catalog_payload(payload)
                registry = reload_strategy_registry()
                self.assertEqual(registry.strategy_names, ("量价共振",))
                self.assertEqual(get_strategy_filter_labels(), ["全部", "量价共振"])

    def test_registry_computes_dependency_driven_scores_even_when_catalog_order_is_not_linear(self) -> None:
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

        main_force_score = 84.0 * 0.18 + 74.0 * 0.18 + 79.0 * 0.14 + 75.0 * 0.20 + 77.0 * 0.12
        board_attack_score = 84.0 * 0.27 + 79.0 * 0.24 + 77.0 * 0.14 + 86.0 * 0.15 + 75.0 * 0.12
        one_day_hold_score = (
            84.0 * 0.22
            + 74.0 * 0.18
            + 79.0 * 0.14
            + 75.0 * 0.16
            + 77.0 * 0.08
            + board_attack_score * 0.12
            + main_force_score * 0.08
            + 90.0 * 0.10
        )
        tail_buy_score = (
            84.0 * 0.18
            + 74.0 * 0.12
            + 79.0 * 0.16
            + 75.0 * 0.12
            + 77.0 * 0.05
            + main_force_score * 0.14
            + board_attack_score * 0.05
            + one_day_hold_score * 0.18
            + 94.0 * 0.10
            + 12.0
        )

        self.assertAlmostEqual(scores["main_force_score"], round(main_force_score, 2), places=2)
        self.assertAlmostEqual(scores["board_attack_score"], round(board_attack_score, 2), places=2)
        self.assertAlmostEqual(scores["one_day_hold_score"], round(one_day_hold_score, 2), places=2)
        self.assertAlmostEqual(scores["tail_buy_score"], round(tail_buy_score, 2), places=2)
        self.assertEqual(scores["primary_strategy"], "尾盘买入法")

    def test_registry_exports_ui_specs_from_catalog(self) -> None:
        registry = get_strategy_registry()

        self.assertEqual(get_strategy_filter_labels(), ["全部", *list(registry.strategy_names)])
        self.assertEqual(get_strategy_score_fields()["尾盘买入法"], "tail_buy_score")
        self.assertIn(("掘龙决策", "汇总前五大战法，给最终动作"), get_strategy_workbench_specs())

    def test_strategy_formula_helpers_expose_reference_text_and_examples(self) -> None:
        reference = strategy_formula_reference_text("aggregate")
        example = strategy_formula_example_weights("aggregate")

        self.assertIn("公式参考（聚合战法）", reference)
        self.assertIn("龙头模型", reference)
        self.assertTrue(example)
        self.assertIn("technical", example)

    def test_validate_strategy_definition_payload_flags_unknown_and_self_formula_keys(self) -> None:
        payload = build_strategy_template_payload("量价共振")
        payload["formula_weights"] = {
            "technical": 0.5,
            "量价共振": 0.2,
            "mystery_factor": 0.3,
        }

        report = validate_strategy_definition_payload(payload)

        self.assertTrue(report["errors"])
        self.assertIn("mystery_factor", report["unknown_formula_keys"])
        self.assertIn("technical", report["context_formula_keys"])
        self.assertTrue(any("不能引用当前战法自己" in item for item in report["errors"]))

    def test_dynamic_strategy_score_helpers_prefer_strategy_scores_payload(self) -> None:
        row = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                "龙头模型": 68.0,
                "主力雷达": 72.0,
                "擒龙打板": 80.0,
                "价值低吸": 66.0,
                "尾盘买入法": 78.0,
                "一日持股法": 75.0,
                "掘龙决策": 77.0,
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

        self.assertEqual(score_map["擒龙打板"], 80.0)
        self.assertEqual(ranked[0][0], "擒龙打板")
        self.assertEqual(PaperTradingEngine().infer_strategy_name(row), "擒龙打板")

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
                reason="主力净流入 龙头修复",
                source_path="demo",
            )
        ]
        profiles = {
            "SHSE.600000": type(
                "Profile",
                (),
                {"stock_id": "600000", "name": "Leader Demo", "industry": "bank", "notes": "主力净流入", "is_leader": True},
            )(),
        }

        pool = DailyPoolBuilder(stock_profiles=profiles).build(rows, {"SHSE.600000": []}, [], top_n=5)

        self.assertEqual(len(pool), 1)
        item = pool[0]
        self.assertEqual(set(item.strategy_scores), set(get_strategy_registry().strategy_names))
        self.assertAlmostEqual(item.strategy_scores["龙头模型"], item.leader_model_score, places=2)
        self.assertAlmostEqual(item.strategy_scores["掘龙决策"], item.dragon_decision_score, places=2)

    def test_ui_refresh_strategy_focus_detail_uses_dynamic_strategy_scores(self) -> None:
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

        row = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                "龙头模型": 60.0,
                "主力雷达": 61.0,
                "擒龙打板": 63.0,
                "价值低吸": 64.0,
                "尾盘买入法": 66.0,
                "一日持股法": 88.0,
                "掘龙决策": 76.0,
            },
            one_day_hold_score=0.0,
            next_focus="盯次日竞价是否高开转强、开盘 5 分钟量能是否放大。",
            buy_point="竞价转强后在 10.00 附近跟随",
            sell_point="冲高到 10.55 附近先兑现",
            mainline_tag="机器人",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=84.0,
            mainline_continuation_score=79.0,
            mainline_risk_flag="低",
        )
        window = SimpleNamespace(
            strategy_detail_text=DummyText(),
            strategy_detail_combo=DummyCombo(),
            daily_pool_table=DummyTable(),
            daily_pool_rows=[row],
            _filtered_daily_pool_rows=lambda: [row],
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _display_leader_level=lambda value: value or "前排",
        )

        ui_refresh.refresh_strategy_focus_detail(window, STRATEGY_SCORE_FIELDS)

        text = window.strategy_detail_text.toPlainText()
        self.assertIn("战法 88.0", text)
        self.assertIn("一日 88.0", text)
        self.assertIn("隔日三段判断", text)

    def test_ui_refresh_strategy_pack_panels_rank_with_dynamic_strategy_scores(self) -> None:
        from quant_hunter import ui_refresh
        from quant_hunter.ui_config import STRATEGY_SCORE_FIELDS

        class DummyCard:
            def __init__(self) -> None:
                self.payload = None

            def set_empty(self, text: str) -> None:
                self.payload = ("empty", text)

            def set_strategy_summary(self, **kwargs) -> None:
                self.payload = kwargs

        strong = _make_recommendation(
            stock_name="强样本",
            stock_id="300111",
            symbol="SZSE.300111",
            primary_strategy="",
            strategy_scores={
                "龙头模型": 90.0,
                "主力雷达": 68.0,
                "擒龙打板": 70.0,
                "价值低吸": 55.0,
                "尾盘买入法": 50.0,
                "一日持股法": 52.0,
                "掘龙决策": 78.0,
            },
            leader_model_score=0.0,
            theme_name="机器人",
        )
        weak = _make_recommendation(
            stock_name="弱样本",
            stock_id="300222",
            symbol="SZSE.300222",
            primary_strategy="",
            strategy_scores={
                "龙头模型": 72.0,
                "主力雷达": 66.0,
                "擒龙打板": 64.0,
                "价值低吸": 58.0,
                "尾盘买入法": 54.0,
                "一日持股法": 50.0,
                "掘龙决策": 70.0,
            },
            leader_model_score=0.0,
            theme_name="机器人",
        )
        card = DummyCard()
        window = SimpleNamespace(
            daily_pool_rows=[weak, strong],
            strategy_pack_cards={"龙头模型": card},
            _display_action=lambda value: {"BUY": "买入", "WATCH": "观察", "SELL": "卖出"}.get(value, value),
            _refresh_strategy_focus_detail=lambda: None,
        )

        ui_refresh.refresh_strategy_pack_panels(window, {"龙头模型": STRATEGY_SCORE_FIELDS["龙头模型"]})

        self.assertIsNotNone(card.payload)
        self.assertEqual(card.payload["focus_name"], "强样本 (300111)")
        self.assertAlmostEqual(card.payload["focus_score"], 90.0, places=2)

    def test_export_daily_trade_plan_surfaces_dynamic_strategy_brief(self) -> None:
        recommendation = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                "龙头模型": 68.0,
                "主力雷达": 72.0,
                "擒龙打板": 91.0,
                "价值低吸": 66.0,
                "尾盘买入法": 61.0,
                "一日持股法": 64.0,
                "掘龙决策": 82.0,
            },
            board_attack_score=0.0,
            rationale="动态战法测试",
        )
        trade_plan = DecisionEngine().build_plan([recommendation], [], available_cash=100000, max_picks=5)
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = export_daily_trade_plan(
                output_dir=tmp,
                recommendations=[recommendation],
                trade_plan=trade_plan,
                holdings=[],
            )
            with Path(artifacts.csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
                csv_rows = list(csv.reader(handle))
            markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")

        self.assertEqual(csv_rows[0][:16], [
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
        ])
        self.assertIn("擒龙打板", csv_rows[1][-1])
        self.assertIn("战法: 擒龙打板", markdown)

    def test_export_end_of_day_review_surfaces_dynamic_strategy_brief(self) -> None:
        recommendation = _make_recommendation(
            primary_strategy="",
            strategy_scores={
                "龙头模型": 70.0,
                "主力雷达": 88.0,
                "擒龙打板": 74.0,
                "价值低吸": 66.0,
                "尾盘买入法": 58.0,
                "一日持股法": 55.0,
                "掘龙决策": 79.0,
            },
            main_force_score=0.0,
            rationale="复盘动态战法测试",
        )
        trade_plan = DecisionEngine().build_plan([recommendation], [], available_cash=100000, max_picks=5)
        board_plan = BoardPlan(temperature="先观察", avg_score=0.0)
        with tempfile.TemporaryDirectory() as tmp:
            artifacts = export_end_of_day_review(
                output_dir=tmp,
                recommendations=[recommendation],
                trade_plan=trade_plan,
                board_plan=board_plan,
                holdings=[],
            )
            csv_text = Path(artifacts.csv_path).read_text(encoding="utf-8-sig")
            markdown = Path(artifacts.markdown_path).read_text(encoding="utf-8")

        self.assertIn("主力雷达", csv_text)
        self.assertIn("战法: 主力雷达", markdown)

    def test_strategy_catalog_helpers_support_replace_delete_and_import(self) -> None:
        import quant_hunter.strategy_registry as registry_module

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                reload_strategy_registry()
                template = build_strategy_template_payload("量价共振")
                save_strategy_catalog_payload({"strategies": [template, build_strategy_template_payload("尾盘验证")]})
                loaded = load_strategy_catalog_payload()
                self.assertEqual(len(loaded["strategies"]), 2)
                self.assertEqual(loaded["strategies"][0]["name"], "量价共振")

                updated = replace_strategy_in_catalog(
                    {
                        **template,
                        "description": "抓量价共振和承接确认",
                    },
                    previous_name="量价共振",
                )
                self.assertIn("抓量价共振和承接确认", str(updated["strategies"][0]))

                imported = import_strategy_payloads(
                    {
                        "name": "情绪切换",
                        "score_field": "switch_score",
                        "description": "抓情绪切换",
                        "formula_stage": "base",
                        "formula_weights": {"technical": 0.5, "news": 0.5},
                    }
                )
                self.assertEqual(len(imported["strategies"]), 3)

                deleted = delete_strategy_from_catalog("尾盘验证")
                self.assertEqual(len(deleted["strategies"]), 2)
                self.assertTrue(catalog_path.exists())

    def test_app_qt_refresh_strategy_config_workspace_populates_list_and_editor(self) -> None:
        import app_qt as module
        import quant_hunter.strategy_registry as registry_module

        class DummyEditor:
            def __init__(self) -> None:
                self.value = ""

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyInput:
            def __init__(self) -> None:
                self.value = ""

            def setText(self, value: str) -> None:
                self.value = value

            def text(self) -> str:
                return self.value

        class DummyItem:
            def __init__(self, value: str) -> None:
                self._value = value

            def text(self) -> str:
                return self._value

        class DummyList:
            def __init__(self) -> None:
                self.items: list[str] = []
                self.current: str = ""

            def blockSignals(self, _value: bool) -> None:
                return None

            def clear(self) -> None:
                self.items.clear()
                self.current = ""

            def addItem(self, value: str) -> None:
                self.items.append(value)

            def currentItem(self):
                return DummyItem(self.current) if self.current else None

            def findItems(self, value: str, _match_flag) -> list[DummyItem]:
                return [DummyItem(value)] if value in self.items else []

            def setCurrentItem(self, item) -> None:
                self.current = item.text()

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            payload = {"strategies": [build_strategy_template_payload("量价共振")]}
            catalog_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                reload_strategy_registry()
                window = SimpleNamespace(
                    strategy_config_list=DummyList(),
                    strategy_config_name_input=DummyInput(),
                    strategy_config_editor=DummyEditor(),
                    _strategy_config_loaded_name="",
                    _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
                    _set_strategy_config_status=lambda headline, detail="": None,
                )

                module.QuantHunterWindow._refresh_strategy_config_workspace(window)

                self.assertEqual(window.strategy_config_list.items, ["量价共振"])
                self.assertEqual(window.strategy_config_name_input.value, "量价共振")
                self.assertIn('"name": "量价共振"', window.strategy_config_editor.value)

    def test_app_qt_save_strategy_config_from_editor_persists_catalog(self) -> None:
        import app_qt as module
        import quant_hunter.strategy_registry as registry_module

        class DummyEditor:
            def __init__(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            payload = build_strategy_template_payload("量价共振")
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                reload_strategy_registry()
                window = SimpleNamespace(
                    strategy_config_editor=DummyEditor(json.dumps(payload, ensure_ascii=False, indent=2)),
                    _strategy_config_loaded_name="",
                    _reload_strategy_catalog_runtime=lambda **kwargs: setattr(window, "reload_kwargs", kwargs),
                )
                with patch.object(module.QMessageBox, "information", return_value=None), patch.object(module.QMessageBox, "critical", return_value=None):
                    module.QuantHunterWindow.save_strategy_config_from_editor(window)
                stored = json.loads(catalog_path.read_text(encoding="utf-8"))
                self.assertTrue(any(item.get("name") == "量价共振" for item in stored["strategies"]))
                self.assertEqual(window.reload_kwargs["selected_name"], "量价共振")

    def test_app_qt_duplicate_current_strategy_config_builds_copy_in_editor(self) -> None:
        import app_qt as module

        class DummyEditor:
            def __init__(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyInput:
            def __init__(self) -> None:
                self.value = ""

            def setText(self, value: str) -> None:
                self.value = value

            def text(self) -> str:
                return self.value

        class DummyPlainText:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        class DummyCombo:
            def __init__(self, value: str = "base") -> None:
                self._value = value
                self.index = 0

            def currentData(self) -> str:
                return self._value

            def count(self) -> int:
                return 2

            def itemData(self, index: int) -> str:
                return ["base", "aggregate"][index]

            def setCurrentIndex(self, index: int) -> None:
                self.index = index

        payload = build_strategy_template_payload("量价共振")
        window = SimpleNamespace(
            strategy_config_editor=DummyEditor(json.dumps(payload, ensure_ascii=False, indent=2)),
            strategy_config_name_input=DummyInput(),
            strategy_config_score_field_input=DummyInput(),
            strategy_config_description_input=DummyInput(),
            strategy_config_aliases_input=DummyInput(),
            strategy_config_formula_stage_combo=DummyCombo(),
            strategy_config_short_label_input=DummyInput(),
            strategy_config_capital_style_input=DummyInput(),
            strategy_config_badge_palette_input=DummyInput(),
            strategy_config_default_risk_input=DummyInput(),
            strategy_config_low_flag_risk_input=DummyInput(),
            strategy_config_stop_pct_input=DummyInput(),
            strategy_config_target_pct_input=DummyInput(),
            strategy_config_budget_strong_input=DummyInput(),
            strategy_config_budget_normal_input=DummyInput(),
            strategy_config_budget_threshold_input=DummyInput(),
            strategy_config_formula_weights_text=DummyPlainText(),
            strategy_config_scene_input=DummyPlainText(),
            strategy_config_positioning_input=DummyPlainText(),
            strategy_config_empty_hint_input=DummyPlainText(),
            strategy_config_position_hint_input=DummyPlainText(),
            strategy_config_no_go_input=DummyPlainText(),
            strategy_config_applicable_market_input=DummyPlainText(),
            strategy_config_capacity_limit_input=DummyPlainText(),
            strategy_config_standard_action_buy_input=DummyPlainText(),
            strategy_config_standard_action_sell_input=DummyPlainText(),
            strategy_config_failure_sample_input=DummyPlainText(),
            _strategy_config_loaded_name="量价共振",
            _strategy_catalog_current_name=lambda: "量价共振",
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        module.QuantHunterWindow.duplicate_current_strategy_config(window)

        self.assertIn('"name": "量价共振 副本"', window.strategy_config_editor.value)
        self.assertEqual(window.strategy_config_name_input.value, "量价共振 副本")

    def test_app_qt_validate_strategy_config_editor_reports_summary(self) -> None:
        import app_qt as module

        class DummyEditor:
            def __init__(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        payload = build_strategy_template_payload("量价共振")
        window = SimpleNamespace(
            strategy_config_editor=DummyEditor(json.dumps(payload, ensure_ascii=False, indent=2)),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        with patch.object(module.QMessageBox, "information", return_value=None), patch.object(module.QMessageBox, "critical", return_value=None):
            module.QuantHunterWindow.validate_strategy_config_editor(window)

        self.assertEqual(window.status[0], "战法配置校验通过")
        self.assertIn("量价共振", window.status[1])
        self.assertIn("公式项", window.status[1])

    def test_app_qt_validate_strategy_config_editor_rejects_unknown_formula_key(self) -> None:
        import app_qt as module

        class DummyEditor:
            def __init__(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        class DummyPlainText:
            def __init__(self) -> None:
                self.value = ""

            def setPlainText(self, value: str) -> None:
                self.value = value

        payload = build_strategy_template_payload("量价共振")
        payload["formula_weights"] = {"technical": 0.6, "mystery_factor": 0.4}
        window = SimpleNamespace(
            strategy_config_editor=DummyEditor(json.dumps(payload, ensure_ascii=False, indent=2)),
            strategy_config_formula_help_text=DummyPlainText(),
            _strategy_config_loaded_name="",
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        with patch.object(module.QMessageBox, "critical", return_value=None) as critical_mock:
            module.QuantHunterWindow.validate_strategy_config_editor(window)

        self.assertEqual(window.status[0], "战法配置校验失败")
        self.assertIn("mystery_factor", window.status[1])
        critical_mock.assert_called_once()

    def test_app_qt_fill_strategy_config_formula_example_uses_stage_template(self) -> None:
        import app_qt as module

        class DummyCombo:
            def currentData(self) -> str:
                return "aggregate"

        class DummyPlainText:
            def __init__(self) -> None:
                self.value = ""

            def setPlainText(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        window = SimpleNamespace(
            strategy_config_formula_stage_combo=DummyCombo(),
            strategy_config_formula_weights_text=DummyPlainText(),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _on_strategy_config_form_changed=lambda: setattr(window, "synced", True),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        module.QuantHunterWindow.fill_strategy_config_formula_example(window)

        self.assertTrue(getattr(window, "synced", False))
        self.assertIn('"technical"', window.strategy_config_formula_weights_text.value)
        self.assertEqual(window.status[0], "已填充公式示例")

    def test_app_qt_market_hover_sync_key_normalizes_intraday_timestamp(self) -> None:
        import app_qt as module

        window = SimpleNamespace(
            _normalize_market_timeframe=lambda timeframe=None: str(timeframe or "分时"),
            _is_intraday_market_timeframe=lambda timeframe=None: str(timeframe or "") in {"分时", "1分", "5分", "15分", "30分", "60分"},
        )

        intraday_key = module.QuantHunterWindow._market_hover_sync_key(window, "2026-04-19 09:35", "分时")
        daily_key = module.QuantHunterWindow._market_hover_sync_key(window, "2026-04-19", "日线")

        self.assertEqual(intraday_key, "09:35")
        self.assertEqual(daily_key, "2026-04-19")

    def test_app_qt_set_market_chart_hover_summary_updates_label(self) -> None:
        import app_qt as module

        class DummyLabel:
            def __init__(self) -> None:
                self.value = ""

            def setText(self, value: str) -> None:
                self.value = value

        label = DummyLabel()
        window = SimpleNamespace(
            market_chart_hover_label=label,
            _set_label_text_if_changed=lambda widget, text: widget.setText(text),
            _market_chart_hover_default_text=lambda: "图表悬浮：移动鼠标到主图或副图，可联动查看同一时点。",
        )

        module.QuantHunterWindow._set_market_chart_hover_summary(
            window,
            "时间: 09:35\n价格: 10.23\n成交量: 123万",
            source_name="主图",
        )

        self.assertIn("图表悬浮 · 主图：", label.value)
        self.assertIn("时间: 09:35", label.value)
        self.assertIn("价格: 10.23", label.value)

    def test_app_qt_market_chart_hover_source_name_maps_known_views(self) -> None:
        import app_qt as module

        daily = object()
        momentum = object()
        window = SimpleNamespace(
            daily_chart_view=daily,
            intraday_chart_view=object(),
            fund_chart_view=object(),
            momentum_chart_view=momentum,
            indicator_chart_view=object(),
        )

        self.assertEqual(module.QuantHunterWindow._market_chart_hover_source_name(window, daily), "主图")
        self.assertEqual(module.QuantHunterWindow._market_chart_hover_source_name(window, momentum), "动量")

    def test_app_qt_safe_reset_market_chart_zoom_calls_chart_reset(self) -> None:
        import app_qt as module

        class DummyChart:
            def __init__(self) -> None:
                self.called = False

            def zoomReset(self) -> None:
                self.called = True

        class DummyView:
            def __init__(self) -> None:
                self._chart = DummyChart()
                self._layout_static_annotations = lambda: None
                self._layout_hover_summary_card = lambda: None

            def chart(self):
                return self._chart

        view = DummyView()
        window = SimpleNamespace()

        with patch.object(module.QTimer, "singleShot", side_effect=lambda *_args, **_kwargs: None):
            module.QuantHunterWindow._safe_reset_market_chart_zoom(window, view)

        self.assertTrue(view._chart.called)

    def test_storage_load_app_state_restores_market_chart_preferences(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state_path = Path(tmp) / "app_state.json"
            state_path.write_text(
                json.dumps(
                    {
                        "market_overlay_modes": ["MA", "BREAK"],
                        "market_secondary_indicator_mode": "RSI",
                        "market_primary_chart_expanded": True,
                        "market_chart_preset": "SIGNAL",
                        "market_chart_custom_presets": {
                            "USER_1": {
                                "label": "我的盯盘",
                                "detail": "自定义量价视图",
                                "overlays": ["MA", "BREAK"],
                                "annotation_mode": "PLAN",
                                "indicator": "RSI",
                                "expanded": True,
                                "pinned": True,
                            }
                        },
                        "market_chart_recent_presets": ["USER_1", "BALANCED"],
                        "market_chart_preset_usage_counts": {"USER_1": 7, "BALANCED": 3},
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            state = load_app_state(state_path)

        self.assertEqual(state.market_overlay_modes, ["MA", "BREAK"])
        self.assertEqual(state.market_secondary_indicator_mode, "RSI")
        self.assertTrue(state.market_primary_chart_expanded)
        self.assertEqual(state.market_chart_preset, "SIGNAL")
        self.assertIn("USER_1", state.market_chart_custom_presets)
        self.assertEqual(state.market_chart_custom_presets["USER_1"]["label"], "我的盯盘")

        self.assertTrue(state.market_chart_custom_presets["USER_1"]["pinned"])

        self.assertEqual(state.market_chart_recent_presets, ["USER_1", "BALANCED"])
        self.assertEqual(state.market_chart_preset_usage_counts, {"USER_1": 7, "BALANCED": 3})

    def test_app_qt_sync_market_chart_preset_state_marks_custom_and_persists(self) -> None:
        import app_qt as module

        state = SimpleNamespace(
            market_chart_preset="BALANCED",
            market_overlay_modes=[],
            market_secondary_indicator_mode="",
            market_primary_chart_expanded=False,
            market_strategy_annotation_mode="FULL",
            market_chart_custom_presets={"USER_1": {"label": "我的盯盘", "detail": "", "overlays": {"MA"}}},
        )
        window = SimpleNamespace(
            market_overlay_modes={"MA"},
            market_strategy_annotation_mode="OFF",
            market_secondary_indicator_mode="MACD",
            market_primary_chart_expanded=True,
            market_chart_preset="BALANCED",
            market_chart_custom_presets={"USER_1": {"label": "我的盯盘", "detail": "", "overlays": {"MA"}}},
            state=state,
            _resolve_market_chart_preset_key=lambda: "CUSTOM",
            _normalize_market_strategy_annotation_mode=lambda value: str(value or "FULL"),
            _normalized_market_chart_custom_presets=lambda: window.market_chart_custom_presets,
            save_state=lambda: setattr(window, "saved", True),
        )

        module.QuantHunterWindow._sync_market_chart_preset_state(window, persist=True)

        self.assertEqual(window.market_chart_preset, "CUSTOM")
        self.assertEqual(state.market_chart_preset, "CUSTOM")
        self.assertEqual(state.market_overlay_modes, ["MA"])
        self.assertEqual(state.market_secondary_indicator_mode, "MACD")
        self.assertTrue(state.market_primary_chart_expanded)
        self.assertTrue(getattr(window, "saved", False))
        self.assertIn("USER_1", state.market_chart_custom_presets)
        self.assertIn("tags", state.market_chart_custom_presets["USER_1"])

    def test_app_qt_market_chart_preset_specs_include_custom_presets(self) -> None:
        import app_qt as module

        custom_spec = {
            "label": "我的盯盘",
            "detail": "自定义量价视图",
            "overlays": {"MA", "BREAK"},
            "annotation_mode": "PLAN",
            "indicator": "RSI",
            "expanded": True,
        }
        window = SimpleNamespace(
            market_overlay_modes={"MA"},
            market_strategy_annotation_mode="FULL",
            market_secondary_indicator_mode="MACD",
            market_primary_chart_expanded=False,
            market_chart_custom_presets={"USER_1": custom_spec},
            _market_chart_builtin_preset_specs=lambda: module.QuantHunterWindow._market_chart_builtin_preset_specs(SimpleNamespace()),
            _normalized_market_chart_custom_presets=lambda: {"USER_1": custom_spec},
        )

        specs = module.QuantHunterWindow._market_chart_preset_specs(window)

        self.assertIn("BALANCED", specs)
        self.assertIn("USER_1", specs)
        self.assertEqual(specs["USER_1"]["label"], "我的盯盘")

        self.assertIn("lock_note", specs["BALANCED"])
        self.assertIn("update_log", specs["BALANCED"])

        self.assertIn("template_owner", specs["BALANCED"])
        self.assertIn("template_version", specs["BALANCED"])

    def test_app_qt_ordered_market_chart_custom_preset_keys_filters_and_sorts(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "我的盯盘",
                "detail": "量价联动",
                "tags": ["盯盘", "量价"],
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
                "pinned": False,
            },
            "USER_2": {
                "label": "复盘信号",
                "detail": "买卖点复盘",
                "tags": ["复盘"],
                "overlays": {"BREAK"},
                "annotation_mode": "PLAN",
                "indicator": "KDJ",
                "expanded": True,
                "pinned": True,
            },
        }
        window = SimpleNamespace(
            _normalized_market_chart_custom_presets=lambda: presets,
        )

        ordered = module.QuantHunterWindow._ordered_market_chart_custom_preset_keys(window)
        filtered = module.QuantHunterWindow._ordered_market_chart_custom_preset_keys(window, search_text="复盘")
        filtered_by_tag = module.QuantHunterWindow._ordered_market_chart_custom_preset_keys(window, search_text="量价")

        self.assertEqual(ordered, ["USER_2", "USER_1"])
        self.assertEqual(filtered, ["USER_2"])
        self.assertEqual(filtered_by_tag, ["USER_1"])

    def test_app_qt_record_market_chart_recent_preset_moves_current_to_front(self) -> None:
        import app_qt as module

        state = SimpleNamespace(market_chart_recent_presets=[])
        window = SimpleNamespace(
            market_chart_recent_presets=["USER_1", "BALANCED"],
            state=state,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _normalized_market_chart_custom_presets=lambda: {"USER_1": {"label": "我的盯盘"}},
            _market_chart_builtin_preset_specs=lambda: module.QuantHunterWindow._market_chart_builtin_preset_specs(SimpleNamespace()),
            save_state=lambda: setattr(window, "saved", True),
        )

        module.QuantHunterWindow._record_market_chart_recent_preset(window, "FLOW", persist=True)

        self.assertEqual(window.market_chart_recent_presets[:3], ["FLOW", "USER_1", "BALANCED"])
        self.assertEqual(state.market_chart_recent_presets[:3], ["FLOW", "USER_1", "BALANCED"])
        self.assertTrue(getattr(window, "saved", False))

    def test_app_qt_market_chart_usage_rank_rows_orders_by_count(self) -> None:
        import app_qt as module

        window = SimpleNamespace(
            _normalized_market_chart_preset_usage_counts=lambda: {"USER_1": 5, "BALANCED": 8, "FLOW": 3},
            _market_chart_preset_label=lambda key=None: {
                "USER_1": "我的盯盘",
                "BALANCED": "均衡盯盘",
                "FLOW": "量价联动",
            }.get(key or "", key or ""),
        )

        rows = module.QuantHunterWindow._market_chart_usage_rank_rows(window, limit=2)

        self.assertEqual(rows, [("BALANCED", 8), ("USER_1", 5)])

    def test_app_qt_market_chart_template_timeline_entries_include_version_and_owner(self) -> None:
        import app_qt as module

        builtin = {
            "BALANCED": {
                "label": "均衡盯盘",
                "template_owner": "投研终端组",
                "template_version": "T-2026.04",
                "update_log": [
                    "2026-04-19 | 团队默认视图升级",
                    "2026-04-18 | 主图结构校正",
                ],
            }
        }
        window = SimpleNamespace(
            _market_chart_builtin_preset_specs=lambda: builtin,
        )

        entries = module.QuantHunterWindow._market_chart_template_timeline_entries(window, limit=2)

        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["preset_label"], "均衡盯盘")
        self.assertEqual(entries[0]["template_owner"], "投研终端组")
        self.assertEqual(entries[0]["template_version"], "T-2026.04")

    def test_app_qt_market_chart_hottest_preset_key_returns_top_rank(self) -> None:
        import app_qt as module

        window = SimpleNamespace(
            _market_chart_usage_rank_rows=lambda limit=None: [("BALANCED", 8), ("USER_1", 5)],
        )

        hottest = module.QuantHunterWindow._market_chart_hottest_preset_key(window)

        self.assertEqual(hottest, "BALANCED")

    def test_app_qt_market_chart_template_timeline_entries_filter_by_template(self) -> None:
        import app_qt as module

        builtin = {
            "BALANCED": {
                "label": "鍧囪　鐩洏",
                "template_owner": "鎶曠爺缁堢缁? ,
                "template_version": "T-2026.04",
                "update_log": ["2026-04-19 | 团队默认视图升级"],
            },
            "FLOW": {
                "label": "閲忎环鑱斿姩",
                "template_owner": "鎶曠爺缁堢缁? ,
                "template_version": "T-2026.04",
                "update_log": ["2026-04-20 | 量价模板刷新"],
            },
        }
        window = SimpleNamespace(
            _market_chart_builtin_preset_specs=lambda: builtin,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
        )

        entries = module.QuantHunterWindow._market_chart_template_timeline_entries(window, preset_key="FLOW")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["preset_key"], "FLOW")

    def test_app_qt_save_current_market_chart_preset_persists_custom_spec(self) -> None:
        import app_qt as module

        window = SimpleNamespace(
            market_chart_preset="BALANCED",
            market_chart_custom_presets={},
            _market_chart_preset_label=lambda key=None: "均衡盯盘",
            _market_chart_custom_preset_key_for_label=lambda label: "USER_1",
            _normalized_market_chart_custom_presets=lambda: window.market_chart_custom_presets,
            _capture_market_chart_preset_spec=lambda **kwargs: {
                "label": kwargs.get("label", ""),
                "detail": kwargs.get("detail", ""),
                "overlays": {"MA", "BREAK"},
                "annotation_mode": "PLAN",
                "indicator": "RSI",
                "expanded": True,
            },
            _sync_market_chart_preset_state=lambda persist=False: setattr(window, "synced", persist),
            _show_market_chart_feedback=lambda message: setattr(window, "feedback", message),
        )

        with patch.object(module.QInputDialog, "getText", return_value=("我的盯盘", True)), patch.object(module.QMessageBox, "information", return_value=None):
            saved_key = module.QuantHunterWindow._save_current_market_chart_preset(window, prompt_overwrite=False)

        self.assertEqual(saved_key, "USER_1")
        self.assertEqual(window.market_chart_preset, "USER_1")
        self.assertIn("USER_1", window.market_chart_custom_presets)
        self.assertEqual(window.market_chart_custom_presets["USER_1"]["label"], "我的盯盘")
        self.assertTrue(getattr(window, "synced", False))

    def test_app_qt_toggle_market_chart_preset_pinned_updates_spec(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "鎴戠殑鐩洏",
                "detail": "",
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
                "pinned": False,
            }
        }
        window = SimpleNamespace(
            market_chart_preset="USER_1",
            market_chart_custom_presets=presets,
            _normalized_market_chart_custom_presets=lambda: presets,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _normalize_market_chart_custom_preset_spec=lambda raw: module.QuantHunterWindow._normalize_market_chart_custom_preset_spec(raw),
            _sync_market_chart_preset_state=lambda persist=False: setattr(window, "synced", persist),
            _show_market_chart_feedback=lambda message: setattr(window, "feedback", message),
        )

        toggled = module.QuantHunterWindow.toggle_market_chart_preset_pinned(window, "USER_1")

        self.assertTrue(toggled)
        self.assertTrue(presets["USER_1"]["pinned"])
        self.assertTrue(getattr(window, "synced", False))

    def test_app_qt_market_chart_custom_preset_export_payload_contains_selected_rows(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "我的盯盘",
                "detail": "量价视图",
                "tags": ["盯盘", "量价"],
                "overlays": {"MA", "BREAK"},
                "annotation_mode": "PLAN",
                "indicator": "RSI",
                "expanded": True,
            }
        }
        window = SimpleNamespace(
            market_chart_custom_presets=presets,
            _normalized_market_chart_custom_presets=lambda: presets,
            _normalize_market_chart_preset_key=lambda value: str(value or "").upper(),
            _normalize_market_strategy_annotation_mode=lambda value: str(value or "FULL"),
        )

        payload = module.QuantHunterWindow._market_chart_custom_preset_export_payload(window, ["USER_1"])

        self.assertEqual(payload["kind"], "market_chart_presets")
        self.assertEqual(len(payload["presets"]), 1)
        self.assertEqual(payload["presets"][0]["label"], "我的盯盘")
        self.assertEqual(payload["presets"][0]["tags"], ["盯盘", "量价"])

        self.assertEqual(payload["package"]["title"], "我的盯盘")
        self.assertEqual(payload["package"]["preset_count"], 1)
        self.assertFalse(payload["presets"][0]["pinned"])

    def test_app_qt_market_chart_custom_preset_export_payload_accepts_package_metadata(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "我的盯盘",
                "detail": "量价视图",
                "tags": ["盯盘"],
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
                "pinned": True,
            }
        }
        window = SimpleNamespace(
            market_chart_custom_presets=presets,
            _normalized_market_chart_custom_presets=lambda: presets,
            _normalize_market_chart_preset_key=lambda value: str(value or "").upper(),
            _normalize_market_strategy_annotation_mode=lambda value: str(value or "FULL"),
        )

        payload = module.QuantHunterWindow._market_chart_custom_preset_export_payload(
            window,
            ["USER_1"],
            package_title="早盘预设包",
            package_detail="给交易组共享的早盘盯盘模板。",
        )

        self.assertEqual(payload["package"]["title"], "早盘预设包")
        self.assertEqual(payload["package"]["detail"], "给交易组共享的早盘盯盘模板。")

    def test_app_qt_import_market_chart_custom_preset_payload_merges_by_label(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "我的盯盘",
                "detail": "",
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
            }
        }
        state = SimpleNamespace(
            market_chart_preset="BALANCED",
            market_overlay_modes=[],
            market_secondary_indicator_mode="",
            market_primary_chart_expanded=False,
            market_strategy_annotation_mode="FULL",
            market_chart_custom_presets={},
        )
        window = SimpleNamespace(
            market_chart_custom_presets=presets,
            market_overlay_modes={"MA"},
            market_strategy_annotation_mode="FULL",
            market_secondary_indicator_mode="MACD",
            market_primary_chart_expanded=False,
            market_chart_preset="BALANCED",
            state=state,
            _normalized_market_chart_custom_presets=lambda: presets,
            _normalize_market_chart_custom_preset_spec=lambda raw: module.QuantHunterWindow._normalize_market_chart_custom_preset_spec(raw),
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _market_chart_custom_preset_key_for_label=lambda label: "USER_2",
            _sync_market_chart_preset_state=lambda persist=False: setattr(window, "synced", persist),
        )

        imported = module.QuantHunterWindow._import_market_chart_custom_preset_payload(
            window,
            {
                "presets": [
                    {
                        "label": "我的盯盘",
                        "detail": "新的量价视图",
                        "overlays": ["MA", "BREAK"],
                        "annotation_mode": "PLAN",
                        "indicator": "RSI",
                        "expanded": True,
                    }
                ]
            },
            persist=True,
        )

        self.assertEqual(imported, ["USER_1"])
        self.assertEqual(presets["USER_1"]["detail"], "新的量价视图")
        self.assertEqual(presets["USER_1"]["indicator"], "RSI")
        self.assertTrue(getattr(window, "synced", False))

    def test_app_qt_rename_market_chart_preset_updates_label(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "我的盯盘",
                "detail": "",
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
            }
        }
        window = SimpleNamespace(
            market_chart_preset="USER_1",
            market_chart_custom_presets=presets,
            _normalized_market_chart_custom_presets=lambda: presets,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _normalize_market_chart_custom_preset_spec=lambda raw: module.QuantHunterWindow._normalize_market_chart_custom_preset_spec(raw),
            _sync_market_chart_preset_state=lambda persist=False: setattr(window, "synced", persist),
            _show_market_chart_feedback=lambda message: setattr(window, "feedback", message),
        )

        with patch.object(module.QInputDialog, "getText", return_value=("我的复盘", True)), patch.object(module.QMessageBox, "information", return_value=None):
            renamed = module.QuantHunterWindow.rename_market_chart_preset(window, "USER_1")

        self.assertEqual(renamed, "USER_1")
        self.assertEqual(presets["USER_1"]["label"], "我的复盘")
        self.assertTrue(getattr(window, "synced", False))

    def test_app_qt_duplicate_market_chart_preset_as_custom_from_builtin(self) -> None:
        import app_qt as module

        builtin = {
            "BALANCED": {
                "label": "均衡盯盘",
                "detail": "团队默认视图",
                "tags": ["团队模板", "日常盯盘"],
                "overlays": {"MA", "BOLL", "HIGHLOW"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
            }
        }
        window = SimpleNamespace(
            market_chart_preset="BALANCED",
            market_chart_custom_presets={},
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _market_chart_preset_specs=lambda: {**builtin, **window.market_chart_custom_presets},
            _market_chart_builtin_preset_specs=lambda: builtin,
            _normalized_market_chart_custom_presets=lambda: window.market_chart_custom_presets,
            _market_chart_custom_preset_key_for_label=lambda label: "USER_1",
            _normalize_market_chart_custom_preset_spec=lambda raw: module.QuantHunterWindow._normalize_market_chart_custom_preset_spec(raw),
            _sync_market_chart_preset_state=lambda persist=False: setattr(window, "synced", persist),
            _show_market_chart_feedback=lambda message: setattr(window, "feedback", message),
        )

        created = module.QuantHunterWindow.duplicate_market_chart_preset_as_custom(window, "BALANCED")

        self.assertEqual(created, "USER_1")
        self.assertEqual(window.market_chart_preset, "USER_1")
        self.assertIn("USER_1", window.market_chart_custom_presets)
        self.assertEqual(window.market_chart_custom_presets["USER_1"]["label"], "均衡盯盘 副本")
        self.assertIn("自定义", window.market_chart_custom_presets["USER_1"]["tags"])

    def test_app_qt_sync_strategy_config_form_to_editor_includes_enabled_flag(self) -> None:
        import app_qt as module

        class DummyInput:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def setText(self, value: str) -> None:
                self.value = value

            def text(self) -> str:
                return self.value

        class DummyCombo:
            def currentData(self) -> str:
                return "base"

        class DummyCheck:
            def isChecked(self) -> bool:
                return False

        class DummyPlainText:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def setPlainText(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        window = SimpleNamespace(
            strategy_config_name_input=DummyInput("量价共振"),
            strategy_config_score_field_input=DummyInput("coflow_score"),
            strategy_config_description_input=DummyInput("抓量价共振"),
            strategy_config_aliases_input=DummyInput("量价共振"),
            strategy_config_enabled_checkbox=DummyCheck(),
            strategy_config_formula_stage_combo=DummyCombo(),
            strategy_config_short_label_input=DummyInput("共振"),
            strategy_config_capital_style_input=DummyInput("试错 / 跟随"),
            strategy_config_badge_palette_input=DummyInput("#111111, #eeeeee"),
            strategy_config_default_risk_input=DummyInput("中风险"),
            strategy_config_low_flag_risk_input=DummyInput("中低风险"),
            strategy_config_stop_pct_input=DummyInput("0.05"),
            strategy_config_target_pct_input=DummyInput("0.09"),
            strategy_config_budget_strong_input=DummyInput("1.0"),
            strategy_config_budget_normal_input=DummyInput("0.8"),
            strategy_config_budget_threshold_input=DummyInput("70"),
            strategy_config_formula_weights_text=DummyPlainText('{"technical": 0.5}'),
            strategy_config_scene_input=DummyPlainText("适合放量共振。"),
            strategy_config_positioning_input=DummyPlainText("抓量价共振。"),
            strategy_config_empty_hint_input=DummyPlainText("等待共振候选。"),
            strategy_config_position_hint_input=DummyPlainText("先试仓，再加仓。"),
            strategy_config_no_go_input=DummyPlainText("信号冲突时不做。"),
            strategy_config_applicable_market_input=DummyPlainText("适合共振行情。"),
            strategy_config_capacity_limit_input=DummyPlainText("轻仓滚动。"),
            strategy_config_standard_action_buy_input=DummyPlainText("先等放量确认。"),
            strategy_config_standard_action_sell_input=DummyPlainText("失效后退出。"),
            strategy_config_failure_sample_input=DummyPlainText("最容易失败在假突破。"),
            strategy_config_editor=DummyPlainText(),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        module.QuantHunterWindow.sync_strategy_config_form_to_editor(window)

        self.assertIn('"enabled": false', window.strategy_config_editor.value)

    def test_app_qt_sync_strategy_config_form_to_editor_generates_json(self) -> None:
        import app_qt as module

        class DummyInput:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def setText(self, value: str) -> None:
                self.value = value

            def text(self) -> str:
                return self.value

        class DummyCombo:
            def currentData(self) -> str:
                return "base"

        class DummyPlainText:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def setPlainText(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        window = SimpleNamespace(
            strategy_config_name_input=DummyInput("量价共振"),
            strategy_config_score_field_input=DummyInput("coflow_score"),
            strategy_config_description_input=DummyInput("抓量价共振"),
            strategy_config_aliases_input=DummyInput("量价共振, 共振战法"),
            strategy_config_formula_stage_combo=DummyCombo(),
            strategy_config_short_label_input=DummyInput("共振"),
            strategy_config_capital_style_input=DummyInput("试错 / 跟随"),
            strategy_config_badge_palette_input=DummyInput("#111111, #eeeeee"),
            strategy_config_default_risk_input=DummyInput("中风险"),
            strategy_config_low_flag_risk_input=DummyInput("中低风险"),
            strategy_config_stop_pct_input=DummyInput("0.05"),
            strategy_config_target_pct_input=DummyInput("0.09"),
            strategy_config_budget_strong_input=DummyInput("1.0"),
            strategy_config_budget_normal_input=DummyInput("0.8"),
            strategy_config_budget_threshold_input=DummyInput("70"),
            strategy_config_formula_weights_text=DummyPlainText('{"technical": 0.5, "news": 0.5}'),
            strategy_config_scene_input=DummyPlainText("适合放量共振。"),
            strategy_config_positioning_input=DummyPlainText("抓量价共振。"),
            strategy_config_empty_hint_input=DummyPlainText("等待共振候选。"),
            strategy_config_position_hint_input=DummyPlainText("先试仓，再加仓。"),
            strategy_config_no_go_input=DummyPlainText("信号冲突时不做。"),
            strategy_config_applicable_market_input=DummyPlainText("适合共振行情。"),
            strategy_config_capacity_limit_input=DummyPlainText("轻仓滚动。"),
            strategy_config_standard_action_buy_input=DummyPlainText("先等放量确认。"),
            strategy_config_standard_action_sell_input=DummyPlainText("失效后退出。"),
            strategy_config_failure_sample_input=DummyPlainText("最容易失败在假突破。"),
            strategy_config_editor=DummyPlainText(),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        module.QuantHunterWindow.sync_strategy_config_form_to_editor(window)

        self.assertIn('"name": "量价共振"', window.strategy_config_editor.value)
        self.assertIn('"score_field": "coflow_score"', window.strategy_config_editor.value)
        self.assertIn('"default_risk_level": "中风险"', window.strategy_config_editor.value)
        self.assertIn('"position_hint": "先试仓，再加仓。"', window.strategy_config_editor.value)
        self.assertEqual(window.status[0], "表单已生成 JSON")

    def test_app_qt_sync_strategy_config_editor_to_form_backfills_fields(self) -> None:
        import app_qt as module

        class DummyInput:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def setText(self, value: str) -> None:
                self.value = value

            def text(self) -> str:
                return self.value

        class DummyCombo:
            def __init__(self) -> None:
                self.index = 0

            def count(self) -> int:
                return 2

            def itemData(self, index: int) -> str:
                return ["base", "aggregate"][index]

            def setCurrentIndex(self, index: int) -> None:
                self.index = index

        class DummyPlainText:
            def __init__(self, value: str = "") -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

            def setPlainText(self, value: str) -> None:
                self.value = value

        payload = build_strategy_template_payload("量价共振")
        payload["description"] = "抓量价共振"
        payload["aliases"] = ["共振战法"]
        payload["ui_metadata"]["short_label"] = "共振"
        payload["ui_metadata"]["default_risk_level"] = "中风险"
        payload["ui_metadata"]["position_hint"] = "先试仓，再加仓。"
        window = SimpleNamespace(
            strategy_config_editor=DummyPlainText(json.dumps(payload, ensure_ascii=False, indent=2)),
            strategy_config_name_input=DummyInput(),
            strategy_config_score_field_input=DummyInput(),
            strategy_config_description_input=DummyInput(),
            strategy_config_aliases_input=DummyInput(),
            strategy_config_formula_stage_combo=DummyCombo(),
            strategy_config_short_label_input=DummyInput(),
            strategy_config_capital_style_input=DummyInput(),
            strategy_config_badge_palette_input=DummyInput(),
            strategy_config_default_risk_input=DummyInput(),
            strategy_config_low_flag_risk_input=DummyInput(),
            strategy_config_stop_pct_input=DummyInput(),
            strategy_config_target_pct_input=DummyInput(),
            strategy_config_budget_strong_input=DummyInput(),
            strategy_config_budget_normal_input=DummyInput(),
            strategy_config_budget_threshold_input=DummyInput(),
            strategy_config_formula_weights_text=DummyPlainText(),
            strategy_config_scene_input=DummyPlainText(),
            strategy_config_positioning_input=DummyPlainText(),
            strategy_config_empty_hint_input=DummyPlainText(),
            strategy_config_position_hint_input=DummyPlainText(),
            strategy_config_no_go_input=DummyPlainText(),
            strategy_config_applicable_market_input=DummyPlainText(),
            strategy_config_capacity_limit_input=DummyPlainText(),
            strategy_config_standard_action_buy_input=DummyPlainText(),
            strategy_config_standard_action_sell_input=DummyPlainText(),
            strategy_config_failure_sample_input=DummyPlainText(),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
        )

        module.QuantHunterWindow.sync_strategy_config_editor_to_form(window)

        self.assertEqual(window.strategy_config_name_input.value, "量价共振")
        self.assertEqual(window.strategy_config_description_input.value, "抓量价共振")
        self.assertIn("共振战法", window.strategy_config_aliases_input.value)
        self.assertEqual(window.strategy_config_short_label_input.value, "共振")
        self.assertEqual(window.strategy_config_default_risk_input.value, "中风险")
        self.assertEqual(window.strategy_config_position_hint_input.value, "先试仓，再加仓。")
        self.assertEqual(window.status[0], "JSON 已回填表单")

    def test_app_qt_export_current_strategy_config_writes_file(self) -> None:
        import app_qt as module

        class DummyEditor:
            def __init__(self, value: str) -> None:
                self.value = value

            def toPlainText(self) -> str:
                return self.value

        with tempfile.TemporaryDirectory() as tmp:
            export_path = Path(tmp) / "量价共振.json"
            payload = build_strategy_template_payload("量价共振")
            window = SimpleNamespace(
                strategy_config_editor=DummyEditor(json.dumps(payload, ensure_ascii=False, indent=2)),
                _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
            )
            with patch.object(module.QFileDialog, "getSaveFileName", return_value=(str(export_path), "JSON 文件 (*.json)")), patch.object(module.QMessageBox, "information", return_value=None), patch.object(module.QMessageBox, "critical", return_value=None):
                module.QuantHunterWindow.export_current_strategy_config(window)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(exported["name"], "量价共振")
            self.assertEqual(window.status[0], "已导出当前战法")

    def test_app_qt_export_all_strategy_configs_writes_catalog_file(self) -> None:
        import app_qt as module
        import quant_hunter.strategy_registry as registry_module

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            export_path = Path(tmp) / "strategy_catalog_export.json"
            payload = {"strategies": [build_strategy_template_payload("量价共振"), build_strategy_template_payload("尾盘验证")]}
            catalog_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                reload_strategy_registry()
                window = SimpleNamespace(
                    _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
                )
                with patch.object(module.QFileDialog, "getSaveFileName", return_value=(str(export_path), "JSON 文件 (*.json)")), patch.object(module.QMessageBox, "information", return_value=None):
                    module.QuantHunterWindow.export_all_strategy_configs(window)
            exported = json.loads(export_path.read_text(encoding="utf-8"))
            self.assertEqual(len(exported["strategies"]), 2)
            self.assertEqual(window.status[0], "已导出全部战法")

    def test_app_qt_open_strategy_config_directory_reports_status(self) -> None:
        import app_qt as module
        import quant_hunter.strategy_registry as registry_module

        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = Path(tmp) / "strategy_catalog.json"
            with patch.object(registry_module, "_catalog_path", return_value=catalog_path):
                window = SimpleNamespace(
                    _set_strategy_config_status=lambda headline, detail="": setattr(window, "status", (headline, detail)),
                )
                with patch.object(module.QDesktopServices, "openUrl", return_value=True):
                    module.QuantHunterWindow.open_strategy_config_directory(window)
                self.assertEqual(window.status[0], "已打开战法配置目录")
                self.assertIn(str(catalog_path.parent), window.status[1])

    def test_app_qt_filtered_daily_pool_rows_uses_dynamic_tail_buy_scores(self) -> None:
        import app_qt as module

        strong = _make_recommendation(
            symbol="SZSE.301188",
            stock_id="301188",
            stock_name="强尾盘",
            primary_strategy="",
            strategy_scores={
                "龙头模型": 55.0,
                "主力雷达": 62.0,
                "擒龙打板": 68.0,
                "价值低吸": 57.0,
                "尾盘买入法": 89.0,
                "一日持股法": 74.0,
                "掘龙决策": 80.0,
            },
            tail_buy_score=0.0,
            execution_readiness=80.0,
            mainline_risk_flag="低",
        )
        weak = _make_recommendation(
            symbol="SZSE.301189",
            stock_id="301189",
            stock_name="弱尾盘",
            primary_strategy="",
            strategy_scores={
                "龙头模型": 55.0,
                "主力雷达": 60.0,
                "擒龙打板": 64.0,
                "价值低吸": 57.0,
                "尾盘买入法": 77.0,
                "一日持股法": 70.0,
                "掘龙决策": 76.0,
            },
            tail_buy_score=0.0,
            execution_readiness=69.0,
            mainline_risk_flag="中",
        )
        window = SimpleNamespace(
            daily_pool_rows=[strong, weak],
            recommend_theme_filter="全部",
            recommend_strategy_filter="尾盘优选",
        )

        rows = module.QuantHunterWindow._filtered_daily_pool_rows(window)

        self.assertEqual([item.stock_id for item in rows], ["301188"])

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
                "龙头模型": 70.0,
                "主力雷达": 72.0,
                "擒龙打板": 91.0,
                "价值低吸": 66.0,
                "尾盘买入法": 61.0,
                "一日持股法": 64.0,
                "掘龙决策": 82.0,
            },
            board_attack_score=0.0,
        )
        window = SimpleNamespace(strategy_detail_combo=DummyCombo())

        module.QuantHunterWindow._set_strategy_detail_from_row(window, row)

        self.assertEqual(window.strategy_detail_combo.value, "擒龙打板")

    def test_decision_engine_uses_registry_defaults_for_legacy_strategy_alias(self) -> None:
        recommendations = [
            _make_recommendation(
                primary_strategy="强势接力",
                technical_score=86.0,
                position_score=78.0,
                persistence_score=82.0,
                leader_score=88.0,
                total_score=86.0,
                dragon_decision_score=86.0,
            )
        ]

        plan = DecisionEngine().build_plan(recommendations, [], available_cash=100000, max_picks=5)

        self.assertEqual(len(plan.decisions), 1)
        decision = plan.decisions[0]
        self.assertAlmostEqual(decision.planned_stop, 9.65, places=2)
        self.assertAlmostEqual(decision.planned_target, 11.3, places=2)
        self.assertAlmostEqual(decision.suggested_budget, 100000.0, places=2)
        self.assertIn("擒龙打板", decision.rationale)


if __name__ == "__main__":
    unittest.main()
