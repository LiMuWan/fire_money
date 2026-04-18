from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class PriceBar:
    date: str
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class TrapState:
    index: int
    date: str
    symbol: str
    breakout_level: float
    trap_high: float
    trap_low: float
    trap_close: float
    trap_midpoint: float
    atr_at_trap: float
    trap_volume: float
    expire_index: int


@dataclass(frozen=True)
class DailyAnalysis:
    date: str
    symbol: str
    close: float
    atr: float
    ma_fast: float
    ma_slow: float
    breakout_level: float
    volume_ratio: float
    upper_shadow_pct: float
    close_location: float
    label: str
    score: int
    reason: str
    entry_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    hold_days: int
    exit_reason: str


@dataclass(frozen=True)
class EquityPoint:
    date: str
    equity: float


@dataclass(frozen=True)
class BacktestResult:
    initial_capital: float
    ending_equity: float
    total_return: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)


@dataclass(frozen=True)
class PortfolioSnapshot:
    date: str
    cash: float
    market_value: float
    total_equity: float
    position_count: int
    exposure_ratio: float


@dataclass(frozen=True)
class PortfolioBacktestResult:
    initial_capital: float
    ending_equity: float
    total_return: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    avg_exposure: float = 0.0
    max_concurrent_positions: int = 0
    trades: list[Trade] = field(default_factory=list)
    equity_curve: list[EquityPoint] = field(default_factory=list)
    snapshots: list[PortfolioSnapshot] = field(default_factory=list)


@dataclass(frozen=True)
class BrokerStatus:
    name: str
    mode: str
    connected: bool
    note: str


@dataclass(frozen=True)
class ScanRow:
    symbol: str
    signal_date: str
    label: str
    action: str
    score: int
    close: float
    entry_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    reason: str
    source_path: str
    stock_id: str = ""
    stock_name: str = ""


@dataclass(frozen=True)
class SymbolBacktestSummary:
    symbol: str
    trades: int
    total_return: float
    max_drawdown: float
    win_rate: float
    ending_equity: float


@dataclass(frozen=True)
class StockProfile:
    symbol: str
    stock_id: str
    name: str
    industry: str = ""
    is_leader: bool = False
    notes: str = ""


@dataclass(frozen=True)
class NewsCatalyst:
    symbol: str
    title: str
    summary: str
    published_at: str
    source: str = ""
    url: str = ""
    sentiment_score: float = 0.0
    heat: float = 0.0


@dataclass(frozen=True)
class RecommendationRow:
    symbol: str
    stock_id: str
    stock_name: str
    action: str
    label: str
    signal_date: str
    close: float
    entry_price: Optional[float]
    stop_price: Optional[float]
    target_price: Optional[float]
    technical_score: float
    position_score: float
    persistence_score: float
    news_score: float
    leader_score: float
    total_score: float
    backtest_quality_score: float = 0.0
    portfolio_fit_score: float = 0.0
    diversification_score: float = 0.0
    concentration_penalty_score: float = 0.0
    theme_name: str = ""
    theme_score: float = 0.0
    theme_rank: int = 0
    leader_level: str = ""
    primary_strategy: str = ""
    stock_pool: str = ""
    pool_score: float = 0.0
    buy_point: str = ""
    add_point: str = ""
    sell_point: str = ""
    risk_line: str = ""
    leader_model_score: float = 0.0
    main_force_score: float = 0.0
    board_attack_score: float = 0.0
    value_recovery_score: float = 0.0
    tail_buy_score: float = 0.0
    one_day_hold_score: float = 0.0
    dragon_decision_score: float = 0.0
    mainline_tag: str = ""
    mainline_rank: int = 0
    mainline_role: str = ""
    mainline_strength_score: float = 0.0
    mainline_continuation_score: float = 0.0
    leader_position_score: float = 0.0
    mainline_window_score: float = 0.0
    theme_divergence_score: float = 0.0
    theme_failure_risk: float = 0.0
    theme_rotation_score: float = 0.0
    mainline_risk_flag: str = ""
    confidence_score: float = 0.0
    execution_readiness: float = 0.0
    timeliness_score: float = 0.0
    freshness_score: float = 0.0
    setup_quality_score: float = 0.0
    risk_reward_ratio: float = 0.0
    signal_age_days: int = 0
    signal_source: str = ""
    opportunity_tier: str = ""
    reject_reason: str = ""
    next_focus: str = ""
    invalidation_reason: str = ""
    catalyst: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class ThemeHeatRow:
    theme_name: str
    strength_score: float
    continuation_score: float
    news_score: float
    leader_count: int
    stock_count: int
    theme_rank: int
    risk_flag: str
    divergence_score: float = 0.0
    failure_risk: float = 0.0
    rotation_score: float = 0.0
    window_score: float = 0.0
    is_primary: bool = False


