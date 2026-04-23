# T3 Chat Thread Exporter

- Project: t3-message-parser
- Workspace: `C:\Users\super\Documents\dev\t3-message-parser`
- Project ID: `2f9d3d03-b682-4c00-881b-f09cf6e54e80`
- Thread ID: `90a120a9-12cd-4928-aef8-61061594cb0b`
- Thread created: `2026-04-23T12:17:34.500Z`
- Thread updated: `2026-04-23T12:30:02.711Z`
- Messages exported: 10

## 1. User

_Created: `2026-04-23T12:23:42.032Z`_

I want to make a "thread-parser" for my t3 chats (UI on top of codex) projects.
It should basically just take the threads from the projects, from a thread title I pass it. Then read/query the sql of where the info is stored, and then export the messages in a .md format (parsing the user, and assistant messages)
The sqlite db is here: "C:\Users\super\.t3\userdata\state.sqlite"
 - Before writing the script, take a look at it and tell me what, if anything you can interpret from the db tables, and references for this task. And also what all queries will you use to construct the final output
So basically, inputs of the project name (maybe you can even do a SELECT and give me the options before hand, on program start), then FROM which thread title (maybe another SELECT can be done)

## 2. Assistant

_Created: `2026-04-23T12:23:56.888Z`_

I’ll inspect the SQLite schema and sample rows first, then I’ll report the table relationships and the exact queries I’d use before writing any script. I’ll also use the local coding-guidelines skill because this is a small tool where the shape of the DB should drive the implementation.

## 3. Assistant

_Created: `2026-04-23T12:24:08.452Z`_

Using `karpathy-guidelines` for this turn: I’m keeping this to DB inspection and a concrete query plan first, with no script edits yet. Next I’m checking what SQLite tooling is available, then I’ll query the DB read-only.

## 4. Assistant

_Created: `2026-04-23T12:24:14.547Z`_

`sqlite3` CLI isn’t on PATH, so I’m using Python’s built-in SQLite library in read-only mode. I’ll avoid dumping full message bodies and focus on schema, counts, keys, and short title samples.

## 5. Assistant

_Created: `2026-04-23T12:24:23.123Z`_

The first schema pass shows the useful surface is projection tables, not raw event payloads: `projection_projects`, `projection_threads`, `projection_turns`, and `projection_thread_messages`. I’m doing a second pass now for row counts, indexes/foreign keys, and enough sample metadata to confirm ordering and relationships.

## 6. Assistant

_Created: `2026-04-23T12:24:45.475Z`_

One important pattern is already visible: assistant output is stored as multiple assistant message rows per turn, while user prompts are separate rows with `turn_id = NULL`. I’m checking whether `projection_turns` links those rows cleanly and whether `created_at` ordering is enough for the Markdown export.

## 7. Assistant

_Created: `2026-04-23T12:26:05.118Z`_

I inspected `C:\Users\super\.t3\userdata\state.sqlite` read-only. The export can be built cleanly from the projection tables; no need to parse raw event payloads.

**Useful Tables**

`projection_projects`
- Project list.
- Key fields: `project_id`, `title`, `workspace_root`, `deleted_at`.
- There are 13 projects, 8 active/non-deleted.

`projection_threads`
- Threads per project.
- Key fields: `thread_id`, `project_id`, `title`, `created_at`, `updated_at`, `deleted_at`, `archived_at`, `model_selection_json`.
- `project_id` implicitly references `projection_projects.project_id`.

`projection_thread_messages`
- Main export source.
- Key fields: `message_id`, `thread_id`, `turn_id`, `role`, `text`, `created_at`, `is_streaming`, `attachments_json`.
- Roles are only `user` and `assistant`.
- User messages usually have `turn_id = NULL`.
- Assistant messages have `turn_id`.
- Assistant output is split into multiple rows per turn: progress/status messages plus final answer.

`projection_turns`
- Useful for grouping user prompt -> assistant response.
- `pending_message_id` points to the user message.
- `assistant_message_id` points to the final assistant message for that turn.
- This is important if you want “final-answer only” instead of the full T3 transcript.

Other related but probably optional:
- `projection_thread_activities`: tool/status/activity events. Not needed for user/assistant Markdown unless you want tool logs.
- `projection_thread_proposed_plans`: plan markdown rows, optional.
- `projection_thread_sessions`: provider/session metadata.
- `orchestration_events`: raw event store. Since projections already contain the messages, I would not use it for v1.

