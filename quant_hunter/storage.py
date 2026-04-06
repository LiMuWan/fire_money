from __future__ import annotations

import json
from datetime import date
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .models import BrokerProfile


@dataclass
class AppState:
    universe_dir: str = ""
    selected_symbol: str = ""
    watchlist: list[str] = field(default_factory=list)
    ui_theme: str = "sunrise"
    theme_alias_path: str = ""
    recommend_theme_filter: str = "全部"
    market_theme_filter: str = "全部"
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
    broker_profile: BrokerProfile = field(default_factory=BrokerProfile)


def load_app_state(path: str | Path) -> AppState:
    file_path = Path(path)
    if not file_path.exists():
        return AppState()
    data = json.loads(file_path.read_text(encoding="utf-8"))
    broker_data = data.get("broker_profile", {})
    return AppState(
        universe_dir=data.get("universe_dir", ""),
        selected_symbol=data.get("selected_symbol", ""),
        watchlist=list(data.get("watchlist", [])),
        ui_theme=data.get("ui_theme", "sunrise"),
        theme_alias_path=data.get("theme_alias_path", ""),
        recommend_theme_filter=data.get("recommend_theme_filter", "全部"),
        market_theme_filter=data.get("market_theme_filter", "全部"),
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
        broker_profile=BrokerProfile(
            account_name=broker_data.get("account_name", "东方财富账户"),
            account_id=broker_data.get("account_id", ""),
            mode=broker_data.get("mode", "export"),
            export_dir=broker_data.get("export_dir", ""),
            sdk_module=broker_data.get("sdk_module", "gm.api"),
            sdk_python_path=broker_data.get("sdk_python_path", ""),
            token=broker_data.get("token", ""),
            strategy_id=broker_data.get("strategy_id", ""),
            username=broker_data.get("username", ""),
            password=broker_data.get("password", ""),
            auth_channel=broker_data.get("auth_channel", "eastmoney"),
        ),
    )


def save_app_state(path: str | Path, state: AppState) -> None:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(state)
    file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
