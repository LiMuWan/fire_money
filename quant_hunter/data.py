from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .models import CashSnapshot, HoldingRecord, NewsCatalyst, PriceBar, StockProfile


REQUIRED_COLUMNS = {
    "date": {"date", "datetime", "trade_date"},
    "open": {"open", "o"},
    "high": {"high", "h"},
    "low": {"low", "l"},
    "close": {"close", "c"},
    "volume": {"volume", "vol", "amount"},
    "symbol": {"symbol", "code", "ticker"},
}

PROFILE_SYMBOL_COLUMNS = ("symbol", "code", "ticker", "stock_id")
PROFILE_NAME_COLUMNS = ("name", "stock_name", "display_name")
PROFILE_INDUSTRY_COLUMNS = ("industry", "sector", "theme")
PROFILE_LEADER_COLUMNS = ("is_leader", "leader", "leader_flag")
PROFILE_NOTES_COLUMNS = ("notes", "comment", "memo")
NEWS_TITLE_COLUMNS = ("title", "headline")
NEWS_SUMMARY_COLUMNS = ("summary", "content", "brief")
NEWS_TIME_COLUMNS = ("published_at", "date", "datetime")
NEWS_SENTIMENT_COLUMNS = ("sentiment_score", "sentiment", "score")
NEWS_HEAT_COLUMNS = ("heat", "hotness", "importance")
NEWS_SOURCE_COLUMNS = ("source", "publisher", "media", "source_name")
NEWS_URL_COLUMNS = ("url", "link", "source_url")
THEME_NAME_COLUMNS = ("theme_name", "theme", "name")
THEME_KEYWORD_COLUMNS = ("keywords", "keyword", "aliases")


def normalize_symbol(raw: str) -> str:
    value = raw.strip().upper()
    if not value:
        return ""
    if "." in value:
        left, right = value.split(".", 1)
        if left in {"SHSE", "SZSE", "HKSE", "NASDAQ", "NYSE", "AMEX", "US"}:
            return f"{left}.{right}"
        if left in {"0", "1", "105", "106", "107", "116"}:
            exchange = {
                "0": "SZSE",
                "1": "SHSE",
                "105": "NASDAQ",
                "106": "NYSE",
                "107": "AMEX",
                "116": "HKSE",
            }.get(left, "")
            if exchange:
                return f"{exchange}.{right}"
        if right in {"SH", "SS"}:
            return f"SHSE.{left.zfill(6) if left.isdigit() else left}"
        if right == "SZ":
            return f"SZSE.{left.zfill(6) if left.isdigit() else left}"
        if right in {"HK", "HKG"} and left.isdigit():
            return f"HKSE.{left.zfill(5)}"
        if right in {"NASDAQ", "OQ"}:
            return f"NASDAQ.{left}"
        if right in {"NYSE", "N"}:
            return f"NYSE.{left}"
        if right == "AMEX":
            return f"AMEX.{left}"
        if right == "US":
            return f"US.{left}"
    digits = "".join(ch for ch in value if ch.isdigit())
    if len(digits) == 5:
        return f"HKSE.{digits.zfill(5)}"
    if len(digits) == 6:
        exchange = "SHSE" if digits.startswith(("5", "6", "9")) else "SZSE"
        return f"{exchange}.{digits}"
    if value.isalpha():
        return value
    return value


def extract_stock_id(symbol: str) -> str:
    normalized = normalize_symbol(symbol)
    return normalized.split(".", 1)[1] if "." in normalized else normalized


def _find_optional_column(fieldnames: list[str], aliases: tuple[str, ...]) -> str:
    lowered = {name.strip().lower(): name for name in fieldnames}
    for alias in aliases:
        if alias in lowered:
            return lowered[alias]
    return ""


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y", "是"}


def _parse_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _row_is_blank(row: dict[str, object]) -> bool:
    return all(not str(value or "").strip() for value in row.values())


def _require_text(value: object, *, field_name: str, row_number: int, file_path: Path) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{file_path.name} 第 {row_number} 行字段 {field_name} 为空。")
    return text


def _require_float(value: object, *, field_name: str, row_number: int, file_path: Path) -> float:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{file_path.name} 第 {row_number} 行字段 {field_name} 为空。")
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{file_path.name} 第 {row_number} 行字段 {field_name} 不是有效数字: {raw!r}") from exc


def _require_int(value: object, *, field_name: str, row_number: int, file_path: Path) -> int:
    return int(_require_float(value, field_name=field_name, row_number=row_number, file_path=file_path))


