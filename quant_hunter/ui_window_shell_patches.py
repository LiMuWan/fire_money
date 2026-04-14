from __future__ import annotations

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from quant_hunter.models import PaperTradingState
from quant_hunter.paper_trading import summarize_paper_trading_performance
from quant_hunter.ui_config import WORKSPACE_TAB_ORDER


def shell_stage_for_workspace_v42(workspace_key: str) -> str:
    if workspace_key in {"overview", "scanner", "board"}:
        return "market"
    if workspace_key == "recommend":
        return "recommend"
    if workspace_key == "detail":
        return "experiment"
    if workspace_key in {"broker", "auth", "config"}:
        return "trade"
    return ""


def shell_workflow_stage_specs_v42(
    *,
    current_workspace_key: str,
    pool_count: int,
    trade_decisions_count: int,
    pending_orders: int,
    submitted_orders: int,
    paper_enabled: bool,
    paper_closed_trades: int,
    paper_position_count: int,
) -> tuple[list[dict[str, str]], str]:
    market_status = "已同步" if pool_count else "待刷新"
    recommend_status = "已生成" if pool_count else "待生成"
    trade_status = "跟踪中" if submitted_orders else ("待确认" if pending_orders or trade_decisions_count else "未启动")
    experiment_status = "可复盘" if paper_closed_trades else ("跑样本" if paper_enabled else "待初始化")
    experiment_widget = "paper_positions_table" if (paper_enabled and (paper_closed_trades or paper_position_count)) else ("paper_run_button" if paper_enabled else "paper_initialize_button")

    specs: list[dict[str, str]] = [
        {
            "key": "market",
            "title": "市场",
            "status": market_status,
            "workspace": "overview",
            "widget": "market_pool_table",
            "hint": "回到市场总览，先确认主线、资金和题材快照。",
        },
        {
            "key": "recommend",
            "title": "推荐",
            "status": recommend_status,
            "workspace": "recommend",
            "widget": "trade_plan_table" if trade_decisions_count else "daily_pool_table",
            "hint": "进入推荐成交台，压缩候选判断并生成执行计划。",
        },
        {
            "key": "trade",
            "title": "交易",
            "status": trade_status,
            "workspace": "broker",
            "widget": "execution_table" if submitted_orders else "orders_table",
            "hint": "进入交易执行台，复核委托、风控和成交回执。",
        },
        {
            "key": "experiment",
            "title": "实验",
            "status": experiment_status,
            "workspace": "broker",
            "widget": experiment_widget,
            "hint": "进入 AI 策略实验室，跟踪模拟盘样本与复盘结论。",
        },
    ]

    next_stage_key = "market"
    if pool_count:
        next_stage_key = "recommend"
    if trade_decisions_count or pending_orders or submitted_orders:
        next_stage_key = "trade"
    if paper_enabled and (paper_closed_trades or paper_position_count) and not pending_orders:
        next_stage_key = "experiment"

    stage_index = {spec["key"]: index for index, spec in enumerate(specs)}
    current_stage_key = shell_stage_for_workspace_v42(current_workspace_key)
    current_stage_index = stage_index.get(current_stage_key, -1)
    next_stage_index = stage_index.get(next_stage_key, 0)

    for index, spec in enumerate(specs):
        role = "ghost"
        if current_stage_index >= 0:
            if index < current_stage_index:
                role = "tonal"
            if spec["key"] == current_stage_key:
                role = "accent"
        else:
            if index < next_stage_index:
                role = "tonal"
            if spec["key"] == next_stage_key:
                role = "accent"
        spec["role"] = role
        spec["button_text"] = f"{spec['title']} {spec['status']}"
    return specs, next_stage_key


