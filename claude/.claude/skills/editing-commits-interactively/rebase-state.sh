#!/bin/sh
# Print the shape of the current interactive-rebase stop, and the facts that distinguish it.
# Run this BEFORE touching anything at a stop: the states need different handling, and
# CONFLICT-RESOLVED looks like a clean stop (see SKILL.md, step 3).
#
# Usage: rebase-state.sh [verify-command]
#
# With a verify command it also runs it and prints the stop's remaining work as a
# checklist, ending in handoff: READY or handoff: BLOCKED. BLOCKED means the
# carry-forward is unfinished -- the commit names something an earlier commit of this
# walk renamed, moved or deleted -- and the user's turn has not started yet.
set -e

# Not REBASE_HEAD: git leaves it behind after the rebase finishes.
if [ ! -d "$(git rev-parse --git-path rebase-merge)" ]; then
    echo "state:   NO-REBASE"
    exit 0
fi

# REBASE_HEAD is not always set at a stop: a commit git applied by fast-forward
# leaves none. Every branch below that needs it must say so, or the script reports
# a state it did not establish -- and prints git's fatals while doing it.
if git rev-parse --verify -q REBASE_HEAD >/dev/null 2>&1; then
    pending=$(git rev-parse REBASE_HEAD)
else
    pending=
fi

if [ -n "$(git diff --name-only --diff-filter=U)" ]; then
    state=CONFLICT-UNRESOLVED
elif [ -f "$(git rev-parse --git-path rebase-merge/amend)" ]; then
    state=EDIT-STOP
elif [ -z "$pending" ]; then
    # Nothing pending and no amend marker: git has applied this commit and HEAD is
    # it. Same handling as an edit stop, but say which fact got us here.
    state=EDIT-STOP-NO-REBASE-HEAD
elif [ "$(git rev-parse HEAD)" != "$pending" ] &&
     [ "$(git log -1 --format='%an%ae%ad%B' HEAD)" = "$(git log -1 --format='%an%ae%ad%B' REBASE_HEAD)" ]; then
    # `git commit -C REBASE_HEAD` copies author, date, and message, so HEAD is the
    # resolved rewrite of the pending commit rather than the previous one.
    state=CONFLICT-COMMITTED
else
    state=CONFLICT-RESOLVED
fi

echo "state:   $state"
echo "HEAD:    $(git log -1 --format='%h %s')"
if [ -n "$pending" ]; then
    echo "pending: $(git log -1 --format='%h %s' REBASE_HEAD)"
else
    echo "pending: (none -- REBASE_HEAD unset; HEAD is this commit)"
fi
if [ -f "$(git rev-parse --git-path rebase-merge/msgnum)" ]; then
    echo "position: $(cat "$(git rev-parse --git-path rebase-merge/msgnum)")/$(cat "$(git rev-parse --git-path rebase-merge/end)")"
fi
unmerged=$(git diff --name-only --diff-filter=U)
[ -n "$unmerged" ] && echo "unmerged: $unmerged"

case "$state" in
  EDIT-STOP|EDIT-STOP-NO-REBASE-HEAD|CONFLICT-COMMITTED)
                      echo "land-with: git commit --amend, then GIT_EDITOR=true git rebase --continue  (HEAD IS this commit)" ;;
  CONFLICT-*)         echo "next:      resolve, then git add -A && git commit -C REBASE_HEAD  (turns this into an edit stop)" ;;
esac

[ $# -eq 0 ] && exit 0

# The stop's own work, as a checklist. Each line is one task; the hand-off is the
# last one and cannot start while any line above it is open.
log=$(mktemp)
set +e
sh -c "$*" >"$log" 2>&1
rc=$?
set -e

case "$state" in
  CONFLICT-UNRESOLVED) echo "todo:  [ ] resolve the conflict, then git add -A && git commit -C REBASE_HEAD" ;;
  CONFLICT-RESOLVED)   echo "todo:  [ ] commit the resolution: git add -A && git commit -C REBASE_HEAD" ;;
  *)                   echo "todo:  [x] commit exists" ;;
esac

if [ "$rc" -eq 0 ]; then
    echo "todo:  [x] carry-forward complete ($* passed)"
else
    echo "todo:  [ ] carry-forward: $* exited $rc -- every error names a symbol to carry"
    echo "verify-log: $log"
fi

echo "todo:  [ ] amend and hand off for review"

case "$state" in EDIT-STOP|EDIT-STOP-NO-REBASE-HEAD|CONFLICT-COMMITTED) ok_to_hand_off=1 ;; *) ok_to_hand_off= ;; esac
if [ -n "$ok_to_hand_off" ]; then
    if [ "$rc" -eq 0 ]; then
        echo "handoff: READY"
        rm -f "$log"
        exit 0
    fi
fi
echo "handoff: BLOCKED -- finish the open lines before writing to the user"
exit 1
