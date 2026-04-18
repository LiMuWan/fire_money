from __future__ import annotations

import itertools
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import median, pstdev

from .backtest import BacktestParams, Backtester, PortfolioBacktester
from .models import BacktestResult, OptimizationRun, PortfolioBacktestResult, PriceBar, ReportArtifacts
from .reports import export_optimization_report
from .strategy import AntiHarvestStrategy, StrategyParams


DEFAULT_GRID: dict[str, list[float | int]] = {
    "breakout_lookback": [15, 20, 25],
    "min_volume_ratio": [1.6, 1.8, 2.0],
    "max_reclaim_volume_ratio": [0.8, 0.85, 0.9],
    "stop_atr_multiple": [1.0, 1.2, 1.4],
    "target_atr_multiple": [2.0, 2.4, 2.8],
}


@dataclass(frozen=True)
class OptimizationWindowEvaluation:
    label: str
    total_return: float
    max_drawdown: float
    win_rate: float
    profit_factor: float
    trade_count: int


@dataclass(frozen=True)
class OptimizationSymbolEvaluation:
    total_return: float
    max_drawdown: float
    win_rate: float
    trade_count: int
    profit_factor: float
    out_of_sample_return: float
    median_window_return: float
    worst_window_return: float
    return_std: float
    positive_window_ratio: float


@dataclass(frozen=True)
class OptimizationPortfolioEvaluation:
    total_return: float
    max_drawdown: float
    profit_factor: float
    avg_exposure: float
    max_concurrent_positions: int
    out_of_sample_return: float
    worst_window_return: float
    return_std: float
    positive_window_ratio: float


