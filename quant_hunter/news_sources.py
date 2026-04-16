from __future__ import annotations

import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

from .data import extract_stock_id, load_news_catalysts_from_csv, normalize_symbol
from .models import NewsCatalyst


CNINFO_NOTICE_ENDPOINT = "https://www.cninfo.com.cn/new/hisAnnouncement/query"
CNINFO_STATIC_PREFIX = "https://static.cninfo.com.cn/"
CNINFO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.cninfo.com.cn/new/commonUrl?url=disclosure/list/notice",
    "Accept": "application/json,text/plain,*/*",
    "Connection": "close",
}
_HTML_TAG_RE = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class NewsSourceDescriptor:
    key: str
    label: str
    description: str
    requires_path: bool = False
    available: bool = True


@dataclass(frozen=True)
class NewsSourceConfig:
    provider: str = "csv"
    path: str = ""
    symbols: tuple[str, ...] = ()
    symbol_names: dict[str, str] = field(default_factory=dict)
    limit_per_symbol: int = 3
    recent_days: int = 20
    timeout: float = 12.0


@dataclass(frozen=True)
class NewsLoadResult:
    provider: str
    label: str
    news_map: dict[str, list[NewsCatalyst]]
    source_path: str = ""
    summary: str = ""


_SAMPLE_NEWS_PATH = Path(__file__).resolve().parent.parent / "sample_data" / "news_catalysts.csv"

_DESCRIPTORS: tuple[NewsSourceDescriptor, ...] = (
    NewsSourceDescriptor("csv", "本地 CSV", "适合手工整理、测试接入和离线回放。", requires_path=True),
    NewsSourceDescriptor("sample", "示例消息源", "加载项目自带示例消息，用于演示消息催化和逻辑链路。"),
    NewsSourceDescriptor("cls_api", "财联社适配器", "预留正式授权接口位，拿到授权后接入快讯/电报流。", available=False),
    NewsSourceDescriptor(
        "cninfo_api",
        "巨潮公告适配器",
        "基于巨潮资讯官网公开公告检索链路推断实现，优先抓最近公告标题、时间和 PDF 链接。",
        available=True,
    ),
    NewsSourceDescriptor("exchange_api", "交易所互动适配器", "预留上证 e 互动 / 深交所互动易适配器位。", available=False),
)


def list_news_source_descriptors() -> list[NewsSourceDescriptor]:
    return list(_DESCRIPTORS)


def get_news_source_descriptor(key: str) -> NewsSourceDescriptor:
    normalized = str(key or "csv").strip().lower() or "csv"
    return next((item for item in _DESCRIPTORS if item.key == normalized), _DESCRIPTORS[0])


def resolve_news_source_label(key: str) -> str:
    return get_news_source_descriptor(key).label


def _normalize_text(value: object) -> str:
    return str(value or "").replace("\r", " ").replace("\n", " ").strip()


def _strip_html_tags(text: str) -> str:
    return _HTML_TAG_RE.sub("", html.unescape(text or "")).strip()


def _cninfo_market_scope(symbol: str) -> tuple[str, str]:
    normalized = normalize_symbol(symbol)
    if normalized.startswith("SHSE."):
        return "sse", "sh"
    if normalized.startswith("SZSE."):
        return "szse", "sz"
    return "", ""


def _cninfo_recent_range(days: int) -> str:
    today = date.today()
    start = today - timedelta(days=max(int(days or 20) - 1, 1))
    return f"{start:%Y-%m-%d}~{today:%Y-%m-%d}"


def _cninfo_stock_query(symbol: str, symbol_names: dict[str, str]) -> str:
    code = extract_stock_id(symbol)
    name = _normalize_text(symbol_names.get(symbol, ""))
    return f"{code},{name}" if name else code


def _cninfo_announcement_url(raw_path: object) -> str:
    path = _normalize_text(raw_path)
    if not path:
        return ""
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return urllib.parse.urljoin(CNINFO_STATIC_PREFIX, path.lstrip("/"))


def _cninfo_published_at(value: object) -> str:
    raw = value
    if isinstance(raw, (int, float)):
        ts = float(raw)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    text = _normalize_text(raw)
    if text.isdigit():
        ts = float(text)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    return text


