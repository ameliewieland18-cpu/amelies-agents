"""Small, non-secret examples shared by the tests."""

from email import policy
from email.parser import BytesParser

from email_responder.config import Settings
from email_responder.mail.normalize import normalize_message
from email_responder.models import IncomingEmail, RankedPage


# Example: settings = make_settings()
def make_settings(**overrides) -> Settings:
    """Provide dummy credentials, with optional overrides for a particular test."""

    values = dict(
        account_email="hello@example.com",
        gmail_app_password="test-password",
        openai_api_key="test-key",
        wikijs_api_token="test-token",
        database_url="postgresql://unused",
    )
    values.update(overrides)
    return Settings(**values)


# Example: message = make_message(sender="client@example.com")
def make_message(sender="client@example.com", body="What services do you offer?"):
    """Parse a realistic message with a fixed date and identifier."""

    raw = (
        f"From: {sender}\r\nTo: hello@example.com\r\nSubject: Services\r\n"
        "Date: Mon, 14 Sep 2026 12:00:00 +0200\r\n"
        f"Message-ID: <test@example.com>\r\n\r\n{body}"
    )
    return BytesParser(policy=policy.default).parsebytes(raw.encode())


# Example: email = make_email()
def make_email() -> IncomingEmail:
    """Return the same normalized email for workflow and adapter tests."""

    email = normalize_message(make_message(), 42, make_settings())
    assert email is not None
    return email


# Example: page = make_page()
def make_page() -> RankedPage:
    """Provide one ranked page with factual content for the writer."""

    return RankedPage(
        "1",
        "services",
        "Services",
        None,
        0.1,
        0,
        0,
        content="We offer strategy and design.",
        rank=1,
    )
