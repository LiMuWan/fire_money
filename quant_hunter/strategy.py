from __future__ import annotations

from dataclasses import dataclass
from statistics import fmean

from .models import DailyAnalysis, PriceBar, TrapState


def _mean(values: list[float]) -> float:
    return fmean(values) if values else 0.0


def _true_range(current: PriceBar, previous_close: float) -> float:
    return max(
        current.high - current.low,
        abs(current.high - previous_close),
        abs(current.low - previous_close),
    )


@dataclass(frozen=True)
class StrategyParams:
    breakout_lookback: int = 20
    atr_window: int = 14
    volume_window: int = 5
    fast_ma_window: int = 5
    slow_ma_window: int = 20
    reclaim_window: int = 3
    min_breakout_pct: float = 0.01
    min_volume_ratio: float = 1.8
    min_upper_shadow_pct: float = 0.35
    max_close_location: float = 0.35
    max_reclaim_volume_ratio: float = 0.85
    stop_atr_multiple: float = 1.2
    target_atr_multiple: float = 2.4

    @classmethod
    def from_mapping(cls, values: dict[str, str]) -> "StrategyParams":
        return cls(
            breakout_lookback=int(values["breakout_lookback"]),
            atr_window=int(values["atr_window"]),
            volume_window=int(values["volume_window"]),
            fast_ma_window=int(values["fast_ma_window"]),
            slow_ma_window=int(values["slow_ma_window"]),
            reclaim_window=int(values["reclaim_window"]),
            min_breakout_pct=float(values["min_breakout_pct"]),
            min_volume_ratio=float(values["min_volume_ratio"]),
            min_upper_shadow_pct=float(values["min_upper_shadow_pct"]),
            max_close_location=float(values["max_close_location"]),
            max_reclaim_volume_ratio=float(values["max_reclaim_volume_ratio"]),
            stop_atr_multiple=float(values["stop_atr_multiple"]),
            target_atr_multiple=float(values["target_atr_multiple"]),
        )


class AntiHarvestStrategy:
    def __init__(self, params: StrategyParams | None = None) -> None:
        self.params = params or StrategyParams()

    def analyze(self, bars: list[PriceBar]) -> list[DailyAnalysis]:
        if len(bars) < max(self.params.breakout_lookback, self.params.slow_ma_window) + 2:
            raise ValueError("数据不足，至少需要 25 根以上 K 线。")

        analyses: list[DailyAnalysis] = []
        true_ranges: list[float] = []
        active_trap: TrapState | None = None

        for index, bar in enumerate(bars):
            previous_close = bars[index - 1].close if index else bar.close
            tr = _true_range(bar, previous_close)
            true_ranges.append(tr)

            lookback_start = max(0, index - self.params.breakout_lookback)
            volume_start = max(0, index - self.params.volume_window)
            fast_start = max(0, index + 1 - self.params.fast_ma_window)
            slow_start = max(0, index + 1 - self.params.slow_ma_window)
            atr_start = max(0, index + 1 - self.params.atr_window)

            prev_highs = [item.high for item in bars[lookback_start:index]]
            breakout_level = max(prev_highs) if prev_highs else bar.high
            avg_volume = _mean([item.volume for item in bars[volume_start:index]])
            ma_fast = _mean([item.close for item in bars[fast_start : index + 1]])
            ma_slow = _mean([item.close for item in bars[slow_start : index + 1]])
            atr = _mean(true_ranges[atr_start : index + 1])

            bar_range = max(bar.high - bar.low, 0.01)
            upper_shadow_pct = (bar.high - max(bar.open, bar.close)) / bar_range
            close_location = (bar.close - bar.low) / bar_range
            volume_ratio = bar.volume / avg_volume if avg_volume else 1.0

            label = "NONE"
            score = 0
            reason = "无有效信号。"
            entry_price = None
            stop_price = None
            target_price = None

            if active_trap and index > active_trap.expire_index:
                active_trap = None

            trap_detected = (
                index >= self.params.breakout_lookback
                and bar.high >= breakout_level * (1 + self.params.min_breakout_pct)
                and bar.close <= breakout_level * 1.003
                and upper_shadow_pct >= self.params.min_upper_shadow_pct
                and close_location <= self.params.max_close_location
                and volume_ratio >= self.params.min_volume_ratio
            )

            if trap_detected:
                active_trap = TrapState(
                    index=index,
                    date=bar.date,
                    symbol=bar.symbol,
                    breakout_level=breakout_level,
                    trap_high=bar.high,
                    trap_low=bar.low,
                    trap_close=bar.close,
                    trap_midpoint=(bar.high + bar.low) / 2,
                    atr_at_trap=atr,
                    trap_volume=bar.volume,
                    expire_index=index + self.params.reclaim_window,
                )
                label = "TRAP_DETECTED"
                score = 72
                reason = (
                    "识别到放量假突破: 创出阶段新高后回落到突破位附近，"
                    "同时上影较长、收盘贴近低位。"
                )
            elif active_trap and index > active_trap.index:
                reclaim_trigger = max(
                    active_trap.breakout_level,
                    active_trap.trap_midpoint,
                    active_trap.trap_close,
                )
                reclaim_confirmed = (
                    bar.close >= reclaim_trigger
                    and bar.volume <= active_trap.trap_volume * self.params.max_reclaim_volume_ratio
                    and bar.close >= ma_slow
                    and bar.low > active_trap.trap_low
                )
                if reclaim_confirmed:
                    entry_price = bar.close
                    stop_price = min(
                        active_trap.trap_low,
                        bar.close - active_trap.atr_at_trap * self.params.stop_atr_multiple,
                    )
                    target_price = bar.close + active_trap.atr_at_trap * self.params.target_atr_multiple
                    label = "RECLAIM_LONG"
                    score = 88
                    reason = (
                        "假突破后的价格修复成立: 收盘重新站回陷阱中轴或突破位，"
                        "且量能较陷阱日降温。"
                    )
                    active_trap = None
                else:
                    label = "WATCH"
                    score = 45
                    reason = (
                        "仍在观察修复是否成立，当前更适合等待二次确认，避免追逐"
                        "量化和游资制造的第一脚冲动。"
                    )

            analyses.append(
                DailyAnalysis(
                    date=bar.date,
                    symbol=bar.symbol,
                    close=bar.close,
                    atr=atr,
                    ma_fast=ma_fast,
                    ma_slow=ma_slow,
                    breakout_level=breakout_level,
                    volume_ratio=volume_ratio,
                    upper_shadow_pct=upper_shadow_pct,
                    close_location=close_location,
                    label=label,
                    score=score,
                    reason=reason,
                    entry_price=entry_price,
                    stop_price=stop_price,
                    target_price=target_price,
                )
            )
        return analyses
