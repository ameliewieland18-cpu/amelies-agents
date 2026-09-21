// Keep each page's best match across all email chunks, then sort by distance.
// Example: pages = rankDistinctPages(rows);
function rankDistinctPages(rows) {
  const bestByPage = new Map();

  for (const row of rows) {
    if (!row.page_id) continue;
    const distance = Number(row.distance);
    if (!Number.isFinite(distance)) continue;

    const key = String(row.page_id);
    const current = bestByPage.get(key);
    if (!current || distance < current.best_distance) {
      bestByPage.set(key, {
        ...row,
        page_id: key,
        best_distance: distance,
      });
    }
  }

  const rankedPages = [...bestByPage.values()]
    .sort((a, b) => a.best_distance - b.best_distance);

  if (!rankedPages.length) {
    throw new Error('No distinct Wiki.js pages were available. Run wikijs-embeddings-index before enabling the responder.');
  }

  return rankedPages;
}
