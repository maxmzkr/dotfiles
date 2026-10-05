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
- Your human partner wants to walk the branch and mark it up commit by commit — see
  **Commit-by-Commit Review Pass**, which stands on its own and needs no regrouping first.

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

**When a commit's file state has to be written by hand** — because the split runs through
one file and no combination of hunks produces it — build that state **forward from the
parent**: take the parent's version and add what this commit introduces, where it belongs.
Never build it backward from the final version by deleting what belongs to later commits.
Backward reconstruction re-inserts the surviving code wherever your splice put it, so
functions the commit never touches move, and the reviewer reads their bodies twice — once
as a deletion, once as an addition. One commit built that way in a recent branch carried
205 lines of pure movement in a 1,000-line diff, all of it functions a later commit deleted
anyway.

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

**Make the harness cheap before running it eleven times.** The per-commit gate has to prove the
commit builds and its tests pass; everything else is tax you pay once per commit. On a Go monorepo
branch, three changes took a sweep from ~12 minutes to 32 seconds:

- **Do not link.** `go build ./service/...` links every `main` package into an executable it then
  discards, and the Go build cache does not cache links. Measured on one service: 42 library
  packages compiled in 0.43s, five binaries linked in 3.4s. Build the non-main packages
  (`go list -f '{{if ne .Name "main"}}{{.ImportPath}}{{end}}'`) per commit and link once at the tip.
- **Regenerate generated code only when its input changed**, and decide that from the *tree*, not
  from the commit: `find proto -name '*.proto' -newer "$newest_generated_file"`. A
  `git diff HEAD~ HEAD` check misses the first commit of a sweep, where the generated files are
  left over from the previous run's tip, and cannot tell that a fresh worktree has none.
- **Pin the CPU profile** for the duration: `with-performance git rebase <base> --exec ...` was
  27% faster than the same sweep on a balanced profile.

Whatever remains, delete the slowest test that never earns its place. A brute-force sweep that has
never been the only test to catch a mutation is pure per-commit tax -- one such test was 31 of a
suite's 35 seconds.

Then check that no commit pads its own diff with code it only moved:

```bash
./moved_functions.py <base>..HEAD          # in this skill's directory
```

Anything it prints is diff the idea did not need. Zero is the expected answer; a nonzero
one is legitimate only when the move **is** the idea — extracting a file, regrouping a
package — in which case say so rather than letting it pass unnoticed.

Report the result honestly. A commit that fails its tests is a regrouping bug — usually a
hunk folded into the wrong parent — not something to note and move past.

Three things make an `--exec` harness lie. Two look like success, one looks like failure:

- **A command that cannot fail.** `cmd | grep ...; echo PASS` reports PASS unconditionally,
  because the exit status came from `echo`. A pipe does it silently too: `cmd | head` is 0
  even when `cmd` exits 1, since without `set -o pipefail` only the last stage's status
  survives. Chain with `&&`, and make the failure branch say FAIL.
- **A command that cannot succeed.** The mirror image, and the one that wastes a whole
  rebase, because a red harness reads as a real regrouping bug. A filter that trims output
  also *owns the exit status*, and filters fail when they match nothing:
  `go test ./... | grep -v '^ok'` exits **1 on a fully green tree**, because `grep` found
  nothing left to print. `grep -c` does the same, printing `0` and exiting 1. Don't filter
  inside the harness — redirect to a file, let the tool's own status decide, and print the
  log only on failure.
- **Generated or untracked artifacts left at the final state.** Anything not in the tree —
  generated protobuf/ORM/codegen output, build caches — does not rewind with the checkout,
  so early commits get compiled against late generated code and fail for a reason that does
  not exist in their own history. Regenerate inside the `--exec`, and be suspicious of a
  failure that names a symbol a later commit introduces.

A harness you have never watched both pass *and* fail has not been verified in either
direction. Before trusting a clean run, break something on purpose and confirm it goes red;
before believing a red run, check that the tool itself — not the plumbing around it — is
what returned nonzero.

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

## Commit-by-Commit Review Pass

Once the branch is regrouped, your human partner may want to walk it commit by commit and
mark it up — the same way you'd mark up a draft. This is a separate pass with its own rules,
and it can be run standalone on any branch, regrouped or not.

