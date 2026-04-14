from __future__ import annotations

from PySide6.QtWidgets import QWidget


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
    border-radius: 24px;
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
    border-radius: 18px;
}
QFrame#shellPulseBar {
    border-radius: 18px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 27, 38, 0.98), stop:1 rgba(11, 17, 24, 0.98));
    border: 1px solid rgba(120, 142, 165, 0.20);
}
QFrame#shellPulseBar[stateTone="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.28);
}
QFrame#shellPulseBar[stateTone="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.28);
}
QFrame#shellPulseBar[stateTone="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.28);
}
QLabel#topBadge {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0aa4d, stop:1 #ffd166);
    color: #111720;
    border-radius: 12px;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 900;
}
QTabWidget::pane {
    border: 1px solid rgba(109, 131, 153, 0.16);
    border-radius: 18px;
    background: rgba(10, 15, 21, 0.72);
    top: -2px;
}
QTabBar::tab {
    min-width: 108px;
    padding: 11px 16px;
    margin-right: 8px;
    border-radius: 14px;
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
                "把市场结构、主线持续性、消息催化与交易节奏收束进统一驾驶舱。",
                "全局态势",
            ),
            "scanner": (
                "量化猎手 Pro / 扫描观察",
                "把盘中扫描、观察池与临门一脚的焦点筛选收成一条连续工作流。",
                "观察筛选",
            ),
            "recommend": (
                "量化猎手 Pro / 机会推荐",
                "从候选排序、主线审查到交易计划生成，尽量压缩人工切页成本。",
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
                "围绕单票形成决策画像、执行回放与复盘结论，沉淀可复用经验。",
                "复盘研究",
            ),
            "broker": (
                "量化猎手 Pro / 交易执行",
                "把委托生成、下单确认、回执回看与模拟盘试运行压进同一执行工作台。",
                "交易执行",
            ),
        }
        title, subtitle, badge = page_copy.get(page_key, ("量化猎手 Pro", "统一管理行情、推荐、执行与复盘。", "机构终端"))
        if hasattr(self, "shell_product_title"):
            self._set_label_text_if_changed(self.shell_product_title, title, tooltip=title)
        if hasattr(self, "shell_product_subtitle"):
            self._set_label_text_if_changed(self.shell_product_subtitle, subtitle, tooltip=subtitle)
        if hasattr(self, "top_badge"):
            badge_text = f"{badge} | 推荐 {pool_count} | 计划 {plan_count} | 待审 {pending_orders}"
            self._set_label_text_if_changed(self.top_badge, badge_text, tooltip=badge_text)
        if hasattr(self, "shell_runtime_chip"):
            runtime_value = f"已提交 {submitted_orders} / 风险 {'红灯' if blockers else ('黄灯' if warnings else '绿灯')}"
            set_shell_chip_fn(self.shell_runtime_chip, runtime_value)

        if page_key == "recommend":
            focus_hint = "先看前排候选，再送审，再去交易执行。"
        elif page_key == "broker":
            focus_hint = "先核对闸门与风险灯，再确认下单，再回看回执。"
        elif page_key == "detail":
            focus_hint = "先看决策画像，再看执行偏差，最后沉淀结论。"
        elif page_key == "scanner":
            focus_hint = "先筛焦点，再补观察池，再联动推荐和复盘。"
        elif page_key == "board":
            focus_hint = "先盯候选和回封，再决定是否送入交易链路。"
        else:
            focus_hint = "先确认市场快照，再推进推荐、计划和交易链路。"
        if hasattr(self, "shell_pulse_hint"):
            self._set_label_text_if_changed(self.shell_pulse_hint, focus_hint, tooltip=focus_hint)

        for widget_name in ["shell_header", "shell_pulse_bar"]:
            widget = getattr(self, widget_name, None)
            if isinstance(widget, QWidget):
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
