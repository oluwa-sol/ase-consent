"""Web pages: a public transparency page and a password-protected panel page.

Self-contained on purpose: no web fonts, CDNs, analytics or trackers. A page about health-data
consent should not leak its visitors to third parties.
"""

import hmac
import os
from datetime import datetime, timezone
from html import escape

from fastapi import APIRouter, Cookie, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select

from . import consent, datausers, notify, requests_flow, stats
from .db import SessionLocal
from .models import AccessRequest, DataUser, DataUserAccess, WithdrawalNotice

router = APIRouter()
COOKIE = "ase_panel"

L = {
    "en": {
        "tagline": "Community-controlled consent for health data",
        "title": "Transparency",
        "intro": "This page shows, in public and in real time, what people have agreed to, who is allowed to use the data, and whether every withdrawal has been respected. It never shows anyone's personal information.",
        "people": "people have made their choices",
        "uses": "What people agreed to",
        "yes": "Yes", "no": "No", "withdrawn": "Withdrawn",
        "nobody": "No answers yet",
        "orgs": "Organisations allowed to use this",
        "no_orgs": "No organisation is approved for this yet",
        "notices": "Withdrawals respected",
        "notices_intro": "When someone withdraws, every organisation that used their data is told to stop and must confirm it.",
        "sent": "Notices sent", "confirmed": "Confirmed", "open": "Still open",
        "oldest": "Oldest open notice: {d} day(s)",
        "all_kept": "Every notice has been confirmed.",
        "record": "Consent record check",
        "ok": "Untampered", "broken": "Problem found",
        "record_ok": "All {n} saved decisions are intact. Each one is chained to the one before it, so any change would be detected.",
        "record_bad": "The record was changed at entry {i}. This must be investigated.",
        "updated": "Updated",
        "source": "Open source",
        "lang": "Pidgin",
        "requests": "Who has asked for the data",
        "requests_intro": "Organisations must ask the community panel, explain why, and say what they will give back.",
        "req_pending": "Waiting", "req_approved": "Approved", "req_declined": "Declined",
        "org_cta": "Are you an organisation? Request access",
        "for_orgs": "For organisations",
        "org_box": "Are you an organisation that wants to use this data? Look at what people have agreed to below, then ask the community panel.",
        "org_btn": "Request access",
    },
    "pcm": {
        "tagline": "Community dey control how dem go use health information",
        "title": "Open book",
        "intro": "This page dey show everybody, live, wetin people don agree to, who get permission to use the information, and whether dem respect every withdrawal. E no dey ever show anybody personal information.",
        "people": "people don make their choice",
        "uses": "Wetin people agree to",
        "yes": "Yes", "no": "No", "withdrawn": "Withdraw",
        "nobody": "Nobody don answer yet",
        "orgs": "Organisations wey get permission",
        "no_orgs": "No organisation get permission for this one yet",
        "notices": "Withdrawal wey dem respect",
        "notices_intro": "When person withdraw, we go tell every organisation wey use im information make dem stop, and dem must confirm.",
        "sent": "Notice wey we send", "confirmed": "Dem don confirm", "open": "Never confirm",
        "oldest": "The oldest one wey never confirm: {d} day(s)",
        "all_kept": "Dem don confirm every notice.",
        "record": "Check the record",
        "ok": "Nobody touch am", "broken": "Problem dey",
        "record_ok": "All {n} choice wey we save dey intact. Each one join the one before am, so if anybody change anything, we go know.",
        "record_bad": "Somebody change the record for entry {i}. Dem must check am.",
        "updated": "Last update",
        "source": "Open source",
        "lang": "English",
        "requests": "Who don ask for the information",
        "requests_intro": "Organisation must ask the community panel, explain why dem need am, and talk wetin dem go give back.",
        "req_pending": "Dey wait", "req_approved": "Dem approve", "req_declined": "Dem no gree",
        "org_cta": "You be organisation? Ask for permission here",
        "for_orgs": "For organisations",
        "org_box": "You be organisation wey wan use this information? First look wetin people agree to for down, then ask the community panel.",
        "org_btn": "Ask for permission",
    },
}

