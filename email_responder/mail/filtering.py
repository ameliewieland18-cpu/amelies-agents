"""Sender blocklist rules, independent of Gmail and the database."""

from ..config import Settings
from ..text import normalize_whitespace


# Example: reason = blocked_sender_reason("news@example.com", "News", settings)
def blocked_sender_reason(
    sender_email: str, sender_raw: str, settings: Settings
) -> dict[str, str]:
    """Explain why a sender matches the configured domain or name blocklist."""

    sender_domain = sender_email.rsplit("@", 1)[-1]
    for blocked_domain in settings.blocked_domains:
        if sender_domain == blocked_domain or sender_domain.endswith(
            f".{blocked_domain}"
        ):
            return {
                "skip_reason": "blocked_sender",
                "skip_detail": f"sender domain matches {blocked_domain}",
                "blocked_sender_domain": blocked_domain,
            }

    lowered_sender = normalize_whitespace(sender_raw).lower()
    for blocked_keyword in settings.blocked_keywords:
        if blocked_keyword in lowered_sender:
            return {
                "skip_reason": "blocked_sender",
                "skip_detail": f"sender name matches {blocked_keyword}",
                "blocked_sender_keyword": blocked_keyword,
            }

    return {}
