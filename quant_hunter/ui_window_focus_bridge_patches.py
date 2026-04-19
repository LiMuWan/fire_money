from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTableWidget, QTextEdit, QVBoxLayout

from quant_hunter.strategy_registry import resolved_primary_strategy


def apply_focus_bridge_patches(
    window_cls: type,
    *,
    mainline_signal_brief_fn,
    signal_action_text_fn,
    recommend_execution_summary_fn,
    recommend_cta_labels_fn,
    paper_strategy_experiment_bridge_fn,
    recommend_queue_snapshot_fn,
    queue_sequence_summary_fn,
    next_review_target_fn,
) -> None:
    if getattr(window_cls, "_qh_focus_bridge_patches_applied_v20", False):
        return

    original_install_paper_trading_workspace_v19 = window_cls._install_paper_trading_workspace
    original_refresh_paper_trading_panels_v19 = window_cls._refresh_paper_trading_panels
    original_export_paper_trading_report_v19 = window_cls.export_paper_trading_report
    original_refresh_recommendation_focus_panels_v20 = window_cls._refresh_recommendation_focus_panels

    def _selected_paper_position_symbol_v19(self) -> str:
        table = getattr(self, "paper_positions_table", None)
        if not isinstance(table, QTableWidget) or table.rowCount() <= 0:
            return ""
        row_index = table.currentRow()
        if row_index < 0 and table.rowCount() == 1:
            row_index = 0
        if row_index < 0:
            return ""
        item = table.item(row_index, 1)
        return (item.text() if item else "").strip()

    def _selected_paper_ledger_symbol_v19(self) -> str:
        table = getattr(self, "paper_ledger_table", None)
        if not isinstance(table, QTableWidget) or table.rowCount() <= 0:
            return ""
        row_index = table.currentRow()
        if row_index < 0 and table.rowCount() == 1:
            row_index = 0
        if row_index < 0:
            return ""
        item = table.item(row_index, 2)
        return (item.text() if item else "").strip()

    def _selected_paper_symbol_v19(self) -> str:
        return (
            self._selected_paper_position_symbol()
            or self._selected_paper_ledger_symbol()
            or getattr(self, "active_symbol", "")
        )

    def _sync_paper_symbol_from_tables_v19(self) -> None:
        symbol = self._selected_paper_symbol()
        if not symbol:
            self._update_paper_trading_focus_hint()
            return
        self.active_symbol = symbol
        if hasattr(self, "_focus_symbol_everywhere"):
            self._focus_symbol_everywhere(symbol, origin="paper")
        else:
            self.active_symbol = symbol
        self._update_paper_trading_focus_hint()

    def _open_paper_symbol_in_recommend_v19(self) -> None:
        symbol = self._selected_paper_symbol()
        if symbol:
            self.active_symbol = symbol
            self._focus_symbol_in_recommend_workspace(symbol)
            if hasattr(self, "_focus_symbol_everywhere"):
                self._focus_symbol_everywhere(symbol, origin="paper")
        else:
            self._navigate_to_workspace("recommend", "daily_pool_table", "daily_pool_table")
        self._update_paper_trading_focus_hint()

    def _open_paper_symbol_in_detail_v19(self) -> None:
        symbol = self._selected_paper_symbol()
        if symbol:
            self.active_symbol = symbol
            if hasattr(self, "_focus_symbol_everywhere"):
                self._focus_symbol_everywhere(symbol, origin="paper")
            self._navigate_to_workspace("detail", "metrics_text")
        else:
            self._navigate_to_workspace("detail", "metrics_text")
        self._update_paper_trading_focus_hint()

    def _open_paper_symbol_in_broker_v19(self) -> None:
        symbol = self._selected_paper_symbol()
        if symbol:
            self.active_symbol = symbol
            self._focus_symbol_in_broker_workspace(symbol)
            if hasattr(self, "_focus_symbol_everywhere"):
                self._focus_symbol_everywhere(symbol, origin="paper")
        else:
            self._navigate_to_workspace("broker", "orders_table")
        self._update_paper_trading_focus_hint()

    def _open_paper_report_dir_v19(self) -> None:
        target_dir = Path(getattr(self, "paper_last_export_dir", "") or self._paper_trading_output_dir())
        target_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target_dir)))

    def _update_paper_trading_focus_hint_v19(self) -> None:
        label = getattr(self, "paper_trading_focus_label", None)
        if not isinstance(label, QLabel):
            return
        symbol = self._selected_paper_symbol()
        if not symbol:
            label.setText("模拟盘联动：点击持仓或交割单后，可直接跳到推荐页、复盘页或交易页继续处理。")
        else:
            stock_name = self._stock_name_for_symbol(symbol)
            stock_id = self._stock_id_for_symbol(symbol)
            label.setText(
                f"模拟盘联动：当前焦点 {stock_name} ({stock_id} / {symbol})，可继续查看推荐、复盘或交易执行。"
            )
        has_symbol = bool(symbol)
        for attr_name in ["paper_to_recommend_button", "paper_to_detail_button", "paper_to_broker_button"]:
            button = getattr(self, attr_name, None)
            if isinstance(button, QPushButton):
                button.setEnabled(has_symbol)

    def _install_paper_trading_workspace_v19(self) -> None:
        original_install_paper_trading_workspace_v19(self)
        if not hasattr(self, "paper_trading_box") or hasattr(self, "paper_trading_focus_label"):
            return
        paper_layout = self.paper_trading_box.layout()
        if not isinstance(paper_layout, QVBoxLayout):
            return

        helper_label = QLabel("模拟盘路径：1 初始化账户 -> 2 跑一轮 -> 3 看调仓建议 -> 4 导出报告。")
        helper_label.setObjectName("inlineHint")
        helper_label.setWordWrap(True)
        self.paper_trading_step_label = helper_label
        paper_layout.insertWidget(1, helper_label)

        focus_label = QLabel("模拟盘联动：点击持仓或交割单后，可直接跳到推荐页、复盘页或交易页继续处理。")
        focus_label.setObjectName("focusStateLabel")
        focus_label.setWordWrap(True)
        self.paper_trading_focus_label = focus_label
        paper_layout.insertWidget(2, focus_label)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.paper_to_recommend_button = QPushButton("查看推荐页")
        self.paper_to_detail_button = QPushButton("查看复盘页")
        self.paper_to_broker_button = QPushButton("看交易计划")
        self.paper_report_dir_button = QPushButton("打开报告目录")
        self._set_button_role(self.paper_to_recommend_button, "tonal")
        self._set_button_role(self.paper_to_detail_button, "ghost")
        self._set_button_role(self.paper_to_broker_button, "accent")
        self._set_button_role(self.paper_report_dir_button, "ghost")
        self.paper_to_recommend_button.clicked.connect(self.open_paper_symbol_in_recommend)
        self.paper_to_detail_button.clicked.connect(self.open_paper_symbol_in_detail)
        self.paper_to_broker_button.clicked.connect(self.open_paper_symbol_in_broker)
        self.paper_report_dir_button.clicked.connect(self.open_paper_report_dir)
        for button in [
            self.paper_to_recommend_button,
            self.paper_to_detail_button,
            self.paper_to_broker_button,
            self.paper_report_dir_button,
        ]:
            action_row.addWidget(button)
        action_row.addStretch(1)
        paper_layout.insertLayout(3, action_row)

        self.paper_positions_table.itemSelectionChanged.connect(self._sync_paper_symbol_from_tables)
        self.paper_ledger_table.itemSelectionChanged.connect(self._sync_paper_symbol_from_tables)
        self._update_paper_trading_focus_hint()

    def _refresh_paper_trading_panels_v19(self) -> None:
        original_refresh_paper_trading_panels_v19(self)
        self._update_paper_trading_focus_hint()

    def _export_paper_trading_report_v19(self) -> None:
        original_export_paper_trading_report_v19(self)
        self.paper_last_export_dir = str(self._paper_trading_output_dir())
        self._update_paper_trading_focus_hint()

    def _current_recommend_focus_v20(self):
        if hasattr(self, "_explicit_recommendation_focus"):
            current = self._explicit_recommendation_focus()
            if current is not None:
                return current
        if hasattr(self, "_selected_daily_pool_recommendation"):
            return self._selected_daily_pool_recommendation()
        return None

    def _open_selected_recommend_in_detail_v20(self) -> None:
        current = self._current_recommend_focus()
        if current is None:
            self._navigate_to_workspace("detail", "metrics_text")
            return
        self.active_symbol = current.symbol
        if hasattr(self, "_focus_symbol_everywhere"):
            self._focus_symbol_everywhere(current.symbol, origin="recommend")
        self._navigate_to_workspace("detail", "metrics_text")

    def _open_selected_recommend_in_broker_v20(self) -> None:
        current = self._current_recommend_focus()
        if current is None:
            self._navigate_to_workspace("broker", "orders_table")
            return
        self.active_symbol = current.symbol
        self._focus_symbol_in_broker_workspace(current.symbol)
        if hasattr(self, "_focus_symbol_everywhere"):
            self._focus_symbol_everywhere(current.symbol, origin="recommend")

    def _refresh_recommend_decision_summary_v20(self, row=None) -> None:
        label = getattr(self, "recommend_decision_summary_label", None)
        text_widget = getattr(self, "recommend_decision_summary_text", None)
        if not isinstance(label, QLabel) or not isinstance(text_widget, QTextEdit):
            return

        current = row or self._current_recommend_focus()
        if current is None:
            button_labels = recommend_cta_labels_fn(can_submit=False, can_open_broker=False, execution_state="")
            self._set_label_text_if_changed(label, "先选中一只股票，再看结论、关键价位、失效条件和下一步。")
            self._set_plain_text_if_changed(
                text_widget,
                "单票决策摘要\n\n"
                "这里会先给出当前结论、关键买卖点、失效条件和下一步动作。\n"
                "你不需要先翻完所有卡片，再决定要不要送审。",
            )
            push_button = getattr(self, "recommend_push_focus_button", None)
            if isinstance(push_button, QPushButton):
                push_button.setText(button_labels["push"])
                push_button.setEnabled(False)
                push_button.setToolTip("暂不送审：先从机会池选中焦点股票，再判断是否进入送审链路。")
            detail_button = getattr(self, "recommend_detail_focus_button", None)
            if isinstance(detail_button, QPushButton):
                detail_button.setText(button_labels["detail"])
                detail_button.setEnabled(False)
                detail_button.setToolTip("查看复盘证据：先选中焦点股票，再查看信号、执行回放和近期消息。")
            broker_button = getattr(self, "recommend_broker_focus_button", None)
            if isinstance(broker_button, QPushButton):
                broker_button.setText(button_labels["broker"])
                broker_button.setEnabled(False)
                broker_button.setToolTip("暂不进交易：先建立焦点票，再去交易页查看计划、委托和回执链路。")
            return

        self.active_symbol = getattr(current, "symbol", "") or getattr(self, "active_symbol", "")
        symbol = getattr(current, "symbol", "") or ""
        stock_name = getattr(current, "stock_name", "") or self._stock_name_for_symbol(symbol)
        stock_id = getattr(current, "stock_id", "") or self._stock_id_for_symbol(symbol)
        theme_name = getattr(current, "mainline_tag", "") or getattr(current, "theme_name", "") or "待确认"
        strategy_name = resolved_primary_strategy(current, default="掘龙决策") or "掘龙决策"
        signal = mainline_signal_brief_fn(current)
        action_text = signal_action_text_fn(current)
        verdict, execution_summary, can_submit, can_open_broker = recommend_execution_summary_fn(self, current)
        next_focus = getattr(current, "next_focus", "") or "继续盯量能、承接和主线延续。"
        invalidation = getattr(current, "invalidation_reason", "") or getattr(current, "risk_line", "") or "跌破计划防守线，或主线窗口继续收缩时先退出。"
        risk_flag = getattr(current, "mainline_risk_flag", "") or "待评估"
        planned_entry = float(getattr(current, "entry_price", 0.0) or getattr(current, "close", 0.0) or 0.0)
        planned_stop = float(getattr(current, "stop_price", 0.0) or (planned_entry * 0.95 if planned_entry > 0 else 0.0))
        planned_target = float(getattr(current, "target_price", 0.0) or (planned_entry * 1.08 if planned_entry > 0 else 0.0))
        price_snapshot = self._recommend_price_snapshot(current) if hasattr(self, "_recommend_price_snapshot") else {}
        price_brief = self._recommend_price_brief(current) if hasattr(self, "_recommend_price_brief") else ""
        hype_logic = (
            self._hype_logic_for_symbol(symbol, recommendation=current)
            if hasattr(self, "_hype_logic_for_symbol")
            else (getattr(current, "rationale", "") or "等待逻辑生成")
        )
        news_lines = self._news_digest_lines_for_symbol(symbol, limit=2) if hasattr(self, "_news_digest_lines_for_symbol") else []
        decision = next(
            (
                item
                for item in list(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or [])
                if getattr(item, "symbol", "") == symbol
            ),
            None,
        )
        advice = next(
            (
                item
                for item in list(getattr(self, "current_position_advice", []) or [])
                if getattr(item, "symbol", "") == symbol
            ),
            None,
        )
        queue_snapshot = recommend_queue_snapshot_fn(self)
        execution_state = getattr(current, "execution_status", "") or "待观察"
        queue_summary = queue_sequence_summary_fn(queue_snapshot)
        next_review_target = next_review_target_fn(queue_snapshot)
        paper_state = getattr(self, "paper_trading_state", getattr(getattr(self, "state", None), "paper_trading_state", None))
        experiment_bridge = paper_strategy_experiment_bridge_fn(paper_state, strategy_name)
        button_labels = recommend_cta_labels_fn(
            can_submit=can_submit,
            can_open_broker=can_open_broker,
            execution_state=execution_state,
        )

        self._set_label_text_if_changed(
            label,
            f"当前结论：{stock_name} | {verdict} | {strategy_name} | 实验 {experiment_bridge['badge']}",
        )
        price_plan_line = f"价格计划：{price_brief or '等待行情同步'}"
        price_detail_line = f"关键价位：买点 {planned_entry:.2f} | 止损 {planned_stop:.2f} | 目标 {planned_target:.2f}"
        lines = [
            f"单票：{stock_name} ({stock_id} / {symbol})",
            "",
            f"决策快照：{verdict} | {signal} | 风险 {risk_flag}",
            f"执行提示：{execution_summary}（原动作为 {action_text} | 链路 {execution_state}）",
            price_detail_line,
            price_plan_line,
            f"逻辑 / 题材：{theme_name} | {hype_logic}",
            f"模拟盘联动：{experiment_bridge['title']}",
            f"实验提示：{experiment_bridge['detail']}",
            f"失效条件：{invalidation}",
            f"队列状态：{queue_summary}",
            f"下一复核：{next_review_target}",
            f"下一步：{next_focus}",
            f"实验 CTA：{experiment_bridge['cta']}",
        ]
        upside_pct = price_snapshot.get("upside_pct") if isinstance(price_snapshot, dict) else None
        downside_pct = price_snapshot.get("downside_pct") if isinstance(price_snapshot, dict) else None
        rr_ratio = price_snapshot.get("rr_ratio") if isinstance(price_snapshot, dict) else None
        if upside_pct is not None and downside_pct is not None:
            lines.append(
                f"空间评估：上行 {float(upside_pct):.1f}% | 防守 {float(downside_pct):.1f}% | 收益/风险比 {float(rr_ratio):.2f}"
                if rr_ratio is not None
                else f"空间评估：上行 {float(upside_pct):.1f}% | 防守 {float(downside_pct):.1f}%"
            )
        if decision is not None:
            lines.append(
                f"交易计划：准备 {float(getattr(decision, 'execution_readiness', 0.0) or 0.0):.1f} | 预算 {float(getattr(decision, 'suggested_budget', 0.0) or 0.0):,.0f}"
            )
        if advice is not None:
            lines.append(
                f"持仓处理：{self._display_action(getattr(advice, 'action', 'WATCH'))} | {getattr(advice, 'rationale', '') or '继续跟踪。'}"
            )
        if news_lines:
            lines.extend(["近期消息：", *news_lines])
        self._set_plain_text_if_changed(text_widget, "\n".join(lines))

        push_button = getattr(self, "recommend_push_focus_button", None)
        if isinstance(push_button, QPushButton):
            push_button.setText(button_labels["push"])
            push_button.setEnabled(can_submit)
            push_tooltip = (
                f"{button_labels['push']}：{stock_name}\n"
                f"结论：{verdict}\n"
                f"执行提示：{execution_summary}\n"
                f"模拟盘：{experiment_bridge['title']}\n"
                f"下一复核：{next_review_target}"
                if can_submit
                else f"{button_labels['push']}：{stock_name}\n结论：{verdict}\n原因：{execution_summary}\n模拟盘：{experiment_bridge['title']}\n建议：{next_focus}"
            )
            push_button.setToolTip(push_tooltip)
        detail_button = getattr(self, "recommend_detail_focus_button", None)
        if isinstance(detail_button, QPushButton):
            detail_button.setText(button_labels["detail"])
            detail_button.setEnabled(True)
            detail_button.setToolTip(
                f"{button_labels['detail']}：{stock_name}\n"
                f"重点：信号、执行回放、失效条件与近期消息。\n"
                f"当前结论：{verdict}"
            )
        broker_button = getattr(self, "recommend_broker_focus_button", None)
        if isinstance(broker_button, QPushButton):
            broker_button.setText(button_labels["broker"])
            broker_button.setEnabled(can_open_broker)
            broker_tooltip = (
                f"{button_labels['broker']}：{stock_name}\n价格计划：{price_brief}\n模拟盘：{experiment_bridge['title']}\n预算与执行链路会在交易页展开。"
                if can_open_broker
                else f"{button_labels['broker']}：{stock_name}\n原因：{execution_summary}\n模拟盘：{experiment_bridge['title']}\n建议：先回看复盘和确认信号。"
            )
            broker_button.setToolTip(broker_tooltip)

    def _refresh_recommendation_focus_panels_v20(self, row=None) -> None:
        original_refresh_recommendation_focus_panels_v20(self, row)
        self._refresh_recommend_decision_summary(row)

    window_cls._selected_paper_position_symbol = _selected_paper_position_symbol_v19
    window_cls._selected_paper_ledger_symbol = _selected_paper_ledger_symbol_v19
    window_cls._selected_paper_symbol = _selected_paper_symbol_v19
    window_cls._sync_paper_symbol_from_tables = _sync_paper_symbol_from_tables_v19
    window_cls.open_paper_symbol_in_recommend = _open_paper_symbol_in_recommend_v19
    window_cls.open_paper_symbol_in_detail = _open_paper_symbol_in_detail_v19
    window_cls.open_paper_symbol_in_broker = _open_paper_symbol_in_broker_v19
    window_cls.open_paper_report_dir = _open_paper_report_dir_v19
    window_cls._update_paper_trading_focus_hint = _update_paper_trading_focus_hint_v19
    window_cls._install_paper_trading_workspace = _install_paper_trading_workspace_v19
    window_cls._refresh_paper_trading_panels = _refresh_paper_trading_panels_v19
    window_cls.export_paper_trading_report = _export_paper_trading_report_v19
    window_cls._current_recommend_focus = _current_recommend_focus_v20
    window_cls.open_selected_recommend_in_detail = _open_selected_recommend_in_detail_v20
    window_cls.open_selected_recommend_in_broker = _open_selected_recommend_in_broker_v20
    window_cls._refresh_recommend_decision_summary = _refresh_recommend_decision_summary_v20
    window_cls._refresh_recommendation_focus_panels = _refresh_recommendation_focus_panels_v20
    window_cls._qh_focus_bridge_patches_applied_v20 = True
