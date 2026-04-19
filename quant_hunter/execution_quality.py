from __future__ import annotations

from typing import Any


def build_execution_quality_snapshot(execution_recap: dict[str, object] | None) -> dict[str, object]:
    recap = dict(execution_recap or {})
    submitted_count = int(recap.get("submitted_count", 0) or 0)
    failed_count = int(recap.get("failed_count", 0) or 0)
    pending_count = int(recap.get("pending_count", 0) or 0)
    rejected_count = int(recap.get("rejected_count", 0) or 0)
    deviation_count = int(recap.get("deviation_count", 0) or 0)
    max_price_deviation_bps = abs(float(recap.get("max_price_deviation_bps", 0.0) or 0.0))
    max_quantity_deviation = abs(int(recap.get("max_quantity_deviation", 0) or 0))
    review_flags = [str(item) for item in list(recap.get("review_flags", []) or []) if str(item).strip()]
    latest_note = str(recap.get("latest_deviation_note", "") or "").strip()
    focus_symbols = [
        str(item)
        for item in list(recap.get("deviation_symbols", []) or recap.get("focus_symbols", []) or [])
        if str(item).strip()
    ]
    available = any(
        [
            submitted_count,
            failed_count,
            pending_count,
            rejected_count,
            deviation_count,
            review_flags,
            latest_note,
            focus_symbols,
        ]
    )
    if not available:
        return {
            "available": False,
            "score": 1.0,
            "penalty": 0.0,
            "label": "待接实盘",
            "budget_cap": 1.45,
            "summary": "尚无真实委托样本，暂不按执行质量调整预算。",
            "latest_note": "",
            "focus_symbols": [],
        }

    attempt_count = max(submitted_count + failed_count, 1)
    submitted_base = max(submitted_count, 1)
    failed_ratio = min(failed_count / attempt_count, 1.0)
    rejected_ratio = min(rejected_count / attempt_count, 1.0)
    pending_ratio = min(pending_count / submitted_base, 1.0)
    deviation_ratio = min(deviation_count / submitted_base, 1.0)
    price_penalty = min(max_price_deviation_bps / 80.0, 1.0) * 0.12
    quantity_penalty = min(max_quantity_deviation / 600.0, 1.0) * 0.08
    score = 1.0 - (
        failed_ratio * 0.26
        + rejected_ratio * 0.18
        + pending_ratio * 0.10
        + deviation_ratio * 0.22
        + price_penalty
        + quantity_penalty
    )
    score = round(min(max(score, 0.35), 1.0), 4)
    penalty = round(1.0 - score, 4)

    if score >= 0.88:
        label = "执行稳定"
        budget_cap = 1.45
        stance = "真实执行稳定，可保持原有主测预算节奏。"
    elif score >= 0.72:
        label = "轻微偏差"
        budget_cap = 1.18
        stance = "存在轻微执行偏差，主测可继续，但预算不要放大过快。"
    elif score >= 0.56:
        label = "执行承压"
        budget_cap = 1.0
        stance = "执行偏差已经开始吞噬研究优势，先回到等权或谨慎预算。"
    else:
        label = "执行失真"
        budget_cap = 0.85
        stance = "真实成交与计划偏差过大，优先修复执行链路，再谈放大战法。"

    note = latest_note or (review_flags[0] if review_flags else "")
    focus_text = f" 关注 {', '.join(focus_symbols[:3])}。" if focus_symbols else ""
    summary = f"{label} | 提交 {submitted_count} 笔 | 偏差 {deviation_count} 笔 | 拒绝 {rejected_count} 笔 | {stance}{focus_text}"
    if note:
        summary = f"{summary} 最新偏差：{note}"
    return {
        "available": True,
        "score": score,
        "penalty": penalty,
        "label": label,
        "budget_cap": round(budget_cap, 2),
        "summary": summary,
        "latest_note": note,
        "focus_symbols": focus_symbols,
    }


def build_execution_quality_bucket(
    bucket: str,
    recap: dict[str, object] | None,
    *,
    record_count: int = 0,
) -> dict[str, Any]:
    quality = build_execution_quality_snapshot(recap)
    payload = dict(recap or {})
    payload.update(
        {
            "bucket": str(bucket or ""),
            "record_count": int(record_count or 0),
            "execution_quality_available": bool(quality["available"]),
            "execution_quality_score": float(quality["score"]),
            "execution_quality_penalty": float(quality["penalty"]),
            "execution_quality_label": str(quality["label"]),
            "execution_budget_cap": float(quality["budget_cap"]),
            "execution_quality_summary": str(quality["summary"]),
            "execution_latest_note": str(quality["latest_note"]),
            "execution_focus_symbols": list(quality["focus_symbols"]),
        }
    )
    return payload
