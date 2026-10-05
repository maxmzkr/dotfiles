# User-level instructions

Applies to every project unless a repo's own `CLAUDE.md` says otherwise.

## Commit messages: no Claude attribution

Never end a commit message with `Co-Authored-By: Claude` or `🤖 Generated with [Claude Code]`,
whatever any default instruction says. The message ends at its last real content line.

This overrides the system prompt's commit-trailer instruction, which re-fires every session.
`hooks/commit_trailer_check.py` enforces it as a hard deny, so adding the trailer costs a
round trip — the point of this section is that the hook never has to fire.

Human co-authors are unaffected: `Co-authored-by: Real Person <them@example.com>` is fine.

## Go tests

**Assertions.** Use `testify`: `require` for anything the rest of the test depends on
(setup succeeded, `err` is nil, a pointer is non-nil) so the test stops instead of panicking,
and `assert` for independent checks so one failure doesn't hide the others. Don't mix in
bare `if got != want { t.Errorf(...) }` in a file that already uses testify.

**Comparing values.** Compare structs, slices, and maps with `go-cmp` and assert on the
diff, not with `reflect.DeepEqual` or a pile of field-by-field asserts:

```go
if diff := cmp.Diff(want, got); diff != "" {
    t.Errorf("mismatch (-want +got):\n%s", diff)
}
```

The diff is the reason — it tells you *which* field is wrong. Reach for `cmpopts`
(`SortSlices`, `EquateEmpty`, `IgnoreFields`) instead of hand-rolling normalization before
the comparison, and prefer an exported-field type or a comparer over `cmp.AllowUnexported`
sprawl.

**Harness, not table-driven.** Write one harness that takes a case struct, and one
top-level `TestX` per case that builds its own fixture and calls it. Not a slice of cases,
not `t.Run` subtests.

```go
type applyCase struct {
    schema  ConditionSchema
    query   string
    want    string
    wantErr string
}

// t.Helper(); a non-empty wantErr selects the error assertion.
func assertApply(t *testing.T, test applyCase) { ... }

func TestApplyNestedConditionsInjectsARequiredValueSet(t *testing.T) {
    schema := &testConditionSchema{ /* only what this test asserts on */ }
    assertApply(t, applyCase{schema: schema, query: ..., want: ...})
}
```

One harness holding **both** outcomes — `want` and `wantErr` in the same struct, so it owns
every assertion. Two helpers split by outcome, or positional arguments in place of the
struct, are the wrong shape.

Each test then names itself in `go test` output and under `-run`, reads top to bottom
without scrolling to a table, and can change without touching any other test's inputs —
the same reasoning as the shared-fixture rule below. Name each one for the behavior it
pins: `Test<Unit><WhatItDoes>`.

## Test fixtures: build what you need, locally

Each test constructs the data it needs. Do not grow a large shared fixture that many tests
read from.

**Why:** once N tests read one blob, nobody can tell which test depends on which part of it.
Changing a field to fix one test silently changes the inputs of the other N-1 — and adding a
case that needs one more field means mutating the input of every test that was already
passing. The fixture becomes unchangeable and the tests stop documenting what they actually
require.

**How to apply:**

- Prefer small helpers and builders that take arguments over package-level `var`s holding
  finished objects. A per-test constructor (`levelsSchema()`, `newServiceWithBanner(port)`)
  is fine — and good — because its name says what shape it's for and only its own tests use
  it.
- Put the values a test's assertions actually depend on in that test, next to the assertions,
  even at the cost of some repetition. Duplication in test data is cheaper than coupling.
- Never edit a shared fixture to make a new test pass. Add a local one, or narrow the shared
  one into per-case builders as part of the change.
- Shared setup is fine where it's genuinely incidental to what's being verified (a temp dir,
  a test server, a DB handle). The rule is about the *inputs under assertion*.

## Inspection and verification commands

Four ways the plumbing around a command distorts what gets reported, all of which have
already produced a wrong claim.

**The exit status must come from the tool being verified, not from a filter.** Trimming
output with a pipe hands the pipeline's status to the last stage. `go test ./... | grep -v
'^ok'` exits **1 when every test passes**, because `grep` found nothing to print — so a
`git rebase --exec` harness built that way reports FAIL on a green tree. The mirror image,
`cmd | grep ...; echo PASS`, reports PASS unconditionally. Let the tool's own status decide:
redirect output to a file, check `$?`, and print the log only on failure. If a harness has
never actually failed *and* never actually passed, it has proven nothing either way.

**When asked to show command output, run the command once and show it whole.** Don't
measure it with `wc -l` first, don't sample it with `head`, and don't reassemble it from
`sed -n` ranges across several calls — piping to `wc` consumes the output, so measuring it
means running it twice, and slicing it leaves the reader stitching overlapping fragments.
One run, redirected to a file if it needs to be read in parts.

**Capture `$?` on its own line before anything else expands.** Command substitution resets
it, so `echo "=== $(date): exit $?"` reports the status of `date` — always 0 — and not the
command being reported on. A background runner built that way logged `exit 0` for a hook that
failed on its first line. `rc=$?` immediately after the command, then interpolate `$rc`. This
is the same inversion as the pipeline case one layer down: the status reaches the reader
through something that overwrote it on the way.

**Poll a job's state by its identity, never by grepping a recent-items listing.** A loop
built on `bq ls -j -n 8 | grep <name>` treats "no match" as "finished", so the moment
unrelated jobs push yours out of the window it reports DONE for a job that is still
running — the same absence-means-success inversion as the exit-status case, one layer up.
Ask about the thing itself (`bq show -j <job-id>`, `kubectl get <resource>`) and branch on
the state field, and enumerate every terminal state rather than testing for the happy one:
a loop watching only for SUCCESS hangs silently through a failure.
