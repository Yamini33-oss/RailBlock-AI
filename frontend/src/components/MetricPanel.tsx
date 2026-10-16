import type { ElementType } from 'react'
import { ArrowDownRight, ArrowRight, ArrowUpRight } from 'lucide-react'
import type { MetricDelta } from '../types'

export type Accent = 'teal' | 'amber' | 'green' | 'blue' | 'red' | 'violet'

const ACCENT: Record<Accent, string> = {
  teal: 'bg-neon/15 text-neon',
  amber: 'bg-warn/15 text-warn',
  green: 'bg-neon/15 text-neon',
  blue: 'bg-blue/15 text-blue',
  red: 'bg-crit/15 text-crit',
  violet: 'bg-violet/15 text-violet',
}

interface Props {
  label: string
  value: number | string
  icon: ElementType
  accent: Accent
  delta?: MetricDelta
}

export default function MetricPanel({ label, value, icon: Icon, accent, delta }: Props) {
  const Arrow = delta?.direction === 'up' ? ArrowUpRight : delta?.direction === 'down' ? ArrowDownRight : ArrowRight
  return (
    <div className="rounded-lg border border-line bg-panel/90 p-3.5">
      <div className="flex items-center gap-2.5">
        <span className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-md ${ACCENT[accent]}`}>
          <Icon className="h-4 w-4" />
        </span>
        <span className="text-xs font-medium text-ink/90">{label}</span>
      </div>
      <div className="mt-3 font-display text-3xl font-semibold leading-none">{value}</div>
      <div className="mt-1.5 text-[11px] font-medium text-teal">Demo data</div>
      {delta && (
        <div className="mt-2 flex items-center gap-1 text-[11px] text-muted">
          <Arrow className="h-3 w-3 text-neon" />
          {delta.text}
        </div>
      )}
    </div>
  )
}
