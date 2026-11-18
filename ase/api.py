"""HTTP API.

- /telegram/webhook: incoming Telegram messages.
- /v1/consent/check: how an organisation's own system asks "may I use this person's data for X?"
- /v1/ledger/verify: anyone can check the consent record has not been tampered with.
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select

from . import consent, ledger
from .channels import telegram, whatsapp
from .db import SessionLocal, init_db
from .models import DataUse, Person
from .seed import seed_uses


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    with SessionLocal() as db:
        seed_uses(db)
        db.commit()
    yield


app = FastAPI(title="Àṣẹ", version="0.1.0", lifespan=lifespan)


def _check_org_key(key: str | None) -> None:
    expected = os.environ.get("ASE_ORG_API_KEY", "")
    if not expected or key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing API key")


@app.get("/")
def about():
    return {
        "name": "Àṣẹ",
        "about": "Community-controlled consent for health data, on WhatsApp and Telegram.",
        "source": "https://github.com/oluwa-sol/ase-consent",
        "endpoints": ["/health", "/v1/uses", "/v1/ledger/verify", "/v1/consent/check (API key)"],
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


@app.get("/v1/consent/check")
def consent_check(reference: str, use: str, x_api_key: str | None = Header(default=None)):
    """Ask before using data. Answers only allowed/not allowed, never anything else about the person."""
    _check_org_key(x_api_key)
    with SessionLocal() as db:
        if db.get(DataUse, use) is None:
            raise HTTPException(status_code=404, detail="unknown data use")
        person = db.scalars(select(Person).where(Person.reference == reference.upper())).first()
        if person is None:
            return {"reference": reference, "use": use, "allowed": False, "decision": None}
        e = consent.latest_decisions(db, person).get(use)
        return {
            "reference": person.reference,
            "use": use,
            "allowed": bool(e and e.decision == "granted"),
            "decision": e.decision if e else None,
            "decided_at": e.created_at if e else None,
            "record_hash": e.hash if e else None,
        }


@app.get("/v1/ledger/verify")
def ledger_verify():
    with SessionLocal() as db:
        return ledger.verify_chain(db)


@app.get("/v1/uses")
def list_uses():
    with SessionLocal() as db:
        return [{"code": u.code, "text": u.text, "notice_version": u.notice_version} for u in consent.active_uses(db)]
