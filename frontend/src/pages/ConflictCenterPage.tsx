import { useState } from 'react'
import { AlertTriangle, RefreshCw, ShieldCheck } from 'lucide-react'

const trainSchedules = [
  {
    id: 'TR-101',
    section: 'Tirupati-S1',
    start: 9 * 60,
    end: 9 * 60 + 10,
  },
  {
    id: 'TR-102',
    section: 'Tirupati-S1',
    start: 9 * 60 + 30,
    end: 9 * 60 + 40,
  },
  {
    id: 'TR-103',
    section: 'Tirupati-S2',
    start: 10 * 60,
    end: 10 * 60 + 8,
  },
  {
    id: 'TR-104',
    section: 'Tirupati-S2',
    start: 10 * 60 + 30,
    end: 10 * 60 + 40,
  },
  {
    id: 'TR-105',
    section: 'Tirupati-S1',
    start: 9 * 60 + 35,
    end: 9 * 60 + 45,
  },
]

const formatTime = (minutes: number) =>
  `${String(Math.floor(minutes / 60)).padStart(2, '0')}:${String(
    minutes % 60,
  ).padStart(2, '0')}`

type Conflict = {
  trainA: string
  trainB: string
  section: string
  overlapStart: number
  overlapEnd: number
}

function detectConflicts(): Conflict[] {
  const conflicts: Conflict[] = []

  for (let i = 0; i < trainSchedules.length; i++) {
    for (let j = i + 1; j < trainSchedules.length; j++) {
      const a = trainSchedules[i]
      const b = trainSchedules[j]

      if (
        a.section === b.section &&
        a.start < b.end &&
        a.end > b.start
      ) {
        conflicts.push({
          trainA: a.id,
          trainB: b.id,
          section: a.section,
          overlapStart: Math.max(a.start, b.start),
          overlapEnd: Math.min(a.end, b.end),
        })
      }
    }
  }

  return conflicts
}

export default function ConflictCenterPage() {
  const [conflicts, setConflicts] = useState<Conflict[]>(detectConflicts)
  const [lastChecked, setLastChecked] = useState('Not checked yet')

  function checkConflicts() {
    setConflicts(detectConflicts())
    setLastChecked(new Date().toLocaleTimeString())
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Validation
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          Conflict Center
        </h1>

        <p className="mt-2 text-sm text-muted">
          Check sample train movements for overlapping time intervals on the
          same track section.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          DEMO DATA · NOT OFFICIAL RAILWAY VALIDATION
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Train Movements</p>
          <p className="mt-2 text-3xl font-bold">{trainSchedules.length}</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Potential Conflicts</p>
          <p className="mt-2 text-3xl font-bold text-red-400">
            {conflicts.length}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Track Sections</p>
          <p className="mt-2 text-3xl font-bold">2</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-bold">Conflict Analysis</h2>
            <p className="mt-1 text-sm text-muted">
              {lastChecked === 'Not checked yet'
                ? 'Initial analysis of the sample schedule'
                : `Last checked at ${lastChecked}`}
            </p>
          </div>

          <button
            type="button"
            onClick={checkConflicts}
            className="inline-flex items-center gap-2 rounded-lg bg-lime-500 px-4 py-2.5 text-sm font-semibold text-black hover:bg-lime-400"
          >
            <RefreshCw size={16} />
            Check Again
          </button>
        </div>

        {conflicts.length > 0 ? (
          <div className="mt-6 overflow-x-auto">
            <div className="mb-4 flex items-center gap-2 font-semibold text-red-400">
              <AlertTriangle size={18} />
              Potential overlapping movements detected
            </div>

            <table className="w-full min-w-[600px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted">
                  <th className="px-3 py-3">Train A</th>
                  <th className="px-3 py-3">Train B</th>
                  <th className="px-3 py-3">Track Section</th>
                  <th className="px-3 py-3">Overlap Period</th>
                  <th className="px-3 py-3">Status</th>
                </tr>
              </thead>

              <tbody>
                {conflicts.map((conflict) => (
                  <tr
                    key={`${conflict.trainA}-${conflict.trainB}`}
                    className="border-b border-border"
                  >
                    <td className="px-3 py-4 font-semibold">
                      {conflict.trainA}
                    </td>
                    <td className="px-3 py-4 font-semibold">
                      {conflict.trainB}
                    </td>
                    <td className="px-3 py-4">{conflict.section}</td>
                    <td className="px-3 py-4">
                      {formatTime(conflict.overlapStart)}–{formatTime(conflict.overlapEnd)}
                    </td>
                    <td className="px-3 py-4">
                      <span className="rounded-full border border-red-500/30 px-2.5 py-1 text-xs text-red-400">
                        CONFLICT
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="mt-6 rounded-lg border border-green-500/30 p-5">
            <div className="flex items-center gap-2 font-semibold text-green-400">
              <ShieldCheck size={18} />
              No overlapping movements found
            </div>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-border p-4">
        <p className="text-sm text-muted">
          <strong>How it works:</strong> The page compares train movements
          pairwise. A potential conflict is flagged when two movements belong
          to the same section and their time intervals overlap. This is a
          demonstration only, not a complete railway conflict-validation system.
        </p>
      </div>
    </div>
  )
}
