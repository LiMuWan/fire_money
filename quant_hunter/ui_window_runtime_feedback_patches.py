from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget

from quant_hunter.ui_config import workbench_empty_panel_copy


def apply_runtime_feedback_patches(
    window_cls: type,
    *,
    mainline_signal_brief_fn,
    signal_action_text_fn,
) -> None:
    if getattr(window_cls, "_qh_runtime_feedback_patches_applied_v16", False):
        return

    original_open_detail_to_recommend_v11 = window_cls.open_detail_to_recommend
    original_open_detail_to_scanner_v11 = window_cls.open_detail_to_scanner
    original_open_detail_to_broker_v11 = window_cls.open_detail_to_broker
    original_open_broker_focus_recommend_v11 = window_cls.open_broker_focus_recommend
    original_open_broker_focus_orders_v11 = window_cls.open_broker_focus_orders
    original_open_broker_focus_execution_v11 = window_cls.open_broker_focus_execution
    original_open_runtime_to_overview_v11 = window_cls.open_runtime_to_overview
    original_refresh_runtime_panel_v11 = window_cls.refresh_runtime_panel
    original_export_runtime_log_v11 = window_cls.export_runtime_log
    original_refresh_workspace_status_labels_v11 = window_cls._refresh_workspace_status_labels

    def _emit_action_feedback_v11(
        self,
        destination: str,
        detail: str,
        recommend_text: str = "",
        broker_text: str = "",
        scan_text: str = "",
    ) -> None:
        try:
            self._append_runtime_log(f"页面联动：{destination} | {detail}")
        except Exception:
            pass

        if recommend_text and hasattr(self, "recommend_status_label"):
            self._set_label_text_if_changed(self.recommend_status_label, recommend_text)
        if broker_text and hasattr(self, "broker_status_banner"):
            self._set_label_text_if_changed(self.broker_status_banner, broker_text)
        if scan_text and hasattr(self, "scan_summary_label"):
            self._set_label_text_if_changed(self.scan_summary_label, scan_text)

        if hasattr(self, "_refresh_runtime_story_v10"):
            self._refresh_runtime_story_v10()

    def _open_detail_to_recommend_v11(self) -> None:
        original_open_detail_to_recommend_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        detail = f"复盘 -> 机会池 | {self._stock_name_for_symbol(symbol)}" if symbol else "复盘 -> 机会池"
        recommend_text = (
            f"推荐状态：已从复盘同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 当前结论：继续复核 | 下一步：继续看主线、计划与风险。"
            if symbol
            else "推荐状态：已从复盘切回机会池 | 当前结论：继续复核 | 下一步：继续看主线、计划与风险。"
        )
        self._emit_action_feedback_v11("机会池", detail, recommend_text=recommend_text)

    def _open_detail_to_scanner_v11(self) -> None:
        original_open_detail_to_scanner_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        scan_text = (
            f"扫描状态：已从复盘同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 当前结论：继续复核 | 下一步：继续看盘中监控与观察池。"
            if symbol
            else "扫描状态：已从复盘切回信号扫描 | 当前结论：继续复核 | 下一步：继续看盘中监控与观察池。"
        )
        self._emit_action_feedback_v11("信号扫描", "复盘 -> 信号扫描", scan_text=scan_text)

    def _open_detail_to_broker_v11(self) -> None:
        original_open_detail_to_broker_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        broker_text = (
            f"交易状态：已从复盘同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 当前结论：继续复核 | 下一步：先复核委托链路与风险灯。"
            if symbol
            else "交易状态：已从复盘切到执行中控 | 当前结论：继续复核 | 下一步：优先核对当前委托链路。"
        )
        self._emit_action_feedback_v11("执行中控", "复盘 -> 执行中控", broker_text=broker_text)

    def _open_broker_focus_recommend_v11(self) -> None:
        original_open_broker_focus_recommend_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        recommend_text = (
            f"推荐状态：已从执行中控回看 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 当前结论：继续复核 | 下一步：继续看主线与送审理由。"
            if symbol
            else "推荐状态：已从执行中控回到机会池 | 当前结论：继续复核 | 下一步：继续看主线与送审理由。"
        )
        self._emit_action_feedback_v11("机会池", "执行中控 -> 机会池", recommend_text=recommend_text)

    def _open_broker_focus_orders_v11(self) -> None:
        original_open_broker_focus_orders_v11(self)
        self._emit_action_feedback_v11(
            "委托区",
            "执行中控定位到委托建议",
            broker_text="交易状态：已定位到委托建议区 | 当前结论：继续复核 | 下一步：优先核对价格、数量、主线闸门与原因摘要。",
        )

    def _open_broker_focus_execution_v11(self) -> None:
        original_open_broker_focus_execution_v11(self)
        self._emit_action_feedback_v11(
            "成交区",
            "执行中控定位到提交记录",
            broker_text="交易状态：已定位到提交记录区 | 当前结论：继续复核 | 下一步：继续看回执、成交状态与执行偏差。",
        )

    def _open_runtime_to_overview_v11(self) -> None:
        original_open_runtime_to_overview_v11(self)
        self._emit_action_feedback_v11(
            "市场总览",
            "运行页 -> 市场总览",
            scan_text="扫描状态：已回到市场总览链路 | 当前结论：继续复核 | 下一步：继续刷新市场、扫描候选并建立跨页焦点。",
        )

    def _refresh_runtime_panel_v11(self) -> None:
        original_refresh_runtime_panel_v11(self)
        self._emit_action_feedback_v11("运行页", "已刷新运行诊断与状态摘要")

    def _export_runtime_log_v11(self) -> None:
        original_export_runtime_log_v11(self)
        self._emit_action_feedback_v11("运行页", "已导出运行日志，请继续看最新事件与异常记录")

    def _refresh_workspace_status_labels_v11(self) -> None:
        original_refresh_workspace_status_labels_v11(self)
        if hasattr(self, "_refresh_runtime_story_v10"):
            self._refresh_runtime_story_v10()

    window_cls._emit_action_feedback_v11 = _emit_action_feedback_v11
    window_cls.open_detail_to_recommend = _open_detail_to_recommend_v11
    window_cls.open_detail_to_scanner = _open_detail_to_scanner_v11
    window_cls.open_detail_to_broker = _open_detail_to_broker_v11
    window_cls.open_broker_focus_recommend = _open_broker_focus_recommend_v11
    window_cls.open_broker_focus_orders = _open_broker_focus_orders_v11
    window_cls.open_broker_focus_execution = _open_broker_focus_execution_v11
    window_cls.open_runtime_to_overview = _open_runtime_to_overview_v11
    window_cls.refresh_runtime_panel = _refresh_runtime_panel_v11
    window_cls.export_runtime_log = _export_runtime_log_v11
    window_cls._refresh_workspace_status_labels = _refresh_workspace_status_labels_v11

    original_load_sample_universe_v12 = window_cls.load_sample_universe
    original_rescan_universe_v12 = window_cls.rescan_universe
    original_refresh_remote_market_v12 = window_cls.refresh_remote_market
    original_refresh_daily_pool_v12 = window_cls.refresh_daily_pool
    original_generate_order_suggestions_v12 = window_cls.generate_order_suggestions
    original_load_sample_reference_data_v12 = window_cls.load_sample_reference_data

    def _sync_pipeline_panels_v12(self) -> None:
        scan_count = len(getattr(self, "scan_rows", []) or [])
        recommend_count = len(getattr(self, "daily_pool_rows", []) or [])
        order_count = len(getattr(self, "order_intents", []) or [])
        runtime_count = len(getattr(self, "order_submission_records", []) or [])

        if hasattr(self, "scanner_live_summary_headline"):
            self.scanner_live_summary_headline.setText("扫描态势")
        if hasattr(self, "scanner_live_summary_detail"):
            self.scanner_live_summary_detail.setText(f"已扫描 {scan_count} 只候选，观察池与监控链路{'已建立' if scan_count else '等待建立'}。")
        if hasattr(self, "scanner_live_summary_meta"):
            self.scanner_live_summary_meta.setText("下一步：进入机会池继续看主线和位置。" if scan_count else "下一步：先刷新市场或载入样例数据。")

        if hasattr(self, "recommend_live_summary_headline"):
            self.recommend_live_summary_headline.setText("推荐态势")
        if hasattr(self, "recommend_live_summary_detail"):
            self.recommend_live_summary_detail.setText(f"已生成 {recommend_count} 只机会候选，{'可继续送审' if recommend_count else '等待机会池建立'}。")
        if hasattr(self, "recommend_live_summary_meta"):
            self.recommend_live_summary_meta.setText("下一步：先看前排和风险，再生成委托链路。" if recommend_count else "下一步：先刷新市场，再重算机会池。")

        if hasattr(self, "broker_live_summary_headline"):
            self.broker_live_summary_headline.setText("交易态势")
        if hasattr(self, "broker_live_summary_detail"):
            self.broker_live_summary_detail.setText(f"委托建议 {order_count} 笔，提交记录 {runtime_count} 笔 | 审查 继续复核。")
        if hasattr(self, "broker_live_summary_meta"):
            self.broker_live_summary_meta.setText(
                "当前结论：继续复核 | 下一步：复核委托后再进确认弹窗提交。"
                if order_count
                else "当前结论：继续复核 | 下一步：先从机会池生成委托链路。"
            )

    def _load_sample_universe_v12(self) -> None:
        self._emit_action_feedback_v11(
            "扫描页",
            "准备载入样例市场数据",
            recommend_text="推荐状态：载入中 | 样例市场与机会池待建立 | 当前结论：继续复核 | 下一步：等待样例数据接入。",
            scan_text="扫描状态：载入中 | 示例数据、观察池与监控待建立 | 当前结论：继续复核 | 下一步：等待扫描结果写回。",
        )
        original_load_sample_universe_v12(self)
        self._sync_pipeline_panels_v12()

    def _rescan_universe_v12(self) -> None:
        self._emit_action_feedback_v11(
            "扫描页",
            "开始重新扫描市场与观察池",
            recommend_text="推荐状态：等待回流 | 新扫描结果待写回 | 当前结论：继续复核 | 下一步：稍后自动刷新机会池。",
            scan_text="扫描状态：重扫中 | 市场、观察池与盘中监控待更新 | 当前结论：继续复核 | 下一步：等待扫描结果写回。",
        )
        original_rescan_universe_v12(self)
        self._sync_pipeline_panels_v12()

    def _refresh_remote_market_v12(self, quiet: bool = False, update_chart: bool = False, async_mode: bool = True) -> None:
        self._emit_action_feedback_v11(
            "市场总览",
            "开始刷新市场快照",
            recommend_text="推荐状态：等待市场快照 | 机会池待重算 | 当前结论：继续复核 | 下一步：稍后自动重算机会池。",
            scan_text="扫描状态：刷新中 | 市场快照与盘中候选待同步 | 当前结论：继续复核 | 下一步：等待快照写回。",
        )
        original_refresh_remote_market_v12(self, quiet=quiet, update_chart=update_chart, async_mode=async_mode)
        self._sync_pipeline_panels_v12()

    def _refresh_daily_pool_v12(self, async_mode: bool = True) -> None:
        self._emit_action_feedback_v11(
            "机会池",
            "开始重算每日机会池",
            recommend_text="推荐状态：重算中 | 主线、位置、消息与风险待回写 | 当前结论：继续复核 | 下一步：等待机会池生成。",
        )
        original_refresh_daily_pool_v12(self, async_mode=async_mode)
        if getattr(self, "daily_pool_rows", None):
            top = self.daily_pool_rows[0]
            self._emit_action_feedback_v11(
                "机会池",
                f"机会池已更新，共 {len(self.daily_pool_rows)} 只候选",
                recommend_text=f"推荐状态：已生成 {len(self.daily_pool_rows)} 只候选 | 当前前排 {top.stock_name} | 当前结论：继续复核 | 下一步：先继续看，再决定是否送审。",
            )
        self._sync_pipeline_panels_v12()

    def _generate_order_suggestions_v12(self) -> None:
        self._emit_action_feedback_v11(
            "执行中控",
            "开始生成委托链路",
            broker_text="交易状态：继续复核 | 正在生成委托建议 | 下一步：等待价格、数量和风险灯计算完成。",
        )
        original_generate_order_suggestions_v12(self)
        if getattr(self, "order_intents", None):
            top = self.order_intents[0]
            self._emit_action_feedback_v11(
                "执行中控",
                f"委托链路已更新，共 {len(self.order_intents)} 笔建议",
                broker_text=f"交易状态：已生成 {len(self.order_intents)} 笔委托建议 | 当前结论：继续复核 | 优先复核 {self._stock_name_for_symbol(top.symbol)} 的执行链路。",
            )
        else:
            self._emit_action_feedback_v11(
                "执行中控",
                "当前参数下未生成新的委托建议",
                broker_text="交易状态：当前参数下暂无新的委托建议 | 当前结论：继续复核 | 下一步：请先回看机会池、预算和主线状态。",
            )
        self._sync_pipeline_panels_v12()

    def _load_sample_reference_data_v12(self) -> None:
        self._emit_action_feedback_v11(
            "机会池",
            "开始载入示例资料",
            recommend_text="推荐状态：载入中 | 股票资料、消息面和题材词典待接入 | 当前结论：继续复核 | 下一步：等待资料写回。",
        )
        original_load_sample_reference_data_v12(self)
        loaded_profiles = len(getattr(self, "stock_profiles", {}) or {})
        loaded_rows = len(getattr(self, "daily_pool_rows", []) or [])
        recommend_text = f"推荐状态：样例资料已接入 | 当前生成 {loaded_rows} 只候选 | 当前结论：继续复核 | 下一步：可继续重算计划或进入执行中控。"
        status_builder = getattr(self, "_sample_reference_status_text_v1", None)
        if callable(status_builder):
            loaded_parts: list[str] = []
            if loaded_profiles:
                loaded_parts.append(f"股票资料 {loaded_profiles} 条")
            if getattr(self, "news_catalysts", None):
                provider_label = "示例消息源"
                resolve_label = getattr(self, "resolve_news_source_label", None)
                if callable(resolve_label):
                    provider_label = str(resolve_label("sample") or provider_label)
                loaded_parts.append(f"消息源 {provider_label}")
            theme_aliases = getattr(self, "theme_aliases", {}) or {}
            if theme_aliases:
                loaded_parts.append(f"题材词典 {len(theme_aliases)} 个主题")
            try:
                recommend_text = status_builder(loaded_parts=loaded_parts, scan_ready=bool(loaded_rows))
            except Exception:
                pass
        self._emit_action_feedback_v11(
            "机会池",
            f"示例资料已载入，股票资料 {loaded_profiles} 条",
            recommend_text=recommend_text,
            scan_text="扫描状态：样例资料已接入 | 当前结论：继续复核 | 下一步：继续看观察池与盘中监控。",
        )
        self._sync_pipeline_panels_v12()

    window_cls._sync_pipeline_panels_v12 = _sync_pipeline_panels_v12
    window_cls.load_sample_universe = _load_sample_universe_v12
    window_cls.rescan_universe = _rescan_universe_v12
    window_cls.refresh_remote_market = _refresh_remote_market_v12
    window_cls.refresh_daily_pool = _refresh_daily_pool_v12
    window_cls.generate_order_suggestions = _generate_order_suggestions_v12
    window_cls.load_sample_reference_data = _load_sample_reference_data_v12

    original_post_build_ui_tweaks_v14 = window_cls._post_build_ui_tweaks
    original_refresh_live_workspace_summary_panels_v15 = window_cls._refresh_live_workspace_summary_panels
    original_focus_symbol_in_recommend_workspace_v16 = window_cls._focus_symbol_in_recommend_workspace
    original_focus_symbol_in_broker_workspace_v16 = window_cls._focus_symbol_in_broker_workspace

    def _inject_recommend_broker_summary_panels_v13(self) -> None:
        panel_specs = [
            ("recommend_tab", "recommendLiveSummaryPanel", "推荐态势", "recommend_live_summary"),
            ("broker_tab", "brokerLiveSummaryPanel", "交易态势", "broker_live_summary"),
        ]
        for tab_name, object_name, title, prefix in panel_specs:
            tab = getattr(self, tab_name, None)
            if not isinstance(tab, QWidget) or getattr(self, f"{prefix}_headline", None) is not None:
                continue
            tool_panel = tab.findChild(QGroupBox, "workspaceToolPanel")
            if tool_panel is None:
                continue
            layout = tool_panel.layout()
            if not isinstance(layout, (QGridLayout, QHBoxLayout, QVBoxLayout)):
                continue
            panel, headline, detail, meta = self._build_workspace_summary_panel(object_name, title)
            if isinstance(layout, QGridLayout):
                layout.addWidget(panel, 1, 1)
            else:
                layout.addWidget(panel)
            setattr(self, f"{prefix}_headline", headline)
            setattr(self, f"{prefix}_detail", detail)
            setattr(self, f"{prefix}_meta", meta)

    def _upgrade_recommend_and_broker_empty_states_v13(self) -> None:
        text_defaults = {
            key: workbench_empty_panel_copy(key)
            for key in (
                "recommend_core_bucket_text",
                "recommend_watch_bucket_text",
                "recommend_risk_bucket_text",
                "broker_mainline_review_text",
                "broker_execution_text",
                "broker_recap_text",
                "order_result_text",
            )
        }
        for attr_name, text in text_defaults.items():
            widget = getattr(self, attr_name, None)
            if isinstance(widget, QTextEdit):
                current = widget.toPlainText().strip()
                if not current or len(current) < 90:
                    self._set_plain_text_if_changed(widget, text)

    def _post_build_ui_tweaks_v14(self) -> None:
        original_post_build_ui_tweaks_v14(self)
        self._inject_recommend_broker_summary_panels_v13()
        self._upgrade_recommend_and_broker_empty_states_v13()
        self._sync_pipeline_panels_v12()
        self._refresh_live_workspace_summary_panels()

    def _refresh_live_workspace_summary_panels_v15(self) -> None:
        original_refresh_live_workspace_summary_panels_v15(self)

        recommend_count = len(getattr(self, "daily_pool_rows", []) or [])
        plan = getattr(self, "current_trade_plan", None)
        decisions = list(getattr(plan, "decisions", []) or [])
        buy_count = sum(1 for item in decisions if str(getattr(item, "action", "") or "").upper() == "BUY")
        watch_count = sum(1 for item in getattr(self, "daily_pool_rows", []) if str(getattr(item, "action", "") or "").upper() == "WATCH")
        top = getattr(self, "daily_pool_rows", [None])[0] if recommend_count else None

        if hasattr(self, "recommend_live_summary_headline"):
            self._set_label_text_if_changed(self.recommend_live_summary_headline, f"候选 {recommend_count} / 买入 {buy_count} / 观察 {watch_count}")
        if hasattr(self, "recommend_live_summary_detail"):
            if top is not None:
                detail = (
                    f"前排焦点：{getattr(top, 'stock_name', '待确认')} | "
                    f"{getattr(top, 'mainline_tag', '') or getattr(top, 'theme_name', '') or '待确认'} | "
                    f"动作 {self._display_action(getattr(top, 'action', 'WATCH'))}"
                )
            else:
                detail = "等待机会池建立，先刷新市场、导入样例或重算推荐候选。"
            self._set_label_text_if_changed(self.recommend_live_summary_detail, detail)
        if hasattr(self, "recommend_live_summary_meta"):
            meta = (
                f"下一步：先看 {getattr(top, 'stock_name', '前排候选')} 的主线、买点和风险，再决定是否生成委托链路。"
                if top is not None
                else "下一步：先刷新市场，再重算机会池。"
            )
            self._set_label_text_if_changed(self.recommend_live_summary_meta, meta)

        order_count = len(getattr(self, "order_intents", []) or [])
        submit_count = len(getattr(self, "order_submission_records", []) or [])
        selected_intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
        latest_record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
        if latest_record is None:
            records = list(getattr(self, "order_submission_records", []) or [])
            latest_record = records[-1] if records else None

        if hasattr(self, "broker_live_summary_headline"):
            self._set_label_text_if_changed(self.broker_live_summary_headline, f"委托 {order_count} / 提交 {submit_count}")
        if hasattr(self, "broker_live_summary_detail"):
            if selected_intent is not None:
                detail = (
                    f"当前委托：{self._stock_name_for_symbol(getattr(selected_intent, 'symbol', '') or '')} | "
                    f"{self._display_action(getattr(selected_intent, 'side', ''))} | "
                    f"数量 {int(getattr(selected_intent, 'quantity', 0) or 0)} | 审查 继续复核"
                )
            elif latest_record is not None:
                detail = (
                    f"最近回执：{self._stock_name_for_symbol(str(latest_record.get('symbol', '') or ''))} | "
                    f"{self._display_order_status(latest_record.get('order_status', ''))} / "
                    f"{self._display_fill_status(latest_record.get('fill_status', ''))} | 审查 继续复核"
                )
            else:
                detail = "等待委托链路建立，先从机会池生成可执行建议。 | 审查 继续复核"
            self._set_label_text_if_changed(self.broker_live_summary_detail, detail)
        if hasattr(self, "broker_live_summary_meta"):
            meta = (
                "当前结论：继续复核 | 下一步：复核价格、仓位、主线闸门和风险灯后，再进确认弹窗。"
                if order_count
                else "当前结论：继续复核 | 下一步：先从机会池生成委托链路。"
            )
            self._set_label_text_if_changed(self.broker_live_summary_meta, meta)

    def _refresh_live_workspace_summary_panels_v16(self) -> None:
        _refresh_live_workspace_summary_panels_v15(self)

        current_recommend = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
        active_symbol = getattr(self, "active_symbol", "") or ""
        selected_intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
        latest_record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
        if latest_record is None:
            records = list(getattr(self, "order_submission_records", []) or [])
            latest_record = records[-1] if records else None
        fallback_scan_row = None
        if active_symbol:
            fallback_scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == active_symbol), None)
        if fallback_scan_row is None:
            fallback_scan_row = (getattr(self, "scan_rows", []) or [None])[0]
        summary_signature = (
            getattr(current_recommend, "symbol", "") if current_recommend is not None else "",
            getattr(current_recommend, "mainline_tag", "") if current_recommend is not None else "",
            getattr(current_recommend, "mainline_risk_flag", "") if current_recommend is not None else "",
            getattr(current_recommend, "next_focus", "") if current_recommend is not None else "",
            getattr(fallback_scan_row, "symbol", "") if fallback_scan_row is not None else "",
            getattr(fallback_scan_row, "score", 0) if fallback_scan_row is not None else 0,
            getattr(fallback_scan_row, "action", "") if fallback_scan_row is not None else "",
            getattr(fallback_scan_row, "label", "") if fallback_scan_row is not None else "",
            getattr(selected_intent, "symbol", "") if selected_intent is not None else "",
            getattr(selected_intent, "price", 0.0) if selected_intent is not None else 0.0,
            getattr(selected_intent, "quantity", 0) if selected_intent is not None else 0,
            str(latest_record.get("symbol", "") if latest_record is not None else ""),
            str(latest_record.get("order_status", "") if latest_record is not None else ""),
            str(latest_record.get("fill_status", "") if latest_record is not None else ""),
            str(latest_record.get("message", "") if latest_record is not None else ""),
            active_symbol,
        )
        if getattr(self, "_live_workspace_summary_signature_v16", None) == summary_signature:
            return
        self._live_workspace_summary_signature_v16 = summary_signature
        if current_recommend is not None:
            stock_name = getattr(current_recommend, "stock_name", "") or self._stock_name_for_symbol(getattr(current_recommend, "symbol", "") or "")
            stock_id = getattr(current_recommend, "stock_id", "") or self._stock_id_for_symbol(getattr(current_recommend, "symbol", "") or "")
            signal = mainline_signal_brief_fn(current_recommend)
            action_text = signal_action_text_fn(current_recommend)
            theme_name = getattr(current_recommend, "mainline_tag", "") or getattr(current_recommend, "theme_name", "") or "待确认"
            risk_flag = getattr(current_recommend, "mainline_risk_flag", "") or "待评估"
            next_focus = getattr(current_recommend, "next_focus", "") or "继续看主线、位置和催化。"
            if hasattr(self, "recommend_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.recommend_live_summary_detail,
                    f"焦点：{stock_name} ({stock_id} / {getattr(current_recommend, 'symbol', '')}) | {theme_name} | {action_text} / {signal}",
                )
            if hasattr(self, "recommend_live_summary_meta"):
                self._set_label_text_if_changed(self.recommend_live_summary_meta, f"下一步：风险 {risk_flag} | {next_focus[:28]}")
        elif fallback_scan_row is not None:
            symbol = getattr(fallback_scan_row, "symbol", "") or ""
            stock_name = self._stock_name_for_symbol(symbol)
            stock_id = self._stock_id_for_symbol(symbol)
            if hasattr(self, "recommend_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.recommend_live_summary_detail,
                    f"扫描焦点：{stock_name} ({stock_id} / {symbol}) | {self._display_action(getattr(fallback_scan_row, 'action', 'WATCH'))} / {self._display_label(getattr(fallback_scan_row, 'label', 'WATCH'))}",
                )
            if hasattr(self, "recommend_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.recommend_live_summary_meta,
                    f"下一步：先把扫描候选转成机会池，再核对评分 {getattr(fallback_scan_row, 'score', '--')} 与主线位置。",
                )

        if selected_intent is not None:
            symbol = getattr(selected_intent, "symbol", "") or ""
            stock_name = self._stock_name_for_symbol(symbol)
            recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == symbol), None)
            signal = mainline_signal_brief_fn(recommendation)
            risk_lamp = self._broker_risk_lamp_for_intent(selected_intent, recommendation=recommendation) if hasattr(self, "_broker_risk_lamp_for_intent") else "黄灯"
            if hasattr(self, "broker_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_detail,
                    f"焦点委托：{stock_name} ({self._stock_id_for_symbol(symbol)} / {symbol}) | {self._display_action(getattr(selected_intent, 'side', ''))} | 主线 {signal}",
                )
            if hasattr(self, "broker_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_meta,
                    f"下一步：风险灯 {risk_lamp} | 价格 {float(getattr(selected_intent, 'price', 0.0) or 0.0):.2f} | 数量 {int(getattr(selected_intent, 'quantity', 0) or 0)}",
                )
        elif latest_record is not None:
            symbol = str(latest_record.get("symbol", "") or "")
            stock_name = self._stock_name_for_symbol(symbol) if hasattr(self, "_stock_name_for_symbol") else symbol
            if hasattr(self, "broker_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_detail,
                    f"最近回执：{stock_name} ({self._stock_id_for_symbol(symbol) if hasattr(self, '_stock_id_for_symbol') else symbol} / {symbol}) | {self._display_order_status(latest_record.get('order_status', ''))} / {self._display_fill_status(latest_record.get('fill_status', ''))}",
                )
            if hasattr(self, "broker_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_meta,
                    f"下一步：{str(latest_record.get('message', '') or '继续跟踪回执与成交偏差')[:34]}",
                )
        elif fallback_scan_row is not None:
            symbol = getattr(fallback_scan_row, "symbol", "") or ""
            stock_name = self._stock_name_for_symbol(symbol) if hasattr(self, "_stock_name_for_symbol") else symbol
            if hasattr(self, "broker_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_detail,
                    f"待生成委托：{stock_name} ({self._stock_id_for_symbol(symbol) if hasattr(self, '_stock_id_for_symbol') else symbol} / {symbol}) | 扫描评分 {getattr(fallback_scan_row, 'score', '--')} | {self._display_action(getattr(fallback_scan_row, 'action', 'WATCH'))}",
                )
            if hasattr(self, "broker_live_summary_meta"):
                self._set_label_text_if_changed(self.broker_live_summary_meta, "下一步：先生成委托链路，再复核价格、仓位、主线闸门与风险灯。")

        detail_symbol = getattr(self, "active_symbol", "") or ""
        if detail_symbol and hasattr(self, "detail_live_summary_headline"):
            stock_name = self._stock_name_for_symbol(detail_symbol) if hasattr(self, "_stock_name_for_symbol") else detail_symbol
            stock_id = self._stock_id_for_symbol(detail_symbol) if hasattr(self, "_stock_id_for_symbol") else detail_symbol
            recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == detail_symbol), None)
            latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if getattr(item, "label", "") != "NONE"), None)
            action_text = self._display_action(getattr(recommendation, "action", "WATCH")) if recommendation is not None else "观察"
            theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
            self._set_label_text_if_changed(self.detail_live_summary_headline, f"复盘焦点：{stock_name} ({stock_id}) | 审查 继续复核")
            if hasattr(self, "detail_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_detail,
                    f"主线 {theme_name} | 动作 {action_text} | 最新信号 {self._display_label(getattr(latest_signal, 'label', '')) if latest_signal is not None else '等待信号同步'}",
                )
            if hasattr(self, "detail_live_summary_meta"):
                self._set_label_text_if_changed(self.detail_live_summary_meta, "下一步：优先回看执行纪律、买卖节奏和是否仍值得继续跟踪。")
        elif hasattr(self, "detail_live_summary_headline"):
            self._set_label_text_if_changed(self.detail_live_summary_headline, "复盘焦点：等待联动 | 审查 继续复核")
            if hasattr(self, "detail_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_detail,
                    "等待从机会池、扫描页或执行中控同步一只股票，再展开信号、成交与复盘结论。",
                )
            if hasattr(self, "detail_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_meta,
                    "下一步：先在机会池、扫描页或执行中控选中一只票，再进入复盘研究。",
                )

    def _focus_symbol_in_recommend_workspace_v16(self, symbol: str) -> None:
        original_focus_symbol_in_recommend_workspace_v16(self, symbol)
        self._refresh_live_workspace_summary_panels()
        if hasattr(self, "_refresh_workspace_focus_banners"):
            self._refresh_workspace_focus_banners()

    def _focus_symbol_in_broker_workspace_v16(self, symbol: str) -> None:
        original_focus_symbol_in_broker_workspace_v16(self, symbol)
        self._refresh_live_workspace_summary_panels()
        if hasattr(self, "_refresh_workspace_focus_banners"):
            self._refresh_workspace_focus_banners()

    window_cls._inject_recommend_broker_summary_panels_v13 = _inject_recommend_broker_summary_panels_v13
    window_cls._upgrade_recommend_and_broker_empty_states_v13 = _upgrade_recommend_and_broker_empty_states_v13
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v14
    window_cls._refresh_live_workspace_summary_panels = _refresh_live_workspace_summary_panels_v16
    window_cls._focus_symbol_in_recommend_workspace = _focus_symbol_in_recommend_workspace_v16
    window_cls._focus_symbol_in_broker_workspace = _focus_symbol_in_broker_workspace_v16
    window_cls._qh_runtime_feedback_patches_applied_v16 = True
