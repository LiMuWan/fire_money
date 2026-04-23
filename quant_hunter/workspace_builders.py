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
    QListWidgetItem,
    QProgressBar,
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
    OVERVIEW_DEFAULT_STATUS_TEXT,
    ORDERS_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_EMPTY_HINT,
    RECOMMEND_DEFAULT_EMPTY_META,
    RECOMMEND_DEFAULT_EMPTY_TITLE,
    RECOMMEND_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_STATUS_TEXT,
    RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
    RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
    TRADE_PLAN_DEFAULT_FOCUS_TEXT,
    STRATEGY_FILTER_LABELS,
    BOARD_CONTROLS_POLICY,
    broker_terminal_focus_button_copy,
    broker_terminal_primary_cta_labels,
    broker_terminal_primary_cta_tooltips,
    BROKER_SETUP_POLICY,
    OVERVIEW_CONTROLS_POLICY,
    recommend_focus_action_tooltip,
    RECOMMEND_AUX_STAGE_POLICY,
    RECOMMEND_CONTROLS_POLICY,
    recommend_terminal_cta_labels,
    WORKSPACE_STAGE_SUMMARY_SPECS,
    WORKSPACE_UI_SPECS,
    workspace_hero_payload,
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
from quant_hunter.strategy_registry import list_strategy_context_inputs
from quant_hunter.message_center import (
    build_message_center_snapshot,
    message_center_action_bar_text,
    message_center_button_label,
    message_center_metric_accent,
)
from quant_hunter.ui_helpers import AdaptivePanelGrid, build_workspace_badge


def _configure_chart_view(view: QChartView, *, min_height: int) -> None:
    view.setMinimumHeight(min_height)
    view.setObjectName("marketChartPanel")
    view.setFrameShape(QFrame.NoFrame)
    view.setRenderHint(QPainter.Antialiasing, True)


def _configure_terminal_stage_tabs(tab_widget: QTabWidget, *, page_tone: str, tooltips: list[str] | None = None) -> None:
    tab_widget.setObjectName("compactInfoTabs")
    tab_widget.setProperty("pageTone", page_tone)
    bar = tab_widget.tabBar()
    bar.setProperty("pageTone", page_tone)
    bar.setDocumentMode(True)
    bar.setExpanding(True)
    bar.setUsesScrollButtons(False)
    if tooltips:
        for index, tooltip in enumerate(tooltips):
            if index < tab_widget.count():
                bar.setTabToolTip(index, tooltip)


def _build_workspace_stage_summary(window, *, workspace_key: str, attr_prefix: str, tab_widget: QTabWidget) -> QFrame:
    stage_specs = list(WORKSPACE_STAGE_SUMMARY_SPECS.get(workspace_key, ()))
    workspace_label = str(WORKSPACE_UI_SPECS.get(workspace_key, {}).get("tab", "工作区"))

    frame = QFrame()
    frame.setObjectName("workspaceStageHero")
    frame.setProperty("pageTone", workspace_key)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(12)

    accent_strip = QFrame()
    accent_strip.setObjectName("workspaceStageAccent")
    accent_strip.setProperty("pageTone", workspace_key)
    accent_strip.setFixedWidth(3)
    layout.addWidget(accent_strip)

    text_layout = QVBoxLayout()
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(4)

    eyebrow_label = QLabel()
    eyebrow_label.setObjectName("workspaceStageEyebrow")
    title_label = QLabel()
    title_label.setObjectName("workspaceStageTitle")
    subtitle_label = QLabel()
    subtitle_label.setObjectName("workspaceStageSubtitle")
    subtitle_label.setWordWrap(True)

    text_layout.addWidget(eyebrow_label)
    text_layout.addWidget(title_label)
    text_layout.addWidget(subtitle_label)
    layout.addLayout(text_layout, stretch=3)

    badge_rail = AdaptivePanelGrid(min_item_width=132, compact_item_width=110, max_columns=3)
    badge_rail.setObjectName("workspaceBadgeRail")
    badge_rail.set_grid_spacing(6, 6)
    badge_rail.setMaximumWidth(420)
    badge_refs: list[tuple[QFrame, QLabel | None, QLabel | None]] = []
    for _ in range(3):
        badge = build_workspace_badge("--", "摘要", workspace_key)
        badge.setProperty("pageTone", workspace_key)
        badge_refs.append(
            (
                badge,
                badge.findChild(QLabel, "workspaceBadgeValue"),
                badge.findChild(QLabel, "workspaceBadgeCaption"),
            )
        )
        badge_rail.add_panel(badge)
    layout.addWidget(badge_rail, stretch=2)

    def _apply_stage_summary(index: int) -> None:
        safe_index = max(0, min(index, len(stage_specs) - 1)) if stage_specs else max(0, index)
        fallback_title = tab_widget.tabText(safe_index) if 0 <= safe_index < tab_widget.count() else ""
        stage_spec = stage_specs[safe_index] if stage_specs and safe_index < len(stage_specs) else {}
        title = str(stage_spec.get("title") or fallback_title or workspace_label)
        subtitle = str(stage_spec.get("subtitle") or "当前子视图用于承接这一阶段的核心判断与下一步动作。")
        badges = list(stage_spec.get("badges") or [])
        eyebrow_label.setText(f"{workspace_label} / 子视图 {safe_index + 1:02d}")
        title_label.setText(title)
        subtitle_label.setText(subtitle)
        for slot, (badge_frame, value_label, caption_label) in enumerate(badge_refs):
            if slot < len(badges):
                caption, value = badges[slot]
                if caption_label is not None:
                    caption_label.setText(str(caption))
                if value_label is not None:
                    value_label.setText(str(value))
                badge_frame.show()
            else:
                badge_frame.hide()

    setattr(window, f"{attr_prefix}_stage_summary_frame", frame)
    setattr(window, f"{attr_prefix}_stage_summary_title", title_label)
    setattr(window, f"{attr_prefix}_stage_summary_subtitle", subtitle_label)
    tab_widget.currentChanged.connect(_apply_stage_summary)
    _apply_stage_summary(tab_widget.currentIndex() if tab_widget.count() else 0)
    return frame


def _build_workspace_focus_strip(
    window,
    *,
    workspace_key: str,
    attr_prefix: str,
    eyebrow: str,
    title: str,
    subtitle: str,
    badges: list[tuple[str, str]],
) -> QFrame:
    frame = QFrame()
    frame.setObjectName("workspaceStageHero")
    frame.setProperty("pageTone", workspace_key)
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(12)

    accent_strip = QFrame()
    accent_strip.setObjectName("workspaceStageAccent")
    accent_strip.setProperty("pageTone", workspace_key)
    accent_strip.setFixedWidth(3)
    layout.addWidget(accent_strip)

    text_layout = QVBoxLayout()
    text_layout.setContentsMargins(0, 0, 0, 0)
    text_layout.setSpacing(4)
    eyebrow_label = QLabel(eyebrow)
    eyebrow_label.setObjectName("workspaceStageEyebrow")
    title_label = QLabel(title)
    title_label.setObjectName("workspaceStageTitle")
    subtitle_label = QLabel(subtitle)
    subtitle_label.setObjectName("workspaceStageSubtitle")
    subtitle_label.setWordWrap(True)
    text_layout.addWidget(eyebrow_label)
    text_layout.addWidget(title_label)
    text_layout.addWidget(subtitle_label)
    layout.addLayout(text_layout, stretch=3)

    badge_rail = AdaptivePanelGrid(min_item_width=132, compact_item_width=110, max_columns=3)
    badge_rail.setObjectName("workspaceBadgeRail")
    badge_rail.set_grid_spacing(6, 6)
    badge_rail.setMaximumWidth(420)
    for value, caption in badges[:3]:
        badge = build_workspace_badge(value, caption, workspace_key)
        badge.setProperty("pageTone", workspace_key)
        badge_rail.add_panel(badge)
    layout.addWidget(badge_rail, stretch=2)

    setattr(window, f"{attr_prefix}_summary_frame", frame)
    setattr(window, f"{attr_prefix}_summary_title", title_label)
    setattr(window, f"{attr_prefix}_summary_subtitle", subtitle_label)
    return frame


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


def _build_section_hint(text: str, *, page_tone: str = "") -> QLabel:
    label = QLabel(text)
    label.setObjectName("inlineHint")
    if page_tone:
        label.setProperty("pageTone", page_tone)
    label.setWordWrap(True)
    return label


