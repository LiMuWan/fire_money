from __future__ import annotations

from .ui_config import terminal_density_profile


def _set_text_if_changed(widget, text: str, *, set_label_text_fn=None) -> None:
    if widget is None:
        return
    if callable(set_label_text_fn):
        try:
            set_label_text_fn(widget, text)
            return
        except Exception:
            pass
    if hasattr(widget, "text") and hasattr(widget, "setText"):
        try:
            current = widget.text()
        except Exception:
            current = None
        if current != text:
            widget.setText(text)


def _set_widget_visibility(widget, visible: bool, min_height=None) -> None:
    if widget is None:
        return
    if hasattr(widget, "setVisible"):
        widget.setVisible(bool(visible))
    if min_height is not None and hasattr(widget, "setMinimumHeight"):
        try:
            widget.setMinimumHeight(int(min_height))
        except Exception:
            pass


def _resolve_height(height_policy, visible: bool):
    if isinstance(height_policy, dict):
        return height_policy.get(bool(visible))
    return height_policy


def _set_splitter_sizes(splitter, sizes, *, property_name: str = "_qh_watch_sizes_v1") -> None:
    if splitter is None or not hasattr(splitter, "setSizes"):
        return
    normalized_sizes: list[int] = []
    for size in list(sizes or []):
        try:
            normalized_sizes.append(max(int(size), 1))
        except Exception:
            return
    if not normalized_sizes:
        return
    try:
        splitter.setSizes(normalized_sizes)
    except Exception:
        return
    if hasattr(splitter, "setProperty"):
        try:
            splitter.setProperty(property_name, tuple(normalized_sizes))
        except Exception:
            pass


def _broker_profile_is_ready(profile) -> bool:
    if profile is None:
        return False
    candidate_fields = (
        "username",
        "password",
        "token",
        "account_id",
        "sdk_python_path",
        "strategy_id",
    )
    for field_name in candidate_fields:
        value = getattr(profile, field_name, None)
        if str(value or "").strip():
            return True
    return False


def _broker_chain_is_ready(window) -> bool:
    order_intents = list(getattr(window, "order_intents", []) or [])
    submissions = list(getattr(window, "order_submission_records", []) or [])
    return bool(order_intents or submissions)


def apply_visibility_policy(
    window,
    visible: bool,
    *,
    state_attr: str,
    widget_specs: list[tuple[str, object | None]],
    toggle_button_attr: str | None = None,
    toggle_text_map: dict[bool, str] | None = None,
    status_label_attr: str | None = None,
    status_text_map: dict[bool, str] | None = None,
    set_label_text_fn=None,
) -> None:
    setattr(window, state_attr, bool(visible))
    for attr_name, height_policy in widget_specs:
        widget = getattr(window, attr_name, None)
        _set_widget_visibility(widget, bool(visible), _resolve_height(height_policy, visible))

    if toggle_button_attr:
        toggle_button = getattr(window, toggle_button_attr, None)
        if toggle_button is not None and toggle_text_map is not None:
            _set_text_if_changed(toggle_button, str(toggle_text_map[bool(visible)]), set_label_text_fn=set_label_text_fn)

    if status_label_attr:
        status_label = getattr(window, status_label_attr, None)
        if status_label is not None and status_text_map is not None:
            _set_text_if_changed(status_label, str(status_text_map[bool(visible)]), set_label_text_fn=set_label_text_fn)


