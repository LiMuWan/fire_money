from __future__ import annotations

from datetime import datetime
from contextlib import contextmanager
from types import SimpleNamespace

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QApplication, QTableWidgetItem
except ModuleNotFoundError:  # pragma: no cover - enables pure-logic tests without Qt runtime
    Qt = None
    QColor = None

    class QApplication:  # type: ignore[override]
        @staticmethod
        def processEvents() -> None:
            return None

    class QTableWidgetItem:  # type: ignore[override]
        def __init__(self, value="") -> None:
            self._value = value
            self._tooltip = ""

        def setBackground(self, *_args, **_kwargs) -> None:
            return None

        def setForeground(self, *_args, **_kwargs) -> None:
            return None

        def setToolTip(self, value: str) -> None:
            self._tooltip = value

        def toolTip(self) -> str:
            return self._tooltip

        def text(self) -> str:
            return str(self._value)

from quant_hunter.broker import describe_order_intent, summarize_trade_recap
from quant_hunter.broker_status import build_broker_execution_summary
from quant_hunter.risk import RISK_PROFILE_LABELS, risk_profile_brief
from quant_hunter.models import ScanRow
from quant_hunter.reports import _report_mainline_followup_text
from quant_hunter.recommend_status import execution_summary_for_rows
from quant_hunter.theme import display_mainline_role as _shared_display_mainline_role
from quant_hunter.ui_helpers import one_day_hold_grade, one_day_hold_tripwire_metrics, tail_buy_execution_checklist, tail_buy_runtime_panel_lines, tail_buy_runtime_status
from quant_hunter.ui_status import display_fill_status, display_order_status, market_pool_colors, signal_colors, submission_colors, submission_risk_badge_palette_v2, submission_table_snapshot_v2


QT_USER_ROLE = Qt.UserRole if Qt is not None else 0


@contextmanager
def _batched_table_update(table):
    if table is None:
        yield
        return
    previous_updates = table.updatesEnabled() if hasattr(table, "updatesEnabled") else True
    previous_signals = table.blockSignals(True) if hasattr(table, "blockSignals") else False
    sorting_enabled = table.isSortingEnabled() if hasattr(table, "isSortingEnabled") else False
    if hasattr(table, "setSortingEnabled") and sorting_enabled:
        table.setSortingEnabled(False)
    if hasattr(table, "setUpdatesEnabled"):
        table.setUpdatesEnabled(False)
    try:
        yield
    finally:
        if hasattr(table, "setUpdatesEnabled"):
            table.setUpdatesEnabled(previous_updates)
        if hasattr(table, "blockSignals"):
            table.blockSignals(previous_signals)
        if hasattr(table, "setSortingEnabled") and sorting_enabled:
            table.setSortingEnabled(True)
        if hasattr(table, "viewport"):
            table.viewport().update()


def _build_identity_table_item(window, symbol: str, *, badge: str = "--") -> QTableWidgetItem:
    stock_name = window._stock_name_for_symbol(symbol) if symbol else "--"
    stock_id = window._stock_id_for_symbol(symbol) if symbol else "--"
    text = f"{stock_name}  {stock_id}\n状态 {badge} | 标识 {symbol or '--'}"
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    item.setToolTip(f"{stock_name}\n代码：{stock_id}\n交易标识：{symbol or '--'}\n状态：{badge}")
    item.setData(QT_USER_ROLE, {"symbol": symbol, "stock_name": stock_name, "stock_id": stock_id, "badge": badge})
    return item


def _build_market_identity_item(row, *, background, foreground) -> QTableWidgetItem:
    stock_name = getattr(row, "stock_name", "") or "--"
    stock_id = getattr(row, "stock_id", "") or "--"
    symbol = getattr(row, "symbol", "") or "--"
    heat_score = float(getattr(row, "heat_score", 0.0) or 0.0)
    text = f"{stock_name} | {stock_id} | 热度 {heat_score:.1f}"
    item = QTableWidgetItem(text)
    item.setBackground(background)
    item.setForeground(foreground)
    item.setToolTip(
        "\n".join(
            [
                f"{stock_name} ({stock_id})",
                f"交易标识：{symbol}",
                f"热度：{heat_score:.1f}",
                f"涨幅：{float(getattr(row, 'pct_change', 0.0) or 0.0):.2f}%",
                f"决策分：{float(getattr(row, 'decision_score', 0.0) or 0.0):.1f}",
            ]
        )
    )
    item.setData(
        QT_USER_ROLE,
        {
            "symbol": symbol,
            "stock_name": stock_name,
            "stock_id": stock_id,
            "heat_score": heat_score,
            "decision_score": float(getattr(row, "decision_score", 0.0) or 0.0),
        },
    )
    return item


def _build_daily_pool_identity_item(window, row, execution_status: str) -> QTableWidgetItem:
    stock_name = row.stock_name or window._stock_name_for_symbol(row.symbol)
    stock_id = row.stock_id or window._stock_id_for_symbol(row.symbol)
    symbol = row.symbol or "--"
    heat_score = float(getattr(row, "mainline_strength_score", getattr(row, "theme_score", row.total_score)) or 0.0)
    badge = execution_status if execution_status != "待观察" else window._display_action(row.action)
    text = f"{stock_name} | {stock_id} | {badge}"
    item = QTableWidgetItem(text)
    item.setToolTip(
        "\n".join(
            [
                f"股票：{stock_name}",
                f"代码：{stock_id}",
                f"交易标识：{symbol}",
                f"执行状态：{badge}",
                f"主线热度：{heat_score:.1f}",
            ]
        )
    )
    item.setData(
        QT_USER_ROLE,
        {
            "symbol": symbol,
            "stock_name": stock_name,
            "stock_id": stock_id,
            "execution_status": execution_status,
            "badge": badge,
            "heat_score": heat_score,
        },
    )
    return item


def _build_status_badge_item(primary: str, secondary: str) -> QTableWidgetItem:
    text = f"{primary or '--'} / {secondary or '--'}"
    item = QTableWidgetItem(text)
    item.setTextAlignment(Qt.AlignCenter)
    item.setBackground(QColor("#24303A"))
    item.setForeground(QColor("#7ED7FF"))
    item.setToolTip(f"动作：{primary or '--'}\n成交：{secondary or '--'}")
    return item


def _build_compact_badge_item(
    texts: list[str],
    *,
    tooltip: str = "",
    background: str = "#24303A",
    foreground: str = "#DCE4EF",
) -> QTableWidgetItem:
    visible_texts = [str(text).strip() for text in texts if str(text).strip()]
    item = QTableWidgetItem(" / ".join(visible_texts) if visible_texts else "--")
    item.setTextAlignment(Qt.AlignCenter)
    item.setBackground(QColor(background))
    item.setForeground(QColor(foreground))
    if tooltip:
        item.setToolTip(tooltip)
    return item


def _apply_risk_lamp_colors(item: QTableWidgetItem, risk_lamp: str) -> None:
    if risk_lamp.startswith("红灯"):
        item.setBackground(QColor("#FBEAEA"))
        item.setForeground(QColor("#842029"))
    elif risk_lamp.startswith("黄灯"):
        item.setBackground(QColor("#FFF4DB"))
        item.setForeground(QColor("#7C4A03"))
    else:
        item.setBackground(QColor("#E8F7EC"))
        item.setForeground(QColor("#0F5132"))


def _ensure_table_item(table, row_index: int, column: int, value: str = "") -> QTableWidgetItem:
    item = table.item(row_index, column)
    if item is None:
        item = QTableWidgetItem(value)
        table.setItem(row_index, column, item)
    elif item.text() != value:
        item.setText(value)
    return item


def _set_item_data_if_changed(item: QTableWidgetItem, role: int, value) -> None:
    if item.data(role) != value:
        item.setData(role, value)


def _selected_table_symbol(table, rows: list, *, attr_name: str = "symbol") -> str:
    if table is None:
        return ""
    current_row = table.currentRow()
    if current_row < 0 or current_row >= len(rows):
        return ""
    return str(getattr(rows[current_row], attr_name, "") or "")


def _select_row_by_symbol(table, rows: list, symbol: str, *, attr_name: str = "symbol") -> int:
    if table is None or not rows:
        return -1
    target_row = next(
        (index for index, row in enumerate(rows) if str(getattr(row, attr_name, "") or "") == symbol),
        0,
    )
    if hasattr(table, "currentRow") and table.currentRow() == target_row:
        return target_row
    previous_signals = table.blockSignals(True) if hasattr(table, "blockSignals") else False
    try:
        table.selectRow(target_row)
    finally:
        if hasattr(table, "blockSignals"):
            table.blockSignals(previous_signals)
    return target_row


def _set_plain_text_if_changed(widget, text: str) -> None:
    if widget is None:
        return
    if hasattr(widget, "toPlainText") and widget.toPlainText() != text:
        widget.setPlainText(text)


def _set_label_text_if_changed(widget, text: str) -> None:
    if widget is None:
        return
    if hasattr(widget, "text") and widget.text() != text:
        widget.setText(text)


def _set_enabled_if_changed(widget, enabled: bool) -> None:
    if widget is None:
        return
    if hasattr(widget, "isEnabled") and widget.isEnabled() != enabled:
        widget.setEnabled(enabled)


def _set_tooltip_if_changed(widget, tooltip: str) -> None:
    if widget is None:
        return
    if hasattr(widget, "toolTip") and widget.toolTip() != tooltip:
        widget.setToolTip(tooltip)


def _brief_panel_text(title: str, conclusion: str, risk: str, next_step: str) -> str:
    return "\n".join(
        [
            title,
            f"结论：{conclusion}",
            f"风险：{risk}",
            f"下一步：{next_step}",
        ]
    )


def _display_mainline_role(value: str) -> str:
    return _shared_display_mainline_role(value)


def _mainline_flow_brief(recommendation) -> str:
    if recommendation is None:
        return "待核对"
    flow_signal = str(getattr(recommendation, "mainline_flow_signal", "") or "").strip()
    stage = str(getattr(recommendation, "mainline_stage", "") or "").strip()
    role = str(getattr(recommendation, "mainline_role", "") or "").strip()
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "").strip()
    if flow_signal in {"延续偏强", "延续待确认", "继续跟"} or stage in {"加速", "启动"}:
        return "继续跟"
    if flow_signal in {"延续可跟踪", "延续观察", "只观察"} or stage == "观察":
        return "只观察"
    if flow_signal in {"切换预警", "切换/退潮", "防切换"} or stage in {"分歧", "退潮"}:
        return "防切换"
    if role in {"CORE", "FRONT"} and risk_flag != "高" and window_score >= 70.0:
        return "继续跟"
    if role == "FOLLOW" or window_score >= 45.0:
        return "只观察"
    return "防切换"


def _mainline_gate_text(recommendation) -> str:
    if recommendation is None:
        return "待核对"
    role = _display_mainline_role(getattr(recommendation, "mainline_role", ""))
    rank = getattr(recommendation, "mainline_rank", getattr(recommendation, "theme_rank", 0)) or "--"
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    risk_flag = getattr(recommendation, "mainline_risk_flag", "") or "--"
    return f"第 {rank} 位 | {role} | 窗口 {window_score:.1f} | 风险 {risk_flag}"


def _compact_mainline_text(recommendation) -> str:
    if recommendation is None:
        return "待核对"
    flow = _mainline_flow_brief(recommendation)
    tag = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "未分类"
    role = _display_mainline_role(getattr(recommendation, "mainline_role", ""))
    rank = getattr(recommendation, "mainline_rank", getattr(recommendation, "theme_rank", 0)) or "--"
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    risk_flag = getattr(recommendation, "mainline_risk_flag", "") or "--"
    return f"{flow} / {tag} / {role} / 第{rank}位 / 窗{window_score:.1f} / 风{risk_flag}"


def _compact_daily_pool_status(value: str) -> str:
    mapping = {
        "待观察": "待观",
        "已送审": "送审",
        "已提交": "已提",
        "提交失败": "失败",
        "已拒绝": "已拒",
        "提交中": "提中",
        "已撤回": "已撤",
        "待补齐": "待补",
    }
    raw = str(value or "").strip()
    return mapping.get(raw, raw or "--")


def _compact_daily_pool_role(value: str) -> str:
    mapping = {
        "CORE": "核心",
        "FRONT": "前排",
        "ASSIST": "助攻",
        "FOLLOW": "跟随",
        "NOISE": "噪音",
        "ELIMINATED": "淘汰",
    }
    raw = str(value or "").strip()
    return mapping.get(raw, raw or "--")


def _compact_daily_pool_action(value: str) -> str:
    mapping = {
        "BUY": "买",
        "WATCH": "观",
        "HOLD": "持",
        "REDUCE": "减",
        "SELL": "卖",
    }
    raw = str(value or "").strip().upper()
    return mapping.get(raw, raw or "--")


def _compact_daily_pool_strategy(value: str) -> str:
    raw = _canonical_strategy_name(value)
    if not raw:
        return "--"
    if raw == "擒龙打板":
        return "打板"
    if raw in {"尾盘买入法", "尾盘买入"}:
        return "尾盘"
    if raw in {"掘龙决策", "掘龙"}:
        return "掘龙"
    if raw in {"一日持股法", "一日持股"}:
        return "一日"
    return raw if len(raw) <= 4 else raw[:4]


def _canonical_strategy_name(value: str) -> str:
    raw = str(value or "").strip()
    alias_map = {
        "龙头主线": "龙头模型",
        "龙头模型": "龙头模型",
        "资金承接": "主力雷达",
        "主力雷达": "主力雷达",
        "强势接力": "擒龙打板",
        "打板策略": "擒龙打板",
        "擒龙打板": "擒龙打板",
        "趋势低吸": "价值低吸",
        "价值低吸": "价值低吸",
        "尾盘买入": "尾盘买入法",
        "尾盘买入法": "尾盘买入法",
        "一日持股": "一日持股法",
        "隔日强势": "一日持股法",
        "一日持股法": "一日持股法",
        "综合决策": "掘龙决策",
        "掘龙": "掘龙决策",
        "掘龙决策": "掘龙决策",
    }
    return alias_map.get(raw, raw)


def _strategy_scene_copy(strategy_name: str) -> str:
    return {
        "龙头模型": "适合主线最强、龙头属性明确、趋势仍在延续的票。",
        "主力雷达": "适合资金承接清晰、量价匹配、机构或主力动作明显的票。",
        "擒龙打板": "适合强势确认、回封确认、需要盯节奏和情绪的高弹性机会。",
        "价值低吸": "适合回踩修复、低位承接、强调安全边际和修复预期的票。",
        "尾盘买入法": "适合尾盘回流确认后隔夜，重点看 14:30 后承接和次日开盘兑现。",
        "一日持股法": "适合隔日博弈，重点看竞价转强、开盘承接和次日兑现。",
        "掘龙决策": "适合把主线、资金、位置和节奏综合起来做最终动作判断。",
    }.get(strategy_name, "适合等待机会池同步后再看具体打法。")


def _strategy_reason_copy(row, strategy_name: str) -> str:
    strategy_score_map = {
        "龙头模型": float(getattr(row, "leader_model_score", 0.0) or 0.0),
        "主力雷达": float(getattr(row, "main_force_score", 0.0) or 0.0),
        "擒龙打板": float(getattr(row, "board_attack_score", 0.0) or 0.0),
        "价值低吸": float(getattr(row, "value_recovery_score", 0.0) or 0.0),
        "尾盘买入法": float(getattr(row, "tail_buy_score", 0.0) or 0.0),
        "一日持股法": float(getattr(row, "one_day_hold_score", 0.0) or 0.0),
        "掘龙决策": float(getattr(row, "dragon_decision_score", getattr(row, "total_score", 0.0)) or 0.0),
    }
    score = strategy_score_map.get(strategy_name, 0.0)
    mainline_tag = getattr(row, "mainline_tag", "") or getattr(row, "theme_name", "") or "未分类"
    catalyst = getattr(row, "catalyst", "") or "暂无催化"
    if strategy_name == "擒龙打板":
        return f"主线 {mainline_tag} 仍有强势确认机会，回封/加速节奏匹配，当前打板分 {score:.1f}。"
    if strategy_name == "尾盘买入法":
        return f"题材 {mainline_tag} 更适合尾盘回流后隔夜，催化 {catalyst}，当前尾盘分 {score:.1f}。"
    if strategy_name == "一日持股法":
        return f"题材 {mainline_tag} 具备隔日博弈空间，催化 {catalyst}，当前隔日节奏分 {score:.1f}。"
    if strategy_name == "价值低吸":
        return f"主线 {mainline_tag} 有修复预期，位置和承接更偏低吸，当前低吸分 {score:.1f}。"
    if strategy_name == "主力雷达":
        return f"主线 {mainline_tag} 资金承接更清晰，催化 {catalyst}，当前雷达分 {score:.1f}。"
    if strategy_name == "龙头模型":
        return f"主线 {mainline_tag} 龙头属性更明确，窗口和位次更靠前，当前龙头分 {score:.1f}。"
    return f"当前综合决策分 {score:.1f}，说明它在主线、资金和执行窗口上更均衡。"


def _strategy_product_positioning(strategy_name: str) -> str:
    return {
        "龙头模型": "主线最强确认，适合做前排龙头识别和强者恒强。",
        "主力雷达": "资金承接跟随，适合做主力痕迹和资金流确认。",
        "擒龙打板": "高弹性打板，适合做强势确认后的进攻型博弈。",
        "价值低吸": "修复型低吸，适合做回踩承接和安全边际。",
        "尾盘买入法": "尾盘隔夜，适合做尾盘回流后的短周期博弈。",
        "一日持股法": "隔日节奏，适合做竞价转强到次日兑现。",
        "掘龙决策": "综合决策，适合做主线、位置、资金与节奏的总判断。",
    }.get(strategy_name, "等待机会池同步后再确认战法定位。")


def _strategy_capital_style(strategy_name: str) -> str:
    return {
        "龙头模型": "主线进攻 / 趋势跟随",
        "主力雷达": "资金跟随 / 中速切入",
        "擒龙打板": "快进快出 / 高弹性博弈",
        "价值低吸": "分批低吸 / 修复博弈",
        "尾盘买入法": "尾盘试仓 / 隔夜兑现",
        "一日持股法": "隔日试错 / 次日兑现",
        "掘龙决策": "均衡配置 / 最终决策",
    }.get(strategy_name, "等待同步")


def _strategy_risk_level(strategy_name: str, focus_row) -> str:
    explicit_flag = str(getattr(focus_row, "mainline_risk_flag", "") or "").strip()
    if explicit_flag == "高":
        return "高风险"
    if strategy_name in {"擒龙打板", "尾盘买入法", "一日持股法"}:
        return "高风险"
    if strategy_name == "价值低吸":
        return "中低风险" if explicit_flag == "低" else "中风险"
    if explicit_flag == "低":
        return "中风险"
    return "中高风险" if strategy_name == "龙头模型" else "中风险"


def _strategy_position_hint(strategy_name: str, focus_row) -> str:
    action = str(getattr(focus_row, "action", "") or "").upper()
    if action in {"SELL", "REDUCE"}:
        return "当前以处理持仓为主，不新增仓位。"
    return {
        "龙头模型": "先试仓确认，再沿主线延续分批加。 ",
        "主力雷达": "先小仓验证承接，放量确认后再加。",
        "擒龙打板": "只做小样本试错，封板质量确认后再考虑加码。",
        "价值低吸": "优先分批吸，不要一次性打满。",
        "尾盘买入法": "只做尾盘试仓，隔夜后以兑现优先。",
        "一日持股法": "先轻仓博弈，次日不及预期就快速退出。",
        "掘龙决策": "先按综合结论试仓，确认后再进入交易计划。",
    }.get(strategy_name, "先小仓验证，再决定是否继续。").strip()