CSS = """
:root{--bg:#f6efe2;--card:#fffaf1;--ink:#1c2340;--muted:#5d6380;--indigo:#1f2a5a;--indigo-2:#2f3d7a;
--line:#e4d8c3;--yes:#2f7a4f;--no:#a4442f;--wd:#8a8a9a;--ochre:#c8892b;--ok-bg:#e3f1e7;--bad-bg:#f8e1db}
:root[data-theme="dark"]{--bg:#1a1511;--card:#241d17;--ink:#f1e7d6;--muted:#bfb19b;--indigo:#1f2a5a;
--indigo-2:#c8892b;--line:#3a2f25;--yes:#6cbf8a;--no:#e3876f;--wd:#a39a8c;--ochre:#e3a64f;--ok-bg:#20301f;--bad-bg:#3b2119;color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:var(--indigo-2)}
header{background:var(--indigo);color:#f6efe2;
background-image:radial-gradient(circle at 12px 12px,rgba(246,239,226,.10) 3px,transparent 4px),
repeating-linear-gradient(45deg,rgba(246,239,226,.05) 0 2px,transparent 2px 14px);background-size:24px 24px,auto}
.wrap{max-width:860px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-left,0px)) 0 max(16px,env(safe-area-inset-right,0px))}
header .wrap{padding-block:28px 26px;display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}
.brand{font-family:Georgia,"Times New Roman",serif;font-size:2.4rem;line-height:1;margin:0;letter-spacing:.5px}
.tag{margin:.35rem 0 0;color:#d9d2c3;font-size:.95rem}
.pill{border:1px solid rgba(246,239,226,.45);color:#f6efe2;background:transparent;text-decoration:none;padding:6px 12px;border-radius:999px;font-size:.85rem;font-weight:500;cursor:pointer;font-family:inherit}
.tools{display:flex;gap:8px;align-items:center}
main .wrap{padding-block:24px 48px;display:grid;gap:20px}
h2{font-family:Georgia,serif;font-size:1.35rem;margin:0 0 .4rem}
h3{font-size:1rem;margin:0}
.lead{color:var(--muted);margin:0;max-width:65ch}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px}
.big{font-family:Georgia,serif;font-size:2.6rem;line-height:1;color:var(--ochre)}
.uses{display:grid;gap:14px}
.use{display:grid;gap:8px}
.use+.use{border-top:1px solid var(--line);padding-top:14px}
.use p{margin:0}
.bar{display:flex;height:14px;border-radius:7px;overflow:hidden;background:var(--line)}
.bar span{display:block}
.y{background:var(--yes)}.n{background:var(--no)}.w{background:var(--wd)}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:.9rem;color:var(--muted)}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline}
.orgs{font-size:.9rem;color:var(--muted)} .orgs b{color:var(--ink);font-weight:600}
.nums{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin-top:10px}
.num{background:var(--bg);border-radius:10px;padding:10px;text-align:center}
.num b{display:block;font-size:1.6rem;font-family:Georgia,serif}
.badge{display:inline-block;padding:4px 10px;border-radius:999px;font-weight:600;font-size:.9rem}
.good{background:var(--ok-bg);color:var(--yes)}.bad{background:var(--bad-bg);color:var(--no)}
footer{color:var(--muted);font-size:.85rem;text-align:center;padding-bottom:32px}
form{display:grid;gap:8px} label{font-size:.9rem;color:var(--muted)}
input,select{font:inherit;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink);width:100%}
button{font:inherit;font-weight:600;padding:9px 14px;border:0;border-radius:8px;background:var(--indigo-2);color:#fff;cursor:pointer}
a.btn{display:inline-block;font-weight:600;padding:9px 14px;border-radius:8px;background:var(--indigo-2);color:#fff;text-decoration:none}
button.ghost{background:transparent;color:var(--no);border:1px solid var(--line);padding:4px 10px;font-weight:500}
table{width:100%;border-collapse:collapse;font-size:.92rem} td,th{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
.scroll{overflow-x:auto}
main .wrap>*{min-width:0}
.lead,.orgs,td{overflow-wrap:anywhere}
.status{display:flex;align-items:center;gap:8px;font-size:.9rem;color:var(--muted);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:6px 14px;justify-self:start}
.status i{width:8px;height:8px;border-radius:50%;background:var(--yes);display:inline-block}.status.off i{background:var(--no)}
.orglist{display:grid;gap:14px}.org+.org{border-top:1px solid var(--line);padding-top:14px}
.org .who{margin:0 0 8px}.chips{display:grid;gap:8px}
.chip{display:flex;justify-content:space-between;align-items:center;gap:10px;margin:0;background:var(--bg);border-radius:10px;padding:8px 8px 8px 12px}
.chip span{min-width:0}
@media (max-width:560px){header .wrap{padding-block:20px 18px}.brand{font-size:2rem}.card{padding:14px}
.decide{display:grid!important;grid-template-columns:1fr 1fr}.decide button{width:100%}}.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;align-items:end}
.key{font-family:ui-monospace,Consolas,monospace;word-break:break-all;background:var(--bg);padding:10px;border-radius:8px;border:1px dashed var(--ochre)}
"""


