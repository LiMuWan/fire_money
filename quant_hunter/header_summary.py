from __future__ import annotations


def build_header_summary(
    *,
    page_key: str,
    current_name: str,
    market_value: str,
    refresh_value: str,
    focus_full: str,
    focus_compact: str,
    pulse_headline: str,
    pulse_compact: str,
    next_step: str,
    next_step_compact: str,
    meta_text: str,
    meta_compact: str,
) -> dict[str, str]:
    workspace_compact_map = {
        "overview": "总览",
        "scanner": "扫描",
        "recommend": "推荐",
        "broker": "交易",
        "detail": "复盘",
        "auth": "接入",
        "board": "看板",
        "config": "配置",
    }
    return {
        "workspace_full": current_name,
        "workspace_compact": workspace_compact_map.get(page_key, current_name),
        "focus_full": focus_full,
        "focus_compact": focus_compact,
        "market_full": market_value,
        "market_compact": market_value,
        "refresh_full": refresh_value,
        "refresh_compact": refresh_value,
        "pulse_full": pulse_headline,
        "pulse_compact": pulse_compact,
        "next_full": next_step,
        "next_compact": next_step_compact,
        "meta_full": meta_text,
        "meta_compact": meta_compact,
    }
