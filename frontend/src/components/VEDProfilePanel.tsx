import { useState, useEffect } from 'react'
import api from '../api/client'
import { VedProfileDetail, VedDeclaration } from '../types/ved'

interface Props {
  inn: string | null
  onClose: () => void
  onLinked?: () => void
}

function formatNum(v: number | null): string {
  if (v == null) return '—'
  if (v >= 1e9) return `${(v / 1e9).toFixed(2)} млрд`
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)} млн`
  return v.toLocaleString('ru-RU')
}

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (!value && value !== 0) return null
  return (
    <div className="py-1.5">
      <div className="text-xs text-muted">{label}</div>
      <div className="text-sm text-text">{value}</div>
    </div>
  )
}

function DeclarationRow({ decl, expanded, onToggle }: { decl: VedDeclaration; expanded: boolean; onToggle: () => void }) {
  return (
    <div className="border border-muted/10 rounded-lg overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-3 py-2 bg-surface/50 hover:bg-surface transition-colors text-left"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className={`px-1.5 py-0.5 text-xs rounded ${decl.direction === 'import' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'}`}>
            {decl.direction === 'import' ? 'ИМ' : 'ЭК'}
          </span>
          <span className="text-sm text-text truncate">{decl.company_name || '—'}</span>
          <span className="text-xs text-muted font-mono">{decl.declaration_date || '—'}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted">
          {decl.customs_value != null && <span>{formatNum(decl.customs_value)} ₽</span>}
          {decl.country_to && <span>{decl.country_to}</span>}
          <span className={`transition-transform ${expanded ? 'rotate-90' : ''}`}>▸</span>
        </div>
      </button>
      {expanded && (
        <div className="px-3 py-3 border-t border-muted/10 bg-bg/50">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm">
            <Field label="ИНН" value={decl.inn} />
            <Field label="ТН ВЭД" value={decl.hs_code} />
            <Field label="Страна отправления" value={decl.country_from} />
            <Field label="Страна назначения" value={decl.country_to} />
            <Field label="Таможенная стоимость" value={decl.customs_value != null ? `${formatNum(decl.customs_value)} ₽` : null} />
            <Field label="Фактурная стоимость" value={decl.invoice_value != null ? `${formatNum(decl.invoice_value)}` : null} />
            <Field label="Стат. стоимость (USD)" value={decl.stat_value != null ? formatNum(decl.stat_value) : null} />
            <Field label="Инкотермс" value={decl.incoterms} />
            <Field label="Вес нетто" value={decl.net_weight != null ? `${formatNum(decl.net_weight)} кг` : null} />
            <Field label="Вес брутто" value={decl.gross_weight != null ? `${formatNum(decl.gross_weight)} кг` : null} />
            <Field label="Источник" value={decl.source_file} />
            <Field label="Дата декларации" value={decl.declaration_date} />
          </div>
          {decl.row_data && Object.keys(decl.row_data).length > 0 && (
            <details className="mt-3">
              <summary className="text-xs text-muted cursor-pointer hover:text-text">Все поля ГТД</summary>
              <div className="mt-2 max-h-60 overflow-auto text-xs">
                <table className="w-full">
                  <tbody>
                    {Object.entries(decl.row_data).map(([k, v]) => (
                      <tr key={k} className="border-b border-muted/5">
                        <td className="py-1 pr-3 text-muted whitespace-nowrap align-top">{k}</td>
                        <td className="py-1 text-text break-words">{v != null ? String(v) : '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

export default function VEDProfilePanel({ inn, onClose }: Props) {
  const [profile, setProfile] = useState<VedProfileDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [expandedDecl, setExpandedDecl] = useState<string | null>(null)

  useEffect(() => {
    if (!inn) return
    setLoading(true)
    api.get(`/ved/profiles/${inn}`)
      .then(({ data }) => setProfile(data))
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [inn])

  if (!inn) return null

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative w-full max-w-2xl bg-bg border-l border-muted/10 flex flex-col overflow-hidden animate-slide-in">
        <div className="flex items-center justify-between px-4 py-3 border-b border-muted/10 flex-shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <h2 className="text-lg font-semibold text-text truncate">{profile?.company_name || inn}</h2>
            {profile?.company_id && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400 flex-shrink-0">
                В базе CRM
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-muted hover:text-text text-xl leading-none">&times;</button>
        </div>

        {loading ? (
          <div className="flex-1 flex items-center justify-center text-muted">Загрузка...</div>
        ) : !profile ? (
          <div className="flex-1 flex items-center justify-center text-muted">Профиль не найден</div>
        ) : (
          <div className="flex-1 overflow-auto">
            <div className="px-4 py-3 border-b border-muted/10">
              <div className="flex items-center gap-2 mb-2">
                {profile.directions?.map(d => (
                  <span key={d} className={`px-2 py-0.5 text-xs rounded ${d === 'import' ? 'bg-blue-500/20 text-blue-400' : 'bg-green-500/20 text-green-400'}`}>
                    {d === 'import' ? 'Импорт' : 'Экспорт'}
                  </span>
                ))}
                <span className="text-xs text-muted">{profile.total_declarations} деклараций</span>
              </div>
              <div className="text-xs text-muted font-mono">ИНН: {profile.inn}</div>
            </div>

            <div className="px-4 py-3 border-b border-muted/10">
              <h3 className="text-sm font-medium text-text mb-2">Контакты и данные</h3>
              <div className="grid grid-cols-2 gap-x-6">
                <Field label="Телефон" value={profile.contact_phone} />
                <Field label="Email" value={profile.contact_email} />
                <Field label="Сайт" value={profile.website} />
                <Field label="Руководитель" value={profile.director} />
                <Field label="Адрес" value={profile.address} />
                <Field label="Регион" value={profile.region} />
                <Field label="ОГРН" value={profile.ogrn} />
                <Field label="Деятельность" value={profile.activity} />
              </div>
            </div>

            <div className="px-4 py-3 border-b border-muted/10">
              <h3 className="text-sm font-medium text-text mb-2">Финансы и объёмы</h3>
              <div className="grid grid-cols-2 gap-x-6">
                <Field label="Тамож. стоимость (суммарно)" value={profile.total_customs_value != null ? `${formatNum(profile.total_customs_value)} ₽` : null} />
                <Field label="Стат. стоимость (суммарно)" value={profile.total_stat_value != null ? `${formatNum(profile.total_stat_value)} USD` : null} />
                <Field label="Вес нетто (суммарно)" value={profile.total_net_weight != null ? `${formatNum(profile.total_net_weight)} кг` : null} />
                <Field label="Выручка" value={profile.revenue != null ? `${formatNum(profile.revenue)} ₽` : null} />
                <Field label="Сотрудники" value={profile.employees} />
              </div>
            </div>

            <div className="px-4 py-3 border-b border-muted/10">
              <h3 className="text-sm font-medium text-text mb-2">География и товары</h3>
              <div className="grid grid-cols-2 gap-x-6">
                <div className="py-1.5">
                  <div className="text-xs text-muted mb-1">Страны назначения</div>
                  <div className="flex flex-wrap gap-1">
                    {profile.destination_countries?.map(c => (
                      <span key={c} className="px-1.5 py-0.5 text-xs bg-surface rounded text-text">{c}</span>
                    ))}
                  </div>
                </div>
                <div className="py-1.5">
                  <div className="text-xs text-muted mb-1">Источники данных</div>
                  <div className="flex flex-wrap gap-1">
                    {profile.source_files?.map(f => (
                      <span key={f} className="px-1.5 py-0.5 text-xs bg-surface rounded text-text truncate max-w-[200px]" title={f}>{f}</span>
                    ))}
                  </div>
                </div>
              </div>
              {profile.hs_codes && profile.hs_codes.length > 0 && (
                <div className="mt-2 py-1.5">
                  <div className="text-xs text-muted mb-1">Коды ТН ВЭД</div>
                  <div className="flex flex-wrap gap-1">
                    {profile.hs_codes.map(c => (
                      <span key={c} className="px-1.5 py-0.5 text-xs bg-surface rounded text-text font-mono">{c}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="px-4 py-3">
              <h3 className="text-sm font-medium text-text mb-3">Декларации ({profile.declarations.length})</h3>
              <div className="space-y-2">
                {profile.declarations.map(decl => (
                  <DeclarationRow
                    key={decl.id}
                    decl={decl}
                    expanded={expandedDecl === decl.id}
                    onToggle={() => setExpandedDecl(expandedDecl === decl.id ? null : decl.id)}
                  />
                ))}
                {profile.declarations.length === 0 && (
                  <div className="text-sm text-muted py-4 text-center">Нет деклараций</div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
