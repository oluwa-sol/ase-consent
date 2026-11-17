"""Chat text in each language. "pcm" is Nigerian Pidgin (draft, needs community review)."""

LANGUAGES = {"1": "en", "2": "pcm"}

T = {
    "welcome": {
        "en": "Hello, welcome to Àṣẹ.\nReply 1 for English\nReply 2 for Pidgin",
    },
    "intro": {
        "en": ("Àṣẹ lets you decide how your health information is used.\n\n"
               "We will ask you about {n} possible uses, one at a time. You can say YES or NO to each one, "
               "and you can change your mind any time.\n\n"
               "Àṣẹ never stores your health information, only your choices."),
        "pcm": ("Àṣẹ dey help you decide how dem go use your health information.\n\n"
                "We go ask you about {n} ways wey dem fit use am, one by one. You fit talk YES or NO for each one, "
                "and you fit change your mind any time.\n\n"
                "Àṣẹ no dey keep your health information, na only your choice we dey keep."),
    },
    "ask": {
        "en": "{i} of {n}: {title}\n\n{explain}\n\nDo you agree? Reply YES or NO.",
        "pcm": "{i} of {n}: {title}\n\n{explain}\n\nYou gree? Reply YES or NO.",
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
        "pcm": "Show this code {ref} to your health worker, so dem go respect your choice.",
    },
    "menu": {
        "en": "What would you like to do?\n1 See my choices\n2 Change my choices\n3 Withdraw everything\n4 Change language",
        "pcm": "Wetin you wan do?\n1 See my choice dem\n2 Change my choice dem\n3 Withdraw everything\n4 Change language",
    },
    "confirm_withdraw": {
        "en": "This will withdraw every YES you have given. Nobody will be allowed to use your information from now on. Are you sure? Reply YES or NO.",
        "pcm": "This one go cancel every YES wey you don give. Nobody go fit use your information again from now. You sure? Reply YES or NO.",
    },
    "withdrawn": {
        "en": "Done. You have withdrawn {n} permission(s). Anyone using your information has been told to stop.",
        "pcm": "E don do. You don withdraw {n} permission. We don tell everybody wey dey use your information make dem stop.",
    },
    "withdraw_none": {
        "en": "You have not given any YES, so there is nothing to withdraw.",
        "pcm": "You never give any YES, so nothing dey to withdraw.",
    },
    "cancelled": {
        "en": "Okay, nothing has changed.",
        "pcm": "Okay, nothing change.",
    },
}

YES = {"yes", "y", "yeah", "yep", "ok", "okay", "i agree", "agree", "sure", "na so", "i gree", "gree", "ehen", "bẹẹni", "beeni"}
NO = {"no", "n", "nope", "no thanks", "i no gree", "no be so", "rara", "bẹẹkọ", "beeko"}


def t(key: str, lang: str, **kw) -> str:
    entry = T[key]
    text = entry.get(lang) or entry["en"]
    return text.format(**kw) if kw and isinstance(text, str) else text


def yes_no(text: str) -> bool | None:
    s = text.strip().lower().strip(".!")
    if s in YES:
        return True
    if s in NO:
        return False
    return None
