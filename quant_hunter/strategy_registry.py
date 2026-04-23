from __future__ import annotations

import ast
from dataclasses import dataclass, field
from functools import lru_cache
import importlib.util
import json
from pathlib import Path
from pprint import pformat
from typing import Any, Callable, Mapping


_DEFAULT_CATALOG_PAYLOAD: dict[str, object] = {
    "strategies": [
        {
            "name": "龙头模型",
            "score_field": "leader_model_score",
            "description": "抓主线核心龙头与趋势延续",
            "aliases": ["龙头主线"],
            "formula_stage": "base",
            "formula_weights": {
                "technical": 0.32,
                "persistence": 0.22,
                "leader": 0.26,
                "position": 0.12,
                "news": 0.08,
            },
            "plan_defaults": {
                "stop_pct": 0.05,
                "target_pct": 0.08,
                "budget_multiplier_strong": 1.0,
                "budget_multiplier_normal": 1.0,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "主力雷达",
            "score_field": "main_force_score",
            "description": "抓资金净流入和机构强承接",
            "aliases": ["资金承接"],
            "formula_stage": "base",
            "formula_weights": {
                "technical": 0.18,
                "position": 0.18,
                "persistence": 0.14,
                "news": 0.20,
                "leader": 0.12,
                "main_force_bias": 1.0,
            },
            "plan_defaults": {
                "stop_pct": 0.05,
                "target_pct": 0.08,
                "budget_multiplier_strong": 1.0,
                "budget_multiplier_normal": 1.0,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "擒龙打板",
            "score_field": "board_attack_score",
            "description": "抓强势确认、回封确认和打板节奏",
            "aliases": ["打板策略", "强势接力"],
            "formula_stage": "base",
            "formula_weights": {
                "technical": 0.27,
                "persistence": 0.24,
                "leader": 0.14,
                "board_window": 0.15,
                "news": 0.12,
                "board_bias": 1.0,
            },
            "plan_defaults": {
                "stop_pct": 0.035,
                "target_pct": 0.13,
                "budget_multiplier_strong": 1.0,
                "budget_multiplier_normal": 1.0,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "价值低吸",
            "score_field": "value_recovery_score",
            "description": "抓分歧回踩、低位承接和修复",
            "aliases": ["趋势低吸", "龙头低吸"],
            "formula_stage": "base",
            "formula_weights": {
                "position": 0.34,
                "technical": 0.20,
                "persistence": 0.16,
                "news": 0.12,
                "value_window": 0.08,
                "leader": 0.10,
                "value_bias": 1.0,
            },
            "plan_defaults": {
                "stop_pct": 0.055,
                "target_pct": 0.09,
                "budget_multiplier_strong": 0.92,
                "budget_multiplier_normal": 0.92,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "尾盘买入法",
            "score_field": "tail_buy_score",
            "description": "抓尾盘回流确认、次日开盘兑现和短隔夜纪律",
            "aliases": ["尾盘买入", "尾盘抢筹"],
            "formula_stage": "base",
            "formula_weights": {
                "technical": 0.18,
                "position": 0.12,
                "persistence": 0.16,
                "news": 0.12,
                "leader": 0.05,
                "main_force": 0.14,
                "board_attack": 0.05,
                "one_day_hold": 0.18,
                "tail_buy_window": 0.10,
                "tail_buy_bias": 1.0,
            },
            "plan_defaults": {
                "stop_pct": 0.024,
                "target_pct": 0.032,
                "budget_multiplier_strong": 0.82,
                "budget_multiplier_normal": 0.72,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "一日持股法",
            "score_field": "one_day_hold_score",
            "description": "抓次日溢价、隔日兑现和短线节奏",
            "aliases": ["一日持股", "隔日强势"],
            "formula_stage": "base",
            "formula_weights": {
                "technical": 0.22,
                "position": 0.18,
                "persistence": 0.14,
                "news": 0.16,
                "leader": 0.08,
                "board_attack": 0.12,
                "main_force": 0.08,
                "next_day_window": 0.10,
                "one_day_bias": 1.0,
            },
            "plan_defaults": {
                "stop_pct": 0.028,
                "target_pct": 0.055,
                "budget_multiplier_strong": 0.96,
                "budget_multiplier_normal": 0.86,
                "budget_sentiment_threshold": 72.0,
            },
        },
        {
            "name": "掘龙决策",
            "score_field": "dragon_decision_score",
            "description": "汇总前五大战法，给最终动作",
            "aliases": ["综合决策", "掘龙"],
            "formula_stage": "aggregate",
            "formula_weights": {
                "leader_model": 0.22,
                "main_force": 0.16,
                "board_attack": 0.14,
                "value_recovery": 0.15,
                "tail_buy": 0.08,
                "one_day_hold": 0.09,
                "technical": 0.07,
                "position": 0.04,
                "persistence": 0.03,
                "news": 0.02,
            },
            "plan_defaults": {
                "stop_pct": 0.05,
                "target_pct": 0.08,
                "budget_multiplier_strong": 1.0,
                "budget_multiplier_normal": 1.0,
                "budget_sentiment_threshold": 72.0,
            },
        },
    ]
}

_LEGACY_ALIAS_MAP = {
    "强势接力": "擒龙打板",
    "打板策略": "擒龙打板",
    "尾盘买入": "尾盘买入法",
    "一日持股": "一日持股法",
    "综合决策": "掘龙决策",
    "掘龙": "掘龙决策",
    "主力决策": "主力雷达",
    "龙头低吸": "价值低吸",
}

_STRATEGY_UI_METADATA: dict[str, dict[str, object]] = {
    "龙头模型": {
        "short_label": "龙头",
        "scene_copy": "适合主线最强、龙头属性明确、趋势仍在延续的票。",
        "product_positioning": "主线最强确认，适合做前排龙头识别和强者恒强。",
        "capital_style": "主线进攻 / 趋势跟随",
        "badge_palette": ("#5b1216", "#ff6a6f"),
        "empty_hint": "等待龙头池生成后更新前排标的和位置判断。",
        "default_risk_level": "中高风险",
        "low_flag_risk_level": "中风险",
        "position_hint": "先试仓确认，再沿主线延续分批加。",
        "buy_position": "首笔 2 成试仓；龙头位次和主线延续确认后，可加到 4-5 成，单票不超过 5 成。",
        "sell_position": "冲高先分批止盈；失速先减 1/3，主线掉队或跌破防守位降到 0-1 成。",
        "execution_discipline": "只做主线前排；位次后移不加仓，跌破防守位必须先减仓，不能用龙头名义硬扛后排。",
        "no_go": "主线掉队、位次后排、龙头属性不清时不做。",
        "applicable_market": "适合主线最强仍在加速、龙头位次明确、板块仍有持续性的行情。",
        "capacity_limit": "更适合核心仓位逐步放大，但前提是龙头和主线都没有掉队。",
        "standard_action_buy_fallback": "先确认龙头位次和主线延续，再试仓。",
        "standard_action_sell_fallback": "主线掉队或龙头失速时分批处理。",
        "failure_sample": "最容易失败在主线切换后还把后排当龙头，或位次下降后仍试图硬抗。",
    },
    "主力雷达": {
        "short_label": "主力",
        "scene_copy": "适合资金承接清晰、量价匹配、机构或主力动作明显的票。",
        "product_positioning": "资金承接跟随，适合做主力痕迹和资金流确认。",
        "capital_style": "资金跟随 / 中速切入",
        "badge_palette": ("#0f3951", "#7ed7ff"),
        "empty_hint": "等待资金画像生成后更新主力流入和承接质量。",
        "default_risk_level": "中风险",
        "low_flag_risk_level": "中风险",
        "position_hint": "先小仓验证承接，放量确认后再加。",
        "buy_position": "首笔 2 成跟随；资金持续净流入、承接不破时加到 3-4 成。",
        "sell_position": "承接转弱先减半；放量滞涨、净流出或跌破防守位时退出机动仓。",
        "execution_discipline": "必须先看承接再看价格；资金转弱不补仓，放量滞涨当作风险信号处理。",
        "no_go": "资金承接转弱、放量滞涨、催化失真时不做。",
        "applicable_market": "适合资金承接持续增强、量价匹配清晰、机构痕迹明显的行情。",
        "capacity_limit": "更适合中等容量跟随，不适合在承接未确认前瞬间打满。",
        "standard_action_buy_fallback": "先确认承接和量能，再做跟随。",
        "standard_action_sell_fallback": "承接转弱或量价失配时及时收缩。",
        "failure_sample": "最容易失败在资金假承接、放量滞涨、催化兑现后还继续追随。",
    },
    "擒龙打板": {
        "short_label": "打板",
        "scene_copy": "适合强势确认、回封确认、需要盯节奏和情绪的高弹性机会。",
        "product_positioning": "高弹性打板，适合做强势确认后的进攻型博弈。",
        "capital_style": "快进快出 / 高弹性博弈",
        "badge_palette": ("#57430f", "#ffd75b"),
        "empty_hint": "等待强势候选生成后更新打板窗口和回封观察。",
        "default_risk_level": "高风险",
        "low_flag_risk_level": "高风险",
        "position_hint": "只做小样本试错，封板质量确认后再考虑加码。",
        "buy_position": "首笔 1 成试错；封板和回封质量确认后最多 2-3 成，不满仓打板。",
        "sell_position": "炸板、回封失败或次日弱转弱先卖 1/2 到全出；高开不连强分批兑现。",
        "execution_discipline": "宁可错过不能乱打；炸板不幻想，回封失败必须撤，情绪退潮时停止试错。",
        "no_go": "情绪退潮、炸板承接差、非主线硬板时不做。",
        "applicable_market": "适合情绪回暖、回封质量高、前排封板溢价仍在的进攻型行情。",
        "capacity_limit": "只适合小样本快节奏试错，不适合重仓持续摊大单票风险。",
        "standard_action_buy_fallback": "先等强势确认和回封质量，再小仓试错。",
        "standard_action_sell_fallback": "炸板或次日弱转强失败时快速处理。",
        "failure_sample": "最容易失败在情绪退潮、炸板承接差、非主线硬板时继续进攻。",
    },
    "价值低吸": {
        "short_label": "低吸",
        "scene_copy": "适合回踩修复、低位承接、强调安全边际和修复预期的票。",
        "product_positioning": "修复型低吸，适合做回踩承接和安全边际。",
        "capital_style": "分批低吸 / 修复博弈",
        "badge_palette": ("#204728", "#7ef5a2"),
        "empty_hint": "等待回踩修复候选生成后更新低吸窗口。",
        "default_risk_level": "中风险",
        "low_flag_risk_level": "中低风险",
        "position_hint": "优先分批吸，不要一次性打满。",
        "buy_position": "按 1.5 成、1.5 成、1 成分批低吸，总仓 3-4 成；无承接不补第三笔。",
        "sell_position": "修复到压力位先卖 1/3-1/2；跌破防守位停止补仓并退出。",
        "execution_discipline": "只低吸有承接的回踩；越跌越补禁止，第三笔必须等企稳确认。",
        "no_go": "修复逻辑不成立、承接不足、跌破防守位时不做。",
        "applicable_market": "适合主线分歧后的回踩修复、承接重新回流、追高性价比偏低的行情。",
        "capacity_limit": "更适合中等容量分批布局，不适合在无承接时一次性打满。",
        "standard_action_buy_fallback": "先等回踩企稳，再分批低吸。",
        "standard_action_sell_fallback": "修复到计划目标位后分批兑现。",
        "failure_sample": "最容易失败在修复预期落空、承接不足",
    },
    "尾盘买入法": {
        "short_label": "尾盘",
        "scene_copy": "适合尾盘回流确认后隔夜，重点看 14:30 后承接和次日开盘兑现。",
        "product_positioning": "尾盘隔夜，适合做尾盘回流后的短周期博弈。",
        "capital_style": "尾盘试仓 / 隔夜兑现",
        "badge_palette": ("#4b3418", "#ffcf82"),
        "empty_hint": "等待尾盘回流候选生成后更新隔夜确认和次日开盘兑现节奏。",
        "default_risk_level": "高风险",
        "low_flag_risk_level": "高风险",
        "position_hint": "只做尾盘试仓，隔夜后以兑现优先。",
        "buy_position": "14:30 后确认回流再买 1-2 成，强信号也不超过 3 成；不提前埋伏。",
        "sell_position": "次日冲高先卖 1/2；竞价或开盘不及预期直接清掉隔夜仓。",
        "execution_discipline": "14:30 前不提前埋伏；隔夜只赚确定性溢价，次日不及预期必须先撤。",
        "no_go": "14:30 前无回流、尾盘抢拉无承接、隔夜消息走弱时不做。",
        "applicable_market": "适合尾盘回流确认、隔夜博弈仍有溢价、次日兑现窗口较明确的行情。",
        "capacity_limit": "更适合小到中等容量尾盘试仓，不适合全天追高后被动隔夜。",
        "standard_action_buy_fallback": "先看 14:30 后回流和承接，再尾盘试仓。",
        "standard_action_sell_fallback": "次日冲高优先兑现，不恋战。",
        "failure_sample": "最容易失败在尾盘抢拉无承接、隔夜消息走弱、次日竞价不及预期却没有先撤。",
    },
    "一日持股法": {
        "short_label": "一日",
        "scene_copy": "适合隔日博弈，重点看竞价转强、开盘承接和次日兑现。",
        "product_positioning": "隔日节奏，适合做竞价转强到次日兑现。",
        "capital_style": "隔日试错 / 次日兑现",
        "badge_palette": ("#3b2f12", "#ffd27a"),
        "empty_hint": "等待短线爆发候选生成后更新隔日博弈与兑现节奏。",
        "default_risk_level": "高风险",
        "low_flag_risk_level": "高风险",
        "position_hint": "先轻仓博弈，次日不及预期就快速退出。",
        "buy_position": "当日只做 1-2 成轻仓博弈，强势确认最多 3 成；不把隔日票做成中线仓。",
        "sell_position": "次日冲高先卖 1/2；午后不转强或跌破计划位全部离场。",
        "execution_discipline": "隔日票不能恋战；竞价和开盘承接不达标就撤，午后不转强不拖仓。",
        "no_go": "竞价不转强、开盘承接弱、次日兑现逻辑缺失时不做。",
        "applicable_market": "适合隔日强弱切换快、竞价与开盘承接决定盈亏的短节奏行情。",
        "capacity_limit": "更适合轻仓滚动试错，不适合在次日兑现逻辑不清时大仓位隔夜。",
        "standard_action_buy_fallback": "先看竞价转强和开盘承接，再做隔日试错。",
        "standard_action_sell_fallback": "次日不及预期就快速退出。",
        "failure_sample": "最容易失败在竞价不转强、开盘承接弱、次日兑现失败却没有及时认错。",
    },
    "掘龙决策": {
        "short_label": "决策",
        "scene_copy": "适合把主线、资金、位置和节奏综合起来做最终动作判断。",
        "product_positioning": "综合决策，适合做主线、位置、资金与节奏的总判断。",
        "capital_style": "均衡配置 / 最终决策",
        "badge_palette": ("#4b235f", "#db9bff"),
        "empty_hint": "等待综合评分生成后更新最终执行候选。",
        "default_risk_level": "中风险",
        "low_flag_risk_level": "中风险",
        "position_hint": "先按综合结论试仓，确认后再进入交易计划。",
        "buy_position": "按综合评分先 2 成试仓；多项信号共振后加到 3-4 成，单票最高 5 成。",
        "sell_position": "综合优势下降先减 1/3；主线、资金、位置三项同时转弱时退出。",
        "execution_discipline": "必须主线、资金、位置至少两项同向；信号冲突时降级观察，不强行下结论。",
        "no_go": "主线不清、信号冲突、价位没有形成时不做。",
        "applicable_market": "适合主线、资金、位置与节奏需要统一判断的综合型行情。",
        "capacity_limit": "容量跟随总分与执行闸门动态调整，不适合脱离主线单独重仓。",
        "standard_action_buy_fallback": "先按综合结论试仓。",
        "standard_action_sell_fallback": "失去优势后按计划退出。",
        "failure_sample": "最容易失败在主线、位置和资金信号互相冲突时仍强行下结论。",
    },
}


def _normalize_token(value: str) -> str:
    text = str(value or "").strip().lower()
    for token in (" ", "\t", "\n", "\r", "-", "_", "/", "\\"):
        text = text.replace(token, "")
    return text


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


_FORMULA_CONTEXT_SPECS: dict[str, tuple[str, str]] = {
    "technical": ("技术分", "来自扫描与技术结构的基础强度分。"),
    "position": ("位置分", "衡量位置舒适度、突破/回踩位置与追高风险。"),
    "persistence": ("持续性", "衡量信号延续性、趋势稳定度与回测延续。"),
    "news": ("消息分", "来自新闻催化、情绪热度与题材刺激。"),
    "leader": ("龙头属性", "来自龙头识别、前排属性和主线辨识。"),
    "main_force_bias": ("主力偏置", "命中主力/机构/净流入关键词时的附加加分。"),
    "board_bias": ("打板偏置", "命中涨停/回封/连板关键词时的附加加分。"),
    "value_bias": ("低吸偏置", "命中低吸/修复/回踩关键词时的附加加分。"),
    "one_day_bias": ("隔日偏置", "命中次日溢价/隔夜/高开等关键词时的附加加分。"),
    "tail_buy_bias": ("尾盘偏置", "命中尾盘/14:30/次日开盘等关键词时的附加加分。"),
    "next_day_window": ("一日持股窗口", "一日持股法的节奏窗口分。"),
    "tail_buy_window": ("尾盘窗口", "尾盘买入法的尾盘回流窗口分。"),
    "board_window": ("打板窗口", "打板节奏与封板窗口分。"),
    "value_window": ("低吸窗口", "低吸修复窗口与安全边际分。"),
    "half_position_bias": ("半仓做T偏置", "命中半仓、底仓、做T、高抛低吸等关键词时的附加加分。"),
    "t_trade_window": ("做T窗口", "半仓持股法的高抛低吸滚动窗口分。"),
    "single_stock_focus": ("单票熟悉度", "衡量是否强调专注一只熟悉股票、反复跟踪和节奏熟悉。"),
}


@dataclass(frozen=True)
class StrategyPlanDefaults:
    stop_pct: float = 0.05
    target_pct: float = 0.08
    budget_multiplier_strong: float = 1.0
    budget_multiplier_normal: float = 1.0
    budget_sentiment_threshold: float = 72.0


@dataclass(frozen=True)
class StrategyDefinition:
    name: str
    score_field: str
    description: str = ""
    aliases: tuple[str, ...] = ()
    enabled: bool = True
    formula_stage: str = "base"
    formula_weights: dict[str, float] = field(default_factory=dict)
    plan_defaults: StrategyPlanDefaults = field(default_factory=StrategyPlanDefaults)
    ui_metadata: dict[str, object] = field(default_factory=dict)
    order_index: int = 0
    source_type: str = "catalog"
    source_path: str = ""
    readonly: bool = False
    runtime_compute: Callable[..., float] | None = None
    script_capabilities: dict[str, object] = field(default_factory=dict)


class StrategyRegistry:
    def __init__(self, definitions: list[StrategyDefinition], *, diagnostics: list[dict[str, str]] | None = None) -> None:
        self.definitions = tuple(definitions)
        self._definitions_by_name = {item.name: item for item in self.definitions}
        self._token_to_strategy_name = self._build_token_index()
        self._computation_order = self._build_computation_order()
        self.diagnostics = tuple(dict(item) for item in (diagnostics or []))

    @property
    def strategy_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.definitions if item.enabled)

    @property
    def all_strategy_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.definitions)

    @property
    def base_strategy_names(self) -> tuple[str, ...]:
        return tuple(item.name for item in self.definitions if item.enabled and item.formula_stage != "aggregate")

    @property
    def active_definitions(self) -> tuple[StrategyDefinition, ...]:
        return tuple(item for item in self.definitions if item.enabled)

    def canonical_strategy_name(self, value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        normalized = _normalize_token(raw)
        return self._token_to_strategy_name.get(normalized, raw)

    def definition(self, strategy_name: str) -> StrategyDefinition | None:
        canonical = self.canonical_strategy_name(strategy_name)
        return self._definitions_by_name.get(canonical)

    def score_field(self, strategy_name: str) -> str:
        definition = self.definition(strategy_name)
        return definition.score_field if definition is not None else ""

    def plan_defaults(self, strategy_name: str) -> StrategyPlanDefaults:
        definition = self.definition(strategy_name)
        if definition is not None:
            return definition.plan_defaults
        return StrategyPlanDefaults()

    def filter_labels(self, *, include_all: bool = True) -> list[str]:
        labels = list(self.strategy_names)
        return ["全部", *labels] if include_all else labels

    def score_field_map(self) -> dict[str, str]:
        return {item.name: item.score_field for item in self.active_definitions}

    def workbench_specs(self) -> list[tuple[str, str]]:
        return [(item.name, item.description) for item in self.active_definitions]

    def source_meta(self, strategy_name: str) -> dict[str, object]:
        definition = self.definition(strategy_name)
        if definition is None:
            return {
                "source_type": "catalog",
                "source_path": "",
                "readonly": False,
            }
        return {
            "source_type": str(definition.source_type or "catalog"),
            "source_path": str(definition.source_path or ""),
            "readonly": bool(definition.readonly),
        }

    def score_map_from_payload(self, payload: Mapping[str, object] | None) -> dict[str, float]:
        source = dict(payload or {})
        strategy_scores: dict[str, float] = {}
        for definition in self.definitions:
            strategy_scores[definition.name] = round(_safe_float(source.get(definition.score_field), 0.0), 2)
        return strategy_scores

    def score_map_for_item(self, item: object | None) -> dict[str, float]:
        if item is None:
            return {name: 0.0 for name in self.all_strategy_names}
        stored = getattr(item, "strategy_scores", None)
        strategy_scores: dict[str, float] = {name: 0.0 for name in self.all_strategy_names}
        if isinstance(stored, Mapping):
            for key, value in stored.items():
                strategy_name = self.canonical_strategy_name(str(key or ""))
                if strategy_name in strategy_scores:
                    strategy_scores[strategy_name] = round(_safe_float(value), 2)
        for definition in self.definitions:
            if strategy_scores.get(definition.name, 0.0) > 0:
                continue
            strategy_scores[definition.name] = round(_safe_float(getattr(item, definition.score_field, 0.0), 0.0), 2)
        return strategy_scores

    def score_for_item(self, item: object | None, strategy_name: str, default: float = 0.0) -> float:
        canonical = self.canonical_strategy_name(strategy_name)
        if not canonical:
            return default
        definition = self.definition(canonical)
        if definition is not None and not definition.enabled:
            return default
        strategy_scores = self.score_map_for_item(item)
        score = strategy_scores.get(canonical)
        if score is None:
            return default
        if canonical == "掘龙决策" and score <= 0 and item is not None:
            return _safe_float(getattr(item, "total_score", default), default)
        return score

    def ranked_scores_for_item(self, item: object | None) -> list[tuple[str, float]]:
        strategy_scores = self.score_map_for_item(item)
        ranked = sorted(
            ((definition.name, strategy_scores.get(definition.name, 0.0), definition.order_index) for definition in self.active_definitions),
            key=lambda entry: (entry[1], -entry[2]),
            reverse=True,
        )
        return [(name, score) for name, score, _ in ranked]

    def primary_strategy_for_item(self, item: object | None, default: str = "") -> str:
        if item is None:
            return default
        current = self.canonical_strategy_name(str(getattr(item, "primary_strategy", "") or ""))
        current_definition = self.definition(current) if current else None
        if current and (current_definition is None or current_definition.enabled):
            return current
        ranked = self.ranked_scores_for_item(item)
        if ranked and ranked[0][1] > 0:
            return ranked[0][0]
        return default

    def score_summary(self, item: object | None, *, limit: int | None = None, separator: str = " / ") -> str:
        ranked = self.ranked_scores_for_item(item)
        if limit is not None and limit > 0:
            ranked = ranked[:limit]
        parts = [f"{name} {score:.1f}" for name, score in ranked if score > 0]
        return separator.join(parts)

    def compute_scores(
        self,
        context: Mapping[str, object],
        *,
        adjustments_by_name: Mapping[str, float] | None = None,
    ) -> dict[str, float | str]:
        normalized_context = {_normalize_token(key): _safe_float(value) for key, value in context.items()}
        normalized_adjustments = {
            self.canonical_strategy_name(name): _safe_float(value)
            for name, value in dict(adjustments_by_name or {}).items()
            if self.canonical_strategy_name(name)
        }
        computed_scores: dict[str, float] = {}
        for definition in (item for item in self._computation_order if item.enabled):
            score = self._compute_definition_score(definition, normalized_context, computed_scores)
            score = max(0.0, min(score, 99.0))
            adjustment = normalized_adjustments.get(definition.name, 0.0)
            if adjustment:
                score = max(0.0, min(score + adjustment, 99.0))
            computed_scores[definition.name] = round(score, 2)

        ranked = sorted(
            ((definition.name, computed_scores.get(definition.name, 0.0), definition.order_index) for definition in self.active_definitions),
            key=lambda item: (item[1], -item[2]),
            reverse=True,
        )
        payload: dict[str, float | str] = {"primary_strategy": ranked[0][0] if ranked else ""}
        for definition in self.definitions:
            payload[definition.score_field] = computed_scores.get(definition.name, 0.0)
        return payload

    def _resolve_formula_value(
        self,
        token: str,
        context: Mapping[str, float],
        computed_scores: Mapping[str, float],
    ) -> float:
        normalized = _normalize_token(token)
        strategy_name = self._token_to_strategy_name.get(normalized, "")
        if strategy_name and strategy_name in computed_scores:
            return computed_scores[strategy_name]
        return context.get(normalized, 0.0)

    def _build_token_index(self) -> dict[str, str]:
        token_map: dict[str, str] = {}
        for definition in self.definitions:
            for token in self._definition_tokens(definition):
                token_map[token] = definition.name
        for alias, strategy_name in _LEGACY_ALIAS_MAP.items():
            token_map[_normalize_token(alias)] = strategy_name
        return token_map

    def _definition_tokens(self, definition: StrategyDefinition) -> set[str]:
        tokens = {
            _normalize_token(definition.name),
            _normalize_token(definition.score_field),
        }
        if definition.score_field.endswith("_score"):
            tokens.add(_normalize_token(definition.score_field[: -len("_score")]))
        for alias in definition.aliases:
            tokens.add(_normalize_token(alias))
        return {item for item in tokens if item}

    def _definition_dependencies(self, definition: StrategyDefinition) -> set[str]:
        dependencies: set[str] = set()
        for token in definition.formula_weights:
            normalized = _normalize_token(token)
            dependency = self._token_to_strategy_name.get(normalized, "")
            if dependency and dependency != definition.name:
                dependencies.add(dependency)
        return dependencies

    def _build_computation_order(self) -> tuple[StrategyDefinition, ...]:
        dependencies = {item.name: self._definition_dependencies(item) for item in self.definitions}
        dependents: dict[str, set[str]] = {item.name: set() for item in self.definitions}
        for strategy_name, current_dependencies in dependencies.items():
            for dependency in current_dependencies:
                dependents.setdefault(dependency, set()).add(strategy_name)

        indegree = {strategy_name: len(current_dependencies) for strategy_name, current_dependencies in dependencies.items()}
        ready = sorted(
            (item for item in self.definitions if indegree.get(item.name, 0) == 0),
            key=lambda item: item.order_index,
        )
        ordered: list[StrategyDefinition] = []
        while ready:
            current = ready.pop(0)
            ordered.append(current)
            for follower_name in sorted(dependents.get(current.name, ()), key=lambda name: self._definitions_by_name[name].order_index):
                indegree[follower_name] -= 1
                if indegree[follower_name] == 0:
                    ready.append(self._definitions_by_name[follower_name])
                    ready.sort(key=lambda item: item.order_index)

        if len(ordered) != len(self.definitions):
            return tuple(sorted(self.definitions, key=lambda item: item.order_index))
        return tuple(ordered)

    def _compute_definition_score(
        self,
        definition: StrategyDefinition,
        context: Mapping[str, float],
        computed_scores: Mapping[str, float],
    ) -> float:
        runtime_compute = definition.runtime_compute
        if callable(runtime_compute):
            dependency_scores = dict(computed_scores)
            try:
                return _safe_float(
                    runtime_compute(
                        dict(context),
                        dependency_scores=dependency_scores,
                        definition=definition,
                    )
                )
            except TypeError:
                try:
                    return _safe_float(runtime_compute(dict(context), dependency_scores))
                except TypeError:
                    return _safe_float(runtime_compute(dict(context)))
        score = 0.0
        for key, weight in definition.formula_weights.items():
            score += self._resolve_formula_value(key, context, computed_scores) * _safe_float(weight)
        return score


def _catalog_path() -> Path:
    return Path(__file__).with_name("strategy_catalog.json")


def _strategy_plugin_directory() -> Path:
    return Path(__file__).with_name("strategy_plugins")


def _load_catalog_payload() -> dict[str, object]:
    path = _catalog_path()
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(payload, dict):
                return payload
        except Exception:
            pass
    return _DEFAULT_CATALOG_PAYLOAD


def _parse_plan_defaults(payload: Mapping[str, object]) -> StrategyPlanDefaults:
    return StrategyPlanDefaults(
        stop_pct=_safe_float(payload.get("stop_pct"), 0.05),
        target_pct=_safe_float(payload.get("target_pct"), 0.08),
        budget_multiplier_strong=_safe_float(payload.get("budget_multiplier_strong"), 1.0),
        budget_multiplier_normal=_safe_float(payload.get("budget_multiplier_normal"), 1.0),
        budget_sentiment_threshold=_safe_float(payload.get("budget_sentiment_threshold"), 72.0),
    )


def _json_safe_value(value: object) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    return value


def _json_clone(value: Any) -> Any:
    return json.loads(json.dumps(_json_safe_value(value), ensure_ascii=False))


def normalize_script_capabilities(payload: Mapping[str, object] | None) -> dict[str, object]:
    raw = dict(payload or {})
    required_context_keys = [
        str(item).strip()
        for item in list(raw.get("required_context_keys", []) or [])
        if str(item).strip()
    ]
    dependency_strategy_names = [
        str(item).strip()
        for item in list(raw.get("dependency_strategy_names", []) or [])
        if str(item).strip()
    ]
    return {
        "required_context_keys": required_context_keys,
        "dependency_strategy_names": dependency_strategy_names,
        "allow_dependency_scores": bool(raw.get("allow_dependency_scores", bool(dependency_strategy_names))),
        "notes": str(raw.get("notes", "") or "").strip(),
    }


def derive_script_capabilities_from_payload(payload: Mapping[str, object] | None) -> dict[str, object]:
    raw = dict(payload or {})
    formula_weights = {
        str(key).strip(): _safe_float(value)
        for key, value in dict(raw.get("formula_weights", {}) or {}).items()
        if str(key).strip()
    }
    registry = get_strategy_registry()
    required_context_keys: list[str] = []
    dependency_strategy_names: list[str] = []
    for key in formula_weights:
        normalized = _normalize_token(key)
        if normalized in _KNOWN_SCRIPT_CONTEXT_TOKENS:
            required_context_keys.append(_KNOWN_SCRIPT_CONTEXT_TOKENS[normalized])
            continue
        canonical = registry.canonical_strategy_name(key)
        definition = registry.definition(canonical)
        if definition is not None:
            dependency_strategy_names.append(definition.name)
    return normalize_script_capabilities(
        {
            "required_context_keys": list(dict.fromkeys(required_context_keys)),
            "dependency_strategy_names": list(dict.fromkeys(dependency_strategy_names)),
            "allow_dependency_scores": bool(dependency_strategy_names),
        }
    )


def normalize_strategy_definition_payload(
    payload: Mapping[str, object],
    *,
    fallback_name: str = "",
) -> dict[str, object]:
    raw = dict(payload or {})
    name = str(raw.get("name", "") or fallback_name).strip()
    if not name:
        raise ValueError("战法配置缺少 name。")
    normalized_token = _normalize_token(name) or "strategy"
    score_field = str(raw.get("score_field", "") or f"{normalized_token}_score").strip()
    if not score_field:
        raise ValueError("战法配置缺少 score_field。")
    formula_stage = str(raw.get("formula_stage", "") or "base").strip().lower()
    if formula_stage not in {"base", "aggregate"}:
        formula_stage = "base"
    aliases = [
        str(item or "").strip()
        for item in list(raw.get("aliases", []) or [])
        if str(item or "").strip()
    ]
    formula_weights = {
        str(key).strip(): _safe_float(value)
        for key, value in dict(raw.get("formula_weights", {}) or {}).items()
        if str(key).strip()
    }
    ui_metadata = _json_safe_value(dict(raw.get("ui_metadata", {}) or {}))
    source_type = str(raw.get("source_type", "") or "catalog").strip().lower() or "catalog"
    source_path = str(raw.get("source_path", "") or "").strip()
    readonly = bool(raw.get("readonly", source_type == "script"))
    script_capabilities = normalize_script_capabilities(dict(raw.get("script_capabilities", {}) or {}))
    return {
        "name": name,
        "score_field": score_field,
        "description": str(raw.get("description", "") or ""),
        "aliases": aliases,
        "enabled": bool(raw.get("enabled", True)),
        "formula_stage": formula_stage,
        "ui_metadata": ui_metadata,
        "formula_weights": formula_weights,
        "source_type": source_type,
        "source_path": source_path,
        "readonly": readonly,
        "script_capabilities": script_capabilities,
        "plan_defaults": {
            "stop_pct": _safe_float(dict(raw.get("plan_defaults", {}) or {}).get("stop_pct"), 0.05),
            "target_pct": _safe_float(dict(raw.get("plan_defaults", {}) or {}).get("target_pct"), 0.08),
            "budget_multiplier_strong": _safe_float(dict(raw.get("plan_defaults", {}) or {}).get("budget_multiplier_strong"), 1.0),
            "budget_multiplier_normal": _safe_float(dict(raw.get("plan_defaults", {}) or {}).get("budget_multiplier_normal"), 1.0),
            "budget_sentiment_threshold": _safe_float(dict(raw.get("plan_defaults", {}) or {}).get("budget_sentiment_threshold"), 72.0),
        },
    }


def strategy_formula_example_weights(formula_stage: str = "base") -> dict[str, float]:
    stage = str(formula_stage or "base").strip().lower()
    if stage == "aggregate":
        base_names = [
            definition.name
            for definition in get_strategy_registry().active_definitions
            if definition.formula_stage != "aggregate"
        ]
        if not base_names:
            return {
                "technical": 0.32,
                "position": 0.24,
                "persistence": 0.20,
                "news": 0.14,
                "leader": 0.10,
            }
        selected = base_names[:4]
        base_weight = round(0.7 / max(len(selected), 1), 2)
        example = {name: base_weight for name in selected}
        example.update(
            {
                "technical": 0.12,
                "position": 0.08,
                "persistence": 0.06,
                "news": 0.04,
            }
        )
        return example
    return {
        "technical": 0.25,
        "position": 0.20,
        "persistence": 0.20,
        "news": 0.10,
        "leader": 0.10,
        "main_force_bias": 0.15,
    }


def list_strategy_formula_inputs(formula_stage: str = "base") -> list[dict[str, str]]:
    stage = str(formula_stage or "base").strip().lower()
    items = [
        {
            "key": key,
            "label": label,
            "group": "基础因子",
            "description": description,
        }
        for key, (label, description) in _FORMULA_CONTEXT_SPECS.items()
    ]
    for definition in get_strategy_registry().active_definitions:
        if stage == "base" and definition.formula_stage == "aggregate":
            continue
        alias_text = f"；别名 {', '.join(definition.aliases[:2])}" if definition.aliases else ""
        items.append(
            {
                "key": definition.name,
                "label": definition.name,
                "group": "策略依赖",
                "description": f"直接引用 {definition.name} 已计算得分；也可写 {definition.score_field}{alias_text}。",
            }
        )
    return items


def list_strategy_context_inputs() -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "label": label,
            "description": description,
        }
        for key, (label, description) in _FORMULA_CONTEXT_SPECS.items()
    ]


def strategy_formula_reference_text(formula_stage: str = "base") -> str:
    stage = str(formula_stage or "base").strip().lower()
    stage_label = "聚合战法" if stage == "aggregate" else "基础战法"
    grouped: dict[str, list[dict[str, str]]] = {}
    for item in list_strategy_formula_inputs(stage):
        grouped.setdefault(item["group"], []).append(item)

    lines = [
        f"公式参考（{stage_label}）",
        "可直接写基础因子键；若引用其他战法，可写战法名称、score_field 或别名。",
        "基础战法不要依赖聚合战法；任何战法都不要引用自己。",
    ]
    for group_name in ("基础因子", "策略依赖"):
        entries = grouped.get(group_name, [])
        if not entries:
            continue
        lines.append("")
        lines.append(group_name)
        for entry in entries:
            lines.append(f"- {entry['key']}: {entry['description']}")
    lines.append("")
    lines.append("示例权重")
    lines.append(json.dumps(strategy_formula_example_weights(stage), ensure_ascii=False, indent=2))
    return "\n".join(lines)


def validate_strategy_definition_payload(
    payload: Mapping[str, object],
    *,
    previous_name: str = "",
) -> dict[str, object]:
    normalized = normalize_strategy_definition_payload(payload)
    registry = get_strategy_registry()
    stage = str(normalized.get("formula_stage", "base") or "base").strip().lower()
    current_name = str(normalized.get("name", "") or "").strip()
    ignore_names = {name for name in {current_name, str(previous_name or "").strip()} if name}
    formula_weights = dict(normalized.get("formula_weights", {}) or {})

    errors: list[str] = []
    warnings: list[str] = []
    script_capability_errors: list[str] = []
    script_capability_warnings: list[str] = []
    context_formula_keys: list[str] = []
    dependency_formula_keys: list[str] = []
    unknown_formula_keys: list[str] = []
    formula_context_tokens = {_normalize_token(key): key for key in _FORMULA_CONTEXT_SPECS}

    if not formula_weights:
        errors.append("公式权重不能为空，否则这套战法会始终算不出有效分数。")
    elif all(abs(_safe_float(value)) <= 0.0 for value in formula_weights.values()):
        warnings.append("公式权重目前全部为 0，当前战法得分会始终为 0。")

    if not str(normalized.get("score_field", "") or "").endswith("_score"):
        warnings.append("评分字段建议以 _score 结尾，便于运行时识别与排序。")
    if not str(normalized.get("description", "") or "").strip():
        warnings.append("战法简介为空，后续卡片、导出和工作台说明会比较弱。")

    alias_tokens: set[str] = set()
    duplicate_aliases: list[str] = []
    for alias in list(normalized.get("aliases", []) or []):
        normalized_alias = _normalize_token(str(alias or ""))
        if not normalized_alias:
            continue
        if normalized_alias in alias_tokens:
            duplicate_aliases.append(str(alias))
        alias_tokens.add(normalized_alias)
    if duplicate_aliases:
        warnings.append(f"别名里存在重复项：{', '.join(duplicate_aliases)}。")

    score_field_token = _normalize_token(str(normalized.get("score_field", "") or ""))
    for definition in registry.definitions:
        if definition.name in ignore_names:
            continue
        if _normalize_token(definition.score_field) == score_field_token:
            errors.append(f"评分字段 {normalized['score_field']} 与现有战法 {definition.name} 冲突。")
            break

    name_candidates = [current_name, *list(normalized.get("aliases", []) or [])]
    for candidate in name_candidates:
        raw_candidate = str(candidate or "").strip()
        if not raw_candidate:
            continue
        mapped_name = registry.canonical_strategy_name(raw_candidate)
        if mapped_name and mapped_name != raw_candidate and mapped_name not in ignore_names:
            errors.append(f"名称或别名 {raw_candidate} 会映射到现有战法 {mapped_name}，请换一个。")
            break
        mapped_definition = registry.definition(mapped_name)
        if mapped_definition is not None and mapped_definition.name not in ignore_names and mapped_definition.name == mapped_name:
            errors.append(f"名称或别名 {raw_candidate} 与现有战法 {mapped_name} 冲突。")
            break

    current_tokens = {
        _normalize_token(current_name),
        score_field_token,
    }
    if score_field_token.endswith("score"):
        current_tokens.add(score_field_token[: -len("score")])
    current_tokens.update(alias_tokens)

    for key in formula_weights:
        token = _normalize_token(str(key or ""))
        if not token:
            continue
        if token in formula_context_tokens:
            context_formula_keys.append(str(key))
            continue
        if token in current_tokens:
            errors.append(f"公式项 {key} 不能引用当前战法自己，否则会形成空引用。")
            continue
        dependency_name = registry._token_to_strategy_name.get(token, "")
        dependency_definition = registry.definition(dependency_name)
        if dependency_definition is None:
            unknown_formula_keys.append(str(key))
            continue
        if not dependency_definition.enabled:
            errors.append(f"公式项 {key} 引用了已停用战法 {dependency_definition.name}，运行时不会生效。")
            continue
        if stage == "base" and dependency_definition.formula_stage == "aggregate":
            errors.append(f"基础战法不能依赖聚合战法 {dependency_definition.name}。")
            continue
        dependency_formula_keys.append(dependency_definition.name)

    if unknown_formula_keys:
        errors.append(f"存在未识别的公式项：{', '.join(unknown_formula_keys)}。")

    script_capabilities = normalize_script_capabilities(dict(normalized.get("script_capabilities", {}) or {}))
    required_context_keys = list(script_capabilities.get("required_context_keys", []) or [])
    dependency_strategy_names = list(script_capabilities.get("dependency_strategy_names", []) or [])
    allow_dependency_scores = bool(script_capabilities.get("allow_dependency_scores", False))
    unknown_script_context_keys = [key for key in required_context_keys if _normalize_token(key) not in _KNOWN_SCRIPT_CONTEXT_TOKENS]
    if unknown_script_context_keys:
        message = f"脚本上下文字段未识别：{', '.join(unknown_script_context_keys)}。"
        errors.append(message)
        script_capability_errors.append(message)
    resolved_dependency_names: list[str] = []
    for dependency_name in dependency_strategy_names:
        canonical_dependency = registry.canonical_strategy_name(dependency_name)
        dependency_definition = registry.definition(canonical_dependency)
        if dependency_definition is None:
            message = f"脚本依赖战法不存在：{dependency_name}。"
            errors.append(message)
            script_capability_errors.append(message)
            continue
        if dependency_definition.name == current_name:
            message = f"脚本依赖不能引用当前战法自己：{dependency_definition.name}。"
            errors.append(message)
            script_capability_errors.append(message)
            continue
        if stage == "base" and dependency_definition.formula_stage == "aggregate":
            message = f"基础战法不能在脚本依赖里引用聚合战法 {dependency_definition.name}。"
            errors.append(message)
            script_capability_errors.append(message)
            continue
        resolved_dependency_names.append(dependency_definition.name)
    if dependency_strategy_names and not allow_dependency_scores:
        message = "已声明脚本依赖战法，但未开启“允许读取依赖得分”，运行时不会按依赖声明读取这些得分。"
        warnings.append(message)
        script_capability_warnings.append(message)

    return {
        "normalized": normalized,
        "errors": errors,
        "warnings": warnings,
        "formula_keys": list(formula_weights),
        "context_formula_keys": context_formula_keys,
        "dependency_formula_keys": list(dict.fromkeys(dependency_formula_keys)),
        "unknown_formula_keys": unknown_formula_keys,
        "script_required_context_keys": required_context_keys,
        "script_dependency_names": list(dict.fromkeys(resolved_dependency_names)),
        "unknown_script_context_keys": unknown_script_context_keys,
        "script_capability_errors": script_capability_errors,
        "script_capability_warnings": script_capability_warnings,
    }


def strategy_catalog_path() -> Path:
    return _catalog_path()


def load_strategy_catalog_payload() -> dict[str, object]:
    return _json_clone(_load_catalog_payload())


def build_strategy_template_payload(name: str = "新战法") -> dict[str, object]:
    title = str(name or "").strip() or "新战法"
    normalized = _normalize_token(title) or "custom_strategy"
    return {
        "name": title,
        "score_field": f"{normalized}_score",
        "description": "填写你的战法简介，例如抓量价共振与回踩确认。",
        "aliases": [],
        "enabled": True,
        "formula_stage": "base",
        "source_type": "catalog",
        "source_path": "",
        "readonly": False,
        "script_capabilities": {
            "required_context_keys": [],
            "dependency_strategy_names": [],
            "allow_dependency_scores": False,
            "notes": "",
        },
        "ui_metadata": {
            "short_label": title[:4],
            "scene_copy": "填写这套战法最适合的市场场景。",
            "product_positioning": "填写这套战法的定位和使用方式。",
            "capital_style": "填写这套战法更适合的资金风格。",
            "badge_palette": ["#24303a", "#dce4ef"],
            "empty_hint": f"等待{title}候选生成后更新。"
        },
        "formula_weights": strategy_formula_example_weights("base"),
        "plan_defaults": {
            "stop_pct": 0.05,
            "target_pct": 0.08,
            "budget_multiplier_strong": 1.0,
            "budget_multiplier_normal": 0.9,
            "budget_sentiment_threshold": 72.0,
        },
    }


def build_strategy_plugin_template_payload(name: str = "新脚本战法") -> dict[str, object]:
    payload = build_strategy_template_payload(name)
    payload["source_type"] = "script"
    payload["readonly"] = True
    return payload


def build_strategy_plugin_script_text(name: str = "新脚本战法", *, payload: Mapping[str, object] | None = None) -> str:
    base_payload = dict(payload or build_strategy_plugin_template_payload(name))
    payload = normalize_strategy_definition_payload(base_payload, fallback_name=name or str(base_payload.get("name", "") or "新脚本战法"))
    definition = {
        "name": payload["name"],
        "score_field": payload["score_field"],
        "description": payload["description"],
        "aliases": payload["aliases"],
        "enabled": payload["enabled"],
        "formula_stage": payload["formula_stage"],
        "formula_weights": payload["formula_weights"],
        "ui_metadata": payload["ui_metadata"],
        "plan_defaults": payload["plan_defaults"],
    }
    capabilities = normalize_script_capabilities(dict(payload.get("script_capabilities", {}) or {}))
    if not list(capabilities.get("required_context_keys", []) or []) and not list(capabilities.get("dependency_strategy_names", []) or []):
        capabilities = derive_script_capabilities_from_payload(payload)
    return "\n".join(
        [
            '"""Strategy plugin script.',
            "",
            "Rules:",
            "- expose STRATEGY_DEFINITION",
            "- optionally expose STRATEGY_CAPABILITIES",
            "- optionally expose compute_score(context, *, dependency_scores=None, definition=None)",
            "- return a score in [0, 99]",
            '"""',
            "",
            f"STRATEGY_DEFINITION = {pformat(definition, sort_dicts=False, width=100)}",
            f"STRATEGY_CAPABILITIES = {pformat(capabilities, sort_dicts=False, width=100)}",
            "",
            "",
            "def _token(value):",
            "    text = str(value or '').strip().lower()",
            "    for token in (' ', '\\t', '\\n', '\\r', '-', '_', '/', '\\\\'):",
            "        text = text.replace(token, '')",
            "    return text",
            "",
            "",
            "def _resolve_factor_value(key, context, dependency_scores):",
            "    normalized = _token(key)",
            "    if normalized in context:",
            "        return float(context.get(normalized, 0.0) or 0.0)",
            "    for name, value in dict(dependency_scores or {}).items():",
            "        if _token(name) == normalized:",
            "            return float(value or 0.0)",
            "    return 0.0",
            "",
            "def compute_score(context, *, dependency_scores=None, definition=None):",
            '    """',
            "    context: normalized runtime factor map",
            "    dependency_scores: already computed strategy scores",
            "    definition: current strategy definition",
            '    """',
            "    dependency_scores = dict(dependency_scores or {})",
            "    formula_weights = dict((definition.formula_weights or {}) if definition is not None else STRATEGY_DEFINITION.get('formula_weights', {}))",
            "    score = 0.0",
            "    for key, weight in formula_weights.items():",
            "        score += _resolve_factor_value(key, context, dependency_scores) * float(weight or 0.0)",
            "    return score",
            "",
        ]
    )


def strategy_plugin_file_path(name: str) -> Path:
    normalized = _normalize_token(str(name or "").strip()) or "custom_strategy_plugin"
    return strategy_plugin_directory() / f"{normalized}.py"


def create_strategy_plugin_script(name: str, *, overwrite: bool = False) -> Path:
    title = str(name or "").strip() or "新脚本战法"
    target = strategy_plugin_file_path(title)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"脚本已存在：{target}")
    target.write_text(build_strategy_plugin_script_text(title), encoding="utf-8")
    return target


def create_strategy_plugin_script_from_payload(
    payload: Mapping[str, object],
    *,
    overwrite: bool = False,
) -> Path:
    normalized = normalize_strategy_definition_payload(payload)
    title = str(normalized.get("name", "") or "").strip() or "新脚本战法"
    target = strategy_plugin_file_path(title)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() and not overwrite:
        raise FileExistsError(f"脚本已存在：{target}")
    target.write_text(build_strategy_plugin_script_text(title, payload=normalized), encoding="utf-8")
    return target


_KNOWN_SCRIPT_CONTEXT_TOKENS = {_normalize_token(key): key for key in _FORMULA_CONTEXT_SPECS}
_ALLOWED_SCRIPT_IMPORT_ROOTS = {"__future__", "math", "statistics", "typing"}
_ALLOWED_SCRIPT_TOP_LEVEL_ASSIGN_NAMES = {"STRATEGY_DEFINITION", "STRATEGY_CAPABILITIES"}


def _is_safe_script_assignment_value(node: ast.AST) -> bool:
    if isinstance(node, (ast.Dict, ast.List, ast.Tuple, ast.Set, ast.Constant)):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)) and isinstance(node.operand, ast.Constant):
        return True
    return False


