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
    QSizePolicy,
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
from quant_hunter.risk import (
    RISK_PROFILE_AGGRESSIVE,
    RISK_PROFILE_CONSERVATIVE,
    RISK_PROFILE_LABELS,
    RISK_PROFILE_STANDARD,
    risk_profile_brief,
    risk_profile_snapshot_card_state,
    risk_profile_snapshot_text,
)
from quant_hunter.ui_helpers import AdaptivePanelGrid


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


def _configure_recommend_story_text(window, widget: QTextEdit, *, tone: str, min_height: int, max_height: int, seed_text: str) -> None:
    widget.setReadOnly(True)
    widget.setObjectName("marketNotePanel")
    widget.setMinimumHeight(min_height)
    widget.setMaximumHeight(max_height)
    widget.setLineWrapMode(QTextEdit.WidgetWidth)
    widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    widget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    window._style_terminal_console(widget)
    widget.setProperty("panelTone", tone)
    widget.setProperty("pageTone", "recommend")
    widget.setPlainText(seed_text)


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
    form_box.setObjectName("workspaceToolPanel")
    form_box.setProperty("pageTone", "auth")
    form_grid = QGridLayout(form_box)
    profile = window.state.broker_profile

    form_grid.addWidget(QLabel("接入通道"), 0, 0)
    window.auth_channel_combo = QComboBox()
    window.auth_channel_combo.setMinimumHeight(40)
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
        ("account_name", "账户名称", profile.account_name or "东方财富账户"),
        ("username", "登录账号", profile.username),
        ("password", "登录密码", profile.password),
        ("token", "SDK Token", profile.token),
        ("account_id", "账户 ID", profile.account_id),
        ("strategy_id", "策略 ID", profile.strategy_id),
        ("sdk_module", "SDK 模块", profile.sdk_module or "gm.api"),
        ("sdk_python_path", "Bridge Python", profile.sdk_python_path),
    ]
    for index, (key, label, value) in enumerate(login_fields, start=1):
        form_grid.addWidget(QLabel(label), index, 0)
        widget = QLineEdit(value)
        widget.setMinimumHeight(38)
        if key == "password":
            widget.setEchoMode(QLineEdit.Password)
        if key == "sdk_python_path":
            widget.setPlaceholderText("例如：C:\\Users\\18335\\AppData\\Local\\Programs\\Python\\Python312\\python.exe")
        elif key == "sdk_module":
            widget.setPlaceholderText("例如：gm.api")
        window.login_inputs[key] = widget
        form_grid.addWidget(widget, index, 1)
        widget.textChanged.connect(lambda *_args: window._refresh_login_status())

    window.auth_channel_combo.currentIndexChanged.connect(lambda *_args: window._refresh_login_status())

    auth_hint = QLabel("GM / 自定义通道建议在这里同时补齐 SDK 模块与 Bridge Python，再做接入校验。")
    auth_hint.setObjectName("inlineHint")
    auth_hint.setWordWrap(True)
    form_grid.addWidget(auth_hint, len(login_fields) + 1, 0, 1, 2)

    action_row = QHBoxLayout()
    action_row.setSpacing(8)
    save_button = QPushButton("保存登录信息")
    validate_button = QPushButton("校验接入")
    broker_button = QPushButton("前往交易执行")
    recommend_button = QPushButton("前往推荐池")
    window._set_button_role(save_button, "accent")
    window._set_button_role(validate_button, "tonal")
    window._set_button_role(broker_button, "ghost")
    window._set_button_role(recommend_button, "ghost")
    save_button.setMinimumHeight(40)
    validate_button.setMinimumHeight(40)
    broker_button.setMinimumHeight(40)
    recommend_button.setMinimumHeight(40)
    save_button.clicked.connect(window.save_login_profile)
    validate_button.clicked.connect(window.validate_login_connection)
    broker_button.clicked.connect(lambda: window._navigate_to_workspace("broker", "orders_table"))
    recommend_button.clicked.connect(lambda: window._navigate_to_workspace("recommend", "daily_pool_table"))
    action_row.addWidget(save_button)
    action_row.addWidget(validate_button)
    action_row.addWidget(broker_button)
    action_row.addWidget(recommend_button)
    action_row.addStretch(1)
    form_grid.addLayout(action_row, len(login_fields) + 2, 0, 1, 2)
    layout.addWidget(form_box)

    status_box = QGroupBox("连接状态")
    window._style_terminal_panel(status_box)
    status_box.setProperty("pageTone", "auth")
    status_layout = QVBoxLayout(status_box)
    window.login_status_text = QTextEdit()
    window.login_status_text.setReadOnly(True)
    window._style_terminal_console(window.login_status_text)
    window.login_status_text.setProperty("pageTone", "auth")
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
    compare_history_button = QPushButton("战法参数对比")
    export_history_button = QPushButton("导出历史战法")
    history_button = QPushButton("历史战法统计")
    load_button = QPushButton("导入单票 CSV")
    backtest_button = QPushButton("回测当前标的")
    window._set_button_role(load_button)
    window._set_button_role(backtest_button, "accent")
    window._set_button_role(history_button, "tonal")
    window._set_button_role(compare_history_button, "tonal")
    window._set_button_role(export_history_button, "ghost")
    window.active_symbol_label = QLabel("当前标的：未选择")
    window.active_symbol_label.setObjectName("inlineHint")
    load_button.clicked.connect(window.load_single_csv)
    backtest_button.clicked.connect(window.run_backtest_for_active)
    history_button.clicked.connect(window.run_strategy_history_backtest)
    compare_history_button.clicked.connect(window.run_strategy_history_parameter_compare)
    export_history_button.clicked.connect(window.export_strategy_history_report_from_ui)
    controls.addWidget(load_button)
    controls.addWidget(backtest_button)
    controls.addWidget(history_button)
    controls.addWidget(compare_history_button)
    controls.addWidget(export_history_button)
    controls.addWidget(window.active_symbol_label)
    controls.addStretch(1)
    tool_layout.addLayout(controls, 0, 0)

    strategy_history_controls = QHBoxLayout()
    strategy_history_controls.setSpacing(8)
    strategy_history_label = QLabel("战法回测参数")
    strategy_history_label.setObjectName("inlineHint")
    window.strategy_history_start_input = QLineEdit("2021-01-01")
    window.strategy_history_start_input.setMinimumHeight(36)
    window.strategy_history_start_input.setPlaceholderText("起始日期 YYYY-MM-DD")
    window.strategy_history_end_input = QLineEdit("2099-12-31")
    window.strategy_history_end_input.setMinimumHeight(36)
    window.strategy_history_end_input.setPlaceholderText("结束日期 YYYY-MM-DD")
    window.strategy_history_max_hold_input = QLineEdit("8")
    window.strategy_history_max_hold_input.setMinimumHeight(36)
    window.strategy_history_slippage_input = QLineEdit("0.0005")
    window.strategy_history_slippage_input.setMinimumHeight(36)
    window.strategy_history_slippage_input.setPlaceholderText("滑点")
    window.strategy_history_commission_input = QLineEdit("0.0003")
    window.strategy_history_commission_input.setMinimumHeight(36)
    window.strategy_history_commission_input.setPlaceholderText("手续费")
    window.strategy_history_stamp_duty_input = QLineEdit("0.001")
    window.strategy_history_stamp_duty_input.setMinimumHeight(36)
    window.strategy_history_stamp_duty_input.setPlaceholderText("印花税")
    window.strategy_history_max_hold_input.setPlaceholderText("最长持有天数")
    window.strategy_history_include_watch_checkbox = QCheckBox("纳入观察信号")
    window.strategy_history_include_watch_checkbox.setChecked(False)
    window.strategy_history_limit_up_checkbox = QCheckBox("涨停日买不进")
    window.strategy_history_limit_up_checkbox.setChecked(True)
    window.strategy_history_limit_down_checkbox = QCheckBox("跌停日卖不出")
    window.strategy_history_limit_down_checkbox.setChecked(True)
    strategy_history_controls.addWidget(strategy_history_label)
    strategy_history_controls.addWidget(window.strategy_history_start_input)
    strategy_history_controls.addWidget(window.strategy_history_end_input)
    strategy_history_controls.addWidget(window.strategy_history_max_hold_input)
    strategy_history_controls.addWidget(window.strategy_history_slippage_input)
    strategy_history_controls.addWidget(window.strategy_history_commission_input)
    strategy_history_controls.addWidget(window.strategy_history_stamp_duty_input)
    strategy_history_controls.addWidget(window.strategy_history_include_watch_checkbox)
    strategy_history_controls.addWidget(window.strategy_history_limit_up_checkbox)
    strategy_history_controls.addWidget(window.strategy_history_limit_down_checkbox)
    strategy_history_controls.addStretch(1)
    tool_layout.addLayout(strategy_history_controls, 1, 0, 1, 2)

    detail_hint_panel = QFrame()
    detail_hint_panel.setObjectName("detailHintPanel")
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
    board_controls_toggle_row = QHBoxLayout()
    board_controls_toggle_row.setContentsMargins(0, 0, 0, 0)
    board_controls_toggle_row.setSpacing(10)
    window.board_controls_toggle_button = QPushButton("展开打板控制台")
    window._set_button_role(window.board_controls_toggle_button, "ghost")
    window.board_controls_toggle_button.setMinimumHeight(40)
    window.board_controls_toggle_button.clicked.connect(window.toggle_board_controls_panel)
    window.board_controls_status_label = QLabel("首屏优先看候选、监控和回封风险；导出和专项设置默认收起。")
    window.board_controls_status_label.setObjectName("inlineHint")
    window.board_controls_status_label.setProperty("pageTone", "board")
    window.board_controls_status_label.setWordWrap(True)
    window.board_controls_status_label.setMinimumHeight(42)
    board_controls_toggle_row.addWidget(window.board_controls_toggle_button)
    board_controls_toggle_row.addWidget(window.board_controls_status_label, stretch=1)
    layout.addLayout(board_controls_toggle_row)
    board_controls_drawer = QFrame()
    board_controls_drawer.setObjectName("boardControlsDrawer")
    board_controls_drawer.setProperty("actionRow", True)
    board_controls_drawer_layout = QVBoxLayout(board_controls_drawer)
    board_controls_drawer_layout.setContentsMargins(14, 14, 14, 14)
    board_controls_drawer_layout.setSpacing(8)
    board_controls_drawer_layout.addWidget(tool_panel)
    window.board_controls_drawer = board_controls_drawer
    layout.addWidget(board_controls_drawer)

    detail_summary_box = QGroupBox("单票速览")
    detail_summary_box.setObjectName("detailSummaryBox")
    window.detail_summary_box = detail_summary_box
    window._style_terminal_panel(detail_summary_box)
    detail_summary_box.setProperty("pageTone", "detail")
    detail_summary_box.setProperty("surfaceRole", "metric-band")
    detail_summary_layout = QVBoxLayout(detail_summary_box)
    detail_summary_layout.setContentsMargins(12, 12, 12, 12)
    detail_summary_layout.setSpacing(0)
    detail_summary_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    detail_summary_band.setObjectName("detailSummaryBand")
    detail_summary_band.set_grid_spacing(10, 10)
    window.detail_summary_metric_cards = {}
    window.detail_summary_metric_labels = {}
    window.detail_summary_metric_accents = {}
    for key, title, accent in [
        ("theme", "主线 / 动作", "等待焦点同步"),
        ("execution", "执行链路", "等待委托和回执"),
        ("risk", "风险 / 偏差", "等待风险与信号联动"),
        ("next", "下一步", "等待下钻动作"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.detail_summary_metric_cards[key] = card
        window.detail_summary_metric_labels[key] = value_label
        window.detail_summary_metric_accents[key] = accent_label
        detail_summary_band.add_panel(card)
    detail_summary_layout.addWidget(detail_summary_band)
    layout.addWidget(detail_summary_box)

    metrics_box = QGroupBox("策略摘要")
    window.detail_metrics_box = metrics_box
    window._style_terminal_panel(metrics_box)
    metrics_layout = QVBoxLayout(metrics_box)
    window.metrics_text = QTextEdit()
    window.metrics_text.setReadOnly(True)
    window.metrics_text.setObjectName("detailNotePanel")
    window.metrics_text.setMinimumHeight(220)
    window.metrics_text.setMaximumHeight(260)
    window._style_terminal_console(window.metrics_text)
    metrics_layout.addWidget(window.metrics_text)
    detail_recap_splitter = QSplitter(Qt.Horizontal)
    window.detail_recap_splitter = detail_recap_splitter
    detail_recap_splitter.setChildrenCollapsible(False)
    decision_box = QGroupBox("交易决策画像")
    execution_box = QGroupBox("执行状态回放")
    conclusion_box = QGroupBox("复盘结论")
    window._style_terminal_panel(decision_box, execution_box, conclusion_box)
    decision_box.setProperty("pageTone", "detail")
    execution_box.setProperty("pageTone", "detail")
    conclusion_box.setProperty("pageTone", "detail")
    decision_box.setProperty("surfaceRole", "analysis")
    execution_box.setProperty("surfaceRole", "analysis")
    conclusion_box.setProperty("surfaceRole", "analysis")

    decision_layout = QVBoxLayout(decision_box)
    window.detail_decision_text = QTextEdit()
    window.detail_decision_text.setReadOnly(True)
    window.detail_decision_text.setObjectName("detailNotePanel")
    window.detail_decision_text.setMinimumHeight(196)
    window.detail_decision_text.setMaximumHeight(228)
    window._style_terminal_console(window.detail_decision_text)
    window.detail_decision_text.setPlainText("选中标的后，这里会展示当前推荐、题材、策略和计划价位。")
    decision_layout.addWidget(window.detail_decision_text)

    execution_layout = QVBoxLayout(execution_box)
    window.detail_execution_text = QTextEdit()
    window.detail_execution_text.setReadOnly(True)
    window.detail_execution_text.setObjectName("detailNotePanel")
    window.detail_execution_text.setMinimumHeight(196)
    window.detail_execution_text.setMaximumHeight(228)
    window._style_terminal_console(window.detail_execution_text)
    window.detail_execution_text.setPlainText("选中标的后，这里会展示送审、提交、失败和最近执行回放。")
    execution_layout.addWidget(window.detail_execution_text)

    conclusion_layout = QVBoxLayout(conclusion_box)
    window.detail_conclusion_text = QTextEdit()
    window.detail_conclusion_text.setReadOnly(True)
    window.detail_conclusion_text.setObjectName("detailNotePanel")
    window.detail_conclusion_text.setMinimumHeight(196)
    window.detail_conclusion_text.setMaximumHeight(228)
    window._style_terminal_console(window.detail_conclusion_text)
    window.detail_conclusion_text.setPlainText("先看结论、回测和下一步。")
    conclusion_layout.addWidget(window.detail_conclusion_text)

    detail_recap_splitter.addWidget(decision_box)
    detail_recap_splitter.addWidget(execution_box)
    detail_recap_splitter.addWidget(conclusion_box)
    window._configure_splitter(detail_recap_splitter, [420, 420, 420])
    layout.addWidget(detail_recap_splitter)
    layout.addWidget(metrics_box)

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

    history_box = QGroupBox("历史战法统计")
    window._style_terminal_panel(history_box)
    history_layout = QVBoxLayout(history_box)
    window.strategy_history_table = build_table(["战法", "信号数", "成交数", "成交率", "总收益", "胜率", "最大回撤", "平均持有"])
    history_layout.addWidget(window.strategy_history_table)
    window.strategy_history_rank_table = build_table(["排名", "战法", "总收益", "收益因子", "盈亏比", "最大回撤", "最大连亏"])
    history_layout.addWidget(window.strategy_history_rank_table)
    window.strategy_history_leaderboard_table = build_table(["战法", "场景数", "最佳场景", "最佳收益", "最差场景", "最差收益", "收益差", "平均收益"])
    history_layout.addWidget(window.strategy_history_leaderboard_table)
    window.strategy_history_compare_table = build_table(["场景", "战法", "最长持有", "总收益", "胜率", "最大回撤", "收益因子", "盈亏比", "最大连亏", "备注"])
    history_layout.addWidget(window.strategy_history_compare_table)
    window.strategy_history_curve_view = QChartView()
    _configure_chart_view(window.strategy_history_curve_view, min_height=220)
    window.strategy_history_curve_view.setProperty("pageTone", "detail")
    history_layout.addWidget(window.strategy_history_curve_view)
    period_splitter = QSplitter(Qt.Horizontal)
    period_splitter.setChildrenCollapsible(False)
    yearly_box = QGroupBox("年度统计")
    monthly_box = QGroupBox("月度统计")
    window._style_terminal_panel(yearly_box, monthly_box)
    yearly_layout = QVBoxLayout(yearly_box)
    monthly_layout = QVBoxLayout(monthly_box)
    window.strategy_history_yearly_table = build_table(["战法", "年度", "交易数", "胜率", "总收益", "平均收益"])
    window.strategy_history_monthly_table = build_table(["战法", "月度", "交易数", "胜率", "总收益", "平均收益"])
    yearly_layout.addWidget(window.strategy_history_yearly_table)
    monthly_layout.addWidget(window.strategy_history_monthly_table)
    window.strategy_history_heatmap_table = build_table(["战法", "年份", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"])
    monthly_layout.addWidget(window.strategy_history_heatmap_table)
    period_splitter.addWidget(yearly_box)
    period_splitter.addWidget(monthly_box)
    window._configure_splitter(period_splitter, [1, 1])
    history_layout.addWidget(period_splitter)
    window.strategy_history_trade_table = build_table(["战法", "股票", "信号日期", "入场日期", "离场日期", "买入价", "卖出价", "收益率", "持有天数", "退出原因"])
    history_layout.addWidget(window.strategy_history_trade_table)
    layout.addWidget(history_box)

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
    window.broker_status_banner.setProperty("pageTone", "broker")
    layout.addWidget(window.broker_status_banner)
    window.broker_stage_label = QLabel("执行阶段：待生成委托 | 先从推荐页或交易计划建立第一笔可执行委托。")
    window.broker_stage_label.setObjectName("focusStateLabel")
    window.broker_stage_label.setProperty("pageTone", "broker")
    window.broker_stage_label.setWordWrap(True)
    window.broker_stage_label.hide()
    layout.addWidget(window.broker_stage_label)

    broker_summary_box = QGroupBox("执行摘要")
    broker_summary_box.setObjectName("brokerSummaryBox")
    window.broker_summary_box = broker_summary_box
    window._style_terminal_panel(broker_summary_box)
    broker_summary_box.setProperty("pageTone", "broker")
    broker_summary_box.setProperty("surfaceRole", "metric-band")
    broker_summary_layout = QVBoxLayout(broker_summary_box)
    broker_summary_layout.setContentsMargins(12, 12, 12, 12)
    broker_summary_layout.setSpacing(0)
    broker_summary_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=186, max_columns=4)
    broker_summary_band.setObjectName("brokerSummaryBand")
    broker_summary_band.set_grid_spacing(10, 10)
    window.broker_summary_metric_cards = {}
    window.broker_summary_metric_labels = {}
    window.broker_summary_metric_accents = {}
    for key, title, accent in [
        ("stage", "执行阶段", "等待委托链路"),
        ("gate", "主线闸门", "等待主线审查"),
        ("queue", "委托队列", "等待生成委托"),
        ("receipt", "回执状态", "等待成交回执"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_summary_metric_cards[key] = card
        window.broker_summary_metric_labels[key] = value_label
        window.broker_summary_metric_accents[key] = accent_label
        broker_summary_band.add_panel(card)
    broker_summary_layout.addWidget(broker_summary_band)
    layout.addWidget(broker_summary_box)

    profile_box = QGroupBox("账户配置")
    window._style_terminal_panel(profile_box)
    profile_box.setObjectName("workspaceToolPanel")
    profile_grid = QGridLayout(profile_box)
    profile_grid.setHorizontalSpacing(10)
    profile_grid.setVerticalSpacing(10)
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
    guard_row = mode_row + 1
    profile_grid.addWidget(QLabel("提交安全"), guard_row, 0)
    window.test_submit_only_checkbox = QCheckBox("仅允许测试单")
    window.test_submit_only_checkbox.setChecked(bool(getattr(profile, "test_submit_only", True)))
    profile_grid.addWidget(window.test_submit_only_checkbox, guard_row, 1)
    profile_grid.addWidget(QLabel("测试单上限"), guard_row, 2)
    window.test_submit_max_amount_input = QLineEdit(f"{float(getattr(profile, 'test_submit_max_amount', 10000.0) or 10000.0):.0f}")
    profile_grid.addWidget(window.test_submit_max_amount_input, guard_row, 3)
    whitelist_row = guard_row + 1
    profile_grid.addWidget(QLabel("测试白名单"), whitelist_row, 0)
    window.test_submit_symbol_whitelist_input = QLineEdit(str(getattr(profile, "test_submit_symbol_whitelist", "") or ""))
    window.test_submit_symbol_whitelist_input.setPlaceholderText("例如：SHSE.600000,SZSE.000001")
    profile_grid.addWidget(window.test_submit_symbol_whitelist_input, whitelist_row, 1, 1, 3)
    export_row = whitelist_row + 1
    profile_grid.addWidget(QLabel("回执持久化"), export_row, 0)
    window.auto_export_submission_records_checkbox = QCheckBox("提交后自动导出回放")
    window.auto_export_submission_records_checkbox.setChecked(bool(getattr(profile, "auto_export_submission_records", True)))
    profile_grid.addWidget(window.auto_export_submission_records_checkbox, export_row, 1, 1, 3)

    choose_export_button = QPushButton("选择导出目录")
    save_profile_button = QPushButton("保存账户配置")
    create_templates_button = QPushButton("生成模板文件")
    choose_export_button.setObjectName("brokerChooseExportButton")
    save_profile_button.setObjectName("brokerSaveProfileButton")
    create_templates_button.setObjectName("brokerCreateTemplatesButton")
    window.choose_export_dir_button = choose_export_button
    window.save_broker_profile_button = save_profile_button
    window.create_broker_templates_button = create_templates_button
    window._set_button_role(choose_export_button)
    window._set_button_role(save_profile_button, "accent")
    window._set_button_role(create_templates_button)
    for button in (choose_export_button, save_profile_button, create_templates_button):
        button.setMinimumHeight(38)
        button.setMinimumWidth(128)
    choose_export_button.clicked.connect(window.choose_export_dir)
    save_profile_button.clicked.connect(window.save_profile)
    create_templates_button.clicked.connect(window.create_broker_templates)
    profile_grid.addWidget(choose_export_button, 0, 4)
    profile_grid.addWidget(save_profile_button, 1, 4)
    profile_grid.addWidget(create_templates_button, 2, 4)
    validate_profile_button = QPushButton("校验连接")
    window._set_button_role(validate_profile_button)
    validate_profile_button.setObjectName("brokerValidateConnectionButton")
    validate_profile_button.setMinimumHeight(38)
    validate_profile_button.setMinimumWidth(128)
    validate_profile_button.clicked.connect(window.validate_broker_connection)
    window.validate_broker_connection_button = validate_profile_button
    profile_grid.addWidget(validate_profile_button, 3, 4)

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
        button.setObjectName(
            [
                "brokerImportHoldingsButton",
                "brokerImportCashButton",
                "brokerGenerateSuggestionsButton",
                "brokerExportPlanButton",
                "brokerExportReplayButton",
                "brokerSyncSdkButton",
                "brokerGenerateScriptButton",
                "brokerConfirmSubmitButton",
            ][index]
        )
        button.setMinimumHeight(42)
        button.clicked.connect(handler)
        if label == "生成盘中计划":
            window.generate_order_suggestions_button = button
        elif label == "确认提交":
            window.confirm_submit_orders_button = button
        action_grid.addWidget(button, index // 4, index % 4)
        if handler == window.sync_broker_via_sdk:
            window.sync_broker_button = button
    window.broker_action_buttons = [
        action_box.findChild(QPushButton, "brokerImportHoldingsButton"),
        action_box.findChild(QPushButton, "brokerImportCashButton"),
        action_box.findChild(QPushButton, "brokerGenerateSuggestionsButton"),
        action_box.findChild(QPushButton, "brokerExportPlanButton"),
        action_box.findChild(QPushButton, "brokerExportReplayButton"),
        action_box.findChild(QPushButton, "brokerSyncSdkButton"),
        action_box.findChild(QPushButton, "brokerGenerateScriptButton"),
        action_box.findChild(QPushButton, "brokerConfirmSubmitButton"),
    ]

    broker_metrics_box = QGroupBox("执行指标")
    window.broker_metrics_box = broker_metrics_box
    window._style_terminal_panel(broker_metrics_box)
    broker_metrics_layout = QVBoxLayout(broker_metrics_box)
    broker_metrics_layout.setContentsMargins(12, 12, 12, 12)
    broker_metrics_layout.setSpacing(0)
    broker_metrics_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    broker_metrics_band.setObjectName("brokerMetricsBand")
    broker_metrics_band.set_grid_spacing(10, 10)
    window.broker_metric_labels = {}
    window.broker_metric_accents = {}
    for key, title, accent in [
        ("readiness", "能否提交", "等待评估"),
        ("capital", "占用预估", "0.00"),
        ("risk_reward", "盈亏期望", "-- / --"),
        ("risk_budget", "风险预算", "等待评估"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_metric_labels[key] = value_label
        window.broker_metric_accents[key] = accent_label
        broker_metrics_band.add_panel(card)
    broker_metrics_layout.addWidget(broker_metrics_band)
    layout.addWidget(broker_metrics_box)

    broker_execution_box = QGroupBox("主线审查 / 执行中控")
    window.broker_execution_box = broker_execution_box
    window._style_terminal_panel(broker_execution_box)
    broker_execution_layout = QVBoxLayout(broker_execution_box)
    broker_execution_layout.setContentsMargins(12, 12, 12, 12)
    broker_execution_layout.setSpacing(10)
    window.broker_gate_summary_text = QTextEdit()
    window.broker_gate_summary_text.setReadOnly(True)
    window.broker_gate_summary_text.setMinimumHeight(96)
    window.broker_gate_summary_text.setMaximumHeight(120)
    window._style_terminal_console(window.broker_gate_summary_text)
    window.broker_gate_summary_text.setPlainText("先看红灯，再看主线闸门和资金占用。")
    broker_execution_layout.addWidget(window.broker_gate_summary_text)

    broker_execution_summary_box = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    broker_execution_summary_box.setObjectName("brokerExecutionSummaryBox")
    broker_execution_summary_box.set_grid_margins(0, 0, 0, 0)
    broker_execution_summary_box.set_grid_spacing(8, 8)
    window.broker_execution_summary_metric_cards = {}
    window.broker_execution_summary_metric_labels = {}
    window.broker_execution_summary_metric_accents = {}
    for key, title, accent in [
        ("blocker", "阻塞 / 预警", "等待风控结论"),
        ("mainline", "主线前排", "等待主线审查"),
        ("action", "确认动作", "等待委托链路"),
        ("portfolio", "组合风控", "等待仓位校验"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        if key == "blocker":
            title_label = next(
                (child for child in card.findChildren(QLabel) if child not in {value_label, accent_label}),
                None,
            )
            if title_label is not None:
                title_label.setText("绾㈢伅 / 棰勮")
        elif key == "mainline":
            title_label = next(
                (child for child in card.findChildren(QLabel) if child not in {value_label, accent_label}),
                None,
            )
            if title_label is not None:
                title_label.setText("璧勯噾闂搁棬")
        elif key == "action":
            title_label = next(
                (child for child in card.findChildren(QLabel) if child not in {value_label, accent_label}),
                None,
            )
            if title_label is not None:
                title_label.setText("涓诲棣栫エ")
        elif key == "portfolio":
            title_label = next(
                (child for child in card.findChildren(QLabel) if child not in {value_label, accent_label}),
                None,
            )
            if title_label is not None:
                title_label.setText("涓嬩竴姝?")
        window.broker_execution_summary_metric_cards[key] = card
        window.broker_execution_summary_metric_labels[key] = value_label
        window.broker_execution_summary_metric_accents[key] = accent_label
        broker_execution_summary_box.add_panel(card)
    broker_execution_layout.addWidget(broker_execution_summary_box)

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

    broker_execution_detail_splitter = QSplitter(Qt.Horizontal)
    broker_execution_detail_splitter.setObjectName("brokerExecutionDetailSplit")
    broker_execution_detail_splitter.setChildrenCollapsible(False)
    window.broker_execution_detail_splitter = broker_execution_detail_splitter

    window.broker_mainline_review_text = QTextEdit()
    window.broker_mainline_review_text.setReadOnly(True)
    window.broker_mainline_review_text.setMinimumHeight(118)
    window.broker_mainline_review_text.setMaximumHeight(148)
    window._style_terminal_console(window.broker_mainline_review_text)
    window.broker_mainline_review_text.setPlainText("这里会显示主线闸门结果、阻塞原因和优先级说明。")

    window.broker_execution_text = QTextEdit()
    window.broker_execution_text.setReadOnly(True)
    window.broker_execution_text.setMinimumHeight(118)
    window.broker_execution_text.setMaximumHeight(148)
    window._style_terminal_console(window.broker_execution_text)
    window.broker_execution_text.setPlainText("生成盘中计划后，这里会汇总订单节奏、确认建议和提交记录。")

    broker_execution_detail_splitter.addWidget(window.broker_mainline_review_text)
    broker_execution_detail_splitter.addWidget(window.broker_execution_text)
    window._configure_splitter(broker_execution_detail_splitter, [1, 1])
    broker_execution_layout.addWidget(broker_execution_detail_splitter)
    layout.addWidget(broker_execution_box)

    status_box = QGroupBox("账户状态 / 诊断")
    window.broker_status_box = status_box
    window._style_terminal_panel(status_box)
    status_layout = QVBoxLayout(status_box)
    window.broker_status_text = QTextEdit()
    window.broker_status_text.setReadOnly(True)
    window.broker_status_text.setMinimumHeight(200)
    window.broker_status_text.setMaximumHeight(240)
    window._style_terminal_console(window.broker_status_text)
    status_layout.addWidget(window.broker_status_text)

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

    runtime_action_row = QGridLayout()
    runtime_action_row.setContentsMargins(0, 0, 0, 0)
    runtime_action_row.setHorizontalSpacing(8)
    runtime_action_row.setVerticalSpacing(8)
    runtime_action_specs = [
        ("刷新诊断", window.refresh_runtime_panel, "ghost", "runtimeRefreshButton"),
        ("导出运行日志", window.export_runtime_log, "ghost", "runtimeExportButton"),
        ("清理行情缓存", window.clear_market_cache, "ghost", "runtimeClearCacheButton"),
    ]
    for index, (label, handler, role, object_name) in enumerate(runtime_action_specs):
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setObjectName(object_name)
        button.setMinimumHeight(38)
        button.setMinimumWidth(104)
        button.clicked.connect(handler)
        runtime_action_row.addWidget(button, index // 2, index % 2)
    runtime_action_row.setColumnStretch(0, 1)
    runtime_action_row.setColumnStretch(1, 1)
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
    window.orders_focus_label.setProperty("pageTone", "broker")
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
    window.broker_order_focus_text.setMinimumHeight(220)
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
    result_layout.setContentsMargins(12, 12, 12, 12)
    result_layout.setSpacing(10)
    broker_result_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    broker_result_band.setObjectName("brokerResultSummaryBox")
    broker_result_band.set_grid_margins(0, 0, 0, 0)
    broker_result_band.set_grid_spacing(8, 8)
    window.broker_result_metric_cards = {}
    window.broker_result_metric_labels = {}
    window.broker_result_metric_accents = {}
    for key, title, accent in [
        ("stage", "\u56de\u6267\u9636\u6bb5", "\u7b49\u5f85\u63d0\u4ea4\u540e\u56de\u5199"),
        ("status", "\u8ba2\u5355 / \u6210\u4ea4", "\u7b49\u5f85\u9996\u6761\u56de\u6267"),
        ("risk", "\u5f02\u5e38 / \u504f\u5dee", "\u6682\u65e0\u65b0\u7684\u6267\u884c\u504f\u5dee"),
        ("next", "\u4e0b\u4e00\u6b65", "\u63d0\u4ea4\u540e\u81ea\u52a8\u805a\u7126\u6700\u65b0\u56de\u6267"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_result_metric_cards[key] = card
        window.broker_result_metric_labels[key] = value_label
        window.broker_result_metric_accents[key] = accent_label
        broker_result_band.add_panel(card)
    result_layout.addWidget(broker_result_band)

    window.broker_replay_event_cards = {}
    window.broker_replay_event_labels = {}
    window.broker_replay_event_accents = {}
    current_card, current_value_label, current_accent_label = window._create_metric_card(
        "\u5f53\u524d\u8282\u70b9",
        "--",
        "\u7b49\u5f85\u6700\u65b0\u56de\u6267",
    )
    current_card.setProperty("eventRail", "replay-master")
    current_card.setProperty("eventRole", "current")
    current_card.setProperty("replaySelected", False)
    current_card.setMinimumHeight(144)
    current_accent_label.setWordWrap(True)
    window.broker_replay_event_cards["current"] = current_card
    window.broker_replay_event_labels["current"] = current_value_label
    window.broker_replay_event_accents["current"] = current_accent_label
    result_layout.addWidget(current_card)
    if hasattr(window, "_bind_replay_event_card_click_v1"):
        window._bind_replay_event_card_click_v1(current_card, "current")

    broker_event_band = AdaptivePanelGrid(min_item_width=260, compact_item_width=196, max_columns=2)
    broker_event_band.setObjectName("brokerReplayEventBox")
    broker_event_band.set_grid_margins(0, 0, 0, 0)
    broker_event_band.set_grid_spacing(8, 8)
    for key, title, accent in [
        ("previous", "\u4e0a\u4e00\u8282\u70b9", "\u8fd9\u91cc\u4f1a\u4fdd\u7559\u4e0a\u4e00\u6761\u5bf9\u7167"),
        ("exception", "\u5f02\u5e38\u7126\u70b9", "\u5931\u8d25\u6216\u504f\u5dee\u4f1a\u5728\u8fd9\u91cc\u524d\u79fb"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        card.setProperty("eventRail", "replay")
        card.setProperty("eventRole", key)
        card.setProperty("replaySelected", False)
        card.setMinimumHeight(104)
        accent_label.setWordWrap(True)
        window.broker_replay_event_cards[key] = card
        window.broker_replay_event_labels[key] = value_label
        window.broker_replay_event_accents[key] = accent_label
        broker_event_band.add_panel(card)
        if hasattr(window, "_bind_replay_event_card_click_v1"):
            window._bind_replay_event_card_click_v1(card, key)
    result_layout.addWidget(broker_event_band)
    replay_action_row = QFrame()
    replay_action_row.setObjectName("brokerReplayActionRow")
    replay_action_row.setProperty("actionRow", True)
    replay_action_layout = QHBoxLayout(replay_action_row)
    replay_action_layout.setContentsMargins(10, 8, 10, 8)
    replay_action_layout.setSpacing(10)
    window.broker_replay_action_buttons = {}
    for key, label, role in [
        ("current", "\u770b\u5f53\u524d\u56de\u6267", "accent"),
        ("previous", "\u56de\u770b\u4e0a\u4e00\u6761", "tonal"),
        ("exception", "\u5904\u7f6e\u5f02\u5e38", "ghost"),
    ]:
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setMinimumHeight(36)
        button.clicked.connect(lambda _checked=False, replay_role=key: window._on_replay_event_card_clicked_v1(replay_role))
        replay_action_layout.addWidget(button)
        window.broker_replay_action_buttons[key] = button
    replay_action_layout.addStretch(1)
    result_layout.addWidget(replay_action_row)
    window.execution_table = build_table(["时间", "订单", "成交", "代码", "动作", "价格", "数量", "错误", "信息"])
    window.execution_table.setMinimumHeight(248)
    window.execution_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.execution_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.execution_table.setObjectName("submissionTable")
    result_layout.addWidget(window.execution_table)

    window.order_result_text = QTextEdit()
    window.order_result_text.setReadOnly(True)
    window.order_result_text.setMinimumHeight(124)
    window.order_result_text.setMaximumHeight(156)
    window._style_terminal_console(window.order_result_text)
    window.order_result_text.setPlainText("等待新的执行结果...\n")
    result_layout.addWidget(window.order_result_text)
    layout.addWidget(result_box, stretch=1)

    recap_box = QGroupBox("偏差复盘")
    window._style_terminal_panel(recap_box)
    window.broker_recap_box = recap_box
    recap_layout = QVBoxLayout(recap_box)
    recap_layout.setContentsMargins(12, 12, 12, 12)
    recap_layout.setSpacing(10)
    broker_recap_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    broker_recap_band.setObjectName("brokerRecapSummaryBox")
    broker_recap_band.set_grid_margins(0, 0, 0, 0)
    broker_recap_band.set_grid_spacing(8, 8)
    window.broker_recap_metric_cards = {}
    window.broker_recap_metric_labels = {}
    window.broker_recap_metric_accents = {}
    for key, title, accent in [
        ("verdict", "\u504f\u5dee\u7ed3\u8bba", "\u7b49\u5f85\u63d0\u4ea4\u540e\u751f\u6210"),
        ("mainline", "\u4e3b\u7ebf\u4e00\u81f4", "\u7b49\u5f85\u4e3b\u7ebf\u4e0e\u56de\u6267\u8054\u52a8"),
        ("quality", "\u6267\u884c\u8d28\u91cf", "\u7b49\u5f85\u4ef7\u683c\u548c\u6210\u4ea4\u56de\u5199"),
        ("action", "\u5904\u7406\u52a8\u4f5c", "\u63d0\u4ea4\u540e\u8fd9\u91cc\u4f1a\u7ed9\u51fa\u590d\u76d8\u52a8\u4f5c"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_recap_metric_cards[key] = card
        window.broker_recap_metric_labels[key] = value_label
        window.broker_recap_metric_accents[key] = accent_label
        broker_recap_band.add_panel(card)
    recap_layout.addWidget(broker_recap_band)
    window.broker_recap_text = QTextEdit()
    window.broker_recap_text.setReadOnly(True)
    window.broker_recap_text.setMinimumHeight(144)
    window.broker_recap_text.setMaximumHeight(184)
    window._style_terminal_console(window.broker_recap_text)
    window.broker_recap_text.setPlainText("提交后，这里沉淀通过率、阻塞原因和偏差。")
    recap_layout.addWidget(window.broker_recap_text)
    layout.addWidget(recap_box)

    broker_setup_toggle_row = QHBoxLayout()
    broker_setup_toggle_row.setContentsMargins(0, 0, 0, 0)
    broker_setup_toggle_row.setSpacing(10)
    window.broker_setup_toggle_button = QPushButton("展开账户与通道设置")
    window._set_button_role(window.broker_setup_toggle_button, "ghost")
    window.broker_setup_toggle_button.setMinimumHeight(40)
    window.broker_setup_toggle_button.clicked.connect(window.toggle_broker_setup_panel)
    window.broker_setup_status_label = QLabel("账户接入、SDK、导出与运行维护默认收起；盘中先看委托、风险闸门和回执。")
    window.broker_setup_status_label.setObjectName("inlineHint")
    window.broker_setup_status_label.setProperty("pageTone", "broker")
    window.broker_setup_status_label.setWordWrap(True)
    window.broker_setup_status_label.setMinimumHeight(42)
    window.broker_setup_profile_button = QPushButton("账户")
    window.broker_setup_action_button = QPushButton("执行参数")
    window.broker_setup_runtime_button = QPushButton("运行维护")
    for button in (
        window.broker_setup_profile_button,
        window.broker_setup_action_button,
        window.broker_setup_runtime_button,
    ):
        window._set_button_role(button, "ghost")
        button.setMinimumHeight(36)
    window.broker_setup_profile_button.clicked.connect(lambda: window.open_broker_setup_section("profile"))
    window.broker_setup_action_button.clicked.connect(lambda: window.open_broker_setup_section("action"))
    window.broker_setup_runtime_button.clicked.connect(lambda: window.open_broker_setup_section("runtime"))
    broker_setup_toggle_row.addWidget(window.broker_setup_toggle_button)
    broker_setup_toggle_row.addWidget(window.broker_setup_profile_button)
    broker_setup_toggle_row.addWidget(window.broker_setup_action_button)
    broker_setup_toggle_row.addWidget(window.broker_setup_runtime_button)
    broker_setup_toggle_row.addWidget(window.broker_setup_status_label, stretch=1)
    layout.addLayout(broker_setup_toggle_row)

    broker_setup_drawer = QFrame()
    broker_setup_drawer.setObjectName("brokerSetupDrawer")
    broker_setup_drawer.setProperty("actionRow", True)
    broker_setup_drawer_layout = QVBoxLayout(broker_setup_drawer)
    broker_setup_drawer_layout.setContentsMargins(14, 14, 14, 14)
    broker_setup_drawer_layout.setSpacing(14)
    broker_setup_drawer_layout.addWidget(status_box)
    broker_setup_drawer_layout.addWidget(broker_control_splitter)
    window.broker_setup_drawer = broker_setup_drawer
    layout.addWidget(broker_setup_drawer)

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
    window.overview_content = overview_content
    window.overview_scroll_area.setWidget(overview_content)
    layout = QVBoxLayout(overview_content)
    window.overview_root_layout = layout
    layout.setContentsMargins(10, 10, 10, 18)
    layout.setSpacing(14)
    quick_row = QGridLayout()
    quick_row.setHorizontalSpacing(8)
    quick_row.setVerticalSpacing(8)
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
        button.setMinimumWidth(92)
        button.setStyleSheet(window._overview_outline_style(color))
        button.clicked.connect(lambda checked=False, current_text=text: window.activate_overview_quick_action(current_text))
        window.overview_quick_buttons[text] = button
        quick_row.addWidget(button, index // 4, index % 4)
    for column in range(4):
        quick_row.setColumnStretch(column, 1)
    toolbar = QVBoxLayout()
    toolbar.setContentsMargins(12, 10, 12, 10)
    toolbar.setSpacing(8)
    search_input_row = QHBoxLayout()
    search_input_row.setContentsMargins(0, 0, 0, 0)
    search_input_row.setSpacing(10)
    window.market_search_input = QLineEdit()
    window.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材")
    window.market_search_input.setMinimumHeight(42)
    window.market_search_input.setMinimumWidth(180)
    window.market_search_input.setMaximumWidth(280)
    window.market_search_input.textChanged.connect(window._apply_market_filters)
    window.market_theme_combo = QComboBox()
    window.market_theme_combo.addItem("全部")
    window.market_theme_combo.setMinimumHeight(42)
    window.market_theme_combo.setMinimumWidth(96)
    window.market_theme_combo.currentTextChanged.connect(window._on_market_theme_filter_changed)
    window.market_history_date_combo = QComboBox()
    window.market_history_date_combo.addItem("最新")
    window.market_history_date_combo.setMinimumHeight(42)
    window.market_history_date_combo.setMinimumWidth(126)
    window.market_history_date_combo.currentTextChanged.connect(window._on_market_history_date_changed)
    window.market_refresh_button = QPushButton("刷新市场")
    window.market_refresh_button.setMinimumHeight(42)
    window.market_refresh_button.setMinimumWidth(148)
    window.market_refresh_button.setStyleSheet(window._overview_filled_style("#237fa2"))
    window.market_refresh_button.clicked.connect(lambda: window.refresh_remote_market(update_chart=True))
    window.market_history_reset_button = QPushButton("回最新")
    window.market_history_reset_button.setMinimumHeight(42)
    window.market_history_reset_button.setMinimumWidth(108)
    window._set_button_role(window.market_history_reset_button, "ghost")
    window.market_history_reset_button.clicked.connect(window.reset_market_history_view)
    window.dashboard_auto_refresh_checkbox = QCheckBox("自动刷新")
    window.dashboard_auto_refresh_checkbox.setMinimumHeight(40)
    window.dashboard_auto_refresh_checkbox.toggled.connect(window.toggle_dashboard_auto_refresh)
    window.dashboard_auto_refresh_checkbox.blockSignals(True)
    window.dashboard_auto_refresh_checkbox.setChecked(True)
    window.dashboard_auto_refresh_checkbox.blockSignals(False)
    window.market_status_label = QLabel("总览：同步市场与主线")
    window.market_status_label.setObjectName("statusBanner")
    window.market_status_label.setWordWrap(True)
    window.market_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    window.market_status_label.setMinimumHeight(40)
    search_input_row.addWidget(window.market_search_input, stretch=3)
    search_input_row.addWidget(window.market_theme_combo, stretch=1)
    search_input_row.addWidget(window.market_history_date_combo, stretch=1)
    toolbar.addLayout(search_input_row)
    search_action_row = QHBoxLayout()
    search_action_row.setContentsMargins(0, 0, 0, 0)
    search_action_row.setSpacing(8)
    search_action_row.addWidget(window.market_refresh_button)
    search_action_row.addWidget(window.market_history_reset_button)
    search_action_row.addWidget(window.dashboard_auto_refresh_checkbox)
    search_action_row.addWidget(window.market_status_label, stretch=1)
    toolbar.addLayout(search_action_row)
    filter_row = QGridLayout()
    filter_row.setHorizontalSpacing(8)
    filter_row.setVerticalSpacing(8)
    window.market_filter_buttons = {}
    filter_button_style = window._overview_outline_style("#6f8196")
    for tag in ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "掘龙决策"]:
        button = QPushButton(tag)
        button.setCheckable(True)
        button.setMinimumHeight(40)
        button.setMinimumWidth(96)
        button.setStyleSheet(filter_button_style)
        button.clicked.connect(lambda checked=False, current_tag=tag: window.set_market_filter(current_tag))
        if tag == "全部":
            button.setChecked(True)
        window.market_filter_buttons[tag] = button
        button_index = len(window.market_filter_buttons) - 1
        filter_row.addWidget(button, button_index // 4, button_index % 4)
    if "一日持股法" not in window.market_filter_buttons:
        one_day_button = QPushButton("一日持股法")
        one_day_button.setCheckable(True)
        one_day_button.setMinimumHeight(40)
        one_day_button.setMinimumWidth(96)
        one_day_button.setStyleSheet(filter_button_style)
        one_day_button.clicked.connect(lambda checked=False: window.set_market_filter("一日持股法"))
        window.market_filter_buttons["一日持股法"] = one_day_button
        button_index = len(window.market_filter_buttons) - 1
        filter_row.addWidget(one_day_button, button_index // 4, button_index % 4)
    for column in range(4):
        filter_row.setColumnStretch(column, 1)
    controls_container = QWidget()
    controls_container.setObjectName("overviewControlsContainer")
    controls_layout = QGridLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setHorizontalSpacing(12)
    controls_layout.setVerticalSpacing(12)
    overview_view_box = QGroupBox("视图")
    overview_view_box.setObjectName("overviewViewBox")
    overview_search_box = QGroupBox("控制")
    overview_search_box.setObjectName("overviewSearchBox")
    overview_tag_box = QGroupBox("快筛")
    overview_tag_box.setObjectName("overviewTagBox")
    overview_view_box.setProperty("surfaceRole", "control")
    overview_search_box.setProperty("surfaceRole", "control")
    overview_tag_box.setProperty("surfaceRole", "control")
    window._style_terminal_panel(overview_view_box, overview_search_box, overview_tag_box)
    overview_view_box.setProperty("pageTone", "overview")
    overview_search_box.setProperty("pageTone", "overview")
    overview_tag_box.setProperty("pageTone", "overview")
    overview_view_layout = QVBoxLayout(overview_view_box)
    overview_view_layout.setContentsMargins(12, 10, 12, 12)
    overview_view_layout.setSpacing(8)
    overview_view_layout.addLayout(quick_row)
    overview_search_layout = QVBoxLayout(overview_search_box)
    overview_search_layout.setContentsMargins(12, 10, 12, 12)
    overview_search_layout.setSpacing(8)
    overview_search_layout.addLayout(toolbar)
    overview_tag_layout = QVBoxLayout(overview_tag_box)
    overview_tag_layout.setContentsMargins(12, 10, 12, 12)
    overview_tag_layout.setSpacing(8)
    overview_tag_layout.addLayout(filter_row)
    controls_layout.addWidget(overview_view_box, 0, 0)
    controls_layout.addWidget(overview_search_box, 0, 1)
    controls_layout.addWidget(overview_tag_box, 0, 2)
    controls_layout.setColumnStretch(0, 4)
    controls_layout.setColumnStretch(1, 5)
    controls_layout.setColumnStretch(2, 4)
    window.overview_controls_container = controls_container
    window.overview_controls_layout = controls_layout
    window.overview_view_box = overview_view_box
    window.overview_search_box = overview_search_box
    window.overview_tag_box = overview_tag_box
    overview_controls_toggle_row = QHBoxLayout()
    overview_controls_toggle_row.setContentsMargins(0, 0, 0, 0)
    overview_controls_toggle_row.setSpacing(10)
    window.overview_controls_toggle_button = QPushButton("展开控制区")
    window._set_button_role(window.overview_controls_toggle_button, "ghost")
    window.overview_controls_toggle_button.setMinimumHeight(40)
    window.overview_controls_toggle_button.clicked.connect(window.toggle_overview_controls_panel)
    window.overview_controls_status_label = QLabel("首屏先看市场洞察，控制区默认收起。")
    window.overview_controls_status_label.setObjectName("inlineHint")
    window.overview_controls_status_label.setProperty("pageTone", "overview")
    window.overview_controls_status_label.setWordWrap(True)
    window.overview_controls_status_label.setMinimumHeight(42)
    overview_controls_toggle_row.addWidget(window.overview_controls_toggle_button)
    overview_controls_toggle_row.addWidget(window.overview_controls_status_label, stretch=1)
    layout.addLayout(overview_controls_toggle_row)
    overview_controls_drawer = QFrame()
    overview_controls_drawer.setObjectName("overviewControlsDrawer")
    overview_controls_drawer.setProperty("actionRow", True)
    overview_controls_drawer_layout = QVBoxLayout(overview_controls_drawer)
    overview_controls_drawer_layout.setContentsMargins(14, 14, 14, 14)
    overview_controls_drawer_layout.setSpacing(8)
    overview_controls_drawer_layout.addWidget(controls_container)
    window.overview_controls_drawer = overview_controls_drawer
    layout.addWidget(overview_controls_drawer)
    dashboard_metrics_box = QGroupBox("核心指标带")
    dashboard_metrics_box.setObjectName("dashboardMetricsBox")
    window.dashboard_metrics_box = dashboard_metrics_box
    window._style_terminal_panel(dashboard_metrics_box)
    dashboard_metrics_box.setProperty("pageTone", "overview")
    dashboard_metrics_box.setProperty("surfaceRole", "metric-band")
    metrics_row = QVBoxLayout(dashboard_metrics_box)
    metrics_row.setContentsMargins(12, 12, 12, 12)
    metrics_row.setSpacing(0)
    metrics_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    metrics_band.setObjectName("dashboardMetricsBand")
    metrics_band.set_grid_spacing(10, 10)
    window.dashboard_metric_labels = {}
    window.dashboard_metric_accents = {}
    for key, title, accent in [
        ("candidate_count", "候选总量", "等待刷新"),
        ("buy_count", "可做数量", "等待刷新"),
        ("avg_heat", "市场温度", "等待刷新"),
        ("top_theme", "主线占优", "等待刷新"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.dashboard_metric_labels[key] = value_label
        window.dashboard_metric_accents[key] = accent_label
        metrics_band.add_panel(card)
    metrics_row.addWidget(metrics_band)
    layout.addWidget(dashboard_metrics_box)
    cockpit_box = QGroupBox("市场驾驶舱")
    cockpit_box.setObjectName("cockpitBox")
    window.overview_cockpit_box = cockpit_box
    window._style_terminal_panel(cockpit_box)
    cockpit_box.setProperty("pageTone", "overview")
    cockpit_box.setProperty("surfaceRole", "spotlight")
    cockpit_layout = QVBoxLayout(cockpit_box)
    cockpit_body = QSplitter(Qt.Horizontal)
    cockpit_body.setChildrenCollapsible(False)
    window.overview_command_text = QTextEdit()
    window.overview_command_text.setReadOnly(True)
    window.overview_command_text.setObjectName("marketNotePanel")
    window.overview_command_text.setProperty("panelTone", "command")
    window.overview_command_text.setMinimumHeight(162)
    cockpit_body.addWidget(window.overview_command_text)
    window.overview_execution_text = QTextEdit()
    window.overview_execution_text.setReadOnly(True)
    window.overview_execution_text.setObjectName("marketNotePanel")
    window.overview_execution_text.setProperty("panelTone", "execution")
    window.overview_execution_text.setMinimumHeight(162)
    cockpit_body.addWidget(window.overview_execution_text)
    window._configure_splitter(cockpit_body, [1, 1])
    cockpit_layout.addWidget(cockpit_body)
    cockpit_action_row_widget = QWidget()
    cockpit_action_row_widget.setObjectName("overviewCockpitActionRow")
    cockpit_action_row = QHBoxLayout(cockpit_action_row_widget)
    cockpit_action_row.setContentsMargins(0, 0, 0, 0)
    cockpit_action_row.setSpacing(10)
    window.overview_cockpit_action_buttons = []
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
        window.overview_cockpit_action_buttons.append(button)
    window.overview_cockpit_more_button = QPushButton("更多")
    window.overview_cockpit_more_button.setObjectName("overviewCockpitMoreButton")
    window._set_button_role(window.overview_cockpit_more_button, "ghost")
    window.overview_cockpit_more_button.setMinimumHeight(40)
    window.overview_cockpit_more_button.hide()
    cockpit_action_row.addWidget(window.overview_cockpit_more_button)
    cockpit_action_row.addStretch(1)
    cockpit_layout.addWidget(cockpit_action_row_widget)
    layout.addWidget(cockpit_box)

    playbook_box = QGroupBox("行动剧本")
    playbook_box.setObjectName("playbookBox")
    window.overview_playbook_box = playbook_box
    window._style_terminal_panel(playbook_box)
    playbook_box.setProperty("pageTone", "overview")
    playbook_box.setProperty("surfaceRole", "spotlight")
    playbook_layout = QVBoxLayout(playbook_box)
    window.overview_playbook_text = QTextEdit()
    window.overview_playbook_text.setReadOnly(True)
    window.overview_playbook_text.setObjectName("marketNotePanel")
    window.overview_playbook_text.setProperty("panelTone", "playbook")
    window.overview_playbook_text.setMinimumHeight(128)
    window.overview_playbook_text.setPlainText(
        "先完成登录与交易通道配置，再刷新市场、查看主线和推荐池，最后进入交易执行页复核委托。"
    )
    playbook_layout.addWidget(window.overview_playbook_text)
    playbook_action_row_widget = QWidget()
    playbook_action_row_widget.setObjectName("overviewPlaybookActionRow")
    playbook_action_row = QHBoxLayout(playbook_action_row_widget)
    playbook_action_row.setContentsMargins(0, 0, 0, 0)
    playbook_action_row.setSpacing(10)
    window.overview_playbook_action_buttons = []
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
        window.overview_playbook_action_buttons.append(button)
    window.overview_playbook_more_button = QPushButton("更多")
    window.overview_playbook_more_button.setObjectName("overviewPlaybookMoreButton")
    window._set_button_role(window.overview_playbook_more_button, "ghost")
    window.overview_playbook_more_button.setMinimumHeight(38)
    window.overview_playbook_more_button.hide()
    playbook_action_row.addWidget(window.overview_playbook_more_button)
    playbook_action_row.addStretch(1)
    playbook_layout.addWidget(playbook_action_row_widget)
    layout.addWidget(playbook_box)

    window.overview_stage_container = QWidget()
    window.overview_stage_container.setObjectName("workspaceStage")
    overview_stage_layout = QVBoxLayout(window.overview_stage_container)
    overview_stage_layout.setContentsMargins(0, 0, 0, 0)
    overview_stage_layout.setSpacing(12)
    overview_command_stage = QWidget()
    overview_detail_stage = QWidget()
    overview_stage_layout.addWidget(overview_command_stage, stretch=6)
    overview_stage_layout.addWidget(overview_detail_stage, stretch=2)
    layout.addWidget(window.overview_stage_container, stretch=5)
    command_stage_layout = QVBoxLayout(overview_command_stage)
    window.overview_command_stage_layout = command_stage_layout
    command_stage_layout.setContentsMargins(0, 4, 0, 0)
    command_stage_layout.setSpacing(12)
    detail_stage_layout = QVBoxLayout(overview_detail_stage)
    window.overview_detail_stage_layout = detail_stage_layout
    detail_stage_layout.setContentsMargins(0, 8, 0, 0)
    detail_stage_layout.setSpacing(14)
    overview_priority_box = QGroupBox("盘前优先级")
    overview_priority_box.setObjectName("overviewPriorityBox")
    window.overview_priority_box = overview_priority_box
    window._style_terminal_panel(overview_priority_box)
    overview_priority_box.setProperty("pageTone", "overview")
    overview_priority_box.setProperty("surfaceRole", "priority-rail")
    overview_priority_layout = QVBoxLayout(overview_priority_box)
    overview_priority_layout.setContentsMargins(14, 12, 14, 12)
    overview_priority_layout.setSpacing(6)
    overview_priority_band = AdaptivePanelGrid(min_item_width=260, compact_item_width=224, max_columns=4)
    overview_priority_band.setObjectName("overviewPriorityBand")
    overview_priority_band.set_grid_spacing(10, 10)
    window.overview_priority_cards = {
        "market": action_flow_card_cls("买", "#25d07f"),
        "theme": action_flow_card_cls("持", "#4fc3f7"),
        "strategy": action_flow_card_cls("减", "#ffb347"),
        "focus": action_flow_card_cls("卖", "#ff6b6b"),
    }
    for key in ["market", "theme", "strategy", "focus"]:
        overview_priority_band.add_panel(window.overview_priority_cards[key])
    overview_priority_layout.addWidget(overview_priority_band)
    command_stage_layout.addWidget(overview_priority_box)
    main_splitter = QSplitter(Qt.Horizontal)
    main_splitter.setChildrenCollapsible(False)
    window.overview_main_splitter = main_splitter
    left_panel = QWidget()
    left_panel.setObjectName("overviewSidePanel")
    left_panel.setMinimumWidth(264)
    window.overview_left_panel = left_panel
    left_layout = QVBoxLayout(left_panel)
    left_layout.setContentsMargins(0, 0, 0, 0)
    left_layout.setSpacing(10)
    left_title = QLabel("市场快照")
    left_title.setObjectName("heroTitle")
    window.overview_left_title = left_title
    left_layout.addWidget(left_title)
    window.overview_intraday_container = QWidget()
    window.overview_intraday_container_layout = QVBoxLayout(window.overview_intraday_container)
    window.overview_intraday_container_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_intraday_container_layout.setSpacing(0)
    window.intraday_chart_view = chart_view_cls()
    _configure_chart_view(window.intraday_chart_view, min_height=260)
    window.overview_intraday_container_layout.addWidget(window.intraday_chart_view)
    left_layout.addWidget(window.overview_intraday_container, stretch=5)
    left_notes = QTabWidget()
    left_notes.setObjectName("compactInfoTabs")
    window.left_signal_tabs = left_notes
    buy_box = QGroupBox("今天能不能买")
    buy_box.setObjectName("buySignalBox")
    buy_box.setProperty("pageTone", "overview")
    buy_layout = QVBoxLayout(buy_box)
    window.market_buy_text = QTextEdit()
    window.market_buy_text.setReadOnly(True)
    window.market_buy_text.setObjectName("marketNotePanel")
    window.market_buy_text.setProperty("panelTone", "buy")
    window.market_buy_text.setMinimumHeight(140)
    buy_layout.addWidget(window.market_buy_text)
    risk_box = QGroupBox("减仓和卖点")
    risk_box.setObjectName("riskSignalBox")
    risk_box.setProperty("pageTone", "overview")
    risk_layout = QVBoxLayout(risk_box)
    window.market_sell_text = QTextEdit()
    window.market_sell_text.setReadOnly(True)
    window.market_sell_text.setObjectName("marketNotePanel")
    window.market_sell_text.setProperty("panelTone", "risk")
    window.market_sell_text.setMinimumHeight(140)
    risk_layout.addWidget(window.market_sell_text)
    breadth_box = QGroupBox("消息面")
    breadth_box.setObjectName("breadthSignalBox")
    breadth_box.setProperty("pageTone", "overview")
    breadth_layout = QVBoxLayout(breadth_box)
    window.market_news_group = breadth_box
    window.market_breadth_text = QTextEdit()
    window.market_breadth_text.setReadOnly(True)
    window.market_breadth_text.setObjectName("marketNotePanel")
    window.market_breadth_text.setProperty("panelTone", "watch")
    window.market_breadth_text.setMinimumHeight(150)
    breadth_layout.addWidget(window.market_breadth_text)
    breadth_action_row = QHBoxLayout()
    breadth_action_row.setContentsMargins(0, 2, 0, 0)
    breadth_action_row.setSpacing(10)
    window.market_open_news_button = QPushButton("查看原文")
    window.market_news_detail_button = QPushButton("消息详情")
    window._set_button_role(window.market_open_news_button, "ghost")
    window._set_button_role(window.market_news_detail_button, "ghost")
    window.market_open_news_button.setToolTip(window._news_source_button_base_tooltip())
    window.market_news_detail_button.setToolTip(window._news_detail_button_base_tooltip())
    window.market_open_news_button.clicked.connect(window.open_overview_focus_news_source)
    window.market_news_detail_button.clicked.connect(window.open_overview_focus_news_detail)
    breadth_action_row.addWidget(window.market_open_news_button)
    breadth_action_row.addWidget(window.market_news_detail_button)
    breadth_action_row.addStretch(1)
    breadth_layout.addLayout(breadth_action_row)
    left_notes.addTab(buy_box, "买点")
    left_notes.addTab(risk_box, "卖点")
    left_notes.addTab(breadth_box, "消息面")
    left_layout.addWidget(left_notes, stretch=2)
    main_splitter.addWidget(left_panel)
    center_panel = QWidget()
    center_panel.setObjectName("overviewCenterPanel")
    center_panel.setMinimumWidth(760)
    center_layout = QVBoxLayout(center_panel)
    center_layout.setContentsMargins(0, 0, 0, 0)
    center_layout.setSpacing(10)
    window.market_header_label = QLabel("市场机会工作台")
    window.market_header_label.setObjectName("heroTitle")
    center_layout.addWidget(window.market_header_label)
    window.market_subheader_label = QLabel("主线、趋势、消息、决策一屏联动。")
    window.market_subheader_label.setObjectName("heroSubtitle")
    window.market_subheader_label.setWordWrap(True)
    center_layout.addWidget(window.market_subheader_label)
    window.market_signal_label = QLabel("主线 / 趋势 / 资金 / 消息 / 决策")
    window.market_signal_label.setObjectName("terminalSignal")
    center_layout.addWidget(window.market_signal_label)
    window.market_quote_label = QLabel("开高低收 / 涨跌幅 / 换手 / 主力净流入 / 龙头级别 / 股票池")
    window.market_quote_label.setObjectName("inlineHint")
    window.market_quote_label.setWordWrap(True)
    center_layout.addWidget(window.market_quote_label)
    market_focus_box = QGroupBox("焦点速览")
    market_focus_box.setObjectName("marketFocusSummaryBox")
    window.market_focus_summary_box = market_focus_box
    window._style_terminal_panel(market_focus_box)
    market_focus_box.setProperty("pageTone", "overview")
    market_focus_box.setProperty("surfaceRole", "metric-band")
    market_focus_layout = QVBoxLayout(market_focus_box)
    market_focus_layout.setContentsMargins(12, 12, 12, 12)
    market_focus_layout.setSpacing(0)
    market_focus_band = AdaptivePanelGrid(min_item_width=188, compact_item_width=160, max_columns=4)
    market_focus_band.setObjectName("marketFocusSummaryBand")
    market_focus_band.set_grid_spacing(10, 10)
    window.market_focus_metric_cards = {}
    window.market_focus_metric_labels = {}
    window.market_focus_metric_accents = {}
    for key, title, accent in [
        ("structure", "结构节奏", "等待图表同步"),
        ("zone", "交易区间", "等待价位带"),
        ("momentum", "K线 / 共振", "等待共振判断"),
        ("flow", "资金温度", "等待资金画像"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.market_focus_metric_cards[key] = card
        window.market_focus_metric_labels[key] = value_label
        window.market_focus_metric_accents[key] = accent_label
        market_focus_band.add_panel(card)
    market_focus_layout.addWidget(market_focus_band)
    center_layout.addWidget(market_focus_box)
    timeframe_row = QHBoxLayout()
    timeframe_row.setContentsMargins(0, 0, 0, 0)
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
    history_row = QHBoxLayout()
    history_row.setContentsMargins(0, 0, 0, 0)
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
    chart_control_row = QHBoxLayout()
    chart_control_row.setContentsMargins(0, 0, 0, 0)
    chart_control_row.setSpacing(8)
    prev_chart_button = QPushButton("向左翻一屏")
    next_chart_button = QPushButton("向右翻一屏")
    reset_chart_button = QPushButton("回到最新")
    window.market_chart_prev_button = prev_chart_button
    window.market_chart_next_button = next_chart_button
    window.market_chart_reset_button = reset_chart_button
    window._set_button_role(prev_chart_button)
    window._set_button_role(next_chart_button)
    window._set_button_role(reset_chart_button, "tonal")
    prev_chart_button.setToolTip("向左翻一屏，查看更早的数据。按 PageUp 也可翻屏，Shift+左键 可细步进。")
    next_chart_button.setToolTip("向右翻一屏，返回更近的数据。按 PageDown 也可翻屏，Shift+右键 可细步进。")
    reset_chart_button.setToolTip("回到最新窗口。按 Home 可快速重置。")
    prev_chart_button.clicked.connect(lambda: window.shift_market_chart_window(1))
    next_chart_button.clicked.connect(lambda: window.shift_market_chart_window(-1))
    reset_chart_button.clicked.connect(window.reset_market_chart_window)
    chart_control_row.addWidget(prev_chart_button)
    chart_control_row.addWidget(next_chart_button)
    chart_control_row.addWidget(reset_chart_button)
    chart_control_row.addSpacing(12)
    window.market_chart_nav_label = QLabel("K 线导航：日线 | 近1年 | 第 1 屏 / 共 1 屏")
    window.market_chart_nav_label.setObjectName("inlineHint")
    chart_control_row.addWidget(window.market_chart_nav_label)
    chart_control_row.addSpacing(12)
    chart_control_row.addWidget(QLabel("主图叠加"))
    window.market_overlay_buttons = {}
    for text, checked in [("MA", True), ("BOLL", True), ("HIGHLOW", True), ("BREAK", False)]:
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
    for text, checked in [("MACD", True), ("RSI", False), ("KDJ", False), ("VOL", False)]:
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
    chart_controls_tabs = QTabWidget()
    chart_controls_tabs.setObjectName("compactInfoTabs")
    window.overview_chart_controls_tabs = chart_controls_tabs

    timeframe_tab = QWidget()
    timeframe_tab_layout = QVBoxLayout(timeframe_tab)
    timeframe_tab_layout.setContentsMargins(8, 8, 8, 8)
    timeframe_tab_layout.setSpacing(8)
    timeframe_tab_layout.addLayout(timeframe_row)
    timeframe_tab_layout.addLayout(history_row)

    chart_tools_tab = QWidget()
    chart_tools_tab_layout = QVBoxLayout(chart_tools_tab)
    chart_tools_tab_layout.setContentsMargins(8, 8, 8, 8)
    chart_tools_tab_layout.setSpacing(8)
    chart_tools_tab_layout.addLayout(chart_control_row)

    chart_controls_tabs.addTab(timeframe_tab, "周期窗口")
    chart_controls_tabs.addTab(chart_tools_tab, "图层导航")
    center_layout.addWidget(chart_controls_tabs)
    window.overview_primary_chart_tabs = QTabWidget()
    window.overview_primary_chart_tabs.setObjectName("compactInfoTabs")
    window.overview_daily_chart_page = QWidget()
    window.overview_daily_chart_layout = QVBoxLayout(window.overview_daily_chart_page)
    window.overview_daily_chart_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_daily_chart_layout.setSpacing(0)
    window.daily_chart_view = chart_view_cls()
    _configure_chart_view(window.daily_chart_view, min_height=360)
    window.overview_daily_chart_layout.addWidget(window.daily_chart_view)
    window.overview_intraday_chart_page = QWidget()
    window.overview_intraday_chart_layout = QVBoxLayout(window.overview_intraday_chart_page)
    window.overview_intraday_chart_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_intraday_chart_layout.setSpacing(0)
    window.overview_primary_chart_tabs.addTab(window.overview_daily_chart_page, "日线主图")
    window.overview_primary_chart_tabs.addTab(window.overview_intraday_chart_page, "分时快照")
    center_layout.addWidget(window.overview_primary_chart_tabs, stretch=6)
    mini_chart_row = QTabWidget()
    mini_chart_row.setObjectName("compactInfoTabs")
    window.overview_mini_chart_tabs = mini_chart_row
    window.fund_chart_view = chart_view_cls()
    _configure_chart_view(window.fund_chart_view, min_height=200)
    mini_chart_row.addTab(window.fund_chart_view, "资金强度")
    window.momentum_chart_view = chart_view_cls()
    _configure_chart_view(window.momentum_chart_view, min_height=200)
    mini_chart_row.addTab(window.momentum_chart_view, "动量节奏")
    window.indicator_chart_view = chart_view_cls()
    _configure_chart_view(window.indicator_chart_view, min_height=200)
    mini_chart_row.addTab(window.indicator_chart_view, "指标副图")
    center_layout.addWidget(mini_chart_row, stretch=2)
    window.price_chart_view = window.daily_chart_view
    window.volume_chart_view = window.fund_chart_view
    pool_box = QGroupBox("机会股票池")
    pool_box.setObjectName("opportunityPoolBox")
    pool_box.setProperty("pageTone", "overview")
    pool_layout = QVBoxLayout(pool_box)
    pool_layout.setContentsMargins(14, 14, 14, 14)
    pool_layout.setSpacing(12)
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
    right_panel.setObjectName("overviewRightPanel")
    right_panel.setMinimumWidth(428)
    window.overview_right_panel = right_panel
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(10)
    leaderboard_box = QGroupBox("掘龙榜")
    leaderboard_box.setObjectName("leaderboardBox")
    leaderboard_box.setProperty("pageTone", "overview")
    leaderboard_box.setProperty("surfaceRole", "analysis")
    leaderboard_layout = QVBoxLayout(leaderboard_box)
    leaderboard_layout.setContentsMargins(12, 14, 12, 14)
    leaderboard_layout.setSpacing(14)
    window.market_leaderboard_text = QTextEdit()
    window.market_leaderboard_text.setReadOnly(True)
    window.market_leaderboard_text.hide()
    window.market_leaderboard_text.setObjectName("marketNotePanel")
    leaderboard_layout.addWidget(window.market_leaderboard_text)
    window.market_leaderboard_cards = [leaderboard_card_cls() for _ in range(3)]
    for card in window.market_leaderboard_cards:
        leaderboard_layout.addWidget(card)
    overview_summary_box = QGroupBox("主控摘要")
    overview_summary_box.setObjectName("overviewSummaryBox")
    window.overview_summary_box = overview_summary_box
    window._style_terminal_panel(overview_summary_box)
    overview_summary_box.setProperty("pageTone", "overview")
    overview_summary_box.setProperty("surfaceRole", "metric-band")
    overview_summary_layout = QVBoxLayout(overview_summary_box)
    overview_summary_layout.setContentsMargins(14, 14, 14, 14)
    overview_summary_layout.setSpacing(6)
    overview_summary_band = AdaptivePanelGrid(min_item_width=190, compact_item_width=168, max_columns=2)
    overview_summary_band.setObjectName("overviewSummaryBand")
    overview_summary_band.set_grid_spacing(10, 10)
    window.overview_summary_cards = {
        "theme": compact_summary_card_cls("主线", "#c792ea"),
        "source": compact_summary_card_cls("催化", "#7ed7ff"),
        "capital": compact_summary_card_cls("资金", "#25d07f"),
        "decision": compact_summary_card_cls("决策", "#ff9f43"),
    }
    for key in ["theme", "source", "capital", "decision"]:
        overview_summary_band.add_panel(window.overview_summary_cards[key])
    overview_summary_layout.addWidget(overview_summary_band)
    right_layout.addWidget(leaderboard_box, stretch=5)
    window.right_intel_tabs = QTabWidget()
    window.right_intel_tabs.setObjectName("compactInfoTabs")
    right_tab_bar = window.right_intel_tabs.tabBar()
    right_tab_bar.setUsesScrollButtons(False)
    right_tab_bar.setExpanding(True)
    right_tab_bar.setElideMode(Qt.ElideRight)
    right_tab_bar.setDocumentMode(True)
    right_layout.addWidget(window.right_intel_tabs, stretch=4)
    right_summary_box = QGroupBox("主题摘要")
    right_summary_box.setObjectName("themeSummaryBox")
    right_summary_box.setProperty("pageTone", "overview")
    right_summary_box.setProperty("surfaceRole", "analysis")
    right_summary_layout = QVBoxLayout(right_summary_box)
    right_summary_layout.setContentsMargins(14, 14, 14, 14)
    right_summary_layout.setSpacing(10)
    window.market_theme_brief_text = QTextEdit()
    window.market_theme_brief_text.setReadOnly(True)
    window.market_theme_brief_text.setObjectName("marketNotePanel")
    window.market_theme_brief_text.setProperty("panelTone", "theme")
    window.market_theme_brief_text.setMinimumHeight(144)
    window.market_theme_brief_text.setMaximumHeight(176)
    right_summary_layout.addWidget(window.market_theme_brief_text, stretch=1)
    window.market_source_status_text = QTextEdit()
    window.market_source_status_text.setReadOnly(True)
    window.market_source_status_text.setObjectName("marketNotePanel")
    window.market_source_status_text.setProperty("panelTone", "system")
    window.market_source_status_text.setMinimumHeight(136)
    window.market_source_status_text.setMaximumHeight(164)
    right_summary_layout.addWidget(window.market_source_status_text, stretch=1)
    capital_box = QGroupBox("持仓与大盘")
    capital_box.setObjectName("capitalBox")
    capital_box.setProperty("pageTone", "overview")
    capital_box.setProperty("surfaceRole", "analysis")
    capital_layout = QVBoxLayout(capital_box)
    capital_layout.setContentsMargins(14, 14, 14, 14)
    capital_layout.setSpacing(10)
    window.market_capital_text = QTextEdit()
    window.market_capital_text.setReadOnly(True)
    window.market_capital_text.setObjectName("marketNotePanel")
    window.market_capital_text.setProperty("panelTone", "capital")
    window.market_capital_text.setMinimumHeight(156)
    window.market_capital_text.setMaximumHeight(192)
    capital_layout.addWidget(window.market_capital_text)
    decision_box = QGroupBox("买卖点结论")
    decision_box.setObjectName("decisionBox")
    decision_box.setProperty("pageTone", "overview")
    decision_box.setProperty("surfaceRole", "analysis")
    decision_layout = QVBoxLayout(decision_box)
    decision_layout.setContentsMargins(14, 14, 14, 14)
    decision_layout.setSpacing(10)
    window.market_decision_text = QTextEdit()
    window.market_decision_text.setReadOnly(True)
    window.market_decision_text.setObjectName("marketNotePanel")
    window.market_decision_text.setProperty("panelTone", "decision")
    window.market_decision_text.setMinimumHeight(164)
    window.market_decision_text.setMaximumHeight(204)
    decision_layout.addWidget(window.market_decision_text)
    window.right_intel_tabs.addTab(right_summary_box, "主题摘要")
    window.right_intel_tabs.addTab(capital_box, "资金画像")
    window.right_intel_tabs.addTab(decision_box, "交易决策")
    main_splitter.addWidget(right_panel)
    window._configure_splitter(main_splitter, [260, 1220, 360])
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
    window.news_source_combo = QComboBox()
    window.news_source_apply_button = QPushButton("载入当前消息源")
    window.news_source_hint_label = QLabel("当前来源：等待选择消息源。")
    window.news_source_hint_label.setObjectName("inlineHint")
    window.news_source_hint_label.setWordWrap(True)
    import_profile_button.clicked.connect(window.import_stock_profiles_csv)
    import_news_button.clicked.connect(window.import_news_catalysts_csv)
    import_theme_button.clicked.connect(window.import_theme_aliases_csv)
    edit_theme_button.clicked.connect(window.open_theme_alias_editor)
    refresh_button.clicked.connect(window.refresh_daily_pool)
    load_sample_button.clicked.connect(window.load_sample_universe)
    window.news_source_apply_button.clicked.connect(window.load_news_from_current_source)
    window.news_source_combo.currentIndexChanged.connect(lambda *_: window._on_news_source_changed())
    window._set_button_role(import_profile_button)
    window._set_button_role(import_news_button)
    window._set_button_role(import_theme_button)
    window._set_button_role(edit_theme_button)
    window._set_button_role(refresh_button, "accent")
    window._set_button_role(load_sample_button)
    window._set_button_role(window.news_source_apply_button, "tonal")
    window.news_source_apply_button.setMinimumHeight(40)
    if hasattr(window, "_populate_news_source_combo"):
        window._populate_news_source_combo()

    window.recommend_status_label = QLabel(RECOMMEND_DEFAULT_STATUS_TEXT)
    window.recommend_status_label.setObjectName("statusBanner")
    window.recommend_status_label.setProperty("pageTone", "recommend")
    window.recommend_status_label.setWordWrap(True)
    window.recommend_status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    layout.addWidget(window.recommend_status_label)
    window.recommend_message_toast_label = QLabel("等待新提醒")
    window.recommend_message_toast_label.setObjectName("workspaceFocusBanner")
    window.recommend_message_toast_label.setProperty("pageTone", "recommend")
    window.recommend_message_toast_label.setProperty("stateTone", "idle")
    window.recommend_message_toast_label.setWordWrap(True)
    window.recommend_message_toast_label.hide()
    layout.addWidget(window.recommend_message_toast_label)

    recommend_empty_box = QGroupBox("快速进入")
    window._style_terminal_panel(recommend_empty_box)
    recommend_empty_box.setObjectName("emptyStatePanel")
    recommend_empty_box.setProperty("surfaceRole", "analysis")
    recommend_empty_box.setProperty("pageTone", "recommend")
    recommend_empty_layout = QVBoxLayout(recommend_empty_box)
    recommend_empty_layout.setContentsMargins(12, 10, 12, 10)
    recommend_empty_layout.setSpacing(6)
    window.recommend_empty_title = QLabel(RECOMMEND_DEFAULT_EMPTY_TITLE)
    window.recommend_empty_title.setObjectName("emptyStateTitle")
    window.recommend_empty_title.setWordWrap(True)
    window.recommend_empty_title.setMinimumHeight(0)
    window.recommend_empty_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    recommend_empty_layout.addWidget(window.recommend_empty_title)
    window.recommend_empty_hint = QLabel(RECOMMEND_DEFAULT_EMPTY_HINT)
    window.recommend_empty_hint.setWordWrap(True)
    window.recommend_empty_hint.setObjectName("emptyStateHint")
    window.recommend_empty_hint.setMinimumHeight(0)
    window.recommend_empty_hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    recommend_empty_layout.addWidget(window.recommend_empty_hint)
    window.recommend_empty_meta = QLabel(RECOMMEND_DEFAULT_EMPTY_META)
    window.recommend_empty_meta.setObjectName("emptyStateMeta")
    window.recommend_empty_meta.setWordWrap(True)
    window.recommend_empty_meta.setMinimumHeight(0)
    window.recommend_empty_meta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    recommend_empty_layout.addWidget(window.recommend_empty_meta)
    recommend_empty_action_row = QHBoxLayout()
    recommend_empty_action_row.setContentsMargins(0, 0, 0, 0)
    recommend_empty_action_row.setSpacing(8)
    window.recommend_empty_sample_button = QPushButton(RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
    window.recommend_empty_refresh_button = QPushButton(RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)
    window._set_button_role(window.recommend_empty_sample_button, "accent")
    window._set_button_role(window.recommend_empty_refresh_button, "ghost")
    window.recommend_empty_sample_button.setMinimumHeight(38)
    window.recommend_empty_refresh_button.setMinimumHeight(38)
    window.recommend_empty_sample_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    window.recommend_empty_refresh_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
    window.recommend_empty_sample_button.clicked.connect(window.load_sample_universe)
    window.recommend_empty_refresh_button.clicked.connect(window.refresh_daily_pool)
    recommend_empty_action_row.addWidget(window.recommend_empty_sample_button)
    recommend_empty_action_row.addWidget(window.recommend_empty_refresh_button)
    recommend_empty_action_row.addStretch(1)
    recommend_empty_layout.addLayout(recommend_empty_action_row)
    window.recommend_empty_action_row = recommend_empty_action_row
    window.recommend_empty_box = recommend_empty_box
    layout.addWidget(window.recommend_empty_box)

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
    window.recommend_action_buttons = [
        recommend_to_broker_button,
        plan_to_broker_button,
        focus_pending_button,
        retry_failed_button,
        push_priority_button,
    ]
    recommend_to_broker_button.clicked.connect(window.push_selected_recommendation_to_broker)
    plan_to_broker_button.clicked.connect(window.push_selected_trade_plan_to_broker)
    focus_pending_button.clicked.connect(window.focus_next_pending_recommendation)
    retry_failed_button.clicked.connect(window.review_failed_recommendation)
    push_priority_button.clicked.connect(window.push_priority_recommendation_to_broker)
    window.recommend_action_more_button = QPushButton("更多")
    window._set_button_role(window.recommend_action_more_button, "ghost")
    window.recommend_action_more_button.setMinimumHeight(40)
    window.recommend_action_more_button.setToolTip("打开更多送审相关动作。")
    window.recommend_action_more_button.hide()

    controls_deck = AdaptivePanelGrid(min_item_width=360, compact_item_width=300, max_columns=3)
    controls_deck.setObjectName("recommendControlDeck")
    controls_deck.setProperty("pageTone", "recommend")
    controls_deck.set_grid_spacing(12, 12)
    data_box = QGroupBox("数据接入")
    filter_box = QGroupBox("主线筛选")
    action_box = QGroupBox("送审动作")
    window._style_terminal_panel(data_box, filter_box, action_box)
    data_box.setObjectName("workspaceToolPanel")
    filter_box.setObjectName("workspaceToolPanel")
    action_box.setObjectName("workspaceToolPanel")
    data_box.setProperty("pageTone", "recommend")
    filter_box.setProperty("pageTone", "recommend")
    action_box.setProperty("pageTone", "recommend")
    data_box.setProperty("surfaceRole", "analysis")
    filter_box.setProperty("surfaceRole", "analysis")
    action_box.setProperty("surfaceRole", "analysis")

    data_layout = QVBoxLayout(data_box)
    data_layout.setContentsMargins(14, 14, 14, 14)
    data_layout.setSpacing(10)
    news_source_row = QHBoxLayout()
    news_source_row.setSpacing(8)
    news_source_row.addWidget(QLabel("消息源"))
    news_source_row.addWidget(window.news_source_combo, stretch=1)
    news_source_row.addWidget(window.news_source_apply_button)
    data_layout.addLayout(news_source_row)
    data_layout.addWidget(window.news_source_hint_label)
    data_grid = QGridLayout()
    data_grid.setHorizontalSpacing(10)
    data_grid.setVerticalSpacing(10)
    for index, button in enumerate(
        [import_profile_button, import_news_button, import_theme_button, edit_theme_button, refresh_button, load_sample_button]
    ):
        button.setMinimumHeight(40)
        data_grid.addWidget(button, index // 3, index % 3)
    data_layout.addLayout(data_grid)
    filter_layout = QGridLayout(filter_box)
    filter_layout.setHorizontalSpacing(12)
    filter_layout.setVerticalSpacing(10)
    filter_layout.setContentsMargins(14, 14, 14, 14)
    filter_layout.addWidget(QLabel("主线筛选"), 0, 0)
    filter_layout.addWidget(window.recommend_theme_combo, 0, 1)
    filter_layout.addWidget(QLabel("策略"), 0, 2)
    filter_layout.addWidget(window.recommend_strategy_combo, 0, 3)
    filter_layout.addWidget(QLabel("动作"), 1, 0)
    filter_layout.addWidget(window.recommend_action_combo, 1, 1)
    filter_layout.addWidget(QLabel("状态"), 1, 2)
    filter_layout.addWidget(window.recommend_execution_combo, 1, 3)
    for column in range(4):
        filter_layout.setColumnStretch(column, 1 if column % 2 else 0)

    action_layout = QGridLayout(action_box)
    action_layout.setHorizontalSpacing(10)
    action_layout.setVerticalSpacing(10)
    action_layout.setContentsMargins(14, 14, 14, 14)
    for index, button in enumerate(
        [recommend_to_broker_button, plan_to_broker_button, focus_pending_button, retry_failed_button, push_priority_button]
    ):
        button.setMinimumHeight(40)
        action_layout.addWidget(button, index // 2, index % 2)
    action_layout.addWidget(window.recommend_action_more_button, 3, 0, 1, 2)
    action_layout.setColumnStretch(0, 1)
    action_layout.setColumnStretch(1, 1)

    controls_deck.add_panel(data_box)
    controls_deck.add_panel(filter_box)
    controls_deck.add_panel(action_box)
    recommend_controls_toggle_row = QHBoxLayout()
    recommend_controls_toggle_row.setContentsMargins(0, 0, 0, 0)
    recommend_controls_toggle_row.setSpacing(10)
    window.recommend_controls_toggle_button = QPushButton("展开推荐控制台")
    window._set_button_role(window.recommend_controls_toggle_button, "ghost")
    window.recommend_controls_toggle_button.setMinimumHeight(40)
    window.recommend_controls_toggle_button.clicked.connect(window.toggle_recommend_controls_panel)
    window.recommend_controls_status_label = QLabel("首屏优先看焦点、送审和结论；数据接入与筛选默认收起。")
    window.recommend_controls_status_label.setObjectName("inlineHint")
    window.recommend_controls_status_label.setProperty("pageTone", "recommend")
    window.recommend_controls_status_label.setWordWrap(True)
    window.recommend_controls_status_label.setMinimumHeight(42)
    recommend_controls_toggle_row.addWidget(window.recommend_controls_toggle_button)
    recommend_controls_toggle_row.addWidget(window.recommend_controls_status_label, stretch=1)
    recommend_controls_drawer = QFrame()
    recommend_controls_drawer.setObjectName("recommendControlsDrawer")
    recommend_controls_drawer.setProperty("actionRow", True)
    recommend_controls_drawer_layout = QVBoxLayout(recommend_controls_drawer)
    recommend_controls_drawer_layout.setContentsMargins(14, 14, 14, 14)
    recommend_controls_drawer_layout.setSpacing(8)
    recommend_controls_drawer_layout.addWidget(controls_deck)
    window.recommend_controls_drawer = recommend_controls_drawer
    recommend_controls_section = QWidget()
    recommend_controls_section.setObjectName("recommendControlsSection")
    recommend_controls_section.setProperty("pageTone", "recommend")
    recommend_controls_section_layout = QVBoxLayout(recommend_controls_section)
    recommend_controls_section_layout.setContentsMargins(0, 0, 0, 0)
    recommend_controls_section_layout.setSpacing(8)
    recommend_controls_section_layout.addLayout(recommend_controls_toggle_row)
    recommend_controls_section_layout.addWidget(recommend_controls_drawer)
    window.recommend_controls_section = recommend_controls_section

    recommend_focus_cards_box = QGroupBox("当前焦点")
    window.recommend_focus_cards_box = recommend_focus_cards_box
    window._style_terminal_panel(recommend_focus_cards_box)
    recommend_focus_cards_box.setProperty("surfaceRole", "metric-band")
    recommend_focus_cards_box.setProperty("pageTone", "recommend")
    recommend_focus_cards_layout = QVBoxLayout(recommend_focus_cards_box)
    recommend_focus_cards_layout.setContentsMargins(12, 12, 12, 12)
    recommend_focus_cards_layout.setSpacing(0)
    recommend_focus_cards_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=184, max_columns=4)
    recommend_focus_cards_band.setObjectName("recommendFocusCardsBand")
    recommend_focus_cards_band.set_grid_spacing(10, 10)
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
        recommend_focus_cards_band.add_panel(card)
    recommend_focus_cards_layout.addWidget(recommend_focus_cards_band)
    layout.addWidget(recommend_focus_cards_box)

    dispatch_splitter = QSplitter(Qt.Horizontal)
    window.recommend_dispatch_splitter = dispatch_splitter
    dispatch_splitter.setProperty("pageTone", "recommend")
    dispatch_splitter.setChildrenCollapsible(False)
    dispatch_box = QGroupBox("盘中分发")
    focus_review_box = QGroupBox("单票审查")
    queue_box = QGroupBox("执行队列")
    window._style_terminal_panel(dispatch_box, focus_review_box, queue_box)
    dispatch_box.setProperty("surfaceRole", "analysis")
    focus_review_box.setProperty("surfaceRole", "analysis")
    queue_box.setProperty("surfaceRole", "analysis")
    dispatch_box.setProperty("pageTone", "recommend")
    focus_review_box.setProperty("pageTone", "recommend")
    queue_box.setProperty("pageTone", "recommend")

    dispatch_layout = QVBoxLayout(dispatch_box)
    dispatch_layout.setContentsMargins(12, 12, 12, 12)
    dispatch_layout.setSpacing(10)
    window.recommend_dispatch_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_dispatch_text,
        tone="dispatch",
        min_height=168,
        max_height=228,
        seed_text="先看单票结论，再扫执行节奏。",
    )
    dispatch_layout.addWidget(window.recommend_dispatch_text)

    focus_review_layout = QVBoxLayout(focus_review_box)
    focus_review_layout.setContentsMargins(12, 12, 12, 12)
    focus_review_layout.setSpacing(10)
    window.recommend_focus_review_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_focus_review_text,
        tone="focus-review",
        min_height=182,
        max_height=244,
        seed_text="这里只保留价位、风险和复核重点。",
    )
    focus_review_layout.addWidget(window.recommend_focus_review_text)
    focus_review_action_row = QHBoxLayout()
    focus_review_action_row.setContentsMargins(0, 2, 0, 0)
    focus_review_action_row.setSpacing(10)
    window.recommend_news_source_button = QPushButton("查看消息原文")
    window.recommend_news_detail_button = QPushButton("查看消息详情")
    window.recommend_ai_review_button = QPushButton("AI评测当前焦点")
    window._set_button_role(window.recommend_news_source_button, "ghost")
    window._set_button_role(window.recommend_news_detail_button, "ghost")
    window._set_button_role(window.recommend_ai_review_button, "tonal")
    window.recommend_news_source_button.setToolTip(window._news_source_button_base_tooltip())
    window.recommend_news_detail_button.setToolTip(window._news_detail_button_base_tooltip())
    window.recommend_ai_review_button.setToolTip("调用 GPT-5.4 对当前焦点票做单票复核。")
    window.recommend_news_source_button.clicked.connect(window.open_selected_recommend_news_source)
    window.recommend_news_detail_button.clicked.connect(window.open_selected_recommend_news_detail)
    window.recommend_ai_review_button.clicked.connect(window.run_ai_review_for_selected_recommendation)
    focus_review_action_row.addWidget(window.recommend_news_source_button)
    focus_review_action_row.addWidget(window.recommend_news_detail_button)
    focus_review_action_row.addWidget(window.recommend_ai_review_button)
    focus_review_action_row.addStretch(1)
    focus_review_layout.addLayout(focus_review_action_row)

    queue_layout = QVBoxLayout(queue_box)
    queue_layout.setContentsMargins(12, 12, 12, 12)
    queue_layout.setSpacing(10)
    window.recommend_queue_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_queue_text,
        tone="queue",
        min_height=168,
        max_height=228,
        seed_text="这里只看待复核、已送审和失败回看。",
    )
    queue_layout.addWidget(window.recommend_queue_text)

    dispatch_splitter.addWidget(dispatch_box)
    dispatch_splitter.addWidget(focus_review_box)
    dispatch_splitter.addWidget(queue_box)
    window._configure_splitter(dispatch_splitter, [340, 460, 300])

    summary_splitter = QSplitter(Qt.Horizontal)
    window.recommend_summary_splitter = summary_splitter
    summary_splitter.setProperty("pageTone", "recommend")
    summary_splitter.setChildrenCollapsible(False)
    theme_box = QGroupBox("题材热度")
    leader_box = QGroupBox("龙头榜")
    window._style_terminal_panel(theme_box, leader_box)
    theme_box.setProperty("surfaceRole", "analysis")
    leader_box.setProperty("surfaceRole", "analysis")
    theme_box.setProperty("pageTone", "recommend")
    leader_box.setProperty("pageTone", "recommend")

    theme_layout = QVBoxLayout(theme_box)
    theme_layout.setContentsMargins(12, 12, 12, 12)
    theme_layout.setSpacing(10)
    window.theme_heat_table = build_table(["题材", "热度", "延续", "窗口", "分歧", "消息", "龙头数", "排序", "风险"])
    window.theme_heat_table.verticalHeader().setDefaultSectionSize(42)
    window.theme_heat_table.setMinimumHeight(280)
    window.theme_heat_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.theme_heat_table.itemSelectionChanged.connect(window._on_theme_heat_selection_changed)
    theme_layout.addWidget(window.theme_heat_table)

    leader_layout = QVBoxLayout(leader_box)
    leader_layout.setContentsMargins(12, 12, 12, 12)
    leader_layout.setSpacing(10)
    window.leader_table = build_table(["名称", "ID", "题材", "级别", "角色", "窗口", "风险", "龙头层级", "动作", "说明"])
    window.leader_table.verticalHeader().setDefaultSectionSize(46)
    window.leader_table.setMinimumHeight(280)
    window.leader_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.leader_table.itemSelectionChanged.connect(window._on_leader_table_selection_changed)
    leader_layout.addWidget(window.leader_table)

    summary_splitter.addWidget(theme_box)
    summary_splitter.addWidget(leader_box)
    window._configure_splitter(summary_splitter, [410, 790])

    pool_box = QGroupBox("主线看板")
    window.recommend_pool_box = pool_box
    window._style_terminal_panel(pool_box)
    pool_box.setProperty("surfaceRole", "analysis")
    pool_box.setProperty("pageTone", "recommend")
    pool_layout = QVBoxLayout(pool_box)
    pool_layout.setContentsMargins(12, 12, 12, 12)
    pool_layout.setSpacing(10)
    window.daily_pool_focus_label = QLabel(RECOMMEND_DEFAULT_FOCUS_TEXT)
    window.daily_pool_focus_label.setObjectName("focusStateLabel")
    window.daily_pool_focus_label.setProperty("pageTone", "recommend")
    window.daily_pool_focus_label.setWordWrap(True)
    pool_layout.addWidget(window.daily_pool_focus_label)
    window.daily_pool_table = _build_recommend_daily_pool_table(window, build_table)
    pool_layout.addWidget(window.daily_pool_table)

    section_hint = QLabel("推荐成交台只保留 3 个核心动作：选焦点、过门槛、进交易。辅助洞察按需展开。")
    section_hint.setObjectName("inlineHint")
    window.recommend_section_hint = section_hint

    decision_summary_box = QGroupBox("单票成交卡")
    window.recommend_decision_summary_box = decision_summary_box
    window._style_terminal_panel(decision_summary_box)
    decision_summary_box.setProperty("surfaceRole", "spotlight")
    decision_summary_box.setProperty("pageTone", "recommend")
    decision_summary_layout = QVBoxLayout(decision_summary_box)
    decision_summary_layout.setContentsMargins(14, 14, 14, 14)
    decision_summary_layout.setSpacing(10)
    window.recommend_decision_summary_label = QLabel("先选中一只股票，再判断是否具备成交条件、要不要进入送审。")
    window.recommend_decision_summary_label.setObjectName("focusStateLabel")
    window.recommend_decision_summary_label.setProperty("pageTone", "recommend")
    window.recommend_decision_summary_label.setWordWrap(True)
    decision_summary_layout.addWidget(window.recommend_decision_summary_label)
    window.recommend_decision_summary_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_decision_summary_text,
        tone="decision",
        min_height=208,
        max_height=286,
        seed_text=(
            "单票成交卡\n\n"
            "这里会先给出当前结论、送审门槛、关键价位、失效条件和下一步动作。\n"
            "你不需要先翻完所有卡片，再决定是否推进到送审和交易。"
        ),
    )
    decision_summary_layout.addWidget(window.recommend_decision_summary_text)
    decision_action_row = QHBoxLayout()
    decision_action_row.setContentsMargins(0, 2, 0, 0)
    decision_action_row.setSpacing(10)
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
    layout.addWidget(pool_box, stretch=3)
    layout.addWidget(recommend_controls_section)
    layout.addWidget(section_hint)
    layout.addWidget(dispatch_splitter, stretch=2)
    layout.addWidget(summary_splitter, stretch=2)

    stage_control_row = QHBoxLayout()
    stage_control_row.setContentsMargins(0, 2, 0, 0)
    stage_control_row.setSpacing(10)
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
    window.recommend_stage_container.setObjectName("workspaceStage")
    window.recommend_stage_container.setProperty("pageTone", "recommend")
    recommend_stage_layout = QVBoxLayout(window.recommend_stage_container)
    recommend_stage_layout.setContentsMargins(0, 0, 0, 0)
    recommend_stage_layout.setSpacing(14)
    execution_stage = QWidget()
    execution_stage.setObjectName("workspaceStage")
    execution_stage.setProperty("pageTone", "recommend")
    decision_stage = QWidget()
    decision_stage.setObjectName("workspaceStage")
    decision_stage.setProperty("pageTone", "recommend")
    recap_stage = QWidget()
    recap_stage.setObjectName("workspaceStage")
    recap_stage.setProperty("pageTone", "recommend")
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
    bucket_action_row.setContentsMargins(0, 2, 0, 0)
    bucket_action_row.setSpacing(10)
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
    bucket_splitter.setProperty("pageTone", "recommend")
    bucket_splitter.setChildrenCollapsible(False)
    core_bucket_box = QGroupBox("高优先池")
    watch_bucket_box = QGroupBox("观察池")
    risk_bucket_box = QGroupBox("风险池")
    window._style_terminal_panel(core_bucket_box, watch_bucket_box, risk_bucket_box)
    core_bucket_box.setProperty("surfaceRole", "analysis")
    watch_bucket_box.setProperty("surfaceRole", "analysis")
    risk_bucket_box.setProperty("surfaceRole", "analysis")
    core_bucket_box.setProperty("pageTone", "recommend")
    watch_bucket_box.setProperty("pageTone", "recommend")
    risk_bucket_box.setProperty("pageTone", "recommend")

    core_bucket_layout = QVBoxLayout(core_bucket_box)
    core_bucket_layout.setContentsMargins(12, 12, 12, 12)
    core_bucket_layout.setSpacing(10)
    window.recommend_core_bucket_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_core_bucket_text,
        tone="buy",
        min_height=176,
        max_height=236,
        seed_text="继续跟。先执行。",
    )
    core_bucket_layout.addWidget(window.recommend_core_bucket_text)

    watch_bucket_layout = QVBoxLayout(watch_bucket_box)
    watch_bucket_layout.setContentsMargins(12, 12, 12, 12)
    watch_bucket_layout.setSpacing(10)
    window.recommend_watch_bucket_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_watch_bucket_text,
        tone="watch",
        min_height=176,
        max_height=236,
        seed_text="只观察。先盯信号。",
    )
    watch_bucket_layout.addWidget(window.recommend_watch_bucket_text)

    risk_bucket_layout = QVBoxLayout(risk_bucket_box)
    risk_bucket_layout.setContentsMargins(12, 12, 12, 12)
    risk_bucket_layout.setSpacing(10)
    window.recommend_risk_bucket_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_risk_bucket_text,
        tone="risk",
        min_height=176,
        max_height=236,
        seed_text="防切换。先管风险。",
    )
    risk_bucket_layout.addWidget(window.recommend_risk_bucket_text)

    bucket_splitter.addWidget(core_bucket_box)
    bucket_splitter.addWidget(watch_bucket_box)
    bucket_splitter.addWidget(risk_bucket_box)
    window._configure_splitter(bucket_splitter, [420, 420, 420])
    execution_layout.addWidget(bucket_splitter, stretch=2)

    strategy_pack_box = QGroupBox("战法工作台")
    window._style_terminal_panel(strategy_pack_box)
    strategy_pack_box.setProperty("surfaceRole", "metric-band")
    strategy_pack_box.setProperty("pageTone", "recommend")
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
    strategy_detail_box.setProperty("surfaceRole", "analysis")
    strategy_detail_box.setProperty("pageTone", "recommend")
    strategy_detail_box.setMinimumHeight(316)
    strategy_detail_layout = QVBoxLayout(strategy_detail_box)
    strategy_detail_layout.setContentsMargins(12, 12, 12, 12)
    strategy_detail_layout.setSpacing(10)
    strategy_detail_header = QHBoxLayout()
    strategy_detail_header.setContentsMargins(0, 0, 0, 0)
    strategy_detail_header.setSpacing(10)
    window.strategy_detail_combo = QComboBox()
    for name in strategy_score_fields:
        window.strategy_detail_combo.addItem(name)
    window.strategy_detail_combo.currentTextChanged.connect(window._refresh_strategy_focus_detail)
    strategy_detail_header.addWidget(QLabel("当前战法"))
    strategy_detail_header.addWidget(window.strategy_detail_combo)
    strategy_detail_header.addStretch(1)
    strategy_detail_layout.addLayout(strategy_detail_header)
    window.strategy_detail_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.strategy_detail_text,
        tone="theme",
        min_height=96,
        max_height=120,
        seed_text="等待推荐池。",
    )
    strategy_detail_layout.addWidget(window.strategy_detail_text)
    decision_layout.addWidget(strategy_detail_box, stretch=1)

    action_flow_box = QGroupBox("决策流程")
    window._style_terminal_panel(action_flow_box)
    action_flow_box.setProperty("surfaceRole", "metric-band")
    action_flow_box.setProperty("pageTone", "recommend")
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
    priority_box.setProperty("surfaceRole", "metric-band")
    priority_box.setProperty("pageTone", "recommend")
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
    alert_box.setProperty("surfaceRole", "metric-band")
    alert_box.setProperty("pageTone", "recommend")
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
    strategy_path_box.setProperty("surfaceRole", "analysis")
    strategy_path_box.setProperty("pageTone", "recommend")
    strategy_path_box.setMinimumHeight(260)
    strategy_path_layout = QVBoxLayout(strategy_path_box)
    strategy_path_layout.setContentsMargins(12, 12, 12, 12)
    strategy_path_layout.setSpacing(10)
    window.strategy_path_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.strategy_path_text,
        tone="theme",
        min_height=170,
        max_height=236,
        seed_text="等待推荐池。",
    )
    strategy_path_layout.addWidget(window.strategy_path_text)
    decision_layout.addWidget(strategy_path_box, stretch=1)

    summary_cards_box = QGroupBox("决策摘要")
    window._style_terminal_panel(summary_cards_box)
    summary_cards_box.setProperty("surfaceRole", "metric-band")
    summary_cards_box.setProperty("pageTone", "recommend")
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

    message_center_box = QGroupBox("统一消息中心")
    window._style_terminal_panel(message_center_box)
    message_center_box.setProperty("surfaceRole", "analysis")
    message_center_box.setProperty("pageTone", "recommend")
    message_center_layout = QVBoxLayout(message_center_box)
    message_center_layout.setContentsMargins(12, 12, 12, 12)
    message_center_layout.setSpacing(10)
    message_center_header = QHBoxLayout()
    message_center_header.setContentsMargins(0, 0, 0, 0)
    message_center_header.setSpacing(10)
    window.recommend_message_center_summary_label = QLabel("等待新事件")
    window.recommend_message_center_summary_label.setObjectName("focusStateLabel")
    window.recommend_message_center_summary_label.setProperty("pageTone", "recommend")
    window.recommend_message_center_summary_label.setWordWrap(True)
    window.recommend_message_center_filter_combo = QComboBox()
    for label, value in [
        ("全部", "all"),
        ("AI", "ai"),
        ("消息", "news"),
        ("交易", "trade"),
        ("系统", "system"),
    ]:
        window.recommend_message_center_filter_combo.addItem(label, value)
    if hasattr(window, "_on_recommend_message_center_filter_changed"):
        window.recommend_message_center_filter_combo.currentIndexChanged.connect(window._on_recommend_message_center_filter_changed)
    window.recommend_message_center_clear_button = QPushButton("清空")
    window._set_button_role(window.recommend_message_center_clear_button, "ghost")
    if hasattr(window, "clear_recommend_message_center"):
        window.recommend_message_center_clear_button.clicked.connect(window.clear_recommend_message_center)
    message_center_header.addWidget(window.recommend_message_center_summary_label, stretch=1)
    message_center_header.addWidget(window.recommend_message_center_filter_combo)
    message_center_header.addWidget(window.recommend_message_center_clear_button)
    message_center_layout.addLayout(message_center_header)
    window.recommend_message_center_table = build_table(["时间", "类型", "事件", "标的"])
    window.recommend_message_center_table.setObjectName("terminalTable")
    window.recommend_message_center_table.setProperty("pageTone", "recommend")
    window.recommend_message_center_table.setMinimumHeight(186)
    if hasattr(window, "_on_recommend_message_center_selection_changed"):
        window.recommend_message_center_table.itemSelectionChanged.connect(window._on_recommend_message_center_selection_changed)
    if hasattr(window, "open_selected_recommend_message_event"):
        window.recommend_message_center_table.itemDoubleClicked.connect(lambda *_args: window.open_selected_recommend_message_event())
    message_center_layout.addWidget(window.recommend_message_center_table)
    message_center_action_row = QHBoxLayout()
    message_center_action_row.setContentsMargins(0, 2, 0, 0)
    message_center_action_row.setSpacing(10)
    window.recommend_message_center_action_label = QLabel("建议动作：等待新事件")
    window.recommend_message_center_action_label.setObjectName("inlineHint")
    window.recommend_message_center_action_label.setWordWrap(True)
    window.recommend_message_center_symbol_button = QPushButton("定位股票")
    window.recommend_message_center_open_button = QPushButton("打开关联页")
    window._set_button_role(window.recommend_message_center_symbol_button, "tonal")
    window._set_button_role(window.recommend_message_center_open_button, "accent")
    if hasattr(window, "focus_selected_recommend_message_symbol"):
        window.recommend_message_center_symbol_button.clicked.connect(window.focus_selected_recommend_message_symbol)
    if hasattr(window, "open_selected_recommend_message_event"):
        window.recommend_message_center_open_button.clicked.connect(window.open_selected_recommend_message_event)
    message_center_action_row.addWidget(window.recommend_message_center_action_label, stretch=1)
    message_center_action_row.addWidget(window.recommend_message_center_symbol_button)
    message_center_action_row.addWidget(window.recommend_message_center_open_button)
    message_center_layout.addLayout(message_center_action_row)
    window.recommend_message_center_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_message_center_text,
        tone="system",
        min_height=132,
        max_height=188,
        seed_text="这里会汇总 AI 评测、消息源刷新、推荐池刷新和交易回执。",
    )
    message_center_layout.addWidget(window.recommend_message_center_text)
    recap_layout.addWidget(message_center_box, stretch=1)
    if hasattr(window, "_refresh_recommend_message_center"):
        window._refresh_recommend_message_center()

    detail_box = QGroupBox("主线说明")
    plan_box = QGroupBox("今日交易计划")
    pulse_box = QGroupBox("市场温度")
    holding_box = QGroupBox("持仓处理建议")
    window._style_terminal_panel(detail_box, plan_box, pulse_box, holding_box)
    for box in (detail_box, plan_box, pulse_box, holding_box):
        box.setProperty("surfaceRole", "analysis")
        box.setProperty("pageTone", "recommend")

    detail_layout = QVBoxLayout(detail_box)
    detail_layout.setContentsMargins(12, 12, 12, 12)
    detail_layout.setSpacing(10)
    window.daily_pool_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.daily_pool_text,
        tone="theme",
        min_height=220,
        max_height=292,
        seed_text=(
        "说明：\n"
        "- 主线：先看最强方向。\n"
        "- 位次：优先看前排。\n"
        "- 窗口：只看修复和加速。\n"
        "- 风险：转弱、退潮、假突破会降权。\n"
        "- 催化：更偏向能持续的消息与龙头企业。"
        ),
    )
    detail_layout.addWidget(window.daily_pool_text)

    plan_layout = QVBoxLayout(plan_box)
    plan_layout.setContentsMargins(12, 12, 12, 12)
    plan_layout.setSpacing(10)
    window.trade_plan_focus_label = QLabel("计划焦点：等待生成或选中")
    window.trade_plan_focus_label.setObjectName("focusStateLabel")
    window.trade_plan_focus_label.setProperty("pageTone", "broker")
    window.trade_plan_focus_label.setWordWrap(True)
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
    window.trade_plan_empty_actions.setProperty("actionRow", True)
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
    _configure_recommend_story_text(
        window,
        window.trade_plan_text,
        tone="dispatch",
        min_height=160,
        max_height=224,
        seed_text="先刷新主线，再生成今日交易计划。",
    )
    plan_layout.addWidget(window.trade_plan_text)

    pulse_layout = QVBoxLayout(pulse_box)
    pulse_layout.setContentsMargins(12, 12, 12, 12)
    pulse_layout.setSpacing(10)
    window.market_pulse_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.market_pulse_text,
        tone="capital",
        min_height=176,
        max_height=236,
        seed_text="等待推荐池生成后，再更新市场温度和仓位建议。",
    )
    pulse_layout.addWidget(window.market_pulse_text)

    holding_layout = QVBoxLayout(holding_box)
    holding_layout.setContentsMargins(12, 12, 12, 12)
    holding_layout.setSpacing(10)
    window.position_advice_table = build_table(
        ["名称", "ID", "交易码", "动作", "主线", "置信度", "现价", "成本", "盈亏", "处理"]
    )
    window.position_advice_table.setMinimumHeight(280)
    window.position_advice_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.position_advice_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.position_advice_table.itemSelectionChanged.connect(window._on_position_advice_selection_changed)
    holding_layout.addWidget(window.position_advice_table)
    window.position_advice_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.position_advice_text,
        tone="risk",
        min_height=168,
        max_height=236,
        seed_text="导入持仓后，这里会给出继续持有、减仓、退出或观察建议。",
    )
    holding_layout.addWidget(window.position_advice_text)

    middle = QSplitter(Qt.Horizontal)
    window.recommend_recap_middle_splitter = middle
    middle.setProperty("pageTone", "recommend")
    middle.setChildrenCollapsible(False)
    middle.addWidget(detail_box)
    middle.addWidget(plan_box)
    window._configure_splitter(middle, [350, 890])
    recap_layout.addWidget(middle, stretch=2)

    bottom = QSplitter(Qt.Horizontal)
    window.recommend_recap_bottom_splitter = bottom
    bottom.setProperty("pageTone", "recommend")
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(pulse_box)
    bottom.addWidget(holding_box)
    window._configure_splitter(bottom, [340, 900])
    recap_layout.addWidget(bottom, stretch=2)

    recommend_review_splitter = QSplitter(Qt.Horizontal)
    window.recommend_review_splitter = recommend_review_splitter
    recommend_review_splitter.setProperty("pageTone", "recommend")
    recommend_review_splitter.setChildrenCollapsible(False)
    recommend_review_box = QGroupBox("当日复盘")
    recommend_next_day_box = QGroupBox("次日策略")
    recommend_ai_review_box = QGroupBox("AI评测")
    window._style_terminal_panel(recommend_review_box, recommend_next_day_box, recommend_ai_review_box)
    recommend_review_box.setProperty("surfaceRole", "analysis")
    recommend_next_day_box.setProperty("surfaceRole", "analysis")
    recommend_ai_review_box.setProperty("surfaceRole", "analysis")
    recommend_review_box.setProperty("pageTone", "recommend")
    recommend_next_day_box.setProperty("pageTone", "recommend")
    recommend_ai_review_box.setProperty("pageTone", "recommend")

    recommend_review_layout = QVBoxLayout(recommend_review_box)
    recommend_review_layout.setContentsMargins(12, 12, 12, 12)
    recommend_review_layout.setSpacing(10)
    window.recommend_review_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_review_text,
        tone="watch",
        min_height=198,
        max_height=260,
        seed_text="复盘先看继续跟、只观察还是防切换。",
    )
    recommend_review_layout.addWidget(window.recommend_review_text)

    recommend_next_day_layout = QVBoxLayout(recommend_next_day_box)
    recommend_next_day_layout.setContentsMargins(12, 12, 12, 12)
    recommend_next_day_layout.setSpacing(10)
    window.recommend_next_day_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_next_day_text,
        tone="decision",
        min_height=198,
        max_height=260,
        seed_text="次日先看继续跟、只观察还是防切换。",
    )
    recommend_next_day_layout.addWidget(window.recommend_next_day_text)

    recommend_ai_review_layout = QVBoxLayout(recommend_ai_review_box)
    recommend_ai_review_layout.setContentsMargins(12, 12, 12, 12)
    recommend_ai_review_layout.setSpacing(10)
    window.recommend_ai_review_text = QTextEdit()
    _configure_recommend_story_text(
        window,
        window.recommend_ai_review_text,
        tone="focus-review",
        min_height=198,
        max_height=260,
        seed_text="AI评测会结合推荐、消息和单票上下文，给出一份外部模型复核意见。",
    )
    recommend_ai_review_layout.addWidget(window.recommend_ai_review_text)

    recommend_review_splitter.addWidget(recommend_review_box)
    recommend_review_splitter.addWidget(recommend_next_day_box)
    recommend_review_splitter.addWidget(recommend_ai_review_box)
    window._configure_splitter(recommend_review_splitter, [430, 430, 360])
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
    window.board_tool_action_row = control_row
    control_row.setSpacing(8)
    refresh_button = QPushButton("刷新打板池")
    plan_export_button = QPushButton("导出盘前交易计划")
    export_button = QPushButton("导出收盘复盘日报")
    window.auto_review_export_checkbox = QCheckBox("15:05 后自动导出复盘日报")
    window.auto_review_export_checkbox.setChecked(True)
    window._set_button_role(refresh_button, "accent")
    window._set_button_role(plan_export_button, "ghost")
    window._set_button_role(export_button)
    window.board_refresh_button = refresh_button
    window.board_plan_export_button = plan_export_button
    window.board_review_export_button = export_button
    window.board_tool_action_buttons = [refresh_button, plan_export_button, export_button]
    window.board_tool_more_button = QPushButton("更多")
    window._set_button_role(window.board_tool_more_button, "ghost")
    window.board_tool_more_button.setMinimumHeight(40)
    window.board_tool_more_button.setToolTip("打开更多打板专项动作。")
    window.board_tool_more_button.hide()
    refresh_button.clicked.connect(window._refresh_board_mode)
    plan_export_button.clicked.connect(window.export_daily_trade_plan_from_ui)
    export_button.clicked.connect(window.export_end_of_day_review_from_ui)
    control_row.addWidget(refresh_button)
    control_row.addWidget(plan_export_button)
    control_row.addWidget(export_button)
    control_row.addWidget(window.board_tool_more_button)
    control_row.addWidget(window.auto_review_export_checkbox)
    control_row.addStretch(1)
    tool_layout.addLayout(control_row, 0, 0)

    board_hint = QLabel("围绕高辨识度强势股，统一查看专项候选、回封监控、导出计划和收盘复盘。")
    board_hint.setObjectName("inlineHint")
    board_hint.setWordWrap(True)
    board_meta = QFrame()
    board_meta.setObjectName("boardMetaPanel")
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
    candidate_box.setProperty("pageTone", "board")
    monitor_box.setProperty("pageTone", "board")
    candidate_box.setProperty("surfaceRole", "analysis")
    monitor_box.setProperty("surfaceRole", "analysis")

    candidate_layout = QVBoxLayout(candidate_box)
    window.board_table = build_table(
        ["股票名称", "股票ID", "交易代码", "打板级别", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"]
    )
    window.board_table.horizontalHeader().setSectionResizeMode(header_view_cls.Stretch)
    candidate_layout.addWidget(window.board_table)
    window.board_text = QTextEdit()
    window.board_text.setReadOnly(True)
    window.board_text.setObjectName("marketNotePanel")
    window._style_terminal_console(window.board_text)
    window.board_text.setProperty("pageTone", "board")
    window.board_text.setProperty("panelTone", "decision")
    window.board_text.setMinimumHeight(176)
    window.board_text.setMaximumHeight(228)
    window.board_text.setPlainText("先生成每日推荐池，再生成打板候选。")
    candidate_layout.addWidget(window.board_text)

    monitor_layout = QVBoxLayout(monitor_box)
    window.board_monitor_table = build_table(
        ["股票名称", "股票ID", "交易代码", "监控状态", "强度", "连续性", "回封概率", "炸板风险", "动作建议", "备注"]
    )
    window.board_monitor_table.horizontalHeader().setSectionResizeMode(header_view_cls.Stretch)
    monitor_layout.addWidget(window.board_monitor_table)
    window.board_monitor_text = QTextEdit()
    window.board_monitor_text.setReadOnly(True)
    window.board_monitor_text.setObjectName("marketNotePanel")
    window._style_terminal_console(window.board_monitor_text)
    window.board_monitor_text.setProperty("pageTone", "board")
    window.board_monitor_text.setProperty("panelTone", "watch")
    window.board_monitor_text.setMinimumHeight(176)
    window.board_monitor_text.setMaximumHeight(228)
    window.board_monitor_text.setPlainText("专项监控会显示回封观察、炸板风险和强势连板候选。")
    monitor_layout.addWidget(window.board_monitor_text)
    board_workspace_splitter = QSplitter(Qt.Horizontal)
    board_workspace_splitter.setChildrenCollapsible(False)
    board_workspace_splitter.addWidget(candidate_box)
    board_workspace_splitter.addWidget(monitor_box)
    window._configure_splitter(board_workspace_splitter, [640, 620])
    window.board_workspace_splitter = board_workspace_splitter
    layout.addWidget(board_workspace_splitter, stretch=1)

def _build_config_workspace_core(window) -> None:
    layout = QVBoxLayout(window.config_tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    window.config_tab.setObjectName("configRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "\u7b56\u7565\u914d\u7f6e / \u5546\u4e1a\u5316",
            "\u7b56\u7565\u53c2\u6570\u4e0e\u6388\u6743\u72b6\u6001",
            "\u96c6\u4e2d\u7ba1\u7406\u4e3b\u7ebf\u9608\u503c\u3001\u9898\u6750\u6743\u91cd\u3001\u76d8\u524d\u6a21\u677f\u548c\u7248\u672c\u80fd\u529b\u8fb9\u754c\u3002",
            [("\u7b56\u7565", "\u4e3b\u7ebf\u4f18\u5148"), ("\u6388\u6743", window.state.license_plan or "TRIAL")],
        )
    )

    top = QSplitter(Qt.Horizontal)
    top.setChildrenCollapsible(False)

    strategy_box = QGroupBox("\u7b56\u7565\u53c2\u6570")
    strategy_box.setObjectName("configStrategyBox")
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
    window.theme_drop_reduce_checkbox = QCheckBox("\u9898\u6750\u6389\u961f\u65f6\u4f18\u5148\u51cf\u4ed3")
    window.theme_drop_reduce_checkbox.setChecked(window.state.strategy_theme_drop_reduce)
    window.auto_daily_plan_export_checkbox = QCheckBox("\u542f\u7528\u81ea\u52a8\u76d8\u524d\u62a5\u544a")
    window.auto_daily_plan_export_checkbox.setChecked(window.state.auto_daily_plan_export)
    window.daily_plan_focus_only_checkbox = QCheckBox("\u4ec5\u8f93\u51fa\u5173\u6ce8\u9898\u6750")
    window.daily_plan_focus_only_checkbox.setChecked(window.state.daily_plan_focus_only)
    window.daily_plan_template_combo = QComboBox()
    for key, label in [
        ("balanced", "\u5747\u8861\u6a21\u677f"),
        ("focus", "\u5173\u6ce8\u9898\u6750"),
        ("mainline", "\u4e3b\u7ebf\u4f18\u5148"),
        ("compact", "\u7d27\u51d1\u6a21\u677f"),
    ]:
        window.daily_plan_template_combo.addItem(label, key)
    for index in range(window.daily_plan_template_combo.count()):
        if window.daily_plan_template_combo.itemData(index) == window.state.daily_plan_template:
            window.daily_plan_template_combo.setCurrentIndex(index)
            break

    strategy_layout.addRow("\u4e3b\u7ebf\u524d\u6392 N", window.config_inputs["top_theme_limit"])
    strategy_layout.addRow("\u98ce\u9669\u6863\u4f4d", window.strategy_risk_profile_combo)
    strategy_layout.addRow("\u603b\u4ed3\u4f4d\u4e0a\u9650", window.config_inputs["max_total_exposure"])
    strategy_layout.addRow("\u76d8\u524d\u5019\u9009\u4e0a\u9650", window.config_inputs["daily_plan_candidate_limit"])
    strategy_layout.addRow("\u5173\u6ce8\u9898\u6750", window.focus_themes_input)
    strategy_layout.addRow("\u76d8\u524d\u6a21\u677f", window.daily_plan_template_combo)
    strategy_layout.addRow("", window.daily_plan_focus_only_checkbox)
    strategy_layout.addRow("", window.theme_drop_reduce_checkbox)
    strategy_layout.addRow("", window.auto_daily_plan_export_checkbox)
    top.addWidget(strategy_box)

    license_box = QGroupBox("\u6388\u6743\u4e0e\u72b6\u6001")
    license_box.setObjectName("configLicenseBox")
    window._style_terminal_panel(license_box)
    license_layout = QVBoxLayout(license_box)
    window.license_status_text = QTextEdit()
    window.license_status_text.setReadOnly(True)
    window._style_terminal_console(window.license_status_text)
    license_layout.addWidget(window.license_status_text)

    license_buttons = QGridLayout()
    license_buttons.setHorizontalSpacing(10)
    license_buttons.setVerticalSpacing(10)
    trial_button = QPushButton("\u5207\u6362\u8bd5\u7528\u7248")
    pro_button = QPushButton("\u5207\u6362\u4e13\u4e1a\u7248")
    enterprise_button = QPushButton("\u5207\u6362\u4f01\u4e1a\u7248")
    save_button = QPushButton("\u4fdd\u5b58\u5f53\u524d\u914d\u7f6e")
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

    snapshot_box = QGroupBox("\u98ce\u9669\u6863\u4f4d\u5feb\u7167")
    snapshot_box.setObjectName("configRiskSnapshotBox")
    window._style_terminal_panel(snapshot_box)
    snapshot_layout = QGridLayout(snapshot_box)
    snapshot_layout.setHorizontalSpacing(12)
    snapshot_layout.setVerticalSpacing(12)
    window.risk_snapshot_cards = {}
    for column, profile_key in enumerate((RISK_PROFILE_CONSERVATIVE, RISK_PROFILE_STANDARD, RISK_PROFILE_AGGRESSIVE)):
        card = QFrame()
        card.setObjectName("riskSnapshotCard")
        card.setProperty("actionRow", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(RISK_PROFILE_LABELS.get(profile_key, profile_key))
        title.setObjectName("workspaceTitle")
        detail = QLabel(risk_profile_brief(profile_key))
        detail.setObjectName("workspaceSubtitle")
        detail.setWordWrap(True)
        metrics = QLabel(risk_profile_snapshot_text(profile_key, getattr(window, "last_daily_pool_meta", {})))
        metrics.setObjectName("workspaceEyebrow")
        metrics.setWordWrap(True)
        flag = QLabel("\u5f53\u524d\u542f\u7528" if getattr(window.state, "strategy_risk_profile", "standard") == profile_key else "\u70b9\u51fb\u5207\u6362")
        flag.setObjectName("workspaceHeroStamp")
        action_button = QPushButton("\u5207\u6362\u5230\u6b64\u6863")
        window._set_button_role(action_button, "accent" if getattr(window.state, "strategy_risk_profile", "standard") == profile_key else "tonal")
        action_button.clicked.connect(lambda checked=False, current=profile_key: window.switch_strategy_risk_profile(current))
        detail_tooltip = f"{RISK_PROFILE_LABELS.get(profile_key, profile_key)}\u6863\uff1a{risk_profile_brief(profile_key)}"
        card.setToolTip(detail_tooltip)
        title.setToolTip(detail_tooltip)
        detail.setToolTip(detail_tooltip)
        metrics.setToolTip(detail_tooltip)
        flag.setToolTip(detail_tooltip)
        action_button.setToolTip(
            f"\u5207\u6362\u5230{RISK_PROFILE_LABELS.get(profile_key, profile_key)}\u6863\u5e76\u7acb\u5373\u5237\u65b0\u63a8\u8350\u6c60"
        )
        card_layout.addWidget(title)
        card_layout.addWidget(detail)
        card_layout.addWidget(metrics)
        card_layout.addWidget(flag)
        card_layout.addWidget(action_button)
        card_layout.addStretch(1)
        snapshot_layout.addWidget(card, 0, column)
        window.risk_snapshot_cards[profile_key] = {
            "card": card,
            "title": title,
            "detail": detail,
            "metrics": metrics,
            "flag": flag,
            "button": action_button,
        }
    layout.addWidget(snapshot_box, stretch=1)

    news_box = QGroupBox("消息源管理")
    news_box.setObjectName("configNewsSourceBox")
    window._style_terminal_panel(news_box)
    news_layout = QVBoxLayout(news_box)
    window.news_source_status_text = QTextEdit()
    window.news_source_status_text.setReadOnly(True)
    window._style_terminal_console(window.news_source_status_text)
    news_layout.addWidget(window.news_source_status_text)
    news_action_row = QHBoxLayout()
    news_action_row.setSpacing(10)
    news_apply_button = QPushButton("载入当前消息源")
    news_mixed_button = QPushButton("切到混合消息源")
    news_cninfo_button = QPushButton("切到巨潮公告源")
    news_sample_button = QPushButton("切到示例消息源")
    news_recommend_button = QPushButton("前往推荐页")
    window._set_button_role(news_apply_button, "accent")
    window._set_button_role(news_mixed_button, "tonal")
    window._set_button_role(news_cninfo_button, "tonal")
    window._set_button_role(news_sample_button, "tonal")
    window._set_button_role(news_recommend_button, "ghost")
    news_apply_button.clicked.connect(window.load_news_from_current_source)
    news_mixed_button.clicked.connect(lambda: (setattr(window, "news_source_provider_key", "mixed_api"), window._sync_news_source_controls(), window._load_news_source("mixed_api")))
    news_cninfo_button.clicked.connect(lambda: (setattr(window, "news_source_provider_key", "cninfo_api"), window._sync_news_source_controls(), window._load_news_source("cninfo_api")))
    news_sample_button.clicked.connect(lambda: window._load_news_source("sample"))
    news_recommend_button.clicked.connect(lambda: window._navigate_to_workspace("recommend", "daily_pool_table"))
    news_action_row.addWidget(news_apply_button)
    news_action_row.addWidget(news_mixed_button)
    news_action_row.addWidget(news_cninfo_button)
    news_action_row.addWidget(news_sample_button)
    news_action_row.addWidget(news_recommend_button)
    news_action_row.addStretch(1)
    news_layout.addLayout(news_action_row)
    layout.addWidget(news_box, stretch=1)

    ai_box = QGroupBox("AI评测")
    ai_box.setObjectName("configAiReviewBox")
    window._style_terminal_panel(ai_box)
    ai_layout = QVBoxLayout(ai_box)
    ai_form = QFormLayout()
    ai_form.setLabelAlignment(Qt.AlignRight)
    window.ai_review_base_url_input = QLineEdit(window.state.ai_review_base_url or "https://api.openai.com/v1")
    window.ai_review_api_key_input = QLineEdit(window.state.ai_review_api_key)
    window.ai_review_api_key_input.setEchoMode(QLineEdit.Password)
    window.ai_review_model_input = QLineEdit(window.state.ai_review_model or "gpt-5.4")
    window.ai_review_reasoning_effort_combo = QComboBox()
    for value, label in [
        ("minimal", "最省"),
        ("low", "低"),
        ("medium", "中"),
        ("high", "高"),
    ]:
        window.ai_review_reasoning_effort_combo.addItem(label, value)
    for index in range(window.ai_review_reasoning_effort_combo.count()):
        if window.ai_review_reasoning_effort_combo.itemData(index) == (window.state.ai_review_reasoning_effort or "medium"):
            window.ai_review_reasoning_effort_combo.setCurrentIndex(index)
            break
    window.ai_review_timeout_input = QLineEdit(str(window.state.ai_review_timeout_seconds or 45.0))
    window.ai_review_max_tokens_input = QLineEdit(str(window.state.ai_review_max_output_tokens or 900))
    window.ai_review_auto_run_checkbox = QCheckBox("推荐链路变化后自动重评当前焦点")
    window.ai_review_auto_on_news_checkbox = QCheckBox("消息源载入后自动触发")
    window.ai_review_auto_on_pool_checkbox = QCheckBox("推荐池刷新后自动触发")
    window.ai_review_auto_run_checkbox.setChecked(bool(getattr(window.state, "ai_review_auto_run_enabled", False)))
    window.ai_review_auto_on_news_checkbox.setChecked(bool(getattr(window.state, "ai_review_auto_run_on_news_refresh", True)))
    window.ai_review_auto_on_pool_checkbox.setChecked(bool(getattr(window.state, "ai_review_auto_run_on_pool_refresh", True)))
    window.ai_review_api_key_input.setPlaceholderText("sk-...")
    window.ai_review_base_url_input.setPlaceholderText("https://api.openai.com/v1")
    ai_form.addRow("Base URL", window.ai_review_base_url_input)
    ai_form.addRow("API Key", window.ai_review_api_key_input)
    ai_form.addRow("模型", window.ai_review_model_input)
    ai_form.addRow("推理强度", window.ai_review_reasoning_effort_combo)
    ai_form.addRow("超时(秒)", window.ai_review_timeout_input)
    ai_form.addRow("最大输出", window.ai_review_max_tokens_input)
    ai_layout.addLayout(ai_form)
    ai_toggle_row = QVBoxLayout()
    ai_toggle_row.setContentsMargins(0, 0, 0, 0)
    ai_toggle_row.setSpacing(6)
    ai_toggle_row.addWidget(window.ai_review_auto_run_checkbox)
    ai_toggle_row.addWidget(window.ai_review_auto_on_news_checkbox)
    ai_toggle_row.addWidget(window.ai_review_auto_on_pool_checkbox)
    ai_layout.addLayout(ai_toggle_row)
    window.ai_review_status_text = QTextEdit()
    window.ai_review_status_text.setReadOnly(True)
    window._style_terminal_console(window.ai_review_status_text)
    ai_layout.addWidget(window.ai_review_status_text)
    ai_action_row = QHBoxLayout()
    ai_action_row.setSpacing(10)
    ai_save_button = QPushButton("保存AI配置")
    ai_review_button = QPushButton("评测当前焦点")
    ai_recommend_button = QPushButton("前往推荐页")
    window._set_button_role(ai_save_button, "accent")
    window._set_button_role(ai_review_button, "tonal")
    window._set_button_role(ai_recommend_button, "ghost")
    ai_save_button.clicked.connect(window.save_ai_review_preferences)
    ai_review_button.clicked.connect(window.run_ai_review_for_selected_recommendation)
    ai_recommend_button.clicked.connect(lambda: window._navigate_to_workspace("recommend", "daily_pool_table"))
    ai_action_row.addWidget(ai_save_button)
    ai_action_row.addWidget(ai_review_button)
    ai_action_row.addWidget(ai_recommend_button)
    ai_action_row.addStretch(1)
    ai_layout.addLayout(ai_action_row)
    layout.addWidget(ai_box, stretch=1)

    notes_box = QGroupBox("\u8bf4\u660e")
    notes_box.setObjectName("configNotesBox")
    window._style_terminal_panel(notes_box)
    notes_layout = QVBoxLayout(notes_box)
    window.config_notes_text = QTextEdit()
    window.config_notes_text.setReadOnly(True)
    window._style_terminal_console(window.config_notes_text)
    window.config_notes_text.setPlainText(
        "\u914d\u7f6e\u8bf4\u660e\n\n"
        "- \u5f53\u524d\u914d\u7f6e\u4f1a\u76f4\u63a5\u5f71\u54cd\u6bcf\u65e5\u63a8\u8350\u3001\u76d8\u524d\u8ba1\u5212\u3001\u76d8\u4e2d\u76d1\u63a7\u548c\u7248\u672c\u80fd\u529b\u8fb9\u754c\u3002\n"
        "- \u4e3b\u7ebf\u9608\u503c\u8d8a\u9ad8\uff0c\u5f00\u4ed3\u8d8a\u504f\u5411\u9f99\u5934\u548c\u524d\u6392\u3002\n"
        "- \u5173\u6ce8\u9898\u6750\u4f1a\u5f71\u54cd\u6392\u5e8f\u3001\u62a5\u544a\u548c\u63d0\u9192\u3002\n"
        "- \u81ea\u52a8\u76d8\u524d\u62a5\u544a\u4f1a\u5728\u5237\u65b0\u540e\u540c\u6b65\u751f\u6210\u3002"
    )
    notes_layout.addWidget(window.config_notes_text)
    layout.addWidget(notes_box, stretch=1)

    window._refresh_license_status_view()
    if hasattr(window, "_refresh_news_source_status_panel"):
        window._refresh_news_source_status_panel()
    if hasattr(window, "_refresh_ai_review_status_panel"):
        window._refresh_ai_review_status_panel()







def _refresh_config_risk_snapshot_fallback(window) -> None:
    current_profile = getattr(getattr(window, "state", None), "strategy_risk_profile", RISK_PROFILE_STANDARD)
    meta = getattr(window, "last_daily_pool_meta", {}) or {}

    if not hasattr(window, "risk_snapshot_cards"):
        return

    for profile_key, labels in getattr(window, "risk_snapshot_cards", {}).items():
        card = labels.get("card")
        title = labels.get("title")
        detail = labels.get("detail")
        metrics = labels.get("metrics")
        flag = labels.get("flag")
        button = labels.get("button")
        card_state = risk_profile_snapshot_card_state(
            profile_key,
            current_profile=current_profile,
            meta=meta,
        )
        label = str(card_state["label"])
        brief = str(card_state["brief"])
        tooltip = str(card_state["tooltip"])
        is_current = bool(card_state["is_current"])
        if card is not None and hasattr(card, "setToolTip"):
            card.setToolTip(tooltip)
        if card is not None and hasattr(card, "setProperty"):
            card.setProperty("riskActive", is_current)
        if title is not None:
            title.setText(label)
            title.setToolTip(tooltip)
        if detail is not None:
            detail.setText(brief)
            detail.setToolTip(tooltip)
        if metrics is not None:
            metrics.setText(str(card_state["metrics"]))
            metrics.setToolTip(tooltip)
        if flag is not None:
            flag.setText(str(card_state["flag_text"]))
            flag.setToolTip(tooltip)
        if button is not None:
            button.setText(str(card_state["button_text"]))
            if hasattr(window, "_set_button_role"):
                window._set_button_role(button, "accent" if is_current else "tonal")
            button.setToolTip(str(card_state["button_tooltip"]))
            button.setEnabled(not is_current)

def build_config_workspace(window) -> None:
    _build_config_workspace_core(window)

    if hasattr(window, "_refresh_risk_snapshot_cards"):
        window._refresh_risk_snapshot_cards()
        return

    _refresh_config_risk_snapshot_fallback(window)
