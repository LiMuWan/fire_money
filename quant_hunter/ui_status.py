from __future__ import annotations

try:
    from PySide6.QtGui import QColor
except ModuleNotFoundError:  # pragma: no cover - enables non-Qt test environments
    class QColor:  # type: ignore[override]
        def __init__(self, value: str) -> None:
            self.value = value

from .ui_config import DISPLAY_TEXT


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
    order_status = item.get("order_status", "")
    fill_status = item.get("fill_status", "")
    if order_status == "FAILED" or fill_status == "REJECTED":
        return QColor("#FBEAEA"), QColor("#842029")
    if fill_status == "PENDING":
        return QColor("#FFF4DB"), QColor("#7C4A03")
    if order_status == "SUBMITTED":
        return QColor("#E7F1FF"), QColor("#084298")
    if fill_status == "FILLED":
        return QColor("#E8F7EC"), QColor("#0F5132")
    return QColor("#F8F9FA"), QColor("#212529")


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
    mapping = {
        "龙头模型": ("#5b1216", "#ff6a6f"),
        "主力雷达": ("#0f3951", "#7ed7ff"),
        "擒龙打板": ("#57430f", "#ffd75b"),
        "价值低吸": ("#204728", "#7ef5a2"),
        "掘龙决策": ("#4b235f", "#db9bff"),
    }
    return mapping.get(text, ("#24303a", "#dce4ef"))


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
