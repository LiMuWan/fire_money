from __future__ import annotations

from pathlib import Path


def append_runtime_log(window, message: str, *, datetime_cls, level: str = "INFO") -> None:
    timestamp = datetime_cls.now().strftime("%H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    window.runtime_events.append(line)
    window.runtime_events = window.runtime_events[-200:]
    if hasattr(window, "runtime_log_text"):
        window.runtime_log_text.setPlainText("\n".join(window.runtime_events) + "\n")


def build_runtime_overview_text(window, *, cache_cls, datetime_cls) -> str:
    cache_stats = cache_cls().cache_stats()
    last_status_label = {
        "idle": "空闲",
        "running": "执行中",
        "success": "成功",
        "failed": "失败",
    }.get(window.last_job_status, window.last_job_status or "未知")
    last_job_line = "最近任务：暂无"
    if window.last_job_name:
        last_job_line = (
            f"最近任务：{window.last_job_name} | {last_status_label} | "
            f"{window.last_job_duration_ms:.0f} ms"
        )
    lines = [
        f"活跃任务：{len(window.active_jobs)}",
        f"累计任务：{window.job_run_count} | 成功 {window.job_success_count} | 失败 {window.job_failure_count}",
        f"缓存文件：{cache_stats['files']}",
        f"缓存体积：{cache_stats['bytes'] / 1024:.1f} KB",
        f"最近日志：{len(window.runtime_events)} 条",
        last_job_line,
    ]
    if window.last_job_finished_at:
        lines.append(f"最近完成：{window.last_job_finished_at}")
    if window.active_jobs:
        lines.append(f"执行队列：{', '.join(sorted(window.active_jobs))}")
    if window.last_cache_purge_summary:
        lines.append(f"缓存维护：{window.last_cache_purge_summary}")
    if window.last_runtime_export_path:
        lines.append(f"日志导出：{Path(window.last_runtime_export_path).name}")
    return "\n".join(lines)


def refresh_runtime_panel(window, *, cache_cls, datetime_cls) -> None:
    overview_text = build_runtime_overview_text(window, cache_cls=cache_cls, datetime_cls=datetime_cls)
    if hasattr(window, "runtime_status_text"):
        window.runtime_status_text.setPlainText(overview_text)
    if hasattr(window, "runtime_log_text"):
        payload = "\n".join(window.runtime_events)
        window.runtime_log_text.setPlainText(f"{payload}\n" if payload else "")


def runtime_export_dir(window, *, project_root) -> Path:
    export_dir = ""
    if "export_dir" in window.broker_inputs:
        export_dir = window.broker_inputs["export_dir"].text().strip()
    root = Path(export_dir) if export_dir else (project_root / "exports")
    return root / "runtime"


def export_runtime_log(window, *, project_root, datetime_cls, info_dialog_fn, cache_cls) -> None:
    export_dir = runtime_export_dir(window, project_root=project_root)
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / f"runtime_log_{datetime_cls.now().strftime('%Y%m%d_%H%M%S')}.txt"
    content_lines = [
        "量化猎手 Pro 运行日志",
        f"导出时间：{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "[运行概览]",
        build_runtime_overview_text(window, cache_cls=cache_cls, datetime_cls=datetime_cls),
        "",
        "[事件日志]",
    ]
    content_lines.extend(window.runtime_events or ["暂无运行日志"])
    target.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
    window.last_runtime_export_path = str(target)
    window._append_runtime_log(f"运行日志已导出：{target}")
    refresh_runtime_panel(window, cache_cls=cache_cls, datetime_cls=datetime_cls)
    info_dialog_fn(window, "导出完成", f"运行日志已导出到：\n{target}")



def clear_market_cache(window, *, cache_cls, datetime_cls, info_dialog_fn) -> None:
    cache = cache_cls()
    result = cache.clear()
    window.last_cache_purge_summary = f"?? {result['files']} ??? / {result['bytes'] / 1024:.1f} KB"
    window._append_runtime_log(f"????????{window.last_cache_purge_summary}")
    refresh_runtime_panel(window, cache_cls=cache_cls, datetime_cls=datetime_cls)
    info_dialog_fn(window, "??????", f"????????\n{window.last_cache_purge_summary}")



def record_job_result(window, job_name: str, status: str, duration_ms: float, *, datetime_cls, message: str = "") -> None:
    metric = window.job_metrics.setdefault(
        job_name,
        {
            "runs": 0,
            "success": 0,
            "failed": 0,
            "last_status": "idle",
            "last_duration_ms": 0.0,
            "last_message": "",
            "last_finished_at": "",
        },
    )
    metric["runs"] = int(metric["runs"]) + 1
    if status == "success":
        metric["success"] = int(metric["success"]) + 1
    elif status == "failed":
        metric["failed"] = int(metric["failed"]) + 1
    metric["last_status"] = status
    metric["last_duration_ms"] = duration_ms
    metric["last_message"] = message[:160]
    metric["last_finished_at"] = datetime_cls.now().strftime("%Y-%m-%d %H:%M:%S")
    window.last_job_name = job_name
    window.last_job_status = status
    window.last_job_duration_ms = duration_ms
    window.last_job_finished_at = str(metric["last_finished_at"])
