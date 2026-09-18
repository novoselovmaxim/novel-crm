import { useState, useEffect, useRef, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import api from '../api/client'
import { VedProfile } from '../types/ved'

interface Props {
  onSelect: (profile: VedProfile) => void
  onOpenCRM: (profile: VedProfile) => void
  onCreateInCRM: (profile: VedProfile) => void
  selectedInn: string | null
}

const DIR_COLORS: Record<string, string> = {
  import: 'bg-blue-500/20 text-blue-400',
  export: 'bg-green-500/20 text-green-400',
}

const PAGE_SIZES = [30, 50, 100]

const COL_DEFS = [
  { key: 'company_name', label: 'Компания', w: 240 },
  { key: 'inn', label: 'ИНН', w: 120 },
  { key: 'directions', label: 'Направление', w: 130 },
  { key: 'total_declarations', label: 'Деклараций', w: 100 },
  { key: 'total_customs_value', label: 'Тамож. стоимость', w: 140 },
  { key: 'destination_countries', label: 'Страны', w: 180 },
  { key: 'hs_codes', label: 'ТН ВЭД', w: 140 },
  { key: 'contact_phone', label: 'Телефон', w: 140 },
  { key: 'director', label: 'Руководитель', w: 180 },
  { key: 'company_id', label: 'В базе', w: 80 },
  { key: 'actions', label: 'Действия', w: 140 },
]

const TOTAL_W = COL_DEFS.reduce((s, c) => s + c.w, 0)

function formatNum(v: number | null): string {
  if (v == null) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} млрд`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн`
  return v.toLocaleString('ru-RU')
}

function CellValue({ profile, col, onOpenCRM, onCreateInCRM }: { profile: VedProfile; col: string; onOpenCRM: (p: VedProfile) => void; onCreateInCRM: (p: VedProfile) => void }) {
  switch (col) {
    case 'company_name':
      return <span className="font-medium text-text">{profile.company_name || '—'}</span>
    case 'inn':
      return <span className="text-muted font-mono text-xs">{profile.inn}</span>
    case 'directions':
      return (
        <div className="flex gap-1 flex-wrap">
          {profile.directions?.map(d => (
            <span key={d} className={`px-1.5 py-0.5 text-xs rounded ${DIR_COLORS[d] || 'bg-gray-500/20 text-gray-400'}`}>
              {d === 'import' ? 'ИМ' : 'ЭК'}
            </span>
          ))}
        </div>
      )
    case 'total_declarations':
      return <span className="text-text">{profile.total_declarations}</span>
    case 'total_customs_value':
      return <span className="text-text">{formatNum(profile.total_customs_value)}</span>
    case 'destination_countries':
      return (
        <span className="text-muted text-xs">
          {profile.destination_countries?.slice(0, 4).join(', ')}{profile.destination_countries && profile.destination_countries.length > 4 ? '...' : ''}
        </span>
      )
    case 'hs_codes':
      return (
        <span className="text-muted text-xs font-mono">
          {profile.hs_codes?.slice(0, 2).join(', ')}{profile.hs_codes && profile.hs_codes.length > 2 ? '...' : ''}
        </span>
      )
    case 'contact_phone':
      return <span className="text-muted text-xs truncate block max-w-[130px]">{profile.contact_phone || '—'}</span>
    case 'director':
      return <span className="text-muted text-xs truncate block max-w-[170px]">{profile.director || '—'}</span>
    case 'company_id':
      return profile.company_id
        ? <span className="text-green-400 text-lg" title="Есть в CRM">✓</span>
        : <span className="text-gray-600 text-lg" title="Нет в CRM">—</span>
    case 'actions':
      return (
        <div className="flex items-center gap-1">
          {profile.company_id ? (
            <button
              onClick={(e) => { e.stopPropagation(); onOpenCRM(profile) }}
              className="px-2 py-1 text-xs bg-accent/20 text-accent rounded hover:bg-accent/30 transition-colors"
              title="Открыть в CRM"
            >
              Открыть
            </button>
          ) : (
            <button
              onClick={(e) => { e.stopPropagation(); onCreateInCRM(profile) }}
              className="px-2 py-1 text-xs bg-green-500/20 text-green-400 rounded hover:bg-green-500/30 transition-colors"
              title="Создать в CRM"
            >
              + CRM
            </button>
          )}
        </div>
      )
    default:
      return <span className="text-muted">{(profile as any)[col] ?? '—'}</span>
  }
}

