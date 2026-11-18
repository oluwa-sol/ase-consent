from ase import consent
from ase.conversation import handle_message


def chat(db, text, who="555"):
    return handle_message(db, "telegram", who, text)


def test_full_first_time_flow_in_pidgin(db):
    assert "Reply 1 for English" in chat(db, "hi")[0]
    replies = chat(db, "2")
    assert "Àṣẹ dey make you be the person" in replies[0]
    assert "1 of 4" in replies[1]
    assert "You gree?" in replies[1]
    chat(db, "yes")
    chat(db, "no")
    chat(db, "i gree")
    final = chat(db, "no")
    assert len(final) == 1, "save confirmation, summary and hint must be one message"
    assert "We don save your choice" in final[0]
    assert "code ASE-" in final[0]
    assert "Send MENU" in final[0]
    assert "Wetin you wan do?" not in final[0]
    p = consent.get_or_create_person(db, "telegram", "555")
    assert consent.is_allowed(db, p, "community_research")
    assert not consent.is_allowed(db, p, "partner_sharing")
    assert consent.is_allowed(db, p, "ai_training")
    assert not consent.is_allowed(db, p, "follow_up_contact")


def test_unclear_answer_asks_again_without_recording(db):
    chat(db, "hi")
    chat(db, "1")
    assert "please reply YES or NO" in chat(db, "maybe later")[0]
    p = consent.get_or_create_person(db, "telegram", "555")
    assert consent.latest_decisions(db, p) == {}


def _complete_all_yes(db):
    chat(db, "hi")
    chat(db, "1")
    for _ in range(4):
        out = chat(db, "yes")
    return out


def test_withdraw_needs_confirmation_and_then_withdraws_everything(db):
    _complete_all_yes(db)
    assert "Are you sure?" in chat(db, "3")[0]
    out = chat(db, "yes")
    assert "withdrawn 4 permission" in out[0]
    p = consent.get_or_create_person(db, "telegram", "555")
    assert not any(consent.is_allowed(db, p, u.code) for u in consent.active_uses(db))


def test_withdraw_cancelled_changes_nothing(db):
    _complete_all_yes(db)
    chat(db, "withdraw")
    assert "nothing has changed" in chat(db, "no")[0]
    p = consent.get_or_create_person(db, "telegram", "555")
    assert all(consent.is_allowed(db, p, u.code) for u in consent.active_uses(db))


def test_change_choices_again(db):
    _complete_all_yes(db)
    assert "1 of 4" in chat(db, "2")[0]
    chat(db, "no")
    p = consent.get_or_create_person(db, "telegram", "555")
    assert not consent.is_allowed(db, p, "community_research")


def test_returning_user_choosing_language_goes_to_menu(db):
    _complete_all_yes(db)
    chat(db, "4")
    out = chat(db, "1")
    assert "What would you like to do?" in out[0]


def test_menu_only_when_asked(db):
    _complete_all_yes(db)
    out = chat(db, "1")
    assert len(out) == 1 and "What would you like to do?" not in out[0]
    assert "What would you like to do?" in chat(db, "MENU")[0]


def test_ok_and_random_text_do_not_dump_the_menu(db):
    _complete_all_yes(db)
    assert chat(db, "ok") == ["Okay 👍"]
    out = chat(db, "blah blah")
    assert "didn't get that" in out[0] and "What would you like to do?" not in out[0]
    assert "What would you like to do?" in chat(db, "hi")[0]
