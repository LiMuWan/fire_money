from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTableWidgetItem

from quant_hunter.models import ScanRow


def refresh_recommend_summary_cards(window, plan) -> None:
    if not hasattr(window, "recommend_summary_cards"):
        return
    top_pick = window.daily_pool_rows[0] if window.daily_pool_rows else None
    top_note = plan.notes[0] if plan.notes else "等待推荐池刷新。"
    window.recommend_summary_cards["logic"].set_data(
        f"{getattr(top_pick, 'primary_strategy', '') or '掘龙决策'}" if top_pick else "--",
        (
            f"{top_pick.stock_name} | {top_pick.theme_name or '未分类'} | 决策分 {getattr(top_pick, 'dragon_decision_score', top_pick.total_score):.1f}"
            if top_pick
            else "等待生成推荐池后更新。"
        ),
    )
    window.recommend_summary_cards["plan"].set_data(
        f"{len(plan.decisions)} 只",
        (
            f"首选 {plan.decisions[0].stock_name} | 买点 {plan.decisions[0].planned_entry:.2f}"
            if plan.decisions
            else "当前暂无新开仓建议。"
        ),
    )
    window.recommend_summary_cards["pulse"].set_data(
        f"{plan.market_pulse.sentiment_score:.1f}",
        f"{plan.market_pulse.sentiment_label} / {plan.market_pulse.market_regime} / 风险 {plan.market_pulse.risk_level}",
    )
    window.recommend_summary_cards["holding"].set_data(
        f"{len(plan.position_advice)} 条",
        (
            f"卖出 {sum(1 for item in plan.position_advice if item.action == 'SELL')} | "
            f"减仓 {sum(1 for item in plan.position_advice if item.action == 'REDUCE')} | "
            f"{top_note}"
            if plan.position_advice
            else "当前没有持仓数据。"
        ),
    )


def refresh_strategy_path_panel(window, plan, top_theme, top_strategy_name, top_pick) -> None:
    if not hasattr(window, "strategy_path_text"):
        return
    if not top_pick:
        window.strategy_path_text.setPlainText("等待生成推荐池后更新主线推演路径。")
        return
    lines = [
        "题材 -> 龙头 -> 个股 -> 动作",
        "",
        f"1. 市场温度：{plan.market_pulse.sentiment_label} / {plan.market_pulse.market_regime}",
        f"2. 主线题材：{top_theme.theme_name if top_theme else '暂无'}",
        f"3. 高优先策略：{top_strategy_name or '掘龙决策'}",
        f"4. 龙头焦点：{top_pick.stock_name} ({top_pick.stock_id}) / {window._display_leader_level(top_pick.leader_level)}",
        f"5. 当前动作：{window._display_action(top_pick.action)}",
        "",
        "推演摘要",
        f"- {top_pick.theme_name or '未分类'} 题材当前位于前排，{getattr(top_pick, 'primary_strategy', '') or '掘龙决策'} 得分领先。",
        f"- 个股综合分 {top_pick.total_score:.1f}，决策分 {getattr(top_pick, 'dragon_decision_score', top_pick.total_score):.1f}。",
        f"- 催化：{top_pick.catalyst or '量价共振'}。",
    ]
    if window.market_path_alert_history:
        lines.extend(["", "最近提示"])
        lines.extend(f"- {item}" for item in window.market_path_alert_history[-4:])
    window.strategy_path_text.setPlainText("\n".join(lines))


