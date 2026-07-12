"""RoadmapOutputをDiscord向けMarkdownテキストに整形する。"""

import datetime

from llm import RoadmapOutput


def format_roadmap(roadmap: RoadmapOutput, goal: dict | None = None) -> str:
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    lines = [f"**🚁 週次ロードマップ({today_str})**"]

    if goal:
        days = goal.get("days_remaining")
        days_str = f"残り{days}日" if days is not None else "日程未定"
        imminent = " ⚠️直前" if goal.get("is_imminent") else ""
        lines.append(f"🎯 目標: {goal.get('competition_name', '')}({days_str}){imminent}")

    lines.append("\n**▶️ 今週の注力ポイント**")
    for focus in roadmap.roadmap:
        lines.append(f"* **{focus.focus}**")
        for task_id in focus.tasks:
            lines.append(f"  - {task_id}")

    if roadmap.assignments:
        lines.append("\n**👤 アサイン**")
        for a in roadmap.assignments:
            lines.append(f"* {a.member} → {a.task}")
            lines.append(f"  理由: {a.reason}")

    if roadmap.risks:
        lines.append("\n**⚠️ リスク**")
        for r in roadmap.risks:
            lines.append(f"* {r}")

    lines.append("\n**🧭 なぜこの優先順位か**")
    lines.append(roadmap.priority_reasoning)

    return "\n".join(lines)
