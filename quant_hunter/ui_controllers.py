from __future__ import annotations

from quant_hunter.backtest import BacktestParams, PortfolioBacktester
from quant_hunter.broker import build_submission_intents
from quant_hunter.broker_status import build_broker_execution_summary
from quant_hunter.models import OrderIntent, PaperTradingState
from quant_hunter.paper_trading import build_strategy_rotation_snapshot
from quant_hunter.risk import (
    RISK_PROFILE_AGGRESSIVE,
    RISK_PROFILE_CONSERVATIVE,
    RISK_PROFILE_STANDARD,
    normalize_risk_profile,
)
from quant_hunter.ui_window_paper_experiment_patches import paper_strategy_experiment_bridge_v45


def _submission_recommendation_for_symbol(window, symbol: str):
    for item in list(getattr(window, "daily_pool_rows", []) or []):
        if str(getattr(item, "symbol", "") or "") == symbol:
            return item
    return None


def build_order_submission_experiment_context(window) -> dict[str, object]:
    strategy_name = ""
    intents = list(getattr(window, "order_intents", []) or [])
    preferred_symbols: list[str] = []
    for intent in intents:
        symbol = str(getattr(intent, "symbol", "") or "")
        if not symbol:
            continue
        if str(getattr(intent, "side", "") or "").upper() == "BUY":
            preferred_symbols.append(symbol)
    for intent in intents:
        symbol = str(getattr(intent, "symbol", "") or "")
        if symbol and symbol not in preferred_symbols:
            preferred_symbols.append(symbol)

    for symbol in preferred_symbols:
        recommendation = _submission_recommendation_for_symbol(window, symbol)
        candidate = str(getattr(recommendation, "primary_strategy", "") or "").strip()
        if candidate:
            strategy_name = candidate
            break

    if not strategy_name:
        current_focus_fn = getattr(window, "_current_recommend_focus", None)
        if callable(current_focus_fn):
            current_focus = current_focus_fn()
            strategy_name = str(getattr(current_focus, "primary_strategy", "") or "").strip()

    if not strategy_name:
        strategy_name = "掘龙决策"

    paper_state = getattr(window, "paper_trading_state", getattr(getattr(window, "state", None), "paper_trading_state", None))
    if not isinstance(paper_state, PaperTradingState):
        paper_state = PaperTradingState()

    return {
        "strategy_name": strategy_name,
        "experiment_bridge": paper_strategy_experiment_bridge_v45(paper_state, strategy_name),
    }


def save_broker_profile_controller(window, *, info_dialog_fn) -> None:
    window.state.broker_profile = window.current_broker_profile()
    window.save_state()
    window._refresh_broker_status()
    info_dialog_fn(window, "提示", "账户配置已保存。")


def create_broker_templates_controller(window, *, adapter_cls) -> None:
    files = adapter_cls().create_templates(window.current_broker_profile().export_dir)
    window._refresh_broker_status(extra="\n".join(f"已生成模板：{item}" for item in files))


