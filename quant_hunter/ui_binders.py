from __future__ import annotations


def apply_daily_pool_rows(window, rows, summarize_themes_fn) -> None:
    window.daily_pool_rows = rows
    panel_size = int(window._license_capabilities()["theme_panel_size"])
    window.theme_heat_rows, window.leader_candidates = summarize_themes_fn(
        window.daily_pool_rows,
        top_n_themes=panel_size,
        top_n_leaders=panel_size,
    )
    window._refresh_recommend_theme_options()
    window._populate_filtered_daily_pool_table()
    window._refresh_theme_heat_panels()
    if hasattr(window, "daily_pool_text"):
        if window.daily_pool_rows:
            top = window.daily_pool_rows[0]
            theme_summary = "、".join(f"{item.theme_rank}.{item.theme_name}" for item in window.theme_heat_rows[:3]) or "暂无"
            window.daily_pool_text.setPlainText(
                "今日优先候选：\n"
                f"- 股票：{top.stock_name} ({top.stock_id} / {top.symbol})\n"
                f"- 题材：{top.theme_name or '未分类'}，题材排名第 {top.theme_rank}，龙头级别 {window._display_leader_level(top.leader_level)}\n"
                f"- 主线题材：{theme_summary}\n"
                f"- 总分：{top.total_score:.1f}\n"
                f"- 逻辑：{top.rationale}\n"
                f"- 催化：{top.catalyst or '暂无外部催化，偏技术面驱动'}\n"
            )
        else:
            window.daily_pool_text.setPlainText(
                "当前没有生成推荐池。\n"
                "- 请先扫描股票池。\n"
                "- 可选：导入股票资料 CSV，补全股票名称、行业和龙头标记。\n"
                "- 可选：导入消息面 CSV，增强每日推荐排序。\n"
            )
    if hasattr(window, "recommend_status_label"):
        top_theme = window.theme_heat_rows[0].theme_name if window.theme_heat_rows else "未分类"
        window.recommend_status_label.setText(
            f"每日推荐池已生成：{len(window.daily_pool_rows)} 只候选，当前主线题材为 {top_theme}。"
        )
    window._append_runtime_log(f"推荐池已生成：{len(window.daily_pool_rows)} 只候选")
    window._refresh_trade_plan()
    window._refresh_board_mode()



def apply_scan_universe_result(window, folder, payload) -> None:
    rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol, summaries = payload
    window.scan_rows = rows
    window.universe_bars = bars_by_symbol
    window.universe_analyses = analyses_by_symbol
    window.paths_by_symbol = paths_by_symbol
    window.backtest_summaries = summaries
    window.state.universe_dir = str(folder)

    if hasattr(window, "universe_label"):
        window.universe_label.setText(f"??????{folder}")
    if hasattr(window, "scan_summary_label"):
        window.scan_summary_label.setText(
            f"??? {len(bars_by_symbol)} ?????????? {len(rows)} ??"
        )
    window._append_runtime_log(
        f"???????{len(bars_by_symbol)} ????{len(rows)} ?????"
    )

    window._fill_scan_rows()
    window._fill_backtest_summaries()
    window._refresh_intraday_monitor()
    window.refresh_daily_pool(async_mode=True)

    if window.state.selected_symbol and window.state.selected_symbol in bars_by_symbol:
        window.select_symbol(window.state.selected_symbol)
    elif rows:
        window.select_symbol(rows[0].symbol)
    elif bars_by_symbol:
        window.select_symbol(next(iter(bars_by_symbol)))
    window.save_state()



def apply_market_screen_result(
    window,
    result,
    update_chart=False,
    feed_state=None,
    *,
    cache_cls,
    extract_stock_id_fn,
    stock_profile_cls,
    project_root,
) -> None:
    cache_stats = cache_cls().cache_stats()
    source_label = "????" if result.market_name == "????" else "????????"
    window._append_runtime_log(
        f"{source_label}?{len(result.algorithmic_pool)} ?????? {cache_stats['files']} ?? / {cache_stats['bytes'] / 1024:.1f} KB"
    )
    window.market_screen_result = result
    window.market_snapshots = result.snapshots
    window.scan_rows = result.scan_rows
    window.daily_pool_rows = result.recommendations
    window.universe_bars = result.bars_by_symbol
    window.universe_analyses = result.analyses_by_symbol
    window.paths_by_symbol = {
        symbol: project_root / "remote_market" / f"{extract_stock_id_fn(symbol)}.json"
        for symbol in result.bars_by_symbol
    }
    window.backtest_summaries = result.summaries
    if result.market_name == "????":
        window.load_sample_reference_data()
        window.market_data_source = "sample"
        window.last_market_error = ""
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("?????????????????????")
        window._refresh_overview_side_panels([])
        window._refresh_market_source_status(["- ??????????", "- ?????????"])
        return
    if not result.algorithmic_pool:
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("????????????????????????????")
        window._refresh_overview_side_panels([])
        return

    window.stock_profiles = {
        symbol: stock_profile_cls(
            symbol=symbol,
            stock_id=snapshot.stock_id,
            name=snapshot.stock_name,
            industry=snapshot.strategy_tag,
            is_leader=snapshot.heat_score >= 80,
            notes=snapshot.fund_model,
        )
        for symbol, snapshot in result.snapshots.items()
    }

    window._refresh_market_theme_options()
    window._apply_market_filters()
    window._update_dashboard_metrics()
    window._populate_existing_views_from_market()
    window._refresh_broker_status(extra=f"???????{len(result.algorithmic_pool)} ??")

    preferred = None
    if result.algorithmic_pool:
        preferred = (
            window.state.selected_symbol
            if window.state.selected_symbol in result.bars_by_symbol
            else result.algorithmic_pool[0].symbol
        )
        if update_chart or not window.active_symbol:
            window.select_symbol(preferred)

    if hasattr(window, "market_status_label"):
        window.market_status_label.setText(
            f"{result.market_name} | ??? {len(result.algorithmic_pool)} ??? | ???? {result.generated_at}"
        )
    state = feed_state or {}
    window.market_data_source = state.get("source", "remote") or "remote"
    window.last_market_success_at = result.generated_at
    window.last_market_error = state.get("error", "") or ""
    window._refresh_market_source_status(["- ?????????", f"- ?????{window._market_source_mode_label()}"])



