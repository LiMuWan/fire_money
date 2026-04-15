from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QTextEdit

from quant_hunter.models import PaperTradingState
from quant_hunter.paper_trading import (
    build_strategy_rotation_snapshot,
    describe_strategy_experiment,
    summarize_paper_trading_performance,
)


def strategy_experiment_verdict_v36(
    closed_trade_count: int,
    win_rate: float,
) -> tuple[str, str]:
    if closed_trade_count <= 0:
        return ("先积累样本", "先跑出完整买卖闭环，再判断这套战法值不值得放大。")
    if closed_trade_count >= 4 and win_rate >= 0.55:
        return ("可继续加样本", "闭环胜率暂时领先，主测战法可以继续验证，但先别放大单票仓位。")
    if closed_trade_count >= 4 and win_rate < 0.45:
        return ("建议先降权", "闭环胜率偏低，下一轮先缩候选或降低仓位，再回看失败样本。")
    return ("继续观察", "样本还不够厚，先保持小样本滚动验证，不急着扩大实验。")


def build_paper_experiment_lines_v36(
    state,
    analytics: dict[str, object],
    rotation_rows: list[dict[str, object]],
) -> list[str]:
    snapshot = describe_strategy_experiment(state, analytics, rotation_rows)
    top_rows = list(snapshot.get("top_strategies", []) or [])
    rotation_map = {
        str(item.get("strategy_name", "") or ""): dict(item)
        for item in rotation_rows or []
    }
    recent = dict(snapshot.get("recent_experiment", {}) or {})
    closed_trade_count = int(analytics.get("closed_trade_count", 0) or 0)
    win_rate = float(analytics.get("win_rate", 0.0) or 0.0)
    avg_hold_days = float(analytics.get("avg_hold_days", 0.0) or 0.0)
    hold_samples = int(analytics.get("hold_cycle_sample_count", 0) or 0)
    verdict, verdict_detail = strategy_experiment_verdict_v36(closed_trade_count, win_rate)
    lines = [
        "策略实验洞察",
        "",
        f"实验结论：{verdict} | 闭环 {closed_trade_count} | 胜率 {win_rate:.1%}",
        f"结论解释：{verdict_detail}",
    ]

    if top_rows:
        lead_row = top_rows[0]
        lead_name = str(lead_row.get("strategy_name", "") or "主测战法")
        lead_rotation = rotation_map.get(lead_name, {})
        lead_bias = str(lead_row.get("bias_label", "") or "中性")
        lead_multiplier = float(
            lead_rotation.get("budget_multiplier", lead_row.get("budget_multiplier", 1.0)) or 1.0
        )
        lead_realized = float(lead_row.get("realized_pnl", 0.0) or 0.0)
        lines.append(
            f"主测战法：{lead_name} | 倾向 {lead_bias} x{lead_multiplier:.2f} | 已实现 {lead_realized:,.0f}"
        )
        if len(top_rows) > 1:
            compare_row = top_rows[1]
            compare_name = str(compare_row.get("strategy_name", "") or "暂无")
            compare_rotation = rotation_map.get(compare_name, {})
            lines.append(
                f"对照战法：{compare_name} | 倾向 {str(compare_row.get('bias_label', '') or '中性')} "
                f"x{float(compare_rotation.get('budget_multiplier', compare_row.get('budget_multiplier', 1.0)) or 1.0):.2f}"
            )
    else:
        lines.append("主测战法：暂时还没有形成稳定样本，先让模拟盘多跑几轮。")

    if hold_samples > 0:
        lines.append(f"持有周期：平均 {avg_hold_days:.1f} 天 | 样本 {hold_samples}")
    else:
        lines.append("持有周期：暂时还没有完整样本，先等待第一批闭环单。")

    recent_summary = str(recent.get("summary", "") or state.last_strategy_note or "").strip()
    if recent_summary:
        lines.append(f"最近实验：{recent_summary}")

    next_action = "下一轮建议：先初始化或继续跑一轮，让系统形成第一批闭环数据。"
    if top_rows:
        lead_name = str(top_rows[0].get("strategy_name", "") or "主测战法")
        if verdict == "可继续加样本":
            next_action = f"下一轮建议：继续以 {lead_name} 为主测，优先观察它在同类标的上的复现度。"
        elif verdict == "建议先降权":
            next_action = f"下一轮建议：先降低 {lead_name} 的权重，优先复盘失败样本和止损触发点。"
        else:
            next_action = f"下一轮建议：保留 {lead_name} 做主测，但先继续补足闭环样本再放大仓位。"
    lines.append(next_action)
    return lines


