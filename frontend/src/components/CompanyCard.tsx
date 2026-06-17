import { useState, useEffect, useRef } from 'react'
import api from '../api/client'
import { Company, User, Comment, CallLog } from '../types'
import { useAuth } from '../store/auth'
import CalendarPicker from './CalendarPicker'
import CalendarModal from './CalendarModal'
import { getClientTimeInfo } from '../utils/timezone'

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

function Field({ label, value, field, companyId, rawValue, onUpdate, onError, highlight }: {
  label: string
  value: string | null | undefined
  field?: string
  companyId?: string
  rawValue?: string
  onUpdate?: (field: string, value: string) => void
  onError?: (msg: string) => void
  highlight?: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [editVal, setEditVal] = useState('')

  if (!value && !field) return null

  const displayValue = value || '—'
  const canEdit = field && companyId

  const startEdit = () => {
    if (!canEdit) return
    setEditVal(rawValue ?? value ?? '')
    setEditing(true)
  }

  const savingRef = useRef(false)
  const save = async () => {
    if (!field || !companyId) return
    if (savingRef.current) return
    savingRef.current = true
    setEditing(false)
    if (editVal === (rawValue ?? value ?? '')) { savingRef.current = false; return }
    if (editVal === '' && value === null) { savingRef.current = false; return }
    try {
      await api.patch(`/companies/${companyId}`, { [field]: editVal || null })
      onUpdate?.(field, editVal)
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Не удалось сохранить'
      console.error('Save error:', msg, e)
      onError?.(msg)
    } finally {
      savingRef.current = false
    }
  }

  const cancel = () => {
    setEditing(false)
    setEditVal(rawValue ?? value ?? '')
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      e.stopPropagation()
      save()
    }
    if (e.key === 'Escape') {
      cancel()
    }
  }

  if (editing) {
    return (
      <div className={`flex justify-between py-1.5 border-b border-muted/5 gap-4 ${highlight ? 'border-l-2 border-accent/40 pl-2' : ''}`}>
        <span className={`text-xs shrink-0 w-40 ${highlight ? 'text-accent' : 'text-muted'}`}>{label}</span>
        <input
          autoFocus
          value={editVal}
          onChange={(e) => setEditVal(e.target.value)}
          onBlur={save}
          onKeyDown={handleKeyDown}
          className="w-full max-w-[280px] px-2 py-0.5 bg-bg border border-accent rounded text-sm text-right focus:outline-none"
        />
      </div>
    )
  }

  return (
    <div className={`flex justify-between py-1.5 border-b border-muted/5 gap-4 group ${highlight ? 'border-l-2 border-accent/40 pl-2' : ''}`} onClick={startEdit}>
      <span className={`text-xs shrink-0 w-40 ${highlight ? 'text-accent' : 'text-muted'}`}>{label}</span>
      <span className={`text-sm text-right break-words ${canEdit ? 'cursor-pointer hover:text-accent group-hover:bg-bg/50 px-1 -mx-1 rounded transition-colors' : ''}`}>
        {displayValue}
        {canEdit && <span className="ml-1.5 text-[10px] text-muted/30 group-hover:text-muted/60">✎</span>}
      </span>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="px-4 py-3 border-b border-muted/10">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-accent mb-2">{title}</h3>
      {children}
    </div>
  )
}

function formatMoney(val: number | null | undefined) {
  if (val === null || val === undefined) return '—'
  if (val >= 1e9) return `${(val / 1e9).toFixed(1)} млрд`
  if (val >= 1e6) return `${(val / 1e6).toFixed(0)} млн`
  if (val >= 1e3) return `${(val / 1e3).toFixed(0)} тыс`
  return val.toLocaleString('ru-RU')
}

function TimeZoneBlock({ region }: { region: string }) {
  const info = getClientTimeInfo(region)
  const colors = { working: 'text-success', border: 'text-yellow-400', off: 'text-error' }
  const labels = { working: 'рабочее', border: 'граничное', off: 'нерабочее' }
  return (
    <div className="text-xs text-muted mb-2">
      UTC{info.utcOffset >= 0 ? '+' : ''}{info.utcOffset} · {info.currentTime} <span className={colors[info.period]}>({labels[info.period]})</span>
    </div>
  )
}

