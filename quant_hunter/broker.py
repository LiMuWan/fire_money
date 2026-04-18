from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import platform
import subprocess
import sys
from dataclasses import asdict, replace
from datetime import datetime
from pathlib import Path
from typing import Any

from .decision import TradeDecision
from .models import BrokerProfile, BrokerStatus, CashSnapshot, HoldingRecord, OrderIntent, ScanRow
from .risk import DEFAULT_RISK_CONTROLS, normalize_risk_profile, resolve_risk_controls
from .theme import display_mainline_role

_MIN_ORDER_RISK_REWARD_RATIO = DEFAULT_RISK_CONTROLS.plan_min_risk_reward_ratio
_WARN_TOTAL_LOSS_RATIO = DEFAULT_RISK_CONTROLS.warn_total_loss_ratio
_BLOCK_TOTAL_LOSS_RATIO = DEFAULT_RISK_CONTROLS.block_total_loss_ratio
_WARN_SINGLE_LOSS_RATIO = DEFAULT_RISK_CONTROLS.warn_single_loss_ratio
_BLOCK_SINGLE_LOSS_RATIO = DEFAULT_RISK_CONTROLS.block_single_loss_ratio
_WARN_SINGLE_POSITION_ASSET_RATIO = DEFAULT_RISK_CONTROLS.warn_single_position_asset_ratio
_BLOCK_SINGLE_POSITION_ASSET_RATIO = DEFAULT_RISK_CONTROLS.block_single_position_asset_ratio
_WARN_SINGLE_POSITION_CASH_RATIO = DEFAULT_RISK_CONTROLS.warn_single_position_cash_ratio
_BLOCK_SINGLE_POSITION_CASH_RATIO = DEFAULT_RISK_CONTROLS.block_single_position_cash_ratio

TEST_SUBMIT_REQUIRE_WHITELIST_TEXT = "\u6d4b\u8bd5\u5355\u6a21\u5f0f\u8981\u6c42\u5148\u586b\u5199\u6d4b\u8bd5\u767d\u540d\u5355\u80a1\u7968\u4ee3\u7801\u3002"
TEST_SUBMIT_WHITELIST_PREFIX = "\u6d4b\u8bd5\u767d\u540d\u5355\uff1a"
MAINLINE_GATE_PREFIX = "\u4e3b\u7ebf\u5ba1\u67e5 / \u4e3b\u7ebf\u95f8\u95e8\uff1a"
MAINLINE_REVIEW_PENDING_DETAIL = "\u672a\u547d\u4e2d\u5f53\u524d\u63a8\u8350\u6c60\uff0c\u9700\u4eba\u5de5\u590d\u6838\u540e\u518d\u51b3\u5b9a\u662f\u5426\u6267\u884c\u3002"
PORTFOLIO_FIT_GATE_PREFIX = "\u7ec4\u5408\u9002\u914d / \u6267\u884c\u95f8\u95e8\uff1a"
PORTFOLIO_FIT_PENDING_DETAIL = "\u5f53\u524d\u63a8\u8350\u6c60\u5c1a\u672a\u8f93\u51fa\u7ec4\u5408\u9002\u914d\u4fe1\u53f7\uff0c\u5148\u6309\u4e3b\u7ebf\u95f8\u95e8\u4eba\u5de5\u590d\u6838\u3002"


def _is_trade_plan_viable(price: float, stop_price: float, target_price: float, min_ratio: float = _MIN_ORDER_RISK_REWARD_RATIO) -> bool:
    if price <= 0 or stop_price <= 0 or target_price <= 0:
        return False
    estimated_loss = price - stop_price
    estimated_profit = target_price - price
    if estimated_loss <= 0 or estimated_profit <= 0:
        return False
    return (estimated_profit / estimated_loss) >= min_ratio


def _trade_plan_risk_reward_ratio(price: float, stop_price: float, target_price: float) -> float:
    if price <= 0 or stop_price <= 0 or target_price <= 0:
        return 0.0
    estimated_loss = price - stop_price
    estimated_profit = target_price - price
    if estimated_loss <= 0 or estimated_profit <= 0:
        return 0.0
    return estimated_profit / estimated_loss


def _display_mainline_role(value: str) -> str:
    return display_mainline_role(value)


def _mainline_gate_message(symbol_or_name: str, text: str) -> str:
    return f"{MAINLINE_GATE_PREFIX}{symbol_or_name} {text}"


def _portfolio_fit_gate_message(symbol_or_name: str, text: str) -> str:
    return f"{PORTFOLIO_FIT_GATE_PREFIX}{symbol_or_name} {text}"


def _normalize_test_submit_max_amount(value: float | int | None, default: float = 10000.0) -> float:
    try:
        amount = float(value or default)
    except (TypeError, ValueError):
        amount = default
    return round(max(amount, 100.0), 2)



def _parse_test_submit_symbol_whitelist(value: str | None) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    for token in ["\r", "\n", "\t", ";", "\uff1b", ",", "\uff0c", "\u3001", "|", " "]:
        text = text.replace(token, ",")
    items = [item.strip().upper() for item in text.split(",") if item.strip()]
    normalized: list[str] = []
    for item in items:
        compact = item.replace("-", "").replace("_", "")
        if compact.startswith("SHSE.") or compact.startswith("SZSE."):
            normalized.append(compact)
            continue
        if compact.startswith("SH") and len(compact) == 8 and compact[2:].isdigit():
            normalized.append(f"SHSE.{compact[2:]}")
            continue
        if compact.startswith("SZ") and len(compact) == 8 and compact[2:].isdigit():
            normalized.append(f"SZSE.{compact[2:]}")
            continue
        digits = "".join(ch for ch in compact if ch.isdigit())
        if len(digits) == 6:
            if digits[0] in {"5", "6", "9"}:
                normalized.append(f"SHSE.{digits}")
                continue
            if digits[0] in {"0", "1", "2", "3"}:
                normalized.append(f"SZSE.{digits}")
                continue
        normalized.append(compact)
    return list(dict.fromkeys(normalized))


