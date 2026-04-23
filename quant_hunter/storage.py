from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import date
from pathlib import Path

from .models import BrokerProfile, PaperEquityPoint, PaperOrderRecord, PaperPatrolLog, PaperPosition, PaperTradingState
from .risk import normalize_risk_profile
from .secret_store import protect_secret, reveal_secret

_ALL = "\u5168\u90e8"
_DEFAULT_ACCOUNT_NAME = "\u4e1c\u65b9\u8d22\u5bcc\u8d26\u6237"
_DEFAULT_MARKET_TIMEFRAME = "\u65e5\u7ebf"
_DEFAULT_MARKET_HISTORY_WINDOW = "\u8fd11\u5e74"
_DEFAULT_MARKET_REVIEW_DATE = "\u6700\u65b0"
_DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE = "FULL"
_DEFAULT_MARKET_OVERLAY_MODES = ["MA", "BOLL", "HIGHLOW"]
_DEFAULT_MARKET_SECONDARY_INDICATOR = "MACD"
_DEFAULT_MARKET_CHART_PRESET = "BALANCED"
_DEFAULT_MARKET_CHART_ACTION_NOTE_FILTER_SOURCE = ""
_SENSITIVE_BROKER_FIELDS = ("token", "password")
_SENSITIVE_STATE_FIELDS = ("ai_review_api_key",)


def _as_string_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item or "") for item in value if str(item or "").strip()]
    if isinstance(value, tuple):
        return [str(item or "") for item in value if str(item or "").strip()]
    return []


def _safe_float(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: object, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default


def _as_int_list(value: object, *, count: int | None = None) -> list[int]:
    items: list[int] = []
    if isinstance(value, (list, tuple)):
        for raw in value:
            parsed = _safe_int(raw, 0)
            if parsed > 0:
                items.append(parsed)
    if count is not None and len(items) != count:
        return []
    return items


def _normalize_market_strategy_annotation_mode(value: object) -> str:
    normalized = str(value or _DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE).strip().upper()
    return normalized if normalized in {"FULL", "PLAN", "OFF"} else _DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE


def _normalize_market_overlay_modes(value: object) -> list[str]:
    allowed = ["MA", "BOLL", "HIGHLOW", "BREAK"]
    items = [str(item or "").strip().upper() for item in _as_string_list(value)]
    normalized = [item for item in allowed if item in items]
    return normalized or list(_DEFAULT_MARKET_OVERLAY_MODES)


def _normalize_market_secondary_indicator(value: object) -> str:
    normalized = str(value or _DEFAULT_MARKET_SECONDARY_INDICATOR).strip().upper()
    return normalized if normalized in {"MACD", "RSI", "KDJ", "VOL"} else _DEFAULT_MARKET_SECONDARY_INDICATOR


def _normalize_market_chart_preset(value: object) -> str:
    normalized = str(value or _DEFAULT_MARKET_CHART_PRESET).strip().upper()
    if normalized in {"BALANCED", "CLEAN", "SIGNAL", "FLOW", "CUSTOM"}:
        return normalized
    if normalized.startswith("USER_"):
        return normalized
    return _DEFAULT_MARKET_CHART_PRESET


def _normalize_market_chart_custom_presets(value: object) -> dict[str, dict[str, object]]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, dict[str, object]] = {}
    for raw_key, raw_item in value.items():
        if not isinstance(raw_item, dict):
            continue
        key = _normalize_market_chart_preset(raw_key)
        if not key.startswith("USER_"):
            continue
        normalized[key] = {
            "label": str(raw_item.get("label", "") or "").strip() or key.replace("USER_", "自定义 "),
            "detail": str(raw_item.get("detail", "") or "").strip(),
            "tags": _as_string_list(raw_item.get("tags", [])),
            "overlays": _normalize_market_overlay_modes(raw_item.get("overlays", _DEFAULT_MARKET_OVERLAY_MODES)),
            "annotation_mode": _normalize_market_strategy_annotation_mode(
                raw_item.get("annotation_mode", _DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE)
            ),
            "indicator": _normalize_market_secondary_indicator(
                raw_item.get("indicator", _DEFAULT_MARKET_SECONDARY_INDICATOR)
            ),
            "expanded": bool(raw_item.get("expanded", False)),
            "pinned": bool(raw_item.get("pinned", False)),
        }
    return normalized


