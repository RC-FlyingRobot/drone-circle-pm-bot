"""週次ロードマップ生成+タスクアサイン自動化のエントリポイント。

流れ:
  1. Sheets読み込み(gspread)
  2. 前処理・事実の集計(AI不使用。critical_path / stalled / member_load / goal)
  3. 履歴ログ読み込み(前回の提案)
  4. Gemini APIで判断(ロードマップ+アサイン+理由)
  5. Discord用に整形して送信
  6. 履歴ログに1行追記

--dry-run を付けると、Discord送信と履歴追記を行わず、事実サマリと送信予定メッセージを標準出力に表示するだけ。
"""

import argparse
import datetime
import json

import config
import formatter
import llm
import notify
import preprocess
import sheets


def run(dry_run: bool = False) -> str:
    client = sheets.get_client()

    goals = sheets.read_goals(client)
    tasks = sheets.read_tasks(client)
    members = sheets.read_members(client)
    history = sheets.read_history(client)

    goal = preprocess.analyze_goal(goals)
    cp_result = preprocess.critical_path(tasks)
    stalled = preprocess.detect_stalled(tasks)
    loads = preprocess.member_load(tasks, members)

    previous_roadmap = None
    if history:
        previous_json = (history[-1] or {}).get("roadmap_json")
        if previous_json:
            try:
                previous_roadmap = json.loads(previous_json)
            except json.JSONDecodeError:
                previous_roadmap = None

    fact_summary = llm.build_fact_summary(goal, cp_result, stalled, loads, previous_roadmap)
    roadmap = llm.generate_roadmap(fact_summary)
    message = formatter.format_roadmap(roadmap, goal)

    if dry_run:
        print("=== 事実サマリ(Geminiへの入力) ===")
        print(json.dumps(fact_summary, ensure_ascii=False, indent=2))
        print("\n=== Discord送信予定メッセージ(dry-runのため送信・履歴追記は行いません) ===")
        print(message)
        return message

    notify.send_to_discord(message)
    sheets.append_history(
        week=datetime.date.today().isoformat(),
        roadmap_json=roadmap.model_dump_json(),
        client=client,
    )

    return message


def main() -> None:
    parser = argparse.ArgumentParser(description="週次ロードマップ生成+タスクアサイン")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discord送信・履歴追記を行わず、結果を標準出力に表示するだけの確認モード",
    )
    args = parser.parse_args()

    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
