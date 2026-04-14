from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from .data import extract_stock_id
from .models import DailyAnalysis, NewsCatalyst, RecommendationRow, ScanRow, StockProfile, SymbolBacktestSummary
from .risk import DEFAULT_RISK_CONTROLS, RiskControls, normalize_risk_profile, resolve_risk_controls
from .theme import ThemeHeatEngine, infer_mainline_flow_signal, infer_mainline_stage, infer_theme_name


def _mainline_stage_priority(stage: str) -> int:
    return {
        "加速": 0,
        "启动": 1,
        "分歧": 2,
        "观察": 3,
        "退潮": 4,
    }.get(stage, 9)


def _mainline_flow_priority(signal: str) -> int:
    return {
        "延续偏强": 0,
        "延续待确认": 1,
        "延续可跟踪": 2,
        "延续观察": 3,
        "切换预警": 4,
        "切换/退潮": 5,
    }.get(signal, 9)


def _one_day_hold_sort_priority(item: RecommendationRow) -> tuple[float, float, float, float]:
    strategy_name = (getattr(item, "primary_strategy", "") or "")
    if strategy_name not in {"一日持股法", "尾盘买入法"}:
        return (1.0, 0.0, 0.0, 0.0)
    one_day_score = float(
        getattr(item, "tail_buy_score", 0.0) or 0.0
        if strategy_name == "尾盘买入法"
        else getattr(item, "one_day_hold_score", 0.0) or 0.0
    )
    readiness = float(getattr(item, "execution_readiness", 0.0) or 0.0)
    window_score = float(getattr(item, "mainline_window_score", 0.0) or 0.0)
    continuation = float(getattr(item, "mainline_continuation_score", 0.0) or window_score or 0.0)
    risk_flag = str(getattr(item, "mainline_risk_flag", "") or "")
    risk_adjust = {"低": 2.0, "中": -4.0, "高": -12.0}.get(risk_flag, 0.0)

    auction_score = round(one_day_score * 0.52 + readiness * 0.28 + window_score * 0.20 + risk_adjust, 2)
    open_score = round(one_day_score * 0.30 + readiness * 0.46 + continuation * 0.24 + risk_adjust, 2)
    afternoon_score = round(one_day_score * 0.24 + readiness * 0.24 + window_score * 0.28 + continuation * 0.24 + risk_adjust - 3.0, 2)
    tripwire_score = round(auction_score * 0.45 + open_score * 0.35 + afternoon_score * 0.20, 2)
    return (0.0, -tripwire_score, -auction_score, -open_score)


def _recommendation_sort_key(item: RecommendationRow) -> tuple[object, ...]:
    stage_label = infer_mainline_stage(
        theme_rank=item.mainline_rank or item.theme_rank or 0,
        strength_score=item.mainline_strength_score or item.theme_score or item.total_score,
        continuation_score=item.mainline_continuation_score,
        divergence_score=item.theme_divergence_score,
        failure_risk=item.theme_failure_risk,
        window_score=item.mainline_window_score,
        mainline_role=item.mainline_role,
    )
    flow_signal = infer_mainline_flow_signal(
        theme_rank=item.mainline_rank or item.theme_rank or 0,
        strength_score=item.mainline_strength_score or item.theme_score or item.total_score,
        continuation_score=item.mainline_continuation_score,
        divergence_score=item.theme_divergence_score,
        failure_risk=item.theme_failure_risk,
        window_score=item.mainline_window_score,
        mainline_role=item.mainline_role,
    )
    return (
        item.mainline_rank == 0,
        item.mainline_rank or 99,
        _mainline_stage_priority(stage_label),
        _mainline_flow_priority(flow_signal),
        *_one_day_hold_sort_priority(item),
        -(getattr(item, "backtest_quality_score", 0.0) or 0.0),
        -(getattr(item, "setup_quality_score", 0.0) or 0.0),
        -(getattr(item, "freshness_score", 0.0) or 0.0),
        -(getattr(item, "risk_reward_ratio", 0.0) or 0.0),
        -item.mainline_window_score,
        -item.leader_position_score,
        -item.total_score,
        item.stock_id,
    )


def _parse_date(value: str) -> date | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


