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
CNINFO_TOP_SEARCH_ENDPOINT = "https://www.cninfo.com.cn/new/information/topSearch/query"
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
_CNINFO_TYPE_LABELS = {
    "010301": "年报",
    "011301": "分红预案",
    "012301": "续聘审计",
    "012303": "高管变动",
    "012330": "可持续发展",
    "012913": "审计报告",
    "01239901": "董事会决议",
    "011905": "股东会决议",
    "011906": "股东会资料",
    "012111": "业绩快报",
    "012001": "投资者关系",
    "012903": "法律意见",
}
_CNINFO_POSITIVE_KEYWORDS = {
    "分红": 4.0,
    "利润分配": 4.0,
    "回购": 4.0,
    "增持": 4.0,
    "中标": 4.0,
    "订单": 3.5,
    "预增": 3.5,
    "快报": 3.0,
    "年报": 2.5,
    "年度报告": 2.5,
    "年度报告摘要": 2.0,
    "季报": 2.5,
    "半年报": 2.5,
    "可转债": 2.0,
    "董事会决议": 1.5,
    "续聘": 1.0,
}
_CNINFO_NEGATIVE_KEYWORDS = {
    "投资者关系": -4.5,
    "摘要": -0.5,
    "独立董事述职": -2.0,
    "法律意见": -1.5,
    "会议资料": -2.0,
    "提示性公告": -1.0,
}
_CNINFO_HIGH_PRIORITY_KEYWORDS = (
    "分红",
    "利润分配",
    "回购",
    "增持",
    "中标",
    "订单",
    "预增",
    "快报",
    "年报",
    "年度报告",
    "季报",
    "半年报",
)
_CNINFO_TRANSLATION_RULES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (("利润分配", "分红", "股息"), "分红预案", "偏稳健催化，适合看高股息、防御线和资金回流。"),
    (("业绩快报", "预增", "扭亏"), "业绩快报", "业绩确认型催化，先看利润兑现和预期差。"),
    (("年度报告", "年报", "季报", "半年报"), "定期报告", "业绩确认型催化，适合看业绩兑现和估值修复。"),
    (("回购", "增持"), "资本动作", "资本动作催化，先看资金态度和回购力度。"),
    (("中标", "订单", "合同"), "订单催化", "订单兑现型催化，适合看题材扩散和业绩映射。"),
    (("董事会决议", "股东会决议", "股东大会决议"), "治理动作", "治理/资本动作催化，需看是否配套分红、回购或融资安排。"),
    (("高管", "聘任", "任职资格"), "高管变动", "治理层变化催化，先看是否伴随战略调整。"),
    (("可转债", "定增", "融资"), "融资事项", "资金工具催化，需看融资节奏和摊薄预期。"),
    (("续聘", "审计"), "审计安排", "中性治理催化，更多影响合规和审计预期。"),
    (("投资者关系", "说明会", "交流会"), "交流信息", "偏低信号公告，更多用于跟踪市场沟通。"),
)
_CNINFO_CLUSTER_RULES: tuple[tuple[tuple[str, ...], str, str], ...] = (
    (
        ("年报", "年度报告", "年报摘要", "利润分配", "分红", "快报", "审计", "内部控制", "可持续发展"),
        "年报季",
        "适合一起看业绩、分红和审计口径，判断资金会不会继续做估值修复。",
    ),
    (
        ("董事会", "股东会", "决议", "聘任", "任职资格", "独立董事"),
        "治理动作",
        "治理类公告通常需要和分红、回购、融资安排一起看，单独交易价值偏中性。",
    ),
    (
        ("回购", "增持", "可转债", "融资"),
        "资本动作",
        "资本动作更适合结合资金承接和预期差来判断持续性。",
    ),
)


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
    NewsSourceDescriptor("mixed_api", "公告+线索混排", "优先展示巨潮公告，再把本地或示例线索按统一排序混入同一条消息流。"),
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
    raw_type_name = _normalize_text(item.get("announcementTypeName", ""))
    if raw_type_name:
        parts.append(raw_type_name)
    raw_type_codes = _normalize_text(item.get("announcementType", ""))
    if raw_type_codes:
        for code in [piece.strip() for piece in raw_type_codes.split("||") if piece.strip()]:
            label = _CNINFO_TYPE_LABELS.get(code, "")
            if label and label not in parts:
                parts.append(label)
    raw_type_desc = _normalize_text(item.get("announcementTypeDesc", ""))
    if raw_type_desc and raw_type_desc not in parts:
        parts.append(raw_type_desc)
    for key in ("secName", "orgName", "batchNum"):
        value = _normalize_text(item.get(key, ""))
        if value and value not in parts:
            parts.append(value)
    return " | ".join(parts[:3])


