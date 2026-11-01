import type { ReactNode } from 'react'

export type Cat = 'inherited' | 'measured' | 'published' | 'model'
export const catMeta: Record<Cat, { label: string; cls: string; dot: string }> = {
  inherited: { label: 'Inherited', cls: 'text-inherited bg-inherited/10 border-inherited/25', dot: 'bg-inherited' },
  measured: { label: 'Measured', cls: 'text-measured bg-measured/10 border-measured/25', dot: 'bg-measured' },
  published: { label: 'Published', cls: 'text-published bg-published/10 border-published/25', dot: 'bg-published' },
  model: { label: 'Model prediction', cls: 'text-model bg-model/10 border-model/25', dot: 'bg-model' },
}

export function CatTag({ c, children }: { c: Cat; children?: ReactNode }) {
  const m = catMeta[c]
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${m.cls}`}>
      <span className={`size-1.5 rounded-full ${m.dot}`} />
      {children ?? m.label}
    </span>
  )
}

export function Synthetic() {
  return (
    <span className="inline-flex items-center rounded border border-dashed border-ink/40 px-1.5 py-px font-mono text-[10px] uppercase tracking-wider text-ink/70">
      synthetic
    </span>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-2xl border border-line bg-card ${className}`}>{children}</div>
}

export function Eyebrow({ children }: { children: ReactNode }) {
  return <div className="font-mono text-[11px] uppercase tracking-[0.14em] text-mute">{children}</div>
}

export function rng(seed: number) {
  let s = seed
  return () => ((s = (s * 16807) % 2147483647) / 2147483647)
}