def refresh_action_flow_cards(window, plan) -> None:
    if not hasattr(window, "action_flow_cards"):
        return
    buy_focus = plan.decisions[0] if plan.decisions else None
    watch_focus = next((item for item in window.daily_pool_rows if item.action == "WATCH"), None)
    reduce_focus = next((item for item in plan.position_advice if item.action == "REDUCE"), None)
    sell_focus = next((item for item in plan.position_advice if item.action == "SELL"), None)
    buy_count = len(plan.decisions)
    watch_count = sum(1 for item in window.daily_pool_rows if item.action == "WATCH")
    reduce_count = sum(1 for item in plan.position_advice if item.action == "REDUCE")
    sell_count = sum(1 for item in plan.position_advice if item.action == "SELL")

    window.action_flow_cards["BUY"].set_data(
        f"{buy_count} 只",
        f"焦点: {buy_focus.stock_name if buy_focus else '暂无'}",
        "优先从主线前排与高决策分候选中开仓。" if buy_focus else "当前暂无符合条件的新开仓建议。",
    )
    window.action_flow_cards["WATCH"].set_data(
        f"{watch_count} 只",
        f"焦点: {watch_focus.stock_name if watch_focus else '暂无'}",
        "继续观察量价、题材和资金是否共振。" if watch_focus else "当前观察池为空。",
    )
    window.action_flow_cards["REDUCE"].set_data(
        f"{reduce_count} 只",
        f"焦点: {reduce_focus.stock_name if reduce_focus else '暂无'}",
        "已有浮盈且题材掉队时优先分批减仓。" if reduce_focus else "当前没有减仓建议。",
    )
    window.action_flow_cards["SELL"].set_data(
        f"{sell_count} 只",
        f"焦点: {sell_focus.stock_name if sell_focus else '暂无'}",
        "跌破防守位或出现陷阱信号时优先离场。" if sell_focus else "当前没有明确离场建议。",
    )


def refresh_priority_cards(window, plan) -> None:
    if not hasattr(window, "priority_cards"):
        return
    top_theme = window.theme_heat_rows[0] if getattr(window, "theme_heat_rows", None) else None
    top_pick = window.daily_pool_rows[0] if window.daily_pool_rows else None
    strategy_counter: dict[str, int] = {}
    for item in window.daily_pool_rows:
        name = getattr(item, "primary_strategy", "") or "掘龙决策"
        strategy_counter[name] = strategy_counter.get(name, 0) + 1
    top_strategy_name, top_strategy_count = ("暂无", 0)
    if strategy_counter:
        top_strategy_name, top_strategy_count = max(strategy_counter.items(), key=lambda pair: pair[1])

    pulse = plan.market_pulse
    window.priority_cards["market"].set_data(
        f"{pulse.sentiment_score:.1f}",
        f"焦点: {pulse.sentiment_label} / {pulse.market_regime}",
        f"风险 {pulse.risk_level} | 总仓位上限 {pulse.max_total_exposure:.0%}",
    )
    window.priority_cards["theme"].set_data(
        f"{getattr(top_theme, 'strength_score', 0.0):.1f}" if top_theme else "--",
        f"焦点: {top_theme.theme_name if top_theme else '暂无'}",
        f"持续性 {getattr(top_theme, 'continuation_score', 0.0):.1f} | 龙头数 {getattr(top_theme, 'leader_count', 0)}",
    )
    window.priority_cards["strategy"].set_data(
        f"{top_strategy_count} 只",
        f"焦点: {top_strategy_name}",
        "当前推荐池中最拥挤、最优先复核的打法。",
    )
    window.priority_cards["focus"].set_data(
        f"{getattr(top_pick, 'dragon_decision_score', getattr(top_pick, 'total_score', 0.0)):.1f}" if top_pick else "--",
        f"焦点: {top_pick.stock_name if top_pick else '暂无'}",
        (
            f"{getattr(top_pick, 'primary_strategy', '') or '掘龙决策'} | {top_pick.theme_name or '未分类'}"
            if top_pick
            else "等待推荐池刷新。"
        ),
    )
    refresh_strategy_path_panel(window, plan, top_theme, top_strategy_name, top_pick)


