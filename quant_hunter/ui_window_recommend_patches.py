from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import QLabel, QPushButton, QTextEdit

from quant_hunter.models import PaperTradingState
from quant_hunter.strategy_registry import resolved_primary_strategy
from quant_hunter.ui_window_paper_experiment_patches import paper_strategy_experiment_bridge_v45


def recommend_workspace_stage_v37(
    current,
    verdict: str,
    can_submit: bool,
    execution_state: str,
    can_open_broker: bool,
) -> tuple[str, str]:
    if current is None:
        return ("待建立焦点", "先从主线前排选一只焦点票，再判断是否进入成交链路。")
    action = str(getattr(current, "action", "") or "").upper()
    if execution_state == "已提交":
        return ("交易跟踪", "已经进入交易执行，当前重点是回执、成交和偏差复核。")
    if execution_state == "已送审":
        return ("送审复核", "已经进入送审链路，当前重点是确认结果并准备切到交易。")
    if execution_state == "提交失败":
        return ("失败回看", "送审失败，先修正风险项和参数，再决定是否重试。")
    if can_submit:
        return ("可推进成交", "当前结论和价位已具备，优先推进送审，不要继续停留在观察态。")
    if action in {"SELL", "REDUCE"}:
        return ("持仓处理", "当前以风险处理为主，不以新开仓推进为优先目标。")
    if action == "HOLD" and can_open_broker:
        return ("持仓跟踪", "当前以持仓处理和交易计划复核为主，确认是否继续拿。")
    return ("候选筛选", f"当前结论为“{verdict}”，先补确认信号，再决定是否推进。")


def recommend_cta_labels_v37(
    *,
    can_submit: bool,
    can_open_broker: bool,
    execution_state: str,
) -> dict[str, str]:
    push_label = "暂不送审"
    broker_label = "暂不进交易"
    if execution_state == "已提交":
        push_label = "查看已提交"
        broker_label = "查看交易回执"
    elif execution_state == "已送审":
        push_label = "查看送审中"
        broker_label = "查看交易链路"
    elif execution_state == "提交失败":
        push_label = "重试前复核"
        broker_label = "查看失败链路" if can_open_broker else "先回看复盘"
    else:
        if can_submit:
            push_label = "进入送审"
        if can_open_broker:
            broker_label = "打开交易执行"
    return {
        "push": push_label,
        "detail": "查看复盘证据",
        "broker": broker_label,
    }