def _page(title: str, body: str, lang: str = "en", switch: str = "") -> str:
    tl = L[lang]
    return f"""<!doctype html><html lang="{'en' if lang == 'en' else 'pcm'}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="referrer" content="no-referrer"><script>try{{if(localStorage.getItem("ase-theme")==="dark")document.documentElement.dataset.theme="dark"}}catch(e){{}}</script><title>{escape(title)} · Àṣẹ</title><style>{CSS}</style></head><body>
<header><div class="wrap"><div><p class="brand">Àṣẹ</p><p class="tag">{escape(tl['tagline'])}</p></div><div class="tools">{switch}<button class="pill" id="theme" type="button" aria-label="Switch light or dark mode">🌙</button></div></div></header>
<main><div class="wrap">{body}</div></main>
<footer><a href="https://github.com/oluwa-sol/ase-consent">{escape(tl['source'])}</a> · Apache 2.0</footer>
<script>(function(){{var b=document.getElementById("theme"),r=document.documentElement;
function show(){{b.textContent=r.dataset.theme==="dark"?"☀️":"🌙"}}show();
b.addEventListener("click",function(){{if(r.dataset.theme==="dark"){{delete r.dataset.theme}}else{{r.dataset.theme="dark"}}
try{{localStorage.setItem("ase-theme",r.dataset.theme||"light")}}catch(e){{}}show()}})}})();</script></body></html>"""


def _pct(part: int, whole: int) -> float:
    return round(100 * part / whole, 1) if whole else 0


