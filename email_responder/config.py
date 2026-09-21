"""Available settings and their defaults. Environment parsing is in environment.py."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BLOCKED_DOMAINS = (
    "freelancer.nl",
    "freelancer.com",
    "makro.nl",
    "makromarket.nl",
    "makro.market",
    "makro-market.nl",
)

DEFAULT_BLOCKED_KEYWORDS = (
    "freelancer.nl",
    "makro market",
    "makromarket",
    "makro-market",
)


# Example: settings = Settings.from_environment()
@dataclass(frozen=True)
class Settings:
    """Configuration loaded from environment variables or a local ``.env`` file."""

    account_email: str
    gmail_app_password: str
    openai_api_key: str
    wikijs_api_token: str
    database_url: str
    imap_host: str = "imap.gmail.com"
    imap_port: int = 993
    imap_mailbox: str = "INBOX"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    wikijs_graphql_url: str = "http://127.0.0.1:3000/graphql"
    response_model: str = "gpt-5.4"
    embedding_model: str = "text-embedding-3-small"
    poll_seconds: int = 60
    store_openai_responses: bool = False
    blocked_domains: tuple[str, ...] = DEFAULT_BLOCKED_DOMAINS
    blocked_keywords: tuple[str, ...] = DEFAULT_BLOCKED_KEYWORDS

    # Example: settings = Settings.from_environment()
    @classmethod
    def from_environment(cls) -> Settings:
        """Read the optional .env file and convert environment strings to settings."""

        # Import here so the settings description does not depend on its loader.
        from .environment import load_settings

        return load_settings()

    # Example: settings.validate(require_gmail=False)
    def validate(
        self,
        require_gmail: bool = True,
        require_openai: bool = True,
        require_wikijs: bool = True,
    ) -> None:
        """Raise a helpful error when a required secret is missing."""

        missing: list[str] = []
        if require_gmail and not self.gmail_app_password:
            missing.append("GMAIL_APP_PASSWORD")
        if require_openai and not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if require_wikijs and not self.wikijs_api_token:
            missing.append("WIKIJS_API_TOKEN")

        if missing:
            names = ", ".join(missing)
            raise ValueError(f"Missing required environment variable(s): {names}")
