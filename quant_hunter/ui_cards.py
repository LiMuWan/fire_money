from __future__ import annotations

from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget


class InsightCardBase(QFrame):
    def __init__(self, object_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName(object_name)

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
            f"QFrame#{self.objectName()} {{ background:#11161d; border:1px solid {border_color}; border-radius:14px; }}",
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
        self.setStyleSheet("".join(rules))


class LeaderboardCard(InsightCardBase):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("leaderboardCard", parent)
        self.setMinimumHeight(168)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        self.rank_label = QLabel("TOP")
        self.rank_label.setObjectName("leaderboardRank")
        self.name_label = QLabel("等待刷新")
        self.name_label.setObjectName("leaderboardName")
        self.strategy_label = QLabel("题材方向")
        self.strategy_label.setObjectName("leaderboardMeta")
        self.fund_label = QLabel("资金标签")
        self.fund_label.setObjectName("leaderboardMeta")
        self.metrics_label = QLabel("热度 / 涨幅")
        self.metrics_label.setObjectName("leaderboardMetric")
        self.flow_label = QLabel("主力净流入")
        self.flow_label.setObjectName("leaderboardFlow")

        for widget in (
            self.rank_label,
            self.name_label,
            self.strategy_label,
            self.fund_label,
            self.metrics_label,
            self.flow_label,
        ):
            widget.setWordWrap(True)
            layout.addWidget(widget)
        layout.addStretch(1)

    def set_row(self, rank_text: str, row) -> None:
        accent = {"TOP 1": "#f5c451", "TOP 2": "#cfd8e3", "TOP 3": "#b7835a"}.get(rank_text, "#7ed7ff")
        strategy_name = getattr(row, "primary_strategy", "") or getattr(row, "strategy_tag", "")
        decision_score = getattr(row, "dragon_decision_score", getattr(row, "heat_score", 0.0))
        self._apply_card_styles(
            border_color=accent,
            title_selector="leaderboardName",
            title_color="#f5f7fa",
            title_size=18,
            subtitle_selector="leaderboardMeta",
            subtitle_color="#8fa0b6",
            emphasis_selector="leaderboardMetric",
            emphasis_color="#25f3ff",
            emphasis_size=12,
        )
        self.rank_label.setStyleSheet(f"color:{accent}; font-size:12px; font-weight:800;")
        self.flow_label.setStyleSheet(f"color:{accent}; font-size:12px; font-weight:700;")
        self.rank_label.setText(rank_text)
        self.name_label.setText(f"{row.stock_name} {row.stock_id}")
        self.strategy_label.setText(f"主策略: {strategy_name}")
        self.fund_label.setText(f"资金标签: {getattr(row, 'fund_model', '')}")
        self.metrics_label.setText(
            f"决策分 {decision_score:.1f} | 热度 {getattr(row, 'heat_score', 0.0):.1f} | 涨幅 {getattr(row, 'pct_change', 0.0):.2f}%"
        )
        self.flow_label.setText(f"主力净流入 {getattr(row, 'main_inflow', 0.0) / 1e8:.2f} 亿")

    def set_message(self, title: str, message: str) -> None:
        self.setStyleSheet(
            "QFrame#leaderboardCard { background:#11161d; border:1px solid #2f3d4f; border-radius:12px; }"
            "QLabel#leaderboardRank { color:#8fa0b6; font-size:12px; font-weight:800; }"
            "QLabel#leaderboardName { color:#f5f7fa; font-size:16px; font-weight:800; }"
            "QLabel#leaderboardMeta { color:#8fa0b6; font-size:12px; }"
            "QLabel#leaderboardMetric { color:#8fa0b6; font-size:12px; font-weight:700; }"
            "QLabel#leaderboardFlow { color:#8fa0b6; font-size:12px; }"
        )
        self.rank_label.setText(title)
        self.name_label.setText(message)
        self.strategy_label.setText("")
        self.fund_label.setText("")
        self.metrics_label.setText("")
        self.flow_label.setText("")


class StrategyWorkbenchCard(InsightCardBase):
    def __init__(self, title: str, subtitle: str, parent: QWidget | None = None) -> None:
        super().__init__("strategyWorkbenchCard", parent)
        self.setMinimumHeight(188)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

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
        self.summary_label.setStyleSheet("color:#e6eef7; font-size:13px; font-weight:700;")
        self.top_list_label.setStyleSheet("color:#cdd9e5; font-size:12px;")

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
        self.summary_label.setText(f"头号候选：{focus_name}")
        self.meta_label.setText(
            f"{strategy_name} 命中 {primary_count} 只 | 评分 {focus_score:.1f} | 题材 {focus_theme} | 动作 {focus_action}"
        )
        self.top_list_label.setText("\n".join(top_rows) if top_rows else "等待生成推荐池后更新。")

    def set_empty(self, message: str = "等待生成推荐池后更新。") -> None:
        self.summary_label.setText(message)
        self.meta_label.setText("")
        self.top_list_label.setText("")


class ActionFlowCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("actionFlowCard", parent)
        self.accent = accent
        self.setMinimumHeight(132)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

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

        layout.addWidget(self.title_label)
        layout.addWidget(self.count_label)
        layout.addWidget(self.focus_label)
        layout.addWidget(self.note_label)
        layout.addStretch(1)
        self._apply()

    def _apply(self) -> None:
        self._apply_card_styles(
            border_color=self.accent,
            title_selector="actionFlowTitle",
            title_color="#f5f7fa",
            title_size=15,
            emphasis_selector="actionFlowCount",
            emphasis_color=self.accent,
            emphasis_size=22,
        )
        self.focus_label.setStyleSheet("color:#dce7f3; font-size:12px; font-weight:700;")
        self.note_label.setStyleSheet("color:#8fa0b6; font-size:12px;")

    def set_data(self, count_text: str, focus_text: str, note_text: str) -> None:
        self.count_label.setText(count_text)
        self.focus_label.setText(focus_text)
        self.note_label.setText(note_text)


class CompactSummaryCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("compactSummaryCard", parent)
        self.setMinimumHeight(118)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("compactSummaryTitle")
        self.headline_label = QLabel("--")
        self.headline_label.setObjectName("compactSummaryHeadline")
        self.detail_label = QLabel("")
        self.detail_label.setObjectName("compactSummaryDetail")
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        layout.addWidget(self.headline_label)
        layout.addWidget(self.detail_label)
        layout.addStretch(1)

        self._apply_card_styles(
            border_color=accent,
            title_selector="compactSummaryTitle",
            title_color="#f5f7fa",
            title_size=14,
            emphasis_selector="compactSummaryHeadline",
            emphasis_color=accent,
            emphasis_size=18,
        )
        self.detail_label.setStyleSheet("color:#d5e1ec; font-size:12px;")

    def set_data(self, headline: str, detail: str) -> None:
        self.headline_label.setText(headline)
        self.detail_label.setText(detail)


class AlertSignalCard(InsightCardBase):
    def __init__(self, title: str, accent: str, parent: QWidget | None = None) -> None:
        super().__init__("alertSignalCard", parent)
        self.accent = accent
        self.setMinimumHeight(116)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("alertSignalTitle")
        self.status_label = QLabel("待刷新")
        self.status_label.setObjectName("alertSignalStatus")
        self.detail_label = QLabel("等待盘中刷新后更新提示。")
        self.detail_label.setObjectName("alertSignalDetail")
        self.detail_label.setWordWrap(True)

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
        self.detail_label.setStyleSheet("color:#d5e1ec; font-size:12px;")

    def set_data(self, status: str, detail: str) -> None:
        self.status_label.setText(status)
        self.detail_label.setText(detail)
