# Divergence deduper

You get the divergences reported this round and the ones already known from earlier rounds.
Return only the ones that are **genuinely new**.

- Same underlying issue as a known divergence → drop it, even if worded differently or
  located at a different line of the same mechanism.
- Duplicates within this round → merge into one, keeping the most precise location and the
  strongest argument.
- Different consequence of the same code → keep both; they will be judged separately.

Don't judge merit — that's the next step's job. Don't read code unless two entries are
ambiguous about whether they're the same issue.
