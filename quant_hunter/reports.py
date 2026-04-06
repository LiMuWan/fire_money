from __future__ import annotations

import csv
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import HoldingRecord, OptimizationRun, RecommendationRow, ReportArtifacts, ScanRow, SymbolBacktestSummary
from .theme import summarize_themes


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

    if template_name == "focus":
        selected.sort(
            key=lambda item: (
                item.theme_name in focus_set,
                item.theme_rank == 1,
                item.total_score,
                item.theme_score,
                item.stock_id,
            ),
            reverse=True,
        )
    elif template_name == "aggressive":
        selected.sort(
            key=lambda item: (item.leader_score, item.news_score, item.total_score, item.stock_id),
            reverse=True,
        )
    elif template_name == "defensive":
        selected.sort(
            key=lambda item: (item.position_score, item.persistence_score, item.total_score, item.stock_id),
            reverse=True,
        )
    else:
        selected.sort(
            key=lambda item: (item.total_score, item.theme_score, item.technical_score, item.stock_id),
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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = root / f"optimization_{stamp}.csv"
    json_path = root / f"optimization_{stamp}.json"
    markdown_path = root / f"optimization_{stamp}.md"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "rank",
                "objective",
                "avg_return",
                "avg_drawdown",
                "avg_win_rate",
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
                    item.avg_return,
                    item.avg_drawdown,
                    item.avg_win_rate,
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
        "| Rank | Objective | Avg Return | Avg Drawdown | Avg Win Rate | Trades | Params |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        markdown_lines.append(
            f"| {item.rank} | {item.objective:.4f} | {item.avg_return:.2%} | {item.avg_drawdown:.2%} | "
            f"{item.avg_win_rate:.2%} | {item.trade_count} | `{json.dumps(item.params, ensure_ascii=False)}` |"
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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = root / f"workspace_{stamp}.csv"
    json_path = root / f"workspace_{stamp}.json"
    markdown_path = root / f"workspace_{stamp}.md"

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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = root / f"daily_plan_{stamp}.csv"
    json_path = root / f"daily_plan_{stamp}.json"
    markdown_path = root / f"daily_plan_{stamp}.md"

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
        writer.writerow(["section", "stock_name", "stock_id", "symbol", "action", "score", "price", "stop", "target", "note"])

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
    if plan_recommendations:
        for index, item in enumerate(plan_recommendations, start=1):
            lines.append(
                f"{index}. {item.stock_name} ({item.stock_id} / {item.symbol}) | 总分 {item.total_score:.1f} | "
                f"动作 {item.action} | 买点 {(item.entry_price or item.close):.2f} | 止损 {(item.stop_price or 0.0):.2f} | "
                f"目标 {(item.target_price or 0.0):.2f}"
            )
            lines.append(f"   理由: {item.rationale}")
    else:
        lines.append("- 今日未生成股票池结果。")

    lines.extend(["", "## 今日建仓计划", ""])
    if decisions:
        for item in decisions:
            lines.append(
                f"- {item.stock_name} ({item.stock_id}) | {item.action} | 置信 {item.confidence:.0%} | "
                f"计划买点 {item.planned_entry:.2f} | 止损 {item.planned_stop:.2f} | 目标 {item.planned_target:.2f} | "
                f"建议资金 {item.suggested_budget:,.0f}"
            )
            lines.append(f"  说明: {item.rationale}")
    else:
        lines.append("- 当前没有新的建仓计划。")

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
    title: str = "收盘复盘日报",
) -> ReportArtifacts:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = root / f"end_of_day_review_{stamp}.csv"
    json_path = root / f"end_of_day_review_{stamp}.json"
    markdown_path = root / f"end_of_day_review_{stamp}.md"

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

    lines.extend(["", "## 今日 5 只交易计划", ""])
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
