"""Choose what the program should do, then hand off to that workflow.

Reading path: app.py -> responder.py -> drafting.py -> individual services/.
Command-line option details live in cli.py; object construction lives in setup.py.
"""

import logging
from collections.abc import Sequence

from .cli import build_argument_parser, configure_logging
from .config import Settings
from .mail.sample import make_manual_test_email
from .services.database import Database
from .setup import build_inbox, build_responder

LOGGER = logging.getLogger("email_responder")


# Example: main(["--once"])
def main(arguments: Sequence[str] | None = None) -> None:
    """Read the command, validate its settings, and run the requested workflow."""

    parser = build_argument_parser()
    args = parser.parse_args(arguments)
    configure_logging(args.log_level)
    if args.draft_only and not args.manual_test:
        parser.error("--draft-only must be used together with --manual-test")

    settings = Settings.from_environment()
    if args.reset_baseline:
        reset_baseline(settings)
    elif args.manual_test:
        run_manual_test(settings, draft_only=args.draft_only)
    else:
        run_inbox(settings, once=args.once)


# Example: reset_baseline(settings)
def reset_baseline(settings: Settings) -> None:
    """Move the old-email cutoff to now without requiring unrelated services."""

    Database(settings.database_url).reset_baseline(settings.account_email)
    LOGGER.info("Old-email cutoff reset for %s.", settings.account_email)


# Example: run_manual_test(settings, draft_only=True)
def run_manual_test(settings: Settings, draft_only: bool) -> None:
    """Preview a synthetic email, or send its answer to our own test alias."""

    settings.validate(require_gmail=not draft_only)
    responder = build_responder(settings)
    email = make_manual_test_email(settings)
    if draft_only:
        print(responder.preview_email(email))
    else:
        status = responder.process_email(email)
        LOGGER.info("Manual test finished with status %s.", status)


# Example: run_inbox(settings, once=True)
def run_inbox(settings: Settings, once: bool) -> None:
    """Check the inbox once, or keep polling until the user presses Ctrl+C."""

    settings.validate()
    inbox = build_inbox(settings)
    if once:
        inbox.run_once()
        return

    try:
        inbox.run_forever()
    except KeyboardInterrupt:
        LOGGER.info("Email responder stopped.")


if __name__ == "__main__":
    main()
