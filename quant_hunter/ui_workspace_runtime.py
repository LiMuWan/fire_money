from __future__ import annotations

from quant_hunter.broker import build_execution_review_snapshot
from quant_hunter.risk import risk_pool_impact_text, risk_profile_brief, risk_profile_projection_text
from quant_hunter.ui_config import (
    action_row_compact_label,
    action_row_tooltip_copy,
    broker_terminal_focus_button_copy,
    contextual_entry_tooltip_suffix,
    contextual_route_button_rule,
    SCANNER_DEFAULT_STATUS_TEXT,
    workbench_empty_panel_copy,
    workspace_key_from_label,
)


def _set_label_text(widget, text: str, *, set_label_text_fn=None) -> None:
    if widget is None:
        return
    if callable(set_label_text_fn):
        try:
            set_label_text_fn(widget, text)
            return
        except Exception:
            pass
    if hasattr(widget, "text") and hasattr(widget, "setText"):
        try:
            current = widget.text()
        except Exception:
            current = None
        if current != text:
            widget.setText(text)


def _set_plain_text(widget, text: str, *, set_text_fn=None) -> None:
    if widget is None:
        return
    if callable(set_text_fn):
        try:
            set_text_fn(widget, text)
            return
        except Exception:
            pass
    if hasattr(widget, "toPlainText") and hasattr(widget, "setPlainText"):
        try:
            current = widget.toPlainText()
        except Exception:
            current = None
        if current != text:
            widget.setPlainText(text)
        return
    if hasattr(widget, "text") and hasattr(widget, "setText"):
        try:
            current = widget.text() if callable(widget.text) else widget.text
        except Exception:
            current = None
        if current != text:
            widget.setText(text)


def _label_text(widget, fallback: str = "--") -> str:
    if widget is None or not hasattr(widget, "text"):
        return fallback
    try:
        value = widget.text()
    except Exception:
        value = ""
    return str(value or fallback)


def _set_tooltip(widget, text: str) -> None:
    if widget is None or not hasattr(widget, "setToolTip"):
        return
    try:
        current = widget.toolTip() if hasattr(widget, "toolTip") else None
    except Exception:
        current = None
    if current != text:
        widget.setToolTip(text)


def _set_enabled(widget, enabled: bool) -> None:
    if widget is None or not hasattr(widget, "setEnabled"):
        return
    try:
        current = widget.isEnabled() if hasattr(widget, "isEnabled") else None
    except Exception:
        current = None
    if current != enabled:
        widget.setEnabled(enabled)


def refresh_monitor_summary_empty_state(window) -> None:
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    _set_plain_text(
        getattr(window, "monitor_summary_text", None),
        workbench_empty_panel_copy("monitor_summary_text"),
        set_text_fn=set_text,
    )
    for attr_name in (
        "_refresh_scanner_focus_status",
        "_refresh_scanner_focus_cards",
        "_refresh_scanner_summary_cards",
        "_refresh_scanner_monitor_summary_v1",
    ):
        refresh_fn = getattr(window, attr_name, None)
        if callable(refresh_fn):
            refresh_fn("")


def refresh_board_empty_state(window) -> None:
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    for attr_name in ("board_text", "board_monitor_text"):
        _set_plain_text(
            getattr(window, attr_name, None),
            workbench_empty_panel_copy(attr_name),
            set_text_fn=set_text,
        )


def button_route_action_key(button) -> str:
    if button is None:
        return ""
    if hasattr(button, "property"):
        try:
            action_key = button.property("routeActionKey")
        except Exception:
            action_key = None
        normalized = str(action_key or "").strip()
        if normalized:
            return normalized
    if hasattr(button, "text"):
        try:
            return str(button.text() or "").strip()
        except Exception:
            return ""
    return ""


def contextual_button_prefix(button) -> str:
    ancestor = button.parentWidget() if button is not None and hasattr(button, "parentWidget") else None
    while ancestor is not None:
        object_name = ""
        if hasattr(ancestor, "objectName"):
            try:
                object_name = str(ancestor.objectName() or "").strip()
            except Exception:
                object_name = ""
        if object_name:
            if "Capital" in object_name:
                return "资金"
            if "Decision" in object_name:
                return "决策"
            if "Theme" in object_name:
                return "主线"
            if "Execution" in object_name:
                return "执行"
            if "Metrics" in object_name:
                return "指标"
            if "Gate" in object_name:
                return "闸门"
            if "Monitor" in object_name:
                return "监控"
            if "Candidate" in object_name:
                return "候选"
            if "Holding" in object_name:
                return "持仓"
            if "Plan" in object_name:
                return "计划"
            if "Pulse" in object_name:
                return "脉搏"
            if "Log" in object_name:
                return "日志"
            if object_name == "workspaceToolPanel":
                return "工具"
            if object_name == "terminalPanel":
                return "面板"
        ancestor = ancestor.parentWidget() if hasattr(ancestor, "parentWidget") else None
    return "工作台"


def contextual_entry_action_key(
    button,
    *,
    original_text: str,
    replacements: list[str],
    index: int,
) -> str:
    if 0 <= index < len(replacements):
        return str(replacements[index] or "").strip()
    prefix = contextual_button_prefix(button)
    return f"{prefix}{str(original_text or '').strip()}"


def contextual_entry_display_text(action_key: str) -> str:
    normalized = str(action_key or "").strip()
    if not normalized:
        return ""
    return action_row_compact_label(normalized, normalized)


def contextual_entry_tooltip(action_key: str, *, prefix: str = "", fallback: str = "") -> str:
    normalized = str(action_key or "").strip()
    if not normalized:
        return fallback
    base = action_row_tooltip_copy(normalized, "")
    suffix = contextual_entry_tooltip_suffix(str(prefix or "").strip(), "")
    if base and suffix:
        return f"{base} {suffix}"
    return base or suffix or fallback


def contextual_route_button_state(
    label: str,
    *,
    focus_symbol: bool,
    has_pool: bool,
    order_intents: bool,
    decisions: bool,
    selected_paper_symbol: bool,
) -> tuple[bool, str, str] | None:
    rule = contextual_route_button_rule(label)
    if not rule:
        return None
    condition = str(rule.get("condition", "") or "").strip()
    enabled = False
    if condition == "focus_or_pool":
        enabled = bool(focus_symbol or has_pool)
    elif condition == "decisions_or_orders":
        enabled = bool(decisions or order_intents)
    elif condition == "focus_or_orders":
        enabled = bool(focus_symbol or order_intents)
    elif condition == "has_pool":
        enabled = bool(has_pool)
    elif condition == "focus_only":
        enabled = bool(focus_symbol)
    elif condition == "paper_focus":
        enabled = bool(selected_paper_symbol)
    return (
        enabled,
        str(rule.get("disabled", "") or ""),
        str(rule.get("enabled", "") or ""),
    )


def _compact_focus_text(text: str, fallback: str = "--") -> str:
    normalized = str(text or "").strip()
    if not normalized:
        return fallback
    for sep in ("：", ":"):
        if sep in normalized:
            normalized = normalized.split(sep, 1)[-1].strip()
    return normalized or fallback


def focus_strip_subtitle(status: str, focus: str, next_step: str) -> str:
    status_text = str(status or "").strip() or "--"
    focus_text = str(focus or "").strip() or "--"
    next_text = str(next_step or "").strip() or "--"
    return f"当前状态：{status_text} | 焦点：{focus_text} | 下一步：{next_text}"


def refresh_live_workspace_summary_panels(window) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)

    if hasattr(window, "scanner_live_summary_headline"):
        scan_count = window.scan_table.rowCount() if hasattr(window, "scan_table") else 0
        watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
        monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
        _set_label_text(window.scanner_live_summary_headline, f"扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}", set_label_text_fn=set_label)
        auto_refresh = "开启" if hasattr(window, "auto_refresh_checkbox") and window.auto_refresh_checkbox.isChecked() else "关闭"
        _set_label_text(
            window.scanner_live_summary_detail,
            f"自动刷新：{auto_refresh} | 最近刷新：{_label_text(getattr(window, 'last_refresh_label', None))}",
            set_label_text_fn=set_label,
        )
        _set_label_text(
            window.scanner_live_summary_meta,
            f"当前股票池：{_label_text(getattr(window, 'universe_label', None))}",
            set_label_text_fn=set_label,
        )
        if hasattr(window, "scanner_summary_metric_labels"):
            summary_values = {
                "coverage": (f"扫描 {scan_count}", f"股票池 {_label_text(getattr(window, 'universe_label', None), '未加载')}"),
                "watch": (f"观察 {watch_count}", "优先从观察池里锁定下一只焦点"),
                "monitor": (f"监控 {monitor_count}", f"自动刷新 {auto_refresh}"),
                "next": ("去机会池" if scan_count else "先扫描", "有焦点后联动机会池与交易" if scan_count else "先建立首轮扫描结果"),
            }
            for key, (value, accent) in summary_values.items():
                if key in window.scanner_summary_metric_labels:
                    _set_label_text(window.scanner_summary_metric_labels[key], value, set_label_text_fn=set_label)
                if hasattr(window, "scanner_summary_metric_accents") and key in window.scanner_summary_metric_accents:
                    _set_label_text(window.scanner_summary_metric_accents[key], accent, set_label_text_fn=set_label)
        if hasattr(window, "scanner_status_banner"):
            active_symbol = getattr(window, "active_symbol", "") or ""
            scanner_banner = (
                f"扫描状态：已锁定 {window._stock_name_for_symbol(active_symbol)} | 观察池与交易可联动 | 下一步：决定是否下钻。"
                if active_symbol
                else (
                    f"扫描状态：已形成 {scan_count} 条信号 | 观察 {watch_count} / 监控 {monitor_count} | 下一步：锁定焦点票。"
                    if scan_count
                    else SCANNER_DEFAULT_STATUS_TEXT
                )
            )
            _set_label_text(window.scanner_status_banner, scanner_banner, set_label_text_fn=set_label)
            scanner_focus_symbol = _scanner_focus_symbol(window)
            if scanner_focus_symbol:
                _set_label_text(
                    window.scanner_status_banner,
                    f"扫描状态：已锁定 {window._stock_name_for_symbol(scanner_focus_symbol)} | 观察池与监控可联动 | 下一步：核对焦点去向。",
                    set_label_text_fn=set_label,
                )
        if hasattr(window, "scanner_desk_summary_subtitle"):
            scanner_subtitle = (
                "当前已有焦点票，先核对扫描信号、观察池状态和盘中监控动作，再决定是否联动机会池与交易。"
                if getattr(window, "active_symbol", "") or ""
                else "先确认扫描范围、观察池焦点和盘中监控动作，再决定是否联动机会池和交易。"
            )
            _set_label_text(window.scanner_desk_summary_subtitle, scanner_subtitle, set_label_text_fn=set_label)
            active_symbol = getattr(window, "active_symbol", "") or ""
            scanner_focus = _compact_focus_text(
                window._stock_name_for_symbol(active_symbol) if active_symbol and hasattr(window, "_stock_name_for_symbol") else "",
                "观察池与监控链路",
            )
            _set_label_text(
                window.scanner_desk_summary_subtitle,
                focus_strip_subtitle(
                    "盘中链路已联动" if active_symbol else "等待扫描结果",
                    scanner_focus if active_symbol else "观察池与监控链路",
                    "继续核对监控动作与候选去向" if active_symbol else "先执行扫描，再确认焦点标的",
                ),
                set_label_text_fn=set_label,
            )

    if hasattr(window, "board_live_summary_headline"):
        candidate_count = window.board_table.rowCount() if hasattr(window, "board_table") else 0
        monitor_count = window.board_monitor_table.rowCount() if hasattr(window, "board_monitor_table") else 0
        _set_label_text(window.board_live_summary_headline, f"候选 {candidate_count} / 监控 {monitor_count}", set_label_text_fn=set_label)
        auto_export = "开启" if hasattr(window, "auto_review_export_checkbox") and window.auto_review_export_checkbox.isChecked() else "关闭"
        _set_label_text(window.board_live_summary_detail, f"收盘导出：{auto_export} | 焦点联动：扫描 / 推荐 / 复盘", set_label_text_fn=set_label)
        _set_label_text(
            window.board_live_summary_meta,
            _label_text(getattr(window, "board_focus_label", None), "等待焦点同步"),
            set_label_text_fn=set_label,
        )
        if hasattr(window, "board_summary_metric_labels"):
            focus_text = _label_text(getattr(window, "board_focus_label", None), "等待焦点同步")
            summary_values = {
                "candidate": (f"{candidate_count} 只", "前排候选与计划买点"),
                "monitor": (f"{monitor_count} 条", "回封概率与炸板风险"),
                "focus": ("已联动" if "等待" not in focus_text else "待联动", focus_text),
                "next": ("看回封" if monitor_count else "先刷新专项", "优先核对最强候选与回封质量" if monitor_count else "先建立专项候选池"),
            }
            for key, (value, accent) in summary_values.items():
                if key in window.board_summary_metric_labels:
                    _set_label_text(window.board_summary_metric_labels[key], value, set_label_text_fn=set_label)
                if hasattr(window, "board_summary_metric_accents") and key in window.board_summary_metric_accents:
                    _set_label_text(window.board_summary_metric_accents[key], accent, set_label_text_fn=set_label)
        if hasattr(window, "board_status_banner"):
            focus_text = _label_text(getattr(window, "board_focus_label", None), "等待焦点同步")
            board_banner = (
                f"专项状态：已形成 {candidate_count} 只候选 | 监控 {monitor_count} 条 | 下一步：锁定最强回封。"
                if candidate_count or monitor_count
                else "专项状态：待同步 | 候选池与回封监控待建立 | 下一步：刷新专项候选。"
            )
            if "等待" not in focus_text:
                board_banner = f"{board_banner} 当前焦点已同步。"
            _set_label_text(window.board_status_banner, board_banner, set_label_text_fn=set_label)
        if hasattr(window, "board_desk_summary_subtitle"):
            board_subtitle = (
                "当前已形成专项候选与监控焦点，先定最强回封与炸板风险，再决定是否进入执行链路。"
                if candidate_count or monitor_count
                else "先定强势候选、回封质量和执行准备，再进入候选总览与回封监控。"
            )
            _set_label_text(window.board_desk_summary_subtitle, board_subtitle, set_label_text_fn=set_label)
            _set_label_text(
                window.board_desk_summary_subtitle,
                focus_strip_subtitle(
                    "候选与监控已建立" if (candidate_count or monitor_count) else "等待专项候选",
                    _compact_focus_text(focus_text, "回封监控链路"),
                    "核对回封质量与执行动作" if (candidate_count or monitor_count) else "先刷新候选，再确认监控焦点",
                ),
                set_label_text_fn=set_label,
            )

    if hasattr(window, "detail_live_summary_headline"):
        signal_count = window.signal_table.rowCount() if hasattr(window, "signal_table") else 0
        trade_count = window.trades_table.rowCount() if hasattr(window, "trades_table") else 0
        active_symbol = getattr(window, "active_symbol", "") or "未选中"
        _set_label_text(window.detail_live_summary_headline, f"当前标的：{active_symbol}", set_label_text_fn=set_label)
        _set_label_text(window.detail_live_summary_detail, f"近期信号 {signal_count} 条 | 交易记录 {trade_count} 条", set_label_text_fn=set_label)
        _set_label_text(window.detail_live_summary_meta, _label_text(getattr(window, "active_symbol_label", None), "当前标的：未选择"), set_label_text_fn=set_label)
        if hasattr(window, "detail_status_banner"):
            detail_banner = (
                f"复盘状态：已锁定 {active_symbol} | 偏差与时间线可核对 | 下一步：沉淀复盘结论。"
                if active_symbol != "未选中"
                else "复盘状态：待联动 | 焦点票尚未同步 | 下一步：从机会池、扫描或执行中控联动。"
            )
            _set_label_text(window.detail_status_banner, detail_banner, set_label_text_fn=set_label)
        if hasattr(window, "detail_desk_summary_subtitle"):
            detail_subtitle = (
                "当前已有焦点票，先核对单票结论、执行偏差和下一步观察，再进入信号与交易、历史战法与结论沉淀。"
                if active_symbol != "未选中"
                else "先定单票结论、执行偏差和下一步观察，再进入信号与交易、历史战法与结论沉淀。"
            )
            _set_label_text(window.detail_desk_summary_subtitle, detail_subtitle, set_label_text_fn=set_label)
            _set_label_text(
                window.detail_desk_summary_subtitle,
                focus_strip_subtitle(
                    "单票复盘已联动" if active_symbol != "éˆîˆâ‚¬å¤‰è…‘" else "等待单票联动",
                    _compact_focus_text(active_symbol, "当前焦点标的"),
                    "核对决策、执行与结论" if active_symbol != "éˆîˆâ‚¬å¤‰è…‘" else "先从机会池、扫描或执行中控选中一只股票",
                ),
                set_label_text_fn=set_label,
            )

    if hasattr(window, "detail_desk_summary_subtitle"):
        _set_label_text(
            window.detail_desk_summary_subtitle,
            focus_strip_subtitle(
                "å•ç¥¨å¤ç›˜å·²è”åŠ¨" if active_symbol != "æœªé€‰ä¸­" else "ç­‰å¾…å•ç¥¨è”åŠ¨",
                _compact_focus_text(active_symbol, "å½“å‰ç„¦ç‚¹æ ‡çš„"),
                "æ ¸å¯¹å†³ç­–ã€æ‰§è¡Œä¸Žç»“è®º" if active_symbol != "æœªé€‰ä¸­" else "å…ˆä»Žæœºä¼šæ± ã€æ‰«ææˆ–æ‰§è¡Œä¸­æŽ§é€‰ä¸­ä¸€åªè‚¡ç¥¨",
            ),
            set_label_text_fn=set_label,
        )

    if hasattr(window, "detail_desk_summary_subtitle"):
        _set_label_text(
            window.detail_desk_summary_subtitle,
            focus_strip_subtitle(
                "å•ç¥¨å¤ç›˜å·²è”åŠ¨" if active_symbol != "æœªé€‰ä¸­" else "ç­‰å¾…å•ç¥¨è”åŠ¨",
                _compact_focus_text(active_symbol, "å½“å‰ç„¦ç‚¹æ ‡çš„"),
                "æ ¸å¯¹å†³ç­–ã€æ‰§è¡Œä¸Žç»“è®º" if active_symbol != "æœªé€‰ä¸­" else "å…ˆä»Žæœºä¼šæ± ã€æ‰«ææˆ–æ‰§è¡Œä¸­æŽ§é€‰ä¸­ä¸€åªè‚¡ç¥¨",
            ),
            set_label_text_fn=set_label,
        )

    if hasattr(window, "config_live_summary_headline"):
        state = getattr(window, "state", None)
        plan_text = getattr(state, "license_plan", "") or "TRIAL"
        top_theme_limit, max_total_exposure, _ = window._current_strategy_runtime_config()
        _set_label_text(window.config_live_summary_headline, f"方案：{plan_text} | 主线前排 {top_theme_limit}", set_label_text_fn=set_label)
        risk_key = getattr(state, "strategy_risk_profile", "standard")
        risk_hint = risk_profile_brief(risk_key)
        meta = getattr(window, "last_daily_pool_meta", {}) or {}
        pool_impact = risk_pool_impact_text(meta)
        pool_projection = risk_profile_projection_text(risk_key, meta)
        template_text = window.daily_plan_template_combo.currentText() if hasattr(window, "daily_plan_template_combo") else "--"
        _set_label_text(
            window.config_live_summary_detail,
            f"总仓位上限 {max_total_exposure:.2f} | 模板 {template_text} | {pool_impact}",
            set_label_text_fn=set_label,
        )
        focus_theme_text = window.focus_themes_input.text().strip() if hasattr(window, "focus_themes_input") else ""
        risk_text = window.strategy_risk_profile_combo.currentText() if hasattr(window, "strategy_risk_profile_combo") else getattr(state, "strategy_risk_profile", "standard")
        _set_label_text(
            window.config_live_summary_meta,
            f"风险档位：{risk_text} | {risk_hint} | {pool_projection} | 关注题材：{focus_theme_text or '未设置'}",
            set_label_text_fn=set_label,
        )
        if hasattr(window, "config_status_banner"):
            config_banner = f"配置状态：{plan_text} | 风险 {risk_text} / 模板 {template_text} | 下一步：保存后刷新机会池。"
            _set_label_text(window.config_status_banner, config_banner, set_label_text_fn=set_label)
        if hasattr(window, "config_desk_summary_subtitle"):
            config_subtitle = f"当前已锁定风险 {risk_text}、模板 {template_text} 与消息源边界，下一步保存后刷新机会池与交易链路。"
            _set_label_text(window.config_desk_summary_subtitle, config_subtitle, set_label_text_fn=set_label)
            _set_label_text(
                window.config_desk_summary_subtitle,
                focus_strip_subtitle(
                    "策略方案已就绪",
                    f"{risk_text} / {template_text}",
                    "保存后刷新机会池",
                ),
                set_label_text_fn=set_label,
            )
        if hasattr(window, "_refresh_risk_snapshot_cards"):
            window._refresh_risk_snapshot_cards()

    if hasattr(window, "detail_desk_summary_subtitle"):
        active_symbol = getattr(window, "active_symbol", "") or "æœªé€‰ä¸­"
        _set_label_text(
            window.detail_desk_summary_subtitle,
            focus_strip_subtitle(
                "å•ç¥¨å¤ç›˜å·²è”åŠ¨" if active_symbol != "æœªé€‰ä¸­" else "ç­‰å¾…å•ç¥¨è”åŠ¨",
                _compact_focus_text(active_symbol, "å½“å‰ç„¦ç‚¹æ ‡çš„"),
                "æ ¸å¯¹å†³ç­–ã€æ‰§è¡Œä¸Žç»“è®º" if active_symbol != "æœªé€‰ä¸­" else "å…ˆä»Žæœºä¼šæ± ã€æ‰«ææˆ–æ‰§è¡Œä¸­æŽ§é€‰ä¸­ä¸€åªè‚¡ç¥¨",
            ),
            set_label_text_fn=set_label,
        )

    refresh_scanner_board_action_feedback(window)


def workspace_badge_text(
    current_name: str,
    *,
    scan_count: int = 0,
    watch_count: int = 0,
    monitor_count: int = 0,
    board_count: int = 0,
    board_monitor_count: int = 0,
    pool_count: int = 0,
    plan_count: int = 0,
    pending_orders: int = 0,
    submitted_orders: int = 0,
) -> str:
    page_key = workspace_key_from_label(current_name, default="overview")
    label = str(current_name or "工作区").strip() or "工作区"
    if page_key == "scanner":
        return f"量化猎手 Pro v2.2 · {label} · 扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}"
    if page_key == "board":
        return f"量化猎手 Pro v2.2 · {label} · 候选 {board_count} / 监控 {board_monitor_count}"
    if page_key == "recommend":
        return f"量化猎手 Pro v2.2 · {label} · 候选 {pool_count} / 计划 {plan_count}"
    if page_key == "broker":
        return f"量化猎手 Pro v2.2 · {label} · 待审 {pending_orders} / 已提交 {submitted_orders}"
    return f"量化猎手 Pro v2.2 · {label}"


def broker_status_banner_text(
    *,
    pending_orders: int,
    submitted_orders: int,
    blockers: list[str] | tuple[str, ...],
    warnings: list[str] | tuple[str, ...],
) -> str:
    blockers = list(blockers or [])
    warnings = list(warnings or [])
    if blockers:
        return f"交易状态：红灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：先处理阻塞项。"
    if warnings and pending_orders:
        return f"交易状态：黄灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：复核风险后进入确认。"
    if pending_orders:
        return f"交易状态：绿灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：优先推动高等级委托送审。"
    if submitted_orders:
        return f"交易状态：已提交 {submitted_orders} 笔 | 下一步：跟踪成交与回执。"
    return "交易状态：继续复核 | 主线与闸门待确认 | 下一步：生成并复核委托。"


