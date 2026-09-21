# Read the project one file at a time

You do not need to understand Gmail, databases, and AI APIs to follow the main
program. Start with its actions. Open a lower-level file only when you want to
understand one of those actions.

## First: follow the story

1. Read [`app.py`](../email_responder/app.py). `main()` chooses between resetting
   the cutoff, trying a sample email, and running the inbox. The short functions
   below it describe those three choices.
2. Read [`responder.py`](../email_responder/responder.py). `process_email()` handles
   one email: claim it, create a draft, send the reply, and save the outcome.
   A claim is permission from the database to process that particular message.
3. Read [`drafting.py`](../email_responder/drafting.py). `create_draft()` finds
   relevant pages, builds writing instructions, and asks the writer for a reply.
   `find_relevant_pages()` breaks the question into pieces and finds matching pages.
4. Read [`inbox.py`](../email_responder/inbox.py). It repeats the single-email story
   for unread messages, and optionally repeats the inbox check on a timer.

At this point you have followed the entire application. None of these workflows
unpacks a web response or contains a database query.

## Next: understand the building blocks

| If you are curious about… | Read this file |
| --- | --- |
| The fields in an email, a page, or a draft | [`models.py`](../email_responder/models.py) |
| How the real services are connected together | [`setup.py`](../email_responder/setup.py) |
| Instructions given to the reply writer | [`prompt.py`](../email_responder/prompt.py) |
| Available settings and defaults | [`config.py`](../email_responder/config.py) |
| Converting environment variables into settings | [`environment.py`](../email_responder/environment.py) |
| Command-line flags and console logs | [`cli.py`](../email_responder/cli.py) |
| Converting a parsed message into our email object | [`mail/normalize.py`](../email_responder/mail/normalize.py) |
| Rules for blocked senders | [`mail/filtering.py`](../email_responder/mail/filtering.py) |
| The synthetic email used by manual tests | [`mail/sample.py`](../email_responder/mail/sample.py) |
| Cleaning text and splitting it into pieces | [`text.py`](../email_responder/text.py) |

A `dataclass` in `models.py` is a small container with named fields. For example,
`draft.body` is the answer and `draft.pages` contains the pages used to write it.
Using names means you do not need to remember positions inside a tuple or the
field names returned by a particular service.

`setup.py` creates objects and hands them to the workflows. This is called
*dependency injection*: passing in a building block instead of creating it inside
the function that uses it. There is no framework or registration system to learn.
The tests pass in stand-ins using exactly the same constructors.

## Last: inspect one service in detail

Each adapter translates a service's request and response formats into the simple
objects used by the workflow. Keep that translation inside its own adapter.

| Service | Public operations | Implementation details |
| --- | --- | --- |
| Gmail | [`services/gmail.py`](../email_responder/services/gmail.py) | [`imap.py`](../email_responder/services/imap.py) reads messages and flags; [`smtp.py`](../email_responder/services/smtp.py) builds and sends replies |
| OpenAI | [`services/openai.py`](../email_responder/services/openai.py) | Orders embedding results and extracts the reply body from SDK responses |
| Wiki.js | [`services/wiki.py`](../email_responder/services/wiki.py) | Sends GraphQL requests, checks errors, and extracts page content |
| PostgreSQL | [`services/database.py`](../email_responder/services/database.py) | [`storage/claims.py`](../email_responder/storage/claims.py), [`search.py`](../email_responder/storage/search.py), and [`history.py`](../email_responder/storage/history.py) each implement one kind of operation |

The SQL itself is in [`storage/queries.py`](../email_responder/storage/queries.py).
Email character sets and multipart bodies are in
[`mail/parsing.py`](../email_responder/mail/parsing.py). The old workflow's message
hash arithmetic is in [`mail/identity.py`](../email_responder/mail/identity.py).
These are details you can leave until you need them.

The other tools use n8n. Their visual nodes already describe the workflow;
[`workflow_sources/README.md`](../workflow_sources/README.md) explains how to read
the scripts behind each node without navigating exported JSON.
The files in `schema/` and `compose.yaml` describe database structure and service
configuration. They are separate from the application workflows.

## Behavior to preserve when making changes

- Claim before drafting or sending. The unique database key prevents concurrent
  workers and later runs from sending a second reply to the same message.
- Old and blocked mail is recorded but never reaches the writer or sender. Mail
  from the responder's own address is ignored during normalization.
- Draft-only mode may retrieve knowledge and call OpenAI. It never claims a
  message, writes reply history, sends mail, or changes inbox flags.
- Fetching uses `BODY.PEEK[]`, which leaves a message unread. After handling it,
  the inbox runner marks it read, including when processing fails. This is the
  existing policy, not an automatic retry system.
- A failed send retains its draft for inspection. If sending succeeds but saving
  history fails, the existing claim still prevents an automatic second send;
  someone must inspect that outcome before deciding what to do next.
- Page retrieval selects distinct pages across all email chunks. Fewer than K
  pages is fine; an empty knowledge base is an error.

## Keep the next change approachable

Give each file one clear job. Put the main action before its supporting helpers.
Use a short function with a concrete name for each step that has a meaningful
purpose. Add a docstring and a one-line usage example to every function or class.
Explain non-obvious decisions in comments, especially behavior that protects
against duplicate sends or maintains compatibility with existing records.

When a workflow starts inspecting nested API dictionaries, move that translation
into the appropriate service adapter. When one file starts explaining several
unrelated topics, split it by responsibility. Avoid creating a new abstraction
when a straightforward function will do.

The tests follow these same boundaries: responder, drafting, inbox, configuration,
mail handling, web services, storage, and workflow exports. Run the commands in
the [main README](../README.md#reading-and-changing-the-code) after changing code.
The automated checks are offline; they do not prove live credentials or running
service versions are configured correctly.
