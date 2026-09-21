// A successful AI response becomes the body of the prepared reply.
const promptItem = $items('Build reply prompt')[0]?.json;
if (!promptItem) {
  throw new Error('Missing reply prompt context.');
}

const replyBody = readReplyBody($json);

return [{
  json: {
    ...promptItem,
    reply_body: replyBody,
  },
}];