def _strategy_no_go_text(strategy_name: str, focus_row) -> str:
    invalidation = _strategy_invalidation_signal_text(focus_row)
    base = {
        "龙头模型": "主线掉队、位次后排、龙头属性不清时不做。",
        "主力雷达": "资金承接转弱、放量滞涨、催化失真时不做。",
        "擒龙打板": "情绪退潮、炸板承接差、非主线硬板时不做。",
        "价值低吸": "修复逻辑不成立、承接不足、跌破防守位时不做。",
        "尾盘买入法": "14:30 前无回流、尾盘抢拉无承接、隔夜消息走弱时不做。",
        "一日持股法": "竞价不转强、开盘承接弱、次日兑现逻辑缺失时不做。",
        "掘龙决策": "主线不清、信号冲突、价位没有形成时不做。",
    }.get(strategy_name, "等待更多确认后再决定。")
    return f"{base} 当前失效线：{invalidation}"


def _strategy_applicable_market(strategy_name: str, focus_row) -> str:
    custom = str(
        getattr(focus_row, "applicable_market", "")
        or getattr(focus_row, "market_condition", "")
        or ""
    ).strip()
    if custom:
        return custom
    return {
        "龙头模型": "适合主线最强仍在加速、龙头位次明确、板块仍有持续性的行情。",
        "主力雷达": "适合资金承接持续增强、量价匹配清晰、机构痕迹明显的行情。",
        "擒龙打板": "适合情绪回暖、回封质量高、前排封板溢价仍在的进攻型行情。",
        "价值低吸": "适合主线分歧后的回踩修复、承接重新回流、追高性价比偏低的行情。",
        "尾盘买入法": "适合尾盘回流确认、隔夜博弈仍有溢价、次日兑现窗口较明确的行情。",
        "一日持股法": "适合隔日强弱切换快、竞价与开盘承接决定盈亏的短节奏行情。",
        "掘龙决策": "适合主线、资金、位置与节奏需要统一判断的综合型行情。",
    }.get(strategy_name, "等待样本和机会池同步后再确认适用行情。")


def _strategy_capacity_limit(strategy_name: str, focus_row) -> str:
    custom = str(getattr(focus_row, "capacity_limit", "") or "").strip()
    if custom:
        return custom
    action = str(getattr(focus_row, "action", "") or "").upper()
    if action in {"SELL", "REDUCE"}:
        return "当前以收缩和处理持仓为主，不适合继续扩大战法容量。"
    return {
        "龙头模型": "更适合核心仓位逐步放大，但前提是龙头和主线都没有掉队。",
        "主力雷达": "更适合中等容量跟随，不适合在承接未确认前瞬间打满。",
        "擒龙打板": "只适合小样本快节奏试错，不适合重仓持续摊大单票风险。",
        "价值低吸": "更适合中等容量分批布局，不适合在无承接时一次性打满。",
        "尾盘买入法": "更适合小到中等容量尾盘试仓，不适合全天追高后被动隔夜。",
        "一日持股法": "更适合轻仓滚动试错，不适合在次日兑现逻辑不清时大仓位隔夜。",
        "掘龙决策": "容量跟随总分与执行闸门动态调整，不适合脱离主线单独重仓。",
    }.get(strategy_name, "先小样本运行，确认稳定后再逐步扩大战法容量。")


def _strategy_standard_action(strategy_name: str, focus_row) -> str:
    custom = str(getattr(focus_row, "standard_action", "") or "").strip()
    if custom:
        return custom
    buy_point = str(getattr(focus_row, "buy_point", "") or "").strip()
    sell_point = str(getattr(focus_row, "sell_point", "") or "").strip()
    if strategy_name == "价值低吸":
        return f"先等回踩企稳，再分批低吸；{sell_point or '修复到计划目标位后分批兑现。'}"
    if strategy_name == "擒龙打板":
        return f"先等强势确认和回封质量，再小仓试错；{sell_point or '炸板或次日弱转强失败时快速处理。'}"
    if strategy_name == "尾盘买入法":
        return f"先看 14:30 后回流和承接，再尾盘试仓；{sell_point or '次日冲高优先兑现，不恋战。'}"
    if strategy_name == "一日持股法":
        return f"先看竞价转强和开盘承接，再做隔日试错；{sell_point or '次日不及预期就快速退出。'}"
    if strategy_name == "龙头模型":
        return f"{buy_point or '先确认龙头位次和主线延续，再试仓。'}；{sell_point or '主线掉队或龙头失速时分批处理。'}"
    if strategy_name == "主力雷达":
        return f"{buy_point or '先确认承接和量能，再做跟随。'}；{sell_point or '承接转弱或量价失配时及时收缩。'}"
    return f"{buy_point or '先按综合结论试仓。'}；{sell_point or '失去优势后按计划退出。'}"


def _strategy_failure_sample_text(strategy_name: str, focus_row) -> str:
    custom = str(
        getattr(focus_row, "failure_example", "")
        or getattr(focus_row, "failure_sample", "")
        or ""
    ).strip()
    if custom:
        return custom
    invalidation = _strategy_invalidation_signal_text(focus_row)
    return {
        "龙头模型": f"最容易失败在主线切换后还把后排当龙头，或位次下降后仍试图硬抗。当前失效线：{invalidation}",
        "主力雷达": f"最容易失败在资金假承接、放量滞涨、催化兑现后还继续追随。当前失效线：{invalidation}",
        "擒龙打板": f"最容易失败在情绪退潮、炸板承接差、非主线硬板时继续进攻。当前失效线：{invalidation}",
        "价值低吸": f"最容易失败在修复预期落空、承接不足、{invalidation}后还继续摊低成本。",
        "尾盘买入法": f"最容易失败在尾盘抢拉无承接、隔夜消息走弱、次日竞价不及预期却没有先撤。当前失效线：{invalidation}",
        "一日持股法": f"最容易失败在竞价不转强、开盘承接弱、次日兑现失败却没有及时认错。当前失效线：{invalidation}",
        "掘龙决策": f"最容易失败在主线、位置和资金信号互相冲突时仍强行下结论。当前失效线：{invalidation}",
    }.get(strategy_name, f"最容易失败在信号不一致却强行执行。当前失效线：{invalidation}")


def _compact_daily_pool_date(value: str) -> str:
    raw = str(value or "").strip()
    if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
        return raw[5:]
    return raw or "--"


def _daily_pool_price_snapshot(row) -> dict[str, float | None]:
    entry_price = getattr(row, "entry_price", None)
    close_price = getattr(row, "close", 0.0) or 0.0
    entry = float(entry_price if entry_price is not None else close_price) if (entry_price is not None or close_price) else 0.0
    stop_price = getattr(row, "stop_price", None)
    target_price = getattr(row, "target_price", None)
    stop = float(stop_price if stop_price is not None else (entry * 0.95 if entry else 0.0))
    target = float(target_price if target_price is not None else (entry * 1.08 if entry else 0.0))
    upside_pct = ((target - entry) / entry * 100.0) if entry and target > entry else None
    downside_pct = ((entry - stop) / entry * 100.0) if entry and stop < entry else None
    rr_ratio = None
    if entry and stop and target and entry > stop and target > entry:
        rr_ratio = (target - entry) / max(entry - stop, 0.001)
    return {
        "entry": entry,
        "stop": stop,
        "target": target,
        "upside_pct": upside_pct,
        "downside_pct": downside_pct,
        "rr_ratio": rr_ratio,
    }


def _shorten_daily_pool_text(value: str, limit: int = 8) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "--"
    if len(raw) <= limit:
        return raw
    return raw[: max(1, limit - 1)] + "…"


def _news_digest_lines(window, symbol: str, limit: int = 2) -> list[str]:
    items = list(getattr(window, "news_catalysts", {}).get(symbol, []) or [])
    if not items:
        return []
    lines: list[str] = []
    for item in items[:limit]:
        title = getattr(item, "title", "") or "消息标题未填写"
        source = getattr(item, "source", "") or "来源未知"
        published = getattr(item, "published_at", "") or ""
        meta = " / ".join(part for part in [source, published] if part)
        lines.append(f"- {title}{f' ({meta})' if meta else ''}")
        summary = getattr(item, "summary", "") or ""
        if summary:
            lines.append(f"  {summary[:42]}")
    return lines


def _daily_pool_row_tooltip(window, row, execution_status: str) -> str:
    mainline_tag = getattr(row, "mainline_tag", "") or getattr(row, "theme_name", "") or "未分类"
    mainline_rank = getattr(row, "mainline_rank", getattr(row, "theme_rank", 0)) or "--"
    mainline_role = _display_mainline_role(getattr(row, "mainline_role", ""))
    mainline_window = float(getattr(row, "mainline_window_score", 0.0) or 0.0)
    mainline_risk = getattr(row, "mainline_risk_flag", "--") or "--"
    strategy = _canonical_strategy_name(getattr(row, "primary_strategy", "") or "掘龙决策")
    lead_level = window._display_leader_level(getattr(row, "leader_level", "")) if hasattr(window, "_display_leader_level") else str(getattr(row, "leader_level", "") or "--")
    catalyst = getattr(row, "catalyst", "") or "暂无催化"
    stock_pool = getattr(row, "stock_pool", "") or "趋势股"
    pool_score = float(getattr(row, "pool_score", 0.0) or 0.0)
    news_score = float(getattr(row, "news_score", 0.0) or 0.0)
    buy_point = getattr(row, "buy_point", "") or "等待入场确认"
    sell_point = getattr(row, "sell_point", "") or "按计划目标分批处理"
    rationale = getattr(row, "rationale", "") or "暂无附加说明"
    price_snapshot = _daily_pool_price_snapshot(row)
    entry_price = float(price_snapshot["entry"] or 0.0)
    stop_price = float(price_snapshot["stop"] or 0.0)
    target_price = float(price_snapshot["target"] or 0.0)
    rr_ratio = price_snapshot["rr_ratio"]
    upside_pct = price_snapshot["upside_pct"]
    downside_pct = price_snapshot["downside_pct"]
    lines = [
        f"状态：{execution_status} | 动作：{getattr(row, 'action', '') or '--'}",
        f"主线：{mainline_tag} | 第 {mainline_rank} 位 | {mainline_role}",
        f"窗口：{mainline_window:.1f} | 风险：{mainline_risk}",
        f"策略：{strategy} | 级别：{lead_level} | 总分：{getattr(row, 'total_score', 0.0):.1f}",
        f"七策：龙头 {getattr(row, 'leader_model_score', 0.0):.1f} / 主力 {getattr(row, 'main_force_score', 0.0):.1f} / "
        f"打板 {getattr(row, 'board_attack_score', 0.0):.1f} / 低吸 {getattr(row, 'value_recovery_score', 0.0):.1f} / "
        f"尾盘 {getattr(row, 'tail_buy_score', 0.0):.1f} / 一日 {getattr(row, 'one_day_hold_score', 0.0):.1f} / 决策 {getattr(row, 'dragon_decision_score', getattr(row, 'total_score', 0.0)):.1f}",
        f"股池：{stock_pool} | 池分：{pool_score:.1f} | 消息：{news_score:.1f}",
        f"买卖点：{buy_point} / {sell_point}",
        f"价格：买 {entry_price:.2f} / 止损 {stop_price:.2f} / 目标 {target_price:.2f}",
        f"收益/风险比：{rr_ratio:.2f}" if rr_ratio is not None else "收益/风险比：--",
        f"空间：上行 {upside_pct:.1f}% / 防守 {downside_pct:.1f}%" if upside_pct is not None and downside_pct is not None else "空间：--",
        f"催化：{catalyst}",
        f"理由：{rationale}",
        f"日期：{_compact_daily_pool_date(getattr(row, 'signal_date', ''))}",
    ]
    grade = one_day_hold_grade(row)
    if grade:
        lines.insert(7, f"隔日博弈等级：{grade}")
    news_lines = _news_digest_lines(window, getattr(row, "symbol", "") or "")
    if news_lines:
        lines.append("消息：")
        lines.extend(news_lines)
    else:
        lines.append("消息：暂无近期催化")
    return "\n".join(lines)


def _order_available_quantity(window, symbol: str) -> int | None:
    for holding in getattr(window, "holdings", []) or []:
        if getattr(holding, "symbol", "") != symbol:
            continue
        available = getattr(holding, "available", None)
        if available is None:
            available = getattr(holding, "quantity", None)
        try:
            return int(available) if available is not None else None
        except (TypeError, ValueError):
            return None
    return None


def _order_risk_lamp_text(window, item, recommendation=None, details=None, summary=None) -> str:
    details = details or {}
    summary = summary or getattr(window, "last_broker_execution_summary", None) or {}
    blockers = list(summary.get("blockers", []) or [])
    warnings = list(summary.get("warnings", []) or [])
    side = str(getattr(item, "side", "")).upper()
    quantity = int(getattr(item, "quantity", 0) or 0)
    symbol = getattr(item, "symbol", "")
    available = _order_available_quantity(window, symbol)

    if side in {"SELL", "REDUCE"}:
        if available is None:
            return "红灯 缺持仓"
        if quantity > available:
            return f"红灯 超卖 {quantity - available} 股"
        if quantity == available:
            return f"黄灯 清仓 {available} 股"
        if blockers:
            return "黄灯 阻塞待处理"
        if warnings:
            return "黄灯 风险复核"
        return f"绿灯 可卖 {available - quantity} 股"

    if blockers:
        return "红灯 阻塞待处理"
    if recommendation is None:
        return "黄灯 待核对"

    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
    role = str(getattr(recommendation, "mainline_role", "") or "")
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    if role in {"NOISE", "ELIMINATED"} or risk_flag == "高" or window_score < 48:
        return "红灯 主线风险高"
    if risk_flag == "中" or role == "FOLLOW":
        return "黄灯 主线观察"
    if warnings:
        return "黄灯 风险复核"
    if details.get("checks"):
        return "黄灯 需复核"
    return "绿灯 可提交"


def build_market_proxy_points(rows: list) -> tuple[list[object], float]:
    visible_rows = list(rows)[:8]
    if not visible_rows:
        return [], 0.0
    avg_pct = sum(getattr(row, "pct_change", 0.0) for row in visible_rows) / max(len(visible_rows), 1)
    base_price = 1000.0
    values = [
        base_price,
        base_price * (1 + avg_pct / 100.0 * 0.04),
        base_price * (1 + avg_pct / 100.0 * 0.01),
        base_price * (1 + avg_pct / 100.0 * 0.08),
        base_price * (1 + avg_pct / 100.0 * 0.15),
        base_price * (1 + avg_pct / 100.0 * 0.11),
        base_price * (1 + avg_pct / 100.0 * 0.18),
    ]
    points = [type("P", (), {"t": f"{index}", "v": value})() for index, value in enumerate(values)]
    return points, base_price


def history_window_limit(window: str, timeframe: str) -> int:
    mapping = {
        "近3月": {"日线": 60, "周线": 14, "月线": 3},
        "近1年": {"日线": 240, "周线": 52, "月线": 12},
        "近3年": {"日线": 720, "周线": 156, "月线": 36},
        "全部": {"日线": 5000, "周线": 5000, "月线": 5000},
    }
    return mapping.get(window or "近1年", mapping["近1年"]).get(timeframe, 240)


def history_start_for_timeframe(timeframe: str) -> str:
    if timeframe == "月线":
        return "20180101"
    if timeframe == "周线":
        return "20200101"
    return "20240101"


def refresh_recommend_summary_cards(window, plan) -> None:
    if not hasattr(window, "recommend_summary_cards"):
        return
    top_pick = window.daily_pool_rows[0] if window.daily_pool_rows else None
    top_flow = _mainline_flow_brief(top_pick) if top_pick else "--"
    top_grade = one_day_hold_grade(top_pick) if top_pick else ""
    top_tail_phase, _top_tail_hint = tail_buy_runtime_status(top_pick) if top_pick else ("", "")
    top_note = plan.notes[0] if plan.notes else "等待交易计划生成"
    execution_summary = (
        window._recommend_execution_summary(plan)
        if hasattr(window, "_recommend_execution_summary")
        else {"reviewing": 0, "submitted": 0, "failed": 0, "pending": len(getattr(plan, "decisions", []))}
    )
    window.recommend_summary_cards["logic"].set_data(
        top_flow,
        _compact_mainline_text(top_pick) if top_pick else "等待主线同步",
    )
    plan_detail = "等待交易计划生成"
    if plan.decisions:
        plan_detail_parts = [f"焦点 {plan.decisions[0].stock_name}"]
        if top_tail_phase:
            plan_detail_parts.append(f"尾盘 {top_tail_phase}")
        elif top_grade:
            plan_detail_parts.append(f"隔日 {top_grade}")
        plan_detail_parts.append(f"复核 {execution_summary['reviewing']}")
        plan_detail_parts.append(f"失败 {execution_summary['failed']}")
        plan_detail = " | ".join(plan_detail_parts)
    window.recommend_summary_cards["plan"].set_data(
        f"计划 {len(plan.decisions)} / 送审 {execution_summary['submitted']}",
        plan_detail,
    )
    window.recommend_summary_cards["pulse"].set_data(
        f"{plan.market_pulse.sentiment_score:.1f}",
        f"{plan.market_pulse.sentiment_label} | {plan.market_pulse.market_regime} | 风险 {plan.market_pulse.risk_level}",
    )
    window.recommend_summary_cards["holding"].set_data(
        f"待执行 {execution_summary['pending']}",
        (
            f"{top_flow} | {(f'尾盘 {top_tail_phase}' if top_tail_phase else (f'隔日 {top_grade}' if top_grade else '盘中跟踪'))} | 送审 {execution_summary['submitted']}"
            if plan.decisions
            else "等待持仓建议生成"
        ),
    )


def refresh_strategy_path_panel(window, plan, top_theme, top_strategy_name, top_pick) -> None:
    if not hasattr(window, "strategy_path_text"):
        return
    if not top_pick:
        _set_plain_text_if_changed(window.strategy_path_text, "主线推演\n结论：等待主线确认\n风险：暂无主线风险\n下一步：先确认主线。")
        return
    lines = [
        "主线推演",
        f"结论：{top_theme.theme_name if top_theme else '暂无'} | {window._display_action(top_pick.action)} | {top_pick.stock_name}",
        f"风险：窗口 {getattr(top_pick, 'mainline_window_score', 0.0):.1f} | {getattr(top_pick, 'mainline_risk_flag', '--')}",
        f"下一步：{(top_pick.next_focus or top_pick.catalyst or '继续盯主线与量价')[:22]}",
    ]
    if window.market_path_alert_history:
        lines.append(f"提示：{window.market_path_alert_history[-1][:22]}")
    _set_plain_text_if_changed(window.strategy_path_text, "\n".join(lines))


