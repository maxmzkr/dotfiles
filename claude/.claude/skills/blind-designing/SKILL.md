---
name: blind-designing
description: Use when a change should be designed independently of any existing implementation — to get an unanchored yardstick for judging a PR, or several independent takes on how to build something from a written brief or ticket — "design this blind", "how would we build this from scratch", "what should this have looked like".
---

# Blind designing

Three solvers design from a brief and the base code only, each under a different lens
(**minimal**, **robust**, **operable**). One synthesizer aligns their decision points and
resolves them into a reference design that is generous about acceptable choices and strict
only about invariants. Nobody in this phase sees an implementation, and nobody asks the user anything.

## Inputs

- **A brief** at `<run_dir>/brief.json`: `{problem, requirements[], assumptions[],
  relevant_code[]}`. extracting-pr-requirements produces one from a PR; standalone, write
  it yourself from the ticket or request — outcomes, not mechanisms.
- **A base checkout** the solvers are confined to: a detached worktree at the commit to
  design against. Blindness is only as good as this confinement — never point `base_dir`
  at a checkout that contains the implementation.

## Running it

Read `workflow.js` from this skill's directory and pass its contents as `script`:

```
Workflow({script: <workflow.js>, args: {rules, skill_dir, run_dir, brief_path,
          base_dir, base_sha}})
```

`rules` is the absolute path to blind-design-review's `prompts/rules.md`; `skill_dir` is
this skill's directory.

**Output:** `<run_dir>/design.json` (written by the synthesizer); the workflow returns
`{design, solutions}`. Check the file exists before moving on.

## Role files

| File | Role |
|---|---|
| `prompts/solver.md` | blind solution under one lens |
| `prompts/reference.md` | align decision points and synthesize the reference design |
