from __future__ import annotations

THEME_OPTIONS = [
    ("graphite", "专业终端"),
    ("cerulean", "钛蓝终端"),
    ("ember", "琥珀终端"),
]

TERMINAL_DENSITY_OPTIONS = [
    ("standard", "标准"),
    ("compact", "紧凑"),
    ("watch", "盯盘"),
]

DEFAULT_TERMINAL_DENSITY = "compact"

TERMINAL_DENSITY_LABELS = {
    "standard": "标准",
    "compact": "紧凑",
    "watch": "盯盘",
}

TERMINAL_DENSITY_HINTS = {
    "standard": "标准密度：保留更完整的摘要、留白和说明，适合盘前研究与多面板对照。",
    "compact": "紧凑密度：压缩间距与表头，优先保证主链效率，适合日常盘中处理。",
    "watch": "盯盘密度：进一步收紧 Hero、表格和面板，优先保留焦点、主表与主动作。",
}

TERMINAL_LAYOUT_BREAKPOINTS = {
    "width": {
        "wide": 1680,
        "standard": 1440,
        "compact": 1280,
        "minimum": 1200,
    },
    "height": {
        "tall": 900,
        "standard": 820,
        "minimum": 760,
    },
}


def normalize_terminal_density(value: object) -> str:
    aliases = {
        "default": DEFAULT_TERMINAL_DENSITY,
        "balanced": "standard",
        "compact": "compact",
        "dense": "compact",
        "watch": "watch",
        "focus": "watch",
        "monitor": "watch",
        "scalp": "watch",
        "standard": "standard",
    }
    normalized = str(value or DEFAULT_TERMINAL_DENSITY).strip().lower()
    mapped = aliases.get(normalized, normalized)
    if mapped in TERMINAL_DENSITY_LABELS:
        return mapped
    return DEFAULT_TERMINAL_DENSITY


def terminal_density_label(key: object) -> str:
    normalized = normalize_terminal_density(key)
    return TERMINAL_DENSITY_LABELS.get(normalized, TERMINAL_DENSITY_LABELS[DEFAULT_TERMINAL_DENSITY])


def terminal_density_hint(key: object) -> str:
    normalized = normalize_terminal_density(key)
    return TERMINAL_DENSITY_HINTS.get(normalized, TERMINAL_DENSITY_HINTS[DEFAULT_TERMINAL_DENSITY])


def terminal_density_profile(density_key: object, *, width: int, height: int) -> dict[str, object]:
    normalized = normalize_terminal_density(density_key)
    width_value = max(int(width or 0), TERMINAL_LAYOUT_BREAKPOINTS["width"]["minimum"])
    height_value = max(int(height or 0), TERMINAL_LAYOUT_BREAKPOINTS["height"]["minimum"])

    if width_value >= TERMINAL_LAYOUT_BREAKPOINTS["width"]["wide"]:
        width_mode = "wide"
    elif width_value >= TERMINAL_LAYOUT_BREAKPOINTS["width"]["standard"]:
        width_mode = "standard"
    elif width_value >= TERMINAL_LAYOUT_BREAKPOINTS["width"]["compact"]:
        width_mode = "compact"
    else:
        width_mode = "critical"

    if height_value >= TERMINAL_LAYOUT_BREAKPOINTS["height"]["tall"]:
        height_mode = "tall"
    elif height_value >= TERMINAL_LAYOUT_BREAKPOINTS["height"]["standard"]:
        height_mode = "standard"
    else:
        height_mode = "short"

    manual_compact = normalized in {"compact", "watch"}
    manual_watch = normalized == "watch"
    compact_layout = manual_compact or width_mode in {"compact", "critical"} or height_mode == "short"
    watch_layout = manual_watch or width_mode == "critical" or (normalized == "compact" and height_mode == "short")
    shell_compact = normalized != "standard" or width_mode != "wide" or height_mode != "tall"

    if normalized == "standard":
        table_row_scale = 1.06
        table_header_scale = 1.04
        table_min_height_scale = 1.04
        table_breakpoint_shift = -120
        hero_min_height = 118
        hero_compact_min_height = 98
        badge_min_height = 48
        shell_header_min_height = 108
        shell_pulse_height = 50
        root_margin = 12
        panel_margin = 12
        panel_spacing = 10
    elif normalized == "watch":
        table_row_scale = 0.88
        table_header_scale = 0.92
        table_min_height_scale = 0.82
        table_breakpoint_shift = 140
        hero_min_height = 92
        hero_compact_min_height = 76
        badge_min_height = 40
        shell_header_min_height = 92
        shell_pulse_height = 42
        root_margin = 8
        panel_margin = 10
        panel_spacing = 8
    else:
        table_row_scale = 1.0
        table_header_scale = 1.0
        table_min_height_scale = 0.94
        table_breakpoint_shift = 0
        hero_min_height = 104
        hero_compact_min_height = 86
        badge_min_height = 44
        shell_header_min_height = 98
        shell_pulse_height = 46
        root_margin = 10
        panel_margin = 11
        panel_spacing = 9

    return {
        "mode": normalized,
        "label": terminal_density_label(normalized),
        "hint": terminal_density_hint(normalized),
        "width_mode": width_mode,
        "height_mode": height_mode,
        "manual_compact": manual_compact,
        "manual_watch": manual_watch,
        "compact_layout": compact_layout,
        "watch_layout": watch_layout,
        "shell_compact": shell_compact,
        "table_row_scale": table_row_scale,
        "table_header_scale": table_header_scale,
        "table_min_height_scale": table_min_height_scale,
        "table_breakpoint_shift": table_breakpoint_shift,
        "hero_min_height": hero_min_height,
        "hero_compact_min_height": hero_compact_min_height,
        "badge_min_height": badge_min_height,
        "shell_header_min_height": shell_header_min_height,
        "shell_pulse_height": shell_pulse_height,
        "root_margin": root_margin,
        "panel_margin": panel_margin,
        "panel_spacing": panel_spacing,
    }


TERMINAL_TABLE_VISIBILITY_STAGE_LIMITS = {
    "standard": 3,
    "compact": 2,
    "watch": 1,
    "ultra": 1,
}


def terminal_table_visibility_priority(
    spec: dict[str, object],
    *,
    column_count: int | None = None,
) -> dict[int, int]:
    explicit = spec.get("visibility_priority", {})
    priority_map: dict[int, int] = {}
    if isinstance(explicit, dict):
        for raw_column, raw_priority in explicit.items():
            try:
                column = int(raw_column)
                priority = int(raw_priority)
            except (TypeError, ValueError):
                continue
            if priority < 1:
                priority = 1
            priority_map[column] = min(priority, 3)

    compact_hidden = {int(column) for column in list(spec.get("compact_hidden", []) or [])}
    ultra_hidden = {int(column) for column in list(spec.get("ultra_compact_hidden", []) or [])}
    known_columns = set(priority_map)
    known_columns.update(compact_hidden)
    known_columns.update(ultra_hidden)
    for column in known_columns:
        if column in priority_map:
            continue
        if column in compact_hidden:
            priority_map[column] = 3
        elif column in ultra_hidden:
            priority_map[column] = 2
        else:
            priority_map[column] = 1

    if column_count is not None:
        for column in range(max(int(column_count), 0)):
            priority_map.setdefault(column, 1)
    return priority_map


def terminal_table_visibility_stage(
    spec: dict[str, object],
    *,
    available_width: int,
    density_mode: object,
) -> str:
    density_key = normalize_terminal_density(density_mode)
    compact_breakpoint = int(spec.get("compact_breakpoint", 0) or 0)
    ultra_compact_breakpoint = int(spec.get("ultra_compact_breakpoint", 0) or 0)
    width = max(int(available_width or 0), 0)

    if ultra_compact_breakpoint and width and width <= ultra_compact_breakpoint:
        return "ultra"
    if density_key == "watch":
        return "watch"
    if compact_breakpoint and width and width <= compact_breakpoint:
        return "compact"
    return "standard"


def terminal_table_hidden_columns(
    spec: dict[str, object],
    *,
    available_width: int,
    density_mode: object,
    column_count: int | None = None,
) -> tuple[str, set[int], dict[int, int]]:
    stage = terminal_table_visibility_stage(
        spec,
        available_width=available_width,
        density_mode=density_mode,
    )
    stage_limit = TERMINAL_TABLE_VISIBILITY_STAGE_LIMITS.get(stage, TERMINAL_TABLE_VISIBILITY_STAGE_LIMITS["standard"])
    hidden = {int(column) for column in list(spec.get("hidden", []) or [])}
    priority_map = terminal_table_visibility_priority(spec, column_count=column_count)
    for column, priority in priority_map.items():
        if priority > stage_limit:
            hidden.add(int(column))
    return stage, hidden, priority_map

WORKSPACE_TAB_ORDER = [
    "overview",
    "auth",
    "recommend",
    "broker",
    "paper",
    "scanner",
    "board",
    "detail",
    "config",
]