**Position the worktree AT the commit. Do not `git show` it from the tip.** "Let's go
commit by commit" means their editor must be showing that commit's tree and nothing later.
Reading a commit out with `git show` while `HEAD` sits at the tip looks like progress and
isn't: they open a file and see the final version, `HEAD~1` is the wrong commit, and both of
you spend the next several turns disagreeing about where you are.

```bash
GIT_SEQUENCE_EDITOR='sed -i "s/^pick/edit/"' GIT_EDITOR=true git rebase -i <base>
```

Every commit becomes an `edit` stop, so the rebase halts with the worktree at commit 1.
Announce which commit you're on and how many remain — `git status` prints "Last command
done" and "Next commands to do", and the counters are in
`$(git rev-parse --git-path rebase-merge)/{msgnum,end}`. In a worktree that path is under
`.git/worktrees/<name>/`, not `.git/`, so resolve it with `git rev-parse --git-path` rather
than assuming.

### The markup loop

Each stop is one round of: they mark up → you apply → they review → advance.

1. **They mark up the working tree**, leaving `CLAUDE` comments in the code where they want
   something changed. Treat each one as an instruction about the code around it.
2. **On "next", apply every marker** — make the change, delete the marker comment, and amend
   into the current commit. Never let a marker survive into a commit.
3. **Stop and report.** They review the amended commit before it's final.
4. **Only advance when they say so**, with `git rebase --continue`, then announce the new
   position.

"Next" means *apply and stop*, not *apply and move on*. Advancing on your own costs them the
review they asked for, and the commit is already rewritten by the time they notice.

Find markers across the whole tree, not just the files you expect:

```bash
git grep -n 'CLAUDE'
```

Amend without reopening the message unless they asked for a message change:

```bash
git add -A && git commit --amend --no-edit
```

### What to watch for

- **An edit at commit N may need the same change at N+1.** A later commit can re-add or
  overwrite the lines you just changed, silently reverting the edit. When the rebase reaches
  it, check whether the markup still holds, and say so rather than letting it regress.
- **Conflicts on `--continue` are normal** once you've changed an early commit. Resolve them
  in favour of the edit you just made, and never resolve by taking the later commit wholesale
  without reading it.
- **Run the per-commit gate on the amended commit** before advancing, so a broken commit is
  caught at the stop that caused it rather than at the end of the sweep.
- **The final tree is no longer expected to match.** This pass changes code on purpose, so
  the byte-identical invariant from the regrouping procedure does not apply — check the
  intended change instead: diff the finished branch against the pre-pass tip and confirm
  every hunk traces back to a marker.
- **Leaving the rebase half-done strands the branch** in a detached rebase state. If they
  stop mid-pass, say so explicitly and name the escape hatch (`git rebase --abort`, or the
  backup branch) rather than leaving it implicit.

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
- Reconstructing a commit's file by starting from the final version.
- Every commit passed on the first try and you never watched the harness report a failure.
- Squashing to hit a number the user named, past the point where ideas are still separable.
- Presenting a commit with `git show` when they asked to go commit by commit — position the
  worktree at it instead.
- About to `git rebase --continue` before they have reviewed the commit you just amended.

## Common Mistakes

| Mistake | Consequence |
|---|---|
| Classifying by commit subject alone | Fixups get kept, real ideas get merged |
| Rewriting code during the rebase | The diff no longer matches what was reviewed; the invariant check fails and you can't tell why |
| Folding everything into one commit because it's easier | Reviewer loses the build-up; large PRs become unreviewable |
| Testing only the final commit | Broken intermediate commits survive and poison bisect |
| Reconstructing a file backward from the final state | Untouched functions move; half the diff is the reviewer reading the same body twice |
| Skipping the backup branch | A botched rebase costs the whole branch instead of one `git switch` |
| Reading a commit out from the tip instead of stopping at it | They see the final file, `HEAD~1` is the wrong commit, and you argue about where you are |
| Advancing past a stop without their review | The commit is rewritten before they can object, and undoing it means another rebase |
| Force-pushing a branch someone else has pulled | Their work is silently orphaned |