@router.get("/transparency", response_class=HTMLResponse)
def transparency(lang: str = "en"):
    lang = lang if lang in L else "en"
    tl = L[lang]
    with SessionLocal() as db:
        s = stats.summary(db)
        rq = requests_flow.counts(db)

    use_html = []
    for u in s["uses"]:
        c, total = u["counts"], u["answered"]
        title = (u["text"].get(lang) or u["text"]["en"])["title"]
        bar = (f'<div class="bar" role="img" aria-label="{c["granted"]} yes, {c["refused"]} no, {c["withdrawn"]} withdrawn">'
               f'<span class="y" style="width:{_pct(c["granted"], total)}%"></span>'
               f'<span class="n" style="width:{_pct(c["refused"], total)}%"></span>'
               f'<span class="w" style="width:{_pct(c["withdrawn"], total)}%"></span></div>') if total else \
              f'<p class="lead">{escape(tl["nobody"])}</p>'
        orgs = (f'{escape(tl["orgs"])}: ' + ", ".join(f"<b>{escape(o)}</b>" for o in u["orgs"])) if u["orgs"] \
            else escape(tl["no_orgs"])
        use_html.append(f"""<div class="use"><h3>{escape(title)}</h3>{bar}
<div class="legend"><span><i class="dot y"></i>{escape(tl['yes'])} {c['granted']}</span>
<span><i class="dot n"></i>{escape(tl['no'])} {c['refused']}</span>
<span><i class="dot w"></i>{escape(tl['withdrawn'])} {c['withdrawn']}</span></div>
<div class="orgs">{orgs}</div></div>""")

    n = s["notices"]
    notice_note = (escape(tl["all_kept"]) if n["open"] == 0 else escape(tl["oldest"].format(d=n["oldest_open_days"])))
    led = s["ledger"]
    led_html = (f'<span class="badge good">✓ {escape(tl["ok"])}</span><p class="lead">{escape(tl["record_ok"].format(n=led["events"]))}</p>'
                if led["ok"] else
                f'<span class="badge bad">! {escape(tl["broken"])}</span><p class="lead">{escape(tl["record_bad"].format(i=led["broken_at"]))}</p>')

    other = "pcm" if lang == "en" else "en"
    switch = (f'<a class="pill" href="/request-access">{escape(tl["for_orgs"])}</a>'
              f'<a class="pill" href="/transparency?lang={other}">{escape(tl["lang"])}</a>')
    body = f"""
<section><h2>{escape(tl['title'])}</h2><p class="lead">{escape(tl['intro'])}</p></section>
<section class="card" style="display:flex;gap:14px;align-items:center;justify-content:space-between;flex-wrap:wrap;border-color:var(--ochre)">
<p style="margin:0;max-width:60ch">{escape(tl['org_box'])}</p><a class="btn" href="/request-access">{escape(tl['org_btn'])} →</a></section>
<section class="card"><span class="big">{s['people']}</span> {escape(tl['people'])}</section>
<section class="card"><h2>{escape(tl['uses'])}</h2><div class="uses">{''.join(use_html)}</div></section>
<section class="card"><h2>{escape(tl['notices'])}</h2><p class="lead">{escape(tl['notices_intro'])}</p>
<div class="nums"><div class="num"><b>{n['sent']}</b>{escape(tl['sent'])}</div>
<div class="num"><b>{n['confirmed']}</b>{escape(tl['confirmed'])}</div>
<div class="num"><b>{n['open']}</b>{escape(tl['open'])}</div></div><p class="lead" style="margin-top:10px">{notice_note}</p></section>
<section class="card"><h2>{escape(tl['requests'])}</h2><p class="lead">{escape(tl['requests_intro'])}</p>
<div class="nums"><div class="num"><b>{rq['approved']}</b>{escape(tl['req_approved'])}</div>
<div class="num"><b>{rq['declined']}</b>{escape(tl['req_declined'])}</div>
<div class="num"><b>{rq['pending']}</b>{escape(tl['req_pending'])}</div></div>
<p style="margin:12px 0 0"><a href="/request-access">{escape(tl['org_cta'])}</a></p></section>
<section class="card"><h2>{escape(tl['record'])}</h2>{led_html}</section>
<p class="lead" style="font-size:.85rem">{escape(tl['updated'])}: {escape(s['generated_at'])} UTC</p>"""
    return _page(tl["title"], body, lang, switch)


# ---------- panel (admin) ----------

def _admin_ok(key: str | None) -> bool:
    expected = os.environ.get("ASE_ADMIN_KEY") or os.environ.get("ASE_ORG_API_KEY", "")
    return bool(expected and key and hmac.compare_digest(key, expected))


def _login(msg: str = "") -> str:
    m = f'<p class="badge bad">{escape(msg)}</p>' if msg else ""
    return _page("Panel", f"""<section class="card"><h2>Panel sign in</h2>
<p class="lead">For the community panel and the health organisation only.</p>{m}
<form method="post" action="/panel/login"><label for="k">Admin key</label>
<input id="k" name="key" type="password" autocomplete="current-password" required><button>Sign in</button></form></section>""")


def _redirect_with(cookie_key: str | None = None) -> RedirectResponse:
    r = RedirectResponse("/panel", status_code=303)
    if cookie_key is not None:
        r.set_cookie(COOKIE, cookie_key, httponly=True, secure=True, samesite="strict", max_age=8 * 3600)
    return r


