import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, FolderOpen, FileText, Users, BookOpen, Menu, X, Building2, BarChart2
} from 'lucide-react'
import { useState } from 'react'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Дашборд' },
  { to: '/projects', icon: FolderOpen, label: 'Проекты' },
  { to: '/documents', icon: FileText, label: 'Документы' },
  { to: '/agents', icon: Users, label: 'Команда' },
  { to: '/normatives', icon: BookOpen, label: 'Нормативы РК' },
  { to: '/statistics', icon: BarChart2, label: 'Статистика' },
]

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <aside className={`
        flex flex-col bg-slate-900 text-white transition-all duration-300
        ${sidebarOpen ? 'w-64' : 'w-16'}
      `}>
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-slate-700">
          <Building2 size={28} className="text-blue-400 shrink-0" />
          {sidebarOpen && (
            <div>
              <div className="font-bold text-lg leading-tight">KazBuildOS</div>
              <div className="text-xs text-slate-400">Строительство РК</div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 overflow-y-auto">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 mx-2 rounded-lg transition-colors
                ${isActive
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`
              }
            >
              <Icon size={20} className="shrink-0" />
              {sidebarOpen && <span className="text-sm font-medium">{label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* Toggle */}
        <button
          onClick={() => setSidebarOpen(!sidebarOpen)}
          className="flex items-center justify-center p-4 border-t border-slate-700 hover:bg-slate-800"
        >
          {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
        </button>
      </aside>

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-slate-800">
              Система управления строительством
            </h1>
            <p className="text-xs text-slate-500">
              Нормативная база: Республика Казахстан
            </p>
          </div>
          <div className="flex items-center gap-2 text-xs text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            Система активна
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
