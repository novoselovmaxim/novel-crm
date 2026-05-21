import { useState } from 'react'
import api from '../api/client'
import { Company } from '../types'

const statuses = [
  { value: 'new', label: 'Новый', color: 'bg-gray-500' },
  { value: 'not_reached', label: 'Не дозвонился', color: 'bg-orange-500' },
  { value: 'no_answer', label: 'Не отвечает', color: 'bg-red-500' },
  { value: 'callback', label: 'Перезвонить', color: 'bg-blue-500' },
  { value: 'in_progress', label: 'В работе', color: 'bg-yellow-500' },
  { value: 'interested', label: 'Заинтересован', color: 'bg-green-500' },
  { value: 'meeting', label: 'Встреча назначена', color: 'bg-purple-500' },
  { value: 'refused', label: 'Отказ', color: 'bg-gray-600' },
]

export default function CompanyCard({ company, onClose }: { company: Company; onClose: () => void }) {
  const [notes, setNotes] = useState('')
  const [selectedStatus, setSelectedStatus] = useState(company.call_status)
  const [nextCallDate, setNextCallDate] = useState(company.next_call_date || '')

  const handleSaveCall = async () => {
    await api.post(`/companies/${company.id}/call`, {
      call_status: selectedStatus,
      notes,
    })
    setNotes('')
    window.location.reload()
  }

  return (
    <div className="w-[480px] bg-surface border-l border-muted/10 overflow-y-auto">
      <div className="sticky top-0 bg-surface border-b border-muted/10 p-4">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-lg font-bold">{company.name}</h2>
          <button onClick={onClose} className="text-muted hover:text-text">✕</button>
        </div>
        <p className="text-sm text-muted font-mono">ИНН: {company.inn}</p>
        {company.region && <p className="text-sm text-muted">Регион: {company.region}</p>}
        
        <div className="mt-3 flex gap-2">
          {company.phone && (
            <a href={`tel:${company.phone}`} className="px-3 py-1 bg-accent text-white text-sm rounded-lg hover:bg-accent/90">
              {company.phone}
            </a>
          )}
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

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Статус</h3>
        <div className="flex flex-wrap gap-2">
          {statuses.map((s) => (
            <button
              key={s.value}
              onClick={() => setSelectedStatus(s.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
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

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Комментарий к звонку</h3>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full h-24 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Результат звонка..."
        />
      </div>

      <div className="p-4 border-b border-muted/10">
        <h3 className="text-sm font-medium mb-2">Следующий звонок</h3>
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
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+1 день</button>
          <button onClick={() => {
            const d = new Date()
            d.setDate(d.getDate() + 3)
            setNextCallDate(d.toISOString().split('T')[0])
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+3 дня</button>
          <button onClick={() => {
            const d = new Date()
            d.setDate(d.getDate() + 7)
            setNextCallDate(d.toISOString().split('T')[0])
          }} className="px-2 py-1 text-xs bg-surfaceHover rounded hover:bg-muted/20">+неделя</button>
        </div>
      </div>

      <div className="p-4">
        <button
          onClick={handleSaveCall}
          className="w-full py-2 bg-accent hover:bg-accent/90 text-white font-medium rounded-lg transition-colors"
        >
          Сохранить звонок
        </button>
      </div>
    </div>
  )
}
