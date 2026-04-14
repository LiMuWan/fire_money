from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from quant_hunter.models import PaperTradingState
from quant_hunter.paper_trading import build_strategy_rotation_snapshot, summarize_paper_trading_performance


def paper_experiment_role_specs_v43(
    state: PaperTradingState,
    analytics: dict[str, object],
    rotation_rows: list[dict[str, object]],
    *,
    paper_lab_stage_fn=None,
) -> list[dict[str, str]]:
    if paper_lab_stage_fn is None:
        from quant_hunter.ui_window_visibility_patches import paper_lab_stage_v39

        paper_lab_stage_fn = paper_lab_stage_v39
    strategy_rows = {
        str(item.get("strategy_name", "") or ""): dict(item)
        for item in list(analytics.get("strategy_rows", []) or [])
    }
    stage_title, _ = paper_lab_stage_fn(state, analytics)
    slots: list[tuple[str, str, dict[str, object] | None]] = []
    lead_row = rotation_rows[0] if rotation_rows else None
    compare_row = rotation_rows[1] if len(rotation_rows) > 1 else None
    trailing_row = None
    if len(rotation_rows) > 2:
        trailing_row = rotation_rows[-1]
        if trailing_row is lead_row or trailing_row is compare_row:
            trailing_row = None
    slots.extend(
        [
            ("lead", "主测战法", lead_row),
            ("compare", "对照战法", compare_row),
            ("watch", "降权观察", trailing_row),
        ]
    )

    specs: list[dict[str, str]] = []
    for slot_key, title, rotation in slots:
        if rotation:
            strategy_name = str(rotation.get("strategy_name", "") or "待确认")
            realized = float(rotation.get("realized_pnl", 0.0) or 0.0)
            multiplier = float(rotation.get("budget_multiplier", 1.0) or 1.0)
            bias_label = str(rotation.get("bias_label", "") or "中性")
            sample_count = int(rotation.get("sample_count", 0) or 0)
            metrics = strategy_rows.get(strategy_name, {})
            win_rate = float(metrics.get("win_rate", rotation.get("win_rate", 0.0)) or 0.0)
            if slot_key == "lead":
                next_step = "继续加样本，优先看同类标的复现。"
            elif slot_key == "compare":
                next_step = "保留对照，避免只看单一胜样本。"
            else:
                next_step = "若继续掉队，下轮先降权或暂停。"
            detail = (
                f"{bias_label} x{multiplier:.2f} | 样本 {sample_count} | 胜率 {win_rate:.1%} | "
                f"已实现 {realized:,.0f} | {next_step}"
            )
        else:
            strategy_name = "待补样本"
            if slot_key == "lead":
                detail = f"{stage_title} | 先跑出第一套可闭环样本。"
            elif slot_key == "compare":
                detail = "主测尚未稳定，先不要急着扩大战法对照。"
            else:
                detail = "当前没有明确掉队战法，继续跟踪样本分化。"
        specs.append(
            {
                "key": slot_key,
                "title": title,
                "headline": f"{title}：{strategy_name}",
                "detail": detail,
            }
        )
    return specs


