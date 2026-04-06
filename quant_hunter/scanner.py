from __future__ import annotations

from pathlib import Path

from .backtest import Backtester
from .data import discover_csv_files, extract_stock_id, load_bars_from_csv
from .models import DailyAnalysis, PriceBar, ScanRow, SymbolBacktestSummary
from .strategy import AntiHarvestStrategy, StrategyParams


ACTION_MAP = {
    "RECLAIM_LONG": "BUY",
    "WATCH": "WATCH",
    "TRAP_DETECTED": "AVOID",
}


class UniverseScanner:
    def __init__(self, params: StrategyParams | None = None, recent_window: int = 5) -> None:
        self.params = params or StrategyParams()
        self.recent_window = recent_window
        self.strategy = AntiHarvestStrategy(self.params)

    def scan_folder(
        self, folder: str | Path
    ) -> tuple[list[ScanRow], dict[str, list[PriceBar]], dict[str, list[DailyAnalysis]], dict[str, Path]]:
        rows: list[ScanRow] = []
        bars_by_symbol: dict[str, list[PriceBar]] = {}
        analyses_by_symbol: dict[str, list[DailyAnalysis]] = {}
        paths_by_symbol: dict[str, Path] = {}

        for path in discover_csv_files(folder):
            try:
                bars = load_bars_from_csv(path, default_symbol=path.stem)
            except Exception:
                continue
            if not bars:
                continue
            symbol = bars[-1].symbol
            analyses = self.strategy.analyze(bars)
            selected = self._pick_recent_signal(analyses)
            if selected is not None:
                rows.append(
                    ScanRow(
                        symbol=symbol,
                        signal_date=selected.date,
                        label=selected.label,
                        action=ACTION_MAP.get(selected.label, "HOLD"),
                        score=selected.score,
                        close=selected.close,
                        entry_price=selected.entry_price,
                        stop_price=selected.stop_price,
                        target_price=selected.target_price,
                        reason=selected.reason,
                        source_path=str(path),
                        stock_id=extract_stock_id(symbol),
                    )
                )
            bars_by_symbol[symbol] = bars
            analyses_by_symbol[symbol] = analyses
            paths_by_symbol[symbol] = path

        rows.sort(key=lambda item: (item.score, item.signal_date, item.symbol), reverse=True)
        return rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol

    def summarize_backtests(
        self,
        bars_by_symbol: dict[str, list[PriceBar]],
        analyses_by_symbol: dict[str, list[DailyAnalysis]],
    ) -> list[SymbolBacktestSummary]:
        summaries: list[SymbolBacktestSummary] = []
        backtester = Backtester(strategy_params=self.params)
        for symbol, bars in bars_by_symbol.items():
            result = backtester.run(bars, analyses_by_symbol[symbol])
            summaries.append(
                SymbolBacktestSummary(
                    symbol=symbol,
                    trades=len(result.trades),
                    total_return=result.total_return,
                    max_drawdown=result.max_drawdown,
                    win_rate=result.win_rate,
                    ending_equity=result.ending_equity,
                )
            )
        summaries.sort(key=lambda item: (item.total_return, item.win_rate, item.symbol), reverse=True)
        return summaries

    def _pick_recent_signal(self, analyses: list[DailyAnalysis]) -> DailyAnalysis | None:
        if not analyses:
            return None
        recent = [item for item in analyses[-self.recent_window :] if item.label != "NONE"]
        if recent:
            recent.sort(key=lambda item: (item.score, item.date), reverse=True)
            return recent[0]
        history = [item for item in analyses if item.label != "NONE"]
        return history[-1] if history else None
