// Split paragraphs into overlapping pieces small enough to embed.
const chunkText = (text, maxLength = 1200, overlap = 180) => {
  if (!text) return [];
  const blocks = text.split(/\n(?=#{1,6}\s)|\n\n+/).map((block) => block.trim()).filter(Boolean);
  const chunks = [];
  let current = '';

  const pushCurrent = () => {
    const trimmed = current.trim();
    if (trimmed) chunks.push(trimmed);
    current = '';
  };

  for (const block of blocks) {
    if (block.length > maxLength) {
      pushCurrent();
      for (let start = 0; start < block.length; start += maxLength - overlap) {
        chunks.push(block.slice(start, start + maxLength).trim());
      }
      continue;
    }

    const candidate = current ? `${current}\n\n${block}` : block;
    if (candidate.length > maxLength) {
      pushCurrent();
      current = block;
    } else {
      current = candidate;
    }
  }

  pushCurrent();
  return chunks;
};
