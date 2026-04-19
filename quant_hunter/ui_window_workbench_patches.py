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
        banner = QLabel("交易工作台：先生成委托，再确认提交，最后回看执行偏差。")
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
                text = f"交易工作台：正在回看 {stock_name} 的执行反馈，继续检查成交状态、失败原因和偏差。"
            elif intent is not None:
                symbol = getattr(intent, "symbol", "") or ""
                stock_name = self._stock_name_for_symbol(symbol) if symbol else "焦点委托"
                experiment_badge = experiment_lines[0].replace("模拟盘实验：", "") if experiment_lines else "实验待同步"
                text = f"交易工作台：当前聚焦 {stock_name}，下一步打开确认弹窗核对账户、价格、止损与仓位。| {experiment_badge}"
            elif order_count:
                text = f"交易工作台：已生成 {order_count} 笔待提交委托，优先选中一笔查看主线闸门和风险灯。"
            elif submit_count:
                text = f"交易工作台：已有 {submit_count} 条回执记录，可继续在下方复盘执行偏差。"
            else:
                text = "交易工作台：先从推荐池生成委托，再进入确认提交和执行回顾。"
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
            ("recommend_tab", "recommend_scroll_area", "recommend_workbench_banner", "推荐工作台：先看主线前排，再做送审和交易决策。"),
            ("detail_tab", "detail_workspace_scroll_area", "detail_workbench_banner", "复盘工作台：先看决策画像，再看执行偏差和复盘结论。"),
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
            ("recommend_review_splitter", [820, 620]),
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
                text = "推荐工作台：先刷新市场和推荐池，再从前排候选里挑出今天最值得送审的标的。"
            else:
                stock_name = getattr(current, "stock_name", "") or self._stock_name_for_symbol(getattr(current, "symbol", "") or "")
                action_text = self._display_action(getattr(current, "action", "WATCH"))
                text = f"推荐工作台：当前聚焦 {stock_name}，先复核价位与风险，再决定是否送审并转入交易链路。"
                if str(getattr(current, "action", "") or "").upper() == "BUY":
                    text = f"推荐工作台：当前聚焦 {stock_name}，属于可执行候选，下一步优先核对买点、止损和主线延续。"
                elif action_text:
                    text = f"推荐工作台：当前聚焦 {stock_name}，动作偏向{action_text}，先确认主线状态再决定是否推进。"
            self._set_label_text_if_changed(self.recommend_workbench_banner, text)

        if current is None and hasattr(self, "recommend_decision_summary_text"):
            self._set_plain_text_if_changed(
                self.recommend_decision_summary_text,
                "\n".join(
                    [
                        "单票决策摘要",
                        "",
                        "当前还没有焦点股票。",
                        "建议动作：",
                        "1. 先刷新市场，生成每日推荐池。",
                        "2. 从前排候选里选中一只股票，查看主线、价位和风险。",
                        "3. 确认逻辑成立后，再决定是否送审进入交易链路。",
                    ]
                ),
            )

    def _refresh_detail_workspace_panels_v28(self) -> None:
        original_refresh_detail_workspace_panels_v28(self)
        symbol = getattr(self, "active_symbol", "") or ""
        stock_name = self._stock_name_for_symbol(symbol) if symbol else ""
        if hasattr(self, "detail_workbench_banner"):
            if symbol:
                self._set_label_text_if_changed(
                    self.detail_workbench_banner,
                    f"复盘工作台：当前聚焦 {stock_name}，继续核对决策逻辑、执行偏差和下一次识别点。",
                )
            else:
                self._set_label_text_if_changed(
                    self.detail_workbench_banner,
                    "复盘工作台：先从推荐页、交易页或扫描页联动一只股票，再查看完整复盘链路。",
                )

        if not symbol:
            if hasattr(self, "metrics_text"):
                self._set_plain_text_if_changed(
                    self.metrics_text,
                    "\n".join(
                        [
                            "策略摘要",
                            "",
                            "这里会在选中股票后展示收益、回撤、胜率、阶段统计和近期信号。",
                            "建议动作：",
                            "1. 先从推荐页或交易页联动一只焦点股票。",
                            "2. 再看这只票的题材位置、信号质量和最近执行情况。",
                        ]
                    ),
                )
            if hasattr(self, "detail_decision_text"):
                self._set_plain_text_if_changed(
                    self.detail_decision_text,
                    "\n".join(
                        [
                            "交易决策画像",
                            "",
                            "这里会汇总单票的主线地位、动作建议、计划价位和核心逻辑。",
                            "建议动作：先选中一只股票，再判断这笔交易当时该不该做。",
                        ]
                    ),
                )
            if hasattr(self, "detail_execution_text"):
                self._set_plain_text_if_changed(
                    self.detail_execution_text,
                    "\n".join(
                        [
                            "执行状态回放",
                            "",
                            "这里会关联送审、委托、提交、成交和失败记录。",
                            "建议动作：先从交易页选中一笔委托或回执，再回来定位执行偏差。",
                        ]
                    ),
                )
            if hasattr(self, "detail_conclusion_text"):
                self._set_plain_text_if_changed(
                    self.detail_conclusion_text,
                    "\n".join(
                        [
                            "复盘结论",
                            "",
                            "这里会沉淀单票最值得留下来的结论、纪律得失和下一步观察点。",
                            "建议动作：选中焦点股票后，再回看今天做对了什么、错过了什么。",
                        ]
                    ),
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
            ("scanner_tab", "scanner_workspace_scroll_area", "scanner_workbench_banner", "扫描工作台：先看扫描结果，再看观察池和盘中监控联动。"),
            ("board_tab", "board_workspace_scroll_area", "board_workbench_banner", "打板工作台：先看强势候选，再看回封监控和风险灯。"),
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
                    f"扫描工作台：当前聚焦 {stock_name}，继续核对扫描信号、观察池状态和盘中监控联动。",
                )
            elif scan_count:
                self._set_label_text_if_changed(
                    self.scanner_workbench_banner,
                    f"扫描工作台：已生成 {scan_count} 条扫描信号，下一步优先从观察池 {watch_count} 只里选中焦点票。",
                )
            else:
                self._set_label_text_if_changed(
                    self.scanner_workbench_banner,
                    "扫描工作台：先执行扫描或载入样本数据，再查看观察池和盘中监控摘要。",
                )

        if not target and hasattr(self, "monitor_summary_text"):
            self._set_plain_text_if_changed(
                self.monitor_summary_text,
                "\n".join(
                    [
                        "盘中监控摘要",
                        "",
                        f"当前状态：扫描信号 {scan_count} 条 | 观察池 {watch_count} 只",
                        "建议动作：",
                        "1. 先执行扫描，或载入样本数据建立首轮股票池。",
                        "2. 再从观察池里选中一只股票，查看信号、催化和推荐联动。",
                        "3. 如果出现强势候选，可继续联动到打板页或交易页。",
                    ]
                ),
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
                    f"打板工作台：当前聚焦 {stock_name}，继续核对触发方式、回封强度、炸板风险和是否值得送审。",
                )
            elif candidate_count or monitor_count:
                self._set_label_text_if_changed(
                    self.board_workbench_banner,
                    f"打板工作台：当前有 {candidate_count} 只候选、{monitor_count} 条监控，优先查看最强回封和高风险炸板票。",
                )
            else:
                self._set_label_text_if_changed(
                    self.board_workbench_banner,
                    "打板工作台：先从扫描页或推荐页联动强势候选，再看回封观察和风险灯。",
                )

        if not target_symbol and hasattr(self, "board_monitor_text"):
            self._set_plain_text_if_changed(
                self.board_monitor_text,
                "\n".join(
                    [
                        "炸板 / 回封监控",
                        "",
                        f"当前状态：打板候选 {candidate_count} 只 | 监控记录 {monitor_count} 条",
                        "建议动作：",
                        "1. 先从左侧候选或监控表里选中一只强势票。",
                        "2. 核对触发方式、回封概率、炸板风险和动作建议。",
                        "3. 若逻辑成立，再联动去推荐页或交易页继续推进。",
                    ]
                ),
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
            ("recommend_to_broker_button", current_recommend is not None, "先从推荐池选中一只焦点股票，再送入交易链路。", "把当前焦点股票送入交易页，并自动生成委托候选。"),
            ("plan_to_broker_button", bool(decisions), "需要先生成今日交易计划，才能把计划股送入交易页。", "把交易计划里的焦点股票送入交易页。"),
            ("focus_pending_button", pending_exists, "当前没有待复核的候选，先刷新推荐池再看。", "快速定位待复核的高优先候选。"),
            ("retry_failed_button", failed_exists, "当前没有失败候选可复核。", "快速回看最近送审失败的标的。"),
            ("push_priority_button", bool(getattr(self, "daily_pool_rows", []) or []), "需要先生成每日推荐池。", "把当前最高优先候选直接送入交易链路。"),
            ("broker_focus_blocker_button", bool(blockers), "当前没有阻塞项，先查看前排委托或继续生成委托。", "快速定位需要优先处理的阻塞委托。"),
            ("broker_focus_priority_button", bool(order_intents), "当前还没有委托建议，先从推荐池生成委托。", "快速定位当前最高优先的委托建议。"),
        ]
        for attr_name, enabled, disabled_tip, enabled_tip in button_specs:
            button = getattr(self, attr_name, None)
            if not isinstance(button, QPushButton):
                continue
            button.setEnabled(enabled)
            button.setToolTip(enabled_tip if enabled else disabled_tip)

        selected_paper_symbol = bool(getattr(self, "_selected_paper_symbol", lambda: "")())
        for attr_name, enabled, disabled_tip, enabled_tip in [
            ("paper_to_recommend_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到推荐页。"),
            ("paper_to_detail_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到复盘页。"),
            ("paper_to_broker_button", selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着当前模拟盘焦点回到交易页。"),
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
                "先在扫描页、打板页、推荐页或交易页选中一只焦点股票。",
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
                "带着当前焦点股票跳到交易页。",
            ),
            "去交易页": (
                bool(focus_symbol) or bool(order_intents) or bool(decisions),
                "先生成焦点股票、委托建议或交易计划。",
                "跳到交易页继续推进委托和执行。",
            ),
            "查看推荐": (
                bool(focus_symbol) or bool(getattr(self, "daily_pool_rows", []) or []),
                "先刷新推荐池，或先选中一只焦点股票。",
                "带着当前焦点股票跳到推荐页。",
            ),
            "查看机会池": (
                bool(getattr(self, "daily_pool_rows", []) or []),
                "需要先生成每日推荐池。",
                "跳到机会池并自动定位当前焦点。",
            ),
        }
        for tab_name in ["scanner_tab", "board_tab", "recommend_tab", "broker_tab", "detail_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for button in tab.findChildren(QPushButton):
                text = (button.text() or "").strip()
                spec = route_button_specs.get(text)
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
                text = (button.text() or "").strip()
                if text in {"查看复盘", "查看复盘研究"}:
                    try:
                        button.clicked.disconnect()
                    except Exception:
                        pass
                    button.clicked.connect(self.open_monitor_symbol_in_detail)
                    button.setToolTip("带着当前焦点股票跳到复盘页，继续查看决策、执行和复盘结论。")

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
        tooltip_map = {
            "打开推荐池": "从总览直接跳到推荐池。",
            "打开消息线索": "从总览直接查看消息催化。",
            "资金看推荐": "带着资金画像视角切到推荐页。",
            "资金回总览": "回到市场总览继续看全局。",
            "决策去交易": "从决策视角直接切到交易页。",
            "决策看推荐": "从决策视角回到推荐池。",
            "机会池看总览": "带着机会池上下文回看市场总览。",
            "定位机会池": "定位到推荐池中的当前焦点。",
            "重算交易计划": "重新生成今日交易计划。",
            "计划去交易": "带着计划上下文跳到交易页。",
            "计划看观察池": "跳到观察池继续筛选。",
            "脉搏回总览": "回到总览继续看市场脉搏。",
            "脉搏看消息": "查看消息催化与新闻线索。",
            "持仓看风险池": "优先查看风险处理建议。",
            "持仓去交易": "带着持仓处理上下文切到交易页。",
            "候选看推荐": "把当前打板候选同步到推荐页。",
            "候选看扫描": "把当前打板候选同步到扫描页。",
            "候选看总览": "把当前打板候选同步到总览。",
            "候选去交易": "把当前打板候选带到交易页。",
            "刷新专项监控": "刷新打板专项监控与回封观察。",
            "监控看推荐": "把当前监控焦点同步到推荐页。",
            "监控看扫描": "把当前监控焦点同步到扫描页。",
            "监控看总览": "把当前监控焦点同步到总览。",
            "闸门定位委托": "定位到交易页里的焦点委托。",
            "闸门看推荐": "回到推荐页核对主线和价位。",
            "执行看委托": "查看委托建议和价格计划。",
            "执行看成交": "查看最新提交记录和成交反馈。",
            "执行看推荐": "回到推荐页检查原始逻辑。",
            "回执看成交": "直接查看执行回执与成交反馈。",
            "回执看委托": "回到委托列表继续核对。",
            "复盘回总览": "带着当前焦点回到总览。",
            "复盘看机会池": "带着当前焦点回到推荐池。",
            "决策看机会池": "从决策画像跳回机会池。",
            "决策看扫描": "从决策画像跳回扫描页。",
            "执行去交易": "带着当前焦点跳到交易执行页。",
            "执行看复盘": "继续查看当前焦点的复盘内容。",
            "结论看机会池": "从复盘结论回到机会池。",
            "结论去交易": "从复盘结论切到交易执行页。",
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
                if final_text in tooltip_map:
                    button.setToolTip(tooltip_map[final_text])

    def _post_build_ui_tweaks_v31(self) -> None:
        original_post_build_ui_tweaks_v31(self)
        self._dedupe_action_row_labels_v31()

    window_cls._dedupe_action_row_labels_v31 = _dedupe_action_row_labels_v31
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v31

    original_post_build_ui_tweaks_v32 = window_cls._post_build_ui_tweaks

    def _button_context_prefix_v32(self, button: QPushButton) -> str:
        ancestor = button.parentWidget()
        while ancestor is not None:
            object_name = (ancestor.objectName() or "").strip()
            if object_name:
                if "Capital" in object_name:
                    return "资金"
                if "Decision" in object_name:
                    return "决策"
                if "Theme" in object_name:
                    return "主线"
                if "Execution" in object_name:
                    return "执行"
                if "Metrics" in object_name:
                    return "指标"
                if "Gate" in object_name:
                    return "闸门"
                if "Monitor" in object_name:
                    return "监控"
                if "Candidate" in object_name:
                    return "候选"
                if "Holding" in object_name:
                    return "持仓"
                if "Plan" in object_name:
                    return "计划"
                if "Pulse" in object_name:
                    return "脉搏"
                if "Log" in object_name:
                    return "日志"
                if object_name == "workspaceToolPanel":
                    return "工具"
                if object_name == "terminalPanel":
                    return "面板"
            ancestor = ancestor.parentWidget()
        return "工作台"

    def _trim_duplicate_entry_buttons_v32(self) -> None:
        rename_targets = {
            "overview_tab": {
                "全部": ["主线全部", "资金全部"],
                "去看推荐": ["资金看推荐", "决策看推荐"],
                "回到最新": ["主线回最新", "资金回最新"],
                "查看机会池": ["资金看机会池", "决策看机会池"],
            },
            "scanner_tab": {
                "查看打板": ["工具看打板", "面板看打板"],
                "查看推荐": ["工具看推荐", "面板看推荐"],
            },
            "recommend_tab": {
                "前往交易执行": ["计划去交易", "持仓去交易"],
                "重算计划": ["轻量重算计划"],
            },
            "broker_tab": {
                "刷新诊断": ["工具刷新诊断", "日志刷新诊断"],
                "导出日志": ["工具导出日志", "日志导出日志"],
                "查看机会池": ["闸门看机会池", "执行看机会池"],
            },
            "board_tab": {
                "查看机会池": ["候选看机会池", "监控看机会池"],
            },
            "detail_tab": {
                "回到市场总览": ["指标回总览", "决策回总览"],
                "查看扫描": ["指标看扫描", "执行看扫描"],
            },
        }
        tooltip_suffix = {
            "资金": "以资金与轮动视角继续联动。",
            "决策": "以决策推演视角继续联动。",
            "主线": "以主线强弱视角继续联动。",
            "执行": "以交易执行视角继续联动。",
            "指标": "以复盘指标视角继续联动。",
            "闸门": "以闸门审查视角继续联动。",
            "监控": "以盘中监控视角继续联动。",
            "候选": "以打板候选视角继续联动。",
            "持仓": "以持仓处理视角继续联动。",
            "计划": "以交易计划视角继续联动。",
            "脉搏": "以市场脉搏视角继续联动。",
            "日志": "以日志与回放视角继续联动。",
            "工具": "从工具入口继续联动。",
            "面板": "从内容面板继续联动。",
            "工作台": "从当前工作台继续联动。",
        }
        for tab_name, mapping in rename_targets.items():
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for original_text, replacements in mapping.items():
                buttons = [button for button in tab.findChildren(QPushButton) if (button.text() or "").strip() == original_text]
                for index, button in enumerate(buttons):
                    target_text = replacements[index] if index < len(replacements) else f"{self._button_context_prefix_v32(button)}{original_text}"
                    if (button.text() or "").strip() != target_text:
                        self._set_label_text_if_changed(button, target_text)
                    prefix = self._button_context_prefix_v32(button)
                    if not button.toolTip():
                        button.setToolTip(tooltip_suffix.get(prefix, tooltip_suffix["工作台"]))

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

        extended_specs = {
            "资金看推荐": (bool(focus_symbol) or has_pool, "先刷新推荐池，或先选中一只焦点股票。", "从资金视角跳到推荐页继续联动。"),
            "决策看推荐": (bool(focus_symbol) or has_pool, "先刷新推荐池，或先选中一只焦点股票。", "从决策视角跳到推荐页继续联动。"),
            "工具看推荐": (bool(focus_symbol) or has_pool, "先扫描或刷新推荐池，形成可跟踪焦点。", "从工具栏带着焦点跳到推荐页。"),
            "面板看推荐": (bool(focus_symbol) or has_pool, "先扫描或刷新推荐池，形成可跟踪焦点。", "从内容面板带着焦点跳到推荐页。"),
            "候选看推荐": (bool(focus_symbol) or has_pool, "先生成打板候选，或先选中一只焦点股票。", "把打板候选同步到推荐页。"),
            "监控看推荐": (bool(focus_symbol) or has_pool, "先生成盘中监控焦点，再去推荐页联动。", "把监控焦点同步到推荐页。"),
            "计划去交易": (bool(decisions) or bool(order_intents), "需要先生成交易计划或委托建议。", "带着计划上下文跳到交易页。"),
            "持仓去交易": (bool(focus_symbol) or bool(order_intents), "先从推荐池选中持仓处理对象，或先生成委托建议。", "带着持仓处理上下文跳到交易页。"),
            "执行去交易": (bool(focus_symbol) or bool(order_intents), "先选中一只股票，或先生成委托建议。", "从执行画像跳到交易页。"),
            "结论去交易": (bool(focus_symbol) or bool(order_intents), "先选中一只股票，或先生成委托建议。", "从复盘结论跳到交易页推进执行。"),
            "候选去交易": (bool(focus_symbol) or bool(order_intents), "先选中候选股票，或先生成委托建议。", "把打板候选带到交易页。"),
            "闸门看机会池": (has_pool, "需要先生成每日推荐池。", "从闸门审查跳回机会池核对逻辑。"),
            "执行看机会池": (has_pool, "需要先生成每日推荐池。", "从执行区跳回机会池核对逻辑。"),
            "候选看机会池": (has_pool, "需要先生成每日推荐池。", "从候选区跳回机会池。"),
            "监控看机会池": (has_pool, "需要先生成每日推荐池。", "从监控区跳回机会池。"),
            "复盘看机会池": (has_pool, "需要先生成每日推荐池。", "从复盘指标区跳回机会池。"),
            "结论看机会池": (has_pool, "需要先生成每日推荐池。", "从复盘结论跳回机会池。"),
            "决策看机会池": (has_pool, "需要先生成每日推荐池。", "从决策画像跳回机会池。"),
            "指标看扫描": (bool(focus_symbol), "先在推荐页、扫描页或交易页选中一只焦点股票。", "从指标区跳回扫描页继续查看。"),
            "执行看扫描": (bool(focus_symbol), "先在当前页面选中一只焦点股票。", "从执行区跳回扫描页继续查看。"),
            "候选看扫描": (bool(focus_symbol), "先选中一只打板候选股票。", "把当前候选同步到扫描页。"),
            "监控看扫描": (bool(focus_symbol), "先选中一只监控焦点股票。", "把当前监控焦点同步到扫描页。"),
            "纸面看推荐": (selected_paper_symbol, "先在模拟盘持仓或流水里选中一只股票。", "带着模拟盘焦点跳到推荐页。"),
        }
        for tab_name in ["scanner_tab", "board_tab", "recommend_tab", "broker_tab", "detail_tab", "overview_tab"]:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget):
                continue
            for button in tab.findChildren(QPushButton):
                text = (button.text() or "").strip()
                spec = extended_specs.get(text)
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
                    "\n".join(
                        [
                            "运行日志",
                            "",
                            "这里会记录刷新市场、导出报告、生成委托、提交执行和跨页联动动作。",
                            "建议先这样用：",
                            "1. 先刷新市场或生成推荐池，确认今天的前排焦点。",
                            "2. 再进入交易页生成委托，并观察最新执行回执。",
                            "3. 收盘后回到复盘页，沉淀执行偏差与结论。",
                        ]
                    ),
                )

        if hasattr(self, "paper_experiment_text") and isinstance(self.paper_experiment_text, QTextEdit):
            current = self.paper_experiment_text.toPlainText().strip()
            if not current:
                self._set_plain_text_if_changed(
                    self.paper_experiment_text,
                    "\n".join(
                        [
                            "实验记录",
                            "",
                            "这里会沉淀模拟盘的策略轮动、仓位变化、失败样本和可复用经验。",
                            "建议动作：",
                            "- 先初始化模拟盘，再运行一轮 AI 自主交易。",
                            "- 导出报告后，把收益和回撤对照到推荐与执行页面继续校验。",
                        ]
                    ),
                )

    def _post_build_ui_tweaks_v33(self) -> None:
        original_post_build_ui_tweaks_v33(self)
        self._hydrate_runtime_empty_states_v33()
        self._refresh_action_button_states_v30()

    window_cls._refresh_action_button_states_v30 = _refresh_action_button_states_v33
    window_cls._hydrate_runtime_empty_states_v33 = _hydrate_runtime_empty_states_v33
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v33
    window_cls._qh_workspace_workbench_patches_applied_v33 = True