def _validate_strategy_plugin_ast(path: Path) -> list[dict[str, str]]:
    diagnostics: list[dict[str, str]] = []
    try:
        source = path.read_text(encoding="utf-8")
    except Exception as exc:
        return [
            {
                "level": "error",
                "path": str(path),
                "name": path.stem,
                "message": f"脚本读取失败：{exc}",
            }
        ]
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return [
            {
                "level": "error",
                "path": str(path),
                "name": path.stem,
                "message": f"脚本语法错误：{exc.msg} (line {exc.lineno})",
            }
        ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = str(alias.name or "").split(".", 1)[0]
                if root not in _ALLOWED_SCRIPT_IMPORT_ROOTS:
                    diagnostics.append(
                        {
                            "level": "error",
                            "path": str(path),
                            "name": path.stem,
                            "message": f"不允许导入模块：{alias.name}",
                        }
                    )
        elif isinstance(node, ast.ImportFrom):
            module_name = str(node.module or "").strip()
            root = module_name.split(".", 1)[0] if module_name else ""
            if node.level != 0 or root not in _ALLOWED_SCRIPT_IMPORT_ROOTS:
                diagnostics.append(
                    {
                        "level": "error",
                        "path": str(path),
                        "name": path.stem,
                        "message": f"不允许导入模块：{'.' * node.level}{module_name}",
                    }
                )

    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
            continue
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
            continue
        if isinstance(node, ast.Assign):
            target_names = [item.id for item in node.targets if isinstance(item, ast.Name)]
            if not target_names or any(name not in _ALLOWED_SCRIPT_TOP_LEVEL_ASSIGN_NAMES for name in target_names):
                diagnostics.append(
                    {
                        "level": "error",
                        "path": str(path),
                        "name": path.stem,
                        "message": "顶层只允许定义 STRATEGY_DEFINITION / STRATEGY_CAPABILITIES 和函数。",
                    }
                )
                continue
            if not _is_safe_script_assignment_value(node.value):
                diagnostics.append(
                    {
                        "level": "error",
                        "path": str(path),
                        "name": path.stem,
                        "message": "顶层配置赋值必须是字面量常量，不能执行函数或表达式。",
                    }
                )
            continue
        diagnostics.append(
            {
                "level": "error",
                "path": str(path),
                "name": path.stem,
                "message": f"不允许的顶层语句：{type(node).__name__}",
            }
        )
    return diagnostics


def _persistable_strategy_payload(payload: Mapping[str, object]) -> dict[str, object]:
    normalized = normalize_strategy_definition_payload(payload)
    return {
        key: value
        for key, value in normalized.items()
        if key not in {"source_type", "source_path", "readonly"}
    }


def save_strategy_catalog_payload(payload: Mapping[str, object]) -> Path:
    raw_items = list(dict(payload or {}).get("strategies", []) or [])
    if not raw_items:
        raise ValueError("战法配置不能为空，至少保留一套战法。")
    normalized_items = [_persistable_strategy_payload(item) for item in raw_items if isinstance(item, dict)]
    if not normalized_items:
        raise ValueError("战法配置解析失败，未发现有效战法。")
    if not any(bool(item.get("enabled", True)) for item in normalized_items):
        raise ValueError("至少需要启用一套战法，不能全部停用。")
    path = strategy_catalog_path()
    path.write_text(
        json.dumps({"strategies": normalized_items}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def replace_strategy_in_catalog(
    strategy_payload: Mapping[str, object],
    *,
    previous_name: str = "",
) -> dict[str, object]:
    catalog = load_strategy_catalog_payload()
    strategies = [item for item in list(catalog.get("strategies", []) or []) if isinstance(item, dict)]
    normalized = _persistable_strategy_payload(strategy_payload)
    previous = str(previous_name or "").strip()
    name = str(normalized.get("name", "") or "").strip()
    updated: list[dict[str, object]] = []
    replaced = False
    for item in strategies:
        item_name = str(item.get("name", "") or "").strip()
        if item_name in {previous, name}:
            if not replaced:
                updated.append(normalized)
                replaced = True
            continue
        updated.append(item)
    if not replaced:
        updated.append(normalized)
    payload = {"strategies": updated}
    save_strategy_catalog_payload(payload)
    return payload


def delete_strategy_from_catalog(strategy_name: str) -> dict[str, object]:
    target = str(strategy_name or "").strip()
    if not target:
        raise ValueError("请选择要删除的战法。")
    catalog = load_strategy_catalog_payload()
    strategies = [item for item in list(catalog.get("strategies", []) or []) if isinstance(item, dict)]
    updated = [item for item in strategies if str(item.get("name", "") or "").strip() != target]
    if len(updated) == len(strategies):
        raise ValueError(f"未找到战法：{target}")
    if not updated:
        raise ValueError("至少需要保留一套战法，不能删除最后一个。")
    payload = {"strategies": updated}
    save_strategy_catalog_payload(payload)
    return payload


def import_strategy_payloads(import_payload: Mapping[str, object] | list[object]) -> dict[str, object]:
    if isinstance(import_payload, list):
        imported_items = [item for item in import_payload if isinstance(item, dict)]
    elif isinstance(import_payload, Mapping):
        imported_items = list(dict(import_payload).get("strategies", []) or [])
        if not imported_items and "name" in import_payload:
            imported_items = [dict(import_payload)]
        imported_items = [item for item in imported_items if isinstance(item, dict)]
    else:
        raise ValueError("导入的战法配置格式不正确。")
    if not imported_items:
        raise ValueError("导入文件里没有找到有效战法配置。")
    catalog = load_strategy_catalog_payload()
    strategies = [item for item in list(catalog.get("strategies", []) or []) if isinstance(item, dict)]
    strategy_map = {str(item.get("name", "") or "").strip(): item for item in strategies}
    for item in imported_items:
        normalized = _persistable_strategy_payload(item)
        strategy_map[str(normalized.get("name", "") or "").strip()] = normalized
    payload = {"strategies": list(strategy_map.values())}
    save_strategy_catalog_payload(payload)
    return payload


def strategy_plugin_directory() -> Path:
    return _strategy_plugin_directory()


def _load_strategy_plugin_specs() -> tuple[list[dict[str, object]], list[dict[str, str]]]:
    plugin_dir = strategy_plugin_directory()
    diagnostics: list[dict[str, str]] = []
    plugin_specs: list[dict[str, object]] = []
    if not plugin_dir.exists():
        return plugin_specs, diagnostics

    for path in sorted(plugin_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        ast_diagnostics = _validate_strategy_plugin_ast(path)
        diagnostics.extend(ast_diagnostics)
        if any(str(item.get("level", "") or "").strip().lower() == "error" for item in ast_diagnostics):
            continue
        module_name = f"quant_hunter.strategy_plugins.{path.stem}"
        try:
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                raise ImportError("无法构建模块加载器")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        except Exception as exc:
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(path),
                    "name": path.stem,
                    "message": f"脚本加载失败：{exc}",
                }
            )
            continue

        payload = getattr(module, "STRATEGY_DEFINITION", None)
        if not isinstance(payload, Mapping):
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(path),
                    "name": path.stem,
                    "message": "缺少 STRATEGY_DEFINITION 映射。",
                }
            )
            continue

        try:
            normalized = normalize_strategy_definition_payload(
                {
                    **dict(payload),
                    "script_capabilities": getattr(module, "STRATEGY_CAPABILITIES", dict(payload).get("script_capabilities", {})),
                    "source_type": "script",
                    "source_path": str(path),
                    "readonly": True,
                }
            )
        except Exception as exc:
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(path),
                    "name": path.stem,
                    "message": f"脚本元数据无效：{exc}",
                }
            )
            continue

        runtime_compute = getattr(module, "compute_score", None)
        if runtime_compute is not None and not callable(runtime_compute):
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(path),
                    "name": str(normalized.get("name", "") or path.stem),
                    "message": "compute_score 必须是可调用对象。",
                }
            )
            continue

        plugin_specs.append(
            {
                "payload": normalized,
                "runtime_compute": runtime_compute if callable(runtime_compute) else None,
                "path": str(path),
            }
        )
    return plugin_specs, diagnostics


