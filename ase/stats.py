"""Aggregate numbers for the public transparency page. Never returns anything about an individual."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import consent, ledger
from .models import ConsentEvent, DataUser, DataUserAccess, Person, WithdrawalNotice


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def summary(db: Session) -> dict:
    uses = consent.active_uses(db)

    # latest decision per (person, use): the latest event always wins
    latest: dict[tuple[int, str], str] = {}
    for e in db.scalars(select(ConsentEvent).order_by(ConsentEvent.id)):
        latest[(e.person_id, e.data_use_code)] = e.decision

    per_use = []
    for u in uses:
        counts = {"granted": 0, "refused": 0, "withdrawn": 0}
        for (_, code), decision in latest.items():
            if code == u.code:
                counts[decision] += 1
        orgs = list(db.scalars(
            select(DataUser.name).join(DataUserAccess, DataUserAccess.data_user_id == DataUser.id)
            .where(DataUserAccess.data_use_code == u.code, DataUser.active).order_by(DataUser.name)))
        per_use.append({"code": u.code, "text": u.text, "counts": counts,
                        "answered": sum(counts.values()), "orgs": orgs})

    notices = list(db.scalars(select(WithdrawalNotice)))
    open_ = [n for n in notices if n.acknowledged_at is None]
    now = datetime.now(timezone.utc)
    oldest_open_days = max(((now - _aware(n.created_at)).days for n in open_), default=None)

    return {
        "people": db.scalar(select(func.count(Person.id))) or 0,
        "uses": per_use,
        "notices": {"sent": len(notices), "confirmed": len(notices) - len(open_),
                    "open": len(open_), "oldest_open_days": oldest_open_days},
        "ledger": ledger.verify_chain(db),
        "generated_at": now.strftime("%d %b %Y, %H:%M"),
    }