def validate_broker_connection_controller(window, *, adapter_cls, info_dialog_fn, warning_dialog_fn) -> bool:
    profile = window.current_broker_profile()
    if hasattr(window, "state"):
        window.state.broker_profile = profile
    if hasattr(window, "save_state"):
        window.save_state()

    adapter = adapter_cls()
    env = adapter.diagnose_environment(profile)
    issues: list[str] = []
    checks: list[str] = []

    if str(getattr(profile, "mode", "") or "") == "sdk":
        if not str(getattr(profile, "account_id", "") or "").strip():
            issues.append("缺少账户 ID。")
        if not str(getattr(profile, "token", "") or "").strip():
            issues.append("缺少 SDK Token。")
        if not str(getattr(profile, "strategy_id", "") or "").strip():
            issues.append("缺少策略 ID。")
        if env.get("direct_ready"):
            checks.append("当前环境已满足直接 SDK 调用条件。")
        elif env.get("bridge_ready"):
            checks.append("当前环境已满足桥接 SDK 调用条件，可通过 Python 3.12 + GM SDK 执行。")
        else:
            issues.append("GM SDK 当前未就绪，请先检查桥接 Python 和 gm.api 环境。")
    else:
        checks.append("当前为导出模式，不会直接触发实盘下单。")

    if getattr(profile, "test_submit_only", False):
        whitelist = str(getattr(profile, "test_submit_symbol_whitelist", "") or "").strip()
        checks.append(f"测试单买入上限：{float(getattr(profile, 'test_submit_max_amount', 10000.0) or 10000.0):,.0f}")
        if whitelist:
            checks.append(f"测试白名单：{whitelist}")
        else:
            issues.append("测试单模式已开启，但测试白名单未填写。")
    else:
        checks.append("测试单模式：已关闭。")

    checks.append(f"提交回放自动导出：{'开启' if getattr(profile, 'auto_export_submission_records', True) else '关闭'}")

    lines = [
        "联调预检",
        f"- 交易模式：{getattr(profile, 'mode', '') or '--'}",
        f"- SDK 模块：{env.get('sdk_module', '--')}",
        f"- 主程序 Python：{env.get('python_version', '--')}",
    ]
    if env.get("bridge_python"):
        lines.append(f"- 桥接 Python：{env.get('bridge_python')}")
    if checks:
        lines.extend(["", "通过项"])
        lines.extend(f"- {item}" for item in checks)
    if issues:
        lines.extend(["", "待修复"])
        lines.extend(f"- {item}" for item in issues)

    summary = "\n".join(lines)
    window._refresh_broker_status(extra=summary)
    if issues:
        warning_dialog_fn(window, "连接校验未通过", summary)
        return False
    info_dialog_fn(window, "连接校验通过", summary)
    return True


