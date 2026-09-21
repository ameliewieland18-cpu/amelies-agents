// Database records for a page's chunks, including indexing metadata.
// Example: records = buildChunkRecords(page, text, chunks);
function buildChunkRecords(page, text, chunks) {
  const wikiBaseUrl = 'http://localhost:3000';
  const contentHash = hashText([page.id, page.path, page.updatedAt, text].join('\n'));
  const wikiUrl = wikiBaseUrl && page.path ? `${wikiBaseUrl}/${String(page.path).replace(/^\/+/, '')}` : null;
  const indexedAt = new Date().toISOString();

  return chunks.map((chunk, index) => ({
    json: {
      page_id: String(page.id),
      chunk_index: index,
      chunk_count: chunks.length,
      chunk_text: chunk,
      path: page.path ?? '',
      title: page.title ?? page.path ?? `Wiki.js page ${page.id}`,
      wiki_url: wikiUrl,
      last_seen_updated_at: page.updatedAt ?? null,
      content_hash: contentHash,
      indexed_at: indexedAt,
      metadata: {
        source: 'wikijs',
        page_id: String(page.id),
        path: page.path ?? '',
        title: page.title ?? page.path ?? `Wiki.js page ${page.id}`,
        wiki_url: wikiUrl,
        locale: page.locale ?? null,
        editor: page.editor ?? null,
        created_at: page.createdAt ?? null,
        updated_at: page.updatedAt ?? null,
        chunk_index: index,
        chunk_count: chunks.length,
      },
    },
  }));
}
