from __future__ import annotations

from pathlib import Path

_RUNTIME_LOG_LEVEL_LABELS = {
    "INFO": "状态",
    "SUCCESS": "完成",
    "WARN": "提示",
    "ERROR": "异常",
}

_RUNTIME_JOB_STATUS_LABELS = {
    "idle": "待机",
    "running": "执行中",
    "success": "已完成",
    "failed": "异常结束",
}


def runtime_log_level_label(level: str) -> str:
    normalized = str(level or "INFO").strip().upper() or "INFO"
    return _RUNTIME_LOG_LEVEL_LABELS.get(normalized, normalized)


def build_runtime_log_line(message: str, *, datetime_cls, level: str = "INFO") -> str:
    timestamp = datetime_cls.now().strftime("%H:%M:%S")
    return f"[{timestamp}] [{runtime_log_level_label(level)}] {str(message or '').strip()}"


def _runtime_log_payload(lines: list[str]) -> str:
    payload = "\n".join(lines)
    return f"{payload}\n" if payload else ""


def _widget_plain_text(widget) -> str:
    cached = getattr(widget, "_qh_plain_text_cache_v1", None)
    if isinstance(cached, str):
        return cached
    if hasattr(widget, "toPlainText"):
        try:
            text = str(widget.toPlainText())
        except Exception:
            text = ""
        setattr(widget, "_qh_plain_text_cache_v1", text)
        return text
    return ""


def _set_plain_text_if_changed(widget, text: str) -> None:
    if widget is None or not hasattr(widget, "setPlainText"):
        return
    if _widget_plain_text(widget) != text:
        widget.setPlainText(text)
        setattr(widget, "_qh_plain_text_cache_v1", text)


def _append_plain_text_line(widget, line: str) -> bool:
    if widget is None:
        return False
    current = _widget_plain_text(widget)
    payload = f"{current}{line}\n" if current else f"{line}\n"
    if hasattr(widget, "textCursor") and hasattr(widget, "setTextCursor"):
        try:
            cursor = widget.textCursor()
            move_operation = getattr(getattr(cursor, "MoveOperation", None), "End", None)
            if move_operation is None:
                move_operation = getattr(cursor, "End", None)
            if move_operation is not None and hasattr(cursor, "movePosition"):
                cursor.movePosition(move_operation)
            if hasattr(cursor, "insertText"):
                cursor.insertText(f"{line}\n")
                widget.setTextCursor(cursor)
                setattr(widget, "_qh_plain_text_cache_v1", payload)
                return True
        except Exception:
            pass
    if hasattr(widget, "appendPlainText"):
        try:
            widget.appendPlainText(line)
            setattr(widget, "_qh_plain_text_cache_v1", payload)
            return True
        except Exception:
            pass
    if hasattr(widget, "setPlainText"):
        widget.setPlainText(payload)
        setattr(widget, "_qh_plain_text_cache_v1", payload)
        return True
    return False


def append_runtime_log(window, message: str, *, datetime_cls, level: str = "INFO") -> None:
    line = build_runtime_log_line(message, datetime_cls=datetime_cls, level=level)
    previous_count = len(window.runtime_events)
    window.runtime_events.append(line)
    window.runtime_events = window.runtime_events[-200:]
    payload = _runtime_log_payload(window.runtime_events)
    widget = getattr(window, "runtime_log_text", None)
    if widget is None:
        return
    previous_payload = getattr(window, "_runtime_log_rendered_payload_v1", "")
    trimmed = len(window.runtime_events) != previous_count + 1
    if not trimmed and isinstance(previous_payload, str) and f"{previous_payload}{line}\n" == payload:
        if _append_plain_text_line(widget, line):
            window._runtime_log_rendered_payload_v1 = payload
            return
    _set_plain_text_if_changed(widget, payload)
    window._runtime_log_rendered_payload_v1 = payload


def build_runtime_overview_text(window, *, cache_cls, datetime_cls) -> str:
    cache_stats = cache_cls().cache_stats()
    last_status_label = _RUNTIME_JOB_STATUS_LABELS.get(window.last_job_status, window.last_job_status or "未知")
    last_job_line = "当前任务：待机 | 等待新的刷新、重算、导出或执行动作。"
    if window.last_job_name:
        last_job_line = (
            f"当前任务：{window.last_job_name} | {last_status_label} | "
            f"{window.last_job_duration_ms:.0f} ms"
        )
    lines = [
        f"运行中枢：活跃 {len(window.active_jobs)} | 累计 {window.job_run_count}",
        f"任务结果：完成 {window.job_success_count} | 异常 {window.job_failure_count}",
        f"缓存概览：文件 {cache_stats['files']} | 体积 {cache_stats['bytes'] / 1024:.1f} KB",
        f"日志队列：最近 {len(window.runtime_events)} 条",
        last_job_line,
    ]
    if window.last_job_finished_at:
        lines.append(f"最近落点：{window.last_job_finished_at}")
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
        _set_plain_text_if_changed(window.runtime_status_text, overview_text)
    if hasattr(window, "runtime_log_text"):
        payload = _runtime_log_payload(window.runtime_events)
        _set_plain_text_if_changed(window.runtime_log_text, payload)
        window._runtime_log_rendered_payload_v1 = payload


