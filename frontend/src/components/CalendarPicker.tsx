import { useState, useRef, useEffect } from 'react'

const MONTHS = ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек']
const DAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function getMonthDays(year: number, month: number): (number | null)[] {
  const first = new Date(year, month, 1).getDay()
  const startOffset = first === 0 ? 6 : first - 1
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const cells: (number | null)[] = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  return cells
}

export default function CalendarPicker({
  value,
  onChange,
}: {
  value: string
  onChange: (date: string) => void
}) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const selected = value ? new Date(value + 'T00:00:00') : null
  const [viewYear, setViewYear] = useState(selected?.getFullYear() ?? new Date().getFullYear())
  const [viewMonth, setViewMonth] = useState(selected?.getMonth() ?? new Date().getMonth())

  useEffect(() => {
    if (selected) {
      setViewYear(selected.getFullYear())
      setViewMonth(selected.getMonth())
    }
  }, [value])

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  const cells = getMonthDays(viewYear, viewMonth)
  const today = new Date()
  const todayStr = today.toISOString().split('T')[0]

  function selectDay(day: number) {
    const m = String(viewMonth + 1).padStart(2, '0')
    const d = String(day).padStart(2, '0')
    onChange(`${viewYear}-${m}-${d}`)
    setOpen(false)
  }

  function prevMonth() {
    if (viewMonth === 0) { setViewYear(v => v - 1); setViewMonth(11) }
    else setViewMonth(m => m - 1)
  }

  function nextMonth() {
    if (viewMonth === 11) { setViewYear(v => v + 1); setViewMonth(0) }
    else setViewMonth(m => m + 1)
  }

  const formatted = value
    ? `${value.split('-')[2]}.${value.split('-')[1]}.${value.split('-')[0]}`
    : ''

  return (
    <div ref={ref} className="relative flex-1">
      <div
        onClick={() => setOpen(o => !o)}
        className="px-2 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent select-none"
      >
        {formatted || <span className="text-muted">дд.мм.гггг</span>}
      </div>

      {open && (
        <div className="absolute bottom-full mb-1 left-0 z-50 w-64 bg-surface border border-muted/20 rounded-xl shadow-xl p-3">
          {/* Header */}
          <div className="flex items-center justify-between mb-2">
            <button onClick={prevMonth} className="w-7 h-7 flex items-center justify-center rounded hover:bg-bg text-muted hover:text-text text-sm">◀</button>
            <span className="text-sm font-semibold">{MONTHS[viewMonth]} {viewYear}</span>
            <button onClick={nextMonth} className="w-7 h-7 flex items-center justify-center rounded hover:bg-bg text-muted hover:text-text text-sm">▶</button>
          </div>

          {/* Day names */}
          <div className="grid grid-cols-7 mb-1">
            {DAYS.map(d => (
              <div key={d} className="text-center text-xs text-muted py-1">{d}</div>
            ))}
          </div>

          {/* Days */}
          <div className="grid grid-cols-7">
            {cells.map((day, i) => {
              if (!day) return <div key={i} />
              const dayStr = `${viewYear}-${String(viewMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
              const isSelected = dayStr === value
              const isToday = dayStr === todayStr
              return (
                <button
                  key={i}
                  onClick={() => selectDay(day)}
                  className={`w-full aspect-square flex items-center justify-center text-xs rounded-full transition-colors
                    ${isSelected ? 'bg-accent text-white font-semibold' : ''}
                    ${!isSelected && isToday ? 'border border-accent text-accent font-semibold' : ''}
                    ${!isSelected && !isToday ? 'hover:bg-bg text-text' : ''}
                  `}
                >
                  {day}
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
