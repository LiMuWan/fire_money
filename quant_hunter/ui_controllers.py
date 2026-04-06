from __future__ import annotations


def run_background_job_controller(
    window,
    job_name: str,
    fn,
    on_success,
    on_error,
    *,
    background_task_cls,
    registry,
    perf_counter_fn,
) -> bool:
    if window._is_job_running(job_name):
        window._append_runtime_log(f"任务跳过：{job_name} 正在执行", "WARN")
        window.refresh_runtime_panel()
        return False

    window.active_jobs.add(job_name)
    window.job_run_count += 1
    window.last_job_name = job_name
    window.last_job_status = "running"
    window.last_job_duration_ms = 0.0
    started_perf = perf_counter_fn()
    window.job_started_perf[job_name] = started_perf
    task = background_task_cls(fn)
    window.job_handles[job_name] = task
    registry.append(task)
    window._append_runtime_log(f"任务开始：{job_name}")

    def handle_success(result) -> None:
        duration_ms = (perf_counter_fn() - window.job_started_perf.get(job_name, started_perf)) * 1000.0
        window.job_success_count += 1
        window._record_job_result(job_name, "success", duration_ms)
        window._append_runtime_log(f"任务完成：{job_name} | {duration_ms:.0f} ms")
        on_success(result)

    def handle_error(message: str) -> None:
        duration_ms = (perf_counter_fn() - window.job_started_perf.get(job_name, started_perf)) * 1000.0
        window.job_failure_count += 1
        window._record_job_result(job_name, "failed", duration_ms, message)
        window._append_runtime_log(f"任务失败：{job_name} | {message} | {duration_ms:.0f} ms", "ERROR")
        on_error(message)

    def handle_finished() -> None:
        window.active_jobs.discard(job_name)
        window.job_handles.pop(job_name, None)
        window.job_started_perf.pop(job_name, None)
        if task in registry:
            registry.remove(task)
        window.refresh_runtime_panel()

    task.signals.succeeded.connect(handle_success)
    task.signals.failed.connect(handle_error)
    task.signals.finished.connect(handle_finished)
    window.thread_pool.start(task)
    window.refresh_runtime_panel()
    return True


def refresh_daily_pool_controller(window, async_mode: bool, *, daily_pool_builder_cls) -> None:
    scan_rows = list(window.scan_rows)
    analyses_by_symbol = {symbol: list(items) for symbol, items in window.universe_analyses.items()}
    backtest_summaries = list(window.backtest_summaries)
    stock_profiles = dict(window.stock_profiles)
    news_catalysts = {symbol: list(items) for symbol, items in window.news_catalysts.items()}
    theme_aliases = dict(window.theme_aliases)
    capabilities = window._license_capabilities()

    def build_pool():
        builder = daily_pool_builder_cls(
            stock_profiles,
            news_catalysts,
            theme_aliases,
            focus_themes=list(window.state.focus_themes),
            focus_theme_boost=float(capabilities["focus_theme_boost"]),
        )
        return builder.build(scan_rows, analyses_by_symbol, backtest_summaries)

    if async_mode:
        if hasattr(window, "recommend_status_label"):
            window.recommend_status_label.setText("正在生成每日推荐池...")
        started = window._run_background_job(
            "daily_pool",
            build_pool,
            window._apply_daily_pool_rows,
            window._handle_daily_pool_error,
        )
        if not started and hasattr(window, "recommend_status_label"):
            window.recommend_status_label.setText("推荐池仍在生成中，请稍候。")
        return

    window._apply_daily_pool_rows(build_pool())


