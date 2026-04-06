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

from .models import BrokerProfile, BrokerStatus, CashSnapshot, HoldingRecord, OrderIntent, ScanRow


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
            quantity = int(per_trade_budget / row.entry_price)
            quantity = (quantity // lot_size) * lot_size
            if quantity < lot_size or row.stop_price is None or row.target_price is None:
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
        buy_side = self._resolve_attr(gm, ["OrderSide_Buy", "ORDER_SIDE_BUY"])
        sell_side = self._resolve_attr(gm, ["OrderSide_Sell", "ORDER_SIDE_SELL"])
        limit_type = self._resolve_attr(gm, ["OrderType_Limit", "ORDER_TYPE_LIMIT"])
        open_effect = self._resolve_attr(gm, ["PositionEffect_Open", "POSITION_EFFECT_OPEN"])
        results: list[str] = []
        for item in intents:
            kwargs = {
                "symbol": item.symbol,
                "volume": int(item.quantity),
                "side": buy_side if item.side == "BUY" else sell_side,
                "order_type": limit_type,
                "price": float(item.price),
                "account": profile.account_id,
            }
            if open_effect is not None:
                kwargs["position_effect"] = open_effect
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
            "def init(context):",
            "    for item in ORDERS:",
            "        order_volume(",
            "            symbol=item['symbol'],",
            "            volume=int(item['quantity']),",
            "            side=OrderSide_Buy if item['side'] == 'BUY' else OrderSide_Sell,",
            "            order_type=OrderType_Limit,",
            "            position_effect=PositionEffect_Open,",
            "            price=float(item['price']),",
            f"            account='{profile.account_id}',",
            "        )",
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
