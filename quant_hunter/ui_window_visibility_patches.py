from __future__ import annotations

from typing import Any

try:
    from PySide6.QtWidgets import QGroupBox, QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover - enables pure-logic imports without Qt runtime
    class _QtStub:
        def __init__(self, *args, **kwargs) -> None:
            self._text = str(args[0]) if args else ""

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

        def text(self) -> str:
            return self._text

        def setText(self, value: str) -> None:
            self._text = str(value)

        def toPlainText(self) -> str:
            return self._text

        def setPlainText(self, value: str) -> None:
            self._text = str(value)

    class QWidget(_QtStub):  # type: ignore[override]
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

from quant_hunter.models import PaperTradingState
from quant_hunter.paper_trading import summarize_paper_trading_performance
from quant_hunter.ui_config import RECOMMEND_AUX_STAGE_POLICY


def paper_lab_stage_v39(
    state: PaperTradingState,
    analytics: dict[str, object],
) -> tuple[str, str]:
    if not getattr(state, "enabled", False):
        return ("待初始化", "先创建实验账户，再跑第一轮策略样本。")
    ledger_count = len(list(getattr(state, "ledger", []) or []))
    closed_trade_count = int(analytics.get("closed_trade_count", 0) or 0)
    if ledger_count <= 0:
        return ("等待首轮样本", "账户已创建，但还没有成交；先运行一轮 AI 自主实验。")
    if closed_trade_count <= 0:
        return ("样本积累中", "已经开始建仓，但还没有形成完整闭环，先继续滚动验证。")
    if closed_trade_count < 4:
        return ("形成复盘样本", "已经有闭环单，适合开始比较战法表现和失败原因。")
    return ("进入策略复盘", "闭环样本已经足够，可以把这里当成策略实验室持续复盘。")