def _validate_script_strategy_capabilities(
    registry: StrategyRegistry,
    definition: StrategyDefinition,
) -> list[dict[str, str]]:
    capabilities = dict(definition.script_capabilities or {})
    diagnostics: list[dict[str, str]] = []
    required_context_keys = [
        str(item).strip()
        for item in list(capabilities.get("required_context_keys", []) or [])
        if str(item).strip()
    ]
    dependency_strategy_names = [
        str(item).strip()
        for item in list(capabilities.get("dependency_strategy_names", []) or [])
        if str(item).strip()
    ]
    allow_dependency_scores = bool(capabilities.get("allow_dependency_scores", bool(dependency_strategy_names)))

    unknown_context_keys = [
        key for key in required_context_keys if _normalize_token(key) not in _KNOWN_SCRIPT_CONTEXT_TOKENS
    ]
    if unknown_context_keys:
        diagnostics.append(
            {
                "level": "error",
                "path": definition.source_path,
                "name": definition.name,
                "message": f"脚本能力声明里存在未知上下文键：{', '.join(unknown_context_keys)}",
            }
        )

    resolved_dependencies: list[str] = []
    for dependency_name in dependency_strategy_names:
        canonical = registry.canonical_strategy_name(dependency_name)
        dependency_definition = registry.definition(canonical)
        if dependency_definition is None:
            diagnostics.append(
                {
                    "level": "error",
                    "path": definition.source_path,
                    "name": definition.name,
                    "message": f"脚本能力声明里引用了不存在的依赖战法：{dependency_name}",
                }
            )
            continue
        if definition.formula_stage == "base" and dependency_definition.formula_stage == "aggregate":
            diagnostics.append(
                {
                    "level": "error",
                    "path": definition.source_path,
                    "name": definition.name,
                    "message": f"基础脚本战法不能声明聚合依赖：{dependency_definition.name}",
                }
            )
            continue
        resolved_dependencies.append(dependency_definition.name)

    if dependency_strategy_names and not allow_dependency_scores:
        diagnostics.append(
            {
                "level": "warning",
                "path": definition.source_path,
                "name": definition.name,
                "message": "已声明 dependency_strategy_names，但 allow_dependency_scores 为关闭，运行时不会按声明使用依赖得分。",
            }
        )

    if definition.runtime_compute is not None and not required_context_keys and not dependency_strategy_names:
        diagnostics.append(
            {
                "level": "info",
                "path": definition.source_path,
                "name": definition.name,
                "message": "脚本未声明 required_context_keys 或 dependency_strategy_names，建议补充脚本能力声明以便后续校验和维护。",
            }
        )

    return diagnostics


