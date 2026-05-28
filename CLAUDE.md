# dotfiles

Personal config files for Max Mizikar's Linux setup, organized as **GNU Stow packages**.

## Layout convention

Each top-level directory is a stow package whose contents mirror the target layout under `$HOME`. Running `stow <package>` from this repo symlinks the package's files into `~/`.

Example: `zsh/.zshrc` → `~/.zshrc`, `neovim/.config/nvim/init.lua` → `~/.config/nvim/init.lua`.

Files inside a package directory keep their leading dot (`.zshrc`, `.config/`, `.local/`) because that's where they land in `$HOME`.

## Packages

- `byobu/` — byobu's bundled tmux config (forces zsh)
- `dconf/` — GNOME/dconf settings dump (binary GVariant DB)
- `git/` — global git config (`~/.gitconfig`)
- `gitwork/` — work-only git overrides, included from `~/.gitconfig`
- `golangci-lint/` — `~/.golangci.yaml`
- `neovim/` — LazyVim-based nvim config
- `stylua/` — stylua formatter config
- `tmux/` — main tmux config (`~/.tmux.conf`)
- `zsh/` — zsh + antidote + p10k + custom scripts

## Setup

```bash
cd ~/dotfiles
stow zsh neovim git tmux ...
```

## CLAUDE.md and stow

Some subdirectories have a `CLAUDE.md`. Stow has no default rule to skip them, so `stow zsh` will symlink (for example) `~/.zshrc.d/CLAUDE.md` into `$HOME`. If that's a problem, add a `.stow-local-ignore` at the repo root with `CLAUDE\.md`.
