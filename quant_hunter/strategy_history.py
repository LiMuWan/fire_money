from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .data import extract_stock_id, normalize_symbol
from .market_feed import EastmoneyMarketFeed
from .models import (
    PriceBar,
    StrategyHistoryEquityPoint,
    StrategyHistoryPeriodStat,
    StrategyHistoryReport,
    StrategyHistoryScenarioComparison,
    StrategyHistoryScenarioLeaderboard,
    StrategyHistorySignal,
    StrategyHistorySummary,
    StrategyHistoryTrade,
)


@dataclass(frozen=True)
class StrategyHistoryReplayParams:
    start_date: str = "2021-01-01"
    end_date: str = "2099-12-31"
    max_hold_days: int = 8
    fallback_stop_pct: float = 0.05
    fallback_target_pct: float = 0.08
    slippage_rate: float = 0.0005
    commission_rate: float = 0.0003
    stamp_duty_rate: float = 0.001
    include_watch_only: bool = False
    block_limit_up_entry: bool = True
    block_limit_down_exit: bool = True


@dataclass(frozen=True)
class StrategyHistoryScenarioPreset:
    label: str
    note: str
    params: StrategyHistoryReplayParams


class StrategyHistoryReplayer:
    def __init__(
        self,
        market_feed: EastmoneyMarketFeed | None = None,
        params: StrategyHistoryReplayParams | None = None,
    ) -> None:
        self.market_feed = market_feed or EastmoneyMarketFeed()
        self.params = params or StrategyHistoryReplayParams()

    def build_report(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        roots: list[str | Path] | None = None,
        include_watch_only: bool | None = None,
    ) -> StrategyHistoryReport:
        params = self._resolved_params(
            start_date=start_date,
            end_date=end_date,
            include_watch_only=include_watch_only,
        )
        source_files = self._discover_source_files(roots=roots)
        signals = self._load_signals(source_files, params)
        trades, notes = self._replay_signals(signals, params)
        summaries = self._build_summaries(signals, trades, notes)
        equity_points = self._build_equity_points(trades)
        yearly_stats = self._build_period_stats(trades, period="year")
        monthly_stats = self._build_period_stats(trades, period="month")
        return StrategyHistoryReport(
            start_date=params.start_date,
            end_date=params.end_date,
            source_files=[str(path) for path in source_files],
            signals=signals,
            trades=trades,
            summaries=summaries,
            equity_points=equity_points,
            yearly_stats=yearly_stats,
            monthly_stats=monthly_stats,
            notes=notes,
        )

    def compare_parameter_scenarios(
        self,
        scenarios: list[StrategyHistoryScenarioPreset] | None = None,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        roots: list[str | Path] | None = None,
        include_watch_only: bool | None = None,
    ) -> list[StrategyHistoryScenarioComparison]:
        base_params = self._resolved_params(
            start_date=start_date,
            end_date=end_date,
            include_watch_only=include_watch_only,
        )
        source_files = self._discover_source_files(roots=roots)
        scenario_rows = scenarios or self.default_comparison_scenarios(base_params)
        rows: list[StrategyHistoryScenarioComparison] = []
        for scenario in scenario_rows:
            scenario_params = StrategyHistoryReplayParams(
                start_date=base_params.start_date,
                end_date=base_params.end_date,
                max_hold_days=scenario.params.max_hold_days,
                fallback_stop_pct=scenario.params.fallback_stop_pct,
                fallback_target_pct=scenario.params.fallback_target_pct,
                slippage_rate=scenario.params.slippage_rate,
                commission_rate=scenario.params.commission_rate,
                stamp_duty_rate=scenario.params.stamp_duty_rate,
                include_watch_only=scenario.params.include_watch_only,
                block_limit_up_entry=scenario.params.block_limit_up_entry,
                block_limit_down_exit=scenario.params.block_limit_down_exit,
            )
            signals = self._load_signals(source_files, scenario_params)
            trades, notes = self._replay_signals(signals, scenario_params)
            summaries = self._build_summaries(signals, trades, notes)
            for summary in summaries:
                rows.append(
                    StrategyHistoryScenarioComparison(
                        scenario_label=scenario.label,
                        scenario_note=scenario.note,
                        strategy_name=summary.strategy_name,
                        max_hold_days=scenario_params.max_hold_days,
                        slippage_rate=scenario_params.slippage_rate,
                        commission_rate=scenario_params.commission_rate,
                        stamp_duty_rate=scenario_params.stamp_duty_rate,
                        block_limit_up_entry=scenario_params.block_limit_up_entry,
                        block_limit_down_exit=scenario_params.block_limit_down_exit,
                        signal_count=summary.signal_count,
                        trade_count=summary.trade_count,
                        filled_ratio=summary.filled_ratio,
                        total_return=summary.total_return,
                        win_rate=summary.win_rate,
                        max_drawdown=summary.max_drawdown,
                        profit_factor=summary.profit_factor,
                        payoff_ratio=summary.payoff_ratio,
                        avg_hold_days=summary.avg_hold_days,
                        max_consecutive_losses=summary.max_consecutive_losses,
                    )
                )
        rows.sort(key=lambda item: (item.strategy_name, item.scenario_label, -float(item.total_return)))
        return rows

    def _resolved_params(
        self,
        *,
        start_date: str | None,
        end_date: str | None,
        include_watch_only: bool | None,
    ) -> StrategyHistoryReplayParams:
        return StrategyHistoryReplayParams(
            start_date=start_date or self.params.start_date,
            end_date=end_date or self.params.end_date,
            max_hold_days=self.params.max_hold_days,
            fallback_stop_pct=self.params.fallback_stop_pct,
            fallback_target_pct=self.params.fallback_target_pct,
            slippage_rate=self.params.slippage_rate,
            commission_rate=self.params.commission_rate,
            stamp_duty_rate=self.params.stamp_duty_rate,
            include_watch_only=self.params.include_watch_only if include_watch_only is None else include_watch_only,
            block_limit_up_entry=self.params.block_limit_up_entry,
            block_limit_down_exit=self.params.block_limit_down_exit,
        )

    def _discover_source_files(self, *, roots: list[str | Path] | None) -> list[Path]:
        search_roots = [Path(item) for item in roots] if roots else []
        if not search_roots:
            project_root = Path(__file__).resolve().parents[1]
            search_roots = [
                project_root / "exports" / "review_reports",
                project_root / "exports" / "daily_plans",
                project_root / "reports",
                project_root / "reports" / "daily_plans",
            ]
        files: list[Path] = []
        for root in search_roots:
            if root.is_file() and root.suffix.lower() == ".json":
                files.append(root)
                continue
            if not root.exists() or not root.is_dir():
                continue
            files.extend(sorted(root.glob("end_of_day_review_*.json")))
            files.extend(sorted(root.glob("daily_plan_*.json")))
        unique: dict[str, Path] = {}
        for path in files:
            unique[str(path.resolve())] = path
        return sorted(unique.values(), key=lambda item: item.name)

    def _load_signals(
        self,
        source_files: list[Path],
        params: StrategyHistoryReplayParams,
    ) -> list[StrategyHistorySignal]:
        signals: list[StrategyHistorySignal] = []
        for path in source_files:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            source_kind = "daily_plan" if path.name.startswith("daily_plan_") else "end_of_day_review"
            signals.extend(self._signals_from_payload(payload, path, source_kind, params))
        signals.sort(key=lambda item: (item.signal_date, item.generated_at, item.strategy_name, item.symbol, item.source_file))
        deduped: list[StrategyHistorySignal] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for item in signals:
            key = (item.signal_date, item.symbol, item.strategy_name, item.action, item.source_file)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    def _signals_from_payload(
        self,
        payload: dict[str, Any],
        path: Path,
        source_kind: str,
        params: StrategyHistoryReplayParams,
    ) -> list[StrategyHistorySignal]:
        generated_at = str(payload.get("generated_at", "") or "")
        recommendations = list(payload.get("recommendations", []) or [])
        decisions_by_symbol = {
            normalize_symbol(str(item.get("symbol", "") or "")): item
            for item in ((payload.get("trade_plan", {}) or {}).get("decisions", []) or [])
            if str(item.get("symbol", "") or "").strip()
        }
        board_candidates_by_symbol = {
            normalize_symbol(str(item.get("symbol", "") or "")): item
            for item in ((payload.get("board_plan", {}) or {}).get("candidates", []) or [])
            if str(item.get("symbol", "") or "").strip()
        }
        signals: list[StrategyHistorySignal] = []
        for item in recommendations:
            signal = self._build_signal(
                row=item,
                generated_at=generated_at,
                source_file=str(path),
                source_kind=source_kind,
                decision=decisions_by_symbol.get(normalize_symbol(str(item.get("symbol", "") or ""))),
                board_candidate=board_candidates_by_symbol.get(normalize_symbol(str(item.get("symbol", "") or ""))),
                params=params,
            )
            if signal is None:
                continue
            if signal.signal_date < params.start_date or signal.signal_date > params.end_date:
                continue
            signals.append(signal)
        if signals:
            return signals

        for item in decisions_by_symbol.values():
            signal = self._build_signal_from_decision(
                decision=item,
                generated_at=generated_at,
                source_file=str(path),
                source_kind=source_kind,
                params=params,
            )
            if signal is None:
                continue
            if signal.signal_date < params.start_date or signal.signal_date > params.end_date:
                continue
            signals.append(signal)
        return signals

    def _build_signal(
        self,
        *,
        row: dict[str, Any],
        generated_at: str,
        source_file: str,
        source_kind: str,
        decision: dict[str, Any] | None,
        board_candidate: dict[str, Any] | None,
        params: StrategyHistoryReplayParams,
    ) -> StrategyHistorySignal | None:
        symbol = normalize_symbol(str(row.get("symbol", "") or ""))
        if not symbol:
            return None
        action = str(row.get("action", "") or "WATCH").upper()
        if action == "WATCH" and not params.include_watch_only:
            return None
        close_price = self._safe_float(row.get("close"))
        entry_price = self._first_positive(
            row.get("entry_price"),
            (decision or {}).get("planned_entry"),
            (board_candidate or {}).get("planned_entry"),
            close_price,
        )
        if entry_price <= 0:
            return None
        stop_price = self._first_positive(
            row.get("stop_price"),
            (decision or {}).get("planned_stop"),
            (board_candidate or {}).get("planned_stop"),
            entry_price * (1.0 - params.fallback_stop_pct),
        )
        target_price = self._first_positive(
            row.get("target_price"),
            (decision or {}).get("planned_target"),
            (board_candidate or {}).get("planned_target"),
            entry_price * (1.0 + params.fallback_target_pct),
        )
        strategy_name = self._resolve_strategy_name(row, decision, board_candidate)
        return StrategyHistorySignal(
            symbol=symbol,
            stock_id=str(row.get("stock_id", "") or extract_stock_id(symbol)),
            stock_name=str(row.get("stock_name", "") or ""),
            signal_date=str(row.get("signal_date", "") or self._date_from_generated_at(generated_at)),
            generated_at=generated_at,
            strategy_name=strategy_name,
            action=action,
            entry_price=round(entry_price, 4),
            stop_price=round(stop_price, 4),
            target_price=round(target_price, 4),
            source_file=source_file,
            source_kind=source_kind,
            rationale=str(row.get("rationale", "") or (decision or {}).get("rationale", "") or ""),
        )

    def _build_signal_from_decision(
        self,
        *,
        decision: dict[str, Any],
        generated_at: str,
        source_file: str,
        source_kind: str,
        params: StrategyHistoryReplayParams,
    ) -> StrategyHistorySignal | None:
        symbol = normalize_symbol(str(decision.get("symbol", "") or ""))
        if not symbol:
            return None
        action = str(decision.get("action", "") or "WATCH").upper()
        if action == "WATCH" and not params.include_watch_only:
            return None
        entry_price = self._first_positive(decision.get("planned_entry"))
        if entry_price <= 0:
            return None
        stop_price = self._first_positive(decision.get("planned_stop"), entry_price * (1.0 - params.fallback_stop_pct))
        target_price = self._first_positive(decision.get("planned_target"), entry_price * (1.0 + params.fallback_target_pct))
        strategy_name = self._canonical_strategy_name(
            str(decision.get("strategy_name", "") or decision.get("stock_pool", "") or "")
        ) or "掘龙决策"
        return StrategyHistorySignal(
            symbol=symbol,
            stock_id=str(decision.get("stock_id", "") or extract_stock_id(symbol)),
            stock_name=str(decision.get("stock_name", "") or ""),
            signal_date=self._date_from_generated_at(generated_at),
            generated_at=generated_at,
            strategy_name=strategy_name,
            action=action,
            entry_price=round(entry_price, 4),
            stop_price=round(stop_price, 4),
            target_price=round(target_price, 4),
            source_file=source_file,
            source_kind=source_kind,
            rationale=str(decision.get("rationale", "") or ""),
        )

    def _resolve_strategy_name(
        self,
        row: dict[str, Any],
        decision: dict[str, Any] | None,
        board_candidate: dict[str, Any] | None,
    ) -> str:
        candidates = [
            row.get("primary_strategy"),
            (decision or {}).get("strategy_name"),
            (board_candidate or {}).get("trigger_style"),
            row.get("stock_pool"),
        ]
        for value in candidates:
            canonical = self._canonical_strategy_name(str(value or "").strip())
            if canonical:
                return canonical
        return "掘龙决策"

    def _replay_signals(
        self,
        signals: list[StrategyHistorySignal],
        params: StrategyHistoryReplayParams,
    ) -> tuple[list[StrategyHistoryTrade], list[str]]:
        trades: list[StrategyHistoryTrade] = []
        notes: list[str] = []
        bars_cache: dict[str, list[PriceBar]] = {}
        for signal in signals:
            bars = bars_cache.get(signal.symbol)
            if bars is None:
                try:
                    bars = self.market_feed.fetch_daily_bars(signal.symbol, start="20200101", end="20500101")
                except Exception as exc:
                    bars = []
                    notes.append(f"缺少行情：{signal.symbol} | {signal.strategy_name} | {exc}")
                bars_cache[signal.symbol] = bars
            trade = self._replay_single_signal(signal, bars, params)
            if trade is None:
                notes.append(f"未成交或缺少样本：{signal.signal_date} | {signal.symbol} | {signal.strategy_name}")
                continue
            trades.append(trade)
        trades.sort(key=lambda item: (item.entry_date, item.strategy_name, item.symbol))
        return trades, self._unique_notes(notes)

    def _replay_single_signal(
        self,
        signal: StrategyHistorySignal,
        bars: list[PriceBar],
        params: StrategyHistoryReplayParams,
    ) -> StrategyHistoryTrade | None:
        if len(bars) < 2:
            return None
        signal_index = next((index for index, bar in enumerate(bars) if bar.date >= signal.signal_date), -1)
        if signal_index < 0 or signal_index + 1 >= len(bars):
            return None
        entry_date, entry_price, entry_index = self._resolve_entry(signal, bars, signal_index + 1, params)
        if not entry_date or entry_price <= 0:
            return None

        exit_date = entry_date
        exit_price = entry_price
        exit_reason = "样本结束"
        hold_days = 1
        for index in range(entry_index, len(bars)):
            bar = bars[index]
            hold_days = index - entry_index + 1
            if bar.low <= signal.stop_price and not self._is_limit_down(bar, params):
                exit_date = bar.date
                exit_price = signal.stop_price * (1.0 - params.slippage_rate)
                exit_reason = "止损"
                break
            if bar.high >= signal.target_price and not self._is_limit_down(bar, params):
                exit_date = bar.date
                exit_price = signal.target_price * (1.0 - params.slippage_rate)
                exit_reason = "止盈"
                break
            if hold_days >= params.max_hold_days:
                exit_date = bar.date
                exit_price = self._resolve_timeout_exit_price(bar, params)
                exit_reason = "超时"
                break
            exit_date = bar.date
            exit_price = self._resolve_timeout_exit_price(bar, params)

        pnl_pct = self._net_pnl_pct(entry_price, exit_price, params)
        return StrategyHistoryTrade(
            strategy_name=signal.strategy_name,
            symbol=signal.symbol,
            stock_id=signal.stock_id,
            stock_name=signal.stock_name,
            signal_date=signal.signal_date,
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=round(entry_price, 4),
            exit_price=round(exit_price, 4),
            pnl_pct=round(pnl_pct, 4),
            hold_days=hold_days,
            exit_reason=exit_reason,
            source_file=signal.source_file,
        )

    def _resolve_entry(
        self,
        signal: StrategyHistorySignal,
        bars: list[PriceBar],
        start_index: int,
        params: StrategyHistoryReplayParams,
    ) -> tuple[str, float, int]:
        for index in range(start_index, len(bars)):
            bar = bars[index]
            if self._is_limit_up(bar, params):
                continue
            if bar.open <= signal.entry_price:
                return bar.date, bar.open * (1.0 + params.slippage_rate), index
            if bar.low <= signal.entry_price <= bar.high:
                return bar.date, signal.entry_price * (1.0 + params.slippage_rate), index
        return "", 0.0, -1

    def _resolve_timeout_exit_price(self, bar: PriceBar, params: StrategyHistoryReplayParams) -> float:
        if self._is_limit_down(bar, params):
            return bar.close
        return bar.close * (1.0 - params.slippage_rate)

    def _net_pnl_pct(self, entry_price: float, exit_price: float, params: StrategyHistoryReplayParams) -> float:
        if entry_price <= 0:
            return 0.0
        entry_cost = entry_price * (1.0 + params.commission_rate)
        exit_income = exit_price * (1.0 - params.commission_rate - params.stamp_duty_rate)
        return (exit_income - entry_cost) / entry_price

    @staticmethod
    def _is_limit_up(bar: PriceBar, params: StrategyHistoryReplayParams) -> bool:
        if not params.block_limit_up_entry:
            return False
        return abs(bar.high - bar.low) < 1e-9 and abs(bar.close - bar.high) < 1e-9

    @staticmethod
    def _is_limit_down(bar: PriceBar, params: StrategyHistoryReplayParams) -> bool:
        if not params.block_limit_down_exit:
            return False
        return abs(bar.high - bar.low) < 1e-9 and abs(bar.close - bar.low) < 1e-9

    def _build_summaries(
        self,
        signals: list[StrategyHistorySignal],
        trades: list[StrategyHistoryTrade],
        notes: list[str],
    ) -> list[StrategyHistorySummary]:
        trades_by_strategy: dict[str, list[StrategyHistoryTrade]] = {}
        for trade in trades:
            trades_by_strategy.setdefault(trade.strategy_name, []).append(trade)
        signals_by_strategy: dict[str, list[StrategyHistorySignal]] = {}
        for signal in signals:
            signals_by_strategy.setdefault(signal.strategy_name, []).append(signal)

        missing_data_count_by_strategy: dict[str, int] = {}
        for note in notes:
            if not note.startswith("缺少行情：") and not note.startswith("未成交或缺少样本："):
                continue
            parts = [item.strip() for item in note.split("|")]
            if len(parts) < 2:
                continue
            strategy_name = parts[1] if note.startswith("缺少行情：") else (parts[2] if len(parts) >= 3 else "")
            if strategy_name:
                missing_data_count_by_strategy[strategy_name] = missing_data_count_by_strategy.get(strategy_name, 0) + 1

        summaries: list[StrategyHistorySummary] = []
        for strategy_name in sorted(signals_by_strategy):
            strategy_signals = signals_by_strategy[strategy_name]
            strategy_trades = trades_by_strategy.get(strategy_name, [])
            signal_count = len(strategy_signals)
            trade_count = len(strategy_trades)
            returns = [item.pnl_pct for item in strategy_trades]
            equity_curve = self._compound_curve(returns)
            max_drawdown = self._max_drawdown(equity_curve)
            wins = [item for item in strategy_trades if item.pnl_pct > 0]
            losses = [item for item in strategy_trades if item.pnl_pct < 0]
            gross_profit = sum(float(item.pnl_pct) for item in wins)
            gross_loss = abs(sum(float(item.pnl_pct) for item in losses))
            avg_win = (gross_profit / len(wins)) if wins else 0.0
            avg_loss = (gross_loss / len(losses)) if losses else 0.0
            profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
            payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else (999.0 if avg_win > 0 else 0.0)
            max_consecutive_wins, max_consecutive_losses = self._max_streaks(strategy_trades)
            best_trade_return = max(returns) if returns else 0.0
            worst_trade_return = min(returns) if returns else 0.0
            avg_hold_days = (sum(item.hold_days for item in strategy_trades) / trade_count) if trade_count else 0.0
            no_fill_count = max(signal_count - trade_count, 0)
            summaries.append(
                StrategyHistorySummary(
                    strategy_name=strategy_name,
                    signal_count=signal_count,
                    trade_count=trade_count,
                    filled_ratio=round(trade_count / signal_count, 4) if signal_count else 0.0,
                    win_rate=round(len(wins) / trade_count, 4) if trade_count else 0.0,
                    total_return=round(equity_curve[-1] - 1.0, 4) if equity_curve else 0.0,
                    avg_return=round(sum(returns) / trade_count, 4) if trade_count else 0.0,
                    max_drawdown=round(max_drawdown, 4),
                    avg_hold_days=round(avg_hold_days, 2),
                    symbol_count=len({item.symbol for item in strategy_signals}),
                    no_fill_count=no_fill_count,
                    missing_data_count=missing_data_count_by_strategy.get(strategy_name, 0),
                    profit_factor=round(profit_factor, 4),
                    payoff_ratio=round(payoff_ratio, 4),
                    max_consecutive_wins=max_consecutive_wins,
                    max_consecutive_losses=max_consecutive_losses,
                    best_trade_return=round(best_trade_return, 4),
                    worst_trade_return=round(worst_trade_return, 4),
                    target_hits=sum(1 for item in strategy_trades if item.exit_reason == "止盈"),
                    stop_hits=sum(1 for item in strategy_trades if item.exit_reason == "止损"),
                    timeout_exits=sum(1 for item in strategy_trades if item.exit_reason == "超时"),
                    end_exits=sum(1 for item in strategy_trades if item.exit_reason == "样本结束"),
                )
            )
        summaries.sort(key=lambda item: (item.total_return, item.win_rate, item.trade_count, item.strategy_name), reverse=True)
        return summaries

    def _build_equity_points(self, trades: list[StrategyHistoryTrade]) -> list[StrategyHistoryEquityPoint]:
        trades_by_strategy: dict[str, list[StrategyHistoryTrade]] = {}
        for trade in trades:
            trades_by_strategy.setdefault(trade.strategy_name, []).append(trade)
        points: list[StrategyHistoryEquityPoint] = []
        for strategy_name, strategy_trades in trades_by_strategy.items():
            equity = 1.0
            for index, trade in enumerate(sorted(strategy_trades, key=lambda item: (item.exit_date, item.entry_date, item.symbol)), start=1):
                equity *= 1.0 + float(trade.pnl_pct)
                points.append(
                    StrategyHistoryEquityPoint(
                        strategy_name=strategy_name,
                        date=trade.exit_date or trade.entry_date or trade.signal_date,
                        equity=round(equity, 6),
                        trade_index=index,
                    )
                )
        points.sort(key=lambda item: (item.strategy_name, item.date, item.trade_index))
        return points

    def _build_period_stats(self, trades: list[StrategyHistoryTrade], *, period: str) -> list[StrategyHistoryPeriodStat]:
        grouped: dict[tuple[str, str], list[StrategyHistoryTrade]] = {}
        for trade in trades:
            date_text = trade.exit_date or trade.entry_date or trade.signal_date
            if not date_text:
                continue
            key_period = date_text[:7] if period == "month" else date_text[:4]
            grouped.setdefault((trade.strategy_name, key_period), []).append(trade)
        results: list[StrategyHistoryPeriodStat] = []
        for (strategy_name, key_period), items in sorted(grouped.items()):
            returns = [float(item.pnl_pct) for item in items]
            wins = [item for item in items if float(item.pnl_pct) > 0]
            equity_curve = self._compound_curve(returns)
            results.append(
                StrategyHistoryPeriodStat(
                    strategy_name=strategy_name,
                    period=key_period,
                    trade_count=len(items),
                    win_rate=round(len(wins) / len(items), 4) if items else 0.0,
                    total_return=round(equity_curve[-1] - 1.0, 4) if equity_curve else 0.0,
                    avg_return=round(sum(returns) / len(items), 4) if items else 0.0,
                )
            )
        return results

    @staticmethod
    def _max_streaks(trades: list[StrategyHistoryTrade]) -> tuple[int, int]:
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        for trade in sorted(trades, key=lambda item: (item.exit_date, item.entry_date, item.symbol)):
            pnl = float(trade.pnl_pct)
            if pnl > 0:
                current_wins += 1
                current_losses = 0
            elif pnl < 0:
                current_losses += 1
                current_wins = 0
            else:
                current_wins = 0
                current_losses = 0
            max_wins = max(max_wins, current_wins)
            max_losses = max(max_losses, current_losses)
        return max_wins, max_losses

    @staticmethod
    def report_as_table_rows(report: StrategyHistoryReport) -> list[dict[str, Any]]:
        return [asdict(item) for item in report.summaries]

    @staticmethod
    def comparison_as_table_rows(rows: list[StrategyHistoryScenarioComparison] | None) -> list[dict[str, Any]]:
        return [asdict(item) for item in (rows or [])]

    @staticmethod
    def comparison_leaderboard(rows: list[StrategyHistoryScenarioComparison] | None) -> list[StrategyHistoryScenarioLeaderboard]:
        grouped: dict[str, list[StrategyHistoryScenarioComparison]] = {}
        for item in rows or []:
            grouped.setdefault(item.strategy_name, []).append(item)
        results: list[StrategyHistoryScenarioLeaderboard] = []
        for strategy_name, items in grouped.items():
            ordered = sorted(items, key=lambda item: (float(item.total_return), float(item.win_rate)), reverse=True)
            best = ordered[0]
            worst = ordered[-1]
            avg_total_return = sum(float(item.total_return) for item in items) / len(items) if items else 0.0
            results.append(
                StrategyHistoryScenarioLeaderboard(
                    strategy_name=strategy_name,
                    scenario_count=len(items),
                    best_scenario_label=best.scenario_label,
                    best_total_return=round(float(best.total_return), 4),
                    worst_scenario_label=worst.scenario_label,
                    worst_total_return=round(float(worst.total_return), 4),
                    return_spread=round(float(best.total_return) - float(worst.total_return), 4),
                    avg_total_return=round(avg_total_return, 4),
                )
            )
        results.sort(key=lambda item: (item.return_spread, item.best_total_return, item.strategy_name), reverse=True)
        return results

    @staticmethod
    def leaderboard_as_table_rows(rows: list[StrategyHistoryScenarioLeaderboard] | None) -> list[dict[str, Any]]:
        return [asdict(item) for item in (rows or [])]

    @staticmethod
    def select_summary(
        report: StrategyHistoryReport | None,
        strategy_name: str = "",
    ) -> StrategyHistorySummary | None:
        if report is None:
            return None
        target = str(strategy_name or "").strip()
        if target:
            return next((item for item in report.summaries if item.strategy_name == target), None)
        return report.summaries[0] if report.summaries else None

    @staticmethod
    def trades_for_strategy(
        report: StrategyHistoryReport | None,
        strategy_name: str = "",
    ) -> list[StrategyHistoryTrade]:
        if report is None:
            return []
        target = str(strategy_name or "").strip()
        if not target:
            return list(report.trades)
        return [item for item in report.trades if item.strategy_name == target]

    @staticmethod
    def trade_as_table_rows(
        report: StrategyHistoryReport | None,
        strategy_name: str = "",
    ) -> list[dict[str, Any]]:
        return [asdict(item) for item in StrategyHistoryReplayer.trades_for_strategy(report, strategy_name)]

    @staticmethod
    def format_report_summary(report: StrategyHistoryReport, *, selected_strategy: str = "") -> str:
        lines = [
            "历史战法回测",
            f"区间：{report.start_date} -> {report.end_date}",
            f"样本文件：{len(report.source_files)}",
            f"荐股信号：{len(report.signals)}",
            f"成交样本：{len(report.trades)}",
        ]
        if selected_strategy:
            summary = next((item for item in report.summaries if item.strategy_name == selected_strategy), None)
            if summary is not None:
                lines.extend(
                    [
                        "",
                        f"当前战法：{summary.strategy_name}",
                        f"总收益：{summary.total_return:.2%} | 胜率：{summary.win_rate:.2%} | 最大回撤：{summary.max_drawdown:.2%}",
                        f"信号 {summary.signal_count} | 成交 {summary.trade_count} | 成交率 {summary.filled_ratio:.2%} | 平均持有 {summary.avg_hold_days:.2f} 天",
                        f"止盈 {summary.target_hits} | 止损 {summary.stop_hits} | 超时 {summary.timeout_exits} | 样本结束 {summary.end_exits}",
                    ]
                )
        elif report.summaries:
            top = report.summaries[0]
            lines.extend(
                [
                    "",
                    f"领先战法：{top.strategy_name}",
                    f"总收益：{top.total_return:.2%} | 胜率：{top.win_rate:.2%} | 最大回撤：{top.max_drawdown:.2%}",
                ]
            )
        if report.notes:
            lines.extend(["", "备注："] + [f"- {item}" for item in report.notes[:6]])
        return "\n".join(lines)

    @staticmethod
    def default_comparison_scenarios(base_params: StrategyHistoryReplayParams) -> list[StrategyHistoryScenarioPreset]:
        return [
            StrategyHistoryScenarioPreset(
                label="当前参数",
                note="使用当前界面回测参数",
                params=base_params,
            ),
            StrategyHistoryScenarioPreset(
                label="短持快出",
                note="持有 3 天，观察短线效率",
                params=StrategyHistoryReplayParams(
                    start_date=base_params.start_date,
                    end_date=base_params.end_date,
                    max_hold_days=3,
                    fallback_stop_pct=base_params.fallback_stop_pct,
                    fallback_target_pct=base_params.fallback_target_pct,
                    slippage_rate=base_params.slippage_rate,
                    commission_rate=base_params.commission_rate,
                    stamp_duty_rate=base_params.stamp_duty_rate,
                    include_watch_only=base_params.include_watch_only,
                    block_limit_up_entry=base_params.block_limit_up_entry,
                    block_limit_down_exit=base_params.block_limit_down_exit,
                ),
            ),
            StrategyHistoryScenarioPreset(
                label="波段持有",
                note="持有 10 天，观察延续能力",
                params=StrategyHistoryReplayParams(
                    start_date=base_params.start_date,
                    end_date=base_params.end_date,
                    max_hold_days=10,
                    fallback_stop_pct=base_params.fallback_stop_pct,
                    fallback_target_pct=base_params.fallback_target_pct,
                    slippage_rate=base_params.slippage_rate,
                    commission_rate=base_params.commission_rate,
                    stamp_duty_rate=base_params.stamp_duty_rate,
                    include_watch_only=base_params.include_watch_only,
                    block_limit_up_entry=base_params.block_limit_up_entry,
                    block_limit_down_exit=base_params.block_limit_down_exit,
                ),
            ),
            StrategyHistoryScenarioPreset(
                label="低摩擦",
                note="降低交易摩擦，观察净收益弹性",
                params=StrategyHistoryReplayParams(
                    start_date=base_params.start_date,
                    end_date=base_params.end_date,
                    max_hold_days=base_params.max_hold_days,
                    fallback_stop_pct=base_params.fallback_stop_pct,
                    fallback_target_pct=base_params.fallback_target_pct,
                    slippage_rate=min(base_params.slippage_rate, 0.0002),
                    commission_rate=min(base_params.commission_rate, 0.0001),
                    stamp_duty_rate=min(base_params.stamp_duty_rate, 0.0005),
                    include_watch_only=base_params.include_watch_only,
                    block_limit_up_entry=base_params.block_limit_up_entry,
                    block_limit_down_exit=base_params.block_limit_down_exit,
                ),
            ),
            StrategyHistoryScenarioPreset(
                label="放宽涨跌停",
                note="不阻断涨停买入和跌停卖出，观察理论上限",
                params=StrategyHistoryReplayParams(
                    start_date=base_params.start_date,
                    end_date=base_params.end_date,
                    max_hold_days=base_params.max_hold_days,
                    fallback_stop_pct=base_params.fallback_stop_pct,
                    fallback_target_pct=base_params.fallback_target_pct,
                    slippage_rate=base_params.slippage_rate,
                    commission_rate=base_params.commission_rate,
                    stamp_duty_rate=base_params.stamp_duty_rate,
                    include_watch_only=base_params.include_watch_only,
                    block_limit_up_entry=False,
                    block_limit_down_exit=False,
                ),
            ),
        ]

    @staticmethod
    def _date_from_generated_at(value: str) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if "T" in text:
            return text.split("T", 1)[0]
        if " " in text:
            return text.split(" ", 1)[0]
        return text[:10]

    @staticmethod
    def _safe_float(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _first_positive(*values: Any) -> float:
        for value in values:
            try:
                result = float(value)
            except (TypeError, ValueError):
                continue
            if result > 0:
                return result
        return 0.0

    @staticmethod
    def _compound_curve(returns: list[float]) -> list[float]:
        equity = 1.0
        curve = []
        for value in returns:
            equity *= 1.0 + value
            curve.append(equity)
        return curve

    @staticmethod
    def _max_drawdown(equity_curve: list[float]) -> float:
        peak = 1.0
        max_drawdown = 0.0
        for equity in equity_curve:
            peak = max(peak, equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - equity) / peak)
        return max_drawdown

    @staticmethod
    def _unique_notes(notes: list[str]) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()
        for item in notes:
            text = str(item or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
        return result

    @staticmethod
    def _canonical_strategy_name(value: str) -> str:
        raw = str(value or "").strip()
        alias_map = {
            "龙头主线": "龙头模型",
            "龙头模型": "龙头模型",
            "资金承接": "主力雷达",
            "主力雷达": "主力雷达",
            "强势接力": "擒龙打板",
            "打板策略": "擒龙打板",
            "擒龙打板": "擒龙打板",
            "趋势低吸": "价值低吸",
            "价值低吸": "价值低吸",
            "尾盘买入": "尾盘买入法",
            "尾盘买入法": "尾盘买入法",
            "一日持股": "一日持股法",
            "隔日强势": "一日持股法",
            "一日持股法": "一日持股法",
            "综合决策": "掘龙决策",
            "掘龙": "掘龙决策",
            "掘龙决策": "掘龙决策",
        }
        return alias_map.get(raw, raw)