def sync_first_screen_visibility(window, *, policy: dict[str, dict[str, object]]) -> None:
    daily_pool_rows = list(getattr(window, "daily_pool_rows", []) or [])
    order_submission_records = list(getattr(window, "order_submission_records", []) or [])
    scan_rows = list(getattr(window, "scan_rows", []) or [])
    active_symbol = str(getattr(window, "active_symbol", "") or "").strip()
    paper_state = getattr(window, "paper_trading_state", getattr(getattr(window, "state", None), "paper_trading_state", None))

    width = 1920
    height = 1080
    try:
        width = int(window.width()) if hasattr(window, "width") else width
    except Exception:
        width = 1920
    try:
        height = int(window.height()) if hasattr(window, "height") else height
    except Exception:
        height = 1080
    density_profile = terminal_density_profile(
        getattr(window, "current_density", "compact"),
        width=width,
        height=height,
    )
    compact_first_screen = bool(density_profile.get("compact_layout", False))
    watch_first_screen = bool(density_profile.get("watch_layout", False))

    auth_summary_box = getattr(window, "auth_summary_box", None)
    auth_ready = False
    if auth_summary_box is not None:
        current_profile = None
        current_profile_fn = getattr(window, "current_broker_profile", None)
        if callable(current_profile_fn):
            try:
                current_profile = current_profile_fn()
            except Exception:
                current_profile = None
        if current_profile is None:
            current_profile = getattr(getattr(window, "state", None), "broker_profile", None)
        auth_ready = _broker_profile_is_ready(current_profile)
        hide_on_watch = bool(
            dict(policy.get("auth_summary_box", {}) or {}).get("hide_on_watch_when_auth_ready", False)
        )
        _set_widget_visibility(auth_summary_box, not (hide_on_watch and watch_first_screen and auth_ready))

    auth_capability_box = getattr(window, "auth_capability_box", None)
    if auth_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("auth_capability_box", {}) or {}).get("hide_on_watch_when_auth_ready", False)
        )
        _set_widget_visibility(auth_capability_box, not (hide_on_watch and watch_first_screen and auth_ready))

    auth_status_banner = getattr(window, "auth_status_banner", None)
    if auth_status_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("auth_status_banner", {}) or {}).get("hide_on_watch_when_auth_ready", False)
        )
        _set_widget_visibility(auth_status_banner, not (hide_on_watch and watch_first_screen and auth_ready))

    auth_status_box = getattr(window, "auth_status_box", None)
    if auth_status_box is not None:
        hide_on_watch = bool(
            dict(policy.get("auth_status_box", {}) or {}).get("hide_on_watch_when_auth_ready", False)
        )
        _set_widget_visibility(auth_status_box, not (hide_on_watch and watch_first_screen and auth_ready))

    auth_desk_summary_frame = getattr(window, "auth_desk_summary_frame", None)
    if auth_desk_summary_frame is not None:
        hide_on_watch = bool(
            dict(policy.get("auth_desk_summary_frame", {}) or {}).get("hide_on_watch_when_auth_ready", False)
        )
        _set_widget_visibility(auth_desk_summary_frame, not (hide_on_watch and watch_first_screen and auth_ready))

    overview_pool_table = getattr(window, "market_pool_table", None)
    overview_pool_count = 0
    if overview_pool_table is not None and hasattr(overview_pool_table, "rowCount"):
        try:
            overview_pool_count = int(overview_pool_table.rowCount())
        except Exception:
            overview_pool_count = 0
    overview_ready = bool(active_symbol) or overview_pool_count > 0

    market_status_label = getattr(window, "market_status_label", None)
    if market_status_label is not None:
        hide_on_watch = bool(
            dict(policy.get("market_status_label", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(market_status_label, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_priority_box = getattr(window, "overview_priority_box", None)
    if overview_priority_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_priority_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_priority_box, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_left_panel = getattr(window, "overview_left_panel", None)
    if overview_left_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_left_panel", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_left_panel, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_right_panel = getattr(window, "overview_right_panel", None)
    if overview_right_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_right_panel", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_right_panel, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_main_splitter = getattr(window, "overview_main_splitter", None)
    if overview_main_splitter is not None and hasattr(overview_main_splitter, "setSizes") and hasattr(overview_main_splitter, "count"):
        try:
            splitter_count = int(overview_main_splitter.count())
        except Exception:
            splitter_count = 0
        if splitter_count == 3 and watch_first_screen and overview_ready:
            try:
                overview_main_splitter.setSizes([0, max(width, 1), 0])
            except Exception:
                pass

    market_header_copy_policy = dict(policy.get("overview_market_header_copy", {}) or {})
    if market_header_copy_policy:
        hide_on_watch = bool(market_header_copy_policy.get("hide_on_watch_when_market_ready", False))
        show_market_header_copy = not (hide_on_watch and watch_first_screen and overview_ready)
        for attr_name in (
            "market_header_label",
            "market_subheader_label",
            "market_signal_label",
            "market_quote_label",
        ):
            widget = getattr(window, attr_name, None)
            if widget is not None:
                _set_widget_visibility(widget, show_market_header_copy)

    overview_dashboard_metrics_box = getattr(window, "dashboard_metrics_box", None)
    if overview_dashboard_metrics_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_dashboard_metrics_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_dashboard_metrics_box, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_summary_box = getattr(window, "overview_summary_box", None)
    if overview_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_summary_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_summary_box, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_capability_box = getattr(window, "overview_capability_box", None)
    if overview_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_capability_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_capability_box, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_signal_summary_column = getattr(window, "overview_signal_summary_column", None)
    if overview_signal_summary_column is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_signal_summary_column", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_signal_summary_column, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_mini_chart_tabs = getattr(window, "overview_mini_chart_tabs", None)
    if overview_mini_chart_tabs is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_mini_chart_tabs", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_mini_chart_tabs, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_chart_controls_tabs = getattr(window, "overview_chart_controls_tabs", None)
    if overview_chart_controls_tabs is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_chart_controls_tabs", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_chart_controls_tabs, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_right_intel_tabs = getattr(window, "right_intel_tabs", None)
    if overview_right_intel_tabs is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_right_intel_tabs", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_right_intel_tabs, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_leaderboard_box = getattr(window, "overview_leaderboard_box", None)
    if overview_leaderboard_box is not None:
        hide_on_watch = bool(dict(policy.get("overview_leaderboard_box", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(overview_leaderboard_box, not (hide_on_watch and watch_first_screen))

    overview_theme_summary_box = getattr(window, "overview_theme_summary_box", None)
    if overview_theme_summary_box is not None:
        hide_on_watch = bool(dict(policy.get("overview_theme_summary_box", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(overview_theme_summary_box, not (hide_on_watch and watch_first_screen))

    overview_cockpit_box = getattr(window, "overview_cockpit_box", None)
    if overview_cockpit_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_cockpit_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_cockpit_box, not (hide_on_watch and watch_first_screen and overview_ready))

    overview_playbook_box = getattr(window, "overview_playbook_box", None)
    if overview_playbook_box is not None:
        hide_on_watch = bool(
            dict(policy.get("overview_playbook_box", {}) or {}).get("hide_on_watch_when_market_ready", False)
        )
        _set_widget_visibility(overview_playbook_box, not (hide_on_watch and watch_first_screen and overview_ready))

    recommend_empty_box = getattr(window, "recommend_empty_box", None)
    if recommend_empty_box is not None:
        show_when_empty = bool(dict(policy.get("recommend_empty_box", {}) or {}).get("show_when_daily_pool_empty", True))
        _set_widget_visibility(recommend_empty_box, (not bool(daily_pool_rows)) if show_when_empty else bool(daily_pool_rows))

    recommend_status_label = getattr(window, "recommend_status_label", None)
    if recommend_status_label is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_status_label", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_status_label, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    recommend_section_hint = getattr(window, "recommend_section_hint", None)
    if recommend_section_hint is not None:
        hide_on_compact = bool(
            dict(policy.get("recommend_section_hint", {}) or {}).get("hide_on_compact_when_daily_pool_exists", True)
        )
        _set_widget_visibility(recommend_section_hint, not (hide_on_compact and compact_first_screen and bool(daily_pool_rows)))

    broker_recap_box = getattr(window, "broker_recap_box", None)
    if broker_recap_box is not None:
        show_when_submissions = bool(
            dict(policy.get("broker_recap_box", {}) or {}).get("show_when_submission_records", True)
        )
        _set_widget_visibility(broker_recap_box, bool(order_submission_records) if show_when_submissions else False)

    recommend_desk_summary_frame = getattr(window, "recommend_desk_summary_frame", None)
    if recommend_desk_summary_frame is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_desk_summary_frame", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_desk_summary_frame, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    recommend_focus_cards_box = getattr(window, "recommend_focus_cards_box", None)
    if recommend_focus_cards_box is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_focus_cards_box", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_focus_cards_box, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    recommend_capability_box = getattr(window, "recommend_capability_box", None)
    if recommend_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_capability_box", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_capability_box, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    recommend_deep_summary_box = getattr(window, "recommend_deep_summary_box", None)
    if recommend_deep_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_deep_summary_box", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_deep_summary_box, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    recommend_stage_summary_frame = getattr(window, "recommend_stage_summary_frame", None)
    if recommend_stage_summary_frame is not None:
        hide_on_watch = bool(
            dict(policy.get("recommend_stage_summary_frame", {}) or {}).get("hide_on_watch_when_daily_pool_exists", False)
        )
        _set_widget_visibility(recommend_stage_summary_frame, not (hide_on_watch and watch_first_screen and bool(daily_pool_rows)))

    if daily_pool_rows and watch_first_screen:
        recommend_dispatch_splitter = getattr(window, "recommend_dispatch_splitter", None)
        if recommend_dispatch_splitter is not None and hasattr(recommend_dispatch_splitter, "count") and hasattr(recommend_dispatch_splitter, "setSizes"):
            try:
                if int(recommend_dispatch_splitter.count()) == 3:
                    dispatch_sizes = [
                        max(int(width * 0.24), 220),
                        max(int(width * 0.52), 420),
                        max(int(width * 0.24), 220),
                    ]
                    _set_splitter_sizes(recommend_dispatch_splitter, dispatch_sizes)
            except Exception:
                pass

        recommend_summary_splitter = getattr(window, "recommend_summary_splitter", None)
        if recommend_summary_splitter is not None and hasattr(recommend_summary_splitter, "count") and hasattr(recommend_summary_splitter, "setSizes"):
            try:
                if int(recommend_summary_splitter.count()) == 2:
                    summary_sizes = [
                        max(int(width * 0.36), 280),
                        max(int(width * 0.64), 480),
                    ]
                    _set_splitter_sizes(recommend_summary_splitter, summary_sizes)
            except Exception:
                pass

        recommend_recap_middle_splitter = getattr(window, "recommend_recap_middle_splitter", None)
        if recommend_recap_middle_splitter is not None and hasattr(recommend_recap_middle_splitter, "count") and hasattr(recommend_recap_middle_splitter, "setSizes"):
            try:
                if int(recommend_recap_middle_splitter.count()) == 2:
                    recap_middle_sizes = [
                        max((width * 34) // 100, 260),
                        max((width * 66) // 100, 420),
                    ]
                    _set_splitter_sizes(recommend_recap_middle_splitter, recap_middle_sizes)
            except Exception:
                pass

        recommend_recap_bottom_splitter = getattr(window, "recommend_recap_bottom_splitter", None)
        if recommend_recap_bottom_splitter is not None and hasattr(recommend_recap_bottom_splitter, "count") and hasattr(recommend_recap_bottom_splitter, "setSizes"):
            try:
                if int(recommend_recap_bottom_splitter.count()) == 2:
                    recap_bottom_sizes = [
                        max((width * 34) // 100, 260),
                        max((width * 66) // 100, 420),
                    ]
                    _set_splitter_sizes(recommend_recap_bottom_splitter, recap_bottom_sizes)
            except Exception:
                pass

        recommend_review_splitter = getattr(window, "recommend_review_splitter", None)
        if recommend_review_splitter is not None and hasattr(recommend_review_splitter, "count") and hasattr(recommend_review_splitter, "setSizes"):
            try:
                if int(recommend_review_splitter.count()) == 2:
                    review_sizes = [
                        max((width * 50) // 100, 360),
                        max((width * 50) // 100, 360),
                    ]
                    _set_splitter_sizes(recommend_review_splitter, review_sizes)
            except Exception:
                pass

    broker_ready = _broker_chain_is_ready(window)

    broker_workbench_banner = getattr(window, "broker_workbench_banner", None)
    if broker_workbench_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_workbench_banner", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_workbench_banner, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_stage_label = getattr(window, "broker_stage_label", None)
    if broker_stage_label is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_stage_label", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_stage_label, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_desk_summary_frame = getattr(window, "broker_desk_summary_frame", None)
    if broker_desk_summary_frame is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_desk_summary_frame", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_desk_summary_frame, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_stage_summary_frame = getattr(window, "broker_stage_summary_frame", None)
    if broker_stage_summary_frame is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_stage_summary_frame", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_stage_summary_frame, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_summary_box = getattr(window, "broker_summary_box", None)
    if broker_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_summary_box", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_summary_box, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_metrics_box = getattr(window, "broker_metrics_box", None)
    if broker_metrics_box is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_metrics_box", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_metrics_box, not (hide_on_watch and watch_first_screen and broker_ready))

    broker_capability_box = getattr(window, "broker_capability_box", None)
    if broker_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("broker_capability_box", {}) or {}).get("hide_on_watch_when_broker_ready", False)
        )
        _set_widget_visibility(broker_capability_box, not (hide_on_watch and watch_first_screen and broker_ready))

    if broker_ready and watch_first_screen:
        broker_workbench_splitter = getattr(window, "broker_workbench_splitter", None)
        if broker_workbench_splitter is not None and hasattr(broker_workbench_splitter, "count") and hasattr(broker_workbench_splitter, "setSizes"):
            try:
                if int(broker_workbench_splitter.count()) == 2:
                    workbench_sizes = [max(int(width * 0.24), 220), max(int(width * 0.76), 520)]
                    _set_splitter_sizes(broker_workbench_splitter, workbench_sizes)
            except Exception:
                pass

        broker_middle_splitter = getattr(window, "broker_middle_splitter", None)
        if broker_middle_splitter is not None and hasattr(broker_middle_splitter, "count") and hasattr(broker_middle_splitter, "setSizes"):
            try:
                if int(broker_middle_splitter.count()) == 2:
                    middle_sizes = [max(int(width * 0.28), 220), max(int(width * 0.72), 520)]
                    _set_splitter_sizes(broker_middle_splitter, middle_sizes)
            except Exception:
                pass

        broker_control_splitter = getattr(window, "broker_control_splitter", None)
        if broker_control_splitter is not None and hasattr(broker_control_splitter, "count") and hasattr(broker_control_splitter, "setSizes"):
            try:
                if int(broker_control_splitter.count()) == 3:
                    control_sizes = [
                        max((width * 30) // 100, 320),
                        max((width * 34) // 100, 360),
                        max((width * 36) // 100, 360),
                    ]
                    _set_splitter_sizes(broker_control_splitter, control_sizes)
            except Exception:
                pass

        broker_order_focus_splitter = getattr(window, "broker_order_focus_splitter", None)
        if broker_order_focus_splitter is not None and hasattr(broker_order_focus_splitter, "count") and hasattr(broker_order_focus_splitter, "setSizes"):
            try:
                if int(broker_order_focus_splitter.count()) == 2:
                    focus_sizes = [max((width * 70) // 100, 360), max((width * 30) // 100, 220)]
                    _set_splitter_sizes(broker_order_focus_splitter, focus_sizes)
            except Exception:
                pass

        broker_execution_detail_splitter = getattr(window, "broker_execution_detail_splitter", None)
        if broker_execution_detail_splitter is not None and hasattr(broker_execution_detail_splitter, "count") and hasattr(broker_execution_detail_splitter, "setSizes"):
            try:
                if int(broker_execution_detail_splitter.count()) == 2:
                    execution_detail_sizes = [
                        max((width * 42) // 100, 280),
                        max((width * 58) // 100, 360),
                    ]
                    _set_splitter_sizes(broker_execution_detail_splitter, execution_detail_sizes)
            except Exception:
                pass

    scanner_summary_box = getattr(window, "scanner_summary_box", None)
    summary_table = getattr(window, "summary_table", None)
    summary_count = 0
    if summary_table is not None and hasattr(summary_table, "rowCount"):
        try:
            summary_count = int(summary_table.rowCount())
        except Exception:
            summary_count = 0
    monitor_table = getattr(window, "monitor_table", None)
    monitor_count = 0
    if monitor_table is not None and hasattr(monitor_table, "rowCount"):
        try:
            monitor_count = int(monitor_table.rowCount())
        except Exception:
            monitor_count = 0
    scanner_ready = bool(scan_rows) or summary_count > 0 or monitor_count > 0
    scanner_status_banner = getattr(window, "scanner_status_banner", None)
    if scanner_status_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_status_banner", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_status_banner, not (hide_on_watch and watch_first_screen and scanner_ready))
    if scanner_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_summary_box", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_summary_box, not (hide_on_watch and watch_first_screen and bool(scan_rows)))

    scanner_capability_box = getattr(window, "scanner_capability_box", None)
    if scanner_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_capability_box", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_capability_box, not (hide_on_watch and watch_first_screen and scanner_ready))

    scanner_watch_summary_box = getattr(window, "scanner_watch_summary_box", None)
    if scanner_watch_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_watch_summary_box", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_watch_summary_box, not (hide_on_watch and watch_first_screen and scanner_ready))

    scanner_monitor_summary_box = getattr(window, "scanner_monitor_summary_box", None)
    if scanner_monitor_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_monitor_summary_box", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_monitor_summary_box, not (hide_on_watch and watch_first_screen and scanner_ready))

    scanner_desk_summary_frame = getattr(window, "scanner_desk_summary_frame", None)
    if scanner_desk_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("scanner_desk_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(scanner_desk_summary_frame, not (hide_on_watch and watch_first_screen))

    scanner_tool_panel = getattr(window, "scanner_tool_panel", None)
    if scanner_tool_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("scanner_tool_panel", {}) or {}).get("hide_on_watch_when_scan_rows_exist", False)
        )
        _set_widget_visibility(scanner_tool_panel, not (hide_on_watch and watch_first_screen and bool(scan_rows)))

    scanner_stage_summary_frame = getattr(window, "scanner_stage_summary_frame", None)
    if scanner_stage_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("scanner_stage_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(scanner_stage_summary_frame, not (hide_on_watch and watch_first_screen))

    if scanner_ready and watch_first_screen:
        scanner_watch_summary_splitter = getattr(window, "scanner_watch_summary_splitter", None)
        if scanner_watch_summary_splitter is not None and hasattr(scanner_watch_summary_splitter, "count"):
            try:
                if int(scanner_watch_summary_splitter.count()) == 2:
                    scanner_sizes = [
                        max((width * 30) // 100, 260),
                        max((width * 70) // 100, 480),
                    ]
                    _set_splitter_sizes(scanner_watch_summary_splitter, scanner_sizes)
            except Exception:
                pass

    board_summary_box = getattr(window, "board_summary_box", None)
    if board_summary_box is not None:
        board_table = getattr(window, "board_table", None)
        board_count = 0
        if board_table is not None and hasattr(board_table, "rowCount"):
            try:
                board_count = int(board_table.rowCount())
            except Exception:
                board_count = 0
        hide_on_watch = bool(
            dict(policy.get("board_summary_box", {}) or {}).get("hide_on_watch_when_board_rows_exist", False)
        )
        _set_widget_visibility(board_summary_box, not (hide_on_watch and watch_first_screen and board_count > 0))

    board_capability_box = getattr(window, "board_capability_box", None)
    if board_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("board_capability_box", {}) or {}).get("hide_on_watch_when_board_rows_exist", False)
        )
        _set_widget_visibility(board_capability_box, not (hide_on_watch and watch_first_screen and board_count > 0))

    board_status_banner = getattr(window, "board_status_banner", None)
    if board_status_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("board_status_banner", {}) or {}).get("hide_on_watch_when_board_rows_exist", False)
        )
        _set_widget_visibility(board_status_banner, not (hide_on_watch and watch_first_screen and board_count > 0))

    board_desk_summary_frame = getattr(window, "board_desk_summary_frame", None)
    if board_desk_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("board_desk_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(board_desk_summary_frame, not (hide_on_watch and watch_first_screen))

    board_tool_panel = getattr(window, "board_tool_panel", None)
    if board_tool_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("board_tool_panel", {}) or {}).get("hide_on_watch_when_board_rows_exist", False)
        )
        _set_widget_visibility(board_tool_panel, not (hide_on_watch and watch_first_screen and board_count > 0))

    board_stage_summary_frame = getattr(window, "board_stage_summary_frame", None)
    if board_stage_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("board_stage_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(board_stage_summary_frame, not (hide_on_watch and watch_first_screen))

    if board_count > 0 and watch_first_screen:
        board_workspace_splitter = getattr(window, "board_workspace_splitter", None)
        if board_workspace_splitter is not None and hasattr(board_workspace_splitter, "count"):
            try:
                if int(board_workspace_splitter.count()) == 2:
                    board_sizes = [
                        max(int(width * 0.45), 360),
                        max(int(width * 0.55), 420),
                    ]
                    _set_splitter_sizes(board_workspace_splitter, board_sizes)
            except Exception:
                pass

    detail_summary_box = getattr(window, "detail_summary_box", None)
    if detail_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("detail_summary_box", {}) or {}).get("hide_on_watch_when_active_symbol_exists", False)
        )
        _set_widget_visibility(detail_summary_box, not (hide_on_watch and watch_first_screen and bool(active_symbol)))

    detail_capability_box = getattr(window, "detail_capability_box", None)
    if detail_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("detail_capability_box", {}) or {}).get("hide_on_watch_when_active_symbol_exists", False)
        )
        _set_widget_visibility(detail_capability_box, not (hide_on_watch and watch_first_screen and bool(active_symbol)))

    detail_status_banner = getattr(window, "detail_status_banner", None)
    if detail_status_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("detail_status_banner", {}) or {}).get("hide_on_watch_when_active_symbol_exists", False)
        )
        _set_widget_visibility(detail_status_banner, not (hide_on_watch and watch_first_screen and bool(active_symbol)))

    detail_desk_summary_frame = getattr(window, "detail_desk_summary_frame", None)
    if detail_desk_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("detail_desk_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(detail_desk_summary_frame, not (hide_on_watch and watch_first_screen))

    detail_tool_panel = getattr(window, "detail_tool_panel", None)
    if detail_tool_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("detail_tool_panel", {}) or {}).get("hide_on_watch_when_active_symbol_exists", False)
        )
        _set_widget_visibility(detail_tool_panel, not (hide_on_watch and watch_first_screen and bool(active_symbol)))

    detail_stage_summary_frame = getattr(window, "detail_stage_summary_frame", None)
    if detail_stage_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("detail_stage_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(detail_stage_summary_frame, not (hide_on_watch and watch_first_screen))

    if active_symbol and watch_first_screen:
        detail_recap_splitter = getattr(window, "detail_recap_splitter", None)
        if detail_recap_splitter is not None and hasattr(detail_recap_splitter, "count"):
            try:
                if int(detail_recap_splitter.count()) == 3:
                    detail_sizes = [
                        max(int(width * 0.32), 280),
                        max(int(width * 0.38), 340),
                        max(int(width * 0.30), 260),
                    ]
                    _set_splitter_sizes(detail_recap_splitter, detail_sizes)
            except Exception:
                pass

    paper_summary_box = getattr(window, "paper_summary_box", None)
    paper_ready = bool(
        getattr(paper_state, "enabled", False)
        or list(getattr(paper_state, "positions", []) or [])
        or list(getattr(paper_state, "ledger", []) or [])
        or list(getattr(paper_state, "patrol_logs", []) or [])
    )
    if paper_summary_box is not None:
        hide_on_watch = bool(
            dict(policy.get("paper_summary_box", {}) or {}).get("hide_on_watch_when_paper_ready", False)
        )
        _set_widget_visibility(paper_summary_box, not (hide_on_watch and watch_first_screen and paper_ready))

    paper_capability_box = getattr(window, "paper_capability_box", None)
    if paper_capability_box is not None:
        hide_on_watch = bool(
            dict(policy.get("paper_capability_box", {}) or {}).get("hide_on_watch_when_paper_ready", False)
        )
        _set_widget_visibility(paper_capability_box, not (hide_on_watch and watch_first_screen and paper_ready))

    paper_status_banner = getattr(window, "paper_status_banner", None)
    if paper_status_banner is not None:
        hide_on_watch = bool(
            dict(policy.get("paper_status_banner", {}) or {}).get("hide_on_watch_when_paper_ready", False)
        )
        _set_widget_visibility(paper_status_banner, not (hide_on_watch and watch_first_screen and paper_ready))

    paper_desk_summary_frame = getattr(window, "paper_desk_summary_frame", None)
    if paper_desk_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("paper_desk_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(paper_desk_summary_frame, not (hide_on_watch and watch_first_screen))

    paper_overview_box = getattr(window, "paper_overview_box", None)
    if paper_overview_box is not None:
        hide_on_watch = bool(
            dict(policy.get("paper_overview_box", {}) or {}).get("hide_on_watch_when_paper_ready", False)
        )
        _set_widget_visibility(paper_overview_box, not (hide_on_watch and watch_first_screen and paper_ready))

    paper_tool_panel = getattr(window, "paper_tool_panel", None)
    if paper_tool_panel is not None:
        hide_on_watch = bool(
            dict(policy.get("paper_tool_panel", {}) or {}).get("hide_on_watch_when_paper_ready", False)
        )
        _set_widget_visibility(paper_tool_panel, not (hide_on_watch and watch_first_screen and paper_ready))

    paper_stage_summary_frame = getattr(window, "paper_stage_summary_frame", None)
    if paper_stage_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("paper_stage_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(paper_stage_summary_frame, not (hide_on_watch and watch_first_screen))

    if paper_ready and watch_first_screen:
        paper_trading_splitter = getattr(window, "paper_trading_splitter", None)
        if paper_trading_splitter is not None and hasattr(paper_trading_splitter, "count"):
            try:
                if int(paper_trading_splitter.count()) == 2:
                    trading_sizes = [
                        max((width * 43) // 100, 360),
                        max((width * 57) // 100, 420),
                    ]
                    _set_splitter_sizes(paper_trading_splitter, trading_sizes)
            except Exception:
                pass

        paper_analytics_splitter = getattr(window, "paper_analytics_splitter", None)
        if paper_analytics_splitter is not None and hasattr(paper_analytics_splitter, "count"):
            try:
                if int(paper_analytics_splitter.count()) == 2:
                    analytics_sizes = [
                        max(int(width * 0.40), 340),
                        max(int(width * 0.60), 420),
                    ]
                    _set_splitter_sizes(paper_analytics_splitter, analytics_sizes)
            except Exception:
                pass

    config_tool_panel = getattr(window, "config_tool_panel", None)
    if config_tool_panel is not None:
        hide_on_watch = bool(dict(policy.get("config_tool_panel", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_tool_panel, not (hide_on_watch and watch_first_screen))

    config_status_banner = getattr(window, "config_status_banner", None)
    if config_status_banner is not None:
        hide_on_watch = bool(dict(policy.get("config_status_banner", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_status_banner, not (hide_on_watch and watch_first_screen))

    config_desk_summary_frame = getattr(window, "config_desk_summary_frame", None)
    if config_desk_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("config_desk_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_desk_summary_frame, not (hide_on_watch and watch_first_screen))

    config_risk_snapshot_box = getattr(window, "config_risk_snapshot_box", None)
    if config_risk_snapshot_box is not None:
        hide_on_watch = bool(dict(policy.get("config_risk_snapshot_box", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_risk_snapshot_box, not (hide_on_watch and watch_first_screen))

    config_capability_box = getattr(window, "config_capability_box", None)
    if config_capability_box is not None:
        hide_on_watch = bool(dict(policy.get("config_capability_box", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_capability_box, not (hide_on_watch and watch_first_screen))

    config_stage_summary_frame = getattr(window, "config_stage_summary_frame", None)
    if config_stage_summary_frame is not None:
        hide_on_watch = bool(dict(policy.get("config_stage_summary_frame", {}) or {}).get("hide_on_watch", False))
        _set_widget_visibility(config_stage_summary_frame, not (hide_on_watch and watch_first_screen))

    if watch_first_screen:
        strategy_config_splitter = getattr(window, "strategy_config_splitter", None)
        if strategy_config_splitter is not None and hasattr(strategy_config_splitter, "count"):
            try:
                if int(strategy_config_splitter.count()) == 2:
                    config_sizes = [
                        max(int(width * 0.24), 240),
                        max(int(width * 0.76), 620),
                    ]
                    _set_splitter_sizes(strategy_config_splitter, config_sizes)
            except Exception:
                pass
