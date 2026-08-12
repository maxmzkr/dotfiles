# bin/

User scripts that land in `~/.local/bin/` and get added to `$PATH` from `.zshrc.d/worktree.zsh`.

## Scripts

### `worktree-tmux` (alias: `wt`)
Manages git worktree + tmux session lifecycle:
- If a worktree for the branch exists: switch/attach to its session (creating one if needed and starting nvim)
- Otherwise: create the worktree at `~/worktrees/<repo>/<branch>` branched from `main` (or `master`), open a tmux session, launch nvim

Tab completion comes from `../../.config/zsh/completions/_worktree-tmux`.

### `beats`
Switches the noise-control mode (`off` / `anc` / `transparency`, plus `cycle` and `status`) on Beats
Fit Pro / AirPods from Linux, where no vendor app exists. Speaks Apple's AAP protocol over its own
L2CAP channel (PSM 0x1001), which is independent of A2DP/HFP, so it doesn't interrupt playback and
needs no root — only that the device is paired and connected. Autodetects the device by Apple's
vendor id in its modalias; override with `--mac`.

The earbuds only send a state notification when the mode actually *changes*, so a no-op set is
short-circuited rather than waited on. `beats raw` dumps AAP packets for 30s if the protocol needs
poking at again.

### `screenshot-to-file`
Reads PNG from clipboard, saves to `~/Pictures/screenshots/screenshot-<timestamp>.png`, replaces the clipboard content with the filepath, and shows a `notify-send` toast. Useful for pasting screenshot **paths** into tools that accept file refs but not raw image data.

Requires: `xclip`, `notify-send`.

`README.md` in this directory has more detail (not tracked as a stowed config — it ends up at `~/.local/bin/README.md` after stow, which is harmless).
