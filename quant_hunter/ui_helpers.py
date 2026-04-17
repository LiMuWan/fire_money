from __future__ import annotations

from datetime import date, datetime, time as datetime_time


def _workspace_hero_tone(eyebrow: str, title: str) -> str:
    combined = f"{eyebrow} {title}"
    if any(token in combined for token in ("市场", "总览", "驾驶舱")):
        return "overview"
    if any(token in combined for token in ("推荐", "机会")):
        return "recommend"
    if any(token in combined for token in ("交易", "执行")):
        return "broker"
    if any(token in combined for token in ("复盘", "明细")):
        return "detail"
    if any(token in combined for token in ("扫描", "观察")):
        return "scanner"
    if any(token in combined for token in ("登录", "账户")):
        return "auth"
    if any(token in combined for token in ("配置", "系统")):
        return "config"
    if any(token in combined for token in ("打板", "监控")):
        return "board"
    return "default"


def _workspace_hero_stamp(hero_tone: str) -> str:
    return {
        "overview": "MARKET CORE",
        "recommend": "ALPHA FLOW",
        "broker": "EXECUTION CORE",
        "detail": "REVIEW LAB",
        "scanner": "LIVE SCAN",
        "auth": "ACCESS LAYER",
        "config": "SYSTEM LAB",
        "board": "BOARD WATCH",
    }.get(hero_tone, "QH PRO")

try:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QFrame, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover - enables pure-logic imports without Qt runtime
    class _QtStub:
        def __init__(self, *args, **kwargs) -> None:
            self._text = str(args[0]) if args else ""
            self._tooltip = ""

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

        def style(self):
            return self

        def text(self) -> str:
            return self._text

        def setText(self, value: str) -> None:
            self._text = str(value)

        def toolTip(self) -> str:
            return self._tooltip

        def setToolTip(self, value: str) -> None:
            self._tooltip = str(value)

        def toPlainText(self) -> str:
            return self._text

        def setPlainText(self, value: str) -> None:
            self._text = str(value)

        def rowCount(self) -> int:
            return 0

        def verticalScrollBar(self):
            return None

    class QTimer:  # type: ignore[override]
        @staticmethod
        def singleShot(_msec: int, callback) -> None:
            if callable(callback):
                callback()

    class QColor:  # type: ignore[override]
        def __init__(self, value="") -> None:
            self.value = value

    class QWidget(_QtStub):  # type: ignore[override]
        pass

    class QFrame(QWidget):  # type: ignore[override]
        pass

    class QGroupBox(QWidget):  # type: ignore[override]
        pass

    class QLabel(QWidget):  # type: ignore[override]
        pass

    class QPushButton(QWidget):  # type: ignore[override]
        pass

    class QTextEdit(QWidget):  # type: ignore[override]
        pass

    class QHBoxLayout(_QtStub):  # type: ignore[override]
        pass

    class QVBoxLayout(_QtStub):  # type: ignore[override]
        pass


def build_workspace_badge(value: str, caption: str, hero_tone: str = "default") -> QFrame:
    frame = QFrame()
    frame.setObjectName("workspaceBadge")
    frame.setProperty("heroTone", hero_tone)
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(14, 10, 14, 10)
    layout.setSpacing(3)

    value_label = QLabel(value)
    value_label.setObjectName("workspaceBadgeValue")
    value_label.setProperty("heroTone", hero_tone)
    value_label.setWordWrap(True)
    caption_label = QLabel(caption)
    caption_label.setObjectName("workspaceBadgeCaption")
    caption_label.setProperty("heroTone", hero_tone)
    caption_label.setWordWrap(True)

    layout.addWidget(value_label)
    layout.addWidget(caption_label)
    frame.setMinimumWidth(100)
    return frame


