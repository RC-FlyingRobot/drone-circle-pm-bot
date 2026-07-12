"""Google Sheets読み書き。ヘッダーの表記ゆれは normalize_header() で吸収する。"""

import json
import unicodedata

import gspread
from google.oauth2.service_account import Credentials

import config

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def normalize_header(text: str) -> str:
    """全角/半角・空白・括弧の表記ゆれを吸収するための正規化。"""
    text = unicodedata.normalize("NFKC", text or "")
    for ch in " 　()（）・-_":
        text = text.replace(ch, "")
    return text.lower()


def _build_reverse_lookup(aliases: dict) -> dict:
    lookup = {}
    for canonical, variants in aliases.items():
        for variant in variants:
            lookup[normalize_header(variant)] = canonical
    return lookup


def get_client() -> gspread.Client:
    if not config.GCP_SERVICE_ACCOUNT_JSON:
        raise RuntimeError("環境変数 GCP_SERVICE_ACCOUNT_JSON が設定されていません。")
    info = json.loads(config.GCP_SERVICE_ACCOUNT_JSON)
    creds = Credentials.from_service_account_info(info, scopes=SCOPES)
    return gspread.authorize(creds)


def _read_tab(client: gspread.Client, tab_name: str, aliases: dict) -> list[dict]:
    """タブを読み込み、ヘッダーを正規化フィールド名に変換した辞書リストで返す。"""
    spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(tab_name)
    raw_rows = worksheet.get_all_values()

    if not raw_rows:
        return []

    lookup = _build_reverse_lookup(aliases)
    header_row = raw_rows[0]
    normalized_header = [lookup.get(normalize_header(h)) for h in header_row]

    records = []
    for row in raw_rows[1:]:
        if not any(cell.strip() for cell in row):
            continue  # 空行はスキップ
        record = {}
        for key, value in zip(normalized_header, row):
            if key is None:
                continue  # 未知の列(別名リストにない列)は無視
            record[key] = value.strip()
        records.append(record)

    return records


def read_goals(client: gspread.Client | None = None) -> list[dict]:
    client = client or get_client()
    return _read_tab(client, config.TAB_GOALS, config.GOALS_HEADER_ALIASES)


def read_tasks(client: gspread.Client | None = None) -> list[dict]:
    client = client or get_client()
    return _read_tab(client, config.TAB_TASKS, config.TASKS_HEADER_ALIASES)


def read_members(client: gspread.Client | None = None) -> list[dict]:
    client = client or get_client()
    return _read_tab(client, config.TAB_MEMBERS, config.MEMBERS_HEADER_ALIASES)


def read_history(client: gspread.Client | None = None) -> list[dict]:
    client = client or get_client()
    return _read_tab(client, config.TAB_HISTORY, config.HISTORY_HEADER_ALIASES)


def append_history(
    week: str,
    roadmap_json: str,
    diff_notes: str = "",
    client: gspread.Client | None = None,
) -> None:
    """履歴ログタブに1行追記する。"""
    client = client or get_client()
    spreadsheet = client.open_by_key(config.SPREADSHEET_ID)
    worksheet = spreadsheet.worksheet(config.TAB_HISTORY)
    worksheet.append_row([week, roadmap_json, diff_notes], value_input_option="USER_ENTERED")
