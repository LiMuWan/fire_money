from __future__ import annotations

import importlib
import json
import sys
from typing import Any


def _pick_value(row: Any, candidates: list[str], fallback: Any = None) -> Any:
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


def _call_first_available(gm: Any, names: list[str], **kwargs):
    for name in names:
        func = getattr(gm, name, None)
        if not callable(func):
            continue
        try:
            return func(**kwargs)
        except TypeError:
            return func()
    raise RuntimeError(f"SDK 中不存在这些函数: {', '.join(names)}")


def _call_optional_available(gm: Any, names: list[str], **kwargs):
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


def _resolve_attr(obj: Any, names: list[str]):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _normalize_submit_result(symbol: str, result: Any) -> dict[str, Any]:
    result_text = str(
        _pick_value(
            result,
            ["result", "message", "msg", "status_msg", "remark"],
            fallback=str(result or "submitted"),
        )
        or "submitted"
    )
    fill_price = _pick_value(result, ["fill_price", "filled_price", "avg_fill_price", "filled_avg_price", "trade_price", "deal_price"], fallback=0.0)
    fill_quantity = _pick_value(result, ["fill_quantity", "filled_quantity", "filled_volume", "trade_volume", "deal_volume", "filled_qty"], fallback=0)
    return {
        "symbol": symbol,
        "result": result_text,
        "order_status": str(_pick_value(result, ["order_status", "status"], fallback="SUBMITTED") or "SUBMITTED"),
        "fill_status": str(_pick_value(result, ["fill_status", "filled_status", "exec_status", "deal_status"], fallback="") or ""),
        "fill_price": float(fill_price or 0.0) if fill_price not in {None, ""} else 0.0,
        "fill_quantity": int(float(fill_quantity or 0)) if fill_quantity not in {None, ""} else 0,
        "order_id": str(_pick_value(result, ["order_id", "cl_ord_id", "entrust_no", "order_no"], fallback="") or ""),
    }


def _sync(gm: Any, payload: dict[str, Any]) -> dict[str, Any]:
    cash_rows = _call_first_available(gm, ["get_cash"], account_id=payload["account_id"])
    cash_row = cash_rows[0] if isinstance(cash_rows, list) and cash_rows else cash_rows
    available_cash = _pick_value(cash_row, ["available", "available_cash", "cash", "nav"], fallback=0.0)
    total_assets = _pick_value(cash_row, ["nav", "total_assets", "asset", "market_value"], fallback=available_cash)

    positions = _call_first_available(gm, ["get_position", "get_positions"], account_id=payload["account_id"])
    if positions is None:
        positions = []
    holdings = []
    for item in positions:
        symbol = _pick_value(item, ["symbol", "sec_id", "security", "instrument"])
        if not symbol:
            continue
        quantity = int(float(_pick_value(item, ["volume", "quantity", "amount"], fallback=0)))
        available = int(float(_pick_value(item, ["available", "available_volume"], fallback=quantity)))
        cost_price = float(_pick_value(item, ["vwap", "cost", "cost_price"], fallback=0.0))
        market_value = float(_pick_value(item, ["market_value", "value"], fallback=cost_price * quantity))
        holdings.append(
            {
                "symbol": str(symbol),
                "quantity": quantity,
                "available": available,
                "cost_price": cost_price,
                "market_value": market_value,
            }
        )
    return {
        "cash": {
            "available_cash": float(available_cash or 0.0),
            "total_assets": float(total_assets or 0.0),
        },
        "holdings": holdings,
    }


def _submit(gm: Any, payload: dict[str, Any]) -> dict[str, Any]:
    order_func = getattr(gm, "order_volume", None)
    if not callable(order_func):
        raise RuntimeError("当前 SDK 中没有找到 order_volume 函数。")
    buy_side = _resolve_attr(gm, ["OrderSide_Buy", "ORDER_SIDE_BUY"])
    sell_side = _resolve_attr(gm, ["OrderSide_Sell", "ORDER_SIDE_SELL"])
    limit_type = _resolve_attr(gm, ["OrderType_Limit", "ORDER_TYPE_LIMIT"])
    open_effect = _resolve_attr(gm, ["PositionEffect_Open", "POSITION_EFFECT_OPEN"])

    results = []
    for item in payload["intents"]:
        kwargs = {
            "symbol": item["symbol"],
            "volume": int(item["quantity"]),
            "side": buy_side if item["side"] == "BUY" else sell_side,
            "order_type": limit_type,
            "price": float(item["price"]),
            "account": payload["account_id"],
        }
        if open_effect is not None:
            kwargs["position_effect"] = open_effect
        try:
            result = order_func(**kwargs)
        except TypeError:
            kwargs.pop("position_effect", None)
            result = order_func(**kwargs)
        results.append(_normalize_submit_result(item["symbol"], result))
    return {"results": results}


def _execution(gm: Any, payload: dict[str, Any]) -> dict[str, Any]:
    orders = _call_optional_available(gm, ["get_orders", "get_unfinished_orders", "get_order"], account_id=payload["account_id"])
    trades = _call_optional_available(gm, ["get_execution_reports", "get_trades", "get_deals", "get_trade"], account_id=payload["account_id"])
    rows: list[dict[str, Any]] = []
    for source in (orders or [], trades or []):
        if source is None:
            continue
        bucket = source if isinstance(source, list) else [source]
        for item in bucket:
            symbol = str(_pick_value(item, ["symbol", "sec_id", "security", "instrument"], fallback="") or "")
            rows.append(
                _normalize_submit_result(symbol, item)
                | {
                    "side": str(_pick_value(item, ["side", "order_side", "direction"], fallback="") or ""),
                    "timestamp": str(_pick_value(item, ["timestamp", "create_time", "created_at", "trade_time", "update_time", "updated_at", "order_time", "entrust_time"], fallback="") or ""),
                    "price": float(_pick_value(item, ["price", "order_price", "limit_price", "entrust_price"], fallback=0.0) or 0.0),
                    "quantity": int(float(_pick_value(item, ["quantity", "volume", "order_qty", "entrust_amount", "entrust_qty"], fallback=0) or 0)),
                }
            )
    limit = max(int(payload.get("limit", 40) or 40), 1)
    return {"execution_records": rows[:limit]}


def main() -> int:
    if len(sys.argv) < 2:
        raise SystemExit("missing action")
    action = sys.argv[1]
    payload = json.loads(sys.stdin.read())
    module_name = payload.get("sdk_module", "gm.api")
    if action == "diagnose":
        import importlib.util

        spec = importlib.util.find_spec(module_name)
        print(json.dumps({"module_installed": spec is not None}))
        return 0
    gm = importlib.import_module(module_name)
    set_token = getattr(gm, "set_token", None)
    if callable(set_token):
        set_token(payload["token"])
    if action == "sync":
        print(json.dumps(_sync(gm, payload), ensure_ascii=False))
        return 0
    if action == "submit":
        print(json.dumps(_submit(gm, payload), ensure_ascii=False))
        return 0
    if action == "execution":
        print(json.dumps(_execution(gm, payload), ensure_ascii=False))
        return 0
    raise SystemExit(f"unknown action: {action}")


if __name__ == "__main__":
    main()
