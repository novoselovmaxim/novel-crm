import { useState, useRef, useEffect } from 'react'

const STATUSES = [
  { value: 'new', label: 'Новый' },
  { value: 'not_reached', label: 'Не дозвонился' },
  { value: 'no_answer', label: 'Не отвечает' },
  { value: 'callback', label: 'Перезвонить' },
  { value: 'in_progress', label: 'В работе' },
  { value: 'interested', label: 'Заинтересован' },
  { value: 'meeting', label: 'Встреча назначена' },
  { value: 'refused', label: 'Отказ' },
]

const statusColors: Record<string, string> = {
  new: 'bg-gray-500/20 text-gray-400',
  not_reached: 'bg-orange-500/20 text-orange-400',
  no_answer: 'bg-red-500/20 text-red-400',
  callback: 'bg-blue-500/20 text-blue-400',
  in_progress: 'bg-yellow-500/20 text-yellow-400',
  interested: 'bg-green-500/20 text-green-400',
  meeting: 'bg-purple-500/20 text-purple-400',
  refused: 'bg-gray-600/20 text-gray-500',
}

const statusDotColors: Record<string, string> = {
  new: 'bg-gray-500',
  not_reached: 'bg-orange-500',
  no_answer: 'bg-red-500',
  callback: 'bg-blue-500',
  in_progress: 'bg-yellow-500',
  interested: 'bg-green-500',
  meeting: 'bg-purple-500',
  refused: 'bg-gray-600',
}

export default function StatusDropdown({ value, onChange, disabled }: { value: string; onChange: (v: string) => void; disabled?: boolean }) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div ref={ref} className="relative w-full">
      <button
        type="button"
        onClick={() => !disabled && setOpen(p => !p)}
        disabled={disabled}
        className="w-full px-1.5 py-1 rounded text-xs text-left flex items-center gap-1.5 border border-muted/20 bg-bg cursor-pointer hover:border-muted/40 disabled:opacity-50 disabled:cursor-default"
      >
        <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${statusDotColors[value] || 'bg-gray-500'}`} />
        <span className={statusColors[value]?.replace(/\s+\S+$/, '') || ''}>
          {STATUSES.find(s => s.value === value)?.label || value}
        </span>
      </button>
      {open && (
        <div className="absolute top-full left-0 mt-1 w-48 bg-surface border border-muted/20 rounded-lg shadow-xl z-50 py-1">
          {STATUSES.map(s => (
            <button
              key={s.value}
              onClick={() => { onChange(s.value); setOpen(false) }}
              className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-surfaceHover ${value === s.value ? 'font-medium' : ''}`}
            >
              <span className={`w-2 h-2 rounded-full shrink-0 ${statusDotColors[s.value]}`} />
              <span className={statusColors[s.value]}>{s.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
