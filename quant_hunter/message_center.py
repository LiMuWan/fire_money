from __future__ import annotations

from dataclasses import dataclass

MESSAGE_CENTER_MAX_EVENTS = 120

_CATEGORY_LABELS = {
    "all": "全部",
    "ai": "AI",
    "news": "消息",
    "trade": "交易",
    "system": "系统",
}

_LEVEL_LABELS = {
    "INFO": "进行中",
    "SUCCESS": "完成",
    "WARN": "提示",
    "ERROR": "异常",
}

_TONE_BY_LEVEL = {
    "INFO": "idle",
    "SUCCESS": "buy",
    "WARN": "watch",
    "ERROR": "risk",
}

_MESSAGE_CENTER_BUTTON_LABELS = {
    "clear": "清空事件",
    "mark_all_read": "全标已读",
    "clear_handled": "清已处理",
    "mark_read": "标已读",
    "mark_handled": "标已处理",
    "symbol": "定位焦点",
    "open": "看链路",
}

_MESSAGE_CENTER_METRIC_ACCENTS = {
    "unread": "待看新事件",
    "open": "等待落地的处理动作",
    "ai": "AI 评测与重试链路",
    "news": "消息源刷新与催化联动",
    "trade": "委托回执与执行反馈",
}

_MESSAGE_CENTER_METRIC_TOOLTIPS = {
    "unread": "点击后切到未读优先排序。",
    "open": "点击后只看未处理事件。",
    "ai": "点击后只看 AI 评测事件。",
    "news": "点击后只看消息事件。",
    "trade": "点击后只看交易事件。",
}


@dataclass(frozen=True)
class SmartMessageEvent:
    timestamp: str
    category: str
    title: str
    detail: str = ""
    symbol: str = ""
    level: str = "INFO"
    is_read: bool = False
    is_handled: bool = False


@dataclass(frozen=True)
class MessageActionHint:
    button_label: str
    summary: str


def message_center_button_label(key: str, fallback: str = "") -> str:
    return str(_MESSAGE_CENTER_BUTTON_LABELS.get(str(key or "").strip(), fallback) or fallback)


def message_center_metric_accent(key: str, fallback: str = "") -> str:
    return str(_MESSAGE_CENTER_METRIC_ACCENTS.get(str(key or "").strip(), fallback) or fallback)


def message_center_metric_tooltip(key: str, fallback: str = "") -> str:
    return str(_MESSAGE_CENTER_METRIC_TOOLTIPS.get(str(key or "").strip(), fallback) or fallback)


