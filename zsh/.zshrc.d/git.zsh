# git helpers.

# The merge base of HEAD and a base branch, as a bare sha so it composes:
# `git diff $(gmb)`, `git log $(gmb)..HEAD`. git reports its own errors for an
# unknown revision or a missing origin/main.
gmb() { git merge-base HEAD "${1:-origin/main}" }

# git diff against that merge base — what this branch changed, with none of the
# base's own commits mixed in. A first argument that isn't a flag is the base;
# everything else goes to git diff, so a path sharing a branch's name needs `--`.
gdmb() {
  local base=origin/main
  [[ -n $1 && $1 != -* ]] && { base=$1; shift }
  git diff "$(gmb $base)" "$@"
}
