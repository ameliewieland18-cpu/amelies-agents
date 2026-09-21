# Readable n8n workflow sources

Read the short entry script for a node first. Helper files explain the details it
calls. `manifest.json` lists the helper files and entry script for each node, in
execution order. Names correspond to the nodes visible in n8n.

| Tool | Start here | Details live beside it |
| --- | --- | --- |
| Job report | [`job_report/build_report_document.js`](job_report/build_report_document.js) | Markdown layout, HTML layout, and escaping |
| Wiki.js indexing | [`wiki_index/extract_page_list.js`](wiki_index/extract_page_list.js), then [`prepare_chunks.js`](wiki_index/prepare_chunks.js) | Chunk record fields; shared response and text helpers in `common/` |
| Legacy email responder | [`email_responder/normalize_email.js`](email_responder/normalize_email.js), [`prepare_email_chunks.js`](email_responder/prepare_email_chunks.js), [`rank_top_k_pages.js`](email_responder/rank_top_k_pages.js), [`build_reply_prompt.js`](email_responder/build_reply_prompt.js), [`prepare_email_reply.js`](email_responder/prepare_email_reply.js) | Sender rules, message fields, ranking, prompt text, and OpenAI response unpacking |

The legacy email responder is an inactive migration reference. The Python
responder is the current implementation. Do not enable both for the same inbox.

## Editing and rebuilding

Edit these `.js` and `.sql` files, then run from the repository root:

```bash
python scripts/build_workflows.py
python scripts/build_workflows.py --check
node --test tests/workflows/*.test.cjs
```

The build script copies SQL and joins JavaScript helper declarations before each
entry script. It places the result in the corresponding node's `query` or
`jsCode` field. The generated scripts include source-path comments for tracing
code back to these files. The exported workflow remains self-contained: n8n does
not need this source directory, a module loader, or additional permissions.

Commit both the source changes and rebuilt `workflows/*.json` exports. Import the
rebuilt JSON through your usual n8n workflow import process. Building files does
not deploy or activate workflows.

To add a helper, put its path before the entry script in that node's manifest
entry. Helpers use ordinary JavaScript functions or constants; they are combined
into a single scope, so give them distinct names. Only the entry script returns
n8n items. The `$json`, `$input`, `$items`, and `items` values are supplied by n8n.

For visual connections or other node settings, edit/export the workflow JSON as
usual, then rebuild its script fields from these sources. To retain a code change
made in the n8n editor, copy it into its source file before rebuilding. The
`--check` command reports differences without writing files.
