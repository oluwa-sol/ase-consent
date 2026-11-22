"""Chat text in each language. "pcm" is Nigerian Pidgin (draft, needs community review)."""

LANGUAGES = {"1": "en", "2": "pcm", "english": "en", "pidgin": "pcm"}


class Reply(str):
    """A chat message that may offer tap buttons. Channels without buttons just send the text."""

    def __new__(cls, text: str, buttons: list[str] | None = None):
        obj = super().__new__(cls, text)
        obj.buttons = list(buttons or [])
        return obj

T = {
    "welcome": {
        "en": "Hello, welcome to Àṣẹ.\nReply 1 for English\nReply 2 for Pidgin",
    },
    "intro": {
        "en": ("Àṣẹ lets you decide how your health information is used.\n\n"
               "We will ask you about {n} possible uses, one at a time. You can say YES or NO to each one, "
               "and you can change your mind any time.\n\n"
               "Àṣẹ never stores your health information, only your choices."),
        "pcm": ("Àṣẹ dey make you be the person wey go talk how dem go use your health information.\n\n"
                "We go ask you about {n} ways wey dem fit use am, one by one. You fit talk YES or NO for each one, "
                "and you fit change your mind any time.\n\n"
                "Àṣẹ no dey keep your health information, na only your choice we dey keep."),
    },
    "ask": {
        "en": "{i} of {n}: {title}\n\n{explain}\n\nDo you agree? Reply YES or NO.",
        "pcm": "{i} of {n}: {title}\n\n{explain}\n\nYou gree? Reply YES or NO.",
    },
    "ask_change": {
        "en": "{i} of {n}: {title}\n\n{explain}\n\nYour current choice: {current}.\nReply YES or NO, or KEEP to leave it as it is.",
        "pcm": "{i} of {n}: {title}\n\n{explain}\n\nWetin you choose before: {current}.\nReply YES or NO, or KEEP make e stay like that.",
    },
    "back_hint": {
        "en": "(Send BACK to change the previous answer.)",
        "pcm": "(Send BACK make you change the answer wey you give before.)",
    },
    "not_understood_yes_no": {
        "en": "Sorry, please reply YES or NO.",
        "pcm": "Abeg, reply YES or NO.",
    },
    "done": {
        "en": "Thank you. Your choices are saved.",
        "pcm": "Thank you. We don save your choice.",
    },
    "summary_header": {
        "en": "Your choices (code {ref}):",
        "pcm": "Your choice dem (code {ref}):",
    },
    "status": {
        "en": {"granted": "YES", "refused": "NO", "withdrawn": "NO (withdrawn)", None: "not asked yet"},
        "pcm": {"granted": "YES", "refused": "NO", "withdrawn": "NO (you don withdraw)", None: "we never ask"},
    },
    "code_hint": {
        "en": "Show the code {ref} to your health worker so your choices are respected.",
        "pcm": "Show this code {ref} give your health worker, so dem go respect your choice.",
    },
    "menu": {
        "en": "What would you like to do?\n1 See my choices\n2 Change my choices\n3 Withdraw everything\n4 Change language\n5 Link another app (WhatsApp or Telegram)",
        "pcm": "Wetin you wan do?\n1 See my choice dem\n2 Change my choice dem\n3 Withdraw everything\n4 Change language\n5 Join another app (WhatsApp or Telegram)",
    },
    "menu_hint": {
        "en": "Send MENU any time to see your options.",
        "pcm": "Send MENU any time wey you wan see wetin you fit do.",
    },
    "not_understood": {
        "en": "Sorry, I didn't get that. Send MENU any time to see your options.",
        "pcm": "I no understand that one. Send MENU any time wey you wan see wetin you fit do.",
    },
    "bye": {
        "en": "Bye! Your choices are saved. Send MENU any time you need to check or change them.",
        "pcm": "Bye bye! Your choice dem dey safe. Send MENU any time wey you wan check or change am.",
    },
    "ack": {
        "en": "Okay 👍",
        "pcm": "Okay 👍",
    },
    "link_code": {
        "en": "Your link code is {code}. It works for {mins} minutes.\n\nOn your other app (WhatsApp or Telegram), message Àṣẹ: LINK {code}\n\nBoth apps will then share the same choices. Never share this code with anyone.",
        "pcm": "Your link code na {code}. E go work for {mins} minutes.\n\nFor your other app (WhatsApp or Telegram), send this to Àṣẹ: LINK {code}\n\nThe two apps go kon carry the same choice. No show this code to anybody.",
    },
    "linked": {
        "en": "Linked. This app now shares your choices (code {ref}).",
        "pcm": "E don join. This app don carry your choice dem now (code {ref}).",
    },
    "link_invalid": {
        "en": "That link code is wrong or has expired. Get a new one from your other app: open the menu and choose 5.",
        "pcm": "That link code no correct, or e don expire. Collect new one for your other app: open the menu, choose 5.",
    },
    "link_same": {
        "en": "This app is already linked to your choices.",
        "pcm": "This app don already join your choice dem.",
    },
    "link_has_choices": {
        "en": "This app still has a YES saved, so it can't be linked. To link it, first choose 3 to withdraw here, then try again.",
        "pcm": "This app still get YES wey you give for here, so e no fit join. To join am, first choose 3 make you withdraw for here, then try again.",
    },
    "confirm_withdraw": {
        "en": "This will withdraw every YES you have given. Nobody will be allowed to use your information from now on. Are you sure? Reply YES or NO.",
        "pcm": "This one go cancel every YES wey you don give. Nobody go fit use your information again from now. You sure? Reply YES or NO.",
    },
    "withdrawn": {
        "en": "Done. You have withdrawn {n} permission(s). From now on, nobody is allowed to use your information for these.",
        "pcm": "E don do. You don withdraw {n} permission. From now go, nobody get right to use your information for these ones again.",
    },
    "notified": {
        "en": "We have told {k} organisation(s) that used your information to stop. They must confirm they have stopped.",
        "pcm": "We don tell {k} organisation wey dey use your information make dem stop. Dem must confirm say dem don stop.",
    },
    "withdraw_none": {
        "en": "You have not given any YES, so there is nothing to withdraw.",
        "pcm": "You never talk YES, so nothing dey to withdraw.",
    },
    "cancelled": {
        "en": "Okay, nothing has changed.",
        "pcm": "Okay, nothing change.",
    },
}

YES = {"yes", "y", "yea", "yeah", "yeh", "ya", "yah", "yes o", "yess", "yup", "yep", "of course", "i do", "ok", "okay", "i agree", "agree", "sure", "na so", "i gree", "gree", "ehen", "bẹẹni", "beeni"}
NO = {"no", "n", "nah", "naa", "no o", "nope", "not really", "i don't", "i dont", "no thanks", "i no gree", "no be so", "rara", "bẹẹkọ", "beeko"}


def t(key: str, lang: str, **kw) -> str:
    entry = T[key]
    text = entry.get(lang) or entry["en"]
    return text.format(**kw) if kw and isinstance(text, str) else text


BACK = {"back", "go back", "previous", "undo", "prev"}


def is_back(text: str) -> bool:
    return text.strip().lower().strip(".!") in BACK


KEEP = {"keep", "skip", "same", "leave it", "no change"}


def is_keep(text: str) -> bool:
    return text.strip().lower().strip(".!") in KEEP


def yes_no(text: str) -> bool | None:
    s = text.strip().lower().strip(".!")
    if s in YES:
        return True
    if s in NO:
        return False
    return None
