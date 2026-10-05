---
name: editing-commits-interactively
description: Use when the user wants to go through a branch's commits one at a time and change their contents by hand — "commit by commit review", "review this commit by commit", "go through it commit by commit", "let me edit these commits one by one", "stop at each commit so I can change it", "walk me through the commits", "I want to fix each of these before they land", or after an agent run leaves a stack of commits the user intends to revise rather than reorganize. A review asked for *per commit* is this skill, not a code-review skill: the user is opening a rebase to edit each commit, not asking for a written list of findings.
---

# Editing Commits Interactively

## Overview

The user drives; you hold the rebase. An interactive rebase stops on each commit, the user
edits that commit's files by hand, you verify and propose changes, and the two of you iterate
until the commit is right. Then it lands and the next one starts — carrying whatever conflicts
the edits just created. A conflict is resolved and committed before the user's turn, so every
turn happens at the same kind of stop: `HEAD` is the commit, and the user's edits are amended in.

**Core principle:** every commit in the range gets the user's turn. A commit that lands without
one is a bug in the procedure, not a shortcut. The single most common way this goes wrong is a
conflict silently consuming a commit's turn (see step 4).

This skill **changes code on purpose**. That is what distinguishes it from
**regrouping-commits**, which rewrites history and must leave the tree byte-identical. Do not
apply that skill's tree-identity check here — it will fail by design. If the user wants the same
code in fewer commits, use regrouping-commits instead.

## When to Use

- A branch has commits whose *contents* the user wants to revise, commit by commit.
- The user wants to review each commit as a checkpoint, with tests run at each one.
- After an agentic run produced a plausible but unreviewed stack of commits.
- The user says "review" but scopes it to the commits — "commit by commit review", "review
  these one at a time". The scope is the tell: a code-review skill answers with findings and
  leaves the branch alone, and that is not what "commit by commit" asks for.

**Do NOT use when:**
- The goal is fewer or better-organized commits with unchanged code → **regrouping-commits**.
- Only the final state matters → just edit the working tree and commit normally.
- The commits are public and others may have branched from them, unless the user accepts a
  force-push.
- The branch is a gh-stack/stacked-PR chain — rewriting one branch reparents everything above it.

## The Procedure

### 1. Set up

```bash
git status --porcelain                      # MUST be empty before starting
git merge-base HEAD <default-branch>        # never guess the base; confirm it with the user
git rev-parse HEAD                          # record: the pre-edit head
git branch backup/<branch>-pre-edit         # escape hatch that is not `--abort`
git log --oneline <base>..HEAD
```

### 2. Start the rebase

Default to stopping at **every** commit. The user says so if they want a subset; do not ask
which they'd prefer.

```bash
GIT_SEQUENCE_EDITOR='sed -i "s/^pick/edit/"' git rebase -i <base>
```

Interactive editors are unavailable in this environment — every rebase command is scripted.
For a named subset, rewrite only those lines; leave the rest as `pick`.

### 3. At every stop, identify the state BEFORE doing anything

Never infer the state from "are there conflict markers". Run `rebase-state.sh` from this
skill's directory, or inline:

```bash
test -d "$(git rev-parse --git-path rebase-merge)" || echo "NO-REBASE"   # not REBASE_HEAD: it outlives the rebase
git diff --name-only --diff-filter=U                          # non-empty => unresolved conflict
test -f "$(git rev-parse --git-path rebase-merge/amend)"      # exists   => clean edit stop
# else HEAD's author, date, and message == REBASE_HEAD's       => conflict already committed
```

| | `EDIT-STOP` | `CONFLICT-UNRESOLVED` | `CONFLICT-RESOLVED` | `CONFLICT-COMMITTED` |
|---|---|---|---|---|
| Commit created yet? | **yes**, `HEAD` is it | no | no | **yes**, `HEAD` is it |
| `HEAD` is | this commit | the **previous** commit | the **previous** commit | this commit, resolved |
| `amend` marker file | present | absent | absent | absent |
| Unmerged paths | none | present | none | none |
| Next | the user's turn | resolve (step 4) | commit it (step 4) | the user's turn |
| `git commit --amend` here | correct | **destroys the previous commit** | **destroys the previous commit** | correct |

