import { useState } from 'react'
import {
  CalendarClock,
  Play,
  AlertTriangle,
  CheckCircle,
  Loader2,
} from 'lucide-react'
import {
  API_BASE,
  getOptimizationRecommendation,
  type OptimizationRequest,
} from '../services/api'

type ResultData = Record<string, any>

export default function BlockPlanningPage() {
  const [section, setSection] = useState('SEC-01')
  const [date, setDate] = useState('2026-10-15')
  const [startTime, setStartTime] = useState('09:10')
  const [duration, setDuration] = useState('1')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ResultData | null>(null)

  async function findWindow() {
    setError('')
    setResult(null)

    if (!date || !startTime || !duration || Number(duration) <= 0) {
      setError('Please enter a valid date, start time and duration.')
      return
    }

    const durationMinutes = Number(duration) * 60

    if (
      durationMinutes < 15 ||
      durationMinutes > 720 ||
      !Number.isFinite(durationMinutes)
    ) {
      setError('Duration must be between 0.25 and 12 hours.')
      return
    }

    if (startTime >= '18:00') {
      setError('Choose a start time before 18:00.')
      return
    }

    const timezone = '+05:30'
    const planningStart = `${date}T09:00:00${timezone}`
    const planningEnd = `${date}T18:00:00${timezone}`
    const earliestStart = `${date}T${startTime}:00${timezone}`

    const request: OptimizationRequest = {
      request_id: `KAVACH-${Date.now()}`,
      track_section_id: section,
      planning_start: planningStart,
      planning_end: planningEnd,
      required_duration_minutes: durationMinutes,
      maintenance_priority: 'MEDIUM',
      required_resources: [],
      earliest_start_time: earliestStart,
      latest_end_time: planningEnd,
      task_dependencies: [],
      existing_approved_blocks: [],
      config: {
        step_minutes: 15,
        max_validation_attempts: 5,
        solver_time_limit_seconds: 10,
        max_alternatives: 5,
        weights: {
          weight_delay: 0.4,
          weight_trains: 0.3,
          weight_traffic_density: 0.15,
          weight_slack_duration: 0.05,
          weight_priority_urgency: 0.1,
        },
        default_timezone: 'Asia/Kolkata',
        allow_unvalidated_fallback: false,
      },
    }

    setLoading(true)

    try {
      const data = await getOptimizationRecommendation(request)
      setResult(data)

      if (
        data.status &&
        !['RECOMMENDED', 'SUCCESS', 'OPTIMAL'].includes(
          String(data.status).toUpperCase(),
        )
      ) {
        setError(`Optimizer returned status: ${data.status}`)
      }
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Could not get an optimizer recommendation.',
      )
    } finally {
      setLoading(false)
    }
  }

  const recommendation =
    result?.recommendation ?? result?.recommended_window ?? result

  const start =
    recommendation?.start_time ??
    recommendation?.recommended_start ??
    recommendation?.start ??
    recommendation?.window_start

  const end =
    recommendation?.end_time ??
    recommendation?.recommended_end ??
    recommendation?.end ??
    recommendation?.window_end

  const alternatives = Array.isArray(result?.alternatives)
    ? result.alternatives
    : Array.isArray(recommendation?.alternatives)
      ? recommendation.alternatives
      : []

  const displayValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') return 'Not provided'
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

  const formatDateTime = (value: unknown) => {
    if (typeof value !== 'string') return displayValue(value)
    const match = value.match(/T(\d{2}:\d{2})/)
    return match ? `${value.slice(0, 10)} ${match[1]}` : value
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Planning
        </p>
        <h1 className="mt-2 font-display text-2xl font-bold">
          Block Planning
        </h1>
        <p className="mt-2 text-sm text-muted">
          Find a recommended maintenance window using the AI optimization service.
        </p>
        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          SYNTHETIC DEMO DATA · NOT A REAL RAILWAY APPROVAL
        </p>
      </div>

      <div className="max-w-3xl rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="mb-5 flex items-center gap-2">
          <CalendarClock size={20} />
          <h2 className="text-lg font-bold">Find an Optimized Window</h2>
        </div>

        <div className="space-y-5">
          <div>
            <label htmlFor="section" className="mb-2 block text-sm font-medium">
              Optimizer Demo Track Section
            </label>
            <select
              id="section"
              value={section}
              onChange={(event) => {
                setSection(event.target.value)
                setResult(null)
                setError('')
              }}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm"
            >
              <option value="SEC-01">SEC-01 (verified demo section)</option>
            </select>
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor="date" className="mb-2 block text-sm font-medium">
                Planning Date
              </label>
              <input
                id="date"
                type="date"
                value={date}
                onChange={(event) => {
                  setDate(event.target.value)
                  setResult(null)
                  setError('')
                }}
                required
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm"
              />
            </div>

            <div>
              <label htmlFor="startTime" className="mb-2 block text-sm font-medium">
                Earliest Start Time
              </label>
              <input
                id="startTime"
                type="time"
                value={startTime}
                onChange={(event) => {
                  setStartTime(event.target.value)
                  setResult(null)
                  setError('')
                }}
                required
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm"
              />
            </div>

            <div>
              <label htmlFor="duration" className="mb-2 block text-sm font-medium">
                Required Duration (hours)
              </label>
              <input
                id="duration"
                type="number"
                min="0.25"
                max="12"
                step="0.25"
                value={duration}
                onChange={(event) => {
                  setDuration(event.target.value)
                  setResult(null)
                  setError('')
                }}
                required
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm"
              />
            </div>
          </div>

          <p className="text-xs text-muted">
            Planning window: 09:00 to 18:00 IST. The optimizer searches from
            your earliest start time and uses its configured demo data.
          </p>

          {error && (
            <div className="rounded-lg border border-red-500/30 p-3 text-sm text-red-400">
              {error}
            </div>
          )}

          <button
            type="button"
            onClick={findWindow}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg bg-lime-500 px-5 py-3 text-sm font-semibold text-black hover:bg-lime-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {loading ? 'Optimizing...' : 'Find Best Window'}
          </button>
        </div>
      </div>

      {result && (
        <div className="max-w-3xl rounded-xl border border-border bg-panel p-5 sm:p-7">
          <h2 className="text-lg font-bold">Optimizer Response</h2>

          <div className="mt-4 rounded-lg border border-border p-4">
            <p className="text-sm text-muted">Optimization Status</p>
            <p className="mt-1 text-xl font-bold">
              {displayValue(result.status)}
            </p>
            <p className="mt-2 text-xs text-muted">
              Section: {displayValue(result.track_section_id ?? section)}
            </p>
          </div>

          {start && end ? (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted">Recommended Start</p>
                <p className="mt-1 text-xl font-bold">
                  {formatDateTime(start)}
                </p>
              </div>
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-muted">Recommended End</p>
                <p className="mt-1 text-xl font-bold">
                  {formatDateTime(end)}
                </p>
              </div>
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted">
              The response did not contain recognizable start/end fields.
              Check the raw response below for the exact result structure.
            </p>
          )}

          <div className="mt-4 grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm text-muted">Validation</p>
              <p className="mt-1 font-semibold">
                {displayValue(
                  result.validation?.status ??
                  result.validation_status ??
                  result.validation,
                )}
              </p>
            </div>
            <div className="rounded-lg border border-border p-4">
              <p className="text-sm text-muted">Solver</p>
              <p className="mt-1 font-semibold">
                {displayValue(
                  result.solver_status ??
                  result.solver?.status ??
                  result.solver,
                )}
              </p>
            </div>
          </div>

          {String(result.validation?.validator_used ?? '')
            .toLowerCase()
            .includes('mock') && (
            <p className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-sm text-amber-400">
              Validation here came from the mock validator only, not the real
              Member 4 conflict checker. This is a student demonstration result,
              not an approved railway instruction.
            </p>
          )}

          {alternatives.length > 0 && (
            <div className="mt-5">
              <h3 className="font-bold">Alternative Windows</h3>
              <div className="mt-3 space-y-2">
                {alternatives.map((alternative: ResultData, index: number) => (
                  <div
                    key={index}
                    className="rounded-lg border border-border p-3 text-sm"
                  >
                    <p className="font-semibold">
                      {formatDateTime(
                        alternative.start_time ??
                        alternative.start ??
                        alternative.recommended_start,
                      )}
                      {' → '}
                      {formatDateTime(
                        alternative.end_time ??
                        alternative.end ??
                        alternative.recommended_end,
                      )}
                    </p>
                    <p className="mt-1 text-muted">
                      {alternative.status
                        ? `Status: ${alternative.status}`
                        : `Alternative ${index + 1}`}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {(result.estimated_affected_trains !== undefined ||
            result.predicted_delay_minutes !== undefined) && (
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              {result.estimated_affected_trains !== undefined && (
                <div className="rounded-lg border border-border p-4">
                  <p className="text-sm text-muted">Estimated Affected Trains</p>
                  <p className="mt-1 text-xl font-bold">
                    {displayValue(result.estimated_affected_trains)}
                  </p>
                </div>
              )}
              {result.predicted_delay_minutes !== undefined && (
                <div className="rounded-lg border border-border p-4">
                  <p className="text-sm text-muted">Predicted Delay (minutes)</p>
                  <p className="mt-1 text-xl font-bold">
                    {displayValue(result.predicted_delay_minutes)}
                  </p>
                </div>
              )}
            </div>
          )}

          <details className="mt-5">
            <summary className="cursor-pointer text-sm font-semibold">
              View full optimizer response
            </summary>
            <pre className="mt-3 overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-border p-4 text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
          </details>

          <div className="mt-5 flex items-start gap-2 rounded-lg border border-amber-500/30 p-4 text-sm">
            {result.status === 'RECOMMENDED' ? (
              <CheckCircle size={18} className="shrink-0 text-amber-400" />
            ) : (
              <AlertTriangle size={18} className="shrink-0 text-amber-400" />
            )}
            <p className="text-muted">
              This is an optimizer recommendation using synthetic demo data.
              It is not a live railway schedule, safety clearance, or official
              maintenance approval.
            </p>
          </div>
        </div>
      )}

      <p className="text-xs text-muted">
        API: {API_BASE}/api/optimization/recommend
      </p>
    </div>
  )
}