def normalize_message_category(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _CATEGORY_LABELS and normalized != "all" else "system"


def normalize_message_filter(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _CATEGORY_LABELS else "all"


def normalize_message_sort_mode(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in {"latest", "unread", "open", "priority"} else "latest"


def normalize_message_level(value: str) -> str:
    return str(value or "INFO").strip().upper() or "INFO"


def normalize_message_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "y", "on", "已读", "已处理"}


def message_category_label(value: str) -> str:
    return _CATEGORY_LABELS.get(normalize_message_category(value), "系统")


def message_level_label(value: str) -> str:
    return _LEVEL_LABELS.get(normalize_message_level(value), normalize_message_level(value))


def message_level_tone(value: str) -> str:
    return _TONE_BY_LEVEL.get(normalize_message_level(value), "idle")


def message_event_signature(event: SmartMessageEvent) -> tuple[str, str, str, str, str, str]:
    return (
        str(getattr(event, "timestamp", "") or ""),
        str(getattr(event, "category", "") or ""),
        str(getattr(event, "title", "") or ""),
        str(getattr(event, "detail", "") or ""),
        str(getattr(event, "symbol", "") or ""),
        str(getattr(event, "level", "") or ""),
    )


def message_event_status_label(event: SmartMessageEvent | None) -> str:
    if event is None:
        return "无事件"
    read_text = "已读" if bool(getattr(event, "is_read", False)) else "未读"
    handled_text = "已处理" if bool(getattr(event, "is_handled", False)) else "未处理"
    return f"{read_text} / {handled_text}"


def message_center_badge_text(counts: dict[str, int] | None) -> str:
    stats = dict(counts or {})
    return f"状态：待处理 {int(stats.get('open', 0) or 0)} | 未读 {int(stats.get('unread', 0) or 0)}"


def message_center_summary_text(headline: str, detail: str) -> str:
    lead = str(headline or "").strip() or "等待新事件"
    tail = str(detail or "").strip()
    return f"消息中控：{lead} | {tail}" if tail else f"消息中控：{lead}"


def message_center_action_bar_text(event: SmartMessageEvent | None, action_hint: MessageActionHint | None = None) -> str:
    hint = action_hint or message_event_action_hint(event)
    if event is None:
        return "事件动作：先选中一条事件，再决定定位焦点、看链路或标记处理。 | 处理进度：未选中"
    return f"事件动作：{hint.summary} | 处理进度：{message_event_status_label(event)}"


def build_message_center_event_detail(
    event: SmartMessageEvent | None,
    *,
    action_hint: MessageActionHint | None = None,
    route_label: str = "",
    route_workspace: str = "",
    route_widget: str = "",
) -> str:
    if event is None:
        return build_message_center_snapshot([], category_filter="all")["text"]

    hint = action_hint or message_event_action_hint(event)
    symbol = str(getattr(event, "symbol", "") or "").strip()
    detail = str(getattr(event, "detail", "") or "").strip() or "暂无附加说明"
    lines = [
        "事件详情",
        f"时间：{getattr(event, 'timestamp', '') or '--:--:--'}",
        f"分类：{message_category_label(getattr(event, 'category', 'system'))}",
        f"事件级别：{message_level_label(getattr(event, 'level', 'INFO'))}",
        f"处理进度：{message_event_status_label(event)}",
        f"焦点标的：{symbol or '无'}",
        f"终端动作：{hint.button_label}",
        "",
        f"标题：{getattr(event, 'title', '') or '未命名事件'}",
        f"摘要：{detail}",
        "",
        f"下一步：{hint.summary}",
        f"联动路径：{route_label or '看关联页'} -> {route_workspace or '--'}/{route_widget or '--'}",
    ]
    return "\n".join(lines)


def message_event_action_hint(event: SmartMessageEvent | None) -> MessageActionHint:
    if event is None:
        return MessageActionHint("看机会", "去机会池看最新焦点和执行链路。")

    category = normalize_message_category(getattr(event, "category", "system"))
    title = str(getattr(event, "title", "") or "").strip()
    detail = str(getattr(event, "detail", "") or "").strip()
    level = normalize_message_level(getattr(event, "level", "INFO"))
    symbol = str(getattr(event, "symbol", "") or "").strip()
    is_handled = bool(getattr(event, "is_handled", False))

    if is_handled:
        if symbol:
            return MessageActionHint("看关联票", "这条事件已经处理完成，去关联股票继续跟踪。")
        return MessageActionHint("看机会", "这条事件已经处理完成，去机会池看当前主线和焦点。")

    if category == "trade":
        if level == "ERROR":
            return MessageActionHint("去交易盯回执", "先看失败原因、回执和回退结果，再决定是否重试。")
        return MessageActionHint("去交易盯回执", "先核对提交结果、成交状态和执行偏差。")

    if category == "news":
        if level == "ERROR":
            return MessageActionHint("去配置看消息源", "先查消息源配置、文件路径或网络，再重载。")
        if symbol:
            return MessageActionHint("去机会池复核", "结合最新消息，复核这只股票的主线、催化和执行窗口。")
        return MessageActionHint("去配置看消息源", "看消息源状态和最近一次载入结果。")

    if category == "ai":
        if level == "ERROR":
            if any(token in detail.lower() for token in ("api key", "unauthorized", "401", "403", "invalid_api_key")):
                return MessageActionHint("去配置补 Key", "先检查 API Key、模型和网络，再重新发起 AI 评测。")
            return MessageActionHint("去机会池重评", "先看失败原因，再去机会池重评。")
        if level == "INFO":
            return MessageActionHint("去机会池看评测", "当前焦点正在生成评测，先看流式内容和上下文。")
        return MessageActionHint("去机会池看评测结果", "看 AI 评测结论、价格计划和下一步。")

    if "AI评测配置" in title:
        return MessageActionHint("去配置看设置", "确认模型、Key 和自动重评开关是否符合当前使用方式。")

    if "推荐池已刷新" in title or "机会池已刷新" in title:
        if symbol:
            return MessageActionHint("去机会池复核新焦点", "先看新焦点股票的主线、风险灯和催化。")
        return MessageActionHint("去机会池看排序", "看新的机会池排序、主线变化和执行候选。")

    if symbol:
        return MessageActionHint("去机会池定位股票", "围绕这只股票继续处理机会、复盘或执行链路。")
    return MessageActionHint("看机会", "去机会池看最新状态。")


def append_message_event(
    events: list[SmartMessageEvent] | None,
    *,
    timestamp: str,
    category: str,
    title: str,
    detail: str = "",
    symbol: str = "",
    level: str = "INFO",
    max_events: int = MESSAGE_CENTER_MAX_EVENTS,
) -> list[SmartMessageEvent]:
    items = list(events or [])
    items.append(
        SmartMessageEvent(
            timestamp=str(timestamp or "").strip(),
            category=normalize_message_category(category),
            title=str(title or "").strip() or "未命名事件",
            detail=str(detail or "").strip(),
            symbol=str(symbol or "").strip(),
            level=normalize_message_level(level),
            is_read=False,
            is_handled=False,
        )
    )
    return items[-max(1, int(max_events or MESSAGE_CENTER_MAX_EVENTS)) :]


def update_message_event_flags(
    events: list[SmartMessageEvent] | None,
    *,
    target_signature: tuple[str, str, str, str, str, str] | None,
    is_read: bool | None = None,
    is_handled: bool | None = None,
) -> list[SmartMessageEvent]:
    items = list(events or [])
    if target_signature is None:
        return items
    updated: list[SmartMessageEvent] = []
    for item in items:
        if message_event_signature(item) != target_signature:
            updated.append(item)
            continue
        updated.append(
            SmartMessageEvent(
                timestamp=item.timestamp,
                category=item.category,
                title=item.title,
                detail=item.detail,
                symbol=item.symbol,
                level=item.level,
                is_read=item.is_read if is_read is None else bool(is_read),
                is_handled=item.is_handled if is_handled is None else bool(is_handled),
            )
        )
    return updated


def remove_handled_message_events(events: list[SmartMessageEvent] | None) -> list[SmartMessageEvent]:
    return [item for item in list(events or []) if not bool(getattr(item, "is_handled", False))]


def mark_all_message_events_read(events: list[SmartMessageEvent] | None) -> list[SmartMessageEvent]:
    updated: list[SmartMessageEvent] = []
    for item in list(events or []):
        if bool(getattr(item, "is_read", False)):
            updated.append(item)
            continue
        updated.append(
            SmartMessageEvent(
                timestamp=item.timestamp,
                category=item.category,
                title=item.title,
                detail=item.detail,
                symbol=item.symbol,
                level=item.level,
                is_read=True,
                is_handled=item.is_handled,
            )
        )
    return updated


def sort_message_events(events: list[SmartMessageEvent] | None, *, mode: str = "latest") -> list[SmartMessageEvent]:
    items = list(events or [])
    sort_mode = normalize_message_sort_mode(mode)
    level_priority = {"ERROR": 0, "WARN": 1, "INFO": 2, "SUCCESS": 3}

    indexed = list(enumerate(items))

    def base_key(index: int, item: SmartMessageEvent) -> tuple[int]:
        return (-index,)

    def unread_key(index: int, item: SmartMessageEvent) -> tuple[bool, int]:
        return (bool(getattr(item, "is_read", False)), -index)

    def open_key(index: int, item: SmartMessageEvent) -> tuple[bool, int]:
        return (bool(getattr(item, "is_handled", False)), -index)

    def priority_key(index: int, item: SmartMessageEvent) -> tuple[int, bool, bool, int]:
        level = normalize_message_level(getattr(item, "level", "INFO"))
        return (
            level_priority.get(level, 9),
            bool(getattr(item, "is_handled", False)),
            bool(getattr(item, "is_read", False)),
            -index,
        )

    key_fn = {
        "latest": lambda pair: base_key(pair[0], pair[1]),
        "unread": lambda pair: unread_key(pair[0], pair[1]),
        "open": lambda pair: open_key(pair[0], pair[1]),
        "priority": lambda pair: priority_key(pair[0], pair[1]),
    }[sort_mode]

    indexed.sort(key=key_fn)
    return [item for _index, item in indexed]


def message_center_counts(events: list[SmartMessageEvent] | None) -> dict[str, int]:
    counts = {"all": 0, "ai": 0, "news": 0, "trade": 0, "system": 0, "unread": 0, "open": 0}
    for item in list(events or []):
        category = normalize_message_category(getattr(item, "category", "system"))
        counts["all"] += 1
        counts[category] += 1
        if not bool(getattr(item, "is_read", False)):
            counts["unread"] += 1
        if not bool(getattr(item, "is_handled", False)):
            counts["open"] += 1
    return counts


def build_message_center_snapshot(
    events: list[SmartMessageEvent] | None,
    *,
    category_filter: str = "all",
    limit: int = 18,
) -> dict[str, str]:
    filter_key = normalize_message_filter(category_filter)
    counts = message_center_counts(events)
    filtered = [
        item
        for item in list(events or [])
        if filter_key == "all" or normalize_message_category(getattr(item, "category", "system")) == filter_key
    ]
    visible = filtered[-max(1, int(limit or 18)) :]

    lines = [
        "统一消息中心",
        f"- 当前视角：{_CATEGORY_LABELS.get(filter_key, '全部')}",
        (
            f"- 状态总览：待处理 {counts['open']} | 未读 {counts['unread']} | "
            f"AI {counts['ai']} | 消息 {counts['news']} | 交易 {counts['trade']} | 系统 {counts['system']}"
        ),
    ]
    if not visible:
        lines.extend(
            [
                "",
                "当前状态：等待新事件写入。",
                "来源：AI 评测、消息源刷新、机会池刷新和交易回执会汇总到这里。",
                "下一步：先刷新市场、机会池或交易链路，再回来看这里的最新事件。",
            ]
        )
        return {
            "headline": "等待新事件",
            "detail": "AI / 消息 / 交易写入后会汇总到这里",
            "text": "\n".join(lines),
        }

    for item in reversed(visible):
        category = normalize_message_category(getattr(item, "category", "system"))
        level = normalize_message_level(getattr(item, "level", "INFO"))
        stock_hint = f" | {item.symbol}" if getattr(item, "symbol", "") else ""
        lines.append(
            f"[{getattr(item, 'timestamp', '') or '--:--:--'}] "
            f"[{_CATEGORY_LABELS.get(category, '系统')}/{_LEVEL_LABELS.get(level, level)}] "
            f"{getattr(item, 'title', '') or '未命名事件'}{stock_hint} | {message_event_status_label(item)}"
        )
        detail = str(getattr(item, "detail", "") or "").strip()
        if detail:
            lines.append(f"  摘要：{detail}")

    latest = visible[-1]
    action_hint = message_event_action_hint(latest)
    headline = (
        f"{_CATEGORY_LABELS.get(normalize_message_category(latest.category), '系统')} / "
        f"{_LEVEL_LABELS.get(normalize_message_level(latest.level), '进行中')}"
    )
    detail = f"{str(getattr(latest, 'title', '') or '最新事件')} | {action_hint.button_label}"
    return {
        "headline": headline,
        "detail": detail,
        "text": "\n".join(lines),
    }
