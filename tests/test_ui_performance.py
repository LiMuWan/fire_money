from __future__ import annotations

import importlib
import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import patch

from quant_hunter.models import CashSnapshot, DailyAnalysis, HoldingRecord, LeaderCandidate, OrderIntent, PaperOrderRecord, PaperPatrolLog, PaperPosition, PaperTradingState, RecommendationRow, ScanRow, ThemeHeatRow, Trade
from quant_hunter import ui_refresh


try:
    from PySide6.QtWidgets import QApplication, QCheckBox, QGroupBox, QLabel, QLineEdit, QScrollArea, QTableWidget, QTextEdit, QWidget
    from PySide6.QtCharts import QChartView
except ModuleNotFoundError:  # pragma: no cover - optional Qt runtime in tests
    QApplication = None
    QCheckBox = None
    QGroupBox = None
    QLabel = None
    QLineEdit = None
    QScrollArea = None
    QTableWidget = None
    QTextEdit = None
    QWidget = None
    QChartView = None


def _color_value(color) -> str:
    if hasattr(color, "name"):
        try:
            return str(color.name()).lower()
        except Exception:
            pass
    return str(color).lower()


class UIPerformanceTests(unittest.TestCase):
    def setUp(self) -> None:
        if QApplication is None or QTableWidget is None or QTextEdit is None or QLineEdit is None or QCheckBox is None or QLabel is None:
            self.skipTest("PySide6 is not installed in the current interpreter")
        self._app = QApplication.instance() or QApplication([])

    def test_layout_polish_skips_when_signature_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        window = SimpleNamespace(
            _qh_layout_polish_running_v19=False,
            _qh_layout_polish_signature_cache_v19=("stable-layout",),
        )
        window._layout_polish_signature_v19 = lambda: ("stable-layout",)
        window._safe_window_minimum_v19 = lambda: (_ for _ in ()).throw(AssertionError("layout polish should have been skipped"))

        module._qh_apply_layout_polish_v19(window)

        self.assertFalse(window._qh_layout_polish_running_v19)
        self.assertTrue(hasattr(window, "_qh_last_layout_polish_perf_v19"))

    def test_layout_finish_passes_skip_when_signature_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        window = SimpleNamespace(
            _qh_world_class_institutional_finish_signature_v73=("stable-layout",),
            _qh_data_desk_information_finish_signature_v74=("stable-layout",),
        )
        window._layout_polish_signature_v19 = lambda: ("stable-layout",)
        window.styleSheet = lambda: (_ for _ in ()).throw(AssertionError("finish pass should have been skipped"))

        with patch.object(module, "_qh_window_ready_for_ui_v1", return_value=True):
            module._qh_apply_world_class_institutional_finish_v73(window)
            module._qh_apply_data_desk_information_finish_v74(window)

    def test_final_layout_polish_wrapper_skips_when_signature_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        window = SimpleNamespace(
            _qh_layout_polish_final_signature_v78=("stable-layout",),
        )
        window._layout_polish_signature_v19 = lambda: ("stable-layout",)

        with patch.object(module, "_ORIGINAL_QH_APPLY_LAYOUT_POLISH_V78", side_effect=AssertionError("final wrapper should have been skipped")):
            module._qh_apply_layout_polish_v78(window)

        self.assertTrue(hasattr(window, "_qh_last_layout_polish_perf_v19"))

    def test_status_refresh_skips_shell_header_when_tab_change_already_refreshed_it(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        calls = {"normalize": 0, "shell": 0, "summary": 0, "banner": 0, "submission": 0, "scanner": 0, "monitor": 0}
        window = SimpleNamespace(
            _qh_skip_shell_header_in_status_refresh_v1=True,
            _normalize_action_row_texts=lambda: calls.__setitem__("normalize", calls["normalize"] + 1),
            _refresh_shell_header=lambda: calls.__setitem__("shell", calls["shell"] + 1),
            _refresh_live_workspace_summary_panels=lambda: calls.__setitem__("summary", calls["summary"] + 1),
            _refresh_workspace_focus_banners=lambda: calls.__setitem__("banner", calls["banner"] + 1),
            _refresh_submission_focus=lambda: calls.__setitem__("submission", calls["submission"] + 1),
            _refresh_scanner_focus_status=lambda: calls.__setitem__("scanner", calls["scanner"] + 1),
            _refresh_monitor_summary=lambda: calls.__setitem__("monitor", calls["monitor"] + 1),
            _apply_focus_dashboard_v7=lambda: None,
            _sync_signal_panel_tones_v6=lambda: None,
            _refresh_runtime_story_v10=lambda: None,
            _refresh_action_button_states_v30=lambda: None,
            _refresh_overview_capability_overview_v1=lambda: None,
            _apply_status_spotlight_semantics_v74=lambda: None,
        )

        module.QuantHunterWindow._refresh_workspace_status_labels(window)

        self.assertEqual(calls["normalize"], 1)
        self.assertEqual(calls["shell"], 0)
        self.assertEqual(calls["summary"], 1)
        self.assertEqual(calls["banner"], 1)
        self.assertEqual(calls["submission"], 1)
        self.assertEqual(calls["scanner"], 1)
        self.assertEqual(calls["monitor"], 1)
        self.assertFalse(window._qh_skip_shell_header_in_status_refresh_v1)

    def test_select_first_row_uses_guarded_selector_when_available(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        selector_calls = {"count": 0}
        raw_select_calls = {"count": 0}

        class _FakeTable:
            def rowCount(self) -> int:
                return 3

            def selectRow(self, _row: int) -> None:
                raw_select_calls["count"] += 1

        table = _FakeTable()
        window = SimpleNamespace(
            sample_table=table,
            _select_table_row_if_needed=lambda widget, row: selector_calls.__setitem__("count", selector_calls["count"] + (1 if widget is table and row == 0 else 0)),
        )

        module.QuantHunterWindow._select_first_row(window, "sample_table")

        self.assertEqual(selector_calls["count"], 1)
        self.assertEqual(raw_select_calls["count"], 0)

    def test_paper_scroll_heavy_updates_toggle_widgets_and_viewports(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        table = QTableWidget()
        text = QTextEdit()
        window = SimpleNamespace(
            _qh_paper_scroll_heavy_updates_enabled_v1=True,
            _paper_scroll_heavy_widgets_v1=lambda: [table, text],
        )

        module._qh_set_paper_scroll_heavy_updates_v1(window, False)
        self.assertFalse(table.updatesEnabled())
        self.assertFalse(table.viewport().updatesEnabled())
        self.assertFalse(text.updatesEnabled())
        self.assertFalse(text.viewport().updatesEnabled())

        module._qh_set_paper_scroll_heavy_updates_v1(window, True)
        self.assertTrue(table.updatesEnabled())
        self.assertTrue(table.viewport().updatesEnabled())
        self.assertTrue(text.updatesEnabled())
        self.assertTrue(text.viewport().updatesEnabled())

    def test_install_paper_scroll_optimizations_marks_scroll_area_and_tunes_chart(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        scroll_area = QScrollArea()
        content = QWidget()
        scroll_area.setWidget(content)
        chart = QChartView()
        paper_text = QTextEdit()
        paper_text.setReadOnly(True)
        overview_box = QGroupBox()
        overview_text = QTextEdit()
        overview_text.setReadOnly(True)
        overview_text.setParent(overview_box)
        window = SimpleNamespace(
            paper_workspace_scroll_area=scroll_area,
            paper_equity_chart_view=chart,
            paper_trading_text=paper_text,
            paper_experiment_text=None,
            paper_overview_box=overview_box,
            _on_paper_workspace_scroll_value_changed_v1=lambda _value: None,
            _paper_scroll_heavy_widgets_v1=lambda: [chart, paper_text],
        )

        with patch.object(module.QScroller, "ungrabGesture") as ungrab_mock:
            module._qh_install_paper_scroll_optimizations_v1(window)

        self.assertTrue(bool(scroll_area.property("_qh_scroll_opt_installed_v1")))
        self.assertGreaterEqual(scroll_area.verticalScrollBar().singleStep(), 28)
        self.assertFalse(bool(chart.renderHints() & module.QPainter.Antialiasing))
        self.assertEqual(chart.viewportUpdateMode(), QChartView.MinimalViewportUpdate)
        self.assertGreaterEqual(ungrab_mock.call_count, 2)
        self.assertEqual(paper_text.verticalScrollBarPolicy(), module.Qt.ScrollBarAlwaysOff)
        self.assertEqual(overview_text.verticalScrollBarPolicy(), module.Qt.ScrollBarAlwaysOff)
        self.assertTrue(hasattr(window, "_qh_paper_wheel_proxy_filter_v1"))

    def test_paper_equity_chart_refresh_reuses_chart_when_signature_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        chart_view = QChartView()
        state = PaperTradingState(
            enabled=True,
            initial_cash=100000.0,
            equity_curve=[
                SimpleNamespace(timestamp="2026-04-23 09:30:00", total_equity=100000.0),
                SimpleNamespace(timestamp="2026-04-23 10:00:00", total_equity=101500.0),
            ],
        )
        window = SimpleNamespace(
            paper_equity_chart_view=chart_view,
            paper_trading_state=state,
            state=SimpleNamespace(paper_trading_state=state),
            _style_dark_chart=lambda chart, _title: None,
        )

        module._qh_refresh_paper_trading_equity_chart_v18(window)
        first_chart = chart_view.chart()
        module._qh_refresh_paper_trading_equity_chart_v18(window)
        second_chart = chart_view.chart()

        self.assertIs(first_chart, second_chart)

        next_state = replace(state, equity_curve=list(state.equity_curve) + [SimpleNamespace(timestamp="2026-04-23 10:30:00", total_equity=102200.0)])
        window.paper_trading_state = next_state
        window.state = SimpleNamespace(paper_trading_state=next_state)
        module._qh_refresh_paper_trading_equity_chart_v18(window)

        self.assertIsNot(second_chart, chart_view.chart())

    def test_current_paper_stage_index_reads_tab_widget(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        tabs = module.QTabWidget()
        tabs.addTab(module.QWidget(), "A")
        tabs.addTab(module.QWidget(), "B")
        tabs.setCurrentIndex(1)
        window = SimpleNamespace(paper_stage_tabs=tabs)

        self.assertEqual(module._qh_current_paper_stage_index_v1(window), 1)

    def test_paper_stage_tab_changed_refreshes_panels_and_enables_detail(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        calls = {"detail": 0, "refresh": 0, "install": 0}
        window = SimpleNamespace(
            _set_paper_lab_detail_visibility_v39=lambda visible: calls.__setitem__("detail", calls["detail"] + (1 if visible else 0)),
            _refresh_paper_trading_panels=lambda: calls.__setitem__("refresh", calls["refresh"] + 1),
            _install_paper_scroll_optimizations_v1=lambda: calls.__setitem__("install", calls["install"] + 1),
        )

        module._qh_on_paper_stage_tab_changed_v1(window, 2)

        self.assertEqual(calls["detail"], 1)
        self.assertEqual(calls["refresh"], 1)
        self.assertEqual(calls["install"], 1)

    def test_daily_pool_refresh_reuses_identity_items_and_resets_status_palette(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(24)
        execution_state = {"SHSE.600000": "已提交"}
        row = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-21",
            close=10.0,
            entry_price=10.1,
            stop_price=9.6,
            target_price=11.3,
            technical_score=84.0,
            position_score=80.0,
            persistence_score=79.0,
            news_score=75.0,
            leader_score=82.0,
            total_score=88.0,
            theme_name="银行修复",
            theme_score=84.0,
            theme_rank=1,
            leader_level="龙头",
            primary_strategy="掘龙决策",
            stock_pool="龙头股",
            pool_score=81.0,
            buy_point="10.10 放量确认",
            sell_point="11.30 附近分批落袋",
            leader_model_score=82.0,
            main_force_score=77.0,
            board_attack_score=65.0,
            value_recovery_score=58.0,
            tail_buy_score=61.0,
            one_day_hold_score=55.0,
            dragon_decision_score=91.0,
            mainline_tag="银行修复",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_strength_score=86.0,
            mainline_window_score=82.0,
            mainline_risk_flag="高",
            catalyst="业绩与修复预期共振",
            rationale="量价结构修复，等待确认继续放量。",
        )
        window = SimpleNamespace(
            daily_pool_table=table,
            daily_pool_rows=[row],
            news_catalysts={},
            _filtered_daily_pool_rows=lambda: list(window.daily_pool_rows),
            _execution_status_for_symbol=lambda symbol: execution_state.get(symbol, "待观察"),
            _stock_id_for_symbol=lambda _symbol: "600000",
            _stock_name_for_symbol=lambda _symbol: "浦发银行",
            _display_leader_level=lambda value: value or "--",
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
        )

        ui_refresh.populate_filtered_daily_pool_table(window)

        first_identity_item = table.item(0, 1)
        first_status_item = table.item(0, 0)
        self.assertIsNotNone(first_identity_item)
        self.assertEqual(_color_value(first_status_item.background().color()), "#163552")

        execution_state["SHSE.600000"] = "待观察"
        window.daily_pool_rows = [
            replace(
                row,
                total_score=92.0,
                mainline_risk_flag="低",
                catalyst="资金回流延续",
            )
        ]

        ui_refresh.populate_filtered_daily_pool_table(window)

        second_identity_item = table.item(0, 1)
        second_status_item = table.item(0, 0)
        self.assertIs(first_identity_item, second_identity_item)
        self.assertEqual(_color_value(second_status_item.background().color()), "#171f28")
        self.assertIn("银行修复", second_identity_item.text())
        self.assertIn("买入", second_identity_item.text())

    def test_intraday_monitor_refresh_reuses_identity_and_action_items(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(9)
        summary_text = QTextEdit()
        scan_row = ScanRow(
            symbol="SZSE.300001",
            signal_date="2026-04-21",
            label="RECLAIM_LONG",
            action="BUY",
            score=88,
            close=12.34,
            entry_price=12.4,
            stop_price=11.8,
            target_price=13.3,
            reason="放量修复",
            source_path="",
        )
        window = SimpleNamespace(
            monitor_table=table,
            intraday_monitor_rows=[],
            daily_pool_rows=[],
            scan_rows=[scan_row],
            universe_analyses={},
            paths_by_symbol={},
            monitor_alert_state={},
            state=SimpleNamespace(watchlist=[], strategy_top_theme_limit=3, focus_themes=[]),
            sound_alert_checkbox=SimpleNamespace(isChecked=lambda: False),
            monitor_summary_text=summary_text,
            _stock_name_for_symbol=lambda _symbol: "龙头样本",
            _stock_id_for_symbol=lambda _symbol: "300001",
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
            _display_label=lambda value: {
                "RECLAIM_LONG": "回补做多",
                "TRAP_DETECTED": "诱多陷阱",
            }.get(str(value or "").upper(), str(value or "--")),
            _license_capabilities=lambda: {"monitor_summary_limit": 3},
            _refresh_monitor_summary=lambda symbol="": None,
        )

        ui_refresh.refresh_intraday_monitor(window)

        first_identity_item = table.item(0, 0)
        first_action_item = table.item(0, 3)
        self.assertIsNotNone(first_identity_item)
        self.assertIsNotNone(first_action_item)
        self.assertIn("回补做多", first_action_item.text())

        window.scan_rows = [
            replace(
                scan_row,
                label="TRAP_DETECTED",
                action="WATCH",
                score=72,
            )
        ]

        ui_refresh.refresh_intraday_monitor(window)

        second_identity_item = table.item(0, 0)
        second_action_item = table.item(0, 3)
        self.assertIs(first_identity_item, second_identity_item)
        self.assertIs(first_action_item, second_action_item)
        self.assertIn("诱多陷阱", second_action_item.text())
        self.assertIn("观察", second_action_item.text())

    def test_theme_heat_refresh_reuses_items_and_updates_values(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(9)
        row = ThemeHeatRow(
            theme_name="AI",
            strength_score=81.0,
            continuation_score=72.0,
            news_score=64.0,
            leader_count=3,
            stock_count=8,
            theme_rank=1,
            risk_flag="中",
            divergence_score=18.0,
            window_score=74.0,
        )
        window = SimpleNamespace(
            theme_heat_table=table,
            theme_heat_rows=[row],
        )

        ui_refresh.refresh_theme_heat_panels(window, strategy_score_fields=[])

        first_theme_item = table.item(0, 0)
        first_strength_item = table.item(0, 1)
        self.assertIsNotNone(first_theme_item)
        self.assertEqual(first_strength_item.text(), "81.0")

        window.theme_heat_rows = [
            replace(
                row,
                strength_score=89.0,
                risk_flag="低",
                theme_rank=2,
            )
        ]

        ui_refresh.refresh_theme_heat_panels(window, strategy_score_fields=[])

        second_theme_item = table.item(0, 0)
        second_strength_item = table.item(0, 1)
        second_rank_item = table.item(0, 7)
        self.assertIs(first_theme_item, second_theme_item)
        self.assertIs(first_strength_item, second_strength_item)
        self.assertEqual(second_strength_item.text(), "89.0")
        self.assertEqual(second_rank_item.text(), "2")

    def test_leader_refresh_reuses_items_and_updates_risk_style(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(10)
        row = LeaderCandidate(
            symbol="SZSE.300001",
            stock_id="300001",
            stock_name="Leader Demo",
            theme_name="AI",
            leader_level="龙头",
            leader_score=91.0,
            theme_rank=1,
            action="BUY",
            rationale="first wave",
            mainline_role="CORE",
            mainline_window_score=83.0,
            mainline_risk_flag="高",
        )
        window = SimpleNamespace(
            leader_table=table,
            leader_candidates=[row],
            _display_leader_level=lambda value: value or "--",
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
        )

        ui_refresh.refresh_theme_heat_panels(window, strategy_score_fields=[])

        first_identity_item = table.item(0, 0)
        first_risk_item = table.item(0, 6)
        first_action_item = table.item(0, 8)
        self.assertIsNotNone(first_identity_item)
        self.assertEqual(_color_value(first_risk_item.background().color()), "#fbeaea")
        self.assertIn("买入", first_identity_item.text())

        window.leader_candidates = [
            replace(
                row,
                action="WATCH",
                rationale="wait for pullback",
                mainline_risk_flag="低",
            )
        ]

        ui_refresh.refresh_theme_heat_panels(window, strategy_score_fields=[])

        second_identity_item = table.item(0, 0)
        second_risk_item = table.item(0, 6)
        second_action_item = table.item(0, 8)
        self.assertIs(first_identity_item, second_identity_item)
        self.assertIs(first_risk_item, second_risk_item)
        self.assertIs(first_action_item, second_action_item)
        self.assertEqual(_color_value(second_risk_item.background().color()), "#e8f7ec")
        self.assertIn("观察", second_identity_item.text())
        self.assertEqual(second_action_item.text(), "观察")

    def test_holdings_refresh_reuses_table_items(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(5)
        refresh_calls = {"count": 0}
        row = HoldingRecord(
            symbol="SHSE.600000",
            quantity=1000,
            available=800,
            cost_price=10.5,
            market_value=10500.0,
        )
        window = SimpleNamespace(
            holdings_table=table,
            holdings=[row],
            _refresh_broker_status=lambda: refresh_calls.__setitem__("count", refresh_calls["count"] + 1),
        )

        ui_refresh.fill_holdings_table(window)

        first_symbol_item = table.item(0, 0)
        first_market_value_item = table.item(0, 4)
        self.assertIsNotNone(first_symbol_item)
        self.assertEqual(first_market_value_item.text(), "10,500.00")

        window.holdings = [
            replace(
                row,
                quantity=1200,
                available=1000,
                market_value=12600.0,
            )
        ]

        ui_refresh.fill_holdings_table(window)

        second_symbol_item = table.item(0, 0)
        second_market_value_item = table.item(0, 4)
        self.assertIs(first_symbol_item, second_symbol_item)
        self.assertIs(first_market_value_item, second_market_value_item)
        self.assertEqual(second_market_value_item.text(), "12,600.00")
        self.assertEqual(refresh_calls["count"], 2)

    def test_broker_status_refresh_reuses_cached_summary_when_inputs_unchanged(self) -> None:
        _ = self._app
        status_text = QTextEdit()
        build_calls = {"count": 0}
        panel_calls = {"execution": 0, "recap": 0, "shell": 0}
        summary_payload = {
            "risk_profile": "standard",
            "readiness": "可确认",
            "readiness_score": 88,
            "estimated_capital": 12000.0,
            "estimated_loss": 800.0,
            "estimated_profit": 1800.0,
            "available_cash": 50000.0,
            "capital_usage_ratio": 0.24,
            "asset_usage_ratio": 0.12,
            "portfolio_risk_review": {"status": "通过", "rows": [], "total_loss_ratio": 0.03},
            "portfolio_fit_review": {
                "status": "通过",
                "rows": [],
                "avg_fit_score": 72.0,
                "avg_diversification_score": 66.0,
                "max_concentration_penalty_score": 12.0,
                "pass_count": 1,
                "caution_count": 0,
                "blocked_count": 0,
                "unevaluated_count": 0,
            },
            "mainline_review": {"status": "通过", "rows": [], "pass_count": 1, "missing_count": 0},
            "risk_reward_ratio": 2.1,
            "blockers": [],
            "warnings": [],
            "symbols": ["SHSE.600000"],
            "side_counts": {"BUY": 1, "SELL": 0, "REDUCE": 0},
        }
        env_payload = {
            "python_version": "3.12",
            "module_installed": True,
            "sdk_module": "gm.api",
            "bridge_python": "",
            "bridge_module_installed": False,
            "bridge_ready": False,
            "direct_ready": True,
        }
        window = SimpleNamespace(
            broker_status_text=status_text,
            holdings=[HoldingRecord(symbol="SHSE.600000", quantity=100, available=100, cost_price=10.0, market_value=1000.0)],
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=80000.0),
            order_intents=[],
            daily_pool_rows=[],
            state=SimpleNamespace(strategy_risk_profile="standard"),
            current_broker_profile=lambda: SimpleNamespace(mode="sdk", account_name="demo", account_id="001"),
            _display_mode=lambda value: value,
            _refresh_shell_header=lambda: panel_calls.__setitem__("shell", panel_calls["shell"] + 1),
        )

        def _fake_build(**_kwargs):
            build_calls["count"] += 1
            return dict(summary_payload), dict(env_payload)

        with patch.object(ui_refresh, "build_broker_execution_summary", side_effect=_fake_build), patch.object(
            ui_refresh,
            "refresh_broker_execution_panel",
            side_effect=lambda *_args, **_kwargs: panel_calls.__setitem__("execution", panel_calls["execution"] + 1),
        ), patch.object(
            ui_refresh,
            "refresh_trade_recap",
            side_effect=lambda *_args, **_kwargs: panel_calls.__setitem__("recap", panel_calls["recap"] + 1),
        ):
            ui_refresh.refresh_broker_status(window, adapter_cls=lambda: object())
            ui_refresh.refresh_broker_status(window, adapter_cls=lambda: object())
            self.assertEqual(build_calls["count"], 1)

            window.holdings = [
                HoldingRecord(symbol="SHSE.600000", quantity=200, available=180, cost_price=10.0, market_value=2000.0)
            ]
            ui_refresh.refresh_broker_status(window, adapter_cls=lambda: object())

        self.assertEqual(build_calls["count"], 2)
        self.assertEqual(panel_calls["execution"], 3)
        self.assertEqual(panel_calls["recap"], 3)
        self.assertEqual(panel_calls["shell"], 3)

    def test_trade_recap_reuses_cached_summary_until_inputs_change(self) -> None:
        _ = self._app
        recap_text = QTextEdit()
        summary_calls = {"count": 0}
        summary_payload = {
            "submitted_count": 1,
            "failed_count": 0,
            "pending_count": 0,
            "deviation_count": 0,
            "review_flags": [],
            "latest_messages": ["继续跟踪回执"],
            "focus_symbols": ["SHSE.600000"],
            "latest_deviation_note": "",
        }
        window = SimpleNamespace(
            broker_recap_text=recap_text,
            order_submission_records=[],
            holdings=[],
            order_intents=[],
            order_submission_log=["sent"],
            daily_pool_rows=[],
            active_symbol="",
        )

        def _fake_summary(**_kwargs):
            summary_calls["count"] += 1
            return dict(summary_payload)

        with patch.object(ui_refresh, "summarize_trade_recap", side_effect=_fake_summary):
            ui_refresh.refresh_trade_recap(window)
            ui_refresh.refresh_trade_recap(window)
            self.assertEqual(summary_calls["count"], 1)

            window.order_submission_log.append("filled")
            ui_refresh.refresh_trade_recap(window)

        self.assertEqual(summary_calls["count"], 2)

    def test_order_intent_refresh_reuses_cells_and_avoids_duplicate_row_computation(self) -> None:
        _ = self._app
        table = QTableWidget()
        table.setColumnCount(13)
        counts = {"describe": 0, "available": 0, "refresh": 0}
        recommendation = RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-21",
            close=10.0,
            entry_price=10.1,
            stop_price=9.6,
            target_price=11.2,
            technical_score=80.0,
            position_score=78.0,
            persistence_score=76.0,
            news_score=70.0,
            leader_score=74.0,
            total_score=82.0,
            theme_name="银行修复",
            theme_rank=1,
            mainline_tag="银行修复",
            mainline_rank=1,
            mainline_role="CORE",
            mainline_window_score=81.0,
            mainline_risk_flag="低",
        )
        intent = OrderIntent(
            symbol="SHSE.600000",
            side="BUY",
            price=10.1,
            quantity=1000,
            stop_price=9.6,
            target_price=11.2,
            signal_date="2026-04-21",
            reason="突破后跟随",
        )
        window = SimpleNamespace(
            orders_table=table,
            order_intents=[intent],
            daily_pool_rows=[recommendation],
            holdings=[HoldingRecord(symbol="SHSE.600000", quantity=1500, available=1200, cost_price=9.8, market_value=14700.0)],
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=80000.0),
            state=SimpleNamespace(strategy_risk_profile="standard"),
            last_broker_execution_summary={},
            _stock_name_for_symbol=lambda _symbol: "浦发银行",
            _stock_id_for_symbol=lambda _symbol: "600000",
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
            _refresh_broker_status=lambda: counts.__setitem__("refresh", counts["refresh"] + 1),
        )

        original_describe = ui_refresh.describe_order_intent
        original_available = ui_refresh._order_available_quantity

        def _count_describe(*args, **kwargs):
            counts["describe"] += 1
            return original_describe(*args, **kwargs)

        def _count_available(*args, **kwargs):
            counts["available"] += 1
            return original_available(*args, **kwargs)

        with patch.object(ui_refresh, "describe_order_intent", side_effect=_count_describe), patch.object(
            ui_refresh,
            "_order_available_quantity",
            side_effect=_count_available,
        ):
            ui_refresh.fill_order_intents_table(window)
            self.assertEqual(counts["describe"], 1)
            self.assertEqual(counts["available"], 1)

            first_identity_item = table.item(0, 1)
            first_action_item = table.item(0, 2)

            window.order_intents = [
                replace(
                    intent,
                    quantity=1200,
                    reason="量能继续放大后上调仓位",
                )
            ]
            counts["describe"] = 0
            counts["available"] = 0

            ui_refresh.fill_order_intents_table(window)

        second_identity_item = table.item(0, 1)
        second_action_item = table.item(0, 2)
        self.assertEqual(counts["describe"], 1)
        self.assertEqual(counts["available"], 1)
        self.assertIs(first_identity_item, second_identity_item)
        self.assertIs(first_action_item, second_action_item)
        self.assertIn("买入", second_action_item.text())
        self.assertEqual(counts["refresh"], 2)

    def test_signal_panel_refresh_reuses_table_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        table = QTableWidget()
        table.setColumnCount(5)
        analysis = DailyAnalysis(
            date="2026-04-21",
            symbol="SHSE.600000",
            close=10.1,
            atr=0.3,
            ma_fast=10.0,
            ma_slow=9.8,
            breakout_level=10.2,
            volume_ratio=1.8,
            upper_shadow_pct=0.02,
            close_location=0.7,
            label="RECLAIM_LONG",
            score=88,
            reason="量价共振",
            entry_price=10.1,
            stop_price=9.7,
            target_price=11.0,
        )
        window = SimpleNamespace(
            analyses=[analysis],
            signal_table=table,
            _display_label=lambda value: {"RECLAIM_LONG": "回补做多"}.get(value, value),
            _selected_detail_signal_snapshot=lambda: None,
        )

        module.QuantHunterWindow._refresh_signal_panel(window)

        first_date_item = table.item(0, 0)
        first_score_item = table.item(0, 2)
        self.assertEqual(first_score_item.text(), "88")

        window.analyses = [replace(analysis, score=92, reason="主线强化")]
        module.QuantHunterWindow._refresh_signal_panel(window)

        second_date_item = table.item(0, 0)
        second_score_item = table.item(0, 2)
        self.assertIs(first_date_item, second_date_item)
        self.assertIs(first_score_item, second_score_item)
        self.assertEqual(second_score_item.text(), "92")

    def test_run_backtest_reuses_trades_table_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        table = QTableWidget()
        table.setColumnCount(7)
        metrics_text = QTextEdit()
        analysis = DailyAnalysis(
            date="2026-04-21",
            symbol="SHSE.600000",
            close=10.1,
            atr=0.3,
            ma_fast=10.0,
            ma_slow=9.8,
            breakout_level=10.2,
            volume_ratio=1.8,
            upper_shadow_pct=0.02,
            close_location=0.7,
            label="RECLAIM_LONG",
            score=88,
            reason="量价共振",
            entry_price=10.1,
            stop_price=9.7,
            target_price=11.0,
        )
        result_queue = [
            SimpleNamespace(
                trades=[
                    Trade(
                        symbol="SHSE.600000",
                        entry_date="2026-04-21",
                        exit_date="2026-04-22",
                        entry_price=10.1,
                        exit_price=10.8,
                        shares=1000,
                        pnl=700.0,
                        pnl_pct=0.0693,
                        hold_days=1,
                        exit_reason="target",
                    )
                ]
            ),
            SimpleNamespace(
                trades=[
                    Trade(
                        symbol="SHSE.600000",
                        entry_date="2026-04-21",
                        exit_date="2026-04-22",
                        entry_price=10.1,
                        exit_price=10.9,
                        shares=1000,
                        pnl=800.0,
                        pnl_pct=0.0792,
                        hold_days=1,
                        exit_reason="target",
                    )
                ]
            ),
        ]

        class _FakeBacktester:
            def __init__(self, *args, **kwargs) -> None:
                return None

            def run(self, *_args, **_kwargs):
                return result_queue.pop(0)

        window = SimpleNamespace(
            bars=[object()],
            analyses=[analysis],
            active_symbol="SHSE.600000",
            paths_by_symbol={"SHSE.600000": "demo.csv"},
            metrics_text=metrics_text,
            trades_table=table,
            strategy_params=lambda: None,
            _display_label=lambda value: {"RECLAIM_LONG": "回补做多"}.get(value, value),
            _selected_detail_trade_snapshot=lambda: None,
            _refresh_detail_workspace_panels=lambda: None,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
        )

        with patch.object(module, "Backtester", _FakeBacktester), patch.object(module, "format_result", lambda _result: "summary"):
            module.QuantHunterWindow.run_backtest_for_active(window, quiet=True)
            first_exit_price_item = table.item(0, 3)
            first_pnl_item = table.item(0, 5)
            self.assertEqual(first_exit_price_item.text(), "10.8")

            module.QuantHunterWindow.run_backtest_for_active(window, quiet=True)

        second_exit_price_item = table.item(0, 3)
        second_pnl_item = table.item(0, 5)
        self.assertIs(first_exit_price_item, second_exit_price_item)
        self.assertIs(first_pnl_item, second_pnl_item)
        self.assertEqual(second_exit_price_item.text(), "10.9")
        self.assertEqual(second_pnl_item.text(), "800.0")

    def test_strategy_history_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        strategy_table = QTableWidget()
        strategy_table.setColumnCount(8)
        trade_table = QTableWidget()
        trade_table.setColumnCount(10)
        history_rows = [
            {
                "strategy_name": "龙头模型",
                "signal_count": 12,
                "trade_count": 8,
                "filled_ratio": 0.66,
                "total_return": 0.23,
                "win_rate": 0.62,
                "max_drawdown": 0.08,
                "avg_hold_days": 1.8,
            }
        ]
        trade_rows = [
            {
                "strategy_name": "龙头模型",
                "stock_name": "浦发银行",
                "signal_date": "2026-04-21",
                "entry_date": "2026-04-21",
                "exit_date": "2026-04-22",
                "entry_price": 10.1,
                "exit_price": 10.8,
                "pnl_pct": 0.0693,
                "hold_days": 1,
                "exit_reason": "target",
            }
        ]
        window = SimpleNamespace(
            strategy_history_table=strategy_table,
            strategy_history_rows=history_rows,
            strategy_history_trade_table=trade_table,
            strategy_history_trade_rows=trade_rows,
            _fill_strategy_history_rank_table=lambda: None,
            _selected_strategy_history_name=lambda: "龙头模型",
            _strategy_history_selected_trades=lambda: list(window.strategy_history_trade_rows),
        )

        module.QuantHunterWindow._fill_strategy_history_table(window)
        module.QuantHunterWindow._fill_strategy_history_trade_table(window)

        first_signal_count_item = strategy_table.item(0, 1)
        first_exit_price_item = trade_table.item(0, 6)

        window.strategy_history_rows = [
            {
                **history_rows[0],
                "signal_count": 15,
                "trade_count": 9,
            }
        ]
        window.strategy_history_trade_rows = [
            {
                **trade_rows[0],
                "exit_price": 11.2,
                "pnl_pct": 0.1089,
            }
        ]

        module.QuantHunterWindow._fill_strategy_history_table(window)
        module.QuantHunterWindow._fill_strategy_history_trade_table(window)

        second_signal_count_item = strategy_table.item(0, 1)
        second_exit_price_item = trade_table.item(0, 6)
        self.assertIs(first_signal_count_item, second_signal_count_item)
        self.assertIs(first_exit_price_item, second_exit_price_item)
        self.assertEqual(second_signal_count_item.text(), "15")
        self.assertEqual(second_exit_price_item.text(), "11.2000")

    def test_strategy_history_rank_leaderboard_compare_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        rank_table = QTableWidget()
        rank_table.setColumnCount(7)
        leaderboard_table = QTableWidget()
        leaderboard_table.setColumnCount(8)
        compare_table = QTableWidget()
        compare_table.setColumnCount(10)
        strategy_rows = [
            {
                "strategy_name": "龙头模型",
                "total_return": 0.23,
                "profit_factor": 1.8,
                "payoff_ratio": 1.4,
                "max_drawdown": 0.08,
                "max_consecutive_losses": 2,
            }
        ]
        leaderboard_rows = [
            {
                "strategy_name": "龙头模型",
                "scenario_count": 4,
                "best_scenario_label": "牛市",
                "best_total_return": 0.38,
                "worst_scenario_label": "震荡",
                "worst_total_return": -0.04,
                "return_spread": 0.42,
                "avg_total_return": 0.18,
            }
        ]
        compare_rows = [
            {
                "scenario_label": "牛市",
                "strategy_name": "龙头模型",
                "max_hold_days": 3,
                "total_return": 0.31,
                "win_rate": 0.64,
                "max_drawdown": 0.07,
                "profit_factor": 1.9,
                "payoff_ratio": 1.5,
                "max_consecutive_losses": 2,
                "scenario_note": "趋势最强",
            }
        ]
        window = SimpleNamespace(
            strategy_history_rank_table=rank_table,
            strategy_history_rows=strategy_rows,
            strategy_history_leaderboard_table=leaderboard_table,
            strategy_history_leaderboard_rows=leaderboard_rows,
            strategy_history_compare_table=compare_table,
            strategy_history_compare_rows=compare_rows,
            _strategy_history_leaderboard_rows_view=lambda: list(window.strategy_history_leaderboard_rows),
            _strategy_history_selected_compare_rows=lambda: list(window.strategy_history_compare_rows),
        )

        module.QuantHunterWindow._fill_strategy_history_rank_table(window)
        module.QuantHunterWindow._fill_strategy_history_leaderboard_table(window)
        module.QuantHunterWindow._fill_strategy_history_compare_table(window)

        first_rank_return_item = rank_table.item(0, 2)
        first_leaderboard_best_item = leaderboard_table.item(0, 3)
        first_compare_return_item = compare_table.item(0, 3)

        window.strategy_history_rows = [{**strategy_rows[0], "total_return": 0.29, "profit_factor": 2.1}]
        window.strategy_history_leaderboard_rows = [{**leaderboard_rows[0], "best_total_return": 0.41, "avg_total_return": 0.22}]
        window.strategy_history_compare_rows = [{**compare_rows[0], "total_return": 0.35, "scenario_note": "趋势延续更强"}]

        module.QuantHunterWindow._fill_strategy_history_rank_table(window)
        module.QuantHunterWindow._fill_strategy_history_leaderboard_table(window)
        module.QuantHunterWindow._fill_strategy_history_compare_table(window)

        second_rank_return_item = rank_table.item(0, 2)
        second_leaderboard_best_item = leaderboard_table.item(0, 3)
        second_compare_return_item = compare_table.item(0, 3)
        self.assertIs(first_rank_return_item, second_rank_return_item)
        self.assertIs(first_leaderboard_best_item, second_leaderboard_best_item)
        self.assertIs(first_compare_return_item, second_compare_return_item)
        self.assertEqual(second_rank_return_item.text(), "29.00%")
        self.assertEqual(second_leaderboard_best_item.text(), "41.00%")
        self.assertEqual(second_compare_return_item.text(), "35.00%")

    def test_strategy_history_period_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        yearly_table = QTableWidget()
        yearly_table.setColumnCount(6)
        monthly_table = QTableWidget()
        monthly_table.setColumnCount(6)
        heatmap_table = QTableWidget()
        heatmap_table.setColumnCount(14)
        yearly_rows = [
            {
                "strategy_name": "龙头模型",
                "period": "2026",
                "trade_count": 12,
                "win_rate": 0.58,
                "total_return": 0.26,
                "avg_return": 0.03,
            }
        ]
        monthly_rows = [
            {
                "strategy_name": "龙头模型",
                "period": "2026-04",
                "trade_count": 4,
                "win_rate": 0.75,
                "total_return": 0.12,
                "avg_return": 0.03,
            }
        ]
        window = SimpleNamespace(
            strategy_history_yearly_table=yearly_table,
            strategy_history_monthly_table=monthly_table,
            strategy_history_heatmap_table=heatmap_table,
            _strategy_history_selected_yearly_rows=lambda: list(yearly_rows),
            _strategy_history_selected_monthly_rows=lambda: list(monthly_rows),
        )

        module.QuantHunterWindow._fill_strategy_history_period_tables(window)

        first_yearly_return_item = yearly_table.item(0, 4)
        first_monthly_return_item = monthly_table.item(0, 4)
        first_heatmap_april_item = heatmap_table.item(0, 5)

        yearly_rows[:] = [{**yearly_rows[0], "total_return": 0.31, "avg_return": 0.04}]
        monthly_rows[:] = [{**monthly_rows[0], "total_return": 0.18, "avg_return": 0.045}]

        module.QuantHunterWindow._fill_strategy_history_period_tables(window)

        second_yearly_return_item = yearly_table.item(0, 4)
        second_monthly_return_item = monthly_table.item(0, 4)
        second_heatmap_april_item = heatmap_table.item(0, 5)
        self.assertIs(first_yearly_return_item, second_yearly_return_item)
        self.assertIs(first_monthly_return_item, second_monthly_return_item)
        self.assertIs(first_heatmap_april_item, second_heatmap_april_item)
        self.assertEqual(second_yearly_return_item.text(), "31.00%")
        self.assertEqual(second_monthly_return_item.text(), "18.00%")
        self.assertEqual(second_heatmap_april_item.text(), "18.0%")

    def test_paper_trading_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        positions_table = QTableWidget()
        positions_table.setColumnCount(10)
        ledger_table = QTableWidget()
        ledger_table.setColumnCount(12)
        strategy_table = QTableWidget()
        strategy_table.setColumnCount(11)
        patrol_table = QTableWidget()
        patrol_table.setColumnCount(5)
        trading_text = QTextEdit()

        state_one = PaperTradingState(
            enabled=True,
            auto_run=True,
            initial_cash=100000.0,
            cash=98000.0,
            total_equity=101500.0,
            total_return=0.015,
            realized_pnl=500.0,
            last_run_at="2026-04-21 10:00:00",
            last_strategy_note="首轮运行",
            positions=[
                PaperPosition(
                    symbol="SHSE.600000",
                    stock_name="浦发银行",
                    quantity=1000,
                    available=1000,
                    avg_cost=10.0,
                    current_price=10.5,
                    market_value=10500.0,
                    strategy_name="龙头模型",
                    buy_point="10.00",
                    sell_point="10.80",
                    rationale="等待确认",
                    unrealized_pnl=500.0,
                    unrealized_pnl_pct=0.05,
                )
            ],
            ledger=[
                PaperOrderRecord(
                    order_id="P001",
                    timestamp="2026-04-21 10:00:00",
                    symbol="SHSE.600000",
                    stock_id="600000",
                    stock_name="浦发银行",
                    side="BUY",
                    price=10.0,
                    quantity=1000,
                    amount=10000.0,
                    strategy_name="龙头模型",
                    position_pct=0.1,
                    note="first buy",
                    realized_pnl=0.0,
                    cumulative_realized_pnl=0.0,
                )
            ],
            patrol_logs=[
                PaperPatrolLog(
                    timestamp="2026-04-21 10:05:00",
                    event_type="BUY",
                    summary="首次建仓",
                    equity=101500.0,
                    position_count=1,
                )
            ],
        )
        state_two = replace(
            state_one,
            cash=96000.0,
            total_equity=103000.0,
            total_return=0.03,
            realized_pnl=800.0,
            last_run_at="2026-04-21 10:30:00",
            positions=[
                replace(
                    state_one.positions[0],
                    current_price=10.9,
                    market_value=10900.0,
                    unrealized_pnl=900.0,
                    unrealized_pnl_pct=0.09,
                )
            ],
            ledger=[
                replace(
                    state_one.ledger[0],
                    side="SELL",
                    price=10.9,
                    amount=10900.0,
                    realized_pnl=900.0,
                    cumulative_realized_pnl=900.0,
                )
            ],
            patrol_logs=[
                replace(
                    state_one.patrol_logs[0],
                    event_type="SELL",
                    summary="止盈卖出",
                    equity=103000.0,
                )
            ],
        )

        analytics_payload = {
            "win_rate": 0.6,
            "closed_trade_count": 1,
            "avg_realized_pnl": 900.0,
            "strategy_rows": [
                {
                    "strategy_name": "龙头模型",
                    "buy_count": 1,
                    "sell_count": 1,
                    "win_rate": 0.6,
                    "avg_hold_days": 1.2,
                    "realized_pnl": 900.0,
                    "avg_position_pct": 0.1,
                }
            ],
        }
        rotation_payload = [
            {
                "strategy_name": "龙头模型",
                "bias_label": "进攻",
                "budget_multiplier": 1.2,
                "sample_count": 2,
                "rotation_score": 0.22,
            }
        ]
        experiment_payload = {
            "龙头模型": {
                "role_label": "主测",
                "decision": "继续主测",
                "win_rate_delta": 0.0,
                "hold_delta": 0.0,
            }
        }

        window = SimpleNamespace(
            paper_trading_box=object(),
            state=SimpleNamespace(strategy_risk_profile="standard"),
            paper_trading_state=state_one,
            paper_initial_cash_input=QLineEdit(),
            paper_max_position_input=QLineEdit(),
            paper_auto_interval_input=QLineEdit(),
            paper_auto_run_checkbox=QCheckBox(),
            paper_trading_status_label=QLabel(),
            paper_metric_labels={key: QLabel() for key in ["cash", "equity", "realized", "return", "win_rate", "closed", "positions", "fills"]},
            paper_positions_table=positions_table,
            paper_ledger_table=ledger_table,
            paper_strategy_table=strategy_table,
            paper_patrol_table=patrol_table,
            paper_trading_text=trading_text,
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _current_execution_profile=lambda: {},
            _current_strategy_runtime_config=lambda: (3, 0.8, False),
            _current_strategy_budget_bias_map=lambda: {},
            _refresh_paper_trading_equity_chart=lambda: None,
            _sync_paper_trading_timer=lambda: None,
            daily_pool_rows=[],
        )

        with patch.object(module, "summarize_paper_trading_performance", return_value=dict(analytics_payload)), patch.object(
            module,
            "build_strategy_rotation_snapshot",
            return_value=list(rotation_payload),
        ), patch.object(
            module,
            "_qh_paper_experiment_table_context_v44",
            return_value=dict(experiment_payload),
        ):
            module._qh_refresh_paper_trading_panels_v17(window)

            first_position_pnl_item = positions_table.item(0, 7)
            first_ledger_side_item = ledger_table.item(0, 3)
            first_strategy_decision_item = strategy_table.item(0, 10)
            first_patrol_event_item = patrol_table.item(0, 1)

            window.paper_trading_state = state_two
            module._qh_refresh_paper_trading_panels_v17(window)

        second_position_pnl_item = positions_table.item(0, 7)
        second_ledger_side_item = ledger_table.item(0, 3)
        second_strategy_decision_item = strategy_table.item(0, 10)
        second_patrol_event_item = patrol_table.item(0, 1)
        self.assertIs(first_position_pnl_item, second_position_pnl_item)
        self.assertIs(first_ledger_side_item, second_ledger_side_item)
        self.assertIs(first_strategy_decision_item, second_strategy_decision_item)
        self.assertIs(first_patrol_event_item, second_patrol_event_item)
        self.assertEqual(second_position_pnl_item.text(), "900")
        self.assertEqual(second_ledger_side_item.text(), "卖出")
        self.assertEqual(second_patrol_event_item.text(), "SELL")
        self.assertEqual(_color_value(second_ledger_side_item.foreground().color()), "#c44536")

    def test_trade_plan_and_position_advice_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        trade_plan_table = QTableWidget()
        trade_plan_table.setColumnCount(15)
        position_advice_table = QTableWidget()
        position_advice_table.setColumnCount(9)
        trade_plan_text = QTextEdit()
        market_pulse_text = QTextEdit()
        position_advice_text = QTextEdit()
        decision_one = SimpleNamespace(
            stock_name="浦发银行",
            stock_id="600000",
            symbol="SHSE.600000",
            action="BUY",
            stock_pool="龙头股",
            opportunity_tier="A",
            execution_readiness=82.0,
            confidence=0.86,
            planned_entry=10.1,
            planned_stop=9.7,
            planned_target=11.2,
            suggested_budget=12000.0,
            next_focus="关注量能延续",
            rationale="主线修复",
        )
        advice_one = SimpleNamespace(
            stock_name="浦发银行",
            stock_id="600000",
            symbol="SHSE.600000",
            action="HOLD",
            confidence=0.72,
            current_price=10.6,
            cost_price=10.0,
            pnl_pct=0.06,
            rationale="继续持有观察",
        )
        pulse = SimpleNamespace(
            market_regime="修复",
            risk_level="中",
            max_total_exposure=0.8,
            buy_ratio=0.5,
            average_total_score=81.0,
            strong_candidates=2,
            caution_candidates=1,
            sentiment_label="回暖",
            sentiment_score=72.0,
        )
        plan_one = SimpleNamespace(
            decisions=[decision_one],
            position_advice=[advice_one],
            notes=["等待确认"],
            market_sentiment="回暖",
            sentiment_score=72.0,
            market_pulse=pulse,
            max_new_positions=2,
        )
        decision_two = SimpleNamespace(**{**decision_one.__dict__, "planned_target": 11.5, "next_focus": "继续放量"})
        advice_two = SimpleNamespace(**{**advice_one.__dict__, "action": "REDUCE", "pnl_pct": 0.09, "rationale": "高位先收缩"})
        plan_two = SimpleNamespace(
            decisions=[decision_two],
            position_advice=[advice_two],
            notes=["优先锁盈"],
            market_sentiment="偏强",
            sentiment_score=78.0,
            market_pulse=SimpleNamespace(**{**pulse.__dict__, "sentiment_label": "偏强", "sentiment_score": 78.0}),
            max_new_positions=2,
        )
        plan_queue = [plan_one, plan_two]

        class _FakeDecisionEngine:
            def __init__(self, *args, **kwargs) -> None:
                return None

            def build_plan(self, *_args, **_kwargs):
                return plan_queue.pop(0)

        window = SimpleNamespace(
            trade_plan_table=trade_plan_table,
            position_advice_table=position_advice_table,
            trade_plan_text=trade_plan_text,
            market_pulse_text=market_pulse_text,
            position_advice_text=position_advice_text,
            trade_plan_focus_label=QLabel(),
            trade_plan_empty_hint=QLabel(),
            trade_plan_empty_actions=QLabel(),
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=80000.0),
            state=SimpleNamespace(
                strategy_risk_profile="standard",
                strategy_top_theme_limit=3,
                strategy_max_total_exposure=0.8,
                strategy_theme_drop_reduce=False,
                focus_themes=[],
            ),
            daily_pool_rows=[],
            holdings=[],
            _current_strategy_budget_bias_map=lambda: {},
            _emit_market_path_alerts=lambda _plan: None,
            _refresh_action_flow_cards=lambda _plan: None,
            _refresh_priority_cards=lambda _plan: None,
            _refresh_recommend_summary_cards=lambda _plan: None,
            _apply_plan_table_visuals_v4=lambda: None,
            _apply_position_advice_visuals_v4=lambda: None,
            _refresh_recommend_capability_overview_v1=lambda: None,
            _news_action_brief=lambda _symbol: "",
            _display_action=lambda value: {
                "BUY": "买入",
                "WATCH": "观察",
                "HOLD": "持有",
                "REDUCE": "减仓",
                "SELL": "卖出",
            }.get(str(value or "").upper(), str(value or "--")),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
        )

        with patch.object(module, "DecisionEngine", _FakeDecisionEngine), patch.object(module, "trade_decision_focus_lines", lambda *_args, **_kwargs: []):
            module.QuantHunterWindow._refresh_trade_plan(window)
            first_target_item = trade_plan_table.item(0, 11)
            first_action_item = position_advice_table.item(0, 3)

            window.cash_snapshot = CashSnapshot(available_cash=42000.0, total_assets=80000.0)
            module.QuantHunterWindow._refresh_trade_plan(window)

        second_target_item = trade_plan_table.item(0, 11)
        second_action_item = position_advice_table.item(0, 3)
        self.assertIs(first_target_item, second_target_item)
        self.assertIs(first_action_item, second_action_item)
        self.assertEqual(second_target_item.text(), "11.50")
        self.assertEqual(second_action_item.text(), "减仓")

    def test_board_tables_reuse_items(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        board_table = QTableWidget()
        board_table.setColumnCount(12)
        board_monitor_table = QTableWidget()
        board_monitor_table.setColumnCount(10)
        candidate_one = SimpleNamespace(
            stock_name="龙头样本",
            stock_id="300001",
            symbol="SZSE.300001",
            board_score=92.0,
            momentum_score=86.0,
            liquidity_score=80.0,
            leader_score=88.0,
            trigger_style="回封",
            risk_level="高",
            planned_entry=12.3,
            planned_stop=11.7,
            planned_target=13.5,
            rationale="回封预期",
        )
        monitor_one = SimpleNamespace(
            stock_name="龙头样本",
            stock_id="300001",
            symbol="SZSE.300001",
            monitor_state="盯盘",
            strength_score=84.0,
            continuity_score=78.0,
            reboard_probability=66.0,
            blast_risk=18.0,
            action_plan="等待回封",
            note="量能仍强",
        )
        candidate_two = SimpleNamespace(**{**candidate_one.__dict__, "risk_level": "低", "planned_target": 13.8})
        monitor_two = SimpleNamespace(**{**monitor_one.__dict__, "monitor_state": "观察", "note": "等待确认"})
        plan_queue = [
            SimpleNamespace(candidates=[candidate_one], monitor_rows=[monitor_one], temperature="高", avg_score=88.0, notes=["先看回封"]),
            SimpleNamespace(candidates=[candidate_two], monitor_rows=[monitor_two], temperature="中", avg_score=85.0, notes=["等待确认"]),
        ]

        class _FakeBoardEngine:
            def build(self, *_args, **_kwargs):
                return plan_queue.pop(0)

        window = SimpleNamespace(
            board_table=board_table,
            board_monitor_table=board_monitor_table,
            daily_pool_rows=[],
            board_text=QTextEdit(),
            board_monitor_text=QTextEdit(),
            _board_risk_colors=lambda level: (module.QColor("#FBEAEA"), module.QColor("#842029")) if level == "高" else (module.QColor("#E8F7EC"), module.QColor("#0F5132")),
            _board_monitor_colors=lambda state: (module.QColor("#FFF4DB"), module.QColor("#7C4A03")) if state == "盯盘" else (module.QColor("#E8F7EC"), module.QColor("#0F5132")),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _apply_identity_table_headers=lambda: None,
            _refresh_board_focus_panels=lambda: None,
        )

        with patch.object(module, "BoardModeEngine", _FakeBoardEngine):
            module.QuantHunterWindow._refresh_board_mode(window)
            first_board_risk_item = board_table.item(0, 8)
            first_monitor_state_item = board_monitor_table.item(0, 3)

            window.daily_pool_rows = [SimpleNamespace(symbol="SZSE.300001", action="BUY")]
            module.QuantHunterWindow._refresh_board_mode(window)

        second_board_risk_item = board_table.item(0, 8)
        second_monitor_state_item = board_monitor_table.item(0, 3)
        self.assertIs(first_board_risk_item, second_board_risk_item)
        self.assertIs(first_monitor_state_item, second_monitor_state_item)
        self.assertEqual(second_board_risk_item.text(), "低")
        self.assertEqual(second_monitor_state_item.text(), "观察")

    def test_trade_plan_refresh_reuses_cached_plan_when_inputs_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        build_calls = {"count": 0}
        plan = SimpleNamespace(
            decisions=[],
            position_advice=[],
            notes=[],
            market_sentiment="观望",
            sentiment_score=60.0,
            market_pulse=SimpleNamespace(
                market_regime="震荡",
                risk_level="中",
                max_total_exposure=0.8,
                buy_ratio=0.4,
                average_total_score=70.0,
                strong_candidates=0,
                caution_candidates=0,
                sentiment_label="观望",
                sentiment_score=60.0,
            ),
            max_new_positions=0,
        )

        class _FakeDecisionEngine:
            def __init__(self, *args, **kwargs) -> None:
                return None

            def build_plan(self, *_args, **_kwargs):
                build_calls["count"] += 1
                return plan

        window = SimpleNamespace(
            trade_plan_table=QTableWidget(),
            position_advice_table=QTableWidget(),
            trade_plan_text=QTextEdit(),
            market_pulse_text=QTextEdit(),
            position_advice_text=QTextEdit(),
            trade_plan_focus_label=QLabel(),
            trade_plan_empty_hint=QLabel(),
            trade_plan_empty_actions=QLabel(),
            cash_snapshot=CashSnapshot(available_cash=50000.0, total_assets=80000.0),
            state=SimpleNamespace(
                strategy_risk_profile="standard",
                strategy_top_theme_limit=3,
                strategy_max_total_exposure=0.8,
                strategy_theme_drop_reduce=False,
                focus_themes=[],
            ),
            daily_pool_rows=[],
            holdings=[],
            _current_strategy_budget_bias_map=lambda: {},
            _emit_market_path_alerts=lambda _plan: None,
            _refresh_action_flow_cards=lambda _plan: None,
            _refresh_priority_cards=lambda _plan: None,
            _refresh_recommend_summary_cards=lambda _plan: None,
            _apply_plan_table_visuals_v4=lambda: None,
            _apply_position_advice_visuals_v4=lambda: None,
            _refresh_recommend_capability_overview_v1=lambda: None,
            _news_action_brief=lambda _symbol: "",
            _display_action=lambda value: value,
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
        )

        with patch.object(module, "DecisionEngine", _FakeDecisionEngine), patch.object(module, "trade_decision_focus_lines", lambda *_args, **_kwargs: []):
            module.QuantHunterWindow._refresh_trade_plan(window)
            module.QuantHunterWindow._refresh_trade_plan(window)

        self.assertEqual(build_calls["count"], 1)

    def test_board_mode_refresh_reuses_cached_plan_when_inputs_unchanged(self) -> None:
        _ = self._app
        module = importlib.import_module("app_qt")
        build_calls = {"count": 0}
        board_plan = SimpleNamespace(candidates=[], monitor_rows=[], temperature="低", avg_score=0.0, notes=["等待候选"])

        class _FakeBoardEngine:
            def build(self, *_args, **_kwargs):
                build_calls["count"] += 1
                return board_plan

        window = SimpleNamespace(
            board_table=QTableWidget(),
            board_monitor_table=QTableWidget(),
            daily_pool_rows=[],
            board_text=QTextEdit(),
            board_monitor_text=QTextEdit(),
            _board_risk_colors=lambda _level: (module.QColor("#FBEAEA"), module.QColor("#842029")),
            _board_monitor_colors=lambda _state: (module.QColor("#FFF4DB"), module.QColor("#7C4A03")),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _apply_identity_table_headers=lambda: None,
            _refresh_board_focus_panels=lambda: None,
        )

        with patch.object(module, "BoardModeEngine", _FakeBoardEngine):
            module.QuantHunterWindow._refresh_board_mode(window)
            module.QuantHunterWindow._refresh_board_mode(window)

        self.assertEqual(build_calls["count"], 1)

    def test_execution_profile_cache_reuses_results_until_inputs_change(self) -> None:
        module = importlib.import_module("app_qt")
        build_calls = {"count": 0}

        def _fake_build(**_kwargs):
            build_calls["count"] += 1
            return {"recap": {"runs": build_calls["count"]}}

        window = SimpleNamespace(
            order_submission_records=[{"symbol": "SHSE.600000"}],
            holdings=[],
            order_intents=[],
            order_submission_log=["boot"],
        )
        window._snapshot_signature_v1 = lambda value: module.QuantHunterWindow._snapshot_signature_v1(window, value)
        window._execution_profile_inputs_signature_v1 = lambda: module.QuantHunterWindow._execution_profile_inputs_signature_v1(window)

        with patch.object(module, "build_execution_quality_profile", side_effect=_fake_build):
            first = module.QuantHunterWindow._current_execution_profile(window)
            second = module.QuantHunterWindow._current_execution_profile(window)
            self.assertEqual(build_calls["count"], 1)
            self.assertEqual(first["recap"]["runs"], 1)
            self.assertEqual(second["recap"]["runs"], 1)

            window.order_submission_log.append("changed")
            third = module.QuantHunterWindow._current_execution_profile(window)

        self.assertEqual(build_calls["count"], 2)
        self.assertEqual(third["recap"]["runs"], 2)

    def test_paper_analytics_bundle_cache_reuses_results_until_inputs_change(self) -> None:
        module = importlib.import_module("app_qt")
        calls = {"summary": 0, "rotation": 0, "execution": 0}

        def _fake_execution(**_kwargs):
            calls["execution"] += 1
            return {"recap": {"token": calls["execution"]}}

        def _fake_summary(*_args, **_kwargs):
            calls["summary"] += 1
            return {"closed_trade_count": calls["summary"]}

        def _fake_rotation(*_args, **_kwargs):
            calls["rotation"] += 1
            return [{"strategy_name": "龙头模型", "budget_multiplier": 1.0, "sample_count": calls["rotation"]}]

        paper_state = PaperTradingState(enabled=True, last_run_at="2026-04-21 10:00:00")
        window = SimpleNamespace(
            state=SimpleNamespace(paper_trading_state=paper_state),
            paper_trading_state=paper_state,
            order_submission_records=[],
            holdings=[],
            order_intents=[],
            order_submission_log=[],
        )
        window._snapshot_signature_v1 = lambda value: module.QuantHunterWindow._snapshot_signature_v1(window, value)
        window._execution_profile_inputs_signature_v1 = lambda: module.QuantHunterWindow._execution_profile_inputs_signature_v1(window)
        window._current_execution_profile = lambda: module.QuantHunterWindow._current_execution_profile(window)

        with patch.object(module, "build_execution_quality_profile", side_effect=_fake_execution), patch.object(
            module,
            "summarize_paper_trading_performance",
            side_effect=_fake_summary,
        ), patch.object(
            module,
            "build_strategy_rotation_snapshot",
            side_effect=_fake_rotation,
        ):
            first = module.QuantHunterWindow._cached_paper_analytics_bundle_v1(window)
            second = module.QuantHunterWindow._cached_paper_analytics_bundle_v1(window)
            self.assertEqual(calls["execution"], 1)
            self.assertEqual(calls["summary"], 1)
            self.assertEqual(calls["rotation"], 1)
            self.assertEqual(first["analytics"]["closed_trade_count"], 1)
            self.assertEqual(second["analytics"]["closed_trade_count"], 1)

            window.paper_trading_state = replace(paper_state, last_run_at="2026-04-21 10:30:00")
            window.state = SimpleNamespace(paper_trading_state=window.paper_trading_state)
            third = module.QuantHunterWindow._cached_paper_analytics_bundle_v1(window)

        self.assertEqual(calls["execution"], 1)
        self.assertEqual(calls["summary"], 2)
        self.assertEqual(calls["rotation"], 2)
        self.assertEqual(third["analytics"]["closed_trade_count"], 2)
