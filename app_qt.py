from __future__ import annotations

import csv
import sys
import time as time_module
from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDateTime, QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QColor
from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QCandlestickSeries,
    QCandlestickSet,
    QChart,
    QChartView,
    QDateTimeAxis,
    QLineSeries,
    QValueAxis,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QScroller,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QHeaderView,
)

from quant_hunter.backtest import Backtester, format_result
from quant_hunter.board import BoardModeEngine
from quant_hunter.broker import EastmoneyBrokerAdapter
from quant_hunter.decision import DecisionEngine
from quant_hunter.data import (
    extract_stock_id,
    load_bars_from_csv,
    load_cash_snapshot_from_csv,
    load_holdings_from_csv,
    load_news_catalysts_from_csv,
    load_stock_profiles_from_csv,
    load_theme_aliases_from_csv,
)
from quant_hunter.models import (
    BrokerProfile,
    CashSnapshot,
    DailyAnalysis,
    HoldingRecord,
    RecommendationRow,
    OptimizationRun,
    OrderIntent,
    PriceBar,
    ScanRow,
    StockProfile,
    SymbolBacktestSummary,
)
from quant_hunter.market_feed import CacheOnlyMarketFeed, LocalMarketCache, MarketScreenResult, RemoteMarketScreener
from quant_hunter.optimizer import ParameterOptimizer
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.reports import export_daily_trade_plan, export_end_of_day_review, export_workspace_report
from quant_hunter.scanner import UniverseScanner
from quant_hunter.storage import AppState, load_app_state, save_app_state
from quant_hunter.strategy import AntiHarvestStrategy, StrategyParams
from quant_hunter.theme import summarize_themes
from quant_hunter.ui_cards import (
    ActionFlowCard,
    AlertSignalCard,
    CompactSummaryCard,
    InsightCardBase,
    LeaderboardCard,
    StrategyWorkbenchCard,
)
from quant_hunter.ui_controllers import refresh_daily_pool_controller, refresh_remote_market_controller, run_background_job_controller, run_parameter_optimization_controller, save_strategy_preferences_controller
from quant_hunter.ui_config import (
    DISPLAY_TEXT,
    OVERVIEW_QUICK_ROUTE_SPECS,
    STRATEGY_FILTER_LABELS,
    STRATEGY_SCORE_FIELDS,
    STRATEGY_WORKBENCH_SPECS,
    THEME_OPTIONS,
    WORKSPACE_LABEL_BY_KEY,
    WORKSPACE_TAB_LABELS,
    WORKSPACE_TAB_ORDER,
)
from quant_hunter.ui_runtime import append_runtime_log as append_runtime_log_runtime, build_runtime_overview_text, clear_market_cache as clear_market_cache_runtime, export_runtime_log as export_runtime_log_runtime, record_job_result as record_job_result_runtime, refresh_runtime_panel as refresh_runtime_panel_runtime, runtime_export_dir as runtime_export_dir_runtime
from quant_hunter.ui_helpers import (
    build_workspace_badge,
    build_workspace_hero,
    set_button_role,
    style_terminal_console,
    style_terminal_panel,
)
from quant_hunter.ui_binders import apply_daily_pool_rows, apply_market_screen_result, apply_scan_universe_result, handle_daily_pool_error, handle_market_refresh_error, handle_scan_error, refresh_license_status_view
from quant_hunter.ui_refresh import (
    apply_market_filters,
    fill_backtest_summaries,
    fill_scan_rows,
    populate_market_depth_texts,
    populate_filtered_daily_pool_table,
    refresh_intraday_monitor,
    refresh_action_flow_cards,
    refresh_overview_priority_cards,
    refresh_priority_cards,
    refresh_recommend_summary_cards,
    refresh_watchlist,
    refresh_strategy_pack_panels,
    refresh_strategy_focus_detail,
    refresh_theme_heat_panels,
    refresh_strategy_path_panel,
    render_leaderboard_cards,
)
from quant_hunter.workspace_builders import (
    build_auth_workspace,
    build_board_workspace,
    build_broker_workspace,
    build_config_workspace,
    build_detail_workspace,
    build_overview_workspace,
    build_recommend_workspace,
)


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DIR = PROJECT_ROOT / "sample_data"
STATE_FILE = PROJECT_ROOT / ".quant_hunter" / "app_state.json"
REPORT_DIR = PROJECT_ROOT / "reports"
THEME_STYLES = {
    "sunrise": """
        QMainWindow, QWidget {
            background: #f7f1e7;
            color: #2d261f;
            font-family: "Microsoft YaHei UI", "Segoe UI";
            font-size: 13px;
        }
        QTabWidget::pane {
            border: 1px solid #decdb6;
            border-radius: 18px;
            background: #fbf7f1;
            top: -1px;
        }
        QTabBar::tab {
            background: #eadbc7;
            color: #5b4730;
            border: 1px solid #d5c1a9;
            padding: 10px 18px;
            margin-right: 6px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        QTabBar::tab:selected {
            background: #fff8ee;
            color: #8a5a10;
            font-weight: 700;
        }
        QGroupBox {
            border: 1px solid #dcc8a7;
            border-radius: 16px;
            margin-top: 14px;
            padding: 18px 14px 14px 14px;
            background: #fffaf3;
            font-weight: 700;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #8a5a10;
        }
        QPushButton {
            background: #c98b2e;
            color: #fffaf5;
            border: none;
            border-radius: 12px;
            padding: 9px 16px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #b7771e;
        }
        QPushButton:pressed {
            background: #9f6518;
        }
        QLineEdit, QComboBox, QListWidget, QTextEdit, QTableWidget {
            background: #fffdf9;
            border: 1px solid #d6c4aa;
            border-radius: 12px;
            padding: 6px;
            selection-background-color: #d79b3d;
            selection-color: #ffffff;
        }
        QTableWidget {
            gridline-color: #eadfce;
            alternate-background-color: #f8f1e6;
        }
        QHeaderView::section {
            background: #f0dfc6;
            color: #6f4a11;
            border: none;
            border-bottom: 1px solid #dcc8a7;
            padding: 8px;
            font-weight: 700;
        }
        QCheckBox {
            spacing: 8px;
        }
        QLabel#heroTitle {
            color: #6d4711;
            font-size: 26px;
            font-weight: 800;
            padding: 6px 0;
        }
        QLabel#heroSubtitle {
            color: #7d6a54;
            font-size: 14px;
            padding-bottom: 4px;
        }
        QLabel#topBadge {
            color: #8a5a10;
            font-weight: 700;
            padding-right: 8px;
        }
    """,
    "ocean": """
        QMainWindow, QWidget {
            background: #edf4f7;
            color: #1d3340;
            font-family: "Microsoft YaHei UI", "Segoe UI";
            font-size: 13px;
        }
        QTabWidget::pane {
            border: 1px solid #bfd2db;
            border-radius: 18px;
            background: #f7fbfd;
            top: -1px;
        }
        QTabBar::tab {
            background: #d4e4ea;
            color: #28556b;
            border: 1px solid #c1d5dc;
            padding: 10px 18px;
            margin-right: 6px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        QTabBar::tab:selected {
            background: #ffffff;
            color: #0d5e7a;
            font-weight: 700;
        }
        QGroupBox {
            border: 1px solid #c9dbe2;
            border-radius: 16px;
            margin-top: 14px;
            padding: 18px 14px 14px 14px;
            background: #ffffff;
            font-weight: 700;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #0d5e7a;
        }
        QPushButton {
            background: #227c9d;
            color: #f5fcff;
            border: none;
            border-radius: 12px;
            padding: 9px 16px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #16637f;
        }
        QPushButton:pressed {
            background: #114f67;
        }
        QLineEdit, QComboBox, QListWidget, QTextEdit, QTableWidget {
            background: #ffffff;
            border: 1px solid #c7d9e0;
            border-radius: 12px;
            padding: 6px;
            selection-background-color: #2b8dad;
            selection-color: #ffffff;
        }
        QTableWidget {
            gridline-color: #dde8ec;
            alternate-background-color: #f2f8fa;
        }
        QHeaderView::section {
            background: #d9e9ef;
            color: #1f5168;
            border: none;
            border-bottom: 1px solid #c7d9e0;
            padding: 8px;
            font-weight: 700;
        }
        QLabel#heroTitle {
            color: #14536d;
            font-size: 26px;
            font-weight: 800;
            padding: 6px 0;
        }
        QLabel#heroSubtitle {
            color: #5b7785;
            font-size: 14px;
            padding-bottom: 4px;
        }
        QLabel#topBadge {
            color: #14536d;
            font-weight: 700;
            padding-right: 8px;
        }
    """,
    "graphite": """
        QMainWindow, QWidget {
            background: #1f2329;
            color: #e8ecf1;
            font-family: "Microsoft YaHei UI", "Segoe UI";
            font-size: 13px;
        }
        QTabWidget::pane {
            border: 1px solid #38414d;
            border-radius: 18px;
            background: #242b33;
            top: -1px;
        }
        QTabBar::tab {
            background: #313943;
            color: #cbd5e1;
            border: 1px solid #43505f;
            padding: 10px 18px;
            margin-right: 6px;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }
        QTabBar::tab:selected {
            background: #2d3640;
            color: #ffd48a;
            font-weight: 700;
        }
        QGroupBox {
            border: 1px solid #3c4652;
            border-radius: 16px;
            margin-top: 14px;
            padding: 18px 14px 14px 14px;
            background: #262e37;
            font-weight: 700;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 6px;
            color: #ffd48a;
        }
        QPushButton {
            background: #d18f35;
            color: #1f2329;
            border: none;
            border-radius: 12px;
            padding: 9px 16px;
            font-weight: 700;
        }
        QPushButton:hover {
            background: #e2a64e;
        }
        QPushButton:pressed {
            background: #b9781f;
        }
        QLineEdit, QComboBox, QListWidget, QTextEdit, QTableWidget {
            background: #20262d;
            border: 1px solid #465262;
            border-radius: 12px;
            padding: 6px;
            selection-background-color: #d18f35;
            selection-color: #12161b;
        }
        QTableWidget {
            gridline-color: #33404c;
            alternate-background-color: #252d36;
        }
        QHeaderView::section {
            background: #2d3640;
            color: #ffd48a;
            border: none;
            border-bottom: 1px solid #465262;
            padding: 8px;
            font-weight: 700;
        }
        QLabel#heroTitle {
            color: #ffd48a;
            font-size: 26px;
            font-weight: 800;
            padding: 6px 0;
        }
        QLabel#heroSubtitle {
            color: #9faab6;
            font-size: 14px;
            padding-bottom: 4px;
        }
        QLabel#topBadge {
            color: #ffd48a;
            font-weight: 700;
            padding-right: 8px;
        }
    """,
}

TERMINAL_DASHBOARD_STYLE = """
    QWidget#overviewRoot {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #121823, stop:0.42 #0d1219, stop:1 #101722);
    }
    QFrame#metricCard {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b2533, stop:1 #121a23);
        border: 1px solid rgba(120, 143, 168, 0.26);
        border-radius: 16px;
    }
    QLabel#metricCaption {
        color: #8ea0b6;
        font-size: 12px;
        font-weight: 600;
    }
    QLabel#metricValue {
        color: #f4f7fb;
        font-size: 24px;
        font-weight: 900;
    }
    QLabel#metricAccent {
        color: #ffd166;
        font-size: 12px;
        font-weight: 700;
    }
    QTableWidget#marketPoolTable {
        background: rgba(12, 16, 22, 0.96);
        border: 1px solid rgba(109, 128, 151, 0.20);
        border-radius: 18px;
        padding: 8px;
        selection-background-color: #182331;
        selection-color: #ffffff;
    }
    QTableWidget#marketPoolTable::item {
        padding: 7px;
        border-bottom: 1px solid rgba(28, 38, 50, 0.65);
    }
    QTableWidget#marketPoolTable QTableCornerButton::section {
        background: #11161d;
        border: none;
    }
    QChartView#marketChartPanel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b0e13, stop:1 #0f141b);
        border: 1px solid rgba(114, 132, 157, 0.22);
        border-radius: 16px;
    }
    QTextEdit#marketNotePanel {
        background: rgba(13, 18, 24, 0.94);
        border: 1px solid rgba(114, 132, 157, 0.18);
        border-radius: 16px;
        padding: 10px;
        color: #dce3eb;
    }
    QLabel#terminalSignal {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #131b22, stop:1 #10151b);
        color: #ffcf5b;
        border: 1px solid #384352;
        border-radius: 8px;
        padding: 8px 12px;
        font-weight: 700;
    }
"""

TERMINAL_WORKSPACE_STYLE = """
    QWidget#scannerRoot,
    QWidget#recommendRoot,
    QWidget#boardRoot,
    QWidget#authRoot,
    QWidget#detailRoot,
    QWidget#brokerRoot {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #171c24, stop:0.5 #121820, stop:1 #151c26);
    }
    QFrame#workspaceHero {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1b2634, stop:0.4 #141c26, stop:1 #0f151c);
        border: 1px solid rgba(121, 144, 168, 0.22);
        border-radius: 22px;
    }
    QLabel#workspaceEyebrow {
        color: #76a9ff;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    QLabel#workspaceTitle {
        color: #f6f8fb;
        font-size: 24px;
        font-weight: 900;
    }
    QLabel#workspaceSubtitle {
        color: #93a2b4;
        font-size: 13px;
    }
    QFrame#workspaceBadge {
        background: rgba(13, 20, 31, 0.92);
        border: 1px solid rgba(112, 132, 156, 0.18);
        border-radius: 16px;
    }
    QLabel#workspaceBadgeValue {
        color: #ffd166;
        font-size: 16px;
        font-weight: 900;
    }
    QLabel#workspaceBadgeCaption {
        color: #8392a6;
        font-size: 11px;
        font-weight: 600;
    }
    QGroupBox#terminalPanel {
        background: rgba(22, 30, 40, 0.96);
        border: 1px solid rgba(111, 130, 153, 0.18);
        border-radius: 18px;
        margin-top: 16px;
        padding: 18px 16px 14px 16px;
    }
    QGroupBox#terminalPanel::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #e5edf7;
        font-weight: 800;
    }
    QTableWidget#terminalTable {
        background: rgba(12, 17, 24, 0.97);
        border: 1px solid rgba(112, 130, 153, 0.16);
        border-radius: 16px;
        padding: 10px;
        selection-background-color: #172231;
        selection-color: #f8fbff;
    }
    QTableWidget#terminalTable QHeaderView::section {
        background: rgba(29, 39, 51, 0.92);
        color: #c9d6e4;
        border: none;
        border-bottom: 1px solid rgba(112, 130, 153, 0.15);
        padding: 10px 8px;
        font-weight: 800;
    }
    QTableWidget#terminalTable::item {
        padding: 8px 7px;
        border-bottom: 1px solid rgba(24, 32, 43, 0.85);
    }
    QListWidget#watchlistPanel {
        background: rgba(12, 17, 24, 0.97);
        border: 1px solid rgba(112, 130, 153, 0.16);
        border-radius: 16px;
        padding: 10px;
    }
    QListWidget#watchlistPanel::item {
        padding: 8px 10px;
        border-radius: 8px;
    }
    QListWidget#watchlistPanel::item:selected {
        background: #182231;
        color: #ffffff;
    }
    QTextEdit#terminalConsole {
        background: rgba(13, 18, 24, 0.96);
        border: 1px solid rgba(112, 130, 153, 0.16);
        border-radius: 16px;
        padding: 12px;
        color: #dfe7f1;
    }
    QLabel#inlineHint {
        color: #90a0b3;
        font-size: 12px;
    }
    QLineEdit#intervalInput {
        background: rgba(13, 18, 24, 0.96);
        border: 1px solid rgba(112, 130, 153, 0.22);
        border-radius: 12px;
        padding: 6px 8px;
    }
    QPushButton#ghostButton {
        background: #273140;
        color: #e6edf7;
        border: 1px solid #435167;
    }
    QPushButton#ghostButton:hover {
        background: #314052;
    }
    QPushButton#accentButton {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0aa4d, stop:1 #ffd166);
        color: #151b23;
        border: none;
    }
    QPushButton#accentButton:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f5b459, stop:1 #ffda73);
    }
    QSplitter::handle {
        background: transparent;
        width: 10px;
        height: 10px;
    }
    QSplitter::handle:horizontal {
        image: none;
        background: qlineargradient(x1:0.5, y1:0, x2:0.5, y2:1, stop:0 transparent, stop:0.2 rgba(255,255,255,0.02), stop:0.5 rgba(118, 140, 168, 0.22), stop:0.8 rgba(255,255,255,0.02), stop:1 transparent);
    }
    QSplitter::handle:vertical {
        image: none;
        background: qlineargradient(x1:0, y1:0.5, x2:1, y2:0.5, stop:0 transparent, stop:0.2 rgba(255,255,255,0.02), stop:0.5 rgba(118, 140, 168, 0.22), stop:0.8 rgba(255,255,255,0.02), stop:1 transparent);
    }
    QScrollBar:vertical, QScrollBar:horizontal {
        background: transparent;
        border: none;
        width: 0px;
        height: 0px;
        margin: 0px;
    }
    QScrollBar::handle:vertical, QScrollBar::handle:horizontal,
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
        background: transparent;
        border: none;
    }
"""


