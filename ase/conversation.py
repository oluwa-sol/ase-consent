"""Channel-agnostic chat flow.

handle_message() takes plain text from any channel and returns the replies to send.
Connectors (Telegram, WhatsApp, SMS) only translate between their API and this function.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import consent
from .messages import LANGUAGES, t, yes_no
from .models import Conversation, Person

RESET_WORDS = {"start", "/start", "hi", "hello", "menu", "help"}
WITHDRAW_WORDS = {"withdraw", "stop", "cancel all"}
BYE_WORDS = {"bye", "goodbye", "good bye", "bye bye", "byee", "see you", "see you later", "later", "good night", "goodnight", "ok bye", "make we see later", "ó dàbọ̀", "o dabo"}
ACK_WORDS = {"ok", "okay", "ok thanks", "thanks", "thank you", "alright", "fine", "cool", "noted", "e don do", "i don hear"}


def _conversation(db: Session, person: Person, channel: str) -> Conversation:
    conv = db.scalars(select(Conversation).where(
        Conversation.person_id == person.id, Conversation.channel == channel)).first()
    if conv is None:
        conv = Conversation(person_id=person.id, channel=channel, step="new")
        db.add(conv)
        db.flush()
    return conv


def _ask(db: Session, person: Person, conv: Conversation) -> str:
    uses = consent.active_uses(db)
    use = uses[conv.use_index]
    txt = use.text.get(person.language) or use.text["en"]
    return t("ask", person.language, i=conv.use_index + 1, n=len(uses), title=txt["title"], explain=txt["explain"])


def _summary(db: Session, person: Person) -> str:
    lang = person.language
    status = t("status", lang)
    latest = consent.latest_decisions(db, person)
    lines = [t("summary_header", lang, ref=person.reference)]
    for use in consent.active_uses(db):
        title = (use.text.get(lang) or use.text["en"])["title"]
        e = latest.get(use.code)
        lines.append(f"- {title}: {status[e.decision if e else None]}")
    lines.append("")
    lines.append(t("code_hint", lang, ref=person.reference))
    return "\n".join(lines)


def _join(*parts: str) -> str:
    """Several pieces of text sent as ONE chat message, so the phone buzzes once."""
    return "\n\n".join(parts)


def _start_asking(db: Session, person: Person, conv: Conversation) -> list[str]:
    conv.step, conv.use_index = "asking", 0
    return [_ask(db, person, conv)]


def handle_message(db: Session, channel: str, external_id: str, text: str) -> list[str]:
    person = consent.get_or_create_person(db, channel, external_id)
    conv = _conversation(db, person, channel)
    lang = person.language
    msg = (text or "").strip()
    low = msg.lower()

    # "LINK 123456" works from any step, including a brand-new chat on the second app.
    if low.startswith("link ") and low[5:].strip().isdigit():
        status, target = consent.redeem_link_code(db, low[5:].strip(), channel, external_id)
        if status in ("linked", "same"):
            new_conv = _conversation(db, target, channel)
            new_conv.step = "menu"
            key = "linked" if status == "linked" else "link_same"
            return [_join(t(key, target.language, ref=target.reference), t("menu_hint", target.language))]
        key = "link_invalid" if status == "invalid" else "link_has_choices"
        return [t(key, lang)]

    if conv.step == "new":
        conv.step = "language"
        return [t("welcome", "en")]

    if conv.step == "language":
        if msg in LANGUAGES:
            person.language = LANGUAGES[msg]
            n = len(consent.active_uses(db))
            first_time = not consent.latest_decisions(db, person)
            if first_time:
                return [t("intro", person.language, n=n)] + _start_asking(db, person, conv)
            conv.step = "menu"
            return [t("menu", person.language)]
        return [t("welcome", "en")]

    if conv.step == "asking":
        answer = yes_no(msg)
        if answer is None:
            return [t("not_understood_yes_no", lang)]
        uses = consent.active_uses(db)
        consent.record(db, person, uses[conv.use_index], "granted" if answer else "refused", channel)
        conv.use_index += 1
        if conv.use_index < len(uses):
            return [_ask(db, person, conv)]
        conv.step = "menu"
        return [_join(t("done", lang), _summary(db, person), t("menu_hint", lang))]

    if conv.step == "confirm_withdraw":
        answer = yes_no(msg)
        if answer is None:
            return [t("not_understood_yes_no", lang)]
        conv.step = "menu"
        if not answer:
            return [_join(t("cancelled", lang), t("menu_hint", lang))]
        withdrawn = consent.withdraw_all(db, person, channel)
        if not withdrawn:
            return [_join(t("withdraw_none", lang), t("menu_hint", lang))]
        # Week 3: notify every approved data user here (withdrawal that travels).
        return [_join(t("withdrawn", lang, n=len(withdrawn)), _summary(db, person), t("menu_hint", lang))]

    # step == "menu"
    if low in WITHDRAW_WORDS or msg == "3":
        conv.step = "confirm_withdraw"
        return [t("confirm_withdraw", lang)]
    if msg == "1" or low in {"my data", "my choices"}:
        return [_join(_summary(db, person), t("menu_hint", lang))]
    if msg == "2" or low in {"change"}:
        return _start_asking(db, person, conv)
    if msg == "5" or low in {"link", "link app"}:
        code = consent.create_link_code(db, person)
        return [t("link_code", lang, code=code, mins=consent.LINK_MINUTES)]
    if msg == "4" or low in {"language", "lang"}:
        conv.step = "language"
        return [t("welcome", "en")]
    if low.strip(".!") in RESET_WORDS:
        return [t("menu", lang)]
    if low.strip(".!") in BYE_WORDS:
        return [t("bye", lang)]
    if low.strip(".!") in ACK_WORDS:
        return [t("ack", lang)]
    return [t("not_understood", lang)]
