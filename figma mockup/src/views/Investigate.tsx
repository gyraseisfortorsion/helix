import { Card, CatTag, Eyebrow, rng } from '../ui'

function Track({ label, ctx, color, seed, alt }: { label: string; ctx: string; color: string; seed: number; alt?: boolean }) {
  const r = rng(seed)
  const n = 120
  const pts = Array.from({ length: n }, (_, i) => {
    const peak = Math.exp(-((i - 60) ** 2) / 90) * 0.6 + Math.exp(-((i - 25) ** 2) / 50) * 0.25
    const bump = alt ? Math.exp(-((i - 60) ** 2) / 30) * 0.28 : 0
    return Math.min(0.95, 0.06 + peak + bump + r() * 0.07)
  })
  const d = pts.map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / (n - 1)) * 600},${70 - v * 66}`).join(' ')
  return (
    <div className="grid grid-cols-[150px_1fr] items-center gap-4 border-b border-line py-2">
      <div>
        <div className="text-sm font-medium">{label}</div>
        <div className="font-mono text-[10px] text-mute">{ctx}</div>
      </div>
      <svg viewBox="0 0 600 72" className="h-[72px] w-full">
        <path d={`${d} L600,72 L0,72Z`} fill={color} opacity=".14" />
        <path d={d} fill="none" stroke={color} strokeWidth="1.6" />
        <line x1="300" x2="300" y1="0" y2="72" stroke="#1b1a2e" strokeDasharray="3 3" opacity=".5" />
      </svg>
    </div>
  )
}

export default function Investigate() {
  const bases = ['A', 'C', 'G', 'T']
  const r = rng(7)
  const heat = Array.from({ length: 4 }, () => Array.from({ length: 11 }, () => (r() - 0.5) * 2))
  const col = (v: number, ref: boolean) =>
    ref ? '#1b1a2e' : v > 0 ? `rgba(190,24,93,${Math.min(.9, v)})` : `rgba(15,118,110,${Math.min(.9, -v)})`
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-10 py-8">
      <div className="rise flex items-end justify-between">
        <div>
          <Eyebrow>Variant investigation</Eyebrow>
          <h1 className="mt-1 text-4xl">LDLR promoter · chr19:11,089,362 A&gt;G</h1>
          <p className="mt-2 text-sm text-mute">GRCh38 · reference allele verified · present in Ava (heterozygous)</p>
        </div>
        <div className="flex gap-2 text-sm">
          {['Annotate', 'Score', 'Evo 2', 'Mutagenesis'].map((s, i) => (
            <span key={s} className={`rounded-full border px-3 py-1 ${i < 3 ? 'border-measured/40 bg-measured/10 text-measured' : 'border-line text-mute'}`}>
              {i < 3 ? '✓ ' : ''}
              {s}
            </span>
          ))}
        </div>
      </div>

      <Card className="rise p-6">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-xl">Reference vs alternative</h3>
          <CatTag c="model" />
        </div>
        <div className="mb-3 flex gap-4 font-mono text-[11px] text-mute">
          <span>Model: AlphaGenome v1</span><span>Context: HepG2 · CAGE (selected)</span><span>Cached · 2 min ago</span>
        </div>
        <Track label="REF  A" ctx="HepG2 · CAGE" color="#4338ca" seed={3} />
        <Track label="ALT  G" ctx="HepG2 · CAGE" color="#be185d" seed={3} alt />
        <Track label="Δ ALT−REF" ctx="HepG2 · CAGE" color="#1b1a2e" seed={11} />
        <div className="mt-4 rounded-lg bg-paper p-3 text-sm">
          <b className="font-medium">Cartilage context unavailable.</b> Not substituted with blood or cancer-line data.
        </div>
      </Card>

      <div className="grid grid-cols-5 gap-6">
        <Card className="rise col-span-3 p-6">
          <div className="flex items-center justify-between">
            <h3 className="text-xl">Bounded mutagenesis</h3>
            <CatTag c="model" />
          </div>
          <p className="mb-4 mt-1 text-xs text-mute">±5 bases. A model experiment, not a simulation of you.</p>
          <div className="space-y-1">
            {heat.map((row, bi) => (
              <div key={bi} className="flex items-center gap-1">
                <span className="w-5 font-mono text-xs text-mute">{bases[bi]}</span>
                {row.map((v, i) => (
                  <div key={i} className="grid h-9 flex-1 place-items-center rounded-sm text-[10px] text-white" style={{ background: i === 5 && bi === 0 ? '#1b1a2e' : col(v, false), outline: i === 5 ? '1.5px solid #1b1a2e' : undefined, outlineOffset: 1 }}>
                    {i === 5 && bi === 0 ? 'ref' : ''}
                  </div>
                ))}
              </div>
            ))}
            <div className="ml-6 flex font-mono text-[10px] text-mute">
              {'GTCAC A CTGGA'.replace(/ /g, '').split('').map((b, i) => (
                <span key={i} className={`flex-1 text-center ${i === 5 ? 'font-medium text-ink' : ''}`}>{b}</span>
              ))}
            </div>
          </div>
        </Card>

        <div className="col-span-2 space-y-6">
          <Card className="rise p-5">
            <div className="flex items-center justify-between"><h3 className="text-lg">Evo 2 · 7B</h3><CatTag c="model" /></div>
            <div className="mt-3 font-mono text-3xl">−0.0043</div>
            <p className="mt-1 text-xs text-mute">Δ log-likelihood · 8,192-base window. A sequence-model score, not a disease probability, and not combined with AlphaGenome.</p>
          </Card>
          <Card className="rise p-5">
            <div className="flex items-center justify-between"><h3 className="text-lg">Supporting experiment</h3><CatTag c="published" /></div>
            <p className="mt-2 text-sm">Saturation-mutagenesis MPRA in HepG2 reports reduced expression for substitutions at this position.</p>
            <p className="mt-2 font-mono text-[11px] text-mute">Reporter assay · not a personal-health outcome</p>
          </Card>
        </div>
      </div>
    </div>
  )
}
