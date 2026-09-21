=WITH email_embedding AS (
  SELECT '[{{ $json.data[0].embedding.join(',') }}]'::vector AS embedding
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
), best_chunk_per_page AS (
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
)
SELECT
  '{{ $('Prepare email chunks').item.json.email_payload_sql }}'::jsonb AS email_payload,
  {{ $('Prepare email chunks').item.json.chunk_index }}::integer AS email_chunk_index,
  {{ $('Prepare email chunks').item.json.chunk_count }}::integer AS email_chunk_count,
  {{ $('Prepare email chunks').item.json.top_k }}::integer AS top_k,
  page_id,
  path,
  title,
  wiki_url,
  distance,
  chunk_index AS matched_chunk_index,
  chunk_text AS matched_chunk_text
FROM best_chunk_per_page
ORDER BY distance ASC;
