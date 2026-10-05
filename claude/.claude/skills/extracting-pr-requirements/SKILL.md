---
name: extracting-pr-requirements
description: Use when the requirements behind a pull request need to be written down independently of how it was built — before designing or judging it blind, or when asked "what is this PR actually supposed to do", "what are the requirements here".
---

# Extracting PR requirements

Three readers pull requirements from a PR through different lenses — what the author
**stated**, what the diff's **behavior** implies, and what the surrounding **system**
demands that nobody wrote down — and one writer merges them into a brief that describes
outcomes without revealing the mechanism. Fully automated: ambiguities become recorded
assumptions, never questions.

Usually run by blind-design-review, which prepares the inputs. Standalone, prepare them the
same way (see that skill's "Setup").

## Running it

Read `workflow.js` from this skill's directory and pass its contents as `script` (Workflow
won't read a `scriptPath` outside the working directory):

```
Workflow({script: <workflow.js>, args: {rules, skill_dir, run_dir, pr_url, title,
          head_dir, base_dir, base_sha, head_sha}})
```

- `rules` — absolute path to blind-design-review's `prompts/rules.md`.
- `skill_dir` — absolute path to this skill's directory; agents read `prompts/*.md` from it.

**Output:** `<run_dir>/brief.json` (the brief writer saves it), and the workflow returns
`{brief, readings}`. Check the file exists before moving on.

## Role files

| File | Role |
|---|---|
| `prompts/reader.md` | one reader per lens: stated / behavior / system |
| `prompts/brief.md` | merge, resolve conflicts, scrub the mechanism out |
