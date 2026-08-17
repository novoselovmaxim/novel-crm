import { useState, useRef, useCallback, useEffect } from 'react'
import api from '../api/client'

interface ImportField {
  key: string
  label: string
  type: string
}

interface UploadPreview {
  file_id: string
  original_filename: string
  sheets: string[]
  columns: string[]
  sample_rows: (string | null)[][]
  auto_mapping: Record<string, string>
  unmatched: string[]
}

interface ImportTemplate {
  id: string
  name: string
  mapping: Record<string, string>
}

interface ImportRunCreated {
  source_id: string
  status: string
  total_rows: number
}

interface ImportRunStatus {
  source_id: string
  status: string
  total_rows: number
  processed_rows: number
  added_count: number
  updated_count: number
  skipped_count: number
  error_message: string | null
}

type Step = 'idle' | 'mapping' | 'running' | 'done'

export default function ImportModal({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [step, setStep] = useState<Step>('idle')
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [preview, setPreview] = useState<UploadPreview | null>(null)
  const [fields, setFields] = useState<ImportField[]>([])
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [sheet, setSheet] = useState('')
  const [templates, setTemplates] = useState<ImportTemplate[]>([])
  const [templateName, setTemplateName] = useState('')
  const [selectedTemplateId, setSelectedTemplateId] = useState('')
  const [overwrite, setOverwrite] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)
  const [runStatus, setRunStatus] = useState<ImportRunStatus | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const pollStartRef = useRef<number | null>(null)

  useEffect(() => {
    api.get('/import/fields').then(({ data }) => setFields(data))
    api.get('/import/templates').then(({ data }) => setTemplates(data))
  }, [])

  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f && (f.name.endsWith('.xlsx') || f.name.endsWith('.xls'))) {
      setFile(f)
    }
  }, [])

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post<UploadPreview>('/import/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setPreview(data)
      setSheet(data.sheets[0] || '')
      setMapping({ ...data.auto_mapping })
      setStep('mapping')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const applyTemplate = (tmpl: ImportTemplate) => {
    setMapping({ ...tmpl.mapping })
  }

  const saveTemplate = async () => {
    if (!templateName.trim()) return
    try {
      await api.post('/import/templates', { name: templateName, mapping })
      const { data } = await api.get<ImportTemplate[]>('/import/templates')
      setTemplates(data)
      setTemplateName('')
    } catch { }
  }

  const startImport = async () => {
    if (!preview) return
    setStep('running')
    setError(null)
    setRunStatus(null)
    const tmpl = templates.find(t => t.id === selectedTemplateId)
    try {
      const { data } = await api.post<ImportRunCreated>('/import/run', {
        file_id: preview.file_id,
        sheet,
        mapping,
        original_filename: file?.name || 'import',
        template_name: tmpl?.name || null,
        overwrite,
      })
      pollStartRef.current = Date.now()
      pollRef.current = setInterval(async () => {
        try {
          if (pollStartRef.current && Date.now() - pollStartRef.current > 900000) {
            if (pollRef.current) clearInterval(pollRef.current)
            setError('Import timed out after 15 minutes')
            setStep('mapping')
            return
          }
          const { data: status } = await api.get<ImportRunStatus>(`/import/run/${data.source_id}/status`)
          setRunStatus(status)
          if (status.status === 'imported' || status.status === 'error') {
            if (pollRef.current) clearInterval(pollRef.current)
            setStep('done')
          }
        } catch {
          if (pollRef.current) clearInterval(pollRef.current)
          setError('Status check failed')
          setStep('mapping')
        }
      }, 1000)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Import failed')
      setStep('mapping')
    }
  }

  const progress = runStatus && runStatus.total_rows > 0
    ? Math.round((runStatus.processed_rows / runStatus.total_rows) * 100)
    : 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="w-full max-w-2xl bg-surface rounded-2xl border border-muted/10 p-6 mx-4 max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-5 shrink-0">
          <h2 className="text-lg font-semibold">Импорт данных</h2>
          <button onClick={onClose} className="text-muted hover:text-text text-xl leading-none">&times;</button>
        </div>

        {step === 'idle' && (
          <div>
            {!file ? (
              <div
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
                  dragOver ? 'border-accent bg-accent/5' : 'border-muted/20 hover:border-accent/50'
                }`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => inputRef.current?.click()}
              >
                <p className="text-muted mb-1">Перетащите файл .xlsx сюда</p>
                <p className="text-xs text-muted/60">или нажмите для выбора</p>
                <input ref={inputRef} type="file" accept=".xlsx,.xls" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </div>
            ) : (
              <div>
                <div className="flex items-center gap-3 mb-4 p-3 bg-bg rounded-xl">
                  <span className="text-accent text-lg">📄</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate">{file.name}</p>
                    <p className="text-xs text-muted">{(file.size / 1024).toFixed(0)} KB</p>
                  </div>
                  <button onClick={() => setFile(null)} className="text-muted hover:text-text text-sm">Изменить</button>
                </div>
                <button onClick={handleUpload} disabled={uploading} className="w-full py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 disabled:opacity-50 transition-colors">
                  {uploading ? 'Загрузка...' : 'Загрузить'}
                </button>
              </div>
            )}
            {error && <p className="mt-3 text-sm text-error">{error}</p>}
          </div>
        )}

        {step === 'mapping' && preview && (
          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="flex items-center gap-3 mb-3 shrink-0">
              <span className="text-xs text-muted">Лист:</span>
              <select value={sheet} onChange={(e) => setSheet(e.target.value)} className="px-2 py-1 bg-bg border border-muted/20 rounded text-xs">
                {preview.sheets.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
              <div className="flex-1" />
              <span className="text-xs text-muted">Шаблон:</span>
              <select onChange={(e) => { setSelectedTemplateId(e.target.value); const t = templates.find(t => t.id === e.target.value); if (t) applyTemplate(t) }} className="px-2 py-1 bg-bg border border-muted/20 rounded text-xs" value={selectedTemplateId}>
                <option value="">Выбрать...</option>
                {templates.map(t => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </div>

            <div className="flex items-center gap-2 mb-3 shrink-0">
              <input value={templateName} onChange={(e) => setTemplateName(e.target.value)} placeholder="Новый шаблон..." className="flex-1 px-2 py-1 bg-bg border border-muted/20 rounded text-xs" />
              <button onClick={saveTemplate} disabled={!templateName.trim()} className="px-3 py-1 bg-accent text-white text-xs rounded hover:bg-accent/90 disabled:opacity-50">Сохранить</button>
            </div>

            <div className="overflow-y-auto flex-1 space-y-1 mb-3">
              {preview.columns.map((col) => {
                const isAuto = preview.auto_mapping[mapping[col] || ''] === col || Object.values(preview.auto_mapping).includes(col)
                const mappedField = Object.entries(mapping).find(([, v]) => v === col)?.[0] || ''
                return (
                  <div key={col} className="flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-bg/50">
                    <span className="text-xs text-muted w-48 truncate shrink-0" title={col}>{col}</span>
                    <span className="text-muted/40">→</span>
                    <select
                      value={mappedField}
                      onChange={(e) => {
                        const next = { ...mapping }
                        Object.keys(next).forEach(k => { if (next[k] === col) delete next[k] })
                        if (e.target.value) next[e.target.value] = col
                        setMapping(next)
                      }}
                      className="flex-1 px-2 py-1 bg-bg border border-muted/20 rounded text-xs"
                    >
                      <option value="">─ Пропустить</option>
                      {fields.map(f => (
                        <option key={f.key} value={f.key}>{f.label} ({f.type})</option>
                      ))}
                    </select>
                    {isAuto && <span className="text-[10px] text-accent shrink-0">авто</span>}
                  </div>
                )
              })}
            </div>

            {preview.sample_rows.length > 0 && (
              <div className="shrink-0 border-t border-muted/10 pt-3">
                <p className="text-[10px] text-muted mb-2">Preview (первые строки):</p>
                <div className="overflow-x-auto">
                  <table className="text-[10px] w-full">
                    <thead>
                      <tr>
                        {preview.columns.map(col => (
                          <th key={col} className="text-left text-muted pr-3 pb-1 whitespace-nowrap">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.sample_rows.map((row, ri) => (
                        <tr key={ri}>
                          {row.map((cell, ci) => (
                            <td key={ci} className="pr-3 pb-0.5 whitespace-nowrap max-w-[200px] truncate text-text/80">{cell || ''}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {error && <p className="mt-2 text-sm text-error shrink-0">{error}</p>}

            <label className="flex items-center gap-2 mt-2 shrink-0 text-xs text-muted cursor-pointer select-none">
              <input type="checkbox" checked={overwrite} onChange={(e) => setOverwrite(e.target.checked)} className="accent-accent" />
              Перезаписать существующие данные
            </label>

            <div className="flex gap-3 mt-3 shrink-0">
              <button onClick={() => { setFile(null); setPreview(null); setStep('idle') }} className="flex-1 py-2.5 rounded-xl border border-muted/20 text-muted hover:text-text transition-colors text-sm">
                Назад
              </button>
              <button onClick={startImport} className="flex-1 py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 transition-colors text-sm">
                Запустить импорт
              </button>
            </div>
          </div>
        )}

        {step === 'running' && (
          <div className="flex flex-col items-center py-8">
            <div className="w-8 h-8 border-2 border-accent border-t-transparent rounded-full animate-spin mb-4" />
            <p className="text-sm text-muted mb-1">Импорт выполняется...</p>
            {runStatus && runStatus.total_rows > 0 && (
              <>
                <div className="w-full max-w-xs bg-bg rounded-full h-2 mb-3">
                  <div
                    className="bg-accent h-2 rounded-full transition-all duration-500"
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-muted/80">
                  {runStatus.processed_rows} / {runStatus.total_rows} строк
                  {runStatus.added_count > 0 && ` · +${runStatus.added_count}`}
                  {runStatus.updated_count > 0 && ` · ~${runStatus.updated_count}`}
                  {runStatus.skipped_count > 0 && ` · -${runStatus.skipped_count}`}
                </p>
              </>
            )}
            {error && <p className="mt-3 text-sm text-error">{error}</p>}
          </div>
        )}

        {step === 'done' && runStatus && (
          <div>
            {runStatus.status === 'error' ? (
              <div className="p-4 bg-error/10 border border-error/20 rounded-xl mb-4">
                <p className="text-error font-medium mb-2">Ошибка импорта</p>
                <p className="text-sm text-muted">{runStatus.error_message || 'Неизвестная ошибка'}</p>
              </div>
            ) : (
              <div className="p-4 bg-success/10 border border-success/20 rounded-xl mb-4">
                <p className="text-success font-medium mb-2">Импорт завершён</p>
                <div className="text-sm space-y-1 text-muted">
                  <p>Добавлено компаний: <span className="text-text font-medium">{runStatus.added_count}</span></p>
                  <p>Обновлено: <span className="text-text font-medium">{runStatus.updated_count}</span></p>
                  <p>Пропущено (без ИНН): <span className="text-text font-medium">{runStatus.skipped_count}</span></p>
                  <p className="text-xs text-muted/60">Всего строк: {runStatus.total_rows}</p>
                </div>
              </div>
            )}
            <button onClick={onClose} className="w-full py-2.5 rounded-xl bg-accent text-white font-medium hover:bg-accent/90 transition-colors">
              Готово
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
