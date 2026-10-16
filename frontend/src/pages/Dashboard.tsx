
import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowRight,
  CalendarRange,
  CheckCircle2,
  Clock3,
  FileText,
  Info,
  Layers,
  ListChecks,
  SearchX,
  TrainTrack,
} from 'lucide-react'

import type { LayoutContext } from '../layouts/AppLayout'
import Panel from '../components/Panel'
import MetricPanel from '../components/MetricPanel'
import StatusBadge from '../components/StatusBadge'
import TrackTimeline from '../components/TrackTimeline'
import { HeroArt } from '../components/RailArt'
import { toneForSeverity } from '../components/statusTone'

import {
  DEMO_DELTAS,
  DEMO_EVENTS,
  DEMO_METRICS,
  DEMO_TIMELINE,
  DEMO_TRACKS,
} from '../data/demoData'

import type {
  ModuleInfo,
  ModuleStatus,
  Severity,
} from '../types'

import {
  getMaintenanceRequests,
  checkAllServices,
} from '../services/api'

const DemoTag = () => (
  <StatusBadge tone="warn">Demo data</StatusBadge>
)

const SEV_LABEL: Record<Severity, string> = {
  ok: 'OK',
  warn: 'WARN',
  crit: 'CRIT',
  info: 'INFO',
}

const MOD_DOT: Record<ModuleStatus, string> = {
  CONNECTED: 'bg-neon',
  'NOT CONNECTED': 'bg-warn',
  'DEMO MODE': 'bg-warn',
  ERROR: 'bg-crit',
}

const MOD_BADGE: Record<ModuleStatus, string> = {
  CONNECTED: 'border-neon/40 bg-neon/10 text-neon',
  'NOT CONNECTED': 'border-warn/40 bg-warn/10 text-warn',
  'DEMO MODE': 'border-warn/40 bg-warn/10 text-warn',
  ERROR: 'border-crit/40 bg-crit/10 text-crit',
}

function formatStamp(d: Date) {
  const date = d.toLocaleDateString('en-GB', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    timeZone: 'Asia/Kolkata',
  })

  const time = d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
    timeZone: 'Asia/Kolkata',
  })

  return `${date} ${time} IST`
}

