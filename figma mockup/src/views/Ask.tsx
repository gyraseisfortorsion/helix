import { useState } from 'react'
import { Card, CatTag, Eyebrow, type Cat } from '../ui'

const evidence: { id: string; cat: Cat; title: string; src: string; note: string; limit: string }[] = [
  { id: 'E1', cat: 'inherited', title: 'COL1A1 rs1800012 · G/T', src: 'Ava_synthetic.vcf · GRCh38 chr17:50,184,096', note: 'Heterozygous call, quality 99. Present in uploaded file.', limit: 'A single common variant; says nothing about your current knee state.' },
  { id: 'E2', cat: 'published', title: 'Association with ligament and tendon injury', src: 'Europe PMC · PMID 18312345', note: 'Meta-analysis of 6 cohorts reports a modest association with soft-tissue injury risk.', limit: 'Effect sizes small; cohorts mostly athletes of European ancestry.' },
  { id: 'E3', cat: 'measured', title: 'Daily steps rose 38% over 5 weeks', src: 'Ava_synthetic_wearable.csv · 28-day baseline', note: 'Mean 6,100 → 8,400 steps/day since week 12.', limit: 'Observational. Does not identify the cause of pain.' },
  { id: 'E4', cat: 'model', title: 'No regulatory shift in chondrocyte context', src: 'AlphaGenome · context unavailable', note: 'Cartilage track not exposed by the model; no substitute used.', limit: 'Absence of a prediction is not evidence of no effect.' },
]

const steps = [
  ['Coordinator', 'Resolved profile Ava · 3 datasets'],
  ['Genomics', '14 knee-related variants checked, 1 present'],
  ['Health trends', 'Step volume change flagged'],
  ['Reviewer', '4 claims checked · 0 unsupported'],
]

function Ref({ id, active, on }: { id: string; active: string; on: (s: string) => void }) {
  const e = evidence.find((x) => x.id === id)!
  return (
    <button
      onClick={() => on(id)}
      className={`mx-0.5 inline-flex h-5 items-center rounded px-1.5 align-baseline font-mono text-[11px] transition ${
        active === id ? 'bg-ink text-paper' : 'bg-ink/8 text-ink hover:bg-ink/15'
      }`}
      title={e.title}
    >
      {id}
    </button>
  )
}

export default function Ask() {
  const [active, setActive] = useState('E1')
  const ev = evidence.find((e) => e.id === active)!
  return (
    <div className="grid h-full grid-cols-[1fr_340px]">
      <div className="flex min-h-0 flex-col">
        <div className="flex-1 space-y-8 overflow-y-auto px-10 py-8">
          <div className="rise ml-auto max-w-lg rounded-2xl rounded-br-sm bg-ink px-5 py-3 text-paper">
            My knees hurt. Does my genetic data contain anything relevant?
          </div>

          <div className="rise max-w-2xl" style={{ animationDelay: '.1s' }}>
            <div className="mb-4 flex flex-wrap gap-2">
              {steps.map(([a, b], i) => (
                <div key={a} className="flex items-center gap-2 rounded-full border border-line bg-card px-3 py-1 text-xs">
                  <span className="grid size-4 place-items-center rounded-full bg-measured text-[9px] text-white">{i + 1}</span>
                  <b className="font-medium">{a}</b>
                  <span className="text-mute">{b}</span>
                </div>
              ))}
            </div>

            <Eyebrow>Reviewed answer</Eyebrow>
            <h2 className="mt-2 text-[28px] leading-tight">
              One variant is loosely linked to soft-tissue injury. It does not explain your pain.
            </h2>
            <div className="mt-5 space-y-4 text-[15px] leading-relaxed text-ink/90">
              <p>
                Your file contains one variant in <i>COL1A1</i>, present in one copy<Ref id="E1" active={active} on={setActive} />. Published
                studies associate it with a small shift in tendon and ligament injury risk<Ref id="E2" active={active} on={setActive} />, which
                is a population-level tendency rather than a diagnosis.
              </p>
              <p>
                Your wearable data shows a recent rise in daily steps<Ref id="E3" active={active} on={setActive} />. A load increase is a common,
                non-genetic contributor to knee discomfort, but these data cannot confirm it is the cause.
              </p>
              <p>
                A cartilage-specific regulatory prediction was not available, so none is shown<Ref id="E4" active={active} on={setActive} />.
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-3">
              <Card className="p-4">
                <Eyebrow>What this cannot tell you</Eyebrow>
                <ul className="mt-2 space-y-1.5 text-sm text-ink/80">
                  <li>· Whether the pain is structural or inflammatory</li>
                  <li>· Variants missing from this file are unknown, not absent</li>
                </ul>
              </Card>
              <Card className="p-4">
                <Eyebrow>Suggested action</Eyebrow>
                <p className="mt-2 text-sm text-ink/80">Ramp weekly load by ≤10%. Track knee pain 0–10 each evening for 3 weeks.</p>
              </Card>
            </div>

            <div className="mt-5 flex flex-wrap gap-2">
              {['Investigate this variant', 'Show step trend', 'What else is not covered?'].map((t) => (
                <button key={t} className="rounded-full border border-ink/20 px-3.5 py-1.5 text-sm transition hover:bg-ink hover:text-paper">
                  {t}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="border-t border-line bg-card/70 px-10 py-4 backdrop-blur">
          <div className="flex items-center gap-3 rounded-full border border-ink/20 bg-white px-5 py-2.5 shadow-sm">
            <input className="flex-1 bg-transparent text-sm outline-none placeholder:text-mute" placeholder="Ask about your genetics, measurements, or a variant…" />
            <span className="font-mono text-[11px] text-mute">4 of 12 model requests</span>
            <button className="rounded-full bg-ink px-4 py-1.5 text-sm text-paper">Ask</button>
          </div>
        </div>
      </div>

      <aside className="overflow-y-auto border-l border-line bg-card/60 p-6">
        <Eyebrow>Evidence drawer</Eyebrow>
        <div key={ev.id} className="rise mt-4 rounded-2xl border border-line bg-white p-5">
          <div className="flex items-center justify-between">
            <span className="font-mono text-xs">{ev.id}</span>
            <CatTag c={ev.cat} />
          </div>
          <h3 className="mt-3 text-lg leading-snug">{ev.title}</h3>
          <p className="mt-1 font-mono text-[11px] text-mute">{ev.src}</p>
          <p className="mt-3 text-sm">{ev.note}</p>
          <div className="mt-4 rounded-lg bg-paper p-3 text-xs text-ink/80">
            <b className="font-medium">Limitation.</b> {ev.limit}
          </div>
        </div>
        <div className="mt-6 space-y-1.5">
          {evidence.map((e) => (
            <button
              key={e.id}
              onClick={() => setActive(e.id)}
              className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${active === e.id ? 'bg-ink/8' : 'hover:bg-ink/5'}`}
            >
              <span className="font-mono text-xs text-mute">{e.id}</span>
              <span className="flex-1 truncate">{e.title}</span>
              <CatTag c={e.cat}>{''}</CatTag>
            </button>
          ))}
        </div>
      </aside>
    </div>
  )
}