`CONFLICT-RESOLVED` is the trap: no conflicts are present, so it *looks* like a clean edit
stop, and amending there folds the pending commit into the one the user just finished editing.
This is why the check keys on the `amend` file and on `HEAD`'s identity, never on conflict
markers. Don't leave the rebase sitting in that state. Commit it, and it becomes
`CONFLICT-COMMITTED`, which is handled exactly like `EDIT-STOP`.

### 4. Reconcile the incoming commit — before the user's turn

A commit arrives rewritten on top of every edit made so far. Git stops and says so when
the collision is textual; when it is not — a rename that lands cleanly and leaves the call
sites stale — it says nothing and the commit arrives red. Both are the cost of the
rewrite, not the user's turn. Finish this phase before step 5 begins.

1. **Resolve conflicts, if the stop shape says there are any, and commit the result.**
   Show the user each hunk with what **each side** wanted and which you took. An earlier
   commit's edit frequently means a later commit should now do something different — or
   nothing — and only the user knows which, so the resolution is a proposal. Once it's
   resolved:

   ```bash
   git add -A && git commit -C REBASE_HEAD     # original message, author, and date
   ```

   Now `HEAD` is this commit and the stop is an ordinary edit stop. `git show HEAD`
   shows the commit against its parent, with the resolution folded in, and the user's
   edits show up alone in `git diff`. If the resolution empties the commit, `git commit`
   refuses. Don't pass `--allow-empty`. That refusal is step 7's silent drop showing
   up early, so ask the user whether the commit should go (`git rebase --skip`).
2. **Carry earlier edits forward.** Apply this walk's decisions through the commit —
   call sites, signatures, fixtures, flag text, docs — whether or not git flagged
   anything. This is mechanical propagation of decisions already made, so it needs no
   approval; a carry-forward that requires a *choice* is not mechanical, and that one
   goes to the user. Amend it into `HEAD` before the hand-off
   (`git add -A && git commit --amend --no-edit`), so the user's `git diff` holds only
   their own edits — step 5.5's capture depends on that.

   **Run `rebase-state.sh '<verify command>'` and make every line it prints a todo.**
   A rename or deletion from an earlier commit does not conflict: a declaration this
   walk moved into a *later* commit, or deleted outright, leaves the incoming commit
   naming a symbol that no longer exists, and git says nothing. The verify command's
   errors *are* the carry-forward list.

   ```bash
   ./rebase-state.sh 'cd services/foo && go build ./...'   # from this skill's directory
   ```

   It ends in `handoff: READY` or `handoff: BLOCKED`, and exits nonzero on BLOCKED.
   BLOCKED means a todo above it is still open. Finish them; do not write to the user
   from a BLOCKED stop, and do not re-plan around it. The failure mode this closes is
   not forgetting to look — it is looking, narrating what you found, and never closing
   it.
3. **Verify.** Build, then the scoped tests for what the commit touches. Green before
   hand-off, always.
4. **Report what you carried**, not what is broken. Handing back a red tree with a
   diagnosis asks the user to do the mechanical half of your job.

**Never let `git rebase --continue` create a conflicted commit.** Verified git behaviour:
when a commit conflicts, resolving it and running `--continue` creates the commit and
does not honor its `edit` stop. The rebase goes straight to the *next* commit, and the
conflicted commit — the one that most needed review — lands unseen. Committing the
resolution yourself is what gives it back its stop: `--continue` only runs after the
user's turn, the same as at any other stop.

### 5. The turn

Every turn starts from `EDIT-STOP` or `CONFLICT-COMMITTED`. The two are handled the same way.

1. Report position (`3/7`) and the commit's subject, and say whether a conflict was resolved into it.
2. Show what this commit does — `git show HEAD`.
3. **Hand off and end the turn.** "Make your edits and tell me when you're done." Do not poll,
   do not guess when they're finished, do not continue on their behalf.
4. When they say done: `git status` and `git diff` to see exactly what changed.
5. **Capture his comment voice before touching anything.** That diff is the only
   evidence of which comments are his; the moment you edit the tree the provenance
   is gone and capture has to be reconstructed from a snapshot, if one was taken.
   Run **learning-comment-voice**'s capture here, not at the end of the walk.