def refresh_broker_status_panel(
    window,
    *,
    profile,
    env: dict,
    holdings,
    cash_snapshot,
    order_intents,
    extra: str = "",
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    display_mode = getattr(window, "_display_mode", lambda value: str(value or ""))

    market_value = sum(getattr(item, "market_value", 0.0) or 0.0 for item in holdings or [])
    available = cash_snapshot.available_cash if cash_snapshot else 0.0
    total_assets = cash_snapshot.total_assets if cash_snapshot else market_value + available
    connected = bool((env.get("direct_ready") or env.get("bridge_ready")) and getattr(profile, "mode", "") == "sdk")

    note_lines = [
        "环境诊断",
        f"- 主程序 Python：{env.get('python_version', '--')}",
        f"- 当前解释器 SDK：{'已安装' if env.get('module_installed') else '未安装'} ({env.get('sdk_module', '--')})",
    ]
    if env.get("bridge_python"):
        note_lines.append(
            f"- 桥接解释器：{env.get('bridge_python')} | SDK {'已安装' if env.get('bridge_module_installed') else '未安装'}"
        )
    if env.get("bridge_ready"):
        note_lines.append("- 当前环境已满足桥接下单条件，可通过 Python 3.12 + GM SDK 调用。")
    elif env.get("direct_ready"):
        note_lines.append("- 当前环境已满足直连 SDK 调用条件。")
    else:
        note_lines.append("- 当前环境暂未满足 SDK 下单条件，建议继续使用导出 CSV 或 GM 脚本。")

    content = [
        "网关：东方财富 / 掘金 GM",
        f"模式：{display_mode(getattr(profile, 'mode', ''))}",
        f"连接状态：{'已就绪' if connected else '未就绪'}",
        "",
        "\n".join(note_lines),
        "",
        "账户概览",
        f"- 持仓证券数：{len(holdings or [])}",
        f"- 持仓市值：{market_value:,.2f}",
        f"- 可用资金：{available:,.2f}",
        f"- 总资产：{total_assets:,.2f}",
        "",
        f"委托建议数：{len(order_intents or [])}",
    ]
    if extra:
        content.extend(["", extra])
    if hasattr(window, "broker_status_text") and callable(set_text):
        set_text(window.broker_status_text, "\n".join(content))

    if hasattr(window, "broker_metric_labels"):
        readiness = "已就绪" if connected else ("桥接可用" if env.get("bridge_ready") else "待配置")
        risk_count = sum(1 for item in order_intents or [] if getattr(item, "side", "") in {"SELL", "REDUCE"})
        buy_count = sum(1 for item in order_intents or [] if getattr(item, "side", "") == "BUY")
        buy_budget = sum(
            float(getattr(item, "price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0)
            for item in order_intents or []
            if getattr(item, "side", "") == "BUY"
        )
        exposure = (buy_budget / available) if available > 0 else 0.0
        _set_label_text(window.broker_metric_labels["readiness"], readiness, set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_accents["readiness"], "SDK 可下单" if connected else ("可桥接调用" if env.get("bridge_ready") else "建议先导出/桥接"), set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_labels["capital"], f"{available:,.0f}", set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_accents["capital"], f"持仓市值 {market_value:,.0f}", set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_labels["risk_reward"], f"{buy_count} / {risk_count}", set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_accents["risk_reward"], "买入候选 / 卖减建议", set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_labels["risk_budget"], f"{exposure:.0%}" if buy_budget > 0 else "0%", set_label_text_fn=set_label)
        _set_label_text(window.broker_metric_accents["risk_budget"], "预计买入力度", set_label_text_fn=set_label)


def refresh_broker_auxiliary_panels_status(
    window,
    *,
    stage_title: str,
    stage_detail: str,
    order_count: int,
    submit_count: int,
    blockers,
    broker_setup_policy: dict[str, object],
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)

    stage_label = getattr(window, "broker_stage_label", None)
    if stage_label is not None:
        _set_label_text(stage_label, f"执行阶段：{stage_title} | {stage_detail}", set_label_text_fn=set_label)

    banner = getattr(window, "broker_workbench_banner", None)
    if banner is not None:
        _set_label_text(banner, f"执行中控：当前处于“{stage_title}”阶段，{stage_detail}", set_label_text_fn=set_label)

    status_label = getattr(window, "broker_detail_status_label", None)
    if status_label is not None and not getattr(window, "_qh_broker_detail_visible_v40", False):
        if stage_title in {"待确认提交", "执行回执"}:
            _set_label_text(status_label, "执行明细已折叠；当前已经进入提交或回执阶段，需要时可展开看明细和偏差复盘。", set_label_text_fn=set_label)
        else:
            _set_label_text(status_label, "执行明细已折叠，先看焦点委托、阶段判断和风险闸门。", set_label_text_fn=set_label)

    setup_status_label = getattr(window, "broker_setup_status_label", None)
    if setup_status_label is not None and not getattr(window, "_qh_broker_setup_visible_v41", False):
        collapsed_map = dict(broker_setup_policy.get("collapsed_status_by_stage", {}) or {})
        if stage_title == "执行回执":
            _set_label_text(setup_status_label, str(collapsed_map.get("submissions", "")), set_label_text_fn=set_label)
        elif stage_title == "待确认提交":
            _set_label_text(setup_status_label, str(collapsed_map.get("orders", "")), set_label_text_fn=set_label)
        else:
            _set_label_text(setup_status_label, str(collapsed_map.get("default", "")), set_label_text_fn=set_label)

    focus_button = getattr(window, "broker_focus_priority_button", None)
    if focus_button is not None and hasattr(focus_button, "setText"):
        target_text = "定位待提委托" if order_count > 0 else "定位前排"
        current_text = focus_button.text() if hasattr(focus_button, "text") else ""
        if current_text != target_text:
            focus_button.setText(target_text)


def refresh_broker_action_flow(
    window,
    *,
    risk_profile_labels: dict[str, str],
    broker_primary_cta_labels_fn,
    broker_primary_cta_tooltips_fn,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    set_button_role = getattr(window, "_set_button_role", None)

    order_count = len(getattr(window, "order_intents", []) or [])
    submit_count = len(getattr(window, "order_submission_records", []) or [])
    risk_key = getattr(getattr(window, "state", None), "strategy_risk_profile", "standard")
    risk_label = risk_profile_labels.get(risk_key, risk_key)
    focus_recommend = window._explicit_recommendation_focus() if hasattr(window, "_explicit_recommendation_focus") else None
    selected_intent = window._selected_order_intent() if hasattr(window, "_selected_order_intent") else None
    broker_summary = dict(getattr(window, "last_broker_execution_summary", {}) or {})

    latest_symbol = ""
    latest_stage = ""
    if submit_count:
        latest_record = getattr(window, "order_submission_records", [])[-1]
        latest_symbol = str(latest_record.get("symbol", "") or "")
        latest_stage = str(broker_summary.get("stage", "") or "")
    elif selected_intent is not None:
        latest_symbol = str(getattr(selected_intent, "symbol", "") or "")
    elif order_count:
        latest_symbol = str(getattr(getattr(window, "order_intents", [None])[0], "symbol", "") or "")
    elif focus_recommend is not None:
        latest_symbol = str(getattr(focus_recommend, "symbol", "") or "")

    cta_labels = broker_primary_cta_labels_fn(
        stage=latest_stage,
        order_count=order_count,
        submit_count=submit_count,
        has_focus_symbol=bool(latest_symbol or (getattr(window, "active_symbol", "") or "")),
    )
    focus_symbol = latest_symbol or (getattr(window, "active_symbol", "") or "")
    focus_stock_name = window._stock_name_for_symbol(focus_symbol) if focus_symbol else "当前焦点"

    review_snapshot = build_execution_review_snapshot(broker_summary)
    portfolio_review = dict(broker_summary.get("portfolio_risk_review", {}) or {})
    portfolio_row = next(
        (row for row in list(portfolio_review.get("rows", []) or []) if str(row.get("symbol", "") or "") == focus_symbol),
        {},
    )
    portfolio_status = str(portfolio_row.get("status", "") or portfolio_review.get("status", "") or "待评估")
    portfolio_detail = str(portfolio_row.get("detail", "") or "")
    blockers = list(broker_summary.get("blockers", []) or [])
    warnings = list(broker_summary.get("warnings", []) or [])
    mainline_review = dict(broker_summary.get("mainline_review", {}) or {})
    mainline_rows = list(mainline_review.get("rows", []) or [])
    first_mainline_row = mainline_rows[0] if mainline_rows else {}
    review_status = str(mainline_review.get("status", "待审查") or "待审查")
    available_cash = float(getattr(getattr(window, "cash_snapshot", None), "available_cash", 0.0) or 0.0)
    estimated_capital = sum(
        float(getattr(item, "price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0)
        for item in getattr(window, "order_intents", []) or []
        if str(getattr(item, "side", "") or "").upper() == "BUY"
    )
    capital_usage_ratio = (estimated_capital / available_cash) if available_cash > 0 and estimated_capital > 0 else 0.0
    risk_lamp = "红灯" if blockers else ("黄灯" if warnings else ("绿灯" if (order_count or submit_count or focus_symbol) else "待评估"))
    risk_note = blockers[0] if blockers else (warnings[0] if warnings else "当前未发现硬阻塞")
    cta_tooltips = broker_primary_cta_tooltips_fn(
        stage=latest_stage,
        order_count=order_count,
        submit_count=submit_count,
        stock_name=focus_stock_name,
    )

    profile = window.current_broker_profile() if hasattr(window, "current_broker_profile") else None
    missing_sdk_fields: list[str] = []
    missing_submission_guards: list[str] = []
    if profile is not None and getattr(profile, "mode", "export") == "sdk":
        if not getattr(profile, "account_id", "").strip():
            missing_sdk_fields.append("账户 ID")
        if not getattr(profile, "strategy_id", "").strip():
            missing_sdk_fields.append("策略 ID")
        if not getattr(profile, "token", "").strip():
            missing_sdk_fields.append("SDK Token")
        if bool(getattr(profile, "test_submit_only", False)) and not str(getattr(profile, "test_submit_symbol_whitelist", "") or "").strip():
            missing_submission_guards.append("测试白名单")

    blocker_button = getattr(window, "broker_focus_blocker_button", None)
    if blocker_button is not None and hasattr(blocker_button, "setText"):
        blocker_text, blocker_tip = broker_terminal_focus_button_copy("blocker", order_count=order_count, submit_count=submit_count)
        _set_label_text(blocker_button, blocker_text, set_label_text_fn=set_label)
        _set_tooltip(blocker_button, f"{blocker_tip}\n{review_snapshot.get('headline', '')}".strip())

    priority_button = getattr(window, "broker_focus_priority_button", None)
    if priority_button is not None and hasattr(priority_button, "setText"):
        priority_text, priority_tip = broker_terminal_focus_button_copy(
            "priority",
            order_count=order_count,
            submit_count=submit_count,
            stock_name=window._stock_name_for_symbol(latest_symbol) if latest_symbol else "",
        )
        _set_label_text(priority_button, priority_text, set_label_text_fn=set_label)
        _set_tooltip(priority_button, f"{priority_tip}\n{review_snapshot.get('headline', '')}".strip())

    button = getattr(window, "confirm_submit_orders_button", None)
    confirm_ready = bool(order_count > 0 and not missing_sdk_fields and not missing_submission_guards)
    if button is not None and hasattr(button, "setText"):
        _set_enabled(button, confirm_ready)
        button_text = cta_labels["confirm_text"] if order_count > 0 else "确认并提交委托"
        button_tip = (
            f"当前是 SDK 模式，先补齐 {', '.join(missing_sdk_fields)} 后再提交。"
            if missing_sdk_fields
            else (
                f"当前测试单模式仍缺少 {', '.join(missing_submission_guards)}，先完成联调保护配置后再提交。"
                if missing_submission_guards
                else cta_tooltips["confirm_tooltip"]
            )
        )
        if confirm_ready and focus_symbol:
            impact_tail = portfolio_detail or f"组合{portfolio_status}"
            button_tip = f"当前焦点：{focus_stock_name} | {impact_tail} | {review_snapshot.get('headline', '')} | 进确认弹窗前先核对价格、数量和风险闸门。"
        elif not missing_sdk_fields and not missing_submission_guards and review_snapshot.get("headline"):
            button_tip = f"{button_tip} | {review_snapshot.get('headline', '')}".strip(" |")
        _set_label_text(button, button_text if confirm_ready else "确认并提交委托", set_label_text_fn=set_label)
        _set_tooltip(button, button_tip)
        if callable(set_button_role):
            set_button_role(button, "accent" if confirm_ready else "ghost")

    generate_button = getattr(window, "generate_order_suggestions_button", None)
    if generate_button is not None and hasattr(generate_button, "setText"):
        _set_label_text(generate_button, cta_labels["generate_text"], set_label_text_fn=set_label)
        generate_tip = cta_tooltips["generate_tooltip"]
        if review_snapshot.get("headline"):
            generate_tip = f"{generate_tip} | {review_snapshot.get('headline', '')}".strip(" |")
        _set_tooltip(generate_button, generate_tip)
        if callable(set_button_role):
            set_button_role(generate_button, "accent" if order_count <= 0 else "tonal")

    sync_button = getattr(window, "sync_broker_button", None)
    sync_ready = bool(profile is not None and getattr(profile, "mode", "export") == "sdk" and not missing_sdk_fields)
    if sync_button is not None and hasattr(sync_button, "setEnabled"):
        _set_enabled(sync_button, sync_ready)
        if missing_sdk_fields:
            sync_tip = f"先补齐 {', '.join(missing_sdk_fields)}，再同步资金和持仓。"
        elif profile is not None and getattr(profile, "mode", "export") != "sdk":
            sync_tip = "当前是导出模式，切到 SDK 模式后再同步资金和持仓。"
        else:
            sync_tip = "先做连接校验，再同步 SDK 资金和持仓。"
        _set_tooltip(sync_button, sync_tip)
        if callable(set_button_role):
            set_button_role(sync_button, "tonal" if sync_ready else "ghost")

    validate_button = getattr(window, "validate_broker_connection_button", None)
    validate_ready = bool(
        profile is not None
        and getattr(profile, "mode", "export") == "sdk"
        and not missing_sdk_fields
        and not missing_submission_guards
    )
    if validate_button is not None and hasattr(validate_button, "setEnabled"):
        _set_enabled(validate_button, True)
        if missing_sdk_fields:
            validate_tip = f"先用这个预检缺少哪些字段：{', '.join(missing_sdk_fields)}。"
        elif missing_submission_guards:
            validate_tip = f"先用这个预检联调保护项：{', '.join(missing_submission_guards)}。"
        elif profile is not None and getattr(profile, "mode", "export") != "sdk":
            validate_tip = "当前是导出模式，可用它核对环境与当前提交安全配置。"
        else:
            validate_tip = "先做联调预检，确认环境、测试单和白名单都已就绪。"
        _set_tooltip(validate_button, validate_tip)
        if callable(set_button_role):
            set_button_role(validate_button, "accent" if validate_ready else "ghost")

    banner = getattr(window, "broker_status_banner", None)
    if banner is not None and hasattr(banner, "setText"):
        news_brief = window._news_action_brief(focus_symbol) if focus_symbol and hasattr(window, "_news_action_brief") else ""
        if missing_sdk_fields:
            banner_text = f"交易状态：{risk_label}档审查 | SDK 字段待补齐 | 下一步：去接入中心补齐 {', '.join(missing_sdk_fields)}。"
        elif submit_count:
            stock_name = window._stock_name_for_symbol(latest_symbol) if latest_symbol else "最新委托"
            banner_text = f"交易状态：{risk_label}档审查 | 已提交 {submit_count} 笔 | 下一步：跟踪 {stock_name} 的回执反馈。"
        elif order_count:
            banner_text = f"交易状态：{risk_label}档审查 | 待审 {order_count} 笔 | 下一步：优先复核 {focus_stock_name}。"
        elif focus_symbol:
            banner_text = (
                f"交易状态：{risk_label}档审查 | 已同步 {focus_stock_name} | 下一步：生成委托并复核闸门。"
                f"{(' | ' + news_brief) if news_brief else ''}"
            )
        else:
            banner_text = f"交易状态：{risk_label}档审查 | 委托链路待建立 | 下一步：先从机会池生成委托。"
        _set_label_text(banner, banner_text, set_label_text_fn=set_label)

    if hasattr(window, "broker_summary_metric_labels"):
        if missing_sdk_fields:
            stage_value = "待配置"
            stage_accent = f"先补齐 {' / '.join(missing_sdk_fields)}"
        elif order_count:
            stage_value = "待确认"
            stage_accent = f"已生成 {order_count} 笔 | 焦点 {focus_stock_name}"
        elif submit_count:
            stage_value = "看回执"
            stage_accent = f"最新回执 {focus_stock_name or '最新委托'}"
        elif focus_symbol:
            stage_value = "待委托"
            stage_accent = f"围绕 {focus_stock_name} 建链"
        else:
            stage_value = "待委托"
            stage_accent = "先从机会池或交易计划生成委托"

        gate_value = str(mainline_review.get("status", "待审查") or "待审查")
        if blockers:
            gate_accent = blockers[0]
        elif warnings:
            gate_accent = warnings[0]
        elif first_mainline_row:
            gate_accent = f"{first_mainline_row.get('theme', '--')} | {first_mainline_row.get('status', '--')}"
        else:
            gate_accent = "等待主线审查与风险灯联动"

        queue_value = f"{order_count} 笔" if order_count else "0 笔"
        queue_accent = f"回执 {submit_count} | 焦点 {focus_stock_name}" if (order_count or submit_count) else "等待生成第一批委托"
        receipt_value = ("红灯" if blockers else ("黄灯" if warnings else "绿灯")) if (order_count or submit_count or focus_symbol) else "无回执"
        receipt_accent = (
            f"回执 {submit_count} | 组合 {portfolio_status}"
            if submit_count
            else ("提交后这里会回写成交状态" if not order_count else f"待提交 {order_count} | 组合 {portfolio_status}")
        )
        _set_label_text(window.broker_summary_metric_labels["stage"], stage_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_accents["stage"], stage_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_labels["gate"], gate_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_accents["gate"], gate_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_labels["queue"], queue_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_accents["queue"], queue_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_labels["receipt"], receipt_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_summary_metric_accents["receipt"], receipt_accent, set_label_text_fn=set_label)

    next_action_accent = "先从机会池或交易计划生成第一批委托"
    gate_headline = "可进入确认"
    gate_capital_value = "待预算"
    gate_lead_value = "待首票"

    if hasattr(window, "broker_execution_summary_metric_labels"):
        blocker_value = risk_lamp
        blocker_accent = risk_note
        mainline_value = f"占资 {capital_usage_ratio * 100:.1f}%" if estimated_capital > 0 else "待预算"
        mainline_accent = (
            f"可用 {available_cash:,.0f} | 计划 {estimated_capital:,.0f}"
            if estimated_capital > 0
            else "等待委托生成后估算资金闸门"
        )
        action_value = (
            str(first_mainline_row.get("name", first_mainline_row.get("symbol", "")) or "")
            or (focus_stock_name if focus_symbol else "待首票")
        )
        action_accent = (
            f"{first_mainline_row.get('theme', '--')} | {first_mainline_row.get('status', '--')}"
            if first_mainline_row
            else f"{str(mainline_review.get('status', '待审查') or '待审查')} | 当前焦点 {focus_stock_name}"
        )
        if missing_sdk_fields:
            portfolio_value = "先补配置"
            portfolio_accent = f"补齐 {' / '.join(missing_sdk_fields)}"
        elif available_cash <= 0 and estimated_capital > 0:
            portfolio_value = "先同步资金"
            portfolio_accent = "先回写可用资金，再确认预算占用"
        elif submit_count:
            portfolio_value = "看最新回执"
            portfolio_accent = f"最新回执 {focus_stock_name or '当前焦点'}"
        elif order_count:
            portfolio_value = "提交确认"
            portfolio_accent = f"当前焦点 {focus_stock_name} | 先核对价格和数量"
        elif focus_symbol:
            portfolio_value = "生成委托"
            portfolio_accent = f"围绕 {focus_stock_name} 建立第一条委托链路"
        else:
            portfolio_value = "待委托"
            portfolio_accent = "先从机会池或交易计划生成第一批委托"
        next_action_accent = portfolio_accent
        gate_capital_value = mainline_value
        gate_lead_value = action_value
        _set_label_text(window.broker_execution_summary_metric_labels["blocker"], blocker_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_accents["blocker"], blocker_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_labels["mainline"], mainline_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_accents["mainline"], mainline_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_labels["action"], action_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_accents["action"], action_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_labels["portfolio"], portfolio_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_execution_summary_metric_accents["portfolio"], portfolio_accent, set_label_text_fn=set_label)

    if hasattr(window, "broker_gate_summary_text"):
        if missing_sdk_fields:
            gate_headline = "先补配置"
        elif available_cash <= 0 and estimated_capital > 0:
            gate_headline = "先同步资金"
        elif blockers:
            gate_headline = "先处理阻塞"
        elif warnings:
            gate_headline = "可继续，建议复核"
        elif submit_count:
            gate_headline = "转看回执"
        elif focus_symbol and not order_count:
            gate_headline = "先生成委托"
        gate_risk = f"{risk_lamp} | {risk_label}档 | 组合 {portfolio_status} | {risk_note}"
        gate_conclusion = f"{gate_headline} | 资金 {gate_capital_value} | 首票 {gate_lead_value}"
        _set_plain_text(
            window.broker_gate_summary_text,
            "\n".join(
                [
                    "闸门提要",
                    f"结论：{gate_conclusion}",
                    f"风险：{gate_risk}",
                    f"下一步：{next_action_accent}",
                ]
            ),
            set_text_fn=set_text,
        )

    if hasattr(window, "broker_result_metric_labels"):
        if submit_count:
            result_stage_value = "看回执"
            result_stage_accent = f"最新回执 {focus_stock_name or '当前焦点'}"
        elif order_count:
            result_stage_value = "待提交"
            result_stage_accent = f"已生成 {order_count} 笔委托"
        elif focus_symbol:
            result_stage_value = "待回执"
            result_stage_accent = f"围绕 {focus_stock_name} 等第一条回执"
        else:
            result_stage_value = "待回执"
            result_stage_accent = "提交后这里会回写执行阶段"
        result_status_value = f"{order_count} / {submit_count}" if (order_count or submit_count) else "待提交"
        result_status_accent = (
            f"订单 {order_count} 笔 | 回执 {submit_count} 笔"
            if (order_count or submit_count)
            else "等待第一条订单和成交回执"
        )
        result_risk_value = risk_lamp
        result_risk_accent = risk_note
        result_next_value = gate_headline
        result_next_accent = next_action_accent
        _set_label_text(window.broker_result_metric_labels["stage"], result_stage_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["stage"], result_stage_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["status"], result_status_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["status"], result_status_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["risk"], result_risk_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["risk"], result_risk_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["next"], result_next_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["next"], result_next_accent, set_label_text_fn=set_label)

    if hasattr(window, "broker_replay_event_labels"):
        submission_records = list(getattr(window, "order_submission_records", []) or [])
        latest_event = submission_records[-1] if submission_records else None
        previous_event = submission_records[-2] if len(submission_records) >= 2 else None
        if latest_event is not None:
            latest_symbol = str(latest_event.get("symbol", "") or "")
            latest_name = window._stock_name_for_symbol(latest_symbol) if latest_symbol else "最新回执"
            current_value = f"{latest_name} | {window._display_fill_status(latest_event.get('fill_status', ''))}"
            current_accent = (
                f"{window._display_action(latest_event.get('side', ''))} | "
                f"{latest_event.get('price', '--')} x {latest_event.get('quantity', '--')} | "
                f"{window._display_order_status(latest_event.get('order_status', ''))} / {window._display_fill_status(latest_event.get('fill_status', ''))}\n"
                f"下一步 {gate_headline} | {next_action_accent}\n点击看当前回执"
            )
        elif order_count:
            current_value = "待回执"
            current_accent = f"已生成 {order_count} 笔委托，等待第一条回执\n下一步 {gate_headline} | {next_action_accent}\n点击聚焦当前节点"
        elif focus_symbol:
            current_value = focus_stock_name
            current_accent = f"当前焦点已同步，等待回执事件\n下一步 {gate_headline} | {next_action_accent}\n点击聚焦当前节点"
        else:
            current_value = "待回执"
            current_accent = "提交后这里会定位当前节点\n下一步 先从机会池或交易计划生成第一批委托\n点击聚焦当前节点"

        if previous_event is not None:
            previous_symbol = str(previous_event.get("symbol", "") or "")
            previous_name = window._stock_name_for_symbol(previous_symbol) if previous_symbol else "上一条"
            previous_value = previous_name
            previous_accent = (
                f"{window._display_order_status(previous_event.get('order_status', ''))} / "
                f"{window._display_fill_status(previous_event.get('fill_status', ''))}\n点击回看上一条"
            )
        else:
            previous_value = "暂无上一条"
            previous_accent = "这里会保留上一条对照\n点击后定位上一条回执"

        if blockers:
            exception_value = "阻塞"
            exception_accent = f"{blockers[0]}\n点击去阻塞入口"
        elif warnings:
            exception_value = "预警"
            exception_accent = f"{warnings[0]}\n点击定位预警"
        elif latest_event is not None and str(latest_event.get("failure_reason", "") or "").strip():
            exception_value = "异常"
            exception_accent = f"{str(latest_event.get('failure_reason', '') or '').strip()}\n点击定位异常回执"
        else:
            exception_value = "无异常"
            exception_accent = "失败或偏差会在这里前移\n点击后优先去阻塞入口"

        _set_label_text(window.broker_replay_event_labels["current"], current_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["current"], current_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_labels["previous"], previous_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["previous"], previous_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_labels["exception"], exception_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["exception"], exception_accent, set_label_text_fn=set_label)
        exception_active = bool(blockers or warnings or (latest_event is not None and str(latest_event.get("failure_reason", "") or "").strip()))
        if hasattr(window, "_set_replay_event_card_state_v1"):
            current_tone = "watch" if (latest_event is not None or order_count or focus_symbol) else "idle"
            if blockers or warnings:
                current_tone = "risk"
            window._set_replay_event_card_state_v1("current", active=bool(latest_event is not None or focus_symbol or order_count), tone=current_tone)
            window._set_replay_event_card_state_v1("previous", active=bool(previous_event is not None), tone="watch" if previous_event is not None else "idle")
            window._set_replay_event_card_state_v1("exception", active=exception_active, tone="risk" if exception_active else "idle")
        if hasattr(window, "_update_replay_action_buttons_v1"):
            window._update_replay_action_buttons_v1(
                current_enabled=bool(latest_event is not None or focus_symbol or order_count),
                current_tooltip="定位当前回执，并同步当前节点主控卡。",
                previous_enabled=bool(previous_event is not None),
                previous_tooltip=(f"回看上一条：{previous_value}" if previous_event is not None else "上一条回执尚未产生。"),
                exception_enabled=exception_active,
                exception_tooltip=exception_accent.split("\n", 1)[0] if exception_active else "当前没有异常回执，将退回阻塞入口。",
            )

    if hasattr(window, "broker_recap_metric_labels"):
        recap_verdict_value = "继续复核" if (submit_count or order_count) else "待复盘"
        if blockers:
            recap_verdict_value = "禁止提交"
        elif warnings:
            recap_verdict_value = "继续复核"
        recap_verdict_accent = (
            f"回执 {submit_count} | 风险 {risk_lamp}"
            if submit_count
            else ("当前没有新增执行偏差" if not order_count else f"待提交 {order_count} | 风险 {risk_lamp}")
        )
        recap_mainline_value = review_status
        recap_mainline_accent = (
            f"{first_mainline_row.get('theme', '--')} | {first_mainline_row.get('status', '--')}"
            if first_mainline_row
            else "等待主线、回执和成交联动"
        )
        recap_quality_value = "待回写" if not submit_count else ("待成交" if warnings else "已回写")
        if blockers:
            recap_quality_value = "有偏差"
        recap_quality_accent = portfolio_detail or ("等待价格、数量和成交状态回写" if not submit_count else f"组合 {portfolio_status} | {risk_label}档")
        recap_action_value = "先看回执" if submit_count else ("先生成委托" if not order_count else "提交确认")
        if blockers:
            recap_action_value = "先处理阻塞"
        recap_action_accent = next_action_accent
        _set_label_text(window.broker_recap_metric_labels["verdict"], recap_verdict_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["verdict"], recap_verdict_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["mainline"], recap_mainline_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["mainline"], recap_mainline_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["quality"], recap_quality_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["quality"], recap_quality_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["action"], recap_action_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["action"], recap_action_accent, set_label_text_fn=set_label)

    status_text = (
            f"交易流程：已生成 {order_count} 笔待提交委托，下一步进确认弹窗完成提交。"
        if order_count
        else (
            "交易流程：已有成交回执，可在下方继续回看执行偏差。"
            if submit_count
            else (
                f"交易流程：已同步 {focus_stock_name}，下一步先生成这只票的委托链路。"
                if focus_symbol
                else "交易流程：先从机会池生成委托链路，再进入提交确认流程。"
            )
        )
    )
    if hasattr(window, "broker_execution_text") and hasattr(window.broker_execution_text, "toPlainText"):
        current = window.broker_execution_text.toPlainText().strip()
        if (not current) or current.startswith("交易流程：") or "生成盘中计划后" in current or "生成委托链路后" in current:
            _set_plain_text(
                window.broker_execution_text,
                "\n".join(
                    [
                        status_text,
                        "",
                        "盘中流程",
                        "1. 从机会池选中焦点股票，生成委托链路。",
                        "2. 在下单确认弹窗中核对账户、价格、仓位与风险。",
                        "3. 提交后自动聚焦最新回执，并同步到成交回顾与复盘区。",
                    ]
                ),
                set_text_fn=set_text,
            )

    detail_status_label = getattr(window, "broker_detail_status_label", None)
    if detail_status_label is not None and hasattr(detail_status_label, "setText"):
        if order_count > 0:
            detail_text = "执行明细已折叠，先看焦点委托、阶段判断和风险闸门。"
        elif focus_symbol:
            detail_text = f"执行明细已折叠，当前先围绕 {focus_stock_name} 生成委托链路，再看焦点委托和风险闸门。"
        else:
            detail_text = "执行明细已折叠，先从机会池同步焦点股票，再生成委托链路。"
        _set_label_text(detail_status_label, detail_text, set_label_text_fn=set_label)


def refresh_workspace_status_labels(
    window,
    *,
    workspace_badge_text_fn,
    broker_status_banner_text_fn,
    orders_default_focus_text: str,
    trade_plan_default_focus_text: str,
    recommend_default_focus_text: str,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    if hasattr(window, "top_badge"):
        current_name = window._workspace_name_for_index(window.tabs.currentIndex()) if hasattr(window, "tabs") else "龙头主控台"
        _set_label_text(
            window.top_badge,
            workspace_badge_text_fn(
                current_name,
                scan_count=len(getattr(window, "scan_rows", []) or []),
                watch_count=getattr(window, "watchlist_widget", None).count() if hasattr(window, "watchlist_widget") else 0,
                monitor_count=getattr(window, "monitor_table", None).rowCount() if hasattr(window, "monitor_table") else 0,
                board_count=getattr(window, "board_table", None).rowCount() if hasattr(window, "board_table") else 0,
                board_monitor_count=getattr(window, "board_monitor_table", None).rowCount() if hasattr(window, "board_monitor_table") else 0,
                pool_count=len(getattr(window, "daily_pool_rows", []) or []),
                plan_count=len(getattr(getattr(window, "current_trade_plan", None), "decisions", []) or []),
                pending_orders=len(getattr(window, "order_intents", []) or []),
                submitted_orders=len(getattr(window, "order_submission_records", []) or []),
            ),
            set_label_text_fn=set_label,
        )

    if hasattr(window, "_refresh_shell_header"):
        window._refresh_shell_header()
    if hasattr(window, "_refresh_live_workspace_summary_panels"):
        window._refresh_live_workspace_summary_panels()
    if hasattr(window, "_refresh_workspace_focus_banners"):
        window._refresh_workspace_focus_banners()

    if hasattr(window, "broker_status_banner"):
        pending_orders = len(getattr(window, "order_intents", []) or [])
        submitted_orders = len(getattr(window, "order_submission_records", []) or [])
        summary = getattr(window, "last_broker_execution_summary", {}) or {}
        blockers = list(summary.get("blockers", []) or [])
        warnings = list(summary.get("warnings", []) or [])
        banner_text = broker_status_banner_text_fn(
            pending_orders=pending_orders,
            submitted_orders=submitted_orders,
            blockers=blockers,
            warnings=warnings,
        )
        _set_label_text(window.broker_status_banner, banner_text, set_label_text_fn=set_label)
        if hasattr(window.broker_status_banner, "setToolTip"):
            try:
                if window.broker_status_banner.toolTip() != banner_text:
                    window.broker_status_banner.setToolTip(banner_text)
            except Exception:
                pass

    if hasattr(window, "orders_focus_label") and not getattr(window, "order_intents", []):
        _set_label_text(window.orders_focus_label, orders_default_focus_text, set_label_text_fn=set_label)
    if hasattr(window, "trade_plan_focus_label") and not getattr(getattr(window, "current_trade_plan", None), "decisions", []):
        _set_label_text(window.trade_plan_focus_label, trade_plan_default_focus_text, set_label_text_fn=set_label)
    if hasattr(window, "daily_pool_focus_label") and not getattr(window, "daily_pool_rows", []):
        _set_label_text(window.daily_pool_focus_label, recommend_default_focus_text, set_label_text_fn=set_label)


def refresh_shell_header_status(
    window,
    *,
    build_shell_status_snapshot_fn,
    set_shell_chip_fn,
    set_label_text_fn=None,
) -> None:
    current_name = window._workspace_name_for_index(window.tabs.currentIndex()) if hasattr(window, "tabs") else "龙头主控台"
    if hasattr(window, "shell_workspace_chip"):
        set_shell_chip_fn(window.shell_workspace_chip, current_name)

    trade_plan = getattr(window, "current_trade_plan", None)
    trade_decisions = list(getattr(trade_plan, "decisions", []) or [])
    pending_orders = len(getattr(window, "order_intents", []) or [])
    submitted_orders = len(getattr(window, "order_submission_records", []) or [])
    pool_count = len(getattr(window, "daily_pool_rows", []) or [])
    blockers = list((getattr(window, "last_broker_execution_summary", {}) or {}).get("blockers", []))
    warnings = list((getattr(window, "last_broker_execution_summary", {}) or {}).get("warnings", []))
    market_running = window._is_job_running("market_refresh")
    scan_running = window._is_job_running("scan_universe")
    shell_snapshot = build_shell_status_snapshot_fn(
        market_data_source=str(getattr(window, "market_data_source", "unknown") or "unknown"),
        last_market_success_at=str(getattr(window, "last_market_success_at", "") or ""),
        last_market_error=str(getattr(window, "last_market_error", "") or ""),
        dashboard_auto=bool(hasattr(window, "dashboard_auto_refresh_checkbox") and window.dashboard_auto_refresh_checkbox.isChecked()),
        scanner_auto=bool(hasattr(window, "auto_refresh_checkbox") and window.auto_refresh_checkbox.isChecked()),
        market_refresh_running=bool(market_running),
        scan_running=bool(scan_running),
        last_job_status=str(getattr(window, "last_job_status", "idle") or "idle"),
        last_job_name=str(getattr(window, "last_job_name", "") or ""),
        trade_decisions_count=len(trade_decisions),
        pending_orders=pending_orders,
        submitted_orders=submitted_orders,
        pool_count=pool_count,
        blockers=blockers,
        warnings=warnings,
        last_job_finished_at=str(getattr(window, "last_job_finished_at", "") or ""),
    )
    if hasattr(window, "shell_market_chip"):
        set_shell_chip_fn(window.shell_market_chip, shell_snapshot["market_value"])
    if hasattr(window, "shell_refresh_chip"):
        set_shell_chip_fn(window.shell_refresh_chip, shell_snapshot["refresh_value"])
    if hasattr(window, "shell_runtime_chip"):
        set_shell_chip_fn(window.shell_runtime_chip, shell_snapshot["runtime_value"])
    if hasattr(window, "shell_pulse_label"):
        _set_label_text(window.shell_pulse_label, shell_snapshot["pulse_headline"], set_label_text_fn=set_label_text_fn)
        if hasattr(window.shell_pulse_label, "setToolTip"):
            window.shell_pulse_label.setToolTip(shell_snapshot["pulse_headline"])
    if hasattr(window, "shell_pulse_hint"):
        _set_label_text(window.shell_pulse_hint, shell_snapshot["next_step"], set_label_text_fn=set_label_text_fn)
        if hasattr(window.shell_pulse_hint, "setToolTip"):
            window.shell_pulse_hint.setToolTip(shell_snapshot["next_step"])
    if hasattr(window, "shell_pulse_meta"):
        _set_label_text(window.shell_pulse_meta, shell_snapshot["meta_text"], set_label_text_fn=set_label_text_fn)
        if hasattr(window.shell_pulse_meta, "setToolTip"):
            window.shell_pulse_meta.setToolTip(shell_snapshot["meta_text"])


def _scanner_focus_symbol(window, *, symbol: str = "") -> str:
    target = str(symbol or "").strip()
    if target:
        return target
    if hasattr(window, "_selected_symbol_from_monitor_table"):
        try:
            target = str(window._selected_symbol_from_monitor_table() or "").strip()
        except Exception:
            target = ""
        if target:
            return target
    if hasattr(window, "_selected_symbol_from_watchlist"):
        try:
            target = str(window._selected_symbol_from_watchlist() or "").strip()
        except Exception:
            target = ""
        if target:
            return target
    if hasattr(window, "_selected_symbol_from_summary_table"):
        try:
            target = str(window._selected_symbol_from_summary_table() or "").strip()
        except Exception:
            target = ""
        if target:
            return target
    if hasattr(window, "_selected_symbol_from_scan"):
        try:
            target = str(window._selected_symbol_from_scan() or "").strip()
        except Exception:
            target = ""
        if target:
            return target
    return str(getattr(window, "active_symbol", "") or "").strip()


def refresh_workspace_focus_banners(window) -> None:
    target_symbol = getattr(window, "active_symbol", "") or ""
    if not target_symbol and hasattr(window, "_selected_symbol_from_watchlist"):
        target_symbol = window._selected_symbol_from_watchlist() or ""
    if not target_symbol and hasattr(window, "_selected_board_symbol"):
        target_symbol = window._selected_board_symbol() or ""

    stock_name = window._stock_name_for_symbol(target_symbol) if target_symbol else "等待联动"
    stock_id = window._stock_id_for_symbol(target_symbol) if target_symbol else "--"
    recommendation = (
        next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target_symbol), None)
        if target_symbol
        else None
    )
    scan_row = (
        next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == target_symbol), None)
        if target_symbol
        else None
    )
    tone = window._focus_banner_tone(symbol=target_symbol, recommendation=recommendation, scan_row=scan_row)

    if hasattr(window, "scanner_focus_banner"):
        scanner_target_symbol = _scanner_focus_symbol(window)
        scanner_stock_name = window._stock_name_for_symbol(scanner_target_symbol) if scanner_target_symbol else "绛夊緟鑱斿姩"
        scanner_stock_id = window._stock_id_for_symbol(scanner_target_symbol) if scanner_target_symbol else "--"
        scanner_recommendation = (
            next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == scanner_target_symbol), None)
            if scanner_target_symbol
            else None
        )
        scanner_scan_row = (
            next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == scanner_target_symbol), None)
            if scanner_target_symbol
            else None
        )
        scanner_tone = window._focus_banner_tone(symbol=scanner_target_symbol, recommendation=scanner_recommendation, scan_row=scanner_scan_row)
        scan_count = window.scan_table.rowCount() if hasattr(window, "scan_table") else 0
        watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
        text = (
            f"扫描焦点：{stock_name} ({stock_id} / {target_symbol}) | 扫描 {scan_count} | 观察 {watch_count}"
            if target_symbol
            else "扫描焦点：等待从扫描榜、观察池或盘中监控联动标的"
        )
        window._set_focus_banner_state(window.scanner_focus_banner, tone if target_symbol else "idle", text)
        scanner_text = (
            f"扫描焦点：{scanner_stock_name} ({scanner_stock_id} / {scanner_target_symbol}) | 扫描 {scan_count} | 观察 {watch_count}"
            if scanner_target_symbol
            else "扫描焦点：等待从扫描榜、观察池或盘中监控联动标的"
        )
        window._set_focus_banner_state(window.scanner_focus_banner, scanner_tone if scanner_target_symbol else "idle", scanner_text)

    if hasattr(window, "board_focus_banner"):
        candidate_count = window.board_table.rowCount() if hasattr(window, "board_table") else 0
        monitor_count = window.board_monitor_table.rowCount() if hasattr(window, "board_monitor_table") else 0
        text = (
            f"打板焦点：{stock_name} ({stock_id} / {target_symbol}) | 候选 {candidate_count} | 监控 {monitor_count}"
            if target_symbol
            else "打板焦点：等待扫描页或机会池同步强势候选"
        )
        window._set_focus_banner_state(window.board_focus_banner, tone if target_symbol else "idle", text)

    if hasattr(window, "detail_focus_banner"):
        signal_count = window.signal_table.rowCount() if hasattr(window, "signal_table") else 0
        trade_count = window.trades_table.rowCount() if hasattr(window, "trades_table") else 0
        text = (
            f"复盘焦点：{stock_name} ({stock_id} / {target_symbol}) | 信号 {signal_count} | 成交 {trade_count}"
            if target_symbol
            else "复盘焦点：等待扫描、机会池或涨停策略同步单票标的"
        )
        window._set_focus_banner_state(window.detail_focus_banner, tone if target_symbol else "idle", text)


