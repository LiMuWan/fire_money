from __future__ import annotations

from datetime import date, datetime

from .data import extract_stock_id
from .models import DailyAnalysis, NewsCatalyst, RecommendationRow, ScanRow, StockProfile, SymbolBacktestSummary
from .theme import ThemeHeatEngine, infer_theme_name


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
    ) -> None:
        self.stock_profiles = stock_profiles or {}
        self.news_map = news_map or {}
        self.theme_aliases = theme_aliases or {}
        self.focus_themes = tuple(item.strip() for item in (focus_themes or []) if item.strip())
        self.focus_theme_boost = max(focus_theme_boost, 0.0)
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
            technical_score = float(row.score)
            position_score = self._position_score(row, analyses)
            persistence_score = self._persistence_score(analyses, summary_map.get(row.symbol))
            news_score, catalyst = self._news_score(row.symbol, as_of)
            leader_score = 88.0 if profile and profile.is_leader else 58.0
            theme_name = infer_theme_name(
                profile.industry if profile else "",
                profile.notes if profile else "",
                catalyst,
                row.reason,
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
            total_score = round(
                technical_score * 0.34
                + position_score * 0.2
                + persistence_score * 0.22
                + news_score * 0.14
                + leader_score * 0.1
                + strategy_scores["dragon_decision_score"] * 0.06,
                2,
            )
            if focus_boost:
                total_score = round(min(99.0, total_score + focus_boost), 2)
            reasons = [
                f"技术面 {technical_score:.0f}",
                f"位置 {position_score:.0f}",
                f"持续性 {persistence_score:.0f}",
            ]
            if catalyst:
                reasons.append(f"消息面 {catalyst}")
            if profile and profile.is_leader:
                reasons.append("具备龙头属性")
            if theme_name:
                reasons.append(f"题材 {theme_name}")
            if focus_boost:
                reasons.append(f"关注题材加权 +{focus_boost:.0f}")

            reasons.append(
                f"绛栫暐 {strategy_scores['primary_strategy']} "
                f"(榫欏ご {strategy_scores['leader_model_score']:.0f} / 涓诲姏 {strategy_scores['main_force_score']:.0f} / "
                f"鎵撴澘 {strategy_scores['board_attack_score']:.0f} / 浣庡惛 {strategy_scores['value_recovery_score']:.0f} / "
                f"鍐崇瓥 {strategy_scores['dragon_decision_score']:.0f})"
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
                    news_score=news_score,
                    leader_score=leader_score,
                    total_score=total_score,
                    theme_name=theme_name,
                    primary_strategy=strategy_scores["primary_strategy"],
                    leader_model_score=strategy_scores["leader_model_score"],
                    main_force_score=strategy_scores["main_force_score"],
                    board_attack_score=strategy_scores["board_attack_score"],
                    value_recovery_score=strategy_scores["value_recovery_score"],
                    dragon_decision_score=strategy_scores["dragon_decision_score"],
                    catalyst=catalyst,
                    rationale=" | ".join(reasons),
                )
            )

        themed_candidates, theme_rows, leader_rows = ThemeHeatEngine(theme_aliases=self.theme_aliases).analyze(candidates)
        themed_candidates.sort(
            key=lambda item: (item.total_score, item.theme_score, item.technical_score, item.persistence_score, item.stock_id),
            reverse=True,
        )
        self.last_theme_rows = theme_rows
        self.last_leader_rows = leader_rows
        return themed_candidates[:top_n]

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
        dragon_decision_score = min(
            99.0,
            leader_model_score * 0.24
            + main_force_score * 0.18
            + board_attack_score * 0.16
            + value_recovery_score * 0.16
            + technical_score * 0.08
            + position_score * 0.07
            + persistence_score * 0.06
            + news_score * 0.05,
        )
        ranked = [
            ("龙头模型", leader_model_score),
            ("主力雷达", main_force_score),
            ("擒龙打板", board_attack_score),
            ("价值低吸", value_recovery_score),
            ("掘龙决策", dragon_decision_score),
        ]
        ranked.sort(key=lambda item: item[1], reverse=True)
        return {
            "primary_strategy": ranked[0][0],
            "leader_model_score": round(leader_model_score, 2),
            "main_force_score": round(main_force_score, 2),
            "board_attack_score": round(board_attack_score, 2),
            "value_recovery_score": round(value_recovery_score, 2),
            "dragon_decision_score": round(dragon_decision_score, 2),
        }
