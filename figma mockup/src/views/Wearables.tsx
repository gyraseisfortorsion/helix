import { Card, CatTag, Eyebrow, rng, Synthetic } from '../ui'

export default function Wearables() {
  const r = rng(21)
  const n = 84
  const hr = Array.from({ length: n }, (_, i) => 58 + (i > 56 ? (i - 56) * 0.28 : 0) + (r() - 0.5) * 3.2)
  const gap = [30, 31, 32, 33, 34]
  const W = 860, H = 240
  const x = (i: number) => 30 + (i / (n - 1)) * (W - 50)
  const y = (v: number) => H - 28 - ((v - 52) / 20) * (H - 50)
  const base = 58.4
  const line = hr.map((v, i) => (gap.includes(i) ? null : [x(i), y(v)])).reduce<string>((a, p, i, arr) => (p ? `${a}${i === 0 || !arr[i - 1] ? 'M' : 'L'}${p[0]},${p[1]}` : a), '')
  const sleep = Array.from({ length: 28 }, () => 5.2 + r() * 3)
  return (
    <div className="mx-auto max-w-5xl space-y-6 px-10 py-8">
      <div className="rise">
        <Eyebrow>Wearables · rolling 28-day personal baseline</Eyebrow>
        <h1 className="mt-1 text-4xl">Resting heart rate has drifted above your baseline.</h1>
        <p className="mt-2 max-w-2xl text-sm text-mute">Seven valid days required for a baseline; resting and exercise readings are never mixed. This describes a change, not a cause.</p>
      </div>

      <Card className="rise p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2"><h3 className="text-xl">Resting heart rate</h3><Synthetic /></div>
          <CatTag c="measured" />
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} className="mt-3 w-full">
          <rect x="30" width={W - 50} y={y(base + 3)} height={y(base - 3) - y(base + 3)} fill="#0f766e" opacity=".12" />
          <line x1="30" x2={W - 20} y1={y(base)} y2={y(base)} stroke="#0f766e" strokeDasharray="4 4" />
          <rect x={x(30)} width={x(34) - x(30)} y="10" height={H - 38} fill="#1b1a2e" opacity=".07" />
          <text x={x(32)} y="26" textAnchor="middle" fontSize="10" fill="#6d6a7c">missing</text>
          <line x1={x(52)} x2={x(52)} y1="10" y2={H - 28} stroke="#b45309" />
          <text x={x(52) + 6} y="24" fontSize="10" fill="#b45309">Logged: new training plan</text>
          <path d={line} fill="none" stroke="#1b1a2e" strokeWidth="2" strokeLinejoin="round" />
          {[55, 60, 65, 70].map((t) => (
            <g key={t}><text x="0" y={y(t) + 3} fontSize="10" fill="#6d6a7c">{t}</text><line x1="30" x2={W - 20} y1={y(t)} y2={y(t)} stroke="#ddd5c6" opacity=".6" /></g>
          ))}
          <text x={W - 20} y={y(base) - 6} textAnchor="end" fontSize="10" fill="#0f766e">baseline 58.4 bpm</text>
        </svg>
      </Card>

      <div className="grid grid-cols-3 gap-6">
        <Card className="rise p-5">
          <h3 className="text-lg">Sleep, last 28 nights</h3>
          <div className="mt-4 flex h-24 items-end gap-0.5">
            {sleep.map((s, i) => <div key={i} className="flex-1 rounded-t-sm bg-inherited/70" style={{ height: `${(s / 9) * 100}%` }} />)}
          </div>
          <p className="mt-2 font-mono text-[11px] text-mute">avg 6.7 h · source: Watch → Band (changed wk 9)</p>
        </Card>
        <Card className="rise col-span-2 p-5">
          <div className="flex items-center justify-between"><h3 className="text-lg">Supported actions</h3><CatTag c="published" /></div>
          <ul className="mt-3 space-y-3 text-sm">
            {[
              ['Add one easy-effort day after each hard session', 'Training load rose in the same window.', 'Track: morning resting HR for 14 days'],
              ['Hold bedtime within 45 min', 'Sleep averaged 6.7 h with high variance.', 'Track: sleep duration variance'],
            ].map(([a, b, c]) => (
              <li key={a} className="rounded-lg bg-paper p-3">
                <div className="font-medium">{a}</div>
                <div className="text-ink/70">{b}</div>
                <div className="mt-1 font-mono text-[11px] text-measured">{c}</div>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-mute">Genetic data was not used: the guidance library has no supported link here.</p>
        </Card>
      </div>
    </div>
  )
}
