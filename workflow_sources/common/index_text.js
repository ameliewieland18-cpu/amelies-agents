// Plain text for embeddings and page context.
const stripHtml = (value) => String(value)
  .replace(/<script[\s\S]*?<\/script>/gi, ' ')
  .replace(/<style[\s\S]*?<\/style>/gi, ' ')
  .replace(/<[^>]+>/g, ' ');

const normalizeText = (value) => stripHtml(value)
  .replace(/```[\s\S]*?```/g, (block) => `\n${block}\n`)
  .replace(/\r\n/g, '\n')
  .replace(/[\t ]+/g, ' ')
  .replace(/\n{3,}/g, '\n\n')
  .trim();
