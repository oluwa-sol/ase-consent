from ase.channels import telegram, whatsapp
from ase.conversation import handle_message


def test_questions_offer_buttons_and_both_channels_render_them(db):
    first = handle_message(db, "whatsapp", "wa-b", "hi")[0]
    assert first.buttons == ["English", "Pidgin"]
    handle_message(db, "whatsapp", "wa-b", "English")  # tapping the button works
    out = handle_message(db, "whatsapp", "wa-b", "yes")
    assert out[-1].buttons == ["YES", "NO", "BACK"]

    wa = whatsapp.build_payload("123", out[-1])
    assert wa["type"] == "interactive" and wa["interactive"]["type"] == "button"
    assert [b["reply"]["title"] for b in wa["interactive"]["action"]["buttons"]] == ["YES", "NO", "BACK"]

    tg = telegram.build_payload(1, out[-1])
    assert [b["text"] for row in tg["reply_markup"]["keyboard"] for b in row] == ["YES", "NO", "BACK"]


def test_four_buttons_become_a_whatsapp_list_and_plain_text_has_none(db):
    for msg in ("hi", "1", "yes", "no", "yes", "yes"):
        handle_message(db, "telegram", "tg-b", msg)
    handle_message(db, "telegram", "tg-b", "2")       # change my choices
    out = handle_message(db, "telegram", "tg-b", "keep")
    assert out[-1].buttons == ["YES", "NO", "KEEP", "BACK"]
    assert whatsapp.build_payload("1", out[-1])["interactive"]["type"] == "list"
    assert telegram.build_payload(1, "plain")["reply_markup"] == {"remove_keyboard": True}
    assert whatsapp.build_payload("1", "plain")["type"] == "text"
