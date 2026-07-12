"""Gemini APIによる総合判断(ロードマップ生成)。

役割分担の原則: 事実の集計はPython(preprocess.py)、総合判断だけここでGeminiに任せる。
生データは渡さず、事実サマリ(要約済みJSON)だけを渡す。
"""

import datetime
import json
from pathlib import Path

from google import genai
from google.genai import types
from pydantic import BaseModel, Field

import config

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "system_prompt.md"


class RoadmapFocus(BaseModel):
    focus: str = Field(description="今週注力すべきテーマ")
    tasks: list[str] = Field(description="対応するタスクIDのリスト")


class Assignment(BaseModel):
    member: str = Field(description="担当メンバー名")
    task: str = Field(description="タスクIDまたはタスク名")
    reason: str = Field(description="このアサインを選んだ理由")


class RoadmapOutput(BaseModel):
    roadmap: list[RoadmapFocus]
    assignments: list[Assignment]
    risks: list[str]
    priority_reasoning: str = Field(
        description="なぜこの優先順位にしたか。部員が逆算思考を学べるように具体的に書く"
    )


def _load_system_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")


def build_fact_summary(
    goal: dict | None,
    critical_path_result: dict,
    stalled_tasks: list[dict],
    member_loads: list[dict],
    previous_roadmap: dict | None,
) -> dict:
    """前処理結果をGeminiに渡す「事実サマリ」としてまとめる。"""
    return {
        "today": datetime.date.today().isoformat(),
        "goal": goal,
        "critical_path": critical_path_result,
        "stalled_tasks": stalled_tasks,
        "member_loads": member_loads,
        "previous_roadmap": previous_roadmap,
    }


def generate_roadmap(fact_summary: dict) -> RoadmapOutput:
    if not config.GEMINI_API_KEY:
        raise RuntimeError("環境変数 GEMINI_API_KEY が設定されていません。")

    client = genai.Client(api_key=config.GEMINI_API_KEY)

    response = client.models.generate_content(
        model=config.GEMINI_MODEL,
        contents=_fact_summary_to_text(fact_summary),
        config=types.GenerateContentConfig(
            system_instruction=_load_system_prompt(),
            response_mime_type="application/json",
            response_schema=RoadmapOutput,
        ),
    )

    return RoadmapOutput.model_validate_json(response.text)


def _fact_summary_to_text(fact_summary: dict) -> str:
    return json.dumps(fact_summary, ensure_ascii=False, indent=2)
