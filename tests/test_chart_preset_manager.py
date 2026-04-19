from __future__ import annotations

import unittest
from types import SimpleNamespace


class ChartPresetManagerTests(unittest.TestCase):
    def test_market_chart_hottest_preset_key_returns_top_rank(self) -> None:
        import app_qt as module

        window = SimpleNamespace(
            _market_chart_usage_rank_rows=lambda limit=None: [("BALANCED", 8), ("USER_1", 5)],
        )

        hottest = module.QuantHunterWindow._market_chart_hottest_preset_key(window)

        self.assertEqual(hottest, "BALANCED")

    def test_market_chart_template_timeline_entries_filter_by_template(self) -> None:
        import app_qt as module

        builtin = {
            "BALANCED": {
                "label": "Balanced",
                "template_owner": "Research Desk",
                "template_version": "T-2026.04",
                "update_log": ["2026-04-19 | Team default view upgraded"],
            },
            "FLOW": {
                "label": "Flow",
                "template_owner": "Research Desk",
                "template_version": "T-2026.04",
                "update_log": ["2026-04-20 | Flow template refreshed"],
            },
        }
        window = SimpleNamespace(
            _market_chart_builtin_preset_specs=lambda: builtin,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
        )

        entries = module.QuantHunterWindow._market_chart_template_timeline_entries(window, preset_key="FLOW")

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["preset_key"], "FLOW")
        self.assertEqual(entries[0]["template_owner"], "Research Desk")

    def test_ordered_market_chart_custom_preset_keys_filters_tags_and_sort(self) -> None:
        import app_qt as module

        presets = {
            "USER_1": {
                "label": "My Watchlist",
                "detail": "Intraday watch view",
                "tags": ["watch", "flow"],
                "overlays": {"MA"},
                "annotation_mode": "FULL",
                "indicator": "MACD",
                "expanded": False,
                "pinned": False,
            },
            "USER_2": {
                "label": "Signal Replay",
                "detail": "Review entry and exit points",
                "tags": ["replay"],
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
        filtered = module.QuantHunterWindow._ordered_market_chart_custom_preset_keys(window, search_text="replay")
        filtered_by_tag = module.QuantHunterWindow._ordered_market_chart_custom_preset_keys(window, search_text="flow")

        self.assertEqual(ordered, ["USER_2", "USER_1"])
        self.assertEqual(filtered, ["USER_2"])
        self.assertEqual(filtered_by_tag, ["USER_1"])

    def test_record_market_chart_preset_usage_increments_counter(self) -> None:
        import app_qt as module

        state = SimpleNamespace(market_chart_preset_usage_counts={})
        window = SimpleNamespace(
            market_chart_preset_usage_counts={"BALANCED": 2},
            state=state,
            _normalize_market_chart_preset_key=lambda value: module.QuantHunterWindow._normalize_market_chart_preset_key(value),
            _normalized_market_chart_preset_usage_counts=lambda: {"BALANCED": 2},
            save_state=lambda: setattr(window, "saved", True),
        )

        module.QuantHunterWindow._record_market_chart_preset_usage(window, "BALANCED", persist=True)

        self.assertEqual(window.market_chart_preset_usage_counts["BALANCED"], 3)
        self.assertEqual(state.market_chart_preset_usage_counts["BALANCED"], 3)
        self.assertTrue(getattr(window, "saved", False))


if __name__ == "__main__":
    unittest.main()
