# tmux

Stow package for tmux. Symlinks `~/.tmux.conf` into `$HOME`.

Highlights:
- **cgroup-per-window:** `default-command = systemd-run --user --scope /usr/bin/zsh` so each pane gets its own transient cgroup
- **Prefix:** `C-a` (not the default `C-b`)
- **vim-aware split nav:** `C-h/j/k/l` either move the tmux pane or pass the key through if vim is the foreground command
- **attention flags in `status-right`:** two per-session user options, each rendered for
  *every* session through `#{S:...}` so any session can see which others want you —
  `@cc_done` (`✓`, set from nvim when CodeCompanion finishes) and `@claude_waiting`
  (`✻`, set from Claude Code's `Stop`/`Notification` hooks in `~/.claude/settings.json`,
  cleared on `UserPromptSubmit`/`SessionStart`). `client-session-changed`
  clears only `@cc_done` — switching in means you saw it, whereas a Claude session keeps
  advertising until you actually reply.
- Solarized-light theme via `tmux-colors-solarized`
- TPM plugins: tpm, tmux-sensible, tmux-fzf, tmux-colors-solarized
- `prefix S` runs the tmux-fzf session picker
- mouse on, history 100000, vi copy-mode
- Splits/new-windows inherit `pane_current_path`

Plugins are installed via TPM (`~/.tmux/plugins/tpm`) — this repo doesn't vendor them.
