---
name: session-retro
description: >-
  Look back over the session and turn what was learned into durable memories,
  user-level instructions, and skills, so the next session starts further ahead.
  Writes memories and CLAUDE.md edits autonomously; proposes skills and hooks and
  waits for approval. Use at the end of a session, or when asked to "run a retro",
  "what did we learn", "update your memories", "save what you learned", "should
  this be a skill".
---

# Session retro

Read the session back and ask what should have been known at the **start** of it.
Whatever answers that question gets written down; everything else is discarded.

The output per finding is a user-level instruction, a project memory, a skill, a
hook, or an edit to one of those that already exists.

These form a ladder of enforcement, and where a finding lands depends on how much
it needs to be *guaranteed*. A memory informs; an instruction directs; a skill
supplies a procedure on demand; a hook is the only one the harness enforces whether
or not it was recalled. Start at the cheapest rung that could work.

## The durability test

Every candidate passes both halves or it is dropped:

1. **Would knowing this at the start of the session have saved time or avoided a
   wrong turn?**
2. **Will it still be true next month, on a *different* task in this project?**

This is the whole skill. The categories below are just where survivors get filed.

**Always reject:**

- Facts about the code this task touched — what a function now does, what the fix
  was, which files changed. That is what the diff and the commit message are for.
- Anything recoverable by reading the repo, `git log`, or the existing `CLAUDE.md`
  files. A memory that restates documentation is worse than no memory, because it
  will drift out of sync with the thing it copies.
- One-off decisions with no rule behind them ("we named it `exporter`"). If there
  *is* a rule behind it, record the rule, not the instance.
- Narration of the session ("we debugged the flaky test and fixed it"). Nobody
  reads that later.

**The signal to look for is friction, not accomplishment.** A retro that lists what
went well has found nothing. What earns a memory is the thing that cost time:

- The user corrected something, pushed back, or had to say it twice.
- A command failed for an environmental reason and needed a non-obvious fix.
- An assumption turned out wrong, and the correct model isn't written anywhere.
- A procedure had to be reconstructed from scratch that had clearly been run before.

## Core constraints

1. **Read the current state before judging anything.** Existing memories and
   instructions are the baseline; a candidate can only be evaluated against them.
   Do this first, every run — not after drafting.
2. **Updating beats creating.** When a finding touches something already recorded,
   edit that file. Two memories on one subject are worse than one, because neither
   is authoritative and the reader has to reconcile them.
3. **Delete what turned out to be wrong.** A memory contradicted by this session is
   not left alongside its correction — it gets fixed or removed.
4. **Memories are written without asking; skills are proposed.** A memory is cheap
   to change and scoped to one fact. A skill changes how future work is done and is
   a much bigger artifact — it gets a yes first.
5. **Finding nothing is a valid, common outcome.** Most sessions teach nothing
   durable. Say so and stop. Do not pad the run with marginal entries — the value of
   the memory directory is inversely proportional to how much junk is in it.

## Procedure

1. **Load the baseline.** Read, in this order:
   - `~/.claude/CLAUDE.md` — the user-level instructions (a symlink into
     `~/dotfiles/claude/.claude/CLAUDE.md`).
   - The project's `~/.claude/projects/<mangled-path>/memory/MEMORY.md` and every
     file it indexes. The path is the project's absolute path with `/` → `-`, so
     `/home/max/pipeline` → `-home-max-pipeline`. If the directory is empty or
     absent, the baseline is empty — that's fine.
   - The repo's own `CLAUDE.md` files, so nothing already documented gets copied
     into a memory.
   - `ls ~/.claude/skills/` and the plugin skill list, so an existing skill isn't
     proposed a second time under a new name.

2. **Sweep the session for friction.** Walk the conversation for the four signals
   above. Collect them as raw observations with the evidence attached — what was
   said or what failed. Don't classify yet.

3. **Apply the durability test** to each observation. Expect to drop most of them.

