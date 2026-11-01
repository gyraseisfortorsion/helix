import { useState } from 'react'
import Ask from './views/Ask'
import Investigate from './views/Investigate'
import Wearables from './views/Wearables'
import Family from './views/Family'
import Methylation from './views/Methylation'
import { CatTag, Synthetic, catMeta, type Cat } from './ui'

const nav = [
  ['ask', 'Ask', Ask],
  ['investigate', 'Investigate', Investigate],
  ['wearables', 'Wearables', Wearables],
  ['family', 'Family', Family],
  ['methylation', 'Methylation', Methylation],
] as const

function Helix() {
  return (
    <svg viewBox="0 0 28 36" className="h-9 w-7">
      {Array.from({ length: 9 }, (_, i) => {
        const t = i / 8
        const a = Math.sin(t * Math.PI * 2) * 9
        return (
          <g key={i}>
            <line x1={14 - a} x2={14 + a} y1={3 + i * 3.8} y2={3 + i * 3.8} stroke="#1b1a2e" opacity=".25" />
            <circle cx={14 - a} cy={3 + i * 3.8} r="2" fill="#4338ca" />
            <circle cx={14 + a} cy={3 + i * 3.8} r="2" fill="#be185d" />
          </g>
        )
      })}
    </svg>
  )
}

export default function App() {
  const [view, setView] = useState<string>('ask')
  const [profile, setProfile] = useState('Ava')
  const View = nav.find((n) => n[0] === view)![2]
  return (
    <div className="flex h-screen flex-col">
      <div className="flex items-center justify-center gap-2 bg-ink py-1.5 text-xs text-paper">
        <span className="size-1.5 rounded-full bg-published pulse-dot" />
        Public demo mode · all profiles are <b className="font-medium">synthetic</b> fixtures. Not medical advice.
      </div>
      <div className="flex min-h-0 flex-1">
        <aside className="flex w-60 flex-col border-r border-line bg-card/70 p-5">
          <div className="flex items-center gap-2.5">
            <Helix />
            <div>
              <div className="font-serif text-2xl leading-none">Strand</div>
              <div className="font-mono text-[10px] uppercase tracking-widest text-mute">DNA agent</div>
            </div>
          </div>

          <nav className="mt-8 space-y-1">
            {nav.map(([id, label]) => (
              <button
                key={id}
                onClick={() => setView(id)}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition ${view === id ? 'bg-ink text-paper' : 'hover:bg-ink/6'}`}
              >
                <span className="font-mono text-[10px] opacity-60">0{nav.findIndex((n) => n[0] === id) + 1}</span>
                {label}
              </button>
            ))}
          </nav>

          <div className="mt-8">
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-mute">Profile</div>
            {['Ava', 'Sam'].map((p) => (
              <button
                key={p}
                onClick={() => setProfile(p)}
                className={`mb-1.5 flex w-full items-center gap-3 rounded-xl border px-3 py-2 text-left transition ${profile === p ? 'border-ink bg-white' : 'border-line hover:border-ink/40'}`}
              >
                <span className={`grid size-8 place-items-center rounded-full font-serif text-white ${p === 'Ava' ? 'bg-inherited' : 'bg-model'}`}>{p[0]}</span>
                <span className="flex-1 text-sm">{p}<div className="font-mono text-[10px] text-mute">VCF · wearable · CpG</div></span>
                <Synthetic />
              </button>
            ))}
          </div>

          <div className="mt-auto rounded-xl border border-line bg-paper p-3">
            <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.14em] text-mute">Evidence key</div>
            <div className="space-y-1.5">
              {(Object.keys(catMeta) as Cat[]).map((c) => <div key={c}><CatTag c={c} /></div>)}
            </div>
          </div>
        </aside>

        <main className="helix-bg min-w-0 flex-1 overflow-y-auto">
          <div key={view + profile} className="h-full"><View /></div>
        </main>
      </div>
    </div>
  )
}