function formatNumericString(val: string | null | undefined) {
  if (!val || val === '') return '—'
  // Try to parse as number
  const num = parseFloat(val)
  if (isNaN(num)) return val // Return as-is if not a number
  
  // Format like formatMoney but without the currency symbol
  if (num >= 1e9) return `${(num / 1e9).toFixed(1)} млрд`
  if (num >= 1e6) return `${(num / 1e6).toFixed(0)} млн`
  if (num >= 1e3) return `${(num / 1e3).toFixed(0)} тыс`
  return num.toLocaleString('ru-RU')
}

export default function CompanyCard({ company: initialCompany, onClose, onAssign, onNavigateToCompany }: { company: Company; onClose: () => void; onAssign?: (id: string) => void; onNavigateToCompany?: (id: string) => void }) {
  const [company, setCompany] = useState(initialCompany)
  const [notes, setNotes] = useState('')
  const [selectedStatus, setSelectedStatus] = useState(company.call_status)
  const [nextCallDate, setNextCallDate] = useState(company.next_call_date || '')
  const [saving, setSaving] = useState(false)
  const [assignedTo, setAssignedTo] = useState(company.assigned_to || '')
  const [managers, setManagers] = useState<User[]>([])
  const currentUser = useAuth(s => s.user)
  const isAdminOrLead = currentUser?.role === 'admin' || currentUser?.role === 'lead'

  useEffect(() => {
    setAssignedTo(company.assigned_to || '')
  }, [company.assigned_to])

  useEffect(() => {
    setSelectedStatus(company.call_status)
  }, [company.call_status])

  useEffect(() => {
    if (isAdminOrLead) {
      api.get('/auth/managers').then(({ data }) => setManagers(data))
    }
  }, [])

  const [meetingDate, setMeetingDate] = useState('')
  const [meetingTime, setMeetingTime] = useState('')
  const [meetingNotes, setMeetingNotes] = useState('')
  const [scheduling, setScheduling] = useState(false)
  const [showCalendarBook, setShowCalendarBook] = useState(false)
  const [bookedMeetingId, setBookedMeetingId] = useState<string | null>(null)
  const [savingMeeting, setSavingMeeting] = useState(false)
  const [existingMeeting, setExistingMeeting] = useState<any>(null)
  const [meetingLoading, setMeetingLoading] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [sourceData, setSourceData] = useState<any[]>([])
  const [comments, setComments] = useState<Comment[]>([])
  const [commentText, setCommentText] = useState('')
  const [sendingComment, setSendingComment] = useState(false)
  const [callLogs, setCallLogs] = useState<CallLog[]>([])
  const [refreshKey, setRefreshKey] = useState(0)

  useEffect(() => {
    api.get(`/import/data`, { params: { company_id: company.id } }).then(({ data }) => {
      const grouped: Record<string, { source_id: string; source_filename: string; uploaded_at: string; entries: typeof data }> = {}
      for (const item of data) {
        if (!grouped[item.source_id]) {
          grouped[item.source_id] = { source_id: item.source_id, source_filename: item.source_filename, uploaded_at: item.uploaded_at, entries: [] }
        }
        grouped[item.source_id].entries.push(item)
      }
      setSourceData(Object.values(grouped))
    }).catch(() => setSourceData([]))
  }, [company.id])

  useEffect(() => {
    api.get(`/companies/${company.id}/comments`).then(({ data }) => setComments(data)).catch(() => setComments([]))
  }, [company.id, refreshKey])

  useEffect(() => {
    api.get(`/companies/${company.id}/calls`).then(({ data }) => setCallLogs(data)).catch(() => setCallLogs([]))
  }, [company.id, refreshKey])

  const sendComment = async () => {
    if (!commentText.trim() || sendingComment) return
    setSendingComment(true)
    try {
      const { data } = await api.post(`/companies/${company.id}/comments`, { text: commentText.trim() })
      setComments(prev => [...prev, data])
      setCommentText('')
    } catch {
      // ignore
    } finally {
      setSendingComment(false)
    }
  }

  const NUM_FIELDS = new Set(['revenue', 'profit', 'employees', 'capital', 'balance'])
  const [saveError, setSaveError] = useState('')
  const [cpError, setCpError] = useState('')

  const handleFieldUpdate = (field: string, val: string) => {
    const parsed = NUM_FIELDS.has(field) ? (val ? parseInt(val.replace(/\s/g, ''), 10) : null) : val
    setCompany(prev => ({ ...prev, [field]: parsed }))
  }

  useEffect(() => {
    if (company.call_status === 'meeting') {
      setMeetingLoading(true)
      api.get(`/availability/meetings/by-company/${company.id}`)
        .then(({ data }) => setExistingMeeting(data))
        .catch(() => setExistingMeeting(null))
        .finally(() => setMeetingLoading(false))
    }
  }, [company.id, company.call_status])

  const handleSaveCall = async (status?: string) => {
    setSaving(true)
    try {
      await api.post(`/companies/${company.id}/call`, {
        call_status: status || selectedStatus,
        notes,
        next_call_date: nextCallDate || null,
      })
      if (notes.trim()) {
        const { data } = await api.post(`/companies/${company.id}/comments`, { text: notes.trim() })
        setComments(prev => [...prev, data])
      }
      setNotes('')
      setCompany(prev => ({
        ...prev,
        call_status: status || selectedStatus,
        call_count: (prev.call_count || 0) + 1,
      }))
      setRefreshKey(k => k + 1)
      setSaving(false)
    } catch {
      setSaving(false)
    }
  }

  const handleSaveMeetingNotes = async () => {
    if (!bookedMeetingId) return
    setSavingMeeting(true)
    try {
      await api.patch(`/availability/meetings/${bookedMeetingId}`, { notes: meetingNotes })
      window.location.reload()
    } finally {
      setSavingMeeting(false)
    }
  }

  const handleBookedSlot = (result: { date: string; hour: number; meeting_id: string }) => {
    setBookedMeetingId(result.meeting_id)
    setMeetingDate(result.date)
    setMeetingTime(`${String(result.hour).padStart(2, '0')}:00`)
  }

  const handleCancelMeeting = async () => {
    if (!existingMeeting) return
    setCancelling(true)
    try {
      await api.delete(`/availability/meetings/${existingMeeting.id}`)
      window.location.reload()
    } finally {
      setCancelling(false)
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

  return (
    <div className="w-[520px] bg-surface flex flex-col h-full">
      {/* Header - sticky */}
      <div className="sticky top-0 bg-surface z-10 p-4 border-b border-muted/10">
        <div className="flex items-start justify-between mb-2">
          <h2 className="text-base font-bold leading-tight flex-1 mr-2">{company.name}</h2>
          <button onClick={onClose} className="text-muted hover:text-text shrink-0 text-lg">✕</button>
        </div>
        <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-sm text-muted mb-2">
          <span className="font-mono">ИНН {company.inn}</span>
          {company.kpp && <span>КПП {company.kpp}</span>}
        </div>
        {company.region && <p className="text-sm text-muted mb-1">{company.region}</p>}
        {company.region && <TimeZoneBlock region={company.region} />}
        {company.activity_main && <p className="text-sm text-muted mb-2 line-clamp-2">{company.activity_main}</p>}

        {phones.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-2">
            {phones.map((p, i) => (
              <a key={i} href={`tel:${p}`} className="px-2.5 py-1 bg-accent text-white text-xs rounded-md hover:bg-accent/90">
                {p}
              </a>
            ))}
          </div>
        )}

        <div className="flex flex-wrap gap-1.5">
          {website && (
            <a href={website.startsWith('http') ? website : `https://${website}`} target="_blank" rel="noopener" className="px-2.5 py-1 bg-surfaceHover text-xs rounded-md hover:bg-muted/20">
              Сайт
            </a>
          )}
          {emails.map((e, i) => (
            <a key={i} href={`mailto:${e}`} className="px-2.5 py-1 bg-surfaceHover text-xs rounded-md hover:bg-muted/20">
              Email
            </a>
          ))}
        </div>
        {company.address && <p className="text-xs text-muted mt-2 line-clamp-2">{company.address}</p>}
        {isAdminOrLead && (
          <div className="mt-2 flex items-center gap-2">
            <span className="text-xs text-muted shrink-0">Менеджер:</span>
            <select
              value={assignedTo}
              onChange={async (e) => {
                const val = e.target.value
                setAssignedTo(val)
                try {
                  await api.patch(`/companies/${company.id}/assign`, { user_id: val || null })
                  onAssign?.(val)
                } catch {
                  setAssignedTo(company.assigned_to || '')
                }
              }}
              className="flex-1 px-2 py-1 bg-bg border border-muted/20 rounded text-xs focus:outline-none focus:ring-1 focus:ring-accent cursor-pointer"
            >
              <option value="">—</option>
              {managers.map(m => (
                <option key={m.id} value={m.id}>{m.name || m.email}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Call */}
        <Section title="Звонок">
          <div className="flex flex-wrap gap-1.5 mb-3">
            {STATUSES.map((s) => (
              <button
                key={s.value}
                onClick={() => setSelectedStatus(s.value)}
                disabled={saving}
                className={`px-2 py-1 text-xs font-medium rounded-md transition-colors ${
                  selectedStatus === s.value ? `${s.color} text-white` : 'bg-bg text-muted hover:text-text'
                }`}
              >
                {s.label}
              </button>
            ))}
          </div>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="w-full h-16 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            placeholder="Результат звонка..."
          />
          <div className="mt-2 flex items-center gap-2">
            <CalendarPicker value={nextCallDate} onChange={setNextCallDate} />
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 1); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1.5 text-xs bg-bg rounded border border-muted/20 hover:bg-muted/20">+1</button>
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 3); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1.5 text-xs bg-bg rounded border border-muted/20 hover:bg-muted/20">+3</button>
            <button onClick={() => { const d = new Date(); d.setDate(d.getDate() + 7); setNextCallDate(d.toISOString().split('T')[0]) }} className="px-2 py-1.5 text-xs bg-bg rounded border border-muted/20 hover:bg-muted/20">+7</button>
          </div>
          <button onClick={() => handleSaveCall()} disabled={saving} className="w-full py-2 mt-3 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
            {saving ? 'Сохранение...' : 'Сохранить звонок'}
          </button>
          {callLogs.length > 0 && (
            <div className="mt-3 space-y-2 max-h-32 overflow-y-auto">
              {callLogs.map(cl => (
                <div key={cl.id} className="text-xs border-l-2 border-muted/20 pl-2 group">
                  <div className="flex items-center gap-1">
                    <span className="text-muted">{new Date(cl.called_at).toLocaleString('ru-RU')} — {cl.call_status}</span>
                    {(currentUser?.role === 'admin' || currentUser?.role === 'lead' || cl.user_id === currentUser?.id) && (
                      <button
                        onClick={async () => {
                          try {
                            await api.delete(`/companies/${company.id}/calls/${cl.id}`)
                            setCallLogs(prev => prev.filter(x => x.id !== cl.id))
                          } catch { /* ignore */ }
                        }}
                        className="ml-auto text-muted/30 hover:text-error opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                      >✕</button>
                    )}
                  </div>
                  {cl.notes && <p className="text-text/80 mt-0.5">{cl.notes}</p>}
                </div>
              ))}
            </div>
          )}
        </Section>

        {/* Comments */}
        <Section title="Комментарии">
          <div className="space-y-2 mb-3 max-h-48 overflow-y-auto">
            {comments.length === 0 && <p className="text-xs text-muted">Нет комментариев</p>}
            {comments.map(c => {
              const canDelete = currentUser?.role === 'admin' || currentUser?.role === 'lead' || c.user_id === currentUser?.id
              return (
                <div key={c.id} className="text-xs border-l-2 border-accent/30 pl-2 group">
                  <div className="flex items-center gap-1.5 mb-0.5">
                    <span className="font-semibold text-text">{c.user_name || '—'}</span>
                    <span className="text-muted">{new Date(c.created_at).toLocaleString('ru-RU')}</span>
                    {canDelete && (
                      <button
                        onClick={async () => {
                          try {
                            await api.delete(`/companies/${company.id}/comments/${c.id}`)
                            setComments(prev => prev.filter(x => x.id !== c.id))
                          } catch { /* ignore */ }
                        }}
                        className="ml-auto text-muted/30 hover:text-error opacity-0 group-hover:opacity-100 transition-opacity text-[10px]"
                      >✕</button>
                    )}
                  </div>
                  <p className="text-text/90 whitespace-pre-wrap">{c.text}</p>
                </div>
              )
            })}
          </div>
          <div className="flex gap-2">
            <input
              value={commentText}
              onChange={e => setCommentText(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendComment() } }}
              className="flex-1 px-2 py-1.5 bg-bg border border-muted/20 rounded text-sm focus:outline-none focus:ring-1 focus:ring-accent"
              placeholder="Написать комментарий..."
            />
            <button onClick={sendComment} disabled={!commentText.trim() || sendingComment} className="px-3 py-1.5 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-xs font-medium rounded transition-colors">
              {sendingComment ? '...' : '→'}
            </button>
          </div>
        </Section>

        {/* Meeting */}
        <Section title="Встреча">
          {existingMeeting ? (
            <>
              <div className="text-sm space-y-1 mb-3">
                <p><span className="text-muted">Дата:</span> {existingMeeting.date}</p>
                <p><span className="text-muted">Время:</span> {existingMeeting.hour}:00</p>
                <p><span className="text-muted">Назначил:</span> {existingMeeting.booked_by}</p>
                {existingMeeting.notes && <p><span className="text-muted">Заметки:</span> {existingMeeting.notes}</p>}
              </div>
              <button onClick={handleCancelMeeting} disabled={cancelling} className="w-full py-2 bg-error hover:bg-error/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
                {cancelling ? 'Отмена...' : 'Отменить встречу'}
              </button>
            </>
          ) : bookedMeetingId ? (
            <>
              <div className="flex gap-2 mb-2">
                <CalendarPicker value={meetingDate} onChange={setMeetingDate} />
                <input type="time" value={meetingTime} onChange={(e) => setMeetingTime(e.target.value)} className="w-24 px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent" />
              </div>
              <textarea
                value={meetingNotes}
                onChange={(e) => setMeetingNotes(e.target.value)}
                className="w-full h-20 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none text-sm mt-2 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="Место, тема, участники..."
              />
              <button onClick={handleSaveMeetingNotes} disabled={savingMeeting} className="w-full py-2 mt-2 bg-purple-600 hover:bg-purple-600/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
                {savingMeeting ? 'Сохранение...' : 'Сохранить встречу'}
              </button>
            </>
          ) : company.call_status === 'meeting' && meetingLoading ? (
            <p className="text-sm text-muted">Загрузка...</p>
          ) : (
            <>
              <button
                onClick={() => setShowCalendarBook(true)}
                className="w-full py-2 mb-3 bg-purple-600 hover:bg-purple-600/90 text-white text-sm font-medium rounded-lg transition-colors"
              >
                Выбрать слот в календаре
              </button>
              <div className="flex gap-2">
                <CalendarPicker value={meetingDate} onChange={setMeetingDate} />
                <input type="time" value={meetingTime} onChange={(e) => setMeetingTime(e.target.value)} className="w-24 px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent" />
              </div>
              <textarea
                value={meetingNotes}
                onChange={(e) => setMeetingNotes(e.target.value)}
                className="w-full h-12 px-3 py-2 bg-bg border border-muted/20 rounded-lg resize-none text-sm mt-2 focus:outline-none focus:ring-2 focus:ring-accent"
                placeholder="Место, тема..."
              />
              <button onClick={handleScheduleMeeting} disabled={!meetingDate || !meetingTime || scheduling} className="w-full py-2 mt-2 bg-purple-600/50 hover:bg-purple-600/70 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors">
                {scheduling ? 'Назначение...' : 'Назначить (быстро)'}
              </button>
            </>
          )}
        </Section>

        {/* Director */}
          <Section title="Руководство / ЛПР">
            <Field label="Руководитель" value={company.director} field="director" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} highlight={true} />
            <Field label="Должность" value={company.director_title} field="director_title" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
            <Field label="Контактное лицо" value={company.contact_person} field="contact_person" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
            <Field label="Контакты компании" value={company.contact_person_full} field="contact_person_full" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
            <Field label="Фин. директор" value={company.fin_director} field="fin_director" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
            <Field label="ИНН директора" value={company.director_inn} field="director_inn" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
            <Field label="Номер ЛПР" value={company.lpr_phone} field="lpr_phone" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} highlight={true} />
            <Field label="Email ЛПР" value={company.lpr_email} field="lpr_email" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} highlight={true} />
          </Section>

        {/* CP Actions */}
        <Section title="Коммерческое предложение">
          <div className="flex flex-col gap-2">
            <button
              onClick={async () => {
                const missing: string[] = []
                if (!company.director) missing.push('Руководитель')
                if (!company.lpr_phone) missing.push('Номер ЛПР')
                if (missing.length) {
                  setCpError('Заполните: ' + missing.join(', '))
                  return
                }
                setCpError('')
                try {
                  const { data } = await api.post(`/companies/${company.id}/cp`, {}, { responseType: 'blob' })
                  const url = URL.createObjectURL(data)
                  const a = document.createElement('a')
                  a.href = url
                  a.download = `КП_${company.name}.docx`
                  a.click()
                  URL.revokeObjectURL(url)
                } catch (e: any) {
                  const msg = e?.response?.data?.detail || 'Ошибка генерации КП'
                  setCpError(msg)
                }
              }}
              className="w-full py-2 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              📄 Скачать Word
            </button>
            <button
              onClick={async () => {
                const missing: string[] = []
                if (!company.director) missing.push('Руководитель')
                if (!company.lpr_phone) missing.push('Номер ЛПР')
                if (!company.lpr_email) missing.push('Email ЛПР')
                if (missing.length) {
                  setCpError('Заполните: ' + missing.join(', '))
                  return
                }
                setCpError('')
                try {
                  await api.post(`/companies/${company.id}/cp/send`)
                  alert('КП отправлено на ' + company.lpr_email)
                } catch (e: any) {
                  const msg = e?.response?.data?.detail || 'Ошибка отправки'
                  setCpError(msg)
                }
              }}
              className="w-full py-2 bg-blue-600/50 hover:bg-blue-600/70 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
            >
              ✉️ Отправить по email
            </button>
          </div>
          {cpError && (
            <div className="mt-2 px-3 py-2 bg-error/10 rounded text-xs text-error border border-error/20">
              {cpError}
            </div>
          )}
        </Section>

        {/* Activity */}
        <Section title="Профиль деятельности">
          <Field label="Вид деятельности" value={company.activity_main} field="activity_main" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Код ОКВЭД" value={company.activity_code} field="activity_code" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Доп. деятельность" value={company.activity_other} field="activity_other" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Отрасль / Ниша" value={company.niche} field="niche" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Предмет снабжения" value={company.supply_subject} field="supply_subject" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Орг. форма" value={company.org_form} field="org_form" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Сегмент" value={company.segment} field="segment" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Размер" value={company.size} field="size" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Приоритет" value={company.priority} field="priority" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="МСП" value={company.msp} field="msp" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
        </Section>

        {/* Finance */}
        <Section title="Финансы">
          <Field label="Выручка" value={formatMoney(company.revenue)} field="revenue" companyId={company.id} rawValue={company.revenue?.toString() || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Прибыль" value={formatMoney(company.profit)} field="profit" companyId={company.id} rawValue={company.profit?.toString() || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Баланс" value={formatMoney(company.balance)} field="balance" companyId={company.id} rawValue={company.balance?.toString() || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Уставный капитал" value={formatMoney(company.capital)} field="capital" companyId={company.id} rawValue={company.capital?.toString() || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Сотрудники" value={company.employees != null ? `${company.employees} чел.` : null} field="employees" companyId={company.id} rawValue={company.employees?.toString() || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Обороты импорта" value={formatNumericString(company.import_turnover)} field="import_turnover" companyId={company.id} rawValue={company.import_turnover || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Обороты экспорта" value={formatNumericString(company.export_turnover)} field="export_turnover" companyId={company.id} rawValue={company.export_turnover || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Подтв. импорт" value={company.import_confirmed || '—'} field="import_confirmed" companyId={company.id} rawValue={company.import_confirmed || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Валютные платежи" value={company.foreign_payments || '—'} field="foreign_payments" companyId={company.id} rawValue={company.foreign_payments || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
        </Section>

        {/* Details */}
        <Section title="Реквизиты">
          <Field label="ОГРН" value={company.ogrn} field="ogrn" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Дата регистрации" value={company.reg_date} field="reg_date" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Налоговая" value={company.tax_office} field="tax_office" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Юр. адрес" value={company.address} field="address" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Факт. адрес" value={company.actual_address} field="actual_address" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Гражданство" value={company.citizenship} field="citizenship" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Филиалы" value={company.branches} field="branches" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Сайт" value={company.website} field="website" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Email" value={company.email} field="email" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Телефон" value={company.phone} field="phone" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="LinkedIn" value={company.linkedin} field="linkedin" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Focus-ссылка" value={company.focus_link} field="focus_link" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Источник" value={company.source_orig} field="source_orig" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
        </Section>

        {/* Additional */}
        <Section title="Дополнительно">
          <Field label="Арбитраж" value={company.arbitrage} field="arbitrage" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Сумма исков" value={company.arbitrage_amount != null ? `${Number(company.arbitrage_amount).toLocaleString('ru-RU')} ₽` : null} field="arbitrage_amount" companyId={company.id} rawValue={company.arbitrage_amount || ''} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Лицензии" value={company.licenses} field="licenses" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
          <Field label="Реестры" value={company.registries} field="registries" companyId={company.id} onUpdate={handleFieldUpdate} onError={setSaveError} />
        </Section>

        {/* Source Data */}
        {sourceData.length > 0 && (
          <Section title="Данные из источников">
            {sourceData.map((group: any) => (
              <div key={group.source_id} className="mb-3">
                <p className="text-[10px] font-semibold text-accent mb-1">
                  📄 {group.source_filename} ({new Date(group.uploaded_at).toLocaleDateString('ru-RU')})
                </p>
                {group.entries.map((entry: any, ei: number) => (
                  <div key={ei}>
                    {Object.entries(entry.row_data).map(([col, val]) => {
                      if (!val) return null
                      return (
                        <div key={col} className="flex justify-between py-0.5 gap-4">
                          <span className="text-[11px] text-muted shrink-0 w-40">{col}</span>
                          <span className="text-[11px] text-right break-words">{String(val)}</span>
                        </div>
                      )
                    })}
                  </div>
                ))}
              </div>
            ))}
          </Section>
        )}

        {saveError && (
          <div className="px-4 py-2 bg-error/10 border-b border-error/20 text-xs text-error">{saveError}</div>
        )}

        {/* Meta */}
        <div className="p-4 text-xs text-muted space-y-1">
          <p>Попыток: {company.call_count}</p>
          {company.last_called_at && <p>Последний звонок: {new Date(company.last_called_at).toLocaleString('ru-RU')}</p>}
          {company.created_at && <p>Создана: {new Date(company.created_at).toLocaleDateString('ru-RU')}</p>}
        </div>
      </div>

      {showCalendarBook && (
        <CalendarModal onClose={() => setShowCalendarBook(false)} preselectedCompanyId={company.id} onBooked={handleBookedSlot} onMeetingClick={(companyId) => { setShowCalendarBook(false); onNavigateToCompany?.(companyId) }} />
      )}
    </div>
  )
}
