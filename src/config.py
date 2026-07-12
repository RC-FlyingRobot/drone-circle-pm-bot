"""タブ名・ヘッダー別名・環境変数の定義。"""

import os

# --- スプレッドシート ---
SPREADSHEET_ID = os.environ.get(
    "SPREADSHEET_ID", "1AO2TPZP1_bZZ3BbGmwfwRYvMpWSIne7CnxEjP-JpYvs"
)

# --- タブ名 ---
TAB_GOALS = "大会・目標"
TAB_TASKS = "タスク進捗"
TAB_MEMBERS = "メンバー状況"
TAB_HISTORY = "履歴ログ"

# --- 環境変数 ---
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
GCP_SERVICE_ACCOUNT_JSON = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# --- ステータス・区分の定数 ---
STATUS_NOT_STARTED = "未着手"
STATUS_IN_PROGRESS = "進行中"
STATUS_DONE = "完了"
ACTIVE_STATUSES = {STATUS_NOT_STARTED, STATUS_IN_PROGRESS}

BOTTLENECK_NONE = "なし"
BOTTLENECK_PARTS = "部品待ち"
BOTTLENECK_DIFFICULTY = "技術難易度"
BOTTLENECK_CAPACITY = "稼働不足"

EXPERIENCE_LEVELS = ["初心者", "中級", "経験者"]

# 大会直前とみなす残日数のしきい値
IMMINENT_DAYS_THRESHOLD = 14

# --- ヘッダー表記ゆれ吸収用の別名リスト ---
# key: 内部で使う正規化済みフィールド名 / value: シート上で許容する表記のバリエーション
GOALS_HEADER_ALIASES = {
    "competition_name": ["大会名", "大会", "イベント名"],
    "competition_date": ["大会日", "大会日程", "開催日"],
    "goal_content": ["目標内容", "目標", "目標詳細"],
    "is_current_goal": ["現在の目標か", "現在の目標", "対象"],
}

TASKS_HEADER_ALIASES = {
    "task_id": ["タスクID", "タスクId", "ID"],
    "task_name": ["タスク名", "タスク"],
    "department": ["部門", "担当部門", "グループ"],
    "assignee": ["担当者", "担当"],
    "progress_pct": ["進捗率", "進捗率(%)", "進捗率（%）", "進捗"],
    "status": ["ステータス", "状態"],
    "bottleneck_reason": ["ボトルネック理由", "ボトルネック", "停滞理由"],
    "dependency_ids": ["依存タスクID", "依存タスク", "前提タスクID"],
    "remaining_hours": ["残工数h", "残工数(h)", "残工数（h）", "残工数"],
    "notes": ["備考", "メモ"],
}

MEMBERS_HEADER_ALIASES = {
    "name": ["名前", "氏名"],
    "weekly_capacity_hours": [
        "週稼働時間h",
        "週稼働時間(h)",
        "週稼働時間（h）",
        "週稼働時間",
    ],
    "specialty": ["得意分野", "得意領域", "専門"],
    "experience_level": ["経験レベル", "レベル"],
    "current_task_count": ["現在の担当タスク数", "担当タスク数"],
    "remarks": ["特記事項", "備考"],
}

HISTORY_HEADER_ALIASES = {
    "week": ["週", "週次", "対象週"],
    "roadmap_json": ["ロードマップJSON", "ロードマップ", "roadmap"],
    "diff_notes": ["実績差分メモ", "差分メモ", "実績メモ"],
}