def apply_workspace_visibility_patches(
    window_cls: type,
    *,
    recommend_execution_summary_fn,
) -> None:
    if getattr(window_cls, "_qh_workspace_visibility_patches_applied_v39", False):
        return

    original_post_build_ui_tweaks_v38 = window_cls._post_build_ui_tweaks
    original_refresh_recommend_decision_summary_v38 = window_cls._refresh_recommend_decision_summary

    def _set_aux_stage_visibility_v38(self, visible: bool) -> None:
        setattr(self, "_qh_recommend_aux_stage_visible_v38", bool(visible))
        container = getattr(self, "recommend_stage_container", None)
        if isinstance(container, QWidget):
            container.setVisible(bool(visible))
        toggle_button = getattr(self, "recommend_stage_toggle_button", None)
        if isinstance(toggle_button, QPushButton):
            toggle_button.setText(str(RECOMMEND_AUX_STAGE_POLICY["toggle_text"][bool(visible)]))
            toggle_button.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["toggle_tooltip"][bool(visible)]))
        status_label = getattr(self, "recommend_stage_status_label", None)
        if isinstance(status_label, QLabel):
            self._set_label_text_if_changed(status_label, str(RECOMMEND_AUX_STAGE_POLICY["status_text"][bool(visible)]))
            status_label.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["status_tooltip"][bool(visible)]))

    def _toggle_recommend_auxiliary_stage_v38(self) -> None:
        current = bool(getattr(self, "_qh_recommend_aux_stage_visible_v38", False))
        self._set_aux_stage_visibility_v38(not current)

    def _refresh_recommend_decision_summary_v38(self, row: Any = None) -> None:
        original_refresh_recommend_decision_summary_v38(self, row)
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        status_label = getattr(self, "recommend_stage_status_label", None)
        if not isinstance(status_label, QLabel):
            return
        if current is None:
            if not getattr(self, "_qh_recommend_aux_stage_visible_v38", False):
                self._set_label_text_if_changed(status_label, str(RECOMMEND_AUX_STAGE_POLICY["no_focus_collapsed_text"]))
                status_label.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["no_focus_collapsed_tooltip"]))
            return
        if getattr(self, "_qh_recommend_aux_stage_visible_v38", False):
            focus_name = getattr(current, "stock_name", "") or getattr(current, "symbol", "")
            status_label.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["focus_expanded_tooltip_template"]).format(name=focus_name))
            return
        verdict, execution_summary, can_submit, can_open_broker = recommend_execution_summary_fn(self, current)
        if can_submit or can_open_broker or "失败" in execution_summary:
            text = str(RECOMMEND_AUX_STAGE_POLICY["ready_collapsed_text"])
            tooltip = str(RECOMMEND_AUX_STAGE_POLICY["ready_collapsed_tooltip"])
        else:
            focus_name = getattr(current, "stock_name", "") or getattr(current, "symbol", "")
            text = str(RECOMMEND_AUX_STAGE_POLICY["focus_collapsed_text_template"]).format(verdict=verdict)
            tooltip = str(RECOMMEND_AUX_STAGE_POLICY["focus_collapsed_tooltip_template"]).format(name=focus_name)
        self._set_label_text_if_changed(status_label, text)
        status_label.setToolTip(tooltip)

    def _post_build_ui_tweaks_v38(self) -> None:
        original_post_build_ui_tweaks_v38(self)
        self._set_aux_stage_visibility_v38(bool(RECOMMEND_AUX_STAGE_POLICY["default_visible"]))

    window_cls._set_aux_stage_visibility_v38 = _set_aux_stage_visibility_v38
    window_cls.toggle_recommend_auxiliary_stage = _toggle_recommend_auxiliary_stage_v38
    window_cls._refresh_recommend_decision_summary = _refresh_recommend_decision_summary_v38
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v38

    original_install_paper_trading_workspace_v39 = window_cls._install_paper_trading_workspace
    original_refresh_paper_trading_panels_v39 = window_cls._refresh_paper_trading_panels
    original_post_build_ui_tweaks_v39 = window_cls._post_build_ui_tweaks

    def _set_paper_lab_detail_visibility_v39(self, visible: bool) -> None:
        setattr(self, "_qh_paper_lab_detail_visible_v39", bool(visible))
        for attr_name in ["paper_trading_splitter", "paper_analytics_splitter", "paper_trading_text"]:
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QWidget):
                widget.setVisible(bool(visible))
        toggle_button = getattr(self, "paper_lab_toggle_button", None)
        if isinstance(toggle_button, QPushButton):
            toggle_button.setText("收起原始流水" if visible else "展开原始流水")
        status_label = getattr(self, "paper_lab_toggle_status_label", None)
        if isinstance(status_label, QLabel):
            text = (
                "已展开原始流水：可以继续看持仓、交割单、战法拆解和巡航日志。"
                if visible
                else "原始流水已折叠，当前优先只看实验结论、权益曲线和关键指标。"
            )
            self._set_label_text_if_changed(status_label, text)

    def _toggle_paper_lab_detail_v39(self) -> None:
        current = bool(getattr(self, "_qh_paper_lab_detail_visible_v39", False))
        self._set_paper_lab_detail_visibility_v39(not current)

    def _install_paper_trading_workspace_v39(self) -> None:
        original_install_paper_trading_workspace_v39(self)
        box = getattr(self, "paper_trading_box", None)
        if not isinstance(box, QGroupBox) or hasattr(self, "paper_lab_stage_label"):
            return
        box.setTitle("AI 策略实验室")
        paper_layout = box.layout()
        if not isinstance(paper_layout, QVBoxLayout):
            return
        stage_label = QLabel("实验室阶段：待初始化 | 先创建账户，再开始第一轮策略样本。")
        stage_label.setObjectName("focusStateLabel")
        stage_label.setWordWrap(True)
        self.paper_lab_stage_label = stage_label
        paper_layout.insertWidget(1, stage_label)

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        self.paper_lab_toggle_button = QPushButton("展开原始流水")
        self._set_button_role(self.paper_lab_toggle_button, "ghost")
        self.paper_lab_toggle_button.clicked.connect(self.toggle_paper_lab_detail)
        self.paper_lab_toggle_status_label = QLabel("原始流水已折叠，当前优先只看实验结论、权益曲线和关键指标。")
        self.paper_lab_toggle_status_label.setObjectName("inlineHint")
        self.paper_lab_toggle_status_label.setWordWrap(True)
        control_row.addWidget(self.paper_lab_toggle_button)
        control_row.addWidget(self.paper_lab_toggle_status_label, stretch=1)
        paper_layout.insertLayout(4, control_row)

    def _refresh_paper_trading_panels_v39(self) -> None:
        original_refresh_paper_trading_panels_v39(self)
        state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
        analytics = summarize_paper_trading_performance(state)
        stage_label = getattr(self, "paper_lab_stage_label", None)
        if isinstance(stage_label, QLabel):
            stage_title, stage_detail = paper_lab_stage_v39(state, analytics)
            self._set_label_text_if_changed(stage_label, f"实验室阶段：{stage_title} | {stage_detail}")
        run_button = getattr(self, "paper_run_button", None)
        export_button = getattr(self, "paper_export_button", None)
        if isinstance(run_button, QPushButton):
            stage_title, _ = paper_lab_stage_v39(state, analytics)
            run_button.setText("开始第一轮实验" if stage_title in {"待初始化", "等待首轮样本"} else "继续跑一轮实验")
        if isinstance(export_button, QPushButton):
            closed_trade_count = int(analytics.get("closed_trade_count", 0) or 0)
            export_button.setText("导出实验报告" if closed_trade_count > 0 else "导出当前快照")
        status_label = getattr(self, "paper_lab_toggle_status_label", None)
        if isinstance(status_label, QLabel) and not getattr(self, "_qh_paper_lab_detail_visible_v39", False):
            stage_title, _ = paper_lab_stage_v39(state, analytics)
            if stage_title in {"形成复盘样本", "进入策略复盘"}:
                self._set_label_text_if_changed(
                    status_label,
                    "原始流水已折叠；当前已经形成复盘样本，需要时可展开查看持仓、交割和巡航日志。",
                )

    def _post_build_ui_tweaks_v39(self) -> None:
        original_post_build_ui_tweaks_v39(self)
        self._set_paper_lab_detail_visibility_v39(False)

    window_cls._set_paper_lab_detail_visibility_v39 = _set_paper_lab_detail_visibility_v39
    window_cls.toggle_paper_lab_detail = _toggle_paper_lab_detail_v39
    window_cls._install_paper_trading_workspace = _install_paper_trading_workspace_v39
    window_cls._refresh_paper_trading_panels = _refresh_paper_trading_panels_v39
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v39
    window_cls._qh_workspace_visibility_patches_applied_v39 = True