def paper_experiment_table_context_v44(
    analytics: dict[str, object],
    rotation_rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    strategy_rows = {
        str(item.get("strategy_name", "") or ""): dict(item)
        for item in list(analytics.get("strategy_rows", []) or [])
    }
    lead_name = str(rotation_rows[0].get("strategy_name", "") or "") if rotation_rows else ""
    compare_name = str(rotation_rows[1].get("strategy_name", "") or "") if len(rotation_rows) > 1 else ""
    watch_name = ""
    if len(rotation_rows) > 2:
        trailing_name = str(rotation_rows[-1].get("strategy_name", "") or "")
        if trailing_name not in {lead_name, compare_name}:
            watch_name = trailing_name

    lead_metrics = strategy_rows.get(lead_name, {})
    lead_rotation = next(
        (item for item in rotation_rows if str(item.get("strategy_name", "") or "") == lead_name),
        {},
    )
    lead_win_rate = float(lead_metrics.get("win_rate", lead_rotation.get("win_rate", 0.0)) or 0.0)
    lead_hold_days = float(lead_metrics.get("avg_hold_days", lead_rotation.get("avg_hold_days", 0.0)) or 0.0)

    contexts: dict[str, dict[str, object]] = {}
    for rotation in rotation_rows or []:
        strategy_name = str(rotation.get("strategy_name", "") or "")
        if not strategy_name:
            continue
        metrics = strategy_rows.get(strategy_name, {})
        sample_count = int(
            rotation.get(
                "sample_count",
                int(metrics.get("buy_count", 0) or 0) + int(metrics.get("sell_count", 0) or 0),
            )
            or 0
        )
        win_rate = float(metrics.get("win_rate", rotation.get("win_rate", 0.0)) or 0.0)
        avg_hold_days = float(metrics.get("avg_hold_days", rotation.get("avg_hold_days", 0.0)) or 0.0)
        realized_pnl = float(metrics.get("realized_pnl", rotation.get("realized_pnl", 0.0)) or 0.0)
        rotation_score = float(rotation.get("rotation_score", 0.0) or 0.0)
        budget_multiplier = float(rotation.get("budget_multiplier", 1.0) or 1.0)
        bias_label = str(rotation.get("bias_label", "") or "中性")

        if strategy_name == lead_name:
            role_label = "主测"
        elif strategy_name == compare_name:
            role_label = "对照"
        elif strategy_name == watch_name or bias_label == "降权":
            role_label = "观察"
        else:
            role_label = "备选"

        win_rate_delta = 0.0 if strategy_name == lead_name else win_rate - lead_win_rate
        hold_delta = 0.0
        if strategy_name != lead_name and lead_hold_days > 0 and avg_hold_days > 0:
            hold_delta = avg_hold_days - lead_hold_days

        if role_label == "主测":
            if sample_count < 4:
                decision = "继续主测，先补样本"
            elif rotation_score >= 0.18 or budget_multiplier > 1.0:
                decision = "继续主测"
            elif win_rate < 0.45:
                decision = "主测保留，降低仓位"
            else:
                decision = "继续主测观察"
        elif role_label == "对照":
            if sample_count < 3:
                decision = "保留对照，补样本"
            elif win_rate_delta >= 0.05 and rotation_score >= -0.05:
                decision = "具备转主测机会"
            else:
                decision = "保留对照"
        elif role_label == "观察":
            if sample_count < 3:
                decision = "先补样本后定级"
            else:
                decision = "降权观察"
        elif sample_count < 3:
            decision = "先补样本"
        elif realized_pnl < 0 or rotation_score < -0.18:
            decision = "复盘失败样本"
        else:
            decision = "继续观察"

        contexts[strategy_name] = {
            "role_label": role_label,
            "decision": decision,
            "win_rate": win_rate,
            "win_rate_delta": round(win_rate_delta, 4),
            "avg_hold_days": round(avg_hold_days, 2),
            "hold_delta": round(hold_delta, 2),
            "budget_multiplier": round(budget_multiplier, 4),
            "bias_label": bias_label,
            "rotation_score": round(rotation_score, 4),
            "realized_pnl": round(realized_pnl, 2),
            "sample_count": sample_count,
            "buy_count": int(metrics.get("buy_count", 0) or 0),
            "sell_count": int(metrics.get("sell_count", 0) or 0),
        }
    return contexts


def _canonical_paper_strategy_name_v45(strategy_name: str) -> str:
    raw = str(strategy_name or "").strip()
    alias_map = {
        "龙头主线": "龙头模型",
        "资金承接": "主力雷达",
        "强势接力": "擒龙打板",
        "打板策略": "擒龙打板",
        "趋势低吸": "价值低吸",
        "尾盘买入": "尾盘买入法",
        "一日持股": "一日持股法",
        "隔日强势": "一日持股法",
        "综合决策": "掘龙决策",
        "掘龙": "掘龙决策",
    }
    return alias_map.get(raw, raw)


def paper_strategy_experiment_bridge_v45(
    state: PaperTradingState,
    strategy_name: str,
    *,
    analytics: dict[str, object] | None = None,
    rotation_rows: list[dict[str, object]] | None = None,
) -> dict[str, str]:
    canonical_strategy = _canonical_paper_strategy_name_v45(strategy_name) or "掘龙决策"
    paper_state = state if isinstance(state, PaperTradingState) else PaperTradingState()
    experiment_analytics = analytics if analytics is not None else summarize_paper_trading_performance(paper_state)
    experiment_rows = rotation_rows if rotation_rows is not None else build_strategy_rotation_snapshot(paper_state)

    if not getattr(paper_state, "enabled", False):
        return {
            "badge": "待初始化",
            "title": "实验待初始化",
            "detail": "模拟盘还没启用，当前没有可复用的主测/对照结论。",
            "cta": "先初始化模拟盘并跑一轮，再决定哪些推荐值得进入真实交易链路。",
        }

    if not experiment_rows:
        return {
            "badge": "样本积累",
            "title": f"样本积累中 | {canonical_strategy}",
            "detail": "模拟盘已经启用，但还没有形成稳定战法排序。",
            "cta": "推荐页先按主线与价位筛票，等模拟盘补出闭环样本后再放大战法结论。",
        }

    contexts = paper_experiment_table_context_v44(experiment_analytics, experiment_rows)
    lead_name = str(experiment_rows[0].get("strategy_name", "") or "待补样本")
    compare_name = str(experiment_rows[1].get("strategy_name", "") or "待补样本") if len(experiment_rows) > 1 else "待补样本"
    context = contexts.get(canonical_strategy)

    if context is None:
        return {
            "badge": "备选",
            "title": f"未进入实验前排 | {canonical_strategy}",
            "detail": f"当前实验主测 {lead_name} | 对照 {compare_name}，这套战法还没进入前排样本。",
            "cta": "推荐页先把它当备选观察，不要脱离实验排序直接推进真实交易。",
        }

    role_label = str(context.get("role_label", "") or "备选")
    decision = str(context.get("decision", "") or "继续观察")
    sample_count = int(context.get("sample_count", 0) or 0)
    win_rate = float(context.get("win_rate", 0.0) or 0.0)
    avg_hold_days = float(context.get("avg_hold_days", 0.0) or 0.0)
    budget_multiplier = float(context.get("budget_multiplier", 1.0) or 1.0)

    if role_label == "主测":
        cta = "推荐页优先筛同战法前排，交易页按主测纪律推进，但先别因为单票强弱临时改打法。"
    elif role_label == "对照":
        cta = "推荐页继续保留对照观察，不和主测抢仓位，等样本继续领先再考虑转主测。"
    elif role_label == "观察":
        cta = "交易页只保留观察或小样本试错，先复盘失败样本，避免把降权战法直接放大到真实执行。"
    else:
        cta = "先把它放在推荐页备选区观察，等样本和胜率继续抬升后再进入交易链路。"

    return {
        "badge": role_label,
        "title": f"{role_label} | {canonical_strategy} | {decision}",
        "detail": f"样本 {sample_count} | 胜率 {win_rate:.1%} | 平均持有 {avg_hold_days:.1f} 天 | 预算 x{budget_multiplier:.2f}",
        "cta": cta,
    }


def apply_paper_experiment_patches(
    window_cls: type,
    *,
    paper_lab_stage_fn,
) -> None:
    if getattr(window_cls, "_qh_paper_experiment_patches_applied_v43", False):
        return

    original_install_paper_trading_workspace_v43 = window_cls._install_paper_trading_workspace
    original_refresh_paper_trading_panels_v43 = window_cls._refresh_paper_trading_panels

    def _install_paper_trading_workspace_v43(self) -> None:
        original_install_paper_trading_workspace_v43(self)
        widget = getattr(self, "paper_experiment_text", None)
        if not isinstance(widget, QTextEdit) or hasattr(self, "paper_experiment_role_labels"):
            return
        parent = widget.parentWidget()
        layout = parent.layout() if isinstance(parent, QWidget) else None
        if not isinstance(layout, QVBoxLayout):
            return

        summary_label = QLabel("实验编排：先确定主测、保留对照，再识别需要降权或暂停的战法。")
        summary_label.setObjectName("inlineHint")
        summary_label.setWordWrap(True)
        self.paper_experiment_summary_label = summary_label
        layout.insertWidget(0, summary_label)

        rail = QWidget()
        rail_layout = QHBoxLayout(rail)
        rail_layout.setContentsMargins(0, 0, 0, 0)
        rail_layout.setSpacing(8)
        self.paper_experiment_role_labels = {}
        for key in ("lead", "compare", "watch"):
            label = QLabel("等待实验样本")
            label.setObjectName("focusStateLabel")
            label.setWordWrap(True)
            label.setMinimumHeight(72)
            self.paper_experiment_role_labels[key] = label
            rail_layout.addWidget(label, stretch=1)
        layout.insertWidget(1, rail)
        self.paper_experiment_role_rail = rail

    def _refresh_paper_trading_panels_v43(self) -> None:
        original_refresh_paper_trading_panels_v43(self)
        role_labels = getattr(self, "paper_experiment_role_labels", {})
        if not isinstance(role_labels, dict) or not role_labels:
            return
        state = getattr(self, "paper_trading_state", getattr(self.state, "paper_trading_state", PaperTradingState()))
        analytics = summarize_paper_trading_performance(state)
        rotation_rows = build_strategy_rotation_snapshot(state)
        specs = paper_experiment_role_specs_v43(
            state,
            analytics,
            rotation_rows,
            paper_lab_stage_fn=paper_lab_stage_fn,
        )
        for spec in specs:
            label = role_labels.get(spec["key"])
            if isinstance(label, QLabel):
                text = f"{spec['headline']}\n{spec['detail']}"
                self._set_label_text_if_changed(label, text, tooltip=text)

        stage_title, stage_detail = paper_lab_stage_fn(state, analytics)
        summary_label = getattr(self, "paper_experiment_summary_label", None)
        if isinstance(summary_label, QLabel):
            lead_name = specs[0]["headline"].split("：", 1)[-1] if specs else "待补样本"
            compare_name = specs[1]["headline"].split("：", 1)[-1] if len(specs) > 1 else "待补样本"
            summary_text = f"实验编排：{stage_title} | 主测 {lead_name} | 对照 {compare_name} | {stage_detail}"
            self._set_label_text_if_changed(summary_label, summary_text, tooltip=summary_text)

        status_label = getattr(self, "paper_lab_toggle_status_label", None)
        if isinstance(status_label, QLabel) and not getattr(self, "_qh_paper_lab_detail_visible_v39", False):
            lead_name = specs[0]["headline"].split("：", 1)[-1] if specs else "待补样本"
            compare_name = specs[1]["headline"].split("：", 1)[-1] if len(specs) > 1 else "待补样本"
            status_text = f"原始流水已折叠，先看实验编排。主测 {lead_name}；对照 {compare_name}；当前阶段 {stage_title}。"
            self._set_label_text_if_changed(status_label, status_text, tooltip=status_text)

    window_cls._install_paper_trading_workspace = _install_paper_trading_workspace_v43
    window_cls._refresh_paper_trading_panels = _refresh_paper_trading_panels_v43
    window_cls._qh_paper_experiment_patches_applied_v43 = True
