# git

Stow package for the global git config. Symlinks `~/.gitconfig` into `$HOME`.

Key behaviors set here:
- `core.editor = nvim`, with a fallback `vim` block above it
- `url.ssh://git@github.com/.insteadOf = https://github.com/` — every GitHub HTTPS URL gets rewritten to SSH (declared twice in the file)
- `pull.rebase = true`, `init.defaultBranch = main`
- `commit.gpgsign = false` despite a `user.signingkey` being set
- Mergetool/difftool: nvim in `-d` (diff) mode
- `include.path = ~/.gitconfigs/.workconfig` — pulls in work identity from the `gitwork` stow package

Aliases: `co`, `ci`, `st`, `br`, `hist` (graph log), `d` (diff), `a`/`ap` (add/add -p), `ac` (add+commit), `undo` (soft reset HEAD~1), `rmbranches` (delete locally-gone branches), `stashgrep` (grep through stashes).

The `patch` alias is malformed — line 38 concatenates `patch` and `cl = clone` onto one line.
