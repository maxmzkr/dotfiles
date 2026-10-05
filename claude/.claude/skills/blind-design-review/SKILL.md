---
name: blind-design-review
description: Use when asked whether a pull request's implementation is reasonable, what it should have done, or whether its approach holds up — "is this PR reasonable", "review the approach", "deep review", "blind review", "would we have built it this way" — rather than a line-level bug hunt over the diff.
---

# Blind design review

A diff review anchors on the author's solution: every reviewer reads the change first and
inherits its framing. This review designs the change independently, **without seeing it**,
then judges the PR against that design and digs into where they differ and where the change
reaches beyond its diff.

**Fully automated. Never ask the user a question** — not to resolve ambiguity, not to
confirm a phase. Ambiguities become recorded assumptions, and the report surfaces them.

## Phases

Run these skills in order. Each is one Workflow call; each writes its artifact to the run
directory, and the next reads it from there.

| # | Skill | Sees the PR? | Writes |
|---|---|---|---|
| 1 | extracting-pr-requirements | yes | `brief.json` |
| 2 | blind-designing | **no** | `design.json` |
| 3 | comparing-to-design | yes | `adjudicated.json` |
| 4 | deep-reviewing-hotspots | yes | `findings.json` |
| 5 | report (below) | yes | `report.md` |

The brief is the only thing that crosses into phase 2, which is why phase 1 scrubs it of
the change's mechanism. Every role file is read together with `prompts/rules.md` here —
read-only, never ask, trace past the changed lines, blind roles stay blind.

Expect roughly 25–40 agents. Loops are capped (`max_rounds`, default 2) and every cap is logged
and carried into the report. **It is still expensive.** The first version (3 judges
per divergence, 3 refuters per finding, 3 design writers, 3 rounds) spent ~1.1M subagent
tokens on phases 1–2 and ~50 judges in phase 3's first round before being stopped at ~30%
of a 4-hour usage window. Fan-out was then cut: only contested divergences are judged, by
one judge, at most 6 a round; one refuter per finding; blind designing goes straight from
3 solvers to the reference; 2 rounds by default. Run it on PRs whose approach is genuinely
in question, not as a default review.

## Setup

```bash
gh pr view <PR> --json url,title,baseRefName,headRefOid
git fetch origin <baseRefName> <headRefOid>
BASE=$(git merge-base origin/<baseRefName> <headRefOid>)
RUN=<scratchpad>/bdr-<PR>; mkdir -p "$RUN"
git worktree add --detach "$RUN/base" "$BASE"          # the blind phase's only code
git worktree add --detach "$RUN/head" <headRefOid>
```

Common args for every phase: `rules` = `<this skill's dir>/prompts/rules.md`, `run_dir` =
`$RUN`, `pr_url`, `title`, `head_dir` = `$RUN/head`, `base_dir` = `$RUN/base`, `base_sha`,
`head_sha`. Each phase also takes `skill_dir` = **that phase skill's** directory, plus the
artifact paths its SKILL.md lists. Pass `max_rounds` only if the user asked for more or
less depth. Use absolute paths throughout.

## Running a phase

Load the phase skill, Read its `workflow.js`, and pass the contents as `script` (Workflow
won't read a `scriptPath` outside the working directory). When it returns, confirm its
artifact exists in `$RUN` before starting the next phase. If a phase fails, rerun it with
the `scriptPath` and `resumeFromRunId` the failed call returned — finished agents come back
from cache.

## Report

Dispatch one subagent: "Read `<this skill's dir>/prompts/rules.md`, then
`<this skill's dir>/prompts/report.md`, and follow them. Run directory: `$RUN`. Head
checkout: `$RUN/head`." Then Read `$RUN/report.md`, show it to the user, and name the run
directory — `design.json` is often the most useful thing for the author to read. Remove both
worktrees (`git worktree remove --force`). Don't post anything to GitHub unless asked.

## Common mistakes

- **Leaking the implementation into phase 2.** Blind agents get the brief and the base
  checkout, nothing else. "For context, here's the PR" turns the run into a slow diff review.
- **Treating the reference design as correct.** It's a yardstick; `design_wrong` exists
  because the author often knows something the designers didn't.
- **Stopping to ask.** Pick a reading, record it, continue.
- **Reporting refuted findings.** Only findings the refuter failed to break reach the
  Findings section.
