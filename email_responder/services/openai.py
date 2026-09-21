"""OpenAIClient: keep request formats and response unpacking here."""

from collections.abc import Sequence

from openai import OpenAI

from ..config import Settings


# Example: ai = OpenAIClient(settings)
class OpenAIClient:
    """Create embeddings and draft the final email body with OpenAI."""

    # Example: client = OpenAIClient(settings)
    def __init__(self, settings: Settings) -> None:
        """Remember model settings and prepare the SDK client."""

        self.client = OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
        self.response_model = settings.response_model
        self.store_responses = settings.store_openai_responses

    # Example: vectors = ai.create_embeddings(["first chunk", "second chunk"])
    def create_embeddings(self, chunks: Sequence[str]) -> list[list[float]]:
        """Embed all non-empty email chunks in one API request."""

        if not chunks:
            raise ValueError("At least one email chunk is required for embeddings.")

        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=list(chunks),
        )
        ordered_items = sorted(response.data, key=lambda item: item.index)
        return [list(item.embedding) for item in ordered_items]

    # Example: body = ai.draft_reply(prompt)
    def draft_reply(self, prompt: str) -> str:
        """Generate a reply body with the configured Responses API model."""

        response = self.client.responses.create(
            model=self.response_model,
            input=prompt,
            store=self.store_responses,
        )
        reply_body = str(response.output_text or "").strip()
        if not reply_body:
            raise RuntimeError("OpenAI returned an empty email reply.")
        return reply_body