WORKSPACE_UI_SPECS = {
    "overview": {
        "tab": "全局态势",
        "hero_eyebrow": "全局态势",
        "hero_title": "市场总控台",
        "hero_subtitle": "主线、资金、消息与交易温度同屏初判。",
        "hero_badges": [("市场", "主线研判"), ("消息", "交易温度")],
        "shell_title": "量化猎手 Pro / 全局态势",
        "shell_subtitle": "结构 / 主线 / 温度",
        "shell_badge": "全局态势",
        "tab_tooltip": "看市场结构、主线、消息与整体交易温度。",
        "status_title": "全局态势",
        "status_caption": "看市场结构、主线、消息与交易温度。",
    },
    "auth": {
        "tab": "接入中心",
        "hero_eyebrow": "接入中心",
        "hero_title": "接入中控台",
        "hero_subtitle": "账户、通道、凭据与风控边界统一管理。",
        "hero_badges": [("东方财富", "默认通道"), ("人工复核", "最终闸门")],
        "shell_title": "量化猎手 Pro / 接入中心",
        "shell_subtitle": "账户 / 通道 / 状态",
        "shell_badge": "接入中心",
        "tab_tooltip": "维护账户、通道、凭据与接入状态。",
        "status_title": "接入中心",
        "status_caption": "管理账户、通道、凭据与接入状态。",
    },
    "recommend": {
        "tab": "机会池",
        "hero_eyebrow": "机会池",
        "hero_title": "机会池与计划台",
        "hero_subtitle": "先定焦点，再过门槛，再送审。",
        "hero_badges": [("焦点", "当前主票"), ("计划", "送审准备")],
        "shell_title": "量化猎手 Pro / 机会池",
        "shell_subtitle": "焦点 / 门槛 / 送审",
        "shell_badge": "机会池",
        "tab_tooltip": "从候选焦点推进到计划与执行审查。",
        "status_title": "机会池",
        "status_caption": "推进候选排序、计划生成与执行审查。",
    },
    "broker": {
        "tab": "执行中控",
        "hero_eyebrow": "执行中控",
        "hero_title": "执行中控台",
        "hero_subtitle": "先复核，再提交，再看回执。",
        "hero_badges": [("人工复核", "提交模式"), ("风险优先", "执行顺序")],
        "shell_title": "量化猎手 Pro / 执行中控",
        "shell_subtitle": "复核 / 提交 / 回执",
        "shell_badge": "执行中控",
        "tab_tooltip": "完成委托审查、提交确认与回执跟踪。",
        "status_title": "执行中控",
        "status_caption": "完成委托审查、提交确认与回执跟踪。",
    },
    "paper": {
        "tab": "实验台",
        "hero_eyebrow": "策略实验",
        "hero_title": "策略实验台",
        "hero_subtitle": "模拟盘样本、主测对照与实验复盘在独立视图处理。",
        "hero_badges": [("样本", "主测 / 对照"), ("模拟盘", "运行状态")],
        "shell_title": "量化猎手 Pro / 实验台",
        "shell_subtitle": "主测 / 对照 / 复盘",
        "shell_badge": "实验台",
        "tab_tooltip": "看模拟盘样本、主测对照与实验复盘。",
        "status_title": "实验台",
        "status_caption": "看模拟盘样本、主测对照与实验复盘。",
    },
    "scanner": {
        "tab": "信号扫描",
        "hero_eyebrow": "信号扫描",
        "hero_title": "信号扫描与监控台",
        "hero_subtitle": "扫描、观察池与盘中监控在同一链路内联动。",
        "hero_badges": [("扫描", "盘中联动"), ("观察", "监控入口")],
        "shell_title": "量化猎手 Pro / 信号扫描",
        "shell_subtitle": "扫描 / 观察 / 监控",
        "shell_badge": "信号扫描",
        "tab_tooltip": "管理扫描结果、观察池和盘中焦点。",
        "status_title": "信号扫描",
        "status_caption": "筛盘中焦点、观察池与监控入口。",
    },
    "board": {
        "tab": "涨停策略",
        "hero_eyebrow": "涨停策略",
        "hero_title": "涨停策略专项台",
        "hero_subtitle": "聚焦前排强势股、回封质量与执行准备。",
        "hero_badges": [("前排", "核心候选"), ("回封", "执行准备")],
        "shell_title": "量化猎手 Pro / 涨停策略",
        "shell_subtitle": "候选 / 回封 / 准备",
        "shell_badge": "涨停策略",
        "tab_tooltip": "跟踪强势候选、回封质量与专项观察。",
        "status_title": "涨停策略",
        "status_caption": "跟踪前排候选、回封质量与专项观察。",
    },
    "detail": {
        "tab": "单票复盘",
        "hero_eyebrow": "单票复盘",
        "hero_title": "单票复盘与决策台",
        "hero_subtitle": "单票画像、交易依据、执行轨迹与复盘结论集中呈现。",
        "hero_badges": [("单票", "决策视图"), ("轨迹", "执行回放")],
        "shell_title": "量化猎手 Pro / 单票复盘",
        "shell_subtitle": "证据 / 轨迹 / 结论",
        "shell_badge": "单票复盘",
        "tab_tooltip": "看单票画像、执行回放与复盘结论。",
        "status_title": "单票复盘",
        "status_caption": "看单票画像、执行回放与复盘结论。",
    },
    "config": {
        "tab": "策略配置",
        "hero_eyebrow": "策略配置",
        "hero_title": "策略与风控配置台",
        "hero_subtitle": "管理策略参数、风险档位、消息源与 AI 评测边界。",
        "hero_badges": [("风险", "当前档位"), ("授权", "当前计划")],
        "shell_title": "量化猎手 Pro / 策略配置",
        "shell_subtitle": "参数 / 风险 / 边界",
        "shell_badge": "策略配置",
        "tab_tooltip": "维护参数、风险档位与运行边界。",
        "status_title": "策略配置",
        "status_caption": "维护策略参数、风险档位与运行边界。",
    },
}

WORKSPACE_STAGE_SUMMARY_SPECS = {
    "recommend": [
        {
            "title": "机会总览",
            "subtitle": "先完成候选排序、焦点确认与基础筛选，再决定是否进入执行审查。",
            "badges": [
                ("看什么", "焦点票 / 候选层级"),
                ("本页动作", "定焦点 / 过门槛"),
                ("下一步", "进入执行审查"),
            ],
        },
        {
            "title": "执行审查",
            "subtitle": "把焦点票送入分发、复核与送审队列，确认是否具备可执行条件。",
            "badges": [
                ("看什么", "分发 / 复核 / 队列"),
                ("本页动作", "确认可执行委托"),
                ("下一步", "进入深度洞察"),
            ],
        },
        {
            "title": "深度洞察",
            "subtitle": "汇总主线、战法、计划与消息，形成最终判断并决定是否推送执行。",
            "badges": [
                ("看什么", "主线 / 计划 / 消息"),
                ("本页动作", "形成计划 / 风险说明"),
                ("下一步", "推送执行中控"),
            ],
        },
    ],
    "broker": [
        {
            "title": "执行总览",
            "subtitle": "先看执行阶段、主线闸门与关键风险，再判断是否进入委托提交。",
            "badges": [
                ("看什么", "阶段 / 闸门 / 风险"),
                ("本页动作", "确认执行条件"),
                ("下一步", "进入委托提交"),
            ],
        },
        {
            "title": "委托提交",
            "subtitle": "集中处理持仓、计划、委托队列和提交确认，保证动作与风控一致。",
            "badges": [
                ("看什么", "持仓 / 队列 / 当前委托"),
                ("本页动作", "确认并提交"),
                ("下一步", "进入回执复盘"),
            ],
        },
        {
            "title": "回执复盘",
            "subtitle": "跟踪成交回执、偏差和复盘动作，确认执行质量与异常原因。",
            "badges": [
                ("看什么", "回执 / 偏差 / 复盘"),
                ("本页动作", "核对结果 / 导出回放"),
                ("下一步", "回看执行总览"),
            ],
        },
        {
            "title": "接入维护",
            "subtitle": "统一处理账户接入、运行维护和环境诊断，保证执行链路可用。",
            "badges": [
                ("看什么", "账户 / 诊断 / 日志"),
                ("本页动作", "校验连接 / 清理缓存"),
                ("下一步", "进入委托提交"),
            ],
        },
    ],
    "paper": [
        {
            "title": "实验总览",
            "subtitle": "先确认模拟盘状态、实验边界和当前权益，再决定是否启动新一轮主测。",
            "badges": [
                ("看什么", "状态 / 权益 / 实验边界"),
                ("本页动作", "初始化 / 执行一轮"),
                ("下一步", "进入持仓与交割"),
            ],
        },
        {
            "title": "持仓与交割",
            "subtitle": "集中看模拟持仓、交割单和当前样本动作，核对实验结果是否真实可追踪。",
            "badges": [
                ("看什么", "持仓 / 交割 / 样本动作"),
                ("本页动作", "核对实验结果"),
                ("下一步", "进入战法与巡航"),
            ],
        },
        {
            "title": "战法与巡航",
            "subtitle": "看战法收益拆解、巡航日志和实验洞察，判断主测与对照是否具备继续价值。",
            "badges": [
                ("看什么", "战法 / 巡航 / 洞察"),
                ("本页动作", "评估主测与对照"),
                ("下一步", "看实验总览"),
            ],
        },
    ],
    "scanner": [
        {
            "title": "扫描榜",
            "subtitle": "先筛盘中信号和候选强度，形成观察池与复盘入口。",
            "badges": [
                ("看什么", "信号榜 / 最新强弱"),
                ("本页动作", "筛出观察对象"),
                ("下一步", "进入观察池"),
            ],
        },
        {
            "title": "观察池",
            "subtitle": "把候选放进观察池，对照摘要和历史表现，确认是否继续跟踪。",
            "badges": [
                ("看什么", "观察池 / 回测摘要"),
                ("本页动作", "保留 / 剔除候选"),
                ("下一步", "进入盘中监控"),
            ],
        },
        {
            "title": "盘中监控",
            "subtitle": "盯住盘中变化、跳转动作和实时监控，把扫描结果接回执行链路。",
            "badges": [
                ("看什么", "监控 / 跳转动作"),
                ("本页动作", "追踪盘中变化"),
                ("下一步", "跳转机会池或复盘"),
            ],
        },
    ],
    "board": [
        {
            "title": "候选总览",
            "subtitle": "先看涨停候选、触发方式和计划买点，确认是否进入专项监控。",
            "badges": [
                ("看什么", "候选 / 触发 / 风险"),
                ("本页动作", "筛专项候选"),
                ("下一步", "进入回封监控"),
            ],
        },
        {
            "title": "回封监控",
            "subtitle": "盯回封概率、炸板风险和动作建议，把专项候选接回执行链路。",
            "badges": [
                ("看什么", "回封 / 风险 / 动作"),
                ("本页动作", "跟踪盘中变化"),
                ("下一步", "看候选总览"),
            ],
        },
    ],
    "detail": [
        {
            "title": "单票总览",
            "subtitle": "先看单票结论、交易依据和执行轨迹，形成本次复盘的主判断。",
            "badges": [
                ("看什么", "结论 / 依据 / 轨迹"),
                ("本页动作", "判断是否继续跟踪"),
                ("下一步", "进入信号与交易"),
            ],
        },
        {
            "title": "信号与交易",
            "subtitle": "对照信号时间线和真实成交，验证动作是否与预案一致。",
            "badges": [
                ("看什么", "信号 / 成交 / 时间线"),
                ("本页动作", "核对动作一致性"),
                ("下一步", "进入历史战法"),
            ],
        },
        {
            "title": "历史战法",
            "subtitle": "用历史战法统计和参数对比判断策略是否具备可复制性。",
            "badges": [
                ("看什么", "战法统计 / 参数对比"),
                ("本页动作", "验证可复制性"),
                ("下一步", "看单票总览"),
            ],
        },
    ],
    "config": [
        {
            "title": "参数与风险",
            "subtitle": "维护风险档位、授权计划和核心参数，先定边界再谈动作。",
            "badges": [
                ("看什么", "参数 / 风险 / 授权"),
                ("本页动作", "确认运行边界"),
                ("下一步", "进入战法配置"),
            ],
        },
        {
            "title": "战法配置",
            "subtitle": "管理战法目录、表单参数和脚本配置，保证执行逻辑与参数一致。",
            "badges": [
                ("看什么", "战法目录 / 参数 / 脚本"),
                ("本页动作", "维护战法配置"),
                ("下一步", "进入消息与AI"),
            ],
        },
        {
            "title": "消息与AI",
            "subtitle": "统一管理消息源、AI 评测和信息边界，控制外部信息输入质量。",
            "badges": [
                ("看什么", "消息源 / AI 评测"),
                ("本页动作", "校准信息边界"),
                ("下一步", "进入说明"),
            ],
        },
        {
            "title": "说明",
            "subtitle": "说明当前配置的影响范围、依赖关系和使用方式，方便复核与交接。",
            "badges": [
                ("看什么", "影响范围 / 依赖"),
                ("本页动作", "确认说明一致"),
                ("下一步", "看参数与风险"),
            ],
        },
    ],
}

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