@router.post("/panel/login")
def panel_login(key: str = Form(...)):
    if not _admin_ok(key):
        return HTMLResponse(_login("That key is not right."), status_code=401)
    return _redirect_with(key)


@router.post("/panel/logout")
def panel_logout():
    r = RedirectResponse("/panel", status_code=303)
    r.delete_cookie(COOKIE)
    return r


@router.get("/panel", response_class=HTMLResponse)
def panel(ase_panel: str | None = Cookie(default=None), msg: str = ""):
    if not _admin_ok(ase_panel):
        return _login()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        uses = consent.active_uses(db)
        orgs = list(db.scalars(select(DataUser).order_by(DataUser.name)))
        access = {}
        for a in db.scalars(select(DataUserAccess)):
            access.setdefault(a.data_user_id, []).append(a.data_use_code)
        open_notices = list(db.scalars(select(WithdrawalNotice).where(WithdrawalNotice.acknowledged_at.is_(None))
                                       .order_by(WithdrawalNotice.created_at)))
        waiting = requests_flow.pending(db)
        org_names = {o.id: o.name for o in orgs}

    titles = {u.code: u.text["en"]["title"] for u in uses}

    def days(dt):
        dt = dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return (now - dt).days

    req_cards = []
    for r in waiting:
        wanted = ", ".join(escape(titles.get(c, c)) for c in r.uses)
        req_cards.append(f"""<div class="use"><h3>{escape(r.org_name)}</h3>
<p class="orgs">{escape(r.contact_name)} · {escape(r.contact_email)} · waiting {days(r.created_at)} day(s)</p>
<p><b>Wants:</b> {wanted}</p>
<p><b>Why they need it:</b><br>{escape(r.purpose)}</p>
<p><b>What they will give back to the community:</b><br>{escape(r.benefit)}</p>
<form method="post" action="/panel/requests/{r.id}/decide"><div class="row">
<div><label for="note{r.id}">Note to the organisation (required if declining)</label><input id="note{r.id}" name="note" maxlength="1000"></div>
<div class="decide" style="display:flex;gap:8px"><button name="decision" value="approve">Approve</button>
<button name="decision" value="decline" class="ghost">Decline</button></div></div></form></div>""")
    requests_html = "".join(req_cards) or '<p class="lead">No requests waiting.</p>'

    rows = []
    for o in orgs:
        approved = access.get(o.id, [])
        chips = "".join(
            f'<form method="post" action="/panel/revoke" class="chip">'
            f'<input type="hidden" name="data_user_id" value="{o.id}"><input type="hidden" name="use" value="{escape(c)}">'
            f'<span>{escape(titles.get(c, c))}</span><button class="ghost" title="Remove approval">remove</button></form>' for c in approved
        ) or '<span class="lead">Nothing approved</span>'
        rows.append(f"<div class='org'><p class='who'><b>{escape(o.name)}</b><br><span class='lead'>{escape(o.contact)}</span></p><div class='chips'>{chips}</div></div>")

    notice_rows = "".join(
        f"<tr><td>{escape(org_names.get(n.data_user_id, '?'))}</td><td>{escape(titles.get(n.data_use_code, n.data_use_code))}</td><td>{days(n.created_at)} day(s)</td></tr>"
        for n in open_notices) or '<tr><td colspan="3" class="lead">No open notices. Every withdrawal has been confirmed.</td></tr>'

    flash = f'<p class="badge bad">{escape(msg)}</p>' if msg else ""
    email_state = ('<p class="status"><i></i>Email notices on</p>' if notify.enabled()
                   else '<p class="status off"><i></i>Email notices off (SMTP settings not found)</p>')
    body = f"""{flash}{email_state}
<section class="card"><h2>Access requests ({len(waiting)})</h2>
<p class="lead">Organisations ask here. Approving creates their access for exactly the uses listed; they collect their key once from their private link.</p>
<div class="uses" style="margin-top:12px">{requests_html}</div></section>
<section class="card"><h2>Organisations</h2><div class="orglist">{''.join(rows) or '<p class="lead">None yet</p>'}</div></section>
<section class="card"><h2>Open withdrawal notices</h2><div class="scroll"><table><tr><th>Organisation</th><th>Use</th><th>Open for</th></tr>{notice_rows}</table></div></section>
<form method="post" action="/panel/logout"><button class="ghost">Sign out</button></form>"""
    return _page("Panel", body, switch='<a class="pill" href="/transparency">Public page</a>')


