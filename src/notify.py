"""Discord Webhookへの送信。"""

import requests

import config

CHUNK_SIZE = 1900


def send_to_discord(message: str) -> None:
    if not config.DISCORD_WEBHOOK_URL:
        raise RuntimeError("環境変数 DISCORD_WEBHOOK_URL が設定されていません。")

    chunks = [message[i : i + CHUNK_SIZE] for i in range(0, len(message), CHUNK_SIZE)] or [message]
    for chunk in chunks:
        resp = requests.post(config.DISCORD_WEBHOOK_URL, json={"content": chunk})
        resp.raise_for_status()