def runtime_export_dir(window, *, project_root) -> Path:
    export_dir = ""
    if "export_dir" in window.broker_inputs:
        export_dir = window.broker_inputs["export_dir"].text().strip()
    root = Path(export_dir) if export_dir else (project_root / "exports")
    return root / "runtime"


def review_output_dir(window, *, report_dir) -> Path:
    export_dir = window.current_broker_profile().export_dir.strip()
    if export_dir:
        return Path(export_dir) / "review_reports"
    return report_dir


def daily_plan_output_dir(window, *, report_dir) -> Path:
    export_dir = window.current_broker_profile().export_dir.strip()
    if export_dir:
        return Path(export_dir) / "daily_plans"
    return report_dir / "daily_plans"


def current_strategy_runtime_config(config_inputs: dict, state, *, theme_drop_reduce_checkbox=None) -> tuple[int, float, bool]:
    try:
        top_theme_limit = int(config_inputs.get("top_theme_limit").text().strip()) if config_inputs.get("top_theme_limit") else state.strategy_top_theme_limit
    except ValueError:
        top_theme_limit = state.strategy_top_theme_limit
    try:
        max_total_exposure = (
            float(config_inputs.get("max_total_exposure").text().strip())
            if config_inputs.get("max_total_exposure")
            else state.strategy_max_total_exposure
        )
    except ValueError:
        max_total_exposure = state.strategy_max_total_exposure
    drop_reduce = (
        theme_drop_reduce_checkbox.isChecked()
        if theme_drop_reduce_checkbox is not None and hasattr(theme_drop_reduce_checkbox, "isChecked")
        else state.strategy_theme_drop_reduce
    )
    return max(top_theme_limit, 1), max(min(max_total_exposure, 1.0), 0.1), bool(drop_reduce)


def current_report_template_config(config_inputs: dict, state, *, template_combo=None, focus_only_checkbox=None) -> tuple[str, bool, int]:
    template_name = "balanced"
    if template_combo is not None and hasattr(template_combo, "currentData"):
        template_name = str(template_combo.currentData() or "balanced")
    focus_only = focus_only_checkbox.isChecked() if focus_only_checkbox is not None and hasattr(focus_only_checkbox, "isChecked") else False
    try:
        candidate_limit = (
            int(config_inputs.get("daily_plan_candidate_limit").text().strip())
            if config_inputs.get("daily_plan_candidate_limit")
            else state.daily_plan_candidate_limit
        )
    except ValueError:
        candidate_limit = state.daily_plan_candidate_limit
    return template_name, focus_only, max(candidate_limit, 1)


def parse_focus_themes_text(raw_text: str) -> list[str]:
    return [item.strip() for item in raw_text.replace("，", ",").split(",") if item.strip()]


def export_runtime_log(window, *, project_root, datetime_cls, info_dialog_fn, cache_cls) -> None:
    export_dir = runtime_export_dir(window, project_root=project_root)
    export_dir.mkdir(parents=True, exist_ok=True)
    target = export_dir / f"runtime_log_{datetime_cls.now().strftime('%Y%m%d_%H%M%S')}.txt"
    content_lines = [
        "量化猎手 Pro / 运行日志",
        f"导出时间：{datetime_cls.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "[状态摘要]",
        build_runtime_overview_text(window, cache_cls=cache_cls, datetime_cls=datetime_cls),
        "",
        "[事件流水]",
    ]
    content_lines.extend(window.runtime_events or ["当前还没有运行日志。"])
    target.write_text("\n".join(content_lines) + "\n", encoding="utf-8")
    window.last_runtime_export_path = str(target)
    window._append_runtime_log(f"运行日志已导出：{target}")
    refresh_runtime_panel(window, cache_cls=cache_cls, datetime_cls=datetime_cls)
    info_dialog_fn(window, "导出完成", f"运行日志已导出到：\n{target}")


def clear_market_cache(window, *, cache_cls, datetime_cls, info_dialog_fn) -> None:
    cache = cache_cls()
    result = cache.clear()
    window.last_cache_purge_summary = f"已清理 {result['files']} 个文件 / {result['bytes'] / 1024:.1f} KB"
    window._append_runtime_log(f"缓存清理完成：{window.last_cache_purge_summary}")
    refresh_runtime_panel(window, cache_cls=cache_cls, datetime_cls=datetime_cls)
    info_dialog_fn(window, "缓存已清理", f"本地缓存清理完成。\n{window.last_cache_purge_summary}")


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