def generate_order_suggestions_controller(window, *, adapter_cls, info_dialog_fn, error_dialog_fn) -> None:
    plan = getattr(window, "current_trade_plan", None)
    if not getattr(plan, "decisions", []):
        info_dialog_fn(window, "提示", "当前没有通过主线闸门的交易计划，请先生成推荐池和交易计划。")
        return
    try:
        per_trade_budget = float(window.per_trade_budget_input.text().strip())
    except ValueError:
        error_dialog_fn(window, "参数错误", "单笔预算必须填写数字。")
        return

    decisions = list(getattr(plan, "decisions", []) or [])
    if window.state.watchlist:
        watchlist = set(window.state.watchlist)
        decisions = [item for item in decisions if item.symbol in watchlist]

    order_intents: list[OrderIntent] = []
    for item in decisions:
        sizing_budget = float(getattr(item, "suggested_budget", 0.0) or 0.0)
        if sizing_budget <= 0:
            sizing_budget = per_trade_budget
        quantity = int(sizing_budget / item.planned_entry) if item.planned_entry > 0 else 0
        quantity = (quantity // 100) * 100
        if quantity < 100 or item.planned_stop <= 0 or item.planned_target <= 0:
            continue
        order_intents.append(
            OrderIntent(
                symbol=item.symbol,
                side=item.action,
                price=round(item.planned_entry, 3),
                quantity=quantity,
                stop_price=round(item.planned_stop, 3),
                target_price=round(item.planned_target, 3),
                signal_date="计划股",
                reason=item.rationale,
            )
        )

    window.order_intents = order_intents
    window._fill_orders()
    if not window.order_intents:
        window._refresh_broker_status(extra="当前交易计划中暂无可执行委托，请先检查预算、窗口和主线闸门。")


def export_order_plan_controller(window, *, adapter_cls, datetime_cls) -> None:
    if not window.order_intents:
        window.generate_order_suggestions()
    if not window.order_intents:
        return
    output = adapter_cls().export_order_plan(window.order_intents, window.current_broker_profile().export_dir)
    line = f"[{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}] 已导出委托计划：{output}"
    window._append_order_result(line)
    window._refresh_broker_status(extra=f"已导出委托计划：{output}")


def export_order_result_log_controller(window, *, adapter_cls, datetime_cls, info_dialog_fn) -> None:
    if not window.order_submission_records:
        info_dialog_fn(window, "提示", "当前还没有可导出的提交记录。")
        return
    output = adapter_cls().export_submission_records(
        window.order_submission_records,
        window.current_broker_profile().export_dir,
    )
    line = f"[{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}] 已导出提交日志：{output}"
    window._append_order_result(line)
    window._refresh_broker_status(extra=f"已导出提交日志：{output}")


def sync_broker_via_sdk_controller(window, quiet: bool, *, adapter_cls, error_dialog_fn) -> None:
    profile = window.current_broker_profile()
    try:
        cash, holdings = adapter_cls().sync_account_via_sdk(profile)
    except Exception as exc:
        if not quiet:
            error_dialog_fn(window, "SDK 同步失败", str(exc))
        return
    window.cash_snapshot = cash
    window.holdings = holdings
    window._fill_holdings()
    window._refresh_broker_status(extra="已通过 SDK 同步资金和持仓。")


def generate_sdk_strategy_script_controller(window, *, adapter_cls, error_dialog_fn) -> None:
    if not window.order_intents:
        window.generate_order_suggestions()
    if not window.order_intents:
        return
    profile = window.current_broker_profile()
    if not profile.token or not profile.strategy_id or not profile.account_id:
        error_dialog_fn(window, "字段缺失", "请先填写 token、strategy_id 和 account_id。")
        return
    path = adapter_cls().generate_gm_strategy_script(profile, window.order_intents, profile.export_dir)
    window._refresh_broker_status(extra=f"已生成 GM 实盘脚本：{path}")


def prepare_order_submission_controller(window, *, adapter_cls, confirmation_dialog_cls):
    if not window.order_intents:
        window.generate_order_suggestions()
    if not window.order_intents:
        return None
    profile = window.current_broker_profile()
    adapter = adapter_cls()
    state = getattr(window, "state", None)
    summary, _env = build_broker_execution_summary(
        profile=profile,
        adapter=adapter,
        order_intents=window.order_intents,
        holdings=window.holdings,
        cash_snapshot=window.cash_snapshot,
        recommendations=getattr(window, "daily_pool_rows", []),
        risk_profile=getattr(state, "strategy_risk_profile", "standard"),
    )
    window.last_broker_execution_summary = summary
    blockers = list(summary.get("blockers", []))
    if blockers:
        window._refresh_broker_status(extra="提交前硬拦截：\n" + "\n".join(f"- {item}" for item in blockers[:4]))
        return None
    experiment_context = build_order_submission_experiment_context(window)
    confirmed = confirmation_dialog_cls.confirm(
        profile=profile,
        intents=window.order_intents,
        adapter=adapter,
        holdings=window.holdings,
        cash_snapshot=window.cash_snapshot,
        recommendations=getattr(window, "daily_pool_rows", []),
        strategy_name=experiment_context["strategy_name"],
        experiment_bridge=experiment_context["experiment_bridge"],
        parent=window,
    )
    if not confirmed:
        window._refresh_broker_status(extra="本次提交已取消，仍保留委托建议供你继续复核。")
        return None
    return profile, adapter


def handle_order_submission_failure_controller(
    window,
    *,
    adapter,
    profile,
    submit_time: str,
    exc: Exception,
    warning_dialog_fn,
) -> None:
    fallback_path = adapter.export_order_plan(window.order_intents, profile.export_dir)
    failure_lines = [
        f"[{submit_time}] SDK 下单失败：{exc}",
        f"[{submit_time}] 已回退导出 CSV：{fallback_path}",
    ]
    for item in window.order_intents:
        window._append_submission_record(
            timestamp=submit_time,
            order_status="FAILED",
            fill_status="REJECTED",
            symbol=item.symbol,
            side=item.side,
            price=f"{item.price:.3f}",
            quantity=str(item.quantity),
            failure_reason=str(exc),
            message=str(exc),
        )
    for line in failure_lines:
        window._append_order_result(line)
    window._refresh_broker_status(extra="\n".join(failure_lines))
    warning_dialog_fn(window, "下单失败", f"{exc}\n\n已回退导出 CSV：\n{fallback_path}")


def handle_order_submission_success_controller(
    window,
    *,
    results: list[str],
    submit_time: str,
    info_dialog_fn,
) -> None:
    success_lines = [f"[{submit_time}] SDK 下单完成：共 {len(results)} 笔"]
    success_lines.extend(f"[{submit_time}] {item}" for item in results)
    for item, result in zip(window.order_intents, results):
        window._append_submission_record(
            timestamp=submit_time,
            order_status="SUBMITTED",
            fill_status="PENDING",
            symbol=item.symbol,
            side=item.side,
            price=f"{item.price:.3f}",
            quantity=str(item.quantity),
            failure_reason="",
            message=result,
        )
    for line in success_lines:
        window._append_order_result(line)
    window.sync_broker_via_sdk(quiet=True)
    window._refresh_broker_status(extra="\n".join(success_lines))
    info_dialog_fn(window, "下单完成", "\n".join(results))


def confirm_and_submit_orders_controller(
    window,
    *,
    adapter_cls,
    confirmation_dialog_cls,
    datetime_cls,
    info_dialog_fn,
    warning_dialog_fn,
) -> None:
    prepared = prepare_order_submission_controller(
        window,
        adapter_cls=adapter_cls,
        confirmation_dialog_cls=confirmation_dialog_cls,
    )
    if prepared is None:
        return
    profile, adapter = prepared
    submit_time = datetime_cls.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        results = adapter.submit_order_intents(profile, window.order_intents)
    except Exception as exc:
        handle_order_submission_failure_controller(
            window,
            adapter=adapter,
            profile=profile,
            submit_time=submit_time,
            exc=exc,
            warning_dialog_fn=warning_dialog_fn,
        )
        return
    handle_order_submission_success_controller(
        window,
        results=results,
        submit_time=submit_time,
        info_dialog_fn=info_dialog_fn,
    )


def prepare_order_submission_controller(window, *, adapter_cls, confirmation_dialog_cls):
    if not window.order_intents:
        window.generate_order_suggestions()
    if not window.order_intents:
        return None
    profile = window.current_broker_profile()
    adapter = adapter_cls()
    state = getattr(window, "state", None)
    summary, _env = build_broker_execution_summary(
        profile=profile,
        adapter=adapter,
        order_intents=window.order_intents,
        holdings=window.holdings,
        cash_snapshot=window.cash_snapshot,
        recommendations=getattr(window, "daily_pool_rows", []),
        risk_profile=getattr(state, "strategy_risk_profile", "standard"),
    )
    window.last_broker_execution_summary = summary
    blockers = list(summary.get("blockers", []))
    if blockers:
        window._refresh_broker_status(extra="提交前硬拦截：\n" + "\n".join(f"- {item}" for item in blockers[:4]))
        return None

    submission_intents, guard_notes, guard_blockers = build_submission_intents(window.order_intents, profile)
    if guard_blockers:
        window._refresh_broker_status(extra="测试单闸门拦截：\n" + "\n".join(f"- {item}" for item in guard_blockers[:4]))
        return None

    setattr(window, "last_submission_guard_notes", list(guard_notes))
    if guard_notes:
        window._refresh_broker_status(extra="测试单闸门：\n" + "\n".join(f"- {item}" for item in guard_notes[:4]))

    experiment_context = build_order_submission_experiment_context(window)
    confirmed = confirmation_dialog_cls.confirm(
        profile=profile,
        intents=submission_intents,
        adapter=adapter,
        holdings=window.holdings,
        cash_snapshot=window.cash_snapshot,
        recommendations=getattr(window, "daily_pool_rows", []),
        strategy_name=experiment_context["strategy_name"],
        experiment_bridge=experiment_context["experiment_bridge"],
        guard_notes=guard_notes,
        parent=window,
    )
    if not confirmed:
        window._refresh_broker_status(extra="本次提交已取消，仍保留委托建议供你继续复核。")
        return None
    return profile, adapter, submission_intents, guard_notes


def handle_order_submission_failure_controller(
    window,
    *,
    adapter,
    profile,
    submitted_intents: list[OrderIntent],
    submit_time: str,
    exc: Exception,
    warning_dialog_fn,
) -> None:
    fallback_path = adapter.export_order_plan(submitted_intents, profile.export_dir)
    failure_lines = [
        f"[{submit_time}] SDK 下单失败：{exc}",
        f"[{submit_time}] 已回退导出 CSV：{fallback_path}",
    ]
    for item in submitted_intents:
        window._append_submission_record(
            timestamp=submit_time,
            order_status="FAILED",
            fill_status="REJECTED",
            symbol=item.symbol,
            side=item.side,
            price=f"{item.price:.3f}",
            quantity=str(item.quantity),
            failure_reason=str(exc),
            message=str(exc),
        )
    for line in failure_lines:
        window._append_order_result(line)
    window._refresh_broker_status(extra="\n".join(failure_lines))
    warning_dialog_fn(window, "下单失败", f"{exc}\n\n已回退导出 CSV：\n{fallback_path}")


def handle_order_submission_success_controller(
    window,
    *,
    submitted_intents: list[OrderIntent],
    results: list[str],
    submit_time: str,
    guard_notes: list[str] | None,
    info_dialog_fn,
) -> None:
    success_lines = [f"[{submit_time}] SDK 下单完成：共 {len(results)} 笔"]
    success_lines.extend(f"[{submit_time}] {note}" for note in list(guard_notes or []))
    success_lines.extend(f"[{submit_time}] {item}" for item in results)
    for item, result in zip(submitted_intents, results):
        window._append_submission_record(
            timestamp=submit_time,
            order_status="SUBMITTED",
            fill_status="PENDING",
            symbol=item.symbol,
            side=item.side,
            price=f"{item.price:.3f}",
            quantity=str(item.quantity),
            failure_reason="",
            message=result,
        )
    for line in success_lines:
        window._append_order_result(line)
    window.sync_broker_via_sdk(quiet=True)
    window._refresh_broker_status(extra="\n".join(success_lines))
    info_dialog_fn(window, "下单完成", "\n".join(results))


def persist_submission_artifacts_controller(window, *, adapter_cls, datetime_cls) -> str:
    if hasattr(window, "save_state"):
        window.save_state()
    profile = window.current_broker_profile()
    if not getattr(profile, "auto_export_submission_records", True):
        return ""
    records = list(getattr(window, "order_submission_records", []) or [])
    if not records:
        return ""
    try:
        output = adapter_cls().export_submission_records(records, profile.export_dir)
    except Exception as exc:
        if hasattr(window, "_append_order_result"):
            line = f"[{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}] 自动导出提交回放失败：{exc}"
            window._append_order_result(line)
        if hasattr(window, "save_state"):
            window.save_state()
        return ""
    if hasattr(window, "_append_order_result"):
        line = f"[{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}] 已自动导出提交回放：{output}"
        window._append_order_result(line)
    if hasattr(window, "save_state"):
        window.save_state()
    return str(output)


def confirm_and_submit_orders_controller(
    window,
    *,
    adapter_cls,
    confirmation_dialog_cls,
    datetime_cls,
    info_dialog_fn,
    warning_dialog_fn,
) -> None:
    prepared = prepare_order_submission_controller(
        window,
        adapter_cls=adapter_cls,
        confirmation_dialog_cls=confirmation_dialog_cls,
    )
    if prepared is None:
        return
    profile, adapter, submitted_intents, guard_notes = prepared
    submit_time = datetime_cls.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        results = adapter.submit_order_intents(profile, submitted_intents)
    except Exception as exc:
        handle_order_submission_failure_controller(
            window,
            adapter=adapter,
            profile=profile,
            submitted_intents=submitted_intents,
            submit_time=submit_time,
            exc=exc,
            warning_dialog_fn=warning_dialog_fn,
        )
        persist_submission_artifacts_controller(window, adapter_cls=adapter_cls, datetime_cls=datetime_cls)
        return
    handle_order_submission_success_controller(
        window,
        submitted_intents=submitted_intents,
        results=results,
        submit_time=submit_time,
        guard_notes=guard_notes,
        info_dialog_fn=info_dialog_fn,
    )
    persist_submission_artifacts_controller(window, adapter_cls=adapter_cls, datetime_cls=datetime_cls)


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
    bars_by_symbol = {symbol: list(items) for symbol, items in window.universe_bars.items()}
    analyses_by_symbol = {symbol: list(items) for symbol, items in window.universe_analyses.items()}
    backtest_summaries = list(window.backtest_summaries)
    stock_profiles = dict(window.stock_profiles)
    news_catalysts = {symbol: list(items) for symbol, items in window.news_catalysts.items()}
    theme_aliases = dict(window.theme_aliases)
    capabilities = window._license_capabilities()
    paper_state = getattr(window.state, "paper_trading_state", PaperTradingState())
    rotation_rows = build_strategy_rotation_snapshot(paper_state)
    strategy_bias_by_name = {
        str(item.get("strategy_name", "") or ""): float(item.get("rotation_score", 0.0) or 0.0)
        for item in rotation_rows
        if str(item.get("strategy_name", "") or "")
    }
    portfolio_backtest = None
    if bars_by_symbol and analyses_by_symbol:
        try:
            portfolio_backtest = PortfolioBacktester(
                backtest_params=BacktestParams.realistic_cn_equity(
                    max_positions=min(max(len(bars_by_symbol), 1), 5),
                    max_position_fraction=0.42 if len(bars_by_symbol) <= 1 else 0.22,
                    max_volume_participation=0.12,
                )
            ).run(bars_by_symbol, analyses_by_symbol)
        except Exception:
            portfolio_backtest = None

    def build_pool():
        focus_themes = list(window.state.focus_themes)
        focus_theme_boost = float(capabilities["focus_theme_boost"])
        current_risk_profile = getattr(window.state, "strategy_risk_profile", "standard")

        def _build_for_profile(profile_key: str):
            builder = daily_pool_builder_cls(
                stock_profiles,
                news_catalysts,
                theme_aliases,
                focus_themes=focus_themes,
                focus_theme_boost=focus_theme_boost,
                strategy_bias_by_name=strategy_bias_by_name,
                risk_profile=profile_key,
            )
            rows = builder.build(
                scan_rows,
                analyses_by_symbol,
                backtest_summaries,
                portfolio_backtest=portfolio_backtest,
            )
            return rows, dict(getattr(builder, "last_build_meta", {}) or {})

        rows, meta = _build_for_profile(current_risk_profile)
        snapshots: dict[str, dict[str, object]] = {}
        for profile_key in (RISK_PROFILE_CONSERVATIVE, RISK_PROFILE_STANDARD, RISK_PROFILE_AGGRESSIVE):
            snapshot_rows, snapshot_meta = (rows, dict(meta)) if profile_key == current_risk_profile else _build_for_profile(profile_key)
            snapshot_meta["display_count"] = int(snapshot_meta.get("display_count", len(snapshot_rows)) or len(snapshot_rows))
            snapshots[profile_key] = snapshot_meta
        meta["profile_snapshots"] = snapshots
        return rows, meta

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
        for item in window.optimization_results:
            lines.append(
                f"   绋冲仴={item.robustness_score:.0%} | 鏍锋湰澶栨敹鐩?={item.avg_out_of_sample_return:.2%} | "
                f"鏈€宸獥鍙?={item.avg_worst_window_return:.2%} | 鏀剁泭娉㈠姩={item.avg_return_std:.2%} | "
                f"姝ｆ敹绐楀彛={item.avg_positive_window_ratio:.0%}"
            )
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
    selected_risk_profile = (
        str(window.strategy_risk_profile_combo.currentData() or "standard")
        if hasattr(window, "strategy_risk_profile_combo")
        else getattr(window.state, "strategy_risk_profile", "standard")
    )
    window.state.strategy_risk_profile = normalize_risk_profile(selected_risk_profile)
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
    info_dialog_fn(window, "保存成功", "策略配置已保存，并已刷新推荐与监控。")


def switch_strategy_risk_profile_controller(window, profile_key: str, *, info_dialog_fn) -> None:
    normalized = normalize_risk_profile(profile_key)
    combo = getattr(window, "strategy_risk_profile_combo", None)
    if combo is not None and hasattr(combo, "count") and hasattr(combo, "itemData") and hasattr(combo, "setCurrentIndex"):
        for index in range(combo.count()):
            if combo.itemData(index) == normalized:
                combo.setCurrentIndex(index)
                break
    else:
        window.state.strategy_risk_profile = normalized
    save_strategy_preferences_controller(window, info_dialog_fn=info_dialog_fn)


def switch_license_plan_controller(window, plan: str, *, datetime_cls) -> None:
    normalized = (plan or "TRIAL").upper()
    window.state.license_plan = normalized
    if normalized == "TRIAL":
        window.state.trial_started_at = datetime_cls.now().date().isoformat()
    window.save_state()
    window._refresh_license_status_view()
