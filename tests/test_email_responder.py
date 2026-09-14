"""Unit tests for behavior inherited from the n8n email responder."""

import unittest
from email import policy
from email.parser import BytesParser

from email_responder.app import (
    RankedPage,
    Settings,
    blocked_sender_reason,
    build_reply_prompt,
    chunk_text,
    normalize_message,
    normalize_text,
    workflow_hash,
)


# Example: tests = EmailResponderTests()
class EmailResponderTests(unittest.TestCase):
    """Check text handling, sender guards, and prompt construction."""

    # Example: settings = self.make_settings()
    def make_settings(self) -> Settings:
        """Create non-secret settings for isolated unit tests."""

        return Settings(
            account_email="hello.wieland.collective@gmail.com",
            gmail_app_password="test-password",
            openai_api_key="test-key",
            wikijs_api_token="test-token",
            database_url="postgresql://unused",
        )

    # Example: self.test_normalize_text_removes_unsafe_html()
    def test_normalize_text_removes_unsafe_html(self) -> None:
        """HTML scripts and tags do not become prompt content."""

        source = "<style>bad</style><p>Hello&nbsp;there</p><script>bad</script>"
        self.assertEqual(normalize_text(source), "Hello there")

    # Example: self.test_chunk_text_overlaps_long_blocks()
    def test_chunk_text_overlaps_long_blocks(self) -> None:
        """Long blocks use the requested overlap between neighboring chunks."""

        chunks = chunk_text("abcdefghij", max_length=6, overlap=2)
        self.assertEqual(chunks, ["abcdef", "efghij", "ij"])

    # Example: self.test_workflow_hash_is_stable()
    def test_workflow_hash_is_stable(self) -> None:
        """Fallback message keys remain deterministic across runs."""

        self.assertEqual(workflow_hash("hello"), "bfb06f3a63cd7226")

    # Example: self.test_blocked_subdomain_is_detected()
    def test_blocked_subdomain_is_detected(self) -> None:
        """Subdomains of configured blocked domains are skipped."""

        reason = blocked_sender_reason(
            "news@mail.freelancer.com", "Freelancer News", self.make_settings()
        )
        self.assertEqual(reason["blocked_sender_domain"], "freelancer.com")

    # Example: self.test_normalize_message_prefers_plain_text()
    def test_normalize_message_prefers_plain_text(self) -> None:
        """Plain text is used instead of HTML when both versions are present."""

        raw_email = (
            b"From: Client <client@example.com>\r\n"
            b"To: hello.wieland.collective@gmail.com\r\n"
            b"Subject: Project question\r\n"
            b"Date: Mon, 14 Sep 2026 12:00:00 +0200\r\n"
            b"Message-ID: <example-1@example.com>\r\n"
            b"MIME-Version: 1.0\r\n"
            b"Content-Type: multipart/alternative; boundary=test\r\n\r\n"
            b"--test\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n"
            b"Plain question\r\n"
            b"--test\r\nContent-Type: text/html; charset=utf-8\r\n\r\n"
            b"<p>HTML question</p>\r\n"
            b"--test--\r\n"
        )
        message = BytesParser(policy=policy.default).parsebytes(raw_email)

        payload = normalize_message(message, 42, self.make_settings())

        self.assertIsNotNone(payload)
        assert payload is not None
        self.assertEqual(payload.email_text, "Plain question")
        self.assertEqual(payload.reply_subject, "Re: Project question")
        self.assertEqual(payload.message_key, "<example-1@example.com>")

    # Example: self.test_normalize_message_ignores_own_mailbox()
    def test_normalize_message_ignores_own_mailbox(self) -> None:
        """Outgoing mail cannot trigger an automatic reply loop."""

        raw_email = (
            b"From: hello.wieland.collective@gmail.com\r\n"
            b"To: client@example.com\r\n"
            b"Subject: Re: Hello\r\n\r\n"
            b"Reply"
        )
        message = BytesParser(policy=policy.default).parsebytes(raw_email)
        self.assertIsNone(normalize_message(message, 7, self.make_settings()))

    # Example: self.test_build_reply_prompt_contains_email_and_pages()
    def test_build_reply_prompt_contains_email_and_pages(self) -> None:
        """The reply prompt includes both the incoming email and KB facts."""

        raw_email = (
            b"From: client@example.com\r\n"
            b"To: hello.wieland.collective@gmail.com\r\n"
            b"Subject: Services\r\n\r\n"
            b"What services do you offer?"
        )
        message = BytesParser(policy=policy.default).parsebytes(raw_email)
        payload = normalize_message(message, 8, self.make_settings())
        assert payload is not None
        page = RankedPage(
            page_id="1",
            path="services",
            title="Services",
            wiki_url=None,
            best_distance=0.1,
            matched_email_chunk_index=0,
            matched_chunk_index=0,
            content="We offer strategy and design.",
            rank=1,
        )

        prompt = build_reply_prompt(payload, [page])

        self.assertIn("What services do you offer?", prompt)
        self.assertIn("We offer strategy and design.", prompt)
        self.assertIn("do not include a subject line", prompt)


if __name__ == "__main__":
    unittest.main()