@dataclass(frozen=True)
class LeaderCandidate:
    symbol: str
    stock_id: str
    stock_name: str
    theme_name: str
    leader_level: str
    leader_score: float
    theme_rank: int
    action: str
    rationale: str
    mainline_role: str = ""
    mainline_window_score: float = 0.0
    mainline_risk_flag: str = ""


@dataclass(frozen=True)
class BrokerProfile:
    account_name: str = "东方财富账户"
    account_id: str = ""
    mode: str = "export"
    export_dir: str = ""
    sdk_module: str = "gm.api"
    sdk_python_path: str = ""
    token: str = ""
    strategy_id: str = ""
    username: str = ""
    password: str = ""
    auth_channel: str = "eastmoney"
    test_submit_only: bool = True
    test_submit_max_amount: float = 10000.0
    test_submit_symbol_whitelist: str = ""
    auto_export_submission_records: bool = True


@dataclass(frozen=True)
class OrderIntent:
    symbol: str
    side: str
    price: float
    quantity: int
    stop_price: float
    target_price: float
    signal_date: str
    reason: str
    opportunity_tier: str = ""
    risk_flag: str = ""
    signal_source: str = ""
    risk_reward_ratio: float = 0.0


@dataclass(frozen=True)
class HoldingRecord:
    symbol: str
    quantity: int
    available: int
    cost_price: float
    market_value: float


@dataclass(frozen=True)
class CashSnapshot:
    available_cash: float
    total_assets: float


@dataclass(frozen=True)
class PaperPosition:
    symbol: str
    stock_id: str = ""
    stock_name: str = ""
    quantity: int = 0
    available: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    market_value: float = 0.0
    entry_date: str = ""
    strategy_name: str = ""
    buy_point: str = ""
    sell_point: str = ""
    stop_price: float = 0.0
    target_price: float = 0.0
    rationale: str = ""
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0


@dataclass(frozen=True)
class PaperOrderRecord:
    order_id: str
    timestamp: str
    symbol: str
    stock_id: str
    stock_name: str
    side: str
    price: float
    quantity: int
    amount: float
    strategy_name: str = ""
    position_pct: float = 0.0
    signal_source: str = ""
    buy_point: str = ""
    sell_point: str = ""
    status: str = "FILLED"
    note: str = ""
    realized_pnl: float = 0.0
    realized_pnl_pct: float = 0.0
    cumulative_realized_pnl: float = 0.0


@dataclass(frozen=True)
class PaperEquityPoint:
    timestamp: str
    cash: float = 0.0
    market_value: float = 0.0
    total_equity: float = 0.0
    realized_pnl: float = 0.0
    total_return: float = 0.0
    position_count: int = 0


@dataclass(frozen=True)
class PaperPatrolLog:
    timestamp: str
    event_type: str = ""
    summary: str = ""
    detail: str = ""
    equity: float = 0.0
    total_return: float = 0.0
    position_count: int = 0


@dataclass(frozen=True)
class PaperTradingState:
    enabled: bool = False
    auto_run: bool = False
    auto_interval_minutes: float = 5.0
    initial_cash: float = 100000.0
    cash: float = 100000.0
    max_position_pct: float = 0.25
    positions: list[PaperPosition] = field(default_factory=list)
    ledger: list[PaperOrderRecord] = field(default_factory=list)
    equity_curve: list[PaperEquityPoint] = field(default_factory=list)
    patrol_logs: list[PaperPatrolLog] = field(default_factory=list)
    realized_pnl: float = 0.0
    total_equity: float = 100000.0
    total_return: float = 0.0
    last_run_at: str = ""
    last_strategy_note: str = ""
    order_sequence: int = 0


