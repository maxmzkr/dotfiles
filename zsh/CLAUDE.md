# zsh

Stow package for zsh + supporting scripts. Symlinks into `$HOME`:

- `.zshrc` — main config
- `.zsh_plugins.txt` — antidote plugin manifest
- `.p10k.zsh` — generated powerlevel10k theme config (95KB; do not hand-edit, use `p10k configure`)
- `.zshrc.d/worktree.zsh` — per-feature snippet (worktree-tmux alias and fpath)
- `.config/zsh/completions/_worktree-tmux` — zsh completion for the worktree script
- `.local/bin/worktree-tmux`, `.local/bin/screenshot-to-file` — user scripts on `$PATH`

## What `.zshrc` does

- Sets `EDITOR=vim`, `TERM=screen-256color`, `SSH_AUTH_SOCK` to the gnupg ssh-agent socket
- Aggressive history settings (10M entries, shared, dedup)
- Auto-starts tmux but does **not** auto-connect (so each new shell can become its own session — chosen for zed)
- Loads zsh-nvm with lazy loading and `.nvmrc` autoload
- fzf-tab completion with light theme
- Antidote sources `.zsh_plugins.txt` (oh-my-zsh libs/plugins, syntax-highlighting, autosuggestions, p10k, fzf-tab)
- `bindkey -v` — vi keymap
- PATH additions: `~/.bin`, coursier, krew, linuxbrew, snap/tenv, jenv
- Aliases: `vim → nvim`, kubectl shortcuts (`kg`, `kd`, `kw`, `kgj`), git shortcuts (`gcr`, `gmt`, `gcpt`), `sudo`/`watch`/`ipdb` trailing-space tricks
- Custom funcs: `notif`, `set-title`, `new-ses`, `venv`/`makevenv`/`vf` (manage `~/.venvs`)
- Work-specific env (Go proxy, private module sumdb) lives in the private `zshwork` package, not here

## Plugin loading order

Antidote reads `.zsh_plugins.txt` top-to-bottom; **order matters** there:
1. `ez-compinit` runs `compinit` exactly once
2. oh-my-zsh libs and plugins
3. syntax-highlighting, autosuggestions
4. powerlevel10k + the `.p10k.zsh` source
5. `fzf-tab` last (it must be the last plugin to bind `^I`)

## Adding new shell code

Prefer dropping a new file in `.zshrc.d/` (already sourced via the `mattmc3/zshrc.d` antidote plugin) over editing `.zshrc`. See `.zshrc.d/worktree.zsh` for an example.
