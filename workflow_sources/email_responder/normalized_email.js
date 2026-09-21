// Build the ordinary email fields consumed by the rest of the workflow.
// Example: email = normalizeEmail(rawMessage);
function normalizeEmail(message) {
  const senderEmail = extractEmail(message.from);
  if (!senderEmail) {
    throw new Error('Incoming email did not include a parseable From address.');
  }

  if (senderEmail === ACCOUNT_EMAIL) {
    return null;
  }

  const senderRaw = formatAddress(message.from) || senderEmail;
  const skipInfo = getBlockedSenderReason(senderEmail, senderRaw);
  const skipBeforeReply = Boolean(skipInfo.skip_reason);

  const textPlain = normalizeWhitespace(message.textPlain ?? message.text ?? '');
  const textHtml = normalizeWhitespace(stripHtml(message.textHtml ?? message.html ?? message.textAsHtml ?? ''));
  const emailText = textPlain || textHtml;

  if (!emailText && !skipBeforeReply) {
    throw new Error('Incoming email did not include a plain-text or HTML body to answer.');
  }

  const originalSubject = normalizeWhitespace(message.subject ?? '(no subject)');
  const replySubject = /^\s*re:/i.test(originalSubject) ? originalSubject : 'Re: ' + originalSubject;
  const messageId = normalizeWhitespace(message.metadata?.['message-id'] ?? message.metadata?.messageId ?? message.messageId ?? '');
  const gmailId = normalizeWhitespace(message.id ?? '');
  const gmailThreadId = normalizeWhitespace(message.threadId ?? '');
  const imapUid = message.attributes?.uid ?? null;
  const receivedAt = parseDate(message.date).toISOString();
  const messageKey = messageId || (gmailId ? 'gmail-id:' + gmailId : ('imap-uid:' + String(imapUid ?? 'none') + ':' + hashText([senderEmail, receivedAt, originalSubject, emailText].join('\n'))));
  const toRaw = formatAddress(message.to) || ACCOUNT_EMAIL;
  const ccRaw = formatAddress(message.cc);

  const fullEmail = [
    'From: ' + senderRaw,
    'To: ' + toRaw,
    'Date: ' + receivedAt,
    'Subject: ' + originalSubject,
    '',
    emailText,
  ].join('\n');

  const emailPayload = {
    mailbox: ACCOUNT_EMAIL,
    account_email: ACCOUNT_EMAIL,
    sender_email: senderEmail,
    sender_raw: senderRaw,
    to_raw: toRaw,
    cc_raw: ccRaw,
    received_at: receivedAt,
    message_id: messageId,
    message_key: messageKey,
    original_subject: originalSubject,
    reply_subject: replySubject,
    email_text: emailText,
    full_email: fullEmail,
    imap_uid: imapUid,
    gmail_id: gmailId,
    gmail_thread_id: gmailThreadId,
    skip_before_reply: skipBeforeReply,
    ...skipInfo,
  };

  return emailPayload;
}
