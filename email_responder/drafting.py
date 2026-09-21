"""Create a grounded reply: find relevant pages, build a prompt, ask the writer.

This workflow knows nothing about HTTP, SQL, or service response formats.
"""

from .models import IncomingEmail, RankedPage, ReplyDraft
from .prompt import build_reply_prompt
from .services.database import Database
from .services.openai import OpenAIClient
from .services.wiki import WikiJsClient
from .text import chunk_text, normalize_text


# Example: drafter = ReplyDrafter(database, wiki, openai)
class ReplyDrafter:
    """Combine knowledge retrieval and reply writing without sending anything."""

    # Example: drafter = ReplyDrafter(database, wiki, openai)
    def __init__(
        self, database: Database, wiki: WikiJsClient, openai: OpenAIClient
    ) -> None:
        """Receive the three building blocks instead of constructing them here."""

        self.database = database
        self.wiki = wiki
        self.openai = openai

    # Example: draft = drafter.create_draft(email, top_k=5)
    def create_draft(self, email: IncomingEmail, top_k: int) -> ReplyDraft:
        """Use current knowledge-base content to answer the incoming email."""

        pages = self.find_relevant_pages(email.email_text, top_k)
        prompt = build_reply_prompt(email, pages)
        body = self.openai.draft_reply(prompt)
        return ReplyDraft(body, pages)

    # Example: pages = drafter.find_relevant_pages("What services do you offer?", 5)
    def find_relevant_pages(self, email_text: str, top_k: int) -> list[RankedPage]:
        """Match pieces of the email to pages, then fetch each complete page."""

        chunks = chunk_text(normalize_text(email_text))
        if not chunks:
            raise ValueError("Email text produced zero chunks after normalization.")

        # An embedding is a list of numbers representing a piece of text.
        embeddings = self.openai.create_embeddings(chunks)
        ranked_pages = self.database.rank_pages(embeddings, top_k)
        return [self.wiki.fetch_page(page) for page in ranked_pages]