def build_workspace_hero(
    eyebrow: str,
    title: str,
    subtitle: str,
    badges: list[tuple[str, str]] | None = None,
) -> QFrame:
    hero_tone = _workspace_hero_tone(eyebrow, title)
    frame = QFrame()
    frame.setObjectName("workspaceHero")
    frame.setProperty("heroTone", hero_tone)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(18, 14, 18, 14)
    layout.setSpacing(14)

    accent_strip = QFrame()
    accent_strip.setObjectName("workspaceHeroAccent")
    accent_strip.setProperty("heroTone", hero_tone)
    accent_strip.setFixedWidth(4)
    layout.addWidget(accent_strip)

    text_layout = QVBoxLayout()
    text_layout.setSpacing(6)

    top_row = QHBoxLayout()
    top_row.setContentsMargins(0, 0, 0, 0)
    top_row.setSpacing(8)

    eyebrow_label = QLabel(eyebrow)
    eyebrow_label.setObjectName("workspaceEyebrow")
    eyebrow_label.setWordWrap(True)
    top_row.addWidget(eyebrow_label)

    stamp_label = QLabel(_workspace_hero_stamp(hero_tone))
    stamp_label.setObjectName("workspaceHeroStamp")
    stamp_label.setProperty("heroTone", hero_tone)
    top_row.addWidget(stamp_label)
    top_row.addStretch(1)
    text_layout.addLayout(top_row)

    title_label = QLabel(title)
    title_label.setObjectName("workspaceTitle")
    title_label.setWordWrap(True)
    text_layout.addWidget(title_label)

    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("workspaceSubtitle")
    subtitle_label.setWordWrap(True)
    text_layout.addWidget(subtitle_label)

    layout.addLayout(text_layout, stretch=1)

    if badges:
        badge_rail = QFrame()
        badge_rail.setObjectName("workspaceBadgeRail")
        badge_rail.setProperty("heroTone", hero_tone)
        badge_row = QHBoxLayout()
        badge_row.setContentsMargins(6, 4, 6, 4)
        badge_row.setSpacing(8)
        for value, caption in badges:
            badge_row.addWidget(build_workspace_badge(value, caption, hero_tone))
        badge_row.addStretch(1)
        badge_rail.setLayout(badge_row)
        layout.addWidget(badge_rail, stretch=0)

    return frame


def set_button_role(button: QPushButton, role: str = "ghost") -> None:
    if role == "accent":
        object_name = "accentButton"
    elif role == "tonal":
        object_name = "tonalButton"
    else:
        object_name = "ghostButton"
    button.setObjectName(object_name)
    button.style().unpolish(button)
    button.style().polish(button)


def style_terminal_panel(*boxes: QGroupBox) -> None:
    for box in boxes:
        if not (box.objectName() or "").strip():
            box.setObjectName("terminalPanel")
        box.setProperty("terminalPanel", True)


def style_terminal_console(*widgets: QTextEdit) -> None:
    for widget in widgets:
        widget.setObjectName("terminalConsole")


def build_overview_outline_style(accent: str) -> str:
    return (
        "QPushButton {"
        f"border: 1px solid {accent}; color: {accent}; padding: 10px 16px; border-radius: 12px;"
        "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 24, 33, 0.96), stop:1 rgba(13, 18, 26, 0.96));"
        "font-weight: 800; min-height: 20px; }"
        "QPushButton:hover { background: rgba(255,255,255,0.08); border-color: #dcecff; }"
        "QPushButton:checked { background: rgba(56,88,122,0.96); color:#f7fbff; border-color:#dcecff; }"
    )


def build_overview_filled_style(accent: str) -> str:
    return (
        "QPushButton {"
        f"border: 1px solid {accent}; color: #f7fbff; padding: 10px 18px; border-radius: 12px;"
        f"background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {accent}, stop:1 #7fc8ff);"
        "font-weight: 800; min-height: 22px; }"
        "QPushButton:hover { border-color: #f4fbff; }"
        "QPushButton:checked { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2487c2, stop:1 #52c4ef); color:#f7fbff; border-color: #b6eeff; }"
    )