def _cninfo_summary(item: dict[str, object]) -> str:
    parts: list[str] = []
    for key in ("announcementTypeName", "announcementType", "announcementTypeDesc"):
        value = _normalize_text(item.get(key, ""))
        if value and value not in parts:
            parts.append(value)
    for key in ("secName", "orgName", "batchNum"):
        value = _normalize_text(item.get(key, ""))
        if value and value not in parts:
            parts.append(value)
    return " | ".join(parts[:3])


def _fetch_json(url: str, *, method: str = "GET", data: dict[str, object] | None = None, timeout: float = 12.0) -> object:
    body = None
    headers = dict(CNINFO_HEADERS)
    if data is not None:
        body = urllib.parse.urlencode({key: value for key, value in data.items() if value is not None}).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8", errors="ignore")
    return json.loads(payload)


def _load_cninfo_news(config: NewsSourceConfig, descriptor: NewsSourceDescriptor) -> NewsLoadResult:
    symbols = [normalize_symbol(symbol) for symbol in config.symbols if normalize_symbol(symbol)]
    if not symbols:
        raise ValueError("巨潮公告适配器需要至少 1 只股票代码。")
    news_map: dict[str, list[NewsCatalyst]] = {}
    for symbol in symbols:
        column, plate = _cninfo_market_scope(symbol)
        if not column or not plate:
            continue
        payload = {
            "pageNum": 1,
            "pageSize": max(1, min(int(config.limit_per_symbol or 3), 10)),
            "tabName": "fulltext",
            "column": column,
            "plate": plate,
            "stock": _cninfo_stock_query(symbol, config.symbol_names),
            "searchkey": "",
            "secid": "",
            "category": "",
            "trade": "",
            "sortName": "",
            "sortType": "",
            "seDate": _cninfo_recent_range(config.recent_days),
        }
        response = _fetch_json(CNINFO_NOTICE_ENDPOINT, method="POST", data=payload, timeout=config.timeout)
        if not isinstance(response, dict):
            continue
        rows = response.get("announcements", [])
        if not isinstance(rows, list):
            continue
        items: list[NewsCatalyst] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = _strip_html_tags(_normalize_text(row.get("announcementTitle", "")))
            if not title:
                continue
            items.append(
                NewsCatalyst(
                    symbol=symbol,
                    title=title,
                    summary=_cninfo_summary(row),
                    published_at=_cninfo_published_at(row.get("announcementTime", "")),
                    source="巨潮资讯",
                    url=_cninfo_announcement_url(row.get("adjunctUrl", "") or row.get("announcementUrl", "")),
                    sentiment_score=0.0,
                    heat=2.0,
                )
            )
        if items:
            items.sort(key=lambda item: item.published_at or "", reverse=True)
            news_map[symbol] = items
    total = sum(len(items) for items in news_map.values())
    return NewsLoadResult(
        provider=descriptor.key,
        label=descriptor.label,
        news_map=news_map,
        source_path=CNINFO_NOTICE_ENDPOINT,
        summary=f"{descriptor.label} 已载入 {total} 条公告",
    )


def load_news_from_source(config: NewsSourceConfig) -> NewsLoadResult:
    descriptor = get_news_source_descriptor(config.provider)
    if descriptor.key == "csv":
        file_path = Path(str(config.path or "")).expanduser()
        if not str(file_path):
            raise ValueError("本地 CSV 消息源需要先选择一个消息文件。")
        news_map = load_news_catalysts_from_csv(file_path)
        total = sum(len(items) for items in news_map.values())
        return NewsLoadResult(
            provider=descriptor.key,
            label=descriptor.label,
            news_map=news_map,
            source_path=str(file_path),
            summary=f"{descriptor.label} 已载入 {total} 条消息",
        )
    if descriptor.key == "sample":
        if not _SAMPLE_NEWS_PATH.exists():
            raise FileNotFoundError(f"示例消息文件不存在：{_SAMPLE_NEWS_PATH}")
        news_map = load_news_catalysts_from_csv(_SAMPLE_NEWS_PATH)
        total = sum(len(items) for items in news_map.values())
        return NewsLoadResult(
            provider=descriptor.key,
            label=descriptor.label,
            news_map=news_map,
            source_path=str(_SAMPLE_NEWS_PATH),
            summary=f"{descriptor.label} 已载入 {total} 条消息",
        )
    if descriptor.key == "cninfo_api":
        return _load_cninfo_news(config, descriptor)
    raise NotImplementedError(
        f"{descriptor.label} 仍处于预留状态，当前版本先保留接入位，待拿到正式授权或接口文档后再启用。"
    )
