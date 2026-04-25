import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  CartesianGrid,
} from 'recharts'
import { getWorkloads, getWorkloadDetail } from '../api/client'
import type { ClientProfile, WorkloadDetailResponse } from '../types'
import { ArrowLeft } from 'lucide-react'

const RCODE_COLORS = ['#22c55e', '#ef4444', '#f59e0b', '#0066cc', '#6b7280', '#a855f7']

function Spinner() {
  return (
    <div className="flex justify-center items-center py-16">
      <div
        className="animate-spin h-10 w-10 rounded-full border-b-2"
        style={{ borderColor: '#0066cc' }}
      />
    </div>
  )
}

// ─── Workloads list ───────────────────────────────────────────────────────────

function WorkloadsList() {
  const [items, setItems] = useState<ClientProfile[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    getWorkloads({ page, page_size: 50 })
      .then((r) => {
        setItems(r.data.items)
        setTotal(r.data.total)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [page])

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Workloads</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Click an endpoint to explore its DNS behavior, RCODE distribution, and timeline.
      </p>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Client IP</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Hostname</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Subnet</th>
              <th className="text-left px-4 py-3 font-semibold text-gray-700">Business Unit</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">Queries</th>
              <th className="text-right px-4 py-3 font-semibold text-gray-700">FQDNs</th>
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
                  No workloads. Run analysis from the Overview page first.
                </td>
              </tr>
            ) : (
              items.map((w) => (
                <tr
                  key={w.client_ip}
                  className="border-b border-gray-100 hover:bg-gray-50 cursor-pointer"
                  onClick={() => navigate(`/workloads/${w.client_ip}`)}
                >
                  <td className="px-4 py-3 font-mono text-sm" style={{ color: '#0066cc' }}>
                    {w.client_ip}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">{w.hostname ?? '—'}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">
                    {w.subnet ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-gray-600 text-xs">
                    {w.business_unit ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">
                    {w.total_queries.toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-700">{w.unique_fqdns}</td>
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

// ─── Workload detail ──────────────────────────────────────────────────────────

function WorkloadDetailView({ ip }: { ip: string }) {
  const [data, setData] = useState<WorkloadDetailResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    setLoading(true)
    getWorkloadDetail(ip)
      .then((r) => {
        setData(r.data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [ip])

  if (loading) return <Spinner />

  if (!data?.profile) {
    return (
      <div className="p-8">
        <button
          onClick={() => navigate('/workloads')}
          className="flex items-center gap-2 text-sm mb-6 hover:underline"
          style={{ color: '#0066cc' }}
        >
          <ArrowLeft size={16} /> Back to Workloads
        </button>
        <p className="text-gray-500">
          Workload not found. Run analysis from the Overview page first.
        </p>
      </div>
    )
  }

  const { profile, dependencies, rcode_distribution, timeline } = data

  const fqdnChartData = dependencies.slice(0, 10).map((d) => ({
    fqdn: d.fqdn.length > 24 ? d.fqdn.slice(0, 24) + '…' : d.fqdn,
    queries: d.query_count,
  }))

  const rcodeData = Object.entries(rcode_distribution).map(([name, value]) => ({
    name,
    value,
  }))

  return (
    <div className="p-8 max-w-6xl">
      <button
        onClick={() => navigate('/workloads')}
        className="flex items-center gap-2 text-sm mb-6 hover:underline"
        style={{ color: '#0066cc' }}
      >
        <ArrowLeft size={16} /> Back to Workloads
      </button>

      {/* Header card */}
      <div className="bg-white rounded-xl border border-gray-200 p-6 mb-6">
        <h1 className="text-2xl font-bold text-gray-900 font-mono mb-4">{profile.client_ip}</h1>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Subnet</div>
            <div className="font-mono">{profile.subnet ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Business Unit</div>
            <div>{profile.business_unit ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Owner</div>
            <div>{profile.owner ?? '—'}</div>
          </div>
          <div>
            <div className="text-xs text-gray-500 mb-0.5">Site</div>
            <div>{profile.site ?? '—'}</div>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-5 pt-5 border-t border-gray-100">
          <div>
            <div className="text-2xl font-bold text-gray-900">
              {profile.total_queries.toLocaleString()}
            </div>
            <div className="text-xs text-gray-500">Total Queries</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{profile.unique_fqdns}</div>
            <div className="text-xs text-gray-500">Unique FQDNs</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-gray-900">{dependencies.length}</div>
            <div className="text-xs text-gray-500">Dependencies</div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {fqdnChartData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">
              Top FQDNs by Query Count
            </h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart
                data={fqdnChartData}
                layout="vertical"
                margin={{ left: 10, right: 20 }}
              >
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="fqdn"
                  width={130}
                  tick={{ fontSize: 10 }}
                />
                <Tooltip />
                <Bar dataKey="queries" name="Queries" fill="#0066cc" radius={[0, 3, 3, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {rcodeData.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-semibold text-gray-700 mb-4">RCODE Distribution</h2>
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={rcodeData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={80}
                  label={({ name, percent }) =>
                    `${name} ${Math.round((percent ?? 0) * 100)}%`
                  }
                >
                  {rcodeData.map((_, idx) => (
                    <Cell
                      key={idx}
                      fill={RCODE_COLORS[idx % RCODE_COLORS.length]}
                    />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Timeline */}
      {timeline.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-700 mb-4">Query Timeline</h2>
          <ResponsiveContainer width="100%" height={140}>
            <LineChart data={timeline}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10 }}
                interval={Math.max(0, Math.floor(timeline.length / 12) - 1)}
              />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip />
              <Line
                type="monotone"
                dataKey="count"
                name="Queries"
                stroke="#0066cc"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// ─── Router ───────────────────────────────────────────────────────────────────

export default function WorkloadDetail() {
  const { ip } = useParams<{ ip?: string }>()
  if (!ip) return <WorkloadsList />
  return <WorkloadDetailView ip={ip} />
}
