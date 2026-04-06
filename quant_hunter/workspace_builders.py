from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtCharts import QChartView
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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


def build_auth_workspace(window) -> None:
    layout = QVBoxLayout(window.auth_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.auth_tab.setObjectName("authRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "统一登录",
            "券商账号与 SDK 接入配置",
            "用于保存账号、渠道和 SDK 参数。程序保留人工确认，不会绕过券商安全校验直接接管账户。",
            [("东方财富", "当前默认"), ("人工确认", "下单边界")],
        )
    )

    form_box = QGroupBox("账户配置")
    window._style_terminal_panel(form_box)
    form_grid = QGridLayout(form_box)
    profile = window.state.broker_profile

    form_grid.addWidget(QLabel("渠道"), 0, 0)
    window.auth_channel_combo = QComboBox()
    window.auth_channel_combo.addItem("东方财富", "eastmoney")
    window.auth_channel_combo.addItem("掘金 GM", "gm")
    window.auth_channel_combo.addItem("预留渠道", "custom")
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

    save_button = QPushButton("保存登录配置")
    window._set_button_role(save_button, "accent")
    save_button.clicked.connect(window.save_login_profile)
    form_grid.addWidget(save_button, 6, 1)
    layout.addWidget(form_box)

    status_box = QGroupBox("渠道状态与安全边界")
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
            "单只股票信号拆解与回测明细",
            "从扫描页或首页选中一只股票后，这里会联动展示信号、指标摘要和交易记录，适合做日内复核与复盘。",
            [("单票", "深度拆解"), ("回测", "联动展示")],
        )
    )

    controls = QHBoxLayout()
    load_button = QPushButton("载入单个 CSV")
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
    layout.addLayout(controls)

    metrics_box = QGroupBox("策略摘要")
    window._style_terminal_panel(metrics_box)
    metrics_layout = QVBoxLayout(metrics_box)
    window.metrics_text = QTextEdit()
    window.metrics_text.setReadOnly(True)
    window.metrics_text.setMaximumHeight(220)
    window._style_terminal_console(window.metrics_text)
    metrics_layout.addWidget(window.metrics_text)
    layout.addWidget(metrics_box)

    signal_box = QGroupBox("近期信号")
    trade_box = QGroupBox("交易记录")
    window._style_terminal_panel(signal_box, trade_box)

    signal_layout = QVBoxLayout(signal_box)
    window.signal_table = build_table(["日期", "信号", "评分", "收盘价", "原因"])
    signal_layout.addWidget(window.signal_table)

    trade_layout = QVBoxLayout(trade_box)
    window.trades_table = build_table(["开仓日期", "平仓日期", "开仓价", "平仓价", "股数", "盈亏", "退出原因"])
    trade_layout.addWidget(window.trades_table)

    bottom = QSplitter(Qt.Horizontal)
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(signal_box)
    bottom.addWidget(trade_box)
    window._configure_splitter(bottom, [470, 690])
    layout.addWidget(bottom, stretch=1)


