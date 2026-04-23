from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QLabel, QPushButton, QSplitter, QTableWidget, QTextEdit, QVBoxLayout, QWidget
except ModuleNotFoundError:  # pragma: no cover - enables pure-logic imports without Qt runtime
    class _QtStub:
        ScrollBarAlwaysOff = 0

        def __init__(self, *args, **kwargs) -> None:
            self._text = str(args[0]) if args else ""

        def __getattr__(self, _name):
            return lambda *args, **kwargs: None

        def text(self) -> str:
            return self._text

        def setText(self, value: str) -> None:
            self._text = str(value)

        def toPlainText(self) -> str:
            return self._text

        def setPlainText(self, value: str) -> None:
            self._text = str(value)

    class Qt:  # type: ignore[override]
        ScrollBarAlwaysOff = 0

    class QWidget(_QtStub):  # type: ignore[override]
        pass

    class QLabel(QWidget):  # type: ignore[override]
        pass

    class QPushButton(QWidget):  # type: ignore[override]
        pass

    class QSplitter(QWidget):  # type: ignore[override]
        pass

    class QTableWidget(QWidget):  # type: ignore[override]
        pass

    class QTextEdit(QWidget):  # type: ignore[override]
        pass

    class QVBoxLayout(_QtStub):  # type: ignore[override]
        pass

from quant_hunter.models import PaperTradingState, RecommendationRow
from quant_hunter.strategy_registry import resolved_primary_strategy
from quant_hunter.ui_config import (
    action_row_tooltip_copy,
    contextual_entry_rename_targets,
    workbench_banner_copy,
    workbench_empty_panel_copy,
)
from quant_hunter.ui_workspace_runtime import (
    button_route_action_key,
    contextual_button_prefix,
    contextual_entry_action_key,
    contextual_entry_display_text,
    contextual_entry_tooltip,
    contextual_route_button_state,
)
from quant_hunter.ui_window_paper_experiment_patches import paper_strategy_experiment_bridge_v45


def broker_pre_submit_experiment_lines_v48(
    state: PaperTradingState,
    strategy_name: str,
) -> list[str]:
    bridge = paper_strategy_experiment_bridge_v45(state, strategy_name)
    return [
        f"模拟盘实验：{bridge['title']}",
        f"实验纪律：{bridge['detail']}",
        f"提交前提示：{bridge['cta']}",
    ]


def merge_broker_experiment_lines_v47(
    current_text: str,
    experiment_lines: list[str],
) -> str:
    prefixes = ("模拟盘实验：", "实验纪律：", "提交前提示：")
    lines = [
        line
        for line in str(current_text or "").splitlines()
        if not any(line.startswith(prefix) for prefix in prefixes)
    ]
    while lines and not lines[-1].strip():
        lines.pop()
    if lines:
        lines.append("")
    lines.extend(experiment_lines)
    return "\n".join(lines)


