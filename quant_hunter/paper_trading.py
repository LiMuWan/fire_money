from __future__ import annotations

import csv
import json
from dataclasses import asdict, replace
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from .decision import DecisionEngine
from .models import (
    HoldingRecord,
    PaperEquityPoint,
    PaperOrderRecord,
    PaperPatrolLog,
    PaperPosition,
    PaperTradingState,
    RecommendationRow,
    ReportArtifacts,
)

_LOT_SIZE = 100
_STRATEGY_SCORE_FIELDS = (
    ("leader_model_score", "龙头模型"),
    ("main_force_score", "主力雷达"),
    ("board_attack_score", "擒龙打板"),
    ("value_recovery_score", "价值低吸"),
    ("dragon_decision_score", "掘龙决策"),
    ("one_day_hold_score", "一日持股法"),
)


def _unique_paper_report_paths(root: Path) -> tuple[Path, Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    markdown_path = root / f"paper_trading_report_{stamp}.md"
    csv_path = root / f"paper_trading_ledger_{stamp}.csv"
    json_path = root / f"paper_trading_snapshot_{stamp}.json"
    if not any(path.exists() for path in (markdown_path, csv_path, json_path)):
        return markdown_path, csv_path, json_path
    counter = 1
    while True:
        markdown_path = root / f"paper_trading_report_{stamp}_{counter}.md"
        csv_path = root / f"paper_trading_ledger_{stamp}_{counter}.csv"
        json_path = root / f"paper_trading_snapshot_{stamp}_{counter}.json"
        if not any(path.exists() for path in (markdown_path, csv_path, json_path)):
            return markdown_path, csv_path, json_path
        counter += 1


def _risk_profile_position_multiplier(risk_profile: str) -> float:
    normalized = str(risk_profile or "").strip().lower()
    if normalized == "conservative":
        return 0.82
    if normalized == "aggressive":
        return 1.12
    return 1.0


def _canonical_strategy_name(value: str) -> str:
    raw = str(value or "").strip()
    alias_map = {
        "龙头主线": "龙头模型",
        "资金承接": "主力雷达",
        "强势接力": "擒龙打板",
        "打板策略": "擒龙打板",
        "趋势低吸": "价值低吸",
        "一日持股": "一日持股法",
        "隔日强势": "一日持股法",
        "综合决策": "掘龙决策",
        "掘龙": "掘龙决策",
    }
    return alias_map.get(raw, raw)


def _normalize_auto_interval_minutes(value: float | int | None) -> float:
    try:
        interval = float(value or 5.0)
    except (TypeError, ValueError):
        interval = 5.0
    return round(min(max(interval, 0.5), 240.0), 2)


def _parse_run_timestamp(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _describe_hold_stats(durations: list[float]) -> dict[str, float | int]:
    if not durations:
        return {
            "sample_count": 0,
            "avg_hold_minutes": 0.0,
            "max_hold_minutes": 0.0,
            "min_hold_minutes": 0.0,
        }
    minutes = [duration / 60.0 for duration in durations]
    return {
        "sample_count": len(minutes),
        "avg_hold_minutes": round(sum(minutes) / len(minutes), 2),
        "max_hold_minutes": round(max(minutes), 2),
        "min_hold_minutes": round(min(minutes), 2),
    }


def _format_hold_cycle_note(sample_count: int, avg_days: float) -> str:
    if not sample_count:
        return "尚无完整持仓样本"
    return f"平均持有 {avg_days:.2f} 天 / 样本 {sample_count}"


def _collect_hold_cycle_stats(
    ledger: list[PaperOrderRecord],
) -> dict[str, float | int | list[dict[str, float | int | str]]]:
    open_buys: dict[str, list[dict[str, float | int | str]]] = defaultdict(list)
    total_durations: list[float] = []
    strategy_durations: dict[str, list[float]] = defaultdict(list)
    for record in ledger or []:
        symbol = str(getattr(record, "symbol", "") or "").strip()
        if not symbol:
            continue
        side = str(getattr(record, "side", "") or "").upper()
        timestamp = _parse_run_timestamp(getattr(record, "timestamp", ""))
        quantity = int(getattr(record, "quantity", 0) or 0)
        if quantity <= 0 or timestamp is None:
            continue
        canonical_strategy = _canonical_strategy_name(str(getattr(record, "strategy_name", "") or "").strip()) or "综合策略"
        if side == "BUY":
            open_buys[symbol].append(
                {
                    "quantity": quantity,
                    "timestamp": timestamp,
                    "strategy_name": canonical_strategy,
                }
            )
            continue
        if side not in {"SELL", "REDUCE"}:
            continue

        remaining = quantity
        while remaining > 0 and open_buys[symbol]:
            entry = open_buys[symbol][0]
            entry_qty = int(entry.get("quantity", 0) or 0)
            if entry_qty <= 0:
                open_buys[symbol].pop(0)
                continue
            used = min(entry_qty, remaining)
            entry_timestamp = entry.get("timestamp")
            if entry_timestamp is not None:
                delta = (timestamp - entry_timestamp).total_seconds()
                if delta >= 0:
                    total_durations.append(delta)
                    strategy_durations[entry.get("strategy_name", "综合策略")].append(delta)
            entry["quantity"] = entry_qty - used
            remaining -= used
            if entry["quantity"] <= 0:
                open_buys[symbol].pop(0)

    total_samples = len(total_durations)
    avg_hold_days = round((sum(total_durations) / total_samples) / 86400, 2) if total_samples else 0.0
    strategy_rows: list[dict[str, float | int | str]] = []
    for strategy_name, durations in strategy_durations.items():
        if not durations:
            continue
        samples = len(durations)
        avg_strategy_days = round((sum(durations) / samples) / 86400, 2)
        strategy_rows.append(
            {
                "strategy_name": strategy_name,
                "sample_count": samples,
                "avg_hold_days": avg_strategy_days,
                "hold_cycle_note": _format_hold_cycle_note(samples, avg_strategy_days),
            }
        )
    strategy_rows.sort(key=lambda item: (-int(item["sample_count"],), item["strategy_name"]))

    return {
        "total_samples": total_samples,
        "avg_hold_days": avg_hold_days,
        "hold_cycle_note": _format_hold_cycle_note(total_samples, avg_hold_days),
        "strategy_rows": strategy_rows,
    }


def _build_recent_experiment_summary(state: PaperTradingState) -> dict[str, object]:
    logs = list(getattr(state, "patrol_logs", []) or [])
    cycle_log = next((log for log in reversed(logs) if log.event_type == "CYCLE"), None)
    source_log = cycle_log or (logs[-1] if logs else None)
    return {
        "timestamp": source_log.timestamp if source_log else state.last_run_at or "",
        "summary": source_log.summary if source_log else state.last_strategy_note or "",
        "detail": source_log.detail if source_log else "",
        "equity": round(float(source_log.equity or state.total_equity or 0.0), 2) if source_log else round(float(state.total_equity or 0.0), 2),
        "total_return": round(float(source_log.total_return or state.total_return or 0.0), 2) if source_log else round(float(state.total_return or 0.0), 4),
        "position_count": int(source_log.position_count if source_log and source_log.position_count is not None else len(getattr(state, "positions", []) or [])),
        "is_cycle_log": bool(cycle_log),
    }


def describe_strategy_experiment(
    state: PaperTradingState,
    analytics: dict[str, object],
    rotation_rows: list[dict[str, float | int | str]],
) -> dict[str, object]:
    win_rate = float(analytics.get("win_rate", 0.0) or 0.0)
    avg_hold_days = float(analytics.get("avg_hold_days", 0.0) or 0.0)
    sample_count = int(analytics.get("hold_cycle_sample_count", 0) or 0)
    hold_note = str(analytics.get("hold_cycle_note", ""))
    if win_rate >= 0.55:
        risk_tier = "偏稳健"
        risk_brief = "胜率领先，策略表现可持续"
    elif win_rate >= 0.45:
        risk_tier = "中性"
        risk_brief = "继续验证主线与位置"
    else:
        risk_tier = "偏激进"
        risk_brief = "胜率偏低，注意窗口收敛"
    risk_summary = (
        f"{risk_tier} | 胜率 {win_rate:.1%} | 平均持仓 {avg_hold_days:.1f} 天 | 样本 {sample_count} | {risk_brief}"
    )
    if hold_note:
        risk_summary = f"{risk_summary} | {hold_note}"

    top_strategies: list[dict[str, object]] = []
    for entry in (rotation_rows or [])[:3]:
        top_strategies.append(
            {
                "strategy_name": str(entry.get("strategy_name", "")) or "暂无",
                "rotation_score": float(entry.get("rotation_score", 0.0) or 0.0),
                "bias_label": str(entry.get("bias_label", "") or "中性"),
                "hold_cycle_note": str(entry.get("hold_cycle_note", "")),
                "sample_count": int(entry.get("sample_count", 0) or 0),
                "avg_hold_days": float(entry.get("avg_hold_days", 0.0) or 0.0),
                "realized_pnl": float(entry.get("realized_pnl", 0.0) or 0.0),
            }
        )

    recent = _build_recent_experiment_summary(state)
    return {
        "risk_summary": risk_summary,
        "risk_tier": risk_tier,
        "top_strategies": top_strategies,
        "recent_experiment": recent,
        "win_rate": win_rate,
    }


def should_auto_run_paper_trading(
    state: PaperTradingState,
    *,
    now: datetime | None = None,
    in_session: bool = True,
) -> bool:
    if not getattr(state, "enabled", False) or not getattr(state, "auto_run", False) or not in_session:
        return False
    current_dt = now or datetime.now()
    last_run_dt = _parse_run_timestamp(getattr(state, "last_run_at", ""))
    if last_run_dt is None:
        return True
    interval_minutes = _normalize_auto_interval_minutes(getattr(state, "auto_interval_minutes", 5.0))
    return (current_dt - last_run_dt).total_seconds() >= interval_minutes * 60.0


def summarize_paper_trading_performance(state: PaperTradingState) -> dict[str, object]:
    ledger = list(getattr(state, "ledger", []) or [])
    realized_records = [
        item
        for item in ledger
        if str(getattr(item, "side", "") or "").upper() in {"SELL", "REDUCE"} and abs(float(getattr(item, "realized_pnl", 0.0) or 0.0)) > 0
    ]
    closed_trade_count = len(realized_records)
    win_count = sum(1 for item in realized_records if float(item.realized_pnl or 0.0) > 0)
    loss_count = sum(1 for item in realized_records if float(item.realized_pnl or 0.0) < 0)
    flat_count = max(closed_trade_count - win_count - loss_count, 0)
    realized_values = [float(item.realized_pnl or 0.0) for item in realized_records]
    strategy_map: dict[str, dict[str, float | int | str]] = {}

    for item in ledger:
        strategy_name = _canonical_strategy_name(str(getattr(item, "strategy_name", "") or "").strip()) or "未命名战法"
        bucket = strategy_map.setdefault(
            strategy_name,
            {
                "strategy_name": strategy_name,
                "buy_count": 0,
                "sell_count": 0,
                "win_count": 0,
                "loss_count": 0,
                "realized_pnl": 0.0,
                "avg_position_pct": 0.0,
                "position_pct_total": 0.0,
                "position_pct_samples": 0,
            },
        )
        side = str(getattr(item, "side", "") or "").upper()
        if side == "BUY":
            bucket["buy_count"] = int(bucket["buy_count"]) + 1
        elif side in {"SELL", "REDUCE"}:
            bucket["sell_count"] = int(bucket["sell_count"]) + 1
            pnl_value = float(getattr(item, "realized_pnl", 0.0) or 0.0)
            bucket["realized_pnl"] = float(bucket["realized_pnl"]) + pnl_value
            if pnl_value > 0:
                bucket["win_count"] = int(bucket["win_count"]) + 1
            elif pnl_value < 0:
                bucket["loss_count"] = int(bucket["loss_count"]) + 1
        position_pct = float(getattr(item, "position_pct", 0.0) or 0.0)
        if position_pct > 0:
            bucket["position_pct_total"] = float(bucket["position_pct_total"]) + position_pct
            bucket["position_pct_samples"] = int(bucket["position_pct_samples"]) + 1

    strategy_rows: list[dict[str, float | int | str]] = []
    for bucket in strategy_map.values():
        sample_count = int(bucket["position_pct_samples"])
        sell_count = int(bucket["sell_count"])
        win_rate = (int(bucket["win_count"]) / sell_count) if sell_count else 0.0
        avg_position_pct = (float(bucket["position_pct_total"]) / sample_count) if sample_count else 0.0
        strategy_rows.append(
            {
                "strategy_name": str(bucket["strategy_name"]),
                "buy_count": int(bucket["buy_count"]),
                "sell_count": sell_count,
                "win_count": int(bucket["win_count"]),
                "loss_count": int(bucket["loss_count"]),
                "win_rate": round(win_rate, 4),
                "realized_pnl": round(float(bucket["realized_pnl"]), 2),
                "avg_position_pct": round(avg_position_pct, 4),
            }
        )
    strategy_rows.sort(key=lambda item: (float(item["realized_pnl"]), int(item["buy_count"])), reverse=True)

    hold_cycle_stats = _collect_hold_cycle_stats(ledger)
    hold_map = {
        str(entry.get("strategy_name", "")): entry for entry in hold_cycle_stats.get("strategy_rows", []) or []
    }
    for row in strategy_rows:
        hold_entry = hold_map.get(row["strategy_name"])
        row["hold_sample_count"] = int(hold_entry.get("sample_count", 0)) if hold_entry else 0
        row["avg_hold_days"] = round(float(hold_entry.get("avg_hold_days", 0.0)) if hold_entry else 0.0, 2)
        row["hold_cycle_note"] = str(hold_entry.get("hold_cycle_note", "")) if hold_entry else ""

    return {
        "closed_trade_count": closed_trade_count,
        "win_count": win_count,
        "loss_count": loss_count,
        "flat_count": flat_count,
        "win_rate": round((win_count / closed_trade_count), 4) if closed_trade_count else 0.0,
        "avg_realized_pnl": round(sum(realized_values) / closed_trade_count, 2) if closed_trade_count else 0.0,
        "best_trade": round(max(realized_values), 2) if realized_values else 0.0,
        "worst_trade": round(min(realized_values), 2) if realized_values else 0.0,
        "strategy_rows": strategy_rows,
        "avg_hold_days": hold_cycle_stats["avg_hold_days"],
        "hold_cycle_note": hold_cycle_stats["hold_cycle_note"],
        "hold_cycle_sample_count": hold_cycle_stats["total_samples"],
        "hold_cycle": hold_cycle_stats,
    }


def build_strategy_rotation_snapshot(state: PaperTradingState) -> list[dict[str, float | int | str]]:
    analytics = summarize_paper_trading_performance(state)
    initial_cash = max(float(getattr(state, "initial_cash", 0.0) or 0.0), 1.0)
    rows: list[dict[str, float | int | str]] = []
    for item in list(analytics.get("strategy_rows", []) or []):
        strategy_name = _canonical_strategy_name(str(item.get("strategy_name", "") or "").strip()) or "未命名战法"
        buy_count = int(item.get("buy_count", 0) or 0)
        sell_count = int(item.get("sell_count", 0) or 0)
        sample_count = buy_count + sell_count
        realized_pnl = float(item.get("realized_pnl", 0.0) or 0.0)
        win_rate = float(item.get("win_rate", 0.0) or 0.0)
        hold_sample_count = int(item.get("hold_sample_count", 0) or 0)
        avg_hold_days = round(float(item.get("avg_hold_days", 0.0) or 0.0), 2)
        hold_cycle_note = str(item.get("hold_cycle_note", ""))
        sample_factor = min(sample_count / 6.0, 1.0)
        pnl_score = max(min(realized_pnl / max(initial_cash * 0.02, 1000.0), 1.0), -1.0)
        win_score = max(min((win_rate - 0.5) * 2.0, 1.0), -1.0) if sell_count else 0.0
        rotation_score = round((pnl_score * 0.55 + win_score * 0.45) * (0.35 + 0.65 * sample_factor), 4)
        if rotation_score >= 0.18:
            bias_label = "加权"
        elif rotation_score <= -0.18:
            bias_label = "降权"
        else:
            bias_label = "中性"
        rows.append(
            {
                "strategy_name": strategy_name,
                "sample_count": sample_count,
                "rotation_score": rotation_score,
                "budget_multiplier": round(min(max(1.0 + rotation_score * 0.6, 0.35), 1.45), 4),
                "bias_label": bias_label,
                "win_rate": round(win_rate, 4),
                "realized_pnl": round(realized_pnl, 2),
                "hold_sample_count": hold_sample_count,
                "avg_hold_days": avg_hold_days,
                "hold_cycle_note": hold_cycle_note,
            }
        )
    rows.sort(key=lambda item: (float(item["rotation_score"]), float(item["realized_pnl"])), reverse=True)
    return rows


class PaperTradingEngine:
    def initialize_state(
        self,
        *,
        initial_cash: float = 100000.0,
        max_position_pct: float = 0.25,
        auto_run: bool = False,
        auto_interval_minutes: float = 5.0,
    ) -> PaperTradingState:
        cash = round(max(float(initial_cash or 0.0), 0.0), 2)
        position_pct = min(max(float(max_position_pct or 0.25), 0.05), 1.0)
        auto_interval_minutes = _normalize_auto_interval_minutes(auto_interval_minutes)
        return PaperTradingState(
            enabled=True,
            auto_run=bool(auto_run),
            auto_interval_minutes=auto_interval_minutes,
            initial_cash=cash,
            cash=cash,
            max_position_pct=position_pct,
            equity_curve=[
                PaperEquityPoint(
                    timestamp="",
                    cash=cash,
                    market_value=0.0,
                    total_equity=cash,
                    realized_pnl=0.0,
                    total_return=0.0,
                    position_count=0,
                )
            ],
            total_equity=cash,
            total_return=0.0,
        )

    def infer_strategy_name(self, row: RecommendationRow | None) -> str:
        if row is None:
            return "掘龙决策"
        strategy_name = _canonical_strategy_name(str(getattr(row, "primary_strategy", "") or "").strip())
        if strategy_name:
            return strategy_name
        ranked = sorted(
            (
                (float(getattr(row, field_name, 0.0) or 0.0), label)
                for field_name, label in _STRATEGY_SCORE_FIELDS
            ),
            reverse=True,
        )
        return ranked[0][1] if ranked and ranked[0][0] > 0 else "掘龙决策"

    def run_cycle(
        self,
        state: PaperTradingState,
        recommendations: list[RecommendationRow],
        *,
        as_of: str | None = None,
        risk_profile: str = "standard",
        top_theme_limit: int = 3,
        max_total_exposure: float | None = None,
        theme_drop_reduce: bool = True,
    ) -> PaperTradingState:
        if not state.enabled:
            state = self.initialize_state(
                initial_cash=state.initial_cash,
                max_position_pct=state.max_position_pct,
                auto_run=state.auto_run,
                auto_interval_minutes=state.auto_interval_minutes,
            )

        timestamp = as_of or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        recommendation_map = {item.symbol: item for item in recommendations if getattr(item, "symbol", "")}
        positions = {
            item.symbol: replace(item)
            for item in state.positions
            if getattr(item, "symbol", "")
        }
        ledger = list(state.ledger)
        equity_curve = list(getattr(state, "equity_curve", []) or [])
        patrol_logs = list(getattr(state, "patrol_logs", []) or [])
        cash = round(float(state.cash or state.initial_cash or 0.0), 2)
        realized_pnl = round(float(state.realized_pnl or 0.0), 2)
        order_sequence = int(state.order_sequence or 0)
        sell_reason_samples: list[str] = []
        recently_sold_symbols: set[str] = set()
        blocked_rebuy_symbols: list[str] = []

        def note_blocked_rebuy(symbol: str, stock_name: str = "") -> None:
            name = stock_name or symbol
            if name and name not in blocked_rebuy_symbols:
                blocked_rebuy_symbols.append(name)

        def next_order_id() -> str:
            nonlocal order_sequence
            order_sequence += 1
            return f"SIM{order_sequence:05d}"

        def mark_positions() -> tuple[float, float]:
            market_value = 0.0
            for symbol, item in list(positions.items()):
                row = recommendation_map.get(symbol)
                current_price = float(
                    getattr(row, "close", 0.0)
                    or item.current_price
                    or item.avg_cost
                    or 0.0
                )
                market_amount = round(current_price * item.quantity, 2)
                unrealized = round((current_price - item.avg_cost) * item.quantity, 2)
                unrealized_pct = round((current_price - item.avg_cost) / item.avg_cost, 4) if item.avg_cost else 0.0
                positions[symbol] = replace(
                    item,
                    current_price=current_price,
                    market_value=market_amount,
                    unrealized_pnl=unrealized,
                    unrealized_pnl_pct=unrealized_pct,
                    available=item.quantity,
                )
                market_value += market_amount
            equity = round(cash + market_value, 2)
            return round(market_value, 2), equity

        def append_record(
            *,
            symbol: str,
            stock_id: str,
            stock_name: str,
            side: str,
            price: float,
            quantity: int,
            strategy_name: str,
            position_pct: float,
            signal_source: str,
            buy_point: str,
            sell_point: str,
            note: str,
            realized_amount: float = 0.0,
            realized_pct: float = 0.0,
        ) -> None:
            ledger.append(
                PaperOrderRecord(
                    order_id=next_order_id(),
                    timestamp=timestamp,
                    symbol=symbol,
                    stock_id=stock_id,
                    stock_name=stock_name,
                    side=side,
                    price=round(price, 3),
                    quantity=int(quantity),
                    amount=round(price * quantity, 2),
                    strategy_name=strategy_name,
                    position_pct=round(position_pct, 4),
                    signal_source=signal_source,
                    buy_point=buy_point,
                    sell_point=sell_point,
                    status="FILLED",
                    note=note,
                    realized_pnl=round(realized_amount, 2),
                    realized_pnl_pct=round(realized_pct, 4),
                    cumulative_realized_pnl=round(realized_pnl, 2),
                )
            )

        def append_patrol_log(
            event_type: str,
            summary: str,
            detail: str = "",
            *,
            equity_value: float | None = None,
            total_return_value: float | None = None,
            position_count_value: int | None = None,
        ) -> None:
            patrol_logs.append(
                PaperPatrolLog(
                    timestamp=timestamp,
                    event_type=event_type,
                    summary=summary,
                    detail=detail,
                    equity=round(float(total_equity if equity_value is None else equity_value), 2),
                    total_return=round(float(0.0 if total_return_value is None else total_return_value), 4),
                    position_count=int(len(positions) if position_count_value is None else position_count_value),
                )
            )

        def execute_sell(position: PaperPosition, quantity: int, price: float, note: str, row: RecommendationRow | None) -> bool:
            nonlocal cash, realized_pnl
            quantity = min(int(quantity), int(position.available), int(position.quantity))
            if quantity <= 0:
                return False
            amount = round(price * quantity, 2)
            realized_amount = round((price - position.avg_cost) * quantity, 2)
            realized_pct = round((price - position.avg_cost) / position.avg_cost, 4) if position.avg_cost else 0.0
            realized_pnl = round(realized_pnl + realized_amount, 2)
            cash = round(cash + amount, 2)
            remaining = int(position.quantity) - quantity
            if remaining > 0:
                positions[position.symbol] = replace(
                    position,
                    quantity=remaining,
                    available=remaining,
                )
            else:
                positions.pop(position.symbol, None)
            append_record(
                symbol=position.symbol,
                stock_id=position.stock_id,
                stock_name=position.stock_name,
                side="SELL" if remaining == 0 else "REDUCE",
                price=price,
                quantity=quantity,
                strategy_name=self.infer_strategy_name(row) if row is not None else position.strategy_name,
                position_pct=(amount / max(state.initial_cash, 1.0)),
                signal_source=(getattr(row, "label", "") if row is not None else "POSITION"),
                buy_point=position.buy_point,
                sell_point=(getattr(row, "sell_point", "") if row is not None else position.sell_point),
                note=note,
                realized_amount=realized_amount,
                realized_pct=realized_pct,
            )
            append_patrol_log(
                "SELL" if remaining == 0 else "REDUCE",
                f"{position.stock_name or position.symbol} {('清仓' if remaining == 0 else '减仓')} {quantity} 股",
                detail=note,
            )
            return True

        market_value, total_equity = mark_positions()
        current_holdings = [
            HoldingRecord(
                symbol=item.symbol,
                quantity=item.quantity,
                available=item.available,
                cost_price=item.avg_cost,
                market_value=item.market_value or round(item.current_price * item.quantity, 2),
            )
            for item in positions.values()
        ]
        strategy_budget_bias_by_name = {
            str(item.get("strategy_name", "") or ""): float(item.get("budget_multiplier", 1.0) or 1.0)
            for item in build_strategy_rotation_snapshot(state)
            if str(item.get("strategy_name", "") or "")
        }
        plan = DecisionEngine(risk_profile=risk_profile).build_plan(
            recommendations,
            current_holdings,
            cash,
            top_theme_limit=top_theme_limit,
            max_total_exposure=max_total_exposure,
            theme_drop_reduce=theme_drop_reduce,
            strategy_budget_bias_by_name=strategy_budget_bias_by_name,
        )
        advice_by_symbol = {item.symbol: item for item in plan.position_advice}

        sell_count = 0
        for symbol, position in list(positions.items()):
            row = recommendation_map.get(symbol)
            advice = advice_by_symbol.get(symbol)
            current_price = float(getattr(row, "close", 0.0) or position.current_price or position.avg_cost or 0.0)
            sell_quantity = 0
            note = ""

            if position.stop_price > 0 and current_price <= position.stop_price:
                sell_quantity = position.quantity
                note = f"AI 触发止损，价格回落到 {current_price:.2f}"
            elif position.target_price > 0 and current_price >= position.target_price:
                sell_quantity = position.quantity
                note = f"AI 触发止盈，价格抬升到 {current_price:.2f}"
            elif advice is not None and advice.action == "SELL":
                sell_quantity = position.quantity
                note = advice.rationale
            elif advice is not None and advice.action == "REDUCE":
                sell_quantity = (position.quantity // 2 // _LOT_SIZE) * _LOT_SIZE
                if sell_quantity <= 0 and position.quantity > 0:
                    sell_quantity = position.quantity if position.quantity < _LOT_SIZE else _LOT_SIZE
                note = advice.rationale

            if sell_quantity > 0 and execute_sell(position, sell_quantity, current_price, note, row):
                sell_count += 1
                recently_sold_symbols.add(position.symbol)
                if note:
                    sell_reason_samples.append(note)

        for symbol in recently_sold_symbols:
            row = recommendation_map.get(symbol)
            if row is not None and str(getattr(row, "action", "") or "").upper() == "BUY":
                note_blocked_rebuy(symbol, getattr(row, "stock_name", "") or symbol)

        market_value, total_equity = mark_positions()
        refreshed_holdings = [
            HoldingRecord(
                symbol=item.symbol,
                quantity=item.quantity,
                available=item.available,
                cost_price=item.avg_cost,
                market_value=item.market_value,
            )
            for item in positions.values()
        ]
        refreshed_plan = DecisionEngine(risk_profile=risk_profile).build_plan(
            recommendations,
            refreshed_holdings,
            cash,
            top_theme_limit=top_theme_limit,
            max_total_exposure=max_total_exposure,
            theme_drop_reduce=theme_drop_reduce,
            strategy_budget_bias_by_name=strategy_budget_bias_by_name,
        )

        buy_count = 0
        strategy_counter: dict[str, int] = {}
        for decision in refreshed_plan.decisions:
            if decision.symbol in positions:
                continue
            if decision.symbol in recently_sold_symbols:
                note_blocked_rebuy(decision.symbol, decision.stock_name or decision.symbol)
                continue
            row = recommendation_map.get(decision.symbol)
            price = float(decision.planned_entry or getattr(row, "entry_price", 0.0) or getattr(row, "close", 0.0) or 0.0)
            if price <= 0:
                continue
            market_value, total_equity = mark_positions()
            position_budget_cap = round(total_equity * state.max_position_pct * _risk_profile_position_multiplier(risk_profile), 2)
            exposure_limit = float(max_total_exposure or 1.0)
            remaining_exposure_budget = round(max(total_equity * exposure_limit - market_value, 0.0), 2)
            desired_budget = round(float(decision.suggested_budget or 0.0), 2)
            budget = min(
                cash,
                remaining_exposure_budget if remaining_exposure_budget > 0 else 0.0,
                position_budget_cap if position_budget_cap > 0 else cash,
                desired_budget if desired_budget > 0 else cash,
            )
            quantity = int(budget / price)
            quantity = (quantity // _LOT_SIZE) * _LOT_SIZE
            if quantity < _LOT_SIZE:
                continue

            amount = round(price * quantity, 2)
            cash = round(cash - amount, 2)
            current_price = float(getattr(row, "close", 0.0) or price)
            strategy_name = self.infer_strategy_name(row)
            positions[decision.symbol] = PaperPosition(
                symbol=decision.symbol,
                stock_id=decision.stock_id,
                stock_name=decision.stock_name,
                quantity=quantity,
                available=quantity,
                avg_cost=round(price, 3),
                current_price=round(current_price, 3),
                market_value=round(current_price * quantity, 2),
                entry_date=timestamp,
                strategy_name=strategy_name,
                buy_point=getattr(row, "buy_point", "") if row is not None else "",
                sell_point=getattr(row, "sell_point", "") if row is not None else "",
                stop_price=round(float(decision.planned_stop or getattr(row, "stop_price", 0.0) or 0.0), 3),
                target_price=round(float(decision.planned_target or getattr(row, "target_price", 0.0) or 0.0), 3),
                rationale=decision.rationale,
            )
            append_record(
                symbol=decision.symbol,
                stock_id=decision.stock_id,
                stock_name=decision.stock_name,
                side="BUY",
                price=price,
                quantity=quantity,
                strategy_name=strategy_name,
                position_pct=(amount / max(total_equity, 1.0)),
                signal_source=getattr(row, "label", "") if row is not None else "BUY",
                buy_point=getattr(row, "buy_point", "") if row is not None else "",
                sell_point=getattr(row, "sell_point", "") if row is not None else "",
                note=decision.rationale,
            )
            append_patrol_log(
                "BUY",
                f"{decision.stock_name or decision.symbol} 开仓 {quantity} 股",
                detail=f"{strategy_name} | {decision.rationale}",
            )
            strategy_counter[strategy_name] = strategy_counter.get(strategy_name, 0) + 1
            buy_count += 1

        market_value, total_equity = mark_positions()
        total_return = round((total_equity - state.initial_cash) / state.initial_cash, 4) if state.initial_cash else 0.0
        latest_point = PaperEquityPoint(
            timestamp=timestamp,
            cash=round(cash, 2),
            market_value=round(market_value, 2),
            total_equity=round(total_equity, 2),
            realized_pnl=round(realized_pnl, 2),
            total_return=round(total_return, 4),
            position_count=len(positions),
        )
        if not equity_curve or equity_curve[-1] != latest_point:
            equity_curve.append(latest_point)
        latest_strategies = " / ".join(f"{name} {count}" for name, count in sorted(strategy_counter.items(), key=lambda item: item[1], reverse=True))
        strategy_note_parts = [
            f"本轮实验：卖出 {sell_count} 笔，新开 {buy_count} 笔",
            f"账户：现金 {cash:,.0f} | 权益 {total_equity:,.0f}",
        ]
        if latest_strategies:
            strategy_note_parts.append(f"策略分布：{latest_strategies}")
        if sell_reason_samples:
            strategy_note_parts.append(f"卖出原因：{sell_reason_samples[0]}")
        if blocked_rebuy_symbols:
            strategy_note_parts.append(f"暂缓回补：{' / '.join(blocked_rebuy_symbols[:2])}")
        if not buy_count and not sell_count:
            strategy_note_parts.append("本轮没有触发新的模拟成交，继续观察。")

        cycle_note = " | ".join(strategy_note_parts)
        append_patrol_log(
            "CYCLE",
            f"巡航完成：卖出 {sell_count} 笔 | 新开 {buy_count} 笔",
            detail=cycle_note,
            equity_value=total_equity,
            total_return_value=total_return,
            position_count_value=len(positions),
        )

        return PaperTradingState(
            enabled=True,
            auto_run=state.auto_run,
            auto_interval_minutes=_normalize_auto_interval_minutes(state.auto_interval_minutes),
            initial_cash=round(state.initial_cash, 2),
            cash=round(cash, 2),
            max_position_pct=state.max_position_pct,
            positions=sorted(positions.values(), key=lambda item: item.market_value, reverse=True),
            ledger=ledger[-500:],
            equity_curve=equity_curve[-500:],
            patrol_logs=patrol_logs[-500:],
            realized_pnl=round(realized_pnl, 2),
            total_equity=round(total_equity, 2),
            total_return=round(total_return, 4),
            last_run_at=timestamp,
            last_strategy_note=cycle_note,
            order_sequence=order_sequence,
        )


def export_paper_trading_report(
    state: PaperTradingState,
    *,
    output_dir: str | Path,
    exported_at: str | None = None,
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    exported_at = exported_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    markdown_path, csv_path, json_path = _unique_paper_report_paths(root)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "order_id",
                "timestamp",
                "symbol",
                "stock_id",
                "stock_name",
                "side",
                "price",
                "quantity",
                "amount",
                "strategy_name",
                "position_pct",
                "signal_source",
                "buy_point",
                "sell_point",
                "status",
                "note",
                "realized_pnl",
                "realized_pnl_pct",
                "cumulative_realized_pnl",
            ]
        )
        for item in state.ledger:
            writer.writerow(
                [
                    item.order_id,
                    item.timestamp,
                    item.symbol,
                    item.stock_id,
                    item.stock_name,
                    item.side,
                    f"{item.price:.3f}",
                    item.quantity,
                    f"{item.amount:.2f}",
                    item.strategy_name,
                    f"{item.position_pct:.4f}",
                    item.signal_source,
                    item.buy_point,
                    item.sell_point,
                    item.status,
                    item.note,
                    f"{item.realized_pnl:.2f}",
                    f"{item.realized_pnl_pct:.4f}",
                    f"{item.cumulative_realized_pnl:.2f}",
                ]
            )

    analytics = summarize_paper_trading_performance(state)
    recent_experiment = _build_recent_experiment_summary(state)
    payload = {
        "exported_at": exported_at,
        "paper_trading_state": asdict(state),
        "analytics": analytics,
        "recent_experiment": recent_experiment,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    equity_lines = [
        f"- {point.timestamp or '初始'} | 现金 {point.cash:,.0f} | 市值 {point.market_value:,.0f} | 权益 {point.total_equity:,.0f} | 收益率 {point.total_return:.2%}"
        for point in state.equity_curve[-8:]
    ] or ["- 暂无权益轨迹"]
    position_lines = [
        f"- {item.stock_name or item.symbol} ({item.symbol}) | 战法 {item.strategy_name or '--'} | 数量 {item.quantity} | 成本 {item.avg_cost:.2f} | 现价 {item.current_price:.2f} | 浮盈 {item.unrealized_pnl:,.0f}"
        for item in state.positions
    ] or ["- 当前无模拟持仓"]
    ledger_lines = [
        f"- {item.timestamp} | {item.side} {item.stock_name or item.symbol} {item.quantity} 股 @ {item.price:.2f} | 已实现 {item.realized_pnl:,.0f} | {item.note or item.signal_source}"
        for item in state.ledger[-10:]
    ] or ["- 当前无模拟成交记录"]

    strategy_lines = [
        f"- {item['strategy_name']} | 开仓 {item['buy_count']} | 卖出 {item['sell_count']} | 胜率 {float(item['win_rate']):.2%} | 已实现 {float(item['realized_pnl']):,.0f} | 持有 {float(item.get('avg_hold_days', 0.0) or 0.0):.2f} 天"
        for item in list(analytics.get("strategy_rows", []) or [])[:8]
    ] or ["- 当前还没有形成战法收益拆解"]
    patrol_lines = [
        f"- {item.timestamp} | {item.event_type or 'CYCLE'} | {item.summary} | 权益 {float(item.equity or 0.0):,.0f} | 收益率 {float(item.total_return or 0.0):.2%}"
        for item in list(getattr(state, "patrol_logs", []) or [])[-12:]
    ] or ["- 当前还没有巡航日志"]

    markdown = "\n".join(
        [
            "# AI 模拟盘报告",
            "",
            f"- 导出时间：{exported_at}",
            f"- 初始资金：{state.initial_cash:,.2f}",
            f"- 可用资金：{state.cash:,.2f}",
            f"- 总权益：{state.total_equity:,.2f}",
            f"- 累计已实现盈亏：{state.realized_pnl:,.2f}",
            f"- 累计收益率：{state.total_return:.2%}",
            f"- 平均持有周期：{float(analytics.get('avg_hold_days', 0.0) or 0.0):.2f} 天 | 样本 {int(analytics.get('hold_cycle_sample_count', 0) or 0)}",
            f"- 当前持仓：{len(state.positions)} 只",
            f"- 累计交割单：{len(state.ledger)} 笔",
            f"- 最新摘要：{state.last_strategy_note or '暂无'}",
            f"- 最近实验：{recent_experiment.get('summary', '') or '暂无'}",
            "",
            "## 当前持仓",
            *position_lines,
            "",
            "## 最近交割单",
            *ledger_lines,
            "",
            "## 权益曲线",
            *equity_lines,
        ]
    )
    markdown = "\n".join(
        [
            markdown,
            "",
            "## 战法拆解",
            f"- 闭环单数：{int(analytics.get('closed_trade_count', 0) or 0)}",
            f"- 胜率：{float(analytics.get('win_rate', 0.0) or 0.0):.2%}",
            f"- 平均单笔已实现：{float(analytics.get('avg_realized_pnl', 0.0) or 0.0):,.2f}",
            f"- 最佳单笔：{float(analytics.get('best_trade', 0.0) or 0.0):,.2f}",
            f"- 最差单笔：{float(analytics.get('worst_trade', 0.0) or 0.0):,.2f}",
            *strategy_lines,
            "",
            "## 巡航日志",
            *patrol_lines,
        ]
    )
    markdown_path.write_text(markdown, encoding="utf-8")

    return ReportArtifacts(
        markdown_path=str(markdown_path),
        csv_path=str(csv_path),
        json_path=str(json_path),
    )
