"""
毎週火曜17:00(JST)に実行:
Google SheetsのCSV公開URLから、ステータスが
「進行中」または「未着手」のタスクを箇条書きでDiscordに通知する。

出力フォーマット:
  * タスク名：担当者

必要な環境変数:
  CSV_URL              : スプレッドシートの「ウェブに公開」で発行したCSV URL
  DISCORD_WEBHOOK_URL  : DiscordのWebhook URL

事前準備:
  スプレッドシート → ファイル → 共有 → ウェブに公開
  → 対象タブを選択 → 形式を「カンマ区切りの値(.csv)」にして公開
  → 発行されたURLを CSV_URL として使う
"""

import os
import io
import csv
import datetime
import requests

TARGET_STATUSES = {"進行中", "未着手"}


def fetch_active_tasks():
    """
    シートの列構成:
    A: No / B: タスク名 / C: 担当者 / D: グループ / E: 優先度 / F: ステータス / G: メモ / H: 期限

    抽出条件: ステータスが「進行中」または「未着手」
    """
    csv_url = os.environ["CSV_URL"]
    resp = requests.get(csv_url)
    resp.raise_for_status()
    # Google CSVはUTF-8で返る想定。文字化けする場合はresp.contentをcp932等でdecodeする
    resp.encoding = "utf-8"

    all_rows = list(csv.reader(io.StringIO(resp.text)))

    # タイトル行や空行が上に何行あっても対応できるよう、
    # 「タスク名」という列が実際に含まれる行を探してそこをヘッダーとして扱う。
    header_index = None
    for i, row in enumerate(all_rows):
        if "タスク名" in row:
            header_index = i
            break

    if header_index is None:
        raise ValueError(
            "CSV内に「タスク名」列を含むヘッダー行が見つかりませんでした。"
            "シートの列名やCSV_URLの参照先タブを確認してください。"
        )

    header = all_rows[header_index]
    data_rows = all_rows[header_index + 1:]

    rebuilt = io.StringIO()
    writer = csv.writer(rebuilt)
    writer.writerow(header)
    writer.writerows(data_rows)
    rebuilt.seek(0)
    reader = csv.DictReader(rebuilt)

    active_tasks = []
    for row in reader:
        name = (row.get("タスク名") or "").strip()
        assignee = (row.get("担当者") or "").strip()
        status = (row.get("ステータス") or "").strip()

        if not name or status not in TARGET_STATUSES:
            continue

        active_tasks.append({
            "name": name,
            "assignee": assignee or "未割当",
            "status": status,
        })

    return active_tasks


def build_message(tasks):
    today_str = datetime.date.today().strftime("%Y/%m/%d")
    lines = [f"**📋 タスク状況({today_str})**"]

    if not tasks:
        lines.append("進行中・未着手のタスクはありません。")
        return "\n".join(lines)

    in_progress = [t for t in tasks if t["status"] == "進行中"]
    not_started = [t for t in tasks if t["status"] == "未着手"]

    if in_progress:
        lines.append("\n**▶️ 進行中**")
        for t in in_progress:
            lines.append(f"* {t['name']}：{t['assignee']}")

    if not_started:
        lines.append("\n**⬜ 未着手**")
        for t in not_started:
            lines.append(f"* {t['name']}：{t['assignee']}")

    return "\n".join(lines)


def send_to_discord(message: str):
    webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
    chunks = [message[i:i + 1900] for i in range(0, len(message), 1900)] or [message]
    for chunk in chunks:
        resp = requests.post(webhook_url, json={"content": chunk})
        resp.raise_for_status()


def main():
    tasks = fetch_active_tasks()
    message = build_message(tasks)
    send_to_discord(message)
    print("送信完了:\n", message)


if __name__ == "__main__":
    main()