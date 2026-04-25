import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Network,
  ListChecks,
  Server,
  Upload,
  AlertTriangle,
} from 'lucide-react'

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Overview' },
  { path: '/explorer', icon: Network, label: 'Explorer' },
  { path: '/recommendations', icon: ListChecks, label: 'Recommend.' },
  { path: '/workloads', icon: Server, label: 'Workloads' },
  { path: '/publish', icon: Upload, label: 'Publish' },
  { path: '/ambiguity', icon: AlertTriangle, label: 'Ambiguity' },
]

const itemClass = (isActive: boolean) =>
  `w-full flex flex-col items-center justify-center py-2.5 px-1 transition-colors cursor-pointer ${
    isActive
      ? 'text-white'
      : 'hover:bg-black/5'
  }`

export default function Sidebar() {
  return (
    <aside
      className="flex flex-col h-full border-r shrink-0"
      style={{ backgroundColor: '#E9EFE6', borderColor: '#d4ddd0', width: '5.5rem' }}
    >
      <nav className="flex-1 flex flex-col items-center py-3 gap-0.5">
        {navItems.map(({ path, icon: Icon, label }) => (
          <NavLink
            key={path}
            to={path}
            end={path === '/'}
            className={({ isActive }) => itemClass(isActive)}
            style={({ isActive }) => ({
              background: isActive ? '#1F6FE0' : undefined,
              color: isActive ? '#ffffff' : '#5a6e60',
            })}
          >
            <Icon size={20} className="mb-1" />
            <span style={{ fontSize: '10px', lineHeight: '1.2', fontWeight: 500, textAlign: 'center' }}>
              {label}
            </span>
          </NavLink>
        ))}
      </nav>
      <div className="py-3 border-t text-center" style={{ borderColor: '#d4ddd0' }}>
        <span style={{ fontSize: '10px', color: '#8fa897' }}>v0.1.0</span>
      </div>
    </aside>
  )
}
