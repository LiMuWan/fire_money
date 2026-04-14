from __future__ import annotations

from .broker import summarize_execution_statuses


def execution_status_for_symbol(execution_status_by_symbol: dict[str, str], symbol: str) -> str:
    return execution_status_by_symbol.get(symbol, "待观察")


def recommend_execution_summary(plan, execution_status_by_symbol: dict[str, str]) -> dict[str, int]:
    symbols = [item.symbol for item in getattr(plan, "decisions", [])]
    return summarize_execution_statuses(symbols, execution_status_by_symbol)


def execution_summary_for_rows(rows: list, execution_status_by_symbol: dict[str, str]) -> dict[str, int]:
    symbols = [item.symbol for item in rows]
    return summarize_execution_statuses(symbols, execution_status_by_symbol)
