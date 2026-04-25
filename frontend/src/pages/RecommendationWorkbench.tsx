import { Fragment, useState, useEffect } from 'react'
import { getRecommendations, updateRecommendation } from '../api/client'
import type { Recommendation } from '../types'
import { CheckCircle, XCircle, ChevronDown, ChevronRight } from 'lucide-react'

const TYPE_BADGE: Record<string, string> = {
  WORKLOAD_GROUP: 'bg-purple-100 text-purple-800',
  APP_DEPENDENCY: 'bg-blue-100 text-blue-800',
  IP_LIST: 'bg-teal-100 text-teal-800',
  SERVICE: 'bg-orange-100 text-orange-800',
}

const STATUS_BADGE: Record<string, string> = {
  PENDING: 'bg-yellow-100 text-yellow-800',
  APPROVED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  DRAFT_CREATED: 'bg-blue-100 text-blue-800',
}

function ConfBar({ val }: { val: number }) {
  const pct = Math.round(val * 100)
  const color = val >= 0.7 ? '#22c55e' : val >= 0.4 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-200 rounded-full h-1.5">
        <div
          className="h-1.5 rounded-full"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs text-gray-500 w-7 text-right">{pct}%</span>
    </div>
  )
}

export default function RecommendationWorkbench() {
  const [items, setItems] = useState<Recommendation[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [filterType, setFilterType] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [expanded, setExpanded] = useState<number | null>(null)
  const [refreshToken, setRefreshToken] = useState(0)

  useEffect(() => {
    setLoading(true)
    const params: Record<string, unknown> = { page, page_size: 50 }
    if (filterType) params.type = filterType
    if (filterStatus) params.status = filterStatus
    getRecommendations(params)
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [page, filterType, filterStatus, refreshToken])

  const handleAction = (id: number, status: 'APPROVED' | 'REJECTED') => {
    updateRecommendation(id, { status })
      .then(() => setRefreshToken((t) => t + 1))
      .catch(console.error)
  }

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Recommendation Workbench</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Review and approve Illumio policy object recommendations generated from DNS behavior.
      </p>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-wrap items-center gap-4">
        <select
          value={filterType}
          onChange={(e) => {
            setFilterType(e.target.value)
            setPage(1)
          }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
        >
          <option value="">All Types</option>
          {['WORKLOAD_GROUP', 'APP_DEPENDENCY', 'IP_LIST', 'SERVICE'].map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => {
            setFilterStatus(e.target.value)
            setPage(1)
          }}
          className="border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-700 bg-white"
        >
          <option value="">All Statuses</option>
          {['PENDING', 'APPROVED', 'REJECTED', 'DRAFT_CREATED'].map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
        <span className="text-sm text-gray-500 ml-auto">
          {total.toLocaleString()} recommendations
        </span>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="w-8 px-3 py-3" />
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Name</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700 w-36">Confidence</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Status</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="text-center py-10 text-gray-400">
                  Loading…
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="text-center py-10 text-gray-400">
                  No recommendations. Run analysis from the Overview page first.
                </td>
              </tr>
            ) : (
              items.map((rec) => (
                <Fragment key={rec.id}>
                  <tr className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="px-3 py-3">
                      <button
                        onClick={() => setExpanded(expanded === rec.id ? null : rec.id)}
                        className="text-gray-400 hover:text-gray-600"
                      >
                        {expanded === rec.id ? (
                          <ChevronDown size={14} />
                        ) : (
                          <ChevronRight size={14} />
                        )}
                      </button>
                    </td>
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
                    <td className="px-4 py-3 w-36">
                      <ConfBar val={rec.confidence} />
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`text-xs px-2 py-1 rounded-full font-medium ${
                          STATUS_BADGE[rec.status] ?? 'bg-gray-100 text-gray-700'
                        }`}
                      >
                        {rec.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      {rec.status === 'PENDING' && (
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
                      )}
                    </td>
                  </tr>
                  {expanded === rec.id && (
                    <tr className="bg-blue-50 border-b border-blue-100">
                      <td colSpan={6} className="px-8 py-4">
                        <div className="text-sm font-semibold text-gray-700 mb-2">Evidence</div>
                        {rec.evidence.human_readable_reason != null && (
                          <p className="text-sm text-gray-600 mb-3 leading-relaxed">
                            {String(rec.evidence.human_readable_reason)}
                          </p>
                        )}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs text-gray-600">
                          {rec.evidence.client_count != null && (
                            <div>
                              <span className="font-semibold text-gray-700">Clients: </span>
                              {String(rec.evidence.client_count)}
                            </div>
                          )}
                          {rec.evidence.query_count != null && (
                            <div>
                              <span className="font-semibold text-gray-700">Queries: </span>
                              {Number(rec.evidence.query_count).toLocaleString()}
                            </div>
                          )}
                          {rec.evidence.days_observed != null && (
                            <div>
                              <span className="font-semibold text-gray-700">Days: </span>
                              {String(rec.evidence.days_observed)}
                            </div>
                          )}
                          {rec.evidence.confidence_score != null && (
                            <div>
                              <span className="font-semibold text-gray-700">Score: </span>
                              {(Number(rec.evidence.confidence_score) * 100).toFixed(1)}%
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              ))
            )}
          </tbody>
        </table>

        {total > 50 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <span className="text-sm text-gray-500">
              Page {page} of {Math.ceil(total / 50)}
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
                disabled={page >= Math.ceil(total / 50)}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 text-sm border rounded-lg disabled:opacity-40 hover:bg-gray-100"
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
