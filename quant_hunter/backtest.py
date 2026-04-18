from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .models import (
    BacktestResult,
    DailyAnalysis,
    EquityPoint,
    PortfolioBacktestResult,
    PortfolioSnapshot,
    PriceBar,
    SymbolBacktestSummary,
    Trade,
)
from .risk import DEFAULT_RISK_CONTROLS
from .strategy import StrategyParams


@dataclass
class PendingEntry:
    symbol: str
    bar_index: int
    source_signal: DailyAnalysis


@dataclass
class OpenPosition:
    symbol: str
    entry_date: str
    entry_index: int
    entry_price: float
    shares: int
    stop_price: float
    target_price: float
    entry_fee: float


@dataclass(frozen=True)
class BacktestParams:
    initial_capital: float = 200000.0
    risk_fraction: float = 0.01
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0005
    stamp_duty_rate: float = 0.0
    max_hold_days: int = 8
    lot_size: int = 100
    min_entry_risk_reward_ratio: float = DEFAULT_RISK_CONTROLS.backtest_min_entry_risk_reward_ratio
    max_volume_participation: float = 1.0
    block_limit_up_entry: bool = False
    block_limit_down_exit: bool = False
    max_position_fraction: float = 1.0
    max_positions: int = 1

    @classmethod
    def realistic_cn_equity(cls, **overrides: float | int | bool) -> BacktestParams:
        data: dict[str, float | int | bool] = {
            "stamp_duty_rate": 0.001,
            "max_volume_participation": 0.1,
            "block_limit_up_entry": True,
            "block_limit_down_exit": True,
            "max_position_fraction": 0.25,
            "max_positions": 5,
        }
        data.update(overrides)
        return cls(**data)