def build_stock_identity_cell(row) -> QWidget:
    wrapper = QWidget()
    layout = QVBoxLayout(wrapper)
    layout.setContentsMargins(8, 4, 8, 4)
    layout.setSpacing(2)

    header_row = QWidget()
    header_layout = QHBoxLayout(header_row)
    header_layout.setContentsMargins(0, 0, 0, 0)
    header_layout.setSpacing(6)

    name_label = QLabel(row.stock_name)
    name_label.setStyleSheet("QLabel { color: #f3f5f7; font-weight: 800; font-size: 14px; }")
    header_layout.addWidget(name_label)
    identity_badge = getattr(row, "identity_badge", "") or ""
    if identity_badge:
        badge_bg = getattr(row, "identity_badge_bg", "#1b2633")
        badge_fg = getattr(row, "identity_badge_fg", "#8fc7ff")
        badge_label = QLabel(identity_badge)
        badge_label.setStyleSheet(
            "QLabel {"
            f"background: {badge_bg}; color: {badge_fg}; border: 1px solid {badge_fg};"
            "border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: 800; }"
        )
        header_layout.addWidget(badge_label)
    header_layout.addStretch(1)
    meta_label = QLabel(f"{row.stock_id}  |  {row.symbol}  |  热度 {row.heat_score:.1f}")
    meta_label.setStyleSheet("QLabel { color: #8793a6; font-size: 11px; }")

    layout.addWidget(header_row)
    layout.addWidget(meta_label)
    return wrapper