def _normalize_market_chart_preset_usage_counts(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    normalized: dict[str, int] = {}
    for raw_key, raw_value in value.items():
        key = _normalize_market_chart_preset(raw_key)
        if not key:
            continue
        try:
            count = int(raw_value)
        except (TypeError, ValueError):
            try:
                count = int(float(raw_value))
            except (TypeError, ValueError):
                count = 0
        if count > 0:
            normalized[key] = count
    return normalized


def _normalize_market_chart_action_note_filter_source(value: object) -> str:
    normalized = str(value or _DEFAULT_MARKET_CHART_ACTION_NOTE_FILTER_SOURCE).strip()
    return normalized if normalized in {"", "计划", "信号", "复盘", "图表"} else _DEFAULT_MARKET_CHART_ACTION_NOTE_FILTER_SOURCE


_MARKET_CHART_ACTION_NOTE_FIELDS = (
    "symbol",
    "decision_text",
    "execution_text",
    "conclusion_text",
    "title",
    "history_source",
    "history_summary",
    "interacted_at",
    "tone",
    "panel_role",
    "pinned",
)


def _normalize_market_chart_action_note_history(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value[-3:]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "symbol": str(item.get("symbol", "") or ""),
                "decision_text": str(item.get("decision_text", "") or ""),
                "execution_text": str(item.get("execution_text", "") or ""),
                "conclusion_text": str(item.get("conclusion_text", "") or ""),
                "title": str(item.get("title", "") or ""),
                "history_source": _normalize_market_chart_action_note_filter_source(item.get("history_source", "")),
                "history_summary": str(item.get("history_summary", "") or ""),
                "interacted_at": str(item.get("interacted_at", "") or ""),
                "tone": str(item.get("tone", "watch") or "watch"),
                "panel_role": str(item.get("panel_role", "execution") or "execution"),
                "pinned": bool(item.get("pinned", False)),
            }
        )
    return rows


def _normalize_market_chart_action_note_history_index(value: object, history: list[dict[str, object]]) -> int:
    if not history:
        return 0
    try:
        index = int(value)
    except (TypeError, ValueError):
        index = len(history) - 1
    return max(0, min(index, len(history) - 1))