def build_recommend_dispatch_snapshot(
    rows: list,
    plan,
    execution_status_by_symbol: dict[str, str],
    selected_row=None,
    display_action_fn=None,
) -> dict[str, str]:
    top_pick = rows[0] if rows else None
    top_theme = top_pick.theme_name if top_pick and getattr(top_pick, "theme_name", "") else "未分类"
    top_flow = _mainline_flow_brief(top_pick) if top_pick else "待核对"
    buy_rows = [item for item in rows if getattr(item, "action", "") == "BUY"]
    watch_rows = [item for item in rows if getattr(item, "action", "") == "WATCH"]
    queued_rows = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "已送审"]
    submitted_rows = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "已提交"]
    failed_rows = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "提交失败"]
    pending_review = [item for item in buy_rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "待观察") == "待观察"]

    next_step = (
        f"先复核 {pending_review[0].stock_name}"
        if pending_review
        else (
            f"跟踪失败单 {failed_rows[0].stock_name}"
            if failed_rows
            else (f"已提交 {len(submitted_rows)} 只，可转交易台" if submitted_rows else "先审查，再执行")
        )
    )
    headline = (
        f"今日分发 | {top_flow} | 主线: {top_theme} | 总池 {len(rows)} | 买 {len(buy_rows)} | 观 {len(watch_rows)} | "
        f"待复核 {len(pending_review)} | 送审 {len(queued_rows)} | 提交 {len(submitted_rows)} | 失败 {len(failed_rows)} | {next_step}"
    )

    selected = selected_row or top_pick
    if selected is None:
        focus = _brief_panel_text("焦点审查", "等待选择股票", "暂无焦点风险", "请先从推荐池选择一只股票。")
    else:
        execution_status = execution_status_by_symbol.get(getattr(selected, "symbol", ""), "待观察")
        action_text = display_action_fn(selected.action) if callable(display_action_fn) else getattr(selected, "action", "")
        rr_text = "--"
        entry_price = getattr(selected, "entry_price", 0.0) or getattr(selected, "close", 0.0) or 0.0
        stop_price = getattr(selected, "stop_price", 0.0) or 0.0
        target_price = getattr(selected, "target_price", 0.0) or 0.0
        if entry_price > 0 and stop_price > 0 and target_price > entry_price and entry_price > stop_price:
            rr_text = f"{(target_price - entry_price) / max(entry_price - stop_price, 0.001):.2f}"
        next_step = "继续观察量价共振。"
        if getattr(selected, "action", "") == "BUY" and execution_status == "待观察":
            next_step = "可直接推送审查。"
        elif execution_status == "已送审":
            next_step = "已进入审查，可切交易页。"
        elif execution_status == "已提交":
            next_step = "已提交，跟踪成交。"
        elif execution_status == "提交失败":
            next_step = "提交失败，先复核风控。"
        focus = _brief_panel_text(
            "单票审查",
            f"{selected.stock_name} | {_mainline_flow_brief(selected)} | {action_text} / {execution_status}",
            f"主线/位次/角色：{(getattr(selected, 'mainline_tag', '') or selected.theme_name or '未分类')} | "
            f"第 {getattr(selected, 'mainline_rank', getattr(selected, 'theme_rank', 0)) or '--'} 位 | "
            f"{_display_mainline_role(getattr(selected, 'mainline_role', ''))} | 风险 {getattr(selected, 'mainline_risk_flag', '--')} | 盈亏比 {rr_text}",
            next_step,
        )
        focus = focus.replace(f"{action_text} / {execution_status}", f"动作/状态：{action_text} / {execution_status}")

    queue = _brief_panel_text(
        "执行队列概览",
        f"待复核 {len(pending_review)} | 已送审 {len(queued_rows)} | 已提交 {len(submitted_rows)}",
        (
            f"失败单 | {failed_rows[0].stock_name}"
            if failed_rows
            else ("暂无失败单" if rows else "暂无执行队列")
        ),
        (
            f"先处理 {pending_review[0].stock_name}"
            if pending_review
            else (
                f"转交易页跟踪 {queued_rows[0].stock_name}"
                if queued_rows
                else ("复核失败单" if failed_rows else "继续从推荐池挑选高优先票。")
            )
        ),
    )

    return {
        "headline": headline,
        "focus": focus,
        "queue": queue,
    }


def build_overview_command_snapshot(
    pool: list,
    recommendations: list,
    execution_status_by_symbol: dict[str, str],
    *,
    market_data_source: str,
    last_market_success_at: str,
    last_market_error: str,
    last_job_status: str,
    last_job_name: str,
    last_job_finished_at: str,
    order_submission_log: list[str],
) -> dict[str, str]:
    execution_summary = execution_summary_for_rows(recommendations, execution_status_by_symbol)
    buy_rows = [item for item in recommendations if getattr(item, "action", "") == "BUY"]
    top_pick = buy_rows[0] if buy_rows else (recommendations[0] if recommendations else None)
    top_theme = getattr(top_pick, "theme_name", "") if top_pick else ""
    if not recommendations:
        market_strength = "等待"
    elif execution_summary["failed"] > 0 and execution_summary["failed"] >= execution_summary["submitted"] + execution_summary["reviewing"]:
        market_strength = "收缩"
    elif len(buy_rows) >= 3:
        market_strength = "可做"
    elif len(buy_rows) >= 1:
        market_strength = "轻仓"
    else:
        market_strength = "观望"

    source_label = {
        "remote": "实时远程",
        "sample": "示例数据",
        "cache": "本地缓存",
        "unknown": "未识别",
    }.get(market_data_source or "unknown", "未识别")

    focus_name = top_pick.stock_name if top_pick else "暂无"
    focus_buy = getattr(top_pick, "buy_point", "") or "等待确认"
    focus_risk = getattr(top_pick, "risk_line", "") or "先按防守线处理"
    last_refresh = last_market_success_at or "等待同步"
    command_lines = [
        "今日主线",
        "",
        f"总评：{market_strength}",
        f"结论：{_mainline_flow_brief(top_pick) if top_pick else '待核对'} | 主线 {top_theme or '等待确认'} | 可买 {len(buy_rows)}",
        f"焦点：{focus_name} | 买点 {focus_buy}",
        f"风险：防切换 | {focus_risk}",
        f"数据：{source_label} | 最近刷新 {last_refresh}",
    ]
    if last_market_error:
        command_lines.append(f"异常：{last_market_error}")

    runtime_value = last_job_status or "idle"
    execution_lines = [
        "持仓怎么处理",
        "",
        f"总览：待处理 {execution_summary['pending']} | 送审 {execution_summary['reviewing']} | 提交 {execution_summary['submitted']} | 失败 {execution_summary['failed']}",
        f"运行：{runtime_value}",
    ]
    if execution_summary["failed"] > 0:
        execution_lines.append("下一步：先处理失败单，再考虑新开仓。")
    elif execution_summary["reviewing"] > 0:
        execution_lines.append("下一步：有票已送审，先去交易页完成最后确认。")
    elif execution_summary["submitted"] > 0:
        execution_lines.append("下一步：已有持仓在执行，优先盯成交质量和减仓位。")
    else:
        execution_lines.append("下一步：目前没有执行压力，可以先专注于挑最强买点。")
    if order_submission_log:
        execution_lines.extend(["", "最近动作", *[f"- {item}" for item in order_submission_log[-2:]]])
    elif last_job_name or last_job_finished_at:
        execution_lines.extend(["", f"最近任务：{last_job_name or '暂无'}", f"完成时间：{last_job_finished_at or '暂无'}"])

    return {"command": "\n".join(command_lines), "execution": "\n".join(execution_lines)}


def build_dashboard_metrics_snapshot(pool: list, recommendations: list) -> dict[str, tuple[str, str]]:
    buy_count = sum(1 for item in recommendations if getattr(item, "action", "") == "BUY")
    avg_heat = (sum(getattr(item, "heat_score", 0.0) for item in pool) / len(pool)) if pool else 0.0
    theme_counter: dict[str, int] = {}
    theme_source = recommendations if recommendations else pool
    for item in theme_source:
        theme_name = (
            getattr(item, "mainline_tag", "")
            or getattr(item, "theme_name", "")
            or getattr(item, "strategy_tag", "")
            or "未分类"
        )
        theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
    top_theme = max(theme_counter.items(), key=lambda item: item[1])[0] if theme_counter else "暂无"
    top_pick = recommendations[0] if recommendations else None
    top_flow = _mainline_flow_brief(top_pick) if top_pick else "待核对"
    return {
        "candidate_count": (
            str(len(pool)),
            f"Top 1：{pool[0].stock_name}" if pool else "等待候选同步",
        ),
        "buy_count": (
            str(buy_count),
            f"观察 {max(len(recommendations) - buy_count, 0)} 只",
        ),
        "avg_heat": (
            f"{avg_heat:.1f}",
            "热度高于 80 为强势前排" if pool else "等待热度同步",
        ),
        "top_theme": (
            top_theme,
            (
                f"{top_flow} | {theme_counter.get(top_theme, 0)} 只 | 窗口 {getattr(top_pick, 'mainline_window_score', 0.0):.1f}"
                if theme_counter and top_pick
                else (f"{theme_counter.get(top_theme, 0)} 只" if theme_counter else "等待主线同步")
            ),
        ),
    }


def build_market_dashboard_snapshot(snapshot, recommendation=None) -> dict[str, str]:
    title = "SHSE.600000"
    subheader = "程序自动筛选的龙头候选"
    signal = "等待行情与题材快照刷新"
    if snapshot is not None:
        title = f"{snapshot.stock_name}  {snapshot.stock_id}  {snapshot.symbol}"
        subheader = (
            f"{snapshot.strategy_tag} | {snapshot.fund_model} | 涨 {snapshot.pct_change:.2f}% | "
            f"换 {snapshot.turnover:.1f}% | 净流 {snapshot.main_inflow / 1e8:.2f} 亿"
        )
        signal = (
            f"{snapshot.fund_model} | {snapshot.strategy_tag} | "
            f"热 {snapshot.heat_score:.1f} | 动 {snapshot.momentum_bias:.1f}"
        )
    elif recommendation is not None:
        title = f"{recommendation.stock_name}  {recommendation.stock_id}  {recommendation.symbol}"
        subheader = (
            f"{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'} | "
            f"{recommendation.theme_name or '未分类'} | 总分 {recommendation.total_score:.1f}"
        )
        signal = (
            f"动作 {getattr(recommendation, 'action', '') or 'WATCH'}   |   "
            f"热度 {getattr(recommendation, 'heat_score', 0.0):.1f}   |   "
            f"位置 {getattr(recommendation, 'position_score', 0.0):.1f}"
        )
    return {
        "title": title,
        "subheader": subheader,
        "signal": signal,
    }


def build_market_text_snapshot(
    snapshot,
    recommendation,
    latest_signal,
    *,
    display_action_fn,
    display_label_fn,
) -> dict[str, str]:
    market_view = "先等"
    if recommendation is not None and getattr(recommendation, "action", "") == "BUY":
        market_view = "可做"
    elif recommendation is not None and getattr(recommendation, "action", "") in {"REDUCE", "SELL"}:
        market_view = "先减仓"

    capital_lines = ["持仓与大盘", ""]
    if snapshot is not None:
        capital_lines.extend(
            [
                f"大盘结论：{market_view}",
                f"资金：净流入 {snapshot.main_inflow / 1e8:.2f} 亿 | 换手 {snapshot.turnover:.2f}% | 成交额 {snapshot.amount / 1e8:.2f} 亿",
                f"热度：{snapshot.heat_score:.1f} | 涨跌 {snapshot.pct_change:.2f}%",
            ]
        )
        if recommendation is not None:
            capital_lines.append(f"焦点：{recommendation.stock_name} / {getattr(recommendation, 'stock_pool', '') or '趋势股'}")
        capital_headline = market_view
        capital_detail = f"净流入 {snapshot.main_inflow / 1e8:.2f} 亿 / 换手 {snapshot.turnover:.2f}%"
    else:
        capital_lines.append("大盘结论：还没有市场快照，先刷新行情后再判断。")
        capital_headline = "先等"
        capital_detail = "等待行情数据"

    decision_lines = ["买卖点结论", ""]
    if recommendation is not None:
        action_text = display_action_fn(recommendation.action) if callable(display_action_fn) else recommendation.action
        label_text = display_label_fn(recommendation.label) if callable(display_label_fn) else recommendation.label
        decision_lines.extend(
            [
                f"当前动作：{action_text} | 信号标签：{label_text}",
                f"建仓买点：{getattr(recommendation, 'buy_point', '') or f'{(recommendation.entry_price or recommendation.close):.2f} 附近确认后再买'}",
                f"持仓加点：{getattr(recommendation, 'add_point', '') or '放量走强后再考虑加仓'}",
                f"减仓卖点：{getattr(recommendation, 'sell_point', '') or f'接近 {(recommendation.target_price or recommendation.close * 1.1):.2f} 分批兑现'}",
                f"止损风控：{getattr(recommendation, 'risk_line', '') or f'跌破 {(recommendation.stop_price or recommendation.close * 0.95):.2f} 先撤'}",
                f"消息催化：{recommendation.catalyst or '暂时没有强催化，主要看量价确认'}",
            ]
        )
        decision_headline = action_text
        decision_detail = f"{getattr(recommendation, 'stock_pool', '') or '趋势股'} / 决策分 {getattr(recommendation, 'dragon_decision_score', recommendation.total_score):.1f}"
    elif latest_signal is not None:
        label_text = display_label_fn(latest_signal.label) if callable(display_label_fn) else latest_signal.label
        decision_lines.extend([f"- 最新信号：{label_text}", f"- 触发原因：{latest_signal.reason}"])
        decision_headline = "观察"
        decision_detail = label_text
    else:
        decision_lines.append("- 还没有明确买卖点，先等信号和量价共振。")
        decision_headline = "先等"
        decision_detail = "等待信号"

    return {
        "capital_text": "\n".join(capital_lines),
        "capital_headline": capital_headline,
        "capital_detail": capital_detail,
        "decision_text": "\n".join(decision_lines),
        "decision_headline": decision_headline,
        "decision_detail": decision_detail,
    }


def select_recommend_action_targets(rows: list, execution_status_by_symbol: dict[str, str]) -> dict[str, object]:
    buy_rows = [item for item in rows if getattr(item, "action", "") == "BUY"]
    pending_review = [
        item for item in buy_rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "\u5f85\u89c2\u5bdf") == "\u5f85\u89c2\u5bdf"
    ]
    failed_rows = [
        item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "\u63d0\u4ea4\u5931\u8d25"
    ]
    reviewing_rows = [
        item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "\u5df2\u9001\u5ba1"
    ]

    sort_key = lambda item: (
        float(getattr(item, "dragon_decision_score", getattr(item, "total_score", 0.0))),
        float(getattr(item, "total_score", 0.0)),
    )
    priority_buy = max(pending_review, key=sort_key) if pending_review else None
    failed_pick = max(failed_rows, key=sort_key) if failed_rows else None
    review_pick = max(reviewing_rows, key=sort_key) if reviewing_rows else None
    return {
        "priority_buy": priority_buy,
        "failed_pick": failed_pick,
        "review_pick": review_pick,
        "pending_review_count": len(pending_review),
        "failed_count": len(failed_rows),
        "reviewing_count": len(reviewing_rows),
    }


def build_recommend_bucket_snapshot(rows: list, execution_status_by_symbol: dict[str, str]) -> dict[str, str]:
    def score_of(item) -> float:
        return float(getattr(item, "dragon_decision_score", getattr(item, "total_score", 0.0)))

    core_rows = sorted(
        [
            item
            for item in rows
            if getattr(item, "action", "") == "BUY"
            and execution_status_by_symbol.get(getattr(item, "symbol", ""), "\u5f85\u89c2\u5bdf") in {"\u5f85\u89c2\u5bdf", "\u5df2\u9001\u5ba1"}
        ],
        key=score_of,
        reverse=True,
    )
    watch_rows = sorted(
        [item for item in rows if getattr(item, "action", "") in {"WATCH", "HOLD"}],
        key=score_of,
        reverse=True,
    )
    risk_rows = sorted(
        [
            item
            for item in rows
            if getattr(item, "action", "") in {"REDUCE", "SELL"}
            or execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "\u63d0\u4ea4\u5931\u8d25"
        ],
        key=score_of,
        reverse=True,
    )

    def render_block(title: str, empty_text: str, block_rows: list, mode: str) -> str:
        lines = [title, ""]
        if not block_rows:
            lines.append(f"1. {empty_text}")
            return "\n".join(lines)
        focus = block_rows[0]
        lines.append(
            f"- \u7ec4\u5185\u6570\u91cf: {len(block_rows)} | \u7126\u70b9: {focus.stock_name} | \u51b3\u7b56\u5206 {score_of(focus):.1f}"
        )
        if mode == "core":
            lines.append("- \u7ee7\u7eed\u8ddf\u3002")
        elif mode == "watch":
            lines.append("- \u53ea\u89c2\u5bdf\u3002")
        else:
            lines.append("- \u9632\u5207\u6362\u3002")
        lines.append("")
        for index, item in enumerate(block_rows[:3], start=1):
            status = execution_status_by_symbol.get(getattr(item, "symbol", ""), "\u5f85\u89c2\u5bdf")
            lines.append(
                f"{index}. {item.stock_name} | {(item.theme_name or '\u672a\u5206\u7c7b')} | {getattr(item, 'primary_strategy', '') or '\u63d8\u9f99\u51b3\u7b56'} | "
                f"{status} | {score_of(item):.1f}"
            )
        return "\n".join(lines)

    return {
        "core": render_block("\u6838\u5fc3\u6267\u884c", "\u6682\u65e0\u53ef\u6267\u884c\u4e70\u5165\u6807\u7684\u3002", core_rows, "core"),
        "watch": render_block("\u89c2\u5bdf\u8ddf\u8e2a", "\u6682\u65e0\u89c2\u5bdf\u6216\u6301\u6709\u8ddf\u8e2a\u6807\u7684\u3002", watch_rows, "watch"),
        "risk": render_block("\u98ce\u9669\u56de\u907f", "\u6682\u65e0\u9700\u8981\u4f18\u5148\u5904\u7f6e\u7684\u98ce\u9669\u6807\u7684\u3002", risk_rows, "risk"),
    }


def refresh_recommend_bucket_panels(window) -> None:
    if not hasattr(window, "recommend_core_bucket_text"):
        return
    snapshot = build_recommend_bucket_snapshot(
        getattr(window, "daily_pool_rows", []),
        getattr(window, "execution_status_by_symbol", {}),
    )
    _set_plain_text_if_changed(window.recommend_core_bucket_text, snapshot["core"])
    _set_plain_text_if_changed(window.recommend_watch_bucket_text, snapshot["watch"])
    _set_plain_text_if_changed(window.recommend_risk_bucket_text, snapshot["risk"])


def _recommendation_signal_brief(item) -> str:
    if item is None:
        return "暂无"
    tag = getattr(item, "mainline_tag", "") or getattr(item, "theme_name", "") or "未分类"
    return f"{item.stock_name} | {tag} | {_mainline_flow_brief(item)}"


def build_recommend_review_snapshot(rows: list, execution_status_by_symbol: dict[str, str], submission_records: list[dict], plan) -> dict[str, str]:
    recap_summary = summarize_trade_recap(submission_records, [], [], [])
    execution_summary = {
        "reviewing": sum(1 for value in execution_status_by_symbol.values() if value == "已送审"),
        "submitted": sum(1 for value in execution_status_by_symbol.values() if value == "已提交"),
        "failed": sum(1 for value in execution_status_by_symbol.values() if value == "提交失败"),
    }
    pending_rows = [
        item for item in rows if getattr(item, "action", "") == "BUY" and execution_status_by_symbol.get(getattr(item, "symbol", ""), "待观察") == "待观察"
    ]
    focus_buy = pending_rows[0] if pending_rows else (rows[0] if rows else None)
    focus_watch = next((item for item in rows if getattr(item, "action", "") in {"WATCH", "HOLD"}), None)
    focus_risk = next(
        (item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "提交失败"),
        next((item for item in rows if getattr(item, "action", "") in {"REDUCE", "SELL"}), None),
    )

    return {
        "review": _brief_panel_text(
            "当日执行复盘",
            f"送审 {execution_summary['reviewing']} | 提交 {execution_summary['submitted']} | 失败 {execution_summary['failed']}",
            (
                f"失败单 {focus_risk.stock_name}"
                if execution_summary["failed"] and focus_risk is not None
                else (
                    f"已提交重点 {', '.join(recap_summary['focus_symbols'])}"
                    if recap_summary["focus_symbols"]
                    else "当前没有明显失败单"
                )
            ),
            recap_summary["review_flags"][0] if recap_summary["review_flags"] else "先完成送审和提交，再看成交反馈。",
        ),
        "next_day": _brief_panel_text(
            "次日预案",
            f"继续跟 {_recommendation_signal_brief(focus_watch)}",
            f"防切换 {_recommendation_signal_brief(focus_risk)}",
            f"只观察 {_recommendation_signal_brief(focus_buy)}",
        ),
    }


