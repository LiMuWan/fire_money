from __future__ import annotations

try:
    from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit, QWidget
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

    class QLabel(QWidget):  # type: ignore[override]
        pass

    class QPushButton(QWidget):  # type: ignore[override]
        pass

    class QTextEdit(QWidget):  # type: ignore[override]
        pass

from quant_hunter.strategy_registry import resolved_primary_strategy

from quant_hunter.models import PaperTradingState
from quant_hunter.ui_config import BROKER_SETUP_POLICY
from quant_hunter.ui_workspace_runtime import refresh_broker_auxiliary_panels_status
from quant_hunter.ui_window_paper_experiment_patches import paper_strategy_experiment_bridge_v45


def broker_workspace_stage_v40(
    order_count: int,
    submit_count: int,
    blocker_count: int,
) -> tuple[str, str]:
    if blocker_count > 0:
        return ("风控阻塞", "存在阻塞项，先排除风险灯和仓位问题，再进入提交。")
    if submit_count > 0:
        return ("执行回执", "已经进入执行跟踪阶段，当前重点是回执、成交和偏差。")
    if order_count > 0:
        return ("待确认提交", "委托已经生成，下一步进确认弹窗核对后提交。")
    return ("待生成委托", "先从机会池或交易计划生成第一批可执行委托。")


def shell_pipeline_story_v41(
    *,
    pool_count: int,
    trade_decisions_count: int,
    pending_orders: int,
    submitted_orders: int,
    paper_enabled: bool,
    paper_closed_trades: int,
) -> str:
    market_stage = "市场已同步" if pool_count > 0 or trade_decisions_count > 0 or pending_orders > 0 or submitted_orders > 0 else "市场待刷新"
    recommend_stage = "推荐已生成" if pool_count > 0 else "推荐待生成"
    if submitted_orders > 0:
        trade_stage = "交易跟踪中"
    elif pending_orders > 0:
        trade_stage = "交易待确认"
    elif trade_decisions_count > 0:
        trade_stage = "交易待生成"
    else:
        trade_stage = "交易未启动"
    if not paper_enabled:
        experiment_stage = "实验待初始化"
    elif paper_closed_trades > 0:
        experiment_stage = "实验可复盘"
    else:
        experiment_stage = "实验跑样本"
    return f"{market_stage} -> {recommend_stage} -> {trade_stage} -> {experiment_stage}"


def broker_experiment_review_lines_v47(
    state: PaperTradingState,
    strategy_name: str,
) -> list[str]:
    bridge = paper_strategy_experiment_bridge_v45(state, strategy_name)
    return [
        f"模拟盘实验：{bridge['title']}",
        f"实验纪律：{bridge['detail']}",
        f"交易约束：{bridge['cta']}",
    ]


def merge_broker_experiment_lines_v47(
    current_text: str,
    experiment_lines: list[str],
) -> str:
    prefixes = ("模拟盘实验：", "实验纪律：", "交易约束：")
    lines = [
        line
        for line in str(current_text or "").splitlines()
        if not any(line.startswith(prefix) for prefix in prefixes)
    ]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines:
        lines.append("")
    lines.extend(experiment_lines)
    return "\n".join(lines)


