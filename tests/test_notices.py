from ase import consent, datausers
from ase.conversation import handle_message
from ase.models import WithdrawalNotice


def _person_all_yes(db, who="p1"):
    for m in ["hi", "1", "yes", "yes", "yes", "yes"]:
        handle_message(db, "telegram", who, m)
    return consent.get_or_create_person(db, "telegram", who)


def test_api_keys_are_stored_hashed_and_work(db):
    du, key = datausers.register(db, "Uni Research Lab")
    assert key.startswith("ase_") and key not in du.api_key_hash
    assert datausers.by_key(db, key).id == du.id
    assert datausers.by_key(db, "ase_wrong") is None
    assert datausers.by_key(db, None) is None


def test_not_allowed_unless_org_approved_for_that_use(db):
    p = _person_all_yes(db)
    du, _ = datausers.register(db, "AI Startup")
    r = datausers.check(db, du, p, "ai_training")
    assert r["allowed"] is False and r["reason"] == "organisation not approved for this use"
    datausers.approve(db, du, "ai_training")
    assert datausers.check(db, du, p, "ai_training")["allowed"] is True
    assert datausers.check(db, du, p, "partner_sharing")["allowed"] is False  # approval is per use


def test_not_allowed_if_person_said_no(db):
    for m in ["hi", "1", "no", "no", "no", "no"]:
        handle_message(db, "telegram", "p2", m)
    p = consent.get_or_create_person(db, "telegram", "p2")
    du, _ = datausers.register(db, "NGO")
    datausers.approve(db, du, "community_research")
    r = datausers.check(db, du, p, "community_research")
    assert r["allowed"] is False and r["reason"] == "person has not agreed"


def test_withdrawal_notifies_only_orgs_that_used_the_data(db):
    p = _person_all_yes(db)
    used, _ = datausers.register(db, "Used it")
    never, _ = datausers.register(db, "Approved but never checked")
    for du in (used, never):
        datausers.approve(db, du, "ai_training")
    datausers.check(db, used, p, "ai_training")  # this org now uses the data

    handle_message(db, "telegram", "p1", "3")
    out = handle_message(db, "telegram", "p1", "yes")[0]
    assert "told 1 organisation" in out

    assert [n["use"] for n in datausers.pending_notices(db, used)] == ["ai_training"]
    assert datausers.pending_notices(db, never) == []


def test_changing_one_answer_to_no_also_notifies(db):
    p = _person_all_yes(db)
    du, _ = datausers.register(db, "Lab")
    datausers.approve(db, du, "community_research")
    datausers.check(db, du, p, "community_research")
    event = consent.record(db, p, consent.active_uses(db)[0], "refused", "telegram")
    assert event.notified == 1


def test_notice_must_be_acknowledged_by_the_right_org(db):
    p = _person_all_yes(db)
    du, _ = datausers.register(db, "Lab")
    other, _ = datausers.register(db, "Someone else")
    datausers.approve(db, du, "ai_training")
    datausers.check(db, du, p, "ai_training")
    consent.withdraw_all(db, p, "telegram")
    notice_id = datausers.pending_notices(db, du)[0]["id"]

    assert datausers.acknowledge(db, other, notice_id) is False  # can't confirm another org's notice
    assert datausers.acknowledge(db, du, notice_id, "deleted from training set") is True
    assert datausers.pending_notices(db, du) == []
    assert db.get(WithdrawalNotice, notice_id).ack_note == "deleted from training set"


def test_no_notice_when_nobody_used_the_data(db):
    p = _person_all_yes(db)
    handle_message(db, "telegram", "p1", "3")
    out = handle_message(db, "telegram", "p1", "yes")[0]
    assert "We have told" not in out
