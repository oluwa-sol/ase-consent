from datetime import timedelta

from ase import consent
from ase.conversation import handle_message
from ase.models import LinkCode, utcnow


def tg(db, text):
    return handle_message(db, "telegram", "tg-1", text)


def wa(db, text, who="wa-1"):
    return handle_message(db, "whatsapp", who, text)


def _telegram_user_with_choices(db):
    tg(db, "hi")
    tg(db, "1")
    for _ in range(4):
        tg(db, "yes")
    return consent.get_or_create_person(db, "telegram", "tg-1")


def _code_from(reply: str) -> str:
    return reply.split("LINK ")[1].split()[0]


def test_link_whatsapp_to_existing_telegram_record(db):
    person = _telegram_user_with_choices(db)
    code = _code_from(tg(db, "5")[0])
    out = wa(db, f"LINK {code}")
    assert person.reference in out[0]
    linked = consent.get_or_create_person(db, "whatsapp", "wa-1")
    assert linked.id == person.id
    assert consent.is_allowed(db, linked, "ai_training")


def test_withdraw_on_one_app_applies_everywhere(db):
    person = _telegram_user_with_choices(db)
    wa(db, f"LINK {_code_from(tg(db, '5')[0])}")
    wa(db, "3")
    wa(db, "yes")
    assert not any(consent.is_allowed(db, person, u.code) for u in consent.active_uses(db))


def test_code_works_only_once(db):
    _telegram_user_with_choices(db)
    code = _code_from(tg(db, "5")[0])
    wa(db, f"LINK {code}")
    assert "wrong or has expired" in wa(db, f"LINK {code}", who="wa-2")[0]


def test_expired_code_rejected(db):
    _telegram_user_with_choices(db)
    code = _code_from(tg(db, "5")[0])
    link = db.query(LinkCode).filter_by(code=code).one()
    link.expires_at = utcnow() - timedelta(minutes=1)
    db.flush()
    assert "wrong or has expired" in wa(db, f"LINK {code}")[0]


def test_wrong_code_rejected(db):
    _telegram_user_with_choices(db)
    assert "wrong or has expired" in wa(db, "LINK 000000")[0]


def test_never_merges_a_record_with_an_active_yes(db):
    _telegram_user_with_choices(db)
    wa(db, "hi")
    wa(db, "1")
    wa(db, "yes")  # WhatsApp user now has a YES of their own
    code = _code_from(tg(db, "5")[0])
    assert "still has a YES saved" in wa(db, f"LINK {code}")[0]


def test_link_allowed_after_withdrawing_here(db):
    person = _telegram_user_with_choices(db)
    wa(db, "hi")
    wa(db, "1")
    for answer in ("yes", "no", "no", "no"):
        wa(db, answer)
    wa(db, "3")
    wa(db, "yes")  # withdraw everything on WhatsApp
    out = wa(db, f"LINK {_code_from(tg(db, '5')[0])}")
    assert person.reference in out[0]
    assert consent.get_or_create_person(db, "whatsapp", "wa-1").id == person.id


def test_link_allowed_when_only_no_answers(db):
    person = _telegram_user_with_choices(db)
    wa(db, "hi")
    wa(db, "1")
    wa(db, "no")
    out = wa(db, f"LINK {_code_from(tg(db, '5')[0])}")
    assert person.reference in out[0]


def test_menu_escapes_the_questions(db):
    wa(db, "hi")
    wa(db, "1")
    wa(db, "yes")  # answer 1 of 4
    out = wa(db, "menu")
    assert "What would you like to do?" in out[0]
    person = consent.get_or_create_person(db, "whatsapp", "wa-1")
    assert len(consent.latest_decisions(db, person)) == 1  # the answer given is kept


def test_changing_yes_to_no_tells_the_person_who_was_notified(db):
    from ase import datausers
    from ase.models import DataUser, DataUserAccess
    person = _telegram_user_with_choices(db)  # all YES
    du = DataUser(name="Org", contact="o@example.org", api_key_hash="x")
    db.add(du); db.flush()
    db.add(DataUserAccess(data_user_id=du.id, data_use_code="community_research")); db.flush()
    assert datausers.check(db, du, person, "community_research")["allowed"]
    tg(db, "2")          # change my choices
    out = tg(db, "no")   # community research: YES -> NO
    assert "told 1 organisation" in out[0]


def test_change_shows_current_choice_and_keep_leaves_it(db):
    person = _telegram_user_with_choices(db)  # all YES
    out = tg(db, "2")
    assert "Your current choice: YES" in out[0]
    tg(db, "keep")                     # 1: keep YES
    out = tg(db, "no")                 # 2: change to NO
    latest = consent.latest_decisions(db, person)
    assert latest["community_research"].decision == "granted"
    assert latest["partner_sharing"].decision == "refused"


def test_back_returns_to_previous_question_and_yea_counts(db):
    wa(db, "hi")
    wa(db, "1")
    wa(db, "yea")        # 1: YES
    wa(db, "no")         # 2: NO
    out = wa(db, "back")  # back to 2
    assert "2 of 4" in out[0] and "Your current choice: NO" in out[0]
    wa(db, "yeah")       # 2: now YES
    person = consent.get_or_create_person(db, "whatsapp", "wa-1")
    latest = consent.latest_decisions(db, person)
    assert latest["community_research"].decision == "granted"
    assert latest["partner_sharing"].decision == "granted"