class _BacktestExecutionMixin:
    def __init__(self, backtest_params: BacktestParams) -> None:
        self.backtest_params = backtest_params

    def _is_limit_up(self, bar: PriceBar) -> bool:
        if not self.backtest_params.block_limit_up_entry:
            return False
        return abs(bar.high - bar.low) < 1e-9 and abs(bar.close - bar.high) < 1e-9

    def _is_limit_down(self, bar: PriceBar) -> bool:
        if not self.backtest_params.block_limit_down_exit:
            return False
        return abs(bar.high - bar.low) < 1e-9 and abs(bar.close - bar.low) < 1e-9

    @staticmethod
    def _estimated_risk_reward_ratio(signal: DailyAnalysis) -> float:
        if signal.entry_price is None or signal.stop_price is None or signal.target_price is None:
            return 0.0
        estimated_loss = signal.entry_price - signal.stop_price
        estimated_profit = signal.target_price - signal.entry_price
        if estimated_loss <= 0 or estimated_profit <= 0:
            return 0.0
        return estimated_profit / estimated_loss

    def _resolve_entry_price(self, source_signal: DailyAnalysis, bar: PriceBar) -> float | None:
        params = self.backtest_params
        if source_signal.stop_price is None or source_signal.target_price is None:
            return None
        if self._is_limit_up(bar):
            return None

        planned_entry = source_signal.entry_price
        if planned_entry is not None and planned_entry > 0:
            if bar.open <= planned_entry:
                entry_price = bar.open * (1.0 + params.slippage_rate)
            elif bar.low <= planned_entry <= bar.high:
                entry_price = planned_entry * (1.0 + params.slippage_rate)
            else:
                return None
        else:
            entry_price = bar.open * (1.0 + params.slippage_rate)
        if entry_price <= 0:
            return None

        estimated_loss = entry_price - source_signal.stop_price
        estimated_profit = source_signal.target_price - entry_price
        if estimated_loss <= 0 or estimated_profit <= 0:
            return None

        risk_reward_ratio = estimated_profit / estimated_loss
        if risk_reward_ratio < params.min_entry_risk_reward_ratio:
            return None

        return entry_price

    def _position_size_shares(
        self,
        *,
        entry_price: float,
        stop_price: float,
        cash: float,
        equity: float,
        bar: PriceBar,
    ) -> int:
        params = self.backtest_params
        if entry_price <= 0 or stop_price <= 0 or cash <= 0 or equity <= 0:
            return 0

        risk_per_share = max(entry_price - stop_price, 0.01)
        risk_budget = max(equity * params.risk_fraction, 0.0)
        max_by_risk = int(risk_budget / risk_per_share) if risk_budget > 0 else 0
        entry_cash_per_share = entry_price * (1.0 + params.commission_rate)
        max_by_cash = int(cash / entry_cash_per_share) if entry_cash_per_share > 0 else 0

        position_fraction = min(max(params.max_position_fraction, 0.0), 1.0)
        position_budget = equity if position_fraction <= 0 else equity * position_fraction
        max_by_position = int(position_budget / entry_price) if entry_price > 0 else 0

        participation = min(max(params.max_volume_participation, 0.0), 1.0)
        volume_limit = int(float(bar.volume or 0.0) * participation) if participation > 0 else 0
        max_by_volume = volume_limit

        shares = min(max_by_risk, max_by_cash, max_by_position, max_by_volume)
        lot_size = max(int(params.lot_size or 0), 1)
        return (shares // lot_size) * lot_size

    def _open_position(
        self,
        *,
        symbol: str,
        bar_index: int,
        bar: PriceBar,
        entry_price: float,
        stop_price: float,
        target_price: float,
        shares: int,
        cash: float,
    ) -> tuple[float, OpenPosition]:
        entry_cost = shares * entry_price
        entry_fee = entry_cost * self.backtest_params.commission_rate
        cash_after_entry = cash - entry_cost - entry_fee
        position = OpenPosition(
            symbol=symbol,
            entry_date=bar.date,
            entry_index=bar_index,
            entry_price=entry_price,
            shares=shares,
            stop_price=stop_price,
            target_price=target_price,
            entry_fee=entry_fee,
        )
        return cash_after_entry, position

    def _resolve_exit(
        self,
        *,
        position: OpenPosition,
        bar: PriceBar,
        analysis: DailyAnalysis,
        hold_days: int,
    ) -> tuple[float, str] | None:
        params = self.backtest_params
        if bar.low <= position.stop_price:
            if self._is_limit_down(bar):
                return None
            return position.stop_price * (1.0 - params.slippage_rate), "跌破止损"
        if bar.high >= position.target_price:
            return position.target_price * (1.0 - params.slippage_rate), "达到目标位"
        if hold_days >= params.max_hold_days:
            if self._is_limit_down(bar):
                return None
            return bar.close * (1.0 - params.slippage_rate), "超过持有天数"
        if analysis.label == "TRAP_DETECTED":
            if self._is_limit_down(bar):
                return None
            return bar.close * (1.0 - params.slippage_rate), "再次出现诱多陷阱"
        if bar.close < analysis.ma_slow:
            if self._is_limit_down(bar):
                return None
            return bar.close * (1.0 - params.slippage_rate), "失守慢线"
        return None

    def _close_position(
        self,
        *,
        position: OpenPosition,
        exit_date: str,
        exit_price: float,
        exit_reason: str,
        cash: float,
    ) -> tuple[float, Trade]:
        params = self.backtest_params
        proceeds = position.shares * exit_price
        exit_commission = proceeds * params.commission_rate
        stamp_duty = proceeds * params.stamp_duty_rate
        cash_after_exit = cash + proceeds - exit_commission - stamp_duty
        pnl = (exit_price - position.entry_price) * position.shares - position.entry_fee - exit_commission - stamp_duty
        cost_basis = position.entry_price * position.shares
        pnl_pct = (pnl / cost_basis) if cost_basis > 0 else 0.0
        trade = Trade(
            symbol=position.symbol,
            entry_date=position.entry_date,
            exit_date=exit_date,
            entry_price=round(position.entry_price, 3),
            exit_price=round(exit_price, 3),
            shares=position.shares,
            pnl=round(pnl, 2),
            pnl_pct=round(pnl_pct, 4),
            hold_days=max(1, 0),
            exit_reason=exit_reason,
        )
        return cash_after_exit, trade

    @staticmethod
    def _profit_factor(trades: list[Trade]) -> float:
        wins = [trade for trade in trades if trade.pnl > 0]
        losses = [trade for trade in trades if trade.pnl < 0]
        gross_profit = sum(trade.pnl for trade in wins)
        gross_loss = abs(sum(trade.pnl for trade in losses))
        return round(gross_profit / gross_loss, 4) if gross_loss else float("inf")

    def _build_backtest_result(
        self,
        *,
        initial_capital: float,
        ending_equity: float,
        trades: list[Trade],
        equity_curve: list[EquityPoint],
    ) -> BacktestResult:
        peak = initial_capital
        max_drawdown = 0.0
        for point in equity_curve:
            peak = max(peak, point.equity)
            if peak > 0:
                max_drawdown = max(max_drawdown, (peak - point.equity) / peak)
        wins = [trade for trade in trades if trade.pnl > 0]
        return BacktestResult(
            initial_capital=initial_capital,
            ending_equity=round(ending_equity, 2),
            total_return=round((ending_equity - initial_capital) / initial_capital, 4) if initial_capital > 0 else 0.0,
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(len(wins) / len(trades), 4) if trades else 0.0,
            profit_factor=self._profit_factor(trades),
            trades=trades,
            equity_curve=equity_curve,
        )


class Backtester(_BacktestExecutionMixin):
    def __init__(
        self,
        strategy_params: StrategyParams | None = None,
        backtest_params: BacktestParams | None = None,
    ) -> None:
        self.strategy_params = strategy_params or StrategyParams()
        params = backtest_params or BacktestParams()
        super().__init__(params)

    def run(self, bars: list[PriceBar], analyses: list[DailyAnalysis]) -> BacktestResult:
        params = self.backtest_params
        cash = params.initial_capital
        equity = params.initial_capital
        pending_entry: PendingEntry | None = None
        position: OpenPosition | None = None
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []

        for index, bar in enumerate(bars):
            if pending_entry and pending_entry.bar_index == index and position is None:
                source = pending_entry.source_signal
                entry_price = self._resolve_entry_price(source, bar)
                if entry_price is not None and source.stop_price is not None and source.target_price is not None:
                    shares = self._position_size_shares(
                        entry_price=entry_price,
                        stop_price=source.stop_price,
                        cash=cash,
                        equity=equity,
                        bar=bar,
                    )
                    if shares >= max(int(params.lot_size or 0), 1):
                        cash, position = self._open_position(
                            symbol=bar.symbol,
                            bar_index=index,
                            bar=bar,
                            entry_price=entry_price,
                            stop_price=source.stop_price,
                            target_price=source.target_price,
                            shares=shares,
                            cash=cash,
                        )
                pending_entry = None

            if position is not None:
                hold_days = index - position.entry_index + 1
                exit_decision = self._resolve_exit(
                    position=position,
                    bar=bar,
                    analysis=analyses[index],
                    hold_days=hold_days,
                )
                if exit_decision is not None:
                    exit_price, exit_reason = exit_decision
                    cash, trade = self._close_position(
                        position=position,
                        exit_date=bar.date,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        cash=cash,
                    )
                    trade = Trade(
                        symbol=trade.symbol,
                        entry_date=trade.entry_date,
                        exit_date=trade.exit_date,
                        entry_price=trade.entry_price,
                        exit_price=trade.exit_price,
                        shares=trade.shares,
                        pnl=trade.pnl,
                        pnl_pct=trade.pnl_pct,
                        hold_days=hold_days,
                        exit_reason=trade.exit_reason,
                    )
                    trades.append(trade)
                    position = None

            signal = analyses[index]
            if signal.label == "RECLAIM_LONG" and index + 1 < len(bars) and position is None:
                pending_entry = PendingEntry(symbol=bar.symbol, bar_index=index + 1, source_signal=signal)

            market_value = position.shares * bar.close if position is not None else 0.0
            equity = cash + market_value
            equity_curve.append(EquityPoint(date=bar.date, equity=round(equity, 2)))

        if position is not None and bars:
            last_bar = bars[-1]
            exit_price = last_bar.close * (1.0 - params.slippage_rate)
            hold_days = len(bars) - position.entry_index
            cash, trade = self._close_position(
                position=position,
                exit_date=last_bar.date,
                exit_price=exit_price,
                exit_reason="样本结束平仓",
                cash=cash,
            )
            trades.append(
                Trade(
                    symbol=trade.symbol,
                    entry_date=trade.entry_date,
                    exit_date=trade.exit_date,
                    entry_price=trade.entry_price,
                    exit_price=trade.exit_price,
                    shares=trade.shares,
                    pnl=trade.pnl,
                    pnl_pct=trade.pnl_pct,
                    hold_days=hold_days,
                    exit_reason=trade.exit_reason,
                )
            )
            if equity_curve:
                equity_curve[-1] = EquityPoint(date=last_bar.date, equity=round(cash, 2))
            equity = cash

        ending_equity = equity_curve[-1].equity if equity_curve else params.initial_capital
        return self._build_backtest_result(
            initial_capital=params.initial_capital,
            ending_equity=ending_equity,
            trades=trades,
            equity_curve=equity_curve,
        )


class PortfolioBacktester(_BacktestExecutionMixin):
    def __init__(
        self,
        strategy_params: StrategyParams | None = None,
        backtest_params: BacktestParams | None = None,
    ) -> None:
        self.strategy_params = strategy_params or StrategyParams()
        params = backtest_params or BacktestParams.realistic_cn_equity()
        super().__init__(params)

    def run(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        analyses_by_symbol: dict[str, list[DailyAnalysis]],
    ) -> PortfolioBacktestResult:
        params = self.backtest_params
        if not bars_by_symbol:
            return PortfolioBacktestResult(
                initial_capital=params.initial_capital,
                ending_equity=params.initial_capital,
                total_return=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                profit_factor=0.0,
            )

        index_by_symbol_date = {
            symbol: {bar.date: index for index, bar in enumerate(bars)}
            for symbol, bars in bars_by_symbol.items()
        }
        schedule_by_date: dict[str, list[PendingEntry]] = {}
        all_dates = sorted({bar.date for bars in bars_by_symbol.values() for bar in bars})
        latest_close_by_symbol: dict[str, float] = {}

        for symbol, analyses in analyses_by_symbol.items():
            bars = bars_by_symbol.get(symbol, [])
            if len(bars) < 2:
                continue
            limit = min(len(analyses), len(bars))
            for index in range(limit - 1):
                signal = analyses[index]
                if signal.label != "RECLAIM_LONG":
                    continue
                entry_bar = bars[index + 1]
                schedule_by_date.setdefault(entry_bar.date, []).append(
                    PendingEntry(symbol=symbol, bar_index=index + 1, source_signal=signal)
                )

        cash = params.initial_capital
        trades: list[Trade] = []
        equity_curve: list[EquityPoint] = []
        snapshots: list[PortfolioSnapshot] = []
        open_positions: dict[str, OpenPosition] = {}
        max_concurrent_positions = 0

        for current_date in all_dates:
            current_bars: dict[str, PriceBar] = {}
            current_analyses: dict[str, DailyAnalysis] = {}
            current_indices: dict[str, int] = {}
            for symbol, bars in bars_by_symbol.items():
                bar_index = index_by_symbol_date[symbol].get(current_date)
                if bar_index is None:
                    continue
                current_bars[symbol] = bars[bar_index]
                current_indices[symbol] = bar_index
                latest_close_by_symbol[symbol] = bars[bar_index].close
                analyses = analyses_by_symbol.get(symbol, [])
                if bar_index < len(analyses):
                    current_analyses[symbol] = analyses[bar_index]

            for symbol in sorted(list(open_positions)):
                position = open_positions[symbol]
                bar = current_bars.get(symbol)
                analysis = current_analyses.get(symbol)
                index = current_indices.get(symbol)
                if bar is None or analysis is None or index is None:
                    continue
                hold_days = index - position.entry_index + 1
                exit_decision = self._resolve_exit(
                    position=position,
                    bar=bar,
                    analysis=analysis,
                    hold_days=hold_days,
                )
                if exit_decision is None:
                    continue
                exit_price, exit_reason = exit_decision
                cash, trade = self._close_position(
                    position=position,
                    exit_date=bar.date,
                    exit_price=exit_price,
                    exit_reason=exit_reason,
                    cash=cash,
                )
                trades.append(
                    Trade(
                        symbol=trade.symbol,
                        entry_date=trade.entry_date,
                        exit_date=trade.exit_date,
                        entry_price=trade.entry_price,
                        exit_price=trade.exit_price,
                        shares=trade.shares,
                        pnl=trade.pnl,
                        pnl_pct=trade.pnl_pct,
                        hold_days=hold_days,
                        exit_reason=trade.exit_reason,
                    )
                )
                del open_positions[symbol]

            candidates = sorted(
                schedule_by_date.get(current_date, []),
                key=lambda item: (
                    int(item.source_signal.score or 0),
                    self._estimated_risk_reward_ratio(item.source_signal),
                    item.symbol,
                ),
                reverse=True,
            )
            max_positions = max(int(params.max_positions or 0), 1)
            for candidate in candidates:
                if len(open_positions) >= max_positions:
                    break
                if candidate.symbol in open_positions:
                    continue
                bar = current_bars.get(candidate.symbol)
                if bar is None:
                    continue
                signal = candidate.source_signal
                if signal.stop_price is None or signal.target_price is None:
                    continue
                current_equity = cash + sum(
                    position.shares * latest_close_by_symbol.get(symbol, position.entry_price)
                    for symbol, position in open_positions.items()
                )
                entry_price = self._resolve_entry_price(signal, bar)
                if entry_price is None:
                    continue
                shares = self._position_size_shares(
                    entry_price=entry_price,
                    stop_price=signal.stop_price,
                    cash=cash,
                    equity=current_equity,
                    bar=bar,
                )
                if shares < max(int(params.lot_size or 0), 1):
                    continue
                cash, position = self._open_position(
                    symbol=candidate.symbol,
                    bar_index=candidate.bar_index,
                    bar=bar,
                    entry_price=entry_price,
                    stop_price=signal.stop_price,
                    target_price=signal.target_price,
                    shares=shares,
                    cash=cash,
                )
                open_positions[candidate.symbol] = position

            market_value = sum(
                position.shares * latest_close_by_symbol.get(symbol, position.entry_price)
                for symbol, position in open_positions.items()
            )
            total_equity = cash + market_value
            exposure_ratio = (market_value / total_equity) if total_equity > 0 else 0.0
            equity_curve.append(EquityPoint(date=current_date, equity=round(total_equity, 2)))
            snapshots.append(
                PortfolioSnapshot(
                    date=current_date,
                    cash=round(cash, 2),
                    market_value=round(market_value, 2),
                    total_equity=round(total_equity, 2),
                    position_count=len(open_positions),
                    exposure_ratio=round(exposure_ratio, 4),
                )
            )
            max_concurrent_positions = max(max_concurrent_positions, len(open_positions))

        if open_positions:
            for symbol, position in list(open_positions.items()):
                bars = bars_by_symbol.get(symbol, [])
                if not bars:
                    continue
                last_bar = bars[-1]
                hold_days = len(bars) - position.entry_index
                exit_price = last_bar.close * (1.0 - params.slippage_rate)
                cash, trade = self._close_position(
                    position=position,
                    exit_date=last_bar.date,
                    exit_price=exit_price,
                    exit_reason="样本结束平仓",
                    cash=cash,
                )
                trades.append(
                    Trade(
                        symbol=trade.symbol,
                        entry_date=trade.entry_date,
                        exit_date=trade.exit_date,
                        entry_price=trade.entry_price,
                        exit_price=trade.exit_price,
                        shares=trade.shares,
                        pnl=trade.pnl,
                        pnl_pct=trade.pnl_pct,
                        hold_days=hold_days,
                        exit_reason=trade.exit_reason,
                    )
                )
                del open_positions[symbol]
            if equity_curve and snapshots:
                final_date = all_dates[-1]
                equity_curve[-1] = EquityPoint(date=final_date, equity=round(cash, 2))
                snapshots[-1] = PortfolioSnapshot(
                    date=final_date,
                    cash=round(cash, 2),
                    market_value=0.0,
                    total_equity=round(cash, 2),
                    position_count=0,
                    exposure_ratio=0.0,
                )

        ending_equity = equity_curve[-1].equity if equity_curve else params.initial_capital
        base_result = self._build_backtest_result(
            initial_capital=params.initial_capital,
            ending_equity=ending_equity,
            trades=trades,
            equity_curve=equity_curve,
        )
        avg_exposure = round(
            sum(snapshot.exposure_ratio for snapshot in snapshots) / len(snapshots),
            4,
        ) if snapshots else 0.0
        return PortfolioBacktestResult(
            initial_capital=base_result.initial_capital,
            ending_equity=base_result.ending_equity,
            total_return=base_result.total_return,
            max_drawdown=base_result.max_drawdown,
            win_rate=base_result.win_rate,
            profit_factor=base_result.profit_factor,
            avg_exposure=avg_exposure,
            max_concurrent_positions=max_concurrent_positions,
            trades=trades,
            equity_curve=equity_curve,
            snapshots=snapshots,
        )


def summarize_symbol_result(symbol: str, result: BacktestResult) -> SymbolBacktestSummary:
    return SymbolBacktestSummary(
        symbol=symbol,
        trades=len(result.trades),
        total_return=result.total_return,
        max_drawdown=result.max_drawdown,
        win_rate=result.win_rate,
        ending_equity=result.ending_equity,
    )


def format_result(result: BacktestResult) -> str:
    hold_days = fmean([trade.hold_days for trade in result.trades]) if result.trades else 0.0
    profit_factor = result.profit_factor if result.profit_factor != float("inf") else "无穷大"
    return "\n".join(
        [
            f"初始资金：{result.initial_capital:,.2f}",
            f"期末权益：{result.ending_equity:,.2f}",
            f"总收益率：{result.total_return:.2%}",
            f"最大回撤：{result.max_drawdown:.2%}",
            f"胜率：{result.win_rate:.2%}",
            f"盈亏因子：{profit_factor}",
            f"交易次数：{len(result.trades)}",
            f"平均持有天数：{hold_days:.2f}",
        ]
    )


def format_portfolio_result(result: PortfolioBacktestResult) -> str:
    hold_days = fmean([trade.hold_days for trade in result.trades]) if result.trades else 0.0
    profit_factor = result.profit_factor if result.profit_factor != float("inf") else "无穷大"
    return "\n".join(
        [
            f"组合初始资金：{result.initial_capital:,.2f}",
            f"组合期末权益：{result.ending_equity:,.2f}",
            f"组合总收益率：{result.total_return:.2%}",
            f"组合最大回撤：{result.max_drawdown:.2%}",
            f"组合胜率：{result.win_rate:.2%}",
            f"组合盈亏因子：{profit_factor}",
            f"平均仓位暴露：{result.avg_exposure:.2%}",
            f"最大并发持仓：{result.max_concurrent_positions}",
            f"平均持有天数：{hold_days:.2f}",
        ]
    )
