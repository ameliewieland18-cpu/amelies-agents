"""Verify retrieval, full-page fetching, and prompt construction as one workflow."""

import unittest
from unittest.mock import Mock

from email_responder.drafting import ReplyDrafter
from tests.support import make_email, make_page


# Example: python -m unittest tests.test_drafting
class DraftingTests(unittest.TestCase):
    """Check the service boundaries with ordinary email and page objects."""

    # Example: self.test_draft_uses_ranked_pages_with_current_content()
    def test_draft_uses_ranked_pages_with_current_content(self):
        """The writer receives fetched page content and the complete incoming email."""

        database, wiki, ai = Mock(), Mock(), Mock()
        page = make_page()
        ai.create_embeddings.return_value = [[0.1, 0.2]]
        database.rank_pages.return_value = [page]
        wiki.fetch_page.return_value = page
        ai.draft_reply.return_value = "We offer strategy and design."
        email = make_email()

        draft = ReplyDrafter(database, wiki, ai).create_draft(email, top_k=3)

        ai.create_embeddings.assert_called_once_with([email.email_text])
        database.rank_pages.assert_called_once_with([[0.1, 0.2]], 3)
        wiki.fetch_page.assert_called_once_with(page)
        prompt = ai.draft_reply.call_args.args[0]
        self.assertIn(email.full_email, prompt)
        self.assertIn(page.content, prompt)
        self.assertEqual(draft.pages, [page])
        self.assertEqual(draft.body, "We offer strategy and design.")

    # Example: self.test_empty_text_stops_before_embedding()
    def test_empty_text_stops_before_embedding(self):
        """Empty text fails locally before any paid or external operation."""

        database, wiki, ai = Mock(), Mock(), Mock()
        with self.assertRaisesRegex(ValueError, "zero chunks"):
            ReplyDrafter(database, wiki, ai).find_relevant_pages("<p> </p>", 5)
        ai.create_embeddings.assert_not_called()
        database.rank_pages.assert_not_called()
