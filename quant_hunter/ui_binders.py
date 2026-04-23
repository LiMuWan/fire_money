from __future__ import annotations

from .risk import RISK_PROFILE_LABELS, risk_profile_brief, risk_profile_comparison_text


def apply_daily_pool_rows(window, rows, summarize_themes_fn) -> None:
    payload = rows
    build_meta: dict[str, object] = {}
    if isinstance(payload, tuple) and len(payload) == 2 and isinstance(payload[1], dict):
        rows = payload[0]
        build_meta = dict(payload[1])

    window.last_daily_pool_meta = build_meta
    window.daily_pool_rows = list(rows)

    risk_key = getattr(getattr(window, "state", None), "strategy_risk_profile", "standard")
    risk_label = RISK_PROFILE_LABELS.get(risk_key, risk_key)
    risk_hint = risk_profile_brief(risk_key)
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
            theme_summary = " / ".join(f"{item.theme_rank}.{item.theme_name}" for item in window.theme_heat_rows[:3]) or "暂无"
            buy_ready_count = int(build_meta.get("buy_ready_count", 0) or 0)
            rejected_count = int(build_meta.get("rejected_count", 0) or 0)
            portfolio_health_text = str(build_meta.get("portfolio_health_text", "") or "组合回测待生成")
            strategy_execution_focus = str(build_meta.get("strategy_execution_focus", "") or "")
            strategy_execution_detail = str(build_meta.get("strategy_execution_detail", "") or "")
            lines = [
                "今日算法优先候选：",
                f"- 风险档位：{risk_label} | {risk_hint}",
                f"- 股票：{top.stock_name} ({top.stock_id} / {top.symbol})",
                f"- 题材：{top.theme_name or '未分类'}，题材排名第 {top.theme_rank}，龙头级别：{window._display_leader_level(top.leader_level)}",
                f"- 主线题材：{theme_summary}",
                f"- 本轮过滤：{buy_ready_count} 只可执行 / {rejected_count} 只被拦截",
                f"- 组合视角：{portfolio_health_text}",
            ]
            if strategy_execution_focus:
                lines.append(f"- 战法执行：{strategy_execution_focus}")
                if strategy_execution_detail:
                    lines.append(f"- 降权解释：{strategy_execution_detail}")
            lines.extend(
                [
                    f"- 组合适配：{float(getattr(top, 'portfolio_fit_score', 0.0) or 0.0):.1f} | 分散度：{float(getattr(top, 'diversification_score', 0.0) or 0.0):.1f}",
                    f"- 总分：{top.total_score:.1f}",
                    f"- 逻辑：{top.rationale}",
                    f"- 催化：{top.catalyst or '暂无外部催化，偏技术面驱动'}",
                ]
            )
            window.daily_pool_text.setPlainText("\n".join(lines))
        else:
            window.daily_pool_text.setPlainText(
                "\n".join(
                    [
                        "当前还没有生成机会池。",
                        "- 请先扫描股票池。",
                        "- 可选：导入股票资料 CSV，补全股票名称、行业和龙头标记。",
                        "- 可选：导入消息面 CSV，增强机会排序。",
                    ]
                )
            )

    if hasattr(window, "recommend_status_label"):
        top_theme = build_meta.get("top_theme", "") or (window.theme_heat_rows[0].theme_name if window.theme_heat_rows else "未分类")
        rejected_count = int(build_meta.get("rejected_count", 0) or 0)
        portfolio_return = float(build_meta.get("portfolio_return", 0.0) or 0.0)
        status_text = (
            f"机会池已生成：{len(window.daily_pool_rows)} 只候选，风险档位 {risk_label}，当前主线题材 {top_theme}，组合回测 {portfolio_return:.2%}，拦截 {rejected_count} 只。"
        )
        strategy_execution_focus = str(build_meta.get("strategy_execution_focus", "") or "")
        if strategy_execution_focus:
            status_text = f"{status_text} | 战法 {strategy_execution_focus}"
        window.recommend_status_label.setText(status_text)

    if hasattr(window, "_update_recommend_empty_state"):
        window._update_recommend_empty_state()

    rejected_count = int(build_meta.get("rejected_count", 0) or 0)
    window._append_runtime_log(
        f"机会池已生成：{len(window.daily_pool_rows)} 只候选，风险档位 {risk_label}，拦截 {rejected_count} 只"
    )
    window._refresh_trade_plan()
    if hasattr(window, "daily_pool_table") and window.daily_pool_rows and window.daily_pool_table.rowCount() > 0:
        window.daily_pool_table.selectRow(0)
        if hasattr(window, "_refresh_recommend_focus_status"):
            window._refresh_recommend_focus_status()
    window._refresh_board_mode()


