export const meta = {
  name: 'deep-reviewing-hotspots',
  description: 'Pick the places in a PR needing deep review, review each, try to refute each finding, and loop a completeness critic until dry',
  whenToUse: 'Run by the deep-reviewing-hotspots skill with args it prepares',
  phases: [
    { title: 'Hotspots', detail: 'first pass, then completeness critic' },
    { title: 'Deep review', detail: 'one reviewer per place, one refuter per finding' },
    { title: 'Save', detail: 'write findings.json' },
  ],
}

// args: { rules, skill_dir, run_dir, brief_path, adjudicated_path, pr_url, title, head_dir, base_sha, head_sha, max_rounds? }
const A = args
const MAX_ROUNDS = A.max_rounds || 2
const MAX_PLACES = 5
const role = (name, body) => `Read ${A.rules}, then ${A.skill_dir}/prompts/${name}.md, and follow them.\n\n${body}`
const CTX = `The change is ${A.pr_url} ("${A.title}"), checked out at ${A.head_dir} (head ${A.head_sha}, base ${A.base_sha}); use gh pr diff or git -C ${A.head_dir} diff ${A.base_sha}...${A.head_sha}. Its brief is at ${A.brief_path}.`
const j = x => JSON.stringify(x, null, 2)

const PLACES = { type: 'object', properties: { places: { type: 'array', items: { type: 'object', properties: {
  location: { type: 'string' }, why: { type: 'string' }, questions: { type: 'array', items: { type: 'string' } },
}, required: ['location', 'why', 'questions'] } } }, required: ['places'] }

const FINDINGS = { type: 'object', properties: {
  findings: { type: 'array', items: { type: 'object', properties: {
    location: { type: 'string' }, claim: { type: 'string' }, failure_scenario: { type: 'string' },
    severity: { type: 'string', enum: ['blocker', 'major', 'minor', 'nit'] }, evidence: { type: 'string' },
  }, required: ['location', 'claim', 'failure_scenario', 'severity', 'evidence'] } },
  answers: { type: 'array', items: { type: 'string' } },
}, required: ['findings', 'answers'] }

const REFUTE = { type: 'object', properties: { refuted: { type: 'boolean' }, argument: { type: 'string' } }, required: ['refuted', 'argument'] }

const reviewed = []
const upheld = []
const refuted = []
const toReview = []  // places a limit kept us from reviewing, handed to the human
let capped = true
for (let round = 1; round <= MAX_ROUNDS; round++) {
  phase('Hotspots')
  const mode = round === 1
    ? `Mode: first pass. The adjudicated divergences are at ${A.adjudicated_path}.`
    : `Mode: critic. The adjudicated divergences are at ${A.adjudicated_path}.\n\nAlready reviewed:\n${j(reviewed)}\n\nUpheld findings so far:\n${j(upheld)}`
  const picked = await agent(
    role('hotspots', `${CTX}\n\n${mode}\n\nReturn at most ${MAX_PLACES} places.`),
    { label: `hotspots:r${round}`, phase: 'Hotspots', schema: PLACES },
  )
  let places = picked ? picked.places : []
  if (!places.length) { log(`round ${round}: no further places need review`); capped = false; break }
  if (places.length > MAX_PLACES) {
    log(`round ${round}: ${places.length - MAX_PLACES} lower-priority places left for human review`)
    toReview.push(...places.slice(MAX_PLACES).map(p => ({ ...p, reason: 'over the per-round place limit' })))
    places = places.slice(0, MAX_PLACES)
  }

  phase('Deep review')
  const results = await pipeline(
    places,
    p => agent(
      role('deep-reviewer', `${CTX}\n\nPlace:\n${j(p)}`),
      { label: `deep:${p.location.slice(0, 40)}`, phase: 'Deep review', schema: FINDINGS },
    ),
    (r, p) => r && parallel(r.findings.map(f => () => agent(
      role('refuter', `${CTX}\n\nFinding:\n${j(f)}`),
      { label: `refute:${f.location.slice(0, 30)}`, phase: 'Deep review', schema: REFUTE },
    ).then(v => ({ ...f, place: p.location, upheld: !!v && !v.refuted, refutation: v })))).then(findings => ({ place: p, answers: r.answers, findings })),
  )
  for (const r of results.filter(Boolean)) {
    reviewed.push({ ...r.place, answers: r.answers })
    upheld.push(...r.findings.filter(f => f.upheld))
    refuted.push(...r.findings.filter(f => !f.upheld))
  }
  log(`round ${round}: ${places.length} places, ${upheld.length} findings upheld so far, ${refuted.length} refuted`)
}
if (capped) {
  // One more critic pass, not reviewed: what would the next round have looked at?
  const next = await agent(
    role('hotspots', `${CTX}\n\nMode: critic. The adjudicated divergences are at ${A.adjudicated_path}.\n\nAlready reviewed:\n${j(reviewed)}\n\nUpheld findings so far:\n${j(upheld)}\n\nThis review has hit its round limit, so nobody else will look at these — the places you return go to a human as what still deserves review. Return at most ${MAX_PLACES} places.`),
    { label: 'hotspots:unreviewed', phase: 'Hotspots', schema: PLACES },
  )
  toReview.push(...(next ? next.places : []).map(p => ({ ...p, reason: 'round limit reached before it was reviewed' })))
  log(`stopped at the ${MAX_ROUNDS}-round cap; ${toReview.length} places left for human review`)
}

phase('Save')
const out = { upheld, to_review: toReview, refuted: refuted.map(f => ({ location: f.location, claim: f.claim, refutation: f.refutation })), reviewed, capped }
await agent(
  `Write exactly this JSON, unchanged, to ${A.run_dir}/findings.json and write nothing else:\n${j(out)}`,
  { label: 'save', phase: 'Save', effort: 'low' },
)
return out
