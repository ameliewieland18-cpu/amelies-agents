"""Check the shapes sent to and received from Wiki.js and OpenAI."""

import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from email_responder.services.openai import OpenAIClient
from email_responder.services.wiki import WikiJsClient
from tests.support import make_page, make_settings


# Example: python -m unittest tests.test_web_services.OpenAITests
class OpenAITests(unittest.TestCase):
    """SDK response details must be translated to plain vectors and strings."""

    # Example: self.test_embedding_order_and_response_options()
    def test_embedding_order_and_response_options(self):
        """Embeddings follow input order, and customer prompts are not stored."""

        sdk = Mock()
        sdk.embeddings.create.return_value.data = [
            SimpleNamespace(index=1, embedding=[0.2]),
            SimpleNamespace(index=0, embedding=[0.1]),
        ]
        sdk.responses.create.return_value.output_text = "  Thank you! \n"
        with patch("email_responder.services.openai.OpenAI", return_value=sdk):
            client = OpenAIClient(make_settings())
        self.assertEqual(client.create_embeddings(["first", "second"]), [[0.1], [0.2]])
        sdk.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small", input=["first", "second"]
        )
        self.assertEqual(client.draft_reply("Prompt"), "Thank you!")
        sdk.responses.create.assert_called_once_with(
            model="gpt-5.4", input="Prompt", store=False
        )
        sdk.responses.create.return_value.output_text = "  "
        with self.assertRaisesRegex(RuntimeError, "empty email reply"):
            client.draft_reply("Prompt")

    # Example: self.test_empty_embedding_input_never_calls_api()
    def test_empty_embedding_input_never_calls_api(self):
        """The adapter rejects empty input before asking the external service."""

        with patch("email_responder.services.openai.OpenAI") as sdk:
            client = OpenAIClient(make_settings())
            with self.assertRaises(ValueError):
                client.create_embeddings([])
        sdk.return_value.embeddings.create.assert_not_called()


# Example: python -m unittest tests.test_web_services.WikiTests
class WikiTests(unittest.TestCase):
    """Nested GraphQL payloads and transport failures stay inside the adapter."""

    # Example: self.test_fetch_unpacks_graphql_and_preserves_ranking()
    def test_fetch_unpacks_graphql_and_preserves_ranking(self):
        """The workflow receives clean content while similarity metadata survives."""

        response = {
            "data": {
                "pages": {
                    "single": {
                        "title": "New title",
                        "path": "new-path",
                        "render": "<p>Our services</p>",
                    }
                }
            }
        }
        for token in ("test-token", "Bearer test-token"):
            with self.subTest(token=token):
                with patch(
                    "email_responder.services.wiki.urlopen",
                    return_value=io.BytesIO(json.dumps(response).encode()),
                ) as request:
                    page = WikiJsClient(
                        make_settings(wikijs_api_token=token)
                    ).fetch_page(make_page())
                sent = request.call_args.args[0]
                self.assertEqual(sent.get_header("Authorization"), "Bearer test-token")
                self.assertEqual(json.loads(sent.data)["variables"], {"id": 1})
                self.assertEqual(page.content, "Our services")
                self.assertEqual(
                    (page.title, page.path, page.best_distance),
                    ("New title", "new-path", 0.1),
                )

    # Example: self.test_graphql_and_missing_page_errors()
    def test_graphql_and_missing_page_errors(self):
        """Error payloads never become empty successful pages."""

        cases = [
            ({"errors": [{"message": "Forbidden"}]}, "Forbidden"),
            ({"data": {"pages": {"single": None}}}, "no page content"),
        ]
        for response, error in cases:
            with self.subTest(response=response):
                with patch(
                    "email_responder.services.wiki.urlopen",
                    return_value=io.BytesIO(json.dumps(response).encode()),
                ):
                    with self.assertRaisesRegex(RuntimeError, error):
                        WikiJsClient(make_settings()).fetch_page(make_page())

    # Example: self.test_transport_errors_have_service_context()
    def test_transport_errors_have_service_context(self):
        """Connection and HTTP failures produce understandable Wiki.js errors."""

        errors = [
            URLError("Offline"),
            HTTPError("http://unused", 403, "Forbidden", {}, io.BytesIO(b"Denied")),
        ]
        for error in errors:
            if isinstance(error, HTTPError):
                self.addCleanup(error.close)
            with self.subTest(error=error):
                with patch("email_responder.services.wiki.urlopen", side_effect=error):
                    with self.assertRaisesRegex(RuntimeError, "Wiki.js"):
                        WikiJsClient(make_settings()).fetch_page(make_page())
