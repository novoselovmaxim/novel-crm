import { useState, useRef, useEffect } from 'react'
import api from '../api/client'
import { Company } from '../types'

interface ResearchResult {
  company_id: string
  suggestions: Record<string, { current: string; suggested: string; label: string; mode?: string }>
  ai_summary: string
  has_pending: boolean
  sources: { name: string; status: string; count: number; error?: string }[]
  brave_results: { title: string; url: string; description: string; age: string }[]
  exa_results: { title: string; url: string; text: string; score: number }[]
  zveno_answer: string
  zveno_results: { url: string; title: string }[]
  scraped_texts: string[]
  all_urls: string[]
  raw_text_preview: string
  company: Company
}

const QUERY_PRESETS = [
  { label: 'Контакты', query: 'руководство директор контакт телефон email' },
  { label: 'Деятельность', query: 'вид деятельности продукция услуги клиенты' },
  { label: 'Финансы', query: 'выручка прибыль финансовая отчётность' },
  { label: 'ВЭД', query: 'импорт экспорт валютные платежи международные поставки' },
  { label: 'Репутация', query: 'отзывы клиенты жалобы судебные дела' },
  { label: 'Конкуренты', query: 'конкуренты рыночная позиция отрасль' },
  { label: 'ЛПР', query: 'лицо принимающее решение руководитель закупок' },
]

function AutoResizeTextarea({
  value,
  onChange,
  onKeyDown,
  placeholder,
  className,
}: {
  value: string
  onChange: (v: string) => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  placeholder?: string
  className?: string
}) {
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (ref.current) {
      ref.current.style.height = 'auto'
      ref.current.style.height = Math.min(ref.current.scrollHeight, 120) + 'px'
    }
  }, [value])

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={e => onChange(e.target.value)}
      onKeyDown={onKeyDown}
      placeholder={placeholder}
      rows={1}
      className={className}
      style={{ resize: 'none', overflow: 'hidden' }}
    />
  )
}