class DailyPoolBuilder:
    def __init__(
        self,
        stock_profiles: dict[str, StockProfile] | None = None,
        news_map: dict[str, list[NewsCatalyst]] | None = None,
        theme_aliases: dict[str, tuple[str, ...]] | None = None,
        focus_themes: list[str] | None = None,
        focus_theme_boost: float = 0.0,
        strategy_bias_by_name: dict[str, float] | None = None,
        risk_profile: str | None = None,
        risk_controls: RiskControls | None = None,
    ) -> None:
        self.stock_profiles = stock_profiles or {}
        self.news_map = news_map or {}
        self.theme_aliases = theme_aliases or {}
        self.focus_themes = tuple(item.strip() for item in (focus_themes or []) if item.strip())
        self.focus_theme_boost = max(focus_theme_boost, 0.0)
        self.strategy_bias_by_name = {str(key).strip(): float(value or 0.0) for key, value in (strategy_bias_by_name or {}).items() if str(key).strip()}
        self.risk_profile = normalize_risk_profile(risk_profile)
        self.risk_controls = risk_controls or resolve_risk_controls(self.risk_profile)
        self.last_theme_rows = []
        self.last_leader_rows = []

    def build(
        self,
        scan_rows: list[ScanRow],
        analyses_by_symbol: dict[str, list[DailyAnalysis]],
        backtest_summaries: list[SymbolBacktestSummary],
        top_n: int = 15,
        as_of: date | None = None,
    ) -> list[RecommendationRow]:
        as_of = as_of or date.today()
        summary_map = {item.symbol: item for item in backtest_summaries}
        candidates: list[RecommendationRow] = []

        for row in scan_rows:
            if row.label not in {"RECLAIM_LONG", "WATCH"}:
                continue
            profile = self.stock_profiles.get(row.symbol)
            analyses = analyses_by_symbol.get(row.symbol, [])
            summary = summary_map.get(row.symbol)
            technical_score = float(row.score)
            position_score = self._position_score(row, analyses)
            persistence_score = self._persistence_score(analyses, summary)
            backtest_quality_score = self._backtest_quality_score(summary)
            news_score, catalyst = self._news_score(row.symbol, as_of)
            leader_score = 88.0 if profile and profile.is_leader else 58.0
            theme_name = infer_theme_name(
                profile.industry if profile else "",
                profile.notes if profile else "",
                catalyst,
                theme_aliases=self.theme_aliases,
            )
            focus_boost = self.focus_theme_boost if theme_name and theme_name in self.focus_themes else 0.0
            strategy_scores = self._strategy_scores(
                row=row,
                profile=profile,
                technical_score=technical_score,
                position_score=position_score,
                persistence_score=persistence_score,
                news_score=news_score,
                leader_score=leader_score,
                catalyst=catalyst,
            )
            pool_profile = self._stock_pool_profile(
                row=row,
                profile=profile,
                technical_score=technical_score,
                position_score=position_score,
                persistence_score=persistence_score,
                news_score=news_score,
                leader_score=leader_score,
                strategy_scores=strategy_scores,
            )
            total_score = round(
                technical_score * 0.30
                + position_score * 0.18
                + persistence_score * 0.18
                + backtest_quality_score * 0.10
                + news_score * 0.12
                + leader_score * 0.08
                + strategy_scores["dragon_decision_score"] * 0.04,
                2,
            )
            if focus_boost:
                total_score = round(min(99.0, total_score + focus_boost), 2)
            reasons = [
                f"技术面 {technical_score:.0f}",
                f"位置 {position_score:.0f}",
                f"持续性 {persistence_score:.0f}",
            ]
            reasons.append(f"回测稳定性 {backtest_quality_score:.0f}")
            if catalyst:
                reasons.append(f"消息面 {catalyst}")
            if profile and profile.is_leader:
                reasons.append("具备龙头属性")
            if theme_name:
                reasons.append(f"题材 {theme_name}")
            if focus_boost:
                reasons.append(f"关注题材加权 +{focus_boost:.0f}")

            reasons.append(
                f"策略 {strategy_scores['primary_strategy']} "
                f"(龙头 {strategy_scores['leader_model_score']:.0f} / 主力 {strategy_scores['main_force_score']:.0f} / "
                f"打板 {strategy_scores['board_attack_score']:.0f} / 低吸 {strategy_scores['value_recovery_score']:.0f} / "
                f"尾盘 {strategy_scores['tail_buy_score']:.0f} / 一日 {strategy_scores['one_day_hold_score']:.0f} / 决策 {strategy_scores['dragon_decision_score']:.0f})"
            )
            reasons.append(
                f"股票池 {pool_profile['stock_pool']} | 买点 {pool_profile['buy_point']} | 卖点 {pool_profile['sell_point']}"
            )
            candidates.append(
                RecommendationRow(
                    symbol=row.symbol,
                    stock_id=(profile.stock_id if profile else row.stock_id) or extract_stock_id(row.symbol),
                    stock_name=(profile.name if profile else row.stock_name) or extract_stock_id(row.symbol),
                    action=row.action,
                    label=row.label,
                    signal_date=row.signal_date,
                    close=row.close,
                    entry_price=row.entry_price,
                    stop_price=row.stop_price,
                    target_price=row.target_price,
                    technical_score=technical_score,
                    position_score=position_score,
                    persistence_score=persistence_score,
                    backtest_quality_score=backtest_quality_score,
                    news_score=news_score,
                    leader_score=leader_score,
                    total_score=total_score,
                    theme_name=theme_name,
                    primary_strategy=strategy_scores["primary_strategy"],
                    stock_pool=pool_profile["stock_pool"],
                    pool_score=pool_profile["pool_score"],
                    buy_point=pool_profile["buy_point"],
                    add_point=pool_profile["add_point"],
                    sell_point=pool_profile["sell_point"],
                    risk_line=pool_profile["risk_line"],
                    leader_model_score=strategy_scores["leader_model_score"],
                    main_force_score=strategy_scores["main_force_score"],
                    board_attack_score=strategy_scores["board_attack_score"],
                    value_recovery_score=strategy_scores["value_recovery_score"],
                    tail_buy_score=strategy_scores["tail_buy_score"],
                    one_day_hold_score=strategy_scores["one_day_hold_score"],
                    dragon_decision_score=strategy_scores["dragon_decision_score"],
                    signal_source=row.source_path,
                    catalyst=catalyst,
                    rationale=" | ".join(reasons),
                )
            )

        themed_candidates, theme_rows, leader_rows = ThemeHeatEngine(theme_aliases=self.theme_aliases).analyze(candidates)
        themed_candidates = [self._enrich_user_focus(item) for item in themed_candidates]
        themed_candidates.sort(key=_recommendation_sort_key)
        self.last_theme_rows = theme_rows
        self.last_leader_rows = leader_rows
        return themed_candidates[:top_n]

    def _stock_pool_profile(
        self,
        row: ScanRow,
        profile: StockProfile | None,
        technical_score: float,
        position_score: float,
        persistence_score: float,
        news_score: float,
        leader_score: float,
        strategy_scores: dict[str, float | str],
    ) -> dict[str, float | str]:
        primary_strategy = str(strategy_scores.get("primary_strategy", "") or "")
        if primary_strategy == "尾盘买入法":
            entry = row.entry_price or row.close
            stop_price = row.stop_price or entry * 0.976
            target_price = row.target_price or entry * 1.032
            return {
                "stock_pool": "趋势股",
                "pool_score": round(min(float(strategy_scores.get("tail_buy_score", 0.0)), 99.0), 2),
                "buy_point": f"仅在 14:30 之后确认尾盘回流和承接后，围绕 {entry:.2f} 小仓试单，不提前埋伏",
                "add_point": f"尾盘最后半小时若持续站稳 {max(entry * 1.002, stop_price * 1.01):.2f} 且量能不乱，再考虑轻微加码",
                "sell_point": f"次日开盘优先看 {target_price:.2f} 附近兑现，平开也先走一半，弱开直接离场",
                "risk_line": f"若尾盘回流失败或跌破 {stop_price:.2f}，取消隔夜；次日低开低走不恋战",
            }
        if primary_strategy == "一日持股法":
            entry = row.entry_price or row.close
            stop_price = row.stop_price or entry * 0.972
            target_price = row.target_price or entry * 1.055
            return {
                "stock_pool": "趋势股",
                "pool_score": round(min(float(strategy_scores.get("one_day_hold_score", 0.0)), 99.0), 2),
                "buy_point": f"围绕 {entry:.2f} 强势确认介入，原则上只博弈隔日溢价，不追尾盘扩张",
                "add_point": f"次日仅在高开承接强于预期且不破 {max(entry * 0.995, stop_price * 1.01):.2f} 时小幅加码",
                "sell_point": f"次日冲高靠近 {target_price:.2f} 优先兑现，午后仍未转强就收缩战线",
                "risk_line": f"若次日弱开弱走或跌破 {stop_price:.2f}，直接离场，不做恋战",
            }
        leader_pool_score = (
            float(strategy_scores["leader_model_score"]) * 0.54
            + float(strategy_scores["board_attack_score"]) * 0.24
            + leader_score * 0.14
            + news_score * 0.08
        )
        trend_pool_score = (
            float(strategy_scores["main_force_score"]) * 0.44
            + persistence_score * 0.28
            + technical_score * 0.18
            + position_score * 0.10
        )
        value_pool_score = (
            float(strategy_scores["value_recovery_score"]) * 0.50
            + position_score * 0.24
            + technical_score * 0.14
            + persistence_score * 0.12
        )
        ranked = [
            ("龙头股", leader_pool_score),
            ("趋势股", trend_pool_score),
            ("价值股", value_pool_score),
        ]
        if profile and profile.is_leader:
            ranked[0] = (ranked[0][0], ranked[0][1] + 4.0)
        ranked.sort(key=lambda item: item[1], reverse=True)
        stock_pool = ranked[0][0]
        return {
            "stock_pool": stock_pool,
            "pool_score": round(min(ranked[0][1], 99.0), 2),
            "buy_point": self._pool_buy_point(stock_pool, row),
            "add_point": self._pool_add_point(stock_pool, row),
            "sell_point": self._pool_sell_point(stock_pool, row),
            "risk_line": self._pool_risk_line(stock_pool, row),
        }

    def _pool_buy_point(self, stock_pool: str, row: ScanRow) -> str:
        entry = row.entry_price or row.close
        if stock_pool == "龙头股":
            return f"放量突破或回封确认后在 {entry:.2f} 附近分批介入"
        if stock_pool == "趋势股":
            return f"回踩均线企稳或平台突破时在 {entry:.2f} 附近低吸"
        return f"超跌修复确认后在 {entry:.2f} 附近试仓，避免追高"

    def _pool_add_point(self, stock_pool: str, row: ScanRow) -> str:
        entry = row.entry_price or row.close
        stop_price = row.stop_price or entry * 0.95
        if stock_pool == "龙头股":
            return f"分时承接不破 {max(entry * 0.99, stop_price * 1.03):.2f} 可小幅加仓"
        if stock_pool == "趋势股":
            return f"沿 5 日或 10 日均线抬升，站稳 {max(entry * 1.01, stop_price * 1.05):.2f} 再加仓"
        return f"修复后二次回踩不破 {max(entry * 0.98, stop_price * 1.02):.2f} 再考虑补仓"

    def _pool_sell_point(self, stock_pool: str, row: ScanRow) -> str:
        entry = row.entry_price or row.close
        stop_price = row.stop_price or entry * 0.95
        target_price = row.target_price or (entry * 1.12 if stock_pool != "价值股" else entry * 1.08)
        if stock_pool == "龙头股":
            return f"冲高到 {target_price:.2f} 附近分批止盈，炸板或转弱先减仓"
        if stock_pool == "趋势股":
            return f"接近 {target_price:.2f} 分批兑现，跌破趋势支撑 {stop_price:.2f} 先撤"
        return f"修复到 {target_price:.2f} 附近落袋，若再度跌破 {stop_price:.2f} 放弃博弈"

    def _pool_risk_line(self, stock_pool: str, row: ScanRow) -> str:
        entry = row.entry_price or row.close
        stop_price = row.stop_price or (entry * 0.965 if stock_pool == "龙头股" else entry * 0.95)
        if stock_pool == "龙头股":
            return f"跌破 {stop_price:.2f} 或高位爆量转弱立即退守"
        if stock_pool == "趋势股":
            return f"跌破 {stop_price:.2f} 或均线系统走坏时离场"
        return f"跌破 {stop_price:.2f} 或修复失败时止损离场"

    def _position_score(self, row: ScanRow, analyses: list[DailyAnalysis]) -> float:
        if not analyses:
            return 55.0
        latest = analyses[-1]
        breakout_level = latest.breakout_level or row.close
        if breakout_level <= 0:
            return 55.0
        extension = max((row.close - breakout_level) / breakout_level, 0.0)
        if row.label == "RECLAIM_LONG":
            if extension <= 0.03:
                return 92.0
            if extension <= 0.08:
                return 82.0
            if extension <= 0.15:
                return 68.0
            return 52.0
        if extension <= 0.05:
            return 72.0
        return 60.0

    def _persistence_score(
        self,
        analyses: list[DailyAnalysis],
        summary: SymbolBacktestSummary | None,
    ) -> float:
        if not analyses:
            return 50.0
        recent = analyses[-8:]
        reclaim_count = sum(1 for item in recent if item.label == "RECLAIM_LONG")
        watch_count = sum(1 for item in recent if item.label == "WATCH")
        latest = recent[-1]
        ma_trend_bonus = 8.0 if latest.ma_fast >= latest.ma_slow and latest.close >= latest.ma_slow else 0.0
        base = 52.0 + reclaim_count * 12.0 + watch_count * 5.0 + ma_trend_bonus
        if summary:
            base += min(summary.total_return * 100, 12.0)
            base += min(summary.win_rate * 20, 8.0)
        return max(40.0, min(base, 96.0))

    def _backtest_quality_score(self, summary: SymbolBacktestSummary | None) -> float:
        if summary is None:
            return 52.0
        trade_sample = min(float(summary.trades or 0), 12.0)
        quality = (
            52.0
            + min(float(summary.total_return or 0.0) * 100.0, 18.0)
            + min(float(summary.win_rate or 0.0) * 18.0, 12.0)
            - min(float(summary.max_drawdown or 0.0) * 100.0 * 0.7, 16.0)
            + trade_sample
        )
        return max(28.0, min(quality, 96.0))

    def _news_score(self, symbol: str, as_of: date) -> tuple[float, str]:
        items = self.news_map.get(symbol, [])
        if not items:
            return 50.0, ""
        score = 46.0
        headlines: list[str] = []
        for item in items[:3]:
            freshness = self._freshness_weight(item.published_at, as_of)
            score += (item.sentiment_score * 12.0 + item.heat * 4.0) * freshness
            if item.title:
                headlines.append(item.title)
        score = max(30.0, min(score, 95.0))
        return round(score, 2), " / ".join(headlines[:2])

    def _freshness_weight(self, published_at: str, as_of: date) -> float:
        published = _parse_date(published_at)
        if published is None:
            return 0.7
        delta_days = max((as_of - published).days, 0)
        if delta_days <= 1:
            return 1.0
        if delta_days <= 3:
            return 0.8
        if delta_days <= 7:
            return 0.55
        return 0.3

    def _strategy_rotation_bias(self, strategy_name: str) -> float:
        raw = float(self.strategy_bias_by_name.get(strategy_name, 0.0) or 0.0)
        return max(min(raw * 8.0, 6.0), -6.0)

    def _strategy_scores(
        self,
        row: ScanRow,
        profile: StockProfile | None,
        technical_score: float,
        position_score: float,
        persistence_score: float,
        news_score: float,
        leader_score: float,
        catalyst: str,
    ) -> dict[str, float | str]:
        context = " ".join(
            [
                row.reason,
                catalyst,
                profile.industry if profile else "",
                profile.notes if profile else "",
            ]
        ).lower()
        main_force_bias = 8.0 if any(keyword in context for keyword in ("主力", "机构", "净流入", "游资")) else 0.0
        board_bias = 8.0 if any(keyword in context for keyword in ("打板", "回封", "连板", "涨停")) else 0.0
        value_bias = 8.0 if any(keyword in context for keyword in ("低吸", "回踩", "低位", "修复")) else 0.0

        one_day_bias = 10.0 if any(keyword in context for keyword in ("一日持股", "隔日", "次日", "隔夜", "高开", "竞价", "首板", "转强")) else 0.0
        tail_buy_bias = 12.0 if any(keyword in context for keyword in ("尾盘", "收盘前", "14:30", "两点半", "尾盘买入", "开盘卖", "次日开盘", "尾盘回流")) else 0.0
        next_day_window_score = max(0.0, 92.0 - abs(position_score - 76.0))
        tail_buy_window_score = max(0.0, 94.0 - abs(position_score - 72.0))

        leader_model_score = min(
            98.0,
            technical_score * 0.32
            + persistence_score * 0.22
            + leader_score * 0.26
            + position_score * 0.12
            + news_score * 0.08,
        )
        main_force_score = min(
            98.0,
            technical_score * 0.18
            + position_score * 0.18
            + persistence_score * 0.14
            + news_score * 0.20
            + leader_score * 0.12
            + main_force_bias,
        )
        board_attack_score = min(
            98.0,
            technical_score * 0.27
            + persistence_score * 0.24
            + leader_score * 0.14
            + max(0.0, 90.0 - abs(position_score - 78.0)) * 0.15
            + news_score * 0.12
            + board_bias,
        )
        value_recovery_score = min(
            98.0,
            position_score * 0.34
            + technical_score * 0.20
            + persistence_score * 0.16
            + news_score * 0.12
            + max(0.0, 88.0 - abs(technical_score - 70.0)) * 0.08
            + leader_score * 0.10
            + value_bias,
        )
        one_day_hold_score = min(
            98.0,
            technical_score * 0.22
            + position_score * 0.18
            + persistence_score * 0.14
            + news_score * 0.16
            + leader_score * 0.08
            + board_attack_score * 0.12
            + main_force_score * 0.08
            + next_day_window_score * 0.10
            + one_day_bias,
        )
        tail_buy_score = min(
            98.0,
            technical_score * 0.18
            + position_score * 0.12
            + persistence_score * 0.16
            + news_score * 0.12
            + leader_score * 0.05
            + main_force_score * 0.14
            + board_attack_score * 0.05
            + one_day_hold_score * 0.18
            + tail_buy_window_score * 0.10
            + tail_buy_bias,
        )
        leader_model_score = min(99.0, max(0.0, leader_model_score + self._strategy_rotation_bias("龙头模型")))
        main_force_score = min(99.0, max(0.0, main_force_score + self._strategy_rotation_bias("主力雷达")))
        board_attack_score = min(99.0, max(0.0, board_attack_score + self._strategy_rotation_bias("擒龙打板")))
        value_recovery_score = min(99.0, max(0.0, value_recovery_score + self._strategy_rotation_bias("价值低吸")))
        one_day_hold_score = min(99.0, max(0.0, one_day_hold_score + self._strategy_rotation_bias("一日持股法")))
        tail_buy_score = min(99.0, max(0.0, tail_buy_score + self._strategy_rotation_bias("尾盘买入法")))
        dragon_decision_score = min(
            99.0,
            leader_model_score * 0.22
            + main_force_score * 0.16
            + board_attack_score * 0.14
            + value_recovery_score * 0.15
            + tail_buy_score * 0.08
            + one_day_hold_score * 0.09
            + technical_score * 0.07
            + position_score * 0.04
            + persistence_score * 0.03
            + news_score * 0.02,
        )
        ranked = [
            ("龙头模型", leader_model_score),
            ("主力雷达", main_force_score),
            ("强势接力", board_attack_score),
            ("价值低吸", value_recovery_score),
            ("掘龙决策", dragon_decision_score),
        ]
        ranked.append(("尾盘买入法", tail_buy_score))
        ranked.append(("一日持股法", one_day_hold_score))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return {
            "primary_strategy": ranked[0][0],
            "leader_model_score": round(leader_model_score, 2),
            "main_force_score": round(main_force_score, 2),
            "board_attack_score": round(board_attack_score, 2),
            "value_recovery_score": round(value_recovery_score, 2),
            "tail_buy_score": round(tail_buy_score, 2),
            "one_day_hold_score": round(one_day_hold_score, 2),
            "dragon_decision_score": round(dragon_decision_score, 2),
        }

    @staticmethod
    def _bounded_score(value: float) -> float:
        return max(0.0, min(value, 99.0))

    def _signal_age_days(self, row: RecommendationRow) -> int:
        signal_date = _parse_date(getattr(row, "signal_date", "") or "")
        if signal_date is None:
            return 0
        return max((date.today() - signal_date).days, 0)

    def _risk_reward_ratio(self, row: RecommendationRow) -> float:
        entry = float(row.entry_price or row.close or 0.0)
        stop = float(row.stop_price or 0.0)
        target = float(row.target_price or 0.0)
        if entry <= 0 or stop <= 0 or target <= 0:
            return 0.0
        estimated_loss = max(entry - stop, 0.0)
        estimated_profit = max(target - entry, 0.0)
        if estimated_loss <= 0:
            return 0.0
        return estimated_profit / estimated_loss

    def _freshness_score(self, row: RecommendationRow, signal_age_days: int) -> float:
        if signal_age_days <= 0:
            base = 96.0
        elif signal_age_days == 1:
            base = 84.0
        elif signal_age_days == 2:
            base = 68.0
        elif signal_age_days == 3:
            base = 54.0
        else:
            base = 36.0
        if str(getattr(row, "signal_source", "") or "").startswith("synthetic://"):
            base -= 28.0
        return self._bounded_score(base)

    def _enrich_user_focus(self, row: RecommendationRow) -> RecommendationRow:
        signal_age_days = self._signal_age_days(row)
        risk_reward_ratio = round(self._risk_reward_ratio(row), 2)
        freshness_score = round(self._freshness_score(row, signal_age_days), 2)
        setup_quality_score = round(
            self._bounded_score(
                row.technical_score * 0.18
                + row.position_score * 0.16
                + row.backtest_quality_score * 0.12
                + row.mainline_window_score * 0.16
                + row.dragon_decision_score * 0.14
                + min(risk_reward_ratio * 28.0, 99.0) * 0.14
                + freshness_score * 0.10
                + (100.0 - row.theme_failure_risk) * 0.06
            ),
            2,
        )
        confidence_score = round(
            self._bounded_score(
                row.dragon_decision_score * 0.28
                + row.total_score * 0.18
                + row.backtest_quality_score * 0.10
                + row.mainline_window_score * 0.18
                + freshness_score * 0.12
                + min(risk_reward_ratio * 30.0, 99.0) * 0.10
                + setup_quality_score * 0.04
            ),
            2,
        )
        execution_readiness = round(
            self._bounded_score(
                row.position_score * 0.24
                + row.mainline_window_score * 0.20
                + row.technical_score * 0.14
                + row.persistence_score * 0.12
                + row.backtest_quality_score * 0.08
                + freshness_score * 0.10
                + min(risk_reward_ratio * 26.0, 99.0) * 0.10
                + (100.0 - row.theme_failure_risk) * 0.10
            ),
            2,
        )
        timeliness_score = round(
            self._bounded_score(
                row.position_score * 0.30
                + row.news_score * 0.14
                + row.mainline_window_score * 0.16
                + max(0.0, 100.0 - row.theme_rotation_score) * 0.10
                + freshness_score * 0.30
            ),
            2,
        )
        reject_reason = self._reject_reason(
            row,
            signal_age_days=signal_age_days,
            risk_reward_ratio=risk_reward_ratio,
            freshness_score=freshness_score,
        )
        opportunity_tier = self._opportunity_tier(
            row,
            confidence_score=confidence_score,
            execution_readiness=execution_readiness,
            timeliness_score=timeliness_score,
            freshness_score=freshness_score,
            setup_quality_score=setup_quality_score,
            risk_reward_ratio=risk_reward_ratio,
            reject_reason=reject_reason,
        )
        next_focus = self._next_focus(row, reject_reason)
        invalidation_reason = (row.risk_line or "").strip() or "跌破计划防守线或主线窗口继续收缩时放弃。"
        return replace(
            row,
            confidence_score=confidence_score,
            execution_readiness=execution_readiness,
            timeliness_score=timeliness_score,
            freshness_score=freshness_score,
            setup_quality_score=setup_quality_score,
            risk_reward_ratio=risk_reward_ratio,
            signal_age_days=signal_age_days,
            opportunity_tier=opportunity_tier,
            reject_reason=reject_reason,
            next_focus=next_focus,
            invalidation_reason=invalidation_reason,
        )

    def _reject_reason(
        self,
        row: RecommendationRow,
        *,
        signal_age_days: int,
        risk_reward_ratio: float,
        freshness_score: float,
    ) -> str:
        role = (row.mainline_role or "").strip()
        risk_flag = (row.mainline_risk_flag or "").strip()
        signal_source = str(getattr(row, "signal_source", "") or "").strip()
        if signal_source.startswith("synthetic://"):
            return "当前仅有补位候选，缺少真实历史信号，先不作为可执行买点。"
        if row.backtest_quality_score and row.backtest_quality_score < 40.0:
            return "历史回测稳定性偏弱，先观察，不急着执行。"
        if role in {"NOISE", "ELIMINATED"}:
            return "不在主线核心参与区，先不新开仓。"
        if row.mainline_rank and row.mainline_rank > 3:
            return "主线位次偏后，胜率和性价比都在下降。"
        if risk_flag == "高" or row.theme_failure_risk >= 72.0:
            return "题材退潮风险偏高，先回避。"
        if risk_reward_ratio and risk_reward_ratio < self.risk_controls.recommendation_min_risk_reward_ratio:
            return "预期盈亏比偏低，试错空间不够，先不急着出手。"
        if freshness_score < 45.0 or signal_age_days >= 4:
            return "信号已经偏旧，盘面节奏可能变化，需等新的触发点。"
        if row.mainline_window_score and row.mainline_window_score < 50.0:
            return "窗口还没打开，容易追高后被动。"
        if row.position_score < 60.0:
            return "位置不够舒服，先等回踩或确认。"
        if (row.target_price or 0.0) <= (row.entry_price or row.close or 0.0):
            return "目标位没有拉开，暂时不具备足够收益空间。"
        return ""

    def _opportunity_tier(
        self,
        row: RecommendationRow,
        *,
        confidence_score: float,
        execution_readiness: float,
        timeliness_score: float,
        freshness_score: float,
        setup_quality_score: float,
        risk_reward_ratio: float,
        reject_reason: str,
    ) -> str:
        priority_confidence = 78.0
        priority_readiness = 74.0
        priority_timeliness = 70.0
        confirm_risk_reward = 1.45
        if self.risk_profile == "conservative":
            priority_confidence = 82.0
            priority_readiness = 78.0
            priority_timeliness = 74.0
            confirm_risk_reward = 1.6
        elif self.risk_profile == "aggressive":
            priority_confidence = 74.0
            priority_readiness = 70.0
            priority_timeliness = 66.0
            confirm_risk_reward = 1.3
        if getattr(row, "action", "") == "BUY" and not reject_reason:
            if (
                confidence_score >= priority_confidence
                and execution_readiness >= priority_readiness
                and timeliness_score >= priority_timeliness
                and freshness_score >= 72.0
                and setup_quality_score >= 74.0
                and risk_reward_ratio >= 1.8
            ):
                return "优先处理"
            if risk_reward_ratio >= confirm_risk_reward and freshness_score >= 58.0:
                return "跟踪确认"
            return "观察名单"
        if getattr(row, "action", "") in {"WATCH", "HOLD"}:
            return "观察名单"
        return "风险回避"

    def _next_focus(self, row: RecommendationRow, reject_reason: str) -> str:
        strategy_name = getattr(row, "primary_strategy", "") or ""
        if reject_reason:
            if strategy_name == "尾盘买入法":
                return "先等 14:30 之后尾盘回流、承接和量能缩放确认，再看是否值得隔夜，次日只做开盘兑现。"
            if strategy_name == "一日持股法":
                return "先看次日竞价是否高开转强，再看开盘 5 分钟量能与承接，弱于预期就放弃。"
            if row.mainline_window_score < 50.0:
                return "等放量突破或回踩承接确认后再看。"
            if row.theme_failure_risk >= 72.0 or row.mainline_risk_flag == "高":
                return "等题材分歧收敛、风险标签回落后再看。"
            return "先保留观察，不急着出手。"
        if strategy_name == "尾盘买入法":
            return "重点看 14:30 后尾盘回流、承接是否稳定，以及次日开盘能否先兑现，不做拖仓。"
        if row.stock_pool == "龙头股":
            return "盯回封强度、量能放大和主线前排站位。"
        if row.stock_pool == "价值股":
            return "盯修复确认和二次回踩是否站稳。"
        return "盯量价延续、均线承接和主线窗口是否继续扩张。"
