from __future__ import annotations


THEME_OPTIONS = [
    ("sunrise", "晨曦"),
    ("ocean", "海雾"),
    ("graphite", "石墨"),
]

DISPLAY_TEXT = {
    "action": {
        "BUY": "买入",
        "SELL": "卖出",
        "AVOID": "回避",
        "WATCH": "观察",
        "HOLD": "持有",
        "REDUCE": "减仓",
        "RECLAIM_LONG": "回补做多",
        "TRAP_DETECTED": "诱多陷阱",
        "NONE": "无信号",
    },
    "label": {
        "RECLAIM_LONG": "回补做多",
        "TRAP_DETECTED": "诱多陷阱",
        "WATCH": "观察",
        "NONE": "无信号",
    },
    "order_status": {
        "SUBMITTED": "已委托",
        "FAILED": "委托失败",
    },
    "fill_status": {
        "PENDING": "待成交",
        "REJECTED": "已拒绝",
        "FILLED": "已成交",
    },
    "mode": {
        "export": "导出模式",
        "sdk": "SDK 模式",
    },
}

WORKSPACE_TAB_LABELS = [
    "龙头主控台",
    "策略扫描",
    "每日推荐",
    "打板监控",
    "统一登录",
    "明细复盘",
    "交易执行",
    "配置",
]

WORKSPACE_TAB_ORDER = [
    "overview",
    "scanner",
    "recommend",
    "board",
    "config",
    "auth",
    "detail",
    "broker",
]

WORKSPACE_LABEL_BY_KEY = {
    "overview": WORKSPACE_TAB_LABELS[0],
    "scanner": WORKSPACE_TAB_LABELS[1],
    "recommend": WORKSPACE_TAB_LABELS[2],
    "board": WORKSPACE_TAB_LABELS[3],
    "auth": WORKSPACE_TAB_LABELS[4],
    "detail": WORKSPACE_TAB_LABELS[5],
    "broker": WORKSPACE_TAB_LABELS[6],
    "config": WORKSPACE_TAB_LABELS[7],
}

OVERVIEW_QUICK_ROUTE_SPECS = {
    "市场总览": {"workspace": "overview", "widget": "intraday_chart_view"},
    "龙头池": {"workspace": "recommend", "widget": "daily_pool_table", "select_row": "daily_pool_table"},
    "涨跌分布": {"workspace": "overview", "widget": "market_breadth_text"},
    "资金方向": {"workspace": "overview", "widget": "market_capital_text"},
    "题材热度": {"workspace": "recommend", "widget": "theme_heat_table", "select_row": "theme_heat_table"},
    "交易决策": {"workspace": "recommend", "widget": "trade_plan_table", "select_row": "trade_plan_table"},
}

STRATEGY_FILTER_LABELS = ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "掘龙决策"]

STRATEGY_SCORE_FIELDS = {
    "龙头模型": "leader_model_score",
    "主力雷达": "main_force_score",
    "擒龙打板": "board_attack_score",
    "价值低吸": "value_recovery_score",
    "掘龙决策": "dragon_decision_score",
}

STRATEGY_WORKBENCH_SPECS = [
    ("龙头模型", "抓主线核心龙头与趋势延续"),
    ("主力雷达", "抓资金净流入和机构强承接"),
    ("擒龙打板", "抓强势确认、回封确认和连板加速"),
    ("价值低吸", "抓分歧回踩、低位承接和修复"),
    ("掘龙决策", "汇总前四大战法，给最终动作"),
]
