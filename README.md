# Àṣẹ

**Open-source consent for health data, run through the chat apps people already use.**

People decide, use by use, how their health data may be used, and can change their mind at any time. Every decision goes into a tamper-evident log, and organisations must check Àṣẹ before they use anyone's data.

*Àṣẹ* (Yoruba) means "so it is", the word that makes something binding.

**Live:** [ase-consent.onrender.com/transparency](https://ase-consent.onrender.com/transparency) · **Telegram:** working today · **WhatsApp:** working (Meta test number, public number coming soon)

> Free hosting: the first visit after a quiet spell can take up to a minute to load.

## The problem

Health data from African communities, including mental health data, is increasingly used to build AI, often without meaningful consent and without any benefit coming back. When consent exists, it is usually a one-time tap-through that people can't understand or change.

## What works today

- **Consent per use, in chat.** Separate yes or no for community research, sharing with partners, AI training and more, in **English and Nigerian Pidgin**. People can view, change or withdraw everything with a simple message.
- **Tamper-evident record.** Every decision is written to a hash-chained, append-only ledger. Anyone can check that nothing was edited or deleted at [`/v1/ledger/verify`](https://ase-consent.onrender.com/v1/ledger/verify).
- **Organisations must ask, and the community decides.** Organisations apply at [`/request-access`](https://ase-consent.onrender.com/request-access), saying why they need the data and what they will give back. A panel approves or declines, and an approval can be removed at any time.
- **Consent check API.** `GET /v1/consent/check?reference=ASE-XXXXXX&use=ai_training` answers only "allowed" or "not allowed". Allowed needs both an approved organisation and the person's yes, and every "allowed" is logged.
- **Withdrawal that travels.** When someone withdraws, every organisation that used their data for that purpose gets a notice and must confirm it has stopped. The person is told how many were notified.
- **Public transparency page.** Shows what people agreed to, which organisations are approved and whether withdrawal notices are confirmed, without ever showing anyone's personal details.
- **No health data inside Àṣẹ.** It stores consent and decisions only. The health data stays in the organisation's own system.

## How it's built

- **Channel-agnostic core.** The consent rules live in one place, and each messaging app is a thin connector. A person's record is the same whichever app they use, and they can link apps with a one-time code.
- **Python, FastAPI, PostgreSQL**, deployed on Render.
- **Telegram Bot API** (webhook) and **WhatsApp Cloud API** (every webhook checked against Meta's signature).
- Organisation API keys are stored hashed and shown once.
- **53 automated tests.**

## Roadmap

- WhatsApp live on a dedicated number
- Yoruba, and voice notes for people who prefer listening
- SMS for basic phones
- Public benefit log of what each organisation gives back
- Consent records structured to follow ISO/IEC TS 27560

## Principles

Designed around the CARE principles for data governance (Collective benefit, Authority to control, Responsibility, Ethics), dynamic consent, and the consent standard in Nigeria's Data Protection Act 2023: freely given, specific, informed and clear.

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

WhatsApp needs a public HTTPS URL and these settings from your own Meta app: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_APP_SECRET`. Point the webhook at `/whatsapp/webhook` and subscribe to `messages` on the WhatsApp Business Account object.

Background research is in [`research/`](research/).

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
