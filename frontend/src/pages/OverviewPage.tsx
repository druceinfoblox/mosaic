import { useState, useEffect } from 'react'
import { getOverview, generateDemo, generateDemoStatus, runAnalysis, resetDatabase } from '../api/client'
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
  Trash2,
} from 'lucide-react'

interface KPITileProps {
  icon: React.ElementType
  label: string
  value: number | string
  iconColor: string
  sub?: string
}

function KPITile({ icon: Icon, label, value, iconColor, sub }: KPITileProps) {
  return (
    <div
      className="rounded-md p-5 flex items-center justify-between"
      style={{ background: 'white', border: '1px solid hsl(186 8% 88%)' }}
    >
      <div>
        <p style={{ fontSize: '11px', fontWeight: 500, color: '#6E7679', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
          {label}
        </p>
        <p style={{ fontSize: '28px', fontWeight: 700, color: '#1F6FE0', marginTop: '4px', lineHeight: 1 }}>
          {typeof value === 'number' ? value.toLocaleString() : value}
        </p>
        {sub && (
          <p style={{ fontSize: '11px', color: '#6E7679', marginTop: '4px' }}>{sub}</p>
        )}
      </div>
      <Icon size={32} style={{ color: iconColor, opacity: 0.25 }} />
    </div>
  )
}

function Spinner() {
  return (
    <div className="animate-spin h-8 w-8 rounded-full border-2 border-transparent"
      style={{ borderTopColor: '#1F6FE0', borderRightColor: '#1F6FE0' }} />
  )
}

export default function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [msgType, setMsgType] = useState<'success' | 'error'>('success')

  const load = () => {
    setLoading(true)
    setError(null)
    getOverview()
      .then((r) => { setData(r.data); setLoading(false) })
      .catch((e: unknown) => {
        setError(e instanceof Error ? e.message : 'Failed to load overview')
        setLoading(false)
      })
  }

  useEffect(() => { load() }, [])

  const handleGenerateDemo = async () => {
    setRunning(true)
    setMsg('Generating demo data…')
    setMsgType('success')
    try {
      const { data: d } = await generateDemo()
      const jobId = d.job_id
      await new Promise<void>((resolve, reject) => {
        const poll = setInterval(async () => {
          try {
            const { data: job } = await generateDemoStatus(jobId)
            if (job.status === 'done') { clearInterval(poll); resolve() }
            else if (job.status === 'error') { clearInterval(poll); reject(new Error(job.error ?? 'Unknown error')) }
          } catch (e) { clearInterval(poll); reject(e) }
        }, 2000)
      })
      setMsg('Demo data generated and analyzed successfully!')
      setMsgType('success')
      load()
    } catch (e: unknown) {
      setMsg('Error: ' + (e instanceof Error ? e.message : 'unknown error'))
      setMsgType('error')
    } finally { setRunning(false) }
  }

  const handleAnalyze = async () => {
    setRunning(true)
    setMsg(null)
    try {
      await runAnalysis()
      setMsg('Analysis complete!')
      setMsgType('success')
      load()
    } catch (e: unknown) {
      setMsg('Error: ' + (e instanceof Error ? e.message : 'unknown error'))
      setMsgType('error')
    } finally { setRunning(false) }
  }

  const handleReset = async () => {
    if (!window.confirm('Reset database? This will permanently delete all DNS events, profiles, and recommendations.')) return
    setRunning(true)
    setMsg(null)
    try {
      await resetDatabase()
      setMsg('Database cleared.')
      setMsgType('success')
      load()
    } catch (e: unknown) {
      setMsg('Error: ' + (e instanceof Error ? e.message : 'unknown error'))
      setMsgType('error')
    } finally { setRunning(false) }
  }

  return (
    <div className="max-w-7xl">
      {/* Page header */}
      <div className="mb-6">
        <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#22282A' }}>Overview</h1>
        <p style={{ fontSize: '13px', color: '#6E7679', marginTop: '2px' }}>
          DNS dependency analysis for Illumio microsegmentation
        </p>
      </div>

      {loading && (
        <div className="flex justify-center py-16"><Spinner /></div>
      )}

      {error && (
        <div className="rounded-md p-4 mb-5" style={{ background: '#FEF2F2', border: '1px solid #FECACA', color: '#C62828' }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {msg && (
        <div
          className="rounded-md p-4 mb-5"
          style={
            msgType === 'error'
              ? { background: '#FEF2F2', border: '1px solid #FECACA', color: '#C62828' }
              : { background: '#F0FDF4', border: '1px solid #BBF7D0', color: '#166534' }
          }
        >
          {msg}
        </div>
      )}

      {data && !loading && (
        <>
          {/* No-data call to action */}
          {!data.analyzed && (
            <div
              className="rounded-md p-5 mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
              style={{ background: '#EFF6FF', border: '1px solid #BFDBFE' }}
            >
              <div>
                <p style={{ fontWeight: 600, color: '#1e40af' }}>No data yet</p>
                <p style={{ fontSize: '13px', color: '#3b82f6', marginTop: '2px' }}>
                  Generate demo data to explore Mosaic, or upload your own DNS logs via the API.
                </p>
              </div>
              <button
                onClick={handleGenerateDemo}
                disabled={running}
                className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium text-white whitespace-nowrap disabled:opacity-50"
                style={{ background: '#1F6FE0' }}
              >
                {running ? <RefreshCw size={13} className="animate-spin" /> : <Play size={13} />}
                Generate Demo Data
              </button>
            </div>
          )}

          {/* KPI row 1 */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-4">
            <KPITile icon={Database} label="DNS Events" value={data.total_events} iconColor="#1F6FE0" sub={`${data.days_history} day history`} />
            <KPITile icon={Users} label="Unique Endpoints" value={data.unique_endpoints} iconColor="#4f46e5" />
            <KPITile icon={Globe} label="Unique FQDNs" value={data.unique_fqdns} iconColor="#0d9488" />
            <KPITile icon={Layers} label="App Dependencies" value={data.candidate_applications} iconColor="#7c3aed" />
          </div>

          {/* KPI row 2 */}
          <div className="grid grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <KPITile icon={Shield} label="Network Segments" value={data.candidate_segments} iconColor="#ea580c" />
            <KPITile icon={Zap} label="Draft Illumio Objects" value={data.draft_illumio_objects} iconColor="#db2777" />
            <KPITile icon={CheckCircle} label="High-Confidence Recs" value={data.high_confidence_recs} iconColor="#16a34a" sub="confidence ≥ 70%" />
            <KPITile icon={Clock} label="Weeks Saved" value={data.time_saved_weeks} iconColor="#d97706" sub="vs. manual discovery" />
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap gap-3">
            {data.analyzed && (
              <>
                <button
                  onClick={handleAnalyze}
                  disabled={running}
                  className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium text-white disabled:opacity-50"
                  style={{ background: '#1F6FE0' }}
                >
                  {running ? <RefreshCw size={13} className="animate-spin" /> : <RefreshCw size={13} />}
                  Re-run Analysis
                </button>
                <button
                  onClick={handleGenerateDemo}
                  disabled={running}
                  className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
                  style={{ background: 'white', border: '1px solid #d1d5db', color: '#374151' }}
                >
                  <Play size={13} />
                  Reset with Demo Data
                </button>
              </>
            )}
            <button
              onClick={handleReset}
              disabled={running}
              className="flex items-center gap-2 px-4 py-2 rounded text-sm font-medium disabled:opacity-50"
              style={{ background: 'white', border: '1px solid #FECACA', color: '#C62828' }}
            >
              <Trash2 size={13} />
              Clear Database
            </button>
          </div>

          {/* Date range */}
          {data.earliest && data.latest && (
            <p className="mt-6" style={{ fontSize: '12px', color: '#6E7679' }}>
              Data range: {new Date(data.earliest).toLocaleDateString()} — {new Date(data.latest).toLocaleDateString()}
            </p>
          )}
        </>
      )}
    </div>
  )
}