@dataclass
class AppState:
    universe_dir: str = ""
    selected_symbol: str = ""
    watchlist: list[str] = field(default_factory=list)
    ui_theme: str = "dark"
    ui_density: str = "compact"
    theme_alias_path: str = ""
    news_source_provider: str = "csv"
    news_source_path: str = ""
    news_source_last_loaded_at: str = ""
    news_source_status: str = ""
    recommend_theme_filter: str = _ALL
    recommend_strategy_filter: str = _ALL
    recommend_action_filter: str = _ALL
    recommend_execution_filter: str = _ALL
    market_theme_filter: str = _ALL
    focus_themes: list[str] = field(default_factory=list)
    strategy_risk_profile: str = "standard"
    strategy_top_theme_limit: int = 3
    strategy_max_total_exposure: float = 0.85
    strategy_theme_drop_reduce: bool = True
    license_plan: str = "TRIAL"
    trial_started_at: str = field(default_factory=lambda: date.today().isoformat())
    auto_daily_plan_export: bool = False
    daily_plan_template: str = "balanced"
    daily_plan_focus_only: bool = False
    daily_plan_candidate_limit: int = 10
    ai_review_base_url: str = "https://api.openai.com/v1"
    ai_review_api_key: str = ""
    ai_review_model: str = "gpt-5.4"
    ai_review_reasoning_effort: str = "medium"
    ai_review_max_output_tokens: int = 900
    ai_review_timeout_seconds: float = 45.0
    ai_review_auto_run_enabled: bool = False
    ai_review_auto_run_on_news_refresh: bool = True
    ai_review_auto_run_on_pool_refresh: bool = True
    market_data_mode: str = "auto"
    market_timeframe_mode: str = _DEFAULT_MARKET_TIMEFRAME
    market_history_window: str = _DEFAULT_MARKET_HISTORY_WINDOW
    market_review_date: str = _DEFAULT_MARKET_REVIEW_DATE
    market_strategy_annotation_mode: str = _DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE
    market_overlay_modes: list[str] = field(default_factory=lambda: list(_DEFAULT_MARKET_OVERLAY_MODES))
    market_secondary_indicator_mode: str = _DEFAULT_MARKET_SECONDARY_INDICATOR
    market_primary_chart_expanded: bool = False
    market_chart_preset: str = _DEFAULT_MARKET_CHART_PRESET
    market_chart_custom_presets: dict[str, dict[str, object]] = field(default_factory=dict)
    market_chart_recent_presets: list[str] = field(default_factory=list)
    market_chart_preset_usage_counts: dict[str, int] = field(default_factory=dict)
    market_chart_action_note_filter_source: str = _DEFAULT_MARKET_CHART_ACTION_NOTE_FILTER_SOURCE
    market_chart_action_note_history: list[dict[str, object]] = field(default_factory=list)
    market_chart_action_note_history_index: int = 0
    recommend_review_splitter_sizes: list[int] = field(default_factory=list)
    broker_profile: BrokerProfile = field(default_factory=BrokerProfile)
    paper_trading_state: PaperTradingState = field(default_factory=PaperTradingState)
    order_submission_log: list[str] = field(default_factory=list)
    order_submission_records: list[dict[str, str]] = field(default_factory=list)
    smart_message_events: list[dict[str, object]] = field(default_factory=list)
    recommend_message_center_filter: str = "all"
    recommend_message_center_show_unhandled_only: bool = False
    recommend_message_center_sort: str = "latest"


_SUBMISSION_RECORD_FIELDS = (
    "timestamp",
    "order_status",
    "fill_status",
    "order_id",
    "symbol",
    "side",
    "price",
    "quantity",
    "failure_reason",
    "message",
    "planned_price",
    "planned_quantity",
    "planned_stop_price",
    "planned_target_price",
    "strategy_name",
    "opportunity_tier",
    "planned_risk_reward_ratio",
    "portfolio_fit_score",
    "diversification_score",
    "concentration_penalty_score",
    "fill_price",
    "fill_quantity",
)

_SMART_MESSAGE_EVENT_FIELDS = (
    "timestamp",
    "category",
    "title",
    "detail",
    "symbol",
    "level",
    "is_read",
    "is_handled",
)


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
        test_submit_only=bool(payload.get("test_submit_only", True)),
        test_submit_max_amount=_safe_float(payload.get("test_submit_max_amount", 10000.0) or 10000.0, 10000.0),
        test_submit_symbol_whitelist=str(payload.get("test_submit_symbol_whitelist", "") or ""),
        auto_export_submission_records=bool(payload.get("auto_export_submission_records", True)),
    )


def _decode_submission_records(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, str]] = []
    for item in value[:500]:
        if not isinstance(item, dict):
            continue
        rows.append({field: str(item.get(field, "") or "") for field in _SUBMISSION_RECORD_FIELDS})
    return rows


def _decode_smart_message_events(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, object]] = []
    for item in value[:120]:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "timestamp": str(item.get("timestamp", "") or ""),
                "category": str(item.get("category", "") or ""),
                "title": str(item.get("title", "") or ""),
                "detail": str(item.get("detail", "") or ""),
                "symbol": str(item.get("symbol", "") or ""),
                "level": str(item.get("level", "") or ""),
                "is_read": bool(item.get("is_read", False)),
                "is_handled": bool(item.get("is_handled", False)),
            }
        )
    return rows