4. **Route each survivor.**

   - **User preference** — a standing instruction about how to work that isn't
     specific to this repo (tooling choices, style rules, what not to do). Goes in
     `~/dotfiles/claude/.claude/CLAUDE.md` as a `##` section, matching the existing
     ones: the rule first, then *why*, in prose. **Edit the dotfiles path, not the
     `~/.claude/` symlink**, so the change shows up in `git status` there.

   - **Project fact** — true of this repo, not of the user. Goes in the project's
     `memory/` directory as one file holding one fact, using the established
     frontmatter (`name`, `description`, `metadata.type` of
     `user` / `feedback` / `project` / `reference`). For `feedback` and `project`,
     follow the body with **Why:** and **How to apply:** lines. Link related
     memories with `[[slug]]`. Add a one-line pointer to `MEMORY.md`:
     `- [Title](file.md) — hook`.

   - **Skill candidate** — hold for step 6. See the bar below.

   - **Hook candidate** — hold for step 6. The trigger is a rule that was *already
     recorded* and got violated anyway, or a mistake whose cost is high enough that
     catching it after the fact is too late. See the bar below.

   - **Contradiction** — edit or delete the existing memory, instruction, or skill.
     This isn't a separate category so much as what happens when a survivor lands on
     ground that's already occupied.

5. **Write the memories and instructions, then report.** A short list: what was
   written or edited, which file, and the one-line reason. Include what was
   considered and dropped only if the user asks.

6. **Propose skills and hooks, then stop.** For each candidate, state what it would
   do and the evidence from this session that it recurs — for a skill, the phrases
   that should trigger it; for a hook, the event, the matcher, and whether it warns
   or denies. Then wait.

   On approval: skills go to `superpowers:writing-skills`, which authors the
   SKILL.md — don't hand-roll one here. Hooks go to the `update-config` skill for
   registration in `settings.json`. If an existing skill or hook already covers the
   ground, propose an edit to it rather than a second one.

## The bar for a skill

A procedure is a skill only if all three hold:

- **Multi-step**, with ordering or gotchas that are easy to get wrong.
- **Non-obvious** — it would be reconstructed incorrectly, not just slowly.
- **Recurring** — there's real reason to think it happens again.

One-time work is not a skill no matter how involved it was. A single command with
flags is not a skill; it's a memory, or a shell alias. When something is on the
line, prefer the memory — it's cheaper to write, cheaper to delete, and can be
promoted to a skill later once it has actually recurred.

## The bar for a hook

A hook is the right answer when **remembering isn't enough**. Two situations
qualify:

- **A written rule was violated anyway.** The instruction existed, was in context,
  and still didn't fire. Writing it down harder won't help — the model is the
  unreliable part, so the check has to live outside it. `commit_trailer_check.py`
  exists because the trailer instruction re-fires from the system prompt every
  session and no amount of user-level text reliably beats it.
- **The mistake is expensive or hard to undo** — something pushed, published, or
  destructive. A memory catches it on the next session; a `PreToolUse` hook catches
  it before it happens.

Because a hook is executable and runs on every matching call, propose it with the
failure mode spelled out:

- **Deny or warn?** Deny only when there is no legitimate case for the thing.
  Prefer a soft tier that yields on retry, *unless* the rule is fighting a
  system-prompt instruction that will just re-fire — then a soft tier is no tier at
  all.
- **What is the escape hatch?** Every deny hook needs an env-var override.
- **What does it cost when it breaks?** A hook registered by absolute path takes
  down every matching tool call if the file goes missing. Say so out loud.
- **How is it tested?** Hooks in this repo have `test_*.py` next to them, driven by
  stdlib `unittest`. A proposed hook comes with tests or it isn't ready.

Don't propose a hook for something a memory has never actually failed to prevent.
The ladder goes memory → instruction → skill → hook, and a rung is earned by the
one below it visibly failing, not by guessing it will.

## Notes

- Scope defaults to the current session. If the user names a narrower scope ("just
  the deploy stuff"), respect it.
- Memories written from a retro are indistinguishable from ones written in the
  moment — same format, same directory. This skill is a sweep for what got missed,
  not a parallel store.
- If the same observation keeps surfacing across retros and keeps failing the
  durability test, that's a signal the test is wrong for this case, not that the
  observation should be forced through. Raise it with the user instead.
