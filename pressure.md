## CURRENT

Pressure points:
- Selection UX is intentionally ugly. Come back to this after validating export behavior; likely candidates are pagination, fuzzy filtering, or a spacebar TUI.
- Long thread lists currently print all rows at once.
- Snippet extraction is naive sentence splitting and may cut code-heavy messages awkwardly.
- Worktree association depends on `git worktree list --porcelain`; non-Git copied worktrees will only match by path prefix.
- The export includes all assistant message rows, including status/progress updates, because those are stored as assistant messages.

## RECENT

- Added reminder to revisit selection UX after the first working prototype.

## ARCHIVE