def create_metric_card(title: str, value: str, accent: str) -> tuple[QFrame, QLabel, QLabel]:
    card = QFrame()
    card.setObjectName("metricCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(4)

    title_label = QLabel(title)
    title_label.setObjectName("metricCaption")
    value_label = QLabel(value)
    value_label.setObjectName("metricValue")
    accent_label = QLabel(accent)
    accent_label.setObjectName("metricAccent")

    layout.addWidget(title_label)
    layout.addWidget(value_label)
    layout.addWidget(accent_label)
    layout.addStretch(1)
    return card, value_label, accent_label


def build_badge_strip(badges: list[tuple[str, str, str]]) -> QWidget:
    wrapper = QWidget()
    layout = QHBoxLayout(wrapper)
    layout.setContentsMargins(4, 2, 4, 2)
    layout.setSpacing(4)
    for text, bg, fg in badges:
        if not text:
            continue
        badge = QLabel(text)
        badge.setStyleSheet(
            "QLabel {"
            f"background: {bg}; color: {fg}; border: 1px solid {fg};"
            "padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }"
        )
        layout.addWidget(badge)
    layout.addStretch(1)
    return wrapper


def create_shell_chip(label: str, value: str) -> dict[str, object]:
    frame = QFrame()
    frame.setObjectName("shellChip")
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(11, 7, 11, 7)
    layout.setSpacing(2)
    frame.setMinimumHeight(42)
    label_widget = QLabel(label)
    label_widget.setObjectName("shellChipLabel")
    label_widget.setWordWrap(False)
    value_widget = QLabel(value)
    value_widget.setObjectName("shellChipValue")
    value_widget.setWordWrap(True)
    value_widget.setMinimumHeight(18)
    frame.setToolTip(value)
    value_widget.setToolTip(value)
    layout.addWidget(label_widget)
    layout.addWidget(value_widget)
    return {"frame": frame, "label": label_widget, "value": value_widget}


def set_shell_chip(chip: dict[str, object] | None, value: str) -> None:
    if not chip:
        return
    widget = chip.get("value")
    frame = chip.get("frame")
    if isinstance(widget, QLabel):
        widget.setText(value)
        widget.setToolTip(value)
    if isinstance(frame, QFrame):
        frame.setToolTip(value)


def _clean_copy(value: object) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def _compact_copy(value: object, limit: int) -> str:
    text = _clean_copy(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def news_source_tier(source: str) -> str:
    normalized = _clean_copy(source).lower()
    if not normalized:
        return "B级"
    if any(token in normalized for token in ("巨潮", "cninfo", "上交所", "深交所", "公告", "互动易", "e互动", "公司公告")):
        return "A级"
    if any(token in normalized for token in ("股吧", "雪球", "微博", "论坛", "传闻", "社群", "自媒体", "小作文")):
        return "C级"
    if any(
        token in normalized
        for token in ("财联社", "证券时报", "上证报", "中证报", "东方财富", "同花顺", "界面", "wind", "choice")
    ):
        return "B级"
    return "B级"


def news_source_visual_label(source: str) -> str:
    tier = news_source_tier(source)
    return {
        "A级": "已公告",
        "B级": "媒体催化",
        "C级": "传闻线索",
    }.get(tier, "消息线索")


def news_source_visual_tone(source: str) -> str:
    tier = news_source_tier(source)
    return {
        "A级": "buy",
        "B级": "watch",
        "C级": "risk",
    }.get(tier, "watch")


def news_confidence_label(news_items: list[object] | tuple[object, ...] | None) -> str:
    if not news_items:
        return "可信度 待确认"
    source = _clean_copy(getattr(news_items[0], "source", ""))
    return f"可信度 {news_source_tier(source)}"


def build_news_digest_lines(news_items: list[object] | tuple[object, ...] | None, limit: int = 2) -> list[str]:
    if not news_items:
        return []
    lines: list[str] = []
    for item in list(news_items)[: max(0, limit)]:
        title = _clean_copy(getattr(item, "title", "")) or "消息标题未填写"
        source = _clean_copy(getattr(item, "source", "")) or "来源未知"
        published = _clean_copy(getattr(item, "published_at", ""))
        tier = news_source_tier(source)
        visual = news_source_visual_label(source)
        meta = " / ".join(part for part in (source, published, f"可信度 {tier}") if part)
        lines.append(f"- [{visual}] {title}{f' ({meta})' if meta else ''}")
        summary = _clean_copy(getattr(item, "summary", ""))
        if summary:
            lines.append(f"  {_compact_copy(summary, 42)}")
    return lines


def build_hype_logic_summary(
    *,
    theme_name: str = "",
    catalyst: str = "",
    rationale: str = "",
    profile_notes: str = "",
    scan_reason: str = "",
    news_title: str = "",
) -> str:
    trigger = _clean_copy(catalyst) or _clean_copy(news_title)
    thesis = _clean_copy(rationale) or _clean_copy(profile_notes) or _clean_copy(scan_reason)
    theme = _clean_copy(theme_name)
    parts: list[str] = []
    if trigger:
        parts.append(_compact_copy(trigger, 18))
    if theme and theme not in "".join(parts):
        parts.append(_compact_copy(theme, 10))
    if thesis and thesis not in "".join(parts):
        parts.append(_compact_copy(thesis, 24))
    if not parts:
        return "等待逻辑生成"
    return " -> ".join(parts)


def build_hype_logic_lines(
    *,
    theme_name: str = "",
    catalyst: str = "",
    rationale: str = "",
    profile_notes: str = "",
    scan_reason: str = "",
    news_title: str = "",
    next_focus: str = "",
    risk_flag: str = "",
    confidence_label: str = "",
) -> list[str]:
    logic_summary = build_hype_logic_summary(
        theme_name=theme_name,
        catalyst=catalyst,
        rationale=rationale,
        profile_notes=profile_notes,
        scan_reason=scan_reason,
        news_title=news_title,
    )
    watch_text = _compact_copy(next_focus, 30) or "继续盯量能、承接和主线延续"
    risk_text = _compact_copy(risk_flag, 10) or "待评估"
    confidence_text = _clean_copy(confidence_label) or "可信度 待确认"
    return [
        f"炒作逻辑：{logic_summary}",
        f"验证焦点：{watch_text}",
        f"风险/可信度：{risk_text} | {confidence_text}",
    ]


def recommendation_focus_lines(row) -> list[str]:
    if row is None:
        return ["等待推荐池刷新。"]
    entry_price = float(getattr(row, "entry_price", 0.0) or getattr(row, "close", 0.0) or 0.0)
    stop_price = float(getattr(row, "stop_price", 0.0) or 0.0)
    target_price = float(getattr(row, "target_price", 0.0) or 0.0)
    lines = [
        f"机会分层：{getattr(row, 'opportunity_tier', '') or '待观察'}",
        (
            f"主线 {getattr(row, 'mainline_tag', '') or getattr(row, 'theme_name', '') or '待确认'} | "
            f"窗口 {float(getattr(row, 'mainline_window_score', 0.0) or 0.0):.1f} | "
            f"风险 {getattr(row, 'mainline_risk_flag', '--')}"
        ),
        (
            f"置信 {float(getattr(row, 'confidence_score', 0.0) or 0.0):.1f} | "
            f"执行准备 {float(getattr(row, 'execution_readiness', 0.0) or 0.0):.1f} | "
            f"时效 {float(getattr(row, 'timeliness_score', 0.0) or 0.0):.1f}"
        ),
    ]
    if entry_price > 0 or stop_price > 0 or target_price > 0:
        entry_text = f"{entry_price:.2f}" if entry_price > 0 else "--"
        stop_text = f"{stop_price:.2f}" if stop_price > 0 else "--"
        target_text = f"{target_price:.2f}" if target_price > 0 else "--"
        lines.append(f"价格计划：入场 {entry_text} | 止损 {stop_text} | 目标 {target_text}")
    reject_reason = str(getattr(row, "reject_reason", "") or "").strip()
    next_focus = str(getattr(row, "next_focus", "") or "").strip()
    invalidation_reason = str(getattr(row, "invalidation_reason", "") or "").strip()
    one_day_grade = one_day_hold_grade(row)
    if one_day_grade:
        lines.append(f"隔日博弈等级：{one_day_grade}")
    tripwire_metrics = one_day_hold_tripwire_metrics(row)
    if tripwire_metrics:
        focus_metric = max(tripwire_metrics, key=lambda item: item[1])
        lines.append(f"执行窗口：{focus_metric[0]} {focus_metric[1]:.1f} / 100 | {focus_metric[2]}")
    if reject_reason:
        lines.append(f"暂不执行原因：{reject_reason}")
    if next_focus:
        lines.append(f"下一步：{next_focus}")
    discipline = trade_plan_execution_hint(row, row)
    if discipline and discipline != next_focus:
        lines.append(f"交易纪律：{discipline}")
    if invalidation_reason:
        lines.append(f"失效条件：{invalidation_reason}")
    return lines


def trade_decision_focus_lines(decision, recommendation=None) -> list[str]:
    if decision is None:
        return ["当前没有交易计划。"]
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    lines = [
        f"机会分层：{getattr(decision, 'opportunity_tier', '') or getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
        f"计划买点 {float(getattr(decision, 'planned_entry', 0.0) or 0.0):.2f} | 止损 {float(getattr(decision, 'planned_stop', 0.0) or 0.0):.2f} | 目标 {float(getattr(decision, 'planned_target', 0.0) or 0.0):.2f}",
        f"建议资金 {float(getattr(decision, 'suggested_budget', 0.0) or 0.0):,.0f} | 置信度 {float(getattr(decision, 'confidence', 0.0) or 0.0):.0%} | 执行准备 {float(getattr(decision, 'execution_readiness', 0.0) or 0.0):.1f}",
    ]
    if strategy_name == "尾盘买入法":
        lines.append("尾盘节奏：只等尾盘回流确认，隔夜后次日开盘优先卖，不做盘中拖仓。")
    elif strategy_name == "一日持股法":
        lines.append("一日节奏：先看竞价和开盘承接，冲高先兑现，午后不转强不拖仓。")
    next_focus = str(getattr(decision, "next_focus", "") or getattr(recommendation, "next_focus", "") or "").strip()
    if next_focus:
        lines.append(f"执行前再看一眼：{next_focus}")
    return lines


def trade_plan_execution_hint(decision, recommendation=None) -> str:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    action = str(getattr(decision, "action", "") or "").upper()
    next_focus = str(getattr(decision, "next_focus", "") or getattr(recommendation, "next_focus", "") or "").strip()
    if strategy_name == "尾盘买入法":
        if action == "BUY":
            return "只在 14:30 后确认尾盘回流再上，次日开盘优先兑现。"
        return "先看尾盘承接和次日开盘强弱，再决定是否继续隔夜博弈。"
    if strategy_name == "一日持股法":
        if action == "BUY":
            return "竞价转强才跟，冲高先兑现，午后不转强就走。"
        return "先看竞价和开盘承接，再决定是否继续隔日博弈。"
    if next_focus:
        return next_focus
    if action == "BUY":
        return "先核对主线、量能和风险灯，再决定是否执行。"
    if action == "WATCH":
        return "保持观察，等确认后再动。"
    return "优先处理风险，再看是否需要调仓。"


def one_day_hold_grade(recommendation) -> str:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name not in {"一日持股法", "尾盘买入法"}:
        return ""
    score = float(
        getattr(recommendation, "tail_buy_score", 0.0) or 0.0
        if strategy_name == "尾盘买入法"
        else getattr(recommendation, "one_day_hold_score", 0.0) or 0.0
    )
    readiness = float(getattr(recommendation, "execution_readiness", 0.0) or 0.0)
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
    if score >= 86.0 and readiness >= 78.0 and risk_flag != "高":
        return "强博弈"
    if score >= 76.0 and readiness >= 68.0 and risk_flag != "高":
        return "轻试仓"
    return "只观察"


def one_day_hold_tripwire_metrics(recommendation) -> list[tuple[str, float, str]]:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name not in {"一日持股法", "尾盘买入法"}:
        return []
    score = float(
        getattr(recommendation, "tail_buy_score", 0.0) or 0.0
        if strategy_name == "尾盘买入法"
        else getattr(recommendation, "one_day_hold_score", 0.0) or 0.0
    )
    readiness = float(getattr(recommendation, "execution_readiness", 0.0) or 0.0)
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    continuation = float(getattr(recommendation, "mainline_continuation_score", 0.0) or window_score or 0.0)
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
    risk_adjust = {"低": 2.0, "中": -4.0, "高": -12.0}.get(risk_flag, 0.0)

    auction_score = max(0.0, min(100.0, round(score * 0.52 + readiness * 0.28 + window_score * 0.20 + risk_adjust, 1)))
    open_score = max(0.0, min(100.0, round(score * 0.30 + readiness * 0.46 + continuation * 0.24 + risk_adjust, 1)))
    afternoon_score = max(0.0, min(100.0, round(score * 0.24 + readiness * 0.24 + window_score * 0.28 + continuation * 0.24 + risk_adjust - 3.0, 1)))

    def _note(value: float, strong_text: str, medium_text: str, weak_text: str) -> str:
        if value >= 85.0:
            return strong_text
        if value >= 75.0:
            return medium_text
        return weak_text

    if strategy_name == "尾盘买入法":
        return [
            ("尾盘确认率", auction_score, _note(auction_score, "14:30 后可重点盯", "先看尾盘是否回流", "尾盘不抢，继续等")),
            ("尾盘承接率", open_score, _note(open_score, "尾盘承接稳定可隔夜", "承接不弱再考虑隔夜", "承接乱就放弃")),
            ("开盘兑现率", afternoon_score, _note(afternoon_score, "次日开盘适合先兑现", "开盘先减半再看", "弱开直接走不拖仓")),
        ]
    return [
        ("竞价符合率", auction_score, _note(auction_score, "高开转强可优先盯", "先看是否高开稳住", "不及预期先别追")),
        ("开盘承接率", open_score, _note(open_score, "开盘量价承接可跟", "承接不弱再考虑", "弱承接就先观望")),
        ("午后转强率", afternoon_score, _note(afternoon_score, "午后转强可留隔日", "午后需继续确认", "午后不强别拖仓")),
    ]


def tail_buy_execution_checklist(recommendation) -> list[str]:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name != "尾盘买入法":
        return []
    score = float(getattr(recommendation, "tail_buy_score", 0.0) or 0.0)
    readiness = float(getattr(recommendation, "execution_readiness", 0.0) or 0.0)
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
    next_focus = str(getattr(recommendation, "next_focus", "") or "").strip()

    step_one = "14:30回流: 可重点盯回流确认再动手" if score >= 84.0 else "14:30回流: 先等尾盘回流确认，不抢先手"
    step_two = "尾盘承接: 承接稳定可隔夜" if readiness >= 76.0 and risk_flag != "高" else "尾盘承接: 承接不稳就放弃隔夜"
    step_three = "隔夜消息: 主线风险可控再留仓" if window_score >= 72.0 and risk_flag == "低" else "隔夜消息: 有突发或风险抬升就降级处理"
    step_four = "次日开盘: 优先兑现，不做拖仓" if score >= 80.0 else "次日开盘: 弱开直接走，平开也先减"

    checklist = [step_one, step_two, step_three, step_four]
    if next_focus:
        checklist.append(f"补充盯盘: {next_focus}")
    return checklist


def tail_buy_runtime_status(recommendation, current_dt: datetime | None = None) -> tuple[str, str]:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name != "尾盘买入法":
        return "", ""

    now = current_dt or datetime.now()
    signal_date_raw = str(getattr(recommendation, "signal_date", "") or "").strip()
    signal_day: date | None = None
    if signal_date_raw:
        try:
            signal_day = datetime.strptime(signal_date_raw, "%Y-%m-%d").date()
        except ValueError:
            signal_day = None

    current_time = now.time()
    if signal_day is not None and now.date() > signal_day:
        if current_time < datetime_time(9, 35):
            return "次日开盘兑现窗", "优先看竞价与开盘承接，弱开直接走，不做等待。"
        if current_time < datetime_time(10, 0):
            return "兑现复核", "若开盘没有及时兑现，10点前必须完成强弱复核。"
        return "超时复盘", "已经错过最佳开盘兑现窗，优先复盘是否偏离一日纪律。"

    if current_time < datetime_time(14, 30):
        return "尾盘等待", "先等 14:30 后回流确认，不提前抢尾盘先手。"
    if current_time < datetime_time(14, 50):
        return "尾盘执行窗", "回流与承接共振时再试仓，准备隔夜但不追拉升。"
    if current_time < datetime_time(15, 0):
        return "尾盘收口窗", "只做最后确认，控制隔夜仓位，避免收盘前追高。"
    return "隔夜准备", "收盘后复核消息与主线风险，次日开盘优先兑现。"


def tail_buy_runtime_panel_lines(recommendation, current_dt: datetime | None = None) -> list[str]:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name != "尾盘买入法":
        return []

    phase, hint = tail_buy_runtime_status(recommendation, current_dt=current_dt)
    active_tags = {
        "尾盘等待": {"14:30回流": "当前"},
        "尾盘执行窗": {"14:30回流": "当前", "尾盘承接": "当前"},
        "尾盘收口窗": {"尾盘承接": "当前", "隔夜消息": "下一步"},
        "隔夜准备": {"隔夜消息": "当前", "次日开盘": "下一步"},
        "次日开盘兑现窗": {"次日开盘": "当前"},
        "兑现复核": {"次日开盘": "复核"},
        "超时复盘": {"次日开盘": "复盘"},
    }.get(phase, {})
    checklist = tail_buy_execution_checklist(recommendation)
    panel_lines = [f"当前阶段：{phase or '常规观察'}", f"执行提示：{hint or '先核对尾盘回流、承接和次日兑现节奏。'}"]

    for item in checklist[:4]:
        if ": " in item:
            step_name, detail = item.split(": ", 1)
        else:
            step_name, detail = item, item
        tag = active_tags.get(step_name.strip(), "待命")
        summary = detail.strip() or item
        panel_lines.append(f"[{tag}] {step_name.strip()} | {summary}")
    return panel_lines


def position_advice_check_item(advice, recommendation=None) -> str:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    action = str(getattr(advice, "action", "") or "").upper()
    if strategy_name == "尾盘买入法":
        if action == "SELL":
            return "次日低开或开盘承接不足，直接离场，不做等待。"
        if action == "REDUCE":
            return "次日平开或小高开也先兑现大半，剩余仓位只留观察。"
        if action == "HOLD":
            return "只看次日开盘强弱，不做盘中拖仓式观察。"
        return "核对尾盘回流、隔夜消息和次日开盘兑现节奏。"
    if strategy_name == "一日持股法":
        if action == "SELL":
            return "次日竞价不及预期或弱开弱走，直接离场。"
        if action == "REDUCE":
            return "竞价符合预期也先兑现一半，午后不转强继续降仓。"
        if action == "HOLD":
            return "先看竞价强弱和 5 分钟量能，再决定是否继续拿。"
        return "核对竞价、开盘承接和午后转强情况。"
    if action == "SELL":
        return "跌破风控线或主线转弱时优先离场。"
    if action == "REDUCE":
        return "先锁定部分利润，再观察是否继续回落。"
    if action == "HOLD":
        return "继续看主线强度、承接和风险灯。"
    return "保持观察，等新的主线信号。"


def one_day_hold_phase_labels(decision_or_advice=None, recommendation=None) -> list[str]:
    strategy_name = str(getattr(recommendation, "primary_strategy", "") or "")
    if strategy_name not in {"一日持股法", "尾盘买入法"}:
        return []
    action = str(getattr(decision_or_advice, "action", "") or "").upper()
    if strategy_name == "尾盘买入法":
        if action == "SELL":
            return ["尾盘检查: 放弃隔夜", "开盘执行: 弱开直接走", "盘后复盘: 不做拖仓"]
        if action == "REDUCE":
            return ["尾盘检查: 已可隔夜", "开盘执行: 先兑现大半", "盘后复盘: 剩余仓位再评估"]
        if action == "HOLD":
            return ["尾盘检查: 回流待确认", "开盘执行: 只看强弱", "盘后复盘: 若拖仓需复盘原因"]
        return ["尾盘检查: 等 14:30 后回流", "开盘执行: 次日优先卖", "盘后复盘: 不强不留恋"]
    if action == "SELL":
        return ["竞价检查: 不及预期", "开盘5分: 弱承接", "午后确认: 直接离场"]
    if action == "REDUCE":
        return ["竞价检查: 符合预期", "开盘5分: 冲高兑现", "午后确认: 不强再降仓"]
    if action == "HOLD":
        return ["竞价检查: 观察强弱", "开盘5分: 观察量能", "午后确认: 再定去留"]
    return ["竞价检查: 等高开转强", "开盘5分: 看量能承接", "午后确认: 不强就走"]


def style_dark_chart(chart, title: str, theme_key: str) -> None:
    title_color = "#dfe6ee"
    background = "#0a0c10"
    plot_background = "#000000"
    if theme_key == "pro_terminal":
        title_color = "#ffcf70"
        background = "#0b0d11"
        plot_background = "#050607"
    chart.setTitle(title)
    chart.setTitleBrush(QColor(title_color))
    chart.setBackgroundBrush(QColor(background))
    chart.setPlotAreaBackgroundVisible(True)
    chart.setPlotAreaBackgroundBrush(QColor(plot_background))
    chart.setMargins(chart.margins())
    chart.legend().hide()


def configure_splitter(splitter, sizes) -> None:
    if splitter is None:
        return
    splitter.setSizes([int(size) for size in sizes])


def enable_smooth_scroll(scroll_area) -> None:
    if scroll_area is None:
        return
    scroll_bar = scroll_area.verticalScrollBar()
    if scroll_bar is not None:
        scroll_bar.setSingleStep(24)


def select_first_row(widget) -> None:
    if widget is not None and hasattr(widget, "rowCount") and widget.rowCount() > 0:
        widget.selectRow(0)


def focus_widget_later(widget: QWidget | None) -> None:
    if widget is None:
        return
    QTimer.singleShot(0, widget.setFocus)


def stock_profile_for_symbol(stock_profiles: dict, symbol: str):
    return stock_profiles.get(symbol)


def stock_name_for_symbol(stock_profiles: dict, symbol: str, *, extract_stock_id_fn) -> str:
    profile = stock_profile_for_symbol(stock_profiles, symbol)
    if profile and getattr(profile, "name", ""):
        return profile.name
    return extract_stock_id_fn(symbol)


def stock_id_for_symbol(stock_profiles: dict, symbol: str, *, extract_stock_id_fn) -> str:
    profile = stock_profile_for_symbol(stock_profiles, symbol)
    if profile and getattr(profile, "stock_id", ""):
        return profile.stock_id
    return extract_stock_id_fn(symbol)
