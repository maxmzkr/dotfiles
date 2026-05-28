# neovim

Stow package for nvim. Symlinks `~/.config/nvim/` into `$HOME`.

Built on **LazyVim** (the distro). All the heavy lifting — keymaps, LSP, completion, formatting, debugging — comes from upstream LazyVim + its `extras` modules. This package only adds **overrides** on top.

`init.lua` is a one-liner: `require("config.lazy")`. Everything else is in `lua/`.
