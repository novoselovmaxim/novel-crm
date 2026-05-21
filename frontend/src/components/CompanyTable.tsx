import { useState, useEffect, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import api from '../api/client'
import StatusBadge from './StatusBadge'
import CompanyCard from './CompanyCard'
import { Company } from '../types'

const STATUSES = [
  { value: '', label: 'Все статусы' },
  { value: 'new', label: 'Новый' },
  { value: 'not_reached', label: 'Не дозвонился' },
  { value: 'no_answer', label: 'Не отвечает' },
  { value: 'callback', label: 'Перезвонить' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'interested', label: 'Заинтересован' },
  { value: 'meeting', label: 'Встреча назначена' },
  { value: 'refused', label: 'Отказ' },
]

const PAGE_SIZES = [30, 50, 100]

const COLUMNS = [
  { key: 'name', label: 'Компания', width: 'min-w-[200px]' },
  { key: 'inn', label: 'ИНН', width: 'min-w-[110px]' },
  { key: 'region', label: 'Регион', width: 'min-w-[140px]' },
  { key: 'org_form', label: 'ОПФ', width: 'min-w-[80px]' },
  { key: 'activity', label: 'Деятельность', width: 'min-w-[180px]' },
  { key: 'website', label: 'Сайт', width: 'min-w-[120px]' },
  { key: 'capital', label: 'Уст. капитал', width: 'min-w-[100px]' },
  { key: 'revenue', label: 'Выручка', width: 'min-w-[100px]' },
  { key: 'import', label: 'Импорт', width: 'min-w-[100px]' },
  { key: 'export', label: 'Экспорт', width: 'min-w-[100px]' },
  { key: 'director', label: 'Руководитель', width: 'min-w-[160px]' },
  { key: 'calls', label: 'Попыток', width: 'min-w-[70px]' },
  { key: 'status', label: 'Статус', width: 'min-w-[100px]' },
]

function RegionFilter({ value, onChange, regions }: { value: string; onChange: (v: string) => void; regions: string[] }) {
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState(value)
  const ref = useRef<HTMLDivElement>(null)

  const filtered = regions.filter(r => r.toLowerCase().includes(input.toLowerCase())).slice(0, 50)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const select = (r: string) => {
    setInput(r)
    onChange(r)
    setOpen(false)
  }

  return (
    <div ref={ref} className="relative">
      <input
        value={input}
        onChange={(e) => { setInput(e.target.value); onChange(e.target.value) }}
        onFocus={() => setOpen(true)}
        placeholder="Регион..."
        className="w-48 px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
      />
      {open && filtered.length > 0 && (
        <div className="absolute top-full left-0 mt-1 w-64 max-h-60 overflow-auto bg-surface border border-muted/20 rounded-lg shadow-xl z-50">
          {filtered.map(r => (
            <button
              key={r}
              onClick={() => select(r)}
              className={`w-full text-left px-3 py-1.5 text-sm hover:bg-surfaceHover ${r === value ? 'text-accent' : ''}`}
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
  if (!val) return '—'
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
  if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
  if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
  return val.toLocaleString('ru-RU')
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

export default function CompanyTable() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [regionFilter, setRegionFilter] = useState('')
  const [regions, setRegions] = useState<string[]>([])
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    api.get('/companies/regions').then(({ data }) => {
      setRegions(data.regions || [])
    })
  }, [])

  useEffect(() => {
    const fetchCompanies = async () => {
      setLoading(true)
      try {
        const { data } = await api.get('/companies', {
          params: { page, page_size: pageSize, search, status: statusFilter || undefined, region: regionFilter || undefined }
        })
        setCompanies(data.items)
        setTotal(data.total)
      } finally {
        setLoading(false)
      }
    }
    fetchCompanies()
  }, [page, pageSize, search, statusFilter, regionFilter])

  const scrollRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: companies.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => 44,
    overscan: 5,
  })

  const clearFilters = () => {
    setSearch('')
    setStatusFilter('')
    setRegionFilter('')
    setPage(1)
  }

  const hasFilters = search || statusFilter || regionFilter
  const totalPages = Math.ceil(total / pageSize)

  if (loading) return <div className="flex items-center justify-center h-64">Загрузка...</div>

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col min-w-0">
        <div className="p-4 border-b border-muted/10 space-y-3">
          <input
            type="text"
            placeholder="Поиск по названию, ИНН..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
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
            {hasFilters && (
              <button onClick={clearFilters} className="px-3 py-1.5 text-sm text-accent hover:underline">
                Сбросить
              </button>
            )}
          </div>
        </div>
        
        <div className="overflow-x-auto">
          <div className="inline-flex min-w-full">
            {COLUMNS.map(col => (
              <div key={col.key} className={`${col.width} px-3 py-2 text-xs font-medium text-muted border-r border-muted/5 shrink-0`}>
                {col.label}
              </div>
            ))}
          </div>
        </div>

        <div ref={scrollRef} className="flex-1 overflow-auto">
          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const c = companies[virtualRow.index]
              return (
                <div
                  key={c.id}
                  ref={virtualizer.measureElement}
                  data-index={virtualRow.index}
                  onClick={() => setSelectedCompany(c)}
                  className="absolute inset-x-0 flex hover:bg-surfaceHover cursor-pointer border-b border-muted/5"
                  style={{ transform: `translateY(${virtualRow.start}px)`, height: '44px' }}
                >
                  <div className={`${COLUMNS[0].width} px-3 font-medium truncate shrink-0`} title={c.name}>{c.name}</div>
                  <div className={`${COLUMNS[1].width} px-3 font-mono text-xs truncate shrink-0`} title={c.inn}>{c.inn}</div>
                  <div className={`${COLUMNS[2].width} px-3 text-muted truncate shrink-0`} title={c.region || ''}>{c.region || '—'}</div>
                  <div className={`${COLUMNS[3].width} px-3 text-muted text-xs truncate shrink-0`} title={c.org_form || ''}>{getOrgForm(c)}</div>
                  <div className={`${COLUMNS[4].width} px-3 text-muted truncate shrink-0`} title={getActivity(c)}>{getActivity(c)}</div>
                  <div className={`${COLUMNS[5].width} px-3 text-accent truncate shrink-0`} title={getWebsite(c) || ''}>
                    {getWebsite(c) ? <a href={getWebsite(c)!.startsWith('http') ? getWebsite(c)! : `https://${getWebsite(c)}`} target="_blank" rel="noopener" onClick={e => e.stopPropagation()} className="hover:underline">{getWebsite(c)!.replace(/^https?:\/\//, '').substring(0, 20)}</a> : '—'}
                  </div>
                  <div className={`${COLUMNS[6].width} px-3 truncate shrink-0`}>{formatMoney(c.capital)}</div>
                  <div className={`${COLUMNS[7].width} px-3 truncate shrink-0`}>{formatMoney(c.revenue)}</div>
                  <div className={`${COLUMNS[8].width} px-3 truncate shrink-0`}>{c.import_turnover || '—'}</div>
                  <div className={`${COLUMNS[9].width} px-3 truncate shrink-0`}>{c.export_turnover || '—'}</div>
                  <div className={`${COLUMNS[10].width} px-3 truncate shrink-0`} title={c.director || ''}>{c.director || '—'}</div>
                  <div className={`${COLUMNS[11].width} px-3 text-center shrink-0`}>{c.call_count}</div>
                  <div className={`${COLUMNS[12].width} px-3 shrink-0`}><StatusBadge status={c.call_status} /></div>
                </div>
              )
            })}
          </div>
        </div>

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

      {selectedCompany && (
        <CompanyCard company={selectedCompany} onClose={() => setSelectedCompany(null)} />
      )}
    </div>
  )
}
