from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .models import BrokerProfile, PaperEquityPoint, PaperOrderRecord, PaperPatrolLog, PaperPosition, PaperTradingState
from .secret_store import protect_secret, reveal_secret

_ALL = "\u5168\u90e8"
_DEFAULT_ACCOUNT_NAME = "\u4e1c\u65b9\u8d22\u5bcc\u8d26\u6237"
_DEFAULT_MARKET_TIMEFRAME = "\u65e5\u7ebf"
_DEFAULT_MARKET_HISTORY_WINDOW = "\u8fd11\u5e74"
_DEFAULT_MARKET_REVIEW_DATE = "\u6700\u65b0"
_SENSITIVE_BROKER_FIELDS = ("token", "password")


@dataclass
class AppState:
    universe_dir: str = ""
    selected_symbol: str = ""
    watchlist: list[str] = field(default_factory=list)
    ui_theme: str = "sunrise"
    theme_alias_path: str = ""
    recommend_theme_filter: str = _ALL
    recommend_strategy_filter: str = _ALL
    recommend_action_filter: str = _ALL
    recommend_execution_filter: str = _ALL
    market_theme_filter: str = _ALL
    focus_themes: list[str] = field(default_factory=list)
    strategy_top_theme_limit: int = 3
    strategy_max_total_exposure: float = 0.85
    strategy_theme_drop_reduce: bool = True
    license_plan: str = "TRIAL"
    trial_started_at: str = field(default_factory=lambda: date.today().isoformat())
    auto_daily_plan_export: bool = False
    daily_plan_template: str = "balanced"
    daily_plan_focus_only: bool = False
    daily_plan_candidate_limit: int = 10
    market_data_mode: str = "auto"
    market_timeframe_mode: str = _DEFAULT_MARKET_TIMEFRAME
    market_history_window: str = _DEFAULT_MARKET_HISTORY_WINDOW
    market_review_date: str = _DEFAULT_MARKET_REVIEW_DATE
    broker_profile: BrokerProfile = field(default_factory=BrokerProfile)
    paper_trading_state: PaperTradingState = field(default_factory=PaperTradingState)


def _decode_broker_profile(broker_data: object) -> BrokerProfile:
    payload = broker_data if isinstance(broker_data, dict) else {}
    return BrokerProfile(
        account_name=payload.get("account_name", _DEFAULT_ACCOUNT_NAME),
        account_id=payload.get("account_id", ""),
        mode=payload.get("mode", "export"),
        export_dir=payload.get("export_dir", ""),
        sdk_module=payload.get("sdk_module", "gm.api"),
        sdk_python_path=payload.get("sdk_python_path", ""),
        token=reveal_secret(payload.get("token", "")),
        strategy_id=payload.get("strategy_id", ""),
        username=payload.get("username", ""),
        password=reveal_secret(payload.get("password", "")),
        auth_channel=payload.get("auth_channel", "eastmoney"),
    )


def _serialize_state(state: AppState) -> dict[str, object]:
    payload = asdict(state)
    broker_payload = dict(payload.get("broker_profile", {}))
    for field_name in _SENSITIVE_BROKER_FIELDS:
        broker_payload[field_name] = protect_secret(str(broker_payload.get(field_name, "")))
    payload["broker_profile"] = broker_payload
    return payload


