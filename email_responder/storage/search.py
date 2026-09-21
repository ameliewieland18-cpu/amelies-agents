"""Search pgvector and translate database rows into ranked pages.

A page can match several email chunks. Keep its closest match, then choose K
*different pages*, rather than K chunks that might all belong to one page.
"""

from collections.abc import Sequence

import psycopg
from psycopg.rows import dict_row

from ..models import RankedPage
from . import queries


# Example: pages = rank_pages(database_url, embeddings, top_k=5)
def rank_pages(
    database_url: str, embeddings: Sequence[Sequence[float]], top_k: int
) -> list[RankedPage]:
    """Find the nearest knowledge-base page across every email chunk."""

    best_pages: dict[str, RankedPage] = {}
    query = queries.RANK_CHUNKS

    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            for email_chunk_index, embedding in enumerate(embeddings):
                vector_text = "[" + ",".join(str(value) for value in embedding) + "]"
                cursor.execute(query, (vector_text,))
                for row in cursor.fetchall():
                    page_id = str(row["page_id"])
                    distance = float(row["distance"])
                    current = best_pages.get(page_id)
                    if current is None or distance < current.best_distance:
                        best_pages[page_id] = RankedPage(
                            page_id=page_id,
                            path=str(row["path"] or ""),
                            title=str(row["title"] or row["path"] or page_id),
                            wiki_url=row["wiki_url"],
                            best_distance=distance,
                            matched_email_chunk_index=email_chunk_index,
                            matched_chunk_index=int(row["chunk_index"]),
                            matched_chunk_text=str(row["chunk_text"] or ""),
                        )

    ranked = sorted(best_pages.values(), key=lambda page: page.best_distance)
    if not ranked:
        raise RuntimeError(
            "No knowledge-base rows were found. Run the Wiki.js embedding index first."
        )

    selected = ranked[: min(top_k, len(ranked))]
    for rank, page in enumerate(selected, start=1):
        page.rank = rank
    return selected