def apply_workspace_workbench_patches(window_cls: type) -> None:
    if getattr(window_cls, "_qh_workspace_workbench_patches_applied_v33", False):
        return

    original_post_build_ui_tweaks_v27 = window_cls._post_build_ui_tweaks
    original_refresh_broker_aux_panels_v27 = window_cls._refresh_broker_auxiliary_panels

    def _install_broker_workbench_banner_v27(self) -> None:
        tab = getattr(self, "broker_tab", None)
        if not isinstance(tab, QWidget) or hasattr(self, "broker_workbench_banner"):
            return
        scroll_area = getattr(self, "broker_scroll_area", None)
        if scroll_area is None:
            return
        content = scroll_area.widget()
        content_layout = content.layout() if content is not None else None
        if not isinstance(content_layout, QVBoxLayout):
            return
        banner = QLabel(workbench_banner_copy("broker", "seed"))
        banner.setObjectName("workspaceFocusBanner")
        banner.setWordWrap(True)
        content_layout.insertWidget(1, banner)
        self.broker_workbench_banner = banner

    def _polish_broker_workspace_v27(self) -> None:
        self._install_broker_workbench_banner_v27()

        splitter_specs = (
            ("broker_control_splitter", [640, 780, 340]),
            ("broker_middle_splitter", [420, 1160]),
            ("broker_order_focus_splitter", [1000, 420]),
        )
        for attr_name, sizes in splitter_specs:
            splitter = getattr(self, attr_name, None)
            if isinstance(splitter, QSplitter) and splitter.count() == len(sizes):
                self._configure_splitter(splitter, sizes)
                splitter.setSizes(sizes)
                for index in range(splitter.count()):
                    splitter.setStretchFactor(index, max(sizes[index] // 100, 1))

        for attr_name, min_height in (
            ("holdings_table", 320),
            ("orders_table", 340),
            ("execution_table", 300),
            ("broker_order_focus_text", 340),
            ("order_result_text", 200),
            ("broker_recap_text", 220),
            ("broker_mainline_review_text", 170),
            ("broker_execution_text", 210),
            ("runtime_log_text", 160),
        ):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QWidget):
                widget.setMinimumHeight(max(widget.minimumHeight(), min_height))

        for attr_name, max_height in (
            ("broker_mainline_review_text", 220),
            ("broker_execution_text", 260),
            ("broker_recap_text", 260),
        ):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMaximumHeight(max(widget.maximumHeight(), max_height))

        if hasattr(self, "broker_workbench_banner"):
            self.broker_workbench_banner.hide()

    def _refresh_broker_auxiliary_panels_v27(self) -> None:
        original_refresh_broker_aux_panels_v27(self)
        intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
        record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
        order_count = len(getattr(self, "order_intents", []) or [])
        submit_count = len(getattr(self, "order_submission_records", []) or [])
        recommendation = None
        if intent is not None:
            symbol = getattr(intent, "symbol", "") or ""
            recommendation = next(
                (item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol),
                None,
            )
        paper_state = getattr(
            self,
            "paper_trading_state",
            getattr(getattr(self, "state", None), "paper_trading_state", PaperTradingState()),
        )
        experiment_lines = (
            broker_pre_submit_experiment_lines_v48(
                paper_state,
                resolved_primary_strategy(recommendation, default="掘龙决策") or "掘龙决策",
            )
            if recommendation is not None
            else []
        )

        if hasattr(self, "broker_workbench_banner"):
            if record is not None:
                symbol = str(record.get("symbol", "") or "")
                stock_name = self._stock_name_for_symbol(symbol) if symbol else "最新回执"
                text = workbench_banner_copy("broker", "record", stock_name=stock_name)
            elif intent is not None:
                symbol = getattr(intent, "symbol", "") or ""
                stock_name = self._stock_name_for_symbol(symbol) if symbol else "焦点委托"
                experiment_badge = experiment_lines[0].replace("模拟盘实验：", "") if experiment_lines else "实验待同步"
                text = workbench_banner_copy(
                    "broker",
                    "focus",
                    stock_name=stock_name,
                    suffix=f" | {experiment_badge}" if experiment_badge else "",
                )
            elif order_count:
                text = workbench_banner_copy("broker", "queue", order_count=order_count)
            elif submit_count:
                text = workbench_banner_copy("broker", "submitted", submit_count=submit_count)
            else:
                text = workbench_banner_copy("broker", "empty")
            self._set_label_text_if_changed(self.broker_workbench_banner, text)

        if hasattr(self, "order_result_text") and record is None and not getattr(self, "order_submission_log", []):
            self._set_plain_text_if_changed(
                self.order_result_text,
                merge_broker_experiment_lines_v47(
                    "\n".join(
                        [
                            "执行回放",
                            "",
                            f"当前状态：待提交委托 {order_count} 笔 | 已有回执 {submit_count} 条",
                            "建议动作：",
                            "1. 先在左侧选中一笔委托，检查主线闸门和风险灯。",
                            "2. 再打开确认弹窗核对账户、价格、止损和仓位。",
                            "3. 提交后这里会自动滚动到最新回执。",
                        ]
                    ),
                    experiment_lines,
                ),
            )

        if hasattr(self, "broker_recap_text") and record is None and submit_count == 0:
            focus_name = self._stock_name_for_symbol(getattr(intent, "symbol", "") or "") if intent is not None else "暂无焦点"
            self._set_plain_text_if_changed(
                self.broker_recap_text,
                merge_broker_experiment_lines_v47(
                    "\n".join(
                        [
                            "成交回顾",
                            "",
                            f"当前焦点：{focus_name}",
                            "回顾重点：",
                            "- 看提交后是否存在失败、撤单、拒单或价格偏离。",
                            "- 看成交是否符合原计划的主线逻辑和仓位纪律。",
                            "- 看若执行失真，应该回机会池还是只修委托参数。",
                        ]
                    ),
                    experiment_lines,
                ),
            )

    def _post_build_ui_tweaks_v27(self) -> None:
        original_post_build_ui_tweaks_v27(self)
        self._polish_broker_workspace_v27()
        self._update_broker_action_flow_v26()
        self._refresh_broker_auxiliary_panels()

    window_cls._install_broker_workbench_banner_v27 = _install_broker_workbench_banner_v27
    window_cls._polish_broker_workspace_v27 = _polish_broker_workspace_v27
    window_cls._refresh_broker_auxiliary_panels = _refresh_broker_auxiliary_panels_v27
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v27

    original_post_build_ui_tweaks_v28 = window_cls._post_build_ui_tweaks
    original_refresh_recommendation_focus_panels_v28 = window_cls._refresh_recommendation_focus_panels
    original_refresh_detail_workspace_panels_v28 = window_cls._refresh_detail_workspace_panels

    def _install_recommend_detail_workbench_banners_v28(self) -> None:
        banner_specs = [
            ("recommend_tab", "recommend_scroll_area", "recommend_workbench_banner", workbench_banner_copy("recommend", "seed")),
            ("detail_tab", "detail_workspace_scroll_area", "detail_workbench_banner", workbench_banner_copy("detail", "seed")),
        ]
        for tab_name, scroll_name, attr_name, text in banner_specs:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget) or hasattr(self, attr_name):
                continue
            scroll_area = getattr(self, scroll_name, None)
            if scroll_area is None:
                continue
            content = scroll_area.widget()
            content_layout = content.layout() if content is not None else None
            if not isinstance(content_layout, QVBoxLayout):
                continue
            banner = QLabel(text)
            banner.setObjectName("workspaceFocusBanner")
            banner.setWordWrap(True)
            content_layout.insertWidget(1, banner)
            setattr(self, attr_name, banner)

    def _polish_recommend_detail_workspace_v28(self) -> None:
        self._install_recommend_detail_workbench_banners_v28()

        splitter_specs = (
            ("recommend_dispatch_splitter", [460, 820, 360]),
            ("recommend_summary_splitter", [420, 920]),
            ("recommend_recap_middle_splitter", [420, 980]),
            ("recommend_recap_bottom_splitter", [420, 980]),
            ("recommend_review_splitter", [720, 720]),
        )
        for attr_name, sizes in splitter_specs:
            splitter = getattr(self, attr_name, None)
            if isinstance(splitter, QSplitter) and splitter.count() == len(sizes):
                self._configure_splitter(splitter, sizes)
                splitter.setSizes(sizes)
                for index in range(splitter.count()):
                    splitter.setStretchFactor(index, max(sizes[index] // 100, 1))

        for attr_name, min_height in (
            ("recommend_dispatch_text", 170),
            ("recommend_focus_review_text", 186),
            ("recommend_queue_text", 170),
            ("recommend_decision_summary_text", 210),
            ("recommend_core_bucket_text", 190),
            ("recommend_watch_bucket_text", 190),
            ("recommend_risk_bucket_text", 190),
            ("metrics_text", 230),
            ("detail_decision_text", 250),
            ("detail_execution_text", 250),
            ("detail_conclusion_text", 250),
        ):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QWidget):
                widget.setMinimumHeight(max(widget.minimumHeight(), min_height))

        for attr_name, max_height in (
            ("recommend_dispatch_text", 220),
            ("recommend_focus_review_text", 236),
            ("recommend_queue_text", 220),
            ("detail_decision_text", 300),
            ("detail_execution_text", 300),
            ("detail_conclusion_text", 300),
        ):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMaximumHeight(max(widget.maximumHeight(), max_height))

    def _refresh_recommendation_focus_panels_v28(self, row: RecommendationRow | None = None) -> None:
        original_refresh_recommendation_focus_panels_v28(self, row)
        current = row or (self._current_recommend_focus() if hasattr(self, "_current_recommend_focus") else None)
        if hasattr(self, "recommend_workbench_banner"):
            if current is None:
                text = workbench_banner_copy("recommend", "empty")
            else:
                stock_name = getattr(current, "stock_name", "") or self._stock_name_for_symbol(getattr(current, "symbol", "") or "")
                action_text = self._display_action(getattr(current, "action", "WATCH"))
                text = workbench_banner_copy("recommend", "focus", stock_name=stock_name)
                if str(getattr(current, "action", "") or "").upper() == "BUY":
                    text = workbench_banner_copy("recommend", "buy_focus", stock_name=stock_name)
                elif action_text:
                    text = workbench_banner_copy("recommend", "action_focus", stock_name=stock_name, action_text=action_text)
            self._set_label_text_if_changed(self.recommend_workbench_banner, text)

        if current is None and hasattr(self, "recommend_decision_summary_text"):
            self._set_plain_text_if_changed(
                self.recommend_decision_summary_text,
                workbench_empty_panel_copy("recommend_decision_summary_text"),
            )

    def _refresh_detail_workspace_panels_v28(self) -> None:
        original_refresh_detail_workspace_panels_v28(self)
        symbol = getattr(self, "active_symbol", "") or ""
        stock_name = self._stock_name_for_symbol(symbol) if symbol else ""
        if hasattr(self, "detail_workbench_banner"):
            if symbol:
                self._set_label_text_if_changed(
                    self.detail_workbench_banner,
                    workbench_banner_copy("detail", "focus", stock_name=stock_name),
                )
            else:
                self._set_label_text_if_changed(
                    self.detail_workbench_banner,
                    workbench_banner_copy("detail", "empty"),
                )

        if not symbol:
            if hasattr(self, "metrics_text"):
                self._set_plain_text_if_changed(
                    self.metrics_text,
                    workbench_empty_panel_copy("metrics_text"),
                )
            if hasattr(self, "detail_decision_text"):
                self._set_plain_text_if_changed(
                    self.detail_decision_text,
                    workbench_empty_panel_copy("detail_decision_text"),
                )
            if hasattr(self, "detail_execution_text"):
                self._set_plain_text_if_changed(
                    self.detail_execution_text,
                    workbench_empty_panel_copy("detail_execution_text"),
                )
            if hasattr(self, "detail_conclusion_text"):
                self._set_plain_text_if_changed(
                    self.detail_conclusion_text,
                    workbench_empty_panel_copy("detail_conclusion_text"),
                )

    def _post_build_ui_tweaks_v28(self) -> None:
        original_post_build_ui_tweaks_v28(self)
        self._polish_recommend_detail_workspace_v28()
        self._refresh_recommendation_focus_panels()
        self._refresh_detail_workspace_panels()

    window_cls._install_recommend_detail_workbench_banners_v28 = _install_recommend_detail_workbench_banners_v28
    window_cls._polish_recommend_detail_workspace_v28 = _polish_recommend_detail_workspace_v28
    window_cls._refresh_recommendation_focus_panels = _refresh_recommendation_focus_panels_v28
    window_cls._refresh_detail_workspace_panels = _refresh_detail_workspace_panels_v28
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v28

    original_post_build_ui_tweaks_v29 = window_cls._post_build_ui_tweaks
    original_refresh_monitor_summary_v29 = window_cls._refresh_monitor_summary
    original_refresh_board_focus_panels_v29 = window_cls._refresh_board_focus_panels

    def _install_scanner_board_workbench_banners_v29(self) -> None:
        banner_specs = [
            ("scanner_tab", "scanner_workspace_scroll_area", "scanner_workbench_banner", workbench_banner_copy("scanner", "seed")),
            ("board_tab", "board_workspace_scroll_area", "board_workbench_banner", workbench_banner_copy("board", "seed")),
        ]
        for tab_name, scroll_name, attr_name, text in banner_specs:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget) or hasattr(self, attr_name):
                continue
            scroll_area = getattr(self, scroll_name, None)
            if scroll_area is None:
                continue
            content = scroll_area.widget()
            content_layout = content.layout() if content is not None else None
            if not isinstance(content_layout, QVBoxLayout):
                continue
            banner = QLabel(text)
            banner.setObjectName("workspaceFocusBanner")
            banner.setWordWrap(True)
            content_layout.insertWidget(1, banner)
            setattr(self, attr_name, banner)

    def _polish_scanner_board_workspace_v29(self) -> None:
        self._install_scanner_board_workbench_banners_v29()

        if hasattr(self, "watchlist_widget"):
            self.watchlist_widget.setMinimumHeight(max(self.watchlist_widget.minimumHeight(), 280))
        for attr_name, min_height in (
            ("scan_table", 320),
            ("monitor_table", 280),
            ("monitor_summary_text", 170),
            ("board_table", 320),
            ("board_monitor_table", 260),
            ("board_monitor_text", 180),
        ):
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QWidget):
                widget.setMinimumHeight(max(widget.minimumHeight(), min_height))

        scanner_tab = getattr(self, "scanner_tab", None)
        if isinstance(scanner_tab, QWidget):
            for splitter in [item for item in scanner_tab.findChildren(QSplitter) if item.count() == 3]:
                self._configure_splitter(splitter, [380, 640, 640])
                splitter.setSizes([380, 640, 640])
                splitter.setStretchFactor(0, 3)
                splitter.setStretchFactor(1, 5)
                splitter.setStretchFactor(2, 5)

    def _refresh_monitor_summary_v29(self, symbol: str = "") -> None:
        original_refresh_monitor_summary_v29(self, symbol)
        target = symbol or (self._selected_symbol_from_watchlist() if hasattr(self, "_selected_symbol_from_watchlist") else "") or getattr(self, "active_symbol", "") or ""
        scan_count = len(getattr(self, "scan_rows", []) or [])
        watch_count = getattr(self, "watchlist_widget", None).count() if hasattr(self, "watchlist_widget") else 0
        if hasattr(self, "scanner_workbench_banner"):
            if target:
                stock_name = self._stock_name_for_symbol(target)
                self._set_label_text_if_changed(
                    self.scanner_workbench_banner,
                    workbench_banner_copy("scanner", "focus", stock_name=stock_name),
                )
            elif scan_count:
                self._set_label_text_if_changed(
                    self.scanner_workbench_banner,
                    workbench_banner_copy("scanner", "queue", scan_count=scan_count, watch_count=watch_count),
                )
            else:
                self._set_label_text_if_changed(
                    self.scanner_workbench_banner,
                    workbench_banner_copy("scanner", "empty"),
                )

        if not target and hasattr(self, "monitor_summary_text"):
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                workbench_empty_panel_copy("monitor_summary_text"),
            )

    def _refresh_board_focus_panels_v29(self, symbol: str = "") -> None:
        original_refresh_board_focus_panels_v29(self, symbol)
        target_symbol = symbol or (self._selected_board_symbol() if hasattr(self, "_selected_board_symbol") else "") or getattr(self, "active_symbol", "") or ""
        candidate_count = getattr(self, "board_table", None).rowCount() if hasattr(self, "board_table") else 0
        monitor_count = getattr(self, "board_monitor_table", None).rowCount() if hasattr(self, "board_monitor_table") else 0
        if hasattr(self, "board_workbench_banner"):
            if target_symbol:
                stock_name = self._stock_name_for_symbol(target_symbol)
                self._set_label_text_if_changed(
                    self.board_workbench_banner,
                    workbench_banner_copy("board", "focus", stock_name=stock_name),
                )
            elif candidate_count or monitor_count:
                self._set_label_text_if_changed(
                    self.board_workbench_banner,
                    workbench_banner_copy("board", "queue", candidate_count=candidate_count, monitor_count=monitor_count),
                )
            else:
                self._set_label_text_if_changed(
                    self.board_workbench_banner,
                    workbench_banner_copy("board", "empty"),
                )

        if not target_symbol and hasattr(self, "board_monitor_text"):
            self._set_plain_text_if_changed(
                self.board_monitor_text,
                workbench_empty_panel_copy("board_monitor_text"),
            )

    def _post_build_ui_tweaks_v29(self) -> None:
        original_post_build_ui_tweaks_v29(self)
        self._polish_scanner_board_workspace_v29()
        self._refresh_monitor_summary()
        self._refresh_board_focus_panels()

    window_cls._install_scanner_board_workbench_banners_v29 = _install_scanner_board_workbench_banners_v29
    window_cls._polish_scanner_board_workspace_v29 = _polish_scanner_board_workspace_v29
    window_cls._refresh_monitor_summary = _refresh_monitor_summary_v29
    window_cls._refresh_board_focus_panels = _refresh_board_focus_panels_v29
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v29

    original_post_build_ui_tweaks_v30 = window_cls._post_build_ui_tweaks
    original_refresh_workspace_status_labels_v30 = window_cls._refresh_workspace_status_labels
    original_refresh_recommendation_focus_panels_v30 = window_cls._refresh_recommendation_focus_panels
    original_refresh_broker_auxiliary_panels_v30 = window_cls._refresh_broker_auxiliary_panels

    def _has_pending_recommendations_v30(self) -> bool:
        rows = list(getattr(self, "daily_pool_rows", []) or [])
        return any(str(getattr(item, "execution_status", "") or "") in {"待观察", "待复核", "待送审", "REVIEWING"} for item in rows)

    def _has_failed_recommendations_v30(self) -> bool:
        rows = list(getattr(self, "daily_pool_rows", []) or [])
        return any(str(getattr(item, "execution_status", "") or "") in {"提交失败", "FAILED", "REJECTED"} for item in rows)

    def _refresh_action_button_states_v30(self) -> None:
        current_recommend = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
        trade_plan = getattr(self, "current_trade_plan", None)
        decisions = list(getattr(trade_plan, "decisions", []) or [])
        order_intents = list(getattr(self, "order_intents", []) or [])
        blockers = list((getattr(self, "last_broker_execution_summary", {}) or {}).get("blockers", []) or [])
        pending_exists = self._has_pending_recommendations_v30() if hasattr(self, "_has_pending_recommendations_v30") else False
        failed_exists = self._has_failed_recommendations_v30() if hasattr(self, "_has_failed_recommendations_v30") else False

        button_specs = [
            ("recommend_to_broker_button", current_recommend is not None, "先从机会池选中一只焦点股票，再送入交易链路。", "把当前焦点股票送入执行中控，并自动生成委托候选。"),
            ("plan_to_broker_button", bool(decisions), "需要先生成今日交易计划，才能把计划股送入执行中控。", "把交易计划里的焦点股票送入执行中控。"),
            ("focus_pending_button", pending_exists, "当前没有待复核的候选，先刷新机会池再看。", "快速定位待复核的高优先候选。"),
            ("retry_failed_button", failed_exists, "当前没有失败候选可复核。", "快速回看最近送审失败的标的。"),
            ("push_priority_button", bool(getattr(self, "daily_pool_rows", []) or []), "需要先生成机会池。", "把当前最高优先候选直接送入交易链路。"),
            ("broker_focus_blocker_button", bool(blockers), "当前没有阻塞项，先查看前排委托或继续生成委托。", "快速定位需要优先处理的阻塞委托。"),
            ("broker_focus_priority_button", bool(order_intents), "当前还没有委托建议，先从机会池生成委托。", "快速定位当前最高优先的委托建议。"),
        ]
        for attr_name, enabled, disabled_tip, enabled_tip in button_specs:
            button = getattr(self, attr_name, None)
            if not isinstance(button, QPushButton):
                continue
            button.setEnabled(enabled)
            button.setToolTip(enabled_tip if enabled else disabled_tip)

        selected_paper_symbol = bool(getattr(self, "_selected_paper_symbol", lambda: "")())
        for attr_name, enabled, disabled_tip, enabled_tip in [
            ("paper_to_recommend_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到机会池。"),
            ("paper_to_detail_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到复盘页。"),
            ("paper_to_broker_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到执行中控。"),
        ]:
            button = getattr(self, attr_name, None)
            if isinstance(button, QPushButton):
                button.setEnabled(enabled)
                button.setToolTip(enabled_tip if enabled else disabled_tip)

        focus_symbol = (
            getattr(self, "active_symbol", "") or ""
            or (self._selected_symbol_from_watchlist() if hasattr(self, "_selected_symbol_from_watchlist") else "")
            or (self._selected_board_symbol() if hasattr(self, "_selected_board_symbol") else "")
        )
        route_button_specs = {
            "查看复盘": (
                bool(focus_symbol),
                "先在扫描页、涨停策略、机会池或执行中控选中一只焦点股票。",
                "带着当前焦点股票跳到复盘页。",
            ),
            "查看复盘研究": (
                bool(focus_symbol),
                "先在当前页面选中一只焦点股票。",
                "带着当前焦点股票跳到复盘研究页。",
            ),
            "查看交易": (
                bool(focus_symbol) or bool(order_intents),
                "先选中一只股票，或先生成委托建议。",
                "带着当前焦点股票跳到执行中控。",
            ),
            "去交易页": (
                bool(focus_symbol) or bool(order_intents) or bool(decisions),
                "先生成焦点股票、委托建议或交易计划。",
                "跳到执行中控继续推进委托和执行。",
            ),
            "查看推荐": (
                bool(focus_symbol) or bool(getattr(self, "daily_pool_rows", []) or []),
                "先刷新机会池，或先选中一只焦点股票。",
                "带着当前焦点股票跳到机会池。",
            ),
            "查看机会池": (
                bool(getattr(self, "daily_pool_rows", []) or []),
                "需要先生成机会池。",
                "跳到机会池并自动定位当前焦点。",
            ),
        }
        for tab_name in ["scanner_tab", "board_tab", "recommend_tab", "broker_tab", "detail_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for button in tab.findChildren(QPushButton):
                action_key = button_route_action_key(button)
                text = (button.text() or "").strip()
                spec = route_button_specs.get(action_key) or route_button_specs.get(text)
                if spec is None:
                    continue
                enabled, disabled_tip, enabled_tip = spec
                button.setEnabled(enabled)
                button.setToolTip(enabled_tip if enabled else disabled_tip)

    def _open_monitor_symbol_in_detail_v30(self) -> None:
        symbol = self._selected_symbol_from_watchlist() if hasattr(self, "_selected_symbol_from_watchlist") else ""
        if not symbol:
            symbol = getattr(self, "active_symbol", "") or ""
        if symbol and hasattr(self, "_focus_symbol_everywhere"):
            self._focus_symbol_everywhere(symbol, origin="scanner")
        self.open_focus_symbol_in_detail()

    def _rebind_scanner_board_routes_v30(self) -> None:
        for tab_name in ["scanner_tab", "board_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for button in tab.findChildren(QPushButton):
                action_key = button_route_action_key(button)
                text = (button.text() or "").strip()
                if action_key in {"看复盘", "查看复盘", "查看复盘研究"} or text in {"查看复盘", "查看复盘研究", "看复盘"}:
                    try:
                        button.clicked.disconnect()
                    except Exception:
                        pass
                    button.clicked.connect(self.open_monitor_symbol_in_detail)
                    button.setToolTip("带着当前焦点股票跳到复盘页，继续看决策、执行和复盘结论。")

    def _refresh_workspace_status_labels_v30(self) -> None:
        original_refresh_workspace_status_labels_v30(self)
        self._refresh_action_button_states_v30()

    def _refresh_recommendation_focus_panels_v30(self, row: RecommendationRow | None = None) -> None:
        original_refresh_recommendation_focus_panels_v30(self, row)
        self._refresh_action_button_states_v30()

    def _refresh_broker_auxiliary_panels_v30(self) -> None:
        original_refresh_broker_auxiliary_panels_v30(self)
        self._refresh_action_button_states_v30()

    def _post_build_ui_tweaks_v30(self) -> None:
        original_post_build_ui_tweaks_v30(self)
        self._rebind_scanner_board_routes_v30()
        self._refresh_action_button_states_v30()

    window_cls._has_pending_recommendations_v30 = _has_pending_recommendations_v30
    window_cls._has_failed_recommendations_v30 = _has_failed_recommendations_v30
    window_cls._refresh_action_button_states_v30 = _refresh_action_button_states_v30
    window_cls.open_monitor_symbol_in_detail = _open_monitor_symbol_in_detail_v30
    window_cls._rebind_scanner_board_routes_v30 = _rebind_scanner_board_routes_v30
    window_cls._refresh_workspace_status_labels = _refresh_workspace_status_labels_v30
    window_cls._refresh_recommendation_focus_panels = _refresh_recommendation_focus_panels_v30
    window_cls._refresh_broker_auxiliary_panels = _refresh_broker_auxiliary_panels_v30
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v30

    original_post_build_ui_tweaks_v31 = window_cls._post_build_ui_tweaks

    def _dedupe_action_row_labels_v31(self) -> None:
        row_button_text_map = {
            "overviewThemeActionRow": {"查看推荐池": "打开推荐池", "查看消息催化": "打开消息线索"},
            "overviewCapitalActionRow": {"去看推荐": "资金看推荐", "回到总览": "资金回总览"},
            "overviewDecisionActionRow": {"去看交易": "决策去交易", "去看推荐": "决策看推荐"},
            "recommendPoolActionRow": {"查看总览": "机会池看总览", "定位推荐池": "定位机会池"},
            "recommendPlanActionRow": {"重算计划": "重算交易计划", "去交易页": "计划去交易", "看观察池": "计划看观察池"},
            "recommendPulseActionRow": {"回到总览": "脉搏回总览", "看消息催化": "脉搏看消息"},
            "recommendHoldingActionRow": {"查看风险池": "持仓看风险池", "去交易页": "持仓去交易"},
            "boardCandidateActionRow": {"查看推荐": "候选看推荐", "查看扫描": "候选看扫描", "查看总览": "候选看总览", "去交易页": "候选去交易"},
            "boardMonitorActionRow": {"刷新监控": "刷新专项监控", "查看推荐": "监控看推荐", "查看扫描": "监控看扫描", "查看总览": "监控看总览"},
            "brokerGateActionRow": {"定位委托": "闸门定位委托", "查看推荐": "闸门看推荐"},
            "brokerExecutionActionRow": {"查看委托": "执行看委托", "查看成交": "执行看成交", "查看推荐": "执行看推荐"},
            "brokerRecapActionRow": {"查看成交": "回执看成交", "查看委托": "回执看委托"},
            "detailMetricsActionRow": {"回到总览": "复盘回总览", "查看机会池": "复盘看机会池"},
            "detailDecisionActionRow": {"查看机会池": "决策看机会池", "查看扫描": "决策看扫描"},
            "detailExecutionActionRow": {"前往交易执行": "执行去交易", "查看复盘": "执行看复盘"},
            "detailConclusionActionRow": {"查看机会池": "结论看机会池", "前往交易执行": "结论去交易"},
        }
        for row_name, mapping in row_button_text_map.items():
            row = self.findChild(QWidget, row_name)
            if row is None:
                continue
            for button in row.findChildren(QPushButton):
                text = (button.text() or "").strip()
                target = mapping.get(text)
                if target and target != text:
                    self._set_label_text_if_changed(button, target)
                final_text = (button.text() or "").strip()
                tip = action_row_tooltip_copy(final_text)
                if tip:
                    button.setToolTip(tip)

    def _post_build_ui_tweaks_v31(self) -> None:
        original_post_build_ui_tweaks_v31(self)
        self._dedupe_action_row_labels_v31()

    window_cls._dedupe_action_row_labels_v31 = _dedupe_action_row_labels_v31
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v31

    original_post_build_ui_tweaks_v32 = window_cls._post_build_ui_tweaks

    def _button_context_prefix_v32(self, button: QPushButton) -> str:
        return contextual_button_prefix(button)

    def _trim_duplicate_entry_buttons_v32(self) -> None:
        for tab_name in ["overview_tab", "scanner_tab", "recommend_tab", "broker_tab", "board_tab", "detail_tab"]:
            mapping = contextual_entry_rename_targets(tab_name)
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for original_text, replacements in mapping.items():
                buttons = [button for button in tab.findChildren(QPushButton) if (button.text() or "").strip() == original_text]
                for index, button in enumerate(buttons):
                    action_key = contextual_entry_action_key(
                        button,
                        original_text=original_text,
                        replacements=replacements,
                        index=index,
                    )
                    target_text = contextual_entry_display_text(action_key) or action_key
                    if hasattr(button, "property") and hasattr(button, "setProperty"):
                        if button.property("routeActionKey") != action_key:
                            button.setProperty("routeActionKey", action_key)
                    if (button.text() or "").strip() != target_text:
                        self._set_label_text_if_changed(button, target_text)
                    if not button.toolTip():
                        button.setToolTip(
                            contextual_entry_tooltip(
                                action_key,
                                prefix=self._button_context_prefix_v32(button),
                            )
                        )

    def _refine_workspace_proportions_v32(self) -> None:
        text_specs = {
            "recommend_dispatch_text": (156, 204),
            "recommend_focus_review_text": (164, 220),
            "recommend_queue_text": (156, 204),
            "broker_status_text": (150, 220),
            "broker_order_focus_text": (210, 16777215),
            "order_result_text": (168, 16777215),
            "broker_recap_text": (176, 228),
            "detail_execution_text": (216, 16777215),
            "detail_conclusion_text": (216, 16777215),
        }
        for attr_name, (min_height, max_height) in text_specs.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                widget.setMinimumHeight(min_height)
                widget.setMaximumHeight(max_height)
                widget.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        table_specs = {
            "daily_pool_table": 420,
            "trade_plan_table": 280,
            "orders_table": 240,
            "execution_table": 240,
            "board_table": 240,
            "board_monitor_table": 220,
            "scan_table": 260,
        }
        for attr_name, min_height in table_specs.items():
            table = getattr(self, attr_name, None)
            if isinstance(table, QTableWidget):
                table.setMinimumHeight(min_height)
                table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        splitter_specs = {
            "workspaceControlSplit": [230, 260, 230],
            "brokerOrderFocusSplit": [260, 372],
        }
        for object_name, sizes in splitter_specs.items():
            splitter = self.findChild(QSplitter, object_name)
            if isinstance(splitter, QSplitter):
                try:
                    splitter.setSizes(sizes)
                    splitter.setChildrenCollapsible(False)
                except Exception:
                    pass

        for tab_name in ["recommend_tab", "broker_tab", "detail_tab", "scanner_tab", "board_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            layout = tab.layout()
            if layout is not None:
                layout.setContentsMargins(14, 14, 14, 14)
                layout.setSpacing(max(layout.spacing(), 12))

    def _post_build_ui_tweaks_v32(self) -> None:
        original_post_build_ui_tweaks_v32(self)
        self._trim_duplicate_entry_buttons_v32()
        self._refine_workspace_proportions_v32()

    window_cls._button_context_prefix_v32 = _button_context_prefix_v32
    window_cls._trim_duplicate_entry_buttons_v32 = _trim_duplicate_entry_buttons_v32
    window_cls._refine_workspace_proportions_v32 = _refine_workspace_proportions_v32
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v32

    original_refresh_action_button_states_v33 = window_cls._refresh_action_button_states_v30
    original_post_build_ui_tweaks_v33 = window_cls._post_build_ui_tweaks

    def _refresh_action_button_states_v33(self) -> None:
        original_refresh_action_button_states_v33(self)
        focus_symbol = (
            getattr(self, "active_symbol", "") or ""
            or (self._selected_symbol_from_watchlist() if hasattr(self, "_selected_symbol_from_watchlist") else "")
            or (self._selected_board_symbol() if hasattr(self, "_selected_board_symbol") else "")
        )
        has_pool = bool(getattr(self, "daily_pool_rows", []) or [])
        order_intents = list(getattr(self, "order_intents", []) or [])
        decisions = list(getattr(getattr(self, "current_trade_plan", None), "decisions", []) or [])
        selected_paper_symbol = bool(getattr(self, "_selected_paper_symbol", lambda: "")())
        for tab_name in ["scanner_tab", "board_tab", "recommend_tab", "broker_tab", "detail_tab", "overview_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for button in tab.findChildren(QPushButton):
                action_key = button_route_action_key(button)
                spec = contextual_route_button_state(
                    action_key,
                    focus_symbol=bool(focus_symbol),
                    has_pool=has_pool,
                    order_intents=bool(order_intents),
                    decisions=bool(decisions),
                    selected_paper_symbol=selected_paper_symbol,
                )
                if spec is None:
                    continue
                enabled, disabled_tip, enabled_tip = spec
                button.setEnabled(enabled)
                button.setToolTip(enabled_tip if enabled else disabled_tip)

    def _hydrate_runtime_empty_states_v33(self) -> None:
        if hasattr(self, "runtime_log_text") and isinstance(self.runtime_log_text, QTextEdit):
            current = self.runtime_log_text.toPlainText().strip()
            if not current:
                self._set_plain_text_if_changed(
                    self.runtime_log_text,
                    workbench_empty_panel_copy("runtime_log_text"),
                )

        if hasattr(self, "paper_experiment_text") and isinstance(self.paper_experiment_text, QTextEdit):
            current = self.paper_experiment_text.toPlainText().strip()
            if not current:
                self._set_plain_text_if_changed(
                    self.paper_experiment_text,
                    workbench_empty_panel_copy("paper_experiment_text"),
                )

    def _post_build_ui_tweaks_v33(self) -> None:
        original_post_build_ui_tweaks_v33(self)
        self._hydrate_runtime_empty_states_v33()
        self._refresh_action_button_states_v30()

    window_cls._refresh_action_button_states_v30 = _refresh_action_button_states_v33
    window_cls._hydrate_runtime_empty_states_v33 = _hydrate_runtime_empty_states_v33
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v33
    window_cls._qh_workspace_workbench_patches_applied_v33 = True
