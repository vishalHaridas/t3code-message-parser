## CURRENT

Actual behavior:
- `thread_parser.py` is a no-dependency Python CLI.
- `thread-parser.cmd` runs the Python CLI from Windows command lines.
- The CLI opens `C:\Users\super\.t3\userdata\state.sqlite` read-only unless `--db` is provided.
- It finds the active T3 project by comparing the current directory, or `--wd` when provided, parent directories, Git top-level path, and `git worktree list --porcelain` worktree roots against active `projection_projects.workspace_root` values.
- It lists active project threads with title, recorded branch, worktree presence/path, readable created/updated dates, message count, and a short head/tail latest-user snippet. Each row is width-bounded and separated to avoid terminal wrapping making rows look duplicated.
- It prompts interactively for text selection syntax: `3`, `1,4,9`, `2-10,!5,!7`, or `all`.
- It exports selected threads, in displayed order, to `C:\Users\super\.t3\userdata\exports\<date>-<project>-threads-parsed.md` by default.
- It opens the export directory in Explorer after writing the file.
- Exported content comes only from `projection_thread_messages` roles `user` and `assistant`; activity/tool rows are ignored.

Execution trace:
- Entry point: `thread-parser.cmd` -> `python thread_parser.py`.
- Project lookup: current path candidates -> active project rows -> longest workspace path match.
- Thread lookup: selected project id -> active thread rows with correlated latest-message previews.
- Selection: prompt text -> include/exclude indexes -> selected thread rows.
- Export: selected thread ids -> ordered message rows -> Markdown file.

## RECENT

- Added `--wd` for matching another directory and removed `--selection`; selection is now prompt-only.
- Simplified thread list display by removing assistant preview, formatting dates like `21 Apr 2026, 11:25`, shortening user snippets to head/tail previews, and moving branch/worktree info onto the title line.
- Added terminal-width bounded thread rows with separators after a visual wrap issue in longer project lists.
- Changed default export directory to the T3 userdata exports folder and filename format to `<date>-<project>-threads-parsed.md`.
- First end-to-end prototype implemented.

## ARCHIVE
