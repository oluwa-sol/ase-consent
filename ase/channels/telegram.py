"""Telegram connector (Bot API).

Works two ways:
- Webhook: Telegram POSTs updates to /telegram/webhook (production).
- Polling: scripts/telegram_polling.py pulls updates (local development, no public URL needed).
"""

import os

import httpx

from ..conversation import handle_message
from ..db import SessionLocal

CHANNEL = "telegram"
API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")
    return token


def send_message(chat_id: int | str, text: str) -> None:
    r = httpx.post(API.format(token=_token(), method="sendMessage"),
                   json={"chat_id": chat_id, "text": text}, timeout=20)
    r.raise_for_status()


def process_update(update: dict) -> list[str]:
    """Handle one Telegram update and send the replies. Returns the replies (for logging and tests)."""
    msg = update.get("message") or update.get("edited_message")
    if not msg or "text" not in msg:
        return []
    chat_id = msg["chat"]["id"]
    with SessionLocal() as db:
        replies = handle_message(db, CHANNEL, str(chat_id), msg["text"])
        db.commit()
    for reply in replies:
        send_message(chat_id, reply)
    return replies


def get_updates(offset: int | None, timeout: int = 30) -> list[dict]:
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    r = httpx.get(API.format(token=_token(), method="getUpdates"), params=params, timeout=timeout + 10)
    r.raise_for_status()
    return r.json().get("result", [])
