from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    HoldingRecord,
    OptimizationRun,
    RecommendationRow,
    ReportArtifacts,
    ScanRow,
    StrategyHistoryReport,
    SymbolBacktestSummary,
)
from .theme import infer_mainline_flow_signal, infer_mainline_stage, summarize_themes


def _unique_report_paths(root: Path, prefix: str) -> tuple[Path, Path, Path]:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    csv_path = root / f"{prefix}_{stamp}.csv"
    json_path = root / f"{prefix}_{stamp}.json"
    markdown_path = root / f"{prefix}_{stamp}.md"
    if not any(path.exists() for path in (csv_path, json_path, markdown_path)):
        return csv_path, json_path, markdown_path
    counter = 1
    while True:
        csv_path = root / f"{prefix}_{stamp}_{counter}.csv"
        json_path = root / f"{prefix}_{stamp}_{counter}.json"
        markdown_path = root / f"{prefix}_{stamp}_{counter}.md"
        if not any(path.exists() for path in (csv_path, json_path, markdown_path)):
            return csv_path, json_path, markdown_path
        counter += 1


def _report_role_score(value: str) -> int:
    return {
        "CORE": 6,
        "FRONT": 5,
        "ASSIST": 4,
        "FOLLOW": 3,
        "NOISE": 1,
        "ELIMINATED": 0,
    }.get((value or "").upper(), 2)


def _report_mainline_rank_score(item: RecommendationRow) -> int:
    rank = int(getattr(item, "mainline_rank", getattr(item, "theme_rank", 0)) or 0)
    if rank <= 0:
        return 0
    return max(0, 100 - min(rank, 99))


def _report_focus_boost(item: RecommendationRow, focus_set: set[str]) -> int:
    if not focus_set:
        return 0
    names = {
        getattr(item, "theme_name", "") or "",
        getattr(item, "mainline_tag", "") or "",
    }
    return 1 if any(name in focus_set for name in names if name) else 0


def _report_mainline_flow_signal(item: RecommendationRow) -> str:
    signal = str(getattr(item, "mainline_flow_signal", "") or "").strip()
    if signal:
        return signal
    return infer_mainline_flow_signal(
        int(getattr(item, "mainline_rank", getattr(item, "theme_rank", 0)) or 0),
        float(getattr(item, "mainline_strength_score", 0.0) or getattr(item, "theme_score", 0.0) or 0.0),
        float(getattr(item, "mainline_continuation_score", 0.0) or 0.0),
        float(getattr(item, "theme_divergence_score", 0.0) or 0.0),
        float(getattr(item, "theme_failure_risk", 0.0) or 0.0),
        float(getattr(item, "mainline_window_score", 0.0) or 0.0),
        str(getattr(item, "mainline_role", "") or ""),
    )


def _report_mainline_stage(item: RecommendationRow) -> str:
    stage = str(getattr(item, "mainline_stage", "") or "").strip()
    if stage:
        return stage
    return infer_mainline_stage(
        int(getattr(item, "mainline_rank", getattr(item, "theme_rank", 0)) or 0),
        float(getattr(item, "mainline_strength_score", 0.0) or getattr(item, "theme_score", 0.0) or 0.0),
        float(getattr(item, "mainline_continuation_score", 0.0) or 0.0),
        float(getattr(item, "theme_divergence_score", 0.0) or 0.0),
        float(getattr(item, "theme_failure_risk", 0.0) or 0.0),
        float(getattr(item, "mainline_window_score", 0.0) or 0.0),
        str(getattr(item, "mainline_role", "") or ""),
    )


def _report_mainline_followup_label(signal: str) -> str:
    if signal in {"延续偏强", "延续待确认"}:
        return "继续跟"
    if signal in {"延续可跟踪", "延续观察"}:
        return "只观察"
    return "防切换"


def _report_mainline_followup_text(item: RecommendationRow) -> str:
    signal = _report_mainline_flow_signal(item)
    stance = _report_mainline_followup_label(signal)
    tag = getattr(item, "mainline_tag", "") or getattr(item, "theme_name", "") or "未分类"
    role = getattr(item, "mainline_role", "") or "--"
    rank = int(getattr(item, "mainline_rank", getattr(item, "theme_rank", 0)) or 0) or "--"
    window_score = float(getattr(item, "mainline_window_score", 0.0) or 0.0)
    risk_flag = getattr(item, "mainline_risk_flag", "") or "--"
    stage = _report_mainline_stage(item)
    if stance == "继续跟":
        reason = "主线仍在延续，优先跟前排，不追杂毛"
    elif stance == "只观察":
        reason = "主线可跟踪，但位次或窗口还不够硬，先等确认"
    else:
        reason = "主线出现切换/退潮迹象，优先减仓和回避"
    next_focus = getattr(item, "next_focus", "") or ""
    if next_focus:
        reason = f"{reason}。执行观察：{next_focus}"
    return f"{stance}：{tag} | {signal} | {stage} | 第{rank}位 | {role} | 窗口 {window_score:.1f} | 风险 {risk_flag} | {reason}"


