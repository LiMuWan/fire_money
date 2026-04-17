from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class InsightCardBase(QFrame):
    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)

    def _set_label_if_changed(self, widget: QLabel, text: str) -> None:
        if widget.text() != text:
            if hasattr(widget, "setTextFormat"):
                widget.setTextFormat(Qt.RichText if "<span" in str(text) else Qt.AutoText)
            widget.setText(text)

    def _set_stylesheet_if_changed(self, widget, stylesheet: str) -> None:
        if widget.styleSheet() != stylesheet:
            widget.setStyleSheet(stylesheet)

    def _create_accent_strip(self, accent_color: str) -> QFrame:
        strip = QFrame()
        strip.setFixedHeight(5)
        strip.setStyleSheet(
            "QFrame {"
            f"background:qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(255,255,255,0.0), stop:0.2 {accent_color}, stop:0.8 {accent_color}, stop:1 rgba(255,255,255,0.0));"
            "border:none; border-radius:2px; }"
        )
        return strip

    def _apply_card_styles(
        self,
        *,
        border_color: str,
        title_selector: str,
        title_color: str,
        title_size: int,
        title_weight: int = 800,
        subtitle_selector: str | None = None,
        subtitle_color: str = "#8fa0b6",
        subtitle_size: int = 12,
        emphasis_selector: str | None = None,
        emphasis_color: str = "#25f3ff",
        emphasis_size: int = 12,
    ) -> None:
        rules = [
            (
                f"QFrame#{self.objectName()} {{ "
                "background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(19, 26, 35, 0.98), stop:0.52 rgba(13, 18, 25, 0.98), stop:1 rgba(10, 15, 22, 0.99)); "
                f"border:1px solid {border_color}; border-radius:16px; }}"
            ),
            f"QFrame#{self.objectName()} QLabel {{ background: transparent; }}",
            f"QLabel#{title_selector} {{ color:{title_color}; font-size:{title_size}px; font-weight:{title_weight}; }}",
        ]
        if subtitle_selector:
            rules.append(
                f"QLabel#{subtitle_selector} {{ color:{subtitle_color}; font-size:{subtitle_size}px; }}"
            )
        if emphasis_selector:
            rules.append(
                f"QLabel#{emphasis_selector} {{ color:{emphasis_color}; font-size:{emphasis_size}px; font-weight:700; }}"
            )
        rules.append(
            f"QFrame#{self.objectName()}:hover {{ border: 1px solid rgba(151, 203, 255, 0.22); }}"
        )
        self._set_stylesheet_if_changed(self, "".join(rules))


