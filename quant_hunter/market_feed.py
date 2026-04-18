from __future__ import annotations

import json
import math
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

from .backtest import BacktestParams, Backtester, PortfolioBacktester
from .data import extract_stock_id, normalize_symbol
from .models import DailyAnalysis, PriceBar, RecommendationRow, ScanRow, StockProfile, SymbolBacktestSummary
from .recommend import DailyPoolBuilder
from .scanner import ACTION_MAP
from .strategy import AntiHarvestStrategy, StrategyParams


EASTMONEY_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Referer": "https://quote.eastmoney.com/",
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}

TENCENT_HEADERS = {
    "User-Agent": EASTMONEY_HEADERS["User-Agent"],
    "Referer": "https://gu.qq.com/",
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MARKET_CACHE_DIR = PROJECT_ROOT / ".quant_hunter" / "cache" / "market"


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    stock_id: str
    stock_name: str
    latest_price: float
    pct_change: float
    change_amount: float
    turnover: float
    amount: float
    open_price: float
    high_price: float
    low_price: float
    prev_close: float
    main_inflow: float
    pe_ratio: float
    heat_score: float
    fund_model: str
    strategy_tag: str
    momentum_bias: float


@dataclass(frozen=True)
class AlgorithmicPoolRow:
    symbol: str
    stock_id: str
    stock_name: str
    theme_name: str
    latest_price: float
    pct_change: float
    main_inflow: float
    amount: float
    turnover: float
    heat_score: float
    fund_model: str
    strategy_tag: str
    decision_score: float
    signal_label: str
    action: str
    entry_price: float
    stop_price: float
    target_price: float
    rationale: str


@dataclass(frozen=True)
class SeriesPoint:
    t: str
    v: float


@dataclass(frozen=True)
class SymbolChartSeries:
    symbol: str
    intraday_price: list[SeriesPoint] = field(default_factory=list)
    intraday_trend: list[SeriesPoint] = field(default_factory=list)
    capital_flow: list[SeriesPoint] = field(default_factory=list)
    heat_momentum: list[SeriesPoint] = field(default_factory=list)


@dataclass(frozen=True)
class MarketScreenResult:
    market_name: str
    generated_at: str
    algorithmic_pool: list[AlgorithmicPoolRow] = field(default_factory=list)
    scan_rows: list[ScanRow] = field(default_factory=list)
    recommendations: list[RecommendationRow] = field(default_factory=list)
    bars_by_symbol: dict[str, list[PriceBar]] = field(default_factory=dict)
    analyses_by_symbol: dict[str, list[DailyAnalysis]] = field(default_factory=dict)
    summaries: list[SymbolBacktestSummary] = field(default_factory=list)
    snapshots: dict[str, MarketSnapshot] = field(default_factory=dict)
    chart_series_by_symbol: dict[str, SymbolChartSeries] = field(default_factory=dict)


class LocalMarketCache:
    def __init__(
        self,
        root: Path | None = None,
        snapshot_ttl_seconds: int = 20,
        bars_ttl_seconds: int = 1800,
    ) -> None:
        self.root = root or MARKET_CACHE_DIR
        self.snapshot_ttl_seconds = snapshot_ttl_seconds
        self.bars_ttl_seconds = bars_ttl_seconds
        self.root.mkdir(parents=True, exist_ok=True)

    def get_market_snapshots(self, limit: int, allow_stale: bool = False) -> list[MarketSnapshot]:
        payload = self._read_payload(self.root / f"snapshots_{limit}.json", self.snapshot_ttl_seconds, allow_stale)
        if payload is None:
            return []
        return [MarketSnapshot(**item) for item in payload]

    def put_market_snapshots(self, limit: int, snapshots: list[MarketSnapshot]) -> None:
        self._write_payload(self.root / f"snapshots_{limit}.json", [asdict(item) for item in snapshots])

    def get_screen_history(self, limit: int = 12) -> list[MarketScreenResult]:
        payload = self._read_payload(self.root / "screen_history.json", ttl_seconds=365 * 24 * 3600, allow_stale=True)
        if payload is None:
            return []
        results: list[MarketScreenResult] = []
        for item in payload[:limit]:
            try:
                results.append(self._screen_result_from_dict(item))
            except Exception:
                continue
        return results

    def put_screen_result(self, result: MarketScreenResult, max_entries: int = 12) -> None:
        if not result.generated_at:
            return
        history = [self._screen_result_to_dict(item) for item in self.get_screen_history(limit=max_entries * 2)]
        current = self._screen_result_to_dict(result)
        history = [item for item in history if item.get("generated_at") != result.generated_at]
        history.insert(0, current)
        history.sort(key=lambda item: item.get("generated_at", ""), reverse=True)
        self._write_payload(self.root / "screen_history.json", history[:max_entries])

    def get_daily_bars(self, symbol: str, allow_stale: bool = False) -> list[PriceBar]:
        stock_id = extract_stock_id(symbol)
        payload = self._read_payload(self.root / f"bars_{stock_id}.json", self.bars_ttl_seconds, allow_stale)
        if payload is None:
            return []
        return [PriceBar(**item) for item in payload]

    def put_daily_bars(self, symbol: str, bars: list[PriceBar]) -> None:
        stock_id = extract_stock_id(symbol)
        self._write_payload(self.root / f"bars_{stock_id}.json", [asdict(item) for item in bars])

    def cache_stats(self) -> dict[str, int]:
        files = list(self.root.glob("*.json"))
        return {
            "files": len(files),
            "bytes": sum(item.stat().st_size for item in files if item.exists()),
        }

    def clear(self) -> dict[str, int]:
        removed_files = 0
        removed_bytes = 0
        for path in self.root.glob("*.json"):
            try:
                file_size = path.stat().st_size if path.exists() else 0
                path.unlink(missing_ok=True)
                removed_files += 1
                removed_bytes += file_size
            except Exception:
                continue
        return {
            "files": removed_files,
            "bytes": removed_bytes,
        }

    def _read_payload(self, path: Path, ttl_seconds: int, allow_stale: bool) -> list[dict] | None:
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
        saved_at = float(payload.get("saved_at", 0.0) or 0.0)
        if not allow_stale and saved_at > 0 and (time.time() - saved_at) > ttl_seconds:
            return None
        data = payload.get("payload")
        return data if isinstance(data, list) else None

    def _write_payload(self, path: Path, payload: list[dict]) -> None:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps({"saved_at": time.time(), "payload": payload}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    @staticmethod
    def _screen_result_to_dict(result: MarketScreenResult) -> dict:
        return {
            "market_name": result.market_name,
            "generated_at": result.generated_at,
            "algorithmic_pool": [asdict(item) for item in result.algorithmic_pool],
            "scan_rows": [asdict(item) for item in result.scan_rows],
            "recommendations": [asdict(item) for item in result.recommendations],
            "bars_by_symbol": {
                symbol: [asdict(bar) for bar in bars]
                for symbol, bars in result.bars_by_symbol.items()
            },
            "analyses_by_symbol": {
                symbol: [asdict(analysis) for analysis in analyses]
                for symbol, analyses in result.analyses_by_symbol.items()
            },
            "summaries": [asdict(item) for item in result.summaries],
            "snapshots": {symbol: asdict(snapshot) for symbol, snapshot in result.snapshots.items()},
            "chart_series_by_symbol": {symbol: asdict(series) for symbol, series in result.chart_series_by_symbol.items()},
        }

    @staticmethod
    def _screen_result_from_dict(payload: dict) -> MarketScreenResult:
        return MarketScreenResult(
            market_name=str(payload.get("market_name", "") or ""),
            generated_at=str(payload.get("generated_at", "") or ""),
            algorithmic_pool=[AlgorithmicPoolRow(**item) for item in payload.get("algorithmic_pool", []) or []],
            scan_rows=[ScanRow(**item) for item in payload.get("scan_rows", []) or []],
            recommendations=[RecommendationRow(**item) for item in payload.get("recommendations", []) or []],
            bars_by_symbol={
                symbol: [PriceBar(**bar) for bar in bars]
                for symbol, bars in (payload.get("bars_by_symbol", {}) or {}).items()
            },
            analyses_by_symbol={
                symbol: [DailyAnalysis(**analysis) for analysis in analyses]
                for symbol, analyses in (payload.get("analyses_by_symbol", {}) or {}).items()
            },
            summaries=[SymbolBacktestSummary(**item) for item in payload.get("summaries", []) or []],
            snapshots={
                symbol: MarketSnapshot(**snapshot)
                for symbol, snapshot in (payload.get("snapshots", {}) or {}).items()
            },
            chart_series_by_symbol={
                symbol: SymbolChartSeries(
                    symbol=item.get("symbol", symbol),
                    intraday_price=[SeriesPoint(**point) for point in item.get("intraday_price", []) or []],
                    intraday_trend=[SeriesPoint(**point) for point in item.get("intraday_trend", []) or []],
                    capital_flow=[SeriesPoint(**point) for point in item.get("capital_flow", []) or []],
                    heat_momentum=[SeriesPoint(**point) for point in item.get("heat_momentum", []) or []],
                )
                for symbol, item in (payload.get("chart_series_by_symbol", {}) or {}).items()
            },
        )


class EastmoneyMarketFeed:
    def __init__(self, timeout: int = 15, cache: LocalMarketCache | None = None) -> None:
        self.timeout = timeout
        self.cache = cache or LocalMarketCache()
        self.last_snapshot_source = "unknown"
        self.last_snapshot_error = ""

    def fetch_market_snapshots(self, limit: int = 150) -> list[MarketSnapshot]:
        cached_snapshots = self.cache.get_market_snapshots(limit)
        if cached_snapshots:
            self.last_snapshot_source = "cache_fresh"
            self.last_snapshot_error = ""
            return cached_snapshots
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            + urllib.parse.urlencode(
                {
                    "pn": 1,
                    "pz": limit,
                    "po": 1,
                    "np": 1,
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                    "fltt": 2,
                    "invt": 2,
                    "fid": "f3",
                    "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
                    "fields": ",".join(
                        [
                            "f2",
                            "f3",
                            "f4",
                            "f5",
                            "f6",
                            "f8",
                            "f9",
                            "f12",
                            "f14",
                            "f15",
                            "f16",
                            "f17",
                            "f18",
                            "f22",
                            "f23",
                            "f24",
                            "f25",
                            "f62",
                            "f115",
                        ]
                    ),
                }
            )
        )
        try:
            payload = self._fetch_json(url)
            self.last_snapshot_source = "remote"
            self.last_snapshot_error = ""
        except Exception as exc:
            self.last_snapshot_error = str(exc)
            stale_snapshots = self.cache.get_market_snapshots(limit, allow_stale=True)
            if stale_snapshots:
                self.last_snapshot_source = "cache_stale"
                return stale_snapshots
            raise
        diff = payload.get("data", {}).get("diff", []) or []
        snapshots: list[MarketSnapshot] = []
        for item in diff:
            stock_id = str(item.get("f12", "") or "").strip()
            if len(stock_id) != 6:
                continue
            name = str(item.get("f14", "") or "").strip()
            if not name or "ST" in name.upper() or "退" in name:
                continue
            latest_price = self._safe_float(item.get("f2"))
            pct_change = self._safe_float(item.get("f3"))
            turnover = self._safe_float(item.get("f8"))
            amount = self._safe_float(item.get("f6"))
            high_price = self._safe_float(item.get("f15"))
            low_price = self._safe_float(item.get("f16"))
            open_price = self._safe_float(item.get("f17"))
            prev_close = self._safe_float(item.get("f18"))
            main_inflow = self._safe_float(item.get("f62"))
            pe_ratio = self._safe_float(item.get("f9"))
            if latest_price <= 0 or amount <= 0:
                continue
            symbol = normalize_symbol(stock_id)
            momentum_bias = self._momentum_bias(
                latest_price=latest_price,
                high_price=high_price,
                low_price=low_price,
                prev_close=prev_close,
            )
            heat_score = self._heat_score(
                pct_change=pct_change,
                turnover=turnover,
                amount=amount,
                main_inflow=main_inflow,
                momentum_bias=momentum_bias,
            )
            fund_model = self._fund_model(pct_change, turnover, main_inflow, amount)
            strategy_tag = self._strategy_tag(pct_change, turnover, main_inflow, momentum_bias)
            snapshots.append(
                MarketSnapshot(
                    symbol=symbol,
                    stock_id=stock_id,
                    stock_name=name,
                    latest_price=latest_price,
                    pct_change=pct_change,
                    change_amount=self._safe_float(item.get("f4")),
                    turnover=turnover,
                    amount=amount,
                    open_price=open_price,
                    high_price=high_price,
                    low_price=low_price,
                    prev_close=prev_close,
                    main_inflow=main_inflow,
                    pe_ratio=pe_ratio,
                    heat_score=heat_score,
                    fund_model=fund_model,
                    strategy_tag=strategy_tag,
                    momentum_bias=momentum_bias,
                )
            )
        snapshots.sort(key=lambda item: (item.heat_score, item.pct_change, item.main_inflow), reverse=True)
        if not snapshots:
            stale_snapshots = self.cache.get_market_snapshots(limit, allow_stale=True)
            if stale_snapshots:
                self.last_snapshot_source = "cache_stale"
                return stale_snapshots
        self.cache.put_market_snapshots(limit, snapshots)
        return snapshots

    def fetch_daily_bars(self, symbol: str, start: str = "20240101", end: str = "20500101") -> list[PriceBar]:
        cached_bars = self.cache.get_daily_bars(symbol)
        if cached_bars and self._bars_cover_range(cached_bars, start=start, end=end):
            return self._slice_bars_by_range(cached_bars, start=start, end=end)
        try:
            bars = self._fetch_daily_bars_eastmoney(symbol, start=start, end=end)
        except Exception:
            try:
                bars = self._fetch_daily_bars_tencent(symbol, count=self._tencent_count_for_range(start, end))
            except Exception:
                stale_bars = self.cache.get_daily_bars(symbol, allow_stale=True)
                if stale_bars:
                    return self._slice_bars_by_range(stale_bars, start=start, end=end)
                raise
        if bars:
            self.cache.put_daily_bars(symbol, bars)
        return self._slice_bars_by_range(bars, start=start, end=end)


    def _fetch_daily_bars_eastmoney(self, symbol: str, start: str = "20240101", end: str = "20500101") -> list[PriceBar]:
        url = (
            "https://push2his.eastmoney.com/api/qt/stock/kline/get?"
            + urllib.parse.urlencode(
                {
                    "secid": self._secid(symbol),
                    "fields1": "f1,f2,f3,f4,f5,f6",
                    "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                    "klt": 101,
                    "fqt": 1,
                    "beg": start,
                    "end": end,
                }
            )
        )
        payload = self._fetch_json(url)
        data = payload.get("data", {}) or {}
        rows = data.get("klines", []) or []
        bars: list[PriceBar] = []
        normalized = normalize_symbol(symbol)
        for row in rows:
            parts = str(row).split(",")
            if len(parts) < 6:
                continue
            bars.append(
                PriceBar(
                    date=parts[0],
                    symbol=normalized,
                    open=self._safe_float(parts[1]),
                    close=self._safe_float(parts[2]),
                    high=self._safe_float(parts[3]),
                    low=self._safe_float(parts[4]),
                    volume=self._safe_float(parts[5]),
                )
            )
        return bars

    def _fetch_daily_bars_tencent(self, symbol: str, count: int = 180) -> list[PriceBar]:
        code = self._tencent_code(symbol)
        url = (
            "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?"
            + urllib.parse.urlencode({"param": f"{code},day,,,{count},qfq"})
        )
        payload = self._fetch_json(url, headers=TENCENT_HEADERS)
        stock = payload.get("data", {}).get(code, {}) or {}
        rows = stock.get("qfqday") or stock.get("day") or []
        bars: list[PriceBar] = []
        normalized = normalize_symbol(symbol)
        for parts in rows:
            if len(parts) < 6:
                continue
            bars.append(
                PriceBar(
                    date=str(parts[0]),
                    symbol=normalized,
                    open=self._safe_float(parts[1]),
                    close=self._safe_float(parts[2]),
                    high=self._safe_float(parts[3]),
                    low=self._safe_float(parts[4]),
                    volume=self._safe_float(parts[5]),
                )
            )
        return bars

    def _fetch_json(self, url: str, headers: dict[str, str] | None = None) -> dict:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                request = urllib.request.Request(url, headers=headers or EASTMONEY_HEADERS)
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    text = response.read().decode("utf-8")
                return json.loads(text)
            except Exception as exc:
                last_error = exc
                time.sleep(0.35 * (attempt + 1))
        raise RuntimeError(f"远程行情接口请求失败: {last_error}") from last_error

    @staticmethod
    def _secid(symbol: str) -> str:
        normalized = normalize_symbol(symbol)
        if normalized.startswith("SHSE."):
            return f"1.{extract_stock_id(normalized)}"
        return f"0.{extract_stock_id(normalized)}"

    @staticmethod
    def _tencent_code(symbol: str) -> str:
        normalized = normalize_symbol(symbol)
        stock_id = extract_stock_id(normalized)
        return f"sh{stock_id}" if normalized.startswith("SHSE.") else f"sz{stock_id}"

    @staticmethod
    def _safe_float(value: object, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _momentum_bias(latest_price: float, high_price: float, low_price: float, prev_close: float) -> float:
        price_span = max(high_price - low_price, 0.01)
        close_position = (latest_price - low_price) / price_span
        trend = 0.0 if prev_close <= 0 else (latest_price - prev_close) / prev_close * 100
        return round(close_position * 60 + max(min(trend, 15), -10) * 2.5, 2)

    @staticmethod
    def _bars_cover_range(bars: list[PriceBar], *, start: str, end: str) -> bool:
        if not bars:
            return False
        first_date = EastmoneyMarketFeed._normalize_date_key(str(getattr(bars[0], "date", "") or ""))
        last_date = EastmoneyMarketFeed._normalize_date_key(str(getattr(bars[-1], "date", "") or ""))
        start_key = EastmoneyMarketFeed._normalize_date_key(start)
        end_key = EastmoneyMarketFeed._normalize_date_key(end)
        return (not start_key or first_date <= start_key) and (not end_key or last_date >= end_key)

    @staticmethod
    def _slice_bars_by_range(bars: list[PriceBar], *, start: str, end: str) -> list[PriceBar]:
        start_key = EastmoneyMarketFeed._normalize_date_key(start)
        end_key = EastmoneyMarketFeed._normalize_date_key(end)
        return [
            bar
            for bar in bars
            if (not start_key or EastmoneyMarketFeed._normalize_date_key(bar.date) >= start_key)
            and (not end_key or EastmoneyMarketFeed._normalize_date_key(bar.date) <= end_key)
        ]

    @staticmethod
    def _tencent_count_for_range(start: str, end: str) -> int:
        if not start:
            return 300
        try:
            start_year = int(str(start)[:4])
            end_year = int(str(end or "")[:4] or 2050)
        except ValueError:
            return 300
        years = max(end_year - start_year + 1, 1)
        return min(max(years * 260, 300), 5000)

    @staticmethod
    def _normalize_date_key(value: str) -> str:
        return "".join(ch for ch in str(value or "") if ch.isdigit())

    @staticmethod
    def _heat_score(
        pct_change: float,
        turnover: float,
        amount: float,
        main_inflow: float,
        momentum_bias: float,
    ) -> float:
        amount_score = min(amount / 1.2e8, 20.0)
        inflow_score = min(max(main_inflow, 0.0) / 4.0e7, 25.0)
        turnover_score = min(turnover * 1.8, 20.0)
        pct_score = min(max(pct_change, -3.0) * 2.8, 28.0)
        return round(max(0.0, pct_score + turnover_score + amount_score + inflow_score + momentum_bias * 0.15), 2)

    @staticmethod
    def _fund_model(pct_change: float, turnover: float, main_inflow: float, amount: float) -> str:
        if pct_change >= 8 and turnover >= 10 and main_inflow >= 1.2e8:
            return "游资强攻"
        if main_inflow >= 1.8e8 and amount >= 8e8:
            return "主力净流入"
        if turnover <= 6 and amount >= 5e8:
            return "机构趋势"
        if pct_change <= 3 and main_inflow > 0:
            return "低位试盘"
        return "强势博弈"

    @staticmethod
    def _strategy_tag(pct_change: float, turnover: float, main_inflow: float, momentum_bias: float) -> str:
        if pct_change >= 9 and momentum_bias >= 58:
            return "龙头模型"
        if main_inflow >= 2.0e8 and turnover >= 6:
            return "主力雷达"
        if turnover >= 12:
            return "擒龙打板"
        if pct_change <= 4 and main_inflow > 0:
            return "价值低吸"
        return "掘龙决策"


class CacheOnlyMarketFeed(EastmoneyMarketFeed):
    def fetch_market_snapshots(self, limit: int = 150) -> list[MarketSnapshot]:
        stale_snapshots = self.cache.get_market_snapshots(limit, allow_stale=True)
        self.last_snapshot_source = "cache_only"
        self.last_snapshot_error = "" if stale_snapshots else "no cached snapshots"
        return stale_snapshots

    def fetch_daily_bars(self, symbol: str, start: str = "20240101", end: str = "20500101") -> list[PriceBar]:
        return self.cache.get_daily_bars(symbol, allow_stale=True)


class RemoteMarketScreener:
    def __init__(
        self,
        params: StrategyParams | None = None,
        feed: EastmoneyMarketFeed | None = None,
    ) -> None:
        self.params = params or StrategyParams()
        self.feed = feed or EastmoneyMarketFeed()
        self.strategy = AntiHarvestStrategy(self.params)
        self.backtester = Backtester(strategy_params=self.params)

    def screen_market(self, top_n: int = 18, prefetch_limit: int = 120, history_limit: int = 20) -> MarketScreenResult:
        snapshots = self.feed.fetch_market_snapshots(limit=prefetch_limit)
        snapshots = [item for item in snapshots if self._eligible_snapshot(item)]
        selected_snapshots = snapshots[:history_limit]

        bars_by_symbol: dict[str, list[PriceBar]] = {}
        analyses_by_symbol: dict[str, list[DailyAnalysis]] = {}
        scan_rows: list[ScanRow] = []
        summaries: list[SymbolBacktestSummary] = []
        snapshot_map = {item.symbol: item for item in selected_snapshots}
        chart_series_by_symbol: dict[str, SymbolChartSeries] = {}

        for snapshot in selected_snapshots:
            try:
                bars = self.feed.fetch_daily_bars(snapshot.symbol)
            except Exception:
                bars = []
            analyses: list[DailyAnalysis] = []
            if len(bars) >= 35:
                try:
                    analyses = self.strategy.analyze(bars)
                except Exception:
                    analyses = []
            chart_series_by_symbol[snapshot.symbol] = self._build_chart_series(snapshot, bars, analyses)
            if len(bars) < 35:
                continue
            if not analyses:
                continue

            selected = self._pick_signal(analyses, snapshot)
            if selected is None:
                continue

            bars_by_symbol[snapshot.symbol] = bars
            analyses_by_symbol[snapshot.symbol] = analyses
            scan_rows.append(
                ScanRow(
                    symbol=snapshot.symbol,
                    signal_date=selected.date,
                    label=selected.label,
                    action=ACTION_MAP.get(selected.label, "WATCH"),
                    score=selected.score,
                    close=selected.close,
                    entry_price=selected.entry_price,
                    stop_price=selected.stop_price,
                    target_price=selected.target_price,
                    reason=selected.reason,
                    source_path="eastmoney://market-feed",
                    stock_id=snapshot.stock_id,
                    stock_name=snapshot.stock_name,
                )
            )
            result = self.backtester.run(bars, analyses)
            summaries.append(
                SymbolBacktestSummary(
                    symbol=snapshot.symbol,
                    trades=len(result.trades),
                    total_return=result.total_return,
                    max_drawdown=result.max_drawdown,
                    win_rate=result.win_rate,
                    ending_equity=result.ending_equity,
                )
            )

        if not scan_rows:
            synthetic = self._build_synthetic_scan_rows(selected_snapshots, bars_by_symbol)
            scan_rows.extend(synthetic)

        scan_rows.sort(
            key=lambda item: (self._snapshot_heat(snapshot_map.get(item.symbol)), item.score, item.signal_date),
            reverse=True,
        )
        summaries.sort(key=lambda item: (item.total_return, item.win_rate, item.symbol), reverse=True)

        stock_profiles = self._build_profiles(snapshot_map, scan_rows)
        portfolio_backtest = PortfolioBacktester(
            backtest_params=BacktestParams.realistic_cn_equity(
                max_positions=min(max(len(bars_by_symbol), 1), 5),
                max_position_fraction=0.42 if len(bars_by_symbol) <= 1 else 0.22,
                max_volume_participation=0.12,
            )
        ).run(bars_by_symbol, analyses_by_symbol) if bars_by_symbol else None

        recommendations = DailyPoolBuilder(stock_profiles=stock_profiles, news_map={}).build(
            scan_rows,
            analyses_by_symbol,
            summaries,
            top_n=top_n,
            portfolio_backtest=portfolio_backtest,
        )
        recommendations = self._enrich_recommendations(recommendations, snapshot_map)[:top_n]
        algorithmic_pool = self._build_algorithmic_pool(recommendations, scan_rows, snapshot_map)

        return MarketScreenResult(
            market_name="东方财富全市场算法池",
            generated_at=self._now_string(),
            algorithmic_pool=algorithmic_pool,
            scan_rows=scan_rows,
            recommendations=recommendations,
            bars_by_symbol=bars_by_symbol,
            analyses_by_symbol=analyses_by_symbol,
            summaries=summaries,
            snapshots=snapshot_map,
            chart_series_by_symbol=chart_series_by_symbol,
        )

    @staticmethod
    def _now_string() -> str:
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    @staticmethod
    def _eligible_snapshot(snapshot: MarketSnapshot) -> bool:
        if snapshot.latest_price < 2.5 or snapshot.latest_price > 120:
            return False
        if snapshot.amount < 2.0e8:
            return False
        if snapshot.turnover < 2.0:
            return False
        if snapshot.pct_change < -2.5 or snapshot.pct_change > 21:
            return False
        return True

    @staticmethod
    def _pick_recent_non_none(analyses: list[DailyAnalysis]) -> DailyAnalysis | None:
        recent = [item for item in analyses[-5:] if item.label != "NONE"]
        if recent:
            recent.sort(key=lambda item: (item.score, item.date), reverse=True)
            return recent[0]
        history = [item for item in analyses if item.label != "NONE"]
        return history[-1] if history else None

    def _pick_signal(self, analyses: list[DailyAnalysis], snapshot: MarketSnapshot) -> DailyAnalysis | None:
        selected = self._pick_recent_non_none(analyses)
        if selected is not None:
            return selected

        latest = analyses[-1]
        synthetic_score = int(
            max(
                55,
                min(
                    92,
                    round(snapshot.heat_score * 0.58 + snapshot.momentum_bias * 0.22 + max(snapshot.pct_change, 0.0) * 1.4),
                ),
            )
        )
        stop_price = latest.close * 0.95
        target_price = latest.close * 1.1
        return DailyAnalysis(
            date=latest.date,
            symbol=latest.symbol,
            close=latest.close,
            atr=latest.atr,
            ma_fast=latest.ma_fast,
            ma_slow=latest.ma_slow,
            breakout_level=latest.breakout_level,
            volume_ratio=latest.volume_ratio,
            upper_shadow_pct=latest.upper_shadow_pct,
            close_location=latest.close_location,
            label="WATCH",
            score=synthetic_score,
            reason=f"市场热度 {snapshot.heat_score:.1f}，{snapshot.fund_model}，等待更清晰的回封或分歧转一致。",
            entry_price=latest.close,
            stop_price=round(stop_price, 2),
            target_price=round(target_price, 2),
        )

    def _build_profiles(
        self,
        snapshot_map: dict[str, MarketSnapshot],
        scan_rows: list[ScanRow],
    ) -> dict[str, StockProfile]:
        ranked_symbols = [row.symbol for row in scan_rows[:5]]
        profiles: dict[str, StockProfile] = {}
        for symbol, snapshot in snapshot_map.items():
            profiles[symbol] = StockProfile(
                symbol=symbol,
                stock_id=snapshot.stock_id,
                name=snapshot.stock_name,
                industry=snapshot.strategy_tag,
                is_leader=symbol in ranked_symbols or snapshot.heat_score >= 80,
                notes=snapshot.fund_model,
            )
        return profiles

    def _enrich_recommendations(
        self,
        recommendations: list[RecommendationRow],
        snapshot_map: dict[str, MarketSnapshot],
    ) -> list[RecommendationRow]:
        enriched: list[RecommendationRow] = []
        for item in recommendations:
            snapshot = snapshot_map.get(item.symbol)
            if snapshot is None:
                enriched.append(item)
                continue
            catalyst = (
                f"{snapshot.fund_model} / 主力净额 {snapshot.main_inflow / 1e8:.2f} 亿 / "
                f"换手 {snapshot.turnover:.1f}%"
            )
            news_score = min(95.0, max(item.news_score, snapshot.heat_score * 0.75))
            total_score = round(
                item.technical_score * 0.3
                + item.position_score * 0.2
                + item.persistence_score * 0.2
                + news_score * 0.18
                + max(item.leader_score, 88.0 if snapshot.heat_score >= 80 else item.leader_score) * 0.12
                + (item.dragon_decision_score or item.total_score) * 0.06,
                2,
            )
            boosted_primary = item.primary_strategy or snapshot.strategy_tag
            if snapshot.strategy_tag in {"龙头模型", "主力雷达", "擒龙打板", "价值低吸", "掘龙决策"}:
                boosted_primary = snapshot.strategy_tag
            rationale = (
                f"{item.rationale} | 涨幅 {snapshot.pct_change:.2f}% | "
                f"主力净流入 {snapshot.main_inflow / 1e8:.2f} 亿 | {snapshot.strategy_tag}"
            )
            enriched.append(
                RecommendationRow(
                    symbol=item.symbol,
                    stock_id=item.stock_id,
                    stock_name=item.stock_name,
                    action=item.action if str(getattr(item, "signal_source", "") or "").startswith("synthetic://") else ("BUY" if total_score >= 72 else item.action),
                    label=item.label,
                    signal_date=item.signal_date,
                    close=item.close,
                    entry_price=item.entry_price,
                    stop_price=item.stop_price,
                    target_price=item.target_price,
                    technical_score=item.technical_score,
                    position_score=item.position_score,
                    persistence_score=item.persistence_score,
                    backtest_quality_score=float(getattr(item, "backtest_quality_score", 0.0) or 0.0),
                    news_score=news_score,
                    leader_score=max(item.leader_score, 88.0 if snapshot.heat_score >= 80 else item.leader_score),
                    total_score=total_score,
                    theme_name=item.theme_name or snapshot.strategy_tag,
                    theme_score=item.theme_score,
                    theme_rank=item.theme_rank,
                    leader_level=item.leader_level,
                    primary_strategy=boosted_primary,
                    signal_source=getattr(item, "signal_source", ""),
                    signal_age_days=int(getattr(item, "signal_age_days", 0) or 0),
                    freshness_score=float(getattr(item, "freshness_score", 0.0) or 0.0),
                    setup_quality_score=float(getattr(item, "setup_quality_score", 0.0) or 0.0),
                    risk_reward_ratio=float(getattr(item, "risk_reward_ratio", 0.0) or 0.0),
                    confidence_score=float(getattr(item, "confidence_score", 0.0) or 0.0),
                    execution_readiness=float(getattr(item, "execution_readiness", 0.0) or 0.0),
                    timeliness_score=float(getattr(item, "timeliness_score", 0.0) or 0.0),
                    opportunity_tier=getattr(item, "opportunity_tier", ""),
                    reject_reason=getattr(item, "reject_reason", ""),
                    next_focus=getattr(item, "next_focus", ""),
                    invalidation_reason=getattr(item, "invalidation_reason", ""),
                    leader_model_score=item.leader_model_score + (5.0 if boosted_primary == "龙头模型" else 0.0),
                    main_force_score=item.main_force_score + (5.0 if boosted_primary == "主力雷达" else 0.0),
                    board_attack_score=item.board_attack_score + (5.0 if boosted_primary == "擒龙打板" else 0.0),
                    value_recovery_score=item.value_recovery_score + (5.0 if boosted_primary == "价值低吸" else 0.0),
                    dragon_decision_score=max(item.dragon_decision_score, total_score),
                    catalyst=catalyst,
                    rationale=rationale,
                )
            )
        enriched.sort(key=lambda item: (item.total_score, item.technical_score, item.stock_id), reverse=True)
        return enriched

    def _build_algorithmic_pool(
        self,
        recommendations: list[RecommendationRow],
        scan_rows: list[ScanRow],
        snapshot_map: dict[str, MarketSnapshot],
    ) -> list[AlgorithmicPoolRow]:
        scan_map = {item.symbol: item for item in scan_rows}
        rows: list[AlgorithmicPoolRow] = []
        for item in recommendations:
            snapshot = snapshot_map.get(item.symbol)
            scan_row = scan_map.get(item.symbol)
            if snapshot is None or scan_row is None:
                continue
            rows.append(
                AlgorithmicPoolRow(
                    symbol=item.symbol,
                    stock_id=item.stock_id,
                    stock_name=item.stock_name,
                    theme_name=item.theme_name or snapshot.strategy_tag,
                    latest_price=snapshot.latest_price,
                    pct_change=snapshot.pct_change,
                    main_inflow=snapshot.main_inflow,
                    amount=snapshot.amount,
                    turnover=snapshot.turnover,
                    heat_score=snapshot.heat_score,
                    fund_model=snapshot.fund_model,
                    strategy_tag=item.primary_strategy or snapshot.strategy_tag,
                    decision_score=item.dragon_decision_score or item.total_score,
                    signal_label=item.label,
                    action=item.action,
                    entry_price=item.entry_price or item.close,
                    stop_price=item.stop_price or item.close * 0.95,
                    target_price=item.target_price or item.close * 1.1,
                    rationale=item.rationale,
                )
            )
        rows.sort(key=lambda item: (item.heat_score, item.pct_change, item.main_inflow), reverse=True)
        return rows

    def _build_synthetic_scan_rows(
        self,
        snapshots: list[MarketSnapshot],
        bars_by_symbol: dict[str, list[PriceBar]],
    ) -> list[ScanRow]:
        rows: list[ScanRow] = []
        for snapshot in snapshots[: min(18, len(snapshots))]:
            bars = bars_by_symbol.get(snapshot.symbol, [])
            signal_date = bars[-1].date if bars else self._now_string().split(" ")[0]
            close = bars[-1].close if bars else snapshot.latest_price
            score = int(max(58, min(90, round(snapshot.heat_score * 0.72 + max(snapshot.pct_change, 0.0) * 1.8))))
            label = "WATCH"
            action = "WATCH"
            entry = close
            stop = round(close * 0.95, 2)
            target = round(close * 1.1, 2)
            rows.append(
                ScanRow(
                    symbol=snapshot.symbol,
                    signal_date=signal_date,
                    label=label,
                    action=action,
                    score=score,
                    close=close,
                    entry_price=entry,
                    stop_price=stop,
                    target_price=target,
                    reason=(
                        f"热度 {snapshot.heat_score:.1f} / 涨幅 {snapshot.pct_change:.2f}% / "
                        f"主力净流入 {snapshot.main_inflow / 1e8:.2f} 亿，作为短线观察候选。"
                    ),
                    source_path="synthetic://market-fallback",
                    stock_id=snapshot.stock_id,
                    stock_name=snapshot.stock_name,
                )
            )
        return rows

    def _build_chart_series(
        self,
        snapshot: MarketSnapshot,
        bars: list[PriceBar],
        analyses: list[DailyAnalysis],
    ) -> SymbolChartSeries:
        intraday_price, intraday_trend = self._build_pseudo_intraday(snapshot, bars)
        capital_flow = self._build_capital_flow_series(snapshot, bars)
        heat_momentum = self._build_heat_momentum_series(snapshot, bars, analyses)
        return SymbolChartSeries(
            symbol=snapshot.symbol,
            intraday_price=intraday_price,
            intraday_trend=intraday_trend,
            capital_flow=capital_flow,
            heat_momentum=heat_momentum,
        )

    def _build_pseudo_intraday(
        self,
        snapshot: MarketSnapshot,
        bars: list[PriceBar],
        points: int = 48,
    ) -> tuple[list[SeriesPoint], list[SeriesPoint]]:
        base = snapshot.prev_close if snapshot.prev_close > 0 else (bars[-2].close if len(bars) >= 2 else snapshot.latest_price)
        latest = snapshot.latest_price if snapshot.latest_price > 0 else (bars[-1].close if bars else base)
        high = snapshot.high_price if snapshot.high_price > 0 else max(base, latest) * 1.01
        low = snapshot.low_price if snapshot.low_price > 0 else min(base, latest) * 0.99
        drift = (latest - base) / max(points - 1, 1)
        amp = max((high - low) * 0.18, abs(latest - base) * 0.35, base * 0.002)
        phase = (snapshot.momentum_bias / 100.0) * math.pi

        price_series: list[SeriesPoint] = []
        trend_series: list[SeriesPoint] = []
        for i in range(points):
            t = self._intraday_time_label(i, points)
            wave = math.sin((i / max(points - 1, 1)) * 3.8 * math.pi + phase)
            price = base + drift * i + wave * amp
            price = min(max(price, low), high)
            trend = ((price - base) / base * 100.0) if base > 0 else 0.0
            price_series.append(SeriesPoint(t=t, v=round(price, 3)))
            trend_series.append(SeriesPoint(t=t, v=round(trend, 3)))
        if price_series:
            price_series[-1] = SeriesPoint(t=price_series[-1].t, v=round(latest, 3))
            end_trend = ((latest - base) / base * 100.0) if base > 0 else 0.0
            trend_series[-1] = SeriesPoint(t=trend_series[-1].t, v=round(end_trend, 3))
        return price_series, trend_series

    def _build_capital_flow_series(
        self,
        snapshot: MarketSnapshot,
        bars: list[PriceBar],
        points: int = 40,
    ) -> list[SeriesPoint]:
        base_flow = snapshot.main_inflow / 1e8
        turnover_scale = max(snapshot.turnover / 10.0, 0.4)
        volatility = self._volatility_proxy(bars)
        amp = max(abs(base_flow) * 0.2 + turnover_scale * 0.6 + volatility * 0.3, 0.35)
        slope = (snapshot.pct_change / 10.0) * 0.07
        phase = (snapshot.heat_score / 100.0) * math.pi
        series: list[SeriesPoint] = []
        for i in range(points):
            t = f"{i:02d}"
            wave = math.sin((i / max(points - 1, 1)) * 2.6 * math.pi + phase) * amp
            pulse = math.cos((i / max(points - 1, 1)) * 4.8 * math.pi + phase * 0.6) * amp * 0.3
            value = base_flow * (0.3 + i / max(points - 1, 1) * 0.7) + wave + pulse + i * slope
            series.append(SeriesPoint(t=t, v=round(value, 3)))
        return series

    def _build_heat_momentum_series(
        self,
        snapshot: MarketSnapshot,
        bars: list[PriceBar],
        analyses: list[DailyAnalysis],
        points: int = 40,
    ) -> list[SeriesPoint]:
        base = snapshot.heat_score
        atr_boost = analyses[-1].atr if analyses else 0.0
        trend_bias = analyses[-1].score / 100.0 if analyses else 0.55
        volatility = self._volatility_proxy(bars)
        amp = max(4.0 + volatility * 18.0, 5.0)
        phase = snapshot.momentum_bias / 100.0 * math.pi
        slope = (snapshot.pct_change * 0.15 + (trend_bias - 0.5) * 6 + atr_boost * 0.2) / max(points, 1)
        series: list[SeriesPoint] = []
        for i in range(points):
            t = f"{i:02d}"
            wave = math.sin((i / max(points - 1, 1)) * 3.4 * math.pi + phase) * amp
            value = base * 0.75 + wave + i * slope
            value = min(max(value, 0.0), 100.0)
            series.append(SeriesPoint(t=t, v=round(value, 3)))
        return series

    @staticmethod
    def _volatility_proxy(bars: list[PriceBar]) -> float:
        if len(bars) < 2:
            return 0.02
        recent = bars[-20:]
        ranges = [(bar.high - bar.low) / bar.close for bar in recent if bar.close > 0]
        if not ranges:
            return 0.02
        return max(min(sum(ranges) / len(ranges), 0.2), 0.01)

    @staticmethod
    def _intraday_time_label(index: int, total: int) -> str:
        if total <= 1:
            return "09:30"
        # 9:30-11:30 and 13:00-15:00 mapped to [0,total-1]
        ratio = index / (total - 1)
        minutes = int(ratio * 240)
        if minutes <= 120:
            hour = 9 + (30 + minutes) // 60
            minute = (30 + minutes) % 60
        else:
            after_lunch = minutes - 120
            hour = 13 + after_lunch // 60
            minute = after_lunch % 60
        return f"{hour:02d}:{minute:02d}"

    @staticmethod
    def _snapshot_heat(snapshot: MarketSnapshot | None) -> float:
        return snapshot.heat_score if snapshot else 0.0