def build_detail_workspace_snapshot(
    symbol: str,
    recommendation,
    execution_status: str,
    submission_records: list[dict],
    latest_signal,
    backtest_result,
    source_path: str = "",
    order_intent=None,
) -> dict[str, str]:
    display_symbol = symbol or "--"
    if recommendation is not None:
        decision_lines = [
            "\u4ea4\u6613\u51b3\u7b56\u753b\u50cf",
            "",
            f"- \u6807\u7684: {getattr(recommendation, 'stock_name', display_symbol)} ({getattr(recommendation, 'stock_id', display_symbol)})",
            f"- \u9898\u6750 / \u7b56\u7565 / \u80a1\u6c60: {(getattr(recommendation, 'theme_name', '') or '\u672a\u5206\u7c7b')} / {getattr(recommendation, 'primary_strategy', '') or '\u63d8\u9f99\u51b3\u7b56'} / {getattr(recommendation, 'stock_pool', '') or '\u8d8b\u52bf\u80a1'}",
            f"- \u5f53\u524d\u52a8\u4f5c: {getattr(recommendation, 'action', '')} | \u6267\u884c\u72b6\u6001: {execution_status}",
            (
                f"- \u8bc4\u5206: \u603b\u5206 {getattr(recommendation, 'total_score', 0.0):.1f} | "
                f"\u51b3\u7b56\u5206 {getattr(recommendation, 'dragon_decision_score', getattr(recommendation, 'total_score', 0.0)):.1f} | "
                f"\u80a1\u6c60\u5206 {getattr(recommendation, 'pool_score', 0.0):.1f}"
            ),
            (
                f"- \u8ba1\u5212\u4ef7\u4f4d: \u5165\u573a {(getattr(recommendation, 'entry_price', None) or getattr(recommendation, 'close', 0.0)):.2f} | "
                f"\u6b62\u635f {(getattr(recommendation, 'stop_price', None) or 0.0):.2f} | "
                f"\u76ee\u6807 {(getattr(recommendation, 'target_price', None) or 0.0):.2f}"
            ),
            f"- \u50ac\u5316: {getattr(recommendation, 'catalyst', '') or '\u91cf\u4ef7\u5171\u632f'}",
            f"- \u4e70\u70b9: {getattr(recommendation, 'buy_point', '') or '\u7b49\u5f85\u5165\u573a\u786e\u8ba4'}",
            f"- \u52a0\u4ed3: {getattr(recommendation, 'add_point', '') or '\u7b49\u5f85\u8d8b\u52bf\u5ef6\u7eed'}",
            f"- \u5356\u70b9: {getattr(recommendation, 'sell_point', '') or '\u6309\u8ba1\u5212\u76ee\u6807\u5206\u6279\u5904\u7406'}",
            f"- \u98ce\u63a7: {getattr(recommendation, 'risk_line', '') or '\u8bbe\u597d\u6b62\u635f\u7ebf'}",
            f"- \u7406\u7531: {getattr(recommendation, 'rationale', '') or '\u6682\u65e0\u9644\u52a0\u8bf4\u660e'}",
        ]
    else:
        decision_lines = [
            "\u4ea4\u6613\u51b3\u7b56\u753b\u50cf",
            "",
            f"- \u6807\u7684: {display_symbol}",
            "- \u5f53\u524d\u8fd8\u6ca1\u6709\u548c\u63a8\u8350\u6c60\u6216\u4ea4\u6613\u8ba1\u5212\u5efa\u7acb\u8054\u52a8\u3002",
        ]
    if source_path:
        decision_lines.append(f"- \u6570\u636e\u6e90: {source_path}")

    symbol_records = [item for item in submission_records if item.get("symbol") == symbol]
    execution_lines = [
        "\u6267\u884c\u72b6\u6001\u56de\u653e",
        "",
        f"- \u5f53\u524d\u72b6\u6001: {execution_status}",
        f"- \u6267\u884c\u8bb0\u5f55: {len(symbol_records)} \u6761",
    ]
    if order_intent is not None:
        execution_lines.append(
            f"- \u5f85\u6267\u884c\u59d4\u6258: {getattr(order_intent, 'side', '')} {getattr(order_intent, 'quantity', 0)} @ {getattr(order_intent, 'price', 0.0):.2f}"
        )
    if symbol_records:
        execution_lines.extend(["", "\u6700\u8fd1\u56de\u653e"])
        for item in symbol_records[-3:]:
            execution_lines.append(
                f"- {item.get('timestamp', '')} | {item.get('order_status', '')}/{item.get('fill_status', '')} | {item.get('message', '') or item.get('failure_reason', '')}"
            )
    else:
        execution_lines.append("- \u6682\u65e0\u8be5\u6807\u7684\u9001\u5ba1\u6216\u63d0\u4ea4\u8bb0\u5f55\u3002")

    conclusion_lines = [
        "\u590d\u76d8\u7ed3\u8bba",
        "",
    ]
    if latest_signal is not None:
        conclusion_lines.extend(
            [
                f"- \u6700\u65b0\u4fe1\u53f7: {getattr(latest_signal, 'date', '')} | {getattr(latest_signal, 'label', '')} | \u8bc4\u5206 {getattr(latest_signal, 'score', 0)}",
                f"- \u4fe1\u53f7\u539f\u56e0: {getattr(latest_signal, 'reason', '')}",
            ]
        )
    else:
        conclusion_lines.append("- \u6700\u8fd1 K \u7ebf\u4e2d\u6682\u65e0\u660e\u786e\u4fe1\u53f7\u3002")
    if backtest_result is not None:
        trade_count = len(getattr(backtest_result, "trades", []))
        conclusion_lines.extend(
            [
                f"- \u56de\u6d4b\u8868\u73b0: \u4ea4\u6613 {trade_count} \u7b14 | \u603b\u6536\u76ca {getattr(backtest_result, 'total_return', 0.0):.2%} | \u80dc\u7387 {getattr(backtest_result, 'win_rate', 0.0):.2%}",
                f"- \u98ce\u9669\u53c2\u8003: \u6700\u5927\u56de\u64a4 {getattr(backtest_result, 'max_drawdown', 0.0):.2%}",
            ]
        )
    else:
        conclusion_lines.append("- \u6682\u65e0\u56de\u6d4b\u7ed3\u679c\uff0c\u53ef\u5148\u8fd0\u884c\u5f53\u524d\u6807\u7684\u56de\u6d4b\u3002")
    conclusion_lines.extend(["", "\u4e0b\u4e00\u6b65"])
    if execution_status == "\u63d0\u4ea4\u5931\u8d25":
        conclusion_lines.append("1. \u5148\u590d\u6838\u4ef7\u683c\u3001\u6570\u91cf\u548c\u6743\u9650\u3002")
    elif execution_status == "\u5df2\u63d0\u4ea4":
        conclusion_lines.append("1. \u4e3b\u770b\u6210\u4ea4\u8d28\u91cf\u548c\u6301\u4ed3\u53d8\u5316\u3002")
    elif recommendation is not None and getattr(recommendation, "action", "") == "BUY":
        conclusion_lines.append("1. \u5148\u9001\u5ba1\uff0c\u518d\u6838\u5bf9\u4ef7\u91cf\u3002")
    else:
        conclusion_lines.append("1. \u4ee5\u89c2\u5bdf\u4e3a\u4e3b\uff0c\u7ee7\u7eed\u8ddf\u8e2a\u3002")
    return {
        "decision": "\n".join(decision_lines),
        "execution": "\n".join(execution_lines),
        "conclusion": "\n".join(conclusion_lines),
    }


def refresh_recommend_review_panels(window) -> None:
    if not hasattr(window, "recommend_review_text"):
        return
    plan = getattr(window, "current_trade_plan", None)
    if plan is None:
        return
    snapshot = build_recommend_review_snapshot(
        getattr(window, "daily_pool_rows", []),
        getattr(window, "execution_status_by_symbol", {}),
        getattr(window, "order_submission_records", []),
        plan,
    )
    _set_plain_text_if_changed(window.recommend_review_text, snapshot["review"])
    _set_plain_text_if_changed(window.recommend_next_day_text, snapshot["next_day"])


def refresh_recommend_dispatch_panels(window, plan) -> None:
    if not hasattr(window, "recommend_dispatch_text") or not hasattr(window, "recommend_focus_review_text"):
        return
    selected_row = None
    if hasattr(window, "daily_pool_table"):
        row_index = window.daily_pool_table.currentRow()
        filtered_rows = window._filtered_daily_pool_rows() if hasattr(window, "_filtered_daily_pool_rows") else []
        if 0 <= row_index < len(filtered_rows):
            selected_row = filtered_rows[row_index]
    snapshot = build_recommend_dispatch_snapshot(
        getattr(window, "daily_pool_rows", []),
        plan,
        getattr(window, "execution_status_by_symbol", {}),
        selected_row=selected_row,
        display_action_fn=getattr(window, "_display_action", None),
    )
    _set_plain_text_if_changed(window.recommend_dispatch_text, snapshot["headline"])
    _set_plain_text_if_changed(window.recommend_focus_review_text, snapshot["focus"])
    if hasattr(window, "recommend_queue_text"):
        _set_plain_text_if_changed(window.recommend_queue_text, snapshot["queue"])


def refresh_action_flow_cards(window, plan) -> None:
    if not hasattr(window, "action_flow_cards"):
        return
    buy_focus = plan.decisions[0] if plan.decisions else None
    watch_focus = next((item for item in window.daily_pool_rows if item.action == "WATCH"), None)
    reduce_focus = next((item for item in plan.position_advice if item.action == "REDUCE"), None)
    sell_focus = next((item for item in plan.position_advice if item.action == "SELL"), None)
    buy_count = len(plan.decisions)
    watch_count = sum(1 for item in window.daily_pool_rows if item.action == "WATCH")
    reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
    sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")

    window.action_flow_cards["BUY"].set_data(
        f"{buy_count} 只",
        f"焦点: {buy_focus.stock_name if buy_focus else '暂无'}",
        "优先从主线前排与高决策分候选中开仓。" if buy_focus else "当前暂无符合条件的新开仓建议。",
    )
    window.action_flow_cards["WATCH"].set_data(
        f"{watch_count} 只",
        f"焦点: {watch_focus.stock_name if watch_focus else '暂无'}",
        "继续观察量价、题材和资金是否共振。" if watch_focus else "当前观察池为空。",
    )
    window.action_flow_cards["REDUCE"].set_data(
        f"{reduce_count} 只",
        f"焦点: {reduce_focus.stock_name if reduce_focus else '暂无'}",
        "已有浮盈且题材掉队时优先分批减仓。" if reduce_focus else "当前没有减仓建议。",
    )
    window.action_flow_cards["SELL"].set_data(
        f"{sell_count} 只",
        f"焦点: {sell_focus.stock_name if sell_focus else '暂无'}",
        "跌破防守位或出现陷阱信号时优先离场。" if sell_focus else "当前没有明确离场建议。",
    )


def refresh_priority_cards(window, plan) -> None:
    if not hasattr(window, "priority_cards"):
        return
    top_theme = window.theme_heat_rows[0] if getattr(window, "theme_heat_rows", None) else None
    top_pick = window.daily_pool_rows[0] if window.daily_pool_rows else None
    strategy_counter: dict[str, int] = {}
    for item in window.daily_pool_rows:
        name = getattr(item, "primary_strategy", "") or "掘龙决策"
        strategy_counter[name] = strategy_counter.get(name, 0) + 1
    top_strategy_name, top_strategy_count = ("暂无", 0)
    if strategy_counter:
        top_strategy_name, top_strategy_count = max(strategy_counter.items(), key=lambda pair: pair[1])

    pulse = plan.market_pulse
    window.priority_cards["market"].set_data(
        f"{pulse.sentiment_score:.1f}",
        f"状态: {pulse.sentiment_label} / {pulse.market_regime}",
        f"下一步: 总仓位上限 {pulse.max_total_exposure:.0%} | 风险 {pulse.risk_level}",
    )
    window.priority_cards["theme"].set_data(
        f"{getattr(top_theme, 'strength_score', 0.0):.1f}" if top_theme else "--",
        f"状态: {top_theme.theme_name if top_theme else '暂无'}",
        (
            f"下一步: 窗口 {getattr(top_theme, 'window_score', 0.0):.1f} | 风险 {getattr(top_theme, 'risk_flag', '--')} | 龙头数 {getattr(top_theme, 'leader_count', 0)}"
            if top_theme
            else "下一步: 等待主线生成。"
        ),
    )
    window.priority_cards["strategy"].set_data(
        f"{top_strategy_count} 只",
        f"状态: {top_strategy_name}",
        "下一步: 优先复核当前最拥挤的打法。",
    )
    window.priority_cards["focus"].set_data(
        f"{getattr(top_pick, 'dragon_decision_score', getattr(top_pick, 'total_score', 0.0)):.1f}" if top_pick else "--",
        f"状态: {top_pick.stock_name if top_pick else '暂无'}",
        (
            f"下一步: {getattr(top_pick, 'primary_strategy', '') or '掘龙决策'} | {top_pick.theme_name or '未分类'}"
            if top_pick
            else "下一步: 等待推荐池刷新。"
        ),
    )
    refresh_strategy_path_panel(window, plan, top_theme, top_strategy_name, top_pick)


def refresh_overview_priority_cards(window, pool: list, recommendations: list, top_theme: str) -> None:
    if not hasattr(window, "overview_priority_cards"):
        return
    buy_rows = [item for item in recommendations if getattr(item, "action", "") == "BUY"]
    hold_rows = [item for item in recommendations if getattr(item, "action", "") == "HOLD"]
    watch_rows = [item for item in recommendations if getattr(item, "action", "") == "WATCH"]
    reduce_rows = [item for item in recommendations if getattr(item, "action", "") == "REDUCE"]
    sell_rows = [item for item in recommendations if getattr(item, "action", "") == "SELL"]
    avg_heat = (sum(getattr(item, "heat_score", 0.0) for item in pool) / len(pool)) if pool else 0.0

    top_buy = buy_rows[0] if buy_rows else None
    top_hold = hold_rows[0] if hold_rows else (watch_rows[0] if watch_rows else None)
    top_reduce = reduce_rows[0] if reduce_rows else None
    top_sell = sell_rows[0] if sell_rows else None

    market_text = "可做" if avg_heat >= 75 else ("轻仓" if avg_heat >= 60 else "谨慎")
    hold_note = "先看持仓延续，不追高。" if hold_rows else "没有明确持仓票时，先跟踪观察股。"
    top_theme_name = getattr(top_buy, "theme_name", "") or getattr(top_hold, "theme_name", "") or top_theme or "待确认"

    window.overview_priority_cards["market"].set_data(
        f"建仓 {len(buy_rows)}" if recommendations else "--",
        f"{market_text} | {top_buy.stock_name if top_buy else '暂无标的'}",
        (
            f"买点 {getattr(top_buy, 'buy_point', '') or '等待突破确认'} | 主线 {getattr(top_buy, 'theme_name', '') or top_theme_name}"
            if top_buy
            else f"市场节奏 {market_text} | 暂无明确新开仓票"
        ),
    )
    window.overview_priority_cards["theme"].set_data(
        f"持有 {len(hold_rows) or len(watch_rows)}" if recommendations else "--",
        f"跟踪位 | {top_hold.stock_name if top_hold else '暂无标的'}",
        (
            f"加点 {getattr(top_hold, 'add_point', '') or '沿趋势持有'} | {getattr(top_hold, 'stock_pool', '') or '趋势股'}"
            if top_hold
            else hold_note
        ),
    )
    window.overview_priority_cards["strategy"].set_data(
        f"减仓 {len(reduce_rows)}" if recommendations else "--",
        f"风险回收 | {top_reduce.stock_name if top_reduce else '暂无标的'}",
        (
            f"减点 {getattr(top_reduce, 'sell_point', '') or '冲高乏力先减一半'} | 控回撤"
            if top_reduce
            else "暂无明显减仓票，持仓仍以跟踪为主。"
        ),
    )
    window.overview_priority_cards["focus"].set_data(
        f"离场 {len(sell_rows)}" if recommendations else "--",
        f"防守位 | {top_sell.stock_name if top_sell else '暂无标的'}",
        (
            f"风控 {getattr(top_sell, 'risk_line', '') or '跌破防守线直接离场'} | 主线 {top_theme_name}"
            if top_sell
            else f"暂无明确清仓票 | 主线仍看 {top_theme_name}"
        ),
    )


def _strategy_priority_text(strategy_score: float, strategy_count: int) -> str:
    if strategy_score >= 85 and strategy_count >= 2:
        return "高优先，今天可以先盯这套战法。"
    if strategy_score >= 72:
        return "中优先，等确认信号后再出手。"
    return "低优先，先当辅助视角使用。"


def _strategy_mainline_summary(window, focus_row, strategy_count: int) -> str:
    mainline_tag = focus_row.mainline_tag or focus_row.theme_name or "未分类"
    mainline_rank = getattr(focus_row, "mainline_rank", focus_row.theme_rank) or "--"
    leader_level = window._display_leader_level(getattr(focus_row, "leader_level", ""))
    return f"{mainline_tag} / 主线位 {mainline_rank} / {leader_level} / 命中 {strategy_count} 只"


def _strategy_execution_summary(window, focus_row) -> str:
    action = window._display_action(focus_row.action)
    return f"{action} · 关注 {getattr(focus_row, 'buy_point', '') or getattr(focus_row, 'next_focus', '') or '主线节奏与量价配合'}"


def _strategy_attention_focus(focus_row) -> str:
    return getattr(focus_row, 'next_focus', '') or '先盯主线、承接和量价是否继续配合。'


def _strategy_confirm_signal_text(focus_row) -> str:
    candidates = [
        getattr(focus_row, 'buy_point', ''),
        getattr(focus_row, 'next_focus', ''),
        getattr(focus_row, 'catalyst', ''),
    ]
    for text in candidates:
        text = (text or '').strip()
        if text:
            return text
    return '等待量能、承接和主线共振。'


def _strategy_invalidation_signal_text(focus_row) -> str:
    candidates = [
        getattr(focus_row, 'invalidation_reason', ''),
        getattr(focus_row, 'risk_line', ''),
        getattr(focus_row, 'mainline_risk_flag', ''),
    ]
    for text in candidates:
        text = (text or '').strip()
        if text:
            return text
    return '跌破计划防守线，或主线窗口继续收缩时先退出。'


