import { useState } from 'react'
import api from '../api/client'
import { useAuth } from '../store/auth'

export default function ProfileModal({ onClose }: { onClose: () => void }) {
  const user = useAuth(s => s.user)
  const fetchUser = useAuth(s => s.fetchUser)
  const [loading, setLoading] = useState(false)
  const [link, setLink] = useState<string | null>(null)

  const handleBind = async () => {
    setLoading(true)
    try {
      const { data } = await api.post('/auth/tg-link')
      setLink(data.link)
      window.open(data.link, '_blank')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Ошибка при получении ссылки')
    } finally {
      setLoading(false)
    }
  }

  const handleUnbind = async () => {
    setLoading(true)
    try {
      await api.post('/auth/tg-unbind')
      await fetchUser()
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Ошибка при отвязке')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={onClose}>
      <div className="bg-surface rounded-xl p-6 w-96 shadow-2xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-bold">Настройки</h2>
          <button onClick={onClose} className="text-muted hover:text-text">✕</button>
        </div>

        <div className="space-y-4">
          <div className="text-sm text-muted">
            <p><span className="text-text">Пользователь:</span> {user?.name || user?.email}</p>
            <p><span className="text-text">Роль:</span> {user?.role === 'admin' ? 'Администратор' : user?.role === 'lead' ? 'Руководитель' : 'Менеджер'}</p>
          </div>

          <div className="border-t border-muted/10 pt-4">
            <h3 className="text-sm font-semibold mb-2">Telegram</h3>
            {user?.tg_chat_id ? (
              <div>
                <p className="text-xs text-muted mb-2">
                  Привязан: @{user.tg_username || user.tg_chat_id}
                </p>
                <button
                  onClick={handleUnbind}
                  disabled={loading}
                  className="w-full py-2 bg-error hover:bg-error/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {loading ? 'Отвязка...' : 'Отвязать Telegram'}
                </button>
              </div>
            ) : (
              <div>
                <p className="text-xs text-muted mb-2">Telegram не привязан</p>
                <button
                  onClick={handleBind}
                  disabled={loading}
                  className="w-full py-2 bg-accent hover:bg-accent/90 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
                >
                  {loading ? 'Загрузка...' : 'Привязать Telegram'}
                </button>
                {link && (
                  <p className="text-xs text-muted mt-2">
                    Если бот не открылся: <a href={link} target="_blank" rel="noopener" className="text-accent underline">{link}</a>
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