def _serialize_state(state: AppState) -> dict[str, object]:
    payload = asdict(state)
    broker_payload = dict(payload.get("broker_profile", {}))
    for field_name in _SENSITIVE_BROKER_FIELDS:
        broker_payload[field_name] = protect_secret(str(broker_payload.get(field_name, "")))
    payload["broker_profile"] = broker_payload
    for field_name in _SENSITIVE_STATE_FIELDS:
        payload[field_name] = protect_secret(str(payload.get(field_name, "")))
    payload["order_submission_log"] = [str(item or "") for item in list(payload.get("order_submission_log", []) or [])[:200] if str(item or "").strip()]
    payload["order_submission_records"] = _decode_submission_records(payload.get("order_submission_records", []))
    payload["smart_message_events"] = _decode_smart_message_events(payload.get("smart_message_events", []))
    payload["market_chart_action_note_history"] = _normalize_market_chart_action_note_history(
        payload.get("market_chart_action_note_history", [])
    )
    payload["market_chart_action_note_history_index"] = _normalize_market_chart_action_note_history_index(
        payload.get("market_chart_action_note_history_index", 0),
        payload["market_chart_action_note_history"],
    )
    return payload


def _decode_paper_trading_state(payload: object) -> PaperTradingState:
    data = payload if isinstance(payload, dict) else {}
    positions = [
        PaperPosition(
            symbol=str(item.get("symbol", "") or ""),
            stock_id=str(item.get("stock_id", "") or ""),
            stock_name=str(item.get("stock_name", "") or ""),
            quantity=_safe_int(item.get("quantity", 0) or 0, 0),
            available=_safe_int(item.get("available", item.get("quantity", 0)) or 0, 0),
            avg_cost=_safe_float(item.get("avg_cost", 0.0) or 0.0, 0.0),
            current_price=_safe_float(item.get("current_price", 0.0) or 0.0, 0.0),
            market_value=_safe_float(item.get("market_value", 0.0) or 0.0, 0.0),
            entry_date=str(item.get("entry_date", "") or ""),
            strategy_name=str(item.get("strategy_name", "") or ""),
            buy_point=str(item.get("buy_point", "") or ""),
            sell_point=str(item.get("sell_point", "") or ""),
            stop_price=_safe_float(item.get("stop_price", 0.0) or 0.0, 0.0),
            target_price=_safe_float(item.get("target_price", 0.0) or 0.0, 0.0),
            rationale=str(item.get("rationale", "") or ""),
            unrealized_pnl=_safe_float(item.get("unrealized_pnl", 0.0) or 0.0, 0.0),
            unrealized_pnl_pct=_safe_float(item.get("unrealized_pnl_pct", 0.0) or 0.0, 0.0),
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
            price=_safe_float(item.get("price", 0.0) or 0.0, 0.0),
            quantity=_safe_int(item.get("quantity", 0) or 0, 0),
            amount=_safe_float(item.get("amount", 0.0) or 0.0, 0.0),
            strategy_name=str(item.get("strategy_name", "") or ""),
            position_pct=_safe_float(item.get("position_pct", 0.0) or 0.0, 0.0),
            signal_source=str(item.get("signal_source", "") or ""),
            buy_point=str(item.get("buy_point", "") or ""),
            sell_point=str(item.get("sell_point", "") or ""),
            status=str(item.get("status", "FILLED") or "FILLED"),
            note=str(item.get("note", "") or ""),
            realized_pnl=_safe_float(item.get("realized_pnl", 0.0) or 0.0, 0.0),
            realized_pnl_pct=_safe_float(item.get("realized_pnl_pct", 0.0) or 0.0, 0.0),
            cumulative_realized_pnl=_safe_float(item.get("cumulative_realized_pnl", 0.0) or 0.0, 0.0),
        )
        for item in data.get("ledger", [])
        if isinstance(item, dict)
    ]
    equity_curve = [
        PaperEquityPoint(
            timestamp=str(item.get("timestamp", "") or ""),
            cash=_safe_float(item.get("cash", 0.0) or 0.0, 0.0),
            market_value=_safe_float(item.get("market_value", 0.0) or 0.0, 0.0),
            total_equity=_safe_float(item.get("total_equity", 0.0) or 0.0, 0.0),
            realized_pnl=_safe_float(item.get("realized_pnl", 0.0) or 0.0, 0.0),
            total_return=_safe_float(item.get("total_return", 0.0) or 0.0, 0.0),
            position_count=_safe_int(item.get("position_count", 0) or 0, 0),
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
            equity=_safe_float(item.get("equity", 0.0) or 0.0, 0.0),
            total_return=_safe_float(item.get("total_return", 0.0) or 0.0, 0.0),
            position_count=_safe_int(item.get("position_count", 0) or 0, 0),
        )
        for item in data.get("patrol_logs", [])
        if isinstance(item, dict)
    ]
    initial_cash = _safe_float(data.get("initial_cash", 100000.0) or 100000.0, 100000.0)
    cash = _safe_float(data.get("cash", initial_cash) or initial_cash, initial_cash)
    total_equity = _safe_float(data.get("total_equity", cash) or cash, cash)
    return PaperTradingState(
        enabled=bool(data.get("enabled", False)),
        auto_run=bool(data.get("auto_run", False)),
        auto_interval_minutes=_safe_float(data.get("auto_interval_minutes", 5.0) or 5.0, 5.0),
        initial_cash=initial_cash,
        cash=cash,
        max_position_pct=_safe_float(data.get("max_position_pct", 0.25) or 0.25, 0.25),
        positions=positions,
        ledger=ledger,
        equity_curve=equity_curve,
        patrol_logs=patrol_logs,
        realized_pnl=_safe_float(data.get("realized_pnl", 0.0) or 0.0, 0.0),
        total_equity=total_equity,
        total_return=_safe_float(data.get("total_return", 0.0) or 0.0, 0.0),
        last_run_at=str(data.get("last_run_at", "") or ""),
        last_strategy_note=str(data.get("last_strategy_note", "") or ""),
        order_sequence=_safe_int(data.get("order_sequence", 0) or 0, 0),
    )