def refresh_strategy_focus_detail(window, strategy_score_fields) -> None:
    if not hasattr(window, "strategy_detail_text"):
        return
    strategy_name = window.strategy_detail_combo.currentText() if hasattr(window, "strategy_detail_combo") else "掘龙决策"
    canonical_strategy_name = _canonical_strategy_name(strategy_name)
    field_name = strategy_score_fields.get(canonical_strategy_name, "dragon_decision_score")
    selected_row = None
    if hasattr(window, "daily_pool_table"):
        row_index = window.daily_pool_table.currentRow()
        source_rows = window._filtered_daily_pool_rows()
        if 0 <= row_index < len(source_rows):
            selected_row = source_rows[row_index]
    ranked = sorted(window.daily_pool_rows, key=lambda item: getattr(item, field_name, 0.0), reverse=True)
    focus_row = selected_row or (ranked[0] if ranked else None)
    if focus_row is None:
        _set_plain_text_if_changed(window.strategy_detail_text, "等待机会池同步后更新。")
        return
    strategy_count = sum(
        1
        for item in window.daily_pool_rows
        if _canonical_strategy_name(getattr(item, "primary_strategy", "") or "掘龙决策") == canonical_strategy_name
    )
    strategy_score = float(getattr(focus_row, field_name, 0.0) or 0.0)
    top_examples = ranked[:3]
    example_names = (
        " / ".join(
            f"{item.stock_name}（{item.theme_name or '未分类'} / {window._display_action(item.action)}）"
            for item in top_examples
        )
        or focus_row.stock_name
    )
    priority_text = _strategy_priority_text(strategy_score, strategy_count)
    mainline_summary = _strategy_mainline_summary(window, focus_row, strategy_count)
    execution_summary = _strategy_execution_summary(window, focus_row)
    attention_focus = _strategy_attention_focus(focus_row)
    lines = [
        "战法定位",
        f"- 产品定位：{_strategy_product_positioning(canonical_strategy_name)}",
        f"- 风险等级：{_strategy_risk_level(canonical_strategy_name, focus_row)}",
        f"- 适合资金：{_strategy_capital_style(canonical_strategy_name)}",
        f"- 仓位建议：{_strategy_position_hint(canonical_strategy_name, focus_row)}",
        f"- 禁做情形：{_strategy_no_go_text(canonical_strategy_name, focus_row)}",
        "",
        "商品说明",
        f"- 适用行情：{_strategy_applicable_market(canonical_strategy_name, focus_row)}",
        f"- 容量上限：{_strategy_capacity_limit(canonical_strategy_name, focus_row)}",
        f"- 标准动作：{_strategy_standard_action(canonical_strategy_name, focus_row)}",
        f"- 失败样本：{_strategy_failure_sample_text(canonical_strategy_name, focus_row)}",
        "",
        "当前动作",
        f"- 结论：{priority_text}",
        f"- 主线：{mainline_summary}",
        f"- 动作：{execution_summary}",
        "",
        "怎么用",
        f"- 场景：{_strategy_scene_copy(canonical_strategy_name)}",
        f"- 确认：{_strategy_confirm_signal_text(focus_row)}",
        f"- 失效：{_strategy_invalidation_signal_text(focus_row)}",
        f"- 仓位：{_strategy_position_hint(canonical_strategy_name, focus_row)}",
        "",
        "为什么是它",
        f"- 焦点：{example_names}",
        f"- 归因：{_strategy_reason_copy(focus_row, canonical_strategy_name)}",
        f"- 催化：{focus_row.catalyst or '量价共振'}",
        f"- 风险：{getattr(focus_row, 'mainline_risk_flag', '--')} | {focus_row.rationale or '暂无附加说明'}",
        "",
        "评分板",
        f"- 战法 {strategy_score:.1f} | 综合 {focus_row.total_score:.1f} | 窗口 {getattr(focus_row, 'mainline_window_score', 0.0):.1f}",
        f"- 龙头 {getattr(focus_row, 'leader_model_score', 0.0):.1f} | 主力 {getattr(focus_row, 'main_force_score', 0.0):.1f} | 打板 {getattr(focus_row, 'board_attack_score', 0.0):.1f}",
        f"- 低吸 {getattr(focus_row, 'value_recovery_score', 0.0):.1f} | 尾盘 {getattr(focus_row, 'tail_buy_score', 0.0):.1f} | 一日 {getattr(focus_row, 'one_day_hold_score', 0.0):.1f}",
        "",
    ]
    tripwire_metrics = one_day_hold_tripwire_metrics(focus_row)
    if tripwire_metrics:
        lines.extend(
            [
                "隔日三段判断",
                f"- 博弈等级：{one_day_hold_grade(focus_row) or '待确认'}",
                *[f"- {label}：{value:.1f} / 100 | {note}" for label, value, note in tripwire_metrics],
                f"- 盘中节奏：{attention_focus}",
                "",
            ]
        )
    tail_runtime_panel = tail_buy_runtime_panel_lines(focus_row)
    if tail_runtime_panel:
        lines.extend(
            [
                "尾盘执行面板",
                *[f"- {item}" for item in tail_runtime_panel],
                "",
            ]
        )
    tail_checklist = tail_buy_execution_checklist(focus_row)
    if tail_checklist:
        lines.extend(
            [
                "尾盘 checklist",
                *[f"- {item}" for item in tail_checklist],
                "",
            ]
        )
    lines.append("该战法 Top 3")
    for item in top_examples:
        lines.append(
            f"- {item.stock_name} | {getattr(item, field_name, 0.0):.1f} | {item.theme_name or '未分类'} | {window._display_action(item.action)}"
        )
    _set_plain_text_if_changed(window.strategy_detail_text, "\n".join(lines))


def populate_market_depth_texts(window, rows: list) -> None:
    if hasattr(window, "market_buy_text"):
        buy_candidates = [row for row in rows if getattr(row, "signal_label", "") == "RECLAIM_LONG" or getattr(row, "action", "") == "BUY"]
        buy_lines = ["今天能不能买", ""]
        if buy_candidates:
            buy_lines.append(f"- 今天有 {min(len(buy_candidates), 3)} 只票可以先看。")
            for index, row in enumerate(buy_candidates[:3], start=1):
                buy_lines.append(
                    f"{index}. {row.stock_name} | 涨跌 {row.pct_change:.2f}% | 净流入 {row.main_inflow / 1e8:.2f} 亿 | 换手 {row.turnover:.1f}%"
                )
        else:
            buy_lines.extend(["- 还没有明确买点。", "- 先等主线和量价一起确认。"])
        _set_plain_text_if_changed(window.market_buy_text, "\n".join(buy_lines))

    if hasattr(window, "market_sell_text"):
        hot_rows = sorted(rows[:8], key=lambda item: abs(getattr(item, "pct_change", 0.0)), reverse=True)
        sell_lines = ["减仓和卖点", ""]
        if hot_rows:
            sell_lines.append("- 先处理涨太快和转弱的票。")
            for row in hot_rows[:4]:
                action = "冲高看减" if row.pct_change > 0 else "跌弱先撤"
                sell_lines.append(f"- {row.stock_name} | {action} | 涨跌 {row.pct_change:.2f}% | 换手 {row.turnover:.1f}%")
        else:
            sell_lines.append("- 当前没有明显减仓提示。")
        _set_plain_text_if_changed(window.market_sell_text, "\n".join(sell_lines))

    if hasattr(window, "market_breadth_text"):
        news_lines = ["消息面", ""]
        if rows:
            news_lines.append("- 只保留会影响买卖点的催化消息。")
        seen = 0
        for row in rows[:6]:
            symbol_news = window.news_catalysts.get(row.symbol, [])
            if symbol_news:
                item = symbol_news[0]
                source = getattr(item, "source", "") or "来源未知"
                published = getattr(item, "published_at", "") or ""
                meta = " / ".join(part for part in [source, published] if part)
                news_lines.append(f"- {row.stock_name}: {item.title}{f' ({meta})' if meta else ''}")
                seen += 1
                if seen >= 3:
                    break
        if seen == 0:
            news_lines.append("- 目前没有新增强催化，先看价格和资金。")
        _set_plain_text_if_changed(window.market_breadth_text, "\n".join(news_lines))


def render_leaderboard_cards(window, rows: list) -> None:
    if not hasattr(window, "market_leaderboard_cards"):
        return
    visible_rows = rows[:3]
    for index, card in enumerate(window.market_leaderboard_cards):
        if index < len(visible_rows):
            row = visible_rows[index]
            display_row = row
            prepend_badge = getattr(window, "_prepend_card_badge", None)
            if callable(prepend_badge):
                symbol = getattr(row, "symbol", "") or ""
                stock_name = getattr(row, "stock_name", "") or ""
                if symbol and stock_name:
                    try:
                        display_row = SimpleNamespace(**vars(row))
                    except TypeError:
                        display_row = SimpleNamespace(**getattr(row, "__dict__", {}))
                    if getattr(display_row, "stock_name", ""):
                        display_row.stock_name = prepend_badge(str(stock_name), symbol)
            strategy_name = getattr(row, "primary_strategy", "") or getattr(row, "strategy_tag", "")
            decision_score = getattr(row, "dragon_decision_score", getattr(row, "heat_score", 0.0))
            signature = (
                "row",
                f"TOP {index + 1}",
                getattr(row, "stock_name", ""),
                getattr(row, "stock_id", ""),
                strategy_name,
                getattr(row, "fund_model", ""),
                f"{decision_score:.1f}",
                f"{getattr(row, 'heat_score', 0.0):.1f}",
                f"{getattr(row, 'pct_change', 0.0):.2f}",
                f"{getattr(row, 'main_inflow', 0.0):.2f}",
            )
            card.show()
            if getattr(card, "_leaderboard_signature", None) != signature:
                card.set_row(f"TOP {index + 1}", display_row)
                card._leaderboard_signature = signature
        else:
            signature = ("message", "等待候选同步", "当前暂无入选标的，首轮扫描后会在这里显示前排。")
            card.show()
            if getattr(card, "_leaderboard_signature", None) != signature:
                card.set_message("等待候选同步", "当前暂无入选标的，首轮扫描后会在这里显示前排。")
                card._leaderboard_signature = signature


def refresh_strategy_pack_panels(window, strategy_score_fields) -> None:
    if not hasattr(window, "strategy_pack_cards"):
        return
    rows = list(window.daily_pool_rows)
    for strategy_name, field_name in strategy_score_fields.items():
        card = window.strategy_pack_cards.get(strategy_name)
        if card is None:
            continue
        ranked = sorted(rows, key=lambda item: getattr(item, field_name, 0.0), reverse=True)
        if not ranked:
            signature = ("empty", "等待机会池同步后更新。")
            if getattr(card, "_strategy_signature", None) != signature:
                card.set_empty("等待机会池同步后更新。")
                card._strategy_signature = signature
            continue
        top = ranked[0]
        primary_count = sum(
            1
            for item in ranked
            if _canonical_strategy_name(getattr(item, "primary_strategy", "") or "掘龙决策") == _canonical_strategy_name(strategy_name)
        )
        lines = []
        for item in ranked[:3]:
            lines.append(
                f"- {item.stock_name} | {getattr(item, field_name, 0.0):.1f} | {item.theme_name or '未分类'} | {window._display_action(item.action)}"
            )
        lines.append(f"逻辑：{top.rationale[:88]}")
        signature = (
            "summary",
            strategy_name,
            primary_count,
            f"{top.stock_name} ({top.stock_id})",
            f"{getattr(top, field_name, 0.0):.1f}",
            top.theme_name or "未分类",
            window._display_action(top.action),
            tuple(lines),
        )
        if getattr(card, "_strategy_signature", None) != signature:
            card.set_strategy_summary(
                strategy_name=strategy_name,
                primary_count=primary_count,
                focus_name=f"{top.stock_name} ({top.stock_id})",
                focus_score=getattr(top, field_name, 0.0),
                focus_theme=top.theme_name or "未分类",
                focus_action=window._display_action(top.action),
                top_rows=lines,
            )
            card._strategy_signature = signature
    window._refresh_strategy_focus_detail()


def refresh_theme_heat_panels(window, strategy_score_fields) -> None:
    if hasattr(window, "theme_heat_table"):
        selected_theme = _selected_table_symbol(
            window.theme_heat_table,
            getattr(window, "theme_heat_rows", []),
            attr_name="theme_name",
        )
        theme_signature = tuple(
            (
                item.theme_name,
                f"{item.strength_score:.1f}",
                f"{item.continuation_score:.1f}",
                f"{getattr(item, 'window_score', 0.0):.1f}",
                f"{getattr(item, 'divergence_score', 0.0):.1f}",
                f"{item.news_score:.1f}",
                str(item.leader_count),
                str(item.theme_rank),
                item.risk_flag,
            )
            for item in window.theme_heat_rows
        )
        previous_theme_signature = tuple(getattr(window, "_theme_heat_table_signature", ()))
        if previous_theme_signature != theme_signature:
            with _batched_table_update(window.theme_heat_table):
                window.theme_heat_table.setRowCount(len(window.theme_heat_rows))
                for row_index, values in enumerate(theme_signature):
                    for column, value in enumerate(values):
                        window.theme_heat_table.setItem(row_index, column, QTableWidgetItem(value))
            window._theme_heat_table_signature = theme_signature
        current_row = window.theme_heat_table.currentRow()
        if window.theme_heat_rows and (
            previous_theme_signature != theme_signature or current_row < 0 or current_row >= len(window.theme_heat_rows)
        ):
            _select_row_by_symbol(
                window.theme_heat_table,
                window.theme_heat_rows,
                selected_theme,
                attr_name="theme_name",
            )
    if hasattr(window, "leader_table"):
        selected_stock_id = _selected_table_symbol(
            window.leader_table,
            getattr(window, "leader_candidates", []),
            attr_name="stock_id",
        )
        leader_signature = tuple(
            (
                item.stock_name,
                item.stock_id,
                item.theme_name,
                window._display_leader_level(item.leader_level),
                _display_mainline_role(getattr(item, "mainline_role", "")),
                f"{getattr(item, 'mainline_window_score', 0.0):.1f}",
                getattr(item, "mainline_risk_flag", "--"),
                f"{item.leader_score:.1f}",
                window._display_action(item.action),
                item.rationale,
            )
            for item in window.leader_candidates
        )
        previous_leader_signature = tuple(getattr(window, "_leader_table_signature", ()))
        if previous_leader_signature != leader_signature:
            with _batched_table_update(window.leader_table):
                window.leader_table.setRowCount(len(window.leader_candidates))
                for row_index, values in enumerate(leader_signature):
                    leader = window.leader_candidates[row_index]
                    tooltip = (
                        f"{leader.stock_name} ({leader.stock_id})\n"
                        f"题材：{leader.theme_name}\n"
                        f"角色：{_display_mainline_role(getattr(leader, 'mainline_role', ''))}\n"
                        f"动作：{window._display_action(leader.action)}\n"
                        f"风险：{getattr(leader, 'mainline_risk_flag', '--')}"
                    )
                    for column, value in enumerate(values):
                        item = QTableWidgetItem(value)
                        item.setToolTip(tooltip)
                        if column == 6:
                            risk_label = str(value)
                            if risk_label == "高":
                                item.setBackground(QColor("#FBEAEA"))
                                item.setForeground(QColor("#842029"))
                            elif risk_label == "中":
                                item.setBackground(QColor("#FFF4DB"))
                                item.setForeground(QColor("#7C4A03"))
                            else:
                                item.setBackground(QColor("#E8F7EC"))
                                item.setForeground(QColor("#0F5132"))
                        elif column == 8:
                            action_bg, action_fg = signal_colors(leader.action, leader.action)
                            item.setBackground(action_bg)
                            item.setForeground(action_fg)
                        window.leader_table.setItem(row_index, column, item)
                    identity_item = _build_identity_table_item(window, leader.symbol, badge=window._display_action(leader.action))
                    identity_item.setToolTip(tooltip)
                    window.leader_table.setItem(row_index, 0, identity_item)
            window._leader_table_signature = leader_signature
        current_row = window.leader_table.currentRow()
        if window.leader_candidates and (
            previous_leader_signature != leader_signature or current_row < 0 or current_row >= len(window.leader_candidates)
        ):
            _select_row_by_symbol(
                window.leader_table,
                window.leader_candidates,
                selected_stock_id,
                attr_name="stock_id",
            )
    refresh_strategy_pack_panels(window, strategy_score_fields)


def populate_filtered_daily_pool_table(window) -> None:
    if not hasattr(window, "daily_pool_table"):
        return
    rows = window._filtered_daily_pool_rows() if hasattr(window, "_filtered_daily_pool_rows") else list(window.daily_pool_rows)
    selected_symbol = _selected_table_symbol(window.daily_pool_table, rows)
    execution_status_by_symbol = {
        getattr(row, "symbol", ""): (
            window._execution_status_for_symbol(row.symbol)
            if hasattr(window, "_execution_status_for_symbol")
            else "PENDING"
        )
        for row in rows
    }
    table_signature = tuple(
        (
            getattr(row, "symbol", ""),
            execution_status_by_symbol.get(getattr(row, "symbol", ""), ""),
            getattr(row, "stock_name", ""),
            getattr(row, "stock_id", ""),
            getattr(row, "mainline_tag", ""),
            getattr(row, "theme_name", ""),
            getattr(row, "mainline_rank", getattr(row, "theme_rank", "")),
            getattr(row, "mainline_role", ""),
            getattr(row, "mainline_window_score", 0.0),
            getattr(row, "mainline_risk_flag", "--"),
            getattr(row, "primary_strategy", ""),
            getattr(row, "mainline_strength_score", getattr(row, "theme_score", 0.0)),
            getattr(row, "leader_level", ""),
            getattr(row, "total_score", 0.0),
            getattr(row, "leader_model_score", 0.0),
            getattr(row, "main_force_score", 0.0),
            getattr(row, "board_attack_score", 0.0),
            getattr(row, "value_recovery_score", 0.0),
            getattr(row, "tail_buy_score", 0.0),
            getattr(row, "one_day_hold_score", 0.0),
            getattr(row, "dragon_decision_score", getattr(row, "total_score", 0.0)),
            getattr(row, "action", ""),
            getattr(row, "catalyst", ""),
            getattr(row, "signal_date", ""),
            getattr(row, "entry_price", None),
            getattr(row, "stop_price", None),
            getattr(row, "target_price", None),
        )
        for row in rows
    )
    if tuple(getattr(window, "_daily_pool_table_signature", ())) == table_signature:
        if rows:
            _select_row_by_symbol(window.daily_pool_table, rows, selected_symbol)
        return
    previous_signature = tuple(getattr(window, "_daily_pool_table_signature", ()))
    with _batched_table_update(window.daily_pool_table):
        window.daily_pool_table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            if row_index < len(previous_signature) and previous_signature[row_index] == table_signature[row_index]:
                continue
            execution_status = (
                window._execution_status_for_symbol(row.symbol)
                if hasattr(window, "_execution_status_for_symbol")
                else "待观察"
            )
            row_tooltip = _daily_pool_row_tooltip(window, row, execution_status)
            price_snapshot = _daily_pool_price_snapshot(row)
            entry_price = float(price_snapshot["entry"] or 0.0)
            target_price = float(price_snapshot["target"] or 0.0)
            entry_text = f"{entry_price:.2f}" if entry_price else "--"
            target_text = f"{target_price:.2f}" if target_price else "--"
            values = {
                0: _compact_daily_pool_status(execution_status),
                2: row.stock_id or window._stock_id_for_symbol(row.symbol),
                3: row.symbol,
                5: str(getattr(row, "mainline_rank", row.theme_rank) or "--"),
                6: _compact_daily_pool_role(getattr(row, "mainline_role", "")),
                7: f"{getattr(row, 'mainline_window_score', 0.0):.1f}",
                8: getattr(row, "mainline_risk_flag", "--"),
                9: _compact_daily_pool_strategy(getattr(row, "primary_strategy", "") or "掘龙决策"),
                10: f"{getattr(row, 'mainline_strength_score', row.theme_score):.1f}",
                11: _shorten_daily_pool_text(window._display_leader_level(row.leader_level), 6),
                12: f"{row.total_score:.1f}",
                13: f"{getattr(row, 'leader_model_score', 0.0):.0f}",
                14: f"{getattr(row, 'main_force_score', 0.0):.0f}",
                15: f"{getattr(row, 'board_attack_score', 0.0):.0f}",
                16: f"{getattr(row, 'value_recovery_score', 0.0):.0f}",
                17: f"{getattr(row, 'tail_buy_score', 0.0):.0f}",
                18: f"{getattr(row, 'one_day_hold_score', 0.0):.0f}",
                20: _compact_daily_pool_action(row.action),
                21: _shorten_daily_pool_text(row.catalyst, 8),
                22: _compact_daily_pool_date(row.signal_date),
                23: f"买 {entry_text} / 卖 {target_text}",
            }
            for column, value in values.items():
                table_item = _ensure_table_item(window.daily_pool_table, row_index, column, value)
                if hasattr(table_item, "setToolTip") and table_item.toolTip() != row_tooltip:
                    table_item.setToolTip(row_tooltip)
                if column == 0:
                    if execution_status == "已提交":
                        background, foreground = submission_colors({"order_status": "SUBMITTED", "fill_status": ""})
                        table_item.setBackground(background)
                        table_item.setForeground(foreground)
                    elif execution_status == "已送审":
                        background, foreground = submission_colors({"order_status": "", "fill_status": "PENDING"})
                        table_item.setBackground(background)
                        table_item.setForeground(foreground)
                    elif execution_status == "提交失败":
                        background, foreground = submission_colors({"order_status": "FAILED", "fill_status": "REJECTED"})
                        table_item.setBackground(background)
                        table_item.setForeground(foreground)
                elif column == 8:
                    risk_label = str(value)
                    if risk_label == "高":
                        table_item.setBackground(QColor("#FBEAEA"))
                        table_item.setForeground(QColor("#842029"))
                    elif risk_label == "中":
                        table_item.setBackground(QColor("#FFF4DB"))
                        table_item.setForeground(QColor("#7C4A03"))
                    else:
                        table_item.setBackground(QColor("#E8F7EC"))
                        table_item.setForeground(QColor("#0F5132"))
                elif column == 12:
                    try:
                        score = float(value)
                    except ValueError:
                        score = 0.0
                    if score >= 85:
                        table_item.setBackground(QColor("#E8F7EC"))
                        table_item.setForeground(QColor("#0F5132"))
                    elif score >= 70:
                        table_item.setBackground(QColor("#FFF4DB"))
                        table_item.setForeground(QColor("#7C4A03"))
                elif column == 19:
                    action_bg, action_fg = signal_colors(row.action, row.action)
                    table_item.setBackground(action_bg)
                    table_item.setForeground(action_fg)
                elif column == 23:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            identity_item = _build_daily_pool_identity_item(window, row, execution_status)
            if identity_item.toolTip() != row_tooltip:
                identity_item.setToolTip(row_tooltip)
            window.daily_pool_table.setItem(row_index, 1, identity_item)

            theme_item = _ensure_table_item(
                window.daily_pool_table,
                row_index,
                4,
                f"{getattr(row, 'mainline_tag', '') or row.theme_name or '未分类'}\n{_compact_daily_pool_role(getattr(row, 'mainline_role', ''))} | 位次 {getattr(row, 'mainline_rank', row.theme_rank) or '--'}",
            )
            theme_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            theme_item.setBackground(QColor("#24303A"))
            theme_item.setForeground(QColor("#FFD166"))
            if theme_item.toolTip() != row_tooltip:
                theme_item.setToolTip(row_tooltip)
            _set_item_data_if_changed(
                theme_item,
                QT_USER_ROLE,
                {
                    "mainline_tag": getattr(row, "mainline_tag", "") or row.theme_name or "未分类",
                    "mainline_role": getattr(row, "mainline_role", ""),
                    "symbol": row.symbol,
                },
            )

            action_item = _ensure_table_item(
                window.daily_pool_table,
                row_index,
                19,
                f"{_compact_daily_pool_action(row.action)}\n{_compact_daily_pool_strategy(getattr(row, 'primary_strategy', '') or '掘龙决策')}",
            )
            action_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            action_item.setBackground(QColor("#1A2430"))
            action_item.setForeground(QColor("#F4F7FB"))
            if action_item.toolTip() != row_tooltip:
                action_item.setToolTip(row_tooltip)

            rr_ratio = float(price_snapshot["rr_ratio"] or 0.0)
            price_item = _ensure_table_item(
                window.daily_pool_table,
                row_index,
                23,
                f"买 {entry_text} / 卖 {target_text}\n盈亏比 {rr_ratio:.2f}" if rr_ratio else f"买 {entry_text} / 卖 {target_text}",
            )
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            price_item.setBackground(QColor("#183126" if rr_ratio >= 1.8 else ("#3A2F16" if rr_ratio >= 1.0 else "#2A1F1F")))
            price_item.setForeground(QColor("#8FE3B0" if rr_ratio >= 1.8 else ("#FFD166" if rr_ratio >= 1.0 else "#FFB4AE")))
            if price_item.toolTip() != row_tooltip:
                price_item.setToolTip(row_tooltip)
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            _set_item_data_if_changed(
                price_item,
                QT_USER_ROLE,
                {
                    "symbol": row.symbol,
                    "entry_price": entry_price,
                    "target_price": target_price,
                    "rr_ratio": rr_ratio,
                    "upside_pct": price_snapshot["upside_pct"],
                },
            )
            risk_item = _ensure_table_item(window.daily_pool_table, row_index, 8, f"{getattr(row, 'mainline_risk_flag', '--')}\n总分 {row.total_score:.1f}")
            risk_item.setTextAlignment(Qt.AlignCenter)
            risk_item.setBackground(QColor("#2A1F1F" if getattr(row, "mainline_risk_flag", "--") == "高" else ("#3A2F16" if getattr(row, "mainline_risk_flag", "--") == "中" else "#183126")))
            risk_item.setForeground(QColor("#FFB4AE" if getattr(row, "mainline_risk_flag", "--") == "高" else ("#FFD166" if getattr(row, "mainline_risk_flag", "--") == "中" else "#8FE3B0")))
            if risk_item.toolTip() != row_tooltip:
                risk_item.setToolTip(row_tooltip)
    window._daily_pool_table_signature = table_signature
    if hasattr(window, "_configure_terminal_tables"):
        window._configure_terminal_tables()
    if rows:
        _select_row_by_symbol(window.daily_pool_table, rows, selected_symbol)


