# .zshrc.d/

Per-feature snippets sourced after the main `.zshrc`. Loaded automatically by the `mattmc3/zshrc.d` antidote plugin.

Drop a `.zsh` file here to add behavior without touching `.zshrc`. Each file should:
1. Be self-contained (its own PATH/fpath setup, its own aliases/functions)
2. Be safe to source multiple times

## Current files

- `bitwarden.zsh` — `bw-unlock` / `bw-lock`. `bw login` already persists; only the unlock
  session key needs redoing, so the key is cached in `$XDG_RUNTIME_DIR` (tmpfs, cleared at
  logout) to make it one prompt per boot rather than one per terminal. Runs no `bw` at
  startup — `bw` is Node and costs ~1s.
- `git.zsh` — `gmb` prints the merge base of `HEAD` and `origin/main`, or a branch you name,
  as a bare sha so it composes: `git diff $(gmb)`, `git log $(gmb)..HEAD`. `gdmb` is the diff
  against that base — what the branch changed, with none of the base's own commits mixed in;
  a leading non-flag argument is the base and everything else forwards to `git diff`, so a
  path sharing a branch's name needs git's usual `--`. Deliberately thin: git already errors
  clearly on an unknown revision or a missing `origin/main`, so neither function checks.
- `worktree.zsh` — adds `~/.config/zsh/completions` to `$fpath` (must happen before `compinit`), puts `~/.local/bin` on `$PATH`, defines `alias wt=worktree-tmux`
