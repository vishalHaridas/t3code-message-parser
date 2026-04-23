## CURRENT

Actual behavior:
- `thread_parser.py` is a no-dependency Python CLI.
- `thread-parser.cmd` runs the Python CLI from Windows command lines.
- The CLI opens `C:\Users\super\.t3\userdata\state.sqlite` read-only unless `--db` is provided.
- It finds the active T3 project by comparing the current directory, parent directories, Git top-level path, and `git worktree list --porcelain` worktree roots against active `projection_projects.workspace_root` values.
- It lists active project threads with title, created date, updated date, message count, latest user snippet, and latest assistant snippet.
- It accepts text selection syntax: `3`, `1,4,9`, `2-10,!5,!7`, or `all`.
- It exports selected threads, in displayed order, to `./thread-exports/<project>-threads-<timestamp>.md`.
- Exported content comes only from `projection_thread_messages` roles `user` and `assistant`; activity/tool rows are ignored.

Execution trace:
- Entry point: `thread-parser.cmd` -> `python thread_parser.py`.
- Project lookup: current path candidates -> active project rows -> longest workspace path match.
- Thread lookup: selected project id -> active thread rows with correlated latest-message previews.
- Selection: prompt text -> include/exclude indexes -> selected thread rows.
- Export: selected thread ids -> ordered message rows -> Markdown file.

## RECENT

- First end-to-end prototype implemented and verified with `.\thread-parser.cmd --selection 1`.

## ARCHIVE
