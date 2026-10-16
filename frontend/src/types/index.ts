export type ModuleStatus = 'CONNECTED' | 'NOT CONNECTED' | 'DEMO MODE' | 'ERROR'
export type Severity = 'info' | 'ok' | 'warn' | 'crit'

export interface ModuleInfo {
  member: number
  name: string
  role: string
  status: ModuleStatus
}

export interface SystemEvent {
  time: string
  text: string
  severity: Severity
  track: string
}

export type TimelineKind = 'occupancy' | 'recommended' | 'pending' | 'conflict'

export interface TimelineBlock {
  id: string
  track: string
  startHour: number
  endHour: number
  kind: TimelineKind
  label: string
}

export type MetricKey =
  | 'totalRequests' | 'pending' | 'approved'
  | 'recommendedBlocks' | 'conflicts' | 'needsAttention'

export interface MetricDelta {
  text: string
  direction: 'up' | 'down' | 'flat'
}
