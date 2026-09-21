// Writing instructions and readable page formatting, with no service calls.
// Example: prompt = buildReplyPrompt(email, pages);
function buildReplyPrompt(emailPayload, contextPages) {
  const knowledgeBaseContext = contextPages
    .sort((a, b) => a.rank - b.rank)
    .map((page) => [
      '## ' + page.rank + '. ' + page.title,
      'Path: ' + page.path,
      page.wiki_url ? 'URL: ' + page.wiki_url : null,
      page.best_distance !== null ? 'Best embedding distance: ' + page.best_distance : null,
      page.matched_email_chunk_index !== null ? 'Matched email chunk: ' + page.matched_email_chunk_index : null,
      page.matched_chunk_index !== null ? 'Matched KB chunk: ' + page.matched_chunk_index : null,
      '',
      page.content,
    ].filter((line) => line !== null).join('\n'))
    .join('\n\n---\n\n');

  const prompt = [
    'You are replying on behalf of Wieland Collective from ' + emailPayload.account_email + '.',
    '',
    'Write a helpful email reply to the sender. Use the Wiki.js knowledge-base pages below as the factual context for the reply. Do not invent details that are not supported by the context or the incoming email. If the context does not answer a specific question, say that we will follow up. Keep the tone warm, concise, and professional. Match the incoming email language when practical. Return only the email body; do not include a subject line, markdown code fence, or analysis.',
    '',
    '# Retrieved Wiki.js Context (' + contextPages.length + ' distinct pages)',
    knowledgeBaseContext,
    '',
    '# Incoming Email',
    emailPayload.full_email,
    '',
    '# Reply Body',
  ].join('\n');

  return prompt;
}