def refresh_overview_priority_cards(window, pool: list, recommendations: list, top_theme: str) -> None:
    if not hasattr(window, "overview_priority_cards"):
        return
    avg_heat = (sum(getattr(item, "heat_score", 0.0) for item in pool) / len(pool)) if pool else 0.0
    strategy_counter: dict[str, int] = {}
    for item in recommendations:
        name = getattr(item, "primary_strategy", "") or "掘龙决策"
        strategy_counter[name] = strategy_counter.get(name, 0) + 1
    top_strategy_name, top_strategy_count = ("暂无", 0)
    if strategy_counter:
        top_strategy_name, top_strategy_count = max(strategy_counter.items(), key=lambda pair: pair[1])
    top_pick = recommendations[0] if recommendations else None
    window.overview_priority_cards["market"].set_data(
        f"{avg_heat:.1f}" if pool else "--",
        f"焦点: {'偏强' if avg_heat >= 75 else '中性' if avg_heat >= 60 else '谨慎'}",
        "按市场热度先决定进攻还是等待。",
    )
    window.overview_priority_cards["theme"].set_data(
        f"{sum(1 for item in pool if getattr(item, 'strategy_tag', '') == top_theme)} 只" if pool else "--",
        f"焦点: {top_theme or '暂无'}",
        "先看主线题材，再看龙头和动作。",
    )
    window.overview_priority_cards["strategy"].set_data(
        f"{top_strategy_count} 只",
        f"焦点: {top_strategy_name}",
        "当前推荐池里最值得先复核的战法。",
    )
    window.overview_priority_cards["focus"].set_data(
        f"{getattr(top_pick, 'dragon_decision_score', getattr(top_pick, 'total_score', 0.0)):.1f}" if top_pick else "--",
        f"焦点: {top_pick.stock_name if top_pick else '暂无'}",
        (
            f"{getattr(top_pick, 'primary_strategy', '') or '掘龙决策'} | {top_pick.theme_name or '未分类'}"
            if top_pick
            else "等待算法池刷新。"
        ),
    )


def refresh_strategy_focus_detail(window, strategy_score_fields) -> None:
    if not hasattr(window, "strategy_detail_text"):
        return
    strategy_name = window.strategy_detail_combo.currentText() if hasattr(window, "strategy_detail_combo") else "掘龙决策"
    field_name = strategy_score_fields.get(strategy_name, "dragon_decision_score")
    selected_row = None
    if hasattr(window, "daily_pool_table"):
        row_index = window.daily_pool_table.currentRow()
        source_rows = window._filtered_daily_pool_rows()
        if 0 <= row_index < len(source_rows):
            selected_row = source_rows[row_index]
    ranked = sorted(window.daily_pool_rows, key=lambda item: getattr(item, field_name, 0.0), reverse=True)
    focus_row = selected_row or (ranked[0] if ranked else None)
    if focus_row is None:
        window.strategy_detail_text.setPlainText("等待生成推荐池后更新。")
        return
    strategy_count = sum(
        1 for item in window.daily_pool_rows if (getattr(item, "primary_strategy", "") or "掘龙决策") == strategy_name
    )
    lines = [
        f"战法名称：{strategy_name}",
        f"主打法命中：{strategy_count} 只",
        "",
        f"当前焦点：{focus_row.stock_name} ({focus_row.stock_id} / {focus_row.symbol})",
        f"题材：{focus_row.theme_name or '未分类'} | 龙头级别：{window._display_leader_level(focus_row.leader_level)}",
        f"主策略：{getattr(focus_row, 'primary_strategy', '') or '掘龙决策'}",
        f"战法评分：{getattr(focus_row, field_name, 0.0):.1f}",
        f"综合评分：{focus_row.total_score:.1f}",
        f"交易动作：{window._display_action(focus_row.action)}",
        f"催化：{focus_row.catalyst or '量价共振'}",
        "",
        "五策对比",
        f"- 龙头模型：{getattr(focus_row, 'leader_model_score', 0.0):.1f}",
        f"- 主力雷达：{getattr(focus_row, 'main_force_score', 0.0):.1f}",
        f"- 擒龙打板：{getattr(focus_row, 'board_attack_score', 0.0):.1f}",
        f"- 价值低吸：{getattr(focus_row, 'value_recovery_score', 0.0):.1f}",
        f"- 掘龙决策：{getattr(focus_row, 'dragon_decision_score', focus_row.total_score):.1f}",
        "",
        "逻辑摘要",
        f"- {focus_row.rationale}",
        "",
        "该战法 Top 3",
    ]
    for item in ranked[:3]:
        lines.append(
            f"- {item.stock_name} | {getattr(item, field_name, 0.0):.1f} | {item.theme_name or '未分类'} | {window._display_action(item.action)}"
        )
    window.strategy_detail_text.setPlainText("\n".join(lines))


