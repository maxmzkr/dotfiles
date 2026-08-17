# neovim

Stow package for nvim. Symlinks `~/.config/nvim/` into `$HOME`.

Built on **LazyVim** (the distro). All the heavy lifting — keymaps, LSP, completion, formatting, debugging — comes from upstream LazyVim + its `extras` modules. This package only adds **overrides** on top.

`init.lua` is a one-liner: `require("config.lazy")`. Everything else is in `lua/`.

## External binaries

- **fzf must be newer than Ubuntu's.** noble ships 0.44.1, which lacks the `transform` action.
  trouble.nvim's fzf-lua integration puts `transform(...)` in the `<c-t>` binding
  unconditionally, so with 0.44.1 *every* fzf-lua picker dies at launch with
  `fzf error 2: unknown action: transform(...)`. Current fzf comes from the personal apt repo
  (`raw.githubusercontent.com/maxmzkr/packages`), so a fresh machine needs that source added
  before `apt install fzf` — the archive version is too old.
