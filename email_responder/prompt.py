"""The writing instructions and page formatting used for a reply.

This module builds text only; it never calls OpenAI or sends an email.
"""

from collections.abc import Sequence

from .models import IncomingEmail, RankedPage


# Example: prompt = build_reply_prompt(payload, pages)
def build_reply_prompt(payload: IncomingEmail, pages: Sequence[RankedPage]) -> str:
    """Build the same grounded reply request used by the n8n workflow."""

    context_sections: list[str] = []
    for page in sorted(pages, key=lambda item: item.rank):
        lines = [
            f"## {page.rank}. {page.title}",
            f"Path: {page.path}",
        ]
        if page.wiki_url:
            lines.append(f"URL: {page.wiki_url}")
        lines.extend(
            [
                f"Best embedding distance: {page.best_distance}",
                f"Matched email chunk: {page.matched_email_chunk_index}",
                f"Matched KB chunk: {page.matched_chunk_index}",
                "",
                page.content,
            ]
        )
        context_sections.append("\n".join(lines))

    knowledge_base_context = "\n\n---\n\n".join(context_sections)
    return "\n".join(
        [
            "You are replying on behalf of Wieland Collective from "
            f"{payload.account_email}.",
            "",
            "Write a helpful email reply to the sender. Use the Wiki.js "
            "knowledge-base pages below as the factual context for the reply. "
            "Do not invent details that are not supported by the context or the "
            "incoming email. If the context does not answer a specific question, "
            "say that we will follow up. Keep the tone warm, concise, and "
            "professional. Match the incoming email language when practical. "
            "Return only the email body; do not include a subject line, markdown "
            "code fence, or analysis.",
            "",
            f"# Retrieved Wiki.js Context ({len(pages)} distinct pages)",
            knowledge_base_context,
            "",
            "# Incoming Email",
            payload.full_email,
            "",
            "# Reply Body",
        ]
    )