def _report_mainline_preference_rows(recommendations: list[RecommendationRow]) -> tuple[RecommendationRow | None, RecommendationRow | None, RecommendationRow | None]:
    continue_row = None
    watch_row = None
    switch_row = None
    for item in recommendations:
        signal = _report_mainline_flow_signal(item)
        if continue_row is None and signal in {"延续偏强", "延续待确认"}:
            continue_row = item
        if watch_row is None and signal == "延续可跟踪":
            watch_row = item
        if switch_row is None and signal in {"切换预警", "切换/退潮"}:
            switch_row = item
        if continue_row and watch_row and switch_row:
            break
    if watch_row is None:
        for item in recommendations:
            if getattr(item, "action", "") in {"WATCH", "HOLD"}:
                watch_row = item
                break
    return continue_row, watch_row, switch_row


def _report_recommendation_sort_key(
    item: RecommendationRow,
    *,
    template_name: str,
    focus_set: set[str],
) -> tuple[float, ...]:
    focus_boost = _report_focus_boost(item, focus_set)
    primary_boost = 1 if int(getattr(item, "mainline_rank", getattr(item, "theme_rank", 0)) or 0) == 1 else 0
    role_score = _report_role_score(getattr(item, "mainline_role", ""))
    window_score = float(getattr(item, "mainline_window_score", 0.0) or 0.0)
    risk_score = 100.0 - float(getattr(item, "theme_failure_risk", 0.0) or 0.0)
    mainline_strength = float(getattr(item, "mainline_strength_score", 0.0) or getattr(item, "theme_score", 0.0) or 0.0)
    leader_score = float(getattr(item, "leader_score", 0.0) or 0.0)
    total_score = float(getattr(item, "total_score", 0.0) or 0.0)
    persistence_score = float(getattr(item, "persistence_score", 0.0) or 0.0)
    position_score = float(getattr(item, "position_score", 0.0) or 0.0)
    news_score = float(getattr(item, "news_score", 0.0) or 0.0)
    rank_score = _report_mainline_rank_score(item)

    if template_name == "aggressive":
        return (
            focus_boost,
            primary_boost,
            role_score,
            window_score,
            leader_score,
            rank_score,
            total_score,
            news_score,
        )
    if template_name == "defensive":
        return (
            focus_boost,
            primary_boost,
            risk_score,
            window_score,
            rank_score,
            persistence_score,
            position_score,
            total_score,
        )
    return (
        focus_boost,
        primary_boost,
        role_score,
        window_score,
        risk_score,
        rank_score,
        mainline_strength,
        total_score,
        leader_score,
    )


def _filter_recommendations_for_plan(
    recommendations: list[RecommendationRow],
    *,
    focus_themes: list[str] | None = None,
    template_name: str = "balanced",
    focus_only: bool = False,
    candidate_limit: int = 10,
) -> list[RecommendationRow]:
    selected = list(recommendations)
    focus_set = {item.strip() for item in (focus_themes or []) if item.strip()}
    if focus_only and focus_set:
        focused_rows = [item for item in selected if item.theme_name in focus_set]
        if focused_rows:
            selected = focused_rows

    selected.sort(
        key=lambda item: (
            *_report_recommendation_sort_key(item, template_name=template_name, focus_set=focus_set),
            item.stock_id,
        ),
        reverse=True,
    )

    return selected[: max(candidate_limit, 1)]


def _display_leader_level(value: str) -> str:
    return {
        "CORE_LEADER": "核心龙头",
        "ACTIVE_LEADER": "活跃龙头",
        "FOLLOWER": "跟风股",
        "NOISE": "噪声",
    }.get(value, value)