def script_capabilities_summary_text(payload: Mapping[str, object] | None) -> str:
    capabilities = normalize_script_capabilities(dict(payload or {}))
    required_context_keys = list(capabilities.get("required_context_keys", []) or [])
    dependency_strategy_names = list(capabilities.get("dependency_strategy_names", []) or [])
    allow_dependency_scores = bool(capabilities.get("allow_dependency_scores", False))
    notes = str(capabilities.get("notes", "") or "").strip()
    parts = [
        f"上下文 {', '.join(required_context_keys) if required_context_keys else '未声明'}",
        f"依赖 {', '.join(dependency_strategy_names) if dependency_strategy_names else '未声明'}",
        f"依赖得分 {'开启' if allow_dependency_scores else '关闭'}",
    ]
    if notes:
        parts.append(f"备注 {notes}")
    return " | ".join(parts)


def load_strategy_workspace_payload() -> dict[str, object]:
    catalog = load_strategy_catalog_payload()
    catalog_items = [
        normalize_strategy_definition_payload({**dict(item), "source_type": "catalog", "readonly": False})
        for item in list(catalog.get("strategies", []) or [])
        if isinstance(item, dict)
    ]
    plugin_specs, _diagnostics = _load_strategy_plugin_specs()
    plugin_items = [dict(item.get("payload", {}) or {}) for item in plugin_specs]
    return {
        "strategies": [*catalog_items, *plugin_items],
        "catalog_path": str(strategy_catalog_path()),
        "plugin_dir": str(strategy_plugin_directory()),
        "diagnostics": strategy_registry_diagnostics(),
    }


