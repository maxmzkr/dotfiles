# after/queries/

Treesitter query files that **extend** the upstream queries (each file starts with `; extends`). Per-language subdirs:

- `cenql/highlights.scm` — highlights for the custom cenql parser (see `../../lua/plugins/treesitter.lua`)
- `go/highlights.scm` — marks Go identifiers (function names, fields, vars, params) as `@spell` so spell-check runs on identifier names (paired with the `wrap_go_spell` autocmd in `../../lua/config/autocmds.lua`)
- `proto/highlights.scm` — same `@spell` treatment for proto service/rpc/enum/field/message names
- `highlights/` — empty (likely a typo; query subdirs should be named after **languages**, not query types)
