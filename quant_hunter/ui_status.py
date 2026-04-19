from __future__ import annotations

try:
    from PySide6.QtGui import QColor
except ModuleNotFoundError:  # pragma: no cover - enables non-Qt test environments
    class QColor:  # type: ignore[override]
        def __init__(self, value: str) -> None:
            self.value = value

from .strategy_registry import get_strategy_registry, strategy_badge_palette_meta, strategy_empty_hint_meta
from .ui_config import DISPLAY_TEXT


def submission_stage_key(item: dict[str, str]) -> str:
    order_status = str(item.get("order_status", "") or "").upper()
    fill_status = str(item.get("fill_status", "") or "").upper()
    failure_reason = str(item.get("failure_reason", "") or "").strip()
    if failure_reason or order_status in {"FAILED", "REJECTED", "CANCELLED"} or fill_status in {"REJECTED", "CANCELLED"}:
        return "exception"
    if fill_status == "FILLED":
        return "filled"
    if fill_status in {"PARTIAL", "PART_FILLED", "PARTIALLY_FILLED"}:
        return "partial"
    if fill_status == "PENDING":
        return "pending"
    if order_status in {"SUBMITTED", "ACCEPTED", "QUEUED"}:
        return "submitted"
    return "idle"


def submission_node_label(item: dict[str, str]) -> str:
    mapping = {
        "exception": "异常待处理",
        "filled": "已成交",
        "partial": "部分成交",
        "pending": "待成交",
        "submitted": "已送出",
        "idle": "等待回执",
    }
    return mapping.get(submission_stage_key(item), "等待回执")


def submission_table_snapshot(
    item: dict[str, str],
    *,
    stock_name: str,
    stock_id: str,
    action_text: str,
    order_status_text: str,
    fill_status_text: str,
) -> dict[str, str]:
    symbol = str(item.get("symbol", "") or "")
    timestamp_text = str(item.get("timestamp", "") or "--")
    time_part = timestamp_text.split(" ", 1)[-1] if " " in timestamp_text else timestamp_text
    failure_reason = str(item.get("failure_reason", "") or "").strip()
    message_text = str(item.get("message", "") or "").strip() or "等待更多反馈"
    timeline_value = f"{time_part}\n{submission_node_label(item)}"
    focus_value = f"{stock_name}  {stock_id}\n标识 {symbol or '--'} | {order_status_text or '--'}"
    action_value = f"{action_text}\n{order_status_text or '--'} / {fill_status_text or '--'}"
    tooltip = "\n".join(
        [
            f"时间：{timestamp_text}",
            f"股票：{stock_name} ({stock_id} / {symbol or '--'})",
            f"动作：{action_text}",
            f"订单状态：{order_status_text or '--'}",
            f"成交状态：{fill_status_text or '--'}",
            f"异常：{failure_reason or '无'}",
            f"反馈：{message_text}",
        ]
    )
    return {
        "timeline": timeline_value,
        "focus": focus_value,
        "action": action_value,
        "exception": failure_reason or "无",
        "message": message_text,
        "tooltip": tooltip,
    }


def submission_risk_badge_text_v2(item: dict[str, str]) -> str:
    mapping = {
        "exception": "\u7ea2\u706f \u5f02\u5e38",
        "filled": "\u7eff\u706f \u5df2\u6210\u4ea4",
        "partial": "\u9752\u706f \u90e8\u6210",
        "pending": "\u9ec4\u706f \u5f85\u6210\u4ea4",
        "submitted": "\u84dd\u706f \u5df2\u9001\u51fa",
        "idle": "\u7070\u706f \u5f85\u56de\u5199",
    }
    return mapping.get(submission_stage_key(item), "\u7070\u706f \u5f85\u56de\u5199")