class OrderConfirmationDialog(QDialog):
    def __init__(
        self,
        profile: BrokerProfile,
        intents: list[OrderIntent],
        adapter: EastmoneyBrokerAdapter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("下单确认")
        self.resize(980, 560)

        layout = QVBoxLayout(self)

        env = adapter.diagnose_environment(profile)
        account_box = QGroupBox("账户核对")
        account_grid = QGridLayout(account_box)
        info_rows = [
            ("账户名称", profile.account_name or "-"),
            ("账户 ID", profile.account_id or "-"),
            ("策略 ID", profile.strategy_id or "-"),
            ("交易模式", DISPLAY_TEXT["mode"].get(profile.mode or "", profile.mode or "-")),
            ("桥接 Python", env.get("bridge_python") or "未配置"),
            ("SDK 模块", profile.sdk_module or "-"),
        ]
        for idx, (label, value) in enumerate(info_rows):
            row = idx // 2
            col = (idx % 2) * 2
            account_grid.addWidget(QLabel(f"{label}:"), row, col)
            account_grid.addWidget(QLabel(str(value)), row, col + 1)
        layout.addWidget(account_box)

        hint = QLabel(
            "请确认 account_id、token、strategy_id 以及桥接 Python 与实盘账户一致后再提交。"
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.order_table = build_table(
            [
                "代码",
                "方向",
                "价格",
                "数量",
                "止损",
                "目标",
                "信号日期",
            ]
        )
        self.order_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.order_table.setRowCount(len(intents))
        for row_index, item in enumerate(intents):
            values = [
                item.symbol,
                DISPLAY_TEXT["action"].get(item.side, item.side),
                f"{item.price:.3f}",
                str(item.quantity),
                f"{item.stop_price:.3f}",
                f"{item.target_price:.3f}",
                item.signal_date,
            ]
            for column, value in enumerate(values):
                self.order_table.setItem(row_index, column, QTableWidgetItem(value))
        layout.addWidget(self.order_table)

        footer = QHBoxLayout()
        self.confirm_checkbox = QCheckBox("我已核对账户与委托信息。")
        footer.addWidget(self.confirm_checkbox)
        footer.addStretch(1)
        self.submit_button = QPushButton("确认提交")
        self.submit_button.setEnabled(False)
        cancel_button = QPushButton("取消")
        footer.addWidget(self.submit_button)
        footer.addWidget(cancel_button)
        layout.addLayout(footer)

        self.confirm_checkbox.toggled.connect(self.submit_button.setEnabled)
        self.submit_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    @staticmethod
    def confirm(
        profile: BrokerProfile,
        intents: list[OrderIntent],
        adapter: EastmoneyBrokerAdapter,
        parent: QWidget | None = None,
    ) -> bool:
        dialog = OrderConfirmationDialog(profile, intents, adapter, parent)
        return dialog.exec() == QDialog.Accepted


def build_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setSelectionMode(QAbstractItemView.SingleSelection)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setAlternatingRowColors(False)
    table.setShowGrid(False)
    table.setObjectName("terminalTable")
    table.verticalHeader().setDefaultSectionSize(36)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setFrameShape(QFrame.NoFrame)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
    return table


class BackgroundTaskSignals(QObject):
    succeeded = Signal(object)
    failed = Signal(str)
    finished = Signal()


class BackgroundTask(QRunnable):
    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn
        self.signals = BackgroundTaskSignals()
        self.setAutoDelete(False)

    def run(self) -> None:
        try:
            result = self.fn()
        except Exception as exc:
            try:
                self.signals.failed.emit(str(exc))
            except RuntimeError:
                pass
        else:
            try:
                self.signals.succeeded.emit(result)
            except RuntimeError:
                pass
        finally:
            try:
                self.signals.finished.emit()
            except RuntimeError:
                pass


BACKGROUND_TASK_REGISTRY: list[BackgroundTask] = []




class QuantHunterWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("量化猎手")
        self.resize(1380, 880)
        self.setMinimumSize(1200, 760)

        self.state = load_app_state(STATE_FILE)
        self.current_theme = self.state.ui_theme or "graphite"

        self.scan_rows: list[ScanRow] = []
        self.backtest_summaries: list[SymbolBacktestSummary] = []
        self.optimization_results: list[OptimizationRun] = []
        self.universe_bars: dict[str, list[PriceBar]] = {}
        self.universe_analyses: dict[str, list[DailyAnalysis]] = {}
        self.paths_by_symbol: dict[str, Path] = {}
        self.stock_profiles: dict[str, StockProfile] = {}
        self.news_catalysts: dict[str, list] = {}
        self.daily_pool_rows: list[RecommendationRow] = []
        self.theme_heat_rows = []
        self.leader_candidates = []
        self.theme_aliases: dict[str, tuple[str, ...]] = {}
        self.theme_alias_path = self.state.theme_alias_path
        self.holdings: list[HoldingRecord] = []
        self.cash_snapshot: CashSnapshot | None = None
        self.order_intents: list[OrderIntent] = []
        self.order_submission_log: list[str] = []
        self.order_submission_records: list[dict[str, str]] = []
        self.monitor_alert_state: dict[str, str] = {}
        self.path_alert_state: dict[str, str] = {}
        self.market_path_alert_history: list[str] = []
        self.last_review_export_date = ""
        self.last_daily_plan_export_date = ""
        self.market_screen_result = MarketScreenResult(market_name="", generated_at="")
        self.market_snapshots = {}
        self.market_filter_tag = "全部"
        self.market_theme_filter = self.state.market_theme_filter or "全部"
        self.recommend_theme_filter = self.state.recommend_theme_filter or "全部"
        self.market_data_mode = self.state.market_data_mode or "auto"
        self.market_data_source = "unknown"
        self.last_market_success_at = ""
        self.last_market_error = ""
        self.active_symbol = ""
        self.bars: list[PriceBar] = []
        self.analyses: list[DailyAnalysis] = []

        self.strategy_inputs: dict[str, QLineEdit] = {}
        self.broker_inputs: dict[str, QLineEdit] = {}
        self.login_inputs: dict[str, QLineEdit] = {}
        self.config_inputs: dict[str, QLineEdit] = {}
        self.theme_label_map = dict(THEME_OPTIONS)
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(self.thread_pool.maxThreadCount(), 4))
        self.active_jobs: set[str] = set()
        self.job_handles: dict[str, BackgroundTask] = {}
        self.runtime_events: list[str] = []
        self.job_metrics: dict[str, dict[str, object]] = {}
        self.job_started_perf: dict[str, float] = {}
        self.job_run_count = 0
        self.job_success_count = 0
        self.job_failure_count = 0
        self.last_job_name = ""
        self.last_job_status = "idle"
        self.last_job_duration_ms = 0.0
        self.last_job_finished_at = ""
        self.last_runtime_export_path = ""
        self.last_cache_purge_summary = ""
        self.overview_focus_mode = "市场总览"
        self.market_timeframe_mode = "日线"

        if self.theme_alias_path:
            try:
                self.theme_aliases = load_theme_aliases_from_csv(self.theme_alias_path)
            except Exception:
                self.theme_aliases = {}
                self.theme_alias_path = ""

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.execute_refresh_cycle)

        self._build_ui()
        self._post_build_ui_tweaks()
        self._apply_dashboard_labels()
        self._refresh_watchlist()
        self._refresh_broker_status()

        if self.state.universe_dir and Path(self.state.universe_dir).exists():
            QTimer.singleShot(80, lambda: self._scan_universe(Path(self.state.universe_dir), quiet=True, async_mode=True))
        QTimer.singleShot(20, lambda: self.refresh_remote_market(quiet=True, update_chart=True, async_mode=True))

    def _build_ui(self) -> None:
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.overview_tab = QWidget()
        self.scanner_tab = QWidget()
        self.recommend_tab = QWidget()
        self.board_tab = QWidget()
        self.config_tab = QWidget()
        self.auth_tab = QWidget()
        self.detail_tab = QWidget()
        self.broker_tab = QWidget()

        self.tabs.addTab(self.overview_tab, "总览")
        self.tabs.addTab(self.scanner_tab, "扫描")
        self.tabs.addTab(self.recommend_tab, "推荐")
        self.tabs.addTab(self.board_tab, "打板")
        self.tabs.addTab(self.config_tab, "配置")
        self.tabs.addTab(self.auth_tab, "登录")
        self.tabs.addTab(self.detail_tab, "明细")
        self.tabs.addTab(self.broker_tab, "交易")

        corner_widget = QWidget()
        corner_layout = QHBoxLayout(corner_widget)
        corner_layout.setContentsMargins(0, 0, 0, 0)
        self.top_badge = QLabel("中文界面")
        self.top_badge.setObjectName("topBadge")
        self.theme_title_label = QLabel("主题")
        self.theme_combo = QComboBox()
        for key, label in THEME_OPTIONS:
            self.theme_combo.addItem(label, key)
        corner_layout.addWidget(self.top_badge)
        corner_layout.addWidget(self.theme_title_label)
        corner_layout.addWidget(self.theme_combo)
        self.tabs.setCornerWidget(corner_widget, Qt.TopRightCorner)
        self.tabs.currentChanged.connect(self._on_workspace_tab_changed)

        self._build_overview_tab()
        self._build_scanner_tab()
        self._build_recommend_tab()
        self._build_board_tab()
        self._build_config_tab()
        self._build_auth_tab()
        self._build_detail_tab()
        self._build_broker_tab()
        self._configure_market_tables()
        self._set_theme_combo_value(self.current_theme)
        self.theme_combo.currentIndexChanged.connect(self.change_theme)
        self._apply_theme(self.current_theme)
        self._finalize_workspace_ux()
        self.tabs.setCurrentIndex(0)

    def _build_workspace_hero(
        self,
        eyebrow: str,
        title: str,
        subtitle: str,
        badges: list[tuple[str, str]] | None = None,
    ) -> QFrame:
        return build_workspace_hero(eyebrow, title, subtitle, badges)

    def _build_workspace_badge(self, value: str, caption: str) -> QFrame:
        return build_workspace_badge(value, caption)

    def _set_button_role(self, button: QPushButton, role: str = "ghost") -> None:
        set_button_role(button, role)

    def _style_terminal_panel(self, *boxes: QGroupBox) -> None:
        style_terminal_panel(*boxes)

    def _style_terminal_console(self, *widgets: QTextEdit) -> None:
        style_terminal_console(*widgets)

    def _enable_smooth_scroll(self, widget: QWidget, allow_drag: bool = True) -> None:
        if hasattr(widget, "setVerticalScrollBarPolicy"):
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if hasattr(widget, "setHorizontalScrollBarPolicy"):
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        if hasattr(widget, "setFrameShape"):
            widget.setFrameShape(QFrame.NoFrame)
        if hasattr(widget, "setVerticalScrollMode"):
            widget.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        if hasattr(widget, "setHorizontalScrollMode"):
            widget.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        target = widget.viewport() if hasattr(widget, "viewport") else widget
        if allow_drag:
            QScroller.grabGesture(target, QScroller.LeftMouseButtonGesture)

    def _configure_splitter(self, splitter: QSplitter, sizes: list[int] | None = None) -> None:
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(10)
        splitter.setOpaqueResize(False)
        if sizes:
            splitter.setSizes(sizes)

    def _finalize_workspace_ux(self) -> None:
        for table in self.findChildren(QTableWidget):
            self._enable_smooth_scroll(table)
            table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 38))
        for console in self.findChildren(QTextEdit):
            self._enable_smooth_scroll(console)
        for watchlist in self.findChildren(QListWidget):
            self._enable_smooth_scroll(watchlist)
        for splitter in self.findChildren(QSplitter):
            self._configure_splitter(splitter)

    def _append_runtime_log(self, message: str, level: str = "INFO") -> None:
        append_runtime_log_runtime(self, message, datetime_cls=datetime, level=level)

    def _current_strategy_runtime_config(self) -> tuple[int, float, bool]:
        try:
            top_theme_limit = int(self.config_inputs.get("top_theme_limit", QLineEdit("3")).text().strip())
        except ValueError:
            top_theme_limit = self.state.strategy_top_theme_limit
        try:
            max_total_exposure = float(self.config_inputs.get("max_total_exposure", QLineEdit("0.85")).text().strip())
        except ValueError:
            max_total_exposure = self.state.strategy_max_total_exposure
        return max(top_theme_limit, 1), max(min(max_total_exposure, 1.0), 0.1), self.theme_drop_reduce_checkbox.isChecked() if hasattr(self, "theme_drop_reduce_checkbox") else self.state.strategy_theme_drop_reduce

    def _current_report_template_config(self) -> tuple[str, bool, int]:
        template_name = "balanced"
        if hasattr(self, "daily_plan_template_combo"):
            template_name = str(self.daily_plan_template_combo.currentData() or "balanced")
        focus_only = self.daily_plan_focus_only_checkbox.isChecked() if hasattr(self, "daily_plan_focus_only_checkbox") else False
        try:
            candidate_limit = int(self.config_inputs.get("daily_plan_candidate_limit", QLineEdit("10")).text().strip())
        except ValueError:
            candidate_limit = self.state.daily_plan_candidate_limit
        return template_name, focus_only, max(candidate_limit, 1)

    def _build_config_tab(self) -> None:
        build_config_workspace(self)

    def _parse_focus_themes(self) -> list[str]:
        if not hasattr(self, "focus_themes_input"):
            return list(self.state.focus_themes)
        return [item.strip() for item in self.focus_themes_input.text().replace("，", ",").split(",") if item.strip()]

    def save_strategy_preferences(self) -> None:
        save_strategy_preferences_controller(self, info_dialog_fn=QMessageBox.information)

    def _refresh_license_status_view(self) -> None:
        refresh_license_status_view(self, datetime_cls=datetime)

    def activate_professional_plan(self) -> None:
        self.state.license_plan = "PRO"
        self.save_state()
        self._refresh_license_status_view()

    def reset_trial_plan(self) -> None:
        self.state.license_plan = "TRIAL"
        self.state.trial_started_at = datetime.now().date().isoformat()
        self.save_state()
        self._refresh_license_status_view()

    def activate_enterprise_plan(self) -> None:
        self.state.license_plan = "ENTERPRISE"
        self.save_state()
        self._refresh_license_status_view()

    def _license_capabilities(self) -> dict[str, object]:
        plan = (self.state.license_plan or "TRIAL").upper()
        if plan == "ENTERPRISE":
            return {
                "plan": plan,
                "auto_daily_plan_export": True,
                "focus_theme_boost": 7.0,
                "theme_panel_size": 12,
                "daily_plan_export_limit": 20,
                "market_history_limit": 18,
                "monitor_summary_limit": 6,
                "plan_label": "企业版",
            }
        if plan == "PRO":
            return {
                "plan": plan,
                "auto_daily_plan_export": True,
                "focus_theme_boost": 4.0,
                "theme_panel_size": 8,
                "daily_plan_export_limit": 12,
                "market_history_limit": 12,
                "monitor_summary_limit": 4,
                "plan_label": "专业版",
            }
        return {
            "plan": "TRIAL",
            "auto_daily_plan_export": False,
            "focus_theme_boost": 2.0,
            "theme_panel_size": 6,
            "daily_plan_export_limit": 6,
            "market_history_limit": 8,
            "monitor_summary_limit": 3,
            "plan_label": "试用版",
        }

    def _configure_market_tables(self) -> None:
        if hasattr(self, "scan_table"):
            self.scan_table.setColumnCount(11)
            self.scan_table.setHorizontalHeaderLabels(
                ["股票名称", "股票ID", "交易代码", "动作", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"]
            )
        if hasattr(self, "summary_table"):
            self.summary_table.setColumnCount(8)
            self.summary_table.setHorizontalHeaderLabels(
                ["股票名称", "股票ID", "交易代码", "交易数", "收益率", "回撤", "胜率", "期末权益"]
            )
        if hasattr(self, "monitor_table"):
            self.monitor_table.setColumnCount(9)
            self.monitor_table.setHorizontalHeaderLabels(
                ["股票名称", "股票ID", "交易代码", "动作", "信号", "评分", "收盘价", "信号日期", "更新时间"]
            )


    def strategy_params(self) -> StrategyParams:
        return StrategyParams.from_mapping({key: widget.text().strip() for key, widget in self.strategy_inputs.items()})

    def current_broker_profile(self) -> BrokerProfile:
        return BrokerProfile(
            account_name=self.broker_inputs["account_name"].text().strip() or "东方财富账户",
            account_id=self.broker_inputs["account_id"].text().strip(),
            mode=str(self.mode_combo.currentData() or "export"),
            export_dir=self.broker_inputs["export_dir"].text().strip(),
            sdk_module=self.broker_inputs["sdk_module"].text().strip() or "gm.api",
            sdk_python_path=self.broker_inputs["sdk_python_path"].text().strip(),
            token=self.broker_inputs["token"].text().strip(),
            strategy_id=self.broker_inputs["strategy_id"].text().strip(),
            username=self.login_inputs["username"].text().strip() if "username" in self.login_inputs else "",
            password=self.login_inputs["password"].text().strip() if "password" in self.login_inputs else "",
            auth_channel=str(self.auth_channel_combo.currentData() or "eastmoney") if hasattr(self, "auth_channel_combo") else "eastmoney",
        )

    def save_login_profile(self) -> None:
        self.state.broker_profile = self.current_broker_profile()
        self.save_state()
        self._refresh_login_status()
        self._refresh_broker_status(extra="登录配置已更新。")
        QMessageBox.information(self, "提示", "登录配置已保存。")

    def _refresh_login_status(self) -> None:
        if not hasattr(self, "login_status_text"):
            return
        profile = self.current_broker_profile() if "account_name" in self.broker_inputs else self.state.broker_profile
        channel_text = self.auth_channel_combo.currentText() if hasattr(self, "auth_channel_combo") else "东方财富"
        lines = [
            "登录与渠道说明",
            f"- 当前渠道：{channel_text}",
            f"- 登录账号：{profile.username or '未填写'}",
            f"- 账户 ID：{profile.account_id or '未填写'}",
            f"- SDK Token：{'已填写' if profile.token else '未填写'}",
            "",
            "安全边界",
            "- 本程序只保存和展示配置，不会绕过券商安全校验。",
            "- 真实下单仍通过 GM SDK / 桥接脚本，并保留人工确认。",
            "- 后续如果增加新渠道，可以在这里继续扩展。",
        ]
        self.login_status_text.setPlainText("\n".join(lines))

    def import_stock_profiles_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择股票资料 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        try:
            self.stock_profiles = load_stock_profiles_from_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "导入股票资料失败", str(exc))
            return
        self.recommend_status_label.setText(f"已导入股票资料：{len(self.stock_profiles)} 条")
        self._fill_scan_rows()
        self._fill_backtest_summaries()
        self._refresh_intraday_monitor()
        self.refresh_daily_pool()

    def import_news_catalysts_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择消息面 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        try:
            self.news_catalysts = load_news_catalysts_from_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "导入消息面失败", str(exc))
            return
        self.recommend_status_label.setText(f"已导入消息面：{sum(len(items) for items in self.news_catalysts.values())} 条")
        self.refresh_daily_pool()

    def import_theme_aliases_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择题材词典 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        try:
            self.theme_aliases = load_theme_aliases_from_csv(path)
        except Exception as exc:
            QMessageBox.critical(self, "导入题材词典失败", str(exc))
            return
        self.theme_alias_path = path
        self.recommend_status_label.setText(f"已导入题材词典：{len(self.theme_aliases)} 个主题。")
        self.save_state()
        self.refresh_daily_pool()

    def open_theme_alias_editor(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑题材词典")
        dialog.resize(760, 540)
        layout = QVBoxLayout(dialog)

        intro = QLabel("按 CSV 形式编辑题材词典：`theme_name,keywords`。关键词用英文逗号分隔。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        editor = QTextEdit(dialog)
        editor.setPlainText(self._theme_aliases_to_csv_text())
        layout.addWidget(editor, stretch=1)

        button_row = QHBoxLayout()
        save_button = QPushButton("保存词典")
        cancel_button = QPushButton("取消")
        self._set_button_role(save_button, "accent")
        self._set_button_role(cancel_button, "ghost")
        button_row.addStretch(1)
        button_row.addWidget(save_button)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        save_button.clicked.connect(lambda: self._save_theme_aliases_from_editor(dialog, editor.toPlainText()))
        cancel_button.clicked.connect(dialog.reject)
        dialog.exec()

    def _theme_aliases_to_csv_text(self) -> str:
        mapping = self.theme_aliases or {}
        if not mapping:
            mapping = {
                "银行": ("银行", "金融", "信贷"),
                "半导体": ("芯片", "半导体", "算力"),
            }
        lines = ["theme_name,keywords"]
        for theme_name, keywords in mapping.items():
            joined = ",".join(keywords)
            lines.append(f'{theme_name},"{joined}"')
        return "\n".join(lines)

    def _save_theme_aliases_from_editor(self, dialog: QDialog, text: str) -> None:
        target_path = Path(self.theme_alias_path) if self.theme_alias_path else (PROJECT_ROOT / ".quant_hunter" / "theme_aliases.csv")
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(text.strip() + "\n", encoding="utf-8-sig")
            self.theme_aliases = load_theme_aliases_from_csv(target_path)
        except Exception as exc:
            QMessageBox.critical(self, "保存题材词典失败", str(exc))
            return
        self.theme_alias_path = str(target_path)
        self.recommend_status_label.setText(f"已保存题材词典：{len(self.theme_aliases)} 个主题。")
        self.save_state()
        self.refresh_daily_pool()
        dialog.accept()

    def load_sample_reference_data(self) -> None:
        profile_path = SAMPLE_DIR / "stock_profiles.csv"
        news_path = SAMPLE_DIR / "news_catalysts.csv"
        theme_path = SAMPLE_DIR / "theme_aliases.csv"
        loaded_parts: list[str] = []
        if profile_path.exists():
            self.stock_profiles = load_stock_profiles_from_csv(profile_path)
            loaded_parts.append(f"股票资料 {len(self.stock_profiles)} 条")
        if news_path.exists():
            self.news_catalysts = load_news_catalysts_from_csv(news_path)
            loaded_parts.append(f"消息面 {sum(len(items) for items in self.news_catalysts.values())} 条")
        if theme_path.exists():
            self.theme_aliases = load_theme_aliases_from_csv(theme_path)
            self.theme_alias_path = str(theme_path)
            loaded_parts.append(f"题材词典 {len(self.theme_aliases)} 个主题")
        if not loaded_parts:
            QMessageBox.information(self, "提示", "示例资料尚未生成。")
            return
        self.recommend_status_label.setText("已载入示例资料：" + "，".join(loaded_parts))
        self._fill_scan_rows()
        self._fill_backtest_summaries()
        self._refresh_intraday_monitor()
        self.refresh_daily_pool()


    def _refresh_trade_plan(self) -> None:
        if not hasattr(self, "trade_plan_table"):
            return
        available_cash = self.cash_snapshot.available_cash if self.cash_snapshot else 0.0
        plan = DecisionEngine().build_plan(
            self.daily_pool_rows,
            self.holdings,
            available_cash,
            max_picks=5,
            top_theme_limit=self.state.strategy_top_theme_limit,
            max_total_exposure=self.state.strategy_max_total_exposure,
            theme_drop_reduce=self.state.strategy_theme_drop_reduce,
        )
        self.current_trade_plan = plan
        self._emit_market_path_alerts(plan)
        self.trade_plan_table.setRowCount(len(plan.decisions))
        for row_index, item in enumerate(plan.decisions):
            values = [
                item.stock_name,
                item.stock_id,
                item.symbol,
                self._display_action(item.action),
                f"{item.confidence:.0%}",
                f"{item.planned_entry:.2f}",
                f"{item.planned_stop:.2f}",
                f"{item.planned_target:.2f}",
                f"{item.suggested_budget:,.0f}",
                item.rationale,
            ]
            for column, value in enumerate(values):
                self.trade_plan_table.setItem(row_index, column, QTableWidgetItem(value))
        self._refresh_action_flow_cards(plan)
        self._refresh_priority_cards(plan)
        self._refresh_recommend_summary_cards(plan)
        if hasattr(self, "trade_plan_text"):
            capabilities = self._license_capabilities()
            lines = [
                f"市场温度：{plan.market_sentiment} ({plan.sentiment_score:.1f})",
                f"市场周期：{plan.market_pulse.market_regime} | 风险等级：{plan.market_pulse.risk_level}",
                f"建议总仓位上限：{plan.market_pulse.max_total_exposure:.0%}",
                f"建议最多新开仓：{plan.max_new_positions} 只",
                f"报告模板：{self.state.daily_plan_template} | 展示上限：{min(self.state.daily_plan_candidate_limit, int(capabilities['daily_plan_export_limit']))}",
                "",
            ]
            if self.state.focus_themes:
                lines.append(f"关注题材：{', '.join(self.state.focus_themes)}")
                lines.append("")
            lines.extend(f"- {note}" for note in plan.notes)
            self.trade_plan_text.setPlainText("\n".join(lines))
        if hasattr(self, "market_pulse_text"):
            pulse = plan.market_pulse
            self.market_pulse_text.setPlainText(
                "\n".join(
                    [
                        f"市场温度：{pulse.sentiment_label}",
                        f"情绪分数：{pulse.sentiment_score:.1f}",
                        f"市场周期：{pulse.market_regime}",
                        f"风险等级：{pulse.risk_level}",
                        f"总仓位上限：{pulse.max_total_exposure:.0%}",
                        f"买入占比：{pulse.buy_ratio:.0%}",
                        f"候选均分：{pulse.average_total_score:.1f}",
                        f"强势候选数：{pulse.strong_candidates}",
                        f"风险提示候选数：{pulse.caution_candidates}",
                    ]
                )
            )
        if hasattr(self, "position_advice_table"):
            self.current_position_advice = list(plan.position_advice)
            self.position_advice_table.setRowCount(len(plan.position_advice))
            for row_index, item in enumerate(plan.position_advice):
                values = [
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    self._display_action(item.action),
                    f"{item.confidence:.0%}",
                    f"{item.current_price:.2f}",
                    f"{item.cost_price:.2f}",
                    f"{item.pnl_pct:.2%}",
                    item.rationale,
                ]
                for column, value in enumerate(values):
                    self.position_advice_table.setItem(row_index, column, QTableWidgetItem(value))
        if hasattr(self, "position_advice_text"):
            if plan.position_advice:
                sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")
                reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
                hold_count = sum(1 for item in plan.position_advice if item.action == "HOLD")
                self.position_advice_text.setPlainText(
                    "\n".join(
                        [
                            f"持仓处置概览：卖出 {sell_count} 只，减仓 {reduce_count} 只，继续持有 {hold_count} 只。",
                            "说明：出现诱多陷阱、跌破防守位或高位浮盈回落时，会优先给出减仓/卖出建议。",
                        ]
                    )
                )
            else:
                self.position_advice_text.setPlainText("当前没有持仓数据，导入持仓 CSV 后会显示卖出 / 格局建议。")

    def _refresh_recommend_summary_cards(self, plan) -> None:
        refresh_recommend_summary_cards(self, plan)

    def _push_market_path_alert(self, key: str, status: str, detail: str) -> None:
        history_line = f"{status}：{detail}"
        self.market_path_alert_history.append(history_line)
        self.market_path_alert_history = self.market_path_alert_history[-12:]
        if hasattr(self, "alert_cards") and key in self.alert_cards:
            self.alert_cards[key].set_data(status, detail)

    def _refresh_alert_cards_from_state(self) -> None:
        if not hasattr(self, "alert_cards"):
            return
        fallback_map = {
            "theme": ("主线稳定", "等待主线题材发生变化后更新提醒。"),
            "leader": ("龙头稳定", "等待龙头焦点发生变化后更新提醒。"),
            "strategy": ("策略稳定", "等待高优先策略切换后更新提醒。"),
            "action": ("动作稳定", "等待交易动作切换后更新提醒。"),
        }
        latest = getattr(self, "path_alert_state", {})
        for key, card in self.alert_cards.items():
            status = latest.get(f"{key}_status")
            detail = latest.get(f"{key}_detail")
            if status and detail:
                card.set_data(status, detail)
            else:
                card.set_data(*fallback_map[key])

    def _emit_market_path_alerts(self, plan) -> None:
        top_theme = self.theme_heat_rows[0].theme_name if getattr(self, "theme_heat_rows", None) else ""
        top_pick = self.daily_pool_rows[0].stock_name if self.daily_pool_rows else ""
        top_action = plan.decisions[0].action if plan.decisions else ""
        top_strategy = getattr(self.daily_pool_rows[0], "primary_strategy", "") if self.daily_pool_rows else ""
        current_state = {
            "top_theme": top_theme,
            "top_pick": top_pick,
            "top_action": top_action,
            "top_strategy": top_strategy,
        }
        previous = dict(getattr(self, "path_alert_state", {}))
        if previous.get("top_theme") and previous.get("top_theme") != top_theme:
            detail = f"{previous.get('top_theme')} -> {top_theme}"
            self._append_runtime_log(f"主线题材切换：{detail}")
            current_state["theme_status"] = "主线切换"
            current_state["theme_detail"] = detail
        if previous.get("top_pick") and previous.get("top_pick") != top_pick:
            detail = f"{previous.get('top_pick')} -> {top_pick}"
            self._append_runtime_log(f"龙头焦点切换：{detail}")
            current_state["leader_status"] = "龙头切换"
            current_state["leader_detail"] = detail
        if previous.get("top_action") and previous.get("top_action") != top_action:
            detail = f"{previous.get('top_action')} -> {top_action}"
            self._append_runtime_log(f"动作优先级切换：{detail}")
            current_state["action_status"] = "动作切换"
            current_state["action_detail"] = detail
        if previous.get("top_strategy") and previous.get("top_strategy") != top_strategy:
            detail = f"{previous.get('top_strategy')} -> {top_strategy}"
            self._append_runtime_log(f"高优先策略切换：{detail}")
            current_state["strategy_status"] = "策略切换"
            current_state["strategy_detail"] = detail

        current_state.setdefault("theme_status", "主线稳定")
        current_state.setdefault("theme_detail", top_theme or "等待主线题材生成。")
        current_state.setdefault("leader_status", "龙头稳定")
        current_state.setdefault("leader_detail", top_pick or "等待龙头焦点生成。")
        current_state.setdefault("strategy_status", "策略稳定")
        current_state.setdefault("strategy_detail", top_strategy or "等待高优先策略生成。")
        current_state.setdefault("action_status", "动作稳定")
        current_state.setdefault("action_detail", self._display_action(top_action) if top_action else "等待交易动作生成。")

        self.path_alert_state = current_state
        for key in ["theme", "leader", "strategy", "action"]:
            self._push_market_path_alert(
                key,
                current_state[f"{key}_status"],
                current_state[f"{key}_detail"],
            )

    def _refresh_action_flow_cards(self, plan) -> None:
        refresh_action_flow_cards(self, plan)

    def _refresh_priority_cards(self, plan) -> None:
        refresh_priority_cards(self, plan)

    def _refresh_strategy_path_panel(self, plan, top_theme, top_strategy_name, top_pick) -> None:
        refresh_strategy_path_panel(self, plan, top_theme, top_strategy_name, top_pick)

    def toggle_auto_refresh(self, checked: bool) -> None:
        if checked:
            self.execute_refresh_cycle()
            self.refresh_timer.start(self._refresh_interval_ms())
        else:
            self.refresh_timer.stop()


    def _refresh_overview_priority_cards(self, pool: list, recommendations: list, top_theme: str) -> None:
        refresh_overview_priority_cards(self, pool, recommendations, top_theme)

    def _fill_scan_rows(self) -> None:
        fill_scan_rows(self)

    def _fill_backtest_summaries(self) -> None:
        fill_backtest_summaries(self)

    def _refresh_intraday_monitor(self) -> None:
        refresh_intraday_monitor(self)

    def add_selected_to_watchlist(self) -> None:
        symbol = self._selected_symbol_from_scan()
        if not symbol:
            QMessageBox.information(self, "提示", "请先从扫描结果中选择一只股票。")
            return
        if symbol not in self.state.watchlist:
            self.state.watchlist.append(symbol)
            self.state.watchlist.sort()
            self._refresh_watchlist()
            self.save_state()

    def remove_selected_from_watchlist(self) -> None:
        symbol = self._selected_symbol_from_scan() or self._selected_symbol_from_watchlist()
        if not symbol:
            return
        self.state.watchlist = [item for item in self.state.watchlist if item != symbol]
        self._refresh_watchlist()
        self.save_state()

    def _refresh_watchlist(self) -> None:
        refresh_watchlist(self)

    def on_scan_selected(self) -> None:
        symbol = self._selected_symbol_from_scan()
        if symbol:
            self.select_symbol(symbol)

    def on_watchlist_selected(self) -> None:
        symbol = self._selected_symbol_from_watchlist()
        if symbol and symbol in self.universe_bars:
            self.select_symbol(symbol)

    def _selected_symbol_from_scan(self) -> str:
        row = self.scan_table.currentRow()
        if row < 0:
            return ""
        item = self.scan_table.item(row, 2)
        return item.text() if item else ""

    def _selected_symbol_from_watchlist(self) -> str:
        item = self.watchlist_widget.currentItem()
        return item.text() if item else ""


    def load_single_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择行情 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        bars = load_bars_from_csv(path)
        analyses = AntiHarvestStrategy(self.strategy_params()).analyze(bars)
        symbol = bars[-1].symbol
        self.universe_bars[symbol] = bars
        self.universe_analyses[symbol] = analyses
        self.paths_by_symbol[symbol] = Path(path)
        self.select_symbol(symbol)

    def _refresh_signal_panel(self) -> None:
        rows = [row for row in self.analyses if row.label != "NONE"][-20:]
        self.signal_table.setRowCount(len(rows))
        for row_index, item in enumerate(rows):
            values = [item.date, self._display_label(item.label), str(item.score), f"{item.close:.2f}", item.reason]
            for column, value in enumerate(values):
                self.signal_table.setItem(row_index, column, QTableWidgetItem(value))

    def run_backtest_for_active(self, quiet: bool = False) -> None:
        if not self.bars or not self.analyses:
            if not quiet:
                QMessageBox.information(self, "提示", "请先选择一个标的。")
            return
        result = Backtester(strategy_params=self.strategy_params()).run(self.bars, self.analyses)
        latest_signal = next((item for item in reversed(self.analyses) if item.label != "NONE"), None)
        if latest_signal is None:
            latest_note = "最近 K 线中暂无有效信号。"
        else:
            latest_note = (
                f"最新信号：{latest_signal.date} | {self._display_label(latest_signal.label)} | 评分 {latest_signal.score}\n"
                f"{latest_signal.reason}"
            )
        source_path = self.paths_by_symbol.get(self.active_symbol)
        self.metrics_text.setPlainText(
            (
                f"{latest_note}\n"
                f"数据文件：{source_path}\n\n"
                f"{format_result(result)}\n\n"
                "说明：\n"
                "- 回测默认采用下一交易日开盘附近成交的日线近似。\n"
                "- 适合做研究、排序和半自动执行前检查。\n"
            )
        )
        self.trades_table.setRowCount(len(result.trades))
        for row_index, trade in enumerate(result.trades):
            values = [
                trade.entry_date,
                trade.exit_date,
                str(trade.entry_price),
                str(trade.exit_price),
                str(trade.shares),
                str(trade.pnl),
                trade.exit_reason,
            ]
            for column, value in enumerate(values):
                self.trades_table.setItem(row_index, column, QTableWidgetItem(value))


    def export_workspace_report_from_ui(self) -> None:
        if not self.scan_rows:
            QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return
        artifacts = export_workspace_report(self.scan_rows, self.backtest_summaries, REPORT_DIR)
        self.optimization_text.setPlainText(
            "\n".join(
                [
                    "工作台报告已导出。",
                    f"Markdown：{artifacts.markdown_path}",
                    f"CSV：{artifacts.csv_path}",
                    f"JSON：{artifacts.json_path}",
                ]
            )
        )

    def choose_export_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if folder:
            self.broker_inputs["export_dir"].setText(folder)

    def save_profile(self) -> None:
        self.state.broker_profile = self.current_broker_profile()
        self.save_state()
        self._refresh_broker_status()
        QMessageBox.information(self, "提示", "账户配置已保存。")

    def create_broker_templates(self) -> None:
        files = EastmoneyBrokerAdapter().create_templates(self.current_broker_profile().export_dir)
        self._refresh_broker_status(extra="\n".join(f"已生成模板：{item}" for item in files))

    def import_holdings_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择持仓 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        self.holdings = load_holdings_from_csv(path)
        self._fill_holdings()

    def import_cash_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "选择资金 CSV", str(PROJECT_ROOT), "CSV 文件 (*.csv);;所有文件 (*)")
        if not path:
            return
        self.cash_snapshot = load_cash_snapshot_from_csv(path)
        self._refresh_broker_status()

    def _fill_holdings(self) -> None:
        self.holdings_table.setRowCount(len(self.holdings))
        for row_index, item in enumerate(self.holdings):
            values = [
                item.symbol,
                str(item.quantity),
                str(item.available),
                f"{item.cost_price:.2f}",
                f"{item.market_value:,.2f}",
            ]
            for column, value in enumerate(values):
                self.holdings_table.setItem(row_index, column, QTableWidgetItem(value))
        self._refresh_broker_status()

    def generate_order_suggestions(self) -> None:
        if not self.scan_rows:
            QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return
        try:
            per_trade_budget = float(self.per_trade_budget_input.text().strip())
        except ValueError:
            QMessageBox.critical(self, "参数错误", "单笔预算必须填写数字。")
            return
        rows = self.scan_rows if not self.state.watchlist else [row for row in self.scan_rows if row.symbol in self.state.watchlist]
        self.order_intents = EastmoneyBrokerAdapter().build_order_intents(rows, per_trade_budget)
        self._fill_orders()
        if not self.order_intents:
            self._refresh_broker_status(extra="当前参数下暂无新的买入建议。")

    def _fill_orders(self) -> None:
        self.orders_table.setRowCount(len(self.order_intents))
        for row_index, item in enumerate(self.order_intents):
            values = [
                item.symbol,
                self._display_action(item.side),
                f"{item.price:.2f}",
                str(item.quantity),
                f"{item.stop_price:.2f}",
                f"{item.target_price:.2f}",
                item.signal_date,
            ]
            for column, value in enumerate(values):
                self.orders_table.setItem(row_index, column, QTableWidgetItem(value))
        self._refresh_broker_status()

    def export_order_plan(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        output = EastmoneyBrokerAdapter().export_order_plan(self.order_intents, self.current_broker_profile().export_dir)
        self._append_order_result(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已导出委托计划：{output}")
        self._refresh_broker_status(extra=f"已导出委托计划：{output}")

    def export_order_result_log(self) -> None:
        if not self.order_submission_records:
            QMessageBox.information(self, "提示", "当前还没有可导出的提交记录。")
            return
        output = EastmoneyBrokerAdapter().export_submission_records(
            self.order_submission_records,
            self.current_broker_profile().export_dir,
        )
        self._append_order_result(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 已导出提交日志：{output}")
        self._refresh_broker_status(extra=f"已导出提交日志：{output}")

    def sync_broker_via_sdk(self, quiet: bool = False) -> None:
        profile = self.current_broker_profile()
        try:
            cash, holdings = EastmoneyBrokerAdapter().sync_account_via_sdk(profile)
        except Exception as exc:
            if not quiet:
                QMessageBox.critical(self, "SDK 同步失败", str(exc))
            return
        self.cash_snapshot = cash
        self.holdings = holdings
        self._fill_holdings()
        self._refresh_broker_status(extra="已通过 SDK 同步资金和持仓。")

    def generate_sdk_strategy_script(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        profile = self.current_broker_profile()
        if not profile.token or not profile.strategy_id or not profile.account_id:
            QMessageBox.critical(self, "字段缺失", "请先填写 token、strategy_id 和 account_id。")
            return
        path = EastmoneyBrokerAdapter().generate_gm_strategy_script(profile, self.order_intents, profile.export_dir)
        self._refresh_broker_status(extra=f"已生成 GM 实盘脚本：{path}")

    def confirm_and_submit_orders(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        profile = self.current_broker_profile()
        adapter = EastmoneyBrokerAdapter()
        if not OrderConfirmationDialog.confirm(profile, self.order_intents, adapter, self):
            return

        submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            results = adapter.submit_order_intents(profile, self.order_intents)
        except Exception as exc:
            fallback_path = adapter.export_order_plan(self.order_intents, profile.export_dir)
            failure_lines = [
                f"[{submit_time}] SDK 下单失败：{exc}",
                f"[{submit_time}] 已回退导出 CSV：{fallback_path}",
            ]
            for item in self.order_intents:
                self._append_submission_record(
                    timestamp=submit_time,
                    order_status="FAILED",
                    fill_status="REJECTED",
                    symbol=item.symbol,
                    side=item.side,
                    price=f"{item.price:.3f}",
                    quantity=str(item.quantity),
                    failure_reason=str(exc),
                    message=str(exc),
                )
            for line in failure_lines:
                self._append_order_result(line)
            self._refresh_broker_status(extra="\n".join(failure_lines))
            QMessageBox.warning(self, "下单失败", f"{exc}\n\n已回退导出 CSV：\n{fallback_path}")
            return

        success_lines = [f"[{submit_time}] SDK 下单完成：共 {len(results)} 笔"]
        success_lines.extend(f"[{submit_time}] {item}" for item in results)
        for item, result in zip(self.order_intents, results):
            self._append_submission_record(
                timestamp=submit_time,
                order_status="SUBMITTED",
                fill_status="PENDING",
                symbol=item.symbol,
                side=item.side,
                price=f"{item.price:.3f}",
                quantity=str(item.quantity),
                failure_reason="",
                message=result,
            )
        for line in success_lines:
            self._append_order_result(line)
        self.sync_broker_via_sdk(quiet=True)
        self._refresh_broker_status(extra="\n".join(success_lines))
        QMessageBox.information(self, "下单完成", "\n".join(results))

    def _append_order_result(self, line: str) -> None:
        self.order_submission_log.append(line.rstrip())
        self.order_submission_log = self.order_submission_log[-200:]
        self.order_result_text.setPlainText("\n".join(self.order_submission_log) + "\n")

    def _append_submission_record(
        self,
        timestamp: str,
        order_status: str,
        fill_status: str,
        symbol: str,
        side: str,
        price: str,
        quantity: str,
        failure_reason: str,
        message: str,
    ) -> None:
        self.order_submission_records.append(
            {
                "timestamp": timestamp,
                "order_status": order_status,
                "fill_status": fill_status,
                "symbol": symbol,
                "side": side,
                "price": price,
                "quantity": quantity,
                "failure_reason": failure_reason,
                "message": message,
            }
        )
        self.order_submission_records = self.order_submission_records[-500:]
        self._refresh_submission_table()

    def _refresh_submission_table(self) -> None:
        self.execution_table.setRowCount(len(self.order_submission_records))
        for row_index, item in enumerate(self.order_submission_records):
            values = [
                item.get("timestamp", ""),
                self._display_order_status(item.get("order_status", "")),
                self._display_fill_status(item.get("fill_status", "")),
                item.get("symbol", ""),
                self._display_action(item.get("side", "")),
                item.get("price", ""),
                item.get("quantity", ""),
                item.get("failure_reason", ""),
                item.get("message", ""),
            ]
            background, foreground = self._submission_colors(item)
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setBackground(background)
                table_item.setForeground(foreground)
                self.execution_table.setItem(row_index, column, table_item)

    def _signal_colors(self, action: str, label: str) -> tuple[QColor, QColor]:
        key = label or action
        if key == "RECLAIM_LONG" or action == "BUY":
            return QColor("#E8F7EC"), QColor("#0F5132")
        if key == "TRAP_DETECTED" or action == "AVOID":
            return QColor("#FBEAEA"), QColor("#842029")
        if key == "WATCH":
            return QColor("#FFF4DB"), QColor("#7C4A03")
        if key == "NONE" or action == "HOLD":
            return QColor("#F5F6F7"), QColor("#495057")
        return QColor("#F8F9FA"), QColor("#212529")

    def _submission_colors(self, item: dict[str, str]) -> tuple[QColor, QColor]:
        order_status = item.get("order_status", "")
        fill_status = item.get("fill_status", "")
        if order_status == "FAILED" or fill_status == "REJECTED":
            return QColor("#FBEAEA"), QColor("#842029")
        if fill_status == "PENDING":
            return QColor("#FFF4DB"), QColor("#7C4A03")
        if order_status == "SUBMITTED":
            return QColor("#E7F1FF"), QColor("#084298")
        if fill_status == "FILLED":
            return QColor("#E8F7EC"), QColor("#0F5132")
        return QColor("#F8F9FA"), QColor("#212529")

    def _refresh_broker_status(self, extra: str = "") -> None:
        adapter = EastmoneyBrokerAdapter()
        profile = self.current_broker_profile()
        env = adapter.diagnose_environment(profile)
        market_value = sum(item.market_value for item in self.holdings)
        available = self.cash_snapshot.available_cash if self.cash_snapshot else 0.0
        total_assets = self.cash_snapshot.total_assets if self.cash_snapshot else market_value + available
        connected = (env["direct_ready"] or env["bridge_ready"]) and profile.mode == "sdk"
        note_lines = [
            "环境诊断",
            f"- 主程序 Python：{env['python_version']}",
            f"- 当前解释器 SDK：{'已安装' if env['module_installed'] else '未安装'} ({env['sdk_module']})",
        ]
        if env["bridge_python"]:
            note_lines.append(
                f"- 桥接解释器：{env['bridge_python']} | SDK {'已安装' if env['bridge_module_installed'] else '未安装'}"
            )
        if env["bridge_ready"]:
            note_lines.append("- 当前环境已满足桥接下单条件，可通过 Python 3.12 + GM SDK 调用。")
        elif env["direct_ready"]:
            note_lines.append("- 当前环境已满足直接 SDK 调用条件。")
        else:
            note_lines.append("- 当前环境暂未满足 SDK 下单条件，建议继续使用导出 CSV 或 GM 脚本。")
        content = [
            "网关：东方财富 / 掘金 GM",
            f"模式：{self._display_mode(profile.mode)}",
            f"连接状态：{'已就绪' if connected else '未就绪'}",
            "",
            "\n".join(note_lines),
            "",
            "账户概览",
            f"- 持仓证券数：{len(self.holdings)}",
            f"- 持仓市值：{market_value:,.2f}",
            f"- 可用资金：{available:,.2f}",
            f"- 总资产：{total_assets:,.2f}",
            "",
            f"委托建议数：{len(self.order_intents)}",
        ]
        if extra:
            content.extend(["", extra])
        self.broker_status_text.setPlainText("\n".join(content))

    def _display_action(self, value: str) -> str:
        if value == "REDUCE":
            return "减仓"
        return DISPLAY_TEXT["action"].get(value, value)

    def _display_leader_level(self, value: str) -> str:
        return {
            "CORE_LEADER": "核心龙头",
            "ACTIVE_LEADER": "活跃龙头",
            "FOLLOWER": "跟风股",
            "NOISE": "噪声",
            "": "未分类",
        }.get(value, value)

    def _stock_profile_for_symbol(self, symbol: str) -> StockProfile | None:
        return self.stock_profiles.get(symbol)

    def _stock_name_for_symbol(self, symbol: str) -> str:
        profile = self._stock_profile_for_symbol(symbol)
        if profile and profile.name:
            return profile.name
        return extract_stock_id(symbol)

    def _stock_id_for_symbol(self, symbol: str) -> str:
        profile = self._stock_profile_for_symbol(symbol)
        if profile and profile.stock_id:
            return profile.stock_id
        return extract_stock_id(symbol)

    def _display_label(self, value: str) -> str:
        return DISPLAY_TEXT["label"].get(value, value)

    def _display_order_status(self, value: str) -> str:
        return DISPLAY_TEXT["order_status"].get(value, value)

    def _display_fill_status(self, value: str) -> str:
        return DISPLAY_TEXT["fill_status"].get(value, value)

    def _display_mode(self, value: str) -> str:
        return DISPLAY_TEXT["mode"].get(value, value)

    def _set_theme_combo_value(self, theme_key: str) -> None:
        for index in range(self.theme_combo.count()):
            if self.theme_combo.itemData(index) == theme_key:
                self.theme_combo.setCurrentIndex(index)
                return
        self.theme_combo.setCurrentIndex(0)

    def change_theme(self, *_args: object) -> None:
        theme_key = str(self.theme_combo.currentData() or "sunrise")
        self.current_theme = theme_key
        self._apply_theme(theme_key)
        self.save_state()



    def export_end_of_day_review_from_ui(self, show_dialog: bool = True):
        if not self.scan_rows and not self.daily_pool_rows:
            if show_dialog:
                QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return None

        available_cash = self.cash_snapshot.available_cash if self.cash_snapshot else 0.0
        trade_plan = DecisionEngine().build_plan(
            self.daily_pool_rows,
            self.holdings,
            available_cash,
            max_picks=5,
            top_theme_limit=self.state.strategy_top_theme_limit,
            max_total_exposure=self.state.strategy_max_total_exposure,
            theme_drop_reduce=self.state.strategy_theme_drop_reduce,
        )
        board_plan = BoardModeEngine().build(self.daily_pool_rows, top_n=5)
        output_dir = self._review_output_dir()
        artifacts = export_end_of_day_review(
            output_dir=output_dir,
            recommendations=self.daily_pool_rows,
            trade_plan=trade_plan,
            board_plan=board_plan,
            holdings=self.holdings,
            cash_snapshot=self.cash_snapshot,
            scan_rows=self.scan_rows,
            focus_themes=self.state.focus_themes,
            license_plan=self.state.license_plan,
        )

        export_lines = [
            "收盘复盘日报已导出：",
            f"Markdown：{artifacts.markdown_path}",
            f"CSV：{artifacts.csv_path}",
            f"JSON：{artifacts.json_path}",
        ]
        if hasattr(self, "board_monitor_text"):
            existing = self.board_monitor_text.toPlainText().strip()
            merged = "\n".join([existing, "", *export_lines]) if existing else "\n".join(export_lines)
            self.board_monitor_text.setPlainText(merged)
        if show_dialog:
            QMessageBox.information(self, "导出完成", "\n".join(export_lines))
        return artifacts

    def export_daily_trade_plan_from_ui(self, show_dialog: bool = True):
        if not self.scan_rows and not self.daily_pool_rows:
            if show_dialog:
                QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return None

        available_cash = self.cash_snapshot.available_cash if self.cash_snapshot else 0.0
        trade_plan = DecisionEngine().build_plan(
            self.daily_pool_rows,
            self.holdings,
            available_cash,
            max_picks=5,
            top_theme_limit=self.state.strategy_top_theme_limit,
            max_total_exposure=self.state.strategy_max_total_exposure,
            theme_drop_reduce=self.state.strategy_theme_drop_reduce,
        )
        capabilities = self._license_capabilities()
        template_name, focus_only, candidate_limit = self._current_report_template_config()
        output_dir = self._daily_plan_output_dir()
        artifacts = export_daily_trade_plan(
            output_dir=output_dir,
            recommendations=self.daily_pool_rows,
            trade_plan=trade_plan,
            holdings=self.holdings,
            focus_themes=self.state.focus_themes,
            license_plan=self.state.license_plan,
            template_name=template_name,
            focus_only=focus_only,
            candidate_limit=min(candidate_limit, int(capabilities["daily_plan_export_limit"])),
        )

        export_lines = [
            "盘前交易计划已导出：",
            f"Markdown：{artifacts.markdown_path}",
            f"CSV：{artifacts.csv_path}",
            f"JSON：{artifacts.json_path}",
        ]
        if hasattr(self, "trade_plan_text"):
            existing = self.trade_plan_text.toPlainText().strip()
            merged = "\n".join([existing, "", *export_lines]) if existing else "\n".join(export_lines)
            self.trade_plan_text.setPlainText(merged)
        if show_dialog:
            QMessageBox.information(self, "导出完成", "\n".join(export_lines))
        return artifacts

    def _maybe_auto_export_end_of_day_review(self, current_dt: datetime | None = None) -> None:
        if not hasattr(self, "auto_review_export_checkbox"):
            return
        if not self.auto_review_export_checkbox.isChecked():
            return

        current_dt = current_dt or datetime.now()
        if current_dt.time() < time(15, 5):
            return

        today_key = current_dt.strftime("%Y-%m-%d")
        if self.last_review_export_date == today_key:
            return

        artifacts = self.export_end_of_day_review_from_ui(show_dialog=False)
        if artifacts is None:
            return

        self.last_review_export_date = today_key
        self.last_refresh_label.setText(f"收盘复盘已导出：{current_dt.strftime('%H:%M:%S')}")

    def _maybe_auto_export_daily_trade_plan(self, current_dt: datetime | None = None) -> None:
        capabilities = self._license_capabilities()
        if not bool(capabilities["auto_daily_plan_export"]):
            return
        if not getattr(self.state, "auto_daily_plan_export", False):
            return
        if not self.daily_pool_rows:
            return

        current_dt = current_dt or datetime.now()
        current_time = current_dt.time()
        if current_time < time(8, 55) or current_time > time(9, 25):
            return

        today_key = current_dt.strftime("%Y-%m-%d")
        if self.last_daily_plan_export_date == today_key:
            return

        artifacts = self.export_daily_trade_plan_from_ui(show_dialog=False)
        if artifacts is None:
            return

        self.last_daily_plan_export_date = today_key
        if hasattr(self, "trade_plan_text"):
            existing = self.trade_plan_text.toPlainText().strip()
            note = f"自动盘前计划已导出：{current_dt.strftime('%H:%M:%S')}"
            merged = "\n".join([existing, "", note]) if existing else note
            self.trade_plan_text.setPlainText(merged)

    def _review_output_dir(self) -> Path:
        export_dir = self.current_broker_profile().export_dir.strip()
        if export_dir:
            return Path(export_dir) / "review_reports"
        return REPORT_DIR

    def _daily_plan_output_dir(self) -> Path:
        export_dir = self.current_broker_profile().export_dir.strip()
        if export_dir:
            return Path(export_dir) / "daily_plans"
        return REPORT_DIR / "daily_plans"

    def _board_risk_colors(self, risk_level: str) -> tuple[QColor, QColor]:
        if risk_level == "中":
            return QColor("#E9F7EF"), QColor("#146C43")
        if risk_level == "中高":
            return QColor("#FFF4DB"), QColor("#8A5A00")
        if risk_level == "高":
            return QColor("#FBEAEA"), QColor("#842029")
        return QColor("#F8F9FA"), QColor("#212529")

    def _board_monitor_colors(self, state: str) -> tuple[QColor, QColor]:
        if state == "强势连板候选":
            return QColor("#E8F7EC"), QColor("#0F5132")
        if state == "回封观察":
            return QColor("#E7F1FF"), QColor("#084298")
        if state == "炸板风险":
            return QColor("#FBEAEA"), QColor("#842029")
        return QColor("#FFF4DB"), QColor("#7C4A03")


    def _refresh_board_mode(self) -> None:
        if not hasattr(self, "board_table") or not hasattr(self, "board_monitor_table"):
            return
        board_plan = BoardModeEngine().build(self.daily_pool_rows, top_n=5)

        self.board_table.setRowCount(len(board_plan.candidates))
        for row_index, item in enumerate(board_plan.candidates):
            values = [
                item.stock_name,
                item.stock_id,
                item.symbol,
                f"{item.board_score:.1f}",
                f"{item.momentum_score:.1f}",
                f"{item.liquidity_score:.1f}",
                f"{item.leader_score:.1f}",
                item.trigger_style,
                item.risk_level,
                f"{item.planned_entry:.2f}",
                f"{item.planned_stop:.2f}",
                f"{item.planned_target:.2f}",
            ]
            bg, fg = self._board_risk_colors(item.risk_level)
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setBackground(bg)
                table_item.setForeground(fg)
                self.board_table.setItem(row_index, column, table_item)

        self.board_monitor_table.setRowCount(len(board_plan.monitor_rows))
        for row_index, item in enumerate(board_plan.monitor_rows):
            values = [
                item.stock_name,
                item.stock_id,
                item.symbol,
                item.monitor_state,
                f"{item.strength_score:.1f}",
                f"{item.continuity_score:.1f}",
                f"{item.reboard_probability:.1f}",
                f"{item.blast_risk:.1f}",
                item.action_plan,
                item.note,
            ]
            bg, fg = self._board_monitor_colors(item.monitor_state)
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setBackground(bg)
                table_item.setForeground(fg)
                self.board_monitor_table.setItem(row_index, column, table_item)

        if hasattr(self, "board_text"):
            if board_plan.candidates:
                focus = board_plan.candidates[0]
                lines = [
                    f"?????{board_plan.temperature}",
                    f"??????{board_plan.avg_score:.1f}",
                    "",
                    f"?????{focus.stock_name} ({focus.stock_id})",
                    f"?????{focus.trigger_style}",
                    f"?????{focus.planned_entry:.2f} | ???{focus.planned_stop:.2f} | ???{focus.planned_target:.2f}",
                    f"???{focus.rationale}",
                ]
            else:
                lines = ["???????????????????????"]
            self.board_text.setPlainText("\n".join(lines))

        if hasattr(self, "board_monitor_text"):
            self.board_monitor_text.setPlainText("\n".join(board_plan.notes))


    def _build_overview_tab(self) -> None:
        build_overview_workspace(
            self,
            build_table,
            StrategyParams,
            ActionFlowCard,
            CompactSummaryCard,
            LeaderboardCard,
        )

    def _refresh_overview_side_panels(self, rows: list) -> None:
        self._render_leaderboard_cards(rows)
        if hasattr(self, "market_leaderboard_text"):
            badge_map = {1: "TOP 1", 2: "TOP 2", 3: "TOP 3"}
            leaderboard_cards: list[str] = []
            for index, row in enumerate(rows[:3], start=1):
                border = "#f5c451" if index == 1 else ("#cfd8e3" if index == 2 else "#b7835a")
                badge = badge_map.get(index, f"TOP {index}")
                leaderboard_cards.append(
                    (
                        f"<div style='margin:0 0 12px 0;padding:12px;border:1px solid {border};"
                        "border-radius:10px;background:#11161d;'>"
                        f"<div style='color:{border};font-weight:800;font-size:12px;margin-bottom:6px;'>{badge}</div>"
                        f"<div style='color:#f5f7fa;font-weight:800;font-size:18px;'>{row.stock_name} {row.stock_id}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;margin-top:6px;'>题材方向: {getattr(row, 'theme_name', '') or row.strategy_tag}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;'>资金标签: {row.strategy_tag}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;'>资金标签: {row.fund_model}</div>"
                        f"<div style='color:#25f3ff;font-size:12px;margin-top:6px;'>热度 {row.heat_score:.1f} | 涨幅 {row.pct_change:.2f}%</div>"
                        f"<div style='color:#f5c451;font-size:12px;'>主力净流入 {row.main_inflow / 1e8:.2f} 亿</div>"
                        "</div>"
                    )
                )
            if not leaderboard_cards:
                leaderboard_cards.append("<div style='color:#8fa0b6;'>当前暂无入选标的。</div>")
            self.market_leaderboard_text.setHtml(
                "<div style='font-family:Microsoft YaHei UI;font-size:12px;'>"
                "<div style='color:#f5f7fa;font-size:18px;font-weight:800;margin-bottom:10px;'>掘龙榜</div>"
                + "".join(leaderboard_cards)
                + "</div>"
            )
        if hasattr(self, "market_theme_brief_text"):
            theme_counter: dict[str, int] = {}
            strategy_counter: dict[str, int] = {}
            for row in rows:
                theme_name = getattr(row, "theme_name", "") or row.strategy_tag
                theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
                strategy_counter[row.strategy_tag] = strategy_counter.get(row.strategy_tag, 0) + 1
            ranked = sorted(theme_counter.items(), key=lambda item: item[1], reverse=True)
            theme_lines = ["主线题材", ""]
            for theme_name, count in ranked[:5]:
                theme_lines.append(f"- {theme_name}: {count} 只")
            if not ranked:
                theme_lines.append("当前暂无明确主线题材。")
            if strategy_counter:
                theme_lines.extend(["", "策略热度"])
                for strategy_name, count in sorted(strategy_counter.items(), key=lambda item: item[1], reverse=True)[:5]:
                    theme_lines.append(f"- {strategy_name}: {count} 只")
            self.market_theme_brief_text.setPlainText("\n".join(theme_lines))
            if hasattr(self, "overview_summary_cards"):
                top_theme_name = ranked[0][0] if ranked else "暂无"
                top_theme_count = ranked[0][1] if ranked else 0
                self.overview_summary_cards["theme"].set_data(
                    top_theme_name,
                    f"前排 {top_theme_count} 只 | 题材数 {len(ranked)} | 焦点 {rows[0].stock_name if rows else '等待刷新'}",
                )
        if hasattr(self, "market_breadth_text"):
            news_lines = ["新闻流", ""]
            seen_symbols: set[str] = set()
            for row in rows[:6]:
                symbol_news = self.news_catalysts.get(row.symbol, [])
                if symbol_news:
                    item = symbol_news[0]
                    news_lines.append(f"- {row.stock_name}: {item.title}")
                    if getattr(item, "summary", ""):
                        news_lines.append(f"  {item.summary[:42]}")
                    seen_symbols.add(row.symbol)
            if len(news_lines) == 2:
                for row in rows[:4]:
                    if row.symbol in seen_symbols:
                        continue
                    news_lines.append(
                        f"- {row.stock_name}: {row.strategy_tag} / 涨幅 {row.pct_change:.2f}% / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                    )
            if len(news_lines) == 2:
                news_lines.append("- 当前暂无新闻流摘要。")
            self.market_breadth_text.setPlainText("\n".join(news_lines))
        if hasattr(self, "overview_summary_cards") and not rows:
            self.overview_summary_cards["theme"].set_data("暂无", "等待远程行情或本地缓存加载。")
        self._refresh_market_source_status()
        return
        if hasattr(self, "market_leaderboard_text"):
            badge_map = {1: "TOP 1", 2: "TOP 2", 3: "TOP 3"}
            leaderboard_lines = ["掘龙榜", ""]
            for index, row in enumerate(rows[:3], start=1):
                leaderboard_lines.extend(
                    [
                        f"[ {badge_map.get(index, f'TOP {index}')} ] {row.stock_name} {row.stock_id}",
                        f"题材方向: {row.strategy_tag}",
                        f"资金标签: {row.fund_model}",
                        f"热度 / 涨幅: {row.heat_score:.1f} / {row.pct_change:.2f}%",
                        f"主力净流入: {row.main_inflow / 1e8:.2f} 亿",
                        "-" * 28,
                    ]
                )
            if len(leaderboard_lines) == 2:
                leaderboard_lines.append("当前暂无入选标的。")
            self.market_leaderboard_text.setPlainText("\n".join(leaderboard_lines).strip())
        if hasattr(self, "market_theme_brief_text"):
            theme_counter: dict[str, int] = {}
            for row in rows:
                theme_name = getattr(row, "theme_name", "") or row.strategy_tag
                theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
            ranked = sorted(theme_counter.items(), key=lambda item: item[1], reverse=True)
            theme_lines = ["主线题材", ""]
            for theme_name, count in ranked[:5]:
                theme_lines.append(f"- {theme_name}: {count} 只")
            if not ranked:
                theme_lines.append("当前暂无明确主线题材。")
            self.market_theme_brief_text.setPlainText("\n".join(theme_lines))
        if hasattr(self, "market_breadth_text"):
            news_lines = ["新闻流", ""]
            seen_symbols: set[str] = set()
            for row in rows[:6]:
                symbol_news = self.news_catalysts.get(row.symbol, [])
                if symbol_news:
                    item = symbol_news[0]
                    news_lines.append(f"- {row.stock_name}: {item.title}")
                    if getattr(item, "summary", ""):
                        news_lines.append(f"  {item.summary[:42]}")
                    seen_symbols.add(row.symbol)
            if len(news_lines) == 2:
                for row in rows[:4]:
                    if row.symbol in seen_symbols:
                        continue
                    news_lines.append(
                        f"- {row.stock_name}: {row.strategy_tag} / 涨幅 {row.pct_change:.2f}% / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                    )
            if len(news_lines) == 2:
                news_lines.append("- 当前暂无新闻流摘要。")
            self.market_breadth_text.setPlainText("\n".join(news_lines))
        self._refresh_market_source_status()
        return
        if hasattr(self, "market_leaderboard_text"):
            lines = ["掘龙榜", ""]
            for index, row in enumerate(rows[:3], start=1):
                lines.append(
                    f"TOP {index}  {row.stock_name} {row.stock_id}\n"
                    f"入选理由：{row.strategy_tag} / {row.fund_model} / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                )
                lines.append("")
            if len(lines) == 2:
                lines.append("当前暂无入选标的。")
            self.market_leaderboard_text.setPlainText("\n".join(lines).strip())
        if hasattr(self, "market_theme_brief_text"):
            theme_counter: dict[str, int] = {}
            for row in rows:
                theme_name = getattr(row, "theme_name", "") or row.strategy_tag
                theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
            ranked = sorted(theme_counter.items(), key=lambda item: item[1], reverse=True)
            lines = ["主线题材", ""]
            for theme_name, count in ranked[:5]:
                lines.append(f"- {theme_name}: {count} 只")
            if not ranked:
                lines.append("当前暂无明确主线题材。")
            self.market_theme_brief_text.setPlainText("\n".join(lines))
        if hasattr(self, "market_breadth_text"):
            news_lines = ["新闻流", ""]
            seen_symbols: set[str] = set()
            for row in rows[:6]:
                symbol_news = self.news_catalysts.get(row.symbol, [])
                if symbol_news:
                    item = symbol_news[0]
                    news_lines.append(f"- {row.stock_name}: {item.title}")
                    if getattr(item, "summary", ""):
                        news_lines.append(f"  {item.summary[:42]}")
                    seen_symbols.add(row.symbol)
            if len(news_lines) == 2:
                for row in rows[:4]:
                    if row.symbol in seen_symbols:
                        continue
                    news_lines.append(
                        f"- {row.stock_name}: {row.strategy_tag} / 涨幅 {row.pct_change:.2f}% / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                    )
            if len(news_lines) == 2:
                news_lines.append("- 当前暂无新闻流摘要。")
            self.market_breadth_text.setPlainText("\n".join(news_lines))
        self._refresh_market_source_status()
        return
        if hasattr(self, "market_leaderboard_text"):
            lines = ["掘龙榜", ""]
            for index, row in enumerate(rows[:3], start=1):
                lines.append(
                    f"TOP {index}  {row.stock_name} {row.stock_id}\n"
                    f"入选理由：{row.strategy_tag} / {row.fund_model} / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                )
                lines.append("")
            if len(lines) == 2:
                lines.append("当前暂无入选标的。")
            self.market_leaderboard_text.setPlainText("\n".join(lines).strip())
        if hasattr(self, "market_theme_brief_text"):
            theme_counter: dict[str, int] = {}
            for row in rows:
                theme_name = getattr(row, "theme_name", "") or row.strategy_tag
                theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
            ranked = sorted(theme_counter.items(), key=lambda item: item[1], reverse=True)
            lines = ["主线题材 / 涨跌观察", ""]
            for theme_name, count in ranked[:5]:
                lines.append(f"- {theme_name}: {count} 只")
            if not ranked:
                lines.append("当前暂无明确主线题材。")
            self.market_theme_brief_text.setPlainText("\n".join(lines))
        if hasattr(self, "market_breadth_text"):
            up_count = sum(1 for row in rows if getattr(row, "pct_change", 0.0) > 0)
            down_count = sum(1 for row in rows if getattr(row, "pct_change", 0.0) < 0)
            flat_count = max(len(rows) - up_count - down_count, 0)
            hot_news = [
                f"- {row.stock_name}: {row.strategy_tag} / 涨跌幅 {row.pct_change:.2f}% / 主力净流入 {row.main_inflow / 1e8:.2f} 亿"
                for row in rows[:4]
            ]
            lines = [
                "涨跌分布 / 新闻流",
                "",
                f"- 上涨: {up_count}",
                f"- 下跌: {down_count}",
                f"- 平盘: {flat_count}",
                "",
                "热点跟踪",
            ]
            lines.extend(hot_news or ["- 当前暂无热点新闻摘要。"])
            self.market_breadth_text.setPlainText("\n".join(lines))
        self._refresh_market_source_status()

    def _refresh_market_source_status(self, extra_lines: list[str] | None = None) -> None:
        if not hasattr(self, "market_source_status_text"):
            return
        cache_stats = LocalMarketCache().cache_stats()
        source_code = getattr(self, "market_data_source", "unknown")
        cache_hit = "是" if source_code in {"cache_fresh", "cache_stale", "cache_only"} else "否"
        lines = [
            "数据源状态",
            "",
            f"- 东方财富接入: 已配置",
            f"- 当前模式: {self._market_mode_label()}",
            f"- 当前来源: {self._market_source_mode_label()}",
            f"- 本地缓存文件: {cache_stats.get('files', 0)}",
            f"- 本地缓存大小: {cache_stats.get('bytes', 0)} bytes",
            f"- 当前算法池: {len(getattr(self.market_screen_result, 'algorithmic_pool', []))} 只",
        ]
        lines.insert(5, f"- 当前是否命中缓存: {cache_hit}")
        if getattr(self.market_screen_result, "generated_at", ""):
            lines.append(f"- 最近行情时间: {self.market_screen_result.generated_at}")
        if self.last_market_success_at:
            lines.append(f"- 最后一次成功刷新: {self.last_market_success_at}")
        if self.last_market_error:
            lines.append(f"- 最后一次错误: {self.last_market_error[:120]}")
        if self.runtime_events:
            lines.extend(["", "最近诊断"])
            lines.extend(f"- {item}" for item in self.runtime_events[-4:])
        if extra_lines:
            lines.extend(["", *extra_lines])
        self.market_source_status_text.setPlainText("\n".join(lines))
        if hasattr(self, "overview_summary_cards"):
            source_name = self._market_source_mode_label()
            self.overview_summary_cards["source"].set_data(
                source_name,
                f"{self._market_mode_label()} / 缓存 {'命中' if cache_hit == '是' else '未命中'} / 候选 {len(getattr(self.market_screen_result, 'algorithmic_pool', []))} 只",
            )

    def _market_mode_label(self) -> str:
        return {"auto": "自动", "cache": "仅缓存", "sample": "示例模式"}.get(getattr(self, "market_data_mode", "auto"), "自动")

    def _market_source_mode_label(self) -> str:
        return {
            "remote": "东方财富实时",
            "cache_fresh": "本地新缓存",
            "cache_stale": "本地旧缓存",
            "cache_only": "仅缓存模式",
            "sample": "示例模式",
            "unknown": "未确定",
        }.get(getattr(self, "market_data_source", "unknown"), "未确定")

    def set_market_filter(self, tag: str) -> None:
        self.market_filter_tag = tag
        for current_tag, button in getattr(self, "market_filter_buttons", {}).items():
            button.setChecked(current_tag == tag)
        self._apply_market_filters()
        strategy_target = tag if tag in STRATEGY_SCORE_FIELDS else None
        if strategy_target and hasattr(self, "strategy_detail_combo"):
            self.strategy_detail_combo.setCurrentText(strategy_target)
        if hasattr(self, "market_status_label"):
            status_text = self.market_status_label.text().split(" | 策略：", 1)[0].strip()
            strategy_text = strategy_target or "全部"
            self.market_status_label.setText(f"{status_text} | 策略：{strategy_text}")

    def toggle_dashboard_auto_refresh(self, checked: bool) -> None:
        if checked:
            self.execute_refresh_cycle()
            self.refresh_timer.start(self._refresh_interval_ms())
        elif not getattr(self, "auto_refresh_checkbox", None) or not self.auto_refresh_checkbox.isChecked():
            self.refresh_timer.stop()

    def load_universe_folder(self) -> None:
        self.refresh_remote_market(update_chart=True)

    def load_sample_universe(self) -> None:
        self.refresh_remote_market(update_chart=True)

    def rescan_universe(self) -> None:
        self.refresh_remote_market(update_chart=True)


    def _populate_existing_views_from_market(self) -> None:
        if hasattr(self, "scan_table"):
            self._fill_scan_rows()
        if hasattr(self, "summary_table"):
            self._fill_backtest_summaries()
        if hasattr(self, "daily_pool_table"):
            self._populate_daily_pool_table()
        if hasattr(self, "recommend_status_label"):
            self.recommend_status_label.setText(
                f"已切换为程序自动筛选市场股票池，共 {len(self.daily_pool_rows)} 只候选。"
            )
        if hasattr(self, "daily_pool_text"):
            if self.daily_pool_rows:
                top = self.daily_pool_rows[0]
                self.daily_pool_text.setPlainText(
                    "\n".join(
                        [
                            "今日算法优先候选",
                            f"股票：{top.stock_name} ({top.stock_id} / {top.symbol})",
                            f"总分：{top.total_score:.1f}",
                            f"催化：{top.catalyst or '量价共振 + 主力净流入'}",
                            f"逻辑：{top.rationale}",
                        ]
                    )
                )
            else:
                self.daily_pool_text.setPlainText("当前没有筛出满足条件的股票。")
        self._refresh_trade_plan()
        self._refresh_board_mode()
        self._refresh_intraday_monitor()

    def _populate_daily_pool_table(self) -> None:
        self.theme_heat_rows, self.leader_candidates = summarize_themes(self.daily_pool_rows, top_n_themes=8, top_n_leaders=8)
        self._refresh_recommend_theme_options()
        self._populate_filtered_daily_pool_table()
        self._refresh_theme_heat_panels()
        return
        self.daily_pool_table.setRowCount(len(self.daily_pool_rows))
        for row_index, row in enumerate(self.daily_pool_rows):
            values = [
                row.stock_name,
                row.stock_id,
                row.symbol,
                row.theme_name or "未分类",
                f"{row.theme_score:.1f}",
                self._display_leader_level(row.leader_level),
                f"{row.total_score:.1f}",
                f"{row.technical_score:.0f}",
                f"{row.position_score:.0f}",
                f"{row.persistence_score:.0f}",
                f"{row.news_score:.0f}",
                self._display_action(row.action),
                row.catalyst,
                row.signal_date,
            ]
            for column, value in enumerate(values):
                self.daily_pool_table.setItem(row_index, column, QTableWidgetItem(value))
        self._refresh_theme_heat_panels()

    def _populate_filtered_daily_pool_table(self) -> None:
        populate_filtered_daily_pool_table(self)

    def _refresh_recommend_theme_options(self) -> None:
        if not hasattr(self, "recommend_theme_combo"):
            return
        themes = ["全部"] + [item.theme_name for item in self.theme_heat_rows]
        current = self.recommend_theme_filter if self.recommend_theme_filter in themes else "全部"
        self.recommend_theme_combo.blockSignals(True)
        self.recommend_theme_combo.clear()
        for theme in themes:
            self.recommend_theme_combo.addItem(theme)
        self.recommend_theme_combo.setCurrentText(current)
        self.recommend_theme_combo.blockSignals(False)
        self.recommend_theme_filter = current

    def _on_recommend_theme_filter_changed(self, value: str) -> None:
        self.recommend_theme_filter = value or "全部"
        self._populate_filtered_daily_pool_table()
        self.save_state()

    def _refresh_theme_heat_panels(self) -> None:
        refresh_theme_heat_panels(self, STRATEGY_SCORE_FIELDS)

    def _refresh_strategy_pack_panels(self) -> None:
        refresh_strategy_pack_panels(self, STRATEGY_SCORE_FIELDS)

    def _filtered_daily_pool_rows(self) -> list[RecommendationRow]:
        return [
            row
            for row in self.daily_pool_rows
            if self.recommend_theme_filter == "全部" or (row.theme_name or "未分类") == self.recommend_theme_filter
        ]

    def _set_strategy_detail_from_row(self, row: RecommendationRow | None) -> None:
        if row is None or not hasattr(self, "strategy_detail_combo"):
            return
        self.strategy_detail_combo.setCurrentText(getattr(row, "primary_strategy", "") or "掘龙决策")

    def _select_daily_pool_row_by_stock_id(self, stock_id: str) -> RecommendationRow | None:
        if not stock_id or not hasattr(self, "daily_pool_table"):
            return None
        for index, row in enumerate(self._filtered_daily_pool_rows()):
            if row.stock_id == stock_id:
                self.daily_pool_table.selectRow(index)
                self._set_strategy_detail_from_row(row)
                return row
        return None

    def _on_daily_pool_selection_changed(self) -> None:
        self._refresh_strategy_focus_detail()

    def _on_theme_heat_selection_changed(self) -> None:
        if not hasattr(self, "theme_heat_table") or not hasattr(self, "recommend_theme_combo"):
            return
        row_index = self.theme_heat_table.currentRow()
        if row_index < 0 or row_index >= len(self.theme_heat_rows):
            return
        theme_name = self.theme_heat_rows[row_index].theme_name
        self.recommend_theme_combo.setCurrentText(theme_name)

    def _on_leader_table_selection_changed(self) -> None:
        if not hasattr(self, "leader_table") or not hasattr(self, "daily_pool_table"):
            return
        row_index = self.leader_table.currentRow()
        if row_index < 0 or row_index >= len(self.leader_candidates):
            return
        stock_id = self.leader_candidates[row_index].stock_id
        self._select_daily_pool_row_by_stock_id(stock_id)

    def _on_trade_plan_selection_changed(self) -> None:
        if not hasattr(self, "trade_plan_table") or not hasattr(self, "daily_pool_table"):
            return
        row_index = self.trade_plan_table.currentRow()
        if row_index < 0:
            return
        stock_id_item = self.trade_plan_table.item(row_index, 1)
        stock_id = stock_id_item.text() if stock_id_item else ""
        if not stock_id:
            return
        self._select_daily_pool_row_by_stock_id(stock_id)

    def _on_position_advice_selection_changed(self) -> None:
        if not hasattr(self, "position_advice_table") or not hasattr(self, "daily_pool_table"):
            return
        row_index = self.position_advice_table.currentRow()
        if row_index < 0:
            return
        stock_id_item = self.position_advice_table.item(row_index, 1)
        stock_id = stock_id_item.text() if stock_id_item else ""
        if not stock_id:
            return
        self._select_daily_pool_row_by_stock_id(stock_id)

    def _refresh_strategy_focus_detail(self) -> None:
        refresh_strategy_focus_detail(self, STRATEGY_SCORE_FIELDS)

    def _apply_market_filters(self) -> None:
        apply_market_filters(self)

    def _populate_market_depth_texts(self, rows: list) -> None:
        populate_market_depth_texts(self, rows)

    def on_market_pool_selected(self) -> None:
        if not hasattr(self, "market_pool_table"):
            return
        row = self.market_pool_table.currentRow()
        if row < 0:
            return
        symbol_item = self.market_pool_table.item(row, 0)
        symbol = str(symbol_item.data(Qt.UserRole)) if symbol_item and symbol_item.data(Qt.UserRole) else ""
        if symbol and symbol in self.universe_bars:
            self.select_symbol(symbol)

    def select_symbol(self, symbol: str) -> None:
        if symbol not in self.universe_bars:
            return
        self.active_symbol = symbol
        self.bars = self.universe_bars[symbol]
        self.analyses = self.universe_analyses[symbol]
        if hasattr(self, "active_symbol_label"):
            self.active_symbol_label.setText(f"当前标的：{symbol}")
        self.state.selected_symbol = symbol
        self._refresh_signal_panel()
        self.run_backtest_for_active(quiet=True)
        self._render_market_dashboard(symbol)
        self.save_state()

    def _render_market_dashboard(self, symbol: str) -> None:
        snapshot = self.market_snapshots.get(symbol)
        recommendation = next((item for item in self.daily_pool_rows if item.symbol == symbol), None)
        chart_series = getattr(self.market_screen_result, "chart_series_by_symbol", {}).get(symbol)
        if hasattr(self, "market_header_label"):
            title = symbol if snapshot is None else f"{snapshot.stock_name}  {snapshot.stock_id}  {symbol}"
            self.market_header_label.setText(title)
        if hasattr(self, "market_subheader_label"):
            sub = "程序自动筛选的龙头候选"
            if snapshot is not None:
                sub = (
                    f"{snapshot.strategy_tag} | {snapshot.fund_model} | 涨跌幅 {snapshot.pct_change:.2f}% | "
                    f"换手 {snapshot.turnover:.1f}% | 主力净流入 {snapshot.main_inflow / 1e8:.2f} 亿"
                )
            self.market_subheader_label.setText(sub)
        if hasattr(self, "market_signal_label") and snapshot is not None:
            self.market_signal_label.setText(
                f"{snapshot.fund_model}   |   {snapshot.strategy_tag}   |   热度 {snapshot.heat_score:.1f}   |   动能 {snapshot.momentum_bias:.1f}"
            )
        self._update_intraday_chart(symbol, snapshot, chart_series)
        self._update_daily_chart(symbol)
        self._update_fund_chart(symbol, chart_series)
        self._update_momentum_chart(symbol, chart_series)
        self._update_market_text_panels(symbol, snapshot, recommendation)

    def _build_market_proxy_points(self) -> tuple[list[object], float]:
        rows = list(getattr(self.market_screen_result, "algorithmic_pool", []))[:8]
        if not rows:
            return [], 0.0
        avg_pct = sum(getattr(row, "pct_change", 0.0) for row in rows) / max(len(rows), 1)
        base_price = 1000.0
        values = [
            base_price,
            base_price * (1 + avg_pct / 100.0 * 0.04),
            base_price * (1 + avg_pct / 100.0 * 0.01),
            base_price * (1 + avg_pct / 100.0 * 0.08),
            base_price * (1 + avg_pct / 100.0 * 0.15),
            base_price * (1 + avg_pct / 100.0 * 0.11),
            base_price * (1 + avg_pct / 100.0 * 0.18),
        ]
        points = [type("P", (), {"t": f"{index}", "v": value})() for index, value in enumerate(values)]
        return points, base_price

    def _update_intraday_chart(self, symbol: str, snapshot, chart_series) -> None:
        if not hasattr(self, "intraday_chart_view"):
            return
        chart = QChart()
        intraday_title = "市场代理走势"
        self._style_dark_chart(chart, intraday_title)
        price_series = QLineSeries()
        price_series.setColor(QColor("#25f3ff"))
        reference_series = QLineSeries()
        reference_series.setColor(QColor("#f2c94c"))

        proxy_points, proxy_base = self._build_market_proxy_points()
        points = proxy_points if proxy_points else (list(getattr(chart_series, "intraday_price", [])) if chart_series else [])
        if not points and snapshot is not None:
            base = snapshot.prev_close or snapshot.latest_price
            pseudo = [
                base,
                snapshot.open_price or base,
                snapshot.low_price or base * 0.99,
                (snapshot.low_price + snapshot.open_price) / 2 if snapshot.low_price and snapshot.open_price else base,
                (snapshot.high_price + snapshot.latest_price) / 2 if snapshot.high_price and snapshot.latest_price else base,
                snapshot.high_price or base * 1.01,
                snapshot.latest_price or base,
            ]
            points = [type("P", (), {"t": f"{index}", "v": value})() for index, value in enumerate(pseudo)]

        values = []
        base_price = proxy_base if proxy_points else (
            snapshot.prev_close if snapshot and snapshot.prev_close > 0 else (points[0].v if points else 0.0)
        )
        for index, point in enumerate(points):
            price_series.append(index, point.v)
            reference_series.append(index, base_price)
            values.append(point.v)

        chart.addSeries(price_series)
        if points:
            chart.addSeries(reference_series)

        axis_x = QValueAxis()
        axis_x.setLabelsVisible(False)
        axis_x.setGridLineColor(QColor("#252a33"))
        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#b7c0d8"))
        axis_y.setGridLineColor(QColor("#252a33"))
        if values:
            low = min(values + [base_price])
            high = max(values + [base_price])
            pad = max((high - low) * 0.1, base_price * 0.003 if base_price else 0.03)
            axis_y.setRange(low - pad, high + pad)
            axis_x.setRange(0, max(len(points) - 1, 1))
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignRight)
        price_series.attachAxis(axis_x)
        price_series.attachAxis(axis_y)
        if points:
            reference_series.attachAxis(axis_x)
            reference_series.attachAxis(axis_y)
        self.intraday_chart_view.setChart(chart)

    def _update_daily_chart(self, symbol: str) -> None:
        if not hasattr(self, "daily_chart_view"):
            return
        bars = self.universe_bars.get(symbol, [])
        analyses = self.universe_analyses.get(symbol, [])
        chart = QChart()
        self._style_dark_chart(chart, "日线主图")

        candle_series = QCandlestickSeries()
        candle_series.setIncreasingColor(QColor("#1fe3ff"))
        candle_series.setDecreasingColor(QColor("#ff4f4f"))
        candle_series.setBodyOutlineVisible(True)

        ma_fast_series = QLineSeries()
        ma_fast_series.setColor(QColor("#ffe400"))
        ma_fast_series.setName("MA5")
        ma_slow_series = QLineSeries()
        ma_slow_series.setColor(QColor("#d0d0d0"))
        ma_slow_series.setName("MA20")

        visible_bars = bars[-90:]
        visible_analyses = analyses[-90:] if analyses else []
        dates = []
        highs = []
        lows = []
        for index, bar in enumerate(visible_bars):
            dt = QDateTime.fromString(bar.date, "yyyy-MM-dd")
            ts = float(dt.toMSecsSinceEpoch())
            candle_series.append(QCandlestickSet(bar.open, bar.high, bar.low, bar.close, ts))
            dates.append(ts)
            highs.append(bar.high)
            lows.append(bar.low)
            if index < len(visible_analyses):
                analysis = visible_analyses[index]
                ma_fast_series.append(ts, analysis.ma_fast)
                ma_slow_series.append(ts, analysis.ma_slow)

        chart.addSeries(candle_series)
        chart.addSeries(ma_fast_series)
        chart.addSeries(ma_slow_series)

        axis_x = QDateTimeAxis()
        axis_x.setFormat("MM-dd")
        axis_x.setLabelsColor(QColor("#b7c0d8"))
        axis_x.setTickCount(6)

        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#b7c0d8"))
        axis_y.setGridLineColor(QColor("#2d313a"))
        axis_y.setMinorGridLineVisible(False)
        if highs and lows:
            low = min(lows)
            high = max(highs)
            padding = max((high - low) * 0.08, 0.05)
            axis_y.setRange(low - padding, high + padding)

        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignRight)
        for series in [candle_series, ma_fast_series, ma_slow_series]:
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        if dates:
            axis_x.setRange(QDateTime.fromMSecsSinceEpoch(int(dates[0])), QDateTime.fromMSecsSinceEpoch(int(dates[-1])))

        self.daily_chart_view.setChart(chart)

    def _update_price_chart(self, symbol: str) -> None:
        self._update_daily_chart(symbol)

    def _update_fund_chart(self, symbol: str, chart_series) -> None:
        if not hasattr(self, "fund_chart_view"):
            return
        chart = QChart()
        self._style_dark_chart(chart, "主力资金")
        points = list(getattr(chart_series, "capital_flow", [])) if chart_series else []

        positive = QBarSet("流入")
        negative = QBarSet("流出")
        positive.setColor(QColor("#25d07f"))
        negative.setColor(QColor("#ff5e57"))
        categories = []
        values = []
        for point in points[-24:]:
            value = point.v
            categories.append(point.t)
            positive.append(max(value, 0.0))
            negative.append(abs(min(value, 0.0)))
            values.append(abs(value))

        series = QBarSeries()
        series.append(positive)
        series.append(negative)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories or ["00"])
        axis_x.setLabelsColor(QColor("#8fa0b4"))
        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#b7c0d8"))
        axis_y.setGridLineColor(QColor("#252a33"))
        axis_y.setRange(0, max(values) * 1.25 if values else 1.0)
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignRight)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        self.fund_chart_view.setChart(chart)

    def _update_volume_chart(self, symbol: str) -> None:
        chart_series = getattr(self.market_screen_result, "chart_series_by_symbol", {}).get(symbol)
        self._update_fund_chart(symbol, chart_series)

    def _update_momentum_chart(self, symbol: str, chart_series) -> None:
        if not hasattr(self, "momentum_chart_view"):
            return
        chart = QChart()
        self._style_dark_chart(chart, "龙头动能")
        points = list(getattr(chart_series, "heat_momentum", [])) if chart_series else []

        positive = QBarSet("强")
        negative = QBarSet("弱")
        positive.setColor(QColor("#ff3b30"))
        negative.setColor(QColor("#00e5ff"))
        categories = []
        values = []
        for point in points[-24:]:
            shifted = point.v - 50.0
            categories.append(point.t)
            positive.append(max(shifted, 0.0))
            negative.append(abs(min(shifted, 0.0)))
            values.append(abs(shifted))

        series = QBarSeries()
        series.append(positive)
        series.append(negative)
        chart.addSeries(series)

        axis_x = QBarCategoryAxis()
        axis_x.append(categories or ["00"])
        axis_x.setLabelsColor(QColor("#8fa0b4"))
        axis_y = QValueAxis()
        axis_y.setLabelsColor(QColor("#b7c0d8"))
        axis_y.setGridLineColor(QColor("#252a33"))
        axis_y.setRange(0, max(values) * 1.25 if values else 1.0)
        chart.addAxis(axis_x, Qt.AlignBottom)
        chart.addAxis(axis_y, Qt.AlignRight)
        series.attachAxis(axis_x)
        series.attachAxis(axis_y)
        self.momentum_chart_view.setChart(chart)

    def _update_market_text_panels(self, symbol: str, snapshot, recommendation) -> None:
        if hasattr(self, "market_capital_text"):
            lines = ["主力控盘画像", ""]
            if snapshot is not None:
                lines.extend(
                    [
                        f"- 股票：{snapshot.stock_name} ({snapshot.stock_id})",
                        f"- 资金模型：{snapshot.fund_model}",
                        f"- 主力净流入：{snapshot.main_inflow / 1e8:.2f} 亿",
                        f"- 成交额：{snapshot.amount / 1e8:.2f} 亿",
                        f"- 换手率：{snapshot.turnover:.2f}%",
                        f"- 热度分：{snapshot.heat_score:.1f}",
                    ]
                )
                if recommendation is not None:
                    lines.extend(
                        [
                            f"- 主策略：{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'}",
                            (
                                f"- 五策评分：龙头 {getattr(recommendation, 'leader_model_score', 0.0):.1f} / "
                                f"主力 {getattr(recommendation, 'main_force_score', 0.0):.1f} / "
                                f"打板 {getattr(recommendation, 'board_attack_score', 0.0):.1f} / "
                                f"低吸 {getattr(recommendation, 'value_recovery_score', 0.0):.1f} / "
                                f"决策 {getattr(recommendation, 'dragon_decision_score', recommendation.total_score):.1f}"
                            ),
                        ]
                    )
            else:
                lines.append("- 暂无资金画像数据")
            self.market_capital_text.setPlainText("\n".join(lines))
            if hasattr(self, "overview_summary_cards"):
                capital_headline = f"{snapshot.main_inflow / 1e8:.2f} 亿" if snapshot is not None else "--"
                capital_detail = (
                    f"{snapshot.fund_model} / 换手 {snapshot.turnover:.2f}% / 热度 {snapshot.heat_score:.1f}"
                    if snapshot is not None
                    else "等待资金画像数据。"
                )
                self.overview_summary_cards["capital"].set_data(capital_headline, capital_detail)

        if hasattr(self, "market_decision_text"):
            lines = ["龙头状态 / 决策建议", ""]
            latest_signal = next((item for item in reversed(self.analyses) if item.label != "NONE"), None)
            if recommendation is not None:
                strategy_name = getattr(recommendation, "primary_strategy", "") or "掘龙决策"
                lines.extend(
                    [
                        f"- 主策略：{strategy_name}",
                        f"- 推荐动作：{self._display_action(recommendation.action)}",
                        f"- 信号标签：{self._display_label(recommendation.label)}",
                        f"- 综合决策分：{getattr(recommendation, 'dragon_decision_score', recommendation.total_score):.1f}",
                        f"- 计划买点：{(recommendation.entry_price or recommendation.close):.2f}",
                        f"- 防守止损：{(recommendation.stop_price or recommendation.close * 0.95):.2f}",
                        f"- 预期目标：{(recommendation.target_price or recommendation.close * 1.1):.2f}",
                        f"- 催化：{recommendation.catalyst or '量价共振'}",
                        "",
                        f"逻辑：{recommendation.rationale}",
                    ]
                )
            elif latest_signal is not None:
                lines.extend([f"- 最新信号：{latest_signal.label}", latest_signal.reason])
            else:
                lines.append("- 当前没有生成决策建议。")
            self.market_decision_text.setPlainText("\n".join(lines))
            if hasattr(self, "overview_summary_cards"):
                decision_headline = self._display_action(recommendation.action) if recommendation is not None else "观察"
                decision_detail = (
                    f"{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'} / 决策分 {getattr(recommendation, 'dragon_decision_score', recommendation.total_score):.1f}"
                    if recommendation is not None
                    else (latest_signal.label if latest_signal is not None else "等待交易决策生成。")
                )
                self.overview_summary_cards["decision"].set_data(decision_headline, decision_detail)

    def _market_pool_colors(self, row) -> tuple[QColor, QColor]:
        if row.pct_change >= 8:
            return QColor("#2b0909"), QColor("#ff5e57")
        if row.main_inflow > 1.5e8:
            return QColor("#08291d"), QColor("#25d07f")
        if row.turnover >= 10:
            return QColor("#2b2409"), QColor("#f7d354")
        return QColor("#0f1116"), QColor("#d7dce5")

    def _style_dark_chart(self, chart: QChart, title: str) -> None:
        chart.setTitle(title)
        chart.setTitleBrush(QColor("#dfe6ee"))
        chart.setBackgroundBrush(QColor("#0a0c10"))
        chart.setPlotAreaBackgroundVisible(True)
        chart.setPlotAreaBackgroundBrush(QColor("#000000"))
        chart.setMargins(chart.margins())
        chart.legend().hide()

    def _build_stock_identity_cell(self, row) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        name_label = QLabel(row.stock_name)
        name_label.setStyleSheet("QLabel { color: #f3f5f7; font-weight: 800; font-size: 14px; }")
        meta_label = QLabel(f"{row.stock_id}  |  {row.symbol}  |  热度 {row.heat_score:.1f}")
        meta_label.setStyleSheet("QLabel { color: #8793a6; font-size: 11px; }")

        layout.addWidget(name_label)
        layout.addWidget(meta_label)
        return wrapper

    def _create_metric_card(self, title: str, value: str, accent: str) -> tuple[QFrame, QLabel, QLabel]:
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QLabel(title)
        title_label.setObjectName("metricCaption")
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        accent_label = QLabel(accent)
        accent_label.setObjectName("metricAccent")

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(accent_label)
        layout.addStretch(1)
        return card, value_label, accent_label

    def _overview_outline_style(self, accent: str) -> str:
        return (
            "QPushButton {"
            f"border: 1px solid {accent}; color: {accent}; padding: 10px 16px; border-radius: 10px;"
            "background: rgba(255,255,255,0.02); font-weight: 800; min-height: 20px; }"
            "QPushButton:hover { background: rgba(255,255,255,0.06); }"
            "QPushButton:checked { background: rgba(255,255,255,0.08); }"
        )

    def _overview_filled_style(self, accent: str) -> str:
        return (
            "QPushButton {"
            f"border: 1px solid {accent}; color: #f4fbff; padding: 10px 18px; border-radius: 12px;"
            f"background: {accent}; font-weight: 800; min-height: 22px; }}"
            f"QPushButton:hover {{ background: {accent}; border-color: #f4fbff; }}"
            "QPushButton:checked { background: #0f7ea8; border-color: #86e1ff; }"
        )

    def _render_leaderboard_cards(self, rows: list) -> None:
        render_leaderboard_cards(self, rows)

    def _build_badge_strip(self, badges: list[tuple[str, str, str]]) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(4)
        for text, bg, fg in badges:
            if not text:
                continue
            badge = QLabel(text)
            badge.setStyleSheet(
                "QLabel {"
                f"background: {bg}; color: {fg}; border: 1px solid {fg};"
                "padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 700; }"
            )
            layout.addWidget(badge)
        layout.addStretch(1)
        return wrapper

    def _apply_dashboard_labels(self) -> None:
        if not hasattr(self, "tabs"):
            return
        for index, key in enumerate(WORKSPACE_TAB_ORDER):
            if index < self.tabs.count():
                self.tabs.setTabText(index, WORKSPACE_LABEL_BY_KEY.get(key, "????"))
        if hasattr(self, "top_badge"):
            self.top_badge.setText("???? v2.2")
        if hasattr(self, "theme_title_label"):
            self.theme_title_label.setText("??")
        self.setWindowTitle("???? Pro v2.2")

    def _apply_theme(self, theme_key: str) -> None:
        base_style = THEME_STYLES.get(theme_key, THEME_STYLES["sunrise"])
        extra_style = TERMINAL_DASHBOARD_STYLE + TERMINAL_WORKSPACE_STYLE if theme_key == "graphite" else ""
        if theme_key == "graphite":
            extra_style += """
QTableWidget {
    background: #0f1319;
    alternate-background-color: #11161d;
    color: #dfe7f2;
    gridline-color: #1d2630;
    selection-background-color: #143548;
    selection-color: #ffffff;
}
QHeaderView::section {
    background: #151c24;
    color: #9db4c8;
    border: none;
    border-bottom: 1px solid #24303d;
    padding: 8px 10px;
    font-weight: 700;
}
QLineEdit, QComboBox {
    background: #0f1319;
    color: #e9f2fb;
    border: 1px solid #2a3a4a;
    border-radius: 10px;
    padding: 8px 12px;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #4fc3f7;
}
QTextEdit#terminalConsole {
    background: #0f1319;
    color: #dbe8f5;
    border: 1px solid #1e2935;
    border-radius: 12px;
    padding: 10px;
}
QGroupBox#terminalPanel {
    background: #11161d;
    border: 1px solid #1f2a35;
    border-radius: 14px;
    margin-top: 12px;
    padding-top: 12px;
}
QGroupBox#terminalPanel::title {
    color: #f3f8fc;
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px 0 4px;
}
QPushButton#ghostButton {
    background: #131b24;
    color: #d7e6f5;
    border: 1px solid #304355;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 700;
}
QPushButton#ghostButton:hover {
    border-color: #4fc3f7;
}
QPushButton#accentButton {
    background: #1578a6;
    color: #f4fbff;
    border: 1px solid #2196c9;
    border-radius: 10px;
    padding: 8px 14px;
    font-weight: 800;
}
QPushButton#accentButton:hover {
    background: #1a89bc;
}
"""
        self.setStyleSheet(base_style + extra_style)

    def _build_scanner_tab(self) -> None:
        layout = QVBoxLayout(self.scanner_tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        self.scanner_tab.setObjectName("scannerRoot")

        layout.addWidget(
            self._build_workspace_hero(
                "策略扫描",
                "全市场扫描与盘中联动监控",
                "把算法候选、观察池、回测摘要和盘中预警统一放进一个工作台里，适合日内持续盯盘和快速切换。",
                [("实时", "自动刷新"), ("3区", "扫描/观察/监控")],
            )
        )

        controls = QHBoxLayout()
        open_button = QPushButton("打开股票目录")
        sample_button = QPushButton("载入示例数据")
        rescan_button = QPushButton("重新扫描")
        add_watch_button = QPushButton("加入观察池")
        remove_watch_button = QPushButton("移出观察池")
        self.auto_refresh_checkbox = QCheckBox("盘中自动刷新")
        self.sound_alert_checkbox = QCheckBox("声音提醒")
        self.sound_alert_checkbox.setChecked(True)
        self.auto_refresh_checkbox.toggled.connect(self.toggle_auto_refresh)
        self.refresh_interval_input = QLineEdit("60")
        self.refresh_interval_input.setMaximumWidth(60)
        self.refresh_interval_input.setObjectName("intervalInput")
        self.last_refresh_label = QLabel("尚未刷新")
        self.last_refresh_label.setObjectName("inlineHint")

        open_button.clicked.connect(self.load_universe_folder)
        sample_button.clicked.connect(self.load_sample_universe)
        rescan_button.clicked.connect(self.rescan_universe)
        add_watch_button.clicked.connect(self.add_selected_to_watchlist)
        remove_watch_button.clicked.connect(self.remove_selected_from_watchlist)

        self._set_button_role(open_button)
        self._set_button_role(sample_button)
        self._set_button_role(rescan_button, "accent")
        self._set_button_role(add_watch_button)
        self._set_button_role(remove_watch_button)

        for widget in [
            open_button,
            sample_button,
            rescan_button,
            add_watch_button,
            remove_watch_button,
            self.auto_refresh_checkbox,
            self.sound_alert_checkbox,
            self.refresh_interval_input,
            QLabel("秒"),
            self.last_refresh_label,
        ]:
            controls.addWidget(widget)
        controls.addStretch(1)
        layout.addLayout(controls)

        hint = QLabel("扫描页会自动复用首页筛出的市场候选，也支持叠加本地样本与观察池做交叉验证。")
        hint.setObjectName("inlineHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.universe_label = QLabel("股票池目录：未加载")
        self.scan_summary_label = QLabel("尚未执行扫描。")
        self.universe_label.setObjectName("inlineHint")
        self.scan_summary_label.setObjectName("inlineHint")
        info_row = QHBoxLayout()
        info_row.addWidget(self.universe_label)
        info_row.addStretch(1)
        info_row.addWidget(self.scan_summary_label)
        layout.addLayout(info_row)

        scan_box = QGroupBox("信号扫描榜")
        self._style_terminal_panel(scan_box)
        scan_layout = QVBoxLayout(scan_box)
        self.scan_table = build_table(["代码", "动作", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"])
        self.scan_table.itemSelectionChanged.connect(self.on_scan_selected)
        scan_layout.addWidget(self.scan_table)
        layout.addWidget(scan_box, stretch=2)

        bottom = QSplitter(Qt.Horizontal)
        bottom.setChildrenCollapsible(False)

        watch_box = QGroupBox("观察池")
        self._style_terminal_panel(watch_box)
        watch_layout = QVBoxLayout(watch_box)
        self.watchlist_widget = QListWidget()
        self.watchlist_widget.setObjectName("watchlistPanel")
        self.watchlist_widget.itemSelectionChanged.connect(self.on_watchlist_selected)
        watch_layout.addWidget(self.watchlist_widget)
        bottom.addWidget(watch_box)

        summary_box = QGroupBox("回测摘要")
        self._style_terminal_panel(summary_box)
        summary_layout = QVBoxLayout(summary_box)
        self.summary_table = build_table(["代码", "交易数", "收益率", "回撤", "胜率", "期末权益"])
        summary_layout.addWidget(self.summary_table)
        bottom.addWidget(summary_box)

        monitor_box = QGroupBox("盘中监控")
        self._style_terminal_panel(monitor_box)
        monitor_layout = QVBoxLayout(monitor_box)
        self.monitor_table = build_table(["代码", "动作", "信号", "评分", "收盘价", "信号日期", "更新时间"])
        monitor_layout.addWidget(self.monitor_table)
        self.monitor_summary_text = QTextEdit()
        self.monitor_summary_text.setReadOnly(True)
        self._style_terminal_console(self.monitor_summary_text)
        self.monitor_summary_text.setPlainText("等待盘中监控刷新。")
        monitor_layout.addWidget(self.monitor_summary_text)
        bottom.addWidget(monitor_box)

        self._configure_splitter(bottom, [290, 500, 550])
        layout.addWidget(bottom, stretch=1)

    def _build_recommend_tab(self) -> None:
        build_recommend_workspace(
            self,
            build_table,
            StrategyWorkbenchCard,
            ActionFlowCard,
            AlertSignalCard,
            CompactSummaryCard,
            STRATEGY_WORKBENCH_SPECS,
            STRATEGY_SCORE_FIELDS,
        )

    def _build_auth_tab(self) -> None:
        build_auth_workspace(self)

    def _build_detail_tab(self) -> None:
        build_detail_workspace(self, build_table)

    def _build_broker_tab(self) -> None:
        build_broker_workspace(self, build_table, EastmoneyBrokerAdapter, PROJECT_ROOT)

    def _build_board_tab(self) -> None:
        build_board_workspace(self, build_table, QHeaderView)

    def refresh_daily_pool(self, async_mode: bool = True) -> None:
        refresh_daily_pool_controller(self, async_mode, daily_pool_builder_cls=DailyPoolBuilder)

    def _scan_universe_payload(
        self,
        folder: Path,
        params: StrategyParams,
    ) -> tuple[list[ScanRow], dict[str, list[PriceBar]], dict[str, list[DailyAnalysis]], dict[str, Path], list[SymbolBacktestSummary]]:
        scanner = UniverseScanner(params)
        rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol = scanner.scan_folder(folder)
        summaries = scanner.summarize_backtests(bars_by_symbol, analyses_by_symbol)
        return rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol, summaries






    def _refresh_market_theme_options(self) -> None:
        if not hasattr(self, "market_theme_combo"):
            return
        themes = ["全部"] + sorted({(getattr(row, "theme_name", "") or row.strategy_tag) for row in getattr(self.market_screen_result, "algorithmic_pool", []) if (getattr(row, "theme_name", "") or row.strategy_tag)})
        current = self.market_theme_filter if self.market_theme_filter in themes else "全部"
        self.market_theme_combo.blockSignals(True)
        self.market_theme_combo.clear()
        for theme in themes:
            self.market_theme_combo.addItem(theme)
        self.market_theme_combo.setCurrentText(current)
        self.market_theme_combo.blockSignals(False)
        self.market_theme_filter = current

    def _on_market_theme_filter_changed(self, value: str) -> None:
        self.market_theme_filter = value or "全部"
        self._apply_market_filters()
        self.save_state()

    def _on_market_data_mode_changed(self) -> None:
        if not hasattr(self, "market_data_mode_combo"):
            return
        self.market_data_mode = str(self.market_data_mode_combo.currentData() or "auto")
        self.state.market_data_mode = self.market_data_mode
        self.save_state()
        self.refresh_remote_market(quiet=True, update_chart=True, async_mode=True)

    def refresh_remote_market(self, quiet: bool = False, update_chart: bool = False, async_mode: bool = True) -> None:
        refresh_remote_market_controller(
            self,
            quiet,
            update_chart,
            async_mode,
            market_screen_result_cls=MarketScreenResult,
            cache_only_feed_cls=CacheOnlyMarketFeed,
            remote_market_screener_cls=RemoteMarketScreener,
            datetime_cls=datetime,
        )

    def _fund_badge_palette(self, text: str) -> tuple[str, str]:
        mapping = {
            "游资强攻": ("#5f1114", "#ff7f86"),
            "主力净流入": ("#0f3a28", "#41f0a3"),
            "机构趋势": ("#12345d", "#81b9ff"),
            "低位试盘": ("#5d4a12", "#ffd76d"),
            "强势博弈": ("#3c1f63", "#d2a8ff"),
        }
        return mapping.get(text, ("#24303a", "#dce4ef"))

    def _strategy_badge_palette(self, text: str) -> tuple[str, str]:
        mapping = {
            "龙头模型": ("#5b1216", "#ff6a6f"),
            "主力雷达": ("#0f3951", "#7ed7ff"),
            "擒龙打板": ("#57430f", "#ffd75b"),
            "价值低吸": ("#204728", "#7ef5a2"),
            "掘龙决策": ("#4b235f", "#db9bff"),
        }
        return mapping.get(text, ("#24303a", "#dce4ef"))

    def _signal_badge_palette(self, text: str) -> tuple[str, str]:
        mapping = {
            "回补做多": ("#153b23", "#56f0a3"),
            "观察": ("#4b3a14", "#ffd971"),
            "诱多陷阱": ("#5a1016", "#ff7a7a"),
            "无信号": ("#26333d", "#b9c3d0"),
            "BUY": ("#153b23", "#56f0a3"),
            "WATCH": ("#4b3a14", "#ffd971"),
        }
        return mapping.get(text, ("#24303a", "#dce4ef"))

    def _update_dashboard_metrics(self) -> None:
        if not hasattr(self, "dashboard_metric_labels"):
            return
        pool = list(getattr(self.market_screen_result, "algorithmic_pool", []))
        recommendations = list(self.daily_pool_rows)
        buy_count = sum(1 for item in recommendations if item.action == "BUY")
        avg_heat = (sum(item.heat_score for item in pool) / len(pool)) if pool else 0.0
        theme_counter: dict[str, int] = {}
        for item in pool:
            theme_counter[item.strategy_tag] = theme_counter.get(item.strategy_tag, 0) + 1
        top_theme = max(theme_counter.items(), key=lambda item: item[1])[0] if theme_counter else "暂无"

        self.dashboard_metric_labels["candidate_count"].setText(str(len(pool)))
        self.dashboard_metric_accents["candidate_count"].setText(
            f"Top 1：{pool[0].stock_name}" if pool else "等待刷新"
        )

        self.dashboard_metric_labels["buy_count"].setText(str(buy_count))
        self.dashboard_metric_accents["buy_count"].setText(
            f"观察 {max(len(recommendations) - buy_count, 0)} 只"
        )

        self.dashboard_metric_labels["avg_heat"].setText(f"{avg_heat:.1f}")
        self.dashboard_metric_accents["avg_heat"].setText(
            "热度高于 80 为强势前排" if pool else "等待刷新"
        )

        self.dashboard_metric_labels["top_theme"].setText(top_theme)
        self.dashboard_metric_accents["top_theme"].setText(
            f"{theme_counter.get(top_theme, 0)} 只" if theme_counter else "等待刷新"
        )

    def _refresh_interval_ms(self) -> int:
        if not hasattr(self, "refresh_interval_input"):
            return 60000
        try:
            interval = float(self.refresh_interval_input.text().strip())
        except ValueError:
            interval = 60.0
            self.refresh_interval_input.setText("60")
        return max(int(interval * 1000), 5000)

    def execute_refresh_cycle(self) -> None:
        scanner_auto = hasattr(self, "auto_refresh_checkbox") and self.auto_refresh_checkbox.isChecked()
        dashboard_auto = hasattr(self, "dashboard_auto_refresh_checkbox") and self.dashboard_auto_refresh_checkbox.isChecked()
        if not scanner_auto and not dashboard_auto:
            return

        self.refresh_timer.start(self._refresh_interval_ms())
        current_dt = datetime.now()
        now = current_dt.time()
        in_session = time(9, 25) <= now <= time(11, 35) or time(12, 55) <= now <= time(15, 5)

        if dashboard_auto:
            if in_session:
                self.refresh_remote_market(quiet=True, update_chart=False)
                if hasattr(self, "last_refresh_label"):
                    self.last_refresh_label.setText(f"最近刷新：{current_dt.strftime('%H:%M:%S')}")
            else:
                if hasattr(self, "last_refresh_label"):
                    self.last_refresh_label.setText(f"等待交易时段：{current_dt.strftime('%H:%M:%S')}")

        if scanner_auto and self.state.universe_dir and in_session:
            self._scan_universe(Path(self.state.universe_dir), quiet=True)
            if self.current_broker_profile().mode == "sdk":
                self.sync_broker_via_sdk(quiet=True)

        self._maybe_auto_export_end_of_day_review(current_dt)

    def _handle_daily_pool_error(self, message: str) -> None:
        handle_daily_pool_error(self, message, show_error_dialog_fn=QMessageBox.critical)

    def _apply_daily_pool_rows(self, rows: list[RecommendationRow]) -> None:
        apply_daily_pool_rows(self, rows, summarize_themes)

    def _handle_scan_error(self, message: str, quiet: bool) -> None:
        handle_scan_error(self, message, quiet, show_error_dialog_fn=QMessageBox.critical)

    def _apply_scan_universe_result(
        self,
        folder: Path,
        payload: tuple[list[ScanRow], dict[str, list[PriceBar]], dict[str, list[DailyAnalysis]], dict[str, Path], list[SymbolBacktestSummary]],
    ) -> None:
        apply_scan_universe_result(self, folder, payload)

    def _handle_market_refresh_error(self, message: str, quiet: bool) -> None:
        handle_market_refresh_error(self, message, quiet, show_error_dialog_fn=QMessageBox.critical)

    def _apply_market_screen_result(
        self,
        result: MarketScreenResult,
        update_chart: bool = False,
        feed_state: dict[str, str] | None = None,
    ) -> None:
        apply_market_screen_result(
            self,
            result,
            update_chart=update_chart,
            feed_state=feed_state,
            cache_cls=LocalMarketCache,
            extract_stock_id_fn=extract_stock_id,
            stock_profile_cls=StockProfile,
            project_root=PROJECT_ROOT,
        )

    def run_parameter_optimization(self) -> None:
        run_parameter_optimization_controller(
            self,
            parameter_optimizer_cls=ParameterOptimizer,
            report_dir=REPORT_DIR,
            info_dialog_fn=QMessageBox.information,
            error_dialog_fn=QMessageBox.critical,
        )


    def _runtime_overview_text(self) -> str:
        return build_runtime_overview_text(self, cache_cls=LocalMarketCache, datetime_cls=datetime)

    def refresh_runtime_panel(self) -> None:
        refresh_runtime_panel_runtime(self, cache_cls=LocalMarketCache, datetime_cls=datetime)

    def _runtime_export_dir(self) -> Path:
        return runtime_export_dir_runtime(self, project_root=PROJECT_ROOT)

    def export_runtime_log(self) -> None:
        export_runtime_log_runtime(
            self,
            project_root=PROJECT_ROOT,
            datetime_cls=datetime,
            info_dialog_fn=QMessageBox.information,
            cache_cls=LocalMarketCache,
        )

    def clear_market_cache(self) -> None:
        clear_market_cache_runtime(self, cache_cls=LocalMarketCache, datetime_cls=datetime, info_dialog_fn=QMessageBox.information)

    def _record_job_result(self, job_name: str, status: str, duration_ms: float, message: str = "") -> None:
        record_job_result_runtime(self, job_name, status, duration_ms, datetime_cls=datetime, message=message)

    def _is_job_running(self, job_name: str) -> bool:
        return job_name in self.active_jobs or job_name in self.job_handles

    def _run_background_job(
        self,
        job_name: str,
        fn,
        on_success,
        on_error,
    ) -> bool:
        return run_background_job_controller(
            self,
            job_name,
            fn,
            on_success,
            on_error,
            background_task_cls=BackgroundTask,
            registry=BACKGROUND_TASK_REGISTRY,
            perf_counter_fn=time_module.perf_counter,
        )


    def _post_build_ui_tweaks(self) -> None:
        self.resize(max(self.width(), 1500), max(self.height(), 900))
        self.setMinimumSize(max(self.minimumWidth(), 1360), max(self.minimumHeight(), 820))

        if hasattr(self, "broker_scroll_area"):
            self._enable_smooth_scroll(self.broker_scroll_area)

        for button in getattr(self, "overview_quick_buttons", {}).values():
            button.setMinimumHeight(40)
        for button in getattr(self, "market_filter_buttons", {}).values():
            button.setMinimumHeight(40)
        for button in getattr(self, "timeframe_buttons", {}).values():
            button.setMinimumHeight(40)

        if hasattr(self, "market_refresh_button"):
            self.market_refresh_button.setMinimumHeight(42)
        if hasattr(self, "market_theme_combo"):
            self.market_theme_combo.setMinimumHeight(36)
        if hasattr(self, "market_search_input"):
            self.market_search_input.setMinimumHeight(36)

        self.set_market_timeframe(getattr(self, "market_timeframe_mode", "日线"))
        self.set_overview_focus(getattr(self, "overview_focus_mode", "市场总览"))
        self._refresh_alert_cards_from_state()
        if hasattr(self, "overview_summary_cards"):
            self.overview_summary_cards["theme"].set_data("暂无", "等待主线题材与龙头池刷新。")
            self.overview_summary_cards["source"].set_data("待连接", "等待远程行情、缓存或示例数据。")
            self.overview_summary_cards["capital"].set_data("--", "等待主力资金画像生成。")
            self.overview_summary_cards["decision"].set_data("观察", "等待交易决策生成。")

    def _workspace_tabs(self) -> dict[str, QWidget]:
        return {
            "overview": self.overview_tab,
            "scanner": self.scanner_tab,
            "recommend": self.recommend_tab,
            "board": self.board_tab,
            "config": self.config_tab,
            "auth": self.auth_tab,
            "detail": self.detail_tab,
            "broker": self.broker_tab,
        }

    def _workspace_name_for_index(self, index: int) -> str:
        if 0 <= index < len(WORKSPACE_TAB_ORDER):
            return WORKSPACE_LABEL_BY_KEY.get(WORKSPACE_TAB_ORDER[index], "????")
        return "????"

    def _select_first_row(self, widget_name: str | None) -> None:
        if not widget_name:
            return
        widget = getattr(self, widget_name, None)
        if widget is not None and hasattr(widget, "rowCount") and widget.rowCount() > 0:
            widget.selectRow(0)

    def _navigate_to_workspace(self, workspace_key: str, widget_name: str | None = None, select_row: str | None = None) -> None:
        if hasattr(self, "tabs"):
            target_tab = self._workspace_tabs().get(workspace_key)
            if target_tab is not None:
                self.tabs.setCurrentWidget(target_tab)
        self._focus_widget_later(getattr(self, widget_name, None) if widget_name else None)
        self._select_first_row(select_row)

    def _on_workspace_tab_changed(self, index: int) -> None:
        current_name = self._workspace_name_for_index(index)
        if hasattr(self, "top_badge"):
            self.top_badge.setText(f"???? v2.2 ? {current_name}")
        if hasattr(self, "market_status_label") and getattr(self, "tabs", None) and self.tabs.currentWidget() is self.overview_tab:
            status_text = self.market_status_label.text()
            view_part = ""
            if " | ???" in status_text:
                status_text, view_part = status_text.split(" | ???", 1)
            page_part = f" | ???{current_name}"
            if view_part:
                page_part += f" | ???{view_part}"
            self.market_status_label.setText(f"{status_text.split(' | ???', 1)[0]}{page_part}")

    def _focus_widget_later(self, widget: QWidget | None) -> None:
        if widget is None:
            return
        QTimer.singleShot(0, widget.setFocus)

    def activate_overview_quick_action(self, focus: str) -> None:
        self.set_overview_focus(focus)
        route = OVERVIEW_QUICK_ROUTE_SPECS.get(
            focus,
            {"workspace": "overview", "widget": "intraday_chart_view"},
        )
        self._navigate_to_workspace(
            str(route.get("workspace", "overview")),
            str(route.get("widget")) if route.get("widget") else None,
            str(route.get("select_row")) if route.get("select_row") else None,
        )

    def set_overview_focus(self, focus: str) -> None:
        self.overview_focus_mode = focus or "市场总览"
        for button in getattr(self, "overview_quick_buttons", {}).values():
            button.blockSignals(True)
            button.setChecked(button.text() == self.overview_focus_mode)
            button.blockSignals(False)

        main_sizes = {
            "市场总览": [360, 1020, 360],
            "龙头池": [300, 1160, 320],
            "涨跌分布": [430, 950, 320],
            "资金方向": [320, 1080, 320],
            "题材热度": [320, 930, 430],
            "交易决策": [300, 900, 480],
        }.get(self.overview_focus_mode, [360, 1020, 360])
        left_sizes = {
            "市场总览": [1, 1, 1],
            "龙头池": [1, 1, 1],
            "涨跌分布": [110, 160, 260],
            "资金方向": [150, 110, 150],
            "题材热度": [120, 100, 220],
            "交易决策": [110, 110, 180],
        }.get(self.overview_focus_mode, [1, 1, 1])
        mini_sizes = {
            "市场总览": [1, 1],
            "龙头池": [1, 1],
            "涨跌分布": [1, 1],
            "资金方向": [3, 2],
            "题材热度": [1, 1],
            "交易决策": [2, 1],
        }.get(self.overview_focus_mode, [1, 1])

        if hasattr(self, "overview_main_splitter"):
            self._configure_splitter(self.overview_main_splitter, main_sizes)
        if hasattr(self, "overview_left_notes_splitter"):
            self._configure_splitter(self.overview_left_notes_splitter, left_sizes)
        if hasattr(self, "overview_mini_chart_splitter"):
            self._configure_splitter(self.overview_mini_chart_splitter, mini_sizes)

        focus_widget = {
            "龙头池": getattr(self, "market_pool_table", None),
            "涨跌分布": getattr(self, "market_breadth_text", None),
            "资金方向": getattr(self, "market_capital_text", None),
            "题材热度": getattr(self, "market_theme_brief_text", None),
            "交易决策": getattr(self, "market_decision_text", None),
        }.get(self.overview_focus_mode)
        if focus_widget is not None:
            focus_widget.setFocus()

        if hasattr(self, "market_status_label"):
            status_text = self.market_status_label.text()
            if " | 页面：" in status_text:
                base_text, page_suffix = status_text.split(" | 页面：", 1)
                page_text = page_suffix.split(" | 视图：", 1)[0]
                self.market_status_label.setText(f"{base_text} | 页面：{page_text} | 视图：{self.overview_focus_mode}")
            else:
                base_text = status_text.split(" | 视图：", 1)[0].strip()
                self.market_status_label.setText(f"{base_text} | 视图：{self.overview_focus_mode}")

    def set_market_timeframe(self, timeframe: str) -> None:
        self.market_timeframe_mode = timeframe or "日线"
        matched = False
        for button in getattr(self, "timeframe_buttons", {}).values():
            checked = button.text() == self.market_timeframe_mode
            matched = matched or checked
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
        if not matched and getattr(self, "timeframe_buttons", None):
            fallback = next(iter(self.timeframe_buttons.values()))
            self.market_timeframe_mode = fallback.text()
            fallback.setChecked(True)

        intraday_height = 300 if self.market_timeframe_mode != "日线" else 250
        daily_height = 320 if self.market_timeframe_mode != "日线" else 360
        if hasattr(self, "intraday_chart_view"):
            self.intraday_chart_view.setMinimumHeight(intraday_height)
            chart = self.intraday_chart_view.chart()
            if chart is not None:
                chart.setTitle("市场代理走势" if self.market_timeframe_mode == "日线" else f"{self.market_timeframe_mode} 走势")
        if hasattr(self, "daily_chart_view"):
            self.daily_chart_view.setMinimumHeight(daily_height)
            chart = self.daily_chart_view.chart()
            if chart is not None:
                chart.setTitle("日线主图" if self.market_timeframe_mode == "日线" else f"{self.market_timeframe_mode} 主图")
        if hasattr(self, "fund_chart_view"):
            chart = self.fund_chart_view.chart()
            if chart is not None:
                chart.setTitle("主力资金" if self.market_timeframe_mode == "日线" else f"{self.market_timeframe_mode} 资金")
        if hasattr(self, "momentum_chart_view"):
            chart = self.momentum_chart_view.chart()
            if chart is not None:
                chart.setTitle("龙头动能" if self.market_timeframe_mode == "日线" else f"{self.market_timeframe_mode} 动能")

        if self.active_symbol and self.active_symbol in self.universe_bars:
            self._render_market_dashboard(self.active_symbol)
        elif getattr(self.market_screen_result, "algorithmic_pool", []):
            preferred = self.market_screen_result.algorithmic_pool[0].symbol
            if preferred in self.universe_bars:
                self._render_market_dashboard(preferred)

    def save_state(self) -> None:
        save_app_state(
            STATE_FILE,
            AppState(
                universe_dir=self.state.universe_dir,
                selected_symbol=self.state.selected_symbol,
                watchlist=self.state.watchlist,
                ui_theme=self.current_theme,
                theme_alias_path=self.theme_alias_path,
                recommend_theme_filter=self.recommend_theme_filter,
                market_theme_filter=self.market_theme_filter,
                focus_themes=self.state.focus_themes,
                strategy_top_theme_limit=self.state.strategy_top_theme_limit,
                strategy_max_total_exposure=self.state.strategy_max_total_exposure,
                strategy_theme_drop_reduce=self.state.strategy_theme_drop_reduce,
                license_plan=self.state.license_plan,
                trial_started_at=self.state.trial_started_at,
                auto_daily_plan_export=self.state.auto_daily_plan_export,
                daily_plan_template=self.state.daily_plan_template,
                daily_plan_focus_only=self.state.daily_plan_focus_only,
                daily_plan_candidate_limit=self.state.daily_plan_candidate_limit,
                market_data_mode=self.market_data_mode,
                broker_profile=self.current_broker_profile(),
            ),
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        self.refresh_timer.stop()
        self.thread_pool.waitForDone(1200)
        self.save_state()
        event.accept()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("量化猎手")
    window = QuantHunterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
