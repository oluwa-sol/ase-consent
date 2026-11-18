"""Email notifications to organisations. Off unless SMTP settings are configured.

The email never contains the API key, only a note that a decision is ready on the organisation's
private status link (which they saved when they applied).

Settings: SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD, SMTP_FROM.
"""

import os
import smtplib
from email.message import EmailMessage


def enabled() -> bool:
    return bool(os.environ.get("SMTP_HOST") and os.environ.get("SMTP_FROM"))


def send(to: str, subject: str, body: str) -> bool:
    if not enabled():
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ["SMTP_FROM"], to, subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(os.environ["SMTP_HOST"], int(os.environ.get("SMTP_PORT", "587")), timeout=20) as s:
            s.starttls()
            if os.environ.get("SMTP_USER"):
                s.login(os.environ["SMTP_USER"], os.environ.get("SMTP_PASSWORD", ""))
            s.send_message(msg)
        return True
    except Exception as e:  # a failed email must never block the panel's decision
        print(f"[notify] email to {to} failed: {e}")
        return False


def decision(req) -> bool:
    outcome = "approved" if req.status == "approved" else "declined"
    body = (f"Hello {req.contact_name},\n\n"
            f"The community panel has {outcome} {req.org_name}'s request to use data through Àṣẹ.\n\n"
            "Open the private status link you saved when you applied to see the details"
            + (" and collect your API key (it is shown only once)." if outcome == "approved" else ".")
            + "\n\nÀṣẹ")
    return send(req.contact_email, f"Àṣẹ: your access request was {outcome}", body)
