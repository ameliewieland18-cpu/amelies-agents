=WITH ensure_state AS (
  INSERT INTO public.email_responder_state (mailbox, respond_after, top_k)
  VALUES ('hello.wieland.collective@gmail.com', now(), 5)
  ON CONFLICT (mailbox) DO NOTHING
), state AS (
  SELECT mailbox, respond_after, top_k
  FROM public.email_responder_state
  WHERE mailbox = 'hello.wieland.collective@gmail.com'
), incoming AS (
  SELECT
    'hello.wieland.collective@gmail.com'::text AS mailbox,
    '{{ $json.message_key.replace(/'/g, "''") }}'::text AS message_key,
    NULLIF('{{ String($json.message_id ?? '').replace(/'/g, "''") }}', '') AS message_id,
    NULLIF('{{ String($json.imap_uid ?? '').replace(/'/g, "''") }}', '')::bigint AS imap_uid,
    '{{ $json.sender_email.replace(/'/g, "''") }}'::text AS sender_email,
    '{{ String($json.sender_raw ?? '').replace(/'/g, "''") }}'::text AS sender_raw,
    '{{ $json.original_subject.replace(/'/g, "''") }}'::text AS subject,
    '{{ $json.received_at.replace(/'/g, "''") }}'::timestamptz AS received_at,
    NULLIF('{{ String($json.skip_reason ?? '').replace(/'/g, "''") }}', '') AS skip_reason,
    '{{ $json.email_payload_sql }}'::jsonb AS email_payload
), skipped_old AS (
  INSERT INTO public.email_responder_messages (
    mailbox, message_key, message_id, imap_uid, sender_email, sender_raw,
    subject, received_at, status, email_payload, updated_at
  )
  SELECT
    incoming.mailbox, incoming.message_key, incoming.message_id, incoming.imap_uid,
    incoming.sender_email, incoming.sender_raw, incoming.subject, incoming.received_at,
    'skipped_old', incoming.email_payload, now()
  FROM incoming
  CROSS JOIN state
  WHERE incoming.received_at < state.respond_after
  ON CONFLICT (mailbox, message_key) DO NOTHING
  RETURNING id, status
), skipped_blocked AS (
  INSERT INTO public.email_responder_messages (
    mailbox, message_key, message_id, imap_uid, sender_email, sender_raw,
    subject, received_at, status, email_payload, updated_at
  )
  SELECT
    incoming.mailbox, incoming.message_key, incoming.message_id, incoming.imap_uid,
    incoming.sender_email, incoming.sender_raw, incoming.subject, incoming.received_at,
    'skipped_blocked', incoming.email_payload, now()
  FROM incoming
  CROSS JOIN state
  WHERE incoming.received_at >= state.respond_after
    AND incoming.skip_reason IS NOT NULL
  ON CONFLICT (mailbox, message_key) DO NOTHING
  RETURNING id, status
), claimed AS (
  INSERT INTO public.email_responder_messages (
    mailbox, message_key, message_id, imap_uid, sender_email, sender_raw,
    subject, received_at, status, email_payload, claimed_at, updated_at
  )
  SELECT
    incoming.mailbox, incoming.message_key, incoming.message_id, incoming.imap_uid,
    incoming.sender_email, incoming.sender_raw, incoming.subject, incoming.received_at,
    'processing', incoming.email_payload, now(), now()
  FROM incoming
  CROSS JOIN state
  WHERE incoming.received_at >= state.respond_after
    AND incoming.skip_reason IS NULL
  ON CONFLICT (mailbox, message_key) DO NOTHING
  RETURNING id, status
), existing AS (
  SELECT messages.id, messages.status
  FROM public.email_responder_messages AS messages
  JOIN incoming
    ON messages.mailbox = incoming.mailbox
   AND messages.message_key = incoming.message_key
  LIMIT 1
)
SELECT
  COALESCE((SELECT id FROM claimed), (SELECT id FROM skipped_blocked), (SELECT id FROM skipped_old), (SELECT id FROM existing)) AS email_record_id,
  EXISTS (SELECT 1 FROM claimed) AS should_reply,
  COALESCE((SELECT status FROM claimed), (SELECT status FROM skipped_blocked), (SELECT status FROM skipped_old), (SELECT status FROM existing), 'skipped_duplicate') AS status,
  (SELECT skip_reason FROM incoming) AS skip_reason,
  (SELECT top_k FROM state) AS top_k,
  (SELECT respond_after FROM state) AS respond_after,
  (SELECT email_payload FROM incoming) AS email_payload;