def build_submission_intents(
    intents: list[OrderIntent],
    profile: BrokerProfile,
    *,
    lot_size: int = 100,
) -> tuple[list[OrderIntent], list[str], list[str]]:
    prepared = [replace(item) for item in list(intents or [])]
    if not getattr(profile, "test_submit_only", False):
        return prepared, [], []

    notes: list[str] = []
    blockers: list[str] = []
    lot_size = max(int(lot_size or 100), 1)
    max_buy_amount = _normalize_test_submit_max_amount(getattr(profile, "test_submit_max_amount", 10000.0), 10000.0)
    whitelist = _parse_test_submit_symbol_whitelist(getattr(profile, "test_submit_symbol_whitelist", ""))
    buy_intents = [item for item in prepared if str(getattr(item, "side", "") or "").upper() == "BUY"]

    if not whitelist:
        blockers.append(TEST_SUBMIT_REQUIRE_WHITELIST_TEXT)
        return [], [], blockers

    blocked_symbols = [
        str(getattr(item, "symbol", "") or "").upper()
        for item in prepared
        if str(getattr(item, "symbol", "") or "").upper() not in whitelist
    ]
    if blocked_symbols:
        blockers.append(f"以下股票不在测试白名单内：{', '.join(blocked_symbols)}。")
        return [], [], blockers

    if len(buy_intents) > 1:
        blockers.append(f"测试单模式一次只允许提交 1 笔买入委托，当前有 {len(buy_intents)} 笔。")
        return [], [], blockers

    guarded: list[OrderIntent] = []
    for item in prepared:
        side = str(getattr(item, "side", "") or "").upper()
        if side != "BUY":
            guarded.append(item)
            continue
        if item.price <= 0:
            blockers.append(f"{item.symbol} 的委托价格无效，无法按测试单模式换算数量。")
            continue
        max_quantity = int(max_buy_amount / float(item.price))
        max_quantity = (max_quantity // lot_size) * lot_size
        if max_quantity <= 0:
            blockers.append(f"{item.symbol} 当前价格约 {item.price:.3f}，测试单上限 {max_buy_amount:,.0f} 不足以下 1 手。")
            continue
        safe_quantity = min(int(item.quantity), max_quantity)
        if safe_quantity <= 0:
            blockers.append(f"{item.symbol} 的测试单数量换算后为 0，请检查预算和价格。")
            continue
        if safe_quantity < int(item.quantity):
            notes.append(
                f"{item.symbol} 买入数量已从 {int(item.quantity)} 调整为 {safe_quantity}，测试单买入金额不超过 {max_buy_amount:,.0f}。"
            )
        guarded.append(replace(item, quantity=safe_quantity))

    if buy_intents and not notes and not blockers:
        notes.append(f"测试单模式已开启，买入金额上限为 {max_buy_amount:,.0f}。")
    notes.append(f"{TEST_SUBMIT_WHITELIST_PREFIX}{', '.join(whitelist)}")
    return guarded, notes, blockers



def _priority_for_order(risk_reward_ratio: float, checks: list[str], risk_profile: str | None = None) -> str:
    controls = resolve_risk_controls(risk_profile)
    strong_threshold = max(controls.execution_low_risk_reward_ratio + 1.1, 2.2)
    medium_threshold = controls.execution_low_risk_reward_ratio
    if checks:
        return "C"
    if risk_reward_ratio >= strong_threshold:
        return "A"
    if risk_reward_ratio >= medium_threshold:
        return "B"
    return "C"


def _build_portfolio_risk_review(
    buy_intents: list[OrderIntent],
    *,
    available_cash: float,
    total_assets: float,
    risk_profile: str | None = None,
) -> dict[str, Any]:
    controls = resolve_risk_controls(risk_profile)
    warn_total_loss_ratio = controls.warn_total_loss_ratio
    block_total_loss_ratio = controls.block_total_loss_ratio
    warn_single_loss_ratio = controls.warn_single_loss_ratio
    block_single_loss_ratio = controls.block_single_loss_ratio
    warn_single_position_asset_ratio = controls.warn_single_position_asset_ratio
    block_single_position_asset_ratio = controls.block_single_position_asset_ratio
    warn_single_position_cash_ratio = controls.warn_single_position_cash_ratio
    block_single_position_cash_ratio = controls.block_single_position_cash_ratio
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []

    total_estimated_loss = sum(max(item.price - item.stop_price, 0.0) * item.quantity for item in buy_intents)
    total_loss_ratio = total_estimated_loss / total_assets if total_assets > 0 else 0.0
    if total_loss_ratio >= block_total_loss_ratio:
        blockers.append(f"组合预估止损亏损占总资产约 {total_loss_ratio:.1%}，超过执行阈值。")
    elif total_loss_ratio >= warn_total_loss_ratio:
        warnings.append(f"组合预估止损亏损占总资产约 {total_loss_ratio:.1%}，建议继续降杠杆。")

    for item in buy_intents:
        estimated_capital = item.price * item.quantity
        estimated_loss = max(item.price - item.stop_price, 0.0) * item.quantity
        loss_ratio = estimated_loss / total_assets if total_assets > 0 else 0.0
        asset_ratio = estimated_capital / total_assets if total_assets > 0 else 0.0
        cash_ratio = estimated_capital / available_cash if available_cash > 0 else 0.0
        status = "通过"
        detail_parts: list[str] = []

        if loss_ratio >= block_single_loss_ratio:
            status = "拦截"
            detail_parts.append(f"单笔止损亏损 {loss_ratio:.1%} 超限")
            blockers.append(f"{item.symbol} 单笔止损亏损占总资产约 {loss_ratio:.1%}，超过执行阈值。")
        elif loss_ratio >= warn_single_loss_ratio:
            if status != "拦截":
                status = "谨慎"
            detail_parts.append(f"单笔止损亏损 {loss_ratio:.1%} 偏高")
            warnings.append(f"{item.symbol} 单笔止损亏损占总资产约 {loss_ratio:.1%}，建议缩量。")

        if asset_ratio >= block_single_position_asset_ratio or (available_cash > 0 and cash_ratio >= block_single_position_cash_ratio):
            status = "拦截"
            detail_parts.append(f"单笔资金占用 {asset_ratio:.1%}/{cash_ratio:.1%}")
            blockers.append(f"{item.symbol} 单笔资金占用过高，容易造成持仓过度集中。")
        elif asset_ratio >= warn_single_position_asset_ratio or (available_cash > 0 and cash_ratio >= warn_single_position_cash_ratio):
            if status != "拦截":
                status = "谨慎"
            detail_parts.append(f"单笔资金占用 {asset_ratio:.1%}/{cash_ratio:.1%}")
            warnings.append(f"{item.symbol} 单笔资金占用偏高，建议分批或缩量执行。")

        rows.append(
            {
                "symbol": item.symbol,
                "estimated_capital": estimated_capital,
                "estimated_loss": estimated_loss,
                "loss_ratio": round(loss_ratio, 4),
                "asset_usage_ratio": round(asset_ratio, 4),
                "cash_usage_ratio": round(cash_ratio, 4) if available_cash > 0 else 0.0,
                "status": status,
                "detail": " | ".join(detail_parts) if detail_parts else "仓位风险可控",
            }
        )

    for row in rows:
        if row["loss_ratio"] >= block_single_loss_ratio or row["asset_usage_ratio"] >= block_single_position_asset_ratio:
            row["status_code"] = "BLOCKED"
        elif row["loss_ratio"] >= warn_single_loss_ratio or row["asset_usage_ratio"] >= warn_single_position_asset_ratio:
            row["status_code"] = "CAUTION"
        else:
            row["status_code"] = "PASS"
        if row["cash_usage_ratio"] >= block_single_position_cash_ratio:
            row["status_code"] = "BLOCKED"
        elif row["cash_usage_ratio"] >= warn_single_position_cash_ratio and row["status_code"] == "PASS":
            row["status_code"] = "CAUTION"

    return {
        "status": "拦截" if blockers else ("谨慎" if warnings else "通过"),
        "rows": rows,
        "status_code": "BLOCKED" if blockers else ("CAUTION" if warnings else "PASS"),
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "total_estimated_loss": total_estimated_loss,
        "total_loss_ratio": round(total_loss_ratio, 4),
    }


def _build_mainline_review(order_intents: list[OrderIntent], recommendations: list[Any] | None = None) -> dict[str, Any]:
    recommendation_map = {
        getattr(item, "symbol", ""): item
        for item in (recommendations or [])
        if getattr(item, "symbol", "")
    }
    blockers: list[str] = []
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    pass_count = 0
    missing_count = 0

    for intent in order_intents:
        recommendation = recommendation_map.get(intent.symbol)
        if recommendation is None:
            missing_count += 1
            rows.append(
                {
                    "symbol": intent.symbol,
                    "name": intent.symbol,
                    "theme": "未匹配",
                    "rank": 0,
                    "role": "--",
                    "window_score": 0.0,
                    "risk_flag": "待核对",
                    "status": "待核对",
                    "detail": MAINLINE_REVIEW_PENDING_DETAIL,
                }
            )
            if intent.side == "BUY":
                warnings.append(_mainline_gate_message(intent.symbol, "未命中当前推荐池，建议人工复核。"))
            continue

        theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "未分类"
        rank = int(getattr(recommendation, "mainline_rank", getattr(recommendation, "theme_rank", 0)) or 0)
        role = str(getattr(recommendation, "mainline_role", "") or "")
        role_label = _display_mainline_role(role)
        window_score = float(getattr(recommendation, "mainline_window_score", 0.0) or 0.0)
        risk_flag = str(getattr(recommendation, "mainline_risk_flag", "") or "--")
        failure_risk = float(getattr(recommendation, "theme_failure_risk", 0.0) or 0.0)

        status = "通过"
        detail = f"{theme_name} 第 {rank or '--'} 主线位 | {role_label} | 窗口 {window_score:.1f} | 风险 {risk_flag}"
        if intent.side == "BUY":
            if role in {"ELIMINATED", "NOISE"}:
                status = "拦截"
                blockers.append(
                    _mainline_gate_message(
                        getattr(recommendation, "stock_name", intent.symbol),
                        f"已处于{role_label}，不建议新开仓。",
                    )
                )
            elif rank > 3:
                status = "拦截"
                blockers.append(
                    _mainline_gate_message(
                        getattr(recommendation, "stock_name", intent.symbol),
                        "已跌出主线前 3，暂不建议新开仓。",
                    )
                )
            elif risk_flag == "高" or failure_risk >= 72.0:
                status = "拦截"
                blockers.append(
                    _mainline_gate_message(
                        getattr(recommendation, "stock_name", intent.symbol),
                        "主线风险偏高，建议暂缓执行。",
                    )
                )
            elif window_score < 50.0:
                status = "拦截"
                blockers.append(
                    _mainline_gate_message(
                        getattr(recommendation, "stock_name", intent.symbol),
                        "主线窗口不足，等待更清晰买点。",
                    )
                )
            elif role == "FOLLOW" or window_score < 66.0 or risk_flag == "中":
                status = "谨慎"
                warnings.append(
                    _mainline_gate_message(
                        getattr(recommendation, "stock_name", intent.symbol),
                        "更适合缩量试错或等待确认。",
                    )
                )
            else:
                pass_count += 1
        else:
            status = "通过"
            pass_count += 1
            if rank > 3 or risk_flag == "高":
                detail += " | 当前减仓/卖出动作与主线风险一致。"

        rows.append(
            {
                "symbol": intent.symbol,
                "name": getattr(recommendation, "stock_name", intent.symbol),
                "theme": theme_name,
                "rank": rank,
                "role": role_label,
                "window_score": round(window_score, 1),
                "risk_flag": risk_flag,
                "status": status,
                "detail": detail,
            }
        )

    overall_status = "通过"
    if blockers:
        overall_status = "拦截"
    elif warnings:
        overall_status = "谨慎"
    elif missing_count:
        overall_status = "待核对"

    return {
        "status": overall_status,
        "rows": rows,
        "blockers": blockers,
        "warnings": warnings,
        "pass_count": pass_count,
        "missing_count": missing_count,
    }


def _build_portfolio_fit_review(order_intents: list[OrderIntent], recommendations: list[Any] | None = None) -> dict[str, Any]:
    recommendation_map = {
        getattr(item, "symbol", ""): item
        for item in (recommendations or [])
        if getattr(item, "symbol", "")
    }
    rows: list[dict[str, Any]] = []
    blockers: list[str] = []
    warnings: list[str] = []
    pass_count = 0
    caution_count = 0
    blocked_count = 0
    unevaluated_count = 0
    fit_scores: list[float] = []
    diversification_scores: list[float] = []
    concentration_penalties: list[float] = []

    for intent in order_intents:
        recommendation = recommendation_map.get(intent.symbol)
        if recommendation is None:
            rows.append(
                {
                    "symbol": intent.symbol,
                    "name": intent.symbol,
                    "fit_score": 0.0,
                    "diversification_score": 0.0,
                    "concentration_penalty_score": 0.0,
                    "status": "待核对",
                    "status_code": "PENDING",
                    "detail": PORTFOLIO_FIT_PENDING_DETAIL,
                }
            )
            unevaluated_count += 1
            continue

        stock_name = getattr(recommendation, "stock_name", intent.symbol)
        fit_score = float(getattr(recommendation, "portfolio_fit_score", 0.0) or 0.0)
        diversification_score = float(getattr(recommendation, "diversification_score", 0.0) or 0.0)
        concentration_penalty_score = float(getattr(recommendation, "concentration_penalty_score", 0.0) or 0.0)
        opportunity_tier = str(getattr(recommendation, "opportunity_tier", "") or "待确认")
        theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "未分类"

        detail = (
            f"{theme_name} | 组合适配 {fit_score:.0f} | 分散度 {diversification_score:.0f} | "
            f"集中惩罚 {concentration_penalty_score:.0f} | {opportunity_tier}"
        )
        status = "通过"
        status_code = "PASS"

        if str(getattr(intent, "side", "") or "").upper() in {"SELL", "REDUCE"}:
            detail = f"{detail} | 卖出/减仓可优先释放组合拥挤或风险预算。"
        elif fit_score <= 0 and diversification_score <= 0 and concentration_penalty_score <= 0:
            status = "待核对"
            status_code = "PENDING"
            detail = PORTFOLIO_FIT_PENDING_DETAIL
            unevaluated_count += 1
        elif fit_score < 38.0 or concentration_penalty_score >= 68.0:
            status = "拦截"
            status_code = "BLOCKED"
            blocked_count += 1
            blockers.append(
                _portfolio_fit_gate_message(
                    stock_name,
                    f"组合适配 {fit_score:.0f} / 集中惩罚 {concentration_penalty_score:.0f}，当前不建议推进新委托。",
                )
            )
        elif fit_score < 56.0 or concentration_penalty_score >= 42.0 or (diversification_score > 0 and diversification_score < 42.0):
            status = "谨慎"
            status_code = "CAUTION"
            caution_count += 1
            warnings.append(
                _portfolio_fit_gate_message(
                    stock_name,
                    f"组合适配 {fit_score:.0f}，建议缩量或等待更分散的进场窗口。",
                )
            )
        else:
            pass_count += 1

        fit_scores.append(fit_score)
        diversification_scores.append(diversification_score)
        concentration_penalties.append(concentration_penalty_score)
        rows.append(
            {
                "symbol": intent.symbol,
                "name": stock_name,
                "fit_score": round(fit_score, 2),
                "diversification_score": round(diversification_score, 2),
                "concentration_penalty_score": round(concentration_penalty_score, 2),
                "status": status,
                "status_code": status_code,
                "detail": detail,
            }
        )

    return {
        "status": "拦截" if blockers else ("谨慎" if warnings else ("待核对" if rows and pass_count == 0 and caution_count == 0 and blocked_count == 0 else "通过")),
        "status_code": "BLOCKED" if blockers else ("CAUTION" if warnings else ("PENDING" if rows and pass_count == 0 and caution_count == 0 and blocked_count == 0 else "PASS")),
        "rows": rows,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": list(dict.fromkeys(warnings)),
        "pass_count": pass_count,
        "caution_count": caution_count,
        "blocked_count": blocked_count,
        "unevaluated_count": unevaluated_count,
        "avg_fit_score": round(sum(fit_scores) / len(fit_scores), 4) if fit_scores else 0.0,
        "avg_diversification_score": round(sum(diversification_scores) / len(diversification_scores), 4) if diversification_scores else 0.0,
        "max_concentration_penalty_score": round(max(concentration_penalties), 4) if concentration_penalties else 0.0,
    }


def _recommendation_map(recommendations: list[Any] | None) -> dict[str, Any]:
    return {
        str(getattr(item, "symbol", "") or ""): item
        for item in (recommendations or [])
        if str(getattr(item, "symbol", "") or "")
    }


def _review_row_by_symbol(review: dict[str, Any] | None, symbol: str) -> dict[str, Any]:
    rows = list((review or {}).get("rows", []) or [])
    target = str(symbol or "")
    return next((row for row in rows if str(row.get("symbol", "")) == target), {})


def normalize_execution_record(row: Any) -> dict[str, Any]:
    normalized = normalize_submission_result(row)

    def _pick_value_local(source: Any, candidates: list[str], fallback: Any = None) -> Any:
        if source is None:
            return fallback
        if isinstance(source, dict):
            for key in candidates:
                if key in source and source[key] is not None:
                    return source[key]
        for key in candidates:
            if hasattr(source, key):
                value = getattr(source, key)
                if value is not None:
                    return value
        return fallback

    symbol = str(_pick_value_local(row, ["symbol", "sec_id", "security", "instrument"], fallback=normalized["symbol"]) or normalized["symbol"])
    side = str(_pick_value_local(row, ["side", "order_side", "direction"], fallback="") or "").upper()
    timestamp = str(
        _pick_value_local(
            row,
            ["timestamp", "create_time", "created_at", "trade_time", "update_time", "updated_at", "order_time", "entrust_time"],
            fallback="",
        )
        or ""
    )
    price_value = _pick_value_local(row, ["price", "order_price", "limit_price", "entrust_price"], fallback=0.0)
    quantity_value = _pick_value_local(row, ["quantity", "volume", "order_qty", "entrust_amount", "entrust_qty"], fallback=0)
    try:
        price = float(price_value or 0.0)
    except (TypeError, ValueError):
        price = 0.0
    try:
        quantity = int(float(quantity_value or 0))
    except (TypeError, ValueError):
        quantity = 0

    normalized.update(
        {
            "symbol": symbol,
            "side": side,
            "timestamp": timestamp,
            "price": f"{price:.3f}" if price > 0 else "",
            "quantity": str(quantity) if quantity > 0 else "",
        }
    )
    return normalized


def merge_submission_records_with_execution_records(
    records: list[dict[str, Any]],
    execution_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str]]:
    updated_records = [dict(item) for item in records or []]
    notes: list[str] = []
    if not updated_records or not execution_records:
        return updated_records, notes

    for execution in execution_records:
        symbol = str(execution.get("symbol", "") or "")
        side = str(execution.get("side", "") or "").upper()
        order_id = str(execution.get("order_id", "") or "")
        target_index = -1
        if order_id:
            for index in range(len(updated_records) - 1, -1, -1):
                if str(updated_records[index].get("order_id", "") or "") == order_id:
                    target_index = index
                    break
        if target_index < 0 and symbol:
            for index in range(len(updated_records) - 1, -1, -1):
                record = updated_records[index]
                if str(record.get("symbol", "") or "") != symbol:
                    continue
                if side and str(record.get("side", "") or "").upper() != side:
                    continue
                if str(record.get("fill_status", "") or "").upper() in {"FILLED", "REJECTED", "CANCELLED"}:
                    continue
                target_index = index
                break
        if target_index < 0:
            continue

        record = dict(updated_records[target_index])
        changed = False
        for field in ("order_id", "order_status", "fill_status", "fill_price", "fill_quantity", "message", "price", "quantity", "timestamp"):
            value = execution.get(field, "")
            if value in {None, ""}:
                continue
            text_value = str(value)
            if str(record.get(field, "") or "") != text_value:
                record[field] = text_value
                changed = True
        if changed:
            updated_records[target_index] = record
            status_text = str(record.get("fill_status", record.get("order_status", "")) or "")
            notes.append(f"{symbol} 成交回报已更新：{status_text}")

    return updated_records, notes


