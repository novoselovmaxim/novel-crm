import { useState, useEffect, useRef, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import api from '../api/client'
import StatusBadge from './StatusBadge'
import CompanyCard from './CompanyCard'
import CalendarModal from './CalendarModal'
import { Company, User } from '../types'
import { useAuth } from '../store/auth'

interface ImportSource {
  id: string
  original_filename: string
}

const STATUS_DOT: Record<string, string> = {
  new: 'bg-gray-500',
  not_reached: 'bg-orange-500',
  no_answer: 'bg-red-500',
  callback: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  interested: 'bg-green-500',
  thinking: 'bg-teal-500',
  meeting: 'bg-purple-500',
  refused: 'bg-gray-600',
}

const STATUSES = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новый' },
  { value: 'not_reached', label: 'Не дозвонился' },
  { value: 'no_answer', label: 'Не отвечает' },
  { value: 'callback', label: 'Перезвонить' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'interested', label: 'Заинтересован' },
  { value: 'thinking', label: 'Думают' },
  { value: 'meeting', label: 'Встреча назначена' },
  { value: 'refused', label: 'Отказ' },
]

const CHECKBOX_W = 40
const PAGE_SIZES = [30, 50, 100]

const COL_DEFS = [
  { key: 'name', label: 'Компания', w: 220 },
  { key: 'inn', label: 'ИНН', w: 120 },
  { key: 'region', label: 'Регион', w: 160 },
  { key: 'org_form', label: 'ОПФ', w: 70 },
  { key: 'activity', label: 'Вид деятельности', w: 200 },
  { key: 'website', label: 'Сайт', w: 140 },
  { key: 'capital', label: 'Уст. капитал', w: 110 },
  { key: 'revenue', label: 'Выручка', w: 110 },
  { key: 'import', label: 'Импорт', w: 110 },
  { key: 'export', label: 'Экспорт', w: 110 },
  { key: 'director', label: 'Руководитель', w: 180 },
  { key: 'calls', label: 'Попыток', w: 70 },
  { key: 'status', label: 'Статус', w: 110 },
  { key: 'manager', label: 'Менеджер', w: 150 },
]

const TOTAL_W = COL_DEFS.reduce((s, c) => s + c.w, 0)

