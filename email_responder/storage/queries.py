"""SQL statements, grouped in the order an email is processed.

The %s placeholders are filled by psycopg, never by string interpolation.
"""

ENSURE_STATE = """
INSERT INTO public.email_responder_state
  (mailbox, respond_after, top_k)
VALUES (%s, now(), 5)
ON CONFLICT (mailbox) DO NOTHING
"""

READ_STATE = """
SELECT respond_after, top_k
FROM public.email_responder_state
WHERE mailbox = %s
"""

INSERT_CLAIM = """
INSERT INTO public.email_responder_messages (
  mailbox, message_key, message_id, imap_uid, sender_email,
  sender_raw, subject, received_at, status, email_payload,
  claimed_at, updated_at
)
VALUES (
  %s, %s, NULLIF(%s, ''), %s, %s, %s, %s, %s, %s, %s,
  CASE WHEN %s = 'processing' THEN now() ELSE NULL END,
  now()
)
ON CONFLICT (mailbox, message_key) DO NOTHING
RETURNING id, status
"""

READ_CLAIM = """
SELECT id, status
FROM public.email_responder_messages
WHERE mailbox = %s AND message_key = %s
"""

RANK_CHUNKS = """
WITH email_embedding AS (
  SELECT %s::vector AS embedding
), ranked_chunks AS (
  SELECT
    kb.page_id,
    kb.path,
    kb.title,
    kb.wiki_url,
    kb.chunk_index,
    kb.chunk_text,
    kb.embedding <=> email_embedding.embedding AS distance
  FROM public.kb_chunks AS kb
  CROSS JOIN email_embedding
)
SELECT DISTINCT ON (page_id)
  page_id,
  path,
  title,
  wiki_url,
  chunk_index,
  chunk_text,
  distance
FROM ranked_chunks
ORDER BY page_id, distance ASC
"""

SAVE_OUTCOME = """
UPDATE public.email_responder_messages
SET
  status = %s,
  matched_pages = %s,
  reply_subject = %s,
  reply_body = %s,
  send_result = %s,
  replied_at = CASE
    WHEN %s = 'replied' THEN now()
    ELSE replied_at
  END,
  last_error = %s,
  updated_at = now()
WHERE mailbox = %s AND message_key = %s
"""

RESET_BASELINE = """
INSERT INTO public.email_responder_state
  (mailbox, respond_after, top_k, updated_at)
VALUES (%s, now(), 5, now())
ON CONFLICT (mailbox) DO UPDATE
SET respond_after = now(), updated_at = now()
"""