def _submission_result_is_structured(result: Any) -> bool:
    if isinstance(result, dict):
        keys = {str(key) for key in result.keys()}
        return any(
            key in keys
            for key in (
                "order_id",
                "fill_status",
                "filled_status",
                "fill_price",
                "filled_price",
                "avg_fill_price",
                "fill_quantity",
                "filled_quantity",
                "filled_volume",
                "trade_volume",
                "deal_volume",
                "deal_status",
                "exec_status",
            )
        )
    return False


def normalize_submission_result(result: Any, *, symbol: str = "", expected_quantity: int = 0) -> dict[str, Any]:
    def _pick_value_local(row: Any, candidates: list[str], fallback: Any = None) -> Any:
        if row is None:
            return fallback
        if isinstance(row, dict):
            for key in candidates:
                if key in row and row[key] is not None:
                    return row[key]
        for key in candidates:
            if hasattr(row, key):
                value = getattr(row, key)
                if value is not None:
                    return value
        return fallback

    payload = result if isinstance(result, dict) else {}
    result_text = str(
        _pick_value_local(
            payload or result,
            ["result", "message", "msg", "status_msg", "remark"],
            fallback=str(result or "submitted"),
        )
        or "submitted"
    )
    order_status = str(_pick_value_local(payload or result, ["order_status", "status"], fallback="SUBMITTED") or "SUBMITTED").upper()
    fill_price_value = _pick_value_local(
        payload or result,
        ["fill_price", "filled_price", "avg_fill_price", "filled_avg_price", "trade_price", "deal_price"],
        fallback=0.0,
    )
    fill_quantity_value = _pick_value_local(
        payload or result,
        ["fill_quantity", "filled_quantity", "filled_volume", "trade_volume", "deal_volume", "filled_qty"],
        fallback=0,
    )
    try:
        fill_price = float(fill_price_value or 0.0)
    except (TypeError, ValueError):
        fill_price = 0.0
    try:
        fill_quantity = int(float(fill_quantity_value or 0))
    except (TypeError, ValueError):
        fill_quantity = 0
    fill_status = str(
        _pick_value_local(
            payload or result,
            ["fill_status", "filled_status", "exec_status", "deal_status"],
            fallback="",
        )
        or ""
    ).upper()
    if not fill_status:
        if fill_quantity > 0:
            fill_status = "FILLED" if expected_quantity <= 0 or fill_quantity >= expected_quantity else "PARTIAL"
        else:
            fill_status = "PENDING"
    order_id = str(_pick_value_local(payload or result, ["order_id", "cl_ord_id", "entrust_no", "order_no"], fallback="") or "")

    if _submission_result_is_structured(result):
        display_text = result_text
        if symbol and symbol not in display_text:
            display_text = f"{symbol}: {display_text}"
        if fill_quantity > 0 and fill_price > 0:
            display_text = f"{display_text} | 成交 {fill_quantity} @ {fill_price:.3f}"
    else:
        display_text = result_text

    return {
        "symbol": symbol or str(payload.get("symbol", "") or ""),
        "order_status": order_status,
        "fill_status": fill_status,
        "fill_price": f"{fill_price:.3f}" if fill_price > 0 else "",
        "fill_quantity": str(fill_quantity) if fill_quantity > 0 else "",
        "order_id": order_id,
        "message": result_text,
        "display_text": display_text,
    }


