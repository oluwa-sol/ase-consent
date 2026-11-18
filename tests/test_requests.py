import pytest

from ase import consent, datausers, requests_flow
from ase.conversation import handle_message
from ase.models import AccessRequest


def _submit(db, uses=("ai_training",)):
    return requests_flow.submit(db, org_name="Uni Lab", contact_name="Ada", contact_email="ada@uni.example",
                                uses=list(uses), purpose="Study youth mental health needs",
                                benefit="Share findings in community meetings")


def test_submit_stores_only_a_hash_of_the_private_link(db):
    req, token = _submit(db)
    assert req.status == "pending" and token not in req.token_hash
    assert requests_flow.by_token(db, token).id == req.id
    assert requests_flow.by_token(db, "wrong") is None


@pytest.mark.parametrize("bad", [
    {"uses": []},
    {"uses": ["not_a_real_use"]},
    {"contact_email": "no-at-sign"},
    {"purpose": "   "},
    {"benefit": ""},
])
def test_submit_rejects_incomplete_requests(db, bad):
    kwargs = dict(org_name="Lab", contact_name="Ada", contact_email="a@b.c", uses=["ai_training"],
                  purpose="p", benefit="b")
    kwargs.update(bad)
    with pytest.raises(ValueError):
        requests_flow.submit(db, **kwargs)


def test_approve_grants_exactly_the_requested_uses_and_key_is_shown_once(db):
    req, token = _submit(db, uses=("ai_training", "community_research"))
    du = requests_flow.approve(db, req, "Approved for one year")
    assert datausers.is_approved(db, du, "ai_training")
    assert datausers.is_approved(db, du, "community_research")
    assert not datausers.is_approved(db, du, "partner_sharing")

    key = requests_flow.issue_key(db, requests_flow.by_token(db, token))
    assert key and key.startswith("ase_")
    assert datausers.by_key(db, key).id == du.id
    assert requests_flow.issue_key(db, req) is None  # never shown again


def test_approved_org_has_no_working_key_until_it_collects_it(db):
    req, _ = _submit(db)
    du = requests_flow.approve(db, req)
    assert du.api_key_hash  # placeholder only; no key string maps to it
    assert db.query(AccessRequest).one().key_issued is False


def test_decline_needs_a_reason_and_gives_no_access(db):
    req, token = _submit(db)
    with pytest.raises(ValueError):
        requests_flow.decline(db, req, "  ")
    requests_flow.decline(db, req, "Purpose too broad")
    assert req.status == "declined" and req.data_user_id is None
    assert requests_flow.issue_key(db, req) is None


def test_cannot_decide_twice(db):
    req, _ = _submit(db)
    requests_flow.approve(db, req)
    with pytest.raises(ValueError):
        requests_flow.decline(db, req, "changed mind")


def test_full_loop_request_to_withdrawal_notice(db):
    for m in ["hi", "1", "yes", "yes", "yes", "yes"]:
        handle_message(db, "telegram", "p", m)
    person = consent.get_or_create_person(db, "telegram", "p")
    req, token = _submit(db)
    requests_flow.approve(db, req)
    key = requests_flow.issue_key(db, requests_flow.by_token(db, token))
    org = datausers.by_key(db, key)
    assert datausers.check(db, org, person, "ai_training")["allowed"]
    consent.withdraw_all(db, person, "telegram")
    assert len(datausers.pending_notices(db, org)) == 1


def test_counts(db):
    a, _ = _submit(db)
    b, _ = _submit(db)
    _submit(db)
    requests_flow.approve(db, a)
    requests_flow.decline(db, b, "no")
    assert requests_flow.counts(db) == {"pending": 1, "approved": 1, "declined": 1}
