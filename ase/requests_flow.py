"""Organisations request access; the community panel approves or declines.

Nobody gets data access by being registered by hand. Every organisation submits a request saying
why it wants the data and what it will give back, and the panel decides.
"""

import hashlib
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import datausers, notify
from .models import AccessRequest, DataUse, DataUser, utcnow


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def submit(db: Session, *, org_name: str, contact_name: str, contact_email: str,
           uses: list[str], purpose: str, benefit: str) -> tuple[AccessRequest, str]:
    """Create a pending request. Returns it and the private status token (shown to the organisation once)."""
    valid = {u.code for u in db.scalars(select(DataUse).where(DataUse.active))}
    chosen = [u for u in dict.fromkeys(uses) if u in valid]
    if not chosen:
        raise ValueError("choose at least one data use")
    for field, value in (("organisation name", org_name), ("contact name", contact_name),
                         ("contact email", contact_email), ("purpose", purpose), ("benefit", benefit)):
        if not value or not value.strip():
            raise ValueError(f"{field} is required")
    if "@" not in contact_email:
        raise ValueError("contact email looks wrong")
    token = secrets.token_urlsafe(24)
    req = AccessRequest(org_name=org_name.strip()[:120], contact_name=contact_name.strip()[:120],
                        contact_email=contact_email.strip()[:200], uses=chosen,
                        purpose=purpose.strip()[:3000], benefit=benefit.strip()[:3000], token_hash=_hash(token))
    db.add(req)
    db.flush()
    return req, token


def by_token(db: Session, token: str) -> AccessRequest | None:
    return db.scalars(select(AccessRequest).where(AccessRequest.token_hash == _hash(token))).first()


def approve(db: Session, req: AccessRequest, note: str = "") -> DataUser:
    """Approve: create the organisation (with no usable key yet) and grant every requested use."""
    if req.status != "pending":
        raise ValueError("request already decided")
    du = DataUser(name=req.org_name, contact=req.contact_email,
                  api_key_hash=_hash("unissued:" + secrets.token_hex(16)))  # unusable until the key is issued
    db.add(du)
    db.flush()
    for code in req.uses:
        datausers.approve(db, du, code, note=f"access request #{req.id}")
    req.status, req.decision_note, req.decided_at, req.data_user_id = "approved", note.strip(), utcnow(), du.id
    db.flush()
    notify.decision(req)
    return du


def decline(db: Session, req: AccessRequest, reason: str) -> None:
    if req.status != "pending":
        raise ValueError("request already decided")
    if not reason.strip():
        raise ValueError("a reason is required when declining")
    req.status, req.decision_note, req.decided_at = "declined", reason.strip(), utcnow()
    db.flush()
    notify.decision(req)


def issue_key(db: Session, req: AccessRequest) -> str | None:
    """Create and return the API key the first time an approved organisation opens its link. Never again."""
    if req.status != "approved" or req.key_issued or req.data_user_id is None:
        return None
    key = "ase_" + secrets.token_urlsafe(32)
    du = db.get(DataUser, req.data_user_id)
    du.api_key_hash = _hash(key)
    req.key_issued = True
    db.flush()
    return key


def pending(db: Session) -> list[AccessRequest]:
    return list(db.scalars(select(AccessRequest).where(AccessRequest.status == "pending")
                           .order_by(AccessRequest.created_at)))


def counts(db: Session) -> dict:
    out = {"pending": 0, "approved": 0, "declined": 0}
    for (status,) in db.execute(select(AccessRequest.status)):
        out[status] = out.get(status, 0) + 1
    return out