@dataclass(frozen=True)
class OptimizationRun:
    rank: int
    params: dict[str, float | int]
    objective: float
    avg_return: float
    avg_drawdown: float
    avg_win_rate: float
    trade_count: int
    symbols_tested: int
    robustness_score: float = 0.0
    avg_out_of_sample_return: float = 0.0
    avg_median_window_return: float = 0.0
    avg_worst_window_return: float = 0.0
    avg_return_std: float = 0.0
    avg_positive_window_ratio: float = 0.0
    avg_profit_factor: float = 0.0
    portfolio_return: float = 0.0
    portfolio_out_of_sample_return: float = 0.0
    portfolio_worst_window_return: float = 0.0
    portfolio_return_std: float = 0.0
    portfolio_max_drawdown: float = 0.0
    portfolio_profit_factor: float = 0.0
    portfolio_avg_exposure: float = 0.0
    portfolio_max_concurrent_positions: int = 0


@dataclass(frozen=True)
class ReportArtifacts:
    markdown_path: str
    csv_path: str
    json_path: str


@dataclass(frozen=True)
class StrategyHistorySignal:
    symbol: str
    stock_id: str
    stock_name: str
    signal_date: str
    generated_at: str
    strategy_name: str
    action: str
    entry_price: float
    stop_price: float
    target_price: float
    source_file: str
    source_kind: str = ""
    rationale: str = ""


@dataclass(frozen=True)
class StrategyHistoryTrade:
    strategy_name: str
    symbol: str
    stock_id: str
    stock_name: str
    signal_date: str
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    pnl_pct: float
    hold_days: int
    exit_reason: str
    source_file: str


@dataclass(frozen=True)
class StrategyHistorySummary:
    strategy_name: str
    signal_count: int
    trade_count: int
    filled_ratio: float
    win_rate: float
    total_return: float
    avg_return: float
    max_drawdown: float
    avg_hold_days: float
    symbol_count: int
    no_fill_count: int = 0
    missing_data_count: int = 0
    target_hits: int = 0
    stop_hits: int = 0
    timeout_exits: int = 0
    end_exits: int = 0
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0
    max_consecutive_wins: int = 0
    max_consecutive_losses: int = 0
    best_trade_return: float = 0.0
    worst_trade_return: float = 0.0


@dataclass(frozen=True)
class StrategyHistoryEquityPoint:
    strategy_name: str
    date: str
    equity: float
    trade_index: int


@dataclass(frozen=True)
class StrategyHistoryPeriodStat:
    strategy_name: str
    period: str
    trade_count: int
    win_rate: float
    total_return: float
    avg_return: float


@dataclass(frozen=True)
class StrategyHistoryReport:
    start_date: str
    end_date: str
    source_files: list[str] = field(default_factory=list)
    signals: list[StrategyHistorySignal] = field(default_factory=list)
    trades: list[StrategyHistoryTrade] = field(default_factory=list)
    summaries: list[StrategyHistorySummary] = field(default_factory=list)
    equity_points: list[StrategyHistoryEquityPoint] = field(default_factory=list)
    yearly_stats: list[StrategyHistoryPeriodStat] = field(default_factory=list)
    monthly_stats: list[StrategyHistoryPeriodStat] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StrategyHistoryScenarioComparison:
    scenario_label: str
    scenario_note: str
    strategy_name: str
    max_hold_days: int
    slippage_rate: float
    commission_rate: float
    stamp_duty_rate: float
    block_limit_up_entry: bool
    block_limit_down_exit: bool
    signal_count: int
    trade_count: int
    filled_ratio: float
    total_return: float
    win_rate: float
    max_drawdown: float
    profit_factor: float = 0.0
    payoff_ratio: float = 0.0
    avg_hold_days: float = 0.0
    max_consecutive_losses: int = 0


@dataclass(frozen=True)
class StrategyHistoryScenarioLeaderboard:
    strategy_name: str
    scenario_count: int
    best_scenario_label: str
    best_total_return: float
    worst_scenario_label: str
    worst_total_return: float
    return_spread: float
    avg_total_return: float = 0.0
