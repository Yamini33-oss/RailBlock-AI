
import type { ModuleStatus } from '../types'

export const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface ServiceHealth {
  name: string
  endpoint: string
  status: ModuleStatus
}

// Member 2 and Member 4 run as separate services. In development, Vite proxies
// these paths (see vite.config.ts) so the browser never makes a cross-origin call
// to a service that has no CORS configuration. Override with env vars if needed.
const MEMBER2_BASE: string = import.meta.env.VITE_MEMBER2_BASE_URL ?? '/member2'
const MEMBER4_BASE: string = import.meta.env.VITE_MEMBER4_BASE_URL ?? '/member4'

// Check the health of an individual service. An optional `verify` callback can
// inspect the JSON body so that an HTTP 200 alone is not treated as "connected".
async function checkService(
  name: string,
  endpoint: string,
  verify?: (body: any) => boolean,
): Promise<ServiceHealth> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 3000)

  try {
    const response = await fetch(endpoint, { signal: controller.signal })

    if (!response.ok) {
      return { name, endpoint, status: 'ERROR' }
    }

    if (verify) {
      const body = await response.json().catch(() => null)
      return { name, endpoint, status: verify(body) ? 'CONNECTED' : 'ERROR' }
    }

    return { name, endpoint, status: 'CONNECTED' }
  } catch {
    return { name, endpoint, status: 'NOT CONNECTED' }
  } finally {
    clearTimeout(timer)
  }
}

// Check the main backend (Member 5 / integration layer)
export async function checkBackendHealth(): Promise<ModuleStatus> {
  const result = await checkService(
    'Main Backend',
    `${API_BASE}/health`,
    (b) => b?.status === 'HEALTHY',
  )

  return result.status
}

// Check Modules 1-4. The order matters: the dashboard maps results by index.
export async function checkAllServices(): Promise<ServiceHealth[]> {
  return Promise.all([
    // Module 1: train data + maintenance input are served by the main backend.
    checkService(
      'Train Data & Maintenance Input (Member 1)',
      `${API_BASE}/api/v1/datasets`,
    ),
    checkService(
      'ML Delay Prediction (Member 2)',
      `${MEMBER2_BASE}/health`,
      (b) => b?.status === 'healthy' && b?.model_loaded === true,
    ),
    checkService(
      'Window Optimization (Member 3)',
      `${API_BASE}/api/optimization/health`,
      (b) => b?.status === 'HEALTHY' && b?.solver_readiness === 'READY',
    ),
    checkService(
      'Conflict Detection (Member 4)',
      `${MEMBER4_BASE}/health`,
      (b) => b?.status === 'OK',
    ),
  ])
}

// Turn a failed response into a readable message (FastAPI 422s carry a list).
async function readError(response: Response, fallback: string): Promise<Error> {
  const data = await response.json().catch(() => null)
  const detail = data?.detail ?? data?.message

  if (Array.isArray(detail)) {
    const text = detail
      .map((d: any) => `${(d.loc ?? []).slice(1).join('.')}: ${d.msg}`)
      .join('; ')
    return new Error(`${fallback} (${response.status}): ${text}`)
  }

  return new Error(
    detail ? `${fallback} (${response.status}): ${detail}` : `${fallback} (${response.status})`,
  )
}

// Structure of a maintenance request
export interface MaintenanceRequest {
  request_id: string
  track_section: string
  maintenance_type: string
  duration_hours: number
  priority: string
  description: string
}

// Structure of a saved maintenance request
export interface SavedMaintenanceRequest extends MaintenanceRequest {
  created_at: string
}

// The form uses friendly labels; the backend uses an enum.
const PRIORITY_TO_API: Record<string, string> = {
  low: 'LOW',
  medium: 'MEDIUM',
  high: 'HIGH',
  critical: 'EMERGENCY',
}

function priorityFromApi(value: string): string {
  const v = (value ?? '').toUpperCase()
  if (v === 'EMERGENCY') return 'Critical'
  return v.charAt(0) + v.slice(1).toLowerCase()
}

