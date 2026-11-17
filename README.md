# Àṣẹ

**Community-controlled consent for health data, over WhatsApp.**

*Àṣẹ* (Yoruba) means "authority", "so it is". It is the word that makes something binding. This project is about who gets to say it over people's data.

## Why

Health data from African communities, including mental health data, is increasingly used to build AI. Too often that happens without meaningful consent, without the community having any say, and without any of the benefit coming back. Consent, when it exists at all, is usually a one-time tap-through that people can't understand or change.

Àṣẹ is an open-source tool that lets people and communities decide how their data is used, in a channel they already use every day.

## What it does (planned)

- **Plain-language consent on WhatsApp**, in English, Nigerian Pidgin and Yoruba, with voice notes for people who prefer listening to reading.
- **Consent per use, not one big "I agree".** Separate choices for community research, sharing with partners, AI training, and more.
- **Change or withdraw any time** with a simple message. Withdrawal is passed on to every approved data user, who must confirm.
- **A community panel** (young people, people with lived experience, community health workers) that approves or rejects each request to use the data.
- **A public benefit log** recording what every data user gives back to the community.
- **Tamper-evident consent records**, structured to follow ISO/IEC TS 27560.
- **No health data inside Àṣẹ.** It stores consent and decisions only. Health data stays in the organisation's own system, which checks Àṣẹ before any use.

## Principles

Àṣẹ is designed around the CARE principles for data governance (Collective benefit, Authority to control, Responsibility, Ethics), dynamic consent, and the consent standard in Nigeria's Data Protection Act 2023: freely given, specific, informed and clear.

## Status

Early development. Background research is in [`research/`](research/).

## Stack

Python (FastAPI), PostgreSQL, WhatsApp Cloud API, Telegram, a lightweight web dashboard, Docker.

## Licence

Apache License 2.0. See [LICENSE](LICENSE).
