from __future__ import annotations

from dataclasses import dataclass

from .models import DailyAnalysis, RecommendationRow, Trade


@dataclass(frozen=True)
class StrategyPlanLevels:
    source: str
    signal_date: str
    entry_price: float | None = None
    stop_price: float | None = None
    target_price: float | None = None
    label: str = ""
    reason: str = ""


@dataclass(frozen=True)
class StrategyTradeMarker:
    kind: str
    date: str
    price: float
    label: str
    detail: str
    tone: str = "neutral"
    pnl_pct: float | None = None
    exit_reason: str = ""
    entry_date: str = ""


def _normalize_price(value: float | None) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _analysis_has_plan_prices(item: DailyAnalysis | None) -> bool:
    if item is None:
        return False
    return any(
        price is not None
        for price in (
            _normalize_price(item.entry_price),
            _normalize_price(item.stop_price),
            _normalize_price(item.target_price),
        )
    )


def build_strategy_plan_levels(
    recommendation: RecommendationRow | None = None,
    analyses: list[DailyAnalysis] | None = None,
    *,
    selected_signal_date: str = "",
) -> StrategyPlanLevels | None:
    signal_date = str(selected_signal_date or "").strip()
    items = list(analyses or [])
    if signal_date:
        selected_signal = next(
            (item for item in items if item.date == signal_date and _analysis_has_plan_prices(item)),
            None,
        )
        if selected_signal is not None:
            return StrategyPlanLevels(
                source="selected_signal",
                signal_date=selected_signal.date,
                entry_price=_normalize_price(selected_signal.entry_price),
                stop_price=_normalize_price(selected_signal.stop_price),
                target_price=_normalize_price(selected_signal.target_price),
                label=selected_signal.label,
                reason=selected_signal.reason,
            )

    if recommendation is not None:
        entry_price = _normalize_price(getattr(recommendation, "entry_price", None))
        if entry_price is None:
            entry_price = _normalize_price(getattr(recommendation, "close", None))
        stop_price = _normalize_price(getattr(recommendation, "stop_price", None))
        target_price = _normalize_price(getattr(recommendation, "target_price", None))
        if any(price is not None for price in (entry_price, stop_price, target_price)):
            return StrategyPlanLevels(
                source="recommendation",
                signal_date=str(getattr(recommendation, "signal_date", "") or ""),
                entry_price=entry_price,
                stop_price=stop_price,
                target_price=target_price,
                label=str(getattr(recommendation, "label", "") or ""),
                reason=str(getattr(recommendation, "rationale", "") or getattr(recommendation, "next_focus", "") or ""),
            )

    latest_signal = next((item for item in reversed(items) if _analysis_has_plan_prices(item)), None)
    if latest_signal is None:
        return None
    return StrategyPlanLevels(
        source="latest_signal",
        signal_date=latest_signal.date,
        entry_price=_normalize_price(latest_signal.entry_price),
        stop_price=_normalize_price(latest_signal.stop_price),
        target_price=_normalize_price(latest_signal.target_price),
        label=latest_signal.label,
        reason=latest_signal.reason,
    )


def classify_trade_exit_reason(exit_reason: str) -> str:
    text = str(exit_reason or "").strip().lower()
    risk_tokens = ("\u6b62\u635f", "\u8dcc\u7834", "\u5931\u5b88", "\u9677\u9631", "stop", "risk", "down")
    profit_tokens = ("\u6b62\u76c8", "\u76ee\u6807", "\u83b7\u5229", "profit", "target", "gain")
    if any(token in text for token in risk_tokens):
        return "risk"
    if any(token in text for token in profit_tokens):
        return "profit"
    return "neutral"


