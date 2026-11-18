"""Consent service: the channel-agnostic core. Every channel goes through these functions."""

import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ledger
from .models import ChannelIdentity, ConsentEvent, DataUse, Person

_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I/L, to read out loud easily


def new_reference() -> str:
    return "ASE-" + "".join(secrets.choice(_ALPHABET) for _ in range(6))


def get_or_create_person(db: Session, channel: str, external_id: str) -> Person:
    ident = db.scalars(select(ChannelIdentity).where(
        ChannelIdentity.channel == channel, ChannelIdentity.external_id == str(external_id))).first()
    if ident:
        return db.get(Person, ident.person_id)
    person = Person(reference=new_reference())
    db.add(person)
    db.flush()
    db.add(ChannelIdentity(person_id=person.id, channel=channel, external_id=str(external_id)))
    db.flush()
    return person


def active_uses(db: Session) -> list[DataUse]:
    return list(db.scalars(select(DataUse).where(DataUse.active).order_by(DataUse.position)))


def record(db: Session, person: Person, use: DataUse, decision: str, channel: str) -> ConsentEvent:
    """Save a decision. If it turns an earlier YES into a NO, every organisation using that data is notified.

    The returned event carries `.notified`: how many organisations were told to stop.
    """
    previous = latest_decisions(db, person).get(use.code)
    event = ledger.append(
        db,
        person_id=person.id,
        data_use_code=use.code,
        decision=decision,
        channel=channel,
        language=person.language,
        notice_version=use.notice_version,
    )
    event.notified = 0
    if decision != "granted" and previous is not None and previous.decision == "granted":
        from .datausers import notify_withdrawal
        event.notified = notify_withdrawal(db, event)
    return event


def latest_decisions(db: Session, person: Person) -> dict[str, ConsentEvent]:
    """Most recent decision per data use. The latest event always wins."""
    latest: dict[str, ConsentEvent] = {}
    for e in db.scalars(select(ConsentEvent).where(ConsentEvent.person_id == person.id).order_by(ConsentEvent.id)):
        latest[e.data_use_code] = e
    return latest


def is_allowed(db: Session, person: Person, use_code: str) -> bool:
    e = latest_decisions(db, person).get(use_code)
    return bool(e and e.decision == "granted")


LINK_MINUTES = 10


def create_link_code(db: Session, person: Person) -> str:
    """Make a 6-digit code, valid for LINK_MINUTES, that lets another channel join this person."""
    from datetime import timedelta
    from .models import LinkCode, utcnow

    code = f"{secrets.randbelow(1_000_000):06d}"
    db.add(LinkCode(person_id=person.id, code=code, expires_at=utcnow() + timedelta(minutes=LINK_MINUTES)))
    db.flush()
    return code


def redeem_link_code(db: Session, code: str, channel: str, external_id: str) -> tuple[str, Person | None]:
    """Attach (channel, external_id) to the person who generated `code`.

    Returns (status, person). status is one of:
      "linked", "invalid" (unknown/used/expired), "same" (already that person),
      "has_choices" (this channel already holds its own consent record, we never merge two records).
    """
    from .models import Conversation, LinkCode, utcnow

    link = db.scalars(select(LinkCode).where(LinkCode.code == code.strip(), LinkCode.used.is_(False))
                      .order_by(LinkCode.id.desc())).first()
    now = utcnow()
    if link is None:
        return "invalid", None
    expires = link.expires_at if link.expires_at.tzinfo else link.expires_at.replace(tzinfo=now.tzinfo)
    if expires < now:
        return "invalid", None
    target = db.get(Person, link.person_id)

    ident = db.scalars(select(ChannelIdentity).where(
        ChannelIdentity.channel == channel, ChannelIdentity.external_id == str(external_id))).first()
    if ident and ident.person_id == target.id:
        return "same", target
    if ident:
        if latest_decisions(db, db.get(Person, ident.person_id)):
            return "has_choices", None
        old_person_id = ident.person_id
        ident.person_id = target.id
        for conv in db.scalars(select(Conversation).where(Conversation.person_id == old_person_id)):
            db.delete(conv)
        db.flush()
        db.delete(db.get(Person, old_person_id))
    else:
        db.add(ChannelIdentity(person_id=target.id, channel=channel, external_id=str(external_id)))
    link.used = True
    db.flush()
    return "linked", target


def withdraw_everything(db: Session, person: Person, channel: str) -> tuple[list[str], int]:
    """Withdraw every use the person had granted. Returns (codes withdrawn, organisations notified)."""
    withdrawn, notified = [], 0
    uses = {u.code: u for u in active_uses(db)}
    for code, e in latest_decisions(db, person).items():
        if e.decision == "granted" and code in uses:
            event = record(db, person, uses[code], "withdrawn", channel)
            withdrawn.append(code)
            notified += event.notified
    return withdrawn, notified


def withdraw_all(db: Session, person: Person, channel: str) -> list[str]:
    """Withdraw every use the person had granted. Returns the codes withdrawn."""
    return withdraw_everything(db, person, channel)[0]
