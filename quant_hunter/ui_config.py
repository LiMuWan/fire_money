from __future__ import annotations


THEME_OPTIONS = [
    ("sunrise", "晨曦"),
    ("ocean", "海雾"),
    ("graphite", "石墨"),
    ("pro_terminal", "专业黑金"),
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
    "市场机会工作台",
    "策略扫描",
    "每日推荐",
    "打板专项",
    "统一登录",
    "明细复盘",
    "交易执行",
    "参数配置",
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

DAILY_POOL_TABLE_HEADERS = [
    "状态",
    "股票标识",
    "股票ID",
    "交易代码",
    "主线",
    "位次",
    "角色",
    "窗口",
    "风险 / 总分",
    "策略",
    "热度",
    "级别",
    "总分",
    "龙头",
    "雷达",
    "打板",
    "低吸",
    "尾盘",
    "一日",
    "决策",
    "动作",
    "催化",
    "日期",
    "买卖价",
]

RECOMMEND_DEFAULT_STATUS_TEXT = "推荐状态：先看主线、趋势、消息与风险，再决定是否送审。"
RECOMMEND_DEFAULT_EMPTY_TITLE = "等待市场快照"
RECOMMEND_DEFAULT_EMPTY_HINT = "先载入样例数据，或直接重算机会池。"
RECOMMEND_DEFAULT_EMPTY_META = "刷新市场、导入样例或同步本地数据后，系统会生成今日综合机会池、送审优先级与执行链路。"
RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT = "载入样例数据"
RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT = "重算机会池"
RECOMMEND_DEFAULT_FOCUS_TEXT = "推荐焦点：等待高优先、观察与风险候选同步"
TRADE_PLAN_DEFAULT_FOCUS_TEXT = "计划焦点：等待生成今日交易计划"
ORDERS_DEFAULT_FOCUS_TEXT = "委托动作面板 / 委托焦点：等待选中委托建议"
BROKER_DEFAULT_STATUS_TEXT = "交易状态：先确认主线、趋势与消息，再进入委托确认。"


def workspace_name_for_index(index: int) -> str:
    if 0 <= index < len(WORKSPACE_TAB_ORDER):
        return WORKSPACE_LABEL_BY_KEY.get(WORKSPACE_TAB_ORDER[index], "未命名")
    return "未命名"

OVERVIEW_QUICK_ROUTE_SPECS = {
    "市场总览": {"workspace": "overview", "widget": "intraday_chart_view"},
    "主线龙头": {"workspace": "recommend", "widget": "daily_pool_table", "select_row": "daily_pool_table"},
    "趋势机会": {"workspace": "recommend", "widget": "daily_pool_table", "select_row": "daily_pool_table"},
    "消息催化": {"workspace": "overview", "widget": "market_breadth_text"},
    "买卖决策": {"workspace": "recommend", "widget": "trade_plan_table", "select_row": "trade_plan_table"},
    "复盘研究": {"workspace": "recommend", "widget": "recommend_review_text"},
}

STRATEGY_FILTER_LABELS = ["全部", "龙头模型", "主力雷达", "擒龙打板", "价值低吸", "尾盘买入法", "一日持股法", "掘龙决策"]

STRATEGY_SCORE_FIELDS = {
    "龙头模型": "leader_model_score",
    "主力雷达": "main_force_score",
    "擒龙打板": "board_attack_score",
    "价值低吸": "value_recovery_score",
    "尾盘买入法": "tail_buy_score",
    "一日持股法": "one_day_hold_score",
    "掘龙决策": "dragon_decision_score",
}

STRATEGY_WORKBENCH_SPECS = [
    ("龙头模型", "抓主线核心龙头与趋势延续"),
    ("主力雷达", "抓资金净流入和机构强承接"),
    ("擒龙打板", "抓强势确认、回封确认和打板节奏"),
    ("价值低吸", "抓分歧回踩、低位承接和修复"),
    ("尾盘买入法", "抓尾盘回流确认、次日开盘兑现和短隔夜纪律"),
    ("一日持股法", "抓次日溢价、隔日兑现和短线节奏"),
    ("掘龙决策", "汇总前五大战法，给最终动作"),
]
