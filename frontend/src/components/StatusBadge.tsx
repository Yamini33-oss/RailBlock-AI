import type { ReactNode } from 'react'
import type { Tone } from './statusTone'

const TONE: Record<Tone, string> = {
  ok: 'border-neon/40 bg-neon/10 text-neon',
  warn: 'border-warn/40 bg-warn/10 text-warn',
  crit: 'border-crit/40 bg-crit/10 text-crit',
  idle: 'border-line bg-panel-2 text-muted',
}

export default function StatusBadge({ tone, children }: { tone: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wider ${TONE[tone]}`}
    >
      {children}
    </span>
  )
}