WORKSPACE_TAB_LABELS = [WORKSPACE_UI_SPECS[key]["tab"] for key in WORKSPACE_TAB_ORDER]

WORKSPACE_LABEL_BY_KEY = {
    key: str(WORKSPACE_UI_SPECS.get(key, {}).get("tab", "工作区"))
    for key in WORKSPACE_TAB_ORDER
}

WORKSPACE_KEY_ALIASES = {
    "全局态势": "overview",
    "市场总览": "overview",
    "市场机会工作台": "overview",
    "总览": "overview",
    "接入中心": "auth",
    "统一登录": "auth",
    "登录": "auth",
    "机会池": "recommend",
    "每日推荐": "recommend",
    "推荐": "recommend",
    "执行中控": "broker",
    "交易执行": "broker",
    "交易": "broker",
    "实验台": "paper",
    "策略实验": "paper",
    "实验": "paper",
    "AI模拟盘": "paper",
    "信号扫描": "scanner",
    "策略扫描": "scanner",
    "扫描": "scanner",
    "涨停策略": "board",
    "打板专项": "board",
    "打板": "board",
    "单票复盘": "detail",
    "明细复盘": "detail",
    "明细": "detail",
    "策略配置": "config",
    "参数配置": "config",
    "配置": "config",
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

RECOMMEND_DEFAULT_STATUS_TEXT = "推荐状态：待生成 | 机会池与计划待同步 | 当前结论：继续复核 | 下一步：先重算机会池。"
SCANNER_DEFAULT_STATUS_TEXT = "扫描状态：待扫描 | 观察池与监控待建立 | 当前结论：继续复核 | 下一步：执行首轮扫描。"
OVERVIEW_DEFAULT_STATUS_TEXT = "总览状态：待建快照 | 主线温度待同步 | 当前结论：继续复核 | 下一步：刷新市场。"
RECOMMEND_DEFAULT_EMPTY_TITLE = "等待市场快照"
RECOMMEND_DEFAULT_EMPTY_HINT = "先载入样例数据，或直接重算机会池。"
RECOMMEND_DEFAULT_EMPTY_META = "刷新市场、导入样例或同步本地数据后，系统会生成今日综合机会池、送审优先级与执行链路。"
RECOMMEND_EMPTY_SAMPLE_BUTTON_TEXT = "载入样例"
RECOMMEND_EMPTY_REFRESH_BUTTON_TEXT = "重算机会"
RECOMMEND_DEFAULT_FOCUS_TEXT = "机会焦点：待同步 | 前排候选与主线待确认 | 当前结论：继续复核 | 下一步：先锁定今日焦点票。"
TRADE_PLAN_DEFAULT_FOCUS_TEXT = "计划焦点：待生成 | 今日计划尚未建立 | 当前结论：继续复核 | 下一步：先重算交易计划。"
ORDERS_DEFAULT_FOCUS_TEXT = "委托焦点：待选择 | 当前结论 继续复核 | 下一步：先生成并复核委托。"
BROKER_DEFAULT_STATUS_TEXT = "交易状态：继续复核 | 主线与闸门待确认 | 下一步：生成并复核委托。"

WORKBENCH_BANNER_SPECS = {
    "broker": {
        "seed": "执行中控：先锁定焦点委托，再进入确认弹窗，最后盯回执。",
        "empty": "执行中控：先从机会池生成委托链路，再进入提交确认和执行回看。",
        "queue": "执行中控：待提 {order_count} 笔，优先核对最前一笔的闸门、价格和仓位。",
        "submitted": "执行中控：已回写 {submit_count} 条回执，优先盯最新一笔的成交、失败原因和偏差。",
        "focus": "执行中控：当前联动 {stock_name}，下一步核对账户、价格、止损与仓位。{suffix}",
        "record": "执行中控：正在回看 {stock_name} 的执行反馈，继续核对成交、失败原因和偏差。",
    },
    "recommend": {
        "seed": "机会池：先锁定前排，再过门槛，再推执行。",
        "empty": "机会池：先刷新市场和机会池，再从前排候选里锁定今天最值得推进的一只。",
        "focus": "机会池：当前联动 {stock_name}，先复核价位、风险和主线，再决定是否送审。",
        "buy_focus": "机会池：当前联动 {stock_name}，属于可执行候选，下一步优先核对买点、止损和主线延续。",
        "action_focus": "机会池：当前联动 {stock_name}，动作偏向{action_text}，先确认主线状态再决定是否推进。",
    },
    "detail": {
        "seed": "单票复盘：先看决策依据，再回看执行偏差，最后沉淀结论。",
        "empty": "单票复盘：先从机会池、执行中控或信号扫描联动一只票，再展开完整复盘链路。",
        "focus": "单票复盘：当前联动 {stock_name}，继续核对决策依据、执行偏差和下一次识别点。",
    },
    "scanner": {
        "seed": "信号扫描：先看扫描信号，再接观察池和盘中监控。",
        "empty": "信号扫描：先执行扫描或载入样本，再从观察池锁定一只盘中焦点。",
        "queue": "信号扫描：已生成 {scan_count} 条信号，下一步优先从观察池 {watch_count} 只里锁定焦点票。",
        "focus": "信号扫描：当前联动 {stock_name}，继续核对扫描信号、观察池状态和盘中监控联动。",
    },
    "board": {
        "seed": "涨停策略：先看强势候选，再盯回封与炸板风险。",
        "empty": "涨停策略：先从信号扫描或机会池联动强势候选，再看回封观察和风险灯。",
        "queue": "涨停策略：当前有 {candidate_count} 只候选、{monitor_count} 条监控，优先看最强回封和高风险炸板票。",
        "focus": "涨停策略：当前联动 {stock_name}，继续核对触发方式、回封强度、炸板风险和是否值得送审。",
    },
}

WORKBENCH_EMPTY_PANEL_COPY = {
    "runtime_log_text": "\n".join(
        [
            "运行日志",
            "",
            "当前状态：待写入 | 刷新、联动、委托与导出尚未发生。",
            "范围：市场刷新、机会池重算、委托生成、提交回执与跨页联动都会落在这里。",
            "下一步：",
            "1. 先刷新市场或机会池，建立今天的前排焦点。",
            "2. 再去交易生成委托，盯最新回执。",
            "3. 收盘后去复盘页，沉淀执行偏差与结论。",
        ]
    ),
    "paper_experiment_text": "\n".join(
        [
            "实验记录",
            "",
            "状态：待初始化 | 首轮主测结果尚未写入。",
            "范围：策略轮动、仓位变化、失败样本和可复用经验都会沉淀在这里。",
            "下一步：",
            "- 先初始化模拟盘，再运行一轮 AI 主测。",
            "- 导出报告后，把收益和回撤回接到机会池与交易链路校验。",
        ]
    ),
    "recommend_decision_summary_text": "\n".join(
        [
            "单票决策摘要",
            "",
            "状态：待锁定焦点 | 当前还没有主票进入决策链。",
            "看什么：主线、价位、风险和是否值得送审。",
            "下一步：",
            "1. 先刷新市场，生成机会池。",
            "2. 再从前排候选里锁定一只票。",
            "3. 确认逻辑成立后，再推进送审与交易。",
        ]
    ),
    "metrics_text": "\n".join(
        [
            "策略摘要",
            "",
            "状态：待同步焦点 | 当前还没有单票进入复盘链。",
            "看什么：收益、回撤、胜率、阶段统计和近期信号。",
            "下一步：",
            "1. 先从机会池或执行中控联动一只焦点票。",
            "2. 再看题材位置、信号质量和最近执行。",
        ]
    ),
    "detail_decision_text": "\n".join(
        [
            "交易决策画像",
            "",
            "状态：待同步焦点 | 当前还没有单票进入决策回看。",
            "看什么：主线地位、动作建议、计划价位和核心逻辑。",
            "下一步：先选中一只股票，再判断这笔交易当时该不该做。",
        ]
    ),
    "detail_execution_text": "\n".join(
        [
            "执行状态回放",
            "",
            "当前结论：继续复核 | 委托、提交或回执尚未联动。",
            "看什么：送审、委托、提交、成交和失败记录。",
            "下一步：先从执行中控选中一笔委托或回执，再回来定位执行偏差。",
        ]
    ),
    "detail_conclusion_text": "\n".join(
        [
            "复盘结论",
            "",
            "当前结论：待复盘 | 本次单票复盘尚未落结论。",
            "看什么：最值得留下来的结论、纪律得失和下一次观察点。",
            "下一步：选中焦点股票后，再回看今天做对了什么、错过了什么。",
        ]
    ),
    "monitor_summary_text": "\n".join(
        [
            "盘中监控摘要",
            "",
            "状态：待联动 | 当前结论：继续复核 | 首轮扫描与观察池尚未建立。",
            "看什么：扫描信号、观察池状态和盘中催化。",
            "下一步：",
            "1. 先执行扫描，或载入样本数据建立首轮股票池。",
            "2. 再从观察池里锁定一只焦点票，看信号、催化和推荐联动。",
            "3. 若出现强势候选，再联动到涨停策略或执行中控。",
        ]
    ),
    "board_text": "\n".join(
        [
            "打板候选池",
            "",
            "状态：待锁定焦点 | 当前结论：继续复核 | 候选表尚未同步专项焦点。",
            "看什么：触发方式、板位强度、计划买点、止损和目标价。",
            "下一步：",
            "1. 先从左侧候选表、扫描页或机会池里锁定一只强势票。",
            "2. 再核对回封质量、主线位置和计划价格是否还成立。",
            "3. 若逻辑仍成立，再联动到交易或机会池继续推进。",
        ]
    ),
    "board_monitor_text": "\n".join(
        [
            "回封监控",
            "",
            "状态：待锁定焦点 | 当前结论：继续复核 | 候选表或监控表尚未同步专项焦点。",
            "看什么：触发方式、回封概率、炸板风险和动作建议。",
            "下一步：",
            "1. 先从左侧候选或监控表里锁定一只强势票。",
            "2. 再核对触发方式、回封概率、炸板风险和动作建议。",
            "3. 若逻辑成立，再联动到机会池或执行中控推进。",
        ]
    ),
    "recommend_core_bucket_text": (
        "主线前排执行桶\n\n"
        "状态：前排候选待确认。\n"
        "看什么：主线地位、量能承接、催化强化和计划仓位。\n"
        "下一步：有前排机会时先重算计划，没有的话回综合机会池继续筛。"
    ),
    "recommend_watch_bucket_text": (
        "观察池\n\n"
        "状态：观察候选待确认。\n"
        "看什么：分时承接、主线强度、消息兑现和是否重新回前排。\n"
        "下一步：转强就进前排执行桶；逻辑失效就转风险池。"
    ),
    "recommend_risk_bucket_text": (
        "风险池\n\n"
        "状态：风险候选待处理。\n"
        "看什么：主线切换、跌破防守位、量价背离和消息落空。\n"
        "下一步：先处理风险，再决定是否回看机会池补新候选。"
    ),
    "broker_mainline_review_text": (
        "主线闸门 / 为什么\n\n"
        "状态：闸门待复核。\n"
        "看什么：题材位置、主线角色、风险灯和计划仓位是否匹配。\n"
        "下一步：主线成立再确认提交；主线不成立就回机会池重看。"
    ),
    "broker_execution_text": (
        "最近执行\n\n"
        "状态：执行链待回写。\n"
        "看什么：订单状态、成交状态、失败原因和是否偏离计划价格。\n"
        "下一步：未提交先复核；已提交继续跟踪回执和偏差。"
    ),
    "broker_recap_text": (
        "成交回顾\n\n"
        "状态：回顾结论待沉淀。\n"
        "看什么：失败原因、滑点、仓位偏差和是否需要重新送审。\n"
        "下一步：执行合格就继续跟踪；执行失真就回头修正机会池和委托参数。"
    ),
    "order_result_text": (
        "执行回放\n\n"
        "状态：回执时间线待写入。\n"
        "看什么：最新订单状态、成交状态和系统反馈。\n"
        "下一步：提交后这里会自动滚动到最新记录，便于盘中快速复核。"
    ),
}


def workspace_name_for_index(index: int) -> str:
    if 0 <= index < len(WORKSPACE_TAB_ORDER):
        return WORKSPACE_LABEL_BY_KEY.get(WORKSPACE_TAB_ORDER[index], "未命名")
    return "未命名"


def workbench_banner_copy(workspace: str, key: str = "seed", **kwargs) -> str:
    spec = WORKBENCH_BANNER_SPECS.get(workspace, {})
    template = str(spec.get(key, spec.get("seed", "")) or "")
    if not template:
        return ""
    try:
        return template.format(**kwargs)
    except Exception:
        return template


def workbench_empty_panel_copy(panel_name: str, fallback: str = "") -> str:
    return str(WORKBENCH_EMPTY_PANEL_COPY.get(panel_name, fallback) or fallback)


RECOMMEND_TERMINAL_CTA_BASE_TOOLTIPS = {
    "push": "把当前焦点送入送审链路，先过主线、价位和风险闸门。",
    "detail": "跳到复盘页，继续看信号、执行回放、失效条件和近期消息。",
    "broker": "跳到执行中控，继续看这只票的计划、委托和回执链路。",
}


def recommend_terminal_cta_labels(
    *,
    can_submit: bool,
    can_open_broker: bool,
    execution_state: str,
) -> dict[str, str]:
    state = str(execution_state or "")
    push_label = "暂缓送审"
    broker_label = "暂缓进交易"
    if state == "已提交":
        push_label = "看已提"
        broker_label = "看回执"
    elif state == "已送审":
        push_label = "看送审"
        broker_label = "看交易"
    elif state == "提交失败":
        push_label = "复核后重送"
        broker_label = "看失败链路" if can_open_broker else "先看复盘"
    else:
        if can_submit:
            push_label = "送审"
        if can_open_broker:
            broker_label = "进交易"
    return {
        "push": push_label,
        "detail": "看复盘",
        "broker": broker_label,
    }


def recommend_focus_action_tooltip(key: str, fallback: str = "") -> str:
    return str(RECOMMEND_TERMINAL_CTA_BASE_TOOLTIPS.get(str(key or "").strip(), fallback) or fallback)


def broker_terminal_primary_cta_labels(
    *,
    stage: str,
    order_count: int,
    submit_count: int,
    has_focus_symbol: bool,
) -> dict[str, str]:
    stage = str(stage or "")
    order_count = max(int(order_count or 0), 0)
    submit_count = max(int(submit_count or 0), 0)
    if order_count <= 0:
        return {
            "generate_text": "生成委托" if not has_focus_symbol else "生成焦点委托",
            "confirm_text": "确认提交",
        }
    if stage == "阻塞待处理":
        return {
            "generate_text": "按阻塞重算",
            "confirm_text": f"修正后提交 ({order_count})",
        }
    if submit_count > 0:
        return {
            "generate_text": "围绕焦点重算",
            "confirm_text": f"复核后提交 ({order_count})",
        }
    return {
        "generate_text": "重算委托",
        "confirm_text": f"复核后提交 ({order_count})",
    }


def broker_terminal_primary_cta_tooltips(
    *,
    stage: str,
    order_count: int,
    submit_count: int,
    stock_name: str,
) -> dict[str, str]:
    stage = str(stage or "")
    order_count = max(int(order_count or 0), 0)
    submit_count = max(int(submit_count or 0), 0)
    stock_name = str(stock_name or "当前焦点")
    if order_count <= 0:
        return {
            "generate_tooltip": (
                f"围绕 {stock_name} 建立第一批委托链路。"
                if stock_name != "当前焦点"
                else "从机会池或交易计划生成第一批委托链路。"
            ),
            "confirm_tooltip": "请先从机会池生成委托链路。",
        }
    if stage == "阻塞待处理":
        return {
            "generate_tooltip": f"围绕 {stock_name} 按最新阻塞项重算委托链路。",
            "confirm_tooltip": "请先修正阻塞项，再进入确认弹窗提交。",
        }
    if submit_count > 0:
        return {
            "generate_tooltip": f"围绕 {stock_name} 重新生成委托链路，补齐新的执行方案。",
            "confirm_tooltip": "当前仍有待提交委托，可再次复核后提交。",
        }
    return {
        "generate_tooltip": f"围绕 {stock_name} 重新计算委托链路。",
        "confirm_tooltip": "已生成委托建议，可以进入确认弹窗并提交。",
    }


def broker_terminal_focus_button_copy(
    kind: str,
    *,
    order_count: int = 0,
    submit_count: int = 0,
    stock_name: str = "",
) -> tuple[str, str]:
    button_kind = str(kind or "").strip()
    orders = max(int(order_count or 0), 0)
    submissions = max(int(submit_count or 0), 0)
    focus_name = str(stock_name or "").strip()
    if button_kind == "blocker":
        return (
            "定位阻塞项",
            "优先定位需要处理的阻塞回执。"
            if submissions
            else ("优先查看当前委托链路里的阻塞项。" if orders else "当前没有阻塞项，可先生成委托链路。"),
        )
    return (
        "定位优先委托",
        f"优先定位当前执行焦点：{focus_name}。"
        if focus_name
        else ("优先定位当前最值得继续跟进的委托。" if orders else "当前没有优先委托，可先生成委托链路。"),
    )


ACTION_ROW_COMPACT_LABELS = {
    "去看推荐": "看机会",
    "查看推荐": "看机会",
    "查看推荐池": "看机会",
    "查看机会池": "看机会",
    "打开推荐池": "看机会",
    "资金看推荐": "看机会",
    "决策看推荐": "看机会",
    "候选看推荐": "看机会",
    "监控看推荐": "看机会",
    "闸门看推荐": "看机会",
    "执行看推荐": "看机会",
    "复盘看机会池": "看机会",
    "决策看机会池": "看机会",
    "结论看机会池": "看机会",
    "去看交易": "去交易",
    "去交易页": "去交易",
    "前往交易执行": "去交易",
    "计划去交易": "去交易",
    "持仓去交易": "去交易",
    "候选去交易": "去交易",
    "执行去交易": "去交易",
    "结论去交易": "去交易",
    "看观察池": "看观察",
    "查看观察池": "看观察",
    "计划看观察池": "看观察",
    "看消息催化": "看消息",
    "查看消息催化": "看消息",
    "打开消息线索": "看消息",
    "脉搏看消息": "看消息",
    "回到总览": "看总览",
    "看总览": "看总览",
    "回到市场总览": "看总览",
    "资金回总览": "看总览",
    "机会池看总览": "看总览",
    "脉搏回总览": "看总览",
    "候选看总览": "看总览",
    "监控看总览": "看总览",
    "复盘回总览": "看总览",
    "定位推荐池": "定位机会",
    "定位机会池": "定位机会",
    "重算交易计划": "重算计划",
    "查看风险池": "看风险",
    "持仓看风险池": "看风险",
    "刷新专项监控": "刷新监控",
    "定位委托": "定位委托",
    "闸门定位委托": "定位委托",
    "查看委托": "看委托",
    "执行看委托": "看委托",
    "回执看委托": "看委托",
    "查看成交": "看成交",
    "执行看成交": "看成交",
    "回执看成交": "看成交",
    "看当前回执": "看当前",
    "回看上一条": "看上一条",
    "查看复盘": "看复盘",
    "查看复盘研究": "看复盘",
    "执行看复盘": "看复盘",
    "查看扫描": "看扫描",
    "决策看扫描": "看扫描",
    "指标看扫描": "看扫描",
    "执行看扫描": "看扫描",
    "候选看扫描": "看扫描",
    "监控看扫描": "看扫描",
    "前往配置页": "去配置",
    "前往登录配置": "去登录",
    "前往推荐池": "去推荐",
}


ACTION_ROW_TOOLTIP_COPY = {
    "看机会": "跳转到机会池，继续看高优先池、趋势机会和综合评分。",
    "看消息": "切到消息催化视图，看新闻、主题驱动和异动线索。",
    "看总览": "跳到总览，继续看市场结构、主线和趋势全景。",
    "去交易": "跳转到执行中控，看委托建议、执行回放和提交入口。",
    "定位机会": "把焦点定位到机会池表格，方便继续筛选和对比。",
    "重算计划": "重新生成今日交易计划、仓位预算和盘中节奏。",
    "看观察": "跳到观察池，看仍在等待确认的标的。",
    "看风险": "看高风险、减仓和退出建议。",
    "刷新监控": "刷新专项监控与回封观察焦点。",
    "定位委托": "定位到委托建议列表，优先检查待提交订单。",
    "看委托": "看委托表格和当前执行建议。",
    "看成交": "看提交记录、执行结果和成交回放。",
    "看当前": "定位到当前回执，并同步当前节点主控卡。",
    "看上一条": "回看上一条回执，快速做前后对照。",
    "处置异常": "优先定位异常回执，没有异常时退回阻塞入口。",
    "刷新诊断": "刷新运行日志、任务状态和诊断面板。",
    "导出日志": "导出当前运行日志，便于排查问题。",
    "看复盘": "跳到复盘，看单票信号、成交与复盘结论。",
    "看扫描": "跳到信号扫描，继续看盘中监控和观察池联动。",
    "去配置": "跳转到配置页，调整参数、模板和授权设置。",
    "去登录": "跳转到接入中心，检查账户与接入配置。",
    "去推荐": "跳转到机会池，继续看候选节奏与执行准备。",
}


CONTEXTUAL_ENTRY_RENAME_TARGETS = {
    "overview_tab": {
        "全部": ["主线全部", "资金全部"],
        "去看推荐": ["资金看推荐", "决策看推荐"],
        "回到最新": ["主线回最新", "资金回最新"],
        "查看机会池": ["资金看机会池", "决策看机会池"],
    },
    "scanner_tab": {
        "查看打板": ["工具看打板", "面板看打板"],
        "查看推荐": ["工具看推荐", "面板看推荐"],
    },
    "recommend_tab": {
        "前往交易执行": ["计划去交易", "持仓去交易"],
        "重算计划": ["轻量重算计划"],
    },
    "broker_tab": {
        "刷新诊断": ["工具刷新诊断", "日志刷新诊断"],
        "导出日志": ["工具导出日志", "日志导出日志"],
        "查看机会池": ["闸门看机会池", "执行看机会池"],
    },
    "board_tab": {
        "查看机会池": ["候选看机会池", "监控看机会池"],
    },
    "detail_tab": {
        "回到市场总览": ["指标回总览", "决策回总览"],
        "查看扫描": ["指标看扫描", "执行看扫描"],
    },
}


CONTEXTUAL_ENTRY_TOOLTIP_SUFFIX = {
    "资金": "以资金与轮动视角继续联动。",
    "决策": "以决策推演视角继续联动。",
    "主线": "以主线强弱视角继续联动。",
    "执行": "以执行中控视角继续联动。",
    "指标": "以复盘指标视角继续联动。",
    "闸门": "以闸门审查视角继续联动。",
    "监控": "以盘中监控视角继续联动。",
    "候选": "以涨停策略候选视角继续联动。",
    "持仓": "以持仓处理视角继续联动。",
    "计划": "以交易计划视角继续联动。",
    "脉搏": "以市场脉搏视角继续联动。",
    "日志": "以日志与回放视角继续联动。",
    "工具": "从工具入口继续联动。",
    "面板": "从内容面板继续联动。",
    "工作台": "从当前工作台继续联动。",
}


CONTEXTUAL_ROUTE_BUTTON_RULES = {
    "资金看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先刷新机会池，或先选中一只焦点股票。",
        "enabled": "从资金视角跳到机会池继续联动。",
    },
    "决策看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先刷新机会池，或先选中一只焦点股票。",
        "enabled": "从决策视角跳到机会池继续联动。",
    },
    "工具看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先扫描或刷新机会池，形成可跟踪焦点。",
        "enabled": "从工具栏带着焦点跳到机会池。",
    },
    "面板看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先扫描或刷新机会池，形成可跟踪焦点。",
        "enabled": "从内容面板带着焦点跳到机会池。",
    },
    "候选看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先生成打板候选，或先选中一只焦点股票。",
        "enabled": "把打板候选同步到机会池。",
    },
    "监控看推荐": {
        "condition": "focus_or_pool",
        "disabled": "先生成盘中监控焦点，再去机会池联动。",
        "enabled": "把监控焦点同步到机会池。",
    },
    "计划去交易": {
        "condition": "decisions_or_orders",
        "disabled": "需要先生成交易计划或委托建议。",
        "enabled": "带着计划上下文跳到执行中控。",
    },
    "持仓去交易": {
        "condition": "focus_or_orders",
        "disabled": "先从机会池选中持仓处理对象，或先生成委托建议。",
        "enabled": "带着持仓处理上下文跳到执行中控。",
    },
    "执行去交易": {
        "condition": "focus_or_orders",
        "disabled": "先选中一只股票，或先生成委托建议。",
        "enabled": "从执行画像跳到执行中控。",
    },
    "结论去交易": {
        "condition": "focus_or_orders",
        "disabled": "先选中一只股票，或先生成委托建议。",
        "enabled": "从复盘结论跳到执行中控推进执行。",
    },
    "候选去交易": {
        "condition": "focus_or_orders",
        "disabled": "先选中候选股票，或先生成委托建议。",
        "enabled": "把打板候选带到执行中控。",
    },
    "闸门看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从闸门审查跳回机会池核对逻辑。",
    },
    "执行看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从执行区跳回机会池核对逻辑。",
    },
    "候选看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从候选区跳回机会池。",
    },
    "监控看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从监控区跳回机会池。",
    },
    "复盘看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从复盘指标区跳回机会池。",
    },
    "结论看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从复盘结论跳回机会池。",
    },
    "决策看机会池": {
        "condition": "has_pool",
        "disabled": "需要先生成机会池。",
        "enabled": "从决策画像跳回机会池。",
    },
    "指标看扫描": {
        "condition": "focus_only",
        "disabled": "先在机会池、信号扫描或执行中控选中一只焦点股票。",
        "enabled": "从指标区跳回信号扫描继续看。",
    },
    "执行看扫描": {
        "condition": "focus_only",
        "disabled": "先在当前页面选中一只焦点股票。",
        "enabled": "从执行区跳回信号扫描继续看。",
    },
    "候选看扫描": {
        "condition": "focus_only",
        "disabled": "先选中一只打板候选股票。",
        "enabled": "把当前候选同步到信号扫描。",
    },
    "监控看扫描": {
        "condition": "focus_only",
        "disabled": "先选中一只监控焦点股票。",
        "enabled": "把当前监控焦点同步到信号扫描。",
    },
    "纸面看推荐": {
        "condition": "paper_focus",
        "disabled": "先在模拟盘持仓或流水里选中一只股票。",
        "enabled": "带着模拟盘焦点跳到机会池。",
    },
}


