# tmux

Stow package for tmux. Symlinks `~/.tmux.conf` into `$HOME`.

Highlights:
- **cgroup-per-window:** `default-command = systemd-run --user --scope /usr/bin/zsh` so each pane gets its own transient cgroup
- **Prefix:** `C-a` (not the default `C-b`)
- **vim-aware split nav:** `C-h/j/k/l` either move the tmux pane or pass the key through if vim is the foreground command
- **`@cc_done` in `status-right`:** a per-session flag (`✓`, set from nvim when
  CodeCompanion finishes), rendered for *every* session through `#{S:...}` so any
  session can see which others want you. `client-session-changed` clears it —
  switching in means you saw it.
- **Claude Code state** is not in the status line: its hooks set `@claude_state` on
  their pane and the kitty sidebar (`kitty/.config/kitty/claude_sidebar/`) shows it.
  The one piece that lives here is `client-session-changed` turning that session's
  `done` panes `idle`, so a green `✓` in the sidebar means finished and not yet seen.
- Solarized-light theme via `tmux-colors-solarized`
- TPM plugins: tpm, tmux-sensible, tmux-fzf, tmux-colors-solarized
- `prefix S` runs the tmux-fzf session picker
- mouse on, history 100000, vi copy-mode
- Splits/new-windows inherit `pane_current_path`

Plugins are installed via TPM (`~/.tmux/plugins/tpm`) — this repo doesn't vendor them.