// The backend has no "maintenance type" field, so the type is stored as a
// "[Type] " prefix on the description and split back out when listing.
function splitDescription(text: string | null | undefined) {
  const match = /^\[([^\]]+)\]\s*(.*)$/s.exec(text ?? '')
  return match
    ? { type: match[1], description: match[2] }
    : { type: 'General', description: text ?? '' }
}

interface BackendMaintenanceRequest {
  request_id: string
  track_section_id: string
  required_duration_minutes: number
  maintenance_priority: string
  description?: string | null
  created_at?: string | null
}

// Send a new maintenance request to the backend (POST /api/v1/maintenance-requests)
export async function submitMaintenanceRequest(request: MaintenanceRequest) {
  // The form does not collect a planning horizon, so the request is planned
  // over the next 24 hours from submission.
  const start = new Date()
  const end = new Date(start.getTime() + 24 * 60 * 60 * 1000)

  const body = {
    request_id: request.request_id,
    track_section_id: request.track_section,
    planning_start: start.toISOString(),
    planning_end: end.toISOString(),
    required_duration_minutes: Math.round(request.duration_hours * 60),
    maintenance_priority:
      PRIORITY_TO_API[request.priority.toLowerCase()] ?? 'MEDIUM',
    required_resources: [],
    description: `[${request.maintenance_type}] ${request.description}`.trim(),
  }

  const response = await fetch(`${API_BASE}/api/v1/maintenance-requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!response.ok) {
    throw await readError(response, 'Could not submit the request')
  }

  const saved: BackendMaintenanceRequest = await response.json()

  return {
    ...saved,
    message: `Request ${saved.request_id} saved.`,
  }
}

// Retrieve saved maintenance requests (GET /api/v1/maintenance-requests).
// The backend returns a bare array; adapt it to the shape the pages expect.
export async function getMaintenanceRequests(): Promise<{
  count: number
  requests: SavedMaintenanceRequest[]
}> {
  const response = await fetch(`${API_BASE}/api/v1/maintenance-requests`)

  if (!response.ok) {
    throw await readError(response, 'Failed to fetch requests')
  }

  const list: BackendMaintenanceRequest[] = await response.json()

  if (!Array.isArray(list)) {
    throw new Error('Unexpected response from /api/v1/maintenance-requests')
  }

  const requests: SavedMaintenanceRequest[] = list.map((r) => {
    const { type, description } = splitDescription(r.description)
    return {
      request_id: r.request_id,
      track_section: r.track_section_id,
      maintenance_type: type,
      duration_hours: r.required_duration_minutes / 60,
      priority: priorityFromApi(r.maintenance_priority),
      description,
      created_at: r.created_at ?? '',
    }
  })

  return { count: requests.length, requests }
}

// Optimizer request structure
export interface OptimizationRequest {
  request_id: string
  track_section_id: string
  planning_start: string
  planning_end: string
  required_duration_minutes: number
  maintenance_priority: string
  required_resources: string[]
  earliest_start_time: string
  latest_end_time: string
  task_dependencies: string[]
  existing_approved_blocks: unknown[]
  config: {
    step_minutes: number
    max_validation_attempts: number
    solver_time_limit_seconds: number
    max_alternatives: number
    weights: {
      weight_delay: number
      weight_trains: number
      weight_traffic_density: number
      weight_slack_duration: number
      weight_priority_urgency: number
    }
    default_timezone: string
    allow_unvalidated_fallback: boolean
  }
}

// Send a request to the AI optimization engine
export async function getOptimizationRecommendation(
  request: OptimizationRequest,
) {
  const response = await fetch(
    `${API_BASE}/api/optimization/recommend`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    },
  )

  const data = await response.json().catch(() => null)

  if (!response.ok) {
    throw new Error(
      data?.detail ?? `Optimization failed: ${response.status}`,
    )
  }

  return data
}
