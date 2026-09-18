import { useState, useEffect } from 'react'
import api from '../api/client'
import { FollowUp } from '../types'

const statusColors: Record<string, { bg: string; text: string; label: string }> = {
  pending: { bg: 'bg-amber-500/20', text: 'text-amber-400', label: 'Ожидает' },
  sent: { bg: 'bg-green-500/20', text: 'text-green-400', label: 'Отправлено' },
  cancelled: { bg: 'bg-muted/20', text: 'text-muted', label: 'Отменено' },
  failed: { bg: 'bg-error/20', text: 'text-error', label: 'Ошибка' },
}

export default function FollowUpDashboard() {
  const [followUps, setFollowUps] = useState<FollowUp[]>([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [searchInput, setSearchInput] = useState('')
  const [page, setPage] = useState(1)
  const pageSize = 25

  useEffect(() => {
    loadFollowUps()
  }, [])

  const loadFollowUps = async () => {
    try {
      const { data } = await api.get('/follow-ups/all')
      setFollowUps(data)
    } catch (e) {
      console.error('Failed to load follow-ups', e)
    } finally {
      setLoading(false)
    }
  }

  const filtered = followUps
    .filter(f => statusFilter === 'all' || f.status === statusFilter)
    .filter(f => !searchInput || 
      f.subject?.toLowerCase().includes(searchInput.toLowerCase()) ||
      f.recipient_email?.toLowerCase().includes(searchInput.toLowerCase()) ||
      f.company_name?.toLowerCase().includes(searchInput.toLowerCase())
    )
    .sort((a, b) => {
      const aTime = a.scheduled_at ? new Date(a.scheduled_at).getTime() : 0
      const bTime = b.scheduled_at ? new Date(b.scheduled_at).getTime() : 0
      return bTime - aTime
    })

  const totalPages = Math.ceil(filtered.length / pageSize)
  const paginated = filtered.slice((page - 1) * pageSize, page * pageSize)

  const handleStatusChange = async (fup: FollowUp, newStatus: string) => {
    try {
      await api.patch(`/follow-ups/${fup.id}`, { status: newStatus })
      setFollowUps(prev => prev.map(f => f.id === fup.id ? { ...f, status: newStatus } : f))
    } catch (e) {
      console.error('Failed to update follow-up', e)
      alert('Ошибка при обновлении статуса')
    }
  }

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return '—'
    const d = new Date(dateStr)
    return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
  }

  const isOverdue = (fup: FollowUp) => fup.status === 'pending' && fup.scheduled_at && new Date(fup.scheduled_at) < new Date()

  const stats = {
    pending: followUps.filter(f => f.status === 'pending').length,
    sent: followUps.filter(f => f.status === 'sent').length,
    cancelled: followUps.filter(f => f.status === 'cancelled').length,
    overdue: followUps.filter(f => f.status === 'pending' && f.scheduled_at && new Date(f.scheduled_at) < new Date()).length,
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 p-4 bg-bg border-b border-muted/10">
        <h1 className="text-xl font-semibold text-text">Напоминания</h1>
        <div className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Поиск по теме, email, компании..."
            value={searchInput}
            onChange={e => { setSearchInput(e.target.value); setPage(1) }}
            className="px-3 py-1.5 text-sm bg-bg-border border-muted/10 rounded-lg text-text placeholder:text-muted focus:outline-none focus:ring-1 focus:ring-accent w-64"
          />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-3 py-1.5 text-sm bg-bg-border border-muted/10 rounded-lg text-text focus:outline-none focus:ring-1 focus:ring-accent"
          >
            <option value="all">Все статусы</option>
            <option value="pending">Ожидает</option>
            <option value="sent">Отправлено</option>
            <option value="cancelled">Отменено</option>
            <option value="failed">Ошибка</option>
          </select>
        </div>
      </div>

      <div className="flex gap-2 px-4 mb-3">
        <div className="px-3 py-1.5 text-sm bg-accent/20 text-accent rounded-lg">
          Всего: <span className="font-semibold">{followUps.length}</span>
        </div>
        <div className="px-3 py-1.5 text-sm bg-amber-500/20 text-amber-400 rounded-lg">
          Ожидает: <span className="font-semibold">{stats.pending}</span>
        </div>
        <div className="px-3 py-1.5 text-sm bg-error/20 text-error rounded-lg">
          Просрочено: <span className="font-semibold">{stats.overdue}</span>
        </div>
        <div className="px-3 py-1.5 text-sm bg-green-500/20 text-green-400 rounded-lg">
          Отправлено: <span className="font-semibold">{stats.sent}</span>
        </div>
        <div className="px-3 py-1.5 text-sm bg-muted/20 text-muted rounded-lg">
          Отменено: <span className="font-semibold">{stats.cancelled}</span>
        </div>
      </div>

      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center h-full text-muted">Загрузка...</div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-full text-muted text-sm">Напоминаний не найдено</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-muted/10 text-left text-muted">
                <th className="pb-2 pr-4 font-medium">Дата / Время</th>
                <th className="pb-2 pr-4 font-medium">Компания</th>
                <th className="pb-2 pr-4 font-medium">Тема</th>
                <th className="pb-2 pr-4 font-medium">Email</th>
                <th className="pb-2 pr-4 font-medium">Статус</th>
                <th className="pb-2 pr-4 font-medium">Действия</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map(fup => {
                const overdue = isOverdue(fup)
                const s = statusColors[fup.status] || statusColors.pending
                return (
                  <tr key={fup.id} className="border-b border-muted/5 hover:bg-muted/20 transition-colors">
                    <td className="py-2 pr-4 text-text">
                      <span className={overdue ? 'text-error font-medium' : ''}>
                        {formatDate(fup.scheduled_at)}
                      </span>
                      {overdue && <span className="ml-1 text-xs text-error">(просрочено)</span>}
                    </td>
                    <td className="py-2 pr-4 text-text truncate max-w-xs" title={fup.company_name || ''}>
                      {fup.company_name || '—'}
                    </td>
                    <td className="py-2 pr-4 text-text truncate max-w-md" title={fup.subject || ''}>
                      {fup.subject || '—'}
                    </td>
                    <td className="py-2 pr-4 text-muted truncate max-w-xs" title={fup.recipient_email || ''}>
                      {fup.recipient_email || '—'}
                    </td>
                    <td className="py-2 pr-4">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${s.bg} ${s.text}`}>
                        {s.label}
                      </span>
                    </td>
                    <td className="py-2 pr-4">
                      <div className="flex items-center gap-1">
                        {fup.status === 'pending' && (
                          <>
                            <button
                              onClick={() => handleStatusChange(fup, 'cancelled')}
                              className="px-2 py-1 text-xs text-muted hover:text-text hover:bg-muted/20 rounded transition-colors"
                              title="Отменить"
                            >
                              Отменить
                            </button>
                          </>
                        )}
                        {fup.status === 'cancelled' && (
                          <button
                            onClick={() => handleStatusChange(fup, 'pending')}
                            className="px-2 py-1 text-xs text-accent hover:bg-accent/20 rounded transition-colors"
                            title="Вернуть в ожидание"
                          >
                            Активировать
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 px-4 py-3 border-t border-muted/10">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-1.5 text-sm bg-bg-border border-muted/10 rounded-lg text-text hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Назад
          </button>
          <span className="px-3 text-sm text-muted">
            Страница {page} из {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-1.5 text-sm bg-bg-border border-muted/10 rounded-lg text-text hover:bg-muted disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Вперёд
          </button>
        </div>
      )}
    </div>
  )
}