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
    <div className="py-2 border-b border-muted/5">
      <span className="text-xs text-muted">{label}</span>
      <p className="text-sm mt-0.5 break-words">{value}</p>
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

  const [meetingDate, setMeetingDate] = useState('')
  const [meetingTime, setMeetingTime] = useState('')
  const [meetingNotes, setMeetingNotes] = useState('')
  const [scheduling, setScheduling] = useState(false)

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

  const handleScheduleMeeting = async () => {
    if (!meetingDate || !meetingTime) return
    setScheduling(true)
    try {
      await api.post(`/companies/${company.id}/meeting`, {
        meeting_date: meetingDate,
        meeting_time: meetingTime,
        notes: meetingNotes,
      })
      setMeetingDate('')
      setMeetingTime('')
      setMeetingNotes('')
      window.location.reload()
    } finally {
      setScheduling(false)
    }
  }

  const phones = company.phone?.split(/[,;]+/).map(p => p.trim()).filter(Boolean) || []
  const emails = [company.email].filter(Boolean)
  const website = company.website || company.focus_link
  const displayName = company.name

  return (
    <div className="w-[600px] bg-surface border-l border-muted/10 overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-surface border-b border-muted/10 p-4 z-10">
        <div className="flex items-start justify-between mb-3">
          <h2 className="text-lg font-bold leading-tight flex-1 mr-2">{displayName}</h2>
          <button onClick={onClose} className="text-muted hover:text-text shrink-0 text-xl">✕</button>
        </div>

        <div className="space-y-1.5 text-sm">
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-muted">
            <span className="font-mono">ИНН: {company.inn}</span>
            {company.kpp && <span>КПП: {company.kpp}</span>}
          </div>
          {company.region && <p><span className="text-muted">Регион: </span><span>{company.region}</span></p>}
          {company.activity_main && <p><span className="text-muted">Деятельность: </span><span>{company.activity_main}</span></p>}

          {phones.length > 0 && (
            <div className="flex flex-wrap gap-2 pt-1">
              {phones.map((p, i) => (
                <a key={i} href={`tel:${p}`} className="px-3 py-1 bg-accent text-white text-sm rounded-lg hover:bg-accent/90 shrink-0">
                  {p}
                </a>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-2 pt-1">
            {website && (
              <a href={website.startsWith('http') ? website : `https://${website}`} target="_blank" rel="noopener" className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
                Сайт
              </a>
            )}
            {emails.map((e, i) => (
              <a key={i} href={`mailto:${e}`} className="px-3 py-1 bg-surfaceHover text-sm rounded-lg hover:bg-muted/20">
                Email
              </a>
            ))}
          </div>

          {company.address && <p className="text-muted text-xs pt-1">{company.address}</p>}
        </div>
      </div>

      {/* Call Section */}
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
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 1); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+1 день</button>
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 3); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+3 дня</button>
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 7); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1 text-xs bg-bg rounded hover:bg-muted/20">+неделя</button>
          </div>
        </div>
        <button onClick={handleSaveCall} disabled={saving} className="w-full py-2 mt-3 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white font-medium rounded-lg transition-colors">
          {saving ? 'Сохранение...' : 'Сохранить звонок'}
        </button>
      </Section>

      {/* Meeting Section */}
      <Section title="Назначить встречу">
        <div className="flex gap-3">
          <div className="flex-1">
            <span className="text-xs text-muted mb-1 block">Дата</span>
            <input type="date" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} className="w-full px-3 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent" />
          </div>
          <div className="w-28">
            <span className="text-xs text-muted mb-1 block">Время</span>
            <input type="time" value={meetingTime} onChange={(e) => setMeetingTime(e.target.value)} className="w-full px-3 py-2 bg-bg border border-muted/20 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent" />
          </div>
        </div>
        <textarea
          value={meetingNotes}
          onChange={(e) => setMeetingNotes(e.target.value)}
          className="w-full h-16 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent mt-3"
          placeholder="Место, тема встречи..."
        />
        <button onClick={handleScheduleMeeting} disabled={!meetingDate || !meetingTime || scheduling} className="w-full py-2 mt-3 bg-purple-600 hover:bg-purple-600/90 disabled:opacity-50 text-white font-medium rounded-lg transition-colors">
          {scheduling ? 'Назначение...' : 'Назначить встречу'}
        </button>
      </Section>

      {/* Director / LPR */}
      {(company.director || company.director_title || company.contact_person || company.fin_director || company.director_inn) && (
        <Section title="Руководство / ЛПР">
          {company.director && <Field label="Руководитель" value={company.director} />}
          {company.director_title && <Field label="Должность" value={company.director_title} />}
          {company.contact_person && <Field label="Контактное лицо" value={company.contact_person} />}
          {company.fin_director && <Field label="Фин. директор" value={company.fin_director} />}
          {company.director_inn && <Field label="ИНН директора" value={company.director_inn} />}
        </Section>
      )}

      {/* Activity */}
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

      {/* Finance */}
      <Section title="Финансы">
        <Field label="Выручка" value={company.revenue != null ? `${company.revenue.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Прибыль" value={company.profit != null ? `${company.profit.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Уставный капитал" value={company.capital != null ? `${company.capital.toLocaleString('ru-RU')} ₽` : null} />
        <Field label="Численность сотрудников" value={company.employees != null ? `${company.employees} чел.` : null} />
        <Field label="Обороты импорта" value={company.import_turnover} />
        <Field label="Обороты экспорта" value={company.export_turnover} />
        <Field label="Подтверждённый импорт" value={company.import_confirmed} />
        <Field label="Валютные платежи" value={company.foreign_payments} />
      </Section>

      {/* Details */}
      <Section title="Реквизиты и детали">
        <Field label="ОГРН" value={company.ogrn} />
        <Field label="КПП" value={company.kpp} />
        <Field label="Дата регистрации" value={company.reg_date} />
        <Field label="Налоговая" value={company.tax_office} />
        <Field label="Адрес" value={company.address} />
        <Field label="Гражданство" value={company.citizenship} />
        <Field label="Филиалы" value={company.branches} />
        <Field label="LinkedIn" value={company.linkedin} />
        <Field label="Focus-ссылка" value={company.focus_link} />
        <Field label="Источник" value={company.source_orig} />
        <Field label="Сайт" value={company.website} />
        <Field label="Email" value={company.email} />
        <Field label="Телефон" value={company.phone} />
      </Section>

      {/* Additional */}
      <Section title="Дополнительно">
        <Field label="Арбитраж" value={company.arbitrage} />
        <Field label="Лицензии" value={company.licenses} />
        <Field label="Реестры" value={company.registries} />
        <Field label="Комментарий" value={company.comment_static} />
      </Section>

      {/* Meta */}
      <div className="p-4 text-xs text-muted space-y-1">
        <p>Попыток звонков: {company.call_count}</p>
        {company.last_called_at && <p>Последний звонок: {new Date(company.last_called_at).toLocaleString('ru-RU')}</p>}
        {company.created_at && <p>Создана: {new Date(company.created_at).toLocaleDateString('ru-RU')}</p>}
      </div>
    </div>
  )
}