def populate_market_depth_texts(window, rows: list) -> None:
    if hasattr(window, "market_buy_text"):
        leaders = rows[:3]
        avg_change = sum(getattr(row, "pct_change", 0.0) for row in rows) / max(len(rows), 1)
        avg_turnover = sum(getattr(row, "turnover", 0.0) for row in rows) / max(len(rows), 1)
        buy_lines = [
            "指数总览",
            "",
            f"- 候选数量: {len(rows)}",
            f"- 平均涨幅: {avg_change:.2f}%",
            f"- 平均换手: {avg_turnover:.2f}%",
            "",
            "主线代表",
        ]
        for row in leaders:
            buy_lines.append(
                f"- {row.stock_name} | 热度 {row.heat_score:.1f} | 涨幅 {row.pct_change:.2f}% | 净流入 {row.main_inflow / 1e8:.2f} 亿"
            )
        if len(buy_lines) == 7:
            buy_lines.append("- 等待刷新市场快照")
        window.market_buy_text.setPlainText("\n".join(buy_lines))
    if hasattr(window, "market_sell_text"):
        up_count = sum(1 for row in rows if getattr(row, "pct_change", 0.0) > 0)
        down_count = sum(1 for row in rows if getattr(row, "pct_change", 0.0) < 0)
        flat_count = max(len(rows) - up_count - down_count, 0)
        volatile_rows = sorted(rows[:8], key=lambda item: item.turnover, reverse=True)
        sell_lines = [
            "涨跌分布",
            "",
            f"- 上涨: {up_count}",
            f"- 下跌: {down_count}",
            f"- 平盘: {flat_count}",
            "",
            "高波动关注",
        ]
        for row in volatile_rows[:4]:
            sell_lines.append(f"- {row.stock_name} | 换手 {row.turnover:.1f}% | 涨幅 {row.pct_change:.2f}%")
        if len(sell_lines) == 7:
            sell_lines.append("- 暂无分布数据")
        window.market_sell_text.setPlainText("\n".join(sell_lines))


def render_leaderboard_cards(window, rows: list) -> None:
    if not hasattr(window, "market_leaderboard_cards"):
        return
    visible_rows = rows[:3]
    for index, card in enumerate(window.market_leaderboard_cards):
        if index < len(visible_rows):
            card.show()
            card.set_row(f"TOP {index + 1}", visible_rows[index])
        else:
            card.show()
            card.set_message("等待刷新", "当前暂无入选标的。")


def refresh_strategy_pack_panels(window, strategy_score_fields) -> None:
    if not hasattr(window, "strategy_pack_cards"):
        return
    rows = list(window.daily_pool_rows)
    for strategy_name, field_name in strategy_score_fields.items():
        card = window.strategy_pack_cards.get(strategy_name)
        if card is None:
            continue
        ranked = sorted(rows, key=lambda item: getattr(item, field_name, 0.0), reverse=True)
        if not ranked:
            card.set_empty("等待生成推荐池后更新。")
            continue
        top = ranked[0]
        primary_count = sum(
            1 for item in ranked if (getattr(item, "primary_strategy", "") or "掘龙决策") == strategy_name
        )
        lines = []
        for item in ranked[:3]:
            lines.append(
                f"- {item.stock_name} | {getattr(item, field_name, 0.0):.1f} | {item.theme_name or '未分类'} | {window._display_action(item.action)}"
            )
        lines.append(f"逻辑：{top.rationale[:88]}")
        card.set_strategy_summary(
            strategy_name=strategy_name,
            primary_count=primary_count,
            focus_name=f"{top.stock_name} ({top.stock_id})",
            focus_score=getattr(top, field_name, 0.0),
            focus_theme=top.theme_name or "未分类",
            focus_action=window._display_action(top.action),
            top_rows=lines,
        )
    window._refresh_strategy_focus_detail()