def _build_registry() -> StrategyRegistry:
    payload = _load_catalog_payload()
    raw_items = payload.get("strategies", []) if isinstance(payload, dict) else []
    definitions: list[StrategyDefinition] = []
    diagnostics: list[dict[str, str]] = []
    known_names: set[str] = set()
    known_score_fields: set[str] = set()
    for index, item in enumerate(raw_items):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "") or "").strip()
        score_field = str(item.get("score_field", "") or "").strip()
        if not name or not score_field:
            continue
        aliases = tuple(str(value).strip() for value in list(item.get("aliases", []) or []) if str(value).strip())
        formula_weights = {
            str(key).strip(): _safe_float(value)
            for key, value in dict(item.get("formula_weights", {}) or {}).items()
            if str(key).strip()
        }
        definition = StrategyDefinition(
            name=name,
            score_field=score_field,
            description=str(item.get("description", "") or ""),
            aliases=aliases,
            enabled=bool(item.get("enabled", True)),
            formula_stage=str(item.get("formula_stage", "") or "base"),
            formula_weights=formula_weights,
            plan_defaults=_parse_plan_defaults(dict(item.get("plan_defaults", {}) or {})),
            ui_metadata=dict(item.get("ui_metadata", {}) or {}),
            order_index=index,
            source_type="catalog",
            source_path="",
            readonly=False,
            script_capabilities=normalize_script_capabilities(dict(item.get("script_capabilities", {}) or {})),
        )
        definitions.append(definition)
        known_names.add(definition.name)
        known_score_fields.add(_normalize_token(definition.score_field))

    plugin_specs, plugin_diagnostics = _load_strategy_plugin_specs()
    diagnostics.extend(plugin_diagnostics)
    plugin_offset = len(definitions)
    for plugin_index, item in enumerate(plugin_specs):
        payload = dict(item.get("payload", {}) or {})
        name = str(payload.get("name", "") or "").strip()
        score_field = str(payload.get("score_field", "") or "").strip()
        if not name or not score_field:
            continue
        if name in known_names:
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(item.get("path", "") or ""),
                    "name": name,
                    "message": f"脚本战法 {name} 与现有战法重名，已跳过。",
                }
            )
            continue
        normalized_score_field = _normalize_token(score_field)
        if normalized_score_field in known_score_fields:
            diagnostics.append(
                {
                    "level": "error",
                    "path": str(item.get("path", "") or ""),
                    "name": name,
                    "message": f"脚本战法 {name} 的 score_field 与现有战法冲突，已跳过。",
                }
            )
            continue
        definitions.append(
            StrategyDefinition(
                name=name,
                score_field=score_field,
                description=str(payload.get("description", "") or ""),
                aliases=tuple(str(value).strip() for value in list(payload.get("aliases", []) or []) if str(value).strip()),
                enabled=bool(payload.get("enabled", True)),
                formula_stage=str(payload.get("formula_stage", "") or "base"),
                formula_weights={
                    str(key).strip(): _safe_float(value)
                    for key, value in dict(payload.get("formula_weights", {}) or {}).items()
                    if str(key).strip()
                },
                plan_defaults=_parse_plan_defaults(dict(payload.get("plan_defaults", {}) or {})),
                ui_metadata=dict(payload.get("ui_metadata", {}) or {}),
                order_index=plugin_offset + plugin_index,
                source_type="script",
                source_path=str(payload.get("source_path", "") or item.get("path", "") or ""),
                readonly=True,
                runtime_compute=item.get("runtime_compute") if callable(item.get("runtime_compute")) else None,
                script_capabilities=normalize_script_capabilities(dict(payload.get("script_capabilities", {}) or {})),
            )
        )
        known_names.add(name)
        known_score_fields.add(normalized_score_field)

    provisional_registry = StrategyRegistry(definitions, diagnostics=diagnostics)
    for definition in provisional_registry.definitions:
        if str(definition.source_type or "").strip().lower() != "script":
            continue
        diagnostics.extend(_validate_script_strategy_capabilities(provisional_registry, definition))
    return StrategyRegistry(definitions, diagnostics=diagnostics)


