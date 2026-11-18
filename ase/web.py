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

from . import consent, datausers, stats
from .db import SessionLocal
from .models import DataUser, DataUserAccess, WithdrawalNotice

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
button.ghost{background:transparent;color:var(--no);border:1px solid var(--line);padding:4px 10px;font-weight:500}
table{width:100%;border-collapse:collapse;font-size:.92rem} td,th{text-align:left;padding:8px 6px;border-bottom:1px solid var(--line);vertical-align:top}
.scroll{overflow-x:auto}.row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;align-items:end}
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
    switch = f'<a class="pill" href="/transparency?lang={other}">{escape(tl["lang"])}</a>'
    body = f"""
<section><h2>{escape(tl['title'])}</h2><p class="lead">{escape(tl['intro'])}</p></section>
<section class="card"><span class="big">{s['people']}</span> {escape(tl['people'])}</section>
<section class="card"><h2>{escape(tl['uses'])}</h2><div class="uses">{''.join(use_html)}</div></section>
<section class="card"><h2>{escape(tl['notices'])}</h2><p class="lead">{escape(tl['notices_intro'])}</p>
<div class="nums"><div class="num"><b>{n['sent']}</b>{escape(tl['sent'])}</div>
<div class="num"><b>{n['confirmed']}</b>{escape(tl['confirmed'])}</div>
<div class="num"><b>{n['open']}</b>{escape(tl['open'])}</div></div><p class="lead" style="margin-top:10px">{notice_note}</p></section>
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
def panel(ase_panel: str | None = Cookie(default=None), new_key: str = "", new_name: str = ""):
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
        org_names = {o.id: o.name for o in orgs}

    titles = {u.code: u.text["en"]["title"] for u in uses}
    use_opts = "".join(f'<option value="{u.code}">{escape(u.text["en"]["title"])}</option>' for u in uses)
    org_opts = "".join(f'<option value="{o.id}">{escape(o.name)}</option>' for o in orgs)

    shown_key = (f"""<section class="card"><h2>New organisation: {escape(new_name)}</h2>
<p class="lead">Give this API key to them now. It will not be shown again.</p><p class="key">{escape(new_key)}</p></section>"""
                 if new_key else "")

    rows = []
    for o in orgs:
        approved = access.get(o.id, [])
        chips = "".join(
            f'<form method="post" action="/panel/revoke" style="display:inline-flex;gap:6px;align-items:center;margin:0 8px 6px 0">'
            f'<input type="hidden" name="data_user_id" value="{o.id}"><input type="hidden" name="use" value="{escape(c)}">'
            f'<span>{escape(titles.get(c, c))}</span><button class="ghost" title="Remove approval">remove</button></form>' for c in approved
        ) or '<span class="lead">Nothing approved yet</span>'
        rows.append(f"<tr><td><b>{escape(o.name)}</b><br><span class='lead'>{escape(o.contact)}</span></td><td>{chips}</td></tr>")

    def age(n):
        created = n.created_at if n.created_at.tzinfo else n.created_at.replace(tzinfo=timezone.utc)
        return (now - created).days

    notice_rows = "".join(
        f"<tr><td>{escape(org_names.get(n.data_user_id, '?'))}</td><td>{escape(titles.get(n.data_use_code, n.data_use_code))}</td><td>{age(n)} day(s)</td></tr>"
        for n in open_notices) or '<tr><td colspan="3" class="lead">No open notices. Every withdrawal has been confirmed.</td></tr>'

    body = f"""{shown_key}
<section class="card"><h2>Register an organisation</h2>
<form method="post" action="/panel/register"><div class="row">
<div><label for="n">Name</label><input id="n" name="name" required maxlength="120"></div>
<div><label for="c">Contact (email or phone)</label><input id="c" name="contact" maxlength="200"></div>
<div><button>Register</button></div></div></form></section>
<section class="card"><h2>Approve a use</h2><p class="lead">Record a decision the community panel has made.</p>
<form method="post" action="/panel/approve"><div class="row">
<div><label for="o">Organisation</label><select id="o" name="data_user_id" required>{org_opts}</select></div>
<div><label for="u">Use</label><select id="u" name="use" required>{use_opts}</select></div>
<div><button>Approve</button></div></div></form></section>
<section class="card"><h2>Organisations</h2><div class="scroll"><table><tr><th>Organisation</th><th>Approved for</th></tr>{''.join(rows) or '<tr><td colspan="2" class="lead">None yet</td></tr>'}</table></div></section>
<section class="card"><h2>Open withdrawal notices</h2><div class="scroll"><table><tr><th>Organisation</th><th>Use</th><th>Open for</th></tr>{notice_rows}</table></div></section>
<form method="post" action="/panel/logout"><button class="ghost">Sign out</button></form>"""
    return _page("Panel", body, switch='<a class="pill" href="/transparency">Public page</a>')


@router.post("/panel/register", response_class=HTMLResponse)
def panel_register(name: str = Form(...), contact: str = Form(""), ase_panel: str | None = Cookie(default=None)):
    if not _admin_ok(ase_panel):
        return HTMLResponse(_login(), status_code=401)
    with SessionLocal() as db:
        du, key = datausers.register(db, name.strip(), contact.strip())
        db.commit()
    # Shown once, directly in the response, never placed in a URL or stored in plain text.
    return panel(ase_panel=ase_panel, new_key=key, new_name=du.name)


@router.post("/panel/approve")
def panel_approve(data_user_id: int = Form(...), use: str = Form(...), ase_panel: str | None = Cookie(default=None)):
    if not _admin_ok(ase_panel):
        return HTMLResponse(_login(), status_code=401)
    with SessionLocal() as db:
        du = db.get(DataUser, data_user_id)
        if du:
            datausers.approve(db, du, use)
            db.commit()
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
