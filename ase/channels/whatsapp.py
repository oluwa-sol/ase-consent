"""WhatsApp connector (Meta WhatsApp Cloud API).

Environment:
  WHATSAPP_TOKEN            access token (System User token for production)
  WHATSAPP_PHONE_NUMBER_ID  the sending number's ID
  WHATSAPP_VERIFY_TOKEN     any phrase you choose; must match the Meta webhook settings
  WHATSAPP_APP_SECRET       Meta app secret; used to check every webhook really came from Meta

Free-form replies are allowed inside the 24-hour window after the person messages us,
which is always the case here: Àṣẹ only ever answers people who wrote first.
"""

import hashlib
import hmac
import os

import httpx

from ..conversation import handle_message
from ..db import SessionLocal

CHANNEL = "whatsapp"
GRAPH = "https://graph.facebook.com/v22.0"


def verify_signature(raw_body: bytes, signature_header: str | None, app_secret: str | None = None) -> bool:
    """Check Meta's X-Hub-Signature-256 header. Rejects everything if no secret is configured."""
    secret = app_secret if app_secret is not None else os.environ.get("WHATSAPP_APP_SECRET", "")
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header[len("sha256="):])


def extract_messages(payload: dict) -> list[tuple[str, str]]:
    """Return (sender_wa_id, text) for every text or button reply in a webhook payload.

    Delivery and read receipts ("statuses") and media are ignored.
    """
    found = []
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for m in change.get("value", {}).get("messages", []) or []:
                text = (m.get("text", {}).get("body")
                        or m.get("button", {}).get("text")
                        or m.get("interactive", {}).get("button_reply", {}).get("title")
                        or m.get("interactive", {}).get("list_reply", {}).get("title"))
                if text and m.get("from"):
                    found.append((str(m["from"]), text))
    return found


def build_payload(to: str, text: str) -> dict:
    """Plain text, or tap buttons when the reply offers them (up to 3 as buttons, more as a list)."""
    buttons = getattr(text, "buttons", None) or []
    base = {"messaging_product": "whatsapp", "to": to}
    if not buttons or len(text) > 1024:
        return {**base, "type": "text", "text": {"body": str(text)[:4096]}}
    if len(buttons) <= 3:
        action = {"buttons": [{"type": "reply", "reply": {"id": b, "title": b[:20]}} for b in buttons]}
        return {**base, "type": "interactive",
                "interactive": {"type": "button", "body": {"text": str(text)}, "action": action}}
    rows = [{"id": b, "title": b[:24]} for b in buttons[:10]]
    return {**base, "type": "interactive",
            "interactive": {"type": "list", "body": {"text": str(text)},
                            "action": {"button": "Choose", "sections": [{"title": "Options", "rows": rows}]}}}


def send_text(to: str, text: str) -> None:
    token = os.environ["WHATSAPP_TOKEN"].strip()
    number_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"].strip()
    r = httpx.post(
        f"{GRAPH}/{number_id}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json=build_payload(to, text),
        timeout=20,
    )
    r.raise_for_status()


def process_payload(payload: dict) -> list[tuple[str, list[str]]]:
    """Handle every message in one webhook call. Returns [(sender, replies)] for logging and tests."""
    results = []
    for sender, text in extract_messages(payload):
        with SessionLocal() as db:
            replies = handle_message(db, CHANNEL, sender, text)
            db.commit()
        for reply in replies:
            try:
                send_text(sender, reply)
            except Exception as e:  # never fail the webhook: Meta would retry and repeat the message
                detail = getattr(getattr(e, "response", None), "text", "")[:300]
                print(f"[whatsapp] reply to {sender[-4:]} failed: {e} {detail}")
        results.append((sender, replies))
    return results
