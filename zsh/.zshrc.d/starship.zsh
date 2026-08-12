#!/usr/bin/env zsh
# starship prompt. Config lives in the `starship` stow package
# (~/.config/starship.toml).
#
# `starship init zsh` execs the binary on every startup (~10ms), so cache its
# output and regenerate when the binary changes — same trick as the task
# completion cache in .zshrc.
(( $+commands[starship] )) || return

_starship_init_cache="${ZSH_CACHE_DIR:-$HOME/.cache/zsh}/starship-init.zsh"
if [[ ! -s $_starship_init_cache || $commands[starship] -nt $_starship_init_cache ]]; then
  mkdir -p ${_starship_init_cache:h}
  starship init zsh --print-full-init >| $_starship_init_cache
fi
source $_starship_init_cache
unset _starship_init_cache