def build_auth_workspace(window) -> None:
    layout = QVBoxLayout(window.auth_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.auth_tab.setObjectName("authRoot")
    eyebrow, title, subtitle, badges = workspace_hero_payload("auth")
    hero = window._build_workspace_hero(
        eyebrow,
        title,
        subtitle,
        badges,
    )
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "auth")
    layout.addWidget(hero)

    window.auth_status_banner = QLabel("接入状态：待校验 | 凭据与 Bridge 待确认 | 下一步：补齐后校验接入。")
    window.auth_status_banner.setObjectName("statusBanner")
    window.auth_status_banner.setProperty("pageTone", "auth")
    window.auth_status_banner.setWordWrap(True)
    layout.addWidget(window.auth_status_banner)

    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="auth",
            attr_prefix="auth_desk",
            eyebrow="接入中心 / 接入判断",
            title="接入判断条",
            subtitle="先确认通道、凭据与人工闸门，再决定是否进入机会池和交易链路。",
            badges=[
                ("看什么", "通道 / 凭据 / 闸门"),
                ("本页动作", "保存 / 校验接入"),
                ("下一步", "进入机会池 / 交易"),
            ],
        )
    )

    auth_summary_box = QGroupBox("接入摘要")
    window.auth_summary_box = auth_summary_box
    window._style_terminal_panel(auth_summary_box)
    auth_summary_box.setProperty("pageTone", "auth")
    auth_summary_box.setProperty("surfaceRole", "metric-band")
    auth_summary_layout = QVBoxLayout(auth_summary_box)
    auth_summary_layout.setContentsMargins(12, 12, 12, 12)
    auth_summary_layout.setSpacing(0)
    auth_summary_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    auth_summary_band.setObjectName("authSummaryBand")
    auth_summary_band.set_grid_spacing(10, 10)
    window.auth_summary_metric_cards = {}
    window.auth_summary_metric_labels = {}
    window.auth_summary_metric_accents = {}
    for key, title, accent in [
        ("channel", "接入通道", "等待通道确认"),
        ("credential", "凭据齐备", "等待凭据校验"),
        ("bridge", "Bridge 环境", "等待环境确认"),
        ("next", "下一步", "先补参数再校验"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.auth_summary_metric_cards[key] = card
        window.auth_summary_metric_labels[key] = value_label
        window.auth_summary_metric_accents[key] = accent_label
        auth_summary_band.add_panel(card)
    auth_summary_layout.addWidget(auth_summary_band)
    layout.addWidget(auth_summary_box)

    capability_box = QGroupBox("接入能力总览")
    capability_box.setObjectName("authCapabilityBox")
    window.auth_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "auth")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的接入通道、凭据校验、Bridge 环境和后续入口从这里回补，避免接入能力像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.auth_capability_cards = {}
    capability_specs = [
        ("channel", "接入通道", "看通道、账号与策略 ID 表单。", "看通道"),
        ("credential", "凭据校验", "看凭据完整度与校验状态。", "看校验"),
        ("bridge", "Bridge 环境", "看 SDK 模块、Bridge Python 与运行环境。", "看桥接"),
        ("next", "后续入口", "接入完成后继续进入机会池与交易链路。", "看机会"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("authCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "auth")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key == "next" else "tonal")
        if hasattr(window, "_open_auth_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_auth_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, index // 2, index % 2)
        window.auth_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    layout.addWidget(capability_box)

    form_box = QGroupBox("账号连接")
    window.auth_form_box = form_box
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
    save_button = QPushButton("保存接入")
    validate_button = QPushButton("校验接入")
    broker_button = QPushButton("去交易")
    recommend_button = QPushButton("看机会")
    window.auth_save_button = save_button
    window.auth_validate_button = validate_button
    window.auth_to_broker_button = broker_button
    window.auth_to_recommend_button = recommend_button
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

    status_box = QGroupBox("接入状态")
    window.auth_status_box = status_box
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
    if hasattr(window, "_refresh_auth_capability_overview_v1"):
        window._refresh_auth_capability_overview_v1()


def build_paper_workspace(window) -> None:
    layout = QVBoxLayout(window.paper_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.paper_tab.setObjectName("paperRoot")
    eyebrow, title, subtitle, badges = workspace_hero_payload("paper")
    hero = window._build_workspace_hero(eyebrow, title, subtitle, badges)
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "paper")
    layout.addWidget(hero)

    window.paper_status_banner = QLabel("实验状态：待初始化 | 主测样本尚未建立 | 下一步：先启动首轮主测。")
    window.paper_status_banner.setObjectName("statusBanner")
    window.paper_status_banner.setProperty("pageTone", "paper")
    window.paper_status_banner.setWordWrap(True)
    layout.addWidget(window.paper_status_banner)

    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="paper",
            attr_prefix="paper_desk",
            eyebrow="实验台 / 实验判断",
            title="实验判断条",
            subtitle="先确认主测状态、样本边界和下一步动作，再进入持仓交割与战法巡航。",
            badges=[
                ("看什么", "状态 / 样本 / 权益"),
                ("本页动作", "初始化 / 主测"),
                ("下一步", "进入持仓 / 巡航"),
            ],
        )
    )

    paper_summary_box = QGroupBox("实验摘要")
    window.paper_summary_box = paper_summary_box
    window._style_terminal_panel(paper_summary_box)
    paper_summary_box.setProperty("pageTone", "paper")
    paper_summary_box.setProperty("surfaceRole", "metric-band")
    paper_summary_layout = QVBoxLayout(paper_summary_box)
    paper_summary_layout.setContentsMargins(12, 12, 12, 12)
    paper_summary_layout.setSpacing(0)
    paper_summary_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    paper_summary_band.setObjectName("paperSummaryBand")
    paper_summary_band.set_grid_spacing(10, 10)
    window.paper_summary_metric_cards = {}
    window.paper_summary_metric_labels = {}
    window.paper_summary_metric_accents = {}
    for key, title, accent in [
        ("stage", "实验阶段", "等待初始化"),
        ("equity", "模拟权益", "等待首轮主测"),
        ("sample", "闭环样本", "等待第一批闭环"),
        ("next", "下一步", "先初始化模拟盘"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.paper_summary_metric_cards[key] = card
        window.paper_summary_metric_labels[key] = value_label
        window.paper_summary_metric_accents[key] = accent_label
        paper_summary_band.add_panel(card)
    paper_summary_layout.addWidget(paper_summary_band)
    layout.addWidget(paper_summary_box)

    tool_panel = QGroupBox("实验导航")
    window.paper_tool_panel = tool_panel
    tool_panel.setObjectName("workspaceToolPanel")
    tool_panel.setProperty("pageTone", "paper")
    tool_panel.setProperty("surfaceRole", "control")
    window._style_terminal_panel(tool_panel)
    tool_layout = QGridLayout(tool_panel)
    tool_layout.setContentsMargins(14, 12, 14, 12)
    tool_layout.setHorizontalSpacing(16)
    tool_layout.setVerticalSpacing(10)

    hint = QLabel("实验台只处理模拟盘、主测/对照样本与实验结论，不再和执行中控混在同一主页面。")
    hint.setObjectName("inlineHint")
    hint.setWordWrap(True)
    tool_layout.addWidget(hint, 0, 0, 1, 3)

    window.paper_to_recommend_button = QPushButton("看机会")
    window.paper_to_broker_button = QPushButton("去交易")
    window.paper_to_detail_button = QPushButton("看复盘")
    window._set_button_role(window.paper_to_recommend_button, "ghost")
    window._set_button_role(window.paper_to_broker_button, "tonal")
    window._set_button_role(window.paper_to_detail_button, "ghost")
    for button in (window.paper_to_recommend_button, window.paper_to_broker_button, window.paper_to_detail_button):
        button.setMinimumHeight(40)
    window.paper_to_recommend_button.clicked.connect(lambda: window._navigate_to_workspace("recommend", "daily_pool_table"))
    window.paper_to_broker_button.clicked.connect(lambda: window._navigate_to_workspace("broker", "orders_table"))
    window.paper_to_detail_button.clicked.connect(lambda: window._navigate_to_workspace("detail", "detail_decision_text"))
    tool_layout.addWidget(window.paper_to_recommend_button, 1, 0)
    tool_layout.addWidget(window.paper_to_broker_button, 1, 1)
    tool_layout.addWidget(window.paper_to_detail_button, 1, 2)
    layout.addWidget(tool_panel)

    window.paper_workspace_scroll_area = QScrollArea()
    window.paper_workspace_scroll_area.setWidgetResizable(True)
    window.paper_workspace_scroll_area.setFrameShape(QFrame.NoFrame)
    window.paper_workspace_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.paper_workspace_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    layout.addWidget(window.paper_workspace_scroll_area, stretch=1)

    paper_content = QWidget()
    paper_content.setObjectName("paperWorkspaceContent")
    paper_content.setProperty("pageTone", "paper")
    paper_layout = QVBoxLayout(paper_content)
    paper_layout.setContentsMargins(0, 0, 0, 0)
    paper_layout.setSpacing(12)
    window.paper_workspace_scroll_area.setWidget(paper_content)
    window.paper_workspace_content = paper_content
    window.paper_workspace_layout = paper_layout

    window.paper_stage_tabs = QTabWidget()
    window.paper_stage_tabs.setObjectName("compactInfoTabs")

    paper_overview_page = QWidget()
    paper_overview_layout = QVBoxLayout(paper_overview_page)
    paper_overview_layout.setContentsMargins(0, 0, 0, 0)
    paper_overview_layout.setSpacing(12)
    window.paper_stage_tabs.addTab(paper_overview_page, "实验总览")

    paper_records_page = QWidget()
    paper_records_layout = QVBoxLayout(paper_records_page)
    paper_records_layout.setContentsMargins(0, 0, 0, 0)
    paper_records_layout.setSpacing(12)
    window.paper_stage_tabs.addTab(paper_records_page, "持仓与交割")

    paper_analytics_page = QWidget()
    paper_analytics_layout = QVBoxLayout(paper_analytics_page)
    paper_analytics_layout.setContentsMargins(0, 0, 0, 0)
    paper_analytics_layout.setSpacing(12)
    window.paper_stage_tabs.addTab(paper_analytics_page, "战法与巡航")
    _configure_terminal_stage_tabs(
        window.paper_stage_tabs,
        page_tone="paper",
        tooltips=[
            "看模拟盘状态、实验边界与本轮主测概况。",
            "看模拟持仓、交割单与样本动作。",
            "看战法收益拆解、巡航日志与实验洞察。",
        ],
    )
    paper_layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="paper",
            attr_prefix="paper",
            tab_widget=window.paper_stage_tabs,
        )
    )
    paper_layout.addWidget(window.paper_stage_tabs, stretch=1)
    window.paper_overview_stage_layout = paper_overview_layout
    window.paper_records_stage_layout = paper_records_layout
    window.paper_analytics_stage_layout = paper_analytics_layout

    intro_box = QGroupBox("实验总览")
    intro_box.setObjectName("paperOverviewBox")
    window.paper_overview_box = intro_box
    intro_box.setProperty("pageTone", "paper")
    intro_box.setProperty("surfaceRole", "spotlight")
    window._style_terminal_panel(intro_box)
    intro_layout = QVBoxLayout(intro_box)
    intro_layout.setContentsMargins(14, 14, 14, 14)
    intro_layout.setSpacing(10)
    intro_text = QTextEdit()
    intro_text.setReadOnly(True)
    window._style_terminal_console(intro_text)
    intro_text.setProperty("pageTone", "paper")
    intro_text.setMinimumHeight(144)
    intro_text.setMaximumHeight(188)
    intro_text.setPlainText(
        "实验总览\n"
        "结论：实验台独立承载模拟盘、主测/对照与实验复盘。\n"
        "风险：不要再把执行中控与实验样本放在同一主页面里判断。\n"
        "下一步：先初始化模拟盘，再形成主测、对照和观察三类样本。"
    )
    intro_layout.addWidget(intro_text)
    paper_overview_layout.addWidget(intro_box)

    capability_box = QGroupBox("实验能力总览")
    capability_box.setObjectName("paperCapabilityBox")
    window.paper_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "paper")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的实验总览、持仓与交割、战法巡航从这里回补，避免实验能力像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.paper_capability_cards = {}
    capability_specs = [
        ("overview", "实验总览", "看实验状态、权益曲线和本轮主测摘要。", "看总览"),
        ("records", "持仓与交割", "看模拟持仓、交割单和调仓建议。", "看交割"),
        ("analytics", "战法与巡航", "看战法表现、巡航日志和实验洞察。", "看巡航"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("paperCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "paper")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key == "analytics" else "tonal")
        if hasattr(window, "_open_paper_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_paper_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, 0, index)
        window.paper_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    paper_overview_layout.addWidget(capability_box)
    if hasattr(window, "_refresh_paper_capability_overview_v1"):
        window._refresh_paper_capability_overview_v1()

def build_detail_workspace(window, build_table) -> None:
    layout = QVBoxLayout(window.detail_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.detail_tab.setObjectName("detailRoot")
    eyebrow, title, subtitle, badges = workspace_hero_payload("detail")
    hero = window._build_workspace_hero(
        eyebrow,
        title,
        subtitle,
        badges,
    )
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "detail")
    layout.addWidget(hero)

    window.detail_status_banner = QLabel("复盘状态：待联动 | 焦点票尚未同步 | 下一步：从机会池、扫描或执行中控联动。")
    window.detail_status_banner.setObjectName("statusBanner")
    window.detail_status_banner.setProperty("pageTone", "detail")
    window.detail_status_banner.setWordWrap(True)
    layout.addWidget(window.detail_status_banner)

    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="detail",
            attr_prefix="detail_desk",
            eyebrow="单票复盘 / 复盘判断",
            title="复盘判断条",
            subtitle="先定单票结论、执行偏差和下一步观察，再进入信号与交易、历史战法与结论沉淀。",
            badges=[
                ("看什么", "结论 / 偏差 / 证据"),
                ("本页动作", "核对 / 留结论"),
                ("下一步", "进入信号 / 历史"),
            ],
        )
    )

    detail_summary_box = QGroupBox("关键摘要")
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

    tool_panel = QGroupBox("单票工具台")
    window.detail_tool_panel = tool_panel
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
    window.detail_compare_history_button = compare_history_button
    window.detail_export_history_button = export_history_button
    window.detail_history_button = history_button
    window.detail_load_csv_button = load_button
    window.detail_backtest_button = backtest_button
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
    window.detail_hint_title_label = detail_hint_title
    detail_hint_title.setObjectName("inlineHint")
    detail_hint_title.setWordWrap(True)
    detail_hint_layout.addWidget(detail_hint_title)
    tool_layout.addWidget(detail_hint_panel, 0, 1)
    tool_layout.setColumnStretch(0, 3)
    tool_layout.setColumnStretch(1, 2)

    window.detail_stage_tabs = QTabWidget()

    detail_overview_page = QWidget()
    detail_overview_layout = QVBoxLayout(detail_overview_page)
    detail_overview_layout.setContentsMargins(0, 0, 0, 0)
    detail_overview_layout.setSpacing(12)
    window.detail_stage_tabs.addTab(detail_overview_page, "单票总览")

    detail_timeline_page = QWidget()
    detail_timeline_layout = QVBoxLayout(detail_timeline_page)
    detail_timeline_layout.setContentsMargins(0, 0, 0, 0)
    detail_timeline_layout.setSpacing(12)
    window.detail_stage_tabs.addTab(detail_timeline_page, "信号与交易")

    detail_history_page = QWidget()
    detail_history_layout = QVBoxLayout(detail_history_page)
    detail_history_layout.setContentsMargins(0, 0, 0, 0)
    detail_history_layout.setSpacing(12)
    window.detail_stage_tabs.addTab(detail_history_page, "历史战法")
    _configure_terminal_stage_tabs(
        window.detail_stage_tabs,
        page_tone="detail",
        tooltips=[
            "先看单票结论、执行轨迹和复盘结论。",
            "看信号时间线与实际交易记录。",
            "看历史战法统计、参数对比与逐笔表现。",
        ],
    )
    layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="detail",
            attr_prefix="detail",
            tab_widget=window.detail_stage_tabs,
        )
    )
    layout.addWidget(window.detail_stage_tabs, stretch=1)
    layout.addWidget(tool_panel)
    _configure_terminal_stage_tabs(
        window.detail_stage_tabs,
        page_tone="detail",
        tooltips=[
            "先看单票结论、执行轨迹与复盘结论。",
            "看信号时间线与实际交易记录。",
            "看历史战法统计、参数对比与逐笔表现。",
        ],
    )

    metrics_box = QGroupBox("交易依据")
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
    decision_box = QGroupBox("决策依据")
    execution_box = QGroupBox("执行轨迹")
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

    capability_box = QGroupBox("单票能力总览")
    capability_box.setObjectName("detailCapabilityBox")
    window.detail_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "detail")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的单票结论、信号交易回放和历史战法从这里回补，避免历史能力像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.detail_capability_cards = {}
    capability_specs = [
        ("overview", "单票结论", "看决策依据、执行偏差和复盘结论。", "看结论"),
        ("timeline", "信号与交易", "看信号时间线和成交轨迹回放。", "看回放"),
        ("history", "历史战法", "看历史战法统计、参数对比和逐笔表现。", "看历史"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("detailCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "detail")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key == "history" else "tonal")
        if hasattr(window, "_open_detail_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_detail_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, 0, index)
        window.detail_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    detail_overview_layout.addWidget(capability_box)
    if hasattr(window, "_refresh_detail_capability_overview_v1"):
        window._refresh_detail_capability_overview_v1()
    detail_overview_layout.addWidget(detail_recap_splitter)
    detail_overview_layout.addWidget(metrics_box)

    signal_box = QGroupBox("信号时间线")
    trade_box = QGroupBox("成交轨迹")
    window._style_terminal_panel(signal_box, trade_box)
    signal_layout = QVBoxLayout(signal_box)
    window.signal_table = build_table(["日期", "信号", "评分", "收盘价", "原因"])
    signal_layout.addWidget(window.signal_table)
    trade_layout = QVBoxLayout(trade_box)
    window.trades_table = build_table(["入场日期", "离场日期", "买入价", "卖出价", "股数", "盈亏", "退出原因"])
    trade_layout.addWidget(window.trades_table)

    bottom = QSplitter(Qt.Horizontal)
    bottom.setObjectName("detailTimelineSplit")
    window.detail_timeline_splitter = bottom
    bottom.setChildrenCollapsible(False)
    bottom.addWidget(signal_box)
    bottom.addWidget(trade_box)
    window._configure_splitter(bottom, [470, 690])
    detail_timeline_layout.addWidget(bottom, stretch=1)

    history_box = QGroupBox("历史战法统计")
    window._style_terminal_panel(history_box)
    history_layout = QVBoxLayout(history_box)

    history_summary_box = QGroupBox("历史战法速览")
    history_summary_box.setObjectName("detailHistorySummaryBox")
    window.detail_history_summary_box = history_summary_box
    window._style_terminal_panel(history_summary_box)
    history_summary_box.setProperty("pageTone", "detail")
    history_summary_box.setProperty("surfaceRole", "metric-band")
    history_summary_box.setProperty("sectionRole", "summary")
    history_summary_layout = QVBoxLayout(history_summary_box)
    history_summary_layout.setContentsMargins(12, 12, 12, 12)
    history_summary_layout.setSpacing(10)
    history_summary_intro = QLabel("先看当前战法、参数对比和逐笔样本状态，再往下进入统计表、曲线和热力图。")
    history_summary_intro.setObjectName("inlineHint")
    history_summary_intro.setWordWrap(True)
    history_summary_layout.addWidget(history_summary_intro)
    history_summary_grid = QGridLayout()
    history_summary_grid.setHorizontalSpacing(12)
    history_summary_grid.setVerticalSpacing(12)
    window.detail_history_summary_cards = {}
    history_summary_specs = [
        ("strategy", "当前战法", "先看当前锁定战法和收益结论。", "看统计"),
        ("compare", "参数对比", "先看场景对比和收益差。", "看对比"),
        ("trade", "逐笔样本", "先看当前逐笔样本和退出原因。", "看逐笔"),
    ]
    for index, (summary_key, title_text, detail_text, button_text) in enumerate(history_summary_specs):
        card = QFrame()
        card.setObjectName("detailHistorySummaryCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "detail")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if summary_key == "strategy" else "tonal")
        if hasattr(window, "_open_detail_history_summary_v1"):
            button.clicked.connect(lambda checked=False, current=summary_key: window._open_detail_history_summary_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        history_summary_grid.addWidget(card, 0, index)
        window.detail_history_summary_cards[summary_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    history_summary_layout.addLayout(history_summary_grid)
    detail_history_layout.addWidget(history_summary_box)

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
    period_splitter.setObjectName("detailHistoryPeriodSplit")
    window.detail_history_period_splitter = period_splitter
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
    detail_history_layout.addWidget(history_box)
    if hasattr(window, "_refresh_detail_history_summary_v1"):
        window._refresh_detail_history_summary_v1()

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
    layout.setContentsMargins(12, 12, 12, 18)
    layout.setSpacing(14)

    eyebrow, title, subtitle, badges = workspace_hero_payload("broker")
    broker_hero = window._build_workspace_hero(eyebrow, title, subtitle, badges)
    window.broker_workspace_hero = broker_hero
    broker_hero.setProperty("heroCompact", True)
    broker_hero.setProperty("pageTone", "broker")
    hero_layout = broker_hero.layout()
    if isinstance(hero_layout, QHBoxLayout):
        hero_layout.setContentsMargins(16, 10, 16, 10)
        hero_layout.setSpacing(12)
    accent_strip = broker_hero.findChild(QFrame, "workspaceHeroAccent")
    if isinstance(accent_strip, QFrame):
        accent_strip.setFixedWidth(3)
    stamp_label = broker_hero.findChild(QLabel, "workspaceHeroStamp")
    if isinstance(stamp_label, QLabel):
        stamp_label.setText("OMS / EMS")
    badge_rail = broker_hero.findChild(AdaptivePanelGrid, "workspaceBadgeRail")
    if isinstance(badge_rail, AdaptivePanelGrid):
        badge_rail.set_grid_spacing(6, 6)
        badge_rail.setMaximumWidth(320)
    layout.addWidget(broker_hero)
    window.broker_status_banner = QLabel("交易状态：待复核 | 执行阶段与闸门待确认 | 下一步：先核对委托。")
    window.broker_status_banner.setObjectName("statusBanner")
    window.broker_status_banner.setProperty("pageTone", "broker")
    layout.addWidget(window.broker_status_banner)
    window.broker_stage_label = QLabel("执行阶段：待生成委托 | 先从机会池或交易计划建立第一笔可执行委托。")
    window.broker_stage_label.setObjectName("focusStateLabel")
    window.broker_stage_label.setProperty("pageTone", "broker")
    window.broker_stage_label.setWordWrap(True)
    window.broker_stage_label.hide()
    layout.addWidget(window.broker_stage_label)
    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="broker",
            attr_prefix="broker_desk",
            eyebrow="执行中控 / 执行判断",
            title="执行判断条",
            subtitle="先确认执行阶段、主线闸门和提交条件，再进入委托提交与回执复盘。",
            badges=[
                ("看什么", "阶段 / 闸门 / 回执"),
                ("本页动作", "判执行条件"),
                ("下一步", "进入委托提交"),
            ],
        )
    )

    window.broker_stage_tabs = QTabWidget()

    broker_overview_page = QWidget()
    broker_overview_page_layout = QVBoxLayout(broker_overview_page)
    broker_overview_page_layout.setContentsMargins(0, 0, 0, 0)
    broker_overview_page_layout.setSpacing(12)
    window.broker_stage_tabs.addTab(broker_overview_page, "执行总览")

    broker_commit_page = QWidget()
    broker_commit_page_layout = QVBoxLayout(broker_commit_page)
    broker_commit_page_layout.setContentsMargins(0, 0, 0, 0)
    broker_commit_page_layout.setSpacing(12)
    window.broker_stage_tabs.addTab(broker_commit_page, "委托提交")

    broker_posttrade_page = QWidget()
    broker_posttrade_page_layout = QVBoxLayout(broker_posttrade_page)
    broker_posttrade_page_layout.setContentsMargins(0, 0, 0, 0)
    broker_posttrade_page_layout.setSpacing(12)
    window.broker_stage_tabs.addTab(broker_posttrade_page, "回执复盘")

    broker_setup_page = QWidget()
    broker_setup_page_layout = QVBoxLayout(broker_setup_page)
    broker_setup_page_layout.setContentsMargins(0, 0, 0, 0)
    broker_setup_page_layout.setSpacing(12)
    window.broker_stage_tabs.addTab(broker_setup_page, "接入维护")
    _configure_terminal_stage_tabs(
        window.broker_stage_tabs,
        page_tone="broker",
        tooltips=[
            "看执行阶段、主线闸门和关键风险。",
            "看持仓、委托队列和当前委托详情。",
            "看回执、异常偏差与复盘动作。",
            "看账户接入、运行维护与诊断。",
        ],
    )
    layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="broker",
            attr_prefix="broker",
            tab_widget=window.broker_stage_tabs,
        )
    )
    layout.addWidget(window.broker_stage_tabs, stretch=1)
    _configure_terminal_stage_tabs(
        window.broker_stage_tabs,
        page_tone="broker",
        tooltips=[
            "先看执行阶段、主线闸门与当前风险灯。",
            "看持仓、委托队列与当前委托详情。",
            "看执行回执、异常偏差与复盘动作。",
            "看账户接入、运行维护与诊断。",
        ],
    )

    broker_summary_box = QGroupBox("执行总览")
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

    profile_box = QGroupBox("账号与桥接")
    window._style_terminal_panel(profile_box)
    profile_box.setObjectName("workspaceToolPanel")
    profile_box.setProperty("sectionRole", "setup")
    profile_box.setProperty("pageTone", "broker")
    profile_grid = QGridLayout(profile_box)
    profile_grid.setContentsMargins(16, 18, 16, 16)
    profile_grid.setHorizontalSpacing(12)
    profile_grid.setVerticalSpacing(12)
    profile_grid.addWidget(
        _build_section_hint("维护券商接入、桥接环境、导出目录和提交保护项。", page_tone="broker"),
        0,
        0,
        1,
        5,
    )
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
    field_placeholders = {
        "account_name": "例如：东方财富主账户",
        "account_id": "填写券商账户编号",
        "export_dir": "统一存放计划、日志和回放",
        "sdk_module": "例如：gm.api",
        "sdk_python_path": "例如：C:\\Users\\...\\Python312\\python.exe",
        "token": "用于 SDK 校验和下单",
        "strategy_id": "用于策略脚本和回执标识",
    }
    for idx, (key, label, value) in enumerate(fields):
        row = 1 + idx // 2
        col = (idx % 2) * 2
        profile_grid.addWidget(QLabel(label), row, col)
        field = QLineEdit(value)
        field.setMinimumHeight(40)
        if hasattr(field, "setClearButtonEnabled"):
            field.setClearButtonEnabled(True)
        if key in field_placeholders:
            field.setPlaceholderText(field_placeholders[key])
        window.broker_inputs[key] = field
        profile_grid.addWidget(field, row, col + 1)

    mode_row = 5
    current_mode = profile.mode or "export"
    profile_grid.addWidget(QLabel("交易模式"), mode_row, 0)
    window.mode_combo = QComboBox()
    window.mode_combo.addItem("导出模式", "export")
    window.mode_combo.addItem("SDK 模式", "sdk")
    window.mode_combo.setCurrentIndex(0 if current_mode == "export" else 1)
    window.mode_combo.setMinimumHeight(40)
    profile_grid.addWidget(window.mode_combo, mode_row, 1)

    profile_grid.addWidget(QLabel("单笔预算"), mode_row, 2)
    window.per_trade_budget_input = QLineEdit("30000")
    window.per_trade_budget_input.setMinimumHeight(40)
    window.per_trade_budget_input.setPlaceholderText("单位：元")
    profile_grid.addWidget(window.per_trade_budget_input, mode_row, 3)
    guard_row = mode_row + 1
    profile_grid.addWidget(QLabel("提交安全"), guard_row, 0)
    window.test_submit_only_checkbox = QCheckBox("仅允许测试单")
    window.test_submit_only_checkbox.setChecked(bool(getattr(profile, "test_submit_only", True)))
    profile_grid.addWidget(window.test_submit_only_checkbox, guard_row, 1)
    profile_grid.addWidget(QLabel("测试单上限"), guard_row, 2)
    window.test_submit_max_amount_input = QLineEdit(f"{float(getattr(profile, 'test_submit_max_amount', 10000.0) or 10000.0):.0f}")
    window.test_submit_max_amount_input.setMinimumHeight(40)
    profile_grid.addWidget(window.test_submit_max_amount_input, guard_row, 3)
    whitelist_row = guard_row + 1
    profile_grid.addWidget(QLabel("测试白名单"), whitelist_row, 0)
    window.test_submit_symbol_whitelist_input = QLineEdit(str(getattr(profile, "test_submit_symbol_whitelist", "") or ""))
    window.test_submit_symbol_whitelist_input.setMinimumHeight(40)
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
        button.setMinimumHeight(40)
        button.setMinimumWidth(156)
    choose_export_button.clicked.connect(window.choose_export_dir)
    save_profile_button.clicked.connect(window.save_profile)
    create_templates_button.clicked.connect(window.create_broker_templates)
    validate_profile_button = QPushButton("校验连接")
    window._set_button_role(validate_profile_button)
    validate_profile_button.setObjectName("brokerValidateConnectionButton")
    validate_profile_button.setMinimumHeight(40)
    validate_profile_button.setMinimumWidth(156)
    validate_profile_button.clicked.connect(window.validate_broker_connection)
    window.validate_broker_connection_button = validate_profile_button
    profile_action_column = QVBoxLayout()
    profile_action_column.setContentsMargins(0, 0, 0, 0)
    profile_action_column.setSpacing(8)
    profile_action_column.addWidget(save_profile_button)
    profile_action_column.addWidget(validate_profile_button)
    profile_action_column.addWidget(choose_export_button)
    profile_action_column.addWidget(create_templates_button)
    profile_action_column.addStretch(1)
    profile_grid.addLayout(profile_action_column, 1, 4, export_row, 1)
    profile_grid.setColumnStretch(1, 1)
    profile_grid.setColumnStretch(3, 1)
    profile_grid.setColumnMinimumWidth(4, 176)

    action_box = QGroupBox("委托执行台")
    window._style_terminal_panel(action_box)
    action_box.setObjectName("workspaceToolPanel")
    action_box.setProperty("sectionRole", "command")
    action_box.setProperty("pageTone", "broker")
    action_grid = QGridLayout(action_box)
    action_grid.setContentsMargins(16, 18, 16, 16)
    action_grid.setHorizontalSpacing(10)
    action_grid.setVerticalSpacing(10)
    action_grid.addWidget(
        _build_section_hint("盘中顺序：同步账户状态，生成委托链路，复核风险闸门，再进入确认弹窗提交。", page_tone="broker"),
        0,
        0,
        1,
        4,
    )
    initial_broker_cta_labels = broker_terminal_primary_cta_labels(stage="", order_count=0, submit_count=0, has_focus_symbol=False)
    initial_broker_cta_tooltips = broker_terminal_primary_cta_tooltips(stage="", order_count=0, submit_count=0, stock_name="当前焦点")
    action_specs = [
        ("import_holdings", "导入持仓", window.import_holdings_csv, "ghost"),
        ("import_cash", "导入资金", window.import_cash_csv, "ghost"),
        ("generate", initial_broker_cta_labels["generate_text"], window.generate_order_suggestions, "accent"),
        ("export_plan", "导出计划快照", window.export_order_plan, "ghost"),
        ("export_replay", "导出提交回放", window.export_order_result_log, "ghost"),
        ("sync_sdk", "同步 SDK", window.sync_broker_via_sdk, "ghost"),
        ("generate_script", "生成 GM 脚本", window.generate_sdk_strategy_script, "ghost"),
        ("submit", initial_broker_cta_labels["confirm_text"], window.confirm_and_submit_orders, "accent"),
    ]
    action_button_names = {
        "import_holdings": "brokerImportHoldingsButton",
        "import_cash": "brokerImportCashButton",
        "generate": "brokerGenerateSuggestionsButton",
        "export_plan": "brokerExportPlanButton",
        "export_replay": "brokerExportReplayButton",
        "sync_sdk": "brokerSyncSdkButton",
        "generate_script": "brokerGenerateScriptButton",
        "submit": "brokerConfirmSubmitButton",
    }
    action_buttons: dict[str, QPushButton] = {}
    for key, label, handler, role in action_specs:
        button = QPushButton(label)
        window._set_button_role(button, role)
        button.setObjectName(action_button_names[key])
        button.setMinimumHeight(48 if key in {"generate", "submit"} else 40)
        button.clicked.connect(handler)
        action_buttons[key] = button
        if key == "generate":
            window.generate_order_suggestions_button = button
            button.setToolTip(initial_broker_cta_tooltips["generate_tooltip"])
        elif key == "submit":
            window.confirm_submit_orders_button = button
            button.setToolTip(initial_broker_cta_tooltips["confirm_tooltip"])
        elif key == "sync_sdk":
            button.setToolTip("拉取最新账户、资金和持仓状态，确保执行环境一致。")
        if handler == window.sync_broker_via_sdk:
            window.sync_broker_button = button
    action_grid.addWidget(action_buttons["generate"], 1, 0, 1, 2)
    action_grid.addWidget(action_buttons["submit"], 1, 2, 1, 2)
    action_grid.addWidget(action_buttons["import_holdings"], 2, 0)
    action_grid.addWidget(action_buttons["import_cash"], 2, 1)
    action_grid.addWidget(action_buttons["sync_sdk"], 2, 2)
    action_grid.addWidget(action_buttons["generate_script"], 2, 3)
    action_grid.addWidget(action_buttons["export_plan"], 3, 0, 1, 2)
    action_grid.addWidget(action_buttons["export_replay"], 3, 2, 1, 2)
    action_grid.setColumnStretch(0, 1)
    action_grid.setColumnStretch(1, 1)
    action_grid.setColumnStretch(2, 1)
    action_grid.setColumnStretch(3, 1)
    window.broker_action_buttons = [
        action_buttons["import_holdings"],
        action_buttons["import_cash"],
        action_buttons["generate"],
        action_buttons["export_plan"],
        action_buttons["export_replay"],
        action_buttons["sync_sdk"],
        action_buttons["generate_script"],
        action_buttons["submit"],
    ]

    broker_metrics_box = QGroupBox("关键指标")
    window.broker_metrics_box = broker_metrics_box
    window._style_terminal_panel(broker_metrics_box)
    broker_metrics_box.setProperty("pageTone", "broker")
    broker_metrics_box.setProperty("surfaceRole", "metric-band")
    broker_metrics_layout = QVBoxLayout(broker_metrics_box)
    broker_metrics_layout.setContentsMargins(14, 16, 14, 14)
    broker_metrics_layout.setSpacing(10)
    broker_metrics_layout.addWidget(
        _build_section_hint("把可提交性、资金占用、盈亏期望和风险预算放在同一行快速复核。", page_tone="broker")
    )
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

    broker_execution_box = QGroupBox("主线看板")
    window.broker_execution_box = broker_execution_box
    window._style_terminal_panel(broker_execution_box)
    broker_execution_box.setProperty("pageTone", "broker")
    broker_execution_box.setProperty("surfaceRole", "analysis")
    broker_execution_layout = QVBoxLayout(broker_execution_box)
    broker_execution_layout.setContentsMargins(14, 16, 14, 14)
    broker_execution_layout.setSpacing(10)
    broker_execution_layout.addWidget(
        _build_section_hint("先判定红灯、主线闸门和仓位约束，再决定是否进入提交确认。", page_tone="broker")
    )
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
        ("blocker", "风险灯", "等待风控结论"),
        ("mainline", "主线闸门", "等待主线审查"),
        ("action", "确认动作", "等待委托链路"),
        ("portfolio", "下一步", "等待仓位校验"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.broker_execution_summary_metric_cards[key] = card
        window.broker_execution_summary_metric_labels[key] = value_label
        window.broker_execution_summary_metric_accents[key] = accent_label
        broker_execution_summary_box.add_panel(card)
    broker_execution_layout.addWidget(broker_execution_summary_box)

    broker_gate_action_row = QHBoxLayout()
    broker_gate_action_row.setSpacing(10)
    blocker_text, blocker_tooltip = broker_terminal_focus_button_copy("blocker")
    priority_text, priority_tooltip = broker_terminal_focus_button_copy("priority")
    window.broker_focus_blocker_button = QPushButton(blocker_text)
    window.broker_focus_priority_button = QPushButton(priority_text)
    window._set_button_role(window.broker_focus_blocker_button, "ghost")
    window._set_button_role(window.broker_focus_priority_button, "accent")
    window.broker_focus_blocker_button.setMinimumHeight(38)
    window.broker_focus_priority_button.setMinimumHeight(38)
    window.broker_focus_blocker_button.setToolTip(blocker_tooltip)
    window.broker_focus_priority_button.setToolTip(priority_tooltip)
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
    window.broker_execution_text.setPlainText("生成委托链路后，这里会汇总订单节奏、确认建议和提交记录。")

    broker_execution_detail_splitter.addWidget(window.broker_mainline_review_text)
    broker_execution_detail_splitter.addWidget(window.broker_execution_text)
    window._configure_splitter(broker_execution_detail_splitter, [1, 1])
    broker_execution_layout.addWidget(broker_execution_detail_splitter)

    status_box = QGroupBox("接入诊断")
    window.broker_status_box = status_box
    window._style_terminal_panel(status_box)
    status_box.setProperty("pageTone", "broker")
    status_box.setProperty("sectionRole", "diagnostic")
    status_layout = QVBoxLayout(status_box)
    status_layout.setContentsMargins(16, 16, 16, 16)
    status_layout.setSpacing(10)
    status_layout.addWidget(
        _build_section_hint("看接入状态、桥接环境、最近校验结果和提交保护项。", page_tone="broker")
    )
    window.broker_status_text = QTextEdit()
    window.broker_status_text.setReadOnly(True)
    window.broker_status_text.setMinimumHeight(200)
    window.broker_status_text.setMaximumHeight(240)
    window._style_terminal_console(window.broker_status_text)
    status_layout.addWidget(window.broker_status_text)

    runtime_box = QGroupBox("运行维护")
    window._style_terminal_panel(runtime_box)
    runtime_box.setObjectName("workspaceToolPanel")
    runtime_box.setProperty("sectionRole", "runtime")
    runtime_box.setProperty("pageTone", "broker")
    runtime_layout = QVBoxLayout(runtime_box)
    runtime_layout.setContentsMargins(16, 18, 16, 16)
    runtime_layout.setSpacing(10)
    runtime_layout.addWidget(
        _build_section_hint("盘中只保留最关键的运行概览、诊断刷新和异常追踪。", page_tone="broker")
    )
    runtime_status_title = QLabel("运行概览")
    runtime_status_title.setObjectName("sectionTitle")
    runtime_layout.addWidget(runtime_status_title)
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
        if object_name == "runtimeClearCacheButton":
            runtime_action_row.addWidget(button, 1, 0, 1, 2)
        else:
            runtime_action_row.addWidget(button, 0, index, 1, 1)
    runtime_action_row.setColumnStretch(0, 1)
    runtime_action_row.setColumnStretch(1, 1)
    runtime_layout.addLayout(runtime_action_row)

    runtime_log_title = QLabel("事件流")
    runtime_log_title.setObjectName("sectionTitle")
    runtime_layout.addWidget(runtime_log_title)
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
    window._configure_splitter(broker_control_splitter, [620, 720, 340])
    holdings_box = QGroupBox("组合持仓")
    orders_box = QGroupBox("委托执行台")
    window._style_terminal_panel(holdings_box, orders_box)
    holdings_box.setProperty("pageTone", "broker")
    orders_box.setProperty("pageTone", "broker")
    holdings_box.setProperty("sectionRole", "portfolio")
    orders_box.setProperty("sectionRole", "execution")

    holdings_layout = QVBoxLayout(holdings_box)
    holdings_layout.setContentsMargins(16, 16, 16, 16)
    holdings_layout.setSpacing(10)
    holdings_layout.addWidget(
        _build_section_hint("优先看可卖仓位、成本和市值暴露，避免与待提交委托冲突。", page_tone="broker")
    )
    window.holdings_table = build_table(["代码", "持仓数量", "可卖数量", "成本价", "市值"])
    window.holdings_table.setMinimumHeight(300)
    window.holdings_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    holdings_layout.addWidget(window.holdings_table)

    orders_layout = QVBoxLayout(orders_box)
    orders_layout.setContentsMargins(16, 16, 16, 16)
    orders_layout.setSpacing(10)
    orders_layout.addWidget(
        _build_section_hint("左侧看待提交委托，右侧看所选委托的主线闸门、风险灯和仓位变化。", page_tone="broker")
    )
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
    middle.setMinimumHeight(560)
    middle.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    broker_detail_toggle_panel = QWidget()
    broker_detail_toggle_panel.setObjectName("brokerDetailTogglePanel")
    broker_detail_toggle_panel.setProperty("pageTone", "broker")
    detail_toggle_row = QHBoxLayout(broker_detail_toggle_panel)
    detail_toggle_row.setContentsMargins(0, 0, 0, 0)
    detail_toggle_row.setSpacing(10)
    window.broker_detail_toggle_button = QPushButton("展开执行明细")
    window._set_button_role(window.broker_detail_toggle_button, "ghost")
    window.broker_detail_toggle_button.clicked.connect(window.toggle_broker_execution_detail)
    window.broker_detail_status_label = QLabel("执行明细已折叠，先看焦点委托、阶段判断和风险闸门。")
    window.broker_detail_status_label.setObjectName("inlineHint")
    window.broker_detail_status_label.setWordWrap(True)
    detail_toggle_row.addWidget(window.broker_detail_toggle_button)
    detail_toggle_row.addWidget(window.broker_detail_status_label, stretch=1)
    window.broker_detail_toggle_panel = broker_detail_toggle_panel

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

    recap_box = QGroupBox("执行复盘")
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

    broker_cockpit_section = QFrame()
    broker_cockpit_section.setObjectName("brokerCockpitSection")
    broker_cockpit_section.setProperty("pageTone", "broker")
    broker_cockpit_layout = QVBoxLayout(broker_cockpit_section)
    broker_cockpit_layout.setContentsMargins(0, 0, 0, 0)
    broker_cockpit_layout.setSpacing(12)
    broker_cockpit_layout.addWidget(broker_summary_box)
    broker_cockpit_layout.addWidget(broker_metrics_box)
    broker_capability_box = QGroupBox("执行能力总览")
    broker_capability_box.setObjectName("brokerCapabilityBox")
    window.broker_capability_box = broker_capability_box
    window._style_terminal_panel(broker_capability_box)
    broker_capability_box.setProperty("pageTone", "broker")
    broker_capability_box.setProperty("surfaceRole", "metric-band")
    broker_capability_box.setProperty("sectionRole", "capability")
    broker_capability_layout = QVBoxLayout(broker_capability_box)
    broker_capability_layout.setContentsMargins(12, 12, 12, 12)
    broker_capability_layout.setSpacing(10)
    broker_capability_intro = QLabel("拆页后保留的执行总览、委托提交、回执复盘和接入维护从这里回补，避免执行能力像被删掉。")
    broker_capability_intro.setObjectName("inlineHint")
    broker_capability_intro.setWordWrap(True)
    broker_capability_layout.addWidget(broker_capability_intro)
    broker_capability_grid = QGridLayout()
    broker_capability_grid.setHorizontalSpacing(12)
    broker_capability_grid.setVerticalSpacing(12)
    window.broker_capability_cards = {}
    broker_capability_specs = [
        ("overview", "执行总览", "看阶段判断、主线闸门和风险灯。", "看总览"),
        ("commit", "委托提交", "看委托建议、当前委托和持仓。", "看委托"),
        ("posttrade", "回执复盘", "看回执事件、成交表和复盘动作。", "看回执"),
        ("setup", "接入维护", "看账户、执行参数和运行日志。", "看维护"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(broker_capability_specs):
        card = QFrame()
        card.setObjectName("brokerCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "broker")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key in {"commit", "posttrade"} else "tonal")
        if hasattr(window, "_open_broker_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_broker_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        broker_capability_grid.addWidget(card, index // 2, index % 2)
        window.broker_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    broker_capability_layout.addLayout(broker_capability_grid)
    broker_cockpit_layout.addWidget(broker_capability_box)
    window.broker_cockpit_section = broker_cockpit_section
    broker_overview_page_layout.addWidget(broker_cockpit_section)
    if hasattr(window, "_refresh_broker_capability_overview_v1"):
        window._refresh_broker_capability_overview_v1()

    broker_execution_column = QWidget()
    window.broker_execution_column = broker_execution_column
    broker_execution_column.setObjectName("brokerExecutionColumn")
    broker_execution_column.setProperty("pageTone", "broker")
    broker_execution_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    broker_execution_column_layout = QVBoxLayout(broker_execution_column)
    broker_execution_column_layout.setContentsMargins(0, 0, 0, 0)
    broker_execution_column_layout.setSpacing(12)
    broker_execution_column_layout.addWidget(broker_execution_box)
    broker_execution_column_layout.addWidget(broker_detail_toggle_panel)
    broker_execution_column_layout.addStretch(1)

    broker_workbench_splitter = QSplitter(Qt.Horizontal)
    broker_workbench_splitter.setObjectName("brokerWorkbenchSplitter")
    broker_workbench_splitter.setChildrenCollapsible(False)
    broker_workbench_splitter.addWidget(broker_execution_column)
    broker_workbench_splitter.addWidget(middle)
    broker_workbench_splitter.setStretchFactor(0, 5)
    broker_workbench_splitter.setStretchFactor(1, 8)
    window._configure_splitter(broker_workbench_splitter, [520, 900])
    window.broker_workbench_splitter = broker_workbench_splitter
    broker_commit_page_layout.addWidget(broker_workbench_splitter, stretch=3)

    broker_posttrade_section = QFrame()
    broker_posttrade_section.setObjectName("brokerPosttradeSection")
    broker_posttrade_section.setProperty("pageTone", "broker")
    broker_posttrade_layout = QVBoxLayout(broker_posttrade_section)
    broker_posttrade_layout.setContentsMargins(0, 0, 0, 0)
    broker_posttrade_layout.setSpacing(12)
    broker_posttrade_layout.addWidget(result_box)
    broker_posttrade_layout.addWidget(recap_box)
    window.broker_posttrade_section = broker_posttrade_section
    broker_posttrade_page_layout.addWidget(broker_posttrade_section, stretch=2)

    broker_setup_toggle_row = QHBoxLayout()
    broker_setup_toggle_row.setContentsMargins(0, 0, 0, 0)
    broker_setup_toggle_row.setSpacing(10)
    window.broker_setup_toggle_button = QPushButton(BROKER_SETUP_POLICY["toggle_text"][False])
    window._set_button_role(window.broker_setup_toggle_button, "ghost")
    window.broker_setup_toggle_button.setMinimumHeight(40)
    window.broker_setup_toggle_button.clicked.connect(window.toggle_broker_setup_panel)
    window.broker_setup_status_label = QLabel(str(BROKER_SETUP_POLICY["status_text"][False]))
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
    broker_setup_page_layout.addLayout(broker_setup_toggle_row)
    broker_setup_page_layout.addWidget(broker_setup_drawer)

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
    if hasattr(window, "search_market_symbol"):
        window.market_search_input.returnPressed.connect(window.search_market_symbol)
    if hasattr(window, "_refresh_market_search_completer_v1"):
        window._refresh_market_search_completer_v1()
    window.market_search_submit_button = QPushButton("搜股票")
    window.market_search_submit_button.setMinimumHeight(42)
    window.market_search_submit_button.setMinimumWidth(108)
    window._set_button_role(window.market_search_submit_button, "tonal")
    if hasattr(window, "search_market_symbol"):
        window.market_search_submit_button.clicked.connect(window.search_market_symbol)
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
    window.market_search_progress_bar = QProgressBar()
    window.market_search_progress_bar.setObjectName("marketSearchProgressBar")
    window.market_search_progress_bar.setTextVisible(False)
    window.market_search_progress_bar.setMinimumHeight(12)
    window.market_search_progress_bar.setMaximumHeight(12)
    window.market_search_progress_bar.setMinimumWidth(88)
    window.market_search_progress_bar.setMaximumWidth(128)
    window.market_search_progress_bar.setVisible(False)
    window.market_search_progress_bar.setRange(0, 100)
    window.market_search_progress_bar.setValue(0)
    window.dashboard_auto_refresh_checkbox = QCheckBox("自动刷新")
    window.dashboard_auto_refresh_checkbox.setMinimumHeight(40)
    window.dashboard_auto_refresh_checkbox.toggled.connect(window.toggle_dashboard_auto_refresh)
    window.dashboard_auto_refresh_checkbox.blockSignals(True)
    window.dashboard_auto_refresh_checkbox.setChecked(True)
    window.dashboard_auto_refresh_checkbox.blockSignals(False)
    window.market_status_label = QLabel(OVERVIEW_DEFAULT_STATUS_TEXT)
    window.market_status_label.setObjectName("statusBanner")
    window.market_status_label.setWordWrap(True)
    window.market_status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    window.market_status_label.setMinimumHeight(40)
    search_input_row.addWidget(window.market_search_input, stretch=3)
    search_input_row.addWidget(window.market_search_submit_button)
    search_input_row.addWidget(window.market_theme_combo, stretch=1)
    search_input_row.addWidget(window.market_history_date_combo, stretch=1)
    toolbar.addLayout(search_input_row)
    search_action_row = QHBoxLayout()
    search_action_row.setContentsMargins(0, 0, 0, 0)
    search_action_row.setSpacing(8)
    search_action_row.addWidget(window.market_refresh_button)
    search_action_row.addWidget(window.market_history_reset_button)
    search_action_row.addWidget(window.market_search_progress_bar)
    search_action_row.addWidget(window.dashboard_auto_refresh_checkbox)
    search_action_row.addWidget(window.market_status_label, stretch=1)
    toolbar.addLayout(search_action_row)
    filter_row = QGridLayout()
    window.market_filter_button_layout = filter_row
    filter_row.setHorizontalSpacing(8)
    filter_row.setVerticalSpacing(8)
    window.market_filter_buttons = {}
    filter_button_style = window._overview_outline_style("#6f8196")
    for tag in STRATEGY_FILTER_LABELS:
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
    for column in range(4):
        filter_row.setColumnStretch(column, 1)
    controls_container = QWidget()
    controls_container.setObjectName("overviewControlsContainer")
    controls_layout = QGridLayout(controls_container)
    controls_layout.setContentsMargins(0, 0, 0, 0)
    controls_layout.setHorizontalSpacing(12)
    controls_layout.setVerticalSpacing(12)
    overview_view_box = QGroupBox("视图模式")
    overview_view_box.setObjectName("overviewViewBox")
    overview_search_box = QGroupBox("筛选与控制")
    overview_search_box.setObjectName("overviewSearchBox")
    overview_tag_box = QGroupBox("快捷筛选")
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
    window.overview_controls_toggle_button = QPushButton(str(OVERVIEW_CONTROLS_POLICY["toggle_text"][False]))
    window._set_button_role(window.overview_controls_toggle_button, "ghost")
    window.overview_controls_toggle_button.setMinimumHeight(40)
    window.overview_controls_toggle_button.clicked.connect(window.toggle_overview_controls_panel)
    window.overview_controls_status_label = QLabel(str(OVERVIEW_CONTROLS_POLICY["status_text"][False]))
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
    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="overview",
            attr_prefix="overview_desk",
            eyebrow="全局态势 / 市场判断",
            title="市场判断条",
            subtitle="先定市场结构、主线焦点和下一步动作，再进入图表、候选和执行链路。",
            badges=[
                ("看什么", "结构 / 主线 / 资金"),
                ("本页动作", "定市场判断"),
                ("下一步", "进入机会池或执行中控"),
            ],
        )
    )
    capability_box = QGroupBox("总览能力总览")
    capability_box.setObjectName("overviewCapabilityBox")
    window.overview_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "overview")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的市场判断、主线龙头、消息催化和买卖决策从这里回补，避免总览能力像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.overview_capability_cards = {}
    capability_specs = [
        ("market", "市场判断", "看市场总览、主图和机会池。", "看总览"),
        ("leaders", "主线龙头", "看主线龙头和机会池焦点。", "看龙头"),
        ("news", "消息催化", "看消息催化和来源状态。", "看消息"),
        ("decision", "买卖决策", "看计划、机会池和交易入口。", "看决策"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("overviewCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "overview")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key == "decision" else "tonal")
        if hasattr(window, "_open_overview_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_overview_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, index // 2, index % 2)
        window.overview_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    layout.addWidget(capability_box)
    dashboard_metrics_box = QGroupBox("关键指标")
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
    cockpit_box = QGroupBox("主线看板")
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
        ("看机会", "recommend"),
        ("去交易", "broker"),
        ("去配置", "config"),
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

    playbook_box = QGroupBox("下一步动作")
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
        "先完成接入与交易通道配置，再刷新市场、看主线和机会池，最后进入执行中控复核委托。"
    )
    playbook_layout.addWidget(window.overview_playbook_text)
    playbook_action_row_widget = QWidget()
    playbook_action_row_widget.setObjectName("overviewPlaybookActionRow")
    playbook_action_row = QHBoxLayout(playbook_action_row_widget)
    playbook_action_row.setContentsMargins(0, 0, 0, 0)
    playbook_action_row.setSpacing(10)
    window.overview_playbook_action_buttons = []
    for label, workspace, role in [
        ("去登录", "auth", "accent"),
        ("去推荐", "recommend", "ghost"),
        ("去交易", "broker", "ghost"),
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
    overview_priority_box = QGroupBox("优先级看板")
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
    left_title.setObjectName("workspaceTitle")
    left_title.setProperty("pageTone", "overview")
    window.overview_left_title = left_title
    left_layout.addWidget(left_title)
    window.overview_intraday_container = QWidget()
    window.overview_intraday_container_layout = QVBoxLayout(window.overview_intraday_container)
    window.overview_intraday_container_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_intraday_container_layout.setSpacing(10)
    overview_intel_stack = QWidget()
    overview_intel_stack.setObjectName("overviewIntelStack")
    window.overview_intel_stack = overview_intel_stack
    overview_intel_layout = QVBoxLayout(overview_intel_stack)
    overview_intel_layout.setContentsMargins(0, 0, 0, 0)
    overview_intel_layout.setSpacing(10)

    news_quick_box = QGroupBox("消息来源")
    news_quick_box.setObjectName("overviewNewsQuickBox")
    news_quick_box.setProperty("pageTone", "overview")
    window._style_terminal_panel(news_quick_box)
    window.overview_news_quick_box = news_quick_box
    news_quick_layout = QVBoxLayout(news_quick_box)
    news_quick_layout.setContentsMargins(12, 12, 12, 12)
    news_quick_layout.setSpacing(8)
    window.overview_top_news_text = QTextEdit()
    window.overview_top_news_text.setReadOnly(True)
    window._style_terminal_console(window.overview_top_news_text)
    window.overview_top_news_text.setMinimumHeight(94)
    window.overview_top_news_text.setMaximumHeight(122)
    window.overview_top_news_text.setPlainText("消息来源\n\n这里会优先展示当前焦点最近一条可靠消息、来源渠道和动作建议。")
    news_quick_layout.addWidget(window.overview_top_news_text)
    news_quick_action_row = QHBoxLayout()
    news_quick_action_row.setContentsMargins(0, 0, 0, 0)
    news_quick_action_row.setSpacing(8)
    window.overview_top_news_source_button = QPushButton("看原文")
    window.overview_top_news_detail_button = QPushButton("看详情")
    window._set_button_role(window.overview_top_news_source_button, "ghost")
    window._set_button_role(window.overview_top_news_detail_button, "ghost")
    window.overview_top_news_source_button.setToolTip(window._news_source_button_base_tooltip())
    window.overview_top_news_detail_button.setToolTip(window._news_detail_button_base_tooltip())
    window.overview_top_news_source_button.clicked.connect(window.open_overview_focus_news_source)
    window.overview_top_news_detail_button.clicked.connect(window.open_overview_focus_news_detail)
    news_quick_action_row.addWidget(window.overview_top_news_source_button)
    news_quick_action_row.addWidget(window.overview_top_news_detail_button)
    news_quick_action_row.addStretch(1)
    news_quick_layout.addLayout(news_quick_action_row)
    overview_intel_layout.addWidget(news_quick_box)

    ai_quick_box = QGroupBox("AI评测")
    ai_quick_box.setObjectName("overviewAiQuickBox")
    ai_quick_box.setProperty("pageTone", "overview")
    window._style_terminal_panel(ai_quick_box)
    window.overview_ai_quick_box = ai_quick_box
    ai_quick_layout = QVBoxLayout(ai_quick_box)
    ai_quick_layout.setContentsMargins(12, 12, 12, 12)
    ai_quick_layout.setSpacing(8)
    window.overview_top_ai_text = QTextEdit()
    window.overview_top_ai_text.setReadOnly(True)
    window._style_terminal_console(window.overview_top_ai_text)
    window.overview_top_ai_text.setMinimumHeight(94)
    window.overview_top_ai_text.setMaximumHeight(122)
    window.overview_top_ai_text.setPlainText("AI评测\n\n这里会提示当前模型、评测状态和该不该马上复核当前焦点。")
    ai_quick_layout.addWidget(window.overview_top_ai_text)
    ai_quick_action_row = QHBoxLayout()
    ai_quick_action_row.setContentsMargins(0, 0, 0, 0)
    ai_quick_action_row.setSpacing(8)
    window.overview_top_ai_run_button = QPushButton("评测当前焦点")
    window.overview_top_ai_panel_button = QPushButton("AI设置")
    window._set_button_role(window.overview_top_ai_run_button, "tonal")
    window._set_button_role(window.overview_top_ai_panel_button, "ghost")
    window.overview_top_ai_run_button.setToolTip("直接对当前焦点发起 AI 评测。")
    window.overview_top_ai_panel_button.setToolTip("去 AI 评测设置区检查模型、Key 和自动触发。")
    window.overview_top_ai_run_button.clicked.connect(window.run_ai_review_for_selected_recommendation)
    window.overview_top_ai_panel_button.clicked.connect(lambda: window._open_config_capability_v1("ai") if hasattr(window, "_open_config_capability_v1") else None)
    ai_quick_action_row.addWidget(window.overview_top_ai_run_button)
    ai_quick_action_row.addWidget(window.overview_top_ai_panel_button)
    ai_quick_action_row.addStretch(1)
    ai_quick_layout.addLayout(ai_quick_action_row)
    overview_intel_layout.addWidget(ai_quick_box)

    window.overview_intraday_container_layout.addWidget(overview_intel_stack)
    window.intraday_chart_view = chart_view_cls()
    _configure_chart_view(window.intraday_chart_view, min_height=260)
    window.overview_intraday_container_layout.addWidget(window.intraday_chart_view)
    left_layout.addWidget(window.overview_intraday_container, stretch=5)
    signal_summary_column = QWidget()
    signal_summary_column.setObjectName("overviewSignalSummaryColumn")
    signal_summary_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
    window.overview_signal_summary_column = signal_summary_column
    window.left_signal_tabs = None
    signal_summary_layout = QVBoxLayout(signal_summary_column)
    signal_summary_layout.setContentsMargins(0, 0, 0, 0)
    signal_summary_layout.setSpacing(10)
    buy_box = QGroupBox("买入信号")
    buy_box.setObjectName("buySignalBox")
    buy_box.setProperty("pageTone", "overview")
    buy_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    window.market_buy_box = buy_box
    buy_layout = QVBoxLayout(buy_box)
    buy_layout.setContentsMargins(12, 12, 12, 12)
    buy_layout.setSpacing(8)
    window.market_buy_text = QTextEdit()
    window.market_buy_text.setReadOnly(True)
    window.market_buy_text.setObjectName("marketNotePanel")
    window.market_buy_text.setProperty("panelTone", "buy")
    window.market_buy_text.setProperty("signalSummaryRole", "buy")
    window.market_buy_text.setMinimumHeight(112)
    window.market_buy_text.setMaximumHeight(148)
    window.market_buy_text.setLineWrapMode(QTextEdit.WidgetWidth)
    window.market_buy_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_buy_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_buy_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    buy_layout.addWidget(window.market_buy_text)
    risk_box = QGroupBox("风险与退出")
    risk_box.setObjectName("riskSignalBox")
    risk_box.setProperty("pageTone", "overview")
    risk_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    window.market_sell_box = risk_box
    risk_layout = QVBoxLayout(risk_box)
    risk_layout.setContentsMargins(12, 12, 12, 12)
    risk_layout.setSpacing(8)
    window.market_sell_text = QTextEdit()
    window.market_sell_text.setReadOnly(True)
    window.market_sell_text.setObjectName("marketNotePanel")
    window.market_sell_text.setProperty("panelTone", "risk")
    window.market_sell_text.setProperty("signalSummaryRole", "risk")
    window.market_sell_text.setMinimumHeight(112)
    window.market_sell_text.setMaximumHeight(148)
    window.market_sell_text.setLineWrapMode(QTextEdit.WidgetWidth)
    window.market_sell_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_sell_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_sell_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    risk_layout.addWidget(window.market_sell_text)
    breadth_box = QGroupBox("验证与逻辑")
    breadth_box.setObjectName("breadthSignalBox")
    breadth_box.setProperty("pageTone", "overview")
    breadth_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    window.market_breadth_box = breadth_box
    breadth_layout = QVBoxLayout(breadth_box)
    breadth_layout.setContentsMargins(12, 12, 12, 12)
    breadth_layout.setSpacing(8)
    window.market_news_group = breadth_box
    window.market_breadth_text = QTextEdit()
    window.market_breadth_text.setReadOnly(True)
    window.market_breadth_text.setObjectName("marketNotePanel")
    window.market_breadth_text.setProperty("panelTone", "watch")
    window.market_breadth_text.setProperty("signalSummaryRole", "verify")
    window.market_breadth_text.setMinimumHeight(124)
    window.market_breadth_text.setMaximumHeight(172)
    window.market_breadth_text.setLineWrapMode(QTextEdit.WidgetWidth)
    window.market_breadth_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_breadth_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.market_breadth_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    breadth_layout.addWidget(window.market_breadth_text)
    breadth_action_row = QHBoxLayout()
    breadth_action_row.setContentsMargins(0, 2, 0, 0)
    breadth_action_row.setSpacing(10)
    window.market_open_news_button = QPushButton("看原文")
    window.market_news_detail_button = QPushButton("看详情")
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
    signal_summary_layout.addWidget(buy_box)
    signal_summary_layout.addWidget(risk_box)
    signal_summary_layout.addWidget(breadth_box)
    signal_summary_layout.addStretch(1)
    window.overview_signal_summary_boxes = {
        "buy": buy_box,
        "risk": risk_box,
        "verify": breadth_box,
    }
    left_layout.addWidget(signal_summary_column)
    main_splitter.addWidget(left_panel)
    center_panel = QWidget()
    center_panel.setObjectName("overviewCenterPanel")
    center_panel.setMinimumWidth(760)
    center_layout = QVBoxLayout(center_panel)
    center_layout.setContentsMargins(0, 0, 0, 0)
    center_layout.setSpacing(10)
    window.market_header_label = QLabel("市场总控台")
    window.market_header_label.setObjectName("heroTitle")
    center_layout.addWidget(window.market_header_label)
    window.market_subheader_label = QLabel("主线、资金、消息与交易温度在同一视图完成初判。")
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
    market_focus_box = QGroupBox("焦点摘要")
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
    reset_chart_button = QPushButton("回最新")
    zoom_chart_button = QPushButton("放大主图")
    fullscreen_chart_button = QPushButton("全屏看图")
    window.market_chart_prev_button = prev_chart_button
    window.market_chart_next_button = next_chart_button
    window.market_chart_reset_button = reset_chart_button
    window.market_chart_zoom_button = zoom_chart_button
    window.market_chart_fullscreen_button = fullscreen_chart_button
    window._set_button_role(prev_chart_button)
    window._set_button_role(next_chart_button)
    window._set_button_role(reset_chart_button, "tonal")
    window._set_button_role(zoom_chart_button, "ghost")
    window._set_button_role(fullscreen_chart_button, "ghost")
    prev_chart_button.setToolTip("向左翻一屏，看更早的数据。按 PageUp 也可翻屏，Shift+左键 可细步进。")
    next_chart_button.setToolTip("向右翻一屏，看更近的数据。按 PageDown 也可翻屏，Shift+右键 可细步进。")
    reset_chart_button.setToolTip("回最新窗口。按 Home 可快速重置。")
    zoom_chart_button.setToolTip("展开 K 线主图并收起副图，便于专注看主图走势。")
    fullscreen_chart_button.setToolTip("把当前 K 线主图放到独立大窗口里看，便于全屏盯图。")
    prev_chart_button.clicked.connect(lambda: window.shift_market_chart_window(1))
    next_chart_button.clicked.connect(lambda: window.shift_market_chart_window(-1))
    reset_chart_button.clicked.connect(window.reset_market_chart_window)
    zoom_chart_button.clicked.connect(window.toggle_market_primary_chart_expanded)
    fullscreen_chart_button.clicked.connect(window.open_market_chart_focus_dialog)
    chart_control_row.addWidget(prev_chart_button)
    chart_control_row.addWidget(next_chart_button)
    chart_control_row.addWidget(reset_chart_button)
    chart_control_row.addWidget(zoom_chart_button)
    chart_control_row.addWidget(fullscreen_chart_button)
    chart_control_row.addSpacing(12)
    window.market_chart_nav_label = QLabel("K 线导航：日线 | 近1年 | 第 1 屏 / 共 1 屏")
    window.market_chart_nav_label.setObjectName("inlineHint")
    window.market_chart_nav_label.setToolTip("PageUp/PageDown 翻屏，Shift+左右细步进，Home 回最新，右键打开快捷菜单，F 全屏看图，1/2/3 切换战法标注，A 循环切换，Alt+Left/Right 回看提示，Alt+C 清除筛选。")
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
    chart_control_row.addWidget(QLabel("战法标注"))
    window.market_annotation_mode_buttons = {}
    current_annotation_mode = window._normalize_market_strategy_annotation_mode(
        getattr(window, "market_strategy_annotation_mode", "FULL")
    )
    for mode_key, text in [("FULL", "完整"), ("PLAN", "计划"), ("OFF", "关闭")]:
        button = QPushButton(text)
        button.setCheckable(True)
        checked = mode_key == current_annotation_mode
        button.setChecked(checked)
        button.setMinimumHeight(34)
        button.setMinimumWidth(72)
        window._set_button_role(button, "accent" if checked else "ghost")
        button.setToolTip(
            {
                "FULL": "显示计划线、战法信号和回测买卖点标签。快捷键 1。",
                "PLAN": "只显示当前计划线和焦点相关信号。快捷键 2。",
                "OFF": "关闭战法标注，仅保留 K 线与指标。快捷键 3。",
            }.get(mode_key, "切换战法标注模式。")
        )
        button.clicked.connect(lambda checked=False, current=mode_key: window.set_market_strategy_annotation_mode(current))
        window.market_annotation_mode_buttons[mode_key] = button
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
    window.market_chart_hover_label = QLabel("图表悬浮：移动鼠标到主图或副图，可联动看同一时点；右键可直接切换图层和标注。")
    window.market_chart_hover_label.setObjectName("inlineHint")
    window.market_chart_hover_label.setWordWrap(True)
    window.market_chart_hover_label.setMinimumHeight(48)
    chart_tools_tab_layout.addWidget(window.market_chart_hover_label)

    chart_controls_tabs.addTab(timeframe_tab, "周期窗口")
    chart_controls_tabs.addTab(chart_tools_tab, "图层导航")
    _configure_terminal_stage_tabs(
        chart_controls_tabs,
        page_tone="overview",
        tooltips=[
            "切换周期、窗口和时间范围。",
            "切换图层、标注和副图指标。",
        ],
    )
    center_layout.addWidget(chart_controls_tabs)
    window.overview_primary_chart_tabs = QTabWidget()
    window.overview_primary_chart_tabs.setObjectName("compactInfoTabs")
    window.overview_daily_chart_page = QWidget()
    window.overview_daily_chart_layout = QVBoxLayout(window.overview_daily_chart_page)
    window.overview_daily_chart_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_daily_chart_layout.setSpacing(0)
    window.daily_chart_view = chart_view_cls()
    _configure_chart_view(window.daily_chart_view, min_height=420)
    window.overview_daily_chart_layout.addWidget(window.daily_chart_view)
    window.overview_intraday_chart_page = QWidget()
    window.overview_intraday_chart_layout = QVBoxLayout(window.overview_intraday_chart_page)
    window.overview_intraday_chart_layout.setContentsMargins(0, 0, 0, 0)
    window.overview_intraday_chart_layout.setSpacing(0)
    window.overview_primary_chart_tabs.addTab(window.overview_daily_chart_page, "日线主图")
    window.overview_primary_chart_tabs.addTab(window.overview_intraday_chart_page, "分时快照")
    _configure_terminal_stage_tabs(
        window.overview_primary_chart_tabs,
        page_tone="overview",
        tooltips=[
            "看主 K 线和中期结构。",
            "看分时快照和盘中承接。",
        ],
    )
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
    _configure_terminal_stage_tabs(
        mini_chart_row,
        page_tone="overview",
        tooltips=[
            "看资金强弱与增量方向。",
            "看节奏、加速和回踩。",
            "看副图指标与共振状态。",
        ],
    )
    center_layout.addWidget(mini_chart_row, stretch=2)
    window.price_chart_view = window.daily_chart_view
    window.volume_chart_view = window.fund_chart_view
    pool_box = QGroupBox("机会池")
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
    leaderboard_box = QGroupBox("前排龙头")
    leaderboard_box.setObjectName("leaderboardBox")
    window.overview_leaderboard_box = leaderboard_box
    window._style_terminal_panel(leaderboard_box)
    leaderboard_box.setProperty("pageTone", "overview")
    leaderboard_box.setProperty("surfaceRole", "analysis")
    leaderboard_layout = QVBoxLayout(leaderboard_box)
    leaderboard_layout.setContentsMargins(12, 12, 12, 12)
    leaderboard_layout.setSpacing(10)
    window.market_leaderboard_text = QTextEdit()
    window.market_leaderboard_text.setReadOnly(True)
    window.market_leaderboard_text.hide()
    window.market_leaderboard_text.setObjectName("marketNotePanel")
    leaderboard_layout.addWidget(window.market_leaderboard_text)
    window.market_leaderboard_cards = [leaderboard_card_cls() for _ in range(3)]
    for card in window.market_leaderboard_cards:
        leaderboard_layout.addWidget(card)
    overview_summary_box = QGroupBox("关键摘要")
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
    right_layout.addWidget(leaderboard_box, stretch=3)
    right_layout.addWidget(overview_summary_box, stretch=0)
    window.right_intel_tabs = QTabWidget()
    window.right_intel_tabs.setObjectName("compactInfoTabs")
    right_tab_bar = window.right_intel_tabs.tabBar()
    right_tab_bar.setUsesScrollButtons(False)
    right_tab_bar.setExpanding(True)
    right_tab_bar.setElideMode(Qt.ElideRight)
    right_tab_bar.setDocumentMode(True)
    right_layout.addWidget(window.right_intel_tabs, stretch=4)
    right_summary_box = QGroupBox("主线摘要")
    right_summary_box.setObjectName("themeSummaryBox")
    window.overview_theme_summary_box = right_summary_box
    right_summary_box.setProperty("pageTone", "overview")
    right_summary_box.setProperty("surfaceRole", "analysis")
    right_summary_layout = QVBoxLayout(right_summary_box)
    right_summary_layout.setContentsMargins(14, 14, 14, 14)
    right_summary_layout.setSpacing(10)
    window.market_theme_brief_text = QTextEdit()
    window.market_theme_brief_text.setReadOnly(True)
    window.market_theme_brief_text.setObjectName("marketNotePanel")
    window.market_theme_brief_text.setProperty("panelTone", "theme")
    window.market_theme_brief_text.setMinimumHeight(118)
    window.market_theme_brief_text.setMaximumHeight(148)
    right_summary_layout.addWidget(window.market_theme_brief_text, stretch=1)
    window.market_source_status_text = QTextEdit()
    window.market_source_status_text.setReadOnly(True)
    window.market_source_status_text.setObjectName("marketNotePanel")
    window.market_source_status_text.setProperty("panelTone", "system")
    window.market_source_status_text.setMinimumHeight(108)
    window.market_source_status_text.setMaximumHeight(136)
    right_summary_layout.addWidget(window.market_source_status_text, stretch=1)
    capital_box = QGroupBox("资金与指数")
    window.overview_capital_box = capital_box
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
    window.market_capital_text.setMinimumHeight(128)
    window.market_capital_text.setMaximumHeight(164)
    capital_layout.addWidget(window.market_capital_text)
    decision_box = QGroupBox("交易结论")
    window.overview_decision_box = decision_box
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
    window.market_decision_text.setMinimumHeight(136)
    window.market_decision_text.setMaximumHeight(176)
    decision_layout.addWidget(window.market_decision_text)
    window.right_intel_tabs.addTab(right_summary_box, "主题摘要")
    window.right_intel_tabs.addTab(capital_box, "资金画像")
    window.right_intel_tabs.addTab(decision_box, "交易决策")
    _configure_terminal_stage_tabs(
        window.right_intel_tabs,
        page_tone="overview",
        tooltips=[
            "看主线、题材与来源摘要。",
            "看资金、指数与仓位环境。",
            "看交易结论与下一步动作。",
        ],
    )
    main_splitter.addWidget(right_panel)
    window._configure_splitter(main_splitter, [260, 1220, 360])
    command_stage_layout.addWidget(main_splitter, stretch=1)
    params_box = QGroupBox("风险参数")
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
    eyebrow, title, subtitle, badges = workspace_hero_payload("recommend")

    hero = window._build_workspace_hero(
        eyebrow,
        title,
        subtitle,
        badges,
    )
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "recommend")
    layout.addWidget(hero)
    intro = QLabel("先看主线、位置、风险和催化，再看动作与送审。")
    intro.setWordWrap(True)
    intro.setObjectName("inlineHint")
    layout.addWidget(intro)

    import_profile_button = QPushButton("导入股票资料 CSV")
    import_news_button = QPushButton("导入消息面 CSV")
    import_theme_button = QPushButton("导入题材词典 CSV")
    edit_theme_button = QPushButton("编辑题材词典")
    refresh_button = QPushButton("刷新机会池")
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
    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="recommend",
            attr_prefix="recommend_desk",
            eyebrow="机会池 / 今日判断",
            title="今日机会判断",
            subtitle="先确认焦点票、送审条件和下一步动作，再进入执行审查与深度洞察。",
            badges=[
                ("看什么", "焦点 / 风险 / 送审"),
                ("本页动作", "定焦点 / 判送审"),
                ("下一步", "进入执行审查"),
            ],
        )
    )

    recommend_empty_box = QGroupBox("执行入口")
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
    strategy_filter_labels = list(STRATEGY_FILTER_LABELS)
    if "尾盘优选" not in strategy_filter_labels:
        insert_index = strategy_filter_labels.index("尾盘买入法") + 1 if "尾盘买入法" in strategy_filter_labels else len(strategy_filter_labels)
        strategy_filter_labels.insert(insert_index, "尾盘优选")
    window.recommend_strategy_combo.addItems(strategy_filter_labels)
    window.recommend_strategy_combo.currentTextChanged.connect(window._on_recommend_strategy_filter_changed)
    window.recommend_action_combo = QComboBox()
    window.recommend_action_combo.addItems(["全部", "买入", "观察", "持有", "减仓", "离场"])
    window.recommend_action_combo.setCurrentText("全部")
    window.recommend_action_combo.currentTextChanged.connect(window._on_recommend_action_filter_changed)
    window.recommend_execution_combo = QComboBox()
    window.recommend_execution_combo.addItems(["全部", "待观察", "已送审", "已提交", "提交失败"])
    window.recommend_execution_combo.setCurrentText("全部")
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
    window.recommend_action_more_button.setToolTip("看更多送审动作。")
    window.recommend_action_more_button.hide()

    controls_deck = AdaptivePanelGrid(min_item_width=360, compact_item_width=300, max_columns=3)
    controls_deck.setObjectName("recommendControlDeck")
    controls_deck.setProperty("pageTone", "recommend")
    controls_deck.set_grid_spacing(12, 12)
    data_box = QGroupBox("数据与来源")
    filter_box = QGroupBox("主线筛选")
    action_box = QGroupBox("执行动作")
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
    window.recommend_controls_toggle_button = QPushButton(str(RECOMMEND_CONTROLS_POLICY["toggle_text"][False]))
    window._set_button_role(window.recommend_controls_toggle_button, "ghost")
    window.recommend_controls_toggle_button.setMinimumHeight(40)
    window.recommend_controls_toggle_button.clicked.connect(window.toggle_recommend_controls_panel)
    window.recommend_controls_status_label = QLabel(str(RECOMMEND_CONTROLS_POLICY["status_text"][False]))
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

    recommend_focus_cards_box = QGroupBox("关键摘要")
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
        ("symbol", "Desk Focus", "等待候选同步"),
        ("theme", "主线判断", "等待主线同步"),
        ("action", "交易动作", "等待动作生成"),
        ("execution", "执行阶段", "待观察"),
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
    dispatch_box = QGroupBox("执行分发")
    focus_review_box = QGroupBox("单票复核")
    queue_box = QGroupBox("送审队列")
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
    window.recommend_news_source_button = QPushButton("看原文")
    window.recommend_news_detail_button = QPushButton("看详情")
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
    theme_box = QGroupBox("主线热度")
    leader_box = QGroupBox("前排龙头")
    window._style_terminal_panel(theme_box, leader_box)
    theme_box.setProperty("surfaceRole", "analysis")
    leader_box.setProperty("surfaceRole", "analysis")
    theme_box.setProperty("pageTone", "recommend")
    leader_box.setProperty("pageTone", "recommend")

    window.recommend_theme_box = theme_box
    theme_layout = QVBoxLayout(theme_box)
    theme_layout.setContentsMargins(12, 12, 12, 12)
    theme_layout.setSpacing(10)
    window.theme_heat_table = build_table(["题材", "热度", "延续", "窗口", "分歧", "消息", "龙头数", "排序", "风险"])
    window.theme_heat_table.verticalHeader().setDefaultSectionSize(42)
    window.theme_heat_table.setMinimumHeight(280)
    window.theme_heat_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.theme_heat_table.itemSelectionChanged.connect(window._on_theme_heat_selection_changed)
    theme_layout.addWidget(window.theme_heat_table)

    window.recommend_leader_box = leader_box
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

    section_hint = QLabel("推荐台只保留 3 个核心动作：定焦点、过门槛、进执行。辅助洞察按需展开。")
    section_hint.setObjectName("inlineHint")
    window.recommend_section_hint = section_hint

    decision_summary_box = QGroupBox("执行动作卡")
    window.recommend_decision_summary_box = decision_summary_box
    window._style_terminal_panel(decision_summary_box)
    decision_summary_box.setProperty("surfaceRole", "spotlight")
    decision_summary_box.setProperty("pageTone", "recommend")
    decision_summary_layout = QVBoxLayout(decision_summary_box)
    decision_summary_layout.setContentsMargins(14, 14, 14, 14)
    decision_summary_layout.setSpacing(10)
    window.recommend_decision_summary_label = QLabel("先确认焦点票，再判断是否具备推进计划与送审的条件。")
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
    initial_recommend_cta_labels = recommend_terminal_cta_labels(can_submit=True, can_open_broker=True, execution_state="")
    window.recommend_push_focus_button = QPushButton(initial_recommend_cta_labels["push"])
    window.recommend_detail_focus_button = QPushButton(initial_recommend_cta_labels["detail"])
    window.recommend_broker_focus_button = QPushButton(initial_recommend_cta_labels["broker"])
    _configure_recommend_focus_action(
        window,
        window.recommend_push_focus_button,
        role="accent",
        tooltip=recommend_focus_action_tooltip("push", "送审当前焦点股票。系统会结合结论、价格计划和风险状态判断是否适合进入送审链路。"),
        handler=window.push_selected_recommendation_to_broker,
    )
    _configure_recommend_focus_action(
        window,
        window.recommend_detail_focus_button,
        role="ghost",
        tooltip=recommend_focus_action_tooltip("detail", "跳到复盘页，继续看信号、执行回放、失效条件和近期消息。"),
        handler=window.open_selected_recommend_in_detail,
    )
    _configure_recommend_focus_action(
        window,
        window.recommend_broker_focus_button,
        role="tonal",
        tooltip=recommend_focus_action_tooltip("broker", "跳到执行中控，看这只股票对应的交易计划、委托建议和回执链路。"),
        handler=window.open_selected_recommend_in_broker,
    )
    decision_action_row.addWidget(window.recommend_push_focus_button)
    decision_action_row.addWidget(window.recommend_detail_focus_button)
    decision_action_row.addWidget(window.recommend_broker_focus_button)
    decision_action_row.addStretch(1)
    decision_summary_layout.addLayout(decision_action_row)
    layout.addWidget(decision_summary_box)

    window.recommend_workflow_tabs = QTabWidget()
    window.recommend_workflow_tabs.setObjectName("compactInfoTabs")

    recommend_overview_page = QWidget()
    recommend_overview_layout = QVBoxLayout(recommend_overview_page)
    recommend_overview_layout.setContentsMargins(0, 0, 0, 0)
    recommend_overview_layout.setSpacing(12)
    window.recommend_workflow_tabs.addTab(recommend_overview_page, "机会总览")

    recommend_review_page = QWidget()
    recommend_review_layout = QVBoxLayout(recommend_review_page)
    recommend_review_layout.setContentsMargins(0, 0, 0, 0)
    recommend_review_layout.setSpacing(12)
    window.recommend_workflow_tabs.addTab(recommend_review_page, "执行审查")

    recommend_deep_page = QWidget()
    recommend_deep_layout = QVBoxLayout(recommend_deep_page)
    recommend_deep_layout.setContentsMargins(0, 0, 0, 0)
    recommend_deep_layout.setSpacing(12)
    window.recommend_workflow_tabs.addTab(recommend_deep_page, "深度洞察")
    _configure_terminal_stage_tabs(
        window.recommend_workflow_tabs,
        page_tone="recommend",
        tooltips=[
            "看焦点票、机会池和基础控制台。",
            "看分发、单票复核和送审队列。",
            "看主线热度、战法、计划与消息中心。",
        ],
    )
    layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="recommend",
            attr_prefix="recommend",
            tab_widget=window.recommend_workflow_tabs,
        )
    )
    layout.addWidget(window.recommend_workflow_tabs, stretch=4)

    recommend_overview_layout.addWidget(window.recommend_empty_box)
    recommend_overview_layout.addWidget(recommend_controls_section)

    capability_box = QGroupBox("机会能力总览")
    capability_box.setObjectName("recommendCapabilityBox")
    window.recommend_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "recommend")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的战法中控、策略细节、今日计划和复盘消息从这里回补，避免旧功能像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.recommend_capability_cards = {}
    capability_specs = [
        ("strategy", "战法中控", "看战法卡组、动作流和优先级看板。", "看战法"),
        ("detail", "策略细节", "看规则细节、失效条件和主线推演。", "看细节"),
        ("plan", "今日计划", "看计划表、执行聚焦和持仓建议。", "看计划"),
        ("ai", "AI评测", "看当前焦点评测、流式生成和最近缓存。", "看AI评测"),
        ("recap", "复盘消息", "看统一消息中心和复盘消息流。", "看消息"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("recommendCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "recommend")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key in {"strategy", "ai", "recap"} else "tonal")
        if hasattr(window, "_open_recommend_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_recommend_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, index // 2, index % 2)
        window.recommend_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    recommend_overview_layout.addWidget(capability_box)
    recommend_overview_layout.addWidget(pool_box, stretch=3)
    recommend_overview_layout.addWidget(section_hint)
    recommend_review_layout.addWidget(dispatch_splitter, stretch=2)

    deep_summary_box = QGroupBox("深度洞察速览")
    deep_summary_box.setObjectName("recommendDeepSummaryBox")
    window.recommend_deep_summary_box = deep_summary_box
    window._style_terminal_panel(deep_summary_box)
    deep_summary_box.setProperty("pageTone", "recommend")
    deep_summary_box.setProperty("surfaceRole", "metric-band")
    deep_summary_box.setProperty("sectionRole", "summary")
    deep_summary_layout = QVBoxLayout(deep_summary_box)
    deep_summary_layout.setContentsMargins(12, 12, 12, 12)
    deep_summary_layout.setSpacing(10)
    deep_summary_intro = QLabel("先看主线热度、战法中控、今日计划和消息中心，再往下进入多分栏深度研判。")
    deep_summary_intro.setObjectName("inlineHint")
    deep_summary_intro.setWordWrap(True)
    deep_summary_layout.addWidget(deep_summary_intro)
    deep_summary_grid = QGridLayout()
    deep_summary_grid.setHorizontalSpacing(12)
    deep_summary_grid.setVerticalSpacing(12)
    window.recommend_deep_summary_cards = {}
    deep_summary_specs = [
        ("theme", "主线热度", "先看当前主线、龙头焦点和延续窗口。", "看主线"),
        ("strategy", "战法中控", "先看战法卡组、明细和主线映射。", "看战法"),
        ("plan", "今日计划", "先看计划决议、仓位建议和执行顺序。", "看计划"),
        ("recap", "消息中心", "先看消息、AI 评测和复盘待办。", "看消息"),
    ]
    for index, (summary_key, title_text, detail_text, button_text) in enumerate(deep_summary_specs):
        card = QFrame()
        card.setObjectName("recommendDeepSummaryCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "recommend")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if summary_key in {"theme", "strategy"} else "tonal")
        if hasattr(window, "_open_recommend_deep_summary_v1"):
            button.clicked.connect(lambda checked=False, current=summary_key: window._open_recommend_deep_summary_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        deep_summary_grid.addWidget(card, index // 2, index % 2)
        window.recommend_deep_summary_cards[summary_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    deep_summary_layout.addLayout(deep_summary_grid)
    recommend_deep_layout.addWidget(deep_summary_box)
    recommend_deep_layout.addWidget(summary_splitter, stretch=1)

    stage_control_row = QHBoxLayout()
    stage_control_row.setContentsMargins(0, 2, 0, 0)
    stage_control_row.setSpacing(10)
    window.recommend_stage_toggle_button = QPushButton(str(RECOMMEND_AUX_STAGE_POLICY["toggle_text"][False]))
    window._set_button_role(window.recommend_stage_toggle_button, "ghost")
    window.recommend_stage_toggle_button.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["toggle_tooltip"][False]))
    window.recommend_stage_toggle_button.clicked.connect(window.toggle_recommend_auxiliary_stage)
    window.recommend_stage_status_label = QLabel(str(RECOMMEND_AUX_STAGE_POLICY["status_text"][False]))
    window.recommend_stage_status_label.setObjectName("inlineHint")
    window.recommend_stage_status_label.setWordWrap(True)
    window.recommend_stage_status_label.setToolTip(str(RECOMMEND_AUX_STAGE_POLICY["status_tooltip"][False]))
    stage_control_row.addWidget(window.recommend_stage_toggle_button)
    stage_control_row.addWidget(window.recommend_stage_status_label, stretch=1)
    recommend_deep_layout.addLayout(stage_control_row)

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
    recommend_deep_layout.addWidget(window.recommend_stage_container, stretch=3)
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
    core_bucket_box = QGroupBox("主线前排执行桶")
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

    strategy_pack_box = QGroupBox("战法中控")
    window.strategy_pack_box = strategy_pack_box
    window._style_terminal_panel(strategy_pack_box)
    strategy_pack_box.setProperty("surfaceRole", "metric-band")
    strategy_pack_box.setProperty("pageTone", "recommend")
    strategy_pack_layout = QGridLayout(strategy_pack_box)
    window.strategy_pack_layout = strategy_pack_layout
    window.strategy_workbench_card_cls = strategy_workbench_card_cls
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
    window.strategy_detail_box = strategy_detail_box
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
        seed_text="等待机会池。",
    )
    strategy_detail_layout.addWidget(window.strategy_detail_text)
    decision_layout.addWidget(strategy_detail_box, stretch=1)

    action_flow_box = QGroupBox("动作流程")
    window.action_flow_box = action_flow_box
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

    priority_box = QGroupBox("优先级看板")
    window.priority_box = priority_box
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

    alert_box = QGroupBox("风险提醒")
    window.alert_box = alert_box
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
    window.strategy_path_box = strategy_path_box
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
        seed_text="等待机会池。",
    )
    strategy_path_layout.addWidget(window.strategy_path_text)
    decision_layout.addWidget(strategy_path_box, stretch=1)

    summary_cards_box = QGroupBox("关键摘要")
    window.summary_cards_box = summary_cards_box
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
    window.recommend_message_center_box = message_center_box
    window._style_terminal_panel(message_center_box)
    message_center_box.setProperty("surfaceRole", "analysis")
    message_center_box.setProperty("pageTone", "recommend")
    message_center_layout = QVBoxLayout(message_center_box)
    message_center_layout.setContentsMargins(12, 12, 12, 12)
    message_center_layout.setSpacing(10)
    message_center_header = QHBoxLayout()
    message_center_header.setContentsMargins(0, 0, 0, 0)
    message_center_header.setSpacing(10)
    window.recommend_message_center_summary_label = QLabel("等待消息中心更新")
    window.recommend_message_center_summary_label.setObjectName("focusStateLabel")
    window.recommend_message_center_summary_label.setProperty("pageTone", "recommend")
    window.recommend_message_center_summary_label.setWordWrap(True)
    window.recommend_message_center_badge_label = QLabel("未读 0 | 待办 0")
    window.recommend_message_center_badge_label.setObjectName("workspaceHeroStamp")
    window.recommend_message_center_filter_combo = QComboBox()
    for label, value in [
        ("全部", "all"),
        ("AI", "ai"),
        ("消息", "news"),
        ("交易", "trade"),
        ("系统", "system"),
    ]:
        window.recommend_message_center_filter_combo.addItem(label, value)
    window.recommend_message_center_sort_combo = QComboBox()
    for label, value in [
        ("最新优先", "latest"),
        ("未读优先", "unread"),
        ("待处理优先", "open"),
        ("异常优先", "priority"),
    ]:
        window.recommend_message_center_sort_combo.addItem(label, value)
    window.recommend_message_center_unhandled_checkbox = QCheckBox("只看待办")
    current_filter = str(getattr(window, "recommend_message_center_filter", "all") or "all")
    for index in range(window.recommend_message_center_filter_combo.count()):
        if window.recommend_message_center_filter_combo.itemData(index) == current_filter:
            window.recommend_message_center_filter_combo.setCurrentIndex(index)
            break
    current_sort = str(getattr(window, "recommend_message_center_sort", "latest") or "latest")
    for index in range(window.recommend_message_center_sort_combo.count()):
        if window.recommend_message_center_sort_combo.itemData(index) == current_sort:
            window.recommend_message_center_sort_combo.setCurrentIndex(index)
            break
    window.recommend_message_center_unhandled_checkbox.setChecked(bool(getattr(window, "recommend_message_center_show_unhandled_only", False)))
    if hasattr(window, "_on_recommend_message_center_filter_changed"):
        window.recommend_message_center_filter_combo.currentIndexChanged.connect(window._on_recommend_message_center_filter_changed)
    if hasattr(window, "_on_recommend_message_center_sort_changed"):
        window.recommend_message_center_sort_combo.currentIndexChanged.connect(window._on_recommend_message_center_sort_changed)
    if hasattr(window, "_on_recommend_message_center_unhandled_toggled"):
        window.recommend_message_center_unhandled_checkbox.toggled.connect(window._on_recommend_message_center_unhandled_toggled)
    window.recommend_message_center_clear_button = QPushButton(message_center_button_label("clear", "清空"))
    window._set_button_role(window.recommend_message_center_clear_button, "ghost")
    if hasattr(window, "clear_recommend_message_center"):
        window.recommend_message_center_clear_button.clicked.connect(window.clear_recommend_message_center)
    window.recommend_message_center_mark_all_read_button = QPushButton(message_center_button_label("mark_all_read", "全标已读"))
    window._set_button_role(window.recommend_message_center_mark_all_read_button, "ghost")
    if hasattr(window, "mark_all_recommend_messages_read"):
        window.recommend_message_center_mark_all_read_button.clicked.connect(window.mark_all_recommend_messages_read)
    window.recommend_message_center_clear_handled_button = QPushButton(message_center_button_label("clear_handled", "清已办"))
    window._set_button_role(window.recommend_message_center_clear_handled_button, "ghost")
    if hasattr(window, "clear_handled_recommend_message_events"):
        window.recommend_message_center_clear_handled_button.clicked.connect(window.clear_handled_recommend_message_events)
    message_center_header.addWidget(window.recommend_message_center_summary_label, stretch=1)
    message_center_header.addWidget(window.recommend_message_center_badge_label)
    message_center_header.addWidget(window.recommend_message_center_filter_combo)
    message_center_header.addWidget(window.recommend_message_center_sort_combo)
    message_center_header.addWidget(window.recommend_message_center_unhandled_checkbox)
    message_center_header.addWidget(window.recommend_message_center_mark_all_read_button)
    message_center_header.addWidget(window.recommend_message_center_clear_handled_button)
    message_center_header.addWidget(window.recommend_message_center_clear_button)
    message_center_layout.addLayout(message_center_header)
    message_center_metric_band = AdaptivePanelGrid(min_item_width=142, compact_item_width=132, max_columns=5)
    message_center_metric_band.setObjectName("recommendMessageCenterMetricBand")
    message_center_metric_band.set_grid_spacing(8, 8)
    window.recommend_message_center_metric_cards = {}
    window.recommend_message_center_metric_labels = {}
    window.recommend_message_center_metric_accents = {}
    for key, title, accent in [
        ("unread", "未读", "待看"),
        ("open", "待处理", "等待消化"),
        ("ai", "AI 事件", "研究辅助"),
        ("news", "消息事件", "消息驱动"),
        ("trade", "交易事件", "执行回执"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", message_center_metric_accent(key, accent))
        window.recommend_message_center_metric_cards[key] = card
        window.recommend_message_center_metric_labels[key] = value_label
        window.recommend_message_center_metric_accents[key] = accent_label
        message_center_metric_band.add_panel(card)
    message_center_layout.addWidget(message_center_metric_band)
    window.recommend_message_center_table = build_table(["时间", "类型", "状态", "事件", "标的"])
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
    window.recommend_message_center_action_label = QLabel(message_center_action_bar_text(None))
    window.recommend_message_center_action_label.setObjectName("inlineHint")
    window.recommend_message_center_action_label.setWordWrap(True)
    window.recommend_message_center_mark_read_button = QPushButton(message_center_button_label("mark_read", "标已读"))
    window.recommend_message_center_mark_handled_button = QPushButton(message_center_button_label("mark_handled", "标已办"))
    window.recommend_message_center_symbol_button = QPushButton(message_center_button_label("symbol", "定位股票"))
    window.recommend_message_center_open_button = QPushButton(message_center_button_label("open", "看关联页"))
    window._set_button_role(window.recommend_message_center_mark_read_button, "ghost")
    window._set_button_role(window.recommend_message_center_mark_handled_button, "tonal")
    window._set_button_role(window.recommend_message_center_symbol_button, "tonal")
    window._set_button_role(window.recommend_message_center_open_button, "accent")
    if hasattr(window, "mark_selected_recommend_message_read"):
        window.recommend_message_center_mark_read_button.clicked.connect(window.mark_selected_recommend_message_read)
    if hasattr(window, "mark_selected_recommend_message_handled"):
        window.recommend_message_center_mark_handled_button.clicked.connect(window.mark_selected_recommend_message_handled)
    if hasattr(window, "focus_selected_recommend_message_symbol"):
        window.recommend_message_center_symbol_button.clicked.connect(window.focus_selected_recommend_message_symbol)
    if hasattr(window, "open_selected_recommend_message_event"):
        window.recommend_message_center_open_button.clicked.connect(window.open_selected_recommend_message_event)
    message_center_action_row.addWidget(window.recommend_message_center_action_label, stretch=1)
    message_center_action_row.addWidget(window.recommend_message_center_mark_read_button)
    message_center_action_row.addWidget(window.recommend_message_center_mark_handled_button)
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
        seed_text=build_message_center_snapshot([], category_filter="all")["text"],
    )
    message_center_layout.addWidget(window.recommend_message_center_text)
    recap_layout.addWidget(message_center_box, stretch=1)
    if hasattr(window, "_refresh_recommend_message_center"):
        window._refresh_recommend_message_center()
    if hasattr(window, "_refresh_recommend_capability_overview_v1"):
        window._refresh_recommend_capability_overview_v1()

    detail_box = QGroupBox("主线说明")
    plan_box = QGroupBox("今日计划")
    pulse_box = QGroupBox("市场温度")
    holding_box = QGroupBox("持仓建议")
    window.recommend_detail_box = detail_box
    window.recommend_plan_box = plan_box
    window.recommend_pulse_box = pulse_box
    window.recommend_holding_box = holding_box
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
    window.trade_plan_focus_label = QLabel(TRADE_PLAN_DEFAULT_FOCUS_TEXT)
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

    window.trade_plan_empty_actions = QFrame()
    window.trade_plan_empty_actions.setObjectName("emptyActionBar")
    window.trade_plan_empty_actions.setProperty("actionRow", True)
    empty_actions_layout = QHBoxLayout(window.trade_plan_empty_actions)
    empty_actions_layout.setContentsMargins(10, 8, 10, 8)
    empty_actions_layout.setSpacing(8)
    refresh_empty_button = QPushButton("重算计划")
    watch_empty_button = QPushButton("看观察")
    broker_empty_button = QPushButton("去交易")
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
        seed_text="等待机会池生成后，再更新市场温度和仓位建议。",
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

    recommend_review_column = QWidget()
    recommend_review_column.setObjectName("recommendReviewColumn")
    recommend_review_column.setProperty("pageTone", "recommend")
    recommend_review_column.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    window.recommend_review_column = recommend_review_column
    recommend_review_column_layout = QVBoxLayout(recommend_review_column)
    recommend_review_column_layout.setContentsMargins(0, 0, 0, 0)
    recommend_review_column_layout.setSpacing(10)

    recommend_review_splitter = QSplitter(Qt.Horizontal)
    window.recommend_review_splitter = recommend_review_splitter
    recommend_review_splitter.setProperty("pageTone", "recommend")
    recommend_review_splitter.setChildrenCollapsible(False)
    recommend_review_splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    recommend_review_box = QGroupBox("执行复盘")
    recommend_next_day_box = QGroupBox("次日计划")
    recommend_ai_review_box = QGroupBox("AI评测")
    window.recommend_review_box = recommend_review_box
    window.recommend_next_day_box = recommend_next_day_box
    window.recommend_ai_review_box = recommend_ai_review_box
    window._style_terminal_panel(recommend_review_box, recommend_next_day_box, recommend_ai_review_box)
    recommend_review_box.setProperty("surfaceRole", "analysis")
    recommend_next_day_box.setProperty("surfaceRole", "analysis")
    recommend_ai_review_box.setProperty("surfaceRole", "analysis")
    recommend_review_box.setProperty("pageTone", "recommend")
    recommend_next_day_box.setProperty("pageTone", "recommend")
    recommend_ai_review_box.setProperty("pageTone", "recommend")
    recommend_review_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    recommend_next_day_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    recommend_ai_review_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    recommend_ai_review_box.setMinimumHeight(300)

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
        min_height=236,
        max_height=340,
        seed_text="AI评测会结合推荐、消息和单票上下文，给出一份外部模型复核意见。",
    )
    window.recommend_ai_review_text.setMinimumWidth(0)
    recommend_ai_review_layout.addWidget(window.recommend_ai_review_text)

    recommend_review_splitter.addWidget(recommend_review_box)
    recommend_review_splitter.addWidget(recommend_next_day_box)
    window._configure_splitter(recommend_review_splitter, [520, 520])
    recommend_review_column_layout.addWidget(recommend_review_splitter)
    recommend_review_column_layout.addWidget(recommend_ai_review_box)
    recap_layout.addWidget(recommend_review_column, stretch=2)

def build_board_workspace(window, build_table, header_view_cls) -> None:
    layout = QVBoxLayout(window.board_tab)
    layout.setContentsMargins(10, 10, 10, 10)
    layout.setSpacing(10)
    window.board_tab.setObjectName("boardRoot")
    eyebrow, title, subtitle, badges = workspace_hero_payload("board")

    hero = window._build_workspace_hero(
        eyebrow,
        title,
        subtitle,
        badges,
    )
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "board")
    layout.addWidget(hero)

    window.board_status_banner = QLabel("专项状态：待同步 | 候选池与回封监控待建立 | 下一步：刷新专项候选。")
    window.board_status_banner.setObjectName("statusBanner")
    window.board_status_banner.setProperty("pageTone", "board")
    window.board_status_banner.setWordWrap(True)
    layout.addWidget(window.board_status_banner)

    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="board",
            attr_prefix="board_desk",
            eyebrow="涨停策略 / 专项判断",
            title="专项判断条",
            subtitle="先定强势候选、回封质量和执行准备，再进入候选总览与回封监控。",
            badges=[
                ("看什么", "候选 / 回封 / 风险"),
                ("本页动作", "筛候选 / 看回封"),
                ("下一步", "进入候选 / 监控"),
            ],
        )
    )

    board_summary_box = QGroupBox("专项摘要")
    window.board_summary_box = board_summary_box
    window._style_terminal_panel(board_summary_box)
    board_summary_box.setProperty("pageTone", "board")
    board_summary_box.setProperty("surfaceRole", "metric-band")
    board_summary_layout = QVBoxLayout(board_summary_box)
    board_summary_layout.setContentsMargins(12, 12, 12, 12)
    board_summary_layout.setSpacing(0)
    board_summary_band = AdaptivePanelGrid(min_item_width=220, compact_item_width=188, max_columns=4)
    board_summary_band.setObjectName("boardSummaryBand")
    board_summary_band.set_grid_spacing(10, 10)
    window.board_summary_metric_cards = {}
    window.board_summary_metric_labels = {}
    window.board_summary_metric_accents = {}
    for key, title, accent in [
        ("candidate", "专项候选", "等待候选池建立"),
        ("monitor", "回封监控", "等待监控联动"),
        ("focus", "当前焦点", "等待跨页同步"),
        ("next", "下一步", "先刷新专项候选"),
    ]:
        card, value_label, accent_label = window._create_metric_card(title, "--", accent)
        window.board_summary_metric_cards[key] = card
        window.board_summary_metric_labels[key] = value_label
        window.board_summary_metric_accents[key] = accent_label
        board_summary_band.add_panel(card)
    board_summary_layout.addWidget(board_summary_band)
    layout.addWidget(board_summary_box)

    tool_panel = QGroupBox("涨停执行台")
    window.board_tool_panel = tool_panel
    tool_panel.setObjectName("workspaceToolPanel")
    tool_layout = QGridLayout(tool_panel)
    tool_layout.setContentsMargins(14, 12, 14, 12)
    tool_layout.setHorizontalSpacing(16)
    tool_layout.setVerticalSpacing(10)

    control_row = QHBoxLayout()
    window.board_tool_action_row = control_row
    control_row.setSpacing(8)
    refresh_button = QPushButton("刷新候选")
    plan_export_button = QPushButton("导出计划", tool_panel)
    export_button = QPushButton("导出复盘", tool_panel)
    window.auto_review_export_checkbox = QCheckBox("15:05 后自动导出")
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
    window.board_tool_more_button.setToolTip("看更多打板动作。")
    window.board_tool_more_button.hide()
    refresh_button.clicked.connect(window._refresh_board_mode)
    plan_export_button.clicked.connect(window.export_daily_trade_plan_from_ui)
    export_button.clicked.connect(window.export_end_of_day_review_from_ui)
    control_row.addWidget(refresh_button)
    control_row.addWidget(window.board_tool_more_button)
    control_row.addStretch(1)
    tool_layout.addLayout(control_row, 0, 0)

    board_controls_toggle_row = QHBoxLayout()
    board_controls_toggle_row.setContentsMargins(0, 0, 0, 0)
    board_controls_toggle_row.setSpacing(10)
    window.board_controls_toggle_button = QPushButton(str(BOARD_CONTROLS_POLICY["toggle_text"][False]))
    window._set_button_role(window.board_controls_toggle_button, "ghost")
    window.board_controls_toggle_button.setMinimumHeight(40)
    window.board_controls_toggle_button.clicked.connect(window.toggle_board_controls_panel)
    window.board_controls_status_label = QLabel(str(BOARD_CONTROLS_POLICY["status_text"][False]))
    window.board_controls_status_label.setObjectName("inlineHint")
    window.board_controls_status_label.setProperty("pageTone", "board")
    window.board_controls_status_label.setWordWrap(True)
    window.board_controls_status_label.setMinimumHeight(42)
    board_controls_toggle_row.addWidget(window.board_controls_toggle_button)
    board_controls_toggle_row.addWidget(window.board_controls_status_label, stretch=1)
    tool_layout.addLayout(board_controls_toggle_row, 0, 1)

    board_hint = QLabel("围绕高辨识度强势股，统一看专项候选、回封监控、导出计划和收盘复盘。")
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
    board_controls_drawer = QFrame()
    board_controls_drawer.setObjectName("boardControlsDrawer")
    board_controls_drawer.setProperty("actionRow", True)
    board_controls_layout = QVBoxLayout(board_controls_drawer)
    board_controls_layout.setContentsMargins(14, 14, 14, 14)
    board_controls_layout.setSpacing(10)
    board_controls_actions = QHBoxLayout()
    board_controls_actions.setContentsMargins(0, 0, 0, 0)
    board_controls_actions.setSpacing(10)
    window.board_controls_plan_button = QPushButton("导出计划")
    window.board_controls_review_button = QPushButton("导出复盘")
    window._set_button_role(window.board_controls_plan_button, "tonal")
    window._set_button_role(window.board_controls_review_button, "ghost")
    window.board_controls_plan_button.clicked.connect(window.export_daily_trade_plan_from_ui)
    window.board_controls_review_button.clicked.connect(window.export_end_of_day_review_from_ui)
    board_controls_actions.addWidget(window.board_controls_plan_button)
    board_controls_actions.addWidget(window.board_controls_review_button)
    board_controls_actions.addWidget(window.auto_review_export_checkbox)
    board_controls_actions.addStretch(1)
    board_controls_layout.addLayout(board_controls_actions)
    board_controls_layout.addWidget(board_meta)
    window.board_controls_drawer = board_controls_drawer
    tool_layout.addWidget(board_controls_drawer, 1, 0, 1, 2)
    tool_layout.setColumnStretch(0, 3)
    tool_layout.setColumnStretch(1, 2)
    layout.addWidget(tool_panel)

    window.board_stage_tabs = QTabWidget()
    window.board_stage_tabs.setObjectName("compactInfoTabs")

    board_candidate_page = QWidget()
    board_candidate_layout = QVBoxLayout(board_candidate_page)
    board_candidate_layout.setContentsMargins(0, 0, 0, 0)
    board_candidate_layout.setSpacing(12)
    window.board_stage_tabs.addTab(board_candidate_page, "候选总览")

    board_monitor_page = QWidget()
    board_monitor_layout_wrapper = QVBoxLayout(board_monitor_page)
    board_monitor_layout_wrapper.setContentsMargins(0, 0, 0, 0)
    board_monitor_layout_wrapper.setSpacing(12)
    window.board_stage_tabs.addTab(board_monitor_page, "回封监控")
    _configure_terminal_stage_tabs(
        window.board_stage_tabs,
        page_tone="board",
        tooltips=[
            "看涨停候选、计划买点与专项判断。",
            "看回封概率、炸板风险与动作建议。",
        ],
    )
    layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="board",
            attr_prefix="board",
            tab_widget=window.board_stage_tabs,
        )
    )
    layout.addWidget(window.board_stage_tabs, stretch=1)

    candidate_box = QGroupBox("涨停候选池")
    monitor_box = QGroupBox("回封监控")
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
    window.board_text.setPlainText("先生成机会池，再生成打板候选。")
    candidate_layout.addWidget(window.board_text)

    capability_box = QGroupBox("打板能力总览")
    capability_box.setObjectName("boardCapabilityBox")
    window.board_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "board")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的候选判断、回封监控和执行准备从这里回补，避免打板能力像被删掉。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.board_capability_cards = {}
    capability_specs = [
        ("candidate", "候选判断", "看打板候选池、计划买点和专项判断。", "看候选"),
        ("monitor", "回封监控", "看回封观察、炸板风险和动作建议。", "看监控"),
        ("execution", "执行准备", "把候选送进交易链路，继续看委托与执行。", "去交易"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("boardCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "board")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key == "execution" else "tonal")
        if hasattr(window, "_open_board_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_board_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, 0, index)
        window.board_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    board_candidate_layout.addWidget(capability_box)
    if hasattr(window, "_refresh_board_capability_overview_v1"):
        window._refresh_board_capability_overview_v1()

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
    board_candidate_layout.addWidget(candidate_box, stretch=1)
    board_monitor_layout_wrapper.addWidget(monitor_box, stretch=1)

def _build_config_workspace_core(window) -> None:
    window.config_tab.setObjectName("configRoot")
    root_layout = QVBoxLayout(window.config_tab)
    root_layout.setContentsMargins(0, 0, 0, 0)
    root_layout.setSpacing(0)

    window.config_workspace_scroll_area = QScrollArea()
    window.config_workspace_scroll_area.setWidgetResizable(True)
    window.config_workspace_scroll_area.setFrameShape(QFrame.NoFrame)
    window.config_workspace_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    window.config_workspace_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    root_layout.addWidget(window.config_workspace_scroll_area)

    config_content = QWidget()
    config_content.setObjectName("configWorkspaceContent")
    layout = QVBoxLayout(config_content)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(12)
    window.config_workspace_scroll_area.setWidget(config_content)
    eyebrow, title, subtitle, badges = workspace_hero_payload("config")

    hero = window._build_workspace_hero(
        eyebrow,
        title,
        subtitle,
        [
            badges[0] if len(badges) > 0 else ("风险", "当前档位"),
            ("授权", window.state.license_plan or "TRIAL"),
        ],
    )
    hero.setProperty("heroCompact", True)
    hero.setProperty("pageTone", "config")
    layout.addWidget(hero)

    window.config_status_banner = QLabel("配置状态：待确认 | 风险档位与模板待复核 | 下一步：保存后刷新机会池。")
    window.config_status_banner.setObjectName("statusBanner")
    window.config_status_banner.setProperty("pageTone", "config")
    window.config_status_banner.setWordWrap(True)
    layout.addWidget(window.config_status_banner)

    layout.addWidget(
        _build_workspace_focus_strip(
            window,
            workspace_key="config",
            attr_prefix="config_desk",
            eyebrow="策略配置 / 配置判断",
            title="配置判断条",
            subtitle="先确认风险档位、模板、消息源与 AI 边界，再决定是否刷新机会池与交易。",
            badges=[
                ("看什么", "风险 / 模板 / 消息源"),
                ("本页动作", "调参数 / 保存"),
                ("下一步", "刷新机会池 / 交易"),
            ],
        )
    )

    window.config_stage_tabs = QTabWidget()
    window.config_stage_tabs.setObjectName("compactInfoTabs")

    config_overview_page = QWidget()
    config_overview_layout = QVBoxLayout(config_overview_page)
    config_overview_layout.setContentsMargins(0, 0, 0, 0)
    config_overview_layout.setSpacing(12)
    window.config_stage_tabs.addTab(config_overview_page, "参数与风险")

    config_strategy_page = QWidget()
    config_strategy_layout = QVBoxLayout(config_strategy_page)
    config_strategy_layout.setContentsMargins(0, 0, 0, 0)
    config_strategy_layout.setSpacing(12)
    window.config_stage_tabs.addTab(config_strategy_page, "战法配置")

    config_intel_page = QWidget()
    config_intel_layout = QVBoxLayout(config_intel_page)
    config_intel_layout.setContentsMargins(0, 0, 0, 0)
    config_intel_layout.setSpacing(12)
    window.config_stage_tabs.addTab(config_intel_page, "消息与AI")

    config_notes_page = QWidget()
    config_notes_layout = QVBoxLayout(config_notes_page)
    config_notes_layout.setContentsMargins(0, 0, 0, 0)
    config_notes_layout.setSpacing(12)
    window.config_stage_tabs.addTab(config_notes_page, "说明")
    _configure_terminal_stage_tabs(
        window.config_stage_tabs,
        page_tone="config",
        tooltips=[
            "看参数、授权和风险档位。",
            "看战法列表、表单和配置脚本。",
            "看消息源与 AI 评测能力。",
            "看说明和影响范围。",
        ],
    )
    layout.addWidget(
        _build_workspace_stage_summary(
            window,
            workspace_key="config",
            attr_prefix="config",
            tab_widget=window.config_stage_tabs,
        )
    )
    layout.addWidget(window.config_stage_tabs, stretch=1)

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
    config_overview_layout.addWidget(top, stretch=2)

    snapshot_box = QGroupBox("\u98ce\u9669\u6863\u4f4d\u5feb\u7167")
    snapshot_box.setObjectName("configRiskSnapshotBox")
    window.config_risk_snapshot_box = snapshot_box
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
    config_overview_layout.addWidget(snapshot_box, stretch=1)

    capability_box = QGroupBox("配置能力总览")
    capability_box.setObjectName("configCapabilityBox")
    window.config_capability_box = capability_box
    window._style_terminal_panel(capability_box)
    capability_box.setProperty("pageTone", "config")
    capability_box.setProperty("surfaceRole", "metric-band")
    capability_box.setProperty("sectionRole", "capability")
    capability_layout = QVBoxLayout(capability_box)
    capability_layout.setContentsMargins(12, 12, 12, 12)
    capability_layout.setSpacing(10)
    capability_intro = QLabel("拆页后保留的旧能力统一从这里回补：参数与风险、战法配置、消息源管理、AI 评测都必须能直接抵达。")
    capability_intro.setObjectName("inlineHint")
    capability_intro.setWordWrap(True)
    capability_layout.addWidget(capability_intro)
    capability_grid = QGridLayout()
    capability_grid.setHorizontalSpacing(12)
    capability_grid.setVerticalSpacing(12)
    window.config_capability_cards = {}
    capability_specs = [
        ("risk", "参数与风险", "先确认风险档位、模板与题材边界。", "看参数"),
        ("strategy", "战法配置", "看战法目录、表单与 JSON 编辑器。", "看战法"),
        ("news", "消息源管理", "检查 Provider、载入记录与联动状态。", "看消息源"),
        ("ai", "AI 评测", "检查模型、自动触发与缓存状态。", "AI评测"),
    ]
    for index, (capability_key, title_text, detail_text, button_text) in enumerate(capability_specs):
        card = QFrame()
        card.setObjectName("configCapabilityCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "config")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "accent" if capability_key in {"strategy", "news"} else "tonal")
        if hasattr(window, "_open_config_capability_v1"):
            button.clicked.connect(lambda checked=False, current=capability_key: window._open_config_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        capability_grid.addWidget(card, index // 2, index % 2)
        window.config_capability_cards[capability_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    capability_layout.addLayout(capability_grid)
    config_overview_layout.addWidget(capability_box, stretch=1)

    strategy_summary_box = QGroupBox("战法速览")
    strategy_summary_box.setObjectName("configStrategySummaryBox")
    window.config_strategy_summary_box = strategy_summary_box
    window._style_terminal_panel(strategy_summary_box)
    strategy_summary_box.setProperty("pageTone", "config")
    strategy_summary_box.setProperty("surfaceRole", "metric-band")
    strategy_summary_box.setProperty("sectionRole", "summary")
    strategy_summary_layout = QVBoxLayout(strategy_summary_box)
    strategy_summary_layout.setContentsMargins(12, 12, 12, 12)
    strategy_summary_layout.setSpacing(10)
    strategy_summary_intro = QLabel("先看当前目录、草稿状态和 JSON 编辑进度，再决定是改表单、改脚本还是直接保存。")
    strategy_summary_intro.setObjectName("inlineHint")
    strategy_summary_intro.setWordWrap(True)
    strategy_summary_layout.addWidget(strategy_summary_intro)
    strategy_summary_grid = QGridLayout()
    strategy_summary_grid.setHorizontalSpacing(12)
    strategy_summary_grid.setVerticalSpacing(12)
    window.config_strategy_summary_cards = {}
    strategy_summary_specs = [
        ("catalog", "目录速览", "先看目录总量、启用数量和当前筛选。", "看列表"),
        ("form", "草稿速览", "先看当前草稿、阶段和校验状态。", "看表单"),
        ("editor", "JSON速览", "先看脚本行数、公式项和同步状态。", "看JSON"),
        ("script", "脚本能力", "先看能力声明、依赖和脚本诊断。", "看脚本"),
    ]
    for column, (summary_key, title_text, detail_text, button_text) in enumerate(strategy_summary_specs):
        card = QFrame()
        card.setObjectName("configStrategySummaryCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "config")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "tonal")
        if hasattr(window, "_open_config_strategy_summary_v1"):
            button.clicked.connect(lambda checked=False, current=summary_key: window._open_config_strategy_summary_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        strategy_summary_grid.addWidget(card, 0, column)
        window.config_strategy_summary_cards[summary_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    strategy_summary_layout.addLayout(strategy_summary_grid)
    config_strategy_layout.addWidget(strategy_summary_box, stretch=0)

    strategy_center_box = QGroupBox("战法配置中心")
    strategy_center_box.setObjectName("configStrategyCatalogBox")
    window._style_terminal_panel(strategy_center_box)
    strategy_center_layout = QVBoxLayout(strategy_center_box)
    strategy_center_layout.setContentsMargins(12, 12, 12, 12)
    strategy_center_layout.setSpacing(10)

    strategy_action_row = QHBoxLayout()
    strategy_action_row.setContentsMargins(0, 0, 0, 0)
    strategy_action_row.setSpacing(8)
    window.strategy_config_name_input = QLineEdit()
    window.strategy_config_name_input.setPlaceholderText("新战法名称，例如：量价共振")
    window.strategy_config_add_button = QPushButton("新增战法")
    window.strategy_config_script_button = QPushButton("脚本模板")
    window.strategy_config_script_from_current_button = QPushButton("转脚本")
    window.strategy_config_template_button = QPushButton("空白模板")
    window.strategy_config_duplicate_button = QPushButton("复制当前")
    window.strategy_config_save_button = QPushButton("保存战法")
    window.strategy_config_validate_button = QPushButton("校验配置")
    window.strategy_config_delete_button = QPushButton("删除战法")
    window.strategy_config_export_button = QPushButton("导出当前")
    window.strategy_config_export_all_button = QPushButton("导出全部")
    window.strategy_config_import_button = QPushButton("导入配置")
    window.strategy_config_open_source_button = QPushButton("看源文件")
    window.strategy_config_open_dir_button = QPushButton("看目录")
    window.strategy_config_reload_button = QPushButton("重载")
    window._set_button_role(window.strategy_config_add_button, "tonal")
    window._set_button_role(window.strategy_config_script_button, "tonal")
    window._set_button_role(window.strategy_config_script_from_current_button, "tonal")
    window._set_button_role(window.strategy_config_template_button, "ghost")
    window._set_button_role(window.strategy_config_duplicate_button, "ghost")
    window._set_button_role(window.strategy_config_save_button, "accent")
    window._set_button_role(window.strategy_config_validate_button, "tonal")
    window._set_button_role(window.strategy_config_delete_button, "ghost")
    window._set_button_role(window.strategy_config_export_button, "ghost")
    window._set_button_role(window.strategy_config_export_all_button, "ghost")
    window._set_button_role(window.strategy_config_import_button, "tonal")
    window._set_button_role(window.strategy_config_open_source_button, "ghost")
    window._set_button_role(window.strategy_config_open_dir_button, "ghost")
    window._set_button_role(window.strategy_config_reload_button, "ghost")
    window.strategy_config_add_button.clicked.connect(window.new_strategy_config_wizard)
    window.strategy_config_script_button.clicked.connect(window.new_strategy_script_template)
    window.strategy_config_script_from_current_button.clicked.connect(window.generate_script_from_current_strategy_config)
    window.strategy_config_template_button.clicked.connect(window.new_strategy_config_template)
    window.strategy_config_duplicate_button.clicked.connect(window.duplicate_current_strategy_config)
    window.strategy_config_save_button.clicked.connect(window.save_strategy_config_from_editor)
    window.strategy_config_validate_button.clicked.connect(window.validate_strategy_config_editor)
    window.strategy_config_delete_button.clicked.connect(window.delete_selected_strategy_config)
    window.strategy_config_export_button.clicked.connect(window.export_current_strategy_config)
    window.strategy_config_export_all_button.clicked.connect(window.export_all_strategy_configs)
    window.strategy_config_import_button.clicked.connect(window.import_strategy_config_file)
    window.strategy_config_open_source_button.clicked.connect(window.open_selected_strategy_source)
    window.strategy_config_open_dir_button.clicked.connect(window.open_strategy_config_directory)
    window.strategy_config_reload_button.clicked.connect(window.reload_strategy_config_workspace)
    strategy_action_row.addWidget(QLabel("战法名称"))
    strategy_action_row.addWidget(window.strategy_config_name_input, stretch=2)
    strategy_action_row.addWidget(window.strategy_config_add_button)
    strategy_action_row.addWidget(window.strategy_config_script_button)
    strategy_action_row.addWidget(window.strategy_config_script_from_current_button)
    strategy_action_row.addWidget(window.strategy_config_template_button)
    strategy_action_row.addWidget(window.strategy_config_duplicate_button)
    strategy_action_row.addWidget(window.strategy_config_save_button)
    strategy_action_row.addWidget(window.strategy_config_validate_button)
    strategy_action_row.addWidget(window.strategy_config_delete_button)
    strategy_action_row.addWidget(window.strategy_config_export_button)
    strategy_action_row.addWidget(window.strategy_config_export_all_button)
    strategy_action_row.addWidget(window.strategy_config_import_button)
    strategy_action_row.addWidget(window.strategy_config_open_source_button)
    strategy_action_row.addWidget(window.strategy_config_open_dir_button)
    strategy_action_row.addWidget(window.strategy_config_reload_button)
    strategy_center_layout.addLayout(strategy_action_row)

    strategy_splitter = QSplitter(Qt.Horizontal)
    strategy_splitter.setChildrenCollapsible(False)
    window.strategy_config_splitter = strategy_splitter

    strategy_list_box = QGroupBox("战法列表")
    strategy_list_box.setObjectName("configStrategyListBox")
    window._style_terminal_panel(strategy_list_box)
    strategy_list_layout = QVBoxLayout(strategy_list_box)
    strategy_list_layout.setContentsMargins(10, 10, 10, 10)
    strategy_list_layout.setSpacing(8)
    strategy_list_header = QHBoxLayout()
    strategy_list_header.setContentsMargins(0, 0, 0, 0)
    strategy_list_header.setSpacing(8)
    window.strategy_config_search_input = QLineEdit()
    window.strategy_config_search_input.setPlaceholderText("搜索战法名称，如：龙头、低吸、趋势")
    window.strategy_config_search_input.textChanged.connect(window._on_strategy_config_search_changed)
    strategy_list_header.addWidget(window.strategy_config_search_input, stretch=1)
    window.strategy_config_source_filter_combo = QComboBox()
    window.strategy_config_source_filter_combo.addItem("全部来源", "all")
    window.strategy_config_source_filter_combo.addItem("仅 JSON", "catalog")
    window.strategy_config_source_filter_combo.addItem("仅脚本", "script")
    window.strategy_config_source_filter_combo.currentIndexChanged.connect(window._on_strategy_config_source_filter_changed)
    strategy_list_header.addWidget(window.strategy_config_source_filter_combo)
    strategy_list_layout.addLayout(strategy_list_header)
    window.strategy_config_list_status_label = QLabel("等待载入战法列表")
    window.strategy_config_list_status_label.setObjectName("inlineHint")
    window.strategy_config_list_status_label.setWordWrap(True)
    strategy_list_layout.addWidget(window.strategy_config_list_status_label)
    window.strategy_config_list = QListWidget()
    window.strategy_config_list.currentTextChanged.connect(window._on_strategy_config_selected)
    strategy_list_layout.addWidget(window.strategy_config_list)
    window.strategy_plugin_diagnostics_label = QLabel("脚本诊断：等待重载")
    window.strategy_plugin_diagnostics_label.setObjectName("inlineHint")
    window.strategy_plugin_diagnostics_label.setWordWrap(True)
    strategy_diag_header = QHBoxLayout()
    strategy_diag_header.setContentsMargins(0, 0, 0, 0)
    strategy_diag_header.setSpacing(8)
    strategy_diag_header.addWidget(window.strategy_plugin_diagnostics_label, stretch=1)
    window.strategy_plugin_diagnostics_filter_combo = QComboBox()
    window.strategy_plugin_diagnostics_filter_combo.addItem("全部级别", "all")
    window.strategy_plugin_diagnostics_filter_combo.addItem("仅错误", "error")
    window.strategy_plugin_diagnostics_filter_combo.addItem("仅警告", "warning")
    window.strategy_plugin_diagnostics_filter_combo.addItem("仅信息", "info")
    window.strategy_plugin_diagnostics_filter_combo.currentIndexChanged.connect(window._on_strategy_plugin_diagnostic_filter_changed)
    strategy_diag_header.addWidget(window.strategy_plugin_diagnostics_filter_combo)
    window.strategy_plugin_diagnostics_open_button = QPushButton("看报错源")
    window.strategy_plugin_diagnostics_copy_button = QPushButton("复制诊断")
    window._set_button_role(window.strategy_plugin_diagnostics_open_button, "ghost")
    window._set_button_role(window.strategy_plugin_diagnostics_copy_button, "ghost")
    window.strategy_plugin_diagnostics_open_button.clicked.connect(window.open_strategy_plugin_diagnostic_source)
    window.strategy_plugin_diagnostics_copy_button.clicked.connect(window.copy_strategy_plugin_diagnostic_detail)
    strategy_diag_header.addWidget(window.strategy_plugin_diagnostics_copy_button)
    strategy_diag_header.addWidget(window.strategy_plugin_diagnostics_open_button)
    strategy_list_layout.addLayout(strategy_diag_header)
    window.strategy_plugin_diagnostics_list = QListWidget()
    window.strategy_plugin_diagnostics_list.currentRowChanged.connect(window._on_strategy_plugin_diagnostic_selected)
    window.strategy_plugin_diagnostics_list.itemDoubleClicked.connect(lambda *_args: window.open_strategy_plugin_diagnostic_source())
    strategy_list_layout.addWidget(window.strategy_plugin_diagnostics_list)
    window.strategy_plugin_diagnostics_text = QTextEdit()
    window.strategy_plugin_diagnostics_text.setReadOnly(True)
    window._style_terminal_console(window.strategy_plugin_diagnostics_text)
    window.strategy_plugin_diagnostics_text.setMaximumHeight(132)
    strategy_list_layout.addWidget(window.strategy_plugin_diagnostics_text)
    strategy_splitter.addWidget(strategy_list_box)

    strategy_editor_box = QGroupBox("配置脚本")
    strategy_editor_box.setObjectName("configStrategyEditorBox")
    window._style_terminal_panel(strategy_editor_box)
    strategy_editor_layout = QVBoxLayout(strategy_editor_box)
    strategy_editor_layout.setContentsMargins(10, 10, 10, 10)
    strategy_editor_layout.setSpacing(8)
    strategy_form_box = QGroupBox("表单编辑")
    strategy_form_box.setObjectName("configStrategyFormBox")
    window._style_terminal_panel(strategy_form_box)
    strategy_form_layout = QFormLayout(strategy_form_box)
    strategy_form_layout.setLabelAlignment(Qt.AlignRight)
    strategy_form_layout.setContentsMargins(10, 10, 10, 10)
    strategy_form_layout.setSpacing(8)
    window.strategy_config_score_field_input = QLineEdit()
    window.strategy_config_description_input = QLineEdit()
    window.strategy_config_aliases_input = QLineEdit()
    window.strategy_config_formula_stage_combo = QComboBox()
    for key, label in [("base", "基础战法"), ("aggregate", "聚合战法")]:
        window.strategy_config_formula_stage_combo.addItem(label, key)
    window.strategy_config_enabled_checkbox = QCheckBox("启用此战法")
    window.strategy_config_short_label_input = QLineEdit()
    window.strategy_config_capital_style_input = QLineEdit()
    window.strategy_config_badge_palette_input = QLineEdit()
    window.strategy_config_default_risk_input = QLineEdit()
    window.strategy_config_low_flag_risk_input = QLineEdit()
    window.strategy_config_stop_pct_input = QLineEdit()
    window.strategy_config_target_pct_input = QLineEdit()
    window.strategy_config_budget_strong_input = QLineEdit()
    window.strategy_config_budget_normal_input = QLineEdit()
    window.strategy_config_budget_threshold_input = QLineEdit()
    window.strategy_config_formula_weights_text = QTextEdit()
    window._style_terminal_console(window.strategy_config_formula_weights_text)
    window.strategy_config_formula_weights_text.setMaximumHeight(92)
    window.strategy_config_script_allow_dependency_scores_checkbox = QCheckBox("脚本允许读取依赖得分")
    window.strategy_config_script_notes_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_script_notes_input)
    window.strategy_config_script_notes_input.setMaximumHeight(72)
    window.strategy_config_script_required_context_list = QListWidget()
    window.strategy_config_script_required_context_list.setMaximumHeight(132)
    for item in list_strategy_context_inputs():
        option = QListWidgetItem(f"{item['key']} | {item['label']}")
        option.setData(Qt.UserRole, str(item["key"]))
        option.setToolTip(str(item["description"]))
        option.setFlags(option.flags() | Qt.ItemIsUserCheckable)
        option.setCheckState(Qt.Unchecked)
        window.strategy_config_script_required_context_list.addItem(option)
    context_widget = QWidget()
    context_layout = QVBoxLayout(context_widget)
    context_layout.setContentsMargins(0, 0, 0, 0)
    context_layout.setSpacing(6)
    context_layout.addWidget(window.strategy_config_script_required_context_list)
    window.strategy_config_script_required_context_hint_label = QLabel("脚本上下文：可勾选当前脚本允许读取的基础因子。")
    window.strategy_config_script_required_context_hint_label.setObjectName("inlineHint")
    window.strategy_config_script_required_context_hint_label.setWordWrap(True)
    context_layout.addWidget(window.strategy_config_script_required_context_hint_label)
    window.strategy_config_script_dependency_list = QListWidget()
    window.strategy_config_script_dependency_list.setMaximumHeight(132)
    dependency_widget = QWidget()
    dependency_layout = QVBoxLayout(dependency_widget)
    dependency_layout.setContentsMargins(0, 0, 0, 0)
    dependency_layout.setSpacing(6)
    dependency_layout.addWidget(window.strategy_config_script_dependency_list)
    window.strategy_config_script_dependency_hint_label = QLabel("脚本依赖：勾选当前脚本会读取的其他战法得分。")
    window.strategy_config_script_dependency_hint_label.setObjectName("inlineHint")
    window.strategy_config_script_dependency_hint_label.setWordWrap(True)
    dependency_layout.addWidget(window.strategy_config_script_dependency_hint_label)
    window.strategy_config_scene_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_scene_input)
    window.strategy_config_scene_input.setMaximumHeight(72)
    window.strategy_config_positioning_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_positioning_input)
    window.strategy_config_positioning_input.setMaximumHeight(72)
    window.strategy_config_empty_hint_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_empty_hint_input)
    window.strategy_config_empty_hint_input.setMaximumHeight(72)
    window.strategy_config_position_hint_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_position_hint_input)
    window.strategy_config_position_hint_input.setMaximumHeight(72)
    window.strategy_config_no_go_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_no_go_input)
    window.strategy_config_no_go_input.setMaximumHeight(72)
    window.strategy_config_applicable_market_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_applicable_market_input)
    window.strategy_config_applicable_market_input.setMaximumHeight(72)
    window.strategy_config_capacity_limit_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_capacity_limit_input)
    window.strategy_config_capacity_limit_input.setMaximumHeight(72)
    window.strategy_config_standard_action_buy_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_standard_action_buy_input)
    window.strategy_config_standard_action_buy_input.setMaximumHeight(72)
    window.strategy_config_standard_action_sell_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_standard_action_sell_input)
    window.strategy_config_standard_action_sell_input.setMaximumHeight(72)
    window.strategy_config_failure_sample_input = QTextEdit()
    window._style_terminal_console(window.strategy_config_failure_sample_input)
    window.strategy_config_failure_sample_input.setMaximumHeight(72)
    strategy_form_layout.addRow("评分字段", window.strategy_config_score_field_input)
    strategy_form_layout.addRow("战法简介", window.strategy_config_description_input)
    strategy_form_layout.addRow("别名", window.strategy_config_aliases_input)
    strategy_form_layout.addRow("战法阶段", window.strategy_config_formula_stage_combo)
    strategy_form_layout.addRow("", window.strategy_config_enabled_checkbox)
    strategy_form_layout.addRow("简称", window.strategy_config_short_label_input)
    strategy_form_layout.addRow("资金风格", window.strategy_config_capital_style_input)
    strategy_form_layout.addRow("配色", window.strategy_config_badge_palette_input)
    strategy_form_layout.addRow("默认风险", window.strategy_config_default_risk_input)
    strategy_form_layout.addRow("低风险灯等级", window.strategy_config_low_flag_risk_input)
    strategy_form_layout.addRow("止损比例", window.strategy_config_stop_pct_input)
    strategy_form_layout.addRow("止盈比例", window.strategy_config_target_pct_input)
    strategy_form_layout.addRow("强势预算", window.strategy_config_budget_strong_input)
    strategy_form_layout.addRow("常规预算", window.strategy_config_budget_normal_input)
    strategy_form_layout.addRow("强势阈值", window.strategy_config_budget_threshold_input)
    strategy_form_layout.addRow("公式权重(JSON)", window.strategy_config_formula_weights_text)
    strategy_form_layout.addRow("脚本上下文", context_widget)
    strategy_form_layout.addRow("脚本依赖", dependency_widget)
    strategy_form_layout.addRow("", window.strategy_config_script_allow_dependency_scores_checkbox)
    strategy_form_layout.addRow("脚本备注", window.strategy_config_script_notes_input)
    strategy_form_layout.addRow("适用场景", window.strategy_config_scene_input)
    strategy_form_layout.addRow("产品定位", window.strategy_config_positioning_input)
    strategy_form_layout.addRow("空态提示", window.strategy_config_empty_hint_input)
    strategy_form_layout.addRow("仓位建议", window.strategy_config_position_hint_input)
    strategy_form_layout.addRow("禁做情形", window.strategy_config_no_go_input)
    strategy_form_layout.addRow("适用行情", window.strategy_config_applicable_market_input)
    strategy_form_layout.addRow("容量上限", window.strategy_config_capacity_limit_input)
    strategy_form_layout.addRow("标准动作-买", window.strategy_config_standard_action_buy_input)
    strategy_form_layout.addRow("标准动作-卖", window.strategy_config_standard_action_sell_input)
    strategy_form_layout.addRow("失败样本", window.strategy_config_failure_sample_input)
    strategy_form_button_row = QHBoxLayout()
    strategy_form_button_row.setContentsMargins(0, 0, 0, 0)
    strategy_form_button_row.setSpacing(8)
    window.strategy_config_form_to_editor_button = QPushButton("表单生成JSON")
    window.strategy_config_editor_to_form_button = QPushButton("JSON回填表单")
    window.strategy_config_formula_example_button = QPushButton("填充公式示例")
    window.strategy_config_script_capability_derive_button = QPushButton("推导脚本能力")
    window._set_button_role(window.strategy_config_form_to_editor_button, "tonal")
    window._set_button_role(window.strategy_config_editor_to_form_button, "ghost")
    window._set_button_role(window.strategy_config_formula_example_button, "ghost")
    window._set_button_role(window.strategy_config_script_capability_derive_button, "ghost")
    window.strategy_config_form_to_editor_button.clicked.connect(window.sync_strategy_config_form_to_editor)
    window.strategy_config_editor_to_form_button.clicked.connect(window.sync_strategy_config_editor_to_form)
    window.strategy_config_formula_example_button.clicked.connect(window.fill_strategy_config_formula_example)
    window.strategy_config_script_capability_derive_button.clicked.connect(window.derive_strategy_script_capabilities_from_formula)
    window.strategy_config_script_capability_derive_button.setToolTip("按当前公式权重自动推导脚本上下文和依赖战法。")
    strategy_form_button_row.addWidget(window.strategy_config_form_to_editor_button)
    strategy_form_button_row.addWidget(window.strategy_config_editor_to_form_button)
    strategy_form_button_row.addWidget(window.strategy_config_formula_example_button)
    strategy_form_button_row.addWidget(window.strategy_config_script_capability_derive_button)
    strategy_form_button_row.addStretch(1)
    form_text_widgets = [
        getattr(window, "strategy_config_name_input", None),
        getattr(window, "strategy_config_score_field_input", None),
        getattr(window, "strategy_config_description_input", None),
        getattr(window, "strategy_config_aliases_input", None),
        getattr(window, "strategy_config_short_label_input", None),
        getattr(window, "strategy_config_capital_style_input", None),
        getattr(window, "strategy_config_badge_palette_input", None),
        getattr(window, "strategy_config_default_risk_input", None),
        getattr(window, "strategy_config_low_flag_risk_input", None),
        getattr(window, "strategy_config_stop_pct_input", None),
        getattr(window, "strategy_config_target_pct_input", None),
        getattr(window, "strategy_config_budget_strong_input", None),
        getattr(window, "strategy_config_budget_normal_input", None),
        getattr(window, "strategy_config_budget_threshold_input", None),
    ]
    for widget in form_text_widgets:
        if widget is not None and hasattr(widget, "textChanged"):
            widget.textChanged.connect(window._on_strategy_config_form_changed)
    for widget in [
        getattr(window, "strategy_config_formula_weights_text", None),
        getattr(window, "strategy_config_script_notes_input", None),
        getattr(window, "strategy_config_scene_input", None),
        getattr(window, "strategy_config_positioning_input", None),
        getattr(window, "strategy_config_empty_hint_input", None),
        getattr(window, "strategy_config_position_hint_input", None),
        getattr(window, "strategy_config_no_go_input", None),
        getattr(window, "strategy_config_applicable_market_input", None),
        getattr(window, "strategy_config_capacity_limit_input", None),
        getattr(window, "strategy_config_standard_action_buy_input", None),
        getattr(window, "strategy_config_standard_action_sell_input", None),
        getattr(window, "strategy_config_failure_sample_input", None),
    ]:
        if widget is not None and hasattr(widget, "textChanged"):
            widget.textChanged.connect(window._on_strategy_config_form_changed)
    if hasattr(window, "strategy_config_formula_stage_combo") and hasattr(window.strategy_config_formula_stage_combo, "currentIndexChanged"):
        window.strategy_config_formula_stage_combo.currentIndexChanged.connect(lambda _index: window._on_strategy_config_form_changed())
    if hasattr(window, "strategy_config_enabled_checkbox") and hasattr(window.strategy_config_enabled_checkbox, "stateChanged"):
        window.strategy_config_enabled_checkbox.stateChanged.connect(lambda _state: window._on_strategy_config_form_changed())
    if hasattr(window, "strategy_config_script_allow_dependency_scores_checkbox") and hasattr(window.strategy_config_script_allow_dependency_scores_checkbox, "stateChanged"):
        window.strategy_config_script_allow_dependency_scores_checkbox.stateChanged.connect(lambda _state: window._on_strategy_config_form_changed())
    if hasattr(window, "strategy_config_script_required_context_list") and hasattr(window.strategy_config_script_required_context_list, "itemChanged"):
        window.strategy_config_script_required_context_list.itemChanged.connect(lambda *_args: window._on_strategy_config_form_changed())
    if hasattr(window, "strategy_config_script_dependency_list") and hasattr(window.strategy_config_script_dependency_list, "itemChanged"):
        window.strategy_config_script_dependency_list.itemChanged.connect(lambda *_args: window._on_strategy_config_form_changed())
    strategy_editor_layout.addWidget(strategy_form_box)
    strategy_editor_layout.addLayout(strategy_form_button_row)
    window.strategy_config_formula_help_text = QTextEdit()
    window.strategy_config_formula_help_text.setReadOnly(True)
    window._style_terminal_console(window.strategy_config_formula_help_text)
    window.strategy_config_formula_help_text.setMaximumHeight(260)
    window.strategy_config_formula_help_text.setPlaceholderText("这里会显示可用公式因子、策略依赖和当前草稿校验结果。")
    strategy_editor_layout.addWidget(window.strategy_config_formula_help_text)
    window.strategy_config_editor = QTextEdit()
    window._style_terminal_console(window.strategy_config_editor)
    window.strategy_config_editor.setPlaceholderText("这里填写单个战法 JSON 配置，保存后立即生效。")
    window.strategy_config_status_text = QTextEdit()
    window.strategy_config_status_text.setReadOnly(True)
    window._style_terminal_console(window.strategy_config_status_text)
    window.strategy_config_status_text.setMaximumHeight(86)
    strategy_editor_layout.addWidget(window.strategy_config_editor, stretch=1)
    strategy_editor_layout.addWidget(window.strategy_config_status_text)
    strategy_splitter.addWidget(strategy_editor_box)
    window._configure_splitter(strategy_splitter, [280, 760])
    strategy_center_layout.addWidget(strategy_splitter)
    config_strategy_layout.addWidget(strategy_center_box, stretch=2)

    intel_summary_box = QGroupBox("消息与AI速览")
    intel_summary_box.setObjectName("configIntelSummaryBox")
    window.config_intel_summary_box = intel_summary_box
    window._style_terminal_panel(intel_summary_box)
    intel_summary_box.setProperty("pageTone", "config")
    intel_summary_box.setProperty("surfaceRole", "metric-band")
    intel_summary_box.setProperty("sectionRole", "summary")
    intel_summary_layout = QVBoxLayout(intel_summary_box)
    intel_summary_layout.setContentsMargins(12, 12, 12, 12)
    intel_summary_layout.setSpacing(10)
    intel_summary_intro = QLabel("先看消息源与 AI 评测当前状态，再决定载入来源、保存配置还是回机会池继续复核。")
    intel_summary_intro.setObjectName("inlineHint")
    intel_summary_intro.setWordWrap(True)
    intel_summary_layout.addWidget(intel_summary_intro)
    intel_summary_grid = QGridLayout()
    intel_summary_grid.setHorizontalSpacing(12)
    intel_summary_grid.setVerticalSpacing(12)
    window.config_intel_summary_cards = {}
    intel_summary_specs = [
        ("news", "消息源速览", "先看 Provider、载入状态和联动覆盖。", "看消息源"),
        ("ai", "AI评测速览", "先看模型、自动触发和最近评测状态。", "看AI"),
    ]
    for column, (summary_key, title_text, detail_text, button_text) in enumerate(intel_summary_specs):
        card = QFrame()
        card.setObjectName("configIntelSummaryCard")
        card.setProperty("actionRow", True)
        card.setProperty("pageTone", "config")
        card.setProperty("capabilityCard", True)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(6)
        title = QLabel(title_text)
        title.setObjectName("workspaceTitle")
        headline = QLabel("--")
        headline.setObjectName("workspaceSummaryHeadline")
        headline.setWordWrap(True)
        detail = QLabel(detail_text)
        detail.setObjectName("inlineHint")
        detail.setWordWrap(True)
        meta = QLabel("--")
        meta.setObjectName("inlineHint")
        meta.setWordWrap(True)
        button = QPushButton(button_text)
        window._set_button_role(button, "tonal")
        if hasattr(window, "_open_config_capability_v1"):
            button.clicked.connect(lambda checked=False, current=summary_key: window._open_config_capability_v1(current))
        card_layout.addWidget(title)
        card_layout.addWidget(headline)
        card_layout.addWidget(detail)
        card_layout.addWidget(meta)
        card_layout.addWidget(button)
        card_layout.addStretch(1)
        intel_summary_grid.addWidget(card, 0, column)
        window.config_intel_summary_cards[summary_key] = {
            "card": card,
            "title": title,
            "headline": headline,
            "detail": detail,
            "meta": meta,
            "button": button,
        }
    intel_summary_layout.addLayout(intel_summary_grid)
    config_intel_layout.addWidget(intel_summary_box, stretch=0)

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
    news_recommend_button = QPushButton("看机会")
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
    config_intel_layout.addWidget(news_box, stretch=1)

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
    window.ai_review_auto_on_pool_checkbox = QCheckBox("机会池刷新后自动触发")
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
    ai_recommend_button = QPushButton("看机会")
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
    config_intel_layout.addWidget(ai_box, stretch=1)

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
    config_notes_layout.addWidget(notes_box, stretch=1)

    window._refresh_license_status_view()
    if hasattr(window, "_refresh_news_source_status_panel"):
        window._refresh_news_source_status_panel()
    if hasattr(window, "_refresh_ai_review_status_panel"):
        window._refresh_ai_review_status_panel()
    if hasattr(window, "_refresh_config_intel_summary_v1"):
        window._refresh_config_intel_summary_v1()







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
        if hasattr(window, "_refresh_config_capability_overview_v1"):
            window._refresh_config_capability_overview_v1()
        return

    _refresh_config_risk_snapshot_fallback(window)
    if hasattr(window, "_refresh_config_capability_overview_v1"):
        window._refresh_config_capability_overview_v1()
