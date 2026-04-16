from __future__ import annotations

from dataclasses import replace
import re

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


_GENERIC_THEME_LABELS = {
    "未分类",
    "未知",
    "其他",
    "题材",
    "主线",
    "热点",
    "general",
    "theme",
    "concept",
}


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().split())


def _looks_like_theme_label(value: str) -> bool:
    text = _normalize_text(value)
    if not text:
        return False
    lowered = text.lower()
    if lowered in _GENERIC_THEME_LABELS:
        return False
    if any(sep in text for sep in ("|", "/", "\\", ",", ";", ":", "(", ")", "[", "]", "{", "}")):
        return False
    if len(text) > 16:
        return False
    if len(text) > 10 and any(ch.isdigit() for ch in text):
        return False
    if re.search(r"\s{2,}", value):
        return False
    return True


def _match_theme_keyword(value: str, alias_map: dict[str, tuple[str, ...]]) -> str | None:
    lowered = value.lower()
    best_match: tuple[int, str] | None = None
    for theme_name, keywords in alias_map.items():
        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower and keyword_lower in lowered:
                candidate = (len(keyword_lower), theme_name)
                if best_match is None or candidate[0] > best_match[0]:
                    best_match = candidate
    return best_match[1] if best_match else None


def infer_theme_name(*parts: str, theme_aliases: dict[str, tuple[str, ...]] | None = None) -> str:
    normalized_parts = [part.strip() for part in parts if part and part.strip()]
    if not normalized_parts:
        return "未分类"

    alias_map = theme_aliases or DEFAULT_THEME_KEYWORDS
    for part in normalized_parts:
        matched = _match_theme_keyword(part, alias_map)
        if matched:
            return matched

    for part in normalized_parts:
        if _looks_like_theme_label(part):
            return part
    return "未分类"


def infer_mainline_stage(
    theme_rank: int,
    strength_score: float,
    continuation_score: float,
    divergence_score: float,
    failure_risk: float,
    window_score: float,
    mainline_role: str = "",
) -> str:
    if mainline_role in {"NOISE", "ELIMINATED"} or failure_risk >= 70.0 or window_score < 46.0:
        return "退潮"
    if divergence_score >= 60.0 or (failure_risk >= 58.0 and window_score < 62.0):
        return "分歧"
    if (
        theme_rank <= 3
        and window_score >= 82.0
        and continuation_score >= 64.0
        and divergence_score <= 46.0
        and failure_risk <= 48.0
        and strength_score >= 72.0
    ):
        return "加速"
    if (
        theme_rank <= 4
        and window_score >= 58.0
        and continuation_score >= 50.0
        and strength_score >= 66.0
        and failure_risk <= 60.0
    ):
        return "启动"
    if divergence_score >= 50.0 or failure_risk >= 55.0:
        return "分歧"
    return "观察"


def infer_mainline_flow_signal(
    theme_rank: int,
    strength_score: float,
    continuation_score: float,
    divergence_score: float,
    failure_risk: float,
    window_score: float,
    mainline_role: str = "",
) -> str:
    stage_label = infer_mainline_stage(
        theme_rank=theme_rank,
        strength_score=strength_score,
        continuation_score=continuation_score,
        divergence_score=divergence_score,
        failure_risk=failure_risk,
        window_score=window_score,
        mainline_role=mainline_role,
    )
    if stage_label == "退潮" or mainline_role in {"NOISE", "ELIMINATED"} or failure_risk >= 72.0 or window_score < 48.0:
        return "切换/退潮"
    if stage_label == "分歧" or divergence_score >= 60.0 or (failure_risk >= 58.0 and continuation_score < 60.0):
        return "切换预警"
    if (
        stage_label == "加速"
        and continuation_score >= 66.0
        and divergence_score <= 42.0
        and failure_risk <= 46.0
        and window_score >= 80.0
    ):
        return "延续偏强"
    if stage_label == "启动" and continuation_score >= 54.0 and divergence_score <= 52.0 and failure_risk <= 58.0:
        return "延续待确认"
    if theme_rank <= 3 and continuation_score >= 58.0 and window_score >= 62.0 and divergence_score <= 50.0:
        return "延续可跟踪"
    return "延续观察"


