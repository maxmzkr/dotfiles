---
name: learning-comment-voice
description: >-
  Capture the comments Max writes by hand, and serve them back as exemplars
  before Claude writes a comment. Use when Max has just finished hand-editing a
  commit during an interactive commit walk and handed the diff back ("done",
  "I'm finished with this one"), and also whenever Claude is about to write or
  rewrite code comments and wants to match Max's voice rather than a generic
  register. Triggers on "capture my comments", "learn from these edits", "what
  would I have written here", or immediately after a rebase stop's edits land.
---

# Learning comment voice

Two jobs sharing one corpus. **Capture** records the comments Max writes by hand.
**Query** serves them back before Claude writes one. Neither calls the other; they
meet at `corpus/` on disk.

The corpus decides **how a comment reads**. `review-comments/references/rules.md`
decides **whether it exists at all**. Keep the two apart — phrasing written down as
rules becomes another style guide, which is the thing this replaces. `review-comments`
ships in the work-private `claudework` package, not in this skill's own `claude`
package — if it is not present on this machine, skip step 5's rulebook hand-off below
and just report the deleted comments instead.

## Capture

Run this when Max has hand-edited a commit and said he is done, inside an
interactive commit walk. That diff is by construction his own work, which is the
entire provenance argument — do not capture from a diff Claude produced.

1. **Get the diff of his edits.** At an edit stop that is `git diff`; at a conflict
   stop it is `git diff` against the resolution he approved. If Claude has edited
   the tree since he handed it back, stop — the provenance is gone, and a corpus
   entry that is really Claude's text poisons every retrieval that returns it.

2. **Extract candidates.**

   This skill runs while Claude is working in whatever project the commit walk is
   in, not in `~/dotfiles`, so nothing here may depend on the working directory.
   `PYTHONPATH` puts the scripts directory on the import path without `cd`-ing
   into it — the only thing a plain `cd` there bought was making `voice_extract`
   importable, and `PYTHONPATH` gets that without also making every other path in
   this file relative to somewhere the process usually isn't:

   ```bash
   git -C <repo> diff > /tmp/edits.diff
   PYTHONPATH=~/.claude/skills/learning-comment-voice/scripts python3 -c "
import dataclasses, json, voice_extract
voice, deleted = voice_extract.extract(open('/tmp/edits.diff').read())
json.dump(
    {'voice': [dataclasses.asdict(c) for c in voice],
     'deleted': [dataclasses.asdict(c) for c in deleted]},
    open('/tmp/candidates.json', 'w'), indent=2,
)
for label, group in (('voice', voice), ('deleted', deleted)):
    print(f'-- {label} ({len(group)}) --')
    for c in group:
        print(f'{c.path} [{c.placement}/{c.language}] {c.comment!r}')
"
   ```

   Two lists come back: comments he **added or rewrote**, and comments he
   **deleted**. The printed summary is what makes this step reviewable; the
   candidates themselves land in `/tmp/candidates.json`, because the Python
   process exits here and every step below needs fields the summary does not
   show — above all `code`.

   **Steps 3-6 read `/tmp/candidates.json`, never `/tmp/edits.diff`.** The diff
   still has the comments in it. Reconstructing `code` from it is how a comment
   reaches the subagent that must not see one, and `id` stops being reproducible
   the moment `comment` or `code` is retyped rather than copied.

3. **Describe each voice candidate comment-blind.** For each entry in the file's
   `voice` list, dispatch a subagent with that entry's `code` field — which
   already has the comment stripped — and this instruction:

   > Describe in one line what this code presents: what it does, and what about it
   > is non-obvious, constrained, or risky. Do not describe what a comment should
   > say. Return the line, then a single word from: why, warning, contract, domain,
   > pointer — whichever best names the kind of remark this code invites.

   **The subagent must never see the comment.** At query time there is no comment,
   so a description written with knowledge of one is better-aimed than anything the
   query side can produce — retrieval that tests well and degrades in use. Passing
   the stripped `code` field is what makes both ends the same function of the same
   input.

4. **Write the records.** One per voice candidate, via `voice_corpus.write_record`.
   `Record` has twelve fields and no defaults; here is where each one comes from:

   - `comment`, `placement`, `language`, `code`, `path` — copied verbatim from the
     candidate's entry in `/tmp/candidates.json`.
   - `description`, `kind` — the subagent's one-line description and its single
     classifying word from step 3.
   - `id` — `voice_corpus.record_id(comment, code)`, passed the same two strings
     the file holds. Never invent one; it is a deterministic hash of exactly those
     two fields, which is what lets a rerun of capture over the same edit land on
     the same file instead of duplicating it — and a `code` retyped by hand from
     the diff is a different string, so it lands on a second file.
   - `enclosing` — the name of the function, method, or type the candidate's `code`
     sits inside, if you can tell from that snippet; `None` when you cannot. The
     field is typed `str | None` for exactly this case — do not guess to avoid
     leaving it empty.
   - `repo`, `commit`, `captured` — from the current repository state (remote or
     directory name, the commit the edit landed on, and the capture timestamp).

5. **Take the deleted comments to the rulebook.** They are the file's `deleted`
   list, and they are not corpus entries. If `review-comments` is present on this
   machine and a deletion establishes a principle `references/rules.md` does not
   already carry, propose it there per that skill's step 8 — propose, do not add
   unilaterally. If `review-comments` is
   not present (it is work-private and may not be stowed here), skip the proposal
   and just report the deleted comments in step 7 below — they still are the
   signal, they just have nowhere to be filed on this machine.

6. **Record the run.** `voice_corpus.append_stats` with the added, rewritten, and
   deleted counts. Comment edits per commit-walk trending down is the only evidence
   this system does anything.

7. **Report what was captured**, comment by comment. A misattribution cannot be
   prevented at capture time — the only defence is Max seeing it immediately and
   deleting the file.

## Query

Before writing or rewriting a comment:

1. Describe the situation the code presents, in one line, **without reference to
   what you are about to say**. Same instruction as step 3 above — that symmetry is
   what makes retrieval work.

2. Ask for exemplars:

   ```bash
   python3 ~/.claude/skills/learning-comment-voice/scripts/voice_query.py \
       --language go --placement doc \
       --situation "a retry loop whose backoff cap tracks an upstream timeout"
   ```

3. **Read them as register, not as content.** They show sentence length, how much
   context is assumed, whether the reason leads or trails. They are not templates
   to fill, and none of them is about your code.

4. Empty output is the normal early state and means nothing is wrong. Write the
   comment as you otherwise would.

## After a capture run

Rebuild the index if the dependencies are installed:

```bash
python3 ~/.claude/skills/learning-comment-voice/scripts/voice_index.py
```

It prints `indexed 0 records` when `numpy`/`sentence-transformers` are absent,
which is the expected state today and costs nothing — the query path falls back to
returning the whole filtered corpus.

## Red flags — STOP

- Capturing from a diff Claude wrote, or from a tree Claude has touched since Max
  handed it back.
- Letting the describing subagent see the comment.
- Storing Claude's original comment text anywhere in a record.
- Writing a vector into a record — vectors are derived and live in the index.
- Adding a rule to `rules.md` that Max has not endorsed.
- Committing a corpus file, a `corpus/` directory, or a sample record into the
  dotfiles repo. The corpus is machine-local and untracked.
