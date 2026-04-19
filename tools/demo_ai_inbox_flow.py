from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an offscreen demo for the AI review + message center inbox flow.")
    parser.add_argument("--visible", action="store_true", help="Show the window instead of running fully offscreen.")
    parser.add_argument(
        "--scenario",
        choices=["default", "triage", "resolved"],
        default="default",
        help="Choose which inbox state to demonstrate.",
    )
    parser.add_argument(
        "--sort",
        choices=["latest", "unread", "open", "priority"],
        default="latest",
        help="Set the message center sort mode before printing the summary.",
    )
    parser.add_argument(
        "--only-unhandled",
        action="store_true",
        help="Show only unhandled items in the message center.",
    )
    return parser


def _scenario_events(name: str) -> list[dict[str, object]]:
    base = [
        {
            "category": "news",
            "title": "消息源已载入",
            "detail": "混合消息源已载入 6 条消息，覆盖 3 只股票。",
            "symbol": "SHSE.600000",
            "level": "SUCCESS",
        },
        {
            "category": "ai",
            "title": "浦发银行 AI评测完成",
            "detail": "gpt-5.4 | 结论：继续跟 | 执行建议：等承接确认后推进。",
            "symbol": "SHSE.600000",
            "level": "SUCCESS",
        },
        {
            "category": "trade",
            "title": "浦发银行 已提交",
            "detail": "BUY 200 股 @ 12.300 | 回执状态：PENDING",
            "symbol": "SHSE.600000",
            "level": "SUCCESS",
        },
        {
            "category": "ai",
            "title": "AI评测失败",
            "detail": "OpenAI 请求失败：invalid_api_key",
            "symbol": "SZSE.300001",
            "level": "ERROR",
        },
    ]
    if name == "triage":
        base.append(
            {
                "category": "trade",
                "title": "龙头样本 提交失败",
                "detail": "SELL 300 股 @ 18.400 | 原因：可用数量不足",
                "symbol": "SZSE.300001",
                "level": "ERROR",
            }
        )
    return base


def main() -> int:
    args = build_parser().parse_args()
    if not args.visible:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    import app_qt

    app = app_qt.QApplication.instance() or app_qt.QApplication([])
    window = app_qt.QuantHunterWindow()
    window.show()
    app.processEvents()

    window.smart_message_events = []
    window._recommend_message_center_visible_events = []
    window.recommend_message_center_selected_signature = None
    window._refresh_recommend_message_center()
    app.processEvents()

    demo_events = _scenario_events(args.scenario)

    for item in demo_events:
        window._append_smart_message_event(**item)
        app.processEvents()

    if args.scenario == "resolved":
        if demo_events:
            first = window.smart_message_events[0]
            window._update_smart_message_event(app_qt.message_event_signature(first), is_read=True, is_handled=True)
        window.mark_all_recommend_messages_read()
        app.processEvents()

    if hasattr(window, "recommend_message_center_sort_combo"):
        combo = window.recommend_message_center_sort_combo
        index = combo.findData(args.sort)
        if index >= 0:
            combo.setCurrentIndex(index)
    if args.only_unhandled and hasattr(window, "recommend_message_center_unhandled_checkbox"):
        window.recommend_message_center_unhandled_checkbox.setChecked(True)
    app.processEvents()

    window._navigate_to_workspace("recommend", "recommend_message_center_table")
    app.processEvents()

    summary = getattr(window, "recommend_message_center_summary_label", None)
    badge = getattr(window, "recommend_message_center_badge_label", None)
    open_button = getattr(window, "recommend_message_center_open_button", None)
    action_label = getattr(window, "recommend_message_center_action_label", None)
    table = getattr(window, "recommend_message_center_table", None)
    tab_text = window.tabs.tabText(window.tabs.indexOf(window.recommend_tab)) if hasattr(window, "tabs") else "--"

    print("Demo Flow")
    print(f"- Scenario: {args.scenario}")
    print(f"- Sort: {args.sort}")
    print(f"- Only unhandled: {args.only_unhandled}")
    print(f"- Recommend tab: {tab_text}")
    print(f"- Summary: {summary.text() if summary is not None else '--'}")
    print(f"- Badge: {badge.text() if badge is not None else '--'}")
    print(f"- Primary action: {open_button.text() if open_button is not None else '--'}")
    print(f"- Action hint: {action_label.text() if action_label is not None else '--'}")
    print(f"- Rows: {table.rowCount() if table is not None else 0}")
    if table is not None and table.rowCount() > 0:
        first_row = [table.item(0, column).text() if table.item(0, column) is not None else "" for column in range(table.columnCount())]
        print(f"- First row: {' | '.join(first_row)}")
    print("- Suggested next step: open the 推荐 tab and inspect the 统一消息中心 panel.")

    if not args.visible:
        window.close()
        app.processEvents()
        return 0

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
