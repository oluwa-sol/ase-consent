"""Organisations that use data, what they're approved for, and the withdrawal notices they must confirm."""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import consent
from .models import (ConsentEvent, DataAccessLog, DataUse, DataUser, DataUserAccess, Person,
                     WithdrawalNotice, utcnow)


def _hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def register(db: Session, name: str, contact: str = "") -> tuple[DataUser, str]:
    """Create an organisation. Returns it and its API key, which is shown ONCE and only stored hashed."""
    key = "ase_" + secrets.token_urlsafe(32)
    du = DataUser(name=name, contact=contact, api_key_hash=_hash(key))
    db.add(du)
    db.flush()
    return du, key


def by_key(db: Session, key: str | None) -> DataUser | None:
    if not key:
        return None
    du = db.scalars(select(DataUser).where(DataUser.api_key_hash == _hash(key))).first()
    return du if du and du.active else None


def approve(db: Session, du: DataUser, use_code: str, note: str = "") -> DataUserAccess:
    if db.get(DataUse, use_code) is None:
        raise ValueError(f"unknown data use {use_code!r}")
    existing = db.scalars(select(DataUserAccess).where(
        DataUserAccess.data_user_id == du.id, DataUserAccess.data_use_code == use_code)).first()
    if existing:
        return existing
    access = DataUserAccess(data_user_id=du.id, data_use_code=use_code, note=note)
    db.add(access)
    db.flush()
    return access


def is_approved(db: Session, du: DataUser, use_code: str) -> bool:
    return db.scalars(select(DataUserAccess).where(
        DataUserAccess.data_user_id == du.id, DataUserAccess.data_use_code == use_code)).first() is not None


def check(db: Session, du: DataUser, person: Person | None, use_code: str) -> dict:
    """The question an organisation must ask before using someone's data.

    Allowed only if the organisation is approved for this use AND the person's latest choice is YES.
    A YES answer is logged, so if the person later withdraws, this organisation is notified.
    """
    approved = is_approved(db, du, use_code)
    event = consent.latest_decisions(db, person).get(use_code) if person else None
    allowed = bool(approved and event and event.decision == "granted")
    if allowed:
        db.add(DataAccessLog(data_user_id=du.id, person_id=person.id, data_use_code=use_code))
        db.flush()
    reason = ("allowed" if allowed else
              "organisation not approved for this use" if not approved else
              "person has not agreed")
    return {"allowed": allowed, "reason": reason,
            "decision": event.decision if event else None,
            "decided_at": event.created_at if event else None,
            "record_hash": event.hash if event else None}


def notify_withdrawal(db: Session, event: ConsentEvent) -> int:
    """Create a notice for every organisation that used this person's data for this use. Returns how many."""
    users = set(db.scalars(select(DataAccessLog.data_user_id).where(
        DataAccessLog.person_id == event.person_id,
        DataAccessLog.data_use_code == event.data_use_code)))
    for du_id in users:
        db.add(WithdrawalNotice(data_user_id=du_id, person_id=event.person_id,
                                data_use_code=event.data_use_code, consent_event_id=event.id))
    db.flush()
    return len(users)


def pending_notices(db: Session, du: DataUser) -> list[dict]:
    rows = db.scalars(select(WithdrawalNotice).where(
        WithdrawalNotice.data_user_id == du.id, WithdrawalNotice.acknowledged_at.is_(None))
        .order_by(WithdrawalNotice.id))
    out = []
    for n in rows:
        person = db.get(Person, n.person_id)
        out.append({"id": n.id, "reference": person.reference, "use": n.data_use_code,
                    "withdrawn_at": db.get(ConsentEvent, n.consent_event_id).created_at})
    return out


def acknowledge(db: Session, du: DataUser, notice_id: int, note: str = "") -> bool:
    n = db.get(WithdrawalNotice, notice_id)
    if n is None or n.data_user_id != du.id:
        return False
    if n.acknowledged_at is None:
        n.acknowledged_at = utcnow()
        n.ack_note = note
        db.flush()
    return True