export default function Dashboard() {
  const { backendStatus, query } =
    useOutletContext<LayoutContext>()

  const [loadedAt] = useState(() => new Date())
  const [requestCount, setRequestCount] =
    useState<number | null>(null)
  const [requestError, setRequestError] = useState('')
  const [requestLoading, setRequestLoading] = useState(true)

  const [liveServices, setLiveServices] = useState<
    Awaited<ReturnType<typeof checkAllServices>> | null
  >(null)

  // Load the actual maintenance request count.
  useEffect(() => {
    let active = true

    async function loadRequests() {
      setRequestLoading(true)

      try {
        const data = await getMaintenanceRequests()

        if (active) {
          setRequestCount(data.count)
          setRequestError('')
        }
      } catch {
        if (active) {
          setRequestCount(null)
          setRequestError(
            'Could not load saved requests. Check the backend.',
          )
        }
      } finally {
        if (active) {
          setRequestLoading(false)
        }
      }
    }

    void loadRequests()

    return () => {
      active = false
    }
  }, [])

  // Check the live health endpoints for Modules 1-4.
  useEffect(() => {
    let active = true

    async function loadModuleStatus() {
      try {
        const results = await checkAllServices()

        if (active) {
          setLiveServices(results)
        }
      } catch {
        if (active) {
          setLiveServices([])
        }
      }
    }

    void loadModuleStatus()

    return () => {
      active = false
    }
  }, [])

  const m = DEMO_METRICS

  const moduleNames = [
    'Train data and maintenance input',
    'AI/ML delay prediction',
    'Block planning and optimization',
    'Conflict detection and validation',
  ]

  const modules: ModuleInfo[] = [
    ...moduleNames.map((name, index) => {
      const service = liveServices?.[index]

      const status: ModuleStatus =
        liveServices === null
          ? 'DEMO MODE'
          : service?.status === 'CONNECTED'
            ? 'CONNECTED'
            : 'NOT CONNECTED'

      return {
        member: index + 1,
        name,
        role: `Module ${index + 1}`,
        status,
      }
    }),
    {
      member: 5,
      name: 'Frontend, backend and integration',
      role: 'Module 5',
      status: backendStatus,
    },
  ]

  const q = query.trim().toLowerCase()

  const events = q
    ? DEMO_EVENTS.filter((e) =>
        [e.text, e.track, SEV_LABEL[e.severity], e.time].some(
          (s) => s.toLowerCase().includes(q),
        ),
      )
    : DEMO_EVENTS

  return (
    <div className="mx-auto max-w-[1280px] space-y-4">
      {/* Dashboard header */}
      <section className="relative overflow-hidden rounded-lg border border-line">
        <HeroArt />

        <div className="relative flex min-h-[220px] flex-col justify-between p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div className="font-display text-xs font-semibold tracking-[0.2em] text-neon">
                KAVACH BIE
              </div>

              <h1 className="mt-2 font-display text-3xl font-bold leading-tight text-ink md:text-4xl">
                Railway Operations Dashboard
              </h1>

              <p className="mt-2 max-w-sm text-sm text-ink/80">
                AI-powered maintenance planning for a safer, more
                efficient railway network.
              </p>
            </div>

            <div className="hidden shrink-0 rounded-md border border-line bg-bg/70 px-3 py-2 text-right backdrop-blur sm:block">
              <DemoTag />
              <div className="mt-1.5 text-[10px] text-muted">
                Page loaded
              </div>
              <div className="font-mono text-[11px] text-ink">
                {formatStamp(loadedAt)}
              </div>
            </div>
          </div>

          <p className="mt-4 text-[11px] text-ink/70">
            Live request count and module health are fetched from
            backend endpoints. Other sample metrics and timeline
            values are demo data.
          </p>
        </div>
      </section>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <MetricPanel
          label="Total Requests"
          value={
            requestLoading
              ? '...'
              : requestCount !== null
                ? requestCount
                : 'N/A'
          }
          icon={FileText}
          accent="teal"
        />

        <MetricPanel
          label="Pending"
          value={m.pending}
          icon={Clock3}
          accent="amber"
          delta={DEMO_DELTAS.pending}
        />

        <MetricPanel
          label="Approved"
          value={m.approved}
          icon={CheckCircle2}
          accent="green"
          delta={DEMO_DELTAS.approved}
        />

        <MetricPanel
          label="Recommended Blocks"
          value={m.recommendedBlocks}
          icon={CalendarRange}
          accent="blue"
          delta={DEMO_DELTAS.recommendedBlocks}
        />

        <MetricPanel
          label="Conflicts"
          value={m.conflicts}
          icon={AlertTriangle}
          accent="red"
          delta={DEMO_DELTAS.conflicts}
        />

        <MetricPanel
          label="Needs Attention"
          value={m.needsAttention}
          icon={ListChecks}
          accent="violet"
          delta={DEMO_DELTAS.needsAttention}
        />
      </div>

      {/* Backend request loading error */}
      {requestError && (
        <div
          role="alert"
          className="rounded-md border border-crit/40 bg-crit/10 p-3 text-sm text-crit"
        >
          {requestError}
        </div>
      )}

      {/* Timeline and module status */}
      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_340px]">
        <Panel
          title="24-Hour Railway Track Timeline"
          icon={TrainTrack}
          tag={<DemoTag />}
        >
          <TrackTimeline
            tracks={DEMO_TRACKS}
            blocks={DEMO_TIMELINE}
          />
        </Panel>

        <Panel
          title="Module Status"
          icon={Layers}
          tag={<DemoTag />}
        >
          <ul className="space-y-3.5">
            {modules.map((mod) => (
              <li
                key={mod.member}
                className="flex items-start justify-between gap-2"
              >
                <div className="flex min-w-0 items-start gap-2.5">
                  <span
                    className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${MOD_DOT[mod.status]}`}
                  />

                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-ink">
                      {mod.role}
                    </div>
                    <div className="text-[11px] leading-snug text-muted">
                      {mod.name}
                    </div>
                  </div>
                </div>

                <span
                  className={`whitespace-nowrap rounded border px-2 py-0.5 font-mono text-[10px] font-medium uppercase tracking-wide ${MOD_BADGE[mod.status]}`}
                >
                  {mod.status}
                </span>
              </li>
            ))}
          </ul>

          <div className="mt-4 flex items-start gap-2 rounded-md border border-line bg-panel-2/60 p-2.5 text-[11px] leading-snug text-muted">
            <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-neon" />
            Module statuses reflect live health endpoint checks.
            A connected endpoint confirms availability, not complete
            functional integration.
          </div>
        </Panel>
      </div>

      {/* Recent events */}
      <Panel
        title="Recent Decisions and System Events"
        icon={Clock3}
        tag={
          <div className="flex items-center gap-3">
            <DemoTag />

            <Link
              to="/history"
              className="flex items-center gap-1 text-xs text-ink/80 hover:text-neon"
            >
              View All
              <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
        }
        bodyClassName="p-0 pt-2"
      >
        {events.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-8 text-center text-sm text-muted">
            <SearchX className="h-5 w-5" />
            No demo events match "{query}". Clear the search box
            to see all events.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-[13px]">
              <thead className="sr-only">
                <tr>
                  <th>Time</th>
                  <th>Status</th>
                  <th>Event</th>
                  <th>Track</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-line-soft">
                {events.map((e, i) => (
                  <tr
                    key={i}
                    className="hover:bg-panel-2/50"
                  >
                    <td className="w-20 py-2.5 pl-4 font-mono text-xs text-muted">
                      {e.time}
                    </td>

                    <td className="w-20 py-2.5">
                      <StatusBadge tone={toneForSeverity(e.severity)}>
                        {SEV_LABEL[e.severity]}
                      </StatusBadge>
                    </td>

                    <td className="py-2.5 text-ink/90">
                      {e.text}
                    </td>

                    <td className="py-2.5 pr-4 text-right font-mono text-xs text-muted">
                      {e.track}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Panel>
    </div>
  )
}