def load_stock_profiles_from_csv(path: str | Path) -> dict[str, StockProfile]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("股票资料 CSV 没有表头。")
        symbol_column = _find_optional_column(reader.fieldnames, PROFILE_SYMBOL_COLUMNS)
        name_column = _find_optional_column(reader.fieldnames, PROFILE_NAME_COLUMNS)
        if not symbol_column or not name_column:
            raise ValueError("股票资料 CSV 需要至少包含 symbol/code 和 name 两列。")
        industry_column = _find_optional_column(reader.fieldnames, PROFILE_INDUSTRY_COLUMNS)
        leader_column = _find_optional_column(reader.fieldnames, PROFILE_LEADER_COLUMNS)
        notes_column = _find_optional_column(reader.fieldnames, PROFILE_NOTES_COLUMNS)

        profiles: dict[str, StockProfile] = {}
        for row in reader:
            symbol = normalize_symbol(row.get(symbol_column, ""))
            if not symbol:
                continue
            profiles[symbol] = StockProfile(
                symbol=symbol,
                stock_id=extract_stock_id(symbol),
                name=row.get(name_column, "").strip() or extract_stock_id(symbol),
                industry=row.get(industry_column, "").strip() if industry_column else "",
                is_leader=_parse_bool(row.get(leader_column, "")) if leader_column else False,
                notes=row.get(notes_column, "").strip() if notes_column else "",
            )
    return profiles


def load_news_catalysts_from_csv(path: str | Path) -> dict[str, list[NewsCatalyst]]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("消息面 CSV 没有表头。")
        symbol_column = _find_optional_column(reader.fieldnames, PROFILE_SYMBOL_COLUMNS)
        title_column = _find_optional_column(reader.fieldnames, NEWS_TITLE_COLUMNS)
        if not symbol_column or not title_column:
            raise ValueError("消息面 CSV 需要至少包含 symbol/code 和 title 两列。")
        summary_column = _find_optional_column(reader.fieldnames, NEWS_SUMMARY_COLUMNS)
        time_column = _find_optional_column(reader.fieldnames, NEWS_TIME_COLUMNS)
        sentiment_column = _find_optional_column(reader.fieldnames, NEWS_SENTIMENT_COLUMNS)
        heat_column = _find_optional_column(reader.fieldnames, NEWS_HEAT_COLUMNS)
        source_column = _find_optional_column(reader.fieldnames, NEWS_SOURCE_COLUMNS)
        url_column = _find_optional_column(reader.fieldnames, NEWS_URL_COLUMNS)

        news_map: dict[str, list[NewsCatalyst]] = {}
        for row in reader:
            symbol = normalize_symbol(row.get(symbol_column, ""))
            if not symbol:
                continue
            news = NewsCatalyst(
                symbol=symbol,
                title=row.get(title_column, "").strip(),
                summary=row.get(summary_column, "").strip() if summary_column else "",
                published_at=row.get(time_column, "").strip() if time_column else "",
                source=row.get(source_column, "").strip() if source_column else "",
                url=row.get(url_column, "").strip() if url_column else "",
                sentiment_score=_parse_float(row.get(sentiment_column, "")) if sentiment_column else 0.0,
                heat=_parse_float(row.get(heat_column, "")) if heat_column else 0.0,
            )
            news_map.setdefault(symbol, []).append(news)

    for items in news_map.values():
        items.sort(key=lambda item: item.published_at or datetime.min.isoformat(), reverse=True)
    return news_map


def load_theme_aliases_from_csv(path: str | Path) -> dict[str, tuple[str, ...]]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("题材词典 CSV 没有表头。")
        name_column = _find_optional_column(reader.fieldnames, THEME_NAME_COLUMNS)
        keyword_column = _find_optional_column(reader.fieldnames, THEME_KEYWORD_COLUMNS)
        if not name_column or not keyword_column:
            raise ValueError("题材词典 CSV 需要至少包含 theme_name 和 keywords 两列。")

        mapping: dict[str, tuple[str, ...]] = {}
        for row in reader:
            theme_name = (row.get(name_column, "") or "").strip()
            raw_keywords = (row.get(keyword_column, "") or "").strip()
            if not theme_name or not raw_keywords:
                continue
            keywords = tuple(item.strip() for item in raw_keywords.replace("，", ",").split(",") if item.strip())
            if keywords:
                mapping[theme_name] = keywords
    return mapping


