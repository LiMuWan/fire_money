from __future__ import annotations

from .broker import summarize_broker_execution


def build_broker_execution_summary(
    *,
    profile,
    adapter,
    order_intents,
    holdings,
    cash_snapshot,
    recommendations=None,
    env: dict[str, object] | None = None,
) -> tuple[dict[str, object], dict[str, object]]:
    environment = env if env is not None else adapter.diagnose_environment(profile)
    summary = summarize_broker_execution(
        profile=profile,
        env=environment,
        order_intents=order_intents,
        holdings=holdings,
        cash_snapshot=cash_snapshot,
        recommendations=recommendations,
    )
    return summary, environment
