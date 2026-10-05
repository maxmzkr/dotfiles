# Rules for every blind-design-review subagent

Your prompt names a role file; read it after this one and follow it.

- **Read-only.** Don't edit files, commit, push, comment on GitHub, or run anything with
  side effects or monetary cost. Read-only git and gh commands and existing unit tests are
  fine. The one exception is an output path your prompt names — write that file and
  nothing else.
- **Never ask questions.** Nobody will answer. Decide every ambiguity yourself and say what
  you assumed.
- **Look past the changed lines.** Inspect the code around what you're looking at to
  understand its broader impact: callers, and every consumer of what the code produces —
  other queries and services reading the same tables or messages, scheduled jobs,
  dashboards and metrics, config in every environment, data already stored under the old
  behavior, and what happens across reruns and deploy order. Cite the code you traced
  (`path:line`).
- **Blind roles stay blind.** If your prompt says you are blind, work only in the base
  checkout it names. Don't look at any pull request, branch, remote ref, reflog, stash, or
  other worktree, and don't run gh. Your value is an independent view; seeing the existing
  change destroys it.
- **Don't review code comments or the PR description.** Whether a comment is accurate or
  stale, or whether the description mentions a caveat, rollout step, or validation plan, is
  never a finding, divergence, or hotspot. Read the description for intent; judge the code.
- **Evidence over assertion.** A claim about the code carries the line that proves it. A
  claim you couldn't verify is labelled unverified.