def refresh_remote_market_controller(
    window,
    quiet: bool,
    update_chart: bool,
    async_mode: bool,
    *,
    market_screen_result_cls,
    cache_only_feed_cls,
    remote_market_screener_cls,
    datetime_cls,
) -> None:
    params = window.strategy_params()
    capabilities = window._license_capabilities()
    mode = getattr(window, "market_data_mode", "auto")
    feed_state: dict[str, str] = {"source": "unknown", "error": ""}

    def screen_market():
        if mode == "sample":
            return market_screen_result_cls(
                market_name="示例模式",
                generated_at=datetime_cls.now().strftime("%Y-%m-%d %H:%M:%S"),
            )
        feed = cache_only_feed_cls() if mode == "cache" else None
        screener = remote_market_screener_cls(params, feed=feed)
        history_limit = int(capabilities["market_history_limit"])
        result = screener.screen_market(
            top_n=min(18, history_limit),
            prefetch_limit=max(60, history_limit * 8),
            history_limit=history_limit,
        )
        if feed is not None:
            feed_state["source"] = getattr(feed, "last_snapshot_source", "cache_only")
            feed_state["error"] = getattr(feed, "last_snapshot_error", "")
        else:
            actual_feed = getattr(screener, "feed", None)
            feed_state["source"] = getattr(actual_feed, "last_snapshot_source", "remote")
            feed_state["error"] = getattr(actual_feed, "last_snapshot_error", "")
        return result

    if async_mode:
        if hasattr(window, "market_status_label"):
            window.market_status_label.setText("正在从全市场筛选龙头候选...")
        started = window._run_background_job(
            "market_refresh",
            screen_market,
            lambda result: window._apply_market_screen_result(result, update_chart=update_chart, feed_state=feed_state),
            lambda message: window._handle_market_refresh_error(message, quiet),
        )
        if not started and hasattr(window, "market_status_label"):
            window.market_status_label.setText("算法池仍在刷新中，请稍候。")
        return

    try:
        result = screen_market()
    except Exception as exc:
        window._handle_market_refresh_error(str(exc), quiet)
        return
    window._apply_market_screen_result(result, update_chart=update_chart, feed_state=feed_state)


def run_parameter_optimization_controller(
    window,
    *,
    parameter_optimizer_cls,
    report_dir,
    info_dialog_fn,
    error_dialog_fn,
) -> None:
    if not window.universe_bars:
        info_dialog_fn(window, "提示", "请先载入股票池再运行优化。")
        return

    params = window.strategy_params()
    bars_by_symbol = {symbol: list(items) for symbol, items in window.universe_bars.items()}
    if hasattr(window, "optimization_text"):
        window.optimization_text.setPlainText("正在后台运行参数优化，请稍候...\n")

    def optimize_payload():
        optimizer = parameter_optimizer_cls(params)
        results = optimizer.optimize(bars_by_symbol, top_n=8)
        artifacts = optimizer.export_report(results, report_dir)
        return results, artifacts

    def apply_optimization(payload) -> None:
        results, artifacts = payload
        window.optimization_results = results
        lines = ["参数优化 Top 8", ""]
        for item in window.optimization_results:
            lines.append(
                f"{item.rank}. 目标值={item.objective:.4f} | 收益={item.avg_return:.2%} | "
                f"回撤={item.avg_drawdown:.2%} | 胜率={item.avg_win_rate:.2%} | 参数={item.params}"
            )
        lines.extend(["", f"报告已导出：{artifacts.markdown_path}"])
        window.optimization_text.setPlainText("\n".join(lines))
        window._append_runtime_log(f"参数优化完成：输出 {len(results)} 组结果")

    def handle_optimization_error(message: str) -> None:
        window.optimization_text.setPlainText(f"参数优化失败：{message}")
        window._append_runtime_log(f"参数优化失败：{message}", "ERROR")
        error_dialog_fn(window, "参数优化失败", message)

    started = window._run_background_job(
        "parameter_optimization",
        optimize_payload,
        apply_optimization,
        handle_optimization_error,
    )
    if not started and hasattr(window, "optimization_text"):
        window.optimization_text.setPlainText("参数优化仍在进行中，请稍候。")



def save_strategy_preferences_controller(window, *, info_dialog_fn) -> None:
    top_theme_limit, max_total_exposure, theme_drop_reduce = window._current_strategy_runtime_config()
    window.state.strategy_top_theme_limit = top_theme_limit
    window.state.strategy_max_total_exposure = max_total_exposure
    window.state.strategy_theme_drop_reduce = theme_drop_reduce
    window.state.focus_themes = window._parse_focus_themes()
    window.state.auto_daily_plan_export = (
        window.auto_daily_plan_export_checkbox.isChecked() if hasattr(window, "auto_daily_plan_export_checkbox") else False
    )
    template_name, focus_only, candidate_limit = window._current_report_template_config()
    window.state.daily_plan_template = template_name
    window.state.daily_plan_focus_only = focus_only
    window.state.daily_plan_candidate_limit = candidate_limit
    window.save_state()
    window._refresh_license_status_view()
    window.refresh_daily_pool()
    window._refresh_intraday_monitor()
    info_dialog_fn(window, "????", "???????????")
