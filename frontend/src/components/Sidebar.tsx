import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Network,
  ListChecks,
  Server,
  Upload,
  AlertTriangle,
  Shield,
} from 'lucide-react'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Overview' },
  { path: '/explorer', icon: Network, label: 'Dependency Explorer' },
  { path: '/recommendations', icon: ListChecks, label: 'Recommendations' },
  { path: '/workloads', icon: Server, label: 'Workloads' },
  { path: '/publish', icon: Upload, label: 'Publish to Illumio' },
  { path: '/ambiguity', icon: AlertTriangle, label: 'Ambiguity Queue' },
]

export default function Sidebar() {
  return (
    <aside
      className="w-64 flex-shrink-0 flex flex-col h-screen overflow-hidden"
      style={{ background: '#1a2332' }}
    >
      {/* Logo */}
      <div className="p-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0"
            style={{ background: '#0066cc' }}
          >
            <Shield size={18} className="text-white" />
          </div>
          <div className="min-w-0">
            <div className="text-white font-bold text-sm leading-tight">Mosaic</div>
            <div className="text-xs leading-tight" style={{ color: '#7aadda' }}>
              DNS → Microsegmentation
            </div>
          </div>
        </div>
        <div className="mt-3 text-xs" style={{ color: '#4a6480' }}>
          Powered by Infoblox DNS
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-3 space-y-0.5 overflow-y-auto">
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'text-white font-medium'
                  : 'hover:text-white'
              }`
            }
            style={({ isActive }) => ({
              background: isActive ? '#0066cc' : 'transparent',
              color: isActive ? '#ffffff' : '#8fa3b8',
            })}
            onMouseEnter={(e) => {
              const el = e.currentTarget
              if (!el.classList.contains('active')) {
                el.style.background = 'rgba(255,255,255,0.08)'
              }
            }}
            onMouseLeave={(e) => {
              const el = e.currentTarget
              if (!el.dataset.active) {
                el.style.background = 'transparent'
              }
            }}
          >
            <Icon size={16} />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/10">
        <div className="text-xs" style={{ color: '#4a6480' }}>
          Mosaic v0.1.0
        </div>
      </div>
    </aside>
  )
}
