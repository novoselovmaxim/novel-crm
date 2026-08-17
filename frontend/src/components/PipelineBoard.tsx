import { useEffect, useState } from 'react'
import api from '../api/client'
import { PipelineBoard as PipelineBoardType } from '../types'
import StatusBadge from './StatusBadge'

const stageOrder = ['new', 'message_sent', 'diagnosis_done', 'test_offered', 'test_done', 'reserve', 'client', 'partner']

const stageLabels: Record<string, string> = {
  new: 'Новый',
  message_sent: 'Сообщение отправлено',
  diagnosis_done: 'Диагностика пройдена',
  test_offered: 'Тест предложен',
  test_done: 'Тест выполнен',
  reserve: 'Резерв',
  client: 'Клиент',
  partner: 'Партнёр',
}

const stageColors: Record<string, string> = {
  new: 'border-gray-500',
  message_sent: 'border-blue-500',
  diagnosis_done: 'border-yellow-500',
  test_offered: 'border-sky-500',
  test_done: 'border-green-500',
  reserve: 'border-purple-500',
  client: 'border-emerald-500',
  partner: 'border-amber-500',
}

export default function PipelineBoard({ onSelectCompany, onNavigateToCompany }: { onSelectCompany?: (id: string) => void; onNavigateToCompany?: (id: string) => void }) {
  const [board, setBoard] = useState<PipelineBoardType | null>(null)
  const [search, setSearch] = useState('')
  const [moving, setMoving] = useState<string | null>(null)

  const loadBoard = async () => {
    const { data } = await api.get('/pipeline', { params: { search: search || undefined } })
    setBoard(data)
  }

  useEffect(() => {
    loadBoard()
  }, [search])

  const moveCompany = async (companyId: string, stage: string) => {
    setMoving(companyId)
    try {
      await api.patch(`/pipeline/${companyId}`, { stage })
      await loadBoard()
    } finally {
      setMoving(null)
    }
  }

  const getNextStages = (currentStage: string) => {
    const idx = stageOrder.indexOf(currentStage)
    if (idx === -1 || idx >= stageOrder.length - 1) return []
    return stageOrder.slice(idx + 1)
  }

  if (!board) {
    return <div className="flex items-center justify-center h-full text-muted">Загрузка...</div>
  }

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-muted/10">
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          className="w-full max-w-md px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent"
          placeholder="Поиск компании..."
        />
      </div>
      <div className="flex-1 overflow-x-auto">
        <div className="flex gap-3 p-4 h-full min-w-max">
          {stageOrder.map(stage => {
            const group = board.groups.find(g => g.stage === stage)
            const count = group?.count || 0
            const companies = group?.companies || []
            const borderColor = stageColors[stage] || 'border-gray-500'

            return (
              <div key={stage} className={`flex flex-col w-72 bg-surface rounded-xl border-t-2 ${borderColor} shrink-0`}>
                <div className="flex items-center justify-between px-3 py-2 border-b border-muted/10">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={stage} kind="pipeline" />
                    <span className="text-xs text-muted font-mono">{count}</span>
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                  {companies.length === 0 && (
                    <p className="text-xs text-muted text-center py-4">Нет компаний</p>
                  )}
                  {companies.map(company => (
                    <div
                      key={company.id}
                      className="p-2.5 bg-bg rounded-lg border border-muted/10 hover:border-accent/30 cursor-pointer transition-colors"
                      onClick={() => onSelectCompany?.(company.id)}
                    >
                      <p className="text-sm font-medium leading-tight mb-1 line-clamp-2">{company.name}</p>
                      <p className="text-xs text-muted font-mono mb-1">{company.inn}</p>
                      {company.region && <p className="text-xs text-muted mb-1">{company.region}</p>}
                      <div className="flex items-center justify-between mt-1.5">
                        <div className="flex items-center gap-1">
                          {company.tg_contact && (
                            <a
                              href={`https://t.me/${company.tg_contact.replace('@', '')}`}
                              target="_blank"
                              rel="noopener"
                              onClick={e => e.stopPropagation()}
                              className="text-[10px] px-1.5 py-0.5 bg-blue-500/10 text-blue-400 rounded"
                            >
                              TG
                            </a>
                          )}
                          <StatusBadge status={company.call_status} kind="call" />
                          {company.call_status === 'meeting' && (
                            company.next_meeting ? (
                              <span className="text-[10px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded whitespace-nowrap">
                                📅 {company.next_meeting.date} {String(company.next_meeting.hour).padStart(2, '0')}:00
                              </span>
                            ) : (
                              <span className="text-[10px] px-1.5 py-0.5 bg-orange-500/15 text-orange-400 rounded whitespace-nowrap font-medium">
                                ⚠ нет даты
                              </span>
                            )
                          )}
                        </div>
                        {getNextStages(stage).length > 0 && (
                          <div className="relative" onClick={e => e.stopPropagation()}>
                            <button
                              disabled={moving === company.id}
                              className="text-[10px] px-1.5 py-0.5 bg-accent/10 text-accent rounded hover:bg-accent/20 disabled:opacity-50"
                              onClick={(e) => {
                                e.preventDefault()
                                const dropdown = e.currentTarget.nextElementSibling
                                if (dropdown) {
                                  dropdown.classList.toggle('hidden')
                                }
                              }}
                            >
                              {moving === company.id ? '...' : '→'}
                            </button>
                            <div className="hidden absolute right-0 top-full mt-1 z-20 bg-surface border border-muted/20 rounded-lg shadow-xl py-1 min-w-[180px]">
                              {getNextStages(stage).map(nextStage => (
                                <button
                                  key={nextStage}
                                  onClick={() => moveCompany(company.id, nextStage)}
                                  className="w-full text-left px-3 py-1.5 text-xs hover:bg-bg transition-colors"
                                >
                                  {stageLabels[nextStage] || nextStage}
                                </button>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                  {count > companies.length && (
                    <button
                      onClick={() => onNavigateToCompany?.(stage)}
                      className="w-full py-1.5 text-xs text-muted hover:text-text transition-colors"
                    >
                      + ещё {count - companies.length}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
