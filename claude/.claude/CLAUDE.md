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

**Table-driven.** Cases in a slice of structs, each run under `t.Run(tt.name, ...)` so a
failure names itself and `-run` can select one.

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
