#!/usr/bin/env python
import argparse
import datetime as dt
import re
import sqlite3
import subprocess
from pathlib import Path

DEFAULT_DB = Path.home() / ".t3" / "userdata" / "state.sqlite"


def run_git(args, cwd):
    # Control flow: Git is only used to expand path candidates for worktrees.
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except FileNotFoundError:
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def norm_path(value):
    # Data flow: every filesystem path is normalized before prefix comparison.
    return str(Path(value).expanduser().resolve()).casefold()


def is_same_or_child(path, parent):
    path_norm = norm_path(path)
    parent_norm = norm_path(parent)
    return path_norm == parent_norm or path_norm.startswith(parent_norm.rstrip("\\/") + "\\")


def git_path_candidates(cwd):
    # Control flow: start with cwd/ancestors, then add Git toplevel and all worktrees.
    candidates = [cwd, *cwd.parents]

    top = run_git(["rev-parse", "--show-toplevel"], cwd)
    if top:
        candidates.append(Path(top))

    worktree_list = run_git(["worktree", "list", "--porcelain"], cwd)
    if worktree_list:
        for line in worktree_list.splitlines():
            if line.startswith("worktree "):
                candidates.append(Path(line.removeprefix("worktree ").strip()))

    unique = []
    seen = set()
    for candidate in candidates:
        try:
            key = norm_path(candidate)
        except OSError:
            continue
        if key not in seen:
            seen.add(key)
            unique.append(Path(candidate))
    return unique


def connect_readonly(db_path):
    if not db_path.exists():
        raise SystemExit(f"SQLite DB not found: {db_path}")
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


