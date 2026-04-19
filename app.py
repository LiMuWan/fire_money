from __future__ import annotations

import os
import sys
import tkinter as tk
from datetime import datetime, time
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from quant_hunter.backtest import Backtester, format_result
from quant_hunter.broker import (
    EastmoneyBrokerAdapter,
    build_execution_quality_profile,
    build_order_intent_from_trade_decision,
    summarize_trade_recap,
)
from quant_hunter.data import (
    load_bars_from_csv,
    load_cash_snapshot_from_csv,
    load_holdings_from_csv,
    load_news_catalysts_from_csv,
    load_stock_profiles_from_csv,
    load_theme_aliases_from_csv,
)
from quant_hunter.decision import DecisionEngine
from quant_hunter.models import (
    BrokerProfile,
    CashSnapshot,
    DailyAnalysis,
    HoldingRecord,
    OptimizationRun,
    OrderIntent,
    PriceBar,
    RecommendationRow,
    ScanRow,
    SymbolBacktestSummary,
)
from quant_hunter.optimizer import ParameterOptimizer
from quant_hunter.recommend import DailyPoolBuilder
from quant_hunter.reports import export_workspace_report
from quant_hunter.scanner import UniverseScanner
from quant_hunter.storage import AppState, load_app_state, save_app_state
from quant_hunter.strategy import AntiHarvestStrategy, StrategyParams


PROJECT_ROOT = Path(__file__).resolve().parent
SAMPLE_DIR = PROJECT_ROOT / "sample_data"
STATE_FILE = PROJECT_ROOT / ".quant_hunter" / "app_state.json"
REPORT_DIR = PROJECT_ROOT / "reports"


def _configure_tcl_tk_env() -> None:
    candidates = [Path(sys.executable).resolve().parent]
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        candidates.insert(0, Path(meipass))
    for root in candidates:
        tcl_dir = root / "tcl" / "tcl8.6"
        tk_dir = root / "tcl" / "tk8.6"
        if tcl_dir.exists() and "TCL_LIBRARY" not in os.environ:
            os.environ["TCL_LIBRARY"] = str(tcl_dir)
        if tk_dir.exists() and "TK_LIBRARY" not in os.environ:
            os.environ["TK_LIBRARY"] = str(tk_dir)


_configure_tcl_tk_env()


class QuantHunterApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Quant Hunter")
        self.geometry("1380x880")
        self.minsize(1200, 760)

        self.state = load_app_state(STATE_FILE)
        self.strategy_vars = self._build_strategy_vars()
        self.broker_vars = self._build_broker_vars(self.state.broker_profile)
        self.per_trade_budget_var = tk.StringVar(value="30000")
        self.auto_refresh_var = tk.BooleanVar(value=False)
        self.refresh_interval_var = tk.StringVar(value="60")
        self.last_refresh_var = tk.StringVar(value="Not refreshed yet")
        self.refresh_job: str | None = None

        self.scan_rows: list[ScanRow] = []
        self.backtest_summaries: list[SymbolBacktestSummary] = []
        self.optimization_results: list[OptimizationRun] = []
        self.universe_bars: dict[str, list[PriceBar]] = {}
        self.universe_analyses: dict[str, list[DailyAnalysis]] = {}
        self.paths_by_symbol: dict[str, Path] = {}
        self.holdings: list[HoldingRecord] = []
        self.cash_snapshot: CashSnapshot | None = None
        self.order_intents: list[OrderIntent] = []
        self.daily_pool_rows: list[RecommendationRow] = []
        self.current_trade_plan = None
        self.order_submission_log: list[str] = []
        self.active_symbol = ""
        self.bars: list[PriceBar] = []
        self.analyses: list[DailyAnalysis] = []
        self.stock_profiles = self._load_sample_stock_profiles()
        self.news_catalysts = self._load_sample_news_catalysts()
        self.theme_aliases = self._load_sample_theme_aliases()

        self._build_layout()
        self._refresh_watchlist()
        self._refresh_broker_status()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        if self.state.universe_dir and Path(self.state.universe_dir).exists():
            self._scan_universe(Path(self.state.universe_dir), quiet=True)

    def _build_strategy_vars(self) -> dict[str, tk.StringVar]:
        defaults = StrategyParams()
        return {
            "breakout_lookback": tk.StringVar(value=str(defaults.breakout_lookback)),
            "atr_window": tk.StringVar(value=str(defaults.atr_window)),
            "volume_window": tk.StringVar(value=str(defaults.volume_window)),
            "fast_ma_window": tk.StringVar(value=str(defaults.fast_ma_window)),
            "slow_ma_window": tk.StringVar(value=str(defaults.slow_ma_window)),
            "reclaim_window": tk.StringVar(value=str(defaults.reclaim_window)),
            "min_breakout_pct": tk.StringVar(value=str(defaults.min_breakout_pct)),
            "min_volume_ratio": tk.StringVar(value=str(defaults.min_volume_ratio)),
            "min_upper_shadow_pct": tk.StringVar(value=str(defaults.min_upper_shadow_pct)),
            "max_close_location": tk.StringVar(value=str(defaults.max_close_location)),
            "max_reclaim_volume_ratio": tk.StringVar(value=str(defaults.max_reclaim_volume_ratio)),
            "stop_atr_multiple": tk.StringVar(value=str(defaults.stop_atr_multiple)),
            "target_atr_multiple": tk.StringVar(value=str(defaults.target_atr_multiple)),
        }

    def _build_broker_vars(self, profile: BrokerProfile) -> dict[str, tk.StringVar]:
        adapter = EastmoneyBrokerAdapter()
        return {
            "account_name": tk.StringVar(value=profile.account_name),
            "account_id": tk.StringVar(value=profile.account_id),
            "mode": tk.StringVar(value=profile.mode),
            "export_dir": tk.StringVar(value=profile.export_dir or str(PROJECT_ROOT / "exports")),
            "sdk_module": tk.StringVar(value=profile.sdk_module),
            "sdk_python_path": tk.StringVar(value=profile.sdk_python_path or adapter.resolve_bridge_python(profile)),
            "token": tk.StringVar(value=profile.token),
            "strategy_id": tk.StringVar(value=profile.strategy_id),
        }

    @staticmethod
    def _load_sample_stock_profiles() -> dict[str, object]:
        path = SAMPLE_DIR / "stock_profiles.csv"
        if not path.exists():
            return {}
        try:
            return load_stock_profiles_from_csv(path)
        except Exception:
            return {}

    @staticmethod
    def _load_sample_news_catalysts() -> dict[str, list[object]]:
        path = SAMPLE_DIR / "news_catalysts.csv"
        if not path.exists():
            return {}
        try:
            return load_news_catalysts_from_csv(path)
        except Exception:
            return {}

    def _load_sample_theme_aliases(self) -> dict[str, tuple[str, ...]]:
        path = Path(self.state.theme_alias_path) if self.state.theme_alias_path else SAMPLE_DIR / "theme_aliases.csv"
        if not path.exists():
            return {}
        try:
            return load_theme_aliases_from_csv(path)
        except Exception:
            return {}

    def _build_layout(self) -> None:
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=12, pady=12)

        self.overview_tab = ttk.Frame(notebook, padding=14)
        self.plan_tab = ttk.Frame(notebook, padding=14)
        self.scanner_tab = ttk.Frame(notebook, padding=14)
        self.detail_tab = ttk.Frame(notebook, padding=14)
        self.broker_tab = ttk.Frame(notebook, padding=14)

        notebook.add(self.overview_tab, text="Overview")
        notebook.add(self.plan_tab, text="Plan")
        notebook.add(self.scanner_tab, text="Scanner")
        notebook.add(self.detail_tab, text="Detail")
        notebook.add(self.broker_tab, text="Broker")

        self._build_overview_tab()
        self._build_plan_tab()
        self._build_scanner_tab()
        self._build_detail_tab()
        self._build_broker_tab()

    def _build_overview_tab(self) -> None:
        header = ttk.Label(
            self.overview_tab,
            text="Focus on post-trap repair signals instead of chasing the first spike.",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        header.pack(anchor="w", pady=(0, 12))

        intro = ScrolledText(self.overview_tab, height=12, wrap="word")
        intro.insert(
            "1.0",
            "\n".join(
                [
                    "Closed-loop workflow",
                    "1. Scan a stock pool and identify trap breakouts plus repair setups.",
                    "2. Only produce BUY ideas after repair confirmation to avoid chasing the first move.",
                    "3. Use backtests to constrain position size, stop loss, target, and holding period.",
                    "4. Iterate with watchlists, reports, and parameter optimization.",
                    "5. Start from semi-automatic export, then upgrade to GM SDK execution.",
                ]
            ),
        )
        intro.configure(state="disabled")
        intro.pack(fill="x", pady=(0, 12))

        params_frame = ttk.LabelFrame(self.overview_tab, text="Strategy Parameters")
        params_frame.pack(fill="x", pady=(0, 12))
        labels = [
            ("breakout_lookback", "Breakout Lookback"),
            ("atr_window", "ATR Window"),
            ("volume_window", "Volume Window"),
            ("fast_ma_window", "Fast MA"),
            ("slow_ma_window", "Slow MA"),
            ("reclaim_window", "Reclaim Window"),
            ("min_breakout_pct", "Min Breakout %"),
            ("min_volume_ratio", "Min Volume Ratio"),
            ("min_upper_shadow_pct", "Min Upper Shadow %"),
            ("max_close_location", "Max Close Location"),
            ("max_reclaim_volume_ratio", "Max Reclaim Vol Ratio"),
            ("stop_atr_multiple", "Stop ATR"),
            ("target_atr_multiple", "Target ATR"),
        ]
        for idx, (key, label) in enumerate(labels):
            row = idx // 3
            col = (idx % 3) * 2
            ttk.Label(params_frame, text=label).grid(row=row, column=col, sticky="w", padx=8, pady=6)
            ttk.Entry(params_frame, textvariable=self.strategy_vars[key], width=14).grid(
                row=row, column=col + 1, sticky="w", padx=(0, 12), pady=6
            )

        action_frame = ttk.Frame(self.overview_tab)
        action_frame.pack(fill="x", pady=(0, 8))
        ttk.Button(action_frame, text="Run Optimization", command=self.run_parameter_optimization).pack(side="left")
        ttk.Button(action_frame, text="Export Workspace Report", command=self.export_workspace_report_from_ui).pack(
            side="left", padx=8
        )

        self.optimization_text = ScrolledText(self.overview_tab, height=14, wrap="word")
        self.optimization_text.pack(fill="both", expand=True)
        self.optimization_text.insert("1.0", "Optimization results will appear here.\n")

    def _build_plan_tab(self) -> None:
        header = ttk.Label(
            self.plan_tab,
            text="把今天能不能做、先做谁、怎么做，压缩成一屏。",
            font=("Microsoft YaHei UI", 14, "bold"),
        )
        header.pack(anchor="w", pady=(0, 8))

        self.plan_summary_text = ScrolledText(self.plan_tab, height=10, wrap="word")
        self.plan_summary_text.pack(fill="x", pady=(0, 12))
        self.plan_summary_text.insert("1.0", "完成股票池扫描后，这里会生成今日主线、第一目标和交易计划。\n")

        top_frame = ttk.Frame(self.plan_tab)
        top_frame.pack(fill="both", expand=True, pady=(0, 12))

        recommendation_frame = ttk.LabelFrame(top_frame, text="今日推荐池")
        recommendation_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        recommendation_columns = ("stock", "theme", "tier", "ready", "entry", "stop", "target", "focus")
        self.recommend_tree = ttk.Treeview(
            recommendation_frame,
            columns=recommendation_columns,
            show="headings",
            height=12,
        )
        for key, title, width in [
            ("stock", "股票", 180),
            ("theme", "主线", 110),
            ("tier", "机会层级", 90),
            ("ready", "执行准备", 80),
            ("entry", "买点", 80),
            ("stop", "止损", 80),
            ("target", "目标", 80),
            ("focus", "下一步重点", 240),
        ]:
            self.recommend_tree.heading(key, text=title)
            self.recommend_tree.column(key, width=width, anchor="center" if key != "focus" else "w")
        self.recommend_tree.pack(fill="both", expand=True, padx=8, pady=8)

        decision_frame = ttk.LabelFrame(top_frame, text="交易计划")
        decision_frame.pack(side="left", fill="both", expand=True)
        decision_columns = ("status", "stock", "budget", "entry", "stop", "target", "focus")
        self.plan_tree = ttk.Treeview(
            decision_frame,
            columns=decision_columns,
            show="headings",
            height=12,
        )
        for key, title, width in [
            ("status", "状态", 90),
            ("stock", "股票", 180),
            ("budget", "预算", 90),
            ("entry", "买点", 80),
            ("stop", "止损", 80),
            ("target", "目标", 80),
            ("focus", "执行重点", 260),
        ]:
            self.plan_tree.heading(key, text=title)
            self.plan_tree.column(key, width=width, anchor="center" if key != "focus" else "w")
        self.plan_tree.pack(fill="both", expand=True, padx=8, pady=8)

        footer = ttk.Label(
            self.plan_tab,
            text="规则：优先主线、优先可执行、优先能定义止损的计划。",
            foreground="#5f6368",
        )
        footer.pack(anchor="w")

    def _build_scanner_tab(self) -> None:
        controls = ttk.Frame(self.scanner_tab)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Button(controls, text="Open Universe Folder", command=self.load_universe_folder).pack(side="left")
        ttk.Button(controls, text="Load Sample Universe", command=self.load_sample_universe).pack(side="left", padx=8)
        ttk.Button(controls, text="Rescan", command=self.rescan_universe).pack(side="left")
        ttk.Button(controls, text="Add To Watchlist", command=self.add_selected_to_watchlist).pack(side="left", padx=(16, 8))
        ttk.Button(controls, text="Remove From Watchlist", command=self.remove_selected_from_watchlist).pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Auto Refresh During Session",
            variable=self.auto_refresh_var,
            command=self.toggle_auto_refresh,
        ).pack(side="left", padx=(16, 4))
        ttk.Entry(controls, textvariable=self.refresh_interval_var, width=6).pack(side="left")
        ttk.Label(controls, text="sec").pack(side="left", padx=(4, 10))
        ttk.Label(controls, textvariable=self.last_refresh_var).pack(side="left")

        self.universe_label = ttk.Label(self.scanner_tab, text="Universe folder: not loaded")
        self.universe_label.pack(anchor="w", pady=(0, 8))
        self.scan_summary_label = ttk.Label(self.scanner_tab, text="Scanner has not run yet.")
        self.scan_summary_label.pack(anchor="w", pady=(0, 12))

        scan_frame = ttk.LabelFrame(self.scanner_tab, text="Scan Results")
        scan_frame.pack(fill="both", expand=True, pady=(0, 12))
        columns = ("symbol", "action", "label", "score", "date", "close", "entry", "stop", "target")
        self.scan_tree = ttk.Treeview(scan_frame, columns=columns, show="headings", height=12)
        for key, title, width in [
            ("symbol", "Symbol", 120),
            ("action", "Action", 80),
            ("label", "Label", 120),
            ("score", "Score", 80),
            ("date", "Signal Date", 110),
            ("close", "Close", 90),
            ("entry", "Entry", 90),
            ("stop", "Stop", 90),
            ("target", "Target", 90),
        ]:
            self.scan_tree.heading(key, text=title)
            self.scan_tree.column(key, width=width, anchor="center")
        self.scan_tree.pack(fill="both", expand=True)
        self.scan_tree.bind("<<TreeviewSelect>>", self.on_scan_selected)

        bottom = ttk.Frame(self.scanner_tab)
        bottom.pack(fill="both", expand=True)

        watchlist_frame = ttk.LabelFrame(bottom, text="Watchlist")
        watchlist_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.watchlist_box = tk.Listbox(watchlist_frame, height=10)
        self.watchlist_box.pack(fill="both", expand=True, padx=8, pady=8)
        self.watchlist_box.bind("<<ListboxSelect>>", self.on_watchlist_selected)

        summary_frame = ttk.LabelFrame(bottom, text="Backtest Summary")
        summary_frame.pack(side="left", fill="both", expand=True)
        summary_columns = ("symbol", "trades", "return", "drawdown", "win_rate", "ending")
        self.summary_tree = ttk.Treeview(summary_frame, columns=summary_columns, show="headings", height=10)
        for key, title, width in [
            ("symbol", "Symbol", 110),
            ("trades", "Trades", 80),
            ("return", "Return", 90),
            ("drawdown", "Drawdown", 90),
            ("win_rate", "Win Rate", 90),
            ("ending", "Ending Equity", 120),
        ]:
            self.summary_tree.heading(key, text=title)
            self.summary_tree.column(key, width=width, anchor="center")
        self.summary_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _build_detail_tab(self) -> None:
        controls = ttk.Frame(self.detail_tab)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Button(controls, text="Load Single CSV", command=self.load_single_csv).pack(side="left")
        ttk.Button(controls, text="Backtest Active Symbol", command=self.run_backtest_for_active).pack(side="left", padx=8)
        self.active_symbol_label = ttk.Label(controls, text="Active symbol: none")
        self.active_symbol_label.pack(side="left", padx=12)

        self.metrics_text = ScrolledText(self.detail_tab, height=10, wrap="word")
        self.metrics_text.pack(fill="x", pady=(0, 12))

        signal_frame = ttk.LabelFrame(self.detail_tab, text="Recent Signals")
        signal_frame.pack(fill="both", expand=True, pady=(0, 12))
        signal_columns = ("date", "label", "score", "close", "reason")
        self.signal_tree = ttk.Treeview(signal_frame, columns=signal_columns, show="headings", height=10)
        for key, title, width in [
            ("date", "Date", 110),
            ("label", "Label", 120),
            ("score", "Score", 80),
            ("close", "Close", 90),
            ("reason", "Reason", 720),
        ]:
            self.signal_tree.heading(key, text=title)
            self.signal_tree.column(key, width=width, anchor="center" if key != "reason" else "w")
        self.signal_tree.pack(fill="both", expand=True)

        trades_frame = ttk.LabelFrame(self.detail_tab, text="Trade Log")
        trades_frame.pack(fill="both", expand=True)
        trade_columns = ("entry_date", "exit_date", "entry", "exit", "shares", "pnl", "reason")
        self.trades_tree = ttk.Treeview(trades_frame, columns=trade_columns, show="headings", height=10)
        for key, title, width in [
            ("entry_date", "Entry Date", 110),
            ("exit_date", "Exit Date", 110),
            ("entry", "Entry", 90),
            ("exit", "Exit", 90),
            ("shares", "Shares", 90),
            ("pnl", "PnL", 90),
            ("reason", "Exit Reason", 300),
        ]:
            self.trades_tree.heading(key, text=title)
            self.trades_tree.column(key, width=width, anchor="center" if key != "reason" else "w")
        self.trades_tree.pack(fill="both", expand=True)

    def _build_broker_tab(self) -> None:
        profile_frame = ttk.LabelFrame(self.broker_tab, text="Account And Gateway")
        profile_frame.pack(fill="x", pady=(0, 12))

        fields = [
            ("account_name", "Account Name"),
            ("account_id", "Account ID"),
            ("export_dir", "Export Dir"),
            ("sdk_module", "SDK Module"),
            ("sdk_python_path", "Bridge Python"),
            ("token", "SDK Token"),
            ("strategy_id", "Strategy ID"),
        ]
        for idx, (key, label) in enumerate(fields):
            row = idx // 2
            col = (idx % 2) * 3
            ttk.Label(profile_frame, text=label).grid(row=row, column=col, sticky="w", padx=8, pady=6)
            ttk.Entry(profile_frame, textvariable=self.broker_vars[key], width=34).grid(
                row=row, column=col + 1, sticky="we", padx=(0, 10), pady=6
            )
        ttk.Label(profile_frame, text="Mode").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(
            profile_frame,
            textvariable=self.broker_vars["mode"],
            values=("export", "sdk"),
            state="readonly",
            width=12,
        ).grid(row=4, column=1, sticky="w", padx=(0, 10), pady=6)
        ttk.Label(profile_frame, text="Budget / Trade").grid(row=4, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(profile_frame, textvariable=self.per_trade_budget_var, width=16).grid(
            row=4, column=4, sticky="w", padx=(0, 10), pady=6
        )
        ttk.Button(profile_frame, text="Choose Export Dir", command=self.choose_export_dir).grid(
            row=0, column=5, sticky="w", padx=8, pady=6
        )
        ttk.Button(profile_frame, text="Save Profile", command=self.save_profile).grid(
            row=1, column=5, sticky="w", padx=8, pady=6
        )
        ttk.Button(profile_frame, text="Create Templates", command=self.create_broker_templates).grid(
            row=2, column=5, sticky="w", padx=8, pady=6
        )

        actions = ttk.Frame(self.broker_tab)
        actions.pack(fill="x", pady=(0, 10))
        ttk.Button(actions, text="Import Holdings CSV", command=self.import_holdings_csv).pack(side="left")
        ttk.Button(actions, text="Import Cash CSV", command=self.import_cash_csv).pack(side="left", padx=8)
        ttk.Button(actions, text="Generate Order Ideas", command=self.generate_order_suggestions).pack(side="left")
        ttk.Button(actions, text="Export Order Plan", command=self.export_order_plan).pack(side="left", padx=8)
        ttk.Button(actions, text="Sync SDK Account", command=self.sync_broker_via_sdk).pack(side="left", padx=(16, 8))
        ttk.Button(actions, text="Generate GM Script", command=self.generate_sdk_strategy_script).pack(side="left")
        ttk.Button(actions, text="Confirm And Submit", command=self.confirm_and_submit_orders).pack(side="left", padx=(16, 0))

        self.broker_status_text = ScrolledText(self.broker_tab, height=8, wrap="word")
        self.broker_status_text.pack(fill="x", pady=(0, 12))

        bottom = ttk.Frame(self.broker_tab)
        bottom.pack(fill="both", expand=True)

        holdings_frame = ttk.LabelFrame(bottom, text="Holdings")
        holdings_frame.pack(side="left", fill="both", expand=True, padx=(0, 8))
        holdings_columns = ("symbol", "quantity", "available", "cost", "market_value")
        self.holdings_tree = ttk.Treeview(holdings_frame, columns=holdings_columns, show="headings", height=12)
        for key, title, width in [
            ("symbol", "Symbol", 110),
            ("quantity", "Quantity", 90),
            ("available", "Available", 90),
            ("cost", "Cost", 90),
            ("market_value", "Market Value", 120),
        ]:
            self.holdings_tree.heading(key, text=title)
            self.holdings_tree.column(key, width=width, anchor="center")
        self.holdings_tree.pack(fill="both", expand=True, padx=8, pady=8)

        order_frame = ttk.LabelFrame(bottom, text="Order Ideas")
        order_frame.pack(side="left", fill="both", expand=True)
        order_columns = ("symbol", "side", "price", "quantity", "stop", "target", "date")
        self.order_tree = ttk.Treeview(order_frame, columns=order_columns, show="headings", height=12)
        for key, title, width in [
            ("symbol", "Symbol", 110),
            ("side", "Side", 80),
            ("price", "Price", 90),
            ("quantity", "Quantity", 90),
            ("stop", "Stop", 90),
            ("target", "Target", 90),
            ("date", "Signal Date", 110),
        ]:
            self.order_tree.heading(key, text=title)
            self.order_tree.column(key, width=width, anchor="center")
        self.order_tree.pack(fill="both", expand=True, padx=8, pady=8)

        result_frame = ttk.LabelFrame(self.broker_tab, text="Order Result Log")
        result_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.order_result_text = ScrolledText(result_frame, height=8, wrap="word")
        self.order_result_text.pack(fill="both", expand=True, padx=8, pady=8)
        self.order_result_text.insert("1.0", "No orders submitted yet.\n")
        self.order_result_text.configure(state="disabled")

    def strategy_params(self) -> StrategyParams:
        return StrategyParams.from_mapping({key: var.get() for key, var in self.strategy_vars.items()})

    def current_broker_profile(self) -> BrokerProfile:
        return BrokerProfile(
            account_name=self.broker_vars["account_name"].get().strip() or "Eastmoney Account",
            account_id=self.broker_vars["account_id"].get().strip(),
            mode=self.broker_vars["mode"].get().strip() or "export",
            export_dir=self.broker_vars["export_dir"].get().strip(),
            sdk_module=self.broker_vars["sdk_module"].get().strip() or "gm.api",
            sdk_python_path=self.broker_vars["sdk_python_path"].get().strip(),
            token=self.broker_vars["token"].get().strip(),
            strategy_id=self.broker_vars["strategy_id"].get().strip(),
        )

    def load_universe_folder(self) -> None:
        folder = filedialog.askdirectory(title="Choose universe folder")
        if folder:
            self._scan_universe(Path(folder))

    def load_sample_universe(self) -> None:
        self._scan_universe(SAMPLE_DIR)

    def rescan_universe(self) -> None:
        if not self.state.universe_dir:
            messagebox.showinfo("Info", "Please choose a universe folder first.")
            return
        self._scan_universe(Path(self.state.universe_dir))

    def toggle_auto_refresh(self) -> None:
        if self.auto_refresh_var.get():
            self.schedule_next_refresh(immediate=True)
        else:
            self.cancel_auto_refresh()

    def schedule_next_refresh(self, immediate: bool = False) -> None:
        self.cancel_auto_refresh()
        try:
            interval = float(self.refresh_interval_var.get())
        except ValueError:
            interval = 60.0
            self.refresh_interval_var.set("60")
        delay_ms = 100 if immediate else max(int(interval * 1000), 5000)
        self.refresh_job = self.after(delay_ms, self.execute_refresh_cycle)

    def cancel_auto_refresh(self) -> None:
        if self.refresh_job is not None:
            self.after_cancel(self.refresh_job)
            self.refresh_job = None

    def execute_refresh_cycle(self) -> None:
        self.refresh_job = None
        if not self.auto_refresh_var.get():
            return
        now = datetime.now().time()
        in_session = time(9, 25) <= now <= time(11, 35) or time(12, 55) <= now <= time(15, 5)
        if self.state.universe_dir and in_session:
            self._scan_universe(Path(self.state.universe_dir), quiet=True)
            if self.current_broker_profile().mode == "sdk":
                self.sync_broker_via_sdk(quiet=True)
            self.last_refresh_var.set(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
        else:
            self.last_refresh_var.set(f"Waiting for session: {datetime.now().strftime('%H:%M:%S')}")
        self.schedule_next_refresh()

    def _scan_universe(self, folder: Path, quiet: bool = False) -> None:
        try:
            scanner = UniverseScanner(self.strategy_params())
            rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol = scanner.scan_folder(folder)
            summaries = scanner.summarize_backtests(bars_by_symbol, analyses_by_symbol)
        except Exception as exc:
            if not quiet:
                messagebox.showerror("Scan Failed", str(exc))
            return

        self.scan_rows = rows
        self.universe_bars = bars_by_symbol
        self.universe_analyses = analyses_by_symbol
        self.paths_by_symbol = paths_by_symbol
        self.backtest_summaries = summaries

        self.universe_label.configure(text=f"Universe folder: {folder}")
        self.scan_summary_label.configure(
            text=f"Scanned {len(bars_by_symbol)} symbols. Active signals: {len(rows)}."
        )
        self._fill_scan_rows()
        self._fill_backtest_summaries()
        self.state.universe_dir = str(folder)

        if self.state.selected_symbol and self.state.selected_symbol in bars_by_symbol:
            self.select_symbol(self.state.selected_symbol)
        elif rows:
            self.select_symbol(rows[0].symbol)
        elif bars_by_symbol:
            self.select_symbol(next(iter(bars_by_symbol)))
        self.save_state()

    def _fill_scan_rows(self) -> None:
        self._clear_tree(self.scan_tree)
        for row in self.scan_rows:
            self.scan_tree.insert(
                "",
                tk.END,
                iid=row.symbol,
                values=(
                    row.symbol,
                    row.action,
                    row.label,
                    row.score,
                    row.signal_date,
                    f"{row.close:.2f}",
                    "" if row.entry_price is None else f"{row.entry_price:.2f}",
                    "" if row.stop_price is None else f"{row.stop_price:.2f}",
                    "" if row.target_price is None else f"{row.target_price:.2f}",
                ),
            )

    def _fill_backtest_summaries(self) -> None:
        self._clear_tree(self.summary_tree)
        for item in self.backtest_summaries:
            self.summary_tree.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    item.trades,
                    f"{item.total_return:.2%}",
                    f"{item.max_drawdown:.2%}",
                    f"{item.win_rate:.2%}",
                    f"{item.ending_equity:,.0f}",
                ),
            )

    def add_selected_to_watchlist(self) -> None:
        symbol = self._selected_symbol_from_scan()
        if not symbol:
            messagebox.showinfo("Info", "Please choose a symbol from the scan result first.")
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
        if not hasattr(self, "watchlist_box"):
            return
        self.watchlist_box.delete(0, tk.END)
        for symbol in self.state.watchlist:
            self.watchlist_box.insert(tk.END, symbol)

    def on_scan_selected(self, _event=None) -> None:
        symbol = self._selected_symbol_from_scan()
        if symbol:
            self.select_symbol(symbol)

    def on_watchlist_selected(self, _event=None) -> None:
        symbol = self._selected_symbol_from_watchlist()
        if symbol and symbol in self.universe_bars:
            self.select_symbol(symbol)

    def _selected_symbol_from_scan(self) -> str:
        selection = self.scan_tree.selection()
        return selection[0] if selection else ""

    def _selected_symbol_from_watchlist(self) -> str:
        indexes = self.watchlist_box.curselection()
        return self.watchlist_box.get(indexes[0]) if indexes else ""

    def select_symbol(self, symbol: str) -> None:
        if symbol not in self.universe_bars:
            return
        self.active_symbol = symbol
        self.bars = self.universe_bars[symbol]
        self.analyses = self.universe_analyses[symbol]
        self.active_symbol_label.configure(text=f"Active symbol: {symbol}")
        self.state.selected_symbol = symbol
        self._refresh_signal_panel()
        self.run_backtest_for_active(quiet=True)
        self.save_state()

    def load_single_csv(self) -> None:
        path = filedialog.askopenfilename(title="Choose a market CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
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
        self._clear_tree(self.signal_tree)
        for item in [row for row in self.analyses if row.label != "NONE"][-20:]:
            self.signal_tree.insert(
                "",
                tk.END,
                values=(item.date, item.label, item.score, f"{item.close:.2f}", item.reason),
            )

    def run_backtest_for_active(self, quiet: bool = False) -> None:
        if not self.bars or not self.analyses:
            if not quiet:
                messagebox.showinfo("Info", "Please choose a symbol first.")
            return
        result = Backtester(strategy_params=self.strategy_params()).run(self.bars, self.analyses)
        latest_signal = next((item for item in reversed(self.analyses) if item.label != "NONE"), None)
        if latest_signal is None:
            latest_note = "No active signal in recent bars."
        else:
            latest_note = (
                f"Latest signal: {latest_signal.date} | {latest_signal.label} | score {latest_signal.score}\n"
                f"{latest_signal.reason}"
            )
        source_path = self.paths_by_symbol.get(self.active_symbol)
        self.metrics_text.delete("1.0", tk.END)
        self.metrics_text.insert(
            "1.0",
            (
                f"{latest_note}\n"
                f"Data file: {source_path}\n\n"
                f"{format_result(result)}\n\n"
                "Notes:\n"
                "- Backtest assumes next-day open style daily-bar execution.\n"
                "- Use it for research, ranking, and semi-automatic execution checks.\n"
            ),
        )
        self._clear_tree(self.trades_tree)
        for trade in result.trades:
            self.trades_tree.insert(
                "",
                tk.END,
                values=(
                    trade.entry_date,
                    trade.exit_date,
                    trade.entry_price,
                    trade.exit_price,
                    trade.shares,
                    trade.pnl,
                    trade.exit_reason,
                ),
            )

    def run_parameter_optimization(self) -> None:
        if not self.universe_bars:
            messagebox.showinfo("Info", "Please load a universe before optimization.")
            return
        optimizer = ParameterOptimizer(self.strategy_params())
        execution_profile = build_execution_quality_profile(
            submission_records=list(getattr(self, "order_submission_records", []) or []),
            holdings=list(getattr(self, "holdings", []) or []),
            order_intents=list(getattr(self, "order_intents", []) or []),
            order_log=list(getattr(self, "order_submission_log", []) or []),
        )
        self.optimization_results = optimizer.optimize(
            self.universe_bars,
            top_n=8,
            execution_recap=dict(execution_profile.get("recap", {}) or {}),
            execution_profile=execution_profile,
        )
        lines = ["Optimization Top 8", ""]
        for item in self.optimization_results:
            lines.append(
                f"{item.rank}. objective={item.objective:.4f} | robustness={item.robustness_score:.0%} | "
                f"exec={item.execution_quality_label or 'none'} {item.execution_quality_score:.2f} | "
                f"portfolio={item.portfolio_return:.2%} | portfolio_oos={item.portfolio_out_of_sample_return:.2%} | "
                f"portfolio_dd={item.portfolio_max_drawdown:.2%}"
            )
            lines.append(
                f"   return={item.avg_return:.2%} | drawdown={item.avg_drawdown:.2%} | win={item.avg_win_rate:.2%} | "
                f"oos={item.avg_out_of_sample_return:.2%} | worst_window={item.avg_worst_window_return:.2%} | "
                f"return_std={item.avg_return_std:.2%} | positive_windows={item.avg_positive_window_ratio:.0%} | "
                f"exec_penalty={item.execution_penalty:.4f} | params={item.params}"
            )
        artifacts = optimizer.export_report(self.optimization_results, REPORT_DIR)
        lines.extend(["", f"Report exported: {artifacts.markdown_path}"])
        self.optimization_text.delete("1.0", tk.END)
        self.optimization_text.insert("1.0", "\n".join(lines))

    def export_workspace_report_from_ui(self) -> None:
        if not self.scan_rows:
            messagebox.showinfo("Info", "Please finish a universe scan first.")
            return
        artifacts = export_workspace_report(self.scan_rows, self.backtest_summaries, REPORT_DIR)
        self.optimization_text.delete("1.0", tk.END)
        self.optimization_text.insert(
            "1.0",
            "\n".join(
                [
                    "Workspace report exported.",
                    f"Markdown: {artifacts.markdown_path}",
                    f"CSV: {artifacts.csv_path}",
                    f"JSON: {artifacts.json_path}",
                ]
            ),
        )

    def choose_export_dir(self) -> None:
        folder = filedialog.askdirectory(title="Choose export directory")
        if folder:
            self.broker_vars["export_dir"].set(folder)

    def save_profile(self) -> None:
        self.state.broker_profile = self.current_broker_profile()
        self.save_state()
        self._refresh_broker_status()
        messagebox.showinfo("Info", "Broker profile saved.")

    def create_broker_templates(self) -> None:
        files = EastmoneyBrokerAdapter().create_templates(self.current_broker_profile().export_dir)
        self._refresh_broker_status(extra="\n".join(f"Template created: {item}" for item in files))

    def import_holdings_csv(self) -> None:
        path = filedialog.askopenfilename(title="Choose holdings CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        self.holdings = load_holdings_from_csv(path)
        self._fill_holdings()

    def import_cash_csv(self) -> None:
        path = filedialog.askopenfilename(title="Choose cash CSV", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not path:
            return
        self.cash_snapshot = load_cash_snapshot_from_csv(path)
        self._refresh_broker_status()

    def _fill_holdings(self) -> None:
        self._clear_tree(self.holdings_tree)
        for item in self.holdings:
            self.holdings_tree.insert(
                "",
                tk.END,
                values=(item.symbol, item.quantity, item.available, f"{item.cost_price:.2f}", f"{item.market_value:,.2f}"),
            )
        self._refresh_broker_status()

    def generate_order_suggestions(self) -> None:
        if not self.scan_rows:
            messagebox.showinfo("Info", "Please finish a universe scan first.")
            return
        try:
            per_trade_budget = float(self.per_trade_budget_var.get())
        except ValueError:
            messagebox.showerror("Parameter Error", "Budget per trade must be numeric.")
            return
        rows = self.scan_rows if not self.state.watchlist else [row for row in self.scan_rows if row.symbol in self.state.watchlist]
        self.order_intents = EastmoneyBrokerAdapter().build_order_intents(rows, per_trade_budget)
        self._fill_orders()
        if not self.order_intents:
            self._refresh_broker_status(extra="No new BUY ideas under the current settings.")

    def _fill_orders(self) -> None:
        self._clear_tree(self.order_tree)
        for item in self.order_intents:
            self.order_tree.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    item.side,
                    f"{item.price:.2f}",
                    item.quantity,
                    f"{item.stop_price:.2f}",
                    f"{item.target_price:.2f}",
                    item.signal_date,
                ),
            )
        self._refresh_broker_status()

    def export_order_plan(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        output = EastmoneyBrokerAdapter().export_order_plan(self.order_intents, self.current_broker_profile().export_dir)
        self._append_order_result(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Order plan exported: {output}")
        self._refresh_broker_status(extra=f"Order plan exported: {output}")

    def sync_broker_via_sdk(self, quiet: bool = False) -> None:
        profile = self.current_broker_profile()
        try:
            cash, holdings = EastmoneyBrokerAdapter().sync_account_via_sdk(profile)
        except Exception as exc:
            if not quiet:
                messagebox.showerror("SDK Sync Failed", str(exc))
            return
        self.cash_snapshot = cash
        self.holdings = holdings
        self._fill_holdings()
        self._refresh_broker_status(extra="Account cash and holdings synced via SDK.")

    def generate_sdk_strategy_script(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        profile = self.current_broker_profile()
        if not profile.token or not profile.strategy_id or not profile.account_id:
            messagebox.showerror("Missing Fields", "Please fill token, strategy_id, and account_id first.")
            return
        path = EastmoneyBrokerAdapter().generate_gm_strategy_script(profile, self.order_intents, profile.export_dir)
        self._refresh_broker_status(extra=f"GM live script generated: {path}")

    def confirm_and_submit_orders(self) -> None:
        if not self.order_intents:
            self.generate_order_suggestions()
        if not self.order_intents:
            return
        profile = self.current_broker_profile()
        adapter = EastmoneyBrokerAdapter()
        if not self._open_order_confirmation_dialog(profile, self.order_intents, adapter):
            return

        submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            results = adapter.submit_order_intents(profile, self.order_intents)
        except Exception as exc:
            fallback_path = adapter.export_order_plan(self.order_intents, profile.export_dir)
            failure_lines = [
                f"[{submit_time}] SDK submit failed: {exc}",
                f"[{submit_time}] Fallback CSV exported: {fallback_path}",
            ]
            for line in failure_lines:
                self._append_order_result(line)
            self._refresh_broker_status(extra="\n".join(failure_lines))
            messagebox.showwarning(
                "Submit Failed",
                f"{exc}\n\nFallback CSV exported to:\n{fallback_path}",
            )
            return

        success_lines = [f"[{submit_time}] SDK submit completed: {len(results)} order(s)"]
        success_lines.extend(f"[{submit_time}] {item}" for item in results)
        for line in success_lines:
            self._append_order_result(line)

        self.sync_broker_via_sdk(quiet=True)
        self._refresh_broker_status(extra="\n".join(success_lines))
        messagebox.showinfo("Submit Complete", "\n".join(results))

    def _open_order_confirmation_dialog(
        self,
        profile: BrokerProfile,
        intents: list[OrderIntent],
        adapter: EastmoneyBrokerAdapter,
    ) -> bool:
        env = adapter.diagnose_environment(profile)
        dialog = tk.Toplevel(self)
        dialog.title("Order Confirmation")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(True, True)
        dialog.geometry("980x560")

        result = {"confirmed": False}
        confirm_var = tk.BooleanVar(value=False)

        container = ttk.Frame(dialog, padding=14)
        container.pack(fill="both", expand=True)

        info_frame = ttk.LabelFrame(container, text="Account Check")
        info_frame.pack(fill="x", pady=(0, 12))

        info_rows = [
            ("Account Name", profile.account_name or "-"),
            ("Account ID", profile.account_id or "-"),
            ("Strategy ID", profile.strategy_id or "-"),
            ("Mode", profile.mode or "-"),
            ("Bridge Python", env.get("bridge_python") or "Not configured"),
            ("SDK Module", profile.sdk_module or "-"),
        ]
        for idx, (label, value) in enumerate(info_rows):
            row = idx // 2
            col = (idx % 2) * 2
            ttk.Label(info_frame, text=f"{label}:").grid(row=row, column=col, sticky="w", padx=8, pady=6)
            ttk.Label(info_frame, text=value).grid(row=row, column=col + 1, sticky="w", padx=(0, 16), pady=6)

        hint = (
            "Please confirm account_id, token, strategy_id, and bridge Python match the live account before submitting."
        )
        ttk.Label(container, text=hint, foreground="#8a4b08", wraplength=920, justify="left").pack(
            anchor="w", pady=(0, 8)
        )

        order_frame = ttk.LabelFrame(container, text="Pending Orders")
        order_frame.pack(fill="both", expand=True)

        columns = ("symbol", "side", "price", "quantity", "stop", "target", "date")
        tree = ttk.Treeview(order_frame, columns=columns, show="headings", height=10)
        for key, title, width in [
            ("symbol", "Symbol", 120),
            ("side", "Side", 80),
            ("price", "Price", 90),
            ("quantity", "Qty", 90),
            ("stop", "Stop", 90),
            ("target", "Target", 90),
            ("date", "Signal Date", 110),
        ]:
            tree.heading(key, text=title)
            tree.column(key, width=width, anchor="center")
        for item in intents:
            tree.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    item.side,
                    f"{item.price:.3f}",
                    item.quantity,
                    f"{item.stop_price:.3f}",
                    f"{item.target_price:.3f}",
                    item.signal_date,
                ),
            )
        tree.pack(fill="both", expand=True, padx=8, pady=8)

        bottom = ttk.Frame(container)
        bottom.pack(fill="x", pady=(12, 0))

        ttk.Checkbutton(
            bottom,
            text="I have checked the account and order details.",
            variable=confirm_var,
        ).pack(side="left")

        button_bar = ttk.Frame(bottom)
        button_bar.pack(side="right")

        submit_button = ttk.Button(button_bar, text="Submit Orders")
        submit_button.pack(side="left")
        ttk.Button(button_bar, text="Cancel", command=dialog.destroy).pack(side="left", padx=(8, 0))

        def _sync_submit_state(*_args) -> None:
            submit_button.configure(state="normal" if confirm_var.get() else "disabled")

        def _confirm() -> None:
            if not confirm_var.get():
                return
            result["confirmed"] = True
            dialog.destroy()

        confirm_var.trace_add("write", _sync_submit_state)
        submit_button.configure(command=_confirm, state="disabled")
        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        self.wait_window(dialog)
        return bool(result["confirmed"])

    def _append_order_result(self, line: str) -> None:
        self.order_submission_log.append(line.rstrip())
        self.order_submission_log = self.order_submission_log[-200:]
        self.order_result_text.configure(state="normal")
        self.order_result_text.delete("1.0", tk.END)
        self.order_result_text.insert("1.0", "\n".join(self.order_submission_log) + "\n")
        self.order_result_text.see(tk.END)
        self.order_result_text.configure(state="disabled")

    def _refresh_broker_status(self, extra: str = "") -> None:
        adapter = EastmoneyBrokerAdapter()
        status = adapter.describe_status(self.current_broker_profile())
        holdings_summary = adapter.summarize_holdings(self.holdings, self.cash_snapshot)
        order_summary = f"Order ideas: {len(self.order_intents)}"
        content = [
            f"Gateway: {status.name}",
            f"Mode: {status.mode}",
            f"Connected: {'Yes' if status.connected else 'No'}",
            "",
            status.note,
            "",
            holdings_summary,
            "",
            order_summary,
        ]
        if extra:
            content.extend(["", extra])
        self.broker_status_text.delete("1.0", tk.END)
        self.broker_status_text.insert("1.0", "\n".join(content))

    def save_state(self) -> None:
        save_app_state(
            STATE_FILE,
            AppState(
                universe_dir=self.state.universe_dir,
                selected_symbol=self.state.selected_symbol,
                watchlist=self.state.watchlist,
                broker_profile=self.current_broker_profile(),
            ),
        )

    @staticmethod
    def _clear_tree(tree: ttk.Treeview) -> None:
        for row in tree.get_children():
            tree.delete(row)

    def on_close(self) -> None:
        self.cancel_auto_refresh()
        self.save_state()
        self.destroy()


if __name__ == "__main__":
    QuantHunterApp().mainloop()