function SearchableFilter({ value, onChange, items, placeholder }: { value: string; onChange: (v: string) => void; items: string[]; placeholder: string }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = items.filter(r => r.toLowerCase().includes(query.toLowerCase())).slice(0, 80)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (value) setQuery(value)
  }, [value])

  const select = useCallback((r: string) => {
    setQuery(r)
    onChange(r)
    setOpen(false)
    inputRef.current?.blur()
  }, [onChange])

  const clear = useCallback(() => {
    setQuery('')
    onChange('')
  }, [onChange])

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') { setOpen(false); setQuery(value || ''); inputRef.current?.blur() }
            if (e.key === 'Enter' && filtered.length > 0) { select(filtered[0]) }
          }}
          placeholder={placeholder}
          className="w-44 px-3 py-1.5 bg-bg border border-muted/20 rounded-l-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
        />
        {query && (
          <button onClick={clear} className="px-2 py-1.5 bg-bg border border-l-0 border-muted/20 rounded-r-lg text-muted hover:text-text text-xs">
            ✕
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-72 max-h-64 overflow-auto bg-surface border border-muted/20 rounded-lg shadow-xl z-50">
          {filtered.map(r => (
            <button
              key={r}
              onClick={() => select(r)}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-surfaceHover"
            >
              {r}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function RegionFilter({ value, onChange, regions }: { value: string; onChange: (v: string) => void; regions: string[] }) {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const ref = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const filtered = regions.filter(r => r.toLowerCase().includes(query.toLowerCase())).slice(0, 80)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
        setQuery('')
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  useEffect(() => {
    if (value) setQuery(value)
  }, [value])

  const select = useCallback((r: string) => {
    setQuery(r)
    onChange(r)
    setOpen(false)
    inputRef.current?.blur()
  }, [onChange])

  const clear = useCallback(() => {
    setQuery('')
    onChange('')
  }, [onChange])

  return (
    <div ref={ref} className="relative">
      <div className="flex items-center">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => { setQuery(e.target.value); setOpen(true) }}
          onFocus={() => setOpen(true)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') { setOpen(false); setQuery(value || ''); inputRef.current?.blur() }
            if (e.key === 'Enter' && filtered.length > 0) { select(filtered[0]) }
          }}
          placeholder="Регион..."
          className="w-44 px-3 py-1.5 bg-bg border border-muted/20 rounded-l-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
        />
        {query && (
          <button onClick={clear} className="px-2 py-1.5 bg-bg border border-l-0 border-muted/20 rounded-r-lg text-muted hover:text-text text-xs">
            ✕
          </button>
        )}
      </div>
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-72 max-h-64 overflow-auto bg-surface border border-muted/20 rounded-lg shadow-xl z-50">
          {filtered.map(r => (
            <button
              key={r}
              onClick={() => select(r)}
              className="w-full text-left px-3 py-1.5 text-sm hover:bg-surfaceHover"
            >
              {r}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

function formatMoney(val: number | null | undefined) {
  if (val === null || val === undefined) return '—'
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
  if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
  if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
  return val.toLocaleString('ru-RU')
}

function formatNumericString(val: string | null | undefined) {
  if (!val || val === '') return '—'
  // Try to parse as number
  const num = parseFloat(val)
  if (isNaN(num)) return val // Return as-is if not a number
  
  // Format like formatMoney but without the currency symbol
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)} млрд`
  if (num >= 1e6) return `${(num / 1e6).toFixed(0)} млн`
  if (num >= 1e3) return `${(num / 1e3).toFixed(0)} тыс`
  return num.toLocaleString('ru-RU')
}

function getWebsite(c: Company) {
  return c.website || c.focus_link || null
}

function getActivity(c: Company) {
  return c.activity_main || c.niche || c.activity_code || '—'
}

function getOrgForm(c: Company) {
  if (!c.org_form) return '—'
  const map: Record<string, string> = {
    'Общество с ограниченной ответственностью': 'ООО',
    'Акционерное общество': 'АО',
    'Открытое акционерное общество': 'ОАО',
    'Закрытое акционерное общество': 'ЗАО',
    'Индивидуальный предприниматель': 'ИП',
    'Публичное акционерное общество': 'ПАО',
    'Некоммерческая организация': 'НО',
  }
  return map[c.org_form] || c.org_form.substring(0, 10)
}

const STORAGE_KEY = 'crm_table_state'

function loadSavedState<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return key in parsed ? parsed[key] : fallback
    }
  } catch {}
  return fallback
}

function saveTableState(state: Record<string, unknown>) {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const prev = raw ? JSON.parse(raw) : {}
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...prev, ...state }))
  } catch {}
}

export default function CompanyTable({ pipelineFilter, openCompanyId: externalCompanyId, onCompanyClose }: { pipelineFilter?: string | null; openCompanyId?: string | null; onCompanyClose?: () => void }) {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [searchInput, setSearchInput] = useState(() => loadSavedState('searchInput', ''))
  const [search, setSearch] = useState(() => loadSavedState('search', ''))
  const [statusFilter, setStatusFilter] = useState(() => loadSavedState('statusFilter', ''))
  const [regionFilter, setRegionFilter] = useState(() => loadSavedState('regionFilter', ''))
  const [managerFilter, setManagerFilter] = useState(() => loadSavedState('managerFilter', ''))
  const [archived, setArchived] = useState(() => loadSavedState('archived', false))
  const [showCalendar, setShowCalendar] = useState(false)
  const [regions, setRegions] = useState<string[]>([])
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(() => loadSavedState('pageSize', 50))
  const [total, setTotal] = useState(0)
  const [managers, setManagers] = useState<User[]>([])
  const ORG_FORM_SHORT: Record<string, string> = {
    'Общество с ограниченной ответственностью': 'ООО',
    'Акционерное общество': 'АО',
    'Открытое акционерное общество': 'ОАО',
    'Закрытое акционерное общество': 'ЗАО',
    'Индивидуальный предприниматель': 'ИП',
    'Публичное акционерное общество': 'ПАО',
    'Некоммерческая организация': 'НО',
  }

  const [sourceFilter, setSourceFilter] = useState(() => loadSavedState('sourceFilter', ''))
  const [sources, setSources] = useState<ImportSource[]>([])
  const [sortBy, setSortBy] = useState(() => loadSavedState('sortBy', ''))
  const [sortOrder, setSortOrder] = useState(() => loadSavedState('sortOrder', 'desc'))
  const [orgFormFilter, setOrgFormFilter] = useState(() => loadSavedState('orgFormFilter', ''))
  const [activityFilter, setActivityFilter] = useState(() => loadSavedState('activityFilter', ''))
  const [orgForms, setOrgForms] = useState<string[]>([])
  const [activities, setActivities] = useState<string[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [refreshKey, setRefreshKey] = useState(0)
  const currentUser = useAuth(s => s.user)
  const isAdminOrLead = currentUser?.role === 'admin' || currentUser?.role === 'lead'

  const toggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const toggleSelectAll = () => {
    setSelectedIds(prev => prev.size === companies.length ? new Set() : new Set(companies.map(c => c.id)))
  }

  const handleMeetingClick = async (companyId: string) => {
    try {
      const { data } = await api.get(`/companies/${companyId}`)
      setSelectedCompany(data)
    } catch (error) {
      console.error('Failed to fetch company for meeting:', error)
      // Don't setSelectedCompany on error - user stays in current view
      // Modal remains open so they can try again or see context
    }
  }

  useEffect(() => {
    setPage(1)
  }, [pipelineFilter])

  useEffect(() => {
    if (!externalCompanyId) return
    api.get(`/companies/${externalCompanyId}`).then(({ data }) => setSelectedCompany(data)).catch(() => {})
  }, [externalCompanyId])

  useEffect(() => {
    const timer = setTimeout(() => setSearch(searchInput), 400)
    return () => clearTimeout(timer)
  }, [searchInput])

  useEffect(() => {
    api.get('/companies/regions').then(({ data }) => {
      setRegions(data.regions || [])
    })
    api.get('/companies/org-forms').then(({ data }) => {
      setOrgForms(data.org_forms || [])
    })
    api.get('/companies/activities').then(({ data }) => {
      setActivities(data.activities || [])
    })
    api.get('/auth/managers').then(({ data }) => {
      setManagers(data)
    })
    api.get('/import/sources').then(({ data }) => {
      setSources(data)
    })
  }, [])

  const managerMap = Object.fromEntries(managers.map(m => [m.id, m.name || m.email]))

  useEffect(() => {
    const fetchCompanies = async () => {
      setLoading(true)
      try {
        const params: Record<string, any> = { page, page_size: pageSize, search, status: statusFilter || undefined, pipeline_stage: pipelineFilter || undefined, region: regionFilter || undefined, assigned_to: managerFilter || undefined, archived, source: sourceFilter || undefined, org_form: orgFormFilter || undefined, activity: activityFilter || undefined }
        if (sortBy) { params.sort_by = sortBy; params.sort_order = sortOrder }
        const { data } = await api.get('/companies', { params })
        setCompanies(data.items)
        setTotal(data.total)
      } catch {
        setCompanies([])
        setTotal(0)
      } finally {
        setLoading(false)
      }
    }
    fetchCompanies()
  }, [page, pageSize, search, statusFilter, pipelineFilter, regionFilter, managerFilter, archived, sourceFilter, sortBy, sortOrder, orgFormFilter, activityFilter, refreshKey])

  useEffect(() => {
    const timer = setTimeout(() => {
      saveTableState({
        searchInput, search, statusFilter, regionFilter, managerFilter,
        archived, sourceFilter, sortBy, sortOrder, orgFormFilter,
        activityFilter, pageSize
      })
    }, 1000)
    return () => clearTimeout(timer)
  }, [searchInput, search, statusFilter, regionFilter, managerFilter, archived, sourceFilter, sortBy, sortOrder, orgFormFilter, activityFilter, pageSize])

  const scrollRef = useRef<HTMLDivElement>(null)
  const headerRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: companies.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 40,
    overscan: 5,
  })

  useEffect(() => {
    const el = scrollRef.current
    const header = headerRef.current
    if (!el || !header) return
    const handler = () => { header.scrollLeft = el.scrollLeft }
    el.addEventListener('scroll', handler)
    return () => el.removeEventListener('scroll', handler)
  }, [])

  const clearFilters = () => {
    setSearchInput('')
    setSearch('')
    setStatusFilter('')
    setRegionFilter('')
    setManagerFilter('')
    setSourceFilter('')
    setOrgFormFilter('')
    setActivityFilter('')
    setSortBy('')
    setSortOrder('desc')
    setPage(1)
  }

  const toggleSort = (field: string) => {
    const fields = sortBy ? sortBy.split(',') : []
    const orders = sortOrder ? sortOrder.split(',') : []
    const idx = fields.indexOf(field)
    if (idx >= 0) {
      const cur = orders[idx]
      if (cur === 'desc') {
        orders[idx] = 'asc'
      } else {
        fields.splice(idx, 1)
        orders.splice(idx, 1)
      }
    } else {
      fields.push(field)
      orders.push('desc')
    }
    setSortBy(fields.join(','))
    setSortOrder(orders.join(','))
    setPage(1)
  }

  const hasFilters = searchInput || statusFilter || regionFilter || managerFilter || sourceFilter || orgFormFilter || activityFilter || sortBy
  const totalPages = Math.ceil(total / pageSize)

  if (loading) return <div className="flex items-center justify-center h-64">Загрузка...</div>

  return (
    <div className="flex h-full">
      {/* Table area */}
      <div className={`flex flex-col h-full ${selectedCompany ? 'flex-1 min-w-0' : 'flex-1 min-w-0'}`}>
        {/* Filters */}
        <div className="p-3 border-b border-muted/10 space-y-2 shrink-0">
        <input
          type="text"
          placeholder="Поиск по названию, ИНН..."
          value={searchInput}
          onChange={(e) => { setSearchInput(e.target.value); setPage(1) }}
          className="w-full px-4 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
        />
        <div className="flex gap-3 items-center">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(1) }}
            className="px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          >
            {STATUSES.map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          <RegionFilter value={regionFilter} onChange={(v) => { setRegionFilter(v); setPage(1) }} regions={regions} />
          <select
            value={orgFormFilter}
            onChange={(e) => { setOrgFormFilter(e.target.value); setPage(1) }}
            className="px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent w-24 [&>option]:w-auto"
            style={{ maxWidth: 'fit-content' }}
          >
            <option value="">Все ОПФ</option>
            {orgForms.map(f => (
              <option key={f} value={f} className="text-sm">{ORG_FORM_SHORT[f] || f}</option>
            ))}
          </select>
          <SearchableFilter value={activityFilter} onChange={(v) => { setActivityFilter(v); setPage(1) }} items={activities} placeholder="Деятельность..." />
          {sources.length > 0 && (
            <div className="flex items-center gap-1">
              <select
                value={sourceFilter}
                onChange={(e) => { setSourceFilter(e.target.value); setPage(1) }}
                className="px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">Все источники</option>
                {sources.map(s => (
                  <option key={s.id} value={s.id}>{s.original_filename}</option>
                ))}
              </select>
              {sourceFilter && (
                <button
                  onClick={async () => {
                    if (!confirm('Удалить источник импорта и все его данные?')) return
                    try {
                      await api.delete(`/import/sources/${sourceFilter}`)
                      setSources(prev => prev.filter(s => s.id !== sourceFilter))
                      setSourceFilter('')
                    } catch {
                      alert('Ошибка при удалении')
                    }
                  }}
                  className="px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-muted hover:text-error text-xs"
                  title="Удалить источник"
                >
                  🗑
                </button>
              )}
            </div>
          )}
          {isAdminOrLead && managers.map(m => (
            <button
              key={m.id}
              onClick={() => { setManagerFilter(managerFilter === m.id ? '' : m.id); setPage(1) }}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
                managerFilter === m.id
                  ? 'bg-accent text-white'
                  : 'bg-surface text-muted hover:text-text border border-muted/20'
              }`}
            >
              {m.name || m.email}
            </button>
          ))}
          {hasFilters && (
            <button onClick={clearFilters} className="px-3 py-1.5 text-sm text-accent hover:underline">
              Сбросить
            </button>
          )}
          <div className="ml-auto flex gap-1 bg-bg rounded-lg border border-muted/20 p-0.5">
            <button
              onClick={() => setShowCalendar(true)}
              className="px-3 py-1 text-xs font-medium rounded-md text-muted hover:text-text transition-colors"
            >
              Календарь
            </button>
            <button
              onClick={() => { setArchived(false); setPage(1); setStatusFilter('') }}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${!archived ? 'bg-accent text-white' : 'text-muted hover:text-text'}`}
            >
              Активные
            </button>
            <button
              onClick={() => { setArchived(true); setPage(1); setStatusFilter('') }}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${archived ? 'bg-accent text-white' : 'text-muted hover:text-text'}`}
            >
              Архив
            </button>
          </div>
        </div>
      </div>

      {selectedIds.size > 0 && (
        <div className="px-3 py-2 bg-accent/10 border-b border-accent/20 flex items-center gap-3 shrink-0">
          <span className="text-sm font-medium">Выбрано: {selectedIds.size}</span>
          <select
            value=""
            onChange={async (e) => {
              const status = e.target.value
              if (!status) return
              try {
                await api.post('/companies/bulk-status', { company_ids: [...selectedIds], call_status: status })
                setSelectedIds(new Set())
                setRefreshKey(k => k + 1)
              } catch {
                alert('Ошибка при обновлении статуса')
              }
            }}
            className="px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          >
            <option value="">Изменить статус</option>
            {STATUSES.filter(s => s.value).map(s => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
          {isAdminOrLead && (
            <select
              value=""
              onChange={async (e) => {
                const val = e.target.value
                if (!val) return
                try {
                  await api.post('/companies/bulk-assign', { company_ids: [...selectedIds], user_id: val === 'unassign' ? null : val })
                  setSelectedIds(new Set())
                  setRefreshKey(k => k + 1)
                } catch {
                  alert('Ошибка при назначении менеджера')
                }
              }}
              className="px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Назначить менеджера</option>
              <option value="unassign">Снять менеджера</option>
              {managers.map(m => (
                <option key={m.id} value={m.id}>{m.name || m.email}</option>
              ))}
            </select>
          )}
          <button
            onClick={async () => {
              try {
                const response = await api.post('/companies/export', { company_ids: [...selectedIds] }, { responseType: 'blob' })
                const url = URL.createObjectURL(new Blob([response.data], { type: 'text/csv;charset=utf-8' }))
                const link = document.createElement('a')
                link.href = url
                link.setAttribute('download', 'companies.csv')
                document.body.appendChild(link)
                link.click()
                link.remove()
                URL.revokeObjectURL(url)
              } catch {
                alert('Ошибка при экспорте')
              }
            }}
            className="px-3 py-1.5 bg-accent text-white text-sm font-medium rounded-lg hover:bg-accent/90 transition-colors"
          >
            Экспорт CSV
          </button>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="px-3 py-1.5 text-sm text-muted hover:text-text transition-colors"
          >
            Снять выделение
          </button>
        </div>
      )}

      {/* Table */}
      <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
        {/* Header */}
          <div ref={headerRef} className="overflow-x-auto overflow-y-hidden shrink-0" style={{ scrollbarWidth: 'none' }}>
            <div className="flex" style={{ width: TOTAL_W + CHECKBOX_W, minWidth: TOTAL_W + CHECKBOX_W }}>
              <div className="px-3 shrink-0 flex items-center" style={{ width: CHECKBOX_W }}>
                <input type="checkbox" checked={companies.length > 0 && selectedIds.size === companies.length} onChange={toggleSelectAll} onClick={e => e.stopPropagation()} className="cursor-pointer accent-accent" />
              </div>
              {COL_DEFS.map(col => {
              const sortable = col.key === 'revenue' || col.key === 'name'
              const sortFields = sortBy ? sortBy.split(',') : []
              const sortOrders = sortOrder ? sortOrder.split(',') : []
              const si = sortFields.indexOf(col.key)
              return (
                <div
                  key={col.key}
                  onClick={sortable ? () => toggleSort(col.key) : undefined}
                  className={`px-3 py-2 text-xs font-medium text-muted border-r border-muted/5 truncate shrink-0 flex items-center gap-1 ${sortable ? 'cursor-pointer hover:text-text select-none' : ''}`}
                  style={{ width: col.w }}
                >
                  {col.label}
                  {si >= 0 && (
                    <span className="text-[10px]">{sortOrders[si] === 'asc' ? '▲' : '▼'}</span>
                  )}
                  {sortable && si >= 0 && sortFields.length > 1 && (
                    <span className="text-[9px] text-muted/50">{si + 1}</span>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Body */}
          <div ref={scrollRef} className="flex-1 overflow-auto">
            <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative', width: TOTAL_W + CHECKBOX_W, minWidth: TOTAL_W + CHECKBOX_W }}>
              {virtualizer.getVirtualItems().map((virtualRow) => {
                const c = companies[virtualRow.index]
                return (
                  <div
                    key={c.id}
                    ref={virtualizer.measureElement}
                    data-index={virtualRow.index}
                    onClick={() => setSelectedCompany(c)}
                    className="absolute left-0 right-0 flex hover:bg-surfaceHover cursor-pointer border-b border-muted/5"
                    style={{ transform: `translateY(${virtualRow.start}px)`, height: '40px', width: TOTAL_W + CHECKBOX_W, minWidth: TOTAL_W + CHECKBOX_W }}
                  >
                    <div className="px-3 shrink-0 flex items-center" style={{ width: CHECKBOX_W }}>
                      <input type="checkbox" checked={selectedIds.has(c.id)} onChange={() => toggleSelect(c.id)} onClick={e => e.stopPropagation()} className="cursor-pointer accent-accent" />
                    </div>
                    <div className="px-3 font-medium truncate shrink-0 flex items-center" style={{ width: COL_DEFS[0].w }} title={c.name}>{c.name}</div>
                  <div className="px-3 font-mono text-xs truncate shrink-0 flex items-center" style={{ width: COL_DEFS[1].w }} title={c.inn}>{c.inn}</div>
                  <div className="px-3 text-muted truncate shrink-0 flex items-center" style={{ width: COL_DEFS[2].w }} title={c.region || ''}>{c.region || '—'}</div>
                  <div className="px-3 text-muted text-xs truncate shrink-0 flex items-center" style={{ width: COL_DEFS[3].w }} title={c.org_form || ''}>{getOrgForm(c)}</div>
                  <div className="px-3 text-muted truncate shrink-0 flex items-center" style={{ width: COL_DEFS[4].w }} title={getActivity(c)}>{getActivity(c)}</div>
                  <div className="px-3 text-accent truncate shrink-0 flex items-center" style={{ width: COL_DEFS[5].w }} title={getWebsite(c) || ''}>
                    {getWebsite(c) ? (
                      <a href={getWebsite(c)!.startsWith('http') ? getWebsite(c)! : `https://${getWebsite(c)}`} target="_blank" rel="noopener" onClick={e => e.stopPropagation()} className="hover:underline truncate">
                        {getWebsite(c)!.replace(/^https?:\/\//, '').substring(0, 22)}
                      </a>
                    ) : '—'}
                  </div>
<div className="px-3 truncate shrink-0 flex items-center" style={{ width: COL_DEFS[6].w }}>{formatMoney(c.capital)}</div>
<div className="px-3 truncate shrink-0 flex items-center" style={{ width: COL_DEFS[7].w }}>{formatMoney(c.revenue)}</div>
<div className="px-3 truncate shrink-0 flex items-center" style={{ width: COL_DEFS[8].w }}>{formatNumericString(c.import_turnover)}</div>
<div className="px-3 truncate shrink-0 flex items-center" style={{ width: COL_DEFS[9].w }}>{formatNumericString(c.export_turnover)}</div>
                  <div className="px-3 truncate shrink-0 flex items-center" style={{ width: COL_DEFS[10].w }} title={c.director || ''}>{c.director || '—'}</div>
                  <div className="px-3 text-center shrink-0 flex items-center justify-center" style={{ width: COL_DEFS[11].w }}>{c.call_count}</div>
                  <div className="px-1 shrink-0 flex items-center gap-1" style={{ width: COL_DEFS[12].w }}>
                    {isAdminOrLead ? (
                      <>
                        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${STATUS_DOT[c.call_status] || 'bg-gray-500'}`} />
                        <select
                          value={c.call_status}
                          onMouseDown={e => e.stopPropagation()}
                          onClick={e => e.stopPropagation()}
                          onChange={async (e) => {
                            e.stopPropagation()
                            const val = e.target.value
                            const prevStatus = c.call_status
                            setCompanies(prev => prev.map(p => p.id === c.id ? { ...p, call_status: val } : p))
                            try {
                              await api.patch(`/companies/${c.id}/status`, { call_status: val })
                            } catch {
                              setCompanies(prev => prev.map(p => p.id === c.id ? { ...p, call_status: prevStatus } : p))
                            }
                          }}
                          className="w-full px-1 py-1 bg-bg border border-muted/20 rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
                        >
                          {STATUSES.filter(s => s.value).map(s => (
                            <option key={s.value} value={s.value}>{s.label}</option>
                          ))}
                        </select>
                      </>
                    ) : (
                      <StatusBadge status={c.call_status} />
                    )}
                  </div>
                  <div className="px-1 shrink-0 flex items-center" style={{ width: COL_DEFS[13].w }}>
                    {isAdminOrLead ? (
                      <select
                        value={c.assigned_to || ''}
                        onClick={e => e.stopPropagation()}
                        onChange={async (e) => {
                          e.stopPropagation()
                          const val = e.target.value || null
                          const prevAssigned = c.assigned_to
                          setCompanies(prev => prev.map(p => p.id === c.id ? { ...p, assigned_to: val } : p))
                          try {
                            await api.patch(`/companies/${c.id}/assign`, { user_id: val })
                          } catch {
                            setCompanies(prev => prev.map(p => p.id === c.id ? { ...p, assigned_to: prevAssigned } : p))
                          }
                        }}
                        className="w-full px-1 py-1 bg-bg border border-muted/20 rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
                      >
                        <option value="">—</option>
                        {managers.map(m => (
                          <option key={m.id} value={m.id}>{m.name || m.email}</option>
                        ))}
                      </select>
                    ) : (
                      <span className="text-xs text-muted truncate">{managerMap[c.assigned_to || ''] || '—'}</span>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Pagination */}
        <div className="p-3 border-t border-muted/10 flex items-center justify-between text-sm text-muted shrink-0">
          <div className="flex items-center gap-4">
            <span>Всего: {total}</span>
            <span>Страниц: {totalPages}</span>
            <div className="flex items-center gap-2">
              <span className="text-xs">Показать:</span>
              <select
                value={pageSize}
                onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
                className="px-2 py-1 bg-bg border border-muted/20 rounded text-xs focus:outline-none focus:ring-2 focus:ring-accent"
              >
                {PAGE_SIZES.map(n => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-2 items-center">
            <button onClick={() => setPage(1)} disabled={page === 1} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              В начало
            </button>
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              Назад
            </button>
            <span className="px-3 py-1">Стр. {page} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page >= totalPages} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              Вперёд
            </button>
          </div>
        </div>
      </div>
      </div>
      {/* Company Card - right side */}
      {selectedCompany && (
        <div className="shrink-0 border-l border-muted/10">
          <CompanyCard company={selectedCompany} onClose={() => { setSelectedCompany(null); onCompanyClose?.() }} onAssign={(userId) => setCompanies(prev => prev.map(p => p.id === selectedCompany.id ? { ...p, assigned_to: userId } : p))} onFieldUpdate={(field, value) => { setSelectedCompany(prev => prev ? { ...prev, [field]: value } : null); setCompanies(prev => prev.map(p => p.id === selectedCompany.id ? { ...p, [field]: value } : p)) }} onNavigateToCompany={handleMeetingClick} />
        </div>
      )}

      {showCalendar && <CalendarModal onClose={() => setShowCalendar(false)} onMeetingClick={(companyId) => { setShowCalendar(false); handleMeetingClick(companyId) }} />}
    </div>
  )
}
