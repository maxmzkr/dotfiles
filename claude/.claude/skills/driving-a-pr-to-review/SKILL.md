---
name: driving-a-pr-to-review
description: Use when an open PR needs to get from "just pushed" to "reviewers pinged" — watching CI to green, rerunning failures the PR didn't cause, requesting reviewers Max names, and posting the review ask in Slack. Triggers on "hand hold", "handhold", "watch CI", "babysit this PR", "get this reviewed", "ping X for review", "is CI green yet", or right after `gh pr create`. Also triggers on any request to request a reviewer, take a PR out of draft, or post a review ask — including one that dictates the exact reviewer, channel and message text. Spelled-out final steps are still this skill's last two stages, not a standalone errand.
---

# Driving a PR to review

Four stages, strictly in order: **watch → green → reviewers → Slack.**

The ordering is the whole point. A reviewer pinged on a red PR reviews code that is
about to change, and a Slack ping sent before the review request lands leaves people
looking at a PR that isn't asking them for anything. **Never request review before CI
is green. Never post to Slack before `reviewRequests` actually lists the people.**

## Stage 1 — Watch CI in the background

Arm a `Monitor`, don't sit in a blocking `gh pr checks --watch`. The monitor emits a
line per check that lands non-green and one summary line at the end, then exits.

```bash
PR=<number>
prev=""
while true; do
  s=$(gh pr checks "$PR" --json name,bucket,link 2>/dev/null)
  [ -n "$s" ] || { sleep 30; continue; }          # empty = API hiccup, NOT success
  cur=$(jq -r '.[] | select(.bucket=="fail" or .bucket=="cancel") | "\(.bucket)\t\(.name)\t\(.link)"' <<<"$s" | sort)
  comm -13 <(printf '%s\n' "$prev") <(printf '%s\n' "$cur")
  prev=$cur
  if jq -e 'all(.bucket!="pending")' <<<"$s" >/dev/null; then
    jq -r '[group_by(.bucket)[] | "\(.[0].bucket)=\(length)"] | "DONE " + join(" ")' <<<"$s"
    break
  fi
  sleep 30
done
```

- `timeout_ms: 1800000` (the max), and **re-arm on expiry** — a full matrix can
  outlive one window.
- `gh pr checks` **exits non-zero whenever any check is failing.** Never gate the loop
  body on its exit status (`|| continue` skips exactly the iteration that had news).
  Test the output for emptiness instead, as above.
- Don't emit `pass` lines — 25 checks of noise buries the two that matter. The `DONE`
  line carries the counts, so silence is never mistaken for success.

## Stage 2 — Classify a failure before rerunning

Read the log first. `gh run rerun` on a real breakage wastes ten minutes and tells you
nothing you didn't know.

```bash
gh run view <run-id> --log-failed | tail -60
```

| Signature | Verdict |
|---|---|
| Runner lost, `The operation was canceled`, image pull, network/DNS, 5xx from a registry | **Unrelated** — rerun |
| A test in a package your diff doesn't touch, failing the same way on `main` | **Unrelated** — rerun, and say so in the report |
| A test or lint on a path in `git diff --name-only origin/main...HEAD` | **Yours** — stop |
| A check that fails identically on two consecutive runs | **Yours**, whatever the message says — stop |

Rerun the failed jobs only:

```bash
gh run rerun <run-id> --failed
```

**Rerun budget: two per job.** After that, report rather than rerun again.

**Not every check is an Actions run.** A check posted by a GitHub App can't be rerun
with `gh run rerun` — its `link` isn't a `github.com/.../runs/` URL, which is how you
tell. Retry it the way its app says (often a PR comment), or say it's red and hand over
the link rather than inventing a retry. If `references/checks.md` exists, read it here:
it names the app checks this repo runs and how each one is retried.

**When you stop, follow the failed-CI rule**: the `actions/runs/...` URL plus the quoted
error line, and check whether the failure is even yours before reporting it as a break.

## Stage 3 — Request reviewers

CI green, then ask: **"who should review?"** Max answers with names, not logins.

