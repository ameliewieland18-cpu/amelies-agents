"""Stable message identifiers, including compatibility with the old n8n hash.

This arithmetic is a storage detail. Start with normalize.py to follow an email.
"""


# Example: key = workflow_hash("sender@example.com")
def workflow_hash(value: str) -> str:
    """Reproduce the n8n workflow's 64-bit-looking fallback message hash."""

    encoded = value.encode("utf-16-le", errors="surrogatepass")
    character_codes = [
        int.from_bytes(encoded[index : index + 2], "little")
        for index in range(0, len(encoded), 2)
    ]

    mask = 0xFFFFFFFF
    h1 = 0xDEADBEEF
    h2 = 0x41C6CE57

    for character_code in character_codes:
        h1 = ((h1 ^ character_code) * 2654435761) & mask
        h2 = ((h2 ^ character_code) * 1597334677) & mask

    h1 = (
        (((h1 ^ (h1 >> 16)) * 2246822507) & mask)
        ^ (((h2 ^ (h2 >> 13)) * 3266489909) & mask)
    ) & mask
    h2 = (
        (((h2 ^ (h2 >> 16)) * 2246822507) & mask)
        ^ (((h1 ^ (h1 >> 13)) * 3266489909) & mask)
    ) & mask
    return f"{h2:08x}{h1:08x}"
