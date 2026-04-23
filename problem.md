## CURRENT

Problem statement:
- Build an ugly command-line prototype that exports selected T3 project threads from `C:\Users\super\.t3\userdata\state.sqlite` into Markdown.
- The command should be runnable from inside a project directory, infer the matching T3 project from the current path, ask which threads to export, then write user/assistant messages to `.md`.

Scope boundaries:
- Include only user and assistant messages from `projection_thread_messages`.
- Ignore tool calls/results/activity rows.
- Match worktree/subdirectory paths back to the parent T3 project, not only exact `workspace_root` matches.
- For the prototype, prefer direct SQLite queries and explicit control flow over abstractions.

Minimal data model:
- Project: `project_id`, `title`, `workspace_root`, `deleted_at`.
- Thread: `thread_id`, `project_id`, `title`, `created_at`, `updated_at`, `deleted_at`, `archived_at`.
- Message: `message_id`, `thread_id`, `role`, `text`, `created_at`, `is_streaming`.
- Thread selection: ordered set of selected thread indexes from the presented list; ranges are only a shorthand and can have exclusions.
- Export: generated Markdown file containing selected thread metadata and ordered messages grouped by thread.

First implementation target:
- One CLI file that reads the current working directory, finds the best active project by path prefix, lists threads with title/dates/last user and assistant snippets, accepts a compact text selection such as `2-10,!5,!7`, and writes a Markdown export.

## RECENT

- Selection model changed from one thread to multiple selected threads; first ugly input should be text ranges with exclusions before considering a TUI.
- Initial prototype brief captured before implementation.

## ARCHIVE