**Run `./pr-ready.sh <PR> <login,login>` rather than the commands below by hand.** It
re-checks CI, flips the draft, adds the reviewers and reads `reviewRequests` back,
refusing at the first unmet condition with a nonzero exit. It prints `gate: READY` only
when stage 4 may go out. Use it even when Max dictates the reviewer and the Slack text —
**especially** then, because a request that names only the last steps is the one that
skips the first two. The steps it automates, for when you need to know what it checks:

1. Resolve each name through `references/directory.json` (see below).
2. **Take the PR out of draft**: `gh pr ready <PR>`. Every PR here is opened `--draft`,
   and a draft PR cannot be reviewed — requesting review on one asks for something
   GitHub won't let people give. This is the moment it flips, not `gh pr create` time.
   (A PR showing "Not ready for review" in the merge box is *not* the same thing as a
   draft; `gh pr view --json isDraft` is the only answer that counts.)
3. Add them: `gh pr edit <PR> --add-reviewer <login1>,<login2>`
4. **Verify it took.** `gh` exits 0 while silently dropping a login it doesn't
   recognize — which is how a PR sits for a day with nobody assigned:

```bash
gh pr view <PR> --json reviewRequests --jq '.reviewRequests[].login'
```

Every login you asked for must appear. One missing means the handle is wrong — go back
to the directory step, fix the entry, don't just retry the same string.

A PR that already has the right reviewers and is already out of draft needs no second
request; skip to Slack.

## Stage 4 — Post the Slack ask

Only once `pr-ready.sh` has printed `gate: READY`. A Slack message cannot be unsent, so
it is the one step with no recovery — it goes last, after the gate, never on a promise
that CI will be green shortly. Resolve the channel through the directory, then
`slack_send_message`.

**The message is only ever Max's own text, posted verbatim.** Never compose one. If he
has not given the words, ask him for them — do not draft a suggestion, do not fill a
template. When he has, the only edits allowed are turning `@name` into the Slack mention
(`<@ID>` from the directory) and a link placeholder into the PR URL: no prefix, no
reordering, no added clause, no punctuation changes.

If the channel isn't in the directory, ask which one and record the answer.

## The directory — `references/directory.json`

Max says names; GitHub and Slack want handles, and the two rarely match ("Sam" might be
`example-sam-gh` on GitHub and `@sam` on Slack). The file is the accumulated mapping, and
it is meant to grow every time it misses. It may not exist yet — create it on the first
miss.

```json
{
  "people":   { "sam": {"github": "example-sam-gh", "slack": "@sam"} },
  "channels": { "infra": "#team-infra" }
}
```

Keys are lowercased first names or aliases; add an alias rather than a second entry.

**On a miss — a name or a channel that isn't in the file — do all three:**

1. Ask Max for the handle. Never guess a login from a name, and never "try the obvious
   one and see".
2. Verify it exists before writing it down: `gh api users/<login> --jq .login` (404 =
   wrong handle, ask again), and for a channel, that `slack_search_channels` returns it.
3. Append it to the file, and tell Max it changed — it is a tracked dotfiles file, so
   it needs a commit like any other change.

A verified handle written down once is a question never asked twice. Skipping step 3
because "it's just this once" is what keeps the file empty and the question recurring.

## Red flags

- Doing "request X" or posting the review ask without having run `pr-ready.sh` — a
  message that names only the last stages is not a smaller task, it is this one with
  the prerequisites left implicit.
- Rerunning without reading the log — you don't know what you're retrying.
- Gating anything on `gh pr checks`' exit status, or treating empty output as green.
- Requesting review while any check is `pending` or `fail`.
- Requesting review on a PR still in draft, or flipping it ready before CI is green.
- Posting to Slack without reading back `reviewRequests`.
- Any Slack text that is not Max's message word for word — a prefix, a reordered
  mention, a clause you thought helped, or a message he never gave you.
- Typing a login you inferred from a name instead of one the directory or `gh api`
  confirmed.
- Reporting "CI passed" from a monitor that only ever prints failures — quote the `DONE`
  line, which carries the counts.
