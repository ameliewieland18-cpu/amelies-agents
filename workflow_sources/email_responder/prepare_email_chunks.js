// Turn the email body into pieces for semantic retrieval.
const emailPayload = $json.email_payload ?? $json;
const text = normalizeText(emailPayload.email_text ?? '');
const chunks = chunkText(text);

if (!chunks.length) {
  throw new Error('Email text produced zero chunks after normalization.');
}

return chunks.map((chunk, index) => ({
  json: {
    email_payload: emailPayload,
    email_payload_sql: $json.email_payload_sql ?? JSON.stringify(emailPayload).replace(/'/g, "''"),
    top_k: Number(emailPayload.top_k ?? 5),
    chunk_index: index,
    chunk_count: chunks.length,
    chunk_text: chunk,
  },
}));