def action_row_compact_label(label: str, fallback: str = "") -> str:
    normalized = str(label or "").strip()
    if not normalized:
        return fallback
    return str(ACTION_ROW_COMPACT_LABELS.get(normalized, normalized) or fallback or normalized)


def action_row_tooltip_copy(label: str, fallback: str = "") -> str:
    normalized = str(label or "").strip()
    if not normalized:
        return fallback
    compact = action_row_compact_label(normalized, normalized)
    return str(ACTION_ROW_TOOLTIP_COPY.get(compact, fallback) or fallback)


def contextual_entry_rename_targets(tab_name: str) -> dict[str, list[str]]:
    normalized = str(tab_name or "").strip()
    mapping = CONTEXTUAL_ENTRY_RENAME_TARGETS.get(normalized, {})
    return {key: list(values) for key, values in mapping.items()}


def contextual_entry_tooltip_suffix(prefix: str, fallback: str = "") -> str:
    normalized = str(prefix or "").strip()
    if not normalized:
        return fallback
    return str(CONTEXTUAL_ENTRY_TOOLTIP_SUFFIX.get(normalized, fallback) or fallback)


def contextual_route_button_rule(label: str) -> dict[str, str]:
    normalized = str(label or "").strip()
    if not normalized:
        return {}
    return dict(CONTEXTUAL_ROUTE_BUTTON_RULES.get(normalized, {}))


