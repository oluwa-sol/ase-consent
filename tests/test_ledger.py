from ase import consent, ledger
from ase.models import ConsentEvent


def _grant_some(db):
    p = consent.get_or_create_person(db, "telegram", "111")
    uses = consent.active_uses(db)
    for u in uses[:3]:
        consent.record(db, p, u, "granted", "telegram")
    return p


def test_chain_verifies(db):
    _grant_some(db)
    result = ledger.verify_chain(db)
    assert result == {"ok": True, "events": 3, "broken_at": None}


def test_editing_a_past_decision_is_detected(db):
    _grant_some(db)
    second = db.query(ConsentEvent).order_by(ConsentEvent.id).all()[1]
    second.decision = "refused"  # someone quietly changes a YES to a NO
    db.flush()
    result = ledger.verify_chain(db)
    assert result["ok"] is False
    assert result["broken_at"] == second.id


def test_deleting_an_event_is_detected(db):
    _grant_some(db)
    first = db.query(ConsentEvent).order_by(ConsentEvent.id).first()
    db.delete(first)
    db.flush()
    assert ledger.verify_chain(db)["ok"] is False


def test_unknown_decision_rejected(db):
    p = consent.get_or_create_person(db, "telegram", "1")
    use = consent.active_uses(db)[0]
    try:
        ledger.append(db, person_id=p.id, data_use_code=use.code, decision="maybe",
                      channel="telegram", language="en", notice_version="1")
        assert False, "should have raised"
    except ValueError:
        pass
