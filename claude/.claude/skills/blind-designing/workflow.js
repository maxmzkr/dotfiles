export const meta = {
  name: 'blind-designing',
  description: 'Design a change from a brief alone — three blind solvers, then one reference design',
  whenToUse: 'Run by the blind-designing skill with args it prepares',
  phases: [
    { title: 'Solve', detail: 'minimal / robust / operable, blind' },
    { title: 'Design', detail: 'decision matrix and reference design' },
  ],
}

// args: { rules, skill_dir, run_dir, brief_path, base_dir, base_sha }
const A = args
const LENSES = ['minimal', 'robust', 'operable']
const role = (name, body) => `Read ${A.rules}, then ${A.skill_dir}/prompts/${name}.md, and follow them.\n\n${body}`
const BLIND = `You are blind. Base checkout: ${A.base_dir} (commit ${A.base_sha}) — the only code you may read. The brief is at ${A.brief_path}; read it first.`
const j = x => JSON.stringify(x, null, 2)

const SOLUTION = { type: 'object', properties: {
  approach: { type: 'string' },
  changes: { type: 'array', items: { type: 'string' } },
  decisions: { type: 'array', items: { type: 'object', properties: {
    question: { type: 'string' }, choice: { type: 'string' }, rejected: { type: 'string' }, why: { type: 'string' },
  }, required: ['question', 'choice', 'rejected', 'why'] } },
  risks: { type: 'array', items: { type: 'string' } },
  tests: { type: 'array', items: { type: 'string' } },
}, required: ['approach', 'changes', 'decisions', 'risks', 'tests'] }

const DESIGN = { type: 'object', properties: {
  summary: { type: 'string' },
  decisions: { type: 'array', items: { type: 'object', properties: {
    id: { type: 'string' }, question: { type: 'string' }, choice: { type: 'string' },
    acceptable_alternatives: { type: 'array', items: { type: 'string' } }, rationale: { type: 'string' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
  }, required: ['id', 'question', 'choice', 'acceptable_alternatives', 'rationale', 'confidence'] } },
  invariants: { type: 'array', items: { type: 'string' } },
  test_plan: { type: 'array', items: { type: 'string' } },
  rollout: { type: 'string' },
}, required: ['summary', 'decisions', 'invariants', 'test_plan', 'rollout'] }

phase('Solve')
const solutions = (await parallel(LENSES.map(lens => () => agent(
  role('solver', `${BLIND}\n\nYour lens: ${lens}.`),
  { label: `solve:${lens}`, phase: 'Solve', schema: SOLUTION },
).then(r => r && { lens, ...r })))).filter(Boolean)
if (!solutions.length) throw new Error('every blind solver failed')
if (solutions.length < LENSES.length) log(`only ${solutions.length} of ${LENSES.length} solvers returned`)

phase('Design')
const design = await agent(
  role('reference', `${BLIND}\n\nIndependent solutions:\n${j(solutions)}\n\nOutput path: ${A.run_dir}/design.json — the only file you may write.`),
  { label: 'reference-design', phase: 'Design', schema: DESIGN },
)
return { design, solutions }
