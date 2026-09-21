=WITH deleted AS (
  DELETE FROM public.kb_chunks
  WHERE page_id = '{{ $('Prepare chunks').item.json.page_id.replace(/'/g, "''") }}'
    AND {{ $('Prepare chunks').item.json.chunk_index }} = 0
), state AS (
  INSERT INTO public.kb_index_state (
    page_id,
    path,
    title,
    wiki_url,
    last_seen_updated_at,
    last_indexed_at,
    content_hash,
    chunk_count
  ) VALUES (
    '{{ $('Prepare chunks').item.json.page_id.replace(/'/g, "''") }}',
    '{{ $('Prepare chunks').item.json.path.replace(/'/g, "''") }}',
    '{{ $('Prepare chunks').item.json.title.replace(/'/g, "''") }}',
    NULLIF('{{ String($('Prepare chunks').item.json.wiki_url ?? '').replace(/'/g, "''") }}', ''),
    NULLIF('{{ String($('Prepare chunks').item.json.last_seen_updated_at ?? '').replace(/'/g, "''") }}', '')::timestamptz,
    now(),
    '{{ $('Prepare chunks').item.json.content_hash.replace(/'/g, "''") }}',
    {{ $('Prepare chunks').item.json.chunk_count }}
  )
  ON CONFLICT (page_id) DO UPDATE SET
    path = EXCLUDED.path,
    title = EXCLUDED.title,
    wiki_url = EXCLUDED.wiki_url,
    last_seen_updated_at = EXCLUDED.last_seen_updated_at,
    last_indexed_at = now(),
    content_hash = EXCLUDED.content_hash,
    chunk_count = EXCLUDED.chunk_count
  RETURNING page_id
), inserted AS (
  INSERT INTO public.kb_chunks (
    page_id,
    chunk_index,
    chunk_text,
    path,
    title,
    wiki_url,
    content_hash,
    metadata,
    embedding
  )
  SELECT
    state.page_id,
    {{ $('Prepare chunks').item.json.chunk_index }},
    '{{ $('Prepare chunks').item.json.chunk_text.replace(/'/g, "''") }}',
    '{{ $('Prepare chunks').item.json.path.replace(/'/g, "''") }}',
    '{{ $('Prepare chunks').item.json.title.replace(/'/g, "''") }}',
    NULLIF('{{ String($('Prepare chunks').item.json.wiki_url ?? '').replace(/'/g, "''") }}', ''),
    '{{ $('Prepare chunks').item.json.content_hash.replace(/'/g, "''") }}',
    '{{ JSON.stringify($('Prepare chunks').item.json.metadata).replace(/'/g, "''") }}'::jsonb,
    '[{{ $json.data[0].embedding.join(',') }}]'::vector
  FROM state
  ON CONFLICT (page_id, chunk_index) DO UPDATE SET
    chunk_text = EXCLUDED.chunk_text,
    path = EXCLUDED.path,
    title = EXCLUDED.title,
    wiki_url = EXCLUDED.wiki_url,
    content_hash = EXCLUDED.content_hash,
    metadata = EXCLUDED.metadata,
    embedding = EXCLUDED.embedding,
    updated_at = now()
  RETURNING id
)
SELECT
  inserted.id AS kb_chunk_id,
  '{{ $('Prepare chunks').item.json.page_id.replace(/'/g, "''") }}' AS page_id,
  {{ $('Prepare chunks').item.json.chunk_index }} AS chunk_index
FROM inserted;
