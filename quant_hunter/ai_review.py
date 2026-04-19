from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .models import DailyAnalysis, NewsCatalyst, PriceBar, RecommendationRow, ScanRow, StockProfile
from .strategy_registry import resolved_primary_strategy

DEFAULT_AI_BASE_URL = "https://api.openai.com/v1"
DEFAULT_AI_MODEL = "gpt-5.4"
DEFAULT_AI_REASONING_EFFORT = "medium"
_ALLOWED_REASONING_EFFORTS = {"minimal", "low", "medium", "high"}


@dataclass(frozen=True)
class AIReviewConfig:
    base_url: str = DEFAULT_AI_BASE_URL
    api_key: str = ""
    model: str = DEFAULT_AI_MODEL
    reasoning_effort: str = DEFAULT_AI_REASONING_EFFORT
    max_output_tokens: int = 900
    timeout_seconds: float = 45.0


@dataclass(frozen=True)
class AIReviewResult:
    symbol: str
    stock_name: str
    model: str
    reviewed_at: str
    summary: str
    content: str


@dataclass(frozen=True)
class AIReviewStreamEvent:
    symbol: str
    stock_name: str
    model: str
    delta: str
    text: str
    event_type: str = "response.output_text.delta"


def _compact_text(value: object, limit: int = 220) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _safe_float(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _normalize_reasoning_effort(value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _ALLOWED_REASONING_EFFORTS else DEFAULT_AI_REASONING_EFFORT


def normalize_ai_review_config(config: AIReviewConfig) -> AIReviewConfig:
    base_url = str(config.base_url or DEFAULT_AI_BASE_URL).strip() or DEFAULT_AI_BASE_URL
    model = str(config.model or DEFAULT_AI_MODEL).strip() or DEFAULT_AI_MODEL
    max_output_tokens = max(int(config.max_output_tokens or 0), 256)
    timeout_seconds = max(float(config.timeout_seconds or 0.0), 10.0)
    return AIReviewConfig(
        base_url=base_url,
        api_key=str(config.api_key or "").strip(),
        model=model,
        reasoning_effort=_normalize_reasoning_effort(config.reasoning_effort),
        max_output_tokens=max_output_tokens,
        timeout_seconds=timeout_seconds,
    )


def _responses_endpoint(base_url: str) -> str:
    base = str(base_url or DEFAULT_AI_BASE_URL).strip().rstrip("/")
    if not base:
        base = DEFAULT_AI_BASE_URL
    if base.endswith("/responses"):
        return base
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/responses"


def _build_review_payload(config: AIReviewConfig, prompt: str, *, stream: bool) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": config.model,
        "input": [
            {
                "role": "system",
                "content": (
                    "你是量化研究产品里的单票复核助手。请在研究辅助视角下，基于给定上下文给出清晰、"
                    "克制、执行导向的中文评测。不要输出 JSON，不要输出 markdown 表格。"
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "max_output_tokens": int(config.max_output_tokens),
    }
    reasoning_effort = _normalize_reasoning_effort(config.reasoning_effort)
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}
    if stream:
        payload["stream"] = True
    return payload


def _build_review_request(config: AIReviewConfig, payload: dict[str, Any], *, stream: bool) -> urllib.request.Request:
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    return urllib.request.Request(
        _responses_endpoint(config.base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )


def _response_error_message(payload: Any, fallback: str) -> str:
    if isinstance(payload, dict):
        error = payload.get("error", {})
        if isinstance(error, dict):
            message = str(error.get("message", "") or "").strip()
            if message:
                return message
        message = str(payload.get("message", "") or "").strip()
        if message:
            return message
    return fallback


def _openai_request(request: urllib.request.Request, *, timeout_seconds: float):
    try:
        return urllib.request.urlopen(request, timeout=float(timeout_seconds))
    except urllib.error.HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            error_body = ""
        detail = error_body.strip()
        if detail:
            try:
                payload = json.loads(detail)
                message = _response_error_message(payload, detail)
            except json.JSONDecodeError:
                message = detail
            raise RuntimeError(f"OpenAI 请求失败（HTTP {exc.code}）：{message}") from exc
        raise RuntimeError(f"OpenAI 请求失败（HTTP {exc.code}）。") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OpenAI 网络请求失败：{exc.reason}") from exc


def _iter_sse_events(response):
    event_name = ""
    data_lines: list[str] = []

    def flush():
        nonlocal event_name, data_lines
        if not data_lines:
            event_name = ""
            return None
        raw_data = "\n".join(data_lines).strip()
        event_name = event_name.strip()
        data_lines = []
        if not raw_data or raw_data == "[DONE]":
            event_name = ""
            return None
        payload = json.loads(raw_data)
        if isinstance(payload, dict) and event_name and "type" not in payload:
            payload["type"] = event_name
        event_name = ""
        return payload if isinstance(payload, dict) else None

    while True:
        raw_line = response.readline()
        if not raw_line:
            payload = flush()
            if payload is not None:
                yield payload
            break
        line = raw_line.decode("utf-8", errors="replace").rstrip("\r\n")
        if not line:
            payload = flush()
            if payload is not None:
                yield payload
            continue
        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.split(":", 1)[1].strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.split(":", 1)[1].lstrip())


def _build_review_result(
    *,
    row: RecommendationRow,
    model: str,
    content: str,
    now_fn,
) -> AIReviewResult:
    summary = next((line.strip() for line in content.splitlines() if line.strip()), "")
    if summary.startswith("结论："):
        summary = summary.split("：", 1)[1].strip() or summary
    return AIReviewResult(
        symbol=row.symbol,
        stock_name=row.stock_name,
        model=model,
        reviewed_at=now_fn().strftime("%Y-%m-%d %H:%M:%S"),
        summary=_compact_text(summary, 80) or "AI 评测已完成",
        content=content.strip(),
    )


def _extract_output_text(payload: Any) -> str:
    if isinstance(payload, dict):
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        output = payload.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                for content in item.get("content", []) or []:
                    if not isinstance(content, dict):
                        continue
                    text = content.get("text")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            if parts:
                return "\n".join(parts).strip()

    collected: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            node_type = str(node.get("type", "") or "").strip().lower()
            text = node.get("text")
            if node_type in {"output_text", "text"} and isinstance(text, str) and text.strip():
                collected.append(text.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    if collected:
        return "\n".join(collected).strip()
    return ""


def build_recommendation_review_prompt(
    row: RecommendationRow,
    *,
    news_items: list[NewsCatalyst] | None = None,
    profile: StockProfile | None = None,
    scan_row: ScanRow | None = None,
    analyses: list[DailyAnalysis] | None = None,
    bars: list[PriceBar] | None = None,
) -> str:
    news_lines = []
    for index, item in enumerate(list(news_items or [])[:3], start=1):
        news_lines.append(
            f"{index}. 标题：{_compact_text(item.title, 80)} | 来源：{_compact_text(item.source, 28) or '未知'} | "
            f"时间：{_compact_text(item.published_at, 24) or '未知'} | 摘要：{_compact_text(item.summary, 120) or '无'}"
        )
    if not news_lines:
        news_lines.append("1. 暂无外部消息，请按技术面和已有评分做研究辅助判断。")

    analysis_lines = []
    for item in list(analyses or [])[-3:]:
        analysis_lines.append(
            f"- {item.date} | 标签 {item.label} | 分数 {item.score} | 收盘 {item.close:.2f} | 原因：{_compact_text(item.reason, 90) or '无'}"
        )
    if not analysis_lines:
        analysis_lines.append("- 暂无单票分析快照。")

    bar_lines = []
    for item in list(bars or [])[-5:]:
        bar_lines.append(
            f"- {item.date} | O {item.open:.2f} H {item.high:.2f} L {item.low:.2f} C {item.close:.2f} V {item.volume:.0f}"
        )
    if not bar_lines:
        bar_lines.append("- 暂无近期 K 线摘要。")

    prompt_lines = [
        "你是桌面量化研究产品里的 AI 复核助手，只做研究辅助，不替代人工最终决策。",
        "请根据下面的结构化上下文，对当前推荐标的做一份简洁、可执行、偏交易复核风格的中文评测。",
        "输出要求：",
        "1. 使用中文。",
        "2. 不要写免责声明，不要重复原始字段。",
        "3. 严格使用下面这些标题，并保留顺序。",
        "4. 每个标题下尽量 1 到 4 行，结论要明确。",
        "",
        "请严格输出以下结构：",
        "结论：",
        "一句话：",
        "风险等级：",
        "执行建议：",
        "核心理由：",
        "消息面复核：",
        "关键价位：",
        "下一步：",
        "",
        "[当前标的]",
        f"股票：{row.stock_name} ({row.stock_id} / {row.symbol})",
        f"动作：{row.action} | 机会分层：{row.opportunity_tier or '待观察'} | 主策略：{resolved_primary_strategy(row, default='掘龙决策') or '掘龙决策'}",
        f"主线：{row.mainline_tag or row.theme_name or '待确认'} | 主线角色：{row.mainline_role or '待确认'} | 风险灯：{row.mainline_risk_flag or '待评估'}",
        (
            f"评分：总分 {float(row.total_score or 0.0):.1f} | 技术 {float(row.technical_score or 0.0):.1f} | "
            f"位置 {float(row.position_score or 0.0):.1f} | 持续 {float(row.persistence_score or 0.0):.1f} | "
            f"消息 {float(row.news_score or 0.0):.1f} | 回测 {float(row.backtest_quality_score or 0.0):.1f}"
        ),
        (
            f"执行准备：{float(row.execution_readiness or 0.0):.1f} | 置信：{float(row.confidence_score or 0.0):.1f} | "
            f"窗口：{float(row.mainline_window_score or 0.0):.1f} | 风险收益比：{float(row.risk_reward_ratio or 0.0):.2f}"
        ),
        (
            f"价格计划：入场 {_safe_float(row.entry_price or row.close):.2f} | 止损 {_safe_float(row.stop_price):.2f} | "
            f"目标 {_safe_float(row.target_price):.2f} | 收盘 {_safe_float(row.close):.2f}"
        ),
        f"逻辑：{_compact_text(row.rationale, 260) or '无'}",
        f"催化：{_compact_text(row.catalyst, 140) or '无'}",
        f"下一步关注：{_compact_text(row.next_focus, 140) or '无'}",
        f"失效条件：{_compact_text(row.invalidation_reason, 140) or '无'}",
        f"暂不执行原因：{_compact_text(row.reject_reason, 140) or '无'}",
        "",
        "[个股补充]",
        f"股票资料：行业 {_compact_text(getattr(profile, 'industry', ''), 40) or '未知'} | 龙头 {'是' if getattr(profile, 'is_leader', False) else '否'}",
        f"备注：{_compact_text(getattr(profile, 'notes', ''), 180) or '无'}",
        f"扫描理由：{_compact_text(getattr(scan_row, 'reason', ''), 180) or '无'}",
        "",
        "[近期消息]",
        *news_lines,
        "",
        "[近期分析]",
        *analysis_lines,
        "",
        "[近期 K 线摘要]",
        *bar_lines,
    ]
    return "\n".join(prompt_lines).strip()


def review_recommendation_with_openai(
    config: AIReviewConfig,
    row: RecommendationRow,
    *,
    news_items: list[NewsCatalyst] | None = None,
    profile: StockProfile | None = None,
    scan_row: ScanRow | None = None,
    analyses: list[DailyAnalysis] | None = None,
    bars: list[PriceBar] | None = None,
    now_fn=datetime.now,
) -> AIReviewResult:
    config = normalize_ai_review_config(config)
    if not config.api_key:
        raise ValueError("未配置 OpenAI API Key。")

    prompt = build_recommendation_review_prompt(
        row,
        news_items=news_items,
        profile=profile,
        scan_row=scan_row,
        analyses=analyses,
        bars=bars,
    )
    payload = _build_review_payload(config, prompt, stream=False)
    request = _build_review_request(config, payload, stream=False)
    with _openai_request(request, timeout_seconds=config.timeout_seconds) as response:
        raw_body = response.read().decode("utf-8")

    try:
        response_payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenAI 返回了无法解析的 JSON。") from exc

    content = _extract_output_text(response_payload)
    if not content:
        raise RuntimeError("OpenAI 已返回结果，但未解析到正文内容。")

    return _build_review_result(row=row, model=config.model, content=content, now_fn=now_fn)


def stream_recommendation_review_with_openai(
    config: AIReviewConfig,
    row: RecommendationRow,
    *,
    news_items: list[NewsCatalyst] | None = None,
    profile: StockProfile | None = None,
    scan_row: ScanRow | None = None,
    analyses: list[DailyAnalysis] | None = None,
    bars: list[PriceBar] | None = None,
    on_event=None,
    now_fn=datetime.now,
) -> AIReviewResult:
    config = normalize_ai_review_config(config)
    if not config.api_key:
        raise ValueError("未配置 OpenAI API Key。")

    prompt = build_recommendation_review_prompt(
        row,
        news_items=news_items,
        profile=profile,
        scan_row=scan_row,
        analyses=analyses,
        bars=bars,
    )
    payload = _build_review_payload(config, prompt, stream=True)
    request = _build_review_request(config, payload, stream=True)

    final_text = ""
    final_model = config.model

    with _openai_request(request, timeout_seconds=config.timeout_seconds) as response:
        for event in _iter_sse_events(response):
            event_type = str(event.get("type", "") or "").strip()
            if event_type == "response.output_text.delta":
                delta = str(event.get("delta", "") or "")
                if not delta:
                    continue
                final_text += delta
                if callable(on_event):
                    on_event(
                        AIReviewStreamEvent(
                            symbol=row.symbol,
                            stock_name=row.stock_name,
                            model=final_model,
                            delta=delta,
                            text=final_text,
                            event_type=event_type,
                        )
                    )
                continue

            if event_type == "response.output_text.done":
                text = str(event.get("text", "") or "")
                if text and len(text) >= len(final_text):
                    final_text = text
                continue

            if event_type in {"response.completed", "response.in_progress", "response.created"}:
                response_payload = event.get("response", event)
                if isinstance(response_payload, dict):
                    final_model = str(response_payload.get("model", "") or final_model)
                if event_type == "response.completed":
                    completed_text = _extract_output_text(response_payload)
                    if completed_text:
                        final_text = completed_text
                continue

            if event_type in {"error", "response.failed"}:
                raise RuntimeError(_response_error_message(event, "OpenAI 流式请求失败。"))

    if not final_text.strip():
        raise RuntimeError("OpenAI 流式请求已完成，但未解析到正文内容。")

    return _build_review_result(row=row, model=final_model, content=final_text, now_fn=now_fn)