@lru_cache(maxsize=1)
def get_strategy_registry() -> StrategyRegistry:
    return _build_registry()


def reload_strategy_registry() -> StrategyRegistry:
    get_strategy_registry.cache_clear()
    return get_strategy_registry()


def get_strategy_filter_labels(*, include_all: bool = True) -> list[str]:
    return get_strategy_registry().filter_labels(include_all=include_all)


def get_strategy_score_fields() -> dict[str, str]:
    return get_strategy_registry().score_field_map()


def get_strategy_workbench_specs() -> list[tuple[str, str]]:
    return get_strategy_registry().workbench_specs()


def strategy_source_meta(strategy_name: str) -> dict[str, object]:
    return get_strategy_registry().source_meta(strategy_name)


def strategy_registry_diagnostics() -> list[dict[str, str]]:
    return [dict(item) for item in get_strategy_registry().diagnostics]


def strategy_score_map(item: object | None) -> dict[str, float]:
    return get_strategy_registry().score_map_for_item(item)


def strategy_score(item: object | None, strategy_name: str, default: float = 0.0) -> float:
    return get_strategy_registry().score_for_item(item, strategy_name, default)


def ranked_strategy_scores(item: object | None) -> list[tuple[str, float]]:
    return get_strategy_registry().ranked_scores_for_item(item)