def refresh_theme_heat_panels(window, strategy_score_fields) -> None:
    if hasattr(window, "theme_heat_table"):
        window.theme_heat_table.setRowCount(len(window.theme_heat_rows))
        for row_index, item in enumerate(window.theme_heat_rows):
            values = [
                item.theme_name,
                f"{item.strength_score:.1f}",
                f"{item.continuation_score:.1f}",
                f"{item.news_score:.1f}",
                str(item.leader_count),
                str(item.theme_rank),
                item.risk_flag,
            ]
            for column, value in enumerate(values):
                window.theme_heat_table.setItem(row_index, column, QTableWidgetItem(value))
    if hasattr(window, "leader_table"):
        window.leader_table.setRowCount(len(window.leader_candidates))
        for row_index, item in enumerate(window.leader_candidates):
            values = [
                item.stock_name,
                item.stock_id,
                item.theme_name,
                window._display_leader_level(item.leader_level),
                f"{item.leader_score:.1f}",
                window._display_action(item.action),
                item.rationale,
            ]
            for column, value in enumerate(values):
                window.leader_table.setItem(row_index, column, QTableWidgetItem(value))
    refresh_strategy_pack_panels(window, strategy_score_fields)


def populate_filtered_daily_pool_table(window) -> None:
    if not hasattr(window, "daily_pool_table"):
        return
    rows = [
        row
        for row in window.daily_pool_rows
        if window.recommend_theme_filter == "全部" or (row.theme_name or "未分类") == window.recommend_theme_filter
    ]
    window.daily_pool_table.setRowCount(len(rows))
    for row_index, row in enumerate(rows):
        values = [
            row.stock_name or window._stock_name_for_symbol(row.symbol),
            row.stock_id or window._stock_id_for_symbol(row.symbol),
            row.symbol,
            row.theme_name or "未分类",
            getattr(row, "primary_strategy", "") or "掘龙决策",
            f"{row.theme_score:.1f}",
            window._display_leader_level(row.leader_level),
            f"{row.total_score:.1f}",
            f"{getattr(row, 'leader_model_score', 0.0):.0f}",
            f"{getattr(row, 'main_force_score', 0.0):.0f}",
            f"{getattr(row, 'board_attack_score', 0.0):.0f}",
            f"{getattr(row, 'value_recovery_score', 0.0):.0f}",
            f"{getattr(row, 'dragon_decision_score', row.total_score):.0f}",
            window._display_action(row.action),
            row.catalyst,
            row.signal_date,
        ]
        for column, value in enumerate(values):
            window.daily_pool_table.setItem(row_index, column, QTableWidgetItem(value))


