---
name: comparing-to-design
description: Use when an implementation needs judging against a reference design it was not built from — a blind design, a spec, or an RFC — to find where it diverges and whether each divergence is better, equivalent, or worse.
---

# Comparing to a design

Four comparers read the PR against the brief and the reference design, each through one
lens — **coverage** of requirements and invariants, **decisions** made, **impact** outside
the diff, and **extra** scope the design never anticipated. New divergences are deduped
against everything found so far. Ones the comparer rated `equivalent` or `impl_better`
keep that verdict; each contested one (`impl_worse`, `design_wrong`) gets one judge weighing
correctness, simplicity, and operations — at most 6 per round, the overflow logged. Rounds
repeat until one finds nothing new (cap: `max_rounds`, default 2; hitting it is logged and
recorded as `capped`).

The reference is a yardstick, not an oracle: `design_wrong` exists because authors often
know something the blind designers didn't.

## Inputs

`<run_dir>/brief.json` and `<run_dir>/design.json` (from extracting-pr-requirements and
blind-designing, or hand-written), and a head checkout of the PR.

## Running it

Read `workflow.js` from this skill's directory and pass its contents as `script`:

```
Workflow({script: <workflow.js>, args: {rules, skill_dir, run_dir, brief_path,
          design_path, pr_url, title, head_dir, base_sha, head_sha}})
```

`rules` is blind-design-review's `prompts/rules.md`; `skill_dir` is this skill's directory.

**Output:** `<run_dir>/adjudicated.json` `{adjudicated[], capped}`; the workflow returns the
same.

## Role files

| File | Role |
|---|---|
| `prompts/comparer.md` | find divergences under one lens |
| `prompts/dedupe.md` | keep only genuinely new divergences |
| `prompts/judge.md` | verdict on one contested divergence |
