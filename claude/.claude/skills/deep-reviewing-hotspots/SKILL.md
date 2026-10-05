---
name: deep-reviewing-hotspots
description: Use when a PR needs line-by-line scrutiny concentrated where it matters — after a design comparison has flagged divergences, or when asked to "dig into the risky parts", "deep review", or "check what this change breaks downstream".
---

# Deep-reviewing hotspots

A picker chooses the places that most need a close look — contested divergences, risky
code, and code **outside the diff** that the change reaches — each with specific questions.
One reviewer per place answers them and reports findings only with a concrete failure
scenario; one refuter attacks each finding and it survives only if the refuter fails. Then
a completeness critic asks what nobody has examined yet, and the loop repeats until the
critic returns nothing (cap: `max_rounds`, default 2, at most 5 places a round). Hitting
either limit never drops work silently: places over the per-round limit, plus one final
critic pass at the round cap, come back unreviewed in `to_review` — what the review thinks a
human should still look at, with the questions to ask there.

## Inputs

`<run_dir>/brief.json`, `<run_dir>/adjudicated.json` (from comparing-to-design), and a head
checkout of the PR. Standalone without a comparison, hand-write `adjudicated.json` as
`{"adjudicated": []}` and the picker works from risk alone.

## Running it

Read `workflow.js` from this skill's directory and pass its contents as `script`:

```
Workflow({script: <workflow.js>, args: {rules, skill_dir, run_dir, brief_path,
          adjudicated_path, pr_url, title, head_dir, base_sha, head_sha}})
```

`rules` is blind-design-review's `prompts/rules.md`; `skill_dir` is this skill's directory.

**Output:** `<run_dir>/findings.json` `{upheld[], to_review[], refuted[], reviewed[], capped}`; the
workflow returns the same.

## Role files

| File | Role |
|---|---|
| `prompts/hotspots.md` | pick places (first pass) or find gaps (critic) |
| `prompts/deep-reviewer.md` | answer the questions at one place, report findings with scenarios |
| `prompts/refuter.md` | try to refute one finding |