export default function VEDProfileTable({ onSelect, onOpenCRM, onCreateInCRM, selectedInn }: Props) {
  const [profiles, setProfiles] = useState<VedProfile[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [direction, setDirection] = useState('')
  const [hasCompany, setHasCompany] = useState<string>('')
  const [page, setPage] = useState(0)
  const [pageSize, setPageSize] = useState(50)
  const [total, setTotal] = useState(0)
  const [totalPages, setTotalPages] = useState(0)
  const parentRef = useRef<HTMLDivElement>(null)

  const fetchProfiles = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, any> = { offset: page * pageSize, limit: pageSize }
      if (search) params.search = search
      if (direction) params.direction = direction
      if (hasCompany === 'yes') params.has_company = true
      if (hasCompany === 'no') params.has_company = false
      const { data } = await api.get('/ved/profiles', { params })
      setProfiles(data.items)
      setTotal(data.total)
      setTotalPages(data.total_pages)
    } catch (e) {
      console.error('Failed to load VED profiles', e)
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, search, direction, hasCompany])

  useEffect(() => { fetchProfiles() }, [fetchProfiles])

  useEffect(() => { setPage(0) }, [search, direction, hasCompany])

  const rowVirtualizer = useVirtualizer({
    count: profiles.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 44,
    overscan: 10,
  })

  return (
    <div className="flex flex-col h-full">
<div className="flex items-center gap-3 px-4 py-2 border-b border-muted/10 flex-shrink-0">
            <input
              type="text"
              placeholder="Поиск по названию или ИНН..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="flex-1 max-w-xs px-3 py-1.5 text-sm bg-surface border border-muted/20 rounded-lg text-text placeholder:text-muted/50 focus:outline-none focus:ring-1 focus:ring-accent"
            />
            <select
              value={direction}
              onChange={e => setDirection(e.target.value)}
              className="px-2 py-1.5 text-sm bg-surface border border-muted/20 rounded-lg text-text"
            >
              <option value="">Все направления</option>
              <option value="import">Импорт</option>
              <option value="export">Экспорт</option>
            </select>
            <select
              value={hasCompany}
              onChange={e => setHasCompany(e.target.value)}
              className="px-2 py-1.5 text-sm bg-surface border border-muted/20 rounded-lg text-text"
            >
              <option value="">Все</option>
              <option value="yes">В базе</option>
              <option value="no">Не в базе</option>
            </select>
            <select
              value={pageSize}
              onChange={e => { setPageSize(Number(e.target.value)); setPage(0) }}
              className="px-2 py-1.5 text-sm bg-surface border border-muted/20 rounded-lg text-text"
            >
              {PAGE_SIZES.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>

      <div className="flex-1 min-h-0">
        <div
          ref={parentRef}
          className="h-full overflow-auto"
        >
          <div className="sticky top-0 z-10 flex bg-surface border-b border-muted/10" style={{ width: TOTAL_W }}>
            {COL_DEFS.map(col => (
              <div key={col.key} className="flex-shrink-0 px-3 py-2 text-xs font-medium text-muted uppercase tracking-wide" style={{ width: col.w }}>
                {col.label}
              </div>
            ))}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20 text-muted">Загрузка...</div>
          ) : profiles.length === 0 ? (
            <div className="flex items-center justify-center py-20 text-muted">Нет данных</div>
          ) : (
            <div style={{ height: rowVirtualizer.getTotalSize(), width: '100%', position: 'relative' }}>
              {rowVirtualizer.getVirtualItems().map(virtualRow => {
                const profile = profiles[virtualRow.index]
                const isSelected = profile.inn === selectedInn
                return (
                  <div
                    key={profile.inn}
                    ref={rowVirtualizer.measureElement}
                    data-index={virtualRow.index}
                    onClick={() => onSelect(profile)}
                    className={`absolute left-0 flex items-center cursor-pointer hover:bg-accent/5 transition-colors border-b border-muted/5 ${
                      isSelected ? 'bg-accent/10 ring-1 ring-inset ring-accent/30' : ''
                    }`}
                    style={{
                      top: virtualRow.start,
                      height: virtualRow.size,
                      width: TOTAL_W,
                    }}
                  >
                    {COL_DEFS.map(col => (
                      <div key={col.key} className="flex-shrink-0 px-3 py-1 truncate" style={{ width: col.w }}>
                        <CellValue profile={profile} col={col.key} onOpenCRM={onOpenCRM} onCreateInCRM={onCreateInCRM} />
                      </div>
                    ))}
                  </div>
                )
              })}
            </div>
          )}

          <div className="sticky bottom-0 z-10 px-4 py-2 bg-bg/95 backdrop-blur-sm border-t border-muted/10 flex items-center justify-between">
            <span className="text-xs text-muted">
              Страница {page + 1} из {totalPages} • Всего: {total}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="px-3 py-1 text-sm bg-surface border border-muted/20 rounded-lg text-text disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface/80"
              >
                ← Назад
              </button>
              <button
                onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="px-3 py-1 text-sm bg-surface border border-muted/20 rounded-lg text-text disabled:opacity-40 disabled:cursor-not-allowed hover:bg-surface/80"
              >
                Вперёд →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
