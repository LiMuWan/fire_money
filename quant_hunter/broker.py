from __future__ import annotations

import csv
import importlib
import importlib.util
import json
import platform
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from .decision import TradeDecision
from .models import BrokerProfile, BrokerStatus, CashSnapshot, HoldingRecord, OrderIntent, ScanRow
from .risk import DEFAULT_RISK_CONTROLS, normalize_risk_profile, resolve_risk_controls

_MIN_ORDER_RISK_REWARD_RATIO = DEFAULT_RISK_CONTROLS.plan_min_risk_reward_ratio
_WARN_TOTAL_LOSS_RATIO = DEFAULT_RISK_CONTROLS.warn_total_loss_ratio
_BLOCK_TOTAL_LOSS_RATIO = DEFAULT_RISK_CONTROLS.block_total_loss_ratio
_WARN_SINGLE_LOSS_RATIO = DEFAULT_RISK_CONTROLS.warn_single_loss_ratio
_BLOCK_SINGLE_LOSS_RATIO = DEFAULT_RISK_CONTROLS.block_single_loss_ratio
_WARN_SINGLE_POSITION_ASSET_RATIO = DEFAULT_RISK_CONTROLS.warn_single_position_asset_ratio
_BLOCK_SINGLE_POSITION_ASSET_RATIO = DEFAULT_RISK_CONTROLS.block_single_position_asset_ratio
_WARN_SINGLE_POSITION_CASH_RATIO = DEFAULT_RISK_CONTROLS.warn_single_position_cash_ratio
_BLOCK_SINGLE_POSITION_CASH_RATIO = DEFAULT_RISK_CONTROLS.block_single_position_cash_ratio


def _is_trade_plan_viable(price: float, stop_price: float, target_price: float, min_ratio: float = _MIN_ORDER_RISK_REWARD_RATIO) -> bool:
    if price <= 0 or stop_price <= 0 or target_price <= 0:
        return False
    estimated_loss = price - stop_price
    estimated_profit = target_price - price
    if estimated_loss <= 0 or estimated_profit <= 0:
        return False
    return (estimated_profit / estimated_loss) >= min_ratio


def _display_mainline_role(value: str) -> str:
    return {
        "CORE": "核心龙头",
        "FRONT": "前排核心",
        "ASSIST": "助攻前排",
        "FOLLOW": "跟风观察",
        "NOISE": "杂毛噪声",
        "ELIMINATED": "淘汰风险",
    }.get(value or "", value or "--")


def _apply_portfolio_risk_status_codes(
    rows: list[dict[str, Any]],
    *,
    warn_single_loss_ratio: float,
    block_single_loss_ratio: float,
    warn_single_position_asset_ratio: float,
    block_single_position_asset_ratio: float,
    warn_single_position_cash_ratio: float,
    block_single_position_cash_ratio: float,
) -> None:
    _apply_portfolio_risk_status_codes(
        rows,
        warn_single_loss_ratio=warn_single_loss_ratio,
        block_single_loss_ratio=block_single_loss_ratio,
        warn_single_position_asset_ratio=warn_single_position_asset_ratio,
        block_single_position_asset_ratio=block_single_position_asset_ratio,
        warn_single_position_cash_ratio=warn_single_position_cash_ratio,
        block_single_position_cash_ratio=block_single_position_cash_ratio,
    )


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
                    "detail": "未命中当前推荐池，需人工复核后再决定是否执行。",
                }
            )
            if intent.side == "BUY":
                warnings.append(f"主线审查 / 主线闸门：{intent.symbol} 未命中当前推荐池，建议人工复核。")
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
                blockers.append(f"主线审查 / 主线闸门：{getattr(recommendation, 'stock_name', intent.symbol)} 已处于{role_label}，不建议新开仓。")
            elif rank > 3:
                status = "拦截"
                blockers.append(f"主线审查 / 主线闸门：{getattr(recommendation, 'stock_name', intent.symbol)} 已跌出主线前 3，暂不建议新开仓。")
            elif risk_flag == "高" or failure_risk >= 72.0:
                status = "拦截"
                blockers.append(f"主线审查 / 主线闸门：{getattr(recommendation, 'stock_name', intent.symbol)} 主线风险偏高，建议暂缓执行。")
            elif window_score < 50.0:
                status = "拦截"
                blockers.append(f"主线审查 / 主线闸门：{getattr(recommendation, 'stock_name', intent.symbol)} 主线窗口不足，等待更清晰买点。")
            elif role == "FOLLOW" or window_score < 66.0 or risk_flag == "中":
                status = "谨慎"
                warnings.append(f"主线审查 / 主线闸门：{getattr(recommendation, 'stock_name', intent.symbol)} 更适合缩量试错或等待确认。")
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


