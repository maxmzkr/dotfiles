# golangci-lint

Stow package for the global golangci-lint config. Symlinks `~/.golangci.yaml` into `$HOME`.

Notable: `linters.enable: []` — no linters are turned on by default. The file only tunes `linters-settings` (errcheck is stricter than default; exhaustive switch-checking opts in).

Per-project `.golangci.yaml` is expected to override `enable:` with the actual linter set.