def _news_source_tier(source: str) -> str:
    normalized = _normalize_text(source).lower()
    if any(token in normalized for token in ("巨潮", "cninfo", "上交所", "深交所", "公告", "互动易", "e互动", "公司公告")):
        return "A"
    if any(token in normalized for token in ("财联社", "证券时报", "上证报", "中证报", "东方财富", "同花顺", "界面", "wind", "choice", "示例")):
        return "B"
    if any(token in normalized for token in ("股吧", "雪球", "微博", "论坛", "传闻", "社群", "自媒体", "小作文")):
        return "C"
    return "B"


def _news_source_rank(source: str) -> float:
    return {"A": 3.0, "B": 2.0, "C": 1.0}.get(_news_source_tier(source), 2.0)


def _parse_published_at(value: str) -> datetime | None:
    text = _normalize_text(value)
    if not text:
        return None
    for pattern in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text[: len(pattern)], pattern)
        except ValueError:
            continue
    return None


def _news_rank_score(item: NewsCatalyst) -> float:
    published = _parse_published_at(item.published_at)
    recency = 0.0
    if published is not None:
        delta_days = max((date.today() - published.date()).days, 0)
        recency = max(0.0, 6.0 - min(delta_days, 6))
    return _news_source_rank(item.source) * 10.0 + float(item.heat or 0.0) + recency


def _news_dedupe_key(item: NewsCatalyst) -> tuple[str, str, str]:
    title = _normalize_text(item.title)
    title = re.sub(r"^[\u4e00-\u9fa5A-Za-z0-9（）()]{4,40}(股份有限公司|有限责任公司)", "", title, count=1)
    title = title.lstrip("关于：:·-—（）()")
    normalized_title = re.sub(r"\s+", "", title.lower())
    published = _normalize_text(item.published_at)[:10]
    return item.symbol, normalized_title, published


def _merge_news_maps(*maps: dict[str, list[NewsCatalyst]]) -> dict[str, list[NewsCatalyst]]:
    merged: dict[str, dict[tuple[str, str, str], NewsCatalyst]] = {}
    for news_map in maps:
        for symbol, items in (news_map or {}).items():
            bucket = merged.setdefault(symbol, {})
            for item in items:
                key = _news_dedupe_key(item)
                current = bucket.get(key)
                if current is None or _news_rank_score(item) > _news_rank_score(current):
                    bucket[key] = item
    ordered: dict[str, list[NewsCatalyst]] = {}
    for symbol, bucket in merged.items():
        items = list(bucket.values())
        items.sort(key=lambda item: (_news_rank_score(item), item.published_at or "", item.title), reverse=True)
        ordered[symbol] = items
    return ordered


def _cninfo_primary_label(title: str, type_summary: str) -> str:
    combined = f"{title} {type_summary}"
    for keywords, label, _hint in _CNINFO_TRANSLATION_RULES:
        if any(keyword in combined for keyword in keywords):
            return label
    if "董事会" in combined or "股东会" in combined:
        return "治理动作"
    return type_summary.split("|", 1)[0].strip() or "公告"


def _cninfo_trading_hint(title: str, type_summary: str) -> str:
    combined = f"{title} {type_summary}"
    for keywords, _label, hint in _CNINFO_TRANSLATION_RULES:
        if any(keyword in combined for keyword in keywords):
            return hint
    return "中性公告催化，先看是否会被主线资金继续放大。"


def _cninfo_display_summary(title: str, item: dict[str, object], sec_name: str) -> str:
    type_summary = _cninfo_summary(item) or sec_name
    label = _cninfo_primary_label(title, type_summary)
    hint = _cninfo_trading_hint(title, type_summary)
    return f"{label} | {hint}"


def _cninfo_short_title(title: str, sec_name: str) -> str:
    short = _normalize_text(title)
    if sec_name and short.startswith(sec_name):
        short = short[len(sec_name):].lstrip("：:，,、-— ")
    short = re.sub(r"^[\u4e00-\u9fa5A-Za-z0-9（）()]{4,40}(股份有限公司|有限责任公司)", "", short, count=1)
    short = short.lstrip("：:，,、-— ")
    if short.startswith("关于") and short.endswith("公告"):
        short = short[2:]
    return short or _normalize_text(title)


