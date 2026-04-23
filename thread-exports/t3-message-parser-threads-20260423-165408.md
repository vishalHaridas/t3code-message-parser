# T3 Thread Export: t3-message-parser

- Exported at: `2026-04-23 16:54:08`
- Project: `t3-message-parser`
- Workspace: `C:\Users\super\Documents\dev\t3-message-parser`
- Project ID: `2f9d3d03-b682-4c00-881b-f09cf6e54e80`
- Threads exported: `1`

## Thread 1: T3 Chat Thread Exporter

- Thread ID: `90a120a9-12cd-4928-aef8-61061594cb0b`
- Created: `2026-04-23T12:17:34.500Z`
- Updated: `2026-04-23T12:54:07.793Z`
- Messages: `25`

### 1. User

_Created: `2026-04-23T12:23:42.032Z`_

I want to make a "thread-parser" for my t3 chats (UI on top of codex) projects.
It should basically just take the threads from the projects, from a thread title I pass it. Then read/query the sql of where the info is stored, and then export the messages in a .md format (parsing the user, and assistant messages)
The sqlite db is here: "C:\Users\super\.t3\userdata\state.sqlite"
 - Before writing the script, take a look at it and tell me what, if anything you can interpret from the db tables, and references for this task. And also what all queries will you use to construct the final output
So basically, inputs of the project name (maybe you can even do a SELECT and give me the options before hand, on program start), then FROM which thread title (maybe another SELECT can be done)

### 2. Assistant

_Created: `2026-04-23T12:23:56.888Z`_

I’ll inspect the SQLite schema and sample rows first, then I’ll report the table relationships and the exact queries I’d use before writing any script. I’ll also use the local coding-guidelines skill because this is a small tool where the shape of the DB should drive the implementation.

### 3. Assistant

_Created: `2026-04-23T12:24:08.452Z`_

Using `karpathy-guidelines` for this turn: I’m keeping this to DB inspection and a concrete query plan first, with no script edits yet. Next I’m checking what SQLite tooling is available, then I’ll query the DB read-only.

### 4. Assistant

_Created: `2026-04-23T12:24:14.547Z`_

`sqlite3` CLI isn’t on PATH, so I’m using Python’s built-in SQLite library in read-only mode. I’ll avoid dumping full message bodies and focus on schema, counts, keys, and short title samples.

### 5. Assistant

_Created: `2026-04-23T12:24:23.123Z`_

The first schema pass shows the useful surface is projection tables, not raw event payloads: `projection_projects`, `projection_threads`, `projection_turns`, and `projection_thread_messages`. I’m doing a second pass now for row counts, indexes/foreign keys, and enough sample metadata to confirm ordering and relationships.

### 6. Assistant

_Created: `2026-04-23T12:24:45.475Z`_

One important pattern is already visible: assistant output is stored as multiple assistant message rows per turn, while user prompts are separate rows with `turn_id = NULL`. I’m checking whether `projection_turns` links those rows cleanly and whether `created_at` ordering is enough for the Markdown export.

### 7. Assistant

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

### 8. User

_Created: `2026-04-23T12:29:13.256Z`_

Ok, do a test run of this and get the convo of this thread from project "t3-message-parser". The thread's title is "T3 Chat Thread Exporter"
(You can ignore the tool calls, and results)

### 9. Assistant

_Created: `2026-04-23T12:29:26.929Z`_

I’ll run the same selection path the eventual tool would use: resolve the active project by title, resolve the thread by exact title, then pull only `projection_thread_messages` so tool calls/results are excluded. After that I’ll either summarize the export or save a Markdown test artifact if the transcript is long.

### 10. Assistant

_Created: `2026-04-23T12:29:46.115Z`_

The DB resolves cleanly to one active project and one active thread. I’m writing a Markdown test export now from those 9 stored message rows, using only message rows and not the activity/tool-result tables.

### 11. Assistant

_Created: `2026-04-23T12:30:13.107Z`_

The export completed and grew from 9 to 10 rows because my status update itself was persisted into this same live thread while I was running the test. I’m doing one quick readback check on the generated Markdown structure before I report the path.

### 12. Assistant

_Created: `2026-04-23T12:30:19.595Z`_

Done. I created the test Markdown export here:

[exports/t3-message-parser__t3-chat-thread-exporter.md](C:/Users/super/Documents/dev/t3-message-parser/exports/t3-message-parser__t3-chat-thread-exporter.md)

It resolved:
- Project: `t3-message-parser`
- Thread: `T3 Chat Thread Exporter`
- Thread ID: `90a120a9-12cd-4928-aef8-61061594cb0b`
- Messages exported: `10`

I only used `projection_thread_messages`, so SQLite activity/tool-call/tool-result rows were excluded. Since this is the live thread, my status updates during the test were also persisted and included as assistant messages.

### 13. User

_Created: `2026-04-23T12:41:12.972Z`_

