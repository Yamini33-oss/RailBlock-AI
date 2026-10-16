
import { useEffect, useState } from 'react'
import {
  Activity,
  Database,
  Brain,
  CalendarClock,
  ShieldCheck,
  RefreshCw,
} from 'lucide-react'
import { checkAllServices } from '../services/api'
import type { ServiceHealth } from '../services/api'

const teamModules = [
  {
    name: 'Schedule & Traffic Data',
    owner: 'Member 1',
    description: 'Train schedules, traffic and maintenance data',
    icon: Database,
    serviceIndex: 0,
  },
  {
    name: 'ML Delay Prediction',
    owner: 'Member 2',
    description: 'Predicting possible train delays',
    icon: Brain,
    serviceIndex: 1,
  },
  {
    name: 'Window Optimization',
    owner: 'Member 3',
    description: 'Selecting suitable maintenance windows',
    icon: CalendarClock,
    serviceIndex: 2,
  },
  {
    name: 'Conflict Detection',
    owner: 'Member 4',
    description: 'Detecting schedule overlaps and validating windows',
    icon: ShieldCheck,
    serviceIndex: 3,
  },
]

function statusStyle(status: string) {
  if (status === 'CONNECTED') {
    return 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
  }

  if (status === 'ERROR' || status === 'NOT CONNECTED') {
    return 'border-red-500/30 bg-red-500/10 text-red-400'
  }

  if (status === 'CHECKING') {
    return 'border-blue-500/30 bg-blue-500/10 text-blue-400'
  }

  return 'border-amber-500/30 bg-amber-500/10 text-amber-400'
}

export default function ModuleStatusPage() {
  const [services, setServices] = useState<ServiceHealth[]>([])
  const [checking, setChecking] = useState(false)
  const [hasChecked, setHasChecked] = useState(false)

  async function checkModules() {
    setChecking(true)

    try {
      const results = await checkAllServices()
      setServices(results)
    } catch {
      setServices([])
    } finally {
      setHasChecked(true)
      setChecking(false)
    }
  }

  useEffect(() => {
    void checkModules()
  }, [])

  const modulesConnected = services.filter(
    (service) => service.status === 'CONNECTED',
  ).length

  const overallStatus = !hasChecked
    ? 'CHECKING'
    : services.length === 4 && modulesConnected === 4
      ? 'ALL CONNECTED'
      : modulesConnected > 0
        ? 'PARTIALLY CONNECTED'
        : 'NOT CONNECTED'

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          System / Integration
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          Module Status
        </h1>

        <p className="mt-2 text-sm text-muted">
          Monitor the live health of the backend and team services.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          TEAM INTEGRATION MONITOR
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Overall Service Status</p>
          <p className="mt-2 text-xl font-bold">{overallStatus}</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Services Connected</p>
          <p className="mt-2 text-3xl font-bold">
            {modulesConnected}/{hasChecked ? services.length : 4}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Services Monitored</p>
          <p className="mt-2 text-3xl font-bold">4</p>
          <p className="mt-1 text-xs text-muted">
            Live health endpoint checks
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity size={20} />
            <h2 className="text-lg font-bold">Integration Health</h2>
          </div>

          <button
            type="button"
            onClick={() => void checkModules()}
            disabled={checking}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw
              size={15}
              className={checking ? 'animate-spin' : ''}
            />
            {checking ? 'Checking...' : 'Check Again'}
          </button>
        </div>

        <div className="space-y-3">
          {teamModules.map((module) => {
            const Icon = module.icon
            const service = services[module.serviceIndex]
            const status = !hasChecked
              ? 'CHECKING'
              : service?.status ?? 'NOT CONNECTED'

            return (
              <div
                key={module.name}
                className="flex flex-col gap-3 rounded-lg border border-border p-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex items-center gap-3">
                  <Icon size={22} />

                  <div>
                    <p className="font-semibold">{module.name}</p>
                    <p className="mt-1 text-xs text-muted">
                      {module.owner} · {module.description}
                    </p>
                    <p className="mt-1 break-all text-xs text-muted">
                      {service?.endpoint ?? 'Endpoint unavailable'}
                    </p>
                  </div>
                </div>

                <span
                  className={`w-fit rounded-full border px-3 py-1 text-xs font-semibold ${statusStyle(status)}`}
                >
                  {status}
                </span>
              </div>
            )
          })}
        </div>

        <p className="mt-5 text-xs text-muted">
          CONNECTED means the health endpoint responded successfully.
          It does not guarantee that all features or data integrations
          are complete. Health checks verify availability, not full
          functional integration.
        </p>
      </div>
    </div>
  )
}
