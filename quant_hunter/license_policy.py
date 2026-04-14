from __future__ import annotations


def license_capabilities(plan: str | None) -> dict[str, object]:
    normalized = (plan or "TRIAL").upper()
    if normalized == "ENTERPRISE":
        return {
            "plan": normalized,
            "auto_daily_plan_export": True,
            "focus_theme_boost": 7.0,
            "theme_panel_size": 12,
            "daily_plan_export_limit": 20,
            "market_history_limit": 18,
            "monitor_summary_limit": 6,
            "plan_label": "企业版",
        }
    if normalized == "PRO":
        return {
            "plan": normalized,
            "auto_daily_plan_export": True,
            "focus_theme_boost": 4.0,
            "theme_panel_size": 8,
            "daily_plan_export_limit": 12,
            "market_history_limit": 12,
            "monitor_summary_limit": 4,
            "plan_label": "专业版",
        }
    return {
        "plan": "TRIAL",
        "auto_daily_plan_export": False,
        "focus_theme_boost": 2.0,
        "theme_panel_size": 6,
        "daily_plan_export_limit": 6,
        "market_history_limit": 8,
        "monitor_summary_limit": 3,
        "plan_label": "试用版",
    }
