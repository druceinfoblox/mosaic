import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import OverviewPage from './pages/OverviewPage'
import DependencyExplorer from './pages/DependencyExplorer'
import RecommendationWorkbench from './pages/RecommendationWorkbench'
import WorkloadDetail from './pages/WorkloadDetail'
import IllumioPublish from './pages/IllumioPublish'
import AmbiguityQueue from './pages/AmbiguityQueue'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen overflow-hidden">
        {/* Top Nav */}
        <header
          className="flex items-center justify-between px-5 shrink-0"
          style={{ backgroundColor: '#172628', height: '48px' }}
        >
          <div className="flex items-center gap-3">
            {/* Infoblox wordmark */}
            <svg width="90" height="18" viewBox="0 0 90 18" fill="none" xmlns="http://www.w3.org/2000/svg">
              <text x="0" y="14" fontFamily="Inter,sans-serif" fontSize="14" fontWeight="700" fill="white" letterSpacing="-0.3">infoblox</text>
            </svg>
            <span style={{ color: 'rgba(255,255,255,0.35)' }}>|</span>
            <span className="text-sm font-medium" style={{ color: 'rgba(255,255,255,0.85)' }}>Mosaic</span>
          </div>
          <span className="text-xs px-2 py-0.5 rounded" style={{ background: '#1F6FE0', color: 'white' }}>
            DNS → Microsegmentation
          </span>
        </header>

        {/* Body */}
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto p-6" style={{ backgroundColor: '#F4F6F6' }}>
            <Routes>
              <Route path="/" element={<OverviewPage />} />
              <Route path="/explorer" element={<DependencyExplorer />} />
              <Route path="/recommendations" element={<RecommendationWorkbench />} />
              <Route path="/workloads" element={<WorkloadDetail />} />
              <Route path="/workloads/:ip" element={<WorkloadDetail />} />
              <Route path="/publish" element={<IllumioPublish />} />
              <Route path="/ambiguity" element={<AmbiguityQueue />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </main>
        </div>

        {/* Footer */}
        <div
          className="text-center text-xs py-1 border-t shrink-0"
          style={{ color: '#6E7679', borderColor: '#E6E9EA', backgroundColor: 'white' }}
        >
          Infoblox DNS Intelligence &nbsp;·&nbsp; Project Mosaic
        </div>
      </div>
    </BrowserRouter>
  )
}
