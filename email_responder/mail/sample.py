"""A synthetic email that sends manual test replies back to our own mailbox."""

from datetime import UTC, datetime

from ..config import Settings
from ..models import IncomingEmail


# Example: payload = make_manual_test_email(settings)
def make_manual_test_email(settings: Settings) -> IncomingEmail:
    """Create the safe Gmail plus-address test used by the old manual trigger."""

    now = datetime.now(UTC)
    run_id = now.strftime("%Y%m%d%H%M%S%f")
    sender = settings.account_email.replace("@", "+manual-test@", 1)
    subject = f"Manual responder Python test {now.isoformat()}"
    body = "\n".join(
        [
            "Hello Wieland Collective,",
            "",
            "This is a manual test email for the automatic responder program.",
            "Please answer as if I am asking what services you offer "
            "and how to start a project.",
            "",
            "Thanks!",
            "Manual Test",
        ]
    )
    received_at = now.isoformat()
    sender_raw = f"Manual Test <{sender}>"

    return IncomingEmail(
        mailbox=settings.account_email,
        account_email=settings.account_email,
        sender_email=sender,
        sender_raw=sender_raw,
        to_raw=settings.account_email,
        cc_raw="",
        received_at=received_at,
        message_id=f"<manual-test-{run_id}@python.local>",
        message_key=f"<manual-test-{run_id}@python.local>",
        original_subject=subject,
        reply_subject=f"Re: {subject}",
        email_text=body,
        full_email="\n".join(
            [
                f"From: {sender_raw}",
                f"To: {settings.account_email}",
                f"Date: {received_at}",
                f"Subject: {subject}",
                "",
                body,
            ]
        ),
        imap_uid=None,
    )
