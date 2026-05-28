# Worktree Management Scripts

Script to streamline git worktree workflows with tmux and nvim.

## Script

### `worktree-tmux` (alias: `wt`)
Intelligently manage git worktrees and tmux sessions.

**Usage:**
```bash
wt feature/my-branch
```

**Smart behavior:**
- If worktree exists with tmux session → switch to session
- If worktree exists without session → create session and open nvim
- If worktree doesn't exist → create worktree + session + open nvim

**Tab completion:** Press `<TAB>` to see all existing worktree branches

**Worktree location:** `~/worktrees/<repo>/<branch>`

## Installation

Managed via stow:
```bash
cd ~/dotfiles
stow -R zsh
```

This creates symlinks:
- `~/.local/bin/worktree-tmux` → script
- `~/.config/zsh/completions/_worktree-tmux` → completion
- `~/.zshrc.d/worktree.zsh` → config + alias
