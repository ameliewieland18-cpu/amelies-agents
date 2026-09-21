"""Text cleanup and chunking used for email and knowledge-base content."""

from __future__ import annotations

import html
import re


# Example: clean = strip_html("<p>Hello</p>")
def strip_html(value: str) -> str:
    """Remove scripts, styles, and HTML tags while keeping readable spacing."""

    without_scripts = re.sub(
        r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE
    )
    without_styles = re.sub(
        r"<style[\s\S]*?</style>", " ", without_scripts, flags=re.IGNORECASE
    )
    with_line_breaks = re.sub(r"<br\s*/?>", "\n", without_styles, flags=re.IGNORECASE)
    with_paragraphs = re.sub(r"</p>", "\n\n", with_line_breaks, flags=re.IGNORECASE)
    without_tags = re.sub(r"<[^>]+>", " ", with_paragraphs)
    return html.unescape(without_tags).replace("\u00a0", " ")


# Example: clean = normalize_whitespace("Hello   world")
def normalize_whitespace(value: str) -> str:
    """Normalize spaces and blank lines without flattening paragraphs."""

    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[\t ]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


# Example: clean = normalize_text("<p>Hello</p>")
def normalize_text(value: str) -> str:
    """Convert possible HTML into normalized plain text."""

    return normalize_whitespace(strip_html(value))


# Example: chunks = chunk_text("A long message", max_length=1200, overlap=180)
def chunk_text(text: str, max_length: int = 1200, overlap: int = 180) -> list[str]:
    """Split text into overlapping chunks like the original n8n workflow."""

    if not text:
        return []
    if max_length <= 0:
        raise ValueError("max_length must be greater than zero")
    if overlap < 0 or overlap >= max_length:
        raise ValueError("overlap must be at least zero and smaller than max_length")

    blocks = [
        block.strip()
        for block in re.split(r"\n(?=#{1,6}\s)|\n\n+", text)
        if block.strip()
    ]
    chunks: list[str] = []
    current = ""

    for block in blocks:
        # Oversized paragraphs need overlapping slices so nearby ideas stay together.
        if len(block) > max_length:
            if current:
                chunks.append(current.strip())
                current = ""

            step = max_length - overlap
            for start in range(0, len(block), step):
                piece = block[start : start + max_length].strip()
                if piece:
                    chunks.append(piece)
            continue

        # Smaller paragraphs can share one chunk until adding another would exceed it.
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) > max_length:
            if current:
                chunks.append(current.strip())
            current = block
        else:
            current = candidate

    if current:
        chunks.append(current.strip())

    return chunks
