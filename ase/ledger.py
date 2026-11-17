"""Tamper-evident consent ledger.

Every consent decision is appended as a ConsentEvent whose hash covers its own
fields plus the previous event's hash. Editing or deleting any past event breaks
the chain, and verify_chain() reports exactly where.
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import ConsentEvent

GENESIS = "0" * 64
DECISIONS = {"granted", "refused", "withdrawn"}


def _digest(fields: dict, prev_hash: str) -> str:
    payload = json.dumps({**fields, "prev_hash": prev_hash}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _fields(e: ConsentEvent) -> dict:
    return {
        "person_id": e.person_id,
        "data_use_code": e.data_use_code,
        "decision": e.decision,
        "channel": e.channel,
        "language": e.language,
        "notice_version": e.notice_version,
        "created_at": e.created_at,
    }


def last_hash(db: Session) -> str:
    last = db.scalars(select(ConsentEvent).order_by(ConsentEvent.id.desc()).limit(1)).first()
    return last.hash if last else GENESIS


def append(db: Session, *, person_id: int, data_use_code: str, decision: str,
           channel: str, language: str, notice_version: str) -> ConsentEvent:
    if decision not in DECISIONS:
        raise ValueError(f"unknown decision {decision!r}")
    event = ConsentEvent(
        person_id=person_id,
        data_use_code=data_use_code,
        decision=decision,
        channel=channel,
        language=language,
        notice_version=notice_version,
        created_at=datetime.now(timezone.utc).isoformat(timespec="microseconds"),
    )
    event.prev_hash = last_hash(db)
    event.hash = _digest(_fields(event), event.prev_hash)
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session) -> dict:
    """Recompute every hash in order. Returns {"ok": bool, "events": n, "broken_at": id|None}."""
    prev = GENESIS
    count = 0
    for e in db.scalars(select(ConsentEvent).order_by(ConsentEvent.id)):
        count += 1
        if e.prev_hash != prev or _digest(_fields(e), prev) != e.hash:
            return {"ok": False, "events": count, "broken_at": e.id}
        prev = e.hash
    return {"ok": True, "events": count, "broken_at": None}