def export_optimization_report(
    results: list[OptimizationRun],
    output_dir: str | Path,
    title: str = "参数优化报告",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, markdown_path = _unique_report_paths(root, "optimization")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "objective",
                "robustness_score",
                "avg_return",
                "avg_out_of_sample_return",
                "avg_median_window_return",
                "avg_worst_window_return",
                "avg_return_std",
                "avg_drawdown",
                "avg_win_rate",
                "avg_positive_window_ratio",
                "avg_profit_factor",
                "portfolio_return",
                "portfolio_out_of_sample_return",
                "portfolio_worst_window_return",
                "portfolio_return_std",
                "portfolio_max_drawdown",
                "portfolio_profit_factor",
                "portfolio_avg_exposure",
                "portfolio_max_concurrent_positions",
                "trade_count",
                "symbols_tested",
                "params",
            ]
        )
        for item in results:
            writer.writerow(
                [
                    item.rank,
                    item.objective,
                    item.robustness_score,
                    item.avg_return,
                    item.avg_out_of_sample_return,
                    item.avg_median_window_return,
                    item.avg_worst_window_return,
                    item.avg_return_std,
                    item.avg_drawdown,
                    item.avg_win_rate,
                    item.avg_positive_window_ratio,
                    item.avg_profit_factor,
                    item.portfolio_return,
                    item.portfolio_out_of_sample_return,
                    item.portfolio_worst_window_return,
                    item.portfolio_return_std,
                    item.portfolio_max_drawdown,
                    item.portfolio_profit_factor,
                    item.portfolio_avg_exposure,
                    item.portfolio_max_concurrent_positions,
                    item.trade_count,
                    item.symbols_tested,
                    json.dumps(item.params, ensure_ascii=False),
                ]
            )

    json_path.write_text(
        json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    markdown_lines = [
        f"# {title}",
        "",
        "| Rank | Objective | Robustness | Portfolio Return | Portfolio OOS | Portfolio DD | Avg Return | OOS Return | Worst Window | Trades | Params |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        markdown_lines.append(
            f"| {item.rank} | {item.objective:.4f} | {item.robustness_score:.0%} | {item.portfolio_return:.2%} | "
            f"{item.portfolio_out_of_sample_return:.2%} | {item.portfolio_max_drawdown:.2%} | {item.avg_return:.2%} | "
            f"{item.avg_out_of_sample_return:.2%} | {item.avg_worst_window_return:.2%} | {item.trade_count} | "
            f"`{json.dumps(item.params, ensure_ascii=False)}` |"
        )
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    return ReportArtifacts(str(markdown_path), str(csv_path), str(json_path))


def export_workspace_report(
    scan_rows: list[ScanRow],
    summaries: list[SymbolBacktestSummary],
    output_dir: str | Path,
    title: str = "工作台报告",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, markdown_path = _unique_report_paths(root, "workspace")

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["symbol", "action", "label", "score", "signal_date", "total_return", "max_drawdown", "win_rate"])
        summary_map = {item.symbol: item for item in summaries}
        for row in scan_rows:
            summary = summary_map.get(row.symbol)
            writer.writerow(
                [
                    row.symbol,
                    row.action,
                    row.label,
                    row.score,
                    row.signal_date,
                    "" if summary is None else summary.total_return,
                    "" if summary is None else summary.max_drawdown,
                    "" if summary is None else summary.win_rate,
                ]
            )

    payload = {
        "scan_rows": [asdict(item) for item in scan_rows],
        "summaries": [asdict(item) for item in summaries],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [f"# {title}", "", "## 扫描结果", ""]
    for row in scan_rows:
        lines.append(f"- {row.symbol}: {row.label} / {row.action} / score {row.score} / {row.signal_date}")
    lines.extend(["", "## 回测汇总", ""])
    for item in summaries:
        lines.append(
            f"- {item.symbol}: return {item.total_return:.2%}, drawdown {item.max_drawdown:.2%}, "
            f"win rate {item.win_rate:.2%}, trades {item.trades}"
        )
    continue_row, watch_row, switch_row = _report_mainline_preference_rows(recommendations)
    lines.extend(["", "## 次日预案", ""])
    if continue_row:
        lines.append(f"- {_report_mainline_followup_text(continue_row)}")
    if watch_row:
        lines.append(f"- {_report_mainline_followup_text(watch_row)}")
    if switch_row:
        lines.append(f"- {_report_mainline_followup_text(switch_row)}")
    if not any((continue_row, watch_row, switch_row)):
        lines.append("- 当前没有清晰的延续/切换信号，次日先观察盘面确认。")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    return ReportArtifacts(str(markdown_path), str(csv_path), str(json_path))


def export_strategy_history_report(
    *,
    report: StrategyHistoryReport,
    output_dir: str | Path,
    selected_strategy: str = "",
    comparison_rows: list[dict[str, Any]] | None = None,
    leaderboard_rows: list[dict[str, Any]] | None = None,
    title: str = "历史战法统计",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, markdown_path = _unique_report_paths(root, "strategy_history")

    target_strategy = str(selected_strategy or "").strip()
    summary_rows = list(report.summaries)
    trade_rows = list(report.trades)
    if target_strategy:
        summary_rows = [item for item in summary_rows if item.strategy_name == target_strategy]
        trade_rows = [item for item in trade_rows if item.strategy_name == target_strategy]
    equity_rows = [item for item in report.equity_points if not target_strategy or item.strategy_name == target_strategy]
    yearly_rows = [item for item in report.yearly_stats if not target_strategy or item.strategy_name == target_strategy]
    monthly_rows = [item for item in report.monthly_stats if not target_strategy or item.strategy_name == target_strategy]
    compare_rows: list[dict[str, Any]] = []
    for item in (comparison_rows or []):
        payload = _to_payload(item)
        if isinstance(payload, dict):
            compare_rows.append(payload)
    board_rows: list[dict[str, Any]] = []
    for item in (leaderboard_rows or []):
        payload = _to_payload(item)
        if isinstance(payload, dict):
            board_rows.append(payload)
    if target_strategy:
        compare_rows = [item for item in compare_rows if str(item.get("strategy_name", "") or "") == target_strategy]
        board_rows = [item for item in board_rows if str(item.get("strategy_name", "") or "") == target_strategy]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        headers = [
            "section",
            "strategy_name",
            "symbol",
            "stock_id",
            "stock_name",
            "signal_date",
            "entry_date",
            "exit_date",
            "entry_price",
            "exit_price",
            "pnl_pct",
            "hold_days",
            "exit_reason",
            "signal_count",
            "trade_count",
            "filled_ratio",
            "win_rate",
            "total_return",
            "avg_return",
            "max_drawdown",
            "avg_hold_days",
            "symbol_count",
            "no_fill_count",
            "missing_data_count",
            "profit_factor",
            "payoff_ratio",
            "max_consecutive_wins",
            "max_consecutive_losses",
            "target_hits",
            "stop_hits",
            "timeout_exits",
            "end_exits",
            "source_file",
            "scenario_label",
            "scenario_note",
            "scenario_max_hold_days",
            "scenario_slippage_rate",
            "scenario_commission_rate",
            "scenario_stamp_duty_rate",
            "scenario_block_limit_up_entry",
            "scenario_block_limit_down_exit",
            "leaderboard_best_scenario_label",
            "leaderboard_best_total_return",
            "leaderboard_worst_scenario_label",
            "leaderboard_worst_total_return",
            "leaderboard_return_spread",
            "leaderboard_avg_total_return",
            "leaderboard_scenario_count",
        ]
        writer.writerow(headers)

        def write_row(section: str, values: dict[str, Any]) -> None:
            row = {"section": section}
            row.update(values)
            writer.writerow([row.get(key, "") for key in headers])

        for item in summary_rows:
            write_row(
                "summary",
                {
                    "strategy_name": item.strategy_name,
                    "signal_count": item.signal_count,
                    "trade_count": item.trade_count,
                    "filled_ratio": item.filled_ratio,
                    "win_rate": item.win_rate,
                    "total_return": item.total_return,
                    "avg_return": item.avg_return,
                    "max_drawdown": item.max_drawdown,
                    "avg_hold_days": item.avg_hold_days,
                    "symbol_count": item.symbol_count,
                    "no_fill_count": item.no_fill_count,
                    "missing_data_count": item.missing_data_count,
                    "profit_factor": item.profit_factor,
                    "payoff_ratio": item.payoff_ratio,
                    "max_consecutive_wins": item.max_consecutive_wins,
                    "max_consecutive_losses": item.max_consecutive_losses,
                    "target_hits": item.target_hits,
                    "stop_hits": item.stop_hits,
                    "timeout_exits": item.timeout_exits,
                    "end_exits": item.end_exits,
                },
            )
        for item in trade_rows:
            write_row(
                "trade",
                {
                    "strategy_name": item.strategy_name,
                    "symbol": item.symbol,
                    "stock_id": item.stock_id,
                    "stock_name": item.stock_name,
                    "signal_date": item.signal_date,
                    "entry_date": item.entry_date,
                    "exit_date": item.exit_date,
                    "entry_price": item.entry_price,
                    "exit_price": item.exit_price,
                    "pnl_pct": item.pnl_pct,
                    "hold_days": item.hold_days,
                    "exit_reason": item.exit_reason,
                    "source_file": item.source_file,
                },
            )
        for item in compare_rows:
            write_row(
                "comparison",
                {
                    "strategy_name": item.get("strategy_name", ""),
                    "signal_count": item.get("signal_count", ""),
                    "trade_count": item.get("trade_count", ""),
                    "filled_ratio": item.get("filled_ratio", ""),
                    "win_rate": item.get("win_rate", ""),
                    "total_return": item.get("total_return", ""),
                    "max_drawdown": item.get("max_drawdown", ""),
                    "avg_hold_days": item.get("avg_hold_days", ""),
                    "profit_factor": item.get("profit_factor", ""),
                    "payoff_ratio": item.get("payoff_ratio", ""),
                    "max_consecutive_losses": item.get("max_consecutive_losses", ""),
                    "scenario_label": item.get("scenario_label", ""),
                    "scenario_note": item.get("scenario_note", ""),
                    "scenario_max_hold_days": item.get("max_hold_days", ""),
                    "scenario_slippage_rate": item.get("slippage_rate", ""),
                    "scenario_commission_rate": item.get("commission_rate", ""),
                    "scenario_stamp_duty_rate": item.get("stamp_duty_rate", ""),
                    "scenario_block_limit_up_entry": item.get("block_limit_up_entry", ""),
                    "scenario_block_limit_down_exit": item.get("block_limit_down_exit", ""),
                },
            )
        for item in board_rows:
            write_row(
                "leaderboard",
                {
                    "strategy_name": item.get("strategy_name", ""),
                    "leaderboard_best_scenario_label": item.get("best_scenario_label", ""),
                    "leaderboard_best_total_return": item.get("best_total_return", ""),
                    "leaderboard_worst_scenario_label": item.get("worst_scenario_label", ""),
                    "leaderboard_worst_total_return": item.get("worst_total_return", ""),
                    "leaderboard_return_spread": item.get("return_spread", ""),
                    "leaderboard_avg_total_return": item.get("avg_total_return", ""),
                    "leaderboard_scenario_count": item.get("scenario_count", ""),
                },
            )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "selected_strategy": target_strategy,
        "report": _to_payload(report),
        "summary_rows": [_to_payload(item) for item in summary_rows],
        "trade_rows": [_to_payload(item) for item in trade_rows],
        "equity_rows": [_to_payload(item) for item in equity_rows],
        "yearly_rows": [_to_payload(item) for item in yearly_rows],
        "monthly_rows": [_to_payload(item) for item in monthly_rows],
        "comparison_rows": compare_rows,
        "leaderboard_rows": board_rows,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 回放区间: {report.start_date} -> {report.end_date}",
        f"- 样本文件: {len(report.source_files)}",
        f"- 信号数: {len(report.signals)}",
        f"- 成交数: {len(report.trades)}",
    ]
    if target_strategy:
        lines.append(f"- 当前战法: {target_strategy}")
    lines.extend(["", "## 战法汇总", ""])
    if summary_rows:
        lines.append("| 战法 | 信号数 | 成交数 | 成交率 | 总收益 | 胜率 | 最大回撤 | 平均持有 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in summary_rows:
            lines.append(
                f"| {item.strategy_name} | {item.signal_count} | {item.trade_count} | {item.filled_ratio:.2%} | "
                f"{item.total_return:.2%} | {item.win_rate:.2%} | {item.max_drawdown:.2%} | {item.avg_hold_days:.2f} 天 |"
            )
    else:
        lines.append("- 当前筛选下暂无战法汇总。")
    lines.extend(["", "## 逐笔成交", ""])
    if trade_rows:
        lines.append("| 战法 | 股票 | 信号日 | 入场日 | 离场日 | 买入价 | 卖出价 | 收益率 | 持有天数 | 退出原因 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in trade_rows:
            stock_label = item.stock_name or item.symbol
            lines.append(
                f"| {item.strategy_name} | {stock_label} | {item.signal_date} | {item.entry_date} | {item.exit_date} | "
                f"{item.entry_price:.4f} | {item.exit_price:.4f} | {item.pnl_pct:.2%} | {item.hold_days} | {item.exit_reason} |"
            )
    else:
        lines.append("- 当前筛选下暂无逐笔成交。")
    lines.extend(["", "## 年度统计", ""])
    if yearly_rows:
        lines.append("| 战法 | 年度 | 交易数 | 胜率 | 总收益 | 平均收益 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in yearly_rows:
            lines.append(
                f"| {item.strategy_name} | {item.period} | {item.trade_count} | {item.win_rate:.2%} | {item.total_return:.2%} | {item.avg_return:.2%} |"
            )
    else:
        lines.append("- 当前筛选下暂无年度统计。")
    lines.extend(["", "## 月度统计", ""])
    if monthly_rows:
        lines.append("| 战法 | 月度 | 交易数 | 胜率 | 总收益 | 平均收益 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for item in monthly_rows:
            lines.append(
                f"| {item.strategy_name} | {item.period} | {item.trade_count} | {item.win_rate:.2%} | {item.total_return:.2%} | {item.avg_return:.2%} |"
            )
    else:
        lines.append("- 当前筛选下暂无月度统计。")
    lines.extend(["", "## 参数排行榜", ""])
    if board_rows:
        lines.append("| 战法 | 场景数 | 最佳场景 | 最佳收益 | 最差场景 | 最差收益 | 收益差 | 平均收益 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in board_rows:
            lines.append(
                f"| {item.get('strategy_name', '--')} | {int(item.get('scenario_count', 0) or 0)} | "
                f"{item.get('best_scenario_label', '--')} | {float(item.get('best_total_return', 0.0) or 0.0):.2%} | "
                f"{item.get('worst_scenario_label', '--')} | {float(item.get('worst_total_return', 0.0) or 0.0):.2%} | "
                f"{float(item.get('return_spread', 0.0) or 0.0):.2%} | {float(item.get('avg_total_return', 0.0) or 0.0):.2%} |"
            )
    else:
        lines.append("- 当前暂无参数排行榜结果。")
    lines.extend(["", "## 参数对比", ""])
    if compare_rows:
        lines.append("| 场景 | 战法 | 最长持有 | 总收益 | 胜率 | 最大回撤 | 收益因子 | 盈亏比 | 最大连亏 | 备注 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for item in compare_rows:
            lines.append(
                f"| {item.get('scenario_label', '--')} | {item.get('strategy_name', '--')} | "
                f"{int(item.get('max_hold_days', 0) or 0)} 天 | "
                f"{float(item.get('total_return', 0.0) or 0.0):.2%} | "
                f"{float(item.get('win_rate', 0.0) or 0.0):.2%} | "
                f"{float(item.get('max_drawdown', 0.0) or 0.0):.2%} | "
                f"{float(item.get('profit_factor', 0.0) or 0.0):.2f} | "
                f"{float(item.get('payoff_ratio', 0.0) or 0.0):.2f} | "
                f"{int(item.get('max_consecutive_losses', 0) or 0)} | "
                f"{item.get('scenario_note', '--')} |"
            )
    else:
        lines.append("- 当前暂无参数对比结果，可先在界面运行“战法参数对比”。")
    if report.notes:
        lines.extend(["", "## 备注", ""])
        lines.extend(f"- {item}" for item in report.notes[:20])

    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return ReportArtifacts(str(markdown_path), str(csv_path), str(json_path))


def export_daily_trade_plan(
    *,
    output_dir: str | Path,
    recommendations: list[RecommendationRow],
    trade_plan: Any,
    holdings: list[HoldingRecord],
    focus_themes: list[str] | None = None,
    license_plan: str = "TRIAL",
    template_name: str = "balanced",
    focus_only: bool = False,
    candidate_limit: int = 10,
    title: str = "盘前交易计划",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, markdown_path = _unique_report_paths(root, "daily_plan")

    decisions = list(getattr(trade_plan, "decisions", []))
    position_advice = list(getattr(trade_plan, "position_advice", []))
    pulse = getattr(trade_plan, "market_pulse", None)
    plan_recommendations = _filter_recommendations_for_plan(
        recommendations,
        focus_themes=focus_themes,
        template_name=template_name,
        focus_only=focus_only,
        candidate_limit=candidate_limit,
    )
    theme_rows, leader_rows = summarize_themes(plan_recommendations)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "section",
                "stock_name",
                "stock_id",
                "symbol",
                "action",
                "score",
                "price",
                "stop",
                "target",
                "opportunity_tier",
                "risk_flag",
                "risk_reward_ratio",
                "signal_source",
                "next_focus",
                "invalidation_reason",
                "note",
            ]
        )

        for item in plan_recommendations:
            writer.writerow(
                [
                    "daily_pool",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    item.total_score,
                    item.entry_price or item.close,
                    item.stop_price or "",
                    item.target_price or "",
                    getattr(item, "opportunity_tier", ""),
                    getattr(item, "mainline_risk_flag", ""),
                    round(float(getattr(item, "risk_reward_ratio", 0.0) or 0.0), 2),
                    getattr(item, "signal_source", ""),
                    getattr(item, "next_focus", ""),
                    getattr(item, "invalidation_reason", ""),
                    item.rationale,
                ]
            )

        for item in decisions:
            writer.writerow(
                [
                    "trade_plan",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    round(item.confidence * 100, 2),
                    item.planned_entry,
                    item.planned_stop,
                    item.planned_target,
                    getattr(item, "opportunity_tier", ""),
                    "",
                    round(float(getattr(item, "risk_reward_ratio", 0.0) or 0.0), 2),
                    "trade_plan",
                    getattr(item, "next_focus", ""),
                    "",
                    item.rationale,
                ]
            )

        for item in position_advice:
            writer.writerow(
                [
                    "position_advice",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    round(item.confidence * 100, 2),
                    item.current_price,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    item.rationale,
                ]
            )

        for item in holdings:
            writer.writerow(
                [
                    "holdings",
                    item.symbol.split(".")[-1],
                    item.symbol.split(".")[-1],
                    item.symbol,
                    "HOLD",
                    "",
                    item.cost_price,
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    f"quantity={item.quantity}, market_value={item.market_value:.2f}",
                ]
            )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "focus_themes": list(focus_themes or []),
        "license_plan": license_plan,
        "template_name": template_name,
        "focus_only": focus_only,
        "candidate_limit": candidate_limit,
        "recommendations": [_to_payload(item) for item in plan_recommendations],
        "trade_plan": _to_payload(trade_plan),
        "holdings": [_to_payload(item) for item in holdings],
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 授权方案: {license_plan}",
        f"- 报告模板: {template_name}",
        f"- 市场温度: {getattr(trade_plan, 'market_sentiment', '未计算')}",
        f"- 情绪分数: {getattr(trade_plan, 'sentiment_score', 0.0):.1f}",
    ]
    if focus_themes:
        lines.append(f"- 用户关注题材: {', '.join(focus_themes)}")
    lines.append(f"- 仅关注题材: {'是' if focus_only else '否'}")
    lines.append(f"- 股票池展示上限: {candidate_limit}")
    if pulse is not None:
        lines.extend(
            [
                f"- 市场周期: {getattr(pulse, 'market_regime', '未计算')}",
                f"- 风险等级: {getattr(pulse, 'risk_level', '未计算')}",
                f"- 建议总仓位上限: {getattr(pulse, 'max_total_exposure', 0.0):.0%}",
                f"- 建议新增仓位数: {getattr(trade_plan, 'max_new_positions', 0)}",
            ]
        )

    lines.extend(["", "## 市场情绪摘要", ""])
    if pulse is not None:
        lines.extend(
            [
                f"- 买入占比: {pulse.buy_ratio:.0%}",
                f"- 候选平均分: {pulse.average_total_score:.1f}",
                f"- 强势候选数: {pulse.strong_candidates}",
                f"- 风险提示候选数: {pulse.caution_candidates}",
            ]
        )
    else:
        lines.append("- 当前尚未生成市场情绪快照。")

    lines.extend(["", "## 今日主线题材", ""])
    if theme_rows:
        for item in theme_rows:
            lines.append(
                f"- {item.theme_rank}. {item.theme_name} | 热度 {item.strength_score:.1f} | "
                f"持续性 {item.continuation_score:.1f} | 消息 {item.news_score:.1f} | 风险 {item.risk_flag}"
            )
    else:
        lines.append("- 当前没有明确的题材热度结果。")

    lines.extend(["", "## 龙头观察", ""])
    if leader_rows:
        for item in leader_rows:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.theme_name} | {_display_leader_level(item.leader_level)} | "
                f"龙头分 {item.leader_score:.1f} | 动作 {item.action}"
            )
    else:
        lines.append("- 当前没有明显的龙头候选。")

    lines.extend(["", "## 每日股票池", ""])
    continue_row, watch_row, switch_row = _report_mainline_preference_rows(plan_recommendations)
    lines.extend(["", "## 主线预案", ""])
    if continue_row:
        lines.append(f"- {_report_mainline_followup_text(continue_row)}")
    if watch_row:
        lines.append(f"- {_report_mainline_followup_text(watch_row)}")
    if switch_row:
        lines.append(f"- {_report_mainline_followup_text(switch_row)}")
    if not any((continue_row, watch_row, switch_row)):
        lines.append("- 当前没有足够清晰的延续/切换信号，按观察模式处理。")

    if plan_recommendations:
        for index, item in enumerate(plan_recommendations, start=1):
            lines.append(
                f"{index}. {item.stock_name} ({item.stock_id} / {item.symbol}) | 总分 {item.total_score:.1f} | "
                f"动作 {item.action} | 买点 {(item.entry_price or item.close):.2f} | 止损 {(item.stop_price or 0.0):.2f} | "
                f"目标 {(item.target_price or 0.0):.2f}"
            )
            lines.append(
                f"   分层: {getattr(item, 'opportunity_tier', '') or '--'} | 风险: {getattr(item, 'mainline_risk_flag', '') or '--'} | "
                f"盈亏比: {float(getattr(item, 'risk_reward_ratio', 0.0) or 0.0):.2f} | 来源: {getattr(item, 'signal_source', '') or '--'}"
            )
            if getattr(item, "next_focus", ""):
                lines.append(f"   下一步: {getattr(item, 'next_focus', '')}")
            if getattr(item, "invalidation_reason", ""):
                lines.append(f"   失效条件: {getattr(item, 'invalidation_reason', '')}")
            lines.append(f"   理由: {item.rationale}")
    else:
        lines.append("- 今日未生成股票池结果。")

    lines.extend(["", "## 今日交易计划", ""])
    if decisions:
        for item in decisions:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.action} | 置信 {item.confidence:.0%} | "
                f"计划买点 {item.planned_entry:.2f} | 止损 {item.planned_stop:.2f} | 目标 {item.planned_target:.2f} | "
                f"建议资金 {item.suggested_budget:,.0f}"
            )
            lines.append(
                f"  分层: {getattr(item, 'opportunity_tier', '') or '--'} | 执行准备: {float(getattr(item, 'execution_readiness', 0.0) or 0.0):.1f} | "
                f"盈亏比: {float(getattr(item, 'risk_reward_ratio', 0.0) or 0.0):.2f}"
            )
            if getattr(item, "next_focus", ""):
                lines.append(f"  下一步: {getattr(item, 'next_focus', '')}")
            lines.append(f"  说明: {item.rationale}")
    else:
        lines.append("- 当前没有新的交易计划。")

    lines.extend(["", "## 持仓处理建议", ""])
    if position_advice:
        for item in position_advice:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.action} | 盈亏 {item.pnl_pct:.2%} | "
                f"现价 {item.current_price:.2f} | 成本 {item.cost_price:.2f}"
            )
            lines.append(f"  说明: {item.rationale}")
    else:
        lines.append("- 当前没有持仓处理建议。")

    lines.extend(["", "## 风险提示", ""])
    for note in getattr(trade_plan, "notes", []) or ["所有交易动作需人工确认后执行。"]:
        lines.append(f"- {note}")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return ReportArtifacts(str(markdown_path), str(csv_path), str(json_path))


