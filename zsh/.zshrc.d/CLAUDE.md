# .zshrc.d/

Per-feature snippets sourced after the main `.zshrc`. Loaded automatically by the `mattmc3/zshrc.d` antidote plugin.

Drop a `.zsh` file here to add behavior without touching `.zshrc`. Each file should:
1. Be self-contained (its own PATH/fpath setup, its own aliases/functions)
2. Be safe to source multiple times

## Current files

- `worktree.zsh` — adds `~/.config/zsh/completions` to `$fpath` (must happen before `compinit`), puts `~/.local/bin` on `$PATH`, defines `alias wt=worktree-tmux`