def _cninfo_cluster_info(title: str, summary: str) -> tuple[str, str]:
    combined = f"{title} {summary}"
    for keywords, label, hint in _CNINFO_CLUSTER_RULES:
        if any(keyword in combined for keyword in keywords):
            return label, hint
    return "", ""


def _merge_cninfo_items(items: list[NewsCatalyst]) -> list[NewsCatalyst]:
    groups: dict[tuple[str, str], list[NewsCatalyst]] = {}
    passthrough: list[NewsCatalyst] = []
    for item in items:
        cluster_label, cluster_hint = _cninfo_cluster_info(item.title, item.summary)
        if not cluster_label:
            passthrough.append(item)
            continue
        key = ((item.published_at or "")[:10], cluster_label)
        groups.setdefault(key, []).append(
            NewsCatalyst(
                symbol=item.symbol,
                title=item.title,
                summary=item.summary + f" || {cluster_hint}",
                published_at=item.published_at,
                source=item.source,
                url=item.url,
                sentiment_score=item.sentiment_score,
                heat=item.heat,
            )
        )

    merged: list[NewsCatalyst] = list(passthrough)
    for (_date_key, cluster_label), cluster_items in groups.items():
        cluster_items.sort(key=lambda current: (current.heat, current.published_at or "", current.title), reverse=True)
        if len(cluster_items) <= 2:
            merged.extend(
                [
                    NewsCatalyst(
                        symbol=item.symbol,
                        title=item.title,
                        summary=item.summary.split(" || ", 1)[0],
                        published_at=item.published_at,
                        source=item.source,
                        url=item.url,
                        sentiment_score=item.sentiment_score,
                        heat=item.heat,
                    )
                    for item in cluster_items
                ]
            )
            continue
        lead = cluster_items[0]
        hint = lead.summary.split(" || ", 1)[1] if " || " in lead.summary else ""
        lead_summary = lead.summary.split(" || ", 1)[0]
        merged.append(
            NewsCatalyst(
                symbol=lead.symbol,
                title=lead.title,
                summary=f"{lead_summary} | 同日另有 {len(cluster_items) - 1} 条配套公告",
                published_at=lead.published_at,
                source=lead.source,
                url=lead.url,
                sentiment_score=lead.sentiment_score,
                heat=lead.heat,
            )
        )
        extra_titles = [item.title for item in cluster_items[1:4]]
        merged.append(
            NewsCatalyst(
                symbol=lead.symbol,
                title=f"{cluster_label}配套公告（{len(cluster_items) - 1}条）",
                summary=f"{cluster_label} | 同日合并 {len(cluster_items) - 1} 条：{' / '.join(extra_titles)} | {hint}",
                published_at=lead.published_at,
                source=lead.source,
                url=cluster_items[1].url if len(cluster_items) > 1 else lead.url,
                sentiment_score=lead.sentiment_score,
                heat=max(0.5, cluster_items[1].heat - 0.2 if len(cluster_items) > 1 else lead.heat - 0.2),
            )
        )
    merged.sort(key=lambda item: (item.heat, item.published_at or "", item.title), reverse=True)
    return merged


def _cninfo_relevance_score(title: str, signal_text: str) -> float:
    text = f"{title} {signal_text}"
    score = 0.0
    for keyword, weight in _CNINFO_POSITIVE_KEYWORDS.items():
        if keyword in text:
            score += weight
    for keyword, weight in _CNINFO_NEGATIVE_KEYWORDS.items():
        if keyword in text:
            score += weight
    if any(keyword in title for keyword in _CNINFO_HIGH_PRIORITY_KEYWORDS):
        score += 1.0
    return score


def _cninfo_keep_item(title: str, signal_text: str, published_at: str, recent_days: int) -> bool:
    score = _cninfo_relevance_score(title, signal_text)
    if score >= 0.5:
        return True
    if any(token in title for token in _CNINFO_HIGH_PRIORITY_KEYWORDS):
        return True
    try:
        published = datetime.strptime((published_at or "")[:19], "%Y-%m-%d %H:%M:%S")
        return published.date() >= date.today() - timedelta(days=max(int(recent_days or 20) - 1, 1))
    except ValueError:
        return False


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