def _runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def _resolve_bridge_script() -> Path:
    runtime_root = _runtime_root()
    candidates = [
        runtime_root / "quant_hunter" / "sdk_bridge.py",
        runtime_root / "sdk_bridge.py",
    ]
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        meipass_root = Path(meipass)
        candidates.extend(
            [
                meipass_root / "quant_hunter" / "sdk_bridge.py",
                meipass_root / "sdk_bridge.py",
            ]
        )
    candidates.append(Path(__file__).resolve().with_name("sdk_bridge.py"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


PROJECT_ROOT = _runtime_root()
SDK_BRIDGE = _resolve_bridge_script()
_DEFAULT_BRIDGE_PYTHON_CACHE: str | None = None
_MODULE_AVAILABILITY_CACHE: dict[tuple[str, str], bool] = {}
_ENV_DIAG_CACHE: dict[tuple[str, str, bool, bool, str], dict[str, Any]] = {}


class EastmoneyBrokerAdapter:
    """Bridge between the desktop app and Eastmoney/MyQuant SDK workflows."""

    def diagnose_environment(self, profile: BrokerProfile) -> dict[str, Any]:
        cache_key = (
            str(profile.sdk_python_path or "").strip(),
            str(profile.sdk_module or "").strip(),
            bool(profile.token),
            bool(profile.account_id),
            str(profile.mode or "").strip(),
        )
        cached = _ENV_DIAG_CACHE.get(cache_key)
        if cached is not None:
            return dict(cached)
        bridge_python = self.resolve_bridge_python(profile)
        bridge_module_installed = self._module_available_in_interpreter(bridge_python, profile.sdk_module) if bridge_python else False
        module_installed = self._has_module(profile.sdk_module)
        runtime_supported = self._is_runtime_supported(profile.sdk_module, sys.version_info[:2])
        direct_ready = module_installed and runtime_supported and bool(profile.token) and bool(profile.account_id)
        bridge_ready = bool(bridge_python and bridge_module_installed and profile.token and profile.account_id)
        result = {
            "python_version": platform.python_version(),
            "sdk_module": profile.sdk_module,
            "module_installed": module_installed,
            "runtime_supported": runtime_supported,
            "direct_ready": direct_ready,
            "bridge_python": bridge_python or "",
            "bridge_module_installed": bridge_module_installed,
            "bridge_ready": bridge_ready,
            "mode": profile.mode,
        }
        _ENV_DIAG_CACHE[cache_key] = dict(result)
        return result

    def describe_status(self, profile: BrokerProfile) -> BrokerStatus:
        env = self.diagnose_environment(profile)
        note_lines = [
            "当前应用已支持扫描、回测、委托建议导出、SDK 账户同步和直接下单入口。",
            f"主程序 Python: {env['python_version']}",
            f"当前解释器 SDK: {'已安装' if env['module_installed'] else '未安装'} ({env['sdk_module']})",
        ]
        if env["bridge_python"]:
            note_lines.append(
                f"桥接解释器: {env['bridge_python']} | SDK {'已安装' if env['bridge_module_installed'] else '未安装'}"
            )
        if env["bridge_ready"]:
            note_lines.append("当前环境已满足桥接下单条件，将优先通过独立 Python 3.12 进程调用 SDK。")
        elif env["direct_ready"]:
            note_lines.append("当前环境满足直接 SDK 调用条件。")
        else:
            note_lines.append("当前环境未满足直接/桥接下单条件，建议继续使用委托建议 CSV 或 GM 实盘脚本。")
        return BrokerStatus(
            name="东方财富 / 东财掘金",
            mode=profile.mode,
            connected=bool((env["direct_ready"] or env["bridge_ready"]) and profile.mode == "sdk"),
            note="\n".join(note_lines),
        )

    def resolve_bridge_python(self, profile: BrokerProfile) -> str:
        if profile.sdk_python_path:
            return profile.sdk_python_path
        global _DEFAULT_BRIDGE_PYTHON_CACHE
        if _DEFAULT_BRIDGE_PYTHON_CACHE is not None:
            return _DEFAULT_BRIDGE_PYTHON_CACHE
        candidate = Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe"
        if candidate.exists():
            _DEFAULT_BRIDGE_PYTHON_CACHE = str(candidate)
            return _DEFAULT_BRIDGE_PYTHON_CACHE
        try:
            result = subprocess.run(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            _DEFAULT_BRIDGE_PYTHON_CACHE = result.stdout.strip()
            return _DEFAULT_BRIDGE_PYTHON_CACHE
        except Exception:
            return ""

    def build_order_intents(
        self,
        scan_rows: list[ScanRow],
        per_trade_budget: float,
        max_orders: int = 5,
        lot_size: int = 100,
    ) -> list[OrderIntent]:
        candidates = [row for row in scan_rows if row.label == "RECLAIM_LONG" and row.entry_price]
        intents: list[OrderIntent] = []
        for row in candidates[:max_orders]:
            if row.stop_price is None or row.target_price is None:
                continue
            if not _is_trade_plan_viable(row.entry_price, row.stop_price, row.target_price):
                continue
            quantity = int(per_trade_budget / row.entry_price)
            quantity = (quantity // lot_size) * lot_size
            if quantity < lot_size:
                continue
            intents.append(
                OrderIntent(
                    symbol=row.symbol,
                    side="BUY",
                    price=round(row.entry_price, 3),
                    quantity=quantity,
                    stop_price=round(row.stop_price, 3),
                    target_price=round(row.target_price, 3),
                    signal_date=row.signal_date,
                    reason=row.reason,
                )
            )
        return intents



    def export_order_plan(
        self,
        intents: list[OrderIntent],
        export_dir: str | Path,
        *,
        recommendations: list[Any] | None = None,
        execution_summary: dict[str, Any] | None = None,
    ) -> Path:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        output = root / f"eastmoney_order_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        recommendation_map = _recommendation_map(recommendations)
        fit_review = dict((execution_summary or {}).get("portfolio_fit_review", {}) or {})
        mainline_review = dict((execution_summary or {}).get("mainline_review", {}) or {})
        include_execution_context = bool(recommendation_map or execution_summary)
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            header = [
                "symbol",
                "side",
                "price",
                "quantity",
                "stop_price",
                "target_price",
                "signal_date",
                "reason",
            ]
            if include_execution_context:
                header.extend(
                    [
                        "opportunity_tier",
                        "risk_flag",
                        "risk_reward_ratio",
                        "portfolio_fit_score",
                        "diversification_score",
                        "concentration_penalty_score",
                        "portfolio_fit_status",
                        "portfolio_fit_detail",
                        "mainline_status",
                        "mainline_detail",
                    ]
                )
            writer.writerow(header)
            for item in intents:
                row = [
                    item.symbol,
                    item.side,
                    item.price,
                    item.quantity,
                    item.stop_price,
                    item.target_price,
                    item.signal_date,
                    item.reason,
                ]
                if include_execution_context:
                    recommendation = recommendation_map.get(item.symbol)
                    fit_row = _review_row_by_symbol(fit_review, item.symbol)
                    mainline_row = _review_row_by_symbol(mainline_review, item.symbol)
                    risk_reward_ratio = float(getattr(item, "risk_reward_ratio", 0.0) or 0.0)
                    row.extend(
                        [
                            getattr(recommendation, "opportunity_tier", "") if recommendation is not None else "",
                            getattr(recommendation, "mainline_risk_flag", "") if recommendation is not None else "",
                            risk_reward_ratio,
                            getattr(recommendation, "portfolio_fit_score", 0.0) if recommendation is not None else fit_row.get("fit_score", 0.0),
                            getattr(recommendation, "diversification_score", 0.0) if recommendation is not None else fit_row.get("diversification_score", 0.0),
                            getattr(recommendation, "concentration_penalty_score", 0.0) if recommendation is not None else fit_row.get("concentration_penalty_score", 0.0),
                            fit_row.get("status", ""),
                            fit_row.get("detail", ""),
                            mainline_row.get("status", ""),
                            mainline_row.get("detail", ""),
                        ]
                    )
                writer.writerow(row)
        return output

    def export_submission_records(
        self,
        records: list[dict[str, Any]],
        export_dir: str | Path,
        *,
        recommendations: list[Any] | None = None,
        execution_summary: dict[str, Any] | None = None,
    ) -> Path:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        output = root / f"eastmoney_submission_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        recommendation_map = _recommendation_map(recommendations)
        fit_review = dict((execution_summary or {}).get("portfolio_fit_review", {}) or {})
        mainline_review = dict((execution_summary or {}).get("mainline_review", {}) or {})
        include_execution_context = bool(
            recommendation_map
            or execution_summary
            or any(
                str(item.get("planned_price", "") or "")
                or str(item.get("planned_quantity", "") or "")
                or str(item.get("order_id", "") or "")
                or str(item.get("fill_price", "") or "")
                or str(item.get("fill_quantity", "") or "")
                for item in records
            )
        )
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            header = [
                "timestamp",
                "order_status",
                "fill_status",
                "symbol",
                "side",
                "price",
                "quantity",
                "failure_reason",
                "message",
            ]
            if include_execution_context:
                header.extend(
                    [
                        "order_id",
                        "fill_price",
                        "fill_quantity",
                        "planned_price",
                        "planned_quantity",
                        "planned_stop_price",
                        "planned_target_price",
                        "planned_risk_reward_ratio",
                        "opportunity_tier",
                        "portfolio_fit_score",
                        "diversification_score",
                        "concentration_penalty_score",
                        "portfolio_fit_status",
                        "portfolio_fit_detail",
                        "mainline_status",
                        "mainline_detail",
                    ]
                )
            writer.writerow(header)
            for item in records:
                symbol = str(item.get("symbol", "") or "")
                recommendation = recommendation_map.get(symbol)
                fit_row = _review_row_by_symbol(fit_review, symbol)
                mainline_row = _review_row_by_symbol(mainline_review, symbol)
                row = [
                    item.get("timestamp", ""),
                    item.get("order_status", item.get("status", "")),
                    item.get("fill_status", ""),
                    symbol,
                    item.get("side", ""),
                    item.get("price", ""),
                    item.get("quantity", ""),
                    item.get("failure_reason", ""),
                    item.get("message", ""),
                ]
                if include_execution_context:
                    row.extend(
                        [
                            item.get("order_id", ""),
                            item.get("fill_price", ""),
                            item.get("fill_quantity", ""),
                            item.get("planned_price", ""),
                            item.get("planned_quantity", ""),
                            item.get("planned_stop_price", ""),
                            item.get("planned_target_price", ""),
                            item.get("planned_risk_reward_ratio", ""),
                            item.get("opportunity_tier", getattr(recommendation, "opportunity_tier", "") if recommendation is not None else ""),
                            item.get("portfolio_fit_score", getattr(recommendation, "portfolio_fit_score", 0.0) if recommendation is not None else fit_row.get("fit_score", 0.0)),
                            item.get("diversification_score", getattr(recommendation, "diversification_score", 0.0) if recommendation is not None else fit_row.get("diversification_score", 0.0)),
                            item.get("concentration_penalty_score", getattr(recommendation, "concentration_penalty_score", 0.0) if recommendation is not None else fit_row.get("concentration_penalty_score", 0.0)),
                            fit_row.get("status", ""),
                            fit_row.get("detail", ""),
                            mainline_row.get("status", ""),
                            mainline_row.get("detail", ""),
                        ]
                    )
                writer.writerow(row)
        return output

    def create_templates(self, export_dir: str | Path) -> list[Path]:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        holdings = root / "eastmoney_holdings_template.csv"
        cash = root / "eastmoney_cash_template.csv"
        profile = root / "eastmoney_profile_template.json"

        with holdings.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["symbol", "quantity", "available", "cost_price", "market_value"])
            writer.writerow(["SHSE.600000", 1000, 1000, 10.23, 10400.0])

        with cash.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["available_cash", "total_assets"])
            writer.writerow([120000.0, 265000.0])

        profile.write_text(
            json.dumps(
                asdict(
                    BrokerProfile(
                        account_name="东方财富账户",
                        account_id="请填写",
                        mode="export",
                        export_dir=str(root),
                        sdk_module="gm.api",
                        sdk_python_path=self.resolve_bridge_python(BrokerProfile()),
                    )
                ),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return [holdings, cash, profile]

    def summarize_holdings(self, holdings: list[HoldingRecord], cash: CashSnapshot | None) -> str:
        market_value = sum(item.market_value for item in holdings)
        available = cash.available_cash if cash else 0.0
        total_assets = cash.total_assets if cash else market_value + available
        return "\n".join(
            [
                f"持仓只数: {len(holdings)}",
                f"持仓市值: {market_value:,.2f}",
                f"可用资金: {available:,.2f}",
                f"总资产: {total_assets:,.2f}",
            ]
        )

    def sync_account_via_sdk(self, profile: BrokerProfile) -> tuple[CashSnapshot, list[HoldingRecord]]:
        env = self.diagnose_environment(profile)
        if env["bridge_ready"]:
            payload = self._run_bridge(
                env["bridge_python"],
                "sync",
                {"token": profile.token, "account_id": profile.account_id, "sdk_module": profile.sdk_module},
            )
            cash = payload["cash"]
            holdings = payload["holdings"]
            return (
                CashSnapshot(cash["available_cash"], cash["total_assets"]),
                [HoldingRecord(**item) for item in holdings],
            )

        gm = self._prepare_sdk_direct(profile)
        cash_rows = self._call_first_available(gm, ["get_cash"], account_id=profile.account_id)
        cash_row = cash_rows[0] if isinstance(cash_rows, list) and cash_rows else cash_rows
        available_cash = self._pick_value(cash_row, ["available", "available_cash", "cash", "nav"], fallback=0.0)
        total_assets = self._pick_value(cash_row, ["nav", "total_assets", "asset", "market_value"], fallback=available_cash)
        cash_snapshot = CashSnapshot(float(available_cash or 0.0), float(total_assets or 0.0))

        positions = self._call_first_available(gm, ["get_position", "get_positions"], account_id=profile.account_id)
        holdings: list[HoldingRecord] = []
        for item in positions or []:
            symbol = self._pick_value(item, ["symbol", "sec_id", "security", "instrument"])
            if not symbol:
                continue
            quantity = int(float(self._pick_value(item, ["volume", "quantity", "amount"], fallback=0)))
            available = int(float(self._pick_value(item, ["available", "available_volume"], fallback=quantity)))
            cost_price = float(self._pick_value(item, ["vwap", "cost", "cost_price"], fallback=0.0))
            market_value = float(self._pick_value(item, ["market_value", "value"], fallback=cost_price * quantity))
            holdings.append(HoldingRecord(str(symbol), quantity, available, cost_price, market_value))
        return cash_snapshot, holdings

    def sync_execution_records_via_sdk(self, profile: BrokerProfile, limit: int = 40) -> list[dict[str, Any]]:
        env = self.diagnose_environment(profile)
        if env["bridge_ready"]:
            payload = self._run_bridge(
                env["bridge_python"],
                "execution",
                {
                    "token": profile.token,
                    "account_id": profile.account_id,
                    "sdk_module": profile.sdk_module,
                    "limit": int(limit),
                },
            )
            rows = list(payload.get("execution_records", []) or [])
            return [normalize_execution_record(item) for item in rows]

        gm = self._prepare_sdk_direct(profile)
        orders = self._call_optional_available(gm, ["get_orders", "get_unfinished_orders", "get_order"], account_id=profile.account_id)
        trades = self._call_optional_available(gm, ["get_execution_reports", "get_trades", "get_deals", "get_trade"], account_id=profile.account_id)
        combined: list[dict[str, Any]] = []
        for source in (orders or [], trades or []):
            if source is None:
                continue
            bucket = source if isinstance(source, list) else [source]
            combined.extend(normalize_execution_record(item) for item in bucket)
        deduped: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str, str]] = set()
        for item in combined:
            key = (
                str(item.get("order_id", "") or ""),
                str(item.get("symbol", "") or ""),
                str(item.get("side", "") or ""),
                str(item.get("timestamp", "") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[: max(int(limit or 0), 1)]

    def sync_execution_records_via_sdk(self, profile: BrokerProfile, limit: int = 40) -> list[dict[str, Any]]:
        env = self.diagnose_environment(profile)
        if env["bridge_ready"]:
            payload = self._run_bridge(
                env["bridge_python"],
                "execution",
                {
                    "token": profile.token,
                    "account_id": profile.account_id,
                    "sdk_module": profile.sdk_module,
                    "limit": int(limit),
                },
            )
            rows = list(payload.get("execution_records", []) or [])
            return [normalize_execution_record(item) for item in rows]

        gm = self._prepare_sdk_direct(profile)
        orders = self._call_optional_available(gm, ["get_orders", "get_unfinished_orders", "get_order"], account_id=profile.account_id)
        trades = self._call_optional_available(gm, ["get_execution_reports", "get_trades", "get_deals", "get_trade"], account_id=profile.account_id)
        combined: list[dict[str, Any]] = []
        for source in (orders or [], trades or []):
            if source is None:
                continue
            if isinstance(source, list):
                combined.extend(normalize_execution_record(item) for item in source)
            else:
                combined.append(normalize_execution_record(source))
        seen: set[tuple[str, str, str, str]] = set()
        deduped: list[dict[str, Any]] = []
        for item in combined:
            key = (
                str(item.get("order_id", "") or ""),
                str(item.get("symbol", "") or ""),
                str(item.get("side", "") or ""),
                str(item.get("timestamp", "") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped[: max(int(limit or 0), 1)]

    def submit_order_intents(self, profile: BrokerProfile, intents: list[OrderIntent]) -> list[str]:
        env = self.diagnose_environment(profile)
        if env["bridge_ready"]:
            payload = self._run_bridge(
                env["bridge_python"],
                "submit",
                {
                    "token": profile.token,
                    "account_id": profile.account_id,
                    "sdk_module": profile.sdk_module,
                    "intents": [asdict(item) for item in intents],
                },
            )
            results: list[Any] = []
            for item in payload["results"]:
                symbol = str(item.get("symbol", "") or "")
                expected_intent = next((intent for intent in intents if intent.symbol == symbol), None)
                expected_quantity = int(getattr(expected_intent, "quantity", 0) or 0)
                if _submission_result_is_structured(item):
                    results.append(normalize_submission_result(item, symbol=symbol, expected_quantity=expected_quantity))
                else:
                    results.append(f"{symbol}: {item['result']}")
            return results

        gm = self._prepare_sdk_direct(profile)
        order_func = getattr(gm, "order_volume", None)
        if not callable(order_func):
            raise RuntimeError("当前 SDK 中没有找到 order_volume 函数。")
        limit_type = self._resolve_attr(gm, ["OrderType_Limit", "ORDER_TYPE_LIMIT"])
        results: list[Any] = []
        for item in intents:
            side_value = self._resolve_order_side_value(gm, item.side)
            position_effect = self._resolve_position_effect_value(gm, item.side)
            kwargs = {
                "symbol": item.symbol,
                "volume": int(item.quantity),
                "side": side_value,
                "order_type": limit_type,
                "price": float(item.price),
                "account": profile.account_id,
            }
            if position_effect is not None:
                kwargs["position_effect"] = position_effect
            result = self._call_with_fallbacks(order_func, kwargs)
            if _submission_result_is_structured(result):
                results.append(normalize_submission_result(result, symbol=item.symbol, expected_quantity=int(item.quantity)))
            else:
                results.append(f"{item.symbol} {item.side} {item.quantity} @ {item.price}: {self._compact_result(result)}")
        return results

    def generate_gm_strategy_script(
        self,
        profile: BrokerProfile,
        intents: list[OrderIntent],
        export_dir: str | Path,
    ) -> Path:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        script_path = root / f"gm_live_orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py"
        orders_literal = json.dumps([asdict(item) for item in intents], ensure_ascii=False, indent=2)
        lines = [
            "from gm.api import *",
            "",
            f"set_token('{profile.token}')",
            f"ORDERS = {orders_literal}",
            "",
            "def _resolve_side(side):",
            "    if side == 'BUY':",
            "        return OrderSide_Buy",
            "    if side in {'SELL', 'REDUCE'}:",
            "        return OrderSide_Sell",
            "    raise ValueError(f'Unsupported order side: {side}')",
            "",
            "def _resolve_position_effect(side):",
            "    if side == 'BUY':",
            "        return globals().get('PositionEffect_Open')",
            "    if side in {'SELL', 'REDUCE'}:",
            "        return (",
            "            globals().get('PositionEffect_Close')",
            "            or globals().get('PositionEffect_CloseYesterday')",
            "            or globals().get('PositionEffect_CloseToday')",
            "        )",
            "    raise ValueError(f'Unsupported order side: {side}')",
            "",
            "def init(context):",
            "    for item in ORDERS:",
            "        kwargs = {",
            "            'symbol': item['symbol'],",
            "            'volume': int(item['quantity']),",
            "            'side': _resolve_side(item['side']),",
            "            'order_type': OrderType_Limit,",
            "            'price': float(item['price']),",
            f"            'account': '{profile.account_id}',",
            "        }",
            "        position_effect = _resolve_position_effect(item['side'])",
            "        if position_effect is not None:",
            "            kwargs['position_effect'] = position_effect",
            "        order_volume(**kwargs)",
            "    stop()",
            "",
            "if __name__ == '__main__':",
            "    run(",
            f"        strategy_id='{profile.strategy_id}',",
            "        filename=__file__,",
            "        mode=MODE_LIVE,",
            f"        token='{profile.token}',",
            "    )",
        ]
        script_path.write_text("\n".join(lines), encoding="utf-8")
        return script_path

    def _prepare_sdk_direct(self, profile: BrokerProfile):
        if not profile.token:
            raise ValueError("SDK 模式需要填写 token。")
        if not profile.account_id:
            raise ValueError("SDK 模式需要填写 account_id。")
        if not self._is_runtime_supported(profile.sdk_module, sys.version_info[:2]):
            raise RuntimeError("当前主程序运行时不适合直接调用该 SDK，请使用桥接 Python。")
        gm = self._load_sdk_module(profile.sdk_module)
        set_token = getattr(gm, "set_token", None)
        if callable(set_token):
            set_token(profile.token)
        return gm

    def _load_sdk_module(self, module_name: str):
        if not self._has_module(module_name):
            raise RuntimeError(f"未发现 SDK 模块: {module_name}")
        return importlib.import_module(module_name)

    def _run_bridge(self, python_executable: str, action: str, payload: dict[str, Any]) -> dict[str, Any]:
        result = subprocess.run(
            [python_executable, str(SDK_BRIDGE), action],
            cwd=PROJECT_ROOT,
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            message = result.stderr.strip() or result.stdout.strip() or "bridge failed"
            raise RuntimeError(f"桥接调用失败: {message}")
        return json.loads(result.stdout)

    def _module_available_in_interpreter(self, python_executable: str, module_name: str) -> bool:
        if not python_executable:
            return False
        cache_key = (python_executable, module_name)
        if cache_key in _MODULE_AVAILABILITY_CACHE:
            return _MODULE_AVAILABILITY_CACHE[cache_key]
        result = subprocess.run(
            [python_executable, str(SDK_BRIDGE), "diagnose"],
            cwd=PROJECT_ROOT,
            input=json.dumps({"sdk_module": module_name}),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            _MODULE_AVAILABILITY_CACHE[cache_key] = False
            return False
        try:
            available = bool(json.loads(result.stdout).get("module_installed"))
            _MODULE_AVAILABILITY_CACHE[cache_key] = available
            return available
        except Exception:
            _MODULE_AVAILABILITY_CACHE[cache_key] = False
            return False

    def _call_first_available(self, gm: Any, names: list[str], **kwargs):
        last_error: Exception | None = None
        for name in names:
            func = getattr(gm, name, None)
            if not callable(func):
                continue
            try:
                return func(**kwargs)
            except TypeError:
                try:
                    return func()
                except Exception as exc:
                    last_error = exc
            except Exception as exc:
                last_error = exc
        if last_error:
            raise last_error
        raise RuntimeError(f"SDK 中不存在这些函数: {', '.join(names)}")

    def _call_optional_available(self, gm: Any, names: list[str], **kwargs):
        for name in names:
            func = getattr(gm, name, None)
            if not callable(func):
                continue
            try:
                return func(**kwargs)
            except TypeError:
                try:
                    return func()
                except Exception:
                    continue
            except Exception:
                continue
        return None

    def _call_with_fallbacks(self, func, kwargs: dict[str, Any]):
        attempts = [
            kwargs,
            {key: value for key, value in kwargs.items() if key != "position_effect"},
            {key: value for key, value in kwargs.items() if key not in {"position_effect", "account"}},
        ]
        last_error: Exception | None = None
        for attempt in attempts:
            try:
                return func(**attempt)
            except TypeError as exc:
                last_error = exc
                continue
        if last_error:
            raise last_error
        raise RuntimeError("下单调用失败。")

    def _resolve_order_side_value(self, gm: Any, side: str):
        mapping = {
            "BUY": ["OrderSide_Buy", "ORDER_SIDE_BUY"],
            "SELL": ["OrderSide_Sell", "ORDER_SIDE_SELL"],
            "REDUCE": ["OrderSide_Sell", "ORDER_SIDE_SELL"],
        }
        if side not in mapping:
            raise ValueError(f"Unsupported order side: {side}")
        value = self._resolve_attr(gm, mapping[side])
        if value is None:
            raise RuntimeError(f"Missing SDK order side mapping for {side}")
        return value

    def _resolve_position_effect_value(self, gm: Any, side: str):
        if side == "BUY":
            return self._resolve_attr(gm, ["PositionEffect_Open", "POSITION_EFFECT_OPEN"])
        if side in {"SELL", "REDUCE"}:
            return self._resolve_attr(
                gm,
                [
                    "PositionEffect_Close",
                    "POSITION_EFFECT_CLOSE",
                    "PositionEffect_CloseYesterday",
                    "POSITION_EFFECT_CLOSE_YESTERDAY",
                    "PositionEffect_CloseToday",
                    "POSITION_EFFECT_CLOSE_TODAY",
                ],
            )
        raise ValueError(f"Unsupported order side: {side}")

    def _pick_value(self, row: Any, candidates: list[str], fallback: Any = None) -> Any:
        if row is None:
            return fallback
        if isinstance(row, dict):
            for key in candidates:
                if key in row and row[key] is not None:
                    return row[key]
        for key in candidates:
            if hasattr(row, key):
                value = getattr(row, key)
                if value is not None:
                    return value
        return fallback

    def _resolve_attr(self, obj: Any, names: list[str]):
        for name in names:
            if hasattr(obj, name):
                return getattr(obj, name)
        return None

    def _compact_result(self, result: Any) -> str:
        if result is None:
            return "submitted"
        text = str(result)
        return text if len(text) <= 120 else text[:117] + "..."

    def _is_runtime_supported(self, module_name: str, version_info: tuple[int, int]) -> bool:
        if module_name.startswith("gm") and version_info >= (3, 13):
            return False
        return True

    def _has_module(self, module_name: str) -> bool:
        try:
            return importlib.util.find_spec(module_name) is not None
        except ModuleNotFoundError:
            return False


def summarize_broker_execution(
    profile: BrokerProfile,
    env: dict[str, Any],
    order_intents: list[OrderIntent],
    holdings: list[HoldingRecord],
    cash_snapshot: CashSnapshot | None,
    recommendations: list[Any] | None = None,
    risk_profile: str | None = None,
) -> dict[str, Any]:
    buy_intents = [item for item in order_intents if item.side == "BUY"]
    estimated_capital = sum(item.price * item.quantity for item in buy_intents)
    estimated_loss = sum(max(item.price - item.stop_price, 0.0) * item.quantity for item in buy_intents)
    estimated_profit = sum(max(item.target_price - item.price, 0.0) * item.quantity for item in buy_intents)
    available_cash = cash_snapshot.available_cash if cash_snapshot else 0.0
    total_assets = cash_snapshot.total_assets if cash_snapshot else sum(item.market_value for item in holdings) + available_cash
    holding_map = {item.symbol: item for item in holdings}
    portfolio_risk_review = _build_portfolio_risk_review(
        buy_intents,
        available_cash=available_cash,
        total_assets=total_assets,
        risk_profile=risk_profile,
    )
    portfolio_fit_review = _build_portfolio_fit_review(order_intents, recommendations=recommendations)

    side_counts = {
        "BUY": sum(1 for item in order_intents if item.side == "BUY"),
        "SELL": sum(1 for item in order_intents if item.side == "SELL"),
        "REDUCE": sum(1 for item in order_intents if item.side == "REDUCE"),
        "WATCH": sum(1 for item in order_intents if item.side == "WATCH"),
    }
    symbols = [item.symbol for item in order_intents]
    blockers: list[str] = []
    warnings: list[str] = []

    if not profile.export_dir.strip():
        blockers.append("未设置导出目录")
    if not order_intents:
        blockers.append("暂无委托建议")
    if profile.mode == "sdk":
        if not profile.account_id.strip():
            blockers.append("缺少账户 ID")
        if not profile.token.strip():
            blockers.append("缺少 SDK Token")
        if not (env.get("direct_ready") or env.get("bridge_ready")):
            blockers.append("SDK 环境未就绪")
    else:
        warnings.append("当前为导出模式，下单前仍需人工导入券商终端")

    if buy_intents and available_cash <= 0:
        warnings.append("尚未同步可用资金，资金校验仅按预算估算")
    elif buy_intents and estimated_capital > available_cash:
        blockers.append("预计委托金额超过可用资金")

    if not holdings:
        warnings.append("尚未同步持仓，减仓/卖出可用数量需人工复核")
    if any(item.stop_price >= item.price for item in order_intents):
        warnings.append("部分委托止损价不低于委托价")
    if any(item.target_price <= item.price for item in order_intents):
        warnings.append("部分委托目标价不高于委托价")

    for item in order_intents:
        if item.side not in {"SELL", "REDUCE"}:
            continue
        holding = holding_map.get(item.symbol)
        if holding is None:
            blockers.append(f"{item.symbol} \u7f3a\u5c11\u6301\u4ed3\uff0c\u4e0d\u53ef\u6267\u884c\u5356\u51fa/\u51cf\u4ed3")
            continue
        if holding.available <= 0:
            blockers.append(f"{item.symbol} \u53ef\u5356\u6570\u91cf\u4e3a 0\uff0c\u4e0d\u53ef\u6267\u884c\u5356\u51fa/\u51cf\u4ed3")
            continue
        if item.quantity > holding.available:
            blockers.append(
                f"{item.symbol} \u53ef\u5356\u6570\u91cf\u4e0d\u8db3\uff1a\u59d4\u6258 {item.quantity} > \u53ef\u7528 {holding.available}"
            )

    mainline_review = _build_mainline_review(order_intents, recommendations=recommendations)
    blockers.extend(item for item in mainline_review["blockers"] if item not in blockers)
    warnings.extend(item for item in mainline_review["warnings"] if item not in warnings)
    blockers.extend(item for item in portfolio_risk_review["blockers"] if item not in blockers)
    warnings.extend(item for item in portfolio_risk_review["warnings"] if item not in warnings)
    blockers.extend(item for item in portfolio_fit_review["blockers"] if item not in blockers)
    warnings.extend(item for item in portfolio_fit_review["warnings"] if item not in warnings)

    blockers = list(dict.fromkeys(blockers))
    warnings = list(dict.fromkeys(warnings))
    normalized_risk_profile = normalize_risk_profile(risk_profile)

    if profile.mode == "sdk" and not blockers:
        readiness = "可直接提交"
    elif not blockers:
        readiness = "可导出执行"
    else:
        readiness = "待补齐"

    readiness_score = max(0, 100 - len(blockers) * 22 - len(warnings) * 8)
    risk_reward_ratio = estimated_profit / estimated_loss if estimated_loss > 0 else 0.0
    capital_usage_ratio = estimated_capital / available_cash if available_cash > 0 else 0.0
    asset_usage_ratio = estimated_capital / total_assets if total_assets > 0 else 0.0

    return {
        "readiness": readiness,
        "readiness_score": readiness_score,
        "estimated_capital": estimated_capital,
        "estimated_loss": estimated_loss,
        "estimated_profit": estimated_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "capital_usage_ratio": capital_usage_ratio,
        "asset_usage_ratio": asset_usage_ratio,
        "available_cash": available_cash,
        "total_assets": total_assets,
        "intent_count": len(order_intents),
        "holding_count": len(holdings),
        "side_counts": side_counts,
        "symbols": symbols,
        "blockers": blockers,
        "warnings": warnings,
        "mainline_review": mainline_review,
        "portfolio_risk_review": portfolio_risk_review,
        "portfolio_fit_review": portfolio_fit_review,
        "risk_profile": normalized_risk_profile,
    }


def describe_order_intent(item: OrderIntent, available_cash: float = 0.0, risk_profile: str | None = None) -> dict[str, Any]:
    estimated_capital = item.price * item.quantity
    estimated_loss = max(item.price - item.stop_price, 0.0) * item.quantity
    estimated_profit = max(item.target_price - item.price, 0.0) * item.quantity
    risk_reward_ratio = estimated_profit / estimated_loss if estimated_loss > 0 else 0.0
    capital_ratio = estimated_capital / available_cash if available_cash > 0 else 0.0

    checks: list[str] = []
    if item.quantity <= 0:
        checks.append("数量异常")
    if item.stop_price >= item.price:
        checks.append("止损价偏高")
    if item.target_price <= item.price:
        checks.append("目标价偏低")
    if available_cash > 0 and estimated_capital > available_cash:
        checks.append("超出可用资金")

    priority = _priority_for_order(risk_reward_ratio, checks, risk_profile=risk_profile)

    reason_summary = item.reason.strip().replace("\n", " ")
    if len(reason_summary) > 28:
        reason_summary = f"{reason_summary[:28].rstrip()}..."

    return {
        "priority": priority,
        "estimated_capital": estimated_capital,
        "estimated_loss": estimated_loss,
        "estimated_profit": estimated_profit,
        "risk_reward_ratio": risk_reward_ratio,
        "capital_ratio": capital_ratio,
        "reason_summary": reason_summary,
        "check_label": "通过" if not checks else " / ".join(checks[:2]),
        "checks": checks,
    }


def preview_position_changes(
    holdings: list[HoldingRecord],
    order_intents: list[OrderIntent],
) -> dict[str, Any]:
    current_positions = {item.symbol: item.quantity for item in holdings}
    available_positions = {item.symbol: item.available for item in holdings}
    deltas: dict[str, int] = {}
    for item in order_intents:
        if item.side == "BUY":
            delta = item.quantity
        elif item.side in {"SELL", "REDUCE"}:
            delta = -item.quantity
        else:
            delta = 0
        deltas[item.symbol] = deltas.get(item.symbol, 0) + delta

    rows: list[dict[str, Any]] = []
    for symbol in sorted(set(current_positions) | set(deltas)):
        before = current_positions.get(symbol, 0)
        available = available_positions.get(symbol, before)
        delta = deltas.get(symbol, 0)
        sell_quantity = max(-delta, 0)
        oversell = sell_quantity > available
        after = max(before + delta, 0)
        status = "新增"
        if oversell:
            status = "\u8d85\u5356"
        elif before > 0 and after == 0:
            status = "清仓"
        elif before > 0 and after > before:
            status = "加仓"
        elif before > 0 and 0 < after < before:
            status = "减仓"
        elif before > 0 and after == before:
            status = "不变"
        rows.append(
            {
                "symbol": symbol,
                "before": before,
                "available": available,
                "delta": delta,
                "after": after,
                "status": status,
                "oversell": oversell,
            }
        )

    high_risk_symbols = [
        item.symbol
        for item in order_intents
        if describe_order_intent(item).get("checks")
    ]
    high_risk_symbols.extend(item["symbol"] for item in rows if item["oversell"])
    high_risk_symbols = list(dict.fromkeys(high_risk_symbols))
    return {
        "rows": rows,
        "high_risk_symbols": high_risk_symbols,
        "new_symbol_count": sum(1 for item in rows if item["before"] == 0 and item["after"] > 0),
        "exit_symbol_count": sum(1 for item in rows if item["before"] > 0 and item["after"] == 0),
        "increase_count": sum(1 for item in rows if item["after"] > item["before"] and item["before"] > 0),
        "decrease_count": sum(1 for item in rows if 0 < item["after"] < item["before"]),
        "oversell_count": sum(1 for item in rows if item["oversell"]),
    }


def submission_record_execution_delta(record: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(record or {})

    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    planned_price = _safe_float(payload.get("planned_price"))
    submitted_price = _safe_float(payload.get("price"))
    fill_price = _safe_float(payload.get("fill_price"))
    actual_price = fill_price if fill_price > 0 else submitted_price
    planned_quantity = _safe_int(payload.get("planned_quantity"))
    submitted_quantity = _safe_int(payload.get("quantity"))
    fill_quantity = _safe_int(payload.get("fill_quantity"))
    actual_quantity = fill_quantity if fill_quantity > 0 else submitted_quantity

    price_deviation_bps = 0.0
    if planned_price > 0 and actual_price > 0:
        price_deviation_bps = round((actual_price - planned_price) / planned_price * 10000.0, 1)
    quantity_deviation = actual_quantity - planned_quantity if planned_quantity > 0 else 0
    has_price_baseline = planned_price > 0 and actual_price > 0
    has_quantity_baseline = planned_quantity > 0
    has_deviation = (has_price_baseline and abs(price_deviation_bps) >= 1.0) or (has_quantity_baseline and quantity_deviation != 0)

    note_parts: list[str] = []
    if has_price_baseline:
        if abs(price_deviation_bps) < 1.0:
            note_parts.append("价格与计划基本一致")
        elif price_deviation_bps > 0:
            note_parts.append(f"价格高于计划 {price_deviation_bps:.1f}bp")
        else:
            note_parts.append(f"价格低于计划 {abs(price_deviation_bps):.1f}bp")
    if has_quantity_baseline:
        if quantity_deviation == 0:
            note_parts.append("数量与计划一致")
        elif quantity_deviation > 0:
            note_parts.append(f"数量较计划增加 {quantity_deviation}")
        else:
            note_parts.append(f"数量较计划减少 {abs(quantity_deviation)}")

    return {
        "planned_price": planned_price,
        "actual_price": actual_price,
        "planned_quantity": planned_quantity,
        "actual_quantity": actual_quantity,
        "price_deviation_bps": price_deviation_bps,
        "quantity_deviation": quantity_deviation,
        "has_baseline": has_price_baseline or has_quantity_baseline,
        "has_deviation": has_deviation,
        "note": " | ".join(note_parts) if note_parts else "尚未建立计划基线",
    }


def reconcile_submission_records_with_holdings(
    records: list[dict[str, Any]],
    previous_holdings: list[HoldingRecord],
    current_holdings: list[HoldingRecord],
) -> tuple[list[dict[str, Any]], list[str]]:
    previous_map = {item.symbol: item for item in previous_holdings or []}
    current_map = {item.symbol: item for item in current_holdings or []}
    buy_fill_remaining = {
        symbol: max(int(getattr(current_map.get(symbol), "quantity", 0) or 0) - int(getattr(previous_map.get(symbol), "quantity", 0) or 0), 0)
        for symbol in set(previous_map) | set(current_map)
    }
    sell_fill_remaining = {
        symbol: max(int(getattr(previous_map.get(symbol), "quantity", 0) or 0) - int(getattr(current_map.get(symbol), "quantity", 0) or 0), 0)
        for symbol in set(previous_map) | set(current_map)
    }

    updated_records: list[dict[str, Any]] = []
    reconciliation_notes: list[str] = []
    for record in records:
        row = dict(record)
        symbol = str(row.get("symbol", "") or "")
        side = str(row.get("side", "") or "").upper()
        fill_status = str(row.get("fill_status", "") or "").upper()
        if fill_status in {"FILLED", "REJECTED", "CANCELLED"}:
            updated_records.append(row)
            continue

        try:
            target_quantity = int(float(row.get("quantity", 0) or 0))
        except (TypeError, ValueError):
            target_quantity = 0
        try:
            existing_fill_quantity = int(float(row.get("fill_quantity", 0) or 0))
        except (TypeError, ValueError):
            existing_fill_quantity = 0
        remaining_quantity = max(target_quantity - existing_fill_quantity, 0)
        if remaining_quantity <= 0:
            updated_records.append(row)
            continue

        inferred_fill = 0
        if side == "BUY":
            inferred_fill = min(int(buy_fill_remaining.get(symbol, 0) or 0), remaining_quantity)
            buy_fill_remaining[symbol] = max(int(buy_fill_remaining.get(symbol, 0) or 0) - inferred_fill, 0)
        elif side in {"SELL", "REDUCE"}:
            inferred_fill = min(int(sell_fill_remaining.get(symbol, 0) or 0), remaining_quantity)
            sell_fill_remaining[symbol] = max(int(sell_fill_remaining.get(symbol, 0) or 0) - inferred_fill, 0)

        if inferred_fill > 0:
            total_fill_quantity = existing_fill_quantity + inferred_fill
            row["fill_quantity"] = str(total_fill_quantity)
            row["fill_status"] = "FILLED" if total_fill_quantity >= target_quantity else "PARTIAL"
            note = (
                f"SDK持仓同步推断已成交 {inferred_fill}"
                if row["fill_status"] == "FILLED"
                else f"SDK持仓同步推断部分成交 {total_fill_quantity}/{target_quantity}"
            )
            base_message = str(row.get("message", "") or "").strip()
            if note not in base_message:
                row["message"] = f"{base_message} | {note}".strip(" |")
            reconciliation_notes.append(f"{symbol} {note}")
        updated_records.append(row)

    return updated_records, reconciliation_notes


def submission_record_execution_delta(record: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(record or {})

    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _safe_int(value: Any) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0

    planned_price = _safe_float(payload.get("planned_price"))
    submitted_price = _safe_float(payload.get("price"))
    fill_price = _safe_float(payload.get("fill_price"))
    actual_price = fill_price if fill_price > 0 else submitted_price
    planned_quantity = _safe_int(payload.get("planned_quantity"))
    submitted_quantity = _safe_int(payload.get("quantity"))
    fill_quantity = _safe_int(payload.get("fill_quantity"))
    actual_quantity = fill_quantity if fill_quantity > 0 else submitted_quantity

    price_deviation_bps = 0.0
    if planned_price > 0 and actual_price > 0:
        price_deviation_bps = round((actual_price - planned_price) / planned_price * 10000.0, 1)
    quantity_deviation = actual_quantity - planned_quantity if planned_quantity > 0 else 0
    has_price_baseline = planned_price > 0 and actual_price > 0
    has_quantity_baseline = planned_quantity > 0
    has_deviation = (has_price_baseline and abs(price_deviation_bps) >= 1.0) or (has_quantity_baseline and quantity_deviation != 0)

    note_parts: list[str] = []
    if has_price_baseline:
        if abs(price_deviation_bps) < 1.0:
            note_parts.append("价格与计划基本一致")
        elif price_deviation_bps > 0:
            note_parts.append(f"价格高于计划 {price_deviation_bps:.1f}bp")
        else:
            note_parts.append(f"价格低于计划 {abs(price_deviation_bps):.1f}bp")
    if has_quantity_baseline:
        if quantity_deviation == 0:
            note_parts.append("数量与计划一致")
        elif quantity_deviation > 0:
            note_parts.append(f"数量较计划增加 {quantity_deviation}")
        else:
            note_parts.append(f"数量较计划减少 {abs(quantity_deviation)}")

    return {
        "planned_price": planned_price,
        "actual_price": actual_price,
        "planned_quantity": planned_quantity,
        "actual_quantity": actual_quantity,
        "price_deviation_bps": price_deviation_bps,
        "quantity_deviation": quantity_deviation,
        "has_baseline": has_price_baseline or has_quantity_baseline,
        "has_deviation": has_deviation,
        "note": " | ".join(note_parts) if note_parts else "尚未建立计划基线",
    }


def summarize_trade_recap(
    submission_records: list[dict[str, str]],
    holdings: list[HoldingRecord],
    order_intents: list[OrderIntent],
    order_log: list[str],
) -> dict[str, Any]:
    submitted_count = sum(1 for item in submission_records if item.get("order_status") == "SUBMITTED")
    failed_count = sum(1 for item in submission_records if item.get("order_status") == "FAILED")
    pending_count = sum(1 for item in submission_records if item.get("fill_status") == "PENDING")
    rejected_count = sum(1 for item in submission_records if item.get("fill_status") == "REJECTED")
    buy_count = sum(1 for item in submission_records if item.get("side") == "BUY")
    sell_count = sum(1 for item in submission_records if item.get("side") == "SELL")
    reduce_count = sum(1 for item in submission_records if item.get("side") == "REDUCE")
    review_flags: list[str] = []

    executed_capital = 0.0
    deviation_rows: list[dict[str, Any]] = []
    for item in submission_records:
        try:
            executed_capital += float(item.get("price", "0") or 0.0) * float(item.get("quantity", "0") or 0.0)
        except ValueError:
            continue
        delta = submission_record_execution_delta(item)
        if delta["has_baseline"]:
            deviation_rows.append(
                {
                    "symbol": str(item.get("symbol", "") or ""),
                    "timestamp": str(item.get("timestamp", "") or ""),
                    **delta,
                }
            )

    holding_market_value = sum(item.market_value for item in holdings)
    latest_messages = [item for item in order_log[-3:] if item.strip()]
    focus_symbols = []
    for item in submission_records[-5:]:
        symbol = item.get("symbol", "").strip()
        if symbol and symbol not in focus_symbols:
            focus_symbols.append(symbol)
    deviation_items = [item for item in deviation_rows if bool(item.get("has_deviation"))]

    if failed_count:
        review_flags.append(f"有 {failed_count} 笔提交失败，需要核对接口权限或参数映射。")
    if rejected_count:
        review_flags.append(f"有 {rejected_count} 笔委托被拒绝，建议优先复盘价格/数量/账户状态。")
    if pending_count >= max(1, submitted_count):
        review_flags.append("大部分委托仍处于待成交状态，需跟踪是否存在流动性或限价偏离。")
    if deviation_items:
        review_flags.append(f"有 {len(deviation_items)} 笔委托与计划存在偏差，优先复核价格或数量是否被调整。")
    if order_intents and not submission_records:
        review_flags.append("已生成委托建议但尚未提交，可先复核预算分配和执行顺序。")
    if not review_flags:
        review_flags.append("当前执行链路稳定，可进入盘后复盘与策略归因。")

    latest_deviation = deviation_items[-1] if deviation_items else (deviation_rows[-1] if deviation_rows else {})
    max_price_deviation_bps = max((abs(float(item.get("price_deviation_bps", 0.0) or 0.0)) for item in deviation_rows), default=0.0)
    max_quantity_deviation = max((abs(int(item.get("quantity_deviation", 0) or 0)) for item in deviation_rows), default=0)
    deviation_symbols: list[str] = []
    for item in deviation_items:
        symbol = str(item.get("symbol", "") or "")
        if symbol and symbol not in deviation_symbols:
            deviation_symbols.append(symbol)

    return {
        "submitted_count": submitted_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
        "rejected_count": rejected_count,
        "buy_count": buy_count,
        "sell_count": sell_count,
        "reduce_count": reduce_count,
        "executed_capital": executed_capital,
        "holding_market_value": holding_market_value,
        "focus_symbols": focus_symbols,
        "latest_messages": latest_messages,
        "review_flags": review_flags,
        "deviation_count": len(deviation_items),
        "deviation_symbols": deviation_symbols,
        "max_price_deviation_bps": round(max_price_deviation_bps, 1),
        "max_quantity_deviation": max_quantity_deviation,
        "latest_deviation_note": str(latest_deviation.get("note", "") or ""),
    }


def build_order_intent_from_trade_decision(
    decision: TradeDecision,
    lot_size: int = 100,
) -> OrderIntent | None:
    if decision.action != "BUY" or decision.planned_entry <= 0:
        return None
    if not _is_trade_plan_viable(decision.planned_entry, decision.planned_stop, decision.planned_target):
        return None
    quantity = int(decision.suggested_budget / decision.planned_entry)
    quantity = (quantity // lot_size) * lot_size
    if quantity < lot_size or decision.planned_stop <= 0 or decision.planned_target <= 0:
        return None
    computed_risk_reward_ratio = float(getattr(decision, "risk_reward_ratio", 0.0) or 0.0)
    if computed_risk_reward_ratio <= 0:
        computed_risk_reward_ratio = _trade_plan_risk_reward_ratio(
            decision.planned_entry,
            decision.planned_stop,
            decision.planned_target,
        )
    return OrderIntent(
        symbol=decision.symbol,
        side="BUY",
        price=round(decision.planned_entry, 3),
        quantity=quantity,
        stop_price=round(decision.planned_stop, 3),
        target_price=round(decision.planned_target, 3),
        signal_date="计划股",
        reason=decision.rationale,
        opportunity_tier=getattr(decision, "opportunity_tier", ""),
        risk_flag=(
            "高"
            if computed_risk_reward_ratio < DEFAULT_RISK_CONTROLS.execution_low_risk_reward_ratio
            else "低"
        ),
        signal_source="trade_plan",
        risk_reward_ratio=computed_risk_reward_ratio,
    )


def summarize_execution_statuses(
    symbols: list[str],
    execution_status_by_symbol: dict[str, str],
) -> dict[str, int]:
    counts = {
        "total": len(symbols),
        "reviewing": 0,
        "submitted": 0,
        "failed": 0,
        "pending": 0,
    }
    for symbol in symbols:
        status = execution_status_by_symbol.get(symbol, "待观察")
        if status == "已送审":
            counts["reviewing"] += 1
        elif status == "已提交":
            counts["submitted"] += 1
        elif status == "提交失败":
            counts["failed"] += 1
        else:
            counts["pending"] += 1
    return counts

