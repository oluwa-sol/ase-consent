from ase import consent, datausers, stats
from ase.conversation import handle_message


def _answer(db, who, answers):
    for m in ["hi", "1", *answers]:
        handle_message(db, "telegram", who, m)
    return consent.get_or_create_person(db, "telegram", who)


def test_summary_counts_latest_decisions_only(db):
    _answer(db, "a", ["yes", "yes", "yes", "yes"])
    _answer(db, "b", ["no", "yes", "no", "yes"])
    c = _answer(db, "c", ["yes", "no", "yes", "no"])
    consent.withdraw_all(db, c, "telegram")

    s = stats.summary(db)
    assert s["people"] == 3
    research = next(u for u in s["uses"] if u["code"] == "community_research")
    assert research["counts"] == {"granted": 1, "refused": 1, "withdrawn": 1}
    assert research["answered"] == 3
    assert s["ledger"]["ok"] is True


def test_summary_lists_approved_orgs_and_notice_status(db):
    p = _answer(db, "a", ["yes", "yes", "yes", "yes"])
    du, _ = datausers.register(db, "Uni Lab")
    datausers.approve(db, du, "ai_training")
    datausers.check(db, du, p, "ai_training")
    consent.withdraw_all(db, p, "telegram")

    s = stats.summary(db)
    ai = next(u for u in s["uses"] if u["code"] == "ai_training")
    assert ai["orgs"] == ["Uni Lab"]
    assert s["notices"]["sent"] == 1 and s["notices"]["open"] == 1 and s["notices"]["oldest_open_days"] == 0

    notice = datausers.pending_notices(db, du)[0]["id"]
    datausers.acknowledge(db, du, notice)
    assert stats.summary(db)["notices"]["open"] == 0


def test_revoke_stops_access_immediately(db):
    p = _answer(db, "a", ["yes", "yes", "yes", "yes"])
    du, _ = datausers.register(db, "Lab")
    datausers.approve(db, du, "community_research")
    assert datausers.check(db, du, p, "community_research")["allowed"]
    assert datausers.revoke(db, du, "community_research")
    assert not datausers.check(db, du, p, "community_research")["allowed"]


def test_summary_never_exposes_references(db):
    p = _answer(db, "a", ["yes", "yes", "yes", "yes"])
    assert p.reference not in repr(stats.summary(db))