def submission_risk_badge_palette_v2(item: dict[str, str]) -> tuple[QColor, QColor]:
    palette = {
        "exception": ("#5A1623", "#FFD7DD"),
        "filled": ("#143624", "#A7F0C5"),
        "partial": ("#123B33", "#A5F0DF"),
        "pending": ("#4B3613", "#FFE08D"),
        "submitted": ("#163552", "#B7DAFF"),
        "idle": ("#27303A", "#D9E2EE"),
    }
    background, foreground = palette.get(submission_stage_key(item), palette["idle"])
    return QColor(background), QColor(foreground)


def submission_table_snapshot_v2(
    item: dict[str, str],
    *,
    stock_name: str,
    stock_id: str,
    action_text: str,
    order_status_text: str,
    fill_status_text: str,
) -> dict[str, str]:
    def _safe_float(value: str) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(value: str) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    symbol = str(item.get("symbol", "") or "")
    timestamp_text = str(item.get("timestamp", "") or "--")
    time_part = timestamp_text.split(" ", 1)[-1] if " " in timestamp_text else timestamp_text
    failure_reason = str(item.get("failure_reason", "") or "").strip()
    message_text = str(item.get("message", "") or "").strip() or "\u7b49\u5f85\u66f4\u591a\u53cd\u9988"
    order_id = str(item.get("order_id", "") or "").strip()
    planned_price = _safe_float(str(item.get("planned_price", "") or "0"))
    submitted_price = _safe_float(str(item.get("price", "") or "0"))
    fill_price = _safe_float(str(item.get("fill_price", "") or "0"))
    planned_quantity = _safe_int(str(item.get("planned_quantity", "") or "0"))
    submitted_quantity = _safe_int(str(item.get("quantity", "") or "0"))
    fill_quantity = _safe_int(str(item.get("fill_quantity", "") or "0"))

    price_lines: list[str] = []
    if planned_price > 0:
        price_lines.append(f"\u8ba1 {planned_price:.2f}")
    if submitted_price > 0:
        price_lines.append(f"\u9001 {submitted_price:.2f}")
    if fill_price > 0:
        price_lines.append(f"\u6210 {fill_price:.2f}")
    price_compare = "\n".join(price_lines) if price_lines else "--"

    quantity_lines: list[str] = []
    if planned_quantity > 0:
        quantity_lines.append(f"\u8ba1 {planned_quantity}")
    if submitted_quantity > 0:
        quantity_lines.append(f"\u9001 {submitted_quantity}")
    if fill_quantity > 0:
        quantity_lines.append(f"\u6210 {fill_quantity}")
    quantity_compare = "\n".join(quantity_lines) if quantity_lines else "--"

    deviation_note = ""
    if planned_price > 0 and fill_price > 0:
        price_deviation_bps = (fill_price - planned_price) / planned_price * 10000.0
        if abs(price_deviation_bps) >= 1.0:
            deviation_note = (
                f"\u4ef7\u683c\u9ad8\u4e8e\u8ba1\u5212 {price_deviation_bps:.1f}bp"
                if price_deviation_bps > 0
                else f"\u4ef7\u683c\u4f4e\u4e8e\u8ba1\u5212 {abs(price_deviation_bps):.1f}bp"
            )
    if planned_quantity > 0 and fill_quantity > 0 and fill_quantity != planned_quantity:
        quantity_note = (
            f"\u6570\u91cf\u8f83\u8ba1\u5212\u589e\u52a0 {fill_quantity - planned_quantity}"
            if fill_quantity > planned_quantity
            else f"\u6570\u91cf\u8f83\u8ba1\u5212\u51cf\u5c11 {planned_quantity - fill_quantity}"
        )
        deviation_note = f"{deviation_note} | {quantity_note}".strip(" |")
    timeline_value = f"{time_part}\n{submission_node_label(item)}"
    focus_value = f"{stock_name}  {stock_id}\n\u6807\u8bc6 {symbol or '--'} | {order_status_text or '--'}"
    action_value = f"{action_text}\n{order_status_text or '--'} / {fill_status_text or '--'}"
    tooltip = "\n".join(
        [
            f"\u65f6\u95f4\uff1a{timestamp_text}",
            f"\u80a1\u7968\uff1a{stock_name} ({stock_id} / {symbol or '--'})",
            f"\u52a8\u4f5c\uff1a{action_text}",
            f"\u8ba2\u5355 ID\uff1a{order_id or '--'}",
            f"\u8ba2\u5355\u72b6\u6001\uff1a{order_status_text or '--'}",
            f"\u6210\u4ea4\u72b6\u6001\uff1a{fill_status_text or '--'}",
            f"\u8ba1\u5212\u4ef7/\u9001\u5ba1\u4ef7/\u6210\u4ea4\u4ef7\uff1a{item.get('planned_price', '--') or '--'} / {item.get('price', '--') or '--'} / {item.get('fill_price', '--') or '--'}",
            f"\u8ba1\u5212\u91cf/\u9001\u5ba1\u91cf/\u6210\u4ea4\u91cf\uff1a{item.get('planned_quantity', '--') or '--'} / {item.get('quantity', '--') or '--'} / {item.get('fill_quantity', '--') or '--'}",
            f"\u6267\u884c\u504f\u5dee\uff1a{deviation_note or '\u6682\u65e0\u660e\u663e\u504f\u5dee'}",
            f"\u5f02\u5e38\uff1a{failure_reason or '\u65e0'}",
            f"\u53cd\u9988\uff1a{message_text}",
        ]
    )
    return {
        "timeline": timeline_value,
        "focus": focus_value,
        "action": action_value,
        "price_compare": price_compare,
        "quantity_compare": quantity_compare,
        "deviation_note": deviation_note,
        "risk_badge": submission_risk_badge_text_v2(item),
        "exception_detail": failure_reason or "\u65e0",
        "message": f"{message_text}\n{deviation_note}" if deviation_note else message_text,
        "tooltip": tooltip,
    }