hmm.. i am wondering the best use of this would be from a cmd line. so something i can have stored in my path
then when I open the command line to the project I am working on's dir, and run this command - it could do a lookup on the db of the path to the project (I am assuming this would work for git work trees also). 
(Clarifications - if it is done on a work tree, it should find the project it is associated to - not just the threads of that worktree)
Then it should just do a select and ask me from which thread do I want to export
When presenting the thread, show it's title, created date, updated date and last sent user message & assistant message (trimmed to a couple sentences) - present it nicely lol (for every thread "row"). 
The selection should just be a number from the list of the threads. (Expect the list can be long)

Right - let's start an ugly prototype of this

### 14. Assistant

_Created: `2026-04-23T12:41:19.046Z`_

Using `rapid-ugly-prototyping` for this turn because you explicitly want an ugly prototype. I’ll first read its workflow, then I’ll add a small CLI script in this repo that resolves the current directory to a T3 project and exports a selected thread.

### 15. Assistant

_Created: `2026-04-23T12:41:33.026Z`_

The skill forces a short Phase 1 before code. Your message already nails most of the intent, so I’m just capturing the minimal problem/data model in `problem.md` and then I’ll stop at the first implementation target.

### 16. Assistant

_Created: `2026-04-23T12:41:37.670Z`_

I’m adding only the prototype brief now: what the command should do, what is explicitly out of scope, and the small data model we just discovered from SQLite.

### 17. Assistant

_Created: `2026-04-23T12:41:46.703Z`_

Phase 1 is captured in [problem.md](C:\Users\super\Documents\dev\t3-message-parser\problem.md).

First implementation target is now explicit: one CLI file that infers the active T3 project from the current directory, lists matching project threads with useful snippets, accepts a numeric choice, and exports ordered user/assistant messages to Markdown.

Per the ugly-prototype workflow, I’m stopping here before implementation.

### 18. User

_Created: `2026-04-23T12:50:16.559Z`_

Hmm.. yeah, so the thread selected is a "from" - not just the thread. And now I think "from" and "to" is also needed. So would have to re-think the input method for how to take the range. I am assuming the range would not be completely inclusive also. Like if I select threads 2-10, maybe I don't want 5 & 7?
Then maybe a tui is needed where I can press spacebar to select each threads to include it into the array?

### 19. Assistant

_Created: `2026-04-23T12:50:24.173Z`_

Using `rapid-ugly-prototyping` again because we’re still shaping the prototype input model. I’ll update the prototype brief to reflect “export selected threads from a list,” then I’ll give you the simplest input method I’d build first versus when a TUI becomes worth it.

### 20. Assistant

_Created: `2026-04-23T12:50:29.631Z`_

The data model itself barely changes, but the selection model does: an export is now an ordered set of chosen threads, not a single chosen thread. I’m patching that into the prototype brief before choosing an input shape.

### 21. Assistant

_Created: `2026-04-23T12:50:45.896Z`_

Yes, the selected thread is really a `from` point only if your mental model is “export a range of adjacent history.” But your `2-10 except 5 and 7` example means the real model is:

`export = selected ordered set of threads`

So I would not build around `from`/`to` as the core concept. I’d build selection as a list of thread indexes.

For the ugly prototype, I’d avoid a TUI first and use a compact text selector:

```txt
Select threads: 2-10,!5,!7
```

Meaning:
- Include `2,3,4,5,6,7,8,9,10`
- Exclude `5`
- Exclude `7`
- Final selection: `2,3,4,6,8,9,10`

Also support simple forms:

```txt
3
1,4,9
2-10
2-10,!5,!7,14
all
```

A TUI with spacebar selection is probably the right polished version, but it adds terminal complexity before we’ve validated the export shape. For the first prototype, text selection is faster, scriptable, and easy to debug. The displayed list can still be nice and paginated-looking.

I updated [problem.md](C:\Users\super\Documents\dev\t3-message-parser\problem.md) with this revised model.

### 22. User

_Created: `2026-04-23T12:52:21.062Z`_

hmm, ok, let's just get this thing working from top to bottom, and then we will come back to the UX of the selection (Remember to come back)

### 23. Assistant

_Created: `2026-04-23T12:52:39.160Z`_

I’ll build the ugly end-to-end CLI now, keeping selection basic so we can revisit UX after the data flow works. First I’m checking the repo state and then I’ll add a direct Python script plus a Windows command shim.

### 24. Assistant

_Created: `2026-04-23T12:52:53.636Z`_

The repo only has `problem.md` and the earlier test export, so I can keep the prototype isolated. I’m making one no-dependency Python CLI and a `.cmd` wrapper; the script will use current directory plus Git worktree metadata to find the matching T3 project.

### 25. Assistant

_Created: `2026-04-23T12:54:06.483Z`_

The first pass is in place. I’m running it non-interactively against this repo now so the full path matching, thread list query, selection parser, and Markdown write all get exercised.
