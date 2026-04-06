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
            symbols_tested = 0

            for bars in bars_by_symbol.values():
                analyses = AntiHarvestStrategy(params).analyze(bars)
                result = Backtester(strategy_params=params).run(bars, analyses)
                total_return += result.total_return
                total_drawdown += result.max_drawdown
                total_win_rate += result.win_rate
                total_trades += len(result.trades)
                symbols_tested += 1

            avg_return = total_return / max(symbols_tested, 1)
            avg_drawdown = total_drawdown / max(symbols_tested, 1)
            avg_win_rate = total_win_rate / max(symbols_tested, 1)
            objective = avg_return - avg_drawdown * 0.8 + avg_win_rate * 0.15

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