def signal_colors(action: str, label: str) -> tuple[QColor, QColor]:
    key = label or action
    if key == "RECLAIM_LONG" or action == "BUY":
        return QColor("#E8F7EC"), QColor("#0F5132")
    if key == "TRAP_DETECTED" or action == "AVOID":
        return QColor("#FBEAEA"), QColor("#842029")
    if key == "WATCH":
        return QColor("#FFF4DB"), QColor("#7C4A03")
    if key == "NONE" or action == "HOLD":
        return QColor("#F5F6F7"), QColor("#495057")
    return QColor("#F8F9FA"), QColor("#212529")


def submission_colors(item: dict[str, str]) -> tuple[QColor, QColor]:
    palette = {
        "exception": ("#32151B", "#FFB4BC"),
        "filled": ("#102B20", "#73E0A5"),
        "partial": ("#12322A", "#7CE5C2"),
        "pending": ("#34260F", "#FFD46B"),
        "submitted": ("#12283E", "#8FCAFF"),
        "idle": ("#1B222B", "#D9E2EE"),
    }
    background, foreground = palette.get(submission_stage_key(item), palette["idle"])
    return QColor(background), QColor(foreground)


def market_pool_colors(row) -> tuple[QColor, QColor]:
    if getattr(row, "pct_change", 0.0) >= 8:
        return QColor("#2b0909"), QColor("#ff5e57")
    if getattr(row, "main_inflow", 0.0) > 1.5e8:
        return QColor("#08291d"), QColor("#25d07f")
    if getattr(row, "turnover", 0.0) >= 10:
        return QColor("#2b2409"), QColor("#f7d354")
    return QColor("#0f1116"), QColor("#d7dce5")


def board_risk_colors(risk_level: str) -> tuple[QColor, QColor]:
    if risk_level == "中":
        return QColor("#E9F7EF"), QColor("#146C43")
    if risk_level == "中高":
        return QColor("#FFF4DB"), QColor("#7C4A03")
    if risk_level == "高":
        return QColor("#FBEAEA"), QColor("#842029")
    return QColor("#F8F9FA"), QColor("#212529")


