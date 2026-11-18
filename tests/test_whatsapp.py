import hashlib
import hmac
import json

from ase.channels import whatsapp

SAMPLE = {
    "object": "whatsapp_business_account",
    "entry": [{"changes": [{"field": "messages", "value": {
        "messages": [
            {"from": "2348000000001", "type": "text", "text": {"body": "hi"}},
            {"from": "2348000000002", "type": "button", "button": {"text": "YES"}},
            {"from": "2348000000003", "type": "interactive", "interactive": {"button_reply": {"title": "NO"}}},
            {"from": "2348000000004", "type": "image", "image": {"id": "x"}},
        ],
        "statuses": [{"id": "wamid.x", "status": "read"}],
    }}]}],
}


def test_extracts_text_and_button_replies_only():
    assert whatsapp.extract_messages(SAMPLE) == [
        ("2348000000001", "hi"),
        ("2348000000002", "YES"),
        ("2348000000003", "NO"),
    ]


def test_status_only_payload_gives_nothing():
    payload = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    assert whatsapp.extract_messages(payload) == []


def test_signature_check():
    body = json.dumps(SAMPLE).encode()
    good = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert whatsapp.verify_signature(body, good, app_secret="s3cret")
    assert not whatsapp.verify_signature(body, good, app_secret="other")
    assert not whatsapp.verify_signature(body + b" ", good, app_secret="s3cret")
    assert not whatsapp.verify_signature(body, None, app_secret="s3cret")
    assert not whatsapp.verify_signature(body, good, app_secret="")  # no secret configured = reject
