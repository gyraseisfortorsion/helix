import { Card, CatTag, Eyebrow } from '../ui'

type S = 'conditional' | 'unresolved' | 'none'
const conds: { name: string; gene: string; a: string; b: string; status: S; note: string }[] = [
  { name: 'Cystic fibrosis', gene: 'CFTR', a: 'Carrier · F508del', b: 'Carrier · G542X', status: 'conditional', note: 'Different compatible variants in the same condition.' },
  { name: 'Phenylketonuria', gene: 'PAH', a: 'Carrier · R408W', b: 'Variant of uncertain significance', status: 'unresolved', note: 'VUS in partner; no probability given.' },
  { name: 'Tay–Sachs disease', gene: 'HEXA', a: 'No supported variant seen', b: 'Coverage incomplete', status: 'unresolved', note: 'Missing calls are unknown, not negative.' },
]

function Punnett() {
  const cells = [['AA', 'Aa'], ['aA', 'aa']]
  return (
    <div className="grid grid-cols-[auto_1fr_1fr] gap-1.5 font-mono text-xs">
      <span /><span className="text-center text-mute">A</span><span className="text-center text-mute">a</span>
      {cells.map((row, i) => (
        <div key={i} className="contents">
          <span className="self-center text-mute">{i ? 'a' : 'A'}</span>
          {row.map((c) => (
            <div key={c} className={`grid h-14 place-items-center rounded-lg ${c === 'aa' ? 'bg-model text-white' : c === 'AA' ? 'bg-paper' : 'bg-inherited/15 text-inherited'}`}>
              <div>{c}<div className="text-[10px] opacity-80">25%</div></div>
            </div>
          ))}
        </div>
      ))}
    </div>
  )
}

export default function Family() {
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-10 py-8">
      <div className="rise">
        <Eyebrow>Family planning · paired comparison</Eyebrow>
        <h1 className="mt-1 text-4xl">Ava &amp; Sam: three conditions, assessed one at a time.</h1>
        <p className="mt-2 max-w-2xl text-sm text-mute">Raw-data results are conditional and unconfirmed. No compatibility score, no ranking, no prediction of a future child.</p>
      </div>
      {conds.map((c, i) => (
        <Card key={c.name} className="rise grid grid-cols-[1fr_220px] gap-8 p-6" >
          <div style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-center gap-3">
              <h3 className="text-2xl">{c.name}</h3>
              <span className="rounded bg-ink/8 px-1.5 py-0.5 font-mono text-xs italic">{c.gene}</span>
              <span className={`ml-auto rounded-full px-3 py-1 text-xs font-medium ${c.status === 'conditional' ? 'bg-model/10 text-model' : 'bg-ink/8 text-mute'}`}>
                {c.status === 'conditional' ? 'Conditional 25% affected' : 'Unresolved'}
              </span>
            </div>
            <div className="mt-5 grid grid-cols-2 gap-4 text-sm">
              {[['Ava', c.a], ['Sam', c.b]].map(([p, f]) => (
                <div key={p} className="rounded-xl bg-paper p-3">
                  <div className="font-mono text-[11px] uppercase text-mute">{p}</div>
                  <div className="mt-1 flex items-center justify-between gap-2"><span>{f}</span><CatTag c="inherited">{''}</CatTag></div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm text-ink/80">{c.note}</p>
            <p className="mt-1 font-mono text-[11px] text-mute">Panel v1.2 · ClinVar provenance · phase assumed trans</p>
          </div>
          <div className={c.status === 'conditional' ? '' : 'pointer-events-none opacity-25 grayscale'}>
            <Punnett />
            {c.status !== 'conditional' && <p className="mt-2 text-center text-xs">Not computable</p>}
          </div>
        </Card>
      ))}
    </div>
  )
}
