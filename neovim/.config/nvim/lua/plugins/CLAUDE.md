# plugins/

One file per plugin override or addition. Each returns a lazy.nvim spec table (or list of specs). Auto-imported by `../config/lazy.lua`.

## Files

- `avante.lua` — avante.nvim. Disabled (`enabled = false`); superseded by `sidekick.lua`.
- `codecompanion.lua` — CodeCompanion (LLM chat/inline/CLI) routed through a local Bifrost proxy. Disabled (`enabled = false`); superseded by `sidekick.lua`.
- `sidekick.lua` — sidekick.nvim CLI integration (active AI plugin). Two Claude tool profiles: `claude` (`<leader>aa`, subscription — clears ambient `ANTHROPIC_*` vars) and `claude-bifrost` (`<leader>ab`, routes through the Bifrost proxy via `~/.config/bifrost/credentials.json`). `<leader>aa` also auto-opens on blank launch. NES disabled (no Copilot sub).
- `colorscheme.lua` — `solarized.nvim`, light background.
- `copilot.lua` — copilot.lua + CopilotChat.nvim. Disabled (`enabled = false`); the `ai.copilot`/`ai.copilot-chat` LazyVim extras are also removed from `lazyvim.json`.
- `mcphub.lua` — MCPHub plugin with `<leader>am` keymap; wires it into CodeCompanion as an extension.
- `dap-python.lua` — `<leader>dn/df/ds` for nvim-dap-python test/debug actions.
- `fugitive.lua` — vim-fugitive + vim-rhubarb, loaded on `BufWinEnter`.
- `go.lua` — disables `gofumpt` in gopls and removes the `goimports`/`gofumpt` formatters from conform.nvim (gopls already does this). Most of the file is commented-out experiments (none-ls/golangci-lint, sonarlint).
- `mason.lua` — bumps mason log level to DEBUG.
- `mini.pairs.lua` — disables mini.pairs (autocompletion of `)` was unwanted).
- `nvim-cmp.lua` — empty (all content commented out).
- `snacks.lua` — disables snacks animations and scroll smoothing.
- `sql.lua` — empty (all content commented out).
- `tmux-navigator.lua` — `christoomey/vim-tmux-navigator` with `C-h/j/k/l` keys.
- `treesitter.lua` — registers a custom `cenql` parser sourced from `~/tree-sitter-cenql`, adds `cenql` filetype detection, ensures `cenql` and `proto` are installed.
- `xml.lua` — installs `xml` treesitter parser and `lemminx` LSP.
- `yaml.lua` — yamlls schema for `development.values.yaml`, format disabled.

## Conventions

- One plugin per file
- Empty files (`nvim-cmp.lua`, `sql.lua`) and heavily-commented files (`go.lua`) are kept as scratch space — don't delete them on cleanup unless you understand the intent