def handle_market_refresh_error(window, message, quiet, *, show_error_dialog_fn) -> None:
    window._append_runtime_log(f"?????????{message}", "ERROR")
    window.market_data_source = "unknown"
    if hasattr(window, "market_status_label"):
        window.market_status_label.setText(f"???????{message}")
    window.last_market_error = message
    help_lines = [
        "????????????????",
        "",
        "?????",
        "- ????????????????????",
        "- ?????????????????????",
        "- ?????????????????",
        "",
        "?????",
        "- ????????????",
        "- ????????????????",
        "- ???????????????????????",
    ]
    if hasattr(window, "market_leaderboard_text") and not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.market_leaderboard_text.setPlainText("\n".join(help_lines))
    if hasattr(window, "market_theme_brief_text") and not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.market_theme_brief_text.setPlainText("???? / ????\n\n??????????????")
    window._refresh_market_source_status(["- ?????????", "- ??????????????"])
    if not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.load_sample_reference_data()
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("?????????????????????")
    if not quiet:
        show_error_dialog_fn(window, "??????", message)



def handle_daily_pool_error(window, message, *, show_error_dialog_fn) -> None:
    if hasattr(window, "recommend_status_label"):
        window.recommend_status_label.setText(f"????????{message}")
    window._append_runtime_log(f"????????{message}", "ERROR")
    show_error_dialog_fn(window, "???????", message)



def handle_scan_error(window, message, quiet, *, show_error_dialog_fn) -> None:
    if hasattr(window, "scan_summary_label"):
        window.scan_summary_label.setText(f"?????{message}")
    window._append_runtime_log(f"???????{message}", "ERROR")
    if not quiet:
        show_error_dialog_fn(window, "????", message)


def refresh_license_status_view(window, *, datetime_cls) -> None:
    if not hasattr(window, "license_status_text"):
        return
    started = window.state.trial_started_at or datetime_cls.now().date().isoformat()
    try:
        start_date = datetime_cls.strptime(started, "%Y-%m-%d").date()
    except ValueError:
        start_date = datetime_cls.now().date()
    days_used = max((datetime_cls.now().date() - start_date).days, 0)
    trial_days = 14
    remaining = max(trial_days - days_used, 0)
    capabilities = window._license_capabilities()
    plan = capabilities["plan"]
    lines = [
        f"当前方案：{plan}",
        f"试用开始：{start_date.isoformat()}",
        f"试用剩余：{remaining} 天",
        "",
    ]
    if plan == "ENTERPRISE":
        lines.append("企业版已启用：自动盘前报告、增强题材加权和扩展题材面板已开放。")
    elif plan == "PRO":
        lines.append("专业版已启用：自动盘前报告和题材优先加权已开放。")
    else:
        lines.append("试用版保留手动研究流程，自动盘前报告保持关闭。")
    lines.append(f"关注题材：{', '.join(window.state.focus_themes) if window.state.focus_themes else '未设置'}")
    lines.append(f"主线题材阈值：前 {window.state.strategy_top_theme_limit}")
    lines.append(f"题材加权：{float(capabilities['focus_theme_boost']):.0f}")
    lines.append(f"盘前模板：{window.state.daily_plan_template}")
    lines.append(f"模板仅关注题材：{'是' if window.state.daily_plan_focus_only else '否'}")
    lines.append(f"盘前股票池上限：{min(window.state.daily_plan_candidate_limit, int(capabilities['daily_plan_export_limit']))}")
    lines.append(f"市场历史回看深度：{int(capabilities['market_history_limit'])}")
    lines.append(f"监控摘要容量：{int(capabilities['monitor_summary_limit'])}")
    lines.append(
        "自动盘前报告："
        + (
            "已开启"
            if window.state.auto_daily_plan_export and bool(capabilities["auto_daily_plan_export"])
            else "未开启"
        )
    )
    if hasattr(window, "auto_daily_plan_export_checkbox"):
        enabled = bool(capabilities["auto_daily_plan_export"])
        window.auto_daily_plan_export_checkbox.setEnabled(enabled)
        if not enabled:
            window.auto_daily_plan_export_checkbox.setChecked(False)
            window.state.auto_daily_plan_export = False
    if hasattr(window, "config_inputs") and "daily_plan_candidate_limit" in window.config_inputs:
        window.config_inputs["daily_plan_candidate_limit"].setPlaceholderText(str(capabilities["daily_plan_export_limit"]))
    window.license_status_text.setPlainText("\n".join(lines))
