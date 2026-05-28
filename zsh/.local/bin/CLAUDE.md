# bin/

User scripts that land in `~/.local/bin/` and get added to `$PATH` from `.zshrc.d/worktree.zsh`.

## Scripts

### `worktree-tmux` (alias: `wt`)
Manages git worktree + tmux session lifecycle:
- If a worktree for the branch exists: switch/attach to its session (creating one if needed and starting nvim)
- Otherwise: create the worktree at `~/worktrees/<repo>/<branch>` branched from `main` (or `master`), open a tmux session, launch nvim

Tab completion comes from `../../.config/zsh/completions/_worktree-tmux`.

### `screenshot-to-file`
Reads PNG from clipboard, saves to `~/Pictures/screenshots/screenshot-<timestamp>.png`, replaces the clipboard content with the filepath, and shows a `notify-send` toast. Useful for pasting screenshot **paths** into tools that accept file refs but not raw image data.

Requires: `xclip`, `notify-send`.

`README.md` in this directory has more detail (not tracked as a stowed config — it ends up at `~/.local/bin/README.md` after stow, which is harmless).