def apply_scan_universe_result(window, folder, payload) -> None:
    if len(payload) >= 6:
        rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol, summaries, scan_warnings = payload
    else:
        rows, bars_by_symbol, analyses_by_symbol, paths_by_symbol, summaries = payload
        scan_warnings = []

    window.scan_rows = rows
    window.universe_bars = bars_by_symbol
    window.universe_analyses = analyses_by_symbol
    window.paths_by_symbol = paths_by_symbol
    window.backtest_summaries = summaries
    window.last_scan_warnings = list(scan_warnings or [])
    window.state.universe_dir = str(folder)

    if hasattr(window, "universe_label"):
        window.universe_label.setText(f"当前股票池：{folder}")
    if hasattr(window, "scan_summary_label"):
        warning_suffix = f" | 跳过 {len(scan_warnings)} 个异常文件" if scan_warnings else ""
        window.scan_summary_label.setText(f"已扫描 {len(bars_by_symbol)} 只股票，生成 {len(rows)} 条策略信号{warning_suffix}")

    window._append_runtime_log(f"扫描完成：{len(bars_by_symbol)} 只股票，{len(rows)} 条信号")
    for warning in list(scan_warnings or [])[:3]:
        window._append_runtime_log(f"扫描跳过：{warning}")

    window._fill_scan_rows()
    window._fill_backtest_summaries()
    window._refresh_intraday_monitor()
    force_sync = bool(getattr(window, "_force_sync_daily_pool_after_scan_v81", False))
    window.refresh_daily_pool(async_mode=not force_sync)

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
    source_label = "示例模式" if result.market_name == "SAMPLE" else "东方财富直连"
    window._append_runtime_log(
        f"{source_label}：{len(result.algorithmic_pool)} 只算法池，缓存 {cache_stats['files']} 个文件 / {cache_stats['bytes'] / 1024:.1f} KB"
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

    if result.market_name == "SAMPLE":
        window.load_sample_reference_data()
        window.market_data_source = "sample"
        window.last_market_error = ""
        if hasattr(window, "_refresh_shell_header"):
            window._refresh_shell_header()
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("远程行情不可用，已自动切换到示例模式")
        window._refresh_overview_side_panels([])
        window._refresh_market_source_status(["- 当前来源：示例数据", "- 模式：本地兜底"])
        return

    if not result.algorithmic_pool:
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("本次刷新成功，但暂未生成可用算法池，请稍后再试。")
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
    window._refresh_broker_status(extra=f"市场候选：{len(result.algorithmic_pool)} 只")

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
            f"{result.market_name} | 算法池 {len(result.algorithmic_pool)} 只 | 更新于 {result.generated_at}"
        )
    state = feed_state or {}
    window.market_data_source = state.get("source", "remote") or "remote"
    window.last_market_success_at = result.generated_at
    window.last_market_error = state.get("error", "") or ""
    if hasattr(window, "_refresh_shell_header"):
        window._refresh_shell_header()
    window._refresh_market_source_status(["- 数据源已连接", f"- 当前模式：{window._market_source_mode_label()}"])


def handle_market_refresh_error(window, message, quiet, *, show_error_dialog_fn) -> None:
    window._append_runtime_log(f"市场刷新失败：{message}", "ERROR")
    window.market_data_source = "unknown"
    if hasattr(window, "market_status_label"):
        window.market_status_label.setText(f"行情刷新失败：{message}")
    window.last_market_error = message
    if hasattr(window, "_refresh_shell_header"):
        window._refresh_shell_header()

    help_lines = [
        "当前未成功获取市场数据。",
        "",
        "排查建议：",
        "- 检查东方财富接口当前是否可访问。",
        "- 检查本机网络或代理是否拦截行情请求。",
        "- 如果是首次启动，先手动刷新生成本地缓存。",
        "",
        "可临时处理：",
        "- 切换到仅缓存模式。",
        "- 使用示例模式先查看界面联动。",
        "- 稍后重试，等待行情接口恢复。",
    ]
    if hasattr(window, "market_leaderboard_text") and not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.market_leaderboard_text.setPlainText("\n".join(help_lines))
    if hasattr(window, "market_theme_brief_text") and not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.market_theme_brief_text.setPlainText("主线题材 / 主题摘要\n\n当前暂无可用市场数据。")
    window._refresh_market_source_status(["- 数据源状态：异常", "- 已进入失败兜底流程"])
    if not getattr(window.market_screen_result, "algorithmic_pool", []):
        window.load_sample_reference_data()
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("远程行情暂不可用，已自动加载本地示例数据")
    if not quiet:
        show_error_dialog_fn(window, "行情刷新失败", message)


def handle_daily_pool_error(window, message, *, show_error_dialog_fn) -> None:
    if hasattr(window, "recommend_status_label"):
        window.recommend_status_label.setText(f"机会池生成失败：{message}")
    window._append_runtime_log(f"机会池生成失败：{message}", "ERROR")
    show_error_dialog_fn(window, "机会池生成失败", message)


