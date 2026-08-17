import { useEffect, useState } from 'react'
import { useAuth } from '../store/auth'
import api from '../api/client'
import CompanyTable from '../components/CompanyTable'
import PipelineBoard from '../components/PipelineBoard'
import ImportModal from '../components/ImportModal'
import ProfileModal from '../components/ProfileModal'
import GuideModal, { shouldShowGuide } from '../components/GuideModal'
import StatusBadge from '../components/StatusBadge'
import { DashboardStats } from '../types'

const tabs = [
  { key: 'companies', label: 'Компании' },
  { key: 'pipeline', label: 'Воронка' },
  { key: 'followup', label: 'Follow-up', disabled: true },
]

export default function Dashboard() {
  const user = useAuth((s) => s.user)
  const logout = useAuth((s) => s.logout)
  const [metrics, setMetrics] = useState<DashboardStats | null>(null)
  const [showImport, setShowImport] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [activeTab, setActiveTab] = useState('companies')
  const [pipelineFilter, setPipelineFilter] = useState<string | null>(null)
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null)
  const [showGuide, setShowGuide] = useState(false)

  useEffect(() => {
    api.get('/dashboard/me').then(({ data }) => setMetrics(data))
  }, [])

  useEffect(() => {
    const timer = setTimeout(() => {
      if (shouldShowGuide()) setShowGuide(true)
    }, 600)
    return () => clearTimeout(timer)
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
          <button onClick={() => setShowGuide(true)} className="w-8 h-8 rounded-full font-bold text-sm bg-accent/20 text-accent hover:bg-accent/30 transition-colors" title="Мануал" aria-label="Открыть мануал">
            ?
          </button>
          <span className="text-sm text-muted">{user?.name || user?.email}</span>
          <button onClick={logout} className="text-sm text-muted hover:text-text">Выйти</button>
        </div>
      </header>

      {metrics && (
        <div className="grid grid-cols-7 gap-4 p-4">
          <MetricCard label="Задач сегодня" value={metrics.tasks_today} color="accent" />
          <MetricCard label="Просрочено" value={metrics.overdue} color="error" />
          <MetricCard label="Звонков сегодня" value={metrics.calls_today} color="success" />
          <MetricCard label="Необработанных" value={metrics.unprocessed} color="info" />
          <MetricCard label="В архиве" value={metrics.archived} color="warning" />
          <MetricCard label="Всего компаний" value={metrics.total_companies} color="muted" />
          <MetricCard label="Воронка" value={
            metrics.pipeline_counts ? Object.values(metrics.pipeline_counts).reduce((a, b) => a + b, 0) : 0
          } color="pipeline" />
        </div>
      )}

      {/* Pipeline mini-stats */}
      {metrics?.pipeline_counts && (
        <div className="flex gap-2 px-4 pb-2 overflow-x-auto">
          {Object.entries(metrics.pipeline_counts).map(([stage, count]) => (
            <button
              key={stage}
              onClick={() => { setActiveTab('companies'); setPipelineFilter(stage) }}
              className={`flex items-center gap-1.5 px-2 py-1 rounded-lg text-xs transition-colors ${
                pipelineFilter === stage ? 'bg-accent/20 ring-1 ring-accent' : 'bg-surface hover:bg-surface/80'
              }`}
            >
              <StatusBadge status={stage} kind="pipeline" />
              <span className="font-mono text-muted">{count}</span>
            </button>
          ))}
          {pipelineFilter && (
            <button
              onClick={() => setPipelineFilter(null)}
              className="text-xs text-muted hover:text-text px-2"
            >
              ✕
            </button>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 px-4 border-b border-muted/10">
        {tabs.map(tab => (
          <button
            key={tab.key}
            disabled={tab.disabled}
            onClick={() => setActiveTab(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.key
                ? 'border-accent text-text'
                : 'border-transparent text-muted hover:text-text'
            } ${tab.disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === 'companies' && <CompanyTable pipelineFilter={pipelineFilter} openCompanyId={selectedCompanyId} onCompanyClose={() => setSelectedCompanyId(null)} />}
        {activeTab === 'pipeline' && (
          <PipelineBoard
            onSelectCompany={(id) => { setSelectedCompanyId(id); setActiveTab('companies') }}
            onNavigateToCompany={(stage) => { setSelectedCompanyId(null); setActiveTab('companies'); setPipelineFilter(stage) }}
          />
        )}
        {activeTab === 'followup' && (
          <div className="flex items-center justify-center h-full text-muted text-sm">
            Скоро
          </div>
        )}
      </div>

      {showImport && <ImportModal onClose={() => setShowImport(false)} />}
      {showProfile && <ProfileModal onClose={() => setShowProfile(false)} />}
      <GuideModal open={showGuide} onClose={() => setShowGuide(false)} />
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
    pipeline: 'border-purple-500/30',
  }
  const valueColors: Record<string, string> = {
    accent: 'text-accent',
    error: 'text-error',
    success: 'text-success',
    muted: 'text-text',
    info: 'text-info',
    warning: 'text-warning',
    pipeline: 'text-purple-400',
  }
  
  return (
    <div className={`p-4 bg-surface rounded-xl border ${colorClasses[color] || 'border-muted/20'}`}>
      <p className="text-sm text-muted">{label}</p>
      <p className={`text-2xl font-bold ${valueColors[color] || 'text-text'}`}>{value}</p>
    </div>
  )
}
