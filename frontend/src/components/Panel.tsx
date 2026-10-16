import type { ElementType, ReactNode } from 'react'

interface PanelProps {
  title: string
  icon?: ElementType
  tag?: ReactNode
  className?: string
  bodyClassName?: string
  children: ReactNode
}

export default function Panel({ title, icon: Icon, tag, className = '', bodyClassName = 'p-4', children }: PanelProps) {
  return (
    <section className={`rounded-lg border border-line bg-panel/90 ${className}`}>
      <header className="flex items-center justify-between gap-2 px-4 pt-3.5">
        <div className="flex items-center gap-2.5">
          {Icon && <Icon className="h-4 w-4 text-neon" />}
          <h2 className="font-display text-sm font-semibold text-ink">{title}</h2>
        </div>
        {tag}
      </header>
      <div className={bodyClassName}>{children}</div>
    </section>
  )
}