@router.post("/panel/requests/{request_id}/decide")
def panel_decide(request_id: int, decision: str = Form(...), note: str = Form(""),
                 ase_panel: str | None = Cookie(default=None)):
    if not _admin_ok(ase_panel):
        return HTMLResponse(_login(), status_code=401)
    with SessionLocal() as db:
        req = db.get(AccessRequest, request_id)
        try:
            if req is None:
                raise ValueError("unknown request")
            if decision == "approve":
                requests_flow.approve(db, req, note)
            else:
                requests_flow.decline(db, req, note)
            db.commit()
        except ValueError as e:
            return panel(ase_panel=ase_panel, msg=str(e))
    return _redirect_with()


@router.post("/panel/revoke")
def panel_revoke(data_user_id: int = Form(...), use: str = Form(...), ase_panel: str | None = Cookie(default=None)):
    if not _admin_ok(ase_panel):
        return HTMLResponse(_login(), status_code=401)
    with SessionLocal() as db:
        du = db.get(DataUser, data_user_id)
        if du:
            datausers.revoke(db, du, use)
            db.commit()
    return _redirect_with()


# ---------- organisations: request access ----------

def _request_form(uses, error: str = "", values: dict | None = None) -> str:
    v = values or {}
    chosen = set(v.get("uses", []))
    boxes = "".join(
        f'<label style="display:flex;gap:10px;align-items:flex-start;color:var(--ink)">'
        f'<input type="checkbox" name="uses" value="{u.code}" style="width:auto;margin-top:5px"'
        f'{" checked" if u.code in chosen else ""}><span><b>{escape(u.text["en"]["title"])}</b><br>'
        f'<span class="orgs">{escape(u.text["en"]["explain"])}</span></span></label>' for u in uses)
    err = f'<p class="badge bad">{escape(error)}</p>' if error else ""
    def val(k): return escape(v.get(k, ""))
    return f"""<section><h2>Request access to community data</h2>
<p class="lead">Àṣẹ data is controlled by the community. Tell the community panel who you are, why you need the data, and what you will give back. They decide. You will only ever receive data from people who said YES.</p></section>
<section class="card">{err}
<form method="post" action="/request-access">
<div class="row"><div><label for="o">Organisation name</label><input id="o" name="org_name" required maxlength="120" value="{val('org_name')}"></div>
<div><label for="cn">Contact person</label><input id="cn" name="contact_name" required maxlength="120" value="{val('contact_name')}"></div>
<div><label for="ce">Contact email</label><input id="ce" name="contact_email" type="email" required maxlength="200" value="{val('contact_email')}"></div></div>
<label style="margin-top:8px">Which uses are you asking for?</label>
<div style="display:grid;gap:10px">{boxes}</div>
<label for="p" style="margin-top:8px">Why do you need this data? What exactly will you do with it?</label>
<textarea id="p" name="purpose" required maxlength="3000" rows="5" style="font:inherit;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)">{val('purpose')}</textarea>
<label for="b">What will you give back to the community?</label>
<textarea id="b" name="benefit" required maxlength="3000" rows="4" style="font:inherit;padding:9px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--ink)">{val('benefit')}</textarea>
<div style="position:absolute;left:-5000px" aria-hidden="true"><label for="w">Leave this empty</label><input id="w" name="website" tabindex="-1" autocomplete="off"></div>
<label style="display:flex;gap:10px;align-items:flex-start;color:var(--ink);margin-top:8px"><input type="checkbox" name="agree" value="yes" required style="width:auto;margin-top:5px">
<span>We will check consent with Àṣẹ before every use, stop as soon as someone withdraws, and confirm every withdrawal notice.</span></label>
<button style="margin-top:8px">Send request</button></form></section>"""


