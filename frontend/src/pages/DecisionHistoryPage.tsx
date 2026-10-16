
import { useEffect, useState } from 'react'
import { RefreshCw, History } from 'lucide-react'
import {
  getMaintenanceRequests,
  type SavedMaintenanceRequest,
} from '../services/api'

export default function DecisionHistoryPage() {
  const [requests, setRequests] = useState<SavedMaintenanceRequest[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadHistory() {
    setLoading(true)
    setError('')

    try {
      const result = await getMaintenanceRequests()
      setRequests(result.requests)
    } catch {
      setError('Unable to load history. Check whether the backend is running.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadHistory()
  }, [])

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Records
        </p>

        <h1 className="mt-2 font-display text-2xl font-bold">
          Decision History
        </h1>

        <p className="mt-2 text-sm text-muted">
          Review maintenance requests saved in the project database.
        </p>

        <p className="mt-3 inline-flex rounded-full border border-amber-500/30 px-3 py-1 text-xs text-amber-400">
          REQUEST HISTORY · NOT OFFICIAL RAILWAY DECISIONS
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Saved Requests</p>
          <p className="mt-2 text-3xl font-bold">{requests.length}</p>
        </div>

        <div className="rounded-xl border border-border bg-panel p-5">
          <p className="text-sm text-muted">Record Source</p>
          <p className="mt-2 text-xl font-bold">Backend Database</p>
        </div>
      </div>

      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <History size={20} />
            <h2 className="text-lg font-bold">Maintenance Request Records</h2>
          </div>

          <button
            type="button"
            onClick={() => void loadHistory()}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-4 py-2 text-sm font-semibold hover:bg-white/5 disabled:opacity-50"
          >
            <RefreshCw size={15} />
            Refresh
          </button>
        </div>

        {loading ? (
          <p className="py-8 text-center text-sm text-muted">
            Loading saved records...
          </p>
        ) : error ? (
          <p className="py-8 text-center text-sm text-red-400">{error}</p>
        ) : requests.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted">
            No saved requests yet. Submit a request first.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[850px] text-left text-sm">
              <thead>
                <tr className="border-b border-border text-muted">
                  <th className="px-3 py-3">Request ID</th>
                  <th className="px-3 py-3">Section</th>
                  <th className="px-3 py-3">Maintenance</th>
                  <th className="px-3 py-3">Duration</th>
                  <th className="px-3 py-3">Priority</th>
                  <th className="px-3 py-3">Description</th>
                  <th className="px-3 py-3">Created At</th>
                </tr>
              </thead>

              <tbody>
                {requests.map((request) => (
                  <tr
                    key={request.request_id}
                    className="border-b border-border"
                  >
                    <td className="px-3 py-4 font-semibold">
                      {request.request_id}
                    </td>
                    <td className="px-3 py-4">{request.track_section}</td>
                    <td className="px-3 py-4">{request.maintenance_type}</td>
                    <td className="px-3 py-4">
                      {request.duration_hours} hr
                    </td>
                    <td className="px-3 py-4">{request.priority}</td>
                    <td className="px-3 py-4">{request.description || '-'}</td>
                    <td className="px-3 py-4">
                      {new Date(request.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mt-4 text-xs text-muted">
          This page displays saved maintenance requests. Recommendation
          outcomes will appear here only after the optimization backend
          provides them.
        </p>
      </div>
    </div>
  )
}
