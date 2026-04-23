"""Example script strategy.

Rename or copy this file to a name without a leading underscore to activate it.
"""

STRATEGY_DEFINITION = {
    "name": "量价突破",
    "score_field": "volume_breakout_score",
    "description": "抓放量突破、承接确认和二次加速",
    "aliases": ["量价共振突破"],
    "enabled": True,
    "formula_stage": "base",
    "ui_metadata": {
        "short_label": "突破",
        "scene_copy": "适合放量突破、回踩承接清晰、主线扩散仍在的进攻段。",
        "product_positioning": "作为脚本型战法示例，演示如何用自定义算法替代固定权重公式。",
        "capital_style": "突破跟随 / 放量确认",
        "empty_hint": "等待量价突破候选生成后更新。",
    },
    "plan_defaults": {
        "stop_pct": 0.04,
        "target_pct": 0.10,
        "budget_multiplier_strong": 1.0,
        "budget_multiplier_normal": 0.9,
        "budget_sentiment_threshold": 72.0,
    },
}


def compute_score(context, *, dependency_scores=None, definition=None):
    dependency_scores = dict(dependency_scores or {})
    technical = float(context.get("technical", 0.0) or 0.0)
    persistence = float(context.get("persistence", 0.0) or 0.0)
    position = float(context.get("position", 0.0) or 0.0)
    news = float(context.get("news", 0.0) or 0.0)
    leader = float(context.get("leader", 0.0) or 0.0)
    main_force = float(context.get("mainforce", context.get("main_force", 0.0)) or 0.0)
    board_attack = float(dependency_scores.get("擒龙打板", 0.0) or 0.0)
    breakout_bonus = 10.0 if technical >= 75.0 and persistence >= 68.0 else 0.0
    return (
        technical * 0.32
        + persistence * 0.18
        + position * 0.14
        + news * 0.10
        + leader * 0.08
        + main_force * 0.10
        + board_attack * 0.08
        + breakout_bonus
    )
