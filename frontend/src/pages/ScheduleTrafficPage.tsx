import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  AlertTriangle,
  Clock3,
  RefreshCw,
  Search,
  TrainFront,
} from 'lucide-react'
import { getMaintenanceRequests } from '../services/api'
import type { SavedMaintenanceRequest } from '../services/api'

type FilterStatus = 'All' | 'High' | 'Critical' | 'Medium' | 'Low'

const priorityStyles: Record<string, string> = {
  Critical: 'bg-red-500/10 text-red-400',
  High: 'bg-amber-500/10 text-amber-400',
  Medium: 'bg-blue-500/10 text-blue-400',
  Low: 'bg-green-500/10 text-green-400',
}

export default function ScheduleTrafficPage() {
  const [requests, setRequests] = useState<SavedMaintenanceRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [priority, setPriority] = useState<FilterStatus>('All')

  const loadRequests = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true)
    else setLoading(true)

    setError('')

    try {
      const data = await getMaintenanceRequests()
      setRequests(data.requests ?? [])
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Unable to retrieve maintenance requests.',
      )
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void loadRequests()
  }, [loadRequests])

  const filteredRequests = useMemo(() => {
    const query = search.trim().toLowerCase()

    return requests.filter((request) => {
      const matchesSearch =
        request.request_id.toLowerCase().includes(query) ||
        request.track_section.toLowerCase().includes(query) ||
        request.maintenance_type.toLowerCase().includes(query)

      const matchesPriority =
        priority === 'All' ||
        request.priority.toLowerCase() === priority.toLowerCase()

      return matchesSearch && matchesPriority
    })
  }, [requests, search, priority])

  const trackSections = useMemo(
    () => [...new Set(requests.map((request) => request.track_section))],
    [requests],
  )

  const totalHours = requests.reduce(
    (total, request) => total + Number(request.duration_hours || 0),
    0,
  )

  const criticalCount = requests.filter(
    (request) => request.priority.toLowerCase() === 'critical',
  ).length

  const highCount = requests.filter(
    (request) => request.priority.toLowerCase() === 'high',
  ).length

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <header>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Maintenance Planning
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          Smart Maintenance Schedule
        </h1>

        <p className="mt-2 text-sm text-muted">
          Review saved maintenance requests by track, duration, and priority.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-emerald-500/30 bg-emerald-500/5 px-3 py-1 text-xs font-semibold text-emerald-400">
          REQUESTS LOADED FROM BACKEND
        </p>
      </header>

      {error && (
        <div
          role="alert"
          className="flex flex-col gap-3 rounded-xl border border-red-500/30 bg-red-500/5 p-4 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="flex items-start gap-2">
            <AlertTriangle size={20} className="mt-0.5 shrink-0 text-red-400" />
            <div>
              <p className="font-semibold text-red-400">
                Could not load maintenance requests
              </p>
              <p className="mt-1 text-sm text-muted">{error}</p>
            </div>
          </div>

          <button
            onClick={() => void loadRequests(true)}
            className="rounded-lg border border-border px-3 py-2 text-sm hover:bg-background"
          >
            Try again
          </button>
        </div>
      )}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          title="Saved Requests"
          value={requests.length}
          icon={<TrainFront size={20} />}
        />

        <MetricCard
          title="Track Sections"
          value={trackSections.length}
          icon={<Clock3 size={20} />}
        />

        <MetricCard
          title="High Priority"
          value={highCount}
          icon={<AlertTriangle size={20} />}
          color="text-amber-400"
        />

        <MetricCard
          title="Critical Priority"
          value={criticalCount}
          icon={<AlertTriangle size={20} />}
          color="text-red-400"
        />
      </section>

      <section className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-lg font-bold">Maintenance Workload by Track</h2>
            <p className="mt-1 text-sm text-muted">
              Total requested duration: {totalHours} hours
            </p>
          </div>

          <button
            onClick={() => void loadRequests(true)}
            disabled={refreshing}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-border px-3 py-2 text-sm hover:bg-background disabled:opacity-50"
          >
            <RefreshCw
              size={15}
              className={refreshing ? 'animate-spin' : ''}
            />
            {refreshing ? 'Refreshing...' : 'Refresh data'}
          </button>
        </div>

        {loading ? (
          <p className="py-12 text-center text-sm text-muted">
            Loading saved requests from the backend...
          </p>
        ) : requests.length === 0 ? (
          <div className="py-12 text-center">
            <TrainFront size={28} className="mx-auto text-muted" />
            <p className="mt-3 font-semibold">No saved requests found</p>
            <p className="mt-1 text-sm text-muted">
              Submit a maintenance request to populate this view.
            </p>
          </div>
        ) : (
          <div className="mt-6 space-y-5">
            {trackSections.map((track) => {
              const trackRequests = requests.filter(
                (request) => request.track_section === track,
              )

              const hours = trackRequests.reduce(
                (sum, request) =>
                  sum + Number(request.duration_hours || 0),
                0,
              )

              const maxHours = Math.max(totalHours, 1)
              const width = Math.max((hours / maxHours) * 100, 2)

              return (
                <div key={track}>
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-semibold">{track}</p>
                    <p className="text-xs text-muted">
                      {trackRequests.length} request(s) · {hours} requested hours
                    </p>
                  </div>

                  <div
                    className="h-4 overflow-hidden rounded-full bg-background"
                    role="img"
                    aria-label={`${track}: ${hours} requested maintenance hours`}
                  >
                    <div
                      className="h-full rounded-full bg-amber-500 transition-all"
                      style={{ width: `${width}%` }}
                    />
                  </div>

                  <div className="mt-3 flex flex-wrap gap-2">
                    {trackRequests.map((request) => (
                      <span
                        key={request.request_id}
                        title={`${request.maintenance_type}, ${request.duration_hours} hours`}
                        className={`rounded-md border border-border px-2 py-1 text-xs ${
                          priorityStyles[request.priority] ??
                          'bg-background text-muted'
                        }`}
                      >
                        {request.request_id} · {request.duration_hours}h
                      </span>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        <p className="mt-6 border-t border-border pt-4 text-xs text-muted">
          This visualization shows requested workload only. It does not represent
          an approved timetable, train occupancy, or an optimizer-approved window.
        </p>
      </section>

      <section className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h2 className="text-lg font-bold">Saved Maintenance Requests</h2>
            <p className="mt-1 text-sm text-muted">
              Search and filter requests retrieved from the database.
            </p>
          </div>

          <div className="flex flex-col gap-3 sm:flex-row">
            <div className="relative">
              <Search
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-muted"
              />
              <input
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Search ID, type, track"
                aria-label="Search maintenance requests"
                className="w-full rounded-lg border border-border bg-background py-2 pl-9 pr-3 text-sm outline-none focus:border-amber-500 sm:w-56"
              />
            </div>

            <select
              value={priority}
              onChange={(event) =>
                setPriority(event.target.value as FilterStatus)
              }
              aria-label="Filter by priority"
              className="rounded-lg border border-border bg-background px-3 py-2 text-sm"
            >
              <option value="All">All priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High</option>
              <option value="Medium">Medium</option>
              <option value="Low">Low</option>
            </select>
          </div>
        </div>

        {loading ? (
          <p className="py-10 text-center text-sm text-muted">
            Loading requests...
          </p>
        ) : (
          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[800px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted">
                  <th className="px-3 py-3">Request ID</th>
                  <th className="px-3 py-3">Track</th>
                  <th className="px-3 py-3">Maintenance Type</th>
                  <th className="px-3 py-3">Duration</th>
                  <th className="px-3 py-3">Priority</th>
                  <th className="px-3 py-3">Submitted At</th>
                </tr>
              </thead>

              <tbody>
                {filteredRequests.map((request) => (
                  <tr
                    key={request.request_id}
                    className="border-b border-border last:border-0 hover:bg-background/50"
                  >
                    <td className="px-3 py-4 font-semibold">
                      {request.request_id}
                    </td>
                    <td className="px-3 py-4">{request.track_section}</td>
                    <td className="px-3 py-4">{request.maintenance_type}</td>
                    <td className="px-3 py-4">
                      {request.duration_hours} hours
                    </td>
                    <td className="px-3 py-4">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                          priorityStyles[request.priority] ??
                          'bg-background text-muted'
                        }`}
                      >
                        {request.priority || 'Unspecified'}
                      </span>
                    </td>
                    <td className="px-3 py-4 text-muted">
                      {request.created_at
                        ? new Date(request.created_at).toLocaleString()
                        : 'Not available'}
                    </td>
                  </tr>
                ))}

                {filteredRequests.length === 0 && (
                  <tr>
                    <td
                      colSpan={6}
                      className="px-3 py-10 text-center text-muted"
                    >
                      No requests match the selected filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}

function MetricCard({
  title,
  value,
  icon,
  color = 'text-foreground',
}: {
  title: string
  value: number
  icon: React.ReactNode
  color?: string
}) {
  return (
    <div className="rounded-xl border border-border bg-panel p-5">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted">{title}</p>
        <span className="text-muted">{icon}</span>
      </div>
      <p className={`mt-3 text-3xl font-bold ${color}`}>{value}</p>
      <p className="mt-1 text-xs text-muted">Backend data</p>
    </div>
  )
}