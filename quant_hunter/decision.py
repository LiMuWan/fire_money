from __future__ import annotations

from dataclasses import dataclass, field

from .models import HoldingRecord, RecommendationRow
from .theme import infer_mainline_flow_signal, infer_mainline_stage


@dataclass(frozen=True)
class MarketPulse:
    sentiment_label: str
    sentiment_score: float
    market_regime: str
    risk_level: str
    max_total_exposure: float
    buy_ratio: float
    average_total_score: float
    strong_candidates: int
    caution_candidates: int
    mainline_flow_signal: str = ""
    mainline_flow_score: float = 0.0


@dataclass(frozen=True)
class TradeDecision:
    symbol: str
    stock_id: str
    stock_name: str
    action: str
    confidence: float
    planned_entry: float
    planned_stop: float
    planned_target: float
    suggested_budget: float
    rationale: str
    stock_pool: str = ""
    opportunity_tier: str = ""
    execution_readiness: float = 0.0
    setup_quality_score: float = 0.0
    risk_reward_ratio: float = 0.0
    signal_age_days: int = 0
    next_focus: str = ""
    mainline_flow_signal: str = ""
    mainline_stage: str = ""


@dataclass(frozen=True)
class PositionAdvice:
    symbol: str
    stock_id: str
    stock_name: str
    action: str
    confidence: float
    current_price: float
    cost_price: float
    pnl_pct: float
    rationale: str
    mainline_flow_signal: str = ""
    mainline_stage: str = ""


@dataclass(frozen=True)
class DailyTradePlan:
    market_pulse: MarketPulse
    max_new_positions: int
    decisions: list[TradeDecision] = field(default_factory=list)
    position_advice: list[PositionAdvice] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def market_sentiment(self) -> str:
        return self.market_pulse.sentiment_label

    @property
    def sentiment_score(self) -> float:
        return self.market_pulse.sentiment_score


