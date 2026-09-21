=UPDATE public.email_responder_messages
SET
  status = '{{ $json.error ? "failed" : "replied" }}',
  matched_pages = '{{ JSON.stringify($('Prepare email reply').item.json.matched_pages).replace(/'/g, "''") }}'::jsonb,
  reply_subject = '{{ $('Prepare email reply').item.json.reply_subject.replace(/'/g, "''") }}',
  reply_body = '{{ $('Prepare email reply').item.json.reply_body.replace(/'/g, "''") }}',
  send_result = '{{ JSON.stringify($json).replace(/'/g, "''") }}'::jsonb,
  replied_at = CASE WHEN '{{ $json.error ? "failed" : "replied" }}' = 'replied' THEN now() ELSE replied_at END,
  last_error = CASE
    WHEN '{{ $json.error ? "failed" : "replied" }}' = 'failed'
      THEN NULLIF('{{ String($json.error ?? '').replace(/'/g, "''") }}', '')
    ELSE NULL
  END,
  updated_at = now()
WHERE mailbox = 'hello.wieland.collective@gmail.com'
  AND message_key = '{{ $('Prepare email reply').item.json.email_payload.message_key.replace(/'/g, "''") }}'
RETURNING id, mailbox, message_key, status, replied_at, last_error;
