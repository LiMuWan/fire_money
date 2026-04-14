from __future__ import annotations

import itertools
from dataclasses import asdict
from pathlib import Path

from .backtest import Backtester
from .models import OptimizationRun, PriceBar, ReportArtifacts
from .reports import export_optimization_report
from .strategy import AntiHarvestStrategy, StrategyParams


DEFAULT_GRID: dict[str, list[float | int]] = {
    "breakout_lookback": [15, 20, 25],
    "min_volume_ratio": [1.6, 1.8, 2.0],
    "max_reclaim_volume_ratio": [0.8, 0.85, 0.9],
    "stop_atr_multiple": [1.0, 1.2, 1.4],
    "target_atr_multiple": [2.0, 2.4, 2.8],
}


class ParameterOptimizer:
    def __init__(self, base_params: StrategyParams | None = None) -> None:
        self.base_params = base_params or StrategyParams()

    @staticmethod
    def _minimum_bars_required(params: StrategyParams) -> int:
        return max(params.breakout_lookback, params.slow_ma_window) + 2

    def _build_stability_windows(self, bars: list[PriceBar], params: StrategyParams) -> list[list[PriceBar]]:
        minimum = self._minimum_bars_required(params)
        if len(bars) < minimum * 2:
            return []

        midpoint = len(bars) // 2
        second_start = max(0, midpoint - (minimum - 1))
        windows = [bars[:midpoint], bars[second_start:]]
        return [window for window in windows if len(window) >= minimum]

    def _evaluate_symbol(self, bars: list[PriceBar], params: StrategyParams) -> tuple[float, float, float, int, float] | None:
        minimum = self._minimum_bars_required(params)
        if len(bars) < minimum:
            return None

        strategy = AntiHarvestStrategy(params)
        analyses = strategy.analyze(bars)
        result = Backtester(strategy_params=params).run(bars, analyses)

        window_returns: list[float] = []
        for window in self._build_stability_windows(bars, params):
            window_analyses = strategy.analyze(window)
            window_result = Backtester(strategy_params=params).run(window, window_analyses)
            window_returns.append(window_result.total_return)

        instability = max(window_returns) - min(window_returns) if len(window_returns) >= 2 else 0.0
        return result.total_return, result.max_drawdown, result.win_rate, len(result.trades), instability

    def optimize(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        grid: dict[str, list[float | int]] | None = None,
        top_n: int = 10,
    ) -> list[OptimizationRun]:
        if not bars_by_symbol:
            raise ValueError("没有可用于优化的股票池数据。")
        search_grid = grid or DEFAULT_GRID
        keys = list(search_grid.keys())
        results: list[OptimizationRun] = []

        for values in itertools.product(*(search_grid[key] for key in keys)):
            overrides = dict(zip(keys, values))
            params = self._merge_params(overrides)
            total_return = 0.0
            total_drawdown = 0.0
            total_win_rate = 0.0
            total_trades = 0
            total_instability = 0.0
            symbols_tested = 0

            for bars in bars_by_symbol.values():
                evaluation = self._evaluate_symbol(bars, params)
                if evaluation is None:
                    continue
                symbol_return, symbol_drawdown, symbol_win_rate, symbol_trades, symbol_instability = evaluation
                total_return += symbol_return
                total_drawdown += symbol_drawdown
                total_win_rate += symbol_win_rate
                total_trades += symbol_trades
                total_instability += symbol_instability
                symbols_tested += 1

            if symbols_tested == 0:
                continue

            avg_return = total_return / max(symbols_tested, 1)
            avg_drawdown = total_drawdown / max(symbols_tested, 1)
            avg_win_rate = total_win_rate / max(symbols_tested, 1)
            avg_instability = total_instability / max(symbols_tested, 1)
            trade_penalty = max(0.0, 2.0 - (total_trades / max(symbols_tested, 1))) * 0.03
            objective = avg_return - avg_drawdown * 0.9 + avg_win_rate * 0.12 - avg_instability * 0.35 - trade_penalty

            results.append(
                OptimizationRun(
                    rank=0,
                    params=overrides,
                    objective=round(objective, 6),
                    avg_return=round(avg_return, 6),
                    avg_drawdown=round(avg_drawdown, 6),
                    avg_win_rate=round(avg_win_rate, 6),
                    trade_count=total_trades,
                    symbols_tested=symbols_tested,
                )
            )

        results.sort(key=lambda item: (item.objective, item.avg_return, item.avg_win_rate), reverse=True)
        ranked = [
            OptimizationRun(
                rank=index + 1,
                params=item.params,
                objective=item.objective,
                avg_return=item.avg_return,
                avg_drawdown=item.avg_drawdown,
                avg_win_rate=item.avg_win_rate,
                trade_count=item.trade_count,
                symbols_tested=item.symbols_tested,
            )
            for index, item in enumerate(results[:top_n])
        ]
        return ranked

    def export_report(
        self,
        results: list[OptimizationRun],
        output_dir: str | Path,
        title: str = "参数优化报告",
    ) -> ReportArtifacts:
        return export_optimization_report(results, output_dir, title)

    def _merge_params(self, overrides: dict[str, float | int]) -> StrategyParams:
        data = asdict(self.base_params)
        data.update(overrides)
        return StrategyParams(**data)
