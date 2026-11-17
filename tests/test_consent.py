from ase import consent


def test_same_channel_id_is_same_person(db):
    a = consent.get_or_create_person(db, "telegram", "42")
    b = consent.get_or_create_person(db, "telegram", "42")
    assert a.id == b.id
    assert a.reference.startswith("ASE-")


def test_different_channels_are_different_people_until_linked(db):
    a = consent.get_or_create_person(db, "telegram", "42")
    b = consent.get_or_create_person(db, "whatsapp", "42")
    assert a.id != b.id


def test_latest_decision_wins(db):
    p = consent.get_or_create_person(db, "telegram", "7")
    use = consent.active_uses(db)[0]
    consent.record(db, p, use, "granted", "telegram")
    assert consent.is_allowed(db, p, use.code)
    consent.record(db, p, use, "refused", "telegram")
    assert not consent.is_allowed(db, p, use.code)


def test_not_asked_means_not_allowed(db):
    p = consent.get_or_create_person(db, "telegram", "8")
    assert not consent.is_allowed(db, p, "ai_training")


def test_withdraw_all_only_touches_granted(db):
    p = consent.get_or_create_person(db, "telegram", "9")
    uses = consent.active_uses(db)
    consent.record(db, p, uses[0], "granted", "telegram")
    consent.record(db, p, uses[1], "refused", "telegram")
    consent.record(db, p, uses[2], "granted", "telegram")
    withdrawn = consent.withdraw_all(db, p, "telegram")
    assert sorted(withdrawn) == sorted([uses[0].code, uses[2].code])
    assert not any(consent.is_allowed(db, p, u.code) for u in uses)
    assert consent.latest_decisions(db, p)[uses[1].code].decision == "refused"
