import { Card, CatTag, Eyebrow, rng, Synthetic } from '../ui'

export default function Methylation() {
  const r = rng(5)
  const probes = Array.from({ length: 48 }, (_, i) => {
    const dip = Math.exp(-((i - 22) ** 2) / 60)
    return { id: `cg${(10000000 + Math.floor(r() * 9e6))}`, pos: 11080000 + i * 310 + Math.floor(r() * 120), b: Math.max(0.02, Math.min(0.98, 0.82 - dip * 0.65 + (r() - 0.5) * 0.12)) }
  })
  const W = 860, H = 220
  const x = (i: number) => 24 + (i / 47) * (W - 48)
  const y = (b: number) => H - 24 - b * (H - 44)
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-10 py-8">
      <div className="rise">
        <Eyebrow>Measured methylation explorer</Eyebrow>
        <h1 className="mt-1 text-4xl">48 CpG probes across a 15 kb region.</h1>
      </div>
      <div className="rise grid grid-cols-4 gap-3">
        {[['Tissue', 'Whole blood'], ['Assay', 'EPIC v1 array'], ['Assembly', 'GRCh38'], ['Collected', '2025-03-14']].map(([k, v]) => (
          <Card key={k} className="p-4"><Eyebrow>{k}</Eyebrow><div className="mt-1 font-serif text-xl">{v}</div></Card>
        ))}
      </div>
      <Card className="rise p-6">
        <div className="flex items-center justify-between"><div className="flex items-center gap-2"><h3 className="text-xl">Beta values by position</h3><Synthetic /></div><CatTag c="measured" /></div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full">
          {[0, 0.5, 1].map((t) => <g key={t}><line x1="24" x2={W - 24} y1={y(t)} y2={y(t)} stroke="#ddd5c6" /><text x="0" y={y(t) + 3} fontSize="10" fill="#6d6a7c">{t}</text></g>)}
          {probes.map((p, i) => (
            <g key={p.id}>
              <line x1={x(i)} x2={x(i)} y1={y(0)} y2={y(p.b)} stroke="#0f766e" strokeWidth="1" opacity=".4" />
              <circle cx={x(i)} cy={y(p.b)} r="4" fill={p.b < 0.35 ? '#b45309' : '#0f766e'} />
            </g>
          ))}
          <text x="24" y={H - 6} fontSize="10" fill="#6d6a7c">chr19:11,080,000</text>
          <text x={W - 24} y={H - 6} textAnchor="end" fontSize="10" fill="#6d6a7c">chr19:11,095,000</text>
        </svg>
        <div className="mt-2 rounded-lg bg-paper p-3 text-sm">
          Measured methylation is shown separately from DNA-based regulatory predictions. No clocks, no inferred tissue, no lifestyle prescriptions.
        </div>
      </Card>
      <Card className="rise overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-paper text-left font-mono text-[11px] uppercase text-mute"><tr><th className="px-4 py-2">Probe</th><th>Position</th><th>Beta</th><th className="w-1/3">&nbsp;</th></tr></thead>
          <tbody>
            {probes.slice(18, 25).map((p) => (
              <tr key={p.id} className="border-t border-line font-mono text-xs">
                <td className="px-4 py-2">{p.id}</td><td>{p.pos.toLocaleString()}</td><td>{p.b.toFixed(3)}</td>
                <td><div className="h-1.5 rounded bg-paper"><div className="h-full rounded bg-measured" style={{ width: `${p.b * 100}%` }} /></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
