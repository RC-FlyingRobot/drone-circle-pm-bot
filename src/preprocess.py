"""事実の集計(AIを使わない前処理)。

シートから読み込んだ生データを、Geminiに渡すための「事実サマリ」に変換する。
クリティカルパス算出・停滞検知・メンバー稼働状況・大会までの残日数を、ここでPythonだけで計算する。
"""

import datetime

import networkx as nx

import config


def build_dependency_graph(tasks: list[dict]) -> nx.DiGraph:
    """依存タスクIDを辺として持つ有向グラフを構築する。

    エッジの向きは 依存先 -> 依存元(そのタスク自身)。依存先が終わらないと着手できない、という関係を表す。
    """
    graph = nx.DiGraph()
    for task in tasks:
        task_id = (task.get("task_id") or "").strip()
        if not task_id:
            continue
        graph.add_node(
            task_id,
            remaining_hours=_to_float(task.get("remaining_hours")),
            task=task,
        )

    for task in tasks:
        task_id = (task.get("task_id") or "").strip()
        if not task_id:
            continue
        for dep_id in _split_ids(task.get("dependency_ids") or ""):
            if dep_id not in graph:
                # 依存先が未登録(完了済みで対象外、または表記ミス)のIDでも落ちないようにする
                graph.add_node(dep_id, remaining_hours=0.0, task=None)
            graph.add_edge(dep_id, task_id)

    return graph


def critical_path(tasks: list[dict]) -> dict:
    """残工数を重みとしたクリティカルパス(最長経路)を算出する。完了タスクは対象外。"""
    active_tasks = [t for t in tasks if t.get("status") != config.STATUS_DONE]
    graph = build_dependency_graph(active_tasks)

    if graph.number_of_nodes() == 0:
        return {"path": [], "total_hours": 0.0}

    if not nx.is_directed_acyclic_graph(graph):
        # 壊れたデータ(循環依存)でも落ちないよう、サイクルを構成するノードを除いてDAG化する
        cycle_nodes: set[str] = set()
        for cycle in nx.simple_cycles(graph):
            cycle_nodes.update(cycle)
        graph.remove_nodes_from(cycle_nodes)

    if graph.number_of_nodes() == 0:
        return {"path": [], "total_hours": 0.0}

    order = list(nx.topological_sort(graph))
    longest = {node: graph.nodes[node]["remaining_hours"] for node in order}
    predecessor: dict[str, str | None] = {node: None for node in order}

    for node in order:
        for succ in graph.successors(node):
            candidate = longest[node] + graph.nodes[succ]["remaining_hours"]
            if candidate > longest[succ]:
                longest[succ] = candidate
                predecessor[succ] = node

    end_node = max(longest, key=longest.get)
    path = []
    node: str | None = end_node
    while node is not None:
        path.append(node)
        node = predecessor[node]
    path.reverse()

    return {"path": path, "total_hours": longest[end_node]}


def detect_stalled(tasks: list[dict]) -> list[dict]:
    """ボトルネック理由が「なし」以外で、未完了のタスクを停滞タスクとして抽出する。"""
    stalled = []
    for task in tasks:
        if task.get("status") == config.STATUS_DONE:
            continue
        reason = (task.get("bottleneck_reason") or "").strip()
        if reason and reason != config.BOTTLENECK_NONE:
            stalled.append(
                {
                    "task_id": task.get("task_id"),
                    "task_name": task.get("task_name"),
                    "assignee": task.get("assignee"),
                    "reason": reason,
                }
            )
    return stalled


def member_load(tasks: list[dict], members: list[dict]) -> list[dict]:
    """メンバーごとの週稼働時間に対する残工数の割当状況を集計する。"""
    remaining_by_assignee: dict[str, float] = {}
    task_count_by_assignee: dict[str, int] = {}
    for task in tasks:
        if task.get("status") == config.STATUS_DONE:
            continue
        assignee = (task.get("assignee") or "").strip()
        if not assignee:
            continue
        hours = _to_float(task.get("remaining_hours"))
        remaining_by_assignee[assignee] = remaining_by_assignee.get(assignee, 0.0) + hours
        task_count_by_assignee[assignee] = task_count_by_assignee.get(assignee, 0) + 1

    result = []
    for member in members:
        name = member.get("name")
        capacity = _to_float(member.get("weekly_capacity_hours"))
        assigned_hours = remaining_by_assignee.get(name, 0.0)
        result.append(
            {
                "name": name,
                "weekly_capacity_hours": capacity,
                "assigned_remaining_hours": assigned_hours,
                "task_count": task_count_by_assignee.get(name, 0),
                "utilization": (assigned_hours / capacity) if capacity > 0 else None,
                "is_overloaded": capacity > 0 and assigned_hours > capacity,
                "is_idle": assigned_hours == 0.0,
                "specialty": member.get("specialty"),
                "experience_level": member.get("experience_level"),
            }
        )

    return result


def analyze_goal(goals: list[dict], today: datetime.date | None = None) -> dict | None:
    """現在の目標を特定し、大会までの残日数・直前判定を行う。"""
    today = today or datetime.date.today()

    current = next((g for g in goals if _to_bool(g.get("is_current_goal"))), None)
    if current is None and goals:
        current = goals[0]
    if current is None:
        return None

    competition_date = _parse_date(current.get("competition_date"))
    days_remaining = (competition_date - today).days if competition_date else None

    return {
        "competition_name": current.get("competition_name"),
        "competition_date": current.get("competition_date"),
        "goal_content": current.get("goal_content"),
        "days_remaining": days_remaining,
        "is_imminent": days_remaining is not None
        and 0 <= days_remaining <= config.IMMINENT_DAYS_THRESHOLD,
    }


def _split_ids(raw: str) -> list[str]:
    normalized = raw
    for sep in ["、", ",", "，", "/", " "]:
        normalized = normalized.replace(sep, "\n")
    return [s.strip() for s in normalized.split("\n") if s.strip()]


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _to_bool(value) -> bool:
    return str(value).strip().upper() in ("TRUE", "1", "YES", "はい")


def _parse_date(value) -> datetime.date | None:
    if not value:
        return None
    try:
        return datetime.datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        return None
