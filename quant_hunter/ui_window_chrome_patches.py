from __future__ import annotations

from PySide6.QtCharts import QChartView
from PySide6.QtWidgets import QLabel, QTableWidget, QTextEdit, QWidget


def apply_commercial_chrome_patches(window_cls: type, *, set_shell_chip_fn) -> None:
    if getattr(window_cls, "_qh_commercial_chrome_patches_applied_v34", False):
        return

    original_refresh_shell_header = window_cls._refresh_shell_header
    original_post_build_ui_tweaks = window_cls._post_build_ui_tweaks

    def _apply_commercial_brand_polish_v34(self) -> None:
        if getattr(self, "_qh_brand_polish_applied_v34", False):
            return
        self.setStyleSheet(
            self.styleSheet()
            + """
QFrame#shellHeader {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #18212c, stop:0.55 #101820, stop:1 #0b1117);
    border: 1px solid rgba(119, 146, 175, 0.26);
    border-radius: 20px;
}
QFrame#shellHeader QLabel,
QFrame#shellPulseBar QLabel,
QFrame#shellWorkflowBar QLabel,
QFrame#workspaceHero QLabel,
QFrame#workspaceBadge QLabel,
QFrame#shellChip QLabel,
QLabel#statusBanner,
QLabel#focusStateLabel,
QLabel#workspaceFocusBanner,
QLabel#inlineHint,
QLabel#sectionTitle {
    background-color: transparent;
}
QFrame#shellBrandBlock,
QWidget#shellChipRail,
QWidget#workspaceStage,
QWidget#workspaceStage > QWidget,
QWidget#workspaceStage > QWidget > QWidget {
    background-color: transparent;
}
QFrame#shellHeader[stateTone="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.34);
}
QFrame#shellHeader[stateTone="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.34);
}
QFrame#shellHeader[stateTone="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.34);
}
QFrame#shellChip {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(14, 20, 28, 0.98), stop:1 rgba(10, 15, 22, 0.98));
    border: 1px solid rgba(120, 142, 165, 0.22);
    border-radius: 14px;
}
QFrame#shellPulseBar {
    border-radius: 14px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 27, 38, 0.98), stop:1 rgba(11, 17, 24, 0.98));
    border: 1px solid rgba(120, 142, 165, 0.20);
}
QFrame#shellWorkflowBar {
    border-radius: 14px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 24, 34, 0.98), stop:1 rgba(10, 15, 21, 0.98));
    border: 1px solid rgba(120, 142, 165, 0.16);
}
QFrame#shellPulseBar[stateTone="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.28);
}
QFrame#shellWorkflowBar[stateTone="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.22);
}
QFrame#shellPulseBar[stateTone="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.28);
}
QFrame#shellWorkflowBar[stateTone="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.22);
}
QFrame#shellPulseBar[stateTone="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.28);
}
QFrame#shellWorkflowBar[stateTone="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.22);
}
QLabel#topBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0aa4d, stop:1 #ffd166);
    color: #111720;
    border-radius: 10px;
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 900;
}
QTabWidget::pane {
    border: 1px solid rgba(109, 131, 153, 0.16);
    border-radius: 18px;
    background: rgba(10, 15, 21, 0.72);
    top: -2px;
}
QTabBar::tab {
    min-width: 96px;
    padding: 9px 14px;
    margin-right: 6px;
    border-radius: 12px;
    background: rgba(19, 28, 39, 0.90);
    border: 1px solid rgba(109, 131, 153, 0.14);
    color: #91a4b8;
    font-weight: 800;
}
QTabBar::tab:hover:!selected {
    color: #e9f1fb;
    background: rgba(27, 40, 56, 0.95);
    border: 1px solid rgba(127, 183, 255, 0.22);
}
QTabBar::tab:selected {
    color: #f9fcff;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(38, 84, 130, 0.98), stop:1 rgba(24, 39, 56, 0.98));
    border: 1px solid rgba(122, 184, 255, 0.26);
}
QComboBox {
    min-height: 34px;
}
QPushButton#ghostButton,
QPushButton#accentButton,
QPushButton#tonalButton {
    transition: none;
}
QPushButton#ghostButton:disabled,
QPushButton#accentButton:disabled,
QPushButton#tonalButton:disabled {
    color: rgba(201, 214, 228, 0.42);
    border-color: rgba(109, 131, 153, 0.10);
    background: rgba(18, 25, 34, 0.52);
}
QFrame[actionRow="true"] {
    background: rgba(12, 18, 25, 0.68);
    border: 1px solid rgba(113, 133, 156, 0.12);
    border-radius: 16px;
}
QToolTip {
    background: rgba(12, 18, 24, 0.96);
    color: #eef4fb;
    border: 1px solid rgba(126, 183, 255, 0.22);
    padding: 8px 10px;
    border-radius: 10px;
}
QWidget#overviewRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121821, stop:0.48 #0e141b, stop:1 #101722);
    color: #eef5fd;
}
QWidget#overviewRoot QLabel {
    background-color: transparent;
    color: #eef5fd;
}
QWidget#overviewRoot QGroupBox {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(19, 27, 36, 0.98), stop:1 rgba(13, 19, 27, 0.98));
    color: #eef5fd;
    border: 1px solid rgba(123, 145, 170, 0.18);
    border-radius: 18px;
}
QWidget#overviewRoot QGroupBox::title {
    color: #eef5fd;
    font-weight: 800;
}
QWidget#overviewRoot QLabel#heroTitle {
    color: #fbfdff;
}
QWidget#overviewRoot QLabel#heroSubtitle,
QWidget#overviewRoot QLabel#inlineHint {
    color: #bfd0e0;
}
QWidget#overviewRoot QLabel#statusBanner,
QWidget#overviewRoot QLabel#focusStateLabel,
QWidget#overviewRoot QLabel#workspaceFocusBanner {
    color: #f7fbff;
}
QWidget#overviewRoot QTextEdit#marketNotePanel,
QWidget#overviewRoot QTextEdit#terminalConsole {
    background: rgba(12, 17, 24, 0.98);
    color: #eef5fd;
    border: 1px solid rgba(120, 142, 166, 0.18);
}
QWidget#overviewRoot QTableWidget#marketPoolTable,
QWidget#overviewRoot QTableWidget#terminalTable {
    background: rgba(11, 16, 22, 0.98);
    color: #eef5fd;
    border: 1px solid rgba(120, 142, 166, 0.18);
}
QWidget#overviewRoot QLineEdit,
QWidget#overviewRoot QComboBox {
    background: rgba(13, 19, 27, 0.98);
    color: #eef5fd;
    border: 1px solid rgba(126, 151, 179, 0.18);
    border-radius: 14px;
    padding: 8px 12px;
}
QWidget#overviewRoot QLineEdit:focus,
QWidget#overviewRoot QComboBox:focus {
    border-color: rgba(126, 183, 255, 0.30);
}
QWidget#overviewRoot QPushButton {
    color: #eef5fd;
}
QWidget#overviewRoot QCheckBox {
    color: #d9e6f2;
    spacing: 8px;
}
QLabel#shellWorkflowLabel {
    color: #90a4bb;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.04em;
}
QLabel#shellWorkflowNote {
    color: #c5d5e5;
    font-size: 11px;
    font-weight: 700;
}
QLabel#shellChipLabel {
    font-size: 10px;
}
QLabel#shellChipValue {
    font-size: 12px;
}
QLabel#shellPulseLabel {
    font-size: 12px;
}
QLabel#shellPulseHint,
QLabel#shellPulseMeta {
    font-size: 11px;
}
QWidget#brokerRoot {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #101822, stop:0.52 #0d141c, stop:1 #111a24);
    color: #eef4fb;
}
QWidget#brokerRoot QFrame#workspaceHero {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(20, 30, 42, 0.98), stop:1 rgba(10, 15, 22, 0.98));
    border: 1px solid rgba(120, 141, 165, 0.18);
    border-radius: 22px;
}
QWidget#brokerRoot QLabel#statusBanner,
QWidget#brokerRoot QLabel#focusStateLabel,
QWidget#brokerRoot QLabel#workspaceFocusBanner {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 27, 38, 0.96), stop:1 rgba(11, 17, 24, 0.96));
    border: 1px solid rgba(112, 132, 154, 0.18);
    border-radius: 16px;
    padding: 10px 14px;
    color: #f4f8fd;
    font-weight: 800;
}
QWidget#brokerRoot QGroupBox#workspaceToolPanel,
QWidget#brokerRoot QGroupBox#terminalPanel,
QWidget#brokerRoot QGroupBox[terminalPanel="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(20, 28, 38, 0.98), stop:1 rgba(11, 17, 24, 0.98));
    border: 1px solid rgba(110, 129, 150, 0.16);
    border-radius: 20px;
    margin-top: 18px;
    padding-top: 12px;
}
QWidget#brokerRoot QGroupBox#workspaceToolPanel[sectionRole="setup"] {
    border-color: rgba(120, 151, 183, 0.22);
}
QWidget#brokerRoot QGroupBox#workspaceToolPanel[sectionRole="command"] {
    border-color: rgba(103, 149, 214, 0.26);
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(22, 32, 46, 0.99), stop:1 rgba(12, 18, 27, 0.99));
}
QWidget#brokerRoot QGroupBox#workspaceToolPanel[sectionRole="runtime"],
QWidget#brokerRoot QGroupBox[sectionRole="diagnostic"] {
    border-color: rgba(135, 148, 166, 0.18);
}
QWidget#brokerRoot QGroupBox#workspaceToolPanel[sectionRole="execution"],
QWidget#brokerRoot QGroupBox[sectionRole="portfolio"] {
    border-color: rgba(112, 139, 172, 0.20);
}
QWidget#brokerRoot QGroupBox::title {
    color: #f4f8fd;
    font-size: 15px;
    font-weight: 800;
    subcontrol-origin: margin;
    left: 16px;
    padding: 0 6px 0 6px;
}
QWidget#brokerRoot QLabel#inlineHint {
    color: #8ea4bc;
    line-height: 1.45;
}
QWidget#brokerRoot QLabel#sectionTitle {
    color: #d6e2ee;
    font-size: 12px;
    font-weight: 800;
    letter-spacing: 0.04em;
}
QWidget#brokerRoot QLineEdit,
QWidget#brokerRoot QComboBox {
    background: rgba(12, 18, 26, 0.98);
    color: #edf3fa;
    border: 1px solid rgba(104, 123, 144, 0.18);
    border-radius: 12px;
    padding: 9px 12px;
}
QWidget#brokerRoot QLineEdit:focus,
QWidget#brokerRoot QComboBox:focus {
    border-color: rgba(122, 182, 255, 0.40);
    background: rgba(15, 22, 31, 0.99);
}
QWidget#brokerRoot QTextEdit#terminalConsole {
    background: rgba(8, 13, 19, 0.97);
    color: #e7eff8;
    border: 1px solid rgba(101, 119, 140, 0.16);
    border-radius: 14px;
    padding: 10px 12px;
}
QWidget#brokerRoot QTableWidget#terminalTable,
QWidget#brokerRoot QTableWidget#brokerOrdersTable,
QWidget#brokerRoot QTableWidget#submissionTable {
    background: rgba(8, 13, 19, 0.98);
    color: #eaf1f9;
    border: 1px solid rgba(107, 125, 146, 0.16);
    border-radius: 16px;
    padding: 6px;
    gridline-color: rgba(57, 72, 88, 0.55);
}
QWidget#brokerRoot QTableWidget#brokerOrdersTable::item,
QWidget#brokerRoot QTableWidget#submissionTable::item {
    padding: 7px 10px;
    border-bottom: 1px solid rgba(48, 62, 78, 0.46);
}
QWidget#brokerRoot QTableWidget#brokerOrdersTable::item:selected,
QWidget#brokerRoot QTableWidget#submissionTable::item:selected {
    background: rgba(44, 84, 132, 0.84);
    color: #f8fbff;
}
QWidget#brokerRoot QHeaderView::section {
    background: rgba(15, 22, 30, 0.98);
    color: #8ea4bd;
    border: none;
    border-bottom: 1px solid rgba(96, 115, 137, 0.22);
    padding: 10px 12px;
    font-weight: 800;
}
QWidget#brokerRoot QFrame#metricCard {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(22, 32, 44, 0.98), stop:1 rgba(11, 17, 24, 0.98));
    border: 1px solid rgba(111, 132, 156, 0.18);
    border-radius: 18px;
}
QWidget#brokerRoot QFrame#metricCard QLabel#metricCaption {
    color: #8a9eb4;
}
QWidget#brokerRoot QFrame#metricCard QLabel#metricValue {
    color: #f7fbff;
}
QWidget#brokerRoot QFrame#metricCard QLabel#metricAccent {
    color: #a8c4e3;
}
QWidget#brokerRoot QFrame#brokerSetupDrawer {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(13, 19, 27, 0.92), stop:1 rgba(9, 14, 20, 0.92));
    border: 1px solid rgba(110, 129, 150, 0.14);
    border-radius: 22px;
}
QWidget#brokerRoot QPushButton#ghostButton,
QWidget#brokerRoot QPushButton#tonalButton,
QWidget#brokerRoot QPushButton#accentButton {
    border-radius: 14px;
    padding: 10px 16px;
    font-weight: 800;
}
QWidget#brokerRoot QPushButton#ghostButton {
    background: rgba(17, 24, 33, 0.94);
    border: 1px solid rgba(108, 127, 148, 0.18);
    color: #d9e5f1;
}
QWidget#brokerRoot QPushButton#ghostButton:hover {
    border-color: rgba(144, 193, 255, 0.26);
    background: rgba(21, 29, 40, 0.98);
}
QWidget#brokerRoot QPushButton#tonalButton {
    background: rgba(29, 42, 58, 0.92);
    border: 1px solid rgba(126, 170, 232, 0.22);
    color: #eef5fc;
}
QWidget#brokerRoot QPushButton#accentButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(50, 92, 144, 0.98), stop:1 rgba(76, 128, 191, 0.98));
    border: 1px solid rgba(141, 190, 255, 0.34);
    color: #f8fbff;
}
QWidget#brokerRoot QPushButton#accentButton:hover {
    border-color: rgba(214, 233, 255, 0.62);
}
"""
        )
        self._qh_brand_polish_applied_v34 = True

    def _sync_commercial_navigation_v34(self) -> None:
        if not hasattr(self, "tabs"):
            return
        tab_specs = [
            ("市场总览", "查看市场结构、主线、消息面与全局节奏。"),
            ("扫描观察", "管理扫描结果、观察池和盘中焦点。"),
            ("机会推荐", "从每日推荐池推进到计划与送审。"),
            ("打板监控", "管理打板候选、回封监控与专项观察。"),
            ("系统配置", "统一维护参数、导出目录和运行偏好。"),
            ("账户登录", "维护东方财富、GM 与扩展渠道登录配置。"),
            ("复盘研究", "查看单票画像、执行回放与复盘结论。"),
            ("交易执行", "生成委托、确认提交、回看回执与模拟盘。"),
        ]
        bar = self.tabs.tabBar()
        for index, (label, tooltip) in enumerate(tab_specs):
            if index >= self.tabs.count():
                break
            if self.tabs.tabText(index) != label:
                self.tabs.setTabText(index, label)
            bar.setTabToolTip(index, tooltip)

    def _refresh_shell_header_v34(self) -> None:
        original_refresh_shell_header(self)
        current_index = self.tabs.currentIndex() if hasattr(self, "tabs") else 0
        current_name = self._workspace_name_for_index(current_index) if hasattr(self, "_workspace_name_for_index") else "龙头主控台"
        pool_count = len(getattr(self, "daily_pool_rows", []) or [])
        plan_count = len(list(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or []))
        pending_orders = len(getattr(self, "order_intents", []) or [])
        submitted_orders = len(getattr(self, "order_submission_records", []) or [])
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []) or [])
        warnings = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("warnings", []) or [])
        risk_tone = "risk" if blockers else ("watch" if warnings or pending_orders else ("buy" if submitted_orders or plan_count or pool_count else "idle"))

        page_key = {
            "市场总览": "overview",
            "市场机会工作台": "overview",
            "总览": "overview",
            "扫描": "scanner",
            "策略扫描": "scanner",
            "推荐": "recommend",
            "每日推荐": "recommend",
            "打板": "board",
            "打板专项": "board",
            "配置": "config",
            "参数配置": "config",
            "登录": "auth",
            "统一登录": "auth",
            "明细": "detail",
            "明细复盘": "detail",
            "交易": "broker",
            "交易执行": "broker",
        }.get(current_name, "overview")

        page_copy = {
            "overview": (
                "量化猎手 Pro",
                "把市场结构、主线持续性与交易节奏收束进统一驾驶舱。",
                "全局态势",
            ),
            "scanner": (
                "量化猎手 Pro / 扫描观察",
                "把盘中扫描、观察池与焦点筛选收成一条连续工作流。",
                "观察筛选",
            ),
            "recommend": (
                "量化猎手 Pro / 机会推荐",
                "从候选排序到交易计划生成，尽量压缩人工切页成本。",
                "推荐分发",
            ),
            "board": (
                "量化猎手 Pro / 打板监控",
                "把候选、回封监控与专项复盘做成一个真正可跟单的盘中工作台。",
                "打板监控",
            ),
            "config": (
                "量化猎手 Pro / 系统配置",
                "把策略参数、导出目录与运行偏好统一归口，减少碎片化设置成本。",
                "系统配置",
            ),
            "auth": (
                "量化猎手 Pro / 账户登录",
                "把登录、渠道与桥接环境统一托管，为后续多券商接入预留接口。",
                "账户连接",
            ),
            "detail": (
                "量化猎手 Pro / 复盘研究",
                "围绕单票形成决策画像、执行回放与复盘结论。",
                "复盘研究",
            ),
            "broker": (
                "量化猎手 Pro / 交易执行",
                "把委托生成、确认提交与回执回看压进同一执行工作台。",
                "交易执行",
            ),
        }
        pill_copy = {
            "overview": "FLAGSHIP DESK",
            "scanner": "LIVE SCAN",
            "recommend": "ALPHA FLOW",
            "board": "BOARD WATCH",
            "config": "SYSTEM LAB",
            "auth": "ACCESS LAYER",
            "detail": "REVIEW LAB",
            "broker": "EXECUTION CORE",
        }
        title, subtitle, badge = page_copy.get(page_key, ("量化猎手 Pro", "统一管理行情、推荐、执行与复盘。", "机构终端"))
        pulse_label_detail = getattr(getattr(self, "shell_pulse_label", None), "text", lambda: "")()
        pulse_hint_detail = getattr(getattr(self, "shell_pulse_hint", None), "text", lambda: "")()
        pulse_meta_detail = getattr(getattr(self, "shell_pulse_meta", None), "text", lambda: "")()
        if hasattr(self, "shell_product_title"):
            self._set_label_text_if_changed(self.shell_product_title, title, tooltip=title)
        if hasattr(self, "shell_product_subtitle"):
            self._set_label_text_if_changed(self.shell_product_subtitle, subtitle, tooltip=subtitle)
        if hasattr(self, "shell_brand_pill"):
            pill_text = pill_copy.get(page_key, "FLAGSHIP DESK")
            self._set_label_text_if_changed(self.shell_brand_pill, pill_text, tooltip=pill_text)
        for widget_name in [
            "tabs",
            "shell_brand_pill",
            "shell_product_eyebrow",
            "shell_product_title",
            "shell_product_subtitle",
            "top_badge",
            "shell_header",
            "shell_pulse_bar",
            "shell_workflow_bar",
            "shell_pulse_label",
            "shell_pulse_hint",
            "shell_pulse_meta",
        ]:
            widget = getattr(self, widget_name, None)
            if isinstance(widget, QWidget) and widget.property("pageTone") != page_key:
                widget.setProperty("pageTone", page_key)
                self.style().unpolish(widget)
                self.style().polish(widget)
                widget.update()
        shell_root = self.centralWidget() if hasattr(self, "centralWidget") else None
        if isinstance(shell_root, QWidget) and shell_root.property("pageTone") != page_key:
            shell_root.setProperty("pageTone", page_key)
            self.style().unpolish(shell_root)
            self.style().polish(shell_root)
            shell_root.update()
        if hasattr(self, "tabs"):
            bar = self.tabs.tabBar()
            if isinstance(bar, QWidget) and bar.property("pageTone") != page_key:
                bar.setProperty("pageTone", page_key)
                self.style().unpolish(bar)
                self.style().polish(bar)
                bar.update()
        for chip_name in ["shell_workspace_chip", "shell_focus_chip", "shell_market_chip", "shell_pipeline_chip", "shell_refresh_chip", "shell_runtime_chip"]:
            chip = getattr(self, chip_name, None)
            if isinstance(chip, dict):
                for key in ("frame", "label", "value"):
                    widget = chip.get(key)
                    if isinstance(widget, QWidget) and widget.property("pageTone") != page_key:
                        widget.setProperty("pageTone", page_key)
                        self.style().unpolish(widget)
                        self.style().polish(widget)
                        widget.update()
        for label_name in ("statusBanner", "focusStateLabel", "workspaceFocusBanner"):
            for label in self.findChildren(QLabel, label_name):
                if label.property("pageTone") != page_key:
                    label.setProperty("pageTone", page_key)
                    self.style().unpolish(label)
                    self.style().polish(label)
                    label.update()
        for label in self.findChildren(QLabel, "sectionTitle"):
            if label.property("pageTone") != page_key:
                label.setProperty("pageTone", page_key)
                self.style().unpolish(label)
                self.style().polish(label)
                label.update()
        for label in self.findChildren(QLabel, "inlineHint"):
            if label.property("pageTone") != page_key:
                label.setProperty("pageTone", page_key)
                self.style().unpolish(label)
                self.style().polish(label)
                label.update()
        for group_name in ("workspaceToolPanel", "terminalPanel"):
            for group in self.findChildren(QWidget, group_name):
                if group.property("pageTone") != page_key:
                    group.setProperty("pageTone", page_key)
                    self.style().unpolish(group)
                    self.style().polish(group)
                    group.update()
        for widget_name in ("marketNotePanel", "terminalConsole"):
            for text in self.findChildren(QTextEdit, widget_name):
                if text.property("pageTone") != page_key:
                    text.setProperty("pageTone", page_key)
                    self.style().unpolish(text)
                    self.style().polish(text)
                    text.update()
        for table_name in ("terminalTable", "marketPoolTable", "recommendPoolTable"):
            for table in self.findChildren(QTableWidget, table_name):
                if table.property("pageTone") != page_key:
                    table.setProperty("pageTone", page_key)
                    self.style().unpolish(table)
                    self.style().polish(table)
                    table.update()
        for chart in self.findChildren(QChartView, "marketChartPanel"):
            if chart.property("pageTone") != page_key:
                chart.setProperty("pageTone", page_key)
                self.style().unpolish(chart)
                self.style().polish(chart)
                chart.update()
        if hasattr(self, "top_badge"):
            badge_text = f"{badge} · 推{pool_count} · 计{plan_count} · 审{pending_orders}"
            self._set_label_text_if_changed(self.top_badge, badge_text, tooltip=badge_text)
        if hasattr(self, "shell_runtime_chip"):
            runtime_value = f"已提交 {submitted_orders} / 风险 {'红灯' if blockers else ('黄灯' if warnings else '绿灯')}"
            set_shell_chip_fn(self.shell_runtime_chip, runtime_value)

        if page_key == "recommend":
            focus_hint = "先看前排候选，再推进计划与送审。"
        elif page_key == "broker":
            focus_hint = "先核对闸门，再确认下单，再回看回执。"
        elif page_key == "detail":
            focus_hint = "先看决策画像，再看执行偏差，最后沉淀结论。"
        elif page_key == "scanner":
            focus_hint = "先筛焦点，再补观察池，再联动推荐和复盘。"
        elif page_key == "board":
            focus_hint = "先盯候选和回封，再决定是否送入交易链路。"
        else:
            focus_hint = "先确认市场快照，再推进推荐、计划和交易链路。"
        if hasattr(self, "shell_pulse_hint"):
            self._set_label_text_if_changed(self.shell_pulse_hint, focus_hint, tooltip=pulse_hint_detail or focus_hint)

        risk_label = "红灯" if blockers else ("黄灯" if warnings or pending_orders else "绿灯")
        pulse_summary = {
            "overview": f"市场总览：已生成 {pool_count} 只候选，{plan_count} 笔计划待推进。",
            "scanner": f"扫描观察：已完成 {pool_count} 条候选梳理，可继续聚焦重点标的。",
            "recommend": f"机会推荐：当前 {pool_count} 只候选，{plan_count} 笔计划待确认。",
            "board": f"打板监控：当前 {pool_count} 只候选，继续跟踪回封强度与承接。",
            "config": f"系统配置：当前任务{'运行中' if risk_tone == 'buy' else '待机中'}，状态 {risk_label}。",
            "auth": f"账户接入：连接状态待确认，当前风险提示 {risk_label}。",
            "detail": f"复盘研究：已回写 {submitted_orders} 笔执行记录，可继续查看复盘结论。",
            "broker": f"交易执行：{pending_orders} 笔待确认，{submitted_orders} 笔已提交。",
        }.get(page_key, f"终端概览：当前 {pool_count} 只候选，{plan_count} 笔计划待推进。")
        meta_summary = f"状态 {risk_label} | 候选 {pool_count} | 计划 {plan_count} | 已提交 {submitted_orders}"
        if hasattr(self, "shell_pulse_label"):
            self._set_label_text_if_changed(self.shell_pulse_label, pulse_summary, tooltip=pulse_label_detail or pulse_summary)
        if hasattr(self, "shell_pulse_meta"):
            self._set_label_text_if_changed(self.shell_pulse_meta, meta_summary, tooltip=pulse_meta_detail or meta_summary)

        for widget_name in ["shell_header", "shell_pulse_bar", "shell_workflow_bar"]:
            widget = getattr(self, widget_name, None)
            if isinstance(widget, QWidget):
                if widget.property("stateTone") != risk_tone:
                    widget.setProperty("stateTone", risk_tone)
                    self.style().unpolish(widget)
                    self.style().polish(widget)
                    widget.update()
        self.setWindowTitle(f"量化猎手 Pro - {badge}")

    def _post_build_ui_tweaks_v34(self) -> None:
        original_post_build_ui_tweaks(self)
        self._apply_commercial_brand_polish_v34()
        self._sync_commercial_navigation_v34()
        self._refresh_shell_header()

    window_cls._apply_commercial_brand_polish_v34 = _apply_commercial_brand_polish_v34
    window_cls._sync_commercial_navigation_v34 = _sync_commercial_navigation_v34
    window_cls._refresh_shell_header = _refresh_shell_header_v34
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v34
    window_cls._qh_commercial_chrome_patches_applied_v34 = True
