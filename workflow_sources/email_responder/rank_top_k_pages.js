// Select up to K different pages and carry the email along to the next node.
const rows = $input.all().map((item) => item.json);
if (!rows.length) {
  throw new Error('No knowledge-base rows were scored. Run wikijs-embeddings-index before enabling the responder.');
}

const emailPayload = parsePayload(rows[0].email_payload);
const topK = Number(rows[0].top_k ?? emailPayload.top_k ?? 5);
const rankedPages = rankDistinctPages(rows);

const effectiveTopK = Math.min(topK, rankedPages.length);

return rankedPages.slice(0, effectiveTopK).map((page, index) => ({
  json: {
    email_payload: emailPayload,
    top_k: topK,
    available_page_count: rankedPages.length,
    returned_page_count: effectiveTopK,
    rank: index + 1,
    page_id: page.page_id,
    page_id_number: Number(page.page_id),
    path: page.path ?? '',
    title: page.title ?? page.path ?? ('Wiki.js page ' + page.page_id),
    wiki_url: page.wiki_url ?? null,
    best_distance: page.best_distance,
    matched_email_chunk_index: Number(page.email_chunk_index ?? 0),
    matched_chunk_index: Number(page.matched_chunk_index ?? 0),
    matched_chunk_text: page.matched_chunk_text ?? '',
  },
}));
