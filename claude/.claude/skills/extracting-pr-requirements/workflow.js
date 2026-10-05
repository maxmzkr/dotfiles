export const meta = {
  name: 'extracting-pr-requirements',
  description: 'Extract a PR\'s requirements from three lenses and merge them into an implementation-free brief',
  whenToUse: 'Run by the extracting-pr-requirements skill with args it prepares',
  phases: [
    { title: 'Read', detail: 'stated / behavior / system lenses' },
    { title: 'Brief', detail: 'merge, resolve, scrub the mechanism' },
  ],
}

// args: { rules, skill_dir, run_dir, pr_url, title, head_dir, base_dir, base_sha, head_sha }
const A = args
const role = (name, body) => `Read ${A.rules}, then ${A.skill_dir}/prompts/${name}.md, and follow them.\n\n${body}`
const PR = `The change is ${A.pr_url} ("${A.title}"), checked out at ${A.head_dir} (head ${A.head_sha}, base ${A.base_sha}). Use gh pr view / gh pr diff and git -C ${A.head_dir} diff ${A.base_sha}...${A.head_sha}.`

const REQ = { type: 'object', properties: { requirements: { type: 'array', items: { type: 'object', properties: {
  statement: { type: 'string' }, kind: { type: 'string', enum: ['functional', 'constraint', 'non_goal'] },
  evidence: { type: 'string' }, confidence: { type: 'string', enum: ['stated', 'inferred', 'guessed'] },
}, required: ['statement', 'kind', 'evidence', 'confidence'] } } }, required: ['requirements'] }

const BRIEF = { type: 'object', properties: {
  problem: { type: 'string' },
  requirements: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, statement: { type: 'string' },
    kind: { type: 'string', enum: ['functional', 'constraint', 'non_goal'] }, support: { type: 'string' },
  }, required: ['id', 'statement', 'kind', 'support'] } },
  assumptions: { type: 'array', items: { type: 'string' } },
  relevant_code: { type: 'array', items: { type: 'string' } },
}, required: ['problem', 'requirements', 'assumptions', 'relevant_code'] }

phase('Read')
const readings = (await parallel(['stated', 'behavior', 'system'].map(lens => () => agent(
  role('reader', `${PR}\n\nYour lens: ${lens}.`),
  { label: `reader:${lens}`, phase: 'Read', schema: REQ },
).then(r => r && { lens, ...r })))).filter(Boolean)
if (!readings.length) throw new Error('every requirements reader failed')
if (readings.length < 3) log(`only ${readings.length} of 3 readers returned`)

phase('Brief')
const brief = await agent(
  role('brief', `Readings:\n${JSON.stringify(readings, null, 2)}\n\nBase checkout (verify relevant_code here): ${A.base_dir} at ${A.base_sha}.\nOutput path: ${A.run_dir}/brief.json — the only file you may write.`),
  { label: 'brief', phase: 'Brief', schema: BRIEF },
)
return { brief, readings }
