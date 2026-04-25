import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { getDependencies } from '../api/client'
import type { Dependency } from '../types'

function getCategoryColor(isInternal: boolean, fqdn: string): string {
  if (isInternal) return '#22c55e'
  const lower = fqdn.toLowerCase()
  if (
    lower.includes('salesforce') ||
    lower.includes('office365') ||
    lower.includes('github') ||
    lower.includes('slack') ||
    lower.includes('workday') ||
    lower.includes('okta') ||
    lower.includes('aws') ||
    lower.includes('azure')
  ) {
    return '#0066cc'
  }
  return '#3b82f6'
}

function ConfBar({ val }: { val: number }) {
  const pct = Math.round(val * 100)
  const color = val >= 0.7 ? '#22c55e' : val >= 0.4 ? '#f59e0b' : '#ef4444'
  return (
    <div className="flex items-center gap-2">
      <div className="w-20 bg-gray-200 rounded-full h-1.5 flex-shrink-0">
        <div
          className="h-1.5 rounded-full"
          style={{ width: `${pct}%`, background: color }}
        />
      </div>
      <span className="text-xs text-gray-500 w-7 text-right">{pct}%</span>
    </div>
  )
}

export default function DependencyExplorer() {
  const [items, setItems] = useState<Dependency[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [minConf, setMinConf] = useState(0)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    const params: Record<string, unknown> = { page, page_size: 50 }
    if (minConf > 0) params.min_confidence = minConf
    getDependencies(params)
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [page, minConf])

  const chartData = items.slice(0, 15).map((d) => ({
    fqdn: d.fqdn.length > 28 ? d.fqdn.slice(0, 28) + '…' : d.fqdn,
    queries: d.query_count,
    color: getCategoryColor(d.is_internal, d.fqdn),
  }))

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Dependency Explorer</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Client endpoints → FQDNs → Answer IPs. Color: green=internal, blue=SaaS/external.
      </p>

      {/* Filters */}
      <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6 flex flex-wrap items-center gap-6">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
            Min Confidence
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={minConf}
            onChange={(e) => {
              setMinConf(Number(e.target.value))
              setPage(1)
            }}
            className="w-32 accent-blue-600"
          />
          <span className="text-sm text-gray-600 w-8">{Math.round(minConf * 100)}%</span>
        </div>
        <div className="text-sm text-gray-500 ml-auto">
          {total.toLocaleString()} dependencies
        </div>
      </div>

      {/* Bar Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-1">
            Top FQDNs by Query Count
          </h2>
          <p className="text-xs text-gray-400 mb-4">
            First page of results, sorted by confidence
          </p>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={chartData} margin={{ left: 0, right: 8, bottom: 40 }}>
              <XAxis
                dataKey="fqdn"
                tick={{ fontSize: 10 }}
                interval={0}
                angle={-25}
                textAnchor="end"
                height={55}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="queries" name="Queries" radius={[3, 3, 0, 0]}>
                {chartData.map((entry, idx) => (
                  <Cell key={idx} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-5 mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm inline-block bg-green-500" />
              Internal
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm inline-block bg-blue-600" />
              SaaS / External
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm inline-block bg-orange-400" />
              Ambiguous
            </span>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Client IP</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">FQDN</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700 w-36">Confidence</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Queries</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Days</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Type</th>
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
                  No data. Generate demo data or upload DNS logs, then run analysis.
                </td>
              </tr>
            ) : (
              items.map((d) => (
                <tr key={d.id} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <button
                      className="font-mono text-sm hover:underline"
                      style={{ color: '#0066cc' }}
                      onClick={() => navigate(`/workloads/${d.client_ip}`)}
                    >
                      {d.client_ip}
                    </button>
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-700 max-w-xs truncate">
                    {d.fqdn}
                  </td>
                  <td className="px-4 py-3 w-36">
                    <ConfBar val={d.confidence_score} />
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">
                    {d.query_count.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-600">{d.days_observed}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`text-xs px-2 py-1 rounded-full font-medium ${
                        d.is_internal
                          ? 'bg-green-100 text-green-800'
                          : 'bg-blue-100 text-blue-800'
                      }`}
                    >
                      {d.is_internal ? 'Internal' : 'External'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {total > 50 && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 bg-gray-50">
            <span className="text-sm text-gray-500">
              Page {page} of {Math.ceil(total / 50)} ({total.toLocaleString()} total)
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