def _build_identity_table_item(window, symbol: str, *, badge: str = "--") -> QTableWidgetItem:
    stock_name = window._stock_name_for_symbol(symbol) if symbol else "--"
    stock_id = window._stock_id_for_symbol(symbol) if symbol else "--"
    text = f"{stock_name} | {stock_id} | {symbol or '--'}"
    item = QTableWidgetItem(text)
    item.setToolTip(f"{stock_name}\n代码：{stock_id}\n交易标识：{symbol or '--'}\n状态：{badge}")
    item.setData(QT_USER_ROLE, {"symbol": symbol, "stock_name": stock_name, "stock_id": stock_id, "badge": badge})
    return item


def _build_market_identity_item(row, *, background, foreground) -> QTableWidgetItem:
    stock_name = getattr(row, "stock_name", "") or "--"
    stock_id = getattr(row, "stock_id", "") or "--"
    symbol = getattr(row, "symbol", "") or "--"
    heat_score = float(getattr(row, "heat_score", 0.0) or 0.0)
    decision_score = float(getattr(row, "decision_score", 0.0) or 0.0)
    action = str(getattr(row, "action", "") or "").upper()
    action_label_map = {
        "BUY": "建仓",
        "HOLD": "持有",
        "WATCH": "观察",
        "REDUCE": "减仓",
        "SELL": "离场",
    }
    action_label = action_label_map.get(action, "跟踪")
    stock_line = f"{stock_name}  {stock_id}"
    detail_line = f"{action_label} · 热 {heat_score:.1f} · 评 {decision_score:.1f}"
    item = QTableWidgetItem(f"{stock_line}\n{detail_line}")
    item.setBackground(QColor("#111A24"))
    item.setForeground(QColor("#F3F7FC"))
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    item.setToolTip(
        "\n".join(
            [
                f"{stock_name} ({stock_id})",
                f"交易标识：{symbol}",
                f"当前动作：{action_label}",
                f"热度：{heat_score:.1f}",
                f"涨幅：{float(getattr(row, 'pct_change', 0.0) or 0.0):.2f}%",
                f"决策分：{decision_score:.1f}",
            ]
        )
    )
    item.setData(
        QT_USER_ROLE,
        {
            "symbol": symbol,
            "stock_name": stock_name,
            "stock_id": stock_id,
            "stock_line": stock_line,
            "detail_line": detail_line,
            "action_label": action_label,
            "heat_score": heat_score,
            "decision_score": decision_score,
        },
    )
    return item


def _build_daily_pool_identity_item(window, row, execution_status: str) -> QTableWidgetItem:
    stock_name = row.stock_name or window._stock_name_for_symbol(row.symbol)
    stock_id = row.stock_id or window._stock_id_for_symbol(row.symbol)
    symbol = row.symbol or "--"
    heat_score = float(getattr(row, "mainline_strength_score", getattr(row, "theme_score", row.total_score)) or 0.0)
    badge = execution_status if execution_status != "待观察" else window._display_action(row.action)
    action_text = window._display_action(getattr(row, "action", "") or "WATCH")
    decision_score = float(getattr(row, "dragon_decision_score", getattr(row, "total_score", 0.0)) or 0.0)
    item = QTableWidgetItem(f"{stock_name}  {stock_id}\n{badge} | {action_text} | 评 {decision_score:.1f}")
    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    item.setToolTip(
        "\n".join(
            [
                f"股票：{stock_name}",
                f"代码：{stock_id}",
                f"交易标识：{symbol}",
                f"执行状态：{badge}",
                f"主线热度：{heat_score:.1f}",
            ]
        )
    )
    item.setData(
        QT_USER_ROLE,
        {
            "symbol": symbol,
            "stock_name": stock_name,
            "stock_id": stock_id,
            "execution_status": execution_status,
            "badge": badge,
            "heat_score": heat_score,
        },
    )
    return item


def _build_status_badge_item(primary: str, secondary: str) -> QTableWidgetItem:
    item = QTableWidgetItem(f"{primary or '--'} / {secondary or '--'}")
    item.setTextAlignment(Qt.AlignCenter)
    item.setBackground(QColor("#24303A"))
    item.setForeground(QColor("#7ED7FF"))
    item.setToolTip(f"动作：{primary or '--'}\n成交：{secondary or '--'}")
    return item


def _decision_tone(decision_score: float) -> tuple[str, QColor, QColor]:
    if decision_score >= 85:
        return "高优", QColor("#173323"), QColor("#71F0A7")
    if decision_score >= 72:
        return "跟踪", QColor("#3A3018"), QColor("#FFD36B")
    return "谨慎", QColor("#321C1F"), QColor("#FF9E9E")


def _fund_model_tone(row) -> tuple[str, QColor, QColor]:
    main_inflow = float(getattr(row, "main_inflow", 0.0) or 0.0)
    turnover = float(getattr(row, "turnover", 0.0) or 0.0)
    fund_model = str(getattr(row, "fund_model", "") or "待同步")
    if main_inflow >= 1.5e8:
        return fund_model, QColor("#133225"), QColor("#66E3A4")
    if turnover >= 10:
        return fund_model, QColor("#3A3018"), QColor("#FFD36B")
    return fund_model, QColor("#18222C"), QColor("#A7B9CA")


def _strategy_tone(row, theme_name: str, signal_text: str) -> tuple[str, str, QColor, QColor]:
    strategy_name = str(getattr(row, "strategy_tag", "") or "待同步")
    action = str(getattr(row, "action", "") or "").upper()
    if action == "BUY":
        return strategy_name, f"{theme_name} · {signal_text}", QColor("#2B181B"), QColor("#FF9D9D")
    if action in {"HOLD", "WATCH"}:
        return strategy_name, f"{theme_name} · {signal_text}", QColor("#1A2330"), QColor("#7ED7FF")
    return strategy_name, f"{theme_name} · {signal_text}", QColor("#2A2417"), QColor("#E5C47A")


def apply_market_filters(window) -> None:
    if not hasattr(window, "market_pool_table"):
        return
    previous_rows = list(getattr(window, "filtered_market_rows", []))
    previous_selected_symbol = _selected_table_symbol(window.market_pool_table, previous_rows)
    query = window.market_search_input.text().strip().lower() if hasattr(window, "market_search_input") else ""
    source_rows = list(getattr(window.market_screen_result, "algorithmic_pool", []))
    filtered_rows = []
    for row in source_rows:
        theme_name = getattr(row, "theme_name", "") or "未分类"
        if window.market_filter_tag != "全部" and row.strategy_tag != window.market_filter_tag:
            continue
        if window.market_theme_filter != "全部" and theme_name != window.market_theme_filter:
            continue
        haystacks = (
            row.stock_name.lower(),
            row.stock_id.lower(),
            row.symbol.lower(),
            theme_name.lower(),
            row.strategy_tag.lower(),
            getattr(row, "rationale", "").lower(),
        )
        if query and not any(query in item for item in haystacks):
            continue
        filtered_rows.append(row)
    market_signature = (
        window.market_filter_tag,
        window.market_theme_filter,
        query,
        tuple(
            (
                getattr(row, "symbol", ""),
                getattr(row, "stock_name", ""),
                getattr(row, "stock_id", ""),
                getattr(row, "theme_name", ""),
                getattr(row, "strategy_tag", ""),
                getattr(row, "action", ""),
                getattr(row, "signal_label", ""),
                getattr(row, "fund_model", ""),
                getattr(row, "main_inflow", 0.0),
                getattr(row, "pct_change", 0.0),
                getattr(row, "latest_price", 0.0),
                getattr(row, "decision_score", 0.0),
            )
            for row in filtered_rows
        ),
    )
    if tuple(getattr(window, "_market_pool_table_signature", ())) == market_signature:
        window.filtered_market_rows = list(filtered_rows)
        window._populate_market_depth_texts(filtered_rows)
        window._refresh_overview_side_panels(filtered_rows)
        if filtered_rows:
            _select_row_by_symbol(window.market_pool_table, filtered_rows, previous_selected_symbol)
        return
    previous_signature = tuple(getattr(window, "_market_pool_table_signature", ()))
    with _batched_table_update(window.market_pool_table):
        window.market_pool_table.setRowCount(len(filtered_rows))
        for row_index, row in enumerate(filtered_rows):
            if row_index < len(previous_signature) and previous_signature[row_index] == market_signature[3][row_index]:
                continue
            theme_name = getattr(row, "theme_name", "") or "未分类"
            background, foreground = market_pool_colors(row)
            rank_background = QColor("#141D28")
            rank_foreground = QColor("#8EA4BB")
            pct_background = background
            pct_foreground = foreground
            decision_score = float(getattr(row, "decision_score", 0.0) or 0.0)
            decision_label, price_background, price_foreground = _decision_tone(decision_score)

            rank_item = _ensure_table_item(window.market_pool_table, row_index, 0, str(row_index + 1))
            rank_item.setData(QT_USER_ROLE, row.symbol)
            rank_item.setBackground(rank_background)
            rank_item.setForeground(rank_foreground)
            rank_item.setTextAlignment(Qt.AlignCenter)
            identity_item = _build_market_identity_item(row, background=background, foreground=foreground)
            window.market_pool_table.setItem(row_index, 1, identity_item)

            fund_model_label, fund_background, fund_foreground = _fund_model_tone(row)
            fund_tooltip = f"资金模型：{row.fund_model}\n主力净流入：{row.main_inflow / 1e8:.2f} 亿"
            fund_item = _ensure_table_item(window.market_pool_table, row_index, 2, f"{fund_model_label}\n流入 {row.main_inflow / 1e8:.2f} 亿")
            fund_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            fund_item.setBackground(fund_background)
            fund_item.setForeground(fund_foreground)
            if fund_item.toolTip() != fund_tooltip:
                fund_item.setToolTip(fund_tooltip)

            signal_text = window._display_label(row.signal_label)
            strategy_name, strategy_detail, strategy_background, strategy_foreground = _strategy_tone(row, theme_name, signal_text)
            strategy_tooltip = (
                f"策略：{row.strategy_tag}\n"
                f"题材：{theme_name}\n"
                f"信号：{signal_text}"
            )
            strategy_item = _ensure_table_item(
                window.market_pool_table,
                row_index,
                3,
                f"{strategy_name}\n{strategy_detail}",
            )
            strategy_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            strategy_item.setBackground(strategy_background)
            strategy_item.setForeground(strategy_foreground)
            if strategy_item.toolTip() != strategy_tooltip:
                strategy_item.setToolTip(strategy_tooltip)

            pct_item = _ensure_table_item(window.market_pool_table, row_index, 4, f"{row.pct_change:.2f}%")
            pct_item.setBackground(pct_background)
            pct_item.setForeground(pct_foreground)
            pct_item.setTextAlignment(Qt.AlignCenter)
            price_item = _ensure_table_item(
                window.market_pool_table,
                row_index,
                5,
                f"{row.latest_price:.2f}\n{decision_label} {decision_score:.1f}",
            )
            price_tooltip = f"决策分 {decision_score:.1f} | 分级 {decision_label} | 题材 {theme_name}"
            if price_item.toolTip() != price_tooltip:
                price_item.setToolTip(price_tooltip)
            price_item.setBackground(price_background)
            price_item.setForeground(price_foreground)
            price_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

    window._market_pool_table_signature = market_signature
    window.filtered_market_rows = list(filtered_rows)
    window._populate_market_depth_texts(filtered_rows)
    window._refresh_overview_side_panels(filtered_rows)
    if filtered_rows:
        _select_row_by_symbol(window.market_pool_table, filtered_rows, previous_selected_symbol)


def fill_scan_rows(window) -> None:
    selected_symbol = _selected_table_symbol(getattr(window, "scan_table", None), getattr(window, "scan_rows", []))
    scan_signature = tuple(
        (
            getattr(row, "symbol", ""),
            getattr(row, "action", ""),
            getattr(row, "label", ""),
            getattr(row, "score", 0),
            getattr(row, "signal_date", ""),
            float(getattr(row, "close", 0.0) or 0.0),
            float(getattr(row, "entry_price", 0.0) or 0.0),
            float(getattr(row, "stop_price", 0.0) or 0.0),
            float(getattr(row, "target_price", 0.0) or 0.0),
        )
        for row in getattr(window, "scan_rows", [])
    )
    if getattr(window, "_scan_table_signature", None) == scan_signature:
        if window.scan_rows:
            _select_row_by_symbol(window.scan_table, window.scan_rows, selected_symbol)
        return

    previous_signature = tuple(getattr(window, "_scan_table_signature", ()))
    with _batched_table_update(window.scan_table):
        window.scan_table.setRowCount(len(window.scan_rows))
        for row_index, row in enumerate(window.scan_rows):
            if row_index < len(previous_signature) and previous_signature[row_index] == scan_signature[row_index]:
                continue
            tooltip = (
                f"{window._stock_name_for_symbol(row.symbol)} ({window._stock_id_for_symbol(row.symbol)})\n"
                f"交易标识：{row.symbol}\n动作：{window._display_action(row.action)}\n"
                f"信号：{window._display_label(row.label)}\n评分：{row.score}\n原因：{row.reason or '待补充'}"
            )
            identity_item = _ensure_table_item(
                window.scan_table,
                row_index,
                0,
                f"{window._stock_name_for_symbol(row.symbol)} | {window._stock_id_for_symbol(row.symbol)} | {window._display_action(row.action)}",
            )
            identity_item.setData(
                QT_USER_ROLE,
                {
                    "symbol": row.symbol,
                    "stock_name": window._stock_name_for_symbol(row.symbol),
                    "stock_id": window._stock_id_for_symbol(row.symbol),
                    "badge": window._display_action(row.action),
                },
            )
            if identity_item.toolTip() != tooltip:
                identity_item.setToolTip(tooltip)
            action_item = _ensure_table_item(
                window.scan_table,
                row_index,
                3,
                f"{window._display_action(row.action)} / {window._display_label(row.label)}",
            )
            action_item.setTextAlignment(Qt.AlignCenter)
            action_item.setBackground(QColor("#1B2633"))
            action_item.setForeground(QColor("#8FC7FF"))
            if action_item.toolTip() != tooltip:
                action_item.setToolTip(tooltip)
            values = {
                1: window._stock_id_for_symbol(row.symbol),
                2: row.symbol,
                4: window._display_label(row.label),
                5: str(row.score),
                6: row.signal_date,
                7: f"{row.close:.2f}",
                8: "" if row.entry_price is None else f"{row.entry_price:.2f}",
                9: "" if row.stop_price is None else f"{row.stop_price:.2f}",
                10: "" if row.target_price is None else f"{row.target_price:.2f}",
            }
            for column, value in values.items():
                item = _ensure_table_item(window.scan_table, row_index, column, value)
                if item.toolTip() != tooltip:
                    item.setToolTip(tooltip)
    window._scan_table_signature = scan_signature
    if window.scan_rows:
        _select_row_by_symbol(window.scan_table, window.scan_rows, selected_symbol)


def fill_backtest_summaries(window) -> None:
    selected_symbol = _selected_table_symbol(getattr(window, "summary_table", None), getattr(window, "backtest_summaries", []))
    summary_signature = tuple(
        (
            getattr(item, "symbol", ""),
            int(getattr(item, "trades", 0) or 0),
            float(getattr(item, "total_return", 0.0) or 0.0),
            float(getattr(item, "max_drawdown", 0.0) or 0.0),
            float(getattr(item, "win_rate", 0.0) or 0.0),
            float(getattr(item, "ending_equity", 0.0) or 0.0),
        )
        for item in getattr(window, "backtest_summaries", [])
    )
    if getattr(window, "_summary_table_signature", None) == summary_signature:
        if window.backtest_summaries:
            _select_row_by_symbol(window.summary_table, window.backtest_summaries, selected_symbol)
        return

    previous_signature = tuple(getattr(window, "_summary_table_signature", ()))
    with _batched_table_update(window.summary_table):
        window.summary_table.setRowCount(len(window.backtest_summaries))
        for row_index, item in enumerate(window.backtest_summaries):
            if row_index < len(previous_signature) and previous_signature[row_index] == summary_signature[row_index]:
                continue
            tooltip = (
                f"{window._stock_name_for_symbol(item.symbol)} ({window._stock_id_for_symbol(item.symbol)})\n"
                f"交易标识：{item.symbol}\n交易笔数：{item.trades}\n收益率：{item.total_return:.2%}\n胜率：{item.win_rate:.2%}"
            )
            identity_item = _ensure_table_item(
                window.summary_table,
                row_index,
                0,
                f"{window._stock_name_for_symbol(item.symbol)} | {window._stock_id_for_symbol(item.symbol)} | {item.total_return:.2%}",
            )
            identity_item.setData(
                QT_USER_ROLE,
                {
                    "symbol": item.symbol,
                    "stock_name": window._stock_name_for_symbol(item.symbol),
                    "stock_id": window._stock_id_for_symbol(item.symbol),
                    "badge": f"{item.total_return:.2%}",
                },
            )
            if identity_item.toolTip() != tooltip:
                identity_item.setToolTip(tooltip)
            values = {
                1: window._stock_id_for_symbol(item.symbol),
                2: item.symbol,
                3: str(item.trades),
                4: f"{item.total_return:.2%}",
                5: f"{item.max_drawdown:.2%}",
                6: f"{item.win_rate:.2%}",
                7: f"{item.ending_equity:,.0f}",
            }
            for column, value in values.items():
                table_item = _ensure_table_item(window.summary_table, row_index, column, value)
                if table_item.toolTip() != tooltip:
                    table_item.setToolTip(tooltip)
    window._summary_table_signature = summary_signature
    if window.backtest_summaries:
        _select_row_by_symbol(window.summary_table, window.backtest_summaries, selected_symbol)