def _normalize_header_map(fieldnames: list[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    lowered = {name.strip().lower(): name for name in fieldnames}
    for canonical, aliases in REQUIRED_COLUMNS.items():
        for alias in aliases:
            if alias in lowered:
                mapping[canonical] = lowered[alias]
                break
    missing = {"date", "open", "high", "low", "close", "volume"} - mapping.keys()
    if missing:
        raise ValueError(f"CSV 缺少必要字段: {', '.join(sorted(missing))}")
    return mapping


def load_bars_from_csv(path: str | Path, default_symbol: str = "UNKNOWN") -> list[PriceBar]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("CSV 没有表头。")
        header_map = _normalize_header_map(reader.fieldnames)
        bars: list[PriceBar] = []
        for row_number, row in enumerate(reader, start=2):
            if _row_is_blank(row):
                continue
            symbol_key = header_map.get("symbol")
            symbol = normalize_symbol((row.get(symbol_key, "") if symbol_key else "").strip() or default_symbol)
            bars.append(
                PriceBar(
                    date=_require_text(row.get(header_map["date"]), field_name=header_map["date"], row_number=row_number, file_path=file_path),
                    symbol=symbol,
                    open=_require_float(row.get(header_map["open"]), field_name=header_map["open"], row_number=row_number, file_path=file_path),
                    high=_require_float(row.get(header_map["high"]), field_name=header_map["high"], row_number=row_number, file_path=file_path),
                    low=_require_float(row.get(header_map["low"]), field_name=header_map["low"], row_number=row_number, file_path=file_path),
                    close=_require_float(row.get(header_map["close"]), field_name=header_map["close"], row_number=row_number, file_path=file_path),
                    volume=_require_float(row.get(header_map["volume"]), field_name=header_map["volume"], row_number=row_number, file_path=file_path),
                )
            )
    return sorted(bars, key=lambda bar: bar.date)


def aggregate_price_bars(bars: list[PriceBar], timeframe: str) -> list[PriceBar]:
    normalized = (timeframe or "").strip().lower()
    if normalized not in {"week", "weekly", "month", "monthly"}:
        return list(bars)
    if not bars:
        return []

    grouped: dict[str, list[PriceBar]] = {}
    for bar in sorted(bars, key=lambda item: item.date):
        dt = datetime.strptime(bar.date, "%Y-%m-%d")
        if normalized in {"week", "weekly"}:
            iso_year, iso_week, _ = dt.isocalendar()
            bucket_key = f"{iso_year}-W{iso_week:02d}"
        else:
            bucket_key = f"{dt.year}-{dt.month:02d}"
        grouped.setdefault(bucket_key, []).append(bar)

    aggregated: list[PriceBar] = []
    for bucket in grouped.values():
        first = bucket[0]
        last = bucket[-1]
        aggregated.append(
            PriceBar(
                date=last.date,
                symbol=first.symbol,
                open=first.open,
                high=max(item.high for item in bucket),
                low=min(item.low for item in bucket),
                close=last.close,
                volume=sum(item.volume for item in bucket),
            )
        )
    return aggregated


def discover_csv_files(folder: str | Path) -> list[Path]:
    root = Path(folder)
    if not root.exists():
        raise ValueError(f"目录不存在: {root}")
    return sorted(path for path in root.glob("*.csv") if path.is_file())


def load_universe_from_folder(folder: str | Path) -> dict[str, tuple[Path, list[PriceBar]]]:
    universe: dict[str, tuple[Path, list[PriceBar]]] = {}
    for path in discover_csv_files(folder):
        try:
            bars = load_bars_from_csv(path, default_symbol=path.stem)
        except Exception:
            continue
        if bars:
            universe[bars[-1].symbol] = (path, bars)
    return universe


def load_holdings_from_csv(path: str | Path) -> list[HoldingRecord]:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("持仓 CSV 没有表头。")
        lowered = {name.strip().lower(): name for name in reader.fieldnames}
        required = {"symbol", "quantity", "available", "cost_price", "market_value"}
        if not required.issubset(lowered):
            missing = ", ".join(sorted(required - lowered.keys()))
            raise ValueError(f"持仓 CSV 缺少字段: {missing}")
        records: list[HoldingRecord] = []
        for row_number, row in enumerate(reader, start=2):
            if _row_is_blank(row):
                continue
            records.append(
                HoldingRecord(
                    symbol=_require_text(row.get(lowered["symbol"]), field_name=lowered["symbol"], row_number=row_number, file_path=file_path),
                    quantity=_require_int(row.get(lowered["quantity"]), field_name=lowered["quantity"], row_number=row_number, file_path=file_path),
                    available=_require_int(row.get(lowered["available"]), field_name=lowered["available"], row_number=row_number, file_path=file_path),
                    cost_price=_require_float(row.get(lowered["cost_price"]), field_name=lowered["cost_price"], row_number=row_number, file_path=file_path),
                    market_value=_require_float(row.get(lowered["market_value"]), field_name=lowered["market_value"], row_number=row_number, file_path=file_path),
                )
            )
    return records


def load_cash_snapshot_from_csv(path: str | Path) -> CashSnapshot:
    file_path = Path(path)
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        if not rows:
            raise ValueError("资金 CSV 没有数据。")
        lowered = {name.strip().lower(): name for name in reader.fieldnames or []}
        required = {"available_cash", "total_assets"}
        if not required.issubset(lowered):
            missing = ", ".join(sorted(required - lowered.keys()))
            raise ValueError(f"资金 CSV 缺少字段: {missing}")
        row = next((item for item in rows if not _row_is_blank(item)), None)
        if row is None:
            raise ValueError("资金 CSV 没有数据。")
        return CashSnapshot(
            available_cash=_require_float(row.get(lowered["available_cash"]), field_name=lowered["available_cash"], row_number=2, file_path=file_path),
            total_assets=_require_float(row.get(lowered["total_assets"]), field_name=lowered["total_assets"], row_number=2, file_path=file_path),
        )
