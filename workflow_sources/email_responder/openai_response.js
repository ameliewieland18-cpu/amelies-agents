// Unpack the response shapes returned by the n8n OpenAI node.
// Example: body = readReplyBody(response);
function readReplyBody(response) {
  const output = response.output;
  let replyBody = '';

  if (Array.isArray(output)) {
    replyBody = output
      .flatMap((entry) => entry.content ?? [])
      .map((content) => content.text ?? '')
      .join('\n')
      .trim();
  } else if (typeof output === 'string') {
    replyBody = output.trim();
  } else if (response.output_text) {
    replyBody = String(response.output_text).trim();
  } else if (response.text) {
    replyBody = String(response.text).trim();
  }

  if (!replyBody) {
    throw new Error('GPT returned an empty email reply.');
  }

  return replyBody;
}