def update_cross_workspace_focus_labels(window, symbol: str) -> None:
    if not symbol:
        return
    stock_name = window._stock_name_for_symbol(symbol)
    stock_id = window._stock_id_for_symbol(symbol)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == symbol), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(symbol)
    submission_hit = any(str(item.get("symbol", "") or "") == symbol for item in getattr(window, "order_submission_records", []))
    set_label = getattr(window, "_set_label_text_if_changed", None)

    if hasattr(window, "daily_pool_focus_label"):
        action_text = window._display_action(getattr(recommendation, "action", "WATCH")) if recommendation is not None else "观察"
        _set_label_text(window.daily_pool_focus_label, f"当前焦点：{stock_name} ({stock_id} / {symbol}) | 动作 {action_text} | 已联动计划与交易", set_label_text_fn=set_label)
    if hasattr(window, "scan_summary_label"):
        watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
        _set_label_text(window.scan_summary_label, f"扫描状态：当前联动 {stock_name} ({stock_id}) | 观察池 {watch_count} | 已同步推荐/打板/交易", set_label_text_fn=set_label)
    if hasattr(window, "broker_status_banner"):
        broker_suffix = "已同步提交记录" if submission_hit else "等待生成或提交委托"
        _set_label_text(window.broker_status_banner, f"交易状态：当前联动 {stock_name} ({stock_id}) | {broker_suffix}", set_label_text_fn=set_label)
    if hasattr(window, "orders_focus_label"):
        _set_label_text(window.orders_focus_label, f"委托动作面板 / 委托焦点：{stock_name} ({stock_id}) | 已同步机会池与执行链路", set_label_text_fn=set_label)
    if hasattr(window, "board_focus_label"):
        board_text = (
            f"打板焦点：{stock_name} ({stock_id}) | {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']}"
            if board_candidate is not None
            else f"打板焦点：{stock_name} ({stock_id}) | 等待候选或监控联动"
        )
        _set_label_text(window.board_focus_label, board_text, set_label_text_fn=set_label)