class LeaderboardCard(InsightCardBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("leaderboardCard", parent)
        self._compact_density = False
        self.setMinimumHeight(142)
        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(4)

        self.rank_label = QLabel("TOP")
        self.rank_label.setObjectName("leaderboardRank")
        self.status_label = QLabel("LIVE")
        self.status_label.setObjectName("leaderboardBadge")
        self.name_label = QLabel("等待刷新")
        self.name_label.setObjectName("leaderboardName")
        self.strategy_label = QLabel("题材方向")
        self.strategy_label.setObjectName("leaderboardMeta")
        self.reason_label = QLabel("Signal building")
        self.reason_label.setObjectName("leaderboardReason")
        self.fund_label = QLabel("资金标签")
        self.fund_label.setObjectName("leaderboardMeta")
        self.metrics_label = QLabel("热度 / 涨幅")
        self.metrics_label.setObjectName("leaderboardMetric")
        self.flow_label = QLabel("主力净流入")
        self.flow_label.setObjectName("leaderboardFlow")

        for widget in (
            self.rank_label,
            self.status_label,
            self.name_label,
            self.strategy_label,
            self.reason_label,
            self.fund_label,
            self.metrics_label,
            self.flow_label,
        ):
            widget.setWordWrap(True)
            layout.addWidget(widget)
        layout.addStretch(1)
        self.set_density(False)

    def set_density(self, compact: bool) -> None:
        self._compact_density = bool(compact)
        self.setMinimumHeight(104 if self._compact_density else 142)
        self.setMaximumHeight(118 if self._compact_density else 16777215)
        self._layout.setContentsMargins(
            12 if self._compact_density else 16,
            10 if self._compact_density else 13,
            12 if self._compact_density else 16,
            10 if self._compact_density else 13,
        )
        self._layout.setSpacing(3 if self._compact_density else 4)
        self.fund_label.setVisible(True)
        self.flow_label.setVisible(not self._compact_density)

    def set_row(self, rank_text: str, row) -> None:
        accent = {"TOP 1": "#f5c451", "TOP 2": "#cfd8e3", "TOP 3": "#b7835a"}.get(rank_text, "#7ed7ff")
        strategy_name = getattr(row, "primary_strategy", "") or getattr(row, "strategy_tag", "")
        decision_score = getattr(row, "dragon_decision_score", getattr(row, "heat_score", 0.0))
        pct_change = float(getattr(row, "pct_change", 0.0) or 0.0)
        main_inflow = float(getattr(row, "main_inflow", 0.0) or 0.0)
        heat_score = float(getattr(row, "heat_score", 0.0) or 0.0)
        action = str(getattr(row, "action", "") or "").upper()
        if action == "BUY":
            status_text = "可执行"
        elif action in {"SELL", "REDUCE"}:
            status_text = "风险升高"
        else:
            status_text = "交易中"
        reason_parts: list[str] = []
        if heat_score >= 85:
            reason_parts.append("主线强化")
        elif heat_score >= 70:
            reason_parts.append("热度上行")
        if main_inflow > 0:
            reason_parts.append("资金承接")
        if pct_change >= 5:
            reason_parts.append("趋势扩散")
        if not reason_parts and strategy_name:
            reason_parts.append(strategy_name)
        reason_text = "入选原因：" + " | ".join(reason_parts[:2]) if reason_parts else "入选原因：等待市场与候选同步"
        self._apply_card_styles(
            border_color="rgba(110, 129, 151, 0.20)",
            title_selector="leaderboardName",
            title_color="#f5f7fa",
            title_size=17,
            subtitle_selector="leaderboardMeta",
            subtitle_color="#8ea2b8",
            emphasis_selector="leaderboardMetric",
            emphasis_color="#d8e7f6",
            emphasis_size=11,
        )
        self._set_stylesheet_if_changed(self.rank_label, f"color:{accent}; font-size:11px; font-weight:900; letter-spacing:0.6px;")
        self._set_stylesheet_if_changed(self.flow_label, "color:#9eb4ca; font-size:11px; font-weight:700;")
        self._set_stylesheet_if_changed(
            self.status_label,
            f"color:{accent}; font-size:10px; font-weight:800; letter-spacing:0.8px; "
            "background:rgba(255,255,255,0.03); border:1px solid rgba(126, 183, 255, 0.14); "
            "border-radius:9px; padding:3px 8px;"
        )
        self._set_stylesheet_if_changed(self.reason_label, "color:#c7d5e3; font-size:10px; font-weight:600;")
        self._set_label_if_changed(self.rank_label, rank_text)
        self._set_label_if_changed(self.status_label, status_text)
        self.status_label.setToolTip(
            "\n".join(
                [
                    f"动作：{getattr(row, 'action', '') or 'WAIT'}",
                    f"策略：{strategy_name or '待确认'}",
                    f"主线：{getattr(row, 'mainline_tag', '') or getattr(row, 'theme_name', '') or '待确认'}",
                    f"原因：{' | '.join(reason_parts[:2]) if reason_parts else '等待市场与候选同步'}",
                ]
            )
        )
        self._set_label_if_changed(self.name_label, f"{row.stock_name} {row.stock_id}")
        short_reason = " | ".join(reason_parts[:2]) if reason_parts else (strategy_name or "等待同步")
        self._set_label_if_changed(self.reason_label, short_reason)
        self._set_label_if_changed(self.strategy_label, f"主策略：{strategy_name}")
        self._set_label_if_changed(self.fund_label, f"资金标签：{getattr(row, 'fund_model', '')}")
        self._set_label_if_changed(
            self.metrics_label,
            f"决策 {decision_score:.1f} | 热度 {getattr(row, 'heat_score', 0.0):.1f} | 涨跌 {getattr(row, 'pct_change', 0.0):.2f}%"
        )
        self._set_label_if_changed(self.flow_label, f"资金 {getattr(row, 'main_inflow', 0.0) / 1e8:.2f} 亿")

    def set_message(self, title: str, message: str) -> None:
        self._set_stylesheet_if_changed(
            self,
            "QFrame#leaderboardCard { background:qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(19,26,35,0.98), stop:1 rgba(10,15,22,0.99)); border:1px solid rgba(110,129,151,0.18); border-radius:16px; }"
            "QLabel#leaderboardRank { color:#8fa0b6; font-size:11px; font-weight:900; }"
            "QLabel#leaderboardBadge { color:#8fa0b6; font-size:10px; font-weight:800; }"
            "QLabel#leaderboardName { color:#f5f7fa; font-size:15px; font-weight:800; }"
            "QLabel#leaderboardMeta { color:#8fa0b6; font-size:11px; }"
            "QLabel#leaderboardReason { color:#c7d6e6; font-size:11px; font-weight:600; }"
            "QLabel#leaderboardMetric { color:#8fa0b6; font-size:11px; font-weight:700; }"
            "QLabel#leaderboardFlow { color:#8fa0b6; font-size:11px; }"
        )
        self._set_label_if_changed(self.rank_label, title)
        self._set_label_if_changed(self.status_label, "WAIT")
        self.status_label.setToolTip("动作：WAIT\n状态：等待同步新的市场与推荐数据")
        self._set_label_if_changed(self.name_label, message)
        self._set_label_if_changed(self.strategy_label, "")
        self._set_label_if_changed(self.reason_label, "等待市场与候选同步")
        self._set_label_if_changed(self.fund_label, "")
        self._set_label_if_changed(self.metrics_label, "")
        self._set_label_if_changed(self.flow_label, "")


class StrategyWorkbenchCard(InsightCardBase):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__("strategyWorkbenchCard", parent)
        self.setMinimumHeight(176)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.accent_strip = self._create_accent_strip("#8fc7ff")
        self.title_label = QLabel(title)
        self.title_label.setObjectName("strategyWorkbenchTitle")
        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("strategyWorkbenchSubtitle")
        self.subtitle_label.setWordWrap(True)
        self.summary_label = QLabel("等待生成推荐池后更新。")
        self.summary_label.setObjectName("strategyWorkbenchSummary")
        self.summary_label.setWordWrap(True)
        self.meta_label = QLabel("")
        self.meta_label.setObjectName("strategyWorkbenchMeta")
        self.meta_label.setWordWrap(True)
        self.top_list_label = QLabel("")
        self.top_list_label.setObjectName("strategyWorkbenchList")
        self.top_list_label.setWordWrap(True)

        layout.addWidget(self.accent_strip)
        layout.addWidget(self.title_label)
        layout.addWidget(self.subtitle_label)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.meta_label)
        layout.addWidget(self.top_list_label)
        layout.addStretch(1)

        self._apply_card_styles(
            border_color="#223040",
            title_selector="strategyWorkbenchTitle",
            title_color="#f5f7fa",
            title_size=17,
            subtitle_selector="strategyWorkbenchSubtitle",
            subtitle_color="#8fa0b6",
            emphasis_selector="strategyWorkbenchMeta",
            emphasis_color="#8fc7ff",
            emphasis_size=12,
        )
        self.summary_label.setStyleSheet("color:#eef4fb; font-size:13px; font-weight:700;")
        self.top_list_label.setStyleSheet("color:#d6e0ea; font-size:12px; line-height:1.45;")

    def set_strategy_summary(
        self,
        strategy_name: str,
        primary_count: int,
        focus_name: str,
        focus_score: float,
        focus_theme: str,
        focus_action: str,
        top_rows: list[str],
    ) -> None:
        self._set_label_if_changed(self.summary_label, f"头号候选：{focus_name}")
        self._set_label_if_changed(
            self.meta_label,
            f"{strategy_name} 命中 {primary_count} 只 | 评分 {focus_score:.1f} | 题材 {focus_theme} | 动作 {focus_action}",
        )
        self._set_label_if_changed(self.top_list_label, "\n".join(top_rows) if top_rows else "等待生成推荐池后更新。")

    def set_empty(self, message: str = "等待生成推荐池后更新。") -> None:
        self._set_label_if_changed(self.summary_label, message)
        self._set_label_if_changed(self.meta_label, "建议先刷新市场、同步题材和候选，再看该战法的前排标的。")
        self._set_label_if_changed(self.top_list_label, "前排列表会在生成推荐池后出现在这里。")


class ActionFlowCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("actionFlowCard", parent)
        self.accent = accent
        self.setMinimumHeight(96)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(3)

        self.accent_strip = self._create_accent_strip(accent)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("actionFlowTitle")
        self.count_label = QLabel("--")
        self.count_label.setObjectName("actionFlowCount")
        self.focus_label = QLabel("等待更新")
        self.focus_label.setObjectName("actionFlowFocus")
        self.focus_label.setWordWrap(True)
        self.note_label = QLabel("")
        self.note_label.setObjectName("actionFlowNote")
        self.note_label.setWordWrap(True)

        layout.addWidget(self.accent_strip)
        layout.addWidget(self.title_label)
        layout.addWidget(self.count_label)
        layout.addWidget(self.focus_label)
        layout.addWidget(self.note_label)
        layout.addStretch(1)
        self._apply()

    def _apply(self) -> None:
        self._apply_card_styles(
            border_color="rgba(110, 129, 151, 0.16)",
            title_selector="actionFlowTitle",
            title_color="#889db1",
            title_size=11,
            emphasis_selector="actionFlowCount",
            emphasis_color=self.accent,
            emphasis_size=16,
        )
        self.focus_label.setStyleSheet("color:#e8f0f8; font-size:11px; font-weight:800;")
        self.note_label.setStyleSheet("color:#7d92a7; font-size:9px; line-height:1.2;")

    def set_data(self, count_text: str, focus_text: str, note_text: str) -> None:
        self._set_label_if_changed(self.count_label, count_text)
        self._set_label_if_changed(self.focus_label, focus_text)
        self._set_label_if_changed(self.note_label, note_text)


class CompactSummaryCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("compactSummaryCard", parent)
        self._compact_density = False
        self.setMinimumHeight(96)
        layout = QVBoxLayout(self)
        self._layout = layout
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)

        self.accent_strip = self._create_accent_strip(accent)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("compactSummaryTitle")
        self.headline_label = QLabel("--")
        self.headline_label.setObjectName("compactSummaryHeadline")
        self.headline_label.setWordWrap(True)
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("compactSummaryDetail")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.accent_strip)
        layout.addWidget(self.title_label)
        layout.addWidget(self.headline_label)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)

        self._apply_card_styles(
            border_color="rgba(110, 129, 151, 0.18)",
            title_selector="compactSummaryTitle",
            title_color="#98aec5",
            title_size=12,
            emphasis_selector="compactSummaryHeadline",
            emphasis_color="#f4f8fc",
            emphasis_size=17,
        )
        self.detail_label.setStyleSheet("color:#90a4b8; font-size:10px; line-height:1.3;")
        self.set_density(False)

    def set_density(self, compact: bool) -> None:
        self._compact_density = bool(compact)
        self.setMinimumHeight(74 if self._compact_density else 96)
        self.setMaximumHeight(82 if self._compact_density else 16777215)
        self._layout.setContentsMargins(
            12 if self._compact_density else 16,
            10 if self._compact_density else 14,
            12 if self._compact_density else 16,
            10 if self._compact_density else 14,
        )
        self._layout.setSpacing(3 if self._compact_density else 5)
        self.title_label.setStyleSheet(
            f"color:#98aec5; font-size:{11 if self._compact_density else 12}px; font-weight:900;"
        )
        self.headline_label.setStyleSheet(
            f"color:#f4f8fc; font-size:{15 if self._compact_density else 17}px; font-weight:800;"
        )
        self.detail_label.setStyleSheet(
            f"color:#90a4b8; font-size:{9 if self._compact_density else 10}px; line-height:1.25;"
        )

    def set_data(self, headline: str, detail: str) -> None:
        self._set_label_if_changed(self.headline_label, headline)
        self._set_label_if_changed(self.detail_label, detail)


class AlertSignalCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("alertSignalCard", parent)
        self.accent = accent
        self.setMinimumHeight(106)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(6)

        self.accent_strip = self._create_accent_strip(accent)
        self.title_label = QLabel(title)
        self.title_label.setObjectName("alertSignalTitle")
        self.status_label = QLabel("待刷新")
        self.status_label.setObjectName("alertSignalStatus")
        self.status_label.setWordWrap(True)
        self.detail_label = QLabel("等待盘中刷新后更新提醒。")
        self.detail_label.setObjectName("alertSignalDetail")
        self.detail_label.setWordWrap(True)

        layout.addWidget(self.accent_strip)
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)

        self._apply_card_styles(
            border_color=accent,
            title_selector="alertSignalTitle",
            title_color="#f5f7fa",
            title_size=14,
            emphasis_selector="alertSignalStatus",
            emphasis_color=accent,
            emphasis_size=17,
        )
        self.detail_label.setStyleSheet("color:#dce6f0; font-size:12px; line-height:1.4;")

    def set_data(self, status: str, detail: str) -> None:
        self._set_label_if_changed(self.status_label, status)
        self._set_label_if_changed(self.detail_label, detail)

