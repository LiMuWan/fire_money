from __future__ import annotations

import importlib
import unittest
from pathlib import Path
from types import SimpleNamespace

from quant_hunter.message_center import (
    SmartMessageEvent,
    append_message_event,
    build_message_center_snapshot,
    message_event_action_hint,
    message_level_tone,
)
from quant_hunter.storage import AppState, load_app_state, save_app_state


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
        self.assertIn("事件统计：全部 3 | AI 1 | 消息 1 | 交易 1 | 系统 0", snapshot["text"])
        self.assertIn("浦发银行 已提交", snapshot["text"])
        self.assertIn("消息源已载入", snapshot["text"])

    def test_build_message_center_snapshot_supports_filter(self) -> None:
        events = []
        events = append_message_event(events, timestamp="10:01:00", category="news", title="消息源已载入")
        events = append_message_event(events, timestamp="10:02:00", category="ai", title="AI评测完成")

        snapshot = build_message_center_snapshot(events, category_filter="ai")

        self.assertIn("当前筛选：AI", snapshot["text"])
        self.assertIn("AI评测完成", snapshot["text"])
        self.assertNotIn("消息源已载入", snapshot["text"])

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

        self.assertEqual(hint.button_label, "去配置页补 Key")
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

        self.assertEqual(hint.button_label, "去交易页看回执")
        self.assertIn("提交结果", hint.summary)

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
                    },
                    {
                        "timestamp": "10:02:00",
                        "category": "ai",
                        "title": "AI评测完成",
                        "detail": "gpt-5.4 | 继续跟",
                        "symbol": "SHSE.600000",
                        "level": "SUCCESS",
                    },
                ]
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        restored = load_app_state(state_path)

        self.assertEqual(len(restored.smart_message_events), 2)
        self.assertEqual(restored.smart_message_events[0]["category"], "news")
        self.assertEqual(restored.smart_message_events[1]["title"], "AI评测完成")

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


if __name__ == "__main__":
    unittest.main()
