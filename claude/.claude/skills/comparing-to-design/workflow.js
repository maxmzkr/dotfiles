export const meta = {
  name: 'comparing-to-design',
  description: 'Compare a PR to a blind reference design through four lenses and adjudicate each divergence, until a round finds nothing new',
  whenToUse: 'Run by the comparing-to-design skill with args it prepares',
  phases: [
    { title: 'Compare', detail: 'coverage / decisions / impact / extra, then dedupe' },
    { title: 'Adjudicate', detail: 'one judge per contested divergence' },
    { title: 'Save', detail: 'write adjudicated.json' },
  ],
}

// args: { rules, skill_dir, run_dir, brief_path, design_path, pr_url, title, head_dir, base_sha, head_sha, max_rounds? }
const A = args
const MAX_ROUNDS = A.max_rounds || 2
const MAX_JUDGED = 6
const role = (name, body) => `Read ${A.rules}, then ${A.skill_dir}/prompts/${name}.md, and follow them.\n\n${body}`
const CTX = `The change is ${A.pr_url} ("${A.title}"), checked out at ${A.head_dir} (head ${A.head_sha}, base ${A.base_sha}); use gh pr diff or git -C ${A.head_dir} diff ${A.base_sha}...${A.head_sha}. The brief it was meant to satisfy is at ${A.brief_path}; the blind reference design is at ${A.design_path}. Read both first.`
const j = x => JSON.stringify(x, null, 2)

const DIVERGENCES = { type: 'object', properties: { divergences: { type: 'array', items: { type: 'object', properties: {
  title: { type: 'string' }, location: { type: 'string' },
  design_expects: { type: 'string' }, impl_does: { type: 'string' },
  initial_take: { type: 'string', enum: ['impl_better', 'equivalent', 'impl_worse', 'design_wrong'] },
  argument: { type: 'string' },
}, required: ['title', 'location', 'design_expects', 'impl_does', 'initial_take', 'argument'] } } }, required: ['divergences'] }

const VERDICT = { type: 'object', properties: {
  verdict: { type: 'string', enum: ['impl_better', 'equivalent', 'impl_worse', 'design_wrong'] },
  reasonable: { type: 'boolean' }, argument: { type: 'string' },
}, required: ['verdict', 'reasonable', 'argument'] }

const seen = []
const adjudicated = []
let capped = true
for (let round = 1; round <= MAX_ROUNDS; round++) {
  phase('Compare')
  const known = seen.length ? `\n\nAlready found — report only divergences not in this list:\n${j(seen.map(d => `${d.title} @ ${d.location}`))}` : ''
  const found = (await parallel(['coverage', 'decisions', 'impact', 'extra'].map(lens => () => agent(
    role('comparer', `${CTX}\n\nYour lens: ${lens}.${known}`),
    { label: `compare:${lens}:r${round}`, phase: 'Compare', schema: DIVERGENCES },
  )))).filter(Boolean).flatMap(r => r.divergences)
  if (!found.length) { log(`round ${round}: nothing reported`); capped = false; break }

  const merged = await agent(
    role('dedupe', `Reported this round:\n${j(found)}\n\nAlready known:\n${j(seen)}`),
    { label: `dedupe:r${round}`, phase: 'Compare', schema: DIVERGENCES, effort: 'low' },
  )
  const fresh = merged ? merged.divergences : []
  log(`round ${round}: ${found.length} reported, ${fresh.length} new`)
  if (!fresh.length) { capped = false; break }
  seen.push(...fresh)

  // Only contested divergences get a judge; the comparer's own take stands for the rest.
  const settled = fresh.filter(d => d.initial_take === 'equivalent' || d.initial_take === 'impl_better')
  let contested = fresh.filter(d => !settled.includes(d))
  adjudicated.push(...settled.map(d => ({ ...d, verdict: d.initial_take, judged: false })))
  if (contested.length > MAX_JUDGED) {
    log(`round ${round}: judging ${MAX_JUDGED} of ${contested.length} contested divergences; the rest keep the comparer's take`)
    adjudicated.push(...contested.slice(MAX_JUDGED).map(d => ({ ...d, verdict: d.initial_take, judged: false })))
    contested = contested.slice(0, MAX_JUDGED)
  }

  phase('Adjudicate')
  const judged = await parallel(contested.map(d => () => agent(
    role('judge', `${CTX}\n\nDivergence:\n${j(d)}`),
    { label: `judge:${d.title.slice(0, 40)}`, phase: 'Adjudicate', schema: VERDICT },
  ).then(v => v && { ...d, verdict: v.verdict, reasonable: v.reasonable, judge_argument: v.argument, judged: true })))
  adjudicated.push(...judged.filter(Boolean))
}
if (capped) log(`stopped at the ${MAX_ROUNDS}-round cap; another round might find more`)

phase('Save')
await agent(
  `Write exactly this JSON, unchanged, to ${A.run_dir}/adjudicated.json and write nothing else:\n${j({ adjudicated, capped })}`,
  { label: 'save', phase: 'Save', effort: 'low' },
)
return { adjudicated, capped }
