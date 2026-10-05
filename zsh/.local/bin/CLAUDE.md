# bin/

User scripts that land in `~/.local/bin/` and get added to `$PATH` from `.zshrc.d/worktree.zsh`.

## Scripts

### `worktree-tmux` (alias: `wt`)
Manages git worktree + tmux session lifecycle:
- If a worktree for the branch exists: switch/attach to its session (creating one if needed and starting nvim)
- Otherwise: create the worktree at `~/worktrees/<repo>/<branch>` branched from `main` (or `master`), open a tmux session, launch nvim

On **creation only**, it looks for `~/.config/worktree-setup/<repo>.sh` and, if present, runs it
with `setsid` in the new worktree, detached, with output to
`~/.cache/worktree-setup/<repo>-<session>.log`. It is fired before the tmux session is created and
never waited on, so nvim opens at the same speed whether a hook exists or not (~35ms either way).
The log's last line is `=== <date>: exit <rc>`, which is the only way to tell a finished hook from a
killed one — note the `rc=$?` capture in the runner, because the `$(date)` in that same `echo`
would otherwise clobber the status and report success for every failure.

The hooks themselves are deliberately **not** in this package: a repo-specific one names a repo, and
this package is public. They live untracked under `~/.config/worktree-setup/`, or in a work-private
stow package if they ever want tracking.

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

### `with-performance`
Runs a command with the CPU power profile pinned to `performance`, restoring the previous profile on
exit -- including Ctrl-C, via a trap. For build/test sweeps: an eleven-commit `git rebase --exec`
verification of a Go branch went 44s to 32s.

`powerprofilesctl` is what makes this possible without root: power-profiles-daemon accepts the
change from the active session's user over polkit, where writing `scaling_governor` in sysfs would
not. Under active `intel_pstate` the governor still reads as `powersave` -- what actually moves is
the energy-performance preference. It is a system-wide setting, so a long sweep affects everything
else running, and the daemon may refuse `performance` on battery.

### `screenshot-to-file`
Reads PNG from clipboard, saves to `~/Pictures/screenshots/screenshot-<timestamp>.png`, replaces the clipboard content with the filepath, and shows a `notify-send` toast. Useful for pasting screenshot **paths** into tools that accept file refs but not raw image data.

Requires: `xclip`, `notify-send`.

`README.md` in this directory has more detail (not tracked as a stowed config — it ends up at `~/.local/bin/README.md` after stow, which is harmless).
