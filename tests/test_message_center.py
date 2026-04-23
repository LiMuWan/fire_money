from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from types import SimpleNamespace

from quant_hunter.message_center import (
    SmartMessageEvent,
    append_message_event,
    build_message_center_event_detail,
    build_message_center_snapshot,
    mark_all_message_events_read,
    message_center_action_bar_text,
    message_center_badge_text,
    message_center_button_label,
    message_event_action_hint,
    message_event_status_label,
    message_level_tone,
    remove_handled_message_events,
    sort_message_events,
    update_message_event_flags,
)
from quant_hunter.storage import AppState, load_app_state, save_app_state
from quant_hunter.ui_runtime import build_runtime_log_line


class MessageCenterTests(unittest.TestCase):
    def _temp_dir(self) -> Path:
        output_dir = Path(__file__).resolve().parent / ".tmp"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def test_build_message_center_snapshot_groups_counts_and_latest_event(self) -> None:
        events = []
        events = append_message_event(
            events,
            timestamp="10:01:00",
            category="news",
            title="消息源已载入",
            detail="示例消息 4 条",
            level="SUCCESS",
        )
        events = append_message_event(
            events,
            timestamp="10:02:00",
            category="ai",
            title="浦发银行 AI评测完成",
            detail="gpt-5.4 | 继续跟",
            symbol="SHSE.600000",
            level="SUCCESS",
        )
        events = append_message_event(
            events,
            timestamp="10:03:00",
            category="trade",
            title="浦发银行 已提交",
            detail="BUY 200 股 @ 12.300",
            symbol="SHSE.600000",
            level="SUCCESS",
        )

        snapshot = build_message_center_snapshot(events, category_filter="all")

        self.assertEqual(snapshot["headline"], "交易 / 完成")
        self.assertIn("状态总览：待处理 3 | 未读 3 | AI 1 | 消息 1 | 交易 1 | 系统 0", snapshot["text"])
        self.assertIn("浦发银行 已提交", snapshot["text"])
        self.assertIn("消息源已载入", snapshot["text"])

    def test_build_message_center_snapshot_supports_filter(self) -> None:
        events = []
        events = append_message_event(events, timestamp="10:01:00", category="news", title="消息源已载入")
        events = append_message_event(events, timestamp="10:02:00", category="ai", title="AI评测完成")

        snapshot = build_message_center_snapshot(events, category_filter="ai")

        self.assertIn("当前视角：AI", snapshot["text"])
        self.assertIn("AI评测完成", snapshot["text"])
        self.assertNotIn("消息源已载入", snapshot["text"])

    def test_message_center_action_and_detail_use_terminal_templates(self) -> None:
        event = SmartMessageEvent(
            timestamp="10:04:00",
            category="trade",
            title="浦发银行 已提交",
            detail="BUY 200 股 @ 12.300",
            symbol="SHSE.600000",
            level="SUCCESS",
        )
        hint = message_event_action_hint(event)
        action_text = message_center_action_bar_text(event, hint)
        detail_text = build_message_center_event_detail(
            event,
            action_hint=hint,
            route_label="去交易",
            route_workspace="broker",
            route_widget="execution_table",
        )

        self.assertIn("事件动作：", action_text)
        self.assertIn("处理进度：未读 / 未处理", action_text)
        self.assertIn("终端动作：去交易盯回执", detail_text)
        self.assertIn("下一步：先核对提交结果、成交状态和执行偏差。", detail_text)
        self.assertIn("联动路径：去交易 -> broker/execution_table", detail_text)

    def test_message_center_badge_and_button_labels_use_terminal_copy(self) -> None:
        badge_text = message_center_badge_text({"open": 4, "unread": 2})

        self.assertEqual(badge_text, "状态：待处理 4 | 未读 2")
        self.assertEqual(message_center_button_label("clear"), "清空事件")
        self.assertEqual(message_center_button_label("open"), "看链路")

    def test_message_level_tone_maps_priority_levels(self) -> None:
        self.assertEqual(message_level_tone("INFO"), "idle")
        self.assertEqual(message_level_tone("SUCCESS"), "buy")
        self.assertEqual(message_level_tone("WARN"), "watch")
        self.assertEqual(message_level_tone("ERROR"), "risk")

    def test_message_event_action_hint_maps_ai_key_error_to_config(self) -> None:
        hint = message_event_action_hint(
            SmartMessageEvent(
                timestamp="10:03:00",
                category="ai",
                title="AI评测失败",
                detail="OpenAI 请求失败：invalid_api_key",
                symbol="SHSE.600000",
                level="ERROR",
            )
        )

        self.assertEqual(hint.button_label, "去配置补 Key")
        self.assertIn("API Key", hint.summary)

    def test_message_event_action_hint_maps_trade_success_to_broker(self) -> None:
        hint = message_event_action_hint(
            SmartMessageEvent(
                timestamp="10:04:00",
                category="trade",
                title="浦发银行 已提交",
                detail="BUY 200 股 @ 12.300",
                symbol="SHSE.600000",
                level="SUCCESS",
            )
        )

        self.assertEqual(hint.button_label, "去交易盯回执")
        self.assertIn("提交结果", hint.summary)

    def test_message_event_action_hint_maps_news_success_to_opportunity_pool(self) -> None:
        hint = message_event_action_hint(
            SmartMessageEvent(
                timestamp="10:05:00",
                category="news",
                title="消息源已载入",
                detail="机器人题材热度回升",
                symbol="SZSE.300001",
                level="SUCCESS",
            )
        )

        self.assertEqual(hint.button_label, "去机会池复核")
        self.assertIn("主线", hint.summary)

    def test_message_event_action_hint_default_targets_opportunity_pool(self) -> None:
        hint = message_event_action_hint(None)

        self.assertEqual(hint.button_label, "看机会")
        self.assertIn("机会池", hint.summary)

    def test_update_message_event_flags_marks_read_and_handled(self) -> None:
        event = SmartMessageEvent(
            timestamp="10:05:00",
            category="news",
            title="消息源已载入",
            detail="示例消息 4 条",
            symbol="SHSE.600000",
            level="SUCCESS",
        )
        updated = update_message_event_flags(
            [event],
            target_signature=("10:05:00", "news", "消息源已载入", "示例消息 4 条", "SHSE.600000", "SUCCESS"),
            is_read=True,
            is_handled=True,
        )

        self.assertTrue(updated[0].is_read)
        self.assertTrue(updated[0].is_handled)
        self.assertIn("已读", message_event_status_label(updated[0]))

    def test_remove_handled_message_events_keeps_open_items(self) -> None:
        events = [
            SmartMessageEvent(timestamp="10:01:00", category="news", title="消息源已载入", is_handled=False),
            SmartMessageEvent(timestamp="10:02:00", category="ai", title="AI评测完成", is_handled=True),
            SmartMessageEvent(timestamp="10:03:00", category="trade", title="已提交", is_handled=False),
        ]

        remaining = remove_handled_message_events(events)

        self.assertEqual(len(remaining), 2)
        self.assertEqual([item.title for item in remaining], ["消息源已载入", "已提交"])

    def test_mark_all_message_events_read_marks_only_unread_items(self) -> None:
        events = [
            SmartMessageEvent(timestamp="10:01:00", category="news", title="消息源已载入", is_read=False),
            SmartMessageEvent(timestamp="10:02:00", category="ai", title="AI评测完成", is_read=True),
        ]

        updated = mark_all_message_events_read(events)

        self.assertTrue(updated[0].is_read)
        self.assertTrue(updated[1].is_read)

    def test_sort_message_events_prioritizes_unread_and_open_modes(self) -> None:
        events = [
            SmartMessageEvent(timestamp="10:01:00", category="news", title="消息源已载入", is_read=True, is_handled=False),
            SmartMessageEvent(timestamp="10:02:00", category="ai", title="AI评测完成", is_read=False, is_handled=True),
            SmartMessageEvent(timestamp="10:03:00", category="trade", title="已提交", is_read=False, is_handled=False),
        ]

        unread_sorted = sort_message_events(events, mode="unread")
        open_sorted = sort_message_events(events, mode="open")

        self.assertEqual(unread_sorted[0].title, "已提交")
        self.assertEqual(unread_sorted[1].title, "AI评测完成")
        self.assertEqual(open_sorted[0].title, "已提交")
        self.assertEqual(open_sorted[1].title, "消息源已载入")

    def test_sort_message_events_priority_mode_promotes_errors(self) -> None:
        events = [
            SmartMessageEvent(timestamp="10:01:00", category="news", title="消息源已载入", level="SUCCESS"),
            SmartMessageEvent(timestamp="10:02:00", category="ai", title="AI评测失败", level="ERROR"),
            SmartMessageEvent(timestamp="10:03:00", category="trade", title="已提交", level="SUCCESS"),
        ]

        sorted_rows = sort_message_events(events, mode="priority")

        self.assertEqual(sorted_rows[0].title, "AI评测失败")

    def test_runtime_log_line_uses_terminal_level_labels(self) -> None:
        class _FakeNow:
            def strftime(self, _fmt: str) -> str:
                return "10:08:00"

        class _FakeDateTime:
            @staticmethod
            def now() -> _FakeNow:
                return _FakeNow()

        self.assertEqual(
            build_runtime_log_line("机会池已刷新", datetime_cls=_FakeDateTime, level="INFO"),
            "[10:08:00] [状态] 机会池已刷新",
        )
        self.assertEqual(
            build_runtime_log_line("委托已提交", datetime_cls=_FakeDateTime, level="SUCCESS"),
            "[10:08:00] [完成] 委托已提交",
        )

    def test_app_state_roundtrip_persists_message_center_events(self) -> None:
        state_path = self._temp_dir() / "app_state_message_center.json"
        save_app_state(
            state_path,
            AppState(
                smart_message_events=[
                    {
                        "timestamp": "10:01:00",
                        "category": "news",
                        "title": "消息源已载入",
                        "detail": "示例消息 4 条",
                        "symbol": "SHSE.600000",
                        "level": "SUCCESS",
                        "is_read": True,
                        "is_handled": False,
                    },
                    {
                        "timestamp": "10:02:00",
                        "category": "ai",
                        "title": "AI评测完成",
                        "detail": "gpt-5.4 | 继续跟",
                        "symbol": "SHSE.600000",
                        "level": "SUCCESS",
                        "is_read": True,
                        "is_handled": True,
                    },
                ]
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(len(restored.smart_message_events), 2)
        self.assertEqual(restored.smart_message_events[0]["category"], "news")
        self.assertEqual(restored.smart_message_events[1]["title"], "AI评测完成")
        self.assertTrue(restored.smart_message_events[0]["is_read"])
        self.assertTrue(restored.smart_message_events[1]["is_handled"])

    def test_app_state_roundtrip_persists_message_center_preferences(self) -> None:
        state_path = self._temp_dir() / "app_state_message_center_prefs.json"
        save_app_state(
            state_path,
            AppState(
                recommend_message_center_filter="trade",
                recommend_message_center_show_unhandled_only=True,
                recommend_message_center_sort="priority",
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(restored.recommend_message_center_filter, "trade")
        self.assertTrue(restored.recommend_message_center_show_unhandled_only)
        self.assertEqual(restored.recommend_message_center_sort, "priority")

    def test_recommend_message_toast_skips_repeated_same_event_when_visible(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        class DummyTimer:
            def __init__(self) -> None:
                self.calls = 0
                self.last_ms = 0

            def start(self, value: int) -> None:
                self.calls += 1
                self.last_ms = value

        label = module.QLabel()
        calls = {"label": 0}
        window = SimpleNamespace(
            recommend_message_toast_label=label,
            _recommend_message_toast_timer=DummyTimer(),
            _stock_name_for_symbol=lambda symbol: "龙头样本",
            _set_label_text_if_changed=lambda widget, text: (
                calls.__setitem__("label", calls["label"] + 1),
                widget.setText(text),
            ),
        )
        event = module.SmartMessageEvent(
            timestamp="10:30:00",
            category="trade",
            title="龙头样本 已提交",
            detail="BUY 200 股 @ 12.300",
            symbol="SZSE.300001",
            level="SUCCESS",
        )

        module.QuantHunterWindow._maybe_show_recommend_message_toast(window, event)
        first_label_calls = calls["label"]
        first_timer_calls = window._recommend_message_toast_timer.calls
        module.QuantHunterWindow._maybe_show_recommend_message_toast(window, event)

        self.assertEqual(calls["label"], first_label_calls)
        self.assertEqual(window._recommend_message_toast_timer.calls, first_timer_calls)
        self.assertTrue(label.isVisible())

    def test_refresh_recommend_message_center_ui_smoke(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        summary_label = module.QLabel()
        badge_label = module.QLabel()
        table = module.QTableWidget()
        table.setColumnCount(5)
        text_widget = module.QTextEdit()
        filter_combo = module.QComboBox()
        for label, value in [("全部", "all"), ("AI", "ai"), ("消息", "news"), ("交易", "trade"), ("系统", "system")]:
            filter_combo.addItem(label, value)
        sort_combo = module.QComboBox()
        for label, value in [("最新优先", "latest"), ("未读优先", "unread"), ("待处理优先", "open"), ("异常优先", "priority")]:
            sort_combo.addItem(label, value)
        unhandled_checkbox = module.QCheckBox()
        action_label = module.QLabel()
        symbol_button = module.QPushButton()
        open_button = module.QPushButton()
        mark_all_button = module.QPushButton()
        clear_handled_button = module.QPushButton()
        mark_read_button = module.QPushButton()
        mark_handled_button = module.QPushButton()
        tabs = module.QTabWidget()
        recommend_tab = module.QWidget()
        tabs.addTab(recommend_tab, "推荐")

        events = [
            SmartMessageEvent(
                timestamp="10:01:00",
                category="news",
                title="消息源已载入",
                detail="示例消息 4 条",
                symbol="SHSE.600000",
                level="SUCCESS",
                is_read=False,
                is_handled=False,
            ),
            SmartMessageEvent(
                timestamp="10:02:00",
                category="trade",
                title="浦发银行 已提交",
                detail="BUY 200 股 @ 12.300",
                symbol="SHSE.600000",
                level="SUCCESS",
                is_read=False,
                is_handled=False,
            ),
        ]

        window = SimpleNamespace(
            smart_message_events=events,
            recommend_message_center_filter="all",
            recommend_message_center_show_unhandled_only=False,
            recommend_message_center_summary_label=summary_label,
            recommend_message_center_badge_label=badge_label,
            recommend_message_center_table=table,
            recommend_message_center_text=text_widget,
            recommend_message_center_filter_combo=filter_combo,
            recommend_message_center_sort_combo=sort_combo,
            recommend_message_center_unhandled_checkbox=unhandled_checkbox,
            recommend_message_center_action_label=action_label,
            recommend_message_center_symbol_button=symbol_button,
            recommend_message_center_open_button=open_button,
            recommend_message_center_mark_all_read_button=mark_all_button,
            recommend_message_center_clear_handled_button=clear_handled_button,
            recommend_message_center_mark_read_button=mark_read_button,
            recommend_message_center_mark_handled_button=mark_handled_button,
            recommend_message_center_metric_cards={},
            recommend_message_center_metric_labels={},
            recommend_message_center_metric_accents={},
            _recommend_message_center_visible_events=[],
            recommend_message_center_selected_signature=None,
            tabs=tabs,
            recommend_tab=recommend_tab,
            recommend_message_center_sort="latest",
            _stock_name_for_symbol=lambda symbol: "浦发银行" if symbol == "SHSE.600000" else symbol,
            _filtered_smart_message_events=lambda: module.QuantHunterWindow._filtered_smart_message_events(window),
            _selected_recommend_message_event=lambda: module.QuantHunterWindow._selected_recommend_message_event(window),
            _message_event_route=lambda event: module.QuantHunterWindow._message_event_route(window, event),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: (
                widget.setText(text),
                widget.setToolTip(tooltip if tooltip is not None else widget.toolTip()),
            ),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _select_table_row_if_needed=lambda current_table, row_index: (
                current_table.selectRow(row_index),
                True,
            )[-1],
        )

        module.QuantHunterWindow._refresh_recommend_message_center(window)

        self.assertEqual(table.rowCount(), 2)
        self.assertIn("状态：待处理 2 | 未读 2", badge_label.text())
        self.assertEqual(tabs.tabText(0), "推荐(2/2)")
        self.assertIn("消息中控：交易 / 完成", summary_label.text())
        self.assertEqual(open_button.text(), "去交易盯回执")
        self.assertTrue(mark_all_button.isEnabled())


    def test_refresh_recommend_message_center_auto_focuses_new_priority_event(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        summary_label = module.QLabel()
        open_button = module.QPushButton()
        table = module.QTableWidget(0, 5)
        text_widget = module.QTextEdit()
        filter_combo = module.QComboBox()
        for label, value in [("全部", "all"), ("AI", "ai"), ("消息", "news"), ("交易", "trade"), ("系统", "system")]:
            filter_combo.addItem(label, value)
        sort_combo = module.QComboBox()
        for label, value in [("最新优先", "latest"), ("未读优先", "unread"), ("待处理优先", "open"), ("异常优先", "priority")]:
            sort_combo.addItem(label, value)

        events = [
            SmartMessageEvent(
                timestamp="10:01:00",
                category="news",
                title="消息源已载入",
                detail="示例消息 4 条",
                symbol="SHSE.600000",
                level="SUCCESS",
                is_read=False,
                is_handled=False,
            )
        ]

        window = SimpleNamespace(
            smart_message_events=events,
            recommend_message_center_filter="all",
            recommend_message_center_show_unhandled_only=False,
            recommend_message_center_summary_label=summary_label,
            recommend_message_center_table=table,
            recommend_message_center_text=text_widget,
            recommend_message_center_filter_combo=filter_combo,
            recommend_message_center_sort_combo=sort_combo,
            recommend_message_center_unhandled_checkbox=module.QCheckBox(),
            recommend_message_center_action_label=module.QLabel(),
            recommend_message_center_symbol_button=module.QPushButton(),
            recommend_message_center_open_button=open_button,
            recommend_message_center_mark_all_read_button=module.QPushButton(),
            recommend_message_center_clear_handled_button=module.QPushButton(),
            recommend_message_center_mark_read_button=module.QPushButton(),
            recommend_message_center_mark_handled_button=module.QPushButton(),
            recommend_message_center_metric_cards={},
            recommend_message_center_metric_labels={},
            recommend_message_center_metric_accents={},
            _recommend_message_center_visible_events=[],
            recommend_message_center_selected_signature=None,
            recommend_message_center_selection_locked=False,
            recommend_message_center_sort="latest",
            _stock_name_for_symbol=lambda symbol: "浦发银行" if symbol == "SHSE.600000" else symbol,
            _filtered_smart_message_events=lambda: module.QuantHunterWindow._filtered_smart_message_events(window),
            _selected_recommend_message_event=lambda: module.QuantHunterWindow._selected_recommend_message_event(window),
            _message_event_route=lambda event: module.QuantHunterWindow._message_event_route(window, event),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: (
                widget.setText(text),
                widget.setToolTip(tooltip if tooltip is not None else widget.toolTip()),
            ),
            _set_plain_text_if_changed=lambda widget, text: widget.setPlainText(text),
            _select_table_row_if_needed=lambda current_table, row_index: (
                current_table.selectRow(row_index),
                True,
            )[-1],
        )

        module.QuantHunterWindow._refresh_recommend_message_center(window)
        self.assertIn("消息中控：消息 / 完成", summary_label.text())
        self.assertEqual(open_button.text(), "去机会池复核")

        window.smart_message_events.append(
            SmartMessageEvent(
                timestamp="10:02:00",
                category="ai",
                title="AI评测失败",
                detail="OpenAI 请求失败：invalid_api_key",
                symbol="SHSE.600000",
                level="ERROR",
                is_read=False,
                is_handled=False,
            )
        )
        module.QuantHunterWindow._refresh_recommend_message_center(window)

        self.assertIn("消息中控：AI / 异常", summary_label.text())
        self.assertEqual(open_button.text(), "去配置补 Key")

    def test_message_event_route_maps_ai_key_error_to_config(self) -> None:
        module = importlib.import_module("app_qt")

        event = module.SmartMessageEvent(
            timestamp="10:02:00",
            category="ai",
            title="AI评测失败",
            detail="OpenAI 请求失败：invalid_api_key",
            symbol="SHSE.600000",
            level="ERROR",
        )

        route = module.QuantHunterWindow._message_event_route(SimpleNamespace(), event)

        self.assertEqual(route, ("config", "ai_review_status_text", "去配置"))


if __name__ == "__main__":
    unittest.main()
