import { useState, useEffect } from 'react'
import api from '../api/client'
import VEDProfileTable from './VEDProfileTable'
import VEDProfilePanel from './VEDProfilePanel'
import { VedStats } from '../types/ved'

function formatNum(v: number | null): string {
  if (v == null) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} млрд`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн`
  return v.toLocaleString('ru-RU')
}

export default function VEDTab() {
  const [selectedInn, setSelectedInn] = useState<string | null>(null)
  const [stats, setStats] = useState<VedStats | null>(null)

  useEffect(() => {
    api.get('/ved/stats')
      .then(({ data }) => setStats(data))
      .catch(console.error)
  }, [])

  return (
    <div className="flex flex-col h-full">
      {stats && (
        <div className="flex items-center gap-4 px-4 py-2 border-b border-muted/10 flex-shrink-0 overflow-x-auto">
          <StatChip label="Профилей" value={stats.total_profiles} />
          <StatChip label="Деклараций" value={stats.total_declarations} />
          <StatChip label="В базе" value={stats.with_company} color="green" />
          <StatChip label="Не в базе" value={stats.without_company} color="orange" />
          <StatChip label="Импорт" value={stats.import_count} color="blue" />
          <StatChip label="Экспорт" value={stats.export_count} color="green" />
          {stats.total_customs_value != null && (
            <StatChip label="Тамож. стоимость" value={formatNum(stats.total_customs_value)} />
          )}
        </div>
      )}

      <div className="flex-1 min-h-0">
        <VEDProfileTable
          onSelect={p => setSelectedInn(p.inn)}
          selectedInn={selectedInn}
        />
      </div>

      {selectedInn && (
        <VEDProfilePanel
          inn={selectedInn}
          onClose={() => setSelectedInn(null)}
        />
      )}
    </div>
  )
}

function StatChip({ label, value, color }: { label: string; value: string | number; color?: string }) {
  const colorClass = color === 'green' ? 'text-green-400'
    : color === 'orange' ? 'text-orange-400'
    : color === 'blue' ? 'text-blue-400'
    : 'text-text'

  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-surface rounded-lg flex-shrink-0">
      <span className="text-xs text-muted">{label}</span>
      <span className={`text-sm font-medium ${colorClass}`}>{value}</span>
    </div>
  )
}
