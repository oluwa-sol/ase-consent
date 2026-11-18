"""Data model.

Àṣẹ stores consent and decisions only. It never stores health data.

- Person: a pseudonymous participant, known to organisations only by a short reference code.
- ChannelIdentity: how a person reaches us (WhatsApp number, Telegram chat). One person can have several.
- DataUse: a specific purpose people can say yes or no to (e.g. community research, AI training).
- ConsentEvent: an append-only, hash-chained record of every consent decision.
- Conversation: where a person is in the chat flow, per channel.
"""

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Person(Base):
    __tablename__ = "persons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class ChannelIdentity(Base):
    __tablename__ = "channel_identities"
    __table_args__ = (UniqueConstraint("channel", "external_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))  # "telegram", "whatsapp", "sms"
    external_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class DataUse(Base):
    __tablename__ = "data_uses"

    code: Mapped[str] = mapped_column(String(48), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    # {"en": {"title": ..., "explain": ...}, "pcm": {...}}
    text: Mapped[dict] = mapped_column(JSON)
    notice_version: Mapped[str] = mapped_column(String(16), default="1")
    active: Mapped[bool] = mapped_column(default=True)


class ConsentEvent(Base):
    __tablename__ = "consent_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    data_use_code: Mapped[str] = mapped_column(ForeignKey("data_uses.code"), index=True)
    decision: Mapped[str] = mapped_column(String(16))  # "granted" | "refused" | "withdrawn"
    channel: Mapped[str] = mapped_column(String(16))
    language: Mapped[str] = mapped_column(String(8))
    notice_version: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[str] = mapped_column(String(40))  # ISO 8601 UTC, stored as text so the hash is stable
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64), unique=True)


class DataUser(Base):
    """An organisation that wants to use people's data (a research team, an NGO, an AI project)."""

    __tablename__ = "data_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(200), default="")
    api_key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class AccessRequest(Base):
    """An organisation asking the community for permission to use data.

    The organisation follows its request through a private link. Only a hash of that link's token
    is stored. On approval, the API key is created at the moment they first open the link and is
    never stored readable.
    """

    __tablename__ = "access_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_name: Mapped[str] = mapped_column(String(120))
    contact_name: Mapped[str] = mapped_column(String(120))
    contact_email: Mapped[str] = mapped_column(String(200))
    uses: Mapped[list] = mapped_column(JSON)
    purpose: Mapped[str] = mapped_column(Text)
    benefit: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | approved | declined
    decision_note: Mapped[str] = mapped_column(Text, default="")
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    data_user_id: Mapped[int | None] = mapped_column(ForeignKey("data_users.id"), nullable=True)
    key_issued: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)


class DataUserAccess(Base):
    """Which data uses an organisation has been approved for (by the community panel)."""

    __tablename__ = "data_user_access"
    __table_args__ = (UniqueConstraint("data_user_id", "data_use_code"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_user_id: Mapped[int] = mapped_column(ForeignKey("data_users.id"), index=True)
    data_use_code: Mapped[str] = mapped_column(ForeignKey("data_uses.code"))
    approved_at: Mapped[datetime] = mapped_column(default=utcnow)
    note: Mapped[str] = mapped_column(Text, default="")


class DataAccessLog(Base):
    """Every time an organisation checked a person and was told "allowed". This is how we know who to notify."""

    __tablename__ = "data_access_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_user_id: Mapped[int] = mapped_column(ForeignKey("data_users.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    data_use_code: Mapped[str] = mapped_column(ForeignKey("data_uses.code"))
    at: Mapped[datetime] = mapped_column(default=utcnow)


class WithdrawalNotice(Base):
    """Tells an organisation to stop using one person's data for one use. Stays open until they confirm."""

    __tablename__ = "withdrawal_notices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    data_user_id: Mapped[int] = mapped_column(ForeignKey("data_users.id"), index=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"))
    data_use_code: Mapped[str] = mapped_column(ForeignKey("data_uses.code"))
    consent_event_id: Mapped[int] = mapped_column(ForeignKey("consent_events.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)
    ack_note: Mapped[str] = mapped_column(Text, default="")


class LinkCode(Base):
    """One-time code that joins a second channel to an existing person.

    The code is only ever shown inside a channel the person already controls,
    so knowing someone's reference (ASE-XXXXXX) is never enough to take over their record.
    """

    __tablename__ = "link_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    code: Mapped[str] = mapped_column(String(8), index=True)
    expires_at: Mapped[datetime] = mapped_column()
    used: Mapped[bool] = mapped_column(default=False)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("person_id", "channel"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("persons.id"), index=True)
    channel: Mapped[str] = mapped_column(String(16))
    step: Mapped[str] = mapped_column(String(32), default="new")
    use_index: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
