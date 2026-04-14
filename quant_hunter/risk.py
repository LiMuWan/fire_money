from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskControls:
    backtest_min_entry_risk_reward_ratio: float = 1.2
    plan_min_risk_reward_ratio: float = 1.2
    recommendation_min_risk_reward_ratio: float = 1.35
    execution_low_risk_reward_ratio: float = 1.35
    max_plan_stop_loss_pct: float = 0.08
    warn_total_loss_ratio: float = 0.02
    block_total_loss_ratio: float = 0.04
    warn_single_loss_ratio: float = 0.012
    block_single_loss_ratio: float = 0.02
    warn_single_position_asset_ratio: float = 0.25
    block_single_position_asset_ratio: float = 0.35
    warn_single_position_cash_ratio: float = 0.5
    block_single_position_cash_ratio: float = 0.7


RISK_PROFILE_STANDARD = "standard"
RISK_PROFILE_CONSERVATIVE = "conservative"
RISK_PROFILE_AGGRESSIVE = "aggressive"

RISK_PROFILE_LABELS: dict[str, str] = {
    RISK_PROFILE_CONSERVATIVE: "\u4fdd\u5b88",
    RISK_PROFILE_STANDARD: "\u6807\u51c6",
    RISK_PROFILE_AGGRESSIVE: "\u6fc0\u8fdb",
}

RISK_PROFILE_BRIEFS: dict[str, str] = {
    RISK_PROFILE_CONSERVATIVE: "\u66f4\u9ad8\u76c8\u4e8f\u6bd4\u3001\u66f4\u7d27\u6b62\u635f\u3001\u66f4\u4f4e\u96c6\u4e2d\u5ea6",
    RISK_PROFILE_STANDARD: "\u76c8\u4e8f\u6bd4\u4e0e\u4ed3\u4f4d\u98ce\u9669\u5747\u8861",
    RISK_PROFILE_AGGRESSIVE: "\u9002\u5ea6\u653e\u5bbd\u95e8\u69db\uff0c\u4f46\u4fdd\u7559\u57fa\u7840\u98ce\u63a7",
}

RISK_PROFILE_PRESETS: dict[str, RiskControls] = {
    RISK_PROFILE_CONSERVATIVE: RiskControls(
        backtest_min_entry_risk_reward_ratio=1.35,
        plan_min_risk_reward_ratio=1.35,
        recommendation_min_risk_reward_ratio=1.55,
        execution_low_risk_reward_ratio=1.55,
        max_plan_stop_loss_pct=0.06,
        warn_total_loss_ratio=0.015,
        block_total_loss_ratio=0.03,
        warn_single_loss_ratio=0.008,
        block_single_loss_ratio=0.015,
        warn_single_position_asset_ratio=0.18,
        block_single_position_asset_ratio=0.28,
        warn_single_position_cash_ratio=0.35,
        block_single_position_cash_ratio=0.55,
    ),
    RISK_PROFILE_STANDARD: RiskControls(),
    RISK_PROFILE_AGGRESSIVE: RiskControls(
        backtest_min_entry_risk_reward_ratio=1.05,
        plan_min_risk_reward_ratio=1.05,
        recommendation_min_risk_reward_ratio=1.2,
        execution_low_risk_reward_ratio=1.2,
        max_plan_stop_loss_pct=0.1,
        warn_total_loss_ratio=0.03,
        block_total_loss_ratio=0.055,
        warn_single_loss_ratio=0.016,
        block_single_loss_ratio=0.028,
        warn_single_position_asset_ratio=0.32,
        block_single_position_asset_ratio=0.42,
        warn_single_position_cash_ratio=0.6,
        block_single_position_cash_ratio=0.78,
    ),
}


def normalize_risk_profile(value: str | None) -> str:
    key = str(value or "").strip().lower()
    if key in {"", "default", "balanced"}:
        return RISK_PROFILE_STANDARD
    if key in {"conservative", "safe", "\u7a33\u5065", "\u4fdd\u5b88"}:
        return RISK_PROFILE_CONSERVATIVE
    if key in {"aggressive", "active", "\u8fdb\u53d6", "\u6fc0\u8fdb"}:
        return RISK_PROFILE_AGGRESSIVE
    return RISK_PROFILE_STANDARD


def resolve_risk_controls(profile: str | None) -> RiskControls:
    normalized = normalize_risk_profile(profile)
    return RISK_PROFILE_PRESETS[normalized]


def risk_profile_brief(profile: str | None) -> str:
    normalized = normalize_risk_profile(profile)
    return RISK_PROFILE_BRIEFS[normalized]


def risk_profile_comparison_text() -> str:
    parts = []
    for key in (RISK_PROFILE_CONSERVATIVE, RISK_PROFILE_STANDARD, RISK_PROFILE_AGGRESSIVE):
        parts.append(f"{RISK_PROFILE_LABELS[key]}={RISK_PROFILE_BRIEFS[key]}")
    return "\uff1b".join(parts)


def risk_pool_impact_text(meta: dict[str, object] | None) -> str:
    payload = dict(meta or {})
    display_count = int(payload.get("display_count", 0) or 0)
    buy_ready_count = int(payload.get("buy_ready_count", 0) or 0)
    rejected_count = int(payload.get("rejected_count", 0) or 0)
    if not payload:
        return "\u63a8\u8350\u7edf\u8ba1\u5f85\u751f\u6210"
    return (
        f"\u63a8\u8350 {display_count} \u53ea | "
        f"\u53ef\u6267\u884c {buy_ready_count} \u53ea | "
        f"\u62e6\u622a {rejected_count} \u53ea"
    )


DEFAULT_RISK_CONTROLS = resolve_risk_controls(RISK_PROFILE_STANDARD)