def apply_market_filters(window) -> None:
    if not hasattr(window, "market_pool_table"):
        return
    query = window.market_search_input.text().strip().lower() if hasattr(window, "market_search_input") else ""
    source_rows = list(getattr(window.market_screen_result, "algorithmic_pool", []))
    filtered_rows = []
    for row in source_rows:
        theme_name = getattr(row, "theme_name", "") or "未分类"
        if window.market_filter_tag != "全部" and row.strategy_tag != window.market_filter_tag:
            continue
        if window.market_theme_filter != "全部" and theme_name != window.market_theme_filter:
            continue
        haystacks = (
            row.stock_name.lower(),
            row.stock_id.lower(),
            row.symbol.lower(),
            theme_name.lower(),
            row.strategy_tag.lower(),
            getattr(row, "rationale", "").lower(),
        )
        if query and not any(query in item for item in haystacks):
            continue
        filtered_rows.append(row)
    window.market_pool_table.setRowCount(len(filtered_rows))
    for row_index, row in enumerate(filtered_rows):
        theme_name = getattr(row, "theme_name", "") or "未分类"
        background, foreground = window._market_pool_colors(row)

        rank_item = QTableWidgetItem(str(row_index + 1))
        rank_item.setData(Qt.UserRole, row.symbol)
        rank_item.setBackground(background)
        rank_item.setForeground(foreground)
        rank_item.setTextAlignment(Qt.AlignCenter)
        window.market_pool_table.setItem(row_index, 0, rank_item)

        window.market_pool_table.setCellWidget(row_index, 1, window._build_stock_identity_cell(row))
        window.market_pool_table.setCellWidget(
            row_index,
            2,
            window._build_badge_strip(
                [
                    (row.fund_model, *window._fund_badge_palette(row.fund_model)),
                    (f"净流入 {row.main_inflow / 1e8:.2f}亿", "#1b2633", "#8fc7ff"),
                ]
            ),
        )
        window.market_pool_table.setCellWidget(
            row_index,
            3,
            window._build_badge_strip(
                [
                    (row.strategy_tag, *window._strategy_badge_palette(row.strategy_tag)),
                    (theme_name, "#24303a", "#ffd166"),
                    (window._display_label(row.signal_label), *window._signal_badge_palette(row.signal_label)),
                ]
            ),
        )

        pct_item = QTableWidgetItem(f"{row.pct_change:.2f}%")
        pct_item.setBackground(background)
        pct_item.setForeground(foreground)
        pct_item.setTextAlignment(Qt.AlignCenter)
        window.market_pool_table.setItem(row_index, 4, pct_item)

        price_item = QTableWidgetItem(f"{row.latest_price:.2f}")
        price_item.setToolTip(f"决策分 {getattr(row, 'decision_score', 0.0):.1f} | 题材 {theme_name}")
        price_item.setBackground(background)
        price_item.setForeground(foreground)
        price_item.setTextAlignment(Qt.AlignCenter)
        window.market_pool_table.setItem(row_index, 5, price_item)

    window._populate_market_depth_texts(filtered_rows)
    window._refresh_overview_side_panels(filtered_rows)
    if filtered_rows:
        window.market_pool_table.selectRow(0)


def fill_scan_rows(window) -> None:
    window.scan_table.setRowCount(len(window.scan_rows))
    for row_index, row in enumerate(window.scan_rows):
        values = [
            window._stock_name_for_symbol(row.symbol),
            window._stock_id_for_symbol(row.symbol),
            row.symbol,
            window._display_action(row.action),
            window._display_label(row.label),
            str(row.score),
            row.signal_date,
            f"{row.close:.2f}",
            "" if row.entry_price is None else f"{row.entry_price:.2f}",
            "" if row.stop_price is None else f"{row.stop_price:.2f}",
            "" if row.target_price is None else f"{row.target_price:.2f}",
        ]
        for column, value in enumerate(values):
            window.scan_table.setItem(row_index, column, QTableWidgetItem(value))


def fill_backtest_summaries(window) -> None:
    window.summary_table.setRowCount(len(window.backtest_summaries))
    for row_index, item in enumerate(window.backtest_summaries):
        values = [
            window._stock_name_for_symbol(item.symbol),
            window._stock_id_for_symbol(item.symbol),
            item.symbol,
            str(item.trades),
            f"{item.total_return:.2%}",
            f"{item.max_drawdown:.2%}",
            f"{item.win_rate:.2%}",
            f"{item.ending_equity:,.0f}",
        ]
        for column, value in enumerate(values):
            window.summary_table.setItem(row_index, column, QTableWidgetItem(value))


def refresh_watchlist(window) -> None:
    window.watchlist_widget.clear()
    window.watchlist_widget.addItems(window.state.watchlist)
    if hasattr(window, "monitor_table"):
        window._refresh_intraday_monitor()


