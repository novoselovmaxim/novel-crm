import { useEffect, useState } from 'react'
import { useAuth } from '../store/auth'
import api from '../api/client'
import CompanyTable from '../components/CompanyTable'
import ImportModal from '../components/ImportModal'
import ProfileModal from '../components/ProfileModal'

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
  archived: number
  unprocessed: number
}

export default function Dashboard() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const [metrics, setMetrics] = useState<Metrics | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showProfile, setShowProfile] = useState(false)

  useEffect(() => {
    api.get('/dashboard/me').then(({ data }) => setMetrics(data))
  }, [])

  return (
    <div className="h-screen flex flex-col bg-bg">
      <header className="flex items-center justify-between px-6 py-3 bg-surface border-b border-muted/10">
        <h1 className="text-xl font-bold">Novel CRM</h1>
        <div className="flex items-center gap-4">
          {user?.role === 'admin' && (
            <button onClick={() => setShowImport(true)} className="text-sm text-muted hover:text-text">Импорт</button>
          )}
          <button onClick={() => setShowProfile(true)} className="text-sm text-muted hover:text-text">Настройки</button>
          <span className="text-sm text-muted">{user?.name || user?.email}</span>
          <button onClick={logout} className="text-sm text-muted hover:text-text">Выйти</button>
        </div>
      </header>

      {metrics && (
        <div className="grid grid-cols-6 gap-4 p-4">
          <MetricCard label="Задач на сегодня" value={metrics.tasks_today} color="accent" />
          <MetricCard label="Просрочено" value={metrics.overdue} color="error" />
          <MetricCard label="Звонков сегодня" value={metrics.calls_today} color="success" />
          <MetricCard label="Необработанных" value={metrics.unprocessed} color="info" />
          <MetricCard label="В архиве" value={metrics.archived} color="warning" />
          <MetricCard label="Всего компаний" value={metrics.total_companies} color="muted" />
        </div>
      )}

      <div className="flex-1 overflow-hidden">
        <CompanyTable />
      </div>

      {showImport && <ImportModal onClose={() => setShowImport(false)} />}
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} />}
    </div>
  )
}

function MetricCard({ label, value, color }: { label: string; value: number; color: string }) {
  const colorClasses: Record<string, string> = {
    accent: 'border-accent/30',
    error: 'border-error/30',
    success: 'border-success/30',
    muted: 'border-muted/20',
    info: 'border-info/30',
    warning: 'border-warning/30',
  }
  const valueColors: Record<string, string> = {
    accent: 'text-accent',
    error: 'text-error',
    success: 'text-success',
    muted: 'text-text',
    info: 'text-info',
    warning: 'text-warning',
  }
  
  return (
    <div className={`p-4 bg-surface rounded-xl border ${colorClasses[color]}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`text-2xl font-bold ${valueColors[color]}`}>{value}</p>
    </div>
  )
}
