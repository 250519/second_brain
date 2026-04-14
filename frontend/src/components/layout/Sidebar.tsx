import { NavLink } from 'react-router-dom'
import { Brain, LayoutDashboard, Upload, MessageSquare, BookOpen, Network, Lightbulb } from 'lucide-react'
import { useWikiStatus } from '../../hooks/useWikiStatus'

const nav = [
  { to: '/',       icon: LayoutDashboard, label: 'Dashboard', end: true },
  { to: '/ingest', icon: Upload,          label: 'Ingest' },
  { to: '/query',  icon: MessageSquare,   label: 'Query' },
  { to: '/wiki',   icon: BookOpen,        label: 'Wiki' },
  { to: '/graph',  icon: Network,         label: 'Graph' },
  { to: '/ideas',  icon: Lightbulb,       label: 'Ideas' },
]

export function Sidebar() {
  const { data: status } = useWikiStatus()

  return (
    <aside className="w-58 shrink-0 flex flex-col bg-surface-950 border-r border-white/[0.05] h-full overflow-y-auto grain">

      {/* Logo */}
      <div className="px-5 pt-6 pb-5 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-violet-600 flex items-center justify-center shrink-0 shadow-lg shadow-violet-900/40">
            <Brain className="h-4.5 w-4.5 text-white" />
          </div>
          <div>
            <p className="font-display text-[0.95rem] text-[#ede9e3] leading-none tracking-tight">Second Brain</p>
            <p className="text-[10px] text-white/25 mt-1 leading-none font-sans tracking-widest uppercase">Knowledge OS</p>
          <p className="text-[10px] text-violet-400/60 mt-1 leading-none font-sans">for Harsh</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-px">
        {nav.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-[0.875rem] font-medium transition-all duration-150 ${
                isActive
                  ? 'bg-violet-500/12 text-violet-200 shadow-[inset_0_0_0_1px_rgba(139,92,246,0.2)]'
                  : 'text-white/35 hover:text-white/75 hover:bg-white/[0.04]'
              }`
            }
          >
            {({ isActive }) => (
              <>
                <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-violet-400' : ''}`} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Stats panel */}
      {status && (
        <div className="mx-3 mb-4">
          <div className="rounded-2xl border border-white/[0.06] bg-surface-800 grain overflow-hidden">
            <div className="px-4 pt-4 pb-1">
              <p className="text-[10px] font-medium text-white/20 uppercase tracking-[0.15em]">Wiki Stats</p>
            </div>
            <div className="px-4 pb-4 pt-2 space-y-2.5">
              {[
                { label: 'Pages',   value: status.total_pages,  highlight: true  },
                { label: 'Sources', value: status.raw_sources,  highlight: false },
                { label: 'Ideas',   value: status.ideas_count,  highlight: false },
              ].map(({ label, value, highlight }) => (
                <div key={label} className="flex justify-between items-baseline">
                  <span className="text-xs text-white/30">{label}</span>
                  <span className={`stat-number text-xl ${highlight ? 'text-[#ede9e3]' : 'text-white/50'}`}>
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
