from __future__ import annotations

from dataclasses import replace

from .models import LeaderCandidate, RecommendationRow, ThemeHeatRow


DEFAULT_THEME_KEYWORDS: dict[str, tuple[str, ...]] = {
    "银行": ("银行", "金融", "信贷", "券商", "保险"),
    "半导体": ("芯片", "半导体", "封装", "算力", "存储"),
    "人工智能": ("ai", "人工智能", "大模型", "机器人", "智能"),
    "新能源": ("光伏", "储能", "锂电", "新能源", "电池"),
    "军工": ("军工", "航空", "航天", "卫星", "国防"),
    "医药": ("医药", "创新药", "医疗", "器械", "生物"),
    "消费": ("消费", "零售", "食品", "饮料", "家电"),
    "地产基建": ("地产", "基建", "建筑", "水泥", "城投"),
    "有色资源": ("黄金", "铜", "稀土", "有色", "资源"),
}


def infer_theme_name(*parts: str, theme_aliases: dict[str, tuple[str, ...]] | None = None) -> str:
    normalized_parts = [part.strip() for part in parts if part and part.strip()]
    if not normalized_parts:
        return "未分类"

    alias_map = theme_aliases or DEFAULT_THEME_KEYWORDS
    lowered = " ".join(normalized_parts).lower()
    for theme_name, keywords in alias_map.items():
        if any(keyword.lower() in lowered for keyword in keywords):
            return theme_name
    return normalized_parts[0]