def _decode_paper_trading_state(payload: object) -> PaperTradingState:
    data = payload if isinstance(payload, dict) else {}
    positions = [
        PaperPosition(
            symbol=str(item.get("symbol", "") or ""),
            stock_id=str(item.get("stock_id", "") or ""),
            stock_name=str(item.get("stock_name", "") or ""),
            quantity=int(item.get("quantity", 0) or 0),
            available=int(item.get("available", item.get("quantity", 0)) or 0),
            avg_cost=float(item.get("avg_cost", 0.0) or 0.0),
            current_price=float(item.get("current_price", 0.0) or 0.0),
            market_value=float(item.get("market_value", 0.0) or 0.0),
            entry_date=str(item.get("entry_date", "") or ""),
            strategy_name=str(item.get("strategy_name", "") or ""),
            buy_point=str(item.get("buy_point", "") or ""),
            sell_point=str(item.get("sell_point", "") or ""),
            stop_price=float(item.get("stop_price", 0.0) or 0.0),
            target_price=float(item.get("target_price", 0.0) or 0.0),
            rationale=str(item.get("rationale", "") or ""),
            unrealized_pnl=float(item.get("unrealized_pnl", 0.0) or 0.0),
            unrealized_pnl_pct=float(item.get("unrealized_pnl_pct", 0.0) or 0.0),
        )
        for item in data.get("positions", [])
        if isinstance(item, dict)
    ]
    ledger = [
        PaperOrderRecord(
            order_id=str(item.get("order_id", "") or ""),
            timestamp=str(item.get("timestamp", "") or ""),
            symbol=str(item.get("symbol", "") or ""),
            stock_id=str(item.get("stock_id", "") or ""),
            stock_name=str(item.get("stock_name", "") or ""),
            side=str(item.get("side", "") or ""),
            price=float(item.get("price", 0.0) or 0.0),
            quantity=int(item.get("quantity", 0) or 0),
            amount=float(item.get("amount", 0.0) or 0.0),
            strategy_name=str(item.get("strategy_name", "") or ""),
            position_pct=float(item.get("position_pct", 0.0) or 0.0),
            signal_source=str(item.get("signal_source", "") or ""),
            buy_point=str(item.get("buy_point", "") or ""),
            sell_point=str(item.get("sell_point", "") or ""),
            status=str(item.get("status", "FILLED") or "FILLED"),
            note=str(item.get("note", "") or ""),
            realized_pnl=float(item.get("realized_pnl", 0.0) or 0.0),
            realized_pnl_pct=float(item.get("realized_pnl_pct", 0.0) or 0.0),
            cumulative_realized_pnl=float(item.get("cumulative_realized_pnl", 0.0) or 0.0),
        )
        for item in data.get("ledger", [])
        if isinstance(item, dict)
    ]
    equity_curve = [
        PaperEquityPoint(
            timestamp=str(item.get("timestamp", "") or ""),
            cash=float(item.get("cash", 0.0) or 0.0),
            market_value=float(item.get("market_value", 0.0) or 0.0),
            total_equity=float(item.get("total_equity", 0.0) or 0.0),
            realized_pnl=float(item.get("realized_pnl", 0.0) or 0.0),
            total_return=float(item.get("total_return", 0.0) or 0.0),
            position_count=int(item.get("position_count", 0) or 0),
        )
        for item in data.get("equity_curve", [])
        if isinstance(item, dict)
    ]
    patrol_logs = [
        PaperPatrolLog(
            timestamp=str(item.get("timestamp", "") or ""),
            event_type=str(item.get("event_type", "") or ""),
            summary=str(item.get("summary", "") or ""),
            detail=str(item.get("detail", "") or ""),
            equity=float(item.get("equity", 0.0) or 0.0),
            total_return=float(item.get("total_return", 0.0) or 0.0),
            position_count=int(item.get("position_count", 0) or 0),
        )
        for item in data.get("patrol_logs", [])
        if isinstance(item, dict)
    ]
    initial_cash = float(data.get("initial_cash", 100000.0) or 100000.0)
    cash = float(data.get("cash", initial_cash) or initial_cash)
    total_equity = float(data.get("total_equity", cash) or cash)
    return PaperTradingState(
        enabled=bool(data.get("enabled", False)),
        auto_run=bool(data.get("auto_run", False)),
        auto_interval_minutes=float(data.get("auto_interval_minutes", 5.0) or 5.0),
        initial_cash=initial_cash,
        cash=cash,
        max_position_pct=float(data.get("max_position_pct", 0.25) or 0.25),
        positions=positions,
        ledger=ledger,
        equity_curve=equity_curve,
        patrol_logs=patrol_logs,
        realized_pnl=float(data.get("realized_pnl", 0.0) or 0.0),
        total_equity=total_equity,
        total_return=float(data.get("total_return", 0.0) or 0.0),
        last_run_at=str(data.get("last_run_at", "") or ""),
        last_strategy_note=str(data.get("last_strategy_note", "") or ""),
        order_sequence=int(data.get("order_sequence", 0) or 0),
    )


def load_app_state(path: str | Path) -> AppState:
    file_path = Path(path)
    if not file_path.exists():
        return AppState()
    try:
        raw_text = file_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return AppState()
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError):
        return AppState()
    return AppState(
        universe_dir=data.get("universe_dir", ""),
        selected_symbol=data.get("selected_symbol", ""),
        watchlist=list(data.get("watchlist", [])),
        ui_theme=data.get("ui_theme", "sunrise"),
        theme_alias_path=data.get("theme_alias_path", ""),
        recommend_theme_filter=data.get("recommend_theme_filter", _ALL),
        recommend_strategy_filter=data.get("recommend_strategy_filter", _ALL),
        recommend_action_filter=data.get("recommend_action_filter", _ALL),
        recommend_execution_filter=data.get("recommend_execution_filter", _ALL),
        market_theme_filter=data.get("market_theme_filter", _ALL),
        focus_themes=list(data.get("focus_themes", [])),
        strategy_top_theme_limit=int(data.get("strategy_top_theme_limit", 3) or 3),
        strategy_max_total_exposure=float(data.get("strategy_max_total_exposure", 0.85) or 0.85),
        strategy_theme_drop_reduce=bool(data.get("strategy_theme_drop_reduce", True)),
        license_plan=data.get("license_plan", "TRIAL"),
        trial_started_at=data.get("trial_started_at", date.today().isoformat()),
        auto_daily_plan_export=bool(data.get("auto_daily_plan_export", False)),
        daily_plan_template=data.get("daily_plan_template", "balanced"),
        daily_plan_focus_only=bool(data.get("daily_plan_focus_only", False)),
        daily_plan_candidate_limit=int(data.get("daily_plan_candidate_limit", 10) or 10),
        market_data_mode=data.get("market_data_mode", "auto"),
        market_timeframe_mode=data.get("market_timeframe_mode", _DEFAULT_MARKET_TIMEFRAME),
        market_history_window=data.get("market_history_window", _DEFAULT_MARKET_HISTORY_WINDOW),
        market_review_date=data.get("market_review_date", _DEFAULT_MARKET_REVIEW_DATE),
        broker_profile=_decode_broker_profile(data.get("broker_profile", {})),
        paper_trading_state=_decode_paper_trading_state(data.get("paper_trading_state", {})),
    )


def save_app_state(path: str | Path, state: AppState) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_state(state)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
