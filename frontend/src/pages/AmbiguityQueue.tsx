import { useState, useEffect } from 'react'
import { getRecommendations, updateRecommendation } from '../api/client'
import type { Recommendation } from '../types'
import { CheckCircle, XCircle } from 'lucide-react'

const TYPE_BADGE: Record<string, string> = {
  WORKLOAD_GROUP: 'bg-purple-100 text-purple-800',
  APP_DEPENDENCY: 'bg-blue-100 text-blue-800',
  IP_LIST: 'bg-teal-100 text-teal-800',
  SERVICE: 'bg-orange-100 text-orange-800',
}

export default function AmbiguityQueue() {
  const [items, setItems] = useState<Recommendation[]>([])
  const [totalPending, setTotalPending] = useState(0)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    setLoading(true)
    getRecommendations({ status: 'PENDING', page, page_size: 100 })
      .then((r) => {
        // Filter low-confidence items client-side
        const lowConf = r.data.items.filter((rec) => rec.confidence < 0.6)
        setItems(lowConf)
        setTotalPending(r.data.total)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [page, refreshToken])

  const handleAction = (id: number, status: 'APPROVED' | 'REJECTED') => {
    updateRecommendation(id, { status })
      .then(() => setRefreshToken((t) => t + 1))
      .catch(console.error)
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Ambiguity Queue</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Low-confidence recommendations (&lt;60%) that require human judgment before approval.
      </p>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        {/* Banner */}
        <div className="px-4 py-3 border-b border-amber-200 bg-amber-50">
          <p className="text-sm text-amber-800">
            These items have insufficient DNS evidence for automatic approval — too few days
            observed, low query volume, or unstable answer IPs. Review the reason and decide.
          </p>
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Name</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700 w-32">Confidence</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Reason</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="text-center py-10 text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={5} className="text-center py-10 text-gray-400">
                  {totalPending > 0
                    ? 'All pending items have sufficient confidence — no ambiguous items.'
                    : 'No pending items. Run analysis from the Overview page first.'}
                </td>
              </tr>
            ) : (
              items.map((rec) => (
                <tr key={rec.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium ${
                        TYPE_BADGE[rec.type] ?? 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {rec.type}
                    </span>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700 max-w-xs truncate">
                    {rec.name}
                  </td>
                  <td className="px-4 py-3 w-32">
                    <div className="flex items-center gap-2">
                      <div className="w-14 bg-gray-200 rounded-full h-1.5">
                        <div
                          className="h-1.5 rounded-full bg-amber-400"
                          style={{ width: `${Math.round(rec.confidence * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">
                        {Math.round(rec.confidence * 100)}%
                      </span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600 max-w-sm">
                    {rec.evidence.human_readable_reason != null
                      ? String(rec.evidence.human_readable_reason).slice(0, 130) + '…'
                      : '—'}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => handleAction(rec.id, 'APPROVED')}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 rounded-lg border border-green-200 transition-colors"
                      >
                        <CheckCircle size={12} /> Approve
                      </button>
                      <button
                        onClick={() => handleAction(rec.id, 'REJECTED')}
                        className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 rounded-lg border border-red-200 transition-colors"
                      >
                        <XCircle size={12} /> Reject
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {totalPending > 100 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <span className="text-sm text-gray-500">
              Page {page} (showing low-confidence items)
            </span>
            <div className="flex gap-2">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-100"
              >
                Prev
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-100"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
