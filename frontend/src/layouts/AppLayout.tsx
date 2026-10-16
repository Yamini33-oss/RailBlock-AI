import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import {
  BarChart3, CalendarClock, Cpu, FilePlus2, FlaskConical, History,
  LayoutDashboard, PanelLeftClose, PanelLeftOpen, Search, ShieldAlert, TrainFront,
} from 'lucide-react'
import { useBackendStatus } from '../services/useBackendStatus'
import StatusBadge from '../components/StatusBadge'
import { LogoMark, SidebarTrain } from '../components/RailArt'
import type { ModuleStatus } from '../types'

const NAV = [
  { to: '/', label: 'Operations', icon: LayoutDashboard },
  { to: '/request', label: 'Maintenance Request', icon: FilePlus2 },
  { to: '/schedule', label: 'Schedule & Traffic', icon: TrainFront },
  { to: '/recommendation', label: 'Recommended Window', icon: CalendarClock },
  { to: '/conflicts', label: 'Conflict Center', icon: ShieldAlert },
  { to: '/compare', label: 'Window Comparison', icon: BarChart3 },
  { to: '/whatif', label: 'What-if Simulation', icon: FlaskConical },
  { to: '/history', label: 'Decision History', icon: History },
  { to: '/modules', label: 'Module Status', icon: Cpu },
]

export interface LayoutContext {
  backendStatus: ModuleStatus
  query: string
}

const DOT: Record<ModuleStatus, string> = {
  CONNECTED: 'bg-neon',
  'NOT CONNECTED': 'bg-crit',
  'DEMO MODE': 'bg-warn',
  ERROR: 'bg-crit',
}

const TEXT: Record<ModuleStatus, string> = {
  CONNECTED: 'text-neon',
  'NOT CONNECTED': 'text-crit',
  'DEMO MODE': 'text-warn',
  ERROR: 'text-crit',
}

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(() => window.innerWidth < 1024)
  const [query, setQuery] = useState('')
  const backendStatus = useBackendStatus()

  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth < 900) setCollapsed(true)
    }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  return (
    <div className="flex h-screen text-ink">
      <aside
        className={`flex shrink-0 flex-col border-r border-line bg-sidebar transition-[width] duration-150 ${
          collapsed ? 'w-16' : 'w-60'
        }`}
      >
        <div className="flex h-16 items-center gap-3 px-4">
          <LogoMark className="h-9 w-9 shrink-0" />
          {!collapsed && (
            <div className="min-w-0 leading-tight">
              <div className="font-display text-lg font-bold tracking-wide text-ink">KAVACH BIE</div>
              <div className="truncate text-[10px] text-muted">Railway Maintenance Intelligence</div>
            </div>
          )}
        </div>

        <nav className="flex-1 space-y-1 overflow-y-auto px-2.5 py-3">
          {NAV.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              title={label}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-3 py-2.5 text-[13px] font-medium ${
                  isActive
                    ? 'bg-neon/90 text-bg shadow-[0_0_14px_rgba(47,229,138,0.25)]'
                    : 'text-ink/75 hover:bg-panel-2 hover:text-ink'
                }`
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {!collapsed && (
          <div className="px-3 pb-2">
            <SidebarTrain />
            <div className="mt-2 border-t border-line pt-3 text-[11px] leading-snug text-muted">
              Smarter Maintenance.
              <br />
              Safer Journeys.
            </div>
          </div>
        )}
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-16 shrink-0 items-center gap-3 border-b border-line bg-sidebar/80 px-4">
          <button
            onClick={() => setCollapsed((c) => !c)}
            className="rounded p-1.5 text-muted hover:bg-panel-2 hover:text-ink"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
          </button>

          <label className="relative max-w-md flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search events by track, status or text"
              aria-label="Search events"
              className="w-full rounded-full border border-line bg-panel py-2 pl-9 pr-3 text-xs text-ink placeholder:text-muted focus:border-neon/60"
            />
          </label>

          <div className="ml-auto flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full border border-line bg-panel px-3 py-1.5">
              <span className={`h-2 w-2 rounded-full ${DOT[backendStatus]}`} />
              <span className="font-mono text-[10px] uppercase tracking-wider text-muted">Backend</span>
              <span className={`font-mono text-[10px] font-semibold uppercase tracking-wider ${TEXT[backendStatus]}`}>
                {backendStatus}
              </span>
            </div>
            <StatusBadge tone="warn">Demo data</StatusBadge>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-5">
          <Outlet context={{ backendStatus, query } satisfies LayoutContext} />
        </main>
      </div>
    </div>
  )
}
