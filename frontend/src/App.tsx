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
      <div className="flex h-screen overflow-hidden bg-gray-50">
        <Sidebar />
        <main className="flex-1 overflow-auto">
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
    </BrowserRouter>
  )
}