def refresh_recommend_focus_status(
    window,
    current,
    *,
    recommend_default_status_text: str,
    recommend_default_focus_text: str,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    if current is None:
        if hasattr(window, "recommend_status_label"):
            total = len(getattr(window, "daily_pool_rows", []) or [])
            text = f"推荐台状态：候选 {total} | 计划待生成 | 执行待联动。" if total else recommend_default_status_text
            _set_label_text(window.recommend_status_label, text, set_label_text_fn=set_label)
        if hasattr(window, "daily_pool_focus_label"):
            _set_label_text(window.daily_pool_focus_label, recommend_default_focus_text, set_label_text_fn=set_label)
        if hasattr(window, "_refresh_workspace_status_labels"):
            window._refresh_workspace_status_labels()
        return

    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    action_label = window._display_action(getattr(current, "action", "WATCH"))
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
    strategy_execution_label = str(getattr(current, "strategy_execution_quality_label", "") or "").strip()
    strategy_execution_score = float(getattr(current, "strategy_execution_quality_score", 1.0) or 1.0)
    execution_state = str((getattr(window, "execution_status_by_symbol", {}) or {}).get(getattr(current, "symbol", ""), "待观察") or "待观察")
    role_name = window._display_mainline_role(getattr(current, "mainline_role", "") or "") or "待确认"

    if hasattr(window, "recommend_status_label"):
        status_text = (
            f"推荐台状态：焦点 {current.stock_name} | 主线 {theme_name} | 动作 {action_label} | "
            f"执行 {execution_state} | 准备 {readiness:.1f} | 置信 {confidence:.1f}"
        )
        if strategy_execution_label:
            status_text = f"{status_text} | 战法 {strategy_execution_label} {strategy_execution_score:.2f}"
        _set_label_text(window.recommend_status_label, status_text, set_label_text_fn=set_label)

    if hasattr(window, "daily_pool_focus_label"):
        focus_text = (
            f"Desk Focus：{current.stock_name} ({current.stock_id} / {current.symbol}) | "
            f"{getattr(current, 'opportunity_tier', '') or '待确认'} | 主线 {theme_name} | 角色 {role_name} | 执行 {execution_state}"
        )
        if strategy_execution_label in {"执行承压", "执行失真"}:
            focus_text = f"{focus_text} | 战法 {strategy_execution_label}"
        _set_label_text(window.daily_pool_focus_label, focus_text, set_label_text_fn=set_label)

    if hasattr(window, "_refresh_workspace_status_labels"):
        window._refresh_workspace_status_labels()


def refresh_recommendation_focus_panels(
    window,
    current,
    *,
    recommendation_focus_lines_fn,
    recommendation_strategy_name_fn,
) -> None:
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    set_label = getattr(window, "_set_label_text_if_changed", None)
    if current is None:
        if hasattr(window, "recommend_dispatch_text") and callable(set_text):
            set_text(window.recommend_dispatch_text, "先看结论，再看分发顺序。\n刷新后这里会显示送审节奏、核心标的和优先队列。")
        if hasattr(window, "recommend_focus_review_text") and callable(set_text):
            set_text(window.recommend_focus_review_text, "先看结论、位置和风险。\n选中一只股票后，这里会显示单票审查摘要。")
        if hasattr(window, "recommend_queue_text") and callable(set_text):
            set_text(window.recommend_queue_text, "待审、已审和失败队列会集中显示在这里。")
        if hasattr(window, "_refresh_recommend_story_panels"):
            window._refresh_recommend_story_panels(None)
        if hasattr(window, "_refresh_recommend_focus_status"):
            window._refresh_recommend_focus_status(None)
        return

    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    action_label = window._display_action(getattr(current, "action", "WATCH"))
    opportunity = getattr(current, "opportunity_tier", "") or "待确认"
    catalyst = getattr(current, "catalyst", "") or "量价共振 + 主力净流入"
    rationale = getattr(current, "rationale", "") or "等待更清晰的主线信号。"
    next_focus = getattr(current, "next_focus", "") or "盯住主线强度、量能承接和资金回流。"
    risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
    confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    strategy_execution_label = str(getattr(current, "strategy_execution_quality_label", "") or "").strip()
    strategy_execution_score = float(getattr(current, "strategy_execution_quality_score", 1.0) or 1.0)
    strategy_execution_summary = str(getattr(current, "strategy_execution_review_summary", "") or "").strip()

    if hasattr(window, "recommend_dispatch_text") and callable(set_text):
        dispatch_lines = [
            f"分发标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
            f"主线：{theme_name} | 动作：{action_label} | 分层：{opportunity}",
            f"送审优先级：执行准备 {readiness:.1f} / 置信 {confidence:.1f}",
            f"催化：{catalyst}",
            f"分发建议：{next_focus}",
        ]
        if strategy_execution_label:
            dispatch_lines.append(f"战法执行：{strategy_execution_label} {strategy_execution_score:.2f}")
            if strategy_execution_summary:
                dispatch_lines.append(f"降权解释：{strategy_execution_summary}")
        set_text(window.recommend_dispatch_text, "\n".join(dispatch_lines))

    if hasattr(window, "recommend_focus_review_text") and callable(set_text):
        review_lines = [
            f"单票审查：{current.stock_name}",
            f"总分 {float(getattr(current, 'total_score', 0.0) or 0.0):.1f} | 风险 {risk_flag} | 主策略 {recommendation_strategy_name_fn(current)}",
        ]
        review_lines.extend(recommendation_focus_lines_fn(current))
        review_lines.append(f"核心理由：{rationale}")
        if strategy_execution_label:
            review_lines.append(f"战法执行：{strategy_execution_label} {strategy_execution_score:.2f}")
            if strategy_execution_summary:
                review_lines.append(f"执行解释：{strategy_execution_summary}")
        set_text(window.recommend_focus_review_text, "\n".join(review_lines))

    if hasattr(window, "recommend_queue_text") and callable(set_text):
        buy_rows = [item for item in getattr(window, "daily_pool_rows", [])[:5] if getattr(item, "action", "") == "BUY"]
        watch_rows = [item for item in getattr(window, "daily_pool_rows", [])[:5] if getattr(item, "action", "") == "WATCH"]
        queue_lines = [
            f"当前前排：{current.stock_name} | {action_label}",
            f"待执行队列：{', '.join(item.stock_name for item in buy_rows[:3]) or '暂无可直接执行标的'}",
            f"观察队列：{', '.join(item.stock_name for item in watch_rows[:3]) or '暂无观察标的'}",
            f"风险提示：{risk_flag} | 失效条件：{getattr(current, 'invalidation_reason', '') or '跌破防守位或主线切换时重新评估'}",
        ]
        set_text(window.recommend_queue_text, "\n".join(queue_lines))

    if hasattr(window, "recommend_focus_metric_labels"):
        metric_values = {
            "symbol": (current.stock_name, f"{current.stock_id} / {current.symbol}"),
            "theme": (theme_name, f"主线位次 {getattr(current, 'mainline_rank', 0) or '--'}"),
            "action": (action_label, f"执行准备 {readiness:.1f}"),
            "execution": ("待处理" if getattr(current, "action", "") in {"BUY", "WATCH"} else "复核中", f"风险 {risk_flag}"),
        }
        for key, (value, accent) in metric_values.items():
            if key in window.recommend_focus_metric_labels:
                _set_label_text(window.recommend_focus_metric_labels[key], value, set_label_text_fn=set_label)
            if hasattr(window, "recommend_focus_metric_accents") and key in window.recommend_focus_metric_accents:
                _set_label_text(window.recommend_focus_metric_accents[key], accent, set_label_text_fn=set_label)

    if hasattr(window, "_refresh_recommend_focus_cards"):
        window._refresh_recommend_focus_cards(current)
    if hasattr(window, "_refresh_recommend_story_panels"):
        window._refresh_recommend_story_panels(current)
    if hasattr(window, "_refresh_recommend_focus_status"):
        window._refresh_recommend_focus_status(current)


def refresh_recommend_bucket_panels(window, row=None) -> None:
    current = row or window._selected_daily_pool_recommendation()
    trade_plan = getattr(window, "current_trade_plan", None)
    decisions = list(getattr(trade_plan, "decisions", []) or [])
    position_advice = list(getattr(window, "current_position_advice", []) or [])
    buy_rows = [item for item in decisions if str(getattr(item, "action", "") or "").upper() == "BUY"]
    watch_rows = [item for item in getattr(window, "daily_pool_rows", []) if str(getattr(item, "action", "") or "").upper() == "WATCH"]
    risk_rows = [item for item in position_advice if str(getattr(item, "action", "") or "").upper() in {"SELL", "REDUCE"}]
    if not any(hasattr(window, name) for name in ("recommend_core_bucket_text", "recommend_watch_bucket_text", "recommend_risk_bucket_text")):
        return

    signature = (
        (
            str(getattr(current, "symbol", "") or ""),
            str(getattr(current, "stock_id", "") or ""),
            str(getattr(current, "stock_name", "") or ""),
            str(getattr(current, "action", "") or ""),
            str(getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or ""),
            str(getattr(current, "opportunity_tier", "") or ""),
            round(float(getattr(current, "execution_readiness", 0.0) or 0.0), 1) if current is not None else 0.0,
            str(getattr(current, "catalyst", "") or ""),
            str(getattr(current, "next_focus", "") or ""),
            str(getattr(current, "mainline_risk_flag", "") or ""),
            str(getattr(current, "invalidation_reason", "") or ""),
            str(getattr(current, "mainline_flow_signal", "") or ""),
            str(getattr(current, "mainline_stage", "") or ""),
        )
        if current is not None
        else ("empty",)
    )
    signature += (
        tuple(
            (
                str(getattr(item, "symbol", "") or ""),
                str(getattr(item, "stock_id", "") or ""),
                str(getattr(item, "stock_name", "") or ""),
                str(getattr(item, "action", "") or ""),
                round(float(getattr(item, "position_pct", 0.0) or 0.0), 4),
                round(float(getattr(item, "planned_price", getattr(item, "entry_price", 0.0)) or 0.0), 4),
                round(float(getattr(item, "stop_price", 0.0) or 0.0), 4),
                round(float(getattr(item, "target_price", 0.0) or 0.0), 4),
                str(getattr(item, "reason", "") or getattr(item, "rationale", "") or ""),
            )
            for item in buy_rows[:1]
        ),
        tuple((str(getattr(item, "symbol", "") or ""), str(getattr(item, "stock_name", "") or "")) for item in watch_rows[:3]),
        len(watch_rows),
        tuple(
            (
                str(getattr(item, "symbol", "") or ""),
                str(getattr(item, "stock_id", "") or ""),
                str(getattr(item, "stock_name", "") or ""),
                str(getattr(item, "action", "") or ""),
                str(getattr(item, "mainline_flow_signal", "") or ""),
                str(getattr(item, "mainline_stage", "") or ""),
                str(getattr(item, "reason", "") or getattr(item, "rationale", "") or ""),
            )
            for item in risk_rows[:3]
        ),
        len(risk_rows),
    )
    if getattr(window, "_recommend_bucket_panels_signature_v1", None) == signature:
        return
    window._recommend_bucket_panels_signature_v1 = signature

    set_text = getattr(window, "_set_plain_text_if_changed", None)
    if hasattr(window, "recommend_core_bucket_text") and callable(set_text):
        if buy_rows:
            top = buy_rows[0]
            lines = [
                "主线前排执行桶",
                f"优先标的：{getattr(top, 'stock_name', '') or window._stock_name_for_symbol(getattr(top, 'symbol', ''))} ({getattr(top, 'stock_id', '') or window._stock_id_for_symbol(getattr(top, 'symbol', ''))})",
                f"计划动作：{window._display_action(getattr(top, 'action', 'BUY'))} | 仓位 {getattr(top, 'position_pct', 0.0):.0%}",
                f"计划价格：{getattr(top, 'planned_price', getattr(top, 'entry_price', 0.0)) or 0.0:.2f} | 止损 {getattr(top, 'stop_price', 0.0) or 0.0:.2f} | 目标 {getattr(top, 'target_price', 0.0) or 0.0:.2f}",
                f"执行理由：{getattr(top, 'reason', '') or getattr(top, 'rationale', '') or '优先处理主线前排。'}",
            ]
        elif current is not None and str(getattr(current, "action", "") or "").upper() == "BUY":
            lines = [
                "主线前排执行桶",
                f"候选标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
                f"主线：{getattr(current, 'mainline_tag', '') or getattr(current, 'theme_name', '') or '待确认'} | 执行准备 {getattr(current, 'execution_readiness', 0.0):.1f}",
                f"预案：可优先送审，确认量能承接后进入执行中控。",
                f"催化：{getattr(current, 'catalyst', '') or '等待资金与主线共振。'}",
            ]
        else:
            lines = ["主线前排执行桶", "当前没有直接执行的新仓计划。", "先看机会池前排和交易计划刷新结果。"]
        set_text(window.recommend_core_bucket_text, "\n".join(lines))

    if hasattr(window, "recommend_watch_bucket_text") and callable(set_text):
        if current is not None:
            lines = [
                "观察池",
                f"当前焦点：{current.stock_name} ({current.stock_id} / {current.symbol})",
                f"观察动作：{window._display_action(getattr(current, 'action', 'WATCH'))} | 分层 {getattr(current, 'opportunity_tier', '') or '待确认'}",
                f"下一步：{getattr(current, 'next_focus', '') or '继续看主线强度、量能回流和分时承接。'}",
                f"备选观察：{', '.join(item.stock_name for item in watch_rows[:3]) or '暂无其他观察标的'}",
            ]
        else:
            lines = [
                "观察池",
                "当前结论：继续复核 | 观察名单待生成",
                f"下一步：先生成机会池，再更新观察名单。当前观察数量：{len(watch_rows)}",
            ]
        set_text(window.recommend_watch_bucket_text, "\n".join(lines))

    if hasattr(window, "recommend_risk_bucket_text") and callable(set_text):
        if risk_rows:
            top = risk_rows[0]
            symbol = getattr(top, "symbol", "")
            lines = [
                "风险池",
                f"优先处理：{getattr(top, 'stock_name', '') or window._stock_name_for_symbol(symbol)} ({getattr(top, 'stock_id', '') or window._stock_id_for_symbol(symbol)})",
                f"动作：{window._display_action(getattr(top, 'action', 'REDUCE'))} | 主线 {getattr(top, 'mainline_flow_signal', '') or '待确认'} / {getattr(top, 'mainline_stage', '') or '待确认'}",
                f"原因：{getattr(top, 'reason', '') or getattr(top, 'rationale', '') or '主线走弱或触发风控条件。'}",
                f"风险队列：{', '.join((getattr(item, 'stock_name', '') or window._stock_name_for_symbol(getattr(item, 'symbol', ''))) for item in risk_rows[:3])}",
            ]
        elif current is not None:
            lines = [
                "风险池",
                f"焦点风险：{getattr(current, 'mainline_risk_flag', '') or '待评估'} | 失效条件：{getattr(current, 'invalidation_reason', '') or '跌破防守位或主线切换。'}",
                f"当前主线：{getattr(current, 'mainline_flow_signal', '') or '待确认'} / {getattr(current, 'mainline_stage', '') or '待确认'}",
                "若盘中出现切换预警，优先减仓或回观察状态。",
            ]
        else:
            lines = [
                "风险池",
                "当前结论：继续复核 | 当前没有新增风险处理任务。",
                "下一步：导入持仓或生成计划后，这里会优先展示卖出 / 减仓建议。",
            ]
        set_text(window.recommend_risk_bucket_text, "\n".join(lines))


def refresh_recommend_story_panels(window, current=None) -> None:
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    if current is None:
        if hasattr(window, "daily_pool_text") and hasattr(window.daily_pool_text, "toPlainText") and not window.daily_pool_text.toPlainText().strip():
            _set_plain_text(
                window.daily_pool_text,
                "综合机会池\n当前结论：继续复核\n风险：机会池待生成，焦点票尚未锁定\n下一步：先刷新市场并生成第一批候选。",
                set_text_fn=set_text,
            )
        if hasattr(window, "strategy_path_text") and hasattr(window.strategy_path_text, "toPlainText") and not window.strategy_path_text.toPlainText().strip():
            _set_plain_text(
                window.strategy_path_text,
                "主线推演\n当前结论：继续复核\n风险：主线轮动与优先级尚未确认\n下一步：先确认主线，再决定动作。",
                set_text_fn=set_text,
            )
        if hasattr(window, "_refresh_recommend_bucket_panels"):
            window._refresh_recommend_bucket_panels(None)
        return

    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    role_name = getattr(current, "mainline_role", "") or ""
    flow_signal = getattr(current, "mainline_flow_signal", "") or "待确认"
    stage_name = getattr(current, "mainline_stage", "") or "待确认"
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    next_focus = getattr(current, "next_focus", "") or "继续盯主线强度、量能承接和回流节奏。"
    invalidation = getattr(current, "invalidation_reason", "") or "跌破防守位或主线切换时重新评估。"

    if hasattr(window, "daily_pool_text"):
        lines = [
            "综合机会池",
            f"结论：{current.stock_name} | {window._display_action(getattr(current, 'action', 'WATCH'))} | 总分 {current.total_score:.1f}",
            f"风险：{theme_name} | {stage_name} | {getattr(current, 'mainline_risk_flag', '--') or '--'}",
            f"下一步：{(next_focus or getattr(current, 'catalyst', '') or '继续盯主线与量价')[:22]}",
        ]
        _set_plain_text(window.daily_pool_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "strategy_path_text"):
        lines = [
            "主线推演",
            f"结论：{theme_name} | {window._display_mainline_role(role_name)} | {flow_signal}",
            f"风险：窗口 {readiness:.1f} | {invalidation[:18]}",
            f"下一步：{next_focus[:22]}",
        ]
        _set_plain_text(window.strategy_path_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "_refresh_recommend_bucket_panels"):
        window._refresh_recommend_bucket_panels(current)


def refresh_recommend_focus_cards(
    window,
    current,
    *,
    recommendation_strategy_name_fn,
    recommendation_decision_score_fn,
) -> None:
    if current is None:
        return

    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    strategy_name = recommendation_strategy_name_fn(current)
    action_label = window._display_action(getattr(current, "action", "WATCH"))
    execution_state = str((getattr(window, "execution_status_by_symbol", {}) or {}).get(getattr(current, "symbol", ""), "待观察") or "待观察")
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    flow_signal = getattr(current, "mainline_flow_signal", "") or "待确认"
    stage_name = getattr(current, "mainline_stage", "") or "待确认"
    risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
    next_focus = getattr(current, "next_focus", "") or "继续跟踪主线强度、量能承接和资金回流。"
    catalyst = getattr(current, "catalyst", "") or "量价共振 + 资金回流"

    if hasattr(window, "recommend_summary_cards"):
        window.recommend_summary_cards["logic"].set_data(
            theme_name,
            f"{current.stock_name} | {window._display_mainline_role(getattr(current, 'mainline_role', '') or '')} | 总分 {current.total_score:.1f}",
        )
        window.recommend_summary_cards["plan"].set_data(
            action_label,
            f"执行 {execution_state} | 准备 {readiness:.1f} | {strategy_name}",
        )
        window.recommend_summary_cards["pulse"].set_data(
            flow_signal,
            f"阶段 {stage_name} | 风险 {risk_flag}",
        )
        window.recommend_summary_cards["holding"].set_data(
            "下一动作",
            next_focus,
        )

    if hasattr(window, "priority_cards"):
        window.priority_cards["theme"].set_data(
            f"{getattr(current, 'mainline_window_score', 0.0):.1f}",
            f"焦点: {theme_name}",
            f"{window._display_mainline_role(getattr(current, 'mainline_role', '') or '')} | 风险 {risk_flag}",
        )
        window.priority_cards["strategy"].set_data(
            f"{strategy_name}",
            f"焦点: {current.stock_name}",
            "主打法与当前焦点一致，优先核对催化和位置。",
        )
        window.priority_cards["focus"].set_data(
            f"{recommendation_decision_score_fn(current):.1f}",
            f"焦点: {current.stock_name}",
            f"{action_label} | {theme_name} | 准备 {readiness:.1f}",
        )

    if hasattr(window, "action_flow_cards"):
        window.action_flow_cards["BUY"].set_data(
            window.action_flow_cards["BUY"].count_label.text(),
            f"焦点: {current.stock_name}" if getattr(current, "action", "") == "BUY" else f"焦点: {window.action_flow_cards['BUY'].focus_label.text().replace('焦点: ', '')}",
            "确认买点后推进送审。" if getattr(current, "action", "") == "BUY" else window.action_flow_cards["BUY"].note_label.text(),
        )
        window.action_flow_cards["WATCH"].set_data(
            window.action_flow_cards["WATCH"].count_label.text(),
            f"焦点: {current.stock_name}" if getattr(current, "action", "") == "WATCH" else window.action_flow_cards["WATCH"].focus_label.text(),
            "继续盯承接、量能和扩散。" if getattr(current, "action", "") == "WATCH" else window.action_flow_cards["WATCH"].note_label.text(),
        )
        if getattr(current, "action", "") in {"REDUCE", "SELL"}:
            key = "SELL" if getattr(current, "action", "") == "SELL" else "REDUCE"
            window.action_flow_cards[key].set_data(
                window.action_flow_cards[key].count_label.text(),
                f"焦点: {current.stock_name}",
                "纪律触发后优先处理。" if key == "SELL" else "先降风险，再决定是否继续。",
            )

    if hasattr(window, "alert_cards"):
        window.alert_cards["theme"].set_data(stage_name, f"主线 {theme_name} | 信号 {flow_signal}")
        window.alert_cards["leader"].set_data(
            window._display_mainline_role(getattr(current, "mainline_role", "") or ""),
            f"焦点标的：{current.stock_name} | 龙头级别 {window._display_leader_level(getattr(current, 'leader_level', '') or '')}",
        )
        window.alert_cards["strategy"].set_data(strategy_name, f"动作 {action_label} | 催化 {catalyst[:12]}")
        window.alert_cards["action"].set_data(action_label, f"下一步 {next_focus[:18]}")


def refresh_recommendation_focus_panel_overlay(
    window,
    current,
    *,
    build_hype_logic_lines_fn,
    news_confidence_label_fn,
    primary_headline: str,
    primary_detail: str,
) -> None:
    review_widget = getattr(window, "recommend_focus_review_text", None)
    action_button = getattr(window, "recommend_news_source_button", None)
    detail_button = getattr(window, "recommend_news_detail_button", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    set_label = getattr(window, "_set_label_text_if_changed", None)

    if review_widget is None or not hasattr(review_widget, "toPlainText"):
        setattr(window, "_recommend_focus_panel_signature_v39", ("missing-review",))
        if hasattr(window, "_update_news_action_button"):
            window._update_news_action_button(action_button, None)
        if hasattr(window, "_update_news_detail_button"):
            window._update_news_detail_button(detail_button, None)
        if hasattr(window, "_refresh_ai_review_panel"):
            window._refresh_ai_review_panel(None)
        return

    if current is None:
        empty_signature = ("empty",)
        if getattr(window, "_recommend_focus_panel_signature_v39", None) == empty_signature:
            return
        setattr(window, "_recommend_focus_panel_signature_v39", empty_signature)
        if hasattr(window, "_update_news_action_button"):
            window._update_news_action_button(action_button, None)
        if hasattr(window, "_update_news_detail_button"):
            window._update_news_detail_button(detail_button, None)
        if hasattr(window, "_refresh_ai_review_panel"):
            window._refresh_ai_review_panel(None)
        return

    execution_state = str(getattr(current, "execution_status", "") or "待观察")
    base_lines = review_widget.toPlainText().splitlines()
    if "辅助消息面：" in base_lines:
        base_lines = base_lines[: base_lines.index("辅助消息面：")]
    lines = [line for line in base_lines if not line.startswith("首选动作：")]
    symbol = getattr(current, "symbol", "") or ""
    news_loader = getattr(window, "_news_items_for_symbol", None)
    symbol_news = list(news_loader(symbol, limit=2) or []) if callable(news_loader) and symbol else list(getattr(window, "news_catalysts", {}).get(symbol, []) or [])
    profile_loader = getattr(window, "_stock_profile_for_symbol", None)
    profile = profile_loader(symbol) if callable(profile_loader) and symbol else None
    signature = (
        symbol,
        str(getattr(current, "stock_name", "") or ""),
        execution_state,
        primary_headline,
        primary_detail,
        str(getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or ""),
        str(getattr(current, "catalyst", "") or ""),
        str(getattr(current, "rationale", "") or ""),
        str(getattr(current, "next_focus", "") or ""),
        str(getattr(current, "mainline_risk_flag", "") or ""),
        str(getattr(profile, "notes", "") if profile is not None else ""),
        tuple(
            (
                str(getattr(item, "title", "") or ""),
                str(getattr(item, "source", "") or ""),
                str(getattr(item, "published_at", "") or ""),
                str(getattr(item, "summary", "") or ""),
            )
            for item in symbol_news[:2]
        ),
    )
    if getattr(window, "_recommend_focus_panel_signature_v39", None) == signature:
        return
    setattr(window, "_recommend_focus_panel_signature_v39", signature)

    logic_lines = build_hype_logic_lines_fn(
        theme_name=getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "",
        catalyst=getattr(current, "catalyst", "") or "",
        rationale=getattr(current, "rationale", "") or "",
        profile_notes=getattr(profile, "notes", "") if profile is not None else "",
        news_title=(getattr(symbol_news[0], "title", "") if symbol_news else ""),
        next_focus=getattr(current, "next_focus", "") or "",
        risk_flag=getattr(current, "mainline_risk_flag", "") or "",
        confidence_label=news_confidence_label_fn(symbol_news),
    )
    digest_loader = getattr(window, "_news_digest_lines_for_symbol", None)
    news_lines = digest_loader(symbol, limit=2) if callable(digest_loader) and symbol else []
    latest_news = symbol_news[0] if symbol_news else None
    lines.append(f"首选动作：{primary_headline} | {primary_detail}")
    lines.append("辅助消息面：")
    lines.extend(logic_lines)
    lines.append("近期消息：")
    if news_lines:
        lines.extend(news_lines)
    else:
        lines.append("暂无已接入的消息催化，先保留主线逻辑与下一步动作。")
    _set_plain_text(review_widget, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "_update_news_action_button"):
        window._update_news_action_button(action_button, latest_news)
    if hasattr(window, "_update_news_detail_button"):
        window._update_news_detail_button(detail_button, latest_news)

    focus_label = getattr(window, "daily_pool_focus_label", None)
    if focus_label is not None:
        stock_name = getattr(current, "stock_name", "") or symbol
        stock_id = getattr(current, "stock_id", "") or (window._stock_id_for_symbol(symbol) if hasattr(window, "_stock_id_for_symbol") else "--")
        suffix = window._news_focus_context_suffix(symbol) if hasattr(window, "_news_focus_context_suffix") else ""
        tooltip = window._news_focus_context_tooltip(symbol) if hasattr(window, "_news_focus_context_tooltip") else ""
        label_text = (
            window._render_text_with_news_badge(
                f"推荐焦点：{stock_name} ({stock_id} / {symbol}) | 已同步单票审查与消息复核 | 审查 继续复核{suffix}",
                symbol,
            )
            if hasattr(window, "_render_text_with_news_badge")
            else f"推荐焦点：{stock_name} ({stock_id} / {symbol}) | 已同步单票审查与消息复核 | 审查 继续复核{suffix}"
        )
        _set_label_text(
            focus_label,
            label_text,
            set_label_text_fn=set_label,
        )
        if tooltip:
            _set_tooltip(focus_label, f"推荐焦点：{stock_name} ({stock_id} / {symbol}) | 已同步单票审查与消息复核 | 审查 继续复核\n{tooltip}")

    if hasattr(window, "_refresh_ai_review_panel"):
        window._refresh_ai_review_panel(current)


def refresh_recommend_decision_summary_text(
    window,
    current,
    *,
    execution_state: str,
    can_submit: bool,
    can_open_broker: bool,
    primary_headline: str,
    primary_detail: str,
) -> None:
    text_widget = getattr(window, "recommend_decision_summary_text", None)
    if text_widget is None or not hasattr(text_widget, "toPlainText"):
        return

    if current is None:
        setattr(window, "_recommend_decision_summary_text_signature_v38", ("empty",))
        return

    if execution_state == "已提交":
        route_detail = "优先点击“看交易回执”"
    elif execution_state == "已送审":
        route_detail = "优先点击“看送审中”"
    elif execution_state == "提交失败":
        route_detail = "优先点击“复核后重送”或先去复盘页"
    elif (not can_submit) and can_open_broker:
        route_detail = "优先点击“进入交易链路”"
    elif not can_submit:
        route_detail = "优先点击“回看复盘链路”"
    else:
        route_detail = "优先点击“推进送审”"

    lines = [
        line
        for line in text_widget.toPlainText().splitlines()
        if not line.startswith("首选动作：") and not line.startswith("路径建议：")
    ]
    push_button = getattr(window, "recommend_push_focus_button", None)
    detail_button = getattr(window, "recommend_detail_focus_button", None)
    broker_button = getattr(window, "recommend_broker_focus_button", None)
    text_signature = (
        str(getattr(current, "symbol", "") or ""),
        execution_state,
        bool(can_submit),
        bool(can_open_broker),
        primary_headline,
        primary_detail,
        route_detail,
        tuple(lines),
        str(getattr(push_button, "toolTip", lambda: "")() or "").split("首选动作：", 1)[0].strip() if push_button is not None and hasattr(push_button, "toolTip") else "",
        str(getattr(detail_button, "toolTip", lambda: "")() or "").split("首选动作：", 1)[0].strip() if detail_button is not None and hasattr(detail_button, "toolTip") else "",
        str(getattr(broker_button, "toolTip", lambda: "")() or "").split("首选动作：", 1)[0].strip() if broker_button is not None and hasattr(broker_button, "toolTip") else "",
    )
    if getattr(window, "_recommend_decision_summary_text_signature_v38", None) == text_signature:
        return
    setattr(window, "_recommend_decision_summary_text_signature_v38", text_signature)

    insert_at = next((index for index, value in enumerate(lines) if value.startswith("下一步：")), len(lines))
    lines[insert_at:insert_at] = [
        f"首选动作：{primary_headline}",
        f"路径建议：{primary_detail} | {route_detail}",
    ]
    _set_plain_text(text_widget, "\n".join(lines), set_text_fn=getattr(window, "_set_plain_text_if_changed", None))

    if push_button is not None and hasattr(push_button, "toolTip"):
        push_tip = str(push_button.toolTip() or "").split("首选动作：", 1)[0].strip()
        _set_tooltip(push_button, (push_tip + "\n" if push_tip else "") + f"首选动作：{primary_headline}")
    if detail_button is not None and hasattr(detail_button, "toolTip"):
        detail_tip = str(detail_button.toolTip() or "").split("首选动作：", 1)[0].strip()
        _set_tooltip(detail_button, (detail_tip + "\n" if detail_tip else "") + f"首选动作：{primary_headline} | {primary_detail}")
    if broker_button is not None and hasattr(broker_button, "toolTip"):
        broker_tip = str(broker_button.toolTip() or "").split("首选动作：", 1)[0].strip()
        _set_tooltip(broker_button, (broker_tip + "\n" if broker_tip else "") + f"首选动作：{primary_headline}")


def refresh_recommend_decision_summary_buttons(
    window,
    current,
    *,
    execution_state: str,
    can_submit: bool,
    can_open_broker: bool,
    primary_key: str,
    primary_headline: str,
    primary_detail: str,
) -> None:
    if current is None:
        setattr(window, "_recommend_decision_summary_signature_v40", ("empty",))
        return

    push_button = getattr(window, "recommend_push_focus_button", None)
    detail_button = getattr(window, "recommend_detail_focus_button", None)
    broker_button = getattr(window, "recommend_broker_focus_button", None)
    button_specs = {
        "push": (
            push_button,
            "accent" if primary_key == "push" else ("tonal" if can_submit or execution_state in {"已送审", "已提交"} else "ghost"),
        ),
        "detail": (
            detail_button,
            "accent" if primary_key == "detail" else ("tonal" if current is not None else "ghost"),
        ),
        "broker": (
            broker_button,
            "accent" if primary_key == "broker" else ("tonal" if can_open_broker else "ghost"),
        ),
    }
    button_state_signature = (
        str(getattr(current, "symbol", "") or ""),
        execution_state,
        bool(can_submit),
        bool(can_open_broker),
        primary_key,
        primary_headline,
        primary_detail,
        tuple(
            (
                key,
                role,
                str(getattr(button, "toolTip", lambda: "")() or "").split("按钮层级：", 1)[0].strip()
                if button is not None and hasattr(button, "toolTip")
                else "",
            )
            for key, (button, role) in button_specs.items()
        ),
    )
    if getattr(window, "_recommend_decision_summary_signature_v40", None) == button_state_signature:
        return
    setattr(window, "_recommend_decision_summary_signature_v40", button_state_signature)

    priority_map = {"accent": "primary", "tonal": "secondary", "ghost": "tertiary"}
    role_label_map = {"accent": "当前主操作", "tonal": "当前次操作", "ghost": "辅助操作"}
    set_button_role = getattr(window, "_set_button_role", None)
    for _key, (button, role) in button_specs.items():
        if button is None:
            continue
        if callable(set_button_role):
            set_button_role(button, role)
        priority = priority_map.get(role, "tertiary")
        if hasattr(button, "property") and hasattr(button, "setProperty"):
            if button.property("ctaPriority") != priority:
                button.setProperty("ctaPriority", priority)
                if hasattr(button, "style") and callable(button.style):
                    style = button.style()
                    if style is not None:
                        try:
                            style.unpolish(button)
                            style.polish(button)
                        except Exception:
                            pass
                if hasattr(button, "update"):
                    try:
                        button.update()
                    except Exception:
                        pass
        tip = str(button.toolTip() or "").split("按钮层级：", 1)[0].strip() if hasattr(button, "toolTip") else ""
        next_tip = (tip + "\n" if tip else "") + f"按钮层级：{role_label_map.get(role, '辅助操作')} | 首选动作：{primary_headline} | {primary_detail}"
        _set_tooltip(button, next_tip)


def refresh_workspace_action_button_states(
    window,
    *,
    current_recommend,
    decisions: list,
    rows: list,
    pending_exists: bool,
    failed_exists: bool,
) -> None:
    role_label_map = {"accent": "当前主操作", "tonal": "当前次操作", "ghost": "辅助操作"}
    priority_map = {"accent": "primary", "tonal": "secondary", "ghost": "tertiary"}
    set_button_role = getattr(window, "_set_button_role", None)
    set_label = getattr(window, "_set_label_text_if_changed", None)

    has_pool = bool(rows)
    primary_key = ""
    if failed_exists:
        primary_key = "retry"
    elif pending_exists:
        primary_key = "pending"
    elif current_recommend is not None:
        primary_key = "current"
    elif decisions:
        primary_key = "plan"
    elif has_pool:
        primary_key = "priority"

    button_specs = {
        "current": (
            getattr(window, "recommend_to_broker_button", None),
            bool(current_recommend is not None),
            "送审当前焦点" if current_recommend is not None else "先选焦点票",
            "先从机会池选中一只焦点票，再推进送审。",
            f"围绕当前焦点推进送审：{getattr(current_recommend, 'stock_name', '焦点标的')}" if current_recommend is not None else "当前没有焦点票可送审。",
        ),
        "plan": (
            getattr(window, "plan_to_broker_button", None),
            bool(decisions),
            "推进当前计划" if decisions else "等待交易计划",
            "先生成交易计划，再把计划股送入交易链路。",
            f"当前计划 {len(decisions)} 笔，优先把计划股送入交易链路。" if decisions else "当前没有交易计划可推进。",
        ),
        "pending": (
            getattr(window, "focus_pending_button", None),
            bool(pending_exists),
            "优先看待审" if pending_exists else "暂无待审",
            "当前没有待审候选，先刷新机会池。",
            "优先定位待审候选，先处理最靠前的一只。" if pending_exists else "当前没有待审候选。",
        ),
        "retry": (
            getattr(window, "retry_failed_button", None),
            bool(failed_exists),
            "优先复核失败" if failed_exists else "暂无失败",
            "当前没有失败候选需要复核。",
            "先复核最近失败候选，再决定是否重送审。" if failed_exists else "当前没有失败候选。",
        ),
        "priority": (
            getattr(window, "push_priority_button", None),
            bool(has_pool),
            "送审最高优先" if has_pool else "等待机会池",
            "需要先生成机会池，才有最高优先候选。",
            f"当前机会池 {len(rows)} 只，优先送审最前排候选。" if has_pool else "当前还没有机会池可推进。",
        ),
    }

    for key, (button, enabled, active_text, disabled_text, tooltip) in button_specs.items():
        if button is None:
            continue
        _set_enabled(button, enabled)
        _set_label_text(button, active_text, set_label_text_fn=set_label)
        if not enabled:
            _set_label_text(button, disabled_text, set_label_text_fn=set_label)
            role = "ghost"
        else:
            role = "accent" if key == primary_key else "tonal"
        if callable(set_button_role):
            set_button_role(button, role)
        priority = priority_map.get(role, "tertiary")
        if hasattr(button, "property") and hasattr(button, "setProperty"):
            if button.property("ctaPriority") != priority:
                button.setProperty("ctaPriority", priority)
                if hasattr(button, "style") and callable(button.style):
                    style = button.style()
                    if style is not None:
                        try:
                            style.unpolish(button)
                            style.polish(button)
                        except Exception:
                            pass
                if hasattr(button, "update"):
                    try:
                        button.update()
                    except Exception:
                        pass
        _set_tooltip(button, f"按钮层级：{role_label_map.get(role, '辅助操作')} | {tooltip}")

    status_label = getattr(window, "recommend_status_label", None)
    if status_label is not None:
        status_text = ""
        if primary_key == "retry":
            status_text = "推荐状态：先复核失败候选，再决定是否重新送审。"
        elif primary_key == "pending":
            status_text = "推荐状态：先处理待审候选，再进入交易链路。"
        elif primary_key == "current":
            status_text = "推荐状态：当前已有焦点票，优先推进送审。"
        elif primary_key == "plan":
            status_text = "推荐状态：当前先推进交易计划，再同步送审。"
        elif primary_key == "priority":
            status_text = "推荐状态：当前先看最高优先候选，再决定是否送审。"
        if status_text:
            _set_label_text(status_label, status_text, set_label_text_fn=set_label)

    board_candidates = bool(getattr(window, "daily_pool_rows", []) or getattr(window, "scan_rows", []) or [])
    board_specs = {
        "refresh": (
            getattr(window, "board_refresh_button", None),
            True,
            "刷新打板池",
            "主操作：刷新专项候选、监控和复盘联动。",
        ),
        "plan": (
            getattr(window, "board_plan_export_button", None),
            board_candidates,
            "导出盘前计划" if board_candidates else "等待候选计划",
            "次操作：导出涨停策略盘前计划。" if board_candidates else "需要先生成候选或机会池后再导出盘前计划。",
        ),
        "review": (
            getattr(window, "board_review_export_button", None),
            board_candidates,
            "导出收盘复盘" if board_candidates else "等待收盘复盘",
            "辅助操作：导出收盘复盘日报。" if board_candidates else "需要先生成候选或机会池后再导出收盘复盘。",
        ),
    }
    board_role_map = {"refresh": "accent", "plan": "tonal", "review": "ghost"}
    for key, (button, enabled, text, tooltip) in board_specs.items():
        if button is None:
            continue
        _set_enabled(button, enabled if key != "refresh" else True)
        _set_label_text(button, text, set_label_text_fn=set_label)
        role = board_role_map.get(key, "ghost")
        if not enabled and key != "refresh":
            role = "ghost"
        if callable(set_button_role):
            set_button_role(button, role)
        priority = priority_map.get(role, "tertiary")
        if hasattr(button, "property") and hasattr(button, "setProperty"):
            if button.property("ctaPriority") != priority:
                button.setProperty("ctaPriority", priority)
                if hasattr(button, "style") and callable(button.style):
                    style = button.style()
                    if style is not None:
                        try:
                            style.unpolish(button)
                            style.polish(button)
                        except Exception:
                            pass
                if hasattr(button, "update"):
                    try:
                        button.update()
                    except Exception:
                        pass
        _set_tooltip(button, f"按钮层级：{role_label_map.get(role, '辅助操作')} | {tooltip}")

    board_meta_hint = getattr(window, "auto_review_export_checkbox", None)
    if board_meta_hint is not None and hasattr(board_meta_hint, "setToolTip"):
        _set_tooltip(board_meta_hint, "辅助设置：控制 15:05 后是否自动导出复盘日报。")


def refresh_scanner_board_action_feedback(window) -> None:
    set_button_role = getattr(window, "_set_button_role", None)
    focus_symbol = _scanner_focus_symbol(window)
    has_focus = bool(focus_symbol)
    selected_scan_symbol = ""
    if hasattr(window, "_selected_symbol_from_scan"):
        try:
            selected_scan_symbol = str(window._selected_symbol_from_scan() or "").strip()
        except Exception:
            selected_scan_symbol = ""
    selected_watch_symbol = ""
    if hasattr(window, "_selected_symbol_from_watchlist"):
        try:
            selected_watch_symbol = str(window._selected_symbol_from_watchlist() or "").strip()
        except Exception:
            selected_watch_symbol = ""
    scan_count = len(getattr(window, "scan_rows", []) or [])
    watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
    summary_count = len(getattr(window, "backtest_summaries", []) or [])
    monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
    has_pool = bool(getattr(window, "daily_pool_rows", []) or [])
    board_candidate_count = window.board_table.rowCount() if hasattr(window, "board_table") else 0
    board_monitor_count = window.board_monitor_table.rowCount() if hasattr(window, "board_monitor_table") else 0
    stock_name = window._stock_name_for_symbol(focus_symbol) if has_focus and hasattr(window, "_stock_name_for_symbol") else "当前焦点"
    universe_dir = str(getattr(getattr(window, "state", None), "universe_dir", "") or "").strip()
    watchlist_values = list(getattr(getattr(window, "state", None), "watchlist", []) or [])
    scan_focus_name = window._stock_name_for_symbol(selected_scan_symbol) if selected_scan_symbol and hasattr(window, "_stock_name_for_symbol") else "当前扫描焦点"

    def _apply_button(button, *, enabled: bool, tooltip: str, role: str | None = None) -> None:
        if button is None:
            return
        _set_enabled(button, enabled)
        if role and callable(set_button_role):
            set_button_role(button, role)
        _set_tooltip(button, tooltip)

    def _card_button(cards, key: str):
        if not isinstance(cards, dict):
            return None
        card = cards.get(key)
        if not isinstance(card, dict):
            return None
        return card.get("button")

    scanner_open_button = getattr(window, "scanner_open_universe_button", None)
    scanner_sample_button = getattr(window, "scanner_sample_universe_button", None)
    scanner_rescan_button = getattr(window, "scanner_rescan_button", None)
    scanner_add_watch_button = getattr(window, "scanner_add_watch_button", None)
    scanner_remove_watch_button = getattr(window, "scanner_remove_watch_button", None)
    scanner_overview_button = getattr(window, "scanner_overview_button", None)
    scanner_recommend_button = getattr(window, "scanner_recommend_button", None)
    scanner_detail_button = getattr(window, "scanner_detail_button", None)
    scanner_board_button = getattr(window, "scanner_board_button", None)
    scanner_hint_label = getattr(window, "scanner_tool_hint_label", None)

    _apply_button(
        scanner_open_button,
        enabled=True,
        tooltip=(
            f"当前本地目录：{universe_dir}。点击后可以切到新的本地股票目录。"
            if universe_dir
            else "当前还没有保存本地股票目录，点击后先选择一个目录建立扫描链路。"
        ),
        role="tonal",
    )
    _apply_button(
        scanner_sample_button,
        enabled=True,
        tooltip="快速载入示例资料，先把扫描、观察池和盘中监控链路跑起来。",
        role="ghost",
    )
    _apply_button(
        scanner_rescan_button,
        enabled=True,
        tooltip=(
            f"基于当前目录 {universe_dir} 重新扫描，刷新股票池、观察池和盘中监控。"
            if universe_dir
            else "当前还没有保存本地目录，点击后会先让你选目录，再执行重扫。"
        ),
        role="accent",
    )
    can_add_watch = bool(selected_scan_symbol and selected_scan_symbol not in watchlist_values)
    _apply_button(
        scanner_add_watch_button,
        enabled=can_add_watch,
        tooltip=(
            f"把当前扫描焦点 {scan_focus_name} 加入观察池，继续跟踪。"
            if can_add_watch
            else (
                f"{scan_focus_name} 已在观察池，无需重复加入。"
                if selected_scan_symbol
                else "先在扫描榜里选中一只股票，再加入观察池。"
            )
        ),
        role="tonal",
    )
    removable_symbol = selected_scan_symbol or selected_watch_symbol
    _apply_button(
        scanner_remove_watch_button,
        enabled=bool(removable_symbol),
        tooltip=(
            f"把 {window._stock_name_for_symbol(removable_symbol) if removable_symbol and hasattr(window, '_stock_name_for_symbol') else removable_symbol} 从观察池移出。"
            if removable_symbol
            else "先在扫描榜或观察池里选中一只股票，再移出观察池。"
        ),
        role="ghost",
    )
    _apply_button(
        scanner_overview_button,
        enabled=True,
        tooltip=(
            f"带着当前焦点 {stock_name} 去总览看主线、量价和市场位置。"
            if has_focus
            else ("当前已有扫描结果，可先回总览看主线，再回来锁焦点。" if scan_count else "当前没有焦点票，点击后会先去总览页。")
        ),
        role="ghost",
    )
    _apply_button(
        scanner_recommend_button,
        enabled=True,
        tooltip=(
            f"带着当前焦点 {stock_name} 去机会池，继续看分层、计划和送审。"
            if has_focus
            else ("机会池已可用，可以先去看机会分层。" if has_pool else "当前没有焦点票，点击后会先去机会池页。")
        ),
        role="tonal",
    )
    _apply_button(
        scanner_detail_button,
        enabled=True,
        tooltip=(
            f"带着当前焦点 {stock_name} 去复盘，继续核对单票结论与执行偏差。"
            if has_focus
            else "当前没有焦点票，点击后会先去复盘页等待联动。"
        ),
        role="accent",
    )
    _apply_button(
        scanner_board_button,
        enabled=True,
        tooltip=(
            f"带着当前焦点 {stock_name} 去看打板候选、回封质量和专项风险。"
            if has_focus
            else ("当前已有打板候选，可先去专项链路查看。" if (board_candidate_count or board_monitor_count) else "当前没有焦点票，点击后会先去打板页。")
        ),
        role="ghost",
    )
    if scanner_hint_label is not None:
        hint_text = (
            f"当前已形成扫描 {scan_count} 条 / 观察 {watch_count} 只 / 监控 {monitor_count} 条，下一步优先锁定 {stock_name}。"
            if (scan_count or watch_count or monitor_count)
            else "先选本地目录或载入示例资料，建立扫描、观察池与盘中监控三条链路。"
        )
        _set_label_text(scanner_hint_label, hint_text, set_label_text_fn=getattr(window, "_set_label_text_if_changed", None))

    _apply_button(
        getattr(window, "monitor_overview_button", None),
        enabled=bool(has_focus or scan_count or watch_count or monitor_count),
        tooltip=(
            f"带着当前焦点 {stock_name} 回总览，看主线、量价和市场位置。"
            if has_focus
            else ("当前已有扫描链路，可先回总览看主线，再回来锁焦点。" if (scan_count or watch_count or monitor_count) else "先执行扫描或载入样本资料，再回总览做联动。")
        ),
        role="ghost",
    )
    _apply_button(
        getattr(window, "monitor_recommend_button", None),
        enabled=bool(has_focus or has_pool),
        tooltip=(
            f"带着当前焦点 {stock_name} 去机会池，继续看分层、计划和送审。"
            if has_focus
            else ("机会池已可用，可以先去看分层，再回来锁监控焦点。" if has_pool else "先刷新机会池，或先在监控链路锁定一只焦点票。")
        ),
        role="tonal",
    )
    _apply_button(
        getattr(window, "monitor_broker_button", None),
        enabled=has_focus,
        tooltip=(
            f"带着当前焦点 {stock_name} 去交易，继续核对委托、仓位和回执。"
            if has_focus
            else "先在观察池或监控表里锁定一只焦点票，再去交易。"
        ),
        role="accent" if has_focus else "tonal",
    )
    _apply_button(
        getattr(window, "monitor_board_button", None),
        enabled=bool(has_focus or board_candidate_count or board_monitor_count),
        tooltip=(
            f"带着当前焦点 {stock_name} 去看打板候选、回封质量和专项风险。"
            if has_focus
            else (
                f"当前已有打板候选 {board_candidate_count} 只 / 监控 {board_monitor_count} 条，可先去看专项链路。"
                if (board_candidate_count or board_monitor_count)
                else "先锁定监控焦点，或先让涨停策略生成候选。"
            )
        ),
        role="ghost",
    )

    scanner_cards = getattr(window, "scanner_capability_cards", None)
    _apply_button(
        _card_button(scanner_cards, "scan"),
        enabled=bool(scan_count),
        tooltip=f"当前已有 {scan_count} 条扫描结果，可继续回扫描榜锁焦点。" if scan_count else "先执行扫描或载入示例资料，再看扫描榜。",
        role="tonal",
    )
    _apply_button(
        _card_button(scanner_cards, "watch"),
        enabled=bool(watch_count or summary_count or has_focus),
        tooltip=(
            f"观察池 {watch_count} 只 / 回测 {summary_count} 条，继续看焦点切换与留样。"
            if (watch_count or summary_count or has_focus)
            else "先建立观察池或回测摘要，再看观察与留样链路。"
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(scanner_cards, "monitor"),
        enabled=bool(monitor_count or has_focus),
        tooltip=(
            f"当前监控 {monitor_count} 条，继续看动作、信号和跨页去向。"
            if (monitor_count or has_focus)
            else "先形成监控焦点，再看盘中监控链路。"
        ),
        role="accent" if (monitor_count or has_focus) else "tonal",
    )

    watch_cards = getattr(window, "scanner_watch_summary_cards", None)
    _apply_button(
        _card_button(watch_cards, "watch"),
        enabled=bool(watch_count or has_focus),
        tooltip=(
            f"当前观察池 {watch_count} 只，继续看焦点切换和是否继续跟踪。"
            if (watch_count or has_focus)
            else "先把扫描结果编入观察池，再看观察焦点。"
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(watch_cards, "summary"),
        enabled=bool(summary_count),
        tooltip=f"当前已有 {summary_count} 条回测摘要，可继续看样本表现。" if summary_count else "先形成回测摘要，再判断是否继续留样。",
        role="tonal",
    )
    _apply_button(
        _card_button(watch_cards, "monitor"),
        enabled=bool(monitor_count or has_focus),
        tooltip=(
            f"当前监控 {monitor_count} 条，继续看监控动作和跨页跳转。"
            if (monitor_count or has_focus)
            else "先形成监控焦点，再看盘中联动。"
        ),
        role="accent" if (monitor_count or has_focus) else "tonal",
    )

    monitor_cards = getattr(window, "scanner_monitor_summary_cards", None)
    _apply_button(
        _card_button(monitor_cards, "monitor"),
        enabled=bool(monitor_count or has_focus),
        tooltip=(
            f"当前监控 {monitor_count} 条，继续核对动作、信号和监控焦点。"
            if (monitor_count or has_focus)
            else "先形成监控记录，再看监控状态。"
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(monitor_cards, "overview"),
        enabled=bool(has_focus or scan_count),
        tooltip=(
            f"带着当前焦点 {stock_name} 去看总览联动。"
            if has_focus
            else ("当前已有扫描结果，可先回总览看主线，再回来锁焦点。" if scan_count else "先执行扫描，再回总览看市场位置。")
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(monitor_cards, "recommend"),
        enabled=bool(has_focus or has_pool),
        tooltip=(
            f"带着当前焦点 {stock_name} 去机会池，继续核对是否值得推进。"
            if has_focus
            else ("机会池已可用，可以先去看机会分层。" if has_pool else "先刷新机会池，或先锁定一只监控焦点。")
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(monitor_cards, "execution"),
        enabled=has_focus,
        tooltip=(
            f"带着当前焦点 {stock_name} 去交易，继续核对委托与执行去向。"
            if has_focus
            else "先锁定一只监控焦点，再去交易链路。"
        ),
        role="accent" if has_focus else "tonal",
    )

    board_cards = getattr(window, "board_capability_cards", None)
    board_has_any = bool(board_candidate_count or board_monitor_count)
    board_focus_symbol = ""
    if hasattr(window, "_selected_board_symbol"):
        try:
            board_focus_symbol = str(window._selected_board_symbol() or "").strip()
        except Exception:
            board_focus_symbol = ""
    board_focus_symbol = board_focus_symbol or str(getattr(window, "active_symbol", "") or "").strip()
    board_focus_name = window._stock_name_for_symbol(board_focus_symbol) if board_focus_symbol and hasattr(window, "_stock_name_for_symbol") else "当前焦点"

    _apply_button(
        _card_button(board_cards, "candidate"),
        enabled=bool(board_candidate_count or board_focus_symbol),
        tooltip=(
            f"当前已有 {board_candidate_count} 只候选，可继续核对 {board_focus_name} 的计划买点与风险。"
            if (board_candidate_count or board_focus_symbol)
            else "先刷新候选或先锁定焦点票，再看专项候选。"
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(board_cards, "monitor"),
        enabled=bool(board_monitor_count or board_focus_symbol),
        tooltip=(
            f"当前已有 {board_monitor_count} 条回封监控，可继续看 {board_focus_name} 的监控动作。"
            if (board_monitor_count or board_focus_symbol)
            else "先建立回封监控或先锁定焦点票，再看专项监控。"
        ),
        role="tonal",
    )
    _apply_button(
        _card_button(board_cards, "execution"),
        enabled=bool(board_focus_symbol),
        tooltip=(
            f"带着当前焦点 {board_focus_name} 去交易，继续核对委托与执行准备。"
            if board_focus_symbol
            else ("当前已有专项候选，可先锁定一只焦点票再去交易。" if board_has_any else "先刷新候选并锁定焦点票，再去交易。")
        ),
        role="accent" if board_focus_symbol else "tonal",
    )

    plan_button = getattr(window, "board_controls_plan_button", None)
    review_button = getattr(window, "board_controls_review_button", None)
    _apply_button(
        plan_button,
        enabled=board_has_any,
        tooltip=(
            f"当前已有专项候选 {board_candidate_count} 只 / 监控 {board_monitor_count} 条，可导出盘前计划。"
            if board_has_any
            else "先刷新候选或先让专项链路形成焦点，再导出盘前计划。"
        ),
        role="tonal",
    )
    _apply_button(
        review_button,
        enabled=board_has_any,
        tooltip=(
            f"当前已有专项候选 {board_candidate_count} 只 / 监控 {board_monitor_count} 条，可导出收盘复盘。"
            if board_has_any
            else "先刷新候选或先让专项链路形成焦点，再导出收盘复盘。"
        ),
        role="ghost",
    )


def refresh_detail_tool_panel_state(
    window,
    *,
    symbol: str,
    stock_name: str,
    stock_id: str,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_button_role = getattr(window, "_set_button_role", None)

    has_symbol = bool(str(symbol or "").strip())
    history_report = getattr(window, "strategy_history_report", None)
    history_rows = list(getattr(window, "strategy_history_rows", []) or [])
    compare_rows = list(getattr(window, "strategy_history_compare_rows", []) or [])
    selected_strategy = (
        window._selected_strategy_history_name() if hasattr(window, "_selected_strategy_history_name") else ""
    )
    history_count = len(history_rows)
    compare_count = len(compare_rows)

    active_label = getattr(window, "active_symbol_label", None)
    if active_label is not None:
        active_text = (
            f"当前标的：{stock_name} ({stock_id} / {symbol})"
            if has_symbol
            else "当前标的：未选择 | 先从机会池、扫描、交易或导入单票 CSV 建立焦点"
        )
        if history_count > 0:
            active_text = f"{active_text} | 历史战法 {history_count} 组"
        _set_label_text(active_label, active_text, set_label_text_fn=set_label)

    hint_label = getattr(window, "detail_hint_title_label", None)
    if hint_label is not None:
        hint_text = (
            f"复盘提示：已锁定 {stock_name}，先看单票结论与执行偏差；若要看长期纪律，再运行历史战法统计。"
            if has_symbol
            else "复盘提示：先锁定焦点票或导入单票 CSV，再看结论、时间线与历史战法。"
        )
        if history_count > 0:
            hint_text += f" 当前已有 {history_count} 组历史战法统计。"
        _set_label_text(hint_label, hint_text, set_label_text_fn=set_label)

    load_button = getattr(window, "detail_load_csv_button", None)
    backtest_button = getattr(window, "detail_backtest_button", None)
    history_button = getattr(window, "detail_history_button", None)
    compare_button = getattr(window, "detail_compare_history_button", None)
    export_button = getattr(window, "detail_export_history_button", None)

    if load_button is not None:
        _set_enabled(load_button, True)
        if callable(set_button_role):
            set_button_role(load_button, "ghost")
        _set_tooltip(
            load_button,
            "如果当前还没有焦点票，可以先导入单票 CSV；已有焦点时，也可以用外部样本补做复盘。",
        )

    if backtest_button is not None:
        _set_enabled(backtest_button, has_symbol)
        if callable(set_button_role):
            set_button_role(backtest_button, "accent" if has_symbol else "tonal")
        _set_tooltip(
            backtest_button,
            (
                f"围绕当前焦点 {stock_name} 运行单票回测，快速看信号、收益与回撤。"
                if has_symbol
                else "先锁定一只焦点票，或先导入单票 CSV，再运行单票回测。"
            ),
        )

    if history_button is not None:
        _set_enabled(history_button, True)
        if callable(set_button_role):
            set_button_role(history_button, "tonal")
        _set_tooltip(
            history_button,
            (
                f"当前可继续补跑历史战法统计；已载入 {history_count} 组结果。"
                if history_count > 0
                else "不依赖当前焦点票，可直接生成历史战法统计，先看长期纪律与参数表现。"
            ),
        )

    if compare_button is not None:
        compare_ready = history_report is not None
        _set_enabled(compare_button, compare_ready)
        if callable(set_button_role):
            set_button_role(compare_button, "accent" if compare_ready else "ghost")
        _set_tooltip(
            compare_button,
            (
                f"当前已有 {history_count} 组历史结果，可继续生成参数对比；已形成 {compare_count} 条场景结果。"
                if compare_ready
                else "先运行历史战法统计，再做战法参数对比。"
            ),
        )

    if export_button is not None:
        export_ready = history_report is not None
        _set_enabled(export_button, export_ready)
        if callable(set_button_role):
            set_button_role(export_button, "ghost" if export_ready else "ghost")
        _set_tooltip(
            export_button,
            (
                f"导出当前历史战法报表。{selected_strategy or '未锁定战法'}会作为当前导出视角。"
                if export_ready
                else "先运行历史战法统计，再导出历史战法报表。"
            ),
        )


def refresh_detail_empty_state(window) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)

    refresh_detail_tool_panel_state(window, symbol="", stock_name="等待联动", stock_id="--")

    labels = getattr(window, "detail_summary_metric_labels", None)
    accents = getattr(window, "detail_summary_metric_accents", None)
    if labels and accents:
        summary_values = {
            "theme": ("待同步", "等待焦点同步"),
            "execution": ("待执行", "等待委托和回执"),
            "risk": ("待评估", "等待风险与信号联动"),
            "next": ("看信号", "先从机会池、扫描或交易链路建立焦点"),
        }
        for key, (value, accent) in summary_values.items():
            if key in labels:
                _set_label_text(labels[key], value, set_label_text_fn=set_label)
            if key in accents:
                _set_label_text(accents[key], accent, set_label_text_fn=set_label)

    empty_panels = {
        "metrics_text": workbench_empty_panel_copy("metrics_text"),
        "detail_decision_text": workbench_empty_panel_copy("detail_decision_text"),
        "detail_execution_text": workbench_empty_panel_copy("detail_execution_text"),
        "detail_conclusion_text": workbench_empty_panel_copy("detail_conclusion_text"),
    }
    for attr_name, text in empty_panels.items():
        widget = getattr(window, attr_name, None)
        _set_plain_text(widget, text, set_text_fn=set_text)


def refresh_detail_workspace_panels_content(
    window,
    *,
    symbol: str,
    stock_name: str,
    stock_id: str,
    recommendation,
    latest_signal,
    selected_signal,
    selected_trade,
    selected_strategy_name: str,
    selected_strategy_trade,
    order_intent,
    execution_row,
    strategy_history_summary,
    compare_rows: list,
    chart_action_note: dict,
    recommendation_strategy_name_fn,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    note_panel_setter = getattr(window, "_set_note_panel_content_if_changed", None)
    has_history_context = strategy_history_summary is not None or selected_strategy_trade is not None

    def _set_note(widget, text: str, *, highlight_text: str = "", highlight_title: str = "图表联动", highlight_tone: str = "watch") -> None:
        if widget is None:
            return
        if callable(note_panel_setter):
            note_panel_setter(
                widget,
                text,
                highlight_text=highlight_text,
                highlight_title=highlight_title,
                highlight_tone=highlight_tone,
            )
            return
        _set_plain_text(widget, text, set_text_fn=set_text)

    refresh_detail_tool_panel_state(window, symbol=symbol, stock_name=stock_name, stock_id=stock_id)

    if hasattr(window, "detail_summary_metric_labels"):
        theme_value = (
            f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {window._display_action(getattr(recommendation, 'action', 'WATCH'))}"
            if recommendation is not None
            else (f"{window._display_label(getattr(latest_signal, 'label', ''))} / 观察" if latest_signal is not None else "待同步")
        )
        theme_accent = (
            f"主策略 {recommendation_strategy_name_fn(recommendation)} | 分层 {getattr(recommendation, 'opportunity_tier', '') or '待确认'}"
            if recommendation is not None
            else (f"信号评分 {getattr(latest_signal, 'score', '--')}" if latest_signal is not None else "等待焦点同步")
        )
        execution_value = (
            f"{window._display_action(getattr(order_intent, 'side', ''))} / {window._display_order_status(execution_row.get('order_status', '')) if execution_row else '待回执'}"
            if order_intent is not None
            else (f"回执 {window._display_order_status(execution_row.get('order_status', ''))}" if execution_row is not None else "待执行")
        )
        execution_accent = (
            f"{getattr(order_intent, 'price', 0.0):.2f} x {int(getattr(order_intent, 'quantity', 0) or 0)} | {window._display_fill_status(execution_row.get('fill_status', '')) if execution_row else '等待回执'}"
            if order_intent is not None
            else (str(execution_row.get('message', '--')) if execution_row is not None else "等待委托和回执")
        )
        risk_value = (
            str(execution_row.get("failure_reason", "") or "待观察")
            if execution_row is not None
            else ("风险待评估" if recommendation is not None else "待评估")
        )
        risk_accent = (
            f"止损 {(getattr(recommendation, 'stop_price', 0.0) or getattr(recommendation, 'close', 0.0) * 0.95):.2f} | 目标 {(getattr(recommendation, 'target_price', 0.0) or getattr(recommendation, 'close', 0.0) * 1.08):.2f}"
            if recommendation is not None
            else "等待风险与信号联动"
        )
        next_value = "去交易" if (order_intent is not None or execution_row is not None) else "看信号"
        next_accent = (
            getattr(recommendation, "next_focus", "") or "继续看量价和主线"
            if recommendation is not None
            else ("去交易核对委托与提交记录" if execution_row is not None else "先从下方信号表选中一条记录")
        )
        _set_label_text(window.detail_summary_metric_labels["theme"], theme_value, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_accents["theme"], theme_accent, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_labels["execution"], execution_value, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_accents["execution"], execution_accent, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_labels["risk"], risk_value, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_accents["risk"], risk_accent, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_labels["next"], next_value, set_label_text_fn=set_label)
        _set_label_text(window.detail_summary_metric_accents["next"], next_accent, set_label_text_fn=set_label)

    if hasattr(window, "metrics_text"):
        lines = [f"策略摘要：{stock_name} ({stock_id} / {symbol})"]
        if latest_signal is not None and recommendation is None:
            lines.append("当前状态：已同步信号，但计划与执行链路还没完全挂回。")
        elif latest_signal is None and recommendation is None and has_history_context:
            lines.append("当前状态：历史画像已就绪，但今天这只票的信号、计划和执行还没完全联动。")
        if selected_strategy_name:
            lines.append(f"当前历史战法视角：{selected_strategy_name} | 基于 2021 年以来机会池信号的规则化回测收益")
        if latest_signal is not None:
            lines.append(f"当前信号：{getattr(latest_signal, 'date', '--')} | {window._display_label(getattr(latest_signal, 'label', ''))} | 评分 {getattr(latest_signal, 'score', '--')}")
        if recommendation is not None:
            lines.append(
                f"当前计划：{recommendation_strategy_name_fn(recommendation)} | 买 {(getattr(recommendation, 'entry_price', 0.0) or getattr(recommendation, 'close', 0.0)):.2f} | "
                f"止 {(getattr(recommendation, 'stop_price', 0.0) or getattr(recommendation, 'close', 0.0) * 0.95):.2f} | "
                f"目 {(getattr(recommendation, 'target_price', 0.0) or getattr(recommendation, 'close', 0.0) * 1.08):.2f}"
            )
        if strategy_history_summary is not None:
            lines.extend(
                [
                    "",
                    f"历史战法：{getattr(strategy_history_summary, 'strategy_name', '--')}",
                    f"总收益：{float(getattr(strategy_history_summary, 'total_return', 0.0) or 0.0):.2%} | 胜率：{float(getattr(strategy_history_summary, 'win_rate', 0.0) or 0.0):.2%} | 最大回撤：{float(getattr(strategy_history_summary, 'max_drawdown', 0.0) or 0.0):.2%}",
                    f"信号 {int(getattr(strategy_history_summary, 'signal_count', 0) or 0)} | 成交 {int(getattr(strategy_history_summary, 'trade_count', 0) or 0)} | 成交率 {float(getattr(strategy_history_summary, 'filled_ratio', 0.0) or 0.0):.2%} | 平均持有 {float(getattr(strategy_history_summary, 'avg_hold_days', 0.0) or 0.0):.2f} 天",
                    f"收益因子 {float(getattr(strategy_history_summary, 'profit_factor', 0.0) or 0.0):.2f} | 盈亏比 {float(getattr(strategy_history_summary, 'payoff_ratio', 0.0) or 0.0):.2f} | 最大连赢 {int(getattr(strategy_history_summary, 'max_consecutive_wins', 0) or 0)} | 最大连亏 {int(getattr(strategy_history_summary, 'max_consecutive_losses', 0) or 0)}",
                    f"执行画像 {getattr(strategy_history_summary, 'execution_quality_label', '') or '待接实盘'} {float(getattr(strategy_history_summary, 'execution_quality_score', 1.0) or 1.0):.2f} | 样本 {int(getattr(strategy_history_summary, 'execution_sample_count', 0) or 0)}",
                    f"最大单笔收益 {float(getattr(strategy_history_summary, 'best_trade_return', 0.0) or 0.0):.2%} | 最大单笔亏损 {float(getattr(strategy_history_summary, 'worst_trade_return', 0.0) or 0.0):.2%}",
                    f"止盈 {int(getattr(strategy_history_summary, 'target_hits', 0) or 0)} | 止损 {int(getattr(strategy_history_summary, 'stop_hits', 0) or 0)} | 超时 {int(getattr(strategy_history_summary, 'timeout_exits', 0) or 0)}",
                ]
            )
            if compare_rows:
                best_compare = max(compare_rows, key=lambda item: float(item.get("total_return", 0.0) or 0.0))
                worst_compare = min(compare_rows, key=lambda item: float(item.get("total_return", 0.0) or 0.0))
                lines.append(
                    f"参数对比：最佳场景 {best_compare.get('scenario_label', '--')} | 总收益 {float(best_compare.get('total_return', 0.0) or 0.0):.2%} | "
                    f"最长持有 {int(best_compare.get('max_hold_days', 0) or 0)} 天"
                )
                lines.append(
                    f"参数敏感度：最差场景 {worst_compare.get('scenario_label', '--')} | 收益差 "
                    f"{(float(best_compare.get('total_return', 0.0) or 0.0) - float(worst_compare.get('total_return', 0.0) or 0.0)):.2%}"
                )
            if selected_strategy_trade is not None:
                lines.append(
                    f"逐笔焦点：{selected_strategy_trade['stock_name']} | {selected_strategy_trade['entry_date']} -> {selected_strategy_trade['exit_date']} | "
                    f"{selected_strategy_trade['pnl_pct']} | {selected_strategy_trade['exit_reason']}"
                )
        else:
            report = getattr(window, "strategy_history_report", None)
            if report is None:
                lines.extend(["", "历史战法：尚未运行统计", "可点击上方“历史战法统计”，按 2021 年以来机会池信号回放长期表现。"])
            else:
                lines.extend(["", "历史战法：当前标的暂无对应统计", "可先检查该票是否有主策略映射，或看表格中的其他战法表现。"])
        _set_plain_text(window.metrics_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "detail_decision_text"):
        lines = ["单票决策"]
        if recommendation is not None:
            lines.extend(
                [
                    "当前状态：计划已形成，可继续复核主线、价位和是否值得推进。",
                    f"结论：{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | {window._display_action(getattr(recommendation, 'action', 'WATCH'))}",
                    f"风险：买 {(getattr(recommendation, 'entry_price', 0.0) or getattr(recommendation, 'close', 0.0)):.2f} / 止 {(getattr(recommendation, 'stop_price', 0.0) or (getattr(recommendation, 'close', 0.0) * 0.95)):.2f} / 目 {(getattr(recommendation, 'target_price', 0.0) or (getattr(recommendation, 'close', 0.0) * 1.08)):.2f}",
                    f"下一步：{getattr(recommendation, 'next_focus', '') or '继续看主线与承接'}",
                ]
            )
        elif latest_signal is not None:
            lines.extend(
                [
                    "当前状态：已同步信号，但计划与主线决策还没完全形成。",
                    f"结论：{window._display_label(getattr(latest_signal, 'label', ''))} | 评分 {getattr(latest_signal, 'score', '--')}",
                    f"看什么：{getattr(latest_signal, 'reason', '') or '先看信号标签、评分和触发原因'}",
                    "下一步：先回机会池确认主线、计划价位和动作建议，再决定是否值得推进。",
                ]
            )
        else:
            lines.extend(["结论：待同步", "下一步：先从下方信号表选中一条记录。"])
            if has_history_context:
                lines.append("当前状态：只有历史画像，今天这只票的决策链路还没补齐。")
        if selected_signal is not None:
            lines.append(f"焦点：{selected_signal['date']} | {selected_signal['label']} | {selected_signal['score']}")
        if strategy_history_summary is not None:
            lines.append(f"历史：{getattr(strategy_history_summary, 'strategy_name', '--')} | 胜率 {float(getattr(strategy_history_summary, 'win_rate', 0.0) or 0.0):.2%} | 总收益 {float(getattr(strategy_history_summary, 'total_return', 0.0) or 0.0):.2%}")
            lines.append(
                f"质量：收益因子 {float(getattr(strategy_history_summary, 'profit_factor', 0.0) or 0.0):.2f} | 盈亏比 {float(getattr(strategy_history_summary, 'payoff_ratio', 0.0) or 0.0):.2f}"
            )
        if selected_strategy_trade is not None:
            lines.append(f"逐笔：{selected_strategy_trade['stock_name']} | 收益 {selected_strategy_trade['pnl_pct']} | {selected_strategy_trade['exit_reason']}")
        _set_note(
            window.detail_decision_text,
            "\n".join(lines),
            highlight_text=str(chart_action_note.get("decision_text", "") or ""),
            highlight_title=str(chart_action_note.get("title", "图表联动") or "图表联动"),
            highlight_tone=str(chart_action_note.get("tone", "watch") or "watch"),
        )

    if hasattr(window, "detail_execution_text"):
        lines = ["执行联动"]
        if order_intent is not None and execution_row is None:
            lines.append("当前状态：委托建议已生成，但提交与回执还没同步。")
        elif order_intent is not None and execution_row is not None:
            lines.append("当前状态：委托与回执已联动，可直接复核执行偏差。")
        elif order_intent is None and execution_row is not None:
            lines.append("当前状态：回执已同步，但委托建议没有完整挂回当前焦点。")
        elif selected_trade is not None:
            lines.append("当前状态：已有成交回放，但委托与回执链路还没完整挂回。")
        if order_intent is not None:
            lines.extend(
                [
                    f"结论：{window._display_action(getattr(order_intent, 'side', ''))} {getattr(order_intent, 'quantity', 0)} 股 @ {float(getattr(order_intent, 'price', 0.0) or 0.0):.2f}",
                    f"风险：止损 {float(getattr(order_intent, 'stop_price', 0.0) or 0.0):.2f} | 目标 {float(getattr(order_intent, 'target_price', 0.0) or 0.0):.2f}",
                ]
            )
        if execution_row is not None:
            lines.append(f"下一步：{window._display_order_status(execution_row.get('order_status', ''))} / {window._display_fill_status(execution_row.get('fill_status', ''))}")
        elif order_intent is not None:
            lines.append("下一步：去交易核对价格、数量和风控，再决定是否送审或提交。")
        if order_intent is None and execution_row is None:
            lines.extend(["结论：待执行", "下一步：先去交易生成委托建议。"])
        if selected_trade is not None:
            lines.append(f"成交：{selected_trade['entry_price']} -> {selected_trade['exit_price']} | {selected_trade['exit_reason']}")
        if strategy_history_summary is not None:
            lines.append(f"历史纪律：成交率 {float(getattr(strategy_history_summary, 'filled_ratio', 0.0) or 0.0):.2%} | 平均持有 {float(getattr(strategy_history_summary, 'avg_hold_days', 0.0) or 0.0):.2f} 天")
            lines.append(
                f"历史执行：{getattr(strategy_history_summary, 'execution_quality_label', '') or '待接实盘'} "
                f"{float(getattr(strategy_history_summary, 'execution_quality_score', 1.0) or 1.0):.2f} | "
                f"{str(getattr(strategy_history_summary, 'execution_review_summary', '') or '等待真实执行样本补齐。')}"
            )
            lines.append(
                f"连续性：最大连赢 {int(getattr(strategy_history_summary, 'max_consecutive_wins', 0) or 0)} | 最大连亏 {int(getattr(strategy_history_summary, 'max_consecutive_losses', 0) or 0)}"
            )
        if selected_strategy_trade is not None:
            lines.append(
                f"历史逐笔：{selected_strategy_trade['entry_price']} -> {selected_strategy_trade['exit_price']} | "
                f"持有 {selected_strategy_trade['hold_days']} 天 | {selected_strategy_trade['exit_reason']}"
            )
        _set_note(
            window.detail_execution_text,
            "\n".join(lines),
            highlight_text=str(chart_action_note.get("execution_text", "") or ""),
            highlight_title=str(chart_action_note.get("title", "图表联动") or "图表联动"),
            highlight_tone=str(chart_action_note.get("tone", "watch") or "watch"),
        )

    if hasattr(window, "detail_conclusion_text"):
        lines = ["复盘结论"]
        if execution_row is not None:
            lines.append("当前状态：执行链已同步，可以开始沉淀结论。")
        elif recommendation is not None and latest_signal is not None:
            lines.append("当前状态：信号与计划已联动，但还缺执行结果验证。")
        elif latest_signal is not None:
            lines.append("当前状态：先有信号，复盘结论还没形成闭环。")
        elif has_history_context:
            lines.append("当前状态：历史画像已就绪，但今天这只票的实时链路还没完全补齐。")
        if latest_signal is not None:
            lines.append(f"结论：{getattr(latest_signal, 'date', '--')} | {window._display_label(getattr(latest_signal, 'label', ''))}")
        if recommendation is not None:
            lines.append(f"风险：{window._display_action(getattr(recommendation, 'action', 'WATCH'))} | {getattr(recommendation, 'next_focus', '') or '继续观察主线与量能'}")
        if execution_row is not None:
            lines.append(f"下一步：{window._display_order_status(execution_row.get('order_status', ''))} / {window._display_fill_status(execution_row.get('fill_status', ''))}")
        elif recommendation is not None and (order_intent is not None or selected_trade is not None):
            lines.append("下一步：先回交易核对委托或成交，再判断这笔票是否真的执行到位。")
        elif recommendation is not None:
            lines.append("下一步：先去交易核对委托建议，或回机会池补看同主线候选。")
        elif latest_signal is not None:
            lines.append("下一步：先回机会池确认主线与计划，再判断这笔票到底该不该做。")
        elif has_history_context:
            lines.append("下一步：先用历史画像校准预期，再补齐今天的信号、计划和执行链路。")
        else:
            lines.append("下一步：回机会池看同主线候选，或去交易核对委托。")
        if strategy_history_summary is not None:
            lines.append(f"历史战法复盘：{getattr(strategy_history_summary, 'strategy_name', '--')} | 最大回撤 {float(getattr(strategy_history_summary, 'max_drawdown', 0.0) or 0.0):.2%}")
        if selected_strategy_trade is not None:
            lines.append(f"历史逐笔结论：{selected_strategy_trade['stock_name']} | {selected_strategy_trade['pnl_pct']} | {selected_strategy_trade['exit_reason']}")
        _set_note(
            window.detail_conclusion_text,
            "\n".join(lines),
            highlight_text=str(chart_action_note.get("conclusion_text", "") or ""),
            highlight_title=str(chart_action_note.get("title", "图表联动") or "图表联动"),
            highlight_tone=str(chart_action_note.get("tone", "watch") or "watch"),
        )


def refresh_scanner_focus_status(
    window,
    *,
    symbol: str = "",
) -> None:
    summary_label = getattr(window, "scan_summary_label", None)
    if summary_label is None:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    total_scans = len(getattr(window, "scan_rows", []))
    monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
    watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
    scan_warning_count = len(getattr(window, "last_scan_warnings", []) or [])

    if not target:
        text = (
            f"扫描状态：已扫描 {total_scans} 条信号 | 观察池 {watch_count} | 盘中监控 {monitor_count} | 当前结论：继续复核 | 下一步：锁定焦点票。"
            if total_scans
            else SCANNER_DEFAULT_STATUS_TEXT
        )
        tooltip = text
        if scan_warning_count:
            tooltip = f"{text} | 本轮有 {scan_warning_count} 个异常文件已跳过，可在运行日志看详情。"
        _set_label_text(summary_label, text, set_label_text_fn=set_label)
        _set_tooltip(summary_label, tooltip)
        if hasattr(window, "_refresh_scanner_summary_cards"):
            window._refresh_scanner_summary_cards("")
        return

    scan_row = next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    stock_name = window._stock_name_for_symbol(target)
    stock_id = window._stock_id_for_symbol(target)
    if scan_row is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | {window._display_action(getattr(scan_row, 'action', 'WATCH'))} / "
            f"{window._display_label(getattr(scan_row, 'label', 'WATCH'))} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count}"
        )
    elif recommendation is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | 推荐 {window._display_action(getattr(recommendation, 'action', 'WATCH'))} | "
            f"主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | 监控 {monitor_count}"
        )
    else:
        text = f"扫描状态：当前联动 {stock_name} ({stock_id}) | 已同步观察池与盘中监控。"
    tooltip = text
    if scan_warning_count:
        tooltip = f"{text} | 本轮有 {scan_warning_count} 个异常文件已跳过，可在运行日志看详情。"
    _set_label_text(summary_label, text, set_label_text_fn=set_label)
    _set_tooltip(summary_label, tooltip)
    refresh_scanner_board_action_feedback(window)
    if hasattr(window, "_refresh_scanner_summary_cards"):
        window._refresh_scanner_summary_cards(target)


def refresh_scanner_focus_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    labels = getattr(window, "scanner_focus_metric_labels", None)
    accents = getattr(window, "scanner_focus_metric_accents", None)
    if not labels or not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    if not target:
        _set_label_text(labels["symbol"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["symbol"], "等待选中", set_label_text_fn=set_label)
        _set_label_text(labels["signal"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], "等待扫描", set_label_text_fn=set_label)
        _set_label_text(labels["action"], "观察", set_label_text_fn=set_label)
        _set_label_text(accents["action"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(labels["monitor"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)
        return

    scan_row = next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    analyses = list(getattr(window, "universe_analyses", {}).get(target, []))
    latest = next((item for item in reversed(analyses) if getattr(item, "label", "") != "NONE"), analyses[-1] if analyses else None)
    board_candidate = window._board_candidate_snapshot_for_symbol(target)

    _set_label_text(labels["symbol"], window._stock_name_for_symbol(target), set_label_text_fn=set_label)
    _set_label_text(accents["symbol"], f"{window._stock_id_for_symbol(target)} / {target}", set_label_text_fn=set_label)

    if scan_row is not None:
        _set_label_text(labels["signal"], f"{getattr(scan_row, 'score', 0):.1f}", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], window._display_label(getattr(scan_row, "label", "WATCH")), set_label_text_fn=set_label)
    elif latest is not None:
        _set_label_text(labels["signal"], f"{getattr(latest, 'score', 0):.1f}", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], window._display_label(getattr(latest, "label", "WATCH")), set_label_text_fn=set_label)
    else:
        _set_label_text(labels["signal"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], "暂无信号", set_label_text_fn=set_label)

    if recommendation is not None:
        _set_label_text(labels["action"], window._display_action(getattr(recommendation, "action", "WATCH")), set_label_text_fn=set_label)
        _set_label_text(
            accents["action"],
            f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(labels["action"], "观察", set_label_text_fn=set_label)
        _set_label_text(accents["action"], "继续复核", set_label_text_fn=set_label)

    if board_candidate is not None:
        _set_label_text(labels["monitor"], board_candidate.get("trigger_style", "继续复核"), set_label_text_fn=set_label)
        _set_label_text(
            accents["monitor"],
            f"风险 {board_candidate.get('risk_level', '--')} | 分数 {board_candidate.get('board_score', '--')}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(labels["monitor"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)


def refresh_scanner_summary_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    labels = getattr(window, "scanner_summary_metric_labels", None)
    accents = getattr(window, "scanner_summary_metric_accents", None)
    if not labels or not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    scan_count = len(getattr(window, "scan_rows", []))
    watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
    summary_count = len(getattr(window, "backtest_summaries", []))
    monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
    stock_name = window._stock_name_for_symbol(target) if target else ""
    stock_id = window._stock_id_for_symbol(target) if target else ""
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    latest_summary = next((item for item in getattr(window, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(target) if target else None
    board_monitor = window._board_monitor_snapshot_for_symbol(target) if target else None

    _set_label_text(labels["scan"], str(scan_count), set_label_text_fn=set_label)
    _set_label_text(labels["watch"], str(watch_count), set_label_text_fn=set_label)
    _set_label_text(labels["summary"], str(summary_count), set_label_text_fn=set_label)
    _set_label_text(labels["monitor"], str(monitor_count), set_label_text_fn=set_label)

    if not target:
        _set_label_text(accents["scan"], "等待扫描链路 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["watch"], "等待观察池 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["summary"], "等待回测摘要 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)
        return

    _set_label_text(accents["scan"], f"{stock_name} / {stock_id}", set_label_text_fn=set_label)
    if recommendation is not None:
        _set_label_text(
            accents["watch"],
            f"推荐 {window._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(accents["watch"], "观察池已同步焦点 | 继续复核", set_label_text_fn=set_label)
    if latest_summary is not None:
        _set_label_text(accents["summary"], f"回测 {getattr(latest_summary, 'trades', 0)} 笔 / 收益 {getattr(latest_summary, 'total_return', 0.0):.2%}", set_label_text_fn=set_label)
    else:
        _set_label_text(accents["summary"], "等待回测摘要 | 继续复核", set_label_text_fn=set_label)
    if board_candidate is not None:
        _set_label_text(accents["monitor"], f"打板 {board_candidate.get('trigger_style', '--')} / 风险 {board_candidate.get('risk_level', '--')}", set_label_text_fn=set_label)
    elif board_monitor is not None:
        _set_label_text(accents["monitor"], f"监控 {board_monitor.get('monitor_state', '--')} / {board_monitor.get('strength', '--')}", set_label_text_fn=set_label)
    else:
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)
    refresh_scanner_board_action_feedback(window)


def focus_strip_subtitle(status: str, focus: str, next_step: str) -> str:
    status_text = str(status or "").strip() or "--"
    focus_text = str(focus or "").strip() or "--"
    next_text = str(next_step or "").strip() or "--"
    verdict = "继续复核"
    if any(token in status_text for token in ("阻塞", "红灯", "禁止")):
        verdict = "禁止提交"
    elif any(token in status_text for token in ("谨慎", "黄灯")):
        verdict = "谨慎推进"
    return f"当前状态：{status_text} | 当前结论：{verdict} | 焦点：{focus_text} | 下一步：{next_text}"


_ORIGINAL_REFRESH_RECOMMEND_FOCUS_STATUS_V2 = refresh_recommend_focus_status


def refresh_recommend_focus_status(
    window,
    current,
    *,
    recommend_default_status_text: str,
    recommend_default_focus_text: str,
) -> None:
    _ORIGINAL_REFRESH_RECOMMEND_FOCUS_STATUS_V2(
        window,
        current,
        recommend_default_status_text=recommend_default_status_text,
        recommend_default_focus_text=recommend_default_focus_text,
    )
    set_label = getattr(window, "_set_label_text_if_changed", None)

    if current is None:
        if hasattr(window, "recommend_status_label"):
            total = len(getattr(window, "daily_pool_rows", []) or [])
            if total:
                _set_label_text(
                    window.recommend_status_label,
                    f"推荐台状态：候选 {total} | 计划待生成 | 执行待联动 | 当前结论：继续复核 | 下一步：先锁定前排票。",
                    set_label_text_fn=set_label,
                )
        return

    if hasattr(window, "recommend_status_label"):
        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        action_label = window._display_action(getattr(current, "action", "WATCH"))
        execution_state = str((getattr(window, "execution_status_by_symbol", {}) or {}).get(getattr(current, "symbol", ""), "待观察") or "待观察")
        _set_label_text(
            window.recommend_status_label,
            f"推荐台状态：焦点 {current.stock_name} | 主线 {theme_name} | 动作 {action_label} | 执行 {execution_state} | 当前结论：继续复核 | 下一步：先核对主线、计划和送审理由。",
            set_label_text_fn=set_label,
        )

    if hasattr(window, "daily_pool_focus_label"):
        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        role_name = window._display_mainline_role(getattr(current, "mainline_role", "") or "") or "待确认"
        execution_state = str((getattr(window, "execution_status_by_symbol", {}) or {}).get(getattr(current, "symbol", ""), "待观察") or "待观察")
        _set_label_text(
            window.daily_pool_focus_label,
            f"当前焦点：{current.stock_name} ({current.stock_id} / {current.symbol}) | {getattr(current, 'opportunity_tier', '') or '待确认'} | 主线 {theme_name} | 角色 {role_name} | 执行 {execution_state} | 审查 继续复核",
            set_label_text_fn=set_label,
        )


_ORIGINAL_REFRESH_BROKER_ACTION_FLOW_V2 = refresh_broker_action_flow


def refresh_broker_action_flow(
    window,
    *,
    risk_profile_labels: dict[str, str],
    broker_primary_cta_labels_fn,
    broker_primary_cta_tooltips_fn,
) -> None:
    _ORIGINAL_REFRESH_BROKER_ACTION_FLOW_V2(
        window,
        risk_profile_labels=risk_profile_labels,
        broker_primary_cta_labels_fn=broker_primary_cta_labels_fn,
        broker_primary_cta_tooltips_fn=broker_primary_cta_tooltips_fn,
    )
    set_label = getattr(window, "_set_label_text_if_changed", None)
    summary_accents = getattr(window, "broker_summary_metric_accents", None)
    replay_accents = getattr(window, "broker_replay_event_accents", None)

    if isinstance(summary_accents, dict) and "queue" in summary_accents:
        queue_widget = summary_accents["queue"]
        current = getattr(queue_widget, "text", lambda: "")()
        if current == "等待生成第一批委托":
            _set_label_text(queue_widget, "继续复核 | 等待生成第一批委托", set_label_text_fn=set_label)

    if isinstance(replay_accents, dict) and "current" in replay_accents:
        current_widget = replay_accents["current"]
        current_text = getattr(current_widget, "text", lambda: "")()
        if current_text and "等待回执事件" in current_text and "当前结论：" not in current_text:
            _set_label_text(current_widget, f"当前结论：继续复核\n{current_text}", set_label_text_fn=set_label)


def refresh_scanner_focus_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    labels = getattr(window, "scanner_focus_metric_labels", None)
    accents = getattr(window, "scanner_focus_metric_accents", None)
    if not labels or not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    if not target:
        empty_signature = ("empty",)
        if getattr(window, "_scanner_focus_cards_signature_v1", None) == empty_signature:
            return
        setattr(window, "_scanner_focus_cards_signature_v1", empty_signature)
        _set_label_text(labels["symbol"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["symbol"], "等待焦点同步", set_label_text_fn=set_label)
        _set_label_text(labels["signal"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], "等待扫描信号", set_label_text_fn=set_label)
        _set_label_text(labels["action"], "观察", set_label_text_fn=set_label)
        _set_label_text(accents["action"], "等待推荐联动", set_label_text_fn=set_label)
        _set_label_text(labels["monitor"], "待联动", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路", set_label_text_fn=set_label)
        return

    scan_row = next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    latest = next((item for item in reversed(list(getattr(window, "universe_analyses", {}).get(target, []))) if getattr(item, "label", "") != "NONE"), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(target)
    focus_signature = (
        target,
        str(window._stock_name_for_symbol(target) or ""),
        str(window._stock_id_for_symbol(target) or ""),
        str(getattr(scan_row, "action", "") or ""),
        str(getattr(scan_row, "label", "") or ""),
        float(getattr(scan_row, "score", 0.0) or 0.0),
        str(getattr(latest, "label", "") or ""),
        float(getattr(latest, "score", 0.0) or 0.0),
        str(getattr(recommendation, "action", "") or ""),
        str(getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or ""),
        str(getattr(recommendation, "opportunity_tier", "") or ""),
        str(board_candidate.get("trigger_style", "") if board_candidate is not None else ""),
        str(board_candidate.get("risk_level", "") if board_candidate is not None else ""),
        str(board_candidate.get("board_score", "") if board_candidate is not None else ""),
    )
    if getattr(window, "_scanner_focus_cards_signature_v1", None) == focus_signature:
        return
    setattr(window, "_scanner_focus_cards_signature_v1", focus_signature)

    _set_label_text(labels["symbol"], window._stock_name_for_symbol(target), set_label_text_fn=set_label)
    _set_label_text(accents["symbol"], f"{window._stock_id_for_symbol(target)} / {target}", set_label_text_fn=set_label)

    if scan_row is not None:
        _set_label_text(labels["signal"], f"{getattr(scan_row, 'score', 0):.1f}", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], window._display_label(getattr(scan_row, "label", "WATCH")), set_label_text_fn=set_label)
    elif latest is not None:
        _set_label_text(labels["signal"], f"{getattr(latest, 'score', 0):.1f}", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], window._display_label(getattr(latest, "label", "WATCH")), set_label_text_fn=set_label)
    else:
        _set_label_text(labels["signal"], "--", set_label_text_fn=set_label)
        _set_label_text(accents["signal"], "暂无信号", set_label_text_fn=set_label)

    if recommendation is not None:
        _set_label_text(labels["action"], window._display_action(getattr(recommendation, "action", "WATCH")), set_label_text_fn=set_label)
        _set_label_text(
            accents["action"],
            f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(labels["action"], "观察", set_label_text_fn=set_label)
        _set_label_text(accents["action"], "等待机会池联动", set_label_text_fn=set_label)

    if board_candidate is not None:
        _set_label_text(labels["monitor"], board_candidate.get("trigger_style", "待联动"), set_label_text_fn=set_label)
        _set_label_text(
            accents["monitor"],
            f"风险 {board_candidate.get('risk_level', '--')} | 分数 {board_candidate.get('board_score', '--')}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(labels["monitor"], "待联动", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路", set_label_text_fn=set_label)


def refresh_scanner_summary_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    labels = getattr(window, "scanner_summary_metric_labels", None)
    accents = getattr(window, "scanner_summary_metric_accents", None)
    if not labels or not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    scan_count = len(getattr(window, "scan_rows", []))
    watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
    summary_count = len(getattr(window, "backtest_summaries", []))
    monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
    stock_name = window._stock_name_for_symbol(target) if target else ""
    stock_id = window._stock_id_for_symbol(target) if target else ""
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    latest_summary = next((item for item in getattr(window, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(target) if target else None
    board_monitor = window._board_monitor_snapshot_for_symbol(target) if target else None

    summary_signature = (
        target,
        scan_count,
        watch_count,
        summary_count,
        monitor_count,
        str(stock_name),
        str(stock_id),
        str(getattr(recommendation, "action", "") or ""),
        str(getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or ""),
        int(getattr(latest_summary, "trades", 0) or 0),
        float(getattr(latest_summary, "total_return", 0.0) or 0.0),
        str(board_candidate.get("trigger_style", "") if board_candidate is not None else ""),
        str(board_candidate.get("risk_level", "") if board_candidate is not None else ""),
        str(board_monitor.get("monitor_state", "") if board_monitor is not None else ""),
        str(board_monitor.get("strength", "") if board_monitor is not None else ""),
    )
    if getattr(window, "_scanner_summary_cards_signature_v1", None) == summary_signature:
        return
    setattr(window, "_scanner_summary_cards_signature_v1", summary_signature)

    _set_label_text(labels["scan"], str(scan_count), set_label_text_fn=set_label)
    _set_label_text(labels["watch"], str(watch_count), set_label_text_fn=set_label)
    _set_label_text(labels["summary"], str(summary_count), set_label_text_fn=set_label)
    _set_label_text(labels["monitor"], str(monitor_count), set_label_text_fn=set_label)

    if not target:
        _set_label_text(accents["scan"], "等待扫描链路", set_label_text_fn=set_label)
        _set_label_text(accents["watch"], "等待观察池", set_label_text_fn=set_label)
        _set_label_text(accents["summary"], "等待回测摘要", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路", set_label_text_fn=set_label)
        return

    _set_label_text(accents["scan"], f"{stock_name} / {stock_id}", set_label_text_fn=set_label)
    if recommendation is not None:
        _set_label_text(
            accents["watch"],
            f"推荐 {window._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
            set_label_text_fn=set_label,
        )
    else:
        _set_label_text(accents["watch"], "观察池已同步焦点", set_label_text_fn=set_label)
    if latest_summary is not None:
        _set_label_text(accents["summary"], f"回测 {getattr(latest_summary, 'trades', 0)} 笔 / 收益 {getattr(latest_summary, 'total_return', 0.0):.2%}", set_label_text_fn=set_label)
    else:
        _set_label_text(accents["summary"], "等待样本回填", set_label_text_fn=set_label)
    if board_candidate is not None:
        _set_label_text(accents["monitor"], f"打板 {board_candidate.get('trigger_style', '--')} / 风险 {board_candidate.get('risk_level', '--')}", set_label_text_fn=set_label)
    elif board_monitor is not None:
        _set_label_text(accents["monitor"], f"监控 {board_monitor.get('monitor_state', '--')} / {board_monitor.get('strength', '--')}", set_label_text_fn=set_label)
    else:
        _set_label_text(accents["monitor"], "盘中监控联动", set_label_text_fn=set_label)
    refresh_scanner_board_action_feedback(window)


def refresh_submission_focus(window) -> None:
    record = window._selected_submission_record() if hasattr(window, "_selected_submission_record") else None
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    if hasattr(window, "order_result_text"):
        if record is None:
            _set_plain_text(
                window.order_result_text,
                "执行回放\n\n"
                "当前结论：继续复核\n"
                "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                "刷新委托或提交模拟单后，这里会自动切换到最新一条。\n"
        "你也可以先从机会池或涨停策略送审候选，再来这里看执行反馈。",
                set_text_fn=set_text,
            )
        else:
            lines = [
                "执行回放",
                "",
                f"时间：{record.get('timestamp', '--')}",
                f"股票：{window._stock_name_for_symbol(record.get('symbol', ''))} ({window._stock_id_for_symbol(record.get('symbol', ''))} / {record.get('symbol', '--')})",
                f"动作：{window._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
                f"订单状态：{window._display_order_status(record.get('order_status', ''))}",
                f"成交状态：{window._display_fill_status(record.get('fill_status', ''))}",
                f"失败原因：{record.get('failure_reason', '') or '无'}",
                f"反馈信息：{record.get('message', '') or '等待更多反馈'}",
            ]
            _set_plain_text(window.order_result_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_recap_text"):
        if record is None:
            _set_plain_text(
                window.broker_recap_text,
                "成交回顾\n\n"
                "当前结论：待复盘\n"
                "提交后，这里会沉淀通过率、阻塞原因、成交偏差和回看要点。\n"
                "当订单建议生成后，可以在这里快速检查执行质量。",
                set_text_fn=set_text,
            )
        else:
            symbol = record.get("symbol", "")
            recommendation = next((item for item in getattr(window, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
            lines = [
                f"成交回顾：{window._stock_name_for_symbol(symbol)}",
                f"订单状态：{window._display_order_status(record.get('order_status', ''))} | 成交状态：{window._display_fill_status(record.get('fill_status', ''))}",
                f"动作：{window._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
            ]
            if recommendation is not None:
                lines.append(
                    f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
                )
                lines.append(f"推荐动作：{window._display_action(getattr(recommendation, 'action', ''))}")
                lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
            message = record.get("message", "") or ""
            if message:
                lines.append(f"系统反馈：{message}")
            failure_reason = record.get("failure_reason", "") or ""
            if failure_reason:
                lines.append(f"需要处理：{failure_reason}")
            else:
                lines.append("后续动作：可继续看委托明细，或去机会池校验主线和仓位。")
            _set_plain_text(window.broker_recap_text, "\n".join(lines), set_text_fn=set_text)


def refresh_submission_focus_context(
    window,
    *,
    record: dict,
    stock_name: str,
    stock_id: str,
    symbol: str,
    failure_reason: str,
    message: str,
    deviation_snapshot: dict,
    recommendation,
    recommend_context_lines: list[str],
    summary: dict,
    followup: dict,
    repair_hint: dict,
    parameter_alignment: dict,
    resolution_action: dict,
    terminal_brief: dict,
    panel_conclusion: str,
    execution_deck: dict,
    shortcut_copy: dict,
    action_strip: dict,
    execution_tone: str,
) -> None:
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    review_verdict = "禁止提交" if failure_reason else "继续复核"
    review_headline = f"当前结论：{review_verdict}"

    if hasattr(window, "order_result_text"):
        lines = [
            "执行回放 / 说明",
            review_headline,
            f"结论：{panel_conclusion}",
            f"风险：{failure_reason or repair_hint['headline'] or summary['judgement']}",
            f"下一步：{summary['next_step']}",
            f"修正：{repair_hint['headline']} | {resolution_action['target']}",
            f"参数：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
        ]
        if deviation_snapshot.get("has_baseline"):
            lines.append(f"偏差：{deviation_snapshot['note']}")
        _set_plain_text(window.order_result_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_result_metric_labels"):
        result_stage_value = summary["stage"]
        result_stage_accent = f"{record.get('timestamp', '--')} | {stock_name}"
        result_status_value = f"{summary['order_status']} / {summary['fill_status']}"
        result_status_accent = f"{window._display_action(record.get('side', ''))} | {record.get('price', '--')} x {record.get('quantity', '--')}"
        result_risk_value = failure_reason or summary["judgement"]
        result_risk_accent = repair_hint["headline"] if failure_reason else (message or repair_hint["checkpoint"])
        result_next_value = followup["headline"]
        result_next_accent = f"{summary['next_step']} | {resolution_action['target']}"
        _set_label_text(window.broker_result_metric_labels["stage"], result_stage_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["stage"], result_stage_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["status"], result_status_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["status"], result_status_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["risk"], result_risk_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["risk"], result_risk_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_labels["next"], result_next_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_result_metric_accents["next"], result_next_accent, set_label_text_fn=set_label)

    if hasattr(window, "broker_replay_event_labels"):
        submission_records = list(getattr(window, "order_submission_records", []) or [])
        previous_record = None
        if submission_records:
            try:
                current_index = submission_records.index(record)
            except ValueError:
                current_index = len(submission_records) - 1
            if current_index > 0:
                previous_record = submission_records[current_index - 1]
            elif len(submission_records) >= 2:
                previous_record = submission_records[-2]

        current_value = f"{stock_name} | {summary['stage']}"
        current_accent = (
            f"{window._display_action(record.get('side', ''))} | "
            f"{record.get('price', '--')} x {record.get('quantity', '--')} | "
            f"{summary['order_status']} / {summary['fill_status']}\n"
            f"结论 {review_verdict}\n"
            f"下一步 {summary['next_step']} | {resolution_action['target']}\n"
            "点击看当前回执"
        )
        if previous_record is not None:
            previous_symbol = str(previous_record.get("symbol", "") or "")
            previous_name = window._stock_name_for_symbol(previous_symbol) if previous_symbol else "上一条"
            previous_value = previous_name
            previous_accent = (
                f"{window._display_order_status(previous_record.get('order_status', ''))} / "
                f"{window._display_fill_status(previous_record.get('fill_status', ''))}\n"
                "点击回看上一条"
            )
        else:
            previous_value = "暂无上一条"
            previous_accent = "这里会保留上一条对照\n点击后定位上一条回执"
        exception_value = failure_reason or summary["judgement"]
        exception_accent = (
            f"{repair_hint['headline']}\n点击定位异常回执"
            if failure_reason
            else f"{message or repair_hint['checkpoint']}\n点击定位当前风险"
        )
        _set_label_text(window.broker_replay_event_labels["current"], current_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["current"], current_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_labels["previous"], previous_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["previous"], previous_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_labels["exception"], exception_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_replay_event_accents["exception"], exception_accent, set_label_text_fn=set_label)
        exception_active = bool(failure_reason)
        if hasattr(window, "_set_replay_event_card_state_v1"):
            window._set_replay_event_card_state_v1("current", active=True, tone=execution_tone)
            window._set_replay_event_card_state_v1("previous", active=bool(previous_record is not None), tone="watch" if previous_record is not None else "idle")
            window._set_replay_event_card_state_v1("exception", active=exception_active, tone="risk" if exception_active else "idle")
        if hasattr(window, "_update_replay_action_buttons_v1"):
            window._update_replay_action_buttons_v1(
                current_enabled=True,
                current_tooltip=f"看当前回执：{stock_name}",
                previous_enabled=bool(previous_record is not None),
                previous_tooltip=(f"回看上一条：{previous_value}" if previous_record is not None else "上一条回执尚未产生。"),
                exception_enabled=True,
                exception_tooltip=exception_accent.split("\n", 1)[0],
            )

    if hasattr(window, "broker_recap_text"):
        lines = [
            f"成交回顾：{stock_name}",
            review_headline,
            panel_conclusion,
            f"执行阶段：{summary['stage']}",
            f"当前判断：{summary['judgement']}",
            f"动作：{window._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
        ]
        if recommendation is not None:
            lines.append(
                f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
            )
            lines.append(f"推荐动作：{window._display_action(getattr(recommendation, 'action', ''))}")
            lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
        lines.extend(recommend_context_lines)
        lines.append(summary["next_step"])
        lines.append(f"链路建议：{followup['headline']} | {followup['detail']}")
        lines.append(f"处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}")
        lines.append(f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}")
        if deviation_snapshot.get("has_baseline"):
            lines.append(f"执行偏差：{deviation_snapshot['note']}")
        lines.append(f"优先入口：{resolution_action['target']} | {resolution_action['detail']}")
        if message:
            lines.append(f"系统反馈：{message}")
        if failure_reason:
            lines.append(f"需要处理：{failure_reason}")
        elif not deviation_snapshot.get("has_baseline"):
            lines.append("执行偏差：继续观察成交结果，并核对是否偏离原计划的价格和仓位。")
        _set_plain_text(window.broker_recap_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_recap_metric_labels"):
        recap_verdict_value = summary["judgement"]
        recap_verdict_accent = panel_conclusion
        recap_mainline_value = (
            f"{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
            if recommendation is not None
            else "待确认"
        )
        recap_mainline_accent = (
            f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | {getattr(recommendation, 'mainline_role', '') or '待确认'}"
            if recommendation is not None
            else "等待主线与回执联动"
        )
        recap_quality_value = parameter_alignment["headline"]
        recap_quality_accent = deviation_snapshot["note"] if deviation_snapshot.get("has_baseline") else parameter_alignment["detail"]
        recap_action_value = repair_hint["headline"]
        recap_action_accent = f"{resolution_action['target']} | {resolution_action['detail']}"
        _set_label_text(window.broker_recap_metric_labels["verdict"], recap_verdict_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["verdict"], recap_verdict_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["mainline"], recap_mainline_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["mainline"], recap_mainline_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["quality"], recap_quality_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["quality"], recap_quality_accent, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_labels["action"], recap_action_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_recap_metric_accents["action"], recap_action_accent, set_label_text_fn=set_label)

    if hasattr(window, "broker_mainline_review_text"):
        lines = [
            f"主线闸门审查：{stock_name}",
            panel_conclusion,
            f"执行阶段：{summary['stage']} | 链路建议：{followup['headline']}",
        ]
        if recommendation is not None:
            lines.extend(
                [
                    f"主线状态：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                    f"主线角色：{getattr(recommendation, 'mainline_role', '') or '待确认'} | 题材：{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
                    f"推荐动作：{window._display_action(getattr(recommendation, 'action', ''))} | 推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}",
                ]
            )
        else:
            lines.append("主线状态：当前缺少推荐联动，请先结合执行中控和扫描页补齐主线判断。")
        lines.extend(recommend_context_lines)
        lines.append(f"处理建议：{repair_hint['headline']} | {repair_hint['detail']}")
        lines.append(f"参数复核：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}")
        lines.append(f"优先入口：{resolution_action['target']} | {resolution_action['detail']}")
        lines.append(f"复核检查：{repair_hint['checkpoint']}")
        _set_plain_text(window.broker_mainline_review_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_execution_text"):
        lines = [
            "交易流程",
            "",
            panel_conclusion,
            f"当前焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"执行阶段：{summary['stage']}",
            f"状态判断：{summary['judgement']}",
            summary["next_step"],
            *recommend_context_lines,
            f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
            f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
            f"联动建议：{followup['headline']} | {followup['detail']}",
            f"修正路径：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            f"推荐链路：建议前往 {followup['route']} 继续处理。",
        ]
        _set_plain_text(window.broker_execution_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_order_focus_text"):
        lines = [
            execution_deck["headline"],
            "",
            panel_conclusion,
            f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"动作：{window._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
            f"主线：{execution_deck['gate_accent']}",
            f"参数：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
            f"处理：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            f"入口：去{resolution_action['target']} | {resolution_action['detail']}",
        ]
        _set_plain_text(window.broker_order_focus_text, "\n".join(lines), set_text_fn=set_text)

    if hasattr(window, "broker_order_metric_labels"):
        _set_label_text(window.broker_order_metric_labels["symbol"], execution_deck["symbol_value"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["symbol"], execution_deck["symbol_accent"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["gate"], execution_deck["gate_value"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["gate"], execution_deck["gate_accent"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["risk"], execution_deck["risk_value"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["risk"], execution_deck["risk_accent"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["position"], execution_deck["position_value"], set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["position"], execution_deck["position_accent"], set_label_text_fn=set_label)

    if hasattr(window, "broker_stage_label"):
        stage_text = terminal_brief.get("stage", summary["stage"])
        stage_tooltip = "\n".join(
            [
                f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
                f"阶段判断：{summary['judgement']}",
                *recommend_context_lines,
                f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}",
                f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
                f"链路建议：{followup['headline']} | {followup['detail']}",
                f"处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            ]
        )
        _set_label_text(window.broker_stage_label, stage_text, set_label_text_fn=set_label)
        _set_tooltip(window.broker_stage_label, stage_tooltip)

    if hasattr(window, "orders_focus_label"):
        focus_text = f"委托动作面板 / {terminal_brief.get('focus', f'执行焦点：{stock_name}')}"
        focus_tooltip = "\n".join(
            [
                f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
                f"执行阶段：{summary['stage']}",
                *recommend_context_lines,
                f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
                f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
                f"链路建议：{followup['headline']} | {followup['detail']}",
                f"处理建议：{repair_hint['headline']} | {repair_hint['detail']}",
                f"复核检查：{repair_hint['checkpoint']}",
            ]
        )
        _set_label_text(window.orders_focus_label, focus_text, set_label_text_fn=set_label)
        _set_tooltip(window.orders_focus_label, focus_tooltip)

    if hasattr(window, "_set_widget_spotlight_v23"):
        for attr_name in [
            "broker_status_banner",
            "broker_workbench_banner",
            "broker_stage_label",
            "orders_focus_label",
            "execution_table",
            "order_result_text",
            "broker_recap_text",
            "broker_execution_text",
            "broker_mainline_review_text",
        ]:
            window._set_widget_spotlight_v23(getattr(window, attr_name, None), execution_tone)

    if hasattr(window, "broker_status_banner"):
        _set_label_text(window.broker_status_banner, terminal_brief.get("status", summary.get("tooltip", summary["judgement"])), set_label_text_fn=set_label)
        _set_tooltip(
            window.broker_status_banner,
            f"{summary['tooltip']}\n"
            + "\n".join(recommend_context_lines)
            + f"\n参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}\n优先入口：{resolution_action['target']} | {resolution_action['detail']}\n链路建议：{followup['headline']} | {followup['detail']}\n处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
        )
    if hasattr(window, "broker_workbench_banner"):
        _set_label_text(
            window.broker_workbench_banner,
            terminal_brief.get("workbench", terminal_brief.get("status", summary.get("tooltip", summary["judgement"]))),
            set_label_text_fn=set_label,
        )
        _set_tooltip(
            window.broker_workbench_banner,
            f"{summary['tooltip']}\n"
            + "\n".join(recommend_context_lines)
            + f"\n参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}\n优先入口：{resolution_action['target']} | {resolution_action['detail']}\n链路建议：{followup['headline']} | {followup['detail']}\n处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
        )

    detail_status_label = getattr(window, "broker_detail_status_label", None)
    if detail_status_label is not None and not getattr(window, "_qh_broker_detail_visible_v40", False):
        status_text = f"执行明细已折叠，当前优先去{resolution_action['target']}。{resolution_action['detail']}"
        _set_label_text(detail_status_label, status_text, set_label_text_fn=set_label)
        _set_tooltip(detail_status_label, status_text)

    generate_button = getattr(window, "generate_order_suggestions_button", None)
    if generate_button is not None and hasattr(generate_button, "setToolTip"):
        base_tip = f"围绕 {stock_name} 重新生成委托建议前，建议先去{resolution_action['target']}。{resolution_action['button_hint']}"
        _set_tooltip(generate_button, base_tip)

    confirm_button = getattr(window, "confirm_submit_orders_button", None)
    if confirm_button is not None and hasattr(confirm_button, "setToolTip"):
        _set_tooltip(confirm_button, f"{resolution_action['button_hint']}")

    blocker_button = getattr(window, "broker_focus_blocker_button", None)
    if blocker_button is not None and hasattr(blocker_button, "setText"):
        _set_label_text(blocker_button, action_strip.get("blocker_text", "定位阻塞项"), set_label_text_fn=set_label)
        _set_tooltip(blocker_button, shortcut_copy.get("blocker_tooltip", "优先定位需要处理的阻塞或异常回执。"))

    priority_button = getattr(window, "broker_focus_priority_button", None)
    if priority_button is not None and hasattr(priority_button, "setText"):
        _set_label_text(priority_button, action_strip.get("priority_text", "定位优先委托"), set_label_text_fn=set_label)
        _set_tooltip(priority_button, shortcut_copy.get("priority_tooltip", f"优先定位当前执行焦点：{stock_name}。"))


def refresh_broker_order_focus(window, *, orders_default_focus_text: str, position_mainline_brief_fn) -> None:
    if not hasattr(window, "broker_order_focus_text"):
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)
    set_text = getattr(window, "_set_plain_text_if_changed", None)
    intent = window._selected_order_intent() if hasattr(window, "_selected_order_intent") else None
    if intent is None:
        _set_plain_text(
            window.broker_order_focus_text,
            "当前委托详情\n\n"
            "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
    "当前结论：继续复核 | 先在上方选中一条委托建议，再决定是否进确认弹窗提交。",
            set_text_fn=set_text,
        )
        if hasattr(window, "orders_focus_label"):
            _set_label_text(window.orders_focus_label, orders_default_focus_text, set_label_text_fn=set_label)
        if hasattr(window, "broker_order_metric_labels"):
            _set_label_text(window.broker_order_metric_labels["symbol"], "--", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_accents["symbol"], "等待选中", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_labels["gate"], "待审查", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_accents["gate"], "等待主线闸门", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_labels["risk"], "待评估", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_accents["risk"], "等待风险灯", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_labels["position"], "待计算", set_label_text_fn=set_label)
            _set_label_text(window.broker_order_metric_accents["position"], "等待仓位测算", set_label_text_fn=set_label)
        return

    recommendation = next((item for item in getattr(window, "daily_pool_rows", []) if getattr(item, "symbol", "") == intent.symbol), None)
    summary = dict(getattr(window, "last_broker_execution_summary", {}) or {})
    review_snapshot = build_execution_review_snapshot(summary)
    blockers = list(summary.get("blockers", []))
    warnings = list(summary.get("warnings", []))
    portfolio_review = dict(summary.get("portfolio_risk_review", {}) or {})
    portfolio_rows = list(portfolio_review.get("rows", []))
    portfolio_row = next((row for row in portfolio_rows if str(row.get("symbol", "")) == str(getattr(intent, "symbol", ""))), {})
    available_qty = next((getattr(item, "available", None) for item in getattr(window, "holdings", []) if getattr(item, "symbol", "") == intent.symbol), None)
    preview_row = {}
    allowed = True
    side = str(getattr(intent, "side", "") or "").upper()
    quantity = int(getattr(intent, "quantity", 0) or 0)
    estimated_amount = float(getattr(intent, "price", 0.0) or 0.0) * quantity
    if side in {"SELL", "REDUCE"} and available_qty is not None and quantity > int(available_qty):
        preview_row = {"status": "超卖"}
        allowed = False
    risk_lamp = window._broker_risk_lamp_for_intent(intent, recommendation=recommendation) if hasattr(window, "_broker_risk_lamp_for_intent") else "黄灯"
    action_label = window._broker_focus_action_label(intent, risk_lamp, blockers=blockers, warnings=warnings, preview_row=preview_row, allowed=allowed)
    action_hint = window._broker_focus_action_hint(intent, risk_lamp, blockers=blockers, warnings=warnings, preview_row=preview_row, allowed=allowed)
    risk_summary = window._broker_focus_risk_summary(
        intent,
        {"checks": []},
        blockers=blockers,
        warnings=warnings,
        preview_row=preview_row,
        available_qty=available_qty,
    )
    flow_signal = str(getattr(recommendation, "mainline_flow_signal", "") or "待确认")
    stage_label = str(getattr(recommendation, "mainline_stage", "") or "待确认")
    mainline_brief = position_mainline_brief_fn(recommendation) if recommendation is not None else "待确认"
    portfolio_status = str(portfolio_row.get("status", "") or portfolio_review.get("status", "待评估") or "待评估")
    portfolio_detail = str(portfolio_row.get("detail", "") or "")
    loss_ratio = float(portfolio_row.get("loss_ratio", 0.0) or 0.0)
    asset_usage_ratio = float(portfolio_row.get("asset_usage_ratio", 0.0) or 0.0)
    cash_usage_ratio = float(portfolio_row.get("cash_usage_ratio", 0.0) or 0.0)
    side_text = window._display_action(getattr(intent, "side", ""))
    if side == "BUY":
        impact_summary = f"组合影响：{portfolio_status} | 单笔止损 {loss_ratio:.1%} 总资产 | 占用 {asset_usage_ratio:.1%} 资产"
        if cash_usage_ratio > 0:
            impact_summary += f" / {cash_usage_ratio:.1%} 可用资金"
        impact_detail = portfolio_detail or "仓位风险可控，可继续结合主线闸门复核。"
        position_value = f"占用 {estimated_amount:,.0f}"
        position_accent = impact_summary.replace("组合影响：", "")
    elif side in {"SELL", "REDUCE"}:
        impact_summary = f"组合影响：预计释放 {estimated_amount:,.0f} 资金 | 可卖 {available_qty if available_qty is not None else '--'}"
        impact_detail = "优先确认这是止盈或风控动作，避免误卖仍在主线前排的仓位。"
        position_value = f"释放 {estimated_amount:,.0f}"
        position_accent = f"可卖 {available_qty}" if available_qty is not None else "等待持仓同步"
    else:
        impact_summary = "组合影响：待结合委托方向继续评估"
        impact_detail = portfolio_detail or "先完成委托生成，再看仓位与风险预算。"
        position_value = f"{side_text} {quantity}"
        position_accent = impact_detail

    lines = [
        "当前委托动作面板",
        f"结论：{window._stock_name_for_symbol(intent.symbol)} | {side_text} | {action_label}",
        f"风险：主线 {flow_signal} / {stage_label} | {mainline_brief} | {risk_summary}",
        f"下一步：{action_hint}",
        f"审查结论：{review_snapshot.get('verdict', '继续复核')} | {review_snapshot.get('action', '先继续复核后再提交。')}",
        impact_summary,
        f"缓解动作：{impact_detail}",
        f"可卖信息：{'可卖 ' + str(available_qty) if available_qty is not None else '暂无持仓数据'}",
    ]
    _set_plain_text(window.broker_order_focus_text, "\n".join(lines), set_text_fn=set_text)
    if hasattr(window, "orders_focus_label"):
        _set_label_text(
            window.orders_focus_label,
            f"委托动作面板 / 委托焦点：动作建议 {action_label} | 主线 {flow_signal} | 审查 {review_snapshot.get('verdict', '继续复核')}",
            set_label_text_fn=set_label,
        )
    if hasattr(window, "broker_order_metric_labels"):
        _set_label_text(window.broker_order_metric_labels["symbol"], window._stock_name_for_symbol(intent.symbol), set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["symbol"], f"{window._stock_id_for_symbol(intent.symbol)} / {intent.symbol}", set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["gate"], mainline_brief, set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["gate"], f"{flow_signal} / {stage_label}", set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["risk"], risk_lamp, set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["risk"], action_hint, set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_labels["position"], position_value, set_label_text_fn=set_label)
        _set_label_text(window.broker_order_metric_accents["position"], position_accent, set_label_text_fn=set_label)


def update_cross_workspace_focus_labels(window, symbol: str) -> None:
    if not symbol:
        return
    stock_name = window._stock_name_for_symbol(symbol)
    stock_id = window._stock_id_for_symbol(symbol)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == symbol), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(symbol)
    submission_hit = any(str(item.get("symbol", "") or "") == symbol for item in getattr(window, "order_submission_records", []))
    set_label = getattr(window, "_set_label_text_if_changed", None)

    if hasattr(window, "daily_pool_focus_label"):
        action_text = window._display_action(getattr(recommendation, "action", "WATCH")) if recommendation is not None else "观察"
        _set_label_text(
            window.daily_pool_focus_label,
            f"当前焦点：{stock_name} ({stock_id} / {symbol}) | 动作 {action_text} | 已联动计划与交易 | 审查 继续复核",
            set_label_text_fn=set_label,
        )
    if hasattr(window, "scan_summary_label"):
        watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
        _set_label_text(
            window.scan_summary_label,
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | 观察池 {watch_count} | 已同步推荐/打板/交易 | 当前结论：继续复核",
            set_label_text_fn=set_label,
        )
    if hasattr(window, "broker_status_banner"):
        broker_suffix = "已同步提交记录" if submission_hit else "等待生成或提交委托"
        _set_label_text(
            window.broker_status_banner,
            f"交易状态：当前联动 {stock_name} ({stock_id}) | {broker_suffix} | 当前结论：继续复核",
            set_label_text_fn=set_label,
        )
    if hasattr(window, "orders_focus_label"):
        _set_label_text(
            window.orders_focus_label,
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id}) | 已同步机会池与执行链路 | 审查 继续复核",
            set_label_text_fn=set_label,
        )
    if hasattr(window, "board_focus_label"):
        board_text = (
            f"打板焦点：{stock_name} ({stock_id}) | {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} | 审查 继续复核"
            if board_candidate is not None
            else f"打板焦点：{stock_name} ({stock_id}) | 等待候选或监控联动 | 审查 继续复核"
        )
        _set_label_text(window.board_focus_label, board_text, set_label_text_fn=set_label)


def refresh_scanner_focus_status(
    window,
    *,
    symbol: str = "",
) -> None:
    summary_label = getattr(window, "scan_summary_label", None)
    if summary_label is None:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)

    target = _scanner_focus_symbol(window, symbol=symbol)
    total_scans = len(getattr(window, "scan_rows", []))
    monitor_count = window.monitor_table.rowCount() if hasattr(window, "monitor_table") else 0
    watch_count = window.watchlist_widget.count() if hasattr(window, "watchlist_widget") else 0
    scan_warning_count = len(getattr(window, "last_scan_warnings", []) or [])

    if not target:
        text = (
            f"扫描状态：已扫描 {total_scans} 条信号 | 观察池 {watch_count} | 盘中监控 {monitor_count} | 当前结论：继续复核 | 下一步：锁定焦点票。"
            if total_scans
            else SCANNER_DEFAULT_STATUS_TEXT
        )
        tooltip = text
        if scan_warning_count:
            tooltip = f"{text} | 本轮有 {scan_warning_count} 个异常文件已跳过，可在运行日志看详情。"
        _set_label_text(summary_label, text, set_label_text_fn=set_label)
        _set_tooltip(summary_label, tooltip)
        if hasattr(window, "_refresh_scanner_summary_cards"):
            window._refresh_scanner_summary_cards("")
        return

    scan_row = next((row for row in getattr(window, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    stock_name = window._stock_name_for_symbol(target)
    stock_id = window._stock_id_for_symbol(target)
    if scan_row is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | {window._display_action(getattr(scan_row, 'action', 'WATCH'))} / "
            f"{window._display_label(getattr(scan_row, 'label', 'WATCH'))} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count} | 当前结论：继续复核"
        )
    elif recommendation is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | 推荐 {window._display_action(getattr(recommendation, 'action', 'WATCH'))} | "
            f"主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | 监控 {monitor_count} | 当前结论：继续复核"
        )
    else:
        text = f"扫描状态：当前联动 {stock_name} ({stock_id}) | 已同步观察池与盘中监控 | 当前结论：继续复核。"
    tooltip = text
    if scan_warning_count:
        tooltip = f"{text} | 本轮有 {scan_warning_count} 个异常文件已跳过，可在运行日志看详情。"
    _set_label_text(summary_label, text, set_label_text_fn=set_label)
    _set_tooltip(summary_label, tooltip)
    refresh_scanner_board_action_feedback(window)
    if hasattr(window, "_refresh_scanner_summary_cards"):
        window._refresh_scanner_summary_cards(target)


_ORIGINAL_REFRESH_SCANNER_FOCUS_CARDS_V2 = refresh_scanner_focus_cards
_ORIGINAL_REFRESH_SCANNER_SUMMARY_CARDS_V2 = refresh_scanner_summary_cards


def refresh_scanner_focus_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    _ORIGINAL_REFRESH_SCANNER_FOCUS_CARDS_V2(window, symbol=symbol)
    labels = getattr(window, "scanner_focus_metric_labels", None)
    accents = getattr(window, "scanner_focus_metric_accents", None)
    if not labels or not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)
    target = _scanner_focus_symbol(window, symbol=symbol)
    if not target:
        _set_label_text(accents["action"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(labels["monitor"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)
        return

    recommendation = next((row for row in getattr(window, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    board_candidate = window._board_candidate_snapshot_for_symbol(target)
    if recommendation is None:
        _set_label_text(accents["action"], "继续复核", set_label_text_fn=set_label)
    if board_candidate is None:
        _set_label_text(labels["monitor"], "继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)


def refresh_scanner_summary_cards(
    window,
    *,
    symbol: str = "",
) -> None:
    _ORIGINAL_REFRESH_SCANNER_SUMMARY_CARDS_V2(window, symbol=symbol)
    accents = getattr(window, "scanner_summary_metric_accents", None)
    if not accents:
        return
    set_label = getattr(window, "_set_label_text_if_changed", None)
    target = _scanner_focus_symbol(window, symbol=symbol)
    if not target:
        _set_label_text(accents["scan"], "等待扫描链路 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["watch"], "等待观察池 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["summary"], "等待回测摘要 | 继续复核", set_label_text_fn=set_label)
        _set_label_text(accents["monitor"], "等待监控链路 | 审查", set_label_text_fn=set_label)