def apply_broker_workspace_patches(window_cls: type) -> None:
    if getattr(window_cls, "_qh_broker_workspace_patches_applied_v40", False):
        return

    original_refresh_broker_auxiliary_panels_v40 = window_cls._refresh_broker_auxiliary_panels
    original_post_build_ui_tweaks_v40 = window_cls._post_build_ui_tweaks
    original_refresh_submission_focus_v47 = window_cls._refresh_submission_focus

    def _set_broker_execution_detail_visibility_v40(self, visible: bool) -> None:
        setattr(self, "_qh_broker_detail_visible_v40", bool(visible))
        for attr_name in ["broker_result_box", "broker_recap_box"]:
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QWidget):
                widget.setVisible(bool(visible))
        toggle_button = getattr(self, "broker_detail_toggle_button", None)
        if isinstance(toggle_button, QPushButton):
            toggle_button.setText("收起执行明细" if visible else "展开执行明细")
        status_label = getattr(self, "broker_detail_status_label", None)
        if isinstance(status_label, QLabel):
            text = (
                "执行明细已展开：可以继续查看回执、执行日志和偏差复盘。"
                if visible
                else "执行明细已折叠，先看焦点委托、阶段判断和风险闸门。"
            )
            self._set_label_text_if_changed(status_label, text)

    def _toggle_broker_execution_detail_v40(self) -> None:
        current = bool(getattr(self, "_qh_broker_detail_visible_v40", False))
        self._set_broker_execution_detail_visibility_v40(not current)

    def _set_broker_setup_visibility_v41(self, visible: bool) -> None:
        setattr(self, "_qh_broker_setup_visible_v41", bool(visible))
        setup_drawer = getattr(self, "broker_setup_drawer", None)
        control_splitter = getattr(self, "broker_control_splitter", None)
        if isinstance(setup_drawer, QWidget):
            setup_drawer.setVisible(bool(visible))
            setup_drawer.setMinimumHeight(int(BROKER_SETUP_POLICY["drawer_min_height"][bool(visible)]))
        if isinstance(control_splitter, QWidget):
            control_splitter.setVisible(bool(visible))
        toggle_button = getattr(self, "broker_setup_toggle_button", None)
        if isinstance(toggle_button, QPushButton):
            toggle_button.setText(str(BROKER_SETUP_POLICY["toggle_text"][bool(visible)]))
        status_label = getattr(self, "broker_setup_status_label", None)
        if isinstance(status_label, QLabel):
            self._set_label_text_if_changed(status_label, str(BROKER_SETUP_POLICY["status_text"][bool(visible)]))
        for attr_name, role in (
            ("broker_setup_profile_button", "ghost"),
            ("broker_setup_action_button", "ghost"),
            ("broker_setup_runtime_button", "ghost"),
        ):
            button = getattr(self, attr_name, None)
            if isinstance(button, QPushButton) and hasattr(self, "_set_button_role"):
                self._set_button_role(button, role)

    def _toggle_broker_setup_panel_v41(self) -> None:
        current = bool(getattr(self, "_qh_broker_setup_visible_v41", False))
        self._set_broker_setup_visibility_v41(not current)

    def _open_broker_setup_section_v42(self, section_key: str) -> None:
        target = str(section_key or "profile")
        self._set_broker_setup_visibility_v41(True)
        splitter = getattr(self, "broker_control_splitter", None)
        if hasattr(self, "_set_button_role"):
            button_map = {
                "profile": getattr(self, "broker_setup_profile_button", None),
                "action": getattr(self, "broker_setup_action_button", None),
                "runtime": getattr(self, "broker_setup_runtime_button", None),
            }
            for key, button in button_map.items():
                if isinstance(button, QPushButton):
                    self._set_button_role(button, "accent" if key == target else "ghost")
        if hasattr(splitter, "count") and splitter.count() == 3 and hasattr(splitter, "setSizes"):
            size_map = dict(BROKER_SETUP_POLICY["section_sizes"])
            splitter.setSizes(list(size_map.get(target, size_map["profile"])))
        status_label = getattr(self, "broker_setup_status_label", None)
        if isinstance(status_label, QLabel):
            text_map = dict(BROKER_SETUP_POLICY["section_status"])
            self._set_label_text_if_changed(status_label, str(text_map.get(target, text_map["profile"])))

    def _refresh_broker_auxiliary_panels_v40(self) -> None:
        original_refresh_broker_auxiliary_panels_v40(self)
        order_count = len(getattr(self, "order_intents", []) or [])
        submit_count = len(getattr(self, "order_submission_records", []) or [])
        blockers = []
        if hasattr(self, "_current_broker_blockers"):
            try:
                blockers = list(self._current_broker_blockers() or [])
            except Exception:
                blockers = []
        stage_title, stage_detail = broker_workspace_stage_v40(order_count, submit_count, len(blockers))
        refresh_broker_auxiliary_panels_status(
            self,
            stage_title=stage_title,
            stage_detail=stage_detail,
            order_count=order_count,
            submit_count=submit_count,
            blockers=blockers,
            broker_setup_policy=BROKER_SETUP_POLICY,
        )

    def _post_build_ui_tweaks_v40(self) -> None:
        original_post_build_ui_tweaks_v40(self)
        self._set_broker_execution_detail_visibility_v40(False)
        self._set_broker_setup_visibility_v41(bool(BROKER_SETUP_POLICY["default_visible"]))

    def _refresh_submission_focus_v47(self) -> None:
        original_refresh_submission_focus_v47(self)
        record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
        if record is None:
            return

        symbol = str(record.get("symbol", "") or "")
        recommendation = next(
            (item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol),
            None,
        )
        if recommendation is None:
            return

        paper_state = getattr(
            self,
            "paper_trading_state",
            getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()),
        )
        experiment_lines = broker_experiment_review_lines_v47(
            paper_state,
            resolved_primary_strategy(recommendation, default="掘龙决策") or "掘龙决策",
        )
        for attr_name in ("broker_mainline_review_text", "broker_execution_text"):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                merged_text = merge_broker_experiment_lines_v47(widget.toPlainText(), experiment_lines)
                self._set_plain_text_if_changed(widget, merged_text)

    window_cls._set_broker_execution_detail_visibility_v40 = _set_broker_execution_detail_visibility_v40
    window_cls.toggle_broker_execution_detail = _toggle_broker_execution_detail_v40
    window_cls._set_broker_setup_visibility_v41 = _set_broker_setup_visibility_v41
    window_cls.toggle_broker_setup_panel = _toggle_broker_setup_panel_v41
    window_cls.open_broker_setup_section = _open_broker_setup_section_v42
    window_cls._refresh_broker_auxiliary_panels = _refresh_broker_auxiliary_panels_v40
    window_cls._refresh_submission_focus = _refresh_submission_focus_v47
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v40
    window_cls._qh_broker_workspace_patches_applied_v40 = True