def summarize_exit_reason_for_label(exit_reason: str, tone: str) -> str:
    text = str(exit_reason or "").strip()
    lowered = text.lower()
    if tone == "profit":
        if "\u76ee\u6807" in text or "target" in lowered:
            return "\u76ee\u6807\u5151\u73b0"
        if "\u6b62\u76c8" in text or "\u83b7\u5229" in text:
            return "\u6b62\u76c8"
        return "\u76c8\u5229\u4e86\u7ed3"
    if tone == "risk":
        if "\u8dcc\u7834" in text or "down" in lowered:
            return "\u8dcc\u7834\u6b62\u635f"
        if "\u5931\u5b88" in text:
            return "\u5931\u5b88\u79bb\u573a"
        if "\u9677\u9631" in text:
            return "\u9677\u9631\u79bb\u573a"
        return "\u6b62\u635f"
    if "\u6837\u672c\u7ed3\u675f" in text or "\u7ed3\u675f" in text:
        return "\u5230\u671f\u5e73\u4ed3"
    if "\u6301\u6709" in text or "\u8d85\u8fc7" in text:
        return "\u65f6\u9650\u79bb\u573a"
    if text:
        return text[:8]
    return "\u5356\u51fa"


def build_trade_marker_chart_label(marker: StrategyTradeMarker) -> str:
    if marker.kind != "exit":
        return ""
    reason_text = summarize_exit_reason_for_label(marker.exit_reason, marker.tone)
    if marker.pnl_pct is None:
        return reason_text
    return f"{reason_text} {marker.pnl_pct:+.1%}"


def build_trade_marker_label_tone(marker: StrategyTradeMarker) -> str:
    if marker.kind != "exit":
        return str(marker.tone or "neutral")
    pnl_pct = float(marker.pnl_pct or 0.0)
    if marker.tone == "profit":
        if pnl_pct >= 0.12:
            return "profit_strong"
        if pnl_pct >= 0.04:
            return "profit"
        return "profit_soft"
    if marker.tone == "risk":
        if pnl_pct <= -0.08:
            return "risk_hard"
        if pnl_pct <= -0.03:
            return "risk"
        return "risk_soft"
    if pnl_pct >= 0.02:
        return "neutral_up"
    if pnl_pct <= -0.02:
        return "neutral_down"
    return "neutral"


def build_trade_markers(trades: list[Trade] | None = None) -> list[StrategyTradeMarker]:
    markers: list[StrategyTradeMarker] = []
    for trade in list(trades or []):
        entry_date = str(getattr(trade, "entry_date", "") or "").strip()
        exit_date = str(getattr(trade, "exit_date", "") or "").strip()
        entry_price = _normalize_price(getattr(trade, "entry_price", None))
        exit_price = _normalize_price(getattr(trade, "exit_price", None))
        shares = int(getattr(trade, "shares", 0) or 0)
        pnl_pct = float(getattr(trade, "pnl_pct", 0.0) or 0.0)
        exit_reason = str(getattr(trade, "exit_reason", "") or "").strip()

        if entry_date and entry_price is not None:
            detail = f"\u56de\u6d4b\u4e70\u5165 {entry_price:.2f}"
            if shares > 0:
                detail = f"{detail} | {shares} \u80a1"
            markers.append(
                StrategyTradeMarker(
                    kind="entry",
                    date=entry_date,
                    price=entry_price,
                    label="\u56de\u6d4b\u4e70\u70b9",
                    detail=detail,
                    tone="buy",
                    pnl_pct=None,
                    exit_reason="",
                    entry_date=entry_date,
                )
            )

        if exit_date and exit_price is not None:
            markers.append(
                StrategyTradeMarker(
                    kind="exit",
                    date=exit_date,
                    price=exit_price,
                    label="\u56de\u6d4b\u5356\u70b9",
                    detail=f"{exit_reason or '\u56de\u6d4b\u5356\u51fa'} | {pnl_pct:+.2%}",
                    tone=classify_trade_exit_reason(exit_reason),
                    pnl_pct=pnl_pct,
                    exit_reason=exit_reason,
                    entry_date=entry_date,
                )
            )
    return markers
