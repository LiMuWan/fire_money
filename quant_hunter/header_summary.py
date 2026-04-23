from __future__ import annotations


def build_header_summary(
    *,
    page_key: str,
    current_name: str,
    market_value: str,
    refresh_value: str,
    focus_full: str,
    focus_compact: str,
    pulse_headline: str,
    pulse_compact: str,
    next_step: str,
    next_step_compact: str,
    meta_text: str,
    meta_compact: str,
) -> dict[str, str]:
    workspace_compact_map = {
        "overview": "总览",
        "scanner": "扫描",
        "recommend": "推荐",
        "broker": "交易",
        "detail": "复盘",
        "auth": "接入",
        "board": "看板",
        "config": "配置",
    }
    return {
        "workspace_full": current_name,
        "workspace_compact": workspace_compact_map.get(page_key, current_name),
        "focus_full": focus_full,
        "focus_compact": focus_compact,
        "market_full": market_value,
        "market_compact": market_value,
        "refresh_full": refresh_value,
        "refresh_compact": refresh_value,
        "pulse_full": pulse_headline,
        "pulse_compact": pulse_compact,
        "next_full": next_step,
        "next_compact": next_step_compact,
        "meta_full": meta_text,
        "meta_compact": meta_compact,
    }


def build_shell_status_snapshot(
    *,
    market_data_source: str,
    last_market_success_at: str,
    last_market_error: str,
    dashboard_auto: bool,
    scanner_auto: bool,
    market_refresh_running: bool,
    scan_running: bool,
    last_job_status: str,
    last_job_name: str,
    trade_decisions_count: int,
    pending_orders: int,
    submitted_orders: int,
    pool_count: int,
    blockers: list[str] | tuple[str, ...],
    warnings: list[str] | tuple[str, ...],
    last_job_finished_at: str,
) -> dict[str, str]:
    market_source_label = {
        "remote": "远端实时",
        "cache": "本地缓存",
        "cache_only": "缓存只读",
        "sample": "示例模式",
        "unknown": "等待行情接入",
    }.get(str(market_data_source or "unknown"), "等待行情接入")

    if last_market_success_at:
        market_value = f"{market_source_label} · {last_market_success_at[-8:]}"
    elif last_market_error:
        market_value = f"{market_source_label} · 异常"
    else:
        market_value = market_source_label

    if market_refresh_running or scan_running:
        refresh_value = "刷新中"
    elif dashboard_auto and scanner_auto:
        refresh_value = "双通道开启"
    elif dashboard_auto:
        refresh_value = "总览自动"
    elif scanner_auto:
        refresh_value = "扫描自动"
    else:
        refresh_value = "手动"

    runtime_value = {
        "running": "任务执行中",
        "success": "最近成功",
        "failed": "最近失败",
        "idle": "空闲",
    }.get(str(last_job_status or "idle"), "空闲")
    if last_job_name and str(last_job_status or "") == "running":
        runtime_value = str(last_job_name)

    blockers = list(blockers or [])
    warnings = list(warnings or [])
    risk_state = "红灯" if blockers else ("黄灯" if warnings else "绿灯")

    pulse_verdict = "禁止提交" if blockers else "继续复核"
    if market_refresh_running and scan_running:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 行情与扫描双线程运行中，工作台正在推进最新快照。"
    elif market_refresh_running:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 行情刷新进行中，主控台正在更新市场总览与题材脉冲。"
    elif scan_running:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 扫描任务进行中，候选池与监控焦点正在同步。"
    elif pending_orders:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 机会池 {pool_count} 只，已形成计划 {trade_decisions_count} 笔，待审委托 {pending_orders} 笔。"
    elif trade_decisions_count:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 机会池已转成交易计划，当前 {trade_decisions_count} 笔可进入审查。"
    elif pool_count:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 机会池已生成 {pool_count} 只候选，正在等待计划与执行联动。"
    else:
        pulse_headline = f"系统脉冲：{pulse_verdict} | 终端正在等待市场快照、候选优先级与交易链路同步。"

    if market_refresh_running or scan_running:
        next_step = "下一动作：等待任务完成后回看主线与焦点池"
    elif blockers:
        next_step = f"下一动作：先处理阻塞项，再推进送审 | {blockers[0]}"
    elif pending_orders:
        next_step = f"下一动作：复核风险灯后送审 {pending_orders} 笔委托"
    elif trade_decisions_count:
        next_step = "下一动作：从高优先计划里选股送审"
    elif pool_count:
        next_step = "下一动作：由机会池继续生成交易计划"
    else:
        next_step = "下一动作：先建立市场快照，再生成机会池并推进交易链路"

    market_stamp = last_market_success_at or "等待行情接入"
    job_stamp = last_job_finished_at or "待执行"
    meta_text = " | ".join(
        [
            f"风险灯 {risk_state}",
            f"已提交 {submitted_orders}",
            f"市场 {market_stamp[-8:] if len(market_stamp) >= 8 else market_stamp}",
            f"任务 {job_stamp[-8:] if len(job_stamp) >= 8 else job_stamp}",
        ]
    )

    return {
        "market_value": market_value,
        "refresh_value": refresh_value,
        "runtime_value": runtime_value,
        "pulse_headline": pulse_headline,
        "next_step": next_step,
        "meta_text": meta_text,
        "risk_state": risk_state,
    }
