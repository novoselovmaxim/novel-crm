import { useState } from 'react'
import api from '../api/client'
import { Company } from '../types'

const STATUSES = [
  { value: 'new', label: 'Новый', color: 'bg-gray-500' },
  { value: 'not_reached', label: 'Не дозвонился', color: 'bg-orange-500' },
  { value: 'no_answer', label: 'Не отвечает', color: 'bg-red-500' },
  { value: 'callback', label: 'Перезвонить', color: 'bg-blue-500' },
  { value: 'in_progress', label: 'В работе', color: 'bg-yellow-500' },
  { value: 'interested', label: 'Заинтересован', color: 'bg-green-500' },
  { value: 'meeting', label: 'Встреча назначена', color: 'bg-purple-500' },
  { value: 'refused', label: 'Отказ', color: 'bg-gray-600' },
]

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null
  return (
    <div className="py-1.5 border-b border-muted/5">
      <span className="text-xs text-muted">{label}</span>
      <p className="text-sm mt-0.5">{value}</p>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p-4 border-b border-muted/10">
      <h3 className="text-sm font-medium mb-3 text-accent">{title}</h3>
      {children}
    </div>
  )
}

export default function CompanyCard({ company, onClose }: { company: Company; onClose: () => void }) {
  const [notes, setNotes] = useState('')
  const [selectedStatus, setSelectedStatus] = useState(company.call_status)
  const [nextCallDate, setNextCallDate] = useState(company.next_call_date || '')
  const [saving, setSaving] = useState(false)

  const handleSaveCall = async () => {
    setSaving(true)
    try {
      await api.post(`/companies/${company.id}/call`, {
        call_status: selectedStatus,
        notes,
        next_call_date: nextCallDate || null,
      })
      setNotes('')
      window.location.reload()
    } finally {
      setSaving(false)
    }
  }

  const phones = company.phone?.split(',').map(p => p.trim()).filter(Boolean) || []

  return (
    <div className="w-[560px] bg-surface border-l border-muted/10 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-surface border-b border-muted/10 p-4 z-10">
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-lg font-bold leading-tight flex-1 mr-2">{company.name}</h2>
          <button onClick={onClose} className="text-muted hover:text-text shrink-0">✕</button>
        </div>
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
          <span className="font-mono">ИНН: {company.inn}</span>
          {company.kpp && <span>КПП: {company.kpp}</span>}
          {company.region && <span>{company.region}</span>}
        </div>
        {company.director && (
          <p className="text-sm mt-1">
            <span className="text-muted">Руководитель: </span>
            <span className="font-medium">{company.director}</span>
            {company.director_title && <span className="text-muted"> ({company.director_title})</span>}
          </p>
        )}
        {company.contact_person && (
          <p className="text-sm">
            <span className="text-muted">Контакт: </span>
            <span className="font-medium">{company.contact_person}</span>
          </p>
        )}
        {company.fin_director && (
          <p className="text-sm">
            <span className="text-muted">Фин. директор: </span>
            <span className="font-medium">{company.fin_director}</span>
          </p>
        )}
        {phones.length > 0 && (
          <div className="flex flex-wrap gap-2 mt-2">
            {phones.map((p, i) => (
              <a key={i} href={`tel:${p}`} className="px-3 py-1 bg-accent text-white text-sm rounded-lg hover:bg-accent/90">
                {p}
              </a>
            ))}
          </div>
        )}
        <div className="flex gap-2 mt-2">
          {company.email && (
            <a href={`mailto:${company.email}`} className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
              Email
            </a>
          )}
          {company.website && (
            <a href={company.website} target="_blank" rel="noopener" className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
              Сайт
            </a>
          )}
        </div>
      </div>

      {/* Manager Work Zone */}
      <div className="bg-surfaceHover/50">
        <Section title="Звонок">
          <div className="mb-3">
            <span className="text-xs text-muted mb-2 block">Статус</span>
            <div className="flex flex-wrap gap-1.5">
              {STATUSES.map((s) => (
                <button
                  key={s.value}
                  onClick={() => setSelectedStatus(s.value)}
                  className={`px-2.5 py-1 text-xs font-medium rounded-lg transition-colors ${
                    selectedStatus === s.value
                      ? `${s.color} text-white`
                      : 'bg-bg text-muted hover:text-text'
                  }`}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full h-20 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="Результат звонка..."
          />
          <div className="mt-3">
            <span className="text-xs text-muted mb-1 block">Перезвонить</span>
            <input
              type="date"
              value={nextCallDate}
              onChange={(e) => setNextCallDate(e.target.value)}
              className="w-full px-3 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent"
            />
            <div className="flex gap-2 mt-2">
              <button onClick={() => {
                const d = new Date()
                d.setDate(d.getDate() + 1)
                setNextCallDate(d.toISOString().split('T')[0])
              }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+1 день</button>
              <button onClick={() => {
                const d = new Date()
                d.setDate(d.getDate() + 3)
                setNextCallDate(d.toISOString().split('T')[0])
              }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+3 дня</button>
              <button onClick={() => {
                const d = new Date()
                d.setDate(d.getDate() + 7)
                setNextCallDate(d.toISOString().split('T')[0])
              }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+неделя</button>
            </div>
          </div>
          <button
            onClick={handleSaveCall}
            disabled={saving}
            className="w-full py-2 mt-3 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
          >
            {saving ? 'Сохранение...' : 'Сохранить звонок'}
          </button>
        </Section>
      </div>

      {/* Company Info */}
      <Section title="Профиль деятельности">
        <Field label="Основной вид деятельности" value={company.activity_main} />
        <Field label="Код ОКВЭД" value={company.activity_code} />
        <Field label="Доп. деятельность" value={company.activity_other} />
        <Field label="Отрасль / Ниша" value={company.niche} />
        <Field label="Предмет снабжения" value={company.supply_subject} />
        <Field label="Орг. форма" value={company.org_form} />
        <Field label="Сегмент" value={company.segment} />
        <Field label="Размер" value={company.size} />
        <Field label="Приоритет" value={company.priority} />
        <Field label="МСП" value={company.msp} />
      </Section>

      <Section title="Финансы">
        <Field label="Выручка" value={company.revenue != null ? `${company.revenue.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Прибыль" value={company.profit != null ? `${company.profit.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Уставный капитал" value={company.capital != null ? `${company.capital.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Численность сотрудников" value={company.employees != null ? `${company.employees} чел.` : null} />
        <Field label="Импортный оборот" value={company.import_turnover} />
        <Field label="Экспортный оборот" value={company.export_turnover} />
        <Field label="Подтверждённый импорт" value={company.import_confirmed} />
        <Field label="Валютные платежи" value={company.foreign_payments} />
      </Section>

      <Section title="Реквизиты">
        <Field label="ОГРН" value={company.ogrn} />
        <Field label="Дата регистрации" value={company.reg_date} />
        <Field label="Налоговая" value={company.tax_office} />
        <Field label="Адрес" value={company.address} />
        <Field label="Гражданство" value={company.citizenship} />
        <Field label="ИНН директора" value={company.director_inn} />
        <Field label="Филиалы" value={company.branches} />
        <Field label="LinkedIn" value={company.linkedin} />
        <Field label="Focus-ссылка" value={company.focus_link} />
        <Field label="Источник" value={company.source_orig} />
      </Section>

      <Section title="Дополнительно">
        <Field label="Арбитраж" value={company.arbitrage} />
        <Field label="Лицензии" value={company.licenses} />
        <Field label="Реестры" value={company.registries} />
        <Field label="Комментарий" value={company.comment_static} />
      </Section>

      <div className="p-4 text-xs text-muted space-y-1">
        <p>Попыток звонков: {company.call_count}</p>
        {company.last_called_at && <p>Последний звонок: {new Date(company.last_called_at).toLocaleString('ru-RU')}</p>}
        <p>Создана: {new Date(company.created_at!).toLocaleDateString('ru-RU')}</p>
      </div>
    </div>
  )
}
