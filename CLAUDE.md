# dotfiles

Personal config files for Max Mizikar's Linux setup, organized as **GNU Stow packages**.

## Layout convention

Each top-level directory is a stow package whose contents mirror the target layout under `$HOME`. Running `stow <package>` from this repo symlinks the package's files into `~/`.

Example: `zsh/.zshrc` → `~/.zshrc`, `neovim/.config/nvim/init.lua` → `~/.config/nvim/init.lua`.

Files inside a package directory keep their leading dot (`.zshrc`, `.config/`, `.local/`) because that's where they land in `$HOME`.

## Packages

- `byobu/` — byobu's bundled tmux config (forces zsh)
- `git/` — global git config (`~/.gitconfig`)
- `gitwork/` — work-only git overrides, included from `~/.gitconfig`
- `golangci-lint/` — `~/.golangci.yaml`
- `kitty/` — kitty terminal config (`~/.config/kitty/kitty.conf`)
- `mcphub/` — mcphub.nvim MCP server registry (`~/.config/mcphub/servers.json`). No secrets or internal
  hostnames live here: values are `${cmd: ...}` placeholders that mcp-hub resolves at launch (it resolves
  them in `env`, `args`, `command`, `url`, `headers`, `cwd`). The `bifrost` server reads both its
  `mcp_url` and `api_key` from the untracked `~/.config/bifrost/credentials.json`, so that file must exist
  on a new machine — see `neovim/.config/nvim/lua/plugins/` for the nvim side of the same file.
- `librepods/` — autostart entry for LibrePods, the tray app for Beats/AirPods noise modes. The
  AppImage itself lives at `~/Applications/librepods-x86_64.AppImage` (untracked binary), so the
  `Exec=` path is machine-specific. It draws its icon via StatusNotifier, which GNOME only renders
  with `gnome-shell-extension-appindicator` installed. Holds the AAP L2CAP channel while running,
  which is the same channel `zsh/.local/bin/beats` needs — only one of the two can talk at a time.
- `neovim/` — LazyVim-based nvim config
- `starship/` — starship prompt config (`~/.config/starship.toml`), the replacement for
  powerlevel10k. Separate from `zsh/` so the prompt can be stowed on its own; the shell-side
  init lives in `zsh/.zshrc.d/starship.zsh`. Config is ASCII-only — no Nerd Font required.
- `stylua/` — stylua formatter config
- `tmux/` — main tmux config (`~/.tmux.conf`)
- `wireplumber/` — audio output auto-switching: Bluetooth headphones take over on connect and hand back
  on disconnect. Spans two XDG roots, because WirePlumber looks up config under `XDG_CONFIG_HOME` but
  scripts only under `XDG_DATA_HOME` — a custom hook in `.config/wireplumber/scripts/` is silently never
  found. Replaces the stock `find-selected-default-node` hook, whose flat +30000 boost makes a manual
  pick outrank every device forever.
- `zsh/` — zsh + antidote + custom scripts (prompt is in `starship/`)

## Setup

```bash
cd ~/dotfiles
stow zsh neovim git tmux starship ...
```

### On a fresh machine

`.zshrc` is written to survive a bare box: every optional tool (task, nvim, terraform, pyenv,
jenv, gvm, tenv, linuxbrew, krew, coursier) is behind an existence check, and the gpg ssh-agent
socket is only exported if it's actually there. Two things are worth knowing:

- **antidote self-bootstraps.** If `~/.antidote` is missing, `.zshrc` clones it (needs `git` and
  network) and antidote then clones every plugin on first shell — the first startup is slow and
  noisy, subsequent ones aren't. Without `git` it prints one warning and comes up plugin-less
  instead of erroring on every line.
- **starship is not bootstrapped.** Install it (`~/.local/bin/starship` here) or the prompt
  silently falls back to zsh's default; `.zshrc.d/starship.zsh` no-ops when the binary is absent.

Verify changes against a throwaway `$HOME` rather than your own:

```bash
stow --no-folding -t /tmp/fakehome -d ~/dotfiles zsh starship
env -i HOME=/tmp/fakehome PATH=/usr/bin:/bin TERM=xterm zsh -i -c 'echo up'
```

`--no-folding` matters: with folding, `~/.local` in the fake home becomes a symlink to
`zsh/.local` in the repo, and anything the test shell writes under it (gh device ids, caches)
lands in your working tree.

## CLAUDE.md and stow

Some subdirectories have a `CLAUDE.md`. Stow has no default rule to skip them, so `stow zsh` will symlink (for example) `~/.zshrc.d/CLAUDE.md` into `$HOME`. If that's a problem, add a `.stow-local-ignore` at the repo root with `CLAUDE\.md`.