def resolved_primary_strategy(item: object | None, default: str = "") -> str:
    return get_strategy_registry().primary_strategy_for_item(item, default=default)


def strategy_score_summary(item: object | None, *, limit: int | None = None, separator: str = " / ") -> str:
    return get_strategy_registry().score_summary(item, limit=limit, separator=separator)


def _strategy_ui_meta(strategy_name: str) -> dict[str, object]:
    registry = get_strategy_registry()
    canonical = registry.canonical_strategy_name(strategy_name) or str(strategy_name or "").strip()
    definition = registry.definition(canonical)
    payload = dict(_STRATEGY_UI_METADATA.get(canonical, {}))
    if definition is not None:
        payload.update(dict(definition.ui_metadata or {}))
        payload.setdefault("short_label", definition.name)
        payload.setdefault("scene_copy", f"适合{definition.description}。")
        payload.setdefault("product_positioning", definition.description or "等待机会池同步后再确认战法定位。")
        payload.setdefault("capital_style", "均衡配置 / 最终决策")
        payload.setdefault("empty_hint", f"等待{definition.name}候选生成后更新{definition.description}。")
    return payload


def strategy_short_label(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("short_label", strategy_name) or strategy_name)


def strategy_scene_copy(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("scene_copy", "适合等待机会池同步后再看具体打法。") or "适合等待机会池同步后再看具体打法。")