def workspace_key_from_label(label: str, default: str = "overview") -> str:
    normalized = str(label or "").strip()
    if not normalized:
        return default
    return WORKSPACE_KEY_ALIASES.get(normalized, default)


def workspace_hero_payload(key: str) -> tuple[str, str, str, list[tuple[str, str]]]:
    spec = WORKSPACE_UI_SPECS.get(key, {})
    return (
        str(spec.get("hero_eyebrow", WORKSPACE_LABEL_BY_KEY.get(key, "工作区"))),
        str(spec.get("hero_title", WORKSPACE_LABEL_BY_KEY.get(key, "工作区"))),
        str(spec.get("hero_subtitle", "")),
        list(spec.get("hero_badges", []) or []),
    )


def workspace_shell_header_copy(key: str) -> tuple[str, str, str]:
    spec = WORKSPACE_UI_SPECS.get(key, {})
    title = str(spec.get("shell_title", f"量化猎手 Pro / {WORKSPACE_LABEL_BY_KEY.get(key, '工作区')}"))
    subtitle = str(spec.get("shell_subtitle", "状态 / 焦点 / 下一步"))
    badge = str(spec.get("shell_badge", WORKSPACE_LABEL_BY_KEY.get(key, "工作区")))
    return title, subtitle, badge


def workspace_tab_tooltip(key: str) -> str:
    return str(WORKSPACE_UI_SPECS.get(key, {}).get("tab_tooltip", "进入对应工作区。"))


def workspace_statusbar_caption(key: str) -> tuple[str, str]:
    spec = WORKSPACE_UI_SPECS.get(key, {})
    title = str(spec.get("status_title", WORKSPACE_LABEL_BY_KEY.get(key, "工作区")))
    caption = str(spec.get("status_caption", "统一管理行情、推荐、执行与复盘。"))
    return title, caption