class ParameterOptimizer:
    def __init__(self, base_params: StrategyParams | None = None) -> None:
        self.base_params = base_params or StrategyParams()

    @staticmethod
    def _minimum_bars_required(params: StrategyParams) -> int:
        return max(params.breakout_lookback, params.slow_ma_window) + 2

    @staticmethod
    def _cap_profit_factor(value: float) -> float:
        if value == float("inf"):
            return 5.0
        return max(0.0, min(value, 5.0))

    @staticmethod
    def _bounded_return_score(value: float, *, floor: float = -0.08, ceiling: float = 0.12) -> float:
        if ceiling <= floor:
            return 0.0
        clipped = max(floor, min(value, ceiling))
        return (clipped - floor) / (ceiling - floor)

    def _run_backtest(self, bars: list[PriceBar], params: StrategyParams) -> BacktestResult:
        strategy = AntiHarvestStrategy(params)
        analyses = strategy.analyze(bars)
        return Backtester(strategy_params=params).run(bars, analyses)

    def _analyze_universe(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        params: StrategyParams,
    ) -> dict[str, list[object]]:
        strategy = AntiHarvestStrategy(params)
        return {symbol: strategy.analyze(bars) for symbol, bars in bars_by_symbol.items()}

    def _portfolio_backtest_params(self, symbol_count: int) -> BacktestParams:
        max_positions = min(max(symbol_count, 1), 5)
        max_position_fraction = 0.42 if symbol_count <= 1 else 0.22
        return BacktestParams.realistic_cn_equity(
            max_positions=max_positions,
            max_position_fraction=max_position_fraction,
            max_volume_participation=0.12,
        )

    def _run_portfolio_backtest(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        params: StrategyParams,
    ) -> PortfolioBacktestResult | None:
        minimum = self._minimum_bars_required(params)
        eligible_bars = {symbol: list(bars) for symbol, bars in bars_by_symbol.items() if len(bars) >= minimum}
        if not eligible_bars:
            return None
        analyses_by_symbol = self._analyze_universe(eligible_bars, params)
        backtester = PortfolioBacktester(
            strategy_params=params,
            backtest_params=self._portfolio_backtest_params(len(eligible_bars)),
        )
        return backtester.run(eligible_bars, analyses_by_symbol)

    def _build_regime_windows(
        self,
        bars: list[PriceBar],
        params: StrategyParams,
    ) -> list[tuple[str, list[PriceBar]]]:
        minimum = self._minimum_bars_required(params)
        if len(bars) < minimum + 2:
            return []

        windows: list[tuple[str, list[PriceBar]]] = []
        if len(bars) < minimum * 3:
            window_size = max(minimum, int(len(bars) * 0.65))
            first_window = bars[:window_size]
            last_window = bars[-window_size:]
            if len(first_window) >= minimum:
                windows.append(("regime_1", first_window))
            if (
                len(last_window) >= minimum
                and (first_window[0].date != last_window[0].date or len(first_window) != len(last_window))
            ):
                windows.append(("out_of_sample_tail", last_window))
            return windows

        desired_segments = 3
        base_segment_size = len(bars) // desired_segments
        start = 0
        for index in range(desired_segments):
            end = len(bars) if index == desired_segments - 1 else start + base_segment_size
            segment = bars[start:end]
            if len(segment) >= minimum:
                label = "out_of_sample_tail" if index == desired_segments - 1 else f"regime_{index + 1}"
                windows.append((label, segment))
            start = end
        return windows

    def _slice_universe_window(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        *,
        start_ratio: float,
        end_ratio: float,
        minimum: int,
    ) -> dict[str, list[PriceBar]]:
        sliced: dict[str, list[PriceBar]] = {}
        for symbol, bars in bars_by_symbol.items():
            if len(bars) < minimum:
                continue
            start = max(0, min(int(len(bars) * start_ratio), len(bars) - minimum))
            end = len(bars) if end_ratio >= 1.0 else int(len(bars) * end_ratio)
            end = max(end, start + minimum)
            segment = bars[start:min(end, len(bars))]
            if len(segment) >= minimum:
                sliced[symbol] = segment
        return sliced

    def _build_portfolio_windows(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        params: StrategyParams,
    ) -> list[tuple[str, dict[str, list[PriceBar]]]]:
        minimum = self._minimum_bars_required(params)
        eligible = {symbol: bars for symbol, bars in bars_by_symbol.items() if len(bars) >= minimum + 2}
        if not eligible:
            return []

        average_length = sum(len(bars) for bars in eligible.values()) / max(len(eligible), 1)
        windows: list[tuple[str, dict[str, list[PriceBar]]]] = []
        if average_length < minimum * 3:
            first_window = self._slice_universe_window(eligible, start_ratio=0.0, end_ratio=0.65, minimum=minimum)
            tail_window = self._slice_universe_window(eligible, start_ratio=0.35, end_ratio=1.0, minimum=minimum)
            if first_window:
                windows.append(("regime_1", first_window))
            if tail_window and any(
                len(tail_window.get(symbol, [])) != len(first_window.get(symbol, [])) or tail_window.get(symbol, [None])[0] != first_window.get(symbol, [None])[0]
                for symbol in tail_window
            ):
                windows.append(("out_of_sample_tail", tail_window))
            return windows

        spans = (
            ("regime_1", 0.0, 0.34),
            ("regime_2", 0.33, 0.67),
            ("out_of_sample_tail", 0.66, 1.0),
        )
        for label, start_ratio, end_ratio in spans:
            window = self._slice_universe_window(eligible, start_ratio=start_ratio, end_ratio=end_ratio, minimum=minimum)
            if window:
                windows.append((label, window))
        return windows

    def _evaluate_symbol(
        self,
        bars: list[PriceBar],
        params: StrategyParams,
    ) -> OptimizationSymbolEvaluation | None:
        minimum = self._minimum_bars_required(params)
        if len(bars) < minimum:
            return None

        full_result = self._run_backtest(bars, params)
        window_results: list[OptimizationWindowEvaluation] = []
        for label, window in self._build_regime_windows(bars, params):
            result = self._run_backtest(window, params)
            window_results.append(
                OptimizationWindowEvaluation(
                    label=label,
                    total_return=result.total_return,
                    max_drawdown=result.max_drawdown,
                    win_rate=result.win_rate,
                    profit_factor=result.profit_factor,
                    trade_count=len(result.trades),
                )
            )

        if window_results:
            window_returns = [item.total_return for item in window_results]
            out_of_sample_return = next(
                (item.total_return for item in window_results if item.label == "out_of_sample_tail"),
                window_results[-1].total_return,
            )
            median_window_return = median(window_returns)
            worst_window_return = min(window_returns)
            return_std = pstdev(window_returns) if len(window_returns) >= 2 else 0.0
            positive_window_ratio = sum(1 for value in window_returns if value > 0) / len(window_returns)
        else:
            out_of_sample_return = full_result.total_return
            median_window_return = full_result.total_return
            worst_window_return = full_result.total_return
            return_std = 0.0
            positive_window_ratio = 1.0 if full_result.total_return > 0 else 0.0

        return OptimizationSymbolEvaluation(
            total_return=full_result.total_return,
            max_drawdown=full_result.max_drawdown,
            win_rate=full_result.win_rate,
            trade_count=len(full_result.trades),
            profit_factor=self._cap_profit_factor(full_result.profit_factor),
            out_of_sample_return=out_of_sample_return,
            median_window_return=median_window_return,
            worst_window_return=worst_window_return,
            return_std=return_std,
            positive_window_ratio=positive_window_ratio,
        )

    def _evaluate_portfolio(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        params: StrategyParams,
    ) -> OptimizationPortfolioEvaluation | None:
        full_result = self._run_portfolio_backtest(bars_by_symbol, params)
        if full_result is None:
            return None

        window_results: list[tuple[str, PortfolioBacktestResult]] = []
        for label, window_bars in self._build_portfolio_windows(bars_by_symbol, params):
            result = self._run_portfolio_backtest(window_bars, params)
            if result is not None:
                window_results.append((label, result))

        if window_results:
            window_returns = [item.total_return for _, item in window_results]
            out_of_sample_return = next(
                (item.total_return for label, item in window_results if label == "out_of_sample_tail"),
                window_results[-1][1].total_return,
            )
            worst_window_return = min(window_returns)
            return_std = pstdev(window_returns) if len(window_returns) >= 2 else 0.0
            positive_window_ratio = sum(1 for value in window_returns if value > 0) / len(window_returns)
        else:
            out_of_sample_return = full_result.total_return
            worst_window_return = full_result.total_return
            return_std = 0.0
            positive_window_ratio = 1.0 if full_result.total_return > 0 else 0.0

        return OptimizationPortfolioEvaluation(
            total_return=full_result.total_return,
            max_drawdown=full_result.max_drawdown,
            profit_factor=self._cap_profit_factor(full_result.profit_factor),
            avg_exposure=full_result.avg_exposure,
            max_concurrent_positions=full_result.max_concurrent_positions,
            out_of_sample_return=out_of_sample_return,
            worst_window_return=worst_window_return,
            return_std=return_std,
            positive_window_ratio=positive_window_ratio,
        )

    def _robustness_score(
        self,
        *,
        avg_drawdown: float,
        avg_out_of_sample_return: float,
        avg_worst_window_return: float,
        avg_return_std: float,
        avg_positive_window_ratio: float,
    ) -> float:
        oos_score = self._bounded_return_score(avg_out_of_sample_return)
        worst_window_score = self._bounded_return_score(avg_worst_window_return)
        dispersion_score = max(0.0, 1.0 - min(avg_return_std / 0.12, 1.0))
        drawdown_score = max(0.0, 1.0 - min(avg_drawdown / 0.18, 1.0))
        robustness = (
            avg_positive_window_ratio * 0.35
            + worst_window_score * 0.25
            + oos_score * 0.2
            + dispersion_score * 0.1
            + drawdown_score * 0.1
        )
        return round(max(0.0, min(robustness, 1.0)), 4)

    def _score_candidate(
        self,
        evaluations: list[OptimizationSymbolEvaluation],
        portfolio_evaluation: OptimizationPortfolioEvaluation | None,
        symbols_tested: int,
    ) -> tuple[float, dict[str, float | int]]:
        avg_return = sum(item.total_return for item in evaluations) / symbols_tested
        avg_drawdown = sum(item.max_drawdown for item in evaluations) / symbols_tested
        avg_win_rate = sum(item.win_rate for item in evaluations) / symbols_tested
        avg_out_of_sample_return = sum(item.out_of_sample_return for item in evaluations) / symbols_tested
        avg_median_window_return = sum(item.median_window_return for item in evaluations) / symbols_tested
        avg_worst_window_return = sum(item.worst_window_return for item in evaluations) / symbols_tested
        avg_return_std = sum(item.return_std for item in evaluations) / symbols_tested
        avg_positive_window_ratio = sum(item.positive_window_ratio for item in evaluations) / symbols_tested
        avg_profit_factor = sum(item.profit_factor for item in evaluations) / symbols_tested
        total_trades = sum(item.trade_count for item in evaluations)

        portfolio_return = portfolio_evaluation.total_return if portfolio_evaluation is not None else avg_return
        portfolio_oos_return = portfolio_evaluation.out_of_sample_return if portfolio_evaluation is not None else avg_out_of_sample_return
        portfolio_worst_window_return = portfolio_evaluation.worst_window_return if portfolio_evaluation is not None else avg_worst_window_return
        portfolio_return_std = portfolio_evaluation.return_std if portfolio_evaluation is not None else avg_return_std
        portfolio_drawdown = portfolio_evaluation.max_drawdown if portfolio_evaluation is not None else avg_drawdown
        portfolio_profit_factor = portfolio_evaluation.profit_factor if portfolio_evaluation is not None else avg_profit_factor
        portfolio_avg_exposure = portfolio_evaluation.avg_exposure if portfolio_evaluation is not None else 0.0
        portfolio_max_concurrent_positions = portfolio_evaluation.max_concurrent_positions if portfolio_evaluation is not None else 0
        portfolio_positive_window_ratio = (
            portfolio_evaluation.positive_window_ratio if portfolio_evaluation is not None else avg_positive_window_ratio
        )

        symbol_trade_penalty = max(0.0, 2.5 - (total_trades / symbols_tested)) * 0.03
        deployment_penalty = max(0.0, 0.14 - portfolio_avg_exposure) * 0.08
        objective = (
            avg_return * 0.08
            + avg_out_of_sample_return * 0.18
            + avg_median_window_return * 0.12
            + avg_worst_window_return * 0.1
            + avg_win_rate * 0.05
            + avg_positive_window_ratio * 0.04
            + portfolio_return * 0.18
            + portfolio_oos_return * 0.2
            + portfolio_worst_window_return * 0.13
            + portfolio_profit_factor * 0.01
            - avg_drawdown * 0.6
            - avg_return_std * 0.18
            - portfolio_drawdown * 0.95
            - portfolio_return_std * 0.32
            - symbol_trade_penalty
            - deployment_penalty
        )
        symbol_robustness = self._robustness_score(
            avg_drawdown=avg_drawdown,
            avg_out_of_sample_return=avg_out_of_sample_return,
            avg_worst_window_return=avg_worst_window_return,
            avg_return_std=avg_return_std,
            avg_positive_window_ratio=avg_positive_window_ratio,
        )
        portfolio_robustness = self._robustness_score(
            avg_drawdown=portfolio_drawdown,
            avg_out_of_sample_return=portfolio_oos_return,
            avg_worst_window_return=portfolio_worst_window_return,
            avg_return_std=portfolio_return_std,
            avg_positive_window_ratio=portfolio_positive_window_ratio,
        )
        robustness_score = round(symbol_robustness * 0.55 + portfolio_robustness * 0.45, 4)
        return objective, {
            "avg_return": round(avg_return, 6),
            "avg_drawdown": round(avg_drawdown, 6),
            "avg_win_rate": round(avg_win_rate, 6),
            "trade_count": total_trades,
            "robustness_score": robustness_score,
            "avg_out_of_sample_return": round(avg_out_of_sample_return, 6),
            "avg_median_window_return": round(avg_median_window_return, 6),
            "avg_worst_window_return": round(avg_worst_window_return, 6),
            "avg_return_std": round(avg_return_std, 6),
            "avg_positive_window_ratio": round(avg_positive_window_ratio, 6),
            "avg_profit_factor": round(avg_profit_factor, 6),
            "portfolio_return": round(portfolio_return, 6),
            "portfolio_out_of_sample_return": round(portfolio_oos_return, 6),
            "portfolio_worst_window_return": round(portfolio_worst_window_return, 6),
            "portfolio_return_std": round(portfolio_return_std, 6),
            "portfolio_max_drawdown": round(portfolio_drawdown, 6),
            "portfolio_profit_factor": round(portfolio_profit_factor, 6),
            "portfolio_avg_exposure": round(portfolio_avg_exposure, 6),
            "portfolio_max_concurrent_positions": int(portfolio_max_concurrent_positions),
        }

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
            evaluations: list[OptimizationSymbolEvaluation] = []

            for bars in bars_by_symbol.values():
                evaluation = self._evaluate_symbol(bars, params)
                if evaluation is not None:
                    evaluations.append(evaluation)

            symbols_tested = len(evaluations)
            if symbols_tested == 0:
                continue

            portfolio_evaluation = self._evaluate_portfolio(bars_by_symbol, params)
            objective, metrics = self._score_candidate(evaluations, portfolio_evaluation, symbols_tested)
            results.append(
                OptimizationRun(
                    rank=0,
                    params=overrides,
                    objective=round(objective, 6),
                    avg_return=float(metrics["avg_return"]),
                    avg_drawdown=float(metrics["avg_drawdown"]),
                    avg_win_rate=float(metrics["avg_win_rate"]),
                    trade_count=int(metrics["trade_count"]),
                    symbols_tested=symbols_tested,
                    robustness_score=float(metrics["robustness_score"]),
                    avg_out_of_sample_return=float(metrics["avg_out_of_sample_return"]),
                    avg_median_window_return=float(metrics["avg_median_window_return"]),
                    avg_worst_window_return=float(metrics["avg_worst_window_return"]),
                    avg_return_std=float(metrics["avg_return_std"]),
                    avg_positive_window_ratio=float(metrics["avg_positive_window_ratio"]),
                    avg_profit_factor=float(metrics["avg_profit_factor"]),
                    portfolio_return=float(metrics["portfolio_return"]),
                    portfolio_out_of_sample_return=float(metrics["portfolio_out_of_sample_return"]),
                    portfolio_worst_window_return=float(metrics["portfolio_worst_window_return"]),
                    portfolio_return_std=float(metrics["portfolio_return_std"]),
                    portfolio_max_drawdown=float(metrics["portfolio_max_drawdown"]),
                    portfolio_profit_factor=float(metrics["portfolio_profit_factor"]),
                    portfolio_avg_exposure=float(metrics["portfolio_avg_exposure"]),
                    portfolio_max_concurrent_positions=int(metrics["portfolio_max_concurrent_positions"]),
                )
            )

        results.sort(
            key=lambda item: (
                item.objective,
                item.robustness_score,
                item.portfolio_out_of_sample_return,
                item.portfolio_return,
                item.portfolio_worst_window_return,
                item.avg_out_of_sample_return,
                item.avg_return,
            ),
            reverse=True,
        )
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
                robustness_score=item.robustness_score,
                avg_out_of_sample_return=item.avg_out_of_sample_return,
                avg_median_window_return=item.avg_median_window_return,
                avg_worst_window_return=item.avg_worst_window_return,
                avg_return_std=item.avg_return_std,
                avg_positive_window_ratio=item.avg_positive_window_ratio,
                avg_profit_factor=item.avg_profit_factor,
                portfolio_return=item.portfolio_return,
                portfolio_out_of_sample_return=item.portfolio_out_of_sample_return,
                portfolio_worst_window_return=item.portfolio_worst_window_return,
                portfolio_return_std=item.portfolio_return_std,
                portfolio_max_drawdown=item.portfolio_max_drawdown,
                portfolio_profit_factor=item.portfolio_profit_factor,
                portfolio_avg_exposure=item.portfolio_avg_exposure,
                portfolio_max_concurrent_positions=item.portfolio_max_concurrent_positions,
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
