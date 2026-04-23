from __future__ import annotations

import importlib
import json
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from quant_hunter.ai_review import (
    AIReviewConfig,
    build_recommendation_review_prompt,
    review_recommendation_with_openai,
    stream_recommendation_review_with_openai,
)
from quant_hunter.models import NewsCatalyst, RecommendationRow
from quant_hunter.storage import AppState, load_app_state, save_app_state


class _FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def read(self) -> bytes:
        return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class _FakeStreamResponse:
    def __init__(self, lines: list[str]) -> None:
        self.lines = [line.encode("utf-8") for line in lines]
        self.index = 0

    def readline(self) -> bytes:
        if self.index >= len(self.lines):
            return b""
        line = self.lines[self.index]
        self.index += 1
        return line

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


class AIReviewTests(unittest.TestCase):
    def _temp_dir(self) -> Path:
        output_dir = Path(__file__).resolve().parent / ".tmp"
        output_dir.mkdir(exist_ok=True)
        return output_dir

    def _sample_row(self) -> RecommendationRow:
        return RecommendationRow(
            symbol="SHSE.600000",
            stock_id="600000",
            stock_name="浦发银行",
            action="BUY",
            label="RECLAIM_LONG",
            signal_date="2026-04-18",
            close=12.34,
            entry_price=12.30,
            stop_price=11.80,
            target_price=13.20,
            technical_score=78.0,
            position_score=74.0,
            persistence_score=72.0,
            news_score=66.0,
            leader_score=60.0,
            total_score=76.5,
            mainline_tag="银行",
            primary_strategy="掘龙决策",
            opportunity_tier="继续跟",
            mainline_risk_flag="中",
            execution_readiness=73.0,
            confidence_score=69.0,
            mainline_window_score=71.0,
            risk_reward_ratio=1.8,
            catalyst="公告催化",
            rationale="量价修复后重新站回关键位，适合作为研究观察样本。",
            next_focus="观察量能承接和午后回流。",
            invalidation_reason="跌破防守位或主线切换后重新评估。",
        )

    def test_build_recommendation_review_prompt_contains_required_sections(self) -> None:
        row = self._sample_row()
        prompt = build_recommendation_review_prompt(
            row,
            news_items=[
                NewsCatalyst(
                    symbol=row.symbol,
                    title="公司发布季度经营简报",
                    summary="经营数据略超预期，市场关注资金回流。",
                    published_at="2026-04-18 09:35:00",
                    source="交易所公告",
                )
            ],
        )

        self.assertIn("结论：", prompt)
        self.assertIn("执行建议：", prompt)
        self.assertIn("浦发银行", prompt)
        self.assertIn("公司发布季度经营简报", prompt)

    def test_review_recommendation_with_openai_parses_responses_payload(self) -> None:
        row = self._sample_row()
        payload = {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {
                            "type": "output_text",
                            "text": (
                                "结论：继续跟\n"
                                "一句话：当前更适合做研究跟踪而不是盲目追高。\n"
                                "风险等级：中\n"
                                "执行建议：等待承接确认后再推进。\n"
                            ),
                        }
                    ],
                }
            ]
        }

        with patch("quant_hunter.ai_review.urllib.request.urlopen", return_value=_FakeResponse(payload)):
            result = review_recommendation_with_openai(
                AIReviewConfig(api_key="sk-test"),
                row,
                now_fn=lambda: datetime(2026, 4, 18, 10, 30, 0),
            )

        self.assertEqual(result.symbol, row.symbol)
        self.assertEqual(result.reviewed_at, "2026-04-18 10:30:00")
        self.assertEqual(result.summary, "继续跟")
        self.assertIn("执行建议：等待承接确认后再推进。", result.content)

    def test_stream_recommendation_review_with_openai_emits_deltas(self) -> None:
        row = self._sample_row()
        streamed: list[str] = []
        lines = [
            'event: response.output_text.delta\n',
            'data: {"type":"response.output_text.delta","delta":"结论：继续跟\\n"}\n',
            '\n',
            'event: response.output_text.delta\n',
            'data: {"type":"response.output_text.delta","delta":"一句话：当前更适合继续跟踪。\\n"}\n',
            '\n',
            'event: response.completed\n',
            'data: {"type":"response.completed","response":{"model":"gpt-5.4","output":[{"type":"message","content":[{"type":"output_text","text":"结论：继续跟\\n一句话：当前更适合继续跟踪。\\n执行建议：等待承接确认后再推进。"}]}]}}\n',
            '\n',
        ]

        with patch("quant_hunter.ai_review.urllib.request.urlopen", return_value=_FakeStreamResponse(lines)):
            result = stream_recommendation_review_with_openai(
                AIReviewConfig(api_key="sk-test"),
                row,
                on_event=lambda event: streamed.append(event.text),
                now_fn=lambda: datetime(2026, 4, 18, 10, 35, 0),
            )

        self.assertGreaterEqual(len(streamed), 2)
        self.assertEqual(streamed[0], "结论：继续跟\n")
        self.assertIn("一句话：当前更适合继续跟踪。", streamed[-1])
        self.assertEqual(result.summary, "继续跟")
        self.assertIn("执行建议：等待承接确认后再推进。", result.content)

    def test_app_state_roundtrip_persists_ai_review_settings(self) -> None:
        state_path = self._temp_dir() / "app_state_ai_review.json"
        save_app_state(
            state_path,
            AppState(
                ai_review_base_url="https://api.openai.com/v1",
                ai_review_api_key="sk-demo",
                ai_review_model="gpt-5.4",
                ai_review_reasoning_effort="high",
                ai_review_max_output_tokens=1200,
                ai_review_timeout_seconds=60.0,
                ai_review_auto_run_enabled=True,
                ai_review_auto_run_on_news_refresh=False,
                ai_review_auto_run_on_pool_refresh=True,
                ui_density="watch",
            ),
        )
        self.addCleanup(lambda: state_path.unlink(missing_ok=True))

        raw_payload = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotEqual(raw_payload["ai_review_api_key"], "sk-demo")

        restored = load_app_state(state_path)
        self.assertEqual(restored.ai_review_base_url, "https://api.openai.com/v1")
        self.assertEqual(restored.ai_review_api_key, "sk-demo")
        self.assertEqual(restored.ai_review_model, "gpt-5.4")
        self.assertEqual(restored.ai_review_reasoning_effort, "high")
        self.assertEqual(restored.ai_review_max_output_tokens, 1200)
        self.assertEqual(restored.ai_review_timeout_seconds, 60.0)
        self.assertEqual(restored.ui_density, "watch")
        self.assertTrue(restored.ai_review_auto_run_enabled)
        self.assertFalse(restored.ai_review_auto_run_on_news_refresh)
        self.assertTrue(restored.ai_review_auto_run_on_pool_refresh)

    def test_refresh_ai_review_status_panel_skips_repeated_same_signature(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        calls = {"text": 0}
        panel = module.QTextEdit()
        result = SimpleNamespace(symbol="SHSE.600000", stock_name="浦发银行", reviewed_at="2026-04-19 10:30:00", summary="继续跟")
        window = SimpleNamespace(
            ai_review_status_text=panel,
            ai_review_results_by_symbol={"SHSE.600000": result},
            ai_review_last_symbol="SHSE.600000",
            ai_review_pending_symbol="",
            ai_review_last_error="",
            ai_review_last_trigger="manual",
            ai_review_partial_content_by_symbol={},
            _current_ai_review_config=lambda: AIReviewConfig(api_key="sk-test", model="gpt-5.4", reasoning_effort="high", max_output_tokens=1200, timeout_seconds=60.0),
            _current_ai_review_automation_settings=lambda: (True, True, True),
            _stock_name_for_symbol=lambda symbol: "浦发银行",
            _set_plain_text_if_changed=lambda widget, text: (calls.__setitem__("text", calls["text"] + 1), widget.setPlainText(text)),
        )

        module.QuantHunterWindow._refresh_ai_review_status_panel(window)
        first_calls = calls["text"]
        module.QuantHunterWindow._refresh_ai_review_status_panel(window)

        self.assertEqual(calls["text"], first_calls)

    def test_refresh_ai_review_panel_skips_repeated_same_signature(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        calls = {"text": 0}
        panel = module.QTextEdit()
        row = self._sample_row()
        cached = SimpleNamespace(
            symbol=row.symbol,
            stock_name=row.stock_name,
            reviewed_at="2026-04-19 10:35:00",
            model="gpt-5.4",
            summary="继续跟",
            content="结论：继续跟\n执行建议：等待承接确认后推进。",
        )
        window = SimpleNamespace(
            recommend_ai_review_text=panel,
            ai_review_results_by_symbol={row.symbol: cached},
            ai_review_pending_symbol="",
            ai_review_last_symbol=row.symbol,
            ai_review_last_error="",
            ai_review_partial_content_by_symbol={},
            news_catalysts={},
            _selected_daily_pool_recommendation=lambda: row,
            _current_ai_review_config=lambda: AIReviewConfig(api_key="sk-test", model="gpt-5.4", reasoning_effort="high", max_output_tokens=1200, timeout_seconds=60.0),
            _stock_name_for_symbol=lambda symbol: row.stock_name,
            _set_plain_text_if_changed=lambda widget, text: (calls.__setitem__("text", calls["text"] + 1), widget.setPlainText(text)),
        )

        module.QuantHunterWindow._refresh_ai_review_panel(window, row)
        first_calls = calls["text"]
        module.QuantHunterWindow._refresh_ai_review_panel(window, row)

        self.assertEqual(calls["text"], first_calls)

    def test_handle_ai_review_stream_event_skips_repeated_same_status_label(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app

        class _CountingLabel(module.QLabel):
            def __init__(self) -> None:
                super().__init__()
                self.set_calls = 0

            def setText(self, text: str) -> None:
                self.set_calls += 1
                super().setText(text)

        calls = {"status": 0, "panel": 0}
        label = _CountingLabel()
        window = SimpleNamespace(
            recommend_status_label=label,
            ai_review_partial_content_by_symbol={},
            ai_review_pending_symbol="SHSE.600000",
            _stock_name_for_symbol=lambda symbol: "娴﹀彂閾惰",
            _refresh_ai_review_status_panel=lambda: calls.__setitem__("status", calls["status"] + 1),
            _refresh_ai_review_panel=lambda: calls.__setitem__("panel", calls["panel"] + 1),
        )
        event = SimpleNamespace(
            symbol="SHSE.600000",
            text="缁撹锛氱户缁窡",
            delta="缁撹锛氱户缁窡\n",
        )

        module.QuantHunterWindow._handle_ai_review_stream_event(window, event)
        first_calls = label.set_calls
        module.QuantHunterWindow._handle_ai_review_stream_event(window, event)

        self.assertEqual(label.set_calls, first_calls)
        self.assertEqual(calls["status"], 2)
        self.assertEqual(calls["panel"], 2)

    def test_start_ai_review_without_api_key_routes_to_config_and_refreshes_feedback(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        row = self._sample_row()
        nav_calls: list[tuple[str, str | None]] = []
        refresh_calls: list[str] = []
        window = SimpleNamespace(
            _current_ai_review_config=lambda: AIReviewConfig(api_key="", model="gpt-5.4"),
            _navigate_to_workspace=lambda workspace_key, widget_name=None: nav_calls.append((workspace_key, widget_name)),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: (
                widget.setText(text),
                widget.setToolTip(tooltip or ""),
            ),
            _refresh_live_workspace_summary_panels=lambda: refresh_calls.append("summary"),
            _refresh_workspace_focus_banners=lambda: refresh_calls.append("focus"),
            config_status_banner=module.QLabel(),
        )

        with patch.object(module.QMessageBox, "information", return_value=0) as info_box:
            result = module.QuantHunterWindow._start_ai_review_for_row(window, row, trigger="manual")

        self.assertFalse(result)
        self.assertEqual(nav_calls, [("config", "ai_review_status_text")])
        self.assertEqual(refresh_calls, ["summary", "focus"])
        self.assertIn("当前缺 OpenAI API Key", window.config_status_banner.text())
        info_box.assert_called_once()

    def test_start_ai_review_refreshes_summary_and_banners_when_started(self) -> None:
        module = importlib.import_module("app_qt")
        app = module.QApplication.instance() or module.QApplication([])
        _ = app
        row = self._sample_row()
        calls = {"status": 0, "panel": 0, "summary": 0, "focus": 0}
        window = SimpleNamespace(
            _current_ai_review_config=lambda: AIReviewConfig(api_key="sk-test", model="gpt-5.4", reasoning_effort="high"),
            _is_job_running=lambda job_name: False,
            _stock_name_for_symbol=lambda symbol: row.stock_name,
            _ai_review_signature_for_row=lambda current: "sig",
            ai_review_completed_signature_by_symbol={},
            ai_review_pending_signature_by_symbol={},
            scan_rows=[],
            universe_analyses={},
            universe_bars={},
            news_catalysts={},
            _stock_profile_for_symbol=lambda symbol: None,
            ai_review_partial_content_by_symbol={},
            ai_review_pending_symbol="",
            ai_review_last_symbol="",
            ai_review_last_error="",
            ai_review_last_trigger="",
            _append_runtime_log=lambda text: None,
            _append_smart_message_event=lambda **kwargs: None,
            recommend_status_label=module.QLabel(),
            _set_label_text_if_changed=lambda widget, text, tooltip=None: widget.setText(text),
            _refresh_ai_review_status_panel=lambda: calls.__setitem__("status", calls["status"] + 1),
            _refresh_ai_review_panel=lambda current=None: calls.__setitem__("panel", calls["panel"] + 1),
            _refresh_live_workspace_summary_panels=lambda: calls.__setitem__("summary", calls["summary"] + 1),
            _refresh_workspace_focus_banners=lambda: calls.__setitem__("focus", calls["focus"] + 1),
            _apply_ai_review_result=lambda result: None,
            _handle_ai_review_error=lambda error: None,
            _handle_ai_review_stream_event=lambda event: None,
            _run_background_job=lambda *args, **kwargs: True,
        )

        result = module.QuantHunterWindow._start_ai_review_for_row(window, row, trigger="manual")

        self.assertTrue(result)
        self.assertEqual(calls, {"status": 1, "panel": 1, "summary": 1, "focus": 1})
        self.assertIn("正在请求 gpt-5.4 评测", window.recommend_status_label.text())


if __name__ == "__main__":
    unittest.main()