def apply_shell_workflow_patches(window_cls: type) -> None:
    if getattr(window_cls, "_qh_shell_workflow_patches_applied_v42", False):
        return

    original_build_ui_v42 = window_cls._build_ui
    original_refresh_shell_header_v42 = window_cls._refresh_shell_header

    def _current_workspace_key_v42(self) -> str:
        if not hasattr(self, "tabs"):
            return "overview"
        index = self.tabs.currentIndex()
        if 0 <= index < len(WORKSPACE_TAB_ORDER):
            return WORKSPACE_TAB_ORDER[index]
        return "overview"

    def _install_shell_workflow_bar_v42(self) -> None:
        if hasattr(self, "shell_workflow_bar"):
            return
        root = self.centralWidget()
        root_layout = root.layout() if isinstance(root, QWidget) else None
        if not isinstance(root_layout, QVBoxLayout):
            return

        bar = QFrame()
        bar.setObjectName("shellPulseBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(10)

        label = QLabel("流程直达")
        label.setObjectName("shellPulseMeta")
        layout.addWidget(label)

        self.shell_workflow_buttons = {}
        specs, next_stage_key = shell_workflow_stage_specs_v42(
            current_workspace_key="overview",
            pool_count=0,
            trade_decisions_count=0,
            pending_orders=0,
            submitted_orders=0,
            paper_enabled=False,
            paper_closed_trades=0,
            paper_position_count=0,
        )
        for spec in specs:
            button = QPushButton(spec["button_text"])
            button.setMinimumWidth(128)
            button.setToolTip(spec["hint"])
            self._set_button_role(button, spec["role"])
            button.clicked.connect(lambda checked=False, target=spec["key"]: self._open_shell_workflow_stage(target))
            self.shell_workflow_buttons[spec["key"]] = button
            layout.addWidget(button)

        note_label = QLabel(f"建议动作：{next((item['hint'] for item in specs if item['key'] == next_stage_key), '先刷新市场快照。')}")
        note_label.setObjectName("shellPulseMeta")
        note_label.setWordWrap(True)
        self.shell_workflow_note_label = note_label
        layout.addStretch(1)
        layout.addWidget(note_label, stretch=2)

        pulse_index = root_layout.indexOf(self.shell_pulse_bar) if hasattr(self, "shell_pulse_bar") else -1
        root_layout.insertWidget(pulse_index + 1 if pulse_index >= 0 else 1, bar)
        self.shell_workflow_bar = bar

    def _build_ui_v42(self) -> None:
        original_build_ui_v42(self)
        self._install_shell_workflow_bar_v42()

    def _open_shell_workflow_stage_v42(self, stage_key: str) -> None:
        trade_plan = getattr(self, "current_trade_plan", None)
        trade_decisions = list(getattr(trade_plan, "decisions", []) or [])
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()))
        paper_analytics = summarize_paper_trading_performance(paper_state)
        current_workspace_key = self._current_workspace_key_v42() if hasattr(self, "_current_workspace_key_v42") else _current_workspace_key_v42(self)
        specs, _ = shell_workflow_stage_specs_v42(
            current_workspace_key=current_workspace_key,
            pool_count=len(getattr(self, "daily_pool_rows", []) or []),
            trade_decisions_count=len(trade_decisions),
            pending_orders=len(getattr(self, "order_intents", []) or []),
            submitted_orders=len(getattr(self, "order_submission_records", []) or []),
            paper_enabled=bool(getattr(paper_state, "enabled", False)),
            paper_closed_trades=int(paper_analytics.get("closed_trade_count", 0) or 0),
            paper_position_count=len(getattr(paper_state, "positions", []) or []),
        )
        route = next((item for item in specs if item["key"] == stage_key), None)
        if route is None:
            return
        self._navigate_to_workspace(route["workspace"], route["widget"])

    def _refresh_shell_header_v42(self) -> None:
        original_refresh_shell_header_v42(self)
        buttons = getattr(self, "shell_workflow_buttons", {})
        if not isinstance(buttons, dict) or not buttons:
            return

        trade_plan = getattr(self, "current_trade_plan", None)
        trade_decisions = list(getattr(trade_plan, "decisions", []) or [])
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()))
        paper_analytics = summarize_paper_trading_performance(paper_state)
        current_workspace_key = self._current_workspace_key_v42() if hasattr(self, "_current_workspace_key_v42") else _current_workspace_key_v42(self)
        specs, next_stage_key = shell_workflow_stage_specs_v42(
            current_workspace_key=current_workspace_key,
            pool_count=len(getattr(self, "daily_pool_rows", []) or []),
            trade_decisions_count=len(trade_decisions),
            pending_orders=len(getattr(self, "order_intents", []) or []),
            submitted_orders=len(getattr(self, "order_submission_records", []) or []),
            paper_enabled=bool(getattr(paper_state, "enabled", False)),
            paper_closed_trades=int(paper_analytics.get("closed_trade_count", 0) or 0),
            paper_position_count=len(getattr(paper_state, "positions", []) or []),
        )
        for spec in specs:
            button = buttons.get(spec["key"])
            if not isinstance(button, QPushButton):
                continue
            if button.text() != spec["button_text"]:
                button.setText(spec["button_text"])
            if button.toolTip() != spec["hint"]:
                button.setToolTip(spec["hint"])
            self._set_button_role(button, spec["role"])

        note_label = getattr(self, "shell_workflow_note_label", None)
        if isinstance(note_label, QLabel):
            next_hint = next((item["hint"] for item in specs if item["key"] == next_stage_key), "先刷新市场快照。")
            note_text = f"建议动作：{next_hint}"
            if note_label.text() != note_text:
                note_label.setText(note_text)

    window_cls._current_workspace_key_v42 = _current_workspace_key_v42
    window_cls._install_shell_workflow_bar_v42 = _install_shell_workflow_bar_v42
    window_cls._open_shell_workflow_stage = _open_shell_workflow_stage_v42
    window_cls._build_ui = _build_ui_v42
    window_cls._refresh_shell_header = _refresh_shell_header_v42
    window_cls._qh_shell_workflow_patches_applied_v42 = True
