from __future__ import annotations
from PySide6.QtCore import Qt
from PySide6.QtCharts import QChartView
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from quant_hunter.ui_config import (
    DAILY_POOL_TABLE_HEADERS,
    ORDERS_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_EMPTY_HINT,
    RECOMMEND_DEFAULT_EMPTY_META,
    RECOMMEND_DEFAULT_EMPTY_TITLE,
    RECOMMEND_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_STATUS_TEXT,
    RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
    RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
)
from quant_hunter.risk import RISK_PROFILE_LABELS


def _configure_chart_view(view: QChartView, *, min_height: int) -> None:
    view.setMinimumHeight(min_height)
    view.setObjectName("marketChartPanel")
    view.setFrameShape(QFrame.NoFrame)
    view.setRenderHint(QPainter.Antialiasing, True)
    view.setRenderHint(QPainter.TextAntialiasing, True)
    view.setRenderHint(QPainter.SmoothPixmapTransform, True)


def _build_recommend_daily_pool_table(window, build_table):
    table = build_table(DAILY_POOL_TABLE_HEADERS)
    table.verticalHeader().setDefaultSectionSize(74)
    table.setMinimumHeight(420)
    table.setWordWrap(True)
    table.setTextElideMode(Qt.ElideNone)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setObjectName("recommendPoolTable")
    table.itemSelectionChanged.connect(window._on_daily_pool_selection_changed)
    return table


def _configure_recommend_focus_action(window, button: QPushButton, *, role: str, tooltip: str, handler) -> None:
    window._set_button_role(button, role)
    button.setEnabled(False)
    button.setToolTip(tooltip)
    button.clicked.connect(handler)