RECOMMEND_AUX_STAGE_POLICY = {
    "default_visible": False,
    "toggle_text": {
        False: "展开辅助洞察",
        True: "收起辅助洞察",
    },
    "toggle_tooltip": {
        False: "展开后会补充战法、观察池、复盘与次日预案，适合需要更深判断时查看。",
        True: "收起后只保留成交决策核心区块，适合快速过门槛与进交易。",
    },
    "status_text": {
        False: "辅助洞察已折叠，当前只保留成交决策所需核心区块。",
        True: "辅助洞察已展开：这里会补充战法、观察池、复盘与次日预案。",
    },
    "status_tooltip": {
        False: "当前保持折叠，系统建议先看焦点票结论、价格计划和交易门槛。",
        True: "当前已展开辅助区，适合补看战法、复盘证据和次日预案。",
    },
    "no_focus_collapsed_text": "辅助洞察已折叠，先建立焦点票，再决定要不要展开更深分析。",
    "no_focus_collapsed_tooltip": "先从机会池选中焦点股票，核心决策区就会同步显示结论、价格计划与下一步。",
    "ready_collapsed_text": "辅助洞察可按需展开：当前已接近成交或复核阶段，若要看战法和复盘可展开下半区。",
    "ready_collapsed_tooltip": "当前已接近送审、复核或执行中控节点；若要确认战法背景和复盘证据，可以展开辅助区。",
    "focus_collapsed_text_template": "辅助洞察保持折叠：当前先聚焦成交门槛，结论“{verdict}”仍以核心区块判断为主。",
    "focus_collapsed_tooltip_template": "当前焦点为 {name}；建议先看核心区块里的结论、价格计划和执行门槛。",
    "focus_expanded_tooltip_template": "当前焦点为 {name}，辅助区已展开，可继续看战法、复盘与次日预案。",
}


BROKER_SETUP_POLICY = {
    "default_visible": True,
    "drawer_min_height": {
        False: 0,
        True: 408,
    },
    "toggle_text": {
        False: "展开账户与通道设置",
        True: "收起账户与通道设置",
    },
    "status_text": {
        False: "账户接入、SDK、导出与运行维护默认收起；盘中先看委托、闸门和回执。",
        True: "账户与通道设置已展开：现在可以继续校验连接、调整参数和运行维护。",
    },
    "section_status": {
        "profile": "账户与通道设置已展开：当前聚焦账户接入、桥接环境和导出目录。",
        "action": "账户与通道设置已展开：当前聚焦执行参数、模板与联调入口。",
        "runtime": "账户与通道设置已展开：当前聚焦运行维护、日志与缓存处理。",
    },
    "section_sizes": {
        "profile": [760, 460, 320],
        "action": [380, 800, 300],
        "runtime": [300, 360, 820],
    },
    "collapsed_status_by_stage": {
        "default": "账户接入、SDK、导出与运行维护默认收起；盘中先看委托、闸门和回执。",
        "orders": "账户与通道设置已收起；当前重点是焦点委托、闸门和提交确认。",
        "submissions": "账户与通道设置已收起；当前重点是回执、成交和偏差复盘。",
    },
}


OVERVIEW_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 284,
    },
    "container_min_height": {
        False: 0,
        True: 244,
    },
    "toggle_text": {
        False: "展开市场控制台",
        True: "收起市场控制台",
    },
    "status_text": {
        False: "首屏已聚焦市场洞察；搜索、刷新与快筛默认收起。",
        True: "市场控制台已展开：现在可以继续搜索、刷新和切换快筛。",
    },
}


RECOMMEND_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 368,
    },
    "toggle_text": {
        False: "展开推荐控制台",
        True: "收起推荐控制台",
    },
    "status_text": {
        False: "首屏优先看焦点、送审和结论；数据接入与筛选默认收起。",
        True: "推荐控制台已展开：现在可以继续接入数据、切换筛选和调整送审动作。",
    },
}


BOARD_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 276,
    },
    "toggle_text": {
        False: "展开打板控制台",
        True: "收起打板控制台",
    },
    "status_text": {
        False: "首屏优先看候选、监控和回封风险；导出和专项设置默认收起。",
        True: "打板控制台已展开：现在可以继续刷新专项候选和导出计划/复盘。",
    },
}


WORKSPACE_PRIMARY_FLOW_POLICY = {
    "overview": {
        "anchor_attr": "dashboard_metrics_box",
        "before_anchor_attrs": [
            "market_focus_summary_box",
            "overview_summary_box",
            "overview_desk_summary_frame",
            "overview_capability_box",
        ],
        "after_anchor_attrs": [
            "overview_stage_container",
            "overview_cockpit_box",
            "overview_playbook_box",
        ],
        "stretch": {
            "overview_stage_container": 5,
        },
    },
    "recommend": {
        "sequence_attrs": [
            "recommend_desk_summary_frame",
            "recommend_focus_cards_box",
            "recommend_decision_summary_box",
            "recommend_stage_summary_frame",
            "recommend_workflow_tabs",
        ],
        "stretch": {
            "recommend_workflow_tabs": 4,
        },
    },
    "broker": {
        "sequence_attrs": [
            "broker_desk_summary_frame",
            "broker_stage_summary_frame",
            "broker_stage_tabs",
        ],
        "stretch": {
            "broker_stage_tabs": 4,
        },
    },
}


WORKSPACE_ROOT_LAYOUT_POLICY = {
    "auth": {
        "insert_start": 1,
        "sequence_attrs": [
            "auth_status_banner",
            "auth_desk_summary_frame",
            "auth_summary_box",
            "auth_capability_box",
            "auth_form_box",
            "auth_status_box",
        ],
    },
    "recommend": {
        "insert_start": 1,
        "sequence_attrs": [
            "recommend_status_label",
            "recommend_message_toast_label",
            "recommend_desk_summary_frame",
            "recommend_focus_cards_box",
            "recommend_decision_summary_box",
            "recommend_stage_summary_frame",
            "recommend_workflow_tabs",
        ],
    },
    "broker": {
        "insert_start": 0,
        "sequence_attrs": [
            "broker_workspace_hero",
            "broker_status_banner",
            "broker_stage_label",
            "broker_workbench_banner",
            "broker_desk_summary_frame",
            "broker_stage_summary_frame",
            "broker_stage_tabs",
        ],
    },
}


FIRST_SCREEN_VISIBILITY_POLICY = {
    "auth_status_banner": {
        "hide_on_watch_when_auth_ready": True,
    },
    "auth_summary_box": {
        "hide_on_watch_when_auth_ready": True,
    },
    "auth_capability_box": {
        "hide_on_watch_when_auth_ready": True,
    },
    "auth_status_box": {
        "hide_on_watch_when_auth_ready": True,
    },
    "auth_desk_summary_frame": {
        "hide_on_watch_when_auth_ready": True,
    },
    "market_status_label": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_leaderboard_box": {
        "hide_on_watch": True,
    },
    "overview_priority_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_left_panel": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_right_panel": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_market_header_copy": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_dashboard_metrics_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_summary_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_capability_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_signal_summary_column": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_mini_chart_tabs": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_chart_controls_tabs": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_right_intel_tabs": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_theme_summary_box": {
        "hide_on_watch": True,
    },
    "overview_cockpit_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "overview_playbook_box": {
        "hide_on_watch_when_market_ready": True,
    },
    "recommend_empty_box": {
        "show_when_daily_pool_empty": True,
    },
    "recommend_status_label": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "recommend_section_hint": {
        "hide_on_compact_when_daily_pool_exists": True,
    },
    "recommend_desk_summary_frame": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "recommend_focus_cards_box": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "recommend_capability_box": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "recommend_deep_summary_box": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "recommend_stage_summary_frame": {
        "hide_on_watch_when_daily_pool_exists": True,
    },
    "broker_recap_box": {
        "show_when_submission_records": True,
    },
    "broker_workbench_banner": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_stage_label": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_desk_summary_frame": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_stage_summary_frame": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_summary_box": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_metrics_box": {
        "hide_on_watch_when_broker_ready": True,
    },
    "broker_capability_box": {
        "hide_on_watch_when_broker_ready": True,
    },
    "scanner_summary_box": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_capability_box": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_watch_summary_box": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_monitor_summary_box": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_status_banner": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_desk_summary_frame": {
        "hide_on_watch": True,
    },
    "scanner_tool_panel": {
        "hide_on_watch_when_scan_rows_exist": True,
    },
    "scanner_stage_summary_frame": {
        "hide_on_watch": True,
    },
    "board_summary_box": {
        "hide_on_watch_when_board_rows_exist": True,
    },
    "board_capability_box": {
        "hide_on_watch_when_board_rows_exist": True,
    },
    "board_status_banner": {
        "hide_on_watch_when_board_rows_exist": True,
    },
    "board_desk_summary_frame": {
        "hide_on_watch": True,
    },
    "board_tool_panel": {
        "hide_on_watch_when_board_rows_exist": True,
    },
    "board_stage_summary_frame": {
        "hide_on_watch": True,
    },
    "detail_summary_box": {
        "hide_on_watch_when_active_symbol_exists": True,
    },
    "detail_capability_box": {
        "hide_on_watch_when_active_symbol_exists": True,
    },
    "detail_status_banner": {
        "hide_on_watch_when_active_symbol_exists": True,
    },
    "detail_desk_summary_frame": {
        "hide_on_watch": True,
    },
    "detail_tool_panel": {
        "hide_on_watch_when_active_symbol_exists": True,
    },
    "detail_stage_summary_frame": {
        "hide_on_watch": True,
    },
    "paper_summary_box": {
        "hide_on_watch_when_paper_ready": True,
    },
    "paper_capability_box": {
        "hide_on_watch_when_paper_ready": True,
    },
    "paper_status_banner": {
        "hide_on_watch_when_paper_ready": True,
    },
    "paper_desk_summary_frame": {
        "hide_on_watch": True,
    },
    "paper_overview_box": {
        "hide_on_watch_when_paper_ready": True,
    },
    "paper_tool_panel": {
        "hide_on_watch_when_paper_ready": True,
    },
    "paper_stage_summary_frame": {
        "hide_on_watch": True,
    },
    "config_tool_panel": {
        "hide_on_watch": True,
    },
    "config_status_banner": {
        "hide_on_watch": True,
    },
    "config_desk_summary_frame": {
        "hide_on_watch": True,
    },
    "config_risk_snapshot_box": {
        "hide_on_watch": True,
    },
    "config_capability_box": {
        "hide_on_watch": True,
    },
    "config_stage_summary_frame": {
        "hide_on_watch": True,
    },
}


