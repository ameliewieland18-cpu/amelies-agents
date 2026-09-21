// Indexing recipe. Response unpacking and record fields live in helper modules.
const page = readWikiPage($json, 'Wiki.js returned no page content. Check the page permissions and API token.');
const text = normalizeText(page.content || page.render || '');
const chunks = chunkText(text);
return buildChunkRecords(page, text, chunks);
