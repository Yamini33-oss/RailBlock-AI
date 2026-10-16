import type { MetricDelta, MetricKey, ModuleInfo, SystemEvent, TimelineBlock } from '../types'

// Every value in this file is fictional demonstration data.
// None of it comes from a live railway system.

export const DEMO_METRICS: Record<MetricKey, number> & { rejected: number } = {
  totalRequests: 24,
  pending: 7,
  approved: 15,
  rejected: 2,
  recommendedBlocks: 12,
  conflicts: 3,
  needsAttention: 5,
}

export const DEMO_DELTAS: Record<MetricKey, MetricDelta> = {
  totalRequests: { text: '+2 since last 24h', direction: 'up' },
  pending: { text: '1 since last 24h', direction: 'down' },
  approved: { text: '3 since last 24h', direction: 'up' },
  recommendedBlocks: { text: '2 since last 24h', direction: 'up' },
  conflicts: { text: '1 since last 24h', direction: 'down' },
  needsAttention: { text: '0 since last 24h', direction: 'flat' },
}

export const DEMO_TRACKS = ['TRK-A', 'TRK-B', 'TRK-C', 'TRK-D']

export const DEMO_TIMELINE: TimelineBlock[] = [
  { id: 'a1', track: 'TRK-A', startHour: 3.8, endHour: 8.2, kind: 'occupancy', label: 'Train occupancy 03:48-08:12' },
  { id: 'a2', track: 'TRK-A', startHour: 9.2, endHour: 9.9, kind: 'pending', label: 'Pending window 09:12-09:54' },
  { id: 'a3', track: 'TRK-A', startHour: 14.2, endHour: 15, kind: 'recommended', label: 'Recommended block 14:12-15:00' },
  { id: 'a4', track: 'TRK-A', startHour: 19, endHour: 20, kind: 'occupancy', label: 'Train occupancy 19:00-20:00' },

  { id: 'b1', track: 'TRK-B', startHour: 0, endHour: 3.6, kind: 'occupancy', label: 'Train occupancy 00:00-03:36' },
  { id: 'b2', track: 'TRK-B', startHour: 4.6, endHour: 5.3, kind: 'pending', label: 'Pending window 04:36-05:18' },
  { id: 'b3', track: 'TRK-B', startHour: 7.8, endHour: 9.8, kind: 'conflict', label: 'Conflict: schedule overlap 07:48-09:48' },
  { id: 'b4', track: 'TRK-B', startHour: 18, endHour: 18.6, kind: 'pending', label: 'Pending window 18:00-18:36' },

  { id: 'c1', track: 'TRK-C', startHour: 6.8, endHour: 7.4, kind: 'pending', label: 'Pending window 06:48-07:24' },
  { id: 'c2', track: 'TRK-C', startHour: 10.5, endHour: 11.1, kind: 'pending', label: 'Pending window 10:30-11:06' },
  { id: 'c3', track: 'TRK-C', startHour: 15, endHour: 15.6, kind: 'pending', label: 'Pending window 15:00-15:36' },
  { id: 'c4', track: 'TRK-C', startHour: 21, endHour: 21.5, kind: 'occupancy', label: 'Train occupancy 21:00-21:30' },

  { id: 'd1', track: 'TRK-D', startHour: 9, endHour: 9.6, kind: 'pending', label: 'Pending window 09:00-09:36' },
  { id: 'd2', track: 'TRK-D', startHour: 13.2, endHour: 16, kind: 'recommended', label: 'Recommended block 13:12-16:00' },
]

export const DEMO_EVENTS: SystemEvent[] = [
  { time: '02:14', text: 'Block recommended for TRK-A (demo)', severity: 'ok', track: 'TRK-A' },
  { time: '02:09', text: 'Validation conflict flagged on TRK-B (demo)', severity: 'crit', track: 'TRK-B' },
  { time: '01:58', text: 'Request awaiting resource confirmation (demo)', severity: 'warn', track: 'TRK-D' },
  { time: '01:41', text: 'Request submitted for TRK-D (demo)', severity: 'info', track: 'TRK-D' },
  { time: '01:32', text: 'Maintenance window optimized for TRK-C (demo)', severity: 'ok', track: 'TRK-C' },
  { time: '01:12', text: 'Candidate windows generated (demo)', severity: 'info', track: '-' },
]

// Members 1-4 have no adapters yet, so nothing has been checked.
// Initial module information.
// Live health status will be supplied by the Overview page.
export const MODULES_1_TO_4: ModuleInfo[] = [
  {
    member: 1,
    name: 'Train data and maintenance input',
    role: 'Module 1',
    status: 'NOT CONNECTED',
  },
  {
    member: 2,
    name: 'AI/ML delay prediction',
    role: 'Module 2',
    status: 'NOT CONNECTED',
  },
  {
    member: 3,
    name: 'Block planning and optimization',
    role: 'Module 3',
    status: 'NOT CONNECTED',
  },
  {
    member: 4,
    name: 'Conflict detection and validation',
    role: 'Module 4',
    status: 'NOT CONNECTED',
  },
]
