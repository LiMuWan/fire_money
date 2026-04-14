from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QTextEdit, QVBoxLayout, QWidget


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
        detail = f"复盘页 -> 机会池 | {self._stock_name_for_symbol(symbol)}" if symbol else "复盘页 -> 机会池"
        recommend_text = (
            f"推荐状态：已从复盘页同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)})，继续核对主线、计划与风险。"
            if symbol
            else "推荐状态：已从复盘页切回机会池，继续核对主线、计划与风险。"
        )
        self._emit_action_feedback_v11("机会池", detail, recommend_text=recommend_text)

    def _open_detail_to_scanner_v11(self) -> None:
        original_open_detail_to_scanner_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        scan_text = (
            f"扫描状态：已从复盘页同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)})，继续查看盘中监控与观察池。"
            if symbol
            else "扫描状态：已从复盘页切回扫描页，继续查看盘中监控与观察池。"
        )
        self._emit_action_feedback_v11("扫描页", "复盘页 -> 扫描页", scan_text=scan_text)

    def _open_detail_to_broker_v11(self) -> None:
        original_open_detail_to_broker_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        broker_text = (
            f"交易台：已从复盘页同步 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)}) | 请先复核委托链路与风险灯。"
            if symbol
            else "交易台：已从复盘页切到交易执行页 | 请优先核对当前委托链路。"
        )
        self._emit_action_feedback_v11("交易页", "复盘页 -> 交易执行", broker_text=broker_text)

    def _open_broker_focus_recommend_v11(self) -> None:
        original_open_broker_focus_recommend_v11(self)
        symbol = getattr(self, "active_symbol", "") or ""
        recommend_text = (
            f"推荐状态：已从交易页回看 {self._stock_name_for_symbol(symbol)} ({self._stock_id_for_symbol(symbol)})，继续复核主线与送审理由。"
            if symbol
            else "推荐状态：已从交易页回到机会池，继续复核主线与送审理由。"
        )
        self._emit_action_feedback_v11("机会池", "交易页 -> 机会池", recommend_text=recommend_text)

    def _open_broker_focus_orders_v11(self) -> None:
        original_open_broker_focus_orders_v11(self)
        self._emit_action_feedback_v11(
            "委托区",
            "交易页定位到委托建议",
            broker_text="交易台：已定位到委托建议区，请优先核对价格、数量、主线闸门与原因摘要。",
        )

    def _open_broker_focus_execution_v11(self) -> None:
        original_open_broker_focus_execution_v11(self)
        self._emit_action_feedback_v11(
            "成交区",
            "交易页定位到提交记录",
            broker_text="交易台：已定位到提交记录区，请继续核对回执、成交状态与执行偏差。",
        )

    def _open_runtime_to_overview_v11(self) -> None:
        original_open_runtime_to_overview_v11(self)
        self._emit_action_feedback_v11(
            "市场总览",
            "运行页 -> 市场总览",
            scan_text="扫描状态：已回到市场总览链路，可继续刷新市场、扫描候选并建立跨页焦点。",
        )

    def _refresh_runtime_panel_v11(self) -> None:
        original_refresh_runtime_panel_v11(self)
        self._emit_action_feedback_v11("运行页", "已刷新运行诊断与状态摘要")

    def _export_runtime_log_v11(self) -> None:
        original_export_runtime_log_v11(self)
        self._emit_action_feedback_v11("运行页", "已导出运行日志，请继续核对最新事件与异常记录")

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
            self.broker_live_summary_detail.setText(f"委托建议 {order_count} 笔，提交记录 {runtime_count} 笔。")
        if hasattr(self, "broker_live_summary_meta"):
            self.broker_live_summary_meta.setText("下一步：复核委托后再确认提交。" if order_count else "下一步：先从机会池生成委托链路。")

    def _load_sample_universe_v12(self) -> None:
        self._emit_action_feedback_v11(
            "扫描页",
            "准备载入样例市场数据",
            recommend_text="推荐状态：正在准备样例市场与机会池数据。",
            scan_text="扫描状态：正在载入示例数据并建立观察池、监控与联动焦点。",
        )
        original_load_sample_universe_v12(self)
        self._sync_pipeline_panels_v12()

    def _rescan_universe_v12(self) -> None:
        self._emit_action_feedback_v11(
            "扫描页",
            "开始重新扫描市场与观察池",
            recommend_text="推荐状态：正在等待扫描结果回流，稍后自动刷新机会池。",
            scan_text="扫描状态：正在重新扫描市场、观察池与盘中监控。",
        )
        original_rescan_universe_v12(self)
        self._sync_pipeline_panels_v12()

    def _refresh_remote_market_v12(self, quiet: bool = False, update_chart: bool = False, async_mode: bool = True) -> None:
        self._emit_action_feedback_v11(
            "市场总览",
            "开始刷新市场快照",
            recommend_text="推荐状态：正在等待市场快照刷新，稍后自动重算机会池。",
            scan_text="扫描状态：正在同步市场快照与盘中候选。",
        )
        original_refresh_remote_market_v12(self, quiet=quiet, update_chart=update_chart, async_mode=async_mode)
        self._sync_pipeline_panels_v12()

    def _refresh_daily_pool_v12(self, async_mode: bool = True) -> None:
        self._emit_action_feedback_v11(
            "机会池",
            "开始重算每日机会池",
            recommend_text="推荐状态：正在根据主线、位置、消息与风险重算机会池。",
        )
        original_refresh_daily_pool_v12(self, async_mode=async_mode)
        if getattr(self, "daily_pool_rows", None):
            top = self.daily_pool_rows[0]
            self._emit_action_feedback_v11(
                "机会池",
                f"机会池已更新，共 {len(self.daily_pool_rows)} 只候选",
                recommend_text=f"推荐状态：已生成 {len(self.daily_pool_rows)} 只候选，当前前排 {top.stock_name}，可继续核对后送审。",
            )
        self._sync_pipeline_panels_v12()

    def _generate_order_suggestions_v12(self) -> None:
        self._emit_action_feedback_v11(
            "交易页",
            "开始生成委托链路",
            broker_text="交易台：正在生成委托建议，请等待价格、数量和风险灯计算完成。",
        )
        original_generate_order_suggestions_v12(self)
        if getattr(self, "order_intents", None):
            top = self.order_intents[0]
            self._emit_action_feedback_v11(
                "交易页",
                f"委托链路已更新，共 {len(self.order_intents)} 笔建议",
                broker_text=f"交易台：已生成 {len(self.order_intents)} 笔委托建议，优先复核 {self._stock_name_for_symbol(top.symbol)} 的执行链路。",
            )
        else:
            self._emit_action_feedback_v11(
                "交易页",
                "当前参数下未生成新的委托建议",
                broker_text="交易台：当前参数下暂无新的委托建议，请先回看机会池、预算和主线状态。",
            )
        self._sync_pipeline_panels_v12()

    def _load_sample_reference_data_v12(self) -> None:
        self._emit_action_feedback_v11(
            "机会池",
            "开始载入示例资料",
            recommend_text="推荐状态：正在载入股票资料、消息面和题材词典。",
        )
        original_load_sample_reference_data_v12(self)
        loaded_profiles = len(getattr(self, "stock_profiles", {}) or {})
        loaded_rows = len(getattr(self, "daily_pool_rows", []) or [])
        self._emit_action_feedback_v11(
            "机会池",
            f"示例资料已载入，股票资料 {loaded_profiles} 条",
            recommend_text=f"推荐状态：样例资料已接入，当前生成 {loaded_rows} 只候选，可继续重算计划或进入交易执行。",
            scan_text="扫描状态：样例资料已接入，可继续查看观察池与盘中监控。",
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
            "recommend_core_bucket_text": (
                "主线前排执行桶\n\n"
                "结论：这里只保留最值得优先送审的前排候选，不把观察票和风险票混在一起。\n"
                "检查项：看主线地位、量能承接、催化是否强化，以及计划仓位是否还能承载。\n"
                "下一步：有前排机会时先重算计划，没有的话先回综合机会池继续筛。"
            ),
            "recommend_watch_bucket_text": (
                "观察池\n\n"
                "结论：这里放延续待确认、需要二次确认或只适合盯盘的标的。\n"
                "检查项：优先看分时承接、主线强度、消息兑现和是否重新回到前排。\n"
                "下一步：一旦条件转强，就转入前排执行桶；若逻辑失效，就转风险池。"
            ),
            "recommend_risk_bucket_text": (
                "风险池\n\n"
                "结论：这里集中展示减仓、卖出、回避和逻辑失效的标的，不让风险散落在别处。\n"
                "检查项：重点看主线切换、跌破防守位、量价背离和消息落空。\n"
                "下一步：优先处理风险，再决定是否回看机会池补新候选。"
            ),
            "broker_mainline_review_text": (
                "主线闸门 / 为什么\n\n"
                "结论：这里先判断委托有没有站在主线前排、有没有硬阻塞，再决定能不能送审。\n"
                "检查项：优先核对题材位置、主线角色、风险灯和计划仓位是否匹配。\n"
                "下一步：主线成立再进入一键确认；主线不成立就回机会池重看。"
            ),
            "broker_execution_text": (
                "最近执行\n\n"
                "结论：这里沉淀当前委托、提交回执和执行链路，不需要来回切页看。\n"
                "检查项：重点看订单状态、成交状态、失败原因和是否偏离计划价格。\n"
                "下一步：若还未提交，先复核；若已提交，继续跟踪回执和成交偏差。"
            ),
            "broker_recap_text": (
                "成交回顾\n\n"
                "结论：这里复盘通过率、阻塞原因、成交偏差，以及主线是否还成立。\n"
                "检查项：优先看失败原因、滑点、仓位偏差和是否需要重新送审。\n"
                "下一步：执行合格就继续跟踪；执行失真就回头修正机会池和委托参数。"
            ),
            "order_result_text": (
                "执行回放\n\n"
                "结论：新的提交结果会按时间顺序沉淀在这里，包括订单状态、成交状态和系统反馈。\n"
                "检查项：先看最新一条记录，再回看是否存在重复失败或连续阻塞。\n"
                "下一步：确认提交后，这里会自动滚动到最新记录，便于盘中快速复核。"
            ),
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
                    f"数量 {int(getattr(selected_intent, 'quantity', 0) or 0)}"
                )
            elif latest_record is not None:
                detail = (
                    f"最近回执：{self._stock_name_for_symbol(str(latest_record.get('symbol', '') or ''))} | "
                    f"{self._display_order_status(latest_record.get('order_status', ''))} / "
                    f"{self._display_fill_status(latest_record.get('fill_status', ''))}"
                )
            else:
                detail = "等待委托链路建立，先从机会池生成可执行建议。"
            self._set_label_text_if_changed(self.broker_live_summary_detail, detail)
        if hasattr(self, "broker_live_summary_meta"):
            meta = "下一步：复核价格、仓位、主线闸门和风险灯后，再进入一键确认。" if order_count else "下一步：先从机会池生成委托链路。"
            self._set_label_text_if_changed(self.broker_live_summary_meta, meta)

    def _refresh_live_workspace_summary_panels_v16(self) -> None:
        _refresh_live_workspace_summary_panels_v15(self)

        current_recommend = self._selected_daily_pool_recommendation() if hasattr(self, "_selected_daily_pool_recommendation") else None
        active_symbol = getattr(self, "active_symbol", "") or ""
        fallback_scan_row = None
        if active_symbol:
            fallback_scan_row = next((row for row in getattr(self, "scan_rows", []) if getattr(row, "symbol", "") == active_symbol), None)
        if fallback_scan_row is None:
            fallback_scan_row = (getattr(self, "scan_rows", []) or [None])[0]
        if current_recommend is not None:
            stock_name = getattr(current_recommend, "stock_name", "") or self._stock_name_for_symbol(getattr(current_recommend, "symbol", "") or "")
            stock_id = getattr(current_recommend, "stock_id", "") or self._stock_id_for_symbol(getattr(current_recommend, "symbol", "") or "")
            signal = mainline_signal_brief_fn(current_recommend)
            action_text = signal_action_text_fn(current_recommend)
            theme_name = getattr(current_recommend, "mainline_tag", "") or getattr(current_recommend, "theme_name", "") or "待确认"
            risk_flag = getattr(current_recommend, "mainline_risk_flag", "") or "待评估"
            next_focus = getattr(current_recommend, "next_focus", "") or "继续核对主线、位置和催化。"
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

        selected_intent = self._selected_order_intent() if hasattr(self, "_selected_order_intent") else None
        latest_record = self._selected_submission_record() if hasattr(self, "_selected_submission_record") else None
        if latest_record is None:
            records = list(getattr(self, "order_submission_records", []) or [])
            latest_record = records[-1] if records else None

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
            stock_name = self._stock_name_for_symbol(symbol)
            if hasattr(self, "broker_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_detail,
                    f"最近回执：{stock_name} ({self._stock_id_for_symbol(symbol)} / {symbol}) | {self._display_order_status(latest_record.get('order_status', ''))} / {self._display_fill_status(latest_record.get('fill_status', ''))}",
                )
            if hasattr(self, "broker_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_meta,
                    f"下一步：{str(latest_record.get('message', '') or '继续跟踪回执与成交偏差')[:34]}",
                )
        elif fallback_scan_row is not None:
            symbol = getattr(fallback_scan_row, "symbol", "") or ""
            stock_name = self._stock_name_for_symbol(symbol)
            if hasattr(self, "broker_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.broker_live_summary_detail,
                    f"待生成委托：{stock_name} ({self._stock_id_for_symbol(symbol)} / {symbol}) | 扫描评分 {getattr(fallback_scan_row, 'score', '--')} | {self._display_action(getattr(fallback_scan_row, 'action', 'WATCH'))}",
                )
            if hasattr(self, "broker_live_summary_meta"):
                self._set_label_text_if_changed(self.broker_live_summary_meta, "下一步：先生成委托链路，再复核价格、仓位、主线闸门与风险灯。")

        detail_symbol = getattr(self, "active_symbol", "") or ""
        if detail_symbol and hasattr(self, "detail_live_summary_headline"):
            stock_name = self._stock_name_for_symbol(detail_symbol)
            stock_id = self._stock_id_for_symbol(detail_symbol)
            recommendation = next((item for item in getattr(self, "daily_pool_rows", []) if getattr(item, "symbol", "") == detail_symbol), None)
            latest_signal = next((item for item in reversed(getattr(self, "analyses", [])) if getattr(item, "label", "") != "NONE"), None)
            action_text = self._display_action(getattr(recommendation, "action", "WATCH")) if recommendation is not None else "观察"
            theme_name = getattr(recommendation, "mainline_tag", "") or getattr(recommendation, "theme_name", "") or "待确认"
            self._set_label_text_if_changed(self.detail_live_summary_headline, f"复盘焦点：{stock_name} ({stock_id})")
            if hasattr(self, "detail_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_detail,
                    f"主线 {theme_name} | 动作 {action_text} | 最新信号 {self._display_label(getattr(latest_signal, 'label', '')) if latest_signal is not None else '等待信号同步'}",
                )
            if hasattr(self, "detail_live_summary_meta"):
                self._set_label_text_if_changed(self.detail_live_summary_meta, "下一步：优先回看执行纪律、买卖节奏和是否仍值得继续跟踪。")
        elif hasattr(self, "detail_live_summary_headline"):
            self._set_label_text_if_changed(self.detail_live_summary_headline, "复盘焦点：等待联动")
            if hasattr(self, "detail_live_summary_detail"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_detail,
                    "等待从推荐页、扫描页或交易页同步一只股票，再展开信号、成交与复盘结论。",
                )
            if hasattr(self, "detail_live_summary_meta"):
                self._set_label_text_if_changed(
                    self.detail_live_summary_meta,
                    "下一步：先在机会池、扫描页或交易页选中一只票，再进入复盘研究。",
                )

    def _focus_symbol_in_recommend_workspace_v16(self, symbol: str) -> None:
        original_focus_symbol_in_recommend_workspace_v16(self, symbol)
        self._refresh_live_workspace_summary_panels()

    def _focus_symbol_in_broker_workspace_v16(self, symbol: str) -> None:
        original_focus_symbol_in_broker_workspace_v16(self, symbol)
        self._refresh_live_workspace_summary_panels()

    window_cls._inject_recommend_broker_summary_panels_v13 = _inject_recommend_broker_summary_panels_v13
    window_cls._upgrade_recommend_and_broker_empty_states_v13 = _upgrade_recommend_and_broker_empty_states_v13
    window_cls._post_build_ui_tweaks = _post_build_ui_tweaks_v14
    window_cls._refresh_live_workspace_summary_panels = _refresh_live_workspace_summary_panels_v16
    window_cls._focus_symbol_in_recommend_workspace = _focus_symbol_in_recommend_workspace_v16
    window_cls._focus_symbol_in_broker_workspace = _focus_symbol_in_broker_workspace_v16
    window_cls._qh_runtime_feedback_patches_applied_v16 = True
