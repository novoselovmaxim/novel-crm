import { useEffect, useState } from 'react'
import { useAuth } from '../store/auth'
import api from '../api/client'
import CompanyTable from '../components/CompanyTable'

interface Metrics {
  total_companies: number
  new_companies: number
  in_progress: number
  interested: number
  meetings_scheduled: number
  refused: number
  calls_today: number
  tasks_today: number
  overdue: number
}

export default function Dashboard() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const [metrics, setMetrics] = useState<Metrics | null>(null)

  useEffect(() => {
    api.get('/dashboard/me').then(({ data }) => setMetrics(data))
  }, [])

  return (
    <div className="h-screen flex flex-col bg-bg">
      <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-muted/10">
        <h1 className="text-xl font-bold">Novel CRM</h1>
        <div className="flex items-center gap-4">
          <span className="text-sm text-muted">{user?.name || user?.email}</span>
          <button onClick={logout} className="text-sm text-muted hover:text-text">Выйти</button>
        </div>
      </header>

      {metrics && (
        <div className="grid grid-cols-4 gap-4 p-4">
          <MetricCard label="Задач на сегодня" value={metrics.tasks_today} color="accent" />
          <MetricCard label="Просрочено" value={metrics.overdue} color="error" />
          <MetricCard label="Звонков сегодня" value={metrics.calls_today} color="success" />
          <MetricCard label="Всего компаний" value={metrics.total_companies} color="muted" />
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <CompanyTable />
      </div>
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    accent: 'border-accent/30',
    error: 'border-error/30',
    success: 'border-success/30',
    muted: 'border-muted/20',
  }
  const valueColors: Record<string, string> = {
    accent: 'text-accent',
    error: 'text-error',
    success: 'text-success',
    muted: 'text-text',
  }
  
  return (
    <div className={`p-4 bg-surface rounded-xl border ${colorClasses[color]}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`text-2xl font-bold ${valueColors[color]}`}>{value}</p>
    </div>
  )
}
