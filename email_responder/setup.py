"""Assemble the building blocks in one place.

The workflows receive their dependencies as arguments. Tests can supply simple
stand-ins, while the command-line application uses these real service clients.
"""

from .config import Settings
from .drafting import ReplyDrafter
from .inbox import InboxRunner
from .responder import EmailResponder
from .services.database import Database
from .services.gmail import GmailClient
from .services.openai import OpenAIClient
from .services.wiki import WikiJsClient


# Example: responder = build_responder(settings)
def build_responder(settings: Settings) -> EmailResponder:
    """Connect the database, knowledge sources, reply writer, and mailbox."""

    database = Database(settings.database_url)
    wiki = WikiJsClient(settings)
    openai = OpenAIClient(settings)
    gmail = GmailClient(settings)
    drafter = ReplyDrafter(database, wiki, openai)
    return EmailResponder(database, drafter, gmail)


# Example: inbox = build_inbox(settings)
def build_inbox(settings: Settings) -> InboxRunner:
    """Use the same Gmail client for reading messages and sending their replies."""

    responder = build_responder(settings)
    return InboxRunner(settings, responder.gmail, responder)