function StructuredContent({ text }: { text: string }) {
  const sections = text.split(/\n{2,}/).filter(Boolean)
  return (
    <div className="space-y-2">
      {sections.map((section, i) => {
        const trimmed = section.trim()
        if (trimmed.startsWith('===') && trimmed.endsWith('===')) {
          const title = trimmed.replace(/=/g, '').trim()
          return (
            <div key={i} className="pt-2">
              <h4 className="text-[11px] font-bold text-accent uppercase tracking-wide">{title}</h4>
            </div>
          )
        }
        if (trimmed.startsWith('##')) {
          return (
            <h4 key={i} className="text-[11px] font-bold text-text pt-1">
              {trimmed.replace(/^#+\s*/, '')}
            </h4>
          )
        }
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
          const items = trimmed.split('\n').filter(l => l.match(/^[-*]\s/))
          return (
            <ul key={i} className="list-disc list-inside space-y-0.5">
              {items.map((item, j) => (
                <li key={j} className="text-[11px] text-text/80">
                  {item.replace(/^[-*]\s/, '')}
                </li>
              ))}
            </ul>
          )
        }
        if (trimmed.match(/^\d+\.\s/)) {
          const items = trimmed.split('\n').filter(l => l.match(/^\d+\.\s/))
          return (
            <ol key={i} className="list-decimal list-inside space-y-0.5">
              {items.map((item, j) => (
                <li key={j} className="text-[11px] text-text/80">
                  {item.replace(/^\d+\.\s/, '')}
                </li>
              ))}
            </ol>
          )
        }
        return (
          <div key={i} className="text-[11px] text-text/80 leading-relaxed whitespace-pre-wrap">
            {trimmed.split('\n').map((line, j) => (
              <span key={j}>
                {line}
                {j < trimmed.split('\n').length - 1 && <br />}
              </span>
            ))}
          </div>
        )
      })}
    </div>
  )
}

export default function ResearchModal({
  company,
  onClose,
  onApplySuggestion,
  onUpdateCompany,
}: {
  company: Company
  onClose: () => void
  onApplySuggestion?: (field: string, value: string) => void
  onUpdateCompany?: (data: Partial<Company>) => void
}) {
  const [selectedSources, setSelectedSources] = useState<string[]>(['brave', 'exa', 'zveno'])
  const [customQuery, setCustomQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<ResearchResult | null>(null)
  const [error, setError] = useState('')
  const [activeResultTab, setActiveResultTab] = useState<'brave' | 'exa' | 'zveno' | 'content' | 'suggestions'>('brave')

  const [followUpQuestion, setFollowUpQuestion] = useState('')
  const [followUpLoading, setFollowUpLoading] = useState(false)
  const [followUpAnswer, setFollowUpAnswer] = useState('')
  const [followUpHistory, setFollowUpHistory] = useState<{ q: string; a: string }[]>([])

  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')

  const toggleSource = (src: string) => {
    setSelectedSources(prev =>
      prev.includes(src) ? prev.filter(s => s !== src) : [...prev, src]
    )
  }

  const runResearch = async () => {
    if (selectedSources.length === 0 || loading) return
    setLoading(true)
    setError('')
    setResult(null)
    setFollowUpHistory([])
    setFollowUpAnswer('')
    try {
      const { data } = await api.post(`/research/${company.id}`, {
        sources: selectedSources,
        custom_query: customQuery.trim(),
      })
      setResult(data)
      if (data.company) {
        onUpdateCompany?.(data.company)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка исследования')
    } finally {
      setLoading(false)
    }
  }

  const applySuggestion = async (field: string, value: string) => {
    try {
      await api.post(`/ai/apply/${company.id}`, { field, value })
      onApplySuggestion?.(field, value)
      setResult(prev => {
        if (!prev) return prev
        const s = { ...prev.suggestions }
        delete s[field]
        return { ...prev, suggestions: s }
      })
    } catch {}
  }

  const rejectSuggestion = async (field: string) => {
    try {
      await api.post(`/ai/reject/${company.id}`, { field, value: '' })
      setResult(prev => {
        if (!prev) return prev
        const s = { ...prev.suggestions }
        delete s[field]
        return { ...prev, suggestions: s }
      })
    } catch {}
  }

  const saveAllSuggestions = async () => {
    if (!result || Object.keys(result.suggestions).length === 0) return
    setSaving(true)
    setSavedMsg('')
    try {
      const payload: Record<string, string> = {}
      for (const [field, val] of Object.entries(result.suggestions)) {
        payload[field] = val.suggested
      }
      const { data } = await api.post(`/research/${company.id}/save`, {
        suggestions: payload,
      })
      setSavedMsg(`Сохранено: ${data.updated_fields.join(', ') || 'без изменений'}`)
      if (data.company) {
        onUpdateCompany?.(data.company)
      }
      setResult(prev => {
        if (!prev) return prev
        return { ...prev, suggestions: {}, company: data.company }
      })
      setTimeout(() => setSavedMsg(''), 3000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Ошибка сохранения')
    } finally {
      setSaving(false)
    }
  }

  const askFollowUp = async () => {
    if (!followUpQuestion.trim() || followUpLoading) return
    setFollowUpLoading(true)
    setFollowUpAnswer('')
    try {
      const context = result
        ? [
            result.zveno_answer && `ZVENO: ${result.zveno_answer.slice(0, 1000)}`,
            result.ai_summary && `AI: ${result.ai_summary.slice(0, 1000)}`,
            ...result.brave_results.slice(0, 3).map(r => `Brave: ${r.title} — ${r.description}`),
            ...result.exa_results.slice(0, 3).map(r => `Exa: ${r.title} — ${(r.text || '').slice(0, 300)}`),
          ].filter(Boolean).join('\n\n')
        : ''
      const { data } = await api.post(`/research/${company.id}/follow-up`, {
        question: followUpQuestion.trim(),
        context,
      })
      setFollowUpAnswer(data.answer)
      setFollowUpHistory(prev => [...prev, { q: followUpQuestion.trim(), a: data.answer }])
      setFollowUpQuestion('')
    } catch (e: any) {
      setFollowUpAnswer(e?.response?.data?.detail || 'Ошибка запроса')
    } finally {
      setFollowUpLoading(false)
    }
  }

  const sourceStatus = (name: string) => result?.sources?.find(s => s.name === name)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface w-[950px] max-h-[85vh] rounded-xl shadow-2xl flex flex-col overflow-hidden border border-muted/10">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-3 border-b border-muted/10 shrink-0">
          <div>
            <h2 className="text-base font-bold">Исследование</h2>
            <p className="text-xs text-muted mt-0.5">{company.name} · ИНН {company.inn}</p>
          </div>
          <button onClick={onClose} className="text-muted hover:text-text text-lg px-2">✕</button>
        </div>

        {/* Config section */}
        <div className="px-5 py-3 border-b border-muted/10 shrink-0">
          {/* Source toggles */}
          <div className="flex items-center gap-3 mb-3">
            <span className="text-xs text-muted font-medium">Источники:</span>
            {['brave', 'exa', 'zveno'].map(src => {
              const labels: Record<string, string> = { brave: 'Brave Search', exa: 'Exa Semantic', zveno: 'ZVENO Sonar' }
              const st = sourceStatus(src)
              return (
                <label key={src} className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedSources.includes(src)}
                    onChange={() => toggleSource(src)}
                    className="accent-accent"
                  />
                  <span className="text-xs text-text">{labels[src]}</span>
                  {st && (
                    <span className={`text-[10px] ${
                      st.status === 'ok' ? 'text-success'
                      : st.status === 'blocked' ? 'text-orange-400'
                      : st.status === 'error' ? 'text-error'
                      : 'text-muted'
                    }`}>
                      {st.status === 'ok' ? `✓ ${st.count}`
                        : st.status === 'blocked' ? '⚠ блок'
                        : st.status === 'error' ? '✕'
                        : '—'}
                    </span>
                  )}
                </label>
              )
            })}
            {sourceStatus('exa')?.status === 'blocked' && (
              <span className="text-[10px] text-orange-400/80">Exa заблокирована с VPS. Используйте Brave.</span>
            )}
          </div>

          {/* Preset buttons */}
          <div className="flex flex-wrap gap-1.5 mb-2">
            {QUERY_PRESETS.map(p => (
              <button
                key={p.label}
                onClick={() => setCustomQuery(prev => prev ? `${prev} ${p.query}` : p.query)}
                className="px-2 py-1 text-[11px] bg-bg border border-muted/20 rounded hover:bg-muted/20 text-muted hover:text-text transition-colors"
              >
                {p.label}
              </button>
            ))}
            {customQuery && (
              <button
                onClick={() => setCustomQuery('')}
                className="px-2 py-1 text-[11px] bg-error/10 border border-error/20 rounded text-error hover:bg-error/20 transition-colors"
              >
                Очистить
              </button>
            )}
          </div>

          {/* Custom query — auto-resize textarea */}
          <div className="flex gap-2">
            <AutoResizeTextarea
              value={customQuery}
              onChange={setCustomQuery}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); runResearch() } }}
              placeholder="Дополнительный запрос для поиска (Enter — поиск)..."
              className="flex-1 px-3 py-2 bg-bg border border-muted/20 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-accent min-h-[36px] max-h-[120px]"
            />
            <button
              onClick={runResearch}
              disabled={selectedSources.length === 0 || loading}
              className="px-4 py-2 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors shrink-0"
            >
              {loading ? 'Поиск...' : '🔍 Исследовать'}
            </button>
          </div>
        </div>

        {/* Loading indicators */}
        {loading && (
          <div className="px-5 py-3 border-b border-muted/10 shrink-0">
            <div className="flex gap-4">
              {selectedSources.map(src => {
                const labels: Record<string, string> = { brave: 'Brave', exa: 'Exa', zveno: 'ZVENO' }
                return (
                  <div key={src} className="flex items-center gap-2 text-xs text-muted">
                    <div className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                    {labels[src]}
                  </div>
                )
              })}
              <div className="flex items-center gap-2 text-xs text-muted">
                <div className="w-3 h-3 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                Scraping
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="px-5 py-2 bg-error/10 border-b border-error/20 text-xs text-error shrink-0">
            {error}
          </div>
        )}

        {/* Saved message */}
        {savedMsg && (
          <div className="px-5 py-2 bg-success/10 border-b border-success/20 text-xs text-success shrink-0">
            ✓ {savedMsg}
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="flex-1 overflow-y-auto">
            {/* Result tabs */}
            <div className="flex border-b border-muted/10 shrink-0">
              {[
                { key: 'brave', label: `Brave (${result.brave_results.length})` },
                { key: 'exa', label: `Exa (${result.exa_results.length})` },
                { key: 'zveno', label: 'ZVENO' },
                { key: 'content', label: `Контент (${result.scraped_texts.length})` },
                { key: 'suggestions', label: `Данные (${Object.keys(result.suggestions).length})` },
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveResultTab(tab.key as any)}
                  className={`px-4 py-2 text-[11px] font-semibold uppercase tracking-wider transition-colors ${
                    activeResultTab === tab.key
                      ? 'text-accent border-b-2 border-accent'
                      : 'text-muted hover:text-text border-b-2 border-transparent'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="p-4">
              {/* Brave results */}
              {activeResultTab === 'brave' && (
                <div className="space-y-2">
                  {result.brave_results.length === 0 ? (
                    <p className="text-xs text-muted">Нет результатов</p>
                  ) : (
                    result.brave_results.map((r, i) => (
                      <div key={i} className="p-2 bg-bg rounded border border-muted/10">
                        <div className="flex items-start gap-2">
                          <span className="text-[10px] text-muted mt-0.5 shrink-0">{i + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <a href={r.url} target="_blank" rel="noopener" className="text-xs font-medium text-accent hover:underline block truncate">
                              {r.title}
                            </a>
                            <p className="text-[11px] text-muted mt-0.5 line-clamp-2">{r.description}</p>
                            {r.age && <span className="text-[10px] text-muted/50 mt-0.5 block">{r.age}</span>}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Exa results */}
              {activeResultTab === 'exa' && (
                <div className="space-y-2">
                  {result.exa_results.length === 0 ? (
                    <p className="text-xs text-muted">Нет результатов</p>
                  ) : (
                    result.exa_results.map((r, i) => (
                      <div key={i} className="p-2 bg-bg rounded border border-muted/10">
                        <div className="flex items-start gap-2">
                          <span className="text-[10px] text-muted mt-0.5 shrink-0">{i + 1}.</span>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <a href={r.url} target="_blank" rel="noopener" className="text-xs font-medium text-accent hover:underline truncate">
                                {r.title}
                              </a>
                              {r.score > 0 && (
                                <span className="text-[10px] text-muted shrink-0">score: {r.score.toFixed(2)}</span>
                              )}
                            </div>
                            {r.text && <p className="text-[11px] text-muted mt-0.5 line-clamp-3">{r.text}</p>}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ZVENO */}
              {activeResultTab === 'zveno' && (
                <div className="space-y-3">
                  {result.zveno_answer ? (
                    <div className="p-3 bg-indigo-600/5 border border-indigo-600/20 rounded text-xs text-text leading-relaxed">
                      <StructuredContent text={result.zveno_answer} />
                    </div>
                  ) : (
                    <p className="text-xs text-muted">Нет ответа</p>
                  )}
                  {result.zveno_results.length > 0 && (
                    <div>
                      <p className="text-[10px] font-semibold text-muted mb-1">Источники ZVENO:</p>
                      {result.zveno_results.map((r, i) => (
                        <div key={i} className="text-[11px]">
                          <a href={r.url} target="_blank" rel="noopener" className="text-accent hover:underline">{r.title || r.url}</a>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Scraped content — structured display */}
              {activeResultTab === 'content' && (
                <div className="space-y-3">
                  {result.all_urls.length > 0 && (
                    <div className="mb-2">
                      <p className="text-[10px] font-semibold text-muted mb-1">Просканированные URL:</p>
                      {result.all_urls.map((url, i) => (
                        <div key={i} className="text-[11px]">
                          <a href={url} target="_blank" rel="noopener" className="text-accent hover:underline truncate block">{url}</a>
                        </div>
                      ))}
                    </div>
                  )}
                  {result.scraped_texts.length === 0 ? (
                    <p className="text-xs text-muted">Нет контента для отображения</p>
                  ) : (
                    result.scraped_texts.map((text, i) => (
                      <div key={i} className="p-3 bg-bg rounded border border-muted/10">
                        <p className="text-[10px] font-semibold text-accent mb-2">Страница {i + 1}:</p>
                        <StructuredContent text={text} />
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* Suggestions */}
              {activeResultTab === 'suggestions' && (
                <div className="space-y-3">
                  {Object.keys(result.suggestions).length === 0 ? (
                    <p className="text-xs text-muted">Нет предложений по обновлению данных</p>
                  ) : (
                    <>
                      {/* Save all button */}
                      <div className="flex items-center gap-2 mb-2">
                        <button
                          onClick={saveAllSuggestions}
                          disabled={saving}
                          className="px-3 py-1.5 bg-success hover:bg-success/90 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors"
                        >
                          {saving ? 'Сохранение...' : `💾 Сохранить всё (${Object.keys(result.suggestions).length})`}
                        </button>
                        {savedMsg && <span className="text-[10px] text-success">{savedMsg}</span>}
                      </div>

                      {Object.entries(result.suggestions).map(([field, val]) => (
                        <div key={field} className="p-2 bg-yellow-500/5 border border-yellow-500/20 rounded text-xs">
                          <div className="text-yellow-400 font-semibold mb-1">💡 {val.label}</div>
                          <div className="flex items-center gap-2">
                            <span className="text-muted line-through">{val.current || '—'}</span>
                            <span className="text-accent">→</span>
                            <span className="text-text font-medium">{val.suggested}</span>
                            <button
                              onClick={() => applySuggestion(field, val.suggested)}
                              className="ml-auto px-2 py-0.5 bg-success/20 hover:bg-success/30 text-success text-[10px] rounded"
                            >Принять</button>
                            <button
                              onClick={() => rejectSuggestion(field)}
                              className="px-2 py-0.5 bg-error/20 hover:bg-error/30 text-error text-[10px] rounded"
                            >✕</button>
                          </div>
                        </div>
                      ))}
                    </>
                  )}

                  {/* AI summary */}
                  {(result.ai_summary || company.ai_summary) && (
                    <div className="p-2 bg-indigo-600/5 border border-indigo-600/20 rounded text-xs text-text leading-relaxed">
                      <span className="font-semibold text-indigo-400">📝 AI:</span>{' '}
                      <StructuredContent text={(result.ai_summary || company.ai_summary || '').slice(0, 500)} />
                    </div>
                  )}

                  {/* Raw text preview */}
                  {result.raw_text_preview && (
                    <details className="mt-2">
                      <summary className="text-[10px] text-muted cursor-pointer hover:text-text">
                        Сырой текст (превью)
                      </summary>
                      <pre className="mt-1 p-2 bg-bg rounded text-[10px] text-muted whitespace-pre-wrap max-h-40 overflow-y-auto">
                        {result.raw_text_preview}
                      </pre>
                    </details>
                  )}
                </div>
              )}
            </div>

            {/* Follow-up question section */}
            <div className="px-4 pb-4 border-t border-muted/10 pt-3">
              <p className="text-[10px] font-semibold text-muted mb-2 uppercase tracking-wider">Задать вопрос по результатам</p>

              {/* History */}
              {followUpHistory.length > 0 && (
                <div className="space-y-2 mb-3 max-h-40 overflow-y-auto">
                  {followUpHistory.map((h, i) => (
                    <div key={i} className="text-[11px]">
                      <div className="text-accent font-medium">→ {h.q}</div>
                      <div className="text-text/80 mt-0.5 pl-2 border-l-2 border-muted/20">{h.a}</div>
                    </div>
                  ))}
                </div>
              )}

              {/* Current answer */}
              {followUpAnswer && !followUpHistory.some(h => h.a === followUpAnswer) && (
                <div className="p-2 bg-indigo-600/5 border border-indigo-600/20 rounded text-[11px] text-text mb-2">
                  {followUpAnswer}
                </div>
              )}

              {/* Input */}
              <div className="flex gap-2">
                <input
                  value={followUpQuestion}
                  onChange={e => setFollowUpQuestion(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') askFollowUp() }}
                  className="flex-1 px-3 py-1.5 bg-bg border border-muted/20 rounded-lg text-xs focus:outline-none focus:ring-2 focus:ring-accent"
                  placeholder="Например: Кто главный rival? Есть ли филиалы за рубежом?"
                  disabled={followUpLoading}
                />
                <button
                  onClick={askFollowUp}
                  disabled={!followUpQuestion.trim() || followUpLoading}
                  className="px-3 py-1.5 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-xs font-medium rounded-lg transition-colors shrink-0"
                >
                  {followUpLoading ? '...' : '→'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="flex items-center justify-end px-5 py-3 border-t border-muted/10 shrink-0">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-bg border border-muted/20 rounded-lg text-sm text-muted hover:text-text"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  )
}