def apply_recommend_workspace_patches(
    window_cls: type,
    *,
    recommend_execution_summary_fn,
) -> None:
    if getattr(window_cls, "_qh_recommend_workspace_patches_applied_v37", False):
        return

    original_refresh_recommend_decision_summary = window_cls._refresh_recommend_decision_summary
    original_refresh_recommendation_focus_panels = window_cls._refresh_recommendation_focus_panels

    def _refresh_recommend_decision_summary_v37(self, row: Any = None) -> None:
        original_refresh_recommend_decision_summary(self, row)
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        label = getattr(self, "recommend_decision_summary_label", None)
        push_button = getattr(self, "recommend_push_focus_button", None)
        detail_button = getattr(self, "recommend_detail_focus_button", None)
        broker_button = getattr(self, "recommend_broker_focus_button", None)
        banner = getattr(self, "recommend_workbench_banner", None)
        if current is None:
            if isinstance(label, QLabel):
                self._set_label_text_if_changed(label, "单票成交卡：先建立焦点，再判断是否具备成交条件。")
            if isinstance(banner, QLabel):
                self._set_label_text_if_changed(banner, "推荐成交台：先挑焦点，再过送审门槛，最后进入交易链路。")
            button_labels = recommend_cta_labels_v37(can_submit=False, can_open_broker=False, execution_state="")
            if isinstance(push_button, QPushButton):
                push_button.setText(button_labels["push"])
            if isinstance(detail_button, QPushButton):
                detail_button.setText(button_labels["detail"])
            if isinstance(broker_button, QPushButton):
                broker_button.setText(button_labels["broker"])
            return

        verdict, execution_summary, can_submit, can_open_broker = recommend_execution_summary_fn(self, current)
        execution_state = str(getattr(current, "execution_status", "") or "待观察")
        stage_title, stage_detail = recommend_workspace_stage_v37(
            current,
            verdict,
            can_submit,
            execution_state,
            can_open_broker,
        )
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()))
        experiment_bridge = paper_strategy_experiment_bridge_v45(
            paper_state,
            resolved_primary_strategy(current, default="掘龙决策") or "掘龙决策",
        )
        strategy_execution_label = str(getattr(current, "strategy_execution_quality_label", "") or "").strip()
        strategy_execution_score = float(getattr(current, "strategy_execution_quality_score", 1.0) or 1.0)
        strategy_execution_summary = str(getattr(current, "strategy_execution_review_summary", "") or "").strip()
        if isinstance(label, QLabel):
            self._set_label_text_if_changed(
                label,
                f"单票成交卡：{getattr(current, 'stock_name', '') or '当前焦点'} | {stage_title} | {verdict} | 实验 {experiment_bridge['badge']}",
            )
        if isinstance(banner, QLabel):
            stock_name = getattr(current, "stock_name", "") or self._stock_name_for_symbol(getattr(current, "symbol", "") or "")
            self._set_label_text_if_changed(
                banner,
                f"推荐成交台：当前聚焦 {stock_name} | 阶段 {stage_title} | {stage_detail} | 实验 {experiment_bridge['badge']}",
            )
        summary_widget = getattr(self, "recommend_decision_summary_text", None)
        if isinstance(summary_widget, QTextEdit):
            base_lines = [
                line
                for line in summary_widget.toPlainText().splitlines()
                if not line.startswith("模拟盘联动：") and not line.startswith("实验提示：") and not line.startswith("实验 CTA：")
            ]
            while base_lines and not base_lines[-1].strip():
                base_lines.pop()
            base_lines.extend(
                [
                    f"模拟盘联动：{experiment_bridge['title']}",
                    f"实验提示：{experiment_bridge['detail']}",
                    f"实验 CTA：{experiment_bridge['cta']}",
                ]
            )
            if strategy_execution_label:
                base_lines.append(f"战法执行：{strategy_execution_label} {strategy_execution_score:.2f}")
                if strategy_execution_summary:
                    base_lines.append(f"降权解释：{strategy_execution_summary}")
            self._set_plain_text_if_changed(summary_widget, "\n".join(base_lines))
        button_labels = recommend_cta_labels_v37(
            can_submit=can_submit,
            can_open_broker=can_open_broker,
            execution_state=execution_state,
        )
        if isinstance(push_button, QPushButton):
            push_button.setText(button_labels["push"])
            if not can_submit and execution_state not in {"已送审", "已提交", "提交失败"}:
                push_button.setEnabled(False)
            base_tooltip = str(push_button.toolTip() or "").strip()
            if f"模拟盘：{experiment_bridge['title']}" not in base_tooltip:
                push_button.setToolTip((base_tooltip + "\n" if base_tooltip else "") + f"模拟盘：{experiment_bridge['title']}")
        if isinstance(detail_button, QPushButton):
            detail_button.setText(button_labels["detail"])
        if isinstance(broker_button, QPushButton):
            broker_button.setText(button_labels["broker"])
            base_tooltip = str(broker_button.toolTip() or "").strip()
            if f"模拟盘：{experiment_bridge['title']}" not in base_tooltip:
                broker_button.setToolTip((base_tooltip + "\n" if base_tooltip else "") + f"模拟盘：{experiment_bridge['title']}")

    def _refresh_recommendation_focus_panels_v37(self, row: Any = None) -> None:
        original_refresh_recommendation_focus_panels(self, row)
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        dispatch_widget = getattr(self, "recommend_dispatch_text", None)
        queue_widget = getattr(self, "recommend_queue_text", None)
        if not isinstance(dispatch_widget, QTextEdit):
            return
        if current is None:
            self._set_plain_text_if_changed(
                dispatch_widget,
                "执行速览\n阶段：待建立焦点\n下一步：先在主线看板里选中一只股票，再判断是否推进成交。",
            )
            if isinstance(queue_widget, QTextEdit):
                self._set_plain_text_if_changed(
                    queue_widget,
                    "送审队列\n当前阶段：候选筛选\n下一步：先形成焦点票，再进入送审排队。",
                )
            return
        verdict, _, can_submit, can_open_broker = recommend_execution_summary_fn(self, current)
        execution_state = str(getattr(current, "execution_status", "") or "待观察")
        stage_title, stage_detail = recommend_workspace_stage_v37(
            current,
            verdict,
            can_submit,
            execution_state,
            can_open_broker,
        )
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()))
        experiment_bridge = paper_strategy_experiment_bridge_v45(
            paper_state,
            resolved_primary_strategy(current, default="掘龙决策") or "掘龙决策",
        )
        strategy_execution_label = str(getattr(current, "strategy_execution_quality_label", "") or "").strip()
        strategy_execution_score = float(getattr(current, "strategy_execution_quality_score", 1.0) or 1.0)
        strategy_execution_summary = str(getattr(current, "strategy_execution_review_summary", "") or "").strip()
        dispatch_lines = [
            "执行速览",
            f"阶段：{stage_title}",
            f"结论：{getattr(current, 'stock_name', '') or '--'} | {verdict}",
            f"模拟盘：{experiment_bridge['title']}",
            f"阶段说明：{stage_detail}",
        ]
        if strategy_execution_label:
            dispatch_lines.append(f"战法执行：{strategy_execution_label} {strategy_execution_score:.2f}")
            if strategy_execution_summary:
                dispatch_lines.append(f"降权解释：{strategy_execution_summary}")
        self._set_plain_text_if_changed(dispatch_widget, "\n".join(dispatch_lines))
        review_widget = getattr(self, "recommend_focus_review_text", None)
        if isinstance(review_widget, QTextEdit):
            review_lines = [
                line
                for line in review_widget.toPlainText().splitlines()
                if not line.startswith("实验提示：") and not line.startswith("实验 CTA：")
            ]
            while review_lines and not review_lines[-1].strip():
                review_lines.pop()
            review_lines.extend(
                [
                    f"实验提示：{experiment_bridge['detail']}",
                    f"实验 CTA：{experiment_bridge['cta']}",
                ]
            )
            if strategy_execution_label:
                review_lines.append(f"战法执行：{strategy_execution_label} {strategy_execution_score:.2f}")
                if strategy_execution_summary:
                    review_lines.append(f"降权解释：{strategy_execution_summary}")
            self._set_plain_text_if_changed(review_widget, "\n".join(review_lines))
        if isinstance(queue_widget, QTextEdit):
            queue_text = queue_widget.toPlainText().splitlines()
            queue_lines = [line for line in queue_text if not line.startswith("当前阶段：")]
            if len(queue_lines) >= 2:
                queue_lines.insert(1, f"当前阶段：{stage_title}")
            else:
                queue_lines.extend([f"当前阶段：{stage_title}", f"下一步：{stage_detail}"])
            self._set_plain_text_if_changed(queue_widget, "\n".join(queue_lines))

    window_cls._refresh_recommend_decision_summary = _refresh_recommend_decision_summary_v37
    window_cls._refresh_recommendation_focus_panels = _refresh_recommendation_focus_panels_v37
    window_cls._qh_recommend_workspace_patches_applied_v37 = True