def recommend_review_sequence_v36(
    signal: str,
    action: str,
    can_submit: bool,
    execution_summary: str,
) -> str:
    action_text = str(action or "").upper()
    if can_submit:
        return "1 主线确认 2 价位确认 3 风险确认 4 送审执行"
    if signal == "防切换" or action_text in {"SELL", "REDUCE"}:
        return "1 先处理风险 2 再决定是否保留观察 3 当前不急于送审"
    if action_text == "BUY":
        return "1 先等确认信号 2 再核对买点/止损 3 通过门槛后再送审"
    if "失败" in execution_summary:
        return "1 先回看失败原因 2 修正参数或风险项 3 再重新进入送审"
    return "1 先看主线 2 再看价位与风险 3 条件不足先观察"


def apply_window_tail_patches(
    window_cls: type,
    *,
    mainline_signal_brief_fn,
    recommend_execution_summary_fn,
) -> None:
    if getattr(window_cls, "_qh_tail_patches_applied_v36", False):
        return

    original_emit_action_feedback = window_cls._emit_action_feedback_v11
    original_refresh_shell_header = window_cls._refresh_shell_header
    original_post_build_ui_tweaks = window_cls._post_build_ui_tweaks

    def _install_commercial_statusbar_v35(self) -> None:
        status_bar = self.statusBar()
        if status_bar is None:
            return
        if getattr(self, "_qh_commercial_statusbar_ready_v35", False):
            return
        status_bar.setSizeGripEnabled(False)
        status_bar.setObjectName("commercialStatusBar")
        if hasattr(status_bar, "setContentsMargins"):
            status_bar.setContentsMargins(8, 4, 8, 6)

        self.status_breadcrumb_label = QLabel("当前页面：市场机会工作台")
        self.status_breadcrumb_label.setObjectName("statusBreadcrumb")
        self.status_action_label = QLabel("最近动作：终端已就绪，等待建立市场快照。")
        self.status_action_label.setObjectName("statusAction")
        self.status_health_label = QLabel("健康度：绿灯 | 推荐 0 | 计划 0 | 待审 0")
        self.status_health_label.setObjectName("statusHealth")

        status_bar.addWidget(self.status_breadcrumb_label, 1)
        status_bar.addWidget(self.status_action_label, 2)
        status_bar.addPermanentWidget(self.status_health_label, 0)
        self._qh_commercial_statusbar_ready_v35 = True

    def _statusbar_page_caption_v35(self, current_name: str) -> tuple[str, str]:
        mapping = {
            "市场机会工作台": ("市场机会工作台", "看全局结构、主线持续性与题材催化。"),
            "总览": ("市场机会工作台", "看全局结构、主线持续性与题材催化。"),
            "策略扫描": ("策略扫描", "筛盘中焦点、观察池与联动入口。"),
            "扫描": ("策略扫描", "筛盘中焦点、观察池与联动入口。"),
            "每日推荐": ("每日推荐", "推进候选排序、计划生成与送审动作。"),
            "推荐": ("每日推荐", "推进候选排序、计划生成与送审动作。"),
            "打板专项": ("打板专项", "跟踪候选、回封监控与专项观察。"),
            "打板": ("打板专项", "跟踪候选、回封监控与专项观察。"),
            "参数配置": ("参数配置", "维护策略参数、目录与运行偏好。"),
            "配置": ("参数配置", "维护策略参数、目录与运行偏好。"),
            "统一登录": ("统一登录", "管理账户、渠道与桥接环境。"),
            "登录": ("统一登录", "管理账户、渠道与桥接环境。"),
            "明细复盘": ("明细复盘", "查看单票画像、执行回放和结论沉淀。"),
            "明细": ("明细复盘", "查看单票画像、执行回放和结论沉淀。"),
            "交易执行": ("交易执行", "完成委托生成、确认提交与回执跟踪。"),
            "交易": ("交易执行", "完成委托生成、确认提交与回执跟踪。"),
        }
        return mapping.get(current_name, ("市场机会工作台", "统一管理行情、推荐、执行与复盘。"))

    def _sync_commercial_statusbar_v35(self) -> None:
        self._install_commercial_statusbar_v35()
        current_index = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        current_name = (
            self._workspace_name_for_index(current_index)
            if hasattr(self, "_workspace_name_for_index")
            else "市场机会工作台"
        )
        page_title, page_caption = self._statusbar_page_caption_v35(current_name)

        pool_count = len(getattr(self, "daily_pool_rows", []) or [])
        plan_count = len(list(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or []))
        pending_orders = len(getattr(self, "order_intents", []) or [])
        submitted_orders = len(getattr(self, "order_submission_records", []) or [])
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []) or [])
        warnings = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("warnings", []) or [])
        health = "红灯" if blockers else ("黄灯" if warnings or pending_orders else "绿灯")

        breadcrumb = f"当前页面：{page_title} | {page_caption}"
        if hasattr(self, "status_breadcrumb_label"):
            self._set_label_text_if_changed(self.status_breadcrumb_label, breadcrumb, tooltip=breadcrumb)

        action_text = getattr(self, "_qh_last_action_feedback_v35", "") or "最近动作：终端已就绪，等待建立市场快照。"
        if hasattr(self, "status_action_label"):
            self._set_label_text_if_changed(self.status_action_label, action_text, tooltip=action_text)

        health_text = f"健康度：{health} | 推荐 {pool_count} | 计划 {plan_count} | 待审 {pending_orders} | 已提交 {submitted_orders}"
        if hasattr(self, "status_health_label"):
            self._set_label_text_if_changed(self.status_health_label, health_text, tooltip=health_text)

    def _emit_action_feedback_v35(
        self,
        destination: str,
        detail: str,
        recommend_text: str = "",
        broker_text: str = "",
        scan_text: str = "",
    ) -> None:
        original_emit_action_feedback(
            self,
            destination,
            detail,
            recommend_text=recommend_text,
            broker_text=broker_text,
            scan_text=scan_text,
        )
        action_text = f"最近动作：{destination} | {detail}"
        self._qh_last_action_feedback_v35 = action_text
        status_bar = self.statusBar()
        if status_bar is not None:
            try:
                status_bar.showMessage(action_text, 5000)
            except Exception:
                pass
        if hasattr(self, "shell_pulse_meta"):
            current_meta = self.shell_pulse_meta.text() if hasattr(self.shell_pulse_meta, "text") else ""
            meta_text = f"{current_meta} | 动作 {destination}" if current_meta else f"动作 {destination}"
            self._set_label_text_if_changed(self.shell_pulse_meta, meta_text, tooltip=meta_text)
        if hasattr(self, "_refresh_shell_header"):
            self._refresh_shell_header()
        self._sync_commercial_statusbar_v35()

    def _refresh_shell_header_v35(self) -> None:
        original_refresh_shell_header(self)
        self._sync_commercial_statusbar_v35()

    def _post_build_ui_tweaks_v35(self) -> None:
        original_post_build_ui_tweaks(self)
        self.setStyleSheet(
            self.styleSheet()
            + """
QStatusBar#commercialStatusBar {
    background: rgba(8, 12, 18, 0.94);
    color: #dbe7f4;
    border-top: 1px solid rgba(108, 130, 153, 0.16);
}
QStatusBar#commercialStatusBar QLabel#statusBreadcrumb {
    color: #e8f1fb;
    font-size: 12px;
    font-weight: 800;
    padding: 4px 10px;
}
QStatusBar#commercialStatusBar QLabel#statusAction {
    color: #9fb5cb;
    font-size: 12px;
    padding: 4px 10px;
}
QStatusBar#commercialStatusBar QLabel#statusHealth {
    color: #ffd88a;
    font-size: 12px;
    font-weight: 800;
    padding: 4px 10px;
}
"""
        )
        self._install_commercial_statusbar_v35()
        self._sync_commercial_statusbar_v35()

    window_cls._install_commercial_statusbar_v35 = _install_commercial_statusbar_v35
    window_cls._statusbar_page_caption_v35 = _statusbar_page_caption_v35
    window_cls._sync_commercial_statusbar_v35 = _sync_commercial_statusbar_v35
    window_cls._emit_action_feedback_v11 = _emit_action_feedback_v35
    window_cls._refresh_shell_header = _refresh_shell_header_v35
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v35

    original_refresh_paper_trading_panels = window_cls._refresh_paper_trading_panels
    original_refresh_recommend_decision_summary = window_cls._refresh_recommend_decision_summary
    original_refresh_recommendation_focus_panels = window_cls._refresh_recommendation_focus_panels

    def _refresh_paper_trading_panels_v36(self) -> None:
        original_refresh_paper_trading_panels(self)
        widget = getattr(self, "paper_experiment_text", None)
        if not isinstance(widget, QTextEdit):
            return
        state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
        analytics = summarize_paper_trading_performance(state)
        rotation_rows = build_strategy_rotation_snapshot(state)
        self._set_plain_text_if_changed(widget, "\n".join(build_paper_experiment_lines_v36(state, analytics, rotation_rows)))

    def _refresh_recommend_decision_summary_v36(self, row: Any = None) -> None:
        original_refresh_recommend_decision_summary(self, row)
        text_widget = getattr(self, "recommend_decision_summary_text", None)
        if not isinstance(text_widget, QTextEdit):
            return
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        if current is None:
            return
        signal = mainline_signal_brief_fn(current)
        action = str(getattr(current, "action", "") or "").upper()
        _, execution_summary, can_submit, _ = recommend_execution_summary_fn(self, current)
        gate_text = "送审门槛：已通过，可以进入交易链路。" if can_submit else f"送审门槛：暂未通过，{execution_summary}"
        review_sequence = recommend_review_sequence_v36(signal, action, can_submit, execution_summary)
        lines = [
            line
            for line in text_widget.toPlainText().splitlines()
            if not line.startswith("送审门槛：") and not line.startswith("决策顺序：")
        ]
        insert_at = next((index for index, value in enumerate(lines) if value.startswith("下一步：")), len(lines))
        lines[insert_at:insert_at] = [gate_text, f"决策顺序：{review_sequence}"]
        self._set_plain_text_if_changed(text_widget, "\n".join(lines))

    def _refresh_recommendation_focus_panels_v36(self, row: Any = None) -> None:
        original_refresh_recommendation_focus_panels(self, row)
        review_widget = getattr(self, "recommend_focus_review_text", None)
        if not isinstance(review_widget, QTextEdit):
            return
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        if current is None:
            return
        signal = mainline_signal_brief_fn(current)
        action = str(getattr(current, "action", "") or "").upper()
        _, execution_summary, can_submit, _ = recommend_execution_summary_fn(self, current)
        gate_text = "门槛：已通过，优先核对买点后推进送审。 " if can_submit else f"门槛：暂未通过，{execution_summary}"
        review_sequence = recommend_review_sequence_v36(signal, action, can_submit, execution_summary)
        lines = [
            line
            for line in review_widget.toPlainText().splitlines()
            if not line.startswith("门槛：") and not line.startswith("决策顺序：")
        ]
        lines.extend([gate_text, f"决策顺序：{review_sequence}"])
        self._set_plain_text_if_changed(review_widget, "\n".join(lines))

    window_cls._refresh_paper_trading_panels = _refresh_paper_trading_panels_v36
    window_cls._refresh_recommend_decision_summary = _refresh_recommend_decision_summary_v36
    window_cls._refresh_recommendation_focus_panels = _refresh_recommendation_focus_panels_v36
    window_cls._qh_tail_patches_applied_v36 = True
