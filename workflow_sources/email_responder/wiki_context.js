// Join fetched Wiki.js content to the ranking metadata used in the prompt.
// Example: pages = buildContextPages(responses, rankedPages);
function buildContextPages(pageResponses, rankedPages) {
  return pageResponses.map((item, index) => {
    const response = item.json ?? {};
    const page = readWikiPage(response, 'Wiki.js returned no page content for a ranked page.');

    const ranking = rankedPages[index] ?? rankedPages.find((candidate) => String(candidate.page_id) === String(page.id));
    const content = normalizeText(page.content || page.render || '');

    return {
      rank: ranking?.rank ?? index + 1,
      title: page.title ?? ranking?.title ?? page.path ?? ('Wiki.js page ' + page.id),
      path: page.path ?? ranking?.path ?? '',
      wiki_url: ranking?.wiki_url ?? null,
      best_distance: ranking?.best_distance ?? null,
      matched_email_chunk_index: ranking?.matched_email_chunk_index ?? null,
      matched_chunk_index: ranking?.matched_chunk_index ?? null,
      content,
    };
  });

}
