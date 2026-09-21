# Amelie's Agents

This repository contains local automation tools and a Docker Compose setup for supporting services such as Wiki.js, Mathesar, Postgres, and Gotenberg. The automatic email responder is a standalone Python program and does not need n8n.

## Reading and changing the code

Start with the [code reading guide](docs/reading-the-code.md). It introduces the
project one file at a time, beginning with the main workflow and following its
building blocks down to service-specific details.

The Python responder starts in [`email_responder/app.py`](email_responder/app.py).
The story for one email is in
[`email_responder/responder.py`](email_responder/responder.py): claim the email,
create a draft, send it, and record the result. Gmail protocols, SQL, and API
response unpacking live in dedicated modules below that workflow.

The n8n scripts are readable source files in [`workflow_sources/`](workflow_sources/README.md).
After editing them, rebuild the self-contained workflow JSON files:

```bash
python scripts/build_workflows.py
```

Run the offline checks before committing (Node.js is needed for the workflow tests):

```bash
uv run python -m unittest discover -s tests -v
node --test tests/workflows/*.test.cjs
python scripts/build_workflows.py --check
uvx ruff check email_responder tests scripts
uvx ruff format --check email_responder tests scripts
```

The tests use fake services and do not send email, use API credits, or change a database.

## Included Files

- `compose.yaml`: runs `n8n`, `Wiki.js`, `Mathesar`, `Postgres`, and `Gotenberg`
- `mathesar-data/`: host folder for Mathesar state, uploads, secrets, and its internal PostgreSQL data
- `.env.example`: optional environment values you can customize
- `local-files/`: host folder mounted into the container at `/files`
- `local-files/reports/`: host folder where generated Markdown and PDF reports are written
- `workflows/`: tracked host folder mounted into the container at `/workflows`
- `workflow_sources/`: readable JavaScript and SQL sources for the n8n exports
- `scripts/build_workflows.py`: bundles those sources into the importable exports
- `schema/00_pgvector.sql`: enables the `pgvector` extension in the app database
- `schema/01_wikijs.sh`: creates the Wiki.js database and enables its PostgreSQL extensions on first startup
- `schema/02_kb_embeddings.sql`: creates the Wiki.js knowledge-base embedding tables
- `schema/03_email_responder.sql`: creates the automatic email responder state and processed-message tables
- `email_responder/`: standalone Python email responder
- `tests/`: unit tests for the Python email responder
- `pyproject.toml`: Python dependencies, package metadata, and the `email-responder` command
- `schema/freelance.sql`: core tables for the freelance assistant database
- `schema/job_search.sql`: expected `job_search` table definition for the report workflow
- `n8n-data/`: host folder for n8n state and SQLite data
- `postgres-data/`: host folder for Postgres database files

## First Run

1. Start Docker Desktop and wait until it shows as running.
2. Open PowerShell in this project directory.
3. Optionally copy the example environment file:

```powershell
Copy-Item .env.example .env
```

4. Start the stack:

```powershell
docker compose up -d
```