class ThemeHeatEngine:
    def __init__(self, theme_aliases: dict[str, tuple[str, ...]] | None = None) -> None:
        self.theme_aliases = theme_aliases or DEFAULT_THEME_KEYWORDS

    def analyze(
        self,
        recommendations: list[RecommendationRow],
        top_n_themes: int = 8,
        top_n_leaders: int = 8,
    ) -> tuple[list[RecommendationRow], list[ThemeHeatRow], list[LeaderCandidate]]:
        if not recommendations:
            return [], [], []

        normalized_rows = [
            replace(
                item,
                theme_name=infer_theme_name(item.theme_name, item.catalyst, item.rationale, theme_aliases=self.theme_aliases),
            )
            for item in recommendations
        ]

        grouped: dict[str, list[RecommendationRow]] = {}
        for item in normalized_rows:
            theme_name = item.theme_name.strip() or "未分类"
            grouped.setdefault(theme_name, []).append(item)

        theme_rows: list[ThemeHeatRow] = []
        ranked_groups: list[tuple[str, float, float, float, int, int, str]] = []
        for theme_name, items in grouped.items():
            avg_total = sum(item.total_score for item in items) / len(items)
            avg_technical = sum(item.technical_score for item in items) / len(items)
            avg_persistence = sum(item.persistence_score for item in items) / len(items)
            avg_news = sum(item.news_score for item in items) / len(items)
            buy_ratio = sum(1 for item in items if item.action == "BUY") / len(items)
            leader_count = sum(1 for item in items if item.leader_score >= 80)
            strength_score = min(
                98.0,
                avg_total * 0.35 + avg_technical * 0.2 + avg_persistence * 0.15 + avg_news * 0.1 + buy_ratio * 18.0,
            )
            continuation_score = min(96.0, avg_persistence * 0.55 + avg_technical * 0.15 + avg_total * 0.15 + leader_count * 5.0)
            composite = strength_score * 0.55 + continuation_score * 0.25 + avg_news * 0.2
            if composite >= 82:
                risk_flag = "低"
            elif composite >= 68:
                risk_flag = "中"
            else:
                risk_flag = "高"
            ranked_groups.append(
                (
                    theme_name,
                    round(strength_score, 2),
                    round(continuation_score, 2),
                    round(avg_news, 2),
                    leader_count,
                    len(items),
                    risk_flag,
                )
            )

        ranked_groups.sort(key=lambda item: (item[1], item[2], item[3], item[4]), reverse=True)
        rank_map: dict[str, int] = {}
        strength_map: dict[str, float] = {}
        continuation_map: dict[str, float] = {}
        for index, row in enumerate(ranked_groups, start=1):
            theme_name, strength_score, continuation_score, news_score, leader_count, stock_count, risk_flag = row
            rank_map[theme_name] = index
            strength_map[theme_name] = strength_score
            continuation_map[theme_name] = continuation_score
            theme_rows.append(
                ThemeHeatRow(
                    theme_name=theme_name,
                    strength_score=strength_score,
                    continuation_score=continuation_score,
                    news_score=news_score,
                    leader_count=leader_count,
                    stock_count=stock_count,
                    theme_rank=index,
                    risk_flag=risk_flag,
                )
            )

        enriched: list[RecommendationRow] = []
        leader_rows: list[LeaderCandidate] = []
        for theme_name, items in grouped.items():
            sorted_items = sorted(
                items,
                key=lambda item: (item.total_score, item.leader_score, item.technical_score, item.news_score),
                reverse=True,
            )
            for index, item in enumerate(sorted_items, start=1):
                theme_rank = rank_map[theme_name]
                theme_score = strength_map[theme_name]
                continuation_score = continuation_map[theme_name]
                leader_level = self._leader_level(index=index, item=item, theme_rank=theme_rank)
                risk_penalty = 5.0 if theme_rank > 5 and item.position_score < 60 else 0.0
                leader_component = {
                    "CORE_LEADER": 92.0,
                    "ACTIVE_LEADER": 80.0,
                    "FOLLOWER": 64.0,
                    "NOISE": 48.0,
                }[leader_level]
                theme_rank_bonus = 3.5 if theme_rank <= 3 else (1.5 if theme_rank <= 5 else 0.0)
                total_score = (
                    item.technical_score * 0.20
                    + item.position_score * 0.15
                    + item.persistence_score * 0.15
                    + item.news_score * 0.10
                    + theme_score * 0.20
                    + continuation_score * 0.05
                    + leader_component * 0.15
                    - risk_penalty
                    + theme_rank_bonus
                )
                total_score = min(99.0, max(30.0, total_score))
                rationale = (
                    f"{item.rationale} | 题材 {theme_name} 排名第 {theme_rank} | "
                    f"题材热度 {theme_score:.1f} | 龙头级别 {self._display_leader_level(leader_level)}"
                )
                updated = replace(
                    item,
                    total_score=round(total_score, 2),
                    theme_name=theme_name,
                    theme_score=theme_score,
                    theme_rank=theme_rank,
                    leader_level=leader_level,
                    rationale=rationale,
                )
                enriched.append(updated)
                if leader_level in {"CORE_LEADER", "ACTIVE_LEADER"}:
                    leader_rows.append(
                        LeaderCandidate(
                            symbol=updated.symbol,
                            stock_id=updated.stock_id,
                            stock_name=updated.stock_name,
                            theme_name=theme_name,
                            leader_level=leader_level,
                            leader_score=round(updated.leader_score, 2),
                            theme_rank=theme_rank,
                            action=updated.action,
                            rationale=updated.rationale,
                        )
                    )

        enriched.sort(
            key=lambda item: (
                item.total_score,
                item.theme_score,
                -item.theme_rank,
                item.leader_score,
                item.technical_score,
                item.stock_id,
            ),
            reverse=True,
        )
        leader_rows.sort(
            key=lambda item: (
                self._leader_priority(item.leader_level),
                item.theme_rank,
                -item.leader_score,
                item.stock_id,
            )
        )
        return enriched, theme_rows[:top_n_themes], leader_rows[:top_n_leaders]

    @staticmethod
    def _leader_level(index: int, item: RecommendationRow, theme_rank: int) -> str:
        if index == 1 and item.leader_score >= 80 and theme_rank <= 5:
            return "CORE_LEADER"
        if index <= 2 or item.leader_score >= 74:
            return "ACTIVE_LEADER"
        if item.total_score >= 65:
            return "FOLLOWER"
        return "NOISE"

    @staticmethod
    def _leader_priority(level: str) -> int:
        return {
            "CORE_LEADER": 0,
            "ACTIVE_LEADER": 1,
            "FOLLOWER": 2,
            "NOISE": 3,
        }.get(level, 9)

    @staticmethod
    def _display_leader_level(level: str) -> str:
        return {
            "CORE_LEADER": "核心龙头",
            "ACTIVE_LEADER": "活跃龙头",
            "FOLLOWER": "跟风股",
            "NOISE": "噪声",
        }.get(level, level)


def summarize_themes(
    recommendations: list[RecommendationRow],
    top_n_themes: int = 5,
    top_n_leaders: int = 5,
    theme_aliases: dict[str, tuple[str, ...]] | None = None,
) -> tuple[list[ThemeHeatRow], list[LeaderCandidate]]:
    _, theme_rows, leader_rows = ThemeHeatEngine(theme_aliases=theme_aliases).analyze(
        recommendations,
        top_n_themes=top_n_themes,
        top_n_leaders=top_n_leaders,
    )
    return theme_rows, leader_rows
