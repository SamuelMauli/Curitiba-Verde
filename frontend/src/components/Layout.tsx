import { Outlet, NavLink } from 'react-router-dom'
import { LayoutDashboard, Map, Clock, GitCompare, FileText, TreePine } from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/map', icon: Map, label: 'Mapa' },
  { to: '/timeline', icon: Clock, label: 'Timeline' },
  { to: '/compare', icon: GitCompare, label: 'Comparar' },
  { to: '/reports', icon: FileText, label: 'Relatórios' },
]

export default function Layout() {
  return (
    <div style={{ display: 'flex', height: '100vh', width: '100vw' }}>
      {/* Sidebar */}
      <nav style={{
        width: 72,
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '16px 0',
        gap: 4,
      }}>
        <div style={{
          width: 40, height: 40,
          background: 'var(--accent)',
          borderRadius: 10,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 24,
        }}>
          <TreePine size={22} color="#fff" />
        </div>

        {navItems.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            style={({ isActive }) => ({
              width: 48, height: 48,
              borderRadius: 10,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: isActive ? '#10B981' : '#6b7280',
              background: isActive ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
              textDecoration: 'none',
              transition: 'all 0.2s',
            })}
            title={label}
          >
            <Icon size={22} />
          </NavLink>
        ))}
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
        <Outlet />
      </main>
    </div>
  )
}
