import { useState } from 'react'
import { Activity, RotateCcw, TrendingUp } from 'lucide-react'

const baseWindows = [
  { id: 'W-01', section: 'Tirupati-S1', start: '09:10', end: '10:10', conflicts: 2, delay: 18 },
  { id: 'W-02', section: 'Tirupati-S1', start: '09:45', end: '10:15', conflicts: 0, delay: 5 },
  { id: 'W-03', section: 'Tirupati-S1', start: '10:15', end: '10:45', conflicts: 0, delay: 8 },
  { id: 'W-04', section: 'Tirupati-S2', start: '10:00', end: '10:30', conflicts: 1, delay: 12 },
]

export default function WhatIfPage() {
  const [extraDelay, setExtraDelay] = useState(0)
  const [affectedSection, setAffectedSection] = useState('Tirupati-S1')
  const [showResults, setShowResults] = useState(false)

  const windows = baseWindows
    .map((window) => {
      const addedDelay =
        window.section === affectedSection ? extraDelay : 0

      const estimatedDelay = window.delay + addedDelay
      const score = Math.max(
        0,
        100 - window.conflicts * 30 - estimatedDelay * 2,
      )

      return {
        ...window,
        estimatedDelay,
        score,
      }
    })
    .sort((a, b) => b.score - a.score)

  function resetSimulation() {
    setExtraDelay(0)
    setAffectedSection('Tirupati-S1')
    setShowResults(false)
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Scenario Analysis
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          What-if Simulation
        </h1>

        <p className="mt-2 text-sm text-muted">
          Change a hypothetical train delay and see how the sample window
          ranking responds.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          SIMULATED DATA · NOT A LIVE PREDICTION
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Extra Delay</p>
          <p className="mt-2 text-3xl font-bold">{extraDelay} min</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Affected Section</p>
          <p className="mt-2 text-xl font-bold">{affectedSection}</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Top Candidate</p>
          <p className="mt-2 text-3xl font-bold text-lime-400">
            {windows[0].id}
          </p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="mb-5 flex items-center gap-2">
          <Activity size={20} />
          <h2 className="text-lg font-bold">Configure Scenario</h2>
        </div>

        <div className="space-y-6">
          <div>
            <label htmlFor="affectedSection" className="mb-2 block text-sm font-medium">
              Section affected by the delay
            </label>

            <select
              id="affectedSection"
              value={affectedSection}
              onChange={(event) => {
                setAffectedSection(event.target.value)
                setShowResults(false)
              }}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm sm:max-w-md"
            >
              <option value="Tirupati-S1">Tirupati-S1</option>
              <option value="Tirupati-S2">Tirupati-S2</option>
            </select>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between gap-3">
              <label htmlFor="extraDelay" className="text-sm font-medium">
                Add hypothetical delay
              </label>
              <span className="text-sm font-bold">{extraDelay} minutes</span>
            </div>

            <input
              id="extraDelay"
              type="range"
              min="0"
              max="60"
              step="5"
              value={extraDelay}
              onChange={(event) => {
                setExtraDelay(Number(event.target.value))
                setShowResults(false)
              }}
              className="w-full accent-lime-500"
            />

            <div className="mt-1 flex justify-between text-xs text-muted">
              <span>0 min</span>
              <span>30 min</span>
              <span>60 min</span>
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => setShowResults(true)}
              className="inline-flex items-center gap-2 rounded-lg bg-lime-500 px-5 py-3 text-sm font-semibold text-black hover:bg-lime-400"
            >
              <TrendingUp size={16} />
              Run Simulation
            </button>

            <button
              type="button"
              onClick={resetSimulation}
              className="inline-flex items-center gap-2 rounded-lg border border-border px-5 py-3 text-sm font-semibold hover:bg-white/5"
            >
              <RotateCcw size={16} />
              Reset
            </button>
          </div>
        </div>
      </div>

      {showResults && (
        <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
          <h2 className="text-lg font-bold">Simulation Results</h2>

          <p className="mt-2 text-sm text-muted">
            Windows in {affectedSection} have been assigned the extra
            hypothetical delay. Other sections remain unchanged.
          </p>

          <div className="mt-5 overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted">
                  <th className="px-3 py-3">Rank</th>
                  <th className="px-3 py-3">Window</th>
                  <th className="px-3 py-3">Section</th>
                  <th className="px-3 py-3">Conflicts</th>
                  <th className="px-3 py-3">Estimated Delay</th>
                  <th className="px-3 py-3">Demo Score</th>
                </tr>
              </thead>

              <tbody>
                {windows.map((window, index) => (
                  <tr key={window.id} className="border-b border-border">
                    <td className="px-3 py-4">{index + 1}</td>
                    <td className="px-3 py-4 font-semibold">{window.id}</td>
                    <td className="px-3 py-4">{window.section}</td>
                    <td className="px-3 py-4">{window.conflicts}</td>
                    <td className="px-3 py-4">{window.estimatedDelay} min</td>
                    <td className="px-3 py-4 font-semibold">
                      {window.score}/100
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="mt-4 text-xs text-muted">
            This scenario uses a simple illustrative scoring formula. It does
            not modify real schedules or produce an official railway decision.
          </p>
        </div>
      )}
    </div>
  )
}