def display_mainline_role(role: str) -> str:
    return {
        "CORE": "\u6838\u5fc3\u9f99\u5934",
        "FRONT": "\u524d\u6392\u6838\u5fc3",
        "ASSIST": "\u52a9\u653b\u524d\u6392",
        "FOLLOW": "\u8ddf\u98ce\u89c2\u5bdf",
        "NOISE": "\u6742\u6bdb\u566a\u58f0",
        "ELIMINATED": "\u6dd8\u6c70\u98ce\u9669",
    }.get(role or "", role or "--")


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
                theme_name=infer_theme_name(item.theme_name, item.catalyst, theme_aliases=self.theme_aliases),
            )
            for item in recommendations
        ]

        grouped: dict[str, list[RecommendationRow]] = {}
        for item in normalized_rows:
            theme_name = item.theme_name.strip() or "未分类"
            grouped.setdefault(theme_name, []).append(item)

        theme_rows: list[ThemeHeatRow] = []
        ranked_groups: list[dict[str, object]] = []
        for theme_name, items in grouped.items():
            sorted_items = sorted(
                items,
                key=lambda item: (item.total_score, item.leader_score, item.technical_score, item.news_score),
                reverse=True,
            )
            avg_total = sum(item.total_score for item in items) / len(items)
            avg_technical = sum(item.technical_score for item in items) / len(items)
            avg_persistence = sum(item.persistence_score for item in items) / len(items)
            avg_news = sum(item.news_score for item in items) / len(items)
            avg_leader = sum(item.leader_score for item in items) / len(items)
            buy_ratio = sum(1 for item in items if item.action == "BUY") / len(items)
            leader_count = sum(1 for item in items if item.leader_score >= 80)
            front_slice = sorted_items[:2]
            tail_slice = sorted_items[2:] or sorted_items[-1:]
            front_avg = sum(item.total_score for item in front_slice) / len(front_slice)
            tail_avg = sum(item.total_score for item in tail_slice) / len(tail_slice)
            front_gap = max(front_avg - tail_avg, 0.0)
            dispersion = sum(abs(item.total_score - avg_total) for item in items) / len(items)
            strength_score = self._clamp(
                avg_total * 0.30
                + avg_technical * 0.14
                + avg_persistence * 0.12
                + avg_news * 0.10
                + avg_leader * 0.08
                + buy_ratio * 18.0
                + min(len(items), 5) * 1.5,
                28.0,
                98.0,
            )
            continuation_score = self._clamp(
                avg_persistence * 0.42
                + avg_total * 0.18
                + avg_technical * 0.12
                + avg_leader * 0.08
                + buy_ratio * 12.0
                + leader_count * 4.0,
                24.0,
                97.0,
            )
            divergence_score = self._clamp(
                front_gap * 0.95
                + dispersion * 1.05
                + (1.0 - buy_ratio) * 20.0
                + max(0.0, 72.0 - avg_persistence) * 0.28,
                18.0,
                95.0,
            )
            failure_risk = self._clamp(
                78.0
                - strength_score * 0.34
                - continuation_score * 0.22
                - buy_ratio * 16.0
                + divergence_score * 0.36
                + max(0, 3 - leader_count) * 3.2,
                8.0,
                95.0,
            )
            ranked_groups.append(
                {
                    "theme_name": theme_name,
                    "items": sorted_items,
                    "strength_score": round(strength_score, 2),
                    "continuation_score": round(continuation_score, 2),
                    "news_score": round(avg_news, 2),
                    "leader_count": leader_count,
                    "stock_count": len(items),
                    "divergence_score": round(divergence_score, 2),
                    "failure_risk": round(failure_risk, 2),
                    "buy_ratio": round(buy_ratio, 4),
                }
            )

        ranked_groups.sort(
            key=lambda item: (
                float(item["strength_score"]),
                float(item["continuation_score"]),
                float(item["news_score"]),
                int(item["leader_count"]),
            ),
            reverse=True,
        )
        rank_map: dict[str, int] = {}
        strength_map: dict[str, float] = {}
        continuation_map: dict[str, float] = {}
        divergence_map: dict[str, float] = {}
        failure_risk_map: dict[str, float] = {}
        rotation_map: dict[str, float] = {}
        window_map: dict[str, float] = {}
        risk_flag_map: dict[str, str] = {}
        top_strength = float(ranked_groups[0]["strength_score"]) if ranked_groups else 0.0
        top_failure = float(ranked_groups[0]["failure_risk"]) if ranked_groups else 0.0
        second_strength = float(ranked_groups[1]["strength_score"]) if len(ranked_groups) > 1 else top_strength
        for index, row in enumerate(ranked_groups, start=1):
            theme_name = str(row["theme_name"])
            strength_score = float(row["strength_score"])
            continuation_score = float(row["continuation_score"])
            news_score = float(row["news_score"])
            leader_count = int(row["leader_count"])
            stock_count = int(row["stock_count"])
            divergence_score = float(row["divergence_score"])
            failure_risk = float(row["failure_risk"])
            buy_ratio = float(row["buy_ratio"])
            if index == 1:
                gap_to_next = max(strength_score - second_strength, 0.0)
                rotation_score = self._clamp(
                    failure_risk * 0.52 + divergence_score * 0.24 + max(0.0, 10.0 - gap_to_next) * 2.1,
                    10.0,
                    95.0,
                )
            else:
                gap_to_top = max(top_strength - strength_score, 0.0)
                rotation_score = self._clamp(
                    continuation_score * 0.22
                    + max(0.0, 14.0 - gap_to_top) * 2.4
                    + top_failure * 0.28
                    - failure_risk * 0.14,
                    10.0,
                    95.0,
                )
            window_score = self._clamp(
                strength_score * 0.42
                + continuation_score * 0.30
                + buy_ratio * 16.0
                - divergence_score * 0.18
                - failure_risk * 0.16,
                12.0,
                98.0,
            )
            risk_flag = self._risk_flag(failure_risk, divergence_score)
            rank_map[theme_name] = index
            strength_map[theme_name] = strength_score
            continuation_map[theme_name] = continuation_score
            divergence_map[theme_name] = round(divergence_score, 2)
            failure_risk_map[theme_name] = round(failure_risk, 2)
            rotation_map[theme_name] = round(rotation_score, 2)
            window_map[theme_name] = round(window_score, 2)
            risk_flag_map[theme_name] = risk_flag
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
                    divergence_score=round(divergence_score, 2),
                    failure_risk=round(failure_risk, 2),
                    rotation_score=round(rotation_score, 2),
                    window_score=round(window_score, 2),
                    is_primary=index == 1,
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
                divergence_score = divergence_map[theme_name]
                failure_risk = failure_risk_map[theme_name]
                rotation_score = rotation_map[theme_name]
                theme_window_score = window_map[theme_name]
                leader_position_score = self._clamp(
                    (102.0 - (index - 1) * 14.0) * 0.46
                    + item.leader_score * 0.28
                    + item.technical_score * 0.14
                    + item.news_score * 0.12
                    + (6.0 if item.action == "BUY" else 0.0),
                    20.0,
                    98.0,
                )
                mainline_role = self._mainline_role(
                    index=index,
                    item=item,
                    theme_rank=theme_rank,
                    leader_position_score=leader_position_score,
                    theme_window_score=theme_window_score,
                    theme_failure_risk=failure_risk,
                )
                leader_level = self._leader_level_from_role(mainline_role)
                role_bonus = {
                    "CORE": 8.0,
                    "FRONT": 5.0,
                    "ASSIST": 2.0,
                    "FOLLOW": 0.0,
                    "NOISE": -4.0,
                    "ELIMINATED": -8.0,
                }[mainline_role]
                mainline_window_score = self._clamp(
                    theme_window_score * 0.54
                    + leader_position_score * 0.24
                    + item.position_score * 0.08
                    + item.technical_score * 0.08
                    + role_bonus
                    - (6.0 if item.action not in {"BUY", "HOLD"} else 0.0)
                    - theme_rank * 0.6,
                    10.0,
                    98.0,
                )
                stage_label = infer_mainline_stage(
                    theme_rank=theme_rank,
                    strength_score=theme_score,
                    continuation_score=continuation_score,
                    divergence_score=divergence_score,
                    failure_risk=failure_risk,
                    window_score=mainline_window_score,
                    mainline_role=mainline_role,
                )
                flow_signal = infer_mainline_flow_signal(
                    theme_rank=theme_rank,
                    strength_score=theme_score,
                    continuation_score=continuation_score,
                    divergence_score=divergence_score,
                    failure_risk=failure_risk,
                    window_score=mainline_window_score,
                    mainline_role=mainline_role,
                )
                risk_penalty = (
                    failure_risk * 0.06
                    + divergence_score * 0.04
                    + (3.0 if mainline_role in {"NOISE", "ELIMINATED"} else 0.0)
                    + (2.0 if item.action != "BUY" else 0.0)
                )
                total_score = self._clamp(
                    item.total_score * 0.56
                    + theme_score * 0.12
                    + continuation_score * 0.08
                    + leader_position_score * 0.12
                    + mainline_window_score * 0.08
                    + role_bonus
                    - risk_penalty,
                    30.0,
                    99.0,
                )
                rationale = (
                    f"{item.rationale} | 题材 {theme_name} 第 {theme_rank} 位 | "
                    f"阶段 {stage_label} | 信号 {flow_signal} | 主线强度 {theme_score:.1f} | 延续 {continuation_score:.1f} | "
                    f"角色 {mainline_role} | 窗口 {mainline_window_score:.1f} | 风险 {risk_flag_map[theme_name]}"
                )
                updated = replace(
                    item,
                    total_score=round(total_score, 2),
                    theme_name=theme_name,
                    theme_score=theme_score,
                    theme_rank=theme_rank,
                    leader_level=leader_level,
                    mainline_tag=theme_name,
                    mainline_rank=theme_rank,
                    mainline_role=mainline_role,
                    mainline_strength_score=theme_score,
                    mainline_continuation_score=continuation_score,
                    leader_position_score=round(leader_position_score, 2),
                    mainline_window_score=round(mainline_window_score, 2),
                    theme_divergence_score=round(divergence_score, 2),
                    theme_failure_risk=round(failure_risk, 2),
                    theme_rotation_score=round(rotation_score, 2),
                    mainline_risk_flag=risk_flag_map[theme_name],
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
                            mainline_role=updated.mainline_role,
                            mainline_window_score=updated.mainline_window_score,
                            mainline_risk_flag=updated.mainline_risk_flag,
                        )
                    )

        enriched.sort(
            key=lambda item: (
                item.mainline_rank == 0,
                item.mainline_rank or 99,
                self._flow_signal_priority(
                    infer_mainline_flow_signal(
                        theme_rank=item.mainline_rank or item.theme_rank or 0,
                        strength_score=item.mainline_strength_score or item.theme_score or item.total_score,
                        continuation_score=item.mainline_continuation_score,
                        divergence_score=item.theme_divergence_score,
                        failure_risk=item.theme_failure_risk,
                        window_score=item.mainline_window_score,
                        mainline_role=item.mainline_role,
                    )
                ),
                -item.mainline_window_score,
                self._mainline_role_priority(item.mainline_role),
                -item.total_score,
                -item.leader_position_score,
                item.stock_id,
            )
        )
        leader_rows.sort(
            key=lambda item: (
                item.theme_rank,
                self._mainline_role_priority(item.mainline_role),
                -item.mainline_window_score,
                -item.leader_score,
                item.stock_id,
            )
        )
        return enriched, theme_rows[:top_n_themes], leader_rows[:top_n_leaders]

    @staticmethod
    def _mainline_role(
        index: int,
        item: RecommendationRow,
        theme_rank: int,
        leader_position_score: float,
        theme_window_score: float,
        theme_failure_risk: float,
    ) -> str:
        if (
            theme_rank <= 3
            and index == 1
            and item.leader_score >= 82
            and item.action == "BUY"
            and theme_window_score >= 62
        ):
            return "CORE"
        if (
            theme_rank <= 3
            and index <= 2
            and leader_position_score >= 78
            and item.action == "BUY"
            and theme_failure_risk <= 62
        ):
            return "FRONT"
        if theme_rank <= 5 and index <= 3 and item.total_score >= 72:
            return "ASSIST"
        if theme_rank <= 6 and item.total_score >= 64:
            return "FOLLOW"
        if theme_rank <= 8 and item.total_score >= 58 and theme_failure_risk <= 78:
            return "NOISE"
        return "ELIMINATED"

    @staticmethod
    def _mainline_role_priority(role: str) -> int:
        return {
            "CORE": 0,
            "FRONT": 1,
            "ASSIST": 2,
            "FOLLOW": 3,
            "NOISE": 4,
            "ELIMINATED": 5,
        }.get(role, 9)

    @staticmethod
    def _flow_signal_priority(signal: str) -> int:
        return {
            "延续偏强": 0,
            "延续待确认": 1,
            "延续可跟踪": 2,
            "延续观察": 3,
            "切换预警": 4,
            "切换/退潮": 5,
        }.get(signal, 9)

    @staticmethod
    def _leader_level_from_role(role: str) -> str:
        return {
            "CORE": "CORE_LEADER",
            "FRONT": "ACTIVE_LEADER",
            "ASSIST": "ACTIVE_LEADER",
            "FOLLOW": "FOLLOWER",
            "NOISE": "NOISE",
            "ELIMINATED": "NOISE",
        }.get(role, "NOISE")

    @staticmethod
    def _risk_flag(failure_risk: float, divergence_score: float) -> str:
        if failure_risk <= 28 and divergence_score <= 40:
            return "低"
        if failure_risk <= 55:
            return "中"
        return "高"

    @staticmethod
    def _clamp(value: float, lower: float, upper: float) -> float:
        return max(lower, min(value, upper))

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