def refresh_intraday_monitor(window) -> None:
    updated = datetime.now().strftime("%H:%M:%S")
    rows_to_show: list[ScanRow] = []
    recommendation_map = {item.symbol: item for item in window.daily_pool_rows}
    if window.state.watchlist:
        scan_map = {row.symbol: row for row in window.scan_rows}
        for symbol in window.state.watchlist:
            row = scan_map.get(symbol)
            if row is not None:
                rows_to_show.append(row)
                continue
            analyses = window.universe_analyses.get(symbol, [])
            if analyses:
                latest = next((item for item in reversed(analyses) if item.label != "NONE"), analyses[-1])
                rows_to_show.append(
                    ScanRow(
                        symbol=symbol,
                        signal_date=latest.date,
                        label=latest.label,
                        action="HOLD" if latest.label == "NONE" else latest.label,
                        score=latest.score,
                        close=latest.close,
                        entry_price=latest.entry_price,
                        stop_price=latest.stop_price,
                        target_price=latest.target_price,
                        reason=latest.reason,
                        source_path=str(window.paths_by_symbol.get(symbol, "")),
                    )
                )
    else:
        rows_to_show = window.scan_rows[:10]

    should_beep = False
    window.monitor_table.setRowCount(len(rows_to_show))
    for row_index, row in enumerate(rows_to_show):
        values = [
            window._stock_name_for_symbol(row.symbol),
            window._stock_id_for_symbol(row.symbol),
            row.symbol,
            window._display_action(row.action),
            window._display_label(row.label),
            str(row.score),
            f"{row.close:.2f}",
            row.signal_date,
            updated,
        ]
        background, foreground = window._signal_colors(row.action, row.label)
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setBackground(background)
            item.setForeground(foreground)
            window.monitor_table.setItem(row_index, column, item)

        recommendation = recommendation_map.get(row.symbol)
        if recommendation and recommendation.theme_rank > window.state.strategy_top_theme_limit:
            alert_state = f"THEME_DROP::{recommendation.theme_rank}"
        else:
            alert_state = row.label if row.label in {"RECLAIM_LONG", "TRAP_DETECTED"} else ""
        previous_state = window.monitor_alert_state.get(row.symbol, "")
        if alert_state and alert_state != previous_state:
            should_beep = True
        window.monitor_alert_state[row.symbol] = alert_state

    active_symbols = {row.symbol for row in rows_to_show}
    window.monitor_alert_state = {
        symbol: state for symbol, state in window.monitor_alert_state.items() if symbol in active_symbols
    }
    if hasattr(window, "monitor_summary_text"):
        summary_limit = int(window._license_capabilities()["monitor_summary_limit"])
        theme_drop_rows = [
            recommendation_map[row.symbol]
            for row in rows_to_show
            if row.symbol in recommendation_map
            and recommendation_map[row.symbol].theme_rank > window.state.strategy_top_theme_limit
        ]
        notes: list[str] = []
        if window.state.focus_themes:
            focused_rows = [
                recommendation_map[row.symbol]
                for row in rows_to_show
                if row.symbol in recommendation_map and recommendation_map[row.symbol].theme_name in window.state.focus_themes
            ]
            notes.append(f"关注题材：{', '.join(window.state.focus_themes)}")
            notes.append(f"命中关注题材标的：{len(focused_rows)}")
        if theme_drop_rows:
            if notes:
                notes.append("")
            notes.extend(["盘中题材掉队提醒", ""])
            for item in theme_drop_rows[:summary_limit]:
                notes.append(
                    f"- {item.stock_name} | 题材 {item.theme_name} 跌至第 {item.theme_rank} 位，优先考虑减仓或观察。"
                )
        if not notes:
            notes.append("当前监控标的仍处在主线或未触发题材掉队提醒。")
        window.monitor_summary_text.setPlainText("\n".join(notes))
    if should_beep and window.sound_alert_checkbox.isChecked():
        QApplication.beep()
