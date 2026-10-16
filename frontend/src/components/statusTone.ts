import type { ModuleStatus, Severity } from '../types'

export type Tone = 'ok' | 'warn' | 'crit' | 'idle'

export function toneForStatus(status: ModuleStatus): Tone {
  switch (status) {
    case 'CONNECTED': return 'ok'
    case 'DEMO MODE': return 'warn'
    case 'ERROR': return 'crit'
    default: return 'warn'
  }
}

export function toneForSeverity(severity: Severity): Tone {
  return severity === 'info' ? 'idle' : severity
}
