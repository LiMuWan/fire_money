from __future__ import annotations

THEME_OPTIONS = [
    ("graphite", "专业终端"),
    ("cerulean", "钛蓝终端"),
    ("ember", "琥珀终端"),
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
    "统一登录",
    "每日推荐",
    "交易执行",
    "策略扫描",
    "打板专项",
    "明细复盘",
    "参数配置",
]

WORKSPACE_TAB_ORDER = [
    "overview",
    "auth",
    "recommend",
    "broker",
    "scanner",
    "board",
    "detail",
    "config",
]

WORKSPACE_LABEL_BY_KEY = {
    "overview": WORKSPACE_TAB_LABELS[0],
    "auth": WORKSPACE_TAB_LABELS[1],
    "recommend": WORKSPACE_TAB_LABELS[2],
    "broker": WORKSPACE_TAB_LABELS[3],
    "scanner": WORKSPACE_TAB_LABELS[4],
    "board": WORKSPACE_TAB_LABELS[5],
    "detail": WORKSPACE_TAB_LABELS[6],
    "config": WORKSPACE_TAB_LABELS[7],
}

DAILY_POOL_TABLE_HEADERS = [
    "状态",
    "标的 / 代码",
    "股票ID",
    "交易代码",
    "主线 / 位次",
    "位次",
    "角色",
    "窗口",
    "风险 / 总分",
    "策略归因",
    "热度",
    "级别",
    "总分",
    "龙头",
    "雷达",
    "打板",
    "低吸",
    "尾盘",
    "一日",
    "动作",
    "决策",
    "催化摘要",
    "日期",
    "价格 / 计划",
]

RECOMMEND_DEFAULT_STATUS_TEXT = "推荐台状态：等待机会池、计划与执行链路同步。"
RECOMMEND_DEFAULT_EMPTY_TITLE = "等待市场快照"
RECOMMEND_DEFAULT_EMPTY_HINT = "先载入样例数据，或直接重算机会池。"
RECOMMEND_DEFAULT_EMPTY_META = "刷新市场、导入样例或同步本地数据后，系统会生成今日综合机会池、送审优先级与执行链路。"
RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT = "载入完整示例"
RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT = "重算机会池"
RECOMMEND_DEFAULT_FOCUS_TEXT = "Desk Focus：等待前排候选、主线判断与执行状态同步。"
TRADE_PLAN_DEFAULT_FOCUS_TEXT = "计划焦点：等待生成今日交易计划"
ORDERS_DEFAULT_FOCUS_TEXT = "委托动作面板 / 委托焦点：等待选中委托建议"
BROKER_DEFAULT_STATUS_TEXT = "交易状态：先确认主线、趋势与消息，再进入委托确认。"


def workspace_name_for_index(index: int) -> str:
    if 0 <= index < len(WORKSPACE_TAB_ORDER):
        return WORKSPACE_LABEL_BY_KEY.get(WORKSPACE_TAB_ORDER[index], "未命名")
    return "未命名"


from .strategy_registry import get_strategy_filter_labels, get_strategy_score_fields, get_strategy_workbench_specs


OVERVIEW_QUICK_ROUTE_SPECS = {
    "市场总览": {"workspace": "overview", "widget": "intraday_chart_view"},
    "主线龙头": {"workspace": "recommend", "widget": "daily_pool_table", "select_row": "daily_pool_table"},
    "趋势机会": {"workspace": "recommend", "widget": "daily_pool_table", "select_row": "daily_pool_table"},
    "消息催化": {"workspace": "overview", "widget": "market_breadth_text"},
    "买卖决策": {"workspace": "recommend", "widget": "trade_plan_table", "select_row": "trade_plan_table"},
    "复盘研究": {"workspace": "recommend", "widget": "recommend_review_text"},
}

STRATEGY_FILTER_LABELS = get_strategy_filter_labels()

STRATEGY_SCORE_FIELDS = get_strategy_score_fields()

STRATEGY_WORKBENCH_SPECS = get_strategy_workbench_specs()