def load_projects(conn):
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT project_id, title, workspace_root, created_at, updated_at
        FROM projection_projects
        WHERE deleted_at IS NULL
        ORDER BY updated_at DESC, title ASC
        """
    ).fetchall()


def find_project_for_cwd(projects, cwd):
    # Data flow: current directory and Git worktree roots are matched to T3 workspace roots.
    candidates = git_path_candidates(cwd)
    matches = []
    for project in projects:
        root = Path(project["workspace_root"])
        for candidate in candidates:
            if is_same_or_child(candidate, root):
                matches.append((len(norm_path(root)), project, candidate))
                break
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches, candidates


def format_date(value):
    if not value:
        return "-"
    cleaned = value.replace("T", " ").replace("Z", "")
    return cleaned[:19]


def clean_text(value):
    return re.sub(r"\s+", " ", value or "").strip()


def snippet(value, max_chars=220):
    # Data flow: message text becomes a compact preview for the selection screen.
    text = clean_text(value)
    if not text:
        return "-"

    sentences = re.split(r"(?<=[.!?])\s+", text)
    preview = " ".join(sentences[:2]).strip()
    if not preview:
        preview = text
    if len(preview) > max_chars:
        preview = preview[: max_chars - 1].rstrip() + "..."
    return preview


def load_threads(conn, project_id):
    # Data flow: each thread row includes correlated previews from its latest user/assistant messages.
    return conn.execute(
        """
        SELECT
          t.thread_id,
          t.title,
          t.created_at,
          t.updated_at,
          t.archived_at,
          (
            SELECT m.text
            FROM projection_thread_messages m
            WHERE m.thread_id = t.thread_id
              AND m.role = 'user'
              AND m.is_streaming = 0
            ORDER BY m.created_at DESC, m.message_id DESC
            LIMIT 1
          ) AS last_user_text,
          (
            SELECT m.created_at
            FROM projection_thread_messages m
            WHERE m.thread_id = t.thread_id
              AND m.role = 'user'
              AND m.is_streaming = 0
            ORDER BY m.created_at DESC, m.message_id DESC
            LIMIT 1
          ) AS last_user_at,
          (
            SELECT m.text
            FROM projection_thread_messages m
            WHERE m.thread_id = t.thread_id
              AND m.role = 'assistant'
              AND m.is_streaming = 0
            ORDER BY m.created_at DESC, m.message_id DESC
            LIMIT 1
          ) AS last_assistant_text,
          (
            SELECT m.created_at
            FROM projection_thread_messages m
            WHERE m.thread_id = t.thread_id
              AND m.role = 'assistant'
              AND m.is_streaming = 0
            ORDER BY m.created_at DESC, m.message_id DESC
            LIMIT 1
          ) AS last_assistant_at,
          (
            SELECT COUNT(*)
            FROM projection_thread_messages m
            WHERE m.thread_id = t.thread_id
              AND m.is_streaming = 0
          ) AS message_count
        FROM projection_threads t
        WHERE t.project_id = ?
          AND t.deleted_at IS NULL
        ORDER BY t.updated_at DESC, t.created_at DESC
        """,
        (project_id,),
    ).fetchall()


def print_thread_list(threads):
    print()
    print(f"Threads ({len(threads)}):")
    print("Selection examples: 3  |  1,4,9  |  2-10,!5,!7  |  all")
    print()
    for index, thread in enumerate(threads, start=1):
        archived = " archived" if thread["archived_at"] else ""
        print(f"[{index}] {thread['title']}{archived}")
        print(
            f"    created {format_date(thread['created_at'])} | "
            f"updated {format_date(thread['updated_at'])} | "
            f"messages {thread['message_count']}"
        )
        print(
            f"    user      {format_date(thread['last_user_at'])}: "
            f"{snippet(thread['last_user_text'])}"
        )
        print(
            f"    assistant {format_date(thread['last_assistant_at'])}: "
            f"{snippet(thread['last_assistant_text'])}"
        )
        print()


def parse_selection(raw, count):
    # Control flow: build include/exclude sets, then return selected indexes in displayed order.
    text = raw.strip().lower()
    if not text:
        raise ValueError("No selection entered.")
    if text == "all":
        return list(range(1, count + 1))

    includes = set()
    excludes = set()
    for token in [part.strip() for part in text.split(",") if part.strip()]:
        target = excludes if token.startswith("!") else includes
        if token.startswith("!"):
            token = token[1:].strip()
        if not token:
            raise ValueError("Empty exclusion token.")

        if "-" in token:
            left, right = token.split("-", 1)
            if not left.isdigit() or not right.isdigit():
                raise ValueError(f"Invalid range: {token}")
            start = int(left)
            end = int(right)
            if start > end:
                start, end = end, start
            target.update(range(start, end + 1))
        else:
            if not token.isdigit():
                raise ValueError(f"Invalid selection token: {token}")
            target.add(int(token))

    if not includes:
        raise ValueError("Selection must include at least one thread.")

    selected = [index for index in range(1, count + 1) if index in includes and index not in excludes]
    invalid = sorted((includes | excludes) - set(range(1, count + 1)))
    if invalid:
        raise ValueError(f"Selection out of range: {', '.join(str(item) for item in invalid)}")
    if not selected:
        raise ValueError("Selection excluded every included thread.")
    return selected


def load_messages(conn, thread_id):
    return conn.execute(
        """
        SELECT message_id, role, text, created_at
        FROM projection_thread_messages
        WHERE thread_id = ?
          AND is_streaming = 0
          AND role IN ('user', 'assistant')
        ORDER BY created_at ASC, message_id ASC
        """,
        (thread_id,),
    ).fetchall()


def slugify(value):
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "thread-export"


def build_markdown(project, selected_threads, messages_by_thread):
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        f"# T3 Thread Export: {project['title']}",
        "",
        f"- Exported at: `{now}`",
        f"- Project: `{project['title']}`",
        f"- Workspace: `{project['workspace_root']}`",
        f"- Project ID: `{project['project_id']}`",
        f"- Threads exported: `{len(selected_threads)}`",
        "",
    ]

    for thread_number, thread in enumerate(selected_threads, start=1):
        messages = messages_by_thread[thread["thread_id"]]
        lines.extend(
            [
                f"## Thread {thread_number}: {thread['title']}",
                "",
                f"- Thread ID: `{thread['thread_id']}`",
                f"- Created: `{thread['created_at']}`",
                f"- Updated: `{thread['updated_at']}`",
                f"- Messages: `{len(messages)}`",
                "",
            ]
        )

        for message_number, message in enumerate(messages, start=1):
            role = message["role"].title()
            lines.extend(
                [
                    f"### {message_number}. {role}",
                    "",
                    f"_Created: `{message['created_at']}`_",
                    "",
                    message["text"].rstrip(),
                    "",
                ]
            )

    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Ugly prototype: export T3 project threads from the local SQLite state DB."
    )
    parser.add_argument("--db", default=str(DEFAULT_DB), help=f"SQLite DB path. Default: {DEFAULT_DB}")
    parser.add_argument("--out", default=None, help="Output directory. Default: ./thread-exports")
    parser.add_argument("--selection", default=None, help="Non-interactive selection, e.g. 2-10,!5,!7")
    args = parser.parse_args()

    cwd = Path.cwd()
    conn = connect_readonly(Path(args.db))
    projects = load_projects(conn)
    matches, candidates = find_project_for_cwd(projects, cwd)

    if not matches:
        print("No active T3 project matched the current directory or Git worktree roots.")
        print()
        print("Path candidates checked:")
        for candidate in candidates:
            print(f"- {candidate}")
        return 1

    project = matches[0][1]
    matched_by = matches[0][2]
    print(f"Matched project: {project['title']}")
    print(f"Workspace: {project['workspace_root']}")
    print(f"Matched by: {matched_by}")

    threads = load_threads(conn, project["project_id"])
    if not threads:
        print("This project has no active threads.")
        return 1

    print_thread_list(threads)

    while True:
        raw = args.selection if args.selection is not None else input("Select threads to export: ")
        try:
            selected_indexes = parse_selection(raw, len(threads))
            break
        except ValueError as error:
            print(f"Selection error: {error}")
            if args.selection is not None:
                return 1

    selected_threads = [threads[index - 1] for index in selected_indexes]
    messages_by_thread = {}
    for thread in selected_threads:
        messages_by_thread[thread["thread_id"]] = load_messages(conn, thread["thread_id"])

    out_dir = Path(args.out) if args.out else cwd / "thread-exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    out_path = out_dir / f"{slugify(project['title'])}-threads-{stamp}.md"
    out_path.write_text(build_markdown(project, selected_threads, messages_by_thread), encoding="utf-8")

    print()
    print(f"Exported {len(selected_threads)} thread(s) to:")
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
