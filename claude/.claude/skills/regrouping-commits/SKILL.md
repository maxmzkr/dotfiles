---
name: regrouping-commits
description: Use when a branch has accumulated more commits than a reviewer needs — "reduce the number of commits", "squash these", "clean up the history", "too many commits", "tidy the branch before review", or before opening a PR whose log reads as an authoring diary rather than a sequence of ideas.
---

# Regrouping Commits

## Overview

A branch's commit log is written for a reviewer, not for the person who wrote it. Authoring
order is incidental: it records when you noticed things. Review order is deliberate: each
commit is one idea the reviewer can hold in their head, verify, and sign off on before moving
to the next.

**Core principle:** the target is not a smaller number. The target is that every surviving
commit is one self-contained idea, and no commit exists only because of how the work
happened to unfold. The count falls out of that.

The end state of the branch's tree must be **byte-identical** to what it was before. This is
a history rewrite, never a code change.

## When to Use

- A branch has commits whose messages describe fixing, cleaning, renaming, or adjusting
  something introduced earlier on the same branch.
- The log reads chronologically ("then I also...") rather than as a build-up of ideas.
- Before opening or updating a PR, when the reviewer will read commit-by-commit.

**Do NOT use when:**
- The commits are already public and others may have branched from them, unless the user
  confirms a force-push is acceptable.
- The branch is a stack managed by gh-stack or similar — rewriting one branch's history
  reparents everything above it. Use the stack tool's own restack flow instead.
- The work is a single commit, or every commit is already an independent idea.

## The Procedure

### 1. Establish the range and the invariant

```bash
git log --oneline <base>..HEAD
git rev-parse HEAD^{tree}          # record this — it must be unchanged at the end
```

Never guess the base. Take it from the user, or from the merge-base with the default branch.

### 2. Read every commit's actual diff, not just its subject

```bash
git log --stat <base>..HEAD
git show <sha>                     # for any commit whose role is unclear
```

Subjects lie about scope. A commit called "add protos" that also wires up a caller is two
ideas; a commit called "refactor comments" that only touches lines added three commits
earlier is not an idea at all.

### 3. Classify each commit

| Shape | Signal | Disposition |
|---|---|---|
| **Fixup** | Touches only lines introduced by an earlier commit in the range; message says fix/drop/rename/adjust/address | Fold into that commit |
| **Continuation** | Extends an earlier commit's idea; neither half is separately reviewable | Fold into that commit |
| **Idea** | Stands alone: a reviewer could approve it without reading the rest | Keep |
| **Stray** | Unrelated to the branch's purpose (a typo fix, an unrelated lint) | Keep separate, or offer to split it out |

A commit is an **idea** only if you can state what it does without referring to another
commit in the range. "Also handles the web case" is a continuation. "Adds the layered web
property RPCs" is an idea.

Assign the tests too, not just the source. A test that exercises a commit's new behaviour
belongs in that commit even when it lives in a file the rest of the branch owns — otherwise
the commit that introduces the behaviour lands with nothing proving it.

### 4. Propose the plan and stop

Present, before touching anything:

- The current log, one line each.
- The proposed log, one line each, with the final commit messages written out.
- For each dropped commit, which surviving commit absorbs it.
- Anything you could not classify confidently, named as a question.

**Wait for approval.** Do not start the rebase on the assumption the plan is obviously right.

### 5. Execute

Prefer a scripted, non-interactive rebase — interactive flags are unavailable in this
environment.

```bash
git switch -c backup/<branch>-pre-squash && git switch -   # cheap escape hatch
GIT_SEQUENCE_EDITOR='sed -i -e "2,4s/^pick/fixup/"' git rebase -i <base>
```

Or, when messages are being rewritten wholesale, reset and recommit:

```bash
git reset --soft <base>
# then stage and commit each idea's files/hunks in order
```

If the commits were authored with `fixup!`/`squash!` subjects, `git rebase --autosquash
<base>` does it with no editor at all.

### 6. Verify

```bash
git diff <old-head> HEAD           # MUST be empty
git rev-parse HEAD^{tree}          # MUST match the tree recorded in step 1
```

An empty tree diff is the proof the rewrite was lossless. Then run the project's full test
suite on **every** resulting commit, so each one is independently good and `git bisect` stays
meaningful:

```bash
git rebase <base> --exec '<project test command>'
```

Report the result honestly. A commit that fails its tests is a regrouping bug — usually a
hunk folded into the wrong parent — not something to note and move past.

Two things make an `--exec` harness lie, and both look like success:

- **A command that cannot fail.** `cmd | grep ...; echo PASS` reports PASS unconditionally,
  because the exit status came from `echo`. Chain with `&&`, and make the failure branch say
  FAIL. If you never saw the harness fail, you have not verified anything.
- **Generated or untracked artifacts left at the final state.** Anything not in the tree —
  generated protobuf/ORM/codegen output, build caches — does not rewind with the checkout,
  so early commits get compiled against late generated code and fail for a reason that does
  not exist in their own history. Regenerate inside the `--exec`, and be suspicious of a
  failure that names a symbol a later commit introduces.

`git rebase --exec` also exports `GIT_DIR`, `GIT_WORK_TREE`, and `GIT_INDEX_FILE` to the
command. Build tooling that locates the repo root by shelling out to
`git rev-parse --show-toplevel` (Taskfile/Make variables often do) then resolves the wrong
root and fails on paths that exist. Strip them:

```bash
git rebase <base> --exec 'env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE <regen && test>'
```

### 7. Push

Only with `--force-with-lease`, never bare `--force`:

```bash
git push --force-with-lease
```

## Writing the Surviving Messages

Each message describes the idea as it now stands, not the sequence that produced it. Delete
every trace of the folded commits: no "and also", no "plus cleanup", no "(includes review
fixes)". A reader must not be able to tell the commit was assembled.

Match the repo's existing convention — check `git log` on the default branch and any
`commitlint.config.*` before inventing a format.

## Red Flags — STOP

- About to rebase without having shown the plan.
- About to fold a commit whose diff you have not read.
- Tree diff at the end is non-empty and you are looking for a reason it's fine.
- Reaching for `git push --force` because `--force-with-lease` was rejected.
- Tempted to fix a bug, rename a variable, or drop a comment "while in there."
- Every commit passed on the first try and you never watched the harness report a failure.
- Squashing to hit a number the user named, past the point where ideas are still separable.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Classifying by commit subject alone | Fixups get kept, real ideas get merged |
| Rewriting code during the rebase | The diff no longer matches what was reviewed; the invariant check fails and you can't tell why |
| Folding everything into one commit because it's easier | Reviewer loses the build-up; large PRs become unreviewable |
| Testing only the final commit | Broken intermediate commits survive and poison bisect |
| Skipping the backup branch | A botched rebase costs the whole branch instead of one `git switch` |
| Force-pushing a branch someone else has pulled | Their work is silently orphaned |