WORKSPACE_SPLITTER_POLICY = {
    "post_build_defaults": {
        "broker_control_splitter": [360, 980],
        "broker_middle_splitter": [380, 760],
        "recommend_splitter": [820, 420],
    },
    "workspace_defaults": {
        "recommend_dispatch_splitter": [320, 520, 280],
        "recommend_summary_splitter": [380, 760],
    },
}


OVERVIEW_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 284,
    },
    "container_min_height": {
        False: 0,
        True: 244,
    },
    "toggle_text": {
        False: "展开市场控制台",
        True: "收起市场控制台",
    },
    "status_text": {
        False: "首屏已聚焦市场洞察；搜索、刷新与快筛默认收起。",
        True: "市场控制台已展开：现在可以继续搜索、刷新和切换快筛。",
    },
}


RECOMMEND_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 368,
    },
    "toggle_text": {
        False: "展开推荐控制台",
        True: "收起推荐控制台",
    },
    "status_text": {
        False: "首屏优先看焦点、送审和结论；数据接入与筛选默认收起。",
        True: "推荐控制台已展开：现在可以继续接入数据、切换筛选和调整送审动作。",
    },
}


BOARD_CONTROLS_POLICY = {
    "default_visible": False,
    "drawer_min_height": {
        False: 0,
        True: 276,
    },
    "toggle_text": {
        False: "展开打板控制台",
        True: "收起打板控制台",
    },
    "status_text": {
        False: "首屏优先看候选、监控和回封风险；导出和专项设置默认收起。",
        True: "打板控制台已展开：现在可以继续刷新专项候选和导出计划/复盘。",
    },
}


