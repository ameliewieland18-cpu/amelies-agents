"""Command-line flags and console logging. Start with app.py for what they do."""

import argparse
import logging
import os


# Example: parser = build_argument_parser()
def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line options for normal runs and safe testing."""

    parser = argparse.ArgumentParser(
        description="Run the Wieland Collective email responder without n8n."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Check the inbox once and then exit instead of polling forever.",
    )
    parser.add_argument(
        "--manual-test",
        action="store_true",
        help="Create the same synthetic test email as the old manual workflow.",
    )
    parser.add_argument(
        "--draft-only",
        action="store_true",
        help="With --manual-test, print a draft without claiming or sending it.",
    )
    parser.add_argument(
        "--reset-baseline",
        action="store_true",
        help="Set the old-email cutoff to now, then exit.",
    )
    parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR"),
        default=os.getenv("EMAIL_RESPONDER_LOG_LEVEL", "INFO").upper(),
        help="Choose how much information the program prints.",
    )
    return parser


# Example: configure_logging("INFO")
def configure_logging(level: str) -> None:
    """Configure readable timestamped console logs."""

    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