def build_broker_workspace(window, build_table, adapter_factory, project_root) -> None:
    root_layout = QVBoxLayout(window.broker_tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)
    window.broker_tab.setObjectName("brokerRoot")
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
            "账户、委托建议与人工确认下单",
            "支持东方财富 / 掘金 GM 的参数接入、持仓同步、委托建议生成与一键确认下单，保留人工确认为最后闸门。",
            [("人工", "确认下单"), ("SDK", "可选联动")],
        )
    )

    profile_box = QGroupBox("账户与网关")
    window._style_terminal_panel(profile_box)
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
    profile_grid.addWidget(QLabel("模式"), mode_row, 0)
    window.mode_combo = QComboBox()
    window.mode_combo.addItem("导出模式", "export")
    window.mode_combo.addItem("SDK 模式", "sdk")
    current_mode = profile.mode or "export"
    window.mode_combo.setCurrentIndex(0 if current_mode == "export" else 1)
    profile_grid.addWidget(window.mode_combo, mode_row, 1)

    profile_grid.addWidget(QLabel("单笔预算"), mode_row, 2)
    window.per_trade_budget_input = QLineEdit("30000")
    profile_grid.addWidget(window.per_trade_budget_input, mode_row, 3)

    choose_export_button = QPushButton("选择导出目录")
    save_profile_button = QPushButton("保存账户配置")
    create_templates_button = QPushButton("生成模板")
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
    layout.addWidget(profile_box)

    action_box = QGroupBox("执行与同步")
    window._style_terminal_panel(action_box)
    action_grid = QGridLayout(action_box)
    action_grid.setHorizontalSpacing(10)
    action_grid.setVerticalSpacing(10)
    action_specs = [
        ("导入持仓 CSV", window.import_holdings_csv, "ghost"),
        ("导入资金 CSV", window.import_cash_csv, "ghost"),
        ("生成委托建议", window.generate_order_suggestions, "accent"),
        ("导出委托计划", window.export_order_plan, "ghost"),
        ("导出结果日志", window.export_order_result_log, "ghost"),
        ("同步 SDK 账户", window.sync_broker_via_sdk, "ghost"),
        ("生成 GM 脚本", window.generate_sdk_strategy_script, "ghost"),
        ("确认并下单", window.confirm_and_submit_orders, "accent"),
    ]
    for index, (label, handler, role) in enumerate(action_specs):
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setMinimumHeight(42)
        button.clicked.connect(handler)
        action_grid.addWidget(button, index // 4, index % 4)
    layout.addWidget(action_box)

    status_box = QGroupBox("账户状态 / 环境诊断")
    window._style_terminal_panel(status_box)
    status_layout = QVBoxLayout(status_box)
    window.broker_status_text = QTextEdit()
    window.broker_status_text.setReadOnly(True)
    window.broker_status_text.setMaximumHeight(220)
    window._style_terminal_console(window.broker_status_text)
    status_layout.addWidget(window.broker_status_text)
    layout.addWidget(status_box)

    runtime_box = QGroupBox("运行状态 / 系统日志")
    window._style_terminal_panel(runtime_box)
    runtime_layout = QVBoxLayout(runtime_box)
    window.runtime_status_text = QTextEdit()
    window.runtime_status_text.setReadOnly(True)
    window.runtime_status_text.setMaximumHeight(96)
    window._style_terminal_console(window.runtime_status_text)
    runtime_layout.addWidget(window.runtime_status_text)
    runtime_action_row = QHBoxLayout()
    runtime_action_specs = [
        ("刷新运行状态", window.refresh_runtime_panel, "ghost", "runtimeRefreshButton"),
        ("导出运行日志", window.export_runtime_log, "ghost", "runtimeExportButton"),
        ("清理市场缓存", window.clear_market_cache, "ghost", "runtimeClearCacheButton"),
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
    layout.addWidget(runtime_box)
    window.runtime_status_text.setPlainText(window._runtime_overview_text())
    if not window.runtime_events:
        window._append_runtime_log("运行日志面板已就绪。")

    holdings_box = QGroupBox("持仓")
    orders_box = QGroupBox("委托建议")
    window._style_terminal_panel(holdings_box, orders_box)

    holdings_layout = QVBoxLayout(holdings_box)
    window.holdings_table = build_table(["代码", "持仓数量", "可用数量", "成本价", "市值"])
    holdings_layout.addWidget(window.holdings_table)

    orders_layout = QVBoxLayout(orders_box)
    window.orders_table = build_table(["代码", "方向", "价格", "数量", "止损", "目标", "信号日期"])
    orders_layout.addWidget(window.orders_table)

    middle = QSplitter(Qt.Horizontal)
    middle.setChildrenCollapsible(False)
    middle.addWidget(holdings_box)
    middle.addWidget(orders_box)
    window._configure_splitter(middle, [500, 620])
    layout.addWidget(middle, stretch=1)

    result_box = QGroupBox("下单结果")
    window._style_terminal_panel(result_box)
    result_layout = QVBoxLayout(result_box)
    window.execution_table = build_table(
        ["时间", "委托状态", "成交状态", "代码", "方向", "价格", "数量", "失败原因", "消息"]
    )
    result_layout.addWidget(window.execution_table)
    window.order_result_text = QTextEdit()
    window.order_result_text.setReadOnly(True)
    window._style_terminal_console(window.order_result_text)
    window.order_result_text.setPlainText("暂无下单记录。\n")
    result_layout.addWidget(window.order_result_text)
    layout.addWidget(result_box, stretch=1)


def build_overview_workspace(
    window,
    build_table,
    strategy_params_factory,
    action_flow_card_cls,
    compact_summary_card_cls,
    leaderboard_card_cls,
) -> None:
    layout = QVBoxLayout(window.overview_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.overview_tab.setObjectName("overviewRoot")
    window._style_terminal_panel(window.overview_tab)

    quick_row = QHBoxLayout()
    quick_row.setSpacing(10)
    window.overview_quick_buttons = {}
    for index, (text, color) in enumerate(
        [
            ("市场总览", "#f1c40f"),
            ("龙头池", "#f1c40f"),
            ("涨跌分布", "#f1c40f"),
            ("资金方向", "#ff5b57"),
            ("题材热度", "#d16aff"),
            ("交易决策", "#d16aff"),
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
    layout.addLayout(quick_row)

    toolbar = QHBoxLayout()
    toolbar.setSpacing(10)
    window.market_search_input = QLineEdit()
    window.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材")
    window.market_search_input.setMinimumHeight(46)
    window.market_search_input.setMinimumWidth(240)
    window.market_search_input.setMaximumWidth(360)
    window.market_search_input.textChanged.connect(window._apply_market_filters)
    window.market_theme_combo = QComboBox()
    window.market_theme_combo.addItem("全部")
    window.market_theme_combo.setMinimumHeight(46)
    window.market_theme_combo.setMinimumWidth(120)
    window.market_theme_combo.currentTextChanged.connect(window._on_market_theme_filter_changed)
    window.market_refresh_button = QPushButton("一键刷新算法池")
    window.market_refresh_button.setMinimumHeight(46)
    window.market_refresh_button.setMinimumWidth(180)
    window.market_refresh_button.setStyleSheet(window._overview_filled_style("#237fa2"))
    window.market_refresh_button.clicked.connect(lambda: window.refresh_remote_market(update_chart=True))
    window.dashboard_auto_refresh_checkbox = QCheckBox("盘中自动刷新")
    window.dashboard_auto_refresh_checkbox.toggled.connect(window.toggle_dashboard_auto_refresh)
    window.dashboard_auto_refresh_checkbox.blockSignals(True)
    window.dashboard_auto_refresh_checkbox.setChecked(True)
    window.dashboard_auto_refresh_checkbox.blockSignals(False)
    window.market_status_label = QLabel("正在准备市场数据...")
    window.market_status_label.setObjectName("inlineHint")
    toolbar.addWidget(window.market_search_input)
    toolbar.addWidget(window.market_theme_combo)
    toolbar.addWidget(window.market_refresh_button)
    toolbar.addWidget(window.dashboard_auto_refresh_checkbox)
    toolbar.addWidget(window.market_status_label, stretch=1)
    layout.addLayout(toolbar)

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
    filter_row.addStretch(1)
    layout.addLayout(filter_row)

    metrics_row = QHBoxLayout()
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
    layout.addLayout(metrics_row)

    overview_priority_box = QGroupBox("盘前优先级")
    window._style_terminal_panel(overview_priority_box)
    overview_priority_layout = QHBoxLayout(overview_priority_box)
    overview_priority_layout.setContentsMargins(12, 12, 12, 12)
    overview_priority_layout.setSpacing(10)
    window.overview_priority_cards = {
        "market": action_flow_card_cls("市场", "#4fc3f7"),
        "theme": action_flow_card_cls("主线", "#c792ea"),
        "strategy": action_flow_card_cls("策略", "#ffd166"),
        "focus": action_flow_card_cls("焦点", "#25d07f"),
    }
    for key in ["market", "theme", "strategy", "focus"]:
        overview_priority_layout.addWidget(window.overview_priority_cards[key])
    layout.addWidget(overview_priority_box)

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

    window.intraday_chart_view = QChartView()
    window.intraday_chart_view.setMinimumHeight(320)
    window.intraday_chart_view.setObjectName("marketChartPanel")
    window.intraday_chart_view.setFrameShape(QFrame.NoFrame)
    left_layout.addWidget(window.intraday_chart_view, stretch=5)

    left_notes = QSplitter(Qt.Vertical)
    left_notes.setChildrenCollapsible(False)
    window.overview_left_notes_splitter = left_notes
    buy_box = QGroupBox("强承接席位")
    buy_layout = QVBoxLayout(buy_box)
    window.market_buy_text = QTextEdit()
    window.market_buy_text.setReadOnly(True)
    window.market_buy_text.setObjectName("marketNotePanel")
    window.market_buy_text.setMinimumHeight(118)
    buy_layout.addWidget(window.market_buy_text)
    risk_box = QGroupBox("高博弈风险席位")
    risk_layout = QVBoxLayout(risk_box)
    window.market_sell_text = QTextEdit()
    window.market_sell_text.setReadOnly(True)
    window.market_sell_text.setObjectName("marketNotePanel")
    window.market_sell_text.setMinimumHeight(118)
    risk_layout.addWidget(window.market_sell_text)
    breadth_box = QGroupBox("新闻流")
    breadth_layout = QVBoxLayout(breadth_box)
    window.market_news_group = breadth_box
    window.market_breadth_text = QTextEdit()
    window.market_breadth_text.setReadOnly(True)
    window.market_breadth_text.setObjectName("marketNotePanel")
    window.market_breadth_text.setMinimumHeight(126)
    breadth_layout.addWidget(window.market_breadth_text)
    left_notes.addWidget(buy_box)
    left_notes.addWidget(risk_box)
    left_notes.addWidget(breadth_box)
    window._configure_splitter(left_notes, [2, 2, 2])
    left_layout.addWidget(left_notes, stretch=2)
    main_splitter.addWidget(left_panel)

    center_panel = QWidget()
    center_panel.setMinimumWidth(980)
    center_layout = QVBoxLayout(center_panel)
    center_layout.setContentsMargins(0, 0, 0, 0)
    center_layout.setSpacing(10)
    window.market_header_label = QLabel("龙头掘金终端")
    window.market_header_label.setObjectName("heroTitle")
    center_layout.addWidget(window.market_header_label)
    window.market_subheader_label = QLabel("程序自动筛选全市场强势股，联动龙头池、题材热度、交易计划和复盘。")
    window.market_subheader_label.setObjectName("heroSubtitle")
    window.market_subheader_label.setWordWrap(True)
    center_layout.addWidget(window.market_subheader_label)
    window.market_signal_label = QLabel("资金模型 / 策略标签 / 主力净流入 / 换手率")
    window.market_signal_label.setObjectName("terminalSignal")
    center_layout.addWidget(window.market_signal_label)

    timeframe_row = QHBoxLayout()
    timeframe_row.setSpacing(8)
    window.timeframe_buttons = {}
    for text in ["分时", "1分", "5分", "15分", "30分", "60分", "日线"]:
        button = QPushButton(text)
        button.setCheckable(True)
        button.setMinimumHeight(42)
        button.setMinimumWidth(80)
        button.setStyleSheet(window._overview_filled_style("#237fa2"))
        button.clicked.connect(lambda checked=False, current_timeframe=text: window.set_market_timeframe(current_timeframe))
        if text in {"分时", "日线"}:
            button.setChecked(True)
        window.timeframe_buttons[text] = button
        timeframe_row.addWidget(button)
    timeframe_row.addStretch(1)
    center_layout.addLayout(timeframe_row)

    window.daily_chart_view = QChartView()
    window.daily_chart_view.setMinimumHeight(460)
    window.daily_chart_view.setObjectName("marketChartPanel")
    window.daily_chart_view.setFrameShape(QFrame.NoFrame)
    center_layout.addWidget(window.daily_chart_view, stretch=6)

    mini_chart_row = QSplitter(Qt.Horizontal)
    mini_chart_row.setChildrenCollapsible(False)
    window.overview_mini_chart_splitter = mini_chart_row
    window.fund_chart_view = QChartView()
    window.fund_chart_view.setMinimumHeight(250)
    window.fund_chart_view.setObjectName("marketChartPanel")
    window.fund_chart_view.setFrameShape(QFrame.NoFrame)
    mini_chart_row.addWidget(window.fund_chart_view)
    window.momentum_chart_view = QChartView()
    window.momentum_chart_view.setMinimumHeight(250)
    window.momentum_chart_view.setObjectName("marketChartPanel")
    window.momentum_chart_view.setFrameShape(QFrame.NoFrame)
    mini_chart_row.addWidget(window.momentum_chart_view)
    window._configure_splitter(mini_chart_row, [1, 1])
    center_layout.addWidget(mini_chart_row, stretch=2)

    window.price_chart_view = window.daily_chart_view
    window.volume_chart_view = window.fund_chart_view

    pool_box = QGroupBox("龙头股票池")
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
    window.market_pool_table.verticalHeader().setDefaultSectionSize(68)
    window.market_pool_table.setObjectName("marketPoolTable")
    pool_layout.addWidget(window.market_pool_table)
    center_layout.addWidget(pool_box, stretch=7)
    main_splitter.addWidget(center_panel)

    right_panel = QWidget()
    right_panel.setMinimumWidth(420)
    right_layout = QVBoxLayout(right_panel)
    right_layout.setContentsMargins(0, 0, 0, 0)
    right_layout.setSpacing(10)
    leaderboard_box = QGroupBox("掘龙榜")
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
    overview_summary_layout = QHBoxLayout(overview_summary_box)
    overview_summary_layout.setContentsMargins(10, 10, 10, 10)
    overview_summary_layout.setSpacing(10)
    window.overview_summary_cards = {
        "theme": compact_summary_card_cls("主线题材", "#c792ea"),
        "source": compact_summary_card_cls("数据状态", "#7ed7ff"),
        "capital": compact_summary_card_cls("资金画像", "#25d07f"),
        "decision": compact_summary_card_cls("交易决策", "#ff9f43"),
    }
    for key in ["theme", "source", "capital", "decision"]:
        overview_summary_layout.addWidget(window.overview_summary_cards[key])
    right_layout.addWidget(overview_summary_box, stretch=2)

    window.market_theme_brief_text = QTextEdit()
    window.market_theme_brief_text.setReadOnly(True)
    window.market_theme_brief_text.setObjectName("marketNotePanel")
    window.market_theme_brief_text.setMinimumHeight(132)
    window.market_theme_brief_text.setMaximumHeight(156)
    right_layout.addWidget(window.market_theme_brief_text, stretch=1)

    window.market_source_status_text = QTextEdit()
    window.market_source_status_text.setReadOnly(True)
    window.market_source_status_text.setObjectName("marketNotePanel")
    window.market_source_status_text.setMinimumHeight(132)
    window.market_source_status_text.setMaximumHeight(156)
    right_layout.addWidget(window.market_source_status_text, stretch=1)

    capital_box = QGroupBox("主力控盘 / 资金画像")
    capital_layout = QVBoxLayout(capital_box)
    window.market_capital_text = QTextEdit()
    window.market_capital_text.setReadOnly(True)
    window.market_capital_text.setObjectName("marketNotePanel")
    window.market_capital_text.setMinimumHeight(170)
    window.market_capital_text.setMaximumHeight(176)
    capital_layout.addWidget(window.market_capital_text)
    right_layout.addWidget(capital_box, stretch=2)

    decision_box = QGroupBox("龙头状态 / 交易决策")
    decision_layout = QVBoxLayout(decision_box)
    window.market_decision_text = QTextEdit()
    window.market_decision_text.setReadOnly(True)
    window.market_decision_text.setObjectName("marketNotePanel")
    window.market_decision_text.setMinimumHeight(170)
    window.market_decision_text.setMaximumHeight(176)
    decision_layout.addWidget(window.market_decision_text)
    right_layout.addWidget(decision_box, stretch=2)
    main_splitter.addWidget(right_panel)

    window._configure_splitter(main_splitter, [300, 1450, 430])
    layout.addWidget(main_splitter, stretch=1)

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
    layout.addWidget(params_box)


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
    layout = QVBoxLayout(window.recommend_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.recommend_tab.setObjectName("recommendRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "每日推荐",
            "程序自动生成当天推荐股票池",
            "结合技术面、位置、持续性、消息催化和龙头属性，形成更适合日内决策的推荐列表与交易计划。",
            [("Top 5", "今日计划"), ("多因子", "程序筛选")],
        )
    )

    intro = QLabel("推荐页直接承接程序自动筛出的候选池，不再依赖本地股票池文件，导入资料与消息面只是为了增强排序。")
    intro.setWordWrap(True)
    intro.setObjectName("inlineHint")
    layout.addWidget(intro)

    controls = QHBoxLayout()
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
    controls.addWidget(import_profile_button)
    controls.addWidget(import_news_button)
    controls.addWidget(import_theme_button)
    controls.addWidget(edit_theme_button)
    controls.addWidget(refresh_button)
    controls.addWidget(load_sample_button)
    controls.addStretch(1)
    layout.addLayout(controls)

    window.recommend_status_label = QLabel("可先扫描股票池，再导入股票资料和消息面 CSV 增强排序。")
    window.recommend_status_label.setObjectName("inlineHint")
    layout.addWidget(window.recommend_status_label)

    recommend_filter_row = QHBoxLayout()
    recommend_filter_row.addWidget(QLabel("题材筛选"))
    window.recommend_theme_combo = QComboBox()
    window.recommend_theme_combo.addItem("全部")
    window.recommend_theme_combo.currentTextChanged.connect(window._on_recommend_theme_filter_changed)
    recommend_filter_row.addWidget(window.recommend_theme_combo)
    recommend_filter_row.addStretch(1)
    layout.addLayout(recommend_filter_row)

    summary_splitter = QSplitter(Qt.Horizontal)
    summary_splitter.setChildrenCollapsible(False)

    theme_box = QGroupBox("题材热度榜")
    leader_box = QGroupBox("龙头股榜")
    window._style_terminal_panel(theme_box, leader_box)

    theme_layout = QVBoxLayout(theme_box)
    window.theme_heat_table = build_table(["题材", "热度", "持续性", "消息", "龙头数", "排序", "风险"])
    window.theme_heat_table.verticalHeader().setDefaultSectionSize(42)
    window.theme_heat_table.itemSelectionChanged.connect(window._on_theme_heat_selection_changed)
    theme_layout.addWidget(window.theme_heat_table)

    leader_layout = QVBoxLayout(leader_box)
    window.leader_table = build_table(["股票名称", "股票ID", "题材", "级别", "龙头分", "动作", "说明"])
    window.leader_table.verticalHeader().setDefaultSectionSize(46)
    window.leader_table.itemSelectionChanged.connect(window._on_leader_table_selection_changed)
    leader_layout.addWidget(window.leader_table)

    summary_splitter.addWidget(theme_box)
    summary_splitter.addWidget(leader_box)
    window._configure_splitter(summary_splitter, [460, 740])
    layout.addWidget(summary_splitter, stretch=2)

    pool_box = QGroupBox("每日推荐股票池")
    window._style_terminal_panel(pool_box)
    pool_layout = QVBoxLayout(pool_box)
    window.daily_pool_table = build_table(
        [
            "股票名称",
            "股票ID",
            "交易代码",
            "题材",
            "主策略",
            "题材热度",
            "龙头级别",
            "总分",
            "龙头模型",
            "主力雷达",
            "擒龙打板",
            "价值低吸",
            "掘龙决策",
            "动作",
            "最新催化",
            "信号日期",
        ]
    )
    window.daily_pool_table.verticalHeader().setDefaultSectionSize(48)
    window.daily_pool_table.itemSelectionChanged.connect(window._on_daily_pool_selection_changed)
    pool_layout.addWidget(window.daily_pool_table)
    layout.addWidget(pool_box, stretch=3)

    strategy_pack_box = QGroupBox("五大战法工作台")
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
    layout.addWidget(strategy_pack_box, stretch=2)

    strategy_detail_box = QGroupBox("战法明细联动")
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
    window.strategy_detail_text.setMinimumHeight(190)
    window._style_terminal_console(window.strategy_detail_text)
    window.strategy_detail_text.setPlainText("等待生成推荐池后更新。")
    strategy_detail_layout.addWidget(window.strategy_detail_text)
    layout.addWidget(strategy_detail_box, stretch=1)

    action_flow_box = QGroupBox("决策流程总览")
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
    layout.addWidget(action_flow_box, stretch=1)

    priority_box = QGroupBox("优先级排序面板")
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
    layout.addWidget(priority_box, stretch=1)

    alert_box = QGroupBox("盘中提醒面板")
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
    layout.addWidget(alert_box, stretch=1)

    strategy_path_box = QGroupBox("主线推演路径")
    window._style_terminal_panel(strategy_path_box)
    strategy_path_layout = QVBoxLayout(strategy_path_box)
    window.strategy_path_text = QTextEdit()
    window.strategy_path_text.setReadOnly(True)
    window.strategy_path_text.setMinimumHeight(120)
    window.strategy_path_text.setMaximumHeight(156)
    window._style_terminal_console(window.strategy_path_text)
    window.strategy_path_text.setPlainText("等待生成推荐池后更新主线推演路径。")
    strategy_path_layout.addWidget(window.strategy_path_text)
    layout.addWidget(strategy_path_box, stretch=1)

    summary_cards_box = QGroupBox("决策摘要卡")
    window._style_terminal_panel(summary_cards_box)
    summary_cards_layout = QHBoxLayout(summary_cards_box)
    summary_cards_layout.setContentsMargins(12, 12, 12, 12)
    summary_cards_layout.setSpacing(10)
    window.recommend_summary_cards = {
        "logic": compact_summary_card_cls("推荐逻辑", "#7ed7ff"),
        "plan": compact_summary_card_cls("盘前计划", "#25d07f"),
        "pulse": compact_summary_card_cls("市场情绪", "#ffd166"),
        "holding": compact_summary_card_cls("持仓建议", "#ff9f43"),
    }
    for key in ["logic", "plan", "pulse", "holding"]:
        summary_cards_layout.addWidget(window.recommend_summary_cards[key])
    layout.addWidget(summary_cards_box, stretch=1)

    detail_box = QGroupBox("推荐逻辑说明")
    plan_box = QGroupBox("今日 5 只交易计划")
    pulse_box = QGroupBox("市场情绪仪表")
    holding_box = QGroupBox("持仓卖出 / 格局建议")
    window._style_terminal_panel(detail_box, plan_box, pulse_box, holding_box)

    detail_layout = QVBoxLayout(detail_box)
    window.daily_pool_text = QTextEdit()
    window.daily_pool_text.setReadOnly(True)
    window.daily_pool_text.setMaximumHeight(176)
    window._style_terminal_console(window.daily_pool_text)
    window.daily_pool_text.setPlainText(
        "说明：\n"
        "- 题材：优先取股票资料中的行业/主题字段，远程市场模式下取策略标签。\n"
        "- 题材热度：根据题材内候选强度、持续性、消息面与龙头密度计算。\n"
        "- 龙头级别：分为核心龙头、活跃龙头、跟风股和噪声。\n"
        "- 技术面：来自策略信号评分与趋势结构。\n"
        "- 位置：越接近有效突破或回补区域，分值越高。\n"
        "- 持续性：结合均线、最近信号连续性与回测表现。\n"
        "- 消息面：优先近期、偏正向、热度更高的催化。\n"
        "- 龙头：优先具备行业辨识度与持续性的核心企业。"
    )
    detail_layout.addWidget(window.daily_pool_text)

    plan_layout = QVBoxLayout(plan_box)
    window.trade_plan_table = build_table(
        ["股票名称", "股票ID", "交易代码", "动作", "置信度", "计划买点", "止损", "目标", "建议资金", "说明"]
    )
    window.trade_plan_table.itemSelectionChanged.connect(window._on_trade_plan_selection_changed)
    plan_layout.addWidget(window.trade_plan_table)
    window.trade_plan_text = QTextEdit()
    window.trade_plan_text.setReadOnly(True)
    window.trade_plan_text.setMaximumHeight(146)
    window._style_terminal_console(window.trade_plan_text)
    window.trade_plan_text.setPlainText("先生成每日推荐池，再根据市场温度生成今日 5 只交易计划。")
    plan_layout.addWidget(window.trade_plan_text)

    pulse_layout = QVBoxLayout(pulse_box)
    window.market_pulse_text = QTextEdit()
    window.market_pulse_text.setReadOnly(True)
    window.market_pulse_text.setMaximumHeight(152)
    window._style_terminal_console(window.market_pulse_text)
    window.market_pulse_text.setPlainText("等待推荐池生成后更新市场温度。")
    pulse_layout.addWidget(window.market_pulse_text)

    holding_layout = QVBoxLayout(holding_box)
    window.position_advice_table = build_table(
        ["股票名称", "股票ID", "交易代码", "动作", "置信度", "现价", "成本", "盈亏幅度", "说明"]
    )
    holding_layout.addWidget(window.position_advice_table)
    window.position_advice_text = QTextEdit()
    window.position_advice_text.setReadOnly(True)
    window.position_advice_text.setMaximumHeight(146)
    window._style_terminal_console(window.position_advice_text)
    window.position_advice_text.setPlainText("导入持仓后，这里会给出止盈、止损、减仓或继续持有建议。")
    holding_layout.addWidget(window.position_advice_text)

    middle = QSplitter(Qt.Horizontal)
    middle.setChildrenCollapsible(False)
    middle.addWidget(detail_box)
    middle.addWidget(plan_box)
    window._configure_splitter(middle, [380, 860])
    layout.addWidget(middle, stretch=2)

    bottom = QSplitter(Qt.Horizontal)
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(pulse_box)
    bottom.addWidget(holding_box)
    window._configure_splitter(bottom, [320, 920])
    layout.addWidget(bottom, stretch=2)


def build_board_workspace(window, build_table, header_view_cls) -> None:
    layout = QVBoxLayout(window.board_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.board_tab.setObjectName("boardRoot")

    layout.addWidget(
        window._build_workspace_hero(
            "打板监控",
            "强势龙头、回封确认与炸板风险联动",
            "把打板候选、回封观察、炸板风险和收盘复盘统一到一个页面里，适合专门盯高辨识度强势股。",
            [("Top 5", "打板候选"), ("15:05", "自动复盘")],
        )
    )

    control_row = QHBoxLayout()
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
    layout.addLayout(control_row)

    candidate_box = QGroupBox("打板候选池")
    monitor_box = QGroupBox("炸板 / 回封监控")
    window._style_terminal_panel(candidate_box, monitor_box)

    candidate_layout = QVBoxLayout(candidate_box)
    window.board_table = build_table(
        ["股票名称", "股票ID", "交易代码", "打板分", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"]
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
    window.board_monitor_text.setPlainText("打板监控会显示回封观察、炸板风险和强势连板候选。")
    monitor_layout.addWidget(window.board_monitor_text)
    layout.addWidget(monitor_box, stretch=1)



def build_config_workspace(window) -> None:
    layout = QVBoxLayout(window.config_tab)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)

    hero = window._build_workspace_hero(
        "???? / ???",
        "???????",
        "????????????????????????",
        [("??", "????"), ("??", window.state.license_plan or "TRIAL")],
    )
    layout.addWidget(hero)

    top = QSplitter(Qt.Horizontal)
    top.setChildrenCollapsible(False)

    strategy_box = QGroupBox("????")
    window._style_terminal_panel(strategy_box)
    strategy_layout = QFormLayout(strategy_box)
    strategy_layout.setLabelAlignment(Qt.AlignRight)

    window.config_inputs["top_theme_limit"] = QLineEdit(str(window.state.strategy_top_theme_limit))
    window.config_inputs["max_total_exposure"] = QLineEdit(str(window.state.strategy_max_total_exposure))
    window.config_inputs["daily_plan_candidate_limit"] = QLineEdit(str(window.state.daily_plan_candidate_limit))
    window.focus_themes_input = QLineEdit(", ".join(window.state.focus_themes))
    window.theme_drop_reduce_checkbox = QCheckBox("?????????")
    window.theme_drop_reduce_checkbox.setChecked(window.state.strategy_theme_drop_reduce)
    window.auto_daily_plan_export_checkbox = QCheckBox("????????")
    window.auto_daily_plan_export_checkbox.setChecked(window.state.auto_daily_plan_export)
    window.daily_plan_focus_only_checkbox = QCheckBox("???????")
    window.daily_plan_focus_only_checkbox.setChecked(window.state.daily_plan_focus_only)
    window.daily_plan_template_combo = QComboBox()
    for key, label in [("balanced", "????"), ("focus", "????"), ("mainline", "????"), ("compact", "????")]:
        window.daily_plan_template_combo.addItem(label, key)
    for index in range(window.daily_plan_template_combo.count()):
        if window.daily_plan_template_combo.itemData(index) == window.state.daily_plan_template:
            window.daily_plan_template_combo.setCurrentIndex(index)
            break

    strategy_layout.addRow("??? N ??", window.config_inputs["top_theme_limit"])
    strategy_layout.addRow("?????", window.config_inputs["max_total_exposure"])
    strategy_layout.addRow("??????", window.config_inputs["daily_plan_candidate_limit"])
    strategy_layout.addRow("????", window.focus_themes_input)
    strategy_layout.addRow("????", window.daily_plan_template_combo)
    strategy_layout.addRow("", window.daily_plan_focus_only_checkbox)
    strategy_layout.addRow("", window.theme_drop_reduce_checkbox)
    strategy_layout.addRow("", window.auto_daily_plan_export_checkbox)
    top.addWidget(strategy_box)

    license_box = QGroupBox("?????")
    window._style_terminal_panel(license_box)
    license_layout = QVBoxLayout(license_box)
    window.license_status_text = QTextEdit()
    window.license_status_text.setReadOnly(True)
    window._style_terminal_console(window.license_status_text)
    license_layout.addWidget(window.license_status_text)

    license_buttons = QHBoxLayout()
    trial_button = QPushButton("???")
    pro_button = QPushButton("???")
    enterprise_button = QPushButton("???")
    save_button = QPushButton("????")
    window._set_button_role(trial_button)
    window._set_button_role(pro_button)
    window._set_button_role(enterprise_button)
    window._set_button_role(save_button, "accent")
    trial_button.clicked.connect(window.reset_trial_plan)
    pro_button.clicked.connect(window.activate_professional_plan)
    enterprise_button.clicked.connect(window.activate_enterprise_plan)
    save_button.clicked.connect(window.save_strategy_preferences)
    for button in [trial_button, pro_button, enterprise_button, save_button]:
        license_buttons.addWidget(button)
    license_layout.addLayout(license_buttons)
    top.addWidget(license_box)

    window._configure_splitter(top, [620, 620])
    layout.addWidget(top, stretch=2)

    notes_box = QGroupBox("??")
    window._style_terminal_panel(notes_box)
    notes_layout = QVBoxLayout(notes_box)
    window.config_notes_text = QTextEdit()
    window.config_notes_text.setReadOnly(True)
    window._style_terminal_console(window.config_notes_text)
    window.config_notes_text.setPlainText(
        "???????????????????????????????\n"
        "- ?????????????????\n"
        "- ????????????????\n"
        "- ??????????????\n"
        "- ?????????????????"
    )
    notes_layout.addWidget(window.config_notes_text)
    layout.addWidget(notes_box, stretch=1)

    window._refresh_license_status_view()