TERMINAL_TABLE_LAYOUT_SPECS = {
    "market_pool_table": {
        "visibility_priority": {
            0: 1,
            1: 1,
            2: 3,
            3: 2,
            4: 1,
            5: 1,
        },
        "header_labels": {
            0: "位次",
            1: "标的 / 代码",
            2: "资金标签",
            3: "策略标签",
            4: "涨跌幅",
            5: "最新价",
        },
        "compact_header_labels": {
            1: "标的",
            2: "资金",
            3: "策略",
            4: "涨跌",
            5: "现价",
        },
        "widths": {0: 62, 1: 228, 2: 132, 3: 132, 4: 92, 5: 96},
        "stretch_column": 1,
        "min_height": 260,
        "row_height": 56,
        "header_height": 36,
        "empty_title": "等待市场快照",
        "empty_hint": "先刷新市场或载入样例，市场池会在这里形成。",
        "compact_breakpoint": 980,
        "ultra_compact_breakpoint": 760,
        "left_columns": [1, 2, 3],
        "center_columns": [0],
        "right_columns": [4, 5],
        "emphasis_columns": [1],
        "primary_numeric_columns": [4, 5],
        "compact_hidden": [2],
        "ultra_compact_hidden": [2, 3],
        "empty_title": "等待市场快照",
        "empty_hint": "先刷新市场或载入样例，市场池会在这里形成。",
        "header_tooltips": {
            0: "综合排序位次。",
            1: "标的身份信息，优先扫读名称与交易对象。",
            2: "资金标签，判断主力和风格来源。",
            3: "策略标签，说明当前归属的判断框架。",
            4: "行情强弱，属于数字列。",
            5: "最新价格，属于数字列。",
        },
    },
    "daily_pool_table": {
        "visibility_priority": {
            0: 1,
            1: 1,
            2: 3,
            3: 3,
            4: 1,
            5: 3,
            6: 3,
            7: 3,
            8: 1,
            9: 2,
            10: 3,
            11: 3,
            12: 3,
            13: 3,
            14: 3,
            15: 3,
            16: 3,
            17: 3,
            18: 3,
            19: 1,
            21: 2,
            22: 3,
            23: 1,
        },
        "header_labels": {
            0: "状态",
            1: "标的 / 代码",
            4: "主线 / 位次",
            8: "风险 / 总分",
            9: "策略归因",
            19: "动作",
            21: "催化摘要",
            23: "价格 / 计划",
        },
        "compact_header_labels": {
            1: "标的",
            4: "主线",
            8: "风险",
            9: "归因",
            21: "催化",
            23: "价格",
        },
        "hidden": [20],
        "widths": {0: 72, 1: 188, 2: 88, 3: 112, 4: 152, 5: 72, 6: 84, 7: 88, 8: 94, 9: 128, 18: 82, 19: 122, 21: 132, 22: 96, 23: 146},
        "stretch_column": 4,
        "min_height": 320,
        "row_height": 58,
        "header_height": 36,
        "empty_title": "等待机会池",
        "empty_hint": "先刷新推荐或载入样例，机会池和主线候选会在这里生成。",
        "compact_breakpoint": 1280,
        "ultra_compact_breakpoint": 1080,
        "left_columns": [1, 4, 9, 21],
        "center_columns": [0, 2, 3, 5, 6, 7, 13, 14, 15, 16, 17, 18, 19, 22],
        "right_columns": [8, 10, 11, 12, 23],
        "emphasis_columns": [1, 4],
        "primary_numeric_columns": [8, 10, 12, 23],
        "compact_hidden": [2, 3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 18, 22],
        "ultra_compact_hidden": [2, 3, 5, 6, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 21, 22],
        "empty_title": "等待机会池",
        "empty_hint": "先刷新推荐或载入样例，机会池和主线候选会在这里生成。",
        "header_tooltips": {
            1: "标的身份与交易对象。",
            4: "主线标签和位次判断，是机会池首要扫读列。",
            8: "风险与总分，属于数字判断列。",
            9: "策略归因，说明为何进入当前池。",
            19: "当前建议动作。",
            21: "催化摘要与消息结论。",
            23: "价格与计划区间，属于数字判断列。",
        },
    },
    "trade_plan_table": {
        "visibility_priority": {
            0: 1,
            1: 1,
            2: 3,
            3: 3,
            4: 3,
            5: 1,
            6: 3,
            7: 3,
            8: 3,
            9: 3,
            10: 3,
            11: 3,
            12: 3,
            14: 2,
            15: 1,
        },
        "header_labels": {
            0: "状态",
            1: "标的 / 代码",
            4: "动作",
            5: "主线",
            8: "置信",
            10: "止损",
            11: "目标",
            12: "资金",
            14: "执行提示",
            15: "策略说明",
        },
        "compact_header_labels": {
            1: "标的",
            14: "提示",
            15: "说明",
        },
        "hidden": [13],
        "widths": {0: 78, 1: 184, 2: 88, 3: 112, 4: 86, 5: 108, 6: 88, 7: 90, 8: 82, 9: 92, 10: 92, 11: 92, 12: 96, 14: 164, 15: 260},
        "stretch_column": 15,
        "min_height": 280,
        "row_height": 42,
        "header_height": 36,
        "empty_title": "等待交易计划",
        "empty_hint": "先确认焦点票和送审条件，今日计划会在这里沉淀。",
        "compact_breakpoint": 1220,
        "ultra_compact_breakpoint": 1020,
        "left_columns": [1, 14, 15],
        "center_columns": [0, 2, 3, 4, 8],
        "right_columns": [5, 6, 7, 9, 10, 11, 12],
        "emphasis_columns": [1, 14],
        "primary_numeric_columns": [5, 9, 10, 11, 12],
        "compact_hidden": [2, 3, 4, 6, 7, 8, 9, 10, 11, 12],
        "ultra_compact_hidden": [2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 14],
        "empty_title": "等待交易计划",
        "empty_hint": "先确认焦点票和送审条件，今日计划会在这里沉淀。",
        "header_tooltips": {
            1: "计划标的与身份信息。",
            14: "执行理由摘要。",
            15: "完整计划说明与处理动作。",
        },
    },
    "orders_table": {
        "visibility_priority": {
            0: 3,
            1: 1,
            2: 1,
            3: 1,
            4: 1,
            9: 2,
            11: 1,
            12: 1,
        },
        "header_labels": {
            0: "优先级",
            1: "标的",
            2: "动作",
            3: "价格",
            4: "数量",
            9: "主线闸门",
            11: "原因摘要",
            12: "风险灯",
        },
        "compact_header_labels": {
            0: "优先",
            9: "闸门",
            11: "原因",
            12: "风险",
        },
        "hidden": [5, 6, 7, 8, 10],
        "widths": {0: 72, 1: 138, 2: 76, 3: 86, 4: 82, 9: 132, 11: 320, 12: 92},
        "stretch_column": 11,
        "min_height": 340,
        "row_height": 42,
        "header_height": 36,
        "empty_title": "等待委托建议",
        "empty_hint": "先从机会池或交易计划生成委托，执行台会在这里排队。",
        "compact_breakpoint": 1180,
        "ultra_compact_breakpoint": 980,
        "left_columns": [1, 9, 11],
        "center_columns": [0, 2, 12],
        "right_columns": [3, 4],
        "emphasis_columns": [1, 11],
        "primary_numeric_columns": [3, 4],
        "compact_hidden": [0],
        "ultra_compact_hidden": [0, 9],
        "empty_title": "等待委托建议",
        "empty_hint": "先从机会池或交易计划生成委托，执行台会在这里排队。",
        "header_tooltips": {
            0: "委托优先级，越靠前越优先复核。",
            1: "交易标的。",
            2: "执行动作。",
            3: "计划价格，属于数字列。",
            4: "计划数量，属于数字列。",
            9: "主线闸门结论。",
            11: "委托原因摘要，是委托台主阅读列。",
            12: "风险灯语义，只服务风控，不服务涨跌判断。",
        },
    },
    "execution_table": {
        "visibility_priority": {
            0: 1,
            1: 2,
            2: 2,
            3: 1,
            4: 1,
            5: 1,
            6: 1,
            7: 3,
            8: 1,
        },
        "header_labels": {
            0: "节点 / 时间",
            1: "订单",
            2: "成交",
            3: "标的",
            4: "动作",
            5: "价格",
            6: "数量",
            7: "异常",
            8: "反馈信息",
        },
        "compact_header_labels": {
            0: "节点",
            8: "反馈",
        },
        "widths": {0: 148, 1: 86, 2: 86, 3: 132, 4: 96, 5: 82, 6: 74, 7: 118, 8: 260},
        "stretch_column": 8,
        "min_height": 266,
        "row_height": 42,
        "header_height": 36,
        "empty_title": "等待执行回执",
        "empty_hint": "提交后回执、异常和反馈会按时间顺序出现在这里。",
        "compact_breakpoint": 600,
        "ultra_compact_breakpoint": 460,
        "left_columns": [3, 7, 8],
        "center_columns": [0, 1, 2, 4],
        "right_columns": [5, 6],
        "emphasis_columns": [3, 8],
        "primary_numeric_columns": [5, 6],
        "compact_hidden": [7],
        "ultra_compact_hidden": [1, 2, 7],
        "empty_title": "等待执行回执",
        "empty_hint": "提交后回执、异常和反馈会按时间顺序出现在这里。",
        "header_tooltips": {
            0: "回执时间。",
            1: "订单状态。",
            2: "成交状态。",
            3: "交易标的。",
            5: "成交价格，属于数字列。",
            6: "成交数量，属于数字列。",
            7: "错误摘要。",
            8: "系统反馈与执行信息。",
        },
    },
    "board_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 3,
            3: 2,
            4: 3,
            5: 3,
            6: 3,
            7: 1,
            8: 1,
            9: 1,
            10: 1,
            11: 1,
        },
        "header_labels": {
            0: "标的 / 代码",
            3: "打板级别",
            7: "触发方式",
            8: "风险级别",
            9: "计划买点",
            10: "止损",
            11: "目标",
        },
        "compact_header_labels": {
            0: "标的",
            3: "级别",
            7: "触发",
            8: "风险",
            9: "买点",
            10: "止损",
            11: "目标",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            7: "触发",
            8: "风险",
            9: "买",
            10: "损",
            11: "目",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 96, 2: 122, 3: 88, 4: 84, 5: 84, 6: 84, 7: 116, 8: 96, 9: 102, 10: 92, 11: 92},
        "stretch_column": 7,
        "min_height": 250,
        "row_height": 42,
        "header_height": 36,
        "compact_breakpoint": 1140,
        "ultra_compact_breakpoint": 940,
        "left_columns": [0, 7],
        "center_columns": [3, 8],
        "right_columns": [4, 5, 6, 9, 10, 11],
        "emphasis_columns": [0, 7, 8],
        "primary_numeric_columns": [9, 10, 11],
        "compact_hidden": [2, 4, 5, 6],
        "ultra_compact_hidden": [2, 3, 4, 5, 6],
        "empty_title": "等待打板候选",
        "empty_hint": "先从信号扫描或机会池同步强势候选，专项候选会在这里排队。",
        "header_tooltips": {
            0: "专项候选身份信息，是首要扫读列。",
            3: "当前打板级别。",
            7: "当前触发方式与条件。",
            8: "专项风险判断。",
            9: "计划买点，属于数字列。",
            10: "计划止损，属于数字列。",
            11: "计划目标，属于数字列。",
        },
    },
    "board_monitor_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 3,
            3: 1,
            4: 2,
            5: 2,
            6: 3,
            7: 1,
            8: 1,
            9: 2,
        },
        "header_labels": {
            0: "标的 / 代码",
            3: "监控状态",
            4: "强度",
            5: "连续性",
            7: "炸板风险",
            8: "动作建议",
            9: "备注",
        },
        "compact_header_labels": {
            0: "标的",
            3: "状态",
            4: "强度",
            5: "连续",
            7: "风险",
            8: "动作",
            9: "备注",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            3: "状态",
            7: "风险",
            8: "动作",
            9: "备注",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 96, 2: 122, 3: 110, 4: 84, 5: 84, 6: 96, 7: 96, 8: 144, 9: 240},
        "stretch_column": 9,
        "min_height": 250,
        "row_height": 42,
        "header_height": 36,
        "compact_breakpoint": 1120,
        "ultra_compact_breakpoint": 920,
        "left_columns": [0, 8, 9],
        "center_columns": [3, 7],
        "right_columns": [4, 5, 6],
        "emphasis_columns": [0, 8],
        "primary_numeric_columns": [4, 5, 6],
        "compact_hidden": [2, 6],
        "ultra_compact_hidden": [2, 4, 5, 6],
        "empty_title": "等待专项监控",
        "empty_hint": "回封监控和炸板风险会在这里继续跟踪。",
        "header_tooltips": {
            0: "专项监控标的。",
            3: "当前监控状态。",
            4: "强度评分，属于数字列。",
            5: "连续性评分，属于数字列。",
            7: "炸板风险结论。",
            8: "当前动作建议。",
            9: "监控备注。",
        },
    },
    "scan_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 3,
            3: 1,
            4: 2,
            5: 2,
            6: 1,
            7: 1,
            8: 1,
            9: 1,
            10: 1,
        },
        "header_labels": {
            0: "标的 / 代码",
            3: "动作 / 信号",
            5: "评分",
            6: "信号日期",
            7: "收盘价",
            8: "入场价",
            9: "止损价",
            10: "目标价",
        },
        "compact_header_labels": {
            0: "标的",
            3: "动作",
            5: "评分",
            6: "日期",
            7: "收盘",
            8: "买点",
            9: "止损",
            10: "目标",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            3: "动作",
            6: "日期",
            8: "买",
            9: "损",
            10: "目",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 88, 2: 112, 3: 128, 4: 96, 5: 82, 6: 96, 7: 88, 8: 88, 9: 88, 10: 88},
        "stretch_column": 0,
        "min_height": 280,
        "row_height": 42,
        "header_height": 36,
        "compact_breakpoint": 1160,
        "ultra_compact_breakpoint": 940,
        "left_columns": [0],
        "center_columns": [3, 4, 6],
        "right_columns": [5, 7, 8, 9, 10],
        "emphasis_columns": [0, 3],
        "primary_numeric_columns": [5, 7, 8, 9, 10],
        "compact_hidden": [2, 4],
        "ultra_compact_hidden": [2, 4, 5, 7],
        "empty_title": "等待扫描信号",
        "empty_hint": "先执行扫描或载入样例，候选信号会在这里生成。",
        "header_tooltips": {
            0: "扫描候选标的。",
            3: "当前动作与信号结论。",
            5: "扫描评分，属于数字列。",
            6: "信号日期。",
            7: "收盘价，属于数字列。",
            8: "计划入场价，属于数字列。",
            9: "计划止损价，属于数字列。",
            10: "计划目标价，属于数字列。",
        },
    },
    "summary_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 3,
            3: 1,
            4: 1,
            5: 2,
            6: 2,
            7: 1,
        },
        "header_labels": {
            0: "标的 / 代码",
            3: "交易笔数",
            4: "收益率",
            5: "最大回撤",
            6: "胜率",
            7: "期末权益",
        },
        "compact_header_labels": {
            0: "标的",
            3: "笔数",
            4: "收益",
            5: "回撤",
            6: "胜率",
            7: "权益",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            3: "笔数",
            4: "收益",
            7: "权益",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 88, 2: 112, 3: 82, 4: 92, 5: 96, 6: 84, 7: 116},
        "stretch_column": 0,
        "min_height": 240,
        "row_height": 40,
        "header_height": 36,
        "compact_breakpoint": 980,
        "ultra_compact_breakpoint": 860,
        "left_columns": [0],
        "center_columns": [3],
        "right_columns": [4, 5, 6, 7],
        "emphasis_columns": [0],
        "primary_numeric_columns": [4, 5, 6, 7],
        "compact_hidden": [2],
        "ultra_compact_hidden": [2, 5, 6],
        "empty_title": "等待回测摘要",
        "empty_hint": "完成扫描与回测后，摘要会在这里汇总。",
    },
    "monitor_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 3,
            3: 1,
            4: 2,
            5: 2,
            6: 1,
            7: 1,
            8: 1,
        },
        "header_labels": {
            0: "标的 / 代码",
            3: "动作 / 信号",
            5: "评分",
            6: "收盘价",
            7: "信号日期",
            8: "更新时间",
        },
        "compact_header_labels": {
            0: "标的",
            3: "动作",
            5: "评分",
            6: "收盘",
            7: "日期",
            8: "更新",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            3: "动作",
            7: "日期",
            8: "更新",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 88, 2: 112, 3: 128, 4: 96, 5: 82, 6: 88, 7: 96, 8: 96},
        "stretch_column": 0,
        "min_height": 240,
        "row_height": 40,
        "header_height": 36,
        "compact_breakpoint": 1080,
        "ultra_compact_breakpoint": 880,
        "left_columns": [0],
        "center_columns": [3, 7, 8],
        "right_columns": [5, 6],
        "emphasis_columns": [0, 3],
        "primary_numeric_columns": [5, 6],
        "compact_hidden": [2, 4],
        "ultra_compact_hidden": [2, 4, 5, 6],
        "empty_title": "等待盘中监控",
        "empty_hint": "观察池或扫描榜同步后，盘中监控会在这里刷新。",
    },
    "leader_table": {
        "visibility_priority": {
            0: 1,
            1: 3,
            2: 1,
            3: 2,
            4: 1,
            5: 1,
            6: 1,
            7: 1,
            8: 1,
            9: 2,
        },
        "header_labels": {
            0: "标的 / 代码",
            2: "题材",
            3: "级别",
            4: "角色",
            5: "窗口",
            6: "风险",
            7: "龙头分",
            8: "动作",
            9: "说明",
        },
        "compact_header_labels": {
            0: "标的",
            2: "题材",
            3: "级别",
            4: "角色",
            5: "窗口",
            6: "风险",
            7: "评分",
            8: "动作",
            9: "说明",
        },
        "ultra_compact_header_labels": {
            0: "标的",
            2: "题材",
            4: "角色",
            6: "风险",
            7: "评分",
            8: "动作",
        },
        "hidden": [1],
        "widths": {0: 220, 1: 88, 2: 108, 3: 96, 4: 96, 5: 82, 6: 82, 7: 88, 8: 82, 9: 280},
        "stretch_column": 9,
        "min_height": 240,
        "row_height": 40,
        "header_height": 36,
        "compact_breakpoint": 1120,
        "ultra_compact_breakpoint": 920,
        "left_columns": [0, 2, 9],
        "center_columns": [3, 4, 6, 8],
        "right_columns": [5, 7],
        "emphasis_columns": [0, 2, 9],
        "primary_numeric_columns": [5, 7],
        "compact_hidden": [3],
        "ultra_compact_hidden": [3, 5, 9],
        "empty_title": "等待龙头榜",
        "empty_hint": "主线与候选同步后，龙头榜会在这里刷新。",
    },
}


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
