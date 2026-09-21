// Read published pages, then expose the fields the next node needs.
const pages = readWikiPageList(items[0]?.json ?? {});

return pages
  .filter((page) => page && page.id !== undefined && page.id !== null)
  .filter((page) => page.isPublished !== false)
  .map((page) => ({
    json: {
      page_id: String(page.id),
      page_id_number: Number(page.id),
      path: page.path ?? '',
      title: page.title ?? page.path ?? `Wiki.js page ${page.id}`,
      locale: page.locale ?? null,
      description: page.description ?? null,
      updated_at: page.updatedAt ?? null,
      created_at: page.createdAt ?? null,
    },
  }));
