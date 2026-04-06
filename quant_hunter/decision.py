from __future__ import annotations

from dataclasses import dataclass, field

from .models import HoldingRecord, RecommendationRow


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
        ]
        buy_candidates = buy_candidates[:max_new_positions]
        budget_per_pick = available_cash / max(len(buy_candidates), 1) if available_cash > 0 else 0.0

        decisions: list[TradeDecision] = []
        for row in buy_candidates:
            planned_entry = row.entry_price or row.close
            strategy_name = getattr(row, "primary_strategy", "") or "掘龙决策"
            if strategy_name == "擒龙打板":
                planned_stop = row.stop_price or planned_entry * 0.965
                planned_target = row.target_price or planned_entry * 1.13
            elif strategy_name == "价值低吸":
                planned_stop = row.stop_price or planned_entry * 0.945
                planned_target = row.target_price or planned_entry * 1.09
            else:
                planned_stop = row.stop_price or planned_entry * 0.95
                planned_target = row.target_price or planned_entry * 1.08
            confidence_source = getattr(row, "dragon_decision_score", 0.0) or row.total_score
            confidence = min(max(confidence_source / 100.0, 0.0), 0.99)
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
                    suggested_budget=round(budget_per_pick, 2),
                    rationale=f"{strategy_name} | {row.rationale}",
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
        ]
        if pulse.risk_level == "高":
            notes.append("情绪偏弱时优先处理已有持仓的止盈止损，减少无把握的新仓试错。")
        if not decisions:
            notes.append("当前没有符合条件的新开仓候选，可优先等待或只处理现有持仓。")

        strategy_mix = self._strategy_mix(recommendations)
        if strategy_mix:
            notes.append("策略分布：" + "，".join(f"{name} {count} 只" for name, count in strategy_mix[:4]))

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

            if row and row.label == "TRAP_DETECTED":
                action = "SELL"
                rationale = "出现诱多陷阱信号，优先兑现或撤退。"
                confidence = 0.9
            elif pnl_pct <= -0.06:
                action = "SELL"
                rationale = "跌破防守区，优先执行止损，控制回撤。"
                confidence = 0.88
            elif pnl_pct >= 0.12 and sentiment_score < 78:
                action = "REDUCE"
                rationale = "已有明显浮盈且市场温度不高，适合分批兑现。"
                confidence = 0.8
            elif row and theme_drop_reduce and row.theme_rank > top_theme_limit and pnl_pct > 0:
                action = "REDUCE"
                rationale = f"所属题材已退出主线前 {top_theme_limit}，优先降低非主线仓位暴露。"
                confidence = 0.74
            elif row and row.label == "RECLAIM_LONG" and sentiment_score >= 70:
                action = "HOLD"
                rationale = "趋势仍在延续，可继续持有观察。"
                rationale += f" 策略：{getattr(row, 'primary_strategy', '') or '掘龙决策'}"
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