@router.get("/request-access", response_class=HTMLResponse)
def request_access_form():
    with SessionLocal() as db:
        uses = consent.active_uses(db)
    return _page("Request access", _request_form(uses), switch='<a class="pill" href="/transparency">← See what people agreed to</a>')


@router.post("/request-access", response_class=HTMLResponse)
def request_access_submit(org_name: str = Form(""), contact_name: str = Form(""), contact_email: str = Form(""),
                          purpose: str = Form(""), benefit: str = Form(""), agree: str = Form(""),
                          website: str = Form(""), uses: list[str] = Form(default=[])):
    switch = '<a class="pill" href="/transparency">← See what people agreed to</a>'
    if website:  # bots fill the hidden field; people never see it
        return _page("Request access", '<section class="card"><p>Thank you.</p></section>', switch=switch)
    values = {"org_name": org_name, "contact_name": contact_name, "contact_email": contact_email,
              "purpose": purpose, "benefit": benefit, "uses": uses}
    with SessionLocal() as db:
        all_uses = consent.active_uses(db)
        try:
            if agree != "yes":
                raise ValueError("please agree to check consent and confirm every withdrawal")
            req, token = requests_flow.submit(db, org_name=org_name, contact_name=contact_name,
                                              contact_email=contact_email, uses=uses, purpose=purpose, benefit=benefit)
            db.commit()
        except ValueError as e:
            return HTMLResponse(_page("Request access", _request_form(all_uses, str(e), values), switch=switch),
                                status_code=400)
    link = f"/request-access/status/{token}"
    body = f"""<section class="card"><h2>Request sent</h2>
<p>The community panel will review it. <b>Save this private link now.</b> It is the only way to see the decision and,
if approved, to collect your API key. It is not stored anywhere readable, so it cannot be sent to you again.</p>
<p class="key"><a href="{escape(link)}">{escape(link)}</a></p>
<p class="lead">Add it to your bookmarks, or copy the full address from your browser after opening it.</p></section>"""
    return _page("Request sent", body, switch=switch)


@router.get("/request-access/status/{token}", response_class=HTMLResponse)
def request_status(token: str):
    switch = '<a class="pill" href="/transparency">← See what people agreed to</a>'
    with SessionLocal() as db:
        req = requests_flow.by_token(db, token)
        if req is None:
            return HTMLResponse(_page("Request status", '<section class="card"><h2>Not found</h2><p class="lead">This link is not valid.</p></section>', switch=switch), status_code=404)
        key = requests_flow.issue_key(db, req)
        db.commit()
        titles = {u.code: u.text["en"]["title"] for u in consent.active_uses(db)}
        wanted = ", ".join(escape(titles.get(c, c)) for c in req.uses)
        if req.status == "pending":
            state = '<span class="badge" style="background:var(--bg)">Waiting for the community panel</span><p class="lead">Check this page again later.</p>'
        elif req.status == "declined":
            state = f'<span class="badge bad">Declined</span><p><b>Reason from the panel:</b><br>{escape(req.decision_note)}</p>'
        elif key:
            state = (f'<span class="badge good">✓ Approved</span>'
                     + (f'<p><b>Note from the panel:</b><br>{escape(req.decision_note)}</p>' if req.decision_note else "")
                     + f'<p><b>Your API key.</b> Copy it now and store it safely. <b>It will never be shown again</b>, not even to you on this page.</p>'
                     f'<p class="key">{escape(key)}</p>'
                     '<p class="lead">Send it as the <code>X-API-Key</code> header to <code>/v1/consent/check</code> before every use, '
                     'and check <code>/v1/notices</code> regularly for withdrawals you must confirm.</p>')
        else:
            state = ('<span class="badge good">✓ Approved</span><p class="lead">Your API key was already shown once on this page. '
                     'If it was lost, contact the community panel to request a new one.</p>')
        body = f"""<section class="card"><h2>{escape(req.org_name)}</h2>
<p class="lead">Asked for: {wanted}</p>{state}</section>"""
    return _page("Request status", body, switch=switch)