def refresh_watchlist(window) -> None:
    current_watchlist = list(getattr(window.state, "watchlist", []) or [])
    watchlist_signature = tuple(current_watchlist)
    selected_items = window.watchlist_widget.selectedItems()
    selected_symbol = selected_items[0].text() if selected_items else ""
    if getattr(window, "_watchlist_signature", None) != watchlist_signature:
        window.watchlist_widget.clear()
        window.watchlist_widget.addItems(current_watchlist)
        window._watchlist_signature = watchlist_signature
    if selected_symbol and selected_symbol in current_watchlist:
        matches = window.watchlist_widget.findItems(selected_symbol, Qt.MatchExactly)
        if matches:
            window.watchlist_widget.setCurrentItem(matches[0])
    if hasattr(window, "monitor_table"):
        window._refresh_intraday_monitor()


def refresh_intraday_monitor(window) -> None:
    updated = datetime.now().strftime("%H:%M:%S")
    rows_to_show: list[ScanRow] = []
    previous_selected_symbol = _selected_table_symbol(getattr(window, "monitor_table", None), getattr(window, "intraday_monitor_rows", []))
    recommendation_map = {item.symbol: item for item in window.daily_pool_rows}
    if window.state.watchlist:
        scan_map = {row.symbol: row for row in window.scan_rows}
        for symbol in window.state.watchlist:
            row = scan_map.get(symbol)
            if row is not None:
                rows_to_show.append(row)
                continue
            analyses = window.universe_analyses.get(symbol, [])
            if analyses:
                latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1])
                rows_to_show.append(
                    ScanRow(
                        symbol=symbol,
                        signal_date=latest.date,
                        label=latest.label,
                        action="HOLD" if latest.label == "NONE" else latest.label,
                        score=latest.score,
                        close=latest.close,
                        entry_price=latest.entry_price,
                        stop_price=latest.stop_price,
                        target_price=latest.target_price,
                        reason=latest.reason,
                        source_path=str(window.paths_by_symbol.get(symbol, "")),
                    )
                )
    else:
        rows_to_show = window.scan_rows[:10]

    should_beep = False
    table_signature: list[tuple[str, ...]] = []
    for row_index, row in enumerate(rows_to_show):
        values = [
            window._stock_name_for_symbol(row.symbol),
            window._stock_id_for_symbol(row.symbol),
            row.symbol,
            window._display_action(row.action),
            window._display_label(row.label),
            str(row.score),
            f"{row.close:.2f}",
            row.signal_date,
        ]
        background, foreground = signal_colors(row.action, row.label)
        table_signature.append(tuple(values + [row.action, row.label]))

        recommendation = recommendation_map.get(row.symbol)
        if recommendation and recommendation.theme_rank > window.state.strategy_top_theme_limit:
            alert_state = f"THEME_DROP::{recommendation.theme_rank}"
        else:
            alert_state = row.label if row.label in {"RECLAIM_LONG", "TRAP_DETECTED"} else ""
        previous_state = window.monitor_alert_state.get(row.symbol, "")
        if alert_state and alert_state != previous_state:
            should_beep = True
        window.monitor_alert_state[row.symbol] = alert_state

    active_symbols = {row.symbol for row in rows_to_show}
    window.monitor_alert_state = {
        symbol: state for symbol, state in window.monitor_alert_state.items() if symbol in active_symbols
    }
    previous_signature = tuple(getattr(window, "_monitor_table_signature", ()))
    current_signature = tuple(table_signature)
    if previous_signature != current_signature:
        with _batched_table_update(window.monitor_table):
            window.monitor_table.setRowCount(len(rows_to_show))
            for row_index, row in enumerate(rows_to_show):
                if row_index < len(previous_signature) and previous_signature[row_index] == current_signature[row_index]:
                    continue
                values = list(current_signature[row_index][:-2]) + [updated]
                background, foreground = signal_colors(row.action, row.label)
                tooltip = (
                    f"{window._stock_name_for_symbol(row.symbol)} ({window._stock_id_for_symbol(row.symbol)})\n"
                    f"交易标识：{row.symbol}\n动作：{window._display_action(row.action)}\n"
                    f"信号：{window._display_label(row.label)}\n评分：{row.score}"
                )
                for column, value in enumerate(values):
                    item = window.monitor_table.item(row_index, column)
                    if item is None:
                        item = QTableWidgetItem(value)
                        window.monitor_table.setItem(row_index, column, item)
                    elif item.text() != value:
                        item.setText(value)
                    item.setBackground(background)
                    item.setForeground(foreground)
                    if item.toolTip() != tooltip:
                        item.setToolTip(tooltip)
                identity_item = _build_identity_table_item(window, row.symbol, badge=window._display_label(row.label))
                identity_item.setBackground(background)
                identity_item.setForeground(foreground)
                identity_item.setToolTip(tooltip)
                window.monitor_table.setItem(row_index, 0, identity_item)
                action_item = _build_compact_badge_item(
                    [window._display_action(row.action), window._display_label(row.label)],
                    tooltip=f"{window._stock_name_for_symbol(row.symbol)} ({window._stock_id_for_symbol(row.symbol)})",
                    background="#223040",
                    foreground="#FFD166",
                )
                action_item.setBackground(background)
                action_item.setForeground(foreground)
                window.monitor_table.setItem(row_index, 3, action_item)
        window._monitor_table_signature = current_signature
    window.intraday_monitor_rows = list(rows_to_show)
    if rows_to_show:
        selected_row = window.monitor_table.currentRow()
        if previous_signature != current_signature or selected_row < 0 or selected_row >= len(rows_to_show):
            selected_row = _select_row_by_symbol(window.monitor_table, rows_to_show, previous_selected_symbol)
        if hasattr(window, "_refresh_monitor_summary"):
            focus_symbol = rows_to_show[selected_row].symbol if selected_row >= 0 else rows_to_show[0].symbol
            window._refresh_monitor_summary(focus_symbol)
    elif hasattr(window, "_refresh_monitor_summary"):
        window._refresh_monitor_summary("")
    if hasattr(window, "monitor_summary_text"):
        summary_limit = int(window._license_capabilities()["monitor_summary_limit"])
        theme_drop_rows = [
            recommendation_map[row.symbol]
            for row in rows_to_show
            if row.symbol in recommendation_map
            and recommendation_map[row.symbol].theme_rank > window.state.strategy_top_theme_limit
        ]
        notes: list[str] = []
        if window.state.focus_themes:
            focused_rows = [
                recommendation_map[row.symbol]
                for row in rows_to_show
                if row.symbol in recommendation_map and recommendation_map[row.symbol].theme_name in window.state.focus_themes
            ]
            notes.extend(
                [
                    "盘中监控快照",
                    f"- 关注题材：{', '.join(window.state.focus_themes)}",
                    f"- 命中关注题材标的：{len(focused_rows)}",
                    f"- 当前监控标的：{len(rows_to_show)}",
                ]
            )
        if theme_drop_rows:
            if notes:
                notes.append("")
            notes.extend(["盘中题材掉队提醒", ""])
            for item in theme_drop_rows[:summary_limit]:
                notes.append(
                    f"- {item.stock_name} | 题材 {item.theme_name} 跌至第 {item.theme_rank} 位，优先考虑减仓或观察。"
                )
        if not notes:
            notes = [
                "盘中监控快照",
                f"- 当前监控标的：{len(rows_to_show)}",
                "- 暂无新增主线掉队提醒，继续观察分时承接与量能变化。",
            ]
        _set_plain_text_if_changed(window.monitor_summary_text, "\n".join(notes))
    if should_beep and window.sound_alert_checkbox.isChecked():
        QApplication.beep()


def refresh_trade_recap(window) -> None:
    if not hasattr(window, "broker_recap_text"):
        return
    focus_symbol = ""
    selected_intent = window._selected_order_intent() if hasattr(window, "_selected_order_intent") else None
    if selected_intent is not None:
        focus_symbol = str(getattr(selected_intent, "symbol", "") or "")
    if not focus_symbol and hasattr(window, "_explicit_recommendation_focus"):
        focus_recommend = window._explicit_recommendation_focus()
        focus_symbol = str(getattr(focus_recommend, "symbol", "") or "") if focus_recommend is not None else ""
    if not focus_symbol:
        focus_symbol = str(getattr(window, "active_symbol", "") or "")
    summary = summarize_trade_recap(
        submission_records=window.order_submission_records,
        holdings=window.holdings,
        order_intents=window.order_intents,
        order_log=window.order_submission_log,
    )
    conclusion = (
        f"提交 {summary['submitted_count']} | 失败 {summary['failed_count']} | 待成 {summary['pending_count']}"
        if summary["submitted_count"] or summary["pending_count"] or summary["failed_count"]
        else "等待提交后生成回顾"
    )
    risk = summary["review_flags"][0] if summary["review_flags"] else "当前没有新增执行偏差"
    next_step = (
        summary["latest_messages"][0]
        if summary["latest_messages"]
        else (f"跟踪 {', '.join(summary['focus_symbols'][:3])}" if summary["focus_symbols"] else "继续跟踪成交与主线是否延续")
    )
    if focus_symbol:
        matching_record = next(
            (
                item
                for item in reversed(list(getattr(window, "order_submission_records", []) or []))
                if str(item.get("symbol", "") or "") == focus_symbol
            ),
            None,
        )
        focus_name = window._stock_name_for_symbol(focus_symbol) if hasattr(window, "_stock_name_for_symbol") else focus_symbol
        if matching_record is not None:
            record_message = str(matching_record.get("message", "") or "").strip()
            record_failure = str(matching_record.get("failure_reason", "") or "").strip()
            next_step = record_message or record_failure or f"优先复核 {focus_name} 的成交回执与执行偏差"
            risk = record_failure or risk
    if hasattr(window, "order_intents") and hasattr(window, "daily_pool_rows"):
        recommendation_map = {getattr(item, "symbol", ""): item for item in getattr(window, "daily_pool_rows", [])}
        gated = []
        for item in getattr(window, "order_intents", []):
            recommendation = recommendation_map.get(getattr(item, "symbol", ""))
            if recommendation is not None:
                gated.append(f"{getattr(recommendation, 'stock_name', item.symbol)} {_report_mainline_followup_text(recommendation)}")
        if gated:
            if focus_symbol:
                focused_gate = next(
                    (
                        f"{getattr(recommendation_map.get(focus_symbol), 'stock_name', focus_symbol)} {_report_mainline_followup_text(recommendation_map.get(focus_symbol))}"
                        for _ in [0]
                        if recommendation_map.get(focus_symbol) is not None
                    ),
                    "",
                )
                next_step = focused_gate or gated[0]
            else:
                next_step = gated[0]
    _set_plain_text_if_changed(window.broker_recap_text, _brief_panel_text("成交回顾", conclusion, risk, next_step))
    if hasattr(window, "broker_recap_metric_labels"):
        focused_recommendation = recommendation_map.get(focus_symbol) if "recommendation_map" in locals() else None
        verdict_value = "待复盘" if not summary["submitted_count"] and not summary["pending_count"] else ("建议复核" if summary["failed_count"] else "继续跟踪")
        verdict_accent = conclusion
        mainline_value = (
            _report_mainline_followup_text(focused_recommendation)
            if focused_recommendation is not None
            else "待联动"
        )
        mainline_accent = (
            f"{getattr(focused_recommendation, 'stock_name', focus_symbol)}"
            if focused_recommendation is not None
            else "等待主线、回执和成交联动"
        )
        quality_value = "有偏差" if summary["failed_count"] else ("待回写" if not summary["submitted_count"] else "已回写")
        quality_accent = risk
        action_value = "先看回执" if summary["submitted_count"] else "继续观察"
        action_accent = next_step
        _set_label_text_if_changed(window.broker_recap_metric_labels["verdict"], verdict_value)
        _set_label_text_if_changed(window.broker_recap_metric_accents["verdict"], verdict_accent)
        _set_label_text_if_changed(window.broker_recap_metric_labels["mainline"], mainline_value)
        _set_label_text_if_changed(window.broker_recap_metric_accents["mainline"], mainline_accent)
        _set_label_text_if_changed(window.broker_recap_metric_labels["quality"], quality_value)
        _set_label_text_if_changed(window.broker_recap_metric_accents["quality"], quality_accent)
        _set_label_text_if_changed(window.broker_recap_metric_labels["action"], action_value)
        _set_label_text_if_changed(window.broker_recap_metric_accents["action"], action_accent)


def refresh_broker_execution_panel(window, summary: dict[str, object]) -> None:
    blockers = list(summary.get("blockers", []))
    warnings = list(summary.get("warnings", []))
    symbols = list(summary.get("symbols", []))
    risk_profile = str(summary.get("risk_profile", "standard") or "standard")
    risk_profile_label = RISK_PROFILE_LABELS.get(risk_profile, risk_profile)
    risk_profile_hint = risk_profile_brief(risk_profile)
    mainline_review = dict(summary.get("mainline_review", {}) or {})
    review_status = str(mainline_review.get("status", "--"))
    review_pass_count = int(mainline_review.get("pass_count", 0) or 0)
    review_missing_count = int(mainline_review.get("missing_count", 0) or 0)
    readiness = str(summary.get("readiness", "--"))
    readiness_score = int(summary.get("readiness_score", 0))
    estimated_capital = float(summary.get("estimated_capital", 0.0))
    estimated_loss = float(summary.get("estimated_loss", 0.0))
    estimated_profit = float(summary.get("estimated_profit", 0.0))
    available_cash = float(summary.get("available_cash", 0.0))
    capital_usage_ratio = float(summary.get("capital_usage_ratio", 0.0))
    asset_usage_ratio = float(summary.get("asset_usage_ratio", 0.0))
    portfolio_review = dict(summary.get("portfolio_risk_review", {}) or {})
    portfolio_rows = list(portfolio_review.get("rows", []))
    portfolio_status = str(portfolio_review.get("status", "待评估") or "待评估")
    total_loss_ratio = float(portfolio_review.get("total_loss_ratio", 0.0) or 0.0)
    top_portfolio_row = max(
        portfolio_rows,
        key=lambda item: (
            float(item.get("loss_ratio", 0.0) or 0.0),
            float(item.get("asset_usage_ratio", 0.0) or 0.0),
            float(item.get("cash_usage_ratio", 0.0) or 0.0),
        ),
        default={},
    )
    top_portfolio_symbol = str(top_portfolio_row.get("symbol", "") or "")
    top_portfolio_asset_ratio = float(top_portfolio_row.get("asset_usage_ratio", 0.0) or 0.0)
    top_portfolio_cash_ratio = float(top_portfolio_row.get("cash_usage_ratio", 0.0) or 0.0)
    side_counts = summary.get("side_counts", {})
    buy_count = int(side_counts.get("BUY", 0) or 0)
    sell_reduce_count = int(side_counts.get("SELL", 0) or 0) + int(side_counts.get("REDUCE", 0) or 0)
    risk_lamp = "红灯" if blockers else ("黄灯" if warnings else "绿灯")
    risk_note = blockers[0] if blockers else (warnings[0] if warnings else "当前无硬阻塞")
    submission_count = len(getattr(window, "order_submission_records", []) or [])

    if hasattr(window, "broker_summary_metric_labels"):
        has_execution_focus = bool(symbols) or submission_count > 0
        stage_value = headline = ("先处理阻塞" if blockers else ("建议复核" if warnings else readiness))
        stage_accent = f"准备 {readiness_score}% | 组合 {portfolio_status}"
        if not has_execution_focus:
            stage_value = "待委托"
            stage_accent = "先从推荐页或交易计划生成第一批委托"
        gate_value = review_status
        if blockers:
            gate_accent = blockers[0]
        elif warnings:
            gate_accent = warnings[0]
        else:
            gate_accent = f"通过 {review_pass_count} | 待核对 {review_missing_count}"
        if not has_execution_focus:
            gate_value = "待审查"
            gate_accent = "等待主线审查与风险灯联动"
        queue_value = f"{len(symbols)} 笔" if has_execution_focus else "0 笔"
        queue_accent = f"买 {buy_count} / 卖减 {sell_reduce_count}" if has_execution_focus else "等待生成委托"
        receipt_value = risk_lamp if has_execution_focus else "无回执"
        receipt_accent = f"待审 {len(symbols)} / 回执 {submission_count}" if has_execution_focus else "提交后这里会回写成交状态"
        _set_label_text_if_changed(window.broker_summary_metric_labels["stage"], stage_value)
        _set_label_text_if_changed(window.broker_summary_metric_accents["stage"], stage_accent)
        _set_label_text_if_changed(window.broker_summary_metric_labels["gate"], gate_value)
        _set_label_text_if_changed(window.broker_summary_metric_accents["gate"], gate_accent)
        _set_label_text_if_changed(window.broker_summary_metric_labels["queue"], queue_value)
        _set_label_text_if_changed(window.broker_summary_metric_accents["queue"], queue_accent)
        _set_label_text_if_changed(window.broker_summary_metric_labels["receipt"], receipt_value)
        _set_label_text_if_changed(window.broker_summary_metric_accents["receipt"], receipt_accent)

    if hasattr(window, "broker_metric_labels"):
        risk_reward_ratio = float(summary.get("risk_reward_ratio", 0.0))
        has_execution_focus = bool(symbols) or submission_count > 0

        readiness_value = readiness if has_execution_focus else "待委托"
        readiness_accent = f"准备度 {readiness_score}%" if has_execution_focus else "先生成委托，再进入确认流程"
        _set_label_text_if_changed(window.broker_metric_labels["readiness"], readiness_value)
        _set_label_text_if_changed(window.broker_metric_accents["readiness"], readiness_accent)

        capital_value = f"{estimated_capital:,.0f}" if estimated_capital > 0 else "待预算"
        capital_hint = f"占可用资金 {capital_usage_ratio * 100:.1f}%"
        if not has_execution_focus:
            capital_hint = "等待委托生成后估算占用"
        elif available_cash <= 0 and estimated_capital > 0:
            capital_hint = "待同步资金后校验"
        _set_label_text_if_changed(window.broker_metric_labels["capital"], capital_value)
        _set_label_text_if_changed(window.broker_metric_accents["capital"], capital_hint)

        risk_reward_value = f"{risk_reward_ratio:.2f}" if risk_reward_ratio > 0 else "待计划"
        risk_reward_hint = f"{risk_profile_label}档 | 综合止盈 / 综合止损" if has_execution_focus else "先生成计划后计算盈亏比"
        _set_label_text_if_changed(window.broker_metric_labels["risk_reward"], risk_reward_value)
        _set_label_text_if_changed(window.broker_metric_accents["risk_reward"], risk_reward_hint)

        risk_budget_value = f"{estimated_loss:,.0f}" if estimated_loss > 0 else "待风控"
        portfolio_hint = f"组合{portfolio_status} | 止损 {total_loss_ratio * 100:.1f}%"
        if not has_execution_focus:
            portfolio_hint = "等待委托链路后评估组合止损"
        elif top_portfolio_symbol:
            symbol_tail = top_portfolio_symbol.split(".")[-1]
            portfolio_hint += f" | {symbol_tail} 占资 {top_portfolio_asset_ratio * 100:.1f}%"
            if top_portfolio_cash_ratio > 0:
                portfolio_hint += f" / 资金 {top_portfolio_cash_ratio * 100:.1f}%"
        _set_label_text_if_changed(window.broker_metric_labels["risk_budget"], risk_budget_value)
        _set_label_text_if_changed(window.broker_metric_accents["risk_budget"], portfolio_hint)

    if hasattr(window, "broker_gate_summary_text"):
        headline = "可进入确认"
        if blockers:
            headline = "先处理阻塞再提交"
        elif warnings:
            headline = "可继续，建议复核"
        next_step = blockers[0] if blockers else (warnings[0] if warnings else (f"优先核对 {symbols[0]}" if symbols else "继续确认委托"))
        if available_cash <= 0 and estimated_capital > 0:
            next_step = "先同步资金，再确认委托占用"
        risk = f"{risk_lamp} | {risk_profile_label}档 | 组合 {portfolio_status} | {risk_note}"
        conclusion = f"{headline} | 准备 {readiness_score}% | 闸门 {review_status} | 组合 {portfolio_status}"
        _set_plain_text_if_changed(window.broker_gate_summary_text, _brief_panel_text("闸门提要", conclusion, risk, next_step))

    if hasattr(window, "broker_execution_summary_metric_labels"):
        first_review_row = next(iter(list(mainline_review.get("rows", []) or [])), {})
        blocker_value = risk_lamp
        blocker_accent = risk_note
        mainline_value = f"占资 {asset_usage_ratio * 100:.1f}%" if has_execution_focus else "待预算"
        mainline_accent = (
            f"可用 {available_cash:,.0f} | 计划 {estimated_capital:,.0f}"
            if has_execution_focus
            else "等待委托生成后估算资金闸门"
        )
        lead_name = str(first_review_row.get("name", first_review_row.get("symbol", "")) or "")
        action_value = lead_name or (symbols[0] if symbols else "待首票")
        action_accent = (
            f"{first_review_row.get('theme', '--')} | {first_review_row.get('status', '--')}"
            if first_review_row
            else f"{review_status} | 通过 {review_pass_count} | 待核对 {review_missing_count}"
        )
        portfolio_value = "先同步资金" if available_cash <= 0 and estimated_capital > 0 else headline
        portfolio_accent = next_step if next_step else f"止损 {total_loss_ratio * 100:.1f}% | 占资 {asset_usage_ratio * 100:.1f}%"
        _set_label_text_if_changed(window.broker_execution_summary_metric_labels["blocker"], blocker_value)
        _set_label_text_if_changed(window.broker_execution_summary_metric_accents["blocker"], blocker_accent)
        _set_label_text_if_changed(window.broker_execution_summary_metric_labels["mainline"], mainline_value)
        _set_label_text_if_changed(window.broker_execution_summary_metric_accents["mainline"], mainline_accent)
        _set_label_text_if_changed(window.broker_execution_summary_metric_labels["action"], action_value)
        _set_label_text_if_changed(window.broker_execution_summary_metric_accents["action"], action_accent)
        _set_label_text_if_changed(window.broker_execution_summary_metric_labels["portfolio"], portfolio_value)
        _set_label_text_if_changed(window.broker_execution_summary_metric_accents["portfolio"], portfolio_accent)
    if hasattr(window, "broker_focus_blocker_button"):
        _set_enabled_if_changed(window.broker_focus_blocker_button, bool(blockers))
        _set_tooltip_if_changed(window.broker_focus_blocker_button, blockers[0] if blockers else "当前没有阻塞委托")
    if hasattr(window, "broker_focus_priority_button"):
        has_priority_target = bool(symbols) and not blockers
        _set_enabled_if_changed(window.broker_focus_priority_button, has_priority_target)
        if blockers:
            _set_tooltip_if_changed(window.broker_focus_priority_button, "请先处理阻塞委托，再查看高优先级票")
        elif symbols:
            _set_tooltip_if_changed(window.broker_focus_priority_button, f"定位当前高优先级委托候选：{symbols[0]}")
        else:
            _set_tooltip_if_changed(window.broker_focus_priority_button, "当前没有可定位的委托")

    if hasattr(window, "broker_mainline_review_text"):
        review = dict(summary.get("mainline_review", {}) or {})
        review_rows = list(review.get("rows", []))
        review_blockers = list(review.get("blockers", []))
        review_warnings = list(review.get("warnings", []))
        first_row = review_rows[0] if review_rows else {}
        conclusion = f"{review.get('status', '--')} | 通过 {int(review.get('pass_count', 0))} | 待核对 {int(review.get('missing_count', 0))}"
        risk = (
            review_blockers[0]
            if review_blockers
            else (review_warnings[0] if review_warnings else f"{first_row.get('theme', '--')} | {first_row.get('status', '--')}" if first_row else "当前主线审查通过")
        )
        next_step = (
            f"优先处理 {first_row.get('name', first_row.get('symbol', '--'))}"
            if first_row
            else ("继续确认主线前排" if not review_blockers else "先处理拦截项")
        )
        review_lines = [
            "主线审查",
            f"结论：{conclusion}",
            f"风险：{risk}",
            f"下一步：{next_step}",
        ]
        if first_row:
            review_lines.append(f"首票：{first_row.get('name', first_row.get('symbol', '--'))} | {first_row.get('theme', '--')}")
        _set_plain_text_if_changed(window.broker_mainline_review_text, "\n".join(review_lines))

    if hasattr(window, "broker_execution_text"):
        conclusion = f"{readiness} | 委托 {len(symbols)} 笔 | 主线闸门 {review_status} | 组合 {portfolio_status}"
        risk = f"{risk_lamp} | {risk_profile_label}档 | 止损 {estimated_loss:,.0f} | 组合止损 {total_loss_ratio * 100:.1f}% | 资产占比 {asset_usage_ratio * 100:.1f}%"
        next_step = blockers[0] if blockers else (warnings[0] if warnings else (f"继续确认 {symbols[0]}" if symbols else "等待新的委托建议"))
        execution_lines = [
            "执行中控",
            f"结论：{conclusion}",
            f"风险：{risk}",
            f"下一步：{next_step}",
            f"档位：{risk_profile_hint}",
        ]
        _set_plain_text_if_changed(window.broker_execution_text, "\n".join(execution_lines))