def export_end_of_day_review(
    *,
    output_dir: str | Path,
    recommendations: list[RecommendationRow],
    trade_plan: Any,
    board_plan: Any,
    holdings: list[HoldingRecord],
    cash_snapshot: Any | None = None,
    scan_rows: list[ScanRow] | None = None,
    focus_themes: list[str] | None = None,
    license_plan: str = "TRIAL",
    title: str = "收盘复盘",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    csv_path, json_path, markdown_path = _unique_report_paths(root, "end_of_day_review")

    decisions = list(getattr(trade_plan, "decisions", []))
    position_advice = list(getattr(trade_plan, "position_advice", []))
    board_candidates = list(getattr(board_plan, "candidates", []))
    board_monitors = list(getattr(board_plan, "monitor_rows", []))
    pulse = getattr(trade_plan, "market_pulse", None)
    theme_rows, leader_rows = summarize_themes(recommendations)

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["section", "stock_name", "stock_id", "symbol", "action", "score", "price", "stop", "target", "note"])

        for item in recommendations:
            writer.writerow(
                [
                    "daily_pool",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    item.total_score,
                    item.entry_price or item.close,
                    item.stop_price or "",
                    item.target_price or "",
                    item.rationale,
                ]
            )

        for item in decisions:
            writer.writerow(
                [
                    "trade_plan",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    round(item.confidence * 100, 2),
                    item.planned_entry,
                    item.planned_stop,
                    item.planned_target,
                    item.rationale,
                ]
            )

        for item in board_candidates:
            writer.writerow(
                [
                    "board_candidate",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.trigger_style,
                    item.board_score,
                    item.planned_entry,
                    item.planned_stop,
                    item.planned_target,
                    item.rationale,
                ]
            )

        for item in board_monitors:
            writer.writerow(
                [
                    "board_monitor",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.monitor_state,
                    item.strength_score,
                    "",
                    "",
                    "",
                    f"{item.action_plan} | {item.note}",
                ]
            )

        for item in position_advice:
            writer.writerow(
                [
                    "position_advice",
                    item.stock_name,
                    item.stock_id,
                    item.symbol,
                    item.action,
                    round(item.confidence * 100, 2),
                    item.current_price,
                    "",
                    "",
                    item.rationale,
                ]
            )

        for item in holdings:
            writer.writerow(
                [
                    "holdings",
                    item.symbol.split(".")[-1],
                    item.symbol.split(".")[-1],
                    item.symbol,
                    "HOLD",
                    "",
                    item.cost_price,
                    "",
                    "",
                    f"quantity={item.quantity}, market_value={item.market_value:.2f}",
                ]
            )

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "focus_themes": list(focus_themes or []),
        "license_plan": license_plan,
        "scan_rows": [_to_payload(item) for item in scan_rows or []],
        "recommendations": [_to_payload(item) for item in recommendations],
        "trade_plan": _to_payload(trade_plan),
        "board_plan": _to_payload(board_plan),
        "holdings": [_to_payload(item) for item in holdings],
        "cash_snapshot": _to_payload(cash_snapshot),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# {title}",
        "",
        f"- 导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- 授权方案: {license_plan}",
        f"- 市场温度: {getattr(trade_plan, 'market_sentiment', '未计算')}",
        f"- 情绪分数: {getattr(trade_plan, 'sentiment_score', 0.0):.1f}",
        f"- 打板温度: {getattr(board_plan, 'temperature', '未计算')}",
        f"- 打板候选均分: {getattr(board_plan, 'avg_score', 0.0):.1f}",
    ]
    if focus_themes:
        lines.append(f"- 用户关注题材: {', '.join(focus_themes)}")
    if pulse is not None:
        lines.extend(
            [
                f"- 市场周期: {getattr(pulse, 'market_regime', '未计算')}",
                f"- 风险等级: {getattr(pulse, 'risk_level', '未计算')}",
                f"- 建议总仓位上限: {getattr(pulse, 'max_total_exposure', 0.0):.0%}",
            ]
        )

    lines.extend(["", "## 主线题材", ""])
    if theme_rows:
        for item in theme_rows:
            lines.append(
                f"- {item.theme_rank}. {item.theme_name} | 热度 {item.strength_score:.1f} | "
                f"持续性 {item.continuation_score:.1f} | 龙头 {item.leader_count} | 风险 {item.risk_flag}"
            )
    else:
        lines.append("- 当前没有明确题材热度结果。")

    lines.extend(["", "## 龙头股摘要", ""])
    if leader_rows:
        for item in leader_rows:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.theme_name} | {_display_leader_level(item.leader_level)} | "
                f"龙头分 {item.leader_score:.1f} | 动作 {item.action}"
            )
    else:
        lines.append("- 当前没有明显龙头候选。")

    lines.extend(["", "## 今日股票池", ""])
    if recommendations:
        for index, item in enumerate(recommendations[:10], start=1):
            lines.append(
                f"{index}. {item.stock_name} ({item.stock_id} / {item.symbol}) | 总分 {item.total_score:.1f} | "
                f"{item.rationale}"
            )
    else:
        lines.append("- 今日无股票池结果。")

    lines.extend(["", "## 今日交易计划", ""])
    if decisions:
        for item in decisions:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.action} | 置信 {item.confidence:.0%} | "
                f"计划买点 {item.planned_entry:.2f} | 止损 {item.planned_stop:.2f} | 目标 {item.planned_target:.2f}"
            )
    else:
        lines.append("- 当前没有新的交易计划。")

    lines.extend(["", "## 持仓处理建议", ""])
    if position_advice:
        for item in position_advice:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.action} | 盈亏 {item.pnl_pct:.2%} | {item.rationale}"
            )
    else:
        lines.append("- 当前没有持仓处理建议。")

    lines.extend(["", "## 打板候选", ""])
    if board_candidates:
        for item in board_candidates:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | 分数 {item.board_score:.1f} | {item.trigger_style} | "
                f"风控 {item.risk_level}"
            )
    else:
        lines.append("- 当前没有满足条件的打板候选。")

    lines.extend(["", "## 炸板 / 回封监控", ""])
    if board_monitors:
        for item in board_monitors:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.monitor_state} | 强度 {item.strength_score:.1f} | "
                f"回封概率 {item.reboard_probability:.1f} | 炸板风险 {item.blast_risk:.1f}"
            )
    else:
        lines.append("- 当前没有监控对象。")

    lines.extend(["", "## 资金与持仓", ""])
    if cash_snapshot is not None:
        lines.append(
            f"- 可用资金: {getattr(cash_snapshot, 'available_cash', 0.0):,.2f} | "
            f"总资产: {getattr(cash_snapshot, 'total_assets', 0.0):,.2f}"
        )
    else:
        lines.append("- 尚未导入资金快照。")

    if holdings:
        for item in holdings:
            lines.append(
                f"- {item.symbol}: 数量 {item.quantity}, 可用 {item.available}, 成本 {item.cost_price:.2f}, "
                f"市值 {item.market_value:,.2f}"
            )
    else:
        lines.append("- 当前没有持仓数据。")

    markdown_path.write_text("\n".join(lines), encoding="utf-8")
    return ReportArtifacts(str(markdown_path), str(csv_path), str(json_path))


def _to_payload(value: Any) -> Any:
    if value is None:
        return None
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, list):
        return [_to_payload(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_payload(item) for key, item in value.items()}
    return value