def handle_scan_error(window, message, quiet, *, show_error_dialog_fn) -> None:
    if hasattr(window, "scan_summary_label"):
        window.scan_summary_label.setText(f"扫描失败：{message}")
    window._append_runtime_log(f"扫描失败：{message}", "ERROR")
    if not quiet:
        show_error_dialog_fn(window, "扫描失败", message)


def refresh_license_status_view(window, *, datetime_cls) -> None:
    if not hasattr(window, "license_status_text"):
        return

    started = window.state.trial_started_at or datetime_cls.now().date().isoformat()
    try:
        start_date = datetime_cls.strptime(started, "%Y-%m-%d").date()
    except ValueError:
        start_date = datetime_cls.now().date()

    days_used = max((datetime_cls.now().date() - start_date).days, 0)
    remaining = max(14 - days_used, 0)
    capabilities = window._license_capabilities()
    plan = capabilities["plan"]
    risk_key = getattr(window.state, "strategy_risk_profile", "standard")
    risk_label = RISK_PROFILE_LABELS.get(risk_key, risk_key)

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

    lines.extend(
        [
            f"风险档位：{risk_label}",
            f"档位说明：{risk_profile_brief(risk_key)}",
            f"档位对比：{risk_profile_comparison_text()}",
            f"关注题材：{', '.join(window.state.focus_themes) if window.state.focus_themes else '未设置'}",
            f"主线题材阈值：前 {window.state.strategy_top_theme_limit}",
            f"题材加权：{float(capabilities['focus_theme_boost']):.0f}",
            f"盘前模板：{window.state.daily_plan_template}",
            f"模板仅关注题材：{'是' if window.state.daily_plan_focus_only else '否'}",
            f"盘前股票池上限：{min(window.state.daily_plan_candidate_limit, int(capabilities['daily_plan_export_limit']))}",
            f"市场历史回看深度：{int(capabilities['market_history_limit'])}",
            f"监控摘要容量：{int(capabilities['monitor_summary_limit'])}",
            "自动盘前报告："
            + (
                "已开启"
                if window.state.auto_daily_plan_export and bool(capabilities["auto_daily_plan_export"])
                else "未开启"
            ),
        ]
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


def append_order_result_entry(window, line: str) -> None:
    window.order_submission_log.append(line.rstrip())
    window.order_submission_log = window.order_submission_log[-200:]
    window.order_result_text.setPlainText("\n".join(window.order_submission_log) + "\n")
    window._refresh_trade_recap()


def append_submission_record_entry(
    window,
    *,
    timestamp: str,
    order_status: str,
    fill_status: str,
    order_id: str = "",
    symbol: str,
    side: str,
    price: str,
    quantity: str,
    failure_reason: str,
    message: str,
    planned_price: str = "",
    planned_quantity: str = "",
    planned_stop_price: str = "",
    planned_target_price: str = "",
    strategy_name: str = "",
    opportunity_tier: str = "",
    planned_risk_reward_ratio: str = "",
    portfolio_fit_score: str = "",
    diversification_score: str = "",
    concentration_penalty_score: str = "",
    fill_price: str = "",
    fill_quantity: str = "",
) -> None:
    window.order_submission_records.append(
        {
            "timestamp": timestamp,
            "order_status": order_status,
            "fill_status": fill_status,
            "order_id": str(order_id or ""),
            "symbol": symbol,
            "side": side,
            "price": price,
            "quantity": quantity,
            "failure_reason": failure_reason,
            "message": message,
            "planned_price": str(planned_price or ""),
            "planned_quantity": str(planned_quantity or ""),
            "planned_stop_price": str(planned_stop_price or ""),
            "planned_target_price": str(planned_target_price or ""),
            "strategy_name": str(strategy_name or ""),
            "opportunity_tier": str(opportunity_tier or ""),
            "planned_risk_reward_ratio": str(planned_risk_reward_ratio or ""),
            "portfolio_fit_score": str(portfolio_fit_score or ""),
            "diversification_score": str(diversification_score or ""),
            "concentration_penalty_score": str(concentration_penalty_score or ""),
            "fill_price": str(fill_price or ""),
            "fill_quantity": str(fill_quantity or ""),
        }
    )
    if symbol:
        if order_status == "FAILED" or fill_status == "REJECTED":
            window.execution_status_by_symbol[symbol] = "提交失败"
        elif order_status == "SUBMITTED":
            window.execution_status_by_symbol[symbol] = "已提交"
    if hasattr(window, "daily_pool_table"):
        window._populate_filtered_daily_pool_table()
    if hasattr(window, "trade_plan_table"):
        window._refresh_trade_plan()
    window.order_submission_records = window.order_submission_records[-500:]
    window._refresh_submission_table()
    window._refresh_trade_recap()
