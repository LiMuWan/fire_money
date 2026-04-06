from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .models import BacktestResult, DailyAnalysis, EquityPoint, PriceBar, SymbolBacktestSummary, Trade
from .strategy import StrategyParams


@dataclass
class PendingEntry:
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


@dataclass(frozen=True)
class BacktestParams:
    initial_capital: float = 200000.0
    risk_fraction: float = 0.01
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0005
    max_hold_days: int = 8
    lot_size: int = 100


class Backtester:
    def __init__(
        self,
        strategy_params: StrategyParams | None = None,
        backtest_params: BacktestParams | None = None,
    ) -> None:
        self.strategy_params = strategy_params or StrategyParams()
        self.backtest_params = backtest_params or BacktestParams()

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
                if source.stop_price is not None and source.target_price is not None:
                    entry_price = bar.open * (1 + params.slippage_rate)
                    risk_per_share = max(entry_price - source.stop_price, 0.01)
                    risk_budget = equity * params.risk_fraction
                    max_by_risk = int(risk_budget / risk_per_share)
                    max_by_cash = int(cash / entry_price)
                    shares = min(max_by_risk, max_by_cash)
                    shares = (shares // params.lot_size) * params.lot_size
                    if shares >= params.lot_size:
                        cost = shares * entry_price
                        fee = cost * params.commission_rate
                        cash -= cost + fee
                        position = OpenPosition(
                            symbol=bar.symbol,
                            entry_date=bar.date,
                            entry_index=index,
                            entry_price=entry_price,
                            shares=shares,
                            stop_price=source.stop_price,
                            target_price=source.target_price,
                        )
                pending_entry = None

            if position:
                exit_price = None
                exit_reason = ""
                hold_days = index - position.entry_index + 1

                if bar.low <= position.stop_price:
                    exit_price = position.stop_price * (1 - params.slippage_rate)
                    exit_reason = "跌破止损"
                elif bar.high >= position.target_price:
                    exit_price = position.target_price * (1 - params.slippage_rate)
                    exit_reason = "达到目标位"
                elif hold_days >= params.max_hold_days:
                    exit_price = bar.close * (1 - params.slippage_rate)
                    exit_reason = "超过持有天数"
                elif analyses[index].label == "TRAP_DETECTED":
                    exit_price = bar.close * (1 - params.slippage_rate)
                    exit_reason = "再次出现诱多陷阱"
                elif bar.close < analyses[index].ma_slow:
                    exit_price = bar.close * (1 - params.slippage_rate)
                    exit_reason = "失守慢线"

                if exit_price is not None:
                    proceeds = position.shares * exit_price
                    fee = proceeds * params.commission_rate
                    cash += proceeds - fee
                    pnl = (exit_price - position.entry_price) * position.shares - (
                        (position.entry_price * position.shares + proceeds) * params.commission_rate
                    )
                    pnl_pct = pnl / (position.entry_price * position.shares)
                    trades.append(
                        Trade(
                            symbol=position.symbol,
                            entry_date=position.entry_date,
                            exit_date=bar.date,
                            entry_price=round(position.entry_price, 3),
                            exit_price=round(exit_price, 3),
                            shares=position.shares,
                            pnl=round(pnl, 2),
                            pnl_pct=round(pnl_pct, 4),
                            hold_days=hold_days,
                            exit_reason=exit_reason,
                        )
                    )
                    position = None

            signal = analyses[index]
            if signal.label == "RECLAIM_LONG" and index + 1 < len(bars) and position is None:
                pending_entry = PendingEntry(bar_index=index + 1, source_signal=signal)

            market_value = position.shares * bar.close if position else 0.0
            equity = cash + market_value
            equity_curve.append(EquityPoint(date=bar.date, equity=round(equity, 2)))

        if position:
            last_bar = bars[-1]
            exit_price = last_bar.close * (1 - params.slippage_rate)
            proceeds = position.shares * exit_price
            fee = proceeds * params.commission_rate
            cash += proceeds - fee
            pnl = (exit_price - position.entry_price) * position.shares - (
                (position.entry_price * position.shares + proceeds) * params.commission_rate
            )
            pnl_pct = pnl / (position.entry_price * position.shares)
            trades.append(
                Trade(
                    symbol=position.symbol,
                    entry_date=position.entry_date,
                    exit_date=last_bar.date,
                    entry_price=round(position.entry_price, 3),
                    exit_price=round(exit_price, 3),
                    shares=position.shares,
                    pnl=round(pnl, 2),
                    pnl_pct=round(pnl_pct, 4),
                    hold_days=len(bars) - position.entry_index,
                    exit_reason="样本结束平仓",
                )
            )
            equity = cash
            equity_curve[-1] = EquityPoint(date=last_bar.date, equity=round(equity, 2))

        ending_equity = equity_curve[-1].equity if equity_curve else params.initial_capital
        wins = [trade for trade in trades if trade.pnl > 0]
        losses = [trade for trade in trades if trade.pnl < 0]
        gross_profit = sum(trade.pnl for trade in wins)
        gross_loss = abs(sum(trade.pnl for trade in losses))
        peak = params.initial_capital
        max_drawdown = 0.0
        for point in equity_curve:
            peak = max(peak, point.equity)
            if peak:
                max_drawdown = max(max_drawdown, (peak - point.equity) / peak)

        return BacktestResult(
            initial_capital=params.initial_capital,
            ending_equity=round(ending_equity, 2),
            total_return=round((ending_equity - params.initial_capital) / params.initial_capital, 4),
            max_drawdown=round(max_drawdown, 4),
            win_rate=round(len(wins) / len(trades), 4) if trades else 0.0,
            profit_factor=round(gross_profit / gross_loss, 4) if gross_loss else float("inf"),
            trades=trades,
            equity_curve=equity_curve,
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
