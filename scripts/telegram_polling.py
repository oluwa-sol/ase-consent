"""Run the Telegram bot locally by polling (no public URL needed).

    set TELEGRAM_BOT_TOKEN=...   (Windows)   or   export TELEGRAM_BOT_TOKEN=...
    python scripts/telegram_polling.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ase.channels import telegram  # noqa: E402
from ase.db import SessionLocal, init_db  # noqa: E402
from ase.seed import seed_uses  # noqa: E402


def main():
    init_db()
    with SessionLocal() as db:
        seed_uses(db)
        db.commit()
    print("Àṣẹ Telegram bot running. Press Ctrl+C to stop.")
    offset = None
    while True:
        for update in telegram.get_updates(offset):
            offset = update["update_id"] + 1
            try:
                replies = telegram.process_update(update)
                if replies:
                    print(f"[{update['update_id']}] replied with {len(replies)} message(s)")
            except Exception as e:  # keep the bot alive; one bad update must not stop it
                print(f"[{update['update_id']}] error: {e}")


if __name__ == "__main__":
    main()
