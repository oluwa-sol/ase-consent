# Àṣẹ

**Community-controlled consent for health data, on the messaging apps people already use: WhatsApp and Telegram.**

*Àṣẹ* (Yoruba) means "authority", "so it is". It is the word that makes something binding. This project is about who gets to say it over people's data.

## Why

Health data from African communities, including mental health data, is increasingly used to build AI. Too often that happens without meaningful consent, without the community having any say, and without any of the benefit coming back. Consent, when it exists at all, is usually a one-time tap-through that people can't understand or change.

Àṣẹ is an open-source tool that lets people and communities decide how their data is used, in a channel they already use every day.

## Built for the channel people already have

Communities don't all use the same app. WhatsApp dominates in Nigeria and much of Africa, Telegram is the main messenger in other regions and in communities where WhatsApp is restricted or unreliable, and some people have no smartphone at all. So Àṣẹ is **channel-agnostic by design**: the consent logic lives in one core, and each messaging app is a thin connector on top.

- **WhatsApp** and **Telegram** are both first-class channels from day one, with the same features on each.
- A person's consent is the same record whichever channel they use, so they can switch apps without losing control.
- **SMS** is planned next, for people on basic phones.
- New channels can be added without touching the consent rules.

## What it does (planned)

- **Plain-language consent in the chat**, on WhatsApp or Telegram, in English, Nigerian Pidgin and Yoruba, with voice notes for people who prefer listening to reading.
- **Consent per use, not one big "I agree".** Separate choices for community research, sharing with partners, AI training, and more.
- **Change or withdraw any time** with a simple message. Withdrawal is passed on to every approved data user, who must confirm.
- **A community panel** (young people, people with lived experience, community health workers) that approves or rejects each request to use the data.
- **A public benefit log** recording what every data user gives back to the community.
- **Tamper-evident consent records**, structured to follow ISO/IEC TS 27560.
- **No health data inside Àṣẹ.** It stores consent and decisions only. Health data stays in the organisation's own system, which checks Àṣẹ before any use.

## Principles

Àṣẹ is designed around the CARE principles for data governance (Collective benefit, Authority to control, Responsibility, Ethics), dynamic consent, and the consent standard in Nigeria's Data Protection Act 2023: freely given, specific, informed and clear.

## Status

Early development. Working today:

- Channel-agnostic consent core with a **hash-chained, append-only consent ledger** (any edit or deletion is detected)
- Chat flow in **English and Nigerian Pidgin**: consent per use, view choices, change them, withdraw everything (with confirmation)
- **Telegram** connector (webhook and local polling). WhatsApp connector next.
- **Consent check API** for organisations: `GET /v1/consent/check?reference=ASE-XXXXXX&use=ai_training` answers only "allowed or not", never anything else about the person
- Public **ledger verification**: `GET /v1/ledger/verify`

Background research is in [`research/`](research/).

## Run it locally

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -e ".[dev]"
pytest                        # run the tests

# Telegram bot (create a bot with @BotFather first)
set TELEGRAM_BOT_TOKEN=your-token       # macOS/Linux: export TELEGRAM_BOT_TOKEN=your-token
python scripts/telegram_polling.py

# API
set ASE_ORG_API_KEY=choose-a-key
uvicorn ase.api:app --reload
```

## Stack

Python (FastAPI), PostgreSQL, a channel-agnostic consent core with connectors for the WhatsApp Cloud API and the Telegram Bot API (SMS planned), a lightweight web dashboard, Docker.

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