def build_auth_workspace(window) -> None:
    layout = QVBoxLayout(window.auth_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.auth_tab.setObjectName("authRoot")
    layout.addWidget(
        window._build_workspace_hero(
            "统一登录",
            "券商账户 / SDK 接入",
            "集中管理券商账号、登录通道和 SDK 参数，真实交易仍以人工确认作为最终闸门。",
            [("东方财富", "默认通道"), ("人工确认", "最终闸门")],
        )
    )

    form_box = QGroupBox("账号连接")
    window._style_terminal_panel(form_box)
    form_grid = QGridLayout(form_box)
    profile = window.state.broker_profile

    form_grid.addWidget(QLabel("接入通道"), 0, 0)
    window.auth_channel_combo = QComboBox()
    window.auth_channel_combo.addItem("东方财富", "eastmoney")
    window.auth_channel_combo.addItem("GM", "gm")
    window.auth_channel_combo.addItem("自定义", "custom")
    auth_channel = profile.auth_channel or "eastmoney"
    for index in range(window.auth_channel_combo.count()):
        if window.auth_channel_combo.itemData(index) == auth_channel:
            window.auth_channel_combo.setCurrentIndex(index)
            break
    form_grid.addWidget(window.auth_channel_combo, 0, 1)

    login_fields = [
        ("username", "登录账号", profile.username),
        ("password", "登录密码", profile.password),
        ("token", "SDK Token", profile.token),
        ("account_id", "账户 ID", profile.account_id),
        ("strategy_id", "策略 ID", profile.strategy_id),
    ]
    for index, (key, label, value) in enumerate(login_fields, start=1):
        form_grid.addWidget(QLabel(label), index, 0)
        widget = QLineEdit(value)
        if key == "password":
            widget.setEchoMode(QLineEdit.Password)
        window.login_inputs[key] = widget
        form_grid.addWidget(widget, index, 1)

    save_button = QPushButton("保存登录信息")
    window._set_button_role(save_button, "accent")
    save_button.clicked.connect(window.save_login_profile)
    form_grid.addWidget(save_button, 6, 1)
    layout.addWidget(form_box)

    status_box = QGroupBox("连接状态")
    window._style_terminal_panel(status_box)
    status_layout = QVBoxLayout(status_box)
    window.login_status_text = QTextEdit()
    window.login_status_text.setReadOnly(True)
    window._style_terminal_console(window.login_status_text)
    status_layout.addWidget(window.login_status_text)
    layout.addWidget(status_box, stretch=1)

    window._refresh_login_status()

def build_detail_workspace(window, build_table) -> None:
    layout = QVBoxLayout(window.detail_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.detail_tab.setObjectName("detailRoot")
    layout.addWidget(
        window._build_workspace_hero(
            "明细复盘",
            "单票信号复核与回测明细",
            "从扫描页或首页选中个股后，这里会联动展示信号、指标摘要和交易记录，便于做单票复盘。",
            [("单票", "深度复核"), ("回测", "联动面板")],
        )
    )

    tool_panel = QGroupBox("复盘工具台")
    tool_panel.setObjectName("workspaceToolPanel")
    tool_layout = QGridLayout(tool_panel)
    tool_layout.setContentsMargins(14, 12, 14, 12)
    tool_layout.setHorizontalSpacing(16)
    tool_layout.setVerticalSpacing(10)

    controls = QHBoxLayout()
    controls.setSpacing(8)
    load_button = QPushButton("导入单票 CSV")
    backtest_button = QPushButton("回测当前标的")
    window._set_button_role(load_button)
    window._set_button_role(backtest_button, "accent")
    window.active_symbol_label = QLabel("当前标的：未选择")
    window.active_symbol_label.setObjectName("inlineHint")
    load_button.clicked.connect(window.load_single_csv)
    backtest_button.clicked.connect(window.run_backtest_for_active)
    controls.addWidget(load_button)
    controls.addWidget(backtest_button)
    controls.addWidget(window.active_symbol_label)
    controls.addStretch(1)
    tool_layout.addLayout(controls, 0, 0)

    detail_hint_panel = QFrame()
    detail_hint_panel.setProperty("actionRow", True)
    detail_hint_layout = QVBoxLayout(detail_hint_panel)
    detail_hint_layout.setContentsMargins(12, 10, 12, 10)
    detail_hint_layout.setSpacing(6)
    detail_hint_title = QLabel("复盘提示：单票信号、回测摘要和交易记录会联动到同一焦点标的。")
    detail_hint_title.setObjectName("inlineHint")
    detail_hint_title.setWordWrap(True)
    detail_hint_layout.addWidget(detail_hint_title)
    tool_layout.addWidget(detail_hint_panel, 0, 1)
    tool_layout.setColumnStretch(0, 3)
    tool_layout.setColumnStretch(1, 2)
    layout.addWidget(tool_panel)

    metrics_box = QGroupBox("策略摘要")
    window._style_terminal_panel(metrics_box)
    metrics_layout = QVBoxLayout(metrics_box)
    window.metrics_text = QTextEdit()
    window.metrics_text.setReadOnly(True)
    window.metrics_text.setMinimumHeight(220)
    window.metrics_text.setMaximumHeight(260)
    window._style_terminal_console(window.metrics_text)
    metrics_layout.addWidget(window.metrics_text)
    layout.addWidget(metrics_box)

    detail_recap_splitter = QSplitter(Qt.Horizontal)
    detail_recap_splitter.setChildrenCollapsible(False)
    decision_box = QGroupBox("交易决策画像")
    execution_box = QGroupBox("执行状态回放")
    conclusion_box = QGroupBox("复盘结论")
    window._style_terminal_panel(decision_box, execution_box, conclusion_box)

    decision_layout = QVBoxLayout(decision_box)
    window.detail_decision_text = QTextEdit()
    window.detail_decision_text.setReadOnly(True)
    window.detail_decision_text.setMinimumHeight(210)
    window.detail_decision_text.setMaximumHeight(240)
    window._style_terminal_console(window.detail_decision_text)
    window.detail_decision_text.setPlainText("选中标的后，这里会展示当前推荐、题材、策略和计划价位。")
    decision_layout.addWidget(window.detail_decision_text)

    execution_layout = QVBoxLayout(execution_box)
    window.detail_execution_text = QTextEdit()
    window.detail_execution_text.setReadOnly(True)
    window.detail_execution_text.setMinimumHeight(210)
    window.detail_execution_text.setMaximumHeight(240)
    window._style_terminal_console(window.detail_execution_text)
    window.detail_execution_text.setPlainText("选中标的后，这里会展示送审、提交、失败和最近执行回放。")
    execution_layout.addWidget(window.detail_execution_text)

    conclusion_layout = QVBoxLayout(conclusion_box)
    window.detail_conclusion_text = QTextEdit()
    window.detail_conclusion_text.setReadOnly(True)
    window.detail_conclusion_text.setMinimumHeight(210)
    window.detail_conclusion_text.setMaximumHeight(240)
    window._style_terminal_console(window.detail_conclusion_text)
    window.detail_conclusion_text.setPlainText("先看结论、回测和下一步。")
    conclusion_layout.addWidget(window.detail_conclusion_text)

    detail_recap_splitter.addWidget(decision_box)
    detail_recap_splitter.addWidget(execution_box)
    detail_recap_splitter.addWidget(conclusion_box)
    window._configure_splitter(detail_recap_splitter, [420, 420, 420])
    layout.addWidget(detail_recap_splitter)

    signal_box = QGroupBox("近期信号")
    trade_box = QGroupBox("交易记录")
    window._style_terminal_panel(signal_box, trade_box)
    signal_layout = QVBoxLayout(signal_box)
    window.signal_table = build_table(["日期", "信号", "评分", "收盘价", "原因"])
    signal_layout.addWidget(window.signal_table)
    trade_layout = QVBoxLayout(trade_box)
    window.trades_table = build_table(["入场日期", "离场日期", "买入价", "卖出价", "股数", "盈亏", "退出原因"])
    trade_layout.addWidget(window.trades_table)

    bottom = QSplitter(Qt.Horizontal)
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(signal_box)
    bottom.addWidget(trade_box)
    window._configure_splitter(bottom, [470, 690])
    layout.addWidget(bottom, stretch=1)

def build_broker_workspace(window, build_table, adapter_factory, project_root: Path) -> None:
    window.broker_tab.setObjectName("brokerRoot")
    root_layout = QVBoxLayout(window.broker_tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    window.broker_scroll_area = QScrollArea()
    window.broker_scroll_area.setWidgetResizable(True)
    window.broker_scroll_area.setFrameShape(QFrame.NoFrame)
    window.broker_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.broker_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    root_layout.addWidget(window.broker_scroll_area)

    broker_content = QWidget()
    window.broker_scroll_area.setWidget(broker_content)
    layout = QVBoxLayout(broker_content)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)

    layout.addWidget(
        window._build_workspace_hero(
            "交易执行",
            "账户接入、委托计划、人工确认",
            "先看主线闸门、风险灯和提交状态，再决定是否一键确认下单。",
            [("人工确认", "确认下单"), ("SDK", "可选接入")],
        )
    )
    window.broker_status_banner = QLabel("交易状态：先看执行阶段，再确认闸门和回执。")
    window.broker_status_banner.setObjectName("statusBanner")
    layout.addWidget(window.broker_status_banner)
    window.broker_stage_label = QLabel("执行阶段：待生成委托 | 先从推荐页或交易计划建立第一笔可执行委托。")
    window.broker_stage_label.setObjectName("focusStateLabel")
    window.broker_stage_label.setWordWrap(True)
    layout.addWidget(window.broker_stage_label)

    profile_box = QGroupBox("账户配置")
    window._style_terminal_panel(profile_box)
    profile_box.setObjectName("workspaceToolPanel")
    profile_grid = QGridLayout(profile_box)
    adapter = adapter_factory()
    profile = window.state.broker_profile
    fields = [
        ("account_name", "账户名称", profile.account_name),
        ("account_id", "账户 ID", profile.account_id),
        ("export_dir", "导出目录", profile.export_dir or str(project_root / "exports")),
        ("sdk_module", "SDK 模块", profile.sdk_module),
        ("sdk_python_path", "桥接 Python", profile.sdk_python_path or adapter.resolve_bridge_python(profile)),
        ("token", "SDK Token", profile.token),
        ("strategy_id", "策略 ID", profile.strategy_id),
    ]
    for idx, (key, label, value) in enumerate(fields):
        row = idx // 2
        col = (idx % 2) * 2
        profile_grid.addWidget(QLabel(label), row, col)
        field = QLineEdit(value)
        window.broker_inputs[key] = field
        profile_grid.addWidget(field, row, col + 1)

    mode_row = 4
    current_mode = profile.mode or "export"
    profile_grid.addWidget(QLabel("交易模式"), mode_row, 0)
    window.mode_combo = QComboBox()
    window.mode_combo.addItem("导出模式", "export")
    window.mode_combo.addItem("SDK 模式", "sdk")
    window.mode_combo.setCurrentIndex(0 if current_mode == "export" else 1)
    profile_grid.addWidget(window.mode_combo, mode_row, 1)

    profile_grid.addWidget(QLabel("单笔预算"), mode_row, 2)
    window.per_trade_budget_input = QLineEdit("30000")
    profile_grid.addWidget(window.per_trade_budget_input, mode_row, 3)

    choose_export_button = QPushButton("选择导出目录")
    save_profile_button = QPushButton("保存账户配置")
    create_templates_button = QPushButton("生成模板文件")
    window._set_button_role(choose_export_button)
    window._set_button_role(save_profile_button, "accent")
    window._set_button_role(create_templates_button)
    for button in (choose_export_button, save_profile_button, create_templates_button):
        button.setMinimumHeight(38)
        button.setMinimumWidth(150)
    choose_export_button.clicked.connect(window.choose_export_dir)
    save_profile_button.clicked.connect(window.save_profile)
    create_templates_button.clicked.connect(window.create_broker_templates)
    profile_grid.addWidget(choose_export_button, 0, 4)
    profile_grid.addWidget(save_profile_button, 1, 4)
    profile_grid.addWidget(create_templates_button, 2, 4)

    action_box = QGroupBox("快速执行")
    window._style_terminal_panel(action_box)
    action_box.setObjectName("workspaceToolPanel")
    action_grid = QGridLayout(action_box)
    action_grid.setHorizontalSpacing(10)
    action_grid.setVerticalSpacing(10)
    action_specs = [
        ("导入持仓", window.import_holdings_csv, "ghost"),
        ("导入资金", window.import_cash_csv, "ghost"),
        ("生成盘中计划", window.generate_order_suggestions, "accent"),
        ("导出计划快照", window.export_order_plan, "ghost"),
        ("导出提交回放", window.export_order_result_log, "ghost"),
        ("同步 SDK", window.sync_broker_via_sdk, "ghost"),
        ("生成 GM 脚本", window.generate_sdk_strategy_script, "ghost"),
        ("确认提交", window.confirm_and_submit_orders, "accent"),
    ]
    for index, (label, handler, role) in enumerate(action_specs):
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setMinimumHeight(42)
        button.clicked.connect(handler)
        if label == "生成盘中计划":
            window.generate_order_suggestions_button = button
        elif label == "确认提交":
            window.confirm_submit_orders_button = button
        action_grid.addWidget(button, index // 4, index % 4)

    broker_metrics_box = QGroupBox("执行指标")
    window._style_terminal_panel(broker_metrics_box)
    broker_metrics_layout = QHBoxLayout(broker_metrics_box)
    broker_metrics_layout.setContentsMargins(12, 12, 12, 12)
    broker_metrics_layout.setSpacing(10)
    window.broker_metric_labels = {}
    window.broker_metric_accents = {}
    for key, title, accent in [
        ("readiness", "执行准备度", "等待评估"),
        ("capital", "资金占用", "0.00"),
        ("risk_reward", "盈亏比", "-- / --"),
        ("risk_budget", "可用风险", "等待评估"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_metric_labels[key] = value_label
        window.broker_metric_accents[key] = accent_label
        broker_metrics_layout.addWidget(card)
    layout.addWidget(broker_metrics_box)

    broker_execution_box = QGroupBox("主线审查 / 执行中控")
    window._style_terminal_panel(broker_execution_box)
    broker_execution_layout = QVBoxLayout(broker_execution_box)
    window.broker_gate_summary_text = QTextEdit()
    window.broker_gate_summary_text.setReadOnly(True)
    window.broker_gate_summary_text.setMinimumHeight(112)
    window.broker_gate_summary_text.setMaximumHeight(136)
    window._style_terminal_console(window.broker_gate_summary_text)
    window.broker_gate_summary_text.setPlainText("先看红灯，再看主线闸门和资金占用。")
    broker_execution_layout.addWidget(window.broker_gate_summary_text)

    broker_gate_action_row = QHBoxLayout()
    broker_gate_action_row.setSpacing(10)
    window.broker_focus_blocker_button = QPushButton("定位阻塞")
    window.broker_focus_priority_button = QPushButton("定位前排")
    window._set_button_role(window.broker_focus_blocker_button, "ghost")
    window._set_button_role(window.broker_focus_priority_button, "accent")
    window.broker_focus_blocker_button.setMinimumHeight(38)
    window.broker_focus_priority_button.setMinimumHeight(38)
    window.broker_focus_blocker_button.clicked.connect(window.focus_first_broker_blocker)
    window.broker_focus_priority_button.clicked.connect(window.focus_priority_broker_order)
    broker_gate_action_row.addWidget(window.broker_focus_blocker_button)
    broker_gate_action_row.addWidget(window.broker_focus_priority_button)
    broker_gate_action_row.addStretch(1)
    broker_execution_layout.addLayout(broker_gate_action_row)

    window.broker_mainline_review_text = QTextEdit()
    window.broker_mainline_review_text.setReadOnly(True)
    window.broker_mainline_review_text.setMinimumHeight(150)
    window.broker_mainline_review_text.setMaximumHeight(180)
    window._style_terminal_console(window.broker_mainline_review_text)
    window.broker_mainline_review_text.setPlainText("这里会显示主线闸门结果、阻塞原因和优先级说明。")
    broker_execution_layout.addWidget(window.broker_mainline_review_text)

    window.broker_execution_text = QTextEdit()
    window.broker_execution_text.setReadOnly(True)
    window.broker_execution_text.setMinimumHeight(190)
    window.broker_execution_text.setMaximumHeight(230)
    window._style_terminal_console(window.broker_execution_text)
    window.broker_execution_text.setPlainText("生成盘中计划后，这里会汇总订单节奏、确认建议和提交记录。")
    broker_execution_layout.addWidget(window.broker_execution_text)
    layout.addWidget(broker_execution_box)

    status_box = QGroupBox("账户状态 / 诊断")
    window._style_terminal_panel(status_box)
    status_layout = QVBoxLayout(status_box)
    window.broker_status_text = QTextEdit()
    window.broker_status_text.setReadOnly(True)
    window.broker_status_text.setMinimumHeight(200)
    window.broker_status_text.setMaximumHeight(240)
    window._style_terminal_console(window.broker_status_text)
    status_layout.addWidget(window.broker_status_text)
    layout.addWidget(status_box)

    runtime_box = QGroupBox("运行维护 / 日志")
    window._style_terminal_panel(runtime_box)
    runtime_box.setObjectName("workspaceToolPanel")
    runtime_layout = QVBoxLayout(runtime_box)
    window.runtime_status_text = QTextEdit()
    window.runtime_status_text.setReadOnly(True)
    window.runtime_status_text.setMinimumHeight(110)
    window.runtime_status_text.setMaximumHeight(126)
    window._style_terminal_console(window.runtime_status_text)
    runtime_layout.addWidget(window.runtime_status_text)

    runtime_action_row = QHBoxLayout()
    runtime_action_specs = [
        ("刷新诊断", window.refresh_runtime_panel, "ghost", "runtimeRefreshButton"),
        ("导出运行日志", window.export_runtime_log, "ghost", "runtimeExportButton"),
        ("清理行情缓存", window.clear_market_cache, "ghost", "runtimeClearCacheButton"),
    ]
    for label, handler, role, object_name in runtime_action_specs:
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setObjectName(object_name)
        button.setMinimumHeight(38)
        button.clicked.connect(handler)
        runtime_action_row.addWidget(button)
    runtime_action_row.addStretch(1)
    runtime_layout.addLayout(runtime_action_row)

    window.runtime_log_text = QTextEdit()
    window.runtime_log_text.setReadOnly(True)
    window._style_terminal_console(window.runtime_log_text)
    runtime_layout.addWidget(window.runtime_log_text)
    window.runtime_status_text.setPlainText(window._runtime_overview_text())
    if not window.runtime_events:
        window._append_runtime_log("运行面板已初始化，后续会记录刷新、导出和执行事件。")

    broker_control_splitter = QSplitter(Qt.Horizontal)
    window.broker_control_splitter = broker_control_splitter
    broker_control_splitter.setObjectName("workspaceControlSplit")
    broker_control_splitter.setChildrenCollapsible(False)
    broker_control_splitter.addWidget(profile_box)
    broker_control_splitter.addWidget(action_box)
    broker_control_splitter.addWidget(runtime_box)
    window._configure_splitter(broker_control_splitter, [520, 500, 360])
    layout.addWidget(broker_control_splitter)

    holdings_box = QGroupBox("当前持仓")
    orders_box = QGroupBox("委托执行台")
    window._style_terminal_panel(holdings_box, orders_box)

    holdings_layout = QVBoxLayout(holdings_box)
    window.holdings_table = build_table(["代码", "持仓数量", "可卖数量", "成本价", "市值"])
    window.holdings_table.setMinimumHeight(300)
    window.holdings_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    holdings_layout.addWidget(window.holdings_table)

    orders_layout = QVBoxLayout(orders_box)
    order_focus_splitter = QSplitter(Qt.Horizontal)
    window.broker_order_focus_splitter = order_focus_splitter
    order_focus_splitter.setChildrenCollapsible(False)
    order_focus_splitter.setObjectName("brokerOrderFocusSplit")

    orders_table_panel = QWidget()
    orders_table_layout = QVBoxLayout(orders_table_panel)
    orders_table_layout.setContentsMargins(0, 0, 0, 0)
    orders_table_layout.setSpacing(8)
    window.orders_focus_label = QLabel(ORDERS_DEFAULT_FOCUS_TEXT)
    window.orders_focus_label.setObjectName("focusStateLabel")
    orders_table_layout.addWidget(window.orders_focus_label)
    window.orders_table = build_table(
        ["优先级", "代码", "动作", "价格", "数量", "预计占用", "盈亏比", "止损", "目标", "主线闸门", "信号日期", "原因摘要", "风险灯"]
    )
    window.orders_table.setMinimumHeight(300)
    window.orders_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.orders_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.orders_table.setObjectName("brokerOrdersTable")
    window.orders_table.itemSelectionChanged.connect(window._on_orders_selection_changed)
    orders_table_layout.addWidget(window.orders_table)

    order_focus_panel = QWidget()
    order_focus_layout = QVBoxLayout(order_focus_panel)
    order_focus_layout.setContentsMargins(0, 0, 0, 0)
    order_focus_layout.setSpacing(8)
    order_focus_title = QLabel("当前委托详情")
    order_focus_title.setObjectName("sectionTitle")
    order_focus_layout.addWidget(order_focus_title)

    broker_order_cards_box = QFrame()
    broker_order_cards_layout = QHBoxLayout(broker_order_cards_box)
    broker_order_cards_layout.setContentsMargins(0, 0, 0, 0)
    broker_order_cards_layout.setSpacing(8)
    window.broker_order_metric_cards = {}
    window.broker_order_metric_labels = {}
    window.broker_order_metric_accents = {}
    for key, title, accent in [
        ("symbol", "焦点委托", "等待选中"),
        ("gate", "主线闸门", "待审查"),
        ("risk", "风险检查", "待评估"),
        ("position", "仓位变化", "待计算"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_order_metric_cards[key] = card
        window.broker_order_metric_labels[key] = value_label
        window.broker_order_metric_accents[key] = accent_label
        broker_order_cards_layout.addWidget(card)
    order_focus_layout.addWidget(broker_order_cards_box)

    window.broker_order_focus_text = QTextEdit()
    window.broker_order_focus_text.setReadOnly(True)
    window.broker_order_focus_text.setMinimumHeight(300)
    window._style_terminal_console(window.broker_order_focus_text)
    window.broker_order_focus_text.setPlainText("选中一笔委托后，这里会显示风险灯、主线闸门和仓位变化。")
    order_focus_layout.addWidget(window.broker_order_focus_text)

    order_focus_splitter.addWidget(orders_table_panel)
    order_focus_splitter.addWidget(order_focus_panel)
    window._configure_splitter(order_focus_splitter, [720, 340])
    orders_layout.addWidget(order_focus_splitter)

    middle = QSplitter(Qt.Horizontal)
    window.broker_middle_splitter = middle
    middle.setChildrenCollapsible(False)
    middle.addWidget(holdings_box)
    middle.addWidget(orders_box)
    window._configure_splitter(middle, [460, 700])
    layout.addWidget(middle, stretch=1)

    detail_toggle_row = QHBoxLayout()
    window.broker_detail_toggle_button = QPushButton("展开执行明细")
    window._set_button_role(window.broker_detail_toggle_button, "ghost")
    window.broker_detail_toggle_button.clicked.connect(window.toggle_broker_execution_detail)
    window.broker_detail_status_label = QLabel("执行明细已折叠，先看焦点委托、阶段判断和风险闸门。")
    window.broker_detail_status_label.setObjectName("inlineHint")
    window.broker_detail_status_label.setWordWrap(True)
    detail_toggle_row.addWidget(window.broker_detail_toggle_button)
    detail_toggle_row.addWidget(window.broker_detail_status_label, stretch=1)
    layout.addLayout(detail_toggle_row)

    result_box = QGroupBox("执行回执")
    window._style_terminal_panel(result_box)
    window.broker_result_box = result_box
    result_layout = QVBoxLayout(result_box)
    window.execution_table = build_table(["时间", "订单", "成交", "代码", "动作", "价格", "数量", "错误", "信息"])
    window.execution_table.setMinimumHeight(280)
    window.execution_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.execution_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.execution_table.setObjectName("submissionTable")
    result_layout.addWidget(window.execution_table)

    window.order_result_text = QTextEdit()
    window.order_result_text.setReadOnly(True)
    window._style_terminal_console(window.order_result_text)
    window.order_result_text.setPlainText("等待新的执行结果...\n")
    result_layout.addWidget(window.order_result_text)
    layout.addWidget(result_box, stretch=1)

    recap_box = QGroupBox("偏差复盘")
    window._style_terminal_panel(recap_box)
    window.broker_recap_box = recap_box
    recap_layout = QVBoxLayout(recap_box)
    window.broker_recap_text = QTextEdit()
    window.broker_recap_text.setReadOnly(True)
    window.broker_recap_text.setMinimumHeight(180)
    window.broker_recap_text.setMaximumHeight(220)
    window._style_terminal_console(window.broker_recap_text)
    window.broker_recap_text.setPlainText("提交后，这里沉淀通过率、阻塞原因和偏差。")
    recap_layout.addWidget(window.broker_recap_text)
    layout.addWidget(recap_box)

def build_overview_workspace(
    window,
    build_table,
    strategy_params_factory,
    action_flow_card_cls,
    compact_summary_card_cls,
    leaderboard_card_cls,
) -> None:
    chart_view_cls = getattr(window, "_chart_view_cls", QChartView)
    window.overview_tab.setObjectName("overviewRoot")
    root_layout = QVBoxLayout(window.overview_tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)
    window.overview_scroll_area = QScrollArea()
    window.overview_scroll_area.setWidgetResizable(True)
    window.overview_scroll_area.setFrameShape(QFrame.NoFrame)
    window.overview_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.overview_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    root_layout.addWidget(window.overview_scroll_area)
    overview_content = QWidget()
    overview_content.setObjectName("overviewRoot")
    window.overview_scroll_area.setWidget(overview_content)
    layout = QVBoxLayout(overview_content)
    layout.setContentsMargins(10, 10, 10, 18)
    layout.setSpacing(14)
    quick_row = QHBoxLayout()
    quick_row.setSpacing(10)
    window.overview_quick_buttons = {}
    for index, (text, color) in enumerate(
        [
            ("市场总览", "#f1c40f"),
            ("主线龙头", "#f1c40f"),
            ("趋势机会", "#39b980"),
            ("消息催化", "#ff5b57"),
            ("买卖决策", "#d16aff"),
            ("复盘研究", "#7a9cff"),
        ]
    ):
        button = QPushButton(text)
        button.setCheckable(True)
        button.setChecked(index == 0)
        button.setMinimumHeight(42)
        button.setMinimumWidth(120)
        button.setStyleSheet(window._overview_outline_style(color))
        button.clicked.connect(lambda checked=False, current_text=text: window.activate_overview_quick_action(current_text))
        window.overview_quick_buttons[text] = button
        quick_row.addWidget(button)
    quick_row.addStretch(1)
    toolbar = QHBoxLayout()
    toolbar.setSpacing(10)
    window.market_search_input = QLineEdit()
    window.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材")
    window.market_search_input.setMinimumHeight(42)
    window.market_search_input.setMinimumWidth(240)
    window.market_search_input.setMaximumWidth(360)
    window.market_search_input.textChanged.connect(window._apply_market_filters)
    window.market_theme_combo = QComboBox()
    window.market_theme_combo.addItem("全部")
    window.market_theme_combo.setMinimumHeight(42)
    window.market_theme_combo.setMinimumWidth(120)
    window.market_theme_combo.currentTextChanged.connect(window._on_market_theme_filter_changed)
    window.market_history_date_combo = QComboBox()
    window.market_history_date_combo.addItem("最新")
    window.market_history_date_combo.setMinimumHeight(42)
    window.market_history_date_combo.setMinimumWidth(180)
    window.market_history_date_combo.currentTextChanged.connect(window._on_market_history_date_changed)
    window.market_refresh_button = QPushButton("一键刷新算法池")
    window.market_refresh_button.setMinimumHeight(42)
    window.market_refresh_button.setMinimumWidth(180)
    window.market_refresh_button.setStyleSheet(window._overview_filled_style("#237fa2"))
    window.market_refresh_button.clicked.connect(lambda: window.refresh_remote_market(update_chart=True))
    window.market_history_reset_button = QPushButton("回到最新")
    window.market_history_reset_button.setMinimumHeight(42)
    window.market_history_reset_button.setMinimumWidth(126)
    window._set_button_role(window.market_history_reset_button, "ghost")
    window.market_history_reset_button.clicked.connect(window.reset_market_history_view)
    window.dashboard_auto_refresh_checkbox = QCheckBox("盘中自动刷新")
    window.dashboard_auto_refresh_checkbox.toggled.connect(window.toggle_dashboard_auto_refresh)
    window.dashboard_auto_refresh_checkbox.blockSignals(True)
    window.dashboard_auto_refresh_checkbox.setChecked(True)
    window.dashboard_auto_refresh_checkbox.blockSignals(False)
    window.market_status_label = QLabel("总览状态：正在准备市场数据...")
    window.market_status_label.setObjectName("statusBanner")
    toolbar.addWidget(window.market_search_input)
    toolbar.addWidget(window.market_theme_combo)
    toolbar.addWidget(window.market_history_date_combo)
    toolbar.addWidget(window.market_history_reset_button)
    toolbar.addWidget(window.market_refresh_button)
    toolbar.addWidget(window.dashboard_auto_refresh_checkbox)
    toolbar.addWidget(window.market_status_label, stretch=1)
    filter_row = QHBoxLayout()
    filter_row.setSpacing(10)
    window.market_filter_buttons = {}
    for tag in ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "掘龙决策"]:
        button = QPushButton(tag)
        button.setCheckable(True)
        button.setMinimumHeight(44)
        button.setMinimumWidth(128)
        button.setStyleSheet(window._overview_filled_style("#237fa2"))
        button.clicked.connect(lambda checked=False, current_tag=tag: window.set_market_filter(current_tag))
        if tag == "全部":
            button.setChecked(True)
        window.market_filter_buttons[tag] = button
        filter_row.addWidget(button)
    if "一日持股法" not in window.market_filter_buttons:
        one_day_button = QPushButton("一日持股法")
        one_day_button.setCheckable(True)
        one_day_button.setMinimumHeight(44)
        one_day_button.setMinimumWidth(128)
        one_day_button.setStyleSheet(window._overview_filled_style("#237fa2"))
        one_day_button.clicked.connect(lambda checked=False: window.set_market_filter("一日持股法"))
        window.market_filter_buttons["一日持股法"] = one_day_button
        filter_row.addWidget(one_day_button)
    filter_row.addStretch(1)
    controls_splitter = QSplitter(Qt.Horizontal)
    controls_splitter.setObjectName("workspaceControlSplit")
    controls_splitter.setChildrenCollapsible(False)
    overview_view_box = QGroupBox("投资视图")
    overview_search_box = QGroupBox("搜索与刷新")
    overview_tag_box = QGroupBox("策略快筛")
    window._style_terminal_panel(overview_view_box, overview_search_box, overview_tag_box)
    overview_view_layout = QVBoxLayout(overview_view_box)
    overview_view_layout.addLayout(quick_row)
    overview_search_layout = QVBoxLayout(overview_search_box)
    overview_search_layout.addLayout(toolbar)
    overview_tag_layout = QVBoxLayout(overview_tag_box)
    overview_tag_layout.addLayout(filter_row)
    controls_splitter.addWidget(overview_view_box)
    controls_splitter.addWidget(overview_search_box)
    controls_splitter.addWidget(overview_tag_box)
    window._configure_splitter(controls_splitter, [420, 520, 560])
    layout.addWidget(controls_splitter)
    dashboard_metrics_box = QGroupBox("核心指标带")
    window._style_terminal_panel(dashboard_metrics_box)
    dashboard_metrics_box.setProperty("surfaceRole", "metric-band")
    metrics_row = QHBoxLayout(dashboard_metrics_box)
    metrics_row.setContentsMargins(12, 12, 12, 12)
    metrics_row.setSpacing(10)
    window.dashboard_metric_labels = {}
    window.dashboard_metric_accents = {}
    for key, title, accent in [
        ("candidate_count", "算法候选", "等待刷新"),
        ("buy_count", "可买数量", "等待刷新"),
        ("avg_heat", "平均热度", "等待刷新"),
        ("top_theme", "当前主线", "等待刷新"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.dashboard_metric_labels[key] = value_label
        window.dashboard_metric_accents[key] = accent_label
        metrics_row.addWidget(card)
    layout.addWidget(dashboard_metrics_box)
    cockpit_box = QGroupBox("市场驾驶舱")
    window._style_terminal_panel(cockpit_box)
    cockpit_box.setProperty("surfaceRole", "spotlight")
    cockpit_layout = QVBoxLayout(cockpit_box)
    cockpit_body = QSplitter(Qt.Horizontal)
    cockpit_body.setChildrenCollapsible(False)
    window.overview_command_text = QTextEdit()
    window.overview_command_text.setReadOnly(True)
    window.overview_command_text.setObjectName("marketNotePanel")
    window.overview_command_text.setProperty("panelTone", "command")
    window.overview_command_text.setMinimumHeight(150)
    cockpit_body.addWidget(window.overview_command_text)
    window.overview_execution_text = QTextEdit()
    window.overview_execution_text.setReadOnly(True)
    window.overview_execution_text.setObjectName("marketNotePanel")
    window.overview_execution_text.setProperty("panelTone", "execution")
    window.overview_execution_text.setMinimumHeight(150)
    cockpit_body.addWidget(window.overview_execution_text)
    window._configure_splitter(cockpit_body, [1, 1])
    cockpit_layout.addWidget(cockpit_body)
    cockpit_action_row = QHBoxLayout()
    for label, workspace in [
        ("前往推荐页", "recommend"),
        ("前往交易页", "broker"),
        ("前往配置页", "config"),
    ]:
        button = QPushButton(label)
        window._set_button_role(button, "ghost" if workspace != "broker" else "accent")
        button.setMinimumHeight(40)
        button.clicked.connect(lambda checked=False, target=workspace: window._navigate_to_workspace(target))
        cockpit_action_row.addWidget(button)
    cockpit_action_row.addStretch(1)
    cockpit_layout.addLayout(cockpit_action_row)
    layout.addWidget(cockpit_box)

    playbook_box = QGroupBox("行动剧本")
    window._style_terminal_panel(playbook_box)
    playbook_box.setProperty("surfaceRole", "spotlight")
    playbook_layout = QVBoxLayout(playbook_box)
    window.overview_playbook_text = QTextEdit()
    window.overview_playbook_text.setReadOnly(True)
    window.overview_playbook_text.setObjectName("marketNotePanel")
    window.overview_playbook_text.setProperty("panelTone", "playbook")
    window.overview_playbook_text.setMinimumHeight(118)
    window.overview_playbook_text.setPlainText(
        "先完成登录与交易通道配置，再刷新市场、查看主线和推荐池，最后进入交易执行页复核委托。"
    )
    playbook_layout.addWidget(window.overview_playbook_text)
    playbook_action_row = QHBoxLayout()
    for label, workspace, role in [
        ("前往登录配置", "auth", "accent"),
        ("前往推荐池", "recommend", "ghost"),
        ("前往交易执行", "broker", "ghost"),
    ]:
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setMinimumHeight(38)
        button.clicked.connect(lambda checked=False, target=workspace: window._navigate_to_workspace(target))
        playbook_action_row.addWidget(button)
    playbook_action_row.addStretch(1)
    playbook_layout.addLayout(playbook_action_row)
    layout.addWidget(playbook_box)

    window.overview_stage_container = QWidget()
    overview_stage_layout = QVBoxLayout(window.overview_stage_container)
    overview_stage_layout.setContentsMargins(0, 0, 0, 0)
    overview_stage_layout.setSpacing(14)
    overview_command_stage = QWidget()
    overview_detail_stage = QWidget()
    overview_stage_layout.addWidget(overview_command_stage, stretch=5)
    overview_stage_layout.addWidget(overview_detail_stage, stretch=2)
    layout.addWidget(window.overview_stage_container, stretch=5)
    command_stage_layout = QVBoxLayout(overview_command_stage)
    command_stage_layout.setContentsMargins(0, 8, 0, 0)
    command_stage_layout.setSpacing(14)
    detail_stage_layout = QVBoxLayout(overview_detail_stage)
    detail_stage_layout.setContentsMargins(0, 8, 0, 0)
    detail_stage_layout.setSpacing(14)
    overview_priority_box = QGroupBox("盘前优先级")
    window._style_terminal_panel(overview_priority_box)
    overview_priority_box.setProperty("surfaceRole", "priority-rail")
    overview_priority_layout = QHBoxLayout(overview_priority_box)
    overview_priority_layout.setContentsMargins(12, 12, 12, 12)
    overview_priority_layout.setSpacing(10)
    window.overview_priority_cards = {
        "market": action_flow_card_cls("买", "#25d07f"),
        "theme": action_flow_card_cls("持", "#4fc3f7"),
        "strategy": action_flow_card_cls("减", "#ffb347"),
        "focus": action_flow_card_cls("卖", "#ff6b6b"),
    }
    for key in ["market", "theme", "strategy", "focus"]:
        overview_priority_layout.addWidget(window.overview_priority_cards[key])
    command_stage_layout.addWidget(overview_priority_box)
    main_splitter = QSplitter(Qt.Horizontal)
    main_splitter.setChildrenCollapsible(False)
    window.overview_main_splitter = main_splitter
    left_panel = QWidget()
    left_panel.setMinimumWidth(300)
    left_layout = QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(10)
    left_title = QLabel("市场快照")
    left_title.setObjectName("heroTitle")
    left_layout.addWidget(left_title)
    window.intraday_chart_view = chart_view_cls()
    _configure_chart_view(window.intraday_chart_view, min_height=260)
    left_layout.addWidget(window.intraday_chart_view, stretch=5)
    left_notes = QWidget()
    left_notes_layout = QVBoxLayout(left_notes)
    left_notes_layout.setContentsMargins(0, 0, 0, 0)
    left_notes_layout.setSpacing(10)
    buy_box = QGroupBox("今天能不能买")
    buy_layout = QVBoxLayout(buy_box)
    window.market_buy_text = QTextEdit()
    window.market_buy_text.setReadOnly(True)
    window.market_buy_text.setObjectName("marketNotePanel")
    window.market_buy_text.setProperty("panelTone", "buy")
    window.market_buy_text.setMinimumHeight(140)
    buy_layout.addWidget(window.market_buy_text)
    risk_box = QGroupBox("减仓和卖点")
    risk_layout = QVBoxLayout(risk_box)
    window.market_sell_text = QTextEdit()
    window.market_sell_text.setReadOnly(True)
    window.market_sell_text.setObjectName("marketNotePanel")
    window.market_sell_text.setProperty("panelTone", "risk")
    window.market_sell_text.setMinimumHeight(140)
    risk_layout.addWidget(window.market_sell_text)
    breadth_box = QGroupBox("消息面")
    breadth_layout = QVBoxLayout(breadth_box)
    window.market_news_group = breadth_box
    window.market_breadth_text = QTextEdit()
    window.market_breadth_text.setReadOnly(True)
    window.market_breadth_text.setObjectName("marketNotePanel")
    window.market_breadth_text.setProperty("panelTone", "watch")
    window.market_breadth_text.setMinimumHeight(150)
    breadth_layout.addWidget(window.market_breadth_text)
    left_notes_layout.addWidget(buy_box)
    left_notes_layout.addWidget(risk_box)
    left_notes_layout.addWidget(breadth_box)
    left_layout.addWidget(left_notes, stretch=2)
    main_splitter.addWidget(left_panel)
    center_panel = QWidget()
    center_panel.setMinimumWidth(860)
    center_layout = QVBoxLayout(center_panel)
    center_layout.setContentsMargins(0, 0, 0, 0)
    center_layout.setSpacing(10)
    window.market_header_label = QLabel("市场机会工作台")
    window.market_header_label.setObjectName("heroTitle")
    center_layout.addWidget(window.market_header_label)
    window.market_subheader_label = QLabel("统一查看主线龙头、趋势机会、消息催化、买卖决策和复盘研究。")
    window.market_subheader_label.setObjectName("heroSubtitle")
    window.market_subheader_label.setWordWrap(True)
    center_layout.addWidget(window.market_subheader_label)
    window.market_signal_label = QLabel("资金模型 / 策略标签 / 主力净流入 / 换手率")
    window.market_signal_label.setObjectName("terminalSignal")
    center_layout.addWidget(window.market_signal_label)
    window.market_quote_label = QLabel("开高低收 / 涨跌幅 / 换手 / 主力净流入 / 龙头级别 / 股票池")
    window.market_quote_label.setObjectName("inlineHint")
    window.market_quote_label.setWordWrap(True)
    center_layout.addWidget(window.market_quote_label)
    timeframe_row = QHBoxLayout()
    timeframe_row.setSpacing(8)
    window.timeframe_buttons = {}
    for text in ["分时", "1分", "5分", "15分", "30分", "60分", "日线", "周线", "月线"]:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(42)
        button.setMinimumWidth(80)
        button.setStyleSheet(window._overview_filled_style("#237fa2"))
        button.clicked.connect(lambda checked=False, current_timeframe=text: window.set_market_timeframe(current_timeframe))
        if text == "日线":
            button.setChecked(True)
        window.timeframe_buttons[text] = button
        timeframe_row.addWidget(button)
    timeframe_row.addStretch(1)
    center_layout.addLayout(timeframe_row)
    history_row = QHBoxLayout()
    history_row.setSpacing(8)
    window.history_window_buttons = {}
    for text in ["近3月", "近1年", "近3年", "全部"]:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(38)
        button.setMinimumWidth(92)
        button.setStyleSheet(window._overview_outline_style("#8f6c34"))
        button.clicked.connect(lambda checked=False, current_window=text: window.set_market_history_window(current_window))
        if text == "近1年":
            button.setChecked(True)
        window.history_window_buttons[text] = button
        history_row.addWidget(button)
    history_row.addStretch(1)
    center_layout.addLayout(history_row)
    chart_control_row = QHBoxLayout()
    chart_control_row.setSpacing(8)
    prev_chart_button = QPushButton("向左看")
    next_chart_button = QPushButton("向右看")
    reset_chart_button = QPushButton("回到最新")
    window._set_button_role(prev_chart_button)
    window._set_button_role(next_chart_button)
    window._set_button_role(reset_chart_button, "tonal")
    prev_chart_button.clicked.connect(lambda: window.shift_market_chart_window(1))
    next_chart_button.clicked.connect(lambda: window.shift_market_chart_window(-1))
    reset_chart_button.clicked.connect(window.reset_market_chart_window)
    chart_control_row.addWidget(prev_chart_button)
    chart_control_row.addWidget(next_chart_button)
    chart_control_row.addWidget(reset_chart_button)
    chart_control_row.addSpacing(12)
    chart_control_row.addWidget(QLabel("主图叠加"))
    window.market_overlay_buttons = {}
    for text, checked in [("MA", True), ("BOLL", True)]:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setMinimumHeight(34)
        button.setMinimumWidth(72)
        window._set_button_role(button, "tonal" if checked else "ghost")
        button.clicked.connect(lambda checked=False, current=text: window.toggle_market_overlay(current))
        window.market_overlay_buttons[text] = button
        chart_control_row.addWidget(button)
    chart_control_row.addSpacing(12)
    chart_control_row.addWidget(QLabel("副图指标"))
    window.secondary_indicator_buttons = {}
    for text, checked in [("MACD", True), ("RSI", False), ("KDJ", False)]:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setChecked(checked)
        button.setMinimumHeight(34)
        button.setMinimumWidth(76)
        window._set_button_role(button, "accent" if checked else "ghost")
        button.clicked.connect(lambda checked=False, current=text: window.set_market_secondary_indicator(current))
        window.secondary_indicator_buttons[text] = button
        chart_control_row.addWidget(button)
    chart_control_row.addStretch(1)
    center_layout.addLayout(chart_control_row)
    window.daily_chart_view = chart_view_cls()
    _configure_chart_view(window.daily_chart_view, min_height=360)
    center_layout.addWidget(window.daily_chart_view, stretch=6)
    mini_chart_row = QSplitter(Qt.Horizontal)
    mini_chart_row.setChildrenCollapsible(False)
    window.overview_mini_chart_splitter = mini_chart_row
    window.fund_chart_view = chart_view_cls()
    _configure_chart_view(window.fund_chart_view, min_height=200)
    mini_chart_row.addWidget(window.fund_chart_view)
    window.momentum_chart_view = chart_view_cls()
    _configure_chart_view(window.momentum_chart_view, min_height=200)
    mini_chart_row.addWidget(window.momentum_chart_view)
    window.indicator_chart_view = chart_view_cls()
    _configure_chart_view(window.indicator_chart_view, min_height=200)
    mini_chart_row.addWidget(window.indicator_chart_view)
    window._configure_splitter(mini_chart_row, [1, 1, 1])
    center_layout.addWidget(mini_chart_row, stretch=2)
    window.price_chart_view = window.daily_chart_view
    window.volume_chart_view = window.fund_chart_view
    pool_box = QGroupBox("机会股票池")
    pool_layout = QVBoxLayout(pool_box)
    window.market_pool_table = build_table(["序", "股票", "资金标签", "策略标签", "涨跌幅", "最新价"])
    window.market_pool_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
    window.market_pool_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
    window.market_pool_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    window.market_pool_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
    window.market_pool_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
    window.market_pool_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
    window.market_pool_table.itemSelectionChanged.connect(window.on_market_pool_selected)
    window.market_pool_table.setShowGrid(False)
    window.market_pool_table.setAlternatingRowColors(False)
    window.market_pool_table.verticalHeader().setDefaultSectionSize(82)
    window.market_pool_table.setObjectName("marketPoolTable")
    window.market_pool_table.setMinimumHeight(260)
    window.market_pool_table.setWordWrap(True)
    window.market_pool_table.setTextElideMode(Qt.ElideNone)
    window.market_pool_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    window.market_pool_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    pool_layout.addWidget(window.market_pool_table)
    center_layout.addWidget(pool_box, stretch=7)
    main_splitter.addWidget(center_panel)
    right_panel = QWidget()
    right_panel.setMinimumWidth(340)
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(10)
    leaderboard_box = QGroupBox("掘龙榜")
    leaderboard_box.setProperty("surfaceRole", "analysis")
    leaderboard_layout = QVBoxLayout(leaderboard_box)
    leaderboard_layout.setContentsMargins(10, 10, 10, 10)
    leaderboard_layout.setSpacing(10)
    window.market_leaderboard_text = QTextEdit()
    window.market_leaderboard_text.setReadOnly(True)
    window.market_leaderboard_text.hide()
    window.market_leaderboard_text.setObjectName("marketNotePanel")
    leaderboard_layout.addWidget(window.market_leaderboard_text)
    window.market_leaderboard_cards = [leaderboard_card_cls() for _ in range(3)]
    for card in window.market_leaderboard_cards:
        leaderboard_layout.addWidget(card)
    right_layout.addWidget(leaderboard_box, stretch=5)
    overview_summary_box = QGroupBox("主控摘要")
    window._style_terminal_panel(overview_summary_box)
    overview_summary_box.setProperty("surfaceRole", "metric-band")
    overview_summary_layout = QHBoxLayout(overview_summary_box)
    overview_summary_layout.setContentsMargins(10, 10, 10, 10)
    overview_summary_layout.setSpacing(10)
    window.overview_summary_cards = {
        "theme": compact_summary_card_cls("大盘", "#c792ea"),
        "source": compact_summary_card_cls("消息", "#7ed7ff"),
        "capital": compact_summary_card_cls("建仓", "#25d07f"),
        "decision": compact_summary_card_cls("持仓", "#ff9f43"),
    }
    for key in ["theme", "source", "capital", "decision"]:
        overview_summary_layout.addWidget(window.overview_summary_cards[key])
    right_layout.addWidget(overview_summary_box, stretch=2)
    right_notes = QWidget()
    right_notes_layout = QVBoxLayout(right_notes)
    right_notes_layout.setContentsMargins(0, 0, 0, 0)
    right_notes_layout.setSpacing(10)
    right_layout.addWidget(right_notes, stretch=4)
    right_summary_box = QGroupBox("主题摘要")
    right_summary_box.setProperty("surfaceRole", "analysis")
    right_summary_layout = QVBoxLayout(right_summary_box)
    right_summary_layout.setContentsMargins(10, 10, 10, 10)
    right_summary_layout.setSpacing(10)
    window.market_theme_brief_text = QTextEdit()
    window.market_theme_brief_text.setReadOnly(True)
    window.market_theme_brief_text.setObjectName("marketNotePanel")
    window.market_theme_brief_text.setProperty("panelTone", "theme")
    window.market_theme_brief_text.setMinimumHeight(168)
    window.market_theme_brief_text.setMaximumHeight(220)
    right_summary_layout.addWidget(window.market_theme_brief_text, stretch=1)
    summary_action_row = QHBoxLayout()
    summary_focus_button = QPushButton("查看推荐池")
    summary_news_button = QPushButton("查看消息催化")
    window._set_button_role(summary_focus_button, "tonal")
    window._set_button_role(summary_news_button, "ghost")
    summary_focus_button.clicked.connect(window.open_overview_theme_to_recommend)
    summary_news_button.clicked.connect(window.open_overview_source_to_news)
    summary_action_row.addWidget(summary_focus_button)
    summary_action_row.addWidget(summary_news_button)
    summary_action_row.addStretch(1)
    right_summary_layout.addLayout(summary_action_row)
    window.market_source_status_text = QTextEdit()
    window.market_source_status_text.setReadOnly(True)
    window.market_source_status_text.setObjectName("marketNotePanel")
    window.market_source_status_text.setProperty("panelTone", "system")
    window.market_source_status_text.setMinimumHeight(168)
    window.market_source_status_text.setMaximumHeight(220)
    right_summary_layout.addWidget(window.market_source_status_text, stretch=1)
    right_notes_layout.addWidget(right_summary_box, stretch=1)
    capital_box = QGroupBox("持仓与大盘")
    capital_box.setProperty("surfaceRole", "analysis")
    capital_layout = QVBoxLayout(capital_box)
    window.market_capital_text = QTextEdit()
    window.market_capital_text.setReadOnly(True)
    window.market_capital_text.setObjectName("marketNotePanel")
    window.market_capital_text.setProperty("panelTone", "capital")
    window.market_capital_text.setMinimumHeight(210)
    window.market_capital_text.setMaximumHeight(260)
    capital_layout.addWidget(window.market_capital_text)
    capital_action_row = QHBoxLayout()
    capital_recommend_button = QPushButton("去看推荐")
    capital_refresh_button = QPushButton("回到总览")
    window._set_button_role(capital_recommend_button, "tonal")
    window._set_button_role(capital_refresh_button, "ghost")
    capital_recommend_button.clicked.connect(window.open_overview_capital_to_recommend)
    capital_refresh_button.clicked.connect(lambda: window._navigate_to_workspace("overview", "market_pool_table"))
    capital_action_row.addWidget(capital_recommend_button)
    capital_action_row.addWidget(capital_refresh_button)
    capital_action_row.addStretch(1)
    capital_layout.addLayout(capital_action_row)
    right_notes_layout.addWidget(capital_box, stretch=1)
    decision_box = QGroupBox("买卖点结论")
    decision_box.setProperty("surfaceRole", "analysis")
    decision_layout = QVBoxLayout(decision_box)
    window.market_decision_text = QTextEdit()
    window.market_decision_text.setReadOnly(True)
    window.market_decision_text.setObjectName("marketNotePanel")
    window.market_decision_text.setProperty("panelTone", "decision")
    window.market_decision_text.setMinimumHeight(210)
    window.market_decision_text.setMaximumHeight(260)
    decision_layout.addWidget(window.market_decision_text)
    decision_action_row = QHBoxLayout()
    decision_broker_button = QPushButton("去看交易")
    decision_recommend_button = QPushButton("去看推荐")
    window._set_button_role(decision_broker_button, "accent")
    window._set_button_role(decision_recommend_button, "tonal")
    decision_broker_button.clicked.connect(window.open_overview_decision_to_broker)
    decision_recommend_button.clicked.connect(window.open_overview_theme_to_recommend)
    decision_action_row.addWidget(decision_broker_button)
    decision_action_row.addWidget(decision_recommend_button)
    decision_action_row.addStretch(1)
    decision_layout.addLayout(decision_action_row)
    right_notes_layout.addWidget(decision_box, stretch=1)
    main_splitter.addWidget(right_panel)
    window._configure_splitter(main_splitter, [300, 1050, 360])
    command_stage_layout.addWidget(main_splitter, stretch=1)
    params_box = QGroupBox("策略参数")
    params_layout = QGridLayout(params_box)
    defaults = strategy_params_factory()
    param_fields = [
        ("breakout_lookback", defaults.breakout_lookback, "突破回看"),
        ("atr_window", defaults.atr_window, "ATR"),
        ("volume_window", defaults.volume_window, "量能窗口"),
        ("fast_ma_window", defaults.fast_ma_window, "快均线"),
        ("slow_ma_window", defaults.slow_ma_window, "慢均线"),
        ("reclaim_window", defaults.reclaim_window, "回补观察"),
        ("min_breakout_pct", defaults.min_breakout_pct, "突破幅度"),
        ("min_volume_ratio", defaults.min_volume_ratio, "放量阈值"),
        ("min_upper_shadow_pct", defaults.min_upper_shadow_pct, "上影比例"),
        ("max_close_location", defaults.max_close_location, "收盘位置"),
        ("max_reclaim_volume_ratio", defaults.max_reclaim_volume_ratio, "回封量比"),
        ("stop_atr_multiple", defaults.stop_atr_multiple, "止损倍数"),
        ("target_atr_multiple", defaults.target_atr_multiple, "止盈倍数"),
    ]
    window.strategy_inputs = {}
    for index, (key, value, label) in enumerate(param_fields):
        row = index // 4
        col = (index % 4) * 2
        widget = QLineEdit(str(value))
        widget.setMaximumWidth(96)
        window.strategy_inputs[key] = widget
        params_layout.addWidget(QLabel(label), row, col)
        params_layout.addWidget(widget, row, col + 1)
    detail_hint = QLabel("参数与细节已并入总览工作台，盘中先看上方结论，盘后再回来微调。")
    detail_hint.setObjectName("inlineHint")
    detail_hint.setWordWrap(True)
    detail_stage_layout.addWidget(detail_hint)
    detail_stage_layout.addWidget(params_box)

def build_recommend_workspace(
    window,
    build_table,
    strategy_workbench_card_cls,
    action_flow_card_cls,
    alert_signal_card_cls,
    compact_summary_card_cls,
    strategy_workbench_specs,
    strategy_score_fields,
) -> None:
    window.recommend_tab.setObjectName("recommendRoot")
    root_layout = QVBoxLayout(window.recommend_tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    window.recommend_scroll_area = QScrollArea()
    window.recommend_scroll_area.setWidgetResizable(True)
    window.recommend_scroll_area.setFrameShape(QFrame.NoFrame)
    window.recommend_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.recommend_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    root_layout.addWidget(window.recommend_scroll_area)

    recommend_content = QWidget()
    recommend_content.setObjectName("recommendRoot")
    window.recommend_scroll_area.setWidget(recommend_content)
    layout = QVBoxLayout(recommend_content)
    layout.setContentsMargins(10, 10, 10, 18)
    layout.setSpacing(14)

    layout.addWidget(
        window._build_workspace_hero(
            "每日推荐",
            "主线先行，盘中执行，盘后复盘",
            "先看主线、位置、风险和送审状态，再决定是否进入今日交易计划。",
            [("Top 5", "今日计划"), ("多因子", "主线筛选")],
        )
    )
    intro = QLabel("先看主线、位置、风险和催化，再看动作与送审。")
    intro.setWordWrap(True)
    intro.setObjectName("inlineHint")
    layout.addWidget(intro)

    import_profile_button = QPushButton("导入股票资料 CSV")
    import_news_button = QPushButton("导入消息面 CSV")
    import_theme_button = QPushButton("导入题材词典 CSV")
    edit_theme_button = QPushButton("编辑题材词典")
    refresh_button = QPushButton("刷新每日推荐池")
    load_sample_button = QPushButton("载入示例资料")
    import_profile_button.clicked.connect(window.import_stock_profiles_csv)
    import_news_button.clicked.connect(window.import_news_catalysts_csv)
    import_theme_button.clicked.connect(window.import_theme_aliases_csv)
    edit_theme_button.clicked.connect(window.open_theme_alias_editor)
    refresh_button.clicked.connect(window.refresh_daily_pool)
    load_sample_button.clicked.connect(window.load_sample_reference_data)
    window._set_button_role(import_profile_button)
    window._set_button_role(import_news_button)
    window._set_button_role(import_theme_button)
    window._set_button_role(edit_theme_button)
    window._set_button_role(refresh_button, "accent")
    window._set_button_role(load_sample_button)

    window.recommend_status_label = QLabel(RECOMMEND_DEFAULT_STATUS_TEXT)
    window.recommend_status_label.setObjectName("statusBanner")

    recommend_empty_box = QGroupBox("快速进入")
    window._style_terminal_panel(recommend_empty_box)
    recommend_empty_box.setObjectName("emptyStatePanel")
    recommend_empty_layout = QVBoxLayout(recommend_empty_box)
    window.recommend_empty_title = QLabel(RECOMMEND_DEFAULT_EMPTY_TITLE)
    window.recommend_empty_title.setObjectName("emptyStateTitle")
    recommend_empty_layout.addWidget(window.recommend_empty_title)
    recommend_empty_hint = QLabel(RECOMMEND_DEFAULT_EMPTY_HINT)
    recommend_empty_hint.setWordWrap(True)
    recommend_empty_hint.setObjectName("inlineHint")
    recommend_empty_layout.addWidget(recommend_empty_hint)
    window.recommend_empty_meta = QLabel(RECOMMEND_DEFAULT_EMPTY_META)
    window.recommend_empty_meta.setObjectName("emptyStateMeta")
    window.recommend_empty_meta.setWordWrap(True)
    recommend_empty_layout.addWidget(window.recommend_empty_meta)
    recommend_empty_action_row = QHBoxLayout()
    window.recommend_empty_sample_button = QPushButton(RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
    window.recommend_empty_refresh_button = QPushButton(RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)
    window._set_button_role(window.recommend_empty_sample_button, "accent")
    window._set_button_role(window.recommend_empty_refresh_button, "ghost")
    window.recommend_empty_sample_button.setMinimumHeight(40)
    window.recommend_empty_refresh_button.setMinimumHeight(40)
    window.recommend_empty_sample_button.clicked.connect(window.load_sample_reference_data)
    window.recommend_empty_refresh_button.clicked.connect(window.refresh_daily_pool)
    recommend_empty_action_row.addWidget(window.recommend_empty_sample_button)
    recommend_empty_action_row.addWidget(window.recommend_empty_refresh_button)
    recommend_empty_action_row.addStretch(1)
    recommend_empty_layout.addLayout(recommend_empty_action_row)
    window.recommend_empty_box = recommend_empty_box

    window.recommend_theme_combo = QComboBox()
    window.recommend_theme_combo.addItem("全部")
    window.recommend_theme_combo.currentTextChanged.connect(window._on_recommend_theme_filter_changed)
    window.recommend_strategy_combo = QComboBox()
    window.recommend_strategy_combo.addItem("全部")
    window.recommend_strategy_combo.currentTextChanged.connect(window._on_recommend_strategy_filter_changed)
    window.recommend_action_combo = QComboBox()
    window.recommend_action_combo.addItems(["全部", "买入", "观察", "持有", "减仓", "离场"])
    window.recommend_action_combo.currentTextChanged.connect(window._on_recommend_action_filter_changed)
    window.recommend_execution_combo = QComboBox()
    window.recommend_execution_combo.addItems(["全部", "待观察", "已送审", "已提交", "提交失败"])
    window.recommend_execution_combo.currentTextChanged.connect(window._on_recommend_execution_filter_changed)

    recommend_to_broker_button = QPushButton("送审选中票")
    plan_to_broker_button = QPushButton("送审计划股")
    focus_pending_button = QPushButton("定位待审")
    retry_failed_button = QPushButton("复核失败")
    push_priority_button = QPushButton("一键送审前排")
    window._set_button_role(recommend_to_broker_button, "accent")
    window._set_button_role(plan_to_broker_button, "tonal")
    window._set_button_role(focus_pending_button, "tonal")
    window._set_button_role(retry_failed_button, "tonal")
    window._set_button_role(push_priority_button, "accent")
    recommend_to_broker_button.setToolTip("送审当前选中的推荐标的。")
    plan_to_broker_button.setToolTip("送审当前计划中的标的。")
    focus_pending_button.setToolTip("定位待送审的高优先级标的。")
    retry_failed_button.setToolTip("复核最近送审失败的标的。")
    push_priority_button.setToolTip("一键送审当前最高优先标的。")
    window.recommend_to_broker_button = recommend_to_broker_button
    window.plan_to_broker_button = plan_to_broker_button
    window.focus_pending_button = focus_pending_button
    window.retry_failed_button = retry_failed_button
    window.push_priority_button = push_priority_button
    recommend_to_broker_button.clicked.connect(window.push_selected_recommendation_to_broker)
    plan_to_broker_button.clicked.connect(window.push_selected_trade_plan_to_broker)
    focus_pending_button.clicked.connect(window.focus_next_pending_recommendation)
    retry_failed_button.clicked.connect(window.review_failed_recommendation)
    push_priority_button.clicked.connect(window.push_priority_recommendation_to_broker)

    controls_splitter = QSplitter(Qt.Horizontal)
    controls_splitter.setObjectName("workspaceControlSplit")
    controls_splitter.setChildrenCollapsible(False)
    data_box = QGroupBox("数据接入")
    filter_box = QGroupBox("主线筛选")
    action_box = QGroupBox("送审动作")
    window._style_terminal_panel(data_box, filter_box, action_box)
    data_box.setObjectName("workspaceToolPanel")
    filter_box.setObjectName("workspaceToolPanel")
    action_box.setObjectName("workspaceToolPanel")

    data_layout = QVBoxLayout(data_box)
    data_grid = QGridLayout()
    data_grid.setHorizontalSpacing(10)
    data_grid.setVerticalSpacing(10)
    for index, button in enumerate(
        [import_profile_button, import_news_button, import_theme_button, edit_theme_button, refresh_button, load_sample_button]
    ):
        button.setMinimumHeight(40)
        data_grid.addWidget(button, index // 3, index % 3)
    data_layout.addLayout(data_grid)
    data_layout.addWidget(window.recommend_status_label)
    data_layout.addWidget(window.recommend_empty_box)

    filter_layout = QGridLayout(filter_box)
    filter_layout.setHorizontalSpacing(12)
    filter_layout.setVerticalSpacing(10)
    filter_layout.addWidget(QLabel("主线筛选"), 0, 0)
    filter_layout.addWidget(window.recommend_theme_combo, 0, 1)
    filter_layout.addWidget(QLabel("策略"), 0, 2)
    filter_layout.addWidget(window.recommend_strategy_combo, 0, 3)
    filter_layout.addWidget(QLabel("动作"), 1, 0)
    filter_layout.addWidget(window.recommend_action_combo, 1, 1)
    filter_layout.addWidget(QLabel("状态"), 1, 2)
    filter_layout.addWidget(window.recommend_execution_combo, 1, 3)

    action_layout = QGridLayout(action_box)
    action_layout.setHorizontalSpacing(10)
    action_layout.setVerticalSpacing(10)
    for index, button in enumerate(
        [recommend_to_broker_button, plan_to_broker_button, focus_pending_button, retry_failed_button, push_priority_button]
    ):
        button.setMinimumHeight(40)
        action_layout.addWidget(button, index // 2, index % 2)

    controls_splitter.addWidget(data_box)
    controls_splitter.addWidget(filter_box)
    controls_splitter.addWidget(action_box)
    window._configure_splitter(controls_splitter, [500, 520, 430])
    layout.addWidget(controls_splitter)

    recommend_focus_cards_box = QGroupBox("当前焦点")
    window._style_terminal_panel(recommend_focus_cards_box)
    recommend_focus_cards_box.setProperty("surfaceRole", "metric-band")
    recommend_focus_cards_layout = QHBoxLayout(recommend_focus_cards_box)
    recommend_focus_cards_layout.setContentsMargins(12, 12, 12, 12)
    recommend_focus_cards_layout.setSpacing(10)
    window.recommend_focus_metric_cards = {}
    window.recommend_focus_metric_labels = {}
    window.recommend_focus_metric_accents = {}
    for key, title, accent in [
        ("symbol", "焦点票", "等待候选"),
        ("theme", "主线", "等待同步"),
        ("action", "动作", "等待生成"),
        ("execution", "状态", "待观察"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.recommend_focus_metric_cards[key] = card
        window.recommend_focus_metric_labels[key] = value_label
        window.recommend_focus_metric_accents[key] = accent_label
        recommend_focus_cards_layout.addWidget(card)
    layout.addWidget(recommend_focus_cards_box)

    dispatch_splitter = QSplitter(Qt.Horizontal)
    window.recommend_dispatch_splitter = dispatch_splitter
    dispatch_splitter.setChildrenCollapsible(False)
    dispatch_box = QGroupBox("盘中分发")
    focus_review_box = QGroupBox("单票审查")
    queue_box = QGroupBox("执行队列")
    window._style_terminal_panel(dispatch_box, focus_review_box, queue_box)
    dispatch_box.setProperty("surfaceRole", "analysis")
    focus_review_box.setProperty("surfaceRole", "analysis")
    queue_box.setProperty("surfaceRole", "analysis")

    dispatch_layout = QVBoxLayout(dispatch_box)
    window.recommend_dispatch_text = QTextEdit()
    window.recommend_dispatch_text.setReadOnly(True)
    window.recommend_dispatch_text.setMinimumHeight(156)
    window.recommend_dispatch_text.setMaximumHeight(188)
    window._style_terminal_console(window.recommend_dispatch_text)
    window.recommend_dispatch_text.setProperty("panelTone", "dispatch")
    window.recommend_dispatch_text.setPlainText("先看单票结论，再扫执行节奏。")
    dispatch_layout.addWidget(window.recommend_dispatch_text)

    focus_review_layout = QVBoxLayout(focus_review_box)
    window.recommend_focus_review_text = QTextEdit()
    window.recommend_focus_review_text.setReadOnly(True)
    window.recommend_focus_review_text.setMinimumHeight(172)
    window.recommend_focus_review_text.setMaximumHeight(204)
    window._style_terminal_console(window.recommend_focus_review_text)
    window.recommend_focus_review_text.setProperty("panelTone", "focus-review")
    window.recommend_focus_review_text.setPlainText("这里只保留价位、风险和复核重点。")
    focus_review_layout.addWidget(window.recommend_focus_review_text)

    queue_layout = QVBoxLayout(queue_box)
    window.recommend_queue_text = QTextEdit()
    window.recommend_queue_text.setReadOnly(True)
    window.recommend_queue_text.setMinimumHeight(156)
    window.recommend_queue_text.setMaximumHeight(188)
    window._style_terminal_console(window.recommend_queue_text)
    window.recommend_queue_text.setProperty("panelTone", "queue")
    window.recommend_queue_text.setPlainText("这里只看待复核、已送审和失败回看。")
    queue_layout.addWidget(window.recommend_queue_text)

    dispatch_splitter.addWidget(dispatch_box)
    dispatch_splitter.addWidget(focus_review_box)
    dispatch_splitter.addWidget(queue_box)
    window._configure_splitter(dispatch_splitter, [340, 460, 300])
    layout.addWidget(dispatch_splitter, stretch=2)

    summary_splitter = QSplitter(Qt.Horizontal)
    window.recommend_summary_splitter = summary_splitter
    summary_splitter.setChildrenCollapsible(False)
    theme_box = QGroupBox("题材热度")
    leader_box = QGroupBox("龙头榜")
    window._style_terminal_panel(theme_box, leader_box)

    theme_layout = QVBoxLayout(theme_box)
    window.theme_heat_table = build_table(["题材", "热度", "延续", "窗口", "分歧", "消息", "龙头数", "排序", "风险"])
    window.theme_heat_table.verticalHeader().setDefaultSectionSize(42)
    window.theme_heat_table.setMinimumHeight(280)
    window.theme_heat_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.theme_heat_table.itemSelectionChanged.connect(window._on_theme_heat_selection_changed)
    theme_layout.addWidget(window.theme_heat_table)

    leader_layout = QVBoxLayout(leader_box)
    window.leader_table = build_table(["名称", "ID", "题材", "级别", "角色", "窗口", "风险", "龙头层级", "动作", "说明"])
    window.leader_table.verticalHeader().setDefaultSectionSize(46)
    window.leader_table.setMinimumHeight(280)
    window.leader_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.leader_table.itemSelectionChanged.connect(window._on_leader_table_selection_changed)
    leader_layout.addWidget(window.leader_table)

    summary_splitter.addWidget(theme_box)
    summary_splitter.addWidget(leader_box)
    window._configure_splitter(summary_splitter, [410, 790])
    layout.addWidget(summary_splitter, stretch=2)

    pool_box = QGroupBox("主线看板")
    window._style_terminal_panel(pool_box)
    pool_layout = QVBoxLayout(pool_box)
    window.daily_pool_focus_label = QLabel(RECOMMEND_DEFAULT_FOCUS_TEXT)
    window.daily_pool_focus_label.setObjectName("focusStateLabel")
    pool_layout.addWidget(window.daily_pool_focus_label)
    window.daily_pool_table = _build_recommend_daily_pool_table(window, build_table)
    pool_layout.addWidget(window.daily_pool_table)
    layout.addWidget(pool_box, stretch=3)

    section_hint = QLabel("推荐成交台只保留 3 个核心动作：选焦点、过门槛、进交易。辅助洞察按需展开。")
    section_hint.setObjectName("inlineHint")
    layout.addWidget(section_hint)

    decision_summary_box = QGroupBox("单票成交卡")
    window._style_terminal_panel(decision_summary_box)
    decision_summary_box.setProperty("surfaceRole", "spotlight")
    decision_summary_layout = QVBoxLayout(decision_summary_box)
    window.recommend_decision_summary_label = QLabel("先选中一只股票，再判断是否具备成交条件、要不要进入送审。")
    window.recommend_decision_summary_label.setObjectName("focusStateLabel")
    window.recommend_decision_summary_label.setWordWrap(True)
    decision_summary_layout.addWidget(window.recommend_decision_summary_label)
    window.recommend_decision_summary_text = QTextEdit()
    window.recommend_decision_summary_text.setReadOnly(True)
    window.recommend_decision_summary_text.setMinimumHeight(188)
    window.recommend_decision_summary_text.setMaximumHeight(236)
    window._style_terminal_console(window.recommend_decision_summary_text)
    window.recommend_decision_summary_text.setProperty("panelTone", "decision")
    window.recommend_decision_summary_text.setPlainText(
        "单票成交卡\n\n"
        "这里会先给出当前结论、送审门槛、关键价位、失效条件和下一步动作。\n"
        "你不需要先翻完所有卡片，再决定是否推进到送审和交易。"
    )
    decision_summary_layout.addWidget(window.recommend_decision_summary_text)
    decision_action_row = QHBoxLayout()
    window.recommend_push_focus_button = QPushButton("进入送审")
    window.recommend_detail_focus_button = QPushButton("查看复盘证据")
    window.recommend_broker_focus_button = QPushButton("打开交易执行")
    _configure_recommend_focus_action(
        window,
        window.recommend_push_focus_button,
        role="accent",
        tooltip="送审当前焦点股票。系统会结合结论、价格计划和风险状态判断是否适合进入送审链路。",
        handler=window.push_selected_recommendation_to_broker,
    )
    _configure_recommend_focus_action(
        window,
        window.recommend_detail_focus_button,
        role="ghost",
        tooltip="跳到复盘页，继续查看信号、执行回放、失效条件和近期消息。",
        handler=window.open_selected_recommend_in_detail,
    )
    _configure_recommend_focus_action(
        window,
        window.recommend_broker_focus_button,
        role="tonal",
        tooltip="跳到交易页，查看这只股票对应的交易计划、委托建议和回执链路。",
        handler=window.open_selected_recommend_in_broker,
    )
    decision_action_row.addWidget(window.recommend_push_focus_button)
    decision_action_row.addWidget(window.recommend_detail_focus_button)
    decision_action_row.addWidget(window.recommend_broker_focus_button)
    decision_action_row.addStretch(1)
    decision_summary_layout.addLayout(decision_action_row)
    layout.addWidget(decision_summary_box)

    stage_control_row = QHBoxLayout()
    window.recommend_stage_toggle_button = QPushButton("展开辅助洞察")
    window._set_button_role(window.recommend_stage_toggle_button, "ghost")
    window.recommend_stage_toggle_button.setToolTip("展开后会看到战法、观察池、复盘与次日预案；折叠时只保留成交决策核心区块。")
    window.recommend_stage_toggle_button.clicked.connect(window.toggle_recommend_auxiliary_stage)
    window.recommend_stage_status_label = QLabel("辅助洞察已折叠，当前只保留成交决策所需核心区块。")
    window.recommend_stage_status_label.setObjectName("inlineHint")
    window.recommend_stage_status_label.setWordWrap(True)
    window.recommend_stage_status_label.setToolTip("这里会说明当前为什么建议展开或保持折叠，帮助你把注意力放在更接近成交的区块。")
    stage_control_row.addWidget(window.recommend_stage_toggle_button)
    stage_control_row.addWidget(window.recommend_stage_status_label, stretch=1)
    layout.addLayout(stage_control_row)

    window.recommend_stage_container = QWidget()
    recommend_stage_layout = QVBoxLayout(window.recommend_stage_container)
    recommend_stage_layout.setContentsMargins(0, 0, 0, 0)
    recommend_stage_layout.setSpacing(14)
    execution_stage = QWidget()
    decision_stage = QWidget()
    recap_stage = QWidget()
    recommend_stage_layout.addWidget(execution_stage, stretch=3)
    recommend_stage_layout.addWidget(decision_stage, stretch=3)
    recommend_stage_layout.addWidget(recap_stage, stretch=4)
    layout.addWidget(window.recommend_stage_container, stretch=4)
    window.recommend_stage_container.hide()

    execution_layout = QVBoxLayout(execution_stage)
    execution_layout.setContentsMargins(0, 8, 0, 0)
    execution_layout.setSpacing(14)
    execution_hint = QLabel("执行区：先看高优先池、观察池和风险池。")
    execution_hint.setObjectName("inlineHint")
    execution_layout.addWidget(execution_hint)
    decision_layout = QVBoxLayout(decision_stage)
    decision_layout.setContentsMargins(0, 8, 0, 0)
    decision_layout.setSpacing(14)
    decision_hint = QLabel("策略区：看战法解释、优先级、盘中提醒和主线推演。")
    decision_hint.setObjectName("inlineHint")
    decision_layout.addWidget(decision_hint)
    recap_layout = QVBoxLayout(recap_stage)
    recap_layout.setContentsMargins(0, 8, 0, 0)
    recap_layout.setSpacing(14)
    recap_hint = QLabel("复盘区：看计划、持仓处理建议、当日复盘和次日预案。")
    recap_hint.setObjectName("inlineHint")
    recap_layout.addWidget(recap_hint)

    bucket_action_row = QHBoxLayout()
    core_bucket_button = QPushButton("只看高优先池")
    watch_bucket_button = QPushButton("只看观察池")
    risk_bucket_button = QPushButton("只看风险池")
    window._set_button_role(core_bucket_button, "accent")
    window._set_button_role(watch_bucket_button, "tonal")
    window._set_button_role(risk_bucket_button, "tonal")
    core_bucket_button.clicked.connect(window.show_core_execution_bucket)
    watch_bucket_button.clicked.connect(window.show_watch_bucket)
    risk_bucket_button.clicked.connect(window.show_risk_bucket)
    bucket_action_row.addWidget(core_bucket_button)
    bucket_action_row.addWidget(watch_bucket_button)
    bucket_action_row.addWidget(risk_bucket_button)
    bucket_action_row.addStretch(1)
    execution_layout.addLayout(bucket_action_row)

    bucket_splitter = QSplitter(Qt.Horizontal)
    bucket_splitter.setChildrenCollapsible(False)
    core_bucket_box = QGroupBox("高优先池")
    watch_bucket_box = QGroupBox("观察池")
    risk_bucket_box = QGroupBox("风险池")
    window._style_terminal_panel(core_bucket_box, watch_bucket_box, risk_bucket_box)
    core_bucket_box.setProperty("surfaceRole", "analysis")
    watch_bucket_box.setProperty("surfaceRole", "analysis")
    risk_bucket_box.setProperty("surfaceRole", "analysis")

    core_bucket_layout = QVBoxLayout(core_bucket_box)
    window.recommend_core_bucket_text = QTextEdit()
    window.recommend_core_bucket_text.setReadOnly(True)
    window.recommend_core_bucket_text.setMinimumHeight(168)
    window.recommend_core_bucket_text.setMaximumHeight(220)
    window._style_terminal_console(window.recommend_core_bucket_text)
    window.recommend_core_bucket_text.setProperty("panelTone", "buy")
    window.recommend_core_bucket_text.setPlainText("继续跟。先执行。")
    core_bucket_layout.addWidget(window.recommend_core_bucket_text)

    watch_bucket_layout = QVBoxLayout(watch_bucket_box)
    window.recommend_watch_bucket_text = QTextEdit()
    window.recommend_watch_bucket_text.setReadOnly(True)
    window.recommend_watch_bucket_text.setMinimumHeight(168)
    window.recommend_watch_bucket_text.setMaximumHeight(220)
    window._style_terminal_console(window.recommend_watch_bucket_text)
    window.recommend_watch_bucket_text.setProperty("panelTone", "watch")
    window.recommend_watch_bucket_text.setPlainText("只观察。先盯信号。")
    watch_bucket_layout.addWidget(window.recommend_watch_bucket_text)

    risk_bucket_layout = QVBoxLayout(risk_bucket_box)
    window.recommend_risk_bucket_text = QTextEdit()
    window.recommend_risk_bucket_text.setReadOnly(True)
    window.recommend_risk_bucket_text.setMinimumHeight(168)
    window.recommend_risk_bucket_text.setMaximumHeight(220)
    window._style_terminal_console(window.recommend_risk_bucket_text)
    window.recommend_risk_bucket_text.setProperty("panelTone", "risk")
    window.recommend_risk_bucket_text.setPlainText("防切换。先管风险。")
    risk_bucket_layout.addWidget(window.recommend_risk_bucket_text)

    bucket_splitter.addWidget(core_bucket_box)
    bucket_splitter.addWidget(watch_bucket_box)
    bucket_splitter.addWidget(risk_bucket_box)
    window._configure_splitter(bucket_splitter, [420, 420, 420])
    execution_layout.addWidget(bucket_splitter, stretch=2)

    strategy_pack_box = QGroupBox("战法工作台")
    window._style_terminal_panel(strategy_pack_box)
    strategy_pack_layout = QGridLayout(strategy_pack_box)
    strategy_pack_layout.setContentsMargins(12, 12, 12, 12)
    strategy_pack_layout.setHorizontalSpacing(10)
    strategy_pack_layout.setVerticalSpacing(10)
    window.strategy_pack_cards = {}
    for index, (title, subtitle) in enumerate(strategy_workbench_specs):
        card = strategy_workbench_card_cls(title, subtitle)
        window.strategy_pack_cards[title] = card
        strategy_pack_layout.addWidget(card, index // 3, index % 3)
    decision_layout.addWidget(strategy_pack_box, stretch=2)

    strategy_detail_box = QGroupBox("战法明细")
    window._style_terminal_panel(strategy_detail_box)
    strategy_detail_layout = QVBoxLayout(strategy_detail_box)
    strategy_detail_header = QHBoxLayout()
    window.strategy_detail_combo = QComboBox()
    for name in strategy_score_fields:
        window.strategy_detail_combo.addItem(name)
    window.strategy_detail_combo.currentTextChanged.connect(window._refresh_strategy_focus_detail)
    strategy_detail_header.addWidget(QLabel("当前战法"))
    strategy_detail_header.addWidget(window.strategy_detail_combo)
    strategy_detail_header.addStretch(1)
    strategy_detail_layout.addLayout(strategy_detail_header)
    window.strategy_detail_text = QTextEdit()
    window.strategy_detail_text.setReadOnly(True)
    window.strategy_detail_text.setMinimumHeight(220)
    window._style_terminal_console(window.strategy_detail_text)
    window.strategy_detail_text.setPlainText("等待推荐池。")
    strategy_detail_layout.addWidget(window.strategy_detail_text)
    decision_layout.addWidget(strategy_detail_box, stretch=1)

    action_flow_box = QGroupBox("决策流程")
    window._style_terminal_panel(action_flow_box)
    action_flow_layout = QHBoxLayout(action_flow_box)
    action_flow_layout.setContentsMargins(12, 12, 12, 12)
    action_flow_layout.setSpacing(10)
    window.action_flow_cards = {
        "BUY": action_flow_card_cls("买入", "#25d07f"),
        "WATCH": action_flow_card_cls("观察", "#f7d354"),
        "REDUCE": action_flow_card_cls("减仓", "#ff9f43"),
        "SELL": action_flow_card_cls("离场", "#ff5e57"),
    }
    for key in ["BUY", "WATCH", "REDUCE", "SELL"]:
        action_flow_layout.addWidget(window.action_flow_cards[key])
    decision_layout.addWidget(action_flow_box, stretch=1)

    priority_box = QGroupBox("优先级")
    window._style_terminal_panel(priority_box)
    priority_layout = QHBoxLayout(priority_box)
    priority_layout.setContentsMargins(12, 12, 12, 12)
    priority_layout.setSpacing(10)
    window.priority_cards = {
        "market": action_flow_card_cls("市场情绪", "#4fc3f7"),
        "theme": action_flow_card_cls("主线题材", "#c792ea"),
        "strategy": action_flow_card_cls("高优先策略", "#ffd166"),
        "focus": action_flow_card_cls("一号标的", "#25d07f"),
    }
    for key in ["market", "theme", "strategy", "focus"]:
        priority_layout.addWidget(window.priority_cards[key])
    decision_layout.addWidget(priority_box, stretch=1)

    alert_box = QGroupBox("盘中提醒")
    window._style_terminal_panel(alert_box)
    alert_layout = QHBoxLayout(alert_box)
    alert_layout.setContentsMargins(12, 12, 12, 12)
    alert_layout.setSpacing(10)
    window.alert_cards = {
        "theme": alert_signal_card_cls("主线切换", "#c792ea"),
        "leader": alert_signal_card_cls("龙头切换", "#25d07f"),
        "strategy": alert_signal_card_cls("策略切换", "#ffd166"),
        "action": alert_signal_card_cls("动作切换", "#ff9f43"),
    }
    for key in ["theme", "leader", "strategy", "action"]:
        alert_layout.addWidget(window.alert_cards[key])
    decision_layout.addWidget(alert_box, stretch=1)

    strategy_path_box = QGroupBox("主线推演")
    window._style_terminal_panel(strategy_path_box)
    strategy_path_layout = QVBoxLayout(strategy_path_box)
    window.strategy_path_text = QTextEdit()
    window.strategy_path_text.setReadOnly(True)
    window.strategy_path_text.setMinimumHeight(156)
    window.strategy_path_text.setMaximumHeight(210)
    window._style_terminal_console(window.strategy_path_text)
    window.strategy_path_text.setPlainText("等待推荐池。")
    strategy_path_layout.addWidget(window.strategy_path_text)
    decision_layout.addWidget(strategy_path_box, stretch=1)

    summary_cards_box = QGroupBox("决策摘要")
    window._style_terminal_panel(summary_cards_box)
    summary_cards_layout = QHBoxLayout(summary_cards_box)
    summary_cards_layout.setContentsMargins(12, 12, 12, 12)
    summary_cards_layout.setSpacing(10)
    window.recommend_summary_cards = {
        "logic": compact_summary_card_cls("主线逻辑", "#7ed7ff"),
        "plan": compact_summary_card_cls("今日交易计划", "#25d07f"),
        "pulse": compact_summary_card_cls("市场温度", "#ffd166"),
        "holding": compact_summary_card_cls("持仓处理建议", "#ff9f43"),
    }
    for key in ["logic", "plan", "pulse", "holding"]:
        summary_cards_layout.addWidget(window.recommend_summary_cards[key])
    recap_layout.addWidget(summary_cards_box, stretch=1)

    detail_box = QGroupBox("主线说明")
    plan_box = QGroupBox("今日交易计划")
    pulse_box = QGroupBox("市场温度")
    holding_box = QGroupBox("持仓处理建议")
    window._style_terminal_panel(detail_box, plan_box, pulse_box, holding_box)

    detail_layout = QVBoxLayout(detail_box)
    window.daily_pool_text = QTextEdit()
    window.daily_pool_text.setReadOnly(True)
    window.daily_pool_text.setMinimumHeight(210)
    window.daily_pool_text.setMaximumHeight(260)
    window._style_terminal_console(window.daily_pool_text)
    window.daily_pool_text.setPlainText(
        "说明：\n"
        "- 主线：先看最强方向。\n"
        "- 位次：优先看前排。\n"
        "- 窗口：只看修复和加速。\n"
        "- 风险：转弱、退潮、假突破会降权。\n"
        "- 催化：更偏向能持续的消息与龙头企业。"
    )
    detail_layout.addWidget(window.daily_pool_text)

    plan_layout = QVBoxLayout(plan_box)
    window.trade_plan_focus_label = QLabel("计划焦点：等待生成或选中")
    window.trade_plan_focus_label.setObjectName("focusStateLabel")
    plan_layout.addWidget(window.trade_plan_focus_label)
    window.trade_plan_table = build_table(
        ["状态", "名称", "ID", "代码", "动作", "主线", "角色", "窗口", "风险", "置信", "买点", "止损", "目标", "资金", "说明"]
    )
    window.trade_plan_table.setMinimumHeight(300)
    window.trade_plan_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.trade_plan_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.trade_plan_table.setObjectName("tradePlanTable")
    window.trade_plan_table.itemSelectionChanged.connect(window._on_trade_plan_selection_changed)
    plan_layout.addWidget(window.trade_plan_table)
    window.trade_plan_empty_hint = QLabel("当前还没有可执行的今日交易计划。")
    window.trade_plan_empty_hint.setObjectName("emptyStateMeta")
    window.trade_plan_empty_hint.setWordWrap(True)
    window.trade_plan_empty_hint.hide()
    plan_layout.addWidget(window.trade_plan_empty_hint)

    window.trade_plan_empty_actions = QFrame()
    window.trade_plan_empty_actions.setObjectName("emptyActionBar")
    empty_actions_layout = QHBoxLayout(window.trade_plan_empty_actions)
    empty_actions_layout.setContentsMargins(10, 8, 10, 8)
    empty_actions_layout.setSpacing(8)
    refresh_empty_button = QPushButton("重算计划")
    watch_empty_button = QPushButton("看观察池")
    broker_empty_button = QPushButton("去交易页")
    window._set_button_role(refresh_empty_button, "accent")
    window._set_button_role(watch_empty_button, "tonal")
    window._set_button_role(broker_empty_button, "ghost")
    refresh_empty_button.clicked.connect(window.trigger_trade_plan_refresh)
    watch_empty_button.clicked.connect(window.open_trade_plan_watch_bucket)
    broker_empty_button.clicked.connect(window.open_trade_plan_broker_workspace)
    empty_actions_layout.addWidget(refresh_empty_button)
    empty_actions_layout.addWidget(watch_empty_button)
    empty_actions_layout.addWidget(broker_empty_button)
    empty_actions_layout.addStretch(1)
    window.trade_plan_empty_actions.hide()
    plan_layout.addWidget(window.trade_plan_empty_actions)

    window.trade_plan_text = QTextEdit()
    window.trade_plan_text.setReadOnly(True)
    window.trade_plan_text.setMinimumHeight(150)
    window.trade_plan_text.setMaximumHeight(198)
    window._style_terminal_console(window.trade_plan_text)
    window.trade_plan_text.setPlainText("先刷新主线，再生成今日交易计划。")
    plan_layout.addWidget(window.trade_plan_text)

    pulse_layout = QVBoxLayout(pulse_box)
    window.market_pulse_text = QTextEdit()
    window.market_pulse_text.setReadOnly(True)
    window.market_pulse_text.setMinimumHeight(168)
    window.market_pulse_text.setMaximumHeight(210)
    window._style_terminal_console(window.market_pulse_text)
    window.market_pulse_text.setPlainText("等待推荐池生成后，再更新市场温度和仓位建议。")
    pulse_layout.addWidget(window.market_pulse_text)

    holding_layout = QVBoxLayout(holding_box)
    window.position_advice_table = build_table(
        ["名称", "ID", "交易码", "动作", "主线", "置信度", "现价", "成本", "盈亏", "处理"]
    )
    window.position_advice_table.setMinimumHeight(280)
    window.position_advice_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.position_advice_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.position_advice_table.itemSelectionChanged.connect(window._on_position_advice_selection_changed)
    holding_layout.addWidget(window.position_advice_table)
    window.position_advice_text = QTextEdit()
    window.position_advice_text.setReadOnly(True)
    window.position_advice_text.setMinimumHeight(160)
    window.position_advice_text.setMaximumHeight(210)
    window._style_terminal_console(window.position_advice_text)
    window.position_advice_text.setPlainText("导入持仓后，这里会给出继续持有、减仓、退出或观察建议。")
    holding_layout.addWidget(window.position_advice_text)

    middle = QSplitter(Qt.Horizontal)
    window.recommend_recap_middle_splitter = middle
    middle.setChildrenCollapsible(False)
    middle.addWidget(detail_box)
    middle.addWidget(plan_box)
    window._configure_splitter(middle, [350, 890])
    recap_layout.addWidget(middle, stretch=2)

    bottom = QSplitter(Qt.Horizontal)
    window.recommend_recap_bottom_splitter = bottom
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(pulse_box)
    bottom.addWidget(holding_box)
    window._configure_splitter(bottom, [340, 900])
    recap_layout.addWidget(bottom, stretch=2)

    recommend_review_splitter = QSplitter(Qt.Horizontal)
    window.recommend_review_splitter = recommend_review_splitter
    recommend_review_splitter.setChildrenCollapsible(False)
    recommend_review_box = QGroupBox("当日复盘")
    recommend_next_day_box = QGroupBox("次日策略")
    window._style_terminal_panel(recommend_review_box, recommend_next_day_box)

    recommend_review_layout = QVBoxLayout(recommend_review_box)
    window.recommend_review_text = QTextEdit()
    window.recommend_review_text.setReadOnly(True)
    window.recommend_review_text.setMinimumHeight(190)
    window.recommend_review_text.setMaximumHeight(240)
    window._style_terminal_console(window.recommend_review_text)
    window.recommend_review_text.setPlainText("复盘先看继续跟、只观察还是防切换。")
    recommend_review_layout.addWidget(window.recommend_review_text)

    recommend_next_day_layout = QVBoxLayout(recommend_next_day_box)
    window.recommend_next_day_text = QTextEdit()
    window.recommend_next_day_text.setReadOnly(True)
    window.recommend_next_day_text.setMinimumHeight(190)
    window.recommend_next_day_text.setMaximumHeight(240)
    window._style_terminal_console(window.recommend_next_day_text)
    window.recommend_next_day_text.setPlainText("次日先看继续跟、只观察还是防切换。")
    recommend_next_day_layout.addWidget(window.recommend_next_day_text)

    recommend_review_splitter.addWidget(recommend_review_box)
    recommend_review_splitter.addWidget(recommend_next_day_box)
    window._configure_splitter(recommend_review_splitter, [660, 580])
    recap_layout.addWidget(recommend_review_splitter, stretch=2)

def build_board_workspace(window, build_table, header_view_cls) -> None:
    layout = QVBoxLayout(window.board_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.board_tab.setObjectName("boardRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "打板专项",
            "高弹性擒龙打板、回封确认与炸板风险联动",
            "把擒龙打板候选、回封观察、炸板风险和收盘复盘统一到一个页面里，作为专项策略工具使用。",
            [("Top 5", "打板候选"), ("15:05", "自动复盘")],
        )
    )

    tool_panel = QGroupBox("打板专项面板")
    tool_panel.setObjectName("workspaceToolPanel")
    tool_layout = QGridLayout(tool_panel)
    tool_layout.setContentsMargins(14, 12, 14, 12)
    tool_layout.setHorizontalSpacing(16)
    tool_layout.setVerticalSpacing(10)

    control_row = QHBoxLayout()
    control_row.setSpacing(8)
    refresh_button = QPushButton("刷新打板池")
    plan_export_button = QPushButton("导出盘前交易计划")
    export_button = QPushButton("导出收盘复盘日报")
    window.auto_review_export_checkbox = QCheckBox("15:05 后自动导出复盘日报")
    window.auto_review_export_checkbox.setChecked(True)
    window._set_button_role(refresh_button, "accent")
    window._set_button_role(plan_export_button, "ghost")
    window._set_button_role(export_button)
    refresh_button.clicked.connect(window._refresh_board_mode)
    plan_export_button.clicked.connect(window.export_daily_trade_plan_from_ui)
    export_button.clicked.connect(window.export_end_of_day_review_from_ui)
    control_row.addWidget(refresh_button)
    control_row.addWidget(plan_export_button)
    control_row.addWidget(export_button)
    control_row.addWidget(window.auto_review_export_checkbox)
    control_row.addStretch(1)
    tool_layout.addLayout(control_row, 0, 0)

    board_hint = QLabel("围绕高辨识度强势股，统一查看专项候选、回封监控、导出计划和收盘复盘。")
    board_hint.setObjectName("inlineHint")
    board_hint.setWordWrap(True)
    board_meta = QFrame()
    board_meta.setProperty("actionRow", True)
    board_meta_layout = QVBoxLayout(board_meta)
    board_meta_layout.setContentsMargins(12, 10, 12, 10)
    board_meta_layout.setSpacing(6)
    board_meta_layout.addWidget(QLabel("联动说明：候选、监控和复盘会围绕同一只股票同步切换。"))
    board_meta_layout.addWidget(board_hint)
    tool_layout.addWidget(board_meta, 0, 1)
    tool_layout.setColumnStretch(0, 3)
    tool_layout.setColumnStretch(1, 2)
    layout.addWidget(tool_panel)

    candidate_box = QGroupBox("打板候选池")
    monitor_box = QGroupBox("炸板 / 回封监控")
    window._style_terminal_panel(candidate_box, monitor_box)

    candidate_layout = QVBoxLayout(candidate_box)
    window.board_table = build_table(
        ["股票名称", "股票ID", "交易代码", "打板级别", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"]
    )
    window.board_table.horizontalHeader().setSectionResizeMode(header_view_cls.Stretch)
    candidate_layout.addWidget(window.board_table)
    window.board_text = QTextEdit()
    window.board_text.setReadOnly(True)
    window._style_terminal_console(window.board_text)
    window.board_text.setPlainText("先生成每日推荐池，再生成打板候选。")
    candidate_layout.addWidget(window.board_text)
    layout.addWidget(candidate_box, stretch=1)

    monitor_layout = QVBoxLayout(monitor_box)
    window.board_monitor_table = build_table(
        ["股票名称", "股票ID", "交易代码", "监控状态", "强度", "连续性", "回封概率", "炸板风险", "动作建议", "备注"]
    )
    window.board_monitor_table.horizontalHeader().setSectionResizeMode(header_view_cls.Stretch)
    monitor_layout.addWidget(window.board_monitor_table)
    window.board_monitor_text = QTextEdit()
    window.board_monitor_text.setReadOnly(True)
    window._style_terminal_console(window.board_monitor_text)
    window.board_monitor_text.setPlainText("专项监控会显示回封观察、炸板风险和强势连板候选。")
    monitor_layout.addWidget(window.board_monitor_text)
    layout.addWidget(monitor_box, stretch=1)

def build_config_workspace(window) -> None:
    layout = QVBoxLayout(window.config_tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    window.config_tab.setObjectName("configRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "策略配置 / 商业化",
            "策略参数与授权状态",
            "集中管理主线阈值、题材权重、盘前模板和版本能力边界。",
            [("策略", "主线优先"), ("授权", window.state.license_plan or "TRIAL")],
        )
    )

    top = QSplitter(Qt.Horizontal)
    top.setChildrenCollapsible(False)

    strategy_box = QGroupBox("策略参数")
    window._style_terminal_panel(strategy_box)
    strategy_layout = QFormLayout(strategy_box)
    strategy_layout.setLabelAlignment(Qt.AlignRight)

    window.config_inputs["top_theme_limit"] = QLineEdit(str(window.state.strategy_top_theme_limit))
    window.config_inputs["max_total_exposure"] = QLineEdit(str(window.state.strategy_max_total_exposure))
    window.config_inputs["daily_plan_candidate_limit"] = QLineEdit(str(window.state.daily_plan_candidate_limit))
    window.focus_themes_input = QLineEdit(", ".join(window.state.focus_themes))
    window.strategy_risk_profile_combo = QComboBox()
    for key in ["conservative", "standard", "aggressive"]:
        window.strategy_risk_profile_combo.addItem(RISK_PROFILE_LABELS.get(key, key), key)
    for index in range(window.strategy_risk_profile_combo.count()):
        if window.strategy_risk_profile_combo.itemData(index) == window.state.strategy_risk_profile:
            window.strategy_risk_profile_combo.setCurrentIndex(index)
            break
    window.theme_drop_reduce_checkbox = QCheckBox("题材掉队时优先减仓")
    window.theme_drop_reduce_checkbox.setChecked(window.state.strategy_theme_drop_reduce)
    window.auto_daily_plan_export_checkbox = QCheckBox("启用自动盘前报告")
    window.auto_daily_plan_export_checkbox.setChecked(window.state.auto_daily_plan_export)
    window.daily_plan_focus_only_checkbox = QCheckBox("仅输出关注题材")
    window.daily_plan_focus_only_checkbox.setChecked(window.state.daily_plan_focus_only)
    window.daily_plan_template_combo = QComboBox()
    for key, label in [
        ("balanced", "均衡模板"),
        ("focus", "关注题材"),
        ("mainline", "主线优先"),
        ("compact", "紧凑模板"),
    ]:
        window.daily_plan_template_combo.addItem(label, key)
    for index in range(window.daily_plan_template_combo.count()):
        if window.daily_plan_template_combo.itemData(index) == window.state.daily_plan_template:
            window.daily_plan_template_combo.setCurrentIndex(index)
            break

    strategy_layout.addRow("主线前排 N", window.config_inputs["top_theme_limit"])
    strategy_layout.addRow("风险档位", window.strategy_risk_profile_combo)
    strategy_layout.addRow("总仓位上限", window.config_inputs["max_total_exposure"])
    strategy_layout.addRow("盘前候选上限", window.config_inputs["daily_plan_candidate_limit"])
    strategy_layout.addRow("关注题材", window.focus_themes_input)
    strategy_layout.addRow("盘前模板", window.daily_plan_template_combo)
    strategy_layout.addRow("", window.daily_plan_focus_only_checkbox)
    strategy_layout.addRow("", window.theme_drop_reduce_checkbox)
    strategy_layout.addRow("", window.auto_daily_plan_export_checkbox)
    top.addWidget(strategy_box)

    license_box = QGroupBox("授权与状态")
    window._style_terminal_panel(license_box)
    license_layout = QVBoxLayout(license_box)
    window.license_status_text = QTextEdit()
    window.license_status_text.setReadOnly(True)
    window._style_terminal_console(window.license_status_text)
    license_layout.addWidget(window.license_status_text)

    license_buttons = QGridLayout()
    license_buttons.setHorizontalSpacing(10)
    license_buttons.setVerticalSpacing(10)
    trial_button = QPushButton("切换试用版")
    pro_button = QPushButton("切换专业版")
    enterprise_button = QPushButton("切换企业版")
    save_button = QPushButton("保存当前配置")
    window._set_button_role(trial_button)
    window._set_button_role(pro_button)
    window._set_button_role(enterprise_button)
    window._set_button_role(save_button, "accent")
    trial_button.clicked.connect(window.reset_trial_plan)
    pro_button.clicked.connect(window.activate_professional_plan)
    enterprise_button.clicked.connect(window.activate_enterprise_plan)
    save_button.clicked.connect(window.save_strategy_preferences)
    for button, row, column in [
        (trial_button, 0, 0),
        (pro_button, 0, 1),
        (enterprise_button, 1, 0),
        (save_button, 1, 1),
    ]:
        license_buttons.addWidget(button, row, column)
    license_layout.addLayout(license_buttons)
    top.addWidget(license_box)

    window._configure_splitter(top, [620, 620])
    layout.addWidget(top, stretch=2)

    notes_box = QGroupBox("说明")
    window._style_terminal_panel(notes_box)
    notes_layout = QVBoxLayout(notes_box)
    window.config_notes_text = QTextEdit()
    window.config_notes_text.setReadOnly(True)
    window._style_terminal_console(window.config_notes_text)
    window.config_notes_text.setPlainText(
        "配置说明\n\n"
        "- 当前配置会直接影响每日推荐、盘前计划、盘中监控和版本能力边界。\n"
        "- 主线阈值越高，开仓越偏向龙头和前排。\n"
        "- 关注题材会影响排序、报告和提醒。\n"
        "- 自动盘前报告会在刷新后同步生成。"
    )
    notes_layout.addWidget(window.config_notes_text)
    layout.addWidget(notes_box, stretch=1)

    window._refresh_license_status_view()