def strategy_product_positioning(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("product_positioning", "等待机会池同步后再确认战法定位。") or "等待机会池同步后再确认战法定位。")


def strategy_capital_style(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("capital_style", "等待同步") or "等待同步")


def strategy_default_risk_level(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("default_risk_level", "中风险") or "中风险")


def strategy_low_flag_risk_level(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("low_flag_risk_level", strategy_default_risk_level(strategy_name)) or strategy_default_risk_level(strategy_name))


def strategy_badge_palette_meta(strategy_name: str) -> tuple[str, str]:
    payload = _strategy_ui_meta(strategy_name)
    palette = payload.get("badge_palette")
    if isinstance(palette, (tuple, list)) and len(palette) == 2:
        return (str(palette[0]), str(palette[1]))
    return ("#24303a", "#dce4ef")


def strategy_empty_hint_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("empty_hint", "等待机会池生成后更新。") or "等待机会池生成后更新。")


def strategy_position_hint_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("position_hint", "先小仓验证，再决定是否继续。") or "先小仓验证，再决定是否继续。")


def strategy_buy_position_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("buy_position", strategy_position_hint_meta(strategy_name)) or strategy_position_hint_meta(strategy_name))


def strategy_sell_position_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("sell_position", "失去优势后按计划分批退出。") or "失去优势后按计划分批退出。")


def strategy_execution_discipline_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("execution_discipline", "严格按买入仓位、卖出仓位和失效条件执行，不临盘扩大风险。") or "严格按买入仓位、卖出仓位和失效条件执行，不临盘扩大风险。")


def strategy_no_go_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("no_go", "等待更多确认后再决定。") or "等待更多确认后再决定。")


def strategy_applicable_market_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("applicable_market", "等待样本和机会池同步后再确认适用行情。") or "等待样本和机会池同步后再确认适用行情。")


def strategy_capacity_limit_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("capacity_limit", "先小样本运行，确认稳定后再逐步扩大战法容量。") or "先小样本运行，确认稳定后再逐步扩大战法容量。")


def strategy_standard_action_meta(strategy_name: str) -> tuple[str, str]:
    payload = _strategy_ui_meta(strategy_name)
    return (
        str(payload.get("standard_action_buy_fallback", "先按综合结论试仓。") or "先按综合结论试仓。"),
        str(payload.get("standard_action_sell_fallback", "失去优势后按计划退出。") or "失去优势后按计划退出。"),
    )


def strategy_failure_sample_meta(strategy_name: str) -> str:
    payload = _strategy_ui_meta(strategy_name)
    return str(payload.get("failure_sample", "最容易失败在信号不一致却强行执行。") or "最容易失败在信号不一致却强行执行。")
