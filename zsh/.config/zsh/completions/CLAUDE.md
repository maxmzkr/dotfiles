# completions/

Custom zsh completion functions. Files must be named `_<command>` and start with `#compdef <command>`.

Added to `$fpath` from `.zshrc.d/worktree.zsh` before `compinit`, so any file dropped here is picked up automatically on next shell start.

Current files:
- `_worktree-tmux` — completes worktree branch names by parsing `git worktree list --porcelain`. Also bound to the `wt` alias via `#compdef worktree-tmux wt`.
