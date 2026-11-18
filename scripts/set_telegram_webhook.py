"""Point the Telegram bot at the deployed server (or back to local polling).

    python scripts/set_telegram_webhook.py https://your-app.onrender.com   # use the live server
    python scripts/set_telegram_webhook.py --delete                        # go back to local polling

Needs TELEGRAM_BOT_TOKEN and TELEGRAM_WEBHOOK_SECRET (the same secret as on the server).
"""

import os
import sys

import httpx


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    api = f"https://api.telegram.org/bot{token}"
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    if sys.argv[1] == "--delete":
        r = httpx.post(f"{api}/deleteWebhook", timeout=20)
    else:
        url = sys.argv[1].rstrip("/") + "/telegram/webhook"
        secret = os.environ["TELEGRAM_WEBHOOK_SECRET"].strip()
        r = httpx.post(f"{api}/setWebhook", json={
            "url": url, "secret_token": secret, "allowed_updates": ["message", "edited_message"],
            "drop_pending_updates": True}, timeout=20)
    print(r.json())
    info = httpx.get(f"{api}/getWebhookInfo", timeout=20).json()["result"]
    print("webhook now:", info.get("url") or "(none, polling mode)")


if __name__ == "__main__":
    main()
