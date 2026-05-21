import { useState, useEffect, useRef } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import api from '../api/client'
import StatusBadge from './StatusBadge'
import CompanyCard from './CompanyCard'

interface Company {
  id: string
  name: string
  inn: string
  region: string | null
  phone: string | null
  website: string | null
  call_status: string
  call_count: number
  next_call_date: string | null
  assigned_to: string | null
  revenue: number | null
  activity_main: string | null
}

export default function CompanyTable() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const { data } = await api.get('/companies', {
          params: { page, page_size: 50, search }
        })
        setCompanies(data.items)
        setTotal(data.total)
      } finally {
        setLoading(false)
      }
    }
    fetchCompanies()
  }, [page, search])

  const parentRef = useRef<HTMLDivElement>(null)
  const virtualizer = useVirtualizer({
    count: companies.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 5,
  })

  const formatRevenue = (val: number | null) => {
    if (!val) return '—'
    if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
    if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
    if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
    return val.toString()
  }

  if (loading) return <div className="flex items-center justify-center h-64">Загрузка...</div>

  return (
    <div className="flex h-full">
      <div className="flex-1 flex flex-col">
        <div className="p-4 border-b border-muted/10">
          <input
            type="text"
            placeholder="Поиск по названию, ИНН, телефону..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full px-4 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
          />
        </div>
        
        <div className="grid grid-cols-12 gap-2 px-4 py-2 text-xs font-medium text-muted border-b border-muted/10">
          <div className="col-span-3">Компания</div>
          <div className="col-span-1">ИНН</div>
          <div className="col-span-1">Регион</div>
          <div className="col-span-2">Деятельность</div>
          <div className="col-span-1">Выручка</div>
          <div className="col-span-1">Телефон</div>
          <div className="col-span-1">Попыток</div>
          <div className="col-span-1">Статус</div>
          <div className="col-span-1">Перезвонить</div>
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
                  className="absolute inset-x-0 grid grid-cols-12 gap-2 px-4 items-center h-10 hover:bg-surfaceHover cursor-pointer border-b border-muted/5"
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                >
                  <div className="col-span-3 font-medium truncate">{company.name}</div>
                  <div className="col-span-1 font-mono text-xs truncate">{company.inn}</div>
                  <div className="col-span-1 text-muted truncate">{company.region || '—'}</div>
                  <div className="col-span-2 text-muted truncate">{company.activity_main || '—'}</div>
                  <div className="col-span-1">{formatRevenue(company.revenue)}</div>
                  <div className="col-span-1">
                    {company.phone ? (
                      <a href={`tel:${company.phone}`} className="text-accent hover:underline">{company.phone}</a>
                    ) : '—'}
                  </div>
                  <div className="col-span-1 text-center">{company.call_count}</div>
                  <div className="col-span-1"><StatusBadge status={company.call_status} /></div>
                  <div className="col-span-1 text-xs">
                    {company.next_call_date ? (
                      <span className={new Date(company.next_call_date) < new Date() ? 'text-error' : ''}>
                        {company.next_call_date}
                      </span>
                    ) : '—'}
                  </div>
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
