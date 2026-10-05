#!/usr/bin/env zsh
# Bitwarden CLI session.
#
# `bw login` persists in ~/.config/Bitwarden CLI/data.json until `bw logout`,
# so staying logged in needs nothing. What a new shell lacks is the *unlock*
# session key, which lives only in $BW_SESSION. Cache it in $XDG_RUNTIME_DIR
# (tmpfs, cleared at logout) so it's one master-password prompt per boot
# instead of one per terminal.
#
# Lazy on purpose: `bw` is Node and costs ~1s to start, so nothing runs `bw`
# at shell startup — only reading the cache file.
(( $+commands[bw] )) || return

_bw_session_file="${XDG_RUNTIME_DIR:-/run/user/$UID}/bw-session"

bw-unlock() {
  # A cached key can be stale: unlocking invalidates every earlier session key,
  # so another shell's bw-unlock supersedes ours. Re-read the file first (it may
  # already hold the newer key), and only prompt if that fails --check.
  if [[ -s $_bw_session_file ]]; then
    export BW_SESSION="$(<$_bw_session_file)"
    bw unlock --check --session "$BW_SESSION" &>/dev/null && return 0
    # Proven dead: drop it so a later shell doesn't export it at source time.
    rm -f $_bw_session_file
    unset BW_SESSION
  fi

  # `bw unlock --raw` exits 0 with empty output when it cannot read a password
  # (no tty, or ^D at the prompt), so test the key rather than the exit status —
  # otherwise an empty BW_SESSION gets exported and cached, which reads as
  # "unlocked" everywhere downstream.
  local key
  key="$(bw unlock --raw)"
  if [[ -z $key ]]; then
    print -u2 "bw-unlock: no session key returned; vault still locked"
    return 1
  fi
  ( umask 077; print -r -- "$key" >| $_bw_session_file )
  export BW_SESSION="$key"
}

bw-lock() {
  bw lock &>/dev/null
  rm -f $_bw_session_file
  unset BW_SESSION
}

# Shells opened after the first unlock inherit the key without prompting.
[[ -s $_bw_session_file ]] && export BW_SESSION="$(<$_bw_session_file)"