class DecisionEngine:
    @staticmethod
    def _row_is_buy_allowed(row: RecommendationRow) -> bool:
        role = str(getattr(row, "mainline_role", "") or "")
        failure_risk = float(getattr(row, "theme_failure_risk", 0.0) or 0.0)
        window_score = float(getattr(row, "mainline_window_score", 0.0) or 0.0)
        reject_reason = str(getattr(row, "reject_reason", "") or "").strip()
        signal_source = str(getattr(row, "signal_source", "") or "").strip()
        signal_age_days = int(getattr(row, "signal_age_days", 0) or 0)
        risk_reward_ratio = float(getattr(row, "risk_reward_ratio", 0.0) or 0.0)
        rank = int(getattr(row, "mainline_rank", getattr(row, "theme_rank", 0)) or 0)
        has_mainline_signal = bool(role or failure_risk or window_score or rank)
        if reject_reason:
            return False
        if signal_source.startswith("synthetic://"):
            return False
        if signal_age_days >= 4:
            return False
        if risk_reward_ratio and risk_reward_ratio < 1.35:
            return False
        if not has_mainline_signal:
            return True
        if role in {"NOISE", "ELIMINATED"}:
            return False
        if failure_risk >= 72.0:
            return False
        if window_score and window_score < 48.0:
            return False
        return True

    @staticmethod
    def _row_mainline_flow_signal(row: RecommendationRow) -> str:
        return infer_mainline_flow_signal(
            int(getattr(row, "mainline_rank", getattr(row, "theme_rank", 0)) or 0),
            float(getattr(row, "mainline_strength_score", 0.0) or getattr(row, "theme_score", 0.0) or getattr(row, "total_score", 0.0) or 0.0),
            float(getattr(row, "mainline_continuation_score", 0.0) or 0.0),
            float(getattr(row, "theme_divergence_score", 0.0) or 0.0),
            float(getattr(row, "theme_failure_risk", 0.0) or 0.0),
            float(getattr(row, "mainline_window_score", 0.0) or 0.0),
            str(getattr(row, "mainline_role", "") or ""),
        )

    @staticmethod
    def _row_mainline_stage(row: RecommendationRow) -> str:
        return infer_mainline_stage(
            int(getattr(row, "mainline_rank", getattr(row, "theme_rank", 0)) or 0),
            float(getattr(row, "mainline_strength_score", 0.0) or getattr(row, "theme_score", 0.0) or getattr(row, "total_score", 0.0) or 0.0),
            float(getattr(row, "mainline_continuation_score", 0.0) or 0.0),
            float(getattr(row, "theme_divergence_score", 0.0) or 0.0),
            float(getattr(row, "theme_failure_risk", 0.0) or 0.0),
            float(getattr(row, "mainline_window_score", 0.0) or 0.0),
            str(getattr(row, "mainline_role", "") or ""),
        )

    @staticmethod
    def _mainline_role_label(role: str) -> str:
        return {
            "CORE": "核心龙头",
            "FRONT": "前排主线",
            "FOLLOW": "跟随补位",
            "NOISE": "噪声支线",
            "ELIMINATED": "主线淘汰",
        }.get(role, "主线观察")

    def build_plan(
        self,
        recommendations: list[RecommendationRow],
        holdings: list[HoldingRecord],
        available_cash: float,
        max_picks: int = 5,
        top_theme_limit: int = 3,
        max_total_exposure: float | None = None,
        theme_drop_reduce: bool = True,
    ) -> DailyTradePlan:
        pulse = self._market_pulse(recommendations)
        if max_total_exposure is not None:
            pulse = MarketPulse(
                sentiment_label=pulse.sentiment_label,
                sentiment_score=pulse.sentiment_score,
                market_regime=pulse.market_regime,
                risk_level=pulse.risk_level,
                max_total_exposure=max_total_exposure,
                buy_ratio=pulse.buy_ratio,
                average_total_score=pulse.average_total_score,
                strong_candidates=pulse.strong_candidates,
                caution_candidates=pulse.caution_candidates,
                mainline_flow_signal=pulse.mainline_flow_signal,
                mainline_flow_score=pulse.mainline_flow_score,
            )

        theme_leaders = [item for item in recommendations if item.theme_rank and item.theme_rank <= top_theme_limit]
        if pulse.sentiment_score >= 78:
            max_new_positions = min(max_picks, 5)
        elif pulse.sentiment_score >= 62:
            max_new_positions = min(max_picks, 3)
        else:
            max_new_positions = min(max_picks, 1)

        held_symbols = {item.symbol for item in holdings}
        buy_candidates = [
            row
            for row in recommendations
            if row.symbol not in held_symbols
            and row.action == "BUY"
            and (row.theme_rank == 0 or row.theme_rank <= top_theme_limit)
            and self._row_is_buy_allowed(row)
        ]
        buy_candidates.sort(
            key=lambda row: (
                float(getattr(row, "setup_quality_score", 0.0) or 0.0),
                float(getattr(row, "execution_readiness", 0.0) or 0.0),
                float(getattr(row, "risk_reward_ratio", 0.0) or 0.0),
                -int(getattr(row, "signal_age_days", 0) or 0),
                float(getattr(row, "dragon_decision_score", 0.0) or getattr(row, "total_score", 0.0) or 0.0),
            ),
            reverse=True,
        )
        buy_candidates = buy_candidates[:max_new_positions]
        holding_market_value = sum(
            float(getattr(item, "market_value", 0.0) or 0.0)
            if float(getattr(item, "market_value", 0.0) or 0.0) > 0
            else float(getattr(item, "cost_price", 0.0) or 0.0) * float(getattr(item, "quantity", 0) or 0.0)
            for item in holdings
        )
        total_equity = holding_market_value + max(available_cash, 0.0)
        remaining_exposure_budget = max(total_equity * pulse.max_total_exposure - holding_market_value, 0.0)
        deployable_budget = min(max(available_cash, 0.0), remaining_exposure_budget)
        budget_per_pick = deployable_budget / max(len(buy_candidates), 1) if deployable_budget > 0 else 0.0

        decisions: list[TradeDecision] = []
        remaining_budget = deployable_budget
        for row in buy_candidates:
            planned_entry = row.entry_price or row.close
            strategy_name = getattr(row, "primary_strategy", "") or "掘龙决策"
            stock_pool = getattr(row, "stock_pool", "")
            if strategy_name in {"打板策略", "擒龙打板"}:
                planned_stop = row.stop_price or planned_entry * 0.965
                planned_target = row.target_price or planned_entry * 1.13
            elif strategy_name == "尾盘买入法":
                planned_stop = row.stop_price or planned_entry * 0.976
                planned_target = row.target_price or planned_entry * 1.032
            elif strategy_name == "一日持股法":
                planned_stop = row.stop_price or planned_entry * 0.972
                planned_target = row.target_price or planned_entry * 1.055
            elif strategy_name == "价值低吸":
                planned_stop = row.stop_price or planned_entry * 0.945
                planned_target = row.target_price or planned_entry * 1.09
            else:
                planned_stop = row.stop_price or planned_entry * 0.95
                planned_target = row.target_price or planned_entry * 1.08

            budget_multiplier = 1.0
            if stock_pool == "龙头股":
                budget_multiplier = 1.08
            elif stock_pool == "价值股":
                budget_multiplier = 0.92
            elif strategy_name == "尾盘买入法":
                budget_multiplier = 0.82 if pulse.sentiment_score >= 72 else 0.72
            elif strategy_name == "一日持股法":
                budget_multiplier = 0.96 if pulse.sentiment_score >= 72 else 0.86

            confidence_source = getattr(row, "dragon_decision_score", 0.0) or row.total_score
            confidence = min(max(confidence_source / 100.0, 0.0), 0.99)
            flow_signal = self._row_mainline_flow_signal(row)
            stage_label = self._row_mainline_stage(row)
            mainline_tag = getattr(row, "mainline_tag", "") or getattr(row, "theme_name", "") or "未分类"
            role_label = self._mainline_role_label(str(getattr(row, "mainline_role", "") or ""))
            window_score = float(getattr(row, "mainline_window_score", 0.0) or 0.0)

            rationale_parts = [
                strategy_name,
                f"主线 {mainline_tag}",
                role_label,
                f"窗口 {window_score:.1f}",
                f"信号 {flow_signal}",
                f"阶段 {stage_label}",
            ]
            if getattr(row, "buy_point", ""):
                rationale_parts.append(f"买点 {getattr(row, 'buy_point')}")
            if getattr(row, "sell_point", ""):
                rationale_parts.append(f"卖点 {getattr(row, 'sell_point')}")
            if strategy_name == "尾盘买入法":
                rationale_parts.append("纪律 只做尾盘确认隔夜，次日开盘优先卖，不做盘中拖仓")
            if strategy_name == "一日持股法":
                rationale_parts.append("纪律 隔日优先兑现，不做拖仓")
            if row.rationale:
                rationale_parts.append(row.rationale)

            suggested_budget = round(min(remaining_budget, budget_per_pick * budget_multiplier), 2)
            if suggested_budget <= 0:
                continue
            remaining_budget = max(0.0, remaining_budget - suggested_budget)

            decisions.append(
                TradeDecision(
                    symbol=row.symbol,
                    stock_id=row.stock_id,
                    stock_name=row.stock_name,
                    action="BUY",
                    confidence=confidence,
                    planned_entry=planned_entry,
                    planned_stop=planned_stop,
                    planned_target=planned_target,
                    suggested_budget=suggested_budget,
                    rationale=" | ".join(part for part in rationale_parts if part),
                    stock_pool=stock_pool,
                    opportunity_tier=getattr(row, "opportunity_tier", ""),
                    execution_readiness=float(getattr(row, "execution_readiness", 0.0) or 0.0),
                    setup_quality_score=float(getattr(row, "setup_quality_score", 0.0) or 0.0),
                    risk_reward_ratio=float(getattr(row, "risk_reward_ratio", 0.0) or 0.0),
                    signal_age_days=int(getattr(row, "signal_age_days", 0) or 0),
                    next_focus=(
                        "只在 14:30 后确认尾盘回流和承接，隔夜后次日开盘优先兑现，弱开直接走。"
                        if strategy_name == "尾盘买入法"
                        else (
                        "盯次日竞价强弱、开盘 5 分钟承接和冲高兑现节奏，午后不转强就离场。"
                        if strategy_name == "一日持股法"
                        else getattr(row, "next_focus", "")
                        )
                    ),
                    mainline_flow_signal=flow_signal,
                    mainline_stage=stage_label,
                )
            )

        position_advice = self._position_advice(
            recommendations,
            holdings,
            pulse.sentiment_score,
            top_theme_limit=top_theme_limit,
            theme_drop_reduce=theme_drop_reduce,
        )

        notes = [
            "交易计划仅用于研究、筛选、风控和人工确认前准备，不替代你的自主判断。",
            f"当前市场处于{pulse.market_regime}，风险等级为{pulse.risk_level}，建议总仓位上限控制在{pulse.max_total_exposure:.0%}以内。",
            "所有新开仓动作都应从每日股票池中产生，先看市场，再选方向，最后做个股。",
            f"当前只优先参与题材排名前 {top_theme_limit} 的主线方向，符合条件的主线候选共 {len(theme_leaders)} 只。",
            f"市场脉冲信号：{pulse.mainline_flow_signal}（{pulse.mainline_flow_score:.1f}）",
        ]
        if pulse.risk_level == "高":
            notes.append("情绪偏弱时优先处理已有持仓的止盈止损，减少无把握的新仓试错。")
        if not decisions:
            notes.append("当前没有符合条件的新开仓候选，可优先等待或只处理现有持仓。")

        strategy_mix = self._strategy_mix(recommendations)
        if strategy_mix:
            notes.append("策略分布：" + "；".join(f"{name} {count} 只" for name, count in strategy_mix[:4]))
        pool_mix = self._pool_mix(recommendations)
        if pool_mix:
            notes.append("股票池分布：" + "；".join(f"{name} {count} 只" for name, count in pool_mix[:4]))
        focus_targets = [item.next_focus for item in decisions[:3] if item.next_focus]
        if focus_targets:
            notes.append("下一步重点：" + " / ".join(focus_targets))

        return DailyTradePlan(
            market_pulse=pulse,
            max_new_positions=max_new_positions,
            decisions=decisions,
            position_advice=position_advice,
            notes=notes,
        )

    def _market_pulse(self, recommendations: list[RecommendationRow]) -> MarketPulse:
        if not recommendations:
            return MarketPulse(
                sentiment_label="谨慎",
                sentiment_score=45.0,
                market_regime="冰点观察",
                risk_level="高",
                max_total_exposure=0.2,
                buy_ratio=0.0,
                average_total_score=45.0,
                strong_candidates=0,
                caution_candidates=0,
                mainline_flow_signal="切换/退潮",
                mainline_flow_score=45.0,
            )

        top = recommendations[: min(len(recommendations), 10)]
        avg_total = sum(item.total_score for item in top) / len(top)
        buy_ratio = sum(1 for item in top if item.action == "BUY") / len(top)
        strong_candidates = sum(1 for item in top if item.total_score >= 78 and item.action == "BUY")
        caution_candidates = sum(1 for item in top if item.news_score < 48 or item.position_score < 58)
        news_boost = sum(item.news_score for item in top) / len(top)
        leader_boost = sum(item.leader_score for item in top) / len(top)
        sentiment_score = min(
            95.0,
            max(
                35.0,
                avg_total * 0.58 + buy_ratio * 20 + news_boost * 0.1 + leader_boost * 0.06 - caution_candidates * 1.5,
            ),
        )

        lead_row = top[0]
        flow_scores = [
            float(getattr(item, "mainline_window_score", 0.0) or 0.0)
            + float(getattr(item, "mainline_strength_score", getattr(item, "theme_score", 0.0)) or 0.0) * 0.25
            - float(getattr(item, "theme_failure_risk", 0.0) or 0.0) * 0.2
            for item in top
        ]
        mainline_flow_score = round(sum(flow_scores) / len(flow_scores), 2) if flow_scores else round(sentiment_score, 2)
        mainline_flow_signal = self._row_mainline_flow_signal(lead_row)

        if sentiment_score >= 82:
            label = "积极"
            regime = "主升"
            risk_level = "低"
            exposure = 0.85
        elif sentiment_score >= 70:
            label = "偏强"
            regime = "修复"
            risk_level = "中"
            exposure = 0.6
        elif sentiment_score >= 58:
            label = "中性"
            regime = "分歧"
            risk_level = "中"
            exposure = 0.4
        else:
            label = "谨慎"
            regime = "退潮"
            risk_level = "高"
            exposure = 0.2

        return MarketPulse(
            sentiment_label=label,
            sentiment_score=round(sentiment_score, 2),
            market_regime=regime,
            risk_level=risk_level,
            max_total_exposure=exposure,
            buy_ratio=round(buy_ratio, 4),
            average_total_score=round(avg_total, 2),
            strong_candidates=strong_candidates,
            caution_candidates=caution_candidates,
            mainline_flow_signal=mainline_flow_signal,
            mainline_flow_score=mainline_flow_score,
        )

    def _position_advice(
        self,
        recommendations: list[RecommendationRow],
        holdings: list[HoldingRecord],
        sentiment_score: float,
        top_theme_limit: int = 3,
        theme_drop_reduce: bool = True,
    ) -> list[PositionAdvice]:
        recommendation_map = {item.symbol: item for item in recommendations}
        advice: list[PositionAdvice] = []
        for item in holdings:
            row = recommendation_map.get(item.symbol)
            current_price = row.close if row else (item.market_value / item.quantity if item.quantity else item.cost_price)
            pnl_pct = ((current_price - item.cost_price) / item.cost_price) if item.cost_price else 0.0
            flow_signal = self._row_mainline_flow_signal(row) if row else ""
            stage_label = self._row_mainline_stage(row) if row else ""
            strategy_name = getattr(row, "primary_strategy", "") if row else ""

            if row and row.label == "TRAP_DETECTED":
                action = "SELL"
                rationale = "出现诱多陷阱信号，优先兑现或撤退。"
                confidence = 0.9
            elif strategy_name == "尾盘买入法" and pnl_pct <= -0.015:
                action = "SELL"
                rationale = "尾盘买入法不接受隔夜后弱开弱走，次日一旦不及预期并出现亏损，优先离场。"
                confidence = 0.92
            elif strategy_name == "尾盘买入法" and pnl_pct >= 0.015:
                action = "REDUCE"
                rationale = "尾盘买入法的核心是赚开盘溢价，已有浮盈时优先在次日开盘附近兑现。"
                confidence = 0.86
            elif strategy_name == "一日持股法" and pnl_pct <= -0.02:
                action = "SELL"
                rationale = "一日持股法不接受隔夜弱转弱，次日未转强且出现亏损时优先离场。"
                confidence = 0.91
            elif strategy_name == "一日持股法" and pnl_pct >= 0.03:
                action = "REDUCE"
                rationale = "一日持股法以隔日兑现为主，已有浮盈时优先分批落袋。"
                confidence = 0.84
            elif pnl_pct <= -0.06:
                action = "SELL"
                rationale = "跌破防守区，优先执行止损，控制回撤。"
                confidence = 0.88
            elif row and theme_drop_reduce and str(getattr(row, "mainline_role", "") or "") == "ELIMINATED":
                action = "REDUCE"
                rationale = "主线地位已被淘汰，优先降低暴露。"
                confidence = 0.8
            elif row and flow_signal == "切换/退潮":
                action = "SELL"
                rationale = "主线进入切换/退潮，优先退出弱势持仓。"
                confidence = 0.9
            elif row and flow_signal == "切换预警":
                action = "REDUCE"
                rationale = "主线出现切换预警，先降仓位再等确认。"
                confidence = 0.82
            elif pnl_pct >= 0.12 and sentiment_score < 78:
                action = "REDUCE"
                rationale = "已有明显浮盈且市场温度不高，适合分批兑现。"
                confidence = 0.8
            elif row and theme_drop_reduce and row.theme_rank > top_theme_limit and pnl_pct > 0:
                action = "REDUCE"
                rationale = f"主线已掉出前 {top_theme_limit}，优先降低非主线仓位暴露。"
                confidence = 0.74
            elif row and row.label == "RECLAIM_LONG" and sentiment_score >= 70:
                action = "HOLD"
                rationale = f"趋势仍在延续，可继续持有观察。策略：{getattr(row, 'primary_strategy', '') or '掘龙决策'}"
                confidence = 0.78
            else:
                action = "WATCH"
                rationale = "暂无强制卖出信号，继续跟踪量价与消息变化。"
                confidence = 0.65

            advice.append(
                PositionAdvice(
                    symbol=item.symbol,
                    stock_id=(row.stock_id if row else item.symbol.split(".")[-1]),
                    stock_name=(row.stock_name if row else item.symbol.split(".")[-1]),
                    action=action,
                    confidence=confidence,
                    current_price=round(current_price, 3),
                    cost_price=round(item.cost_price, 3),
                    pnl_pct=round(pnl_pct, 4),
                    rationale=rationale,
                    mainline_flow_signal=flow_signal,
                    mainline_stage=stage_label,
                )
            )
        return advice

    @staticmethod
    def _strategy_mix(recommendations: list[RecommendationRow]) -> list[tuple[str, int]]:
        counter: dict[str, int] = {}
        for item in recommendations:
            name = getattr(item, "primary_strategy", "") or "掘龙决策"
            counter[name] = counter.get(name, 0) + 1
        return sorted(counter.items(), key=lambda pair: pair[1], reverse=True)

    @staticmethod
    def _pool_mix(recommendations: list[RecommendationRow]) -> list[tuple[str, int]]:
        counter: dict[str, int] = {}
        for item in recommendations:
            name = getattr(item, "stock_pool", "") or "趋势股"
            counter[name] = counter.get(name, 0) + 1
        return sorted(counter.items(), key=lambda pair: pair[1], reverse=True)
