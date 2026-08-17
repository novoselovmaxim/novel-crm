import { useState } from 'react'

const GUIDE_KEY = 'novel_crm_guide_seen_v1'

const steps = [
  {
    id: 'start',
    title: 'Привет! 👋',
    text: `Это короткий мануал по Novel CRM. Покажу главные вкладки и как в них работать. Один раз посмотрите — и он больше не будет показываться. Чтобы открыть его снова — нажмите «?» в правом верхнем углу.`,
  },
  {
    id: 'companies',
    title: '1. Вкладка «Компании»',
    text: `Здесь весь список компаний. Нажмите на любую строку — справа откроется карточка компании. В карточке 4 вкладки: Активность, Коммуникации, Данные, AI.`,
  },
  {
    id: 'activity',
    title: '2. «Активность» — звонки и статусы',
    text: `Вверху выберите статус (Новый, Заинтересован, Думают, Отказ...), напишите результат звонка и нажмите «Сохранить звонок». Строка появится в истории звонков ниже.`,
  },
  {
    id: 'meeting',
    title: '3. Как назначить встречу',
    text: `Откройте карточку компании → блок «Встреча». Нажмите «Назначить (быстро)», выберите дату и время, добавьте заметки (место, тема) и сохраните. Встреча появится в календаре, а вам и руководителю придёт уведомление в Telegram.`,
  },
  {
    id: 'meeting-date',
    title: '4. Встреча назначена, но нет даты ⚠',
    text: `В воронке у компаний со статусом «Встреча назначена» появляется пометка «⚠ нет даты». Это значит: договорились о встрече, но время ещё не проставлено. Откройте карточку → блок «Встреча» → выберите дату/время → сохраните. После этого напоминания (за сутки, час и 10 минут) будут приходить вам и руководителю в Telegram.`,
  },
  {
    id: 'pipeline',
    title: '5. Вкладка «Воронка»',
    text: `Здесь компании разложены по этапам: Новый → Сообщение отправлено → Диагностика пройдена → Тест предложен → Тест выполнен → Резерв → Клиент → Партнёр.`,
  },
  {
    id: 'pipeline-move',
    title: '6. Как двигать по воронке',
    text: `На карточке компании в воронке нажмите стрелку «→» и выберите следующий этап. Например, после успешного разговора — «Диагностика пройдена». Статус звонка при этом ставится отдельно во вкладке «Активность».`,
  },
  {
    id: 'comms',
    title: '7. Вкладка «Коммуникации»',
    text: `Здесь вся работа с письмами:\n• 📄 КП — скачать или отправить коммерческое предложение клиенту;\n• ✉️ Написать письмо — отправить email вручную;\n• ⏰ Создать follow-up — запланировать повторное письмо;\n• Email-история — все отправленные письма и их статус (открыто/не открыто).`,
  },
  {
    id: 'followup',
    title: '8. Что такое follow-up (фоллоу-ап)',
    text: `Follow-up — это «повторное касание» клиента: письмо, которое отправится автоматически в выбранный день, если клиент не ответил на первое. В русском — «напоминающее письмо» или «догоняющее письмо».\n\nКак пользоваться: после отправки КП создайте follow-up на 3–7 дней вперёд с коротким вопросом («Написали, не получили ли ответ на наше КП?»). Система отправит его сама, а в истории появится запись.`,
  },
  {
    id: 'ai',
    title: '9. Вкладка «AI»',
    text: `Здесь ИИ помогает с компанией: генерирует саммари, подсказывает аргументы для разговора и подставляет данные в карточку. Пользуйтесь перед звонком — быстрее подготовитесь.`,
  },
  {
    id: 'dashboard',
    title: '10. Сводка наверху',
    text: `Вверху — счётчики: задачи на сегодня, просроченные, звонки, компании в воронке. Клик по этапу воронки отфильтрует список компаний по этому этапу.`,
  },
  {
    id: 'end',
    title: 'Всё! 🎉',
    text: `Помните главное:\n• После звонка — сохраняйте статус и результат.\n• Договорились о встрече — сразу проставьте дату и время в блоке «Встреча».\n• Follow-up — для повторных писем через несколько дней.\n\nУдачи в работе!`,
  },
]

export default function GuideModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [idx, setIdx] = useState(0)
  const step = steps[idx]
  const isLast = idx === steps.length - 1

  const finish = () => {
    try { localStorage.setItem(GUIDE_KEY, '1') } catch {}
    onClose()
    setIdx(0)
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[60]" onClick={onClose}>
      <div className="bg-surface rounded-xl w-[480px] max-w-[92vw] shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
        <div className="h-1 bg-accent" style={{ width: `${((idx + 1) / steps.length) * 100}%`, transition: 'width 0.3s' }} />
        <div className="p-6 max-h-[70vh] overflow-y-auto">
          <div className="flex items-start justify-between mb-3">
            <h2 className="text-lg font-bold">{step.title}</h2>
            <button onClick={onClose} className="text-muted hover:text-text text-lg leading-none">✕</button>
          </div>
          <p className="text-sm text-text/90 whitespace-pre-wrap leading-relaxed">{step.text}</p>
        </div>
        <div className="flex items-center justify-between px-6 py-4 border-t border-muted/10">
          <button
            onClick={() => setIdx(i => Math.max(0, i - 1))}
            disabled={idx === 0}
            className="px-3 py-1.5 text-sm text-muted hover:text-text disabled:opacity-30 transition-colors"
          >
            ← Назад
          </button>
          <div className="flex gap-1.5">
            {steps.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setIdx(i)}
                className={`w-2 h-2 rounded-full transition-colors ${i === idx ? 'bg-accent w-4' : 'bg-muted/30 hover:bg-muted/50'}`}
                aria-label={`Шаг ${i + 1}`}
              />
            ))}
          </div>
          {isLast ? (
            <button
              onClick={finish}
              className="px-4 py-1.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Готово
            </button>
          ) : (
            <button
              onClick={() => setIdx(i => Math.min(steps.length - 1, i + 1))}
              className="px-4 py-1.5 bg-accent hover:bg-accent/90 text-white text-sm font-medium rounded-lg transition-colors"
            >
              Далее →
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function shouldShowGuide(): boolean {
  try {
    return localStorage.getItem(GUIDE_KEY) !== '1'
  } catch {
    return false
  }
}
