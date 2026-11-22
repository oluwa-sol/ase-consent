"""Channel-agnostic chat flow.

handle_message() takes plain text from any channel and returns the replies to send.
Connectors (Telegram, WhatsApp, SMS) only translate between their API and this function.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import consent
from .messages import LANGUAGES, Reply, is_back, is_keep, t, yes_no
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
    current = consent.latest_decisions(db, person).get(use.code)
    if current is not None:  # changing an earlier answer: show it, and allow KEEP
        label = t("status", person.language)[current.decision]
        text = t("ask_change", person.language, i=conv.use_index + 1, n=len(uses), title=txt["title"],
                 explain=txt["explain"], current=label)
    else:
        text = t("ask", person.language, i=conv.use_index + 1, n=len(uses), title=txt["title"], explain=txt["explain"])
    buttons = ["YES", "NO"]
    if current is not None:
        buttons.append("KEEP")
    if conv.use_index > 0:
        buttons.append("BACK")
    return Reply(text, buttons)


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
    """Several pieces of text sent as ONE chat message, so the phone buzzes once.
    Tap buttons on the last part are kept."""
    last = parts[-1] if parts else ""
    return Reply("\n\n".join(parts), getattr(last, "buttons", None))


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
        return [Reply(t("welcome", "en"), ["English", "Pidgin"])]

    if conv.step == "language":
        if low in LANGUAGES:
            person.language = LANGUAGES[low]
            n = len(consent.active_uses(db))
            first_time = not consent.latest_decisions(db, person)
            if first_time:
                return [t("intro", person.language, n=n)] + _start_asking(db, person, conv)
            conv.step = "menu"
            return [t("menu", person.language)]
        return [Reply(t("welcome", "en"), ["English", "Pidgin"])]

    # MENU / HI / HELP always gets you out of a question flow; answers already given stay saved.
    if conv.step in ("asking", "confirm_withdraw") and low.strip(".!") in RESET_WORDS:
        conv.step = "menu"
        return [t("menu", lang)]

    if conv.step == "asking" and is_back(msg):
        conv.use_index = max(0, conv.use_index - 1)  # earlier answers stay saved; this just re-asks
        return [_ask(db, person, conv)]

    if conv.step == "asking":
        uses = consent.active_uses(db)
        current = consent.latest_decisions(db, person).get(uses[conv.use_index].code)
        if current is not None and is_keep(msg):
            told = []  # keep the earlier answer, record nothing new
        else:
            answer = yes_no(msg)
            if answer is None:
                return [Reply(t("not_understood_yes_no", lang), _ask(db, person, conv).buttons)]
            event = consent.record(db, person, uses[conv.use_index], "granted" if answer else "refused", channel)
            told = [t("notified", lang, k=event.notified)] if event.notified else []
        conv.use_index += 1
        if conv.use_index < len(uses):
            return [_join(*told, _ask(db, person, conv))]
        conv.step = "menu"
        return [_join(*told, t("done", lang), _summary(db, person), t("menu_hint", lang))]

    if conv.step == "confirm_withdraw":
        answer = yes_no(msg)
        if answer is None:
            return [Reply(t("not_understood_yes_no", lang), ["YES", "NO"])]
        conv.step = "menu"
        if not answer:
            return [_join(t("cancelled", lang), t("menu_hint", lang))]
        withdrawn, notified = consent.withdraw_everything(db, person, channel)
        if not withdrawn:
            return [_join(t("withdraw_none", lang), t("menu_hint", lang))]
        parts = [t("withdrawn", lang, n=len(withdrawn))]
        if notified:
            parts.append(t("notified", lang, k=notified))
        return [_join(*parts, _summary(db, person), t("menu_hint", lang))]

    # step == "menu"
    if low in WITHDRAW_WORDS or msg == "3":
        conv.step = "confirm_withdraw"
        return [Reply(t("confirm_withdraw", lang), ["YES", "NO"])]
    if msg == "1" or low in {"my data", "my choices"}:
        return [_join(_summary(db, person), t("menu_hint", lang))]
    if msg == "2" or low in {"change"}:
        return _start_asking(db, person, conv)
    if msg == "5" or low in {"link", "link app"}:
        code = consent.create_link_code(db, person)
        return [t("link_code", lang, code=code, mins=consent.LINK_MINUTES)]
    if msg == "4" or low in {"language", "lang"}:
        conv.step = "language"
        return [Reply(t("welcome", "en"), ["English", "Pidgin"])]
    if low.strip(".!") in RESET_WORDS:
        return [t("menu", lang)]
    if low.strip(".!") in BYE_WORDS:
        return [t("bye", lang)]
    if low.strip(".!") in ACK_WORDS:
        return [t("ack", lang)]
    return [t("not_understood", lang)]
