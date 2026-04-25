import { useState, useEffect } from 'react'
import { getRecommendations, pushToIllumio } from '../api/client'
import type { Recommendation } from '../types'
import { Upload, CheckCircle, ToggleLeft, ToggleRight } from 'lucide-react'

const TYPE_BADGE: Record<string, string> = {
  WORKLOAD_GROUP: 'bg-purple-100 text-purple-800',
  APP_DEPENDENCY: 'bg-blue-100 text-blue-800',
  IP_LIST: 'bg-teal-100 text-teal-800',
  SERVICE: 'bg-orange-100 text-orange-800',
}

function syntaxHighlight(json: string): string {
  const escaped = json
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
  return escaped.replace(
    /("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*"(\s*:)?|\b(true|false|null)\b|-?\d+(?:\.\d*)?(?:[eE][+\-]?\d+)?)/g,
    (match) => {
      let cls = 'color:#fb923c'
      if (/^"/.test(match)) {
        cls = /:$/.test(match) ? 'color:#93c5fd' : 'color:#86efac'
      } else if (/true|false/.test(match)) {
        cls = 'color:#c4b5fd'
      } else if (/null/.test(match)) {
        cls = 'color:#6b7280'
      }
      return `<span style="${cls}">${match}</span>`
    },
  )
}

export default function IllumioPublish() {
  const [approved, setApproved] = useState<Recommendation[]>([])
  const [selected, setSelected] = useState<Recommendation | null>(null)
  const [dryRun, setDryRun] = useState(true)
  const [pushing, setPushing] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getRecommendations({ status: 'APPROVED', page_size: 200 })
      .then((r) => {
        const items = r.data.items
        setApproved(items)
        if (items.length > 0) setSelected(items[0])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  const handlePush = async () => {
    setPushing(true)
    setResult(null)
    try {
      const r = await pushToIllumio(dryRun)
      setResult(JSON.stringify(r.data, null, 2))
    } catch (e: unknown) {
      setResult('Error: ' + (e instanceof Error ? e.message : 'unknown'))
    } finally {
      setPushing(false)
    }
  }

  const payloadJson = selected?.illumio_payload
    ? JSON.stringify(selected.illumio_payload, null, 2)
    : '{}'

  return (
    <div className="p-8 h-full flex flex-col">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Publish to Illumio</h1>
      <p className="text-gray-500 mb-6 text-sm">
        Push approved policy objects to Illumio PCE as drafts.
      </p>

      <div className="flex gap-6 flex-1 min-h-0" style={{ height: 'calc(100vh - 200px)' }}>
        {/* Left panel */}
        <div className="w-72 flex-shrink-0 bg-white rounded-xl border border-gray-200 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-200 bg-gray-50 flex-shrink-0">
            <div className="text-sm font-semibold text-gray-700">
              Approved ({approved.length})
            </div>
            {approved.length === 0 && !loading && (
              <p className="text-xs text-gray-400 mt-0.5">
                Go to Recommendations to approve items
              </p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-sm text-gray-400">Loading…</div>
            ) : (
              approved.map((rec) => (
                <button
                  key={rec.id}
                  onClick={() => { setSelected(rec); setResult(null) }}
                  className="w-full text-left px-4 py-3 border-b border-gray-100 hover:bg-gray-50 transition-colors"
                  style={
                    selected?.id === rec.id
                      ? { background: '#eff6ff', borderLeft: '3px solid #0066cc' }
                      : {}
                  }
                >
                  <div className="flex items-center justify-between mb-1">
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-medium ${
                        TYPE_BADGE[rec.type] ?? 'bg-gray-100 text-gray-700'
                      }`}
                    >
                      {rec.type}
                    </span>
                    <CheckCircle size={12} className="text-green-500" />
                  </div>
                  <div className="font-mono text-xs text-gray-700 truncate">{rec.name}</div>
                </button>
              ))
            )}
          </div>

          {/* Controls */}
          <div className="p-4 border-t border-gray-200 space-y-3 flex-shrink-0">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-700">Dry Run</span>
              <button
                onClick={() => setDryRun((d) => !d)}
                className="text-gray-400 hover:text-gray-600"
                style={{ color: dryRun ? '#0066cc' : '#9ca3af' }}
              >
                {dryRun ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
              </button>
            </div>
            {dryRun && (
              <p className="text-xs text-amber-700 bg-amber-50 rounded px-2 py-1.5">
                Dry run: payloads only, no PCE writes
              </p>
            )}
            <button
              onClick={handlePush}
              disabled={pushing || approved.length === 0}
              className="w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium text-white disabled:opacity-50 transition-opacity"
              style={{ background: '#0066cc' }}
            >
              {pushing ? (
                <span
                  className="animate-spin h-4 w-4 rounded-full border-b-2 border-white"
                />
              ) : (
                <Upload size={14} />
              )}
              {dryRun ? 'Preview Push' : 'Push to PCE'}
            </button>
          </div>
        </div>

        {/* Right panel — JSON preview */}
        <div
          className="flex-1 rounded-xl overflow-hidden flex flex-col"
          style={{ background: '#1a2332' }}
        >
          <div
            className="px-4 py-3 border-b flex items-center justify-between flex-shrink-0"
            style={{ borderColor: 'rgba(255,255,255,0.1)' }}
          >
            <span className="text-sm font-medium" style={{ color: '#8fa3b8' }}>
              {result
                ? 'Push Result'
                : selected
                  ? `Payload: ${selected.name}`
                  : 'Select a recommendation'}
            </span>
            {result && (
              <button
                onClick={() => setResult(null)}
                className="text-xs hover:text-gray-200"
                style={{ color: '#6b7280' }}
              >
                Clear
              </button>
            )}
          </div>
          <pre
            className="flex-1 overflow-auto p-5 text-xs leading-relaxed font-mono"
            style={{ color: '#d1d5db' }}
            dangerouslySetInnerHTML={{
              __html: syntaxHighlight(result ?? payloadJson),
            }}
          />
        </div>
      </div>
    </div>
  )
}
