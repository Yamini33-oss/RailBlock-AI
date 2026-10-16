import { useState } from 'react'
import { BarChart3, Trophy, RefreshCw } from 'lucide-react'

const candidates = [
  {
    id: 'W-01',
    start: '09:10',
    end: '10:10',
    section: 'Tirupati-S1',
    conflicts: 2,
    delay: 18,
  },
  {
    id: 'W-02',
    start: '09:45',
    end: '10:15',
    section: 'Tirupati-S1',
    conflicts: 0,
    delay: 5,
  },
  {
    id: 'W-03',
    start: '10:15',
    end: '10:45',
    section: 'Tirupati-S1',
    conflicts: 0,
    delay: 8,
  },
  {
    id: 'W-04',
    start: '10:00',
    end: '10:30',
    section: 'Tirupati-S2',
    conflicts: 1,
    delay: 12,
  },
]

export default function WindowComparisonPage() {
  const [sortBy, setSortBy] = useState('score')
  const [checked, setChecked] = useState(false)

  const rankedCandidates = [...candidates]
    .map((candidate) => ({
      ...candidate,
      score: Math.max(
        0,
        100 - candidate.conflicts * 30 - candidate.delay * 2,
      ),
    }))
    .sort((a, b) =>
      sortBy === 'delay'
        ? a.delay - b.delay
        : sortBy === 'conflicts'
          ? a.conflicts - b.conflicts
          : b.score - a.score,
    )

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Optimization
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          Window Comparison
        </h1>

        <p className="mt-2 text-sm text-muted">
          Compare candidate maintenance windows using illustrative conflict
          counts and estimated delay values.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          DEMO DATA · NOT AN OPTIMIZER OUTPUT
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Candidate Windows</p>
          <p className="mt-2 text-3xl font-bold">{candidates.length}</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Zero-Conflict Candidates</p>
          <p className="mt-2 text-3xl font-bold text-green-400">
            {candidates.filter((item) => item.conflicts === 0).length}
          </p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Lowest Sample Delay</p>
          <p className="mt-2 text-3xl font-bold">
            {Math.min(...candidates.map((item) => item.delay))} min
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <BarChart3 size={20} />
            <h2 className="text-lg font-bold">Candidate Ranking</h2>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <label htmlFor="sortBy" className="text-sm text-muted">
              Rank by
            </label>

            <select
              id="sortBy"
              value={sortBy}
              onChange={(event) => {
                setSortBy(event.target.value)
                setChecked(false)
              }}
              className="rounded-lg border border-border bg-transparent px-3 py-2 text-sm"
            >
              <option value="score">Demo score</option>
              <option value="conflicts">Fewest conflicts</option>
              <option value="delay">Lowest delay</option>
            </select>

            <button
              type="button"
              onClick={() => setChecked(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-lime-500 px-4 py-2.5 text-sm font-semibold text-black hover:bg-lime-400"
            >
              <RefreshCw size={16} />
              Compare
            </button>
          </div>
        </div>

        {checked && (
          <p className="mt-4 text-sm text-green-400">
            Candidate windows sorted by{' '}
            {sortBy === 'score'
              ? 'demo score'
              : sortBy === 'delay'
                ? 'estimated delay'
                : 'conflict count'}.
          </p>
        )}

        <div className="mt-5 overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-muted">
                <th className="px-3 py-3">Rank</th>
                <th className="px-3 py-3">Window</th>
                <th className="px-3 py-3">Section</th>
                <th className="px-3 py-3">Time</th>
                <th className="px-3 py-3">Conflicts</th>
                <th className="px-3 py-3">Delay</th>
                <th className="px-3 py-3">Demo Score</th>
              </tr>
            </thead>

            <tbody>
              {rankedCandidates.map((item, index) => (
                <tr key={item.id} className="border-b border-border">
                  <td className="px-3 py-4 font-semibold">
                    {index === 0 ? (
                      <span className="inline-flex items-center gap-1 text-lime-400">
                        <Trophy size={15} />
                        1
                      </span>
                    ) : (
                      index + 1
                    )}
                  </td>
                  <td className="px-3 py-4 font-semibold">{item.id}</td>
                  <td className="px-3 py-4">{item.section}</td>
                  <td className="px-3 py-4">
                    {item.start}–{item.end}
                  </td>
                  <td
                    className={`px-3 py-4 ${
                      item.conflicts > 0 ? 'text-red-400' : 'text-green-400'
                    }`}
                  >
                    {item.conflicts}
                  </td>
                  <td className="px-3 py-4">{item.delay} min</td>
                  <td className="px-3 py-4 font-semibold">{item.score}/100</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="mt-4 text-xs text-muted">
          The score is a simple illustrative formula, not a trained ML
          prediction or a real railway maintenance recommendation.
        </p>
      </div>
    </div>
  )
}