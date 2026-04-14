from __future__ import annotations

import csv
import sys
import time as time_module
from dataclasses import replace
from datetime import datetime, time
from pathlib import Path

from PySide6.QtCore import QDateTime, QModelIndex, QObject, QRunnable, Qt, QThreadPool, QTimer, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QColor, QDesktopServices, QFont, QFontDatabase
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
    QSizePolicy,
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
    PaperTradingState,
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
from quant_hunter.paper_trading import (
    PaperTradingEngine,
    build_strategy_rotation_snapshot,
    describe_strategy_experiment,
    export_paper_trading_report,
    should_auto_run_paper_trading,
    summarize_paper_trading_performance,
)
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
from quant_hunter.ui_controllers import refresh_daily_pool_controller, refresh_remote_market_controller, run_background_job_controller, run_parameter_optimization_controller, save_strategy_preferences_controller, switch_license_plan_controller
from quant_hunter.ui_config import (
    DAILY_POOL_TABLE_HEADERS,
    BROKER_DEFAULT_STATUS_TEXT,
    DISPLAY_TEXT,
    OVERVIEW_QUICK_ROUTE_SPECS,
    ORDERS_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_EMPTY_TITLE,
    RECOMMEND_DEFAULT_EMPTY_META,
    RECOMMEND_DEFAULT_FOCUS_TEXT,
    RECOMMEND_DEFAULT_STATUS_TEXT,
    RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
    RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
    STRATEGY_FILTER_LABELS,
    STRATEGY_SCORE_FIELDS,
    TRADE_PLAN_DEFAULT_FOCUS_TEXT,
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
    create_shell_chip,
    one_day_hold_phase_labels,
    one_day_hold_grade,
    position_advice_check_item,
    recommendation_focus_lines,
    set_shell_chip,
    set_button_role,
    style_terminal_console,
    style_terminal_panel,
    tail_buy_runtime_panel_lines,
    tail_buy_runtime_status,
    trade_decision_focus_lines,
    trade_plan_execution_hint,
)
from quant_hunter.ui_binders import apply_daily_pool_rows, apply_market_screen_result, apply_scan_universe_result, handle_daily_pool_error, handle_market_refresh_error, handle_scan_error, refresh_license_status_view
from quant_hunter.ui_refresh import (
    apply_market_filters,
    fill_backtest_summaries,
    fill_order_intents_table,
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
from quant_hunter.ui_window_tail_patches import (
    apply_window_tail_patches,
    build_paper_experiment_lines_v36 as _qh_build_paper_experiment_lines_v36,
    recommend_review_sequence_v36 as _qh_recommend_review_sequence_v36,
    strategy_experiment_verdict_v36 as _qh_strategy_experiment_verdict_v36,
)
from quant_hunter.ui_window_recommend_patches import (
    apply_recommend_workspace_patches,
    recommend_cta_labels_v37 as _qh_recommend_cta_labels_v37,
    recommend_workspace_stage_v37 as _qh_recommend_workspace_stage_v37,
)
from quant_hunter.ui_window_chrome_patches import apply_commercial_chrome_patches
from quant_hunter.ui_window_visibility_patches import (
    apply_workspace_visibility_patches,
    paper_lab_stage_v39 as _qh_paper_lab_stage_v39,
)
from quant_hunter.ui_window_broker_patches import (
    apply_broker_workspace_patches,
    broker_workspace_stage_v40 as _qh_broker_workspace_stage_v40,
    shell_pipeline_story_v41 as _qh_shell_pipeline_story_v41,
)
from quant_hunter.ui_window_workbench_patches import apply_workspace_workbench_patches
from quant_hunter.ui_window_shell_patches import (
    apply_shell_workflow_patches,
    shell_stage_for_workspace_v42 as _qh_shell_stage_for_workspace_v42,
    shell_workflow_stage_specs_v42 as _qh_shell_workflow_stage_specs_v42,
)
from quant_hunter.ui_window_paper_experiment_patches import (
    apply_paper_experiment_patches,
    paper_experiment_role_specs_v43 as _qh_paper_experiment_role_specs_v43,
    paper_experiment_table_context_v44 as _qh_paper_experiment_table_context_v44,
    paper_strategy_experiment_bridge_v45 as _qh_paper_strategy_experiment_bridge_v45,
)
from quant_hunter.ui_window_cross_workspace_focus_patches import apply_cross_workspace_focus_patches
from quant_hunter.ui_window_focus_bridge_patches import apply_focus_bridge_patches
from quant_hunter.ui_window_runtime_feedback_patches import apply_runtime_feedback_patches


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
    QTableWidget#recommendPoolTable {
        background: rgba(12, 16, 22, 0.97);
        border: 1px solid rgba(109, 128, 151, 0.20);
        border-radius: 18px;
        padding: 8px;
        selection-background-color: #182331;
        selection-color: #ffffff;
    }
    QTableWidget#recommendPoolTable::item {
        padding: 7px;
        border-bottom: 1px solid rgba(28, 38, 50, 0.72);
    }
    QTableWidget#marketPoolTable::item:selected,
    QTableWidget#recommendPoolTable::item:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(32, 69, 104, 0.96), stop:1 rgba(25, 39, 55, 0.98));
        color: #ffffff;
    }
    QTableWidget#recommendPoolTable QTableCornerButton::section {
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
        selection-background-color: rgba(38, 85, 130, 0.92);
        line-height: 1.45;
    }
    QTextEdit#marketNotePanel:focus {
        border: 1px solid rgba(126, 183, 255, 0.34);
        background: rgba(15, 21, 29, 0.98);
    }
    QTextEdit#marketNotePanel[stateTone="buy"] {
        border: 1px solid rgba(77, 226, 154, 0.34);
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 49, 35, 0.92), stop:1 rgba(13, 18, 24, 0.96));
    }
    QTextEdit#marketNotePanel[stateTone="watch"] {
        border: 1px solid rgba(255, 209, 102, 0.34);
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(52, 41, 15, 0.92), stop:1 rgba(13, 18, 24, 0.96));
    }
    QTextEdit#marketNotePanel[stateTone="risk"] {
        border: 1px solid rgba(255, 123, 114, 0.34);
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(63, 24, 27, 0.92), stop:1 rgba(13, 18, 24, 0.96));
    }
    QTextEdit#marketNotePanel[stateTone="idle"] {
        border: 1px solid rgba(109, 184, 255, 0.26);
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
    QFrame#shellHeader {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #141b24, stop:0.55 #10161f, stop:1 #0d131b);
        border: 1px solid rgba(118, 140, 168, 0.22);
        border-radius: 22px;
    }
    QFrame#shellBrandBlock {
        background: transparent;
    }
    QLabel#shellProductEyebrow {
        color: #7bb2ff;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    QLabel#shellProductTitle {
        color: #f6f8fb;
        font-size: 20px;
        font-weight: 900;
    }
    QLabel#shellProductSubtitle {
        color: #92a3b7;
        font-size: 12px;
    }
    QFrame#shellChip {
        background: rgba(11, 17, 24, 0.92);
        border: 1px solid rgba(118, 140, 168, 0.18);
        border-radius: 16px;
    }
    QLabel#shellChipLabel {
        color: #7d90a7;
        font-size: 11px;
        font-weight: 700;
    }
    QLabel#shellChipValue {
        color: #f4f7fb;
        font-size: 14px;
        font-weight: 900;
    }
    QFrame#shellPulseBar {
        background: rgba(13, 19, 27, 0.9);
        border: 1px solid rgba(118, 140, 168, 0.14);
        border-radius: 16px;
    }
    QLabel#shellPulseLabel {
        color: #f4f7fb;
        font-size: 12px;
        font-weight: 700;
    }
    QLabel#shellPulseHint {
        color: #8fb5ff;
        font-size: 11px;
        font-weight: 700;
    }
    QLabel#shellPulseMeta {
        color: #7d90a7;
        font-size: 11px;
        font-weight: 700;
    }
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
        border-radius: 20px;
    }
    QLabel#workspaceEyebrow {
        color: #76a9ff;
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1px;
    }
    QLabel#workspaceTitle {
        color: #f6f8fb;
        font-size: 18px;
        font-weight: 900;
    }
    QLabel#workspaceSubtitle {
        color: #93a2b4;
        font-size: 11px;
    }
    QFrame#workspaceBadge {
        background: rgba(13, 20, 31, 0.92);
        border: 1px solid rgba(112, 132, 156, 0.18);
        border-radius: 14px;
    }
    QLabel#workspaceBadgeValue {
        color: #ffd166;
        font-size: 14px;
        font-weight: 900;
    }
    QLabel#workspaceBadgeCaption {
        color: #8392a6;
        font-size: 10px;
        font-weight: 600;
    }
    QLabel#workspaceSummaryHeadline {
        color: #f6fbff;
        font-size: 13px;
        font-weight: 900;
    }
    QLabel#workspaceFocusBanner {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(27, 40, 56, 0.96), stop:1 rgba(16, 24, 34, 0.96));
        color: #eef5ff;
        border: 1px solid rgba(121, 145, 171, 0.22);
        border-left: 4px solid #6db8ff;
        border-radius: 14px;
        padding: 10px 14px;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#workspaceFocusBanner[stateTone="buy"] {
        border-left: 4px solid #4de29a;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(18, 49, 35, 0.96), stop:1 rgba(16, 24, 34, 0.96));
    }
    QLabel#workspaceFocusBanner[stateTone="watch"] {
        border-left: 4px solid #ffd166;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(52, 41, 15, 0.96), stop:1 rgba(16, 24, 34, 0.96));
    }
    QLabel#workspaceFocusBanner[stateTone="risk"] {
        border-left: 4px solid #ff7b72;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(63, 24, 27, 0.96), stop:1 rgba(16, 24, 34, 0.96));
    }
    QLabel#workspaceFocusBanner[stateTone="idle"] {
        border-left: 4px solid #6db8ff;
    }
    QGroupBox#workspaceToolPanel {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #17212d, stop:1 #111821);
        border: 1px solid rgba(123, 145, 170, 0.22);
        border-radius: 18px;
        margin-top: 16px;
        padding: 16px 14px 12px 14px;
    }
    QGroupBox#workspaceToolPanel::title {
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: #f1f5fb;
        font-weight: 800;
    }
    QLabel#statusBanner {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(25, 36, 48, 0.98), stop:1 rgba(17, 24, 32, 0.98));
        color: #eef4fb;
        border: 1px solid rgba(126, 151, 179, 0.24);
        border-left: 4px solid #ffd166;
        border-radius: 14px;
        padding: 10px 14px;
        font-size: 12px;
        font-weight: 800;
    }
    QLabel#focusStateLabel {
        background: rgba(16, 23, 31, 0.9);
        color: #f5f8fc;
        border: 1px solid rgba(113, 133, 156, 0.18);
        border-radius: 12px;
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
    }
    QLabel#emptyStateMeta {
        color: #9aaaba;
        font-size: 12px;
        line-height: 1.4;
        padding: 2px 4px;
    }
    QFrame#emptyActionBar {
        background: rgba(14, 20, 28, 0.92);
        border: 1px solid rgba(113, 133, 156, 0.16);
        border-radius: 14px;
    }
    QGroupBox#terminalPanel {
        background: rgba(22, 30, 40, 0.96);
        border: 1px solid rgba(111, 130, 153, 0.18);
        border-radius: 16px;
        margin-top: 16px;
        padding: 16px 14px 12px 14px;
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
        border-radius: 14px;
        padding: 10px;
        color: #dfe7f1;
    }
    QLabel#inlineHint {
        color: #90a0b3;
        font-size: 11px;
    }
    QTabWidget#compactInfoTabs::pane {
        border: 1px solid rgba(112, 130, 153, 0.18);
        border-radius: 16px;
        background: rgba(14, 19, 27, 0.92);
        top: -1px;
    }
    QTabWidget#compactInfoTabs QTabBar::tab {
        background: rgba(25, 33, 44, 0.86);
        color: #98aabc;
        border: 1px solid rgba(112, 130, 153, 0.14);
        border-bottom: none;
        padding: 9px 16px;
        margin-right: 6px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        font-weight: 700;
    }
    QTabWidget#compactInfoTabs QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(45, 72, 102, 0.98), stop:1 rgba(29, 46, 66, 0.98));
        color: #f6fbff;
        border-color: rgba(126, 183, 255, 0.24);
    }
    QTabWidget#compactInfoTabs QTabBar::tab:hover:!selected {
        color: #dce8f5;
        background: rgba(32, 42, 55, 0.94);
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
        updates_enabled = self.order_table.updatesEnabled()
        self.order_table.setUpdatesEnabled(False)
        self.order_table.blockSignals(True)
        try:
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
        finally:
            self.order_table.blockSignals(False)
            self.order_table.setUpdatesEnabled(updates_enabled)
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
    table.setWordWrap(False)
    table.setTextElideMode(Qt.ElideRight)
    table.verticalHeader().setDefaultSectionSize(42)
    table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    table.setFrameShape(QFrame.NoFrame)
    table.setCornerButtonEnabled(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
    table.horizontalHeader().setFixedHeight(46)
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
        QApplication.setApplicationName("量化猎手")
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
        self.recommend_strategy_filter = self.state.recommend_strategy_filter or "全部"
        self.recommend_action_filter = self.state.recommend_action_filter or "全部"
        self.recommend_execution_filter = self.state.recommend_execution_filter or "全部"
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
        self._symbol_data_revision = 0
        self._last_rendered_symbol = ""
        self._last_rendered_symbol_revision = -1
        self._pending_market_dashboard_symbol = ""
        self.last_runtime_export_path = ""
        self.last_cache_purge_summary = ""
        self.overview_focus_mode = "市场总览"
        self.market_timeframe_mode = "日线"
        self.market_history_window = "近1年"
        self.market_history_date = "最新"
        self.market_chart_offset = 0
        self.market_overlay_modes: set[str] = {"MA", "BOLL"}
        self.market_secondary_indicator_mode = "MACD"

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
        shell_root = QWidget()
        shell_layout = QVBoxLayout(shell_root)
        shell_layout.setContentsMargins(12, 10, 12, 12)
        shell_layout.setSpacing(10)
        self.setCentralWidget(shell_root)

        self.shell_header = QFrame()
        self.shell_header.setObjectName("shellHeader")
        shell_header_layout = QHBoxLayout(self.shell_header)
        shell_header_layout.setContentsMargins(18, 12, 18, 12)
        shell_header_layout.setSpacing(14)

        shell_brand_block = QFrame()
        shell_brand_block.setObjectName("shellBrandBlock")
        shell_brand_layout = QVBoxLayout(shell_brand_block)
        shell_brand_layout.setContentsMargins(0, 0, 0, 0)
        shell_brand_layout.setSpacing(2)
        self.shell_product_eyebrow = QLabel("INSTITUTIONAL DECISION & EXECUTION TERMINAL")
        self.shell_product_eyebrow.setObjectName("shellProductEyebrow")
        self.shell_product_title = QLabel("量化猎手 Pro")
        self.shell_product_title.setObjectName("shellProductTitle")
        self.shell_product_subtitle = QLabel("把主线判断、候选推荐、风险控制、交易执行与收盘复盘收束进同一张机构级工作台。")
        self.shell_product_subtitle.setObjectName("shellProductSubtitle")
        self.shell_product_subtitle.setWordWrap(True)
        shell_brand_layout.addWidget(self.shell_product_eyebrow)
        shell_brand_layout.addWidget(self.shell_product_title)
        shell_brand_layout.addWidget(self.shell_product_subtitle)
        shell_header_layout.addWidget(shell_brand_block, stretch=3)

        shell_chip_rail = QWidget()
        shell_chip_layout = QHBoxLayout(shell_chip_rail)
        shell_chip_layout.setContentsMargins(0, 0, 0, 0)
        shell_chip_layout.setSpacing(10)
        self.shell_workspace_chip = create_shell_chip("当前页面", "龙头主控台")
        self.shell_market_chip = create_shell_chip("行情通道", "等待行情接入")
        self.shell_pipeline_chip = create_shell_chip("今日流程", "市场待刷新")
        self.shell_refresh_chip = create_shell_chip("自动刷新", "待机")
        self.shell_runtime_chip = create_shell_chip("运行状态", "空闲")
        for chip in (
            self.shell_workspace_chip,
            self.shell_market_chip,
            self.shell_pipeline_chip,
            self.shell_refresh_chip,
            self.shell_runtime_chip,
        ):
            shell_chip_layout.addWidget(chip["frame"])
        shell_chip_layout.addStretch(1)
        shell_header_layout.addWidget(shell_chip_rail, stretch=4)
        shell_layout.addWidget(self.shell_header)

        self.shell_pulse_bar = QFrame()
        self.shell_pulse_bar.setObjectName("shellPulseBar")
        shell_pulse_layout = QHBoxLayout(self.shell_pulse_bar)
        shell_pulse_layout.setContentsMargins(16, 10, 16, 10)
        shell_pulse_layout.setSpacing(10)
        self.shell_pulse_label = QLabel("系统脉搏：终端正在等待市场快照、候选优先级与交易链路完成同步")
        self.shell_pulse_label.setObjectName("shellPulseLabel")
        self.shell_pulse_hint = QLabel("下一步：先建立市场快照，再确认主线窗口、候选优先级与待审委托。")
        self.shell_pulse_hint.setObjectName("shellPulseHint")
        self.shell_pulse_meta = QLabel("运行透明度：等待首轮终端快照")
        self.shell_pulse_meta.setObjectName("shellPulseMeta")
        self.shell_pulse_meta.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        shell_pulse_layout.addWidget(self.shell_pulse_label, stretch=5)
        shell_pulse_layout.addWidget(self.shell_pulse_hint, stretch=4)
        shell_pulse_layout.addWidget(self.shell_pulse_meta, stretch=3)
        shell_layout.addWidget(self.shell_pulse_bar)

        self.tabs = QTabWidget()
        shell_layout.addWidget(self.tabs, stretch=1)

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
        self.top_badge = QLabel("机构级终端")
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
        if hasattr(self, "recommend_status_label"):
            self.recommend_status_label.setText("正在保存策略配置并刷新推荐与监控...")
        save_strategy_preferences_controller(self, info_dialog_fn=QMessageBox.information)

    def _refresh_license_status_view(self) -> None:
        if not hasattr(self, "license_status_text"):
            return
        started = self.state.trial_started_at or datetime.now().date().isoformat()
        try:
            start_date = datetime.strptime(started, "%Y-%m-%d").date()
        except ValueError:
            start_date = datetime.now().date()
        days_used = max((datetime.now().date() - start_date).days, 0)
        trial_days = 14
        remaining = max(trial_days - days_used, 0)
        capabilities = self._license_capabilities()
        plan = str(capabilities.get("plan", self.state.license_plan or "TRIAL")).upper()
        plan_label = {
            "TRIAL": "试用版",
            "PRO": "专业版",
            "ENTERPRISE": "企业版",
        }.get(plan, plan)
        lines = [
            "授权与状态",
            f"- 当前方案：{plan_label} ({plan})",
            f"- 试用开始：{start_date.isoformat()}",
            f"- 试用剩余：{remaining} 天",
            f"- 版本能力：自动盘前报告 {'开启' if capabilities.get('auto_daily_plan_export') else '关闭'}，盘前候选上限 {int(capabilities.get('daily_plan_export_limit', 0))} 只",
            f"- 关注题材：{', '.join(self.state.focus_themes) if self.state.focus_themes else '未设置'}",
            f"- 主线题材阈值：前 {self.state.strategy_top_theme_limit}",
            f"- 题材加权：{float(capabilities.get('focus_theme_boost', 0.0)):.0f}",
            f"- 盘前模板：{self.state.daily_plan_template}",
            f"- 模板仅关注题材：{'是' if self.state.daily_plan_focus_only else '否'}",
            f"- 盘前股票池上限：{min(self.state.daily_plan_candidate_limit, int(capabilities.get('daily_plan_export_limit', self.state.daily_plan_candidate_limit)))}",
            f"- 市场历史回看深度：{int(capabilities.get('market_history_limit', 0))}",
            f"- 监控摘要容量：{int(capabilities.get('monitor_summary_limit', 0))}",
            f"- 自动盘前报告：{'开启' if self.state.auto_daily_plan_export and bool(capabilities.get('auto_daily_plan_export')) else '关闭'}",
            "",
            "说明",
        ]
        if plan == "ENTERPRISE":
            lines.append("- 企业版已启用：自动盘前报告、增强题材加权和扩展题材面板。")
        elif plan == "PRO":
            lines.append("- 专业版已启用：自动盘前报告和题材优先加权已开放。")
        else:
            lines.append("- 试用版保留手动研究流程，自动盘前报告保持关闭。")
        lines.append("- 切换版本、保存配置或刷新市场后，状态会自动同步。")
        self._set_plain_text_if_changed(self.license_status_text, "\n".join(lines))

    def activate_professional_plan(self) -> None:
        switch_license_plan_controller(self, "PRO", datetime_cls=datetime)

    def reset_trial_plan(self) -> None:
        switch_license_plan_controller(self, "TRIAL", datetime_cls=datetime)

    def activate_enterprise_plan(self) -> None:
        switch_license_plan_controller(self, "ENTERPRISE", datetime_cls=datetime)

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
                ["股票名称", "股票ID", "交易代码", "交易笔数", "收益率", "最大回撤", "胜率", "期末权益"]
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
        self._refresh_broker_status(extra="账户连接已更新。")
        QMessageBox.information(self, "提示", "账户连接已保存。")

    def _refresh_login_status(self) -> None:
        if not hasattr(self, "login_status_text"):
            return
        profile = self.current_broker_profile() if "account_name" in self.broker_inputs else self.state.broker_profile
        channel_text = self.auth_channel_combo.currentText() if hasattr(self, "auth_channel_combo") else "东方财富"
        mode_text = self._display_mode(profile.mode) if hasattr(self, "_display_mode") else profile.mode
        lines = [
            "登录与通道说明",
            f"- 当前通道：{channel_text}",
            f"- 账户名称：{profile.account_name or '未填写'}",
            f"- 登录账号：{profile.username or '未填写'}",
            f"- 账户 ID：{profile.account_id or '未填写'}",
            f"- 委托模式：{mode_text or '未填写'}",
            f"- 策略 ID：{profile.strategy_id or '未填写'}",
            f"- SDK Token：{'已填写' if profile.token else '未填写'}",
            "",
            "安全边界",
            "- 本程序只保存和展示配置，不会绕过券商安全校验。",
            "- 真实下单仍通过 GM SDK / 桥接脚本执行，并保留人工确认。",
            "- 后续如果增加新通道，可以在这里继续扩展。",
        ]
        self._set_plain_text_if_changed(self.login_status_text, "\n".join(lines))

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
        self.recommend_status_label.setText(f"已导入题材词典：{len(self.theme_aliases)} 个主题")
        self.save_state()
        self.refresh_daily_pool()

    def open_theme_alias_editor(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("编辑题材词典")
        dialog.resize(760, 540)
        layout = QVBoxLayout(dialog)

        intro = QLabel("按 CSV 形式编辑题材词典，格式为 `theme_name,keywords`。关键词使用英文逗号分隔。")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        editor = QTextEdit(dialog)
        self._set_plain_text_if_changed(editor, self._theme_aliases_to_csv_text())
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
        self.recommend_status_label.setText(f"已保存题材词典：{len(self.theme_aliases)} 个主题")
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
        self.recommend_status_label.setText("已载入示例资料：" + "；".join(loaded_parts))
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
        trade_plan_signature = tuple(
            (
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
            )
            for item in plan.decisions
        )
        if getattr(self, "_trade_plan_table_signature_v1", None) != trade_plan_signature:
            trade_updates_enabled = self.trade_plan_table.updatesEnabled()
            self.trade_plan_table.setUpdatesEnabled(False)
            self.trade_plan_table.blockSignals(True)
            try:
                self.trade_plan_table.setRowCount(len(plan.decisions))
                for row_index, row_values in enumerate(trade_plan_signature):
                    for column, value in enumerate(row_values):
                        self.trade_plan_table.setItem(row_index, column, QTableWidgetItem(value))
            finally:
                self.trade_plan_table.blockSignals(False)
                self.trade_plan_table.setUpdatesEnabled(trade_updates_enabled)
            self._trade_plan_table_signature_v1 = trade_plan_signature
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
            self._set_plain_text_if_changed(self.trade_plan_text, "\n".join(lines))
        if hasattr(self, "market_pulse_text"):
            pulse = plan.market_pulse
            self._set_plain_text_if_changed(
                self.market_pulse_text,
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
            advice_signature = tuple(
                (
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    self._display_action(item.action),
                    f"{item.confidence:.0%}",
                    f"{item.current_price:.2f}",
                    f"{item.cost_price:.2f}",
                    f"{item.pnl_pct:.2%}",
                    item.rationale,
                )
                for item in plan.position_advice
            )
            if getattr(self, "_position_advice_table_signature_v1", None) != advice_signature:
                advice_updates_enabled = self.position_advice_table.updatesEnabled()
                self.position_advice_table.setUpdatesEnabled(False)
                self.position_advice_table.blockSignals(True)
                try:
                    self.position_advice_table.setRowCount(len(plan.position_advice))
                    for row_index, row_values in enumerate(advice_signature):
                        for column, value in enumerate(row_values):
                            self.position_advice_table.setItem(row_index, column, QTableWidgetItem(value))
                finally:
                    self.position_advice_table.blockSignals(False)
                    self.position_advice_table.setUpdatesEnabled(advice_updates_enabled)
                self._position_advice_table_signature_v1 = advice_signature
        if hasattr(self, "position_advice_text"):
            if plan.position_advice:
                sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")
                reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
                hold_count = sum(1 for item in plan.position_advice if item.action == "HOLD")
                self._set_plain_text_if_changed(
                    self.position_advice_text,
                    "\n".join(
                        [
                            f"持仓处置概览：卖出 {sell_count} 只，减仓 {reduce_count} 只，继续持有 {hold_count} 只。",
                            "说明：出现诱多陷阱、跌破防守位或高位浮盈回落时，会优先给出减仓/卖出建议。",
                        ]
                    )
                )
            else:
                self._set_plain_text_if_changed(
                    self.position_advice_text,
                    "当前没有持仓数据，导入持仓 CSV 后会显示卖出 / 格局建议。"
                )

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
            "theme": ("主线稳定", "等待主线强度、位次或风险灯变化后更新提醒。"),
            "leader": ("焦点稳定", "等待前排焦点或龙头位次变化后更新提醒。"),
            "strategy": ("策略稳定", "等待高优先策略切换后更新提醒。"),
            "action": ("动作稳定", "等待交易动作或链路阶段变化后更新提醒。"),
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
            self._sync_scanner_selection(symbol, "scan")
            self.select_symbol(symbol)
            self._refresh_monitor_summary(symbol)
            self._refresh_scanner_focus_status(symbol)
            self._refresh_scanner_summary_cards(symbol)

    def on_watchlist_selected(self) -> None:
        symbol = self._selected_symbol_from_watchlist()
        if symbol and symbol in self.universe_bars:
            self._sync_scanner_selection(symbol, "watchlist")
            self.select_symbol(symbol)
            self._refresh_monitor_summary(symbol)
            self._refresh_scanner_focus_status(symbol)
            self._refresh_scanner_summary_cards(symbol)

    def on_summary_selected(self) -> None:
        if not hasattr(self, "summary_table"):
            return
        row = self.summary_table.currentRow()
        if row < 0:
            return
        item = self.summary_table.item(row, 2)
        symbol = item.text() if item else ""
        if symbol:
            self._sync_scanner_selection(symbol, "summary")
            if symbol in self.universe_bars:
                self.select_symbol(symbol)
            self._refresh_monitor_summary(symbol)
            self._refresh_scanner_focus_status(symbol)
            self._refresh_scanner_summary_cards(symbol)

    def on_monitor_selected(self) -> None:
        if not hasattr(self, "monitor_table"):
            return
        row = self.monitor_table.currentRow()
        if row < 0:
            return
        item = self.monitor_table.item(row, 2)
        symbol = item.text() if item else ""
        if symbol and symbol in self.universe_bars:
            self._sync_scanner_selection(symbol, "monitor")
            self.select_symbol(symbol)
        self._refresh_monitor_summary(symbol)
        self._refresh_scanner_focus_status(symbol)
        self._refresh_scanner_summary_cards(symbol)

    def _selected_symbol_from_scan(self) -> str:
        row = self.scan_table.currentRow()
        if row < 0:
            return ""
        item = self.scan_table.item(row, 2)
        return item.text() if item else ""

    def _selected_symbol_from_watchlist(self) -> str:
        item = self.watchlist_widget.currentItem()
        return item.text() if item else ""

    def _select_watchlist_symbol(self, symbol: str) -> None:
        if not symbol or not hasattr(self, "watchlist_widget"):
            return
        for index in range(self.watchlist_widget.count()):
            item = self.watchlist_widget.item(index)
            if item and item.text() == symbol:
                if self.watchlist_widget.currentRow() == index:
                    return
                self.watchlist_widget.blockSignals(True)
                self.watchlist_widget.setCurrentRow(index)
                self.watchlist_widget.blockSignals(False)
                break

    def _select_table_row_if_needed(self, table: QTableWidget | None, row_index: int) -> bool:
        if not isinstance(table, QTableWidget) or row_index < 0:
            return False
        if table.currentRow() == row_index and table.selectionModel() is not None and table.selectionModel().isRowSelected(row_index, QModelIndex()):
            return False
        table.blockSignals(True)
        table.selectRow(row_index)
        table.blockSignals(False)
        return True

    def _select_market_pool_row_for_symbol(self, symbol: str) -> bool:
        if not symbol or not hasattr(self, "market_pool_table"):
            return False
        for row_index in range(self.market_pool_table.rowCount()):
            item = self.market_pool_table.item(row_index, 0)
            if item and item.data(Qt.UserRole) == symbol:
                return self._select_table_row_if_needed(self.market_pool_table, row_index)
        return False

    def _sync_symbol_across_workspaces(self, symbol: str, origin: str = "") -> None:
        if not symbol:
            return
        if origin != "overview":
            self._select_market_pool_row_for_symbol(symbol)
        if origin != "scanner":
            self._sync_scanner_selection(symbol)
        if origin != "recommend":
            self._select_daily_pool_row_by_stock_id(self._stock_id_for_symbol(symbol))
        if origin != "board":
            self._select_board_candidate_row_for_symbol(symbol)
            self._select_board_monitor_row_for_symbol(symbol)

    def _select_monitor_row_for_symbol(self, symbol: str) -> None:
        if not symbol or not hasattr(self, "monitor_table"):
            return
        for row_index in range(self.monitor_table.rowCount()):
            item = self.monitor_table.item(row_index, 2)
            if item and item.text() == symbol:
                self._select_table_row_if_needed(self.monitor_table, row_index)
                break

    def _select_scan_row_for_symbol(self, symbol: str) -> None:
        if not symbol or not hasattr(self, "scan_table"):
            return
        for row_index in range(self.scan_table.rowCount()):
            item = self.scan_table.item(row_index, 2)
            if item and item.text() == symbol:
                self._select_table_row_if_needed(self.scan_table, row_index)
                break

    def _select_summary_row_for_symbol(self, symbol: str) -> None:
        if not symbol or not hasattr(self, "summary_table"):
            return
        for row_index in range(self.summary_table.rowCount()):
            item = self.summary_table.item(row_index, 2)
            if item and item.text() == symbol:
                self._select_table_row_if_needed(self.summary_table, row_index)
                break

    def _sync_scanner_selection(self, symbol: str, source: str = "") -> None:
        if not symbol:
            return
        if source != "scan":
            self._select_scan_row_for_symbol(symbol)
        if source != "watchlist":
            self._select_watchlist_symbol(symbol)
        if source != "summary":
            self._select_summary_row_for_symbol(symbol)
        if source != "monitor":
            self._select_monitor_row_for_symbol(symbol)

    def _board_candidate_row_for_symbol(self, symbol: str) -> int:
        if not symbol or not hasattr(self, "board_table"):
            return -1
        for row_index in range(self.board_table.rowCount()):
            item = self.board_table.item(row_index, 2)
            if item and item.text() == symbol:
                return row_index
        return -1

    def _board_monitor_row_for_symbol(self, symbol: str) -> int:
        if not symbol or not hasattr(self, "board_monitor_table"):
            return -1
        for row_index in range(self.board_monitor_table.rowCount()):
            item = self.board_monitor_table.item(row_index, 2)
            if item and item.text() == symbol:
                return row_index
        return -1

    def _select_board_candidate_row_for_symbol(self, symbol: str) -> bool:
        row_index = self._board_candidate_row_for_symbol(symbol)
        if row_index < 0:
            return False
        return self._select_table_row_if_needed(self.board_table, row_index)

    def _select_board_monitor_row_for_symbol(self, symbol: str) -> bool:
        row_index = self._board_monitor_row_for_symbol(symbol)
        if row_index < 0:
            return False
        return self._select_table_row_if_needed(self.board_monitor_table, row_index)

    def _board_candidate_snapshot_for_symbol(self, symbol: str) -> dict[str, str] | None:
        row_index = self._board_candidate_row_for_symbol(symbol)
        if row_index < 0:
            return None
        return {
            "stock_name": self.board_table.item(row_index, 0).text() if self.board_table.item(row_index, 0) else self._stock_name_for_symbol(symbol),
            "stock_id": self.board_table.item(row_index, 1).text() if self.board_table.item(row_index, 1) else self._stock_id_for_symbol(symbol),
            "symbol": symbol,
            "board_score": self.board_table.item(row_index, 3).text() if self.board_table.item(row_index, 3) else "--",
            "trigger_style": self.board_table.item(row_index, 7).text() if self.board_table.item(row_index, 7) else "待确认",
            "risk_level": self.board_table.item(row_index, 8).text() if self.board_table.item(row_index, 8) else "待评估",
            "planned_entry": self.board_table.item(row_index, 9).text() if self.board_table.item(row_index, 9) else "--",
            "planned_stop": self.board_table.item(row_index, 10).text() if self.board_table.item(row_index, 10) else "--",
            "planned_target": self.board_table.item(row_index, 11).text() if self.board_table.item(row_index, 11) else "--",
        }

    def _board_monitor_snapshot_for_symbol(self, symbol: str) -> dict[str, str] | None:
        row_index = self._board_monitor_row_for_symbol(symbol)
        if row_index < 0:
            return None
        return {
            "stock_name": self.board_monitor_table.item(row_index, 0).text() if self.board_monitor_table.item(row_index, 0) else self._stock_name_for_symbol(symbol),
            "stock_id": self.board_monitor_table.item(row_index, 1).text() if self.board_monitor_table.item(row_index, 1) else self._stock_id_for_symbol(symbol),
            "symbol": symbol,
            "monitor_state": self.board_monitor_table.item(row_index, 3).text() if self.board_monitor_table.item(row_index, 3) else "待观察",
            "strength": self.board_monitor_table.item(row_index, 4).text() if self.board_monitor_table.item(row_index, 4) else "--",
            "continuity": self.board_monitor_table.item(row_index, 5).text() if self.board_monitor_table.item(row_index, 5) else "--",
            "action_plan": self.board_monitor_table.item(row_index, 8).text() if self.board_monitor_table.item(row_index, 8) else "等待监控",
            "note": self.board_monitor_table.item(row_index, 9).text() if self.board_monitor_table.item(row_index, 9) else "等待监控链路同步",
        }

    def _refresh_monitor_summary(self, symbol: str = "") -> None:
        if not hasattr(self, "monitor_summary_text"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会跟踪观察池和焦点票的最新动作、信号、催化与推荐联动。\n"
                "先执行扫描或从观察池选中一只股票，下面会自动切换到对应摘要。"
            )
            self._refresh_scanner_focus_status("")
            self._refresh_scanner_focus_cards("")
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        stock_name = self._stock_name_for_symbol(target)
        stock_id = self._stock_id_for_symbol(target)

        lines = [f"盘中焦点：{stock_name} ({stock_id} / {target})"]
        if scan_row is not None:
            lines.append(f"动作：{self._display_action(scan_row.action)} | 信号：{self._display_label(scan_row.label)} | 分数：{scan_row.score}")
            lines.append(f"收盘价：{scan_row.close:.2f} | 信号日期：{scan_row.signal_date}")
            if scan_row.reason:
                lines.append(f"原因：{scan_row.reason}")
        elif latest is not None:
            lines.append(f"最新信号：{self._display_label(latest.label)} | 分数：{latest.score} | 收盘价：{latest.close:.2f}")
            if latest.reason:
                lines.append(f"原因：{latest.reason}")
        else:
            lines.append("当前没有盘中信号，等待扫描链路同步。")

        if recommendation is not None:
            lines.append(
                f"推荐联动：{self._display_action(recommendation.action)} | 主线 {recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 分层 {recommendation.opportunity_tier or '待确认'}"
            )
            lines.append(f"催化：{recommendation.catalyst or '等待消息催化'}")
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        if board_candidate is not None:
            lines.append(
                f"打板联动：{board_candidate['trigger_style']} | 风险 {board_candidate['risk_level']} | 入场 {board_candidate['planned_entry']} | 止损 {board_candidate['planned_stop']} | 目标 {board_candidate['planned_target']}"
            )
        board_monitor = self._board_monitor_snapshot_for_symbol(target)
        if board_monitor is not None:
            lines.append(
                f"打板监控：{board_monitor['monitor_state']} | 强度 {board_monitor['strength']} | 连续性 {board_monitor['continuity']}"
            )
        self._set_plain_text_if_changed(self.monitor_summary_text, "\n".join(lines))
        self._refresh_scanner_focus_status(target)
        self._refresh_scanner_focus_cards(target)
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_status(self, symbol: str = "") -> None:
        if not hasattr(self, "scan_summary_label"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        total_scans = len(getattr(self, "scan_rows", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        if not target:
            if total_scans:
                self._set_label_text_if_changed(
                    self.scan_summary_label,
                    f"已扫描 {total_scans} 条信号 | 观察池 {watch_count} | 监控 {monitor_count}",
                )
            else:
                self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。")
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        stock_name = self._stock_name_for_symbol(target)
        if scan_row is not None:
            action_text = self._display_action(getattr(scan_row, "action", "WATCH"))
            signal_text = self._display_label(getattr(scan_row, "label", "WATCH"))
            board_candidate = self._board_candidate_snapshot_for_symbol(target)
            board_piece = (
                f" | 打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} / 分数 {board_candidate['board_score']}"
                if board_candidate is not None
                else ""
            )
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | {action_text} / {signal_text} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count}{board_piece}"
            )
            self._refresh_scanner_summary_cards(target)
            return
        if recommendation is not None:
            board_candidate = self._board_candidate_snapshot_for_symbol(target)
            board_piece = (
                f" | 打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} / 分数 {board_candidate['board_score']}"
                if board_candidate is not None
                else ""
            )
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | 推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} | 主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}{board_piece}"
            )
            self._refresh_scanner_summary_cards(target)
            return
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_piece = (
            f" | 打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} / 分数 {board_candidate['board_score']}"
            if board_candidate is not None
            else ""
        )
        self._set_label_text_if_changed(
            self.scan_summary_label,
            f"当前焦点：{stock_name} | 已纳入工作台联动 | 监控 {monitor_count}{board_piece}",
        )
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_focus_metric_labels", None)
        accents = getattr(self, "scanner_focus_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_label_text_if_changed(labels["symbol"], "--")
            self._set_label_text_if_changed(accents["symbol"], "等待选中")
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "等待扫描")
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待联动")
            self._set_label_text_if_changed(labels["monitor"], "待刷新")
            self._set_label_text_if_changed(accents["monitor"], "等待盘中监控")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        stock_name = self._stock_name_for_symbol(target)
        self._set_label_text_if_changed(labels["symbol"], stock_name)
        self._set_label_text_if_changed(accents["symbol"], self._stock_id_for_symbol(target))
        if scan_row is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(scan_row, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(scan_row, "label", "WATCH")))
            board_candidate = self._board_candidate_snapshot_for_symbol(target)
            if board_candidate is not None:
                self._set_label_text_if_changed(labels["monitor"], board_candidate["trigger_style"])
                self._set_label_text_if_changed(accents["monitor"], f"风险 {board_candidate['risk_level']} | 分数 {board_candidate['board_score']}")
            else:
                self._set_label_text_if_changed(labels["monitor"], "已联动")
                self._set_label_text_if_changed(accents["monitor"], f"信号日 {getattr(scan_row, 'signal_date', '--')}")
        elif latest is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(latest, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(latest, "label", "WATCH")))
            board_candidate = self._board_candidate_snapshot_for_symbol(target)
            if board_candidate is not None:
                self._set_label_text_if_changed(labels["monitor"], board_candidate["trigger_style"])
                self._set_label_text_if_changed(accents["monitor"], f"风险 {board_candidate['risk_level']} | 分数 {board_candidate['board_score']}")
            else:
                self._set_label_text_if_changed(labels["monitor"], "已跟踪")
                self._set_label_text_if_changed(accents["monitor"], "来自历史信号")
        else:
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "暂无信号")
            board_candidate = self._board_candidate_snapshot_for_symbol(target)
            if board_candidate is not None:
                self._set_label_text_if_changed(labels["monitor"], board_candidate["trigger_style"])
                self._set_label_text_if_changed(accents["monitor"], f"风险 {board_candidate['risk_level']} | 分数 {board_candidate['board_score']}")
            else:
                self._set_label_text_if_changed(labels["monitor"], "待刷新")
                self._set_label_text_if_changed(accents["monitor"], "等待盘中监控")

        if recommendation is not None:
            self._set_label_text_if_changed(labels["action"], self._display_action(getattr(recommendation, "action", "WATCH")))
            self._set_label_text_if_changed(
                accents["action"],
                f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}"
            )
        else:
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待推荐池联动")

    def _refresh_scanner_summary_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_summary_metric_labels", None)
        accents = getattr(self, "scanner_summary_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        scan_count = len(getattr(self, "scan_rows", []))
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        summary_count = len(getattr(self, "backtest_summaries", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        self._set_label_text_if_changed(labels["scan"], str(scan_count) if scan_count else "0")
        self._set_label_text_if_changed(labels["watch"], str(watch_count) if watch_count else "0")
        self._set_label_text_if_changed(labels["summary"], str(summary_count) if summary_count else "0")
        self._set_label_text_if_changed(labels["monitor"], str(monitor_count) if monitor_count else "0")
        if not target:
            self._set_label_text_if_changed(accents["scan"], "等待首轮扫描")
            self._set_label_text_if_changed(accents["watch"], "等待观察池")
            self._set_label_text_if_changed(accents["summary"], "等待回测摘要")
            self._set_label_text_if_changed(accents["monitor"], "等待盘中联动")
            return

        stock_name = self._stock_name_for_symbol(target)
        stock_id = self._stock_id_for_symbol(target)
        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        latest_summary = next((item for item in getattr(self, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_monitor = self._board_monitor_snapshot_for_symbol(target)

        self._set_label_text_if_changed(accents["scan"], f"{stock_name} / {stock_id}" if scan_row is not None else f"焦点 {stock_name}")
        if recommendation is not None:
            self._set_label_text_if_changed(
                accents["watch"],
                f"推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}"
            )
        else:
            self._set_label_text_if_changed(accents["watch"], "观察池联动")
        if latest_summary is not None:
            self._set_label_text_if_changed(accents["summary"], f"回测 {latest_summary.trades} 笔 / 收益 {latest_summary.total_return:.2%}")
        else:
            self._set_label_text_if_changed(accents["summary"], "等待样本回填")
        if board_candidate is not None:
            self._set_label_text_if_changed(accents["monitor"], f"打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']}")
        elif board_monitor is not None:
            self._set_label_text_if_changed(accents["monitor"], f"监控 {board_monitor['monitor_state']} / {board_monitor['strength']}")
        else:
            self._set_label_text_if_changed(accents["monitor"], "盘中监控联动")

    def _focus_symbol_in_recommend_workspace(self, symbol: str) -> None:
        if not symbol:
            return
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == symbol), None)
        self._navigate_to_workspace("recommend", "daily_pool_table")
        if recommendation is not None:
            self._select_daily_pool_row_by_stock_id(recommendation.stock_id)

    def _focus_symbol_in_broker_workspace(self, symbol: str) -> None:
        if not symbol:
            return
        self._queue_symbol_to_watchlist(symbol)
        self.generate_order_suggestions()
        self._navigate_to_workspace("broker", "orders_table")
        self._refresh_broker_order_focus()
        self._refresh_submission_focus()

    def open_monitor_symbol_in_overview(self) -> None:
        symbol = self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not symbol:
            return
        if symbol in self.universe_bars:
            self.select_symbol(symbol)
        self._navigate_to_workspace("overview", "market_pool_table")

    def open_monitor_symbol_in_recommend(self) -> None:
        symbol = self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not symbol:
            return
        self._focus_symbol_in_recommend_workspace(symbol)

    def open_monitor_symbol_in_broker(self) -> None:
        symbol = self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not symbol:
            return
        self._focus_symbol_in_broker_workspace(symbol)

    def open_monitor_symbol_in_board(self) -> None:
        symbol = self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not symbol:
            self._navigate_to_workspace("board", "board_table")
            return
        self._select_board_candidate_row_for_symbol(symbol)
        self._select_board_monitor_row_for_symbol(symbol)
        self._navigate_to_workspace("board", "board_table")
        self._refresh_board_focus_panels(symbol)

    def open_overview_theme_to_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")

    def open_overview_source_to_news(self) -> None:
        self.activate_overview_quick_action("消息催化")

    def open_overview_capital_to_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "theme_heat_table", "daily_pool_table")

    def open_overview_decision_to_broker(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_broker_workspace(symbol)
        else:
            self._navigate_to_workspace("broker", "orders_table")

    def _selected_board_symbol(self) -> str:
        for table_name in ["board_table", "board_monitor_table"]:
            table = getattr(self, table_name, None)
            if table is None:
                continue
            row = table.currentRow()
            if row < 0:
                continue
            item = table.item(row, 2)
            if item and item.text():
                return item.text()
        return ""

    def _refresh_board_focus_panels(self, symbol: str = "") -> None:
        target_symbol = symbol or self._selected_board_symbol()
        if not target_symbol:
            if hasattr(self, "board_text"):
                self._set_plain_text_if_changed(
                    self.board_text,
                    "打板候选池\n\n"
                    "这里会汇总强势连板、回封质量、入场价位和风险等级。\n"
                    "先生成推荐池或在扫描页选中一只股票，这里会自动切到对应打板焦点。\n"
                    "打板页会优先展示主线前排、接力确定性和可执行的回封区间。"
                )
            if hasattr(self, "board_monitor_text"):
                self._set_plain_text_if_changed(
                    self.board_monitor_text,
                    "炸板 / 回封监控\n\n"
                    "这里会持续跟踪回封强度、炸板风险和是否还保留博弈价值。\n"
                    "盘中监控生成后，会自动切换到当前最值得盯的标的，也会跟扫描页联动。\n"
                    "当候选和监控都到位时，这里会告诉你是继续观察、转交易还是直接放弃。"
                )
            self._refresh_board_focus_cards("", None, None)
            return

        candidate = self._board_candidate_snapshot_for_symbol(target_symbol)
        monitor_payload = self._board_monitor_snapshot_for_symbol(target_symbol)
        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target_symbol), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target_symbol), None)

        if hasattr(self, "board_text"):
            if candidate is not None:
                lines = [
                    f"打板焦点：{candidate['stock_name']} ({candidate['stock_id']} / {candidate['symbol']})",
                    f"触发方式：{candidate['trigger_style']} | 风险等级：{candidate['risk_level']} | 打板分：{candidate['board_score']}",
                    f"计划价格：入场 {candidate['planned_entry']} | 止损 {candidate['planned_stop']} | 目标 {candidate['planned_target']}",
                    f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                    f"执行参考：{self._display_action(getattr(recommendation, 'action', 'WATCH')) if recommendation is not None else '观察'} | {getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                    "下一步：优先确认回封强度、成交承接和是否仍处于主线前排。",
                ]
                if recommendation is not None and getattr(recommendation, "rationale", ""):
                    lines.append(f"推荐理由：{recommendation.rationale}")
            elif scan_row is not None:
                lines = [
                    f"打板焦点：{self._stock_name_for_symbol(target_symbol)} ({self._stock_id_for_symbol(target_symbol)} / {target_symbol})",
                    f"扫描联动：{self._display_action(getattr(scan_row, 'action', 'WATCH'))} | 信号 {self._display_label(getattr(scan_row, 'label', 'WATCH'))} | 评分 {getattr(scan_row, 'score', '--')}",
                    f"收盘价：{getattr(scan_row, 'close', 0.0):.2f} | 信号日期：{getattr(scan_row, 'signal_date', '--')}",
                    f"原因：{getattr(scan_row, 'reason', '') or '等待扫描摘要联动'}",
                    "下一步：若打板池尚未生成，可先回到扫描页或推荐页补齐候选。",
                ]
            else:
                lines = [
                    f"打板焦点：{self._stock_name_for_symbol(target_symbol)} ({self._stock_id_for_symbol(target_symbol)} / {target_symbol})",
                    "当前没有满足条件的打板候选。",
                    "下一步：先从扫描页或推荐页选中股票，再联动查看打板候选。",
                ]
            self._set_plain_text_if_changed(self.board_text, "\n".join(lines))

        if hasattr(self, "board_monitor_text"):
            if monitor_payload is not None:
                lines = [
                    f"监控焦点：{monitor_payload['stock_name']} ({monitor_payload['stock_id']} / {target_symbol})",
                    f"状态：{monitor_payload['monitor_state']} | 强度：{monitor_payload['strength']} | 连续性：{monitor_payload['continuity']}",
                    f"动作建议：{monitor_payload['action_plan']}",
                    f"备注：{monitor_payload['note']}",
                ]
                if recommendation is not None:
                    lines.extend(
                        [
                            f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                            f"推荐动作：{self._display_action(getattr(recommendation, 'action', 'WATCH'))} | 下一步：{getattr(recommendation, 'next_focus', '') or '继续观察盘中量能与回封节奏'}",
                        ]
                    )
            elif scan_row is not None:
                lines = [
                    f"监控焦点：{self._stock_name_for_symbol(target_symbol)} ({self._stock_id_for_symbol(target_symbol)} / {target_symbol})",
                    f"扫描联动：{self._display_action(getattr(scan_row, 'action', 'WATCH'))} | 信号 {self._display_label(getattr(scan_row, 'label', 'WATCH'))} | 评分 {getattr(scan_row, 'score', '--')}",
                    f"备注：{getattr(scan_row, 'reason', '') or '等待监控链路同步'}",
                ]
            else:
                lines = [
                    f"监控焦点：{self._stock_name_for_symbol(target_symbol)} ({self._stock_id_for_symbol(target_symbol)} / {target_symbol})",
                    "暂无可用的打板监控摘要，等待监控链路同步。",
                ]
            self._set_plain_text_if_changed(self.board_monitor_text, "\n".join(lines))
        self._refresh_board_focus_cards(target_symbol, candidate, monitor_payload)

    def _refresh_board_focus_cards(self, symbol: str = "", candidate: dict | None = None, monitor_payload: dict | None = None) -> None:
        labels = getattr(self, "board_focus_metric_labels", None)
        accents = getattr(self, "board_focus_metric_accents", None)
        if not labels or not accents:
            return
        if not symbol:
            self._set_label_text_if_changed(labels["symbol"], "--")
            self._set_label_text_if_changed(accents["symbol"], "等待候选同步")
            self._set_label_text_if_changed(labels["score"], "--")
            self._set_label_text_if_changed(accents["score"], "等待打板评分同步")
            self._set_label_text_if_changed(labels["risk"], "待评估")
            self._set_label_text_if_changed(accents["risk"], "等待风险灯同步")
            self._set_label_text_if_changed(labels["action"], "待联动")
            self._set_label_text_if_changed(accents["action"], "等待监控链路")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == symbol), None)
        self._set_label_text_if_changed(labels["symbol"], (candidate or {}).get("stock_name", self._stock_name_for_symbol(symbol)))
        self._set_label_text_if_changed(accents["symbol"], (candidate or {}).get("stock_id", self._stock_id_for_symbol(symbol)))
        if candidate is not None:
            self._set_label_text_if_changed(labels["score"], str(candidate.get("board_score", "--")))
            self._set_label_text_if_changed(accents["score"], candidate.get("trigger_style", "待确认"))
        elif scan_row is not None:
            self._set_label_text_if_changed(labels["score"], f"{getattr(scan_row, 'score', 0.0):.1f}")
            self._set_label_text_if_changed(accents["score"], self._display_label(getattr(scan_row, "label", "WATCH")))
        else:
            self._set_label_text_if_changed(labels["score"], "--")
            self._set_label_text_if_changed(accents["score"], "等待打板评分同步")
        self._set_label_text_if_changed(labels["risk"], str((candidate or {}).get("risk_level", "待评估")))
        self._set_label_text_if_changed(
            accents["risk"],
            monitor_payload["state"] if monitor_payload is not None else ("扫描联动" if scan_row is not None else "等待风险跟踪")
        )
        self._set_label_text_if_changed(
            labels["action"],
            monitor_payload["action_plan"] if monitor_payload is not None else (self._display_action(getattr(scan_row, "action", "WATCH")) if scan_row is not None else "继续观察")
        )
        self._set_label_text_if_changed(
            accents["action"],
            f"强度 {monitor_payload['strength']} / 连续性 {monitor_payload['continuity']}"
            if monitor_payload is not None
            else ("扫描摘要已接入" if scan_row is not None else "等待监控链路")
        )

    def _on_board_candidate_selection_changed(self) -> None:
        symbol = ""
        if hasattr(self, "board_table"):
            row = self.board_table.currentRow()
            if row >= 0 and self.board_table.item(row, 2):
                symbol = self.board_table.item(row, 2).text()
        if symbol:
            self._select_board_monitor_row_for_symbol(symbol)
            self._refresh_board_focus_panels(symbol)

    def _on_board_monitor_selection_changed(self) -> None:
        symbol = ""
        if hasattr(self, "board_monitor_table"):
            row = self.board_monitor_table.currentRow()
            if row >= 0 and self.board_monitor_table.item(row, 2):
                symbol = self.board_monitor_table.item(row, 2).text()
        if symbol:
            self._select_board_candidate_row_for_symbol(symbol)
            self._refresh_board_focus_panels(symbol)

    def open_board_symbol_in_recommend(self) -> None:
        symbol = self._selected_board_symbol()
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")

    def open_board_symbol_in_scanner(self) -> None:
        symbol = self._selected_board_symbol()
        if symbol:
            self._select_scan_row_for_symbol(symbol)
            self._select_watchlist_symbol(symbol)
            self._select_monitor_row_for_symbol(symbol)
            if symbol in self.universe_bars:
                self.select_symbol(symbol)
            self._refresh_monitor_summary(symbol)
            self._refresh_scanner_focus_status(symbol)
            self._refresh_scanner_focus_cards(symbol)
        self._navigate_to_workspace("scanner", "scan_table")

    def open_board_symbol_in_overview(self) -> None:
        symbol = self._selected_board_symbol()
        if symbol and symbol in self.universe_bars:
            self.select_symbol(symbol)
        self._navigate_to_workspace("overview", "market_pool_table")

    def open_board_symbol_in_broker(self) -> None:
        symbol = self._selected_board_symbol()
        if symbol:
            self._focus_symbol_in_broker_workspace(symbol)
        else:
            self._navigate_to_workspace("broker", "orders_table")
        self._refresh_broker_order_focus()

    def open_broker_focus_orders(self) -> None:
        self._navigate_to_workspace("broker", "orders_table", "orders_table")
        self._refresh_broker_order_focus()

    def open_broker_focus_execution(self) -> None:
        self._navigate_to_workspace("broker", "execution_table", "execution_table")
        self._refresh_submission_focus()

    def open_broker_focus_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "trade_plan_table", "trade_plan_table")

    def open_runtime_to_overview(self) -> None:
        self._navigate_to_workspace("overview", "market_pool_table")

    def open_runtime_to_broker_logs(self) -> None:
        self._navigate_to_workspace("broker", "runtime_log_text")

    def open_detail_to_overview(self) -> None:
        symbol = self.active_symbol or ""
        if symbol and symbol in self.universe_bars:
            self.select_symbol(symbol)
        self._navigate_to_workspace("overview", "market_pool_table")

    def open_detail_to_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")

    def open_detail_to_scanner(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._select_watchlist_symbol(symbol)
            self._select_monitor_row_for_symbol(symbol)
        self._navigate_to_workspace("scanner", "scan_table", "scan_table")

    def open_selected_recommend_in_detail(self) -> None:
        symbol = ""
        table = getattr(self, "daily_pool_table", None)
        if table is not None:
            row_index = table.currentRow()
            if row_index >= 0:
                source_rows = (
                    self._filtered_daily_pool_rows()
                    if hasattr(self, "_filtered_daily_pool_rows")
                    else list(getattr(self, "daily_pool_rows", []) or [])
                )
                if row_index < len(source_rows):
                    symbol = getattr(source_rows[row_index], "symbol", "") or ""
        if not symbol:
            symbol = getattr(self, "active_symbol", "") or ""
        if not symbol:
            return
        self.active_symbol = symbol
        if hasattr(self, "open_focus_symbol_in_detail"):
            self.open_focus_symbol_in_detail()
        else:
            self._refresh_detail_workspace_panels()
            self._navigate_to_workspace("detail", "metrics_text")

    def _refresh_detail_workspace_panels(self) -> None:
        if not hasattr(self, "metrics_text"):
            return
        symbol = self.active_symbol or ""
        if not symbol:
            return
        stock_name = self._stock_name_for_symbol(symbol)
        stock_id = self._stock_id_for_symbol(symbol)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == symbol), None)
        latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if item.label != "NONE"), None)
        selected_signal = self._selected_detail_signal_snapshot()
        selected_trade = self._selected_detail_trade_snapshot()

        if hasattr(self, "detail_decision_text"):
            lines = [f"单票决策：{stock_name} ({stock_id} / {symbol})"]
            if recommendation is not None:
                lines.extend(
                    [
                        f"主线：{recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 动作：{self._display_action(recommendation.action)}",
                        f"主策略：{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'} | 分层：{getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                        f"买点：{(recommendation.entry_price or recommendation.close):.2f} | 止损：{(recommendation.stop_price or recommendation.close * 0.95):.2f} | 目标：{(recommendation.target_price or recommendation.close * 1.08):.2f}",
                        f"逻辑：{recommendation.rationale or '等待推荐逻辑生成。'}",
                    ]
                )
            elif latest_signal is not None:
                lines.extend(
                    [
                        f"最新信号：{self._display_label(latest_signal.label)} | 评分 {latest_signal.score}",
                        f"原因：{latest_signal.reason}",
                    ]
                )
            else:
                lines.append("当前没有可用的决策信息。")
            if selected_signal is not None:
                lines.extend(
                    [
                        "",
                        f"焦点信号：{selected_signal['date']} | {selected_signal['label']} | 评分 {selected_signal['score']}",
                        f"触发原因：{selected_signal['reason']}",
                    ]
                )
            elif getattr(self, "signal_table", None) is not None and self.signal_table.rowCount() > 0:
                lines.append("可在下方“近期信号”里点选一条记录，查看更细的触发原因。")
            self._set_plain_text_if_changed(self.detail_decision_text, "\n".join(lines))

        if hasattr(self, "detail_execution_text"):
            lines = [f"执行联动：{stock_name}"]
            order_intent = next((item for item in getattr(self, "order_intents", []) if getattr(item, "symbol", "") == symbol), None)
            execution_row = next((item for item in getattr(self, "order_result_rows", []) if str(item.get("symbol", "")) == symbol), None)
            if order_intent is not None:
                lines.append(f"委托建议：{getattr(order_intent, 'side', '')} {getattr(order_intent, 'quantity', 0)} 股 @ {getattr(order_intent, 'price', 0.0):.2f}")
            if execution_row:
                lines.append(f"最近执行：{execution_row.get('order_status', '--')} / {execution_row.get('fill_status', '--')}")
                lines.append(f"反馈：{execution_row.get('message', '--')}")
            if order_intent is None and not execution_row:
                lines.append("当前没有委托或执行记录，可先去交易页生成委托建议。")
            if selected_trade is not None:
                lines.extend(
                    [
                        "",
                        f"焦点成交：{selected_trade['entry_date']} -> {selected_trade['exit_date']}",
                        f"价格区间：{selected_trade['entry_price']} -> {selected_trade['exit_price']} | 股数 {selected_trade['shares']}",
                        f"盈亏：{selected_trade['pnl']} | 退出原因：{selected_trade['exit_reason']}",
                    ]
                )
            elif getattr(self, "trades_table", None) is not None and self.trades_table.rowCount() > 0:
                lines.append("可在下方“交易记录”里点选一笔成交，快速回看执行质量。")
            self._set_plain_text_if_changed(self.detail_execution_text, "\n".join(lines))

        if hasattr(self, "detail_conclusion_text"):
            lines = [f"复盘结论：{stock_name}"]
            if latest_signal is not None:
                lines.append(f"最近信号：{latest_signal.date} | {self._display_label(latest_signal.label)} | 评分 {latest_signal.score}")
            if recommendation is not None:
                lines.append(f"建议动作：{self._display_action(recommendation.action)} | 下一步：{getattr(recommendation, 'next_focus', '') or '继续观察主线与量能'}")
            if selected_signal is not None:
                lines.append(f"当前聚焦：{selected_signal['label']}，优先回看当日量价和主线强度。")
            if selected_trade is not None:
                lines.append(f"成交复盘：{selected_trade['exit_reason']}，可对照进出场纪律检查执行质量。")
            lines.append("后续动作：可继续去推荐页看同主线候选，或去交易页查看委托执行。")
            self._set_plain_text_if_changed(self.detail_conclusion_text, "\n".join(lines))

    def _selected_detail_signal_snapshot(self) -> dict[str, str] | None:
        table = getattr(self, "signal_table", None)
        if table is None:
            return None
        row = table.currentRow()
        if row < 0:
            return None
        values: list[str] = []
        for column in range(min(table.columnCount(), 5)):
            item = table.item(row, column)
            values.append(item.text() if item is not None else "--")
        if not values:
            return None
        while len(values) < 5:
            values.append("--")
        return {
            "date": values[0],
            "label": values[1],
            "score": values[2],
            "close": values[3],
            "reason": values[4],
        }

    def _selected_detail_trade_snapshot(self) -> dict[str, str] | None:
        table = getattr(self, "trades_table", None)
        if table is None:
            return None
        row = table.currentRow()
        if row < 0:
            return None
        values: list[str] = []
        for column in range(min(table.columnCount(), 7)):
            item = table.item(row, column)
            values.append(item.text() if item is not None else "--")
        if not values:
            return None
        while len(values) < 7:
            values.append("--")
        return {
            "entry_date": values[0],
            "exit_date": values[1],
            "entry_price": values[2],
            "exit_price": values[3],
            "shares": values[4],
            "pnl": values[5],
            "exit_reason": values[6],
        }

    def _on_detail_signal_selection_changed(self) -> None:
        self._refresh_detail_workspace_panels()

    def _on_detail_trade_selection_changed(self) -> None:
        self._refresh_detail_workspace_panels()


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
        selected_signal = self._selected_detail_signal_snapshot()
        signal_signature = tuple(
            (
                item.date,
                self._display_label(item.label),
                str(item.score),
                f"{item.close:.2f}",
                item.reason,
            )
            for item in rows
        )
        if getattr(self, "_signal_table_signature", None) != signal_signature:
            updates_enabled = self.signal_table.updatesEnabled()
            self.signal_table.setUpdatesEnabled(False)
            self.signal_table.blockSignals(True)
            try:
                self.signal_table.setRowCount(len(rows))
                for row_index, row_values in enumerate(signal_signature):
                    for column, value in enumerate(row_values):
                        self.signal_table.setItem(row_index, column, QTableWidgetItem(value))
            finally:
                self.signal_table.blockSignals(False)
                self.signal_table.setUpdatesEnabled(updates_enabled)
            self._signal_table_signature = signal_signature
        if rows:
            target_row = next(
                (
                    index
                    for index, row in enumerate(rows)
                    if selected_signal
                    and row.date == selected_signal.get("date", "")
                    and self._display_label(row.label) == selected_signal.get("label", "")
                ),
                0,
            )
            self.signal_table.selectRow(target_row)

    def run_backtest_for_active(self, quiet: bool = False) -> None:
        if not self.bars or not self.analyses:
            if not quiet:
                QMessageBox.information(self, "提示", "请先选择一个标的。")
            return
        result = Backtester(strategy_params=self.strategy_params()).run(self.bars, self.analyses)
        self.last_backtest_result = result
        latest_signal = next((item for item in reversed(self.analyses) if item.label != "NONE"), None)
        if latest_signal is None:
            latest_note = "最近 K 线中暂无有效信号。"
        else:
            latest_note = (
                f"最新信号：{latest_signal.date} | {self._display_label(latest_signal.label)} | 评分 {latest_signal.score}\n"
                f"{latest_signal.reason}"
            )
        source_path = self.paths_by_symbol.get(self.active_symbol)
        self._set_plain_text_if_changed(
            self.metrics_text,
            (
                f"{latest_note}\n"
                f"数据文件：{source_path}\n\n"
                f"{format_result(result)}\n\n"
                "说明：\n"
                "- 回测默认使用下一交易日开盘附近成交的日线近似。\n"
                "- 适合做研究、排序和半自动执行前检查。\n"
            )
        )
        selected_trade = self._selected_detail_trade_snapshot()
        trade_signature = tuple(
            (
                trade.entry_date,
                trade.exit_date,
                str(trade.entry_price),
                str(trade.exit_price),
                str(trade.shares),
                str(trade.pnl),
                trade.exit_reason,
            )
            for trade in result.trades
        )
        if getattr(self, "_trades_table_signature", None) != trade_signature:
            updates_enabled = self.trades_table.updatesEnabled()
            self.trades_table.setUpdatesEnabled(False)
            self.trades_table.blockSignals(True)
            try:
                self.trades_table.setRowCount(len(result.trades))
                for row_index, row_values in enumerate(trade_signature):
                    for column, value in enumerate(row_values):
                        self.trades_table.setItem(row_index, column, QTableWidgetItem(value))
            finally:
                self.trades_table.blockSignals(False)
                self.trades_table.setUpdatesEnabled(updates_enabled)
            self._trades_table_signature = trade_signature
        if result.trades:
            target_row = next(
                (
                    index
                    for index, trade in enumerate(result.trades)
                    if selected_trade
                    and trade.entry_date == selected_trade.get("entry_date", "")
                    and trade.exit_date == selected_trade.get("exit_date", "")
                    and str(trade.entry_price) == selected_trade.get("entry_price", "")
                ),
                0,
            )
            self.trades_table.selectRow(target_row)
        self._refresh_detail_workspace_panels()


    def export_workspace_report_from_ui(self) -> None:
        if not self.scan_rows:
            QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return
        artifacts = export_workspace_report(self.scan_rows, self.backtest_summaries, REPORT_DIR)
        self._set_plain_text_if_changed(
            self.optimization_text,
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
        fill_holdings_table(self)

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
        fill_order_intents_table(self)

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
        self._set_plain_text_if_changed(self.order_result_text, "\n".join(self.order_submission_log) + "\n")

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
        selected_timestamp = ""
        if not hasattr(self, "execution_table"):
            return
        records_signature = tuple(
            (
                item.get("timestamp", ""),
                item.get("order_status", ""),
                item.get("fill_status", ""),
                item.get("symbol", ""),
                item.get("side", ""),
                item.get("price", ""),
                item.get("quantity", ""),
                item.get("failure_reason", ""),
                item.get("message", ""),
            )
            for item in self.order_submission_records
        )
        if getattr(self, "_execution_table_signature", None) == records_signature:
            self._refresh_submission_focus()
            return
        current_row = self.execution_table.currentRow()
        if 0 <= current_row < len(self.order_submission_records):
            selected_timestamp = str(self.order_submission_records[current_row].get("timestamp", "") or "")
        updates_enabled = self.execution_table.updatesEnabled()
        self.execution_table.setUpdatesEnabled(False)
        self.execution_table.blockSignals(True)
        try:
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
        finally:
            self.execution_table.blockSignals(False)
            self.execution_table.setUpdatesEnabled(updates_enabled)
        self._execution_table_signature = records_signature
        if self.order_submission_records:
            target_row = next(
                (
                    index
                    for index, record in enumerate(self.order_submission_records)
                    if str(record.get("timestamp", "") or "") == selected_timestamp
                ),
                len(self.order_submission_records) - 1,
            )
            self.execution_table.selectRow(target_row)
        self._refresh_submission_focus()

    def _selected_submission_record(self) -> dict[str, str] | None:
        if not hasattr(self, "execution_table") or not self.order_submission_records:
            return None
        row_index = self.execution_table.currentRow()
        if row_index < 0:
            return self.order_submission_records[-1]
        if row_index >= len(self.order_submission_records):
            return self.order_submission_records[-1]
        return self.order_submission_records[row_index]

    def _on_execution_selection_changed(self) -> None:
        self._refresh_submission_focus()

    def _refresh_submission_focus(self) -> None:
        record = self._selected_submission_record()
        if hasattr(self, "order_result_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "执行回放\n\n"
                    "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                    "刷新委托或提交模拟单后，这里会自动切换到最新一条。\n"
                    "你也可以先从推荐页或打板页送审候选，再回到这里看执行反馈。"
                )
            else:
                lines = [
                    "执行回放",
                    "",
                    f"时间：{record.get('timestamp', '--')}",
                    f"股票：{self._stock_name_for_symbol(record.get('symbol', ''))} ({self._stock_id_for_symbol(record.get('symbol', ''))} / {record.get('symbol', '--')})",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))}",
                    f"成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"失败原因：{record.get('failure_reason', '') or '无'}",
                    f"反馈信息：{record.get('message', '') or '等待更多反馈'}",
                ]
                self._set_plain_text_if_changed(self.order_result_text, "\n".join(lines))
        if hasattr(self, "broker_recap_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.broker_recap_text,
                    "成交回顾\n\n"
                    "提交后，这里会沉淀通过率、阻塞原因、成交偏差和回看要点。\n"
                    "当订单建议生成后，可以在这里快速检查执行质量。"
                )
            else:
                symbol = record.get("symbol", "")
                recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
                lines = [
                    f"成交回顾：{self._stock_name_for_symbol(symbol)}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))} | 成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
                ]
                if recommendation is not None:
                    lines.append(
                        f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
                    )
                    lines.append(f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))}")
                    lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
                message = record.get("message", "") or ""
                if message:
                    lines.append(f"系统反馈：{message}")
                failure_reason = record.get("failure_reason", "") or ""
                if failure_reason:
                    lines.append(f"需要处理：{failure_reason}")
                else:
                    lines.append("后续动作：可继续查看委托明细，或回到推荐页校验主线和仓位。")
                self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))

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
            note_lines.append("- 当前环境已满足直连 SDK 调用条件。")
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
        self._set_plain_text_if_changed(self.broker_status_text, "\n".join(content))
        if hasattr(self, "broker_metric_labels"):
            readiness = "已就绪" if connected else ("桥接可用" if env["bridge_ready"] else "待配置")
            risk_count = sum(1 for item in self.order_intents if getattr(item, "side", "") in {"SELL", "REDUCE"})
            buy_count = sum(1 for item in self.order_intents if getattr(item, "side", "") == "BUY")
            buy_budget = sum(float(getattr(item, "price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0) for item in self.order_intents if getattr(item, "side", "") == "BUY")
            exposure = (buy_budget / available) if available > 0 else 0.0
            self.broker_metric_labels["readiness"].setText(readiness)
            self.broker_metric_accents["readiness"].setText("SDK 可下单" if connected else ("可桥接调用" if env["bridge_ready"] else "建议先导出/桥接"))
            self.broker_metric_labels["capital"].setText(f"{available:,.0f}")
            self.broker_metric_accents["capital"].setText(f"持仓市值 {market_value:,.0f}")
            self.broker_metric_labels["risk_reward"].setText(f"{buy_count} / {risk_count}")
            self.broker_metric_accents["risk_reward"].setText("买入候选 / 卖减建议")
            self.broker_metric_labels["risk_budget"].setText(f"{exposure:.0%}" if buy_budget > 0 else "0%")
            self.broker_metric_accents["risk_budget"].setText("预计买入力度")

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

    def _display_mainline_role(self, value: str) -> str:
        return {
            "CORE": "核心龙头",
            "FRONT": "前排核心",
            "ASSIST": "助攻前排",
            "FOLLOW": "跟风观察",
            "NOISE": "杂毛噪声",
            "ELIMINATED": "淘汰风险",
            "": "待确认",
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

    def _theme_for_symbol(self, symbol: str, recommendation=None) -> str:
        theme_name = ""
        if recommendation is not None:
            theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "")
        if not theme_name:
            profile = self._stock_profile_for_symbol(symbol)
            theme_name = getattr(profile, "industry", "") if profile is not None else ""
        return theme_name or "待确认"

    def _hype_logic_for_symbol(self, symbol: str, recommendation=None, scan_row=None) -> str:
        if recommendation is not None and getattr(recommendation, "rationale", ""):
            return str(getattr(recommendation, "rationale", "")).strip()
        profile = self._stock_profile_for_symbol(symbol)
        if profile is not None and getattr(profile, "notes", ""):
            return str(getattr(profile, "notes", "")).strip()
        if scan_row is not None and getattr(scan_row, "reason", ""):
            return str(getattr(scan_row, "reason", "")).strip()
        return "等待逻辑生成"

    def _news_digest_lines_for_symbol(self, symbol: str, limit: int = 2) -> list[str]:
        if not symbol:
            return []
        items = list(getattr(self, "news_catalysts", {}).get(symbol, []) or [])
        if not items:
            return []
        lines: list[str] = []
        for item in items[:limit]:
            title = getattr(item, "title", "") or "消息标题未填写"
            source = getattr(item, "source", "") or "来源未知"
            published = getattr(item, "published_at", "") or ""
            meta = " / ".join(part for part in [source, published] if part)
            lines.append(f"- {title}{f' ({meta})' if meta else ''}")
            summary = getattr(item, "summary", "") or ""
            if summary:
                lines.append(f"  {summary[:42]}")
        return lines

    def _compact_news_badge(self, symbol: str) -> str:
        items = list(getattr(self, "news_catalysts", {}).get(symbol, []) or [])
        if not items:
            return "消息：暂无"
        item = items[0]
        title = (getattr(item, "title", "") or "消息标题未填写")[:16]
        source = getattr(item, "source", "") or "来源未知"
        return f"消息：{title} | {source}"

    def _recommend_price_snapshot(self, recommendation) -> dict[str, float | None]:
        close_price = float(getattr(recommendation, "close", 0.0) or 0.0)
        entry_price = getattr(recommendation, "entry_price", None)
        stop_price = getattr(recommendation, "stop_price", None)
        target_price = getattr(recommendation, "target_price", None)
        entry = float(entry_price if entry_price is not None else close_price) if (entry_price is not None or close_price) else 0.0
        stop = float(stop_price if stop_price is not None else (entry * 0.95 if entry else 0.0))
        target = float(target_price if target_price is not None else (entry * 1.08 if entry else 0.0))
        upside_pct = ((target - entry) / entry * 100.0) if entry and target > entry else None
        downside_pct = ((entry - stop) / entry * 100.0) if entry and stop < entry else None
        rr_ratio = None
        if entry and stop and target and entry > stop and target > entry:
            rr_ratio = (target - entry) / max(entry - stop, 0.001)
        return {
            "entry": entry,
            "stop": stop,
            "target": target,
            "upside_pct": upside_pct,
            "downside_pct": downside_pct,
            "rr_ratio": rr_ratio,
        }

    def _recommend_price_brief(self, recommendation) -> str:
        snapshot = self._recommend_price_snapshot(recommendation)
        entry = float(snapshot["entry"] or 0.0)
        stop = float(snapshot["stop"] or 0.0)
        target = float(snapshot["target"] or 0.0)
        upside_pct = snapshot["upside_pct"]
        rr_ratio = snapshot["rr_ratio"]
        parts = [f"买 {entry:.2f}", f"损 {stop:.2f}", f"目标 {target:.2f}"]
        if upside_pct is not None:
            parts.append(f"上行 {upside_pct:.1f}%")
        if rr_ratio is not None:
            parts.append(f"盈亏比 {rr_ratio:.2f}")
        return " | ".join(parts)

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
            self._set_plain_text_if_changed(self.board_monitor_text, merged)
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
            self._set_plain_text_if_changed(self.trade_plan_text, merged)
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
        self._set_label_text_if_changed(self.last_refresh_label, f"收盘复盘已导出：{current_dt.strftime('%H:%M:%S')}")

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
            self._set_plain_text_if_changed(self.trade_plan_text, merged)

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
        if risk_level == "低":
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
        board_signature = tuple(
            (
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
            )
            for item in board_plan.candidates
        )
        monitor_signature = tuple(
            (
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
            )
            for item in board_plan.monitor_rows
        )
        selected_board_symbol = ""
        if self.board_table.currentRow() >= 0 and self.board_table.currentRow() < self.board_table.rowCount():
            item = self.board_table.item(self.board_table.currentRow(), 2)
            selected_board_symbol = item.text() if item else ""
        selected_monitor_symbol = ""
        if self.board_monitor_table.currentRow() >= 0 and self.board_monitor_table.currentRow() < self.board_monitor_table.rowCount():
            item = self.board_monitor_table.item(self.board_monitor_table.currentRow(), 2)
            selected_monitor_symbol = item.text() if item else ""

        if getattr(self, "_board_table_signature", None) != board_signature:
            board_updates_enabled = self.board_table.updatesEnabled()
            self.board_table.setUpdatesEnabled(False)
            self.board_table.blockSignals(True)
            try:
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
                        table_item.setToolTip(
                            f"{item.stock_name} ({item.stock_id})\n"
                            f"交易标识：{item.symbol}\n"
                            f"触发方式：{item.trigger_style}\n"
                            f"风险级别：{item.risk_level}\n"
                            f"计划买点：{item.planned_entry:.2f}"
                        )
                        self.board_table.setItem(row_index, column, table_item)
                    identity_item = QTableWidgetItem(f"{item.stock_name} | {item.stock_id} | {item.symbol}")
                    identity_item.setBackground(bg)
                    identity_item.setForeground(fg)
                    identity_item.setToolTip(
                        f"{item.stock_name} ({item.stock_id})\n交易标识：{item.symbol}\n打板分：{item.board_score:.1f}\n风险：{item.risk_level}"
                    )
                    self.board_table.setItem(row_index, 0, identity_item)
            finally:
                self.board_table.blockSignals(False)
                self.board_table.setUpdatesEnabled(board_updates_enabled)
            self._board_table_signature = board_signature
            if board_plan.candidates:
                target_row = next(
                    (index for index, item in enumerate(board_plan.candidates) if item.symbol == selected_board_symbol),
                    0,
                )
                self.board_table.selectRow(target_row)

        if getattr(self, "_board_monitor_signature", None) != monitor_signature:
            monitor_updates_enabled = self.board_monitor_table.updatesEnabled()
            self.board_monitor_table.setUpdatesEnabled(False)
            self.board_monitor_table.blockSignals(True)
            try:
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
                        table_item.setToolTip(
                            f"{item.stock_name} ({item.stock_id})\n"
                            f"交易标识：{item.symbol}\n"
                            f"监控状态：{item.monitor_state}\n"
                            f"动作建议：{item.action_plan}\n"
                            f"备注：{item.note}"
                        )
                        self.board_monitor_table.setItem(row_index, column, table_item)
                    identity_item = QTableWidgetItem(f"{item.stock_name} | {item.stock_id} | {item.symbol}")
                    identity_item.setBackground(bg)
                    identity_item.setForeground(fg)
                    identity_item.setToolTip(
                        f"{item.stock_name} ({item.stock_id})\n交易标识：{item.symbol}\n监控状态：{item.monitor_state}\n强度：{item.strength_score:.1f}"
                    )
                    self.board_monitor_table.setItem(row_index, 0, identity_item)
            finally:
                self.board_monitor_table.blockSignals(False)
                self.board_monitor_table.setUpdatesEnabled(monitor_updates_enabled)
            self._board_monitor_signature = monitor_signature
            if board_plan.monitor_rows:
                target_row = next(
                    (index for index, item in enumerate(board_plan.monitor_rows) if item.symbol == selected_monitor_symbol),
                    0,
                )
                self.board_monitor_table.selectRow(target_row)
        self._apply_identity_table_headers()

        if hasattr(self, "board_text"):
            if board_plan.candidates:
                focus = board_plan.candidates[0]
                lines = [
                    f"打板温度：{board_plan.temperature}",
                    f"候选平均分：{board_plan.avg_score:.1f}",
                    "",
                    f"核心标的：{focus.stock_name} ({focus.stock_id})",
                    f"触发方式：{focus.trigger_style}",
                    f"计划价格：入场 {focus.planned_entry:.2f} | 止损 {focus.planned_stop:.2f} | 目标 {focus.planned_target:.2f}",
                    f"逻辑：{focus.rationale}",
                ]
            else:
                lines = ["当前没有满足条件的打板候选。"]
            self._set_plain_text_if_changed(self.board_text, "\n".join(lines))

        if hasattr(self, "board_monitor_text"):
            self._set_plain_text_if_changed(self.board_monitor_text, "\n".join(board_plan.notes))
        self._refresh_board_focus_panels()


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
                theme_name = getattr(row, "theme_name", "") or row.strategy_tag
                leaderboard_cards.append(
                    (
                        f"<div style='margin:0 0 12px 0;padding:12px;border:1px solid {border};"
                        "border-radius:10px;background:#11161d;'>"
                        f"<div style='color:{border};font-weight:800;font-size:12px;margin-bottom:6px;'>{badge}</div>"
                        f"<div style='color:#f5f7fa;font-weight:800;font-size:18px;'>{row.stock_name} {row.stock_id}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;margin-top:6px;'>题材方向：{theme_name}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;'>策略标签：{row.strategy_tag}</div>"
                        f"<div style='color:#8fa0b6;font-size:12px;'>资金标签：{row.fund_model}</div>"
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
            self._set_plain_text_if_changed(self.market_theme_brief_text, "\n".join(theme_lines))
            if hasattr(self, "overview_summary_cards"):
                top_theme_name = ranked[0][0] if ranked else "暂无"
                top_theme_count = ranked[0][1] if ranked else 0
                self.overview_summary_cards["theme"].set_data(
                    top_theme_name,
                    f"前排 {top_theme_count} 只 | 题材数 {len(ranked)} | 焦点 {rows[0].stock_name if rows else '等待候选同步'}",
                )
        if hasattr(self, "market_breadth_text"):
            news_lines = ["新闻流", ""]
            seen_symbols: set[str] = set()
            for row in rows[:6]:
                symbol_news = self.news_catalysts.get(row.symbol, [])
                if symbol_news:
                    item = symbol_news[0]
                    source = getattr(item, "source", "") or "来源未知"
                    published = getattr(item, "published_at", "") or ""
                    meta = " / ".join(part for part in [source, published] if part)
                    news_lines.append(f"- {row.stock_name}: {item.title}{f' ({meta})' if meta else ''}")
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
            self._set_plain_text_if_changed(self.market_breadth_text, "\n".join(news_lines))
        if hasattr(self, "overview_summary_cards") and not rows:
            self.overview_summary_cards["theme"].set_data("暂无", "等待远程行情或本地缓存加载。")
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
            "- 东方财富接入：已配置",
            f"- 当前模式：{self._market_mode_label()}",
            f"- 当前来源：{self._market_source_mode_label()}",
            f"- 本地缓存文件：{cache_stats.get('files', 0)}",
            f"- 本地缓存大小：{cache_stats.get('bytes', 0)} bytes",
            f"- 当前算法池：{len(getattr(self.market_screen_result, 'algorithmic_pool', []))} 只",
        ]
        lines.insert(5, f"- 当前是否命中缓存：{cache_hit}")
        if getattr(self.market_screen_result, "generated_at", ""):
            lines.append(f"- 最近行情时间：{self.market_screen_result.generated_at}")
        if self.last_market_success_at:
            lines.append(f"- 最后一次成功刷新：{self.last_market_success_at}")
        if self.last_market_error:
            lines.append(f"- 最后一次错误：{self.last_market_error[:120]}")
        if self.runtime_events:
            lines.extend(["", "最近诊断"])
            lines.extend(f"- {item}" for item in self.runtime_events[-4:])
        if extra_lines:
            lines.extend(["", *extra_lines])
        self._set_plain_text_if_changed(self.market_source_status_text, "\n".join(lines))
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
        if strategy_target:
            self.recommend_strategy_filter = "尾盘优选" if strategy_target == "尾盘买入法" else strategy_target
            if hasattr(self, "_populate_filtered_daily_pool_table"):
                self._populate_filtered_daily_pool_table()
        if getattr(self, "market_status_label", None) is not None:
            status_text = self.market_status_label.text().split(" | 策略：", 1)[0].strip()
            strategy_text = "尾盘优选" if strategy_target == "尾盘买入法" else (strategy_target or "全部")
            self._set_label_text_if_changed(self.market_status_label, f"{status_text} | 策略：{strategy_text}")

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
            self._set_label_text_if_changed(
                self.recommend_status_label,
                f"已切换为程序自动筛选股票池，共 {len(self.daily_pool_rows)} 只候选。"
            )
        if hasattr(self, "daily_pool_text"):
            if self.daily_pool_rows:
                top = self.daily_pool_rows[0]
                self._set_plain_text_if_changed(
                    self.daily_pool_text,
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
                self._set_plain_text_if_changed(self.daily_pool_text, "当前没有筛出满足条件的股票。")
        self._refresh_trade_plan()
        self._refresh_board_mode()
        self._refresh_intraday_monitor()

    def _populate_daily_pool_table(self) -> None:
        self.theme_heat_rows, self.leader_candidates = summarize_themes(self.daily_pool_rows, top_n_themes=8, top_n_leaders=8)
        self._refresh_recommend_theme_options()
        self._populate_filtered_daily_pool_table()
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
        rows = [
            row
            for row in self.daily_pool_rows
            if self.recommend_theme_filter == "全部" or (row.theme_name or "未分类") == self.recommend_theme_filter
        ]
        strategy_filter = str(getattr(self, "recommend_strategy_filter", "全部") or "全部")
        if strategy_filter == "尾盘优选":
            rows = [
                row
                for row in rows
                if (getattr(row, "primary_strategy", "") or "") == "尾盘买入法"
                and float(getattr(row, "tail_buy_score", 0.0) or 0.0) >= 82.0
                and float(getattr(row, "execution_readiness", 0.0) or 0.0) >= 72.0
                and str(getattr(row, "mainline_risk_flag", "") or "") != "高"
            ]
        elif strategy_filter not in {"全部", "全部策略"}:
            rows = [row for row in rows if (getattr(row, "primary_strategy", "") or "") == strategy_filter]
        return rows

    def _set_strategy_detail_from_row(self, row: RecommendationRow | None) -> None:
        if row is None or not hasattr(self, "strategy_detail_combo"):
            return
        self.strategy_detail_combo.setCurrentText(getattr(row, "primary_strategy", "") or "掘龙决策")

    def _refresh_recommendation_focus_panels(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        if current is None:
            if hasattr(self, "recommend_dispatch_text"):
                self._set_plain_text_if_changed(self.recommend_dispatch_text, "先看结论，再看分发顺序。\n刷新后这里会显示送审节奏、核心标的和优先队列。")
            if hasattr(self, "recommend_focus_review_text"):
                self._set_plain_text_if_changed(self.recommend_focus_review_text, "先看结论、位置和风险。\n选中一只股票后，这里会显示单票审查摘要。")
            if hasattr(self, "recommend_queue_text"):
                self._set_plain_text_if_changed(self.recommend_queue_text, "待审、已审和失败队列会集中显示在这里。")
            self._refresh_recommend_story_panels(None)
            self._refresh_recommend_focus_status(None)
            return

        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        action_label = self._display_action(getattr(current, "action", "WATCH"))
        opportunity = getattr(current, "opportunity_tier", "") or "待确认"
        catalyst = getattr(current, "catalyst", "") or "量价共振 + 主力净流入"
        rationale = getattr(current, "rationale", "") or "等待更清晰的主线信号。"
        next_focus = getattr(current, "next_focus", "") or "盯住主线强度、量能承接和资金回流。"
        risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
        confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
        readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)

        if hasattr(self, "recommend_dispatch_text"):
            dispatch_lines = [
                f"分发标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
                f"主线：{theme_name} | 动作：{action_label} | 分层：{opportunity}",
                f"送审优先级：执行准备 {readiness:.1f} / 置信 {confidence:.1f}",
                f"催化：{catalyst}",
                f"分发建议：{next_focus}",
            ]
            self._set_plain_text_if_changed(self.recommend_dispatch_text, "\n".join(dispatch_lines))

        if hasattr(self, "recommend_focus_review_text"):
            review_lines = [
                f"单票审查：{current.stock_name}",
                f"总分 {current.total_score:.1f} | 风险 {risk_flag} | 主策略 {getattr(current, 'primary_strategy', '') or '掘龙决策'}",
            ]
            review_lines.extend(recommendation_focus_lines(current))
            review_lines.append(f"核心理由：{rationale}")
            self._set_plain_text_if_changed(self.recommend_focus_review_text, "\n".join(review_lines))

        if hasattr(self, "recommend_queue_text"):
            buy_rows = [item for item in self.daily_pool_rows[:5] if getattr(item, "action", "") == "BUY"]
            watch_rows = [item for item in self.daily_pool_rows[:5] if getattr(item, "action", "") == "WATCH"]
            queue_lines = [
                f"当前前排：{current.stock_name} | {action_label}",
                f"待执行队列：{', '.join(item.stock_name for item in buy_rows[:3]) or '暂无可直接执行标的'}",
                f"观察队列：{', '.join(item.stock_name for item in watch_rows[:3]) or '暂无观察标的'}",
                f"风险提示：{risk_flag} | 失效条件：{getattr(current, 'invalidation_reason', '') or '跌破防守位或主线切换时重新评估'}",
            ]
            self._set_plain_text_if_changed(self.recommend_queue_text, "\n".join(queue_lines))

        if hasattr(self, "recommend_focus_metric_labels"):
            metric_values = {
                "symbol": (current.stock_name, f"{current.stock_id} / {current.symbol}"),
                "theme": (theme_name, f"主线位次 {getattr(current, 'mainline_rank', 0) or '--'}"),
                "action": (action_label, f"执行准备 {readiness:.1f}"),
                "execution": ("待处理" if getattr(current, "action", "") in {"BUY", "WATCH"} else "复核中", f"风险 {risk_flag}"),
            }
            for key, (value, accent) in metric_values.items():
                if key in self.recommend_focus_metric_labels:
                    self._set_label_text_if_changed(self.recommend_focus_metric_labels[key], value)
                if hasattr(self, "recommend_focus_metric_accents") and key in self.recommend_focus_metric_accents:
                    self._set_label_text_if_changed(self.recommend_focus_metric_accents[key], accent)
        self._refresh_recommend_focus_cards(current)
        self._refresh_recommend_story_panels(current)
        self._refresh_recommend_focus_status(current)

    def _refresh_recommend_focus_status(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        if current is None:
            if hasattr(self, "recommend_status_label"):
                total = len(getattr(self, "daily_pool_rows", []))
                self._set_label_text_if_changed(
                    self.recommend_status_label,
                    f"推荐状态：已生成 {total} 只候选，先看主线、位置、风险，再决定是否送审。"
                    if total
                    else RECOMMEND_DEFAULT_STATUS_TEXT
                )
            if hasattr(self, "daily_pool_focus_label"):
                self._set_label_text_if_changed(self.daily_pool_focus_label, RECOMMEND_DEFAULT_FOCUS_TEXT)
            self._refresh_workspace_status_labels()
            return

        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        action_label = self._display_action(getattr(current, "action", "WATCH"))
        readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
        confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(
                self.recommend_status_label,
                f"推荐状态：{current.stock_name} | {theme_name} | {action_label} | 执行准备 {readiness:.1f} | 置信 {confidence:.1f}"
            )
        if hasattr(self, "daily_pool_focus_label"):
            self._set_label_text_if_changed(
                self.daily_pool_focus_label,
                f"当前焦点：{current.stock_name} | {getattr(current, 'opportunity_tier', '') or '待确认'} | 主线 {theme_name}"
            )
        self._refresh_workspace_status_labels()

    def _refresh_recommend_bucket_panels(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        trade_plan = getattr(self, "current_trade_plan", None)
        decisions = list(getattr(trade_plan, "decisions", []) or [])
        position_advice = list(getattr(self, "current_position_advice", []) or [])
        buy_rows = [item for item in decisions if str(getattr(item, "action", "") or "").upper() == "BUY"]
        watch_rows = [item for item in getattr(self, "daily_pool_rows", []) if str(getattr(item, "action", "") or "").upper() == "WATCH"]
        risk_rows = [item for item in position_advice if str(getattr(item, "action", "") or "").upper() in {"SELL", "REDUCE"}]

        if hasattr(self, "recommend_core_bucket_text"):
            if buy_rows:
                top = buy_rows[0]
                lines = [
                    "主线前排执行桶",
                    f"优先标的：{getattr(top, 'stock_name', '') or self._stock_name_for_symbol(getattr(top, 'symbol', ''))} ({getattr(top, 'stock_id', '') or self._stock_id_for_symbol(getattr(top, 'symbol', ''))})",
                    f"计划动作：{self._display_action(getattr(top, 'action', 'BUY'))} | 仓位 {getattr(top, 'position_pct', 0.0):.0%}",
                    f"计划价格：{getattr(top, 'planned_price', getattr(top, 'entry_price', 0.0)) or 0.0:.2f} | 止损 {getattr(top, 'stop_price', 0.0) or 0.0:.2f} | 目标 {getattr(top, 'target_price', 0.0) or 0.0:.2f}",
                    f"执行理由：{getattr(top, 'reason', '') or getattr(top, 'rationale', '') or '优先处理主线前排。'}",
                ]
            elif current is not None and str(getattr(current, "action", "") or "").upper() == "BUY":
                lines = [
                    "主线前排执行桶",
                    f"候选标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
                    f"主线：{getattr(current, 'mainline_tag', '') or getattr(current, 'theme_name', '') or '待确认'} | 执行准备 {getattr(current, 'execution_readiness', 0.0):.1f}",
                    f"预案：可优先送审，确认量能承接后进入交易页。",
                    f"催化：{getattr(current, 'catalyst', '') or '等待资金与主线共振。'}",
                ]
            else:
                lines = ["主线前排执行桶", "当前没有直接执行的新仓计划。", "先看推荐池前排和交易计划刷新结果。"]
            self._set_plain_text_if_changed(self.recommend_core_bucket_text, "\n".join(lines))

        if hasattr(self, "recommend_watch_bucket_text"):
            if current is not None:
                lines = [
                    "观察池",
                    f"当前焦点：{current.stock_name} ({current.stock_id} / {current.symbol})",
                    f"观察动作：{self._display_action(getattr(current, 'action', 'WATCH'))} | 分层 {getattr(current, 'opportunity_tier', '') or '待确认'}",
                    f"下一步：{getattr(current, 'next_focus', '') or '继续看主线强度、量能回流和分时承接。'}",
                    f"备选观察：{', '.join(item.stock_name for item in watch_rows[:3]) or '暂无其他观察标的'}",
                ]
            else:
                lines = ["观察池", "等待推荐池生成后，再更新观察名单。", f"当前观察数量：{len(watch_rows)}"]
            self._set_plain_text_if_changed(self.recommend_watch_bucket_text, "\n".join(lines))

        if hasattr(self, "recommend_risk_bucket_text"):
            if risk_rows:
                top = risk_rows[0]
                symbol = getattr(top, "symbol", "")
                lines = [
                    "风险池",
                    f"优先处理：{getattr(top, 'stock_name', '') or self._stock_name_for_symbol(symbol)} ({getattr(top, 'stock_id', '') or self._stock_id_for_symbol(symbol)})",
                    f"动作：{self._display_action(getattr(top, 'action', 'REDUCE'))} | 主线 {getattr(top, 'mainline_flow_signal', '') or '待确认'} / {getattr(top, 'mainline_stage', '') or '待确认'}",
                    f"原因：{getattr(top, 'reason', '') or getattr(top, 'rationale', '') or '主线走弱或触发风控条件。'}",
                    f"风险队列：{', '.join((getattr(item, 'stock_name', '') or self._stock_name_for_symbol(getattr(item, 'symbol', ''))) for item in risk_rows[:3])}",
                ]
            elif current is not None:
                lines = [
                    "风险池",
                    f"焦点风险：{getattr(current, 'mainline_risk_flag', '') or '待评估'} | 失效条件：{getattr(current, 'invalidation_reason', '') or '跌破防守位或主线切换。'}",
                    f"当前主线：{getattr(current, 'mainline_flow_signal', '') or '待确认'} / {getattr(current, 'mainline_stage', '') or '待确认'}",
                    "若盘中出现切换预警，优先减仓或回到观察状态。",
                ]
            else:
                lines = ["风险池", "当前没有新增风险处理任务。", "导入持仓或生成计划后，这里会优先展示卖出 / 减仓建议。"]
            self._set_plain_text_if_changed(self.recommend_risk_bucket_text, "\n".join(lines))

    def _refresh_recommend_focus_cards(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        if current is None:
            return

        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        strategy_name = getattr(current, "primary_strategy", "") or "掘龙决策"
        action_label = self._display_action(getattr(current, "action", "WATCH"))
        readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
        confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
        flow_signal = getattr(current, "mainline_flow_signal", "") or "待确认"
        stage_name = getattr(current, "mainline_stage", "") or "待确认"
        risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
        next_focus = getattr(current, "next_focus", "") or "继续跟踪主线强度、量能承接和资金回流。"
        catalyst = getattr(current, "catalyst", "") or "量价共振 + 资金回流"

        if hasattr(self, "recommend_summary_cards"):
            self.recommend_summary_cards["logic"].set_data(
                theme_name,
                f"{current.stock_name} | {self._display_mainline_role(getattr(current, 'mainline_role', '') or '')} | 总分 {current.total_score:.1f}",
            )
            self.recommend_summary_cards["plan"].set_data(
                action_label,
                f"执行准备 {readiness:.1f} | 置信 {confidence:.1f} | {strategy_name}",
            )
            self.recommend_summary_cards["pulse"].set_data(
                flow_signal,
                f"阶段 {stage_name} | 风险 {risk_flag}",
            )
            self.recommend_summary_cards["holding"].set_data(
                "盯下一步",
                next_focus,
            )

        if hasattr(self, "priority_cards"):
            self.priority_cards["theme"].set_data(
                f"{getattr(current, 'mainline_window_score', 0.0):.1f}",
                f"焦点: {theme_name}",
                f"{self._display_mainline_role(getattr(current, 'mainline_role', '') or '')} | 风险 {risk_flag}",
            )
            self.priority_cards["strategy"].set_data(
                f"{strategy_name}",
                f"焦点: {current.stock_name}",
                f"主打法与当前焦点一致，优先核对催化和位置。",
            )
            self.priority_cards["focus"].set_data(
                f"{getattr(current, 'dragon_decision_score', getattr(current, 'total_score', 0.0)):.1f}",
                f"焦点: {current.stock_name}",
                f"{action_label} | {theme_name} | 准备 {readiness:.1f}",
            )

        if hasattr(self, "action_flow_cards"):
            self.action_flow_cards["BUY"].set_data(
                self.action_flow_cards["BUY"].count_label.text(),
                f"焦点: {current.stock_name}" if getattr(current, "action", "") == "BUY" else f"焦点: {self.action_flow_cards['BUY'].focus_label.text().replace('焦点: ', '')}",
                "确认买点后推进送审。" if getattr(current, "action", "") == "BUY" else self.action_flow_cards["BUY"].note_label.text(),
            )
            self.action_flow_cards["WATCH"].set_data(
                self.action_flow_cards["WATCH"].count_label.text(),
                f"焦点: {current.stock_name}" if getattr(current, "action", "") == "WATCH" else self.action_flow_cards["WATCH"].focus_label.text(),
                "继续盯承接、量能和扩散。" if getattr(current, "action", "") == "WATCH" else self.action_flow_cards["WATCH"].note_label.text(),
            )
            if getattr(current, "action", "") in {"REDUCE", "SELL"}:
                key = "SELL" if getattr(current, "action", "") == "SELL" else "REDUCE"
                self.action_flow_cards[key].set_data(
                    self.action_flow_cards[key].count_label.text(),
                    f"焦点: {current.stock_name}",
                    "纪律触发后优先处理。" if key == "SELL" else "先降风险，再决定是否继续。",
                )

        if hasattr(self, "alert_cards"):
            self.alert_cards["theme"].set_data(stage_name, f"主线 {theme_name} | 信号 {flow_signal}")
            self.alert_cards["leader"].set_data(
                self._display_mainline_role(getattr(current, "mainline_role", "") or ""),
                f"焦点标的：{current.stock_name} | 龙头级别 {self._display_leader_level(getattr(current, 'leader_level', '') or '')}",
            )
            self.alert_cards["strategy"].set_data(strategy_name, f"动作 {action_label} | 催化 {catalyst[:12]}")
            self.alert_cards["action"].set_data(action_label, f"下一步 {next_focus[:18]}")

    def _refresh_overview_focus_cards(self, symbol: str, snapshot, recommendation) -> None:
        if not hasattr(self, "overview_summary_cards"):
            return
        if recommendation is not None:
            theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
            role_name = self._display_mainline_role(getattr(recommendation, "mainline_role", "") or "")
            strategy_name = getattr(recommendation, "primary_strategy", "") or "掘龙决策"
            action_label = self._display_action(getattr(recommendation, "action", "WATCH"))
            catalyst = getattr(recommendation, "catalyst", "") or "等待消息与量价共振"
            decision_score = float(getattr(recommendation, "dragon_decision_score", getattr(recommendation, "total_score", 0.0)) or 0.0)
            self.overview_summary_cards["theme"].set_data(
                theme_name,
                f"{recommendation.stock_name} | {role_name} | 位次 {getattr(recommendation, 'mainline_rank', getattr(recommendation, 'theme_rank', '--'))}",
            )
            self.overview_summary_cards["source"].set_data(
                strategy_name,
                f"{action_label} | 催化 {catalyst}",
            )
            self.overview_summary_cards["capital"].set_data(
                f"{float(getattr(recommendation, 'mainline_window_score', 0.0) or 0.0):.1f}",
                f"总分 {float(getattr(recommendation, 'total_score', 0.0) or 0.0):.1f} | 风险 {getattr(recommendation, 'mainline_risk_flag', '') or '待评估'}",
            )
            self.overview_summary_cards["decision"].set_data(
                action_label,
                f"决策分 {decision_score:.1f} | 执行准备 {float(getattr(recommendation, 'execution_readiness', 0.0) or 0.0):.1f}",
            )
            return
        if snapshot is not None:
            self.overview_summary_cards["theme"].set_data(
                snapshot.strategy_tag or "待确认",
                f"{snapshot.stock_name} | 热度 {snapshot.heat_score:.1f} | 动能 {snapshot.momentum_bias:.1f}",
            )
            self.overview_summary_cards["source"].set_data(
                snapshot.fund_model or "待确认",
                f"{snapshot.stock_id} | 涨跌 {snapshot.pct_change:.2f}% | 换手 {snapshot.turnover:.2f}%",
            )
            self.overview_summary_cards["capital"].set_data(
                f"{snapshot.main_inflow / 1e8:.2f} 亿",
                f"热度 {snapshot.heat_score:.1f} | 动能 {snapshot.momentum_bias:.1f} | 换手 {snapshot.turnover:.2f}%",
            )
            self.overview_summary_cards["decision"].set_data(
                "观察",
                f"{snapshot.strategy_tag} | 涨跌 {snapshot.pct_change:.2f}% | 先看量价承接",
            )
            return
        stock_name = self._stock_name_for_symbol(symbol) if symbol else "等待行情接入"
        self.overview_summary_cards["theme"].set_data("等待行情接入", f"{stock_name} | 等待主线题材、龙头位次与前排数量刷新。")
        self.overview_summary_cards["source"].set_data("等待行情接入", "等待远程行情、缓存或示例数据接入。")

    def _refresh_recommend_story_panels(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        if current is None:
            if hasattr(self, "daily_pool_text") and not self.daily_pool_text.toPlainText().strip():
                self._set_plain_text_if_changed(self.daily_pool_text, "每日推荐池将在刷新后生成，默认最多展示 5 只可执行候选。")
            if hasattr(self, "strategy_path_text") and not self.strategy_path_text.toPlainText().strip():
                self._set_plain_text_if_changed(self.strategy_path_text, "等待生成推荐池后更新主线推演路径。")
            self._refresh_recommend_bucket_panels(None)
            return

        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        role_name = getattr(current, "mainline_role", "") or ""
        flow_signal = getattr(current, "mainline_flow_signal", "") or "待确认"
        stage_name = getattr(current, "mainline_stage", "") or "待确认"
        readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
        confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
        stock_pool = getattr(current, "stock_pool", "") or "程序自动筛选池"
        catalyst = getattr(current, "catalyst", "") or "量价共振 + 资金回流"
        next_focus = getattr(current, "next_focus", "") or "继续盯主线强度、量能承接和回流节奏。"
        invalidation = getattr(current, "invalidation_reason", "") or "跌破防守位或主线切换时重新评估。"

        if hasattr(self, "daily_pool_text"):
            lines = [
                "今日优先候选",
                f"焦点标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
                f"主线：{theme_name} | 阶段：{stage_name} | 角色：{self._display_mainline_role(role_name)}",
                f"动作：{self._display_action(getattr(current, 'action', 'WATCH'))} | 总分 {current.total_score:.1f}",
                f"执行准备：{readiness:.1f} | 置信：{confidence:.1f} | 股票池：{stock_pool}",
                f"催化：{catalyst}",
                f"逻辑：{getattr(current, 'rationale', '') or '等待更清晰的主线与量价确认。'}",
            ]
            self._set_plain_text_if_changed(self.daily_pool_text, "\n".join(lines))

        if hasattr(self, "strategy_path_text"):
            lines = [
                f"主线推演：{current.stock_name}",
                f"第一步：主线 {theme_name} 目前处于 {stage_name}，信号为 {flow_signal}。",
                f"第二步：当前角色是 {self._display_mainline_role(role_name)}，先看是否继续维持前排强度。",
                f"第三步：若执行准备 {readiness:.1f} 持续抬升，可考虑按 {getattr(current, 'primary_strategy', '') or '掘龙决策'} 计划推进。",
                f"第四步：重点观察 {next_focus}",
                f"失效条件：{invalidation}",
            ]
            self._set_plain_text_if_changed(self.strategy_path_text, "\n".join(lines))
        self._refresh_recommend_bucket_panels(current)

    def _select_daily_pool_row_by_stock_id(self, stock_id: str) -> RecommendationRow | None:
        if not stock_id or not hasattr(self, "daily_pool_table"):
            return None
        for index, row in enumerate(self._filtered_daily_pool_rows()):
            if row.stock_id == stock_id:
                changed = self._select_table_row_if_needed(self.daily_pool_table, index)
                self._set_strategy_detail_from_row(row)
                if changed:
                    self._refresh_recommendation_focus_panels(row)
                return row
        return None

    def _on_daily_pool_selection_changed(self) -> None:
        self._refresh_recommendation_focus_panels()
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
        selected = self._select_daily_pool_row_by_stock_id(stock_id)
        self._refresh_recommendation_focus_panels(selected)

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
            self.select_symbol(symbol, origin="overview")

    def select_symbol(self, symbol: str, origin: str = "") -> None:
        if symbol not in self.universe_bars:
            return
        self.active_symbol = symbol
        self.bars = self.universe_bars[symbol]
        self.analyses = self.universe_analyses[symbol]
        if hasattr(self, "active_symbol_label"):
            self._set_label_text_if_changed(self.active_symbol_label, f"当前标的：{symbol}")
        self.state.selected_symbol = symbol
        self._refresh_signal_panel()
        self.run_backtest_for_active(quiet=True)
        self._render_market_dashboard(symbol)
        self._refresh_detail_workspace_panels()
        self._sync_symbol_across_workspaces(symbol, origin=origin)
        self._refresh_workspace_focus_banners()
        self._refresh_live_workspace_summary_panels()
        self.save_state()

    def _render_market_dashboard(self, symbol: str) -> None:
        snapshot = self.market_snapshots.get(symbol)
        recommendation = next((item for item in self.daily_pool_rows if item.symbol == symbol), None)
        chart_series = getattr(self.market_screen_result, "chart_series_by_symbol", {}).get(symbol)
        if hasattr(self, "market_header_label"):
            title = symbol if snapshot is None else f"{snapshot.stock_name}  {snapshot.stock_id}  {symbol}"
            self._set_label_text_if_changed(self.market_header_label, title)
        if hasattr(self, "market_subheader_label"):
            sub = "程序自动筛选出的龙头候选"
            if snapshot is not None:
                sub = (
                    f"{snapshot.strategy_tag} | {snapshot.fund_model} | 涨跌幅 {snapshot.pct_change:.2f}% | "
                    f"换手 {snapshot.turnover:.1f}% | 主力净流入 {snapshot.main_inflow / 1e8:.2f} 亿"
                )
            self._set_label_text_if_changed(self.market_subheader_label, sub)
        if hasattr(self, "market_signal_label") and snapshot is not None:
            self._set_label_text_if_changed(
                self.market_signal_label,
                f"{snapshot.fund_model}   |   {snapshot.strategy_tag}   |   热度 {snapshot.heat_score:.1f}   |   动能 {snapshot.momentum_bias:.1f}"
            )
        if hasattr(self, "market_quote_label"):
            if snapshot is not None:
                self._set_label_text_if_changed(
                    self.market_quote_label,
                    f"开 {snapshot.open_price:.2f} / 高 {snapshot.high_price:.2f} / 低 {snapshot.low_price:.2f} / 收 {snapshot.latest_price:.2f} "
                    f"| 涨跌 {snapshot.pct_change:.2f}% | 换手 {snapshot.turnover:.2f}% | 历史窗口 {self.market_history_window}"
                )
            else:
                self._set_label_text_if_changed(
                    self.market_quote_label,
                    f"历史窗口 {self.market_history_window} | 周期 {self.market_timeframe_mode} | 叠加 {'/'.join(sorted(self.market_overlay_modes)) or '关闭'}"
                )
        self._update_intraday_chart(symbol, snapshot, chart_series)
        self._update_daily_chart(symbol)
        self._update_fund_chart(symbol, chart_series)
        self._update_momentum_chart(symbol, chart_series)
        self._update_indicator_chart(symbol)
        self._update_market_text_panels(symbol, snapshot, recommendation)
        self._refresh_overview_focus_cards(symbol, snapshot, recommendation)

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
        boll_mid_series = QLineSeries()
        boll_mid_series.setColor(QColor("#7ed7ff"))
        boll_mid_series.setName("BOLL 中轨")
        boll_upper_series = QLineSeries()
        boll_upper_series.setColor(QColor("#ff9f43"))
        boll_upper_series.setName("BOLL 上轨")
        boll_lower_series = QLineSeries()
        boll_lower_series.setColor(QColor("#25d07f"))
        boll_lower_series.setName("BOLL 下轨")

        visible_bars, visible_analyses = self._windowed_market_bars(symbol, bars, analyses)
        dates = []
        highs = []
        lows = []
        closes: list[float] = []
        for index, bar in enumerate(visible_bars):
            dt = QDateTime.fromString(bar.date, "yyyy-MM-dd")
            ts = float(dt.toMSecsSinceEpoch())
            candle_series.append(QCandlestickSet(bar.open, bar.high, bar.low, bar.close, ts))
            dates.append(ts)
            highs.append(bar.high)
            lows.append(bar.low)
            closes.append(bar.close)
            if "MA" in self.market_overlay_modes and index < len(visible_analyses):
                analysis = visible_analyses[index]
                ma_fast_series.append(ts, analysis.ma_fast)
                ma_slow_series.append(ts, analysis.ma_slow)
            if "BOLL" in self.market_overlay_modes and len(closes) >= 20:
                window = closes[-20:]
                mid = sum(window) / len(window)
                variance = sum((value - mid) ** 2 for value in window) / len(window)
                std = variance ** 0.5
                boll_mid_series.append(ts, mid)
                boll_upper_series.append(ts, mid + std * 2)
                boll_lower_series.append(ts, mid - std * 2)

        chart.addSeries(candle_series)
        if "MA" in self.market_overlay_modes and ma_fast_series.count():
            chart.addSeries(ma_fast_series)
            chart.addSeries(ma_slow_series)
        if "BOLL" in self.market_overlay_modes and boll_mid_series.count():
            chart.addSeries(boll_mid_series)
            chart.addSeries(boll_upper_series)
            chart.addSeries(boll_lower_series)

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
        attach_series = [candle_series]
        if "MA" in self.market_overlay_modes and ma_fast_series.count():
            attach_series.extend([ma_fast_series, ma_slow_series])
        if "BOLL" in self.market_overlay_modes and boll_mid_series.count():
            attach_series.extend([boll_mid_series, boll_upper_series, boll_lower_series])
        for series in attach_series:
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
        if dates:
            axis_x.setRange(QDateTime.fromMSecsSinceEpoch(int(dates[0])), QDateTime.fromMSecsSinceEpoch(int(dates[-1])))

        self.daily_chart_view.setChart(chart)

    def _windowed_market_bars(
        self,
        symbol: str,
        bars: list[PriceBar] | None = None,
        analyses: list[DailyAnalysis] | None = None,
    ) -> tuple[list[PriceBar], list[DailyAnalysis]]:
        full_bars = list(bars if bars is not None else self.universe_bars.get(symbol, []))
        full_analyses = list(analyses if analyses is not None else self.universe_analyses.get(symbol, []))
        if not full_bars:
            return [], []

        history_sizes = {
            "近1月": 22,
            "近3月": 66,
            "近1年": 250,
            "全部": len(full_bars),
        }
        target_size = history_sizes.get(getattr(self, "market_history_window", "近1年"), 250)
        target_size = max(20, min(target_size, len(full_bars)))
        step = max(10, target_size // 3)
        max_offset = max((len(full_bars) - target_size + step - 1) // step, 0)
        self.market_chart_offset = max(0, min(getattr(self, "market_chart_offset", 0), max_offset))

        end_index = len(full_bars) - self.market_chart_offset * step
        end_index = max(target_size, min(end_index, len(full_bars)))
        start_index = max(0, end_index - target_size)
        return full_bars[start_index:end_index], full_analyses[start_index:end_index]

    def _update_indicator_chart(self, symbol: str) -> None:
        if not hasattr(self, "indicator_chart_view"):
            return
        bars, _ = self._windowed_market_bars(symbol)
        chart = QChart()
        indicator_name = getattr(self, "market_secondary_indicator_mode", "MACD") or "MACD"
        self._style_dark_chart(chart, f"{indicator_name} 副图")
        if not bars:
            self.indicator_chart_view.setChart(chart)
            return

        closes = [bar.close for bar in bars]
        categories = [bar.date[5:] for bar in bars[-30:]]
        recent_closes = closes[-30:]

        if indicator_name == "RSI":
            series = QLineSeries()
            series.setColor(QColor("#25f3ff"))
            series.setName("RSI")
            values = []
            for index in range(1, len(recent_closes)):
                window = recent_closes[max(0, index - 6): index + 1]
                gains = []
                losses = []
                for left, right in zip(window[:-1], window[1:]):
                    diff = right - left
                    gains.append(max(diff, 0.0))
                    losses.append(abs(min(diff, 0.0)))
                avg_gain = sum(gains) / max(len(gains), 1)
                avg_loss = sum(losses) / max(len(losses), 1)
                rs = avg_gain / avg_loss if avg_loss else 100.0
                rsi = 100.0 - (100.0 / (1.0 + rs))
                series.append(index, rsi)
                values.append(rsi)
            chart.addSeries(series)
            axis_x = QValueAxis()
            axis_x.setLabelsVisible(False)
            axis_y = QValueAxis()
            axis_y.setRange(0, 100)
            axis_y.setLabelsColor(QColor("#b7c0d8"))
            axis_y.setGridLineColor(QColor("#252a33"))
            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignRight)
            series.attachAxis(axis_x)
            series.attachAxis(axis_y)
            axis_x.setRange(0, max(series.count() - 1, 1))
        elif indicator_name == "KDJ":
            k_series = QLineSeries()
            d_series = QLineSeries()
            j_series = QLineSeries()
            k_series.setColor(QColor("#25f3ff"))
            d_series.setColor(QColor("#f7d354"))
            j_series.setColor(QColor("#ff6b6b"))
            k_value = 50.0
            d_value = 50.0
            for index in range(len(bars[-30:])):
                scope = bars[max(0, len(bars) - 30 + index - 8): len(bars) - 30 + index + 1]
                if not scope:
                    continue
                high = max(item.high for item in scope)
                low = min(item.low for item in scope)
                close = scope[-1].close
                rsv = 50.0 if high == low else (close - low) / (high - low) * 100.0
                k_value = k_value * 2 / 3 + rsv / 3
                d_value = d_value * 2 / 3 + k_value / 3
                j_value = 3 * k_value - 2 * d_value
                k_series.append(index, k_value)
                d_series.append(index, d_value)
                j_series.append(index, j_value)
            for series in [k_series, d_series, j_series]:
                chart.addSeries(series)
            axis_x = QValueAxis()
            axis_x.setLabelsVisible(False)
            axis_y = QValueAxis()
            axis_y.setRange(0, 120)
            axis_y.setLabelsColor(QColor("#b7c0d8"))
            axis_y.setGridLineColor(QColor("#252a33"))
            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignRight)
            for series in [k_series, d_series, j_series]:
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)
            axis_x.setRange(0, max(k_series.count() - 1, 1))
        else:
            dif_series = QLineSeries()
            dea_series = QLineSeries()
            dif_series.setColor(QColor("#25f3ff"))
            dea_series.setColor(QColor("#ff9f43"))
            positive = QBarSet("红柱")
            negative = QBarSet("绿柱")
            positive.setColor(QColor("#ff5e57"))
            negative.setColor(QColor("#25d07f"))
            ema12 = recent_closes[0]
            ema26 = recent_closes[0]
            dea = 0.0
            values = []
            for index, close in enumerate(recent_closes):
                ema12 = ema12 * 11 / 13 + close * 2 / 13
                ema26 = ema26 * 25 / 27 + close * 2 / 27
                dif = ema12 - ema26
                dea = dea * 8 / 10 + dif * 2 / 10
                hist = (dif - dea) * 2
                dif_series.append(index, dif)
                dea_series.append(index, dea)
                positive.append(max(hist, 0.0))
                negative.append(abs(min(hist, 0.0)))
                values.extend([abs(dif), abs(dea), abs(hist)])
            bars_series = QBarSeries()
            bars_series.append(positive)
            bars_series.append(negative)
            chart.addSeries(bars_series)
            chart.addSeries(dif_series)
            chart.addSeries(dea_series)
            axis_x = QBarCategoryAxis()
            axis_x.append(categories or ["--"])
            axis_x.setLabelsColor(QColor("#8fa0b4"))
            axis_y = QValueAxis()
            upper = max(values) * 1.3 if values else 1.0
            axis_y.setRange(-upper, upper)
            axis_y.setLabelsColor(QColor("#b7c0d8"))
            axis_y.setGridLineColor(QColor("#252a33"))
            chart.addAxis(axis_x, Qt.AlignBottom)
            chart.addAxis(axis_y, Qt.AlignRight)
            for series in [bars_series, dif_series, dea_series]:
                series.attachAxis(axis_x)
                series.attachAxis(axis_y)

        self.indicator_chart_view.setChart(chart)

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

        positive = QBarSet("强势")
        negative = QBarSet("回落")
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
        if hasattr(self, "overview_command_text"):
            command_lines = ["盘前指挥摘要", ""]
            if recommendation is not None:
                command_lines.extend(
                    [
                        f"焦点标的：{recommendation.stock_name} ({recommendation.stock_id} / {recommendation.symbol})",
                        f"主线：{recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 分层：{getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                        f"动作：{self._display_action(recommendation.action)} | 主策略：{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'}",
                        f"执行准备：{float(getattr(recommendation, 'execution_readiness', 0.0) or 0.0):.1f} | 置信：{float(getattr(recommendation, 'confidence_score', 0.0) or 0.0):.1f}",
                        f"催化：{recommendation.catalyst or '等待消息催化'}",
                        f"下一步：{getattr(recommendation, 'next_focus', '') or '先看分时承接、量能和主线持续性'}",
                    ]
                )
            elif snapshot is not None:
                command_lines.extend(
                    [
                        f"焦点标的：{snapshot.stock_name} ({snapshot.stock_id} / {symbol})",
                        f"状态：{snapshot.strategy_tag} | 资金模型：{snapshot.fund_model}",
                        f"热度：{snapshot.heat_score:.1f} | 动能：{snapshot.momentum_bias:.1f}",
                        "动作建议：先看主线、盘口承接和主力净流入，再决定是否进入推荐池。",
                    ]
                )
            else:
                command_lines.extend(
                    [
                        "当前还没有焦点标的。",
                        "建议先刷新市场，再确认主线方向、容量核心和今天最值得跟踪的前排股票。",
                    ]
                )
            self._set_plain_text_if_changed(self.overview_command_text, "\n".join(command_lines))

        if hasattr(self, "overview_execution_text"):
            execution_lines = ["执行路径", ""]
            if recommendation is not None:
                execution_lines.extend(
                    [
                        f"买点：{(recommendation.entry_price or recommendation.close):.2f}",
                        f"止损：{(recommendation.stop_price or recommendation.close * 0.95):.2f}",
                        f"目标：{(recommendation.target_price or recommendation.close * 1.08):.2f}",
                        f"失效条件：{getattr(recommendation, 'invalidation_reason', '') or '跌破防守位或主线切换时重新评估'}",
                        f"逻辑：{recommendation.rationale or '等待推荐逻辑生成。'}",
                    ]
                )
            elif snapshot is not None:
                execution_lines.extend(
                    [
                        f"最新价：{snapshot.latest_price:.2f} | 涨跌幅：{snapshot.pct_change:.2f}%",
                        f"换手：{snapshot.turnover:.2f}% | 主力净流入：{snapshot.main_inflow / 1e8:.2f} 亿",
                        "执行建议：先观察，再等待推荐池和交易计划确认。",
                    ]
                )
            else:
                execution_lines.extend(
                    [
                        "当前还没有可执行路径。",
                        "推荐池和交易计划生成后，这里会同步给出买点、止损、目标和失效条件。",
                    ]
                )
            self._set_plain_text_if_changed(self.overview_execution_text, "\n".join(execution_lines))

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
                                f"- 七策评分：龙头 {getattr(recommendation, 'leader_model_score', 0.0):.1f} / "
                                f"主力 {getattr(recommendation, 'main_force_score', 0.0):.1f} / "
                                f"打板 {getattr(recommendation, 'board_attack_score', 0.0):.1f} / "
                                f"低吸 {getattr(recommendation, 'value_recovery_score', 0.0):.1f} / "
                                f"尾盘 {getattr(recommendation, 'tail_buy_score', 0.0):.1f} / "
                                f"一日 {getattr(recommendation, 'one_day_hold_score', 0.0):.1f} / "
                                f"决策 {getattr(recommendation, 'dragon_decision_score', recommendation.total_score):.1f}"
                            ),
                        ]
                    )
            else:
                lines.extend(
                    [
                        "- 当前暂无资金画像数据",
                        "- 刷新市场后，这里会补上主力净流入、换手率和热度变化。",
                    ]
                )
            self._set_plain_text_if_changed(self.market_capital_text, "\n".join(lines))
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
                lines.extend(
                    [
                        "- 当前还没有生成明确决策建议",
                        "- 先看主线是否清晰、量价是否匹配，再决定是否进入推荐池。",
                    ]
                )
            self._set_plain_text_if_changed(self.market_decision_text, "\n".join(lines))
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
                self.tabs.setTabText(index, WORKSPACE_LABEL_BY_KEY.get(key, "工作区"))
        if hasattr(self, "top_badge"):
            self.top_badge.setText("量化猎手 Pro v2.2")
        if hasattr(self, "theme_title_label"):
            self.theme_title_label.setText("主题")
        self.setWindowTitle("量化猎手 Pro v2.2")
        self._refresh_shell_header()

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
    QFrame[actionRow="true"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(29, 38, 51, 0.92), stop:1 rgba(18, 24, 33, 0.88));
        border: 1px solid rgba(109, 137, 167, 0.22);
        border-radius: 14px;
    }
    QFrame[actionRow="true"]:hover {
        border-color: rgba(138, 186, 245, 0.30);
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 rgba(34, 45, 61, 0.96), stop:1 rgba(20, 27, 38, 0.92));
    }
    QGroupBox#terminalPanel {
        background: #11161d;
        border: 1px solid #1f2a35;
        border-radius: 14px;
        margin-top: 11px;
        padding-top: 10px;
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
    padding: 7px 12px;
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
    padding: 7px 12px;
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
                "把算法候选、观察池、回测摘要和盘中预警统一收进一个工作台里，适合日内盯盘和快速切换。",
                [("实时", "自动刷新"), ("3 区", "扫描/观察/监控")],
            )
        )

        tool_panel = QGroupBox("扫描工作台")
        tool_panel.setObjectName("workspaceToolPanel")
        tool_layout = QGridLayout(tool_panel)
        tool_layout.setContentsMargins(14, 12, 14, 12)
        tool_layout.setHorizontalSpacing(16)
        tool_layout.setVerticalSpacing(10)

        controls = QHBoxLayout()
        controls.setSpacing(8)
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
        tool_layout.addLayout(controls, 0, 0)

        quick_row = QHBoxLayout()
        quick_row.setSpacing(8)
        scanner_overview_button = QPushButton("回到总览")
        scanner_recommend_button = QPushButton("查看推荐")
        scanner_detail_button = QPushButton("查看复盘")
        scanner_board_button = QPushButton("查看打板")
        self._set_button_role(scanner_overview_button, "ghost")
        self._set_button_role(scanner_recommend_button, "tonal")
        self._set_button_role(scanner_detail_button, "accent")
        self._set_button_role(scanner_board_button, "ghost")
        scanner_overview_button.clicked.connect(self.open_monitor_symbol_in_overview)
        scanner_recommend_button.clicked.connect(self.open_monitor_symbol_in_recommend)
        scanner_detail_button.clicked.connect(lambda: self._navigate_to_workspace("detail", "metrics_text"))
        scanner_board_button.clicked.connect(self.open_monitor_symbol_in_board)
        quick_row.addWidget(scanner_overview_button)
        quick_row.addWidget(scanner_recommend_button)
        quick_row.addWidget(scanner_detail_button)
        quick_row.addWidget(scanner_board_button)
        quick_row.addStretch(1)
        tool_layout.addLayout(quick_row, 1, 0)

        hint = QLabel("扫描页会自动复用首页筛出的市场候选，也支持叠加本地样本与观察池做交叉验证。")
        hint.setObjectName("inlineHint")
        hint.setWordWrap(True)

        self.universe_label = QLabel("股票池目录：未加载")
        self.scan_summary_label = QLabel("尚未执行扫描。")
        self.universe_label.setObjectName("inlineHint")
        self.scan_summary_label.setObjectName("inlineHint")
        info_panel = QFrame()
        info_panel.setProperty("actionRow", True)
        info_layout = QVBoxLayout(info_panel)
        info_layout.setContentsMargins(12, 10, 12, 10)
        info_layout.setSpacing(6)
        info_layout.addWidget(self.universe_label)
        info_layout.addWidget(self.scan_summary_label)
        info_layout.addWidget(hint)
        tool_layout.addWidget(info_panel, 0, 1, 2, 1)
        tool_layout.setColumnStretch(0, 3)
        tool_layout.setColumnStretch(1, 2)
        layout.addWidget(tool_panel)

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
        self.summary_table.itemSelectionChanged.connect(self.on_summary_selected)
        summary_layout.addWidget(self.summary_table)
        bottom.addWidget(summary_box)

        monitor_box = QGroupBox("盘中监控")
        self._style_terminal_panel(monitor_box)
        monitor_layout = QVBoxLayout(monitor_box)
        self.monitor_table = build_table(["代码", "动作", "信号", "评分", "收盘价", "信号日期", "更新时间"])
        self.monitor_table.itemSelectionChanged.connect(self.on_monitor_selected)
        monitor_layout.addWidget(self.monitor_table)
        self.monitor_summary_text = QTextEdit()
        self.monitor_summary_text.setReadOnly(True)
        self._style_terminal_console(self.monitor_summary_text)
        self._set_plain_text_if_changed(self.monitor_summary_text, "等待监控链路同步。")
        monitor_layout.addWidget(self.monitor_summary_text)
        monitor_action_row = QHBoxLayout()
        monitor_overview_button = QPushButton("查看首页")
        monitor_recommend_button = QPushButton("查看推荐")
        monitor_broker_button = QPushButton("查看交易")
        monitor_board_button = QPushButton("查看打板")
        self._set_button_role(monitor_overview_button, "ghost")
        self._set_button_role(monitor_recommend_button, "tonal")
        self._set_button_role(monitor_broker_button, "accent")
        self._set_button_role(monitor_board_button, "ghost")
        monitor_overview_button.clicked.connect(self.open_monitor_symbol_in_overview)
        monitor_recommend_button.clicked.connect(self.open_monitor_symbol_in_recommend)
        monitor_broker_button.clicked.connect(self.open_monitor_symbol_in_broker)
        monitor_board_button.clicked.connect(self.open_monitor_symbol_in_board)
        monitor_action_row.addWidget(monitor_overview_button)
        monitor_action_row.addWidget(monitor_recommend_button)
        monitor_action_row.addWidget(monitor_broker_button)
        monitor_action_row.addWidget(monitor_board_button)
        monitor_action_row.addStretch(1)
        monitor_layout.addLayout(monitor_action_row)
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
        if async_mode and hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "正在生成每日推荐池...")
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

    def _scan_universe(self, folder: Path, quiet: bool = False, async_mode: bool = True) -> None:
        target_folder = Path(folder)
        if not target_folder.exists():
            self._handle_scan_error(f"股票目录不存在：{target_folder}", quiet)
            return
        try:
            params = self.current_strategy_params() if hasattr(self, "current_strategy_params") else StrategyParams()
        except Exception as exc:
            self._handle_scan_error(str(exc), quiet)
            return
        if async_mode:
            if hasattr(self, "scan_summary_label"):
                self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：正在后台刷新股票池、观察池与盘中监控焦点...")
            started = self._run_background_job(
                "scan_universe",
                lambda: self._scan_universe_payload(target_folder, params),
                lambda payload: self._apply_scan_universe_result(target_folder, payload),
                lambda message: self._handle_scan_error(message, quiet),
            )
            if not started and hasattr(self, "scan_summary_label"):
                self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：上一轮扫描仍在执行，本轮自动刷新已跳过。")
            self._refresh_shell_header()
            return
        try:
            payload = self._scan_universe_payload(target_folder, params)
        except Exception as exc:
            self._handle_scan_error(str(exc), quiet)
            return
        self._apply_scan_universe_result(target_folder, payload)






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
        if async_mode and hasattr(self, "market_status_label"):
            self._set_label_text_if_changed(self.market_status_label, "总览状态：正在从全市场筛选龙头候选...")
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
            "打板策略": ("#57430f", "#ffd75b"),
            "强势接力": ("#57430f", "#ffd75b"),
            "价值低吸": ("#204728", "#7ef5a2"),
            "尾盘买入法": ("#4b3418", "#ffcf82"),
            "一日持股法": ("#3b2f12", "#ffd27a"),
            "隔日强势": ("#3b2f12", "#ffd27a"),
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

        self._set_label_text_if_changed(self.dashboard_metric_labels["candidate_count"], str(len(pool)))
        self._set_label_text_if_changed(
            self.dashboard_metric_accents["candidate_count"],
            f"Top 1：{pool[0].stock_name}" if pool else "等待候选同步"
        )

        self._set_label_text_if_changed(self.dashboard_metric_labels["buy_count"], str(buy_count))
        self._set_label_text_if_changed(
            self.dashboard_metric_accents["buy_count"],
            f"观察 {max(len(recommendations) - buy_count, 0)} 只"
        )

        self._set_label_text_if_changed(self.dashboard_metric_labels["avg_heat"], f"{avg_heat:.1f}")
        self._set_label_text_if_changed(
            self.dashboard_metric_accents["avg_heat"],
            "热度高于 80 为强势前排" if pool else "等待热度同步"
        )

        self._set_label_text_if_changed(self.dashboard_metric_labels["top_theme"], top_theme)
        self._set_label_text_if_changed(
            self.dashboard_metric_accents["top_theme"],
            f"{theme_counter.get(top_theme, 0)} 只" if theme_counter else "等待主线同步"
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
                market_job_running = self._is_job_running("market_refresh")
                if not market_job_running:
                    self.refresh_remote_market(quiet=True, update_chart=False)
                if hasattr(self, "last_refresh_label"):
                    label_prefix = "最近刷新"
                    if market_job_running:
                        label_prefix = "最近检查"
                    self._set_label_text_if_changed(
                        self.last_refresh_label,
                        f"{label_prefix}：{current_dt.strftime('%H:%M:%S')}",
                    )
                if market_job_running and hasattr(self, "market_status_label"):
                    self._set_label_text_if_changed(
                        self.market_status_label,
                        f"总览状态：上一轮市场刷新仍在执行，本轮于 {current_dt.strftime('%H:%M:%S')} 跳过。",
                    )
            else:
                if hasattr(self, "last_refresh_label"):
                    self._set_label_text_if_changed(
                        self.last_refresh_label,
                        f"等待交易时段：{current_dt.strftime('%H:%M:%S')}",
                    )

        if scanner_auto and self.state.universe_dir and in_session:
            scan_job_running = self._is_job_running("scan_universe")
            if not scan_job_running:
                self._scan_universe(Path(self.state.universe_dir), quiet=True, async_mode=True)
            elif hasattr(self, "scan_summary_label"):
                self._set_label_text_if_changed(
                    self.scan_summary_label,
                    f"扫描状态：上一轮扫描仍在执行，本轮于 {current_dt.strftime('%H:%M:%S')} 跳过。",
                )
            if self.current_broker_profile().mode == "sdk" and not scan_job_running:
                self.sync_broker_via_sdk(quiet=True)

        self._maybe_auto_export_end_of_day_review(current_dt)
        self._refresh_shell_header()

    def _handle_daily_pool_error(self, message: str) -> None:
        handle_daily_pool_error(self, message, show_error_dialog_fn=QMessageBox.critical)

    def _apply_daily_pool_rows(self, rows: list[RecommendationRow]) -> None:
        self._symbol_data_revision += 1
        apply_daily_pool_rows(self, rows, summarize_themes)

    def _handle_scan_error(self, message: str, quiet: bool) -> None:
        handle_scan_error(self, message, quiet, show_error_dialog_fn=QMessageBox.critical)

    def _apply_scan_universe_result(
        self,
        folder: Path,
        payload: tuple[list[ScanRow], dict[str, list[PriceBar]], dict[str, list[DailyAnalysis]], dict[str, Path], list[SymbolBacktestSummary]],
    ) -> None:
        self._symbol_data_revision += 1
        apply_scan_universe_result(self, folder, payload)

    def _handle_market_refresh_error(self, message: str, quiet: bool) -> None:
        handle_market_refresh_error(self, message, quiet, show_error_dialog_fn=QMessageBox.critical)
        self._refresh_shell_header()

    def _apply_market_screen_result(
        self,
        result: MarketScreenResult,
        update_chart: bool = False,
        feed_state: dict[str, str] | None = None,
    ) -> None:
        self._symbol_data_revision += 1
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
        self._refresh_shell_header()

    def run_parameter_optimization(self) -> None:
        if hasattr(self, "optimization_text"):
            self._set_plain_text_if_changed(self.optimization_text, "正在后台运行参数优化，请稍候...\n")
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
        self._refresh_shell_header()

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
        self._refresh_shell_header()

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
        self._stabilize_workspace_layouts()
        self._polish_workspace_density()

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
        for label_name in ("market_status_label", "recommend_status_label", "broker_status_banner", "daily_pool_focus_label", "orders_focus_label", "trade_plan_focus_label"):
            label = getattr(self, label_name, None)
            if isinstance(label, QLabel):
                label.setWordWrap(True)

        self._normalize_overview_builder_texts()
        self._normalize_aux_workspace_texts()
        self._normalize_auth_workspace_texts()
        self._normalize_config_workspace_texts()
        self._normalize_broker_workspace_texts()
        self._normalize_recommend_workspace_texts()
        self._normalize_board_workspace_texts()
        self._normalize_detail_workspace_texts()
        self._repair_runtime_widget_texts()
        self._prime_recommend_workspace_defaults()
        self._prime_broker_workspace_defaults()
        self._inject_overview_action_rows()
        self._inject_scanner_action_row()
        self._inject_scanner_focus_cards()
        self._inject_scanner_summary_cards()
        self._inject_recommend_action_rows()
        self._inject_board_focus_cards()
        self._inject_board_action_rows()
        self._inject_broker_action_rows()
        self._inject_detail_action_rows()
        self._inject_config_tool_panel()
        self._inject_live_workspace_summary_panels()
        self._inject_workspace_focus_banners()
        self._normalize_scanner_workspace_texts()
        self._apply_identity_table_headers()
        self._ensure_selection_hook(getattr(self, "board_table", None), self._on_board_candidate_selection_changed)
        self._ensure_selection_hook(getattr(self, "board_monitor_table", None), self._on_board_monitor_selection_changed)
        self._ensure_selection_hook(getattr(self, "execution_table", None), self._on_execution_selection_changed)
        self._ensure_selection_hook(getattr(self, "signal_table", None), self._on_detail_signal_selection_changed)
        self._ensure_selection_hook(getattr(self, "trades_table", None), self._on_detail_trade_selection_changed)
        self._tune_workspace_splitters()
        self.set_market_timeframe(getattr(self, "market_timeframe_mode", "日线"))
        self.set_overview_focus(getattr(self, "overview_focus_mode", "市场总览"))
        self._hydrate_empty_workspace_panels()
        self._refresh_alert_cards_from_state()
        self._refresh_workspace_status_labels()
        self._refresh_submission_focus()
        self._refresh_scanner_focus_status()
        self._refresh_recommend_focus_status()
        self._refresh_recommend_bucket_panels()
        self._refresh_live_workspace_summary_panels()
        self._refresh_workspace_focus_banners()
        if hasattr(self, "overview_summary_cards"):
            self.overview_summary_cards["theme"].set_data("等待行情接入", "等待主线题材、龙头位次与前排数量刷新。")
            self.overview_summary_cards["source"].set_data("等待行情接入", "等待远程行情、缓存或示例数据接入。")
            self.overview_summary_cards["capital"].set_data("--", "等待主力资金画像、热度与换手同步。")
            self.overview_summary_cards["decision"].set_data("观察", "等待推荐池与交易决策联动生成。")

    def _refresh_workspace_status_labels(self) -> None:
        if hasattr(self, "top_badge"):
            current_name = self._workspace_name_for_index(self.tabs.currentIndex()) if hasattr(self, "tabs") else "龙头主控台"
            self.top_badge.setText(self._workspace_badge_text(current_name))
        self._refresh_shell_header()
        self._refresh_live_workspace_summary_panels()
        self._refresh_workspace_focus_banners()
        if hasattr(self, "broker_status_banner"):
            pending_orders = len(getattr(self, "order_intents", []) or [])
            submitted_orders = len(getattr(self, "order_submission_records", []) or [])
            summary = getattr(self, "last_broker_execution_summary", {}) or {}
            blockers = list(summary.get("blockers", []) or [])
            warnings = list(summary.get("warnings", []) or [])
            if blockers:
                banner_text = (
                    f"交易状态：红灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | "
                    f"下一步：先处理阻塞项。"
                )
            elif warnings and pending_orders:
                banner_text = (
                    f"交易状态：黄灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | "
                    f"下一步：复核风险后进入确认。"
                )
            elif pending_orders:
                banner_text = (
                    f"交易状态：绿灯 | 待审 {pending_orders} / 已提交 {submitted_orders} | "
                    f"下一步：优先推动高等级委托送审。"
                )
            elif submitted_orders:
                banner_text = f"交易状态：已提交 {submitted_orders} 笔 | 下一步：跟踪成交与回执。"
            else:
                banner_text = "交易状态：先看主线，再看闸门，最后进入委托确认。"
            self._set_label_text_if_changed(self.broker_status_banner, banner_text, tooltip=banner_text)
        if hasattr(self, "orders_focus_label") and not getattr(self, "order_intents", []):
            self._set_label_text_if_changed(
                self.orders_focus_label,
                ORDERS_DEFAULT_FOCUS_TEXT,
            )
        if hasattr(self, "trade_plan_focus_label") and not getattr(getattr(self, "current_trade_plan", None), "decisions", []):
            self._set_label_text_if_changed(
                self.trade_plan_focus_label,
                TRADE_PLAN_DEFAULT_FOCUS_TEXT,
            )
        if hasattr(self, "daily_pool_focus_label") and not getattr(self, "daily_pool_rows", []):
            self._set_label_text_if_changed(
                self.daily_pool_focus_label,
                RECOMMEND_DEFAULT_FOCUS_TEXT,
            )

    def _workspace_badge_text(self, current_name: str) -> str:
        label = current_name or "龙头主控台"
        if label == "策略扫描":
            scan_count = len(getattr(self, "scan_rows", []) or [])
            watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
            monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
            return f"量化猎手 Pro v2.2 · {label} · 扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}"
        if label == "打板监控":
            board_count = getattr(self, "board_table", None).rowCount() if hasattr(self, "board_table") else 0
            monitor_count = getattr(self, "board_monitor_table", None).rowCount() if hasattr(self, "board_monitor_table") else 0
            return f"量化猎手 Pro v2.2 · {label} · 候选 {board_count} / 监控 {monitor_count}"
        if label == "每日推荐":
            pool_count = len(getattr(self, "daily_pool_rows", []) or [])
            plan_count = len(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or [])
            return f"量化猎手 Pro v2.2 · {label} · 候选 {pool_count} / 计划 {plan_count}"
        if label == "交易执行":
            pending_orders = len(getattr(self, "order_intents", []) or [])
            submitted_orders = len(getattr(self, "order_submission_records", []) or [])
            return f"量化猎手 Pro v2.2 · {label} · 待审 {pending_orders} / 已提交 {submitted_orders}"
        return f"量化猎手 Pro v2.2 · {label}"

    def _set_label_text_if_changed(self, widget: QLabel | None, text: str, *, tooltip: str | None = None) -> None:
        if widget is None:
            return
        current_text_attr = getattr(widget, "text", None)
        current_text = current_text_attr() if callable(current_text_attr) else current_text_attr
        if current_text != text:
            widget.setText(text)
        current_tooltip_attr = getattr(widget, "toolTip", None)
        current_tooltip = current_tooltip_attr() if callable(current_tooltip_attr) else current_tooltip_attr
        if tooltip is not None and current_tooltip != tooltip:
            widget.setToolTip(tooltip)

    def _set_plain_text_if_changed(self, widget, text: str) -> None:
        if widget is None:
            return
        current_text = None
        if hasattr(widget, "toPlainText"):
            current_text = widget.toPlainText()
        else:
            current_text_attr = getattr(widget, "text", None)
            current_text = current_text_attr() if callable(current_text_attr) else current_text_attr
        if hasattr(widget, "setPlainText") and current_text != text:
            widget.setPlainText(text)

    def _refresh_shell_header(self) -> None:
        current_name = self._workspace_name_for_index(self.tabs.currentIndex()) if hasattr(self, "tabs") else "龙头主控台"
        if hasattr(self, "shell_workspace_chip"):
            set_shell_chip(self.shell_workspace_chip, current_name)

        market_source_label = {
            "remote": "远端实时",
            "cache": "本地缓存",
            "cache_only": "缓存只读",
            "sample": "示例模式",
            "unknown": "等待行情接入",
        }.get(getattr(self, "market_data_source", "unknown"), "等待行情接入")
        if getattr(self, "last_market_success_at", ""):
            market_value = f"{market_source_label} · {self.last_market_success_at[-8:]}"
        elif getattr(self, "last_market_error", ""):
            market_value = f"{market_source_label} · 异常"
        else:
            market_value = market_source_label
        if hasattr(self, "shell_market_chip"):
            set_shell_chip(self.shell_market_chip, market_value)

        dashboard_auto = hasattr(self, "dashboard_auto_refresh_checkbox") and self.dashboard_auto_refresh_checkbox.isChecked()
        scanner_auto = hasattr(self, "auto_refresh_checkbox") and self.auto_refresh_checkbox.isChecked()
        if self._is_job_running("market_refresh") or self._is_job_running("scan_universe"):
            refresh_value = "刷新中"
        elif dashboard_auto and scanner_auto:
            refresh_value = "双通道开启"
        elif dashboard_auto:
            refresh_value = "总览自动"
        elif scanner_auto:
            refresh_value = "扫描自动"
        else:
            refresh_value = "手动"
        if hasattr(self, "shell_refresh_chip"):
            set_shell_chip(self.shell_refresh_chip, refresh_value)

        runtime_value = {
            "running": "任务执行中",
            "success": "最近成功",
            "failed": "最近失败",
            "idle": "空闲",
        }.get(getattr(self, "last_job_status", "idle"), "空闲")
        if getattr(self, "last_job_name", "") and getattr(self, "last_job_status", "") == "running":
            runtime_value = self.last_job_name
        if hasattr(self, "shell_runtime_chip"):
            set_shell_chip(self.shell_runtime_chip, runtime_value)

        trade_plan = getattr(self, "current_trade_plan", None)
        trade_decisions = list(getattr(trade_plan, "decisions", []) or [])
        pending_orders = len(getattr(self, "order_intents", []) or [])
        submitted_orders = len(getattr(self, "order_submission_records", []) or [])
        pool_count = len(getattr(self, "daily_pool_rows", []) or [])
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []))
        warnings = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("warnings", []))
        risk_state = "红灯" if blockers else ("黄灯" if warnings else "绿灯")
        market_running = self._is_job_running("market_refresh")
        scan_running = self._is_job_running("scan_universe")
        if market_running and scan_running:
            pulse_headline = "系统脉搏：行情与扫描双线程运行中，工作台正在推进最新快照。"
        elif market_running:
            pulse_headline = "系统脉搏：行情刷新进行中，主控台正在更新市场总览与题材脉冲。"
        elif scan_running:
            pulse_headline = "系统脉搏：扫描任务进行中，候选池与监控焦点正在同步。"
        elif pending_orders:
            pulse_headline = (
                f"系统脉搏：推荐 {pool_count} 只，已形成计划 {len(trade_decisions)} 笔，"
                f"待审委托 {pending_orders} 笔。"
            )
        elif trade_decisions:
            pulse_headline = (
                f"系统脉搏：推荐池已转成交易计划，当前 {len(trade_decisions)} 笔可进入审查。"
            )
        elif pool_count:
            pulse_headline = f"系统脉搏：推荐池已生成 {pool_count} 只候选，正在等待计划与执行联动。"
        else:
            pulse_headline = "系统脉搏：终端正在等待市场快照、候选优先级与交易链路同步。"

        if market_running or scan_running:
            next_step = "下一动作：等待任务完成后回看主线与焦点池"
        elif blockers:
            next_step = f"下一动作：先处理阻塞项，再推进送审 | {blockers[0]}"
        elif pending_orders:
            next_step = f"下一动作：复核风险灯后送审 {pending_orders} 笔委托"
        elif trade_decisions:
            next_step = "下一动作：从高优先计划里选股送审"
        elif pool_count:
            next_step = "下一动作：由机会池继续生成交易计划"
        else:
            next_step = "下一动作：先建立市场快照，再生成机会池并推进交易链路"

        market_stamp = getattr(self, "last_market_success_at", "") or "等待行情接入"
        job_stamp = getattr(self, "last_job_finished_at", "") or "待执行"
        meta_segments = [
            f"风险灯 {risk_state}",
            f"已提交 {submitted_orders}",
            f"市场 {market_stamp[-8:] if len(market_stamp) >= 8 else market_stamp}",
            f"任务 {job_stamp[-8:] if len(job_stamp) >= 8 else job_stamp}",
        ]
        meta_text = " | ".join(meta_segments)
        if hasattr(self, "shell_pulse_label"):
            self._set_label_text_if_changed(self.shell_pulse_label, pulse_headline, tooltip=pulse_headline)
        if hasattr(self, "shell_pulse_hint"):
            self._set_label_text_if_changed(self.shell_pulse_hint, next_step, tooltip=next_step)
        if hasattr(self, "shell_pulse_meta"):
            self._set_label_text_if_changed(self.shell_pulse_meta, meta_text, tooltip=meta_text)

    def _ensure_action_row(
        self,
        target_widget: QWidget | None,
        row_name: str,
        actions: list[tuple[str, str, object]],
    ) -> None:
        if target_widget is None:
            return
        parent = target_widget.parentWidget()
        if parent is None or parent.findChild(QWidget, row_name) is not None:
            return
        layout = parent.layout()
        if layout is None:
            return

        row_frame = QFrame()
        row_frame.setObjectName(row_name)
        row_frame.setProperty("actionRow", True)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(10)
        for label, role, handler in actions:
            button = QPushButton(label)
            self._set_button_role(button, role)
            button.setMinimumHeight(36)
            button.clicked.connect(handler)
            row_layout.addWidget(button)
        row_layout.addStretch(1)
        layout.addWidget(row_frame)

    def _ensure_metric_row(
        self,
        target_widget: QWidget | None,
        row_name: str,
        specs: list[tuple[str, str, str]],
    ) -> tuple[dict[str, QLabel], dict[str, QLabel]] | None:
        if target_widget is None:
            return None
        parent = target_widget.parentWidget()
        if parent is None:
            return None
        existing = parent.findChild(QWidget, row_name)
        if existing is not None:
            value_labels = {
                label.objectName().split("__")[-1]: label
                for label in existing.findChildren(QLabel)
                if label.objectName().startswith(f"{row_name}__value__")
            }
            accent_labels = {
                label.objectName().split("__")[-1]: label
                for label in existing.findChildren(QLabel)
                if label.objectName().startswith(f"{row_name}__accent__")
            }
            return value_labels, accent_labels
        layout = parent.layout()
        if layout is None:
            return None

        row_frame = QFrame()
        row_frame.setObjectName(row_name)
        row_frame.setProperty("actionRow", True)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(0, 0, 0, 4)
        row_layout.setSpacing(8)
        value_labels: dict[str, QLabel] = {}
        accent_labels: dict[str, QLabel] = {}
        for key, title, accent in specs:
            card, value_label, accent_label = self._create_metric_card(title, "--", accent)
            value_label.setObjectName(f"{row_name}__value__{key}")
            accent_label.setObjectName(f"{row_name}__accent__{key}")
            row_layout.addWidget(card)
            value_labels[key] = value_label
            accent_labels[key] = accent_label
        layout.insertWidget(max(layout.indexOf(target_widget), 0), row_frame)
        return value_labels, accent_labels

    def _inject_overview_action_rows(self) -> None:
        self._ensure_action_row(
            getattr(self, "market_theme_brief_text", None),
            "overviewThemeActionRow",
            [
                ("查看推荐池", "tonal", self.open_overview_theme_to_recommend),
                ("查看消息催化", "ghost", self.open_overview_source_to_news),
            ],
        )

    def _inject_scanner_focus_cards(self) -> None:
        result = self._ensure_metric_row(
            getattr(self, "monitor_summary_text", None),
            "scannerFocusMetricRow",
            [
                ("symbol", "扫描焦点", "等待选中"),
                ("signal", "信号分数", "等待扫描"),
                ("action", "推荐动作", "等待联动"),
                ("monitor", "监控状态", "等待监控链路"),
            ],
        )
        if result is not None:
            self.scanner_focus_metric_labels, self.scanner_focus_metric_accents = result
            self._refresh_scanner_focus_cards("")

    def _inject_scanner_summary_cards(self) -> None:
        result = self._ensure_metric_row(
            getattr(self, "scan_table", None),
            "scannerSummaryMetricRow",
            [
                ("scan", "扫描结果", "等待扫描链路"),
                ("watch", "观察池", "等待编入"),
                ("summary", "回测摘要", "等待样本"),
                ("monitor", "盘中监控", "等待联动"),
            ],
        )
        if result is not None:
            self.scanner_summary_metric_labels, self.scanner_summary_metric_accents = result
            self._refresh_scanner_summary_cards("")

    def _inject_board_focus_cards(self) -> None:
        result = self._ensure_metric_row(
            getattr(self, "board_text", None),
            "boardFocusMetricRow",
            [
                ("symbol", "打板焦点", "等待候选"),
                ("score", "打板分", "等待计算"),
                ("risk", "风险等级", "等待评估"),
                ("action", "监控动作", "等待监控链路"),
            ],
        )
        if result is not None:
            self.board_focus_metric_labels, self.board_focus_metric_accents = result
            self._refresh_board_focus_cards("")
        self._ensure_action_row(
            getattr(self, "market_capital_text", None),
            "overviewCapitalActionRow",
            [
                ("去看推荐", "tonal", self.open_overview_capital_to_recommend),
                ("回到总览", "ghost", lambda: self._navigate_to_workspace("overview", "market_pool_table")),
            ],
        )
        self._ensure_action_row(
            getattr(self, "market_decision_text", None),
            "overviewDecisionActionRow",
            [
                ("去看交易", "accent", self.open_overview_decision_to_broker),
                ("去看推荐", "tonal", self.open_overview_theme_to_recommend),
            ],
        )

    def _inject_recommend_action_rows(self) -> None:
        self._ensure_action_row(
            getattr(self, "daily_pool_text", None),
            "recommendPoolActionRow",
            [
                ("查看总览", "ghost", lambda: self._navigate_to_workspace("overview", "market_pool_table")),
                ("定位推荐池", "tonal", lambda: self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")),
            ],
        )
        self._ensure_action_row(
            getattr(self, "trade_plan_text", None),
            "recommendPlanActionRow",
            [
                ("重算计划", "accent", self.trigger_trade_plan_refresh),
                ("去交易页", "tonal", self.open_trade_plan_broker_workspace),
                ("看观察池", "ghost", self.open_trade_plan_watch_bucket),
            ],
        )
        self._ensure_action_row(
            getattr(self, "market_pulse_text", None),
            "recommendPulseActionRow",
            [
                ("回到总览", "ghost", lambda: self._navigate_to_workspace("overview", "market_pool_table")),
                ("看消息催化", "tonal", self.open_overview_source_to_news),
            ],
        )
        self._ensure_action_row(
            getattr(self, "position_advice_text", None),
            "recommendHoldingActionRow",
            [
                ("查看风险池", "tonal", self.show_risk_bucket),
                ("去交易页", "accent", self.open_trade_plan_broker_workspace),
            ],
        )

    def _inject_board_action_rows(self) -> None:
        self._ensure_action_row(
            getattr(self, "board_text", None),
            "boardCandidateActionRow",
            [
                ("查看推荐", "tonal", self.open_board_symbol_in_recommend),
                ("查看扫描", "ghost", self.open_board_symbol_in_scanner),
                ("查看总览", "ghost", self.open_board_symbol_in_overview),
                ("去交易页", "accent", self.open_board_symbol_in_broker),
            ],
        )
        self._ensure_action_row(
            getattr(self, "board_monitor_text", None),
            "boardMonitorActionRow",
            [
                ("刷新监控", "accent", self._refresh_board_mode),
                ("查看推荐", "tonal", self.open_board_symbol_in_recommend),
                ("查看扫描", "ghost", self.open_board_symbol_in_scanner),
                ("查看总览", "ghost", self.open_board_symbol_in_overview),
            ],
        )

    def _inject_broker_action_rows(self) -> None:
        self._ensure_action_row(
            getattr(self, "broker_gate_summary_text", None),
            "brokerGateActionRow",
            [
                ("定位委托", "accent", self.open_broker_focus_orders),
                ("查看推荐", "tonal", self.open_broker_focus_recommend),
            ],
        )
        self._ensure_action_row(
            getattr(self, "broker_execution_text", None),
            "brokerExecutionActionRow",
            [
                ("查看委托", "accent", self.open_broker_focus_orders),
                ("查看成交", "tonal", self.open_broker_focus_execution),
                ("查看推荐", "ghost", self.open_broker_focus_recommend),
            ],
        )
        self._ensure_action_row(
            getattr(self, "broker_recap_text", None),
            "brokerRecapActionRow",
            [
                ("查看成交", "accent", self.open_broker_focus_execution),
                ("查看委托", "tonal", self.open_broker_focus_orders),
            ],
        )
        self._ensure_action_row(
            getattr(self, "runtime_log_text", None),
            "runtimeLogActionRow",
            [
                ("刷新诊断", "accent", self.refresh_runtime_panel),
                ("导出日志", "tonal", self.export_runtime_log),
                ("回到总览", "ghost", self.open_runtime_to_overview),
            ],
        )

    def _inject_detail_action_rows(self) -> None:
        self._ensure_action_row(
            getattr(self, "metrics_text", None),
            "detailMetricsActionRow",
            [
                ("回到总览", "ghost", self.open_detail_to_overview),
                ("查看推荐", "tonal", self.open_detail_to_recommend),
                ("查看扫描", "accent", self.open_detail_to_scanner),
            ],
        )
        self._ensure_action_row(
            getattr(self, "detail_decision_text", None),
            "detailDecisionActionRow",
            [
                ("查看推荐", "accent", self.open_detail_to_recommend),
                ("回到总览", "ghost", self.open_detail_to_overview),
            ],
        )
        self._ensure_action_row(
            getattr(self, "detail_execution_text", None),
            "detailExecutionActionRow",
            [
                ("去交易页", "accent", self.open_overview_decision_to_broker),
                ("查看扫描", "tonal", self.open_detail_to_scanner),
            ],
        )
        self._ensure_action_row(
            getattr(self, "detail_conclusion_text", None),
            "detailConclusionActionRow",
            [
                ("查看推荐", "tonal", self.open_detail_to_recommend),
                ("去交易页", "accent", self.open_overview_decision_to_broker),
            ],
        )

    def _inject_scanner_action_row(self) -> None:
        scan_box = getattr(self, "scan_table", None)
        if scan_box is None:
            return
        parent = scan_box.parentWidget()
        if parent is None:
            return
        layout = parent.layout()
        if layout is None or parent.findChild(QWidget, "scannerTopActionRow") is not None:
            return
        row_frame = QFrame()
        row_frame.setObjectName("scannerTopActionRow")
        row_frame.setProperty("actionRow", True)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(10, 8, 10, 8)
        row_layout.setSpacing(10)
        actions = [
            ("回到总览", "ghost", self.open_monitor_symbol_in_overview),
            ("查看推荐", "tonal", self.open_monitor_symbol_in_recommend),
            ("查看复盘", "accent", lambda: self._navigate_to_workspace("detail", "metrics_text")),
        ]
        for label, role, handler in actions:
            button = QPushButton(label)
            self._set_button_role(button, role)
            button.setMinimumHeight(36)
            button.clicked.connect(handler)
            row_layout.addWidget(button)
        row_layout.addStretch(1)
        layout.insertWidget(1, row_frame)

    def _inject_config_tool_panel(self) -> None:
        config_tab = getattr(self, "config_tab", None)
        if config_tab is None:
            return
        layout = config_tab.layout()
        if layout is None or config_tab.findChild(QGroupBox, "configToolPanel") is not None:
            return

        panel = QGroupBox("配置总控")
        panel.setObjectName("configToolPanel")
        panel.setProperty("actionRow", True)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(14, 10, 14, 10)
        panel_layout.setSpacing(16)

        summary = QLabel("参数、模板和授权会直接影响推荐池、盘前计划、盘中提醒和交易审查。")
        summary.setObjectName("inlineHint")
        summary.setWordWrap(True)

        quick = QLabel("建议顺序：先定模板与题材，再看总仓位，最后保存并刷新推荐链路。")
        quick.setObjectName("inlineHint")
        quick.setWordWrap(True)

        left = QVBoxLayout()
        left.setSpacing(6)
        left.addWidget(summary)
        left.addWidget(quick)
        panel_layout.addLayout(left, 3)
        panel_layout.addStretch(2)

        insert_index = 1 if layout.count() >= 1 else 0
        layout.insertWidget(insert_index, panel)

    def _build_workspace_summary_panel(self, object_name: str, title: str) -> tuple[QFrame, QLabel, QLabel, QLabel]:
        panel = QFrame()
        panel.setObjectName(object_name)
        panel.setProperty("actionRow", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setObjectName("inlineHint")
        headline_label = QLabel("--")
        headline_label.setObjectName("workspaceSummaryHeadline")
        detail_label = QLabel("--")
        detail_label.setObjectName("inlineHint")
        meta_label = QLabel("--")
        meta_label.setObjectName("inlineHint")

        for label in (title_label, headline_label, detail_label, meta_label):
            label.setWordWrap(True)
            layout.addWidget(label)
        return panel, headline_label, detail_label, meta_label

    def _inject_live_workspace_summary_panels(self) -> None:
        scanner_panel = getattr(self, "scanner_tab", None)
        if isinstance(scanner_panel, QWidget):
            tool_panel = scanner_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "scanner_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("scannerLiveSummaryPanel", "扫描态势")
                    grid.addWidget(panel, 1, 1)
                    self.scanner_live_summary_headline = headline
                    self.scanner_live_summary_detail = detail
                    self.scanner_live_summary_meta = meta

        board_panel = getattr(self, "board_tab", None)
        if isinstance(board_panel, QWidget):
            tool_panel = board_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "board_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("boardLiveSummaryPanel", "打板态势")
                    grid.addWidget(panel, 1, 1)
                    self.board_live_summary_headline = headline
                    self.board_live_summary_detail = detail
                    self.board_live_summary_meta = meta

        detail_panel = getattr(self, "detail_tab", None)
        if isinstance(detail_panel, QWidget):
            tool_panel = detail_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "detail_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("detailLiveSummaryPanel", "复盘态势")
                    grid.addWidget(panel, 1, 1)
                    self.detail_live_summary_headline = headline
                    self.detail_live_summary_detail = detail
                    self.detail_live_summary_meta = meta

        config_panel = getattr(self, "config_tab", None)
        if isinstance(config_panel, QWidget):
            tool_panel = config_panel.findChild(QGroupBox, "configToolPanel")
            if tool_panel is not None and getattr(self, "config_live_summary_headline", None) is None:
                layout = tool_panel.layout()
                if isinstance(layout, QHBoxLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("configLiveSummaryPanel", "配置状态")
                    layout.addWidget(panel, 2)
                    self.config_live_summary_headline = headline
                    self.config_live_summary_detail = detail
                    self.config_live_summary_meta = meta

    def _inject_workspace_focus_banners(self) -> None:
        banner_specs = [
            ("scanner_tab", "scan_table", "scanner_focus_banner"),
            ("board_tab", "board_table", "board_focus_banner"),
            ("detail_tab", "metrics_text", "detail_focus_banner"),
        ]
        for tab_name, anchor_name, banner_name in banner_specs:
            tab = getattr(self, tab_name, None)
            anchor = getattr(self, anchor_name, None)
            if not isinstance(tab, QWidget) or anchor is None or getattr(self, banner_name, None) is not None:
                continue
            parent = anchor.parentWidget()
            if parent is None:
                continue
            layout = parent.layout()
            if layout is None:
                continue
            banner = QLabel("焦点标的：等待联动")
            banner.setObjectName("workspaceFocusBanner")
            banner.setWordWrap(True)
            layout.insertWidget(0, banner)
            setattr(self, banner_name, banner)

    def _apply_identity_table_headers(self) -> None:
        if hasattr(self, "scan_table"):
            self.scan_table.setColumnCount(11)
            self.scan_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"]
            )
            self.scan_table.setColumnHidden(1, True)
        if hasattr(self, "summary_table"):
            self.summary_table.setColumnCount(8)
            self.summary_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "交易代码", "交易笔数", "收益率", "最大回撤", "胜率", "期末权益"]
            )
            self.summary_table.setColumnHidden(1, True)
        if hasattr(self, "monitor_table"):
            self.monitor_table.setColumnCount(9)
            self.monitor_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "收盘价", "信号日期", "更新时间"]
            )
            self.monitor_table.setColumnHidden(1, True)
        if hasattr(self, "board_table"):
            self.board_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "交易代码", "打板级别", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"]
            )
            self.board_table.setColumnHidden(1, True)
        if hasattr(self, "board_monitor_table"):
            self.board_monitor_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "交易代码", "监控状态", "强度", "连续性", "回封概率", "炸板风险", "动作建议", "备注"]
            )
            self.board_monitor_table.setColumnHidden(1, True)
        if hasattr(self, "leader_table"):
            self.leader_table.setHorizontalHeaderLabels(
                ["股票标识", "股票ID", "题材", "级别", "角色", "窗口", "风险", "龙头分", "动作", "说明"]
            )
            self.leader_table.setColumnHidden(1, True)
        if hasattr(self, "daily_pool_table"):
            self.daily_pool_table.setColumnCount(len(DAILY_POOL_TABLE_HEADERS))
            self.daily_pool_table.setHorizontalHeaderLabels(DAILY_POOL_TABLE_HEADERS)
            self.daily_pool_table.setColumnHidden(2, True)
        if hasattr(self, "market_pool_table"):
            self.market_pool_table.setHorizontalHeaderLabels(["序", "股票标识", "资金标签", "策略标签", "涨跌幅", "最新价"])

    def _refresh_live_workspace_summary_panels(self) -> None:
        if hasattr(self, "scanner_live_summary_headline"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            monitor_count = self.monitor_table.rowCount() if hasattr(self, "monitor_table") else 0
            self.scanner_live_summary_headline.setText(f"扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}")
            self.scanner_live_summary_detail.setText(
                f"自动刷新：{'开启' if hasattr(self, 'auto_refresh_checkbox') and self.auto_refresh_checkbox.isChecked() else '关闭'} | 最近刷新：{getattr(self, 'last_refresh_label', QLabel('--')).text()}"
            )
            self.scanner_live_summary_meta.setText(
                f"当前股票池：{getattr(self, 'universe_label', QLabel('--')).text()}"
            )

        if hasattr(self, "board_live_summary_headline"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            self.board_live_summary_headline.setText(f"候选 {candidate_count} / 监控 {monitor_count}")
            auto_export = "开启" if hasattr(self, "auto_review_export_checkbox") and self.auto_review_export_checkbox.isChecked() else "关闭"
            self.board_live_summary_detail.setText(f"收盘导出：{auto_export} | 焦点联动：扫描 / 推荐 / 复盘")
            self.board_live_summary_meta.setText(getattr(self, "board_focus_label", QLabel("等待焦点同步")).text() if hasattr(self, "board_focus_label") else "等待焦点同步")

        if hasattr(self, "detail_live_summary_headline"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            active_symbol = getattr(self, "active_symbol", "") or "未选中"
            self.detail_live_summary_headline.setText(f"当前标的：{active_symbol}")
            self.detail_live_summary_detail.setText(f"近期信号 {signal_count} 条 | 交易记录 {trade_count} 条")
            self.detail_live_summary_meta.setText(getattr(self, "active_symbol_label", QLabel("当前标的：未选择")).text())

        if hasattr(self, "config_live_summary_headline"):
            plan_text = self.state.license_plan or "TRIAL"
            top_theme_limit, max_total_exposure, _ = self._current_strategy_runtime_config()
            self.config_live_summary_headline.setText(f"方案：{plan_text} | 主线前排 {top_theme_limit}")
            self.config_live_summary_detail.setText(f"总仓位上限 {max_total_exposure:.2f} | 模板 {self.daily_plan_template_combo.currentText() if hasattr(self, 'daily_plan_template_combo') else '--'}")
            focus_theme_text = self.focus_themes_input.text().strip() if hasattr(self, "focus_themes_input") else ""
            self.config_live_summary_meta.setText(f"关注题材：{focus_theme_text or '未设置'}")

    def _refresh_workspace_focus_banners(self) -> None:
        target_symbol = self.active_symbol or self._selected_symbol_from_watchlist() or self._selected_board_symbol() or ""
        stock_name = self._stock_name_for_symbol(target_symbol) if target_symbol else "等待联动"
        stock_id = self._stock_id_for_symbol(target_symbol) if target_symbol else "--"
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        tone = self._focus_banner_tone(symbol=target_symbol, recommendation=recommendation, scan_row=scan_row)
        if hasattr(self, "scanner_focus_banner"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            text = (
                f"扫描焦点：{stock_name} ({stock_id} / {target_symbol}) | 扫描 {scan_count} | 观察 {watch_count}"
                if target_symbol
                else "扫描焦点：等待从扫描榜、观察池或盘中监控联动标的"
            )
            self._set_focus_banner_state(self.scanner_focus_banner, tone if target_symbol else "idle", text)
        if hasattr(self, "board_focus_banner"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            text = (
                f"打板焦点：{stock_name} ({stock_id} / {target_symbol}) | 候选 {candidate_count} | 监控 {monitor_count}"
                if target_symbol
                else "打板焦点：等待扫描页或推荐页同步强势候选"
            )
            self._set_focus_banner_state(self.board_focus_banner, tone if target_symbol else "idle", text)
        if hasattr(self, "detail_focus_banner"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            text = (
                f"复盘焦点：{stock_name} ({stock_id} / {target_symbol}) | 信号 {signal_count} | 成交 {trade_count}"
                if target_symbol
                else "复盘焦点：等待扫描、推荐或打板页同步单票标的"
            )
            self._set_focus_banner_state(self.detail_focus_banner, tone if target_symbol else "idle", text)

    def _update_cross_workspace_focus_labels(self, symbol: str) -> None:
        if not symbol:
            return
        stock_name = self._stock_name_for_symbol(symbol)
        stock_id = self._stock_id_for_symbol(symbol)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == symbol), None)
        board_candidate = self._board_candidate_snapshot_for_symbol(symbol)
        submission_hit = any(str(item.get("symbol", "") or "") == symbol for item in getattr(self, "order_submission_records", []))

        if hasattr(self, "daily_pool_focus_label"):
            action_text = self._display_action(getattr(recommendation, "action", "WATCH")) if recommendation is not None else "观察"
            self._set_label_text_if_changed(
                self.daily_pool_focus_label,
                f"当前焦点：{stock_name} ({stock_id} / {symbol}) | 动作 {action_text} | 已联动计划与交易",
            )
        if hasattr(self, "scan_summary_label"):
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"扫描状态：当前联动 {stock_name} ({stock_id}) | 观察池 {watch_count} | 已同步推荐/打板/交易",
            )
        if hasattr(self, "broker_status_banner"):
            broker_suffix = "已同步提交记录" if submission_hit else "等待生成或提交委托"
            self._set_label_text_if_changed(
                self.broker_status_banner,
                f"交易状态：当前联动 {stock_name} ({stock_id}) | {broker_suffix}",
            )
        if hasattr(self, "orders_focus_label"):
            self._set_label_text_if_changed(
                self.orders_focus_label,
                f"委托动作面板 / 委托焦点：{stock_name} ({stock_id}) | 已同步推荐池与执行链路",
            )
        board_text = (
            f"打板焦点：{stock_name} ({stock_id}) | {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']}"
            if board_candidate is not None
            else f"打板焦点：{stock_name} ({stock_id}) | 等待候选或监控联动"
        )
        if hasattr(self, "board_focus_label"):
            self._set_label_text_if_changed(self.board_focus_label, board_text)

    def _on_daily_pool_selection_changed(self) -> None:
        current = self._selected_daily_pool_recommendation()
        if current is not None:
            symbol = getattr(current, "symbol", "") or ""
            stock_id = getattr(current, "stock_id", "") or self._stock_id_for_symbol(symbol)
            if symbol:
                self._select_trade_plan_row_by_stock_id(stock_id)
                self._select_position_advice_row_by_stock_id(stock_id)
                self._select_order_intent_row_for_symbol(symbol)
                self._select_execution_row_for_symbol(symbol)
                self._select_board_candidate_row_for_symbol(symbol)
                self._select_board_monitor_row_for_symbol(symbol)
                self._select_scan_row_for_symbol(symbol)
                self._select_watchlist_symbol(symbol)
                self._select_monitor_row_for_symbol(symbol)
                if symbol in self.universe_bars:
                    self.select_symbol(symbol, origin="recommend")
                self._update_cross_workspace_focus_labels(symbol)
                if hasattr(self, "recommend_focus_banner"):
                    self._set_focus_banner_state(
                        self.recommend_focus_banner,
                        self._focus_banner_tone(symbol=symbol, recommendation=current),
                        f"推荐焦点：{current.stock_name} ({stock_id} / {symbol}) | 已联动计划、仓位、委托、执行与打板",
                    )
        self._refresh_recommendation_focus_panels()
        self._refresh_strategy_focus_detail()

    def _on_execution_selection_changed(self) -> None:
        record = self._selected_submission_record()
        symbol = str((record or {}).get("symbol", "") or "")
        if symbol:
            self._sync_execution_focus_from_symbol(symbol)
            self._update_cross_workspace_focus_labels(symbol)
            if hasattr(self, "broker_status_banner"):
                self._set_label_text_if_changed(
                    self.broker_status_banner,
                    f"交易状态：已定位到 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) 的提交记录，可继续回看委托与复盘。",
                )
        self._refresh_submission_focus()

    def _sync_execution_focus_from_symbol(self, symbol: str) -> None:
        if not symbol:
            return
        stock_id = self._stock_id_for_symbol(symbol)
        self._select_daily_pool_row_by_stock_id(stock_id)
        self._select_trade_plan_row_by_stock_id(stock_id)
        self._select_position_advice_row_by_stock_id(stock_id)
        self._select_order_intent_row_for_symbol(symbol)
        self._select_execution_row_for_symbol(symbol)
        self._select_board_candidate_row_for_symbol(symbol)
        self._select_board_monitor_row_for_symbol(symbol)
        self._select_scan_row_for_symbol(symbol)
        self._select_watchlist_symbol(symbol)
        self._select_monitor_row_for_symbol(symbol)
        if symbol in getattr(self, "universe_bars", {}):
            self.select_symbol(symbol, origin="execution")
        else:
            self._refresh_workspace_focus_banners()
            self._refresh_live_workspace_summary_panels()

    def _on_execution_selection_changed(self) -> None:
        record = self._selected_submission_record()
        symbol = str((record or {}).get("symbol", "") or "")
        if symbol:
            self._sync_execution_focus_from_symbol(symbol)
            if hasattr(self, "broker_status_banner"):
                self._set_label_text_if_changed(
                    self.broker_status_banner,
                    f"交易状态：已定位到 {self._stock_name_for_symbol(symbol)} 的提交记录，可继续回看委托与复盘。",
                )
        self._refresh_submission_focus()

    def _on_daily_pool_selection_changed(self) -> None:
        current = self._selected_daily_pool_recommendation()
        if current is not None:
            symbol = getattr(current, "symbol", "") or ""
            stock_id = getattr(current, "stock_id", "") or self._stock_id_for_symbol(symbol)
            if symbol:
                self._select_trade_plan_row_by_stock_id(stock_id)
                self._select_position_advice_row_by_stock_id(stock_id)
                self._select_order_intent_row_for_symbol(symbol)
                self._select_execution_row_for_symbol(symbol)
                self._select_board_candidate_row_for_symbol(symbol)
                self._select_board_monitor_row_for_symbol(symbol)
                if symbol in self.universe_bars:
                    self.select_symbol(symbol, origin="recommend")
                if hasattr(self, "recommend_focus_banner"):
                    self._set_focus_banner_state(
                        self.recommend_focus_banner,
                        self._focus_banner_tone(symbol=symbol, recommendation=current),
                        f"推荐焦点：{current.stock_name} ({stock_id} / {symbol}) | 已联动计划、仓位、委托与执行",
                    )
        self._refresh_recommendation_focus_panels()
        self._refresh_strategy_focus_detail()

    def _focus_banner_tone(self, symbol: str = "", recommendation=None, scan_row=None) -> str:
        if not symbol:
            return "idle"
        action = str(getattr(recommendation, "action", "") or getattr(scan_row, "action", "") or "").upper()
        risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
        if action in {"SELL", "REDUCE"} or any(token in risk_flag for token in ["红", "高", "风险"]):
            return "risk"
        if action == "BUY":
            return "buy"
        if action == "WATCH" or action:
            return "watch"
        return "idle"

    def _set_focus_banner_state(self, banner: QLabel, tone: str, text: str) -> None:
        changed = banner.property("stateTone") != tone
        if changed:
            banner.setProperty("stateTone", tone)
            banner.style().unpolish(banner)
            banner.style().polish(banner)
        self._set_label_text_if_changed(banner, text)

    def _ensure_selection_hook(self, widget: QWidget | None, handler) -> None:
        if widget is None or not hasattr(widget, "itemSelectionChanged"):
            return
        flag_name = f"_{getattr(widget, 'objectName', lambda: '')() or id(widget)}_selection_hooked"
        if getattr(self, flag_name, False):
            return
        widget.itemSelectionChanged.connect(handler)
        setattr(self, flag_name, True)

    def _tune_workspace_splitters(self) -> None:
        splitter_sizes: list[tuple[str, list[int]]] = [
            ("overview_main_splitter", [330, 1120, 350]),
            ("overview_left_notes_splitter", [125, 115, 180]),
            ("overview_mini_chart_splitter", [2, 2, 1]),
            ("recommend_dispatch_splitter", [420, 560, 320]),
            ("recommend_summary_splitter", [460, 820]),
            ("recommend_recap_middle_splitter", [380, 860]),
            ("recommend_recap_bottom_splitter", [360, 880]),
            ("recommend_review_splitter", [700, 540]),
            ("broker_control_splitter", [520, 520, 360]),
            ("broker_middle_splitter", [500, 720]),
            ("broker_order_focus_splitter", [780, 360]),
        ]
        for attr_name, sizes in splitter_sizes:
            splitter = getattr(self, attr_name, None)
            if splitter is not None:
                self._configure_splitter(splitter, sizes)

        detail_tab = getattr(self, "detail_tab", None)
        if detail_tab is not None:
            detail_splitters = [splitter for splitter in detail_tab.findChildren(QSplitter) if splitter.count() >= 2]
            if len(detail_splitters) >= 2:
                self._configure_splitter(detail_splitters[0], [420, 420, 420] if detail_splitters[0].count() == 3 else [520, 680])
                self._configure_splitter(detail_splitters[-1], [520, 680] if detail_splitters[-1].count() == 2 else [420, 420, 420])

    def _normalize_detail_workspace_texts(self) -> None:
        title_map = {
            "metrics_text": "策略摘要",
            "detail_decision_text": "交易决策画像",
            "detail_execution_text": "执行状态回放",
            "detail_conclusion_text": "复盘结论",
            "signal_table": "近期信号",
            "trades_table": "交易记录",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        if hasattr(self, "signal_table"):
            self.signal_table.setHorizontalHeaderLabels(["日期", "信号", "评分", "收盘价", "原因"])
        if hasattr(self, "trades_table"):
            self.trades_table.setHorizontalHeaderLabels(["入场日期", "离场日期", "买入价", "卖出价", "股数", "盈亏", "退出原因"])
        if not getattr(self, "active_symbol", ""):
            if hasattr(self, "detail_decision_text"):
                self._set_plain_text_if_changed(
                    self.detail_decision_text,
                    "交易决策画像\n\n"
                    "选中一只股票后，这里会汇总主线地位、动作建议、买卖区间和核心逻辑，帮助你先看懂再决定是否出手。"
                )
            if hasattr(self, "detail_execution_text"):
                self._set_plain_text_if_changed(
                    self.detail_execution_text,
                    "执行状态回放\n\n"
                    "这里会关联委托建议、提交结果和成交记录，用来检查执行是否偏离原计划。"
                )
            if hasattr(self, "detail_conclusion_text"):
                self._set_plain_text_if_changed(
                    self.detail_conclusion_text,
                    "复盘结论\n\n"
                    "这里会沉淀单票的关键得失、纪律执行情况，以及下一步是否值得继续跟踪。"
                )

    def _normalize_broker_workspace_texts(self) -> None:
        title_map = {
            "holdings_table": "当前持仓",
            "orders_table": "委托建议",
            "execution_table": "提交记录",
            "broker_recap_text": "成交回顾",
            "broker_order_focus_text": "当前委托详情",
            "runtime_log_text": "运行日志",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        if hasattr(self, "holdings_table"):
            self.holdings_table.setHorizontalHeaderLabels(["代码", "持仓数量", "可卖数量", "成本价", "市值"])
        if hasattr(self, "orders_table"):
            self.orders_table.setHorizontalHeaderLabels(
                ["优先级", "代码", "动作", "价格", "数量", "预计占用", "盈亏比", "止损", "目标", "主线闸门", "信号日期", "原因摘要", "风险灯"]
            )
        if hasattr(self, "execution_table"):
            self.execution_table.setHorizontalHeaderLabels(["时间", "订单", "成交", "代码", "动作", "价格", "数量", "错误", "信息"])
        if hasattr(self, "orders_focus_label"):
            self.orders_focus_label.setText(ORDERS_DEFAULT_FOCUS_TEXT)
        if not getattr(self, "order_intents", []):
            if hasattr(self, "broker_order_focus_text"):
                self._set_plain_text_if_changed(
                    self.broker_order_focus_text,
                    "当前委托详情\n\n"
                    "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
                    "先在上方选中一条委托建议，再决定是否一键确认提交。\n"
                    "如果暂时没有委托，可以先去推荐页生成送审候选，再回到这里检查闸门。"
                )
        if not getattr(self, "order_submission_records", []):
            if hasattr(self, "order_result_text"):
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "执行回放\n\n"
                    "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                    "刷新委托或提交模拟单后，这里会自动切换到最新一条。\n"
                    "你也可以从打板页直接把候选送进来，再看这里的执行结果。"
                )
            if hasattr(self, "broker_recap_text"):
                self._set_plain_text_if_changed(
                    self.broker_recap_text,
                    "成交回顾\n\n"
                    "这里用于复盘通过率、阻塞原因、成交偏差和主线是否仍然成立。\n"
                    "提交记录产生后，可回到这里快速检查执行质量。\n"
                    "如果后续生成了更多委托记录，这里会自动切到最新一笔。"
                )

    def _normalize_recommend_workspace_texts(self) -> None:
        title_map = {
            "recommend_core_bucket_text": "主线前排",
            "recommend_watch_bucket_text": "观察池",
            "recommend_risk_bucket_text": "风险池",
            "strategy_detail_text": "战法明细",
            "strategy_path_text": "主线推演",
            "daily_pool_text": "今日优先候选",
            "market_pulse_text": "市场温度",
            "position_advice_text": "持仓处理",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        if hasattr(self, "recommend_stage_tabs"):
            for index, label in enumerate(["执行", "策略", "复盘"]):
                if index < self.recommend_stage_tabs.count():
                    self.recommend_stage_tabs.setTabText(index, label)

        button_labels = {
            "show_core_execution_bucket": "只看主线前排",
            "show_watch_bucket": "只看观察池",
            "show_risk_bucket": "只看风险池",
        }
        for button in self.findChildren(QPushButton):
            text = button.text().strip()
            if text in {"鍙湅涓荤嚎鍓嶆帓", "只看主线前排"}:
                button.setText(button_labels["show_core_execution_bucket"])
            elif text in {"鍙湅瑙傚療姹?", "只看观察池"}:
                button.setText(button_labels["show_watch_bucket"])
            elif text in {"鍙湅鍥為伩姹?", "只看风险池", "只看回避池"}:
                button.setText(button_labels["show_risk_bucket"])
            elif text == "导出运行日志":
                button.setText("导出日志")

        card_title_map = {
            "涔板叆": "买入",
            "瑙傚療": "观察",
            "鍑忎粨": "减仓",
            "绂诲満": "离场",
            "甯傚満鎯呯华": "市场情绪",
            "涓荤嚎棰樻潗": "主线题材",
            "楂樹紭鍏堢瓥鐣?": "高优先策略",
            "涓€鍙锋爣鐨?": "焦点标的",
        }
        for card_map_name in ["action_flow_cards", "priority_cards"]:
            card_map = getattr(self, card_map_name, None)
            if not card_map:
                continue
            for card in card_map.values():
                title_label = getattr(card, "title_label", None)
                if title_label is not None:
                    title_label.setText(card_title_map.get(title_label.text(), title_label.text()))

        strategy_combo = getattr(self, "strategy_detail_combo", None)
        if strategy_combo is not None and strategy_combo.count():
            labels = ["龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"]
            current = strategy_combo.currentText()
            strategy_combo.blockSignals(True)
            strategy_combo.clear()
            strategy_combo.addItems(labels)
            strategy_combo.setCurrentText(current if current in labels else labels[0])
            strategy_combo.blockSignals(False)

    def _normalize_board_workspace_texts(self) -> None:
        title_map = {
            "board_text": "打板候选池",
            "board_monitor_text": "炸板 / 回封监控",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        for button in self.findChildren(QPushButton):
            text = button.text().strip()
            if text == "鍒锋柊鎵撴澘姹?":
                button.setText("刷新打板池")
            elif text == "瀵煎嚭鐩樺墠浜ゆ槗璁″垝":
                button.setText("导出盘前交易计划")
            elif text == "瀵煎嚭鏀剁洏澶嶇洏鏃ユ姤":
                button.setText("导出收盘复盘日报")

        if hasattr(self, "auto_review_export_checkbox"):
            self.auto_review_export_checkbox.setText("15:05 后自动导出复盘日报")
        if hasattr(self, "board_text"):
            text = self.board_text.toPlainText().strip()
            if not text or text in {
                "先生成每日推荐池，再生成打板候选。",
                "打板候选池",
            }:
                self._set_plain_text_if_changed(
                    self.board_text,
                    "打板候选池\n\n"
                    "这里会汇总强势连板、回封质量、入场价位和风险等级。\n"
                    "先生成推荐池或在扫描页选中一只股票，这里会自动切到对应打板焦点。\n"
                    "打板页会优先展示主线前排、接力确定性和可执行的回封区间。"
                )
        if hasattr(self, "board_monitor_text"):
            text = self.board_monitor_text.toPlainText().strip()
            if not text or text in {
                "打板监控会显示回封观察、炸板风险和强势连板候选。",
                "炸板 / 回封监控",
            }:
                self._set_plain_text_if_changed(
                    self.board_monitor_text,
                    "炸板 / 回封监控\n\n"
                    "这里会持续跟踪回封强度、炸板风险和是否还保留博弈价值。\n"
                    "盘中监控生成后，会自动切换到当前最值得盯的标的，也会跟扫描页联动。\n"
                    "当候选和监控都到位时，这里会告诉你是继续观察、转交易还是直接放弃。"
                )

    def _repair_runtime_widget_texts(self) -> None:
        bad_to_good = {
            "鍙湅涓荤嚎鍓嶆帓": "只看主线前排",
            "鍙湅瑙傚療姹?": "只看观察池",
            "鍙湅鍥為伩姹?": "只看风险池",
            "只看回避池": "只看风险池",
            "瀵煎嚭鐩樺墠浜ゆ槗璁″垝": "导出盘前交易计划",
            "瀵煎嚭鏀剁洏澶嶇洏鏃ユ姤": "导出收盘复盘日报",
            "瀵煎嚭杩愯鏃ュ織": "导出日志",
            "鍒锋柊璇婃柇": "刷新诊断",
            "鍒锋柊鎵撴澘姹?": "刷新打板池",
            "涔板叆": "买入",
            "瑙傚療": "观察",
            "鍑忎粨": "减仓",
            "绂诲満": "离场",
            "甯傚満鎯呯华": "市场情绪",
            "涓荤嚎棰樻潗": "主线题材",
            "楂樹紭鍏堢瓥鐣?": "高优先策略",
            "涓€鍙锋爣鐨?": "焦点标的",
        }

        def normalize_text(raw: str) -> str:
            text = (raw or "").strip()
            return bad_to_good.get(text, raw)

        for button in self.findChildren(QPushButton):
            normalized = normalize_text(button.text())
            if normalized != button.text():
                button.setText(normalized)

        for checkbox in self.findChildren(QCheckBox):
            normalized = normalize_text(checkbox.text())
            if normalized != checkbox.text():
                self._set_label_text_if_changed(checkbox, normalized)

        for label in self.findChildren(QLabel):
            normalized = normalize_text(label.text())
            if normalized != label.text():
                self._set_label_text_if_changed(label, normalized)

        for box in self.findChildren(QGroupBox):
            normalized = normalize_text(box.title())
            if normalized != box.title():
                box.setTitle(normalized)

        for tabs in self.findChildren(QTabWidget):
            for index in range(tabs.count()):
                text = tabs.tabText(index)
                normalized = normalize_text(text)
                if normalized != text:
                    tabs.setTabText(index, normalized)

    def _normalize_overview_builder_texts(self) -> None:
        if hasattr(self, "market_search_input"):
            self.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材")
        if hasattr(self, "market_theme_combo"):
            self.market_theme_combo.blockSignals(True)
            self.market_theme_combo.clear()
            self.market_theme_combo.addItem("全部")
            self.market_theme_combo.blockSignals(False)
        if hasattr(self, "market_history_date_combo"):
            self.market_history_date_combo.blockSignals(True)
            self.market_history_date_combo.clear()
            self.market_history_date_combo.addItem("最新")
            self.market_history_date_combo.blockSignals(False)
        if hasattr(self, "market_refresh_button"):
            self.market_refresh_button.setText("一键刷新算法池")
        if hasattr(self, "market_history_reset_button"):
            self.market_history_reset_button.setText("回到最新")
        if hasattr(self, "dashboard_auto_refresh_checkbox"):
            self.dashboard_auto_refresh_checkbox.setText("盘中自动刷新")
        if hasattr(self, "market_status_label"):
            self.market_status_label.setText("总览状态：正在建立市场快照...")
        if hasattr(self, "market_header_label"):
            self.market_header_label.setText("市场机会工作台")
        if hasattr(self, "market_subheader_label"):
            self.market_subheader_label.setText("统一查看主线龙头、趋势机会、消息催化、买卖决策和复盘研究。")
        if hasattr(self, "market_signal_label"):
            self.market_signal_label.setText("资金模型 / 策略标签 / 主力净流入 / 换手率")
        if hasattr(self, "market_quote_label"):
            self.market_quote_label.setText("开高低收 / 涨跌幅 / 换手 / 主力净流入 / 龙头级别 / 股票池")

        button_groups = [
            ("overview_quick_buttons", ["市场总览", "主线龙头", "趋势机会", "消息催化", "买卖决策", "复盘研究"], self.activate_overview_quick_action),
            ("market_filter_buttons", ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"], self.set_market_filter),
            ("timeframe_buttons", ["分时", "1分", "5分", "15分", "30分", "60分", "日线", "周线", "月线"], self.set_market_timeframe),
            ("history_window_buttons", ["近1月", "近3月", "近1年", "全部"], self.set_market_history_window),
            ("secondary_indicator_buttons", ["MACD", "RSI", "KDJ"], self.set_market_secondary_indicator),
        ]
        for attr_name, labels, handler in button_groups:
            current_map = getattr(self, attr_name, None)
            if not current_map:
                continue
            buttons = list(current_map.values())
            normalized: dict[str, QPushButton] = {}
            for index, button in enumerate(buttons):
                label = labels[index] if index < len(labels) else button.text()
                try:
                    button.clicked.disconnect()
                except Exception:
                    pass
                button.setText(label)
                button.clicked.connect(lambda checked=False, current=label, callback=handler: callback(current))
                normalized[label] = button
            setattr(self, attr_name, normalized)

        for name, button in getattr(self, "market_overlay_buttons", {}).items():
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(lambda checked=False, current=name: self.toggle_market_overlay(current))

        if hasattr(self, "market_pool_table"):
            self.market_pool_table.setHorizontalHeaderLabels(["代码", "股票", "资金标签", "策略标签", "涨跌幅", "最新价"])

        if hasattr(self, "right_intel_tabs"):
            self.right_intel_tabs.setTabText(0, "主题摘要")
            self.right_intel_tabs.setTabText(1, "资金决策")

        for attr_name, title in {"market_news_group": "消息面"}.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setTitle"):
                widget.setTitle(title)

    def _normalize_aux_workspace_texts(self) -> None:
        if hasattr(self, "tabs"):
            tab_labels = ["龙头主控台", "策略扫描", "每日推荐", "打板监控", "配置", "统一登录", "明细复盘", "交易执行"]
            for index, label in enumerate(tab_labels):
                if index < self.tabs.count():
                    self.tabs.setTabText(index, label)

        if hasattr(self, "auth_channel_combo"):
            current = self.auth_channel_combo.currentData()
            self.auth_channel_combo.blockSignals(True)
            self.auth_channel_combo.clear()
            self.auth_channel_combo.addItem("东方财富", "eastmoney")
            self.auth_channel_combo.addItem("GM", "gm")
            self.auth_channel_combo.addItem("自定义", "custom")
            for idx in range(self.auth_channel_combo.count()):
                if self.auth_channel_combo.itemData(idx) == current:
                    self.auth_channel_combo.setCurrentIndex(idx)
                    break
            self.auth_channel_combo.blockSignals(False)

        text_map = {
            "active_symbol_label": "当前标的：未选择",
            "broker_status_banner": BROKER_DEFAULT_STATUS_TEXT,
            "orders_focus_label": ORDERS_DEFAULT_FOCUS_TEXT,
            "trade_plan_focus_label": TRADE_PLAN_DEFAULT_FOCUS_TEXT,
            "recommend_status_label": RECOMMEND_DEFAULT_STATUS_TEXT,
            "recommend_empty_title": RECOMMEND_DEFAULT_EMPTY_TITLE,
            "recommend_empty_meta": RECOMMEND_DEFAULT_EMPTY_META,
            "daily_pool_focus_label": RECOMMEND_DEFAULT_FOCUS_TEXT,
            "universe_label": "股票池目录：未加载",
            "scan_summary_label": "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。",
            "last_refresh_label": "最近刷新：等待市场快照建立",
        }
        for attr_name, value in text_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                if not widget.text().strip() or any(token in widget.text() for token in ["鍛", "鏃", "璁", "缁", "閫", "榫", "甯"]):
                    widget.setText(value)

        button_map = {
            "recommend_empty_sample_button": RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
            "recommend_empty_refresh_button": RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
            "broker_focus_blocker_button": "定位阻塞",
            "broker_focus_priority_button": "定位前排",
            "generate_order_suggestions_button": "生成盘中计划",
            "confirm_submit_orders_button": "确认提交",
        }
        for attr_name, value in button_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                widget.setText(value)

        if hasattr(self, "recommend_stage_tabs"):
            for index, label in enumerate(["执行", "策略", "复盘"]):
                if index < self.recommend_stage_tabs.count():
                    self.recommend_stage_tabs.setTabText(index, label)
        if hasattr(self, "right_intel_tabs"):
            for index, label in enumerate(["主题摘要", "资金决策"]):
                if index < self.right_intel_tabs.count():
                    self.right_intel_tabs.setTabText(index, label)

    def _normalize_scanner_workspace_texts(self) -> None:
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：等待首轮扫描，同步观察池与监控焦点。")
        if hasattr(self, "monitor_summary_text") and not self.monitor_summary_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会在扫描结果、观察池和回测摘要之间建立焦点联动。\n"
                "选中任意一条记录后，下方会展示信号、监控状态、动作建议和回看要点。"
            )
        if hasattr(self, "scan_table"):
            self.scan_table.setHorizontalHeaderLabels(["日期", "股票", "代码", "动作", "信号", "评分", "收盘价", "成交量", "原因"])

    def _normalize_auth_workspace_texts(self) -> None:
        auth_tab = getattr(self, "auth_tab", None)
        if auth_tab is None:
            return
        for group in auth_tab.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            if not title:
                continue
            title_map = {
                "登录配置": "统一登录",
                "登录表单": "账号连接",
                "账户配置": "账号连接",
                "连接状态": "连接状态",
            }
            if title in title_map:
                group.setTitle(title_map[title])
        for label in auth_tab.findChildren(QLabel):
            text = (label.text() or "").strip()
            text_map = {
                "使用东方财富、GM 或自定义渠道保存登录参数，后续可继续扩展接入。": "在这里统一保存东方财富、GM 或自定义渠道的登录参数，后续也方便扩展更多接入方式。",
                "连接状态会在保存后自动更新。": "保存后，这里会同步显示当前连接方式、账号摘要和可用状态。",
            }
            if text in text_map:
                label.setText(text_map[text])
        for button in auth_tab.findChildren(QPushButton):
            text = (button.text() or "").strip()
            button_map = {
                "保存登录配置": "保存登录信息",
                "保存账号": "保存登录信息",
                "测试连接": "校验连接",
            }
            if text in button_map:
                button.setText(button_map[text])
        if hasattr(self, "login_status_text") and (
            not self.login_status_text.toPlainText().strip()
            or any(token in self.login_status_text.toPlainText() for token in ["缁", "鎺", "鍙", "閫", "璐", "鐧"])
        ):
            self._set_plain_text_if_changed(
                self.login_status_text,
                "登录与通道说明\n\n"
                f"- 当前通道：{self.auth_channel_combo.currentText() if hasattr(self, 'auth_channel_combo') else '东方财富'}\n"
                f"- 登录账号：{self.login_inputs.get('username').text().strip() if 'username' in getattr(self, 'login_inputs', {}) else '未填写'}\n"
                f"- 账户 ID：{self.login_inputs.get('account_id').text().strip() if 'account_id' in getattr(self, 'login_inputs', {}) else '未填写'}\n"
                f"- SDK Token：{'已填写' if 'token' in getattr(self, 'login_inputs', {}) and self.login_inputs['token'].text().strip() else '未填写'}\n\n"
                "安全边界\n"
                "- 这里只保存和展示登录参数，不绕过券商安全校验。\n"
                "- 真实下单仍由 GM SDK / 桥接脚本执行，并保留人工确认。\n"
                "- 如果后续增加新通道，可以继续在这里扩展。"
            )

    def _normalize_config_workspace_texts(self) -> None:
        config_tab = getattr(self, "config_tab", None)
        if config_tab is None:
            return
        for group in config_tab.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            title_map = {
                "策略参数": "策略参数",
                "盘前输出": "盘前输出",
                "授权与状态": "授权与状态",
                "风险设置": "风险与仓位",
            }
            if title in title_map:
                group.setTitle(title_map[title])
        for checkbox in config_tab.findChildren(QCheckBox):
            text = (checkbox.text() or "").strip()
            text_map = {
                "启用自动盘前报告": "启用自动盘前报告",
                "仅输出关注题材": "仅输出关注题材",
                "15:05 后自动导出复盘日报": "15:05 后自动导出复盘日报",
                "题材掉队时优先减仓": "题材掉队时优先减仓",
            }
            if text in text_map:
                checkbox.setText(text_map[text])
        for button in config_tab.findChildren(QPushButton):
            text = (button.text() or "").strip()
            button_map = {
                "切换试用版": "切换试用版",
                "切换专业版": "切换专业版",
                "切换企业版": "切换企业版",
                "保存策略配置": "保存当前配置",
            }
            if text in button_map:
                button.setText(button_map[text])
        if hasattr(self, "license_status_text") and (
            not self.license_status_text.toPlainText().strip()
            or any(token in self.license_status_text.toPlainText() for token in ["缁", "鎺", "鍙", "閫", "璐", "鐧"])
        ):
            capabilities = self._license_capabilities()
            plan_name = str(self.state.license_plan or "TRIAL").upper()
            plan_label = {
                "TRIAL": "试用版",
                "PRO": "专业版",
                "ENTERPRISE": "企业版",
            }.get(plan_name, plan_name)
            auto_report = "开启" if self.state.auto_daily_plan_export else "关闭"
            template_name = self.state.daily_plan_template or "balanced"
            self._set_plain_text_if_changed(
                self.license_status_text,
                "授权与状态\n\n"
                f"- 当前方案：{plan_label} ({plan_name})\n"
                f"- 版本能力：自动盘前报告 {auto_report}，盘前候选上限 {capabilities['daily_plan_export_limit']} 只\n"
                f"- 关注题材：{len(self.state.focus_themes)} 个\n"
                f"- 盘前模板：{template_name}\n"
                f"- 主线阈值：前 {self.state.strategy_top_theme_limit}，题材加权 {self.state.strategy_theme_weight}\n\n"
                "这里会显示当前方案、可用功能边界和切换后的即时状态。\n"
                "切换版本、保存配置或刷新市场后，授权卡会自动同步。"
            )

        if hasattr(self, "config_notes_text") and (
            not self.config_notes_text.toPlainText().strip()
            or any(token in self.config_notes_text.toPlainText() for token in ["缁", "鎺", "鍙", "閫", "璐", "鐧"])
        ):
            self._set_plain_text_if_changed(
                self.config_notes_text,
                "配置说明\n\n"
                "- 当前配置会直接影响每日推荐、盘前计划、盘中监控和版本能力边界。\n"
                "- 主线阈值越高，开仓越偏向龙头和前排。\n"
                "- 关注题材会影响排序、报告和提醒。\n"
                "- 自动盘前报告会在刷新后同步生成。\n"
                "- 保存配置后，登录页、推荐页和交易页都会同步刷新说明。"
            )

        group_titles = {
            "market_news_group": "消息面",
        }
        for attr_name, value in group_titles.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setTitle"):
                widget.setTitle(value)

        if hasattr(self, "strategy_detail_combo") and self.strategy_detail_combo.count() <= 7:
            labels = ["龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"]
            current = self.strategy_detail_combo.currentText()
            self.strategy_detail_combo.blockSignals(True)
            self.strategy_detail_combo.clear()
            self.strategy_detail_combo.addItems(labels)
            self.strategy_detail_combo.setCurrentText(current if current in labels else labels[0])
            self.strategy_detail_combo.blockSignals(False)

    def _normalize_scanner_workspace_texts(self) -> None:
        if hasattr(self, "scan_summary_label"):
            text = self.scan_summary_label.text().strip()
            if not text or any(token in text for token in ["鍛", "鏃", "璁", "缁", "閫", "榫", "甯"]):
                self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。")
        if hasattr(self, "last_refresh_label"):
            text = self.last_refresh_label.text().strip()
            if not text or any(token in text for token in ["鍛", "鏃", "璁", "缁", "閫", "榫", "甯"]):
                self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")
        if hasattr(self, "monitor_summary_text") and (
            not self.monitor_summary_text.toPlainText().strip()
            or any(token in self.monitor_summary_text.toPlainText() for token in ["鍛", "鏃", "璁", "缁", "閫", "榫", "甯"])
        ):
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会跟踪观察池和焦点票的最新动作、信号、催化与推荐联动。\n"
                "先执行扫描或从观察池选中一只股票，下面会自动切换到对应摘要。"
            )
        if hasattr(self, "universe_label"):
            text = self.universe_label.text().strip()
            if not text or any(token in text for token in ["鍛", "鏃", "璁", "缁", "閫", "榫", "甯"]):
                self._set_label_text_if_changed(self.universe_label, "股票池目录：未加载")

    def _prime_recommend_workspace_defaults(self) -> None:
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, RECOMMEND_DEFAULT_STATUS_TEXT)

        if hasattr(self, "recommend_empty_title"):
            self._set_label_text_if_changed(self.recommend_empty_title, RECOMMEND_DEFAULT_EMPTY_TITLE)
        if hasattr(self, "recommend_empty_meta"):
            self._set_label_text_if_changed(self.recommend_empty_meta, RECOMMEND_DEFAULT_EMPTY_META)
        if hasattr(self, "recommend_empty_sample_button"):
            self._set_label_text_if_changed(self.recommend_empty_sample_button, RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
        if hasattr(self, "recommend_empty_refresh_button"):
            self._set_label_text_if_changed(self.recommend_empty_refresh_button, RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)
        if hasattr(self, "last_refresh_label") and (not self.last_refresh_label.text().strip() or "尚未刷新" in self.last_refresh_label.text()):
            self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")

        if hasattr(self, "recommend_focus_metric_labels"):
            defaults = {
                "symbol": ("等待标的", "先同步综合机会池"),
                "theme": ("等待主线", "等待主线状态与趋势判断"),
                "action": ("待送审", "等待交易动作生成"),
                "execution": ("待观察", "等待链路阶段同步"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.recommend_focus_metric_labels:
                    self._set_label_text_if_changed(self.recommend_focus_metric_labels[key], value)
                if key in self.recommend_focus_metric_accents:
                    self._set_label_text_if_changed(self.recommend_focus_metric_accents[key], accent)

        if hasattr(self, "strategy_pack_cards"):
            empty_map = {
                "龙头模型": "等待龙头池生成后更新前排标的和位置判断。",
                "主力雷达": "等待资金画像生成后更新主力流入和承接质量。",
                "擒龙打板": "等待强势候选生成后更新打板窗口和回封观察。",
                "价值低吸": "等待回踩修复候选生成后更新低吸窗口。",
                "尾盘买入法": "等待尾盘回流候选生成后更新隔夜确认和次日开盘兑现节奏。",
                "一日持股法": "等待短线爆发候选生成后更新隔日博弈与兑现节奏。",
                "掘龙决策": "等待综合评分生成后更新最终执行候选。",
            }
            for key, card in self.strategy_pack_cards.items():
                if hasattr(card, "set_empty"):
                    card.set_empty(empty_map.get(key, "等待推荐池生成后更新。"))

        if hasattr(self, "action_flow_cards"):
            defaults = {
                "BUY": ("0", "当前无买入候选", "等待候选同步后统计可执行买点"),
                "WATCH": ("0", "当前无观察候选", "等待候选同步后更新观察名单"),
                "REDUCE": ("0", "当前无减仓建议", "等待持仓或计划生成"),
                "SELL": ("0", "当前无卖出建议", "等待风险信号或持仓数据"),
            }
            for key, card in self.action_flow_cards.items():
                if hasattr(card, "set_data"):
                    count, focus, note = defaults.get(key, ("--", "等待更新", "等待链路同步"))
                    card.set_data(count, focus, note)

        if hasattr(self, "priority_cards"):
            defaults = {
                "market": ("等待", "先确认市场温度", "行情刷新后同步情绪和周期"),
                "theme": ("等待", "先确认主线题材", "刷新后同步主线持续性"),
                "strategy": ("等待", "先确认高优先策略", "推荐池生成后自动更新"),
                "focus": ("等待", "先确认头号标的", "筛选完成后同步前排候选"),
            }
            for key, card in self.priority_cards.items():
                if hasattr(card, "set_data"):
                    count, focus, note = defaults.get(key, ("--", "等待更新", "等待链路同步"))
                    card.set_data(count, focus, note)

        if hasattr(self, "overview_priority_cards"):
            defaults = {
                "market": ("等待", "先看市场温度", "刷新后更新总览节奏"),
                "theme": ("等待", "先看主线题材", "刷新后同步前排方向"),
                "strategy": ("等待", "先看优先策略", "候选生成后自动同步"),
                "focus": ("等待", "先看焦点标的", "选股完成后更新盯盘对象"),
            }
            for key, card in self.overview_priority_cards.items():
                if hasattr(card, "set_data"):
                    count, focus, note = defaults.get(key, ("--", "等待更新", "等待链路同步"))
                    card.set_data(count, focus, note)

        if hasattr(self, "recommend_summary_cards"):
            defaults = {
                "logic": ("等待主线同步", "等待主线逻辑、位置和风险因子汇总。"),
                "plan": ("等待计划生成", "等待盘前 5 只计划和执行优先级。"),
                "pulse": ("等待温度同步", "等待市场温度、周期与仓位上限。"),
                "holding": ("等待持仓导入", "等待持仓导入后生成处理建议。"),
            }
            for key, card in self.recommend_summary_cards.items():
                if hasattr(card, "set_data"):
                    headline, detail = defaults.get(key, ("--", "等待链路同步"))
                    card.set_data(headline, detail)

        if hasattr(self, "recommend_dispatch_text"):
            self._set_plain_text_if_changed(
                self.recommend_dispatch_text,
                "盘中分发节奏\n\n"
                "1. 先确认主线是否延续，再决定今天有没有必要送审。\n"
                "2. 分发顺序优先看前排龙头、容量核心和低风险承接。\n"
                "3. 真正送往交易页的候选，应该同时满足位置、量能和风险灯。 "
            )
        if hasattr(self, "recommend_focus_review_text"):
            self._set_plain_text_if_changed(
                self.recommend_focus_review_text,
                "单票审查台\n\n"
                "这里会按焦点标的展开主线地位、买卖节奏、风险点和下一步动作。\n"
                "先选一只票，再看它值不值得进入今日 5 只计划。 "
            )
        if hasattr(self, "recommend_queue_text"):
            self._set_plain_text_if_changed(
                self.recommend_queue_text,
                "执行队列\n\n"
                "待审、已审和失败队列会在这里集中展示。\n"
                "真正进入前排的标的，应该具备更强的持续性、流动性和执行确定性。 "
            )
        if hasattr(self, "strategy_path_text"):
            self._set_plain_text_if_changed(
                self.strategy_path_text,
                "主线推演\n\n"
                "先确认市场主线，再确认龙头位次，最后决定采用打板、低吸还是观察。\n"
                "推荐池生成后，这里会把焦点票的推进路径、失效条件和下一步观察点展开。 "
            )

    def _prime_broker_workspace_defaults(self) -> None:
        if hasattr(self, "broker_metric_labels"):
            defaults = {
                "readiness": ("待评估", "等待环境诊断"),
                "capital": ("0.00", "等待资金同步"),
                "risk_reward": ("-- / --", "等待委托建议"),
                "risk_budget": ("待评估", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_metric_labels:
                    self.broker_metric_labels[key].setText(value)
                if key in self.broker_metric_accents:
                    self.broker_metric_accents[key].setText(accent)

        if hasattr(self, "broker_order_metric_labels"):
            defaults = {
                "symbol": ("--", "等待选中"),
                "gate": ("待审查", "等待主线闸门"),
                "risk": ("待评估", "等待风险灯"),
                "position": ("待计算", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_order_metric_labels:
                    self.broker_order_metric_labels[key].setText(value)
                if key in self.broker_order_metric_accents:
                    self.broker_order_metric_accents[key].setText(accent)
        if hasattr(self, "broker_order_focus_text"):
            self._set_plain_text_if_changed(
                self.broker_order_focus_text,
                "当前委托详情\n\n"
                "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
                "先在上方选中一条委托建议，再决定是否一键确认提交。 "
            )
        if hasattr(self, "order_result_text"):
            self._set_plain_text_if_changed(
                self.order_result_text,
                "执行回放\n\n"
                "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                "刷新委托或提交模拟单后，这里会自动切换到最新一条。 "
            )
        if hasattr(self, "broker_recap_text"):
            self._set_plain_text_if_changed(
                self.broker_recap_text,
                "成交回顾\n\n"
                "这里用于复盘通过率、阻塞原因、成交偏差和主线是否仍然成立。\n"
                "提交记录产生后，可回到这里快速检查执行质量。 "
            )

    def _hydrate_empty_workspace_panels(self) -> None:
        if hasattr(self, "overview_command_text") and not self.overview_command_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.overview_command_text,
                "盘前指挥摘要\n\n"
                "这里会先汇总市场主线、容量核心、焦点标的和盘前行动顺序。\n"
                "刷新市场或载入样本后，会自动切换成今天的总览指挥卡。"
            )
        if hasattr(self, "overview_execution_text") and not self.overview_execution_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.overview_execution_text,
                "执行路径\n\n"
                "这里会集中显示买点、止损、目标、失效条件和跨页面联动建议。\n"
                "推荐池与交易计划生成后，会自动补齐今天的执行节奏。"
            )
        if hasattr(self, "market_capital_text") and not self.market_capital_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_capital_text,
                "主力控盘画像\n\n"
                "刷新市场或选中股票后，这里会补上主力净流入、换手率、热度和资金承接情况。"
            )
        if hasattr(self, "market_decision_text") and not self.market_decision_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_decision_text,
                "龙头状态 / 决策建议\n\n"
                "推荐池生成后，这里会给出主策略、推荐动作、关键价位和核心逻辑。"
            )
        if hasattr(self, "market_buy_text") and not self.market_buy_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_buy_text,
                "买入窗口尚未生成。\n"
                "刷新市场后，这里会提示今天是否适合买、优先看哪种形态。"
            )
        if hasattr(self, "market_sell_text") and not self.market_sell_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_sell_text,
                "卖点与减仓提示尚未生成。\n"
                "导入持仓或生成交易计划后，这里会给出防守位和退出节奏。"
            )
        if hasattr(self, "market_breadth_text") and not self.market_breadth_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_breadth_text,
                "消息面摘要暂未生成。\n"
                "载入样本消息或刷新市场后，这里会展示最近催化、主线新闻和异动线索。"
            )
        if hasattr(self, "market_theme_brief_text") and not self.market_theme_brief_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_theme_brief_text,
                "主线题材摘要暂未生成。\n"
                "刷新后会自动汇总强势主题、数量分布和主线持续性。"
            )
        if hasattr(self, "market_leaderboard_text") and not self.market_leaderboard_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_leaderboard_text,
                "龙头榜单暂未生成。\n"
                "刷新市场后，这里会按热度、资金和位置展示前排候选。"
            )
        if hasattr(self, "market_source_status_text") and not self.market_source_status_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.market_source_status_text,
                "数据源状态尚未同步。\n"
                "程序会在刷新市场后显示缓存命中、刷新时间和异常诊断。"
            )
        if hasattr(self, "daily_pool_text") and not self.daily_pool_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.daily_pool_text,
                "今日优先候选\n\n"
                "每日推荐池生成后，这里会先给出今天最值得盯的 5 只股票，包含名称、代码、主线角色和执行原因。"
            )
        if hasattr(self, "trade_plan_text") and not self.trade_plan_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.trade_plan_text,
                "今日 5 只计划\n\n"
                "先刷新推荐池，再自动生成盘前计划。\n"
                "这里会整理买点、仓位、风控位和盘中优先级。"
            )
        if hasattr(self, "position_advice_text") and not self.position_advice_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.position_advice_text,
                "持仓处理\n\n"
                "导入持仓或同步券商账户后，这里会按主线强弱、风险灯和盈亏结构给出继续持有、减仓或离场建议。"
            )
        if hasattr(self, "board_text") and not self.board_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.board_text,
                "打板候选池\n\n"
                "这里会自动承接扫描页和推荐页的焦点标的，再筛出强势连板、回封质量更高、情绪匹配更好的打板候选。\n"
                "当你在扫描页或推荐页选中一只股票后，这里会尽量直接联动到同一只票的打板视角。"
            )
        if hasattr(self, "board_monitor_text") and not self.board_monitor_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.board_monitor_text,
                "炸板 / 回封监控\n\n"
                "这里会持续跟踪回封观察、炸板风险、连板高度和是否还值得继续博弈。\n"
                "扫描页的盘中监控和打板候选会互相联动，方便你从一个焦点直接跳到另一个焦点。"
            )
        if hasattr(self, "metrics_text") and not self.metrics_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.metrics_text,
                "绩效面板待更新。\n"
                "加载样本或执行扫描后，这里会展示收益、回撤、胜率与阶段统计。"
            )
        if hasattr(self, "broker_execution_text") and not self.broker_execution_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.broker_execution_text,
                "执行回放暂时为空。\n"
                "提交模拟委托、刷新订单建议或同步券商状态后，这里会记录执行日志。"
            )
        if hasattr(self, "detail_decision_text") and not self.detail_decision_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.detail_decision_text,
                "交易决策画像\n\n"
                "选中一只股票后，这里会汇总主线地位、动作建议、买卖区间和核心逻辑，方便快速判断这笔交易该不该做。"
            )
        if hasattr(self, "detail_execution_text") and not self.detail_execution_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.detail_execution_text,
                "执行状态回放\n\n"
                "这里会关联委托建议、提交结果和成交记录，帮助你复盘执行有没有偏离原计划。"
            )
        if hasattr(self, "detail_conclusion_text") and not self.detail_conclusion_text.toPlainText().strip():
            self._set_plain_text_if_changed(
                self.detail_conclusion_text,
                "复盘结论\n\n"
                "这里会沉淀单票的核心教训、下一步观察点，以及是否值得继续跟踪同主线标的。"
            )

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
            return WORKSPACE_LABEL_BY_KEY.get(WORKSPACE_TAB_ORDER[index], "工作区")
        return "工作区"

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
            self.top_badge.setText(f"量化猎手 Pro v2.2 · {current_name}")
        self._refresh_shell_header()
        if hasattr(self, "market_status_label") and getattr(self, "tabs", None) and self.tabs.currentWidget() is self.overview_tab:
            status_text = self.market_status_label.text()
            view_part = ""
            if " | 视图：" in status_text:
                status_text, view_part = status_text.split(" | 视图：", 1)
            page_part = f" | 页面：{current_name}"
            if view_part:
                page_part += f" | 视图：{view_part}"
            self.market_status_label.setText(f"{status_text.split(' | 页面：', 1)[0]}{page_part}")

    def _focus_widget_later(self, widget: QWidget | None) -> None:
        if widget is None:
            return
        QTimer.singleShot(0, widget.setFocus)

    def _on_workspace_tab_changed(self, index: int) -> None:
        current_name = self._workspace_name_for_index(index)
        self._refresh_shell_header()
        if hasattr(self, "market_status_label") and getattr(self, "tabs", None) and self.tabs.currentWidget() is self.overview_tab:
            status_text = self.market_status_label.text()
            view_part = ""
            if " | 视图：" in status_text:
                status_text, view_part = status_text.split(" | 视图：", 1)
            page_part = f" | 页面：{current_name}"
            if view_part:
                page_part += f" | 视图：{view_part}"
            self._set_label_text_if_changed(self.market_status_label, f"{status_text.split(' | 页面：', 1)[0]}{page_part}")
        self._refresh_workspace_status_labels()
        if hasattr(self, "top_badge"):
            self._set_label_text_if_changed(self.top_badge, self._workspace_badge_text(current_name))

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
        if hasattr(self, "overview_command_text"):
            existing = self.overview_command_text.toPlainText().strip()
            prefix = f"当前视图：{focus}"
            if existing:
                lines = existing.splitlines()
                if lines and lines[0].startswith("当前视图："):
                    lines[0] = prefix
                else:
                    lines = [prefix, ""] + lines
                self._set_plain_text_if_changed(self.overview_command_text, "\n".join(lines))
        if hasattr(self, "market_status_label"):
            status_text = self.market_status_label.text().split(" | 快捷：", 1)[0]
            self._set_label_text_if_changed(self.market_status_label, f"{status_text} | 快捷：{focus}")

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
                self._set_label_text_if_changed(self.market_status_label, f"{base_text} | 页面：{page_text} | 视图：{self.overview_focus_mode}")
            else:
                base_text = status_text.split(" | 视图：", 1)[0].strip()
                self._set_label_text_if_changed(self.market_status_label, f"{base_text} | 视图：{self.overview_focus_mode}")

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

    def set_market_history_window(self, window_label: str) -> None:
        self.market_history_window = window_label or "近1年"
        matched = False
        for button in getattr(self, "history_window_buttons", {}).values():
            checked = button.text() == self.market_history_window
            matched = matched or checked
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
        if not matched and getattr(self, "history_window_buttons", None):
            fallback = next(iter(self.history_window_buttons.values()))
            self.market_history_window = fallback.text()
            fallback.setChecked(True)
        self.market_chart_offset = 0
        if hasattr(self, "market_status_label"):
            base = self.market_status_label.text().split(" | 窗口：", 1)[0]
            self._set_label_text_if_changed(self.market_status_label, f"{base} | 窗口：{self.market_history_window}")
        if self.active_symbol and self.active_symbol in self.universe_bars:
            self._render_market_dashboard(self.active_symbol)

    def shift_market_chart_window(self, step_delta: int) -> None:
        current_symbol = self.active_symbol if self.active_symbol in self.universe_bars else ""
        if not current_symbol and getattr(self.market_screen_result, "algorithmic_pool", []):
            candidate = self.market_screen_result.algorithmic_pool[0].symbol
            current_symbol = candidate if candidate in self.universe_bars else ""
        if not current_symbol:
            return
        bars = self.universe_bars.get(current_symbol, [])
        history_sizes = {"近1月": 22, "近3月": 66, "近1年": 250, "全部": len(bars)}
        target_size = max(20, min(history_sizes.get(self.market_history_window, 250), len(bars))) if bars else 20
        step = max(10, target_size // 3)
        max_offset = max((len(bars) - target_size + step - 1) // step, 0) if bars else 0
        self.market_chart_offset = max(0, min(self.market_chart_offset + step_delta, max_offset))
        if hasattr(self, "market_status_label"):
            base = self.market_status_label.text().split(" | 视窗偏移：", 1)[0]
            suffix = "" if self.market_chart_offset == 0 else f" | 视窗偏移：{self.market_chart_offset}"
            self._set_label_text_if_changed(self.market_status_label, base + suffix)
        self._render_market_dashboard(current_symbol)

    def toggle_market_overlay(self, overlay_name: str) -> None:
        if not overlay_name:
            return
        if overlay_name in self.market_overlay_modes:
            if len(self.market_overlay_modes) > 1:
                self.market_overlay_modes.remove(overlay_name)
        else:
            self.market_overlay_modes.add(overlay_name)
        for name, button in getattr(self, "market_overlay_buttons", {}).items():
            checked = name in self.market_overlay_modes
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
            self._set_button_role(button, "tonal" if checked else "ghost")
        if self.active_symbol and self.active_symbol in self.universe_bars:
            self._render_market_dashboard(self.active_symbol)

    def set_market_secondary_indicator(self, indicator_name: str) -> None:
        self.market_secondary_indicator_mode = indicator_name or "MACD"
        for name, button in getattr(self, "secondary_indicator_buttons", {}).items():
            checked = name == self.market_secondary_indicator_mode
            button.blockSignals(True)
            button.setChecked(checked)
            button.blockSignals(False)
            self._set_button_role(button, "accent" if checked else "ghost")
        if self.active_symbol and self.active_symbol in self.universe_bars:
            self._update_indicator_chart(self.active_symbol)

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
        recommendation_map = {item.symbol: item for item in getattr(self, "daily_pool_rows", [])}
        trade_plan_signature = tuple(
            (
                "优先执行" if row_index == 0 else f"候选 {row_index + 1}",
                item.stock_name,
                item.stock_id,
                item.symbol,
                self._display_action(item.action),
                item.stock_pool or "--",
                item.opportunity_tier or "--",
                f"{item.execution_readiness:.1f}",
                f"{item.confidence:.0%}",
                f"{item.planned_entry:.2f}",
                f"{item.planned_stop:.2f}",
                f"{item.planned_target:.2f}",
                f"{item.suggested_budget:,.0f}",
                item.next_focus or "--",
                trade_plan_execution_hint(item, recommendation_map.get(item.symbol)),
                item.rationale,
            )
            for row_index, item in enumerate(plan.decisions)
        )
        if getattr(self, "_trade_plan_table_signature", None) != trade_plan_signature:
            updates_enabled = self.trade_plan_table.updatesEnabled()
            self.trade_plan_table.setUpdatesEnabled(False)
            self.trade_plan_table.blockSignals(True)
            try:
                self.trade_plan_table.setColumnCount(16)
                self.trade_plan_table.setRowCount(len(plan.decisions))
                for row_index, row_values in enumerate(trade_plan_signature):
                    for column, value in enumerate(row_values):
                        self.trade_plan_table.setItem(row_index, column, QTableWidgetItem(value))
            finally:
                self.trade_plan_table.blockSignals(False)
                self.trade_plan_table.setUpdatesEnabled(updates_enabled)
            self._trade_plan_table_signature = trade_plan_signature
        if hasattr(self, "trade_plan_focus_label"):
            if plan.decisions:
                lead = plan.decisions[0]
                self.trade_plan_focus_label.setText(
                    f"今日第一计划：{lead.stock_name} | {lead.opportunity_tier or '待确认'} | 执行准备 {lead.execution_readiness:.1f}"
                )
            else:
                self.trade_plan_focus_label.setText(TRADE_PLAN_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "trade_plan_empty_hint"):
            if plan.decisions:
                self.trade_plan_empty_hint.hide()
            else:
                reason_lines = [note for note in plan.notes if "没有" in note or "等待" in note or "观察" in note]
                hint = reason_lines[0] if reason_lines else "当前没有满足条件的新开仓计划，请先关注市场方向和现有持仓。"
                self.trade_plan_empty_hint.setText(hint)
                self.trade_plan_empty_hint.show()
        if hasattr(self, "trade_plan_empty_actions"):
            self.trade_plan_empty_actions.setVisible(not bool(plan.decisions))
        self._refresh_action_flow_cards(plan)
        self._refresh_priority_cards(plan)
        self._refresh_recommend_summary_cards(plan)
        self._refresh_workspace_status_labels()
        if hasattr(self, "trade_plan_text"):
            lines = [
                f"市场状态：{plan.market_sentiment} ({plan.sentiment_score:.1f})",
                f"交易环境：{plan.market_pulse.market_regime} | 风险等级：{plan.market_pulse.risk_level}",
                f"仓位上限：{plan.market_pulse.max_total_exposure:.0%} | 最多新开仓：{plan.max_new_positions}",
                "",
            ]
            if self.state.focus_themes:
                lines.append(f"当前关注主线：{', '.join(self.state.focus_themes)}")
                lines.append("")
            if plan.decisions:
                lead = plan.decisions[0]
                lead_row = next((row for row in self.daily_pool_rows if row.stock_id == lead.stock_id), None)
                lines.append(f"第一执行计划：{lead.stock_name} ({lead.stock_id} / {lead.symbol})")
                lines.extend(trade_decision_focus_lines(lead, lead_row))
                phase_labels = one_day_hold_phase_labels(lead, lead_row)
                if phase_labels:
                    lines.append("一日持股检查：")
                    lines.extend(f"- {label}" for label in phase_labels)
                lines.append(f"执行动作：{self._display_action(lead.action)}")
                lines.append(f"核心逻辑：{lead.rationale}")
                if len(plan.decisions) > 1:
                    backup = " / ".join(
                        f"{item.stock_name}({item.opportunity_tier or '观察'})" for item in plan.decisions[1:3]
                    )
                    if backup:
                        lines.extend(["", f"备选计划：{backup}"])
            else:
                lines.append("今日结论：暂无可执行新仓计划。")
                lines.append("优先事项：先看市场强弱，再处理已有持仓。")
            note_lines = [note for note in plan.notes if note]
            if note_lines:
                lines.extend(["", "补充提示："])
                lines.extend(f"- {note}" for note in note_lines[:4])
            self._set_plain_text_if_changed(self.trade_plan_text, "\n".join(lines))
        if hasattr(self, "market_pulse_text"):
            pulse = plan.market_pulse
            self._set_plain_text_if_changed(
                self.market_pulse_text,
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
            position_advice_signature = tuple(
                (
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    self._display_action(item.action),
                    getattr(item, "mainline_flow_signal", "") or getattr(item, "mainline_stage", "") or "--",
                    f"{item.confidence:.0%}",
                    f"{item.current_price:.2f}",
                    f"{item.cost_price:.2f}",
                    f"{item.pnl_pct:.2%}",
                    position_advice_check_item(item, recommendation_map.get(item.symbol)),
                    item.rationale,
                )
                for item in plan.position_advice
            )
            if getattr(self, "_position_advice_table_signature", None) != position_advice_signature:
                updates_enabled = self.position_advice_table.updatesEnabled()
                self.position_advice_table.setUpdatesEnabled(False)
                self.position_advice_table.blockSignals(True)
                try:
                    self.position_advice_table.setColumnCount(11)
                    self.position_advice_table.setRowCount(len(plan.position_advice))
                    for row_index, row_values in enumerate(position_advice_signature):
                        for column, value in enumerate(row_values):
                            self.position_advice_table.setItem(row_index, column, QTableWidgetItem(value))
                finally:
                    self.position_advice_table.blockSignals(False)
                    self.position_advice_table.setUpdatesEnabled(updates_enabled)
                self._position_advice_table_signature = position_advice_signature
        if hasattr(self, "position_advice_text"):
            if plan.position_advice:
                sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")
                reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
                hold_count = sum(1 for item in plan.position_advice if item.action == "HOLD")
                one_day_symbols = [
                    item.stock_name
                    for item in plan.position_advice
                    if getattr(recommendation_map.get(item.symbol), "primary_strategy", "") in {"一日持股法", "尾盘买入法"}
                ]
                lines = [
                    f"持仓建议概览：卖出 {sell_count} 只，减仓 {reduce_count} 只，继续持有 {hold_count} 只。",
                    "请结合止盈、止损与盘中异动变化继续观察，必要时优先执行减仓或卖出。",
                ]
                if one_day_symbols:
                    lines.append(
                        f"短隔夜检查：{', '.join(one_day_symbols)} 先看尾盘或次日开盘是否符合节奏，不及预期优先兑现，不做拖仓。"
                    )
                    lead_one_day = next(
                        (
                            item
                            for item in plan.position_advice
                            if getattr(recommendation_map.get(item.symbol), "primary_strategy", "") in {"一日持股法", "尾盘买入法"}
                        ),
                        None,
                    )
                    if lead_one_day is not None:
                        lines.extend(f"- {label}" for label in one_day_hold_phase_labels(lead_one_day, recommendation_map.get(lead_one_day.symbol)))
                self._set_plain_text_if_changed(
                    self.position_advice_text,
                    "\n".join(lines)
                )
            else:
                self._set_plain_text_if_changed(self.position_advice_text, "当前没有持仓数据，导入持仓 CSV 或同步券商账户后会生成建议。")

    def _populate_existing_views_from_market(self) -> None:
        if hasattr(self, "scan_table"):
            self._fill_scan_rows()
        if hasattr(self, "summary_table"):
            self._fill_backtest_summaries()
        if hasattr(self, "daily_pool_table"):
            self._populate_daily_pool_table()
        if hasattr(self, "recommend_status_label"):
            self.recommend_status_label.setText(f"已切换为程序自动筛选股票池，共 {len(self.daily_pool_rows)} 只候选。")
        if hasattr(self, "daily_pool_focus_label"):
            if self.daily_pool_rows:
                top = self.daily_pool_rows[0]
                self.daily_pool_focus_label.setText(
                    f"当前焦点：{top.stock_name} | {top.opportunity_tier or '待确认'} | 主线 {top.mainline_tag or top.theme_name or '待确认'}"
                )
            else:
                self.daily_pool_focus_label.setText(RECOMMEND_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "daily_pool_text"):
            if self.daily_pool_rows:
                top = self.daily_pool_rows[0]
                tradable_count = sum(1 for row in self.daily_pool_rows[:5] if row.action == "BUY")
                backup = " / ".join(row.stock_name for row in self.daily_pool_rows[1:4])
                lines = [
                    "今日优先候选",
                    f"第一目标：{top.stock_name} ({top.stock_id} / {top.symbol})",
                    f"可执行判断：{self._display_action(top.action)} | 总分 {top.total_score:.1f}",
                ]
                grade = one_day_hold_grade(top)
                if grade:
                    lines.append(f"隔日博弈等级：{grade}")
                lines.extend(recommendation_focus_lines(top))
                lines.append(f"触发逻辑：{top.catalyst or '量价共振 + 资金聚焦'}")
                lines.append(f"核心理由：{top.rationale}")
                lines.append(f"前五候选中可执行数量：{tradable_count}")
                if backup:
                    lines.append(f"备选关注：{backup}")
                self._set_plain_text_if_changed(self.daily_pool_text, "\n".join(lines))
            else:
                self._set_plain_text_if_changed(self.daily_pool_text, "当前没有筛出满足条件的股票，请先等待更清晰的市场信号。")
        self._refresh_trade_plan()
        self._refresh_board_mode()
        self._refresh_intraday_monitor()
        self._refresh_scanner_focus_status()
        self._refresh_recommend_focus_status()

    def _on_trade_plan_selection_changed(self) -> None:
        if not hasattr(self, "trade_plan_table") or not hasattr(self, "daily_pool_table"):
            return
        row_index = self.trade_plan_table.currentRow()
        if row_index < 0:
            return
        stock_id_item = self.trade_plan_table.item(row_index, 2)
        stock_id = stock_id_item.text() if stock_id_item else ""
        if not stock_id:
            return
        selected = self._select_daily_pool_row_by_stock_id(stock_id)
        self._refresh_recommendation_focus_panels(selected)

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
        table_rows: list[list[str]] = []
        for row_index, item in enumerate(plan.decisions):
            status = "优先执行" if row_index == 0 else f"候选 {row_index + 1}"
            values = [
                status,
                item.stock_name,
                item.stock_id,
                item.symbol,
                self._display_action(item.action),
                item.stock_pool or "--",
                item.opportunity_tier or "--",
                f"{item.execution_readiness:.1f}",
                f"{item.confidence:.0%}",
                f"{item.planned_entry:.2f}",
                f"{item.planned_stop:.2f}",
                f"{item.planned_target:.2f}",
                f"{item.suggested_budget:,.0f}",
                item.next_focus or "--",
                item.rationale,
            ]
            table_rows.append(values)
        table_signature = tuple(tuple(row) for row in table_rows)
        if getattr(self, "_trade_plan_table_signature", None) != table_signature:
            updates_enabled = self.trade_plan_table.updatesEnabled()
            self.trade_plan_table.setUpdatesEnabled(False)
            self.trade_plan_table.blockSignals(True)
            try:
                self.trade_plan_table.setRowCount(len(table_rows))
                for row_index, values in enumerate(table_rows):
                    for column, value in enumerate(values):
                        item = self.trade_plan_table.item(row_index, column)
                        if item is None:
                            self.trade_plan_table.setItem(row_index, column, QTableWidgetItem(value))
                        elif item.text() != value:
                            item.setText(value)
            finally:
                self.trade_plan_table.blockSignals(False)
                self.trade_plan_table.setUpdatesEnabled(updates_enabled)
            self._trade_plan_table_signature = table_signature
        if hasattr(self, "trade_plan_focus_label"):
            if plan.decisions:
                lead = plan.decisions[0]
                QuantHunterWindow._set_label_text_if_changed(
                    self,
                    self.trade_plan_focus_label,
                    f"今日第一计划：{lead.stock_name} | {lead.opportunity_tier or '待确认'} | 执行准备 {lead.execution_readiness:.1f}"
                )
            else:
                QuantHunterWindow._set_label_text_if_changed(self, self.trade_plan_focus_label, TRADE_PLAN_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "trade_plan_empty_hint"):
            if plan.decisions:
                self.trade_plan_empty_hint.hide()
            else:
                reason_lines = [note for note in plan.notes if "没有" in note or "等待" in note or "观察" in note]
                hint = reason_lines[0] if reason_lines else "当前没有满足条件的新开仓计划，请先关注市场方向和现有持仓。"
                QuantHunterWindow._set_label_text_if_changed(self, self.trade_plan_empty_hint, hint)
                self.trade_plan_empty_hint.show()
        if hasattr(self, "trade_plan_empty_actions"):
            self.trade_plan_empty_actions.setVisible(not bool(plan.decisions))
        self._refresh_action_flow_cards(plan)
        self._refresh_priority_cards(plan)
        self._refresh_recommend_summary_cards(plan)
        if hasattr(self, "trade_plan_text"):
            lines = [
                f"市场状态：{plan.market_sentiment} ({plan.sentiment_score:.1f})",
                f"交易环境：{plan.market_pulse.market_regime} | 风险等级：{plan.market_pulse.risk_level}",
                f"仓位上限：{plan.market_pulse.max_total_exposure:.0%} | 最多新开仓：{plan.max_new_positions}",
                "",
            ]
            if self.state.focus_themes:
                lines.append(f"当前关注主线：{', '.join(self.state.focus_themes)}")
                lines.append("")
            if plan.decisions:
                lead = plan.decisions[0]
                lead_row = next((row for row in self.daily_pool_rows if row.stock_id == lead.stock_id), None)
                lines.append(f"第一执行计划：{lead.stock_name} ({lead.stock_id} / {lead.symbol})")
                lines.extend(trade_decision_focus_lines(lead, lead_row))
                lines.append(f"执行动作：{self._display_action(lead.action)}")
                lines.append(f"核心逻辑：{lead.rationale}")
                if len(plan.decisions) > 1:
                    backup = " / ".join(
                        f"{item.stock_name}({item.opportunity_tier or '观察'})" for item in plan.decisions[1:3]
                    )
                    if backup:
                        lines.extend(["", f"备选计划：{backup}"])
            else:
                lines.append("今日结论：暂无可执行新仓计划。")
                lines.append("优先事项：先看市场强弱，再处理已有持仓。")
            note_lines = [note for note in plan.notes if note]
            if note_lines:
                lines.extend(["", "补充提示："])
                lines.extend(f"- {note}" for note in note_lines[:4])
            QuantHunterWindow._set_plain_text_if_changed(self, self.trade_plan_text, "\n".join(lines))
        if hasattr(self, "market_pulse_text"):
            pulse = plan.market_pulse
            self._set_plain_text_if_changed(
                self.market_pulse_text,
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
            updates_enabled = self.position_advice_table.updatesEnabled()
            self.position_advice_table.setUpdatesEnabled(False)
            self.position_advice_table.blockSignals(True)
            try:
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
            finally:
                self.position_advice_table.blockSignals(False)
                self.position_advice_table.setUpdatesEnabled(updates_enabled)
        if hasattr(self, "position_advice_text"):
            if plan.position_advice:
                sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")
                reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
                hold_count = sum(1 for item in plan.position_advice if item.action == "HOLD")
                self._set_plain_text_if_changed(
                    self.position_advice_text,
                    "\n".join(
                        [
                            f"持仓处理概览：卖出 {sell_count} 只，减仓 {reduce_count} 只，继续持有 {hold_count} 只。",
                            "说明：当出现诱多陷阱、跌破防守位或高位浮盈回落时，会优先给出减仓或卖出建议。",
                        ]
                    )
                )
            else:
                self._set_plain_text_if_changed(
                    self.position_advice_text,
                    "当前没有持仓数据，导入持仓 CSV 后会显示卖出和格局建议。"
                )

    def _on_market_history_date_changed(self, value: str) -> None:
        self.market_history_date = value or "最新"
        if hasattr(self, "market_status_label"):
            base = self.market_status_label.text().split(" | 历史：", 1)[0]
            suffix = "" if self.market_history_date == "最新" else f" | 历史：{self.market_history_date}"
            self._set_label_text_if_changed(self.market_status_label, base + suffix)

    def reset_market_history_view(self) -> None:
        self.market_history_date = "最新"
        if hasattr(self, "market_history_date_combo"):
            self.market_history_date_combo.blockSignals(True)
            self.market_history_date_combo.setCurrentText("最新")
            self.market_history_date_combo.blockSignals(False)
        self._on_market_history_date_changed("最新")

    def reset_market_chart_window(self) -> None:
        self.market_chart_offset = 0
        self.set_market_history_window("近1年")
        self.set_market_timeframe("日线")
        self.set_market_secondary_indicator("MACD")

    def _on_orders_selection_changed(self) -> None:
        self._refresh_broker_order_focus()

    def _on_recommend_strategy_filter_changed(self, value: str) -> None:
        self.recommend_strategy_filter = value or "全部策略"
        self._populate_filtered_daily_pool_table()

    def _on_recommend_action_filter_changed(self, value: str) -> None:
        self.recommend_action_filter = value or "全部动作"
        self._populate_filtered_daily_pool_table()

    def _on_recommend_execution_filter_changed(self, value: str) -> None:
        self.recommend_execution_filter = value or "全部状态"
        self._populate_filtered_daily_pool_table()

    def trigger_trade_plan_refresh(self) -> None:
        self._refresh_trade_plan()

    def open_trade_plan_watch_bucket(self) -> None:
        self._navigate_to_workspace("scanner", "watchlist_widget")

    def open_trade_plan_broker_workspace(self) -> None:
        self._navigate_to_workspace("broker", "orders_table")

    def focus_first_broker_blocker(self) -> None:
        self._navigate_to_workspace("broker", "broker_status_text")

    def focus_priority_broker_order(self) -> None:
        self._navigate_to_workspace("broker", "orders_table", "orders_table")

    def _selected_order_intent(self):
        if not hasattr(self, "orders_table") or not getattr(self, "order_intents", None):
            return None
        row_index = self.orders_table.currentRow()
        if row_index < 0:
            return self.order_intents[0] if self.order_intents else None
        return self.order_intents[row_index] if row_index < len(self.order_intents) else None

    def _position_mainline_brief(self, item) -> str:
        signal = str(getattr(item, "mainline_flow_signal", "") or "")
        if signal in {"延续偏强", "延续待确认", "继续跟"}:
            return "继续跟"
        if signal in {"延续观察", "只观察"}:
            return "只观察"
        if signal in {"切换预警", "切换/退潮", "防切换"}:
            return "防切换"
        stage = str(getattr(item, "mainline_stage", "") or "")
        if stage in {"加速", "启动"}:
            return "继续跟"
        if stage == "观察":
            return "只观察"
        if stage in {"分歧", "退潮"}:
            return "防切换"
        return "待确认"

    def _position_action_brief(self, item) -> str:
        action = str(getattr(item, "action", "") or "").upper()
        if action == "HOLD":
            return "等确认" if QuantHunterWindow._position_mainline_brief(self, item) == "只观察" else "继续拿"
        if action in {"SELL", "REDUCE"}:
            return "先退出"
        if action == "BUY":
            return "继续跟"
        return "待确认"

    def _normalize_overview_focus(self, focus: str) -> str:
        normalized = (focus or "").strip()
        mapping = {
            "龙头池": "主线龙头",
            "题材热度": "主线龙头",
            "资金方向": "消息催化",
            "复盘": "复盘研究",
            "趋势": "趋势机会",
        }
        return mapping.get(normalized, normalized or "市场总览")

    def _broker_focus_action_label(
        self,
        intent,
        risk_lamp: str,
        blockers: list[str] | None = None,
        warnings: list[str] | None = None,
        preview_row: dict | None = None,
        allowed: bool = True,
    ) -> str:
        blockers = blockers or []
        preview_status = str((preview_row or {}).get("status", "") or "")
        side = str(getattr(intent, "side", "") or "").upper()
        if not allowed or "超卖" in preview_status:
            return "先改数量"
        if blockers:
            return "先解阻塞"
        if side == "BUY" and risk_lamp.startswith("绿灯"):
            return "继续确认买入"
        if side in {"SELL", "REDUCE"}:
            return "确认卖出计划"
        return "继续确认"

    def _broker_focus_action_hint(
        self,
        intent,
        risk_lamp: str,
        blockers: list[str] | None = None,
        warnings: list[str] | None = None,
        preview_row: dict | None = None,
        allowed: bool = True,
    ) -> str:
        blockers = blockers or []
        preview_status = str((preview_row or {}).get("status", "") or "")
        side = str(getattr(intent, "side", "") or "").upper()
        if not allowed or "超卖" in preview_status:
            return "卖出数量超过可卖仓位，先改数量再提交。"
        if blockers:
            return blockers[0]
        if side == "BUY":
            return "优先确认前排主线、止损价格和资金占用，再提交买入。"
        if side in {"SELL", "REDUCE"}:
            return "优先核对可卖数量、止盈目标和减仓理由，再提交。"
        return "请先核对委托细节后再提交。"

    def _broker_focus_risk_summary(
        self,
        intent,
        details: dict | None = None,
        blockers: list[str] | None = None,
        warnings: list[str] | None = None,
        preview_row: dict | None = None,
        available_qty: int | None = None,
    ) -> str:
        blockers = list(blockers or [])
        warnings = list(warnings or [])
        preview_status = str((preview_row or {}).get("status", "") or "")
        side = str(getattr(intent, "side", "") or "").upper()
        quantity = int(getattr(intent, "quantity", 0) or 0)
        if side in {"SELL", "REDUCE"} and available_qty is not None and quantity > available_qty:
            return "阻塞项：卖出数量超过可卖仓位"
        if "超卖" in preview_status:
            return "阻塞项：卖出数量超过可卖仓位"
        if blockers:
            return "阻塞项：" + " / ".join(blockers[:2])
        if warnings:
            return "预警项：" + " / ".join(warnings[:2])
        return "阻塞/预警：当前未发现明显风险"

    def _refresh_broker_order_focus(self) -> None:
        if not hasattr(self, "broker_order_focus_text"):
            return
        intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
        if intent is None:
            QuantHunterWindow._set_plain_text_if_changed(
                self,
                self.broker_order_focus_text,
                "当前委托详情\n\n"
                "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
                "先在上方选中一条委托建议，再决定是否一键确认提交。 "
            )
            if hasattr(self, "orders_focus_label"):
                QuantHunterWindow._set_label_text_if_changed(self, self.orders_focus_label, ORDERS_DEFAULT_FOCUS_TEXT)
            if hasattr(self, "broker_order_metric_labels"):
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["symbol"], "--")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["symbol"], "等待选中")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["gate"], "待审查")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["gate"], "等待主线闸门")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["risk"], "待评估")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["risk"], "等待风险灯")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["position"], "待计算")
                QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["position"], "等待仓位测算")
            return

        recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == intent.symbol), None)
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []))
        warnings = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("warnings", []))
        available_qty = next((getattr(item, "available", None) for item in getattr(self, "holdings", []) if getattr(item, "symbol", "") == intent.symbol), None)
        preview_row = {}
        allowed = True
        if str(getattr(intent, "side", "") or "").upper() in {"SELL", "REDUCE"} and available_qty is not None and int(getattr(intent, "quantity", 0) or 0) > int(available_qty):
            preview_row = {"status": "超卖"}
            allowed = False
        risk_lamp = self._broker_risk_lamp_for_intent(intent, recommendation=recommendation) if hasattr(self, "_broker_risk_lamp_for_intent") else "黄灯"
        action_label = self._broker_focus_action_label(intent, risk_lamp, blockers=blockers, warnings=warnings, preview_row=preview_row, allowed=allowed)
        action_hint = self._broker_focus_action_hint(intent, risk_lamp, blockers=blockers, warnings=warnings, preview_row=preview_row, allowed=allowed)
        risk_summary = self._broker_focus_risk_summary(
            intent,
            {"checks": []},
            blockers=blockers,
            warnings=warnings,
            preview_row=preview_row,
            available_qty=available_qty,
        )
        flow_signal = str(getattr(recommendation, "mainline_flow_signal", "") or "待确认")
        stage_label = str(getattr(recommendation, "mainline_stage", "") or "待确认")
        mainline_brief = QuantHunterWindow._position_mainline_brief(self, recommendation) if recommendation is not None else "待确认"

        lines = [
            "当前委托动作面板",
            "",
            f"股票：{self._stock_name_for_symbol(intent.symbol)} ({self._stock_id_for_symbol(intent.symbol)} / {intent.symbol})",
            f"委托方向：{self._display_action(getattr(intent, 'side', ''))}",
            f"动作建议：{action_label}",
            f"主线状态：{flow_signal} / {stage_label} | {mainline_brief}",
            f"下一步：{action_hint}",
            f"阻塞/预警：{risk_summary}",
            f"可卖信息：{'可卖 ' + str(available_qty) if available_qty is not None else '暂无持仓数据'}",
        ]
        QuantHunterWindow._set_plain_text_if_changed(self, self.broker_order_focus_text, "\n".join(lines))
        if hasattr(self, "orders_focus_label"):
            QuantHunterWindow._set_label_text_if_changed(self, self.orders_focus_label, f"委托动作面板 / 委托焦点：动作建议 {action_label} | 主线 {flow_signal}")
        if hasattr(self, "broker_order_metric_labels"):
            side_text = self._display_action(getattr(intent, "side", ""))
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["symbol"], self._stock_name_for_symbol(intent.symbol))
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["symbol"], f"{self._stock_id_for_symbol(intent.symbol)} / {intent.symbol}")
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["gate"], mainline_brief)
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["gate"], f"{flow_signal} / {stage_label}")
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["risk"], risk_lamp)
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_accents["risk"], action_hint)
            quantity = int(getattr(intent, "quantity", 0) or 0)
            QuantHunterWindow._set_label_text_if_changed(self, self.broker_order_metric_labels["position"], f"{side_text} {quantity}")
            QuantHunterWindow._set_label_text_if_changed(
                self,
                self.broker_order_metric_accents["position"],
                f"可卖 {available_qty}" if available_qty is not None else "等待持仓同步"
            )

    def _selected_daily_pool_recommendation(self):
        if not hasattr(self, "daily_pool_table"):
            return None
        row_index = self.daily_pool_table.currentRow()
        if row_index < 0:
            return self.daily_pool_rows[0] if self.daily_pool_rows else None
        filtered = self._filtered_daily_pool_rows()
        return filtered[row_index] if row_index < len(filtered) else (self.daily_pool_rows[0] if self.daily_pool_rows else None)

    def _selected_trade_plan_decision(self):
        if not hasattr(self, "trade_plan_table") or not getattr(self, "current_trade_plan", None):
            return None
        row_index = self.trade_plan_table.currentRow()
        if row_index < 0:
            return self.current_trade_plan.decisions[0] if self.current_trade_plan.decisions else None
        return self.current_trade_plan.decisions[row_index] if row_index < len(self.current_trade_plan.decisions) else None

    def _queue_symbol_to_watchlist(self, symbol: str) -> None:
        if symbol and symbol not in self.state.watchlist:
            self.state.watchlist.append(symbol)
            self.state.watchlist.sort()
            self._refresh_watchlist()
            self.save_state()

    def push_selected_recommendation_to_broker(self) -> None:
        item = self._selected_daily_pool_recommendation()
        if item is None:
            return
        self._queue_symbol_to_watchlist(item.symbol)
        self.generate_order_suggestions()
        self._navigate_to_workspace("broker", "orders_table")

    def push_selected_trade_plan_to_broker(self) -> None:
        item = self._selected_trade_plan_decision()
        if item is None:
            return
        self._queue_symbol_to_watchlist(item.symbol)
        self.generate_order_suggestions()
        self._navigate_to_workspace("broker", "orders_table")

    def push_priority_recommendation_to_broker(self) -> None:
        if not self.daily_pool_rows:
            return
        self._queue_symbol_to_watchlist(self.daily_pool_rows[0].symbol)
        self.generate_order_suggestions()
        self._navigate_to_workspace("broker", "orders_table")

    def review_failed_recommendation(self) -> None:
        self._navigate_to_workspace("broker", "execution_table")

    def show_core_execution_bucket(self) -> None:
        self._navigate_to_workspace("recommend", "trade_plan_table")

    def show_watch_bucket(self) -> None:
        self._navigate_to_workspace("scanner", "watchlist_widget")

    def show_risk_bucket(self) -> None:
        self._navigate_to_workspace("recommend", "position_advice_table")

    def focus_next_pending_recommendation(self) -> None:
        self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")

    def _stabilize_workspace_layouts(self) -> None:
        workspace_scroll_specs = [
            ("scanner_tab", "scanner_workspace_scroll_area"),
            ("board_tab", "board_workspace_scroll_area"),
            ("config_tab", "config_workspace_scroll_area"),
            ("detail_tab", "detail_workspace_scroll_area"),
        ]
        for tab_name, scroll_attr in workspace_scroll_specs:
            tab = getattr(self, tab_name, None)
            if isinstance(tab, QWidget):
                self._wrap_workspace_in_scroll_area(tab, scroll_attr)
        self._rebalance_workspace_panels()

    def _wrap_workspace_in_scroll_area(self, tab: QWidget, scroll_attr: str) -> None:
        if getattr(self, scroll_attr, None) is not None:
            return
        old_layout = tab.layout()
        if old_layout is None:
            return

        content = QWidget()
        content.setObjectName(f"{tab.objectName() or 'workspace'}Content")
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        content.setLayout(old_layout)

        scroll_area = QScrollArea(tab)
        scroll_area.setObjectName(f"{tab.objectName() or 'workspace'}ScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setWidget(content)
        scroll_area.setAlignment(Qt.AlignTop)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        wrapper_layout = QVBoxLayout()
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(scroll_area)
        tab.setLayout(wrapper_layout)

        setattr(self, scroll_attr, scroll_area)
        setattr(self, f"{scroll_attr}_content", content)

        self._enable_smooth_scroll(scroll_area, allow_drag=True)
        QScroller.grabGesture(content, QScroller.LeftMouseButtonGesture)

    def _rebalance_workspace_panels(self) -> None:
        workspace_tabs = [
            getattr(self, "scanner_tab", None),
            getattr(self, "board_tab", None),
            getattr(self, "config_tab", None),
            getattr(self, "detail_tab", None),
        ]
        for tab in workspace_tabs:
            if not isinstance(tab, QWidget):
                continue
            for group in tab.findChildren(QGroupBox):
                group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            for text_edit in tab.findChildren(QTextEdit):
                text_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                text_edit.setMinimumHeight(max(text_edit.minimumHeight(), 132))
            for line_edit in tab.findChildren(QLineEdit):
                line_edit.setMinimumHeight(max(line_edit.minimumHeight(), 36))
            for combo_box in tab.findChildren(QComboBox):
                combo_box.setMinimumHeight(max(combo_box.minimumHeight(), 36))
            for table in tab.findChildren(QTableWidget):
                table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                table.setMinimumHeight(max(table.minimumHeight(), 220))
                table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 42))
                table.horizontalHeader().setFixedHeight(max(table.horizontalHeader().height(), 46))
            for list_widget in tab.findChildren(QListWidget):
                list_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                list_widget.setMinimumHeight(max(list_widget.minimumHeight(), 220))

        preferred_table_heights = {
            "scan_table": 260,
            "summary_table": 240,
            "monitor_table": 240,
            "board_table": 240,
            "board_monitor_table": 220,
            "signal_table": 240,
            "trades_table": 240,
        }
        for attr_name, min_height in preferred_table_heights.items():
            table = getattr(self, attr_name, None)
            if isinstance(table, QTableWidget):
                table.setMinimumHeight(max(table.minimumHeight(), min_height))

        preferred_text_heights = {
            "monitor_summary_text": 140,
            "board_text": 130,
            "board_monitor_text": 130,
            "license_status_text": 220,
            "config_notes_text": 180,
            "metrics_text": 180,
            "detail_decision_text": 210,
            "detail_execution_text": 210,
            "detail_conclusion_text": 210,
        }
        for attr_name, min_height in preferred_text_heights.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(max(widget.minimumHeight(), min_height))
                widget.setMaximumHeight(16777215)

        if hasattr(self, "watchlist_widget"):
            self.watchlist_widget.setMinimumHeight(max(self.watchlist_widget.minimumHeight(), 240))

        scanner_tab = getattr(self, "scanner_tab", None)
        if isinstance(scanner_tab, QWidget):
            scanner_splitters = [splitter for splitter in scanner_tab.findChildren(QSplitter) if splitter.count() == 3]
            for splitter in scanner_splitters:
                splitter.setStretchFactor(0, 3)
                splitter.setStretchFactor(1, 4)
                splitter.setStretchFactor(2, 4)

        config_tab = getattr(self, "config_tab", None)
        if isinstance(config_tab, QWidget):
            config_splitters = [splitter for splitter in config_tab.findChildren(QSplitter) if splitter.count() == 2]
            for splitter in config_splitters:
                splitter.setStretchFactor(0, 5)
                splitter.setStretchFactor(1, 5)

        detail_tab = getattr(self, "detail_tab", None)
        if isinstance(detail_tab, QWidget):
            detail_splitters = [splitter for splitter in detail_tab.findChildren(QSplitter)]
            for splitter in detail_splitters:
                if splitter.count() == 3:
                    splitter.setStretchFactor(0, 4)
                    splitter.setStretchFactor(1, 4)
                    splitter.setStretchFactor(2, 4)
                elif splitter.count() == 2:
                    splitter.setStretchFactor(0, 5)
                    splitter.setStretchFactor(1, 6)

    def _polish_workspace_density(self) -> None:
        if hasattr(self, "shell_header"):
            self.shell_header.setMaximumHeight(112)
            self.shell_header.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if hasattr(self, "shell_pulse_bar"):
            self.shell_pulse_bar.setMaximumHeight(62)
            self.shell_pulse_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for hero in self.findChildren(QFrame, "workspaceHero"):
            hero.setMaximumHeight(108)
            hero.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        for badge in self.findChildren(QFrame, "workspaceBadge"):
            badge.setMaximumHeight(54)
            badge.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        for action_row in self.findChildren(QFrame, "scannerTopActionRow"):
            action_row.setMaximumHeight(58)
        for tab in [
            getattr(self, "scanner_tab", None),
            getattr(self, "board_tab", None),
            getattr(self, "config_tab", None),
            getattr(self, "detail_tab", None),
        ]:
            if not isinstance(tab, QWidget):
                continue
            layout = tab.layout()
            if layout is not None:
                layout.setContentsMargins(0, 0, 0, 0)
                layout.setSpacing(8)

        for label_name in [
            "universe_label",
            "scan_summary_label",
            "last_refresh_label",
            "active_symbol_label",
            "shell_pulse_label",
            "shell_pulse_hint",
            "shell_pulse_meta",
        ]:
            label = getattr(self, label_name, None)
            if isinstance(label, QLabel):
                label.setWordWrap(True)

        compact_text_heights = {
            "metrics_text": 168,
            "board_text": 118,
            "board_monitor_text": 118,
            "config_notes_text": 150,
            "license_status_text": 190,
            "monitor_summary_text": 124,
        }
        for attr_name, height in compact_text_heights.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(height)

        if hasattr(self, "scan_table"):
            self.scan_table.setMinimumHeight(300)
        if hasattr(self, "board_table"):
            self.board_table.setMinimumHeight(260)
        if hasattr(self, "board_monitor_table"):
            self.board_monitor_table.setMinimumHeight(220)
        if hasattr(self, "signal_table"):
            self.signal_table.setMinimumHeight(220)
        if hasattr(self, "trades_table"):
            self.trades_table.setMinimumHeight(220)

    def _inject_live_workspace_summary_panels(self) -> None:
        scanner_panel = getattr(self, "scanner_tab", None)
        if isinstance(scanner_panel, QWidget):
            tool_panel = scanner_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "scanner_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("scannerLiveSummaryPanel", "扫描态势")
                    grid.addWidget(panel, 1, 1)
                    self.scanner_live_summary_headline = headline
                    self.scanner_live_summary_detail = detail
                    self.scanner_live_summary_meta = meta

        board_panel = getattr(self, "board_tab", None)
        if isinstance(board_panel, QWidget):
            tool_panel = board_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "board_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("boardLiveSummaryPanel", "打板态势")
                    grid.addWidget(panel, 1, 1)
                    self.board_live_summary_headline = headline
                    self.board_live_summary_detail = detail
                    self.board_live_summary_meta = meta

        detail_panel = getattr(self, "detail_tab", None)
        if isinstance(detail_panel, QWidget):
            tool_panel = detail_panel.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is not None and getattr(self, "detail_live_summary_headline", None) is None:
                grid = tool_panel.layout()
                if isinstance(grid, QGridLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("detailLiveSummaryPanel", "复盘态势")
                    grid.addWidget(panel, 1, 1)
                    self.detail_live_summary_headline = headline
                    self.detail_live_summary_detail = detail
                    self.detail_live_summary_meta = meta

        config_panel = getattr(self, "config_tab", None)
        if isinstance(config_panel, QWidget):
            tool_panel = config_panel.findChild(QGroupBox, "configToolPanel")
            if tool_panel is not None and getattr(self, "config_live_summary_headline", None) is None:
                layout = tool_panel.layout()
                if isinstance(layout, QHBoxLayout):
                    panel, headline, detail, meta = self._build_workspace_summary_panel("configLiveSummaryPanel", "配置总览")
                    layout.addWidget(panel, 2)
                    self.config_live_summary_headline = headline
                    self.config_live_summary_detail = detail
                    self.config_live_summary_meta = meta

    def _inject_workspace_focus_banners(self) -> None:
        banner_specs = [
            ("overview_tab", "market_pool_table", "overview_focus_banner"),
            ("recommend_tab", "daily_pool_table", "recommend_focus_banner"),
            ("scanner_tab", "scan_table", "scanner_focus_banner"),
            ("board_tab", "board_table", "board_focus_banner"),
            ("detail_tab", "metrics_text", "detail_focus_banner"),
        ]
        for tab_name, anchor_name, banner_name in banner_specs:
            tab = getattr(self, tab_name, None)
            anchor = getattr(self, anchor_name, None)
            if not isinstance(tab, QWidget) or anchor is None or getattr(self, banner_name, None) is not None:
                continue
            parent = anchor.parentWidget()
            if parent is None:
                continue
            layout = parent.layout()
            if layout is None:
                continue
            banner = QLabel("焦点标的：等待联动")
            banner.setObjectName("workspaceFocusBanner")
            banner.setWordWrap(True)
            layout.insertWidget(0, banner)
            setattr(self, banner_name, banner)

    def _apply_identity_table_headers(self) -> None:
        if hasattr(self, "scan_table"):
            self.scan_table.setColumnCount(11)
            self.scan_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"])
            self.scan_table.setColumnHidden(1, True)
        if hasattr(self, "summary_table"):
            self.summary_table.setColumnCount(8)
            self.summary_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "交易笔数", "收益率", "最大回撤", "胜率", "期末权益"])
            self.summary_table.setColumnHidden(1, True)
        if hasattr(self, "monitor_table"):
            self.monitor_table.setColumnCount(9)
            self.monitor_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "收盘价", "信号日期", "更新时间"])
            self.monitor_table.setColumnHidden(1, True)
        if hasattr(self, "board_table"):
            self.board_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "打板级别", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"])
            self.board_table.setColumnHidden(1, True)
        if hasattr(self, "board_monitor_table"):
            self.board_monitor_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "监控状态", "强度", "连续性", "回封概率", "炸板风险", "动作建议", "备注"])
            self.board_monitor_table.setColumnHidden(1, True)
        if hasattr(self, "leader_table"):
            self.leader_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "题材", "级别", "角色", "窗口", "风险", "龙头分", "动作", "说明"])
            self.leader_table.setColumnHidden(1, True)
        if hasattr(self, "daily_pool_table"):
            self.daily_pool_table.setColumnCount(len(DAILY_POOL_TABLE_HEADERS))
            self.daily_pool_table.setHorizontalHeaderLabels(DAILY_POOL_TABLE_HEADERS)
            self.daily_pool_table.setColumnHidden(2, True)
        if hasattr(self, "market_pool_table"):
            self.market_pool_table.setHorizontalHeaderLabels(["序", "股票标识", "资金标签", "策略标签", "涨跌幅", "最新价"])

    def _refresh_live_workspace_summary_panels(self) -> None:
        if hasattr(self, "scanner_live_summary_headline"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            monitor_count = self.monitor_table.rowCount() if hasattr(self, "monitor_table") else 0
            auto_refresh = "开启" if hasattr(self, "auto_refresh_checkbox") and self.auto_refresh_checkbox.isChecked() else "关闭"
            self._set_label_text_if_changed(self.scanner_live_summary_headline, f"扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}")
            self._set_label_text_if_changed(self.scanner_live_summary_detail, f"盘中自动刷新：{auto_refresh} | 最近刷新：{getattr(self, 'last_refresh_label', QLabel('--')).text()}")
            self._set_label_text_if_changed(self.scanner_live_summary_meta, f"当前股票池：{getattr(self, 'universe_label', QLabel('--')).text()}")

        if hasattr(self, "board_live_summary_headline"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            auto_export = "开启" if hasattr(self, "auto_review_export_checkbox") and self.auto_review_export_checkbox.isChecked() else "关闭"
            self._set_label_text_if_changed(self.board_live_summary_headline, f"候选 {candidate_count} / 监控 {monitor_count}")
            self._set_label_text_if_changed(self.board_live_summary_detail, f"收盘导出：{auto_export} | 焦点联动：扫描 / 推荐 / 复盘")
            self._set_label_text_if_changed(self.board_live_summary_meta, getattr(self, "board_focus_label", QLabel("等待焦点同步")).text() if hasattr(self, "board_focus_label") else "等待焦点同步")

        if hasattr(self, "detail_live_summary_headline"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            active_symbol = getattr(self, "active_symbol", "") or "未选中"
            self._set_label_text_if_changed(self.detail_live_summary_headline, f"当前标的：{active_symbol}")
            self._set_label_text_if_changed(self.detail_live_summary_detail, f"近期信号 {signal_count} 条 | 交易记录 {trade_count} 条")
            self._set_label_text_if_changed(self.detail_live_summary_meta, getattr(self, "active_symbol_label", QLabel("当前标的：未选择")).text())

        if hasattr(self, "config_live_summary_headline"):
            plan_text = self.state.license_plan or "TRIAL"
            top_theme_limit, max_total_exposure, _ = self._current_strategy_runtime_config()
            self._set_label_text_if_changed(self.config_live_summary_headline, f"方案：{plan_text} | 主线前排 {top_theme_limit}")
            self._set_label_text_if_changed(self.config_live_summary_detail, f"总仓位上限：{max_total_exposure:.2f} | 模板：{self.daily_plan_template_combo.currentText() if hasattr(self, 'daily_plan_template_combo') else '--'}")
            focus_theme_text = self.focus_themes_input.text().strip() if hasattr(self, "focus_themes_input") else ""
            self._set_label_text_if_changed(self.config_live_summary_meta, f"关注题材：{focus_theme_text or '未设置'}")

    def _refresh_workspace_focus_banners(self) -> None:
        target_symbol = self.active_symbol or self._selected_symbol_from_watchlist() or self._selected_board_symbol() or ""
        stock_name = self._stock_name_for_symbol(target_symbol) if target_symbol else "等待联动"
        stock_id = self._stock_id_for_symbol(target_symbol) if target_symbol else "--"
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        tone = self._focus_banner_tone(symbol=target_symbol, recommendation=recommendation, scan_row=scan_row)
        if hasattr(self, "overview_focus_banner"):
            market_count = self.market_pool_table.rowCount() if hasattr(self, "market_pool_table") else 0
            text = f"总览焦点：{stock_name} ({stock_id} / {target_symbol}) | 龙头池 {market_count} | 与推荐页联动" if target_symbol else "总览焦点：等待从龙头池、推荐池或扫描页联动一只股票"
            self._set_focus_banner_state(self.overview_focus_banner, tone if target_symbol else 'idle', text)
        if hasattr(self, "recommend_focus_banner"):
            pool_count = self.daily_pool_table.rowCount() if hasattr(self, "daily_pool_table") else 0
            strategy_name = getattr(recommendation, "primary_strategy", "") if recommendation is not None else ""
            text = f"推荐焦点：{stock_name} ({stock_id} / {target_symbol}) | 推荐池 {pool_count} | 策略 {strategy_name or '等待策略同步'}" if target_symbol else "推荐焦点：等待从推荐池、龙头榜或交易计划联动一只股票"
            self._set_focus_banner_state(self.recommend_focus_banner, tone if target_symbol else 'idle', text)
        if hasattr(self, "scanner_focus_banner"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            text = f"扫描焦点：{stock_name} ({stock_id} / {target_symbol}) | 扫描 {scan_count} | 观察 {watch_count}" if target_symbol else "扫描焦点：等待从扫描榜、观察池或盘中监控联动标的"
            self._set_focus_banner_state(self.scanner_focus_banner, tone if target_symbol else 'idle', text)
        if hasattr(self, "board_focus_banner"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            text = f"打板焦点：{stock_name} ({stock_id} / {target_symbol}) | 候选 {candidate_count} | 监控 {monitor_count}" if target_symbol else "打板焦点：等待扫描页或推荐页同步强势候选"
            self._set_focus_banner_state(self.board_focus_banner, tone if target_symbol else 'idle', text)
        if hasattr(self, "detail_focus_banner"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            text = f"复盘焦点：{stock_name} ({stock_id} / {target_symbol}) | 信号 {signal_count} | 成交 {trade_count}" if target_symbol else "复盘焦点：等待扫描、推荐或打板页面同步单票标的"
            self._set_focus_banner_state(self.detail_focus_banner, tone if target_symbol else 'idle', text)

    def _focus_banner_tone(self, symbol: str = "", recommendation=None, scan_row=None) -> str:
        if not symbol:
            return "idle"
        action = str(getattr(recommendation, "action", "") or getattr(scan_row, "action", "") or "").upper()
        risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "")
        if action in {"SELL", "REDUCE"} or any(token in risk_flag for token in ["红", "高", "风险"]):
            return "risk"
        if action == "BUY":
            return "buy"
        if action == "WATCH" or action:
            return "watch"
        return "idle"

    def _refresh_overview_focus_cards(self, symbol: str, snapshot, recommendation) -> None:
        if not hasattr(self, "overview_summary_cards"):
            return
        if recommendation is not None:
            theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
            role_name = self._display_mainline_role(getattr(recommendation, "mainline_role", "") or "")
            strategy_name = getattr(recommendation, "primary_strategy", "") or "掘龙决策"
            action_label = self._display_action(getattr(recommendation, "action", "WATCH"))
            catalyst = getattr(recommendation, "catalyst", "") or "等待消息与量价共振"
            decision_score = float(getattr(recommendation, "dragon_decision_score", getattr(recommendation, "total_score", 0.0)) or 0.0)
            self.overview_summary_cards["theme"].set_data(theme_name, f"{recommendation.stock_name} | {role_name} | 位次 {getattr(recommendation, 'mainline_rank', getattr(recommendation, 'theme_rank', '--'))}")
            self.overview_summary_cards["source"].set_data(strategy_name, f"{action_label} | 催化 {catalyst}")
            self.overview_summary_cards["capital"].set_data(f"{float(getattr(recommendation, 'mainline_window_score', 0.0) or 0.0):.1f}", f"总分 {float(getattr(recommendation, 'total_score', 0.0) or 0.0):.1f} | 风险 {getattr(recommendation, 'mainline_risk_flag', '') or '待评估'}")
            self.overview_summary_cards["decision"].set_data(action_label, f"决策分 {decision_score:.1f} | 执行准备 {float(getattr(recommendation, 'execution_readiness', 0.0) or 0.0):.1f}")
            return
        if snapshot is not None:
            self.overview_summary_cards["theme"].set_data(snapshot.strategy_tag or "待确认", f"{snapshot.stock_name} | 热度 {snapshot.heat_score:.1f} | 动能 {snapshot.momentum_bias:.1f}")
            self.overview_summary_cards["source"].set_data(snapshot.fund_model or "待确认", f"{snapshot.stock_id} | 涨跌 {snapshot.pct_change:.2f}% | 换手 {snapshot.turnover:.2f}%")
            self.overview_summary_cards["capital"].set_data(f"{snapshot.main_inflow / 1e8:.2f} 亿", f"热度 {snapshot.heat_score:.1f} | 动能 {snapshot.momentum_bias:.1f} | 换手 {snapshot.turnover:.2f}%")
            self.overview_summary_cards["decision"].set_data("观察", f"{snapshot.strategy_tag} | 涨跌 {snapshot.pct_change:.2f}% | 先看量价承接")
            return
        stock_name = self._stock_name_for_symbol(symbol) if symbol else "等待行情接入"
        self.overview_summary_cards["theme"].set_data("等待行情接入", f"{stock_name} | 等待主线题材、龙头位次与前排数量刷新。")
        self.overview_summary_cards["source"].set_data("等待行情接入", "等待远程行情、缓存或示例数据接入。")

    def _refresh_recommend_story_panels(self, row: RecommendationRow | None = None) -> None:
        current = row or self._selected_daily_pool_recommendation()
        if current is None:
            if hasattr(self, "daily_pool_text") and not self.daily_pool_text.toPlainText().strip():
                self._set_plain_text_if_changed(self.daily_pool_text, "每日推荐池将在刷新后生成，默认最多展示 5 只可执行候选。")
            if hasattr(self, "strategy_path_text") and not self.strategy_path_text.toPlainText().strip():
                self._set_plain_text_if_changed(self.strategy_path_text, "等待生成推荐池后更新主线推演路径。")
            self._refresh_recommend_bucket_panels(None)
            return

        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        role_name = getattr(current, "mainline_role", "") or ""
        flow_signal = getattr(current, "mainline_flow_signal", "") or "待确认"
        stage_name = getattr(current, "mainline_stage", "") or "待确认"
        readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
        confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
        stock_pool = getattr(current, "stock_pool", "") or "程序自动筛选池"
        catalyst = getattr(current, "catalyst", "") or "量价共振 + 资金回流"
        next_focus = getattr(current, "next_focus", "") or "继续盯主线强度、量能承接和回流节奏。"
        invalidation = getattr(current, "invalidation_reason", "") or "跌破防守位或主线切换时重新评估。"

        if hasattr(self, "daily_pool_text"):
            lines = [
                "今日优先候选",
                f"焦点标的：{current.stock_name} ({current.stock_id} / {current.symbol})",
                f"主线：{theme_name} | 阶段：{stage_name} | 角色：{self._display_mainline_role(role_name)}",
                f"动作：{self._display_action(getattr(current, 'action', 'WATCH'))} | 总分 {current.total_score:.1f}",
                f"执行准备：{readiness:.1f} | 置信：{confidence:.1f} | 股票池：{stock_pool}",
                f"催化：{catalyst}",
                f"逻辑：{getattr(current, 'rationale', '') or '等待更清晰的主线与量价确认。'}",
            ]
            self._set_plain_text_if_changed(self.daily_pool_text, "\n".join(lines))

        if hasattr(self, "strategy_path_text"):
            lines = [
                f"主线推演：{current.stock_name}",
                f"第一步：主线 {theme_name} 当前处于 {stage_name}，信号为 {flow_signal}。",
                f"第二步：当前角色是 {self._display_mainline_role(role_name)}，先看是否继续维持前排强度。",
                f"第三步：若执行准备 {readiness:.1f} 持续抬升，可考虑按 {getattr(current, 'primary_strategy', '') or '掘龙决策'} 计划推进。",
                f"第四步：重点观察 {next_focus}",
                f"失效条件：{invalidation}",
            ]
            self._set_plain_text_if_changed(self.strategy_path_text, "\n".join(lines))
        self._refresh_recommend_bucket_panels(current)

    def _on_daily_pool_selection_changed(self) -> None:
        current = self._selected_daily_pool_recommendation()
        if current is not None and getattr(current, "symbol", "") in self.universe_bars:
            self.select_symbol(current.symbol, origin="recommend")
        self._refresh_recommendation_focus_panels()
        self._refresh_strategy_focus_detail()

    def select_symbol(self, symbol: str, origin: str = "") -> None:
        if symbol not in self.universe_bars:
            return
        current_revision = int(getattr(self, "_symbol_data_revision", 0) or 0)
        if (
            symbol == getattr(self, "active_symbol", "")
            and symbol == getattr(self, "_last_rendered_symbol", "")
            and current_revision == int(getattr(self, "_last_rendered_symbol_revision", -1) or -1)
        ):
            self._sync_symbol_across_workspaces(symbol, origin=origin)
            return
        self.active_symbol = symbol
        self.bars = self.universe_bars[symbol]
        self.analyses = self.universe_analyses[symbol]
        if hasattr(self, "active_symbol_label"):
            self._set_label_text_if_changed(self.active_symbol_label, f"当前标的：{symbol}")
        self.state.selected_symbol = symbol
        self._refresh_signal_panel()
        self.run_backtest_for_active(quiet=True)
        if self._should_render_market_dashboard_now():
            self._pending_market_dashboard_symbol = ""
            self._render_market_dashboard(symbol)
        else:
            self._pending_market_dashboard_symbol = symbol
        self._refresh_detail_workspace_panels()
        self._sync_symbol_across_workspaces(symbol, origin=origin)
        self._last_rendered_symbol = symbol
        self._last_rendered_symbol_revision = current_revision
        self._refresh_workspace_focus_banners()
        self._refresh_live_workspace_summary_panels()
        self.save_state()

    def _should_render_market_dashboard_now(self) -> bool:
        if not hasattr(self, "tabs") or not hasattr(self, "overview_tab"):
            return True
        return self.tabs.currentWidget() is self.overview_tab

    def _flush_pending_market_dashboard_render(self) -> None:
        symbol = str(getattr(self, "_pending_market_dashboard_symbol", "") or "")
        if not symbol or symbol not in getattr(self, "universe_bars", {}):
            return
        self._pending_market_dashboard_symbol = ""
        self._render_market_dashboard(symbol)

    def _render_market_dashboard(self, symbol: str) -> None:
        snapshot = self.market_snapshots.get(symbol)
        recommendation = next((item for item in self.daily_pool_rows if item.symbol == symbol), None)
        chart_series = getattr(self.market_screen_result, "chart_series_by_symbol", {}).get(symbol)
        if hasattr(self, "market_header_label"):
            title = symbol if snapshot is None else f"{snapshot.stock_name}  {snapshot.stock_id}  {symbol}"
            self._set_label_text_if_changed(self.market_header_label, title)
        if hasattr(self, "market_subheader_label"):
            sub = "程序自动筛选出的龙头候选"
            if snapshot is not None:
                sub = f"{snapshot.strategy_tag} | {snapshot.fund_model} | 涨跌幅 {snapshot.pct_change:.2f}% | 换手 {snapshot.turnover:.1f}% | 主力净流入 {snapshot.main_inflow / 1e8:.2f} 亿"
            self._set_label_text_if_changed(self.market_subheader_label, sub)
        if hasattr(self, "market_signal_label") and snapshot is not None:
            self._set_label_text_if_changed(self.market_signal_label, f"{snapshot.fund_model}   |   {snapshot.strategy_tag}   |   热度 {snapshot.heat_score:.1f}   |   动能 {snapshot.momentum_bias:.1f}")
        if hasattr(self, "market_quote_label"):
            if snapshot is not None:
                self._set_label_text_if_changed(self.market_quote_label, f"开 {snapshot.open_price:.2f} / 高 {snapshot.high_price:.2f} / 低 {snapshot.low_price:.2f} / 收 {snapshot.latest_price:.2f} | 涨跌 {snapshot.pct_change:.2f}% | 换手 {snapshot.turnover:.2f}% | 历史窗口 {self.market_history_window}")
            else:
                self._set_label_text_if_changed(self.market_quote_label, f"历史窗口 {self.market_history_window} | 周期 {self.market_timeframe_mode} | 叠加 {'/'.join(sorted(self.market_overlay_modes)) or '关闭'}")
        self._update_intraday_chart(symbol, snapshot, chart_series)
        self._update_daily_chart(symbol)
        self._update_fund_chart(symbol, chart_series)
        self._update_momentum_chart(symbol, chart_series)
        self._update_indicator_chart(symbol)
        self._update_market_text_panels(symbol, snapshot, recommendation)
        self._refresh_overview_focus_cards(symbol, snapshot, recommendation)

    def _normalize_recommend_workspace_texts(self) -> None:
        title_map = {
            "recommend_dispatch_text": "\u6267\u884c\u5206\u53d1",
            "recommend_focus_review_text": "\u5355\u7968\u5ba1\u67e5",
            "recommend_queue_text": "\u961f\u5217\u6982\u89c8",
            "strategy_detail_text": "\u6218\u6cd5\u660e\u7ec6",
            "strategy_path_text": "\u4e3b\u7ebf\u63a8\u6f14",
            "daily_pool_text": "\u4eca\u65e5\u4f18\u5148\u5019\u9009",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        if hasattr(self, "recommend_stage_tabs"):
            for index, label in enumerate(["\u6267\u884c", "\u7b56\u7565", "\u590d\u76d8"]):
                if index < self.recommend_stage_tabs.count():
                    self.recommend_stage_tabs.setTabText(index, label)

        button_map = {
            "show_core_execution_bucket": "\u53ea\u770b\u4e3b\u7ebf\u524d\u6392",
            "show_watch_bucket": "\u53ea\u770b\u89c2\u5bdf\u6c60",
            "show_risk_bucket": "\u53ea\u770b\u98ce\u9669\u6c60",
        }
        legacy_aliases = {
            "\u53ea\u770b\u4e3b\u7ebf\u524d\u6392": "show_core_execution_bucket",
            "\u53ea\u770b\u89c2\u5bdf\u6c60": "show_watch_bucket",
            "\u53ea\u770b\u98ce\u9669\u6c60": "show_risk_bucket",
            "\u53ea\u770b\u56de\u907f\u6c60": "show_risk_bucket",
        }
        for button in self.findChildren(QPushButton):
            text = button.text().strip()
            if text in legacy_aliases:
                button.setText(button_map[legacy_aliases[text]])
            elif text == "\u5bfc\u51fa\u8fd0\u884c\u65e5\u5fd7":
                button.setText("\u5bfc\u51fa\u65e5\u5fd7")

        title_aliases = {
            "\u4e70\u5165": "\u4e70\u5165",
            "\u89c2\u5bdf": "\u89c2\u5bdf",
            "\u51cf\u4ed3": "\u51cf\u4ed3",
            "\u79bb\u573a": "\u79bb\u573a",
            "\u5e02\u573a\u60c5\u7eea": "\u5e02\u573a\u60c5\u7eea",
            "\u4e3b\u7ebf\u9898\u6750": "\u4e3b\u7ebf\u9898\u6750",
            "\u9ad8\u4f18\u5148\u7b56\u7565": "\u9ad8\u4f18\u5148\u7b56\u7565",
            "\u7126\u70b9\u6807\u7684": "\u7126\u70b9\u6807\u7684",
        }
        for card_map_name in ["action_flow_cards", "priority_cards"]:
            card_map = getattr(self, card_map_name, None)
            if not card_map:
                continue
            for card in card_map.values():
                title_label = getattr(card, "title_label", None)
                if title_label is not None and title_label.text().strip() in title_aliases:
                    title_label.setText(title_aliases[title_label.text().strip()])

        strategy_combo = getattr(self, "strategy_detail_combo", None)
        if strategy_combo is not None:
            labels = ["\u9f99\u5934\u6a21\u578b", "\u4e3b\u529b\u96f7\u8fbe", "\u64d2\u9f99\u6253\u677f", "\u4ef7\u503c\u4f4e\u5438", "\u4e00\u65e5\u6301\u80a1\u6cd5", "\u6398\u9f99\u51b3\u7b56"]
            current = strategy_combo.currentText()
            strategy_combo.blockSignals(True)
            strategy_combo.clear()
            strategy_combo.addItems(labels)
            strategy_combo.setCurrentText(current if current in labels else labels[0])
            strategy_combo.blockSignals(False)

    def _normalize_board_workspace_texts(self) -> None:
        title_map = {
            "board_text": "\u6253\u677f\u5019\u9009\u6c60",
            "board_monitor_text": "\u70b8\u677f / \u56de\u5c01\u76d1\u63a7",
        }
        for attr_name, title in title_map.items():
            widget = getattr(self, attr_name, None)
            if widget is None:
                continue
            parent = widget.parentWidget()
            while parent is not None and not isinstance(parent, QGroupBox):
                parent = parent.parentWidget()
            if isinstance(parent, QGroupBox):
                parent.setTitle(title)

        button_aliases = {
            "\u5237\u65b0\u6253\u677f\u6c60": "\u5237\u65b0\u6253\u677f\u6c60",
            "\u5bfc\u51fa\u76d8\u524d\u4ea4\u6613\u8ba1\u5212": "\u5bfc\u51fa\u76d8\u524d\u4ea4\u6613\u8ba1\u5212",
            "\u5bfc\u51fa\u6536\u76d8\u590d\u76d8\u65e5\u62a5": "\u5bfc\u51fa\u6536\u76d8\u590d\u76d8\u65e5\u62a5",
        }
        for button in self.findChildren(QPushButton):
            text = button.text().strip()
            if text in button_aliases:
                button.setText(button_aliases[text])

        if hasattr(self, "auto_review_export_checkbox"):
            self.auto_review_export_checkbox.setText("15:05 \u540e\u81ea\u52a8\u5bfc\u51fa\u590d\u76d8\u65e5\u62a5")
        if hasattr(self, "board_text"):
            self._set_plain_text_if_changed(
                self.board_text,
                "\u6253\u677f\u5019\u9009\u6c60\n\n"
                "\u8fd9\u91cc\u4f1a\u6c47\u603b\u5f3a\u52bf\u8fde\u677f\u3001\u56de\u5c01\u8d28\u91cf\u3001\u5165\u573a\u4ef7\u4f4d\u548c\u98ce\u9669\u7b49\u7ea7\u3002\n"
                "\u5148\u751f\u6210\u63a8\u8350\u6c60\u6216\u5728\u626b\u63cf\u9875\u9009\u4e2d\u4e00\u53ea\u80a1\u7968\uff0c\u8fd9\u91cc\u4f1a\u81ea\u52a8\u5207\u5230\u5bf9\u5e94\u7684\u6253\u677f\u7126\u70b9\u3002\n"
                "\u6253\u677f\u9875\u4f1a\u4f18\u5148\u5c55\u793a\u4e3b\u7ebf\u524d\u6392\u3001\u627f\u63a5\u786e\u5b9a\u6027\u548c\u53ef\u6267\u884c\u7684\u56de\u5c01\u533a\u95f4\u3002"
            )
        if hasattr(self, "board_monitor_text"):
            self._set_plain_text_if_changed(
                self.board_monitor_text,
                "\u70b8\u677f / \u56de\u5c01\u76d1\u63a7\n\n"
                "\u8fd9\u91cc\u4f1a\u6301\u7eed\u8ddf\u8e2a\u56de\u5c01\u5f3a\u5ea6\u3001\u70b8\u677f\u98ce\u9669\u548c\u662f\u5426\u8fd8\u4fdd\u7559\u535a\u5f08\u4ef7\u503c\u3002\n"
                "\u76d8\u4e2d\u76d1\u63a7\u751f\u6210\u540e\uff0c\u4f1a\u81ea\u52a8\u5207\u6362\u5230\u5f53\u524d\u6700\u503c\u5f97\u76ef\u7684\u6807\u7684\uff0c\u4e5f\u4f1a\u8ddf\u626b\u63cf\u9875\u8054\u52a8\u3002\n"
                "\u5f53\u5019\u9009\u548c\u76d1\u63a7\u90fd\u5230\u4f4d\u65f6\uff0c\u8fd9\u91cc\u4f1a\u544a\u8bc9\u4f60\u662f\u7ee7\u7eed\u89c2\u5bdf\u3001\u8f6c\u4ea4\u6613\u8fd8\u662f\u76f4\u63a5\u653e\u5f03\u3002"
            )

    def _repair_runtime_widget_texts(self) -> None:
        clean_map = {
            "\u53ea\u770b\u4e3b\u7ebf\u524d\u6392": "\u53ea\u770b\u4e3b\u7ebf\u524d\u6392",
            "\u53ea\u770b\u89c2\u5bdf\u6c60": "\u53ea\u770b\u89c2\u5bdf\u6c60",
            "\u53ea\u770b\u98ce\u9669\u6c60": "\u53ea\u770b\u98ce\u9669\u6c60",
            "\u53ea\u770b\u56de\u907f\u6c60": "\u53ea\u770b\u98ce\u9669\u6c60",
            "\u5bfc\u51fa\u76d8\u524d\u4ea4\u6613\u8ba1\u5212": "\u5bfc\u51fa\u76d8\u524d\u4ea4\u6613\u8ba1\u5212",
            "\u5bfc\u51fa\u6536\u76d8\u590d\u76d8\u65e5\u62a5": "\u5bfc\u51fa\u6536\u76d8\u590d\u76d8\u65e5\u62a5",
            "\u5bfc\u51fa\u65e5\u5fd7": "\u5bfc\u51fa\u65e5\u5fd7",
            "\u5237\u65b0\u8bca\u65ad": "\u5237\u65b0\u8bca\u65ad",
            "\u5237\u65b0\u6253\u677f\u6c60": "\u5237\u65b0\u6253\u677f\u6c60",
            "\u4e70\u5165": "\u4e70\u5165",
            "\u89c2\u5bdf": "\u89c2\u5bdf",
            "\u51cf\u4ed3": "\u51cf\u4ed3",
            "\u79bb\u573a": "\u79bb\u573a",
            "\u5e02\u573a\u60c5\u7eea": "\u5e02\u573a\u60c5\u7eea",
            "\u4e3b\u7ebf\u9898\u6750": "\u4e3b\u7ebf\u9898\u6750",
            "\u9ad8\u4f18\u5148\u7b56\u7565": "\u9ad8\u4f18\u5148\u7b56\u7565",
            "\u7126\u70b9\u6807\u7684": "\u7126\u70b9\u6807\u7684",
        }

        for widget_type in (QPushButton, QCheckBox, QLabel):
            for widget in self.findChildren(widget_type):
                text = widget.text().strip() if hasattr(widget, "text") else ""
                if text in clean_map:
                    widget.setText(clean_map[text])
        self._tune_overview_recommend_tables()
        self._polish_workspace_information_density()
        self._polish_summary_card_blocks()

    def _tune_overview_recommend_tables(self) -> None:
        if hasattr(self, "market_pool_table"):
            table = self.market_pool_table
            table.setAlternatingRowColors(False)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 64))
            header = table.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        if hasattr(self, "daily_pool_table"):
            table = self.daily_pool_table
            table.setAlternatingRowColors(False)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 52))
            header = table.horizontalHeader()
            header.setStretchLastSection(False)
            resize_to_contents = [0, 4, 5, 6, 7, 8, 9, 10, 11, 12, 18, 20]
            stretch_columns = {1, 19}
            for index in range(table.columnCount()):
                if index in stretch_columns:
                    header.setSectionResizeMode(index, QHeaderView.Stretch)
                elif index in resize_to_contents:
                    header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
                else:
                    header.setSectionResizeMode(index, QHeaderView.Interactive)
                    table.setColumnWidth(index, max(table.columnWidth(index), 82))

    def _normalize_overview_builder_texts(self) -> None:
        if hasattr(self, "market_search_input"):
            self.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材")
        if hasattr(self, "market_theme_combo"):
            self.market_theme_combo.blockSignals(True)
            self.market_theme_combo.clear()
            self.market_theme_combo.addItem("全部")
            self.market_theme_combo.blockSignals(False)
        if hasattr(self, "market_history_date_combo"):
            self.market_history_date_combo.blockSignals(True)
            self.market_history_date_combo.clear()
            self.market_history_date_combo.addItem("最新")
            self.market_history_date_combo.blockSignals(False)
        if hasattr(self, "market_refresh_button"):
            self.market_refresh_button.setText("一键刷新算法池")
        if hasattr(self, "market_history_reset_button"):
            self.market_history_reset_button.setText("回到最新")
        if hasattr(self, "dashboard_auto_refresh_checkbox"):
            self._set_label_text_if_changed(self.dashboard_auto_refresh_checkbox, "盘中自动刷新")
        if hasattr(self, "market_status_label"):
            self._set_label_text_if_changed(self.market_status_label, "总览状态：正在建立市场快照...")
        if hasattr(self, "market_header_label"):
            self._set_label_text_if_changed(self.market_header_label, "市场机会工作台")
        if hasattr(self, "market_subheader_label"):
            self._set_label_text_if_changed(self.market_subheader_label, "统一查看主线龙头、趋势机会、消息催化、买卖决策和复盘研究。")
        if hasattr(self, "market_signal_label"):
            self._set_label_text_if_changed(self.market_signal_label, "资金模型 / 策略标签 / 主力净流入 / 换手率")
        if hasattr(self, "market_quote_label"):
            self._set_label_text_if_changed(self.market_quote_label, "开高低收 / 涨跌幅 / 换手 / 主力净流入 / 龙头级别 / 股票池")

        button_groups = [
            ("overview_quick_buttons", ["市场总览", "龙头池", "趋势机会", "消息催化", "交易决策", "复盘研究"], self.activate_overview_quick_action),
            ("market_filter_buttons", ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"], self.set_market_filter),
            ("timeframe_buttons", ["分时", "1分", "5分", "15分", "30分", "60分", "日线", "周线", "月线"], self.set_market_timeframe),
            ("history_window_buttons", ["近1月", "近3月", "近1年", "全部"], self.set_market_history_window),
            ("secondary_indicator_buttons", ["MACD", "RSI", "KDJ"], self.set_market_secondary_indicator),
        ]
        for attr_name, labels, handler in button_groups:
            current_map = getattr(self, attr_name, None)
            if not current_map:
                continue
            buttons = list(current_map.values())
            normalized = {}
            for index, button in enumerate(buttons):
                label = labels[index] if index < len(labels) else button.text()
                try:
                    button.clicked.disconnect()
                except Exception:
                    pass
                self._set_label_text_if_changed(button, label)
                button.clicked.connect(lambda checked=False, current=label, callback=handler: callback(current))
                normalized[label] = button
            setattr(self, attr_name, normalized)

        if hasattr(self, "market_pool_table"):
            self.market_pool_table.setHorizontalHeaderLabels(["序", "股票标识", "资金标签", "策略标签", "涨跌幅", "最新价"])
        if hasattr(self, "right_intel_tabs"):
            if self.right_intel_tabs.count() > 0:
                self.right_intel_tabs.setTabText(0, "主题摘要")
            if self.right_intel_tabs.count() > 1:
                self.right_intel_tabs.setTabText(1, "资金决策")
        if hasattr(self, "market_news_group") and hasattr(self.market_news_group, "setTitle"):
            self.market_news_group.setTitle("消息面")

    def _normalize_aux_workspace_texts(self) -> None:
        if hasattr(self, "tabs"):
            tab_labels = ["龙头主控台", "策略扫描", "每日推荐", "打板监控", "配置", "统一登录", "明细复盘", "交易执行"]
            for index, label in enumerate(tab_labels):
                if index < self.tabs.count():
                    if self.tabs.tabText(index) != label:
                        self.tabs.setTabText(index, label)

        if hasattr(self, "auth_channel_combo"):
            current = self.auth_channel_combo.currentData()
            self.auth_channel_combo.blockSignals(True)
            self.auth_channel_combo.clear()
            self.auth_channel_combo.addItem("东方财富", "eastmoney")
            self.auth_channel_combo.addItem("GM", "gm")
            self.auth_channel_combo.addItem("自定义", "custom")
            for idx in range(self.auth_channel_combo.count()):
                if self.auth_channel_combo.itemData(idx) == current:
                    self.auth_channel_combo.setCurrentIndex(idx)
                    break
            self.auth_channel_combo.blockSignals(False)

        text_map = {
            "active_symbol_label": "当前标的：未选择",
            "broker_status_banner": BROKER_DEFAULT_STATUS_TEXT,
            "orders_focus_label": ORDERS_DEFAULT_FOCUS_TEXT,
            "trade_plan_focus_label": TRADE_PLAN_DEFAULT_FOCUS_TEXT,
            "recommend_status_label": RECOMMEND_DEFAULT_STATUS_TEXT,
            "recommend_empty_title": RECOMMEND_DEFAULT_EMPTY_TITLE,
            "recommend_empty_meta": RECOMMEND_DEFAULT_EMPTY_META,
            "daily_pool_focus_label": RECOMMEND_DEFAULT_FOCUS_TEXT,
            "universe_label": "股票池目录：未加载",
            "scan_summary_label": "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。",
            "last_refresh_label": "最近刷新：等待市场快照建立",
        }
        for attr_name, value in text_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                self._set_label_text_if_changed(widget, value)

        button_map = {
            "recommend_empty_sample_button": RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
            "recommend_empty_refresh_button": RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
            "broker_focus_blocker_button": "定位阻塞",
            "broker_focus_priority_button": "定位前排",
            "generate_order_suggestions_button": "生成盘中计划",
            "confirm_submit_orders_button": "确认提交",
        }
        for attr_name, value in button_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                self._set_label_text_if_changed(widget, value)

        if hasattr(self, "recommend_stage_tabs"):
            for index, label in enumerate(["执行", "策略", "复盘"]):
                if index < self.recommend_stage_tabs.count():
                    if self.recommend_stage_tabs.tabText(index) != label:
                        self.recommend_stage_tabs.setTabText(index, label)
        if hasattr(self, "right_intel_tabs"):
            labels = ["主题摘要", "资金决策"]
            for index, label in enumerate(labels):
                if index < self.right_intel_tabs.count():
                    if self.right_intel_tabs.tabText(index) != label:
                        self.right_intel_tabs.setTabText(index, label)

    def _normalize_scanner_workspace_texts(self) -> None:
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。")
        if hasattr(self, "last_refresh_label"):
            self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")
        if hasattr(self, "monitor_summary_text"):
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会跟踪观察池和焦点票的最新动作、信号、催化与推荐联动。\n"
                "先执行扫描或从观察池选中一只股票，下面会自动切换到对应摘要。"
            )
        if hasattr(self, "universe_label"):
            self._set_label_text_if_changed(self.universe_label, "股票池目录：未加载")
        if hasattr(self, "scan_table"):
            self.scan_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"])

    def _prime_recommend_workspace_defaults(self) -> None:
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, RECOMMEND_DEFAULT_STATUS_TEXT)
        if hasattr(self, "recommend_empty_title"):
            self._set_label_text_if_changed(self.recommend_empty_title, RECOMMEND_DEFAULT_EMPTY_TITLE)
        if hasattr(self, "recommend_empty_meta"):
            self._set_label_text_if_changed(self.recommend_empty_meta, RECOMMEND_DEFAULT_EMPTY_META)
        if hasattr(self, "recommend_empty_sample_button"):
            self._set_label_text_if_changed(self.recommend_empty_sample_button, RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
        if hasattr(self, "recommend_empty_refresh_button"):
            self._set_label_text_if_changed(self.recommend_empty_refresh_button, RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)

        if hasattr(self, "recommend_focus_metric_labels"):
            defaults = {
                "symbol": ("等待标的", "先同步综合机会池"),
                "theme": ("等待主线", "等待主线状态与趋势判断"),
                "action": ("待送审", "等待交易动作生成"),
                "execution": ("待观察", "等待链路阶段同步"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.recommend_focus_metric_labels:
                    self._set_label_text_if_changed(self.recommend_focus_metric_labels[key], value)
                if key in self.recommend_focus_metric_accents:
                    self._set_label_text_if_changed(self.recommend_focus_metric_accents[key], accent)

        if hasattr(self, "recommend_dispatch_text"):
            self._set_plain_text_if_changed(
                self.recommend_dispatch_text,
                "盘中分发节奏\n\n"
                "1. 先确认主线是否延续，再决定今天有没有必要送审。\n"
                "2. 分发顺序优先看前排龙头、容量核心和低风险承接。\n"
                "3. 真正送往交易页的候选，应同时满足位置、量能和风险灯。"
            )
        if hasattr(self, "recommend_focus_review_text"):
            self._set_plain_text_if_changed(
                self.recommend_focus_review_text,
                "单票审查卡\n\n"
                "这里会按焦点标的展开主线地位、买卖节奏、风险点和下一步动作。\n"
                "先选一只票，再看它值不值得进入今日 5 只计划。"
            )
        if hasattr(self, "recommend_queue_text"):
            self._set_plain_text_if_changed(
                self.recommend_queue_text,
                "执行队列\n\n"
                "待审、已审和失败队列会在这里集中展示。\n"
                "真正进入前排的标的，应具备更强的持续性、流动性和执行确定性。"
            )
        if hasattr(self, "strategy_path_text"):
            self._set_plain_text_if_changed(
                self.strategy_path_text,
                "主线推演\n\n"
                "先确认市场主线，再确认龙头位次，最后决定采用打板、低吸还是观察。\n"
                "推荐池生成后，这里会把焦点票的推进路径、失效条件和下一步观察点展开。"
            )

    def _prime_broker_workspace_defaults(self) -> None:
        if hasattr(self, "broker_metric_labels"):
            defaults = {
                "readiness": ("待评估", "等待环境诊断"),
                "capital": ("0.00", "等待资金同步"),
                "risk_reward": ("-- / --", "等待委托建议"),
                "risk_budget": ("待评估", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_metric_labels:
                    self._set_label_text_if_changed(self.broker_metric_labels[key], value)
                if key in self.broker_metric_accents:
                    self._set_label_text_if_changed(self.broker_metric_accents[key], accent)

        if hasattr(self, "broker_order_metric_labels"):
            defaults = {
                "symbol": ("--", "等待选中"),
                "gate": ("待审核", "等待主线闸门"),
                "risk": ("待评估", "等待风险灯"),
                "position": ("待计算", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_order_metric_labels:
                    self._set_label_text_if_changed(self.broker_order_metric_labels[key], value)
                if key in self.broker_order_metric_accents:
                    self._set_label_text_if_changed(self.broker_order_metric_accents[key], accent)
        if hasattr(self, "broker_order_focus_text"):
            self._set_plain_text_if_changed(
                self.broker_order_focus_text,
                "当前委托详情\n\n"
                "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
                "先在上方选中一条委托建议，再决定是否一键确认提交。"
            )
        if hasattr(self, "order_result_text"):
            self._set_plain_text_if_changed(
                self.order_result_text,
                "执行回放\n\n"
                "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                "刷新委托或提交模拟单后，这里会自动切到最新一条。"
            )
        if hasattr(self, "broker_recap_text"):
            self._set_plain_text_if_changed(
                self.broker_recap_text,
                "成交回顾\n\n"
                "这里用于复盘通过率、阻塞原因、成交偏差和主线是否仍然成立。\n"
                "提交记录产生后，可回到这里快速检查执行质量。"
            )

    def _hydrate_empty_workspace_panels(self) -> None:
        panel_defaults = {
            "overview_command_text": "盘前指挥摘要\n\n这里会先汇总市场主线、容量核心、焦点标的和盘前行动顺序。\n刷新市场或载入样本后，会自动切换成今天的总览指挥卡。",
            "overview_execution_text": "执行路径\n\n这里会集中显示买点、止损、目标、失效条件和跨页面联动建议。\n推荐池与交易计划生成后，会自动补齐今天的执行节奏。",
            "market_capital_text": "主力控盘画像\n\n刷新市场或选中股票后，这里会补上主力净流入、换手率、热度和资金承接情况。",
            "market_decision_text": "龙头状态 / 决策建议\n\n推荐池生成后，这里会给出主策略、推荐动作、关键价位和核心逻辑。",
            "market_buy_text": "买入窗口尚未生成。\n刷新市场后，这里会提示今天是否适合买、优先看哪种形态。",
            "market_sell_text": "卖点与减仓提示尚未生成。\n导入持仓或生成交易计划后，这里会给出防守位和退出节奏。",
            "market_breadth_text": "消息面摘要暂未生成。\n载入样本消息或刷新市场后，这里会展示最近催化、主线新闻和异动线索。",
            "market_theme_brief_text": "主线题材摘要暂未生成。\n刷新后会自动汇总强势主题、数量分布和主线持续性。",
            "market_leaderboard_text": "龙头榜单暂未生成。\n刷新市场后，这里会按热度、资金和位置展示前排候选。",
            "market_source_status_text": "数据源状态尚未同步。\n程序会在刷新市场后显示缓存命中、刷新时间和异常诊断。",
            "daily_pool_text": "今日优先候选\n\n每日推荐池生成后，这里会先给出今天最值得盯的 5 只股票，包含名称、代码、主线角色和执行原因。",
            "trade_plan_text": "今日 5 只计划\n\n先刷新推荐池，再自动生成盘前计划。\n这里会整理买点、仓位、风控位和盘中优先级。",
            "position_advice_text": "持仓处理\n\n导入持仓或同步券商账户后，这里会按主线强弱、风险灯和盈亏结构给出继续持有、减仓或离场建议。",
            "board_text": "打板候选池\n\n这里会自动承接扫描页和推荐页的焦点标的，再筛出强势连板、回封质量更高、情绪匹配更好的打板候选。\n当你在扫描页或推荐页选中一只股票后，这里会尽量直接联动到同一只票的打板视角。",
            "board_monitor_text": "炸板 / 回封监控\n\n这里会持续跟踪回封观察、炸板风险、连板高度和是否还值得继续博弈。\n扫描页的盘中监控和打板候选会互相联动，方便你从一个焦点直接跳到另一个焦点。",
            "metrics_text": "绩效面板待更新。\n加载样本或执行扫描后，这里会展示收益、回撤、胜率与阶段统计。",
            "broker_execution_text": "执行回放暂时为空。\n提交模拟委托、刷新订单建议或同步券商状态后，这里会记录执行日志。",
            "detail_decision_text": "交易决策画像\n\n选中一只股票后，这里会汇总主线地位、动作建议、买卖区间和核心逻辑，方便快速判断这笔交易该不该做。",
            "detail_execution_text": "执行状态回收区\n\n这里会整理计划、委托、成交和复盘之间的链路，帮助你快速定位执行偏差。",
            "detail_conclusion_text": "复盘结论\n\n这里会给出这只票今天最值得留下来的结论，包括做对了什么、错过了什么，以及下一次怎样更早识别。",
        }
        for attr_name, text in panel_defaults.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit) and (not widget.toPlainText().strip()):
                self._set_plain_text_if_changed(widget, text)

    def activate_overview_quick_action(self, focus: str) -> None:
        self.set_overview_focus(focus)
        route = OVERVIEW_QUICK_ROUTE_SPECS.get(focus, {"workspace": "overview", "widget": "intraday_chart_view"})
        self._navigate_to_workspace(
            str(route.get("workspace", "overview")),
            str(route.get("widget")) if route.get("widget") else None,
            str(route.get("select_row")) if route.get("select_row") else None,
        )
        if hasattr(self, "overview_command_text"):
            existing = self.overview_command_text.toPlainText().strip()
            prefix = f"\u5f53\u524d\u89c6\u56fe\uff1a{focus}"
            lines = existing.splitlines() if existing else []
            if lines and lines[0].startswith("\u5f53\u524d\u89c6\u56fe\uff1a"):
                lines[0] = prefix
            else:
                lines = [prefix, ""] + lines if lines else [prefix]
            self._set_plain_text_if_changed(self.overview_command_text, "\n".join(lines))
        if hasattr(self, "market_status_label"):
            status_text = self.market_status_label.text().split(" | \u5feb\u6377\uff1a", 1)[0]
            self._set_label_text_if_changed(self.market_status_label, f"{status_text} | \u5feb\u6377\uff1a{focus}")

    def set_overview_focus(self, focus: str) -> None:
        self.overview_focus_mode = focus or "\u5e02\u573a\u603b\u89c8"
        for button in getattr(self, "overview_quick_buttons", {}).values():
            button.blockSignals(True)
            button.setChecked(button.text() == self.overview_focus_mode)
            button.blockSignals(False)

        main_sizes = {
            "\u5e02\u573a\u603b\u89c8": [360, 1020, 360],
            "\u9f99\u5934\u6c60": [300, 1160, 320],
            "\u6da8\u8dcc\u5206\u5e03": [430, 950, 320],
            "\u8d44\u91d1\u65b9\u5411": [320, 1080, 320],
            "\u9898\u6750\u70ed\u5ea6": [320, 930, 430],
            "\u4ea4\u6613\u51b3\u7b56": [300, 900, 480],
        }.get(self.overview_focus_mode, [360, 1020, 360])
        left_sizes = {
            "\u5e02\u573a\u603b\u89c8": [1, 1, 1],
            "\u9f99\u5934\u6c60": [1, 1, 1],
            "\u6da8\u8dcc\u5206\u5e03": [110, 160, 260],
            "\u8d44\u91d1\u65b9\u5411": [150, 110, 150],
            "\u9898\u6750\u70ed\u5ea6": [120, 100, 220],
            "\u4ea4\u6613\u51b3\u7b56": [110, 110, 180],
        }.get(self.overview_focus_mode, [1, 1, 1])
        mini_sizes = {
            "\u5e02\u573a\u603b\u89c8": [1, 1],
            "\u9f99\u5934\u6c60": [1, 1],
            "\u6da8\u8dcc\u5206\u5e03": [1, 1],
            "\u8d44\u91d1\u65b9\u5411": [3, 2],
            "\u9898\u6750\u70ed\u5ea6": [1, 1],
            "\u4ea4\u6613\u51b3\u7b56": [2, 1],
        }.get(self.overview_focus_mode, [1, 1])

        if hasattr(self, "overview_main_splitter"):
            self._configure_splitter(self.overview_main_splitter, main_sizes)
        if hasattr(self, "overview_left_notes_splitter"):
            self._configure_splitter(self.overview_left_notes_splitter, left_sizes)
        if hasattr(self, "overview_mini_chart_splitter"):
            self._configure_splitter(self.overview_mini_chart_splitter, mini_sizes)

        focus_widget = {
            "\u9f99\u5934\u6c60": getattr(self, "market_pool_table", None),
            "\u6da8\u8dcc\u5206\u5e03": getattr(self, "market_breadth_text", None),
            "\u8d44\u91d1\u65b9\u5411": getattr(self, "market_capital_text", None),
            "\u9898\u6750\u70ed\u5ea6": getattr(self, "market_theme_brief_text", None),
            "\u4ea4\u6613\u51b3\u7b56": getattr(self, "market_decision_text", None),
        }.get(self.overview_focus_mode)
        if focus_widget is not None:
            focus_widget.setFocus()

        if hasattr(self, "market_status_label"):
            status_text = self.market_status_label.text()
            if " | \u9875\u9762\uff1a" in status_text:
                base_text, page_suffix = status_text.split(" | \u9875\u9762\uff1a", 1)
                page_text = page_suffix.split(" | \u89c6\u56fe\uff1a", 1)[0]
                self._set_label_text_if_changed(self.market_status_label, f"{base_text} | \u9875\u9762\uff1a{page_text} | \u89c6\u56fe\uff1a{self.overview_focus_mode}")
            else:
                base_text = status_text.split(" | \u89c6\u56fe\uff1a", 1)[0].strip()
                self._set_label_text_if_changed(self.market_status_label, f"{base_text} | \u89c6\u56fe\uff1a{self.overview_focus_mode}")

    def set_market_timeframe(self, timeframe: str) -> None:
        self.market_timeframe_mode = timeframe or "\u65e5\u7ebf"
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

        intraday_height = 300 if self.market_timeframe_mode != "\u65e5\u7ebf" else 250
        daily_height = 320 if self.market_timeframe_mode != "\u65e5\u7ebf" else 360
        if hasattr(self, "intraday_chart_view"):
            self.intraday_chart_view.setMinimumHeight(intraday_height)
            chart = self.intraday_chart_view.chart()
            if chart is not None:
                title = "\u5e02\u573a\u4ee3\u7406\u8d70\u52bf" if self.market_timeframe_mode == "\u65e5\u7ebf" else f"{self.market_timeframe_mode} \u8d70\u52bf"
                if chart.title() != title:
                    chart.setTitle(title)
        if hasattr(self, "daily_chart_view"):
            self.daily_chart_view.setMinimumHeight(daily_height)
            chart = self.daily_chart_view.chart()
            if chart is not None:
                title = "\u65e5\u7ebf\u4e3b\u56fe" if self.market_timeframe_mode == "\u65e5\u7ebf" else f"{self.market_timeframe_mode} \u4e3b\u56fe"
                if chart.title() != title:
                    chart.setTitle(title)
        if hasattr(self, "fund_chart_view"):
            chart = self.fund_chart_view.chart()
            if chart is not None:
                title = "\u4e3b\u529b\u8d44\u91d1" if self.market_timeframe_mode == "\u65e5\u7ebf" else f"{self.market_timeframe_mode} \u8d44\u91d1"
                if chart.title() != title:
                    chart.setTitle(title)
        if hasattr(self, "momentum_chart_view"):
            chart = self.momentum_chart_view.chart()
            if chart is not None:
                title = "\u9f99\u5934\u52a8\u80fd" if self.market_timeframe_mode == "\u65e5\u7ebf" else f"{self.market_timeframe_mode} \u52a8\u80fd"
                if chart.title() != title:
                    chart.setTitle(title)
        if hasattr(self, "market_status_label"):
            base = self.market_status_label.text().split(" | \u7a97\u53e3\uff1a", 1)[0]
            self._set_label_text_if_changed(self.market_status_label, f"{base} | \u7a97\u53e3\uff1a{self.market_timeframe_mode}")

    def _normalize_auth_workspace_texts(self) -> None:
        auth_tab = getattr(self, "auth_tab", None)
        if auth_tab is None:
            return

        title_map = {
            "\u767b\u5f55\u914d\u7f6e": "\u7edf\u4e00\u767b\u5f55",
            "\u767b\u5f55\u8868\u5355": "\u8d26\u53f7\u8fde\u63a5",
            "\u8d26\u6237\u914d\u7f6e": "\u8d26\u53f7\u8fde\u63a5",
            "\u8fde\u63a5\u72b6\u6001": "\u8fde\u63a5\u72b6\u6001",
        }
        for group in auth_tab.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            if title in title_map:
                normalized = title_map[title]
                if title != normalized:
                    group.setTitle(normalized)

        label_map = {
            "login_status_label": "\u5728\u8fd9\u91cc\u7edf\u4e00\u4fdd\u5b58\u4e1c\u65b9\u8d22\u5bcc\u3001GM \u6216\u81ea\u5b9a\u4e49\u6e20\u9053\u7684\u767b\u5f55\u53c2\u6570\uff0c\u540e\u7eed\u4e5f\u65b9\u4fbf\u6269\u5c55\u66f4\u591a\u63a5\u5165\u65b9\u5f0f\u3002",
        }
        for attr_name, value in label_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                self._set_label_text_if_changed(widget, value)

        if hasattr(self, "login_status_text"):
            self._set_plain_text_if_changed(
                self.login_status_text,
                "\u8fde\u63a5\u72b6\u6001\n\n"
                "\u4fdd\u5b58\u540e\uff0c\u8fd9\u91cc\u4f1a\u540c\u6b65\u663e\u793a\u5f53\u524d\u8fde\u63a5\u65b9\u5f0f\u3001\u8d26\u53f7\u6458\u8981\u548c\u53ef\u7528\u72b6\u6001\u3002\n"
                "\u540e\u7eed\u4e5f\u53ef\u4ee5\u5728\u8fd9\u91cc\u8ffd\u52a0\u66f4\u591a\u5238\u5546\u6216 API \u6e20\u9053\u3002"
            )

        button_map = {
            "save_login_button": "\u4fdd\u5b58\u767b\u5f55\u4fe1\u606f",
            "test_login_button": "\u6d4b\u8bd5\u8fde\u63a5",
            "clear_login_button": "\u6e05\u7a7a\u914d\u7f6e",
        }
        for attr_name, value in button_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                self._set_label_text_if_changed(widget, value)

    def _prime_broker_workspace_defaults(self) -> None:
        if hasattr(self, "broker_metric_labels"):
            defaults = {
                "readiness": ("\u5f85\u8bc4\u4f30", "\u7b49\u5f85\u73af\u5883\u8bca\u65ad"),
                "capital": ("0.00", "\u7b49\u5f85\u8d44\u91d1\u540c\u6b65"),
                "risk_reward": ("-- / --", "\u7b49\u5f85\u59d4\u6258\u5efa\u8bae"),
                "risk_budget": ("\u5f85\u8bc4\u4f30", "\u7b49\u5f85\u4ed3\u4f4d\u6d4b\u7b97"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_metric_labels:
                    self._set_label_text_if_changed(self.broker_metric_labels[key], value)
                if key in self.broker_metric_accents:
                    self._set_label_text_if_changed(self.broker_metric_accents[key], accent)

        if hasattr(self, "broker_order_metric_labels"):
            defaults = {
                "symbol": ("--", "\u7b49\u5f85\u9009\u4e2d"),
                "gate": ("\u5f85\u5ba1\u6838", "\u7b49\u5f85\u4e3b\u7ebf\u95f8\u95e8"),
                "risk": ("\u5f85\u8bc4\u4f30", "\u7b49\u5f85\u98ce\u9669\u706f"),
                "position": ("\u5f85\u8ba1\u7b97", "\u7b49\u5f85\u4ed3\u4f4d\u6d4b\u7b97"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_order_metric_labels:
                    self._set_label_text_if_changed(self.broker_order_metric_labels[key], value)
                if key in self.broker_order_metric_accents:
                    self._set_label_text_if_changed(self.broker_order_metric_accents[key], accent)

        if hasattr(self, "broker_order_focus_text"):
            self._set_plain_text_if_changed(
                self.broker_order_focus_text,
                "\u5f53\u524d\u59d4\u6258\u8be6\u60c5\n\n"
                "\u8fd9\u91cc\u4f1a\u6c47\u603b\u7126\u70b9\u59d4\u6258\u7684\u4e3b\u7ebf\u95f8\u95e8\u3001\u52a8\u4f5c\u5efa\u8bae\u3001\u4ed3\u4f4d\u6d4b\u7b97\u548c\u98ce\u9669\u706f\u3002\n"
                "\u5148\u5728\u4e0a\u65b9\u9009\u4e2d\u4e00\u6761\u59d4\u6258\u5efa\u8bae\uff0c\u518d\u51b3\u5b9a\u662f\u5426\u4e00\u952e\u786e\u8ba4\u63d0\u4ea4\u3002"
            )
        if hasattr(self, "order_result_text"):
            self._set_plain_text_if_changed(
                self.order_result_text,
                "\u6267\u884c\u56de\u653e\n\n"
                "\u65b0\u7684\u63d0\u4ea4\u7ed3\u679c\u4f1a\u6309\u65f6\u95f4\u987a\u5e8f\u6c89\u6dc0\u5728\u8fd9\u91cc\uff0c\u5305\u62ec\u8ba2\u5355\u72b6\u6001\u3001\u6210\u4ea4\u72b6\u6001\u3001\u5931\u8d25\u539f\u56e0\u548c\u7cfb\u7edf\u53cd\u9988\u3002\n"
                "\u5237\u65b0\u59d4\u6258\u6216\u63d0\u4ea4\u6a21\u62df\u5355\u540e\uff0c\u8fd9\u91cc\u4f1a\u81ea\u52a8\u5207\u5230\u6700\u65b0\u4e00\u6761\u3002"
            )
        if hasattr(self, "broker_recap_text"):
            self._set_plain_text_if_changed(
                self.broker_recap_text,
                "\u6210\u4ea4\u56de\u987e\n\n"
                "\u8fd9\u91cc\u7528\u4e8e\u590d\u76d8\u901a\u8fc7\u7387\u3001\u963b\u585e\u539f\u56e0\u3001\u6210\u4ea4\u504f\u5dee\u548c\u4e3b\u7ebf\u662f\u5426\u4ecd\u7136\u6210\u7acb\u3002\n"
                "\u63d0\u4ea4\u8bb0\u5f55\u4ea7\u751f\u540e\uff0c\u53ef\u56de\u5230\u8fd9\u91cc\u5feb\u901f\u68c0\u67e5\u6267\u884c\u8d28\u91cf\u3002"
            )

    def _hydrate_empty_workspace_panels(self) -> None:
        panel_defaults = {
            "overview_command_text": "\u76d8\u524d\u6307\u6325\u6458\u8981\n\n\u8fd9\u91cc\u4f1a\u5148\u6c47\u603b\u5e02\u573a\u4e3b\u7ebf\u3001\u5bb9\u91cf\u6838\u5fc3\u3001\u7126\u70b9\u6807\u7684\u548c\u76d8\u524d\u884c\u52a8\u987a\u5e8f\u3002\n\u5237\u65b0\u5e02\u573a\u6216\u8f7d\u5165\u6837\u672c\u540e\uff0c\u4f1a\u81ea\u52a8\u5207\u6362\u6210\u4eca\u5929\u7684\u603b\u89c8\u6307\u6325\u5361\u3002",
            "overview_execution_text": "\u6267\u884c\u8def\u5f84\n\n\u8fd9\u91cc\u4f1a\u96c6\u4e2d\u663e\u793a\u4e70\u70b9\u3001\u6b62\u635f\u3001\u76ee\u6807\u3001\u5931\u6548\u6761\u4ef6\u548c\u8de8\u9875\u9762\u8054\u52a8\u5efa\u8bae\u3002\n\u63a8\u8350\u6c60\u4e0e\u4ea4\u6613\u8ba1\u5212\u751f\u6210\u540e\uff0c\u4f1a\u81ea\u52a8\u8865\u9f50\u4eca\u5929\u7684\u6267\u884c\u8282\u594f\u3002",
            "market_capital_text": "\u4e3b\u529b\u63a7\u76d8\u753b\u50cf\n\n\u5237\u65b0\u5e02\u573a\u6216\u9009\u4e2d\u80a1\u7968\u540e\uff0c\u8fd9\u91cc\u4f1a\u8865\u4e0a\u4e3b\u529b\u51c0\u6d41\u5165\u3001\u6362\u624b\u7387\u3001\u70ed\u5ea6\u548c\u8d44\u91d1\u627f\u63a5\u60c5\u51b5\u3002",
            "market_decision_text": "\u9f99\u5934\u72b6\u6001 / \u51b3\u7b56\u5efa\u8bae\n\n\u63a8\u8350\u6c60\u751f\u6210\u540e\uff0c\u8fd9\u91cc\u4f1a\u7ed9\u51fa\u4e3b\u7b56\u7565\u3001\u63a8\u8350\u52a8\u4f5c\u3001\u5173\u952e\u4ef7\u4f4d\u548c\u6838\u5fc3\u903b\u8f91\u3002",
            "market_buy_text": "\u4e70\u5165\u7a97\u53e3\u5c1a\u672a\u751f\u6210\u3002\n\u5237\u65b0\u5e02\u573a\u540e\uff0c\u8fd9\u91cc\u4f1a\u63d0\u793a\u4eca\u5929\u662f\u5426\u9002\u5408\u4e70\u3001\u4f18\u5148\u770b\u54ea\u79cd\u5f62\u6001\u3002",
            "market_sell_text": "\u5356\u70b9\u4e0e\u51cf\u4ed3\u63d0\u793a\u5c1a\u672a\u751f\u6210\u3002\n\u5bfc\u5165\u6301\u4ed3\u6216\u751f\u6210\u4ea4\u6613\u8ba1\u5212\u540e\uff0c\u8fd9\u91cc\u4f1a\u7ed9\u51fa\u9632\u5b88\u4f4d\u548c\u9000\u51fa\u8282\u594f\u3002",
            "market_breadth_text": "\u6d88\u606f\u9762\u6458\u8981\u6682\u672a\u751f\u6210\u3002\n\u8f7d\u5165\u6837\u672c\u6d88\u606f\u6216\u5237\u65b0\u5e02\u573a\u540e\uff0c\u8fd9\u91cc\u4f1a\u5c55\u793a\u6700\u8fd1\u50ac\u5316\u3001\u4e3b\u7ebf\u65b0\u95fb\u548c\u5f02\u52a8\u7ebf\u7d22\u3002",
            "market_theme_brief_text": "\u4e3b\u7ebf\u9898\u6750\u6458\u8981\u6682\u672a\u751f\u6210\u3002\n\u5237\u65b0\u540e\u4f1a\u81ea\u52a8\u6c47\u603b\u5f3a\u52bf\u4e3b\u9898\u3001\u6570\u91cf\u5206\u5e03\u548c\u4e3b\u7ebf\u6301\u7eed\u6027\u3002",
            "market_leaderboard_text": "\u9f99\u5934\u699c\u5355\u6682\u672a\u751f\u6210\u3002\n\u5237\u65b0\u5e02\u573a\u540e\uff0c\u8fd9\u91cc\u4f1a\u6309\u70ed\u5ea6\u3001\u8d44\u91d1\u548c\u4f4d\u7f6e\u5c55\u793a\u524d\u6392\u5019\u9009\u3002",
            "market_source_status_text": "\u6570\u636e\u6e90\u72b6\u6001\u5c1a\u672a\u540c\u6b65\u3002\n\u7a0b\u5e8f\u4f1a\u5728\u5237\u65b0\u5e02\u573a\u540e\u663e\u793a\u7f13\u5b58\u547d\u4e2d\u3001\u5237\u65b0\u65f6\u95f4\u548c\u5f02\u5e38\u8bca\u65ad\u3002",
            "daily_pool_text": "\u4eca\u65e5\u4f18\u5148\u5019\u9009\n\n\u6bcf\u65e5\u63a8\u8350\u6c60\u751f\u6210\u540e\uff0c\u8fd9\u91cc\u4f1a\u5148\u7ed9\u51fa\u4eca\u5929\u6700\u503c\u5f97\u76ef\u7684 5 \u53ea\u80a1\u7968\uff0c\u5305\u542b\u540d\u79f0\u3001\u4ee3\u7801\u3001\u4e3b\u7ebf\u89d2\u8272\u548c\u6267\u884c\u539f\u56e0\u3002",
            "trade_plan_text": "\u4eca\u65e5 5 \u53ea\u8ba1\u5212\n\n\u5148\u5237\u65b0\u63a8\u8350\u6c60\uff0c\u518d\u81ea\u52a8\u751f\u6210\u76d8\u524d\u8ba1\u5212\u3002\n\u8fd9\u91cc\u4f1a\u6574\u7406\u4e70\u70b9\u3001\u4ed3\u4f4d\u3001\u98ce\u63a7\u4f4d\u548c\u76d8\u4e2d\u4f18\u5148\u7ea7\u3002",
            "position_advice_text": "\u6301\u4ed3\u5904\u7406\n\n\u5bfc\u5165\u6301\u4ed3\u6216\u540c\u6b65\u5238\u5546\u8d26\u6237\u540e\uff0c\u8fd9\u91cc\u4f1a\u6309\u4e3b\u7ebf\u5f3a\u5f31\u3001\u98ce\u9669\u706f\u548c\u76c8\u4e8f\u7ed3\u6784\u7ed9\u51fa\u7ee7\u7eed\u6301\u6709\u3001\u51cf\u4ed3\u6216\u79bb\u573a\u5efa\u8bae\u3002",
            "board_text": "\u6253\u677f\u5019\u9009\u6c60\n\n\u8fd9\u91cc\u4f1a\u81ea\u52a8\u627f\u63a5\u626b\u63cf\u9875\u548c\u63a8\u8350\u9875\u7684\u7126\u70b9\u6807\u7684\uff0c\u518d\u7b5b\u51fa\u5f3a\u52bf\u8fde\u677f\u3001\u56de\u5c01\u8d28\u91cf\u66f4\u9ad8\u3001\u60c5\u7eea\u5339\u914d\u66f4\u597d\u7684\u6253\u677f\u5019\u9009\u3002\n\u5f53\u4f60\u5728\u626b\u63cf\u9875\u6216\u63a8\u8350\u9875\u9009\u4e2d\u4e00\u53ea\u80a1\u7968\u540e\uff0c\u8fd9\u91cc\u4f1a\u5c3d\u91cf\u76f4\u63a5\u8054\u52a8\u5230\u540c\u4e00\u53ea\u7968\u7684\u6253\u677f\u89c6\u89d2\u3002",
            "board_monitor_text": "\u70b8\u677f / \u56de\u5c01\u76d1\u63a7\n\n\u8fd9\u91cc\u4f1a\u6301\u7eed\u8ddf\u8e2a\u56de\u5c01\u89c2\u5bdf\u3001\u70b8\u677f\u98ce\u9669\u3001\u8fde\u677f\u9ad8\u5ea6\u548c\u662f\u5426\u8fd8\u503c\u5f97\u7ee7\u7eed\u535a\u5f08\u3002\n\u626b\u63cf\u9875\u7684\u76d8\u4e2d\u76d1\u63a7\u548c\u6253\u677f\u5019\u9009\u4f1a\u4e92\u76f8\u8054\u52a8\uff0c\u65b9\u4fbf\u4f60\u4ece\u4e00\u4e2a\u7126\u70b9\u76f4\u63a5\u8df3\u5230\u53e6\u4e00\u4e2a\u7126\u70b9\u3002",
            "metrics_text": "\u7ee9\u6548\u9762\u677f\u5f85\u66f4\u65b0\u3002\n\u52a0\u8f7d\u6837\u672c\u6216\u6267\u884c\u626b\u63cf\u540e\uff0c\u8fd9\u91cc\u4f1a\u5c55\u793a\u6536\u76ca\u3001\u56de\u64a4\u3001\u80dc\u7387\u4e0e\u9636\u6bb5\u7edf\u8ba1\u3002",
            "broker_execution_text": "\u6267\u884c\u56de\u653e\u6682\u65f6\u4e3a\u7a7a\u3002\n\u63d0\u4ea4\u6a21\u62df\u59d4\u6258\u3001\u5237\u65b0\u8ba2\u5355\u5efa\u8bae\u6216\u540c\u6b65\u5238\u5546\u72b6\u6001\u540e\uff0c\u8fd9\u91cc\u4f1a\u8bb0\u5f55\u6267\u884c\u65e5\u5fd7\u3002",
            "detail_decision_text": "\u4ea4\u6613\u51b3\u7b56\u753b\u50cf\n\n\u9009\u4e2d\u4e00\u53ea\u80a1\u7968\u540e\uff0c\u8fd9\u91cc\u4f1a\u6c47\u603b\u4e3b\u7ebf\u5730\u4f4d\u3001\u52a8\u4f5c\u5efa\u8bae\u3001\u4e70\u5356\u533a\u95f4\u548c\u6838\u5fc3\u903b\u8f91\uff0c\u65b9\u4fbf\u5feb\u901f\u5224\u65ad\u8fd9\u7b14\u4ea4\u6613\u8be5\u4e0d\u8be5\u505a\u3002",
            "detail_execution_text": "\u6267\u884c\u72b6\u6001\u56de\u6536\u533a\n\n\u8fd9\u91cc\u4f1a\u6574\u7406\u8ba1\u5212\u3001\u59d4\u6258\u3001\u6210\u4ea4\u548c\u590d\u76d8\u4e4b\u95f4\u7684\u94fe\u8def\uff0c\u5e2e\u52a9\u4f60\u5feb\u901f\u5b9a\u4f4d\u6267\u884c\u504f\u5dee\u3002",
            "detail_conclusion_text": "\u590d\u76d8\u7ed3\u8bba\n\n\u8fd9\u91cc\u4f1a\u7ed9\u51fa\u8fd9\u53ea\u7968\u4eca\u5929\u6700\u503c\u5f97\u7559\u4e0b\u6765\u7684\u7ed3\u8bba\uff0c\u5305\u62ec\u505a\u5bf9\u4e86\u4ec0\u4e48\u3001\u9519\u8fc7\u4e86\u4ec0\u4e48\uff0c\u4ee5\u53ca\u4e0b\u4e00\u6b21\u600e\u6837\u66f4\u65e9\u8bc6\u522b\u3002",
        }
        for attr_name, text in panel_defaults.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                current = widget.toPlainText().strip()
                if not current or any(token in current for token in ["\u95b8", "\u93c8", "\u936a", "\u7f01", "\u59d2", "\u69ab", "\u7522"]):
                    self._set_plain_text_if_changed(widget, text)

    def _polish_workspace_information_density(self) -> None:
        card_names = [
            "overview_command_text",
            "overview_execution_text",
            "market_capital_text",
            "market_decision_text",
            "daily_pool_text",
            "trade_plan_text",
            "position_advice_text",
            "broker_order_focus_text",
            "order_result_text",
            "broker_recap_text",
            "detail_decision_text",
            "detail_execution_text",
            "detail_conclusion_text",
        ]
        for attr_name in card_names:
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(max(widget.minimumHeight(), 150))
                widget.setLineWrapMode(QTextEdit.WidgetWidth)
                widget.viewport().setAutoFillBackground(False)
        for group in self.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            if title in {
                "\u4e3b\u9898\u6458\u8981",
                "\u8d44\u91d1\u51b3\u7b56",
                "\u4eca\u65e5\u4f18\u5148\u5019\u9009",
                "\u6267\u884c\u5206\u53d1",
                "\u5355\u7968\u5ba1\u67e5",
                "\u961f\u5217\u6982\u89c8",
            }:
                group.setMinimumHeight(max(group.minimumHeight(), 188))

        splitter_sizes = [
            ("overview_main_splitter", [320, 1100, 380]),
            ("recommend_dispatch_splitter", [400, 600, 300]),
            ("recommend_summary_splitter", [420, 860]),
            ("recommend_recap_middle_splitter", [360, 900]),
            ("recommend_recap_bottom_splitter", [360, 900]),
            ("recommend_review_splitter", [720, 520]),
            ("broker_control_splitter", [500, 540, 340]),
            ("broker_middle_splitter", [480, 760]),
            ("broker_order_focus_splitter", [820, 340]),
        ]
        for attr_name, sizes in splitter_sizes:
            splitter = getattr(self, attr_name, None)
            if isinstance(splitter, QSplitter):
                self._configure_splitter(splitter, sizes)

        for attr_name, height in {
            "market_theme_brief_text": 188,
            "market_source_status_text": 188,
            "market_capital_text": 236,
            "market_decision_text": 236,
            "detail_decision_text": 260,
            "detail_execution_text": 260,
            "detail_conclusion_text": 260,
        }.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(max(widget.minimumHeight(), height))

    def _polish_summary_card_blocks(self) -> None:
        card_maps = [
            getattr(self, "overview_summary_cards", None),
            getattr(self, "recommend_summary_cards", None),
            getattr(self, "overview_priority_cards", None),
            getattr(self, "action_flow_cards", None),
            getattr(self, "priority_cards", None),
        ]
        for card_map in card_maps:
            if not card_map:
                continue
            for card in card_map.values():
                if isinstance(card, QWidget):
                    card.setMinimumHeight(max(card.minimumHeight(), 112))
                    card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
                for label_name in ["title_label", "count_label", "focus_label", "note_label"]:
                    label = getattr(card, label_name, None)
                    if isinstance(label, QLabel):
                        label.setWordWrap(True)
                        label.setMinimumHeight(max(label.minimumHeight(), 20 if label_name == "title_label" else 24))

    def _symbol_identity_text(self, symbol: str) -> str:
        stock_name = self._stock_name_for_symbol(symbol) if symbol else "未选择"
        stock_id = self._stock_id_for_symbol(symbol) if symbol else "--"
        return f"{stock_name} ({stock_id} / {symbol or '--'})"

    def _refresh_monitor_summary(self, symbol: str = "") -> None:
        if not hasattr(self, "monitor_summary_text"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会跟踪观察池和焦点票的最新动作、信号、催化与推荐联动。\n"
                "先执行扫描或从观察池选中一只股票，下面会自动切换到对应摘要。"
            )
            self._refresh_scanner_focus_status("")
            self._refresh_scanner_focus_cards("")
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        lines = [f"盘中焦点：{self._symbol_identity_text(target)}"]
        if scan_row is not None:
            lines.append(f"动作：{self._display_action(scan_row.action)} | 信号：{self._display_label(scan_row.label)} | 评分：{scan_row.score}")
            lines.append(f"收盘价：{scan_row.close:.2f} | 信号日期：{scan_row.signal_date}")
            if scan_row.reason:
                lines.append(f"原因：{scan_row.reason}")
        elif latest is not None:
            lines.append(f"最新信号：{self._display_label(latest.label)} | 评分：{latest.score} | 收盘价：{latest.close:.2f}")
            if latest.reason:
                lines.append(f"原因：{latest.reason}")
        else:
            lines.append("当前没有盘中信号，等待扫描链路同步。")

        if recommendation is not None:
            lines.append(
                f"推荐联动：{self._display_action(recommendation.action)} | 主线 {recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 分层 {recommendation.opportunity_tier or '待确认'}"
            )
            lines.append(f"催化：{recommendation.catalyst or '等待消息催化'}")
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        if board_candidate is not None:
            lines.append(
                f"打板联动：{board_candidate['trigger_style']} | 风险 {board_candidate['risk_level']} | 入场 {board_candidate['planned_entry']} | 止损 {board_candidate['planned_stop']} | 目标 {board_candidate['planned_target']}"
            )
        board_monitor = self._board_monitor_snapshot_for_symbol(target)
        if board_monitor is not None:
            lines.append(
                f"打板监控：{board_monitor['monitor_state']} | 强度 {board_monitor['strength']} | 连续性 {board_monitor['continuity']}"
            )
        self._set_plain_text_if_changed(self.monitor_summary_text, "\n".join(lines))
        self._refresh_scanner_focus_status(target)
        self._refresh_scanner_focus_cards(target)
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_status(self, symbol: str = "") -> None:
        if not hasattr(self, "scan_summary_label"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        total_scans = len(getattr(self, "scan_rows", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        if not target:
            text = f"已扫描 {total_scans} 条信号 | 观察池 {watch_count} | 监控 {monitor_count}" if total_scans else "扫描状态：等待首轮扫描，同步观察池与监控焦点。"
            self._set_label_text_if_changed(self.scan_summary_label, text)
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        stock_name = self._stock_name_for_symbol(target)
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_piece = (
            f" | 打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} / 分数 {board_candidate['board_score']}"
            if board_candidate is not None
            else ""
        )
        if scan_row is not None:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | {self._display_action(scan_row.action)} / {self._display_label(scan_row.label)} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count}{board_piece}",
            )
        elif recommendation is not None:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | 推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} | 主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}{board_piece}",
            )
        else:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | 已纳入工作台联动 | 监控 {monitor_count}{board_piece}",
            )
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_focus_metric_labels", None)
        accents = getattr(self, "scanner_focus_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_label_text_if_changed(labels["symbol"], "--")
            self._set_label_text_if_changed(accents["symbol"], "等待选中")
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "等待扫描")
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待联动")
            self._set_label_text_if_changed(labels["monitor"], "待联动")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        stock_name = self._stock_name_for_symbol(target)
        self._set_label_text_if_changed(labels["symbol"], stock_name)
        self._set_label_text_if_changed(accents["symbol"], self._stock_id_for_symbol(target))
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        if scan_row is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(scan_row, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(scan_row, "label", "WATCH")))
        elif latest is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(latest, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(latest, "label", "WATCH")))
        else:
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "暂无信号")

        if board_candidate is not None:
            self._set_label_text_if_changed(labels["monitor"], board_candidate["trigger_style"])
            self._set_label_text_if_changed(accents["monitor"], f"风险 {board_candidate['risk_level']} | 分数 {board_candidate['board_score']}")
        else:
            self._set_label_text_if_changed(labels["monitor"], "待联动")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")

        if recommendation is not None:
            self._set_label_text_if_changed(labels["action"], self._display_action(getattr(recommendation, "action", "WATCH")))
            self._set_label_text_if_changed(accents["action"], f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}")
        else:
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待推荐池联动")

    def _refresh_scanner_summary_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_summary_metric_labels", None)
        accents = getattr(self, "scanner_summary_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        scan_count = len(getattr(self, "scan_rows", []))
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        summary_count = len(getattr(self, "backtest_summaries", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        self._set_label_text_if_changed(labels["scan"], str(scan_count) if scan_count else "0")
        self._set_label_text_if_changed(labels["watch"], str(watch_count) if watch_count else "0")
        self._set_label_text_if_changed(labels["summary"], str(summary_count) if summary_count else "0")
        self._set_label_text_if_changed(labels["monitor"], str(monitor_count) if monitor_count else "0")
        if not target:
            self._set_label_text_if_changed(accents["scan"], "等待扫描链路")
            self._set_label_text_if_changed(accents["watch"], "等待观察池")
            self._set_label_text_if_changed(accents["summary"], "等待回测摘要")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
            return

        stock_name = self._stock_name_for_symbol(target)
        stock_id = self._stock_id_for_symbol(target)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        latest_summary = next((item for item in getattr(self, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_monitor = self._board_monitor_snapshot_for_symbol(target)
        self._set_label_text_if_changed(accents["scan"], f"{stock_name} / {stock_id}")
        if recommendation is not None:
            self._set_label_text_if_changed(accents["watch"], f"推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}")
        else:
            self._set_label_text_if_changed(accents["watch"], "观察池联动")
        if latest_summary is not None:
            self._set_label_text_if_changed(accents["summary"], f"回测 {latest_summary.trades} 笔 / 收益 {latest_summary.total_return:.2%}")
        else:
            self._set_label_text_if_changed(accents["summary"], "等待样本回填")
        if board_candidate is not None:
            self._set_label_text_if_changed(accents["monitor"], f"打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']}")
        elif board_monitor is not None:
            self._set_label_text_if_changed(accents["monitor"], f"监控 {board_monitor['monitor_state']} / {board_monitor['strength']}")
        else:
            self._set_label_text_if_changed(accents["monitor"], "盘中监控联动")

    def open_overview_source_to_news(self) -> None:
        self.activate_overview_quick_action("消息催化")

    def _refresh_submission_focus(self) -> None:
        record = self._selected_submission_record()
        if hasattr(self, "order_result_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "执行回放\n\n"
                    "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                    "刷新委托或提交模拟单后，这里会自动切到最新一条。\n"
                    "你也可以先从推荐页或打板页送审候选，再回到这里看执行反馈。"
                )
            else:
                lines = [
                    "执行回放",
                    "",
                    f"时间：{record.get('timestamp', '--')}",
                    f"股票：{self._symbol_identity_text(record.get('symbol', ''))}",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))}",
                    f"成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"失败原因：{record.get('failure_reason', '') or '无'}",
                    f"反馈信息：{record.get('message', '') or '等待更多反馈'}",
                ]
                self._set_plain_text_if_changed(self.order_result_text, "\n".join(lines))
        if hasattr(self, "broker_recap_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.broker_recap_text,
                    "成交回顾\n\n"
                    "提交后，这里会沉淀通过率、阻塞原因、成交偏差和回看要点。\n"
                    "当订单建议生成后，可以在这里快速检查执行质量。"
                )
            else:
                symbol = record.get("symbol", "")
                recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
                lines = [
                    f"成交回顾：{self._stock_name_for_symbol(symbol)}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))} | 成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
                ]
                if recommendation is not None:
                    lines.append(f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}")
                    lines.append(f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))}")
                    lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
                message = record.get("message", "") or ""
                if message:
                    lines.append(f"系统反馈：{message}")
                failure_reason = record.get("failure_reason", "") or ""
                if failure_reason:
                    lines.append(f"需要处理：{failure_reason}")
                else:
                    lines.append("后续动作：可继续查看委托明细，或回到推荐页校验主线和仓位。")
                self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))

    def _refresh_detail_workspace_panels(self) -> None:
        if not hasattr(self, "metrics_text"):
            return
        symbol = self.active_symbol or ""
        if not symbol:
            return
        stock_name = self._stock_name_for_symbol(symbol)
        stock_id = self._stock_id_for_symbol(symbol)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == symbol), None)
        latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if item.label != "NONE"), None)
        selected_signal = self._selected_detail_signal_snapshot()
        selected_trade = self._selected_detail_trade_snapshot()

        if hasattr(self, "detail_decision_text"):
            lines = [f"单票决策：{stock_name} ({stock_id} / {symbol})"]
            if recommendation is not None:
                lines.extend(
                    [
                        f"主线：{recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 动作：{self._display_action(recommendation.action)}",
                        f"主策略：{getattr(recommendation, 'primary_strategy', '') or '掘龙决策'} | 分层：{getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                        f"买点：{(recommendation.entry_price or recommendation.close):.2f} | 止损：{(recommendation.stop_price or recommendation.close * 0.95):.2f} | 目标：{(recommendation.target_price or recommendation.close * 1.08):.2f}",
                        f"逻辑：{recommendation.rationale or '等待推荐逻辑生成。'}",
                    ]
                )
            elif latest_signal is not None:
                lines.extend([f"最新信号：{self._display_label(latest_signal.label)} | 评分 {latest_signal.score}", f"原因：{latest_signal.reason}"])
            else:
                lines.append("当前没有可用的决策信息。")
            if selected_signal is not None:
                lines.extend(["", f"焦点信号：{selected_signal['date']} | {selected_signal['label']} | 评分 {selected_signal['score']}", f"触发原因：{selected_signal['reason']}"])
            elif getattr(self, "signal_table", None) is not None and self.signal_table.rowCount() > 0:
                lines.append("可在下方“近期信号”里点选一条记录，查看更细的触发原因。")
            self._set_plain_text_if_changed(self.detail_decision_text, "\n".join(lines))

        if hasattr(self, "detail_execution_text"):
            lines = [f"执行联动：{stock_name}"]
            order_intent = next((item for item in getattr(self, "order_intents", []) if getattr(item, "symbol", "") == symbol), None)
            execution_row = next((item for item in getattr(self, "order_result_rows", []) if str(item.get("symbol", "")) == symbol), None)
            if order_intent is not None:
                lines.append(f"委托建议：{getattr(order_intent, 'side', '')} {getattr(order_intent, 'quantity', 0)} 股 @ {getattr(order_intent, 'price', 0.0):.2f}")
            if execution_row:
                lines.append(f"最近执行：{execution_row.get('order_status', '--')} / {execution_row.get('fill_status', '--')}")
                lines.append(f"反馈：{execution_row.get('message', '--')}")
            if order_intent is None and not execution_row:
                lines.append("当前没有委托或执行记录，可先去交易页生成委托建议。")
            if selected_trade is not None:
                lines.extend(["", f"焦点成交：{selected_trade['entry_date']} -> {selected_trade['exit_date']}", f"价格区间：{selected_trade['entry_price']} -> {selected_trade['exit_price']} | 股数 {selected_trade['shares']}", f"盈亏：{selected_trade['pnl']} | 退出原因：{selected_trade['exit_reason']}"])
            elif getattr(self, "trades_table", None) is not None and self.trades_table.rowCount() > 0:
                lines.append("可在下方“交易记录”里点选一笔成交，快速回看执行质量。")
            self._set_plain_text_if_changed(self.detail_execution_text, "\n".join(lines))

        if hasattr(self, "detail_conclusion_text"):
            lines = [f"复盘结论：{stock_name}"]
            if latest_signal is not None:
                lines.append(f"最近信号：{latest_signal.date} | {self._display_label(latest_signal.label)} | 评分 {latest_signal.score}")
            if recommendation is not None:
                lines.append(f"建议动作：{self._display_action(recommendation.action)} | 下一步：{getattr(recommendation, 'next_focus', '') or '继续观察主线与量能'}")
            if selected_signal is not None:
                lines.append(f"当前聚焦：{selected_signal['label']}，优先回看当日量价和主线强度。")
            if selected_trade is not None:
                lines.append(f"成交复盘：{selected_trade['exit_reason']}，可对照进出场纪律检查执行质量。")
            lines.append("后续动作：可继续去推荐页看同主线候选，或去交易页查看委托执行。")
            self._set_plain_text_if_changed(self.detail_conclusion_text, "\n".join(lines))

    def _symbol_identity_text(self, symbol: str) -> str:
        stock_name = self._stock_name_for_symbol(symbol) if symbol else "未选中"
        stock_id = self._stock_id_for_symbol(symbol) if symbol else "--"
        return f"{stock_name} ({stock_id} / {symbol or '--'})"

    def _refresh_monitor_summary(self, symbol: str = "") -> None:
        if not hasattr(self, "monitor_summary_text"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "盘中监控摘要\n\n"
                "这里会联动展示观察池与焦点个股的最新动作、信号、催化与推荐结论。\n"
                "先执行扫描，或从观察池里选中一只股票，下方会自动切换到对应摘要。",
            )
            self._refresh_scanner_focus_status("")
            self._refresh_scanner_focus_cards("")
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        lines = [f"盘中焦点：{self._symbol_identity_text(target)}"]
        if scan_row is not None:
            lines.append(f"动作：{self._display_action(scan_row.action)} | 信号：{self._display_label(scan_row.label)} | 评分：{scan_row.score}")
            lines.append(f"收盘价：{scan_row.close:.2f} | 信号日期：{scan_row.signal_date}")
            if scan_row.reason:
                lines.append(f"原因：{scan_row.reason}")
        elif latest is not None:
            lines.append(f"最新信号：{self._display_label(latest.label)} | 评分：{latest.score} | 收盘价：{latest.close:.2f}")
            if latest.reason:
                lines.append(f"原因：{latest.reason}")
        else:
            lines.append("当前没有盘中信号，等待扫描链路同步。")

        if recommendation is not None:
            lines.append(
                f"推荐联动：{self._display_action(recommendation.action)} | 主线 {recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 分层 {recommendation.opportunity_tier or '待确认'}"
            )
            lines.append(f"催化：{recommendation.catalyst or '等待消息催化'}")
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        if board_candidate is not None:
            lines.append(
                f"打板联动：{board_candidate['trigger_style']} | 风险 {board_candidate['risk_level']} | 入场 {board_candidate['planned_entry']} | 止损 {board_candidate['planned_stop']} | 目标 {board_candidate['planned_target']}"
            )
        board_monitor = self._board_monitor_snapshot_for_symbol(target)
        if board_monitor is not None:
            lines.append(
                f"打板监控：{board_monitor['monitor_state']} | 强度 {board_monitor['strength']} | 持续性 {board_monitor['continuity']}"
            )
        self._set_plain_text_if_changed(self.monitor_summary_text, "\n".join(lines))
        self._refresh_scanner_focus_status(target)
        self._refresh_scanner_focus_cards(target)
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_status(self, symbol: str = "") -> None:
        if not hasattr(self, "scan_summary_label"):
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        total_scans = len(getattr(self, "scan_rows", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        if not target:
            text = (
                f"已扫描 {total_scans} 条信号 | 观察池 {watch_count} | 监控 {monitor_count}"
                if total_scans
                else "扫描状态：等待首轮扫描，同步观察池与监控焦点。"
            )
            self._set_label_text_if_changed(self.scan_summary_label, text)
            self._refresh_scanner_summary_cards("")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        stock_name = self._stock_name_for_symbol(target)
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_piece = (
            f" | 打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']} / 分数 {board_candidate['board_score']}"
            if board_candidate is not None
            else ""
        )
        if scan_row is not None:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | {self._display_action(scan_row.action)} / {self._display_label(scan_row.label)} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count}{board_piece}",
            )
        elif recommendation is not None:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | 推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} | 主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}{board_piece}",
            )
        else:
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"当前焦点：{stock_name} | 已纳入工作台联动 | 监控 {monitor_count}{board_piece}",
            )
        self._refresh_scanner_summary_cards(target)

    def _refresh_scanner_focus_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_focus_metric_labels", None)
        accents = getattr(self, "scanner_focus_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        if not target:
            self._set_label_text_if_changed(labels["symbol"], "--")
            self._set_label_text_if_changed(accents["symbol"], "等待选中")
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "等待扫描")
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待联动")
            self._set_label_text_if_changed(labels["monitor"], "待联动")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
            return

        scan_row = next((row for row in getattr(self, "scan_rows", []) if row.symbol == target), None)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        analyses = list(getattr(self, "universe_analyses", {}).get(target, []))
        latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1] if analyses else None)
        self._set_label_text_if_changed(labels["symbol"], self._stock_name_for_symbol(target))
        self._set_label_text_if_changed(accents["symbol"], self._stock_id_for_symbol(target))
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        if scan_row is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(scan_row, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(scan_row, "label", "WATCH")))
        elif latest is not None:
            self._set_label_text_if_changed(labels["signal"], f"{getattr(latest, 'score', 0)}")
            self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(latest, "label", "WATCH")))
        else:
            self._set_label_text_if_changed(labels["signal"], "--")
            self._set_label_text_if_changed(accents["signal"], "暂无信号")

        if board_candidate is not None:
            self._set_label_text_if_changed(labels["monitor"], board_candidate["trigger_style"])
            self._set_label_text_if_changed(accents["monitor"], f"风险 {board_candidate['risk_level']} | 分数 {board_candidate['board_score']}")
        else:
            self._set_label_text_if_changed(labels["monitor"], "待联动")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")

        if recommendation is not None:
            self._set_label_text_if_changed(labels["action"], self._display_action(getattr(recommendation, "action", "WATCH")))
            self._set_label_text_if_changed(
                accents["action"],
                f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
            )
        else:
            self._set_label_text_if_changed(labels["action"], "观察")
            self._set_label_text_if_changed(accents["action"], "等待推荐池联动")

    def _refresh_scanner_summary_cards(self, symbol: str = "") -> None:
        labels = getattr(self, "scanner_summary_metric_labels", None)
        accents = getattr(self, "scanner_summary_metric_accents", None)
        if not labels or not accents:
            return
        target = symbol or self._selected_symbol_from_watchlist() or self.active_symbol or ""
        scan_count = len(getattr(self, "scan_rows", []))
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        summary_count = len(getattr(self, "backtest_summaries", []))
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        self._set_label_text_if_changed(labels["scan"], str(scan_count) if scan_count else "0")
        self._set_label_text_if_changed(labels["watch"], str(watch_count) if watch_count else "0")
        self._set_label_text_if_changed(labels["summary"], str(summary_count) if summary_count else "0")
        self._set_label_text_if_changed(labels["monitor"], str(monitor_count) if monitor_count else "0")
        if not target:
            self._set_label_text_if_changed(accents["scan"], "等待扫描链路")
            self._set_label_text_if_changed(accents["watch"], "等待观察池")
            self._set_label_text_if_changed(accents["summary"], "等待回测摘要")
            self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
            return

        stock_name = self._stock_name_for_symbol(target)
        stock_id = self._stock_id_for_symbol(target)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == target), None)
        latest_summary = next((item for item in getattr(self, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
        board_candidate = self._board_candidate_snapshot_for_symbol(target)
        board_monitor = self._board_monitor_snapshot_for_symbol(target)
        self._set_label_text_if_changed(accents["scan"], f"{stock_name} / {stock_id}")
        if recommendation is not None:
            self._set_label_text_if_changed(
                accents["watch"],
                f"推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
            )
        else:
            self._set_label_text_if_changed(accents["watch"], "观察池联动")
        if latest_summary is not None:
            self._set_label_text_if_changed(accents["summary"], f"回测 {latest_summary.trades} 笔 / 收益 {latest_summary.total_return:.2%}")
        else:
            self._set_label_text_if_changed(accents["summary"], "等待样本回填")
        if board_candidate is not None:
            self._set_label_text_if_changed(accents["monitor"], f"打板 {board_candidate['trigger_style']} / 风险 {board_candidate['risk_level']}")
        elif board_monitor is not None:
            self._set_label_text_if_changed(accents["monitor"], f"监控 {board_monitor['monitor_state']} / {board_monitor['strength']}")
        else:
            self._set_label_text_if_changed(accents["monitor"], "盘中监控联动")

    def open_overview_source_to_news(self) -> None:
        self.activate_overview_quick_action("消息催化")

    def _refresh_submission_focus(self) -> None:
        record = self._selected_submission_record()
        if hasattr(self, "order_result_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "执行回放\n\n"
                    "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                    "刷新委托或提交模拟单后，这里会自动切到最新一条。\n"
                    "你也可以先从推荐页或打板页发送候选，再回到这里查看执行反馈。"
                )
            else:
                lines = [
                    "执行回放",
                    "",
                    f"时间：{record.get('timestamp', '--')}",
                    f"股票：{self._symbol_identity_text(record.get('symbol', ''))}",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))}",
                    f"成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"失败原因：{record.get('failure_reason', '') or '无'}",
                    f"反馈信息：{record.get('message', '') or '等待更多反馈'}",
                ]
                self._set_plain_text_if_changed(self.order_result_text, "\n".join(lines))
        if hasattr(self, "broker_recap_text"):
            if record is None:
                self._set_plain_text_if_changed(
                    self.broker_recap_text,
                    "成交回顾\n\n"
                    "提交后，这里会沉淀通过率、阻塞原因、成交偏差和回看要点。\n"
                    "当订单建议生成后，可以在这里快速检查执行质量。"
                )
            else:
                symbol = record.get("symbol", "")
                recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
                lines = [
                    f"成交回顾：{self._stock_name_for_symbol(symbol)}",
                    f"订单状态：{self._display_order_status(record.get('order_status', ''))} | 成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                    f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
                ]
                if recommendation is not None:
                    lines.append(f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}")
                    lines.append(f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))}")
                    lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
                message = record.get("message", "") or ""
                if message:
                    lines.append(f"系统反馈：{message}")
                failure_reason = record.get("failure_reason", "") or ""
                if failure_reason:
                    lines.append(f"需要处理：{failure_reason}")
                else:
                    lines.append("后续动作：可继续查看委托明细，或回到推荐页校验主线和仓位。")
                self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))

    def _refresh_detail_workspace_panels(self) -> None:
        if not hasattr(self, "metrics_text"):
            return
        symbol = self.active_symbol or ""
        if not symbol:
            return
        stock_name = self._stock_name_for_symbol(symbol)
        stock_id = self._stock_id_for_symbol(symbol)
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == symbol), None)
        latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if item.label != "NONE"), None)
        selected_signal = self._selected_detail_signal_snapshot()
        selected_trade = self._selected_detail_trade_snapshot()

        if hasattr(self, "detail_decision_text"):
            lines = [f"单票决策：{stock_name} ({stock_id} / {symbol})"]
            if recommendation is not None:
                lines.extend(
                    [
                        f"主线：{recommendation.mainline_tag or recommendation.theme_name or '待确认'} | 动作：{self._display_action(recommendation.action)}",
                        f"主策略：{getattr(recommendation, 'primary_strategy', '') or '擒龙决策'} | 分层：{getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                        f"买点：{(recommendation.entry_price or recommendation.close):.2f} | 止损：{(recommendation.stop_price or recommendation.close * 0.95):.2f} | 目标：{(recommendation.target_price or recommendation.close * 1.08):.2f}",
                        f"逻辑：{recommendation.rationale or '等待推荐逻辑生成。'}",
                    ]
                )
            elif latest_signal is not None:
                lines.extend([f"最新信号：{self._display_label(latest_signal.label)} | 评分 {latest_signal.score}", f"原因：{latest_signal.reason}"])
            else:
                lines.append("当前没有可用的决策信息。")
            if selected_signal is not None:
                lines.extend(["", f"焦点信号：{selected_signal['date']} | {selected_signal['label']} | 评分 {selected_signal['score']}", f"触发原因：{selected_signal['reason']}"])
            elif getattr(self, "signal_table", None) is not None and self.signal_table.rowCount() > 0:
                lines.append("可在下方“近期信号”里点选一条记录，查看更细的触发原因。")
            self._set_plain_text_if_changed(self.detail_decision_text, "\n".join(lines))

        if hasattr(self, "detail_execution_text"):
            lines = [f"执行联动：{stock_name}"]
            order_intent = next((item for item in getattr(self, "order_intents", []) if getattr(item, "symbol", "") == symbol), None)
            execution_row = next((item for item in getattr(self, "order_result_rows", []) if str(item.get("symbol", "")) == symbol), None)
            if order_intent is not None:
                lines.append(f"委托建议：{getattr(order_intent, 'side', '')} {getattr(order_intent, 'quantity', 0)} 股 @ {getattr(order_intent, 'price', 0.0):.2f}")
            if execution_row:
                lines.append(f"最近执行：{execution_row.get('order_status', '--')} / {execution_row.get('fill_status', '--')}")
                lines.append(f"反馈：{execution_row.get('message', '--')}")
            if order_intent is None and not execution_row:
                lines.append("当前没有委托或执行记录，可先去交易页生成委托建议。")
            if selected_trade is not None:
                lines.extend(["", f"焦点成交：{selected_trade['entry_date']} -> {selected_trade['exit_date']}", f"价格区间：{selected_trade['entry_price']} -> {selected_trade['exit_price']} | 股数 {selected_trade['shares']}", f"盈亏：{selected_trade['pnl']} | 退出原因：{selected_trade['exit_reason']}"])
            elif getattr(self, "trades_table", None) is not None and self.trades_table.rowCount() > 0:
                lines.append("可在下方“交易记录”里点选一笔成交，快速回看执行质量。")
            self._set_plain_text_if_changed(self.detail_execution_text, "\n".join(lines))

        if hasattr(self, "detail_conclusion_text"):
            lines = [f"复盘结论：{stock_name}"]
            if latest_signal is not None:
                lines.append(f"最近信号：{latest_signal.date} | {self._display_label(latest_signal.label)} | 评分 {latest_signal.score}")
            if recommendation is not None:
                lines.append(f"建议动作：{self._display_action(recommendation.action)} | 下一步：{getattr(recommendation, 'next_focus', '') or '继续观察主线与量能'}")
            if selected_signal is not None:
                lines.append(f"当前聚焦：{selected_signal['label']}，优先回看当日量价和主线强度。")
            if selected_trade is not None:
                lines.append(f"成交复盘：{selected_trade['exit_reason']}，可对照进出场纪律检查执行质量。")
            lines.append("后续动作：可继续去推荐页看同主线候选，或去交易页查看委托执行。")
            self._set_plain_text_if_changed(self.detail_conclusion_text, "\n".join(lines))

    def _workspace_badge_text(self, current_name: str) -> str:
        label = current_name or "龙头主控台"
        if label == "策略扫描":
            scan_count = len(getattr(self, "scan_rows", []) or [])
            watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
            monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
            return f"量化猎手 Pro v2.2 · {label} · 扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}"
        if label == "打板监控":
            board_count = getattr(self, "board_table", None).rowCount() if hasattr(self, "board_table") else 0
            monitor_count = getattr(self, "board_monitor_table", None).rowCount() if hasattr(self, "board_monitor_table") else 0
            return f"量化猎手 Pro v2.2 · {label} · 候选 {board_count} / 监控 {monitor_count}"
        if label == "每日推荐":
            pool_count = len(getattr(self, "daily_pool_rows", []) or [])
            plan_count = len(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or [])
            return f"量化猎手 Pro v2.2 · {label} · 候选 {pool_count} / 计划 {plan_count}"
        if label == "交易执行":
            pending_orders = len(getattr(self, "order_intents", []) or [])
            submitted_orders = len(getattr(self, "order_submission_records", []) or [])
            return f"量化猎手 Pro v2.2 · {label} · 待审 {pending_orders} / 已提交 {submitted_orders}"
        return f"量化猎手 Pro v2.2 · {label}"

    def _refresh_workspace_status_labels(self) -> None:
        if hasattr(self, "top_badge"):
            current_name = self._workspace_name_for_index(self.tabs.currentIndex()) if hasattr(self, "tabs") else "龙头主控台"
            self._set_label_text_if_changed(self.top_badge, self._workspace_badge_text(current_name))
        self._refresh_shell_header()
        self._refresh_live_workspace_summary_panels()
        self._refresh_workspace_focus_banners()
        self._refresh_submission_focus()
        self._refresh_scanner_focus_status()
        self._refresh_monitor_summary()

        if hasattr(self, "broker_status_banner"):
            pending_orders = len(getattr(self, "order_intents", []) or [])
            submitted_orders = len(getattr(self, "order_submission_records", []) or [])
            summary = getattr(self, "last_broker_execution_summary", {}) or {}
            blockers = list(summary.get("blockers", []) or [])
            warnings = list(summary.get("warnings", []) or [])
            if blockers:
                banner_text = f"交易状态：红灯阻塞 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：先处理阻塞项，再进入确认。"
            elif warnings and pending_orders:
                banner_text = f"交易状态：黄灯复核 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：复核风险后进入确认。"
            elif pending_orders:
                banner_text = f"交易状态：绿灯待审 | 待审 {pending_orders} / 已提交 {submitted_orders} | 下一步：优先推进高等级委托送审。"
            elif submitted_orders:
                banner_text = f"交易状态：已提交 {submitted_orders} 笔 | 下一步：跟踪成交、回执与执行偏差。"
            else:
                banner_text = "交易状态：先确认主线、趋势与消息，再进入委托确认。"
            self._set_label_text_if_changed(self.broker_status_banner, banner_text, tooltip=banner_text)

        if hasattr(self, "orders_focus_label") and not getattr(self, "order_intents", []):
            self._set_label_text_if_changed(self.orders_focus_label, ORDERS_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "trade_plan_focus_label") and not getattr(getattr(self, "current_trade_plan", None), "decisions", []):
            self._set_label_text_if_changed(self.trade_plan_focus_label, TRADE_PLAN_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "daily_pool_focus_label") and not getattr(self, "daily_pool_rows", []):
            self._set_label_text_if_changed(self.daily_pool_focus_label, RECOMMEND_DEFAULT_FOCUS_TEXT)

    def _refresh_shell_header(self) -> None:
        current_name = self._workspace_name_for_index(self.tabs.currentIndex()) if hasattr(self, "tabs") else "龙头主控台"
        if hasattr(self, "shell_workspace_chip"):
            set_shell_chip(self.shell_workspace_chip, current_name)

        market_source_label = {
            "remote": "远端实时",
            "cache": "本地缓存",
            "cache_only": "只读缓存",
            "sample": "示例模式",
            "unknown": "等待行情接入",
        }.get(getattr(self, "market_data_source", "unknown"), "等待行情接入")
        if getattr(self, "last_market_success_at", ""):
            market_value = f"{market_source_label} · {self.last_market_success_at[-8:]}"
        elif getattr(self, "last_market_error", ""):
            market_value = f"{market_source_label} · 异常"
        else:
            market_value = market_source_label
        if hasattr(self, "shell_market_chip"):
            set_shell_chip(self.shell_market_chip, market_value)

        dashboard_auto = hasattr(self, "dashboard_auto_refresh_checkbox") and self.dashboard_auto_refresh_checkbox.isChecked()
        scanner_auto = hasattr(self, "auto_refresh_checkbox") and self.auto_refresh_checkbox.isChecked()
        if self._is_job_running("market_refresh") or self._is_job_running("scan_universe"):
            refresh_value = "刷新中"
        elif dashboard_auto and scanner_auto:
            refresh_value = "双通道自动"
        elif dashboard_auto:
            refresh_value = "总览自动"
        elif scanner_auto:
            refresh_value = "扫描自动"
        else:
            refresh_value = "手动"
        if hasattr(self, "shell_refresh_chip"):
            set_shell_chip(self.shell_refresh_chip, refresh_value)

        runtime_value = {
            "running": "任务执行中",
            "success": "最近成功",
            "failed": "最近失败",
            "idle": "空闲",
        }.get(getattr(self, "last_job_status", "idle"), "空闲")
        if getattr(self, "last_job_name", "") and getattr(self, "last_job_status", "") == "running":
            runtime_value = self.last_job_name
        if hasattr(self, "shell_runtime_chip"):
            set_shell_chip(self.shell_runtime_chip, runtime_value)

        trade_plan = getattr(self, "current_trade_plan", None)
        trade_decisions = list(getattr(trade_plan, "decisions", []) or [])
        pending_orders = len(getattr(self, "order_intents", []) or [])
        submitted_orders = len(getattr(self, "order_submission_records", []) or [])
        pool_count = len(getattr(self, "daily_pool_rows", []) or [])
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()))
        paper_analytics = summarize_paper_trading_performance(paper_state)
        paper_closed_trades = int(paper_analytics.get("closed_trade_count", 0) or 0)
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []))
        warnings = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("warnings", []))
        risk_state = "红灯" if blockers else ("黄灯" if warnings else "绿灯")
        pipeline_story = _qh_shell_pipeline_story_v41(
            pool_count=pool_count,
            trade_decisions_count=len(trade_decisions),
            pending_orders=pending_orders,
            submitted_orders=submitted_orders,
            paper_enabled=bool(getattr(paper_state, "enabled", False)),
            paper_closed_trades=paper_closed_trades,
        )
        if hasattr(self, "shell_pipeline_chip"):
            set_shell_chip(self.shell_pipeline_chip, pipeline_story)
        market_running = self._is_job_running("market_refresh")
        scan_running = self._is_job_running("scan_universe")
        active_runtime = getattr(self, "last_job_name", "") or ("market_refresh" if market_running else ("scan_universe" if scan_running else "idle"))
        if market_running and scan_running:
            pulse_headline = "系统脉冲：行情与扫描双线程运行中，工作台正在推进最新快照。"
        elif market_running:
            pulse_headline = "系统脉冲：行情刷新进行中，主控台正在更新市场总览与题材脉冲。"
        elif scan_running:
            pulse_headline = "系统脉冲：扫描任务进行中，候选池与监控焦点正在同步。"
        elif pending_orders:
            pulse_headline = f"系统脉冲：推荐 {pool_count} 只，已形成计划 {len(trade_decisions)} 笔，待审委托 {pending_orders} 笔。"
        elif trade_decisions:
            pulse_headline = f"系统脉冲：推荐池已转成交易计划，当前 {len(trade_decisions)} 笔可进入审查。"
        elif pool_count:
            pulse_headline = f"系统脉冲：推荐池已生成 {pool_count} 只候选，正在等待计划与执行联动。"
        elif submitted_orders:
            pulse_headline = f"系统脉冲：已提交 {submitted_orders} 笔委托，等待成交回执与风控复核。"
        else:
            pulse_headline = "系统脉冲：终端正在等待市场快照、候选优先级与交易链路同步。"
        if hasattr(self, "shell_pulse_label"):
            self._set_label_text_if_changed(self.shell_pulse_label, pulse_headline, tooltip=pulse_headline)

        if market_running or scan_running:
            next_step = "下一步：等待后台任务完成后自动落到主线、候选和焦点状态。"
        elif blockers:
            next_step = f"下一步：先处理阻塞项，再推进交易确认。首条阻塞：{blockers[0]}"
        elif pending_orders:
            next_step = f"下一步：复核主线闸门与风险灯，推动 {pending_orders} 笔委托进入确认。"
        elif trade_decisions:
            next_step = "下一步：从高优先级计划中选股送审，打通推荐到交易链路。"
        elif pool_count:
            next_step = "下一步：继续从推荐池生成交易计划，并压缩人工判断路径。"
        else:
            next_step = "下一步：先建立市场快照，再生成推荐池并推进交易链路。"
        if hasattr(self, "shell_pulse_hint"):
            self._set_label_text_if_changed(self.shell_pulse_hint, next_step, tooltip=next_step)
        stage_text = (
            "阶段：市场同步"
            if market_running or scan_running
            else ("阶段：风控阻塞" if blockers else ("阶段：委托待审" if pending_orders else ("阶段：计划就绪" if trade_decisions else ("阶段：推荐生成" if pool_count else "阶段：等待启动"))))
        )
        market_stamp = getattr(self, "last_market_success_at", "") or "等待行情接入"
        job_stamp = getattr(self, "last_job_finished_at", "") or "待执行"
        meta_text = " | ".join(
            [
                stage_text,
                f"风险灯 {risk_state}",
                f"推荐 {pool_count}",
                f"计划 {len(trade_decisions)}",
                f"待审 {pending_orders}",
                f"已提交 {submitted_orders}",
                f"实验闭环 {paper_closed_trades}",
                f"任务 {active_runtime}",
                f"市场 {market_stamp[-8:] if len(market_stamp) >= 8 else market_stamp}",
                f"完成 {job_stamp[-8:] if len(job_stamp) >= 8 else job_stamp}",
            ]
        )
        if hasattr(self, "shell_pulse_meta"):
            self._set_label_text_if_changed(self.shell_pulse_meta, meta_text, tooltip=meta_text)

    def _tune_workspace_splitters(self) -> None:
        splitter_sizes = [
            ("overview_main_splitter", [300, 1180, 360]),
            ("overview_left_notes_splitter", [128, 128, 196]),
            ("overview_mini_chart_splitter", [3, 3, 2]),
            ("recommend_dispatch_splitter", [380, 650, 320]),
            ("recommend_summary_splitter", [420, 900]),
            ("recommend_recap_middle_splitter", [340, 940]),
            ("recommend_recap_bottom_splitter", [340, 940]),
            ("recommend_review_splitter", [740, 520]),
            ("broker_control_splitter", [470, 600, 330]),
            ("broker_middle_splitter", [430, 820]),
            ("broker_order_focus_splitter", [860, 320]),
        ]
        for attr_name, sizes in splitter_sizes:
            splitter = getattr(self, attr_name, None)
            if isinstance(splitter, QSplitter):
                self._configure_splitter(splitter, sizes)
                splitter.setChildrenCollapsible(False)

        for attr_name, height in {
            "market_pool_table": 300,
            "daily_pool_table": 440,
            "board_table": 300,
            "board_monitor_table": 240,
            "trade_plan_table": 280,
            "position_advice_table": 260,
            "execution_table": 260,
            "signal_table": 260,
            "trades_table": 260,
        }.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTableWidget):
                widget.setMinimumHeight(max(widget.minimumHeight(), height))

        for attr_name, height in {
            "monitor_summary_text": 150,
            "board_text": 148,
            "board_monitor_text": 148,
            "license_status_text": 220,
            "config_notes_text": 190,
            "metrics_text": 190,
            "detail_decision_text": 260,
            "detail_execution_text": 260,
            "detail_conclusion_text": 260,
            "broker_order_focus_text": 320,
        }.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(max(widget.minimumHeight(), height))
                widget.setMaximumHeight(16777215)

        if hasattr(self, "watchlist_widget"):
            self.watchlist_widget.setMinimumHeight(max(self.watchlist_widget.minimumHeight(), 260))

    def _has_mojibake_text(self, text: str) -> bool:
        if not text:
            return True
        return any(token in text for token in ["鍒", "鏃", "鐩", "閫", "缁", "璁", "寰", "榫", "甯", "鎵", "鏈"])

    def _normalize_aux_workspace_texts(self) -> None:
        if hasattr(self, "tabs"):
            tab_labels = ["龙头主控台", "策略扫描", "每日推荐", "打板监控", "配置", "统一登录", "明细复盘", "交易执行"]
            for index, label in enumerate(tab_labels):
                if index < self.tabs.count():
                    if self.tabs.tabText(index) != label:
                        self.tabs.setTabText(index, label)

        if hasattr(self, "auth_channel_combo"):
            current = self.auth_channel_combo.currentData()
            self.auth_channel_combo.blockSignals(True)
            self.auth_channel_combo.clear()
            self.auth_channel_combo.addItem("东方财富", "eastmoney")
            self.auth_channel_combo.addItem("GM", "gm")
            self.auth_channel_combo.addItem("自定义渠道", "custom")
            for idx in range(self.auth_channel_combo.count()):
                if self.auth_channel_combo.itemData(idx) == current:
                    self.auth_channel_combo.setCurrentIndex(idx)
                    break
            self.auth_channel_combo.blockSignals(False)

        text_map = {
            "active_symbol_label": "当前标的：未选择",
            "broker_status_banner": BROKER_DEFAULT_STATUS_TEXT,
            "orders_focus_label": ORDERS_DEFAULT_FOCUS_TEXT,
            "trade_plan_focus_label": TRADE_PLAN_DEFAULT_FOCUS_TEXT,
            "recommend_status_label": RECOMMEND_DEFAULT_STATUS_TEXT,
            "recommend_empty_title": RECOMMEND_DEFAULT_EMPTY_TITLE,
            "recommend_empty_meta": RECOMMEND_DEFAULT_EMPTY_META,
            "daily_pool_focus_label": RECOMMEND_DEFAULT_FOCUS_TEXT,
            "universe_label": "股票池目录：未加载",
            "scan_summary_label": "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。",
            "last_refresh_label": "最近刷新：等待市场快照建立",
        }
        for attr_name, value in text_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                current = widget.text().strip() if hasattr(widget, "text") else ""
                if not current or self._has_mojibake_text(current):
                    self._set_label_text_if_changed(widget, value)

        button_map = {
            "recommend_empty_sample_button": RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT,
            "recommend_empty_refresh_button": RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT,
            "broker_focus_blocker_button": "定位阻塞",
            "broker_focus_priority_button": "定位前排",
            "generate_order_suggestions_button": "生成盘中计划",
            "confirm_submit_orders_button": "确认提交",
        }
        for attr_name, value in button_map.items():
            widget = getattr(self, attr_name, None)
            if widget is not None and hasattr(widget, "setText"):
                self._set_label_text_if_changed(widget, value)

        if hasattr(self, "recommend_stage_tabs"):
            for index, label in enumerate(["执行", "策略", "复盘"]):
                if index < self.recommend_stage_tabs.count():
                    if self.recommend_stage_tabs.tabText(index) != label:
                        self.recommend_stage_tabs.setTabText(index, label)
        if hasattr(self, "right_intel_tabs"):
            for index, label in enumerate(["主题摘要", "资金决策"]):
                if index < self.right_intel_tabs.count():
                    if self.right_intel_tabs.tabText(index) != label:
                        self.right_intel_tabs.setTabText(index, label)

    def _normalize_scanner_workspace_texts(self) -> None:
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：等待首轮扫描，生成观察池与盘中监控焦点。")
        if hasattr(self, "last_refresh_label") and self._has_mojibake_text(self.last_refresh_label.text().strip()):
                self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")
        elif hasattr(self, "last_refresh_label") and "尚未刷新" in self.last_refresh_label.text():
            self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")
        if hasattr(self, "monitor_summary_text"):
            text = self.monitor_summary_text.toPlainText().strip()
            if not text or self._has_mojibake_text(text):
                self._set_plain_text_if_changed(
                    self.monitor_summary_text,
                    "盘中监控摘要\n\n"
                    "这里会联动展示扫描结果、观察池和盘中监控的焦点变化。\n"
                    "选中任意一条记录后，下方会自动切换到对应的信号、动作和复盘摘要。"
                )
        if hasattr(self, "universe_label") and self._has_mojibake_text(self.universe_label.text().strip()):
            self._set_label_text_if_changed(self.universe_label, "股票池目录：未加载")
        if hasattr(self, "scan_table"):
            self.scan_table.setHorizontalHeaderLabels(["日期", "股票名称", "股票代码", "动作", "信号", "评分", "收盘价", "成交额", "原因"])

    def _normalize_auth_workspace_texts(self) -> None:
        auth_tab = getattr(self, "auth_tab", None)
        if auth_tab is None:
            return
        for group in auth_tab.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            title_map = {
                "登录配置": "统一登录",
                "登录表单": "账户连接",
                "账户配置": "账户连接",
                "连接状态": "连接状态",
            }
            if title in title_map or self._has_mojibake_text(title):
                normalized = title_map.get(title, "账户连接")
                if title != normalized:
                    group.setTitle(normalized)
        for button in auth_tab.findChildren(QPushButton):
            text = (button.text() or "").strip()
            button_map = {
                "保存登录配置": "保存登录信息",
                "保存账户": "保存登录信息",
                "测试连接": "校验连接",
            }
            if text in button_map:
                self._set_label_text_if_changed(button, button_map[text])
        if hasattr(self, "login_status_text"):
            channel_text = self.auth_channel_combo.currentText() if hasattr(self, "auth_channel_combo") else "东方财富"
            username = self.login_inputs.get("username").text().strip() if "username" in getattr(self, "login_inputs", {}) else "未填写"
            account_id = self.login_inputs.get("account_id").text().strip() if "account_id" in getattr(self, "login_inputs", {}) else "未填写"
            token_filled = "已填写" if "token" in getattr(self, "login_inputs", {}) and self.login_inputs["token"].text().strip() else "未填写"
            self._set_plain_text_if_changed(
                self.login_status_text,
                "登录与渠道说明\n\n"
                f"- 当前渠道：{channel_text}\n"
                f"- 登录账号：{username or '未填写'}\n"
                f"- 账户 ID：{account_id or '未填写'}\n"
                f"- SDK Token：{token_filled}\n\n"
                "安全边界\n"
                "- 这里仅保存和展示登录参数，不绕过券商安全校验。\n"
                "- 真实下单仍由 GM SDK / 桥接脚本执行，并保留人工确认。\n"
                "- 后续如果增加新渠道，可以继续在这里扩展。"
            )

    def _normalize_config_workspace_texts(self) -> None:
        config_tab = getattr(self, "config_tab", None)
        if config_tab is None:
            return
        for group in config_tab.findChildren(QGroupBox):
            title = (group.title() or "").strip()
            title_map = {
                "策略参数": "策略参数",
                "盘前输出": "盘前输出",
                "授权与状态": "授权与状态",
                "风险设置": "风险与仓位",
            }
            if title in title_map or self._has_mojibake_text(title):
                normalized = title_map.get(title, title or "配置分组")
                if title != normalized:
                    group.setTitle(normalized)
        if hasattr(self, "license_status_text"):
            capabilities = self._license_capabilities()
            plan_name = str(self.state.license_plan or "TRIAL").upper()
            plan_label = {"TRIAL": "试用版", "PRO": "专业版", "ENTERPRISE": "企业版"}.get(plan_name, plan_name)
            auto_report = "开启" if self.state.auto_daily_plan_export else "关闭"
            template_name = self.state.daily_plan_template or "balanced"
            self._set_plain_text_if_changed(
                self.license_status_text,
                "授权与状态\n\n"
                f"- 当前方案：{plan_label} ({plan_name})\n"
                f"- 自动盘前报告：{auto_report}\n"
                f"- 盘前候选上限：{capabilities['daily_plan_export_limit']} 只\n"
                f"- 关注题材：{len(self.state.focus_themes)} 个\n"
                f"- 模板：{template_name}\n"
                f"- 主线前排数量：{self.state.strategy_top_theme_limit}\n\n"
                "这里会展示当前方案、功能边界和切换后的即时状态。"
            )
        if hasattr(self, "config_notes_text"):
            self._set_plain_text_if_changed(
                self.config_notes_text,
                "配置说明\n\n"
                "- 当前配置会直接影响每日推荐、盘前计划、盘中监控和仓位控制。\n"
                "- 主线阈值越高，开仓越偏向龙头和前排。\n"
                "- 关注题材会影响排序、报告和提醒。\n"
                "- 保存配置后，登录页、推荐页和交易页都会同步刷新说明。"
            )

    def _prime_recommend_workspace_defaults(self) -> None:
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, RECOMMEND_DEFAULT_STATUS_TEXT)
        if hasattr(self, "recommend_empty_title"):
            self._set_label_text_if_changed(self.recommend_empty_title, RECOMMEND_DEFAULT_EMPTY_TITLE)
        if hasattr(self, "recommend_empty_meta"):
            self._set_label_text_if_changed(self.recommend_empty_meta, RECOMMEND_DEFAULT_EMPTY_META)
        if hasattr(self, "recommend_empty_sample_button"):
            self._set_label_text_if_changed(self.recommend_empty_sample_button, RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
        if hasattr(self, "recommend_empty_refresh_button"):
            self._set_label_text_if_changed(self.recommend_empty_refresh_button, RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)
        if hasattr(self, "last_refresh_label") and (
            not self.last_refresh_label.text().strip()
            or self._has_mojibake_text(self.last_refresh_label.text().strip())
            or "尚未刷新" in self.last_refresh_label.text()
        ):
            self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")

        if hasattr(self, "recommend_focus_metric_labels"):
            defaults = {
                "symbol": ("等待标的", "先同步综合机会池"),
                "theme": ("等待主线", "等待主线状态与趋势判断"),
                "action": ("待送审", "等待交易动作生成"),
                "execution": ("待观察", "等待链路阶段同步"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.recommend_focus_metric_labels:
                    self._set_label_text_if_changed(self.recommend_focus_metric_labels[key], value)
                if key in self.recommend_focus_metric_accents:
                    self._set_label_text_if_changed(self.recommend_focus_metric_accents[key], accent)

        if hasattr(self, "recommend_summary_cards"):
            defaults = {
                "logic": ("等待主线同步", "等待主线逻辑、位置和风险因子汇总。"),
                "plan": ("等待计划生成", "等待盘前 5 只计划和执行优先级。"),
                "pulse": ("等待温度同步", "等待市场温度、周期与仓位上限。"),
                "holding": ("等待持仓导入", "等待持仓导入后生成处理建议。"),
            }
            for key, card in self.recommend_summary_cards.items():
                if hasattr(card, "set_data"):
                    headline, detail = defaults.get(key, ("--", "等待链路同步"))
                    card.set_data(headline, detail)

        if hasattr(self, "recommend_dispatch_text"):
            self._set_plain_text_if_changed(
                self.recommend_dispatch_text,
                "盘中分发节奏\n\n"
                "1. 先确认主线是否延续，再决定今天是否需要送审。\n"
                "2. 分发顺序优先看前排龙头、容量核心和低风险承接。\n"
                "3. 真正送往交易页的候选，应同时满足位置、量能和风险灯。"
            )
        if hasattr(self, "recommend_focus_review_text"):
            self._set_plain_text_if_changed(
                self.recommend_focus_review_text,
                "焦点票复核\n\n"
                "这里会总结当前焦点票的主线地位、执行优先级、风险灯和下一步动作。"
            )
        if hasattr(self, "recommend_queue_text"):
            self._set_plain_text_if_changed(
                self.recommend_queue_text,
                "推荐队列说明\n\n"
                "程序会基于主线强度、位置、持续性、消息催化和执行难度自动排序。"
            )
        if hasattr(self, "strategy_path_text"):
            self._set_plain_text_if_changed(
                self.strategy_path_text,
                "主线推演路径\n\n"
                "等待推荐池生成后，这里会展示今天的核心主线、轮动路径和优先策略。"
            )

    def _prime_broker_workspace_defaults(self) -> None:
        if hasattr(self, "broker_metric_labels"):
            defaults = {
                "readiness": ("待评估", "等待环境诊断"),
                "capital": ("0.00", "等待资金同步"),
                "risk_reward": ("-- / --", "等待委托建议"),
                "risk_budget": ("待评估", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_metric_labels:
                    self._set_label_text_if_changed(self.broker_metric_labels[key], value)
                if key in self.broker_metric_accents:
                    self._set_label_text_if_changed(self.broker_metric_accents[key], accent)

        if hasattr(self, "broker_order_metric_labels"):
            defaults = {
                "symbol": ("--", "等待选中"),
                "gate": ("待审核", "等待主线闸门"),
                "risk": ("待评估", "等待风险灯"),
                "position": ("待计算", "等待仓位测算"),
            }
            for key, (value, accent) in defaults.items():
                if key in self.broker_order_metric_labels:
                    self._set_label_text_if_changed(self.broker_order_metric_labels[key], value)
                if key in self.broker_order_metric_accents:
                    self._set_label_text_if_changed(self.broker_order_metric_accents[key], accent)

        if hasattr(self, "broker_order_focus_text"):
            self._set_plain_text_if_changed(
                self.broker_order_focus_text,
                "当前委托详情\n\n"
                "这里会汇总焦点委托的主线闸门、动作建议、仓位测算和风险灯。\n"
                "先在上方选中一条委托建议，再决定是否一键确认提交。"
            )
        if hasattr(self, "order_result_text"):
            self._set_plain_text_if_changed(
                self.order_result_text,
                "执行回放\n\n"
                "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                "刷新委托或提交模拟单后，这里会自动切换到最新一条。"
            )
        if hasattr(self, "broker_recap_text"):
            self._set_plain_text_if_changed(
                self.broker_recap_text,
                "成交回顾\n\n"
                "这里用于复盘通过率、阻塞原因、成交偏差，以及主线是否仍然成立。\n"
                "提交记录产生后，可以回到这里快速检查执行质量。"
            )

    def _hydrate_empty_workspace_panels(self) -> None:
        fill_texts = {
            "overview_command_text": "盘前指挥摘要\n\n这里会先汇总市场主线、容量核心、焦点标的和盘前行动顺序。\n刷新市场或载入样本后，会自动切换成今天的总览指挥卡。",
            "overview_execution_text": "执行路径\n\n这里会集中展示买点、止损、目标、失效条件和跨页面联动建议。\n推荐池与交易计划生成后，会自动补齐今天的执行节奏。",
            "market_capital_text": "主力控盘画像\n\n刷新市场或选中股票后，这里会补上主力净流入、换手率、热度和资金承接情况。",
            "market_decision_text": "龙头状态 / 决策建议\n\n推荐池生成后，这里会给出主策略、推荐动作、关键价位和核心逻辑。",
            "market_buy_text": "买入窗口尚未生成。\n刷新市场后，这里会提示今天是否适合买、优先看哪种形态。",
            "market_sell_text": "卖点与减仓提示尚未生成。\n导入持仓或生成交易计划后，这里会给出防守位和退出节奏。",
            "market_breadth_text": "消息面摘要暂未生成。\n载入样本消息或刷新市场后，这里会展示最近催化、主线新闻和异动线索。",
            "market_theme_brief_text": "主线题材摘要暂未生成。\n刷新后会自动汇总强势主题、数量分布和主线持续性。",
            "market_leaderboard_text": "龙头榜单暂未生成。\n刷新市场后，这里会按热度、资金和位置展示前排候选。",
            "market_source_status_text": "数据源状态尚未同步。\n程序会在刷新市场后显示缓存命中、刷新时间和异常诊断。",
            "daily_pool_text": "今日优先候选\n\n每日推荐池生成后，这里会先给出今天最值得盯的 5 只股票，包含名称、代码、主线角色和执行原因。",
            "trade_plan_text": "今日 5 只计划\n\n先刷新推荐池，再自动生成盘前计划。\n这里会整理买点、仓位、风控位和盘中优先级。",
            "position_advice_text": "持仓处理\n\n导入持仓或同步券商账户后，这里会按主线强弱、风险灯和盈亏结构给出继续持有、减仓或离场建议。",
            "board_text": "打板候选池\n\n这里会自动承接扫描页和推荐页的焦点标的，再筛出强势连板、回封质量更高、情绪匹配更好的打板候选。",
            "board_monitor_text": "炸板 / 回封监控\n\n这里会持续跟踪回封观察、炸板风险、连板高度和是否还值得继续博弈。",
            "metrics_text": "绩效面板待更新。\n加载样本或执行扫描后，这里会显示收益、回撤、胜率与阶段统计。",
            "broker_execution_text": "执行回放暂时为空。\n提交模拟委托、刷新订单建议或同步券商状态后，这里会记录执行日志。",
            "detail_decision_text": "交易决策画像\n\n选中一只股票后，这里会汇总主线地位、动作建议、买卖区间和核心逻辑，方便快速判断这笔交易该不该做。",
            "detail_execution_text": "执行状态回收\n\n这里会关联委托建议、提交结果和成交记录，帮助你复盘执行有没有偏离原计划。",
            "detail_conclusion_text": "复盘结论\n\n这里会沉淀单票的核心教训、下一步观察点，以及是否值得继续跟踪同主线标的。",
        }
        for attr_name, text in fill_texts.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                current = widget.toPlainText().strip()
                if not current or self._has_mojibake_text(current):
                    self._set_plain_text_if_changed(widget, text)

    def _normalize_action_row_texts(self) -> None:
        label_map = {
            "去看推荐": "查看推荐池",
            "去看交易": "前往交易执行",
            "去交易页": "前往交易执行",
            "看观察池": "查看观察池",
            "看消息催化": "查看消息催化",
        }
        tooltip_map = {
            "查看推荐池": "跳转到推荐页，并尽量联动当前焦点股票。",
            "查看消息催化": "切到消息催化视图，查看新闻和题材驱动。",
            "回到总览": "返回总览页，继续从龙头池和市场全局查看。",
            "前往交易执行": "跳转到交易页，查看委托建议、执行回放和提交入口。",
            "查看总览": "回到总览页，继续看龙头池和市场结构。",
            "定位推荐池": "把焦点定位到推荐池表格，便于继续筛选。",
            "重算计划": "重新生成今日 5 只计划和盘中节奏。",
            "查看观察池": "跳到观察池，查看等待确认的标的。",
            "查看风险池": "查看风险、减仓和退出建议。",
            "查看推荐": "跳到推荐页，并同步当前股票。",
            "查看扫描": "跳到扫描页，并同步当前股票。",
            "刷新监控": "刷新打板监控与回封观察焦点。",
            "定位委托": "定位到委托建议列表，优先查看待提交订单。",
            "查看委托": "查看委托表格与当前建议。",
            "查看成交": "查看提交记录、执行结果和成交回放。",
            "刷新诊断": "刷新运行日志、任务状态和诊断面板。",
            "导出日志": "导出当前运行日志，便于排查问题。",
            "查看复盘": "跳到复盘页查看单票信号、成交和结论。",
        }
        for row_name in [
            "overviewThemeActionRow",
            "overviewCapitalActionRow",
            "overviewDecisionActionRow",
            "scannerTopActionRow",
            "recommendPoolActionRow",
            "recommendPlanActionRow",
            "recommendPulseActionRow",
            "recommendHoldingActionRow",
            "boardCandidateActionRow",
            "boardMonitorActionRow",
            "brokerGateActionRow",
            "brokerExecutionActionRow",
            "brokerRecapActionRow",
            "runtimeLogActionRow",
            "detailMetricsActionRow",
            "detailDecisionActionRow",
            "detailExecutionActionRow",
            "detailConclusionActionRow",
        ]:
            row = self.findChild(QWidget, row_name)
            if row is None:
                continue
            for button in row.findChildren(QPushButton):
                text = (button.text() or "").strip()
                normalized = label_map.get(text, text)
                if normalized and normalized != text:
                    self._set_label_text_if_changed(button, normalized)
                tip = tooltip_map.get(normalized)
                if tip:
                    button.setToolTip(tip)

    def _focus_symbol_everywhere(self, symbol: str, origin: str = "") -> None:
        if not symbol:
            return
        self._sync_symbol_across_workspaces(symbol, origin=origin)
        if symbol in getattr(self, "universe_bars", {}):
            self.select_symbol(symbol, origin=origin)
        self._refresh_monitor_summary(symbol)
        self._refresh_scanner_focus_status(symbol)
        self._refresh_scanner_focus_cards(symbol)
        self._refresh_scanner_summary_cards(symbol)
        self._refresh_board_focus_panels(symbol)
        self._refresh_broker_order_focus()
        self._refresh_submission_focus()
        self._refresh_detail_workspace_panels()
        self._refresh_live_workspace_summary_panels()
        self._refresh_workspace_focus_banners()

    def _select_trade_plan_row_by_stock_id(self, stock_id: str) -> bool:
        if not stock_id or not hasattr(self, "trade_plan_table"):
            return False
        for row_index in range(self.trade_plan_table.rowCount()):
            row_values = []
            for column in (1, 2, 3):
                item = self.trade_plan_table.item(row_index, column)
                row_values.append(item.text() if item else "")
            if stock_id in row_values:
                return self._select_table_row_if_needed(self.trade_plan_table, row_index)
        return False

    def _select_position_advice_row_by_stock_id(self, stock_id: str) -> bool:
        if not stock_id or not hasattr(self, "position_advice_table"):
            return False
        for row_index in range(self.position_advice_table.rowCount()):
            row_values = []
            for column in (1, 2):
                item = self.position_advice_table.item(row_index, column)
                row_values.append(item.text() if item else "")
            if stock_id in row_values:
                return self._select_table_row_if_needed(self.position_advice_table, row_index)
        return False

    def _select_order_intent_row_for_symbol(self, symbol: str) -> bool:
        if not symbol or not hasattr(self, "orders_table"):
            return False
        intents = list(getattr(self, "order_intents", []) or [])
        for row_index, item in enumerate(intents):
            if getattr(item, "symbol", "") == symbol:
                return self._select_table_row_if_needed(self.orders_table, row_index)
        return False

    def _select_execution_row_for_symbol(self, symbol: str) -> bool:
        if not symbol or not hasattr(self, "execution_table"):
            return False
        records = list(getattr(self, "order_submission_records", []) or [])
        target_row = -1
        for row_index, item in enumerate(records):
            if str(item.get("symbol", "") or "") == symbol:
                target_row = row_index
        if target_row < 0:
            return False
        return self._select_table_row_if_needed(self.execution_table, target_row)

    def _focus_symbol_in_recommend_workspace(self, symbol: str) -> None:
        if not symbol:
            return
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if row.symbol == symbol), None)
        stock_id = getattr(recommendation, "stock_id", "") or self._stock_id_for_symbol(symbol)
        self._navigate_to_workspace("recommend", "daily_pool_table")
        if stock_id:
            selected = self._select_daily_pool_row_by_stock_id(stock_id)
            self._select_trade_plan_row_by_stock_id(stock_id)
            self._select_position_advice_row_by_stock_id(stock_id)
            if selected is not None:
                self._refresh_recommendation_focus_panels(selected)
                self._refresh_strategy_focus_detail()
        if hasattr(self, "daily_pool_focus_label"):
                self._set_label_text_if_changed(
                    self.daily_pool_focus_label,
                    f"推荐焦点：{self._stock_name_for_symbol(symbol)} ({stock_id or '--'} / {symbol}) | 已同步到机会池、交易计划和持仓处理建议",
                )

    def _focus_symbol_in_broker_workspace(self, symbol: str) -> None:
        if not symbol:
            return
        self._queue_symbol_to_watchlist(symbol)
        self._navigate_to_workspace("broker", "orders_table")
        has_scan_rows = bool(getattr(self, "scan_rows", []))
        if has_scan_rows:
            self.generate_order_suggestions()
            self._select_order_intent_row_for_symbol(symbol)
            self._select_execution_row_for_symbol(symbol)
        else:
            if hasattr(self, "broker_status_banner"):
                self._set_label_text_if_changed(
                    self.broker_status_banner,
                    f"交易状态：已切到交易执行页，但 {self._stock_name_for_symbol(symbol)} 还缺少扫描结果，请先刷新股票池。",
                )
            if hasattr(self, "orders_focus_label"):
                self._set_label_text_if_changed(
                    self.orders_focus_label,
                    f"委托焦点：{self._stock_name_for_symbol(symbol)} 已加入观察池，等待扫描后生成委托建议",
                )
        self._refresh_broker_order_focus()
        self._refresh_submission_focus()
        if has_scan_rows and hasattr(self, "orders_focus_label"):
                self._set_label_text_if_changed(
                    self.orders_focus_label,
                    f"委托焦点：{self._stock_name_for_symbol(symbol)} 已同步到委托建议与提交记录",
                )
        elif not has_scan_rows and hasattr(self, "orders_focus_label"):
                self._set_label_text_if_changed(
                    self.orders_focus_label,
                    f"委托焦点：{self._stock_name_for_symbol(symbol)} 已加入观察池，等待扫描后生成委托建议",
                )

    def _refresh_workspace_status_labels(self) -> None:
        if hasattr(self, "top_badge"):
            current_name = self._workspace_name_for_index(self.tabs.currentIndex()) if hasattr(self, "tabs") else "龙头主控台"
            self._set_label_text_if_changed(self.top_badge, self._workspace_badge_text(current_name))
        self._normalize_action_row_texts()
        self._refresh_shell_header()
        self._refresh_live_workspace_summary_panels()
        self._refresh_workspace_focus_banners()
        self._refresh_submission_focus()
        self._refresh_scanner_focus_status()
        self._refresh_monitor_summary()

        if hasattr(self, "broker_status_banner"):
            pending_orders = len(getattr(self, "order_intents", []) or [])
            submitted_orders = len(getattr(self, "order_submission_records", []) or [])
            summary = getattr(self, "last_broker_execution_summary", {}) or {}
            blockers = list(summary.get("blockers", []) or [])
            warnings = list(summary.get("warnings", []) or [])
            if blockers:
                banner_text = f"交易台：阻塞中 | 待审 {pending_orders} | 已报 {submitted_orders}"
            elif warnings and pending_orders:
                banner_text = f"交易台：待复核 | 待审 {pending_orders} | 风险灯黄"
            elif pending_orders:
                banner_text = f"交易台：可送审 | 待审 {pending_orders} | 优先高等级"
            elif submitted_orders:
                banner_text = f"交易台：已报单 {submitted_orders} | 跟踪成交回执"
            else:
                banner_text = "交易台：等待委托链路生成 | 先看主线与风险灯"
            self._set_label_text_if_changed(self.broker_status_banner, banner_text, tooltip=banner_text)

        if hasattr(self, "orders_focus_label") and not getattr(self, "order_intents", []):
            self._set_label_text_if_changed(self.orders_focus_label, ORDERS_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "trade_plan_focus_label") and not getattr(getattr(self, "current_trade_plan", None), "decisions", []):
            self._set_label_text_if_changed(self.trade_plan_focus_label, TRADE_PLAN_DEFAULT_FOCUS_TEXT)
        if hasattr(self, "daily_pool_focus_label") and not getattr(self, "daily_pool_rows", []):
            self._set_label_text_if_changed(self.daily_pool_focus_label, RECOMMEND_DEFAULT_FOCUS_TEXT)

    def open_broker_focus_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
            self._focus_symbol_everywhere(symbol, origin="broker")
        else:
            self._navigate_to_workspace("recommend", "trade_plan_table", "trade_plan_table")
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：已从交易页回到推荐页，请优先核对当前执行标的。")

    def open_runtime_to_overview(self) -> None:
        self._navigate_to_workspace("overview", "market_pool_table")
        if hasattr(self, "market_status_label"):
            self._set_label_text_if_changed(self.market_status_label, "总览状态：已从运行日志回到市场总览，建议先看主线与焦点池。")

    def open_detail_to_overview(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_everywhere(symbol, origin="detail")
        self._navigate_to_workspace("overview", "market_pool_table")
        if hasattr(self, "market_status_label"):
            self._set_label_text_if_changed(self.market_status_label, "总览状态：已从复盘页回到总览，并同步当前焦点股票。")

    def open_detail_to_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
            self._focus_symbol_everywhere(symbol, origin="detail")
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：已从复盘页切到推荐页，请核对当前焦点票的执行机会。")

    def open_detail_to_scanner(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_everywhere(symbol, origin="detail")
        self._navigate_to_workspace("scanner", "scan_table", "scan_table")
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：已从复盘页切到扫描页，请继续查看当前焦点票的盘中联动。")

    def load_universe_folder(self) -> None:
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：正在刷新市场与股票池，请稍候...")
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：正在同步市场数据，稍后自动重算候选池。")
        self.refresh_remote_market(update_chart=True)

    def load_sample_universe(self) -> None:
        if hasattr(self, "recommend_empty_meta"):
            self._set_label_text_if_changed(self.recommend_empty_meta, "正在载入样例并刷新市场数据，完成后会自动生成综合机会池。")
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：正在载入示例并准备联动页面。")
        self.refresh_remote_market(update_chart=True)

    def rescan_universe(self) -> None:
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：正在重新扫描市场、观察池与盘中监控。")
        if hasattr(self, "last_refresh_label"):
            self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：正在执行重新扫描")
        self.refresh_remote_market(update_chart=True)

    def generate_order_suggestions(self) -> None:
        if not self.scan_rows:
            QMessageBox.information(self, "提示", "请先完成股票池扫描。")
            return
        try:
            per_trade_budget = float(self.per_trade_budget_input.text().strip())
        except ValueError:
            QMessageBox.critical(self, "参数错误", "单笔预算必须填写数字。")
            return
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(
                self.broker_status_banner,
                "交易状态：正在生成委托建议，请等待风险测算和执行检查完成。",
            )
        rows = self.scan_rows if not self.state.watchlist else [row for row in self.scan_rows if row.symbol in self.state.watchlist]
        self.order_intents = EastmoneyBrokerAdapter().build_order_intents(rows, per_trade_budget)
        self._fill_orders()
        self._refresh_broker_order_focus()
        self._refresh_submission_focus()
        if self.order_intents:
            if hasattr(self, "orders_focus_label"):
                top_intent = self.order_intents[0]
                self._set_label_text_if_changed(
                    self.orders_focus_label,
                    f"委托焦点：已生成 {len(self.order_intents)} 笔委托建议，优先关注 {self._stock_name_for_symbol(top_intent.symbol)}",
                )
            self._refresh_broker_status(extra=f"已生成 {len(self.order_intents)} 笔委托建议，等待确认提交。")
        else:
            self._refresh_broker_status(extra="当前参数下暂无新的买入建议。")

    def confirm_and_submit_orders(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        profile = self.current_broker_profile()
        adapter = EastmoneyBrokerAdapter()
        if not OrderConfirmationDialog.confirm(profile, self.order_intents, adapter, self):
            self._refresh_broker_status(extra="本次提交已取消，仍保留委托建议供你继续复核。")
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
            self._refresh_submission_focus()
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
        self._refresh_submission_focus()
        QMessageBox.information(self, "下单完成", "\n".join(results))

    def trigger_trade_plan_refresh(self) -> None:
        if hasattr(self, "trade_plan_focus_label"):
            self._set_label_text_if_changed(self.trade_plan_focus_label, "计划焦点：正在重算今日交易计划")
        self._refresh_trade_plan()

    def show_core_execution_bucket(self) -> None:
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：已切换到高优先池视角，优先看最强执行候选。")
        self._navigate_to_workspace("recommend", "trade_plan_table")

    def show_watch_bucket(self) -> None:
        self._navigate_to_workspace("scanner", "watchlist_widget")
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, "扫描状态：已定位到观察池，适合继续跟踪等待确认的标的。")

    def show_risk_bucket(self) -> None:
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：已切换到风险池，优先检查减仓、防守与退出建议。")
        self._navigate_to_workspace("recommend", "position_advice_table")

    def open_trade_plan_watch_bucket(self) -> None:
        if hasattr(self, "trade_plan_focus_label"):
            self._set_label_text_if_changed(self.trade_plan_focus_label, "计划焦点：已跳转到观察池，继续筛选需要跟踪的标的。")
        self._navigate_to_workspace("scanner", "watchlist_widget")

    def open_trade_plan_broker_workspace(self) -> None:
        self._navigate_to_workspace("broker", "orders_table")
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, "交易状态：已跳转到交易执行页，请先复核委托建议再提交。")

    def focus_first_broker_blocker(self) -> None:
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, "交易状态：已定位到阻塞信息，优先处理风控或环境问题。")
        self._navigate_to_workspace("broker", "broker_status_text")

    def focus_priority_broker_order(self) -> None:
        self._navigate_to_workspace("broker", "orders_table", "orders_table")
        self._refresh_broker_order_focus()
        if hasattr(self, "orders_focus_label"):
            self._set_label_text_if_changed(self.orders_focus_label, "委托动作面板 / 委托焦点：已定位到优先委托，请先核对动作与仓位。")

    def open_overview_theme_to_recommend(self) -> None:
        symbol = self.active_symbol or ""
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, "推荐状态：已从总览切到推荐页，正在同步当前焦点票。")
        if symbol:
            self._focus_symbol_in_recommend_workspace(symbol)
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")

    def open_overview_decision_to_broker(self) -> None:
        symbol = self.active_symbol or ""
        if symbol:
            self._focus_symbol_in_broker_workspace(symbol)
        else:
            self._navigate_to_workspace("broker", "orders_table")
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, "交易状态：已从总览切到交易执行页，请优先检查当前焦点票。")

    def _refresh_live_workspace_summary_panels(self) -> None:
        if hasattr(self, "scanner_live_summary_headline"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            monitor_count = self.monitor_table.rowCount() if hasattr(self, "monitor_table") else 0
            auto_refresh = "开启" if hasattr(self, "auto_refresh_checkbox") and self.auto_refresh_checkbox.isChecked() else "关闭"
            self._set_label_text_if_changed(self.scanner_live_summary_headline, f"扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}")
            self._set_label_text_if_changed(self.scanner_live_summary_detail, f"盘中自动刷新：{auto_refresh} | {getattr(self, 'last_refresh_label', QLabel('--')).text()}")
            self._set_label_text_if_changed(self.scanner_live_summary_meta, f"{getattr(self, 'universe_label', QLabel('股票池目录：未加载')).text()}")

        if hasattr(self, "board_live_summary_headline"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            auto_export = "开启" if hasattr(self, "auto_review_export_checkbox") and self.auto_review_export_checkbox.isChecked() else "关闭"
            self._set_label_text_if_changed(self.board_live_summary_headline, f"候选 {candidate_count} / 监控 {monitor_count}")
            self._set_label_text_if_changed(self.board_live_summary_detail, f"收盘导出：{auto_export} | 焦点联动：扫描 / 推荐 / 复盘")
            self._set_label_text_if_changed(self.board_live_summary_meta, getattr(self, "board_focus_label", QLabel("等待焦点同步")).text() if hasattr(self, "board_focus_label") else "等待焦点同步")

        if hasattr(self, "detail_live_summary_headline"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            active_symbol = getattr(self, "active_symbol", "") or "未选中"
            self._set_label_text_if_changed(self.detail_live_summary_headline, f"当前标的：{active_symbol}")
            self._set_label_text_if_changed(self.detail_live_summary_detail, f"近期信号 {signal_count} 条 | 交易记录 {trade_count} 条")
            self._set_label_text_if_changed(self.detail_live_summary_meta, getattr(self, "active_symbol_label", QLabel("当前标的：未选择")).text())

        if hasattr(self, "config_live_summary_headline"):
            plan_text = self.state.license_plan or "TRIAL"
            top_theme_limit, max_total_exposure, _ = self._current_strategy_runtime_config()
            template_text = self.daily_plan_template_combo.currentText() if hasattr(self, "daily_plan_template_combo") else "--"
            focus_theme_text = self.focus_themes_input.text().strip() if hasattr(self, "focus_themes_input") else ""
            self._set_label_text_if_changed(self.config_live_summary_headline, f"方案：{plan_text} | 主线前排 {top_theme_limit}")
            self._set_label_text_if_changed(self.config_live_summary_detail, f"总仓位上限：{max_total_exposure:.2f} | 模板：{template_text}")
            self._set_label_text_if_changed(self.config_live_summary_meta, f"关注题材：{focus_theme_text or '未设置'}")

    def _refresh_workspace_focus_banners(self) -> None:
        target_symbol = self.active_symbol or self._selected_symbol_from_watchlist() or self._selected_board_symbol() or ""
        stock_name = self._stock_name_for_symbol(target_symbol) if target_symbol else "等待联动"
        stock_id = self._stock_id_for_symbol(target_symbol) if target_symbol else "--"
        recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target_symbol), None) if target_symbol else None
        tone = self._focus_banner_tone(symbol=target_symbol, recommendation=recommendation, scan_row=scan_row)

        if hasattr(self, "overview_focus_banner"):
            market_count = self.market_pool_table.rowCount() if hasattr(self, "market_pool_table") else 0
            text = (
                f"总览焦点：{stock_name} ({stock_id} / {target_symbol}) | 龙头池 {market_count} | 与推荐页联动"
                if target_symbol
                else "总览焦点：等待从龙头池、推荐池或扫描页联动一只股票"
            )
            self._set_focus_banner_state(self.overview_focus_banner, tone if target_symbol else "idle", text)

        if hasattr(self, "recommend_focus_banner"):
            pool_count = self.daily_pool_table.rowCount() if hasattr(self, "daily_pool_table") else 0
            strategy_name = getattr(recommendation, "primary_strategy", "") if recommendation is not None else ""
            text = (
                f"推荐焦点：{stock_name} ({stock_id} / {target_symbol}) | 推荐池 {pool_count} | 策略 {strategy_name or '等待策略同步'}"
                if target_symbol
                else "推荐焦点：等待从推荐池、龙头榜或交易计划联动一只股票"
            )
            self._set_focus_banner_state(self.recommend_focus_banner, tone if target_symbol else "idle", text)

        if hasattr(self, "scanner_focus_banner"):
            scan_count = self.scan_table.rowCount() if hasattr(self, "scan_table") else 0
            watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
            text = (
                f"扫描焦点：{stock_name} ({stock_id} / {target_symbol}) | 扫描 {scan_count} | 观察 {watch_count}"
                if target_symbol
                else "扫描焦点：等待从扫描榜、观察池或盘中监控联动标的"
            )
            self._set_focus_banner_state(self.scanner_focus_banner, tone if target_symbol else "idle", text)

        if hasattr(self, "board_focus_banner"):
            candidate_count = self.board_table.rowCount() if hasattr(self, "board_table") else 0
            monitor_count = self.board_monitor_table.rowCount() if hasattr(self, "board_monitor_table") else 0
            text = (
                f"打板焦点：{stock_name} ({stock_id} / {target_symbol}) | 候选 {candidate_count} | 监控 {monitor_count}"
                if target_symbol
                else "打板焦点：等待扫描页或推荐页同步强势候选"
            )
            self._set_focus_banner_state(self.board_focus_banner, tone if target_symbol else "idle", text)

        if hasattr(self, "detail_focus_banner"):
            signal_count = self.signal_table.rowCount() if hasattr(self, "signal_table") else 0
            trade_count = self.trades_table.rowCount() if hasattr(self, "trades_table") else 0
            text = (
                f"复盘焦点：{stock_name} ({stock_id} / {target_symbol}) | 信号 {signal_count} | 成交 {trade_count}"
                if target_symbol
                else "复盘焦点：等待扫描、推荐或打板页面同步单票标的"
            )
            self._set_focus_banner_state(self.detail_focus_banner, tone if target_symbol else "idle", text)

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

_ORIGINAL_POST_BUILD_UI_TWEAKS = QuantHunterWindow._post_build_ui_tweaks


def _install_runtime_cjk_font(app: QApplication | None) -> str:
    if app is None:
        return ""
    families = {family.lower(): family for family in QFontDatabase.families()}
    preferred_fonts = [
        "Microsoft YaHei UI",
        "Microsoft YaHei",
        "PingFang SC",
        "Source Han Sans SC",
        "Noto Sans CJK SC",
        "WenQuanYi Micro Hei",
        "SimHei",
    ]
    for family in preferred_fonts:
        resolved = families.get(family.lower())
        if resolved:
            font = QFont(resolved, 10)
            font.setStyleStrategy(QFont.PreferAntialias)
            app.setFont(font)
            return resolved
    return ""


def _qh_apply_runtime_font_preferences(self: QuantHunterWindow) -> None:
    app = QApplication.instance()
    family = _install_runtime_cjk_font(app)
    if family:
        self.setFont(QFont(family, 10))
    self.setWindowTitle("量化猎手")
    QApplication.setApplicationName("量化猎手")


def _qh_polish_visual_surfaces(self: QuantHunterWindow) -> None:
    for attr_name in (
        "overview_focus_banner",
        "recommend_focus_banner",
        "scanner_focus_banner",
        "board_focus_banner",
        "detail_focus_banner",
        "broker_status_banner",
    ):
        label = getattr(self, attr_name, None)
        if isinstance(label, QLabel):
            label.setMinimumHeight(max(label.minimumHeight(), 48))
            label.setWordWrap(True)

    for attr_name in (
        "scanner_live_summary_headline",
        "board_live_summary_headline",
        "detail_live_summary_headline",
        "config_live_summary_headline",
    ):
        label = getattr(self, attr_name, None)
        if isinstance(label, QLabel):
            font = label.font()
            font.setBold(True)
            font.setPointSize(max(font.pointSize(), 11))
            label.setFont(font)

    for frame_name in (
        "scannerLiveSummaryPanel",
        "boardLiveSummaryPanel",
        "detailLiveSummaryPanel",
        "configLiveSummaryPanel",
    ):
        panel = self.findChild(QFrame, frame_name)
        if isinstance(panel, QFrame):
            panel.setMinimumHeight(max(panel.minimumHeight(), 94))

    for table_name, min_height in (
        ("orders_table", 360),
        ("execution_table", 320),
        ("daily_pool_table", 440),
        ("scan_table", 320),
        ("board_table", 300),
    ):
        table = getattr(self, table_name, None)
        if isinstance(table, QTableWidget):
            table.setMinimumHeight(max(table.minimumHeight(), min_height))

    for text_name, min_height in (
        ("broker_status_text", 220),
        ("login_status_text", 260),
    ):
        widget = getattr(self, text_name, None)
        if isinstance(widget, QTextEdit):
            widget.setMinimumHeight(max(widget.minimumHeight(), min_height))

    tab_bar = self.tabs.tabBar() if hasattr(self, "tabs") else None
    if tab_bar is not None:
        tab_bar.setUsesScrollButtons(False)
        tab_bar.setElideMode(Qt.ElideNone)
        tab_bar.setExpanding(False)
        tab_bar.setDocumentMode(True)

    self.setStyleSheet(
        self.styleSheet()
        + """
QWidget {
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", "Source Han Sans SC", "Noto Sans CJK SC", sans-serif;
}
QTabWidget::pane {
    border: 1px solid rgba(113, 143, 171, 0.16);
    border-radius: 18px;
    top: -1px;
    background: rgba(255, 255, 255, 0.66);
}
QTabBar::tab {
    min-width: 120px;
    min-height: 42px;
    padding: 9px 18px;
    margin-right: 8px;
    border-radius: 14px;
    font-weight: 700;
}
QLabel#inlineHint {
    padding: 8px 12px;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.58);
    color: #36516b;
}
QLabel[focusBanner="true"] {
    min-height: 48px;
    padding: 12px 16px;
    border-radius: 15px;
    font-weight: 700;
}
QFrame[actionRow="true"] {
    padding: 6px;
}
QFrame#scannerLiveSummaryPanel,
QFrame#boardLiveSummaryPanel,
QFrame#detailLiveSummaryPanel,
QFrame#configLiveSummaryPanel {
    border-radius: 18px;
    padding: 8px;
}
QTableWidget {
    border-radius: 16px;
}
QHeaderView::section {
    padding: 10px 12px;
}
"""
    )


def _qh_upgrade_auth_workspace(self: QuantHunterWindow) -> None:
    tab = getattr(self, "auth_tab", None)
    layout = tab.layout() if isinstance(tab, QWidget) else None
    if layout is None:
        return

    if getattr(self, "auth_entry_panel", None) is None:
        panel = QFrame()
        panel.setObjectName("authEntryPanel")
        panel.setProperty("actionRow", True)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(14, 12, 14, 12)
        panel_layout.setSpacing(10)

        cards: list[tuple[str, str]] = [
            ("默认券商", "东方财富 / 可扩展"),
            ("委托模式", "人工确认优先"),
            ("安全策略", "只保存配置，不绕过券商校验"),
        ]
        for title, desc in cards:
            card = QFrame()
            card.setProperty("actionRow", True)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(12, 10, 12, 10)
            card_layout.setSpacing(4)
            title_label = QLabel(title)
            title_font = title_label.font()
            title_font.setBold(True)
            title_label.setFont(title_font)
            desc_label = QLabel(desc)
            desc_label.setWordWrap(True)
            desc_label.setObjectName("inlineHint")
            card_layout.addWidget(title_label)
            card_layout.addWidget(desc_label)
            panel_layout.addWidget(card, 1)

        layout.insertWidget(1, panel)
        self.auth_entry_panel = panel

    if getattr(self, "auth_action_row_panel", None) is None and hasattr(self, "login_status_text"):
        panel = QFrame()
        panel.setObjectName("authActionRowPanel")
        panel.setProperty("actionRow", True)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(12, 10, 12, 10)
        panel_layout.setSpacing(10)

        actions = [
            ("保存登录配置", "accent", self.save_login_profile),
            ("前往交易执行", "tonal", lambda: self._navigate_to_workspace("broker", "orders_table")),
            ("前往配置页", "ghost", lambda: self._navigate_to_workspace("config")),
        ]
        for text, role, handler in actions:
            button = QPushButton(text)
            self._set_button_role(button, role)
            button.setMinimumHeight(38)
            button.clicked.connect(handler)
            panel_layout.addWidget(button)
        panel_layout.addStretch(1)

        status_parent = self.login_status_text.parentWidget()
        status_layout = status_parent.layout() if status_parent is not None else None
        if status_layout is not None:
            status_layout.insertWidget(0, panel)
            self.auth_action_row_panel = panel


def _qh_upgrade_broker_workspace(self: QuantHunterWindow) -> None:
    splitter_specs = (
        ("broker_control_splitter", [600, 540, 330]),
        ("broker_middle_splitter", [540, 980]),
        ("broker_order_focus_splitter", [920, 340]),
    )
    for attr_name, sizes in splitter_specs:
        splitter = getattr(self, attr_name, None)
        if isinstance(splitter, QSplitter):
            self._configure_splitter(splitter, sizes)
            for index in range(min(splitter.count(), len(sizes))):
                splitter.setStretchFactor(index, max(sizes[index] // 100, 1))

    if hasattr(self, "orders_focus_label") and isinstance(self.orders_focus_label, QLabel):
        self.orders_focus_label.setMinimumHeight(max(self.orders_focus_label.minimumHeight(), 42))
        self.orders_focus_label.setWordWrap(True)
    if hasattr(self, "broker_status_banner") and isinstance(self.broker_status_banner, QLabel):
        self.broker_status_banner.setMinimumHeight(max(self.broker_status_banner.minimumHeight(), 48))
        self.broker_status_banner.setWordWrap(True)
    if hasattr(self, "broker_status_text") and isinstance(self.broker_status_text, QTextEdit):
        self.broker_status_text.setMinimumHeight(max(self.broker_status_text.minimumHeight(), 220))
    if hasattr(self, "execution_table") and isinstance(self.execution_table, QTableWidget):
        self.execution_table.verticalHeader().setDefaultSectionSize(max(self.execution_table.verticalHeader().defaultSectionSize(), 40))
    if hasattr(self, "orders_table") and isinstance(self.orders_table, QTableWidget):
        self.orders_table.verticalHeader().setDefaultSectionSize(max(self.orders_table.verticalHeader().defaultSectionSize(), 42))


def _qh_upgrade_analysis_workspaces(self: QuantHunterWindow) -> None:
    splitter_specs = (
        ("recommend_dispatch_splitter", [420, 720, 320]),
        ("broker_middle_splitter", [540, 980]),
    )
    for attr_name, sizes in splitter_specs:
        splitter = getattr(self, attr_name, None)
        if isinstance(splitter, QSplitter):
            self._configure_splitter(splitter, sizes)

    if hasattr(self, "scanner_tab"):
        splitters = [item for item in self.scanner_tab.findChildren(QSplitter) if item.count() == 3]
        for splitter in splitters:
            self._configure_splitter(splitter, [360, 620, 620])
            splitter.setStretchFactor(0, 3)
            splitter.setStretchFactor(1, 5)
            splitter.setStretchFactor(2, 5)

    if hasattr(self, "detail_tab"):
        splitters = [item for item in self.detail_tab.findChildren(QSplitter)]
        for splitter in splitters:
            if splitter.count() == 3:
                self._configure_splitter(splitter, [520, 520, 520])
            elif splitter.count() == 2:
                self._configure_splitter(splitter, [700, 900])

    for text_name, min_height in (
        ("board_text", 210),
        ("board_monitor_text", 210),
        ("metrics_text", 220),
        ("detail_decision_text", 280),
        ("detail_execution_text", 280),
        ("detail_conclusion_text", 280),
    ):
        widget = getattr(self, text_name, None)
        if isinstance(widget, QTextEdit):
            widget.setMinimumHeight(max(widget.minimumHeight(), min_height))


def _qh_rebind_workspace_action_rows(self: QuantHunterWindow) -> None:
    row_bindings = {
        "detailExecutionActionRow": {
            "前往交易执行": self.open_detail_to_broker,
            "查看扫描": self.open_detail_to_scanner,
        },
        "detailConclusionActionRow": {
            "前往交易执行": self.open_detail_to_broker,
            "查看推荐池": self.open_detail_to_recommend,
            "查看推荐": self.open_detail_to_recommend,
        },
        "brokerExecutionActionRow": {
            "查看推荐池": self.open_broker_focus_recommend,
            "查看推荐": self.open_broker_focus_recommend,
        },
    }
    for row_name, binding in row_bindings.items():
        row = self.findChild(QWidget, row_name)
        if row is None:
            continue
        for button in row.findChildren(QPushButton):
            text = (button.text() or "").strip()
            handler = binding.get(text)
            if handler is None:
                continue
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(handler)


def _qh_polish_scanner_toolbar(self: QuantHunterWindow) -> None:
    for attr_name in (
        "auto_refresh_checkbox",
        "sound_alert_checkbox",
    ):
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QCheckBox):
            widget.setMinimumHeight(max(widget.minimumHeight(), 34))

    for attr_name in (
        "refresh_interval_input",
        "market_search_input",
    ):
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QLineEdit):
            widget.setMinimumHeight(max(widget.minimumHeight(), 36))
            widget.setAlignment(Qt.AlignCenter if attr_name == "refresh_interval_input" else (Qt.AlignLeft | Qt.AlignVCenter))

    for table_name, text_name in (
        ("monitor_table", "monitor_summary_text"),
    ):
        table = getattr(self, table_name, None)
        text = getattr(self, text_name, None)
        if isinstance(text, QTextEdit):
            text.setMinimumHeight(max(text.minimumHeight(), 168))
        if isinstance(table, QTableWidget):
            table.setMinimumHeight(max(table.minimumHeight(), 260))


def _qh_tune_operational_tables(self: QuantHunterWindow) -> None:
    specs = [
        ("scan_table", {0: "wide", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "content", 8: "content", 9: "content", 10: "stretch"}),
        ("summary_table", {0: "wide", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "stretch"}),
        ("monitor_table", {0: "wide", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "content", 8: "stretch"}),
        ("board_table", {0: "wide", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "wide", 8: "content", 9: "content", 10: "content", 11: "content"}),
        ("board_monitor_table", {0: "wide", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "content", 8: "wide", 9: "stretch"}),
        ("orders_table", {0: "content", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "content", 8: "content", 9: "wide", 10: "content", 11: "stretch", 12: "content"}),
        ("execution_table", {0: "content", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "content", 7: "content", 8: "stretch"}),
        ("signal_table", {0: "content", 1: "content", 2: "content", 3: "content", 4: "stretch"}),
        ("trades_table", {0: "content", 1: "content", 2: "content", 3: "content", 4: "content", 5: "content", 6: "stretch"}),
    ]
    minimum_widths = {
        "scan_table": {0: 220, 1: 88, 2: 128, 3: 128, 4: 92, 5: 76, 6: 118, 7: 92, 8: 92, 9: 92, 10: 110},
        "summary_table": {0: 220, 1: 88, 2: 128, 3: 92, 4: 92, 5: 108, 6: 88, 7: 120},
        "monitor_table": {0: 220, 1: 88, 2: 128, 3: 128, 4: 92, 5: 76, 6: 92, 7: 118, 8: 130},
        "board_table": {0: 220, 1: 88, 2: 128, 3: 108, 4: 88, 5: 88, 6: 76, 7: 160, 8: 96, 9: 92, 10: 92, 11: 92},
        "board_monitor_table": {0: 220, 1: 88, 2: 128, 3: 118, 4: 78, 5: 88, 6: 92, 7: 96, 8: 180, 9: 220},
        "orders_table": {0: 72, 1: 128, 2: 88, 3: 88, 4: 78, 5: 108, 6: 88, 7: 88, 8: 88, 9: 148, 10: 118, 11: 220, 12: 88},
        "execution_table": {0: 138, 1: 92, 2: 92, 3: 128, 4: 88, 5: 88, 6: 78, 7: 118, 8: 220},
        "signal_table": {0: 118, 1: 92, 2: 76, 3: 92, 4: 320},
        "trades_table": {0: 118, 1: 118, 2: 86, 3: 86, 4: 78, 5: 88, 6: 220},
    }
    for attr_name, mapping in specs:
        table = getattr(self, attr_name, None)
        if not isinstance(table, QTableWidget):
            continue
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 42))
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        for index in range(table.columnCount()):
            mode = mapping.get(index, "interactive")
            if mode == "stretch":
                header.setSectionResizeMode(index, QHeaderView.Stretch)
            elif mode == "content":
                header.setSectionResizeMode(index, QHeaderView.ResizeToContents)
            elif mode == "wide":
                header.setSectionResizeMode(index, QHeaderView.Interactive)
                table.setColumnWidth(index, max(table.columnWidth(index), minimum_widths.get(attr_name, {}).get(index, 180)))
            else:
                header.setSectionResizeMode(index, QHeaderView.Interactive)
                table.setColumnWidth(index, max(table.columnWidth(index), minimum_widths.get(attr_name, {}).get(index, 92)))


def _qh_apply_identity_table_headers(self: QuantHunterWindow) -> None:
    if hasattr(self, "scan_table"):
        self.scan_table.setColumnCount(11)
        self.scan_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "信号日期", "收盘价", "入场价", "止损价", "目标价"])
        self.scan_table.setColumnHidden(1, False)
    if hasattr(self, "summary_table"):
        self.summary_table.setColumnCount(8)
        self.summary_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "交易笔数", "收益率", "最大回撤", "胜率", "期末权益"])
        self.summary_table.setColumnHidden(1, False)
    if hasattr(self, "monitor_table"):
        self.monitor_table.setColumnCount(9)
        self.monitor_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "动作 / 信号", "信号", "评分", "收盘价", "信号日期", "更新时间"])
        self.monitor_table.setColumnHidden(1, False)
    if hasattr(self, "board_table"):
        self.board_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "打板级别", "动能", "流动性", "龙头", "触发方式", "风险级别", "计划买点", "止损", "目标"])
        self.board_table.setColumnHidden(1, False)
    if hasattr(self, "board_monitor_table"):
        self.board_monitor_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "交易代码", "监控状态", "强度", "连续性", "回封概率", "炸板风险", "动作建议", "备注"])
        self.board_monitor_table.setColumnHidden(1, False)
    if hasattr(self, "leader_table"):
        self.leader_table.setHorizontalHeaderLabels(["股票标识", "股票ID", "题材", "级别", "角色", "窗口", "风险", "龙头分", "动作", "说明"])
        self.leader_table.setColumnHidden(1, False)
    if hasattr(self, "daily_pool_table"):
        self.daily_pool_table.setColumnCount(len(DAILY_POOL_TABLE_HEADERS))
        self.daily_pool_table.setHorizontalHeaderLabels(DAILY_POOL_TABLE_HEADERS)
        self.daily_pool_table.setColumnHidden(2, False)
    if hasattr(self, "market_pool_table"):
        self.market_pool_table.setHorizontalHeaderLabels(["序", "股票标识", "资金标签", "策略标签", "涨跌幅", "最新价"])


def _qh_force_identity_columns_visible(self: QuantHunterWindow) -> None:
    specs = (
        ("scan_table", 1, 88),
        ("summary_table", 1, 88),
        ("monitor_table", 1, 88),
        ("board_table", 1, 88),
        ("board_monitor_table", 1, 88),
        ("leader_table", 1, 88),
        ("daily_pool_table", 2, 88),
    )
    for attr_name, column, width in specs:
        table = getattr(self, attr_name, None)
        if not isinstance(table, QTableWidget):
            continue
        table.setColumnHidden(column, False)
        table.setColumnWidth(column, max(table.columnWidth(column), width))


def _qh_refresh_login_status(self: QuantHunterWindow) -> None:
    if not hasattr(self, "login_status_text"):
        return
    profile = self.current_broker_profile() if "account_name" in getattr(self, "broker_inputs", {}) else self.state.broker_profile
    channel_text = self.auth_channel_combo.currentText() if hasattr(self, "auth_channel_combo") else "东方财富"
    username = self.login_inputs.get("username").text().strip() if "username" in getattr(self, "login_inputs", {}) else ""
    account_id = self.login_inputs.get("account_id").text().strip() if "account_id" in getattr(self, "login_inputs", {}) else ""
    strategy_id = self.login_inputs.get("strategy_id").text().strip() if "strategy_id" in getattr(self, "login_inputs", {}) else ""
    token_ready = "已填写" if "token" in getattr(self, "login_inputs", {}) and self.login_inputs["token"].text().strip() else "未填写"
    mode_text = self._display_mode(getattr(profile, "mode", "") or "manual") if hasattr(self, "_display_mode") else (getattr(profile, "mode", "") or "manual")
    lines = [
        "登录与通道说明",
        "",
        f"- 当前通道：{channel_text}",
        f"- 登录账号：{username or '未填写'}",
        f"- 账户 ID：{account_id or '未填写'}",
        f"- 策略 ID：{strategy_id or '未填写'}",
        f"- 委托模式：{mode_text or '未配置'}",
        f"- SDK Token：{token_ready}",
        "",
        "接入原则",
        "- 这里统一维护东方财富、GM 或自定义通道的登录参数，方便后续继续扩展。",
        "- 程序只保存配置与工作流状态，不绕过券商侧登录校验和风控校验。",
        "- 真实下单仍保持人工确认优先，适合先做盘中决策、委托准备和执行复盘。",
    ]
    self._set_plain_text_if_changed(self.login_status_text, "\n".join(lines))


def _qh_prime_broker_workspace_defaults(self: QuantHunterWindow) -> None:
    if hasattr(self, "broker_order_focus_text") and not getattr(self, "order_intents", []):
        self._set_plain_text_if_changed(
            self.broker_order_focus_text,
            "当前委托详情\n\n"
            "这里会跟随选中的委托建议，展示主线闸门、风险灯、仓位变化和动作原因。\n"
            "先从推荐池或扫描页联动一只股票，再生成盘中计划，就能在这里看到更完整的执行画像。"
        )
    if hasattr(self, "order_result_text") and not getattr(self, "order_submission_log", []):
        self._set_plain_text_if_changed(
            self.order_result_text,
            "执行回放\n\n"
            "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
            "确认提交后，这里会自动滚动到最新记录。"
        )
    if hasattr(self, "broker_recap_text") and not getattr(self, "order_submission_records", []):
        self._set_plain_text_if_changed(
            self.broker_recap_text,
            "成交回顾\n\n"
            "这里用于复盘通过率、阻塞原因、成交偏差，以及主线是否仍然成立。\n"
            "有提交记录后，你可以从这里快速检查执行质量和偏差来源。"
        )
    if hasattr(self, "broker_status_text"):
        current = self.broker_status_text.toPlainText().strip()
        if not current or self._has_mojibake_text(current):
            self._set_plain_text_if_changed(
                self.broker_status_text,
                "交易闸门总览\n\n"
                "1. 先同步市场、主线和推荐池，确认今天的主攻方向。\n"
                "2. 再生成盘中委托建议，检查主线闸门、预算、仓位和风险灯。\n"
                "3. 最后进入人工确认提交，并在下方回看执行结果与成交偏差。"
            )


def _qh_refresh_broker_status(self: QuantHunterWindow, extra: str = "") -> None:
    adapter = EastmoneyBrokerAdapter()
    profile = self.current_broker_profile()
    env = adapter.diagnose_environment(profile)
    market_value = sum(getattr(item, "market_value", 0.0) for item in getattr(self, "holdings", []))
    available = getattr(getattr(self, "cash_snapshot", None), "available_cash", 0.0) or 0.0
    total_assets = getattr(getattr(self, "cash_snapshot", None), "total_assets", 0.0) or (market_value + available)
    connected = (env.get("direct_ready") or env.get("bridge_ready")) and profile.mode == "sdk"

    note_lines = [
        "环境诊断",
        f"- 主程序 Python：{env.get('python_version', '--')}",
        f"- 当前解释器 SDK：{'已安装' if env.get('module_installed') else '未安装'} ({env.get('sdk_module', '--')})",
    ]
    if env.get("bridge_python"):
        note_lines.append(
            f"- 桥接解释器：{env.get('bridge_python')} | SDK {'已安装' if env.get('bridge_module_installed') else '未安装'}"
        )
    if env.get("bridge_ready"):
        note_lines.append("- 当前环境可通过桥接解释器完成 SDK 调用。")
    elif env.get("direct_ready"):
        note_lines.append("- 当前环境已满足直接 SDK 调用条件。")
    else:
        note_lines.append("- 当前环境暂未满足 SDK 下单条件，建议继续使用导出 CSV 或 GM 脚本。")

    content = [
        f"网关：{self.auth_channel_combo.currentText() if hasattr(self, 'auth_channel_combo') else '东方财富'} / 掘金 GM",
        f"模式：{self._display_mode(profile.mode)}",
        f"连接状态：{'已就绪' if connected else '未就绪'}",
        "",
        "\n".join(note_lines),
        "",
        "账户概览",
        f"- 持仓证券数：{len(getattr(self, 'holdings', []))}",
        f"- 持仓市值：{market_value:,.2f}",
        f"- 可用资金：{available:,.2f}",
        f"- 总资产：{total_assets:,.2f}",
        "",
        f"委托建议数：{len(getattr(self, 'order_intents', []))}",
    ]
    if getattr(self, "daily_pool_rows", None):
        content.append(f"市场候选：{len(self.daily_pool_rows)} 只")
    if extra and extra not in content:
        content.extend(["", extra])

    if hasattr(self, "broker_status_text"):
        self._set_plain_text_if_changed(self.broker_status_text, "\n".join(content))

    if hasattr(self, "broker_metric_labels"):
        readiness = "已就绪" if connected else ("桥接可用" if env.get("bridge_ready") else "待配置")
        risk_count = sum(1 for item in getattr(self, "order_intents", []) if getattr(item, "side", "") in {"SELL", "REDUCE"})
        buy_count = sum(1 for item in getattr(self, "order_intents", []) if getattr(item, "side", "") == "BUY")
        buy_budget = sum(
            float(getattr(item, "price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0)
            for item in getattr(self, "order_intents", [])
            if getattr(item, "side", "") == "BUY"
        )
        exposure = (buy_budget / available) if available > 0 else 0.0
        self._set_label_text_if_changed(self.broker_metric_labels["readiness"], readiness)
        self._set_label_text_if_changed(
            self.broker_metric_accents["readiness"],
            "SDK 可下单" if connected else ("可桥接调用" if env.get("bridge_ready") else "建议先导出/桥接"),
        )
        self._set_label_text_if_changed(self.broker_metric_labels["capital"], f"{available:,.0f}")
        self._set_label_text_if_changed(self.broker_metric_accents["capital"], f"持仓市值 {market_value:,.0f}")
        self._set_label_text_if_changed(self.broker_metric_labels["risk_reward"], f"{buy_count} / {risk_count}")
        self._set_label_text_if_changed(self.broker_metric_accents["risk_reward"], "买入候选 / 卖减建议")
        self._set_label_text_if_changed(self.broker_metric_labels["risk_budget"], f"{exposure:.0%}" if buy_budget > 0 else "0%")
        self._set_label_text_if_changed(self.broker_metric_accents["risk_budget"], "预计买入力度")


def _qh_refresh_submission_focus(self: QuantHunterWindow) -> None:
    record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    if hasattr(self, "order_result_text"):
        if record is None:
            if intent is not None:
                symbol = getattr(intent, "symbol", "") or ""
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "\n".join(
                        [
                            "提交前预演",
                            "",
                            f"股票：{self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)} / {symbol})",
                            f"动作：{self._display_action(getattr(intent, 'side', ''))}",
                            f"价格：{float(getattr(intent, 'price', 0.0) or 0.0):.2f} | 数量：{int(getattr(intent, 'quantity', 0) or 0)}",
                            f"止损：{float(getattr(intent, 'stop_price', 0.0) or 0.0):.2f} | 目标：{float(getattr(intent, 'target_price', 0.0) or 0.0):.2f}",
                            "当前还没有正式提交记录，确认委托后这里会自动切换到真实执行回放。",
                        ]
                    ),
                )
            else:
                self._set_plain_text_if_changed(
                    self.order_result_text,
                    "执行回放\n\n"
                    "新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态、失败原因和系统反馈。\n"
                    "刷新委托或提交模拟单后，这里会自动切到最新一条。\n"
                    "你也可以先从推荐页或打板页发送候选，再回到这里查看执行反馈。"
                )
        else:
            symbol = str(record.get("symbol", "") or "")
            lines = [
                "执行回放",
                "",
                f"时间：{record.get('timestamp', '--')}",
                f"股票：{self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)} / {symbol or '--'})",
                f"动作：{self._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
                f"订单状态：{self._display_order_status(record.get('order_status', ''))}",
                f"成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                f"失败原因：{record.get('failure_reason', '') or '无'}",
                f"反馈信息：{record.get('message', '') or '等待更多反馈'}",
            ]
            self._set_plain_text_if_changed(self.order_result_text, "\n".join(lines))

    if hasattr(self, "broker_recap_text"):
        if record is None:
            if intent is not None:
                symbol = getattr(intent, "symbol", "") or ""
                recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
                lines = [
                    f"成交预演：{self._stock_name_for_symbol(symbol)}",
                    f"预期动作：{self._display_action(getattr(intent, 'side', ''))} | 价格 {float(getattr(intent, 'price', 0.0) or 0.0):.2f} | 数量 {int(getattr(intent, 'quantity', 0) or 0)}",
                    f"预期风控：止损 {float(getattr(intent, 'stop_price', 0.0) or 0.0):.2f} | 目标 {float(getattr(intent, 'target_price', 0.0) or 0.0):.2f}",
                ]
                if recommendation is not None:
                    lines.append(
                        f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
                    )
                    lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
                lines.append("下一步：核对主线、仓位和止损后，再进入一键确认提交。")
                self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))
            else:
                self._set_plain_text_if_changed(
                    self.broker_recap_text,
                    "成交回顾\n\n"
                    "这里用于复盘通过率、阻塞原因、成交偏差，以及主线是否仍然成立。\n"
                    "产生提交记录后，可以从这里快速检查执行质量。"
                )
        else:
            symbol = str(record.get("symbol", "") or "")
            recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
            lines = [
                f"成交回顾：{self._stock_name_for_symbol(symbol)}",
                f"订单状态：{self._display_order_status(record.get('order_status', ''))} | 成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
            ]
            if recommendation is not None:
                lines.append(
                    f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
                )
                lines.append(f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))}")
                lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
            if record.get("message", ""):
                lines.append(f"系统反馈：{record.get('message', '')}")
            if record.get("failure_reason", ""):
                lines.append(f"需要处理：{record.get('failure_reason', '')}")
            else:
                lines.append("后续动作：可继续检查委托细节，或返回推荐页核对主线和仓位。")
            self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))
    self._refresh_broker_auxiliary_panels()


def _qh_on_orders_selection_changed(self: QuantHunterWindow) -> None:
    self._refresh_broker_order_focus()
    intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    if intent is None:
        self._refresh_submission_focus()
        return
    symbol = getattr(intent, "symbol", "") or ""
    if symbol:
        self.active_symbol = symbol
        self._select_execution_row_for_symbol(symbol)
        self._refresh_detail_workspace_panels()
        self._refresh_workspace_focus_banners()
    self._refresh_submission_focus()


def _qh_on_execution_selection_changed(self: QuantHunterWindow) -> None:
    record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    if record is not None:
        symbol = str(record.get("symbol", "") or "")
        if symbol:
            self.active_symbol = symbol
            self._select_order_intent_row_for_symbol(symbol)
            self._refresh_broker_order_focus()
            self._refresh_detail_workspace_panels()
            self._refresh_workspace_focus_banners()
    self._refresh_submission_focus()


def _qh_refresh_broker_auxiliary_panels(self: QuantHunterWindow) -> None:
    intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    summary = getattr(self, "last_broker_execution_summary", {}) or {}
    blockers = list(summary.get("blockers", []) or [])
    warnings = list(summary.get("warnings", []) or [])

    if hasattr(self, "broker_mainline_review_text"):
        if intent is None:
            self._set_plain_text_if_changed(
                self.broker_mainline_review_text,
                "主线闸门 / 为什么\n\n"
                "这里会汇总当前委托的主线状态、硬阻塞项和优先级说明。\n"
                "先从推荐池或扫描页联动一只股票，再生成盘中计划。"
            )
        else:
            symbol = getattr(intent, "symbol", "") or ""
            recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
            lines = [
                f"主线闸门审查：{self._stock_name_for_symbol(symbol)}",
                f"委托动作：{self._display_action(getattr(intent, 'side', ''))} | 数量 {int(getattr(intent, 'quantity', 0) or 0)} | 价格 {float(getattr(intent, 'price', 0.0) or 0.0):.2f}",
                f"主线状态：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                f"主线角色：{getattr(recommendation, 'mainline_role', '') or '待确认'} | 题材：{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
            ]
            if blockers:
                lines.append("硬阻塞：")
                lines.extend(f"- {item}" for item in blockers[:3])
            elif warnings:
                lines.append("关注项：")
                lines.extend(f"- {item}" for item in warnings[:3])
            else:
                lines.append("结论：当前没有发现明显硬阻塞，可以继续复核后送审。")
            self._set_plain_text_if_changed(self.broker_mainline_review_text, "\n".join(lines))

    if hasattr(self, "broker_execution_text"):
        if record is not None:
            symbol = str(record.get("symbol", "") or "")
            self._set_plain_text_if_changed(
                self.broker_execution_text,
                "\n".join(
                    [
                        f"执行链路：{self._stock_name_for_symbol(symbol)}",
                        f"时间：{record.get('timestamp', '--')}",
                        f"订单状态：{self._display_order_status(record.get('order_status', ''))} | 成交状态：{self._display_fill_status(record.get('fill_status', ''))}",
                        f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
                        f"反馈：{record.get('message', '') or '等待更多反馈'}",
                        f"下一步：{'先处理失败原因' if record.get('failure_reason', '') else '继续观察成交与偏差'}",
                    ]
                ),
            )
        elif intent is not None:
            symbol = getattr(intent, "symbol", "") or ""
            self._set_plain_text_if_changed(
                self.broker_execution_text,
                "\n".join(
                    [
                        f"执行链路：{self._stock_name_for_symbol(symbol)}",
                        f"预备动作：{self._display_action(getattr(intent, 'side', ''))} | 价格 {float(getattr(intent, 'price', 0.0) or 0.0):.2f} | 数量 {int(getattr(intent, 'quantity', 0) or 0)}",
                        f"预计占用：{float(getattr(intent, 'price', 0.0) or 0.0) * int(getattr(intent, 'quantity', 0) or 0):,.0f}",
                        f"止损 / 目标：{float(getattr(intent, 'stop_price', 0.0) or 0.0):.2f} / {float(getattr(intent, 'target_price', 0.0) or 0.0):.2f}",
                        "下一步：进入一键确认前，先核对主线、仓位和止损。 ",
                    ],
                ),
            )
        else:
            self._set_plain_text_if_changed(
                self.broker_execution_text,
                "最近执行\n\n"
                "生成盘中计划后，这里会汇总当前委托、提交结果和下一步动作。\n"
                "提交成功后，这里会自动切换成真实执行回放。"
            )


def _qh_refresh_detail_workspace_panels(self: QuantHunterWindow) -> None:
    if not hasattr(self, "metrics_text"):
        return
    symbol = getattr(self, "active_symbol", "") or ""
    if not symbol:
        return

    stock_name = self._stock_name_for_symbol(symbol)
    stock_id = self._stock_id_for_symbol(symbol)
    recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == symbol), None)
    scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == symbol), None)
    latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if getattr(item, "label", "") != "NONE"), None)
    selected_signal = self._selected_detail_signal_snapshot() if hasattr(self, "_selected_detail_signal_snapshot") else None
    selected_trade = self._selected_detail_trade_snapshot() if hasattr(self, "_selected_detail_trade_snapshot") else None
    order_intent = next((item for item in getattr(self, "order_intents", []) if getattr(item, "symbol", "") == symbol), None)
    execution_row = next((item for item in reversed(getattr(self, "order_submission_records", [])) if str(item.get("symbol", "")) == symbol), None)

    if hasattr(self, "detail_decision_text"):
        lines = [f"单票决策：{stock_name} ({stock_id} / {symbol})"]
        if recommendation is not None:
            theme_name = self._theme_for_symbol(symbol, recommendation=recommendation)
            hype_logic = self._hype_logic_for_symbol(symbol, recommendation=recommendation, scan_row=scan_row)
            lines.extend(
                [
                    f"主线：{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | 动作：{self._display_action(getattr(recommendation, 'action', 'WATCH'))}",
                    f"主策略：{getattr(recommendation, 'primary_strategy', '') or '擒龙决策'} | 分层：{getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
                    f"买点：{(getattr(recommendation, 'entry_price', 0.0) or getattr(recommendation, 'close', 0.0)):.2f} | 止损：{(getattr(recommendation, 'stop_price', 0.0) or (getattr(recommendation, 'close', 0.0) * 0.95)):.2f} | 目标：{(getattr(recommendation, 'target_price', 0.0) or (getattr(recommendation, 'close', 0.0) * 1.08)):.2f}",
                    f"题材：{theme_name} | 炒作逻辑：{hype_logic}",
                ]
            )
            news_lines = self._news_digest_lines_for_symbol(symbol, limit=2)
            if news_lines:
                lines.extend(["消息：", *news_lines])
            else:
                lines.append("消息：暂无近期催化")
        elif latest_signal is not None:
            lines.extend(
                [
                    f"最新信号：{self._display_label(getattr(latest_signal, 'label', ''))} | 评分 {getattr(latest_signal, 'score', '--')}",
                    f"原因：{getattr(latest_signal, 'reason', '') or '待补充'}",
                ]
            )
        else:
            lines.append("当前还没有可用的决策信息。")
        if selected_signal is not None:
            lines.extend(
                [
                    "",
                    f"焦点信号：{selected_signal['date']} | {selected_signal['label']} | 评分 {selected_signal['score']}",
                    f"触发原因：{selected_signal['reason']}",
                ]
            )
        self._set_plain_text_if_changed(self.detail_decision_text, "\n".join(lines))

    if hasattr(self, "detail_execution_text"):
        lines = [f"执行联动：{stock_name}"]
        if order_intent is not None:
            lines.append(
                f"委托建议：{self._display_action(getattr(order_intent, 'side', ''))} {getattr(order_intent, 'quantity', 0)} 股 @ {float(getattr(order_intent, 'price', 0.0) or 0.0):.2f}"
            )
        if execution_row is not None:
            lines.append(
                f"最近执行：{self._display_order_status(execution_row.get('order_status', ''))} / {self._display_fill_status(execution_row.get('fill_status', ''))}"
            )
            lines.append(f"反馈：{execution_row.get('message', '--')}")
        if order_intent is None and execution_row is None:
            lines.append("当前还没有委托或执行记录，可先去交易页生成委托建议。")
        if selected_trade is not None:
            lines.extend(
                [
                    "",
                    f"焦点成交：{selected_trade['entry_date']} -> {selected_trade['exit_date']}",
                    f"价格区间：{selected_trade['entry_price']} -> {selected_trade['exit_price']} | 股数 {selected_trade['shares']}",
                    f"盈亏：{selected_trade['pnl']} | 退出原因：{selected_trade['exit_reason']}",
                ]
            )
        self._set_plain_text_if_changed(self.detail_execution_text, "\n".join(lines))

    if hasattr(self, "detail_conclusion_text"):
        lines = [f"复盘结论：{stock_name}"]
        if latest_signal is not None:
            lines.append(
                f"最近信号：{getattr(latest_signal, 'date', '--')} | {self._display_label(getattr(latest_signal, 'label', ''))} | 评分 {getattr(latest_signal, 'score', '--')}"
            )
        if recommendation is not None:
            lines.append(
                f"建议动作：{self._display_action(getattr(recommendation, 'action', 'WATCH'))} | 下一步：{getattr(recommendation, 'next_focus', '') or '继续观察主线与量能'}"
            )
        if selected_signal is not None:
            lines.append(f"当前聚焦：{selected_signal['label']}，优先回看当日量价与主线强度。")
        if selected_trade is not None:
            lines.append(f"成交复盘：{selected_trade['exit_reason']}，可对照进出场纪律检查执行质量。")
        lines.append("后续动作：可继续回推荐页看同主线候选，或去交易页核对委托与提交记录。")
        self._set_plain_text_if_changed(self.detail_conclusion_text, "\n".join(lines))


def _qh_refresh_scanner_focus_status(self: QuantHunterWindow, symbol: str = "") -> None:
    if not hasattr(self, "scan_summary_label"):
        return
    target = symbol or self._selected_symbol_from_watchlist() or getattr(self, "active_symbol", "") or ""
    total_scans = len(getattr(self, "scan_rows", []))
    monitor_count = self.monitor_table.rowCount() if hasattr(self, "monitor_table") else 0
    watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0

    if not target:
        text = (
            f"扫描状态：已扫描 {total_scans} | 观察池 {watch_count} | 盘中监控 {monitor_count}"
            if total_scans
            else "扫描状态：等待首轮扫描，同步观察池与监控焦点。"
        )
        self._set_label_text_if_changed(self.scan_summary_label, text)
        self._refresh_scanner_summary_cards("")
        return

    scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    stock_name = self._stock_name_for_symbol(target)
    stock_id = self._stock_id_for_symbol(target)
    if scan_row is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | {self._display_action(getattr(scan_row, 'action', 'WATCH'))} / "
            f"{self._display_label(getattr(scan_row, 'label', 'WATCH'))} / 评分 {getattr(scan_row, 'score', '--')} | 观察池 {watch_count}"
        )
    elif recommendation is not None:
        text = (
            f"扫描状态：当前联动 {stock_name} ({stock_id}) | 推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} | "
            f"主线 {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} | 监控 {monitor_count}"
        )
    else:
        text = f"扫描状态：当前联动 {stock_name} ({stock_id}) | 已同步观察池与盘中监控。"
    self._set_label_text_if_changed(self.scan_summary_label, text)
    self._refresh_scanner_summary_cards(target)


def _qh_refresh_scanner_focus_cards(self: QuantHunterWindow, symbol: str = "") -> None:
    labels = getattr(self, "scanner_focus_metric_labels", None)
    accents = getattr(self, "scanner_focus_metric_accents", None)
    if not labels or not accents:
        return
    target = symbol or self._selected_symbol_from_watchlist() or getattr(self, "active_symbol", "") or ""
    if not target:
        self._set_label_text_if_changed(labels["symbol"], "--")
        self._set_label_text_if_changed(accents["symbol"], "等待焦点同步")
        self._set_label_text_if_changed(labels["signal"], "--")
        self._set_label_text_if_changed(accents["signal"], "等待扫描信号")
        self._set_label_text_if_changed(labels["action"], "观察")
        self._set_label_text_if_changed(accents["action"], "等待推荐联动")
        self._set_label_text_if_changed(labels["monitor"], "待联动")
        self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
        return

    scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target), None)
    recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    latest = next((item for item in reversed(list(getattr(self, "universe_analyses", {}).get(target, []))) if getattr(item, "label", "") != "NONE"), None)
    board_candidate = self._board_candidate_snapshot_for_symbol(target)

    self._set_label_text_if_changed(labels["symbol"], self._stock_name_for_symbol(target))
    self._set_label_text_if_changed(accents["symbol"], f"{self._stock_id_for_symbol(target)} / {target}")

    if scan_row is not None:
        self._set_label_text_if_changed(labels["signal"], f"{getattr(scan_row, 'score', 0):.1f}")
        self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(scan_row, "label", "WATCH")))
    elif latest is not None:
        self._set_label_text_if_changed(labels["signal"], f"{getattr(latest, 'score', 0):.1f}")
        self._set_label_text_if_changed(accents["signal"], self._display_label(getattr(latest, "label", "WATCH")))
    else:
        self._set_label_text_if_changed(labels["signal"], "--")
        self._set_label_text_if_changed(accents["signal"], "暂无信号")

    if recommendation is not None:
        self._set_label_text_if_changed(labels["action"], self._display_action(getattr(recommendation, "action", "WATCH")))
        self._set_label_text_if_changed(
            accents["action"],
            f"{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'} / {getattr(recommendation, 'opportunity_tier', '') or '待确认'}",
        )
    else:
        self._set_label_text_if_changed(labels["action"], "观察")
        self._set_label_text_if_changed(accents["action"], "等待推荐池联动")

    if board_candidate is not None:
        self._set_label_text_if_changed(labels["monitor"], board_candidate.get("trigger_style", "待联动"))
        self._set_label_text_if_changed(
            accents["monitor"],
            f"风险 {board_candidate.get('risk_level', '--')} | 分数 {board_candidate.get('board_score', '--')}",
        )
    else:
        self._set_label_text_if_changed(labels["monitor"], "待联动")
        self._set_label_text_if_changed(accents["monitor"], "等待监控链路")


def _qh_refresh_scanner_summary_cards(self: QuantHunterWindow, symbol: str = "") -> None:
    labels = getattr(self, "scanner_summary_metric_labels", None)
    accents = getattr(self, "scanner_summary_metric_accents", None)
    if not labels or not accents:
        return
    target = symbol or self._selected_symbol_from_watchlist() or getattr(self, "active_symbol", "") or ""
    scan_count = len(getattr(self, "scan_rows", []))
    watch_count = self.watchlist_widget.count() if hasattr(self, "watchlist_widget") else 0
    summary_count = len(getattr(self, "backtest_summaries", []))
    monitor_count = self.monitor_table.rowCount() if hasattr(self, "monitor_table") else 0

    self._set_label_text_if_changed(labels["scan"], str(scan_count))
    self._set_label_text_if_changed(labels["watch"], str(watch_count))
    self._set_label_text_if_changed(labels["summary"], str(summary_count))
    self._set_label_text_if_changed(labels["monitor"], str(monitor_count))

    if not target:
        self._set_label_text_if_changed(accents["scan"], "等待扫描链路")
        self._set_label_text_if_changed(accents["watch"], "等待观察池")
        self._set_label_text_if_changed(accents["summary"], "等待回测摘要")
        self._set_label_text_if_changed(accents["monitor"], "等待监控链路")
        return

    stock_name = self._stock_name_for_symbol(target)
    stock_id = self._stock_id_for_symbol(target)
    recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target), None)
    latest_summary = next((item for item in getattr(self, "backtest_summaries", []) if getattr(item, "symbol", "") == target), None)
    board_candidate = self._board_candidate_snapshot_for_symbol(target)
    board_monitor = self._board_monitor_snapshot_for_symbol(target)

    self._set_label_text_if_changed(accents["scan"], f"{stock_name} / {stock_id}")
    if recommendation is not None:
        self._set_label_text_if_changed(
            accents["watch"],
            f"推荐 {self._display_action(getattr(recommendation, 'action', 'WATCH'))} / {getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
        )
    else:
        self._set_label_text_if_changed(accents["watch"], "观察池已同步焦点")
    if latest_summary is not None:
        self._set_label_text_if_changed(accents["summary"], f"回测 {getattr(latest_summary, 'trades', 0)} 笔 / 收益 {getattr(latest_summary, 'total_return', 0.0):.2%}")
    else:
        self._set_label_text_if_changed(accents["summary"], "等待样本回填")
    if board_candidate is not None:
        self._set_label_text_if_changed(accents["monitor"], f"打板 {board_candidate.get('trigger_style', '--')} / 风险 {board_candidate.get('risk_level', '--')}")
    elif board_monitor is not None:
        self._set_label_text_if_changed(accents["monitor"], f"监控 {board_monitor.get('monitor_state', '--')} / {board_monitor.get('strength', '--')}")
    else:
        self._set_label_text_if_changed(accents["monitor"], "盘中监控联动")


def _qh_refresh_board_focus_panels(self: QuantHunterWindow, symbol: str = "") -> None:
    target_symbol = symbol or self._selected_board_symbol()
    if not target_symbol:
        if hasattr(self, "board_text"):
            self._set_plain_text_if_changed(
                self.board_text,
                "打板候选池\n\n"
                "这里会汇总强势连板、回封质量、入场价格与风险等级。\n"
                "先从扫描页或推荐页联动一只股票，打板页会自动切到对应候选。"
            )
        if hasattr(self, "board_monitor_text"):
            self._set_plain_text_if_changed(
                self.board_monitor_text,
                "炸板 / 回封监控\n\n"
                "这里会持续跟踪回封观察、炸板风险、连板高度和是否还值得继续博弈。\n"
                "扫描页和打板页会互相联动，方便你快速切换焦点。"
            )
        self._refresh_board_focus_cards("", None, None)
        return

    candidate = self._board_candidate_snapshot_for_symbol(target_symbol)
    monitor_payload = self._board_monitor_snapshot_for_symbol(target_symbol)
    scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == target_symbol), None)
    recommendation = next((row for row in getattr(self, "daily_pool_rows", []) if getattr(row, "symbol", "") == target_symbol), None)
    stock_name = self._stock_name_for_symbol(target_symbol)
    stock_id = self._stock_id_for_symbol(target_symbol)

    if hasattr(self, "board_text"):
        if candidate is not None:
            lines = [
                f"打板焦点：{candidate.get('stock_name', stock_name)} ({candidate.get('stock_id', stock_id)} / {target_symbol})",
                f"触发方式：{candidate.get('trigger_style', '--')} | 风险等级：{candidate.get('risk_level', '--')} | 打板分：{candidate.get('board_score', '--')}",
                f"计划价格：入场 {candidate.get('planned_entry', '--')} | 止损 {candidate.get('planned_stop', '--')} | 目标 {candidate.get('planned_target', '--')}",
                f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                "下一步：优先确认承接强度、板块共振和是否仍处于主线前排。",
            ]
            if recommendation is not None and getattr(recommendation, "rationale", ""):
                lines.append(f"推荐理由：{recommendation.rationale}")
        elif scan_row is not None:
            lines = [
                f"打板焦点：{stock_name} ({stock_id} / {target_symbol})",
                f"扫描联动：{self._display_action(getattr(scan_row, 'action', 'WATCH'))} | 信号 {self._display_label(getattr(scan_row, 'label', 'WATCH'))} | 评分 {getattr(scan_row, 'score', '--')}",
                f"收盘价：{getattr(scan_row, 'close', 0.0):.2f} | 信号日期：{getattr(scan_row, 'signal_date', '--')}",
                f"原因：{getattr(scan_row, 'reason', '') or '等待扫描摘要联动'}",
                "下一步：如打板池尚未生成，可先回扫描页或推荐页补齐候选。",
            ]
        else:
            lines = [
                f"打板焦点：{stock_name} ({stock_id} / {target_symbol})",
                "当前还没有满足条件的打板候选。",
                "下一步：先从扫描页或推荐页选择股票，再联动查看打板候选。",
            ]
        self._set_plain_text_if_changed(self.board_text, "\n".join(lines))

    if hasattr(self, "board_monitor_text"):
        if monitor_payload is not None:
            lines = [
                f"监控焦点：{monitor_payload.get('stock_name', stock_name)} ({monitor_payload.get('stock_id', stock_id)} / {target_symbol})",
                f"状态：{monitor_payload.get('monitor_state', '--')} | 强度：{monitor_payload.get('strength', '--')} | 连续性：{monitor_payload.get('continuity', '--')}",
                f"动作建议：{monitor_payload.get('action_plan', '--')}",
                f"备注：{monitor_payload.get('note', '--')}",
            ]
        elif scan_row is not None:
            lines = [
                f"监控焦点：{stock_name} ({stock_id} / {target_symbol})",
                f"扫描联动：{self._display_action(getattr(scan_row, 'action', 'WATCH'))} | 信号 {self._display_label(getattr(scan_row, 'label', 'WATCH'))} | 评分 {getattr(scan_row, 'score', '--')}",
                f"备注：{getattr(scan_row, 'reason', '') or '等待监控链路同步'}",
            ]
        else:
            lines = [
                f"监控焦点：{stock_name} ({stock_id} / {target_symbol})",
                "暂无可用的打板监控摘要，等待监控链路同步。",
            ]
        if recommendation is not None:
            lines.append(
                f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
            )
        self._set_plain_text_if_changed(self.board_monitor_text, "\n".join(lines))

    self._refresh_board_focus_cards(target_symbol, candidate, monitor_payload)


def _qh_broker_link_copy_v39(
    *,
    stock_name: str,
    stock_id: str,
    symbol: str,
    execution_status: str,
    has_scan_rows: bool,
    has_linked_records: bool,
) -> tuple[str, str]:
    if not has_scan_rows:
        return (
            f"交易状态：已切到交易执行页，但 {stock_name} 还缺少扫描结果，请先刷新股票池。",
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) 已加入观察池，等待扫描后生成委托建议",
        )
    if execution_status == "已提交":
        return (
            f"交易状态：当前联动 {stock_name} ({stock_id}) | 已提交，优先跟踪回执、成交与执行偏差",
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) | 已提交，继续跟踪交易回执与成交偏差",
        )
    if execution_status == "已送审":
        return (
            f"交易状态：当前联动 {stock_name} ({stock_id}) | 已送审，优先确认结果并准备进入交易",
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) | 已送审，优先复核送审结果与交易链路",
        )
    if execution_status == "提交失败":
        return (
            f"交易状态：当前联动 {stock_name} ({stock_id}) | 提交失败，先复核风险、参数与通道状态",
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) | 提交失败，先回看阻塞项再决定是否重试",
        )
    if has_linked_records:
        return (
            f"交易状态：当前联动 {stock_name} ({stock_id}) | 已同步委托建议与提交记录",
            f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) | 已联动推荐池与执行链路",
        )
    return (
        f"交易状态：当前联动 {stock_name} ({stock_id}) | 已切到交易页，等待该票生成委托建议",
        f"委托动作面板 / 委托焦点：{stock_name} ({stock_id} / {symbol}) | 已同步焦点，等待生成委托建议",
    )


def _qh_broker_link_target_v40(
    *,
    execution_status: str,
    order_selected: bool,
    execution_selected: bool,
) -> str:
    if execution_status in {"已提交", "提交失败"} and execution_selected:
        return "execution_table"
    if order_selected:
        return "orders_table"
    if execution_selected:
        return "execution_table"
    return "orders_table"


def _qh_broker_execution_summary_v41(
    *,
    stock_name: str,
    stock_id: str,
    symbol: str,
    order_status_text: str,
    fill_status_text: str,
    failure_reason: str,
    message: str,
) -> dict[str, str]:
    order_status_text = str(order_status_text or "--")
    fill_status_text = str(fill_status_text or "--")
    failure_reason = str(failure_reason or "").strip()
    message = str(message or "").strip()

    if failure_reason or order_status_text in {"提交失败", "失败"} or fill_status_text in {"已拒绝", "拒绝"}:
        stage = "阻塞待处理"
        judgement = "本次委托未顺利进入成交阶段，先处理失败原因、风险参数和交易通道状态。"
        next_step = "下一步：复核价格、数量、账户可用资金和风控阈值，确认后再决定是否重试。"
        banner = f"交易状态：{stock_name} ({stock_id}) | 阻塞待处理，优先排查失败原因与通道状态。"
    elif fill_status_text in {"已成交", "全部成交"}:
        stage = "已成交待复盘"
        judgement = "委托已完成成交，当前重点从提交链路转入执行质量、持仓同步和退出节奏。"
        next_step = "下一步：检查成交价格是否偏离原计划，并同步持仓、止盈止损和退出安排。"
        banner = f"交易状态：{stock_name} ({stock_id}) | 已成交，优先回看执行质量与持仓衔接。"
    elif fill_status_text in {"待成交", "部分成交"} or order_status_text == "已提交":
        stage = "待成交跟踪"
        judgement = "委托已进入执行通道，当前重点是继续跟踪回执、成交状态和价格偏差。"
        next_step = "下一步：持续跟踪回执；如长时间未成交，回看价格、仓位和盘口承接。"
        banner = f"交易状态：{stock_name} ({stock_id}) | 待成交跟踪，优先盯回执、成交与价格偏差。"
    else:
        stage = "执行状态跟踪"
        judgement = "当前记录已进入交易链路，建议结合订单状态与系统反馈继续判断。"
        next_step = "下一步：结合回执信息判断继续等待、重试，或回推荐页复核主线。"
        banner = f"交易状态：{stock_name} ({stock_id}) | 已进入交易链路，继续跟踪执行反馈。"

    tooltip = "\n".join(
        [
            f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"执行阶段：{stage}",
            f"订单状态：{order_status_text}",
            f"成交状态：{fill_status_text}",
            next_step,
        ]
    )
    if failure_reason:
        tooltip += f"\n阻塞原因：{failure_reason}"
    elif message:
        tooltip += f"\n系统反馈：{message}"

    return {
        "stage": stage,
        "judgement": judgement,
        "next_step": next_step,
        "banner": banner,
        "tooltip": tooltip,
        "order_status": order_status_text,
        "fill_status": fill_status_text,
    }


def _qh_broker_execution_followup_v42(
    *,
    stage: str,
    has_recommendation: bool,
    has_intent: bool,
) -> dict[str, str]:
    stage = str(stage or "")
    if stage == "阻塞待处理":
        return {
            "headline": "回推荐页复核",
            "detail": (
                "优先回推荐页复核主线、题材、价位与仓位纪律。"
                if has_recommendation
                else "当前缺少推荐联动，先留在交易页修正委托参数和风控设置。"
            ),
            "route": "推荐页 / 交易页",
        }
    if stage == "已成交待复盘":
        return {
            "headline": "切到复盘页",
            "detail": "成交已经落地，下一步优先复盘执行偏差、持仓同步和退出节奏。",
            "route": "复盘页",
        }
    if stage == "待成交跟踪":
        return {
            "headline": "留在交易页盯回执",
            "detail": (
                "先在交易页继续跟踪回执、成交状态和价格偏差。"
                if has_intent
                else "当前以执行回执为主，先继续盯成交状态，必要时再返回推荐页复核价格计划。"
            ),
            "route": "交易页",
        }
    return {
        "headline": "继续跟踪执行",
        "detail": "当前记录已进入交易链路，先看回执变化，再决定是否返回推荐页或复盘页。",
        "route": "交易页 / 推荐页 / 复盘页",
    }


def _qh_broker_repair_hint_v43(
    *,
    failure_reason: str,
    message: str,
    has_recommendation: bool,
) -> dict[str, str]:
    failure_reason = str(failure_reason or "").strip()
    message = str(message or "").strip()
    combined = f"{failure_reason} {message}".strip()

    if any(token in combined for token in ("可用资金", "资金不足", "余额不足", "现金不足")):
        return {
            "headline": "先收缩仓位",
            "detail": "优先降低数量、拆分委托或调整预算，再回推荐页复核买点与仓位纪律。",
            "checkpoint": "检查账户可用资金、单笔预算和目标仓位是否匹配。",
        }
    if any(token in combined for token in ("超卖", "持仓不足", "风控", "风险", "超过可卖")):
        return {
            "headline": "先修正风控",
            "detail": (
                "先修正数量、方向和风控阈值，再决定是否继续推进。"
                if not has_recommendation
                else "先回推荐页和交易页一起复核方向、止损与仓位纪律，再决定是否重试。"
            ),
            "checkpoint": "检查委托方向、可卖数量、止损位和风险灯是否一致。",
        }
    if any(token in combined for token in ("柜台", "通道", "登录", "环境", "SDK", "桥接")):
        return {
            "headline": "先检查通道",
            "detail": "优先排查登录状态、SDK/桥接环境和柜台可用性，确认后再重新提交。",
            "checkpoint": "检查交易通道、环境诊断、账户登录和桥接解释器状态。",
        }
    return {
        "headline": "先复核参数",
        "detail": (
            "先回推荐页复核主线、价位和题材，再回交易页修正委托参数。"
            if has_recommendation
            else "当前缺少推荐联动，先留在交易页复核价格、数量和风险参数。"
        ),
        "checkpoint": "检查主线是否仍成立、价格是否偏离计划、数量与仓位是否匹配。",
    }


def _qh_broker_execution_tone_v44(stage: str) -> str:
    stage = str(stage or "")
    if stage == "阻塞待处理":
        return "risk"
    if stage == "已成交待复盘":
        return "buy"
    if stage in {"待成交跟踪", "执行状态跟踪"}:
        return "watch"
    return "idle"


def _qh_broker_recommend_context_v45(
    *,
    price_brief: str,
    news_lines: list[str],
) -> list[str]:
    lines: list[str] = []
    price_brief = str(price_brief or "").strip()
    if price_brief:
        lines.append(f"价格计划：{price_brief}")
    cleaned_news = [str(item or "").strip() for item in list(news_lines or []) if str(item or "").strip()]
    if cleaned_news:
        first = cleaned_news[0]
        if first.startswith("- "):
            first = first[2:]
        lines.append(f"最近催化：{first}")
    else:
        lines.append("最近催化：暂无近期催化")
    return lines


def _qh_broker_parameter_alignment_v46(
    *,
    side: str,
    order_price: str | float,
    plan_entry: float | None,
    plan_stop: float | None,
    plan_target: float | None,
) -> dict[str, str]:
    side = str(side or "").upper()
    try:
        price_value = float(order_price or 0.0)
    except (TypeError, ValueError):
        price_value = 0.0
    entry = float(plan_entry or 0.0)
    stop = float(plan_stop or 0.0)
    target = float(plan_target or 0.0)

    if price_value <= 0 or entry <= 0:
        return {
            "headline": "参数待复核",
            "detail": "当前缺少可比较的计划价格，先回推荐页或委托建议区补齐价格带。",
            "checkpoint": "检查买点、止损、目标位是否已经生成并同步到交易页。",
        }

    if side in {"SELL", "REDUCE"}:
        if stop > 0 and price_value <= stop:
            return {
                "headline": "防守位处理",
                "detail": "当前卖减价格已落到防守位附近，更偏向纪律性退出而不是继续等待更高价格。",
                "checkpoint": "确认减仓比例、退出节奏和剩余仓位是否符合防守计划。",
            }
        if target > 0 and price_value >= target * 0.99:
            return {
                "headline": "接近兑现区",
                "detail": "当前卖减价格已经接近原计划目标位，可优先按兑现节奏执行并回看仓位变化。",
                "checkpoint": "检查兑现比例、剩余持仓和后续跟踪计划是否清晰。",
            }
        return {
            "headline": "仍在计划区",
            "detail": "当前卖减价格仍处在可执行区间，继续结合回执与仓位纪律推进。",
            "checkpoint": "检查减仓比例、成交回执和剩余仓位的处理安排。",
        }

    deviation_pct = (price_value - entry) / max(entry, 0.001)
    if stop > 0 and price_value <= stop:
        return {
            "headline": "跌近防守位",
            "detail": "当前委托价格已经逼近原计划防守位，先确认主线和承接是否仍然成立。",
            "checkpoint": "优先复核止损纪律、主线强度和是否应继续执行。",
        }
    if target > 0 and price_value >= target:
        return {
            "headline": "接近目标位",
            "detail": "当前价格已接近原计划目标位，继续追价的性价比明显下降。",
            "checkpoint": "回推荐页复核是否需要降仓、放弃追价或改成等待回踩。",
        }
    if deviation_pct >= 0.02:
        return {
            "headline": "买点偏高",
            "detail": f"当前委托价格较计划买点抬高 {deviation_pct:.1%}，先确认承接和仓位后再决定是否追价。",
            "checkpoint": "检查是否需要降低仓位、分批成交，或回推荐页重算买点区间。",
        }
    if deviation_pct <= -0.02:
        return {
            "headline": "低于计划买点",
            "detail": f"当前价格较计划买点低 {abs(deviation_pct):.1%}，先确认这是更优性价比还是主线走弱。",
            "checkpoint": "检查是否跌破防守位、承接是否减弱，以及是否仍值得执行。",
        }
    return {
        "headline": "价格贴合计划",
        "detail": "当前委托价格仍在原计划买点附近，可重点关注回执、成交与执行偏差。",
        "checkpoint": "保持仓位纪律，继续跟踪回执和成交是否偏离原计划。",
    }


def _qh_broker_resolution_action_v47(
    *,
    stage: str,
    repair_headline: str,
    parameter_headline: str,
    has_recommendation: bool,
    channel_text: str,
) -> dict[str, str]:
    stage = str(stage or "")
    repair_headline = str(repair_headline or "")
    parameter_headline = str(parameter_headline or "")
    channel_text = str(channel_text or "当前通道")

    if repair_headline == "先检查通道":
        return {
            "target": "账户配置",
            "detail": f"先检查 {channel_text} 通道、登录状态和桥接环境，确认可用后再考虑重提。",
            "button_hint": f"当前更建议先检查 {channel_text} 通道和环境，不要直接重复提交。",
        }
    if stage == "已成交待复盘":
        return {
            "target": "复盘页",
            "detail": "当前更适合切到复盘页检查执行偏差、持仓衔接和退出节奏。",
            "button_hint": "当前已经进入成交后处理阶段，优先复盘执行质量而不是重新生成委托。",
        }
    if has_recommendation and parameter_headline in {"买点偏高", "接近目标位", "低于计划买点"}:
        return {
            "target": "推荐页",
            "detail": "优先回推荐页复核买点区间、目标位和主线强度，再回交易页决定是否重生成委托。",
            "button_hint": "建议先回推荐页复核价格计划；确认后再重新生成委托建议。",
        }
    if repair_headline in {"先收缩仓位", "先修正风控"} or parameter_headline in {"跌近防守位", "防守位处理", "接近兑现区"}:
        return {
            "target": "委托参数区",
            "detail": "优先留在交易页调整价格、数量、仓位和止损，再决定是否继续提交。",
            "button_hint": "建议先在交易页修正价格、数量和风控参数，再决定是否提交。",
        }
    return {
        "target": "执行回执区",
        "detail": "当前更适合继续盯执行回执和成交变化，确认没有进一步偏离再操作。",
        "button_hint": "当前更适合继续跟踪回执；如需更新计划，再重新生成委托建议。",
    }


def _qh_broker_terminal_brief_v48(
    *,
    stock_name: str,
    stock_id: str,
    stage: str,
    mainline_signal: str,
    parameter_headline: str,
    resolution_target: str,
) -> dict[str, str]:
    stock_name = str(stock_name or "焦点票")
    stock_id = str(stock_id or "--")
    stage = str(stage or "待跟踪")
    mainline_signal = str(mainline_signal or "待确认")
    parameter_headline = str(parameter_headline or "参数待复核")
    resolution_target = str(resolution_target or "交易页")
    return {
        "status": f"交易状态：{stock_name} {stock_id} | {stage} | 去{resolution_target}",
        "workbench": f"交易工作台：{stock_name} | 主线 {mainline_signal} | {parameter_headline} | 去{resolution_target}",
        "stage": f"执行阶段：{stage} | 主线 {mainline_signal} | 去{resolution_target}",
        "focus": f"执行焦点：{stock_name} | {parameter_headline} | 去{resolution_target}",
    }


def _qh_broker_panel_conclusion_v49(
    *,
    stage: str,
    parameter_headline: str,
    resolution_target: str,
) -> str:
    stage = str(stage or "待跟踪")
    parameter_headline = str(parameter_headline or "参数待复核")
    resolution_target = str(resolution_target or "交易页")
    return f"结论：{stage} / {parameter_headline} / 去{resolution_target}"


def _qh_broker_execution_deck_v50(
    *,
    stock_name: str,
    stock_id: str,
    symbol: str,
    side_text: str,
    quantity: str,
    price: str,
    mainline_signal: str,
    mainline_stage: str,
    stage: str,
    parameter_headline: str,
    repair_headline: str,
    resolution_target: str,
) -> dict[str, str]:
    stock_name = str(stock_name or "焦点票")
    stock_id = str(stock_id or "--")
    symbol = str(symbol or "--")
    side_text = str(side_text or "待确认")
    quantity = str(quantity or "--")
    price = str(price or "--")
    mainline_signal = str(mainline_signal or "待确认")
    mainline_stage = str(mainline_stage or "待确认")
    stage = str(stage or "待跟踪")
    parameter_headline = str(parameter_headline or "参数待复核")
    repair_headline = str(repair_headline or "先复核参数")
    resolution_target = str(resolution_target or "交易页")
    return {
        "symbol_value": stock_name,
        "symbol_accent": f"{stock_id} / {symbol}",
        "gate_value": stage,
        "gate_accent": f"{mainline_signal} / {mainline_stage}",
        "risk_value": parameter_headline,
        "risk_accent": repair_headline,
        "position_value": f"去{resolution_target}",
        "position_accent": f"{side_text} {quantity} @ {price}",
        "headline": f"执行动作面板：{stock_name} | {stage} | 去{resolution_target}",
    }


def _qh_focus_symbol_in_broker_workspace(self: QuantHunterWindow, symbol: str) -> None:
    if not symbol:
        return
    stock_name = self._stock_name_for_symbol(symbol)
    stock_id = self._stock_id_for_symbol(symbol)
    execution_status = str((getattr(self, "execution_status_by_symbol", {}) or {}).get(symbol, "") or "")
    self._queue_symbol_to_watchlist(symbol)
    self._navigate_to_workspace("broker", "orders_table")
    has_scan_rows = bool(getattr(self, "scan_rows", []))
    if has_scan_rows:
        self.generate_order_suggestions()
        order_selected = self._select_order_intent_row_for_symbol(symbol)
        execution_selected = self._select_execution_row_for_symbol(symbol)
        target_widget = _qh_broker_link_target_v40(
            execution_status=execution_status,
            order_selected=bool(order_selected),
            execution_selected=bool(execution_selected),
        )
        banner_text, focus_text = _qh_broker_link_copy_v39(
            stock_name=stock_name,
            stock_id=stock_id,
            symbol=symbol,
            execution_status=execution_status,
            has_scan_rows=True,
            has_linked_records=bool(order_selected or execution_selected),
        )
    else:
        target_widget = "orders_table"
        banner_text, focus_text = _qh_broker_link_copy_v39(
            stock_name=stock_name,
            stock_id=stock_id,
            symbol=symbol,
            execution_status=execution_status,
            has_scan_rows=False,
            has_linked_records=False,
        )
    self._navigate_to_workspace("broker", target_widget, target_widget)
    self._refresh_broker_order_focus()
    self._refresh_submission_focus()
    if hasattr(self, "broker_status_banner"):
        self._set_label_text_if_changed(self.broker_status_banner, banner_text, tooltip=banner_text)
    if hasattr(self, "orders_focus_label"):
        self._set_label_text_if_changed(self.orders_focus_label, focus_text, tooltip=focus_text)


def _qh_open_detail_to_broker(self: QuantHunterWindow) -> None:
    symbol = getattr(self, "active_symbol", "") or ""
    if symbol:
        self._focus_symbol_in_broker_workspace(symbol)
        self._focus_symbol_everywhere(symbol, origin="detail")
    else:
        self._navigate_to_workspace("broker", "orders_table")
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, "交易状态：已从复盘页切到交易执行页，请优先查看当前委托链路。")


def _qh_open_monitor_symbol_in_board(self: QuantHunterWindow) -> None:
    symbol = self._selected_symbol_from_watchlist() or getattr(self, "active_symbol", "") or ""
    if not symbol:
        self._navigate_to_workspace("board", "board_table")
        if hasattr(self, "board_text"):
            self._set_plain_text_if_changed(self.board_text, "打板候选池\n\n已切到打板页，请先从扫描页、推荐页或观察池选中一只股票。")
        return
    self._select_board_candidate_row_for_symbol(symbol)
    self._select_board_monitor_row_for_symbol(symbol)
    self._navigate_to_workspace("board", "board_table")
    self._refresh_board_focus_panels(symbol)
    if hasattr(self, "board_focus_label"):
        self._set_label_text_if_changed(
            self.board_focus_label,
            f"打板焦点：{self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 已从扫描链路同步候选与监控",
        )


def _qh_open_monitor_symbol_in_broker(self: QuantHunterWindow) -> None:
    symbol = self._selected_symbol_from_watchlist() or getattr(self, "active_symbol", "") or ""
    if not symbol:
        self._navigate_to_workspace("broker", "orders_table")
        if hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, "交易状态：已切到交易执行页，请先从扫描页或推荐页同步焦点股票。")
        return
    self._focus_symbol_in_broker_workspace(symbol)
    if hasattr(self, "broker_status_banner"):
        self._set_label_text_if_changed(
            self.broker_status_banner,
            f"交易状态：已从扫描监控联动 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 请复核委托后再提交",
        )


def _qh_open_board_symbol_in_recommend(self: QuantHunterWindow) -> None:
    symbol = self._selected_board_symbol()
    if symbol:
        self._focus_symbol_in_recommend_workspace(symbol)
        if hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(
                self.recommend_status_label,
                f"推荐状态：已从打板页同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)})，请继续核对主线与计划。",
            )
    else:
        self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")


def _qh_open_board_symbol_in_scanner(self: QuantHunterWindow) -> None:
    symbol = self._selected_board_symbol()
    if symbol:
        self._select_scan_row_for_symbol(symbol)
        self._select_watchlist_symbol(symbol)
        self._select_monitor_row_for_symbol(symbol)
        if symbol in self.universe_bars:
            self.select_symbol(symbol)
        self._refresh_monitor_summary(symbol)
        self._refresh_scanner_focus_status(symbol)
        self._refresh_scanner_focus_cards(symbol)
        if hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(
                self.scan_summary_label,
                f"扫描状态：已从打板页同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)})，继续查看盘中监控。",
            )
    self._navigate_to_workspace("scanner", "scan_table")


def _qh_post_build_ui_tweaks(self: QuantHunterWindow) -> None:
    _ORIGINAL_POST_BUILD_UI_TWEAKS(self)
    self._apply_runtime_font_preferences()
    self._polish_visual_surfaces()
    self._upgrade_auth_workspace()
    self._upgrade_broker_workspace()
    self._upgrade_analysis_workspaces()
    self._polish_scanner_toolbar()
    self._apply_identity_table_headers()
    self._force_identity_columns_visible()
    self._tune_operational_tables()
    self._prime_broker_workspace_defaults()
    self._refresh_login_status()
    self._rebind_workspace_action_rows()
    self._refresh_broker_auxiliary_panels()


def _qh_refresh_board_focus_cards(
    self: QuantHunterWindow,
    symbol: str = "",
    candidate: dict | None = None,
    monitor_payload: dict | None = None,
) -> None:
    labels = getattr(self, "board_focus_metric_labels", None)
    accents = getattr(self, "board_focus_metric_accents", None)
    if not labels or not accents:
        return
    if not symbol:
        self._set_label_text_if_changed(labels["symbol"], "--")
        self._set_label_text_if_changed(accents["symbol"], "等待候选同步")
        self._set_label_text_if_changed(labels["score"], "--")
        self._set_label_text_if_changed(accents["score"], "等待强度计算")
        self._set_label_text_if_changed(labels["risk"], "待评估")
        self._set_label_text_if_changed(accents["risk"], "等待风控刷新")
        self._set_label_text_if_changed(labels["action"], "待联动")
        self._set_label_text_if_changed(accents["action"], "等待监控链路")
        return

    scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == symbol), None)
    payload = monitor_payload or {}
    stock_name = (candidate or {}).get("stock_name") or self._stock_name_for_symbol(symbol)
    stock_id = (candidate or {}).get("stock_id") or self._stock_id_for_symbol(symbol)

    self._set_label_text_if_changed(labels["symbol"], stock_name)
    self._set_label_text_if_changed(accents["symbol"], stock_id or "--")

    if candidate is not None:
        self._set_label_text_if_changed(labels["score"], str(candidate.get("board_score", "--")))
        self._set_label_text_if_changed(accents["score"], candidate.get("trigger_style", "待确认"))
    elif scan_row is not None:
        self._set_label_text_if_changed(labels["score"], f"{getattr(scan_row, 'score', 0.0):.1f}")
        self._set_label_text_if_changed(accents["score"], self._display_label(getattr(scan_row, "label", "WATCH")))
    else:
        self._set_label_text_if_changed(labels["score"], "--")
        self._set_label_text_if_changed(accents["score"], "等待强度计算")

    self._set_label_text_if_changed(labels["risk"], str((candidate or {}).get("risk_level", payload.get("risk_level", "待评估"))))
    self._set_label_text_if_changed(
        accents["risk"],
        payload.get("state") or ("扫描联动" if scan_row is not None else "等待风险跟踪"),
    )

    self._set_label_text_if_changed(
        labels["action"],
        payload.get("action_plan")
        or (self._display_action(getattr(scan_row, "action", "WATCH")) if scan_row is not None else "继续观察"),
    )
    self._set_label_text_if_changed(
        accents["action"],
        f"强度 {payload.get('strength', '--')} / 持续性 {payload.get('continuity', '--')}"
        if payload
        else ("扫描摘要已接入" if scan_row is not None else "等待监控链路"),
    )


QuantHunterWindow._apply_runtime_font_preferences = _qh_apply_runtime_font_preferences
QuantHunterWindow._polish_visual_surfaces = _qh_polish_visual_surfaces
QuantHunterWindow._upgrade_auth_workspace = _qh_upgrade_auth_workspace
QuantHunterWindow._upgrade_broker_workspace = _qh_upgrade_broker_workspace
QuantHunterWindow._upgrade_analysis_workspaces = _qh_upgrade_analysis_workspaces
QuantHunterWindow._rebind_workspace_action_rows = _qh_rebind_workspace_action_rows
QuantHunterWindow._polish_scanner_toolbar = _qh_polish_scanner_toolbar
QuantHunterWindow._tune_operational_tables = _qh_tune_operational_tables
QuantHunterWindow._apply_identity_table_headers = _qh_apply_identity_table_headers
QuantHunterWindow._force_identity_columns_visible = _qh_force_identity_columns_visible
QuantHunterWindow._refresh_login_status = _qh_refresh_login_status
QuantHunterWindow._prime_broker_workspace_defaults = _qh_prime_broker_workspace_defaults
QuantHunterWindow._refresh_broker_status = _qh_refresh_broker_status
QuantHunterWindow._refresh_submission_focus = _qh_refresh_submission_focus
QuantHunterWindow._refresh_broker_auxiliary_panels = _qh_refresh_broker_auxiliary_panels
QuantHunterWindow._on_orders_selection_changed = _qh_on_orders_selection_changed
QuantHunterWindow._on_execution_selection_changed = _qh_on_execution_selection_changed
QuantHunterWindow._refresh_detail_workspace_panels = _qh_refresh_detail_workspace_panels
QuantHunterWindow._refresh_scanner_focus_status = _qh_refresh_scanner_focus_status
QuantHunterWindow._refresh_scanner_focus_cards = _qh_refresh_scanner_focus_cards
QuantHunterWindow._refresh_scanner_summary_cards = _qh_refresh_scanner_summary_cards
QuantHunterWindow._refresh_board_focus_panels = _qh_refresh_board_focus_panels
QuantHunterWindow._focus_symbol_in_broker_workspace = _qh_focus_symbol_in_broker_workspace
QuantHunterWindow.open_detail_to_broker = _qh_open_detail_to_broker
QuantHunterWindow.open_monitor_symbol_in_board = _qh_open_monitor_symbol_in_board
QuantHunterWindow.open_monitor_symbol_in_broker = _qh_open_monitor_symbol_in_broker
QuantHunterWindow.open_board_symbol_in_recommend = _qh_open_board_symbol_in_recommend
QuantHunterWindow.open_board_symbol_in_scanner = _qh_open_board_symbol_in_scanner
QuantHunterWindow._post_build_ui_tweaks = _qh_post_build_ui_tweaks
QuantHunterWindow._refresh_board_focus_cards = _qh_refresh_board_focus_cards


def _qh_workspace_badge_text_v2(self: QuantHunterWindow, current_name: str) -> str:
    label_aliases = {
        "龙头主控台": "市场机会工作台",
        "打板监控": "打板专项",
        "强势接力": "擒龙打板",
    }
    label = label_aliases.get(current_name or "", current_name or "市场机会工作台")
    brand = "Fire Money Pro"

    if label in {"策略扫描"}:
        scan_count = len(getattr(self, "scan_rows", []) or [])
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        monitor_count = getattr(self, "monitor_table", None).rowCount() if hasattr(self, "monitor_table") else 0
        return f"{brand} · {label} · 扫描 {scan_count} / 观察 {watch_count} / 监控 {monitor_count}"

    if label in {"打板专项"}:
        board_count = getattr(self, "board_table", None).rowCount() if hasattr(self, "board_table") else 0
        monitor_count = getattr(self, "board_monitor_table", None).rowCount() if hasattr(self, "board_monitor_table") else 0
        return f"{brand} · {label} · 候选 {board_count} / 监控 {monitor_count}"

    if label in {"每日推荐"}:
        pool_count = len(getattr(self, "daily_pool_rows", []) or [])
        plan_count = len(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or [])
        return f"{brand} · {label} · 机会 {pool_count} / 计划 {plan_count}"

    if label in {"交易执行"}:
        pending_orders = len(getattr(self, "order_intents", []) or [])
        submitted_orders = len(getattr(self, "order_submission_records", []) or [])
        return f"{brand} · {label} · 待审 {pending_orders} / 已提交 {submitted_orders}"

    return f"{brand} · {label}"


def _qh_normalize_recommend_workspace_texts_v2(self: QuantHunterWindow) -> None:
    title_map = {
        "recommend_dispatch_text": "待送审",
        "recommend_focus_review_text": "焦点复核",
        "recommend_queue_text": "已提交与失败",
        "strategy_detail_text": "战法明细",
        "strategy_path_text": "主线推演",
        "daily_pool_text": "综合机会池",
        "market_pulse_text": "市场温度",
        "position_advice_text": "持仓处理建议",
        "trade_plan_text": "今日交易计划",
    }
    for attr_name, title in title_map.items():
        widget = getattr(self, attr_name, None)
        if widget is None:
            continue
        parent = widget.parentWidget()
        while parent is not None and not isinstance(parent, QGroupBox):
            parent = parent.parentWidget()
        if isinstance(parent, QGroupBox):
            if parent.title() != title:
                parent.setTitle(title)

    if hasattr(self, "recommend_stage_tabs"):
        for index, label in enumerate(["交易执行", "策略研究", "复盘跟踪"]):
            if index < self.recommend_stage_tabs.count():
                if self.recommend_stage_tabs.tabText(index) != label:
                    self.recommend_stage_tabs.setTabText(index, label)

    button_map = {
        "show_core_execution_bucket": "只看高优先池",
        "show_watch_bucket": "只看观察池",
        "show_risk_bucket": "只看风险池",
    }
    legacy_aliases = {
        "只看主线前排": "show_core_execution_bucket",
        "只看高优先池": "show_core_execution_bucket",
        "只看观察池": "show_watch_bucket",
        "只看风险池": "show_risk_bucket",
        "只看回避池": "show_risk_bucket",
    }
    for button in self.findChildren(QPushButton):
        text = button.text().strip()
        if text in legacy_aliases:
            self._set_label_text_if_changed(button, button_map[legacy_aliases[text]])
        elif text == "导出运行日志":
            self._set_label_text_if_changed(button, "导出日志")

    strategy_combo = getattr(self, "strategy_detail_combo", None)
    if strategy_combo is not None:
        labels = ["龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"]
        current = strategy_combo.currentText().strip()
        alias_map = {
            "龙头主线": "龙头模型",
            "资金承接": "主力雷达",
            "强势接力": "擒龙打板",
            "趋势低吸": "价值低吸",
            "尾盘抢筹": "尾盘买入法",
            "尾盘买入": "尾盘买入法",
            "一日持股": "一日持股法",
            "综合决策": "掘龙决策",
        }
        current = alias_map.get(current, current)
        strategy_combo.blockSignals(True)
        strategy_combo.clear()
        strategy_combo.addItems(labels)
        strategy_combo.setCurrentText(current if current in labels else labels[0])
        strategy_combo.blockSignals(False)


def _qh_normalize_board_workspace_texts_v2(self: QuantHunterWindow) -> None:
    title_map = {
        "board_text": "打板专项候选",
        "board_monitor_text": "炸板 / 回封监控",
    }
    for attr_name, title in title_map.items():
        widget = getattr(self, attr_name, None)
        if widget is None:
            continue
        parent = widget.parentWidget()
        while parent is not None and not isinstance(parent, QGroupBox):
            parent = parent.parentWidget()
        if isinstance(parent, QGroupBox):
            if parent.title() != title:
                parent.setTitle(title)

    if hasattr(self, "auto_review_export_checkbox"):
        self._set_label_text_if_changed(self.auto_review_export_checkbox, "15:05 后自动导出复盘日报")

    if hasattr(self, "board_text"):
        self._set_plain_text_if_changed(
            self.board_text,
            "打板专项候选\n\n"
            "这里只保留高风险高弹性的擒龙打板候选，不和主工作台抢入口。\n"
            "优先看主线前排、回封质量、承接强度和可执行区间，再决定是否转入交易执行。"
        )
    if hasattr(self, "board_monitor_text"):
        self._set_plain_text_if_changed(
            self.board_monitor_text,
            "炸板 / 回封监控\n\n"
            "这里持续跟踪回封力度、炸板风险、封单稳定性和情绪衰减。\n"
            "当候选和监控同时到位时，再决定是继续观察、转入交易，还是直接放弃。"
        )


def _qh_repair_runtime_widget_texts_v2(self: QuantHunterWindow) -> None:
    clean_map = {
        "龙头主控台": "市场机会工作台",
        "龙头股票池": "机会股票池",
        "打板监控": "打板专项",
        "打板模式": "打板专项",
        "强势接力": "擒龙打板",
        "尾盘抢筹": "尾盘买入法",
        "隔日强势": "一日持股法",
        "只看主线前排": "只看高优先池",
        "只看回避池": "只看风险池",
        "主线前排": "高优先池",
        "回避池": "风险池",
        "持仓跟踪": "持仓处理建议",
        "导出运行日志": "导出日志",
        "主题摘要": "主线摘要",
        "资金决策": "资金与决策",
    }

    for widget_type in (QPushButton, QCheckBox, QLabel):
        for widget in self.findChildren(widget_type):
            text = widget.text().strip() if hasattr(widget, "text") else ""
            normalized = clean_map.get(text)
            if normalized:
                self._set_label_text_if_changed(widget, normalized)

    for box in self.findChildren(QGroupBox):
        title = box.title().strip()
        normalized = clean_map.get(title)
        if normalized:
            if title != normalized:
                box.setTitle(normalized)

    for tabs in self.findChildren(QTabWidget):
        for index in range(tabs.count()):
            text = tabs.tabText(index).strip()
            normalized = clean_map.get(text)
            if normalized:
                if text != normalized:
                    tabs.setTabText(index, normalized)

    self._tune_overview_recommend_tables()
    self._polish_workspace_information_density()
    self._polish_summary_card_blocks()


def _qh_normalize_overview_builder_texts_v2(self: QuantHunterWindow) -> None:
    if hasattr(self, "market_search_input"):
        self.market_search_input.setPlaceholderText("请输入股票代码 / 名称 / 题材 / 关键词")
    if hasattr(self, "market_theme_combo"):
        self.market_theme_combo.blockSignals(True)
        self.market_theme_combo.clear()
        self.market_theme_combo.addItem("全部")
        self.market_theme_combo.blockSignals(False)
    if hasattr(self, "market_history_date_combo"):
        self.market_history_date_combo.blockSignals(True)
        self.market_history_date_combo.clear()
        self.market_history_date_combo.addItem("最新")
        self.market_history_date_combo.blockSignals(False)
    if hasattr(self, "market_refresh_button"):
        self._set_label_text_if_changed(self.market_refresh_button, "一键刷新市场")
    if hasattr(self, "market_history_reset_button"):
        self._set_label_text_if_changed(self.market_history_reset_button, "回到最新")
    if hasattr(self, "dashboard_auto_refresh_checkbox"):
        self._set_label_text_if_changed(self.dashboard_auto_refresh_checkbox, "盘中自动刷新")
    if hasattr(self, "market_status_label"):
        current = self.market_status_label.text().strip()
        if not current or self._has_mojibake_text(current):
            self._set_label_text_if_changed(self.market_status_label, "总览状态：准备同步市场、主线、趋势与消息。")
    if hasattr(self, "market_header_label"):
        self._set_label_text_if_changed(self.market_header_label, "市场机会工作台")
    if hasattr(self, "market_subheader_label"):
        self._set_label_text_if_changed(self.market_subheader_label, "统一查看主线龙头、趋势机会、消息催化、买卖决策和复盘研究。")
    if hasattr(self, "market_signal_label"):
        self._set_label_text_if_changed(self.market_signal_label, "主线强度 / 趋势延续 / 资金承接 / 消息催化 / 买卖节奏")
    if hasattr(self, "market_quote_label"):
        self._set_label_text_if_changed(self.market_quote_label, "价格 / 涨跌幅 / 换手 / 资金流 / 主线位次 / 股票池")

    button_groups = [
        ("overview_quick_buttons", list(OVERVIEW_QUICK_ROUTE_SPECS.keys()), self.activate_overview_quick_action),
        ("market_filter_buttons", STRATEGY_FILTER_LABELS, self.set_market_filter),
        ("timeframe_buttons", ["分时", "1分", "5分", "15分", "30分", "60分", "日线", "周线", "月线"], self.set_market_timeframe),
        ("history_window_buttons", ["近1月", "近3月", "近1年", "全部"], self.set_market_history_window),
        ("secondary_indicator_buttons", ["MACD", "RSI", "KDJ"], self.set_market_secondary_indicator),
    ]
    for attr_name, labels, handler in button_groups:
        current_map = getattr(self, attr_name, None)
        if not current_map:
            continue
        buttons = list(current_map.values())
        normalized = {}
        for index, button in enumerate(buttons):
            label = labels[index] if index < len(labels) else button.text()
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            self._set_label_text_if_changed(button, label)
            button.clicked.connect(lambda checked=False, current=label, callback=handler: callback(current))
            normalized[label] = button
        setattr(self, attr_name, normalized)

    if hasattr(self, "market_pool_table"):
        self.market_pool_table.setHorizontalHeaderLabels(["层级", "股票标识", "资金标签", "策略标签", "涨跌幅", "最新价"])
    if hasattr(self, "right_intel_tabs"):
        labels = ["主线摘要", "资金与决策"]
        for index, label in enumerate(labels):
            if index < self.right_intel_tabs.count():
                if self.right_intel_tabs.tabText(index) != label:
                    self.right_intel_tabs.setTabText(index, label)
    if hasattr(self, "market_news_group") and hasattr(self.market_news_group, "setTitle"):
        if self.market_news_group.title() != "消息催化":
            self.market_news_group.setTitle("消息催化")


def _qh_normalize_aux_workspace_texts_v2(self: QuantHunterWindow) -> None:
    if hasattr(self, "tabs"):
        for index, workspace_key in enumerate(WORKSPACE_TAB_ORDER):
            if index < self.tabs.count():
                label = WORKSPACE_LABEL_BY_KEY.get(workspace_key, WORKSPACE_TAB_LABELS[index])
                if self.tabs.tabText(index) != label:
                    self.tabs.setTabText(index, label)

    if hasattr(self, "auth_channel_combo"):
        current = self.auth_channel_combo.currentData()
        self.auth_channel_combo.blockSignals(True)
        self.auth_channel_combo.clear()
        self.auth_channel_combo.addItem("东方财富", "eastmoney")
        self.auth_channel_combo.addItem("GM", "gm")
        self.auth_channel_combo.addItem("自定义", "custom")
        for idx in range(self.auth_channel_combo.count()):
            if self.auth_channel_combo.itemData(idx) == current:
                self.auth_channel_combo.setCurrentIndex(idx)
                break
        self.auth_channel_combo.blockSignals(False)

    text_map = {
        "active_symbol_label": "当前标的：未选择",
        "broker_status_banner": BROKER_DEFAULT_STATUS_TEXT,
        "orders_focus_label": ORDERS_DEFAULT_FOCUS_TEXT,
        "trade_plan_focus_label": TRADE_PLAN_DEFAULT_FOCUS_TEXT,
        "recommend_status_label": RECOMMEND_DEFAULT_STATUS_TEXT,
        "recommend_empty_title": "等待市场快照",
        "recommend_empty_meta": RECOMMEND_DEFAULT_EMPTY_META,
        "daily_pool_focus_label": RECOMMEND_DEFAULT_FOCUS_TEXT,
        "universe_label": "股票池目录：未加载",
        "scan_summary_label": "扫描状态：等待首轮扫描，同步观察池与监控焦点。",
        "last_refresh_label": "最近刷新：等待市场快照建立",
    }
    for attr_name, value in text_map.items():
        widget = getattr(self, attr_name, None)
        if widget is not None and hasattr(widget, "setText"):
            current = widget.text().strip() if hasattr(widget, "text") else ""
            if not current or self._has_mojibake_text(current):
                self._set_label_text_if_changed(widget, value)

    button_map = {
        "recommend_empty_sample_button": "载入样例数据",
        "recommend_empty_refresh_button": "重算机会池",
        "broker_focus_blocker_button": "定位阻塞",
        "broker_focus_priority_button": "定位高优先",
        "generate_order_suggestions_button": "生成委托链路",
        "confirm_submit_orders_button": "确认并提交委托",
    }
    for attr_name, value in button_map.items():
        widget = getattr(self, attr_name, None)
        if widget is not None and hasattr(widget, "setText"):
            current = widget.text().strip() if hasattr(widget, "text") else ""
            if current != value:
                self._set_label_text_if_changed(widget, value)

    if hasattr(self, "recommend_stage_tabs"):
        for index, label in enumerate(["交易执行", "策略研究", "复盘跟踪"]):
            if index < self.recommend_stage_tabs.count():
                self.recommend_stage_tabs.setTabText(index, label)
    if hasattr(self, "right_intel_tabs"):
        for index, label in enumerate(["主线摘要", "资金与决策"]):
            if index < self.right_intel_tabs.count():
                self.right_intel_tabs.setTabText(index, label)


def _qh_prime_recommend_workspace_defaults_v2(self: QuantHunterWindow) -> None:
    if hasattr(self, "recommend_status_label"):
        self._set_label_text_if_changed(self.recommend_status_label, RECOMMEND_DEFAULT_STATUS_TEXT)
    if hasattr(self, "recommend_empty_title"):
        self._set_label_text_if_changed(self.recommend_empty_title, RECOMMEND_DEFAULT_EMPTY_TITLE)
    if hasattr(self, "recommend_empty_meta"):
        self._set_label_text_if_changed(self.recommend_empty_meta, RECOMMEND_DEFAULT_EMPTY_META)
    if hasattr(self, "recommend_empty_sample_button"):
        self._set_label_text_if_changed(self.recommend_empty_sample_button, RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT)
    if hasattr(self, "recommend_empty_refresh_button"):
        self._set_label_text_if_changed(self.recommend_empty_refresh_button, RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT)
    if hasattr(self, "last_refresh_label") and (
        not self.last_refresh_label.text().strip()
        or self._has_mojibake_text(self.last_refresh_label.text().strip())
        or "尚未刷新" in self.last_refresh_label.text()
    ):
        self._set_label_text_if_changed(self.last_refresh_label, "最近刷新：等待市场快照建立")

    if hasattr(self, "recommend_focus_metric_labels"):
        defaults = {
            "symbol": ("等待标的", "先同步综合机会池"),
            "theme": ("等待主线", "等待主线状态与趋势判断"),
            "action": ("待送审", "等待交易动作生成"),
            "execution": ("待观察", "等待链路阶段同步"),
        }
        for key, (value, accent) in defaults.items():
            if key in self.recommend_focus_metric_labels:
                self._set_label_text_if_changed(self.recommend_focus_metric_labels[key], value)
            if key in self.recommend_focus_metric_accents:
                self._set_label_text_if_changed(self.recommend_focus_metric_accents[key], accent)

    if hasattr(self, "recommend_summary_cards"):
        defaults = {
            "logic": ("等待主线同步", "等待主线、位次和风险灯同步。"),
            "plan": ("等待计划生成", "等待交易计划与送审优先级生成。"),
            "pulse": ("等待温度同步", "等待市场温度、周期和主线窗口同步。"),
            "holding": ("等待持仓导入", "等待持仓导入后生成处理建议。"),
        }
        for key, card in self.recommend_summary_cards.items():
            if hasattr(card, "set_data"):
                headline, detail = defaults.get(key, ("--", "等待链路同步"))
                card.set_data(headline, detail)

    if hasattr(self, "recommend_dispatch_text"):
        self._set_plain_text_if_changed(
            self.recommend_dispatch_text,
            "待送审\n\n"
            "1. 先确认主线是否延续，再看趋势是否共振、消息是否强化。\n"
            "2. 这里只保留待复核标的、送审节奏和当前优先链路。\n"
            "3. 只有主线、位置、量能和风险灯同时通过的标的，才送入交易执行。"
        )
    if hasattr(self, "recommend_focus_review_text"):
        self._set_plain_text_if_changed(
            self.recommend_focus_review_text,
            "焦点复核\n\n"
            "这里会汇总主线地位、趋势状态、消息催化、买卖点和失效条件。\n"
            "先确认它为什么值得送审，再确认什么时候能做、什么时候应该放弃。"
        )
    if hasattr(self, "recommend_queue_text"):
        self._set_plain_text_if_changed(
            self.recommend_queue_text,
            "已提交与失败\n\n"
            "这里集中显示已送审、已提交和失败记录，不让盘中视线被杂讯打散。\n"
            "优先跟踪最新回执、失败原因和需要重新处理的异常单。"
        )
    if hasattr(self, "strategy_path_text"):
        self._set_plain_text_if_changed(
            self.strategy_path_text,
            "主线推演\n\n"
            "这里会把主线强弱、趋势延续、消息催化和风险切换串成一条路径。\n"
            "用户看到的应该是结论先行，而不是一堆指标孤立堆在一起。"
        )


def _qh_hydrate_empty_workspace_panels_v2(self: QuantHunterWindow) -> None:
    fill_texts = {
        "overview_command_text": (
            "盘前指挥摘要\n\n"
            "这里先汇总今日主线、趋势延续、资金承接和消息催化，再给出开盘后的优先动作。"
        ),
        "overview_execution_text": (
            "执行路径\n\n"
            "这里集中展示买点、止损、目标、失效条件和跨页面联动建议，方便从总览直接进入执行。"
        ),
        "market_capital_text": (
            "资金画像\n\n"
            "刷新市场后，这里会补上净流入、换手、封单稳定性和资金承接质量。"
        ),
        "market_decision_text": (
            "买卖决策\n\n"
            "这里汇总主线地位、趋势状态、消息催化与执行建议，帮助快速判断该不该做。"
        ),
        "market_buy_text": (
            "买点提示\n\n"
            "市场刷新后，这里会告诉你今天更适合追强、低吸、承接还是继续等待。"
        ),
        "market_sell_text": (
            "卖点与减仓\n\n"
            "导入持仓或生成计划后，这里会给出防守位、减仓节奏和退出条件。"
        ),
        "market_breadth_text": (
            "消息催化摘要\n\n"
            "载入消息或刷新市场后，这里会整理最新催化、主题新闻和异动线索。"
        ),
        "market_theme_brief_text": (
            "主线摘要\n\n"
            "这里会汇总强势主题、趋势延续、切换预警和主线持续性。"
        ),
        "market_leaderboard_text": (
            "机会排行榜\n\n"
            "刷新市场后，这里会按主线、趋势、消息和风险排序展示当前最值得看的标的。"
        ),
        "market_source_status_text": (
            "数据源状态\n\n"
            "程序会在刷新市场后显示缓存命中、刷新时间和异常诊断。"
        ),
        "daily_pool_text": (
            "综合机会池\n\n"
            "这里会优先列出今日最值得盯的股票，包含主线角色、趋势状态、消息分和买卖点。"
        ),
        "trade_plan_text": (
            "今日交易计划\n\n"
            "先刷新机会池，再生成今日交易计划。这里会整理买点、仓位、风控位和盘中优先级。"
        ),
        "position_advice_text": (
            "持仓处理建议\n\n"
            "导入持仓后，这里会结合主线强弱、趋势变化、风险灯和盈亏结构给出处理建议。"
        ),
        "board_text": (
            "打板专项候选\n\n"
            "这里承接高弹性擒龙打板候选，作为专项模式使用，不与主工作台争主入口。"
        ),
        "board_monitor_text": (
            "炸板 / 回封监控\n\n"
            "这里持续跟踪回封、炸板、封单和情绪衰减，帮助你减少高波动误判。"
        ),
        "metrics_text": (
            "绩效面板\n\n"
            "加载样本或执行扫描后，这里会显示收益、回撤、胜率和阶段统计。"
        ),
        "broker_execution_text": (
            "执行回放\n\n"
            "提交模拟委托、刷新订单建议或同步券商状态后，这里会记录执行日志。"
        ),
        "detail_decision_text": (
            "个股决策画像\n\n"
            "选中股票后，这里会汇总主线地位、趋势状态、买卖区间和核心逻辑。"
        ),
        "detail_execution_text": (
            "执行回放\n\n"
            "这里会关联委托建议、提交结果和成交记录，帮助复盘执行有没有偏离计划。"
        ),
        "detail_conclusion_text": (
            "复盘结论\n\n"
            "这里沉淀单票的核心教训、下一步观察点，以及是否值得继续跟踪同主线标的。"
        ),
    }
    for attr_name, text in fill_texts.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            current = widget.toPlainText().strip()
            if not current or self._has_mojibake_text(current):
                self._set_plain_text_if_changed(widget, text)


def _qh_normalize_action_row_texts_v2(self: QuantHunterWindow) -> None:
    label_map = {
        "去看推荐": "查看机会池",
        "查看推荐": "查看机会池",
        "去看交易": "前往交易执行",
        "去交易页": "前往交易执行",
        "看观察池": "查看观察池",
        "看消息催化": "查看消息催化",
        "回到总览": "回到市场总览",
        "看总览": "回到市场总览",
        "定位推荐池": "定位机会池",
        "重算计划": "重算交易计划",
        "查看风险池": "查看风险池",
        "刷新监控": "刷新专项监控",
        "定位委托": "定位委托",
        "查看委托": "查看委托",
        "查看成交": "查看成交",
        "刷新诊断": "刷新诊断",
        "导出日志": "导出日志",
        "查看复盘": "查看复盘研究",
    }
    tooltip_map = {
        "查看机会池": "跳转到推荐页，继续查看高优先池、趋势机会和综合评分。",
        "查看消息催化": "切到消息催化视图，查看新闻、主题驱动和异动线索。",
        "回到市场总览": "回到总览页，继续查看市场结构、主线和趋势全景。",
        "前往交易执行": "跳转到交易页，查看委托建议、执行回放和提交入口。",
        "定位机会池": "把焦点定位到机会池表格，方便继续筛选和对比。",
        "重算交易计划": "重新生成今日交易计划、仓位预算和盘中节奏。",
        "查看观察池": "跳到观察池，查看仍在等待确认的标的。",
        "查看风险池": "查看高风险、减仓和退出建议。",
        "刷新专项监控": "刷新打板专项监控与回封观察焦点。",
        "定位委托": "定位到委托建议列表，优先检查待提交订单。",
        "查看委托": "查看委托表格和当前执行建议。",
        "查看成交": "查看提交记录、执行结果和成交回放。",
        "刷新诊断": "刷新运行日志、任务状态和诊断面板。",
        "导出日志": "导出当前运行日志，便于排查问题。",
        "查看复盘研究": "跳到复盘页，查看单票信号、成交和复盘结论。",
    }
    for row_name in [
        "overviewThemeActionRow",
        "overviewCapitalActionRow",
        "overviewDecisionActionRow",
        "scannerTopActionRow",
        "recommendPoolActionRow",
        "recommendPlanActionRow",
        "recommendPulseActionRow",
        "recommendHoldingActionRow",
        "boardCandidateActionRow",
        "boardMonitorActionRow",
        "brokerGateActionRow",
        "brokerExecutionActionRow",
        "brokerRecapActionRow",
        "runtimeLogActionRow",
        "detailMetricsActionRow",
        "detailDecisionActionRow",
        "detailExecutionActionRow",
        "detailConclusionActionRow",
    ]:
        row = self.findChild(QWidget, row_name)
        if row is None:
            continue
        for button in row.findChildren(QPushButton):
            text = (button.text() or "").strip()
            normalized = label_map.get(text, text)
            if normalized and normalized != text:
                self._set_label_text_if_changed(button, normalized)
            tip = tooltip_map.get(normalized)
            if tip:
                button.setToolTip(tip)


def _qh_apply_scroll_and_table_focus_v2(self: QuantHunterWindow) -> None:
    for attr_name in ["overview_scroll_area", "recommend_scroll_area", "broker_scroll_area"]:
        scroll = getattr(self, attr_name, None)
        if isinstance(scroll, QScrollArea):
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    if hasattr(self, "daily_pool_table"):
        self.daily_pool_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.daily_pool_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for column in [2, 10, 11, 13, 14, 15, 16, 17]:
            if column < self.daily_pool_table.columnCount():
                self.daily_pool_table.setColumnHidden(column, True)

    if hasattr(self, "trade_plan_table"):
        self.trade_plan_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.trade_plan_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for column in [2, 13]:
            if column < self.trade_plan_table.columnCount():
                self.trade_plan_table.setColumnHidden(column, True)

    if hasattr(self, "orders_table"):
        self.orders_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.orders_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        for column in [5, 6, 7, 8, 10]:
            if column < self.orders_table.columnCount():
                self.orders_table.setColumnHidden(column, True)

    if hasattr(self, "execution_table"):
        self.execution_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.execution_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    if hasattr(self, "theme_heat_table"):
        self.theme_heat_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    if hasattr(self, "leader_table"):
        self.leader_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    if hasattr(self, "position_advice_table"):
        self.position_advice_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.position_advice_table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)


def _qh_compact_overview_and_recommend_v3(self: QuantHunterWindow) -> None:
    if hasattr(self, "market_history_date_combo"):
        self.market_history_date_combo.hide()
    if hasattr(self, "market_history_reset_button"):
        self.market_history_reset_button.hide()

    for button_map_name in ["history_window_buttons", "market_overlay_buttons", "secondary_indicator_buttons"]:
        button_map = getattr(self, button_map_name, None) or {}
        for button in button_map.values():
            button.hide()

    if hasattr(self, "market_search_input"):
        self.market_search_input.setMaximumWidth(280)
    if hasattr(self, "market_refresh_button"):
        self.market_refresh_button.setMinimumWidth(148)
    if hasattr(self, "dashboard_auto_refresh_checkbox"):
        self._set_label_text_if_changed(self.dashboard_auto_refresh_checkbox, "盘中自动刷新")

    for button in getattr(self, "overview_quick_buttons", {}).values():
        button.setMinimumWidth(104)
        button.setMinimumHeight(38)

    for attr_name, max_height in {
        "overview_command_text": 118,
        "overview_execution_text": 118,
        "market_buy_text": 110,
        "market_sell_text": 110,
        "market_breadth_text": 118,
        "market_theme_brief_text": 118,
        "market_capital_text": 140,
        "market_decision_text": 140,
    }.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            widget.setMaximumHeight(max_height)

    if hasattr(self, "market_source_status_text"):
        self.market_source_status_text.hide()

    if hasattr(self, "daily_chart_view"):
        self.daily_chart_view.setMinimumHeight(320)
    if hasattr(self, "fund_chart_view"):
        self.fund_chart_view.setMinimumHeight(156)
    if hasattr(self, "momentum_chart_view"):
        self.momentum_chart_view.setMinimumHeight(156)
    if hasattr(self, "indicator_chart_view"):
        self.indicator_chart_view.setMinimumHeight(156)

    if hasattr(self, "daily_pool_table"):
        self.daily_pool_table.setColumnCount(24)
        self.daily_pool_table.setHorizontalHeaderLabels(
            ["状态", "标的", "ID", "交易码", "主线", "位次", "角色", "窗口", "风险", "总分", "热度", "强度", "延续", "龙头", "雷达", "接力", "低吸", "尾盘", "一日", "决策", "动作", "催化", "日期", "买卖价"]
        )
        for column in [20]:
            if column < self.daily_pool_table.columnCount():
                self.daily_pool_table.setColumnHidden(column, True)

    if hasattr(self, "trade_plan_table"):
        self.trade_plan_table.setColumnCount(16)
        self.trade_plan_table.setHorizontalHeaderLabels(
            ["状态", "标的", "ID", "交易码", "动作", "股票池", "分层", "准备度", "置信", "买点", "止损", "目标", "资金", "观察点", "执行提示", "说明"]
        )

    if hasattr(self, "position_advice_table"):
        self.position_advice_table.setColumnCount(11)
        self.position_advice_table.setHorizontalHeaderLabels(
            ["标的", "ID", "交易码", "动作", "主线", "置信度", "现价", "成本", "盈亏", "检查项", "处理"]
        )

    if hasattr(self, "orders_table"):
        self.orders_table.setHorizontalHeaderLabels(
            ["优先级", "交易码", "动作", "价格", "数量", "占用", "盈亏比", "止损", "目标", "主线闸门", "信号日期", "原因摘要", "风险灯"]
        )

    for attr_name, max_height in {
        "recommend_dispatch_text": 136,
        "recommend_focus_review_text": 136,
        "recommend_queue_text": 136,
        "daily_pool_text": 168,
        "trade_plan_text": 132,
        "market_pulse_text": 132,
        "position_advice_text": 150,
    }.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            widget.setMaximumHeight(max_height)

    if hasattr(self, "theme_heat_table"):
        self.theme_heat_table.setMinimumHeight(220)
    if hasattr(self, "leader_table"):
        self.leader_table.setMinimumHeight(220)


def _qh_mainline_signal_brief_v4(recommendation) -> str:
    if recommendation is None:
        return "待确认"
    flow_signal = str(getattr(recommendation, "mainline_flow_signal", "") or "").strip()
    stage = str(getattr(recommendation, "mainline_stage", "") or "").strip()
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "").strip()
    window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
    role = str(getattr(recommendation, "mainline_role", "") or "").strip()
    if flow_signal in {"延续偏强", "继续跟"} or stage in {"加速", "启动"}:
        return "继续跟"
    if flow_signal in {"延续待确认", "延续观察", "只观察"} or role in {"FOLLOW", "ASSIST"} or window_score >= 50:
        return "只观察"
    if risk_flag == "高" or flow_signal in {"切换预警", "切换/退潮", "防切换"} or stage in {"分歧", "退潮"}:
        return "防切换"
    return "只观察"


def _qh_signal_action_text_v4(recommendation) -> str:
    if recommendation is None:
        return "等待机会"
    action = str(getattr(recommendation, "action", "") or "").upper()
    action_map = {
        "BUY": "买入",
        "WATCH": "观察",
        "HOLD": "持有",
        "REDUCE": "减仓",
        "SELL": "卖出",
    }
    return action_map.get(action, "观察")


def _qh_compact_copy_v24(value: str, limit: int = 20) -> str:
    text = " ".join(str(value or "").replace("\n", " ").split())
    if len(text) <= limit:
        return text
    return f"{text[: max(limit - 1, 1)]}…"


def _qh_recommend_focus_reason_v24(self: QuantHunterWindow, recommendation) -> str:
    if recommendation is None:
        return "等待推荐逻辑同步。"
    theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
    strategy_name = getattr(recommendation, "primary_strategy", "") or "掘龙决策"
    role_name = self._display_mainline_role(getattr(recommendation, "mainline_role", "") or "") or "待确认"
    catalyst = _qh_compact_copy_v24(getattr(recommendation, "catalyst", "") or "等待消息强化", 18)
    rationale = _qh_compact_copy_v24(getattr(recommendation, "rationale", "") or "", 20)
    parts = [catalyst, f"{theme_name} | {role_name}", strategy_name]
    if rationale and rationale not in {catalyst, strategy_name}:
        parts.append(rationale)
    return " | ".join(part for part in parts if part) or "等待推荐逻辑同步。"


def _qh_recommend_execution_summary_v24(self: QuantHunterWindow, recommendation) -> tuple[str, str, bool, bool]:
    if recommendation is None:
        return ("等待结论", "先刷新机会池，再决定动作。", False, False)
    signal = _qh_mainline_signal_brief_v4(recommendation)
    action = str(getattr(recommendation, "action", "") or "").upper()
    action_text = _qh_signal_action_text_v4(recommendation)
    execution_status = str(getattr(recommendation, "execution_status", "") or "").strip()
    risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "").strip()
    readiness = float(getattr(recommendation, "execution_readiness", 0.0) or 0.0)
    if execution_status == "已提交":
        return ("已进入交易执行", "委托已提交，优先去交易页跟踪回执和成交。", False, True)
    if execution_status == "已送审":
        return ("等待送审确认", "已进入送审链路，优先跟踪确认结果。", False, True)
    if execution_status == "提交失败":
        return ("需要复核后重试", "送审或提交失败，先回看风险和委托参数。", True, True)
    if signal == "防切换" or action in {"SELL", "REDUCE"}:
        return ("先防守，处理风险", f"{action_text}优先，按风险计划处理。", action in {"SELL", "REDUCE"}, True)
    if action == "BUY" and signal == "继续跟" and risk_flag != "高" and readiness >= 55:
        return ("条件较齐，可以执行", "买点和主线同向，可进入送审或交易计划。", True, True)
    if action == "BUY":
        return ("先观察，等确认再动", "虽然进入候选，但主线或买点还没完全确认，暂不送审。", False, False)
    if action == "HOLD":
        return ("继续跟踪持仓", "持有逻辑还在，优先盯止损、承接和主线延续。", False, True)
    if action == "WATCH" or signal == "只观察":
        return ("进入观察名单", "先盯确认信号，不急着送审或下动作。", False, False)
    return (f"当前动作：{action_text}", "先结合风险和价位再决定下一步。", False, action != "WATCH")


def _qh_recommend_queue_snapshot_v25(self: QuantHunterWindow) -> dict[str, object]:
    rows = list(getattr(self, "daily_pool_rows", []) or [])
    execution_status_by_symbol = dict(getattr(self, "execution_status_by_symbol", {}) or {})
    buy_rows = [item for item in rows if str(getattr(item, "action", "") or "").upper() == "BUY"]
    pending_review = [
        item for item in buy_rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "待观察") == "待观察"
    ]
    reviewing = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "已送审"]
    submitted = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "已提交"]
    failed = [item for item in rows if execution_status_by_symbol.get(getattr(item, "symbol", ""), "") == "提交失败"]
    return {
        "pending_review": pending_review,
        "reviewing": reviewing,
        "submitted": submitted,
        "failed": failed,
    }


def _qh_review_sequence_items(items: list, limit: int = 2) -> str:
    names = []
    for item in items[:limit]:
        name = getattr(item, "stock_name", "") or getattr(item, "symbol", "") or "--"
        names.append(name)
    if not names:
        return "--"
    if len(items) > limit:
        names.append("…")
    return " / ".join(names)


def _qh_queue_sequence_summary(queue_snapshot: dict[str, object], max_preview: int = 2) -> str:
    sections = []
    for label, key in [
        ("待复核", "pending_review"),
        ("已送审", "reviewing"),
        ("提交失败", "failed"),
        ("已提交", "submitted"),
    ]:
        group = queue_snapshot.get(key) or []
        if not group:
            continue
        names = _qh_review_sequence_items(group, limit=max_preview)
        sections.append(f"{label} {len(group)} 只 ({names})")
    if not sections:
        return "暂无待复核票"
    return " | ".join(sections)


def _qh_next_review_target(queue_snapshot: dict[str, object]) -> str:
    for key in ["pending_review", "reviewing", "failed"]:
        group = queue_snapshot.get(key) or []
        if group:
            item = group[0]
            name = getattr(item, "stock_name", "") or getattr(item, "symbol", "")
            if name:
                return name
    return "暂无复核目标"


def _qh_set_note_panel_tone_v5(self: QuantHunterWindow, widget, tone: str) -> None:
    if widget is None:
        return
    current = widget.property("stateTone")
    if current != tone:
        widget.setProperty("stateTone", tone)
        widget.style().unpolish(widget)
        widget.style().polish(widget)


def _qh_apply_plan_table_visuals_v4(self: QuantHunterWindow) -> None:
    plan = getattr(self, "current_trade_plan", None)
    decisions = list(getattr(plan, "decisions", []) or [])
    table = getattr(self, "trade_plan_table", None)
    if not isinstance(table, QTableWidget):
        return
    for row_index, decision in enumerate(decisions):
        signal = _qh_mainline_signal_brief_v4(decision)
        action = str(getattr(decision, "action", "") or "").upper()
        if signal == "继续跟" and action == "BUY":
            bg = QColor("#E8F7EC")
            fg = QColor("#0F5132")
        elif signal == "防切换" or action in {"SELL", "REDUCE"}:
            bg = QColor("#FBEAEA")
            fg = QColor("#842029")
        else:
            bg = QColor("#FFF4DB")
            fg = QColor("#7C4A03")

        for column in [0, 4, 5, 6, 7, 8, 9, 14]:
            if column < table.columnCount():
                item = table.item(row_index, column)
                if item is not None:
                    item.setBackground(bg)
                    item.setForeground(fg)


def _qh_apply_position_advice_visuals_v4(self: QuantHunterWindow) -> None:
    rows = list(getattr(self, "current_position_advice", []) or [])
    table = getattr(self, "position_advice_table", None)
    if not isinstance(table, QTableWidget):
        return
    for row_index, advice in enumerate(rows):
        action = str(getattr(advice, "action", "") or "").upper()
        flow = str(getattr(advice, "mainline_flow_signal", "") or "").strip()
        if action in {"SELL", "REDUCE"} or flow in {"切换预警", "切换/退潮"}:
            bg = QColor("#FBEAEA")
            fg = QColor("#842029")
            brief = "退出" if action == "SELL" else "减仓"
        elif flow in {"延续偏强", "继续跟"} or action == "HOLD":
            bg = QColor("#E8F7EC")
            fg = QColor("#0F5132")
            brief = "继续持有"
        else:
            bg = QColor("#FFF4DB")
            fg = QColor("#7C4A03")
            brief = "只观察"

        for column in [0, 3, 4, 5, 9]:
            if column < table.columnCount():
                item = table.item(row_index, column)
                if item is not None:
                    item.setBackground(bg)
                    item.setForeground(fg)
                    if column == 9:
                        if item.text() != brief:
                            item.setText(brief)


def _qh_refresh_overview_focus_cards_v4(self: QuantHunterWindow, symbol: str, snapshot, recommendation) -> None:
    if not hasattr(self, "overview_summary_cards"):
        return
    if recommendation is not None:
        signal = _qh_mainline_signal_brief_v4(recommendation)
        action_text = _qh_signal_action_text_v4(recommendation)
        theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
        role_name = self._display_mainline_role(getattr(recommendation, "mainline_role", "") or "")
        catalyst = getattr(recommendation, "catalyst", "") or "等待消息强化"
        next_focus = getattr(recommendation, "next_focus", "") or "继续盯量能、承接和主线强度"
        risk_flag = getattr(recommendation, "mainline_risk_flag", "") or "待评估"
        self.overview_summary_cards["theme"].set_data(signal, f"{theme_name} | {role_name} | 位次 {getattr(recommendation, 'mainline_rank', '--')}")
        self.overview_summary_cards["source"].set_data("催化/风险", f"{catalyst[:12]} | 风险 {risk_flag}")
        self.overview_summary_cards["capital"].set_data("窗口/总分", f"窗口 {float(getattr(recommendation, 'mainline_window_score', 0.0) or 0.0):.1f} | 总分 {float(getattr(recommendation, 'total_score', 0.0) or 0.0):.1f}")
        self.overview_summary_cards["decision"].set_data(action_text, f"下一步 {next_focus[:20]}")
        return
    if snapshot is not None:
        pct = float(getattr(snapshot, "pct_change", 0.0) or 0.0)
        inflow = float(getattr(snapshot, "main_inflow", 0.0) or 0.0) / 1e8
        self.overview_summary_cards["theme"].set_data("市场快照", f"{snapshot.stock_name} | 热度 {float(getattr(snapshot, 'heat_score', 0.0) or 0.0):.1f}")
        self.overview_summary_cards["source"].set_data("题材/涨跌", f"{snapshot.strategy_tag or '未分类'} | 涨跌 {pct:.2f}%")
        self.overview_summary_cards["capital"].set_data("资金流", f"净流入 {inflow:.2f} 亿 | 换手 {float(getattr(snapshot, 'turnover', 0.0) or 0.0):.2f}%")
        self.overview_summary_cards["decision"].set_data("先观察", "下一步 先看量价承接")
        return
    stock_name = self._stock_name_for_symbol(symbol) if symbol else "等待标的同步"
    self.overview_summary_cards["theme"].set_data("等待主线", f"{stock_name} | 等待主线、趋势和消息同步")
    self.overview_summary_cards["source"].set_data("等待催化", "等待行情、消息和资金接入")
    self.overview_summary_cards["capital"].set_data("等待窗口", "下一步 先刷新市场")
    self.overview_summary_cards["decision"].set_data("先观察", "下一步 暂不做动作判断")


def _qh_refresh_recommend_focus_cards_v4(self: QuantHunterWindow, row: RecommendationRow | None = None) -> None:
    current = row or self._selected_daily_pool_recommendation()
    if current is None:
        return

    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    signal = _qh_mainline_signal_brief_v4(current)
    action_text = _qh_signal_action_text_v4(current)
    risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
    catalyst = getattr(current, "catalyst", "") or "等待消息强化"
    next_focus = getattr(current, "next_focus", "") or "继续盯量能、承接和主线延续"
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    confidence = float(getattr(current, "confidence_score", 0.0) or 0.0)
    role_name = self._display_mainline_role(getattr(current, "mainline_role", "") or "")
    strategy_name = getattr(current, "primary_strategy", "") or "掘龙决策"

    if hasattr(self, "recommend_summary_cards"):
        self.recommend_summary_cards["logic"].set_data(signal, f"{theme_name} | {role_name} | 风险灯 {risk_flag}")
        self.recommend_summary_cards["plan"].set_data(action_text, f"现在怎么做 {next_focus[:14]} | 准备 {readiness:.1f} | {strategy_name}")
        self.recommend_summary_cards["pulse"].set_data("为什么看它", f"{catalyst[:12]} | 主线窗口 {float(getattr(current, 'mainline_window_score', 0.0) or 0.0):.1f}")
        self.recommend_summary_cards["holding"].set_data("失效前盯什么", next_focus[:20])

    if hasattr(self, "priority_cards"):
        self.priority_cards["theme"].set_data(signal, f"焦点 {theme_name}", f"{role_name} | 风险 {risk_flag}")
        self.priority_cards["strategy"].set_data(strategy_name, f"焦点 {current.stock_name}", f"动作 {self._display_action(getattr(current, 'action', 'WATCH'))} | 催化 {catalyst[:10]}")
        self.priority_cards["focus"].set_data(action_text, f"焦点 {current.stock_name}", f"总分 {float(getattr(current, 'total_score', 0.0) or 0.0):.1f} | 准备 {readiness:.1f}")

    if hasattr(self, "alert_cards"):
        self.alert_cards["theme"].set_data(signal, f"{theme_name} | 风险 {risk_flag}")
        self.alert_cards["leader"].set_data(role_name, f"{current.stock_name} | 位次 {getattr(current, 'mainline_rank', '--')}")
        self.alert_cards["strategy"].set_data(strategy_name, f"催化 {catalyst[:12]}")
        self.alert_cards["action"].set_data(action_text, f"下一步 {next_focus[:18]}")


_ORIGINAL_QH_REFRESH_TRADE_PLAN_V4 = QuantHunterWindow._refresh_trade_plan


def _qh_refresh_trade_plan_v4(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_TRADE_PLAN_V4(self)
    self._apply_plan_table_visuals_v4()
    self._apply_position_advice_visuals_v4()


def _qh_populate_market_depth_texts_v5(self: QuantHunterWindow, rows: list) -> None:
    top_row = rows[0] if rows else None
    top_tone = (
        "buy"
        if top_row is not None and _qh_mainline_signal_brief_v4(top_row) == "继续跟"
        else ("risk" if top_row is not None and _qh_mainline_signal_brief_v4(top_row) == "防切换" else "watch")
    )

    if hasattr(self, "market_buy_text"):
        self._set_note_panel_tone_v5(self.market_buy_text, top_tone if top_row is not None else "idle")
        if top_row is not None:
            self._set_plain_text_if_changed(
                self.market_buy_text,
                "\n".join(
                    [
                        "买点信号",
                        f"结论：{_qh_signal_action_text_v4(top_row)}",
                        f"焦点：{top_row.stock_name} | {_qh_mainline_signal_brief_v4(top_row)}",
                        f"观察：{getattr(top_row, 'next_focus', '') or '量能、承接、窗口是否继续抬升'}",
                    ]
                ),
            )
        else:
            self._set_plain_text_if_changed(self.market_buy_text, "买点信号\n结论：先观察\n等待主线、趋势和量价同步。")

    if hasattr(self, "market_sell_text"):
        weak_row = next((row for row in rows if float(getattr(row, "pct_change", 0.0) or 0.0) < 0), top_row)
        self._set_note_panel_tone_v5(self.market_sell_text, "risk" if weak_row is not None else "idle")
        if weak_row is not None:
            risk_text = getattr(weak_row, "mainline_risk_flag", "") or "待评估"
            self._set_plain_text_if_changed(
                self.market_sell_text,
                "\n".join(
                    [
                        "卖点/防守",
                        f"风险：{risk_text}",
                        f"焦点：{weak_row.stock_name} | {float(getattr(weak_row, 'pct_change', 0.0) or 0.0):.2f}%",
                        "动作：若主线切换或跌破防守位，优先减仓。",
                    ]
                ),
            )
        else:
            self._set_plain_text_if_changed(self.market_sell_text, "卖点/防守\n结论：暂无明显卖点\n先盯主线是否出现切换。")

    if hasattr(self, "market_breadth_text"):
        self._set_note_panel_tone_v5(self.market_breadth_text, "watch" if top_row is not None else "idle")
        if top_row is not None:
            symbol_news = self.news_catalysts.get(top_row.symbol, [])
            title = symbol_news[0].title if symbol_news else (getattr(top_row, "catalyst", "") or "暂无新增强催化")
            self._set_plain_text_if_changed(
                self.market_breadth_text,
                "\n".join(
                    [
                        "消息催化",
                        f"焦点：{top_row.stock_name}",
                        f"催化：{title[:28]}",
                        "处理：只保留会影响买卖点的消息。",
                    ]
                ),
            )
        else:
            self._set_plain_text_if_changed(self.market_breadth_text, "消息催化\n结论：暂无新增催化\n先看价格与资金。")


def _qh_refresh_overview_side_panels_v5(self: QuantHunterWindow, rows: list) -> None:
    self._render_leaderboard_cards(rows)

    if hasattr(self, "market_theme_brief_text"):
        self._set_note_panel_tone_v5(self.market_theme_brief_text, _qh_mainline_signal_brief_v4(rows[0]).replace("继续跟", "buy").replace("只观察", "watch").replace("防切换", "risk") if rows else "idle")
        if rows:
            theme_counter: dict[str, int] = {}
            for row in rows:
                theme_name = getattr(row, "mainline_tag", "") or getattr(row, "theme_name", "") or getattr(row, "strategy_tag", "") or "未分类"
                theme_counter[theme_name] = theme_counter.get(theme_name, 0) + 1
            ranked = sorted(theme_counter.items(), key=lambda item: item[1], reverse=True)
            top_theme, top_count = ranked[0]
            follow_text = rows[1].stock_name if len(rows) > 1 else rows[0].stock_name
            self._set_plain_text_if_changed(
                self.market_theme_brief_text,
                "\n".join(
                    [
                        "主线摘要",
                        f"主线：{top_theme} | 前排 {top_count} 只",
                        f"焦点：{rows[0].stock_name} | 跟踪：{follow_text}",
                        f"结论：{_qh_mainline_signal_brief_v4(rows[0])}",
                    ]
                ),
            )
        else:
            self._set_plain_text_if_changed(self.market_theme_brief_text, "主线摘要\n结论：等待主线同步\n先建立市场快照，再确认主线强弱。")

    self._refresh_market_source_status()


def _qh_update_market_text_panels_v5(self: QuantHunterWindow, symbol: str, snapshot, recommendation) -> None:
    stock_name = getattr(recommendation, "stock_name", "") or getattr(snapshot, "stock_name", "") or self._stock_name_for_symbol(symbol) or "等待标的同步"
    signal = _qh_mainline_signal_brief_v4(recommendation) if recommendation is not None else "先观察"
    action_text = _qh_signal_action_text_v4(recommendation) if recommendation is not None else "等待机会"
    tone = {"继续跟": "buy", "只观察": "watch", "防切换": "risk"}.get(signal, "idle")
    theme_name = (
        getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or getattr(snapshot, "strategy_tag", "") or "待确认"
    )
    catalyst = getattr(recommendation, "catalyst", "") or "等待消息与资金共振"
    if snapshot is not None:
        capital_line = f"资金：{float(getattr(snapshot, 'main_inflow', 0.0) or 0.0) / 1e8:.2f} 亿 | 换手 {float(getattr(snapshot, 'turnover', 0.0) or 0.0):.2f}%"
        price_line = f"价格：{float(getattr(snapshot, 'pct_change', 0.0) or 0.0):.2f}% | 热度 {float(getattr(snapshot, 'heat_score', 0.0) or 0.0):.1f}"
    else:
        capital_line = "资金：等待行情同步"
        price_line = "价格：等待行情同步"

    if hasattr(self, "overview_command_text"):
        self._set_note_panel_tone_v5(self.overview_command_text, tone)
        self._set_plain_text_if_changed(
            self.overview_command_text,
            "\n".join(
                [
                    "盘前指挥",
                    f"焦点：{stock_name}",
                    f"主线：{theme_name} | 信号：{signal}",
                    f"动作：{action_text}",
                ]
            ),
        )

    if hasattr(self, "overview_execution_text"):
        self._set_note_panel_tone_v5(self.overview_execution_text, tone)
        self._set_plain_text_if_changed(
            self.overview_execution_text,
            "\n".join(
                [
                    "执行路径",
                    price_line,
                    capital_line,
                    f"下一步：{getattr(recommendation, 'next_focus', '') or '继续盯量能、承接和风险灯'}",
                ]
            ),
        )

    if hasattr(self, "market_capital_text"):
        self._set_note_panel_tone_v5(self.market_capital_text, tone)
        self._set_plain_text_if_changed(
            self.market_capital_text,
            "\n".join(
                [
                    "资金画像",
                    f"结论：{signal}",
                    f"风险：{capital_line}",
                    f"下一步：{catalyst[:28] or '等待消息与资金共振'}",
                ]
            ),
        )

    if hasattr(self, "market_decision_text"):
        self._set_note_panel_tone_v5(self.market_decision_text, tone)
        risk_flag = getattr(recommendation, "mainline_risk_flag", "") or "待评估"
        self._set_plain_text_if_changed(
            self.market_decision_text,
            "\n".join(
                [
                    "买卖决策",
                    f"结论：{action_text}",
                    f"风险：{risk_flag}",
                    f"下一步：{getattr(recommendation, 'next_focus', '') or '是否继续维持主线前排'}",
                ]
            ),
        )


def _qh_refresh_recommend_story_panels_v5(self: QuantHunterWindow, row=None) -> None:
    current = row or self._selected_daily_pool_recommendation()
    if current is None:
        if hasattr(self, "daily_pool_text"):
            self._set_note_panel_tone_v5(self.daily_pool_text, "idle")
            self._set_plain_text_if_changed(self.daily_pool_text, "综合机会池\n结论：等待候选同步\n先生成机会池，再看焦点票。")
        if hasattr(self, "strategy_path_text"):
            self._set_note_panel_tone_v5(self.strategy_path_text, "idle")
            self._set_plain_text_if_changed(self.strategy_path_text, "主线推演\n结论：等待推演同步\n先确认主线，再决定动作。")
        self._refresh_recommend_bucket_panels(None)
        return

    signal = _qh_mainline_signal_brief_v4(current)
    tone = {"继续跟": "buy", "只观察": "watch", "防切换": "risk"}.get(signal, "idle")
    action_text = _qh_signal_action_text_v4(current)
    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    role_name = self._display_mainline_role(getattr(current, "mainline_role", "") or "")
    catalyst = getattr(current, "catalyst", "") or "等待催化强化"
    next_focus = getattr(current, "next_focus", "") or "继续盯量能、承接和主线延续"

    if hasattr(self, "daily_pool_text"):
        self._set_note_panel_tone_v5(self.daily_pool_text, tone)
        self._set_plain_text_if_changed(
            self.daily_pool_text,
            "\n".join(
                [
                    "综合机会池",
                    f"焦点：{current.stock_name} | {theme_name}",
                    f"结论：{signal} / {action_text}",
                    f"催化：{catalyst[:26]}",
                ]
            ),
        )

    if hasattr(self, "strategy_path_text"):
        self._set_note_panel_tone_v5(self.strategy_path_text, tone)
        self._set_plain_text_if_changed(
            self.strategy_path_text,
            "\n".join(
                [
                    "主线推演",
                    f"角色：{role_name} | 位次 {getattr(current, 'mainline_rank', '--')}",
                    f"窗口：{float(getattr(current, 'mainline_window_score', 0.0) or 0.0):.1f} | 风险 {getattr(current, 'mainline_risk_flag', '') or '待评估'}",
                    f"下一步：{next_focus[:28]}",
                ]
            ),
        )

    self._refresh_recommend_bucket_panels(current)


def _qh_compact_signal_panels_v6(self: QuantHunterWindow) -> None:
    panel_heights = {
        "recommend_core_bucket_text": 112,
        "recommend_watch_bucket_text": 112,
        "recommend_risk_bucket_text": 112,
        "recommend_review_text": 120,
        "recommend_next_day_text": 120,
        "broker_gate_summary_text": 108,
        "broker_mainline_review_text": 126,
        "broker_execution_text": 126,
        "broker_order_focus_text": 170,
        "broker_recap_text": 116,
    }
    for attr_name, height in panel_heights.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            widget.setMinimumHeight(height)
            widget.setMaximumHeight(height)
            widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)


def _qh_sync_signal_panel_tones_v6(self: QuantHunterWindow) -> None:
    current = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
    recommend_tone = {"继续跟": "buy", "只观察": "watch", "防切换": "risk"}.get(_qh_mainline_signal_brief_v4(current), "idle")

    for attr_name, tone in {
        "recommend_core_bucket_text": "buy",
        "recommend_watch_bucket_text": "watch",
        "recommend_risk_bucket_text": "risk",
        "recommend_review_text": recommend_tone,
        "recommend_next_day_text": recommend_tone,
    }.items():
        widget = getattr(self, attr_name, None)
        if widget is not None:
            self._set_note_panel_tone_v5(widget, tone)

    summary = getattr(self, "last_broker_execution_summary", {}) or {}
    blockers = list(summary.get("blockers", []) or [])
    warnings = list(summary.get("warnings", []) or [])
    pending_orders = len(getattr(self, "order_intents", []) or [])
    if blockers:
        broker_tone = "risk"
    elif warnings or pending_orders:
        broker_tone = "watch"
    else:
        broker_tone = "buy" if getattr(self, "order_submission_records", []) else "idle"

    for attr_name in [
        "broker_gate_summary_text",
        "broker_mainline_review_text",
        "broker_execution_text",
        "broker_order_focus_text",
        "broker_recap_text",
    ]:
        widget = getattr(self, attr_name, None)
        if widget is not None:
            self._set_note_panel_tone_v5(widget, broker_tone)


def _qh_signal_next_step_v7(action: str, execution_status: str = "") -> str:
    normalized_action = str(action or "").upper()
    normalized_status = str(execution_status or "").strip()
    if normalized_status == "已提交":
        return "跟踪成交"
    if normalized_status == "已送审":
        return "等待确认"
    if normalized_status == "提交失败":
        return "重新复核"
    return {
        "BUY": "优先送审",
        "WATCH": "继续观察",
        "HOLD": "继续持有",
        "REDUCE": "优先减仓",
        "SELL": "优先退出",
    }.get(normalized_action, "等待确认")


def _qh_groupbox_for_widget_v7(widget) -> QGroupBox | None:
    parent = widget.parentWidget() if widget is not None else None
    while parent is not None and not isinstance(parent, QGroupBox):
        parent = parent.parentWidget()
    return parent if isinstance(parent, QGroupBox) else None


def _qh_set_label_text_v7(self: QuantHunterWindow, widget, text: str) -> None:
    if widget is None:
        return
    if hasattr(self, "_set_label_text_if_changed"):
        self._set_label_text_if_changed(widget, text)
    elif hasattr(widget, "setText"):
        current_attr = getattr(widget, "text", None)
        current = current_attr() if callable(current_attr) else current_attr
        if current != text:
            widget.setText(text)


def _qh_set_tooltip_v7(widget, text: str) -> None:
    if widget is None:
        return
    setter = getattr(widget, "setToolTip", None)
    if callable(setter):
        setter(text)


def _qh_apply_focus_dashboard_v7(self: QuantHunterWindow) -> None:
    if hasattr(self, "recommend_focus_metric_cards"):
        card_titles = {
            "symbol": "标的",
            "theme": "主线状态",
            "action": "执行动作",
            "execution": "链路阶段",
        }
        for key, title in card_titles.items():
            card = self.recommend_focus_metric_cards.get(key)
            if card is not None and hasattr(card, "title_label"):
                self._set_label_text_if_changed(card.title_label, title)
        card = self.recommend_focus_metric_cards.get("symbol")
        box = _qh_groupbox_for_widget_v7(card)
        if box is not None:
            if box.title() != "推荐焦点":
                box.setTitle("推荐焦点")

    if hasattr(self, "broker_order_metric_cards"):
        card_titles = {
            "symbol": "标的",
            "gate": "主线闸门",
            "risk": "风险灯",
            "position": "仓位变化",
        }
        for key, title in card_titles.items():
            card = self.broker_order_metric_cards.get(key)
            if card is not None and hasattr(card, "title_label"):
                self._set_label_text_if_changed(card.title_label, title)

    if hasattr(self, "daily_pool_focus_label"):
        current = self.daily_pool_focus_label.text().strip()
        if not current or "当前焦点" in current:
            _qh_set_label_text_v7(self, self.daily_pool_focus_label, RECOMMEND_DEFAULT_FOCUS_TEXT)
    if hasattr(self, "trade_plan_focus_label"):
        current = self.trade_plan_focus_label.text().strip()
        if not current or "今日第一计划" in current:
            _qh_set_label_text_v7(self, self.trade_plan_focus_label, TRADE_PLAN_DEFAULT_FOCUS_TEXT)
    if hasattr(self, "orders_focus_label"):
        current = self.orders_focus_label.text().strip()
        if not current or "委托动作面板" in current:
            _qh_set_label_text_v7(self, self.orders_focus_label, ORDERS_DEFAULT_FOCUS_TEXT)


_ORIGINAL_QH_REFRESH_WORKSPACE_STATUS_LABELS_V6 = QuantHunterWindow._refresh_workspace_status_labels


def _qh_refresh_workspace_status_labels_v7(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_WORKSPACE_STATUS_LABELS_V6(self)
    self._apply_focus_dashboard_v7()
    self._sync_signal_panel_tones_v6()


_ORIGINAL_QH_REFRESH_RECOMMEND_STORY_PANELS_V6 = QuantHunterWindow._refresh_recommend_story_panels


def _qh_refresh_recommend_story_panels_v6(self: QuantHunterWindow, row=None) -> None:
    _ORIGINAL_QH_REFRESH_RECOMMEND_STORY_PANELS_V6(self, row)
    self._sync_signal_panel_tones_v6()


def _qh_refresh_recommend_story_panels_v7(self: QuantHunterWindow, row=None) -> None:
    current = row or self._selected_daily_pool_recommendation()
    if current is None:
        if hasattr(self, "daily_pool_text"):
            self._set_note_panel_tone_v5(self.daily_pool_text, "idle")
            self._set_plain_text_if_changed(
                self.daily_pool_text,
                "综合机会池\n结论：等待机会池生成\n风险：暂无焦点风险\n下一步：先刷新市场，再生成机会池。",
            )
        if hasattr(self, "strategy_path_text"):
            self._set_note_panel_tone_v5(self.strategy_path_text, "idle")
            self._set_plain_text_if_changed(
                self.strategy_path_text,
                "主线推演\n结论：等待主线确认\n风险：暂无主线风险\n下一步：先确认主线，再决定动作。",
            )
        self._refresh_recommend_bucket_panels(None)
        self._sync_signal_panel_tones_v6()
        return

    signal = _qh_mainline_signal_brief_v4(current)
    tone = {"继续跟": "buy", "只观察": "watch", "防切换": "risk"}.get(signal, "idle")
    action_text = _qh_signal_action_text_v4(current)
    verdict, execution_summary, _, _ = _qh_recommend_execution_summary_v24(self, current)
    focus_reason = _qh_recommend_focus_reason_v24(self, current)
    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    role_name = self._display_mainline_role(getattr(current, "mainline_role", "") or "")
    risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
    next_focus = getattr(current, "next_focus", "") or "继续盯量能、承接和主线延续"
    invalidation = getattr(current, "invalidation_reason", "") or "跌破防守位或主线切换时重新评估"

    if hasattr(self, "daily_pool_text"):
        self._set_note_panel_tone_v5(self.daily_pool_text, tone)
        self._set_plain_text_if_changed(
            self.daily_pool_text,
            "\n".join(
                [
                    "综合机会池",
                    f"结论：{current.stock_name} | {verdict}",
                    f"主线/动作：{signal} | {execution_summary}",
                    f"风险：{theme_name} | {risk_flag} | {invalidation[:18]}",
                    f"下一步：{focus_reason[:18]} | {next_focus[:18]}",
                ]
            ),
        )

    if hasattr(self, "strategy_path_text"):
        self._set_note_panel_tone_v5(self.strategy_path_text, tone)
        self._set_plain_text_if_changed(
            self.strategy_path_text,
            "\n".join(
                [
                    "主线推演",
                    f"结论：{theme_name} | {role_name} | 第 {getattr(current, 'mainline_rank', '--')} 位",
                    f"风险：窗口 {float(getattr(current, 'mainline_window_score', 0.0) or 0.0):.1f} | {risk_flag}",
                    f"下一步：{next_focus[:28]}",
                ]
            ),
        )

    self._refresh_recommend_bucket_panels(current)
    self._sync_signal_panel_tones_v6()


_ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_CARDS_V7 = _qh_refresh_recommend_focus_cards_v4


def _qh_refresh_recommend_focus_cards_v7(self: QuantHunterWindow, row: RecommendationRow | None = None) -> None:
    _ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_CARDS_V7(self, row)
    current = row or (self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None)
    if current is None:
        if hasattr(self, "daily_pool_focus_label"):
            self._set_label_text_if_changed(self.daily_pool_focus_label, RECOMMEND_DEFAULT_FOCUS_TEXT)
        return

    signal = _qh_mainline_signal_brief_v4(current)
    action_text = _qh_signal_action_text_v4(current)
    next_step = _qh_signal_next_step_v7(getattr(current, "action", ""), getattr(current, "execution_status", ""))
    theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
    role_name = self._display_mainline_role(getattr(current, "mainline_role", "") or "")
    readiness = float(getattr(current, "execution_readiness", 0.0) or 0.0)
    risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"

    if hasattr(self, "recommend_focus_metric_labels"):
        payload = {
            "symbol": (current.stock_name, f"{current.stock_id} / {current.symbol}"),
            "theme": (signal, f"{theme_name} | {role_name}"),
            "action": (action_text, f"准备 {readiness:.1f} | 风险 {risk_flag}"),
            "execution": (next_step, f"送审 {getattr(current, 'execution_status', '') or '待观察'}"),
        }
        for key, (value, accent) in payload.items():
            if key in self.recommend_focus_metric_labels:
                _qh_set_label_text_v7(self, self.recommend_focus_metric_labels[key], value)
            if hasattr(self, "recommend_focus_metric_accents") and key in self.recommend_focus_metric_accents:
                _qh_set_label_text_v7(self, self.recommend_focus_metric_accents[key], accent)

    if hasattr(self, "daily_pool_focus_label"):
        execution_state = getattr(current, "execution_status", "") or "待观察"
        _qh_set_label_text_v7(
            self,
            self.daily_pool_focus_label,
            f"推荐焦点：{current.stock_name} | 主线 {signal} | 动作 {action_text} | 链路 {execution_state}",
        )


_ORIGINAL_QH_REFRESH_TRADE_PLAN_V7 = _qh_refresh_trade_plan_v4


def _qh_refresh_trade_plan_v5(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_TRADE_PLAN_V7(self)
    plan = getattr(self, "current_trade_plan", None)
    decision = None
    if plan is not None:
        decisions = list(getattr(plan, "decisions", []) or [])
        decision = decisions[0] if decisions else None
    if decision is None:
        if hasattr(self, "trade_plan_focus_label"):
            _qh_set_label_text_v7(self, self.trade_plan_focus_label, TRADE_PLAN_DEFAULT_FOCUS_TEXT)
        return

    signal = _qh_mainline_signal_brief_v4(decision)
    action = str(getattr(decision, "action", "") or "").upper()
    focus_state = "可执行" if action == "BUY" else ("观察中" if action == "WATCH" else "风险抬升")
    flow_state = "待送审" if action == "BUY" else ("等确认" if action == "WATCH" else "暂缓执行")
    recommendation = next(
        (item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == getattr(decision, "symbol", "")),
        None,
    )
    one_day_grade = one_day_hold_grade(recommendation) if recommendation is not None else ""
    if hasattr(self, "trade_plan_focus_label"):
        label_text = (
            f"计划焦点：{decision.stock_name} | 隔日 {one_day_grade} | {focus_state} | {flow_state} | {signal}"
            if one_day_grade
            else f"计划焦点：{decision.stock_name} | {focus_state} | {flow_state} | {signal}"
        )
        _qh_set_label_text_v7(self, self.trade_plan_focus_label, label_text)


_ORIGINAL_QH_REFRESH_BROKER_ORDER_FOCUS_V7 = QuantHunterWindow._refresh_broker_order_focus


def _qh_refresh_broker_order_focus_v7(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_BROKER_ORDER_FOCUS_V7(self)
    intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    if intent is None:
        if hasattr(self, "orders_focus_label"):
            _qh_set_label_text_v7(self, self.orders_focus_label, ORDERS_DEFAULT_FOCUS_TEXT)
        return

    recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == intent.symbol), None)
    signal = _qh_mainline_signal_brief_v4(recommendation)
    risk_lamp = self._broker_risk_lamp_for_intent(intent, recommendation=recommendation) if hasattr(self, "_broker_risk_lamp_for_intent") else "黄灯"
    action_label = self._broker_focus_action_label(intent, risk_lamp, blockers=[], warnings=[], preview_row={}, allowed=True)
    next_step = _qh_signal_next_step_v7(getattr(intent, "side", ""), "")
    available_qty = next((getattr(item, "available", None) for item in getattr(self, "holdings", []) if getattr(item, "symbol", "") == intent.symbol), None)

    if hasattr(self, "broker_order_metric_labels"):
        _qh_set_label_text_v7(self, self.broker_order_metric_labels["symbol"], self._stock_name_for_symbol(intent.symbol))
        _qh_set_label_text_v7(self, self.broker_order_metric_accents["symbol"], f"{self._stock_id_for_symbol(intent.symbol)} / {intent.symbol}")
        _qh_set_label_text_v7(self, self.broker_order_metric_labels["gate"], signal)
        _qh_set_label_text_v7(
            self,
            self.broker_order_metric_accents["gate"],
            getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认",
        )
        _qh_set_label_text_v7(self, self.broker_order_metric_labels["risk"], risk_lamp)
        _qh_set_label_text_v7(self, self.broker_order_metric_accents["risk"], action_label)
        _qh_set_label_text_v7(self, self.broker_order_metric_labels["position"], next_step)
        _qh_set_label_text_v7(
            self,
            self.broker_order_metric_accents["position"],
            f"可卖 {available_qty}" if available_qty is not None else "等待持仓同步",
        )

    if hasattr(self, "orders_focus_label"):
        side = str(getattr(intent, "side", "") or "").upper()
        submission_state = "待送审" if side == "BUY" else ("等回执" if getattr(intent, "status", "") in {"submitted", "submitted_pending"} else "先处理阻塞")
        chain_state = "买入建议已生成" if side == "BUY" else ("委托已送审" if submission_state == "等回执" else "回执异常")
        focus_price = float(getattr(intent, "price", 0.0) or 0.0)
        plan_brief = ""
        if recommendation is not None and hasattr(self, "_recommend_price_brief"):
            plan_brief = self._recommend_price_brief(recommendation)
        _qh_set_label_text_v7(
            self,
            self.orders_focus_label,
            f"委托焦点：{self._stock_name_for_symbol(intent.symbol)} | {chain_state} | {submission_state} | 状态 {signal} | 下一步 {next_step}",
        )
        _qh_set_tooltip_v7(
            self.orders_focus_label,
            "\n".join(
                [
                    f"标的：{self._stock_name_for_symbol(intent.symbol)} ({self._stock_id_for_symbol(intent.symbol)} / {intent.symbol})",
                    f"委托方向：{self._display_action(side) if hasattr(self, '_display_action') else side}",
                    f"主线状态：{signal}",
                    f"风险灯：{risk_lamp}",
                    f"委托价格：{focus_price:.2f}",
                    f"数量：{int(getattr(intent, 'quantity', 0) or 0)}",
                    f"价格计划：{plan_brief or '等待推荐价格带同步'}",
                    f"下一步：{next_step}",
                ]
            ),
        )


def _qh_reorder_broker_primary_flow_v2(self: QuantHunterWindow) -> None:
    content = self.broker_scroll_area.widget() if hasattr(self, "broker_scroll_area") else None
    layout = content.layout() if content is not None else None
    middle = getattr(self, "broker_middle_splitter", None)
    control = getattr(self, "broker_control_splitter", None)
    if not isinstance(layout, QVBoxLayout) or middle is None or control is None:
        return
    layout.removeWidget(middle)
    layout.insertWidget(4, middle, stretch=2)


def _qh_post_build_ui_tweaks_v2(self: QuantHunterWindow) -> None:
    _qh_post_build_ui_tweaks(self)
    if hasattr(self, "tabs") and isinstance(self.tabs, QTabWidget):
        self.tabs.tabBar().hide()
    self._normalize_overview_builder_texts()
    self._normalize_recommend_workspace_texts()
    self._normalize_board_workspace_texts()
    self._normalize_aux_workspace_texts()
    self._prime_recommend_workspace_defaults()
    self._hydrate_empty_workspace_panels()
    self._repair_runtime_widget_texts()
    self._normalize_action_row_texts()
    self._apply_scroll_and_table_focus_v2()
    self._compact_overview_and_recommend_v3()
    self._compact_signal_panels_v6()
    self._reorder_broker_primary_flow_v2()
    self._apply_focus_dashboard_v7()
    self._sync_signal_panel_tones_v6()


QuantHunterWindow._workspace_badge_text = _qh_workspace_badge_text_v2
QuantHunterWindow._normalize_recommend_workspace_texts = _qh_normalize_recommend_workspace_texts_v2
QuantHunterWindow._normalize_board_workspace_texts = _qh_normalize_board_workspace_texts_v2
QuantHunterWindow._repair_runtime_widget_texts = _qh_repair_runtime_widget_texts_v2
QuantHunterWindow._normalize_overview_builder_texts = _qh_normalize_overview_builder_texts_v2
QuantHunterWindow._normalize_aux_workspace_texts = _qh_normalize_aux_workspace_texts_v2
QuantHunterWindow._prime_recommend_workspace_defaults = _qh_prime_recommend_workspace_defaults_v2
QuantHunterWindow._hydrate_empty_workspace_panels = _qh_hydrate_empty_workspace_panels_v2
QuantHunterWindow._normalize_action_row_texts = _qh_normalize_action_row_texts_v2
QuantHunterWindow._apply_scroll_and_table_focus_v2 = _qh_apply_scroll_and_table_focus_v2
QuantHunterWindow._compact_overview_and_recommend_v3 = _qh_compact_overview_and_recommend_v3
QuantHunterWindow._apply_plan_table_visuals_v4 = _qh_apply_plan_table_visuals_v4
QuantHunterWindow._apply_position_advice_visuals_v4 = _qh_apply_position_advice_visuals_v4
QuantHunterWindow._set_note_panel_tone_v5 = _qh_set_note_panel_tone_v5
QuantHunterWindow._compact_signal_panels_v6 = _qh_compact_signal_panels_v6
QuantHunterWindow._sync_signal_panel_tones_v6 = _qh_sync_signal_panel_tones_v6
QuantHunterWindow._apply_focus_dashboard_v7 = _qh_apply_focus_dashboard_v7
QuantHunterWindow._reorder_broker_primary_flow_v2 = _qh_reorder_broker_primary_flow_v2
QuantHunterWindow._populate_market_depth_texts = _qh_populate_market_depth_texts_v5
QuantHunterWindow._refresh_overview_side_panels = _qh_refresh_overview_side_panels_v5
QuantHunterWindow._update_market_text_panels = _qh_update_market_text_panels_v5
QuantHunterWindow._refresh_overview_focus_cards = _qh_refresh_overview_focus_cards_v4
QuantHunterWindow._refresh_recommend_focus_cards = _qh_refresh_recommend_focus_cards_v7
QuantHunterWindow._refresh_recommend_story_panels = _qh_refresh_recommend_story_panels_v7
QuantHunterWindow._refresh_trade_plan = _qh_refresh_trade_plan_v5
QuantHunterWindow._refresh_broker_order_focus = _qh_refresh_broker_order_focus_v7
QuantHunterWindow._refresh_workspace_status_labels = _qh_refresh_workspace_status_labels_v7
QuantHunterWindow._post_build_ui_tweaks = _qh_post_build_ui_tweaks_v2


def _qh_apply_commercial_table_layout_v8(self: QuantHunterWindow) -> None:
    table_specs = {
        "daily_pool_table": {
            "hidden": [20],
            "widths": {0: 74, 1: 164, 2: 88, 3: 112, 4: 128, 5: 84, 6: 92, 7: 96, 8: 84, 9: 84, 18: 84, 19: 210, 22: 128},
            "stretch_column": 19,
            "min_height": 320,
        },
        "trade_plan_table": {
            "hidden": [13],
            "widths": {0: 74, 1: 164, 2: 88, 3: 112, 4: 84, 5: 128, 6: 92, 7: 92, 8: 84, 9: 92, 10: 92, 11: 92, 12: 92, 14: 280},
            "stretch_column": 14,
            "min_height": 280,
        },
        "orders_table": {
            "hidden": [5, 6, 7, 8, 10],
            "widths": {0: 84, 1: 122, 2: 84, 3: 90, 4: 82, 9: 118, 11: 360, 12: 88},
            "stretch_column": 11,
            "min_height": 320,
        },
        "execution_table": {
            "widths": {0: 144, 1: 88, 2: 88, 3: 112, 4: 84, 5: 90, 6: 84, 7: 118, 8: 320},
            "stretch_column": 8,
            "min_height": 280,
        },
        "board_table": {
            "widths": {0: 220, 1: 96, 2: 122, 3: 88, 4: 84, 5: 84, 6: 84, 7: 116, 8: 96, 9: 102, 10: 92, 11: 92},
            "stretch_column": 7,
            "min_height": 250,
        },
        "board_monitor_table": {
            "widths": {0: 220, 1: 96, 2: 122, 3: 110, 4: 84, 5: 84, 6: 96, 7: 96, 8: 144, 9: 240},
            "stretch_column": 9,
            "min_height": 250,
        },
        "scan_table": {
            "widths": {0: 84, 1: 164, 2: 88, 3: 112, 4: 92, 5: 92, 6: 96, 7: 90, 8: 90, 9: 280},
            "stretch_column": 9,
            "min_height": 280,
        },
        "monitor_table": {
            "widths": {0: 164, 1: 88, 2: 112, 3: 108, 4: 88, 5: 88, 6: 220},
            "stretch_column": 6,
            "min_height": 240,
        },
    }

    for attr_name, spec in table_specs.items():
        table = getattr(self, attr_name, None)
        if not isinstance(table, QTableWidget):
            continue

        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        if "min_height" in spec:
            table.setMinimumHeight(spec["min_height"])

        header = table.horizontalHeader()
        header.setMinimumSectionSize(56)
        header.setStretchLastSection(False)
        for column in range(table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Interactive)

        for column in spec.get("hidden", []):
            if column < table.columnCount():
                table.setColumnHidden(column, True)
        for column, width in spec.get("widths", {}).items():
            if column < table.columnCount():
                table.setColumnHidden(column, False)
                table.setColumnWidth(column, width)

        stretch_column = spec.get("stretch_column")
        if isinstance(stretch_column, int) and stretch_column < table.columnCount():
            header.setSectionResizeMode(stretch_column, QHeaderView.Stretch)


def _qh_balance_workspace_splitters_v8(self: QuantHunterWindow) -> None:
    splitter_specs = {
        "broker_control_splitter": [360, 980],
        "broker_middle_splitter": [380, 760],
        "recommend_splitter": [820, 420],
    }
    for attr_name, sizes in splitter_specs.items():
        splitter = getattr(self, attr_name, None)
        if isinstance(splitter, QSplitter) and splitter.count() == len(sizes):
            splitter.setSizes(sizes)


def _qh_hydrate_empty_workspace_panels_v3(self: QuantHunterWindow) -> None:
    _qh_hydrate_empty_workspace_panels_v2(self)
    richer_defaults = {
        "strategy_detail_text": (
            "战法明细\n\n"
            "这里会先告诉你这套战法适合什么场景、这只票为什么入选、当前该做什么，以及什么时候该放弃。\n"
            "刷新市场或生成机会池后，会展示主线、动作、买卖点、下一步和失效条件，再补充分数参考。"
        ),
        "runtime_log_text": (
            "[系统] 运行日志已就绪\n"
            "[提示] 这里会记录市场刷新、机会池重算、委托送审、执行回放与导出事件。\n"
            "[建议] 遇到界面未更新、链路未联动或提交异常时，先回到这里看最近三条记录。"
        ),
    }
    for attr_name, text in richer_defaults.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            current = widget.toPlainText().strip()
            if not current or current in {"等待推荐池。", "运行日志", "[INFO]"} or len(current) < 18:
                self._set_plain_text_if_changed(widget, text)


def _qh_open_focus_symbol_in_detail_v9(self: QuantHunterWindow) -> None:
    symbol = (
        getattr(self, "active_symbol", "") or ""
        or (self._selected_symbol_from_watchlist() if hasattr(self, "_selected_symbol_from_watchlist") else "")
        or (self._selected_board_symbol() if hasattr(self, "_selected_board_symbol") else "")
    )
    if symbol:
        if hasattr(self, "_focus_symbol_everywhere"):
            self._focus_symbol_everywhere(symbol, origin="detail")
        elif symbol in getattr(self, "universe_bars", {}):
            self.select_symbol(symbol)
        else:
            self.active_symbol = symbol
            self._refresh_detail_workspace_panels()
        self._navigate_to_workspace("detail", "metrics_text")
        if hasattr(self, "detail_conclusion_text"):
            stock_name = self._stock_name_for_symbol(symbol)
            stock_id = self._stock_id_for_symbol(symbol)
            self._set_plain_text_if_changed(
                self.detail_conclusion_text,
                "\n".join(
                    [
                        f"复盘结论：{stock_name} ({stock_id} / {symbol})",
                        "当前已从扫描、推荐或交易链路同步到复盘页。",
                        "优先检查：主线是否仍在前排、买点是否偏离计划、执行是否踩中纪律。",
                        "下一步：可继续对照信号表、成交记录和同主线候选，确认是否值得明天继续跟踪。",
                    ]
                ),
            )
    else:
        self._navigate_to_workspace("detail", "metrics_text")
        if hasattr(self, "detail_conclusion_text"):
            self._set_plain_text_if_changed(
                self.detail_conclusion_text,
                "复盘结论\n\n请先从扫描页、推荐页、打板页或交易页选中一只股票，再进入复盘研究。",
            )


def _qh_rebind_detail_routes_v9(self: QuantHunterWindow) -> None:
    target_rows = [
        "scannerTopActionRow",
        "detailMetricsActionRow",
        "detailDecisionActionRow",
        "detailConclusionActionRow",
    ]
    for row_name in target_rows:
        row = self.findChild(QWidget, row_name)
        if row is None:
            continue
        for button in row.findChildren(QPushButton):
            text = (button.text() or "").strip()
            if text not in {"查看复盘", "查看复盘研究"}:
                continue
            try:
                button.clicked.disconnect()
            except Exception:
                pass
            button.clicked.connect(self.open_focus_symbol_in_detail)
            button.setToolTip("带着当前焦点股票跳到复盘页，继续查看信号、成交与结论。")


def _qh_upgrade_story_defaults_v10(self: QuantHunterWindow) -> None:
    panel_defaults = {
        "trade_plan_text": (
            "今日交易计划\n\n"
            "结论：先刷新市场与机会池，再生成今天的前排计划、观察名单和风控边界。\n"
            "检查项：优先确认主线是否延续、仓位上限是否够用、买点是否还在计划区间内。\n"
            "下一步：生成计划后，优先看前 5 只候选，再决定是否送入交易执行。"
        ),
        "detail_execution_text": (
            "执行状态回放\n\n"
            "结论：这里会把委托建议、提交结果、成交回报和偏离原因串成一条执行链路。\n"
            "检查项：重点看是否按计划价格与仓位执行，是否出现阻塞、失败或超预期滑点。\n"
            "下一步：先对照委托与成交，再决定去交易页处理，还是继续保留复盘观察。"
        ),
        "detail_conclusion_text": (
            "复盘结论\n\n"
            "结论：这里沉淀单票的关键得失、纪律执行情况，以及是否值得继续跟踪。\n"
            "检查项：优先回看主线位置、买卖节奏、量价配合和失败原因，而不是只看盈亏。\n"
            "下一步：若仍属主线前排，可继续留在观察池；若逻辑失效，就转入风险处理。"
        ),
        "runtime_log_text": (
            "[系统] 运行日志已就绪\n"
            "[状态] 当前处于默认待机，等待市场刷新、机会池重算、委托生成或导出动作触发。\n"
            "[建议] 如果页面内容没同步、按钮反馈偏弱或执行链路异常，先回到这里查看最近事件。"
        ),
    }
    legacy_prefixes = {
        "trade_plan_text": {"先刷新主线，再生成今日交易计划。"},
        "detail_execution_text": {"执行状态回放"},
        "detail_conclusion_text": {"复盘结论"},
        "runtime_log_text": {"[", "运行日志"},
    }
    for attr_name, text in panel_defaults.items():
        widget = getattr(self, attr_name, None)
        if not isinstance(widget, QTextEdit):
            continue
        current = widget.toPlainText().strip()
        prefixes = legacy_prefixes.get(attr_name, set())
        if (
            not current
            or self._has_mojibake_text(current)
            or current in prefixes
            or len(current) < 48
            or any(current.startswith(prefix) for prefix in prefixes if prefix)
        ):
            self._set_plain_text_if_changed(widget, text)

    label_defaults = {
        "orders_focus_label": "委托焦点：等待机会池生成委托链路，再继续复核价格、数量与风险灯。",
        "trade_plan_focus_label": "计划焦点：等待市场与机会池建立后，生成今天的前排计划与仓位节奏。",
        "daily_pool_focus_label": "推荐焦点：等待高优先池、观察池和风险池同步后，再决定是否送审。",
    }
    for attr_name, text in label_defaults.items():
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QLabel):
            current = (widget.text() or "").strip()
            if not current or len(current) < 18 or "等待" in current:
                self._set_label_text_if_changed(widget, text)


def _qh_refresh_runtime_story_v10(self: QuantHunterWindow) -> None:
    widget = getattr(self, "runtime_log_text", None)
    if not isinstance(widget, QTextEdit):
        return
    recommend_status = getattr(getattr(self, "recommend_status_label", None), "text", lambda: "")().strip()
    scan_status = getattr(getattr(self, "scan_summary_label", None), "text", lambda: "")().strip()
    broker_status = getattr(getattr(self, "broker_status_banner", None), "text", lambda: "")().strip()
    lines = [
        "[系统] 运行日志已就绪",
        f"[推荐] {recommend_status or '等待推荐链路建立'}",
        f"[扫描] {scan_status or '等待扫描链路建立'}",
        f"[交易] {broker_status or '等待交易链路建立'}",
        "[建议] 若当前内容与预期不一致，先刷新市场与机会池，再检查跨页焦点是否同步。",
    ]
    current = widget.toPlainText().strip()
    if not current or len(current) < 180 or "运行面板已初始化" in current:
        self._set_plain_text_if_changed(widget, "\n".join(lines))


def _qh_post_build_ui_tweaks_v3(self: QuantHunterWindow) -> None:
    _qh_post_build_ui_tweaks_v2(self)
    self._hydrate_empty_workspace_panels()
    self._upgrade_story_defaults_v10()
    self._apply_commercial_table_layout_v8()
    self._balance_workspace_splitters_v8()
    self._rebind_detail_routes_v9()
    self._refresh_runtime_story_v10()
    self._refresh_broker_auxiliary_panels()


QuantHunterWindow._hydrate_empty_workspace_panels = _qh_hydrate_empty_workspace_panels_v3
QuantHunterWindow.open_focus_symbol_in_detail = _qh_open_focus_symbol_in_detail_v9
QuantHunterWindow._rebind_detail_routes_v9 = _qh_rebind_detail_routes_v9
QuantHunterWindow._upgrade_story_defaults_v10 = _qh_upgrade_story_defaults_v10
QuantHunterWindow._refresh_runtime_story_v10 = _qh_refresh_runtime_story_v10
QuantHunterWindow._apply_commercial_table_layout_v8 = _qh_apply_commercial_table_layout_v8
QuantHunterWindow._balance_workspace_splitters_v8 = _qh_balance_workspace_splitters_v8
QuantHunterWindow._post_build_ui_tweaks = _qh_post_build_ui_tweaks_v3

apply_runtime_feedback_patches(
    QuantHunterWindow,
    mainline_signal_brief_fn=_qh_mainline_signal_brief_v4,
    signal_action_text_fn=_qh_signal_action_text_v4,
)


def _qh_paper_trading_config_v17(self: QuantHunterWindow) -> tuple[float, float, bool, float]:
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    initial_cash = float(getattr(state, "initial_cash", 100000.0) or 100000.0)
    max_position_pct = float(getattr(state, "max_position_pct", 0.25) or 0.25)
    auto_run = bool(getattr(state, "auto_run", False))
    auto_interval_minutes = float(getattr(state, "auto_interval_minutes", 5.0) or 5.0)

    if hasattr(self, "paper_initial_cash_input"):
        try:
            initial_cash = float(self.paper_initial_cash_input.text().strip())
        except ValueError:
            pass
    if hasattr(self, "paper_max_position_input"):
        try:
            raw_value = float(self.paper_max_position_input.text().strip())
            max_position_pct = raw_value / 100.0 if raw_value > 1 else raw_value
        except ValueError:
            pass
    if hasattr(self, "paper_auto_run_checkbox"):
        auto_run = self.paper_auto_run_checkbox.isChecked()
    if hasattr(self, "paper_auto_interval_input"):
        try:
            auto_interval_minutes = float(self.paper_auto_interval_input.text().strip())
        except ValueError:
            pass

    initial_cash = max(initial_cash, 1000.0)
    max_position_pct = min(max(max_position_pct, 0.05), 1.0)
    auto_interval_minutes = min(max(auto_interval_minutes, 0.5), 240.0)
    return round(initial_cash, 2), round(max_position_pct, 4), auto_run, round(auto_interval_minutes, 2)


def _qh_install_paper_trading_workspace_v17(self: QuantHunterWindow) -> None:
    if hasattr(self, "paper_trading_box"):
        return
    self.paper_trading_state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    broker_content = self.broker_scroll_area.widget() if hasattr(self, "broker_scroll_area") else None
    root_layout = broker_content.layout() if broker_content is not None else None
    if root_layout is None:
        return

    self.paper_trading_box = QGroupBox("AI 模拟盘")
    self._style_terminal_panel(self.paper_trading_box)
    paper_layout = QVBoxLayout(self.paper_trading_box)
    paper_layout.setContentsMargins(12, 12, 12, 12)
    paper_layout.setSpacing(10)

    self.paper_trading_status_label = QLabel("模拟盘状态：等待初始化")
    self.paper_trading_status_label.setObjectName("statusBanner")
    self.paper_trading_status_label.setWordWrap(True)
    paper_layout.addWidget(self.paper_trading_status_label)

    settings_row = QHBoxLayout()
    settings_row.setSpacing(8)
    settings_row.addWidget(QLabel("初始资金"))
    self.paper_initial_cash_input = QLineEdit()
    self.paper_initial_cash_input.setMaximumWidth(120)
    settings_row.addWidget(self.paper_initial_cash_input)
    settings_row.addWidget(QLabel("单票上限"))
    self.paper_max_position_input = QLineEdit()
    self.paper_max_position_input.setMaximumWidth(100)
    settings_row.addWidget(self.paper_max_position_input)
    settings_row.addWidget(QLabel("巡航间隔(分钟)"))
    self.paper_auto_interval_input = QLineEdit()
    self.paper_auto_interval_input.setMaximumWidth(88)
    settings_row.addWidget(self.paper_auto_interval_input)
    self.paper_auto_run_checkbox = QCheckBox("推荐刷新后自动跟跑")
    settings_row.addWidget(self.paper_auto_run_checkbox)
    self.paper_initialize_button = QPushButton("初始化模拟盘")
    self.paper_run_button = QPushButton("AI 自主运行一轮")
    self.paper_export_button = QPushButton("导出模拟盘报告")
    self.paper_reset_button = QPushButton("重置模拟盘")
    self._set_button_role(self.paper_initialize_button, "ghost")
    self._set_button_role(self.paper_run_button, "accent")
    self._set_button_role(self.paper_export_button, "ghost")
    self._set_button_role(self.paper_reset_button, "ghost")
    self.paper_initialize_button.clicked.connect(self.initialize_paper_trading)
    self.paper_run_button.clicked.connect(self.run_ai_paper_trading_cycle)
    self.paper_export_button.clicked.connect(self.export_paper_trading_report)
    self.paper_reset_button.clicked.connect(self.reset_paper_trading)
    settings_changed_handler = getattr(self, "_on_paper_trading_settings_changed", None)
    if callable(settings_changed_handler):
        self.paper_initial_cash_input.editingFinished.connect(settings_changed_handler)
        self.paper_max_position_input.editingFinished.connect(settings_changed_handler)
        self.paper_auto_interval_input.editingFinished.connect(settings_changed_handler)
        self.paper_auto_run_checkbox.toggled.connect(settings_changed_handler)
    settings_row.addWidget(self.paper_initialize_button)
    settings_row.addWidget(self.paper_run_button)
    settings_row.addWidget(self.paper_export_button)
    settings_row.addWidget(self.paper_reset_button)
    settings_row.addStretch(1)
    paper_layout.addLayout(settings_row)

    metrics_row = QHBoxLayout()
    metrics_row.setSpacing(12)
    self.paper_metric_labels = {}
    for key, title in [
        ("cash", "可用资金"),
        ("equity", "总权益"),
        ("realized", "累计已实现"),
        ("return", "累计收益率"),
        ("win_rate", "闭环胜率"),
        ("closed", "闭环单"),
        ("positions", "持仓"),
        ("fills", "交割单"),
    ]:
        card = QFrame()
        card.setObjectName("metricCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName("metricCardTitle")
        value_label = QLabel("--")
        value_label.setObjectName("metricCardValue")
        value_label.setWordWrap(True)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        self.paper_metric_labels[key] = value_label
        metrics_row.addWidget(card)
    paper_layout.addLayout(metrics_row)

    self.paper_equity_chart_view = QChartView()
    self.paper_equity_chart_view.setObjectName("marketChartPanel")
    self.paper_equity_chart_view.setMinimumHeight(220)
    paper_layout.addWidget(self.paper_equity_chart_view)

    paper_splitter = QSplitter(Qt.Horizontal)
    self.paper_trading_splitter = paper_splitter
    paper_splitter.setChildrenCollapsible(False)

    position_box = QGroupBox("模拟持仓")
    ledger_box = QGroupBox("模拟交割单")
    self._style_terminal_panel(position_box, ledger_box)

    position_layout = QVBoxLayout(position_box)
    self.paper_positions_table = QTableWidget()
    self.paper_positions_table.setColumnCount(10)
    self.paper_positions_table.setHorizontalHeaderLabels(["名称", "代码", "战法", "数量", "成本", "现价", "市值", "浮盈", "收益率", "买卖点"])
    self.paper_positions_table.verticalHeader().setVisible(False)
    self.paper_positions_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.paper_positions_table.setSelectionMode(QAbstractItemView.SingleSelection)
    self.paper_positions_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.paper_positions_table.setAlternatingRowColors(True)
    self.paper_positions_table.horizontalHeader().setStretchLastSection(True)
    self.paper_positions_table.setMinimumHeight(260)
    position_layout.addWidget(self.paper_positions_table)

    ledger_layout = QVBoxLayout(ledger_box)
    self.paper_ledger_table = QTableWidget()
    self.paper_ledger_table.setColumnCount(12)
    self.paper_ledger_table.setHorizontalHeaderLabels(["编号", "时间", "代码", "动作", "价格", "数量", "金额", "战法", "仓位", "已实现", "累计", "备注"])
    self.paper_ledger_table.verticalHeader().setVisible(False)
    self.paper_ledger_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.paper_ledger_table.setSelectionMode(QAbstractItemView.SingleSelection)
    self.paper_ledger_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.paper_ledger_table.setAlternatingRowColors(True)
    self.paper_ledger_table.horizontalHeader().setStretchLastSection(True)
    self.paper_ledger_table.setMinimumHeight(260)
    ledger_layout.addWidget(self.paper_ledger_table)

    paper_splitter.addWidget(position_box)
    paper_splitter.addWidget(ledger_box)
    self._configure_splitter(paper_splitter, [560, 760])
    paper_layout.addWidget(paper_splitter)

    analytics_splitter = QSplitter(Qt.Horizontal)
    analytics_splitter.setChildrenCollapsible(False)
    self.paper_analytics_splitter = analytics_splitter

    strategy_box = QGroupBox("战法收益拆解")
    patrol_box = QGroupBox("巡航日志")
    self._style_terminal_panel(strategy_box, patrol_box)

    strategy_layout = QVBoxLayout(strategy_box)
    self.paper_strategy_table = QTableWidget()
    self.paper_strategy_table.setColumnCount(11)
    self.paper_strategy_table.setHorizontalHeaderLabels(
        ["战法", "角色", "样本", "胜率", "胜率差", "平均持有", "持有差", "已实现", "预算", "倾向", "当前决策"]
    )
    self.paper_strategy_table.verticalHeader().setVisible(False)
    self.paper_strategy_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.paper_strategy_table.setSelectionMode(QAbstractItemView.SingleSelection)
    self.paper_strategy_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.paper_strategy_table.setAlternatingRowColors(True)
    self.paper_strategy_table.horizontalHeader().setStretchLastSection(True)
    self.paper_strategy_table.setMinimumHeight(200)
    strategy_layout.addWidget(self.paper_strategy_table)

    patrol_layout = QVBoxLayout(patrol_box)
    self.paper_patrol_table = QTableWidget()
    self.paper_patrol_table.setColumnCount(5)
    self.paper_patrol_table.setHorizontalHeaderLabels(["时间", "类型", "摘要", "权益", "持仓"])
    self.paper_patrol_table.verticalHeader().setVisible(False)
    self.paper_patrol_table.setSelectionBehavior(QAbstractItemView.SelectRows)
    self.paper_patrol_table.setSelectionMode(QAbstractItemView.SingleSelection)
    self.paper_patrol_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    self.paper_patrol_table.setAlternatingRowColors(True)
    self.paper_patrol_table.horizontalHeader().setStretchLastSection(True)
    self.paper_patrol_table.setMinimumHeight(200)
    patrol_layout.addWidget(self.paper_patrol_table)

    analytics_splitter.addWidget(strategy_box)
    analytics_splitter.addWidget(patrol_box)
    self._configure_splitter(analytics_splitter, [520, 760])
    paper_layout.addWidget(analytics_splitter)

    self.paper_trading_text = QTextEdit()
    self.paper_trading_text.setReadOnly(True)
    self.paper_trading_text.setMinimumHeight(140)
    self.paper_trading_text.setMaximumHeight(190)
    self._style_terminal_console(self.paper_trading_text)
    paper_layout.addWidget(self.paper_trading_text)

    experiment_box = QGroupBox("策略实验洞察")
    experiment_layout = QVBoxLayout(experiment_box)
    experiment_box.setObjectName("paperExperimentPanel")
    self.paper_experiment_text = QTextEdit()
    self.paper_experiment_text.setReadOnly(True)
    self.paper_experiment_text.setMinimumHeight(120)
    self.paper_experiment_text.setMaximumHeight(200)
    self._style_terminal_console(self.paper_experiment_text)
    experiment_layout.addWidget(self.paper_experiment_text)
    paper_layout.addWidget(experiment_box)

    insert_index = root_layout.indexOf(self.broker_middle_splitter) + 1 if hasattr(self, "broker_middle_splitter") else root_layout.count()
    root_layout.insertWidget(insert_index, self.paper_trading_box)
    self.paper_trading_timer = QTimer(self)
    self.paper_trading_timer.timeout.connect(self._paper_trading_patrol_tick)


def _qh_refresh_paper_trading_panels_v17(self: QuantHunterWindow) -> None:
    if not hasattr(self, "paper_trading_box"):
        return
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    if not hasattr(self, "paper_initial_cash_input"):
        return

    if not self.paper_initial_cash_input.hasFocus():
        self.paper_initial_cash_input.setText(f"{float(state.initial_cash or 100000.0):.0f}")
    if not self.paper_max_position_input.hasFocus():
        self.paper_max_position_input.setText(f"{float(state.max_position_pct or 0.25) * 100:.0f}%")
    if hasattr(self, "paper_auto_interval_input") and not self.paper_auto_interval_input.hasFocus():
        self.paper_auto_interval_input.setText(f"{float(getattr(state, 'auto_interval_minutes', 5.0) or 5.0):.1f}")
    self.paper_auto_run_checkbox.blockSignals(True)
    self.paper_auto_run_checkbox.setChecked(bool(state.auto_run))
    self.paper_auto_run_checkbox.blockSignals(False)

    status_text = (
        f"模拟盘状态：已启用 | 自主巡航 {'开启' if state.auto_run else '关闭'}（仅交易时段触发） | 间隔 {float(getattr(state, 'auto_interval_minutes', 5.0) or 5.0):.1f} 分钟 | 最近运行 {state.last_run_at or '未运行'} | 总权益 {float(state.total_equity or state.cash or 0.0):,.2f}"
        if state.enabled
        else "模拟盘状态：未启用，先初始化后再让 AI 自主执行。"
    )
    self.paper_trading_status_label.setText(status_text)

    self.paper_metric_labels["cash"].setText(f"{float(state.cash or 0.0):,.0f}")
    self.paper_metric_labels["equity"].setText(f"{float(state.total_equity or 0.0):,.0f}")
    self.paper_metric_labels["realized"].setText(f"{float(state.realized_pnl or 0.0):,.0f}")
    self.paper_metric_labels["return"].setText(f"{float(state.total_return or 0.0):.2%}")
    analytics = summarize_paper_trading_performance(state)
    self.paper_metric_labels["win_rate"].setText(f"{float(analytics.get('win_rate', 0.0) or 0.0):.1%}")
    self.paper_metric_labels["closed"].setText(str(int(analytics.get("closed_trade_count", 0) or 0)))
    self.paper_metric_labels["positions"].setText(str(len(getattr(state, "positions", []) or [])))
    self.paper_metric_labels["fills"].setText(str(len(getattr(state, "ledger", []) or [])))

    positions = list(getattr(state, "positions", []) or [])
    positions_updates_enabled = self.paper_positions_table.updatesEnabled()
    self.paper_positions_table.setUpdatesEnabled(False)
    self.paper_positions_table.blockSignals(True)
    try:
        self.paper_positions_table.setRowCount(len(positions))
        for row_index, item in enumerate(positions):
            values = [
                item.stock_name or item.symbol,
                item.symbol,
                item.strategy_name or "--",
                str(item.quantity),
                f"{float(item.avg_cost or 0.0):.2f}",
                f"{float(item.current_price or 0.0):.2f}",
                f"{float(item.market_value or 0.0):,.0f}",
                f"{float(item.unrealized_pnl or 0.0):,.0f}",
                f"{float(item.unrealized_pnl_pct or 0.0):.2%}",
                " / ".join(part for part in [item.buy_point, item.sell_point] if part) or item.rationale or "--",
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column in {7, 8}:
                    pnl_value = float(item.unrealized_pnl or 0.0)
                    if pnl_value > 0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif pnl_value < 0:
                        table_item.setForeground(QColor("#C44536"))
                self.paper_positions_table.setItem(row_index, column, table_item)
    finally:
        self.paper_positions_table.blockSignals(False)
        self.paper_positions_table.setUpdatesEnabled(positions_updates_enabled)

    ledger_rows = list(reversed((getattr(state, "ledger", []) or [])[-200:]))
    ledger_updates_enabled = self.paper_ledger_table.updatesEnabled()
    self.paper_ledger_table.setUpdatesEnabled(False)
    self.paper_ledger_table.blockSignals(True)
    try:
        self.paper_ledger_table.setRowCount(len(ledger_rows))
        for row_index, item in enumerate(ledger_rows):
            values = [
                item.order_id,
                item.timestamp,
                item.symbol,
                self._display_action(item.side),
                f"{float(item.price or 0.0):.2f}",
                str(item.quantity),
                f"{float(item.amount or 0.0):,.0f}",
                item.strategy_name or "--",
                f"{float(item.position_pct or 0.0):.1%}",
                f"{float(item.realized_pnl or 0.0):,.0f}",
                f"{float(item.cumulative_realized_pnl or 0.0):,.0f}",
                item.note or item.signal_source or "--",
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 3:
                    side = str(item.side or "").upper()
                    if side == "BUY":
                        table_item.setForeground(QColor("#0F8A4B"))
                    else:
                        table_item.setForeground(QColor("#C44536"))
                elif column in {9, 10}:
                    pnl_value = float(item.realized_pnl or 0.0) if column == 9 else float(item.cumulative_realized_pnl or 0.0)
                    if pnl_value > 0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif pnl_value < 0:
                        table_item.setForeground(QColor("#C44536"))
                self.paper_ledger_table.setItem(row_index, column, table_item)
    finally:
        self.paper_ledger_table.blockSignals(False)
        self.paper_ledger_table.setUpdatesEnabled(ledger_updates_enabled)

    strategy_rows = list(analytics.get("strategy_rows", []) or [])
    rotation_rows = build_strategy_rotation_snapshot(state)
    rotation_map = {str(item.get("strategy_name", "") or ""): item for item in rotation_rows}
    experiment_context_map = _qh_paper_experiment_table_context_v44(analytics, rotation_rows)
    strategy_updates_enabled = self.paper_strategy_table.updatesEnabled()
    self.paper_strategy_table.setUpdatesEnabled(False)
    self.paper_strategy_table.blockSignals(True)
    try:
        self.paper_strategy_table.setRowCount(len(strategy_rows))
        for row_index, item in enumerate(strategy_rows):
            strategy_name = str(item.get("strategy_name", "") or "--")
            rotation = rotation_map.get(strategy_name, {})
            experiment_context = experiment_context_map.get(strategy_name, {})
            bias_label = str(rotation.get("bias_label", "") or "中性")
            multiplier = float(rotation.get("budget_multiplier", 1.0) or 1.0)
            avg_hold_days = float(item.get("avg_hold_days", 0.0) or rotation.get("avg_hold_days", 0.0) or 0.0)
            role_label = str(experiment_context.get("role_label", "") or "备选")
            decision_text = str(experiment_context.get("decision", "") or "继续观察")
            win_rate_delta = float(experiment_context.get("win_rate_delta", 0.0) or 0.0)
            hold_delta = float(experiment_context.get("hold_delta", 0.0) or 0.0)
            hold_text = f"{avg_hold_days:.1f}天" if avg_hold_days > 0 else "--"
            win_rate_delta_text = "基准" if role_label == "主测" else f"{win_rate_delta:+.1%}"
            hold_delta_text = "基准" if role_label == "主测" else (f"{hold_delta:+.1f}天" if avg_hold_days > 0 else "待补样本")
            budget_text = f"x{multiplier:.2f}"
            values = [
                strategy_name,
                role_label,
                str(int(rotation.get("sample_count", int(item.get("buy_count", 0) or 0) + int(item.get("sell_count", 0) or 0)) or 0)),
                f"{float(item.get('win_rate', 0.0) or 0.0):.1%}",
                win_rate_delta_text,
                hold_text,
                hold_delta_text,
                f"{float(item.get('realized_pnl', 0.0) or 0.0):,.0f}",
                budget_text,
                bias_label,
                decision_text,
            ]
            row_tooltip = (
                f"开仓 {int(item.get('buy_count', 0) or 0)} | "
                f"卖出 {int(item.get('sell_count', 0) or 0)} | "
                f"平均仓位 {float(item.get('avg_position_pct', 0.0) or 0.0):.1%} | "
                f"预算倍率 {budget_text} | 当前决策：{decision_text}"
            )
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                table_item.setToolTip(row_tooltip)
                if column == 4:
                    if win_rate_delta > 0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif win_rate_delta < 0:
                        table_item.setForeground(QColor("#C44536"))
                elif column == 6:
                    if hold_delta < 0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif hold_delta > 0:
                        table_item.setForeground(QColor("#C44536"))
                elif column == 7:
                    pnl_value = float(item.get("realized_pnl", 0.0) or 0.0)
                    if pnl_value > 0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif pnl_value < 0:
                        table_item.setForeground(QColor("#C44536"))
                elif column == 8:
                    if multiplier > 1.0:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif multiplier < 1.0:
                        table_item.setForeground(QColor("#C44536"))
                elif column == 9:
                    rotation_score = float(rotation.get("rotation_score", 0.0) or 0.0)
                    if rotation_score > 0.18:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif rotation_score < -0.18:
                        table_item.setForeground(QColor("#C44536"))
                elif column == 10:
                    if "主测" in decision_text or "转主测" in decision_text:
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif "降权" in decision_text or "复盘" in decision_text:
                        table_item.setForeground(QColor("#C44536"))
                self.paper_strategy_table.setItem(row_index, column, table_item)
    finally:
        self.paper_strategy_table.blockSignals(False)
        self.paper_strategy_table.setUpdatesEnabled(strategy_updates_enabled)

    patrol_rows = list(reversed((getattr(state, "patrol_logs", []) or [])[-120:]))
    patrol_updates_enabled = self.paper_patrol_table.updatesEnabled()
    self.paper_patrol_table.setUpdatesEnabled(False)
    self.paper_patrol_table.blockSignals(True)
    try:
        self.paper_patrol_table.setRowCount(len(patrol_rows))
        for row_index, item in enumerate(patrol_rows):
            values = [
                item.timestamp,
                item.event_type or "CYCLE",
                item.summary or item.detail or "--",
                f"{float(item.equity or 0.0):,.0f}",
                str(int(item.position_count or 0)),
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 1:
                    event_type = str(item.event_type or "").upper()
                    if event_type == "BUY":
                        table_item.setForeground(QColor("#0F8A4B"))
                    elif event_type in {"SELL", "REDUCE"}:
                        table_item.setForeground(QColor("#C44536"))
                self.paper_patrol_table.setItem(row_index, column, table_item)
    finally:
        self.paper_patrol_table.blockSignals(False)
        self.paper_patrol_table.setUpdatesEnabled(patrol_updates_enabled)

    lines = [
        "AI 模拟盘说明",
        f"- 运行时间：{state.last_run_at or '未运行'}",
        f"- 最新摘要：{state.last_strategy_note or '等待 AI 根据推荐池和持仓建议生成第一轮模拟动作。'}",
        f"- 模拟持仓：{len(positions)} 只 | 交割单：{len(getattr(state, 'ledger', []) or [])} 笔",
        f"- 可用资金：{float(state.cash or 0.0):,.2f} | 总权益：{float(state.total_equity or 0.0):,.2f} | 累计收益率：{float(state.total_return or 0.0):.2%}",
        f"- 闭环单：{int(analytics.get('closed_trade_count', 0) or 0)} | 胜率：{float(analytics.get('win_rate', 0.0) or 0.0):.2%} | 平均单笔已实现：{float(analytics.get('avg_realized_pnl', 0.0) or 0.0):,.2f}",
    ]
    if rotation_rows:
        lead_rotation = rotation_rows[0]
        lines.append(
            f"- 本轮实验：主测 {lead_rotation['strategy_name']} | 倾向 {lead_rotation['bias_label']} x{float(lead_rotation['budget_multiplier']):.2f} | 样本 {int(lead_rotation['sample_count'] or 0)}"
        )
        if len(rotation_rows) > 1:
            follow_rotation = rotation_rows[1]
            lines.append(
                f"- 策略观察：{follow_rotation['strategy_name']} {follow_rotation['bias_label']} x{float(follow_rotation['budget_multiplier']):.2f}"
            )
    avg_hold_days = float(analytics.get("avg_hold_days", 0.0) or 0.0)
    hold_note = str(analytics.get("hold_cycle_note", "") or "")
    if avg_hold_days > 0:
        lines.append(f"- 持有周期：平均 {avg_hold_days:.1f} 天" + (f" | {hold_note}" if hold_note else ""))
    curve = list(getattr(state, "equity_curve", []) or [])
    if curve:
        recent_curve = " / ".join(
            f"{point.timestamp or '初始'} 权益 {float(point.total_equity or 0.0):,.0f}"
            for point in curve[-3:]
        )
        lines.append(f"- 最近权益：{recent_curve}")
    if positions:
        focus = positions[0]
        lines.append(
            f"- 当前第一仓：{focus.stock_name or focus.symbol} | 战法 {focus.strategy_name or '--'} | 买点 {focus.buy_point or '--'} | 卖点 {focus.sell_point or '--'}"
        )
    if patrol_rows:
        latest_log = patrol_rows[0]
        lines.append(
            f"- 最近巡航：{latest_log.timestamp} | {latest_log.event_type or 'CYCLE'} | {latest_log.summary or latest_log.detail or '--'}"
        )
    if getattr(self, "daily_pool_rows", []):
        top_theme_limit, max_total_exposure, theme_drop_reduce = self._current_strategy_runtime_config()
        simulated_holdings = [
            HoldingRecord(
                symbol=item.symbol,
                quantity=item.quantity,
                available=item.available,
                cost_price=item.avg_cost,
                market_value=item.market_value,
            )
            for item in positions
        ]
        follow_plan = DecisionEngine().build_plan(
            list(getattr(self, "daily_pool_rows", []) or []),
            simulated_holdings,
            float(state.cash or 0.0),
            top_theme_limit=top_theme_limit,
            max_total_exposure=max_total_exposure,
            theme_drop_reduce=theme_drop_reduce,
        )
        if follow_plan.position_advice:
            lines.append("- 本轮调仓建议：")
            for item in follow_plan.position_advice[:3]:
                lines.append(
                    f"  - {item.stock_name or item.symbol}：{self._display_action(item.action)} | {item.rationale}"
                )
        if follow_plan.decisions:
            lines.append("- 下一轮关注：")
            for item in follow_plan.decisions[:2]:
                lines.append(
                    f"  - {item.stock_name or item.symbol}：{item.rationale} | 计划 {item.planned_entry:.2f} / 止损 {item.planned_stop:.2f}"
                )
    self._set_plain_text_if_changed(self.paper_trading_text, "\n".join(lines))
    self._refresh_paper_trading_equity_chart()
    self._sync_paper_trading_timer()


def _qh_initialize_paper_trading_v17(self: QuantHunterWindow) -> None:
    initial_cash, max_position_pct, auto_run, auto_interval_minutes = self._paper_trading_config()
    self.paper_trading_state = PaperTradingEngine().initialize_state(
        initial_cash=initial_cash,
        max_position_pct=max_position_pct,
        auto_run=auto_run,
        auto_interval_minutes=auto_interval_minutes,
    )
    self._refresh_paper_trading_panels()
    self.save_state()
    QMessageBox.information(self, "模拟盘已初始化", "AI 模拟盘账户已经创建，可以开始自主执行。")


def _qh_reset_paper_trading_v17(self: QuantHunterWindow) -> None:
    confirm = QMessageBox.question(
        self,
        "确认重置模拟盘",
        "重置会清空模拟持仓、交割单、巡航日志和收益曲线。确定继续吗？",
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    if confirm != QMessageBox.Yes:
        return
    initial_cash, max_position_pct, auto_run, auto_interval_minutes = self._paper_trading_config()
    self.paper_trading_state = PaperTradingEngine().initialize_state(
        initial_cash=initial_cash,
        max_position_pct=max_position_pct,
        auto_run=auto_run,
        auto_interval_minutes=auto_interval_minutes,
    )
    self._refresh_paper_trading_panels()
    self.save_state()
    QMessageBox.information(self, "模拟盘已重置", "模拟持仓、交割单和累计收益已经清空。")


def _qh_run_ai_paper_trading_cycle_v17(self: QuantHunterWindow) -> None:
    if not getattr(self, "daily_pool_rows", []):
        QMessageBox.information(self, "提示", "请先刷新推荐池，再让 AI 运行模拟盘。")
        return
    initial_cash, max_position_pct, auto_run, auto_interval_minutes = self._paper_trading_config()
    state = getattr(self, "paper_trading_state", PaperTradingState())
    if not state.enabled:
        state = PaperTradingEngine().initialize_state(
            initial_cash=initial_cash,
            max_position_pct=max_position_pct,
            auto_run=auto_run,
            auto_interval_minutes=auto_interval_minutes,
        )
    else:
        state = replace(
            state,
            max_position_pct=max_position_pct,
            auto_run=auto_run,
            auto_interval_minutes=auto_interval_minutes,
        )

    top_theme_limit, max_total_exposure, theme_drop_reduce = self._current_strategy_runtime_config()
    self.paper_trading_state = PaperTradingEngine().run_cycle(
        state,
        list(getattr(self, "daily_pool_rows", []) or []),
        as_of=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        top_theme_limit=top_theme_limit,
        max_total_exposure=max_total_exposure,
        theme_drop_reduce=theme_drop_reduce,
    )
    self._refresh_paper_trading_panels()
    self.save_state()
    if hasattr(self, "broker_status_banner"):
        self.broker_status_banner.setText(
            f"交易状态：AI 模拟盘已完成一轮自主执行 | {self.paper_trading_state.last_strategy_note or '等待下一轮'}"
        )


def _qh_export_paper_trading_report_v17(self: QuantHunterWindow) -> None:
    state = getattr(self, "paper_trading_state", PaperTradingState())
    if not state.enabled:
        QMessageBox.information(self, "提示", "请先初始化模拟盘，再导出报告。")
        return
    if not state.ledger and not state.positions:
        QMessageBox.information(self, "提示", "当前模拟盘还没有成交或持仓，先运行一轮再导出。")
        return
    output_dir = self._paper_trading_output_dir()
    artifacts = export_paper_trading_report(
        state,
        output_dir=output_dir,
        exported_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    )
    self._set_plain_text_if_changed(
        self.paper_trading_text,
        "\n".join(
            [
                self.paper_trading_text.toPlainText().strip(),
                "",
                "模拟盘报告已导出：",
                f"- Markdown：{artifacts.markdown_path}",
                f"- CSV：{artifacts.csv_path}",
                f"- JSON：{artifacts.json_path}",
            ]
        ).strip()
    )
    QMessageBox.information(
        self,
        "导出完成",
        "\n".join(
            [
                "AI 模拟盘报告已导出：",
                f"Markdown：{artifacts.markdown_path}",
                f"CSV：{artifacts.csv_path}",
                f"JSON：{artifacts.json_path}",
            ]
        ),
    )


def _qh_paper_trading_output_dir_v17(self: QuantHunterWindow) -> Path:
    export_dir = self.current_broker_profile().export_dir.strip()
    if export_dir:
        return Path(export_dir) / "paper_trading"
    return PROJECT_ROOT / "exports" / "paper_trading"


def _qh_refresh_paper_trading_equity_chart_v18(self: QuantHunterWindow) -> None:
    chart_view = getattr(self, "paper_equity_chart_view", None)
    if chart_view is None:
        return

    chart = QChart()
    self._style_dark_chart(chart, "AI 模拟盘权益曲线")
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    curve = list(getattr(state, "equity_curve", []) or [])
    if not curve:
        chart_view.setChart(chart)
        return

    equity_series = QLineSeries()
    equity_series.setName("总权益")
    equity_series.setColor(QColor("#25f3ff"))
    baseline_series = QLineSeries()
    baseline_series.setName("初始资金")
    baseline_series.setColor(QColor("#f2c94c"))

    baseline = float(getattr(state, "initial_cash", 0.0) or 0.0)
    values: list[float] = []
    for index, point in enumerate(curve[-120:]):
        total_equity = float(point.total_equity or 0.0)
        equity_series.append(index, total_equity)
        baseline_series.append(index, baseline)
        values.extend([total_equity, baseline])

    chart.addSeries(equity_series)
    chart.addSeries(baseline_series)

    axis_x = QValueAxis()
    axis_x.setLabelsVisible(False)
    axis_x.setGridLineColor(QColor("#252a33"))
    axis_x.setRange(0, max(len(curve[-120:]) - 1, 1))
    axis_y = QValueAxis()
    axis_y.setLabelsColor(QColor("#b7c0d8"))
    axis_y.setGridLineColor(QColor("#252a33"))
    low = min(values) if values else baseline
    high = max(values) if values else baseline
    pad = max((high - low) * 0.12, max(abs(high), abs(low), 1.0) * 0.02)
    axis_y.setRange(low - pad, high + pad)

    chart.addAxis(axis_x, Qt.AlignBottom)
    chart.addAxis(axis_y, Qt.AlignRight)
    equity_series.attachAxis(axis_x)
    equity_series.attachAxis(axis_y)
    baseline_series.attachAxis(axis_x)
    baseline_series.attachAxis(axis_y)
    chart.legend().setVisible(True)
    chart_view.setChart(chart)


def _qh_sync_paper_trading_timer_v18(self: QuantHunterWindow) -> None:
    timer = getattr(self, "paper_trading_timer", None)
    if timer is None:
        return
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    interval_minutes = float(getattr(state, "auto_interval_minutes", 5.0) or 5.0)
    interval_ms = max(int(interval_minutes * 60_000), 30_000)
    timer.setInterval(interval_ms)
    if state.enabled and state.auto_run:
        if not timer.isActive():
            timer.start()
    elif timer.isActive():
        timer.stop()


def _qh_on_paper_trading_settings_changed_v18(self: QuantHunterWindow) -> None:
    if not hasattr(self, "_paper_trading_config"):
        return
    initial_cash, max_position_pct, auto_run, auto_interval_minutes = self._paper_trading_config()
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    if state.enabled:
        state = replace(
            state,
            max_position_pct=max_position_pct,
            auto_run=auto_run,
            auto_interval_minutes=auto_interval_minutes,
        )
    else:
        state = replace(
            state,
            initial_cash=initial_cash,
            cash=float(state.cash or initial_cash),
            max_position_pct=max_position_pct,
            auto_run=auto_run,
            auto_interval_minutes=auto_interval_minutes,
            total_equity=float(state.total_equity or state.cash or initial_cash),
        )
    self.paper_trading_state = state
    self._refresh_paper_trading_panels()
    self.save_state()


def _qh_paper_trading_patrol_tick_v18(self: QuantHunterWindow) -> None:
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    if not state.enabled or not state.auto_run:
        self._sync_paper_trading_timer()
        return

    current_dt = datetime.now()
    now = current_dt.time()
    in_session = time(9, 25) <= now <= time(11, 35) or time(12, 55) <= now <= time(15, 5)
    if not should_auto_run_paper_trading(state, now=current_dt, in_session=in_session):
        return
    if self._is_job_running("daily_pool"):
        return

    if hasattr(self, "broker_status_banner"):
        self.broker_status_banner.setText(
            f"交易状态：AI 模拟盘正在刷新推荐池，准备自主巡航 | {current_dt.strftime('%H:%M:%S')}"
        )
    self.refresh_daily_pool(async_mode=True)


def _qh_maybe_auto_run_paper_trading_v17(self: QuantHunterWindow) -> None:
    if not getattr(self, "daily_pool_rows", []):
        return
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    current_dt = datetime.now()
    now = current_dt.time()
    in_session = time(9, 25) <= now <= time(11, 35) or time(12, 55) <= now <= time(15, 5)
    if not should_auto_run_paper_trading(state, now=current_dt, in_session=in_session):
        return
    self.run_ai_paper_trading_cycle()


def _qh_save_state_v17(self: QuantHunterWindow) -> None:
    state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
    if hasattr(self, "_paper_trading_config"):
        initial_cash, max_position_pct, auto_run, auto_interval_minutes = self._paper_trading_config()
        if state.enabled:
            state = replace(
                state,
                max_position_pct=max_position_pct,
                auto_run=auto_run,
                auto_interval_minutes=auto_interval_minutes,
            )
        else:
            state = replace(
                state,
                initial_cash=initial_cash,
                cash=float(state.cash or initial_cash),
                max_position_pct=max_position_pct,
                auto_run=auto_run,
                auto_interval_minutes=auto_interval_minutes,
                total_equity=float(state.total_equity or state.cash or initial_cash),
            )
    self.paper_trading_state = state
    self.state.paper_trading_state = state
    self.state.focus_themes = self._parse_focus_themes()
    save_app_state(
        STATE_FILE,
        AppState(
            universe_dir=self.state.universe_dir,
            selected_symbol=getattr(self, "active_symbol", "") or self.state.selected_symbol,
            watchlist=self.state.watchlist,
            ui_theme=self.current_theme,
            theme_alias_path=self.theme_alias_path,
            recommend_theme_filter=getattr(self, "recommend_theme_filter", self.state.recommend_theme_filter),
            recommend_strategy_filter=getattr(self, "recommend_strategy_filter", self.state.recommend_strategy_filter),
            recommend_action_filter=getattr(self, "recommend_action_filter", self.state.recommend_action_filter),
            recommend_execution_filter=getattr(self, "recommend_execution_filter", self.state.recommend_execution_filter),
            market_theme_filter=getattr(self, "market_theme_filter", self.state.market_theme_filter),
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
            market_data_mode=getattr(self, "market_data_mode", self.state.market_data_mode),
            market_timeframe_mode=getattr(self, "market_timeframe_mode", self.state.market_timeframe_mode),
            market_history_window=getattr(self, "market_history_window", self.state.market_history_window),
            market_review_date=getattr(self, "market_history_date", self.state.market_review_date),
            broker_profile=self.current_broker_profile(),
            paper_trading_state=state,
        ),
    )


_ORIGINAL_QH_POST_BUILD_UI_TWEAKS_V17 = QuantHunterWindow._post_build_ui_tweaks
_ORIGINAL_QH_APPLY_DAILY_POOL_ROWS_V17 = QuantHunterWindow._apply_daily_pool_rows


def _qh_post_build_ui_tweaks_v17(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_POST_BUILD_UI_TWEAKS_V17(self)
    self._install_paper_trading_workspace()
    self._refresh_paper_trading_panels()


def _qh_apply_daily_pool_rows_v17(self: QuantHunterWindow, rows: list[RecommendationRow]) -> None:
    _ORIGINAL_QH_APPLY_DAILY_POOL_ROWS_V17(self, rows)
    if rows:
        self._maybe_auto_run_paper_trading()


QuantHunterWindow._paper_trading_config = _qh_paper_trading_config_v17
QuantHunterWindow._install_paper_trading_workspace = _qh_install_paper_trading_workspace_v17
QuantHunterWindow._refresh_paper_trading_panels = _qh_refresh_paper_trading_panels_v17
QuantHunterWindow._refresh_paper_trading_equity_chart = _qh_refresh_paper_trading_equity_chart_v18
QuantHunterWindow._sync_paper_trading_timer = _qh_sync_paper_trading_timer_v18
QuantHunterWindow._on_paper_trading_settings_changed = _qh_on_paper_trading_settings_changed_v18
QuantHunterWindow._paper_trading_patrol_tick = _qh_paper_trading_patrol_tick_v18
QuantHunterWindow.initialize_paper_trading = _qh_initialize_paper_trading_v17
QuantHunterWindow.reset_paper_trading = _qh_reset_paper_trading_v17
QuantHunterWindow.run_ai_paper_trading_cycle = _qh_run_ai_paper_trading_cycle_v17
QuantHunterWindow.export_paper_trading_report = _qh_export_paper_trading_report_v17
QuantHunterWindow._paper_trading_output_dir = _qh_paper_trading_output_dir_v17
QuantHunterWindow._maybe_auto_run_paper_trading = _qh_maybe_auto_run_paper_trading_v17
QuantHunterWindow.save_state = _qh_save_state_v17
QuantHunterWindow._apply_daily_pool_rows = _qh_apply_daily_pool_rows_v17
QuantHunterWindow._post_build_ui_tweaks = _qh_post_build_ui_tweaks_v17


apply_focus_bridge_patches(
    QuantHunterWindow,
    mainline_signal_brief_fn=_qh_mainline_signal_brief_v4,
    signal_action_text_fn=_qh_signal_action_text_v4,
    recommend_execution_summary_fn=_qh_recommend_execution_summary_v24,
    recommend_cta_labels_fn=_qh_recommend_cta_labels_v37,
    paper_strategy_experiment_bridge_fn=_qh_paper_strategy_experiment_bridge_v45,
    recommend_queue_snapshot_fn=_qh_recommend_queue_snapshot_v25,
    queue_sequence_summary_fn=_qh_queue_sequence_summary,
    next_review_target_fn=_qh_next_review_target,
)

apply_cross_workspace_focus_patches(
    QuantHunterWindow,
    mainline_signal_brief_fn=_qh_mainline_signal_brief_v4,
    signal_action_text_fn=_qh_signal_action_text_v4,
    recommend_execution_summary_fn=_qh_recommend_execution_summary_v24,
    recommend_focus_reason_fn=_qh_recommend_focus_reason_v24,
    recommend_queue_snapshot_fn=_qh_recommend_queue_snapshot_v25,
    queue_sequence_summary_fn=_qh_queue_sequence_summary,
    next_review_target_fn=_qh_next_review_target,
    tail_buy_runtime_status_fn=tail_buy_runtime_status,
    tail_buy_runtime_panel_lines_fn=tail_buy_runtime_panel_lines,
    set_label_text_fn=_qh_set_label_text_v7,
)


_ORIGINAL_QH_POST_BUILD_UI_TWEAKS_V19 = QuantHunterWindow._post_build_ui_tweaks
_ORIGINAL_QH_CONFIGURE_SPLITTER_V19 = QuantHunterWindow._configure_splitter
_ORIGINAL_QH_SHOW_EVENT_V19 = getattr(QuantHunterWindow, "showEvent")
_ORIGINAL_QH_RESIZE_EVENT_V19 = getattr(QuantHunterWindow, "resizeEvent")
_ORIGINAL_QH_NAVIGATE_TO_WORKSPACE_V20 = QuantHunterWindow._navigate_to_workspace
_ORIGINAL_QH_ON_WORKSPACE_TAB_CHANGED_V20 = QuantHunterWindow._on_workspace_tab_changed


def _qh_configure_splitter_v19(self: QuantHunterWindow, splitter: QSplitter, sizes: list[int] | None = None) -> None:
    _ORIGINAL_QH_CONFIGURE_SPLITTER_V19(self, splitter, sizes)
    splitter.setChildrenCollapsible(False)
    splitter.setOpaqueResize(False)
    splitter.setHandleWidth(max(splitter.handleWidth(), 12))
    for index in range(splitter.count()):
        splitter.setCollapsible(index, False)


def _qh_safe_window_minimum_v19(self: QuantHunterWindow) -> tuple[int, int]:
    screen = self.screen()
    if screen is None:
        return 1200, 760
    available = screen.availableGeometry()
    safe_width = max(1200, min(1460, available.width() - 120))
    safe_height = max(760, min(860, available.height() - 120))
    return safe_width, safe_height


def _qh_apply_splitter_layout_v19(
    self: QuantHunterWindow,
    splitter: QSplitter,
    sizes: list[int],
    min_sizes: list[int],
) -> None:
    if getattr(splitter, "_qh_layout_initialized_v19", False):
        return
    self._configure_splitter(splitter, sizes)
    splitter.setSizes(sizes)
    for index in range(splitter.count()):
        splitter.setStretchFactor(index, max(sizes[index] // 100, 1))
        widget = splitter.widget(index)
        if widget is None:
            continue
        if splitter.orientation() == Qt.Horizontal:
            widget.setMinimumWidth(max(widget.minimumWidth(), min_sizes[index]))
        else:
            widget.setMinimumHeight(max(widget.minimumHeight(), min_sizes[index]))
    splitter._qh_layout_initialized_v19 = True


def _qh_apply_layout_polish_v19(self: QuantHunterWindow) -> None:
    if getattr(self, "_qh_layout_polish_running_v19", False):
        return
    self._qh_layout_polish_running_v19 = True
    try:
        minimum_width, minimum_height = self._safe_window_minimum_v19()
        self.setMinimumSize(max(self.minimumWidth(), minimum_width), max(self.minimumHeight(), minimum_height))

        splitter_specs = {
            "overview_main_splitter": ([340, 1240, 380], [300, 520, 320]),
            "overview_left_notes_splitter": ([150, 150, 220], [120, 120, 160]),
            "recommend_dispatch_splitter": ([420, 780, 340], [320, 420, 280]),
            "recommend_summary_splitter": ([460, 980], [360, 520]),
            "recommend_recap_middle_splitter": ([360, 980], [300, 560]),
            "recommend_recap_bottom_splitter": ([360, 980], [300, 560]),
            "recommend_review_splitter": ([780, 560], [520, 360]),
            "broker_control_splitter": ([560, 620, 360], [320, 320, 280]),
            "broker_middle_splitter": ([560, 1040], [360, 520]),
            "broker_order_focus_splitter": ([960, 400], [560, 320]),
            "paper_trading_splitter": ([620, 920], [420, 520]),
        }
        for attr_name, (sizes, min_sizes) in splitter_specs.items():
            splitter = getattr(self, attr_name, None)
            if not isinstance(splitter, QSplitter) or splitter.count() != len(sizes):
                continue
            self._apply_splitter_layout_v19(splitter, sizes, min_sizes)

        detail_tab = getattr(self, "detail_tab", None)
        if isinstance(detail_tab, QWidget):
            for splitter in detail_tab.findChildren(QSplitter):
                if splitter.count() == 3:
                    self._apply_splitter_layout_v19(splitter, [540, 540, 540], [320, 320, 320])
                elif splitter.count() == 2:
                    self._apply_splitter_layout_v19(splitter, [720, 920], [360, 360])

        for attr_name, min_height in {
            "scan_table": 320,
            "summary_table": 280,
            "monitor_table": 280,
            "daily_pool_table": 320,
            "trade_plan_table": 300,
            "position_advice_table": 260,
            "orders_table": 320,
            "execution_table": 280,
            "paper_positions_table": 300,
            "paper_ledger_table": 300,
        }.items():
            table = getattr(self, attr_name, None)
            if isinstance(table, QTableWidget):
                table.setMinimumHeight(max(table.minimumHeight(), min_height))
                table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 42))

        for attr_name, min_height in {
            "recommend_dispatch_text": 132,
            "recommend_focus_review_text": 148,
            "recommend_queue_text": 132,
            "recommend_decision_summary_text": 220,
            "broker_status_text": 240,
            "broker_order_focus_text": 220,
            "broker_recap_text": 200,
            "order_result_text": 220,
            "detail_decision_text": 240,
            "detail_execution_text": 240,
            "detail_conclusion_text": 240,
            "paper_trading_text": 160,
        }.items():
            text = getattr(self, attr_name, None)
            if isinstance(text, QTextEdit):
                text.setMinimumHeight(max(text.minimumHeight(), min_height))
                text.setMaximumHeight(16777215)

        for attr_name, min_height in {
            "recommend_status_label": 42,
            "daily_pool_focus_label": 42,
            "orders_focus_label": 42,
            "broker_status_banner": 48,
            "paper_trading_status_label": 48,
        }.items():
            label = getattr(self, attr_name, None)
            if isinstance(label, QLabel):
                label.setMinimumHeight(max(label.minimumHeight(), min_height))
                label.setWordWrap(True)

        for name in ["scanner_workspace_scroll_area", "board_workspace_scroll_area", "config_workspace_scroll_area", "detail_workspace_scroll_area", "broker_scroll_area"]:
            scroll = getattr(self, name, None)
            if isinstance(scroll, QScrollArea):
                if not getattr(scroll, "_qh_scroll_polished_v19", False):
                    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
                    self._enable_smooth_scroll(scroll, allow_drag=True)
                    scroll._qh_scroll_polished_v19 = True
        self._qh_last_layout_polish_perf_v19 = time_module.perf_counter()
    finally:
        self._qh_layout_polish_running_v19 = False


def _qh_run_scheduled_layout_polish_v19(self: QuantHunterWindow) -> None:
    self._qh_layout_polish_due_v19 = None
    self._apply_layout_polish_v19()


def _qh_schedule_layout_polish_v19(self: QuantHunterWindow, delays: tuple[int, ...] = (0, 80, 220)) -> None:
    normalized_delays = [max(int(delay), 0) for delay in delays] or [0]
    requested_delay = min(normalized_delays)
    last_applied = float(getattr(self, "_qh_last_layout_polish_perf_v19", 0.0) or 0.0)
    now = time_module.perf_counter()
    if requested_delay == 0 and now - last_applied < 0.18:
        requested_delay = 180

    if not hasattr(self, "_qh_layout_polish_timer_v19"):
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(self._run_scheduled_layout_polish_v19)
        self._qh_layout_polish_timer_v19 = timer

    timer = self._qh_layout_polish_timer_v19
    due_at = now + (requested_delay / 1000.0)
    existing_due = getattr(self, "_qh_layout_polish_due_v19", None)
    if timer.isActive() and existing_due is not None and existing_due <= due_at + 1e-6:
        return
    timer.stop()
    self._qh_layout_polish_due_v19 = due_at
    timer.start(requested_delay)


def _qh_schedule_tab_layout_polish_v20(self: QuantHunterWindow, workspace_key: str = "") -> None:
    delay = 80 if workspace_key in {"recommend", "broker", "detail", "scanner", "board", "overview"} else 120
    self._schedule_layout_polish_v19((delay,))


def _qh_post_build_ui_tweaks_v19(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_POST_BUILD_UI_TWEAKS_V19(self)
    self._schedule_layout_polish_v19()


def _qh_navigate_to_workspace_v20(self: QuantHunterWindow, workspace_key: str, widget_name: str | None = None, select_row: str | None = None) -> None:
    _ORIGINAL_QH_NAVIGATE_TO_WORKSPACE_V20(self, workspace_key, widget_name, select_row)
    self._schedule_tab_layout_polish_v20(workspace_key)


def _qh_on_workspace_tab_changed_v20(self: QuantHunterWindow, index: int) -> None:
    _ORIGINAL_QH_ON_WORKSPACE_TAB_CHANGED_V20(self, index)
    workspace_key = ""
    if index >= 0 and index < len(WORKSPACE_TAB_ORDER):
        workspace_key = WORKSPACE_TAB_ORDER[index]
    if workspace_key == "overview" and hasattr(self, "_flush_pending_market_dashboard_render"):
        self._flush_pending_market_dashboard_render()
    self._schedule_tab_layout_polish_v20(workspace_key)


def _qh_show_event_v19(self: QuantHunterWindow, event) -> None:
    _ORIGINAL_QH_SHOW_EVENT_V19(self, event)
    self._schedule_layout_polish_v19((40,))


def _qh_resize_event_v19(self: QuantHunterWindow, event) -> None:
    _ORIGINAL_QH_RESIZE_EVENT_V19(self, event)
    self._schedule_layout_polish_v19((180,))


QuantHunterWindow._configure_splitter = _qh_configure_splitter_v19
QuantHunterWindow._safe_window_minimum_v19 = _qh_safe_window_minimum_v19
QuantHunterWindow._apply_splitter_layout_v19 = _qh_apply_splitter_layout_v19
QuantHunterWindow._apply_layout_polish_v19 = _qh_apply_layout_polish_v19
QuantHunterWindow._run_scheduled_layout_polish_v19 = _qh_run_scheduled_layout_polish_v19
QuantHunterWindow._schedule_layout_polish_v19 = _qh_schedule_layout_polish_v19
QuantHunterWindow._schedule_tab_layout_polish_v20 = _qh_schedule_tab_layout_polish_v20
QuantHunterWindow._navigate_to_workspace = _qh_navigate_to_workspace_v20
QuantHunterWindow._on_workspace_tab_changed = _qh_on_workspace_tab_changed_v20
QuantHunterWindow._post_build_ui_tweaks = _qh_post_build_ui_tweaks_v19
QuantHunterWindow.showEvent = _qh_show_event_v19
QuantHunterWindow.resizeEvent = _qh_resize_event_v19


def _qh_apply_visual_polish_v21(self: QuantHunterWindow) -> None:
    if not getattr(self, "_qh_visual_style_applied_v21", False):
        self.setStyleSheet(
            self.styleSheet()
            + """
QGroupBox#workspaceToolPanel,
QGroupBox#terminalPanel {
    border-radius: 20px;
}
QGroupBox#workspaceToolPanel {
    padding: 18px 16px 14px 16px;
}
QGroupBox#terminalPanel {
    padding: 18px 16px 14px 16px;
}
QFrame#metricCard {
    border-radius: 18px;
}
QFrame#metricCard:hover {
    border: 1px solid rgba(150, 184, 219, 0.34);
}
QLabel#metricCardTitle {
    color: #92a6bb;
    font-size: 12px;
    font-weight: 700;
}
QLabel#metricCardValue {
    color: #f7fbff;
    font-size: 22px;
    font-weight: 900;
}
QLabel#statusBanner {
    padding: 12px 16px;
}
QTextEdit#terminalConsole,
QTextEdit#marketNotePanel {
    border-radius: 16px;
    padding: 12px;
}
QTableWidget#terminalTable,
QTableWidget#marketPoolTable,
QTableWidget#recommendPoolTable {
    border-radius: 18px;
    padding: 10px;
}
QTableWidget#terminalTable::item,
QTableWidget#marketPoolTable::item,
QTableWidget#recommendPoolTable::item {
    padding-top: 9px;
    padding-bottom: 9px;
}
QPushButton#ghostButton,
QPushButton#accentButton,
QPushButton#tonalButton {
    min-height: 38px;
    padding: 8px 14px;
    border-radius: 12px;
    font-weight: 800;
}
"""
        )
        self._qh_visual_style_applied_v21 = True

    workspace_roots = []
    for attr_name in ["recommend_tab", "broker_tab", "detail_tab", "scanner_tab", "board_tab"]:
        tab = getattr(self, attr_name, None)
        if isinstance(tab, QWidget):
            workspace_roots.append(tab)
    for scroll_name in ["broker_scroll_area", "scanner_workspace_scroll_area", "board_workspace_scroll_area", "detail_workspace_scroll_area", "config_workspace_scroll_area"]:
        scroll = getattr(self, scroll_name, None)
        if isinstance(scroll, QScrollArea) and scroll.widget() is not None:
            workspace_roots.append(scroll.widget())

    for root in workspace_roots:
        layout = root.layout()
        if layout is not None:
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(max(layout.spacing(), 12))
        for group in root.findChildren(QGroupBox):
            group.setMinimumHeight(max(group.minimumHeight(), 96))
            inner_layout = group.layout()
            if inner_layout is not None:
                inner_layout.setContentsMargins(16, 14, 16, 14)
                inner_layout.setSpacing(max(inner_layout.spacing(), 10))
        for frame in root.findChildren(QFrame, "metricCard"):
            frame.setMinimumHeight(max(frame.minimumHeight(), 92))
        for text in root.findChildren(QTextEdit):
            text.setViewportMargins(2, 2, 2, 2)
        for button in root.findChildren(QPushButton):
            button.setMinimumHeight(max(button.minimumHeight(), 38))
            button.setCursor(Qt.PointingHandCursor)

    for attr_name in [
        "recommend_dispatch_text",
        "recommend_focus_review_text",
        "recommend_queue_text",
        "broker_status_text",
        "broker_order_focus_text",
        "broker_recap_text",
        "order_result_text",
        "paper_trading_text",
    ]:
        widget = getattr(self, attr_name, None)
        if isinstance(widget, QTextEdit):
            widget.document().setDocumentMargin(10)

    for attr_name in [
        "recommend_status_label",
        "daily_pool_focus_label",
        "orders_focus_label",
        "broker_status_banner",
        "paper_trading_status_label",
    ]:
        label = getattr(self, attr_name, None)
        if isinstance(label, QLabel):
            label.setMinimumHeight(max(label.minimumHeight(), 46))
            label.setContentsMargins(0, 2, 0, 2)

    for attr_name in ["paper_trading_box"]:
        panel = getattr(self, attr_name, None)
        if isinstance(panel, QGroupBox):
            panel.setMinimumHeight(max(panel.minimumHeight(), 520))


_ORIGINAL_QH_APPLY_LAYOUT_POLISH_V21 = QuantHunterWindow._apply_layout_polish_v19


def _qh_apply_terminal_table_governance_v22(self: QuantHunterWindow) -> None:
    if getattr(self, "_qh_terminal_table_governance_applied_v22", False):
        return
    table_specs = {
        "daily_pool_table": {
            "hidden": [20],
            "content": {0, 2, 5, 6, 7, 8, 9, 18, 21, 22},
            "stretch": {1, 19},
            "widths": {0: 78, 2: 92, 3: 128, 4: 132, 5: 84, 6: 92, 7: 96, 8: 110, 9: 104, 18: 92, 21: 112, 22: 120},
            "min_height": 460,
        },
        "trade_plan_table": {
            "hidden": [13],
            "content": {0, 2, 4, 6, 7, 8, 9, 10, 11, 12},
            "stretch": {1, 5, 14},
            "widths": {0: 78, 2: 92, 3: 128, 4: 82, 6: 92, 7: 96, 8: 110, 9: 104, 10: 92, 11: 92, 12: 92},
            "min_height": 320,
        },
        "position_advice_table": {
            "content": {0, 2, 3, 4, 5, 6, 7},
            "stretch": {1, 8},
            "widths": {0: 82, 2: 96, 3: 88, 4: 94, 5: 110, 6: 110, 7: 104},
            "min_height": 280,
        },
        "orders_table": {
            "hidden": [5, 6, 7, 8, 10],
            "content": {0, 2, 3, 4, 12},
            "stretch": {1, 9, 11},
            "widths": {0: 86, 2: 88, 3: 94, 4: 86, 12: 94},
            "min_height": 360,
        },
        "execution_table": {
            "content": {1, 2, 4, 5, 6},
            "stretch": {0, 3, 7, 8},
            "widths": {1: 96, 2: 96, 4: 88, 5: 92, 6: 82},
            "min_height": 320,
        },
        "paper_positions_table": {
            "content": {2, 3, 4, 5, 7, 8},
            "stretch": {0, 1, 9},
            "widths": {2: 104, 3: 84, 4: 92, 5: 92, 7: 96, 8: 98},
            "min_height": 320,
        },
        "paper_ledger_table": {
            "content": {0, 1, 3, 4, 5, 6, 8, 9, 10},
            "stretch": {2, 7, 11},
            "widths": {0: 92, 1: 150, 3: 88, 4: 88, 5: 78, 6: 104, 8: 86, 9: 92, 10: 92},
            "min_height": 320,
        },
    }
    for attr_name, spec in table_specs.items():
        table = getattr(self, attr_name, None)
        if not isinstance(table, QTableWidget):
            continue
        header = table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(58)
        table.setMinimumHeight(max(table.minimumHeight(), spec.get("min_height", 260)))
        table.verticalHeader().setDefaultSectionSize(max(table.verticalHeader().defaultSectionSize(), 44))
        table.setShowGrid(False)
        table.setWordWrap(False)
        table.setTextElideMode(Qt.ElideRight)
        for column in range(table.columnCount()):
            if column in spec.get("hidden", []):
                table.setColumnHidden(column, True)
                continue
            table.setColumnHidden(column, False)
            if column in spec.get("stretch", set()):
                header.setSectionResizeMode(column, QHeaderView.Stretch)
            elif column in spec.get("content", set()):
                header.setSectionResizeMode(column, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(column, QHeaderView.Interactive)
            if column in spec.get("widths", {}):
                table.setColumnWidth(column, max(table.columnWidth(column), spec["widths"][column]))
    self._qh_terminal_table_governance_applied_v22 = True


def _qh_apply_toolbar_density_v22(self: QuantHunterWindow) -> None:
    if getattr(self, "_qh_toolbar_density_applied_v22", False):
        return
    button_rows = []
    for panel_name in ["recommend_tab", "broker_tab"]:
        panel = getattr(self, panel_name, None)
        if isinstance(panel, QWidget):
            button_rows.extend(panel.findChildren(QFrame))
    for frame in button_rows:
        if not bool(frame.property("actionRow")):
            continue
        layout = frame.layout()
        if isinstance(layout, (QHBoxLayout, QVBoxLayout, QGridLayout)):
            layout.setContentsMargins(14, 12, 14, 12)
            layout.setSpacing(max(layout.spacing(), 10))
        for button in frame.findChildren(QPushButton):
            button.setMinimumWidth(max(button.minimumWidth(), 112))
            button.setMinimumHeight(max(button.minimumHeight(), 38))

    for attr_name in [
        "paper_initialize_button",
        "paper_run_button",
        "paper_export_button",
        "paper_reset_button",
    ]:
        button = getattr(self, attr_name, None)
        if isinstance(button, QPushButton):
            button.setMinimumWidth(max(button.minimumWidth(), 132))
    self._qh_toolbar_density_applied_v22 = True


def _qh_apply_layout_polish_v21(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_APPLY_LAYOUT_POLISH_V21(self)
    self._apply_visual_polish_v21()
    self._apply_terminal_table_governance_v22()
    self._apply_toolbar_density_v22()


QuantHunterWindow._apply_visual_polish_v21 = _qh_apply_visual_polish_v21
QuantHunterWindow._apply_terminal_table_governance_v22 = _qh_apply_terminal_table_governance_v22
QuantHunterWindow._apply_toolbar_density_v22 = _qh_apply_toolbar_density_v22
QuantHunterWindow._apply_layout_polish_v19 = _qh_apply_layout_polish_v21


def _qh_set_widget_spotlight_v23(self: QuantHunterWindow, widget: QWidget | None, tone: str) -> None:
    if widget is None:
        return
    normalized = tone if tone in {"buy", "watch", "risk"} else "idle"
    if widget.property("spotlight") == normalized:
        return
    widget.setProperty("spotlight", normalized)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


def _qh_focus_tone_from_runtime_v23(self: QuantHunterWindow) -> str:
    selected_intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    if selected_intent is not None:
        side = str(getattr(selected_intent, "side", "") or "").upper()
        if side in {"SELL", "REDUCE"}:
            return "risk"
        if side == "BUY":
            return "buy"
        return "watch"

    current_recommend = None
    if hasattr(self, "_explicit_recommendation_focus"):
        current_recommend = self._explicit_recommendation_focus()
    if current_recommend is None and hasattr(self, "_selected_daily_pool_recommendation"):
        current_recommend = self._selected_daily_pool_recommendation()
    if current_recommend is not None and hasattr(self, "_focus_banner_tone"):
        return self._focus_banner_tone(
            symbol=getattr(current_recommend, "symbol", "") or "",
            recommendation=current_recommend,
            scan_row=None,
        )

    submission = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    if submission is not None:
        side = str(submission.get("side", "") or "").upper()
        if side in {"SELL", "REDUCE"} or str(submission.get("order_status", "") or "").upper() == "FAILED":
            return "risk"
        if side == "BUY":
            return "buy"
        return "watch"
    return "idle"


def _qh_apply_focus_spotlight_v23(self: QuantHunterWindow) -> None:
    tone = self._focus_tone_from_runtime_v23() if hasattr(self, "_focus_tone_from_runtime_v23") else "idle"

    for attr_name in [
        "recommend_status_label",
        "daily_pool_focus_label",
        "trade_plan_focus_label",
        "orders_focus_label",
        "broker_status_banner",
        "paper_trading_status_label",
        "scanner_focus_banner",
        "board_focus_banner",
        "detail_focus_banner",
    ]:
        self._set_widget_spotlight_v23(getattr(self, attr_name, None), tone)

    table_tones = {
        "daily_pool_table": tone,
        "trade_plan_table": tone,
        "position_advice_table": "risk" if tone == "risk" else "watch",
        "orders_table": tone,
        "execution_table": tone,
        "paper_positions_table": "buy" if tone == "buy" else tone,
        "paper_ledger_table": tone,
    }
    for attr_name, widget_tone in table_tones.items():
        self._set_widget_spotlight_v23(getattr(self, attr_name, None), widget_tone)


def _qh_apply_focus_spotlight_style_v23(self: QuantHunterWindow) -> None:
    if getattr(self, "_qh_focus_spotlight_style_applied_v23", False):
        return
    self.setStyleSheet(
        self.styleSheet()
        + """
QLabel#statusBanner[spotlight="buy"],
QLabel#workspaceFocusBanner[spotlight="buy"] {
    border-color: rgba(90, 225, 159, 0.42);
    box-shadow: none;
}
QLabel#statusBanner[spotlight="watch"],
QLabel#workspaceFocusBanner[spotlight="watch"] {
    border-color: rgba(255, 209, 102, 0.42);
}
QLabel#statusBanner[spotlight="risk"],
QLabel#workspaceFocusBanner[spotlight="risk"] {
    border-color: rgba(255, 123, 114, 0.44);
}
QLabel#focusStateLabel[spotlight="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.34);
    background: rgba(12, 30, 20, 0.96);
}
QLabel#focusStateLabel[spotlight="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.30);
    background: rgba(34, 29, 15, 0.96);
}
QLabel#focusStateLabel[spotlight="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.34);
    background: rgba(42, 18, 20, 0.96);
}
QTableWidget[spotlight="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.34);
    background: rgba(12, 20, 18, 0.98);
}
QTableWidget[spotlight="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.32);
}
QTableWidget[spotlight="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.34);
    background: rgba(22, 14, 16, 0.98);
}
"""
    )
    self._qh_focus_spotlight_style_applied_v23 = True


_ORIGINAL_QH_REFRESH_WORKSPACE_FOCUS_BANNERS_V23 = QuantHunterWindow._refresh_workspace_focus_banners
_ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_STATUS_V23 = QuantHunterWindow._refresh_recommend_focus_status
_ORIGINAL_QH_REFRESH_BROKER_ORDER_FOCUS_V23 = QuantHunterWindow._refresh_broker_order_focus
_ORIGINAL_QH_REFRESH_SUBMISSION_FOCUS_V23 = QuantHunterWindow._refresh_submission_focus
_ORIGINAL_QH_ON_DAILY_POOL_SELECTION_CHANGED_V23 = QuantHunterWindow._on_daily_pool_selection_changed


def _qh_refresh_workspace_focus_banners_v23(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_WORKSPACE_FOCUS_BANNERS_V23(self)
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


def _qh_refresh_recommend_focus_status_v23(self: QuantHunterWindow, row: RecommendationRow | None = None) -> None:
    _ORIGINAL_QH_REFRESH_RECOMMEND_FOCUS_STATUS_V23(self, row)
    label = getattr(self, "recommend_status_label", None)
    current = row
    if current is None and hasattr(self, "_current_recommend_focus"):
        current = self._current_recommend_focus()
    runtime_phase = ""
    runtime_hint = ""
    if current is not None:
        runtime_phase, runtime_hint = tail_buy_runtime_status(current)
    if label is not None and runtime_phase:
        base_text = (getattr(label, "text", lambda: "")() or "").strip()
        if base_text:
            self._set_label_text_if_changed(label, f"{base_text} | 尾盘阶段 {runtime_phase}")
    if label is not None:
        if current is None:
            _qh_set_tooltip_v7(label, "推荐状态：等待高优先候选同步后，再查看送审理由、价格计划和催化消息。")
        else:
            symbol = getattr(current, "symbol", "") or ""
            stock_name = getattr(current, "stock_name", "") or self._stock_name_for_symbol(symbol)
            stock_id = getattr(current, "stock_id", "") or self._stock_id_for_symbol(symbol)
            theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
            action_text = self._display_action(getattr(current, "action", "WATCH"))
            price_brief = self._recommend_price_brief(current) if hasattr(self, "_recommend_price_brief") else "等待价格计划同步"
            news_lines = self._news_digest_lines_for_symbol(symbol, limit=1) if hasattr(self, "_news_digest_lines_for_symbol") else []
            _qh_set_tooltip_v7(
                label,
                "\n".join(
                    [
                        f"焦点：{stock_name} ({stock_id} / {symbol})",
                        f"主线：{theme_name} | 动作：{action_text}",
                        f"价格计划：{price_brief}",
                        f"尾盘阶段：{runtime_phase or '常规观察'}",
                        f"执行节奏：{runtime_hint or '先核对送审理由、价格计划和消息催化。'}",
                        f"消息：{news_lines[0] if news_lines else '暂无近期催化'}",
                    ]
                ),
            )
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


def _qh_refresh_broker_order_focus_v23(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_BROKER_ORDER_FOCUS_V23(self)
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


def _qh_refresh_submission_focus_v23(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_SUBMISSION_FOCUS_V23(self)
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


def _qh_on_daily_pool_selection_changed_v23(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_ON_DAILY_POOL_SELECTION_CHANGED_V23(self)
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


_ORIGINAL_QH_APPLY_LAYOUT_POLISH_V23 = QuantHunterWindow._apply_layout_polish_v19


def _qh_apply_layout_polish_v23(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_APPLY_LAYOUT_POLISH_V23(self)
    if hasattr(self, "_apply_focus_spotlight_style_v23"):
        self._apply_focus_spotlight_style_v23()
    if hasattr(self, "_apply_focus_spotlight_v23"):
        self._apply_focus_spotlight_v23()


QuantHunterWindow._set_widget_spotlight_v23 = _qh_set_widget_spotlight_v23
QuantHunterWindow._focus_tone_from_runtime_v23 = _qh_focus_tone_from_runtime_v23
QuantHunterWindow._apply_focus_spotlight_v23 = _qh_apply_focus_spotlight_v23
QuantHunterWindow._apply_focus_spotlight_style_v23 = _qh_apply_focus_spotlight_style_v23
QuantHunterWindow._refresh_workspace_focus_banners = _qh_refresh_workspace_focus_banners_v23
QuantHunterWindow._refresh_recommend_focus_status = _qh_refresh_recommend_focus_status_v23
QuantHunterWindow._refresh_broker_order_focus = _qh_refresh_broker_order_focus_v23
QuantHunterWindow._refresh_submission_focus = _qh_refresh_submission_focus_v23
QuantHunterWindow._on_daily_pool_selection_changed = _qh_on_daily_pool_selection_changed_v23
QuantHunterWindow._apply_layout_polish_v19 = _qh_apply_layout_polish_v23


_ORIGINAL_QH_GENERATE_ORDER_SUGGESTIONS_V24 = QuantHunterWindow.generate_order_suggestions
_ORIGINAL_QH_FOCUS_TONE_FROM_RUNTIME_V24 = QuantHunterWindow._focus_tone_from_runtime_v23
_ORIGINAL_QH_APPLY_FOCUS_SPOTLIGHT_V24 = QuantHunterWindow._apply_focus_spotlight_v23
_ORIGINAL_QH_APPLY_FOCUS_SPOTLIGHT_STYLE_V24 = QuantHunterWindow._apply_focus_spotlight_style_v23


def _qh_generate_order_suggestions_v24(self: QuantHunterWindow) -> None:
    if not getattr(self, "scan_rows", []):
        focus_row = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
        if focus_row is not None:
            symbol = getattr(focus_row, "symbol", "") or ""
            if symbol and hasattr(self, "_queue_symbol_to_watchlist"):
                self._queue_symbol_to_watchlist(symbol)
                if hasattr(self, "broker_status_banner"):
                    self._set_label_text_if_changed(
                        self.broker_status_banner,
                        f"交易状态：已根据推荐焦点 {getattr(focus_row, 'stock_name', '') or self._stock_name_for_symbol(symbol)} 自动建立委托候选。",
                    )
        if getattr(self, "daily_pool_rows", []):
            self.scan_rows = list(getattr(self, "daily_pool_rows", []) or [])
    _ORIGINAL_QH_GENERATE_ORDER_SUGGESTIONS_V24(self)


def _qh_focus_tone_from_runtime_v24(self: QuantHunterWindow) -> str:
    submission = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    if submission is not None:
        side = str(submission.get("side", "") or "").upper()
        status = str(submission.get("order_status", "") or "").upper()
        fill_status = str(submission.get("fill_status", "") or "").upper()
        if side in {"SELL", "REDUCE"} or status == "FAILED" or fill_status in {"REJECTED", "CANCELLED"}:
            return "risk"
        if side == "BUY":
            return "buy"
        return "watch"
    return _ORIGINAL_QH_FOCUS_TONE_FROM_RUNTIME_V24(self)


def _qh_apply_focus_spotlight_v24(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_APPLY_FOCUS_SPOTLIGHT_V24(self)
    tone = self._focus_tone_from_runtime_v23() if hasattr(self, "_focus_tone_from_runtime_v23") else "idle"
    for attr_name in [
        "broker_order_focus_text",
        "order_result_text",
        "broker_recap_text",
        "detail_execution_text",
        "detail_conclusion_text",
        "recommend_dispatch_text",
        "recommend_focus_review_text",
        "recommend_queue_text",
    ]:
        self._set_widget_spotlight_v23(getattr(self, attr_name, None), tone)


def _qh_apply_focus_spotlight_style_v24(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_APPLY_FOCUS_SPOTLIGHT_STYLE_V24(self)
    if getattr(self, "_qh_focus_spotlight_text_style_applied_v24", False):
        return
    self.setStyleSheet(
        self.styleSheet()
        + """
QTextEdit[spotlight="buy"] {
    border: 1px solid rgba(77, 226, 154, 0.34);
    background: rgba(11, 22, 18, 0.98);
}
QTextEdit[spotlight="watch"] {
    border: 1px solid rgba(255, 209, 102, 0.30);
    background: rgba(22, 20, 14, 0.98);
}
QTextEdit[spotlight="risk"] {
    border: 1px solid rgba(255, 123, 114, 0.34);
    background: rgba(28, 15, 17, 0.98);
}
"""
    )
    self._qh_focus_spotlight_text_style_applied_v24 = True


QuantHunterWindow.generate_order_suggestions = _qh_generate_order_suggestions_v24
QuantHunterWindow._focus_tone_from_runtime_v23 = _qh_focus_tone_from_runtime_v24
QuantHunterWindow._apply_focus_spotlight_v23 = _qh_apply_focus_spotlight_v24
QuantHunterWindow._apply_focus_spotlight_style_v23 = _qh_apply_focus_spotlight_style_v24


def _qh_generate_order_suggestions_v25(self: QuantHunterWindow) -> None:
    rows = list(getattr(self, "scan_rows", []) or [])
    if not rows and getattr(self, "daily_pool_rows", []):
        rows = list(getattr(self, "daily_pool_rows", []) or [])
        self.scan_rows = list(rows)

    focus_symbol = ""
    focus_row = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
    if focus_row is not None:
        focus_symbol = getattr(focus_row, "symbol", "") or ""
    if not focus_symbol:
        focus_symbol = getattr(self, "active_symbol", "") or ""

    if not rows and not getattr(getattr(self, "current_trade_plan", None), "decisions", []):
        QMessageBox.information(self, "提示", "请先刷新市场，生成每日股票池或交易计划。")
        return
    try:
        per_trade_budget = float(self.per_trade_budget_input.text().strip())
    except ValueError:
        QMessageBox.critical(self, "参数错误", "单笔预算必须填写数字。")
        return

    if hasattr(self, "broker_status_banner"):
        self._set_label_text_if_changed(
            self.broker_status_banner,
            "交易状态：正在生成委托建议，请等待风险测算和执行检查完成。",
        )

    filtered_rows = list(rows)
    watchlist = list(getattr(getattr(self, "state", None), "watchlist", []) or [])
    if watchlist:
        watchlist_set = set(watchlist)
        candidate_rows = [row for row in filtered_rows if getattr(row, "symbol", "") in watchlist_set]
        if candidate_rows:
            filtered_rows = candidate_rows
        elif focus_symbol:
            candidate_rows = [row for row in filtered_rows if getattr(row, "symbol", "") == focus_symbol]
            if candidate_rows:
                filtered_rows = candidate_rows

    order_intents = EastmoneyBrokerAdapter().build_order_intents(filtered_rows, per_trade_budget)
    if not order_intents:
        plan = getattr(self, "current_trade_plan", None)
        decisions = list(getattr(plan, "decisions", []) or [])
        if watchlist:
            watchlist_set = set(watchlist)
            filtered_decisions = [item for item in decisions if getattr(item, "symbol", "") in watchlist_set]
            if filtered_decisions:
                decisions = filtered_decisions
            elif focus_symbol:
                focused_decisions = [item for item in decisions if getattr(item, "symbol", "") == focus_symbol]
                if focused_decisions:
                    decisions = focused_decisions
        elif focus_symbol:
            focused_decisions = [item for item in decisions if getattr(item, "symbol", "") == focus_symbol]
            if focused_decisions:
                decisions = focused_decisions

        fallback_intents = []
        for item in decisions[:5]:
            action = str(getattr(item, "action", "") or "").upper()
            entry = float(getattr(item, "planned_entry", 0.0) or 0.0)
            stop = float(getattr(item, "planned_stop", 0.0) or 0.0)
            target = float(getattr(item, "planned_target", 0.0) or 0.0)
            sizing_budget = float(getattr(item, "suggested_budget", 0.0) or 0.0) or per_trade_budget
            quantity = int(sizing_budget / entry) if entry > 0 else 0
            quantity = (quantity // 100) * 100
            if action != "BUY" or entry <= 0 or stop <= 0 or target <= entry or quantity < 100:
                continue
            fallback_intents.append(
                OrderIntent(
                    symbol=getattr(item, "symbol", "") or "",
                    side="BUY",
                    price=round(entry, 3),
                    quantity=quantity,
                    stop_price=round(stop, 3),
                    target_price=round(target, 3),
                    signal_date="计划池",
                    reason=str(getattr(item, "rationale", "") or "交易计划自动生成"),
                )
            )
        order_intents = fallback_intents

    self.order_intents = order_intents
    self._fill_orders()
    self._refresh_broker_order_focus()
    self._refresh_submission_focus()

    if self.order_intents:
        if hasattr(self, "orders_table") and self.orders_table.rowCount() > 0:
            self.orders_table.selectRow(0)
        if hasattr(self, "orders_focus_label"):
            top_intent = self.order_intents[0]
            self._set_label_text_if_changed(
                self.orders_focus_label,
                f"委托焦点：已生成 {len(self.order_intents)} 笔委托建议，优先关注 {self._stock_name_for_symbol(top_intent.symbol)}",
            )
        self._refresh_broker_status(extra=f"已生成 {len(self.order_intents)} 笔委托建议，等待确认提交。")
    else:
        self._refresh_broker_status(extra="当前参数下暂无新的买入建议，请检查预算、观察池和主线闸门。")


QuantHunterWindow.generate_order_suggestions = _qh_generate_order_suggestions_v25


_ORDER_CONFIRMATION_DIALOG_V25 = OrderConfirmationDialog
_ORIGINAL_QH_REFRESH_BROKER_STATUS_V26 = QuantHunterWindow._refresh_broker_status
_ORIGINAL_QH_REFRESH_SUBMISSION_FOCUS_V26 = QuantHunterWindow._refresh_submission_focus
_ORIGINAL_QH_CONFIRM_AND_SUBMIT_ORDERS_V26 = QuantHunterWindow.confirm_and_submit_orders


class OrderConfirmationDialog(_ORDER_CONFIRMATION_DIALOG_V25):
    def __init__(
        self,
        profile: BrokerProfile,
        intents: list[OrderIntent],
        adapter: EastmoneyBrokerAdapter,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(profile, intents, adapter, parent)
        self.setWindowTitle("一键下单确认")
        self.resize(1080, 660)
        self.setStyleSheet(
            """
QDialog {
    background: #141b24;
    color: #edf3fb;
}
QGroupBox {
    border: 1px solid rgba(112, 130, 153, 0.24);
    border-radius: 16px;
    margin-top: 14px;
    padding: 16px 14px 12px 14px;
    background: rgba(21, 29, 40, 0.98);
    font-weight: 800;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
    color: #f6fbff;
}
QLabel {
    color: #dce6f2;
}
QCheckBox {
    color: #f5f8fc;
    spacing: 8px;
    font-weight: 700;
}
QPushButton {
    background: #273140;
    color: #eef4fb;
    border: 1px solid #435167;
    border-radius: 12px;
    padding: 10px 18px;
    min-height: 18px;
    font-weight: 800;
}
QPushButton:hover {
    background: #314052;
}
QPushButton:disabled {
    background: #222a34;
    color: #79889b;
    border-color: #394657;
}
QPushButton#submitAction {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f0aa4d, stop:1 #ffd166);
    color: #151b23;
    border: none;
}
QPushButton#submitAction:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f5b459, stop:1 #ffda73);
}
QTextEdit, QTableWidget {
    background: rgba(12, 17, 24, 0.98);
    border: 1px solid rgba(112, 130, 153, 0.18);
    border-radius: 14px;
    color: #e4ecf5;
}
QHeaderView::section {
    background: rgba(29, 39, 51, 0.94);
    color: #d7e2ef;
    border: none;
    padding: 10px 8px;
    font-weight: 800;
}
"""
        )

        total_orders = len(intents)
        buy_count = sum(1 for item in intents if str(getattr(item, "side", "") or "").upper() == "BUY")
        sell_count = sum(1 for item in intents if str(getattr(item, "side", "") or "").upper() in {"SELL", "REDUCE"})
        estimated_budget = sum(float(getattr(item, "price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0) for item in intents if str(getattr(item, "side", "") or "").upper() == "BUY")
        top_symbols = []
        for item in intents[:3]:
            symbol = getattr(item, "symbol", "") or ""
            top_symbols.append(symbol)
        summary_box = QGroupBox("提交前总览")
        summary_layout = QVBoxLayout(summary_box)
        summary_intro = QLabel(
            f"本次将提交 {total_orders} 笔委托，其中买入 {buy_count} 笔、卖减 {sell_count} 笔，预计买入占用 {estimated_budget:,.0f}。"
        )
        summary_intro.setWordWrap(True)
        summary_layout.addWidget(summary_intro)
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setMinimumHeight(132)
        self.summary_text.setMaximumHeight(170)
        summary_lines = [
            "确认步骤",
            "1. 核对账户、策略 ID、SDK 与桥接解释器。",
            "2. 核对本次焦点股票、价格、止损、目标与仓位。",
            "3. 勾选确认后提交，提交完成后会自动定位到最新回执。",
            "",
            f"焦点标的：{' / '.join(top_symbols) if top_symbols else '暂无'}",
            f"交易模式：{DISPLAY_TEXT['mode'].get(profile.mode or '', profile.mode or '-')}",
            f"SDK 状态：{'可直接调用' if adapter.diagnose_environment(profile).get('direct_ready') else ('可桥接调用' if adapter.diagnose_environment(profile).get('bridge_ready') else '当前未就绪')}",
        ]
        self.summary_text.setPlainText("\n".join(summary_lines))
        summary_layout.addWidget(self.summary_text)
        layout = self.layout()
        if isinstance(layout, QVBoxLayout):
            layout.insertWidget(1, summary_box)

        self.confirm_checkbox.setText("我已核对账户、委托、止损与风险后，继续提交。")
        self.submit_button.setText("确认并提交")
        self.submit_button.setObjectName("submitAction")

    @staticmethod
    def confirm(
        profile: BrokerProfile,
        intents: list[OrderIntent],
        adapter: EastmoneyBrokerAdapter,
        parent: QWidget | None = None,
    ) -> bool:
        dialog = OrderConfirmationDialog(profile, intents, adapter, parent)
        return dialog.exec() == QDialog.Accepted


def _qh_update_broker_action_flow_v26(self: QuantHunterWindow) -> None:
    order_count = len(getattr(self, "order_intents", []) or [])
    submit_count = len(getattr(self, "order_submission_records", []) or [])
    latest_symbol = ""
    if submit_count:
        latest_symbol = str(getattr(self, "order_submission_records", [])[-1].get("symbol", "") or "")
    elif order_count:
        latest_symbol = str(getattr(self, "order_intents", [None])[0].symbol if getattr(self, "order_intents", []) else "")

    button = getattr(self, "confirm_submit_orders_button", None)
    if isinstance(button, QPushButton):
        button.setEnabled(order_count > 0)
        if order_count > 0:
            button.setText(f"确认并提交委托 ({order_count})")
            button.setToolTip("已生成委托建议，可以打开确认弹窗并提交。")
        else:
            button.setText("确认并提交委托")
            button.setToolTip("请先从推荐池生成委托建议。")

    generate_button = getattr(self, "generate_order_suggestions_button", None)
    if isinstance(generate_button, QPushButton):
        focus_symbol = latest_symbol or (getattr(self, "active_symbol", "") or "")
        if focus_symbol:
            generate_button.setToolTip(f"当前会优先围绕 {self._stock_name_for_symbol(focus_symbol)} 生成委托建议。")
        else:
            generate_button.setToolTip("从每日推荐池或交易计划自动生成委托建议。")

    if hasattr(self, "broker_status_banner"):
        if submit_count:
            symbol = latest_symbol
            stock_name = self._stock_name_for_symbol(symbol) if symbol else "最新委托"
            self._set_label_text_if_changed(
                self.broker_status_banner,
                f"交易状态：已有 {submit_count} 条提交回执，当前聚焦 {stock_name} 的执行反馈。",
            )
        elif order_count:
            self._set_label_text_if_changed(
                self.broker_status_banner,
                f"交易状态：已生成 {order_count} 笔待提交委托，下一步打开确认弹窗并核对后提交。",
            )
        else:
            self._set_label_text_if_changed(
                self.broker_status_banner,
                "交易状态：先从推荐池生成委托，再进入确认提交流程。",
            )

    status_text = (
        f"交易流程：已生成 {order_count} 笔待提交委托，下一步打开确认弹窗完成提交。"
        if order_count
        else ("交易流程：已有成交回执，可在下方继续回看执行偏差。" if submit_count else "交易流程：先从推荐池生成委托，再进入确认提交流程。")
    )
    if hasattr(self, "broker_execution_text"):
        current = self.broker_execution_text.toPlainText().strip()
        if (not current) or current.startswith("交易流程：") or "生成盘中计划后" in current:
            self._set_plain_text_if_changed(
                self.broker_execution_text,
                "\n".join(
                    [
                        status_text,
                        "",
                        "盘中流程",
                        "1. 从推荐池选中焦点股票，生成盘中委托建议。",
                        "2. 在下单确认弹窗中核对账户、价格、仓位与风险。",
                        "3. 提交后自动聚焦最新回执，并同步到成交回顾与复盘区。",
                    ]
                ),
            )


def _qh_refresh_broker_status_v26(self: QuantHunterWindow, extra: str = "") -> None:
    _ORIGINAL_QH_REFRESH_BROKER_STATUS_V26(self, extra)
    self._update_broker_action_flow_v26()


def _qh_refresh_submission_focus_v26(self: QuantHunterWindow) -> None:
    _ORIGINAL_QH_REFRESH_SUBMISSION_FOCUS_V26(self)
    self._update_broker_action_flow_v26()
    record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
    if record is None:
        return

    symbol = str(record.get("symbol", "") or "")
    stock_name = self._stock_name_for_symbol(symbol) if symbol else "最新回执"
    stock_id = self._stock_id_for_symbol(symbol) if symbol else "--"
    failure_reason = str(record.get("failure_reason", "") or "")
    message = str(record.get("message", "") or "")
    intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
    recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
    price_snapshot = self._recommend_price_snapshot(recommendation) if recommendation is not None and hasattr(self, "_recommend_price_snapshot") else {}
    price_brief = self._recommend_price_brief(recommendation) if recommendation is not None and hasattr(self, "_recommend_price_brief") else ""
    news_lines = self._news_digest_lines_for_symbol(symbol, limit=2) if hasattr(self, "_news_digest_lines_for_symbol") else []
    recommend_context_lines = _qh_broker_recommend_context_v45(
        price_brief=price_brief,
        news_lines=news_lines,
    )
    summary = _qh_broker_execution_summary_v41(
        stock_name=stock_name,
        stock_id=stock_id,
        symbol=symbol,
        order_status_text=self._display_order_status(str(record.get("order_status", "") or "")),
        fill_status_text=self._display_fill_status(str(record.get("fill_status", "") or "")),
        failure_reason=failure_reason,
        message=message,
    )
    followup = _qh_broker_execution_followup_v42(
        stage=summary["stage"],
        has_recommendation=recommendation is not None,
        has_intent=intent is not None,
    )
    repair_hint = _qh_broker_repair_hint_v43(
        failure_reason=failure_reason,
        message=message,
        has_recommendation=recommendation is not None,
    )
    parameter_alignment = _qh_broker_parameter_alignment_v46(
        side=str(record.get("side", "") or ""),
        order_price=record.get("price", ""),
        plan_entry=price_snapshot.get("entry"),
        plan_stop=price_snapshot.get("stop"),
        plan_target=price_snapshot.get("target"),
    )
    resolution_action = _qh_broker_resolution_action_v47(
        stage=summary["stage"],
        repair_headline=repair_hint["headline"],
        parameter_headline=parameter_alignment["headline"],
        has_recommendation=recommendation is not None,
        channel_text=self.auth_channel_combo.currentText() if hasattr(self, "auth_channel_combo") else "东方财富",
    )
    terminal_brief = _qh_broker_terminal_brief_v48(
        stock_name=stock_name,
        stock_id=stock_id,
        stage=summary["stage"],
        mainline_signal=getattr(recommendation, "mainline_flow_signal", "") if recommendation is not None else "待确认",
        parameter_headline=parameter_alignment["headline"],
        resolution_target=resolution_action["target"],
    )
    panel_conclusion = _qh_broker_panel_conclusion_v49(
        stage=summary["stage"],
        parameter_headline=parameter_alignment["headline"],
        resolution_target=resolution_action["target"],
    )
    execution_deck = _qh_broker_execution_deck_v50(
        stock_name=stock_name,
        stock_id=stock_id,
        symbol=symbol,
        side_text=self._display_action(record.get("side", "")),
        quantity=str(record.get("quantity", "--") or "--"),
        price=str(record.get("price", "--") or "--"),
        mainline_signal=getattr(recommendation, "mainline_flow_signal", "") if recommendation is not None else "待确认",
        mainline_stage=getattr(recommendation, "mainline_stage", "") if recommendation is not None else "待确认",
        stage=summary["stage"],
        parameter_headline=parameter_alignment["headline"],
        repair_headline=repair_hint["headline"],
        resolution_target=resolution_action["target"],
    )
    execution_tone = _qh_broker_execution_tone_v44(summary["stage"])

    if hasattr(self, "order_result_text"):
        lines = [
            "执行回放",
            "",
            panel_conclusion,
            f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"执行阶段：{summary['stage']} | 时间：{record.get('timestamp', '--')}",
            f"动作：{self._display_action(record.get('side', ''))} | 价格：{record.get('price', '--')} | 数量：{record.get('quantity', '--')}",
            f"状态判断：{summary['judgement']}",
            summary["next_step"],
            f"链路建议：{followup['headline']} | {followup['detail']}",
            f"处理建议：{repair_hint['headline']} | {repair_hint['detail']}",
            f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
            f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
            *recommend_context_lines,
            f"订单状态：{summary['order_status']} | 成交状态：{summary['fill_status']}",
            f"失败原因：{failure_reason or '无'}",
            f"反馈信息：{message or '等待更多反馈'}",
        ]
        self._set_plain_text_if_changed(self.order_result_text, "\n".join(lines))

    if hasattr(self, "broker_recap_text"):
        lines = [
            f"成交回顾：{stock_name}",
            panel_conclusion,
            f"执行阶段：{summary['stage']}",
            f"当前判断：{summary['judgement']}",
            f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
        ]
        if recommendation is not None:
            lines.append(
                f"主线参考：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}"
            )
            lines.append(f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))}")
            lines.append(f"推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}")
        lines.extend(recommend_context_lines)
        lines.append(summary["next_step"])
        lines.append(f"链路建议：{followup['headline']} | {followup['detail']}")
        lines.append(f"处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}")
        lines.append(f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}")
        lines.append(f"优先入口：{resolution_action['target']} | {resolution_action['detail']}")
        if message:
            lines.append(f"系统反馈：{message}")
        if failure_reason:
            lines.append(f"需要处理：{failure_reason}")
        else:
            lines.append("执行偏差：继续观察成交结果，并核对是否偏离原计划的价格和仓位。")
        self._set_plain_text_if_changed(self.broker_recap_text, "\n".join(lines))

    if hasattr(self, "broker_mainline_review_text"):
        lines = [
            f"主线闸门审查：{stock_name}",
            panel_conclusion,
            f"执行阶段：{summary['stage']} | 链路建议：{followup['headline']}",
        ]
        if recommendation is not None:
            lines.extend(
                [
                    f"主线状态：{getattr(recommendation, 'mainline_flow_signal', '') or '待确认'} / {getattr(recommendation, 'mainline_stage', '') or '待确认'}",
                    f"主线角色：{getattr(recommendation, 'mainline_role', '') or '待确认'} | 题材：{getattr(recommendation, 'mainline_tag', '') or getattr(recommendation, 'theme_name', '') or '待确认'}",
                    f"推荐动作：{self._display_action(getattr(recommendation, 'action', ''))} | 推荐理由：{getattr(recommendation, 'rationale', '') or '等待推荐逻辑生成。'}",
                ]
            )
        else:
            lines.append("主线状态：当前缺少推荐联动，请先结合交易页和扫描页补齐主线判断。")
        lines.extend(recommend_context_lines)
        lines.append(f"处理建议：{repair_hint['headline']} | {repair_hint['detail']}")
        lines.append(f"参数复核：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}")
        lines.append(f"优先入口：{resolution_action['target']} | {resolution_action['detail']}")
        lines.append(f"复核检查：{repair_hint['checkpoint']}")
        self._set_plain_text_if_changed(self.broker_mainline_review_text, "\n".join(lines))

    if hasattr(self, "broker_execution_text"):
        lines = [
            "交易流程",
            "",
            panel_conclusion,
            f"当前焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"执行阶段：{summary['stage']}",
            f"状态判断：{summary['judgement']}",
            summary["next_step"],
            *recommend_context_lines,
            f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
            f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
            f"联动建议：{followup['headline']} | {followup['detail']}",
            f"修正路径：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            f"推荐链路：建议前往 {followup['route']} 继续处理。",
        ]
        self._set_plain_text_if_changed(self.broker_execution_text, "\n".join(lines))

    if hasattr(self, "broker_order_focus_text"):
        lines = [
            execution_deck["headline"],
            "",
            panel_conclusion,
            f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
            f"动作：{self._display_action(record.get('side', ''))} | 价格 {record.get('price', '--')} | 数量 {record.get('quantity', '--')}",
            f"主线：{execution_deck['gate_accent']}",
            f"参数：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
            f"处理：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            f"入口：去{resolution_action['target']} | {resolution_action['detail']}",
        ]
        self._set_plain_text_if_changed(self.broker_order_focus_text, "\n".join(lines))

    if hasattr(self, "broker_order_metric_labels"):
        self._set_label_text_if_changed(self.broker_order_metric_labels["symbol"], execution_deck["symbol_value"])
        self._set_label_text_if_changed(self.broker_order_metric_accents["symbol"], execution_deck["symbol_accent"])
        self._set_label_text_if_changed(self.broker_order_metric_labels["gate"], execution_deck["gate_value"])
        self._set_label_text_if_changed(self.broker_order_metric_accents["gate"], execution_deck["gate_accent"])
        self._set_label_text_if_changed(self.broker_order_metric_labels["risk"], execution_deck["risk_value"])
        self._set_label_text_if_changed(self.broker_order_metric_accents["risk"], execution_deck["risk_accent"])
        self._set_label_text_if_changed(self.broker_order_metric_labels["position"], execution_deck["position_value"])
        self._set_label_text_if_changed(self.broker_order_metric_accents["position"], execution_deck["position_accent"])

    if hasattr(self, "broker_stage_label"):
        stage_text = terminal_brief["stage"]
        stage_tooltip = "\n".join(
            [
                f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
                f"阶段判断：{summary['judgement']}",
                *recommend_context_lines,
                f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}",
                f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
                f"链路建议：{followup['headline']} | {followup['detail']}",
                f"处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
            ]
        )
        self._set_label_text_if_changed(
            self.broker_stage_label,
            stage_text,
            tooltip=stage_tooltip,
        )

    if hasattr(self, "orders_focus_label"):
        focus_text = f"委托动作面板 / {terminal_brief['focus']}"
        focus_tooltip = "\n".join(
            [
                f"焦点：{stock_name} ({stock_id} / {symbol or '--'})",
                f"执行阶段：{summary['stage']}",
                *recommend_context_lines,
                f"参数比对：{parameter_alignment['headline']} | {parameter_alignment['detail']}",
                f"优先入口：{resolution_action['target']} | {resolution_action['detail']}",
                f"链路建议：{followup['headline']} | {followup['detail']}",
                f"处理建议：{repair_hint['headline']} | {repair_hint['detail']}",
                f"复核检查：{repair_hint['checkpoint']}",
            ]
        )
        self._set_label_text_if_changed(
            self.orders_focus_label,
            focus_text,
            tooltip=focus_tooltip,
        )

    if hasattr(self, "_set_widget_spotlight_v23"):
        for attr_name in [
            "broker_status_banner",
            "broker_workbench_banner",
            "broker_stage_label",
            "orders_focus_label",
            "execution_table",
            "order_result_text",
            "broker_recap_text",
            "broker_execution_text",
            "broker_mainline_review_text",
        ]:
            self._set_widget_spotlight_v23(getattr(self, attr_name, None), execution_tone)

    if hasattr(self, "broker_status_banner"):
        self._set_label_text_if_changed(
            self.broker_status_banner,
            terminal_brief["status"],
            tooltip=f"{summary['tooltip']}\n" + "\n".join(recommend_context_lines) + f"\n参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}\n优先入口：{resolution_action['target']} | {resolution_action['detail']}\n链路建议：{followup['headline']} | {followup['detail']}\n处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
        )
    if hasattr(self, "broker_workbench_banner"):
        self._set_label_text_if_changed(
            self.broker_workbench_banner,
            terminal_brief["workbench"],
            tooltip=f"{summary['tooltip']}\n" + "\n".join(recommend_context_lines) + f"\n参数比对：{parameter_alignment['headline']} | {parameter_alignment['checkpoint']}\n优先入口：{resolution_action['target']} | {resolution_action['detail']}\n链路建议：{followup['headline']} | {followup['detail']}\n处理建议：{repair_hint['headline']} | {repair_hint['checkpoint']}",
        )

    detail_status_label = getattr(self, "broker_detail_status_label", None)
    if isinstance(detail_status_label, QLabel) and not getattr(self, "_qh_broker_detail_visible_v40", False):
        status_text = f"执行明细已折叠，当前优先去{resolution_action['target']}。{resolution_action['detail']}"
        self._set_label_text_if_changed(detail_status_label, status_text, tooltip=status_text)

    generate_button = getattr(self, "generate_order_suggestions_button", None)
    if isinstance(generate_button, QPushButton):
        base_tip = f"围绕 {stock_name} 重新生成委托建议前，建议先去{resolution_action['target']}。{resolution_action['button_hint']}"
        current_tip = generate_button.toolTip()
        if current_tip != base_tip:
            generate_button.setToolTip(base_tip)

    confirm_button = getattr(self, "confirm_submit_orders_button", None)
    if isinstance(confirm_button, QPushButton):
        base_tip = f"{resolution_action['button_hint']}"
        current_tip = confirm_button.toolTip()
        if current_tip != base_tip:
            confirm_button.setToolTip(base_tip)


def _qh_confirm_and_submit_orders_v26(self: QuantHunterWindow) -> None:
    before_count = len(getattr(self, "order_submission_records", []) or [])
    _ORIGINAL_QH_CONFIRM_AND_SUBMIT_ORDERS_V26(self)
    after_count = len(getattr(self, "order_submission_records", []) or [])
    if after_count > before_count:
        if hasattr(self, "execution_table") and self.execution_table.rowCount() > 0:
            self.execution_table.selectRow(self.execution_table.rowCount() - 1)
            if hasattr(self, "_on_execution_selection_changed"):
                self._on_execution_selection_changed()
        if hasattr(self, "_navigate_to_workspace"):
            self._navigate_to_workspace("broker", "execution_table")
        if hasattr(self, "broker_status_banner"):
            symbol = str(getattr(self, "order_submission_records", [])[-1].get("symbol", "") or "")
            stock_name = self._stock_name_for_symbol(symbol) if symbol else "最新委托"
            self._set_label_text_if_changed(
                self.broker_status_banner,
                f"交易状态：提交完成，已自动定位到 {stock_name} 的最新执行回执。",
            )
    self._update_broker_action_flow_v26()


QuantHunterWindow._update_broker_action_flow_v26 = _qh_update_broker_action_flow_v26
QuantHunterWindow._refresh_broker_status = _qh_refresh_broker_status_v26
QuantHunterWindow._refresh_submission_focus = _qh_refresh_submission_focus_v26
QuantHunterWindow.confirm_and_submit_orders = _qh_confirm_and_submit_orders_v26


apply_workspace_workbench_patches(QuantHunterWindow)
apply_shell_workflow_patches(QuantHunterWindow)


apply_commercial_chrome_patches(
    QuantHunterWindow,
    set_shell_chip_fn=set_shell_chip,
)


apply_window_tail_patches(
    QuantHunterWindow,
    mainline_signal_brief_fn=_qh_mainline_signal_brief_v4,
    recommend_execution_summary_fn=_qh_recommend_execution_summary_v24,
)


apply_recommend_workspace_patches(
    QuantHunterWindow,
    recommend_execution_summary_fn=_qh_recommend_execution_summary_v24,
)


apply_workspace_visibility_patches(
    QuantHunterWindow,
    recommend_execution_summary_fn=_qh_recommend_execution_summary_v24,
)
apply_broker_workspace_patches(QuantHunterWindow)
apply_paper_experiment_patches(
    QuantHunterWindow,
    paper_lab_stage_fn=_qh_paper_lab_stage_v39,
)


def main() -> int:
    app = QApplication(sys.argv)
    _install_runtime_cjk_font(app)
    app.setApplicationName("量化猎手")
    window = QuantHunterWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

