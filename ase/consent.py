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
    return ledger.append(
        db,
        person_id=person.id,
        data_use_code=use.code,
        decision=decision,
        channel=channel,
        language=person.language,
        notice_version=use.notice_version,
    )


def latest_decisions(db: Session, person: Person) -> dict[str, ConsentEvent]:
    """Most recent decision per data use. The latest event always wins."""
    latest: dict[str, ConsentEvent] = {}
    for e in db.scalars(select(ConsentEvent).where(ConsentEvent.person_id == person.id).order_by(ConsentEvent.id)):
        latest[e.data_use_code] = e
    return latest


def is_allowed(db: Session, person: Person, use_code: str) -> bool:
    e = latest_decisions(db, person).get(use_code)
    return bool(e and e.decision == "granted")


def withdraw_all(db: Session, person: Person, channel: str) -> list[str]:
    """Withdraw every use the person had granted. Returns the codes withdrawn."""
    withdrawn = []
    uses = {u.code: u for u in active_uses(db)}
    for code, e in latest_decisions(db, person).items():
        if e.decision == "granted" and code in uses:
            record(db, person, uses[code], "withdrawn", channel)
            withdrawn.append(code)
    return withdrawn
