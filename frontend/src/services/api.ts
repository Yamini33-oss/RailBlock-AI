
import type { ModuleStatus } from '../types'

export const API_BASE: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export interface ServiceHealth {
  name: string
  endpoint: string
  status: ModuleStatus
}

// Check the health of an individual service
async function checkService(
  name: string,
  endpoint: string,
): Promise<ServiceHealth> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 3000)

  try {
    const response = await fetch(endpoint, {
      signal: controller.signal,
    })

    return {
      name,
      endpoint,
      status: response.ok ? 'CONNECTED' : 'ERROR',
    }
  } catch {
    return {
      name,
      endpoint,
      status: 'NOT CONNECTED',
    }
  } finally {
    clearTimeout(timer)
  }
}

// Check the main backend
export async function checkBackendHealth(): Promise<ModuleStatus> {
  const result = await checkService(
    'Main Backend',
    `${API_BASE}/api/health`,
  )

  return result.status
}

// Check all four backend services
export async function checkAllServices(): Promise<ServiceHealth[]> {
  return Promise.all([
    checkService(
      'Main Backend (Member 1)',
      `${API_BASE}/api/health`,
    ),
    checkService(
      'ML Delay Prediction (Member 2)',
      'http://127.0.0.1:8005/health',
    ),
    checkService(
      'Window Optimization (Member 3)',
      `${API_BASE}/api/optimizer/health`,
    ),
    checkService(
      'Conflict Detection (Member 4)',
      `${API_BASE}/api/member4/health`,
    ),
  ])
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

// Send a new maintenance request to the backend
export async function submitMaintenanceRequest(
  request: MaintenanceRequest,
) {
  const response = await fetch(`${API_BASE}/api/maintenance-requests`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(request),
  })

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`)
  }

  return response.json()
}

// Retrieve all saved maintenance requests
export async function getMaintenanceRequests(): Promise<{
  count: number
  requests: SavedMaintenanceRequest[]
}> {
  const response = await fetch(`${API_BASE}/api/maintenance-requests`)

  if (!response.ok) {
    throw new Error(`Failed to fetch requests: ${response.status}`)
  }

  return response.json()
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
