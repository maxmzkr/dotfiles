# Comment rulebook

The rules for deciding whether a comment in a diff earns its place. This file is
the source of truth for the `review-comments` skill and **grows over time** —
add a rule when the user endorses a new principle (see SKILL.md step 7).

## Guiding principle

**Less is more.** A comment must add something the code and its names don't
already convey — intent, a non-obvious *why*, a warning, a contract. When a
comment adds nothing, the default is to remove it. When in doubt and the comment
is low-value, lean toward removing. Prefer rewriting to deleting when the content
is worth keeping but the phrasing restates the code or buries the point.

## Rules

1. **Don't restate what the code does.** If the comment is a prose translation
   of the line below it, delete it. The code already says it.
   - ✗ `// increment the counter` above `counter++`
   - ✗ `# loop over the users` above `for user in users:`

2. **Don't narrate the change you were asked to make.** Comments that explain an
   edit in terms of the request ("switched this to X", "now uses Y instead of Z",
   "per review feedback") are for the PR description, not the code.
   - **Exception — keep it if:** someone would likely make the same mistake again
     (a genuine footgun / non-obvious constraint that invites the wrong fix), or
     the new code is confusing enough that the *why* isn't self-evident. In those
     cases the comment should explain the underlying reason, not reference the
     request.
   - ✗ `// changed from map to slice because Max asked`
   - ✓ `// slice, not map: order matters here — the API replays these in sequence`
   - **Corollary — "not X" is still narrating the change.** Rewriting an edit
     note into a warning against the thing you replaced keeps the diff's frame:
     it documents what the code *stopped* being, not what it *is*. Naming the
     old value at all is the tell. Describe the current state and let the reason
     fall out of it. Reach for the ✓ form under rule 2's exception only when the
     rejected option is one a reader would arrive at independently, not merely
     the one that used to be there.
     - ✗ `// Not kube_job_status_failed: that counts failed pods, so it fires
       mid-retry` (the reader never saw that metric; this is the edit, restated)
     - ✓ `// The Failed condition is set only once backoffLimit is spent, so a
       Job still retrying does not appear here`

3. **Don't comment implementation details that don't matter to the programmer.**
   If a detail has no bearing on how someone reads, uses, or safely changes the
   code, leave it out.
   - ✗ `// uses a temporary variable to hold the result`

