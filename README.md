# t3code-message-parser

A small command-line prototype for going back through my chats in a cleaner way.

The goal is to export selected T3 Code threads into Markdown so I can:

- trace how an app or feature developed over time
- feed the exported context into a long-context LLM like `NotebookLM`
- review, search, and parse the conversation history later

## What’s in the repo

- `thread_parser.py` - main CLI that reads the local T3 SQLite database and exports threads
- `thread-parser.cmd` - Windows wrapper for running the script more easily
- `thread-exports/` - exported Markdown files
- `problem.md` - original problem statement for the prototype
- `system.md` - notes about the approach and system behavior
- `pressure.md` - extra design notes and constraints

## How it works

The script looks for the matching T3 project based on the current directory or Git worktree, shows the available threads, lets you pick one or more, and writes a Markdown export.

## Run it

From the project folder:

```powershell
python thread_parser.py
```

Or on Windows:

```powershell
thread-parser.cmd
```

Optional flags:

- `--db` to point at a different T3 SQLite database
- `--out` to choose a different export directory
- `--wd` to match a different working directory

Default database path:

```text
%USERPROFILE%\.t3\userdata\state.sqlite
```

## Output

Exports are written as Markdown files into `thread-exports/` by default.
