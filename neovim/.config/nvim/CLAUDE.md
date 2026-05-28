# nvim/

Mirrors `~/.config/nvim/` — the actual nvim runtime config.

## Files at this level

- `init.lua` — one line, `require("config.lazy")`
- `lazyvim.json` — generated; tracks which LazyVim `extras` modules are enabled (AI/copilot, dap.core, lang.{go,python,java,scala,terraform,typescript,yaml,markdown,docker,helm,json}, test.core, etc.)
- `lazy-lock.json` — generated; plugin commit lockfile (gitignored by repo root)

## Subdirs

- `lua/config/` — LazyVim's standard slots: `lazy.lua` (bootstrap), `options.lua`, `keymaps.lua`, `autocmds.lua`
- `lua/plugins/` — one file per plugin override/addition
- `ftplugin/` — per-filetype config (currently only commented-out java)
- `queries/`, `after/queries/` — treesitter query overrides for vim, proto, go, and a custom `cenql` parser
- `spell/` — personal spellfile additions

## How LazyVim is set up

`lua/config/lazy.lua` bootstraps `lazy.nvim`, then runs:
```lua
{ "LazyVim/LazyVim", import = "lazyvim.plugins" },
{ import = "plugins" },
```
LazyVim loads its own plugin spec + extras (driven by `lazyvim.json`); `import = "plugins"` then auto-loads every file in `lua/plugins/` to override or extend.

`checker.enabled = true` means lazy checks for plugin updates on each startup.
