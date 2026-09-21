// Wiki.js response envelopes belong here, away from the indexing steps.

// Example: page = readWikiPage(response, 'Page missing');
function readWikiPage(response, missingMessage) {
  checkWikiErrors(response, 'page content');
  const page = response.data?.pages?.single ?? response.pages?.single;
  if (!page) throw new Error(missingMessage);
  return page;
}

// Example: pages = readWikiPageList(response);
function readWikiPageList(response) {
  checkWikiErrors(response, 'list pages');
  const pages = response.data?.pages?.list ?? response.pages?.list;
  if (!Array.isArray(pages)) {
    throw new Error('Wiki.js list pages response did not include data.pages.list. Check the GraphQL schema and API token.');
  }
  return pages;
}

// Example: checkWikiErrors(response, 'page content');
function checkWikiErrors(response, operation) {
  if (Array.isArray(response.errors) && response.errors.length) {
    const messages = response.errors.map((error) => error.message).join('; ');
    throw new Error(`Wiki.js ${operation} GraphQL error: ${messages}`);
  }
}