There are no declared SQLite foreign keys, but the references are clear by convention.

**Project Picker Query**

```sql
SELECT
  p.project_id,
  p.title,
  p.workspace_root,
  COUNT(t.thread_id) AS total_threads,
  SUM(CASE WHEN t.thread_id IS NOT NULL AND t.deleted_at IS NULL THEN 1 ELSE 0 END) AS active_threads,
  SUM(CASE WHEN t.thread_id IS NOT NULL AND t.deleted_at IS NULL AND t.archived_at IS NULL THEN 1 ELSE 0 END) AS unarchived_threads,
  MAX(t.updated_at) AS latest_thread_updated_at
FROM projection_projects p
LEFT JOIN projection_threads t ON t.project_id = p.project_id
WHERE p.deleted_at IS NULL
GROUP BY p.project_id
ORDER BY COALESCE(latest_thread_updated_at, p.updated_at) DESC, p.title;
```

**Thread Picker Query**

After selecting a project:

```sql
SELECT
  t.thread_id,
  t.title,
  t.created_at,
  t.updated_at,
  t.archived_at,
  COUNT(m.message_id) AS message_count,
  SUM(CASE WHEN m.role = 'user' THEN 1 ELSE 0 END) AS user_message_count,
  SUM(CASE WHEN m.role = 'assistant' THEN 1 ELSE 0 END) AS assistant_message_count
FROM projection_threads t
LEFT JOIN projection_thread_messages m ON m.thread_id = t.thread_id
WHERE t.project_id = ?
  AND t.deleted_at IS NULL
GROUP BY t.thread_id
ORDER BY t.updated_at DESC, t.created_at DESC;
```

**Resolve By Thread Title**

```sql
SELECT
  t.thread_id,
  t.title,
  t.created_at,
  t.updated_at,
  t.archived_at
FROM projection_threads t
WHERE t.project_id = ?
  AND t.deleted_at IS NULL
  AND t.title = ?
ORDER BY t.updated_at DESC;
```

If multiple rows come back, the script should ask the user to choose by index/thread id.

**Full Transcript Export Query**

This preserves exactly what T3 shows as user/assistant messages, including assistant progress updates:

```sql
SELECT
  m.message_id,
  m.thread_id,
  m.turn_id,
  m.role,
  m.text,
  m.created_at,
  m.updated_at,
  m.attachments_json
FROM projection_thread_messages m
WHERE m.thread_id = ?
  AND m.is_streaming = 0
ORDER BY m.created_at ASC, m.message_id ASC;
```

**Final-Answer-Only Export Query**

This exports each user prompt plus only the final assistant message for the turn:

```sql
SELECT
  u.message_id AS user_message_id,
  u.text AS user_text,
  u.created_at AS user_created_at,
  a.message_id AS assistant_message_id,
  a.text AS assistant_text,
  a.created_at AS assistant_created_at,
  tr.turn_id,
  tr.state
FROM projection_turns tr
JOIN projection_thread_messages u
  ON u.message_id = tr.pending_message_id
LEFT JOIN projection_thread_messages a
  ON a.message_id = tr.assistant_message_id
WHERE tr.thread_id = ?
  AND tr.state = 'completed'
ORDER BY tr.requested_at ASC, tr.row_id ASC;
```

My recommendation for the script: default to full transcript, and add a `--final-only` flag later if you want cleaner summaries. Full transcript is the safest representation of what the T3 UI stored.

## 8. User

_Created: `2026-04-23T12:29:13.256Z`_

Ok, do a test run of this and get the convo of this thread from project "t3-message-parser". The thread's title is "T3 Chat Thread Exporter"
(You can ignore the tool calls, and results)

## 9. Assistant

_Created: `2026-04-23T12:29:26.929Z`_

I’ll run the same selection path the eventual tool would use: resolve the active project by title, resolve the thread by exact title, then pull only `projection_thread_messages` so tool calls/results are excluded. After that I’ll either summarize the export or save a Markdown test artifact if the transcript is long.

## 10. Assistant

_Created: `2026-04-23T12:29:46.115Z`_

The DB resolves cleanly to one active project and one active thread. I’m writing a Markdown test export now from those 9 stored message rows, using only message rows and not the activity/tool-result tables.
