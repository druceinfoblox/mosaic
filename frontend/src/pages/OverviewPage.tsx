import { useState, useEffect } from 'react'
import { getOverview, generateDemo, runAnalysis } from '../api/client'
import type { Overview } from '../types'
import {
  Database,
  Users,
  Globe,
  Zap,
  Layers,
  Shield,
  CheckCircle,
  Clock,
  RefreshCw,
  Play,
} from 'lucide-react'

interface KPITileProps {
  icon: React.ElementType
  label: string
  value: number | string
  colorClass: string
  sub?: string
}

function KPITile({ icon: Icon, label, value, colorClass, sub }: KPITileProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow">
      <div className={`inline-flex p-3 rounded-lg mb-4 ${colorClass}`}>
        <Icon size={20} className="text-white" />
      </div>
      <div className="text-3xl font-bold text-gray-900">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div className="text-sm font-medium text-gray-700 mt-1">{label}</div>
      {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
    </div>
  )
}

function Spinner() {
  return (
    <div
      className="animate-spin h-10 w-10 rounded-full border-b-2"
      style={{ borderColor: '#0066cc' }}
    />
  )
}

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const load = () => {
    setLoading(true)
    setError(null)
    getOverview()
      .then((r) => {
        setData(r.data)
        setLoading(false)
      })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Failed to load overview')
        setLoading(false)
      })
  }

  useEffect(() => {
    load()
  }, [])

  const handleGenerateDemo = async () => {
    setRunning(true)
    setMsg(null)
    try {
      await generateDemo()
      await runAnalysis()
      setMsg('Demo data generated and analyzed successfully!')
      load()
    } catch (e: unknown) {
      setMsg('Error: ' + (e instanceof Error ? e.message : 'unknown error'))
    } finally {
      setRunning(false)
    }
  }

  const handleAnalyze = async () => {
    setRunning(true)
    setMsg(null)
    try {
      await runAnalysis()
      setMsg('Analysis complete!')
      load()
    } catch (e: unknown) {
      setMsg('Error: ' + (e instanceof Error ? e.message : 'unknown error'))
    } finally {
      setRunning(false)
    }
  }

  return (
    <div className="p-8 max-w-7xl">
      {/* Hero Banner */}
      <div
        className="rounded-xl p-7 mb-8 text-white"
        style={{ background: 'linear-gradient(135deg, #0066cc 0%, #004c99 100%)' }}
      >
        <div className="flex items-center gap-3 mb-2">
          <Shield size={28} />
          <h1 className="text-2xl font-bold">Project Mosaic</h1>
        </div>
        <p className="text-blue-100 text-lg mt-1">
          DNS history → microsegmentation policy in{' '}
          <strong className="text-white">minutes, not months</strong>
        </p>
        <p className="text-blue-200 text-sm mt-2">
          Automatically discover application dependencies from Infoblox DNS logs and generate
          Illumio PCE policy objects with full audit evidence.
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <Spinner />
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-xl p-4 mb-6">
          <strong>Error:</strong> {error}
        </div>
      )}

      {msg && (
        <div className="bg-green-50 border border-green-200 text-green-700 rounded-xl p-4 mb-6">
          {msg}
        </div>
      )}

      {data && !loading && (
        <>
          {!data.analyzed && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-8 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <div>
                <p className="text-blue-800 font-semibold">No data yet</p>
                <p className="text-blue-600 text-sm mt-0.5">
                  Generate demo data to explore Mosaic, or upload your own DNS logs via the API.
                </p>
              </div>
              <button
                onClick={handleGenerateDemo}
                disabled={running}
                className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-medium text-white whitespace-nowrap disabled:opacity-50 transition-opacity"
                style={{ background: '#0066cc' }}
              >
                {running ? <RefreshCw size={14} className="animate-spin" /> : <Play size={14} />}
                Generate Demo Data
              </button>
            </div>
          )}

          {/* KPI Grid Row 1 */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-5">
            <KPITile
              icon={Database}
              label="DNS Events"
              value={data.total_events}
              colorClass="bg-blue-600"
              sub={`${data.days_history} day history`}
            />
            <KPITile
              icon={Users}
              label="Unique Endpoints"
              value={data.unique_endpoints}
              colorClass="bg-indigo-600"
            />
            <KPITile
              icon={Globe}
              label="Unique FQDNs"
              value={data.unique_fqdns}
              colorClass="bg-teal-600"
            />
            <KPITile
              icon={Layers}
              label="App Dependencies"
              value={data.candidate_applications}
              colorClass="bg-purple-600"
            />
          </div>

          {/* KPI Grid Row 2 */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-8">
            <KPITile
              icon={Shield}
              label="Network Segments"
              value={data.candidate_segments}
              colorClass="bg-orange-600"
            />
            <KPITile
              icon={Zap}
              label="Draft Illumio Objects"
              value={data.draft_illumio_objects}
              colorClass="bg-pink-600"
            />
            <KPITile
              icon={CheckCircle}
              label="High-Confidence Recs"
              value={data.high_confidence_recs}
              colorClass="bg-green-600"
              sub="confidence ≥ 70%"
            />
            <KPITile
              icon={Clock}
              label="Weeks Saved"
              value={data.time_saved_weeks}
              colorClass="bg-amber-600"
              sub="vs. manual discovery"
            />
          </div>

          {/* Action buttons */}
          {data.analyzed && (
            <div className="flex gap-3">
              <button
                onClick={handleAnalyze}
                disabled={running}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white disabled:opacity-50 transition-opacity"
                style={{ background: '#0066cc' }}
              >
                {running ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <RefreshCw size={14} />
                )}
                Re-run Analysis
              </button>
              <button
                onClick={handleGenerateDemo}
                disabled={running}
                className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-gray-700 bg-white border border-gray-300 disabled:opacity-50 hover:bg-gray-50 transition-colors"
              >
                <Play size={14} />
                Reset with Demo Data
              </button>
            </div>
          )}

          {/* Date range */}
          {data.earliest && data.latest && (
            <p className="text-xs text-gray-400 mt-6">
              Data range: {new Date(data.earliest).toLocaleDateString()} —{' '}
              {new Date(data.latest).toLocaleDateString()}
            </p>
          )}
        </>
      )}
    </div>
  )
}