def load_app_state(path: str | Path) -> AppState:
    file_path = Path(path)
    if not file_path.exists():
        return AppState(ui_theme="sunrise")
    try:
        raw_text = file_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return AppState(ui_theme="sunrise")
        data = json.loads(raw_text)
    except (OSError, json.JSONDecodeError):
        return AppState(ui_theme="sunrise")
    chart_action_note_history = _normalize_market_chart_action_note_history(data.get("market_chart_action_note_history", []))
    return AppState(
        universe_dir=data.get("universe_dir", ""),
        selected_symbol=data.get("selected_symbol", ""),
        watchlist=_as_string_list(data.get("watchlist", [])),
        ui_theme=data.get("ui_theme", "dark"),
        ui_density=str(data.get("ui_density", "compact") or "compact"),
        theme_alias_path=data.get("theme_alias_path", ""),
        news_source_provider=str(data.get("news_source_provider", "csv") or "csv"),
        news_source_path=str(data.get("news_source_path", "") or ""),
        news_source_last_loaded_at=str(data.get("news_source_last_loaded_at", "") or ""),
        news_source_status=str(data.get("news_source_status", "") or ""),
        recommend_theme_filter=data.get("recommend_theme_filter", _ALL),
        recommend_strategy_filter=data.get("recommend_strategy_filter", _ALL),
        recommend_action_filter=data.get("recommend_action_filter", _ALL),
        recommend_execution_filter=data.get("recommend_execution_filter", _ALL),
        market_theme_filter=data.get("market_theme_filter", _ALL),
        focus_themes=_as_string_list(data.get("focus_themes", [])),
        strategy_risk_profile=normalize_risk_profile(data.get("strategy_risk_profile", "standard")),
        strategy_top_theme_limit=int(data.get("strategy_top_theme_limit", 3) or 3),
        strategy_max_total_exposure=float(data.get("strategy_max_total_exposure", 0.85) or 0.85),
        strategy_theme_drop_reduce=bool(data.get("strategy_theme_drop_reduce", True)),
        license_plan=data.get("license_plan", "TRIAL"),
        trial_started_at=data.get("trial_started_at", date.today().isoformat()),
        auto_daily_plan_export=bool(data.get("auto_daily_plan_export", False)),
        daily_plan_template=data.get("daily_plan_template", "balanced"),
        daily_plan_focus_only=bool(data.get("daily_plan_focus_only", False)),
        daily_plan_candidate_limit=int(data.get("daily_plan_candidate_limit", 10) or 10),
        ai_review_base_url=str(data.get("ai_review_base_url", "https://api.openai.com/v1") or "https://api.openai.com/v1"),
        ai_review_api_key=reveal_secret(str(data.get("ai_review_api_key", "") or "")),
        ai_review_model=str(data.get("ai_review_model", "gpt-5.4") or "gpt-5.4"),
        ai_review_reasoning_effort=str(data.get("ai_review_reasoning_effort", "medium") or "medium"),
        ai_review_max_output_tokens=_safe_int(data.get("ai_review_max_output_tokens", 900) or 900, 900),
        ai_review_timeout_seconds=_safe_float(data.get("ai_review_timeout_seconds", 45.0) or 45.0, 45.0),
        ai_review_auto_run_enabled=bool(data.get("ai_review_auto_run_enabled", False)),
        ai_review_auto_run_on_news_refresh=bool(data.get("ai_review_auto_run_on_news_refresh", True)),
        ai_review_auto_run_on_pool_refresh=bool(data.get("ai_review_auto_run_on_pool_refresh", True)),
        market_data_mode=data.get("market_data_mode", "auto"),
        market_timeframe_mode=data.get("market_timeframe_mode", _DEFAULT_MARKET_TIMEFRAME),
        market_history_window=data.get("market_history_window", _DEFAULT_MARKET_HISTORY_WINDOW),
        market_review_date=data.get("market_review_date", _DEFAULT_MARKET_REVIEW_DATE),
        market_strategy_annotation_mode=_normalize_market_strategy_annotation_mode(
            data.get("market_strategy_annotation_mode", _DEFAULT_MARKET_STRATEGY_ANNOTATION_MODE)
        ),
        market_overlay_modes=_normalize_market_overlay_modes(data.get("market_overlay_modes", _DEFAULT_MARKET_OVERLAY_MODES)),
        market_secondary_indicator_mode=_normalize_market_secondary_indicator(
            data.get("market_secondary_indicator_mode", _DEFAULT_MARKET_SECONDARY_INDICATOR)
        ),
        market_primary_chart_expanded=bool(data.get("market_primary_chart_expanded", False)),
        market_chart_preset=_normalize_market_chart_preset(
            data.get("market_chart_preset", _DEFAULT_MARKET_CHART_PRESET)
        ),
        market_chart_custom_presets=_normalize_market_chart_custom_presets(
            data.get("market_chart_custom_presets", {})
        ),
        market_chart_recent_presets=_as_string_list(data.get("market_chart_recent_presets", []))[:12],
        market_chart_preset_usage_counts=_normalize_market_chart_preset_usage_counts(
            data.get("market_chart_preset_usage_counts", {})
        ),
        market_chart_action_note_filter_source=_normalize_market_chart_action_note_filter_source(
            data.get("market_chart_action_note_filter_source", _DEFAULT_MARKET_CHART_ACTION_NOTE_FILTER_SOURCE)
        ),
        market_chart_action_note_history=chart_action_note_history,
        market_chart_action_note_history_index=_normalize_market_chart_action_note_history_index(
            data.get("market_chart_action_note_history_index", 0),
            chart_action_note_history,
        ),
        recommend_review_splitter_sizes=_as_int_list(
            data.get("recommend_review_splitter_sizes", []),
            count=3,
        ),
        broker_profile=_decode_broker_profile(data.get("broker_profile", {})),
        paper_trading_state=_decode_paper_trading_state(data.get("paper_trading_state", {})),
        order_submission_log=_as_string_list(data.get("order_submission_log", []))[:200],
        order_submission_records=_decode_submission_records(data.get("order_submission_records", [])),
        smart_message_events=_decode_smart_message_events(data.get("smart_message_events", [])),
        recommend_message_center_filter=str(data.get("recommend_message_center_filter", "all") or "all"),
        recommend_message_center_show_unhandled_only=bool(data.get("recommend_message_center_show_unhandled_only", False)),
        recommend_message_center_sort=str(data.get("recommend_message_center_sort", "latest") or "latest"),
    )


def save_app_state(path: str | Path, state: AppState) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _serialize_state(state)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
