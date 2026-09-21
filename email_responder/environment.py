"""Translate environment-variable strings into the Settings object.

Only this file needs to know environment variable names or conversion rules.
"""

import os

from dotenv import load_dotenv

from .config import DEFAULT_BLOCKED_DOMAINS, DEFAULT_BLOCKED_KEYWORDS, Settings


# Example: settings = load_settings()
def load_settings() -> Settings:
    """Read .env without overriding existing environment variables, then convert."""

    load_dotenv()

    postgres_user = os.getenv("POSTGRES_USER", "appuser")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "change-me-for-local-dev")
    postgres_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    postgres_database = os.getenv("POSTGRES_DB", "freelance")
    default_database_url = (
        f"postgresql://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_database}"
    )

    return Settings(
        account_email=os.getenv(
            "EMAIL_RESPONDER_ACCOUNT", "hello.wieland.collective@gmail.com"
        ).lower(),
        gmail_app_password=os.getenv("GMAIL_APP_PASSWORD", ""),
        openai_api_key=os.getenv("OPENAI_API_KEY", ""),
        wikijs_api_token=os.getenv("WIKIJS_API_TOKEN", ""),
        database_url=os.getenv("DATABASE_URL", default_database_url),
        imap_host=os.getenv("EMAIL_RESPONDER_IMAP_HOST", "imap.gmail.com"),
        imap_port=int(os.getenv("EMAIL_RESPONDER_IMAP_PORT", "993")),
        imap_mailbox=os.getenv("EMAIL_RESPONDER_IMAP_MAILBOX", "INBOX"),
        smtp_host=os.getenv("EMAIL_RESPONDER_SMTP_HOST", "smtp.gmail.com"),
        smtp_port=int(os.getenv("EMAIL_RESPONDER_SMTP_PORT", "465")),
        wikijs_graphql_url=os.getenv(
            "WIKIJS_GRAPHQL_URL", "http://127.0.0.1:3000/graphql"
        ),
        response_model=os.getenv("OPENAI_RESPONSE_MODEL", "gpt-5.4"),
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        poll_seconds=max(5, int(os.getenv("EMAIL_RESPONDER_POLL_SECONDS", "60"))),
        store_openai_responses=parse_boolean(
            os.getenv("OPENAI_STORE_RESPONSES", "false")
        ),
        blocked_domains=split_csv(
            os.getenv(
                "EMAIL_RESPONDER_BLOCKED_DOMAINS",
                ",".join(DEFAULT_BLOCKED_DOMAINS),
            )
        ),
        blocked_keywords=split_csv(
            os.getenv(
                "EMAIL_RESPONDER_BLOCKED_KEYWORDS",
                ",".join(DEFAULT_BLOCKED_KEYWORDS),
            )
        ),
    )


# Example: values = split_csv("one, two")
def split_csv(value: str) -> tuple[str, ...]:
    """Turn a comma-separated environment value into clean lowercase items."""

    return tuple(item.strip().lower() for item in value.split(",") if item.strip())


# Example: enabled = parse_boolean("yes")
def parse_boolean(value: str) -> bool:
    """Return ``True`` for common true-like environment values."""

    return value.strip().lower() in {"1", "true", "yes", "on"}
