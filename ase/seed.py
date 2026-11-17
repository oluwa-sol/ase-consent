"""Default data uses. Each organisation can edit these for its own programme.

Pidgin (pcm) text is a first draft and must be reviewed by native speakers and
community members before real use.
"""

from sqlalchemy.orm import Session

from .models import DataUse

DEFAULT_USES = [
    {
        "code": "community_research",
        "position": 1,
        "text": {
            "en": {
                "title": "Community health research",
                "explain": "The health team can use your information, without your name, to understand what people in your community need and to improve services.",
            },
            "pcm": {
                "title": "Research for community health",
                "explain": "Dem health people fit use your information, your name no go show, to sabi wetin people for your community need, so dem go fit make the service better.",
            },
        },
    },
    {
        "code": "partner_sharing",
        "position": 2,
        "text": {
            "en": {
                "title": "Sharing with partner organisations",
                "explain": "Your information, without your name, may be shared with trusted partners like universities or NGOs. The community panel must approve every request.",
            },
            "pcm": {
                "title": "Sharing with partner organisations",
                "explain": "Dem fit share your information, your name no go show, with partners wey dem trust, like university or NGO. But the community panel go approve am first.",
            },
        },
    },
    {
        "code": "ai_training",
        "position": 3,
        "text": {
            "en": {
                "title": "Building AI tools",
                "explain": "Your information, without your name, may be used to build AI tools, for example tools that help health workers notice who needs support. Only with community panel approval.",
            },
            "pcm": {
                "title": "To build AI tools",
                "explain": "Dem fit use your information, your name no go show, take build AI tools, like tools wey go help health workers sabi people wey need support. Na only if the community panel approve am.",
            },
        },
    },
    {
        "code": "follow_up_contact",
        "position": 4,
        "text": {
            "en": {
                "title": "Being contacted for follow-up",
                "explain": "A health worker may message you to check in on you or invite you to take part in a study.",
            },
            "pcm": {
                "title": "Make dem contact you later",
                "explain": "Health worker fit message you to check how you dey, or call you say make you come learn something.",
            },
        },
    },
]


def seed_uses(db: Session) -> None:
    for u in DEFAULT_USES:
        if db.get(DataUse, u["code"]) is None:
            db.add(DataUse(**u))
    db.flush()
