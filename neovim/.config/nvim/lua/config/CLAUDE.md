# config/

LazyVim's standard config slots. Each file is loaded automatically at a specific point:

- `lazy.lua` — bootstrap. Clones `lazy.nvim` if missing, sets leader keys (`<Space>` global, `\` local), calls `require("lazy").setup` with the LazyVim spec + `{ import = "plugins" }`. Has `checker.enabled = true` (auto-check for updates) and disables a few rtp plugins (`gzip`, `tarPlugin`, `tohtml`, `tutor`, `zipPlugin`).
- `options.lua` — empty (defaults from LazyVim only). Add `vim.opt.*` here.
- `keymaps.lua` — empty (defaults from LazyVim only). Add `vim.keymap.set` here.
- `autocmds.lua` — defines two `FileType` autocmds: enable wrap+spell+`camel` spelloption for Go and proto buffers. Uses a `maxmzkr_` augroup prefix.

Don't add plugin specs here; those go in `../plugins/`.
