"""HTTP API.

- /telegram/webhook: incoming Telegram messages.
- /v1/admin/...: register organisations and record which uses they're approved for (admin key).
- /v1/consent/check: how an organisation's own system asks "may I use this person's data for X?" (its own key)
- /v1/notices: withdrawals an organisation must act on, and confirm (its own key)
- /v1/ledger/verify: anyone can check the consent record has not been tampered with.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select

from . import consent, datausers, ledger, web
from .channels import telegram, whatsapp
from .db import SessionLocal, init_db
from .models import DataUse, DataUser, Person
from .seed import seed_uses


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_uses(db)
        db.commit()
    yield


app = FastAPI(title="Àṣẹ", version="0.1.0", lifespan=lifespan)
app.include_router(web.router)


def _check_admin_key(key: str | None) -> None:
    expected = os.environ.get("ASE_ADMIN_KEY") or os.environ.get("ASE_ORG_API_KEY", "")
    if not expected or key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.get("/")
def about():
    return {
        "name": "Àṣẹ",
        "about": "Community-controlled consent for health data, on WhatsApp and Telegram.",
        "source": "https://github.com/oluwa-sol/ase-consent",
        "pages": ["/transparency", "/transparency?lang=pcm"],
        "endpoints": ["/health", "/v1/uses", "/v1/ledger/verify", "/v1/consent/check (org key)", "/v1/notices (org key)"],
    }


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request,
                           x_telegram_bot_api_secret_token: str | None = Header(default=None)):
    secret = os.environ.get("TELEGRAM_WEBHOOK_SECRET", "")
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="bad secret")
    telegram.process_update(await request.json())
    return {"ok": True}


@app.get("/whatsapp/webhook")
def whatsapp_verify(request: Request):
    """Meta calls this once when you save the webhook URL, to check you own it."""
    q = request.query_params
    expected = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
    if q.get("hub.mode") == "subscribe" and expected and q.get("hub.verify_token") == expected:
        return PlainTextResponse(q.get("hub.challenge", ""))
    raise HTTPException(status_code=403, detail="verification failed")


@app.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, x_hub_signature_256: str | None = Header(default=None)):
    raw = await request.body()
    if not whatsapp.verify_signature(raw, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="bad signature")
    whatsapp.process_payload(await request.json())
    return {"ok": True}


class NewDataUser(BaseModel):
    name: str
    contact: str = ""


class Approval(BaseModel):
    use: str
    note: str = ""


class Ack(BaseModel):
    note: str = ""


def _data_user(db, key: str | None):
    du = datausers.by_key(db, key)
    if du is None:
        raise HTTPException(status_code=401, detail="invalid or missing API key")
    return du


@app.post("/v1/admin/data-users")
def admin_register(body: NewDataUser, x_admin_key: str | None = Header(default=None)):
    """Register an organisation. Its API key is shown once here and never again."""
    _check_admin_key(x_admin_key)
    with SessionLocal() as db:
        du, key = datausers.register(db, body.name, body.contact)
        db.commit()
        return {"id": du.id, "name": du.name, "api_key": key,
                "warning": "Store this key now. It cannot be shown again."}


@app.post("/v1/admin/data-users/{data_user_id}/approve")
def admin_approve(data_user_id: int, body: Approval, x_admin_key: str | None = Header(default=None)):
    """Record that the community panel approved this organisation for one data use."""
    _check_admin_key(x_admin_key)
    with SessionLocal() as db:
        du = db.get(DataUser, data_user_id)
        if du is None:
            raise HTTPException(status_code=404, detail="unknown data user")
        try:
            datausers.approve(db, du, body.use, body.note)
        except ValueError as e:
            raise HTTPException(status_code=404, detail=str(e))
        db.commit()
        return {"ok": True, "data_user": du.name, "approved_use": body.use}


@app.get("/v1/consent/check")
def consent_check(reference: str, use: str, x_api_key: str | None = Header(default=None)):
    """Ask before using data. Answers only allowed or not, never anything else about the person.

    Allowed needs both: the organisation is approved for this use, and the person said YES.
    An "allowed" answer is logged, so the organisation is notified if the person later withdraws.
    """
    with SessionLocal() as db:
        du = _data_user(db, x_api_key)
        if db.get(DataUse, use) is None:
            raise HTTPException(status_code=404, detail="unknown data use")
        person = db.scalars(select(Person).where(Person.reference == reference.upper())).first()
        result = datausers.check(db, du, person, use)
        db.commit()
        return {"reference": person.reference if person else reference, "use": use, **result}


@app.get("/v1/notices")
def notices(x_api_key: str | None = Header(default=None)):
    """Withdrawals this organisation still has to act on."""
    with SessionLocal() as db:
        return datausers.pending_notices(db, _data_user(db, x_api_key))


@app.post("/v1/notices/{notice_id}/ack")
def notice_ack(notice_id: int, body: Ack, x_api_key: str | None = Header(default=None)):
    """Confirm the organisation has stopped using (and removed) this person's data for this use."""
    with SessionLocal() as db:
        if not datausers.acknowledge(db, _data_user(db, x_api_key), notice_id, body.note):
            raise HTTPException(status_code=404, detail="unknown notice")
        db.commit()
        return {"ok": True}


@app.get("/v1/ledger/verify")
def ledger_verify():
    with SessionLocal() as db:
        return ledger.verify_chain(db)


@app.get("/v1/uses")
def list_uses():
    with SessionLocal() as db:
        return [{"code": u.code, "text": u.text, "notice_version": u.notice_version} for u in consent.active_uses(db)]
