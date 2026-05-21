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

export default function CompanyTable() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [regionFilter, setRegionFilter] = useState('')
  const [regions, setRegions] = useState<string[]>([])
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    api.get('/companies', { params: { page: 1, page_size: 1000 } }).then(({ data }) => {
      const unique = [...new Set((data.items as Company[]).map((c) => c.region).filter(Boolean))] as string[]
      unique.sort()
      setRegions(unique)
    })
  }, [])

  useEffect(() => {
    const fetchCompanies = async () => {
      setLoading(true)
      try {
        const { data } = await api.get('/companies', {
          params: { page, page_size: 50, search, status: statusFilter || undefined, region: regionFilter || undefined }
        })
        setCompanies(data.items)
        setTotal(data.total)
      } finally {
        setLoading(false)
      }
    }
    fetchCompanies()
  }, [page, search, statusFilter, regionFilter])

  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: companies.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 5,
  })

  const formatRevenue = (val: number | null) => {
    if (!val) return '—'
    if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
    if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
    return val.toString()
  }

  const clearFilters = () => {
    setSearch('')
    setStatusFilter('')
    setRegionFilter('')
    setPage(1)
  }

  const hasFilters = search || statusFilter || regionFilter

  if (loading) return <div className="flex items-center justify-center h-64">Загрузка...</div>

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
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
            <select
              value={regionFilter}
              onChange={(e) => { setRegionFilter(e.target.value); setPage(1) }}
              className="px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            >
              <option value="">Все регионы</option>
              {regions.map(r => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
            {hasFilters && (
              <button onClick={clearFilters} className="px-3 py-1.5 text-sm text-accent hover:underline">
                Сбросить
              </button>
            )}
          </div>
        </div>
        
        <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium text-muted border-b border-muted/10">
          <div className="col-span-4">Компания</div>
          <div className="col-span-1">ИНН</div>
          <div className="col-span-2">Регион</div>
          <div className="col-span-2">Деятельность</div>
          <div className="col-span-1">Выручка</div>
          <div className="col-span-1">Попыток</div>
          <div className="col-span-1">Статус</div>
        </div>

        <div ref={parentRef} className="flex-1 overflow-auto">
          <div style={{ height: `${virtualizer.getTotalSize()}px`, position: 'relative' }}>
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const company = companies[virtualRow.index]
              return (
                <div
                  key={company.id}
                  ref={virtualizer.measureElement}
                  data-index={virtualRow.index}
                  onClick={() => setSelectedCompany(company)}
                  className="absolute inset-x-0 grid grid-cols-12 gap-2 px-4 items-center h-11 hover:bg-surfaceHover cursor-pointer border-b border-muted/5"
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                >
                  <div className="col-span-4 font-medium truncate" title={company.name}>{company.name}</div>
                  <div className="col-span-1 font-mono text-xs truncate" title={company.inn}>{company.inn}</div>
                  <div className="col-span-2 text-muted truncate" title={company.region || ''}>{company.region || '—'}</div>
                  <div className="col-span-2 text-muted truncate" title={company.activity_main || ''}>{company.activity_main || '—'}</div>
                  <div className="col-span-1 truncate">{formatRevenue(company.revenue)}</div>
                  <div className="col-span-1 text-center">{company.call_count}</div>
                  <div className="col-span-1"><StatusBadge status={company.call_status} /></div>
                </div>
              )
            })}
          </div>
        </div>

        <div className="p-3 border-t border-muted/10 flex items-center justify-between text-sm text-muted">
          <span>Всего: {total}</span>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
              Назад
            </button>
            <span className="px-3 py-1">Стр. {page}</span>
            <button onClick={() => setPage(p => p + 1)} disabled={page * 50 >= total} className="px-3 py-1 bg-surface rounded disabled:opacity-50">
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