def _lookup_cninfo_org_id(symbol: str, symbol_names: dict[str, str], timeout: float) -> tuple[str, str]:
    code = extract_stock_id(symbol)
    candidates = [code]
    display_name = _normalize_text(symbol_names.get(symbol, ""))
    if display_name:
        candidates.append(display_name)
    for key_word in candidates:
        query_url = CNINFO_TOP_SEARCH_ENDPOINT + "?" + urllib.parse.urlencode({"keyWord": key_word, "maxNum": 10})
        response = _fetch_json(query_url, method="POST", data={}, timeout=timeout)
        if not isinstance(response, list):
            continue
        for item in response:
            if not isinstance(item, dict):
                continue
            if _normalize_text(item.get("code", "")) != code:
                continue
            org_id = _normalize_text(item.get("orgId", ""))
            sec_name = _normalize_text(item.get("zwjc", "")) or display_name
            if org_id:
                return org_id, sec_name
    return "", display_name


def _load_cninfo_news(config: NewsSourceConfig, descriptor: NewsSourceDescriptor) -> NewsLoadResult:
    symbols = [normalize_symbol(symbol) for symbol in config.symbols if normalize_symbol(symbol)]
    if not symbols:
        raise ValueError("巨潮公告适配器需要至少 1 只股票代码。")
    news_map: dict[str, list[NewsCatalyst]] = {}
    for symbol in symbols:
        org_id, sec_name = _lookup_cninfo_org_id(symbol, config.symbol_names, config.timeout)
        if not org_id:
            continue
        payload = {
            "stock": f"{extract_stock_id(symbol)},{org_id}",
            "pageSize": max(1, min(int(config.limit_per_symbol or 3), 10)),
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
            published_at = _cninfo_published_at(row.get("announcementTime", ""))
            signal_text = _cninfo_summary(row) or sec_name
            summary = _cninfo_display_summary(title, row, sec_name)
            if not _cninfo_keep_item(title, signal_text, published_at, config.recent_days):
                continue
            items.append(
                NewsCatalyst(
                    symbol=symbol,
                    title=_cninfo_short_title(title, sec_name),
                    summary=summary,
                    published_at=published_at,
                    source="巨潮资讯",
                    url=_cninfo_announcement_url(row.get("adjunctUrl", "") or row.get("announcementUrl", "")),
                    sentiment_score=0.0,
                    heat=max(0.5, 2.0 + _cninfo_relevance_score(title, signal_text)),
                )
            )
        if items:
            items = _merge_cninfo_items(items)
            news_map[symbol] = items[: max(1, min(int(config.limit_per_symbol or 3), 10))]
    total = sum(len(items) for items in news_map.values())
    return NewsLoadResult(
        provider=descriptor.key,
        label=descriptor.label,
        news_map=news_map,
        source_path=CNINFO_NOTICE_ENDPOINT,
        summary=f"{descriptor.label} 已载入 {total} 条公告",
    )


def _load_mixed_news(config: NewsSourceConfig, descriptor: NewsSourceDescriptor) -> NewsLoadResult:
    cninfo_descriptor = get_news_source_descriptor("cninfo_api")
    primary = _load_cninfo_news(config, cninfo_descriptor)

    secondary_provider = "sample"
    if str(config.path or "").strip():
        try:
            secondary = load_news_from_source(
                NewsSourceConfig(
                    provider="csv",
                    path=config.path,
                    symbols=config.symbols,
                    symbol_names=dict(config.symbol_names),
                    limit_per_symbol=config.limit_per_symbol,
                    recent_days=config.recent_days,
                    timeout=config.timeout,
                )
            )
            secondary_provider = "csv"
        except Exception:
            secondary = load_news_from_source(NewsSourceConfig(provider="sample"))
            secondary_provider = "sample"
    else:
        secondary = load_news_from_source(NewsSourceConfig(provider="sample"))

    news_map = _merge_news_maps(primary.news_map, secondary.news_map)
    limit = max(1, min(int(config.limit_per_symbol or 3), 10))
    news_map = {symbol: items[:limit] for symbol, items in news_map.items()}
    total = sum(len(items) for items in news_map.values())
    secondary_label = resolve_news_source_label(secondary_provider)
    return NewsLoadResult(
        provider=descriptor.key,
        label=descriptor.label,
        news_map=news_map,
        source_path=f"{primary.source_path} + {secondary.source_path}",
        summary=f"{descriptor.label} 已载入 {total} 条消息（巨潮公告 + {secondary_label}）",
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
    if descriptor.key == "mixed_api":
        return _load_mixed_news(config, descriptor)
    if descriptor.key == "cninfo_api":
        return _load_cninfo_news(config, descriptor)
    raise NotImplementedError(
        f"{descriptor.label} 仍处于预留状态，当前版本先保留接入位，待拿到正式授权或接口文档后再启用。"
    )
