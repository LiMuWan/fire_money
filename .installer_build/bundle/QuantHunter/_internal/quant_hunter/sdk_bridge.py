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


def _resolve_attr(obj: Any, names: list[str]):
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


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
        results.append({"symbol": item["symbol"], "result": str(result)})
    return {"results": results}


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
    raise SystemExit(f"unknown action: {action}")


if __name__ == "__main__":
    main()
