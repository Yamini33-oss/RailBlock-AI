import { useEffect, useState, type FormEvent } from 'react'
import { Send, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react'
import {
  submitMaintenanceRequest,
  getMaintenanceRequests,
  type SavedMaintenanceRequest,
} from '../services/api'

export default function MaintenanceRequestPage() {
  const [trackSection, setTrackSection] = useState('')
  const [maintenanceType, setMaintenanceType] = useState('Track Inspection')
  const [duration, setDuration] = useState('2')
  const [priority, setPriority] = useState('High')
  const [description, setDescription] = useState('')

  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState(false)

  const [requests, setRequests] = useState<SavedMaintenanceRequest[]>([])
  const [loadingRequests, setLoadingRequests] = useState(true)
  const [requestsError, setRequestsError] = useState('')

  // Load saved requests from the backend
  async function loadRequests() {
    setLoadingRequests(true)
    setRequestsError('')

    try {
      const result = await getMaintenanceRequests()
      setRequests(result.requests)
    } catch {
      setRequestsError('Could not load saved requests. Check the backend connection.')
    } finally {
      setLoadingRequests(false)
    }
  }

  useEffect(() => {
    void loadRequests()
  }, [])

  // Submit a new maintenance request
  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setMessage('')
    setError(false)

    try {
      const result = await submitMaintenanceRequest({
        request_id: `MR-${Date.now()}`,
        track_section: trackSection.trim(),
        maintenance_type: maintenanceType,
        duration_hours: Number(duration),
        priority,
        description: description.trim(),
      })

      setMessage(result.message || 'Request submitted successfully.')
      setTrackSection('')
      setDescription('')

      // Refresh the table after saving
      await loadRequests()
    } catch {
      setError(true)
      setMessage(
        'Could not submit the request. Check whether the backend is running.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-[1280px] space-y-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-muted">
          Operations / Maintenance
        </p>
        <h1 className="mt-2 font-display text-2xl font-bold">
          Maintenance Request
        </h1>
        <p className="mt-2 text-sm text-muted">
          Submit a track maintenance request for window planning.
        </p>
      </div>

      {/* Maintenance request form */}
      <div className="max-w-3xl rounded-xl border border-border bg-panel p-5 sm:p-7">
        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label htmlFor="trackSection" className="mb-2 block text-sm font-medium">
              Track Section
            </label>
            <input
              id="trackSection"
              value={trackSection}
              onChange={(e) => setTrackSection(e.target.value)}
              placeholder="e.g. Tirupati-S1"
              required
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm outline-none focus:border-lime-500"
            />
          </div>

          <div className="grid gap-5 sm:grid-cols-2">
            <div>
              <label htmlFor="maintenanceType" className="mb-2 block text-sm font-medium">
                Maintenance Type
              </label>
              <select
                id="maintenanceType"
                value={maintenanceType}
                onChange={(e) => setMaintenanceType(e.target.value)}
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm outline-none"
              >
                <option value="Track Inspection">Track Inspection</option>
                <option value="Track Repair">Track Repair</option>
                <option value="Signal Maintenance">Signal Maintenance</option>
                <option value="Electrical Maintenance">Electrical Maintenance</option>
                <option value="Equipment Maintenance">Equipment Maintenance</option>
              </select>
            </div>

            <div>
              <label htmlFor="duration" className="mb-2 block text-sm font-medium">
                Duration (hours)
              </label>
              <input
                id="duration"
                type="number"
                min="0.25"
                max="24"
                step="0.25"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                required
                className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm outline-none"
              />
            </div>
          </div>

          <div>
            <label htmlFor="priority" className="mb-2 block text-sm font-medium">
              Priority
            </label>
            <select
              id="priority"
              value={priority}
              onChange={(e) => setPriority(e.target.value)}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm outline-none"
            >
              <option value="Low">Low</option>
              <option value="Medium">Medium</option>
              <option value="High">High</option>
              <option value="Critical">Critical</option>
            </select>
          </div>

          <div>
            <label htmlFor="description" className="mb-2 block text-sm font-medium">
              Description
            </label>
            <textarea
              id="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Describe the maintenance work required..."
              rows={4}
              className="w-full rounded-lg border border-border bg-transparent px-3 py-2.5 text-sm outline-none focus:border-lime-500"
            />
          </div>

          {message && (
            <div
              role="status"
              className={`flex items-start gap-2 rounded-lg border p-3 text-sm ${
                error
                  ? 'border-red-500/30 text-red-400'
                  : 'border-green-500/30 text-green-400'
              }`}
            >
              {error ? (
                <AlertCircle size={18} className="mt-0.5 shrink-0" />
              ) : (
                <CheckCircle size={18} className="mt-0.5 shrink-0" />
              )}
              <span>{message}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-lime-500 px-5 py-3 text-sm font-semibold text-black transition hover:bg-lime-400 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Send size={16} />
            {loading ? 'Submitting...' : 'Submit Request'}
          </button>
        </form>
      </div>

      {/* Saved maintenance requests */}
      <div className="rounded-xl border border-border bg-panel p-5 sm:p-7">
        <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold">Saved Maintenance Requests</h2>
            <p className="mt-1 text-sm text-muted">
              Requests retrieved from the backend database
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadRequests()}
            disabled={loadingRequests}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-sm transition hover:bg-black/5 disabled:opacity-60"
          >
            <RefreshCw size={15} />
            {loadingRequests ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {loadingRequests ? (
          <p className="py-6 text-sm text-muted">Loading saved requests...</p>
        ) : requestsError ? (
          <div className="flex items-center gap-2 py-4 text-sm text-red-400">
            <AlertCircle size={18} />
            {requestsError}
          </div>
        ) : requests.length === 0 ? (
          <p className="py-6 text-sm text-muted">
            No maintenance requests found. Submit your first request above.
          </p>
        ) : (
          <>
            <p className="mb-4 text-sm text-muted">
              Total saved requests: {requests.length}
            </p>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[850px] text-left text-sm">
                <thead>
                  <tr className="border-b border-border text-muted">
                    <th className="px-3 py-3 font-medium">Request ID</th>
                    <th className="px-3 py-3 font-medium">Track Section</th>
                    <th className="px-3 py-3 font-medium">Maintenance Type</th>
                    <th className="px-3 py-3 font-medium">Duration</th>
                    <th className="px-3 py-3 font-medium">Priority</th>
                    <th className="px-3 py-3 font-medium">Submitted At</th>
                  </tr>
                </thead>

                <tbody>
                  {requests.map((request) => (
                    <tr
                      key={request.request_id}
                      className="border-b border-border last:border-0"
                    >
                      <td className="px-3 py-4 font-medium">
                        {request.request_id}
                      </td>
                      <td className="px-3 py-4">{request.track_section}</td>
                      <td className="px-3 py-4">{request.maintenance_type}</td>
                      <td className="px-3 py-4">
                        {request.duration_hours} hours
                      </td>
                      <td className="px-3 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            request.priority === 'Critical'
                              ? 'bg-red-500/10 text-red-400'
                              : request.priority === 'High'
                                ? 'bg-orange-500/10 text-orange-400'
                                : request.priority === 'Medium'
                                  ? 'bg-yellow-500/10 text-yellow-400'
                                  : 'bg-green-500/10 text-green-400'
                          }`}
                        >
                          {request.priority}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-muted">
                        {new Date(
                          `${request.created_at.replace(' ', 'T')}Z`,
                        ).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </div>
  )
}