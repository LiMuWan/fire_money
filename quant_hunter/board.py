from __future__ import annotations

from dataclasses import dataclass, field

from .models import RecommendationRow


@dataclass(frozen=True)
class BoardCandidate:
    symbol: str
    stock_id: str
    stock_name: str
    board_score: float
    momentum_score: float
    liquidity_score: float
    leader_score: float
    trigger_style: str
    risk_level: str
    planned_entry: float
    planned_stop: float
    planned_target: float
    rationale: str


@dataclass(frozen=True)
class BoardMonitorRow:
    symbol: str
    stock_id: str
    stock_name: str
    monitor_state: str
    strength_score: float
    continuity_score: float
    reboard_probability: float
    blast_risk: float
    action_plan: str
    note: str


@dataclass(frozen=True)
class BoardPlan:
    temperature: str
    avg_score: float
    candidates: list[BoardCandidate] = field(default_factory=list)
    monitor_rows: list[BoardMonitorRow] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


class BoardModeEngine:
    def build(self, recommendations: list[RecommendationRow], top_n: int = 5) -> BoardPlan:
        candidates: list[BoardCandidate] = []
        monitor_rows: list[BoardMonitorRow] = []

        for row in recommendations:
            if row.action != "BUY":
                continue

            momentum_score = min(96.0, row.technical_score * 0.55 + row.persistence_score * 0.45)
            liquidity_score = min(94.0, row.news_score * 0.35 + row.position_score * 0.65)
            leader_score = row.leader_score
            board_score = round(
                momentum_score * 0.45 + liquidity_score * 0.25 + leader_score * 0.15 + row.news_score * 0.15,
                2,
            )

            if board_score >= 84 and row.position_score >= 78:
                trigger_style = "强更强"
                risk_level = "中"
            elif row.news_score >= 62 and row.persistence_score >= 70:
                trigger_style = "回封确认"
                risk_level = "中高"
            else:
                trigger_style = "分歧转一致"
                risk_level = "高"

            planned_entry = row.entry_price or row.close
            planned_stop = row.stop_price or planned_entry * 0.96
            planned_target = row.target_price or planned_entry * 1.12
            rationale = (
                f"技术 {row.technical_score:.0f} / 持续 {row.persistence_score:.0f} / "
                f"消息 {row.news_score:.0f} / 龙头 {leader_score:.0f}"
            )

            if board_score >= 70:
                candidates.append(
                    BoardCandidate(
                        symbol=row.symbol,
                        stock_id=row.stock_id,
                        stock_name=row.stock_name,
                        board_score=board_score,
                        momentum_score=round(momentum_score, 2),
                        liquidity_score=round(liquidity_score, 2),
                        leader_score=round(leader_score, 2),
                        trigger_style=trigger_style,
                        risk_level=risk_level,
                        planned_entry=planned_entry,
                        planned_stop=planned_stop,
                        planned_target=planned_target,
                        rationale=rationale,
                    )
                )

            monitor_rows.append(self._build_monitor_row(row, board_score, trigger_style))

        candidates.sort(key=lambda item: (item.board_score, item.momentum_score, item.stock_id), reverse=True)
        selected = candidates[:top_n]
        avg_score = round(sum(item.board_score for item in selected) / len(selected), 2) if selected else 0.0

        monitor_rows.sort(
            key=lambda item: (self._monitor_priority(item.monitor_state), item.strength_score, item.reboard_probability),
            reverse=True,
        )
        monitor_rows = monitor_rows[: max(top_n + 3, 6)]

        if avg_score >= 84:
            temperature = "积极试错"
        elif avg_score >= 76:
            temperature = "轻仓参与"
        elif avg_score > 0:
            temperature = "先观察"
        else:
            temperature = "暂停出手"

        blast_risk_count = sum(1 for item in monitor_rows if item.monitor_state == "炸板风险")
        reboard_count = sum(1 for item in monitor_rows if item.monitor_state == "回封观察")
        leader_count = sum(1 for item in selected if item.leader_score >= 80)
        notes = [
            "打板模式优先跟踪强势龙头、回封确认和分歧转一致，不做弱势尾盘跟风票。",
            f"当前监控里回封观察 {reboard_count} 只、炸板风险 {blast_risk_count} 只，优先做最强且最清晰的标的。",
            f"入选候选中具备龙头属性的个股 {leader_count} 只，若板块联动增强可提高关注度。",
        ]
        if not selected:
            notes.append("当前没有达到打板阈值的候选，建议等待更强确认信号。")

        return BoardPlan(
            temperature=temperature,
            avg_score=avg_score,
            candidates=selected,
            monitor_rows=monitor_rows,
            notes=notes,
        )

    def _build_monitor_row(
        self,
        row: RecommendationRow,
        board_score: float,
        trigger_style: str,
    ) -> BoardMonitorRow:
        strength_score = round(board_score, 2)
        continuity_score = round(row.persistence_score * 0.45 + row.leader_score * 0.3 + row.news_score * 0.25, 2)
        reboard_probability = round(
            min(
                95.0,
                row.persistence_score * 0.42
                + row.news_score * 0.18
                + row.leader_score * 0.2
                + max(0.0, 85.0 - abs(row.position_score - 76.0)) * 0.2,
            ),
            2,
        )
        blast_risk = round(
            max(
                18.0,
                100.0
                - (
                    row.position_score * 0.38
                    + row.persistence_score * 0.27
                    + row.news_score * 0.15
                    + row.leader_score * 0.2
                ),
            ),
            2,
        )

        if strength_score >= 84 and blast_risk <= 36 and continuity_score >= 75:
            monitor_state = "强势连板候选"
            action_plan = "板上量价配合时可以跟踪，优先做前排。"
        elif reboard_probability >= 70:
            monitor_state = "回封观察"
            action_plan = "等分时回封并缩量确认，再考虑试错。"
        elif blast_risk >= 62:
            monitor_state = "炸板风险"
            action_plan = "只观察，不抢回封；若冲高回落需快速规避。"
        else:
            monitor_state = "分歧待确认"
            action_plan = "等待板块共振或分时承接增强后再看。"

        note = f"{trigger_style} | 催化: {row.catalyst or '暂无明显外部催化'}"
        return BoardMonitorRow(
            symbol=row.symbol,
            stock_id=row.stock_id,
            stock_name=row.stock_name,
            monitor_state=monitor_state,
            strength_score=strength_score,
            continuity_score=continuity_score,
            reboard_probability=reboard_probability,
            blast_risk=blast_risk,
            action_plan=action_plan,
            note=note,
        )

    @staticmethod
    def _monitor_priority(state: str) -> int:
        return {
            "强势连板候选": 4,
            "回封观察": 3,
            "分歧待确认": 2,
            "炸板风险": 1,
        }.get(state, 0)
