---
name: review-comments
description: >-
  Review the code comments on the added/changed lines of a diff against a
  rulebook of what makes a comment worth keeping, and remove or rewrite the ones
  that fail. Judges only comments inside the diff so the change never grows.
  Removes clear violations autonomously and asks the user only when it genuinely
  cannot tell whether a comment states something obvious to a human. Use when
  asked to "review comments", "clean up comments", "remove unnecessary
  comments", "check my comments", or after writing code to self-audit comment
  noise. Accepts a review request (files, a branch/commit range, or "this diff";
  defaults to the current working diff).
---

# Review comments

Iterate through the comments a diff introduces and judge each one against
`references/rules.md`. Keep what earns its place; delete or tighten the rest.
The bar is **less is more** — a comment must justify its existence, and the
default when a comment adds nothing is to remove it.

## Core constraints

1. **Only comments inside the diff.** Judge a comment only if it sits on a line
   the diff **adds or modifies**. Never touch a comment on an unchanged line,
   even in a changed file, even if it's bad — editing it would enlarge the diff,
   which defeats the purpose. If you spot a pre-existing comment worth changing,
   mention it in the summary; don't edit it.
2. **Don't grow the diff.** The only edits this skill makes are deleting or
   shortening comments that the diff itself introduced (and fixing the
   whitespace that deletion leaves behind). Never add new comments here.
3. **Autonomous on clear violations; ask rarely.** Remove or rewrite a comment
   without asking when a rule clearly applies. Use `AskUserQuestion` **only**
   when the judgment hinges on something you can't determine — most often
   whether a comment states something obvious to a human reader (see the "When
   to ask" rule). When you do ask, batch questions rather than interrupting per
   comment.
4. **Rewrite is a valid outcome.** A comment isn't only keep-or-delete. If the
   content is worth having but restates the code or buries the point, tighten it
   instead of removing it.

## Procedure

1. **Resolve the scope.** From the args:
   - "this diff" / nothing → the current working diff: `git diff HEAD` (include
     staged). This is the default.
   - A branch or range (e.g. `main`, `origin/main...HEAD`) → diff against it.
   - Named files → the diff for just those paths.
   Get the added/changed lines with `git diff` (not the whole file) so you only
   ever consider in-diff comments. Use the `+` lines and their line numbers.

2. **Collect the candidate comments.** From the added/changed lines, list every
   comment — whole-line comments and trailing (end-of-line) comments, in every
   language present (`//`, `#`, `--`, `/* */`, `{{/* */}}`, docstrings, YAML
   `#`, etc.). A comment counts as in-diff if the comment text is on an added or
   modified line.

3. **Judge each against `references/rules.md`.** Work through the candidate list
   from step 2 **in order, one at a time**, and record a verdict for every entry:
   **keep**, **delete**, **rewrite**, or **ask**. Read the rulebook fresh each
   run — it is the source of truth and grows over time. Apply the general
   principle (*a comment must add something the code and its names don't already
   convey*) even for cases no specific rule names yet.

   **Every candidate gets a verdict, including the ones you keep.** Skipping a
   comment and keeping a comment look identical in the output, so a comment you
   never considered is indistinguishable from one you decided about — that is how
   a review silently misses something. If the list is long, judge it in batches,
   but do not finish step 3 with fewer verdicts than candidates.

4. **Fetch voice exemplars for the rewrites.** For each comment whose verdict is
   **rewrite**, describe in one line what the code presents — not what the comment
   should say — and ask for exemplars:

   ```bash
   python3 ~/.claude/skills/learning-comment-voice/scripts/voice_query.py \
       --language go --placement block --situation "<one line>"
   ```

   Read them as register: sentence length, how much context is assumed, whether the
   reason leads or trails. They are not templates, and none is about this code.

   Empty output is the normal early state and means nothing is wrong — rewrite as
   you otherwise would. Never block a rewrite on a missing corpus, a missing script,
   or an empty result.

   Verdicts of keep and delete skip this entirely: whether a comment should exist is
   `rules.md`'s question, and no exemplar answers it.

5. **Apply the clear ones.** Edit the delete/rewrite decisions you're confident
   about. When deleting a whole-line comment, remove its line and any now-orphaned
   blank line it leaves. When deleting a trailing comment, keep the code.

6. **Ask about the genuine unknowns.** Collect the comments where you can't tell
   (typically: is this obvious to a human, or does it capture domain knowledge a
   reader wouldn't have?) and ask the user in one batched `AskUserQuestion`.
   Apply their answers. If the user explains *why* a comment should stay or go,
   consider whether that reasoning is a new general rule — see step 8.

7. **Report.** One row per candidate from step 2 — comment (truncated) ·
   file:line · decision (kept / deleted / rewritten / asked) · what drove it.
   A keep or a delete cites a rule; a **rewrite** cites the exemplars or the
   surrounding file, never a rule — whether a comment exists is the rulebook's
   question, how the replacement reads is the corpus's.

   **The table must have as many rows as the candidate list had entries**;
   state that count, so a dropped comment is visible as a missing row rather
   than as silence. Kept comments are rows too — "kept, adds the non-obvious
   why" is a result. Note separately any out-of-diff comments you deliberately
   left alone.

   If the diff is large enough that a full table is unwieldy, group the kept rows
   ("11 per-test scenario comments in foo_test.go: kept, non-obvious why") but
   keep the count honest — never omit a candidate entirely.

8. **Grow the rulebook (when warranted).** If the user's answer in step 6, or
   explicit feedback, establishes a reusable principle not already covered, add
   it to `references/rules.md` as a new numbered rule with a one-line rationale
   and, ideally, a tiny before/after example. Don't restate existing rules; keep
   each rule crisp. Only edit the rulebook when the user has effectively endorsed
   the principle — don't invent rules unilaterally.

## Notes

- This is about comment *noise*, not correctness. Don't hunt for bugs here.
- Match the surrounding comment density. A file that is heavily commented by
  convention (or a public API with doc comments) is a different bar than an
  internal helper — the rulebook's "less is more" still applies, but doc
  comments that document contract/behavior for callers are legitimate.
- When a comment is factually wrong or stale relative to the new code, that's a
  delete-or-fix regardless of style.