6. Infer a verification command scoped to what the commit touches and run it.
7. Read their changes; propose changes. Whether the comments the commit introduces
   earn their place is **review-comments**' question — run it rather than judging
   them inline. They edit more, or you edit. Re-run. Loop.
8. The loop ends **when the user says it ends** — not when tests go green.

### 6. Land the commit and continue

Re-run the scoped check first: the user's last edit is the one nobody has verified, and a
`--continue` carries it into every commit above.

```bash
# EDIT-STOP / CONFLICT-COMMITTED:
git add -A && git commit --amend --no-edit      # or amend the message if the idea changed
GIT_EDITOR=true git rebase --continue
```

`GIT_EDITOR=true` is mandatory: `git rebase --continue` can open an editor for a commit
message, and a real `$EDITOR` hangs the tool.

### 7. After every continue, check the commit actually landed

```bash
git log --oneline -1                            # or compare against the recorded original log
```

**A conflict resolution that leaves a commit empty makes git drop it silently** — no prompt, no
warning, the branch simply comes out one commit shorter. This is not exotic: it is what happens
whenever the user's edit to an earlier commit already did what a later commit was going to do.
When a commit disappears, say so and confirm the user wants it gone.

### 8. Finish

```bash
git rebase <base> --exec 'env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE <full test command>'
git range-diff backup/<branch>-pre-edit...HEAD  # the whole set of edits, in one view
git push --force-with-lease                     # never bare --force
```

The per-commit command in step 6 is scoped and can narrow to nothing without anyone noticing.
**The final sweep is the full suite, unscoped**, and its exit status must come from the test
tool itself — `go test ./... | grep -v '^ok'` exits 1 on a fully green tree, because `grep`
found nothing to print. Redirect to a file and print it only on failure.

## Recovering From an Overshoot

If a commit's turn was missed, the rebase is already past it. Do **not** hand-patch
`.git/rebase-merge/`, and do **not** `git reset --hard` mid-rebase. Let the rebase finish, then
start a second, targeted rebase with only that commit marked `edit`. Standard git state
throughout; nothing to unwind.

## Red Flags — STOP

- About to run `git rebase --continue` without the user having said they're done.
- Handing a commit over without having checked it still builds and passes.
- Reporting a red build to the user when an earlier commit's edit is what broke it.
- Writing anything to the user while `rebase-state.sh` says `handoff: BLOCKED` — the
  carry-forward is a task to finish, not a finding to relay.
- About to edit the tree at a stop before capturing his comment edits — after that,
  no diff distinguishes his comments from yours.
- About to `git rebase --continue` with a resolved conflict that hasn't been committed yet —
  that skips the commit's turn.
- About to `git commit --amend` without having run `rebase-state.sh`.
- Resolving a conflict by taking one side wholesale and reporting it afterward rather than first.
- Reaching into `.git/rebase-merge/`, or for `git reset --hard`, to fix a rebase.
- Calling a commit done because the tests passed.
- The commit count changed and you have not accounted for it.
- Checking tree-identity against the pre-edit head — this skill changes code on purpose.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Resolving a conflict and running `--continue` instead of `git commit -C REBASE_HEAD` | The commit lands with no review — the exact commit that needed it most |
| Committing the resolution with a plain `git commit` | The original author and date are lost, and `rebase-state.sh` still reports `CONFLICT-RESOLVED` — following its advice commits twice |
| Detecting state by looking for conflict markers | `CONFLICT-RESOLVED` reads as a clean stop; amending folds two commits into one |
| `git rebase --continue` without `GIT_EDITOR=true` | Editor opens on the message, tool call hangs |
| Not checking the log after a continue | An emptied commit vanishes silently and nobody notices |
| Scoped per-commit tests with no full sweep at the end | The gate narrows commit by commit until it proves nothing |
| Continuing when the user went quiet | Their half-finished edits get amended in, or lost |
| `git rebase --abort` instead of the backup branch | Every completed turn in the range is thrown away |
