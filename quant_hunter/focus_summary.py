from __future__ import annotations

from typing import Any, Callable


def clean_next_step(text: str, *, fallback: str) -> str:
    candidate = str(text or "").strip()
    if not candidate:
        return fallback
    invalid_tokens = ("????", "寰呰ˉ", "unknown", "null", "None")
    if any(token in candidate for token in invalid_tokens):
        return fallback
    candidate = candidate.replace("下一步：", "").replace("下一步", "").strip(" |:：")
    return candidate or fallback


def truncate_text(text: str, limit: int) -> str:
    value = str(text or "").strip()
    if len(value) <= limit:
        return value
    return value[:limit] + "…"


def build_focus_summary_parts(
    *,
    page: str,
    symbol: str,
    recommendation: Any,
    intent: Any,
    execution_row: dict | None,
    scan_row: Any,
    stock_name: str,
    stock_id: str,
    tone: str,
    badge: str,
    stage: str,
    stage_key: str,
    market_count: int = 0,
    news_brief: str = "",
    news_badge_html: str = "",
    display_action: Callable[[str], str],
    strategy_name: str = "",
) -> dict[str, object]:
    prefix_map = {
        "overview": "市场池摘要",
        "recommend": "推荐焦点",
        "detail": "复盘焦点",
    }
    empty_map = {
        "overview": "市场池摘要：等待从机会池、龙头榜或扫描页联动一只股票 | 审查 继续复核",
        "recommend": "推荐焦点：等待从机会池、龙头榜或交易计划联动一只股票 | 审查 继续复核",
        "detail": "复盘焦点：等待扫描、机会池或执行中控同步单票标的 | 审查 继续复核",
    }

    if not symbol:
        return {
            "symbol": "",
            "tone": "idle",
            "prefix": prefix_map.get(page, "焦点"),
            "plain_text": empty_map.get(page, "焦点：等待联动 | 审查 继续复核"),
            "stock_name": "",
            "stock_id": "--",
            "badge": "观察中",
            "stage": "等待联动",
            "stage_key": "watching",
            "next_step": "先从推荐、交易或复盘链路同步当前标的。",
            "next_brief": "先同步焦点",
            "news_brief": "",
            "news_badge_html": "",
            "aux_kind": "action",
            "aux_text": "审查 继续复核",
            "recommendation": None,
            "intent": None,
            "execution_row": None,
            "scan_row": scan_row,
        }

    if execution_row is not None:
        next_step = clean_next_step(
            str(execution_row.get("message", "") or ""),
            fallback="继续盯回执、成交与执行偏差。",
        )
    elif intent is not None:
        next_step = "先核对价格、数量、仓位和风险闸门。"
    elif recommendation is not None:
        next_step = clean_next_step(
            str(getattr(recommendation, "next_focus", "") or ""),
            fallback="继续盯主线、位置、承接和消息催化。",
        )
    else:
        next_step = "继续同步扫描、推荐与交易链路。"

    next_brief = truncate_text(next_step, 24)

    if recommendation is not None:
        risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "").strip()
        if risk_flag in {"低", "LOW"}:
            aux_kind, aux_text = "risk_low", f"风险 {risk_flag}"
        elif risk_flag in {"高", "HIGH"}:
            aux_kind, aux_text = "risk_high", f"风险 {risk_flag}"
        else:
            aux_kind, aux_text = "risk_mid", f"风险 {risk_flag or '待评估'}"
    elif intent is not None:
        aux_kind, aux_text = "action", display_action(getattr(intent, "side", ""))
    elif execution_row is not None:
        aux_kind, aux_text = "action", "回执跟踪"
    else:
        aux_kind, aux_text = "action", "审查 继续复核"

    if page == "overview":
        flow_label = getattr(recommendation, "fund_model", "") if recommendation is not None else "待同步"
        plain_text = (
            f"{prefix_map.get(page, '焦点')}：{stock_name} ({stock_id} / {symbol}) | "
            f"{badge} / {stage} | 审查 继续复核 | 资金 {flow_label or '待同步'} | "
            f"策略 {strategy_name or next_brief}{(' | ' + news_brief) if news_brief else ''}"
        )
    else:
        plain_text = (
            f"{prefix_map.get(page, '焦点')}：{stock_name} ({stock_id} / {symbol}) | "
            f"{badge} / {stage} | 审查 继续复核 | 动作 {next_brief}{(' | ' + news_brief) if news_brief else ''}"
        )

    return {
        "symbol": symbol,
        "tone": tone,
        "prefix": prefix_map.get(page, "焦点"),
        "plain_text": plain_text,
        "stock_name": stock_name,
        "stock_id": stock_id,
        "badge": badge,
        "stage": stage,
        "stage_key": stage_key,
        "next_step": next_step,
        "next_brief": next_brief,
        "news_brief": news_brief,
        "news_badge_html": news_badge_html,
        "aux_kind": aux_kind,
        "aux_text": aux_text,
        "recommendation": recommendation,
        "intent": intent,
        "execution_row": execution_row,
        "scan_row": scan_row,
    }