5. Open [http://localhost:5678](http://localhost:5678) for `n8n`.
6. Open [http://localhost:3000](http://localhost:3000) for `Wiki.js` and complete the first-run setup in the browser.

## Configuration

If you create a `.env` file, you can change:

- `GENERIC_TIMEZONE`: timezone used by scheduling nodes
- `TZ`: container system timezone
- `N8N_PORT`: host port exposed by Docker
- `N8N_RESTRICT_FILE_ACCESS_TO`: semicolon-separated allowlist for n8n file read/write nodes
- `POSTGRES_DB`: Postgres database name reusable from other services
- `POSTGRES_USER`: Postgres username reusable from other services
- `POSTGRES_PASSWORD`: Postgres password reusable from other services
- `WIKIJS_PORT`: host port exposed by Docker for Wiki.js
- `WIKIJS_DB_NAME`: dedicated PostgreSQL database name used by Wiki.js
- `MATHESAR_PORT`: host port exposed by Docker for Mathesar
- `MATHESAR_DOMAIN_NAME`: local domain Mathesar uses for generated URLs
- `MATHESAR_ALLOWED_HOSTS`: local hostnames Mathesar is allowed to serve
- `MATHESAR_POSTGRES_DB`: dedicated PostgreSQL database name used by Mathesar for internal metadata
- `MATHESAR_POSTGRES_USER`: PostgreSQL username used by Mathesar for internal metadata
- `MATHESAR_POSTGRES_PASSWORD`: PostgreSQL password used by Mathesar for internal metadata
- `MATHESAR_WEB_CONCURRENCY`: number of Mathesar web workers
- `MATHESAR_SECRET_KEY`: optional persistent Django secret key for Mathesar; if empty, Mathesar persists a generated key in `mathesar-data/secrets/`

The setup stores n8n data in the host directory `n8n-data/`, so workflows, credentials, and the n8n encryption key survive container restarts.

Postgres stores its data in the host directory `postgres-data/`.

The default Postgres database is `freelance`, which is intended to become the central database for the freelance marketing assistant.

Wiki.js uses a separate PostgreSQL database named `wiki` by default, created inside the same Postgres server during first initialization.

Mathesar runs as a browser-based, spreadsheet-like interface for PostgreSQL. It uses its own `mathesar-db` container for internal metadata, while still being able to connect to the main `postgres` service on the Docker network.

Postgres is also exposed on the Windows host at `127.0.0.1:5432`, so local tools can connect with the same database name, username, and password.

On the first container startup with an empty `postgres-data/` directory, Postgres automatically executes every script inside `schema/`. That means the `freelance` database starts with the `pgvector` extension enabled, the freelance tables, and the existing `job_search` table definition, while the dedicated Wiki.js database is also created and prepared.

If you already have initialized Postgres data in `postgres-data/`, the init scripts will not run again automatically. In that case, create the Wiki.js database manually, enable any needed extensions, and apply any SQL changes you need, or recreate the Postgres volume if you want a clean local reset.

The local folder `local-files/` is mounted into the container at `/files`. This is useful for nodes that read or write files on disk.

The Compose setup also allowlists `/files` for n8n file nodes via `N8N_RESTRICT_FILE_ACCESS_TO`, otherwise the `Read/Write Files from Disk` node refuses to write there even though Docker has mounted the directory.

The tracked folder `workflows/` is mounted into the container at `/workflows`. Use it for exported workflow JSON files that you want to commit to Git.

The `job-search-nice-1` workflow expects `public.job_search` to use `text` for `company`, `role`, and `link`. A ready-to-run definition and upgrade script is included in `schema/job_search.sql`.

The `wikijs-embeddings-index` workflow reads all published Wiki.js pages through GraphQL, chunks their Markdown/HTML content, creates OpenAI embeddings, and stores the chunks in `freelance.public.kb_chunks`. It updates `freelance.public.kb_index_state` with the page path, title, content hash, last Wiki.js update timestamp, and chunk count. The workflow is scheduled once per day at midnight by default.

Before running `wikijs-embeddings-index`, create a Wiki.js API token in the Wiki.js admin area. Then create an n8n `Header Auth` credential named `Wiki.js API token` with header name `Authorization` and header value `Bearer <your-token>`, and select that credential on the `List Wiki.js pages` and `Fetch page content` nodes. The workflow uses the n8n credential named `OpenAi account` for embeddings. If your Postgres data directory was already initialized before `schema/02_kb_embeddings.sql` existed, apply the schema manually:

```powershell
Get-Content .\schema\02_kb_embeddings.sql -Raw | docker exec -i postgres psql -U appuser -d freelance
```

Import or refresh workflows from the tracked `workflows/` folder as needed. The Wiki.js embedding workflow is stored at `workflows/wikijs-embeddings-index.json`.

## Standalone Python email responder

The email responder now runs as a normal Python program, without n8n. It reads new unread messages from `hello.wieland.collective@gmail.com` through Gmail IMAP. It chunks the email body with the same strategy as the Wiki.js embedding index, embeds each chunk with OpenAI, scores those embeddings against `public.kb_chunks`, selects up to the configured top-K distinct Wiki.js pages, fetches those pages, asks GPT to draft a reply, sends the reply through Gmail SMTP, and marks the original message as `replied` or `failed` in Postgres. If the knowledge base has fewer than K pages, the program uses every available page.

The old `workflows/automatic-email-responder.json` file remains as an inactive migration reference. Do not activate that workflow and the Python responder at the same time.

### Install and configure

Python and uv must be installed on the host. Copy the example configuration, then fill in the three blank secrets:

```bash
cp .env.example .env
uv sync
```

Required secrets in `.env`:

- `GMAIL_APP_PASSWORD`: a Google App Password for the responder mailbox
- `OPENAI_API_KEY`: the OpenAI project API key used for embeddings and reply drafts
- `WIKIJS_API_TOKEN`: the Wiki.js API token, either with or without the `Bearer ` prefix

The default URLs assume the Python program runs on the host and PostgreSQL and Wiki.js run through this repository's Docker Compose setup. Start those two services with:

```bash
docker compose up -d postgres wikijs
```

The program uses `gpt-5.4` for replies and `text-embedding-3-small` for retrieval by default, matching the old workflow. OpenAI response storage is disabled by default because prompts contain incoming customer email. All settings can be changed in `.env`.

If the database was initialized before `schema/03_email_responder.sql` was added, apply it once:

```bash
docker exec -i postgres psql -U appuser -d freelance < schema/03_email_responder.sql
```

### Test safely

Create a reply draft from the synthetic test email without claiming a database record or sending mail:

```bash
uv run email-responder --manual-test --draft-only
```

Send the synthetic test reply to the mailbox's `+manual-test` Gmail alias:

```bash
uv run email-responder --manual-test
```

### Run automatically

Immediately before the first live run, reset the old-email cutoff. This prevents old unread mail from receiving replies:

```bash
uv run email-responder --reset-baseline
```

Check the inbox once:

```bash
uv run email-responder --once
```

Keep polling the inbox every 60 seconds:

```bash
uv run email-responder
```

Stop the program with `Ctrl+C`. Duplicate protection is stored in PostgreSQL, so restarting the program does not reply to the same message twice.

For manual end-to-end testing, use the `--manual-test` option. It creates a synthetic inbound email from `hello.wieland.collective+manual-test@gmail.com`, so the generated reply is sent back into the same Gmail mailbox instead of a real external contact.

The responder has four duplicate/old-mail guards:

- The IMAP reader requests only `UNSEEN` messages and marks each handled message as read.
- The normalizer skips messages sent by `hello.wieland.collective@gmail.com`, which avoids replying to the responder's own outbound mail.
- The normalizer also blocks configured marketplace/newsletter senders before embeddings or GPT. Blocked messages are stored as `skipped_blocked`; edit `EMAIL_RESPONDER_BLOCKED_DOMAINS` and `EMAIL_RESPONDER_BLOCKED_KEYWORDS` in `.env` to add or remove senders.
- `public.email_responder_messages` has a unique `(mailbox, message_key)` constraint. The program must claim a message as `processing` before embeddings, GPT, or email sending can happen. After the SMTP send succeeds, the program updates the row to `replied`; if SMTP rejects the send, it updates the row to `failed` and stores the error in `last_error`.

`public.email_responder_state.respond_after` defines the old-email cutoff. Messages received before that timestamp are inserted as `skipped_old` and are not answered. Reset this baseline immediately before activating the responder if you want to guarantee that only messages received after activation can be answered:

```powershell
docker exec postgres psql -U appuser -d freelance -c "UPDATE public.email_responder_state SET respond_after = now(), updated_at = now() WHERE mailbox = 'hello.wieland.collective@gmail.com';"
```

Use a Google App Password for Gmail IMAP/SMTP, not the normal Google account password. Store it only in the ignored `.env` file; do not put it in Python code or Git.

Telemetry diagnostics and version-check notifications are disabled for `n8n`.

Because `n8n-data/` is a Windows host bind mount, `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` is disabled in this setup.

`Wiki.js` is configured against the current stable major Docker image (`ghcr.io/requarks/wiki:2`) and uses the same Postgres credentials as the rest of the local stack by default, but with its own empty database.

`Gotenberg` runs as an internal PDF conversion service on the Docker network at `http://gotenberg:3000`. The `job-search-nice-1` workflow uses it to turn an HTML report into a PDF without relying on any external web service.

## Common Commands

Start or recreate the stack:

```powershell
docker compose up -d
```

View logs:

```powershell
docker compose logs -f
```

Export all workflows as separate JSON files into the tracked `workflows/` folder:

```powershell
& "$Env:ProgramFiles\Docker\Docker\resources\bin\docker.exe" exec -u node n8n `
  n8n export:workflow --all --separate --pretty --output=/workflows
```

Stop the stack:

```powershell
docker compose stop
```

Start it again:

```powershell
docker compose start
```

Stop and remove the containers without deleting the host data directories:

```powershell
docker compose down
```

All service data remains in `n8n-data/`, `postgres-data/`, and `mathesar-data/` even after `docker compose down`.

Generated job-search reports are written to `local-files/reports/` on the host and appear inside the `n8n` container at `/files/reports/`.

The workflow writes those reports to fixed paths:

- `local-files/reports/job-search-report.md`
- `local-files/reports/job-search-report.pdf`

Update to the newest n8n image:

```powershell
docker compose pull
docker compose up -d
```

Open Mathesar:

```powershell
docker compose up -d mathesar
```

Then visit [http://localhost:8000](http://localhost:8000) and create the first Mathesar admin account.

To connect Mathesar to the main freelance database from inside the Mathesar UI, use:

- Host: `postgres`
- Port: `5432`
- Database: `freelance`
- Username: `appuser`
- Password: `change-me-for-local-dev`

If you changed the `POSTGRES_*` values in `.env`, use those values instead.

Apply the freelance schema manually to an already-running Postgres container:

```powershell
Get-Content .\schema\freelance.sql -Raw | docker exec -i postgres psql -U appuser -d freelance
```

Enable `pgvector` manually for an already-initialized database:

```powershell
docker exec -i postgres psql -U appuser -d freelance -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

Create the Wiki.js database manually for an already-initialized Postgres container:

```powershell
docker exec -i postgres createdb -U appuser -O appuser wiki
docker exec -i postgres psql -U appuser -d wiki -c "CREATE EXTENSION IF NOT EXISTS pgcrypto; CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

## License

This repository is licensed under the GNU Affero General Public License v3.0. See `LICENSE`.