4. **Don't state what's obvious to the reader.** Assume a competent programmer
   familiar with the language and this codebase. Don't explain standard language
   features, well-known idioms, or things the surrounding context makes plain.
   This includes **tautologies** — a property that's true by construction, so
   the code structure already guarantees it. Naming the guarantee adds nothing;
   the construction *is* the guarantee. If the *why we built it this way* is
   non-obvious, comment that instead of the guaranteed outcome.
   - ✗ `// this is the constructor`
   - ✗ `// JSON marshalling can return an error` above standard error handling
   - ✗ `// same value in both places, so they can't drift` (one variable can't
     disagree with itself — that's what using one variable means)

5. **Don't guard against a mistake that was a slip, not a trap.** Rule 2's
   exception ("someone would likely make the same mistake again") requires the
   wrong path to be genuinely *tempting* — not merely that it was there before.
   A bug that was a typo or a brain-fart needs no comment defending the fix,
   because nobody would choose it deliberately. Ask whether a competent reader
   could plausibly prefer the wrong version; if not, the fix speaks for itself.
   Such a comment is worse than noise: warning against a move nobody would make
   implies a hazard exists, so the reader goes hunting for what they're missing.
   - The wrong path must be reachable from the code **as written**. A trap that
     only exists in a hypothetical rewrite warns against a road the reader isn't
     on. If the code doesn't do the risky thing and nothing on the page suggests
     it, the warning has no anchor.
   - ✗ `// sum/sum, not avg-of-per-pod-avgs, so one slow pod can't skew it`
     (nobody reaches for a mean of means on purpose)
   - ✗ `// embedding slog.Handler here would drop attrs on With()` on a struct
     that uses a named field and explicit methods — the reader never sees the
     embedded version, so the caution reads as a hazard they've failed to spot
   - ✓ `// slice, not map: order matters — the API replays these in sequence`
     (a map is the natural-looking choice here, and it silently breaks)

6. **When to ask instead of deciding (obviousness is reader-dependent).** "Obvious"
   depends on the reader's domain knowledge, which you may not share. If a comment
   might be encoding domain/business/operational knowledge that a human on this
   team would need — and you can't tell whether it's obvious-to-them or genuinely
   redundant — ask the user rather than deleting. You will often *know* it's
   redundant; only ask when you genuinely can't tell.

7. **Don't defend a choice against an alternative that isn't live in this
   codebase.** Naming a rejected option only helps if someone here might
   actually reach for it. Contrasting with a vendor, format, or library the
   project doesn't use answers a question nobody asked, and implies the dead
   option is still in play. Confirm the alternative is reachable from this repo
   before documenting why you avoided it. Note that a *deprecated* package still
   sitting in the tree is usually a dead alternative, not a live one.
   - ✗ `// hex trace IDs, not the decimal Datadog form` — in a project that
     doesn't send anything to Datadog
   - ✓ `// hex, not the decimal form the exporter writes` — only where that
     exporter is live and a reader might match it

8. **A function's doc is about inputs and outputs, not implementation.** The
   signature gives the types; the doc gives the contract — what the return
   *means*, what order it comes back in, what the flags say, what happens when
   there is nothing to return. Reasoning about the implementation (why this
   branch, why this structure, what would break if it changed) belongs *inside*
   the function, on the line it explains. Outside, it answers a question the
   caller isn't asking, and it goes stale silently because the code it describes
   isn't next to it.
   - ✗ `// parentsOf lists every ancestor of node. It walks the parent map
     instead of recursing, because deep trees overflowed the stack.`
   - ✓ `// parentsOf returns every ancestor of node, from the root down to its
     parent.` (the recursion reasoning, if it's needed at all, goes at the loop)
   - **Corollary:** a doc comment that restates the code below it is still a
     restatement (rule 1), and a sentence a reader of this codebase already
     knows is still obvious (rule 4). How long the surviving sentence runs is
     the corpus's question, not this rulebook's.

9. **Never name the test that covers this code.** A comment pointing at a test
    ("TestFooBar fails if you forget X", "covered by the table test below")
    couples two files that move independently: rename or delete the test and the
    comment lies, with nothing to catch it. It also answers the wrong question —
    a reader changing this line wants to know what breaks in *production*, not
    which test will go red, and they will find that out by running them. State
    the constraint itself; if the constraint is real, the test's own name is
    where it gets described.
    - ✗ `// Copied field by field. TestCloneCopiesEveryField fails if a new field
      on Config is not listed here.`
    - ✓ `// Copied field by field, so a field added to Config must be added here
      too.`

## What legitimately stays

These are not violations — keep them (rewrite only if noisy):

- **The non-obvious _why_**: rationale, trade-offs, why an obvious-looking
  alternative was avoided, links to an issue/RFC/spec explaining a decision.
- **Warnings / footguns**: "must stay in sync with X", "not thread-safe",
  ordering constraints, invariants a future editor could unknowingly break.
  The test is whether the code *lets* someone break it: two things that must
  agree but live apart and are edited independently earn the warning; two things
  the code forces to be equal (one variable, one constant) don't — that's a
  tautology (rule 4), not an invariant.
- **Contract / API doc comments**: behavior, params, return, and caveats that
  callers of a public function/type need — even if somewhat mechanical.
  Mechanical is fine here; *long* is not, and rationale belongs in the body
  (rule 8).
- **The order of an ordered return**: which end of the returned slice is which
  (outermost first, newest first, sorted by X). The signature can't express it,
  and a caller who guesses wrong gets a silently reversed result.
- **Required markers**: license headers, `nolint`/`type: ignore`/`noqa`
  directives, codegen markers, and other comments the toolchain acts on.
