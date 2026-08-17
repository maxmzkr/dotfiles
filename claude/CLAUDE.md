# claude

Stow package for Claude Code's user-level config. Symlinks into `~/.claude/`.

Everything here is generic — it carries no information about any particular
employer or codebase. Work-specific skills and fixtures live in the companion
`claudework` package, which stows into the same `~/.claude/` directories, so on a
machine with both the two halves interleave and neither knows the other exists.
Skills that would need a work-only reference file to make sense are wholly in that
package rather than split across the two.

## Contents

- `.claude/skills/` — user skills, available in every project.
  - `session-retro` is the meta one: run at the end of a session, it sweeps the
    conversation for friction (user corrections, environment gaps, wrong
    assumptions, procedures rebuilt from scratch) and files what survives its
    durability test onto a ladder of enforcement — memory → user instruction →
    skill → hook, each rung earned by the one below it visibly failing. It writes
    memories and `CLAUDE.md` edits on its own but only *proposes* skills and hooks,
    handing them to `superpowers:writing-skills` and `update-config`. Its test —
    "would knowing this at the **start** have helped, and is it still true next
    month on a different task?" — is what keeps it from recording the current
    task's diff back at itself.
  - `regrouping-commits` rewrites a branch's log from authoring order into review
    order, one idea per commit, and is mostly about not lying afterwards: its
    verification section covers the three ways a `git rebase --exec` harness
    reports success without proving anything.
  - `gh-stack` drives the `gh-stack` CLI extension for stacked branches and PRs.
- `.claude/hooks/` — hook scripts, registered in `settings.json` by **absolute
  path**, so this package must be stowed before Claude Code runs — a missing hook
  file makes every `Bash` call fail, not just the writes it guards.
  - `pr_body_check.py` (PreToolUse) holds a PR body to the conventions it encodes:
    a description written for a reviewer rather than a summary of the diff. Its
    tests and fixtures are real PR bodies, so they are not in this package; the
    hook itself is generic.
  - `git_events.py` (UserPromptSubmit + SessionStart) reports git operations run
    outside the session — commits, pulls, pushes, rebases, cherry-picks,
    checkouts. It reads the **reflog**, not git hooks: git already names the
    operation that moved each ref, so nothing needs installing per-repo and
    `core.hooksPath` stays free for other uses. Pushes are visible because
    remote-tracking refs get reflogs too. Per-session position markers live in
    `~/.cache/claude/git-events/<session>/`, so a fresh session baselines silently
    instead of replaying old history.
  - `commit_trailer_check.py` (PreToolUse) denies any commit whose message carries
    a Claude attribution trailer, covering `git commit`/`merge`/`revert`/
    `cherry-pick` and the GitHub MCP tools that write commits. It denies
    **indefinitely**, unlike `pr_body_check.py`'s soft tier, because the trailer
    comes from a system-prompt instruction that re-fires on every attempt — a tier
    that yields would just let it through on retry. `git commit --amend` with no
    new message is exempt: it reuses a message that already exists, and the
    trailer-bearing commits already on this repo's main are kept deliberately.
    Escape hatch: `COMMIT_TRAILER_CHECK=off`.

  Tests: `python3 -m unittest discover` in the hooks directory (stdlib
  `unittest`, no pytest — they drive real repos in temp dirs). Run it against the
  stowed `~/.claude/hooks/`, not this package, or the `pr_body_check` tests are
  missing.
- `.claude/CLAUDE.md` — user-level instructions loaded in every project (Go test
  conventions and the no-attribution-trailer rule live here). Distinct from this
  file, which stows to `~/CLAUDE.md` and documents the package.
- `.claude/settings.json` — shared settings. `settings.local.json` stays untracked.
  Beyond the script hooks above it carries the **waiting notifier**: `Stop` (turn
  ended) and `Notification` (permission request or idle) each play a sound —
  `bell.oga` vs `window-attention.oga`, so "done" and "blocked" are
  distinguishable without looking — and set the tmux session option
  `@claude_waiting`, which `tmux/.tmux.conf` renders in `status-right` for every
  session at once. `UserPromptSubmit` and `SessionStart` clear it, so the marker
  survives you switching into the session and only goes away when you actually
  reply (`SessionStart` covers a crashed session leaving a stale flag). These are
  inline shell one-liners rather than files in `hooks/` on purpose: each is
  `[ -n "$TMUX_PANE" ] && tmux ... 2>/dev/null; true`, which cannot fail, whereas a
  missing script on `UserPromptSubmit` would reject the prompt — the same fragility
  the absolute paths above have. `TMUX_PANE` is inherited from the pane Claude Code
  was started in, so each session flags itself with no bookkeeping.

Everything else in `~/.claude/` — session transcripts, `file-history/`,
`shell-snapshots/` — is machine-local churn (~280MB) and deliberately not tracked.
Stow folds at the deepest unique level, so a tracked subdirectory becomes a symlink
while the transcripts beside it stay local. Once both packages are stowed, `hooks/`
and `skills/` are unfolded into real directories with per-file symlinks — that's
expected, not damage.

**Don't restow this package while Claude Code is running.** `stow -R` unlinks every
file and relinks it, so there is a window with no `hooks/pr_body_check.py` on disk —
and a hook registered by absolute path that isn't there makes every tool call fail,
including the ones needed to fix it. Restow from a shell outside Claude Code. Older
stow versions also refuse to restow once two packages share `hooks/` and `skills/`,
erroring with `unstow_contents() called with invalid target`; unfolding those two
directories by hand (a real directory of per-file symlinks) is what stow would have
produced anyway, and it resolves the error.

