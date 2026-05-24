import { useState, useEffect, useCallback } from 'react'
import api from '../api/client'
import { useAuth } from '../store/auth'

interface UserInfo {
  id: string
  name: string
}

interface SlotData {
  hour: number
  users: string[]
}

interface DayData {
  date: string
  slots: SlotData[]
}

interface CalendarData {
  week_start: string
  users: UserInfo[]
  days: DayData[]
}

interface MySlot {
  day_of_week: number
  time_start: string
  time_end: string
}

const DAY_LABELS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
const HOURS = Array.from({ length: 12 }, (_, i) => i + 8)

function formatDate(d: Date) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function getMonday(d: Date) {
  const m = new Date(d)
  const day = m.getDay()
  const diff = m.getDate() - day + (day === 0 ? -6 : 1)
  m.setDate(diff)
  m.setHours(0, 0, 0, 0)
  return m
}

export default function CalendarModal({
  onClose,
  preselectedCompanyId,
  onBooked,
  onMeetingClick,
}: {
  onClose: () => void
  preselectedCompanyId?: string | null
  onBooked?: (result: { date: string; hour: number; meeting_id: string }) => void
  onMeetingClick?: (companyId: string) => void
}) {
  const user = useAuth((s) => s.user)
  const isAdminOrLead = user?.role === 'admin' || user?.role === 'lead'
  const [tab, setTab] = useState<'calendar' | 'schedule'>(isAdminOrLead ? 'calendar' : 'calendar')
  const [weekStart, setWeekStart] = useState(() => getMonday(new Date()))
  const [calendar, setCalendar] = useState<CalendarData | null>(null)
  const [mySlots, setMySlots] = useState<MySlot[]>([])
  const [saving, setSaving] = useState(false)
  const [bookCompanyId, setBookCompanyId] = useState(preselectedCompanyId || '')
  const [bookSlot, setBookSlot] = useState<{ date: string; hour: number } | null>(null)
  const [booking, setBooking] = useState(false)
  const [companySearch, setCompanySearch] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [message, setMessage] = useState('')
  const [meetings, setMeetings] = useState<any[]>([])

  const fetchCalendar = useCallback(async () => {
    const ws = formatDate(weekStart)
    const { data } = await api.get('/availability/calendar', { params: { week_start: ws } })
    setCalendar(data)
  }, [weekStart])

  const fetchMySlots = useCallback(async () => {
    const { data } = await api.get('/availability/slots/my')
    setMySlots(data)
  }, [])

  const fetchMeetings = useCallback(async () => {
    const ws = formatDate(weekStart)
    const end = formatDate(new Date(weekStart.getTime() + 6 * 86400000))
    try {
      const { data } = await api.get('/availability/meetings', { params: { date_from: ws, date_to: end } })
      setMeetings(data)
    } catch {}
  }, [weekStart])

  useEffect(() => {
    fetchCalendar()
    fetchMeetings()
    if (isAdminOrLead) fetchMySlots()
  }, [fetchCalendar, fetchMeetings, fetchMySlots, isAdminOrLead])

  useEffect(() => {
    if (companySearch.length < 2) { setSearchResults([]); return }
    const timer = setTimeout(async () => {
      try {
        const { data } = await api.get('/companies', { params: { search: companySearch, page_size: 10 } })
        setSearchResults(data.items || [])
      } catch {}
    }, 300)
    return () => clearTimeout(timer)
  }, [companySearch])

  const saveSchedule = async () => {
    setSaving(true)
    try {
      await api.put('/availability/slots/my', mySlots)
      setMessage('Расписание сохранено')
      fetchCalendar()
      setTimeout(() => setMessage(''), 2000)
    } catch {
      setMessage('Ошибка при сохранении')
    } finally {
      setSaving(false)
    }
  }

  const handleSlotClick = (day: DayData, slot: SlotData) => {
    if (!calendar) return
    const meeting = meetings.find(m => m.date === day.date && m.hour === slot.hour)
    if (meeting) {
      onMeetingClick?.(meeting.company_id)
      return
    }
    setBookSlot({ date: day.date, hour: slot.hour })
  }

  const confirmBooking = async () => {
    if (!bookSlot) return
    if (!bookCompanyId) return
    setBooking(true)
    try {
      const { data } = await api.post('/availability/book', {
        company_id: bookCompanyId,
        date: bookSlot.date,
        hour: bookSlot.hour,
      })
      onBooked?.({ date: bookSlot.date, hour: bookSlot.hour, meeting_id: data.meeting_id })
      onClose()
    } catch (e: any) {
      setMessage(e.response?.data?.detail || 'Ошибка бронирования')
    } finally {
      setBooking(false)
    }
  }

  const prevWeek = () => setWeekStart(d => new Date(d.getTime() - 7 * 86400000))
  const nextWeek = () => setWeekStart(d => new Date(d.getTime() + 7 * 86400000))

  const weekLabel = (() => {
    const end = new Date(weekStart.getTime() + 6 * 86400000)
    const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'short' }
    return `${weekStart.toLocaleDateString('ru', opts)} – ${end.toLocaleDateString('ru', opts)}`
  })()

  const firstUserId = calendar?.users[0]?.id
  const secondUserId = calendar?.users[1]?.id

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="w-full max-w-5xl bg-surface rounded-2xl border border-muted/10 flex flex-col mx-4"
        style={{ maxHeight: '90vh' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-muted/10 shrink-0">
          <h2 className="text-lg font-semibold">Календарь встреч</h2>
          <button onClick={onClose} className="text-muted hover:text-text text-xl leading-none">&times;</button>
        </div>

        {/* Tabs */}
        {isAdminOrLead && (
          <div className="flex gap-1 px-6 pt-3 shrink-0">
            <button
              onClick={() => { setTab('calendar'); fetchCalendar(); fetchMeetings(); }}
              className={`px-4 py-1.5 text-sm rounded-lg transition-colors ${tab === 'calendar' ? 'bg-accent text-white' : 'text-muted hover:text-text'}`}
            >
              Календарь
            </button>
            <button
              onClick={() => setTab('schedule')}
              className={`px-4 py-1.5 text-sm rounded-lg transition-colors ${tab === 'schedule' ? 'bg-accent text-white' : 'text-muted hover:text-text'}`}
            >
              Моё расписание
            </button>
          </div>
        )}

        {/* Message */}
        {message && (
          <div className="px-6 pt-3 shrink-0">
            <p className="text-sm text-success">{message}</p>
          </div>
        )}

        {tab === 'schedule' && isAdminOrLead && (
          <div className="p-6 space-y-3 overflow-auto">
            {DAY_LABELS.map((label, dow) => {
              const slot = mySlots.find(s => s.day_of_week === dow)
              if (!slot) {
                return (
                  <div key={dow} className="flex items-center gap-4">
                    <span className="w-10 text-sm font-medium">{label}</span>
                    <span className="text-xs text-muted italic">— Выходной</span>
                    <button
                      onClick={() => setMySlots(prev => [...prev, { day_of_week: dow, time_start: '09:00', time_end: '18:00' }])}
                      className="px-2 py-1 text-xs text-accent hover:underline"
                    >
                      + Добавить
                    </button>
                  </div>
                )
              }
              return (
                <div key={dow} className="flex items-center gap-4">
                  <span className="w-10 text-sm font-medium">{label}</span>
                  <span className="text-xs text-muted">с</span>
                  <input
                    type="time"
                    value={slot.time_start}
                    onChange={(e) => {
                      const v = e.target.value
                      setMySlots(prev => {
                        const copy = [...prev]
                        const idx = copy.findIndex(s => s.day_of_week === dow)
                        if (idx >= 0) copy[idx] = { ...copy[idx], time_start: v }
                        else copy.push({ day_of_week: dow, time_start: v, time_end: '18:00' })
                        return copy
                      })
                    }}
                    className="px-2 py-1 bg-bg border border-muted/20 rounded text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                  <span className="text-xs text-muted">до</span>
                  <input
                    type="time"
                    value={slot.time_end}
                    onChange={(e) => {
                      const v = e.target.value
                      setMySlots(prev => {
                        const copy = [...prev]
                        const idx = copy.findIndex(s => s.day_of_week === dow)
                        if (idx >= 0) copy[idx] = { ...copy[idx], time_end: v }
                        else copy.push({ day_of_week: dow, time_start: '09:00', time_end: v })
                        return copy
                      })
                    }}
                    className="px-2 py-1 bg-bg border border-muted/20 rounded text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                  <button
                    onClick={() => setMySlots(prev => prev.filter(s => s.day_of_week !== dow))}
                    className="px-2 py-1 text-xs text-error hover:underline"
                  >
                    Убрать
                  </button>
                </div>
              )
            })}
            <button
              onClick={saveSchedule}
              disabled={saving}
              className="mt-2 px-6 py-2 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
            >
              {saving ? 'Сохранение...' : 'Сохранить'}
            </button>
          </div>
        )}

        {tab === 'calendar' && (
          <div className="flex flex-col flex-1 min-h-0">
            {/* Week nav */}
            <div className="flex items-center justify-between px-6 py-3 shrink-0 border-b border-muted/10">
              <button onClick={prevWeek} className="text-muted hover:text-text px-2">&larr;</button>
              <span className="text-sm font-medium">{weekLabel}</span>
              <button onClick={nextWeek} className="text-muted hover:text-text px-2">&rarr;</button>
            </div>

            {/* Legend */}
            <div className="flex gap-4 px-6 py-2 text-xs text-muted shrink-0 border-b border-muted/10">
              {calendar?.users.map((u, i) => (
                <span key={u.id} className="flex items-center gap-1.5">
                  <span className={`w-3 h-3 rounded ${i === 0 ? 'bg-accent/40' : 'bg-warning/40'}`} />
                  {u.name}
                </span>
              ))}
              {calendar && calendar.users.length === 2 && (
                <span className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded" style={{ background: 'linear-gradient(135deg, rgba(79,110,247,0.4) 50%, rgba(245,158,11,0.4) 50%)' }} />
                  Оба
                </span>
              )}
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-muted/20" />
                Занято
              </span>
            </div>

            {/* Grid */}
            <div className="flex-1 overflow-auto px-6 py-3">
              <div className="grid grid-cols-8 gap-px bg-muted/10 rounded-lg overflow-hidden min-w-[600px]">
                {/* Header row */}
                <div className="bg-surface p-2 text-xs text-muted text-center font-medium" />
                {DAY_LABELS.map((label, i) => {
                  const d = new Date(weekStart.getTime() + i * 86400000)
                  const isToday = formatDate(d) === formatDate(new Date())
                  return (
                    <div key={i} className={`bg-surface p-2 text-xs text-center font-medium ${isToday ? 'text-accent' : 'text-muted'}`}>
                      {label}<br />{d.getDate()}
                    </div>
                  )
                })}

                {/* Hour rows */}
                {HOURS.map((hour) => (
                  [
                    <div key={`h-${hour}`} className="bg-surface p-2 text-xs text-muted text-center">
                      {hour}:00
                    </div>,
                    ...DAY_LABELS.map((_, di) => {
                      const d = new Date(weekStart.getTime() + di * 86400000)
                      const ds = formatDate(d)
                      const dayData = calendar?.days.find(dd => dd.date === ds)
                      const slot = dayData?.slots.find(s => s.hour === hour)
                      const meeting = meetings.find(m => m.date === ds && m.hour === hour)

                      let bg = 'bg-bg'
                      let cursor = 'cursor-default'
                      let title = ''
                      let cellStyle: React.CSSProperties = {}

                      if (meeting) {
                        bg = 'bg-muted/10'
                        cursor = 'cursor-pointer'
                        title = `${meeting.company_name} (${meeting.booked_by})`
                      } else if (slot) {
                        cursor = 'cursor-pointer hover:brightness-110'
                        if (slot.users.length === 2 && firstUserId && secondUserId) {
                          cellStyle = {
                            background: 'linear-gradient(135deg, rgba(79,110,247,0.2) 50%, rgba(245,158,11,0.2) 50%)',
                          }
                          title = 'Оба свободны'
                        } else if (slot.users.length === 1) {
                          const uid = slot.users[0]
                          if (uid === firstUserId) {
                            bg = 'bg-accent/20'
                          } else {
                            bg = 'bg-warning/20'
                          }
                          const userName = calendar?.users.find(u => u.id === uid)?.name || ''
                          title = `Свободно: ${userName}`
                        }
                      }

                      return (
                        <div
                          key={`${ds}-${hour}`}
                          className={`${bg} ${cursor} p-1 text-xs text-center transition-colors relative group`}
                          title={title}
                          onClick={() => {
                            if (meeting) {
                              onMeetingClick?.(meeting.company_id)
                            } else if (dayData && slot) {
                              handleSlotClick(dayData, slot)
                            }
                          }}
                          style={{ minHeight: '28px', ...cellStyle }}
                        >
                           {meeting && (
                               <span 
                                   className="text-[10px] text-muted truncate block leading-tight" 
                                   title={meeting.company_name}
                                   onClick={(e) => {
                                       e.stopPropagation()
                                       onMeetingClick?.(meeting.company_id)
                                   }}
                               >
                                   {meeting.company_name}
                               </span>
                           )}
                        </div>
                      )
                    }),
                  ]
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Booking dialog */}
        {bookSlot && (
          <div className="border-t border-muted/10 p-4 shrink-0">
            <p className="text-sm font-medium mb-3">
              Бронирование: {bookSlot.date} в {bookSlot.hour}:00
            </p>
            {preselectedCompanyId ? (
              <div className="flex gap-3 items-center">
                <span className="text-sm text-muted">Компания выбрана</span>
                <button
                  onClick={confirmBooking}
                  disabled={booking}
                  className="px-4 py-1.5 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {booking ? 'Бронирование...' : 'Подтвердить'}
                </button>
                <button onClick={() => setBookSlot(null)} className="px-4 py-1.5 rounded-xl border border-muted/20 text-muted text-sm hover:text-text transition-colors">
                  Отмена
                </button>
              </div>
            ) : (
              <div className="flex gap-3 items-start">
                <div className="relative flex-1">
                  <input
                    type="text"
                    value={companySearch}
                    onChange={(e) => setCompanySearch(e.target.value)}
                    placeholder="Поиск компании..."
                    className="w-full px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                  />
                  {searchResults.length > 0 && (
                    <div className="absolute top-full left-0 right-0 mt-1 bg-surface border border-muted/20 rounded-lg shadow-xl z-10 max-h-40 overflow-auto">
                      {searchResults.map((c: any) => (
                        <button
                          key={c.id}
                          onClick={() => { setBookCompanyId(c.id); setCompanySearch(c.name); setSearchResults([]) }}
                          className="w-full text-left px-3 py-1.5 text-sm hover:bg-surfaceHover"
                        >
                          {c.name}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <button
                  onClick={confirmBooking}
                  disabled={booking || !bookCompanyId}
                  className="px-4 py-1.5 rounded-xl bg-accent text-white text-sm font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors"
                >
                  {booking ? '...' : 'Забронировать'}
                </button>
                <button onClick={() => { setBookSlot(null); setBookCompanyId(preselectedCompanyId || ''); setCompanySearch(''); setSearchResults([]) }} className="px-4 py-1.5 rounded-xl border border-muted/20 text-muted text-sm hover:text-text transition-colors">
                  Отмена
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}