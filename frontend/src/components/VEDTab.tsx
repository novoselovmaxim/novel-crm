import { useState, useEffect } from 'react'
import api from '../api/client'
import VEDProfileTable from './VEDProfileTable'
import VEDProfilePanel from './VEDProfilePanel'
import { VedStats, VedProfile, VedProfileDetail } from '../types/ved'

interface Props {
  initialInn?: string
  onOpenInCRM?: (companyId: string) => void
  onCreateInCRM?: (profile: VedProfile) => Promise<string | null>
}

function formatNum(v: number | null): string {
  if (v == null) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(1)} млрд`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн`
  return v.toLocaleString('ru-RU')
}

export default function VEDTab({ initialInn, onOpenInCRM, onCreateInCRM }: Props) {
  const [selectedInn, setSelectedInn] = useState<string | null>(initialInn || null)
  const [stats, setStats] = useState<VedStats | null>(null)

  useEffect(() => {
    api.get('/ved/stats')
      .then(({ data }) => setStats(data))
      .catch(console.error)
  }, [])

  useEffect(() => {
    if (initialInn) {
      setSelectedInn(initialInn)
    }
  }, [initialInn])

  const handleOpenCRM = (profile: VedProfile) => {
    if (profile.company_id && onOpenInCRM) {
      onOpenInCRM(profile.company_id)
    }
  }

  const handleCreateInCRM = async (profile: VedProfile) => {
    if (onCreateInCRM) {
      const newCompanyId = await onCreateInCRM(profile)
      if (newCompanyId && onOpenInCRM) {
        onOpenInCRM(newCompanyId)
      }
    } else {
      try {
        const { data } = await api.post('/companies', {
          inn: profile.inn,
          name: profile.company_name,
          region: profile.region,
          address: profile.address,
          phone: profile.contact_phone,
          email: profile.contact_email,
          website: profile.website,
          director: profile.director,
          ogrn: profile.ogrn,
          activity_main: profile.activity,
          revenue: profile.revenue,
          employees: profile.employees,
          source_orig: profile.source_files?.join(', '),
          call_status: 'new',
          pipeline_stage: 'new',
        })
        api.get('/ved/stats').then(({ data }) => setStats(data))
        if (onOpenInCRM) {
          onOpenInCRM(data.id)
        }
      } catch (e) {
        console.error('Failed to create company', e)
        alert('Ошибка при создании компании')
      }
    }
  }

  // Wrapper functions for VEDProfilePanel with correct signatures
  const handleOpenCRMFromPanel = (companyId: string) => {
    if (onOpenInCRM) {
      onOpenInCRM(companyId)
    }
  }

  const handleCreateInCRMFromPanel = async (profile: VedProfileDetail) => {
    if (onCreateInCRM) {
      return onCreateInCRM(profile)
    }
    try {
      const { data } = await api.post('/companies', {
        inn: profile.inn,
        name: profile.company_name,
        region: profile.region,
        address: profile.address,
        phone: profile.contact_phone,
        email: profile.contact_email,
        website: profile.website,
        director: profile.director,
        ogrn: profile.ogrn,
        activity_main: profile.activity,
        revenue: profile.revenue,
        employees: profile.employees,
        source_orig: profile.source_files?.join(', '),
        call_status: 'new',
        pipeline_stage: 'new',
      })
      api.get('/ved/stats').then(({ data }) => setStats(data))
      return data.id
    } catch (e) {
      console.error('Failed to create company', e)
      alert('Ошибка при создании компании')
      return null
    }
  }

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
          onOpenCRM={handleOpenCRM}
          onCreateInCRM={handleCreateInCRM}
          selectedInn={selectedInn}
        />
      </div>

      {selectedInn && (
        <VEDProfilePanel
          inn={selectedInn}
          onClose={() => setSelectedInn(null)}
          onOpenInCRM={handleOpenCRMFromPanel}
          onCreateInCRM={handleCreateInCRMFromPanel}
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
