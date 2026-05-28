# dconf

Stow package for GNOME's dconf settings. Symlinks `~/.config/dconf/user` (a binary GVariant database) into `$HOME`.

Restoring requires more than the symlink — dconf reads `~/.config/dconf/user` but the running `dconf-service` may need a restart (or a session re-login) to pick up changes. Editing this file by hand is not supported; use `dconf` / `dconf-editor` to modify settings and re-commit.