class EastmoneyBrokerAdapter:
    """Bridge between the desktop app and Eastmoney/MyQuant SDK workflows."""

    def diagnose_environment(self, profile: BrokerProfile) -> dict[str, Any]:
        bridge_python = self.resolve_bridge_python(profile)
        bridge_module_installed = self._module_available_in_interpreter(bridge_python, profile.sdk_module) if bridge_python else False
        module_installed = self._has_module(profile.sdk_module)
        runtime_supported = self._is_runtime_supported(profile.sdk_module, sys.version_info[:2])
        direct_ready = module_installed and runtime_supported and bool(profile.token) and bool(profile.account_id)
        bridge_ready = bool(bridge_python and bridge_module_installed and profile.token and profile.account_id)
        return {
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
        candidate = Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "python.exe"
        if candidate.exists():
            return str(candidate)
        try:
            result = subprocess.run(
                ["py", "-3.12", "-c", "import sys; print(sys.executable)"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip()
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



    def export_order_plan(self, intents: list[OrderIntent], export_dir: str | Path) -> Path:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        output = root / f"eastmoney_order_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
                    "symbol",
                    "side",
                    "price",
                    "quantity",
                    "stop_price",
                    "target_price",
                    "signal_date",
                    "reason",
                ]
            )
            for item in intents:
                writer.writerow(
                    [
                        item.symbol,
                        item.side,
                        item.price,
                        item.quantity,
                        item.stop_price,
                        item.target_price,
                        item.signal_date,
                        item.reason,
                    ]
                )
        return output

    def export_submission_records(self, records: list[dict[str, Any]], export_dir: str | Path) -> Path:
        root = Path(export_dir)
        root.mkdir(parents=True, exist_ok=True)
        output = root / f"eastmoney_submission_records_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with output.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(
                [
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
            )
            for item in records:
                writer.writerow(
                    [
                        item.get("timestamp", ""),
                        item.get("order_status", item.get("status", "")),
                        item.get("fill_status", ""),
                        item.get("symbol", ""),
                        item.get("side", ""),
                        item.get("price", ""),
                        item.get("quantity", ""),
                        item.get("failure_reason", ""),
                        item.get("message", ""),
                    ]
                )
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
            return [f"{item['symbol']}: {item['result']}" for item in payload["results"]]

        gm = self._prepare_sdk_direct(profile)
        order_func = getattr(gm, "order_volume", None)
        if not callable(order_func):
            raise RuntimeError("当前 SDK 中没有找到 order_volume 函数。")
        limit_type = self._resolve_attr(gm, ["OrderType_Limit", "ORDER_TYPE_LIMIT"])
        results: list[str] = []
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
        result = subprocess.run(
            [python_executable, str(SDK_BRIDGE), "diagnose"],
            cwd=PROJECT_ROOT,
            input=json.dumps({"sdk_module": module_name}),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return False
        try:
            return bool(json.loads(result.stdout).get("module_installed"))
        except Exception:
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
    for item in submission_records:
        try:
            executed_capital += float(item.get("price", "0") or 0.0) * float(item.get("quantity", "0") or 0.0)
        except ValueError:
            continue

    holding_market_value = sum(item.market_value for item in holdings)
    latest_messages = [item for item in order_log[-3:] if item.strip()]
    focus_symbols = []
    for item in submission_records[-5:]:
        symbol = item.get("symbol", "").strip()
        if symbol and symbol not in focus_symbols:
            focus_symbols.append(symbol)

    if failed_count:
        review_flags.append(f"有 {failed_count} 笔提交失败，需要核对接口权限或参数映射。")
    if rejected_count:
        review_flags.append(f"有 {rejected_count} 笔委托被拒绝，建议优先复盘价格/数量/账户状态。")
    if pending_count >= max(1, submitted_count):
        review_flags.append("大部分委托仍处于待成交状态，需跟踪是否存在流动性或限价偏离。")
    if order_intents and not submission_records:
        review_flags.append("已生成委托建议但尚未提交，可先复核预算分配和执行顺序。")
    if not review_flags:
        review_flags.append("当前执行链路稳定，可进入盘后复盘与策略归因。")

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
            if float(getattr(decision, "risk_reward_ratio", 0.0) or 0.0) < DEFAULT_RISK_CONTROLS.execution_low_risk_reward_ratio
            else "低"
        ),
        signal_source="trade_plan",
        risk_reward_ratio=float(getattr(decision, "risk_reward_ratio", 0.0) or 0.0),
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

