# gitwork

Stow package for work-only git config. Symlinks `~/.gitconfigs/.workconfig` and `~/.gitignorerevs` into `$HOME`.

The main `~/.gitconfig` (from the `git/` package) has `[include] path = ~/.gitconfigs/.workconfig`, which pulls this in to override `user.email`/`signingkey` with the work identity (`maxmzkr@censys.io`).

`.gitignorerevs` is currently empty but is referenced by `.workconfig` as `blame.ignoreRevsFile` — append commit SHAs there to exclude them from `git blame`.

Split out from `git/` so the work identity can be stowed independently on machines that need it.
