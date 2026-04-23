"""Half-position holding strategy plugin."""

STRATEGY_DEFINITION = {
    "name": "半仓持股法",
    "score_field": "half_position_hold_score",
    "description": "专注熟悉单票，底仓半仓持有，机动仓围绕高抛低吸做T",
    "aliases": ["半仓持股", "半仓做T", "做T", "高抛低吸", "单票滚动"],
    "enabled": True,
    "formula_stage": "base",
    "formula_weights": {
        "technical": 0.14,
        "persistence": 0.16,
        "position": 0.12,
        "news": 0.04,
        "t_trade_window": 0.18,
        "single_stock_focus": 0.16,
        "价值低吸": 0.08,
        "主力雷达": 0.05,
        "half_position_bias": 1.0,
    },
    "ui_metadata": {
        "short_label": "半仓",
        "scene_copy": "适合对单票股性熟悉、趋势未坏、分时波动可滚动做T的场景。",
        "product_positioning": "单票滚动战法，底仓半仓拿住，机动仓围绕支撑和冲高做高抛低吸。",
        "capital_style": "半仓底仓 / 机动做T",
        "badge_palette": ["#183f3a", "#76f0d2"],
        "empty_hint": "等待半仓持股候选生成后更新做T区间和高抛低吸节奏。",
        "default_risk_level": "中风险",
        "low_flag_risk_level": "中低风险",
        "position_hint": "底仓不超过半仓，剩余仓位只在熟悉节奏里做T，不追陌生脉冲。",
        "buy_position": "底仓固定 3 成；机动仓 1-2 成只在回踩承接时低吸，总仓不超过 5 成。",
        "sell_position": "冲高先卖机动仓 1-2 成；跌破防守位停止做T，底仓降到 1-2 成或退出。",
        "execution_discipline": "只做熟悉单票；底仓不能越做越重，机动仓只做T，跌破防守位必须停止做T。",
        "no_go": "股性不熟、趋势破位、盘中波动无规律、只能追涨不能低吸时不做。",
        "applicable_market": "适合趋势仍在、承接没有破坏、日内波动给出低吸和高抛空间的熟悉单票。",
        "capacity_limit": "只适合围绕一只熟悉票滚动，不适合扩成多票重仓或越跌越补。",
        "standard_action_buy_fallback": "先确认底仓半仓以内，再等回踩承接做机动仓低吸。",
        "standard_action_sell_fallback": "冲高先抛机动仓，底仓只在趋势破坏或纪律触发时收缩。",
        "failure_sample": "最容易失败在不熟悉股性却频繁做T，或跌破防守位后把机动仓补成满仓。",
    },
    "plan_defaults": {
        "stop_pct": 0.038,
        "target_pct": 0.048,
        "budget_multiplier_strong": 0.5,
        "budget_multiplier_normal": 0.5,
        "budget_sentiment_threshold": 70.0,
    },
}

STRATEGY_CAPABILITIES = {
    "required_context_keys": [
        "technical",
        "position",
        "persistence",
        "news",
        "half_position_bias",
        "t_trade_window",
        "single_stock_focus",
    ],
    "dependency_strategy_names": ["价值低吸", "主力雷达"],
    "allow_dependency_scores": True,
    "notes": "底仓半仓叠加机动仓做T，只有文本和窗口同时匹配时才放大得分。",
}


def _token(value):
    text = str(value or "").strip().lower()
    for token in (" ", "\t", "\n", "\r", "-", "_", "/", "\\"):
        text = text.replace(token, "")
    return text


def _value(mapping, key):
    try:
        return float(dict(mapping or {}).get(_token(key), 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _dependency_score(dependency_scores, name):
    normalized = _token(name)
    for strategy_name, value in dict(dependency_scores or {}).items():
        if _token(strategy_name) == normalized:
            try:
                return float(value or 0.0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def compute_score(context, *, dependency_scores=None, definition=None):
    technical = _value(context, "technical")
    position = _value(context, "position")
    persistence = _value(context, "persistence")
    news = _value(context, "news")
    half_position_bias = _value(context, "half_position_bias")
    t_trade_window = _value(context, "t_trade_window")
    single_stock_focus = _value(context, "single_stock_focus")
    low_absorb = _dependency_score(dependency_scores, "价值低吸")
    main_force = _dependency_score(dependency_scores, "主力雷达")

    score = (
        technical * 0.14
        + persistence * 0.16
        + position * 0.12
        + news * 0.04
        + t_trade_window * 0.18
        + single_stock_focus * 0.16
        + low_absorb * 0.08
        + main_force * 0.05
        + min(half_position_bias, 24.0)
    )
    if half_position_bias <= 0.0 and single_stock_focus <= 0.0:
        score = min(score, 66.0)
    if position >= 86.0:
        score -= min((position - 84.0) * 0.8, 10.0)
    if position < 45.0:
        score -= 6.0
    if technical < 52.0 or persistence < 48.0:
        score -= 8.0
    return score