def refresh_broker_status(window, *, adapter_cls, extra: str = "") -> None:
    adapter = adapter_cls()
    profile = window.current_broker_profile()
    summary, env = build_broker_execution_summary(
        profile=profile,
        adapter=adapter,
        order_intents=window.order_intents,
        holdings=window.holdings,
        cash_snapshot=window.cash_snapshot,
        recommendations=getattr(window, "daily_pool_rows", []),
        risk_profile=getattr(window.state, "strategy_risk_profile", "standard"),
    )
    window.last_broker_execution_summary = summary
    risk_profile = str(summary.get("risk_profile", "standard") or "standard")
    risk_profile_label = RISK_PROFILE_LABELS.get(risk_profile, risk_profile)
    risk_profile_hint = risk_profile_brief(risk_profile)
    market_value = sum(item.market_value for item in window.holdings)
    available = window.cash_snapshot.available_cash if window.cash_snapshot else 0.0
    total_assets = window.cash_snapshot.total_assets if window.cash_snapshot else market_value + available
    connected = (env["direct_ready"] or env["bridge_ready"]) and profile.mode == "sdk"
    note_lines = [
        "环境诊断",
        f"- 主程序 Python：{env['python_version']}",
        f"- 当前解释器 SDK：{'已安装' if env['module_installed'] else '未安装'} ({env['sdk_module']})",
    ]
    if env["bridge_python"]:
        note_lines.append(f"- 桥接解释器：{env['bridge_python']} | SDK {'已安装' if env['bridge_module_installed'] else '未安装'}")
    if env["bridge_ready"]:
        note_lines.append("- 当前环境已满足桥接下单条件，可通过 Python 3.12 + GM SDK 调用。")
    elif env["direct_ready"]:
        note_lines.append("- 当前环境已满足直接 SDK 调用条件。")
    else:
        note_lines.append("- 当前环境暂未满足 SDK 下单条件，建议继续使用导出 CSV 或 GM 脚本。")
    content = [
        "网关：东方财富 / 掘金 GM",
        f"模式：{window._display_mode(profile.mode)}",
        f"风险档位：{risk_profile_label}",
        f"档位说明：{risk_profile_hint}",
        f"连接状态：{'已就绪' if connected else '未就绪'}",
        "",
        "\n".join(note_lines),
        "",
        "账户概览",
        f"- 持仓证券数：{len(window.holdings)}",
        f"- 持仓市值：{market_value:,.2f}",
        f"- 可用资金：{available:,.2f}",
        f"- 总资产：{total_assets:,.2f}",
        "",
        f"委托建议数：{len(window.order_intents)}",
    ]
    if extra:
        content.extend(["", extra])
    _set_plain_text_if_changed(window.broker_status_text, "\n".join(content))
    refresh_broker_execution_panel(window, summary)
    if hasattr(window, "_refresh_broker_order_focus"):
        window._refresh_broker_order_focus()
    refresh_trade_recap(window)
    window._refresh_shell_header()


def fill_holdings_table(window) -> None:
    table_signature = tuple(
        (
            item.symbol,
            str(item.quantity),
            str(item.available),
            f"{item.cost_price:.2f}",
            f"{item.market_value:,.2f}",
        )
        for item in window.holdings
    )
    if tuple(getattr(window, "_holdings_table_signature", ())) != table_signature:
        with _batched_table_update(window.holdings_table):
            window.holdings_table.setRowCount(len(window.holdings))
            for row_index, values in enumerate(table_signature):
                for column, value in enumerate(values):
                    window.holdings_table.setItem(row_index, column, QTableWidgetItem(value))
        window._holdings_table_signature = table_signature
    window._refresh_broker_status()


def fill_order_intents_table(window) -> None:
    selected_symbol = ""
    if hasattr(window, "orders_table"):
        current_row = window.orders_table.currentRow()
        if current_row >= 0 and current_row < len(getattr(window, "order_intents", []) or []):
            selected_symbol = getattr(window.order_intents[current_row], "symbol", "") or ""
    available_cash = window.cash_snapshot.available_cash if window.cash_snapshot else 0.0
    risk_profile = getattr(getattr(window, "state", None), "strategy_risk_profile", "standard")
    recommendation_map = {getattr(item, "symbol", ""): item for item in getattr(window, "daily_pool_rows", [])}
    broker_summary = getattr(window, "last_broker_execution_summary", None) or {}
    signature_rows = []
    for item in window.order_intents:
        details = describe_order_intent(item, available_cash=available_cash, risk_profile=risk_profile)
        recommendation = recommendation_map.get(item.symbol)
        mainline_gate = _mainline_gate_text(recommendation)
        risk_lamp = _order_risk_lamp_text(window, item, recommendation=recommendation, details=details, summary=broker_summary)
        available_qty = _order_available_quantity(window, item.symbol)
        signature_rows.append(
            (
                getattr(item, "symbol", ""),
                getattr(item, "side", ""),
                getattr(item, "price", 0.0),
                getattr(item, "quantity", 0),
                getattr(item, "stop_price", 0.0),
                getattr(item, "target_price", 0.0),
                getattr(item, "signal_date", ""),
                getattr(item, "reason", ""),
                details["priority"],
                details["estimated_capital"],
                details["risk_reward_ratio"],
                details["reason_summary"],
                tuple(details["checks"]),
                mainline_gate,
                risk_lamp,
                available_qty,
            )
        )
    orders_signature = tuple(signature_rows)
    if tuple(getattr(window, "_orders_table_signature", ())) == orders_signature:
        if hasattr(window, "orders_table") and getattr(window, "order_intents", None):
            target_row = next(
                (
                    index
                    for index, order in enumerate(window.order_intents)
                    if getattr(order, "symbol", "") == selected_symbol
                ),
                0,
            )
            window.orders_table.selectRow(target_row)
        window._refresh_broker_status()
        return
    with _batched_table_update(window.orders_table):
        window.orders_table.setRowCount(len(window.order_intents))

        for row_index, item in enumerate(window.order_intents):
            details = describe_order_intent(item, available_cash=available_cash, risk_profile=risk_profile)
            recommendation = recommendation_map.get(item.symbol)
            mainline_gate = _mainline_gate_text(recommendation)
            risk_lamp = _order_risk_lamp_text(window, item, recommendation=recommendation, details=details, summary=broker_summary)
            available_qty = _order_available_quantity(window, item.symbol)

            values = [
                details["priority"],
                item.symbol,
                window._display_action(item.side),
                f"{item.price:.2f}",
                str(item.quantity),
                f"{details['estimated_capital']:,.0f}",
                f"{details['risk_reward_ratio']:.2f}",
                f"{item.stop_price:.2f}",
                f"{item.target_price:.2f}",
                mainline_gate,
                item.signal_date,
                details["reason_summary"],
                risk_lamp,
            ]
            action_bg, action_fg = signal_colors(item.side, item.side)
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if hasattr(table_item, "setToolTip"):
                    tooltip_parts = [
                        f"代码：{item.symbol}",
                        f"主线闸门：{mainline_gate}",
                        f"风险灯：{risk_lamp}",
                        f"完整逻辑：{item.reason}",
                    ]
                    if getattr(item, "side", "").upper() in {"SELL", "REDUCE"}:
                        if available_qty is None:
                            tooltip_parts.append("持仓检查：缺少可卖持仓")
                        else:
                            tooltip_parts.append(f"持仓检查：可卖 {available_qty} 股")
                    if details["checks"]:
                        tooltip_parts.append("检查项：" + " / ".join(details["checks"]))
                    table_item.setToolTip("\n".join(tooltip_parts))
                if column == 0:
                    priority = str(details["priority"])
                    if priority == "A":
                        table_item.setBackground(QColor("#E8F7EC"))
                        table_item.setForeground(QColor("#0F5132"))
                    elif priority == "B":
                        table_item.setBackground(QColor("#FFF4DB"))
                        table_item.setForeground(QColor("#7C4A03"))
                    else:
                        table_item.setBackground(QColor("#FBEAEA"))
                        table_item.setForeground(QColor("#842029"))
                elif column == 2:
                    table_item.setBackground(action_bg)
                    table_item.setForeground(action_fg)
                elif column == 9:
                    if risk_lamp.startswith("红灯"):
                        table_item.setBackground(QColor("#FBEAEA"))
                        table_item.setForeground(QColor("#842029"))
                    elif risk_lamp.startswith("黄灯"):
                        table_item.setBackground(QColor("#FFF4DB"))
                        table_item.setForeground(QColor("#7C4A03"))
                    else:
                        table_item.setBackground(QColor("#E8F7EC"))
                        table_item.setForeground(QColor("#0F5132"))
                elif column == len(values) - 1:
                    if risk_lamp.startswith("红灯"):
                        table_item.setBackground(QColor("#FBEAEA"))
                        table_item.setForeground(QColor("#842029"))
                    elif risk_lamp.startswith("黄灯"):
                        table_item.setBackground(QColor("#FFF4DB"))
                        table_item.setForeground(QColor("#7C4A03"))
                    else:
                        table_item.setBackground(QColor("#E8F7EC"))
                        table_item.setForeground(QColor("#0F5132"))
                window.orders_table.setItem(row_index, column, table_item)

            stock_name = window._stock_name_for_symbol(item.symbol)
            stock_id = window._stock_id_for_symbol(item.symbol)
            identity_item = _build_identity_table_item(window, item.symbol, badge=details["priority"])
            identity_item.setToolTip(
                "\n".join(
                    [
                        f"{stock_name} ({stock_id})",
                        f"交易标识：{item.symbol}",
                        f"优先级：{details['priority']}",
                        f"预计资金：{details['estimated_capital']:,.0f}",
                        f"盈亏比：{details['risk_reward_ratio']:.2f}",
                    ]
                )
            )
            identity_item.setData(
                QT_USER_ROLE,
                {
                    "symbol": item.symbol,
                    "stock_name": stock_name,
                    "stock_id": stock_id,
                    "badge": details["priority"],
                    "risk_reward_ratio": float(details["risk_reward_ratio"] or 0.0),
                    "estimated_capital": float(details["estimated_capital"] or 0.0),
                },
            )
            if str(details["priority"]) == "A":
                identity_item.setBackground(QColor("#E8F7EC"))
                identity_item.setForeground(QColor("#0F5132"))
            elif str(details["priority"]) == "B":
                identity_item.setBackground(QColor("#FFF4DB"))
                identity_item.setForeground(QColor("#7C4A03"))
            else:
                identity_item.setBackground(QColor("#FBEAEA"))
                identity_item.setForeground(QColor("#842029"))
            window.orders_table.setItem(row_index, 1, identity_item)
            action_item = _build_compact_badge_item(
                [window._display_action(item.side), str(details["priority"])],
                tooltip=(
                    f"动作：{window._display_action(item.side)}\n"
                    f"优先级：{details['priority']}\n"
                    f"主线闸门：{mainline_gate}\n"
                    f"风险灯：{risk_lamp}"
                ),
                background="#1A2430",
                foreground="#F4F7FB",
            )
            window.orders_table.setItem(row_index, 2, action_item)

    if hasattr(window, "_configure_terminal_tables"):
        window._configure_terminal_tables()
    if hasattr(window, "orders_table") and getattr(window, "order_intents", None):
        target_row = next(
            (
                index
                for index, order in enumerate(window.order_intents)
                if getattr(order, "symbol", "") == selected_symbol
            ),
            0,
        )
        window.orders_table.selectRow(target_row)
    window._refresh_broker_status()

def refresh_submission_table(window) -> None:
    current_row = window.execution_table.currentRow() if hasattr(window, "execution_table") else -1
    execution_signature = tuple(
        (
            item.get("timestamp", ""),
            item.get("order_status", ""),
            item.get("fill_status", ""),
            item.get("symbol", ""),
            item.get("side", ""),
            item.get("price", ""),
            item.get("quantity", ""),
            item.get("failure_reason", ""),
            item.get("message", ""),
        )
        for item in window.order_submission_records
    )
    if tuple(getattr(window, "_execution_table_signature", ())) == execution_signature:
        if current_row >= 0 and current_row < len(window.order_submission_records):
            window.execution_table.selectRow(current_row)
        return
    with _batched_table_update(window.execution_table):
        window.execution_table.setRowCount(len(window.order_submission_records))
        for row_index, item in enumerate(window.order_submission_records):
            order_status = display_order_status(item.get("order_status", ""))
            fill_status = display_fill_status(item.get("fill_status", ""))
            symbol = str(item.get("symbol", "") or "")
            stock_name = window._stock_name_for_symbol(symbol) if symbol else "--"
            stock_id = window._stock_id_for_symbol(symbol) if symbol else "--"
            action_text = window._display_action(item.get("side", ""))
            snapshot = submission_table_snapshot_v2(
                item,
                stock_name=stock_name,
                stock_id=stock_id,
                action_text=action_text,
                order_status_text=order_status,
                fill_status_text=fill_status,
            )
            values = [
                snapshot["timeline"],
                order_status,
                fill_status,
                snapshot["focus"],
                snapshot["action"],
                item.get("price", ""),
                item.get("quantity", ""),
                snapshot["risk_badge"],
                snapshot["message"],
            ]
            background, foreground = submission_colors(item)
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setBackground(background)
                table_item.setForeground(foreground)
                if column in {0, 3, 4, 8}:
                    table_item.setToolTip(snapshot["tooltip"])
                if column == 0:
                    table_item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                elif column in {5, 6}:
                    table_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                else:
                    table_item.setTextAlignment(Qt.AlignCenter if column in {1, 2, 7} else (Qt.AlignLeft | Qt.AlignVCenter))
                if column == 7:
                    badge_bg, badge_fg = submission_risk_badge_palette_v2(item)
                    table_item.setBackground(badge_bg)
                    table_item.setForeground(badge_fg)
                window.execution_table.setItem(row_index, column, table_item)
    window._execution_table_signature = execution_signature
    if hasattr(window, "_configure_terminal_tables"):
        window._configure_terminal_tables()
    if current_row >= 0 and current_row < len(window.order_submission_records):
        window.execution_table.selectRow(current_row)

