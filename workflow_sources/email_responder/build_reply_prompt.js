// Gather the full pages, build writing instructions, and prepare reply context.
const pageResponses = $input.all();
const rankedPages = $items('Rank top K pages').map((item) => item.json);

if (!rankedPages.length) {
  throw new Error('No ranked Wiki.js pages are available for the reply prompt.');
}

const emailPayload = rankedPages[0].email_payload;

const contextPages = buildContextPages(pageResponses, rankedPages);
const prompt = buildReplyPrompt(emailPayload, contextPages);

return [{
  json: {
    email_payload: emailPayload,
    to_email: emailPayload.sender_email,
    from_email: emailPayload.account_email,
    reply_subject: emailPayload.reply_subject,
    original_subject: emailPayload.original_subject,
    prompt,
    matched_pages: contextPages,
  },
}];