def board_monitor_colors(state: str) -> tuple[QColor, QColor]:
    if state == "强势连板候选":
        return QColor("#E8F7EC"), QColor("#0F5132")
    if state == "回封观察":
        return QColor("#FFF4DB"), QColor("#7C4A03")
    if state == "风险警示":
        return QColor("#FBEAEA"), QColor("#842029")
    return QColor("#F8F9FA"), QColor("#212529")


def market_mode_label(value: str) -> str:
    return {"auto": "自动", "cache": "仅缓存", "sample": "示例模式"}.get(value, "自动")


def market_source_mode_label(value: str) -> str:
    return {
        "remote": "东方财富实时",
        "cache_fresh": "本地新缓存",
        "cache_stale": "本地旧缓存",
        "cache_only": "仅缓存模式",
        "sample": "示例模式",
        "unknown": "未识别",
    }.get(value, "未识别")


def fund_badge_palette(text: str) -> tuple[str, str]:
    mapping = {
        "游资强攻": ("#5f1114", "#ff7f86"),
        "主力净流入": ("#0f3a28", "#41f0a3"),
        "机构趋势": ("#12345d", "#81b9ff"),
        "低位试盘": ("#5d4a12", "#ffd76d"),
        "强势博弈": ("#3c1f63", "#d2a8ff"),
    }
    return mapping.get(text, ("#24303a", "#dce4ef"))


def strategy_badge_palette(text: str) -> tuple[str, str]:
    registry = get_strategy_registry()
    strategy_name = registry.canonical_strategy_name(str(text or "").strip()) or str(text or "").strip()
    palette = strategy_badge_palette_meta(strategy_name)
    if palette != ("#24303a", "#dce4ef"):
        return palette
    fallback_cycle = [
        ("#5b1216", "#ff6a6f"),
        ("#0f3951", "#7ed7ff"),
        ("#57430f", "#ffd75b"),
        ("#204728", "#7ef5a2"),
        ("#4b3418", "#ffcf82"),
        ("#3b2f12", "#ffd27a"),
        ("#4b235f", "#db9bff"),
    ]
    strategy_names = list(registry.strategy_names)
    if strategy_name in strategy_names:
        return fallback_cycle[strategy_names.index(strategy_name) % len(fallback_cycle)]
    return ("#24303a", "#dce4ef")


def strategy_empty_hint(text: str) -> str:
    registry = get_strategy_registry()
    strategy_name = registry.canonical_strategy_name(str(text or "").strip()) or str(text or "").strip()
    return strategy_empty_hint_meta(strategy_name)


def signal_badge_palette(text: str) -> tuple[str, str]:
    mapping = {
        "回补做多": ("#153b23", "#56f0a3"),
        "观察": ("#4b3a14", "#ffd971"),
        "诱多陷阱": ("#5a1016", "#ff7a7a"),
        "无信号": ("#26333d", "#b9c3d0"),
        "BUY": ("#153b23", "#56f0a3"),
        "WATCH": ("#4b3a14", "#ffd971"),
    }
    return mapping.get(text, ("#24303a", "#dce4ef"))


def display_order_status(value: str) -> str:
    return DISPLAY_TEXT["order_status"].get(value, value)


def display_fill_status(value: str) -> str:
    return DISPLAY_TEXT["fill_status"].get(value, value)


def display_action(value: str) -> str:
    if value == "REDUCE":
        return "减仓"
    return DISPLAY_TEXT["action"].get(value, value)


def display_label(value: str) -> str:
    return DISPLAY_TEXT["label"].get(value, value)


def display_mode(value: str) -> str:
    return DISPLAY_TEXT["mode"].get(value, value)


def display_leader_level(value: str) -> str:
    return {
        "CORE_LEADER": "核心龙头",
        "ACTIVE_LEADER": "活跃龙头",
        "FOLLOWER": "跟风股",
        "NOISE": "噪声",
        "": "未分类",
    }.get(value, value)
